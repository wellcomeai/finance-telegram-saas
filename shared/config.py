"""
Application configuration from environment variables
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Settings:
    """Application settings"""
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_WEBAPP_URL: str = os.getenv("TELEGRAM_WEBAPP_URL", "https://finance-telegram-saas.onrender.com/webapp")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-5")
    
    # Application
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    
    # File storage (for temporary files)
    TEMP_DIR: str = os.getenv("TEMP_DIR", "/tmp/finance_bot")
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
    
    # Rate limiting
    MAX_TRANSACTIONS_PER_DAY: int = int(os.getenv("MAX_TRANSACTIONS_PER_DAY", "100"))
    MAX_AI_REQUESTS_PER_HOUR: int = int(os.getenv("MAX_AI_REQUESTS_PER_HOUR", "50"))
    
    # Timeouts
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    AI_TIMEOUT: int = int(os.getenv("AI_TIMEOUT", "30"))
    
    def validate(self) -> bool:
        """
        Validate required settings
        
        Returns:
            True if all required settings are present
        """
        required_fields = [
            ("TELEGRAM_BOT_TOKEN", self.TELEGRAM_BOT_TOKEN),
            ("DATABASE_URL", self.DATABASE_URL),
            ("OPENAI_API_KEY", self.OPENAI_API_KEY)
        ]
        
        missing = []
        for field_name, field_value in required_fields:
            if not field_value:
                missing.append(field_name)
        
        if missing:
            print(f"❌ Missing required environment variables: {', '.join(missing)}")
            return False
        
        return True
    
    def __post_init__(self):
        """Create temp directory if it doesn't exist"""
        import os
        os.makedirs(self.TEMP_DIR, exist_ok=True)


# Global settings instance
settings = Settings()


def validate_config() -> None:
    """
    Validate configuration and raise error if invalid
    """
    if not settings.validate():
        raise ValueError("Invalid configuration. Check environment variables.")
