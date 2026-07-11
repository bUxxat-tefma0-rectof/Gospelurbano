# core/config/settings.py
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class Settings:
    """Configurações globais do sistema"""
    
    # Bot Tokens
    PUBLIC_BOT_TOKEN: str = os.getenv("PUBLIC_BOT_TOKEN", "")
    ADMIN_BOT_TOKEN: str = os.getenv("ADMIN_BOT_TOKEN", "")
    ADMIN_TELEGRAM_ID: int = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Mercado Pago
    MERCADO_PAGO_PUBLIC_KEY: str = os.getenv("MERCADO_PAGO_PUBLIC_KEY", "")
    MERCADO_PAGO_ACCESS_TOKEN: str = os.getenv("MERCADO_PAGO_ACCESS_TOKEN", "")
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # App
    APP_ENV: str = os.getenv("APP_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Cache
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", None)
    
    # Webhook
    WEBHOOK_URL: Optional[str] = os.getenv("WEBHOOK_URL", None)
    
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"
    
    @property
    def database_pool_size(self) -> int:
        return 20 if self.is_production else 5
    
    class Config:
        case_sensitive = True

settings = Settings()
