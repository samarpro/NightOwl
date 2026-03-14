# NightOwl Test Guide

## Quick Reference

```bash
# Run all tests (from api/)
cd api && pdm run pytest

# Run a specific module's tests
pdm run pytest nightowl/sessions/tests/test_manager.py

# Run a single test class
pdm run pytest nightowl/models/tests/test_models.py::TestSessionModel

# Run integration tests (requires BEDROCK_API_KEY)
pdm run pytest nightowl/sessions/tests/test_integration.py

# Verbose output
pdm run pytest -v
```

## Stack

| Tool | Version | Purpose |
|------|---------|---------|
| pytest | >= 9.0.2 | Test runner |
| pytest-asyncio | >= 1.3.0 | Async test support (`asyncio_mode = "auto"`) |
| PDM | — | Dependency/script management |

Dependencies live in the `[dependency-groups] test` section of `api/pyproject.toml`.

## Configuration

All pytest config is in `api/pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"          # no need for @pytest.mark.asyncio
testpaths = ["nightowl"]       # discovery root
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

## Directory Layout

Tests live in a `tests/` subdirectory inside each package — never colocated as siblings of the module under test.

```
api/nightowl/
├── models/
│   ├── session.py
│   ├── message.py
│   ├── approval.py
│   ├── observability.py
│   └── tests/
│       ├── __init__.py
│       └── test_models.py          # all model tests in one file
├── sessions/
│   ├── manager.py
│   ├── runner.py
│   ├── depth.py
│   ├── prompt_builder.py
│   ├── tools.py
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py             # shared fixtures for this package
│       ├── test_manager.py
│       ├── test_depth.py
│       ├── test_prompt_builder.py
│       ├── test_tools.py
│       └── test_integration.py     # requires live Bedrock
├── config.py       # ❌ no tests yet
├── cli.py          # ❌ no tests yet
├── db.py           # ❌ no tests yet
└── main.py         # ❌ no tests yet
```

## Writing Tests

### Rules

1. **Behaviour-driven, not implementation-coupled.** Test what a function *does*, not how it does it internally.
2. **One test class per behaviour group.** Group related assertions under a `Test*` class. Each method tests one thing.
3. **Descriptive names.** `test_spawns_child_with_correct_depth` — no `test_1`, no abbreviations.
4. **Async by default.** `asyncio_mode = "auto"` means you just write `async def test_*` — no decorator needed.
5. **Minimal mocking.** Test real objects wherever possible. Only mock external boundaries (Bedrock API, filesystem). Use `unittest.mock.MagicMock` when you must.
6. **No prompt injection / PII / content filtering tests.** Bedrock Guardrails handles that layer — don't reimplement it in tests.

### Fixture Patterns

**Package-scoped conftest.py** — each `tests/` dir can have its own conftest with shared fixtures:

```python
# nightowl/sessions/tests/conftest.py
@pytest.fixture
def manager() -> SessionManager:
    return SessionManager()

@pytest.fixture
def manager_with_broadcast() -> tuple[SessionManager, asyncio.Queue]:
    m = SessionManager()
    q: asyncio.Queue = asyncio.Queue()
    m.set_broadcast_queue(q)
    return m, q
```

**Factory helpers** — for constructing test objects, use module-level functions prefixed with `_`:

```python
def _make_session(role: SessionRole, depth: int = 0, **kwargs) -> Session:
    return Session(id="session:test", role=role, depth=depth, ...)
```

**Fake dependencies** — use `@dataclass` for minimal stand-ins:

```python
@dataclass
class _FakeCtx:
    deps: AgentState
```

### Async Queue Testing

For testing message delivery through `asyncio.Queue`, always use a timeout:

```python
msg = await asyncio.wait_for(q.get(), timeout=1)
assert "expected content" in msg
```

### Integration Tests

Integration tests that hit real services use conditional skip marks:

```python
needs_bedrock = pytest.mark.skipif(
    not settings.bedrock_api_key,
    reason="BEDROCK_API_KEY not set",
)

@needs_bedrock
class TestBedrockInvocation:
    async def test_agent_responds(self):
        ...
```

These are safe to run in CI without credentials — they skip cleanly.

## Adding Tests for a New Module

1. Create `nightowl/<package>/tests/__init__.py`
2. Create `nightowl/<package>/tests/test_<module>.py`
3. If fixtures are needed, add a `conftest.py` in that `tests/` dir
4. Follow the class-per-behaviour-group pattern
5. Run `pdm run pytest nightowl/<package>/tests/` to verify

## Coverage Gaps

The following modules have no tests yet. When adding features to these, tests are expected:

| Module | Notes |
|--------|-------|
| `config.py` | Settings loading — test env var parsing, defaults |
| `cli.py` | CLI entrypoint — test argument parsing, not Bedrock calls |
| `db.py` | Database layer — test against real DB, not mocks |
| `main.py` | FastAPI app — test route handlers with `httpx.AsyncClient` |
| `sessions/runner.py` | Session execution — unit tests for orchestration logic, integration tests for Bedrock |
