# Documentation Index

This directory contains comprehensive documentation for Otter - the IDE for AI agents.

---

## 📚 Documentation Structure

### For Users (3 documents)

| Document | Purpose | Audience |
|----------|---------|----------|
| **[../README.md](../README.md)** | Quick start, installation, overview | Everyone |
| **[USER_GUIDE.md](USER_GUIDE.md)** | Complete tool reference and usage | Users, Integrators |
| **[DEPENDENCIES.md](DEPENDENCIES.md)** | System requirements and setup | Users, DevOps |

### For Contributors (4 documents)

| Document | Purpose | Audience |
|----------|---------|----------|
| **[CONTRIBUTING.md](CONTRIBUTING.md)** | How to contribute, code patterns, testing | Contributors |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | High-level design and decisions | Developers |
| **[TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md)** | Neovim, LSP, TreeSitter, DAP details | Developers |
| **[ROADMAP.md](ROADMAP.md)** | Planned tools and features by priority | Contributors, Users |

### Project Documentation (2 documents)

| Document | Purpose | Audience |
|----------|---------|----------|
| **[../tests/TESTING.md](../tests/TESTING.md)** | Complete testing guide | Contributors |
| **[../CHANGELOG.md](../CHANGELOG.md)** | Version history and changes | Everyone |

---

## 📖 Quick Navigation

### Getting Started
1. **[../README.md](../README.md)** - Start here for installation
2. **[DEPENDENCIES.md](DEPENDENCIES.md)** - Install system dependencies
3. **[USER_GUIDE.md](USER_GUIDE.md)** - Learn how to use Otter

