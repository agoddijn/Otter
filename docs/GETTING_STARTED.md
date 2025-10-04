# Getting Started with Otter

This guide will help you set up Otter and integrate it with your MCP client.

## Prerequisites

### System Requirements

Otter requires:
- **Python 3.12+**
- **Neovim 0.9+** (headless mode)
- **Node.js 16+** (for JavaScript/TypeScript LSP servers)
- **Git** (for plugin management)

Optional (for specific languages):
- **Rust** (for Rust projects)
- **Go** (for Go projects)

### Platform Support

- ✅ **macOS**: Fully supported
- ✅ **Linux**: Fully supported
- 🚧 **Docker**: Supported (headless environments)
- ⚠️ **Windows**: Not officially supported (may work via WSL)

## Installation

### Option 1: Via PyPI (Coming Soon)

```bash
# Install Otter globally
pip install otter-ide

# Verify installation
otter --version
```

### Option 2: From Source (Current Method)

```bash
# Clone the repository
git clone https://github.com/your-org/otter.git
cd otter

# Install dependencies
pip install uv  # If not already installed
make install

# Verify installation
make check-deps
```

### Installing System Dependencies

#### macOS

```bash
# Using Homebrew
brew install neovim node git ripgrep

# Verify versions
nvim --version  # Should be 0.9+
node --version  # Should be 16+
```

#### Linux (Ubuntu/Debian)

```bash
# Install Neovim from official PPA (for latest version)
sudo add-apt-repository ppa:neovim-ppa/unstable
sudo apt update
sudo apt install neovim nodejs npm git ripgrep

# Verify versions
nvim --version
node --version
```

#### Linux (Arch)

```bash
# Install from official repos
sudo pacman -S neovim nodejs npm git ripgrep

# Verify versions
nvim --version
node --version
```

## Quick Start

### 1. Test Otter Locally

Before integrating with an MCP client, test Otter locally:

```bash
# Navigate to Otter directory
cd /path/to/otter

# Run with MCP Inspector (interactive testing)
make dev PROJECT=/path/to/your/project

# Or run the server directly
make run PROJECT=/path/to/your/project
```

The MCP Inspector will open in your browser, allowing you to:
- View all available tools
- Test tool calls interactively
- See request/response payloads
- Verify Otter is working correctly

### 2. Configure Your Project (Optional)

Otter works without configuration, but you can customize behavior with a `.otter.toml` file:

```bash
# Copy an example configuration
cp /path/to/otter/examples/python-project.otter.toml /path/to/your/project/.otter.toml

# Or create from scratch
cat > /path/to/your/project/.otter.toml << 'EOF'
[lsp.python]
enabled = true
server = "pyright"
python_path = "${VENV}/bin/python"

[lsp.python.settings]
python.analysis.typeCheckingMode = "basic"
EOF
```

See [examples/](../examples/) for configuration templates and [CONFIGURATION.md](./CONFIGURATION.md) for full reference.

### 3. Integrate with MCP Client

Choose your MCP client below:

## MCP Client Integration

### Claude Desktop

Add Otter to your Claude Desktop configuration:

**Location**: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)

```json
{
  "mcpServers": {
    "my-project-ide": {
      "command": "sh",
      "args": [
        "-c",
        "cd /path/to/otter && PYTHONPATH=src IDE_PROJECT_PATH=/path/to/your/project uv run python -m otter.mcp_server"
      ],
      "env": {}
    }
  }
}
```

**Important**: Update both paths:
- `/path/to/otter` - Where you installed Otter
- `/path/to/your/project` - The project you want to work on

**Multiple Projects**: Configure separate Otter instances for each project:

```json
{
  "mcpServers": {
    "frontend-ide": {
      "command": "sh",
      "args": ["-c", "cd /path/to/otter && PYTHONPATH=src IDE_PROJECT_PATH=~/code/frontend uv run python -m otter.mcp_server"]
    },
    "backend-ide": {
      "command": "sh",
      "args": ["-c", "cd /path/to/otter && PYTHONPATH=src IDE_PROJECT_PATH=~/code/backend uv run python -m otter.mcp_server"]
    }
  }
}
```

**Restart Claude Desktop** after editing the configuration.

### Custom Python Client

