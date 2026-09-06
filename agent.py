import json
import re
from llm import chat
from prompts import SYSTEM_PROMPT
from tools import TOOL_SCHEMAS, execute_tool

MAX_ITERATIONS = 10

def extract_tool_calls(message):
    """Parses tool calls, strips markdown backticks, and extracts thoughts."""
    tool_calls = []
    thoughts = []
    
    content = message.get("content", "").strip()
    
    # AGGRESSIVE MARKDOWN STRIPPER: Removes ```json and trailing ```
    content = re.sub(r'^```(?:json)?\s*', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\s*```$', '', content)
    content = content.strip()

    if content.startswith("{") or content.startswith("["):
        try:
            parsed = json.loads(content)
            # Single tool call
            if isinstance(parsed, dict) and "name" in parsed:
                tool_calls.append({"function": parsed})
                if "thought" in parsed:
                    thoughts.append(parsed["thought"])
            # Multiple tool calls
            elif isinstance(parsed, list):
                for item in parsed:
                    if "name" in item:
                        tool_calls.append({"function": item})
                    if "thought" in item:
                        thoughts.append(item["thought"])
        except json.JSONDecodeError:
            pass
            
    return tool_calls, thoughts

def run_agent(user_request: str):
    print(f"\n\033[95m[SYSTEM]: Initializing Agent with 6GB VRAM Constraints...\033[0m")
    print(f"\033[95m[USER REQUEST]: {user_request}\033[0m\n")
    print("=" * 60)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_request}
    ]
    
    for iteration in range(MAX_ITERATIONS):
        print(f"\n\033[1m--- Iteration {iteration + 1} ---\033[0m")
        
        message = chat(messages, tools=TOOL_SCHEMAS)
        messages.append(message)
        
        print(f"\n\033[90m[RAW LLM OUTPUT]:\n{message.get('content', '')}\033[0m")
        
        tool_calls, thoughts = extract_tool_calls(message)
        
        for thought in thoughts:
            print(f"\n\033[96m[PLAN/THINK]: {thought}\033[0m")
        
        if tool_calls:
            for tool_call in tool_calls:
                func = tool_call["function"]
                name = func["name"]
                args = func.get("arguments", {})
                
                print(f"\n\033[94m[ACT]: Executing -> {name}({args})\033[0m")
                result = execute_tool(name, args)
                print(f"\033[93m[OBSERVE - Sending to LLM]:\n{result}\033[0m")
                
                messages.append({
                    "role": "tool",
                    "content": result,
                    "name": name
                })
        else:
            print(f"\n\033[92m[FINAL ANSWER EXECUTED]:\n{message.get('content', '')}\033[0m")
            return

    print("\n\033[91m[SYSTEM]: Max iterations reached.\033[0m")

if __name__ == "__main__":
    # The prompt explicitly asks it to output the python code as the final answer
    run_agent("First list the files in the workspace, then read the file named hello.py. For your final answer, output the exact python code you read from the file.")