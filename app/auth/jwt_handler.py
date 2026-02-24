"""
Zero-Trust JWT Authentication with IP and Device Binding.

Security Features:
- Short-lived access tokens
- Rotating refresh tokens
- Token versioning
- Bind sessions to IP and device fingerprint
- Reject tokens if bindings change
"""
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
import hashlib

from app.config import get_settings
from app.models import User

settings = get_settings()


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    ip_address: Optional[str] = None,
    device_fingerprint: Optional[str] = None
) -> str:
    """
    Create a JWT access token with zero-trust bindings.
    
    Includes:
    - Subject (user ID)
    - Expiration
    - Token type
    - Token version
    - IP binding (optional)
    - Device fingerprint binding (optional)
    """
    to_encode = data.copy()
    
    # Set expiration
    expire = datetime.utcnow() + (
        expires_delta 
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    to_encode.update({
        "exp": expire,
        "type": "access",
        "iat": datetime.utcnow()
    })
    
    # Add token version if user specified
    if "version" not in to_encode:
        to_encode["version"] = 0
    
    # Add zero-trust bindings
    if settings.BIND_TOKEN_TO_IP and ip_address:
        to_encode["ip"] = _hash_ip(ip_address)
    
    if settings.BIND_TOKEN_TO_DEVICE and device_fingerprint:
        to_encode["device"] = _hash_fingerprint(device_fingerprint)
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    data: dict,
    ip_address: Optional[str] = None,
    device_fingerprint: Optional[str] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Refresh tokens:
    - Longer lived (7 days)
    - Can be used to get new access tokens
    - Include same bindings as access token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "iat": datetime.utcnow()
    })
    
    # Add zero-trust bindings
    if settings.BIND_TOKEN_TO_IP and ip_address:
        to_encode["ip"] = _hash_ip(ip_address)
    
    if settings.BIND_TOKEN_TO_DEVICE and device_fingerprint:
        to_encode["device"] = _hash_fingerprint(device_fingerprint)
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(
    token: str,
    ip_address: Optional[str] = None,
    device_fingerprint: Optional[str] = None,
    check_bindings: bool = True
) -> Optional[dict]:
    """
    Decode and validate a JWT token with zero-trust checks.
    
    Args:
        token: JWT token string
        ip_address: Current client IP (for binding verification)
        device_fingerprint: Current device fingerprint
        check_bindings: Whether to verify IP/device bindings
    
    Returns:
        Token payload if valid, None if invalid
    """
    try:
        # Decode without verification first to check token type
        unverified = jwt.decode(token, key="", options={"verify_signature": False})
        
        if unverified.get("type") != "access":
            # Allow refresh tokens but don't bind them as tightly
            pass
        
        # Full decode with signature verification
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # Zero-trust binding checks
        if check_bindings and settings.BIND_TOKEN_TO_IP:
            token_ip = payload.get("ip")
            if token_ip and ip_address:
                if token_ip != _hash_ip(ip_address):
                    # IP changed - potential token theft
                    return None
        
        if check_bindings and settings.BIND_TOKEN_TO_DEVICE:
            token_device = payload.get("device")
            if token_device and device_fingerprint:
                if token_device != _hash_fingerprint(device_fingerprint):
                    # Device changed - potential token theft
                    return None
        
        return payload
        
    except JWTError:
        return None


def verify_token_type(token: str, expected_type: str) -> bool:
    """Verify token type (access or refresh)."""
    payload = decode_token(token, check_bindings=False)
    if payload:
        return payload.get("type") == expected_type
    return False


def verify_token_bindings(
    token: str,
    ip_address: str,
    device_fingerprint: Optional[str] = None
) -> Dict[str, bool]:
    """
    Verify token bindings and return detailed results.
    
    Returns:
        Dict with 'ip_valid' and 'device_valid' booleans
    """
    results = {"ip_valid": True, "device_valid": True}
    
    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False}
        )
        
        # Check IP binding
        if settings.BIND_TOKEN_TO_IP:
            token_ip = payload.get("ip")
            if token_ip and ip_address:
                results["ip_valid"] = (token_ip == _hash_ip(ip_address))
        
        # Check device binding
        if settings.BIND_TOKEN_TO_DEVICE:
            token_device = payload.get("device")
            if token_device and device_fingerprint:
                results["device_valid"] = (token_device == _hash_fingerprint(device_fingerprint))
    
    except JWTError:
        results["ip_valid"] = False
        results["device_valid"] = False
    
    return results


def get_token_claims(token: str) -> Optional[dict]:
    """Get all claims from a token without verification."""
    try:
        return jwt.decode(token, options={"verify_signature": False})
    except JWTError:
        return None


def _hash_ip(ip_address: str) -> str:
    """Hash IP address for storage in token."""
    return hashlib.sha256(ip_address.encode()).hexdigest()[:16]


def _hash_fingerprint(fingerprint: str) -> str:
    """Hash device fingerprint for storage in token."""
    return hashlib.sha256(fingerprint.encode()).hexdigest()[:16]


def invalidate_user_tokens(user: User) -> int:
    """
    Invalidate all tokens for a user by incrementing token version.
    
    Returns the new token version.
    """
    user.token_version += 1
    return user.token_version


def is_token_valid_for_user(token_payload: dict, user: User) -> bool:
    """
    Check if token is valid for the given user.
    
    Checks:
    - Token version matches user
    - User is still active
    """
    if not user.is_active:
        return False
    
    token_version = token_payload.get("version", 0)
    
    if settings.TOKEN_VERSION_ENABLED:
        return user.token_version <= token_version
    
    return True
