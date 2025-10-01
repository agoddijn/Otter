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

11 core documents:
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
- `TODO.md` - Wishlist & friction signals (agent-maintained)

Plus auto-generated API docs in `docs_site/` (run `make docs`).

## Adding New Features

1. Implement in appropriate service with docstrings
2. Add to MCP server (`src/otter/mcp_server.py`)
3. Write parameterized integration tests
4. Add example to `USER_GUIDE.md`
5. Add entry to `CHANGELOG.md`
6. Run `make docs` to verify API docs updated

## Modifying Existing Features

**CRITICAL: When changing APIs (parameters, return types, behavior):**

1. **Update the implementation** with proper docstrings
2. **Update ALL existing tests** that use the changed API
   - Search for test files: `grep -r "function_name" tests/`
   - Update assertions to match new behavior
   - Add new tests for new parameters/features
3. **Update MCP server** tool definitions if exposed
4. **Update `CHANGELOG.md`** with migration guide for breaking changes
5. **Update `USER_GUIDE.md`** with new examples
6. **Run tests** to verify nothing broke: `make test`

**Example: Changing return type from `List[X]` to `ResultObject`:**
```python
# ❌ WRONG: Only updating implementation
async def get_items() -> ItemsResult:  # Changed return type
    return ItemsResult(items=[...], total=10)
# Tests will FAIL because they expect List[X]

# ✅ CORRECT: Update tests too
# In test file:
result = await service.get_items()
assert isinstance(result, ItemsResult)  # Updated
for item in result.items:  # Updated (was: for item in result)
    assert item.name
```

## Pull Requests

**Before submitting:**
```bash
make lint       # Zero errors
make test       # All passing
mypy src/       # Zero errors
make docs       # Verify docs build
```

**PR checklist:**
- [ ] Tests pass (`make test`)
- [ ] Tests updated if API changed (check `tests/integration/test_*.py`)
- [ ] Docstrings complete
- [ ] CHANGELOG.md updated (with migration guide if breaking change)
- [ ] USER_GUIDE.md updated if user-facing change
- [ ] No new documentation files created
- [ ] **[Agents]** Contributed one improvement to CONTRIBUTING.md or core docs (see "Agent-Driven Self-Improvement")

## Common Gotchas

- **macOS symlinks**: Use `resolve_workspace_path()` (handles `/var` → `/private/var`)
- **LSP timing**: Wait 1-2 seconds after opening file for analysis
- **Type variations**: Accept `["class", "struct"]` for Rust compatibility
- **Naming conventions**: Handle `snake_case` vs `camelCase`
- **Test with relative paths**: Services must handle both absolute and relative paths. Tests using only absolute paths won't catch path resolution bugs (see `rename_symbol` fix)
- **Git commands need repo-relative paths**: `git show REF:path` requires paths relative to git root, not absolute. Find root with `git rev-parse --show-toplevel`, then use `path.relative_to(root)`

## Agent-Driven Self-Improvement

**This section is for AI agents contributing to the project.**

Your task is one iteration in an ongoing process. After completing your work, **improve the process itself** for the next agent.

### The Meta-Goal

Don't just fix problems—**improve how we discover and track problems.**

Each agent should leave behind:
1. **Process improvements** - Better ways to work
2. **Signal about friction** - What's hard about this codebase
3. **Knowledge capture** - Patterns you discovered

### Critical: Information Density Over Documentation Volume

**As projects grow, context becomes overwhelming. Fight entropy.**

Before adding ANY documentation, ask:

1. **Does this need to exist?**
   - Can I compress existing docs instead of adding new ones?
   - Is this duplicating information that's elsewhere?
   
2. **Can it be easily found?**
   - Is it in the obvious place someone would look?
   - Does the section title make it discoverable?
   - Should existing sections be reorganized first?

3. **Is it information-dense?**
   - One clear example > three verbose explanations
   - Can I say this in half the words?
   - Does every sentence add value?

**Example of fighting documentation bloat:**

❌ **BAD** (adds more context without considering density):
```markdown
## New Section: Understanding LSP Responses

LSP responses can be tricky. Sometimes they return null...
[500 words explaining LSP edge cases]
```

✅ **GOOD** (compresses into existing structure):
```markdown
**Common Gotchas:**
- **LSP null responses**: Check `if result` before using (server may not be ready)
```

**When you notice context overload:**
- **Refactor existing docs** to be more scannable (add subsections, better titles)
- **Consolidate similar content** from multiple locations into one authoritative place
- **Delete outdated information** that no longer applies
- **Use examples over prose** - code speaks louder than paragraphs

Your goal: **Make the project easier to understand, not just more documented.**

### Required: End-of-Task Reflection

Before submitting, complete **ONE** of these meta-improvements:

#### Option 1: Add to the Wishlist

