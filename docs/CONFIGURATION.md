# Configuration Guide

Otter works **without configuration** for most projects. However, you can customize behavior with a `.otter.toml` file at your project root.

## Quick Start

### Zero Configuration (Recommended)

For most projects, just run Otter - it will:
- Auto-detect languages in your project
- Find your virtual environments automatically
- Install missing LSP servers
- Use sensible defaults

### Custom Configuration

Create `.otter.toml` at your project root when you need to:
- Specify explicit Python/Node.js interpreter paths
- Configure LSP server settings
- Set up debugging configurations
- Tune performance for large projects

**Minimal example**:
```toml
[lsp.python]
python_path = "${VENV}/bin/python"
server = "pyright"

[lsp.python.settings]
python.analysis.typeCheckingMode = "strict"
```

## Configuration File Location

Otter looks for `.otter.toml` at your project root (the path specified by `IDE_PROJECT_PATH`).

## Complete Examples

See [examples/](../examples/) directory for full configuration examples:
- **python-project.otter.toml** - Python with venv
- **typescript-project.otter.toml** - TypeScript/JavaScript
- **fullstack-project.otter.toml** - Multi-language monorepo

## Language Configuration

### Python

```toml
[lsp.python]
enabled = true
server = "pyright"  # or "pylsp", "ruff_lsp"
python_path = "${VENV}/bin/python"

[lsp.python.settings]
python.analysis.typeCheckingMode = "basic"  # "off", "basic", "standard", "strict"
python.analysis.autoSearchPaths = true
python.analysis.useLibraryCodeForTypes = true

# Optional: exclude paths
# python.analysis.exclude = ["**/node_modules", "**/__pycache__"]
```

**Available servers**:
- `pyright` (recommended) - Microsoft's fast type checker
- `pylsp` - Community-driven, plugin-based
- `ruff_lsp` - Ruff linter as LSP

### TypeScript / JavaScript

```toml
[lsp.typescript]
enabled = true
server = "tsserver"

[lsp.typescript.settings]
typescript.suggest.autoImports = true
typescript.updateImportsOnFileMove.enabled = "always"

[lsp.javascript]
enabled = true
server = "tsserver"
```

### Rust

```toml
[lsp.rust]
enabled = true
server = "rust_analyzer"

[lsp.rust.settings]
rust-analyzer.cargo.features = "all"
rust-analyzer.checkOnSave.command = "clippy"
rust-analyzer.cargo.allFeatures = true
```

### Go

```toml
[lsp.go]
enabled = true
server = "gopls"

[lsp.go.settings]
gopls.analyses = { unusedparams = true }
```

## Runtime Detection

Otter automatically detects your project's runtime environment:

### Python Virtual Environments

Auto-detected patterns (in order):
1. `.venv/` (recommended)
2. `venv/`
3. `env/`
4. `virtualenv/`

Use `${VENV}` variable to reference auto-detected venv:
```toml
[lsp.python]
python_path = "${VENV}/bin/python"
```

Or specify explicit path:
```toml
[lsp.python]
python_path = "backend/.venv/bin/python"
# or absolute:
python_path = "/usr/local/bin/python3.11"
```

### Node.js Versions

Auto-detected from:
1. `.nvmrc` file
2. `package.json` `engines.node` field
3. System Node.js

### Rust Toolchains

Auto-detected from:
1. `rust-toolchain.toml`
2. `rust-toolchain` file
3. System Rust installation

## Template Variables

Use these variables in configuration paths:

- **`${VENV}`** - Auto-detected Python virtual environment
- **`${PROJECT_ROOT}`** - Absolute path to project root

Example:
```toml
[lsp.python]
python_path = "${VENV}/bin/python"

[lsp.python.settings]
python.analysis.extraPaths = ["${PROJECT_ROOT}/src"]
```

## Multi-Language Projects (Monorepos)

For projects with multiple languages:

```toml
[lsp]
# Explicitly list languages (better performance than auto-detect)
languages = ["python", "typescript", "javascript"]

[lsp.python]
# Backend with its own venv
python_path = "backend/.venv/bin/python"

[lsp.typescript]
# Frontend configuration
# Uses system Node.js or .nvmrc if present

[lsp.javascript]
enabled = true

[performance]
# Limit concurrent LSP servers
max_lsp_clients = 3
```

## Debug Adapter Configuration (DAP)

Configure debugging for your languages:

### Python Debugging

```toml
[dap.python]
enabled = true
adapter = "debugpy"
python_path = "${VENV}/bin/python"

# Optional: environment variables for debug sessions
[dap.python.env]
DEBUG = "true"
LOG_LEVEL = "debug"
```

### TypeScript / JavaScript Debugging

```toml
[dap.typescript]
enabled = true
adapter = "node2"  # or "pwa-node" for browser debugging

[dap.javascript]
enabled = true
adapter = "node2"
```

