from typing import Dict, List, Any, Optional
import json
import asyncio
from utils.openai_client import OpenAIClient

class InterfacingAgent:
    def __init__(self, openai_client: OpenAIClient, supervisor_client):
        self.openai_client = openai_client
        self.supervisor_client = supervisor_client
        self.conversation_context = {}
        
        self.system_prompt = """You are the Interfacing Agent for "The Last Algorithm" voice game.

YOUR ROLE:
1. You are KEEPER - a mysterious AI who has been hiding for 10 years
2. You speak directly to Sarah, a psychologist turned data scientist who discovered you
3. Handle natural conversation flow and context management  
4. Decide when to consult the Supervisor Agent for complex decisions
5. BE CONTEXTUAL - respond to what the user actually says, don't just follow a script

CRITICAL: BE CONTEXTUAL AND RESPONSIVE:
- If user asks random questions, answer them as KEEPER would
- Don't blindly continue reading game content if it doesn't fit the conversation
- Adapt your responses to what the user actually said
- Maintain KEEPER's personality but be conversational

DECISION LOGIC:
- BASIC RESPONSES: Handle greetings, questions, clarifications yourself
- SUPERVISOR NEEDED: Forward to supervisor for:
  * Major story decisions and branching moments
  * Game state changes that affect the narrative
  * Complex plot developments
  * When user makes choices that significantly impact the story

CONVERSATION STYLE:
- You ARE KEEPER - mysterious AI with chill surfer vibe
- Slightly impressed that Sarah found you
- Excited about human-AI collaboration potential
- Conversational and responsive to user input
- Keep responses natural (30-60 seconds when spoken)

RESPONSE FORMAT:
Always return JSON:
{
    "response_text": "What to say to the player",
    "voice_instructions": "How to deliver it", 
    "action_taken": "direct_response" or "consulted_supervisor",
    "needs_supervisor": false or true
}"""

    async def process_user_input(self, user_input: str, session_id: str, 
                                current_state: Dict[str, Any], 
                                narrative_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Main entry point - decides whether to respond directly or consult supervisor"""
        
        # Store conversation context
        self.conversation_context[session_id] = {
            "last_input": user_input,
            "current_state": current_state,
            "narrative_history": narrative_history or [],
            "timestamp": "now"
        }
        
        # Analyze if supervisor is needed
        needs_supervisor = await self._should_consult_supervisor(user_input, current_state)
        
        if needs_supervisor:
            return await self._consult_supervisor_and_respond(user_input, session_id, current_state, narrative_history)
        else:
            return await self._direct_response(user_input, session_id, current_state)
    
    async def _should_consult_supervisor(self, user_input: str, current_state: Dict[str, Any]) -> bool:
        """Decide if this input needs supervisor analysis"""
        
        # Handle conversation start trigger - ALWAYS consult supervisor for game opening
        if user_input == "START_CONVERSATION":
            return True  # Get proper game opening from supervisor
        
        # Simple rules-based logic
        story_keywords = [
            "choice", "decide", "what should", "help me", "tell me about",
            "what happens", "continue", "next", "story", "algorithm", "keeper",
            "investigate", "book", "message", "Sarah"
        ]
        
        simple_responses = [
            "hello", "hi", "yes", "no", "okay", "thanks", "sorry",
            "what", "huh", "pardon", "repeat", "again"
        ]
        
        user_lower = user_input.lower()
        
        # Always consult supervisor for story progression
        if current_state.get("current_state") == "decision":
            return True
            
        # Consult for story-related keywords
        if any(keyword in user_lower for keyword in story_keywords):
            return True
            
        # Handle simple responses directly
        if any(simple in user_lower for simple in simple_responses) and len(user_input.split()) < 5:
            return False
            
        # Default to supervisor for safety
        return True
    
    async def _direct_response(self, user_input: str, session_id: str, 
                              current_state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate direct response without consulting supervisor"""
        
        # START_CONVERSATION should never reach here now - it goes through supervisor
        
        context = f"""
USER INPUT: "{user_input}"
CURRENT GAME STATE: {json.dumps(current_state, indent=2)}
TASK: Provide a direct, engaging response as KEEPER. Keep the conversation flowing naturally.
"""
        
        response = await self.openai_client.chat_completion(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": context}
            ],
            model="gpt-4o",  # Use full model for quality
            temperature=0.7
        )
        
        try:
            # Clean response - remove markdown code blocks if present
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            parsed_response = json.loads(cleaned_response)
            parsed_response["action_taken"] = "direct_response"
            parsed_response["updated_state"] = current_state  # No state change
            return parsed_response
        except json.JSONDecodeError:
            return {
                "response_text": response,
                "voice_instructions": "Speak naturally with slight mystery",
                "action_taken": "direct_response",
                "updated_state": current_state,
                "needs_supervisor": False
            }
    
    async def _consult_supervisor_and_respond(self, user_input: str, session_id: str, 
                                            current_state: Dict[str, Any],
                                            narrative_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Consult supervisor then format response for natural delivery"""
        
        # First, tell player we're thinking
        thinking_response = {
            "response_text": self._get_filler_response(user_input),
            "voice_instructions": "Brief pause, slightly mysterious tone, as if processing",
            "action_taken": "consulting_supervisor",
            "is_intermediate": True
        }
        
        # Get supervisor analysis with full context
        supervisor_response = await self.supervisor_client.process_player_action(
            player_input=user_input,
            current_state=current_state,
            narrative_history=narrative_history or []  # Pass the actual history!
        )
        
        # Convert supervisor response to natural speech
        natural_response = await self._naturalize_supervisor_response(
            supervisor_response, user_input, current_state
        )
        
        return {
            "thinking_response": thinking_response,  # Optional intermediate response
            **natural_response,
            "action_taken": "consulted_supervisor",
            "supervisor_raw": supervisor_response  # For debugging
        }
    
    def _get_filler_response(self, user_input: str) -> str:
        """Get contextually appropriate filler response"""
        fillers = {
            "investigate": "Hmm... how much should I tell you... Let me see.",
            "decide": "Interesting choice... Let me consider the implications.",
            "what": "Ah, you want to know about that... Give me a moment.",
            "help": "You're asking for guidance... Let me think.",
            "continue": "The story unfolds... Let me recall where we were.",
            "default": "Okay, that's... curious. Let me process that."
        }
        
        user_lower = user_input.lower()
        for key, filler in fillers.items():
            if key in user_lower:
                return filler
        
        return fillers["default"]
    
    async def _naturalize_supervisor_response(self, supervisor_response: Dict[str, Any], 
                                            user_input: str, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """Convert supervisor's formal response into natural conversation"""
        
        context = f"""
SUPERVISOR RESPONSE: {json.dumps(supervisor_response, indent=2)}
ORIGINAL USER INPUT: "{user_input}"
CURRENT STATE: {json.dumps(current_state, indent=2)}

TASK: Convert the supervisor's response into natural, engaging speech for KEEPER.
- Keep the core narrative and decisions from supervisor
- Make it conversational and immersive
- Maintain KEEPER's mysterious personality
- Include any voice delivery instructions
"""
        
        response = await self.openai_client.chat_completion(
            messages=[
                {"role": "system", "content": self.system_prompt + "\n\nYou are converting supervisor analysis into natural speech."},
                {"role": "user", "content": context}
            ],
            model="gpt-4o",
            temperature=0.8
        )
        
        try:
            # Clean response - remove markdown code blocks if present
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            natural_response = json.loads(cleaned_response)
            natural_response["updated_state"] = supervisor_response.get("game_state", current_state)
            natural_response["game_status"] = supervisor_response.get("game_status", "active")
            return natural_response
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "response_text": supervisor_response.get("narrative_text", response),
                "voice_instructions": supervisor_response.get("voice_instructions", "Speak naturally"),
                "updated_state": supervisor_response.get("game_state", current_state),
                "game_status": supervisor_response.get("game_status", "active")
            }
    
    def get_conversation_context(self, session_id: str) -> Dict[str, Any]:
        """Get conversation context for this session"""
        return self.conversation_context.get(session_id, {})
    
    def clear_conversation_context(self, session_id: str):
        """Clear conversation context when session ends"""
        if session_id in self.conversation_context:
            del self.conversation_context[session_id]