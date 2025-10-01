# Quick Start

## Basic Usage

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def use_otter():
    server_params = StdioServerParameters(
        command="sh",
        args=[
            "-c",
            "cd /path/to/otter && PYTHONPATH=src IDE_PROJECT_PATH=/path/to/project uv run python -m otter.mcp_server"
        ],
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Find definition
            result = await session.call_tool("find_definition", {
                "symbol": "MyClass",
                "file": "main.py",
                "line": 10
            })
```

## Available Tools

### Navigation
- `find_definition` - Jump to symbol definitions
- `find_references` - Find all usages
- `get_hover_info` - Type info and docs
- `get_completions` - Context-aware autocomplete

### Intelligence
- `get_symbols` - Extract file symbols
- `get_diagnostics` - LSP errors/warnings
- `analyze_dependencies` - Import/usage analysis

### Debugging
- `start_debug_session` - Start DAP debugging
- `control_execution` - Step, continue, pause
- `inspect_state` - View variables and stack
- `set_breakpoints` - Dynamic breakpoints
- `get_debug_session_info` - Session status

### Files
- `read_file` - Read with optional diagnostics

See [API Reference](../api/overview.md) for detailed documentation.

