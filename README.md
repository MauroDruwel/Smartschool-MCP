# Smartschool MCP Server

<!-- mcp-name: io.github.MauroDruwel/smartschool-mcp -->

A Model Context Protocol (MCP) server that enables AI assistants to interact with the Smartschool platform, providing access to courses, grades, assignments, and messages.

## Overview

This MCP server allows AI assistants like Claude to seamlessly access and retrieve information from Smartschool, a widely-used educational management platform in Belgium and the Netherlands. With this MCP server, students can ask their AI assistant about their grades, upcoming assignments, course information, and messages without leaving their conversation.

## Features

The Smartschool MCP server provides the following tools:

### 📚 `get_courses`
Retrieve all available courses with teacher information.
- Lists all enrolled courses
- Includes teacher names for each course

### 📊 `get_results`
Fetch student grades and results with detailed information.
- Supports pagination with `limit` and `offset` parameters
- Filter by course name using `course_filter`
- Optional detailed statistics (average, median) with `include_details`
- Includes score descriptions, dates, and feedback

### 📝 `get_future_tasks`
Get upcoming assignments and tasks organized by date.
- Shows all future assignments
- Organized by date and course
- Includes task descriptions and labels

### 📧 `get_messages`
Access mailbox messages with powerful filtering options.
- Choose mailbox type: `INBOX`, `SENT`, `DRAFT`, etc.
- Search messages by content with `search_query`
- Filter by sender with `sender_filter`
- Optional full message body with `include_body`
- Pagination support

## Installation

[![PyPI version](https://badge.fury.io/py/smartschool-mcp.svg)](https://pypi.org/project/smartschool-mcp/)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)

### Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) package manager (recommended) or pip
- A Smartschool account with valid credentials

### Quick Install with MCP CLI (Recommended)

The easiest way to install and configure the server is using the MCP CLI:

```bash
# Install from PyPI and configure automatically
uvx mcp install smartschool-mcp \
  -e SMARTSCHOOL_USERNAME="your_username" \
  -e SMARTSCHOOL_PASSWORD="your_password" \
  -e SMARTSCHOOL_MAIN_URL="your-school.smartschool.be" \
  -e SMARTSCHOOL_MFA="YYYY-MM-DD"
```

This command will:
- Install the package from PyPI
- Add it to your Claude Desktop configuration
- Set up the environment variables automatically

### Manual Installation from PyPI

If you prefer to install manually and configure later:

```bash
# Using pip
pip install smartschool-mcp

# Using uv (recommended)
uv pip install smartschool-mcp
```

After manual installation, you'll need to configure Claude Desktop manually (see configuration section below).

### Installation from Source

If you want to contribute or use the latest development version:

```bash
git clone https://github.com/MauroDruwel/Smartschool-MCP.git
cd Smartschool-MCP
uv sync
```

### Configuration Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `SMARTSCHOOL_USERNAME` | Your Smartschool username | `john.doe@student.school.be` |
| `SMARTSCHOOL_PASSWORD` | Your Smartschool password | `yourpassword123` |
| `SMARTSCHOOL_MAIN_URL` | Your school's Smartschool URL (without https://) | `school.smartschool.be` |
| `SMARTSCHOOL_MFA` | Your date of birth (YYYY-MM-DD format) | `2008-01-15` |

## Usage Examples

Once installed and configured with Claude Desktop or another MCP client, you can ask questions like:

- "What are my recent grades?"
- "Show me my upcoming assignments"
- "What courses am I enrolled in?"
- "Do I have any new messages?"
- "What's my average grade in Math?"
- "Show me messages from my teacher about the project"

### Tool Usage Examples

**Get courses:**
```python
get_courses()
```

**Get recent grades:**
```python
get_results(limit=10, course_filter="Math", include_details=True)
```

**Get upcoming assignments:**
```python
get_future_tasks()
```

**Search messages:**
```python
get_messages(
    limit=20,
    search_query="homework",
    sender_filter="teacher",
    include_body=True
)
```

## Claude Desktop Configuration

Add this configuration to your `claude_desktop_config.json`:

### Option 1: Using uvx (Recommended)

```json
{
  "mcpServers": {
    "smartschool": {
      "command": "uvx",
      "args": [
        "smartschool-mcp"
      ],
      "env": {
        "SMARTSCHOOL_USERNAME": "your_username",
        "SMARTSCHOOL_PASSWORD": "your_password",
        "SMARTSCHOOL_MAIN_URL": "your-school.smartschool.be",
        "SMARTSCHOOL_MFA": "YYYY-MM-DD"
      }
    }
  }
}
```

### Option 2: Using Python module

```json
{
  "mcpServers": {
    "smartschool": {
      "command": "python",
      "args": [
        "-m",
        "smartschool_mcp"
      ],
      "env": {
        "SMARTSCHOOL_USERNAME": "your_username",
        "SMARTSCHOOL_PASSWORD": "your_password",
        "SMARTSCHOOL_MAIN_URL": "your-school.smartschool.be",
        "SMARTSCHOOL_MFA": "YYYY-MM-DD"
      }
    }
  }
}
```

### Option 3: From source (for development)

```json
{
  "mcpServers": {
    "smartschool": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "C:\\Users\\YourUsername\\path\\to\\Smartschool-MCP",
        "main.py"
      ],
      "env": {
        "SMARTSCHOOL_USERNAME": "your_username",
        "SMARTSCHOOL_PASSWORD": "your_password",
        "SMARTSCHOOL_MAIN_URL": "your-school.smartschool.be",
        "SMARTSCHOOL_MFA": "YYYY-MM-DD"
      }
    }
  }
}
```

> **Note:** Replace `C:\Users\YourUsername\path\to\Smartschool-MCP` with the actual absolute path where you cloned the repository.

**Config file locations:**
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

## Security Considerations

⚠️ **Important Security Notes:**

- Your Smartschool credentials are stored in environment variables or configuration files
- Never commit credentials to version control
- Use environment variables or secure secret management in production
- Consider using application-specific passwords if supported
- The server only has read-only access to your Smartschool data
- All communication happens locally between your AI assistant and the Smartschool API

## Troubleshooting

### Authentication Issues
- Verify your credentials are correct
- Ensure your MFA date (date of birth) is in the correct format: `YYYY-MM-DD`
- Check that your school's URL is correct (without `https://`)

### Connection Issues
- Verify your internet connection
- Check if Smartschool is accessible from your browser
- Ensure no firewall is blocking the connection

### Installation Issues
- Make sure Python 3.13+ is installed
- Verify uv is properly installed and in your PATH
- Try running `uv sync` to reinstall dependencies

## Development

### Project Structure
```
Smartschool-MCP/
├── main.py              # Main MCP server implementation
├── pyproject.toml       # Project dependencies and metadata
├── README.md            # This file
└── uv.lock              # Locked dependencies
```

### Dependencies
- `mcp[cli]>=1.9.4` - Model Context Protocol SDK
- `smartschool` - Smartschool API wrapper (custom fork)

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is open source and available under the MIT License.

## Credits

- Built using the [Model Context Protocol](https://modelcontextprotocol.io/)
- Uses the Smartschool Python Library (https://github.com/svaningelgem/smartschool)
- Created by [Mauro Druwel](https://github.com/MauroDruwel)

## Disclaimer

This is an unofficial tool and is not affiliated with, endorsed by, or connected to Smartschool or its parent company. Use at your own risk. Always ensure you comply with your school's terms of service and acceptable use policies.

## Support

For issues, questions, or suggestions, please [open an issue](https://github.com/MauroDruwel/Smartschool-MCP/issues) on GitHub.