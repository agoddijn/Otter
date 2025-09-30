# Otter - The IDE for Agents

A powerful text-based IDE designed specifically for AI agents and LLMs, exposed via the Model Context Protocol (MCP). Built on top of Neovim's rich ecosystem of LSP servers and code intelligence tools.

## Overview

This project provides a comprehensive IDE interface for AI agents to interact with codebases. Instead of relying on simple file operations, agents get access to semantic code understanding, intelligent navigation, refactoring tools, and more - all through a clean MCP server interface.

## Features

### 🔍 **Code Navigation & Discovery**
- Find symbol definitions with context-aware resolution
- Find all references to symbols across the project
- Semantic code search that understands structure, not just text

### 🧠 **Code Intelligence**
- Hover information with type signatures and documentation
- Context-aware code completions
- Symbol extraction and analysis

### 🛠️ **Refactoring Tools**
- Safe symbol renaming across all references
- Function extraction with smart variable handling
- Preview changes before applying

### 📊 **Smart Analysis**
- Natural language code explanations
- Actionable improvement suggestions
- Semantic diff understanding (what changed, not just lines)

### 🔬 **Diagnostics & Testing**
- Real-time linting and type checking
- Dependency analysis and graph visualization
- Test execution with smart targeting
- Execution tracing for debugging

### 📁 **Workspace Management**
- Intelligent file reading with context
- Project structure exploration
- Position marking for tracking changes
- Shell command execution

## Quick Start

### System Requirements

**macOS** (Linux and Docker support coming soon)

Required system dependencies:
- **Neovim** (>= 0.9.0) - Core editor with LSP/TreeSitter
- **Ripgrep** (rg) - Fast workspace search
- **Node.js** (>= 16.0) - LSP servers
- **Git** - Plugin management
- **C Compiler** (gcc/clang) - TreeSitter parser compilation

See [docs/DEPENDENCIES.md](./docs/DEPENDENCIES.md) for detailed installation instructions.

### Quick Setup

```bash
# Clone the repository
git clone <repository-url>
cd cli-ide-4

# Check system dependencies
make check-deps

# Install missing dependencies (macOS)
make install-deps

# Install Python dependencies
make install
```

### Running the MCP Server

The IDE is exposed as an MCP server that communicates over stdio.

#### Development Mode (with MCP Inspector)

```bash
# Run with interactive inspector for testing (uses current directory)
make dev

# Or specify a project path
make dev PROJECT=/path/to/your/project

# Or use environment variable
IDE_PROJECT_PATH=/path/to/project make dev
```

This opens the MCP Inspector UI where you can:
- View all available tools
- Test tool calls interactively
- See request/response payloads
- Debug server behavior

#### Production Mode

```bash
# Run the server directly (uses current directory)
make run

# Or specify a project path
make run PROJECT=/path/to/your/project

# Or use environment variable directly
PYTHONPATH=src IDE_PROJECT_PATH=/path/to/project uv run python -m cli_ide.mcp_server
```

### Available Make Commands

Run `make help` to see all available commands:

```bash
make help            # Show all commands
make install         # Install dependencies
make dev             # Run with MCP inspector (development)
make run             # Run server (production)
make test            # Run all tests
make test-unit       # Run unit tests only
make test-coverage   # Run tests with coverage report
make lint            # Run linter checks
make format          # Format code
make clean           # Clean temporary files
```

## Using with MCP Clients

### Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "my-project-ide": {
      "command": "sh",
      "args": [
        "-c",
        "cd /path/to/cli-ide-4 && PYTHONPATH=src IDE_PROJECT_PATH=/path/to/my/project uv run python -m cli_ide.mcp_server"
      ],
      "env": {}
    }
  }
}
```

**Important:** Set both paths:
- `/path/to/cli-ide-4` - Path to this IDE installation
- `/path/to/my/project` - Path to the project you want to analyze

You can configure multiple projects:

```json
{
  "mcpServers": {
    "frontend-ide": {
      "command": "sh",
      "args": [
        "-c",
        "cd /path/to/cli-ide-4 && PYTHONPATH=src IDE_PROJECT_PATH=~/code/frontend uv run python -m cli_ide.mcp_server"
      ]
    },
    "backend-ide": {
      "command": "sh",
      "args": [
        "-c",
        "cd /path/to/cli-ide-4 && PYTHONPATH=src IDE_PROJECT_PATH=~/code/backend uv run python -m cli_ide.mcp_server"
      ]
    }
  }
}
```

### Custom Python Client

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def use_cli_ide():
    server_params = StdioServerParameters(
        command="sh",
        args=[
            "-c",
            "cd /path/to/cli-ide-4 && PYTHONPATH=src uv run python -m cli_ide.mcp_server"
        ],
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Find a definition
            result = await session.call_tool(
                "find_definition",
                {"symbol": "CliIdeServer"}
            )
            print(result.content)
```

## Available Tools

The server exposes **21 tools** across multiple categories:

| Category | Tools | Description |
|----------|-------|-------------|
| **Navigation** | `find_definition`, `find_references`, `search` | Navigate and discover code |
| **Intelligence** | `get_hover_info`, `get_completions` | Type information and suggestions |
| **Files** | `read_file`, `get_project_structure`, `get_symbols` | File and project operations |
| **Refactoring** | `rename_symbol`, `extract_function` | Safe code transformations |
| **Analysis** | `explain_code`, `suggest_improvements`, `semantic_diff` | AI-powered insights |
| **Diagnostics** | `get_diagnostics`, `analyze_dependencies` | Errors and dependencies |
| **Testing** | `run_tests`, `trace_execution` | Test and debug |
| **Workspace** | `mark_position`, `diff_since_mark`, `vim_command`, `shell` | Workspace utilities |

