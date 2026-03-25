# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/MauroDruwel/Smartschool-MCP/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/MauroDruwel/Smartschool-MCP/compare/v0.1.4...v0.2.0
[0.1.4]: https://github.com/MauroDruwel/Smartschool-MCP/releases/tag/v0.1.4
