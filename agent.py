#!/usr/bin/env python3
"""
Agent CLI — Call an LLM from Code with Tools

Usage:
    uv run agent.py "Your question here"

Output:
    JSON with 'answer', 'source', and 'tool_calls' fields to stdout.
    All debug/error messages go to stderr.
"""

import json
import os
import sys
from pathlib import Path
from urllib.parse import urljoin

import httpx
from dotenv import load_dotenv
from openai import OpenAI


# Maximum number of tool calls per question
MAX_TOOL_CALLS = 15


def load_env() -> None:
    """Load environment variables from .env files."""
    # Load LLM config from .env.agent.secret
    env_file_agent = Path(__file__).parent / ".env.agent.secret"
    if env_file_agent.exists():
        load_dotenv(env_file_agent)
    
    # Load LMS API key from .env.docker.secret
    env_file_docker = Path(__file__).parent / ".env.docker.secret"
    if env_file_docker.exists():
        load_dotenv(env_file_docker)
    
    # Also try loading from .env for compatibility
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)


def get_llm_config() -> tuple[str, str, str]:
    """Get LLM configuration from environment variables."""
    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL")

    if not api_key or api_key == "your-llm-api-key-here":
        print("Error: LLM_API_KEY not set in environment", file=sys.stderr)
        sys.exit(1)

    if not api_base or "<" in api_base:
        print("Error: LLM_API_BASE not set properly in environment", file=sys.stderr)
        sys.exit(1)

    if not model:
        print("Error: LLM_MODEL not set in environment", file=sys.stderr)
        sys.exit(1)

    return api_key, api_base, model


def get_api_config() -> tuple[str, str]:
    """Get API configuration from environment variables."""
    lms_api_key = os.getenv("LMS_API_KEY")
    api_base_url = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")
    
    if not lms_api_key:
        print("Warning: LMS_API_KEY not set in environment", file=sys.stderr)
    
    return lms_api_key, api_base_url


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent


def validate_path(path: str) -> tuple[bool, str]:
    """
    Validate that a path is within the project directory.
    Returns (is_valid, error_message).
    """
    # Check for directory traversal
    if ".." in path:
        return False, "Path traversal not allowed"

    # Resolve the full path
    project_root = get_project_root()
    try:
        full_path = (project_root / path).resolve()
        # Check if the resolved path is within project root
        if not str(full_path).startswith(str(project_root.resolve())):
            return False, "Path is outside project directory"
    except Exception as e:
        return False, f"Invalid path: {e}"

    return True, ""


def read_file(path: str) -> dict:
    """
    Read a file from the project repository.

    Args:
        path: Relative path from project root.

    Returns:
        Dict with 'success' and 'content' or 'error' keys.
    """
    is_valid, error = validate_path(path)
    if not is_valid:
        return {"success": False, "error": error}

    project_root = get_project_root()
    full_path = project_root / path

    if not full_path.exists():
        return {"success": False, "error": f"File not found: {path}"}

    if not full_path.is_file():
        return {"success": False, "error": f"Not a file: {path}"}

    try:
        content = full_path.read_text()
        return {"success": True, "content": content}
    except Exception as e:
        return {"success": False, "error": f"Error reading file: {e}"}


def list_files(path: str) -> dict:
    """
    List files and directories at a given path.

    Args:
        path: Relative directory path from project root.

    Returns:
        Dict with 'success' and 'entries' or 'error' keys.
    """
    is_valid, error = validate_path(path)
    if not is_valid:
        return {"success": False, "error": error}

    project_root = get_project_root()
    full_path = project_root / path

    if not full_path.exists():
        return {"success": False, "error": f"Path not found: {path}"}

    if not full_path.is_dir():
        return {"success": False, "error": f"Not a directory: {path}"}

    try:
        entries = []
        for entry in sorted(full_path.iterdir()):
            suffix = "/" if entry.is_dir() else ""
            entries.append(f"{entry.name}{suffix}")
        return {"success": True, "entries": "\n".join(entries)}
    except Exception as e:
        return {"success": False, "error": f"Error listing files: {e}"}


