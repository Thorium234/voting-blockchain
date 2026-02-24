"""Super Admin routes for election lifecycle and advanced management."""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
import uuid
import json
import csv
import io

from app.database import get_db
from app.models import User, Candidate, Election, ActivityLog, Block, Vote, Session as SessionModel
from app.schemas import AdminActionResponse
from app.auth.dependencies import get_current_admin
from app.security.audit_logging import create_audit_log
from app.blockchain.chain import Blockchain

router = APIRouter(prefix="/superadmin", tags=["SuperAdmin"])


def require_superadmin(current_user: User = Depends(get_current_admin)) -> User:
    """Dependency to ensure user is superadmin."""
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required"
        )
    return current_user


# ==================== ELECTION LIFECYCLE ====================

@router.post("/election/initialize-genesis")
def initialize_genesis_block(
    election_id: str,
    title: str,
    description: Optional[str] = None,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Initialize genesis block for new election."""
    # Check if election exists
    existing = db.query(Election).filter(Election.election_id == election_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Election already exists")
    
    # Create genesis block
    blockchain = Blockchain()
    genesis = blockchain.chain[0]  # Get genesis block
    
    # Create election record
    election = Election(
        election_id=election_id,
        title=title,
        description=description,
        status='initialized',
        genesis_block_hash=genesis.hash,
        genesis_created_at=datetime.utcnow(),
        created_by=current_user.id
    )
    db.add(election)
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="initialize_genesis",
        details=f"Initialized genesis block for election: {election_id}",
        ip_address="system"
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Genesis block initialized",
        "election_id": election_id,
        "genesis_hash": genesis.hash
    }


@router.post("/election/{election_id}/open-polls")
def open_polls(
    election_id: str,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Open polls for voting."""
    election = db.query(Election).filter(Election.election_id == election_id).first()
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    
    if election.status != 'initialized':
        raise HTTPException(status_code=400, detail=f"Cannot open polls. Current status: {election.status}")
    
    election.status = 'open'
    election.polls_opened_at = datetime.utcnow()
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="open_polls",
        details=f"Opened polls for election: {election_id}",
        ip_address="system"
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Polls opened successfully",
        "opened_at": election.polls_opened_at
    }


@router.post("/election/{election_id}/close-polls")
def close_polls(
    election_id: str,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Close polls and lock blockchain."""
    election = db.query(Election).filter(Election.election_id == election_id).first()
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    
    if election.status != 'open':
        raise HTTPException(status_code=400, detail=f"Cannot close polls. Current status: {election.status}")
    
    election.status = 'closed'
    election.polls_closed_at = datetime.utcnow()
    
    # Mine any pending votes
    blockchain = Blockchain()
    blockchain.mine_pending_votes()
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="close_polls",
        details=f"Closed polls for election: {election_id}",
        ip_address="system"
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Polls closed successfully",
        "closed_at": election.polls_closed_at
    }


@router.post("/election/{election_id}/commit-results")
def commit_results(
    election_id: str,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Finalize and publish results to immutable ledger."""
    election = db.query(Election).filter(Election.election_id == election_id).first()
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    
    if election.status != 'closed':
        raise HTTPException(status_code=400, detail=f"Cannot commit results. Current status: {election.status}")
    
    # Get final results
    results = db.query(
        Vote.candidate_id,
        func.count(Vote.id).label('vote_count')
    ).group_by(Vote.candidate_id).all()
    
    # Validate blockchain
    blockchain = Blockchain()
    is_valid, _ = blockchain.is_chain_valid()
    
    if not is_valid:
        raise HTTPException(status_code=400, detail="Blockchain validation failed")
    
    election.status = 'finalized'
    election.results_finalized_at = datetime.utcnow()
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="commit_results",
        details=f"Finalized results for election: {election_id}. Total votes: {sum(r.vote_count for r in results)}",
        ip_address="system"
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Results committed successfully",
        "finalized_at": election.results_finalized_at,
        "results": [{"candidate_id": r.candidate_id, "votes": r.vote_count} for r in results],
        "blockchain_valid": is_valid
    }


