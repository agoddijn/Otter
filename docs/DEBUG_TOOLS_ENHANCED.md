# Enhanced Debug Tools - Module Launching & Environment Control

## Overview

Otter's debug tools have been significantly enhanced to support real-world debugging scenarios, particularly for servers, frameworks, and module-based applications.

## What's New

### 1. **Module-Based Launching** 🎯

Debug applications launched with `python -m module_name`:

```python
start_debug_session(
    module="uvicorn",
    args=["fern_mono.main:app", "--port", "8000", "--reload"]
)
```

**Use cases:**
- Web servers: `uvicorn`, `gunicorn`, `flask run`
- Testing: `pytest`, `unittest`
- Tools: `black`, `ruff`, any module

### 2. **Environment Variables** 🔧

Pass environment variables to the debugged process:

```python
start_debug_session(
    module="uvicorn",
    args=["app:main"],
    env={
        "DOPPLER_ENV": "1",
        "DEBUG": "true",
        "DATABASE_URL": "postgresql://localhost/dev"
    }
)
```

**Use cases:**
- Configuration (API keys, feature flags)
- Database connections
- Debug mode flags
- Cloud provider credentials

### 3. **Working Directory Control** 📁

Specify the working directory for the debug session:

```python
start_debug_session(
    file="tests/integration/test_api.py",
    cwd="/Users/you/project/backend"
)
```

**Use cases:**
- Monorepos (run from specific subdirectory)
- Relative imports
- Config file discovery

### 4. **Enhanced Session Info** 📊

Get comprehensive information about the debug session:

```python
{
    "session_id": "abc123",
    "status": "running",
    "module": "uvicorn",  # or "file": "path/to/file.py"
    "configuration": "Otter Debug Session",
    "breakpoints": [...],
    "output": "...",  # stdout/stderr (when available)
    "pid": 12345,  # process ID
    "launch_args": ["app:main", "--port", "8000"],
    "launch_env": {"DEBUG": "true"},
    "launch_cwd": "/path/to/project"
}
```

### 5. **Advanced Debug Options** ⚙️

Fine-tune debugging behavior:

```python
start_debug_session(
    file="src/main.py",
    stop_on_entry=True,  # Pause at first line
    just_my_code=False   # Debug into libraries too
)
```

## Complete API Reference

### `start_debug_session`

```python
start_debug_session(
    file: str | None = None,           # File to debug (XOR with module)
    module: str | None = None,          # Module to debug (XOR with file)
    configuration: str | None = None,   # Named configuration
    breakpoints: List[int] | None = None,  # Line numbers for breakpoints
    args: List[str] | None = None,      # Command-line arguments
    env: Dict[str, str] | None = None,  # Environment variables
    cwd: str | None = None,             # Working directory
    stop_on_entry: bool = False,        # Stop at first line
    just_my_code: bool = True           # Skip library code
) -> DebugSession
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `file` | `str \| None` | Path to Python file to debug. Mutually exclusive with `module`. |
| `module` | `str \| None` | Module name (e.g., "uvicorn"). Mutually exclusive with `file`. |
| `configuration` | `str \| None` | Named debug configuration. Optional. |
| `breakpoints` | `List[int] \| None` | Line numbers for breakpoints. Requires `file`. |
| `args` | `List[str] \| None` | Command-line arguments for the program. |
| `env` | `Dict[str, str] \| None` | Environment variables to set. |
| `cwd` | `str \| None` | Working directory. Defaults to project root. |
| `stop_on_entry` | `bool` | If True, pause at the first line of code. Default: False. |
| `just_my_code` | `bool` | If True, skip debugging library code. Default: True. |

**Returns:** `DebugSession` object with session details.

**Raises:**
- `ValueError`: If both `file` and `module` are provided, or neither is provided.
- `RuntimeError`: If Neovim client unavailable or debugging fails.

## Real-World Examples

### Example 1: Debug Uvicorn Server

```python
# Start uvicorn with Doppler environment
session = await start_debug_session(
    module="uvicorn",
    args=[
        "fern_mono.main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--reload"
    ],
    env={"DOPPLER_ENV": "1"}
)

print(f"Server running with PID: {session.pid}")
print(f"Working directory: {session.launch_cwd}")

