# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | ✅ Current |
| < 0.2   | ❌ End of life |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report security issues by emailing **mauro.druwel@gmail.com** with:

- A description of the vulnerability and its potential impact
- Step-by-step reproduction instructions
- Any proof-of-concept code (if applicable)
- Your GitHub username (so we can credit you if desired)

You should receive an acknowledgement within **48 hours** and a full response
within **7 days**.

## Security Considerations

### Credentials

- Smartschool credentials are read from environment variables — they are never
  logged, stored, or transmitted beyond the Smartschool API.
- Never commit `.env` files or credentials to version control.
- Use a dedicated Smartschool account with minimal permissions when possible.

### HTTP transport (`--transport streamable-http`)

- Always deploy behind HTTPS (TLS-terminating reverse proxy, Cloudflare Tunnel,
  etc.) before exposing to the internet.
- Set `MCP_API_KEY` to a long random secret and add it as a Bearer token in
  your MCP client configuration.
- The `allow_origins=["*"]` CORS setting is intentional for MCP client
  compatibility; narrow it to specific origins in production if possible.
- Bind to `127.0.0.1` instead of `0.0.0.0` when running locally:
  ```bash
  smartschool-mcp --transport streamable-http --host 127.0.0.1
  ```

### Data access

This server provides **read-only** access to Smartschool data. No write
operations (sending messages, submitting assignments, etc.) are implemented.
