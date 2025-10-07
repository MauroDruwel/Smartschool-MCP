# Smartschool MCP Server

<!-- mcp-name: io.github.maurodruwel/smartschool-mcp -->

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

> **⚠️ Note:** This package is not available on PyPI. You must clone the repository to use it.

### Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- Git
- A Smartschool account with valid credentials

### Installation Steps

**This repository must be cloned from GitHub before installation:**

1. **Clone the repository:**
```bash
git clone https://github.com/MauroDruwel/Smartschool-MCP.git
cd Smartschool-MCP
```

2. **Install using MCP CLI:**
```bash
uv run mcp install main.py \
  --name "Smartschool MCP" \
  -v SMARTSCHOOL_USERNAME="your_username" \
  -v SMARTSCHOOL_PASSWORD="your_password" \
  -v SMARTSCHOOL_MAIN_URL="your-school.smartschool.be" \
  -v SMARTSCHOOL_MFA="YYYY-MM-DD"
```

This will install the server and configure it for use with Claude Desktop or other MCP clients.

### Alternative: Manual Setup

If you prefer not to use the MCP CLI, you can set up the server manually:

1. After cloning, install dependencies:
```bash
uv sync
```

2. Configure environment variables (see below)

3. Add the server to your MCP client configuration manually (see Claude Desktop Configuration section)

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

If you installed using the MCP CLI, the configuration is already set up automatically. If you're setting up manually, add this to your `claude_desktop_config.json`:

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

> **Important:** Replace `C:\Users\YourUsername\path\to\Smartschool-MCP` with the actual absolute path where you cloned the repository.

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