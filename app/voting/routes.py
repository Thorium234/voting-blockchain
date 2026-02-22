"""Voting routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Vote, Block as BlockModel, ActivityLog
from app.schemas import VoteCreate, VoteResponse, VotingResults, VoteResult, BlockchainResponse, BlockResponse, ChainValidation
from app.auth.dependencies import get_current_user, get_client_ip
from app.blockchain.chain import Blockchain
from app.blockchain.block import VoteTransaction
import app.blockchain.chain as blockchain_module
import json

router = APIRouter(prefix="/voting", tags=["Voting"])

# Global blockchain instance (in production, store in database)
_blockchain = None


def get_blockchain() -> Blockchain:
    """Get or create blockchain instance."""
    global _blockchain
    if _blockchain is None:
        _blockchain = Blockchain()
        # Load existing blocks from database
        load_blocks_from_db()
    return _blockchain


def load_blocks_from_db(db: Session = None):
    """Load blocks from database into memory."""
    global _blockchain
    if _blockchain is None:
        return
    
    blocks = db.query(BlockModel).order_by(BlockModel.index).all() if db else []
    if blocks:
        _blockchain.chain = []


@router.post("/vote", status_code=status.HTTP_201_CREATED)
def cast_vote(
    vote_data: VoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cast a vote."""
    # Check if user has already voted
    if current_user.has_voted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already cast your vote"
        )
    
    # Check blockchain for double voting
    blockchain = get_blockchain()
    if blockchain.has_voted(current_user.voter_id):
        # Update user record
        current_user.has_voted = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This voter ID has already been used"
        )
    
    # Create vote transaction
    vote = VoteTransaction(
        voter_id=current_user.voter_id,
        candidate_id=vote_data.candidate_id,
        signature=vote_data.signature
    )
    
    # Add to blockchain
    blockchain.add_vote(vote)
    
    # Mine block immediately (for simplicity)
    new_block = blockchain.mine_pending_votes()
    
    if new_block:
        # Store block in database
        db_block = BlockModel(
            index=new_block.index,
            timestamp=new_block.timestamp,
            votes_data=json.dumps(new_block.votes),
            previous_hash=new_block.previous_hash,
            nonce=new_block.nonce,
            hash=new_block.hash
        )
        db.add(db_block)
        
        # Store individual votes
        for vote_dict in new_block.votes:
            vote_record = Vote(
                voter_id=current_user.id,
                candidate_id=vote_dict.get("candidate_id"),
                timestamp=new_block.timestamp,
                block_index=new_block.index,
                transaction_hash=vote.calculate_transaction_hash(),
                signature=vote_dict.get("signature")
            )
            db.add(vote_record)
    
    # Mark user as voted
    current_user.has_voted = True
    
    # Log activity
    log = ActivityLog(
        user_id=current_user.id,
        action="vote",
        details=f"Voted for candidate: {vote_data.candidate_id}",
        ip_address=get_client_ip(db)
    )
    db.add(log)
    
    db.commit()
    
    return {
        "message": "Vote cast successfully",
        "candidate_id": vote_data.candidate_id,
        "block_index": new_block.index if new_block else None
    }


@router.get("/results", response_model=VotingResults)
def get_results(db: Session = Depends(get_db)):
    """Get voting results."""
    blockchain = get_blockchain()
    
    # Get vote counts from blockchain
    vote_counts = blockchain.get_vote_count()
    total_votes = sum(vote_counts.values())
    
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
    
    return VotingResults(
        total_votes=total_votes,
        results=results,
        blockchain_height=len(blockchain)
    )


@router.get("/blockchain", response_model=BlockchainResponse)
def get_blockchain_view(db: Session = Depends(get_db)):
    """View the blockchain."""
    blockchain = get_blockchain()
    
    blocks = [
        BlockResponse(
            index=block.index,
            timestamp=block.timestamp,
            votes_count=len(block.votes),
            previous_hash=block.previous_hash,
            nonce=block.nonce,
            hash=block.hash
        )
        for block in blockchain.chain
    ]
    
    is_valid, _ = blockchain.is_chain_valid()
    
    return BlockchainResponse(
        blocks=blocks,
        height=len(blockchain),
        is_valid=is_valid
    )


@router.get("/blockchain/validate", response_model=ChainValidation)
def validate_blockchain(db: Session = Depends(get_db)):
    """Validate blockchain integrity."""
    blockchain = get_blockchain()
    is_valid, invalid_blocks = blockchain.is_chain_valid()
    
    message = "Blockchain is valid" if is_valid else f"Found {len(invalid_blocks)} invalid block(s)"
    
    return ChainValidation(
        is_valid=is_valid,
        invalid_blocks=invalid_blocks,
        message=message
    )


@router.get("/check-voted")
def check_voted(current_user: User = Depends(get_current_user)):
    """Check if current user has voted."""
    blockchain = get_blockchain()
    blockchain_voted = blockchain.has_voted(current_user.voter_id)
    
    return {
        "has_voted": current_user.has_voted or blockchain_voted,
        "voter_id": current_user.voter_id
    }
