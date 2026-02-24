"""Database models with enhanced security fields and role-based access."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Index, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """User model for voters, admins, and superadmins."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    voter_id = Column(String(50), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    public_key = Column(Text, nullable=True)
    has_voted = Column(Boolean, default=False)
    
    # Role-based access control
    role = Column(String(20), default='voter', nullable=False)
    
    # Voter registration fields (flexible)
    id_number = Column(String(50), nullable=True)
    reg_number = Column(String(50), nullable=True)
    full_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    location = Column(String(100), nullable=True)  # County/State/Region
    custom_fields = Column(JSON, nullable=True)
    
    # Security fields
    device_fingerprint = Column(String(255), nullable=True)
    token_version = Column(Integer, default=0)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_deletable = Column(Boolean, default=True)  # Superadmin cannot be deleted
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    votes = relationship("Vote", back_populates="voter")
    sessions = relationship("Session", back_populates="user")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_email_active', 'email', 'is_active'),
        Index('idx_user_voter_id', 'voter_id'),
        Index('idx_user_role', 'role'),
        Index('idx_user_email', 'email'),
        Index('idx_user_last_login', 'last_login_at'),
        Index('idx_user_created', 'created_at'),
    )
    
    @property
    def is_admin(self) -> bool:
        return self.role in ('admin', 'superadmin')
    
    @property
    def is_superadmin(self) -> bool:
        return self.role == 'superadmin'
    
    @property
    def can_vote(self) -> bool:
        return self.role == 'voter' and self.is_active and not self.has_voted
    
    @property
    def can_manage_users(self) -> bool:
        return self.role in ('admin', 'superadmin')
    
    @property
    def can_manage_admins(self) -> bool:
        return self.role == 'superadmin'


class ElectionSeat(Base):
    """Election seats (Presidential, Governor, Senate, etc.)."""
    __tablename__ = "election_seats"
    
    id = Column(Integer, primary_key=True, index=True)
    election_id = Column(Integer, ForeignKey("elections.id"), nullable=False)
    seat_id = Column(String(50), unique=True, nullable=False)
    seat_name = Column(String(100), nullable=False)
    seat_order = Column(Integer, default=0)
    max_aspirants = Column(Integer, default=10)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_seat_election', 'election_id'),
        Index('idx_seat_id', 'seat_id'),
    )


class SeatAspirant(Base):
    """Aspirants assigned to specific seats."""
    __tablename__ = "seat_aspirants"
    
    id = Column(Integer, primary_key=True, index=True)
    seat_id = Column(Integer, ForeignKey("election_seats.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    position_order = Column(Integer, default=0)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    __table_args__ = (
        Index('idx_seat_aspirant', 'seat_id', 'candidate_id'),
    )


class Candidate(Base):
    """Candidates/Aspirants for voting."""
    __tablename__ = "candidates"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    party = Column(String(100), nullable=True)
    manifesto = Column(Text, nullable=True)
    photo_url = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    status = Column(String(20), default='pending')  # pending, certified, rejected
    
    # Certification
    certified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    certified_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    __table_args__ = (
        Index('idx_candidate_active', 'candidate_id', 'is_active'),
        Index('idx_candidate_id', 'candidate_id'),
        Index('idx_candidate_status', 'status'),
    )


class Election(Base):
    """Election lifecycle management."""
    __tablename__ = "elections"
    
    id = Column(Integer, primary_key=True, index=True)
    election_id = Column(String(50), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Lifecycle status
    status = Column(String(20), default='draft')  # draft, initialized, open, closed, finalized
    
    # Genesis block
    genesis_block_hash = Column(String(64), nullable=True)
    genesis_created_at = Column(DateTime, nullable=True)
    
    # Poll timing
    polls_opened_at = Column(DateTime, nullable=True)
    polls_closed_at = Column(DateTime, nullable=True)
    results_finalized_at = Column(DateTime, nullable=True)
    
    # Configuration
    voter_fields_config = Column(JSON, nullable=True)  # Dynamic field configuration
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_election_status', 'status'),
        Index('idx_election_id', 'election_id'),
    )


class Session(Base):
    """Active session tracking."""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    
    device_fingerprint = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=False)
    ip_address_initial = Column(String(45), nullable=False)
    user_agent = Column(String(500), nullable=True)
    token_fingerprint = Column(String(64), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_activity_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="sessions")
    
    __table_args__ = (
        Index('idx_session_user_active', 'user_id', 'is_active'),
        Index('idx_session_expires', 'expires_at'),
        Index('idx_session_id', 'session_id'),
    )


