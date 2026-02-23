"""Authentication dependencies with zero-trust support."""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.auth.jwt_handler import decode_token, is_token_valid_for_user

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None,
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token with zero-trust validation."""
    token = credentials.credentials
    
    # Get client IP and device fingerprint for binding verification
    client_ip = get_client_ip(request) if request else None
    device_fp = get_device_fingerprint(request) if request else None
    
    # Decode token with binding checks
    payload = decode_token(
        token, 
        ip_address=client_ip,
        device_fingerprint=device_fp,
        check_bindings=True
    )
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user ID from token
    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Fetch user from database
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify token is valid for this user (checks token version)
    if not is_token_valid_for_user(payload, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been invalidated. Please login again."
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user


def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current admin user."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


def get_client_ip(request: Request) -> str:
    """Get client IP address from request with proxy support."""
    if not request:
        return "unknown"
    
    # Check for forwarded header (if behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take first IP (original client)
        return forwarded.split(",")[0].strip()
    
    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host if request.client else "unknown"


def get_device_fingerprint(request: Request) -> str:
    """Generate device fingerprint from request headers."""
    if not request:
        return "unknown"
    
    # Combine multiple signals for fingerprinting
    user_agent = request.headers.get("user-agent", "")
    accept_language = request.headers.get("accept-language", "")
    accept_encoding = request.headers.get("accept-encoding", "")
    ip = get_client_ip(request)
    
    # Simple fingerprint (in production, use a proper library)
    fingerprint = f"{ip}:{user_agent[:50]}:{accept_language[:20]}:{accept_encoding[:20]}"
    return fingerprint
