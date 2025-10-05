"""
Category repository for database operations
"""

import logging
from typing import Optional, List
import asyncpg

from database.models import Category

logger = logging.getLogger(__name__)


class CategoryRepository:
    """Repository for Category operations"""
    
    def __init__(self, connection: asyncpg.Connection):
        self.conn = connection
    
    async def get_by_id(self, category_id: int) -> Optional[Category]:
        """
        Get category by ID
        
        Args:
            category_id: Category ID
            
        Returns:
            Category object or None
        """
        try:
            row = await self.conn.fetchrow(
                "SELECT * FROM categories WHERE id = $1",
                category_id
            )
            
            return Category(**dict(row)) if row else None
            
        except Exception as e:
            logger.error(f"Error getting category by ID: {e}", exc_info=True)
            return None
    
    async def get_by_name(self, name: str) -> Optional[Category]:
        """
        Get category by name
        
        Args:
            name: Category name
            
        Returns:
            Category object or None
        """
        try:
            row = await self.conn.fetchrow(
                "SELECT * FROM categories WHERE name = $1",
                name
            )
            
            return Category(**dict(row)) if row else None
            
        except Exception as e:
            logger.error(f"Error getting category by name: {e}", exc_info=True)
            return None
    
    async def get_all(self, category_type: Optional[str] = None, active_only: bool = True) -> List[Category]:
        """
        Get all categories
        
        Args:
            category_type: Filter by type ('income' or 'expense')
            active_only: Only return active categories
            
        Returns:
            List of Category objects
        """
        try:
            conditions = []
            params = []
            param_idx = 1
            
            if active_only:
                conditions.append("is_active = true")
            
            if category_type:
                conditions.append(f"type = ${param_idx}")
                params.append(category_type)
                param_idx += 1
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = f"""
                SELECT * FROM categories
                WHERE {where_clause}
                ORDER BY id
            """
            
            rows = await self.conn.fetch(query, *params)
            
            return [Category(**dict(row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting all categories: {e}", exc_info=True)
            return []
    
    async def get_expense_categories(self) -> List[Category]:
        """Get all expense categories"""
        return await self.get_all(category_type='expense')
    
    async def get_income_categories(self) -> List[Category]:
        """Get all income categories"""
        return await self.get_all(category_type='income')
    
    async def create(self, name: str, icon: str, category_type: str) -> Category:
        """
        Create a new category
        
        Args:
            name: Category name
            icon: Category icon emoji
            category_type: 'income' or 'expense'
            
        Returns:
            Created Category object
        """
        try:
            row = await self.conn.fetchrow(
                """
                INSERT INTO categories (name, icon, type)
                VALUES ($1, $2, $3)
                RETURNING *
                """,
                name, icon, category_type
            )
            
            logger.info(f"Category created: {name}")
            return Category(**dict(row))
            
        except Exception as e:
            logger.error(f"Error creating category: {e}", exc_info=True)
            raise
    
    async def update(
        self,
        category_id: int,
        name: Optional[str] = None,
        icon: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Category]:
        """
        Update category
        
        Args:
            category_id: Category ID
            name: New name
            icon: New icon
            is_active: Active status
            
        Returns:
            Updated Category object or None
        """
        try:
            updates = []
            params = [category_id]
            param_idx = 2
            
            if name is not None:
                updates.append(f"name = ${param_idx}")
                params.append(name)
                param_idx += 1
            
            if icon is not None:
                updates.append(f"icon = ${param_idx}")
                params.append(icon)
                param_idx += 1
            
            if is_active is not None:
                updates.append(f"is_active = ${param_idx}")
                params.append(is_active)
                param_idx += 1
            
            if not updates:
                return await self.get_by_id(category_id)
            
            update_clause = ", ".join(updates)
            
            query = f"""
                UPDATE categories
                SET {update_clause}
                WHERE id = $1
                RETURNING *
            """
            
            row = await self.conn.fetchrow(query, *params)
            
            if row:
                logger.info(f"Category updated: id={category_id}")
                return Category(**dict(row))
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating category: {e}", exc_info=True)
            return None
    
    async def count(self) -> int:
        """
        Count total number of categories
        
        Returns:
            Total category count
        """
        try:
            count = await self.conn.fetchval("SELECT COUNT(*) FROM categories")
            return count or 0
            
        except Exception as e:
            logger.error(f"Error counting categories: {e}", exc_info=True)
            return 0
