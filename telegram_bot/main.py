"""
Telegram Bot Main Entry Point
"""

import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiohttp import web

from shared.config import settings, validate_config
from shared.logger import setup_logging
from database.connection import init_database, close_database, run_migrations
from api_handlers import setup_api_routes

# Import handlers
from telegram_bot.handlers.start import router as start_router
from telegram_bot.handlers.help import router as help_router
from telegram_bot.handlers.text_handler import router as text_router
from telegram_bot.handlers.voice_handler import router as voice_router
from telegram_bot.handlers.photo_handler import router as photo_router
from telegram_bot.handlers.document_handler import router as document_router
from telegram_bot.handlers.ai_chat_handler import router as ai_chat_router

# Import middleware
from telegram_bot.middleware import AuthMiddleware

# Import webhook setup
from telegram_bot.webhook import on_startup, on_shutdown, setup_webhook_app

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


def setup_static_routes(app):
    """
    Setup static file routes for webapp
    """
    import os
    from aiohttp import web
    
    # Get webapp directory path
    webapp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'webapp')
    
    logger.info(f"Setting up static routes from: {webapp_dir}")
    
    # Check if directory exists
    if not os.path.exists(webapp_dir):
        logger.error(f"Webapp directory not found: {webapp_dir}")
        logger.info(f"Current working directory: {os.getcwd()}")
        # Try alternative path
        webapp_dir = os.path.join(os.getcwd(), 'webapp')
        logger.info(f"Trying alternative path: {webapp_dir}")
        
        if not os.path.exists(webapp_dir):
            logger.error(f"Alternative webapp directory also not found")
            return
    
    # Log directory contents
    logger.info(f"Webapp directory exists: {os.path.exists(webapp_dir)}")
    if os.path.exists(webapp_dir):
        try:
            contents = os.listdir(webapp_dir)
            logger.info(f"Webapp directory contents: {contents}")
        except Exception as e:
            logger.error(f"Error listing directory: {e}")
    
    # Serve index.html at /webapp (БЕЗ trailing slash)
    async def serve_webapp_index(request):
        index_path = os.path.join(webapp_dir, 'index.html')
        if not os.path.exists(index_path):
            logger.error(f"index.html not found: {index_path}")
            return web.Response(text='index.html not found', status=404)
        logger.info(f"Serving index.html from: {index_path}")
        return web.FileResponse(index_path)
    
    # Redirect from root to webapp
    async def redirect_to_webapp(request):
        logger.info("Redirecting / to /webapp")
        return web.HTTPFound('/webapp')
    
    # Add routes in correct order
    app.router.add_get('/', redirect_to_webapp)
    app.router.add_get('/webapp', serve_webapp_index)
    
    # Serve static files (CSS, JS, etc.) - ПОСЛЕ index.html роута
    try:
        app.router.add_static('/webapp/', path=webapp_dir, name='webapp')
        logger.info("Static file route added successfully")
    except Exception as e:
        logger.error(f"Error adding static route: {e}")
    
    logger.info("Static routes configured successfully")
    logger.info(f"Webapp available at: /webapp")


async def init_app():
    """
    Initialize application
    """
    try:
        logger.info("=" * 60)
        logger.info("Finance Tracker Bot Starting...")
        logger.info("=" * 60)
        
        # Validate configuration
        logger.info("Validating configuration...")
        validate_config()
        logger.info("✓ Configuration valid")
        
        # Initialize database
        logger.info("Initializing database...")
        await init_database()
        logger.info("✓ Database initialized")
        
        # Run migrations - ЗАКОММЕНТИРОВАНО (запускать вручную или только первый раз)
        # ВАЖНО: Раскомментируйте только при первом деплое или при добавлении новых миграций
        # logger.info("Running database migrations...")
        # await run_migrations()
        # logger.info("✓ Migrations completed")
        
        logger.info("=" * 60)
        logger.info("Initialization completed successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}", exc_info=True)
        raise


async def main():
    """
    Main function to start the bot with webhook
    """
    bot = None
    
    try:
        # Initialize app (database, etc.)
        await init_app()
        
        # Initialize bot and dispatcher
        bot = Bot(
            token=settings.TELEGRAM_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        dp = Dispatcher()

        # Register middleware
        dp.message.middleware(AuthMiddleware())
        dp.callback_query.middleware(AuthMiddleware())

        # Register bot handlers
        dp.include_router(start_router)
        dp.include_router(help_router)
        dp.include_router(ai_chat_router)
        dp.include_router(text_router)
        dp.include_router(voice_router)
        dp.include_router(photo_router)
        dp.include_router(document_router)

        # Webhook configuration
        WEBHOOK_PATH = "/webhook"
        WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL", "https://your-app.onrender.com")
        WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
        
        # Port for Render (or local development)
        PORT = int(os.getenv("PORT", 8080))

        logger.info("=" * 60)
        logger.info("Starting bot with webhook...")
        logger.info(f"Webhook URL: {WEBHOOK_URL}")
        logger.info(f"Port: {PORT}")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info("=" * 60)

        # Set webhook
        await on_startup(bot, WEBHOOK_URL)
        
        # Setup webhook app
        app = setup_webhook_app(bot, dp, WEBHOOK_PATH)
        
        # Setup static routes for webapp
        setup_static_routes(app)
        
        # Setup API routes
        setup_api_routes(app)
        
        # Health check endpoint
        async def health_check(request):
            return web.json_response({
                'status': 'ok',
                'bot': 'running',
                'webapp': 'available'
            })
        
        app.router.add_get('/health', health_check)
        
        # Start web server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        
        logger.info("=" * 60)
        logger.info(f"✅ Server started successfully on port {PORT}")
        logger.info(f"✅ Bot webhook: {WEBHOOK_URL}")
        logger.info(f"✅ WebApp URL: {WEBHOOK_HOST}/webapp")
        logger.info(f"✅ API endpoint: {WEBHOOK_HOST}/api/")
        logger.info(f"✅ Health check: {WEBHOOK_HOST}/health")
        logger.info("=" * 60)
        logger.info("Bot is ready to accept requests!")
        logger.info("=" * 60)
        
        # Keep running
        await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        # Cleanup
        logger.info("Cleaning up...")
        try:
            if bot is not None:
                await on_shutdown(bot)
                await bot.session.close()
            await close_database()
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}", exc_info=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application crashed: {e}", exc_info=True)
        raise
