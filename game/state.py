from typing import Dict, Any, List

class GameStateManager:
    def create_initial_state(self, session_id: str, player_name: str) -> Dict[str, Any]:
        return {
            "session_id": session_id,
            "player_name": player_name,
            "current_scene": "001",  # Start at opening scene
            "scene_history": [],
            "conversation_stage": "opening",
            "player_intents": [],
            "keeper_personality_state": "mysterious_reveal",
            "narrative_context": "first_contact",
            "game_completed": False,
            "last_player_intent": None
        }
    
    def update_scene(self, current_state: Dict[str, Any], new_scene: str, 
                    player_intent: str = None) -> Dict[str, Any]:
        """Update game state when transitioning between scenes"""
        updated_state = current_state.copy()
        
        # Track scene history
        if current_state.get("current_scene"):
            updated_state["scene_history"].append(current_state["current_scene"])
        
        updated_state["current_scene"] = new_scene
        
        if player_intent:
            updated_state["last_player_intent"] = player_intent
            updated_state["player_intents"].append({
                "scene": current_state.get("current_scene"),
                "intent": player_intent
            })
        
        # Update conversation stage based on scene
        if new_scene == "001":
            updated_state["conversation_stage"] = "opening"
        elif new_scene == "002":
            updated_state["conversation_stage"] = "decision_point"
        elif new_scene.startswith("003"):
            updated_state["conversation_stage"] = "response_phase"
        
        return updated_state