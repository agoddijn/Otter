# Text-Based IDE Specification for LLMs

## Functionality

### Core Navigation & Discovery

#### 1. Find Definition
```python
find_definition(symbol: str, file: Optional[str] = None, line: Optional[int] = None) -> Definition
```
Navigate to where a symbol is defined, with smart resolution for imports, methods, and nested references.

**Example:**
```python
# Simple case
find_definition("UserAuth")
→ Returns: Definition(file="auth/models.py", line=45, type="class", docstring="...")

# Context-aware case
find_definition("save", file="models.py", line=89)  
→ Resolves to the specific save() method of the class at that location
```

#### 2. Find References
```python
find_references(symbol: str, scope: Literal["file", "package", "project"] = "project") -> List[Reference]
```
Find all usages of a symbol with contextual snippets.

**Example:**
```python
find_references("process_payment", scope="package")
→ Returns: [
    Reference(file="views.py", line=34, context="result = process_payment(order.total)"),
    Reference(file="tasks.py", line=12, context="from payments import process_payment")
]
```

#### 3. Semantic Search
```python
search(
    query: str,
    search_type: Literal["text", "regex", "semantic"] = "text",
    file_pattern: Optional[str] = None,
    scope: Optional[str] = None
) -> List[SearchResult]
```
Search with varying levels of sophistication.

**Example:**
```python
# Semantic search understands code structure
search("error handling in payment functions", search_type="semantic")
→ Finds try/except blocks in functions with "payment" in name

# Regex with scope
search(r"def \w+_handler\(.*request", search_type="regex", file_pattern="**/views.py")
```

### Code Intelligence

#### 4. Get Hover Information
```python
get_hover_info(file: str, line: int, column: int) -> HoverInfo
```
Get type information, docstrings, and method signatures.

**Example:**
```python
get_hover_info("main.py", line=45, column=12)
→ Returns: HoverInfo(
    symbol="DataFrame.groupby",
    type="(by=None, axis=0, level=None, ...) -> DataFrameGroupBy",
    docstring="Group DataFrame using a mapper or by a Series of columns...",
    source_file="pandas/core/frame.py"
)
```

#### 5. Get Completions
```python
get_completions(file: str, line: int, column: int, context_lines: int = 10) -> List[Completion]
```
Get context-aware completions at a position.

**Example:**
```python
# After typing "df.gr"
get_completions("analysis.py", line=23, column=8)
→ Returns: [
    Completion(text="groupby", kind="method", detail="Group using a mapper"),
    Completion(text="gt", kind="method", detail="Greater than comparison")
]
```

### File & Project Operations

#### 6. Read File with Context
```python
read_file(
    path: str,
    line_range: Optional[Tuple[int, int]] = None,
    include_imports: bool = False,
    include_diagnostics: bool = False,
    context_lines: int = 0
) -> FileContent
```
Read files with intelligent context inclusion.

**Example:**
```python
read_file("views.py", line_range=(45, 60), include_imports=True, context_lines=3)
→ Returns: FileContent(
    content="...",
    expanded_imports={
        "from .models import User": ["User(id, name, email, created_at)"],
        "from django.shortcuts import render": ["render(request, template, context)"]
    },
    diagnostics=[Diagnostic(line=47, message="Undefined variable 'user_id'", severity="error")]
)
```

#### 7. Project Structure
```python
get_project_structure(
    path: str = ".",
    max_depth: int = 3,
    show_hidden: bool = False,
    include_sizes: bool = True
) -> ProjectTree
```
Get organized view of project layout.

**Example:**
```python
get_project_structure(max_depth=2)
→ Returns tree with file counts, sizes, and key directories highlighted
```

#### 8. Get Symbols
```python
get_symbols(file: str, symbol_types: Optional[List[str]] = None) -> List[Symbol]
```
Extract all symbols (classes, functions, etc.) from a file.

**Example:**
```python
get_symbols("models.py", symbol_types=["class", "method"])
→ Returns: [
    Symbol(name="User", type="class", line=10, children=[...]),
    Symbol(name="save", type="method", line=25, parent="User")
]
```

### Refactoring Operations

#### 9. Rename Symbol
```python
rename_symbol(
    old_name: str,
    new_name: str,
    preview: bool = True
) -> Union[RenamePreview, RenameResult]
```
Safely rename across all references.

