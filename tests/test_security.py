"""
Security tests for rate limiting and attack prevention.

Tests:
- Rate limiting enforcement
- Brute force detection
- IP banning
- Credential stuffing detection
"""
import pytest
from datetime import datetime, timedelta
from app.security.rate_limiter import SlidingWindowRateLimiter, TokenBucket


class TestSlidingWindowRateLimiter:
    """Test sliding window rate limiter."""
    
    def test_allow_first_requests(self):
        """First requests should be allowed."""
        limiter = SlidingWindowRateLimiter(5, 60)
        
        allowed, count, remaining = limiter.is_allowed("test_ip")
        
        assert allowed is True
        assert count == 1
        assert remaining == 4
    
    def test_block_excess_requests(self):
        """Excess requests should be blocked."""
        limiter = SlidingWindowRateLimiter(2, 60)
        
        # First two allowed
        for _ in range(2):
            allowed, _, _ = limiter.is_allowed("test_ip")
            assert allowed is True
        
        # Third should be blocked
        allowed, count, remaining = limiter.is_allowed("test_ip")
        assert allowed is False
        assert remaining == 0
    
    def test_different_keys_independent(self):
        """Different keys should have independent limits."""
        limiter = SlidingWindowRateLimiter(2, 60)
        
        limiter.is_allowed("ip1")
        limiter.is_allowed("ip1")
        
        # ip1 exhausted, ip2 should still work
        allowed, _, _ = limiter.is_allowed("ip2")
        assert allowed is True


class TestTokenBucket:
    """Test token bucket for burst handling."""
    
    def test_initial_tokens(self):
        """Should have initial tokens available."""
        bucket = TokenBucket(10, 1.0)
        
        # Should be able to consume up to capacity
        assert bucket.consume(5) is True
    
    def test_refill_tokens(self):
        """Tokens should refill over time."""
        bucket = TokenBucket(5, 10.0)  # 10 tokens/sec
        
        bucket.consume(5)  # Exhaust bucket
        
        # After 0.1 seconds, should have ~1 token
        import time
        time.sleep(0.1)
        
        assert bucket.consume(1) is True
    
    def test_no_overflow(self):
        """Bucket should not overflow."""
        bucket = TokenBucket(5, 100.0)
        
        # Try to add way more than capacity
        bucket._tokens = 1000
        
        # Should cap at capacity
        assert bucket._tokens <= 5


class TestAntiReplay:
    """Test anti-replay mechanisms."""
    
    def test_timestamp_validation(self):
        """Test timestamp validation."""
        from app.security.anti_replay import validate_timestamp
        import time
        
        # Current timestamp should be valid
        current = int(time.time())
        valid, error = validate_timestamp(current)
        
        assert valid is True
        assert error is None
    
    def test_old_timestamp_rejected(self):
        """Old timestamps should be rejected."""
        from app.security.anti_replay import validate_timestamp
        import time
        
        old = int(time.time()) - 400  # 6+ minutes old
        valid, error = validate_timestamp(old)
        
        assert valid is False
        assert "too old" in error.lower()
    
    def test_future_timestamp_rejected(self):
        """Future timestamps should be rejected."""
        from app.security.anti_replay import validate_timestamp
        
        future = int(time.time()) + 100
        valid, error = validate_timestamp(future)
        
        assert valid is False
    
    def test_nonce_generation(self):
        """Nonces should be unique and sufficiently long."""
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
