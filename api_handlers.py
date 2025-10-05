"""
API Handlers for Web App
Handles HTTP requests from Telegram Mini App
"""

import logging
import json
from typing import Dict, Optional
from datetime import datetime, date, timedelta
from aiohttp import web
from decimal import Decimal

from database.connection import get_db_connection
from database.repositories.user_repo import UserRepository
from database.repositories.transaction_repo import TransactionRepository
from database.repositories.category_repo import CategoryRepository
from shared.utils import format_amount

logger = logging.getLogger(__name__)


# ==================== MIDDLEWARE ====================

@web.middleware
async def auth_middleware(request, handler):
    """
    Authentication middleware
    Validates Telegram user from headers
    """
    # Skip auth for health check
    if request.path == '/health':
        return await handler(request)
    
    # Only apply to /api/* routes
    if not request.path.startswith('/api/'):
        return await handler(request)
    
    try:
        # Get user ID from headers
        user_id = request.headers.get('X-Telegram-User-Id')
        
        if not user_id:
            return web.json_response(
                {'error': 'Unauthorized'},
                status=401
            )
        
        # Get or create user
        async with get_db_connection() as conn:
            user_repo = UserRepository(conn)
            user = await user_repo.get_by_telegram_id(int(user_id))
            
            if not user:
                # Create new user
                user = await user_repo.create(
                    telegram_user_id=int(user_id),
                    username=None,
                    first_name='User',
                    last_name=None
                )
        
        # Add user to request
        request['user'] = user
        
        # Call handler
        return await handler(request)
        
    except Exception as e:
        logger.error(f"Auth middleware error: {e}", exc_info=True)
        return web.json_response(
            {'error': 'Authentication failed'},
            status=401
        )


