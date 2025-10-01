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
- `get_symbols` - Extract file symbols with rich metadata
- `analyze_dependencies` - Module relationships

### AI-Powered Analysis (5 tools)
- `summarize_code` - Compress files into brief summaries (context compression)
- `summarize_changes` - Summarize git diffs
- `quick_review` - Fast code review for sanity checks
- `explain_error` - Interpret cryptic error messages
- `explain_symbol` - Semantic symbol explanation with LSP + LLM

### Files & Diagnostics (3 tools)
- `read_file` - Read with optional diagnostics
- `get_diagnostics` - LSP errors and warnings
- `get_project_structure` - Directory tree with metadata

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

### Navigation Examples

```python
# Find all references to a symbol (enhanced!)
result = await session.call_tool("find_references", {
    "symbol": "CliIdeServer",
    "file": "src/server.py",
    "line": 37
})

# Returns structured result:
# {
#   "references": [...],
#   "total_count": 27,
#   "grouped_by_file": [
#     {
#       "file": "src/server.py",
#       "count": 4,
#       "references": [
#         {
#           "file": "src/server.py",
#           "line": 37,
#           "column": 6,
#           "context": "Line 37: class CliIdeServer:",
#           "is_definition": true,
#           "reference_type": "usage"
#         },
#         ...
#       ]
#     },
#     ...
#   ]
# }

# Exclude the definition, only show usages
result = await session.call_tool("find_references", {
    "symbol": "CliIdeServer",
    "file": "src/server.py",
    "line": 37,
    "exclude_definition": True
})

# Get code completions (enhanced with smart filtering!)
result = await session.call_tool("get_completions", {
    "file": "src/server.py",
    "line": 83,
    "column": 9  # After typing "self."
})

# Returns structured result with top 50 most relevant:
# {
#   "completions": [
#     {
#       "text": "nvim_client",
#       "kind": "property",
#       "detail": "NeovimClient",
#       "documentation": "The Neovim client instance for LSP communication"
#     },
#     {
#       "text": "find_definition",
#       "kind": "method",
#       "detail": "async def find_definition(symbol: str, ...) -> Definition",
#       "documentation": "Find the definition of a symbol using LSP..."
#     },
#     ...
#   ],
#   "total_count": 45,
#   "returned_count": 45,
#   "truncated": false
# }

# Get more results if needed
result = await session.call_tool("get_completions", {
    "file": "src/server.py",
    "line": 83,
    "column": 9,
    "max_results": 100  # Default is 50
})
```

### File Operations Examples

```python
# Read entire file with metadata
result = await session.call_tool("read_file", {
    "path": "src/server.py"
})
# Returns:
# {
#   "content": "1|from pathlib import Path\n2|...",
#   "total_lines": 150,  # NEW: Know the file length!
#   "language": "python",  # NEW: Auto-detected language
#   "expanded_imports": null,
#   "diagnostics": null
# }

# Read specific lines
result = await session.call_tool("read_file", {
    "path": "src/server.py",
    "line_range": [45, 60]  # Lines 45-60 (1-indexed, inclusive)
})
# Returns lines 45-60 with line numbers

# Read with context around a specific section
result = await session.call_tool("read_file", {
    "path": "src/server.py",
    "line_range": [50, 50],  # Just line 50
    "context_lines": 5  # Plus 5 lines before and after
})
# Returns lines 45-55

# Read with diagnostics (linter errors, type errors, etc.)
result = await session.call_tool("read_file", {
    "path": "src/buggy.py",
    "include_diagnostics": True
})
# Returns:
# {
#   "content": "1|def broken(:\n2|    pass",
#   "total_lines": 2,
#   "language": "python",
#   "diagnostics": [
#     {
#       "severity": "error",
#       "message": "expected parameter name",
#       "line": 1,
#       "column": 12,
#       "source": "pyright"
#     }
#   ]
# }

# Read with import detection
result = await session.call_tool("read_file", {
    "path": "src/models.py",
    "include_imports": True
})
# Returns:
# {
#   "content": "1|import os\n2|from pathlib import Path\n...",
#   "total_lines": 50,
#   "expanded_imports": {
#     "import os": [],
#     "from pathlib import Path": []
#     # NOTE: Signature expansion not yet implemented
#     # Future: Will show ["Path(path: str | os.PathLike)"]
#   }
# }

# Get diagnostics for whole project
diagnostics = await session.call_tool("get_diagnostics", {
    "severity": ["error", "warning"]
})

# Get project structure with metadata
result = await session.call_tool("get_project_structure", {
    "path": "src",
    "max_depth": 2,
    "include_sizes": True,
    "exclude_patterns": ["*.pyc", "__pycache__"]
})
# Returns:
# {
#   "root": "/absolute/path/to/src",
#   "tree": {
#     "main.py": {"type": "file", "size": 1234},
#     "utils": {
#       "type": "directory",
#       "children": {
#         "helper.py": {"type": "file", "size": 567}
#       }
#     },
#     "models": {
#       "type": "directory", 
#       "children": {},
#       "children_truncated": true  # max_depth reached
#     }
#   },
#   "file_count": 15,
#   "directory_count": 3,
#   "total_size": 45678  # bytes
# }

# Get symbols with rich metadata
result = await session.call_tool("get_symbols", {
    "file": "src/models.py",
    "symbol_types": ["class", "function"]
})
# Returns:
# {
#   "symbols": [
#     {
#       "name": "User",
#       "type": "class",
#       "line": 5,
#       "column": 0,
#       "signature": "class User",  # From LSP detail
#       "detail": "class User",
#       "children": [
#         {
#           "name": "__init__",
#           "type": "method",
#           "line": 6,
#           "column": 4,
#           "signature": "def __init__(self, name: str, age: int)",
#           "parent": "User"
#         }
#       ]
#     }
#   ],
#   "file": "/absolute/path/to/src/models.py",
#   "total_count": 15,  # All symbols including filtered
#   "language": "python"
# }
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
- Set up an LLM API key in `.env` file (copy from `.env.example`)
- Add your keys: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, etc.
- Check configuration: `make llm-info`

**For complete API reference with parameters, returns, and examples:**  
Run `make docs` and visit http://127.0.0.1:8000
