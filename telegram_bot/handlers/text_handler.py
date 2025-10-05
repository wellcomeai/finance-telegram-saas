"""
Text message handler
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from telegram_bot.config import BotMessages
from telegram_bot.keyboards import transaction_confirmation_keyboard
from ai.text_parser import parse_transaction_text
from database.repositories.transaction_repo import TransactionRepository
from database.connection import get_db_connection
from datetime import datetime

logger = logging.getLogger(__name__)
router = Router()


class TransactionStates(StatesGroup):
    """States for transaction creation"""
    waiting_confirmation = State()
    editing = State()


@router.message(F.text & ~F.text.startswith('/'))
async def handle_text_message(message: Message, state: FSMContext, db_user):
    """
    Handle text messages from user
    """
    # Show processing message
    processing_msg = await message.answer(BotMessages.PROCESSING)
    
    try:
        # Parse transaction with AI
        transaction_data = await parse_transaction_text(message.text)
        
        if transaction_data is None:
            await processing_msg.edit_text(BotMessages.CANT_PARSE)
            return
        
        # Save to state
        await state.set_state(TransactionStates.waiting_confirmation)
        await state.update_data(
            transaction=transaction_data,
            user_id=db_user.id  # ← Changed from db_user['id']
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
            date=transaction_data.get('date', datetime.now().strftime('%d.%m.%Y'))
        )
        
        await processing_msg.edit_text(
            confirmation_text,
            reply_markup=transaction_confirmation_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error handling text message: {e}", exc_info=True)
        await processing_msg.edit_text(BotMessages.ERROR)


@router.callback_query(F.data == "transaction_save")
async def save_transaction(callback: CallbackQuery, state: FSMContext):
    """
    Save transaction to database
    """
    data = await state.get_data()
    transaction = data.get('transaction')
    user_id = data.get('user_id')
    
    if not transaction or not user_id:
        await callback.answer("Ошибка: данные не найдены")
        return
    
    try:
        async with get_db_connection() as conn:
            transaction_repo = TransactionRepository(conn)
            
            # Get category ID
            from database.repositories.category_repo import CategoryRepository
            category_repo = CategoryRepository(conn)
            category = await category_repo.get_by_name(transaction['category_name'])
            
            # Create transaction
            await transaction_repo.create(
                user_id=user_id,
                transaction_type=transaction['type'],
                amount=transaction['amount'],
                category_id=category.id if category else None,  # ← Changed from category['id']
                description=transaction['description'],
                transaction_date=transaction.get('date', datetime.now().date())
            )
        
        await callback.message.edit_text(BotMessages.TRANSACTION_SAVED)
        await state.clear()
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error saving transaction: {e}", exc_info=True)
        await callback.answer(BotMessages.ERROR, show_alert=True)


@router.callback_query(F.data == "transaction_cancel")
async def cancel_transaction(callback: CallbackQuery, state: FSMContext):
    """
    Cancel transaction creation
    """
    await callback.message.edit_text(BotMessages.TRANSACTION_CANCELLED)
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "transaction_edit")
async def edit_transaction(callback: CallbackQuery, state: FSMContext):
    """
    Edit transaction (for future implementation)
    """
    await callback.answer("Редактирование будет доступно в следующей версии", show_alert=True)