@router.post("/election/{election_id}/reset")
def reset_election(
    election_id: str,
    archive: bool = True,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Archive current election and prepare for new one."""
    election = db.query(Election).filter(Election.election_id == election_id).first()
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    
    if archive:
        election.status = 'archived'
    else:
        db.delete(election)
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="reset_election",
        details=f"Reset election: {election_id}. Archived: {archive}",
        ip_address="system"
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Election {'archived' if archive else 'deleted'} successfully"
    }


# ==================== CANDIDATE MANAGEMENT ====================

@router.post("/candidate/register")
def register_candidate(
    name: str,
    party: Optional[str] = None,
    manifesto: Optional[str] = None,
    photo_url: Optional[str] = None,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Register a new candidate/aspirant."""
    candidate_id = f"CAND_{uuid.uuid4().hex[:8].upper()}"
    
    candidate = Candidate(
        candidate_id=candidate_id,
        name=name,
        party=party,
        manifesto=manifesto,
        photo_url=photo_url,
        status='pending',
        created_by=current_user.id
    )
    db.add(candidate)
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="register_candidate",
        details=f"Registered candidate: {name} ({candidate_id})",
        ip_address="system"
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Candidate registered successfully",
        "candidate_id": candidate_id,
        "name": name
    }


@router.post("/candidate/{candidate_id}/certify")
def certify_candidate(
    candidate_id: str,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Certify a candidate for election."""
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    candidate.status = 'certified'
    candidate.certified_by = current_user.id
    candidate.certified_at = datetime.utcnow()
    candidate.is_active = True
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="certify_candidate",
        details=f"Certified candidate: {candidate.name} ({candidate_id})",
        ip_address="system"
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Candidate {candidate.name} certified successfully"
    }


@router.get("/candidates")
def list_candidates(
    status: Optional[str] = None,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """List all candidates."""
    query = db.query(Candidate)
    if status:
        query = query.filter(Candidate.status == status)
    
    candidates = query.all()
    
    return {
        "candidates": [
            {
                "candidate_id": c.candidate_id,
                "name": c.name,
                "party": c.party,
                "status": c.status,
                "certified_at": c.certified_at,
                "is_active": c.is_active
            }
            for c in candidates
        ]
    }


# ==================== VOTER REGISTRATION ====================

@router.post("/voter/register")
def register_voter_flexible(
    email: str,
    password: str,
    full_name: str,
    id_number: Optional[str] = None,
    reg_number: Optional[str] = None,
    phone: Optional[str] = None,
    address: Optional[str] = None,
    custom_fields: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Register voter with flexible fields."""
    from app.auth.password import hash_password
    
    # Auto-generate voter ID
    voter_id = f"V{uuid.uuid4().hex[:10].upper()}"
    
    # Check if email exists
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=email,
        voter_id=voter_id,
        password_hash=hash_password(password),
        role='voter',
        full_name=full_name,
        id_number=id_number,
        reg_number=reg_number,
        phone=phone,
        address=address,
        custom_fields=custom_fields,
        is_active=True,
        created_by=current_user.id
    )
    db.add(user)
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="register_voter",
        details=f"Registered voter: {full_name} ({voter_id})",
        ip_address="system"
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Voter registered successfully",
        "voter_id": voter_id,
        "email": email
    }


