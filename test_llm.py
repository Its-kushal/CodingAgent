from llm import chat

messages = [
    {"role": "system", "content": "You are a senior developer. Be concise."},
    {"role": "user", "content": "Write a 1-line Python function to reverse a string."}
]

print("Thinking...")
response = chat(messages)
print("\nResponse:")
print(response)