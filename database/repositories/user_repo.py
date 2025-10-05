"""
User repository for database operations
"""

import logging
from typing import Optional, List
from datetime import datetime
import asyncpg

from database.models import User

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for User operations"""
    
    def __init__(self, connection: asyncpg.Connection):
        self.conn = connection
    
    async def create(
        self,
        telegram_user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> User:
        """
        Create a new user
        
        Args:
            telegram_user_id: Telegram user ID
            username: Telegram username
            first_name: User's first name
            last_name: User's last name
            
        Returns:
            Created User object
        """
        try:
            row = await self.conn.fetchrow(
                """
                INSERT INTO users (telegram_user_id, username, first_name, last_name)
                VALUES ($1, $2, $3, $4)
                RETURNING id, telegram_user_id, username, first_name, last_name, created_at, updated_at
                """,
                telegram_user_id, username, first_name, last_name
            )
            
            logger.info(f"User created: telegram_id={telegram_user_id}")
            return User(**dict(row))
            
        except Exception as e:
            logger.error(f"Error creating user: {e}", exc_info=True)
            raise
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID
        
        Args:
            user_id: User ID
            
        Returns:
            User object or None
        """
        try:
            row = await self.conn.fetchrow(
                "SELECT * FROM users WHERE id = $1",
                user_id
            )
            
            return User(**dict(row)) if row else None
            
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}", exc_info=True)
            return None
    
    async def get_by_telegram_id(self, telegram_user_id: int) -> Optional[User]:
        """
        Get user by Telegram user ID
        
        Args:
            telegram_user_id: Telegram user ID
            
        Returns:
            User object or None
        """
        try:
            row = await self.conn.fetchrow(
                "SELECT * FROM users WHERE telegram_user_id = $1",
                telegram_user_id
            )
            
            return User(**dict(row)) if row else None
            
        except Exception as e:
            logger.error(f"Error getting user by telegram ID: {e}", exc_info=True)
            return None
    
    async def update(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> Optional[User]:
        """
        Update user information
        
        Args:
            user_id: User ID
            username: New username
            first_name: New first name
            last_name: New last name
            
        Returns:
            Updated User object or None
        """
        try:
            row = await self.conn.fetchrow(
                """
                UPDATE users
                SET username = COALESCE($2, username),
                    first_name = COALESCE($3, first_name),
                    last_name = COALESCE($4, last_name),
                    updated_at = NOW()
                WHERE id = $1
                RETURNING *
                """,
                user_id, username, first_name, last_name
            )
            
            if row:
                logger.info(f"User updated: id={user_id}")
                return User(**dict(row))
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating user: {e}", exc_info=True)
            return None
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[User]:
        """
        Get all users with pagination
        
        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            List of User objects
        """
        try:
            rows = await self.conn.fetch(
                """
                SELECT * FROM users
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit, offset
            )
            
            return [User(**dict(row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting all users: {e}", exc_info=True)
            return []
    
    async def count(self) -> int:
        """
        Count total number of users
        
        Returns:
            Total user count
        """
        try:
            count = await self.conn.fetchval("SELECT COUNT(*) FROM users")
            return count or 0
            
        except Exception as e:
            logger.error(f"Error counting users: {e}", exc_info=True)
            return 0
    
    async def delete(self, user_id: int) -> bool:
        """
        Delete user (soft delete by setting is_active = false in future)
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted successfully
        """
        try:
            result = await self.conn.execute(
                "DELETE FROM users WHERE id = $1",
                user_id
            )
            
            deleted = result.split()[-1] == "1"
            if deleted:
                logger.info(f"User deleted: id={user_id}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Error deleting user: {e}", exc_info=True)
            return False
