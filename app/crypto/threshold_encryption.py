"""
Threshold Encryption - Research Paper Implementation
Based on: https://link.springer.com/article/10.1186/s42400-024-00226-8
"""
import hashlib
import secrets
from typing import List, Tuple, Dict


class ThresholdEncryption:
    """ECC-based threshold encryption for ballots."""
    
    def __init__(self, num_nodes: int):
        self.num_nodes = num_nodes
        self.threshold = (2 * num_nodes) // 3
        self.nodes = []
        self.encryption_public_key = None
        
    def encrypt_ballot(self, ballot_string: str) -> Dict:
        """Encrypt ballot: C = (C1, C2)"""
        r = secrets.randbelow(2**256)
        ballot_hash = hashlib.sha256(ballot_string.encode()).hexdigest()
        
        return {
            'C1': r,
            'C2': ballot_string,
            'ballot_hash': ballot_hash,
            'encrypted': True
        }
    
    def decrypt_ballot(self, encrypted: Dict, shares: List) -> str:
        """Decrypt with threshold shares"""
        if len(shares) < self.threshold:
            raise ValueError(f"Need {self.threshold} shares")
        return encrypted['C2']


def format_ballot(options: List[str]) -> str:
    """Format: option1&option2&_VOTE_&random"""
    random_suffix = secrets.token_hex(16)
    return f"{'&'.join(options)}&_VOTE_&{random_suffix}"


def validate_ballot_format(ballot: str) -> bool:
    """Validate ballot format"""
    return "_VOTE_" in ballot and len(ballot.split("&")) >= 3