@router.post("/voter/bulk-import")
async def bulk_import_voters(
    file: UploadFile = File(...),
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Bulk import voters from CSV."""
    from app.auth.password import hash_password
    
    content = await file.read()
    csv_file = io.StringIO(content.decode('utf-8'))
    reader = csv.DictReader(csv_file)
    
    imported = 0
    errors = []
    
    for row in reader:
        try:
            voter_id = f"V{uuid.uuid4().hex[:10].upper()}"
            
            user = User(
                email=row['email'],
                voter_id=voter_id,
                password_hash=hash_password(row.get('password', 'Voter@123')),
                role='voter',
                full_name=row.get('full_name'),
                id_number=row.get('id_number'),
                reg_number=row.get('reg_number'),
                phone=row.get('phone'),
                is_active=True,
                created_by=current_user.id
            )
            db.add(user)
            imported += 1
        except Exception as e:
            errors.append(f"Row {imported + 1}: {str(e)}")
    
    db.commit()
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="bulk_import_voters",
        details=f"Imported {imported} voters. Errors: {len(errors)}",
        ip_address="system"
    )
    
    return {
        "success": True,
        "imported": imported,
        "errors": errors
    }


# ==================== ACTIVITY MONITORING ====================

@router.get("/activity-feed")
def get_activity_feed(
    hours: int = 24,
    limit: int = 100,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Get real-time admin activity feed."""
    since = datetime.utcnow() - timedelta(hours=hours)
    
    # Get activity logs
    logs = db.query(ActivityLog).filter(
        ActivityLog.timestamp >= since
    ).order_by(desc(ActivityLog.timestamp)).limit(limit).all()
    
    # Get admin sessions
    sessions = db.query(SessionModel, User).join(User).filter(
        and_(
            User.role.in_(['admin', 'superadmin']),
            SessionModel.is_active == True,
            SessionModel.expires_at > datetime.utcnow()
        )
    ).all()
    
    activities = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first()
        activities.append({
            "admin_name": user.email if user else "System",
            "admin_role": user.role if user else "system",
            "action": log.action,
            "details": log.details,
            "timestamp": log.timestamp.isoformat(),
            "ip_address": log.ip_address,
            "status": "SUCCESS"
        })
    
    active_admins = []
    for session, user in sessions:
        active_admins.append({
            "admin_name": user.email,
            "admin_role": user.role,
            "last_active": session.last_activity_at.isoformat(),
            "ip_address": session.ip_address,
            "session_duration": str(datetime.utcnow() - session.created_at)
        })
    
    return {
        "activities": activities,
        "active_admins": active_admins,
        "total_activities": len(activities)
    }


# ==================== ANALYTICS ====================

@router.get("/analytics/dashboard")
def get_dashboard_analytics(
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Get comprehensive dashboard analytics."""
    # Voter turnout
    total_voters = db.query(User).filter(User.role == 'voter').count()
    voted_count = db.query(User).filter(and_(User.role == 'voter', User.has_voted == True)).count()
    turnout_percentage = (voted_count / total_voters * 100) if total_voters > 0 else 0
    
    # Vote distribution
    vote_distribution = db.query(
        Vote.candidate_id,
        func.count(Vote.id).label('count')
    ).group_by(Vote.candidate_id).all()
    
    # Hourly trends (last 24 hours)
    since_24h = datetime.utcnow() - timedelta(hours=24)
    hourly_votes = db.query(
        func.strftime('%H', Vote.timestamp).label('hour'),
        func.count(Vote.id).label('count')
    ).filter(Vote.timestamp >= since_24h).group_by('hour').all()
    
    # Blockchain status
    blockchain = Blockchain()
    is_valid, _ = blockchain.is_chain_valid()
    latest_block = db.query(Block).order_by(desc(Block.index)).first()
    
    return {
        "voter_turnout": {
            "total_registered": total_voters,
            "total_voted": voted_count,
            "percentage": round(turnout_percentage, 2)
        },
        "vote_distribution": [
            {"candidate_id": v.candidate_id, "votes": v.count}
            for v in vote_distribution
        ],
        "hourly_trends": [
            {"hour": h.hour, "votes": h.count}
            for h in hourly_votes
        ],
        "blockchain_status": {
            "is_valid": is_valid,
            "height": latest_block.index if latest_block else 0,
            "latest_hash": latest_block.hash if latest_block else None,
            "merkle_root": latest_block.merkle_root if latest_block else None
        },
        "system_stats": {
            "total_admins": db.query(User).filter(User.role.in_(['admin', 'superadmin'])).count(),
            "total_candidates": db.query(Candidate).filter(Candidate.is_active == True).count(),
            "active_sessions": db.query(SessionModel).filter(
                and_(SessionModel.is_active == True, SessionModel.expires_at > datetime.utcnow())
            ).count()
        }
    }


# ==================== ADMIN MANAGEMENT ====================

@router.get("/admins")
def list_admins(
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """List all admins with activity details."""
    admins = db.query(User).filter(User.role.in_(['admin', 'superadmin'])).all()
    
    result = []
    for admin in admins:
        last_session = db.query(SessionModel).filter(
            SessionModel.user_id == admin.id
        ).order_by(desc(SessionModel.last_activity_at)).first()
        
        result.append({
            "id": admin.id,
            "email": admin.email,
            "role": admin.role,
            "is_deletable": admin.is_deletable,
            "last_login": admin.last_login_at.isoformat() if admin.last_login_at else None,
            "last_login_ip": admin.last_login_ip,
            "last_activity": last_session.last_activity_at.isoformat() if last_session else None,
            "is_active": admin.is_active,
            "created_at": admin.created_at.isoformat()
        })
    
    return {"admins": result}


@router.delete("/admin/{admin_id}")
def delete_admin(
    admin_id: int,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Delete an admin (cannot delete superadmin)."""
    admin = db.query(User).filter(User.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    if not admin.is_deletable or admin.is_superadmin:
        raise HTTPException(status_code=403, detail="Cannot delete this admin")
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="delete_admin",
        details=f"Deleted admin: {admin.email}",
        ip_address="system"
    )
    
    db.delete(admin)
    db.commit()
    
    return {"success": True, "message": "Admin deleted successfully"}


# ==================== FIELD CONFIGURATION ====================

@router.post("/election/{election_id}/configure-fields")
def configure_voter_fields(
    election_id: str,
    fields_config: Dict[str, Any],
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Configure voter registration fields for election."""
    election = db.query(Election).filter(Election.election_id == election_id).first()
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    
    election.voter_fields_config = fields_config
    db.commit()
    
    return {
        "success": True,
        "message": "Voter fields configured successfully",
        "config": fields_config
    }
