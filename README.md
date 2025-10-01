# Otter - The IDE for Agents

A powerful text-based IDE designed specifically for AI agents and LLMs, exposed via the Model Context Protocol (MCP). Built on top of Neovim's rich ecosystem of LSP servers and code intelligence tools.

## Overview

This project provides a comprehensive IDE interface for AI agents to interact with codebases. Instead of relying on simple file operations, agents get access to semantic code understanding, intelligent navigation, refactoring tools, and more - all through a clean MCP server interface.

## Philosophy

**Otter focuses on what agents can't easily do via shell commands**: LSP and TreeSitter-powered semantic code intelligence.

We do **NOT** reimplement shell features:
- ❌ Text/regex search → Use `rg` directly
- ❌ Running tests → Use `pytest`/`cargo test` directly
- ❌ Git operations → Use `git` directly
- ❌ Shell commands → Agents already have shell access

## Features

### 🔍 **LSP-Powered Navigation**
- Find symbol definitions with context-aware resolution
- Find all references to symbols across the project
- Type information and documentation at any position

### 🧠 **Code Intelligence**
- LSP diagnostics (linting, type errors) inline
- Symbol extraction and file outlines
- Dependency analysis (TreeSitter-based, language-agnostic)
- Context-aware code completions (LSP-powered)

### 🐛 **DAP-Powered Debugging** ✨ *NEW*
- **Language-agnostic debugging** via Neovim's DAP client
- Set breakpoints (regular and conditional)
- Step through code (over, into, out)
- Inspect variables, call stack, and expressions
- Supports Python, JavaScript/TypeScript, Rust, Go
- Full programmatic control for AI agents

### 🛠️ **LSP-Powered Refactoring** *(Coming soon)*
- Safe symbol renaming across all references
- Function extraction with smart variable handling
- Preview changes before applying

### 📁 **Enhanced File Operations**
- Read files with diagnostics inline
- Context-aware line range reading

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
cd otter

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
PYTHONPATH=src IDE_PROJECT_PATH=/path/to/project uv run python -m otter.mcp_server
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
        "cd /path/to/otter && PYTHONPATH=src IDE_PROJECT_PATH=/path/to/my/project uv run python -m otter.mcp_server"
      ],
      "env": {}
    }
  }
}
```

**Important:** Set both paths:
- `/path/to/otter` - Path to this IDE installation
- `/path/to/my/project` - Path to the project you want to analyze

You can configure multiple projects:

```json
{
  "mcpServers": {
    "frontend-ide": {
      "command": "sh",
      "args": [
        "-c",
        "cd /path/to/otter && PYTHONPATH=src IDE_PROJECT_PATH=~/code/frontend uv run python -m otter.mcp_server"
      ]
    },
    "backend-ide": {
      "command": "sh",
      "args": [
        "-c",
        "cd /path/to/otter && PYTHONPATH=src IDE_PROJECT_PATH=~/code/backend uv run python -m otter.mcp_server"
      ]
    }
  }
}
```

### Custom Python Client

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def use_otter():
    server_params = StdioServerParameters(
        command="sh",
        args=[
            "-c",
            "cd /path/to/otter && PYTHONPATH=src uv run python -m otter.mcp_server"
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

The server exposes **15 core tools** focused on LSP/TreeSitter/DAP intelligence:

| Category | Tools | Description |
|----------|-------|-------------|
| **Navigation** | `find_definition`, `find_references` | LSP-powered symbol navigation |
| **Intelligence** | `get_hover_info`, `get_symbols`, `get_completions` | Type info, outlines, autocomplete |
| **Debugging** | `start_debug_session`, `control_execution`, `inspect_state`, `set_breakpoints`, `get_debug_session_info` | DAP-powered debugging (Python, JS/TS, Rust, Go) |
| **Files** | `read_file` | Read with diagnostics inline |
| **Diagnostics** | `get_diagnostics`, `analyze_dependencies` | Errors and dependency graphs |
| **Refactoring** *(Coming)* | `rename_symbol`, `extract_function` | Safe transformations |

See [User Guide](./docs/USER_GUIDE.md) for detailed documentation on each tool.

## Example Usage

### Find where a symbol is defined

```python
result = await session.call_tool("find_definition", {
    "symbol": "NavigationService",
    "file": "server.py",
    "line": 48
})
# Returns: Definition with file, line, type, signature, docstring
```

### Find all references to a symbol

```python
result = await session.call_tool("find_references", {
    "symbol": "process_user",
    "file": "services.py",
    "line": 12
})
# Returns: List of all places where process_user is used
```

### Get type information at a position

```python
result = await session.call_tool("get_hover_info", {
    "file": "main.py",
    "line": 45,
    "column": 12
})
# Returns: Type signature, docstring, and source location
```

### Read file with diagnostics inline

```python
result = await session.call_tool("read_file", {
    "path": "src/cli_ide/server.py",
    "line_range": [40, 60],
    "include_diagnostics": true
})
# Returns content with LSP errors/warnings inline
```

### Start debugging session

```python
result = await session.call_tool("start_debug_session", {
    "file": "src/app.py",
    "breakpoints": [10, 25, 42]
})
# Returns: DebugSession with session_id, status, breakpoints
```

### Step through code and inspect variables

```python
# Step over current line
await session.call_tool("control_execution", {
    "action": "step_over"
})

