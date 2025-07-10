from typing import Dict, Any

class GameStateManager:
    def create_initial_state(self, session_id: str, player_name: str) -> Dict[str, Any]:
        return {
            "session_id": session_id,
            "player_name": player_name,
            "current_state": "intro",
            "game_completed": False,
            "choice_made": None
        }