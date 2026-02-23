"""Voting routes with anti-replay protection and vote integrity."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
import time

from app.database import get_db
from app.models import User, Vote, Block as BlockModel, ActivityLog
from app.schemas import VoteCreate, VoteResponse, VotingResults, VoteResult, BlockchainResponse, BlockResponse, ChainValidation
from app.auth.dependencies import get_current_user, get_client_ip
from app.blockchain.chain import Blockchain
from app.blockchain.block import VoteTransaction
from app.security.anti_replay import (
    validate_vote_nonce,
    record_used_nonce,
    validate_timestamp,
    check_double_voting,
    hash_vote_payload,
    generate_nonce
)
from app.security.audit_logging import create_audit_log, log_vote_cast
import json

router = APIRouter(prefix="/voting", tags=["Voting"])

# Global blockchain instance
_blockchain = None


def get_blockchain() -> Blockchain:
    """Get or create blockchain instance."""
    global _blockchain
    if _blockchain is None:
        _blockchain = Blockchain()
    return _blockchain


@router.post("/vote", status_code=status.HTTP_201_CREATED)
def cast_vote(
    vote_data: VoteCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cast a vote with full anti-replay protection.
    
    Security measures:
    - Nonce validation (prevent replay)
    - Timestamp validation (reject old votes)
    - Vote payload hashing before storage
    - Double voting prevention (database + blockchain)
    """
    client_ip = get_client_ip(request)
    
    # Check if user has already voted (database check)
    if current_user.has_voted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already cast your vote"
        )
    
    # Check blockchain for double voting
    blockchain = get_blockchain()
    if blockchain.has_voted(current_user.voter_id):
        # Update user record to sync
        current_user.has_voted = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This voter ID has already been used"
        )
    
    # Check for pending/in-progress voting
    has_pending, pending_info = check_double_voting(db, current_user.id)
    if has_pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pending vote detected: {pending_info}"
        )
    
    # Validate timestamp
    timestamp_valid, timestamp_error = validate_timestamp(vote_data.timestamp)
    if not timestamp_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Timestamp validation failed: {timestamp_error}"
        )
    
    # Create vote payload hash (for integrity)
    vote_payload_hash = hash_vote_payload(
        voter_id=current_user.voter_id,
        candidate_id=vote_data.candidate_id,
        nonce=vote_data.nonce,
        timestamp=vote_data.timestamp
    )
    
    # Validate nonce (anti-replay)
    nonce_valid, nonce_error = validate_vote_nonce(
        db=db,
        voter_id=current_user.id,
        nonce=vote_data.nonce,
        vote_hash=vote_payload_hash,
        ip_address=client_ip
    )
    
    if not nonce_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nonce validation failed: {nonce_error}"
        )
    
    # Create vote transaction
    vote = VoteTransaction(
        voter_id=current_user.voter_id,
        candidate_id=vote_data.candidate_id,
        nonce=vote_data.nonce,
        signature=vote_data.signature,
        timestamp_unix=vote_data.timestamp
    )
    
    # Calculate transaction hash
    transaction_hash = vote.calculate_transaction_hash()
    
    # Add to blockchain
    blockchain.add_vote(vote)
    
    # Mine block immediately
    new_block = blockchain.mine_pending_votes()
    
    if new_block:
        # Store block in database
        db_block = BlockModel(
            index=new_block.index,
            timestamp=new_block.timestamp,
            votes_data=json.dumps(new_block.votes),
            previous_hash=new_block.previous_hash,
            nonce=new_block.nonce,
            hash=new_block.hash,
            merkle_root=new_block.merkle_root,
            validator=new_block.validator
        )
        db.add(db_block)
        
        # Store individual votes with full verification data
        for vote_dict in new_block.votes:
            vote_record = Vote(
                voter_id=current_user.id,
                candidate_id=vote_dict.get("candidate_id"),
                timestamp=new_block.timestamp,
                block_index=new_block.index,
                transaction_hash=transaction_hash,
                signature=vote_dict.get("signature"),
                nonce=vote_dict.get("nonce"),
                vote_payload_hash=vote_payload_hash,
                is_verified=True
            )
            db.add(vote_record)
    
    # Mark user as voted
    current_user.has_voted = True
    
    # Record nonce for anti-replay
    record_used_nonce(
        db=db,
        voter_id=current_user.id,
        nonce=vote_data.nonce,
        vote_hash=vote_payload_hash,
        ip_address=client_ip
    )
    
    # Audit log
    log_vote_cast(
        db=db,
        voter_id=current_user.id,
        candidate_id=vote_data.candidate_id,
        ip_address=client_ip,
        block_index=new_block.index if new_block else 0,
        transaction_hash=transaction_hash
    )
    
    db.commit()
    
    return {
        "message": "Vote cast successfully",
        "candidate_id": vote_data.candidate_id,
        "block_index": new_block.index if new_block else None,
        "transaction_hash": transaction_hash,
        "merkle_root": new_block.merkle_root if new_block else None
    }


