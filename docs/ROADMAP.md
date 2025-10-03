# Otter Tool Roadmap

This document specifies planned tools and features for Otter, prioritized by value and feasibility.

---

## Table of Contents
1. [Current Status](#current-status)
2. [High Priority Tools](#high-priority-tools-critical-gaps)
3. [Medium Priority Tools](#medium-priority-tools-significant-value)
4. [Low Priority Tools](#low-priority-tools-polish)
5. [Out of Scope](#out-of-scope-terminal-is-better)
6. [Implementation Summary](#implementation-summary)

---

## Current Status

**Implemented Tools**: 13 of 15 core tools (87%)

**Next Up**: 
1. `rename_symbol` - LSP-powered safe refactoring
2. `extract_function` - Smart code extraction

**Total Planned Additions**: 13 new tools (3 high, 6 medium, 4 low priority)

---

## High Priority Tools (Critical Gaps)

These are **must-have** tools that fill critical functionality gaps. Without these, LLMs cannot effectively modify code or apply fixes.

### 1. Buffer Editing

**Why Critical**: LLMs can't code without writing changes. Must maintain LSP sync to preserve code intelligence.

#### `edit_buffer`
Core editing primitive for making code changes.

**Parameters**:
- `file` (string, required) - Path to file to edit
- `edits` (array, required) - List of edit operations:
  - `line_start` (int) - Starting line (1-indexed)
  - `line_end` (int) - Ending line (inclusive)
  - `new_text` (string) - Replacement text
- `preview` (boolean, default: true) - Return unified diff before applying
- `save` (boolean, default: false) - Save buffer after edits

**Returns**:
```python
{
  "preview": "unified diff output",  # If preview=True
  "applied": true,                   # If preview=False
  "buffer_state": {
    "is_modified": true,
    "line_count": 150
  }
}
```

**Behavior**:
- Multiple atomic edits applied together
- Preview mode returns unified diff (no changes applied)
- LSP-aware: triggers re-analysis after edits
- Preserves undo history (Neovim buffer state)
- Validates line ranges before applying

**Example**:
```python
# Preview changes first
result = await session.call_tool("edit_buffer", {
    "file": "src/models.py",
    "edits": [
        {
            "line_start": 10,
            "line_end": 12,
            "new_text": "def process_user(self, user_id: int) -> User:\n    return self.db.get_user(user_id)\n"
        }
    ],
    "preview": True
})
# Returns diff to review

# Apply changes
result = await session.call_tool("edit_buffer", {
    "file": "src/models.py",
    "edits": [...],
    "preview": False,
    "save": True
})
```

**Implementation Notes**:
- Use Neovim's `nvim_buf_set_lines()` for atomic edits
- Trigger LSP `textDocument/didChange` events
- Validate file is open in buffer first
- Use `get_buffer_info` to check state before editing

---

#### `get_buffer_info`
Check buffer state before editing to avoid conflicts.

**Parameters**:
- `file` (string, required) - Path to file

**Returns**:
```python
{
  "is_open": true,
  "is_modified": false,
  "content": "full file content",
  "line_count": 150,
  "language": "python"
}
```

**Example**:
```python
info = await session.call_tool("get_buffer_info", {
    "file": "src/models.py"
})

if info["is_modified"]:
    # Buffer has unsaved changes
    pass
```

**Implementation Notes**:
- Query Neovim buffer state via `nvim_buf_get_lines()`
- Check modified flag: `vim.api.nvim_buf_get_option(bufnr, 'modified')`
- Return full content for verification

---

### 2. LSP Quick Fixes

**Why Critical**: `get_diagnostics` shows errors but can't fix them. LSP code actions are essential for auto-importing, applying suggested fixes, and quick refactorings.

#### `apply_code_action`
Apply LSP quick fixes and refactoring suggestions.

**Parameters**:
- `file` (string, required) - Path to file
- `line` (int, required) - Line number (1-indexed)
- `column` (int, required) - Column number (0-indexed)
- `action_kind` (string, optional) - Filter by action kind:
  - `"quickfix"` - Simple fixes (auto-import, typos)
  - `"refactor"` - Refactoring suggestions
  - `"source"` - Source actions (organize imports)
  - `null` - Show all available actions

**Returns**:
```python
{
  "actions": [
    {
      "title": "Import 'User' from models",
      "kind": "quickfix",
      "applied": false
    },
    {
      "title": "Add type annotation",
      "kind": "quickfix", 
      "applied": false
    }
  ],
  "selected_action": "Import 'User' from models",
  "changes_applied": true
}
```

**Behavior**:
- If multiple actions available, return list (let LLM choose)
- If single action matches `action_kind`, auto-apply
- Trigger LSP `textDocument/codeAction` request
- Apply workspace edits returned by LSP

**Example**:
```python
# Auto-import missing symbol
result = await session.call_tool("apply_code_action", {
    "file": "src/server.py",
    "line": 10,
    "column": 5,
    "action_kind": "quickfix"
})

# List all available actions
result = await session.call_tool("apply_code_action", {
    "file": "src/server.py", 
    "line": 10,
    "column": 5
})
# Returns list of actions for LLM to choose from
```

**Implementation Notes**:
- LSP method: `textDocument/codeAction`
- Apply edits via `vim.lsp.util.apply_workspace_edit()`
- Handle multi-file edits (workspace edits can span files)
- Some actions may require user confirmation (skip these or flag them)

---

## Medium Priority Tools (Significant Value)

These tools provide significant value for understanding and refactoring code, but aren't blocking basic workflows.

### 3. Advanced Navigation

**Why Useful**: Understanding code flow and relationships is essential for complex refactorings and debugging.

#### `get_call_hierarchy`
Find who calls a function and what functions it calls.

**Parameters**:
- `file` (string, required) - Path to file
- `line` (int, required) - Line number (1-indexed)
- `column` (int, required) - Column number (0-indexed)
- `direction` (string, default: "both") - Which direction to search:
  - `"incoming"` - Who calls this function
  - `"outgoing"` - What this function calls
  - `"both"` - Both directions

**Returns**:
```python
{
  "incoming_calls": [
    {
      "caller": "process_request",
      "file": "src/handlers.py",
      "line": 45,
      "call_sites": [
        {"line": 45, "column": 12, "context": "user = get_user(user_id)"}
      ]
    }
  ],
  "outgoing_calls": [
    {
      "callee": "db.query",
      "file": "src/database.py",
      "line": 23,
      "call_sites": [
        {"line": 67, "column": 8, "context": "return db.query(...)"}
      ]
    }
  ],
  "total_incoming": 3,
  "total_outgoing": 5
}
```

**Implementation Notes**:
- LSP methods: `callHierarchy/incomingCalls`, `callHierarchy/outgoingCalls`
- Requires LSP server support (pyright, tsserver, rust-analyzer support this)
- May need multiple LSP requests for deep hierarchies

---

#### `find_implementations`
Find concrete implementations of an interface or abstract class.

**Parameters**:
- `file` (string, required) - Path to file with interface/abstract class
- `line` (int, required) - Line number (1-indexed)
- `column` (int, required) - Column number (0-indexed)

**Returns**:
```python
{
  "interface": "UserRepository",
  "implementations": [
    {
      "name": "PostgresUserRepository",
      "file": "src/db/postgres.py",
      "line": 12,
      "signature": "class PostgresUserRepository(UserRepository):"
    },
    {
      "name": "MockUserRepository",
      "file": "tests/mocks.py",
      "line": 8,
      "signature": "class MockUserRepository(UserRepository):"
    }
  ],
  "total_count": 2
}
```

**Implementation Notes**:
- LSP method: `textDocument/implementation`
- Works for interfaces (TypeScript), protocols (Python), traits (Rust)
- Returns empty if symbol is not an interface

---

### 4. More Refactoring

**Why Useful**: Completes the refactoring toolkit for common code transformations.

#### `inline_function`
Inline a function call (reverse of extract_function).

**Parameters**:
- `file` (string, required) - Path to file with function to inline
- `line` (int, required) - Line number of function definition (1-indexed)
- `column` (int, required) - Column number (0-indexed)
- `preview` (boolean, default: true) - Preview changes before applying

**Returns**:
```python
{
  "preview": "unified diff",  # If preview=True
  "applied": false,
  "affected_files": ["src/models.py", "src/handlers.py"],
  "replacements_count": 5
}
```

**Behavior**:
- Replace all calls to function with function body
- Handle variable scoping correctly
- Update all callers across the project
- Preview shows unified diff of all changes

**Implementation Notes**:
- May require LSP code action support
- Manual implementation: find all references, replace with function body
- Handle edge cases (recursion, closures)

---

#### `move_symbol`
Move a class, function, or variable to another file.

**Parameters**:
- `file` (string, required) - Source file path
- `line` (int, required) - Line number of symbol (1-indexed)
- `column` (int, required) - Column number (0-indexed)
- `target_file` (string, required) - Destination file path
- `preview` (boolean, default: true) - Preview changes

**Returns**:
```python
{
  "preview": "unified diff",
  "applied": false,
  "symbol": "UserService",
  "source_file": "src/server.py",
  "target_file": "src/services/user.py",
  "import_updates": [
    {
      "file": "src/handlers.py",
      "old": "from server import UserService",
      "new": "from services.user import UserService"
    }
  ]
}
```

**Behavior**:
- Move symbol definition to target file
- Update all imports across project
- Preserve formatting and docstrings
- Handle circular dependencies

**Implementation Notes**:
- Combine `find_references`, `edit_buffer`, and import management
- May require custom logic per language
- Check for circular imports before applying

---

#### `organize_imports`
Remove unused imports and sort import statements.

**Parameters**:
- `file` (string, required) - Path to file
- `preview` (boolean, default: true) - Preview changes

**Returns**:
```python
{
  "preview": "unified diff",
  "applied": false,
  "removed_imports": ["unused_module", "old_function"],
  "sorted": true
}
```

**Behavior**:
- Remove unused imports
- Sort imports alphabetically
- Group by category (standard lib, third-party, local)
- Language-specific formatting

**Implementation Notes**:
- LSP code action: `source.organizeImports`
- Python: isort-style grouping
- JavaScript: ESLint/Prettier style
- Rust: rustfmt style

---

### 5. External Information Access

**Why Useful**: AI agents often need to look up documentation, API references, library usage examples, and current best practices that aren't available in the local codebase.

#### `web_search`
Search the web using natural language queries.

**Parameters**:
- `query` (string, required) - Natural language search query
- `max_results` (int, default: 5) - Maximum number of results to return

**Returns**:
```python
{
  "query": "how to use async/await in Python",
  "results": [
    {
      "title": "Async IO in Python: A Complete Walkthrough",
      "url": "https://realpython.com/async-io-python/",
      "snippet": "A comprehensive guide to asynchronous programming in Python using async/await syntax...",
      "relevance_score": 0.95
    },
    {
      "title": "Python asyncio documentation",
      "url": "https://docs.python.org/3/library/asyncio.html",
      "snippet": "Official documentation for Python's asyncio library...",
      "relevance_score": 0.92
    }
  ],
  "total_results": 2
}
```

**Behavior**:
- Perform web search using the provided query
- Return ranked results with titles, URLs, and snippets
- Filter for programming-related content when appropriate
- Handle rate limiting gracefully

**Example**:
```python
# Search for library documentation
result = await session.call_tool("web_search", {
    "query": "FastAPI authentication best practices",
    "max_results": 3
})

# Search for error message solutions
result = await session.call_tool("web_search", {
    "query": "Python ModuleNotFoundError: No module named 'pydantic'",
    "max_results": 5
})
```

**Implementation Notes**:
- Use a search API (DuckDuckGo, Brave Search, or similar)
- Consider caching results for common queries
- Rate limit to avoid API abuse
- Prioritize official documentation and reputable sources

---

## Low Priority Tools (Polish)

Nice-to-have tools that improve the developer experience but aren't essential.

### 6. Additional Intelligence

#### `get_signature_help`
Get parameter hints for function calls.

**Parameters**:
- `file` (string, required) - Path to file
- `line` (int, required) - Line number (1-indexed)
- `column` (int, required) - Column number (0-indexed)

**Returns**:
```python
{
  "signatures": [
    {
      "label": "process_user(user_id: int, validate: bool = True) -> User",
      "parameters": [
        {"label": "user_id", "type": "int", "documentation": "User ID to process"},
        {"label": "validate", "type": "bool", "documentation": "Whether to validate"}
      ],
      "active_parameter": 0,  # Which parameter cursor is on
      "documentation": "Process a user by ID..."
    }
  ],
  "active_signature": 0
}
```

**Implementation Notes**:
- LSP method: `textDocument/signatureHelp`
- Triggered when cursor is inside function call parentheses
- Shows which parameter user is currently typing

---

#### `get_type_hierarchy`
Show inheritance tree (supertypes and subtypes).

**Parameters**:
- `file` (string, required) - Path to file
- `line` (int, required) - Line number (1-indexed)
- `column` (int, required) - Column number (0-indexed)
- `direction` (string, default: "both") - Direction to traverse:
  - `"supertypes"` - Parent classes/interfaces
  - `"subtypes"` - Child classes/implementations
  - `"both"` - Full hierarchy

**Returns**:
```python
{
  "supertypes": [
    {"name": "BaseRepository", "file": "src/base.py", "line": 10},
    {"name": "object", "file": "<builtin>", "line": 0}
  ],
  "subtypes": [
    {"name": "PostgresRepository", "file": "src/postgres.py", "line": 15}
  ],
  "current_type": "UserRepository"
}
```

**Implementation Notes**:
- LSP methods: `typeHierarchy/supertypes`, `typeHierarchy/subtypes`
- Not all LSP servers support this (newer feature)
- Fallback: use `find_definition` + `find_implementations`

---

#### `change_signature`
Update function signature and all call sites.

**Parameters**:
- `file` (string, required) - Path to file with function
- `line` (int, required) - Line number of function (1-indexed)
- `column` (int, required) - Column number (0-indexed)
- `new_params` (array, required) - New parameter list:
  - `name` (string) - Parameter name
  - `type` (string, optional) - Type annotation
  - `default` (string, optional) - Default value
- `preview` (boolean, default: true) - Preview changes

**Returns**:
```python
{
  "preview": "unified diff",
  "applied": false,
  "function": "process_user",
  "old_signature": "def process_user(user_id: int)",
  "new_signature": "def process_user(user_id: int, validate: bool = True)",
  "call_sites_updated": 12
}
```

**Behavior**:
- Update function definition
- Update all call sites to match new signature
- Add default values where needed
- Preserve existing arguments

**Implementation Notes**:
- Complex refactoring requiring deep analysis
- May be LSP code action in some servers
- Manual implementation needs careful handling of optional params

---

### 7. Helper Utilities

#### `replace_in_buffer`
Simple string replace wrapper around `edit_buffer`.

**Parameters**:
- `file` (string, required) - Path to file
- `old` (string, required) - Text to find
- `new` (string, required) - Replacement text
- `preview` (boolean, default: true) - Preview changes

**Returns**:
```python
{
  "preview": "unified diff",
  "applied": false,
  "matches_found": 3,
  "matches_replaced": 3
}
```

**Behavior**:
- Find all occurrences of `old` in file
- Replace with `new`
- Return preview or apply changes
- Simple text replacement (not symbol-aware)

**Implementation Notes**:
- Wrapper around `edit_buffer`
- For simple text replacements only
- Use `rename_symbol` for semantic renames

---

## Out of Scope (Terminal is Better)

These features are **explicitly excluded** from Otter's scope. AI agents should use terminal commands directly for these operations.

### ❌ File Operations
- `write_file` → Use `echo`, `cat`, or text editors
- `delete_file` → Use `rm`
- `move_file` → Use `mv`
- `create_directory` → Use `mkdir`
- `copy_file` → Use `cp`

**Rationale**: Shell commands are simpler, more powerful, and universally available.

---

### ❌ Text Search
- `search_text` → Use `rg` (ripgrep)
- `grep` → Use `grep` or `rg`
- `find_files` → Use `find` or `fd`

**Rationale**: Existing tools are faster and more feature-complete. LSP handles semantic search.

---

### ❌ Git Operations
- `git_diff` → Use `git diff`
- `git_stash` → Use `git stash`
- `git_commit` → Use `git commit`
- `git_blame` → Use `git blame`

**Rationale**: Git CLI is comprehensive and well-understood. No need to wrap it.

---

### ❌ Test Running
- `run_tests` → Use `pytest`, `cargo test`, `npm test`
- `run_test_file` → Use test runners directly
- `debug_test` → Use debugger + test runner

**Rationale**: Test frameworks have rich CLIs. Otter provides debugging, not test execution.

---

### ❌ Code Formatting
- `format_file` → Use `black`, `prettier`, `rustfmt`
- `format_buffer` → Use formatters via terminal

**Rationale**: Formatters are designed to run in pipelines. Just call them directly.

---

### ❌ Build/Deploy
- `build_project` → Use `make`, `npm run build`, `cargo build`
- `deploy` → Use deployment tools
- `install_dependencies` → Use `pip`, `npm install`, `cargo add`

**Rationale**: Build systems are too diverse. Agents have shell access.

---

## Implementation Summary

### By Priority

**High Priority (Must Have)**: 3 tools
- `edit_buffer` - Core editing primitive
- `get_buffer_info` - Buffer state queries
- `apply_code_action` - LSP quick fixes

**Medium Priority (Should Have)**: 6 tools
- `get_call_hierarchy` - Function call graphs
- `find_implementations` - Interface → implementations
- `inline_function` - Inline refactoring
- `move_symbol` - Move between files
- `organize_imports` - Import management
- `web_search` - Natural language web search

**Low Priority (Nice to Have)**: 4 tools
- `get_signature_help` - Parameter hints
- `get_type_hierarchy` - Inheritance trees
- `change_signature` - Update function signatures
- `replace_in_buffer` - Simple text replacement

**Total New Tools**: 13

---

### Implementation Order

**Phase 1 (Critical)** - Estimated 2-3 days
1. `edit_buffer` - Core functionality
2. `get_buffer_info` - Supporting tool
3. `apply_code_action` - LSP integration

**Phase 2 (High Value)** - Estimated 3-4 days
4. `get_call_hierarchy` - Advanced navigation
5. `find_implementations` - Interface resolution
6. `organize_imports` - Quick win refactoring
7. `web_search` - External information access

**Phase 3 (Complete Toolkit)** - Estimated 4-5 days
8. `inline_function` - Refactoring
9. `move_symbol` - Complex refactoring
10. `get_signature_help` - Intelligence

**Phase 4 (Polish)** - Estimated 2-3 days
11. `get_type_hierarchy` - Additional navigation
12. `change_signature` - Advanced refactoring
13. `replace_in_buffer` - Utility wrapper

**Total Estimated Time**: 11-15 days

---

## Key Principle

> **Otter focuses on LSP/DAP-powered semantic operations. Shell/terminal handles everything else.**

This keeps Otter focused, maintainable, and aligned with its core value proposition: providing AI agents with semantic code intelligence they cannot easily get from shell commands.

---

## Next Steps

1. ✅ Document planned tools (this document)
2. ⬜ Implement Phase 1 (high priority tools)
3. ⬜ Write comprehensive tests for new tools
4. ⬜ Update USER_GUIDE.md with new tool documentation
5. ⬜ Evaluate Phase 2 priority based on user feedback

---

**Last Updated**: October 1, 2025

