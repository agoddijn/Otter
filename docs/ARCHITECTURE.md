# Architecture

This document describes the high-level architecture and design decisions behind Otter.

## Overview

Otter is a **headless IDE server** that exposes LSP and DAP capabilities through the Model Context Protocol (MCP). It provides AI agents with semantic code intelligence without requiring GUI-based IDEs.

### Core Principles

1. **LSP & DAP First** - Leverage mature tooling, don't reimplement
2. **No Shell Duplication** - Don't reimplement `grep`, `git`, or shell commands
3. **Type-Safe Design** - Comprehensive type hints, mypy strict mode
4. **Service-Oriented** - Clear separation between concerns
5. **Async-First** - Non-blocking I/O for concurrent operations
6. **Language-Agnostic** - Protocol-based, zero per-language code

## System Architecture

### High-Level Layers

```
┌───────────────────────────────────────────────────────────┐
│                    MCP Server Layer                       │
│  - FastMCP framework                                       │
│  - Tool definitions (15 tools)                             │
│  - Request/response serialization                          │
└─────────────────────────────┬─────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────┐
│                 CliIdeServer (Facade)                     │
│  - Coordinates services                                    │
│  - Manages Neovim lifecycle                                │
│  - Validates inputs                                        │
│  - Session management                                      │
└────┬──────────┬──────────┬──────────┬─────────────────────┘
     │          │          │          │
┌────▼────┐ ┌──▼──────┐ ┌─▼─────┐ ┌─▼────────┐
│Workspace│ │Navigation│ │Analysis│ │Debugging │
│Service  │ │Service   │ │Service │ │Service   │
│         │ │          │ │        │ │          │
└────┬────┘ └──┬───────┘ └─┬──────┘ └────┬─────┘
     │         │            │             │
     └─────────┴────────────┴─────────────┘
                           │
              ┌────────────▼──────────────┐
              │   Neovim Client (RPC)     │
              │  - Process management     │
              │  - Buffer operations      │
              │  - LSP integration        │
              │  - DAP integration        │
              │  - Lua execution          │
              │  - Async coordination     │
              └────────────┬──────────────┘
                           │
              ┌────────────▼──────────────┐
              │  Neovim Instance          │
              │  (Headless)               │
              │  - LSP Servers            │
              │  - DAP Adapters           │
              │  - TreeSitter Parsers     │
              │  - Lua Runtime            │
              └───────────────────────────┘
```

### Component Responsibilities

**MCP Server Layer**
- Exposes 15 tools via Model Context Protocol
- Handles tool call routing and response serialization
- Protocol-level concerns only

**CliIdeServer (Facade)**
- Single entry point for all operations
- Coordinates between services
- Manages Neovim process lifecycle
- Validates inputs and normalizes paths

**Service Layer**
- **WorkspaceService**: File operations, session management
- **NavigationService**: Definitions, references, symbols
- **AnalysisService**: Diagnostics, dependencies, completions
- **DebuggingService**: Breakpoints, execution control, inspection

**Neovim Client**
- Wraps pynvim for async operations
- Manages LSP and DAP communication
- Handles buffer operations
- Executes Lua code for LSP/DAP access

**Neovim Instance**
- Headless editor process
- Runs LSP servers and DAP adapters
- Provides TreeSitter parsing
- Lua runtime for extensibility

## Key Design Decisions

### 1. Neovim as IDE Engine

**Decision**: Use headless Neovim instead of implementing LSP/DAP from scratch

**Rationale**:
- ✅ Mature LSP client implementation
- ✅ DAP support via nvim-dap plugin
- ✅ TreeSitter for 40+ languages
- ✅ No language-specific code needed
- ✅ Battle-tested in production

**Trade-offs**:
- ⚠️ External dependency (Neovim required)
- ⚠️ ~500ms startup overhead
- ✅ Worth it for robust foundation

**Outcome**: Excellent - Saves thousands of lines of protocol code

### 2. MCP-Native Design

**Decision**: Build for MCP from the ground up, not as an afterthought

**Rationale**:
- Clean tool definitions
- No adapter layers needed
- Agent-optimized responses
- Standard protocol

**Outcome**: Natural fit for agent consumption

### 3. Service Layer Pattern

**Decision**: Separate concerns into focused services

**Benefits**:
- Clear boundaries and responsibilities
- Easy to extend with new capabilities
- Simple to test in isolation
- No cross-service dependencies

**Services**:
```
WorkspaceService  → File operations, metadata
NavigationService → LSP-powered navigation
AnalysisService   → LSP-powered intelligence
DebuggingService  → DAP-powered debugging
```

### 4. Type-Safe Architecture

**Decision**: Strict typing with mypy, dataclass responses

**Benefits**:
- Zero type errors at runtime
- Self-documenting interfaces
- IDE autocomplete support
- Catches bugs at development time

**Implementation**:
```python
@dataclass
class Definition:
    file: str
    line: int
    column: int
    symbol_type: str
    signature: str
```

