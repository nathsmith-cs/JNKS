#!/bin/bash
set -e

# Get local IP (works on macOS hotspot)
IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr bridge0 2>/dev/null || echo "localhost")
echo "Local IP: $IP"

# Set URLs for frontend
export NEXT_PUBLIC_API_URL="http://$IP:8000"
export NEXT_PUBLIC_WS_URL="ws://$IP:8000"
echo "API URL: $NEXT_PUBLIC_API_URL"
echo "WS URL:  $NEXT_PUBLIC_WS_URL"

# Kill any existing processes on our ports
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

# Load API keys from .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Start backend
echo "Starting backend..."
source venv/bin/activate 2>/dev/null || true
python3 -m pipeline.server &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/references > /dev/null 2>&1; then
        echo "Backend ready!"
        break
    fi
    sleep 1
done

# Start frontend
echo "Starting frontend..."
NEXT_PUBLIC_API_URL="http://$IP:8000" NEXT_PUBLIC_WS_URL="ws://$IP:8000" npm run dev &
FRONTEND_PID=$!

echo ""
echo "========================================="
echo "  Backend:  http://$IP:8000"
echo "  Frontend: http://$IP:3000"
echo "  WebSocket: ws://$IP:8000/ws/analyze"
echo "========================================="
echo "  Open on phone: http://$IP:3000"
echo "  Press Ctrl+C to stop"
echo "========================================="

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