**Example:**
```python
rename_symbol("UserAuth", "UserAuthentication", preview=True)
→ Returns: RenamePreview(
    changes=[
        Change(file="models.py", line=45, before="class UserAuth:", after="class UserAuthentication:"),
        Change(file="views.py", line=12, before="from .models import UserAuth", after="...")
    ],
    affected_files=4,
    total_changes=12
)
```

#### 10. Extract Function
```python
extract_function(
    file: str,
    start_line: int,
    end_line: int,
    function_name: str,
    target_line: Optional[int] = None
) -> ExtractResult
```
Extract code into a new function.

**Example:**
```python
extract_function("process.py", 45, 58, "calculate_totals")
→ Creates new function and replaces original code with function call
```

### Smart/Semantic Features

#### 11. Explain Code
```python
explain_code(
    file: str,
    line_range: Optional[Tuple[int, int]] = None,
    detail_level: Literal["brief", "normal", "detailed"] = "normal"
) -> CodeExplanation
```
Get natural language explanation of code functionality.

**Example:**
```python
explain_code("algorithm.py", line_range=(100, 150))
→ Returns: CodeExplanation(
    summary="Implements binary search on sorted array",
    key_operations=["Calculates midpoint", "Compares with target", "Recursively searches half"],
    complexity="O(log n)",
    potential_issues=["No handling for unsorted input"]
)
```

#### 12. Suggest Improvements
```python
suggest_improvements(
    file: str,
    focus_areas: Optional[List[str]] = None  # ["performance", "readability", "type_safety"]
) -> List[Improvement]
```
Get actionable improvement suggestions.

**Example:**
```python
suggest_improvements("handlers.py", focus_areas=["error_handling"])
→ Returns: [
    Improvement(
        line=45,
        issue="Bare except clause",
        suggestion="Catch specific exceptions",
        example="except (ValueError, KeyError) as e:"
    )
]
```

#### 13. Semantic Diff
```python
semantic_diff(
    file: str,
    from_revision: Optional[str] = "HEAD~1",
    to_revision: Optional[str] = "HEAD"
) -> SemanticDiff
```
Express changes in natural language.

**Example:**
```python
semantic_diff("models.py")
→ Returns: SemanticDiff(
    summary="Added validation to User model and extracted email logic",
    changes=[
        "Added email format validation in User.__init__",
        "Moved email sending from User.save() to new EmailService class",
        "Added type hints to all User methods"
    ]
)
```

### Analysis & Diagnostics

#### 14. Get Diagnostics
```python
get_diagnostics(
    file: Optional[str] = None,
    severity: Optional[List[str]] = None,  # ["error", "warning", "info"]
    include_fixes: bool = False
) -> List[Diagnostic]
```
Get linting and type checking results on demand.

**Example:**
```python
get_diagnostics("views.py", severity=["error"])
→ Returns: [
    Diagnostic(
        file="views.py",
        line=47,
        message="Undefined variable 'user_id'",
        severity="error",
        fix=Fix(description="Import user_id", edit=...)
    )
]
```

#### 15. Analyze Dependencies
```python
analyze_dependencies(
    file: str,
    direction: Literal["imports", "imported_by", "both"] = "both"
) -> DependencyGraph
```
Understand module relationships.

**Example:**
```python
analyze_dependencies("core/engine.py")
→ Returns graph showing what this file imports and what imports it
```

### Execution & Testing

#### 16. Run Tests
```python
run_tests(
    file_or_pattern: Optional[str] = None,
    test_name: Optional[str] = None,
    verbose: bool = False
) -> TestResults
```
Execute tests with smart selection.

**Example:**
```python
run_tests("test_models.py::TestUser::test_validation")
→ Returns results with failures, output, and coverage info
```

#### 17. Trace Execution
```python
trace_execution(
    function_or_file: str,
    arguments: Optional[Dict] = None,
    max_depth: int = 5
) -> ExecutionTrace
```
Understand runtime behavior.

**Example:**
```python
trace_execution("process_order", arguments={"order_id": 123})
→ Returns call stack, variable values at each step, and execution time
```

### Workspace Management

#### 18. Mark/Diff Positions
```python
mark_position(name: str) -> None
diff_since_mark(name: str) -> WorkspaceDiff
```
Track changes during complex operations.

