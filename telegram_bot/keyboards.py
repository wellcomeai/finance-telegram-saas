"""
Keyboards for Telegram bot
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram_bot.config import BotButtons
from shared.config import settings


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Main menu keyboard with Web App button
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BotButtons.OPEN_APP, web_app=WebAppInfo(url=settings.TELEGRAM_WEBAPP_URL))]
        ],
        resize_keyboard=True,
        persistent=True
    )
    return keyboard


def transaction_confirmation_keyboard() -> InlineKeyboardMarkup:
    """
    Keyboard for transaction confirmation
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=BotButtons.SAVE, callback_data="transaction_save"),
                InlineKeyboardButton(text=BotButtons.EDIT, callback_data="transaction_edit")
            ],
            [
                InlineKeyboardButton(text=BotButtons.CANCEL, callback_data="transaction_cancel")
            ]
        ]
    )
    return keyboard


def transaction_edit_keyboard() -> InlineKeyboardMarkup:
    """
    Keyboard for editing transaction fields
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=BotButtons.EDIT_AMOUNT, callback_data="edit_amount"),
                InlineKeyboardButton(text=BotButtons.EDIT_CATEGORY, callback_data="edit_category")
            ],
            [
                InlineKeyboardButton(text=BotButtons.EDIT_DESCRIPTION, callback_data="edit_description"),
                InlineKeyboardButton(text=BotButtons.EDIT_DATE, callback_data="edit_date")
            ],
            [
                InlineKeyboardButton(text=BotButtons.CANCEL, callback_data="transaction_cancel")
            ]
        ]
    )
    return keyboard


def open_app_keyboard() -> InlineKeyboardMarkup:
    """
    Keyboard with button to open Web App
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BotButtons.OPEN_APP,
                    web_app=WebAppInfo(url=settings.TELEGRAM_WEBAPP_URL)
                )
            ]
        ]
    )
    return keyboard
