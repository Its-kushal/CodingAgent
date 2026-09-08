import json
from llm import chat
from prompts import SYSTEM_PROMPT
from tools import TOOL_SCHEMAS, execute_tool

MAX_ITERATIONS = 10

def run_agent_turn(system_prompt: str, messages: list) -> list:
    last_action_signature = None
    loop_strike_count = 0 

    for iteration in range(MAX_ITERATIONS):
        print(f"\n\033[90m--- Iteration {iteration + 1} ---\033[0m")

        message = chat(system_prompt, messages, tools=TOOL_SCHEMAS, iteration=iteration + 1)
        messages.append(message) 

        # RESTORED: Dump the exact JSON payload the LLM generated
        print(f"\n\033[90m[RAW LLM OUTPUT]:\n{json.dumps(message.get('content', []), indent=2)}\033[0m")

        content_blocks = message.get("content", [])
        final_text = ""
        tool_uses = []

        for block in content_blocks:
            if "text" in block:
                final_text += block["text"] + "\n"
            elif "toolUse" in block:
                tool_uses.append(block["toolUse"])

        if tool_uses:
            tool_results_content = []
            
            for tool_use in tool_uses:
                tool_use_id = tool_use["toolUseId"]
                name = tool_use["name"]
                args = tool_use["input"] 

                current_signature = f"{name}:{json.dumps(args, sort_keys=True)}"

                if current_signature == last_action_signature:
                    loop_strike_count += 1
                    print(f"\033[91m[SYSTEM BLOCK]: Prevented repetitive loop on {name}\033[0m")

                    if loop_strike_count >= 3:
                        print("\033[91m[SYSTEM]: Too many consecutive loops. Aborting turn to prevent context poisoning.\033[0m")
                        return messages

                    result = "SYSTEM ERROR: You just executed this exact command. Analyze the observation and provide your final answer, or take a DIFFERENT action."
                else:
                    loop_strike_count = 0 
                    print(f"\n\033[94m[ACT]: Executing -> {name}(...)\033[0m")
                    result = execute_tool(name, args)

                    # State Reset: Clear memory if the workspace changes
                    if name == "write_file" and "SUCCESS" in result:
                        last_action_signature = None
                    else:
                        last_action_signature = current_signature

                print(f"\033[93m[OBSERVE]: {result[:200]}{'...' if len(result) > 200 else ''}\033[0m")

                tool_results_content.append({
                    "toolResult": {
                        "toolUseId": tool_use_id,
                        "content": [{"text": result}]
                    }
                })

            messages.append({
                "role": "user",
                "content": tool_results_content
            })
            
        else:
            print(f"\n\033[92m[AGENT]:\n{final_text.strip()}\033[0m")
            return messages

    print("\n\033[91m[SYSTEM]: Max iterations reached.\033[0m")
    return messages

def start_repl():
    print(f"\033[95m[SYSTEM]: AWS Bedrock Agent Interactive REPL Initialized.\033[0m")
    print(f"\033[95m[SYSTEM]: Type 'exit' to quit, 'clear' to wipe memory.\033[0m")
    print("=" * 60)

    # Bedrock passes the System Prompt via a dedicated API parameter, not in the messages array
    messages = []

    while True:
        try:
            user_input = input("\n\033[1m[YOU]\033[0m> ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit']:
                from monitor import monitor
                monitor.print_session_summary()
                break
            if user_input.lower() == 'clear':
                messages = []
                print("\033[93m[SYSTEM]: Conversation history wiped.\033[0m")
                continue

            # Bedrock expects user content as an array of text blocks
            messages.append({"role": "user", "content": [{"text": user_input}]})
            messages = run_agent_turn(SYSTEM_PROMPT, messages)

        except KeyboardInterrupt:
            print("\n\033[95mForce quit detected. Shutting down...\033[0m")
            break

if __name__ == "__main__":
    start_repl()