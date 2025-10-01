# Otter

**The IDE for AI Agents**

Otter exposes LSP, DAP, and TreeSitter-powered code intelligence through the Model Context Protocol.

## What Otter Provides

- **LSP Navigation** - Find definitions, references, hover info, completions
- **DAP Debugging** - Programmatic debugging (Python, JS/TS, Rust, Go)
- **TreeSitter Analysis** - Language-agnostic dependency analysis
- **Diagnostics** - LSP errors and warnings

## What Otter Doesn't Provide

Use standard shell commands for:

- Text/regex search → `rg`
- Running tests → `pytest`, `cargo test`, etc.
- Git operations → `git`

## Philosophy

Otter is a **thin wrapper** around battle-tested tools. We leverage Neovim's ecosystem instead of reimplementing protocols.

**Key principle**: Code is the source of truth. This documentation is auto-generated from docstrings and type hints.

## Quick Links

- [Installation](getting-started/installation.md)
- [API Reference](api/overview.md)
- [Architecture](development/architecture.md)
- [Contributing](development/contributing.md)

## Status

**13 of 15 tools complete** (87%)

- ✅ Navigation (4 tools): `find_definition`, `find_references`, `get_hover_info`, `get_completions`
- ✅ Intelligence (2 tools): `get_symbols`, `analyze_dependencies`
- ✅ Files (1 tool): `read_file`
- ✅ Diagnostics (1 tool): `get_diagnostics`
- ✅ Debugging (5 tools): DAP-powered debugging
- 🚧 Refactoring (2 tools): Coming soon

