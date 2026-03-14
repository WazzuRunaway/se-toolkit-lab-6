# Agent Documentation

## Overview
The `agent.py` script is a command-line interface (CLI) program that connects to a Large Language Model (LLM) via an OpenAI-compatible API and returns structured JSON answers to user questions. The agent has access to tools (`read_file`, `list_files`) that allow it to navigate the project wiki and answer questions with source references.

## Architecture

### Agentic Loop
The agent implements an agentic loop that:
1. Sends the user's question + tool definitions to the LLM
2. Parses the LLM response for tool calls
3. If tool calls exist:
   - Executes each tool
   - Appends results as tool messages
   - Loops back to step 1
4. If no tool calls (final answer):
   - Extracts answer and source
   - Outputs JSON and exits
5. Maximum 10 tool calls per question (safety limit)

```
Question ──▶ LLM ──▶ tool call? ──yes──▶ execute tool ──▶ back to LLM
                     │
                     no
                     │
                     ▼
                JSON output
```

### Components
- **Input**: Takes a question as the first command-line argument.
- **Processing**: Uses the OpenAI Python client with function calling support.
- **Tools**: `read_file` and `list_files` for navigating the project repository.
- **Output**: Returns a JSON object with `answer`, `source`, and `tool_calls` fields to stdout.
- **Error Handling**: Debug and error messages go to stderr; exits with code 0 on success.

## LLM Provider
This agent uses the Qwen Code API with the `qwen3-coder-plus` model, deployed on the user's VM. This provides 1000 free requests per day and strong tool-calling capabilities.

## Setup
1. Copy `.env.agent.example` to `.env.agent.secret`.
2. Fill in the actual values:
   - `LLM_API_KEY`: Your Qwen API key
   - `LLM_API_BASE`: The URL to your Qwen Code API endpoint (e.g., `http://<vm-ip>:<port>/v1`)
   - `LLM_MODEL`: `qwen3-coder-plus`

## Usage
```bash
uv run agent.py "How do you resolve a merge conflict?"
```

Example output:
```json
{
  "answer": "To resolve a merge conflict, choose which version to keep...",
  "source": "wiki/git.md#merge-conflict",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/git.md"}, "result": "..."}
  ]
}
```

## Tools

### `read_file`
Read a file from the project repository.

- **Parameters**: `path` (string) — relative path from project root.
- **Returns**: File contents as a string, or an error message if the file doesn't exist.
- **Security**: Blocks paths with `../` traversal to prevent accessing files outside the project directory.

### `list_files`
List files and directories at a given path.

- **Parameters**: `path` (string) — relative directory path from project root.
- **Returns**: Newline-separated listing of entries (directories end with `/`).
- **Security**: Blocks paths with `../` traversal to prevent accessing directories outside the project directory.

## System Prompt Strategy
The system prompt instructs the LLM to:
1. Use `list_files` to discover wiki files when asked about documentation
2. Use `read_file` to read specific files and find answers
3. Include source references in the format `wiki/filename.md#section-anchor`
4. Only call tools when needed; provide final answer when enough information is gathered

## Output Fields
- `answer` (string, required): The LLM's answer to the question.
- `source` (string, required): Reference to the wiki section that answers the question (e.g., `wiki/git-workflow.md#resolving-merge-conflicts`).
- `tool_calls` (array, required): All tool calls made during the agentic loop. Each entry has:
  - `tool`: Tool name (`read_file` or `list_files`)
  - `args`: Arguments passed to the tool
  - `result`: Tool output

## Dependencies
- `openai`: For API calls with function calling support
- `python-dotenv`: For loading environment variables

## Response Time
The agent is designed to respond within 60 seconds. If the LLM takes longer or exceeds 10 tool calls, it will error out or return partial results.

## Security
- Path validation prevents directory traversal (`../`)
- Only files within the project root can be accessed
- Uses `Path.resolve()` to verify actual file locations
