"""Authentication routes with enterprise security."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Session as SessionModel, LoginAttempt, ActivityLog
from app.schemas import UserCreate, UserLogin, Token, UserResponse
from app.auth.password import hash_password, verify_password
from app.auth.jwt_handler import (
    create_access_token, 
    create_refresh_token, 
    decode_token,
    verify_token_type,
    verify_token_bindings
)
from app.auth.dependencies import get_current_user, get_current_admin, get_client_ip, get_device_fingerprint
from app.config import get_settings
from app.security.rate_limiter import check_rate_limit, get_rate_limit_status
from app.security.ip_ban import is_ip_banned, detect_credential_stuffing
from app.security.audit_logging import create_audit_log, log_auth_attempt

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate, 
    request: Request, 
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Register a new user (ADMIN ONLY - voters, candidates, or other admins)."""
    client_ip = get_client_ip(request)
    
    # Check if IP is banned
    if is_ip_banned(db, client_ip):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your IP has been temporarily banned. Try again later."
        )
    
    # Check rate limit for registration
    allowed, rate_details = check_rate_limit(db, client_ip, "register")
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many registration attempts. {rate_details.get('reason', 'Please try again later.')}"
        )
    
    # Check if email already exists
    if db.query(User).filter(User.email == user_data.email).first():
        # Log attempt but don't reveal if email exists
        create_audit_log(
            db=db,
            user_id=None,
            action="register_failed",
            details=f"Registration attempt with existing email: {user_data.email}",
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please try again."
        )
    
    # Check if voter_id already exists
    if db.query(User).filter(User.voter_id == user_data.voter_id).first():
        create_audit_log(
            db=db,
            user_id=None,
            action="register_failed",
            details=f"Registration attempt with existing voter_id: {user_data.voter_id}",
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please try again."
        )
    
    # Validate role assignment (only superadmin can create admins)
    if user_data.role in ['admin', 'superadmin']:
        if not current_admin.is_superadmin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superadmin can create admin accounts"
            )
    
    # Create user with specified role
    user = User(
        email=user_data.email,
        voter_id=user_data.voter_id,
        password_hash=hash_password(user_data.password),
        device_fingerprint=user_data.device_fingerprint,
        role=user_data.role or 'voter',
        is_active=True,
        is_verified=True  # Admin-registered users are pre-verified
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Log successful registration by admin
    create_audit_log(
        db=db,
        user_id=current_admin.id,
        action="admin_register_user",
        details=f"Admin {current_admin.email} registered {user_data.role}: {user_data.voter_id}",
        ip_address=client_ip
    )
    
    return user


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, request: Request, db: Session = Depends(get_db)):
    """Login with brute force protection and device binding."""
    client_ip = get_client_ip(request)
    device_fp = get_device_fingerprint(request)
    
    # Check if IP is banned
    if is_ip_banned(db, client_ip):
        create_audit_log(
            db=db,
            user_id=None,
            action="login_banned_ip",
            details=f"Login attempt from banned IP: {client_ip}",
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your IP has been temporarily banned. Try again later."
        )
    
    # Check rate limit
    allowed, rate_details = check_rate_limit(db, client_ip, "auth")
    if not allowed:
        # Check for credential stuffing
        if detect_credential_stuffing(db, client_ip):
            from app.security.ip_ban import auto_ban_malicious
            auto_ban_malicious(db, client_ip, "credential_stuffing")
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )
    
    # Find user
    user = db.query(User).filter(User.email == credentials.email).first()
    
    # Record attempt (we'll update success status later)
    attempt = LoginAttempt(
        ip_address=client_ip,
        email=credentials.email,
        success=False,
        attempt_type="login",
        device_fingerprint=device_fp
    )
    db.add(attempt)
    
    # Check credentials
    if not user or not verify_password(credentials.password, user.password_hash):
        db.commit()
        
        # Log failed attempt
        log_auth_attempt(
            db=db,
            email=credentials.email,
            ip_address=client_ip,
            success=False,
            user_id=user.id if user else None,
            details="Invalid credentials"
        )
        
        # Check if we should ban
        if user:
            from app.security.rate_limiter import check_and_ban_ip
            check_and_ban_ip(db, client_ip)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        db.commit()
        log_auth_attempt(
            db=db,
            email=credentials.email,
            ip_address=client_ip,
            success=False,
            user_id=user.id,
            details="Inactive account"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Check device fingerprint (if required and set)
    if settings.REQUIRE_DEVICE_FINGERPRINT and user.device_fingerprint:
        if credentials.device_fingerprint != user.device_fingerprint:
            attempt.success = False
            attempt.details = "Device fingerprint mismatch"
            db.commit()
            
            log_auth_attempt(
                db=db,
                email=credentials.email,
                ip_address=client_ip,
                success=False,
                user_id=user.id,
                details="Device not recognized"
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Device not recognized. Please contact admin to reset your device."
            )
    
    # Update device fingerprint on first login
    if not user.device_fingerprint and credentials.device_fingerprint:
        user.device_fingerprint = credentials.device_fingerprint
    
    # Check for existing active sessions (single session policy)
    active_session = db.query(SessionModel).filter(
        SessionModel.user_id == user.id,
        SessionModel.is_active == True,
        SessionModel.expires_at > datetime.utcnow()
    ).first()
    
    if active_session:
        # Invalidate previous session
        active_session.is_active = False
        create_audit_log(
            db=db,
            user_id=user.id,
            action="session_invalidated",
            details=f"Previous session invalidated for new login",
            ip_address=client_ip
        )
    
    # Create new session
    session_id = f"{user.id}_{datetime.utcnow().timestamp()}"
    session = SessionModel(
        user_id=user.id,
        session_id=session_id,
        device_fingerprint=device_fp,
        ip_address=client_ip,
        ip_address_initial=client_ip,
        user_agent=request.headers.get("user-agent", ""),
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(session)
    
    # Update token version to invalidate old tokens (handle NULL)
    user.token_version = (user.token_version or 0) + 1
    
    # Update last login info
    user.last_login_at = datetime.utcnow()
    user.last_login_ip = client_ip
    user.failed_login_attempts = 0
    
    # Mark attempt as successful
    attempt.success = True
    attempt.user_id = user.id
    
    # Log successful login
    log_auth_attempt(
        db=db,
        email=credentials.email,
        ip_address=client_ip,
        success=True,
        user_id=user.id,
        details="Login successful"
    )
    
    db.commit()
    
    # Create tokens with IP binding
    access_token = create_access_token(
        data={"sub": str(user.id), "version": user.token_version},
        ip_address=client_ip,
        device_fingerprint=credentials.device_fingerprint or device_fp
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "version": user.token_version},
        ip_address=client_ip,
        device_fingerprint=credentials.device_fingerprint or device_fp
    )
    
    # Calculate expiration
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in
    )


