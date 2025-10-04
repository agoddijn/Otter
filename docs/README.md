# What is Otter?

Otter is a **batteries-included, agent-first IDE** exposed over the Model Context Protocol (MCP). It provides AI agents with comprehensive code understanding, navigation, and debugging capabilities - without requiring heavy GUI-based IDEs.

## Philosophy

### Built for Agents, Not Humans

Otter is designed from the ground up for **AI agents** that need to understand, write, and debug code. Unlike traditional IDEs built for human interaction, Otter provides:

- **Ergonomic MCP interface**: All capabilities exposed as simple tool calls
- **No GUI overhead**: Lightweight, headless architecture
- **Semantic understanding**: LSP and TreeSitter-powered intelligence
- **Drop-in anywhere**: Works in any environment with Neovim

### Batteries Included

Otter handles the complexity so agents don't have to:

- **Auto-bootstrapping**: Automatically installs missing LSP servers and debug adapters
- **Runtime detection**: Finds virtual environments, Node versions, Rust toolchains automatically
- **Multi-language**: Python, TypeScript, JavaScript, Rust, Go - more languages coming
- **Zero configuration**: Works out of the box, configure only when needed

### Focus on What Matters

Otter **does not** reimplement what agents can already do via shell:

- ❌ Text search → Agents use `rg` or `grep`
- ❌ Running tests → Agents use `pytest`, `cargo test`, etc.
- ❌ Git operations → Agents use `git` directly
- ❌ File manipulation → Agents use standard shell tools

Otter **does** provide what agents cannot easily access:

- ✅ **LSP intelligence**: Definitions, references, hover info, completions
- ✅ **Code semantics**: Type checking, diagnostics, symbol extraction
- ✅ **Debug capabilities**: Breakpoints, stepping, variable inspection
- ✅ **Safe refactoring**: Rename symbols, extract functions, apply fixes

## Architecture (High-Level)

Otter is built on three core components:

```
┌─────────────────────────────────────────────┐
│         MCP Server (FastMCP)                │
│  - Tool definitions & serialization         │
│  - Standard MCP protocol interface          │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│      CliIdeServer (Orchestration)           │
│  - Session management                       │
│  - Service coordination                     │
│  - Request validation                       │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────▼────────┐   ┌────────▼────────┐
│  LSP Services  │   │  DAP Services   │
│  - Navigation  │   │  - Debugging    │
│  - Analysis    │   │  - Breakpoints  │
│  - Refactoring │   │  - Inspection   │
└───────┬────────┘   └────────┬────────┘
        │                     │
        └──────────┬──────────┘
                   │
┌──────────────────▼──────────────────────────┐
│     Neovim (Headless Instance)              │
│  - LSP client (built-in)                    │
│  - DAP client (nvim-dap plugin)             │
│  - TreeSitter parsers                       │
│  - Lua runtime                              │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  Language Servers & Debug Adapters          │
│  - pyright, tsserver, rust-analyzer, ...    │
│  - debugpy, node-debug2, codelldb, ...      │
└─────────────────────────────────────────────┘
```

### Why Neovim?

Neovim provides mature, battle-tested infrastructure:

- **Built-in LSP client**: No need to implement LSP protocol
- **Plugin ecosystem**: DAP support via nvim-dap
- **TreeSitter**: 40+ languages with incremental parsing
- **Lua runtime**: Programmable, extensible
- **Headless mode**: Perfect for server applications

**Trade-off**: ~500ms startup time, but provides robust foundation for code intelligence.

## Design Principles

### 1. Type-Safe by Default

All responses are strongly-typed dataclasses. Mypy strict mode ensures zero type errors at runtime.

### 2. Service-Oriented Architecture

Clear separation of concerns:
- **WorkspaceService**: File operations, session management
- **NavigationService**: Definitions, references, symbols
- **AnalysisService**: Diagnostics, dependencies, hover info
- **RefactoringService**: Renames, extractions, code actions
- **DebuggingService**: Breakpoints, execution control, inspection

### 3. Async-First

Non-blocking I/O enables concurrent operations. All Neovim RPC calls run in executor pool to prevent blocking the event loop.

### 4. Real Integration Testing

Tests use real Neovim instances with real LSP servers. Slower, but catches real issues that mocks cannot.

## Unique Aspects

### 1. MCP Protocol Integration

Otter is one of the first IDEs designed specifically for the Model Context Protocol. All capabilities are exposed as MCP tools, making it trivial for any MCP client to integrate.

### 2. Auto-Bootstrap Everything

First-time setup is automatic:
- Missing LSP servers? Installed automatically
- Missing debug adapters? Installed automatically
- No virtual environment? Uses system Python with warning
- Missing TreeSitter parsers? Compiled on demand

### 3. Cross-Language by Design

Otter treats all languages equally. The same test suite runs against Python, TypeScript, JavaScript, and Rust - ensuring consistent behavior across ecosystems.

### 4. Agent-Optimized Responses

Responses are structured for agent consumption:
- File paths are absolute (no ambiguity)
- Line/column numbers are 1-indexed (LSP standard)
- Context included (symbol signatures, surrounding code)
- Diagnostics inline with code (no separate lookup)

### 5. Production-Ready DAP Integration

Full debugging support via Neovim's DAP client:
- Language-agnostic (works with any DAP adapter)
- Robust state management
- Async polling for distributed system reliability
- Battle-tested through nvim-dap plugin

## What Otter Is NOT

Otter is **not** a replacement for:
- Shell access (agents should use shell directly)
- File manipulation tools (use standard UNIX tools)
- Git operations (use git CLI)
- Build systems (use make, cargo, npm, etc.)
- Test runners (use pytest, jest, cargo test, etc.)

Otter complements these tools by providing semantic code understanding that shell commands cannot easily provide.

## Current Status

**Production-Ready Foundation**:
- ✅ 15 core tools implemented
- ✅ 204 tests passing
- ✅ Zero mypy errors (strict mode)
- ✅ Python, TypeScript, JavaScript, Rust support
- ✅ Comprehensive debugging capabilities

**Ready for Use**:
- MCP server interface is stable
- LSP integration is robust and tested
- DAP integration is feature-complete
- Configuration system is flexible and documented

See [CONFIGURATION.md](./CONFIGURATION.md) for setup details and [CONTRIBUTING.md](./CONTRIBUTING.md) for development information.
