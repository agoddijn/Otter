# Why Otter?

## The Problem: Agents Need IDEs

AI agents are getting better at writing code, but they're fundamentally limited by their tools. While agents can:

- ✅ Read files and search text (`cat`, `grep`, `rg`)
- ✅ Run commands and tests (`pytest`, `npm test`)
- ✅ Use Git (`git diff`, `git commit`)

They **cannot** easily:

- ❌ Understand code semantics (types, relationships)
- ❌ Navigate codebases (find definitions, references)
- ❌ Debug running processes (breakpoints, inspection)
- ❌ Safely refactor (rename across files)
- ❌ Access LSP intelligence (completions, diagnostics)

**Otter solves this by giving agents an IDE.**

## Why Traditional IDEs Don't Work

### Problem 1: Built for Human Interaction

Traditional IDEs (VS Code, IntelliJ, etc.) are designed for:
- **Visual interfaces**: Menus, sidebars, panels
- **Mouse/keyboard input**: Click, drag, keyboard shortcuts
- **Human workflows**: Open file, click definition, read popup

Agents need:
- **Programmatic interfaces**: Simple API calls
- **Structured data**: JSON, not rendered UI
- **Direct access**: No navigation through UI

### Problem 2: Heavy & GUI-Dependent

Modern IDEs require:
- Electron/browser engines (100s of MB memory)
- Display servers (X11, Wayland)
- GPU rendering
- Complex initialization

Agents run in:
- Headless environments (Docker, CI/CD)
- Resource-constrained VMs
- Terminal-only contexts
- Sandboxed environments

### Problem 3: Not MCP-Native

Existing IDEs don't speak MCP. Integrating them requires:
- Custom bridges and adapters
- Complex state synchronization
- Protocol translation layers
- Fragile workarounds

### Problem 4: Proprietary & Closed

Many IDE features are:
- Closed source
- Require licenses
- Tied to specific platforms
- Not extensible for agent use

## The Otter Solution

### Built for Agents from Day One

**MCP-Native Interface**: All capabilities exposed as MCP tools. No adapters, no workarounds - just call tools.

**Structured Responses**: Every response is a typed dataclass with complete context. No parsing HTML or scraping UI.

**Headless Architecture**: No GUI, no display server required. Runs anywhere Neovim runs.

**Agent-Optimized**: Designed for programmatic access, not human interaction.

### Batteries Included

**Auto-Bootstrap**: Missing LSP servers? Otter installs them. No manual setup, no configuration files (unless you want them).

**Runtime Detection**: Automatically finds:
- Python virtual environments (`.venv`, `venv`, `env`)
- Node.js versions (`.nvmrc`, `package.json`)
- Rust toolchains (`rust-toolchain`, `rust-toolchain.toml`)

**Multi-Language**: Works with Python, TypeScript, JavaScript, Rust, Go out of the box. More languages easy to add.

**Zero Configuration**: Drop into any project and it works. Configure only for advanced use cases.

### Free & Open Source

**MIT Licensed**: Use anywhere, for anything, no restrictions.

**Open Development**: All code on GitHub, contributions welcome.

**No Vendor Lock-In**: Based on open standards (LSP, DAP, MCP).

**Community-Driven**: Built for the agent development community.

## Use Cases

### 1. Code Understanding & Navigation

**Scenario**: Agent needs to understand a large codebase to add a feature.

**Without Otter**:
```
Agent: Uses grep/ripgrep to find text matches
      → Gets false positives (comments, strings, wrong symbols)
      → Can't distinguish between definitions and usages
      → Must manually trace relationships
      → Time-consuming and error-prone
```

**With Otter**:
```
Agent: find_definition("DatabaseService")
      → Gets exact definition location with signature
      find_references("DatabaseService")  
      → Gets all actual usages (no false positives)
      get_symbols("services.py")
      → Gets complete structure of file
```

**Result**: 10x faster navigation, zero false positives.

### 2. Debugging Production Issues

**Scenario**: Agent needs to debug why a test is failing.

**Without Otter**:
```
Agent: Adds print statements
      → Re-runs test
      → Reads output
      → Adds more print statements
      → Re-runs again
      → Repeat 10+ times
```

**With Otter**:
```
Agent: start_debug_session("test_checkout.py", breakpoints=[45])
      → Runs test with breakpoint
      inspect_state("cart.total")
      → Sees actual value at breakpoint
      control_execution("step_over")
      → Steps through logic
      inspect_state("discount.applied")
      → Finds the bug
```

**Result**: Debug in 2 minutes instead of 20.

### 3. Safe Refactoring

**Scenario**: Agent needs to rename a function used across 50 files.

**Without Otter**:
```
Agent: Uses find-and-replace
      → Misses some usages
      → Renames unrelated symbols with same name
      → Breaks imports
      → Tests fail mysteriously
```

**With Otter** *(coming soon)*:
```
Agent: rename_symbol("process_payment", "handle_payment")
      → LSP finds all actual references
      → Renames safely across all files
      → Updates imports automatically
      → Preview changes before applying
```

**Result**: Safe, correct refactoring every time.

### 4. Multi-Language Projects

**Scenario**: Agent working on fullstack project (Python backend, TypeScript frontend).

**Without Otter**:
```
Agent: Manually configures Python LSP
      → Manually configures TypeScript LSP
      → Manually finds virtual environment
      → Manually finds Node.js version
      → Manually installs all servers
      → Configurations conflict or break
```

**With Otter**:
```
Agent: Just runs Otter with .otter.toml
      → Auto-detects Python venv in backend/
      → Auto-detects Node.js in frontend/
      → Auto-installs pyright and tsserver
      → Works across both languages seamlessly
```

**Result**: Zero configuration, works instantly.

## Why Not Just Use X?

### "Why not just use VS Code Server?"

- ❌ Requires GUI/browser
- ❌ Not MCP-native
- ❌ Heavy (Electron-based)
- ❌ Complex to automate
- ✅ Otter: Headless, MCP-native, lightweight

### "Why not just use LSP directly?"

- ❌ Requires implementing LSP protocol
- ❌ Need to manage server lifecycle
- ❌ Handle initialization, capabilities, etc.
- ❌ Different per language
- ✅ Otter: LSP abstracted away, unified interface

### "Why not just use tree-sitter?"

- ❌ Syntax only, no semantics
- ❌ Can't resolve types
- ❌ Can't find cross-file references
- ❌ No diagnostics
- ✅ Otter: LSP + TreeSitter for complete understanding

### "Why not just parse code manually?"

- ❌ Reinventing the wheel
- ❌ Language-specific parsers
- ❌ Constant maintenance
- ❌ No type information
- ✅ Otter: Leverages mature, battle-tested tools

## The Vision

**Otter aims to be the standard IDE for AI agents.**

Just as human developers use VS Code, IntelliJ, or Vim, AI agents should use Otter. It should be:

- **Universal**: Works with any language, any environment
- **Reliable**: Rock-solid, production-ready
- **Fast**: Optimized for agent workflows
- **Open**: Free, open source, community-driven
- **Simple**: Drop-in anywhere, zero configuration

## Getting Started

Ready to give your agents an IDE?

→ See [GETTING_STARTED.md](./GETTING_STARTED.md) for installation and setup
→ See [CONFIGURATION.md](./CONFIGURATION.md) for advanced configuration
→ See [CONTRIBUTING.md](./CONTRIBUTING.md) to help build the future

**Otter: Because agents deserve an IDE too.** 🦦

