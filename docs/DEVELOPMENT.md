# Implementation Guide - Quick Reference

This document captures key decisions, corrections, and patterns learned during implementation. Read this before implementing new tools!

## Core Principles (READ FIRST!)

### 1. 🎯 We're a Wrapper, Not a Re-implementer

**DO:**
- ✅ Use TreeSitter (via Neovim) for parsing
- ✅ Use LSP for code intelligence  
- ✅ Use ripgrep for searches
- ✅ Execute Lua in Neovim to leverage its ecosystem

**DON'T:**
- ❌ Implement language-specific parsers in Python
- ❌ Use Python's `ast` module for dependency analysis
- ❌ Create regex-based fallbacks
- ❌ Manually scan files when ripgrep exists

**Why**: Let the battle-tested tools do the heavy lifting. Our code is plumbing.

### 2. 🌍 Language-Agnostic by Design

**Pattern**: Define language-specific queries, but use universal execution path.

```python
# ✅ GOOD: One implementation, works for all languages
self._queries = {
    "python": "(import_statement) @import",
    "javascript": "(import_statement) @import",
    "rust": "(use_declaration) @import",
}

filetype = await nvim.execute_lua("return vim.bo.filetype")
query = self._queries.get(filetype)
# Execute via TreeSitter...
```

```python
# ❌ BAD: Language-specific Python code
if file.endswith('.py'):
    tree = ast.parse(content)
elif file.endswith('.js'):
    # JavaScript parsing logic...
```

### 3. 🏗️ Service Organization

| Service | Purpose | nvim_client |
|---------|---------|-------------|
| `WorkspaceService` | File ops, project structure | Optional |
| `AnalysisService` | Semantic analysis | **Required** |
| `NavigationService` | LSP navigation | **Required** |
| `RefactoringService` | Code transformations | **Required** |

**Rule**: If it does semantic analysis → requires Neovim → nvim_client is NOT Optional

```python
# ✅ Semantic analysis service
class AnalysisService:
    def __init__(self, nvim_client: Any, project_path: Optional[str] = None):
        self.nvim_client = nvim_client  # Required!

# ✅ File operations service  
class WorkspaceService:
    def __init__(self, project_path: str, nvim_client: Optional[Any] = None):
        self.nvim_client = nvim_client  # Optional - some features work without
```

### 4. 📂 Centralized Path Resolution

**ALWAYS** use the centralized path utilities from `cli_ide.utils.path`:

```python
from cli_ide.utils.path import (
    resolve_workspace_path,  # For input paths
    normalize_path_for_response,  # For output paths
)

# ✅ GOOD: Centralized path resolution
file_path = resolve_workspace_path(path, self.project_path)

# ❌ BAD: Manual path resolution
file_path = Path(path)
if not file_path.is_absolute():
    file_path = Path(self.project_path) / path
file_path = file_path.resolve()
```

**Why**: Handles workspace-relative paths correctly for MCP calls, manages macOS symlinks, consistent behavior across all services.

### 5. ⚡ Async Compatibility

**ALL pynvim calls must be wrapped in executor!**

```python
# ❌ BAD: Blocks event loop
self.nvim.command("edit file.py")

# ✅ GOOD: Non-blocking
loop = asyncio.get_event_loop()
await loop.run_in_executor(None, lambda: self.nvim.command("edit file.py"))
```

**ALL async operations need timeouts:**

```python
# ✅ Prevents hanging
result = await asyncio.wait_for(
    self.nvim_client.execute_lua(code),
    timeout=5.0
)
```

### 6. 🧪 Testing Strategy

**Integration Tests** (`tests/integration/`):
- Require running Neovim
- Test actual LSP/TreeSitter integration
- **Assert structure, not content** (parsers may be bootstrapping)

```python
# ✅ GOOD: Verify tool runs
result = await service.analyze_dependencies("file.py")
assert isinstance(result.imports, list)
assert isinstance(result.file, str)

# ❌ BAD: Too specific (fails during bootstrap)
assert len(result.imports) > 0
assert "os" in result.imports
```

**Unit Tests** (`tests/unit/`):
- Mock NeovimClient
- Fast (< 1s per file)
- Test business logic

**Import Convention:**
```python
# ✅ GOOD
from cli_ide.services.analysis import AnalysisService

# ❌ BAD
from src.cli_ide.services.analysis import AnalysisService
```

### 7. 🔧 System Dependencies

**Check dependencies at server startup:**

