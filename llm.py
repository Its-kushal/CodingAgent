import boto3
import time
from dotenv import load_dotenv
from monitor import monitor

load_dotenv(".env.local")

REGION = "ap-south-1"
MODEL_ID = "openai.gpt-oss-20b-1:0"

bedrock_runtime = boto3.client(service_name="bedrock-runtime", region_name=REGION)

def chat(system_prompt, messages, tools=None, iteration=1):
    bedrock_tool_config = None
    if tools:
        bedrock_tools = [{
            "toolSpec": {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
                "inputSchema": {"json": t["function"]["parameters"]}
            }
        } for t in tools]
        bedrock_tool_config = {"tools": bedrock_tools}

    kwargs = {
        "modelId": MODEL_ID,
        "system": [{"text": system_prompt}],
        "messages": messages,
        "inferenceConfig": {"temperature": 0.1, "maxTokens": 4096}
    }
    if bedrock_tool_config:
        kwargs["toolConfig"] = bedrock_tool_config

    # --- Telemetry Timers ---
    start_time = time.time()
    first_token_time = None

    try:
        response = bedrock_runtime.converse_stream(**kwargs)
        stream = response.get('stream')

        collected_text = ""
        tool_uses = {}
        input_tokens = 0
        output_tokens = 0

        for event in stream:
            # Capture TTFT on the very first incoming chunk
            if first_token_time is None:
                first_token_time = time.time()

            # Handle content text deltas
            if 'contentBlockDelta' in event:
                delta = event['contentBlockDelta']['delta']
                if 'text' in delta:
                    collected_text += delta['text']
                elif 'toolUse' in delta:
                    idx = event['contentBlockDelta']['contentBlockIndex']
                    tool_uses[idx]["input"] += delta['toolUse'].get('input', '')

            # Start of tool call block
            elif 'contentBlockStart' in event:
                start = event['contentBlockStart']['start']
                if 'toolUse' in start:
                    idx = event['contentBlockStart']['contentBlockIndex']
                    tool_uses[idx] = {
                        "toolUseId": start['toolUse']['toolUseId'],
                        "name": start['toolUse']['name'],
                        "input": ""
                    }

            # Final metadata event with token usage
            elif 'metadata' in event:
                metadata = event['metadata']
                if 'usage' in metadata:
                    input_tokens = metadata['usage'].get('inputTokens', 0)
                    output_tokens = metadata['usage'].get('outputTokens', 0)

        end_time = time.time()

        # Record and print metrics
        metrics = monitor.record_call(
            iteration=iteration,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            start_time=start_time,
            first_token_time=first_token_time or end_time,
            end_time=end_time
        )
        monitor.print_call_summary(metrics)

        # Assemble final message structure expected by agent.py
        formatted_content = []
        if collected_text:
            formatted_content.append({"text": collected_text})
        
        for tu in tool_uses.values():
            import json
            parsed_input = json.loads(tu["input"]) if isinstance(tu["input"], str) and tu["input"] else tu["input"]
            formatted_content.append({
                "toolUse": {
                    "toolUseId": tu["toolUseId"],
                    "name": tu["name"],
                    "input": parsed_input
                }
            })

        return {"role": "assistant", "content": formatted_content}

    except Exception as e:
        return {"role": "assistant", "content": [{"text": f"Error communicating with AWS Bedrock: {e}"}]}