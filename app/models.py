"""Database models with enhanced security fields."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Index
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """User model for voters and admins."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    voter_id = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    public_key = Column(Text, nullable=True)  # For ECDSA signatures
    has_voted = Column(Boolean, default=False)
    
    # Security fields
    device_fingerprint = Column(String(255), nullable=True)
    token_version = Column(Integer, default=0)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    
    # Status
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    votes = relationship("Vote", back_populates="voter")
    sessions = relationship("Session", back_populates="user")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_email_active', 'email', 'is_active'),
        Index('idx_user_voter_id', 'voter_id'),
    )


class Session(Base):
    """Active session tracking with zero-trust bindings."""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    
    # Zero-trust bindings
    device_fingerprint = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=False)
    ip_address_initial = Column(String(45), nullable=False)  # Original IP at login
    user_agent = Column(String(500), nullable=True)
    
    # Token binding
    token_fingerprint = Column(String(64), nullable=True)  # Hash of token for binding
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_activity_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    # Indexes
    __table_args__ = (
        Index('idx_session_user_active', 'user_id', 'is_active'),
        Index('idx_session_expires', 'expires_at'),
    )


class Vote(Base):
    """Vote transaction model with cryptographic verification."""
    __tablename__ = "votes"
    
    id = Column(Integer, primary_key=True, index=True)
    voter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    candidate_id = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Blockchain references
    block_index = Column(Integer, nullable=True)
    transaction_hash = Column(String(64), unique=True, index=True)
    
    # Cryptographic fields
    signature = Column(Text, nullable=True)
    nonce = Column(String(32), nullable=True)  # Anti-replay nonce
    vote_payload_hash = Column(String(64), nullable=False)  # Hash before signing
    
    # Verification status
    is_verified = Column(Boolean, default=False)
    verification_error = Column(Text, nullable=True)
    
    # Relationships
    voter = relationship("User", back_populates="votes")


class Block(Base):
    """Blockchain block model with merkle root."""
    __tablename__ = "blocks"
    
    id = Column(Integer, primary_key=True, index=True)
    index = Column(Integer, unique=True, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    votes_data = Column(Text, nullable=True)  # JSON serialized votes
    previous_hash = Column(String(64), nullable=False)
    nonce = Column(Integer, default=0)
    hash = Column(String(64), unique=True, index=True, nullable=False)
    
    # Enhanced security
    merkle_root = Column(String(64), nullable=True)  # Merkle root of votes
    validator = Column(String(50), default="system")
    signature = Column(Text, nullable=True)  # Block signature (optional)
    
    # Checkpoint
    is_checkpoint = Column(Boolean, default=False)
    checkpoint_hash = Column(String(64), nullable=True)  # Hash for chain verification


class IPBlacklist(Base):
    """IP blacklist with granular control."""
    __tablename__ = "ip_blacklist"
    
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), unique=True, index=True, nullable=False)
    banned_until = Column(DateTime, nullable=False)
    reason = Column(String(255), nullable=True)
    failed_attempts = Column(Integer, default=0)
    
    # Granular control
    ban_type = Column(String(20), default="temp")  # temp, permanent, subnet, asn
    parent_ban_id = Column(Integer, ForeignKey("ip_blacklist.id"), nullable=True)
    
    # Admin info
    banned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class LoginAttempt(Base):
    """Login attempt tracking with detailed forensics."""
    __tablename__ = "login_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), index=True, nullable=False)
    email = Column(String(255), nullable=True)
    success = Column(Boolean, default=False)
    
    # Detailed tracking
    attempt_type = Column(String(20), default="login")  # login, register, refresh, vote
    details = Column(Text, nullable=True)  # Additional context
    user_agent = Column(String(500), nullable=True)
    
    # Security signals
    device_fingerprint = Column(String(255), nullable=True)
    geo_location = Column(String(100), nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_attempt_ip_time', 'ip_address', 'timestamp'),
        Index('idx_attempt_email_time', 'email', 'timestamp'),
    )


class ActivityLog(Base):
    """Append-only audit log with hash chaining."""
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    # Hash chaining for tamper evidence
    previous_log_hash = Column(String(64), nullable=True)
    log_hash = Column(String(64), nullable=False, unique=True)
    
    # Context
    user_agent = Column(String(500), nullable=True)
    request_id = Column(String(36), nullable=True)  # Trace ID
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_log_user_time', 'user_id', 'timestamp'),
        Index('idx_log_action_time', 'action', 'timestamp'),
    )


class VoteNonce(Base):
    """Anti-replay nonce tracking."""
    __tablename__ = "vote_nonces"
    
    id = Column(Integer, primary_key=True, index=True)
    voter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    nonce = Column(String(32), unique=True, nullable=False)
    vote_hash = Column(String(64), nullable=False)  # Hash of vote to prevent replay
    used_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_nonce_voter', 'voter_id', 'used_at'),
    )


class ChainCheckpoint(Base):
    """Blockchain checkpoint for verification."""
    __tablename__ = "chain_checkpoints"
    
    id = Column(Integer, primary_key=True, index=True)
    block_index = Column(Integer, unique=True, nullable=False)
    block_hash = Column(String(64), nullable=False)
    total_votes = Column(Integer, default=0)
    checkpoint_hash = Column(String(64), nullable=False)  # Signed checkpoint
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Index
    __table_args__ = (
        Index('idx_checkpoint_block', 'block_index'),
    )
