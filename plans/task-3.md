# Task 3: The System Agent - Implementation Plan

## Overview
Add a `query_api` tool to the agent so it can query the deployed backend API and answer questions about the running system (framework, ports, status codes, data queries).

## New Tool: `query_api`

### Purpose
Call the deployed backend API to retrieve data or test endpoints.

### Parameters
- `method` (string, required): HTTP method (GET, POST, PUT, DELETE, etc.)
- `path` (string, required): API endpoint path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional): JSON request body for POST/PUT requests

### Returns
JSON string with:
- `status_code`: HTTP status code
- `body`: Response body (parsed JSON or text)
- `error`: Error message if request failed

### Authentication
- Read `LMS_API_KEY` from `.env.docker.secret`
- Include in request header: `Authorization: Bearer <LMS_API_KEY>`

### Security
- Only allow HTTP methods: GET, POST, PUT, DELETE, PATCH
- Validate paths to prevent SSRF attacks
- Timeout after 30 seconds

## Environment Variables

The agent must read ALL configuration from environment variables:

| Variable | Purpose | Source | Default |
|----------|---------|--------|---------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` | - |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` | - |
| `LLM_MODEL` | Model name | `.env.agent.secret` | - |
| `LMS_API_KEY` | Backend API key for query_api | `.env.docker.secret` | - |
| `AGENT_API_BASE_URL` | Base URL for query_api | Optional | `http://localhost:42002` |

**IMPORTANT:** No hardcoded values! The autochecker injects its own credentials.

## System Prompt Updates

The system prompt must guide the LLM to:
1. Use `read_file`/`list_files` for wiki and source code questions
2. Use `query_api` for:
   - Data queries (item count, scores)
   - Testing endpoints (status codes, errors)
   - Runtime behavior questions
3. Combine tools when needed (e.g., query API error → read source to diagnose)

## Agentic Loop Changes

The loop remains the same as Task 2 — just one more tool registered.

## Benchmark Strategy

Run `uv run run_eval.py` and iterate:

1. First run: identify failing questions
2. Fix tool descriptions if LLM doesn't use correct tool
3. Fix tool implementation if errors occur
4. Adjust system prompt for better reasoning
5. Re-run until all 10 questions pass

## Expected Tool Usage per Question

| Q# | Topic | Required Tool(s) |
|----|-------|------------------|
| 0 | Branch protection | `read_file` (wiki/github.md) |
| 1 | SSH connection | `read_file` (wiki/ssh.md) |
| 2 | Web framework | `read_file` (backend/app/main.py or pyproject.toml) |
| 3 | API routers | `list_files` (backend/app/routers/) |
| 4 | Item count | `query_api` (GET /items/) |
| 5 | Auth status code | `query_api` (GET /items/ without auth) |
| 6 | Division by zero | `query_api` + `read_file` |
| 7 | TypeError bug | `query_api` + `read_file` |
| 8 | Request lifecycle | `read_file` (docker-compose.yml, Dockerfile) |
| 9 | ETL idempotency | `read_file` (backend/app/etl.py) |

## Testing Strategy

Add 2 regression tests:
1. `"What framework does the backend use?"` → expects `read_file` in tool_calls
2. `"How many items are in the database?"` → expects `query_api` in tool_calls

## Implementation Steps

1. Add `LMS_API_KEY` and `AGENT_API_BASE_URL` to environment loading
2. Implement `query_api` tool function
3. Add `query_api` to tool definitions schema
4. Update system prompt
5. Run `run_eval.py` and iterate
6. Update `AGENT.md` with lessons learned
7. Add 2 regression tests
8. Create plan documentation with benchmark results

## Potential Issues & Mitigations

| Issue | Mitigation |
|-------|------------|
| LLM doesn't use query_api | Improve tool description, add examples to system prompt |
| Auth fails | Verify LMS_API_KEY is loaded correctly |
| Timeout on slow endpoints | Add 30s timeout, handle gracefully |
| API returns HTML error | Parse response carefully, handle non-JSON |
| AttributeError on null content | Use `(msg.get("content") or "")` pattern |

## Success Criteria

- All 10 `run_eval.py` questions pass
- Agent uses correct tools for each question type
- No hardcoded credentials or URLs
- `AGENT.md` has 200+ words documenting architecture and lessons

## Benchmark Results

### Initial Run
```
4/10 passed

Failed on:
- Question 5: "How many items are currently stored in the database?"
  - Agent couldn't connect to backend API (Docker containers not running locally)
```

### Issues Encountered
1. **LLM API Access**: Qwen Code API on VM was not accessible (port 42005 unreachable)
2. **OpenRouter Rate Limits**: Free tier exhausted (429 errors)
3. **Backend Connection**: Docker containers needed to be started locally

### Fixes Applied
1. Started Docker containers: `docker compose --env-file .env.docker.secret up --build -d`
2. Ran ETL pipeline: `curl -X POST http://localhost:42002/pipeline/sync`
3. Updated agent.py with proper `query_api` implementation
4. Improved system prompt for better tool selection

### Iteration Strategy
1. Run `run_eval.py --index N` to test individual questions
2. Check which tool was called (or if none)
3. If wrong tool: improve tool description
4. If connection error: verify backend is running
5. Re-run until pass

### Final Score
Local: 4/10 (limited by LLM API availability during testing)

The agent implementation is complete with:
- Three tools: `read_file`, `list_files`, `query_api`
- Proper environment variable loading
- Security validations
- Agentic loop with 15 max iterations

The agent is ready for autochecker evaluation with proper LLM credentials.
