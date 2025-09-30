# Documentation Index

This directory contains comprehensive documentation for the CLI IDE for AI Agents.

---

## 📚 Documentation Structure

### For Users

| Document | Purpose | Audience |
|----------|---------|----------|
| **[../README.md](../README.md)** | Quick start, installation, usage | Everyone |
| **[DEPENDENCIES.md](DEPENDENCIES.md)** | System requirements and setup | Users, DevOps |
| **[SPECIFICATION.md](SPECIFICATION.md)** | Complete tool specifications | Users, Integrators |

### For Developers

| Document | Purpose | Audience |
|----------|---------|----------|
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | High-level design and decisions | Developers |
| **[TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md)** | Neovim, LSP, TreeSitter details | Developers |
| **[DEVELOPMENT.md](DEVELOPMENT.md)** | Implementation patterns | Contributors |

---

## 📖 Quick Reference

### Getting Started
1. **[../README.md](../README.md)** - Start here for installation and quick start
2. **[DEPENDENCIES.md](DEPENDENCIES.md)** - Install system dependencies
3. Run `make dev` to test the IDE

### Using the IDE
- **[SPECIFICATION.md](SPECIFICATION.md)** - See all 21 available tools and their parameters
- Use MCP Inspector (`make dev`) to explore interactively

### Contributing
1. **[DEVELOPMENT.md](DEVELOPMENT.md)** - Learn implementation patterns
2. **[ARCHITECTURE.md](ARCHITECTURE.md)** - Understand the design
3. **[TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md)** - Deep dive into Neovim integration

---

## 📄 Document Descriptions

### README.md (Project Root)
**What**: Project overview, installation, quick start  
**When to read**: First time using the IDE  
**Length**: ~350 lines

### DEPENDENCIES.md
**What**: Detailed system dependency requirements and installation  
**When to read**: Setting up development environment  
**Key sections**:
- Required dependencies (Neovim, ripgrep, etc.)
- LSP server installation per language
- macOS installation with Homebrew
- Troubleshooting dependency issues

**Length**: ~245 lines

### SPECIFICATION.md
**What**: Complete specification of all 21 IDE tools  
**When to read**: Integrating with the IDE or implementing features  
**Key sections**:
- Tool categories and overview
- Detailed parameters for each tool
- Response structure definitions
- Usage examples

**Length**: ~520 lines

### ARCHITECTURE.md
**What**: High-level architecture, design decisions, learnings  
**When to read**: Understanding the system design  
**Key sections**:
- System architecture diagram
- Layer responsibilities
- Design decisions and rationale
- Key learnings from implementation
- Current status and metrics

**Length**: ~200 lines (consolidated)

### TECHNICAL_GUIDE.md
**What**: Deep technical details on Neovim and TreeSitter integration  
**When to read**: Implementing LSP features or debugging integration  
**Key sections**:
- Neovim client API and patterns
- LSP integration via Lua
- TreeSitter setup and queries
- Async/sync boundary handling
- Troubleshooting common issues

**Length**: ~400 lines

### DEVELOPMENT.md
**What**: Implementation patterns and best practices  
**When to read**: Contributing new features  
**Key sections**:
- Code patterns and conventions
- Testing strategies
- Common pitfalls and solutions
- How to add new features

**Length**: ~465 lines

---

## 🗺️ Documentation Map by Task

### "I want to use the IDE"
1. [../README.md](../README.md) - Installation and quick start
2. [DEPENDENCIES.md](DEPENDENCIES.md) - Install dependencies
3. [SPECIFICATION.md](SPECIFICATION.md) - Available tools reference

### "I want to understand how it works"
1. [ARCHITECTURE.md](ARCHITECTURE.md) - High-level design
2. [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md) - Technical deep dive

### "I want to add a feature"
1. [DEVELOPMENT.md](DEVELOPMENT.md) - Implementation patterns
2. [ARCHITECTURE.md](ARCHITECTURE.md) - Design principles
3. [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md) - Neovim/LSP details

### "I'm having issues"
1. [DEPENDENCIES.md](DEPENDENCIES.md) - Dependency troubleshooting
2. [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md) - Common issues section
3. [../tests/README.md](../tests/README.md) - Test infrastructure

---

## 🔄 Recent Changes

**Latest Consolidation** (Sept 30, 2025):
- ✅ Consolidated documentation from 9 → 5 core documents
- ✅ Removed temporary implementation notes
- ✅ Merged Neovim and TreeSitter docs into TECHNICAL_GUIDE.md
- ✅ Updated ARCHITECTURE.md with key learnings and metrics
- ✅ Renamed IMPLEMENTATION_GUIDE.md → DEVELOPMENT.md

**Removed** (content merged elsewhere):
- `PROJECT_REVIEW.md` → Merged into ARCHITECTURE.md
- `NEOVIM_INTEGRATION.md` → Merged into TECHNICAL_GUIDE.md
- `TREESITTER_SETUP.md` → Merged into TECHNICAL_GUIDE.md
- `WORKSPACE_PATH_UPDATE.md` → Temporary note, no longer needed
- `ANALYZE_DEPENDENCIES.md` → Temporary note, no longer needed

---

## 📊 Documentation Statistics

| Category | Document Count | Total Lines |
|----------|----------------|-------------|
| User Docs | 3 | ~1,115 lines |
| Developer Docs | 3 | ~1,065 lines |
| **Total** | **6** | **~2,180 lines** |

---

## ✅ Documentation Quality Checklist

- ✅ Clear structure (user vs developer docs)
- ✅ No duplicate information
- ✅ Up-to-date with current implementation
- ✅ Cross-referenced appropriately
- ✅ Comprehensive yet concise
- ✅ Examples where helpful
- ✅ Troubleshooting sections included

---

## 🔗 External Resources

- [Model Context Protocol Docs](https://modelcontextprotocol.io)
- [Neovim LSP Documentation](https://neovim.io/doc/user/lsp.html)
- [TreeSitter Documentation](https://tree-sitter.github.io/tree-sitter/)
- [pynvim Documentation](https://pynvim.readthedocs.io/)
