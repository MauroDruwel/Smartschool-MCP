"""
Main entry point for the Smartschool MCP server.
Can be run as: python -m smartschool_mcp or smartschool-mcp

Supports two transports:
  stdio             (default) - for Claude Desktop / local MCP clients
  streamable-http             - for remote MCP clients such as claude.ai

Environment variables (all overridable by CLI flags):
  MCP_TRANSPORT   stdio | streamable-http  (default: stdio)
  MCP_HOST        bind address for HTTP    (default: 0.0.0.0)
  MCP_PORT        port for HTTP            (default: 8000)
  MCP_API_KEY     optional Bearer token (single-user mode only)
  MCP_UNIVERSAL   set to 1 to enable universal mode

Universal mode (--universal / MCP_UNIVERSAL=1):
  One server instance serves any Smartschool user.  Pass credentials on
  every request instead of baking them into the server environment:

    URL query params:   ?school=school.smartschool.be&mfa=2000-01-15
    Authorization header: Basic base64(username:password)

  In claude.ai → Settings → Integrations, configure the integration URL
  with the school and mfa query params, and supply your Smartschool
  username as the client_id and password as the client_secret (these are
  forwarded as HTTP Basic auth).  MFA is your date of birth (YYYY-MM-DD);
  omit it if your account does not require verification.
"""

from __future__ import annotations

import argparse
import base64
import hmac
import json
import logging
import os
from typing import Any
from urllib.parse import parse_qs

from smartschool import AppCredentials

from smartschool_mcp.server import _request_creds, mcp

_logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for the server."""
    parser = argparse.ArgumentParser(
        description="Smartschool MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  smartschool-mcp                          # stdio (Claude Desktop)\n"
            "  smartschool-mcp --transport streamable-http          # HTTP on :8000\n"
            "  smartschool-mcp --transport streamable-http --port 9000\n"
            "  MCP_TRANSPORT=streamable-http MCP_API_KEY=secret smartschool-mcp\n"
        ),
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_HOST", "0.0.0.0"),
        help="Bind host for HTTP transport (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=os.environ.get("MCP_PORT", "8000"),
        help="Bind port for HTTP transport (default: 8000)",
    )
    parser.add_argument(
        "--universal",
        action="store_true",
        default=os.environ.get("MCP_UNIVERSAL", "").lower() in ("1", "true", "yes"),
        help=(
            "Universal mode: accept per-request credentials via "
            "?school=&mfa= query params and Authorization: Basic header"
        ),
    )
    args = parser.parse_args()

    if args.transport == "streamable-http":
        _run_http(args.host, args.port, universal=args.universal)
    else:
        mcp.run()


def _run_http(host: str, port: int, universal: bool = False) -> None:
    """Run the MCP server over Streamable HTTP (for remote clients / claude.ai).

    The MCP endpoint will be available at:
        http://<host>:<port>/mcp

    When deploying publicly, put this behind a TLS-terminating reverse proxy
    (nginx, Caddy, Traefik, Cloudflare Tunnel, …) so the URL becomes HTTPS.
    Add it to claude.ai under Settings → Integrations → Add custom integration.
    """
    import uvicorn
    from starlette.middleware.cors import CORSMiddleware

    # Stateless + JSON responses are recommended for production HTTP deployments.
    mcp.settings.stateless_http = True
    mcp.settings.json_response = True

    # The ASGI app exposes a single endpoint at /mcp (POST + GET).
    app: Any = mcp.streamable_http_app()

    if universal:
        # Universal mode: credentials come from each request, not from env vars.
        app = _UniversalCredentialMiddleware(app)
        print("[smartschool-mcp] Universal mode enabled")
        print(
            "[smartschool-mcp] Pass ?school=<url>&mfa=<dob> in the URL "
            "and credentials via Authorization: Basic"
        )
    else:
        # Optional Bearer-token guard.  Set MCP_API_KEY to enable.
        api_key = os.environ.get("MCP_API_KEY")
        if api_key:
            app = _BearerAuthMiddleware(app, api_key)
            print(
                "[smartschool-mcp] Bearer auth enabled - "
                "set Authorization: Bearer <MCP_API_KEY>"
            )

    # CORS is required so browser-based clients (including claude.ai) can read
    # the Mcp-Session-Id header returned during initialisation.
    # Wrap outermost so CORS preflight OPTIONS is handled before auth.
    app = CORSMiddleware(
        app,
        allow_origins=["*"],  # tighten to specific origins in production
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id"],
    )

    print(f"[smartschool-mcp] Listening on http://{host}:{port}/mcp")
    uvicorn.run(app, host=host, port=port)


def _parse_auth_header(scope: dict) -> bytes:
    """Extract the raw Authorization header bytes from an ASGI scope."""
    headers: dict[bytes, bytes] = {k.lower(): v for k, v in scope.get("headers", [])}
    return headers.get(b"authorization", b"")


async def _send_401(send, www_authenticate: bytes, message: str) -> None:
    """Send a JSON 401 response with the given WWW-Authenticate challenge."""
    body = json.dumps({"error": message}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 401,
            "headers": [
                [b"content-type", b"application/json"],
                [b"www-authenticate", www_authenticate],
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class _UniversalCredentialMiddleware:
    """ASGI middleware for universal (multi-user) mode.

    Extracts Smartschool credentials from each HTTP request so that a single
    hosted server instance can serve any Smartschool user:

    - ``school`` and ``mfa`` are read from URL query parameters.
    - ``username`` and ``password`` are read from an ``Authorization: Basic``
      header (standard HTTP Basic auth, base64-encoded ``username:password``).

    In claude.ai, configure the integration URL with the school and mfa query
    params, and supply your Smartschool username as the client_id and password
    as the client_secret (forwarded as HTTP Basic auth).
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if scope.get("method", "").upper() == "OPTIONS":
            await self.app(scope, receive, send)
            return

        qs = parse_qs(scope.get("query_string", b"").decode())
        school = (qs.get("school") or [None])[0]
        mfa = (qs.get("mfa") or [""])[0]

        auth_bytes = _parse_auth_header(scope)
        username = password = None
        if auth_bytes[:6].lower() == b"basic ":
            try:
                decoded = base64.b64decode(auth_bytes[6:]).decode()
                if ":" in decoded:
                    username, password = decoded.split(":", 1)
            except Exception as e:
                _logger.debug("Failed to decode Basic auth header: %s", e)

        if not school or not username or not password:
            await _send_401(
                send,
                b'Basic realm="Smartschool MCP"',
                "Provide ?school=<url> in the URL and credentials "
                "via Authorization: Basic <base64(username:password)>",
            )
            return

        token = _request_creds.set(
            AppCredentials(
                username=username,
                password=password,
                main_url=school,
                mfa=mfa,
            )
        )
        try:
            await self.app(scope, receive, send)
        finally:
            _request_creds.reset(token)


class _BearerAuthMiddleware:
    """Minimal ASGI middleware that enforces a static Bearer token."""

    def __init__(self, app: Any, token: str) -> None:
        self.app = app
        self.token = token.encode()

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if scope.get("method", "").upper() == "OPTIONS":
            await self.app(scope, receive, send)
            return

        auth_bytes = _parse_auth_header(scope)
        if not (
            auth_bytes[:7].lower() == b"bearer "
            and hmac.compare_digest(auth_bytes[7:], self.token)
        ):
            await _send_401(send, b'Bearer realm="Smartschool MCP"', "Unauthorized")
            return

        await self.app(scope, receive, send)


if __name__ == "__main__":
    main()
