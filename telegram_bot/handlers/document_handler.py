"""
Document handler
"""

import logging
from aiogram import Router, F
from aiogram.types import Message

from telegram_bot.config import BotMessages

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.document)
async def handle_document_message(message: Message, db_user):
    """
    Handle document messages from user
    """
    await message.answer("📄 Обработка PDF чеков будет добавлена в следующей версии")
    logger.info(f"Document from user {db_user.id}")  # ← Changed from db_user['id']
