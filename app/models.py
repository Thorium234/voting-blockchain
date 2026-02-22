"""Database models."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """User model for voters and admins."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    voter_id = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    public_key = Column(Text, nullable=True)  # For advanced crypto mode
    has_voted = Column(Boolean, default=False)
    device_fingerprint = Column(String(255), nullable=True)
    token_version = Column(Integer, default=0)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    votes = relationship("Vote", back_populates="voter")
    sessions = relationship("Session", back_populates="user")


class Session(Base):
    """Active session tracking."""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    device_fingerprint = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=False)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")


class Vote(Base):
    """Vote transaction model."""
    __tablename__ = "votes"
    
    id = Column(Integer, primary_key=True, index=True)
    voter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    candidate_id = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    block_index = Column(Integer, nullable=True)
    transaction_hash = Column(String(64), unique=True, index=True)
    signature = Column(Text, nullable=True)  # Digital signature
    
    # Relationships
    voter = relationship("User", back_populates="votes")


class Block(Base):
    """Blockchain block model."""
    __tablename__ = "blocks"
    
    id = Column(Integer, primary_key=True, index=True)
    index = Column(Integer, unique=True, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    votes_data = Column(Text, nullable=True)  # JSON serialized votes
    previous_hash = Column(String(64), nullable=False)
    nonce = Column(Integer, default=0)
    hash = Column(String(64), unique=True, index=True, nullable=False)
    validator = Column(String(50), default="system")


class IPBlacklist(Base):
    """IP blacklist for brute force protection."""
    __tablename__ = "ip_blacklist"
    
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), unique=True, index=True, nullable=False)
    banned_until = Column(DateTime, nullable=False)
    reason = Column(String(255), nullable=True)
    failed_attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class LoginAttempt(Base):
    """Login attempt tracking."""
    __tablename__ = "login_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), index=True, nullable=False)
    email = Column(String(255), nullable=True)
    success = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class ActivityLog(Base):
    """Activity logging for audit trail."""
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