### Using Otter
- **[USER_GUIDE.md](USER_GUIDE.md)** - All 15 tools with examples
- **[../README.md#using-with-mcp-clients](../README.md#using-with-mcp-clients)** - Integration examples

### Contributing
1. **[CONTRIBUTING.md](CONTRIBUTING.md)** - Start here for development
2. **[ARCHITECTURE.md](ARCHITECTURE.md)** - Understand the design
3. **[TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md)** - Deep dive into implementation
4. **[../tests/TESTING.md](../tests/TESTING.md)** - Testing guide

---

## 📄 Document Summaries

### ROADMAP.md
**What**: Planned tools and features with detailed specifications  
**When to read**: Understanding future direction or picking tasks  
**Key sections**:
- High priority tools (buffer editing, LSP quick fixes)
- Medium priority tools (advanced navigation, refactoring)
- Low priority tools (polish and helpers)
- Out of scope features (what Otter won't do)
- Implementation estimates and phases

### README.md (Project Root)
**What**: Project overview, installation, quick start  
**When to read**: First time using Otter  
**Key sections**:
- Philosophy & features
- Quick setup
- MCP client integration
- Development status

### USER_GUIDE.md
**What**: Complete reference for all Otter tools  
**When to read**: Learning how to use specific tools  
**Key sections**:
- All 15 tools with parameters, returns, examples
- Language support
- Integration examples
- Troubleshooting

### DEPENDENCIES.md
**What**: System dependency requirements and installation  
**When to read**: Setting up development environment  
**Key sections**:
- Required dependencies (Neovim, ripgrep, Node.js, etc.)
- LSP server installation per language
- DAP adapter installation
- macOS installation with Homebrew
- Troubleshooting

### CONTRIBUTING.md
**What**: Complete contributor guide  
**When to read**: Contributing to Otter  
**Key sections**:
- Core principles (wrapper not reimplementer, language-agnostic)
- Development patterns (services, paths, async, LSP, TreeSitter, DAP)
- Testing guide (unit, integration, parameterized)
- Adding new features
- Pull request process
- Common gotchas

### ARCHITECTURE.md
**What**: High-level architecture and design decisions  
**When to read**: Understanding system design  
**Key sections**:
- System architecture diagram
- Layer responsibilities
- Design decisions and rationale
- Key learnings (LSP via Lua, DAP integration, async patterns)
- Current status and next priorities

### TECHNICAL_GUIDE.md
**What**: Deep technical details on Neovim integration  
**When to read**: Implementing LSP/DAP/TreeSitter features  
**Key sections**:
- Neovim client API and patterns
- LSP integration via Lua
- DAP integration via nvim-dap
- TreeSitter setup and queries
- Async/sync boundary handling
- Troubleshooting

### ../tests/TESTING.md
**What**: Complete testing documentation  
**When to read**: Writing or running tests  
**Key sections**:
- Running tests (all, by type, by language)
- Writing unit and integration tests
- Language-agnostic parameterized testing
- Debug test framework (exponential backoff polling)
- Best practices

### ../CHANGELOG.md
**What**: Version history and notable changes  
**When to read**: Checking what's new or changed  
**Key sections**:
- Latest features (DAP debugging, parameterized tests)
- Breaking changes (none yet)
- Migration guides
- Version history

---

## 🗺️ Documentation Map by Task

### "I want to use Otter"
1. [../README.md](../README.md) - Installation and quick start
2. [DEPENDENCIES.md](DEPENDENCIES.md) - Install dependencies
3. [USER_GUIDE.md](USER_GUIDE.md) - Tool reference

### "I want to understand how it works"
1. [ARCHITECTURE.md](ARCHITECTURE.md) - High-level design
2. [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md) - Technical deep dive

### "I want to contribute"
1. [CONTRIBUTING.md](CONTRIBUTING.md) - Start here
2. [ROADMAP.md](ROADMAP.md) - What needs to be built
3. [ARCHITECTURE.md](ARCHITECTURE.md) - Design principles
4. [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md) - Implementation details
5. [../tests/TESTING.md](../tests/TESTING.md) - Testing guide

### "I'm having issues"
1. [DEPENDENCIES.md](DEPENDENCIES.md) - Dependency troubleshooting
2. [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md) - Common issues
3. [USER_GUIDE.md](USER_GUIDE.md) - Tool-specific troubleshooting

---

## 🔄 Recent Consolidation

**October 1, 2025** - Major documentation consolidation:

**Created (4 new)**:
- ✨ `USER_GUIDE.md` - Complete tool reference
- ✨ `CONTRIBUTING.md` - Contributor guide
- ✨ `../tests/TESTING.md` - Complete testing guide
- ✨ `../CHANGELOG.md` - Version history

**Removed (8 redundant)**:
- ❌ `SPECIFICATION.md` → Merged into USER_GUIDE.md
- ❌ `DEVELOPMENT.md` → Merged into CONTRIBUTING.md
- ❌ `PRIORITY_ANALYSIS.md` → Outdated priorities
- ❌ `DAP_IMPLEMENTATION_COMPLETE.md` → Extracted to CHANGELOG.md
- ❌ `DEBUGGING_TEST_FRAMEWORK.md` → Merged into TESTING.md
- ❌ `DEBUGGING_TEST_REPORT.md` → Historical, archived
- ❌ `DEBUGGING_TEST_RESULTS.md` → Snapshot, not needed
- ❌ `../tests/PARAMETERIZATION_COMPLETE.md` → Merged into TESTING.md
- ❌ `../tests/REFACTORING_SUMMARY.md` → Merged into TESTING.md
- ❌ `../tests/README.md` → Merged into TESTING.md
- ❌ `../tests/LANGUAGE_AGNOSTIC_TESTING_GUIDE.md` → Merged into TESTING.md

**Result**: From 17 documents → 10 core documents + changelog (41% reduction)

---

## 📊 Documentation Statistics

| Category | Documents | Purpose |
|----------|-----------|---------|
| User Docs | 3 | Using Otter |
| Contributor Docs | 4 | Development & roadmap |
| Project Docs | 2 | Testing & history |
| Index | 2 | Navigation (this file + README) |
| **Total** | **11** | **Focused, consolidated** |

---

## ✅ Documentation Quality

- ✅ Clear structure (user vs contributor docs)
- ✅ No duplicate information
- ✅ Up-to-date with current implementation (13/15 tools, 204 tests)
- ✅ Cross-referenced appropriately
- ✅ Comprehensive yet concise
- ✅ Examples where helpful
- ✅ Troubleshooting sections included

---

## 🔗 External Resources

- [Model Context Protocol Docs](https://modelcontextprotocol.io)
- [Neovim LSP Documentation](https://neovim.io/doc/user/lsp.html)
- [Debug Adapter Protocol](https://microsoft.github.io/debug-adapter-protocol/)
- [TreeSitter Documentation](https://tree-sitter.github.io/tree-sitter/)
- [pynvim Documentation](https://pynvim.readthedocs.io/)
