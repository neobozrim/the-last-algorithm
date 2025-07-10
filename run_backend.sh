#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "Starting The Last Algorithm Backend..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${RED}Dependencies not installed. Installing...${NC}"
    pip install -r requirements.txt
fi

# Kill any existing server process
if [ -f "/tmp/last-algorithm-server.pid" ]; then
    OLD_PID=$(cat /tmp/last-algorithm-server.pid)
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "Stopping existing server (PID: $OLD_PID)..."
        kill $OLD_PID
        sleep 2
    fi
fi

# Start the server
echo -e "${GREEN}Starting server...${NC}"
echo "Server will run at: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo ""

# Run uvicorn directly (not in background for better error visibility)
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload