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
    location: str,
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
        location=location,
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



# ==================== LOCATION-BASED ANALYTICS ====================

@router.get("/analytics/location-breakdown")
def get_location_breakdown(
    seat_id: str = None,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Get vote breakdown by location for each seat."""
    from sqlalchemy import and_
    
    query = db.query(
        Vote.seat_id,
        Vote.candidate_id,
        User.location,
        func.count(Vote.id).label('vote_count')
    ).join(User, Vote.voter_id == User.id)
    
    if seat_id:
        query = query.filter(Vote.seat_id == seat_id)
    
    results = query.group_by(Vote.seat_id, Vote.candidate_id, User.location).all()
    
    # Organize by seat -> candidate -> location
    breakdown = {}
    for r in results:
        seat_key = r.seat_id or 'general'
        if seat_key not in breakdown:
            breakdown[seat_key] = {}
        if r.candidate_id not in breakdown[seat_key]:
            breakdown[seat_key][r.candidate_id] = {}
        breakdown[seat_key][r.candidate_id][r.location or 'Unknown'] = r.vote_count
    
    return {"location_breakdown": breakdown}


@router.get("/analytics/comprehensive")
def get_comprehensive_analytics(
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Complete analytics dashboard data."""
    from datetime import timedelta
    
    # Voter turnout by location
    location_turnout = db.query(
        User.location,
        func.count(User.id).label('total_voters'),
        func.sum(func.cast(User.has_voted, Integer)).label('voted_count')
    ).filter(User.role == 'voter').group_by(User.location).all()
    
    # Hourly voting trends
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    hourly_votes = db.query(
        func.strftime('%H', Vote.timestamp).label('hour'),
        func.count(Vote.id).label('count')
    ).filter(Vote.timestamp >= last_24h).group_by('hour').all()
    
    # Seat-wise results
    seat_results = db.query(
        ElectionSeat.seat_name,
        Vote.candidate_id,
        Candidate.name,
        func.count(Vote.id).label('votes')
    ).join(Vote, Vote.seat_id == ElectionSeat.id
    ).join(Candidate, Candidate.candidate_id == Vote.candidate_id
    ).group_by(ElectionSeat.seat_name, Vote.candidate_id, Candidate.name).all()
    
    return {
        "location_turnout": [
            {
                "location": lt.location or "Unknown",
                "total_voters": lt.total_voters,
                "voted": lt.voted_count or 0,
                "percentage": round((lt.voted_count or 0) / lt.total_voters * 100, 2) if lt.total_voters > 0 else 0
            }
            for lt in location_turnout
        ],
        "hourly_trends": [
            {"hour": h.hour, "votes": h.count}
            for h in hourly_votes
        ],
        "seat_results": [
            {
                "seat": sr.seat_name,
                "candidate_id": sr.candidate_id,
                "candidate_name": sr.name,
                "votes": sr.votes
            }
            for sr in seat_results
        ]
    }


@router.get("/reports/summary")
def generate_summary_report(
    election_id: str,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Generate comprehensive election summary report."""
    election = db.query(Election).filter(Election.election_id == election_id).first()
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    
    # Get all seats
    seats = db.query(ElectionSeat).filter(ElectionSeat.election_id == election.id).all()
    
    report = {
        "election_id": election_id,
        "title": election.title,
        "status": election.status,
        "generated_at": datetime.utcnow().isoformat(),
        "seats": []
    }
    
    for seat in seats:
        # Get results for this seat
        results = db.query(
            Candidate.candidate_id,
            Candidate.name,
            Candidate.party,
            func.count(Vote.id).label('total_votes')
        ).join(
            SeatAspirant, SeatAspirant.candidate_id == Candidate.id
        ).outerjoin(
            Vote, and_(Vote.candidate_id == Candidate.candidate_id, Vote.seat_id == seat.id)
        ).filter(
            SeatAspirant.seat_id == seat.id
        ).group_by(Candidate.candidate_id, Candidate.name, Candidate.party).all()
        
        # Location breakdown for this seat
        location_breakdown = db.query(
            User.location,
            Vote.candidate_id,
            func.count(Vote.id).label('votes')
        ).join(
            Vote, Vote.voter_id == User.id
        ).filter(
            Vote.seat_id == seat.id
        ).group_by(User.location, Vote.candidate_id).all()
        
        # Organize location data
        location_data = {}
        for lb in location_breakdown:
            loc = lb.location or "Unknown"
            if loc not in location_data:
                location_data[loc] = {}
            location_data[loc][lb.candidate_id] = lb.votes
        
        seat_report = {
            "seat_name": seat.seat_name,
            "total_votes": sum(r.total_votes for r in results),
            "candidates": [
                {
                    "candidate_id": r.candidate_id,
                    "name": r.name,
                    "party": r.party,
                    "votes": r.total_votes,
                    "percentage": round(r.total_votes / sum(x.total_votes for x in results) * 100, 2) if sum(x.total_votes for x in results) > 0 else 0
                }
                for r in results
            ],
            "location_breakdown": location_data
        }
        
        report["seats"].append(seat_report)
    
    return report



# ==================== IP MANAGEMENT ====================

@router.get("/security/banned-ips")
def get_all_banned_ips(
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Get all banned IPs including expired ones."""
    from app.models import IPBlacklist
    
    bans = db.query(IPBlacklist).order_by(desc(IPBlacklist.created_at)).all()
    
    return {
        "banned_ips": [
            {
                "ip_address": ban.ip_address,
                "banned_until": ban.banned_until.isoformat(),
                "reason": ban.reason,
                "failed_attempts": ban.failed_attempts,
                "ban_type": ban.ban_type,
                "is_active": ban.banned_until > datetime.utcnow(),
                "created_at": ban.created_at.isoformat()
            }
            for ban in bans
        ]
    }


@router.post("/security/unban-ip/{ip_address}")
def superadmin_unban_ip(
    ip_address: str,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Superadmin can unban any IP address."""
    from app.models import IPBlacklist
    
    ban = db.query(IPBlacklist).filter(IPBlacklist.ip_address == ip_address).first()
    
    if not ban:
        raise HTTPException(status_code=404, detail="IP not found in ban list")
    
    # Delete the ban record
    db.delete(ban)
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="unban_ip",
        details=f"Superadmin unbanned IP: {ip_address}. Reason: {ban.reason}",
        ip_address="system"
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": f"IP {ip_address} has been unbanned",
        "ip": ip_address
    }


@router.post("/security/unban-all-ips")
def unban_all_ips(
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Superadmin can unban all IPs at once."""
    from app.models import IPBlacklist
    
    count = db.query(IPBlacklist).count()
    db.query(IPBlacklist).delete()
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="unban_all_ips",
        details=f"Superadmin unbanned all {count} IPs",
        ip_address="system"
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": f"All {count} banned IPs have been cleared",
        "count": count
    }
