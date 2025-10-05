"""
/help command handler
"""

import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from telegram_bot.config import BotMessages

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("help"))
async def cmd_help(message: Message):
    """
    Handle /help command
    """
    await message.answer(BotMessages.HELP)


@router.message(Command("categories"))
async def cmd_categories(message: Message):
    """
    Show all categories
    """
    from shared.constants import CATEGORIES
    
    expense_cats = [f"{cat['icon']} {cat['name']}" for cat in CATEGORIES if cat['type'] == 'expense']
    income_cats = [f"{cat['icon']} {cat['name']}" for cat in CATEGORIES if cat['type'] == 'income']
    
    text = "<b>📁 Категории расходов:</b>\n"
    text += "\n".join(expense_cats)
    text += "\n\n<b>💰 Категории доходов:</b>\n"
    text += "\n".join(income_cats)
    
    await message.answer(text)


@router.message(Command("stats"))
async def cmd_stats(message: Message, db_user):
    """
    Show monthly statistics
    """
    from database.repositories.transaction_repo import TransactionRepository
    from database.connection import get_db_connection
    from datetime import datetime
    
    try:
        async with get_db_connection() as conn:
            transaction_repo = TransactionRepository(conn)
            
            # Get current month stats
            now = datetime.now()
            stats = await transaction_repo.get_monthly_stats(
                user_id=db_user.id,
                year=now.year,
                month=now.month
            )
            
            if stats['count'] == 0:
                await message.answer(BotMessages.NO_STATS)
                return
            
            month_names = {
                1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
                5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
                9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
            }
            
            text = BotMessages.STATS_MONTH.format(
                month=month_names[now.month],
                income=f"{stats['income']:,.0f}".replace(",", " "),
                expenses=f"{stats['expenses']:,.0f}".replace(",", " "),
                balance=f"{stats['balance']:,.0f}".replace(",", " "),
                count=stats['count']
            )
            
            await message.answer(text)
            
    except Exception as e:
        logger.error(f"Error in stats command: {e}", exc_info=True)
        await message.answer(BotMessages.ERROR)
