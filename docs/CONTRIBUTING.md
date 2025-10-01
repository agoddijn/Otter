# Contributing

## Core Principles

1. **Wrapper, Not Reimplementer** - Use TreeSitter/LSP/DAP, don't reimplement them
2. **Language-Agnostic** - Zero per-language code, protocol-based
3. **Type-Safe** - Mypy strict mode, dataclasses everywhere
4. **Code is Documentation** - Write good docstrings, they generate the docs

## Setup

```bash
git clone <repository-url>
cd otter
make check-deps && make install-deps
make install
make test
```

## Development Workflow

```bash
make dev              # Run with MCP inspector
make test             # Run all tests
make lint             # Check code
make docs             # View documentation
```

## Code Patterns

### Services Must Use Neovim for Semantic Operations

```python
class NavigationService:
    def __init__(self, nvim_client: NeovimClient, project_path: str):
        self.nvim_client = nvim_client  # Required for LSP/DAP

class WorkspaceService:
    def __init__(self, project_path: str, nvim_client: Optional[NeovimClient] = None):
        self.nvim_client = nvim_client  # Optional for file ops
```

### Always Use Centralized Path Utilities

```python
from otter.utils.path import resolve_workspace_path, normalize_path_for_response

# Input paths
file_path = resolve_workspace_path(path, self.project_path)

# Output paths  
normalized = normalize_path_for_response(file_path, self.project_path)
```

### Wrap All pynvim Calls in Executor

```python
import asyncio

loop = asyncio.get_event_loop()
await loop.run_in_executor(None, lambda: self.nvim.command("edit file.py"))
```

### LSP Integration via Lua

```python
lua_code = f"""
local result = vim.lsp.buf_request_sync(
    {buf_num},
    'textDocument/definition',
    params,
    2000
)
return result
"""
result = await nvim_client.execute_lua(lua_code)
```

### Remember: LSP is 0-indexed, Users Expect 1-indexed

```python
# To LSP
lsp_result = await client.lsp_definition(file, line - 1, col)

# From LSP
return Definition(line=lsp_result.line + 1)
```

## Testing

### Write Parameterized Tests

Tests automatically run for Python, JavaScript, and Rust:

```python
from tests.fixtures.language_configs import LanguageTestConfig

async def test_feature(
    self, service, temp_language_project, language_config: LanguageTestConfig
):
    ext = language_config.file_extension
    result = await service.do_something(
        file=str(temp_language_project / f"models{ext}")
    )
    assert result is not None, f"Failed for {language_config.language}"
```

### For Debugging Tests, Use DebugTestHelper

Never use `asyncio.sleep()`. Use polling with exponential backoff:

```python
from tests.helpers.debug_helpers import DebugTestHelper

helper = DebugTestHelper(ide_server)
await helper.start_debug_and_wait(file, breakpoints, expected_status="paused")
await helper.step_and_verify("step_over")
```

## Documentation Guidelines

### Update Existing Docs, Don't Create New Ones

**Code → Auto-generated docs:**
- Write good docstrings → API reference auto-updates
- Add type hints → Parameters auto-documented

**Manual updates:**
- Feature: Update `USER_GUIDE.md` examples + `CHANGELOG.md`
- Pattern: Update `CONTRIBUTING.md` (this file)
- Design: Update `ARCHITECTURE.md`

**Never create:**
- Completion reports ("X_COMPLETE.md")
- Analysis documents ("X_ANALYSIS.md")  
- Implementation notes ("X_IMPL.md")

**For temporary work:**
```bash
mkdir tmp  # gitignored
# Work in tmp/, extract to proper docs before PR
```

### Documentation Structure

10 core documents:
- `README.md` - Overview
- `docs/USER_GUIDE.md` - Quick reference (points to auto-docs)
- `docs/DEPENDENCIES.md` - System requirements
- `docs/CONTRIBUTING.md` - This file
- `docs/ARCHITECTURE.md` - High-level design
- `docs/TECHNICAL_GUIDE.md` - Neovim integration
- `tests/TESTING.md` - Testing guide
- `tests/QUICK_START.md` - Test cheat sheet
- `docs/README.md` - Documentation index
- `CHANGELOG.md` - Version history

Plus auto-generated API docs in `docs_site/` (run `make docs`).

## Adding New Features

1. Implement in appropriate service with docstrings
2. Add to MCP server (`src/otter/mcp_server.py`)
3. Write parameterized integration tests
4. Add example to `USER_GUIDE.md`
5. Add entry to `CHANGELOG.md`
6. Run `make docs` to verify API docs updated

## Pull Requests

**Before submitting:**
```bash
make lint       # Zero errors
make test       # All passing
mypy src/       # Zero errors
make docs       # Verify docs build
```

**PR checklist:**
- [ ] Tests pass
- [ ] Docstrings complete
- [ ] CHANGELOG.md updated
- [ ] No new documentation files created

## Common Gotchas

- **macOS symlinks**: Use `resolve_workspace_path()` (handles `/var` → `/private/var`)
- **LSP timing**: Wait 1-2 seconds after opening file for analysis
- **Type variations**: Accept `["class", "struct"]` for Rust compatibility
- **Naming conventions**: Handle `snake_case` vs `camelCase`

## Questions?

- Check auto-generated docs: `make docs`
- Read code docstrings: They're the source of truth
- See `docs/ARCHITECTURE.md` for design decisions
- See `tests/TESTING.md` for testing patterns
