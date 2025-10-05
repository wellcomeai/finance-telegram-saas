"""
Database connection management
"""

import logging
from contextlib import asynccontextmanager
import asyncpg
from typing import Optional

from shared.config import settings

logger = logging.getLogger(__name__)

# Global connection pool
_pool: Optional[asyncpg.Pool] = None


async def init_database() -> None:
    """
    Initialize database connection pool
    """
    global _pool
    
    if _pool is not None:
        logger.warning("Database pool already initialized")
        return
    
    try:
        logger.info("Initializing database connection pool...")
        
        _pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60,
            max_queries=50000,
            max_inactive_connection_lifetime=300
        )
        
        logger.info("Database connection pool initialized successfully")
        
        # Test connection
        async with _pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            logger.info(f"Connected to PostgreSQL: {version}")
        
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}", exc_info=True)
        raise


async def close_database() -> None:
    """
    Close database connection pool
    """
    global _pool
    
    if _pool is None:
        logger.warning("Database pool is not initialized")
        return
    
    try:
        logger.info("Closing database connection pool...")
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")
        
    except Exception as e:
        logger.error(f"Error closing database pool: {e}", exc_info=True)


@asynccontextmanager
async def get_db_connection():
    """
    Get database connection from pool
    
    Usage:
        async with get_db_connection() as conn:
            result = await conn.fetch("SELECT * FROM users")
    """
    global _pool
    
    if _pool is None:
        await init_database()
    
    if _pool is None:
        raise RuntimeError("Database pool is not initialized")
    
    async with _pool.acquire() as connection:
        yield connection


async def execute_sql_file(file_path: str) -> None:
    """
    Execute SQL from file
    
    Args:
        file_path: Path to SQL file
    """
    try:
        logger.info(f"Executing SQL file: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        async with get_db_connection() as conn:
            await conn.execute(sql)
        
        logger.info(f"SQL file executed successfully: {file_path}")
        
    except Exception as e:
        logger.error(f"Error executing SQL file {file_path}: {e}", exc_info=True)
        raise


async def run_migrations() -> None:
    """
    Run all database migrations
    """
    try:
        logger.info("Running database migrations...")
        
        # Execute migration files in order
        migration_files = [
            "database/migrations/001_create_tables.sql",
            "database/migrations/002_seed_categories.sql"
        ]
        
        for migration_file in migration_files:
            await execute_sql_file(migration_file)
        
        logger.info("All migrations completed successfully")
        
    except Exception as e:
        logger.error(f"Error running migrations: {e}", exc_info=True)
        raise
