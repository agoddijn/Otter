# Contributing to Otter

Thank you for your interest in contributing to Otter! This guide will help you get started.

## Core Principles

1. **LSP/DAP First** - Leverage Neovim's LSP and DAP, don't reimplement them
2. **Language-Agnostic** - Zero per-language code, protocol-based
3. **Type-Safe** - Mypy strict mode, dataclasses everywhere
4. **Code is Documentation** - The code explains itself; docs answer "What/Why/How"

## Quick Setup

```bash
# Clone and setup
git clone https://github.com/your-org/otter.git
cd otter

# Check system dependencies
make check-deps

# Install dependencies
make install

# Run tests to verify
make test
```

### System Requirements

- Python 3.12+
- Neovim 0.9+
- Node.js 16+
- Git

See [GETTING_STARTED.md](./GETTING_STARTED.md) for detailed installation instructions.

## Development Workflow

```bash
# Development
make dev                    # Run with MCP inspector
make dev PROJECT=/path      # Test with specific project

# Testing
make test                   # Run all tests
make test-unit             # Unit tests only
make test-integration      # Integration tests only
make test-coverage         # With coverage report

# Code quality
make lint                  # Run linters
make format                # Format code
mypy src/                  # Type checking
```

## Code Patterns

### Service Layer Architecture

All services follow this pattern:

```python
class NavigationService:
    def __init__(self, nvim_client: NeovimClient, project_path: str):
        self.nvim_client = nvim_client  # LSP/DAP access
        self.project_path = project_path
    
    async def find_definition(
        self, 
        symbol: str,
        file: str,
        line: int
    ) -> Optional[Definition]:
        """Find symbol definition via LSP."""
        # Implementation uses nvim_client for LSP
        pass
```

### Path Handling

Always use centralized path utilities:

```python
from otter.utils.path import resolve_workspace_path, normalize_path_for_response

# Input: Handle relative/absolute paths
file_path = resolve_workspace_path(path, self.project_path)

# Output: Return absolute paths
return Definition(
    file=str(file_path.resolve()),  # Absolute path
    line=result.line + 1            # 1-indexed for users
)
```

**Important**: LSP uses 0-indexed lines/columns, but users expect 1-indexed.

### Async Operations

All Neovim RPC calls must run in executor:

```python
import asyncio

loop = asyncio.get_event_loop()

# Wrap synchronous pynvim calls
result = await loop.run_in_executor(
    None,
    lambda: self.nvim.command("edit file.py")
)
```

### LSP Integration via Lua

Use Lua for LSP operations:

```python
lua_code = f"""
local bufnr = {buf_num}
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

## Testing

### Writing Tests

Otter uses **parameterized tests** that run against multiple languages:

```python
from tests.fixtures.language_configs import LanguageTestConfig

async def test_find_definition(
    self,
    navigation_service,
    temp_language_project,
    language_config: LanguageTestConfig
):
    """Test runs for Python, JavaScript, and Rust automatically."""
    ext = language_config.file_extension
    
    result = await navigation_service.find_definition(
        symbol="MyClass",
        file=str(temp_language_project / f"models{ext}"),
        line=10
    )
    
    assert result is not None, f"Failed for {language_config.language}"
    assert result.line > 0
```

### Debugging Tests

Use `DebugTestHelper` for DAP tests - **never use `asyncio.sleep()`**:

```python
from tests.helpers.debug_helpers import DebugTestHelper

helper = DebugTestHelper(ide_server)

# Wait for state with exponential backoff
await helper.start_debug_and_wait(
    file="test.py",
    breakpoints=[10, 25],
    expected_status="paused"
)

