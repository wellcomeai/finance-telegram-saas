"""
Voice message handler
"""

import logging
from aiogram import Router, F
from aiogram.types import Message

from telegram_bot.config import BotMessages

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.voice)
async def handle_voice_message(message: Message, db_user):
    """
    Handle voice messages from user
    """
    await message.answer("🎤 Обработка голосовых сообщений будет добавлена в следующей версии")
    logger.info(f"Voice message from user {db_user.id}")  # ← Changed from db_user['id']
