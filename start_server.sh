#!/bin/bash
# Server startup script - ALWAYS uses port 8001

PORT=8001
HOST=0.0.0.0

echo "Starting The Last Algorithm server on port $PORT..."

# Kill any existing processes on port 8001
lsof -ti:$PORT | xargs kill -9 2>/dev/null || true

# Activate virtual environment and start server
source venv/bin/activate
python -m uvicorn main:app --host $HOST --port $PORT --reload