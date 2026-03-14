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
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


# Maximum number of tool calls per question
MAX_TOOL_CALLS = 10


def load_env() -> None:
    """Load environment variables from .env.agent.secret."""
    env_file = Path(__file__).parent / ".env.agent.secret"
    if not env_file.exists():
        print(f"Error: {env_file} not found", file=sys.stderr)
        print("Copy .env.agent.example to .env.agent.secret and fill in the values", file=sys.stderr)
        sys.exit(1)
    load_dotenv(env_file)


def get_llm_config() -> tuple[str, str, str]:
    """Get LLM configuration from environment variables."""
    import os

    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL")

    if not api_key or api_key == "your-llm-api-key-here":
        print("Error: LLM_API_KEY not set in .env.agent.secret", file=sys.stderr)
        sys.exit(1)

    if not api_base or "<" in api_base:
        print("Error: LLM_API_BASE not set properly in .env.agent.secret", file=sys.stderr)
        sys.exit(1)

    if not model:
        print("Error: LLM_MODEL not set in .env.agent.secret", file=sys.stderr)
        sys.exit(1)

    return api_key, api_base, model


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


def get_tool_definitions() -> list[dict]:
    """Get tool definitions for OpenAI function calling."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file from the project repository. Use this to read specific files to find information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')"
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
                "description": "List files and directories at a given path. Use this to discover what files exist in a directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path from project root (e.g., 'wiki')"
                        }
                    },
                    "required": ["path"]
                }
            }
        }
    ]


def get_system_prompt() -> str:
    """Get the system prompt for the agent."""
    return """You are a documentation assistant for a software engineering toolkit project.
You have access to two tools:
- list_files: List files in a directory
- read_file: Read the contents of a file

When answering questions about the project documentation:
1. First use list_files to discover relevant files in the wiki/ directory
2. Then use read_file to read specific files and find the answer
3. When you have enough information, provide a final answer with a source reference

For the source reference, use the format: wiki/filename.md#section-anchor
where section-anchor is a lowercase version of the section title with hyphens instead of spaces.

Always be concise and accurate. Only call tools when necessary."""


def execute_tool(name: str, args: dict) -> str:
    """
    Execute a tool and return the result as a string.

    Args:
        name: Tool name ('read_file' or 'list_files')
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
                    "content": message.content,
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
                # Try to extract section from the content
                content = tool_call.get("result", "")
                if content and not content.startswith("Error:"):
                    # Return just the file path for now
                    # In a more sophisticated implementation, we could extract the section
                    return path

    # Default source
    return "wiki/"


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
