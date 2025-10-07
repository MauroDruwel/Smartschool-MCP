"""
Main entry point for the Smartschool MCP server.
Can be run as: python -m smartschool_mcp or smartschool-mcp
"""

from smartschool_mcp.server import mcp


def main():
    """Main entry point for the server."""
    mcp.run()


if __name__ == "__main__":
    main()
