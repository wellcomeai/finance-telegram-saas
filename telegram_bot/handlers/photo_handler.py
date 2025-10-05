"""
Photo handler
"""

import logging
import os
import tempfile
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from telegram_bot.config import BotMessages
from telegram_bot.keyboards import transaction_confirmation_keyboard
from ai.image_processor import process_receipt_image, download_photo_file
from telegram_bot.handlers.text_handler import TransactionStates
from datetime import datetime

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.photo)
async def handle_photo_message(message: Message, state: FSMContext, db_user):
    """
    Handle photo messages from user (receipts)
    """
    processing_msg = await message.answer(BotMessages.PROCESSING)
    
    temp_file = None
    
    try:
        # Get the largest photo (best quality)
        photo = message.photo[-1]  # Последнее фото = наибольшее разрешение
        
        logger.info(f"Photo from user {db_user.id}, size: {photo.width}x{photo.height}, file_size: {photo.file_size}")
        
        # Create temp file for photo
        temp_file = tempfile.NamedTemporaryFile(
            suffix='.jpg',
            delete=False,
            dir='/tmp'
        )
        temp_path = temp_file.name
        temp_file.close()
        
        # Download photo
        success = await download_photo_file(
            bot=message.bot,
            file_id=photo.file_id,
            destination=temp_path
        )
        
        if not success:
            await processing_msg.edit_text("❌ Ошибка загрузки фото")
            return
        
        # Process receipt image with Vision AI
        transaction_data = await process_receipt_image(temp_path)
        
        if transaction_data is None:
            await processing_msg.edit_text(
                "❌ Не удалось распознать чек на фото.\n\n"
                "Попробуйте:\n"
                "• Сделать фото чётче\n"
                "• Убедиться что чек полностью в кадре\n"
                "• Улучшить освещение"
            )
            return
        
        # Save to state
        await state.set_state(TransactionStates.waiting_confirmation)
        await state.update_data(
            transaction=transaction_data,
            user_id=db_user.id
        )
        
        # Show confirmation
        type_emoji = "💸"  # Чеки всегда расходы
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
        logger.error(f"Error handling photo message: {e}", exc_info=True)
        await processing_msg.edit_text(BotMessages.ERROR)
    
    finally:
        # Cleanup temp file
        if temp_file and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                logger.info(f"Temp file deleted: {temp_path}")
            except Exception as e:
                logger.error(f"Error deleting temp file: {e}")