class APIHandler:
    """Handler for API requests from webapp"""
    
    # ==================== TRANSACTIONS ====================
    
    @staticmethod
    async def get_transactions(request):
        """
        GET /api/transactions
        Get user's transactions with filters
        """
        try:
            user = request['user']
            
            # Get query parameters
            limit = int(request.query.get('limit', 50))
            offset = int(request.query.get('offset', 0))
            transaction_type = request.query.get('type')
            category_id = request.query.get('category_id')
            start_date = request.query.get('start_date')
            end_date = request.query.get('end_date')
            
            # Parse dates
            start_date_obj = None
            end_date_obj = None
            
            if start_date:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            async with get_db_connection() as conn:
                transaction_repo = TransactionRepository(conn)
                
                transactions = await transaction_repo.get_user_transactions(
                    user_id=user.id,
                    limit=limit,
                    offset=offset,
                    transaction_type=transaction_type,
                    category_id=int(category_id) if category_id else None,
                    start_date=start_date_obj,
                    end_date=end_date_obj
                )
            
            # Format response
            result = []
            for t in transactions:
                result.append({
                    'id': t['id'],
                    'type': t['type'],
                    'amount': float(t['amount']),
                    'category_id': t['category_id'],
                    'category_name': t['category_name'],
                    'category_icon': t['category_icon'],
                    'description': t['description'],
                    'transaction_date': t['transaction_date'].isoformat() if t['transaction_date'] else None,
                    'created_at': t['created_at'].isoformat() if t['created_at'] else None
                })
            
            return web.json_response({
                'transactions': result,
                'count': len(result)
            })
            
        except Exception as e:
            logger.error(f"Get transactions error: {e}", exc_info=True)
            return web.json_response(
                {'error': str(e)},
                status=500
            )
    
    @staticmethod
    async def get_transaction(request):
        """
        GET /api/transactions/{id}
        Get single transaction
        """
        try:
            user = request['user']
            transaction_id = int(request.match_info['id'])
            
            async with get_db_connection() as conn:
                transaction_repo = TransactionRepository(conn)
                transaction = await transaction_repo.get_by_id(transaction_id)
                
                if not transaction or transaction.user_id != user.id:
                    return web.json_response(
                        {'error': 'Transaction not found'},
                        status=404
                    )
                
                # Get category
                category = None
                if transaction.category_id:
                    category_repo = CategoryRepository(conn)
                    category = await category_repo.get_by_id(transaction.category_id)
            
            return web.json_response({
                'id': transaction.id,
                'type': transaction.type,
                'amount': float(transaction.amount),
                'category_id': transaction.category_id,
                'category_name': category.name if category else None,
                'category_icon': category.icon if category else None,
                'description': transaction.description,
                'transaction_date': transaction.transaction_date.isoformat(),
                'created_at': transaction.created_at.isoformat()
            })
            
        except Exception as e:
            logger.error(f"Get transaction error: {e}", exc_info=True)
            return web.json_response(
                {'error': str(e)},
                status=500
            )
    
    @staticmethod
    async def create_transaction(request):
        """
        POST /api/transactions
        Create new transaction
        """
        try:
            user = request['user']
            data = await request.json()
            
            # Validate required fields
            if 'type' not in data or 'amount' not in data or 'category_id' not in data:
                return web.json_response(
                    {'error': 'Missing required fields'},
                    status=400
                )
            
            # Parse date
            transaction_date = date.today()
            if 'date' in data:
                transaction_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            
            async with get_db_connection() as conn:
                transaction_repo = TransactionRepository(conn)
                
                transaction = await transaction_repo.create(
                    user_id=user.id,
                    transaction_type=data['type'],
                    amount=float(data['amount']),
                    category_id=int(data['category_id']),
                    description=data.get('description'),
                    transaction_date=transaction_date
                )
                
                # Get category
                category = None
                if transaction.category_id:
                    category_repo = CategoryRepository(conn)
                    category = await category_repo.get_by_id(transaction.category_id)
            
            return web.json_response({
                'id': transaction.id,
                'type': transaction.type,
                'amount': float(transaction.amount),
                'category_id': transaction.category_id,
                'category_name': category.name if category else None,
                'category_icon': category.icon if category else None,
                'description': transaction.description,
                'transaction_date': transaction.transaction_date.isoformat(),
                'message': 'Transaction created successfully'
            }, status=201)
            
        except Exception as e:
            logger.error(f"Create transaction error: {e}", exc_info=True)
            return web.json_response(
                {'error': str(e)},
                status=500
            )
    
    @staticmethod
    async def update_transaction(request):
        """
        PUT /api/transactions/{id}
        Update transaction
        """
        try:
            user = request['user']
            transaction_id = int(request.match_info['id'])
            data = await request.json()
            
            async with get_db_connection() as conn:
                transaction_repo = TransactionRepository(conn)
                
                # Check if transaction exists and belongs to user
                existing = await transaction_repo.get_by_id(transaction_id)
                if not existing or existing.user_id != user.id:
                    return web.json_response(
                        {'error': 'Transaction not found'},
                        status=404
                    )
                
                # Parse date if provided
                transaction_date = None
                if 'date' in data:
                    transaction_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
                
                # Update transaction
                transaction = await transaction_repo.update(
                    transaction_id=transaction_id,
                    amount=float(data['amount']) if 'amount' in data else None,
                    category_id=int(data['category_id']) if 'category_id' in data else None,
                    description=data.get('description'),
                    transaction_date=transaction_date
                )
                
                # Get category
                category = None
                if transaction.category_id:
                    category_repo = CategoryRepository(conn)
                    category = await category_repo.get_by_id(transaction.category_id)
            
            return web.json_response({
                'id': transaction.id,
                'type': transaction.type,
                'amount': float(transaction.amount),
                'category_id': transaction.category_id,
                'category_name': category.name if category else None,
                'category_icon': category.icon if category else None,
                'description': transaction.description,
                'transaction_date': transaction.transaction_date.isoformat(),
                'message': 'Transaction updated successfully'
            })
            
        except Exception as e:
            logger.error(f"Update transaction error: {e}", exc_info=True)
            return web.json_response(
                {'error': str(e)},
                status=500
            )
    
    @staticmethod
    async def delete_transaction(request):
        """
        DELETE /api/transactions/{id}
        Delete transaction
        """
        try:
            user = request['user']
            transaction_id = int(request.match_info['id'])
            
            async with get_db_connection() as conn:
                transaction_repo = TransactionRepository(conn)
                
                # Check if transaction exists and belongs to user
                existing = await transaction_repo.get_by_id(transaction_id)
                if not existing or existing.user_id != user.id:
                    return web.json_response(
                        {'error': 'Transaction not found'},
                        status=404
                    )
                
                # Delete transaction
                deleted = await transaction_repo.delete(transaction_id)
                
                if not deleted:
                    return web.json_response(
                        {'error': 'Failed to delete transaction'},
                        status=500
                    )
            
            return web.json_response({
                'message': 'Transaction deleted successfully'
            })
            
        except Exception as e:
            logger.error(f"Delete transaction error: {e}", exc_info=True)
            return web.json_response(
                {'error': str(e)},
                status=500
            )
    
    # ==================== STATISTICS ====================
    
    @staticmethod
    async def get_monthly_stats(request):
        """
        GET /api/stats/monthly
        Get monthly statistics
        """
        try:
            user = request['user']
            
            # Get year and month from query params
            now = datetime.now()
            year = int(request.query.get('year', now.year))
            month = int(request.query.get('month', now.month))
            
            async with get_db_connection() as conn:
                transaction_repo = TransactionRepository(conn)
                stats = await transaction_repo.get_monthly_stats(
                    user_id=user.id,
                    year=year,
                    month=month
                )
            
            return web.json_response(stats)
            
        except Exception as e:
            logger.error(f"Get monthly stats error: {e}", exc_info=True)
            return web.json_response(
                {'error': str(e)},
                status=500
            )
    
    @staticmethod
    async def get_category_stats(request):
        """
        GET /api/stats/categories
        Get statistics by category
        """
        try:
            user = request['user']
            
            # Get query parameters
            start_date = request.query.get('start_date')
            end_date = request.query.get('end_date')
            transaction_type = request.query.get('type', 'expense')
            
            # Parse dates
            start_date_obj = None
            end_date_obj = None
            
            if start_date:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            async with get_db_connection() as conn:
                transaction_repo = TransactionRepository(conn)
                stats = await transaction_repo.get_category_stats(
                    user_id=user.id,
                    start_date=start_date_obj,
                    end_date=end_date_obj,
                    transaction_type=transaction_type
                )
            
            return web.json_response(stats)
            
        except Exception as e:
            logger.error(f"Get category stats error: {e}", exc_info=True)
            return web.json_response(
                {'error': str(e)},
                status=500
            )
    
    @staticmethod
    async def get_daily_totals(request):
        """
        GET /api/stats/daily
        Get daily totals for chart
        """
        try:
            user = request['user']
            
            # Get query parameters
            start_date = request.query.get('start_date')
            end_date = request.query.get('end_date')
            transaction_type = request.query.get('type', 'expense')
            
            # Parse dates
            if not start_date or not end_date:
                # Default to current month
                now = datetime.now()
                start_date_obj = date(now.year, now.month, 1)
                end_date_obj = now.date()
            else:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            async with get_db_connection() as conn:
                transaction_repo = TransactionRepository(conn)
                totals = await transaction_repo.get_daily_totals(
                    user_id=user.id,
                    start_date=start_date_obj,
                    end_date=end_date_obj,
                    transaction_type=transaction_type
                )
            
            return web.json_response(totals)
            
        except Exception as e:
            logger.error(f"Get daily totals error: {e}", exc_info=True)
            return web.json_response(
                {'error': str(e)},
                status=500
            )
    
    @staticmethod
    async def get_dashboard_summary(request):
        """
        GET /api/stats/dashboard
        Get dashboard summary
        """
        try:
            user = request['user']
            
            # Get current month dates
            now = datetime.now()
            start_date = date(now.year, now.month, 1)
            end_date = now.date()
            
            async with get_db_connection() as conn:
                transaction_repo = TransactionRepository(conn)
                
                # Get monthly stats
                monthly_stats = await transaction_repo.get_monthly_stats(
                    user_id=user.id,
                    year=now.year,
                    month=now.month
                )
                
                # Get category stats
                category_stats = await transaction_repo.get_category_stats(
                    user_id=user.id,
                    start_date=start_date,
                    end_date=end_date,
                    transaction_type='expense'
                )
            
            # Find top category
            top_category = '—'
            if category_stats:
                top_category = category_stats[0]['category_name']
            
            return web.json_response({
                'income': monthly_stats['income'],
                'expenses': monthly_stats['expenses'],
                'balance': monthly_stats['balance'],
                'count': monthly_stats['count'],
                'top_category': top_category,
                'category_stats': category_stats[:5]  # Top 5
            })
            
        except Exception as e:
            logger.error(f"Get dashboard summary error: {e}", exc_info=True)
            return web.json_response(
                {'error': str(e)},
                status=500
            )
    
    # ==================== CATEGORIES ====================
    
    @staticmethod
    async def get_categories(request):
        """
        GET /api/categories
        Get all categories
        """
        try:
            # Get query parameters
            category_type = request.query.get('type')
            
            async with get_db_connection() as conn:
                category_repo = CategoryRepository(conn)
                
                if category_type:
                    categories = await category_repo.get_all(category_type=category_type)
                else:
                    categories = await category_repo.get_all()
            
            # Format response
            result = []
            for cat in categories:
                result.append({
                    'id': cat.id,
                    'name': cat.name,
                    'icon': cat.icon,
                    'type': cat.type,
                    'is_active': cat.is_active
                })
            
            return web.json_response({
                'categories': result
            })
            
        except Exception as e:
            logger.error(f"Get categories error: {e}", exc_info=True)
            return web.json_response(
                {'error': str(e)},
                status=500
            )
    
    # ==================== USER ====================
    
    @staticmethod
    async def get_user_info(request):
        """
        GET /api/user
        Get current user info
        """
        try:
            user = request['user']
            
            return web.json_response({
                'id': user.id,
                'telegram_user_id': user.telegram_user_id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.full_name,
                'created_at': user.created_at.isoformat()
            })
            
        except Exception as e:
            logger.error(f"Get user info error: {e}", exc_info=True)
            return web.json_response(
                {'error': str(e)},
                status=500
            )
    
    # ==================== AI CHAT ====================
    
    @staticmethod
    async def chat_with_ai(request):
        """
        POST /api/ai/chat
        Send message to AI assistant
        """
        try:
            user = request['user']
            data = await request.json()
            
            message = data.get('message', '').strip()
            new_conversation = data.get('new_conversation', False)
            
            if not message:
                return web.json_response(
                    {'error': 'Message is required'},
                    status=400
                )
            
            # Get all user transactions for context
            async with get_db_connection() as conn:
                transaction_repo = TransactionRepository(conn)
                transactions = await transaction_repo.get_user_transactions(
                    user_id=user.id,
                    limit=1000  # All transactions
                )
            
            # Format transactions for AI context
            context = "Информация о транзакциях пользователя:\n"
            
            if transactions:
                total_income = 0
                total_expense = 0
                
                for t in transactions:
                    amount = float(t['amount'])
                    type_emoji = "💰" if t['type'] == 'income' else "💸"
                    
                    context += f"{type_emoji} {t['transaction_date']}: {amount} ₽ - {t['category_name']}"
                    if t['description']:
                        context += f" ({t['description']})"
                    context += "\n"
                    
                    if t['type'] == 'income':
                        total_income += amount
                    else:
                        total_expense += amount
                
                balance = total_income - total_expense
                context += f"\nИтого: доходы {total_income} ₽, расходы {total_expense} ₽, баланс {balance} ₽"
            else:
                context = "У пользователя пока нет транзакций."
            
            # Add context to message on first message
            if new_conversation and transactions:
                message = f"{context}\n\nВопрос пользователя: {message}"
            
            # Chat with AI agent
            from ai.agent import chat_with_agent
            response = await chat_with_agent(
                user_id=user.id,
                message=message,
                new_conversation=new_conversation
            )
            
            if not response:
                return web.json_response(
                    {'error': 'AI не смог обработать запрос'},
                    status=500
                )
            
            return web.json_response({
                'response': response,
                'success': True
            })
            
        except Exception as e:
            logger.error(f"AI chat error: {e}", exc_info=True)
            return web.json_response(
                {'error': str(e)},
                status=500
            )
    
    @staticmethod
    async def reset_ai_chat(request):
        """
        POST /api/ai/reset
        Reset AI conversation
        """
        try:
            user = request['user']
            
            from ai.agent import reset_agent_conversation
            success = await reset_agent_conversation(user.id)
            
            if success:
                return web.json_response({
                    'message': 'Чат сброшен',
                    'success': True
                })
            else:
                return web.json_response(
                    {'error': 'Не удалось сбросить чат'},
                    status=500
                )
            
        except Exception as e:
            logger.error(f"Reset AI chat error: {e}", exc_info=True)
            return web.json_response(
                {'error': str(e)},
                status=500
            )


