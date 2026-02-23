#!/bin/bash

# Blockchain Voting System - Complete Setup & Run Script

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_msg() {
    echo -e "${1}${2}${NC}"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

print_msg "$BLUE" "=== Blockchain Voting System Setup ==="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_msg "$YELLOW" "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
print_msg "$YELLOW" "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
print_msg "$YELLOW" "Installing Python dependencies..."
pip install -r requirements.txt -q

# Initialize database if needed
if [ ! -f "voting.db" ]; then
    print_msg "$YELLOW" "Initializing database..."
    python3 -c "from app.database import init_db; init_db()"
    
    # Create users
    print_msg "$YELLOW" "Creating users and candidates..."
    python3 << 'PYEOF'
from app.database import get_db
from app.models import User, Candidate
from app.auth.password import hash_password

db = next(get_db())

# Super Admin
db.add(User(
    email='superadmin@example.com',
    voter_id=None,
    password_hash=hash_password('superadmin123'),
    role='superadmin',
    is_active=True,
    is_verified=True
))

# Admin
db.add(User(
    email='admin@example.com',
    voter_id=None,
    password_hash=hash_password('injendi27@'),
    role='admin',
    is_active=True,
    is_verified=True
))

# Candidates
for cid, name in [('A', 'Alpha'), ('B', 'Beta'), ('C', 'Gamma')]:
    db.add(Candidate(candidate_id=cid, name=f'Candidate {name}'))

db.commit()
print("Users and candidates created!")
PYEOF

    # Fix permissions
    chmod 666 voting.db 2>/dev/null
fi

deactivate

# Setup frontend
print_msg "$YELLOW" "Setting up frontend..."
cd frontend
npm install -q 2>/dev/null

# Kill existing processes on ports
print_msg "$YELLOW" "Starting servers..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null
sleep 1

# Start backend
cd "$SCRIPT_DIR"
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend
sleep 3

# Start frontend
cd frontend
nohup npm run dev -- -p 3000 > ../frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend
sleep 8

echo ""
print_msg "$GREEN" "=== Setup Complete! ==="
echo ""
print_msg "$GREEN" "Frontend: http://localhost:3000"
print_msg "$GREEN" "Backend:  http://localhost:8000"
print_msg "$GREEN" "API Docs: http://localhost:8000/docs"
echo ""
print_msg "$YELLOW" "=== Login Credentials ==="
echo ""
echo "Super Admin: superadmin@example.com / superadmin123"
echo "Admin:       admin@example.com / injendi27@"
echo ""
