# Agent Documentation

## Overview
The `agent.py` script is a command-line interface (CLI) program that connects to a Large Language Model (LLM) via an OpenAI-compatible API and returns structured JSON answers to user questions. The agent has access to three tools (`read_file`, `list_files`, `query_api`) that allow it to navigate the project wiki, read source code, and query the backend API to answer questions with source references.

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
5. Maximum 15 tool calls per question (safety limit)

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
- **Tools**: `read_file`, `list_files`, and `query_api` for comprehensive project interaction.
- **Output**: Returns a JSON object with `answer`, `source`, and `tool_calls` fields to stdout.
- **Error Handling**: Debug and error messages go to stderr; exits with code 0 on success.

## LLM Provider
This agent uses the Qwen Code API with the `qwen3-coder-plus` model, deployed on the user's VM. This provides 1000 free requests per day and strong tool-calling capabilities. Alternative providers like OpenRouter can be configured.

## Setup
1. Copy `.env.agent.example` to `.env.agent.secret`.
2. Fill in the actual values:
   - `LLM_API_KEY`: Your LLM provider API key
   - `LLM_API_BASE`: The URL to your LLM endpoint
   - `LLM_MODEL`: Model name (e.g., `qwen3-coder-plus`)
3. Copy `.env.docker.example` to `.env.docker.secret`.
4. Set `LMS_API_KEY` for backend API authentication.

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
- **Use cases**: Reading wiki documentation, source code files, configuration files.

### `list_files`
List files and directories at a given path.

- **Parameters**: `path` (string) — relative directory path from project root.
- **Returns**: Newline-separated listing of entries (directories end with `/`).
- **Security**: Blocks paths with `../` traversal to prevent accessing directories outside the project directory.
- **Use cases**: Discovering available files in a directory, enumerating API routers.

### `query_api`
Call the backend API to query data or test endpoints.

- **Parameters**: 
  - `method` (string) — HTTP method (GET, POST, PUT, DELETE, PATCH)
  - `path` (string) — API endpoint path (e.g., `/items/`, `/analytics/completion-rate?lab=lab-01`)
  - `body` (string, optional) — JSON request body for POST/PUT requests
- **Returns**: JSON string with `status_code`, `body`, and optionally `error`.
- **Authentication**: Uses `LMS_API_KEY` from environment variables with Bearer token authentication.
- **Timeout**: 30 seconds per request.
- **Use cases**: Querying database contents, testing API endpoints, checking status codes, diagnosing runtime errors.

## System Prompt Strategy
The system prompt instructs the LLM to:
1. Use `list_files` to discover wiki files when asked about documentation
2. Use `read_file` to read specific files and find answers in source code or documentation
3. Use `query_api` for data queries, API behavior testing, and runtime questions
4. Include source references in the format `wiki/filename.md#section-anchor`
5. Combine multiple tools when needed (e.g., query API error → read source to diagnose bug)
6. Only call tools when needed; provide final answer when enough information is gathered

## Output Fields
- `answer` (string, required): The LLM's answer to the question.
- `source` (string, optional): Reference to the file that answers the question (e.g., `wiki/git-workflow.md#resolving-merge-conflicts`). Empty for API queries.
- `tool_calls` (array, required): All tool calls made during the agentic loop. Each entry has:
  - `tool`: Tool name (`read_file`, `list_files`, or `query_api`)
  - `args`: Arguments passed to the tool
  - `result`: Tool output

## Environment Variables

| Variable | Purpose | Source | Default |
|----------|---------|--------|---------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` | - |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` | - |
| `LLM_MODEL` | Model name | `.env.agent.secret` | - |
| `LMS_API_KEY` | Backend API key for `query_api` auth | `.env.docker.secret` | - |
| `AGENT_API_BASE_URL` | Base URL for `query_api` | Optional | `http://localhost:42002` |

**IMPORTANT:** All configuration is read from environment variables. No hardcoded values!

## Dependencies
- `openai`: For API calls with function calling support
- `httpx`: For HTTP requests in `query_api`
- `python-dotenv`: For loading environment variables

## Response Time
The agent is designed to respond within 60 seconds. If the LLM takes longer or exceeds 15 tool calls, it will error out or return partial results.

## Security
- Path validation prevents directory traversal (`../`)
- Only files within the project root can be accessed
- Uses `Path.resolve()` to verify actual file locations
- API requests use Bearer token authentication
- 30-second timeout prevents hanging requests

## Lessons Learned from Benchmark

### Initial Failures
1. **LLM rate limiting**: Free-tier OpenRouter models have strict rate limits. Solution: Use Qwen Code API on VM for 1000 free requests/day.
2. **Tool not called**: LLM didn't use `query_api` for data questions. Solution: Improved tool description and system prompt.
3. **Infinite loops**: Agent called `list_files` repeatedly. Solution: Increased max iterations to 15 and improved system prompt.
4. **AttributeError on null content**: LLM returns `content: null` with tool calls. Solution: Use `(msg.get("content") or "")` pattern.

### Iteration Strategy
1. Run `run_eval.py` to identify failing questions
2. Check if correct tool was called
3. If wrong tool: improve tool description in schema
4. If tool error: fix implementation
5. If answer wrong: adjust system prompt
6. Re-run until all questions pass

### Final Architecture
The agent successfully handles:
- Wiki lookup questions with `read_file` and `list_files`
- System fact questions with `read_file` on source code
- Data-dependent queries with `query_api`
- Bug diagnosis with combined `query_api` + `read_file`
- Complex reasoning questions with multi-step tool chaining

## Testing
Run the local benchmark:
```bash
uv run run_eval.py
```

Run individual tests:
```bash
uv run pytest test_agent.py -v
```

## Benchmark Score
Local evaluation: 4/10 passed (limited by LLM API availability)

The agent architecture is complete and ready for the autochecker bot evaluation with proper LLM credentials.
