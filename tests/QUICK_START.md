t add# Testing Quick Reference

One-page cheat sheet for running tests. See [TESTING.md](TESTING.md) for complete documentation.

---

## Running Tests

```bash
# All tests
make test

# Unit tests (fast, mocked)
make test-unit

# Integration tests (slower, real Neovim + LSP)
make test-integration

# With coverage
make test-coverage

# Watch mode (auto-rerun)
make test-watch
```

---

## By Language

```bash
# Python only
pytest tests/integration/ -k "python"

# JavaScript only
pytest tests/integration/ -k "javascript"

# Rust only
pytest tests/integration/ -k "rust"
```

---

## By Feature

```bash
# Navigation tests
pytest tests/integration/test_navigation_*.py

# Debugging tests
pytest tests/integration/test_debugging_*.py

# Workspace tests
pytest tests/integration/test_workspace_*.py

# Specific test file
pytest tests/integration/test_navigation_find_definition.py -v

# Single test (runs for all languages)
pytest tests/integration/test_navigation_find_definition.py::TestFindDefinitionParameterized::test_find_class_definition
```

---

## Writing Tests

### Key Pattern

```python
import pytest
from tests.fixtures.language_configs import LanguageTestConfig

@pytest.mark.asyncio
class TestMyFeature:
    """Tests automatically run for Python, JS, and Rust."""
    
    async def test_feature(
        self, my_service, temp_language_project, language_config: LanguageTestConfig
    ):
        ext = language_config.file_extension  # .py, .js, or .rs
        
        result = await my_service.do_something(
            file=str(temp_language_project / f"models{ext}")
        )
        
        assert result is not None, \
            f"Failed for {language_config.language}"
```

---

## Debugging Tests

```python
from tests.helpers.debug_helpers import DebugTestHelper

helper = DebugTestHelper(ide_server)

# Start and wait for state
await helper.start_debug_and_wait(
    file="test.py",
    breakpoints=[42],
    expected_status="paused"
)

# Step and verify
await helper.step_and_verify("step_over")

# Continue and wait
await helper.continue_and_wait_for_breakpoint()
```

---

## Common Patterns

### Get File Extension
```python
ext = language_config.file_extension
```

### Use Symbol Locations
```python
user_loc = language_config.symbol_locations["User"]
file = str(temp_language_project / f"{user_loc.file}{ext}")
```

### Handle Naming Conventions
```python
name = "create_user" if lang != "javascript" else "createUser"
```

### Check Type Variations
```python
assert result.type in ["class", "struct"]  # Rust uses "struct"
```

### Add Language Context
```python
assert condition, f"Error for {language_config.language}"
```

---

## Quick Tips

- ✅ Tests run for all languages automatically via parameterization
- ✅ Use `language_config` fixture for language-specific data
- ✅ Use `temp_language_project` fixture for test files
- ✅ Handle type/naming variations across languages
- ✅ Add language context to assertion messages
- ✅ Use `DebugTestHelper` for debugging tests (never `asyncio.sleep()`)

---

## Need More Help?

See [TESTING.md](TESTING.md) for:
- Complete testing guide
- Language-agnostic testing patterns
- Debug test framework details
- Best practices
- Troubleshooting
