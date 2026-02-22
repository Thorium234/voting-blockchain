"""Authentication routes."""
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
    verify_token_type
)
from app.auth.dependencies import get_current_user, get_client_ip, get_device_fingerprint
from app.config import get_settings
from app.security.rate_limiter import check_rate_limit, get_rate_limit_status

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    """Register a new voter."""
    # Check if email already exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if voter_id already exists
    if db.query(User).filter(User.voter_id == user_data.voter_id).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Voter ID already registered"
        )
    
    # Check rate limit
    client_ip = get_client_ip(request)
    if not check_rate_limit(db, client_ip, "register"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please try again later."
        )
    
    # Create user
    user = User(
        email=user_data.email,
        voter_id=user_data.voter_id,
        password_hash=hash_password(user_data.password),
        device_fingerprint=user_data.device_fingerprint,
        is_admin=False,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Log activity
    log = ActivityLog(
        user_id=user.id,
        action="register",
        details=f"User registered with voter_id: {user_data.voter_id}",
        ip_address=client_ip
    )
    db.add(log)
    db.commit()
    
    return user


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, request: Request, db: Session = Depends(get_db)):
    """Login and get access tokens."""
    client_ip = get_client_ip(request)
    device_fp = get_device_fingerprint(request)
    
    # Check if IP is banned
    from app.security.ip_ban import is_ip_banned
    if is_ip_banned(db, client_ip):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your IP has been temporarily banned. Try again later."
        )
    
    # Check rate limit
    if not check_rate_limit(db, client_ip, "login"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )
    
    # Find user
    user = db.query(User).filter(User.email == credentials.email).first()
    
    # Record attempt
    attempt = LoginAttempt(
        ip_address=client_ip,
        email=credentials.email,
        success=False
    )
    db.add(attempt)
    
    if not user or not verify_password(credentials.password, user.password_hash):
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check device fingerprint (if set)
    if user.device_fingerprint and credentials.device_fingerprint:
        if user.device_fingerprint != credentials.device_fingerprint:
            # Log failed attempt due to device mismatch
            attempt.success = False
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Device not recognized. Please contact admin to reset your device."
            )
    elif user.device_fingerprint:
        # First login from new device - optionally block or warn
        pass
    
    # Update device fingerprint on first login
    if not user.device_fingerprint and credentials.device_fingerprint:
        user.device_fingerprint = credentials.device_fingerprint
    
    # Check if user already has active session (single session policy)
    active_session = db.query(SessionModel).filter(
        SessionModel.user_id == user.id,
        SessionModel.is_active == True,
        SessionModel.expires_at > datetime.utcnow()
    ).first()
    
    if active_session:
        # Invalidate previous session
        active_session.is_active = False
    
    # Create new session
    session_id = f"{user.id}_{datetime.utcnow().timestamp()}"
    session = SessionModel(
        user_id=user.id,
        session_id=session_id,
        device_fingerprint=device_fp,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent", ""),
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(session)
    
    # Update token version to invalidate old tokens
    user.token_version += 1
    
    # Mark attempt as successful
    attempt.success = True
    
    # Log activity
    log = ActivityLog(
        user_id=user.id,
        action="login",
        details="User logged in",
        ip_address=client_ip
    )
    db.add(log)
    
    db.commit()
    
    # Create tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "version": user.token_version}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "version": user.token_version}
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Logout and invalidate current session."""
    # Invalidate all sessions for this user
    db.query(SessionModel).filter(
        SessionModel.user_id == current_user.id,
        SessionModel.is_active == True
    ).update({"is_active": False})
    
    # Increment token version
    current_user.token_version += 1
    
    # Log activity
    log = ActivityLog(
        user_id=current_user.id,
        action="logout",
        details="User logged out"
    )
    db.add(log)
    
    db.commit()
    
    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=Token)
def refresh_token(refresh_data: dict, db: Session = Depends(get_db)):
    """Refresh access token using refresh token."""
    refresh_token = refresh_data.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token required"
        )
    
    # Verify token type
    if not verify_token_type(refresh_token, "refresh"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    # Decode token
    payload = decode_token(refresh_token)
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
    
    # Create new tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "version": user.token_version}
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.id), "version": user.token_version}
    )
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return current_user
