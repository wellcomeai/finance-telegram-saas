"""
Voice message handler
"""

import logging
import os
import tempfile
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from telegram_bot.config import BotMessages
from telegram_bot.keyboards import transaction_confirmation_keyboard
from ai.voice_transcriber import transcribe_voice, download_voice_file
from telegram_bot.handlers.text_handler import TransactionStates
from database.repositories.transaction_repo import TransactionRepository
from database.repositories.category_repo import CategoryRepository
from database.connection import get_db_connection
from datetime import datetime

logger = logging.getLogger(__name__)
router = Router()


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


@router.message(F.voice)
async def handle_voice_message(message: Message, state: FSMContext, db_user):
    """
    Handle voice messages from user
    Поддерживает как одиночные, так и множественные транзакции
    """
    processing_msg = await message.answer(BotMessages.PROCESSING)
    
    temp_file = None
    
    try:
        # Create temp file for voice
        temp_file = tempfile.NamedTemporaryFile(
            suffix='.ogg',
            delete=False,
            dir='/tmp'
        )
        temp_path = temp_file.name
        temp_file.close()
        
        logger.info(f"Voice message from user {db_user.id}, saving to {temp_path}")
        
        # Download voice file
        success = await download_voice_file(
            bot=message.bot,
            file_id=message.voice.file_id,
            destination=temp_path
        )
        
        if not success:
            await processing_msg.edit_text("❌ Ошибка загрузки голосового сообщения")
            return
        
        # Transcribe and parse - теперь возвращает список транзакций
        transactions = await transcribe_voice(temp_path)
        
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
        
        # ========== НЕСКОЛЬКО ТРАНЗАКЦИЙ - автосохранение ==========
        else:
            saved_count = 0
            failed_count = 0
            summary_lines = []
            
            logger.info(f"Processing {len(transactions)} voice transactions for user {db_user.id}")
            
            # Сохраняем каждую транзакцию
            for idx, transaction_data in enumerate(transactions, 1):
                success = await _save_transaction_to_db(transaction_data, db_user.id)
                
                if success:
                    saved_count += 1
                    
                    # Формируем строку для сводки
                    type_emoji = "💸" if transaction_data['type'] == 'expense' else "💰"
                    amount_formatted = f"{transaction_data['amount']:,.0f}".replace(",", " ")
                    
                    summary_lines.append(
                        f"{idx}. {type_emoji} {transaction_data['category_icon']} "
                        f"<b>{transaction_data['description']}</b> - {amount_formatted} ₽"
                    )
                else:
                    failed_count += 1
                    logger.error(f"Failed to save voice transaction {idx}: {transaction_data}")
            
            # Формируем итоговое сообщение
            if saved_count > 0:
                summary_text = f"🎤 <b>Сохранено транзакций: {saved_count}</b>\n\n"
                summary_text += "\n".join(summary_lines)
                
                if failed_count > 0:
                    summary_text += f"\n\n⚠️ Не удалось сохранить: {failed_count}"
                
                # Показываем общую сумму для расходов/доходов
                total_expenses = sum(t['amount'] for t in transactions if t['type'] == 'expense')
                total_income = sum(t['amount'] for t in transactions if t['type'] == 'income')
                
                summary_text += "\n\n<b>Итого:</b>\n"
                if total_expenses > 0:
                    summary_text += f"💸 Расходы: {total_expenses:,.0f} ₽\n".replace(",", " ")
                if total_income > 0:
                    summary_text += f"💰 Доходы: {total_income:,.0f} ₽\n".replace(",", " ")
                
                await processing_msg.edit_text(summary_text)
            else:
                # Все транзакции провалились
                await processing_msg.edit_text(
                    "❌ Не удалось сохранить транзакции.\n"
                    "Попробуйте еще раз или обратитесь в поддержку."
                )
            
            # Очищаем state (не нужен для множественных транзакций)
            await state.clear()
        
    except Exception as e:
        logger.error(f"Error handling voice message: {e}", exc_info=True)
        await processing_msg.edit_text(BotMessages.ERROR)
    
    finally:
        # Cleanup temp file
        if temp_file and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                logger.info(f"Temp voice file deleted: {temp_path}")
            except Exception as e:
                logger.error(f"Error deleting temp file: {e}")