### 5. Async-First Design

**Decision**: All I/O operations are async

**Rationale**:
- Neovim RPC is naturally async
- Multiple concurrent operations
- Non-blocking MCP server
- Better resource utilization

**Pattern**:
```python
# All pynvim calls wrapped in executor
await loop.run_in_executor(None, sync_nvim_call)
```

### 6. Integration Testing with Real LSP

**Decision**: Tests use real Neovim + real LSP servers

**Trade-offs**:
- ⚠️ Slower tests (~2 minutes total)
- ✅ Catches real issues mocks can't
- ✅ Multi-language validation
- ✅ High confidence in correctness

**Outcome**: Worth the trade-off for production reliability

## Architecture Patterns

### LSP Integration via Lua

Otter accesses LSP through Lua code execution:

```python
lua_code = f"""
local bufnr = {buffer_number}
local result = vim.lsp.buf_request_sync(
    bufnr,
    'textDocument/definition',
    params,
    2000
)
return result
"""
result = await nvim_client.execute_lua(lua_code)
```

**Why Lua?**
- Direct access to Neovim's LSP client
- No protocol implementation needed
- Language-agnostic by design

### DAP Integration via nvim-dap

Debugging uses the nvim-dap plugin:

```python
lua_code = """
local dap = require('dap')
dap.continue()
return dap.session()
"""
session = await nvim_client.execute_lua(lua_code)
```

**Benefits**:
- Zero DAP protocol code
- Works with any DAP adapter
- Battle-tested implementation
- Easy to add new languages

### Path Resolution

All paths go through centralized utilities:

```python
# Input: relative or absolute
file_path = resolve_workspace_path(path, project_root)

# Output: always absolute
return str(file_path.resolve())
```

**Why?**
- Handles macOS symlinks (`/var` → `/private/var`)
- Consistent behavior across operations
- No path ambiguity for agents

### Index Translation

LSP uses 0-indexed lines/columns, users expect 1-indexed:

```python
# To LSP
lsp_params = {"line": user_line - 1, "character": user_col}

# From LSP
return Definition(line=lsp_result.line + 1)
```

## Performance Characteristics

**Startup Time**: ~500ms (Neovim initialization)
**LSP Requests**: 100-500ms (depends on project size)
**DAP Operations**: 0.5-2s (depends on debugger)
**File I/O**: <10ms (async operations)

**Optimization Strategies**:
- Lazy loading (LSPs start on first file open)
- Connection pooling (reuse Neovim instances)
- Concurrent operations (async-first design)
- Minimal dependencies (lean runtime)

## Scalability Considerations

**Large Projects**:
- Limit concurrent LSP clients (`max_lsp_clients`)
- Explicit language list (avoid auto-detection)
- Lazy loading enabled by default

**Monorepos**:
- Per-language configuration
- Separate runtime detection per directory
- Performance tuning options in config

**Resource Management**:
- Neovim processes cleaned up on exit
- LSP servers shut down gracefully
- DAP sessions properly terminated

## What Otter Doesn't Do

Otter explicitly **does not** reimplement what agents can already do via shell:

- ❌ Text/regex search → Use `rg` or `grep`
- ❌ Running tests → Use `pytest`, `cargo test`, etc.
- ❌ Git operations → Use `git` directly
- ❌ File manipulation → Use standard shell tools
- ❌ Build systems → Use `make`, `cargo`, `npm`, etc.

**Focus**: Semantic code intelligence that shell commands cannot provide.

## Future Considerations

**Planned Features**:
- Safe refactoring tools (rename, extract)
- Code actions (quick fixes)
- More language support (C++, Java, etc.)

**Not Planned**:
- GUI interface (headless by design)
- Shell command wrappers (agents have shells)
- Build system integration (use native tools)

## Success Metrics

**Current Status**:
- ✅ 15 tools implemented
- ✅ 204 tests passing
- ✅ Zero mypy errors (strict mode)
- ✅ 4 languages supported (Python, TypeScript, JavaScript, Rust)
- ✅ Production-ready foundation

**Quality Indicators**:
- Type safety: 100% (strict mypy)
- Test coverage: ~85% (integration + unit)
- Multi-language: 100% (all tests run on all languages)
- Documentation: Comprehensive (6 core docs)

## Conclusion

Otter's architecture prioritizes:
- **Simplicity**: Leverage existing tools, don't reinvent
- **Reliability**: Type-safe, well-tested, integration-focused
- **Agent-First**: MCP-native, structured responses, no GUI
- **Extensibility**: Clean service boundaries, easy to add features

The result is a **production-ready IDE for AI agents** that is maintainable, reliable, and easy to extend.

---

For implementation details, see the code - it's self-documenting by design.
For usage information, see [GETTING_STARTED.md](./GETTING_STARTED.md).
For contribution guidelines, see [CONTRIBUTING.md](./CONTRIBUTING.md).