class Vote(Base):
    """Vote transaction model."""
    __tablename__ = "votes"
    
    id = Column(Integer, primary_key=True, index=True)
    voter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seat_id = Column(Integer, ForeignKey("election_seats.id"), nullable=True)
    candidate_id = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    block_index = Column(Integer, nullable=True)
    transaction_hash = Column(String(64), unique=True, index=True)
    signature = Column(Text, nullable=True)
    nonce = Column(String(32), nullable=True)
    vote_payload_hash = Column(String(64), nullable=False)
    
    is_verified = Column(Boolean, default=False)
    verification_error = Column(Text, nullable=True)
    
    voter = relationship("User", back_populates="votes")
    
    __table_args__ = (
        Index('idx_vote_voter', 'voter_id'),
        Index('idx_vote_candidate', 'candidate_id'),
        Index('idx_vote_timestamp', 'timestamp'),
        Index('idx_vote_block', 'block_index'),
    )


class Block(Base):
    """Blockchain block model."""
    __tablename__ = "blocks"
    
    id = Column(Integer, primary_key=True, index=True)
    index = Column(Integer, unique=True, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    votes_data = Column(Text, nullable=True)
    previous_hash = Column(String(64), nullable=False)
    nonce = Column(Integer, default=0)
    hash = Column(String(64), unique=True, index=True, nullable=False)
    merkle_root = Column(String(64), nullable=True)
    validator = Column(String(50), default="system")
    signature = Column(Text, nullable=True)
    is_checkpoint = Column(Boolean, default=False)
    checkpoint_hash = Column(String(64), nullable=True)
    
    __table_args__ = (
        Index('idx_block_index', 'index'),
        Index('idx_block_hash', 'hash'),
        Index('idx_block_timestamp', 'timestamp'),
    )


class IPBlacklist(Base):
    """IP blacklist."""
    __tablename__ = "ip_blacklist"
    
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), unique=True, index=True, nullable=False)
    banned_until = Column(DateTime, nullable=False)
    reason = Column(String(255), nullable=True)
    failed_attempts = Column(Integer, default=0)
    ban_type = Column(String(20), default="temp")
    parent_ban_id = Column(Integer, ForeignKey("ip_blacklist.id"), nullable=True)
    banned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_ip_address', 'ip_address'),
        Index('idx_ip_banned_until', 'banned_until'),
        Index('idx_ip_active_bans', 'ip_address', 'banned_until'),
    )


class LoginAttempt(Base):
    """Login attempt tracking."""
    __tablename__ = "login_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), index=True, nullable=False)
    email = Column(String(255), nullable=True)
    success = Column(Boolean, default=False)
    attempt_type = Column(String(20), default="login")
    details = Column(Text, nullable=True)
    user_agent = Column(String(500), nullable=True)
    device_fingerprint = Column(String(255), nullable=True)
    geo_location = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_attempt_ip_time', 'ip_address', 'timestamp'),
        Index('idx_attempt_email_time', 'email', 'timestamp'),
    )


class ActivityLog(Base):
    """Append-only audit log."""
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    previous_log_hash = Column(String(64), nullable=True)
    log_hash = Column(String(64), nullable=False, unique=True)
    user_agent = Column(String(500), nullable=True)
    request_id = Column(String(36), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
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
    vote_hash = Column(String(64), nullable=False)
    used_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45), nullable=True)
    
    __table_args__ = (
        Index('idx_nonce_voter', 'voter_id', 'used_at'),
        Index('idx_nonce_value', 'nonce'),
    )


class ChainCheckpoint(Base):
    """Blockchain checkpoint."""
    __tablename__ = "chain_checkpoints"
    
    id = Column(Integer, primary_key=True, index=True)
    block_index = Column(Integer, unique=True, nullable=False)
    block_hash = Column(String(64), nullable=False)
    total_votes = Column(Integer, default=0)
    checkpoint_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_checkpoint_block', 'block_index'),
        Index('idx_checkpoint_hash', 'checkpoint_hash'),
    )