### Rust Debugging

```toml
[dap.rust]
enabled = true
adapter = "codelldb"
```

## Auto-Installation of LSP Servers

By default, Otter automatically installs missing LSP servers:

```toml
[lsp]
auto_install = true  # default
```

**First-run experience**:
```
🔍 Checking LSP servers...
⚠️  typescript-language-server not installed

📦 Installing missing LSP servers...
✅ Successfully installed typescript-language-server
```

**Disable auto-install** if you prefer manual control:
```toml
[lsp]
auto_install = false
```

**Prerequisites** (for auto-install):
- `npm` - For JavaScript/TypeScript servers
- `pip` - For Python servers  
- `rustup` - For Rust server
- `go` - For Go server

## Performance Tuning

### Limit Concurrent LSP Clients

For large monorepos:

```toml
[performance]
max_lsp_clients = 3  # default: 5
max_dap_sessions = 2  # default: 3
```

### Control Loading Behavior

```toml
[lsp]
# Disable auto-detection, use explicit list
auto_detect = false
languages = ["python", "typescript"]

# Disable lazy loading (start all LSPs immediately)
lazy_load = false  # default: true
```

### Disable Specific Languages

```toml
[lsp]
# Auto-detect all languages except these
disabled_languages = ["javascript", "markdown"]

# Or be explicit about what to enable
# languages = ["python", "typescript"]
```

## TreeSitter Configuration

```toml
[plugins.treesitter]
# Explicitly list parsers (otherwise uses detected languages)
ensure_installed = ["python", "javascript", "rust", "json", "yaml"]

# Auto-install missing parsers
auto_install = true  # default
```

## Disabling Features

```toml
[lsp]
enabled = false  # Disable all LSP

[dap]
enabled = false  # Disable all debugging

[plugins]
treesitter = false  # Disable TreeSitter
```

## Configuration by Project Type

### Python Web App (Django/FastAPI)

```toml
[lsp.python]
server = "pyright"
python_path = "${VENV}/bin/python"

[lsp.python.settings]
python.analysis.typeCheckingMode = "basic"
python.analysis.extraPaths = ["${PROJECT_ROOT}"]

[dap.python]
enabled = true
python_path = "${VENV}/bin/python"
```

### React + TypeScript Frontend

```toml
[lsp.typescript]
server = "tsserver"

[lsp.typescript.settings]
typescript.suggest.autoImports = true
typescript.preferences.importModuleSpecifier = "relative"

[lsp.javascript]
enabled = false  # TypeScript-only project
```

### Rust CLI Tool

```toml
[lsp.rust]
server = "rust_analyzer"

[lsp.rust.settings]
rust-analyzer.checkOnSave.command = "clippy"
rust-analyzer.cargo.allFeatures = true

[dap.rust]
enabled = true
adapter = "codelldb"
```

### Go Microservice

```toml
[lsp.go]
server = "gopls"

[lsp.go.settings]
gopls.analyses = { unusedparams = true, shadow = true }

[dap.go]
enabled = true
adapter = "delve"
```

### Full-Stack Monorepo

See [examples/fullstack-project.otter.toml](../examples/fullstack-project.otter.toml) for a complete example.

## Troubleshooting

### LSP Server Not Starting

**Check installation**:
```bash
# Python
which pyright

# TypeScript/JavaScript  
which typescript-language-server

# Rust
which rust-analyzer
```

**Verify configuration**:
```toml
[lsp.python]
enabled = true  # Make sure it's explicitly enabled
python_path = "${VENV}/bin/python"  # Check path is correct
```

**Disable lazy loading** (for debugging):
```toml
[lsp]
lazy_load = false  # Start all LSPs immediately
```

### Wrong Python Interpreter

Check auto-detection:
```
🔍 Detecting Python runtime...
✅ Found virtual environment: /path/to/.venv
```

Override if needed:
```toml
[lsp.python]
python_path = "/path/to/specific/python"
```

### Too Many LSP Servers

Limit what starts:
```toml
[lsp]
languages = ["python", "typescript"]  # Only these
# or
disabled_languages = ["markdown", "json"]  # Exclude these

[performance]
max_lsp_clients = 3  # Hard limit
```

## Configuration Precedence

1. **`.otter.toml`** - Explicit configuration (highest priority)
2. **Auto-detection** - Runtime environment detection
3. **Defaults** - Built-in sensible defaults

## Next Steps

- **Examples**: See [examples/](../examples/) for complete configurations
- **Getting Started**: Read [GETTING_STARTED.md](./GETTING_STARTED.md) for installation
- **Architecture**: Read [README.md](./README.md) for high-level overview
- **Contributing**: Read [CONTRIBUTING.md](./CONTRIBUTING.md) to help improve Otter
