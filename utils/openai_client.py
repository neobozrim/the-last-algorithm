import httpx
from typing import List, Dict
import json

class OpenAIClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
    
    async def chat_completion(self, messages: List[Dict[str, str]], model: str = "gpt-4", **kwargs):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Convert messages to new Responses API format
        system_message = None
        user_input = ""
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            elif msg["role"] == "user":
                user_input = msg["content"]
        
        data = {
            "model": model,
            "input": user_input,
            **kwargs
        }
        
        if system_message:
            data["instructions"] = system_message
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/responses",
                headers=headers,
                json=data,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
            
            result = response.json()
            return result["output"][0]["content"][0]["text"]