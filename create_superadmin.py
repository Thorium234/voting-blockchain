#!/usr/bin/env python3
"""
Create Initial Superadmin Account
Run this once to bootstrap the system
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import User
from passlib.context import CryptContext
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_superadmin():
    """Create the first superadmin account."""
    db = SessionLocal()
    
    # Check if superadmin exists
    existing = db.query(User).filter(User.role == 'superadmin').first()
    if existing:
        print(f"⚠️  Superadmin already exists: {existing.email}")
        print(f"   Voter ID: {existing.voter_id}")
        db.close()
        return
    
    print("🔐 Creating Initial Superadmin Account")
    print("=" * 50)
    
    email = input("Email: ").strip()
    voter_id = input("Voter ID: ").strip()
    password = input("Password (min 8 chars, 1 upper, 1 lower, 1 digit): ").strip()[:72]
    
    if len(password) < 8:
        print("❌ Password too short")
        sys.exit(1)
    
    # Create superadmin
    superadmin = User(
        email=email,
        voter_id=voter_id,
        password_hash=hash_password(password),
        role='superadmin',
        is_active=True,
        is_verified=True
    )
    
    db.add(superadmin)
    db.commit()
    db.refresh(superadmin)
    
    print("\n✅ Superadmin created successfully!")
    print(f"   Email: {superadmin.email}")
    print(f"   Voter ID: {superadmin.voter_id}")
    print(f"   Role: {superadmin.role}")
    print("\n🚀 You can now login and register other users")
    
    db.close()

if __name__ == "__main__":
    try:
        create_superadmin()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
