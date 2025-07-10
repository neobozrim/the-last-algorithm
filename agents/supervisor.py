from typing import Dict, List, Any
import json
import os
from utils.openai_client import OpenAIClient

class SupervisorAgent:
    def __init__(self, openai_client: OpenAIClient):
        self.openai_client = openai_client
        self.game_content = self._load_game_content()
        self.system_prompt = self._build_system_prompt()
    
    def _load_game_content(self) -> str:
        """Load the single game content file"""
        content_path = os.path.join(os.path.dirname(__file__), "../data/game_content.txt")
        with open(content_path, 'r') as f:
            return f.read()
    
    def _build_system_prompt(self) -> str:
        return f"""You are the Supervisor Agent for "The Last Algorithm" voice game.

GAME CONTENT:
{self.game_content}

YOUR ROLE:
1. Process player speech input in context of current game state
2. Use the game content above to make story decisions
3. Respond with narrative text that the voice agent will read aloud
4. Update game state based on player choices
5. Keep story coherent and engaging

YOU MUST RESPOND IN EXACT JSON FORMAT:
{{
    "narrative_text": "What the voice agent should say",
    "voice_instructions": "How to deliver it (tone, pacing)",
    "game_state": {{current or updated game state object}},
    "game_status": "active/completed/failed"
}}

RULES:
- ALWAYS respond in valid JSON format
- Keep narrative responses to 30-60 seconds when spoken
- Use the game content as your source of truth
- Update game state based on player decisions
- Stay in character and maintain story consistency"""

    async def process_player_action(self, player_input: str, current_state: Dict[str, Any], 
                                  narrative_history: List[Dict[str, str]]) -> Dict[str, Any]:
        
        # Build context for the LLM
        context = f"""
PLAYER INPUT: "{player_input}"

CURRENT GAME STATE: {json.dumps(current_state, indent=2)}

RECENT NARRATIVE HISTORY: {json.dumps(narrative_history[-3:], indent=2)}

Process this player input and respond with appropriate narrative and state updates.
"""
        
        # Get response from GPT-4.1
        response = await self.openai_client.chat_completion(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": context}
            ],
            model="gpt-4.1",
            temperature=0.2
        )
        
        try:
            # Parse JSON response
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "narrative_text": "The data streams flicker. Please repeat your last input.",
                "voice_instructions": "Speak with slight technical distortion",
                "game_state": current_state,
                "game_status": "active"
            }