The server automatically checks for required system dependencies (Neovim, ripgrep, Node.js, Git, gcc/clang) when it starts. If anything is missing, it throws a human-readable `DependencyError`.

**For local development:**

```bash
# Check what's installed
make check-deps

# Install missing dependencies (macOS)
make install-deps
```

**Required dependencies:**
- Neovim (>= 0.9.0)
- Ripgrep (rg)
- Node.js (>= 16.0)
- Git
- C Compiler (gcc or clang)

See [docs/DEPENDENCIES.md](../DEPENDENCIES.md) for details.

## Implementation Patterns

### Pattern 1: Pure Python (No Neovim)

**When**: Simple file operations, no LSP needed

**Example**: `get_project_structure`

```python
def get_project_structure(path: str, max_depth: int):
    # Pure Python - fast, no dependencies
    for root, dirs, files in os.walk(path):
        # Build tree...
```

### Pattern 2: Dual-Mode (Optional Neovim)

**When**: Basic feature works without Neovim, enhanced features need it

**Example**: `read_file`

```python
async def read_file(path: str, include_diagnostics: bool = False):
    # Resolve path using centralized utility
    file_path = resolve_workspace_path(path, self.project_path)
    
    if include_diagnostics and self.nvim_client:
        # Neovim-powered mode
        await self.nvim_client.open_file(file_path)
        await asyncio.sleep(1.5)  # Give LSP time
        diags = await self._get_diagnostics(file_path)
    else:
        # Direct file read mode
        content = file_path.read_text()
```

### Pattern 3: Neovim-Required (Semantic Analysis)

**When**: Feature requires LSP or TreeSitter

**Example**: `analyze_dependencies`

```python
async def analyze_dependencies(file: str):
    if not self.nvim_client.is_running():
        raise RuntimeError("Neovim required")
    
    # Resolve path using centralized utility
    file_path = resolve_workspace_path(file, self.project_path)
    
    # Use TreeSitter for parsing
    filetype = await self.nvim_client.execute_lua("return vim.bo.filetype")
    query = self._import_queries.get(filetype)
    
    if not query:
        return []  # No fallback - return empty
    
    # Execute TreeSitter query...
    
    # Normalize path for response
    normalized_file = normalize_path_for_response(file_path, self.project_path)
    return DependencyGraph(file=normalized_file, ...)
```

### Pattern 4: TreeSitter Queries

**Structure**:
1. Define queries per language in `__init__`
2. Get filetype from Neovim
3. Execute query via Lua
4. Parse results (language-specific extraction)
5. Return structured data

```python
class AnalysisService:
    def __init__(self, nvim_client, project_path):
        self.nvim_client = nvim_client
        self._import_queries = {
            "python": """
                (import_statement) @import
                (import_from_statement) @import
            """,
            "javascript": """
                (import_statement) @import
            """,
        }
    
    async def _get_imports(self, file_path):
        # 1. Get filetype
        filetype = await self.nvim_client.execute_lua("return vim.bo.filetype")
        
        # 2. Get query
        query = self._import_queries.get(filetype)
        if not query:
            return []
        
        # 3. Execute via TreeSitter
        nodes = await self.nvim_client.execute_lua(f"""
            local parser = vim.treesitter.get_parser(bufnr, '{filetype}')
            local tree = parser:parse()[1]
            local query = vim.treesitter.query.parse('{filetype}', [[{query}]])
            
            local results = {{}}
            for id, node in query:iter_captures(root, bufnr, 0, -1) do
                table.insert(results, vim.treesitter.get_node_text(node, bufnr))
            end
            return results
        """)
        
        # 4. Parse results
        imports = self._extract_module_names(nodes, filetype)
        
        return sorted(set(imports))
```

## Common Gotchas

### 1. LSP Indexing (0 vs 1)

LSP uses 0-indexed positions, users expect 1-indexed:

```python
# ✅ Always convert LSP results
lsp_result = await self.lsp.get_definition(file, line - 1, col - 1)  # To LSP
return Definition(line=lsp_result.line + 1, col=lsp_result.col + 1)  # From LSP
```

### 2. macOS Path Symlinks

`/var` is symlinked to `/private/var` on macOS:

```python
# ✅ Always use centralized utilities
file_path = resolve_workspace_path(path, project_path)
normalized = normalize_path_for_response(file_path, project_path)

# ❌ BAD: Manual resolution fails on macOS
file_path.relative_to(project_path)
```

### 3. Workspace-Relative Paths

MCP clients often send workspace-relative paths like `"main.py"`:

