"""Public aspirant registration routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.database import get_db
from app.models import Candidate, User
from app.auth.dependencies import get_current_admin
from app.security.audit_logging import create_audit_log

router = APIRouter(prefix="/aspirant", tags=["Aspirant"])


@router.post("/register")
def register_as_aspirant(
    name: str,
    party: str = None,
    manifesto: str = None,
    email: str = None,
    phone: str = None,
    db: Session = Depends(get_db)
):
    """Public endpoint for aspirant self-registration."""
    candidate_id = f"CAND_{uuid.uuid4().hex[:8].upper()}"
    
    candidate = Candidate(
        candidate_id=candidate_id,
        name=name,
        party=party,
        manifesto=manifesto,
        status='pending',
        is_active=False
    )
    db.add(candidate)
    db.commit()
    
    return {
        "success": True,
        "message": "Application submitted successfully. Awaiting admin approval.",
        "candidate_id": candidate_id,
        "status": "pending"
    }


@router.get("/pending")
def get_pending_aspirants(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all pending aspirant applications (admin only)."""
    pending = db.query(Candidate).filter(Candidate.status == 'pending').all()
    
    return {
        "pending_aspirants": [
            {
                "candidate_id": c.candidate_id,
                "name": c.name,
                "party": c.party,
                "manifesto": c.manifesto,
                "created_at": c.created_at.isoformat()
            }
            for c in pending
        ]
    }


@router.post("/{candidate_id}/approve")
def approve_aspirant(
    candidate_id: str,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Approve pending aspirant (admin/superadmin only)."""
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Aspirant not found")
    
    if candidate.status != 'pending':
        raise HTTPException(status_code=400, detail=f"Aspirant already {candidate.status}")
    
    candidate.status = 'certified'
    candidate.certified_by = current_user.id
    candidate.certified_at = datetime.utcnow()
    candidate.is_active = True
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="approve_aspirant",
        details=f"Approved aspirant: {candidate.name} ({candidate_id})",
        ip_address="system"
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Aspirant {candidate.name} approved successfully",
        "candidate_id": candidate_id
    }


@router.post("/{candidate_id}/reject")
def reject_aspirant(
    candidate_id: str,
    reason: str = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Reject pending aspirant (admin/superadmin only)."""
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Aspirant not found")
    
    if candidate.status != 'pending':
        raise HTTPException(status_code=400, detail=f"Aspirant already {candidate.status}")
    
    candidate.status = 'rejected'
    candidate.is_active = False
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="reject_aspirant",
        details=f"Rejected aspirant: {candidate.name} ({candidate_id}). Reason: {reason}",
        ip_address="system"
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Aspirant {candidate.name} rejected",
        "candidate_id": candidate_id
    }
