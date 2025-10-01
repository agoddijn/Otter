# Testing Guide

Complete guide for testing Otter - from running tests to writing new ones.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Writing Tests](#writing-tests)
5. [Language-Agnostic Testing](#language-agnostic-testing)
6. [Debug Test Framework](#debug-test-framework)
7. [Best Practices](#best-practices)

---

## Quick Start

### Run All Tests

```bash
make test
```

### Run Specific Test Suite

```bash
# Unit tests only (fast, mocked)
make test-unit

# Integration tests only (slower, real Neovim + LSP)
make test-integration

# With coverage report
make test-coverage
```

### Run Tests for Specific Language

```bash
# Python only
pytest tests/integration/ -k "python"

# JavaScript only
pytest tests/integration/ -k "javascript"

# Rust only
pytest tests/integration/ -k "rust"
```

### Run Single Test File

```bash
pytest tests/integration/test_navigation_find_definition.py -v
```

---

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures (auto-parameterization)
├── unit/                    # Unit tests (mocked, fast)
│   ├── test_workspace.py
│   └── test_workspace_diagnostics.py
├── integration/             # Integration tests (real Neovim + LSP)
│   ├── test_navigation_*.py
│   ├── test_workspace_*.py
│   ├── test_debugging_*.py
│   └── test_refactoring_*.py
├── fixtures/                # Test data and configurations
│   ├── language_configs.py  # Language-specific test data
│   └── projects/            # Mini test projects per language
│       ├── python/
│       ├── javascript/
│       └── rust/
└── helpers/                 # Test utilities
    └── debug_helpers.py     # Debug test framework
```

---

## Running Tests

### All Tests

```bash
# Via make (recommended)
make test

# Via pytest directly
pytest tests/
```

### By Test Type

```bash
# Unit tests (fast, ~1 second)
make test-unit
pytest tests/unit/

# Integration tests (slower, ~2 minutes)
make test-integration
pytest tests/integration/
```

### By Language

All integration tests are parameterized across Python, JavaScript, and Rust:

```bash
# Python tests only
pytest tests/integration/ -k "python"

# JavaScript tests only
pytest tests/integration/ -k "javascript"

# Rust tests only
pytest tests/integration/ -k "rust"
```

### By Feature

```bash
# Navigation tests
pytest tests/integration/test_navigation_*.py

# Debugging tests
pytest tests/integration/test_debugging_*.py

# Workspace tests
pytest tests/integration/test_workspace_*.py

# Refactoring tests
pytest tests/integration/test_refactoring_*.py
```

### Specific Test

```bash
# Single test method
pytest tests/integration/test_navigation_find_definition.py::TestFindDefinitionParameterized::test_find_class_definition

# This runs the test for all 3 languages
```

### With Verbose Output

```bash
# Show test names as they run
pytest tests/ -v

# Show print statements
pytest tests/ -s

# Both
pytest tests/ -vs
```

### With Coverage

```bash
# Generate coverage report
make test-coverage

# View HTML report
open htmlcov/index.html
```

### Watch Mode

```bash
# Auto-rerun tests when files change
make test-watch
```

---

## Writing Tests

### Unit Tests

Unit tests should:
- Test individual functions/methods in isolation
- Use mocked dependencies
- Be fast (<1 second)
- Live in `tests/unit/`

**Example:**

```python
import pytest
from otter.services.workspace import WorkspaceService


@pytest.mark.asyncio
async def test_get_project_structure(temp_project_dir):
    """Test project structure without Neovim."""
    workspace = WorkspaceService(project_path=str(temp_project_dir))
    
    result = await workspace.get_project_structure()
    
    assert result.root == str(temp_project_dir.resolve())
    assert len(result.tree) > 0
```

### Integration Tests

Integration tests should:
- Test multiple components working together
- Use real Neovim + LSP servers
- Test actual behavior, not mocks
- Live in `tests/integration/`
- Be parameterized across languages

**Example:**

```python
import pytest
from otter.neovim.client import NeovimClient
from otter.services.navigation import NavigationService
from tests.fixtures.language_configs import LanguageTestConfig


@pytest.mark.asyncio
class TestNavigationParameterized:
    """Language-agnostic navigation tests."""

    @pytest.fixture
    async def navigation_service(
        self, temp_language_project, language_config: LanguageTestConfig
    ):
        """Create service with real Neovim."""
        nvim_client = NeovimClient(project_path=str(temp_language_project))
        service = NavigationService(nvim_client=nvim_client)

        await nvim_client.start()
        import asyncio
        await asyncio.sleep(2)  # Wait for LSP

        yield service
        await nvim_client.stop()

    async def test_find_definition(
        self, navigation_service, temp_language_project, language_config: LanguageTestConfig
    ):
        """Test finding definitions across all languages."""
        ext = language_config.file_extension
        
        result = await navigation_service.find_definition(
            symbol="User",
            file=str(temp_language_project / f"main{ext}"),
            line=2,
        )
        
        assert result.symbol_name == "User", \
            f"Expected User for {language_config.language}"
        assert result.symbol_type in ["class", "struct"], \
            f"Expected class/struct for {language_config.language}"
```

---

## Language-Agnostic Testing

Otter uses **parameterized testing** to automatically run tests across Python, JavaScript, and Rust.

### How It Works

When you add `language_config: LanguageTestConfig` parameter to a test, pytest automatically:
1. Creates 3 test variants (Python, JavaScript, Rust)
2. Sets up language-specific test projects
3. Runs each variant independently

**Example:**

```python
async def test_my_feature(
    self, my_service, temp_language_project, language_config: LanguageTestConfig
):
    """This test automatically runs 3 times (Python, JS, Rust)."""
    ext = language_config.file_extension
    
    result = await my_service.do_something(
        file=str(temp_language_project / f"models{ext}")
    )
    
    assert result is not None, \
        f"Failed for {language_config.language}"
```

Pytest generates:
- `test_my_feature[python]` ✓
- `test_my_feature[javascript]` ✓
- `test_my_feature[rust]` ✓

### Available Fixtures

#### `language_config`

Provides language-specific configuration:

```python
language_config.language         # "python" | "javascript" | "rust"
language_config.file_extension   # ".py" | ".js" | ".rs"
language_config.lsp_server       # "pyright" | "tsserver" | "rust-analyzer"
language_config.expected_classes # ["User", "UserService"]
language_config.symbol_locations # {"User": SymbolLocation(...)}
```

#### `temp_language_project`

Creates a temporary project with language-specific test files:

```python
# For Python: models.py, services.py, main.py
# For JavaScript: models.js, services.js, main.js, package.json
# For Rust: models.rs, services.rs, main.rs, Cargo.toml
temp_language_project / f"models{language_config.file_extension}"
```

### Handling Language Differences

#### Naming Conventions

```python
# Python/Rust use snake_case, JavaScript uses camelCase
func_name = "create_user" if language_config.language != "javascript" else "createUser"
```

#### Type Names

```python
# Python/JS use "class", Rust uses "struct"
assert result.symbol_type in ["class", "struct"], \
    f"Expected class/struct for {language_config.language}"
```

#### Symbol Locations

```python
# Use predefined locations from config
user_loc = language_config.symbol_locations["User"]
result = await service.find_definition(
    symbol="User",
    file=str(temp_language_project / f"{user_loc.file}{ext}"),
    line=user_loc.line
)
```

### Adding Tests for New Language

To add a new language (e.g., Go):

1. **Update `tests/fixtures/language_configs.py`**:

```python
GO_CONFIG = LanguageTestConfig(
    language="go",
    file_extension=".go",
    lsp_server="gopls",
    models_file_content='''
    package main
    
    type User struct {
        Name string
    }
    ''',
    # ... more config
)

LANGUAGE_CONFIGS["go"] = GO_CONFIG
```

2. **Create test project** in `tests/fixtures/projects/go/`

3. **All existing tests now run for Go automatically!** ✅

---

## Debug Test Framework

### Overview

Debugging tests require special handling due to async distributed system timing. We use a custom framework with **exponential backoff polling** and **state verification**.

### Available in `tests/helpers/debug_helpers.py`

```python
from tests.helpers.debug_helpers import DebugTestHelper

helper = DebugTestHelper(ide_server)
```

### Key Methods

#### `wait_for_state(expected_status, timeout=10.0)`

Poll until debugger reaches expected state:

```python
await helper.wait_for_state("paused", timeout=10.0)
```

#### `start_debug_and_wait(file, breakpoints, expected_status)`

Start debug session and wait for specific state:

```python
await helper.start_debug_and_wait(
    file="test.py",
    breakpoints=[42],
    expected_status="paused"
)
```

#### `continue_and_wait_for_breakpoint(timeout=5.0)`

Continue execution and wait for next breakpoint:

```python
await helper.continue_and_wait_for_breakpoint(timeout=5.0)
```

#### `step_and_verify(action, timeout=3.0)`

Step through code and verify state:

```python
await helper.step_and_verify("step_over", timeout=3.0)
```

### Why Not Use `asyncio.sleep()`?

**Problem**: Fixed delays are unreliable in distributed systems

```python
# ❌ BAD: May be too short or too long
await start_debug_session(file, breakpoints=[10])
await asyncio.sleep(0.5)  # Hope it's paused?
await control_execution("step_over")
```

**Solution**: Poll for actual state

```python
# ✅ GOOD: Verify state before proceeding
await helper.start_debug_and_wait(
    file, breakpoints=[10],
    expected_status="paused"  # Waits until actually paused
)
await helper.step_and_verify("step_over")
```

### Example Debug Test

```python
@pytest.mark.asyncio
class TestDebugging:
    """Debug tests using helper framework."""
    
    async def test_step_through_code(self, ide_server):
        """Test stepping through code."""
        helper = DebugTestHelper(ide_server)
        
        # Start and wait for paused state
        await helper.start_debug_and_wait(
            file="simple.py",
            breakpoints=[5],
            expected_status="paused"
        )
        
        # Step and verify
        await helper.step_and_verify("step_over")
        
        # Continue and wait for next breakpoint
        await helper.continue_and_wait_for_breakpoint()
        
        # Inspect state
        state = await ide_server.inspect_state()
        assert len(state.stack_frames) > 0
```

### Error Messages

The framework provides clear diagnostics:

```
TimeoutError: Timeout waiting for state 'paused' during start_debug_session(test.py).
Attempts: 10, Elapsed: 6.94s, Final state: status=running
```

This immediately shows:
- What was expected ("paused")
- What was found ("running")
- How many attempts were made
- How long it took

---

## Best Practices

### 1. Descriptive Test Names

```python
# ✅ GOOD: Clear what's being tested
async def test_find_definition_for_class_in_different_file(self):
    ...

# ❌ BAD: Unclear
async def test_find(self):
    ...
```

### 2. One Assertion Per Test

```python
# ✅ GOOD: Focused test
async def test_returns_correct_line_number(self):
    result = await service.find_definition("User", "main.py", 1)
    assert result.line == 5

async def test_returns_correct_file(self):
    result = await service.find_definition("User", "main.py", 1)
    assert result.file == "models.py"

# ❌ BAD: Multiple concerns
async def test_find_definition(self):
    result = await service.find_definition("User", "main.py", 1)
    assert result.line == 5
    assert result.file == "models.py"
    assert result.symbol_type == "class"
    # ... 10 more assertions
```

### 3. Arrange-Act-Assert Pattern

```python
async def test_feature(self):
    # Arrange: Set up test data
    file = str(temp_project / "main.py")
    symbol = "User"
    
    # Act: Perform the action
    result = await service.find_definition(symbol, file, 1)
    
    # Assert: Verify outcome
    assert result.symbol_name == "User"
```

### 4. Use Fixtures

```python
# ✅ GOOD: Shared setup via fixture
@pytest.fixture
async def navigation_service(temp_project):
    nvim = NeovimClient(project_path=str(temp_project))
    service = NavigationService(nvim_client=nvim)
    await nvim.start()
    yield service
    await nvim.stop()

async def test_feature_a(navigation_service):
    result = await navigation_service.find_definition(...)

async def test_feature_b(navigation_service):
    result = await navigation_service.find_references(...)
```

### 5. Add Language Context to Assertions

```python
# ✅ GOOD: Clear which language failed
assert result is not None, \
    f"Expected result for {language_config.language}"

# ❌ BAD: No context
assert result is not None
```

### 6. Handle Type Variations

```python
# ✅ GOOD: Accept multiple valid types
assert result.symbol_type in ["class", "struct", "interface"], \
    f"Unexpected type for {language_config.language}"

# ❌ BAD: Too restrictive
assert result.symbol_type == "class"
```

### 7. Wait for LSP Initialization

```python
# ✅ GOOD: Give LSP time to analyze
await nvim_client.start()
await asyncio.sleep(2)  # Critical for reliable tests

# ❌ BAD: Immediate query
await nvim_client.start()
result = await service.find_definition(...)  # May fail!
```

### 8. Assert Structure, Not Content

```python
# ✅ GOOD: Verify structure exists
result = await service.analyze_dependencies("file.py")
assert isinstance(result.imports, list)
assert isinstance(result.file, str)

# ❌ BAD: Too specific (fails during parser bootstrap)
assert len(result.imports) > 0
assert "os" in result.imports
```

---

## Test Statistics

Current test coverage:

- **174 parameterized tests** (58 scenarios × 3 languages)
- **30 debugging tests** (session, execution, inspection)
- **100% pass rate**
- **~2 minutes** total runtime for integration tests
- **Zero linting errors**

---

## Troubleshooting

### Tests Hanging

**Cause**: Using fixed `asyncio.sleep()` for DAP tests

**Solution**: Use `DebugTestHelper` framework

### LSP Not Finding Symbols

**Cause**: LSP hasn't finished analyzing

**Solution**: Increase wait time to 2-3 seconds after `nvim_client.start()`

### Test Fails for One Language

**Cause**: Language-specific variation not handled

**Solution**: 
- Check naming conventions (snake_case vs camelCase)
- Check type names (class vs struct)
- Add conditional logic or accept multiple values

### Import Errors

**Cause**: Using wrong import path

**Solution**:
```python
# ✅ GOOD
from otter.services.navigation import NavigationService

# ❌ BAD
from src.otter.services.navigation import NavigationService
```

---

## See Also

- [Contributing Guide](../docs/CONTRIBUTING.md) - Development patterns
- [Quick Start](QUICK_START.md) - One-page cheat sheet
- [Test Fixtures](fixtures/projects/README.md) - Test project documentation

