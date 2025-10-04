# Otter 🦦

**A batteries-included, agent-first IDE exposed over MCP**

Give your AI agents the power of a full IDE - code intelligence, navigation, and debugging - without the GUI overhead.

---

## What is Otter?

Otter is a **headless IDE server** that provides AI agents with comprehensive code understanding through the Model Context Protocol (MCP). Built on Neovim's mature LSP and DAP infrastructure, it offers semantic code intelligence that shell commands cannot provide.

### Key Features

🧠 **LSP-Powered Intelligence**
- Find definitions, references, and symbols
- Type information and diagnostics
- Code completions and hover info

🐛 **Full Debugging Support**
- Breakpoints and stepping
- Variable inspection
- Stack traces and expressions
- Python, TypeScript, JavaScript, Rust, Go

🔋 **Batteries Included**
- Auto-installs missing LSP servers
- Auto-detects virtual environments
- Zero configuration needed
- Works in any environment

🎯 **Agent-First Design**
- MCP-native interface
- Structured responses
- No GUI dependencies
- Drop-in anywhere

## Why Otter?

Traditional IDEs are built for humans, not agents. They require GUIs, mouse interaction, and visual interfaces. Otter is different:

- ✅ **MCP-native**: Simple tool calls, no adapters
- ✅ **Lightweight**: Headless, no Electron/browser
- ✅ **Semantic**: LSP intelligence, not just text search
- ✅ **Free**: Open source, MIT licensed

**Agents need IDEs too.** Otter is that IDE.

→ Read [docs/WHY.md](./docs/WHY.md) for the full story

## Quick Start

### Prerequisites

- Python 3.12+
- Neovim 0.9+
- Node.js 16+ (for JavaScript/TypeScript)

### Installation

```bash
# Clone and install
git clone https://github.com/your-org/otter.git
cd otter
make install

# Verify
make check-deps
```

### Usage with Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "my-project": {
      "command": "sh",
      "args": [
        "-c",
        "cd /path/to/otter && PYTHONPATH=src IDE_PROJECT_PATH=/path/to/your/project uv run python -m otter.mcp_server"
      ]
    }
  }
}
```

Restart Claude Desktop and start coding!

→ Read [docs/GETTING_STARTED.md](./docs/GETTING_STARTED.md) for detailed instructions

## Example Usage

### Navigate Code

```python
# Find where a symbol is defined
find_definition("DatabaseService", file="main.py", line=45)

# Find all references to a symbol
find_references("process_payment", file="services.py", line=12)

# Get file structure
get_symbols("app.py")
```

### Debug Code

```python
# Start debugging with breakpoints
start_debug_session("test_checkout.py", breakpoints=[45, 67])

# Step through code
control_execution("step_over")

# Inspect variables
inspect_state("cart.total")
```

### Understand Code

```python
# Get type information
get_hover_info("main.py", line=23, column=15)

# Check for errors
get_diagnostics("services.py")

# Analyze dependencies
analyze_dependencies("core/engine.py")
```

## Available Tools

| Category | Tools |
|----------|-------|
| **Navigation** | `find_definition`, `find_references`, `get_symbols` |
| **Intelligence** | `get_hover_info`, `get_completions`, `get_diagnostics` |
| **Debugging** | `start_debug_session`, `control_execution`, `inspect_state`, `set_breakpoints`, `get_debug_session_info` |
| **Analysis** | `analyze_dependencies`, `read_file` |
| **Refactoring** | *(coming soon)* `rename_symbol`, `extract_function` |

**15 tools total** - focused on LSP/DAP capabilities that agents cannot access via shell.

## Configuration

Otter works **without configuration**. For advanced setups, create `.otter.toml`:

```toml
# Python project with virtual environment
[lsp.python]
python_path = "${VENV}/bin/python"
server = "pyright"

[lsp.python.settings]
python.analysis.typeCheckingMode = "strict"
```

See [examples/](./examples/) for templates and [docs/CONFIGURATION.md](./docs/CONFIGURATION.md) for full reference.

## Documentation

- **[What is Otter?](./docs/README.md)** - Philosophy, architecture, design principles
- **[Why Otter?](./docs/WHY.md)** - Use cases and value proposition  
- **[Getting Started](./docs/GETTING_STARTED.md)** - Installation and setup
- **[Configuration](./docs/CONFIGURATION.md)** - Detailed configuration guide
- **[Architecture](./docs/ARCHITECTURE.md)** - High-level system design
- **[Contributing](./docs/CONTRIBUTING.md)** - Development guide

## Project Status

**Production-Ready Foundation**:
- ✅ 15 core tools implemented and tested
- ✅ 204 tests passing (zero mypy errors)
- ✅ Multi-language support (Python, TypeScript, JavaScript, Rust, Go)
- ✅ Full debugging capabilities
- ✅ Comprehensive documentation

**Ready for Use**: Stable MCP interface, robust LSP/DAP integration, flexible configuration.

## Requirements

- Python 3.12+
- Neovim 0.9+
- Node.js 16+ (for JavaScript/TypeScript support)
- Git (for plugin management)

Platform support:
- ✅ macOS
- ✅ Linux
- 🚧 Docker (headless environments)
- ⚠️ Windows (via WSL)

## Contributing

We welcome contributions! See [docs/CONTRIBUTING.md](./docs/CONTRIBUTING.md) for:

- Development setup
- Code patterns and best practices
- Writing tests
- Pull request process

## License

MIT License - See [LICENSE](./LICENSE) for details

## Acknowledgments

Built on:
- [Model Context Protocol](https://modelcontextprotocol.io) by Anthropic
- [Neovim](https://neovim.io) and its LSP/DAP ecosystem
- [pynvim](https://github.com/neovim/pynvim) for Python-Neovim RPC

---

**Give your agents an IDE. Try Otter today.** 🦦