def query_api(method: str, path: str, body: str = None, authorize: bool = True) -> dict:
    """
    Call the backend API.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        path: API endpoint path (e.g., /items/)
        body: Optional JSON request body (as string)
        authorize: Whether to include Authorization header (default: True)

    Returns:
        Dict with 'success', 'status_code', 'body', and optionally 'error'.
    """
    lms_api_key, api_base_url = get_api_config()
    
    # Validate method
    allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
    method = method.upper()
    if method not in allowed_methods:
        return {"success": False, "error": f"Method '{method}' not allowed"}
    
    # Validate path (basic check)
    if not path.startswith("/"):
        return {"success": False, "error": "Path must start with /"}
    
    if ".." in path:
        return {"success": False, "error": "Path traversal not allowed"}
    
    # Build URL
    try:
        url = urljoin(api_base_url.rstrip("/") + "/", path.lstrip("/"))
    except Exception as e:
        return {"success": False, "error": f"Invalid URL: {e}"}
    
    # Build headers
    headers = {}
    if lms_api_key and authorize:
        headers["Authorization"] = f"Bearer {lms_api_key}"
    
    # Build request
    try:
        with httpx.Client(timeout=30.0) as client:
            kwargs = {"headers": headers}
            
            if body:
                try:
                    kwargs["json"] = json.loads(body)
                except json.JSONDecodeError:
                    return {"success": False, "error": "Invalid JSON body"}
            
            response = client.request(method, url, **kwargs)
            
            # Try to parse JSON response
            try:
                response_body = response.json()
            except (json.JSONDecodeError, Exception):
                response_body = response.text
            
            return {
                "success": True,
                "status_code": response.status_code,
                "body": response_body,
                "headers": dict(response.headers)
            }
            
    except httpx.TimeoutException:
        return {"success": False, "error": "Request timed out (30s)"}
    except httpx.RequestError as e:
        return {"success": False, "error": f"Request failed: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {e}"}


def get_tool_definitions() -> list[dict]:
    """Get tool definitions for OpenAI function calling."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file from the project repository. Use this to read source code, configuration files, or documentation to find specific information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path from project root (e.g., 'wiki/git-workflow.md', 'backend/app/main.py', 'docker-compose.yml')"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories at a given path. Use this to discover what files exist in a directory structure.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path from project root (e.g., 'wiki', 'backend/app/routers')"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_api",
                "description": "Call the backend API to query data or test endpoints. Use this for questions about database contents, API behavior, status codes, or runtime errors. For testing authentication errors, set authorize=false to send requests without credentials.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "HTTP method: GET, POST, PUT, DELETE, PATCH"
                        },
                        "path": {
                            "type": "string",
                            "description": "API endpoint path (e.g., '/items/', '/analytics/completion-rate?lab=lab-01')"
                        },
                        "body": {
                            "type": "string",
                            "description": "Optional JSON request body as a string (for POST/PUT requests)"
                        },
                        "authorize": {
                            "type": "boolean",
                            "description": "Whether to include Authorization header (default: true). Set to false to test authentication errors (e.g., getting 401/403 status codes)"
                        }
                    },
                    "required": ["method", "path"]
                }
            }
        }
    ]


def get_system_prompt() -> str:
    """Get the system prompt for the agent."""
    return """You are a helpful assistant for a software engineering toolkit project.
You have access to three tools:
- list_files: List files in a directory
- read_file: Read the contents of a file
- query_api: Call the backend API to query data or test endpoints

## When to use each tool:

### Use `read_file` when:
- Asked about wiki documentation or specific files
- Asked about source code (e.g., "what framework does the backend use?")
- Asked about configuration (docker-compose.yml, Dockerfile, etc.)
- Need to find specific information in a file

### Use `list_files` when:
- Asked what files exist in a directory
- Need to discover available modules or routers
- Asked to enumerate API endpoints or components

### Use `query_api` when:
- Asked about data in the database (e.g., "how many items...?")
- Asked about API behavior (status codes, responses)
- Asked to test an endpoint or find errors
- Asked about runtime behavior or completion rates
- Asked about authentication errors (use authorize=false to test without credentials)

## Strategy:
1. For wiki questions: use `read_file` on the relevant wiki file
2. For source code questions: use `read_file` on the relevant source file
3. For data questions: use `query_api` with the appropriate endpoint
4. For authentication errors (e.g., "What status code without auth?"): use `query_api` with authorize=false
5. For API errors: use `query_api` to reproduce the error, then `read_file` to find the bug in source code
6. For complex questions: combine multiple tools as needed

## Output format:
- Provide concise, accurate answers
- Include source references when reading files (e.g., "wiki/git.md#merge-conflict")
- For API queries, report the actual data returned
- When diagnosing bugs, explain both the error and the root cause in the code

