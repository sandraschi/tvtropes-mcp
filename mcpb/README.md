# tvtropes-mcp (MCPB Bundle)

TVTropes local mirror + MCP server — background scraper + query interface

## Usage

Add to \claude_desktop_config.json\:
\\\json
{
  "mcpServers": {
    "tvtropes-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "\D:\Dev\repos", "python", "-m", "tvtropes_mcp"],
      "env": { "PYTHONPATH": "\D:\Dev\repos/src" }
    }
  }
}
\\\

## Tools

- **tvtropes-mcp**: TVTropes local mirror + MCP server — background scraper + query interface

## Requirements

- Python 3.12+
- uv
