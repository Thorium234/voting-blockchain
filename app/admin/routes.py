"""Admin routes for system management."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import User, IPBlacklist, ActivityLog, Block
from app.schemas import (
    UserResponse, 
    IPRecord, 
    AdminActionResponse, 
    ActivityLogResponse,
    BlockchainResponse,
    BlockResponse
)
from app.auth.dependencies import get_current_admin
from app.security.ip_ban import unban_ip as unban_ip_util
from app.blockchain.chain import Blockchain

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all users (admin only)."""
    users = db.query(User).offset(skip).limit(limit).all()
    return users


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
    
    user.device_fingerprint = None
    user.token_version += 1  # Invalidate existing tokens
    
    # Log activity
    log = ActivityLog(
        user_id=current_user.id,
        action="reset_device",
        details=f"Reset device for user {user_id}",
    )
    db.add(log)
    db.commit()
    
    return AdminActionResponse(
        success=True,
        message=f"Device reset for user {user.voter_id}"
    )


@router.post("/unban-ip", response_model=AdminActionResponse)
def unban_ip(
    ip_address: str,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Unban an IP address (admin only)."""
    success = unban_ip_util(db, ip_address)
    
    if success:
        # Log activity
        log = ActivityLog(
            user_id=current_user.id,
            action="unban_ip",
            details=f"Unbanned IP: {ip_address}",
        )
        db.add(log)
        db.commit()
        
        return AdminActionResponse(
            success=True,
            message=f"IP {ip_address} has been unbanned"
        )
    
    return AdminActionResponse(
        success=False,
        message=f"IP {ip_address} was not banned"
    )


@router.get("/banned-ips", response_model=List[IPRecord])
def get_banned_ips(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get list of banned IPs (admin only)."""
    from datetime import datetime
    now = datetime.utcnow()
    
    bans = db.query(IPBlacklist).filter(
        IPBlacklist.banned_until > now
    ).all()
    
    return bans


@router.get("/logs", response_model=List[ActivityLogResponse])
def get_activity_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: int = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get activity logs (admin only)."""
    query = db.query(ActivityLog).order_by(desc(ActivityLog.timestamp))
    
    if user_id:
        query = query.filter(ActivityLog.user_id == user_id)
    
    logs = query.offset(skip).limit(limit).all()
    return logs


@router.get("/stats")
def get_stats(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get system statistics (admin only)."""
    from datetime import datetime, timedelta
    
    total_users = db.query(User).count()
    total_votes = db.query(Block).count()
    now = datetime.utcnow()
    banned_ips = db.query(IPBlacklist).filter(
        IPBlacklist.banned_until > now
    ).count()
    
    # Get active users (last 24 hours)
    cutoff = datetime.utcnow() - timedelta(days=1)
    active_users = db.query(ActivityLog).filter(
        ActivityLog.timestamp >= cutoff,
        ActivityLog.action == "login"
    ).distinct(ActivityLog.user_id).count()
    
    return {
        "total_users": total_users,
        "total_votes": total_votes,
        "banned_ips": banned_ips,
        "active_users_24h": active_users
    }


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
            hash=b.hash
        )
        for b in blocks
    ]
    
    # Validate chain
    is_valid = True
    for i in range(1, len(blocks)):
        if blocks[i].previous_hash != blocks[i-1].hash:
            is_valid = False
            break
    
    return BlockchainResponse(
        blocks=block_responses,
        height=len(blocks),
        is_valid=is_valid
    )


@router.post("/force-mine", response_model=AdminActionResponse)
def force_mine(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Force block mining (admin only)."""
    # This would integrate with the voting module's blockchain
    # For now, return a placeholder response
    
    log = ActivityLog(
        user_id=current_user.id,
        action="force_mine",
        details="Forced block mining",
    )
    db.add(log)
    db.commit()
    
    return AdminActionResponse(
        success=True,
        message="Block mining triggered"
    )
