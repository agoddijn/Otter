# Examples Cleanup Plan

## Current State
29 files in `/examples` (140KB):

### Config Files (Keep)
- `python-project.otter.toml` ✅
- `typescript-project.otter.toml` ✅
- `fullstack-project.otter.toml` ✅

### Legitimate Examples (Keep & Polish)
- `debug_uvicorn.py` ✅ (Real-world server debugging)
- `debug_pytest.py` ✅ (Testing framework debugging)

### Development Test Files (DELETE)
❌ `test_simple.py`
❌ `test_bootstrap.py`
❌ `test_buffer_editing.py`
❌ `test_ai_features.py`
❌ `test_smart_ai_features.py`
❌ `test_llm_infrastructure.py`
❌ `test_find_replace.py`
❌ `minimal_debug_test.py`
❌ `test_debug_crash_detection.py`
❌ `test_crash.py`
❌ `test_crash_for_query.py`
❌ `test_crash_exit.py`
❌ `test_clean_exit.py`
❌ `test_error_exit.py`
❌ `test_instant_crash.py`
❌ `test_success.py`
❌ `test_success_for_query.py`
❌ `test_cross_project_debug.py`
❌ `test_persist_crash_info.py`
❌ `test_smart_retention.py`
❌ `test_mcp_session_query.py`

**Reason:** These were clearly used during development/debugging. They belong in tests, not examples.

## Proposed New Examples

### 1. Basic Usage (`basic_usage.py`)
```python
"""Basic Otter usage - navigation, editing, analysis."""
```

### 2. Debugging Server (`debug_server.py`)
Consolidate `debug_uvicorn.py` and improve it.

### 3. Debugging Tests (`debug_tests.py`)  
Keep `debug_pytest.py`, rename for clarity.

### 4. Multi-Language Project (`multi_language/`)
```
multi_language/
├── .otter.toml (fullstack config)
├── README.md (explains the example)
├── backend/ (Python)
├── frontend/ (TypeScript)
└── example.py (script showing cross-language navigation)
```

### 5. Configuration Examples (`config_examples/`)
```
config_examples/
├── python_venv.otter.toml
├── typescript_nvm.otter.toml
├── rust_workspace.otter.toml
└── README.md
```

## Proposed Final Structure

```
examples/
├── README.md (← NEW: Overview of all examples)
├── basic_usage.py
├── debug_server.py
├── debug_tests.py
├── config_examples/
│   ├── README.md
│   ├── python_venv.otter.toml
│   ├── typescript_nvm.otter.toml
│   ├── rust_workspace.otter.toml
│   └── monorepo.otter.toml
└── multi_language/
    ├── README.md
    ├── .otter.toml
    ├── backend/
    │   ├── main.py
    │   └── models.py
    ├── frontend/
    │   ├── index.ts
    │   └── types.ts
    └── example_workflow.py
```

## Action Items

### Phase 1: Delete Test Files (15 minutes)
Delete all `test_*.py` files (22 files)

### Phase 2: Improve Existing (30 minutes)
1. Polish `debug_uvicorn.py` → `debug_server.py`
2. Polish `debug_pytest.py` → `debug_tests.py`
3. Add comprehensive docstrings

### Phase 3: Create New Examples (1-2 hours)
1. Create `basic_usage.py`
2. Create `examples/README.md`
3. Organize config examples
4. Create multi-language example

### Phase 4: Documentation (30 minutes)
Update docs to reference new examples

## Expected Outcome
- **From:** 29 files (140KB), mostly dev tests
- **To:** ~15 files (<100KB), all legitimate examples
- Clear, documented examples for real-world use cases
- Better organized by use case

