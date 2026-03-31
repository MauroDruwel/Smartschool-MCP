# Smartschool MCP Server

<!-- mcp-name: io.github.MauroDruwel/smartschool-mcp -->

[![CI](https://github.com/MauroDruwel/Smartschool-MCP/actions/workflows/ci.yml/badge.svg)](https://github.com/MauroDruwel/Smartschool-MCP/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/MauroDruwel/Smartschool-MCP/branch/main/graph/badge.svg)](https://codecov.io/gh/MauroDruwel/Smartschool-MCP)
[![PyPI version](https://img.shields.io/pypi/v/smartschool-mcp)](https://pypi.org/project/smartschool-mcp/)
[![License: MIT](https://img.shields.io/github/license/MauroDruwel/Smartschool-MCP)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)

Connect Claude (and other MCP clients) to your Smartschool account — ask about grades, assignments, messages, and your schedule in plain language.

## Tools

| Tool | What it does |
|------|-------------|
| `get_courses` | List enrolled courses with teacher info |
| `get_results` | Grades with optional filtering, pagination, and statistics |
| `get_future_tasks` | Upcoming assignments organised by date |
| `get_messages` | Inbox/sent/trash with search, sender filter, and body retrieval |
| `get_schedule` | Day schedule by offset (0 = today, 1 = tomorrow, …) |
| `get_periods` | Academic terms for the current school year |
| `get_reports` | Available report cards |
| `get_planned_elements` | Planner items for the next N days |
| `get_student_support_links` | School support resources and links |
| `get_attachments` | List attachments for a specific message |
| `download_attachment` | Download a specific attachment by message and file ID |

## Quick start — Claude Desktop

```bash
uvx mcp install smartschool-mcp \
  -e SMARTSCHOOL_USERNAME="you" \
  -e SMARTSCHOOL_PASSWORD="secret" \
  -e SMARTSCHOOL_MAIN_URL="school.smartschool.be" \
  -e SMARTSCHOOL_MFA="YYYY-MM-DD"
```

Or add it manually to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "smartschool": {
      "command": "uvx",
      "args": ["smartschool-mcp"],
      "env": {
        "SMARTSCHOOL_USERNAME": "you",
        "SMARTSCHOOL_PASSWORD": "secret",
        "SMARTSCHOOL_MAIN_URL": "school.smartschool.be",
        "SMARTSCHOOL_MFA": "YYYY-MM-DD"
      }
    }
  }
}
```

Config file locations: `%APPDATA%\Claude\claude_desktop_config.json` (Windows) · `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) · `~/.config/Claude/claude_desktop_config.json` (Linux)

## Remote / claude.ai

The server supports **Streamable HTTP** transport for use as a remote integration on claude.ai.

### Single-user mode

One server instance, your credentials in environment variables:

```bash
export SMARTSCHOOL_USERNAME="..."
export SMARTSCHOOL_PASSWORD="..."
export SMARTSCHOOL_MAIN_URL="school.smartschool.be"
export SMARTSCHOOL_MFA="YYYY-MM-DD"
export MCP_API_KEY="a-long-random-secret"   # optional but recommended

smartschool-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

Add to claude.ai → Settings → Integrations:
- **URL:** `https://your-domain.example.com/mcp`
- **Authorization header:** `Bearer <your MCP_API_KEY>` (if set)

### Universal mode

One hosted server instance serves **any** Smartschool user — no per-user deployment needed.

```bash
smartschool-mcp --transport streamable-http --universal --host 0.0.0.0 --port 8000
```

Credentials are passed on every request:

| What | Where | Example |
|------|-------|---------|
| School URL | URL query param `school` | `?school=myschool.smartschool.be` |
| Date of birth (MFA) | URL query param `mfa` | `&mfa=2000-01-15` |
| Username | OAuth Client ID | your Smartschool username |
| Password | OAuth Client Secret | your Smartschool password |

In claude.ai → Settings → Integrations → Add custom connector:
- **URL:** `https://your-domain.example.com/mcp?school=myschool.smartschool.be&mfa=YYYY-MM-DD`
- **OAuth Client ID:** your Smartschool username
- **OAuth Client Secret:** your Smartschool password

> **MFA** is your date of birth in `YYYY-MM-DD` format. Omit the `mfa` param if your account does not require it.

### Making the server publicly accessible

Claude.ai requires HTTPS. Some options:

| Option | Command |
|--------|---------|
| Cloudflare Tunnel | `cloudflared tunnel --url http://localhost:8000` |
| ngrok | `ngrok http 8000` |
| VPS | nginx / Caddy with a Let's Encrypt cert |

## Environment variables

| Variable | CLI flag | Default | Description |
|----------|----------|---------|-------------|
| `MCP_TRANSPORT` | `--transport` | `stdio` | `stdio` or `streamable-http` |
| `MCP_HOST` | `--host` | `0.0.0.0` | Bind address (HTTP only) |
| `MCP_PORT` | `--port` | `8000` | Port (HTTP only) |
| `MCP_API_KEY` | — | — | Static Bearer token (single-user mode) |
| `MCP_UNIVERSAL` | `--universal` | off | Enable universal mode |
| `SESSION_TTL_SECONDS` | — | `3600` | How long to cache sessions (universal mode) |
| `SMARTSCHOOL_USERNAME` | — | — | Your Smartschool username |
| `SMARTSCHOOL_PASSWORD` | — | — | Your Smartschool password |
| `SMARTSCHOOL_MAIN_URL` | — | — | School hostname, e.g. `school.smartschool.be` |
| `SMARTSCHOOL_MFA` | — | — | Date of birth `YYYY-MM-DD` (if required) |

## Contributing

PRs are welcome. Run `uv sync --extra dev` to install dev dependencies, then `uv run pytest` / `uv run ruff check .` / `uv run mypy smartschool_mcp/` before submitting.

## Disclaimer

Unofficial tool, not affiliated with Smartschool. Use in accordance with your school's terms of service.
