#!/bin/bash

# Blockchain Voting System - Startup Script
# This script sets up and runs both the backend and frontend

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default ports
BACKEND_PORT=8000
FRONTEND_PORT=3000

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Print colored message
print_msg() {
    local color=$1
    local msg=$2
    echo -e "${color}${msg}${NC}"
}

# Kill processes on specified port
kill_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_msg "$YELLOW" "Killing existing process on port $port..."
        lsof -Pi :$port -sTCP:LISTEN -t | xargs kill -9 2>/dev/null
        sleep 1
    fi
}

# Check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Setup backend
setup_backend() {
    print_msg "$BLUE" "Setting up backend..."
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        print_msg "$YELLOW" "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment using absolute path
    source "$SCRIPT_DIR/venv/bin/activate"
    
    # Install dependencies
    print_msg "$YELLOW" "Installing Python dependencies..."
    pip install -r requirements.txt -q
    
    # Initialize database if needed
    if [ ! -f "voting.db" ]; then
        print_msg "$YELLOW" "Initializing database..."
        python3 -c "from app.database import init_db; init_db()" 2>/dev/null
        
        # Create admin user
        python3 -c "
from app.database import get_db
from app.models import User, Candidate
from app.auth.password import hash_password

db = next(get_db())
admin = User(
    email='admin@example.com',
    voter_id=None,
    password_hash=hash_password('injendi27@'),
    role='admin',
    is_active=True,
    is_verified=True
)
db.add(admin)

# Candidates
for c in [('A','Alpha'), ('B','Beta'), ('C','Gamma')]:
    db.add(Candidate(candidate_id=c[0], name=f'Candidate {c[1]}'))

db.commit()
print('Admin and candidates created')
" 2>/dev/null
    fi
    
    deactivate 2>/dev/null
    print_msg "$GREEN" "Backend setup complete!"
}

# Start backend
start_backend() {
    print_msg "$BLUE" "Starting backend server..."
    
    # Kill existing process on port
    kill_port $BACKEND_PORT
    
    # Activate virtual environment
    source "$SCRIPT_DIR/venv/bin/activate"
    
    # Start uvicorn in background
    nohup uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT > backend.log 2>&1 &
    
    # Wait for server to start
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

# Setup frontend
setup_frontend() {
    print_msg "$BLUE" "Setting up frontend..."
    
    cd "$SCRIPT_DIR/frontend"
    
    # Install dependencies
    print_msg "$YELLOW" "Installing Node dependencies..."
    npm install -q 2>/dev/null
    
    # Check for Tailwind
    if [ ! -f "tailwind.config.js" ]; then
        print_msg "$YELLOW" "Installing Tailwind css..."
        npm install -D tailwindcss@3 postcss autoprefixer -q 2>/dev/null
        npx tailwindcss init -p 2>/dev/null
    fi
    
    cd "$SCRIPT_DIR"
    print_msg "$GREEN" "Frontend setup complete!"
}

# Start frontend
start_frontend() {
    print_msg "$BLUE" "Starting frontend server..."
    
    # Kill existing process on port
    kill_port $FRONTEND_PORT
    
    cd "$SCRIPT_DIR/frontend"
    
    # Clean build cache
    rm -rf .next 2>/dev/null
    
    # Start Next.js in background
    nohup npm run dev -- -p $FRONTEND_PORT > ../frontend.log 2>&1 &
    
    cd "$SCRIPT_DIR"
    
    # Wait for server to start
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

# Stop all servers
stop_all() {
    print_msg "$YELLOW" "Stopping all servers..."
    
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT
    
    print_msg "$GREEN" "All servers stopped!"
}

# Show status
show_status() {
    echo ""
    print_msg "$BLUE" "=== Server Status ==="
    echo ""
    
    if check_port $BACKEND_PORT; then
        print_msg "$GREEN" "✓ Backend:  http://localhost:$BACKEND_PORT"
        print_msg "$BLUE" "  API Docs: http://localhost:$BACKEND_PORT/docs"
    else
        print_msg "$RED" "✗ Backend:  Not running"
    fi
    
    if check_port $FRONTEND_PORT; then
        print_msg "$GREEN" "✓ Frontend: http://localhost:$FRONTEND_PORT"
    else
        print_msg "$RED" "✗ Frontend: Not running"
    fi
    
    echo ""
    print_msg "$YELLOW" "Admin Credentials:"
    echo "  Super Admin: superadmin@example.com / superadmin123"
    echo "  Admin:       admin@example.com / injendi27@"
    echo ""
}

# Show logs
show_logs() {
    echo ""
    print_msg "$BLUE" "=== Recent Logs ==="
    echo ""
    
    if [ -f "backend.log" ]; then
        print_msg "$YELLOW" "--- Backend ---"
        tail -20 backend.log
    fi
    
    if [ -f "frontend.log" ]; then
        print_msg "$YELLOW" "--- Frontend ---"
        tail -20 frontend.log
    fi
}

# Print usage
usage() {
    echo "Blockchain Voting System - Startup Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start       Start both backend and frontend servers"
    echo "  stop        Stop all servers"
    echo "  restart     Restart all servers"
    echo "  status      Show server status"
    echo "  logs        Show recent logs"
    echo "  setup       Setup environment (install deps, init DB)"
    echo "  help        Show this help message"
    echo ""
    echo "Default ports: Backend=$BACKEND_PORT, Frontend=$FRONTEND_PORT"
}

# Main script
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
    logs)
        show_logs
        ;;
    setup)
        setup_backend
        setup_frontend
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        print_msg "$RED" "Unknown command: $1"
        usage
        exit 1
        ;;
esac
