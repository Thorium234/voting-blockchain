"""Pydantic schemas for request/response validation."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# Auth Schemas
class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    voter_id: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    device_fingerprint: Optional[str] = None


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
    created_at: datetime
    
    class Config:
        from_attributes = True


# Voting Schemas
class VoteCreate(BaseModel):
    """Schema for casting a vote."""
    candidate_id: str = Field(..., min_length=1, max_length=50)
    signature: Optional[str] = None  # Digital signature


class VoteResponse(BaseModel):
    """Vote transaction response."""
    id: int
    voter_id: int
    candidate_id: str
    timestamp: datetime
    transaction_hash: str
    block_index: Optional[int] = None
    
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


# Blockchain Schemas
class BlockResponse(BaseModel):
    """Block response schema."""
    index: int
    timestamp: datetime
    votes_count: int
    previous_hash: str
    nonce: int
    hash: str
    
    class Config:
        from_attributes = True


class BlockchainResponse(BaseModel):
    """Full blockchain response."""
    blocks: List[BlockResponse]
    height: int
    is_valid: bool


class ChainValidation(BaseModel):
    """Chain validation result."""
    is_valid: bool
    invalid_blocks: List[int]
    message: str


# Admin Schemas
class DeviceReset(BaseModel):
    """Device reset request."""
    user_id: int


class IPUnban(BaseModel):
    """IP unban request."""
    ip_address: str


class AdminActionResponse(BaseModel):
    """Admin action response."""
    success: bool
    message: str


# Security Schemas
class LoginAttemptResponse(BaseModel):
    """Login attempt info."""
    ip_address: str
    email: Optional[str]
    success: bool
    timestamp: datetime
    
    class Config:
        from_attributes = True


class IPRecord(BaseModel):
    """IP blacklist record."""
    ip_address: str
    banned_until: datetime
    reason: Optional[str]
    failed_attempts: int
    
    class Config:
        from_attributes = True


class ActivityLogResponse(BaseModel):
    """Activity log response."""
    id: int
    user_id: Optional[int]
    action: str
    details: Optional[str]
    ip_address: Optional[str]
    timestamp: datetime
    
    class Config:
        from_attributes = True
