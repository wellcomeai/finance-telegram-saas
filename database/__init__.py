"""
Database Module
Handles all database operations with PostgreSQL
"""

from .connection import get_db_connection, init_database, close_database
from .models import User, Transaction, Category, AgentConfig, AgentSession
from .repositories.user_repo import UserRepository
from .repositories.transaction_repo import TransactionRepository
from .repositories.category_repo import CategoryRepository

__version__ = "1.0.0"

__all__ = [
    "get_db_connection",
    "init_database",
    "close_database",
    "User",
    "Transaction",
    "Category",
    "AgentConfig",
    "AgentSession",
    "UserRepository",
    "TransactionRepository",
    "CategoryRepository"
]
