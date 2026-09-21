# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp"]
# ///
from mcp.server.mcpserver import MCPServer

server = MCPServer("echo-demo")


@server.tool()
def echo(text: str) -> str:
    """Echo back the given text unchanged."""
    return text


if __name__ == "__main__":
    server.run(transport="stdio")
