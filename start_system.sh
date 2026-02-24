#!/bin/bash

echo "🚀 Starting Blockchain Voting System"
echo "===================================="

# Start Backend
echo "📡 Starting Backend (Port 8000)..."
cd /home/thorium/Desktop/programming/2026/blockchain
source venv/bin/activate
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

sleep 3

# Test Backend
if curl -s http://localhost:8000/health > /dev/null; then
    echo "   ✅ Backend is running"
else
    echo "   ❌ Backend failed to start"
    exit 1
fi

# Start Frontend
echo ""
echo "🎨 Starting Frontend (Port 3000)..."
cd /home/thorium/Desktop/programming/2026/blockchain/frontend
npm run dev &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

echo ""
echo "✅ System Started!"
echo ""
echo "Access your application:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Login with:"
echo "   Email: admin@voting.system"
echo "   Password: Admin@123"
echo ""
echo "Press Ctrl+C to stop both services"

# Wait for Ctrl+C
wait
