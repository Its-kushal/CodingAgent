import requests

OLLAMA_URL = "http://host.docker.internal:11434/api/chat"
MODEL = "qwen2.5-coder:3b"

def chat(messages, tools=None):
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_ctx": 32768,
        }
    }

    if tools:
        payload["tools"] = tools

    try:
        # Increased timeout to 5 minutes (300 seconds)
        response = requests.post(OLLAMA_URL, json=payload, timeout=300)
        response.raise_for_status()
        data = response.json()
        return data["message"]
    except requests.exceptions.RequestException as e:
        return {"role": "assistant", "content": f"Error communicating with Ollama: {e}"}