# Inspect current state
result = await session.call_tool("inspect_state", {
    "expression": "user.name"
})
# Returns: stack frames, variables, and evaluation result
```

### Analyze dependencies

```python
result = await session.call_tool("analyze_dependencies", {
    "file": "core/engine.py",
    "direction": "both"
})
# Returns what this file imports and what imports it
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
- **[User Guide](./docs/USER_GUIDE.md)** - Complete tool reference and usage
- **[Dependencies](./docs/DEPENDENCIES.md)** - System requirements and installation

### Developer Documentation
- **[Contributing](./docs/CONTRIBUTING.md)** - How to contribute to Otter
- **[Roadmap](./docs/ROADMAP.md)** - Planned tools and features with specifications
- **[Architecture](./docs/ARCHITECTURE.md)** - Architecture and design decisions
- **[Technical Guide](./docs/TECHNICAL_GUIDE.md)** - Neovim and TreeSitter integration details
- **[Testing Guide](./tests/TESTING.md)** - Complete testing documentation

### Project Documentation
- **[Documentation Index](./docs/README.md)** - Navigate all documentation
- **[Changelog](./CHANGELOG.md)** - Version history and notable changes

## Development Status

**Core Features** - 13 of 15 tools complete (87%):

✅ **Implemented & Tested** (131 tests passing):

**LSP-Powered Intelligence (8 tools)**
- `find_definition` - LSP symbol definitions (7 tests)
- `find_references` - LSP symbol references (9 tests)
- `get_hover_info` - LSP type info and docs (5 tests)
- `get_symbols` - LSP file outlines (12 tests)
- `get_diagnostics` - LSP errors and warnings (12 tests)
- `get_completions` - LSP autocomplete (10 tests)
- `read_file` - Enhanced file reading (20 tests)
- `analyze_dependencies` - TreeSitter imports (6 tests)

**DAP-Powered Debugging (5 tools)** ✨ **NEW**
- `start_debug_session` - Start debugging with breakpoints (8 tests)
- `control_execution` - Step through code (10 tests)
- `inspect_state` - Variables and stack frames (12 tests)
- `set_breakpoints` - Dynamic breakpoints (included in session tests)
- `get_debug_session_info` - Session status (included in session tests)
- **Languages**: Python, JavaScript/TypeScript, Rust, Go

🚧 **Next Priorities**:
1. `rename_symbol` - LSP-powered safe refactoring (high-value)
2. `extract_function` - Smart code extraction (medium-value)
3. **12 additional tools planned** - See [ROADMAP.md](./docs/ROADMAP.md) for complete specifications

❌ **Removed** (agents can use shell directly):
- Text/regex search → Use `rg` 
- Test execution → Use `pytest`/`cargo test`
- Git operations → Use `git`
- Shell commands → Direct access
- See [User Guide](./docs/USER_GUIDE.md) for rationale

### Quality Metrics
- ✅ **Type Safety**: Zero mypy errors (strict mode)
- ✅ **Tests**: 204 tests (174 parameterized, 30 debugging), all passing
- ✅ **Language Coverage**: Python, JavaScript, Rust (58 test scenarios × 3 languages)
- ✅ **Test Framework**: Robust async polling framework for DAP testing
- ✅ **Coverage**: ~85% estimated (comprehensive integration testing)
- ✅ **Documentation**: Consolidated to 10 core documents + changelog

## Testing

The project includes a comprehensive test suite. See [Testing Guide](tests/TESTING.md) for complete documentation.

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

We welcome contributions! See the [Contributing Guide](./docs/CONTRIBUTING.md) for details on:

- Development setup and workflow
- Code patterns and best practices
- Writing tests (including language-agnostic tests)
- Pull request process

## License

[Add your license here]

## Acknowledgments

Built on top of:
- [Model Context Protocol](https://modelcontextprotocol.io) by Anthropic
- [Neovim](https://neovim.io) and its LSP implementation
- [pynvim](https://github.com/neovim/pynvim) for Python-Neovim RPC