Always be precise. Only call tools when necessary."""


def execute_tool(name: str, args: dict) -> str:
    """
    Execute a tool and return the result as a string.

    Args:
        name: Tool name
        args: Tool arguments

    Returns:
        Tool result as a string
    """
    if name == "read_file":
        path = args.get("path", "")
        result = read_file(path)
        if result["success"]:
            return result["content"]
        else:
            return f"Error: {result['error']}"

    elif name == "list_files":
        path = args.get("path", "")
        result = list_files(path)
        if result["success"]:
            return result["entries"]
        else:
            return f"Error: {result['error']}"

    elif name == "query_api":
        method = args.get("method", "GET")
        path = args.get("path", "")
        body = args.get("body")
        authorize = args.get("authorize", True)  # Default to True for backward compatibility
        result = query_api(method, path, body, authorize)

        if result["success"]:
            # Format the response
            output = f"Status: {result['status_code']}\n"
            output += f"Body: {json.dumps(result['body'], indent=2)}"
            return output
        else:
            return f"Error: {result['error']}"

    else:
        return f"Error: Unknown tool '{name}'"


def call_llm_with_tools(
    question: str,
    api_key: str,
    api_base: str,
    model: str,
    tool_calls_log: list[dict]
) -> tuple[str, list[dict]]:
    """
    Call the LLM with tool support and execute the agentic loop.

    Args:
        question: User's question
        api_key: LLM API key
        api_base: LLM API base URL
        model: Model name
        tool_calls_log: List to accumulate tool call records

    Returns:
        Tuple of (final_answer, tool_calls_log)
    """
    client = OpenAI(api_key=api_key, base_url=api_base)

    # Initialize conversation messages
    messages = [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": question}
    ]

    tool_definitions = get_tool_definitions()

    for iteration in range(MAX_TOOL_CALLS):
        print(f"Loop iteration {iteration + 1}/{MAX_TOOL_CALLS}", file=sys.stderr)

        # Call LLM
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tool_definitions,
            temperature=0.7,
            max_tokens=1024,
        )

        choice = response.choices[0]
        message = choice.message

        # Check if LLM wants to call tools
        if message.tool_calls:
            # Log tool calls and execute them
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                print(f"Calling tool: {tool_name} with args: {tool_args}", file=sys.stderr)

                # Execute the tool
                tool_result = execute_tool(tool_name, tool_args)

                # Log the tool call
                tool_call_record = {
                    "tool": tool_name,
                    "args": tool_args,
                    "result": tool_result
                }
                tool_calls_log.append(tool_call_record)

                # Add assistant message with tool call
                messages.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [tool_call]
                })

                # Add tool result as a separate message
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                })

            # Continue loop to get LLM response with tool results
            continue

        else:
            # No tool calls - this is the final answer
            print(f"Final answer received", file=sys.stderr)
            return message.content, tool_calls_log

    # Reached max iterations
    print("Reached maximum tool calls limit", file=sys.stderr)
    return "I reached the maximum number of tool calls. Here's what I found so far.", tool_calls_log


def extract_source_from_tool_calls(tool_calls_log: list[dict]) -> str:
    """
    Extract source reference from tool calls log.

    Args:
        tool_calls_log: List of tool call records

    Returns:
        Source reference string (e.g., 'wiki/git-workflow.md#resolving-merge-conflicts')
    """
    # Find the last read_file call
    for tool_call in reversed(tool_calls_log):
        if tool_call["tool"] == "read_file":
            path = tool_call["args"].get("path", "")
            if path:
                return path

    # Default source
    return ""


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"Your question here\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    print(f"Processing question: {question}", file=sys.stderr)

    load_env()
    api_key, api_base, model = get_llm_config()

    print(f"Calling LLM: {model} at {api_base}", file=sys.stderr)

    tool_calls_log: list[dict] = []

    try:
        answer, tool_calls_log = call_llm_with_tools(
            question, api_key, api_base, model, tool_calls_log
        )
    except Exception as e:
        print(f"Error calling LLM: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract source from tool calls
    source = extract_source_from_tool_calls(tool_calls_log)

    result = {
        "answer": answer,
        "source": source,
        "tool_calls": tool_calls_log,
    }

    print(json.dumps(result))
    print("Done", file=sys.stderr)


if __name__ == "__main__":
    main()
