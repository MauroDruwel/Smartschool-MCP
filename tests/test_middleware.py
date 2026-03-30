"""Tests for _BearerAuthMiddleware ASGI middleware."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import pytest

from smartschool_mcp.__main__ import _BearerAuthMiddleware

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_scope(
    scope_type: str = "http",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> dict[str, Any]:
    return {
        "type": scope_type,
        "headers": headers or [],
    }


def _bearer(token: str) -> list[tuple[bytes, bytes]]:
    return [(b"authorization", f"Bearer {token}".encode())]


async def _collect_responses(scope, receive=None) -> list[dict]:
    """Run _BearerAuthMiddleware with token 'secret-token' and collect all messages."""
    messages: list[dict] = []

    async def send(msg: dict) -> None:
        messages.append(msg)

    async def app(s, r, se) -> None:
        await se({"type": "http.response.start", "status": 200, "headers": []})
        await se({"type": "http.response.body", "body": b"ok"})

    mw = _BearerAuthMiddleware(app, "secret-token")
    await mw(scope, receive or AsyncMock(), send)
    return messages


# ── _BearerAuthMiddleware ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_valid_token_passes_through() -> None:
    scope = _make_scope(headers=_bearer("secret-token"))
    messages = await _collect_responses(scope)
    assert any(m.get("status") == 200 for m in messages)


@pytest.mark.asyncio
async def test_missing_auth_header_returns_401() -> None:
    scope = _make_scope(headers=[])
    messages = await _collect_responses(scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    assert start["status"] == 401


@pytest.mark.asyncio
async def test_wrong_token_returns_401() -> None:
    scope = _make_scope(headers=_bearer("wrong-token"))
    messages = await _collect_responses(scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    assert start["status"] == 401


@pytest.mark.asyncio
async def test_401_body_is_json() -> None:
    scope = _make_scope(headers=[])
    messages = await _collect_responses(scope)
    body_msg = next(m for m in messages if m.get("type") == "http.response.body")
    payload = json.loads(body_msg["body"])
    assert "error" in payload


@pytest.mark.asyncio
async def test_401_includes_www_authenticate_header() -> None:
    scope = _make_scope(headers=[])
    messages = await _collect_responses(scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    header_names = [k.lower() for k, _ in start["headers"]]
    assert b"www-authenticate" in header_names


@pytest.mark.asyncio
async def test_non_http_scope_passes_through_without_auth() -> None:
    """Lifespan / websocket scopes should bypass auth entirely."""
    scope = _make_scope(scope_type="lifespan", headers=[])

    received_by_inner: list[str] = []

    async def app(s, r, se) -> None:
        received_by_inner.append(s["type"])

    mw = _BearerAuthMiddleware(app, "secret-token")
    await mw(scope, AsyncMock(), AsyncMock())
    assert "lifespan" in received_by_inner


@pytest.mark.asyncio
async def test_bearer_prefix_only_without_token_returns_401() -> None:
    scope = _make_scope(headers=[(b"authorization", b"Bearer ")])
    messages = await _collect_responses(scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    assert start["status"] == 401


@pytest.mark.asyncio
async def test_wrong_scheme_returns_401() -> None:
    scope = _make_scope(headers=[(b"authorization", b"Basic c2VjcmV0LXRva2Vu")])
    messages = await _collect_responses(scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    assert start["status"] == 401
