# Debug Session Tracking Architecture

## Overview

Otter's debug session tracking system provides robust, persistent session data that survives process termination, enabling comprehensive crash analysis and diagnostics.

## Design Principles

### 1. **Python as Source of Truth**
- Python (`DebugService`) generates session IDs using UUID
- Lua stores data keyed by these IDs in `_G.otter_session_registry`
- Direct lookup by user-provided ID (no searching)

### 2. **Unified Session Registry**
```lua
_G.otter_session_registry = {
  ["uuid-1234"] = {
    pid = 12345,
    stdout = {"line1", "line2"},
    stderr = {"error1"},
    exit_code = 1,
    terminated = true,
    start_time = 1696348800,
    nvim_session_id = "42"  -- Cross-reference to nvim-dap
  }
}
```

### 3. **Smart Retention Policy**
Session data persists after termination, with duration based on exit status:

| Exit Type | Retention | Rationale |
|-----------|-----------|-----------|
| **Crash** (exit code ≠ 0) | 5 minutes | Need time to diagnose errors |
| **Clean exit** (exit code = 0) | 30 seconds | Less important, prevent memory accumulation |
| **Active session** | ∞ | Never cleaned up while running |

## Architecture

### Session Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Python generates UUID                                    │
│    session_id = str(uuid4())                                │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Lua creates registry entry                               │
│    _G.otter_session_registry[session_id] = { ... }          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. DAP event listeners accumulate data                      │
│    • event_process → captures PID                           │
│    • event_output → accumulates stdout/stderr               │
│    • event_exited → captures exit code                      │
│    • event_terminated → triggers cleanup                    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. On termination: Smart retention                          │
│    if exit_code ≠ 0:   keep for 5 minutes                   │
│    else:               keep for 30 seconds                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Cleanup after retention period                           │
│    _G.otter_session_registry[session_id] = nil              │
└─────────────────────────────────────────────────────────────┘
```

### Session Status Determination

When querying a session, status is determined by:

```lua
if active_session and session_data.nvim_session_id == tostring(active_session.id) then
    if active_session.stopped_thread_id then
        return "paused"
    else
        return "running"
    end
elseif session_data.terminated then
    return "terminated"
elseif session_data.exit_code ~= nil then
    return "exited"
else
    return "no_session"
end
```

## Comparison to Other Tools

| Feature | nvim-dap | VSCode | JetBrains | **Otter** |
|---------|----------|--------|-----------|-----------|
| **Post-termination persistence** | ❌ None | ✅ Manual (UI tabs) | ✅ Manual (UI tabs) | ✅ Automatic (timed) |
| **Crash data retention** | ❌ Immediate cleanup | ✅ Until tab closed | ✅ Until tab closed | ✅ 5 minutes |
| **Memory management** | ✅ Immediate | ❌ Manual cleanup | ❌ Manual cleanup | ✅ Automatic |
| **Programmatic access** | ❌ No | ❌ UI-driven | ❌ UI-driven | ✅ Yes |
| **Cross-session tracking** | ❌ No | ❌ No | ❌ No | ✅ UUID-based |

**Key Insight**: Traditional IDEs rely on **UI-driven manual cleanup** (closing debug console tabs). Otter needs **automatic time-based cleanup** since it's headless and programmatically accessed.

## API Usage

### Starting a Session
```python
# Python generates the session ID
session = await debug_service.start_debug_session(
    file="app.py"
)
# session.session_id is now the permanent identifier
```

### Querying Session Status
```python
# Works for active, paused, or terminated sessions
status = await debug_service.get_session_status(session.session_id)

# Available data:
print(status.status)         # "running" | "paused" | "terminated" | "no_session"
print(status.pid)            # Process ID
print(status.stdout)         # Standard output
print(status.stderr)         # Standard error (separate!)
print(status.exit_code)      # Exit code (if terminated)
print(status.crash_reason)   # Human-readable reason
print(status.uptime_seconds) # How long it ran
```

### Handling Crashes
```python
# Start a server
session = await debug_service.start_debug_session(
    module="uvicorn",
    args=["app:app"]
)

# Server crashes immediately...
await asyncio.sleep(1)

# Crash data is preserved for 5 minutes!
status = await debug_service.get_session_status(session.session_id)

if status.status == "terminated" and status.exit_code != 0:
    print(f"🚨 Crash detected: {status.crash_reason}")
    print(f"📝 Error output:\n{status.stderr}")
    print(f"⏱️  Crashed after {status.uptime_seconds}s")
    
    # Crash data remains available for diagnosis
    # No need to rush - you have 5 minutes
```

## Benefits

### For Agents
1. **Asynchronous diagnosis**: Query crash info at your own pace
2. **Complete context**: Full stdout/stderr, exit codes, timing
3. **No data loss**: Crashes don't lose diagnostic information

### For Memory Management
1. **Automatic cleanup**: No manual intervention needed
2. **Smart retention**: Crashes kept longer than successes
3. **Bounded memory**: Sessions are guaranteed to be cleaned up

### For Debugging
1. **Persistent state**: Query sessions multiple times
2. **Cross-reference**: Map between user IDs and nvim IDs
3. **Timeline tracking**: Start time, uptime, termination time

## Implementation Files

| File | Purpose |
|------|---------|
| `src/otter/neovim/client.py` | Lua session registry, event listeners |
| `src/otter/services/debugging.py` | Python session tracking, UUID generation |
| `src/otter/models/responses.py` | `DebugSession` dataclass with all fields |

## Testing

Run the comprehensive tests:
```bash
# Test smart retention policy
python examples/test_smart_retention.py

# Test crash detection
python examples/test_debug_crash_detection.py

# Test output capture
pytest tests/integration/test_dap_output_capture.py -v
```

## Future Enhancements

Potential improvements:

1. **Configurable retention**: Allow per-project customization
2. **Session history API**: List all recent sessions
3. **Size-based eviction**: Limit total number of cached sessions
4. **Explicit cleanup**: Manual cleanup for specific sessions
5. **Export crash reports**: Save crash data to files

## Conclusion

Otter's session tracking architecture provides **IDE-like persistence** without **UI dependencies**, making it ideal for programmatic debugging and agent-driven workflows. The smart retention policy ensures crash diagnostics remain available while preventing memory leaks.