def setup_api_routes(app):
    """
    Setup API routes
    """
    # Add auth middleware to app
    app.middlewares.append(auth_middleware)
    
    # Transactions
    app.router.add_get('/api/transactions', APIHandler.get_transactions)
    app.router.add_get('/api/transactions/{id}', APIHandler.get_transaction)
    app.router.add_post('/api/transactions', APIHandler.create_transaction)
    app.router.add_put('/api/transactions/{id}', APIHandler.update_transaction)
    app.router.add_delete('/api/transactions/{id}', APIHandler.delete_transaction)
    
    # Statistics
    app.router.add_get('/api/stats/monthly', APIHandler.get_monthly_stats)
    app.router.add_get('/api/stats/categories', APIHandler.get_category_stats)
    app.router.add_get('/api/stats/daily', APIHandler.get_daily_totals)
    app.router.add_get('/api/stats/dashboard', APIHandler.get_dashboard_summary)
    
    # Categories
    app.router.add_get('/api/categories', APIHandler.get_categories)
    
    # User
    app.router.add_get('/api/user', APIHandler.get_user_info)
    
    # AI Chat
    app.router.add_post('/api/ai/chat', APIHandler.chat_with_ai)
    app.router.add_post('/api/ai/reset', APIHandler.reset_ai_chat)
    
    logger.info("API routes configured")