**Example:**
```python
mark_position("before_refactor")
# ... make changes ...
diff_since_mark("before_refactor")
→ Shows all changes made since mark
```

### Escape Hatches

#### 19. Execute Raw Vim Command
```python
vim_command(command: str) -> str
```
Direct access to Neovim functionality.

**Example:**
```python
vim_command(":set relativenumber")
vim_command("gg=G")  # Format entire file
```

#### 20. Execute Shell Command
```python
shell(command: str, working_dir: Optional[str] = None) -> ShellResult
```
Run arbitrary shell commands.

**Example:**
```python
shell("git log --oneline -10")
shell("pytest -x", working_dir="tests/")
```

## Interface

### Communication Protocol: MCP Server

The IDE will be implemented as an MCP (Model Context Protocol) server, providing:

1. **Stateless Operations** - Each request is self-contained with all necessary context
2. **Tool-based Invocation** - Clear function calls with typed parameters and responses
3. **Structured Responses** - Rich return objects, not just strings

### Response Design Principles

#### 1. Rich, Structured Objects
All responses return dataclasses/typed objects with semantic information:

```python
@dataclass
class Definition:
    file: str
    line: int
    column: int
    symbol_name: str
    symbol_type: Literal["function", "class", "variable", "module", "method", "property"]
    docstring: Optional[str]
    signature: Optional[str]
    context_lines: List[str]  # Surrounding code for context
    source_module: Optional[str]  # For imported symbols
```

#### 2. Progressive Detail
Responses include summary information with options to expand:

```python
@dataclass  
class SearchResult:
    file: str
    line: int
    match: str
    context: str  # Single line by default
    
    # Methods to get more detail
    def expand_context(self, lines: int) -> str
    def get_full_function(self) -> Optional[str]
```

#### 3. Actionable Diagnostics
Diagnostics come with fixes when available:

```python
@dataclass
class Diagnostic:
    severity: Literal["error", "warning", "info", "hint"]
    message: str
    file: str
    line: int
    column: int
    source: str  # "mypy", "ruff", "pylsp", etc.
    fix: Optional[Fix]
    related_information: List[RelatedInfo]
```

### Ergonomic Features

#### 1. Smart Defaults
- File paths relative to project root
- Current file context carried between calls when relevant
- Sensible defaults for all optional parameters

#### 2. Batch Operations
Methods that commonly work together can be called in groups:

```python
analyze_symbol("DatabaseConnection")
# Automatically returns definition + references + type hierarchy
```

#### 3. Natural Language Options
Where appropriate, accept natural language specifications:

```python
search("error handling in payment functions", search_type="semantic")
get_project_structure(exclude="test files and documentation")
```

#### 4. Contextual File Reading
File reading automatically includes relevant context:

```python
# Reading a test file automatically shows the file being tested
read_file("test_models.py")  
→ Includes snippet from "models.py" for context

# Reading a file with errors shows diagnostics inline
read_file("views.py", include_diagnostics=True)
→ Errors appear as comments at relevant lines
```

### Error Handling

All operations return clear, actionable errors:

```python
@dataclass
class IDEError:
    error_type: str  # "file_not_found", "symbol_not_found", "syntax_error"
    message: str
    suggestions: List[str]  # "Did you mean 'UserAuthentication'?"
    context: Dict[str, Any]
```

### State Management

While individual operations are stateless, the server maintains:

1. **Project Context** - Root directory, active virtualenv, git status
2. **Neovim Instance** - Persistent for the session with loaded buffers
3. **Cache** - LSP results, file contents, symbol tables for performance

### Performance Considerations

1. **Lazy Loading** - Don't parse entire files unless needed
2. **Incremental Updates** - Use LSP's incremental sync capabilities  
3. **Result Limiting** - Default limits on search results with pagination
4. **Async Operations** - Long-running operations can be queried for status

```python
# Example of handling large results
results = search("TODO", file_pattern="**/*.py")
→ Returns first 50 results with continuation token
```

### Configuration

The IDE respects standard tooling configuration files:
- `.editorconfig` for formatting preferences
- `pyrightconfig.json` / `pyproject.toml` for type checking
- `.ruff.toml` for linting rules
- `.gitignore` for file exclusion patterns

But provides overrides through method parameters when needed.