#!/usr/bin/env python3
"""
Performance Benchmark Script
Tests database query performance before/after indexing
"""

import time
from sqlalchemy import func
from app.database import SessionLocal
from app.models import User, Vote, LoginAttempt, IPBlacklist, Block

def benchmark_query(name, query_func, iterations=10):
    """Benchmark a query function."""
    times = []
    for _ in range(iterations):
        start = time.time()
        query_func()
        elapsed = time.time() - start
        times.append(elapsed)
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"\n📊 {name}")
    print(f"   Average: {avg_time*1000:.2f}ms")
    print(f"   Min: {min_time*1000:.2f}ms")
    print(f"   Max: {max_time*1000:.2f}ms")
    
    return avg_time

def run_benchmarks():
    """Run all performance benchmarks."""
    db = SessionLocal()
    
    print("🚀 Starting Performance Benchmarks")
    print("=" * 50)
    
    # Test 1: Vote count by candidate
    def test_vote_count():
        result = db.query(
            Vote.candidate_id,
            func.count(Vote.id)
        ).group_by(Vote.candidate_id).all()
        return result
    
    benchmark_query("Vote Count Aggregation", test_vote_count)
    
    # Test 2: IP ban check
    def test_ip_ban():
        from datetime import datetime
        result = db.query(IPBlacklist).filter(
            IPBlacklist.ip_address == "192.168.1.1",
            IPBlacklist.banned_until > datetime.utcnow()
        ).first()
        return result
    
    benchmark_query("IP Ban Check", test_ip_ban)
    
    # Test 3: Failed login attempts count
    def test_failed_attempts():
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(hours=1)
        result = db.query(func.count(LoginAttempt.id)).filter(
            LoginAttempt.ip_address == "192.168.1.1",
            LoginAttempt.success == False,
            LoginAttempt.timestamp >= cutoff
        ).scalar()
        return result
    
    benchmark_query("Failed Attempts Count", test_failed_attempts)
    
    # Test 4: User with votes (eager loading)
    def test_user_votes():
        from sqlalchemy.orm import joinedload
        result = db.query(User).options(
            joinedload(User.votes)
        ).first()
        return result
    
    benchmark_query("User with Votes (Eager Load)", test_user_votes)
    
    # Test 5: Recent blocks
    def test_recent_blocks():
        result = db.query(Block).order_by(
            Block.timestamp.desc()
        ).limit(10).all()
        return result
    
    benchmark_query("Recent Blocks Query", test_recent_blocks)
    
    # Test 6: Active sessions
    def test_active_sessions():
        from datetime import datetime
        from app.models import Session as SessionModel
        result = db.query(SessionModel).filter(
            SessionModel.is_active == True,
            SessionModel.expires_at > datetime.utcnow()
        ).count()
        return result
    
    benchmark_query("Active Sessions Count", test_active_sessions)
    
    print("\n" + "=" * 50)
    print("✅ Benchmarks completed!")
    print("\n💡 Expected performance after indexing:")
    print("   - Vote aggregation: <50ms")
    print("   - IP ban check: <5ms")
    print("   - Failed attempts: <10ms")
    print("   - User queries: <20ms")
    
    db.close()

if __name__ == "__main__":
    run_benchmarks()
