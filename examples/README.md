# Otter Examples

This directory contains examples demonstrating Otter's features and usage patterns.

## 📁 Examples

### 🐛 Debugging Examples

#### `debug_server.py` - Debug a Web Server
Debug a running server (like Uvicorn, Flask, FastAPI) with full control over execution, breakpoints, and variable inspection.

**Features:**
- Module-based launching (`python -m uvicorn`)
- Environment variable configuration
- Breakpoint management
- Variable inspection while paused

**Usage:**
```bash
python examples/debug_server.py
```

#### `debug_tests.py` - Debug Test Suites
Debug your test suite (pytest, unittest) to understand test failures and inspect test state.

**Features:**
- Debug specific test cases
- Step through test execution
- Inspect fixtures and test data

**Usage:**
```bash
python examples/debug_tests.py
```

### ⚙️ Configuration Examples

#### `python-project.otter.toml`
Basic Python project configuration with venv detection and LSP settings.

**Use case:** Single-language Python project

#### `typescript-project.otter.toml`
TypeScript/JavaScript project with nvm support and ts-server configuration.

**Use case:** Single-language TypeScript/JavaScript project

#### `fullstack-project.otter.toml`
Multi-language monorepo configuration with Python backend and TypeScript frontend.

**Use case:** Fullstack monorepo with multiple languages

## 🚀 Quick Start

### 1. Install Otter

```bash
pip install otter-ide
```

### 2. Run an Example

```bash
# Debug a server
python examples/debug_server.py

# Debug tests
python examples/debug_tests.py
```

### 3. Configure Your Project

Copy and customize a configuration file:

```bash
# For Python projects
cp examples/python-project.otter.toml .otter.toml

# For TypeScript projects
cp examples/typescript-project.otter.toml .otter.toml

# For monorepos
cp examples/fullstack-project.otter.toml .otter.toml
```

## 📚 What You'll Learn

### From `debug_server.py`
- How to start a debug session for a server
- Setting breakpoints in API routes
- Inspecting request/response data
- Stepping through server code
- Managing environment variables

### From `debug_tests.py`
- Debugging failing tests
- Inspecting test fixtures
- Understanding test execution flow
- Debugging test setup/teardown

### From Configuration Examples
- Project-specific LSP configuration
- Runtime auto-detection (venvs, nvm, etc.)
- Multi-language project setup
- Custom LSP server settings

## 💡 Tips

### Virtual Environments
Otter automatically detects and uses your project's virtual environment:
- Python: `.venv/bin/python` or `venv/bin/python`
- Node.js: `.nvmrc` or `package.json`
- Rust: `rust-toolchain` or `rust-toolchain.toml`

### Language Servers
Otter auto-installs missing LSP servers on first run:
- Python: `pyright`
- JavaScript/TypeScript: `typescript-language-server`
- Rust: `rust-analyzer`

### Debug Adapters
Debug adapters are auto-installed when needed:
- Python: `debugpy`
- JavaScript/TypeScript: `node-debug2`
- Rust: `codelldb`

## 🔗 More Resources

- **Documentation:** https://otter-ide.readthedocs.io
- **GitHub:** https://github.com/your-org/otter
- **Issues:** https://github.com/your-org/otter/issues

## 🤝 Contributing Examples

Have a useful example? We'd love to see it!

1. Create your example file
2. Add comprehensive docstrings
3. Test it works end-to-end
4. Submit a PR!

See [CONTRIBUTING.md](../docs/CONTRIBUTING.md) for guidelines.

