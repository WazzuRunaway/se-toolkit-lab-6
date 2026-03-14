# Agent Documentation

## Overview
The `agent.py` script is a command-line interface (CLI) program that connects to a Large Language Model (LLM) via an OpenAI-compatible API and returns structured JSON answers to user questions.

## Architecture
- **Input**: Takes a question as the first command-line argument.
- **Processing**: Uses the OpenAI Python client to send the question to the configured LLM.
- **Output**: Returns a JSON object with `answer` and `tool_calls` fields to stdout.
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
uv run agent.py "What does REST stand for?"
```

Example output:
```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

## Dependencies
- `openai`: For API calls
- `python-dotenv`: For loading environment variables

## Response Time
The agent is designed to respond within 60 seconds. If the LLM takes longer, it will error out.