Use the MCP Python SDK to integrate Otter:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def use_otter():
    # Configure server
    server_params = StdioServerParameters(
        command="sh",
        args=[
            "-c",
            "cd /path/to/otter && PYTHONPATH=src IDE_PROJECT_PATH=/path/to/project uv run python -m otter.mcp_server"
        ],
    )
    
    # Connect to server
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize session
            await session.initialize()
            
            # Use Otter tools
            result = await session.call_tool(
                "find_definition",
                {"symbol": "MyClass", "file": "main.py", "line": 10}
            )
            print(result.content)

# Run the client
import asyncio
asyncio.run(use_otter())
```

### Other MCP Clients

Otter works with any MCP-compatible client. The general pattern:

1. **Command**: `sh`
2. **Args**: 
   ```
   ["-c", "cd /path/to/otter && PYTHONPATH=src IDE_PROJECT_PATH=/path/to/project uv run python -m otter.mcp_server"]
   ```
3. **Working Directory**: Can be anywhere (we `cd` to Otter dir in command)
4. **Environment**: Optional, usually empty

Consult your MCP client's documentation for specific configuration format.

## First Run Experience

### Automatic LSP Server Installation

On first run, Otter will check for required LSP servers:

```
🔍 Checking LSP servers for your project...
⚠️  python: pyright is not installed
⚠️  javascript: typescript-language-server is not installed

📦 Installing 2 missing LSP server(s)...
   (This may take a minute on first run)

📦 Installing pyright...
✅ Successfully installed pyright

📦 Installing typescript-language-server...
✅ Successfully installed typescript-language-server

✅ All LSP servers ready!
```

This happens automatically - no manual intervention needed.

### Auto-Detected Runtimes

Otter automatically detects your project's runtime:

```
🔍 Detecting Python runtime...
✅ Found virtual environment: /path/to/project/.venv
   Using Python: /path/to/project/.venv/bin/python3.12

🔍 Detecting Node.js runtime...
✅ Found .nvmrc: v18.17.0
   Using Node: ~/.nvm/versions/node/v18.17.0/bin/node
```

### What if detection fails?

If Otter can't find your runtime:

1. **Python**: Creates/uses system Python (with warning)
2. **Node.js**: Uses system Node.js
3. **Rust**: Uses system Rust toolchain

You can override detection with explicit configuration (see [CONFIGURATION.md](./CONFIGURATION.md)).

## Verifying Installation

### Test Basic Functionality

Use the MCP Inspector to test:

```bash
cd /path/to/otter
make dev PROJECT=/path/to/test/project
```

Try these tools:
1. **get_symbols** - Get outline of a file
2. **find_definition** - Jump to a symbol definition
3. **get_diagnostics** - See LSP errors/warnings
4. **start_debug_session** - Start a debug session

If all work, Otter is properly installed!

### Check LSP Servers

Verify LSP servers are installed:

```bash
# Python
which pyright
pyright --version

# TypeScript/JavaScript
which typescript-language-server
typescript-language-server --version

# Rust
which rust-analyzer
rust-analyzer --version
```

### Common Issues

**Issue**: `nvim: command not found`
- **Solution**: Install Neovim (see System Dependencies above)

**Issue**: LSP server installation fails
- **Solution**: Install Node.js/npm, then retry

**Issue**: `ModuleNotFoundError: No module named 'otter'`
- **Solution**: Check `PYTHONPATH=src` is in command, or install with `pip install -e .`

**Issue**: Permission denied errors
- **Solution**: Check file permissions on Otter directory

**Issue**: Neovim starts but LSP doesn't work
- **Solution**: Check `.otter.toml` configuration, verify LSP server is installed

## Next Steps

Now that Otter is installed:

1. **Learn Configuration**: Read [CONFIGURATION.md](./CONFIGURATION.md) for advanced setup
2. **Understand Capabilities**: See the root [README.md](../README.md) for all available tools
3. **Explore Examples**: Check [examples/](../examples/) for project configurations
4. **Contribute**: Read [CONTRIBUTING.md](./CONTRIBUTING.md) to help improve Otter

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/your-org/otter/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/otter/discussions)
- **Documentation**: [docs/](.) - All documentation
- **Examples**: [examples/](../examples/) - Configuration examples

Welcome to Otter! 🦦