See [MCP_USAGE.md](./MCP_USAGE.md) for detailed documentation on each tool.

## Example Usage

### Find where a symbol is defined

```python
result = await session.call_tool("find_definition", {
    "symbol": "NavigationService"
})
# Returns: Definition(file="...", line=8, type="class", ...)
```

### Search semantically

```python
result = await session.call_tool("search", {
    "query": "error handling in async functions",
    "search_type": "semantic"
})
# Finds try/except blocks in async functions
```

### Read file with context

```python
result = await session.call_tool("read_file", {
    "path": "src/cli_ide/server.py",
    "line_range": [40, 60],
    "include_imports": true,
    "include_diagnostics": true
})
# Returns content with expanded imports and inline errors
```

### Get improvement suggestions

```python
result = await session.call_tool("suggest_improvements", {
    "file": "src/cli_ide/services/analysis.py",
    "focus_areas": ["error_handling", "type_safety"]
})
# Returns actionable suggestions with examples
```

## Architecture

```
┌───────────────────────────────────────────────────────────┐
│                    MCP Server Layer                       │
│         (FastMCP - Protocol & Serialization)              │
└─────────────────────────────┬─────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────┐
│                  CliIdeServer Facade                      │
│         (Coordinates between service layers)              │
└─────────────────────────────┬─────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼───────┐  ┌─────────▼─────────┐  ┌────────▼────────┐
│  Navigation   │  │   Refactoring     │  │    Analysis     │
│   Service     │  │     Service       │  │     Service     │
└───────┬───────┘  └─────────┬─────────┘  └────────┬────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────┐
│                   Neovim Wrapper Layer                    │
│         (RPC client, LSP, TreeSitter, Buffers)            │
└─────────────────────────────┬─────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────┐
│              Neovim Instance (Headless)                   │
│    LSP Servers • TreeSitter • Plugins • Vim Runtime       │
└───────────────────────────────────────────────────────────┘
```

See [ARCHITECTURE.md](./docs/ARCHITECTURE.md) for detailed architectural documentation.

## Documentation

### User Documentation
- **[README.md](./README.md)** - This file (quick start and overview)
- **[DEPENDENCIES.md](./docs/DEPENDENCIES.md)** - System requirements and installation
- **[SPECIFICATION.md](./docs/SPECIFICATION.md)** - Complete specification of all 21 IDE tools

### Developer Documentation
- **[ARCHITECTURE.md](./docs/ARCHITECTURE.md)** - Architecture and design decisions
- **[TECHNICAL_GUIDE.md](./docs/TECHNICAL_GUIDE.md)** - Neovim and TreeSitter integration details
- **[DEVELOPMENT.md](./docs/DEVELOPMENT.md)** - Implementation patterns and best practices

## Development Status

**Phase 1 Complete** (8 of 21 tools implemented):

✅ **Implemented & Tested** (91 tests passing):
- `get_project_structure` - File tree traversal (8 tests)
- `read_file` - File reading with LSP context (20 tests)
- `get_diagnostics` - LSP errors and warnings (12 tests)
- `analyze_dependencies` - Import analysis via TreeSitter (6 tests)
- `find_definition` - Jump to symbol definitions (7 tests)
- `find_references` - Find all symbol references (9 tests)
- `get_symbols` - File outline via LSP (12 tests)
- `get_hover_info` - Type info and docs (5 tests)

⏳ **In Progress** (Phase 2):
- `search` - Workspace-wide code search
- `get_completions` - LSP-based autocomplete
- `get_quick_fixes` - LSP code actions

📋 **Planned** (13 remaining tools):
- Refactoring tools (rename, extract, etc.)
- Code formatting and organization
- Test execution and debugging
- See [SPECIFICATION.md](./docs/SPECIFICATION.md) for complete list

### Quality Metrics
- ✅ **Type Safety**: Zero mypy errors (strict mode)
- ✅ **Tests**: 91 tests (33 integration, 58 unit), all passing
- ✅ **Coverage**: ~80% estimated (comprehensive integration testing)
- ✅ **Documentation**: 3,000+ lines across 5 documents

## Testing

The project includes a comprehensive test suite. See [tests/README.md](tests/README.md) for details.

```bash
# Run all tests
make test

# Run with coverage report
make test-coverage

# Run in watch mode (auto-rerun on changes)
make test-watch
```

## Requirements

- Python 3.12+
- Neovim 0.9+ (for the backend, when implemented)
- UV package manager
- Git (for semantic diff and workspace features)

## Contributing

This project is structured to make contributions easy:

1. **Adding new tools**: Add decorated functions in `src/cli_ide/mcp_server.py`
2. **Implementing services**: Fill in service methods in `src/cli_ide/services/`
3. **Neovim integration**: Implement client in `src/cli_ide/neovim/`
4. **Language support**: Add modules in `src/cli_ide/languages/`

## License

[Add your license here]

## Acknowledgments

Built on top of:
- [Model Context Protocol](https://modelcontextprotocol.io) by Anthropic
- [Neovim](https://neovim.io) and its LSP implementation
- [pynvim](https://github.com/neovim/pynvim) for Python-Neovim RPC