```python
# ✅ GOOD: Use centralized utility
file_path = resolve_workspace_path("main.py", "/fern_mono")
# → /fern_mono/main.py

# ❌ BAD: Treats as absolute path
file_path = Path("main.py").resolve()
# → /current/dir/main.py (WRONG!)
```

### 4. LSP Timing

LSP needs time to analyze files:

```python
# ✅ Give LSP time after opening file
await self.nvim_client.open_file(file_path)
await asyncio.sleep(1.5)  # Critical!
diagnostics = await self.nvim_client.get_diagnostics(file_path)
```

### 5. Lua Module Path

Neovim must find your Lua configs:

```lua
-- ✅ MUST set package.path in init.lua
local config_path = vim.fn.fnamemodify(debug.getinfo(1).source:sub(2), ":h")
package.path = package.path .. ";" .. config_path .. "/lua/?.lua"
```

### 6. TreeSitter Parser Installation

Parsers install on first run:

```lua
-- configs/lua/plugins.lua
{
    'nvim-treesitter/nvim-treesitter',
    build = ':TSUpdate',
    config = function()
        require('nvim-treesitter.configs').setup({
            ensure_installed = {  -- CRITICAL!
                "python", "javascript", "typescript",
                "rust", "go", "lua",
            },
            auto_install = true,  -- Auto-install missing parsers
        })
    end,
}
```

### 7. System Dependencies

**MUST** have system dependencies installed:

```bash
# Check before starting
make check-deps

# Install if missing (macOS)
make install-deps
```

Missing dependencies will cause errors like:
- "command not found: rg" → Install ripgrep
- Neovim won't start → Install neovim
- LSP doesn't work → Install node.js

## Checklist for New Tools

Before implementing a new tool:

- [ ] Read SPECIFICATION.md for requirements
- [ ] Decide: Pure Python, Dual-mode, or Neovim-required?
- [ ] Check which service it belongs in (Workspace/Analysis/Navigation/Refactoring)
- [ ] If Neovim-required: make nvim_client a required parameter
- [ ] Use `resolve_workspace_path()` for input paths
- [ ] Use `normalize_path_for_response()` for output paths
- [ ] If using TreeSitter: define queries for all supported languages
- [ ] If using LSP: remember 0→1 index conversion
- [ ] Wrap all pynvim calls in `run_in_executor`
- [ ] Add timeouts to all async operations
- [ ] Write integration tests that verify structure, not content
- [ ] Write unit tests with mocked Neovim
- [ ] Document the implementation in ARCHITECTURE.md

## Quick Command Reference

```bash
# Check system dependencies
make check-deps

# Install dependencies (macOS)
make install-deps

# Run all tests
make test

# Run just integration tests (slower, requires Neovim)
make test-integration

# Run just unit tests (faster, mocked)
make test-unit

# Install package in editable mode
uv pip install -e .

# Check for linter errors
uv run ruff check src/

# Format code
uv run ruff format src/
```

## Next Tool Implementation

When implementing the next tool:

1. Check system dependencies: `make check-deps`
2. Read the SPECIFICATION.md entry for the tool
3. Look at similar implemented tools in this guide
4. Copy the appropriate pattern (Pure Python / Dual-mode / Neovim-required)
5. **Use centralized path utilities** for all path handling
6. Write tests first (TDD)
7. Implement using Neovim/LSP/TreeSitter (not Python-specific logic)
8. Update ARCHITECTURE.md with learnings
9. Update this guide if you discovered new patterns

## Questions to Ask

Before implementing:
- Can this be done without Neovim? (Use Pure Python)
- Do I need LSP? (Make nvim_client required)
- Do I need TreeSitter? (Use query pattern)
- Is this language-specific? (❌ Make it language-agnostic!)
- Am I re-implementing something that exists in Neovim/ripgrep/LSP? (❌ Use the tool!)
- Am I handling paths manually? (❌ Use centralized utilities!)

## Documentation Locations

- **SPECIFICATION.md**: What each tool should do
- **ARCHITECTURE.md**: How it's implemented, detailed patterns
- **IMPLEMENTATION_GUIDE.md**: This file - quick reference
- **DEPENDENCIES.md**: System dependency requirements
- **TREESITTER_SETUP.md**: TreeSitter configuration details
- **ANALYZE_DEPENDENCIES.md**: Example of full implementation writeup

---

**Remember**: We're building a thin wrapper around best-in-class tools. When in doubt, delegate to Neovim/LSP/TreeSitter!