"""
Text message handler
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from telegram_bot.config import BotMessages
from telegram_bot.keyboards import transaction_confirmation_keyboard, multiple_transactions_confirmation_keyboard
from ai.text_parser import parse_transaction_text
from database.repositories.transaction_repo import TransactionRepository
from database.repositories.category_repo import CategoryRepository
from database.connection import get_db_connection
from datetime import datetime

logger = logging.getLogger(__name__)
router = Router()


class TransactionStates(StatesGroup):
    """States for transaction creation"""
    waiting_confirmation = State()  # Для одиночной транзакции
    waiting_multiple_confirmation = State()  # Для множественных транзакций
    editing = State()


async def _save_transaction_to_db(transaction_data: dict, user_id: int) -> bool:
    """
    Вспомогательная функция для сохранения транзакции в БД
    
    Returns:
        True если успешно сохранено, False в случае ошибки
    """
    try:
        async with get_db_connection() as conn:
            transaction_repo = TransactionRepository(conn)
            category_repo = CategoryRepository(conn)
            
            # Get category ID
            category = await category_repo.get_by_name(transaction_data['category_name'])
            
            # Create transaction
            await transaction_repo.create(
                user_id=user_id,
                transaction_type=transaction_data['type'],
                amount=transaction_data['amount'],
                category_id=category.id if category else None,
                description=transaction_data['description'],
                transaction_date=transaction_data.get('date', datetime.now().date())
            )
            
            logger.info(f"Transaction saved: {transaction_data['type']} {transaction_data['amount']} ₽")
            return True
            
    except Exception as e:
        logger.error(f"Error saving transaction to DB: {e}", exc_info=True)
        return False


@router.message(F.text & ~F.text.startswith('/'))
async def handle_text_message(message: Message, state: FSMContext, db_user):
    """
    Handle text messages from user
    Поддерживает как одиночные, так и множественные транзакции
    """
    processing_msg = await message.answer(BotMessages.PROCESSING)
    
    try:
        # Parse transaction(s) with AI - теперь возвращает список
        transactions = await parse_transaction_text(message.text)
        
        # Проверка: если пустой список или None
        if not transactions or len(transactions) == 0:
            await processing_msg.edit_text(BotMessages.CANT_PARSE)
            return
        
        # ========== ОДНА ТРАНЗАКЦИЯ - показываем подтверждение ==========
        if len(transactions) == 1:
            transaction_data = transactions[0]
            
            # Save to state
            await state.set_state(TransactionStates.waiting_confirmation)
            await state.update_data(
                transaction=transaction_data,
                user_id=db_user.id
            )
            
            # Show confirmation
            type_emoji = "💸" if transaction_data['type'] == 'expense' else "💰"
            type_name = "Расход" if transaction_data['type'] == 'expense' else "Доход"
            
            confirmation_text = BotMessages.TRANSACTION_CONFIRM.format(
                type_emoji=type_emoji,
                type_name=type_name,
                amount=f"{transaction_data['amount']:,.2f}".replace(",", " "),
                category_icon=transaction_data['category_icon'],
                category_name=transaction_data['category_name'],
                description=transaction_data['description'],
                date=transaction_data['date'].strftime('%d.%m.%Y') if hasattr(transaction_data['date'], 'strftime') else str(transaction_data['date'])
            )
            
            await processing_msg.edit_text(
                confirmation_text,
                reply_markup=transaction_confirmation_keyboard()
            )
        
        # ========== НЕСКОЛЬКО ТРАНЗАКЦИЙ - показываем подтверждение для всех ==========
        else:
            # Save to state
            await state.set_state(TransactionStates.waiting_multiple_confirmation)
            await state.update_data(
                transactions=transactions,
                user_id=db_user.id
            )
            
            # Формируем список транзакций для отображения
            transactions_list = []
            for idx, transaction_data in enumerate(transactions, 1):
                type_emoji = "💸" if transaction_data['type'] == 'expense' else "💰"
                amount_formatted = f"{transaction_data['amount']:,.0f}".replace(",", " ")
                
                transactions_list.append(
                    f"{idx}. {type_emoji} {transaction_data['category_icon']} "
                    f"<b>{transaction_data['description']}</b> - {amount_formatted} ₽"
                )
            
            # Считаем общие суммы
            total_expenses = sum(t['amount'] for t in transactions if t['type'] == 'expense')
            total_income = sum(t['amount'] for t in transactions if t['type'] == 'income')
            
            totals_parts = []
            if total_expenses > 0:
                totals_parts.append(f"💸 Расходы: {total_expenses:,.0f} ₽".replace(",", " "))
            if total_income > 0:
                totals_parts.append(f"💰 Доходы: {total_income:,.0f} ₽".replace(",", " "))
            
            totals_text = "\n".join(totals_parts)
            
            # Формируем итоговое сообщение
            confirmation_text = BotMessages.MULTIPLE_TRANSACTIONS_CONFIRM.format(
                count=len(transactions),
                transactions_list="\n".join(transactions_list),
                totals=totals_text
            )
            
            await processing_msg.edit_text(
                confirmation_text,
                reply_markup=multiple_transactions_confirmation_keyboard()
            )
            
            logger.info(f"Showing confirmation for {len(transactions)} transactions to user {db_user.id}")
        
    except Exception as e:
        logger.error(f"Error handling text message: {e}", exc_info=True)
        await processing_msg.edit_text(BotMessages.ERROR)


@router.callback_query(F.data == "transaction_save")
async def save_transaction(callback: CallbackQuery, state: FSMContext):
    """
    Save single transaction to database (для подтверждения одиночных транзакций)
    """
    data = await state.get_data()
    transaction = data.get('transaction')
    user_id = data.get('user_id')
    
    if not transaction or not user_id:
        await callback.answer("Ошибка: данные не найдены")
        return
    
    try:
        # Используем вспомогательную функцию
        success = await _save_transaction_to_db(transaction, user_id)
        
        if success:
            await callback.message.edit_text(BotMessages.TRANSACTION_SAVED)
            await state.clear()
            await callback.answer()
        else:
            await callback.answer("Ошибка при сохранении", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error in save_transaction callback: {e}", exc_info=True)
        await callback.answer(BotMessages.ERROR, show_alert=True)


@router.callback_query(F.data == "transactions_save_all")
async def save_all_transactions(callback: CallbackQuery, state: FSMContext):
    """
    Save all transactions to database (для множественных транзакций)
    """
    data = await state.get_data()
    transactions = data.get('transactions')
    user_id = data.get('user_id')
    
    if not transactions or not user_id:
        await callback.answer("Ошибка: данные не найдены")
        return
    
    try:
        saved_count = 0
        failed_count = 0
        
        logger.info(f"Saving {len(transactions)} transactions for user {user_id}")
        
        # Сохраняем каждую транзакцию
        for transaction_data in transactions:
            success = await _save_transaction_to_db(transaction_data, user_id)
            if success:
                saved_count += 1
            else:
                failed_count += 1
        
        # Формируем итоговое сообщение
        if saved_count > 0:
            message_text = BotMessages.TRANSACTIONS_SAVED.format(count=saved_count)
            
            if failed_count > 0:
                message_text += f"\n\n⚠️ Не удалось сохранить: {failed_count}"
            
            await callback.message.edit_text(message_text)
            await state.clear()
            await callback.answer()
        else:
            await callback.answer(
                "Не удалось сохранить транзакции. Попробуйте еще раз.",
                show_alert=True
            )
        
    except Exception as e:
        logger.error(f"Error in save_all_transactions callback: {e}", exc_info=True)
        await callback.answer(BotMessages.ERROR, show_alert=True)


@router.callback_query(F.data == "transaction_cancel")
async def cancel_transaction(callback: CallbackQuery, state: FSMContext):
    """
    Cancel single transaction creation
    """
    await callback.message.edit_text(BotMessages.TRANSACTION_CANCELLED)
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "transactions_cancel_all")
async def cancel_all_transactions(callback: CallbackQuery, state: FSMContext):
    """
    Cancel all transactions creation
    """
    await callback.message.edit_text(BotMessages.TRANSACTIONS_CANCELLED)
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "transaction_edit")
async def edit_transaction(callback: CallbackQuery, state: FSMContext):
    """
    Edit transaction (for future implementation)
    """
    await callback.answer("Редактирование будет доступно в следующей версии", show_alert=True)