# Now you can send requests to http://127.0.0.1:8000
# Breakpoints in your code will be hit automatically
```

### Example 2: Debug Pytest with Custom Environment

```python
# Debug specific test with database URL
session = await start_debug_session(
    module="pytest",
    args=["tests/test_database.py::test_user_creation", "-v", "-s"],
    env={
        "DATABASE_URL": "postgresql://localhost/test_db",
        "TEST_MODE": "1"
    },
    cwd="/Users/you/project"
)

# Wait for breakpoint
await control_execution("continue")

# Inspect variables when hit
state = await inspect_state()
print(state.variables)
```

### Example 3: Debug Flask App with Hot Reload

```python
session = await start_debug_session(
    module="flask",
    args=["run", "--debug", "--port", "5000"],
    env={
        "FLASK_APP": "app.py",
        "FLASK_ENV": "development"
    },
    stop_on_entry=False
)

# Server is now running and debuggable
# Make requests to trigger breakpoints
```

### Example 4: Debug Script with Breakpoints

```python
# Traditional file debugging with breakpoints
session = await start_debug_session(
    file="scripts/data_migration.py",
    breakpoints=[34, 40, 41],  # Pause at these lines
    args=["--dry-run"],
    env={"DATABASE_URL": "postgresql://localhost/prod"}
)

# Execution will stop at line 34
# Step through with control_execution
```

### Example 5: Debug Django Management Command

```python
session = await start_debug_session(
    file="manage.py",
    args=["runserver", "0.0.0.0:8000"],
    env={
        "DJANGO_SETTINGS_MODULE": "myproject.settings.dev",
        "DEBUG": "True"
    }
)
```

### Example 6: Debug from Monorepo Subdirectory

```python
# Debug backend code from monorepo
session = await start_debug_session(
    file="src/api/main.py",
    cwd="/Users/you/monorepo/backend",  # Run from backend dir
    env={"CONFIG_PATH": "../shared/config.yml"}
)
```

## Comparison with Old API

### Before (Limited)

```python
# Could only debug files, no environment/module support
start_debug_session(
    file="src/main.py",
    args=["--port", "8000"]  # ❌ Can't launch modules
                             # ❌ Can't set env vars
                             # ❌ Can't control cwd
)
```

### After (Powerful)

```python
# Can debug modules with full environment control
start_debug_session(
    module="uvicorn",  # ✅ Module launching
    args=["app:main", "--port", "8000"],
    env={"DOPPLER_ENV": "1"},  # ✅ Environment variables
    cwd="/path/to/project"  # ✅ Working directory
)
```

## How It Works

### Architecture

```
User/Agent
    ↓
MCP Tool (start_debug_session)
    ↓
IDE Server (CliIdeServer)
    ↓
Debug Service
    ↓
Neovim Client (DAP)
    ↓
nvim-dap (Lua)
    ↓
debugpy / Debug Adapter
    ↓
Your Application
```

### Under the Hood

1. **Python Layer**: Validates parameters, resolves paths
2. **Lua Layer**: Builds DAP configuration dynamically
3. **DAP Protocol**: Communicates with language-specific debug adapter
4. **Process Spawn**: Adapter launches your application with specified environment

The Lua configuration generated looks like:

```lua
{
    type = "python",
    request = "launch",
    name = "Otter Debug Session",
    module = "uvicorn",  -- or program = "/path/to/file.py"
    args = {"app:main", "--port", "8000"},
    env = {DOPPLER_ENV = "1"},
    cwd = "/path/to/project",
    stopOnEntry = false,
    justMyCode = true,
    console = "integratedTerminal"
}
```

## Debugging the Debugger 🔍

If debugging doesn't work:

### Check 1: Is debugpy installed?

```bash
python -m pip install debugpy
python -c "import debugpy; print(debugpy.__version__)"
```

### Check 2: Can the module be found?

```bash
# For module launching
python -m uvicorn --help  # Should work

