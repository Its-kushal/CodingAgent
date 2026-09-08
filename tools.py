import os
import subprocess
import shutil
import requests
from bs4 import BeautifulSoup

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "workspace"))


def delete_file(path: str) -> str:
    """Deletes a file or empty directory safely within the workspace."""
    target_path = os.path.abspath(os.path.join(WORKSPACE_DIR, path))
    if not target_path.startswith(WORKSPACE_DIR):
        return "ERROR: Security violation. Access denied."
    if not os.path.exists(target_path):
        return f"ERROR: Path not found at {path}"
    
    try:
        if os.path.isdir(target_path):
            os.rmdir(target_path) # Only removes empty directories for safety
            return f"SUCCESS: Directory {path} deleted."
        else:
            os.remove(target_path)
            return f"SUCCESS: File {path} deleted."
    except Exception as e:
        return f"ERROR: Could not delete {path}. {str(e)}"

def web_scrape(url: str) -> str:
    """Fetches and extracts raw text from a webpage."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for script in soup(["script", "style"]):
            script.extract()
            
        text = soup.get_text(separator='\n')
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text[:15000] 
    except Exception as e:
        return f"ERROR: Could not scrape {url}. {str(e)}"

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

def write_file(path: str, content) -> str:
    """Creates or overwrites a file, highly resilient to varying LLM JSON data shapes."""
    target_path = os.path.abspath(os.path.join(WORKSPACE_DIR, path))
    if not target_path.startswith(WORKSPACE_DIR):
        return "ERROR: Security violation. Access denied."
    
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    
    try:
        # 1. Handle List of Lists (e.g., CSV generation)
        if isinstance(content, list) and len(content) > 0 and isinstance(content[0], list):
            final_content = "\n".join(",".join(str(item) for item in row) for row in content)
        # 2. Handle List of Strings (e.g., Line-by-line code)
        elif isinstance(content, list):
            final_content = "\n".join(str(line) for line in content)
        # 3. Handle raw string dumps
        else:
            final_content = str(content)
            
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        return f"SUCCESS: File written to {path}"
    except Exception as e:
        return f"ERROR: Could not write file. {str(e)}"

def run_shell(command: str) -> str:
    """Executes a shell command inside the workspace with a strict 15-second timeout."""
    try:
        # cwd=WORKSPACE_DIR ensures the command runs ONLY inside the workspace folder
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKSPACE_DIR,
            capture_output=True,
            text=True,
            timeout=15 
        )
        output = result.stdout + result.stderr
        if result.returncode == 0:
            return f"SUCCESS (Exit Code 0):\n{output.strip()}"
        else:
            return f"FAILED (Exit Code {result.returncode}):\n{output.strip()}"
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out after 15 seconds."
    except Exception as e:
        return f"ERROR: Shell execution failed. {str(e)}"

TOOL_REGISTRY = {
    "read_file": read_file,
    "list_files": list_files,
    "write_file": write_file,
    "run_shell": run_shell,
    "delete_file": delete_file,
    "web_scrape": web_scrape
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads the content of a specific file.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Lists all files in a directory.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Creates or fully overwrites a file. Can accept raw text, an array of strings (lines of code), or an array of arrays (CSV rows).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to save the file"},
                    "content": {"description": "The exact source code or data to write."}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Executes a bash shell command in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Deletes a specified file or empty directory from the workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_scrape",
            "description": "Fetches and extracts readable text from a URL. Useful for reading documentation.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"]
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