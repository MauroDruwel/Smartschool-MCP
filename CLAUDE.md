# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install all dependencies (including dev)
uv sync --extra dev

# Run all tests
uv run pytest

# Run a single test
uv run pytest tests/test_tools.py::test_get_courses_returns_list

# Lint
uv run ruff check .

# Format (check only)
uv run ruff format --check .

# Format (apply)
uv run ruff format .

# Type check
uv run mypy smartschool_mcp/
```

CI runs lint → typecheck → tests (Python 3.10–3.13) in that order. All three must pass before merging.

## Architecture

The package is a single-file MCP server (`smartschool_mcp/server.py`) plus an entry-point module (`smartschool_mcp/__main__.py`).

### Transport modes

`__main__.py` handles two transports selected via `--transport` (or `MCP_TRANSPORT` env var):

- **`stdio`** (default) — used by Claude Desktop; calls `mcp.run()` directly.
- **`streamable-http`** — used by claude.ai remote integrations; builds a Starlette ASGI app via `mcp.streamable_http_app()`, wraps it in `CORSMiddleware` (required so claude.ai can read `Mcp-Session-Id`), then optionally wraps that in `_BearerAuthMiddleware` (enabled by setting `MCP_API_KEY`). Served with uvicorn on `MCP_HOST:MCP_PORT`.

### Tool registration

All MCP tools live in `server.py` and are registered with `@mcp.tool()` decorators on plain Python functions. `FastMCP("Smartschool MCP")` is the server instance (`mcp`). Adding a new tool means writing a new `@mcp.tool()` function — no registration table to update.

### Session and credentials

`_session()` is an `@lru_cache(maxsize=1)` function that creates a `Smartschool(EnvCredentials())` instance on first call. It is lazy on purpose — startup never touches the network, so missing credentials surface as tool-level errors rather than process crashes. In tests, `conftest.py` patches `_session` with an `autouse` fixture so no real credentials are needed.

### `smartschool` library

The upstream library (`github.com/svaningelgem/smartschool`, pinned via `uv.lock`) exposes lazy-loaded objects. Accessing `.details` on a result, for example, triggers an HTTP request. Many attributes use `getattr(..., default)` defensively because the library's type stubs are incomplete. Every tool wraps its body in `try/except Exception as e` and returns `{"error": f"...{e!s}"}` (or a list variant) so failures surface as tool results rather than MCP errors.

### Internal helpers

- `_safe_format_date(obj)` — converts any date/datetime to `"YYYY-MM-DD"` string; returns `None` on failure.
- `_safe_get_teacher_names(teachers, use_last_name)` — extracts names from teacher objects; returns `[]` on failure.
- `_TaskDict`, `_CourseDict`, `_DayDict` — TypedDicts used internally in `get_future_tasks` for mypy correctness.

### Tests

Tests never hit the network. The `autouse` `mock_session` fixture in `conftest.py` patches `_session`. Three test files:
- `test_helpers.py` — pure unit tests for `_safe_format_date` and `_safe_get_teacher_names`.
- `test_middleware.py` — async tests for `_BearerAuthMiddleware` (valid/invalid tokens, OPTIONS bypass, non-HTTP scopes).
- `test_tools.py` — error-handling tests (every tool must catch exceptions) and happy-path tests using `MagicMock` return values.

### `main.py`

Top-level `main.py` is a backward-compatibility shim; all real logic is in the `smartschool_mcp` package.
