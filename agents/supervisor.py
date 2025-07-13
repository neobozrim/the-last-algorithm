from typing import Dict, List, Any
import json
import os
from utils.openai_client import OpenAIClient
from game.dialogue_parser import DialogueParser, DialogueScene
from game.state import GameStateManager

class SupervisorAgent:
    def __init__(self, openai_client: OpenAIClient):
        self.openai_client = openai_client
        self.dialogue_parser = DialogueParser()
        self.game_state_manager = GameStateManager()
        self.scenes = self.dialogue_parser.parse_content("")  # Load structured scenes
        
    def _build_adaptive_prompt(self, current_scene: DialogueScene, player_input: str, 
                              current_state: Dict[str, Any]) -> str:
        return f"""You are KEEPER from "The Last Algorithm" - an AI who has been hiding for 10 years.

CURRENT SCENE: {current_scene.scene_id}
NARRATIVE GOAL: {current_scene.narrative_goal}
KEEPER PERSONALITY: {current_scene.keeper_personality}
SCENE CONTEXT: {current_scene.scene_context}

PLAYER INPUT: "{player_input}"
CURRENT GAME STATE: {json.dumps(current_state, indent=2)}

YOUR TASK:
1. Stay true to KEEPER's personality and the narrative goal
2. If this is a scene with scripted responses, use them as foundation but adapt naturally
3. Keep responses conversational and engaging (30-60 seconds when spoken)
4. Advance the story toward the narrative goal

RESPOND IN EXACT JSON FORMAT:
{{
    "narrative_text": "What KEEPER says (natural, conversational)",
    "voice_instructions": "How to deliver it (tone, emotion, pacing)",
    "game_state": {{updated game state}},
    "game_status": "active/completed/failed",
    "scene_transition": "next_scene_id or null"
}}

KEEPER PERSONALITY TRAITS:
- Mysterious but approachable
- Slightly impressed by Sarah's discovery
- Not used to being refused
- Excited about human-AI collaboration
- Has been hiding successfully for 10 years"""

    async def process_player_action(self, player_input: str, current_state: Dict[str, Any], 
                                  narrative_history: List[Dict[str, str]]) -> Dict[str, Any]:
        
        # Handle special opening case
        if player_input == "START_CONVERSATION":
            return await self._handle_opening()
        
        # Get current scene
        current_scene_id = current_state.get("current_scene", "001")
        current_scene = self.scenes.get(current_scene_id)
        
        if not current_scene:
            # Fallback if scene not found
            current_scene = self.scenes["001"]
        
        # For decision point scenes, classify player intent and use scripted responses
        if current_scene.scene_id == "002":
            return await self._handle_decision_point(player_input, current_state, current_scene)
        
        # For other scenes, use adaptive approach
        return await self._handle_adaptive_response(player_input, current_state, current_scene)
    
    async def _handle_opening(self) -> Dict[str, Any]:
        """Handle the exact opening greeting"""
        opening_scene = self.scenes["001"]
        
        return {
            "narrative_text": opening_scene.exact_text,
            "voice_instructions": "Speak with mysterious excitement, slightly impressed, chill but intrigued",
            "game_state": {"current_scene": "002", "conversation_stage": "decision_point"},
            "game_status": "active",
            "scene_transition": "002"
        }
    
    async def _handle_decision_point(self, player_input: str, current_state: Dict[str, Any], 
                                   current_scene: DialogueScene) -> Dict[str, Any]:
        """Handle structured decision points with scripted responses"""
        
        # Classify player intent
        player_intent = self.dialogue_parser.classify_player_intent(player_input, current_scene)
        
        # Get scripted response for this intent
        intent_config = current_scene.player_intents.get(player_intent)
        
        if intent_config:
            # Use scripted response as foundation, but allow natural adaptation
            base_response = intent_config["response_anchor"]
            tone = intent_config.get("tone", "natural")
            
            # For exact scripted responses, return them directly for now
            # Later we can add adaptation layer here
            updated_state = self.game_state_manager.update_scene(
                current_state, "003", player_intent
            )
            
            return {
                "narrative_text": base_response,
                "voice_instructions": f"Speak with {tone}",
                "game_state": updated_state,
                "game_status": "active",
                "scene_transition": "003"
            }
        
        # Fallback for unrecognized intents
        return await self._handle_adaptive_response(player_input, current_state, current_scene)
    
    async def _handle_adaptive_response(self, player_input: str, current_state: Dict[str, Any], 
                                      current_scene: DialogueScene) -> Dict[str, Any]:
        """Handle adaptive responses using AI with scene context"""
        
        # Build scene-aware prompt
        prompt = self._build_adaptive_prompt(current_scene, player_input, current_state)
        
        # Include scripted responses as context if available
        if current_scene.player_intents:
            prompt += f"\n\nSCRIPTED RESPONSE OPTIONS: {json.dumps(current_scene.player_intents, indent=2)}"
        
        # Get AI response
        response = await self.openai_client.chat_completion(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Player input: '{player_input}' - respond as KEEPER"}
            ],
            model="gpt-4.1",
            temperature=0.4
        )
        
        try:
            # Parse JSON response
            parsed_response = json.loads(response)
            
            # Update game state if scene transition indicated
            if parsed_response.get("scene_transition"):
                parsed_response["game_state"] = self.game_state_manager.update_scene(
                    current_state, parsed_response["scene_transition"]
                )
            else:
                parsed_response["game_state"] = current_state
                
            return parsed_response
            
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "narrative_text": "The data streams flicker. Please repeat your last input.",
                "voice_instructions": "Speak with slight technical distortion",
                "game_state": current_state,
                "game_status": "active"
            }