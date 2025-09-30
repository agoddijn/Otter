# Technical Guide: Neovim & TreeSitter Integration

This guide explains the technical details of how the CLI IDE leverages Neovim and TreeSitter for code intelligence.

---

## Table of Contents
1. [Neovim Integration](#neovim-integration)
2. [TreeSitter Setup](#treesitter-setup)
3. [LSP Configuration](#lsp-configuration)
4. [Troubleshooting](#troubleshooting)

---

## Neovim Integration

### Architecture

```
┌─────────────────────────────────────┐
│     CliIdeServer                    │
│  (Main server facade)                │
└──────────┬──────────────────────────┘
           │
           ├──> NeovimClient (Manages headless Neovim)
           │      │
           │      ├──> pynvim (RPC communication)
           │      └──> Neovim Process (headless)
           │           │
           │           ├──> LSP Servers (pyright, tsserver, etc.)
           │           ├──> TreeSitter (AST parsing)
           │           └──> Lua IDE API
           │
           └──> Services (Use Neovim client)
                 ├──> NavigationService
                 ├──> WorkspaceService
                 ├──> RefactoringService
                 └──> AnalysisService
```

### NeovimClient API

#### Lifecycle Management

```python
from cli_ide.neovim.client import NeovimClient

# Initialize with project path
client = NeovimClient(project_path="/path/to/project")

# Start Neovim instance
await client.start()

# Use client...

# Stop and cleanup
await client.stop()

# Or use as context manager
async with NeovimClient(project_path="/path/to/project") as client:
    # Automatically started and stopped
    pass
```

#### Core Methods

```python
# Buffer operations
lines = await client.read_buffer(filepath, line_range=(1, 10))
await client.open_file(filepath)

# LSP operations
definition = await client.lsp_definition(filepath, line, column)
references = await client.lsp_references(filepath, line, column)
hover_info = await client.lsp_hover(filepath, line, column)
symbols = await client.lsp_document_symbols(filepath)
diagnostics = await client.get_diagnostics(filepath)

# Lua execution (for advanced features)
result = await client.execute_lua(lua_code, *args)
```

### Async Compatibility

**Critical**: `pynvim` is synchronous, but our server is async. We handle this with:

```python
import asyncio

async def async_method(self):
    # Run sync pynvim calls in executor
    def sync_call():
        return self.nvim.command("...")
    
    return await asyncio.get_event_loop().run_in_executor(None, sync_call)
```

**Pattern**: All `NeovimClient` methods are async and use `run_in_executor` internally.

### LSP Integration Pattern

LSP requests go through Neovim's Lua API:

```python
async def lsp_definition(self, filepath: str, line: int, column: int):
    """Get definition using LSP through Neovim."""
    buf_num = await self.open_file(filepath)
    
    # Wait for LSP to attach
    await asyncio.sleep(0.5)
    
    # Call LSP via Lua
    lua_code = f"""
    local bufnr = {buf_num}
    local params = {{
        textDocument = vim.lsp.util.make_text_document_params(bufnr),
        position = {{ line = {line - 1}, character = {column} }}
    }}
    local result = vim.lsp.buf_request_sync(bufnr, 'textDocument/definition', params, 2000)
    
    -- Extract results
    for _, response in pairs(result) do
        if response.result then
            return response.result
        end
    end
    return nil
    """
    
    return await self.execute_lua(lua_code)
```

**Why Lua?**
- Neovim's LSP client is Lua-native
- pynvim doesn't provide direct LSP bindings
- Lua is the right layer for LSP operations

### Configuration Files

The IDE uses custom Neovim configuration:

```
configs/
├── init.lua           # Main config (loads modules)
├── lua/
    ├── ide.lua        # IDE-specific settings
    ├── lsp.lua        # LSP server configuration
    └── plugins.lua    # Plugin setup (TreeSitter, etc.)
```

**Note**: This config is separate from user's personal Neovim config.

---

## TreeSitter Setup

### Overview

TreeSitter provides language-agnostic parsing through Neovim, enabling features like dependency analysis to work across multiple languages without Python-specific parsers.

### Supported Languages

TreeSitter parsers are automatically installed for:
- **Python** (`.py`)
- **JavaScript** (`.js`)
- **TypeScript** (`.ts`, `.tsx`)
- **Rust** (`.rs`)
- **Go** (`.go`)
- **Lua** (`.lua`)
- **JSON** (`.json`)
- **YAML** (`.yaml`, `.yml`)
- **Markdown** (`.md`)
- **Bash** (`.sh`)

### How It Works

1. **Automatic Installation**: When Neovim starts, TreeSitter automatically downloads and compiles parsers
2. **Language Detection**: Neovim detects filetype based on file extension
3. **Query Execution**: Our services use TreeSitter queries to extract semantic information

### TreeSitter Queries

#### Import Detection Example

```lua
-- Python imports query
local python_imports_query = [[
  (import_statement
    name: (dotted_name) @import)
  
  (import_from_statement
    module_name: (dotted_name) @import)
]]

-- Execute query
local parser = vim.treesitter.get_parser(bufnr, 'python')
local tree = parser:parse()[1]
local query = vim.treesitter.query.parse('python', python_imports_query)

local imports = {}
for id, node in query:iter_captures(tree:root(), bufnr, 0, -1) do
    local text = vim.treesitter.get_node_text(node, bufnr)
    table.insert(imports, text)
end
```

#### Language-Specific Queries

**Python:**
```scheme
(import_statement
  name: (dotted_name) @import)

(import_from_statement
  module_name: (dotted_name) @import)
```

**JavaScript/TypeScript:**
```scheme
(import_statement
  source: (string) @import)

(call_expression
  function: (identifier) @fn (#eq? @fn "require")
  arguments: (arguments (string) @import))
```

**Rust:**
```scheme
(use_declaration
  argument: (scoped_identifier) @import)
```

**Go:**
```scheme
(import_spec
  path: (interpreted_string_literal) @import)
```

### Configuration

In `configs/lua/plugins.lua`:

```lua
-- TreeSitter configuration
require('nvim-treesitter.configs').setup({
  ensure_installed = {
    "python", "javascript", "typescript", "tsx",
    "rust", "go", "lua", "json", "yaml",
    "markdown", "bash"
  },
  
  -- Install parsers synchronously
  sync_install = false,
  
  -- Auto-install missing parsers
  auto_install = true,
  
  highlight = {
    enable = true,
  },
  
  incremental_selection = {
    enable = true,
    keymaps = {
      init_selection = "gnn",
      node_incremental = "grn",
      scope_incremental = "grc",
      node_decremental = "grm",
    },
  },
  
  indent = {
    enable = true
  },
})
```

### Performance Considerations

- **First Run**: TreeSitter parsers are compiled on first use (~10-30 seconds per language)
- **Subsequent Runs**: Cached parsers load instantly
- **Large Files**: TreeSitter is incremental, so parsing is fast even for large files

---

## LSP Configuration

### Automatic LSP Setup

LSP servers are automatically configured in `configs/lua/lsp.lua`:

```lua
local lspconfig = require('lspconfig')

-- Python
lspconfig.pyright.setup({
  settings = {
    python = {
      analysis = {
        typeCheckingMode = "basic",
        autoImportCompletions = true,
      }
    }
  }
})

-- TypeScript/JavaScript
lspconfig.tsserver.setup({})

-- Rust
lspconfig.rust_analyzer.setup({})

-- Go
lspconfig.gopls.setup({})
```

### Required LSP Servers

Install language servers for the languages you use:

```bash
# Python
pip install pyright

# TypeScript/JavaScript
npm install -g typescript typescript-language-server

# Rust
rustup component add rust-analyzer

# Go
go install golang.org/x/tools/gopls@latest
```

See [DEPENDENCIES.md](DEPENDENCIES.md) for full setup instructions.

### LSP Capabilities

The IDE leverages these LSP features:

1. **textDocument/definition** - Jump to definitions
2. **textDocument/references** - Find all references
3. **textDocument/hover** - Type info and docs
4. **textDocument/documentSymbol** - File outline
5. **textDocument/diagnostic** - Errors and warnings
6. **textDocument/completion** - Autocomplete (coming soon)
7. **textDocument/codeAction** - Quick fixes (coming soon)
8. **textDocument/formatting** - Code formatting (coming soon)

---

## Troubleshooting

### Neovim Not Starting

**Problem**: `NeovimClient.start()` times out

**Solutions**:
1. Check Neovim is installed: `nvim --version`
2. Check config is valid: `nvim --clean -u configs/init.lua`
3. Enable debug logging in NeovimClient
4. Check `nvim.log` in project root

### LSP Not Responding

**Problem**: LSP methods return `None`

**Solutions**:
1. Wait longer after opening file (increase `await asyncio.sleep(0.5)`)
2. Check LSP server is installed (see DEPENDENCIES.md)
3. Check Neovim LSP logs: `:LspInfo` in Neovim
4. Verify file type is detected: Check `:set ft?`

### TreeSitter Parsers Missing

**Problem**: Import detection returns empty results

**Solutions**:
1. Parsers install automatically on first run - wait for completion
2. Manually install: `:TSInstall python` in Neovim
3. Check installation: `:TSInstallInfo` in Neovim
4. Verify parser works: Open a file and check syntax highlighting

### Performance Issues

**Problem**: LSP requests are slow

**Solutions**:
1. LSP startup is slower for large projects (~1-2 seconds)
2. First request to a file includes parsing time
3. Subsequent requests to same file are cached by LSP
4. Consider pre-loading files in Neovim if possible

### Async Errors

**Problem**: `RuntimeError: Event loop is closed` or similar

**Solutions**:
1. Always use `await` with NeovimClient methods
2. Don't mix sync and async code
3. Use `asyncio.run()` if calling from sync context
4. Check all pynvim calls use `run_in_executor`

---

## Advanced Topics

### Custom TreeSitter Queries

You can write custom queries for specialized analysis:

```python
async def find_all_classes(self, filepath: str) -> List[str]:
    """Find all class definitions in a Python file."""
    lua_code = """
    local query_string = [[
      (class_definition
        name: (identifier) @class_name)
    ]]
    
    local parser = vim.treesitter.get_parser(0, 'python')
    local tree = parser:parse()[1]
    local query = vim.treesitter.query.parse('python', query_string)
    
    local classes = {}
    for id, node in query:iter_captures(tree:root(), 0, 0, -1) do
        local text = vim.treesitter.get_node_text(node, 0)
        table.insert(classes, text)
    end
    return classes
    """
    
    await self.nvim_client.open_file(filepath)
    return await self.nvim_client.execute_lua(lua_code)
```

### Direct Lua Execution

For maximum flexibility, execute arbitrary Lua:

```python
result = await client.execute_lua("""
    -- Any valid Lua code
    local buf = vim.api.nvim_get_current_buf()
    local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
    return { buffer = buf, line_count = #lines }
""")
```

### Multiple Neovim Instances

For parallel processing, you can run multiple Neovim instances:

```python
# Each instance is independent
client1 = NeovimClient(project_path="/project1")
client2 = NeovimClient(project_path="/project2")

await client1.start()
await client2.start()

# Use concurrently
results = await asyncio.gather(
    client1.lsp_definition(...),
    client2.lsp_definition(...)
)
```

---

## References

- [Neovim LSP Documentation](https://neovim.io/doc/user/lsp.html)
- [TreeSitter Documentation](https://tree-sitter.github.io/tree-sitter/)
- [pynvim Documentation](https://pynvim.readthedocs.io/)
- [LSP Specification](https://microsoft.github.io/language-server-protocol/)
