"""Application configuration."""
import os
from functools import lru_cache


class Settings:
    """Application settings."""
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./voting.db")
    
    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Security
    MAX_LOGIN_ATTEMPTS: int = 10
    BAN_DURATION_MINUTES: int = 30
    RATE_LIMIT_PER_MINUTE: int = 5


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
