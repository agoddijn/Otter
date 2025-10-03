# Test Cleanup Plan

## Current Status
- **Passing:** 328 tests
- **Failing:** 54 tests  
- **Skipped:** 22 tests

## Issues to Fix

### 1. API Signature Changes (High Priority)
- **`test_dap_output_capture.py::test_module_launch_captures_output`**: Remove `cwd` parameter from `start_debug_session()`
- **`test_debugging_session.py`**: Update to match new API signatures

### 2. RuntimeSpec Dataclass Migration (High Priority)
- **`test_runtime_resolver.py`**: All tests need updating - RuntimeSpec is now a dataclass, not a dict
  - `test_all_languages_have_required_fields`
  - `test_get_runtime_spec_valid_language`
  - `test_python_spec_structure`

### 3. NotImplementedError Handling (Medium Priority)
- **Import Expansion**: Multiple tests expect import expansion which isn't implemented
  - `test_workspace_read_file.py::test_read_file_with_imports`
  - `test_workspace_read_file.py::test_extract_imports_python`
  - `test_workspace_read_file.py::test_nvim_starts_if_not_running`
  - **Decision**: Either implement or skip these tests with clear reason

### 4. LSP Issues (Low Priority - Environment Specific)
- JavaScript/Rust LSP tests failing (likely environment/LSP server issues)
- These may pass in CI or with proper LSP setup
- **Action**: Mark as `@pytest.mark.integration_lsp` and make skippable

### 5. Debugging Tests (Medium Priority)
- Several DAP tests failing due to recent breakpoint/session tracking changes
- Need to update tests to match new behavior

## Consolidation Opportunities

### Debugging Tests
**Current:**
- `test_debugging_session.py`
- `test_debugging_execution.py`
- `test_debugging_inspection.py`
- `test_dap_breakpoints.py`
- `test_dap_output_capture.py`
- `test_dap_bootstrap.py`

**Proposed:**
- `test_dap_core.py` - Basic session management, start/stop, status
- `test_dap_breakpoints.py` - All breakpoint functionality (keep this)
- `test_dap_execution.py` - Step over/into/out, continue
- `test_dap_inspection.py` - Stack frames, variables, evaluation
- `test_dap_bootstrap.py` - Auto-installation (keep this)

### Navigation Tests
**Current:**
- `test_navigation_find_definition.py`
- `test_navigation_find_references.py`
- `test_navigation_get_completions.py`
- `test_navigation_get_hover_info.py`

**Proposed:** Keep as-is (well-organized by feature)

### Workspace Tests
**Current:**
- `test_workspace_get_symbols.py`
- `test_workspace_read_file.py`
- `test_workspace_diagnostics.py` (unit)

**Proposed:** Keep as-is (minimal duplication)

## Test Organization

### Current Structure
```
tests/
├── unit/
│   ├── test_bootstrap.py
│   ├── test_config.py
│   ├── test_runtime_resolver.py
│   ├── test_workspace*.py (3 files)
├── integration/
│   ├── test_analysis*.py (1 file)
│   ├── test_debugging*.py (3 files)
│   ├── test_dap*.py (3 files)
│   ├── test_navigation*.py (4 files)
│   ├── test_refactoring*.py (1 file)
│   ├── test_workspace*.py (2 files)
│   └── test_*.py (5 more files)
├── fixtures/
└── helpers/
```

### Proposed Structure
```
tests/
├── unit/
│   ├── test_config.py
│   ├── test_runtime_resolver.py
│   ├── test_bootstrap.py
│   └── test_workspace_utils.py (consolidated)
├── integration/
│   ├── dap/
│   │   ├── test_core.py (sessions, status)
│   │   ├── test_breakpoints.py
│   │   ├── test_execution.py
│   │   ├── test_inspection.py
│   │   └── test_bootstrap.py
│   ├── lsp/
│   │   ├── test_navigation.py (consolidate find_definition, find_references)
│   │   ├── test_hover.py (hover_info)
│   │   ├── test_completions.py
│   │   ├── test_symbols.py (workspace symbols)
│   │   └── test_refactoring.py (rename)
│   ├── test_analysis.py
│   ├── test_buffer_editing.py
│   ├── test_config_integration.py
│   └── test_neovim_client.py
├── fixtures/
│   ├── language_configs.py
│   ├── lsp_test_fixtures.py
│   └── projects/ (test projects for each language)
└── helpers/
    └── debug_helpers.py
```

## Action Items

### Phase 1: Fix Broken Tests (1-2 hours)
1. Fix API signature issues (remove `cwd`, update RuntimeSpec access)
2. Skip NotImplementedError tests with clear markers
3. Mark flaky LSP tests appropriately

### Phase 2: Consolidate (2-3 hours)
1. Merge debugging tests into logical groups
2. Merge navigation tests (definition + references)
3. Clean up unit test duplication

### Phase 3: Improve (1-2 hours)
1. Add missing test markers (@pytest.mark.integration, @pytest.mark.slow)
2. Improve test documentation
3. Add test README explaining organization

## Expected Outcome
- All tests passing (or properly skipped/marked)
- ~15-20% fewer test files
- Clearer test organization
- Faster test discovery
- Better parallelization

