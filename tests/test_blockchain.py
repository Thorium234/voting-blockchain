"""
Unit tests for Blockchain Validation.

Tests:
- Block hash calculation
- Merkle root generation
- Chain validation
- Anti-replay mechanisms
"""
import pytest
import json
from datetime import datetime
from app.blockchain.block import Block, VoteTransaction
from app.blockchain.chain import Blockchain


class TestBlockHash:
    """Test block hashing and verification."""
    
    def test_deterministic_hash(self):
        """Hash should be deterministic across multiple calculations."""
        block = Block(
            index=1,
            timestamp=datetime.utcnow(),
            votes=[{"voter_id": "v1", "candidate_id": "A"}],
            previous_hash="0" * 64
        )
        
        hash1 = block.hash
        hash2 = block.calculate_hash()
        
        assert hash1 == hash2
    
    def test_hash_changes_with_data(self):
        """Hash should change when block data changes."""
        block1 = Block(
            index=1,
            timestamp=datetime.utcnow(),
            votes=[{"voter_id": "v1", "candidate_id": "A"}],
            previous_hash="0" * 64
        )
        
        block2 = Block(
            index=1,
            timestamp=datetime.utcnow(),
            votes=[{"voter_id": "v1", "candidate_id": "B"}],
            previous_hash="0" * 64
        )
        
        assert block1.hash != block2.hash
    
    def test_canonical_serialization(self):
        """Different dict order should produce same hash."""
        block1 = Block(
            index=1,
            timestamp=datetime.utcnow(),
            votes=[{"voter_id": "v1", "candidate_id": "A"}],
            previous_hash="0" * 64
        )
        
        block2 = Block(
            index=1,
            timestamp=datetime.utcnow(),
            votes=[{"candidate_id": "A", "voter_id": "v1"}],
            previous_hash="0" * 64
        )
        
        assert block1.hash == block2.hash


class TestMerkleRoot:
    """Test Merkle tree implementation."""
    
    def test_empty_merkle_root(self):
        """Block with no votes should have None merkle root."""
        block = Block(
            index=0,
            timestamp=datetime.utcnow(),
            votes=[],
            previous_hash="0" * 64
        )
        
        assert block.merkle_root is None
    
    def test_single_vote_merkle(self):
        """Single vote should have vote hash as merkle root."""
        votes = [{"voter_id": "v1", "candidate_id": "A"}]
        block = Block(
            index=1,
            timestamp=datetime.utcnow(),
            votes=votes,
            previous_hash="0" * 64
        )
        
        import hashlib
        expected = hashlib.sha256(json.dumps(votes[0], sort_keys=True).encode()).hexdigest()
        assert block.merkle_root == expected
    
    def test_multiple_votes_merkle(self):
        """Multiple votes should produce proper merkle root."""
        votes = [
            {"voter_id": "v1", "candidate_id": "A"},
            {"voter_id": "v2", "candidate_id": "B"}
        ]
        block = Block(
            index=1,
            timestamp=datetime.utcnow(),
            votes=votes,
            previous_hash="0" * 64
        )
        
        assert block.merkle_root is not None
        assert len(block.merkle_root) == 64


class TestBlockchain:
    """Test blockchain operations."""
    
    def test_genesis_block(self):
        """Genesis block should be created correctly."""
        bc = Blockchain()
        
        assert len(bc.chain) == 1
        assert bc.chain[0].index == 0
        assert bc.chain[0].previous_hash == "0" * 64
    
    def test_add_block(self):
        """Adding blocks should work correctly."""
        bc = Blockchain()
        
        # Add some votes
        vote = VoteTransaction("voter1", "candidate_A", "nonce1")
        bc.add_vote(vote)
        
        new_block = bc.mine_pending_votes()
        
        assert new_block is not None
        assert len(bc.chain) == 2
    
    def test_chain_validation(self):
        """Chain validation should detect tampering."""
        bc = Blockchain()
        
        # Add vote and mine
        vote = VoteTransaction("voter1", "candidate_A", "nonce1")
        bc.add_vote(vote)
        bc.mine_pending_votes()
        
        is_valid, invalid = bc.is_chain_valid()
        
        assert is_valid is True
        assert len(invalid) == 0
    
    def test_tamper_detection(self):
        """Tampering should be detected."""
        bc = Blockchain()
        
        # Add vote and mine
        vote = VoteTransaction("voter1", "candidate_A", "nonce1")
        bc.add_vote(vote)
        bc.mine_pending_votes()
        
        # Tamper with a block
        bc.chain[1].votes[0]["candidate_id"] = "TAMPERED"
        
        is_valid, invalid = bc.is_chain_valid()
        
        assert is_valid is False
        assert 1 in invalid


class TestVoteTransaction:
    """Test vote transaction operations."""
    
    def test_transaction_hash(self):
        """Transaction hash should be deterministic."""
        tx = VoteTransaction("voter1", "candidate_A", "nonce123")
        
        hash1 = tx.calculate_transaction_hash()
        hash2 = tx.calculate_transaction_hash()
        
        assert hash1 == hash2
    
    def test_different_votes_different_hashes(self):
        """Different votes should have different hashes."""
        tx1 = VoteTransaction("voter1", "candidate_A", "nonce1")
        tx2 = VoteTransaction("voter1", "candidate_B", "nonce1")
        
        assert tx1.calculate_transaction_hash() != tx2.calculate_transaction_hash()


class TestSecurityAntiReplay:
    """Test anti-replay protection."""
    
    def test_nonce_generation(self):
        """Nonces should be unique."""
        from app.security.anti_replay import generate_nonce
        
        nonce1 = generate_nonce()
        nonce2 = generate_nonce()
        
        assert nonce1 != nonce2
        assert len(nonce1) >= 16
    
    def test_vote_payload_hash(self):
        """Vote payload hash should be deterministic."""
        from app.security.anti_replay import hash_vote_payload
        
        hash1 = hash_vote_payload("voter1", "A", "nonce1", 1234567890)
        hash2 = hash_vote_payload("voter1", "A", "nonce1", 1234567890)
        
        assert hash1 == hash2
    
    def test_different_payload_different_hash(self):
        """Different payloads should have different hashes."""
        from app.security.anti_replay import hash_vote_payload
        
        hash1 = hash_vote_payload("voter1", "A", "nonce1", 1234567890)
        hash2 = hash_vote_payload("voter1", "B", "nonce1", 1234567890)
        
        assert hash1 != hash2
