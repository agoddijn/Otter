# Architecture

## System Design

```
MCP Server Layer (FastMCP)
    ↓
Server Facade (Orchestration)
    ↓
Service Layer (Navigation, Analysis, Debug, Refactoring)
    ↓
Neovim Client (RPC, LSP, DAP, TreeSitter)
    ↓
Neovim Instance (headless)
    ↓
LSP Servers & DAP Adapters
```

## Core Principles

1. **Wrapper, Not Reimplementer** - Leverage Neovim's ecosystem
2. **Language-Agnostic** - Zero per-language code, protocol-based
3. **Type-Safe** - Mypy strict mode, dataclass responses
4. **Async-First** - Non-blocking operations
5. **Test-Driven** - Integration tests with real LSP/DAP

## Key Design Decisions

### Use Neovim as IDE Engine

**Why**: Mature LSP/DAP/TreeSitter implementations  
**Trade-off**: ~500ms startup overhead  
**Result**: ✅ Excellent - robust code intelligence

### Service Layer Pattern

**Why**: Clean separation of concerns  
**Result**: ✅ Excellent - easy to extend

### Type-Safe Dataclasses

**Why**: Catch bugs early, clear contracts  
**Result**: ✅ Excellent - zero type errors

### Integration Testing

**Why**: Validate against real LSP/DAP  
**Trade-off**: Slower tests (~2 minutes)  
**Result**: ✅ Excellent - high confidence

## Key Learnings

### 1. LSP via Lua Pattern

Use f-strings to embed parameters in Lua code executed by Neovim.

### 2. Path Resolution

Always resolve symlinks before comparison (macOS /var → /private/var).

### 3. Async/Sync Boundary

All pynvim calls need `run_in_executor` for non-blocking operations.

### 4. DAP Integration

Use Neovim's `nvim-dap` plugin instead of implementing DAP protocol.

### 5. Testing Distributed Systems

Use polling with exponential backoff, never fixed delays.

## Status

**13 of 15 tools complete** (87%)

- ✅ Navigation & Intelligence (8 tools)
- ✅ Debugging (5 tools)
- 🚧 Refactoring (2 tools pending)

**Tests**: 204 passing (174 parameterized + 30 debugging)

For implementation details, see the handwritten `docs/ARCHITECTURE.md` in the repository.

