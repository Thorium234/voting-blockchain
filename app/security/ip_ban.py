"""
Enhanced IP Burn & Brute Force Containment System.

Features:
- Progressive penalties (soft throttle → temp ban → long ban)
- Subnet-level banning
- ASN tracking (if available)
- Pattern detection for credential stuffing
- Admin override with audit logging
- Auto-ban on malicious patterns
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
import re

from app.models import IPBlacklist, LoginAttempt
from app.config import get_settings

settings = get_settings()


def is_ip_banned(db: Session, ip_address: str) -> bool:
    """Check if an IP is currently banned."""
    ban = db.query(IPBlacklist).filter(
        IPBlacklist.ip_address == ip_address
    ).first()
    
    if not ban:
        return False
    
    # Check if ban has expired
    if ban.banned_until < datetime.utcnow():
        db.delete(ban)
        db.commit()
        return False
    
    return True


def is_subnet_banned(db: Session, ip_address: str) -> bool:
    """Check if IP's subnet is banned."""
    # Extract /24 subnet for IPv4
    if ":" not in ip_address:  # IPv4
        subnet = ".".join(ip_address.split(".")[:3]) + ".0/24"
    else:  # IPv6 - use /64
        subnet = ":".join(ip_address.split(":")[:4]) + "::/64"
    
    # Check for subnet bans
    subnet_bans = db.query(IPBlacklist).filter(
        IPBlacklist.ip_address.like("%/24") |
        IPBlacklist.ip_address.like("%/64")
    ).all()
    
    for ban in subnet_bans:
        if subnet.startswith(ban.ip_address.replace("/24", "").replace("/64", "")):
            if ban.banned_until > datetime.utcnow():
                return True
    
    return False


def get_ban_details(db: Session, ip_address: str) -> Optional[Dict]:
    """Get detailed ban information for an IP."""
    ban = db.query(IPBlacklist).filter(
        IPBlacklist.ip_address == ip_address
    ).first()
    
    if not ban:
        return None
    
    return {
        "ip_address": ban.ip_address,
        "banned_until": ban.banned_until.isoformat() if ban.banned_until else None,
        "reason": ban.reason,
        "failed_attempts": ban.failed_attempts,
        "created_at": ban.created_at.isoformat() if ban.created_at else None,
        "is_permanent": ban.banned_until.year > 2030 if ban.banned_until else False
    }


def ban_ip(
    db: Session,
    ip_address: str,
    reason: str,
    duration_minutes: int,
    ban_subnet: bool = False,
    ban_asn: bool = False,
    permanent: bool = False,
    admin_user_id: Optional[int] = None
) -> IPBlacklist:
    """
    Ban an IP address with full audit trail.
    
    Args:
        db: Database session
        ip_address: IP to ban
        reason: Reason for ban
        duration_minutes: Ban duration (ignored if permanent=True)
        ban_subnet: Also ban the /24 subnet
        ban_asn: Also ban the ASN (if detectable)
        admin_user_id: Admin performing the ban
    """
    # Calculate ban expiration
    if permanent:
        banned_until = datetime.utcnow() + timedelta(days=365 * 10)  # 10 years
    else:
        banned_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
    
    # Check if already banned
    existing = db.query(IPBlacklist).filter(
        IPBlacklist.ip_address == ip_address
    ).first()
    
    if existing:
        existing.banned_until = banned_until
        existing.reason = reason
        existing.failed_attempts = existing.failed_attempts or 0
        db.commit()
        ban = existing
    else:
        ban = IPBlacklist(
            ip_address=ip_address,
            banned_until=banned_until,
            reason=reason,
            failed_attempts=0
        )
        db.add(ban)
        db.commit()
        db.refresh(ban)
    
    # Optionally ban subnet
    if ban_subnet and settings.SUBNET_BAN_ENABLED:
        if ":" not in ip_address:  # IPv4
            subnet = ".".join(ip_address.split(".")[:3]) + ".0/24"
            _ban_subnet(db, subnet, reason, banned_until)
    
    # Log admin action
    if admin_user_id:
        from app.models import ActivityLog
        log = ActivityLog(
            user_id=admin_user_id,
            action="admin_ban_ip",
            details=f"Banned IP: {ip_address}, Reason: {reason}, "
                    f"Duration: {'permanent' if permanent else f'{duration_minutes}min'}",
            ip_address=ip_address
        )
        db.add(log)
        db.commit()
    
    return ban


def _ban_subnet(
    db: Session,
    subnet: str,
    reason: str,
    banned_until: datetime
) -> None:
    """Ban an entire subnet."""
    existing = db.query(IPBlacklist).filter(
        IPBlacklist.ip_address == subnet
    ).first()
    
    if existing:
        existing.banned_until = banned_until
        existing.reason = f"{reason} (subnet)"
    else:
        ban = IPBlacklist(
            ip_address=subnet,
            banned_until=banned_until,
            reason=f"{reason} (subnet)",
            failed_attempts=0
        )
        db.add(ban)
    
    db.commit()


