"""
AI Agent with conversation context using OpenAI Responses API
Simplified version - no message history stored
"""

import logging
from typing import Optional, Dict
import httpx

from ai.config import ai_config
from database.connection import get_db_connection

logger = logging.getLogger(__name__)


class AIAgent:
    """
    AI Agent с контекстом диалога через OpenAI Responses API
    Хранит только response_id для продолжения разговора
    """
    
    def __init__(self):
        self.default_model = "gpt-4o"
        self.api_url = "https://api.openai.com/v1/responses"
    
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
                    "SELECT response_id FROM agent_sessions WHERE user_id = $1",
                    user_id
                )
                
                return row['response_id'] if row else None
                
        except Exception as e:
            logger.error(f"Error getting last response_id: {e}", exc_info=True)
            return None
    
    async def _save_response_id(self, user_id: int, response_id: str) -> bool:
        """
        Сохранить response_id для пользователя
        
        Args:
            user_id: ID пользователя
            response_id: OpenAI response ID
            
        Returns:
            True если успешно
        """
        try:
            async with get_db_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO agent_sessions (user_id, response_id)
                    VALUES ($1, $2)
                    ON CONFLICT (user_id) DO UPDATE SET 
                        response_id = $2, 
                        updated_at = NOW()
                    """,
                    user_id, response_id
                )
                
                logger.info(f"Response ID saved: user_id={user_id}, response_id={response_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving response_id: {e}", exc_info=True)
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
            
            logger.info(f"Agent chat: user_id={user_id}, msg_len={len(message)}, new={new_conversation}")
            
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
                "store": True
            }
            
            # Добавить инструкции только для новой сессии
            if not previous_response_id:
                request_data["instructions"] = system_prompt
                logger.info("Starting new conversation with system prompt")
            else:
                request_data["previous_response_id"] = previous_response_id
                logger.info(f"Continuing conversation: prev_id={previous_response_id[:20]}...")
            
            # HTTP запрос к OpenAI Responses API
            headers = {
                "Authorization": f"Bearer {ai_config.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    json=request_data,
                    headers=headers
                )
                
                # Проверка статуса
                if response.status_code != 200:
                    logger.error(f"API error: status={response.status_code}, body={response.text}")
                    return "Извините, сервис временно недоступен."
                
                response_data = response.json()
            
            # Извлечь данные из ответа
            response_id = response_data.get('id')
            
            if not response_id:
                logger.error("No response_id in API response")
                return None
            
            # Получить текст ответа
            output = response_data.get('output', [])
            assistant_message = None
            
            if output and len(output) > 0:
                content = output[0].get('content', [])
                if content and len(content) > 0:
                    assistant_message = content[0].get('text', '')
            
            # Альтернатива: output_text
            if not assistant_message:
                assistant_message = response_data.get('output_text', '')
            
            if not assistant_message:
                logger.error("No assistant message in response")
                return None
            
            logger.info(f"Agent response OK: response_id={response_id[:20]}..., len={len(assistant_message)}")
            
            # Сохранить response_id для следующего запроса
            await self._save_response_id(user_id, response_id)
            
            return assistant_message
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error in agent chat: {e}", exc_info=True)
            return "Извините, произошла ошибка соединения."
        except Exception as e:
            logger.error(f"Error in agent chat: {e}", exc_info=True)
            return "Извините, произошла ошибка при обработке вашего запроса."
    
    async def reset_conversation(self, user_id: int) -> bool:
        """
        Сбросить разговор (удалить response_id)
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если успешно
        """
        try:
            async with get_db_connection() as conn:
                result = await conn.execute(
                    "DELETE FROM agent_sessions WHERE user_id = $1",
                    user_id
                )
                
                logger.info(f"Conversation reset for user_id={user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error resetting conversation: {e}", exc_info=True)
            return False


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
