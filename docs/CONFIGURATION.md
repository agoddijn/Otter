# Configuration Guide

Otter IDE can be configured via a `.otter.toml` file at your project root. This allows you to:

- Specify which LSP servers to use
- Point to specific Python/Node.js interpreters
- Configure DAP debug adapters
- Control lazy loading and performance settings

## Quick Start

Create a `.otter.toml` file at your project root:

```toml
# Minimal Python project configuration
[lsp.python]
python_path = "${VENV}/bin/python"
server = "pyright"

[lsp.python.settings]
python.analysis.typeCheckingMode = "strict"
```

That's it! Otter will:
- Auto-detect languages in your project
- Load only the LSPs you need
- Use lazy loading by default (LSPs start when you open files)

## Configuration Locations

Otter looks for `.otter.toml` at your project root (the path you specify via `IDE_PROJECT_PATH`).

## Complete Example

See [`.otter.toml.example`](../.otter.toml.example) for a fully commented example with all options.

## Common Configurations

### Python Project with Virtual Environment

```toml
[lsp.python]
enabled = true
server = "pyright"
python_path = "${VENV}/bin/python"

[lsp.python.settings]
python.analysis.typeCheckingMode = "basic"

[dap.python]
python_path = "${VENV}/bin/python"
```

### TypeScript Project with Custom Node Path

```toml
[lsp.typescript]
enabled = true
server = "tsserver"
node_path = "/usr/local/bin/node"
```

### Rust Project

```toml
[lsp.rust]
enabled = true
server = "rust_analyzer"

[lsp.rust.settings]
rust-analyzer.cargo.features = "all"
rust-analyzer.checkOnSave.command = "clippy"
```

### Monorepo with Multiple Languages

```toml
[lsp]
# Explicitly list languages instead of auto-detect
languages = ["python", "typescript", "go"]

[lsp.python]
python_path = "backend/.venv/bin/python"

[lsp.typescript]
# Uses default settings

[lsp.go]
server = "gopls"
```

### Disable Specific Languages

```toml
[lsp]
# Auto-detect all languages
auto_detect = true
# But exclude these
disabled_languages = ["javascript"]

# Or be explicit about what to enable
# languages = ["python", "typescript"]
```

## Template Variables

Otter supports template variables in path configurations:

- `${PROJECT_ROOT}` - Absolute path to project root
- `${VENV}` - Auto-detected virtualenv path (`.venv`, `venv`, `env`, `.env`)

Example:
```toml
[lsp.python]
# These are equivalent if you have a .venv directory
python_path = "${VENV}/bin/python"
python_path = "${PROJECT_ROOT}/.venv/bin/python"
```

## Auto-Detection

By default, Otter:

1. **Scans your project** for language files (`.py`, `.js`, `.ts`, `.rs`, `.go`)
2. **Loads only necessary LSPs** based on detected files
3. **Uses lazy loading** - LSPs start when you open a file of that type

You can control this:

```toml
[lsp]
# Disable auto-detection and use explicit list
auto_detect = false
languages = ["python"]

# Or disable lazy loading (start all LSPs immediately)
lazy_load = false
```

## Auto-Installation of LSP Servers

**🚀 NEW: Batteries Included!**

Otter now automatically installs missing LSP servers on first startup. No manual setup required!

```toml
[lsp]
# Auto-install missing LSP servers (default: true)
auto_install = true
```

**What happens on startup:**
1. Otter checks which languages your project uses
2. Verifies if the needed LSP servers are installed
3. Automatically installs any missing servers
4. Shows progress with clear messages

**Example startup output:**
```
🔍 Checking LSP servers...
✅ python: pyright is installed
⚠️  javascript: typescript-language-server is not installed
⚠️  rust: rust-analyzer is not installed

📦 Installing 2 missing LSP server(s)...
   (This may take a minute on first run)

📦 Installing typescript-language-server...
   Command: npm install -g typescript typescript-language-server
✅ Successfully installed typescript-language-server

📦 Installing rust-analyzer...
   Command: rustup component add rust-analyzer
✅ Successfully installed rust-analyzer
```