@router.post("/logout")
def logout(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Logout and invalidate current session."""
    client_ip = get_client_ip(request)
    
    # Invalidate all sessions for this user
    db.query(SessionModel).filter(
        SessionModel.user_id == current_user.id,
        SessionModel.is_active == True
    ).update({"is_active": False})
    
    # Increment token version (handle NULL)
    current_user.token_version = (current_user.token_version or 0) + 1
    
    # Log activity
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="logout",
        details="User logged out"
    )
    
    db.commit()
    
    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=Token)
def refresh_token(refresh_data: dict, request: Request, db: Session = Depends(get_db)):
    """Refresh access token with security validation."""
    refresh_token_str = refresh_data.get("refresh_token")
    if not refresh_token_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token required"
        )
    
    client_ip = get_client_ip(request)
    device_fp = get_device_fingerprint(request)
    
    # Verify token type
    if not verify_token_type(refresh_token_str, "refresh"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    # Decode token (with binding checks relaxed for refresh)
    payload = decode_token(
        refresh_token_str, 
        ip_address=client_ip,
        device_fingerprint=device_fp,
        check_bindings=False  # Allow refresh from different IP
    )
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    user_id = payload.get("sub")
    token_version = payload.get("version", 0)
    
    # Get user
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or user.token_version > token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been invalidated"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Create new tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "version": user.token_version},
        ip_address=client_ip,
        device_fingerprint=device_fp
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.id), "version": user.token_version},
        ip_address=client_ip,
        device_fingerprint=device_fp
    )
    
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=expires_in
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return current_user


@router.get("/rate-limit-status")
def get_rate_limit(request: Request):
    """Get current rate limit status."""
    client_ip = get_client_ip(request)
    status = get_rate_limit_status(client_ip, "auth")
    return status


# Add missing import
from typing import Optional
