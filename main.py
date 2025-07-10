from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, List, Any
import os
import json
import httpx
import uuid
from datetime import datetime
from dotenv import load_dotenv

from agents.supervisor import SupervisorAgent
from game.state import GameStateManager
from utils.redis_client import get_redis_client
from utils.openai_client import OpenAIClient

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="The Last Algorithm", version="1.0.0")

# Configure CORS based on environment
cors_origins = ["*"] if os.getenv("ENVIRONMENT") != "production" else [
    "https://*.railway.app",
    "https://*.up.railway.app", 
    "http://localhost:*",
    "http://127.0.0.1:*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAIClient(OPENAI_API_KEY)
supervisor_agent = SupervisorAgent(openai_client)
game_state_manager = GameStateManager()

# Request/Response models
class SessionRequest(BaseModel):
    playerName: str = "Player"

class PlayerActionRequest(BaseModel):
    sessionId: str
    playerInput: str

class SessionResponse(BaseModel):
    client_secret: Dict[str, str]
    session_id: str
    initial_narrative: str

class SupervisorResponse(BaseModel):
    narrative_text: str
    voice_instructions: str
    game_state: Dict[str, Any]
    game_status: str

@app.get("/")
async def root():
    # In production, return API info. In development, serve chat interface
    if os.getenv("ENVIRONMENT") == "production":
        return {"message": "The Last Algorithm Backend API", "status": "running", "docs": "/docs", "health": "/health"}
    else:
        return FileResponse("chat.html")

@app.get("/api")
async def api_root():
    return {"message": "The Last Algorithm Backend API", "status": "running", "docs": "/docs"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "game": "The Last Algorithm"}

@app.post("/debug/test-supervisor")
async def test_supervisor(request: PlayerActionRequest):
    """Debug endpoint to test supervisor directly"""
    try:
        # Test basic supervisor functionality
        response = await supervisor_agent.process_player_action(
            player_input=request.playerInput,
            current_state={"location": "start", "chapter": 1},
            narrative_history=[]
        )
        return {"success": True, "response": response}
    except Exception as e:
        import traceback
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}

@app.post("/api/session", response_model=SessionResponse)
async def create_game_session(request: SessionRequest):
    # Generate session ID
    session_id = str(uuid.uuid4())
    
    # For testing, skip OpenAI realtime session creation
    session_data = {"client_secret": {"value": "test-session-token"}}
    
    # Initialize game state
    initial_state = game_state_manager.create_initial_state(session_id, request.playerName)
    
    # Store in Redis
    redis_client = await get_redis_client()
    await redis_client.hset(
        f"session:{session_id}",
        mapping={
            "game_state": json.dumps(initial_state),
            "narrative_history": json.dumps([]),
            "created_at": datetime.utcnow().isoformat()
        }
    )
    await redis_client.expire(f"session:{session_id}", 7200)  # 2 hours
    
    return SessionResponse(
        client_secret=session_data["client_secret"],
        session_id=session_id,
        initial_narrative="This May the Chicago Sun-Times published a fake book list. 10 out of 15 books on it were AI hallucinations... What if one of the books wasn't a mistake, BUT A MESSAGE?"
    )

@app.post("/api/player-action", response_model=SupervisorResponse)
async def process_player_action(request: PlayerActionRequest):
    # Get current state from Redis
    redis_client = await get_redis_client()
    session_data = await redis_client.hgetall(f"session:{request.sessionId}")
    
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    current_state = json.loads(session_data.get("game_state", "{}"))
    narrative_history = json.loads(session_data.get("narrative_history", "[]"))
    
    # Process through supervisor - returns structured JSON directly
    try:
        supervisor_response = await supervisor_agent.process_player_action(
            player_input=request.playerInput,
            current_state=current_state,
            narrative_history=narrative_history
        )
    except Exception as e:
        print(f"ERROR in supervisor: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Supervisor error: {str(e)}")
    
    # Update Redis with new state
    narrative_history.append({
        "player_input": request.playerInput,
        "supervisor_response": supervisor_response["narrative_text"],
        "timestamp": datetime.utcnow().isoformat()
    })
    
    await redis_client.hset(
        f"session:{request.sessionId}",
        mapping={
            "game_state": json.dumps(supervisor_response["game_state"]),
            "narrative_history": json.dumps(narrative_history[-20:])  # Keep last 20
        }
    )
    
    # Return supervisor response directly
    return SupervisorResponse(**supervisor_response)

@app.get("/api/session/{session_id}/state")
async def get_session_state(session_id: str):
    redis_client = await get_redis_client()
    session_data = await redis_client.hgetall(f"session:{session_id}")
    
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "game_state": json.loads(session_data.get("game_state", "{}")),
        "narrative_history": json.loads(session_data.get("narrative_history", "[]"))
    }