#!/bin/bash

# Script to create admin user
# Usage: ./create_admin.sh [email] [password] [voter_id] [role]

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Get arguments or use defaults
EMAIL="${1:-admin@example.com}"
PASSWORD="${2:-injendi27@}"
VOTER_ID="${3:-}"
ROLE="${4:-voter}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
else
    echo -e "${RED}Virtual environment not found. Run ./start.sh first.${NC}"
    exit 1
fi

echo "Creating user..."
echo "Email: $EMAIL"
echo "Role: $ROLE"

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
    existing.role = "$ROLE"
    existing.is_active = True
    existing.password_hash = hash_password("$PASSWORD")
    print(f"Updated user to role: $ROLE")
else:
    # Create new user
    user = User(
        email="$EMAIL",
        voter_id="$VOTER_ID" if "$VOTER_ID" else None,
        password_hash=hash_password("$PASSWORD"),
        role="$ROLE",
        is_active=True,
        is_verified=True
    )
    db.add(user)
    print(f"Created new user: $EMAIL with role: $ROLE")

db.commit()

# Verify
user = db.query(User).filter(User.email == "$EMAIL").first()
print(f"\n✓ User created/updated successfully!")
print(f"  Email: {user.email}")
print(f"  Role: {user.role}")
print(f"  Is Admin: {user.is_admin}")
EOF

RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo -e "${GREEN}Done!${NC}"
else
    echo -e "${RED}Failed to create user${NC}"
fi

deactivate 2>/dev/null
