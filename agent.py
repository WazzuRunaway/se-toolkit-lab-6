#!/usr/bin/env python3
"""
Agent CLI — Call an LLM from Code

Usage:
    uv run agent.py "Your question here"

Output:
    JSON with 'answer' and 'tool_calls' fields to stdout.
    All debug/error messages go to stderr.
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


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


def call_lllm(question: str, api_key: str, api_base: str, model: str) -> str:
    """Call the LLM and return the answer."""
    client = OpenAI(api_key=api_key, base_url=api_base)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Answer questions concisely and accurately."},
            {"role": "user", "content": question},
        ],
        temperature=0.7,
        max_tokens=1024,
    )

    return response.choices[0].message.content


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

    try:
        answer = call_lllm(question, api_key, api_base, model)
    except Exception as e:
        print(f"Error calling LLM: {e}", file=sys.stderr)
        sys.exit(1)

    result = {
        "answer": answer,
        "tool_calls": [],
    }

    print(json.dumps(result))
    print("Done", file=sys.stderr)


if __name__ == "__main__":
    main()
