import requests

OLLAMA_URL = "http://host.docker.internal:11434/api/chat"
MODEL = "qwen2.5-coder:3b"

def chat(messages, tools=None):
    """Sends a conversation history to Ollama. Returns the full message dictionary."""
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.1
        }
    }
    
    if tools:
        payload["tools"] = tools
        
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        # Return the ENTIRE message object (so we can check for tool_calls)
        return data["message"]
    except requests.exceptions.RequestException as e:
        return {"role": "assistant", "content": f"Error communicating with Ollama: {e}"}