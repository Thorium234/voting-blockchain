"""
Advanced Rate Limiting with Sliding Window Algorithm.

Provides per-IP, per-user, and per-endpoint rate limiting with:
- Sliding window algorithm for smooth rate limiting
- Separate limits for different endpoint categories
- Token bucket algorithm for burst handling
- Fail-closed security model
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session
import hashlib
import threading

from app.models import LoginAttempt, IPBlacklist
from app.config import get_settings

settings = get_settings()

# In-memory sliding window storage (production: use Redis)
class SlidingWindowRateLimiter:
    """Thread-safe sliding window rate limiter."""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()
    
    def _cleanup_old_requests(self, key: str, now: datetime) -> None:
        """Remove requests outside the sliding window."""
        cutoff = now - timedelta(seconds=self.window_seconds)
        self._requests[key] = [
            ts for ts in self._requests[key] 
            if ts > cutoff
        ]
    
    def is_allowed(self, key: str) -> Tuple[bool, int, int]:
        """
        Check if request is allowed under rate limit.
        
        Returns:
            (allowed: bool, current_count: int, remaining: int)
        """
        now = datetime.utcnow()
        
        with self._lock:
            self._cleanup_old_requests(key, now)
            
            current_count = len(self._requests[key])
            remaining = max(0, self.max_requests - current_count)
            
            if current_count >= self.max_requests:
                return False, current_count, remaining
            
            # Record this request
            self._requests[key].append(now)
            return True, current_count + 1, remaining - 1
    
    def get_status(self, key: str) -> Dict:
        """Get current rate limit status."""
        now = datetime.utcnow()
        
        with self._lock:
            self._cleanup_old_requests(key, now)
            
            current_count = len(self._requests[key])
            return {
                "allowed": current_count < self.max_requests,
                "current": current_count,
                "limit": self.max_requests,
                "remaining": max(0, self.max_requests - current_count),
                "reset_in_seconds": self.window_seconds
            }


# Pre-configured limiters for different endpoint categories
_auth_limiter = SlidingWindowRateLimiter(
    settings.RATE_LIMIT_AUTH_PER_MINUTE, 60
)
_vote_limiter = SlidingWindowRateLimiter(
    settings.RATE_LIMIT_VOTE_PER_MINUTE, 60
)
_api_limiter = SlidingWindowRateLimiter(
    settings.RATE_LIMIT_API_PER_MINUTE, 60
)
_admin_limiter = SlidingWindowRateLimiter(
    settings.RATE_LIMIT_ADMIN_PER_MINUTE, 60
)


# Burst protection with token bucket
class TokenBucket:
    """Token bucket for burst handling."""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
        self._tokens = capacity
        self._last_refill = datetime.utcnow()
        self._lock = threading.Lock()
    
    @property
    def _tokens(self):
        return self.__tokens
    
    @_tokens.setter
    def _tokens(self, value):
        """Ensure tokens never exceed capacity."""
        self.__tokens = min(value, self.capacity) if value is not None else self.capacity
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens."""
        now = datetime.utcnow()
        
        with self._lock:
            # Refill tokens based on elapsed time
            elapsed = (now - self._last_refill).total_seconds()
            self._tokens = min(
                self.capacity,
                self._tokens + elapsed * self.refill_rate
            )
            self._last_refill = now
            
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False


# Auth burst protection
_auth_burst = TokenBucket(10, 0.5)  # 10 initial, refill 0.5/sec


def check_rate_limit(
    db: Session,
    ip_address: str,
    endpoint_type: str = "auth",
    user_id: Optional[int] = None
) -> Tuple[bool, Dict]:
    """
    Check if request is allowed under rate limits.
    
    Uses multiple signals:
    - IP-based limiting
    - User-based limiting (if authenticated)
    - Combined key for defense in depth
    
    Args:
        db: Database session
        ip_address: Client IP
        endpoint_type: Type of endpoint (auth, vote, api, admin)
        user_id: Authenticated user ID (optional)
    
    Returns:
        (allowed: bool, details: dict)
    """
    # Select appropriate limiter
    limiter_map = {
        "auth": _auth_limiter,
        "vote": _vote_limiter,
        "api": _api_limiter,
        "admin": _admin_limiter
    }
    limiter = limiter_map.get(endpoint_type, _api_limiter)
    
    # IP-based limiting (primary)
    ip_key = f"ip:{ip_address}"
    ip_allowed, ip_count, ip_remaining = limiter.is_allowed(ip_key)
    
    # User-based limiting (secondary, if available)
    user_allowed, user_count, user_remaining = True, 0, 999
    if user_id:
        user_key = f"user:{user_id}"
        user_allowed, user_count, user_remaining = limiter.is_allowed(user_key)
    
    # Combined decision
    allowed = ip_allowed and user_allowed
    
    # Get ban status from database
    ban_status = _check_db_ban(db, ip_address)
    if ban_status["is_banned"]:
        return False, {
            "reason": "ip_banned",
            "banned_until": ban_status["banned_until"],
            "reason_text": ban_status["reason"]
        }
    
    details = {
        "ip_current": ip_count,
        "ip_remaining": ip_remaining,
        "user_current": user_count,
        "user_remaining": user_remaining,
        "endpoint_type": endpoint_type
    }
    
    if not allowed:
        details["reason"] = "rate_limit_exceeded"
        # Trigger progressive penalty
        _record_rate_limit_violation(db, ip_address, endpoint_type)
    
    return allowed, details


