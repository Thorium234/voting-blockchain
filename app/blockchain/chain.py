"""
Enhanced Blockchain Chain Management with Checkpointing.

Features:
- Canonical block serialization
- Merkle tree integration
- Chain checkpointing
- Enhanced validation
- Deterministic operations
"""
import json
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session

from app.blockchain.block import Block, VoteTransaction
from app.config import get_settings

settings = get_settings()


class Blockchain:
    """
    Manages the blockchain structure and validation.
    
    Security features:
    - Deterministic hashing
    - Merkle root verification
    - Chain checkpointing
    - Tamper detection
    """
    
    DIFFICULTY = 2  # Number of leading zeros required in hash
    
    def __init__(self):
        self.chain: List[Block] = []
        self.pending_votes: List[VoteTransaction] = []
        self.checkpoints: Dict[int, str] = {}  # index -> checkpoint hash
        self.create_genesis_block()
    
    def create_genesis_block(self) -> Block:
        """Create the first block in the chain."""
        genesis_block = Block(
            index=0,
            timestamp=datetime.utcnow(),
            votes=[],
            previous_hash="0" * 64,
            nonce=0,
            merkle_root=None,
            validator="system"
        )
        
        # Mine the genesis block
        self.mine_block(genesis_block)
        
        # Verify genesis
        is_valid, error = genesis_block.verify()
        if not is_valid:
            raise ValueError(f"Genesis block invalid: {error}")
        
        self.chain.append(genesis_block)
        
        # Create initial checkpoint
        self.create_checkpoint(0)
        
        return genesis_block
    
    def get_latest_block(self) -> Block:
        """Get the last block in the chain."""
        return self.chain[-1]
    
    def add_vote(self, vote: VoteTransaction) -> None:
        """Add a vote to pending transactions."""
        self.pending_votes.append(vote)
    
    def mine_pending_votes(self, validator: str = "system") -> Optional[Block]:
        """Create a new block with pending votes."""
        if not self.pending_votes:
            return None
        
        latest_block = self.get_latest_block()
        
        # Convert votes to dictionaries
        votes_data = [vote.to_dict() for vote in self.pending_votes]
        
        # Create new block
        new_block = Block(
            index=latest_block.index + 1,
            timestamp=datetime.utcnow(),
            votes=votes_data,
            previous_hash=latest_block.hash,
            nonce=0,
            validator=validator
        )
        
        # Mine the block
        self.mine_block(new_block)
        
        # Add to chain
        self.chain.append(new_block)
        
        # Clear pending votes
        self.pending_votes = []
        
        # Create checkpoint if needed
        if len(self.chain) % settings.BLOCKCHAIN_CHECKPOINT_INTERVAL == 0:
            self.create_checkpoint(new_block.index)
        
        return new_block
    
    def mine_block(self, block: Block) -> None:
        """Proof of work - find valid nonce."""
        target = "0" * self.DIFFICULTY
        
        while not block.hash.startswith(target):
            block.nonce += 1
            block.hash = block.calculate_hash()
    
    def is_chain_valid(self) -> Tuple[bool, List[int]]:
        """
        Validate the entire blockchain.
        
        Checks:
        - Hash consistency
        - Previous hash links
        - Merkle root integrity
        - PoW validity
        """
        invalid_blocks = []
        
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Check hash consistency
            if current_block.hash != current_block.calculate_hash():
                invalid_blocks.append(i)
                continue
            
            # Check previous hash link
            if current_block.previous_hash != previous_block.hash:
                invalid_blocks.append(i)
                continue
            
            # Check merkle root if votes exist
            if current_block.votes:
                expected_merkle = current_block.calculate_merkle_root()
                if current_block.merkle_root != expected_merkle:
                    invalid_blocks.append(i)
                    continue
            
            # Check PoW
            if not current_block.hash.startswith("0" * self.DIFFICULTY):
                invalid_blocks.append(i)
                continue
        
        return len(invalid_blocks) == 0, invalid_blocks
    
    def verify_chain_from_checkpoint(self, checkpoint_index: int) -> Tuple[bool, List[int]]:
        """
        Verify chain from a specific checkpoint.
        
        More efficient than full validation.
        """
        if checkpoint_index < 0 or checkpoint_index >= len(self.chain):
            return False, []
        
        # Validate from checkpoint to end
        invalid_blocks = []
        start_index = checkpoint_index + 1
        
        for i in range(start_index, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Quick validation
            if current_block.hash != current_block.calculate_hash():
                invalid_blocks.append(i)
            elif current_block.previous_hash != previous_block.hash:
                invalid_blocks.append(i)
        
        return len(invalid_blocks) == 0, invalid_blocks
    
    def create_checkpoint(self, block_index: int) -> str:
        """
        Create a checkpoint at given block index.
        
        Checkpoint is a signed hash that can be used for quick verification.
        """
        if block_index >= len(self.chain):
            return ""
        
        block = self.chain[block_index]
        
        # Create checkpoint data
        checkpoint_data = {
            "block_index": block.index,
            "block_hash": block.hash,
            "merkle_root": block.merkle_root,
            "total_votes": sum(len(b.votes) for b in self.chain[:block_index + 1]),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Create checkpoint hash
        checkpoint_string = json.dumps(checkpoint_data, sort_keys=True)
        checkpoint_hash = hashlib.sha256(checkpoint_string.encode()).hexdigest()
        
        self.checkpoints[block_index] = checkpoint_hash
        
        return checkpoint_hash
    
    def verify_checkpoint(self, block_index: int) -> bool:
        """Verify a checkpoint exists and is valid."""
        if block_index not in self.checkpoints:
            return False
        
        block = self.chain[block_index]
        
        # Rebuild checkpoint
        checkpoint_data = {
            "block_index": block.index,
            "block_hash": block.hash,
            "merkle_root": block.merkle_root,
            "total_votes": sum(len(b.votes) for b in self.chain[:block_index + 1]),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        checkpoint_string = json.dumps(checkpoint_data, sort_keys=True)
        expected_hash = hashlib.sha256(checkpoint_string.encode()).hexdigest()
        
        return self.checkpoints[block_index] == expected_hash
    
    def add_block(self, block: Block) -> bool:
        """Add a block to the chain (for syncing)."""
        latest_block = self.get_latest_block()
        
        # Validate block
        if block.index != latest_block.index + 1:
            return False
        
        if block.previous_hash != latest_block.hash:
            return False
        
        # Verify block
        is_valid, error = block.verify()
        if not is_valid:
            return False
        
        if not block.hash.startswith("0" * self.DIFFICULTY):
            return False
        
        self.chain.append(block)
        return True
    
    def get_votes_by_voter(self, voter_id: str) -> List[dict]:
        """Get all votes by a specific voter."""
        votes = []
        for block in self.chain:
            for vote in block.votes:
                if vote.get("voter_id") == voter_id:
                    votes.append(vote)
        return votes
    
    def has_voted(self, voter_id: str) -> bool:
        """Check if a voter has already voted."""
        return len(self.get_votes_by_voter(voter_id)) > 0
    
    def get_vote_count(self) -> Dict[str, int]:
        """Get vote counts per candidate."""
        counts = {}
        for block in self.chain:
            for vote in block.votes:
                candidate = vote.get("candidate_id")
                counts[candidate] = counts.get(candidate, 0) + 1
        return counts
    
    def get_total_votes(self) -> int:
        """Get total vote count."""
        return sum(len(block.votes) for block in self.chain)
    
    def to_json(self) -> str:
        """Export chain to JSON."""
        chain_data = [block.to_dict() for block in self.chain]
        return json.dumps({
            "chain": chain_data,
            "pending_votes": [v.to_dict() for v in self.pending_votes],
            "checkpoints": self.checkpoints
        }, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "Blockchain":
        """Import chain from JSON."""
        data = json.loads(json_str)
        blockchain = cls()
        blockchain.chain = [Block.from_dict(b) for b in data.get("chain", [])]
        blockchain.pending_votes = [VoteTransaction.from_dict(v) for v in data.get("pending_votes", [])]
        blockchain.checkpoints = data.get("checkpoints", {})
        return blockchain
    
    def get_block_by_index(self, index: int) -> Optional[Block]:
        """Get block by index."""
        if 0 <= index < len(self.chain):
            return self.chain[index]
        return None
    
    def get_block_by_hash(self, block_hash: str) -> Optional[Block]:
        """Get block by hash."""
        for block in self.chain:
            if block.hash == block_hash:
                return block
        return None
    
    def __len__(self) -> int:
        return len(self.chain)
    
    def __repr__(self) -> str:
        return f"<Blockchain(height={len(self.chain)}, pending={len(self.pending_votes)}, checkpoints={len(self.checkpoints)})>"
