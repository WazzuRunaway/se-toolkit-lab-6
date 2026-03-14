# Task 2: The Documentation Agent - Implementation Plan

## Overview
Transform the CLI from Task 1 into an agentic loop that can call tools (`read_file`, `list_files`) to navigate the project wiki and answer questions with source references.

## Agentic Loop Architecture

The loop will:
1. Send user question + tool definitions to LLM
2. Parse LLM response for tool calls
3. If tool calls exist:
   - Execute each tool
   - Append results as tool messages
   - Loop back to step 1
4. If no tool calls (final answer):
   - Extract answer and source
   - Output JSON and exit
5. Maximum 10 tool calls per question (safety limit)

## Tool Definitions

### `read_file`
- **Purpose**: Read contents of a file from the project repository
- **Parameters**: `path` (string) — relative path from project root
- **Returns**: File contents as string, or error message
- **Security**: Block paths with `../` traversal

### `list_files`
- **Purpose**: List files and directories at a given path
- **Parameters**: `path` (string) — relative directory path from project root
- **Returns**: Newline-separated listing of entries
- **Security**: Block paths with `../` traversal

## Tool Schema (OpenAI Function Calling)

Tools will be defined as JSON schemas in the OpenAI API format:

```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "Read a file from the project repository",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string", "description": "Relative path from project root"}
      },
      "required": ["path"]
    }
  }
}
```

## System Prompt Strategy

The system prompt will instruct the LLM to:
1. Use `list_files` to discover wiki files when asked about documentation
2. Use `read_file` to read specific files and find answers
3. Include source references in the format `wiki/filename.md#section-anchor`
4. Only call tools when needed; provide final answer when enough information is gathered

## Output Format

```json
{
  "answer": "The answer text",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "..."}
  ]
}
```

## Security Considerations

- Validate all paths to prevent directory traversal (`../`)
- Only allow paths within the project root
- Use `Path.resolve()` to check actual file locations

## Testing Strategy

Two regression tests:
1. Question about merge conflicts → expects `read_file` tool, `wiki/git-workflow.md` in source
2. Question about wiki files → expects `list_files` tool

## Dependencies

- `openai` — for LLM API with function calling support
- `python-dotenv` — for environment variables
- Standard library: `json`, `sys`, `pathlib`
