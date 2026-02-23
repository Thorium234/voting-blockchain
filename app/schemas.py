"""Pydantic schemas for request/response validation with enhanced security."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


# Auth Schemas
class UserCreate(BaseModel):
    """Schema for user registration with validation."""
    email: EmailStr
    voter_id: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')
    password: str = Field(..., min_length=8, max_length=100)
    device_fingerprint: Optional[str] = None
    
    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Enforce password strength requirements."""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str
    device_fingerprint: Optional[str] = None


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds until expiration


class TokenRefresh(BaseModel):
    """Token refresh request."""
    refresh_token: str


class UserResponse(BaseModel):
    """User response schema."""
    id: int
    email: str
    voter_id: str
    has_voted: bool
    is_admin: bool
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserAdminResponse(UserResponse):
    """Extended user response for admins."""
    failed_login_attempts: int
    locked_until: Optional[datetime] = None
    token_version: int
    last_login_ip: Optional[str] = None


# Voting Schemas
class VoteCreate(BaseModel):
    """Schema for casting a vote with anti-replay protection."""
    candidate_id: str = Field(..., min_length=1, max_length=50)
    signature: Optional[str] = None  # ECDSA signature
    nonce: str = Field(..., min_length=16, max_length=64)  # Anti-replay nonce
    timestamp: int = Field(..., description="Unix timestamp (seconds)")
    
    @field_validator('timestamp')
    @classmethod
    def timestamp_recent(cls, v: int) -> int:
        """Ensure timestamp is within acceptable range."""
        import time
        current = int(time.time())
        if abs(current - v) > 300:  # 5 minute tolerance
            raise ValueError('Timestamp too old or in future')
        return v


class VoteResponse(BaseModel):
    """Vote transaction response."""
    id: int
    voter_id: int
    candidate_id: str
    timestamp: datetime
    transaction_hash: str
    block_index: Optional[int] = None
    nonce: Optional[str] = None
    is_verified: bool = False
    
    class Config:
        from_attributes = True


class VoteResult(BaseModel):
    """Aggregated vote results."""
    candidate_id: str
    vote_count: int
    percentage: float


class VotingResults(BaseModel):
    """All voting results."""
    total_votes: int
    results: List[VoteResult]
    blockchain_height: int
    chain_valid: bool
    merkle_root: Optional[str] = None


# Blockchain Schemas
class BlockResponse(BaseModel):
    """Block response schema."""
    index: int
    timestamp: datetime
    votes_count: int
    previous_hash: str
    nonce: int
    hash: str
    merkle_root: Optional[str] = None
    is_checkpoint: bool = False
    
    class Config:
        from_attributes = True


class BlockchainResponse(BaseModel):
    """Full blockchain response."""
    blocks: List[BlockResponse]
    height: int
    is_valid: bool
    total_votes: int
    latest_merkle_root: Optional[str] = None


class ChainValidation(BaseModel):
    """Chain validation result."""
    is_valid: bool
    invalid_blocks: List[int]
    message: str
    checkpoint_valid: bool = True


class BlockDetailResponse(BlockResponse):
    """Detailed block with vote data."""
    votes: List[dict]
    merkle_proof: Optional[List[str]] = None


# Security Schemas
class LoginAttemptResponse(BaseModel):
    """Login attempt info."""
    id: int
    ip_address: str
    email: Optional[str]
    success: bool
    attempt_type: str
    details: Optional[str]
    timestamp: datetime
    
    class Config:
        from_attributes = True


class IPRecord(BaseModel):
    """IP blacklist record."""
    ip_address: str
    banned_until: datetime
    reason: Optional[str]
    failed_attempts: int
    ban_type: str = "temp"
    
    class Config:
        from_attributes = True


class IPRecordDetail(IPRecord):
    """Detailed IP ban record."""
    banned_by: Optional[int] = None
    created_at: datetime
    is_permanent: bool = False


class ActivityLogResponse(BaseModel):
    """Activity log response."""
    id: int
    user_id: Optional[int]
    action: str
    details: Optional[str]
    ip_address: Optional[str]
    log_hash: Optional[str]
    timestamp: datetime
    
    class Config:
        from_attributes = True


# Admin Schemas
class DeviceReset(BaseModel):
    """Device reset request."""
    user_id: int


class IPUnban(BaseModel):
    """IP unban request."""
    ip_address: str


class IPBanRequest(BaseModel):
    """IP ban request."""
    ip_address: str
    reason: str = Field(..., min_length=10)
    duration_minutes: int = Field(..., ge=1, le=10080)  # 1 min to 1 week
    ban_subnet: bool = False


class AdminActionResponse(BaseModel):
    """Admin action response."""
    success: bool
    message: str
    details: Optional[dict] = None


class StatsResponse(BaseModel):
    """System statistics."""
    total_users: int
    total_votes: int
    total_blocks: int
    banned_ips: int
    active_sessions: int
    chain_valid: bool
    attack_stats: Optional[dict] = None


# Rate Limiting Schemas
class RateLimitStatus(BaseModel):
    """Rate limit status."""
    allowed: bool
    current: int
    limit: int
    remaining: int
    reset_in_seconds: int


class RateLimitResponse(BaseModel):
    """Rate limit response with details."""
    ip_status: RateLimitStatus
    user_status: Optional[RateLimitStatus] = None
    reason: Optional[str] = None
    banned_until: Optional[datetime] = None


# Health & Monitoring
class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    version: str
    database: str
    blockchain_height: int
    chain_valid: bool


# Audit
class AuditTrailResponse(BaseModel):
    """Audit trail response."""
    logs: List[ActivityLogResponse]
    total: int
    has_more: bool
