"""Tests for agent.py"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv


def load_env_and_check_config():
    """Load environment and check if LLM is configured."""
    repo_root = Path(__file__).parent
    env_file = repo_root / ".env.agent.secret"
    load_dotenv(env_file)

    llm_base = os.environ.get("LLM_API_BASE", "")
    if not llm_base or "<" in llm_base:
        pytest.skip("LLM configuration missing; skipping integration test")

    return repo_root


def test_agent_basic():
    """Test that agent.py outputs valid JSON with required fields (no tools)."""
    repo_root = load_env_and_check_config()
    agent_path = repo_root / "agent.py"

    result = subprocess.run(
        [sys.executable, str(agent_path), "What is 2+2?"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        timeout=60,
    )

    assert result.returncode == 0

    try:
        output = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        pytest.fail("Output is not valid JSON")

    assert "answer" in output
    assert "tool_calls" in output
    assert isinstance(output["tool_calls"], list)
    assert isinstance(output["answer"], str)


def test_agent_list_files():
    """Test that agent uses list_files tool for wiki directory question."""
    repo_root = load_env_and_check_config()
    agent_path = repo_root / "agent.py"

    result = subprocess.run(
        [sys.executable, str(agent_path), "What files are in the wiki directory?"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        timeout=60,
    )

    assert result.returncode == 0

    try:
        output = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        pytest.fail("Output is not valid JSON")

    # Check required fields
    assert "answer" in output
    assert "source" in output
    assert "tool_calls" in output

    # Should have used list_files tool
    tool_calls = output["tool_calls"]
    assert len(tool_calls) > 0, "Expected at least one tool call"

    # Find list_files call
    list_files_calls = [tc for tc in tool_calls if tc.get("tool") == "list_files"]
    assert len(list_files_calls) > 0, "Expected list_files tool to be called"

    # Verify list_files was called with wiki path
    wiki_list_call = [tc for tc in list_files_calls if tc.get("args", {}).get("path") == "wiki"]
    assert len(wiki_list_call) > 0, "Expected list_files to be called with path 'wiki'"


def test_agent_read_file_merge_conflict():
    """Test that agent uses read_file tool for merge conflict question."""
    repo_root = load_env_and_check_config()
    agent_path = repo_root / "agent.py"

    result = subprocess.run(
        [sys.executable, str(agent_path), "How do you resolve a merge conflict?"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        timeout=60,
    )

    assert result.returncode == 0

    try:
        output = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        pytest.fail("Output is not valid JSON")

    # Check required fields
    assert "answer" in output
    assert "source" in output
    assert "tool_calls" in output

    # Should have used read_file tool
    tool_calls = output["tool_calls"]
    assert len(tool_calls) > 0, "Expected at least one tool call"

    # Find read_file calls
    read_file_calls = [tc for tc in tool_calls if tc.get("tool") == "read_file"]
    assert len(read_file_calls) > 0, "Expected read_file tool to be called"

    # Source should reference a wiki file
    source = output.get("source", "")
    assert source, "Expected source field to be populated"
    assert "wiki/" in source or ".md" in source, f"Expected source to reference wiki file, got: {source}"


def test_agent_read_file_framework():
    """Test that agent uses read_file tool for backend framework question."""
    repo_root = load_env_and_check_config()
    agent_path = repo_root / "agent.py"

    result = subprocess.run(
        [sys.executable, str(agent_path), "What framework does the backend use?"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        timeout=60,
    )

    assert result.returncode == 0

    try:
        output = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        pytest.fail("Output is not valid JSON")

    # Check required fields
    assert "answer" in output
    assert "tool_calls" in output

    # Should have used read_file tool to read source code
    tool_calls = output["tool_calls"]
    assert len(tool_calls) > 0, "Expected at least one tool call"

    # Find read_file calls
    read_file_calls = [tc for tc in tool_calls if tc.get("tool") == "read_file"]
    assert len(read_file_calls) > 0, "Expected read_file tool to be called for source code question"


def test_agent_query_api_items_count():
    """Test that agent uses query_api tool for database items count question."""
    repo_root = load_env_and_check_config()
    agent_path = repo_root / "agent.py"

    result = subprocess.run(
        [sys.executable, str(agent_path), "How many items are in the database?"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        timeout=60,
    )

    assert result.returncode == 0

    try:
        output = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        pytest.fail("Output is not valid JSON")

    # Check required fields
    assert "answer" in output
    assert "tool_calls" in output

    # Should have used query_api tool for data query
    tool_calls = output["tool_calls"]
    assert len(tool_calls) > 0, "Expected at least one tool call"

    # Find query_api calls
    query_api_calls = [tc for tc in tool_calls if tc.get("tool") == "query_api"]
    assert len(query_api_calls) > 0, "Expected query_api tool to be called for database question"
