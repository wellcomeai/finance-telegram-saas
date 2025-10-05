"""
Document handler
"""

import logging
import os
import tempfile
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from telegram_bot.config import BotMessages
from telegram_bot.keyboards import transaction_confirmation_keyboard
from ai.pdf_processor import process_receipt_pdf, download_document_file
from telegram_bot.handlers.text_handler import TransactionStates
from datetime import datetime

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.document)
async def handle_document_message(message: Message, state: FSMContext, db_user):
    """
    Handle document messages from user (PDF receipts)
    """
    # Проверяем что это PDF
    if not message.document.file_name.lower().endswith('.pdf'):
        await message.answer(
            "❌ Поддерживаются только PDF файлы.\n\n"
            "Отправьте чек в формате PDF."
        )
        return
    
    processing_msg = await message.answer(BotMessages.PROCESSING)
    
    temp_file = None
    
    try:
        logger.info(
            f"PDF document from user {db_user.id}, "
            f"filename: {message.document.file_name}, "
            f"size: {message.document.file_size} bytes"
        )
        
        # Проверка размера файла (20MB limit)
        if message.document.file_size > 20 * 1024 * 1024:
            await processing_msg.edit_text(
                "❌ Файл слишком большой (максимум 20MB).\n\n"
                "Попробуйте сжать PDF или отправить фото чека."
            )
            return
        
        # Create temp file for PDF
        temp_file = tempfile.NamedTemporaryFile(
            suffix='.pdf',
            delete=False,
            dir='/tmp'
        )
        temp_path = temp_file.name
        temp_file.close()
        
        # Download PDF file
        success = await download_document_file(
            bot=message.bot,
            file_id=message.document.file_id,
            destination=temp_path
        )
        
        if not success:
            await processing_msg.edit_text("❌ Ошибка загрузки PDF файла")
            return
        
        # Process PDF receipt
        transaction_data = await process_receipt_pdf(temp_path)
        
        if transaction_data is None:
            await processing_msg.edit_text(
                "❌ Не удалось распознать чек в PDF.\n\n"
                "Убедитесь что:\n"
                "• PDF содержит текст (не просто картинку)\n"
                "• Чек читаемый и не повреждён\n"
                "• Указана сумма покупки\n\n"
                "💡 Попробуйте отправить фото чека вместо PDF"
            )
            return
        
        # Save to state
        await state.set_state(TransactionStates.waiting_confirmation)
        await state.update_data(
            transaction=transaction_data,
            user_id=db_user.id
        )
        
        # Show confirmation
        type_emoji = "💸"  # PDF чеки всегда расходы
        type_name = "Расход"
        
        confirmation_text = BotMessages.TRANSACTION_CONFIRM.format(
            type_emoji=type_emoji,
            type_name=type_name,
            amount=f"{transaction_data['amount']:,.2f}".replace(",", " "),
            category_icon=transaction_data['category_icon'],
            category_name=transaction_data['category_name'],
            description=transaction_data['description'],
            date=transaction_data['date'].strftime('%d.%m.%Y') if hasattr(transaction_data['date'], 'strftime') else transaction_data['date']
        )
        
        await processing_msg.edit_text(
            confirmation_text,
            reply_markup=transaction_confirmation_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error handling PDF document: {e}", exc_info=True)
        await processing_msg.edit_text(
            "❌ Произошла ошибка при обработке PDF.\n\n"
            "Попробуйте:\n"
            "• Отправить другой файл\n"
            "• Отправить фото чека\n"
            "• Написать транзакцию текстом"
        )
    
    finally:
        # Cleanup temp file
        if temp_file and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                logger.info(f"Temp PDF file deleted: {temp_path}")
            except Exception as e:
                logger.error(f"Error deleting temp PDF file: {e}")
