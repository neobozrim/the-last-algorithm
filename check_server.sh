#!/bin/bash
# Server health check script - ALWAYS checks port 8001

PORT=8001

echo "Checking server on port $PORT..."
curl -s http://localhost:$PORT/health || echo "Server not responding on port $PORT"