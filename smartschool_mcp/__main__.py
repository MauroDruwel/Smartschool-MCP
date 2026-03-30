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
  MCP_API_KEY     optional Bearer token required on every HTTP request
"""

from __future__ import annotations

import argparse
import hmac
import os
from typing import Any

from smartschool_mcp.server import mcp


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
        default=int(os.environ.get("MCP_PORT", "8000")),
        help="Bind port for HTTP transport (default: 8000)",
    )
    args = parser.parse_args()

    if args.transport == "streamable-http":
        _run_http(args.host, args.port)
    else:
        mcp.run()


def _run_http(host: str, port: int) -> None:
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

    # CORS is required so browser-based clients (including claude.ai) can read
    # the Mcp-Session-Id header returned during initialisation.
    app = CORSMiddleware(
        app,
        allow_origins=["*"],  # tighten to specific origins in production
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id"],
    )

    # Optional Bearer-token guard.  Set MCP_API_KEY to enable.
    api_key = os.environ.get("MCP_API_KEY")
    if api_key:
        app = _BearerAuthMiddleware(app, api_key)
        print(
            "[smartschool-mcp] Bearer auth enabled - "
            "set Authorization: Bearer <MCP_API_KEY>"
        )

    print(f"[smartschool-mcp] Listening on http://{host}:{port}/mcp")
    uvicorn.run(app, host=host, port=port)


class _BearerAuthMiddleware:
    """Minimal ASGI middleware that enforces a static Bearer token."""

    def __init__(self, app, token: str) -> None:
        self.app = app
        self.token = token.encode()

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "http":
            # Let CORS preflight through so the browser can negotiate headers.
            if scope.get("method", "").upper() == "OPTIONS":
                await self.app(scope, receive, send)
                return
            headers = {k.lower(): v for k, v in scope.get("headers", [])}
            auth_bytes = headers.get(b"authorization", b"")
            if not (
                auth_bytes.startswith(b"Bearer ")
                and hmac.compare_digest(auth_bytes[7:], self.token)
            ):
                await self._reject(send)
                return
        await self.app(scope, receive, send)

    @staticmethod
    async def _reject(send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"www-authenticate", b'Bearer realm="Smartschool MCP"'],
                ],
            }
        )
        await send({"type": "http.response.body", "body": b'{"error":"Unauthorized"}'})


if __name__ == "__main__":
    main()
