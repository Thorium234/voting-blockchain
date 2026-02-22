"""IP banning for brute force protection."""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models import IPBlacklist


def is_ip_banned(db: Session, ip_address: str) -> bool:
    """Check if an IP is currently banned."""
    ban = db.query(IPBlacklist).filter(
        IPBlacklist.ip_address == ip_address
    ).first()
    
    if not ban:
        return False
    
    # Check if ban has expired
    if ban.banned_until < datetime.utcnow():
        # Ban expired, remove it
        db.delete(ban)
        db.commit()
        return False
    
    return True


def ban_ip(
    db: Session,
    ip_address: str,
    reason: str,
    duration_minutes: int
) -> IPBlacklist:
    """Ban an IP address."""
    from datetime import timedelta
    
    banned_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
    
    # Check if already banned
    existing = db.query(IPBlacklist).filter(
        IPBlacklist.ip_address == ip_address
    ).first()
    
    if existing:
        existing.banned_until = banned_until
        existing.reason = reason
        db.commit()
        return existing
    
    # Create new ban
    ban = IPBlacklist(
        ip_address=ip_address,
        banned_until=banned_until,
        reason=reason
    )
    db.add(ban)
    db.commit()
    db.refresh(ban)
    
    return ban


def unban_ip(db: Session, ip_address: str) -> bool:
    """Unban an IP address."""
    ban = db.query(IPBlacklist).filter(
        IPBlacklist.ip_address == ip_address
    ).first()
    
    if ban:
        db.delete(ban)
        db.commit()
        return True
    
    return False


def get_banned_ips(db: Session) -> list:
    """Get all currently banned IPs."""
    now = datetime.utcnow()
    bans = db.query(IPBlacklist).filter(
        IPBlacklist.banned_until > now
    ).all()
    
    return bans


def cleanup_expired_bans(db: Session):
    """Remove expired bans from database."""
    now = datetime.utcnow()
    db.query(IPBlacklist).filter(
        IPBlacklist.banned_until < now
    ).delete()
    db.commit()
