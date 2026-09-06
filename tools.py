import os

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "workspace"))

def read_file(path: str) -> str:
    target_path = os.path.abspath(os.path.join(WORKSPACE_DIR, path))
    if not target_path.startswith(WORKSPACE_DIR):
        return "ERROR: Security violation."
    if not os.path.exists(target_path):
        return f"ERROR: File not found at {path}"
    try:
        with open(target_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"ERROR: Could not read file. {str(e)}"

def list_files(path: str = ".") -> str:
    """Lists files and directories in the workspace."""
    target_path = os.path.abspath(os.path.join(WORKSPACE_DIR, path))
    if not target_path.startswith(WORKSPACE_DIR):
        return "ERROR: Security violation."
    if not os.path.exists(target_path):
        return f"ERROR: Directory not found at {path}"
    try:
        items = os.listdir(target_path)
        return "\n".join(items) if items else "Directory is empty."
    except Exception as e:
        return f"ERROR: Could not list directory. {str(e)}"

TOOL_REGISTRY = {
    "read_file": read_file,
    "list_files": list_files
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads the content of a specific file.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Path to the file"}},
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Lists all files in a directory to see what exists before reading them.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Directory path (use '.' for root)"}},
                "required": ["path"]
            }
        }
    }
]

def execute_tool(name: str, args: dict) -> str:
    if name not in TOOL_REGISTRY:
        return f"ERROR: Tool '{name}' does not exist."
    try:
        return str(TOOL_REGISTRY[name](**args))
    except Exception as e:
        return f"ERROR: Tool execution failed. {str(e)}"