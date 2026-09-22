# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-09-22

### Added

- `get_attachments(message_id)` — list all attachments for a message (name, mime type, size, file ID)
- `download_attachment(message_id, file_id, save_path?)` — download an attachment; defaults to `~/Downloads/smartschool/`, accepts optional `save_path`
- `has_attachments` and `attachment_count` fields in every `get_messages` result
- Mauro Quality Gate (MQG) certification: `.editorconfig`, strict audit workflow check in CI, and repo topic refinement

### Fixed

- `download_attachment` calls `session.get()` directly instead of the upstream library's `Attachment.download()`, which incorrectly base64-decodes a raw binary response (upstream bug)
- Expired sessions no longer make XML-backed tools (`get_messages`, `get_attachments`, `get_future_tasks`) report empty results instead of an error. The environment-credential session is now TTL-cached like the OAuth one, and every session is liveness-probed once with a `GET /` so a dead cookie triggers a real re-login

### Changed

- Upgraded `mcp` SDK to 2.x (`>=2.1.1,<3`), migrating `FastMCP` to `MCPServer`, updating HTTP transport configurations (`stateless_http`, `json_response`, `transport_security`) to `streamable_http_app()`, and typing `SmartschoolOAuthProvider` with `OAuthAuthorizationServerProvider`. `FastMCP` alias is preserved for backwards compatibility
- Updated dependencies: `smartschool>=0.10.0`, `cachetools>=7.1.8`, `types-cachetools>=7.0.0.20260713`, dev tools (`pytest>=9.1.1`, `pytest-cov>=7.1.0`), and GitHub actions (`actions/checkout@v7`, `peter-evans/create-pull-request@v8`)

## [0.2.0] - 2026-03-25

### Added

- **Remote MCP support** via Streamable HTTP transport (`--transport streamable-http`)
- `--host`, `--port` CLI flags with `MCP_HOST`, `MCP_PORT`, `MCP_TRANSPORT` env var counterparts
- Optional Bearer-token authentication via `MCP_API_KEY` (`_BearerAuthMiddleware`)
- CORS middleware — required for browser-based clients such as claude.ai
- `get_schedule(date_offset)` — daily lesson schedule via `SmartschoolLessons`
- `get_periods()` — academic terms/periods via `Periods`
- `get_reports()` — report cards via `Reports`
- `get_planned_elements(days_ahead)` — planner items via `PlannedElements`
- `get_student_support_links()` — school support resources via `StudentSupportLinks`
- `achieved_points`, `total_points`, `percentage` fields in `get_results`
- `teacher` (from `gradebook_owner`, no extra API call) and `period` in `get_results`
- `warning` field in `get_future_tasks` tasks
- Lazy `_session()` singleton — session is created on first tool invocation, not at import time
- Professional OSS infrastructure: CI workflow, issue/PR templates, CodeRabbitAI, pre-commit, tests

### Changed

- Updated `smartschool` dependency from personal fork (v0.5.0) to official library (`svaningelgem/smartschool` v0.8.0+)
- Relaxed Python requirement from `>=3.13` to `>=3.10`
- Modernized all type hints: replaced `typing.List/Dict/Optional` with built-in generics (`list`, `dict`, `str | None`)
- `get_results`: teacher now read from `result.gradebook_owner` (always available); details fetch only used for central tendencies
- `get_messages`: sender filter applied directly from headers (no full message fetch needed); body fetched lazily
- `get_future_tasks`: fixed `course.course_title` (was incorrectly `course.name`)
- Fixed `total_tasks` calculation (was counting dict keys, not tasks)
- Fixed `result.availability_date` and `result.does_count` attribute names (camelCase → snake_case)
- Fixed `teacher.name.starting_with_last_name` / `starting_with_first_name` attribute names
- Fixed `header.unread` (was `header.read`)
- Replaced removed `ResultDetail` class with lazy-loaded `result.details` property
- Updated `publish.yml` to use `uv build` instead of legacy `python -m build` + pip

### Removed

- `ResultDetail` import (class removed in official smartschool library)

## [0.1.4] - 2026-03-01

### Added

- Initial release with `get_courses`, `get_results`, `get_future_tasks`, `get_messages` tools
- Claude Desktop integration via stdio transport
- PyPI distribution and MCP Registry listing

[Unreleased]: https://github.com/MauroDruwel/Smartschool-MCP/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/MauroDruwel/Smartschool-MCP/compare/v0.1.4...v0.3.0
[0.2.0]: https://github.com/MauroDruwel/Smartschool-MCP/compare/v0.1.4...v0.2.0
[0.1.4]: https://github.com/MauroDruwel/Smartschool-MCP/releases/tag/v0.1.4
