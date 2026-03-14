 pytest backend/tests/unit/test_agent.py -q
C:\Users\klimt\projects\SET\se-toolkit-lab-4\.venv\Scripts\python.exe: No module named pip

no tests ran in 0.02s
ERROR: file or directory not found: backend/tests/unit/test_agent.py

(learning-management-service) 
klimt@O_Computador MINGW64 ~/projects/SET (main)
$ cd se-toolkit-lab-6
(learning-management-service) 
klimt@O_Computador MINGW64 ~/projects/SET/se-toolkit-lab-6 (1-task-call-an-llm-from-code)
$ py -m pip install pytest
py -m pytest backend/tests/unit/test_agent.py -q
C:\Users\klimt\projects\SET\se-toolkit-lab-4\.venv\Scripts\python.exe: No module named pip
F                                                                   [100%]
================================ FAILURES ================================ 
____________________________ test_agent_basic ____________________________ 

    def test_agent_basic():
        """Test that agent.py outputs valid JSON with required fields."""  
        # Path to agent.py (repo root)
        repo_root = Path(__file__).parent.parent.parent.parent
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
>       assert result.returncode == 0
E       assert 1 == 0
E        +  where 1 = CompletedProcess(args=['C:\\Users\\klimt\\projects\\SET\\se-toolkit-lab-4\\.venv\\Scripts\\python.exe', 'C:\\Users\\kl...-6\\agent.py", line 13, in <module>\n    from openai import OpenAI\nModuleNotFoundError: No module named \'openai\'\n').returncode

backend\tests\unit\test_agent.py:27: AssertionError
============================ warnings summary ============================ 
..\se-toolkit-lab-4\.venv\Lib\site-packages\_pytest\config\__init__.py:1428

    self._warn_or_fail_if_strict(f"Unknown config option: {key}\n")

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== short test summary info =========================
FAILED backend/tests/unit/test_agent.py::test_agent_basic - assert 1 == 0
1 failed, 1 warning in 0.40s
(learning-management-service)
klimt@O_Computador MINGW64 ~/projects/SET/se-toolkit-lab-6 (1-task-call-an-llm-from-code)
$
yncio_mode
    self._warn_or_fail_if_strict(f"Unknown config option: {key}\n")

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== short test summary info =========================
FAILED backend/tests/unit/test_agent.py::test_agent_basic - assert 1 == 0
1 failed, 1 warning in 0.40s
(learning-management-service)# Advanced Agent Features

Extend your agent with advanced capabilities that improve reliability or expand what it can answer.

## Extension options

Choose **one or more** extensions. Each should measurably improve your agent — higher pass rate, lower latency, or better failure handling.

### Retry logic with backoff

LLM APIs have rate limits. Implement automatic retry with exponential backoff when the API returns 429 (Too Many Requests) or 5xx errors.

### Caching layer

Cache tool results in memory so that if the LLM calls `read_file("backend/app/main.py")` twice in the same run, the second call returns instantly.

### Direct database tool (`query_db`)

Add a `query_db` tool that runs **read-only** SQL queries against PostgreSQL directly. This lets the agent answer data questions without going through the API. Use a read-only connection to prevent accidental writes.

### Multi-step reasoning

Before executing tools, have the agent output a plan (what it needs to find out and which tools to use). Then execute the plan step by step. This improves accuracy on complex questions.

## Deliverables

### 1. Plan (`plans/optional-1.md`)

Document which extension(s) you chose, why, and the expected improvement.

### 2. Implementation (update `agent.py`)

Implement your chosen extension(s).

### 3. Tests

Write tests that demonstrate the extension works correctly.

### 4. Documentation (update `AGENT.md`)

Update `AGENT.md` to describe the extension(s) you implemented.

## Acceptance criteria

- [ ] At least one extension is implemented and working.
- [ ] Tests demonstrate the extension works correctly.
- [ ] `AGENT.md` is updated to describe the extension.
- [ ] [Git workflow](../../../wiki/git-workflow.md): issue `[Task] Advanced Agent Features`, branch, PR with `Closes #...`, partner approval, merge.
