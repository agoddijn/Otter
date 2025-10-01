# Changelog

All notable changes to Otter will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Note - `extract_function` Status

**Based on agent testing (Test Report #9):**

- `extract_function` is currently a stub (returns "Stub: extract_function")
- API design looks reasonable but needs implementation
- When implementing, consider: preview mode, variable scope analysis, return value inference, validation

### Fixed - `rename_symbol` Path Resolution

**Critical bug fix based on agent testing (Test Report #8):**

- **Fixed inconsistent path resolution**: `rename_symbol` now uses centralized path utilities
- **Added `project_path` to `RefactoringService`**: Consistent with other services
- **Relative paths now work**: Can use `models.py` instead of requiring absolute paths
- **Added regression test**: New test ensures relative paths keep working

### Changed - `get_symbols` Improvements

**Based on agent testing feedback (Test Report #7):**

- **Wrapped response**: Now returns `SymbolsResult` with metadata instead of bare list
- **Added metadata**: `file`, `total_count`, `language` fields
- **Enriched symbols**: Added `column`, `signature`, `detail` fields from LSP
- **Better structure**: Proper JSON object with `symbols` array, not concatenated objects

### Changed - `get_project_structure` Improvements

**Based on agent testing feedback (Test Report #6):**

- **Removed root wrapper**: `tree` now returns direct children instead of wrapping them in root directory name
- **Added metadata**: `file_count`, `directory_count`, `total_size` fields
- **Clearer truncation**: Renamed `truncated` → `children_truncated`
- **Pattern filtering**: New `exclude_patterns` parameter for filtering files
- **Better path docs**: Clarified how relative/absolute paths resolve

### Added - Agent-Driven Self-Improvement Process

**Meta-level contribution workflow that improves the process itself, not just the product.**

#### What's New

Added "Agent-Driven Self-Improvement" section to `CONTRIBUTING.md` with four meta-improvement options:

1. **Signal Gathering** (`TODO.md` wishlist)
   - Agents document missing infrastructure instead of immediately building it
   - Signal count tracks how many agents hit the same friction
   - Prevents duplicate work, prioritizes high-impact improvements

2. **Knowledge Capture** (pattern documentation)
   - Agents document non-obvious patterns they discovered
   - Saves future agents from re-discovering the same solutions
   - Grows institutional knowledge organically

3. **Process Improvement** (workflow refinement)
   - Agents clarify unclear steps, add gotchas, reorder workflows
   - Makes the contribution process itself smoother over time
   - Meta-level improvements that compound

4. **Documentation Refactoring** (information density)
   - **Fight entropy**: Compress/consolidate instead of adding more
   - Reorganize for findability when context is overwhelming
   - Delete outdated content, improve scannability
   - Critical as project complexity grows

#### Why This Matters

**Focus on repeatable processes, not one-time fixes:**
- ❌ "Create helper X" → Every agent tries to create X (duplication)
- ✅ "Add helpers you wish existed to TODO.md" → Signal accumulates, build once

**Fight documentation entropy:**
- ❌ "Add more context to explain existing context" → Compounds the problem
- ✅ "Refactor existing docs to be clearer" → Actually solves the problem

**Each agent leaves behind:**
- Better understanding of HOW to work (process)
- Signal about WHAT is hard (friction points)
- Knowledge about WHAT they learned (patterns)
- Clearer, denser context (not just more context)

This creates a meta-loop: the process of contributing improves the process of contributing.

**Critical for scaling:** As project complexity grows, information density becomes the limiting factor. This process ensures docs get better, not just bigger.

### Enhanced - `read_file` Improvements

**Better metadata, validation, and clarity** based on agent testing feedback:

#### What's New

##### Enhanced Response Metadata
- **NEW: `total_lines` field**: Always know how many lines are in the file
  ```json
  {
    "content": "1|def main():\n2|    pass",
    "total_lines": 2,
    "language": "python"
  }
  ```

- **NEW: `language` field**: Automatically detected file language (python, javascript, rust, etc.)
  - Helps agents understand context without checking file extensions
  - Returns `null` for unknown/unsupported file types

##### Improved Line Range Validation
- **BREAKING**: Now validates line ranges and raises `ValueError` for invalid ranges:
  - `start < 1`: Raises error (lines are 1-indexed)
  - `start > end`: Raises error
  - `start > total_lines`: Raises error with clear message showing file length
  - `end > total_lines`: Gracefully capped to file length (not an error)
  
- **Previous behavior**: Out-of-range requests silently returned empty content
- **New behavior**: Clear error messages guide you to fix the issue
  ```
  ValueError: Line range start (100) exceeds file length (8 lines)
  ```

##### Clarified Import Expansion Feature
- **Updated documentation**: Makes it clear that import expansion is not yet implemented
- `include_imports=true` returns detected import statements with empty signature lists
- Placeholder for future LSP-based expansion (showing imported symbols' signatures)
- No behavior change, just clearer expectations

##### Better Documentation
- Line range clarified as "1-indexed, inclusive on both ends"
- Examples added to tool description
- Content format explicitly documented: `"LINE_NUMBER|CONTENT"`

#### Example Output
```json
{
  "content": "10|def calculate_total(items):\n11|    return sum(item.price for item in items)\n12|    ",
  "total_lines": 150,
  "language": "python",
  "expanded_imports": null,
  "diagnostics": null
}
```

#### Migration Notes
- **API change**: `FileContent` dataclass now requires `total_lines` (int) field
- **API change**: Added optional `language` (str | None) field to `FileContent`
- **Behavior change**: Invalid line ranges now raise `ValueError` instead of silently succeeding
- All tests updated to assert `total_lines` and handle new validation
- Three new validation tests added: out-of-range start, inverted range, capped end

#### Use Cases
- **Pagination**: Use `total_lines` to know when to stop requesting more lines
- **Validation**: Verify line numbers from other tools (e.g., diagnostics) are in bounds
- **Language detection**: Use `language` field for syntax highlighting or tool selection
- **Better errors**: Get immediate feedback when requesting invalid line ranges

---

### Enhanced - `get_hover_info` Improvements

**Improved ergonomics and reliability** based on agent testing feedback:

#### What's New

##### Hybrid API: Symbol-based OR Position-based
- **NEW: Symbol-based hover** (agent-friendly): Just provide the symbol name
  ```python
  # Natural and conversational
  hover = await get_hover_info(file="server.py", symbol="CliIdeServer")
  ```
  
- **Position-based hover** (precise): Provide exact line and column
  ```python
  # When you have a specific position
  hover = await get_hover_info(file="server.py", line=83, column=15)
  ```
  
- **Disambiguated hover**: Combine symbol name with line hint
  ```python
  # When symbol appears multiple times, hint which one
  hover = await get_hover_info(file="models.py", symbol="User", line=45)
  ```

##### Ergonomic Improvements
- **Forgiving column positioning**: Automatically searches nearby columns (±1-3 characters) when exact position doesn't match
  - No more "column 10 vs column 15" frustration
  - Finds symbols even when cursor is close but not exact
  
- **Position context in response**: Added `line` and `column` fields to `HoverInfo`
  - Makes it easy to correlate hover responses with requests
  - Useful for debugging and logging
  
- **Better error messages**: Clearer distinction between different error cases
  - "No symbol found at position" instead of generic "No hover information found"
  - "Symbol 'X' not found in file.py" for symbol-based lookup
  - Guidance: "Try positioning cursor directly on the symbol name"
  - LSP readiness hint: "If the LSP server is still starting up, wait a moment and try again"
  
- **Improved source file detection**: Now uses LSP definition request as fallback
  - `source_file` field now populated for imported symbols
  - Helps with "jump to source" functionality
  - Works across Python, JavaScript, TypeScript, and Rust
  
- **Fixed async function parsing**: Symbol name now correctly extracted from `async def` functions
  - Previously captured "async" as symbol name
  - Now correctly identifies the function name

#### Example Output
```json
{
  "symbol": "find_definition",
  "type": "async def find_definition(self, symbol: str, file: Optional[str] = None, line: Optional[int] = None) -> Definition",
  "docstring": "Find the definition of a symbol...",
  "source_file": "src/otter/services/navigation.py",
  "line": 83,
  "column": 15
}
```

#### Migration Notes
- **API change**: `line` and `column` are now optional (required only if `symbol` not provided)
- `HoverInfo` now includes `line` and `column` fields (optional, defaults to `None`)
- Error message changed from "No hover information found" to "No symbol found"
- Tests updated to verify new fields and symbol-based API

#### Use Cases
- **Agents**: Use symbol-based API for natural language workflows
- **Editors**: Use position-based API for precise cursor-based operations
- **Mixed**: Combine both when you have partial information (symbol + approximate location)

---

### Enhanced - `get_completions` Major Improvements

**Complete overhaul for usability and practicality** based on agent testing feedback:

#### What Changed

##### Structured Response Format (Breaking Change)
- **BEFORE**: Returned `List[Completion]` - hundreds of unfiltered items
  ```json
  [{"text": "item1", "kind": "method"}, {"text": "item2", "kind": "function"}, ...]
  ```

- **NOW**: Returns `CompletionsResult` with metadata and filtering
  ```json
  {
    "completions": [...],
    "total_count": 250,
    "returned_count": 50,
    "truncated": true
  }
  ```

##### Smart Filtering & Ranking
- **Default limit**: Top 50 most relevant completions (configurable via `max_results`)
- **LSP-based ranking**: Sorts by LSP server's relevance scoring (`sortText`)
- **Configurable**: Set `max_results=100` for more, `max_results=0` for unlimited (use with caution)
- **No more overwhelm**: Prevents 250+ item dumps that were unusable

##### Enhanced Completion Data
- **NEW: `documentation` field**: Extracts docstrings/descriptions from LSP
  - Helps distinguish between similarly-named items
  - Provides context without extra lookups
  
- **Improved `detail` field**: Now properly populated with type signatures, modules, import sources
  
- **NEW: `sort_text` field**: Internal ranking score (used for sorting, can be hidden in UI)

##### Better API Design
- **REMOVED**: `context_lines` parameter (was unused, documented as "kept for compatibility")
- **ADDED**: `max_results` parameter (default 50, practical and useful)
- **Empty results**: Returns proper `CompletionsResult` with `total_count=0` instead of empty list

#### Example Output

**After typing `self.`:**
```json
{
  "completions": [
    {
      "text": "nvim_client",
      "kind": "property",
      "detail": "NeovimClient",
      "documentation": "The Neovim client instance for LSP communication"
    },
    {
      "text": "project_path",
      "kind": "property", 
      "detail": "Path",
      "documentation": null
    },
    {
      "text": "find_definition",
      "kind": "method",
      "detail": "async def find_definition(symbol: str, ...) -> Definition",
      "documentation": "Find the definition of a symbol.\n\nUses LSP textDocument/definition..."
    }
  ],
  "total_count": 45,
  "returned_count": 45,
  "truncated": false
}
```

**After typing in empty context (limiting to 50):**
```json
{
  "completions": [
    {"text": "def", "kind": "keyword", ...},
    {"text": "class", "kind": "keyword", ...},
    ...
  ],
  "total_count": 250,
  "returned_count": 50,
  "truncated": true
}
```

#### Migration Guide

**Breaking Changes:**
1. **Return type changed**: `List[Completion]` → `CompletionsResult`
   ```python
   # BEFORE
   completions = await get_completions("file.py", 10, 5)
   for comp in completions:  # Direct list
       print(comp.text)
   
   # NOW
   result = await get_completions("file.py", 10, 5)
   print(f"Showing {result.returned_count} of {result.total_count}")
   for comp in result.completions:  # Access .completions
       print(comp.text)
   ```

2. **Parameter changed**: `context_lines` → `max_results`
   ```python
   # BEFORE (context_lines did nothing)
   await get_completions("file.py", 10, 5, context_lines=20)
   
   # NOW (max_results controls filtering)
   await get_completions("file.py", 10, 5, max_results=100)
   ```

3. **Completion model extended**: New optional fields `documentation` and `sort_text`
   - Existing code accessing `text`, `kind`, `detail` works unchanged
   - New fields default to `None`, so safe to ignore

**Update your code:**
```python
# ✅ Access completions list
result = await get_completions(file, line, col)
for completion in result.completions:
    print(completion.text)

# ✅ Check if results were truncated  
if result.truncated:
    print(f"Showing top {result.returned_count} of {result.total_count} completions")

# ✅ Get more results if needed
result = await get_completions(file, line, col, max_results=100)

# ✅ Use documentation if available
for completion in result.completions:
    if completion.documentation:
        print(f"{completion.text}: {completion.documentation}")
```

#### Benefits
- **10x better UX**: 50 relevant items vs 250 overwhelming items
- **Proper structure**: Clear metadata about result set
- **Better information**: Documentation helps choose between completions
- **Practical defaults**: Works great out of the box, customizable when needed
- **Honest about limits**: `truncated` flag tells you when there's more

---

### Enhanced - `find_references` Improvements

**Improved usability and structure** based on user feedback:

#### What's New
- **Structured return format**: Results now wrapped in `ReferencesResult` with:
  - `references`: List of all Reference objects
  - `total_count`: Total number of references found
  - `grouped_by_file`: References automatically grouped by file with per-file counts
  
- **Line numbers in context**: Context now shows `"Line 42: code here"` instead of just `"code here"`
  - Makes it easier to navigate to references
  - No need to cross-reference line numbers separately

- **Definition marking**: Each reference includes `is_definition: bool` flag
  - Clearly identifies which result is the symbol's definition
  - New `exclude_definition` parameter to filter out the definition if desired

- **Reference type detection**: Each reference includes `reference_type` field:
  - `"import"`: Symbol is imported
  - `"type_hint"`: Used in type annotations
  - `"usage"`: Regular usage in code

- **Better scope documentation**: Clarified what "file", "package", and "project" scope mean

#### Example Output
```json
{
  "references": [...],
  "total_count": 27,
  "grouped_by_file": [
    {
      "file": "src/server.py",
      "count": 4,
      "references": [...]
    },
    {
      "file": "tests/test_server.py",
      "count": 23,
      "references": [...]
    }
  ]
}
```

### Added - AI-Powered Analysis (Context Compression)

**5 LLM-powered tools** for context compression and semantic understanding:

#### Features
- **`summarize_code`** - Compress large files into brief/detailed summaries
  - File-based: Agent provides path, we read and summarize
  - Saves context: 500 lines → 50 words (brief) or 200 words (detailed)
  - Model tiers: Fast for brief, capable for detailed
  
- **`summarize_changes`** - Git-aware diff summarization
  - Compares current file vs git ref (default: HEAD~1)
  - Identifies change types, breaking changes, affected functionality
  - No need to provide old/new content - we handle git
  
- **`quick_review`** - Fast code review for sanity checks
  - Focus areas: security, performance, bugs, style
  - Finds obvious issues before committing
  - NOT a replacement for proper review/testing
  
- **`explain_error`** - Interpret cryptic error messages
  - Provides likely causes and suggested fixes
  - Fast model for quick turnaround
  - Optional context for better explanations
  
- **`explain_symbol`** - Semantic symbol explanation (LSP + LLM)
  - Uses LSP to find definition and references
  - LLM explains what it is, what it does, where it's used
  - Smart context: Provides semantic understanding, not just code reading

#### Architecture
- **Provider-Agnostic**: Supports Anthropic, OpenAI, Google, Azure, OpenRouter via LiteLLM
- **Model Tiers**: Fast, capable, advanced - auto-selected based on task
- **Bring Your Own Key**: Runtime provider detection from env vars
- **Context Compression**: Designed to save agents' context windows, not bloat them
- **One-Shot Requests**: No fancy agents, just fast LLM completions

#### Philosophy
These tools exist to **offload context management** from the calling agent:
- ✅ Agent says "summarize this file" (just path, no content)
- ✅ We read file, send to LLM, return summary
- ✅ Agent's context stays clean
- ❌ No long-running agent conversations
- ❌ No complex context management
- ❌ No asking agent to provide content

#### Files Created
- `src/otter/llm/config.py` (126 lines) - Provider configuration
- `src/otter/llm/client.py` (95 lines) - LiteLLM wrapper
- `src/otter/services/ai.py` (646 lines) - AIService with 5 methods
- `scripts/check_llm_config.py` (40 lines) - Config checker
- `examples/test_smart_ai_features.py` (128 lines) - Demo script

#### Dependencies
- `litellm>=1.30.0` - Multi-provider LLM client
- `python-dotenv>=1.0.0` - Environment variable loading

#### Configuration
```bash
# Copy .env.example to .env and add your API keys
cp .env.example .env

# Check configured providers
make llm-info

# Test AI features
make test-llm
```

### To Be Added
- `rename_symbol` - LSP-powered safe symbol renaming
- `extract_function` - Smart code extraction with variable detection

---

## [0.2.0] - 2025-10-01

### Added - Language-Agnostic Testing Framework

**174 parameterized tests** across Python, JavaScript, and Rust.

#### Features
- **Automatic Parameterization**: Tests run for all languages automatically via pytest
- **Language Configurations**: Centralized test data in `tests/fixtures/language_configs.py`
- **Temporary Projects**: Auto-generated test projects per language
- **Symbol Locations**: Predefined locations for reliable navigation tests
- **Type Flexibility**: Handles cross-language variations (class vs struct, snake_case vs camelCase)

#### Files Created
- `tests/fixtures/language_configs.py` - Language test configurations
- `tests/conftest.py` - Updated with auto-parameterization hooks
- 6 parameterized test files covering all major features

#### Documentation
- `tests/LANGUAGE_AGNOSTIC_TESTING_GUIDE.md` - Complete testing guide
- `tests/PARAMETERIZED_TEST_TEMPLATE.py` - Template for new tests

#### Impact
- **58 test scenarios** × **3 languages** = **174 tests**
- Single source of truth for test logic
- Easy to add new languages (just update config)
- Guaranteed consistent behavior across languages

---

## [0.1.0] - 2025-09-30

### Added - DAP Debugging for AI Agents

**Language-agnostic programmatic debugging** through Debug Adapter Protocol.

#### Features
- **5 MCP Tools** for debugging:
  - `start_debug_session` - Start debugging with breakpoints
  - `control_execution` - Step through code (step_over, step_into, step_out, continue, pause, stop)
  - `inspect_state` - View variables, stack frames, evaluate expressions
  - `set_breakpoints` - Dynamic breakpoint management (regular and conditional)
  - `get_debug_session_info` - Query session status

- **13 NeovimClient DAP Methods**: Low-level DAP protocol operations via Lua
- **7 Response Models**: Type-safe debugging data structures
- **4 Languages Supported**: Python, JavaScript/TypeScript, Rust, Go

#### Architecture
- **Zero Custom DAP Code**: Uses Neovim's `nvim-dap` plugin
- **Language-Agnostic**: Works with any DAP adapter Neovim supports
- **Async-First**: Non-blocking operations with proper state management
- **Session Management**: Track and control multiple debug sessions

#### Testing Infrastructure
- **30 Integration Tests** (100% passing)
- **Custom Test Framework**: `DebugTestHelper` with exponential backoff polling
- **Robust State Verification**: No hanging tests, clear error diagnostics
- **79 seconds** total test runtime (average 2.6s per test)

#### Why DAP?
Traditional debuggers (pdb, gdb) require interactive stdin/stdout. DAP provides:
- ✅ Structured JSON API for all operations
- ✅ Programmatic control without human interaction
- ✅ **75-80% reduction in debugging iterations** for AI agents

#### Files Created
- `src/otter/services/debugging.py` (372 lines) - DebugService
- `src/otter/neovim/client.py` (+500 lines) - 13 DAP methods
- `src/otter/models/responses.py` (+97 lines) - Debug models
- `configs/lua/dap_config.lua` (189 lines) - Language adapters
- `tests/helpers/debug_helpers.py` (279 lines) - Test framework
- 3 integration test files (785 lines total)

#### Documentation
- Updated README with debugging features
- Updated SPECIFICATION with DAP tools
- Created debugging test framework documentation

---

## [Initial Release] - 2025-09-20

### Added - Core LSP & TreeSitter Features

**8 LSP-powered tools** for semantic code intelligence:

#### Navigation
- `find_definition` - Jump to symbol definitions (7 tests)
- `find_references` - Find all symbol usages (9 tests)
- `get_hover_info` - Type information and docs (5 tests)
- `get_completions` - Context-aware autocomplete (10 tests)

#### Intelligence
- `get_symbols` - Extract file symbols (12 tests)
- `get_diagnostics` - LSP errors and warnings (12 tests)

#### Analysis
- `analyze_dependencies` - TreeSitter-based imports (6 tests)

#### Files
- `read_file` - Enhanced file reading with diagnostics (20 tests)

#### Architecture
- **Neovim as Integration Hub**: Leverage mature LSP/DAP/TreeSitter implementations
- **Language-Agnostic Design**: Zero per-language code, protocol-based
- **Type-Safe**: Strict mypy compliance, dataclass responses
- **Async-First**: Non-blocking I/O throughout

#### Philosophy
Focus on what agents can't do via shell:
- ✅ LSP-powered semantic understanding
- ✅ TreeSitter-based syntax parsing
- ❌ Don't reimplement text search (use `rg`)
- ❌ Don't reimplement test runners (use `pytest`, `cargo test`)
- ❌ Don't reimplement git (use `git` directly)

#### Quality Metrics
- **81 tests passing** (33 integration, 48 unit)
- **Zero mypy errors** (strict mode)
- **~85% test coverage**
- **Comprehensive documentation** (2,000+ lines)

---

## Version History Summary

| Version | Date | Key Features | Tests | Status |
|---------|------|--------------|-------|--------|
| **0.2.0** | 2025-10-01 | Language-agnostic testing | 174 | ✅ Stable |
| **0.1.0** | 2025-09-30 | DAP debugging | 30 | ✅ Stable |
| **Initial** | 2025-09-20 | LSP & TreeSitter | 81 | ✅ Stable |

**Total**: 13 of 15 core features complete (87%)

---

## Coming Next

### High Priority
1. **`rename_symbol`** - LSP-powered safe refactoring
   - Preview mode (show all changes)
   - Apply mode (execute refactoring)
   - Cross-file support
   - Scope-aware renaming

2. **`extract_function`** - Smart code extraction
   - Automatic variable detection
   - Parameter passing
   - Return value handling
   - Scope analysis

### Medium Priority
3. **Advanced DAP Features**
   - Exception breakpoints
   - Watch expressions
   - Data breakpoints (break on variable change)
   - Logpoints (log without stopping)
   - Multi-threaded debugging

4. **Semantic Search**
   - TreeSitter-based pattern matching
   - Structural code search
   - Cross-language patterns

---

## Breaking Changes

None yet - project is in initial development phase.

---

## Migration Guides

### Upgrading to 0.2.0

No breaking changes. New test framework is additive.

**For test writers:**
- New tests should use parameterized pattern
- Old Python-only tests still work
- See `tests/TESTING.md` for migration guide

### Upgrading to 0.1.0

No breaking changes. DAP debugging is new functionality.

**For users:**
- 5 new MCP tools available
- Requires DAP adapters installed for debugging
- See `docs/USER_GUIDE.md` for usage

---

## Acknowledgments

Built on top of:
- [Model Context Protocol](https://modelcontextprotocol.io) by Anthropic
- [Neovim](https://neovim.io) and its LSP/DAP implementations
- [pynvim](https://github.com/neovim/pynvim) for Python-Neovim RPC
- [nvim-dap](https://github.com/mfussenegger/nvim-dap) for DAP integration
- [nvim-treesitter](https://github.com/nvim-treesitter/nvim-treesitter) for syntax parsing

