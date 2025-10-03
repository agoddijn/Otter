# DAP Bootstrap - Batteries Included Debugging

## Overview

Just like LSP servers, Otter now auto-installs debug adapters when you try to debug code. No manual setup required!

## What Happens When You Debug

### 1. You Start a Debug Session

```python
await start_debug_session(file="src/main.py")
```

### 2. Otter Checks for Debug Adapter

```
🔍 Checking python debugger...
```

### 3a. If Installed → Start Debugging ✅

```
✅ python: debugpy is installed
[Debug session starts immediately]
```

### 3b. If Missing → Auto-Install ⚙️

```
⚠️  python: Python debugger (debugpy) is not installed

📦 Auto-installing python debugger...
   (This may take a minute)

📦 Installing Python debugger (debugpy)...
   Command: pip install debugpy
✅ Successfully installed debugpy

[Debug session starts]
```

### 3c. If Prerequisites Missing → Clear Instructions 📋

```
⚠️  Cannot install python debugger - missing prerequisites:
   - pip

💡 Install pip:
   curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
   python get-pip.py
```

## Supported Debug Adapters

| Language | Adapter | Auto-Install | Prerequisites |
|----------|---------|--------------|---------------|
| **Python** | debugpy | ✅ Yes | pip |
| **JavaScript** | node-debug2 | ✅ Yes | npm |
| **TypeScript** | node-debug2 | ✅ Yes | npm |
| **Go** | delve | ✅ Yes | go |
| **Rust** | lldb-vscode | ⚠️ Manual | lldb |

### Python (debugpy)

```
✅ Auto-installs with: pip install debugpy
✅ Works out of the box
✅ No configuration needed
```

### JavaScript/TypeScript (node-debug2)

```
✅ Auto-installs with: npm install -g node-debug2
✅ Requires Node.js/npm installed
```

### Go (delve)

```
✅ Auto-installs with: go install github.com/go-delve/delve/cmd/dlv@latest
✅ Requires Go installed
```

### Rust (lldb-vscode)

```
⚠️  Manual install: rustup component add lldb-preview
   (Cannot auto-install due to Rust toolchain integration)
```

## Error Messages

### Clear & Actionable

**Before (confusing):**
```
Error: No debug configuration available for filetype: python
```

**After (helpful):**
```
❌ Debug adapter not available for python.

Error: Cannot install python debugger: missing prerequisites ['pip'].
Please install them first.

💡 This usually means the debug adapter needs to be installed.
   Otter attempted to install it automatically but failed.
   Please check the error above for details.
```

## How It Works

```
User: start_debug_session(file="main.py")
   ↓
Debug Service: What language is this?
   ↓ (detects: python)
   ↓
Bootstrap: Check if debugpy installed
   ↓
   ├─ YES → Continue ✅
   │
   └─ NO → Auto-install
        ↓
        ├─ Prerequisites OK → pip install debugpy ✅
        │
        └─ Prerequisites Missing → Error with instructions 📋
```

## Configuration

### Auto-Install Enabled by Default

```python
# Works automatically - no config needed!
await start_debug_session(file="src/main.py")
```

### Disable Auto-Install (if needed)

You can disable auto-install in `.otter.toml`:

```toml
[dap]
auto_install = false  # Require manual installation
```

Then Otter will error with install instructions instead of auto-installing.

## Comparison with LSP

| Feature | LSP Bootstrap | DAP Bootstrap |
|---------|---------------|---------------|
| Auto-detect needed | ✅ Yes | ✅ Yes |
| Auto-install | ✅ Yes | ✅ Yes |
| Prerequisites check | ✅ Yes | ✅ Yes |
| Clear error messages | ✅ Yes | ✅ Yes |
| Works out of box | ✅ Yes | ✅ Yes |

**Consistent experience across all Otter features!**

## Troubleshooting

### "pip not found"

```bash
# Install pip
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py
```

### "npm not found"

```bash
# Install Node.js (includes npm)
# Visit: https://nodejs.org/
```

### "go not found"

```bash
# Install Go
# Visit: https://golang.org/dl/
```

### Manual Installation

If auto-install fails, you can install manually:

```bash
# Python
pip install debugpy

# JavaScript/TypeScript
npm install -g node-debug2

# Go
go install github.com/go-delve/delve/cmd/dlv@latest

# Rust
rustup component add lldb-preview
```

## Testing the Bootstrap

### Check Adapter Status

```python
from otter.bootstrap import check_dap_adapter, DAPAdapterStatus

status = check_dap_adapter("python")
if status == DAPAdapterStatus.INSTALLED:
    print("✅ Python debugger ready!")
elif status == DAPAdapterStatus.MISSING:
    print("⚠️  Python debugger not installed")
elif status == DAPAdapterStatus.PREREQUISITES_MISSING:
    print("❌ Prerequisites missing (e.g., pip)")
```

### Manual Install

```python
from otter.bootstrap import check_and_install_dap_adapter

status, error = await check_and_install_dap_adapter(
    "python",
    auto_install=True
)

if status == DAPAdapterStatus.INSTALLED:
    print("✅ Ready to debug!")
else:
    print(f"❌ {error}")
```

## Benefits

### 1. Zero Setup Required

**Before:**
```bash
# User had to know and run:
pip install debugpy
# Then configure Neovim DAP manually
```

**After:**
```python
# Just works!
await start_debug_session(file="main.py")
```

### 2. Consistent with LSP

Users already expect auto-install from LSP servers. Now debugging has the same experience.

### 3. Clear Error Messages

When something goes wrong, users know exactly what to do.

### 4. Cross-Platform

Works on macOS, Linux, Windows (anywhere Python/pip works).

## Implementation

### Files

- `src/otter/bootstrap/dap_installer.py` - DAP bootstrap logic
- `src/otter/bootstrap/__init__.py` - Exports DAP functions
- `src/otter/services/debugging.py` - Integrates bootstrap into debug service

### Key Functions

```python
# Check if adapter is installed
check_dap_adapter(language: str) -> DAPAdapterStatus

# Check and install if missing
check_and_install_dap_adapter(
    language: str,
    auto_install: bool = True
) -> tuple[DAPAdapterStatus, Optional[str]]

# Ensure adapter available (raises if not)
ensure_dap_adapter(
    language: str,
    auto_install: bool = True
) -> None
```

## Future Enhancements

- [ ] Cache adapter status (avoid repeated checks)
- [ ] Progress bars for long installations
- [ ] Parallel adapter installation (when debugging multiple languages)
- [ ] Custom adapter paths in config
- [ ] Adapter version management

## Summary

**DAP Bootstrap makes debugging "batteries included"** - just like LSP servers, debug adapters now auto-install when needed. Users can start debugging immediately without manual setup, and error messages clearly explain any issues.

This creates a consistent, user-friendly experience across all of Otter's language-agnostic features.

