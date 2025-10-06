"""
/start command handler
"""

import logging
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from telegram_bot.config import BotMessages
from telegram_bot.keyboards import ai_chat_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """
    Handle /start command
    """
    await message.answer(
        BotMessages.WELCOME,
        reply_markup=ai_chat_keyboard()
    )
