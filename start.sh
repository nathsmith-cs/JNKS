#!/bin/bash
set -e

# Kill any existing processes on our ports
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
pkill -f ngrok 2>/dev/null || true
lsof -ti:4040 | xargs kill -9 2>/dev/null || true
lsof -ti:4041 | xargs kill -9 2>/dev/null || true
sleep 1

# Load API keys from .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Start ngrok tunnel first (need the URL before building frontend)
echo "Starting ngrok tunnel..."
ngrok http 8000 --log=stdout > /dev/null &
NGROK_PID=$!

echo "Waiting for ngrok..."
NGROK_URL=""
for i in {1..20}; do
    sleep 1
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "
import sys, json
try:
    t = json.load(sys.stdin)['tunnels']
    print(next(x['public_url'] for x in t if x['public_url'].startswith('https')))
except:
    pass
" 2>/dev/null)
    if [ -n "$NGROK_URL" ]; then
        break
    fi
done

if [ -z "$NGROK_URL" ]; then
    echo "ERROR: ngrok failed to start."
    echo "  Install: brew install ngrok"
    echo "  Auth:    ngrok config add-authtoken YOUR_TOKEN"
    kill $NGROK_PID 2>/dev/null
    exit 1
fi

WS_URL=$(echo "$NGROK_URL" | sed 's|https://|wss://|')
echo "ngrok URL: $NGROK_URL"

# Build frontend with ngrok URLs baked in
echo "Building frontend..."
NEXT_PUBLIC_API_URL="$NGROK_URL" NEXT_PUBLIC_WS_URL="$WS_URL" npx next build

# Start backend (serves API + WebSocket + static frontend)
echo "Starting backend..."
source venv/bin/activate 2>/dev/null || true
python3 -m pipeline.server &
BACKEND_PID=$!

# Wait for backend
echo "Waiting for backend..."
for i in {1..15}; do
    if curl -s http://localhost:8000/api/references > /dev/null 2>&1; then
        echo "Backend ready!"
        break
    fi
    sleep 1
done

echo ""
echo "========================================="
echo "  Everything on: $NGROK_URL"
echo "========================================="
echo ""
echo "  Open on phone: $NGROK_URL"
echo "  Open on Mac:   http://localhost:8000"
echo ""
echo "  Press Ctrl+C to stop"
echo "========================================="

# Cleanup on exit
trap "kill $BACKEND_PID $NGROK_PID 2>/dev/null; exit" INT TERM
wait
