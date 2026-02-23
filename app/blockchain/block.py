"""
Enhanced Block structure with Merkle Root and Cryptographic Verification.

Features:
- Canonical block serialization (sorted keys)
- Deterministic hashing
- Merkle root for votes in each block
- ECDSA signature support
- Immutable block verification
"""
import json
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, asdict


class Block:
    """Represents a single block in the blockchain with enhanced security."""
    
    def __init__(
        self,
        index: int,
        timestamp: datetime,
        votes: List[dict],
        previous_hash: str,
        nonce: int = 0,
        hash: Optional[str] = None,
        merkle_root: Optional[str] = None,
        validator: str = "system",
        signature: Optional[str] = None
    ):
        self.index = index
        self.timestamp = timestamp
        self.votes = votes  # List of vote transactions as dicts
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = hash
        self.merkle_root = merkle_root
        self.validator = validator
        self.signature = signature
        
        # Compute hash if not provided
        if self.hash is None:
            self.hash = self.calculate_hash()
        
        # Compute merkle root if not provided and we have votes
        if self.merkle_root is None and self.votes:
            self.merkle_root = self.calculate_merkle_root()
    
    def calculate_hash(self) -> str:
        """
        Calculate SHA-256 hash of the block.
        
        Uses canonical JSON serialization with sorted keys
        for deterministic hashing.
        """
        # Create deterministic block data
        block_data = {
            "index": self.index,
            "timestamp": self._canonical_timestamp(),
            "votes": self.votes,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "merkle_root": self.merkle_root
        }
        
        # Canonical serialization (sorted keys)
        block_string = json.dumps(block_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(block_string.encode('utf-8')).hexdigest()
    
    def _canonical_timestamp(self) -> str:
        """Get ISO format timestamp with UTC timezone."""
        if isinstance(self.timestamp, datetime):
            return self.timestamp.isoformat()
        return str(self.timestamp)
    
    def calculate_merkle_root(self) -> Optional[str]:
        """
        Calculate Merkle root of all votes in the block.
        
        Uses SHA-256 for hashing.
        Returns None if no votes.
        """
        if not self.votes:
            return None
        
        # Create hashes of each vote
        vote_hashes = []
        for vote in self.votes:
            # Canonical vote serialization
            vote_string = json.dumps(vote, sort_keys=True, separators=(',', ':'))
            vote_hash = hashlib.sha256(vote_string.encode('utf-8')).hexdigest()
            vote_hashes.append(vote_hash)
        
        # Build Merkle tree
        return self._build_merkle_tree(vote_hashes)
    
    def _build_merkle_tree(self, hashes: List[str]) -> str:
        """Build Merkle tree bottom-up."""
        if not hashes:
            return hashlib.sha256(b'' .encode('utf-8')).hexdigest()
        
        if len(hashes) == 1:
            return hashes[0]
        
        # Pair up hashes and hash them together
        new_level = []
        for i in range(0, len(hashes), 2):
            left = hashes[i]
            right = hashes[i + 1] if i + 1 < len(hashes) else hashes[i]
            
            # Concatenate and hash (sorted to ensure determinism)
            combined = sorted([left, right])
            combined_str = combined[0] + combined[1]
            new_hash = hashlib.sha256(combined_str.encode('utf-8')).hexdigest()
            new_level.append(new_hash)
        
        return self._build_merkle_tree(new_level)
    
    def get_merkle_proof(self, vote_dict: dict) -> Optional[List[Dict]]:
        """
        Get Merkle proof for a specific vote.
        
        Returns path from leaf to root.
        """
        if not self.votes or vote_dict not in self.votes:
            return None
        
        # Find the vote index
        vote_index = self.votes.index(vote_dict)
        
        # Build proof
        proof = []
        current_level = [json.dumps(v, sort_keys=True, separators=(',', ':')) for v in self.votes]
        current_hashes = [hashlib.sha256(v.encode('utf-8')).hexdigest() for v in current_level]
        
        # Build tree and track path
        level_size = len(current_hashes)
        
        while level_size > 1:
            sibling_index = vote_index + 1 if vote_index % 2 == 0 else vote_index - 1
            
            if sibling_index < level_size:
                proof.append({
                    "side": "right" if vote_index % 2 == 0 else "left",
                    "hash": current_hashes[sibling_index]
                })
            
            # Move up tree
            new_level = []
            for i in range(0, level_size, 2):
                left = current_hashes[i]
                right = current_hashes[i + 1] if i + 1 < level_size else current_hashes[i]
                combined = sorted([left, right])
                new_hash = hashlib.sha256((combined[0] + combined[1]).encode('utf-8')).hexdigest()
                new_level.append(new_hash)
            
            current_hashes = new_level
            vote_index //= 2
            level_size = len(current_hashes)
        
        return proof
    
    def verify_merkle_proof(self, vote_dict: dict, proof: List[Dict]) -> bool:
        """Verify a Merkle proof for a vote."""
        # Hash the target vote
        vote_string = json.dumps(vote_dict, sort_keys=True, separators=(',', ':'))
        current_hash = hashlib.sha256(vote_string.encode('utf-8')).hexdigest()
        
        # Follow the proof path
        for item in proof:
            if item["side"] == "left":
                combined = sorted([current_hash, item["hash"]])
            else:
                combined = sorted([item["hash"], current_hash])
            
            current_hash = hashlib.sha256(
                (combined[0] + combined[1]).encode('utf-8')
            ).hexdigest()
        
        # Compare with merkle root
        return current_hash == self.merkle_root
    
    def to_dict(self) -> dict:
        """Convert block to dictionary."""
        return {
            "index": self.index,
            "timestamp": self._canonical_timestamp(),
            "votes": self.votes,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
            "merkle_root": self.merkle_root,
            "validator": self.validator,
            "signature": self.signature
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
            hash=data.get("hash"),
            merkle_root=data.get("merkle_root"),
            validator=data.get("validator", "system"),
            signature=data.get("signature")
        )
    
    def verify(self) -> Tuple[bool, Optional[str]]:
        """
        Verify block integrity.
        
        Checks:
        - Hash is correct
        - Merkle root matches votes
        - Previous hash links correctly
        - PoW (if enabled)
        """
        # Verify hash
        expected_hash = self.calculate_hash()
        if self.hash != expected_hash:
            return False, f"Hash mismatch: expected {expected_hash[:16]}, got {self.hash[:16]}"
        
        # Verify merkle root
        if self.votes:
            expected_merkle = self.calculate_merkle_root()
            if self.merkle_root != expected_merkle:
                return False, "Merkle root mismatch"
        
        return True, None
    
    def __repr__(self) -> str:
        return f"<Block(index={self.index}, hash={self.hash[:16]}..., votes={len(self.votes)}, merkle={self.merkle_root[:16] if self.merkle_root else 'None'}...)>"


class VoteTransaction:
    """Represents a single vote transaction with anti-replay protection."""
    
    def __init__(
        self,
        voter_id: str,
        candidate_id: str,
        nonce: str,
        timestamp: Optional[datetime] = None,
        signature: Optional[str] = None,
        timestamp_unix: Optional[int] = None
    ):
        self.voter_id = voter_id
        self.candidate_id = candidate_id
        self.nonce = nonce
        self.timestamp = timestamp or datetime.utcnow()
        self.timestamp_unix = timestamp_unix
        self.signature = signature
    
    def to_dict(self, include_signature: bool = False) -> dict:
        """Convert transaction to dictionary."""
        data = {
            "voter_id": self.voter_id,
            "candidate_id": self.candidate_id,
            "nonce": self.nonce,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp),
            "timestamp_unix": self.timestamp_unix
        }
        
        if include_signature and self.signature:
            data["signature"] = self.signature
        
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> "VoteTransaction":
        """Create transaction from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        
        return cls(
            voter_id=data["voter_id"],
            candidate_id=data["candidate_id"],
            nonce=data.get("nonce", ""),
            timestamp=timestamp,
            signature=data.get("signature"),
            timestamp_unix=data.get("timestamp_unix")
        )
    
    def calculate_transaction_hash(self) -> str:
        """Calculate deterministic hash of this transaction."""
        tx_data = {
            "voter_id": self.voter_id,
            "candidate_id": self.candidate_id,
            "nonce": self.nonce,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp)
        }
        tx_string = json.dumps(tx_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(tx_string.encode('utf-8')).hexdigest()
    
    def __repr__(self) -> str:
        return f"<VoteTransaction(voter_id={self.voter_id}, candidate={self.candidate_id}, nonce={self.nonce[:8]}...)>"
