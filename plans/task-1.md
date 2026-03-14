# Task 1: Call an LLM from Code - Implementation Plan

## LLM Provider and Model Choice
I will use the Qwen Code API as recommended, specifically the `qwen3-coder-plus` model. This provides 1000 free requests per day and supports strong tool calling capabilities, which will be useful for future tasks.

## Agent Structure
The agent will be implemented as a single Python script `agent.py` in the project root. It will:
1. Parse the command-line argument as the user question
2. Load environment variables from `.env.agent.secret`
3. Use the OpenAI Python client to call the LLM API
4. Format the response as JSON with `answer` and `tool_calls` fields
5. Output only valid JSON to stdout, with any debug info to stderr
6. Exit with code 0 on success

## Dependencies
- `openai` Python package for API calls
- `python-dotenv` for loading environment variables
- Standard library for JSON and sys

## Testing
Create a simple regression test that runs the agent as a subprocess and validates the JSON output structure.