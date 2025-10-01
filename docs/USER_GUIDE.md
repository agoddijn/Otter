# User Guide

**For complete API documentation:**
- Run `make docs` to view auto-generated documentation
- All services, models, and tools are automatically extracted from code
- Documentation updates when you update docstrings (no manual maintenance!)

## Quick Start

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def use_otter():
    server_params = StdioServerParameters(
        command="sh",
        args=["-c", "cd /path/to/otter && PYTHONPATH=src IDE_PROJECT_PATH=/path/to/project uv run python -m otter.mcp_server"],
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Navigate to definition
            result = await session.call_tool("find_definition", {
                "symbol": "MyClass",
                "file": "main.py",
                "line": 10
            })
```

## Available Tools

### Navigation (4 tools)
- `find_definition` - Jump to symbol definitions
- `find_references` - Find all usages
- `get_hover_info` - Type info and documentation
- `get_completions` - Context-aware autocomplete

### Intelligence (2 tools)
- `get_symbols` - Extract file symbols  
- `analyze_dependencies` - Module relationships

### AI-Powered Analysis (5 tools)
- `summarize_code` - Compress files into brief summaries (context compression)
- `summarize_changes` - Summarize git diffs
- `quick_review` - Fast code review for sanity checks
- `explain_error` - Interpret cryptic error messages
- `explain_symbol` - Semantic symbol explanation with LSP + LLM

### Files & Diagnostics (2 tools)
- `read_file` - Read with optional diagnostics
- `get_diagnostics` - LSP errors and warnings

### Debugging (5 tools)
- `start_debug_session` - Initialize DAP debugging
- `control_execution` - Step, continue, pause, stop
- `inspect_state` - Variables and stack frames
- `set_breakpoints` - Manage breakpoints
- `get_debug_session_info` - Session status

### Refactoring (2 tools)
- `rename_symbol` - Safe symbol renaming
- `extract_function` - Code extraction (coming soon)

## Language Support

Works with any language that has LSP/DAP support. Currently configured:
- **Python** (pyright, debugpy)
- **JavaScript/TypeScript** (tsserver, node-debug2)
- **Rust** (rust-analyzer, lldb-vscode)
- **Go** (gopls, delve)

## Integration Examples

### Claude Desktop

```json
{
  "mcpServers": {
    "my-project": {
      "command": "sh",
      "args": ["-c", "cd /path/to/otter && PYTHONPATH=src IDE_PROJECT_PATH=/path/to/project uv run python -m otter.mcp_server"]
    }
  }
}
```

### AI-Powered Analysis Examples

```python
# Summarize a large file (saves context!)
summary = await session.call_tool("summarize_code", {
    "file": "payment_processor.py",
    "detail_level": "brief"
})
# → "Payment processing service integrating Stripe and PayPal..."

# Summarize changes vs git
changes = await session.call_tool("summarize_changes", {
    "file": "auth.py",
    "git_ref": "main"  # Compare with main branch
})

# Quick code review
review = await session.call_tool("quick_review", {
    "file": "auth.py",
    "focus": ["security", "bugs"]
})

# Explain a symbol with context
explanation = await session.call_tool("explain_symbol", {
    "file": "server.py",
    "line": 45,
    "character": 10,
    "include_references": True
})
# → Uses LSP to find definition + references, LLM explains usage
```

### Debugging Example

```python
# Start debugging
await session.call_tool("start_debug_session", {
    "file": "app.py",
    "breakpoints": [42]
})

# Continue to breakpoint
await session.call_tool("control_execution", {"action": "continue"})

# Inspect variables
result = await session.call_tool("inspect_state", {
    "expression": "user.email"
})
```

## Troubleshooting

**LSP not responding?**
- Check LSP server is installed
- Verify file extension matches language
- Allow 1-2 seconds for LSP initialization

**Debugging not working?**
- Check DAP adapter is installed (e.g., `pip install debugpy`)
- Verify file path is correct
- Check `configs/lua/dap_config.lua`

**AI features not working?**
- Set up an LLM API key: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, etc.
- Check configuration: `make llm-info`
- Using Doppler? Run with: `make doppler-run CMD="..."`

**For complete API reference with parameters, returns, and examples:**  
Run `make docs` and visit http://127.0.0.1:8000
