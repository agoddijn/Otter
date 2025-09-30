"""Main entry point for the CLI IDE MCP server."""

from cli_ide.mcp_server import main, mcp, set_project_path

# Expose mcp object for MCP inspector
__all__ = ["mcp", "main", "set_project_path"]

if __name__ == "__main__":
    main()
