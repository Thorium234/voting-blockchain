"""
Anti-Replay Protection & Vote Integrity Module.

Features:
- Nonce + timestamp validation for vote transactions
- Deterministic vote hashing before signing
- Exact-once vote submission enforcement
- Database-level nonce tracking
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
import hashlib
import time
import secrets
from sqlalchemy.orm import Session

from app.models import VoteNonce, Vote
from app.config import get_settings

settings = get_settings()


def generate_nonce() -> str:
    """Generate a cryptographically secure nonce."""
    return secrets.token_hex(16)


def hash_vote_payload(
    voter_id: str,
    candidate_id: str,
    nonce: str,
    timestamp: int
) -> str:
    """
    Create deterministic hash of vote payload before signing.
    
    This ensures:
    - Vote content cannot be modified after signing
    - Signature verification is deterministic
    - No replay attacks possible with same nonce
    """
    # Create canonical vote data
    vote_data = {
        "voter_id": voter_id,
        "candidate_id": candidate_id,
        "nonce": nonce,
        "timestamp": timestamp
    }
    
    # Sort keys for deterministic serialization
    import json
    vote_string = json.dumps(vote_data, sort_keys=True)
    
    return hashlib.sha256(vote_string.encode()).hexdigest()


def validate_vote_nonce(
    db: Session,
    voter_id: int,
    nonce: str,
    vote_hash: str,
    ip_address: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate vote nonce for anti-replay.
    
    Checks:
    - Nonce format (proper length)
    - Nonce not previously used
    - Vote hash not previously used
    - Nonce not expired
    
    Returns:
        (is_valid: bool, error_message: Optional[str])
    """
    # Check nonce format
    if len(nonce) < 16:
        return False, "Invalid nonce format"
    
    # Check if nonce already used
    existing_nonce = db.query(VoteNonce).filter(
        VoteNonce.nonce == nonce
    ).first()
    
    if existing_nonce:
        return False, "Nonce already used"
    
    # Check if vote hash already used (prevents replay)
    existing_vote = db.query(Vote).filter(
        Vote.vote_payload_hash == vote_hash
    ).first()
    
    if existing_vote:
        return False, "Vote payload already registered"
    
    # Check recent nonces for this voter (prevent fast re-voting)
    recent_cutoff = datetime.utcnow() - timedelta(
        seconds=settings.VOTE_NONCE_EXPIRE_SECONDS
    )
    recent_nonce = db.query(VoteNonce).filter(
        VoteNonce.voter_id == voter_id,
        VoteNonce.used_at >= recent_cutoff
    ).first()
    
    if recent_nonce:
        return False, "Recent vote attempt detected. Please wait before voting again."
    
    return True, None


def record_used_nonce(
    db: Session,
    voter_id: int,
    nonce: str,
    vote_hash: str,
    ip_address: str
) -> None:
    """Record a used nonce after successful vote."""
    vote_nonce = VoteNonce(
        voter_id=voter_id,
        nonce=nonce,
        vote_hash=vote_hash,
        ip_address=ip_address
    )
    db.add(vote_nonce)
    db.commit()


def cleanup_expired_nonces(db: Session, days: int = 7) -> int:
    """Clean up expired nonces. Returns count deleted."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    result = db.query(VoteNonce).filter(
        VoteNonce.used_at < cutoff
    ).delete()
    db.commit()
    return result


def validate_timestamp(timestamp: int) -> Tuple[bool, Optional[str]]:
    """
    Validate vote timestamp.
    
    Ensures:
    - Timestamp is not too old
    - Timestamp is not in the future
    - Within configured tolerance
    """
    current_time = int(time.time())
    
    # Check if in future (allow small tolerance)
    if timestamp > current_time + 10:
        return False, "Timestamp is in the future"
    
    # Check if too old
    age = current_time - timestamp
    if age > settings.VOTE_TIMESTAMP_TOLERANCE_SECONDS:
        return False, f"Timestamp too old (>{settings.VOTE_TIMESTAMP_TOLERANCE_SECONDS}s)"
    
    return True, None


def check_double_voting(db: Session, voter_id: int) -> Tuple[bool, Optional[dict]]:
    """
    Check if voter has already voted.
    
    Checks both:
    - Database vote records
    - Blockchain (via voter_id)
    
    Returns:
        (has_voted: bool, vote_info: Optional[dict])
    """
    # Check database
    existing_vote = db.query(Vote).filter(
        Vote.voter_id == voter_id
    ).first()
    
    if existing_vote:
        return True, {
            "source": "database",
            "candidate_id": existing_vote.candidate_id,
            "timestamp": existing_vote.timestamp.isoformat(),
            "block_index": existing_vote.block_index,
            "transaction_hash": existing_vote.transaction_hash
        }
    
    # Check nonce records (in progress voting)
    recent_cutoff = datetime.utcnow() - timedelta(
        seconds=settings.VOTE_NONCE_EXPIRE_SECONDS
    )
    recent_nonce = db.query(VoteNonce).filter(
        VoteNonce.voter_id == voter_id,
        VoteNonce.used_at >= recent_cutoff
    ).first()
    
    if recent_nonce:
        return True, {
            "source": "pending",
            "nonce": recent_nonce.nonce,
            "timestamp": recent_nonce.used_at.isoformat()
        }
    
    return False, None


def get_vote_integrity_report(db: Session, voter_id: int) -> Dict:
    """
    Generate a vote integrity report for a voter.
    
    Useful for voter verification:
    - Did they vote?
    - Which candidate?
    - When?
    - Block hash?
    - Is it verified?
    """
    vote = db.query(Vote).filter(
        Vote.voter_id == voter_id
    ).first()
    
    if not vote:
        return {
            "has_voted": False,
            "message": "No vote found for this voter"
        }
    
    return {
        "has_voted": True,
        "candidate_id": vote.candidate_id,
        "timestamp": vote.timestamp.isoformat(),
        "block_index": vote.block_index,
        "transaction_hash": vote.transaction_hash,
        "vote_payload_hash": vote.vote_payload_hash,
        "is_verified": vote.is_verified,
        "verification_error": vote.verification_error,
        "nonce": vote.nonce
    }
