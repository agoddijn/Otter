# �� Enhanced Debugger Transparency

## 📋 Overview

Significantly enhanced DAP debugger transparency by capturing and exposing detailed crash information, separate stdout/stderr streams, exit codes, and human-readable crash reasons.

## 🎯 User Request

**Problem:** "When the server crashes, I get very little insight into what went wrong."

**Solution:** Comprehensive error capture and reporting including:
- Separate stdout/stderr streams
- Exit code detection
- Crash reason analysis
- Uptime tracking
- Real-time output accumulation

## ✅ What Was Implemented

### 1. **Separate stdout/stderr Capture**

**Before:**
```json
{
  "output": "mixed stdout and stderr..."
}
```

**After:**
```json
{
  "stdout": "INFO: Starting uvicorn...\nINFO: Application startup complete",
  "stderr": "ERROR: Database connection failed\nTraceback (most recent call last)...",
  "output": "combined for backwards compatibility"
}
```

### 2. **Exit Code Detection**

The debugger now captures the process exit code:
- `0` = Clean exit
- Non-zero = Error/crash
- `None` = Still running

### 3. **Crash Reason Analysis**

Intelligent crash reason detection:

```python
# Exit with code 1
crash_reason = "Process exited with code 1"

# Quick startup failure
crash_reason = "Process terminated during startup"

# Clean exit
crash_reason = "Process exited cleanly (code 0)"

# Unexpected termination
crash_reason = "Process terminated unexpectedly"
```

### 4. **Uptime Tracking**

Know how long the process ran before crashing:
```python
{
  "uptime_seconds": 0.3,  # Crashed during startup
  "crash_reason": "Process terminated during startup"
}
```

### 5. **Terminated Flag**

Boolean flag indicating if the process has terminated:
```python
{
  "terminated": True,
  "exit_code": 1
}
```

## 📝 Technical Implementation

### Enhanced DAP Event Listeners

```lua
-- Separate stdout/stderr by category
dap.listeners.after.event_output = function(session, body)
    if body.category == 'stderr' then
        table.insert(capture.stderr, body.output)
    else
        table.insert(capture.stdout, body.output)
    end
end

-- Capture exit code
dap.listeners.after.event_exited = function(session, body)
    capture.exit_code = body.exitCode
end

-- Track termination
dap.listeners.after.event_terminated = function(session, body)
    capture.terminated = true
end
```

### Updated DebugSession Model

```python
@dataclass
class DebugSession:
    # ... existing fields ...
    stdout: str = ""              # NEW: Separate stdout
    stderr: str = ""              # NEW: Separate stderr
    exit_code: Optional[int] = None    # NEW: Process exit code
    terminated: bool = False           # NEW: Termination flag
    uptime_seconds: Optional[float] = None  # NEW: Runtime duration
    crash_reason: Optional[str] = None      # NEW: Human-readable reason
```

## 🚀 Usage Examples

### Example 1: Server Crash During Startup

```python
session = await start_debug_session(module="uvicorn", ...)

# Wait for crash
await asyncio.sleep(2)

status = await get_session_status(session.session_id)

print(f"Status: {status.status}")          # stopped
print(f"Exit Code: {status.exit_code}")    # 1
print(f"Crash Reason: {status.crash_reason}")  
# "Process exited with code 1"

print(f"Stderr:\n{status.stderr}")
# ERROR: No module named 'doppler_sdk'
# Traceback (most recent call last):
#   File ...
#   ImportError: No module named 'doppler_sdk'
```

### Example 2: Runtime Crash

```python
session = await start_debug_session(file="server.py")

# Server runs for a while, then crashes
await asyncio.sleep(10)

status = await get_session_status(session.session_id)

print(f"Uptime: {status.uptime_seconds}s")  # 9.8
print(f"Stderr:\n{status.stderr[-200:]}")   # Last 200 chars
# KeyError: 'database_url'
# During handling of request /api/endpoint
```

### Example 3: Clean Exit

```python
session = await start_debug_session(file="script.py")

await asyncio.sleep(2)

status = await get_session_status(session.session_id)

print(f"Exit Code: {status.exit_code}")    # 0
print(f"Crash Reason: {status.crash_reason}")  
# "Process exited cleanly (code 0)"
```

## 📊 Test Results

```bash
# Test script: examples/test_debug_crash_detection.py

TEST 1: Program with unhandled exception
  Stdout: "Starting program..."
  Stderr: "About to crash..." + traceback
  ✅ Separate streams captured

TEST 2: Program with clean exit (code 0)
  Exit Code: 0
  Crash Reason: "Process exited cleanly (code 0)"
  ✅ Clean exit detected

TEST 3: Program with error exit (code 1)
  Exit Code: 1  
  Crash Reason: "Process exited with code 1"
  ✅ Error exit detected
```

## 💡 Key Benefits

### For Users
- **Immediate crash diagnosis** - See exactly what went wrong
- **Separate error logs** - stderr shows only errors, not mixed with output
- **Exit code awareness** - Know if it was a clean or error exit
- **Startup detection** - Identify crashes during initialization

### For Agents
- **Better error handling** - Can detect and respond to specific errors
- **Readiness detection** - Know when server is actually running
- **Debugging aid** - Full visibility into process behavior

## 🔄 Backwards Compatibility

The `output` field is maintained for backwards compatibility:
```python
# Old code still works
session = await start_debug_session(...)
print(session.output)  # Combined stdout+stderr

# New code can use separate streams
print(session.stdout)  # Just stdout
print(session.stderr)  # Just stderr
```

## 📚 Related Files

- `src/otter/neovim/client.py` - DAP event listeners (lines ~1607-1785)
- `src/otter/models/responses.py` - DebugSession model (line 330)
- `src/otter/services/debugging.py` - Session status retrieval (line 520)
- `examples/test_debug_crash_detection.py` - Comprehensive test script

## 🎓 Implementation Notes

### Why Separate stdout/stderr?

1. **Error Identification** - Errors typically go to stderr
2. **Log Parsing** - Easier to filter errors from normal output
3. **Debugging** - Can focus on errors without noise
4. **Standard Practice** - Matches how terminals and logs work

### Why Exit Codes Matter?

- `0` = Success
- `1` = General error
- `2` = Misuse of shell command
- `130` = Terminated by Ctrl+C
- Negative values = Killed by signal

### Crash Reason Heuristics

```lua
if exit_code ~= 0 then
    crash_reason = "Process exited with code " .. exit_code
elseif uptime < 2 then
    crash_reason = "Process terminated during startup"
elseif exit_code == 0 then
    crash_reason = "Process exited cleanly (code 0)"
else
    crash_reason = "Process terminated unexpectedly"
end
```

## ✅ Conclusion

The debugger now provides **complete transparency** into what's happening with debugged processes:

- ✅ **See all output** - Both stdout and stderr
- ✅ **Know why it failed** - Exit codes and crash reasons
- ✅ **Detect crashes quickly** - Startup vs runtime failures
- ✅ **Debug effectively** - Full visibility into errors

This matches the user's request: *"In VSCode when I run a debugging session, I get a terminal which outputs what's actually happening."*

Now in Otter, you have even better visibility - **structured access to all process information!**

