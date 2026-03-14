"""Tests for agent.py"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv


def test_agent_basic():
    """Test that agent.py outputs valid JSON with required fields."""
    # Load LLM configuration from .env.agent.secret
    repo_root = Path(__file__).parent
    env_file = repo_root / ".env.agent.secret"
    load_dotenv(env_file)

    # Skip if LLM configuration is not provided (local dev environment)
    llm_base = os.environ.get("LLM_API_BASE", "")
    if not llm_base or "<" in llm_base:
        pytest.skip("LLM configuration missing; skipping integration test")

    # Path to agent.py (repo root)
    agent_path = repo_root / "agent.py"

    # Run agent as subprocess
    result = subprocess.run(
        [sys.executable, str(agent_path), "What is 2+2?"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        timeout=60,
    )

    # Should exit with code 0
    assert result.returncode == 0

    # Stdout should be valid JSON
    try:
        output = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        pytest.fail("Output is not valid JSON")

    # Check required fields
    assert "answer" in output
    assert "tool_calls" in output
    assert isinstance(output["tool_calls"], list)
    assert len(output["tool_calls"]) == 0

    # Answer should be a string
    assert isinstance(output["answer"], str)
