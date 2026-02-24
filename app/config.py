"""Enhanced application configuration with enterprise security settings."""
import os
from functools import lru_cache
from typing import List


class Settings:
    """Application settings with security defaults."""
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:////home/thorium/Desktop/programming/2026/blockchain/voting.db")
    
    # JWT - Enterprise Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived access tokens
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    TOKEN_VERSION_ENABLED: bool = True  # Token invalidation
    
    # Security - Rate Limiting (Sliding Window)
    RATE_LIMIT_AUTH_PER_MINUTE: int = 5    # Login/register attempts
    RATE_LIMIT_VOTE_PER_MINUTE: int = 10   # Vote casting
    RATE_LIMIT_API_PER_MINUTE: int = 60     # General API
    RATE_LIMIT_ADMIN_PER_MINUTE: int = 30   # Admin endpoints
    
    # Security - Brute Force Protection
    MAX_LOGIN_ATTEMPTS: int = 10            # Before temp ban
    MAX_REGISTRATION_ATTEMPTS: int = 20     # Registration limits
    BAN_DURATION_MINUTES: int = 30          # Initial ban duration
    BAN_DURATION_MAX_MINUTES: int = 1440    # Max ban (24 hours)
    FAILED_ATTEMPTS_WINDOW_HOURS: int = 1   # Time window for counting failures
    
    # Security - IP Intelligence
    TRUST_PROXY_COUNT: int = 1              # X-Forwarded-For depth
    SUBNET_BAN_ENABLED: bool = True         # Ban /24 subnet on repeated offenses
    
    # Security - Anti-Replay
    VOTE_NONCE_EXPIRE_SECONDS: int = 300    # 5 minute window for nonce
    VOTE_TIMESTAMP_TOLERANCE_SECONDS: int = 60  # Reject votes older than 60s
    
    # Security - Zero Trust
    BIND_TOKEN_TO_IP: bool = True           # Bind JWT to original IP
    BIND_TOKEN_TO_DEVICE: bool = True       # Bind JWT to device fingerprint
    REQUIRE_DEVICE_FINGERPRINT: bool = True # Require device FP for auth
    
    # Security - API Protection
    MAX_REQUEST_SIZE_KB: int = 100          # Max request body size
    ALLOWED_ORIGINS: List[str] = os.getenv(
        "ALLOWED_ORIGINS", 
        "http://localhost:3000,http://localhost:8080"
    ).split(",")
    
    # Security - Headers
    ENABLE_HSTS: bool = True                 # HTTP Strict Transport Security
    HSTS_MAX_AGE_SECONDS: int = 31536000     # 1 year
    ENABLE_CSP: bool = True                  # Content Security Policy
    
    # Audit Logging
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_INCLUDE_BODY: bool = False     # Don't log request bodies by default
    AUDIT_LOG_RETENTION_DAYS: int = 90
    
    # Blockchain Security
    BLOCKCHAIN_CHECKPOINT_INTERVAL: int = 100  # Blocks between checkpoints
    MERKLE_TREE_ENABLED: bool = True          # Merkle root for vote verification
    ECDSA_STRICT_MODE: bool = True            # Require valid signatures
    
    # Admin Security
    ADMIN_IP_ALLOWLIST: List[str] = os.getenv(
        "ADMIN_IP_ALLOWLIST", 
        ""
    ).split(",") if os.getenv("ADMIN_IP_ALLOWLIST") else []
    ADMIN_REQUIRE_REAUTH_FOR_DESTRUCTIVE: bool = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
