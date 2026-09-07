import json
import re
from llm import chat
from prompts import SYSTEM_PROMPT
from tools import TOOL_SCHEMAS, execute_tool

MAX_ITERATIONS = 10

def extract_tool_calls(message):
    tool_calls = []
    thoughts = []

    if "tool_calls" in message and message["tool_calls"]:
        for tc in message["tool_calls"]:
            tool_calls.append({"function": tc["function"]})

    content = message.get("content", "").strip()
    content = re.sub(r'^```(?:json)?\s*', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\s*```$', '', content)
    content = content.strip()

    content = re.sub(r'\}\s*\{', '},{', content)
    if content.startswith('{') and content.endswith('}') and '},{' in content:
        content = f"[{content}]"

    if content.startswith("{") or content.startswith("["):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and "name" in parsed:
                if not any(tc["function"]["name"] == parsed["name"] for tc in tool_calls):
                    tool_calls.append({"function": parsed})
                if "thought" in parsed:
                    thoughts.append(parsed["thought"])
            elif isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "name" in item:
                        if not any(tc["function"]["name"] == item["name"] for tc in tool_calls):
                            tool_calls.append({"function": item})
                    if isinstance(item, dict) and "thought" in item:
                        thoughts.append(item["thought"])
        except json.JSONDecodeError:
            pass

    return tool_calls, thoughts

def run_agent_turn(messages: list) -> list:
    recent_signatures = []
    loop_strike_count = 0 # Track consecutive failures

    for iteration in range(MAX_ITERATIONS):
        print(f"\n\033[90m--- Iteration {iteration + 1} ---\033[0m")

        message = chat(messages, tools=TOOL_SCHEMAS)
        messages.append(message)

        print(f"\n\033[90m[RAW LLM OUTPUT]:\n{message.get('content', '')}\033[0m")

        tool_calls, thoughts = extract_tool_calls(message)

        for thought in thoughts:
            print(f"\033[96m[PLAN]: {thought}\033[0m")

        if tool_calls:
            for tool_call in tool_calls:
                func = tool_call["function"]
                name = func["name"]
                args = func.get("arguments", {})

                current_signature = f"{name}:{json.dumps(args, sort_keys=True)}"

                if current_signature in recent_signatures:
                    loop_strike_count += 1
                    print(f"\033[91m[SYSTEM BLOCK]: Prevented repetitive loop on {name}\033[0m")
                    
                    if loop_strike_count >= 3:
                        print("\033[91m[SYSTEM]: Too many consecutive loops. Aborting turn to prevent context poisoning.\033[0m")
                        return messages
                        
                    result = "SYSTEM ERROR: You are repeating recent actions. Analyze the previous observations and provide your final answer, or take a DIFFERENT action."
                else:
                    loop_strike_count = 0 # Reset on valid action
                    print(f"\033[94m[ACT]: {name}(...)\033[0m")
                    result = execute_tool(name, args)
                    
                    recent_signatures.append(current_signature)
                    if len(recent_signatures) > 3:
                        recent_signatures.pop(0)

                print(f"\033[93m[OBSERVE]: {result[:200]}{'...' if len(result) > 200 else ''}\033[0m")

                messages.append({
                    "role": "tool",
                    "content": result,
                    "name": name
                })
        else:
            final_text = message.get('content', '').strip()
            print(f"\n\033[92m[AGENT]:\n{final_text}\033[0m")
            return messages

    print("\n\033[91m[SYSTEM]: Max iterations reached.\033[0m")
    return messages

def start_repl():
    print(f"\033[95m[SYSTEM]: Hybrid Agent Interactive REPL Initialized.\033[0m")
    print(f"\033[95m[SYSTEM]: Type 'exit' to quit, 'clear' to wipe memory.\033[0m")
    print("=" * 60)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        try:
            user_input = input("\n\033[1m[YOU]\033[0m> ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit']:
                print("\033[95mShutting down...\033[0m")
                break
            if user_input.lower() == 'clear':
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                print("\033[93m[SYSTEM]: Conversation history wiped.\033[0m")
                continue

            messages.append({"role": "user", "content": user_input})
            messages = run_agent_turn(messages)

        except KeyboardInterrupt:
            print("\n\033[95mForce quit detected. Shutting down...\033[0m")
            break

if __name__ == "__main__":
    start_repl()