@router.get("/results", response_model=VotingResults)
def get_results(db: Session = Depends(get_db)):
    """Get voting results with chain verification."""
    blockchain = get_blockchain()
    
    # Validate chain first
    is_valid, invalid_blocks = blockchain.is_chain_valid()
    
    # Get vote counts from blockchain
    vote_counts = blockchain.get_vote_count()
    total_votes = blockchain.get_total_votes()
    
    # Convert to response format
    results = [
        VoteResult(
            candidate_id=candidate_id,
            vote_count=count,
            percentage=round((count / total_votes * 100) if total_votes > 0 else 0, 2)
        )
        for candidate_id, count in vote_counts.items()
    ]
    
    # Sort by vote count descending
    results.sort(key=lambda x: x.vote_count, reverse=True)
    
    # Get latest merkle root
    latest_block = blockchain.get_latest_block()
    merkle_root = latest_block.merkle_root if latest_block else None
    
    return VotingResults(
        total_votes=total_votes,
        results=results,
        blockchain_height=len(blockchain),
        chain_valid=is_valid,
        merkle_root=merkle_root
    )


@router.get("/blockchain", response_model=BlockchainResponse)
def get_blockchain_view(db: Session = Depends(get_db)):
    """View the blockchain with full verification data."""
    blockchain = get_blockchain()
    
    blocks = [
        BlockResponse(
            index=block.index,
            timestamp=block.timestamp,
            votes_count=len(block.votes),
            previous_hash=block.previous_hash,
            nonce=block.nonce,
            hash=block.hash,
            merkle_root=block.merkle_root,
            is_checkpoint=False
        )
        for block in blockchain.chain
    ]
    
    is_valid, _ = blockchain.is_chain_valid()
    total_votes = blockchain.get_total_votes()
    
    latest_block = blockchain.get_latest_block()
    latest_merkle = latest_block.merkle_root if latest_block else None
    
    return BlockchainResponse(
        blocks=blocks,
        height=len(blockchain),
        is_valid=is_valid,
        total_votes=total_votes,
        latest_merkle_root=latest_merkle
    )


@router.get("/blockchain/validate", response_model=ChainValidation)
def validate_blockchain(db: Session = Depends(get_db)):
    """Validate blockchain integrity with detailed report."""
    blockchain = get_blockchain()
    is_valid, invalid_blocks = blockchain.is_chain_valid()
    
    # Check checkpoints
    checkpoint_valid = True
    if blockchain.checkpoints:
        checkpoint_valid = all(
            blockchain.verify_checkpoint(idx) 
            for idx in blockchain.checkpoints
        )
    
    message = "Blockchain is valid" if is_valid else f"Found {len(invalid_blocks)} invalid block(s)"
    
    return ChainValidation(
        is_valid=is_valid,
        invalid_blocks=invalid_blocks,
        message=message,
        checkpoint_valid=checkpoint_valid
    )


@router.get("/block/{index}")
def get_block(index: int, db: Session = Depends(get_db)):
    """Get a specific block by index."""
    blockchain = get_blockchain()
    block = blockchain.get_block_by_index(index)
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block {index} not found"
        )
    
    return block.to_dict()


@router.get("/block-by-hash/{block_hash}")
def get_block_by_hash(block_hash: str, db: Session = Depends(get_db)):
    """Get a specific block by hash."""
    blockchain = get_blockchain()
    block = blockchain.get_block_by_hash(block_hash)
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with hash {block_hash} not found"
        )
    
    return block.to_dict()


@router.get("/vote-proof/{voter_id}")
def get_vote_proof(voter_id: str, db: Session = Depends(get_db)):
    """Get vote proof for a voter (merkle proof)."""
    blockchain = get_blockchain()
    
    # Find the vote
    for block in blockchain.chain:
        for i, vote in enumerate(block.votes):
            if vote.get("voter_id") == voter_id:
                merkle_proof = block.get_merkle_proof(vote)
                
                return {
                    "found": True,
                    "voter_id": voter_id,
                    "block_index": block.index,
                    "block_hash": block.hash,
                    "merkle_root": block.merkle_root,
                    "merkle_proof": merkle_proof,
                    "vote": vote
                }
    
    return {"found": False, "message": "No vote found for this voter"}


@router.get("/check-voted")
def check_voted(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Check if current user has voted."""
    blockchain = get_blockchain()
    blockchain_voted = blockchain.has_voted(current_user.voter_id)
    
    return {
        "has_voted": current_user.has_voted or blockchain_voted,
        "voter_id": current_user.voter_id
    }


@router.get("/nonce")
def get_nonce(current_user: User = Depends(get_current_user)):
    """Get a fresh nonce for voting."""
    return {
        "nonce": generate_nonce(),
        "timestamp": int(time.time()),
        "expires_in": 300  # 5 minutes
    }
