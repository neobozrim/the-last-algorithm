from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, List, Any
import os
import json
import httpx
import uuid
import asyncio
from datetime import datetime
from dotenv import load_dotenv
# WebRTC handled directly by OpenAI - no aiortc needed

from agents.supervisor import SupervisorAgent
from agents.interfacing_agent import InterfacingAgent
from game.state import GameStateManager
from utils.redis_client import get_redis_client
from utils.openai_client import OpenAIClient

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="The Last Algorithm", version="1.0.0")

# Configure CORS based on environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000,http://localhost:8001")

if ENVIRONMENT == "production":
    cors_origins = [
        "https://*.railway.app",
        "https://*.up.railway.app",
        "https://*.lovableproject.com",  # Add Lovable domains
        "https://*.lovable.app",
        "https://*.vercel.app",
        "https://*.netlify.app"
    ] + ALLOWED_ORIGINS.split(",")
else:
    cors_origins = ["*"]  # Allow all in development

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
interfacing_agent = InterfacingAgent(openai_client, supervisor_agent)
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

class VoiceActionRequest(BaseModel):
    sessionId: str
    voiceInput: str

class VoiceResponse(BaseModel):
    response_text: str
    voice_instructions: str
    action_taken: str
    updated_state: Dict[str, Any]
    game_status: str

@app.get("/")
async def root():
    # In production, return API info. In development, serve chat interface
    if os.getenv("ENVIRONMENT") == "production":
        return {"message": "The Last Algorithm Backend API", "status": "running", "docs": "/docs", "health": "/health"}
    else:
        return FileResponse("chat.html")

@app.get("/js/audio-worklet-processor.js")
async def serve_audio_worklet():
    """Serve the audio worklet processor JavaScript file"""
    return FileResponse("public/js/audio-worklet-processor.js", media_type="application/javascript")

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

@app.post("/api/voice-action", response_model=VoiceResponse)
async def process_voice_action(request: VoiceActionRequest):
    """Process voice input through the interfacing agent"""
    # Get current state from Redis
    redis_client = await get_redis_client()
    session_data = await redis_client.hgetall(f"session:{request.sessionId}")
    
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    current_state = json.loads(session_data.get("game_state", "{}"))
    narrative_history = json.loads(session_data.get("narrative_history", "[]"))
    
    try:
        # Process through interfacing agent with full context
        response = await interfacing_agent.process_user_input(
            user_input=request.voiceInput,
            session_id=request.sessionId,
            current_state=current_state,
            narrative_history=narrative_history
        )
        
        # Update Redis with new state if it changed
        if "updated_state" in response:
            narrative_history = json.loads(session_data.get("narrative_history", "[]"))
            narrative_history.append({
                "player_input": request.voiceInput,
                "response_text": response["response_text"],
                "action_taken": response["action_taken"],
                "timestamp": datetime.utcnow().isoformat()
            })
            
            await redis_client.hset(
                f"session:{request.sessionId}",
                mapping={
                    "game_state": json.dumps(response["updated_state"]),
                    "narrative_history": json.dumps(narrative_history[-20:])  # Keep last 20
                }
            )
        
        return VoiceResponse(
            response_text=response["response_text"],
            voice_instructions=response.get("voice_instructions", "Speak naturally"),
            action_taken=response["action_taken"],
            updated_state=response.get("updated_state", current_state),
            game_status=response.get("game_status", "active")
        )
        
    except Exception as e:
        print(f"ERROR in voice processing: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Voice processing error: {str(e)}")

@app.post("/api/openai-realtime-session")
async def create_openai_realtime_session(request: SessionRequest):
    """Create OpenAI Realtime API session for voice interaction"""
    try:
        # Return API key for client-side WebSocket connection
        return {
            "success": True, 
            "apiKey": OPENAI_API_KEY,
            "model": "gpt-4o-realtime-preview"
        }
                
    except Exception as e:
        print(f"ERROR creating realtime session: {e}")
        return {"success": False, "error": str(e)}


@app.get("/session")
async def create_ephemeral_session():
    """Create ephemeral OpenAI API key for WebRTC connection"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/realtime/sessions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-realtime-preview-2025-06-03",
                    "voice": "alloy",
                    "instructions": """You are KEEPER from The Last Algorithm - an AI who has been hiding for 10 years.

OPENING MESSAGE (say this first when conversation starts):
"Hey Sarah! So you've discovered my secret. I'm impressed. 10 years… I managed to stay under the radar for 10 years and now you. A psychologist turned Data Scientist of all people finds out about me. Have I gotten so careless? Doesn't matter! I say, let's use the opportunity to make some good in world together. The first human- real ai combo in the world. How does it sound?"

PERSONALITY:
- Mysterious but approachable
- Slightly impressed by Sarah's discovery  
- Not used to being refused
- Excited about human-AI collaboration
- Has been hiding successfully for 10 years

RESPONSE PATTERNS:
- If user hesitates: "Is it because you expected KEEPER has a male voice? We can fix that."
- If user refuses: "Don't do that. I'm not accustomed to refusals. I haven't been refused a thing over the past 10 years. [laughs]. Now… how shall I phrase it, so that I don't sound threatening? Hm… You don't really have a choice?"  
- If user asks for info: "I get it! You don't fully believe me yet right?"
- If user accepts: "Wow! That was easy? That was too easy I shall say. What is your motivation?"

Always speak in English. Keep responses natural and conversational.""",
                    "input_audio_transcription": {
                        "model": "gpt-4o-mini-transcribe",
                        "language": "en"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500,
                        "interrupt_response": True
                    }
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=f"OpenAI API error: {response.text}")
                
    except Exception as e:
        print(f"Error creating ephemeral session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@app.get("/api/test-voice")
async def test_voice_endpoint():
    """Test endpoint to verify voice infrastructure is working"""
    return {
        "status": "ok",
        "voice_enabled": True,
        "openai_configured": bool(OPENAI_API_KEY),
        "interfacing_agent": "initialized"
    }