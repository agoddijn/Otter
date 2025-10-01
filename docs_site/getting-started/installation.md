# Installation

## System Requirements

- **macOS** (Linux support coming soon)
- **Neovim** >= 0.9.0
- **Ripgrep** (rg)
- **Node.js** >= 16.0
- **Git**
- **C Compiler** (gcc/clang)

## Quick Setup

```bash
# Clone repository
git clone <repository-url>
cd otter

# Check dependencies
make check-deps

# Install missing dependencies (macOS)
make install-deps

# Install Python dependencies
make install
```

## Usage with Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "my-project-ide": {
      "command": "sh",
      "args": [
        "-c",
        "cd /path/to/otter && PYTHONPATH=src IDE_PROJECT_PATH=/path/to/project uv run python -m otter.mcp_server"
      ]
    }
  }
}
```

## Development

```bash
# Run MCP inspector
make dev

# Run tests
make test

# With coverage
make test-coverage
```

For detailed system dependencies, see the repository's `docs/DEPENDENCIES.md`.

