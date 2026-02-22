"""Block structure for the blockchain."""
import json
from datetime import datetime
from typing import List, Optional
import hashlib


class Block:
    """Represents a single block in the blockchain."""
    
    def __init__(
        self,
        index: int,
        timestamp: datetime,
        votes: List[dict],
        previous_hash: str,
        nonce: int = 0,
        hash: Optional[str] = None
    ):
        self.index = index
        self.timestamp = timestamp
        self.votes = votes  # List of vote transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = hash or self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate SHA-256 hash of the block."""
        # Create a deterministic string representation
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp),
            "votes": self.votes,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def to_dict(self) -> dict:
        """Convert block to dictionary."""
        return {
            "index": self.index,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp),
            "votes": self.votes,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Block":
        """Create block from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        
        return cls(
            index=data["index"],
            timestamp=timestamp,
            votes=data.get("votes", []),
            previous_hash=data["previous_hash"],
            nonce=data.get("nonce", 0),
            hash=data.get("hash")
        )
    
    def __repr__(self) -> str:
        return f"<Block(index={self.index}, hash={self.hash[:16]}...)>"


class VoteTransaction:
    """Represents a single vote transaction."""
    
    def __init__(
        self,
        voter_id: str,
        candidate_id: str,
        timestamp: Optional[datetime] = None,
        signature: Optional[str] = None
    ):
        self.voter_id = voter_id
        self.candidate_id = candidate_id
        self.timestamp = timestamp or datetime.utcnow()
        self.signature = signature
    
    def to_dict(self) -> dict:
        """Convert transaction to dictionary."""
        return {
            "voter_id": self.voter_id,
            "candidate_id": self.candidate_id,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp),
            "signature": self.signature
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "VoteTransaction":
        """Create transaction from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        
        return cls(
            voter_id=data["voter_id"],
            candidate_id=data["candidate_id"],
            timestamp=timestamp,
            signature=data.get("signature")
        )
    
    def calculate_transaction_hash(self) -> str:
        """Calculate hash of this transaction."""
        tx_data = {
            "voter_id": self.voter_id,
            "candidate_id": self.candidate_id,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp)
        }
        tx_string = json.dumps(tx_data, sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()
    
    def __repr__(self) -> str:
        return f"<VoteTransaction(voter_id={self.voter_id}, candidate={self.candidate_id})>"
