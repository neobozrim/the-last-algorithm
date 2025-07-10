#!/bin/bash
# Installation script for The Last Algorithm backend

echo "Installing The Last Algorithm dependencies..."

# Activate virtual environment
source venv/bin/activate

# Install dependencies in smaller batches to avoid timeout
echo "Installing FastAPI and core dependencies..."
pip install fastapi==0.104.1 pydantic==2.5.0

echo "Installing server dependencies..."
pip install uvicorn[standard]==0.24.0

echo "Installing client dependencies..."
pip install httpx==0.25.2 openai==1.3.7 redis==5.0.1

echo "Installation complete!"
echo ""
echo "To run the server:"
echo "1. Copy .env.example to .env and add your OpenAI API key"
echo "2. Make sure Redis is running"
echo "3. Run: source venv/bin/activate && uvicorn main:app --reload"