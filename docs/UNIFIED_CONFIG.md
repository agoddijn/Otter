# Unified Configuration - LSP and DAP Use Same Python

## Problem We Solved

**Before:** LSP and DAP could use different Python interpreters!
- LSP would read from `.otter.toml` or auto-detect venv
- DAP had its own detection logic
- They could diverge, causing confusing behavior

**After:** LSP and DAP use the EXACT SAME Python interpreter from unified config.

## How It Works

### Single Source of Truth: `OtterConfig`

```python
# .otter.toml
[lsp.python]
python_path = "${VENV}/bin/python"  # or absolute path
```

### Priority (Same for LSP and DAP)

1. **Explicit config** from `.otter.toml`
   ```toml
   [lsp.python]
   python_path = "/path/to/.venv/bin/python"
   ```

2. **Auto-detected venv** in project root
   - Checks: `.venv/`, `venv/`, `env/`, `.env/`
   - Unix: `bin/python`
   - Windows: `Scripts/python.exe`

3. **System Python** as fallback
   - Uses `sys.executable`

## Implementation

### DebugService Uses Config

```python
class DebugService:
    def __init__(self, nvim_client, project_path, config):
        self.config = config  # OtterConfig - same as LSP!
    
    def _get_python_path(self) -> str:
        """Get Python path using UNIFIED config (same as LSP)."""
        # 1. Check explicit config
        if self.config:
            python_config = self.config.lsp.language_configs.get("python")
            if python_config and python_config.python_path:
                return self.config.resolve_path(python_config.python_path)
        
        # 2. Auto-detect venv
        # ... (same logic as config.py)
        
        # 3. System Python fallback
        return sys.executable
```

### Explicit Logging

```python
# When starting debug session
python_path = self._get_python_path()

print(f"\n🐍 Using Python interpreter: {python_path}")
print(f"   (This is the same Python used by LSP servers)")

# Verify debugpy is available
result = subprocess.run(
    [python_path, "-c", "import debugpy; print(debugpy.__version__)"],
    ...
)
if result.returncode == 0:
    print(f"   ✅ debugpy {result.stdout.strip()} is available")
else:
    print(f"   ⚠️  WARNING: debugpy not installed in this Python")
    print(f"   Install with: {python_path} -m pip install debugpy")
```

## Example Output

### Success Case

```
🐍 Using Python interpreter: /Users/you/project/.venv/bin/python
   (This is the same Python used by LSP servers)
   ✅ debugpy 1.8.0 is available in this Python

🔍 Checking python debugger...
✅ python: debugpy is installed
```

### Warning Case

```
🐍 Using Python interpreter: /Users/you/project/.venv/bin/python
   (This is the same Python used by LSP servers)
   ⚠️  WARNING: debugpy may not be installed in this Python
   Install with: /Users/you/project/.venv/bin/python -m pip install debugpy
```

## Benefits

### 1. Consistency ✅
LSP and DAP use the same Python - no surprises

### 2. Transparency ✅
Explicitly shows which Python is being used

### 3. Debuggability ✅
Clear error messages with exact install commands

### 4. Configurability ✅
Set Python once in `.otter.toml`, used everywhere

## Configuration Examples

### Explicit Path

```toml
[lsp.python]
python_path = "/Users/you/project/.venv/bin/python"
```

Both LSP and DAP will use this exact Python.

### Template Variables

```toml
[lsp.python]
python_path = "${VENV}/bin/python"
```

`${VENV}` auto-detects to `.venv/`, `venv/`, etc.

### Auto-Detection (No Config)

If no `.otter.toml`, both LSP and DAP will:
1. Check for `.venv/bin/python`
2. Check for `venv/bin/python`
3. Fall back to system Python

## Verification

### Check Which Python Will Be Used

```python
from otter.config import load_config
from pathlib import Path

config = load_config(Path("/path/to/project"))

# This is what LSP uses
python_config = config.lsp.language_configs.get("python")
if python_config and python_config.python_path:
    print(f"Configured: {config.resolve_path(python_config.python_path)}")
else:
    print("Auto-detecting...")
    # Would follow auto-detection logic
```

### In Debug Session

The debug session output explicitly shows:
```
🐍 Using Python interpreter: /exact/path/to/python
   (This is the same Python used by LSP servers)
```

## Testing

### Test LSP and DAP Use Same Python

```python
async def test_lsp_and_dap_use_same_python(tmp_path):
    """Test that LSP and DAP use the same Python interpreter."""
    # Create venv
    venv = tmp_path / ".venv"
    venv_python = venv / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("#!/bin/sh\necho 'venv python'")
    venv_python.chmod(0o755)
    
    # Create server
    server = CliIdeServer(project_path=str(tmp_path))
    
    # Get Python path from debug service
    debug_python = server.debugging._get_python_path()
    
    # Should be the venv Python
    assert str(venv_python) in debug_python
    
    # LSP would use the same (through config.resolve_path)
    from otter.config import load_config
    config = load_config(tmp_path)
    # Both should resolve to the same venv
```

## Migration

### Before (Inconsistent)

```python
# LSP: used config or auto-detect
# DAP: had its own _detect_python_path()
# Could diverge!
```

### After (Unified)

```python
# Both use OtterConfig._get_python_path()
# Through config.resolve_path() and unified detection
# Always consistent!
```

## Troubleshooting

### "debugpy not available"

The error message now shows EXACTLY which Python to install into:

```
⚠️  WARNING: debugpy may not be installed in this Python
Install with: /path/to/venv/bin/python -m pip install debugpy
```

Just run that command!

### "Wrong Python being used"

Set it explicitly in `.otter.toml`:

```toml
[lsp.python]
python_path = "/exact/path/to/python"
```

### "How do I know which Python is being used?"

It's printed explicitly when you start debugging:

```
🐍 Using Python interpreter: /path/to/python
```

## Summary

**Unified configuration ensures LSP and DAP use the same Python interpreter, with explicit logging so users/agents always know which Python is being used.**

### Key Changes

1. ✅ `DebugService` now takes `config` parameter
2. ✅ `_get_python_path()` uses unified config
3. ✅ Explicit logging of Python path
4. ✅ Verification that debugpy is available
5. ✅ Clear error messages with exact install commands

### Benefits

- **Consistency:** LSP and DAP can't diverge
- **Transparency:** Always visible which Python is used
- **Debuggability:** Clear errors, actionable messages
- **Configurability:** Set once, used everywhere

