"""
Append-Only Audit Logging with Hash Chaining.

Features:
- Hash-chained logs for tamper evidence
- Time-synchronized logging (UTC)
- Automatic hash calculation
- Query and forensic capabilities
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import hashlib
import json
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import ActivityLog
from app.config import get_settings

settings = get_settings()


def compute_log_hash(
    log_id: int,
    user_id: Optional[int],
    action: str,
    details: Optional[str],
    timestamp: datetime,
    previous_hash: Optional[str]
) -> str:
    """
    Compute cryptographic hash for a log entry.
    
    Creates deterministic hash including:
    - Log ID (prevents reordering)
    - User ID
    - Action type
    - Details
    - Timestamp
    - Previous log hash (creates chain)
    """
    log_data = {
        "id": log_id,
        "user_id": user_id,
        "action": action,
        "details": details,
        "timestamp": timestamp.isoformat() if timestamp else None,
        "previous_hash": previous_hash
    }
    
    log_string = json.dumps(log_data, sort_keys=True)
    return hashlib.sha256(log_string.encode()).hexdigest()


def get_last_log_hash(db: Session) -> Optional[str]:
    """Get the hash of the most recent log entry."""
    last_log = db.query(ActivityLog).order_by(
        ActivityLog.id.desc()
    ).first()
    
    return last_log.log_hash if last_log else None


def create_audit_log(
    db: Session,
    user_id: Optional[int],
    action: str,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None
) -> ActivityLog:
    """
    Create a new audit log entry with hash chaining.
    
    This is the main entry point for all audit logging.
    """
    # Get previous hash
    previous_hash = get_last_log_hash(db)
    
    # Get current timestamp
    timestamp = datetime.utcnow()
    
    # Create log entry (ID will be assigned on flush)
    log = ActivityLog(
        user_id=user_id,
        action=action,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
        previous_log_hash=previous_hash,
        timestamp=timestamp
    )
    
    db.add(log)
    db.flush()  # Get the ID
    
    # Compute and set hash
    log.log_hash = compute_log_hash(
        log_id=log.id,
        user_id=user_id,
        action=action,
        details=details,
        timestamp=timestamp,
        previous_hash=previous_hash
    )
    
    db.commit()
    db.refresh(log)
    
    return log


def verify_log_chain(db: Session) -> Dict:
    """
    Verify the integrity of the entire audit log chain.
    
    Returns:
        Dict with verification results
    """
    logs = db.query(ActivityLog).order_by(ActivityLog.id).all()
    
    if not logs:
        return {
            "valid": True,
            "total_logs": 0,
            "message": "No logs to verify"
        }
    
    # Verify each log's hash
    invalid_entries = []
    broken_chain = []
    
    for i, log in enumerate(logs):
        # Verify this log's hash
        expected_hash = compute_log_hash(
            log_id=log.id,
            user_id=log.user_id,
            action=log.action,
            details=log.details,
            timestamp=log.timestamp,
            previous_hash=log.previous_log_hash
        )
        
        if expected_hash != log.log_hash:
            invalid_entries.append({
                "id": log.id,
                "action": log.action,
                "expected_hash": expected_hash[:16],
                "actual_hash": log.log_hash[:16]
            })
        
        # Verify chain link
        if i > 0:
            previous_log = logs[i - 1]
            if log.previous_log_hash != previous_log.log_hash:
                broken_chain.append({
                    "log_id": log.id,
                    "expected_previous": previous_log.log_hash[:16],
                    "actual_previous": log.previous_log_hash[:16] if log.previous_log_hash else "None"
                })
    
    return {
        "valid": len(invalid_entries) == 0 and len(broken_chain) == 0,
        "total_logs": len(logs),
        "invalid_entries": invalid_entries,
        "broken_chain": broken_chain,
        "message": "Audit log chain is intact" if not (invalid_entries or broken_chain) else "Chain integrity compromised"
    }


def log_auth_attempt(
    db: Session,
    email: str,
    ip_address: str,
    success: bool,
    user_id: Optional[int] = None,
    details: Optional[str] = None
) -> ActivityLog:
    """Log an authentication attempt."""
    action = "auth_success" if success else "auth_failure"
    
    return create_audit_log(
        db=db,
        user_id=user_id,
        action=action,
        details=details or f"Login attempt for {email}",
        ip_address=ip_address
    )


def log_vote_cast(
    db: Session,
    voter_id: int,
    candidate_id: str,
    ip_address: str,
    block_index: int,
    transaction_hash: str
) -> ActivityLog:
    """Log a vote casting event."""
    return create_audit_log(
        db=db,
        user_id=voter_id,
        action="vote_cast",
        details=f"Voted for {candidate_id}, block {block_index}, tx {transaction_hash[:16]}",
        ip_address=ip_address
    )


def log_admin_action(
    db: Session,
    admin_user_id: int,
    action: str,
    details: str,
    ip_address: Optional[str] = None
) -> ActivityLog:
    """Log an administrative action."""
    return create_audit_log(
        db=db,
        user_id=admin_user_id,
        action=f"admin_{action}",
        details=details,
        ip_address=ip_address
    )


def log_security_event(
    db: Session,
    event_type: str,
    severity: str,
    details: str,
    ip_address: Optional[str] = None,
    user_id: Optional[int] = None
) -> ActivityLog:
    """Log a security-related event."""
    return create_audit_log(
        db=db,
        user_id=user_id,
        action=f"security_{event_type}",
        details=f"[{severity}] {details}",
        ip_address=ip_address
    )


def query_logs(
    db: Session,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    ip_address: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict:
    """Query audit logs with filters."""
    query = db.query(ActivityLog)
    
    if user_id:
        query = query.filter(ActivityLog.user_id == user_id)
    
    if action:
        query = query.filter(ActivityLog.action.like(f"%{action}%"))
    
    if ip_address:
        query = query.filter(ActivityLog.ip_address == ip_address)
    
    if start_time:
        query = query.filter(ActivityLog.timestamp >= start_time)
    
    if end_time:
        query = query.filter(ActivityLog.timestamp <= end_time)
    
    total = query.count()
    
    logs = query.order_by(
        desc(ActivityLog.timestamp)
    ).offset(offset).limit(limit).all()
    
    return {
        "logs": logs,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total
    }


def get_recent_security_events(
    db: Session,
    hours: int = 24,
    limit: int = 50
) -> List[ActivityLog]:
    """Get recent security-related events."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    return db.query(ActivityLog).filter(
        ActivityLog.action.like("security_%"),
        ActivityLog.timestamp >= cutoff
    ).order_by(desc(ActivityLog.timestamp)).limit(limit).all()


def cleanup_old_logs(db: Session, days: Optional[int] = None) -> int:
    """
    Clean up old audit logs.
    
    WARNING: This breaks the hash chain!
    Only call this if you're sure about the implications.
    Consider exporting logs before cleanup.
    """
    retention_days = days or settings.AUDIT_LOG_RETENTION_DAYS
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    
    result = db.query(ActivityLog).filter(
        ActivityLog.timestamp < cutoff
    ).delete()
    db.commit()
    
    return result


def export_logs_json(
    db: Session,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> str:
    """Export logs as JSON for external auditing."""
    query = db.query(ActivityLog)
    
    if start_time:
        query = query.filter(ActivityLog.timestamp >= start_time)
    if end_time:
        query = query.filter(ActivityLog.timestamp <= end_time)
    
    logs = query.order_by(ActivityLog.id).all()
    
    return json.dumps([
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "details": log.details,
            "ip_address": log.ip_address,
            "timestamp": log.timestamp.isoformat(),
            "log_hash": log.log_hash,
            "previous_hash": log.previous_log_hash
        }
        for log in logs
    ], indent=2)