# For file debugging
python path/to/file.py  # Should work
```

### Check 3: Are environment variables needed?

Some apps require specific env vars to start. Add them to the `env` parameter.

### Check 4: Is the working directory correct?

Relative imports and file paths depend on `cwd`. Ensure it's set correctly.

## Limitations & Future Work

### Current Limitations

1. **Output Capture**: Limited real-time stdout/stderr capture
   - DAP protocol supports this via events
   - Would require event listener in Neovim client
   - **Workaround**: Check application logs or use `console="integratedTerminal"`

2. **Attach Mode**: Only `launch` mode currently supported
   - Can't attach to already-running processes
   - **Future**: Add `attach_debug_session()` tool

3. **Multi-target**: Single debug session at a time
   - **Future**: Support debugging multiple processes

### Planned Enhancements

- [ ] Real-time output streaming via DAP events
- [ ] Attach to running process support
- [ ] Multi-session debugging
- [ ] Remote debugging (debug on different machine)
- [ ] Conditional breakpoints via DAP protocol
- [ ] Logpoints (print without stopping)

## Best Practices

### 1. Use Module Launching for Apps

**Good:**
```python
start_debug_session(
    module="uvicorn",
    args=["app:main"]
)
```

**Less Good:**
```python
# Harder to configure, less idiomatic
start_debug_session(
    file="/path/to/venv/bin/uvicorn",
    args=["app:main"]
)
```

### 2. Always Specify Env Vars

If your app needs env vars to run, pass them explicitly:

```python
start_debug_session(
    module="myapp",
    env={
        "DATABASE_URL": "...",
        "API_KEY": "...",
        # Don't rely on shell environment
    }
)
```

### 3. Set Working Directory for Monorepos

```python
start_debug_session(
    file="src/main.py",
    cwd="/path/to/monorepo/backend"  # Ensures imports resolve correctly
)
```

### 4. Use just_my_code=True (Default)

Skip debugging into library code unless investigating library bugs:

```python
start_debug_session(
    module="myapp",
    just_my_code=True  # Default, skip stdlib/site-packages
)
```

### 5. stop_on_entry for Initial Setup

If you need to inspect state before any code runs:

```python
start_debug_session(
    module="myapp",
    stop_on_entry=True  # Pause at first line
)
```

## Language Support

Currently supported languages:

| Language | Module Support | Env Support | Status |
|----------|---------------|-------------|--------|
| **Python** | ✅ Yes (`python -m`) | ✅ Yes | **Fully Supported** |
| JavaScript/TypeScript | ⚠️ Partial | ✅ Yes | Partial (needs testing) |
| Rust | ❌ N/A (cargo) | ✅ Yes | Basic support |
| Go | ❌ N/A | ✅ Yes | Basic support |

### Python (debugpy)

Fully supported. Module launching, env vars, cwd all working.

### JavaScript/TypeScript (node-debug2)

Basic support. Module launching via node:
```python
start_debug_session(
    file="index.js",  # Node doesn't have -m flag
    args=["--experimental-modules"],
    env={"NODE_ENV": "development"}
)
```

### Other Languages

Environment variables and working directory work for all languages.
Module launching is Python-specific (other languages use different mechanisms).

## Migration Guide

### Migrating Existing Debug Calls

**Old code:**
```python
await start_debug_session(
    file="src/server.py",
    args=["--port", "8000"]
)
```

**New code (file-based):**
```python
# Still works! Backward compatible
await start_debug_session(
    file="src/server.py",
    args=["--port", "8000"]
)
```

**New code (module-based):**
```python
# Better: use module launching
await start_debug_session(
    module="uvicorn",
    args=["myapp.server:app", "--port", "8000"],
    env={"DEBUG": "1"}  # Now you can add env vars!
)
```

### No Breaking Changes

All existing debug calls continue to work. New parameters are optional.

## Summary

The enhanced debug tools provide:

✅ **Module launching** - Debug servers, frameworks, any `python -m` app  
✅ **Environment control** - Pass env vars for configuration  
✅ **Working directory** - Debug monorepos and complex setups  
✅ **Rich session info** - PID, output, launch details  
✅ **Advanced options** - stop_on_entry, just_my_code  
✅ **Backward compatible** - Existing code still works  
✅ **Production-ready** - Tested with uvicorn, pytest, flask, django  

This makes Otter's debugger suitable for real-world development workflows, not just simple script debugging.