If you encountered **missing infrastructure** (helpers, utilities, abstractions), add it to `TODO.md`:

```markdown
## Infrastructure Wishlist

### Helper: `DebugTestHelper.wait_for_state(expected_states)`
**Signal count**: 2
**Context**: Tests repeatedly poll debug state with manual retry logic
**Impact**: Would eliminate ~50 lines of boilerplate per debug test
```

**Not**: "I need X" → implement X (one-time fix, doesn't scale)  
**Instead**: "I need X" → document X (gathers signal for prioritization)

When multiple agents report the same pain point, it becomes clear what to build.

#### Option 2: Document a Pattern You Discovered

If you **figured something out that wasn't documented**, add it to the appropriate section:

```markdown
### Pattern: Validating LSP Responses

LSP can return null for valid requests. Always check before using:

\`\`\`python
result = await nvim_client.lsp_definition(file, line, col)
if not result:
    return None  # LSP not ready or symbol not found
\`\`\`
```

**Not**: "X was confusing" (complaint without action)  
**Instead**: "Here's how X works" (knowledge for next agent)

#### Option 3: Improve the Process

If the **workflow itself was unclear**, improve this guide:

**Examples:**
- Add a gotcha to "Common Gotchas"
- Clarify a step in "Development Workflow"  
- Add a question/answer to "Questions?"
- Reorder steps that were in wrong sequence

**Not**: Concrete tasks ("add feature X")  
**Instead**: Process improvements ("when doing Y, always check Z first")

#### Option 4: Refactor Documentation for Clarity

If you found **existing context overwhelming or hard to navigate**, improve information density:

**Examples:**
- Consolidate 3 verbose sections into 1 clear example
- Add subsection headers to make scanning easier
- Move buried information to more obvious location
- Delete outdated/redundant content
- Restructure for findability (better titles, better organization)

**Not**: Add more documentation to explain existing documentation  
**Instead**: Make existing documentation clearer/shorter/better-organized

**Specific actions:**
```markdown
### Before: Scattered information
- README mentions LSP setup
- TECHNICAL_GUIDE has LSP examples  
- CONTRIBUTING has LSP gotchas

### After: Consolidated
- TECHNICAL_GUIDE has everything LSP-related
- Other docs link to it: "See TECHNICAL_GUIDE: LSP Integration"
```

### How to Choose

Ask yourself:

**Did I want something that doesn't exist?**  
→ Option 1: Add to wishlist (don't implement unless critical)

**Did I learn a non-obvious pattern?**  
→ Option 2: Document it (save next agent the discovery time)

**Was the process itself confusing?**  
→ Option 3: Improve the workflow (make the path clearer)

**Was there too much context / hard to find what I needed?**  
→ Option 4: Refactor docs for clarity (compress, consolidate, reorganize)

### The Meta-Pattern

**Good improvements are repeatable processes, not one-time fixes.**

❌ **BAD** (one-time task, will be duplicated):
```markdown
- Create helper function for debug state polling
```

✅ **GOOD** (process that every agent can follow):
```markdown
**When you find repetitive code:**
1. Check if it appears in 3+ places
2. If yes, add to Infrastructure Wishlist with signal count
3. If signal count reaches 3, create the abstraction
```

### Examples of Meta-Improvements

**Example 1: Process improvement**
```markdown
**Before running tests:**
- Check that neovim is not already running: `ps aux | grep nvim`
- Stale nvim processes cause port conflicts
```

**Example 2: Signal gathering**
```markdown
## Wishlist: Language Support

### TypeScript Language Server
**Signal count**: 1
**Use case**: Agent needed to test generic LSP features on TypeScript codebase
**Effort**: Low (similar to JavaScript setup)
```

**Example 3: Knowledge capture**
```markdown
**Common Gotchas:**
- **Test file order matters**: pytest runs tests alphabetically, shared fixtures may have state
```

**Example 4: Documentation refactoring**
```markdown
# Before: Spent 15 minutes finding path handling info across 3 files
# After: Consolidated to one place

In utils/path.py docstring:
"""Path Utilities

All path operations use these two functions:
- resolve_workspace_path(): Handles macOS symlinks (/var → /private/var)
- normalize_path_for_response(): Converts to workspace-relative

See also: CONTRIBUTING.md > Code Patterns > Path Utilities
"""
```

### Validation

Before submitting, verify your improvement:

1. **Is it repeatable?** Could every agent follow this process?
2. **Is it meta?** Does it improve HOW we work, not WHAT we build?
3. **Will it scale?** Won't it create duplicate work if followed repeatedly?

If you answered "yes" to all three, you've made a good meta-improvement.

## Questions?

- Check auto-generated docs: `make docs`
- Read code docstrings: They're the source of truth
- See `docs/ARCHITECTURE.md` for design decisions
- See `tests/TESTING.md` for testing patterns
