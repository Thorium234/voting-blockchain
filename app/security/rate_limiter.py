"""Rate limiting for brute force protection."""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models import LoginAttempt, IPBlacklist
from app.config import get_settings

settings = get_settings()


def check_rate_limit(db: Session, ip_address: str, attempt_type: str = "login") -> bool:
    """Check if IP has exceeded rate limit."""
    # Get recent attempts
    cutoff = datetime.utcnow() - timedelta(minutes=1)
    recent_attempts = db.query(LoginAttempt).filter(
        LoginAttempt.ip_address == ip_address,
        LoginAttempt.timestamp >= cutoff
    ).count()
    
    return recent_attempts < settings.RATE_LIMIT_PER_MINUTE


def get_rate_limit_status(db: Session, ip_address: str) -> dict:
    """Get current rate limit status for an IP."""
    cutoff = datetime.utcnow() - timedelta(minutes=1)
    attempts = db.query(LoginAttempt).filter(
        LoginAttempt.ip_address == ip_address,
        LoginAttempt.timestamp >= cutoff
    ).count()
    
    remaining = max(0, settings.RATE_LIMIT_PER_MINUTE - attempts)
    
    return {
        "allowed": attempts < settings.RATE_LIMIT_PER_MINUTE,
        "attempts": attempts,
        "limit": settings.RATE_LIMIT_PER_MINUTE,
        "remaining": remaining,
        "reset_in_seconds": 60
    }


def record_failed_attempt(db: Session, ip_address: str, email: Optional[str] = None):
    """Record a failed login attempt and check for ban."""
    # Create attempt record
    attempt = LoginAttempt(
        ip_address=ip_address,
        email=email,
        success=False
    )
    db.add(attempt)
    db.commit()
    
    # Check if we should ban
    check_and_ban_ip(db, ip_address)


def check_and_ban_ip(db: Session, ip_address: str):
    """Check failed attempts and ban if threshold exceeded."""
    # Count failed attempts in last hour
    cutoff = datetime.utcnow() - timedelta(hours=1)
    failed_count = db.query(LoginAttempt).filter(
        LoginAttempt.ip_address == ip_address,
        LoginAttempt.success == False,
        LoginAttempt.timestamp >= cutoff
    ).count()
    
    if failed_count >= settings.MAX_LOGIN_ATTEMPTS:
        # Ban the IP
        ban_until = datetime.utcnow() + timedelta(minutes=settings.BAN_DURATION_MINUTES)
        
        existing_ban = db.query(IPBlacklist).filter(
            IPBlacklist.ip_address == ip_address
        ).first()
        
        if existing_ban:
            existing_ban.banned_until = ban_until
            existing_ban.failed_attempts = failed_count
            existing_ban.reason = "Exceeded maximum login attempts"
        else:
            ban = IPBlacklist(
                ip_address=ip_address,
                banned_until=ban_until,
                reason="Exceeded maximum login attempts",
                failed_attempts=failed_count
            )
            db.add(ban)
        
        db.commit()


def clear_old_attempts(db: Session, days: int = 30):
    """Clean up old login attempts."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    db.query(LoginAttempt).filter(
        LoginAttempt.timestamp < cutoff
    ).delete()
    db.commit()
