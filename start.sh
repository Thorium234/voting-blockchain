#!/bin/bash

# Blockchain Voting System - Startup Script

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BACKEND_PORT=8000
FRONTEND_PORT=3000

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

print_msg() {
    echo -e "${1}${2}${NC}"
}

kill_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        lsof -Pi :$port -sTCP:LISTEN -t | xargs kill -9 2>/dev/null
        sleep 1
    fi
}

check_port() {
    lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1
}

setup_backend() {
    print_msg "$BLUE" "Setting up backend..."
    
    if [ ! -d "venv" ]; then
        print_msg "$YELLOW" "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    source ./venv/bin/activate
    
    pip install -r requirements.txt -q
    
    if [ ! -f "voting.db" ]; then
        print_msg "$YELLOW" "Initializing database..."
        python3 -c "from app.database import init_db; init_db()"
        
        python3 << 'PYEOF'
from app.database import get_db
from app.models import User, Candidate
from app.auth.password import hash_password
db = next(get_db())
db.add(User(email='admin@example.com', voter_id=None, password_hash=hash_password('injendi27@'), role='admin', is_active=True, is_verified=True))
for c in [('A','Alpha'), ('B','Beta'), ('C','Gamma')]:
    db.add(Candidate(candidate_id=c[0], name=f'Candidate {c[1]}'))
db.commit()
print("Done!")
PYEOF
    fi
    
    deactivate 2>/dev/null
    print_msg "$GREEN" "Backend setup complete!"
}

start_backend() {
    print_msg "$BLUE" "Starting backend server..."
    kill_port $BACKEND_PORT
    source ./venv/bin/activate
    nohup uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT > backend.log 2>&1 &
    
    local count=0
    while [ $count -lt 15 ]; do
        if curl -s http://localhost:$BACKEND_PORT/health >/dev/null 2>&1; then
            print_msg "$GREEN" "Backend running on http://localhost:$BACKEND_PORT"
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done
    
    print_msg "$RED" "Failed to start backend server"
    return 1
}

setup_frontend() {
    print_msg "$BLUE" "Setting up frontend..."
    cd frontend
    npm install -q 2>/dev/null
    cd ..
    print_msg "$GREEN" "Frontend setup complete!"
}

start_frontend() {
    print_msg "$BLUE" "Starting frontend server..."
    kill_port $FRONTEND_PORT
    cd frontend
    rm -rf .next 2>/dev/null
    nohup npm run dev -- -p $FRONTEND_PORT > ../frontend.log 2>&1 &
    cd ..
    
    local count=0
    while [ $count -lt 30 ]; do
        if curl -s http://localhost:$FRONTEND_PORT >/dev/null 2>&1; then
            print_msg "$GREEN" "Frontend running on http://localhost:$FRONTEND_PORT"
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done
    
    print_msg "$RED" "Failed to start frontend server"
    return 1
}

stop_all() {
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT
    print_msg "$GREEN" "All servers stopped!"
}

show_status() {
    echo ""
    if check_port $BACKEND_PORT; then
        print_msg "$GREEN" "✓ Backend:  http://localhost:$BACKEND_PORT"
    else
        print_msg "$RED" "✗ Backend:  Not running"
    fi
    
    if check_port $FRONTEND_PORT; then
        print_msg "$GREEN" "✓ Frontend: http://localhost:$FRONTEND_PORT"
    else
        print_msg "$RED" "✗ Frontend: Not running"
    fi
    
    echo ""
    echo "Super Admin: superadmin@example.com / superadmin123"
    echo "Admin:       admin@example.com / injendi27@"
    echo ""
}

case "${1:-start}" in
    start)
        setup_backend
        setup_frontend
        start_backend
        start_frontend
        show_status
        ;;
    stop)
        stop_all
        ;;
    restart)
        stop_all
        sleep 2
        start_backend
        start_frontend
        show_status
        ;;
    status)
        show_status
        ;;
    *)
        ./start.sh start
        ;;
esac