**Disable auto-install** if you prefer manual control:
```toml
[lsp]
auto_install = false
```

**Prerequisites:**
- `npm` - For JavaScript/TypeScript servers
- `pip` - For Python servers
- `rustup` - For Rust server
- `go` - For Go server

If a prerequisite is missing, Otter will show installation instructions.

## Language-Specific LSP Servers

### Python
Available servers:
- `pyright` (default) - Microsoft's type checker
- `pylsp` - Python LSP server
- `ruff_lsp` - Ruff linter as LSP

```toml
[lsp.python]
server = "pyright"  # or "pylsp", "ruff_lsp"
```

### JavaScript/TypeScript
- `tsserver` (only option, default)

### Rust
- `rust_analyzer` (only option, default)

### Go
- `gopls` (only option, default)

## DAP Configuration

Debug adapter configuration follows the same pattern as LSP:

```toml
[dap.python]
enabled = true
adapter = "debugpy"
python_path = "${VENV}/bin/python"

# Custom debug configurations
[[dap.python.configurations]]
name = "Launch with args"
type = "python"
request = "launch"
program = "${file}"
args = ["--verbose", "--debug"]
```

## Performance Tuning

```toml
[performance]
# Limit concurrent LSP clients (prevents resource exhaustion)
max_lsp_clients = 5

# Limit concurrent debug sessions
max_dap_sessions = 2

# Debounce file changes (ms) before triggering LSP
file_change_debounce_ms = 300
```

## TreeSitter Configuration

Control which TreeSitter parsers are installed:

```toml
[plugins.treesitter]
# Explicitly list parsers (otherwise uses detected languages)
ensure_installed = ["python", "javascript", "rust", "json", "yaml"]

# Auto-install missing parsers
auto_install = true
```

## Disabling Features

```toml
[lsp]
enabled = false  # Disable all LSP

[dap]
enabled = false  # Disable all DAP

[plugins]
treesitter = false  # Disable TreeSitter
```

## Configuration Precedence

1. **`.otter.toml`** - Explicit configuration (highest priority)
2. **Auto-detection** - If `auto_detect = true` and no explicit config
3. **Defaults** - Built-in sensible defaults

## Debugging Configuration Issues

### Check what languages were detected:

Otter logs to stderr when starting. Look for:
```
📁 Project: my-project
🔍 Detected languages: python, javascript
```

### View effective configuration:

Use the `project://info` resource in your MCP client to see the current project info and configuration.

### Common Issues

**LSP not starting?**
- Check the server is installed (`pyright`, `rust-analyzer`, etc.)
- Verify `python_path` or `node_path` if specified
- Try disabling `lazy_load` to start LSPs immediately

**Wrong Python interpreter?**
- Use `python_path = "${VENV}/bin/python"` to point to your venv
- Or use absolute path: `python_path = "/path/to/python"`

**Too many LSPs starting?**
- Use `disabled_languages = ["lang1", "lang2"]` to exclude
- Or be explicit: `languages = ["python"]`

## Examples by Project Type

### Django Project
```toml
[lsp.python]
server = "pyright"
python_path = "${VENV}/bin/python"

[lsp.python.settings]
python.analysis.typeCheckingMode = "basic"
python.analysis.extraPaths = ["${PROJECT_ROOT}"]
```

### React + TypeScript
```toml
[lsp.typescript]
server = "tsserver"

[lsp.javascript]
enabled = false  # Using TypeScript only
```

### Rust with Clippy
```toml
[lsp.rust]
server = "rust_analyzer"

[lsp.rust.settings]
rust-analyzer.checkOnSave.command = "clippy"
rust-analyzer.cargo.allFeatures = true
```

### Go Microservice
```toml
[lsp.go]
server = "gopls"

[lsp.go.settings]
gopls.analyses = { unusedparams = true }
```

## Next Steps

- See [`.otter.toml.example`](../.otter.toml.example) for all available options
- Check [User Guide](./USER_GUIDE.md) for tool documentation
- See [Technical Guide](./TECHNICAL_GUIDE.md) for architecture details

