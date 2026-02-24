"""Admin routes with enhanced security and monitoring."""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import Request as FastAPIRequest
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import User, IPBlacklist, ActivityLog, Block, Vote
from app.schemas import (
    UserResponse, 
    IPRecord, 
    IPRecordDetail,
    AdminActionResponse, 
    ActivityLogResponse,
    BlockchainResponse,
    BlockResponse,
    StatsResponse,
    AuditTrailResponse
)
from app.auth.dependencies import get_current_admin, get_client_ip
from app.security.ip_ban import (
    ban_ip as ban_ip_util,
    unban_ip as unban_ip_util,
    get_banned_ips,
    get_attack_statistics
)
from app.security.audit_logging import create_audit_log, verify_log_chain, query_logs
from app.security.rate_limiter import clear_old_attempts
from app.blockchain.chain import Blockchain
import json

router = APIRouter(prefix="/admin", tags=["Admin"])


def get_client_ip_internal(request: FastAPIRequest) -> str:
    """Get client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def require_reauth_for_destructive():
    """
    Dependency for destructive admin actions.
    In production, this would require re-authentication.
    """
    # For now, just ensure user is admin
    pass


@router.get("/users", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all users (admin only)."""
    from sqlalchemy.orm import joinedload
    users = db.query(User).options(
        joinedload(User.votes),
        joinedload(User.sessions)
    ).offset(skip).limit(limit).all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get user details (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.post("/users/{user_id}/deactivate", response_model=AdminActionResponse)
def deactivate_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Deactivate a user account (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Don't allow deactivating admins
    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate admin accounts"
        )
    
    user.is_active = False
    user.token_version += 1  # Invalidate all tokens
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="deactivate_user",
        details=f"Deactivated user {user_id}",
        ip_address=get_client_ip_internal(request)
    )
    
    db.commit()
    
    return AdminActionResponse(
        success=True,
        message=f"User {user.voter_id} has been deactivated"
    )


@router.post("/users/{user_id}/activate", response_model=AdminActionResponse)
def activate_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Activate a user account (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = True
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="activate_user",
        details=f"Activated user {user_id}",
        ip_address=get_client_ip_internal(request)
    )
    
    db.commit()
    
    return AdminActionResponse(
        success=True,
        message=f"User {user.voter_id} has been activated"
    )


@router.post("/reset-device/{user_id}", response_model=AdminActionResponse)
def reset_device(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Reset user's device binding (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    old_fp = user.device_fingerprint
    user.device_fingerprint = None
    user.token_version += 1  # Invalidate existing tokens
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="reset_device",
        details=f"Reset device for user {user_id}. Old FP: {old_fp}",
        ip_address=get_client_ip_internal(request)
    )
    
    db.commit()
    
    return AdminActionResponse(
        success=True,
        message=f"Device reset for user {user.voter_id}"
    )


