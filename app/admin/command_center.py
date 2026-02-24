"""Super Admin Command Center - Complete Election Management."""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime
import uuid
import hashlib

from app.database import get_db
from app.models import User, Candidate, Election, ElectionSeat, SeatAspirant, Vote, ActivityLog
from app.admin.superadmin_routes import require_superadmin
from app.security.audit_logging import create_audit_log

router = APIRouter(prefix="/command-center", tags=["CommandCenter"])


# ==================== ELECTION WIZARD ====================

@router.post("/election/create-wizard")
def create_election_wizard(
    title: str,
    description: str,
    seats: List[Dict[str, Any]],
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Create election with seats in one step.
    seats = [
        {"name": "Presidential", "max_aspirants": 5},
        {"name": "Gubernatorial", "max_aspirants": 3}
    ]
    """
    election_id = f"ELEC_{uuid.uuid4().hex[:8].upper()}"
    
    election = Election(
        election_id=election_id,
        title=title,
        description=description,
        status='draft',
        created_by=current_user.id
    )
    db.add(election)
    db.flush()
    
    created_seats = []
    for idx, seat_data in enumerate(seats):
        seat_id = f"SEAT_{uuid.uuid4().hex[:6].upper()}"
        seat = ElectionSeat(
            election_id=election.id,
            seat_id=seat_id,
            seat_name=seat_data['name'],
            seat_order=idx,
            max_aspirants=seat_data.get('max_aspirants', 10),
            description=seat_data.get('description')
        )
        db.add(seat)
        created_seats.append({
            "seat_id": seat_id,
            "name": seat_data['name'],
            "max_aspirants": seat_data.get('max_aspirants', 10)
        })
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="create_election_wizard",
        details=f"Created election {election_id} with {len(seats)} seats",
        ip_address="system"
    )
    
    db.commit()
    
    return {
        "success": True,
        "election_id": election_id,
        "seats": created_seats,
        "message": f"Election created with {len(seats)} seats"
    }


@router.post("/election/{election_id}/seat/{seat_id}/assign-aspirants")
def assign_aspirants_to_seat(
    election_id: str,
    seat_id: str,
    aspirant_ids: List[str],
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Assign multiple aspirants to a specific seat."""
    seat = db.query(ElectionSeat).filter(ElectionSeat.seat_id == seat_id).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")
    
    if len(aspirant_ids) > seat.max_aspirants:
        raise HTTPException(status_code=400, detail=f"Maximum {seat.max_aspirants} aspirants allowed")
    
    # Clear existing assignments
    db.query(SeatAspirant).filter(SeatAspirant.seat_id == seat.id).delete()
    
    assigned = []
    for idx, candidate_id in enumerate(aspirant_ids):
        candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if not candidate:
            continue
        
        assignment = SeatAspirant(
            seat_id=seat.id,
            candidate_id=candidate.id,
            position_order=idx,
            assigned_by=current_user.id
        )
        db.add(assignment)
        assigned.append(candidate.name)
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="assign_aspirants",
        details=f"Assigned {len(assigned)} aspirants to {seat.seat_name}",
        ip_address="system"
    )
    
    db.commit()
    
    return {
        "success": True,
        "seat": seat.seat_name,
        "assigned_count": len(assigned),
        "aspirants": assigned
    }