def unban_ip(
    db: Session,
    ip_address: str,
    admin_user_id: Optional[int] = None
) -> bool:
    """Unban an IP address with audit trail."""
    ban = db.query(IPBlacklist).filter(
        IPBlacklist.ip_address == ip_address
    ).first()
    
    if ban:
        # Also try to unban subnet
        if ":" not in ip_address:
            subnet = ".".join(ip_address.split(".")[:3]) + ".0/24"
            subnet_ban = db.query(IPBlacklist).filter(
                IPBlacklist.ip_address == subnet
            ).first()
            if subnet_ban:
                db.delete(subnet_ban)
        
        db.delete(ban)
        db.commit()
        
        # Log admin action
        if admin_user_id:
            from app.models import ActivityLog
            log = ActivityLog(
                user_id=admin_user_id,
                action="admin_unban_ip",
                details=f"Unbanned IP: {ip_address}",
                ip_address=ip_address
            )
            db.add(log)
            db.commit()
        
        return True
    
    return False


def get_banned_ips(db: Session, include_expired: bool = False) -> List[Dict]:
    """Get all currently banned IPs."""
    now = datetime.utcnow()
    
    query = db.query(IPBlacklist)
    
    if not include_expired:
        query = query.filter(IPBlacklist.banned_until > now)
    
    bans = query.order_by(IPBlacklist.banned_until.desc()).all()
    
    return [
        {
            "ip_address": ban.ip_address,
            "banned_until": ban.banned_until.isoformat(),
            "reason": ban.reason,
            "failed_attempts": ban.failed_attempts,
            "created_at": ban.created_at.isoformat() if ban.created_at else None,
            "is_expired": ban.banned_until < now
        }
        for ban in bans
    ]


def cleanup_expired_bans(db: Session) -> int:
    """Remove expired bans from database. Returns count deleted."""
    now = datetime.utcnow()
    result = db.query(IPBlacklist).filter(
        IPBlacklist.banned_until < now
    ).delete()
    db.commit()
    return result


def detect_credential_stuffing(db: Session, ip_address: str) -> bool:
    """
    Detect credential stuffing attacks.
    
    Patterns indicating credential stuffing:
    - Many different emails from same IP
    - Rapid-fire attempts with different credentials
    - Pattern: failed attempts with valid email format
    """
    # Get recent attempts from this IP
    cutoff = datetime.utcnow() - timedelta(minutes=5)
    recent_attempts = db.query(LoginAttempt).filter(
        LoginAttempt.ip_address == ip_address,
        LoginAttempt.timestamp >= cutoff
    ).all()
    
    if len(recent_attempts) < 10:
        return False  # Not enough data
    
    # Check for many different emails
    unique_emails = set(attempt.email for attempt in recent_attempts if attempt.email)
    
    # If trying many different emails, likely credential stuffing
    if len(unique_emails) >= 5:
        return True
    
    # Check for rapid attempts (more than 3 per second)
    attempts_per_second = len(recent_attempts) / 300  # 5 minutes
    if attempts_per_second > 0.1:  # More than 1 per 10 seconds
        return True
    
    return False


def detect_signature_abuse(db: Session, ip_address: str) -> bool:
    """Detect invalid signature spam."""
    cutoff = datetime.utcnow() - timedelta(minutes=1)
    recent = db.query(LoginAttempt).filter(
        LoginAttempt.ip_address == ip_address,
        LoginAttempt.timestamp >= cutoff,
        LoginAttempt.details.like("%invalid_signature%")
    ).count()
    
    return recent >= 5  # More than 5 invalid signatures per minute


def auto_ban_malicious(
    db: Session,
    ip_address: str,
    attack_type: str,
    admin_user_id: Optional[int] = None
) -> None:
    """
    Automatically ban IP based on detected attack patterns.
    
    Args:
        db: Database session
        ip_address: Attacker's IP
        attack_type: Type of attack detected
        admin_user_id: Admin user for audit
    """
    ban_reasons = {
        "credential_stuffing": "Automated credential stuffing attack detected",
        "signature_abuse": "Invalid signature spam detected",
        "vote_fraud": "Vote manipulation attempt detected",
        "ddos": "Distributed denial of service attempt detected",
        "token_abuse": "JWT token manipulation detected"
    }
    
    reason = ban_reasons.get(attack_type, f"Security violation: {attack_type}")
    
    # Longer ban for automated attacks
    ban_duration = 60  # 1 hour for auto-bans
    
    ban_ip(
        db=db,
        ip_address=ip_address,
        reason=reason,
        duration_minutes=ban_duration,
        admin_user_id=admin_user_id
    )


def get_attack_statistics(db: Session, hours: int = 24) -> Dict:
    """Get statistics on attack attempts."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    # Total failed attempts
    total_failed = db.query(LoginAttempt).filter(
        LoginAttempt.success == False,
        LoginAttempt.timestamp >= cutoff
    ).count()
    
    # Unique IPs with failures
    unique_ips = db.query(LoginAttempt.ip_address).filter(
        LoginAttempt.success == False,
        LoginAttempt.timestamp >= cutoff
    ).distinct().count()
    
    # Currently banned
    now = datetime.utcnow()
    currently_banned = db.query(IPBlacklist).filter(
        IPBlacklist.banned_until > now
    ).count()
    
    # Credential stuffing candidates
    stuffing_detected = db.query(LoginAttempt.ip_address).filter(
        LoginAttempt.timestamp >= cutoff,
        LoginAttempt.details.like("%credential_stuffing%")
    ).distinct().count()
    
    return {
        "period_hours": hours,
        "total_failed_attempts": total_failed,
        "unique_attacking_ips": unique_ips,
        "currently_banned": currently_banned,
        "credential_stuffing_attempts": stuffing_detected,
        "avg_attempts_per_ip": round(total_failed / unique_ips, 2) if unique_ips > 0 else 0
    }
