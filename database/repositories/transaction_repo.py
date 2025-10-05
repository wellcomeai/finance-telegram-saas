"""
Transaction repository for database operations
"""

import logging
from typing import Optional, List, Dict
from datetime import datetime, date, timedelta
from decimal import Decimal
import asyncpg

from database.models import Transaction, Category

logger = logging.getLogger(__name__)


class TransactionRepository:
    """Repository for Transaction operations"""
    
    def __init__(self, connection: asyncpg.Connection):
        self.conn = connection
    
    async def create(
        self,
        user_id: int,
        transaction_type: str,
        amount: float,
        category_id: Optional[int] = None,
        description: Optional[str] = None,
        transaction_date: Optional[date] = None
    ) -> Transaction:
        """
        Create a new transaction
        
        Args:
            user_id: User ID
            transaction_type: 'income' or 'expense'
            amount: Transaction amount
            category_id: Category ID
            description: Transaction description
            transaction_date: Date of transaction (defaults to today)
            
        Returns:
            Created Transaction object
        """
        try:
            if transaction_date is None:
                transaction_date = date.today()
            
            row = await self.conn.fetchrow(
                """
                INSERT INTO transactions (user_id, type, amount, category_id, description, transaction_date)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, user_id, type, amount, category_id, description, transaction_date, created_at, updated_at
                """,
                user_id, transaction_type, Decimal(str(amount)), category_id, description, transaction_date
            )
            
            logger.info(f"Transaction created: user_id={user_id}, type={transaction_type}, amount={amount}")
            return Transaction(**dict(row))
            
        except Exception as e:
            logger.error(f"Error creating transaction: {e}", exc_info=True)
            raise
    
    async def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """
        Get transaction by ID
        
        Args:
            transaction_id: Transaction ID
            
        Returns:
            Transaction object or None
        """
        try:
            row = await self.conn.fetchrow(
                "SELECT * FROM transactions WHERE id = $1",
                transaction_id
            )
            
            return Transaction(**dict(row)) if row else None
            
        except Exception as e:
            logger.error(f"Error getting transaction by ID: {e}", exc_info=True)
            return None
    
    async def get_user_transactions(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        transaction_type: Optional[str] = None,
        category_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict]:
        """
        Get user's transactions with filters and pagination
        
        Args:
            user_id: User ID
            limit: Maximum number of transactions
            offset: Number of transactions to skip
            transaction_type: Filter by type ('income' or 'expense')
            category_id: Filter by category
            start_date: Filter from date
            end_date: Filter to date
            
        Returns:
            List of transaction dictionaries with category info
        """
        try:
            # Build dynamic query
            conditions = ["t.user_id = $1"]
            params = [user_id]
            param_idx = 2
            
            if transaction_type:
                conditions.append(f"t.type = ${param_idx}")
                params.append(transaction_type)
                param_idx += 1
            
            if category_id:
                conditions.append(f"t.category_id = ${param_idx}")
                params.append(category_id)
                param_idx += 1
            
            if start_date:
                conditions.append(f"t.transaction_date >= ${param_idx}")
                params.append(start_date)
                param_idx += 1
            
            if end_date:
                conditions.append(f"t.transaction_date <= ${param_idx}")
                params.append(end_date)
                param_idx += 1
            
            where_clause = " AND ".join(conditions)
            
            # Add limit and offset
            params.extend([limit, offset])
            
            query = f"""
                SELECT 
                    t.*,
                    c.name as category_name,
                    c.icon as category_icon,
                    c.type as category_type
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE {where_clause}
                ORDER BY t.transaction_date DESC, t.created_at DESC
                LIMIT ${param_idx} OFFSET ${param_idx + 1}
            """
            
            rows = await self.conn.fetch(query, *params)
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting user transactions: {e}", exc_info=True)
            return []
    
    async def get_monthly_stats(self, user_id: int, year: int, month: int) -> Dict:
        """
        Get monthly statistics for user
        
        Args:
            user_id: User ID
            year: Year
            month: Month (1-12)
            
        Returns:
            Dictionary with income, expenses, balance, count
        """
        try:
            row = await self.conn.fetchrow(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as income,
                    COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as expenses,
                    COUNT(*) as count
                FROM transactions
                WHERE user_id = $1
                  AND EXTRACT(YEAR FROM transaction_date) = $2
                  AND EXTRACT(MONTH FROM transaction_date) = $3
                """,
                user_id, year, month
            )
            
            income = float(row['income'])
            expenses = float(row['expenses'])
            balance = income - expenses
            
            return {
                'income': income,
                'expenses': expenses,
                'balance': balance,
                'count': row['count']
            }
            
        except Exception as e:
            logger.error(f"Error getting monthly stats: {e}", exc_info=True)
            return {'income': 0, 'expenses': 0, 'balance': 0, 'count': 0}
    
    async def get_category_stats(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        transaction_type: str = 'expense'
    ) -> List[Dict]:
        """
        Get statistics grouped by category
        
        Args:
            user_id: User ID
            start_date: Filter from date
            end_date: Filter to date
            transaction_type: 'income' or 'expense'
            
        Returns:
            List of dictionaries with category stats
        """
        try:
            conditions = ["t.user_id = $1", "t.type = $2"]
            params = [user_id, transaction_type]
            param_idx = 3
            
            if start_date:
                conditions.append(f"t.transaction_date >= ${param_idx}")
                params.append(start_date)
                param_idx += 1
            
            if end_date:
                conditions.append(f"t.transaction_date <= ${param_idx}")
                params.append(end_date)
                param_idx += 1
            
            where_clause = " AND ".join(conditions)
            
            query = f"""
                SELECT
                    c.id as category_id,
                    c.name as category_name,
                    c.icon as category_icon,
                    COUNT(*) as transaction_count,
                    SUM(t.amount) as total_amount,
                    AVG(t.amount) as avg_amount
                FROM transactions t
                INNER JOIN categories c ON t.category_id = c.id
                WHERE {where_clause}
                GROUP BY c.id, c.name, c.icon
                ORDER BY total_amount DESC
            """
            
            rows = await self.conn.fetch(query, *params)
            
            return [
                {
                    'category_id': row['category_id'],
                    'category_name': row['category_name'],
                    'category_icon': row['category_icon'],
                    'count': row['transaction_count'],
                    'total': float(row['total_amount']),
                    'average': float(row['avg_amount'])
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Error getting category stats: {e}", exc_info=True)
            return []
    
    async def update(
        self,
        transaction_id: int,
        amount: Optional[float] = None,
        category_id: Optional[int] = None,
        description: Optional[str] = None,
        transaction_date: Optional[date] = None
    ) -> Optional[Transaction]:
        """
        Update transaction
        
        Args:
            transaction_id: Transaction ID
            amount: New amount
            category_id: New category ID
            description: New description
            transaction_date: New date
            
        Returns:
            Updated Transaction object or None
        """
        try:
            # Build dynamic update query
            updates = []
            params = [transaction_id]
            param_idx = 2
            
            if amount is not None:
                updates.append(f"amount = ${param_idx}")
                params.append(Decimal(str(amount)))
                param_idx += 1
            
            if category_id is not None:
                updates.append(f"category_id = ${param_idx}")
                params.append(category_id)
                param_idx += 1
            
            if description is not None:
                updates.append(f"description = ${param_idx}")
                params.append(description)
                param_idx += 1
            
            if transaction_date is not None:
                updates.append(f"transaction_date = ${param_idx}")
                params.append(transaction_date)
                param_idx += 1
            
            if not updates:
                logger.warning("No fields to update")
                return await self.get_by_id(transaction_id)
            
            updates.append("updated_at = NOW()")
            update_clause = ", ".join(updates)
            
            query = f"""
                UPDATE transactions
                SET {update_clause}
                WHERE id = $1
                RETURNING *
            """
            
            row = await self.conn.fetchrow(query, *params)
            
            if row:
                logger.info(f"Transaction updated: id={transaction_id}")
                return Transaction(**dict(row))
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating transaction: {e}", exc_info=True)
            return None
    
    async def delete(self, transaction_id: int) -> bool:
        """
        Delete transaction
        
        Args:
            transaction_id: Transaction ID
            
        Returns:
            True if deleted successfully
        """
        try:
            result = await self.conn.execute(
                "DELETE FROM transactions WHERE id = $1",
                transaction_id
            )
            
            deleted = result.split()[-1] == "1"
            if deleted:
                logger.info(f"Transaction deleted: id={transaction_id}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Error deleting transaction: {e}", exc_info=True)
            return False
    
    async def get_daily_totals(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        transaction_type: str = 'expense'
    ) -> List[Dict]:
        """
        Get daily totals for chart
        
        Args:
            user_id: User ID
            start_date: Start date
            end_date: End date
            transaction_type: 'income' or 'expense'
            
        Returns:
            List of dictionaries with date and total
        """
        try:
            rows = await self.conn.fetch(
                """
                SELECT
                    transaction_date as date,
                    SUM(amount) as total
                FROM transactions
                WHERE user_id = $1
                  AND type = $2
                  AND transaction_date BETWEEN $3 AND $4
                GROUP BY transaction_date
                ORDER BY transaction_date
                """,
                user_id, transaction_type, start_date, end_date
            )
            
            return [
                {
                    'date': row['date'].isoformat(),
                    'total': float(row['total'])
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Error getting daily totals: {e}", exc_info=True)
            return []