@router.get("/election/{election_id}/ballot-preview")
def get_ballot_preview(
    election_id: str,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Preview how voters will see the ballot."""
    election = db.query(Election).filter(Election.election_id == election_id).first()
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    
    seats = db.query(ElectionSeat).filter(
        ElectionSeat.election_id == election.id
    ).order_by(ElectionSeat.seat_order).all()
    
    ballot = []
    for seat in seats:
        aspirants_query = db.query(Candidate).join(
            SeatAspirant, SeatAspirant.candidate_id == Candidate.id
        ).filter(
            SeatAspirant.seat_id == seat.id
        ).order_by(SeatAspirant.position_order).all()
        
        ballot.append({
            "seat_id": seat.seat_id,
            "seat_name": seat.seat_name,
            "aspirant_count": len(aspirants_query),
            "aspirants": [
                {
                    "candidate_id": a.candidate_id,
                    "name": a.name,
                    "party": a.party,
                    "photo_url": a.photo_url
                }
                for a in aspirants_query
            ]
        })
    
    return {
        "election_id": election_id,
        "title": election.title,
        "ballot": ballot
    }


# ==================== AUTO VOTER ID GENERATION ====================

@router.post("/voter/mint-identity")
def mint_voter_identity(
    email: str,
    full_name: str,
    id_number: str = None,
    reg_number: str = None,
    phone: str = None,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Generate cryptographically secure voter ID and blockchain address."""
    from app.auth.password import hash_password
    
    # Check duplicate
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate unique voter ID
    timestamp = str(datetime.utcnow().timestamp())
    unique_string = f"{email}{full_name}{timestamp}"
    voter_id = f"V{hashlib.sha256(unique_string.encode()).hexdigest()[:10].upper()}"
    
    # Generate blockchain address
    blockchain_seed = f"{voter_id}{timestamp}"
    blockchain_address = f"0x{hashlib.sha256(blockchain_seed.encode()).hexdigest()[:40]}"
    
    # Generate temporary password
    temp_password = f"Vote{uuid.uuid4().hex[:8]}!"
    
    user = User(
        email=email,
        voter_id=voter_id,
        password_hash=hash_password(temp_password),
        role='voter',
        full_name=full_name,
        id_number=id_number,
        reg_number=reg_number,
        phone=phone,
        public_key=blockchain_address,
        is_active=True,
        created_by=current_user.id
    )
    db.add(user)
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="mint_voter_identity",
        details=f"Minted voter ID: {voter_id} for {full_name}",
        ip_address="system"
    )
    
    db.commit()
    
    return {
        "success": True,
        "voter_id": voter_id,
        "blockchain_address": blockchain_address,
        "email": email,
        "temp_password": temp_password,
        "message": "Voter identity minted successfully"
    }


# ==================== OMNISCIENT MONITORING ====================

