"""
Middleware for bot
"""

import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message

from database.repositories.user_repo import UserRepository
from database.connection import get_db_connection

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """
    Middleware to check if user exists in database and create if not
    """

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        """
        Check and create user if needed
        """
        user = event.from_user
        
        if user is None:
            return await handler(event, data)

        try:
            async with get_db_connection() as conn:
                user_repo = UserRepository(conn)
                
                # Check if user exists
                db_user = await user_repo.get_by_telegram_id(user.id)
                
                # Create user if doesn't exist
                if db_user is None:
                    db_user = await user_repo.create(
                        telegram_user_id=user.id,
                        username=user.username,
                        first_name=user.first_name,
                        last_name=user.last_name
                    )
                    logger.info(f"New user created: {user.id}")
                
                # Add user to data context
                data["db_user"] = db_user
                
        except Exception as e:
            logger.error(f"Error in AuthMiddleware: {e}")
        
        return await handler(event, data)
