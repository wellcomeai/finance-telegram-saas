"""
AI Agent with conversation context using OpenAI Responses API
"""

import logging
from typing import Optional, Dict, List
from openai import AsyncOpenAI
from datetime import datetime

from ai.config import ai_config
from database.connection import get_db_connection

logger = logging.getLogger(__name__)


class AIAgent:
    """
    AI Agent с контекстом диалога через OpenAI Responses API
    """
    
    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self.default_model = "gpt-4o"
    
    async def _get_system_prompt(self, config_key: str = 'default') -> Optional[Dict]:
        """
        Загрузить системный промпт из БД
        
        Args:
            config_key: Ключ конфигурации
            
        Returns:
            Dict с system_prompt и model или None
        """
        try:
            async with get_db_connection() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT system_prompt, model
                    FROM agent_config
                    WHERE config_key = $1 AND is_active = true
                    """,
                    config_key
                )
                
                if row:
                    return {
                        'system_prompt': row['system_prompt'],
                        'model': row['model'] or self.default_model
                    }
                
                logger.warning(f"Agent config not found: {config_key}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading system prompt: {e}", exc_info=True)
            return None
    
    async def _get_last_response_id(self, user_id: int) -> Optional[str]:
        """
        Получить последний response_id для пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            response_id или None
        """
        try:
            async with get_db_connection() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT response_id
                    FROM agent_conversations
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    user_id
                )
                
                return row['response_id'] if row else None
                
        except Exception as e:
            logger.error(f"Error getting last response_id: {e}", exc_info=True)
            return None
    
    async def _save_conversation(
        self,
        user_id: int,
        response_id: str,
        user_message: str,
        assistant_message: str
    ) -> bool:
        """
        Сохранить разговор в БД
        
        Args:
            user_id: ID пользователя
            response_id: OpenAI response ID
            user_message: Сообщение пользователя
            assistant_message: Ответ ассистента
            
        Returns:
            True если успешно
        """
        try:
            async with get_db_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO agent_conversations 
                    (user_id, response_id, user_message, assistant_message)
                    VALUES ($1, $2, $3, $4)
                    """,
                    user_id, response_id, user_message, assistant_message
                )
                
                logger.info(f"Conversation saved: user_id={user_id}, response_id={response_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving conversation: {e}", exc_info=True)
            return False
    
    async def chat(
        self,
        user_id: int,
        message: str,
        new_conversation: bool = False
    ) -> Optional[str]:
        """
        Отправить сообщение агенту и получить ответ
        
        Args:
            user_id: ID пользователя
            message: Сообщение пользователя
            new_conversation: Начать новый разговор (игнорировать контекст)
            
        Returns:
            Ответ ассистента или None
        """
        try:
            # Валидация
            if not message or len(message.strip()) < 1:
                logger.warning("Empty message provided")
                return None
            
            logger.info(f"Agent chat request: user_id={user_id}, message_length={len(message)}")
            
            # Загрузить конфигурацию
            config = await self._get_system_prompt()
            if not config:
                logger.error("Failed to load agent configuration")
                return "Извините, произошла ошибка. Попробуйте позже."
            
            system_prompt = config['system_prompt']
            model = config['model']
            
            # Получить предыдущий response_id для контекста
            previous_response_id = None
            if not new_conversation:
                previous_response_id = await self._get_last_response_id(user_id)
            
            # Подготовить запрос к Responses API
            request_data = {
                "model": model,
                "input": message,
                "store": True  # Сохранить для последующего использования
            }
            
            # Добавить инструкции только для новой сессии
            if not previous_response_id:
                request_data["instructions"] = system_prompt
                logger.info("Starting new conversation with system prompt")
            else:
                request_data["previous_response_id"] = previous_response_id
                logger.info(f"Continuing conversation: previous_id={previous_response_id}")
            
            # Вызов OpenAI Responses API
            async with AsyncOpenAI(api_key=ai_config.OPENAI_API_KEY) as client:
                response = await client.post(
                    "/v1/responses",
                    json=request_data
                )
            
            # Извлечь данные из ответа
            response_data = response.json()
            response_id = response_data.get('id')
            
            # Получить текст ответа
            output = response_data.get('output', [])
            assistant_message = None
            
            if output and len(output) > 0:
                content = output[0].get('content', [])
                if content and len(content) > 0:
                    assistant_message = content[0].get('text', '')
            
            # Также можно использовать output_text если доступен
            if not assistant_message:
                assistant_message = response_data.get('output_text', '')
            
            if not assistant_message:
                logger.error("No assistant message in response")
                return None
            
            logger.info(f"Agent response received: response_id={response_id}, length={len(assistant_message)}")
            
            # Сохранить в БД
            await self._save_conversation(
                user_id=user_id,
                response_id=response_id,
                user_message=message,
                assistant_message=assistant_message
            )
            
            return assistant_message
            
        except Exception as e:
            logger.error(f"Error in agent chat: {e}", exc_info=True)
            return "Извините, произошла ошибка при обработке вашего запроса."
    
    async def reset_conversation(self, user_id: int) -> bool:
        """
        Сбросить историю разговора для пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если успешно
        """
        try:
            async with get_db_connection() as conn:
                result = await conn.execute(
                    "DELETE FROM agent_conversations WHERE user_id = $1",
                    user_id
                )
                
                logger.info(f"Conversation reset for user_id={user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error resetting conversation: {e}", exc_info=True)
            return False
    
    async def get_conversation_history(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """
        Получить историю разговора
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество сообщений
            
        Returns:
            Список словарей с историей
        """
        try:
            async with get_db_connection() as conn:
                rows = await conn.fetch(
                    """
                    SELECT 
                        user_message,
                        assistant_message,
                        created_at
                    FROM agent_conversations
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                    """,
                    user_id, limit
                )
                
                history = []
                for row in reversed(rows):  # Обратный порядок для хронологии
                    history.append({
                        'user': row['user_message'],
                        'assistant': row['assistant_message'],
                        'timestamp': row['created_at'].isoformat()
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}", exc_info=True)
            return []


# Глобальный экземпляр агента
agent = AIAgent()


# ==================== ПУБЛИЧНЫЕ ФУНКЦИИ ====================

async def chat_with_agent(
    user_id: int,
    message: str,
    new_conversation: bool = False
) -> Optional[str]:
    """
    Публичная функция для общения с агентом
    
    Args:
        user_id: ID пользователя
        message: Сообщение
        new_conversation: Начать новый разговор
        
    Returns:
        Ответ агента
    """
    return await agent.chat(user_id, message, new_conversation)


async def reset_agent_conversation(user_id: int) -> bool:
    """
    Сбросить разговор с агентом
    
    Args:
        user_id: ID пользователя
        
    Returns:
        True если успешно
    """
    return await agent.reset_conversation(user_id)


async def get_agent_history(user_id: int, limit: int = 10) -> List[Dict]:
    """
    Получить историю разговора с агентом
    
    Args:
        user_id: ID пользователя
        limit: Количество сообщений
        
    Returns:
        История разговора
    """
    return await agent.get_conversation_history(user_id, limit)
