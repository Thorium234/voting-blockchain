#!/bin/bash

# Script to create admin user
# Usage: ./create_admin.sh [email] [password] [voter_id]

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Get arguments or use defaults
EMAIL="${1:-admin@example.com}"
PASSWORD="${2:-injendi27@}"
VOTER_ID="${3:-admin}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo -e "${RED}Virtual environment not found. Run ./start.sh first.${NC}"
    exit 1
fi

echo "Creating admin user..."
echo "Email: $EMAIL"
echo "Voter ID: $VOTER_ID"

# Run Python script to create admin
python3 << EOF
import sys
sys.path.insert(0, '.')

from app.database import init_db, get_db
from app.models import User
from app.auth.password import hash_password

# Initialize database
init_db()

db = next(get_db())

# Check if user exists
existing = db.query(User).filter(User.email == "$EMAIL").first()

if existing:
    print(f"User {existing.email} already exists")
    existing.is_admin = True
    existing.is_active = True
    existing.password_hash = hash_password("$PASSWORD")
    print("Updated existing user to admin")
else:
    # Create new admin
    admin = User(
        email="$EMAIL",
        voter_id="$VOTER_ID",
        password_hash=hash_password("$PASSWORD"),
        is_admin=True,
        is_active=True,
        is_verified=True
    )
    db.add(admin)
    print(f"Created new admin user: $EMAIL")

db.commit()

# Verify
admin = db.query(User).filter(User.email == "$EMAIL").first()
print(f"\n✓ Admin user created/updated successfully!")
print(f"  Email: {admin.email}")
print(f"  Voter ID: {admin.voter_id}")
print(f"  Is Admin: {admin.is_admin}")
print(f"  Is Active: {admin.is_active}")
EOF

RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo -e "${GREEN}Done!${NC}"
else
    echo -e "${RED}Failed to create admin user${NC}"
fi

deactivate 2>/dev/null