def _check_db_ban(db: Session, ip_address: str) -> Dict:
    """Check if IP is banned in database."""
    ban = db.query(IPBlacklist).filter(
        IPBlacklist.ip_address == ip_address
    ).first()
    
    if not ban:
        return {"is_banned": False}
    
    if ban.banned_until < datetime.utcnow():
        # Ban expired, remove it
        db.delete(ban)
        db.commit()
        return {"is_banned": False}
    
    return {
        "is_banned": True,
        "banned_until": ban.banned_until.isoformat(),
        "reason": ban.reason,
        "failed_attempts": ban.failed_attempts
    }


def _record_rate_limit_violation(
    db: Session, 
    ip_address: str, 
    endpoint_type: str
) -> None:
    """Record rate limit violation for progressive penalties."""
    # This is called when rate limit is exceeded
    # Creates a record that contributes to IP banning
    attempt = LoginAttempt(
        ip_address=ip_address,
        success=False,
        details=f"rate_limit_exceeded:{endpoint_type}"
    )
    db.add(attempt)
    db.commit()
    
    # Check if we should escalate ban
    check_and_ban_ip(db, ip_address)


def get_rate_limit_status(
    ip_address: str,
    endpoint_type: str = "auth"
) -> Dict:
    """Get current rate limit status for an IP."""
    limiter_map = {
        "auth": _auth_limiter,
        "vote": _vote_limiter,
        "api": _api_limiter,
        "admin": _admin_limiter
    }
    limiter = limiter_map.get(endpoint_type, _api_limiter)
    
    return {
        "ip": limiter.get_status(f"ip:{ip_address}"),
        "endpoint_type": endpoint_type
    }


def record_failed_attempt(
    db: Session,
    ip_address: str,
    email: Optional[str] = None,
    attempt_type: str = "login"
) -> None:
    """Record a failed login attempt."""
    attempt = LoginAttempt(
        ip_address=ip_address,
        email=email,
        success=False,
        attempt_type=attempt_type
    )
    db.add(attempt)
    db.commit()
    
    # Check if we should ban
    check_and_ban_ip(db, ip_address)


def check_and_ban_ip(db: Session, ip_address: str) -> None:
    """
    Progressive penalty system for IP banning (optimized).
    
    Penalty levels:
    - Soft throttle: >5 failed attempts in window
    - Temporary ban: >10 failed attempts (30 min)
    - Extended ban: >20 failed attempts (2 hours)
    - Long ban: >50 failed attempts (24 hours)
    """
    from sqlalchemy import func
    
    # Count failed attempts in window (optimized with index)
    cutoff = datetime.utcnow() - timedelta(
        hours=settings.FAILED_ATTEMPTS_WINDOW_HOURS
    )
    
    failed_count = db.query(func.count(LoginAttempt.id)).filter(
        LoginAttempt.ip_address == ip_address,
        LoginAttempt.success == False,
        LoginAttempt.timestamp >= cutoff
    ).scalar() or 0
    
    # Determine ban duration based on failure count
    if failed_count >= 50:
        ban_minutes = settings.BAN_DURATION_MAX_MINUTES  # 24 hours
        reason = "Massive brute force attack detected"
    elif failed_count >= 20:
        ban_minutes = 120  # 2 hours
        reason = "Extended brute force attack"
    elif failed_count >= 10:
        ban_minutes = settings.BAN_DURATION_MINUTES  # 30 minutes
        reason = "Brute force attack detected"
    elif failed_count > 5:
        # Soft throttle - don't ban yet, but log
        reason = "Excessive failed attempts (throttled)"
        ban_minutes = 0
    else:
        return  # No action needed
    
    if ban_minutes > 0:
        ban_until = datetime.utcnow() + timedelta(minutes=ban_minutes)
        
        existing_ban = db.query(IPBlacklist).filter(
            IPBlacklist.ip_address == ip_address
        ).first()
        
        if existing_ban:
            # Extend existing ban
            existing_ban.banned_until = ban_until
            existing_ban.failed_attempts = failed_count
            existing_ban.reason = reason
        else:
            ban = IPBlacklist(
                ip_address=ip_address,
                banned_until=ban_until,
                reason=reason,
                failed_attempts=failed_count
            )
            db.add(ban)
        
        db.commit()


def clear_old_attempts(db: Session, days: int = 30) -> int:
    """Clean up old login attempts. Returns count deleted."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    result = db.query(LoginAttempt).filter(
        LoginAttempt.timestamp < cutoff
    ).delete()
    db.commit()
    return result
