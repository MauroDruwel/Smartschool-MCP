"""Tests for _UniversalCredentialMiddleware."""

from __future__ import annotations

import base64
import json
from unittest.mock import AsyncMock

import pytest

from smartschool_mcp.__main__ import _UniversalCredentialMiddleware
from smartschool_mcp.server import _request_creds


def _make_scope(
    method: str = "POST",
    query_string: bytes = b"",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> dict:
    return {
        "type": "http",
        "method": method,
        "query_string": query_string,
        "headers": headers or [],
    }


def _basic(username: str, password: str) -> list[tuple[bytes, bytes]]:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return [(b"authorization", f"Basic {token}".encode())]


def _qs(school: str, mfa: str = "") -> bytes:
    q = f"school={school}"
    if mfa:
        q += f"&mfa={mfa}"
    return q.encode()


async def _run(scope) -> list[dict]:
    """Run the middleware with a no-op inner app; return all ASGI messages."""
    messages: list[dict] = []

    async def send(msg: dict) -> None:
        messages.append(msg)

    async def app(s, r, se) -> None:
        await se({"type": "http.response.start", "status": 200, "headers": []})
        await se({"type": "http.response.body", "body": b"ok"})

    mw = _UniversalCredentialMiddleware(app)
    await mw(scope, AsyncMock(), send)
    return messages


# ── Rejection cases ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_missing_school_returns_401() -> None:
    scope = _make_scope(headers=_basic("user", "pass"))
    messages = await _run(scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    assert start["status"] == 401


@pytest.mark.asyncio
async def test_missing_credentials_returns_401() -> None:
    scope = _make_scope(query_string=_qs("school.smartschool.be"))
    messages = await _run(scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    assert start["status"] == 401


@pytest.mark.asyncio
async def test_malformed_basic_auth_returns_401() -> None:
    # Base64 of something without a colon
    bad = base64.b64encode(b"nocolon").decode()
    scope = _make_scope(
        query_string=_qs("school.smartschool.be"),
        headers=[(b"authorization", f"Basic {bad}".encode())],
    )
    messages = await _run(scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    assert start["status"] == 401


@pytest.mark.asyncio
async def test_401_body_contains_error_key() -> None:
    scope = _make_scope()
    messages = await _run(scope)
    body_msg = next(m for m in messages if m.get("type") == "http.response.body")
    payload = json.loads(body_msg["body"])
    assert "error" in payload


# ── Pass-through cases ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_valid_credentials_returns_200() -> None:
    scope = _make_scope(
        query_string=_qs("school.smartschool.be", "2000-01-15"),
        headers=_basic("user", "pass"),
    )
    messages = await _run(scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    assert start["status"] == 200


@pytest.mark.asyncio
async def test_mfa_is_optional() -> None:
    scope = _make_scope(
        query_string=_qs("school.smartschool.be"),  # no mfa
        headers=_basic("user", "pass"),
    )
    messages = await _run(scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    assert start["status"] == 200


@pytest.mark.asyncio
async def test_options_bypasses_auth() -> None:
    scope = _make_scope(method="OPTIONS")  # no school, no credentials
    messages = await _run(scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    assert start["status"] == 200


@pytest.mark.asyncio
async def test_non_http_scope_bypasses_auth() -> None:
    scope = {"type": "lifespan"}
    received: list[str] = []

    async def app(s, r, se) -> None:
        received.append(s["type"])

    mw = _UniversalCredentialMiddleware(app)
    await mw(scope, AsyncMock(), AsyncMock())
    assert "lifespan" in received


# ── Contextvar is set correctly ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_request_creds_set_during_request() -> None:
    scope = _make_scope(
        query_string=_qs("myschool.smartschool.be", "1999-12-31"),
        headers=_basic("alice", "s3cr3t"),
    )
    captured: list = []

    async def app(s, r, se) -> None:
        captured.append(_request_creds.get())
        await se({"type": "http.response.start", "status": 200, "headers": []})
        await se({"type": "http.response.body", "body": b""})

    from smartschool import AppCredentials

    mw = _UniversalCredentialMiddleware(app)
    await mw(scope, AsyncMock(), AsyncMock())

    assert len(captured) == 1
    creds = captured[0]
    assert isinstance(creds, AppCredentials)
    assert creds.username == "alice"
    assert creds.password == "s3cr3t"
    assert creds.main_url == "myschool.smartschool.be"
    assert creds.mfa == "1999-12-31"


@pytest.mark.asyncio
async def test_request_creds_cleared_after_request() -> None:
    scope = _make_scope(
        query_string=_qs("school.smartschool.be"),
        headers=_basic("user", "pass"),
    )
    mw = _UniversalCredentialMiddleware(AsyncMock())
    await mw(scope, AsyncMock(), AsyncMock())
    assert _request_creds.get() is None