@router.post("/ban-ip", response_model=AdminActionResponse)
def ban_ip(
    ip_address: str,
    reason: str,
    duration_minutes: int = 30,
    ban_subnet: bool = False,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Ban an IP address (admin only)."""
    ban_ip_util(
        db=db,
        ip_address=ip_address,
        reason=reason,
        duration_minutes=duration_minutes,
        ban_subnet=ban_subnet,
        admin_user_id=current_user.id
    )
    
    return AdminActionResponse(
        success=True,
        message=f"IP {ip_address} has been banned for {duration_minutes} minutes",
        details={"reason": reason, "ban_subnet": ban_subnet}
    )


@router.post("/unban-ip/{ip_address}", response_model=AdminActionResponse)
def unban_ip(
    ip_address: str,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Unban an IP address (admin only)."""
    success = unban_ip_util(
        db=db,
        ip_address=ip_address,
        admin_user_id=current_user.id
    )
    
    if success:
        return AdminActionResponse(
            success=True,
            message=f"IP {ip_address} has been unbanned"
        )
    
    return AdminActionResponse(
        success=False,
        message=f"IP {ip_address} was not banned"
    )


@router.get("/banned-ips", response_model=List[IPRecord])
def list_banned_ips(
    include_expired: bool = False,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get list of banned IPs (admin only)."""
    bans = get_banned_ips(db, include_expired)
    return bans


@router.get("/banned-ips/{ip_address}", response_model=IPRecordDetail)
def get_ban_details(
    ip_address: str,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get detailed ban information (admin only)."""
    ban = db.query(IPBlacklist).filter(
        IPBlacklist.ip_address == ip_address
    ).first()
    
    if not ban:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IP not found in ban list"
        )
    
    return IPRecordDetail(
        ip_address=ban.ip_address,
        banned_until=ban.banned_until,
        reason=ban.reason,
        failed_attempts=ban.failed_attempts,
        ban_type=ban.ban_type,
        banned_by=ban.banned_by,
        created_at=ban.created_at,
        is_permanent=ban.banned_until.year > 2030
    )


@router.get("/logs", response_model=AuditTrailResponse)
def get_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: int = None,
    action: str = None,
    ip_address: str = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get activity logs with filters (admin only)."""
    result = query_logs(
        db=db,
        user_id=user_id,
        action=action,
        ip_address=ip_address,
        limit=limit,
        offset=skip
    )
    
    return AuditTrailResponse(
        logs=result["logs"],
        total=result["total"],
        has_more=result["has_more"]
    )


@router.get("/logs/verify", response_model=dict)
def verify_audit_log(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Verify audit log chain integrity (admin only)."""
    result = verify_log_chain(db)
    return result


@router.get("/security/stats", response_model=dict)
def get_security_stats(
    hours: int = 24,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get security statistics (admin only)."""
    attack_stats = get_attack_statistics(db, hours)
    
    return attack_stats


@router.get("/stats", response_model=StatsResponse)
def get_stats(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get system statistics (admin only)."""
    total_users = db.query(User).count()
    total_votes = db.query(Vote).count()
    total_blocks = db.query(Block).count()
    
    now = datetime.utcnow()
    banned_ips = db.query(IPBlacklist).filter(
        IPBlacklist.banned_until > now
    ).count()
    
    from app.models import Session as SessionModel
    active_sessions = db.query(SessionModel).filter(
        SessionModel.is_active == True,
        SessionModel.expires_at > now
    ).count()
    
    # Chain validation
    blockchain = Blockchain()
    is_valid, _ = blockchain.is_chain_valid()
    
    # Get attack stats
    attack_stats = get_attack_statistics(db, 24)
    
    return StatsResponse(
        total_users=total_users,
        total_votes=total_votes,
        total_blocks=total_blocks,
        banned_ips=banned_ips,
        active_sessions=active_sessions,
        chain_valid=is_valid,
        attack_stats=attack_stats
    )


@router.get("/blockchain", response_model=BlockchainResponse)
def view_blockchain(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """View full blockchain (admin only)."""
    blocks = db.query(Block).order_by(Block.index).all()
    
    block_responses = [
        BlockResponse(
            index=b.index,
            timestamp=b.timestamp,
            votes_count=len(b.votes_data) if b.votes_data else 0,
            previous_hash=b.previous_hash,
            nonce=b.nonce,
            hash=b.hash,
            merkle_root=b.merkle_root,
            is_checkpoint=False
        )
        for b in blocks
    ]
    
    # Validate chain
    blockchain = Blockchain()
    is_valid, invalid = blockchain.is_chain_valid()
    
    return BlockchainResponse(
        blocks=block_responses,
        height=len(blocks),
        is_valid=is_valid,
        total_votes=blockchain.get_total_votes()
    )


@router.post("/force-mine", response_model=AdminActionResponse)
def force_mine(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Force block mining (admin only)."""
    from app.voting.routes import get_blockchain
    
    blockchain = get_blockchain()
    new_block = blockchain.mine_pending_votes()
    
    if new_block:
        # Store in database
        db_block = Block(
            index=new_block.index,
            timestamp=new_block.timestamp,
            votes_data=json.dumps(new_block.votes),
            previous_hash=new_block.previous_hash,
            nonce=new_block.nonce,
            hash=new_block.hash,
            merkle_root=new_block.merkle_root
        )
        db.add(db_block)
        db.commit()
        
        message = f"Block {new_block.index} mined with {len(new_block.votes)} votes"
    else:
        message = "No pending votes to mine"
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="force_mine",
        details=message,
        ip_address=get_client_ip_internal(request)
    )
    
    return AdminActionResponse(
        success=True,
        message=message
    )


@router.post("/cleanup/attempts", response_model=AdminActionResponse)
def cleanup_attempts(
    days: int = 30,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Clean up old login attempts (admin only)."""
    count = clear_old_attempts(db, days)
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="cleanup_attempts",
        details=f"Cleaned up {count} old login attempts",
        ip_address=get_client_ip_internal(request)
    )
    
    return AdminActionResponse(
        success=True,
        message=f"Cleaned up {count} old login attempts"
    )


@router.post("/cleanup/expired-bans", response_model=AdminActionResponse)
def cleanup_expired_bans(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Clean up expired IP bans (admin only)."""
    from app.security.ip_ban import cleanup_expired_bans as cleanup
    
    count = cleanup(db)
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="cleanup_bans",
        details=f"Cleaned up {count} expired bans",
        ip_address=get_client_ip_internal(request)
    )
    
    return AdminActionResponse(
        success=True,
        message=f"Cleaned up {count} expired bans"
    )


# Add missing import
import json
from fastapi import Request as RequestClass
