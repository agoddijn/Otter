# Testing Guide

## Running Tests

### Prerequisites

Before running tests, ensure all LSP servers are installed:

```bash
# Install LSP servers for tests
make install-lsp-servers

# Or manually
uv run python scripts/install_test_lsp_servers.py
```

This will install:
- **Python**: pyright
- **JavaScript/TypeScript**: typescript-language-server
- **Rust**: rust-analyzer (requires rustup)

### Run All Tests

```bash
make test
```

This automatically installs LSP servers before running tests.

### Run Specific Test Suites

```bash
# Unit tests only (no LSP dependencies)
make test-unit

# Integration tests only (requires LSP servers)
make test-integration

# Specific test file
PYTHONPATH=src uv run pytest tests/integration/test_navigation_find_definition.py -v

# Specific test for one language
PYTHONPATH=src uv run pytest tests/integration/ -k "python" -v
```

## Test Architecture

### Unit Tests (`tests/unit/`)

- No external dependencies
- Mock Neovim and LSP interactions
- Fast execution (<1s per test)
- Test individual components in isolation

### Integration Tests (`tests/integration/`)

- Require running Neovim instance
- Require LSP servers installed
- Test real LSP/DAP functionality
- Slower execution (2-5s per test)

### Parameterized Multi-Language Tests

Many integration tests run across Python, JavaScript, and Rust:

```python
@pytest.mark.asyncio
class TestFindDefinitionParameterized:
    async def test_find_class_definition(
        self, navigation_service, language_config
    ):
        # This test runs 3 times:
        # - test_find_class_definition[python]
        # - test_find_class_definition[javascript]
        # - test_find_class_definition[rust]
        ...
```

## LSP Test Robustness

### Current Approach

Tests use conservative delays to ensure LSP servers are ready:

- **LSP_STARTUP_DELAY**: 3 seconds for LSP to attach
- **LSP_INDEX_DELAY**: 2 seconds for file indexing

This is not ideal but ensures deterministic behavior across different systems.

### Future Improvement: LSP Readiness Polling

We have infrastructure in `src/otter/neovim/lsp_readiness.py` for polling
LSP status instead of using delays. This needs additional work to handle:

1. Different LSP server initialization speeds
2. Neovim API version compatibility
3. Worker process stdout/stderr capture in pytest-xdist

**TODO**: Implement proper LSP readiness polling to replace delays.

## CI/CD Considerations

### GitHub Actions

The test suite is designed to work in CI environments:

1. `make install-lsp-servers` handles missing dependencies gracefully
2. Tests skip if LSP server unavailable (e.g., rust without rustup)
3. Conservative delays account for slower CI machines

### Example CI Workflow

```yaml
- name: Install system dependencies
  run: |
    sudo apt-get update
    sudo apt-get install -y neovim nodejs npm
    
- name: Install LSP servers
  run: make install-lsp-servers
  
- name: Run tests
  run: make test
```

## Debugging Failing Tests

### LSP Not Ready

If tests fail with "Definition not found" or "No symbol found":

```bash
# Check LSP servers are installed
make install-lsp-servers

# Run with verbose output
PYTHONPATH=src uv run pytest tests/integration/test_navigation_find_definition.py -v -s

# Check Neovim LSP logs
tail -f ~/.local/state/nvim/lsp.log
```

### Increase Delays for Slow Systems

If your system is slow, increase delays in `tests/fixtures/lsp_test_fixtures.py`:

```python
LSP_STARTUP_DELAY = 5.0  # Increase from 3.0
LSP_INDEX_DELAY = 3.0    # Increase from 2.0
```

### Skip Multi-Language Tests

To test only Python (fastest):

```bash
PYTHONPATH=src uv run pytest tests/integration/ -k "python" -v
```

## Writing New Tests

### Use Shared Fixtures

```python
from tests.fixtures.lsp_test_fixtures import nvim_client_with_lsp

@pytest.mark.asyncio
class TestMyFeature:
    @pytest.fixture
    async def my_service(self, nvim_client_with_lsp, language_project_dir):
        service = MyService(nvim_client_with_lsp)
        yield service
```

The `nvim_client_with_lsp` fixture handles:
- Starting Neovim
- Waiting for LSP to be ready
- Opening test files
- Cleanup

### Parameterize for All Languages

```python
from tests.fixtures.language_configs import LanguageTestConfig

async def test_my_feature(
    self, my_service, language_project_dir, language_config: LanguageTestConfig
):
    # Automatically runs for python, javascript, rust
    ext = language_config.file_extension
    file = str(language_project_dir / f"models{ext}")
    ...
```

## Test Performance

Current test suite statistics:

- **Total tests**: ~340
- **Unit tests**: ~50 (< 5 seconds)
- **Integration tests**: ~290 (60-90 seconds)
- **Parallelization**: pytest-xdist with 12 workers

Tips for faster local development:

```bash
# Run only unit tests (fast)
make test-unit

# Run integration tests for one language
PYTHONPATH=src uv run pytest tests/integration/ -k "python"

# Run specific test class
PYTHONPATH=src uv run pytest tests/integration/test_navigation_find_definition.py -v
```

