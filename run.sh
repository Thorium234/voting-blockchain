#!/bin/bash

# Blockchain Voting System - Complete Setup Script

# Get directory where script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "Working directory: $DIR"
echo ""

# Check if venv exists, if not create it
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
echo "Activating virtual environment..."
source ./venv/bin/activate

# Install deps
echo "Installing Python dependencies..."
pip install -r requirements.txt -q

# Initialize DB if needed
if [ ! -f "voting.db" ]; then
    echo "Initializing database..."
    python3 -c "from app.database import init_db; init_db()"
    
    echo "Creating users..."
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
for cid, name in [('A','Alpha'), ('B','Beta'), ('C','Gamma')]:
    db.add(Candidate(candidate_id=cid, name=f'Candidate {name}'))

db.commit()
print("Users created!")
PYEOF

    chmod 666 voting.db
fi

# Kill existing servers
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null
sleep 1

# Start backend
echo "Starting backend on port 8000..."
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
sleep 3

# Start frontend
if [ -d "frontend" ]; then
    echo "Starting frontend on port 3000..."
    cd frontend
    nohup npm run dev > ../frontend.log 2>&1 &
    cd ..
    sleep 8
else
    echo "Frontend directory not found - skipping frontend"
fi

echo ""
echo "=== DONE ==="
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Login credentials:"
echo "  Super Admin: superadmin@example.com / superadmin123"
echo "  Admin: admin@example.com / injendi27@"
