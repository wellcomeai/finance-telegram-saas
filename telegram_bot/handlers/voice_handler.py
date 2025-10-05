"""
Voice message handler
"""

import logging
import os
import tempfile
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from telegram_bot.config import BotMessages
from telegram_bot.keyboards import transaction_confirmation_keyboard
from ai.voice_transcriber import transcribe_voice, download_voice_file
from telegram_bot.handlers.text_handler import TransactionStates
from datetime import datetime

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.voice)
async def handle_voice_message(message: Message, state: FSMContext, db_user):
    """
    Handle voice messages from user
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
        
        # Transcribe and parse
        transaction_data = await transcribe_voice(temp_path)
        
        if transaction_data is None:
            await processing_msg.edit_text(BotMessages.CANT_PARSE)
            return
        
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
            date=transaction_data['date'].strftime('%d.%m.%Y') if hasattr(transaction_data['date'], 'strftime') else transaction_data['date']
        )
        
        await processing_msg.edit_text(
            confirmation_text,
            reply_markup=transaction_confirmation_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error handling voice message: {e}", exc_info=True)
        await processing_msg.edit_text(BotMessages.ERROR)
    
    finally:
        # Cleanup temp file
        if temp_file and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                logger.info(f"Temp file deleted: {temp_path}")
            except Exception as e:
                logger.error(f"Error deleting temp file: {e}")