# Step and verify
await helper.step_and_verify("step_over")
```

### Test Organization

```
tests/
├── unit/           # Fast, isolated tests
├── integration/    # Full LSP/DAP integration tests
├── fixtures/       # Test data and configs
└── helpers/        # Test utilities
```

## Adding New Features

1. **Implement in service** with comprehensive docstrings
2. **Add to MCP server** (`src/otter/mcp_server.py`)
3. **Write parameterized tests** (all supported languages)
4. **Update CHANGELOG.md** with changes
5. **Update documentation** if needed

Example:

```python
# 1. In service
async def find_references(
    self,
    symbol: str,
    file: str,
    line: int
) -> List[Reference]:
    """Find all references to a symbol.
    
    Args:
        symbol: Symbol name to search for
        file: File containing the symbol
        line: Line number (1-indexed)
    
    Returns:
        List of Reference objects with file, line, column
    """
    # Implementation...
    pass

# 2. In mcp_server.py
@mcp.tool()
async def find_references(
    symbol: str,
    file: str,
    line: int
) -> List[dict]:
    """Find all references to a symbol."""
    result = await navigation_service.find_references(
        symbol=symbol,
        file=file,
        line=line
    )
    return [asdict(ref) for ref in result]

# 3. In tests/integration/test_navigation_find_references.py
async def test_find_references(
    self,
    navigation_service,
    temp_language_project,
    language_config
):
    # Test implementation...
    pass
```

## Documentation

### What Gets Documented

Otter follows a **lean documentation philosophy**:

- ✅ **What is Otter?** - Philosophy, design, architecture
- ✅ **Why Otter?** - Use cases, value proposition
- ✅ **How to use Otter?** - Installation, setup, configuration
- ❌ **NOT code details** - Code should be self-documenting

### Documentation Structure

```
docs/
├── README.md           # What is Otter?
├── WHY.md              # Why Otter?
├── GETTING_STARTED.md  # How to use?
├── CONFIGURATION.md    # Config reference
├── ARCHITECTURE.md     # High-level design
└── CONTRIBUTING.md     # This file
```

### When to Update Docs

- **New feature**: Update CHANGELOG.md
- **Config option**: Update CONFIGURATION.md with example
- **Architecture change**: Update ARCHITECTURE.md (high-level only)
- **Breaking change**: Update CHANGELOG.md with migration guide

**Never**:
- Create implementation notes or analysis docs
- Document code that should be self-documenting
- Create temporary planning docs (use `tmp/` directory, gitignored)

## Pull Requests

### Before Submitting

```bash
# Verify everything works
make lint              # Zero errors
make test              # All tests pass
mypy src/              # Zero type errors

# Check documentation builds
make docs              # If we have auto-generated docs
```

### PR Checklist

- [ ] Tests pass (`make test`)
- [ ] New tests added for new features
- [ ] Tests updated if API changed
- [ ] Type hints complete (mypy passes)
- [ ] CHANGELOG.md updated
- [ ] Documentation updated if needed (sparingly)
- [ ] No unnecessary new files created

### PR Description Template

```markdown
## What

Brief description of changes

## Why

Why this change is needed

## Testing

How you tested this:
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Tested manually with [language]

## Breaking Changes

List any breaking changes and migration path
```

## Common Gotchas

- **macOS symlinks**: Use `resolve_workspace_path()` (handles `/var` → `/private/var`)
- **LSP timing**: Wait 1-2 seconds after opening file for LSP analysis
- **LSP indexing**: Lines/columns are 0-indexed in LSP, 1-indexed for users
- **Path resolution**: Always use absolute paths in responses
- **Async boundaries**: All pynvim calls need `run_in_executor`
- **Type variations**: Accept `["class", "struct"]` for cross-language compatibility

## Getting Help

- **Documentation**: Read [docs/README.md](./README.md) first
- **Examples**: Check [examples/](../examples/) for configurations
- **Tests**: Look at existing tests for patterns
- **Issues**: [GitHub Issues](https://github.com/your-org/otter/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/otter/discussions)

## Code of Conduct

We follow standard open source etiquette:

- Be respectful and constructive
- Focus on what is best for the project
- Assume good intentions
- Accept constructive criticism gracefully

## License

By contributing to Otter, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Otter! 🦦