@router.get("/surveillance/admin-activity")
def get_admin_surveillance(
    hours: int = 24,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Real-time surveillance of all admin activities."""
    from datetime import timedelta
    from app.models import Session as SessionModel
    
    since = datetime.utcnow() - timedelta(hours=hours)
    
    # Get all admins
    admins = db.query(User).filter(User.role.in_(['admin', 'superadmin'])).all()
    
    surveillance = []
    for admin in admins:
        # Last login
        last_session = db.query(SessionModel).filter(
            SessionModel.user_id == admin.id
        ).order_by(desc(SessionModel.last_activity_at)).first()
        
        # Recent actions
        actions = db.query(ActivityLog).filter(
            ActivityLog.user_id == admin.id,
            ActivityLog.timestamp >= since
        ).order_by(desc(ActivityLog.timestamp)).limit(10).all()
        
        # Current session status
        active_session = db.query(SessionModel).filter(
            SessionModel.user_id == admin.id,
            SessionModel.is_active == True,
            SessionModel.expires_at > datetime.utcnow()
        ).first()
        
        surveillance.append({
            "admin_id": admin.id,
            "email": admin.email,
            "role": admin.role,
            "is_deletable": admin.is_deletable,
            "last_login": admin.last_login_at.isoformat() if admin.last_login_at else None,
            "last_login_ip": admin.last_login_ip,
            "last_activity": last_session.last_activity_at.isoformat() if last_session else None,
            "is_online": active_session is not None,
            "session_ip": active_session.ip_address if active_session else None,
            "recent_actions": [
                {
                    "action": a.action,
                    "details": a.details,
                    "timestamp": a.timestamp.isoformat(),
                    "ip": a.ip_address
                }
                for a in actions
            ],
            "action_count_24h": len(actions)
        })
    
    return {
        "surveillance_period_hours": hours,
        "total_admins": len(admins),
        "admins": surveillance
    }


@router.get("/surveillance/unauthorized-attempts")
def get_unauthorized_attempts(
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Track unauthorized access attempts to Super Admin functions."""
    from app.models import LoginAttempt
    
    # Failed login attempts
    failed_logins = db.query(LoginAttempt).filter(
        LoginAttempt.success == False
    ).order_by(desc(LoginAttempt.timestamp)).limit(50).all()
    
    # Suspicious activity logs
    suspicious = db.query(ActivityLog).filter(
        ActivityLog.action.in_(['delete_admin', 'modify_superadmin', 'unauthorized_access'])
    ).order_by(desc(ActivityLog.timestamp)).limit(50).all()
    
    return {
        "failed_logins": [
            {
                "email": f.email,
                "ip": f.ip_address,
                "timestamp": f.timestamp.isoformat(),
                "details": f.details
            }
            for f in failed_logins
        ],
        "suspicious_activities": [
            {
                "user_id": s.user_id,
                "action": s.action,
                "details": s.details,
                "ip": s.ip_address,
                "timestamp": s.timestamp.isoformat()
            }
            for s in suspicious
        ]
    }


# ==================== SYSTEM HEALTH ====================

@router.get("/system/health-check")
def system_health_check(
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Comprehensive system health check."""
    from app.blockchain.chain import Blockchain
    from app.models import Session as SessionModel
    
    blockchain = Blockchain()
    is_valid, invalid_blocks = blockchain.is_chain_valid()
    
    health = {
        "timestamp": datetime.utcnow().isoformat(),
        "database": {
            "status": "healthy",
            "total_users": db.query(User).count(),
            "total_voters": db.query(User).filter(User.role == 'voter').count(),
            "total_admins": db.query(User).filter(User.role.in_(['admin', 'superadmin'])).count()
        },
        "blockchain": {
            "status": "healthy" if is_valid else "corrupted",
            "is_valid": is_valid,
            "height": db.query(func.max(Vote.block_index)).scalar() or 0,
            "total_votes": db.query(Vote).count(),
            "invalid_blocks": invalid_blocks
        },
        "security": {
            "active_sessions": db.query(SessionModel).filter(
                SessionModel.is_active == True,
                SessionModel.expires_at > datetime.utcnow()
            ).count(),
            "banned_ips": db.query(func.count()).select_from(
                db.query(User).filter(User.locked_until > datetime.utcnow()).subquery()
            ).scalar()
        },
        "elections": {
            "total": db.query(Election).count(),
            "active": db.query(Election).filter(Election.status == 'open').count(),
            "draft": db.query(Election).filter(Election.status == 'draft').count()
        }
    }
    
    return health


# ==================== KILL SWITCH ====================

@router.post("/security/lock-admin/{admin_id}")
def emergency_lock_admin(
    admin_id: int,
    reason: str,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Emergency lock admin account (Kill Switch)."""
    from app.models import Session as SessionModel
    
    admin = db.query(User).filter(User.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    if admin.is_superadmin:
        raise HTTPException(status_code=403, detail="Cannot lock superadmin")
    
    # Lock account
    admin.is_active = False
    admin.locked_until = datetime.utcnow() + timedelta(days=365)
    admin.token_version += 1
    
    # Terminate all sessions
    db.query(SessionModel).filter(SessionModel.user_id == admin_id).update({
        "is_active": False
    })
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="emergency_lock_admin",
        details=f"KILL SWITCH: Locked admin {admin.email}. Reason: {reason}",
        ip_address="system"
    )
    
    db.commit()
    
    # TODO: Send SNS alert to Super Admin
    
    return {
        "success": True,
        "message": f"Admin {admin.email} locked immediately",
        "reason": reason
    }
