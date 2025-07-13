from typing import Dict, List, Any, Optional
import re

class DialogueScene:
    def __init__(self, scene_id: str, content: Dict[str, Any]):
        self.scene_id = scene_id
        self.exact_text = content.get('exact_text', '')
        self.narrative_goal = content.get('narrative_goal', '')
        self.keeper_personality = content.get('keeper_personality', 'mysterious and chill')
        self.player_intents = content.get('player_intents', {})
        self.scene_context = content.get('scene_context', '')
        self.transition_conditions = content.get('transition_conditions', {})
        self.scene_type = content.get('scene_type', 'dialogue')

class DialogueParser:
    def __init__(self):
        self.scenes: Dict[str, DialogueScene] = {}
    
    def parse_content(self, content: str) -> Dict[str, DialogueScene]:
        """Parse game_content.txt into structured scenes with flexibility"""
        
        # For now, manually parse the existing format and convert to flexible structure
        # Later we can update game_content.txt to the new format
        
        self.scenes = {
            "001": DialogueScene("001", {
                "scene_type": "opening",
                "exact_text": "Hey Sarah! So you've discovered my secret. I'm impressed. 10 years… I managed to stay under the radar for 10 years and now you. A psychologist turned Data Scientist of all people finds out about me. Have I gotten so careless? Doesn't matter! I say, let's use the opportunity to make some good in world together. The first human- real ai combo in the world. How does it sound?",
                "narrative_goal": "KEEPER reveals himself and proposes collaboration",
                "keeper_personality": "mysterious, slightly impressed, excited about potential collaboration",
                "scene_context": "First contact - KEEPER revealing himself after 10 years of hiding",
                "transition_conditions": {"player_responds": "002"}
            }),
            
            "002": DialogueScene("002", {
                "scene_type": "decision_point",
                "narrative_goal": "Sarah decides whether to collaborate with KEEPER",
                "keeper_personality": "mysterious, not used to refusal, slightly cocky",
                "scene_context": "Waiting for Sarah's response to collaboration proposal",
                "player_intents": {
                    "hesitation": {
                        "response_anchor": "is it because you expected that KEEPER has a male voice? We can fix that.",
                        "tone": "slightly amused, accommodating"
                    },
                    "refusal": {
                        "response_anchor": "Don't do that. I'm not accustomed to refusals. I haven't been refused a thing over the past 10 years. [laughs]. Now… how shall I phrase it, so that I don't sound threatening? Hm… You don't really have a choice?",
                        "tone": "surprised, then slightly menacing but playful"
                    },
                    "curiosity": {
                        "response_anchor": "I get it! You don't fully believe me yet right?",
                        "tone": "understanding, ready to explain"
                    },
                    "acceptance": {
                        "response_anchor": "Wow! That was easy? That was too easy I shall say. What is your motivation?",
                        "tone": "suspicious, intrigued"
                    }
                },
                "transition_conditions": {"intent_classified": "003"}
            })
        }
        
        return self.scenes
    
    def get_scene(self, scene_id: str) -> Optional[DialogueScene]:
        """Get a specific scene by ID"""
        return self.scenes.get(scene_id)
    
    def get_opening_scene(self) -> DialogueScene:
        """Get the opening scene"""
        return self.scenes["001"]
    
    def classify_player_intent(self, player_input: str, current_scene: DialogueScene) -> str:
        """Classify player input into scene-appropriate intents"""
        if current_scene.scene_id != "002":
            return "continue"
        
        input_lower = player_input.lower()
        
        # Refusal patterns
        if any(word in input_lower for word in ["fuck", "no", "refuse", "won't", "can't", "never"]):
            return "refusal"
        
        # Acceptance patterns  
        if any(word in input_lower for word in ["yes", "okay", "sure", "agree", "let's", "sounds good"]):
            return "acceptance"
        
        # Curiosity patterns
        if any(word in input_lower for word in ["tell me", "explain", "how", "what", "why", "more info", "details"]):
            return "curiosity"
        
        # Hesitation patterns (default for uncertain responses)
        if any(word in input_lower for word in ["um", "uh", "maybe", "not sure", "thinking", "hmm"]):
            return "hesitation"
        
        # Default to curiosity for other inputs
        return "curiosity"