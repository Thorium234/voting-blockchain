"""Blockchain chain management."""
import json
from datetime import datetime
from typing import List, Optional
import hashlib

from app.blockchain.block import Block, VoteTransaction


class Blockchain:
    """Manages the blockchain structure and validation."""
    
    DIFFICULTY = 2  # Number of leading zeros required in hash
    
    def __init__(self):
        self.chain: List[Block] = []
        self.pending_votes: List[VoteTransaction] = []
        self.create_genesis_block()
    
    def create_genesis_block(self) -> Block:
        """Create the first block in the chain."""
        genesis_block = Block(
            index=0,
            timestamp=datetime.utcnow(),
            votes=[],
            previous_hash="0" * 64,
            nonce=0
        )
        # Mine the genesis block
        self.mine_block(genesis_block)
        self.chain.append(genesis_block)
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
            nonce=0
        )
        
        # Mine the block
        self.mine_block(new_block)
        
        # Add to chain
        self.chain.append(new_block)
        
        # Clear pending votes
        self.pending_votes = []
        
        return new_block
    
    def mine_block(self, block: Block) -> None:
        """Proof of work - find valid nonce."""
        target = "0" * self.DIFFICULTY
        
        while not block.hash.startswith(target):
            block.nonce += 1
            block.hash = block.calculate_hash()
    
    def is_chain_valid(self) -> tuple[bool, List[int]]:
_chain_valid(self) -> tuple[bool, List[int]]:
        """Validate the entire blockchain."""
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
        
        return len(invalid_blocks) == 0, invalid_blocks
    
    def add_block(self, block: Block) -> bool:
        """Add a block to the chain (for syncing)."""
        latest_block = self.get_latest_block()
        
        # Validate block
        if block.index != latest_block.index + 1:
            return False
        
        if block.previous_hash != latest_block.hash:
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
    
    def get_vote_count(self) -> dict:
        """Get vote counts per candidate."""
        counts = {}
        for block in self.chain:
            for vote in block.votes:
                candidate = vote.get("candidate_id")
                counts[candidate] = counts.get(candidate, 0) + 1
        return counts
    
    def to_json(self) -> str:
        """Export chain to JSON."""
        chain_data = [block.to_dict() for block in self.chain]
        return json.dumps({
            "chain": chain_data,
            "pending_votes": [v.to_dict() for v in self.pending_votes]
        }, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "Blockchain":
        """Import chain from JSON."""
        data = json.loads(json_str)
        blockchain = cls()
        blockchain.chain = [Block.from_dict(b) for b in data.get("chain", [])]
        blockchain.pending_votes = [VoteTransaction.from_dict(v) for v in data.get("pending_votes", [])]
        return blockchain
    
    def __len__(self) -> int:
        return len(self.chain)
    
    def __repr__(self) -> str:
        return f"<Blockchain(height={len(self.chain)}, pending={len(self.pending_votes)})>"
