# Tests

Comprehensive test suite for the CLI IDE project.

## Structure

```
tests/
├── conftest.py          # Shared pytest fixtures
├── unit/                # Unit tests for individual components
│   └── test_workspace.py
├── integration/         # Integration tests for end-to-end flows
└── fixtures/            # Test data and fixtures
```

## Running Tests

### All tests
```bash
make test
```

### Unit tests only
```bash
make test-unit
```

### Integration tests only
```bash
make test-integration
```

### With coverage report
```bash
make test-coverage
```

### Watch mode (auto-rerun on file changes)
```bash
make test-watch
```

## Writing Tests

### Unit Tests

Unit tests should:
- Test individual functions/methods in isolation
- Use mocked dependencies
- Be fast and deterministic
- Live in `tests/unit/`

Example:
```python
import pytest
from cli_ide.services.workspace import WorkspaceService

class TestWorkspaceService:
    @pytest.mark.asyncio
    async def test_get_project_structure(self, temp_project_dir):
        workspace = WorkspaceService(project_path=str(temp_project_dir))
        result = await workspace.get_project_structure()
        assert result.root == str(temp_project_dir.resolve())
```

### Integration Tests

Integration tests should:
- Test multiple components working together
- Use real dependencies when practical
- Test actual MCP server responses
- Live in `tests/integration/`

Example:
```python
import pytest
from mcp import ClientSession
from mcp.client.stdio import stdio_client

@pytest.mark.asyncio
async def test_mcp_tool_get_project_structure():
    # Test actual MCP server communication
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            result = await session.call_tool("get_project_structure", {})
            assert result.content
```

## Fixtures

### Available Fixtures

#### `temp_project_dir`
Creates a temporary project directory with a realistic structure:
```
temp_dir/
    src/
        main.py
        utils/
            helper.py
    tests/
        test_main.py
    README.md
    .gitignore
```

Usage:
```python
async def test_something(temp_project_dir: Path):
    # temp_project_dir is automatically created and cleaned up
    assert temp_project_dir.exists()
```

#### `empty_project_dir`
Creates an empty temporary directory for testing edge cases.

## Coverage

After running `make test-coverage`, view the HTML coverage report:
```bash
open htmlcov/index.html
```

## Best Practices

1. **Descriptive test names**: Use clear, descriptive names that explain what is being tested
2. **One assertion per test**: Keep tests focused on a single behavior
3. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification
4. **Use fixtures**: Leverage shared fixtures to avoid code duplication
5. **Mark slow tests**: Use `@pytest.mark.slow` for tests that take > 1 second
6. **Async tests**: Use `@pytest.mark.asyncio` for async functions

## Current Coverage

- ✅ `get_project_structure` - 10 tests, full coverage
- ⏳ More tests coming as we implement features...
