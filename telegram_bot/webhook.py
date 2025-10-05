"""
Webhook setup for bot
"""

import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

logger = logging.getLogger(__name__)


async def on_startup(bot: Bot, webhook_url: str):
    """Set webhook on startup"""
    await bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to: {webhook_url}")


async def on_shutdown(bot: Bot):
    """Delete webhook on shutdown"""
    await bot.delete_webhook()
    logger.info("Webhook deleted")


def setup_webhook_app(bot: Bot, dp: Dispatcher, webhook_path: str) -> web.Application:
    """
    Setup webhook application
    
    Args:
        bot: Bot instance
        dp: Dispatcher instance
        webhook_path: Path for webhook (e.g., "/webhook")
    
    Returns:
        aiohttp web application
    """
    app = web.Application()
    
    # Setup webhook handler
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    )
    webhook_handler.register(app, path=webhook_path)
    
    # Setup application
    setup_application(app, dp, bot=bot)
    
    return app
