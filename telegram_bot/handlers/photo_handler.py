"""
Photo handler
"""

import logging
from aiogram import Router, F
from aiogram.types import Message

from telegram_bot.config import BotMessages

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.photo)
async def handle_photo_message(message: Message, db_user):
    """
    Handle photo messages from user
    """
    await message.answer("📷 Обработка фото чеков будет добавлена в следующей версии")
    logger.info(f"Photo from user {db_user.id}")  # ← Changed from db_user['id']
