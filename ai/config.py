"""
AI module configuration
"""

from dataclasses import dataclass
from shared.config import settings


@dataclass
class AIConfig:
    """Configuration for AI services"""
    
    # OpenAI settings
    OPENAI_API_KEY: str = settings.OPENAI_API_KEY
    GPT_MODEL: str = "gpt-5"  # или "gpt-5-mini" для экономии
    MAX_TOKENS: int = 1000
    TEMPERATURE: float = 0.3  # Низкая температура для точности
    
    # Whisper settings for voice
    WHISPER_MODEL: str = "whisper-1"
    
    # Vision settings for images/PDF
    VISION_MODEL: str = "gpt-4o"  # Для обработки изображений
    VISION_MAX_TOKENS: int = 500
    
    # Timeouts
    TIMEOUT: int = 30  # seconds
    
    # Retry settings
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2  # seconds


ai_config = AIConfig()
