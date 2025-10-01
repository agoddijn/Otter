"""MCP Server for CLI IDE.

Exposes IDE functionality as MCP tools using FastMCP.
"""

from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from mcp.server import FastMCP

from .server import CliIdeServer

# Global IDE server instance and project path
_ide_server: Optional[CliIdeServer] = None
_project_path: Optional[str] = None


def _get_server_name() -> str:
    """Get dynamic server name based on project path."""
    project_path = get_project_path()
    project_name = Path(project_path).name
    return f"CLI IDE: {project_name}"


def _get_server_description() -> str:
    """Get dynamic server description based on project path."""
    project_path = get_project_path()
    return (
        f"AI-powered IDE for the project at {project_path}\n\n"
        f"Provides semantic code navigation, intelligent refactoring, "
        f"analysis, and workspace management tools powered by Neovim and LSP."
    )


# Create the FastMCP server with initial name (will be updated when project path is set)
mcp = FastMCP("CLI IDE for Agents")


def set_project_path(path: str) -> None:
    """Set the project path for the IDE server."""
    global _project_path
    _project_path = str(Path(path).resolve())
    # Update server metadata with project-specific information
    _update_server_info()


def _update_server_info() -> None:
    """Update server name and description based on current project path.

    Note: FastMCP name is read-only, so we rely on the project://info resource
    to provide dynamic project information instead.
    """
    pass


async def get_ide_server() -> CliIdeServer:
    """Get or create the IDE server instance."""
    global _ide_server, _project_path
    if _ide_server is None:
        # Use environment variable or current directory if not set
        project_path = _project_path or os.getenv("IDE_PROJECT_PATH") or os.getcwd()
        if not _project_path:
            # Set it if it wasn't already set
            _project_path = project_path
        _update_server_info()
        _ide_server = CliIdeServer(project_path=project_path)
        await _ide_server.start()
    return _ide_server


def get_project_path() -> str:
    """Get the current project path."""
    return _project_path or os.getenv("IDE_PROJECT_PATH") or os.getcwd()


def _to_dict(obj: Any) -> Any:
    """Convert dataclass objects to dictionaries for JSON serialization."""
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    elif isinstance(obj, list):
        return [_to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    return obj


# ============================================================================
# Navigation & Discovery Tools
# ============================================================================


@mcp.tool()
async def find_definition(
    symbol: str, file: str | None = None, line: int | None = None
) -> Dict[str, Any]:
    """Find where a symbol is defined.

    Navigate to where a symbol is defined, with smart resolution for imports,
    methods, and nested references. Uses LSP for accurate, language-agnostic
    symbol resolution.

    Args:
        symbol: The symbol name to find the definition for
        file: Optional file path for context-aware resolution. Provide this when the symbol
              appears in multiple places or to ensure accurate resolution of imports/references.
        line: Optional line number (1-indexed) for precise position-based search. When provided
              with file, uses LSP to find the exact definition at that location.

    Returns:
        Definition information including:
        - file, line, column: Location of the definition
        - symbol_name, symbol_type: Identified symbol information
        - signature: Function/method signatures (null for classes, variables, properties)
        - docstring: Extracted documentation if available
        - context_lines: Surrounding code lines with line numbers
        - has_alternatives: Indicates if multiple definitions were found (returns first)

    Note:
        Currently requires both file and line parameters for position-based search.
        Symbol-only search (grep-based) is not yet implemented.
    """
    ide = await get_ide_server()
    result = await ide.find_definition(symbol, file, line)
    return _to_dict(result)


@mcp.tool()
async def find_references(
    symbol: str,
    file: str | None = None,
    line: int | None = None,
    scope: Literal["file", "package", "project"] = "project",
    exclude_definition: bool = False,
) -> Dict[str, Any]:
    """Find all usages of a symbol with enhanced formatting and grouping.

    Find all references to a symbol with contextual snippets including line numbers.
    Results are automatically grouped by file for better readability. For best results,
    provide the file and line number where the symbol appears.

    Args:
        symbol: The symbol name to find references for
        file: Optional file path for context-aware resolution
        line: Optional line number for position-based search
        scope: Search scope:
            - "file": Only references in the same file as the symbol
            - "package": Only references in the same package/module (Note: currently treated as "project")
            - "project": All references across the entire workspace (default)
        exclude_definition: If True, exclude the definition itself from results

    Returns:
        Structured result containing:
            - references: List of all references with file, line, column, context (with line numbers),
                         is_definition flag, and reference_type (import/usage/type_hint)
            - total_count: Total number of references found
            - grouped_by_file: References grouped by file with per-file counts

    Example:
        find_references("UserModel", file="models.py", line=5, exclude_definition=True)
    """
    ide = await get_ide_server()
    result = await ide.find_references(symbol, file, line, scope, exclude_definition)
    return _to_dict(result)


# REMOVED: search tool
# Low-value feature - agents can use ripgrep directly:
#   rg "pattern" --type py
#   rg -e "regex" --glob "*.ts"
# Semantic search (TreeSitter-based) may be added in future.


# ============================================================================
# Code Intelligence Tools
# ============================================================================


@mcp.tool()
async def get_hover_info(
    file: str,
    symbol: str | None = None,
    line: int | None = None,
    column: int | None = None,
) -> Dict[str, Any]:
    """Get type information and documentation for a symbol.

    Supports two usage patterns:
    1. Symbol-based (agent-friendly): Provide symbol name, optionally with line hint
    2. Position-based (precise): Provide exact line and column position

    Args:
        file: File path
        symbol: Symbol name to find (e.g., "CliIdeServer", "find_definition")
        line: Line number (1-indexed), required if symbol not provided, optional hint if symbol provided
        column: Column number (1-indexed), required if symbol not provided

    Returns:
        Hover information including symbol name, type, docstring, source, line, and column

    Examples:
        # Symbol-based
        get_hover_info(file="server.py", symbol="CliIdeServer")
        
        # Position-based
        get_hover_info(file="server.py", line=83, column=15)
        
        # Disambiguated
        get_hover_info(file="server.py", symbol="User", line=45)
    """
    ide = await get_ide_server()
    result = await ide.get_hover_info(file, symbol, line, column)
    return _to_dict(result)


@mcp.tool()
async def get_completions(
    file: str, line: int, column: int, max_results: int = 50
) -> Dict[str, Any]:
    """Get context-aware code completions.

    Get intelligent code completion suggestions at a specific position using LSP.
    Returns results in a structured format with relevance ranking and metadata.

    Args:
        file: File path
        line: Line number (1-indexed)
        column: Column number (0-indexed, cursor position - where cursor would be for typing)
        max_results: Maximum completions to return (default 50, use 0 for unlimited)

    Returns:
        CompletionsResult dict with:
            - completions: List of completion objects (sorted by relevance)
            - total_count: Total completions available  
            - returned_count: Number actually returned
            - truncated: True if limited by max_results
            
        Each completion has:
            - text: The completion text to insert
            - kind: Type of completion (function, method, class, variable, etc.)
            - detail: Additional info (type signature, module, etc.)
            - documentation: Docstring or description if available
        
    Examples:
        # Get top 50 completions after typing "self."
        get_completions("server.py", line=83, column=9)
        
        # Get more results if needed
        get_completions("server.py", line=83, column=9, max_results=100)
        
        # Get all completions (warning: may return 100s of items)
        get_completions("server.py", line=83, column=9, max_results=0)
    """
    ide = await get_ide_server()
    result = await ide.get_completions(file, line, column, max_results)
    return _to_dict(result)


# ============================================================================
# File & Project Operations Tools
# ============================================================================


@mcp.tool()
async def read_file(
    path: str,
    line_range: Tuple[int, int] | None = None,
    include_imports: bool = False,
    include_diagnostics: bool = False,
    context_lines: int = 0,
) -> Dict[str, Any]:
    """Read file with intelligent context inclusion.

    Read files with optional import detection, diagnostics, and context lines.
    Content includes line numbers in format "LINE_NUMBER|CONTENT".

    Args:
        path: File path to read (relative to project root or absolute)
        line_range: Optional tuple of (start_line, end_line) to read specific range (1-indexed, inclusive).
                   Example: (10, 20) reads lines 10 through 20.
        include_imports: Whether to detect import statements.
                        NOTE: Import expansion (showing signatures) is not yet implemented.
                        Returns import statements with empty signature lists.
        include_diagnostics: Whether to include LSP diagnostics (linter errors, warnings, type errors, etc.)
        context_lines: Number of context lines to include around the line_range

    Returns:
        FileContent object with:
        - content: File content with line numbers
        - total_lines: Total number of lines in the file
        - language: Detected file language (e.g., "python", "javascript")
        - expanded_imports: Dict of import statements (if requested)
        - diagnostics: List of diagnostic issues (if requested)

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If line_range is invalid (e.g., start > total_lines)
    """
    ide = await get_ide_server()
    result = await ide.read_file(
        path, line_range, include_imports, include_diagnostics, context_lines
    )
    return _to_dict(result)


@mcp.tool()
async def get_project_structure(
    path: str = ".",
    max_depth: int = 3,
    show_hidden: bool = False,
    include_sizes: bool = True,
    exclude_patterns: List[str] | None = None,
) -> Dict[str, Any]:
    """Get organized view of project layout.

    Explore project structure with configurable depth and detail.
    
    Path Resolution:
        - Relative paths resolve to project root (e.g., "src" -> /project/src)
        - Absolute paths are used as-is
        - "." returns the project root contents

    Args:
        path: Root path to analyze (relative to project or absolute)
        max_depth: Maximum directory depth (0=root only, 1=root+children)
        show_hidden: Include hidden files/directories (starting with .)
        include_sizes: Include file sizes in bytes
        exclude_patterns: Patterns to exclude (e.g., ["*.pyc", "test_*"])

    Returns:
        Project tree with:
            - root: Absolute path to analyzed directory
            - tree: Direct children (no wrapper for root directory)
            - file_count: Total files found
            - directory_count: Total directories found
            - total_size: Sum of file sizes in bytes (0 if include_sizes=False)
    """
    ide = await get_ide_server()
    result = await ide.get_project_structure(
        path, max_depth, show_hidden, include_sizes, exclude_patterns
    )
    return _to_dict(result)


@mcp.tool()
async def get_symbols(
    file: str, symbol_types: List[str] | None = None
) -> Dict[str, Any]:
    """Extract all symbols from a file.

    Get classes, functions, methods, and other symbols with rich metadata.

    Args:
        file: File path to analyze (relative to project or absolute)
        symbol_types: Optional list to filter by symbol type
                     (e.g., ["class", "function", "method"])

    Returns:
        Structured result with:
            - symbols: List of symbols with name, type, line, column, hierarchy
            - file: File path analyzed
            - total_count: Total symbols in file (including filtered out)
            - language: Detected language
        
        Each symbol includes:
            - signature: Function/method signature with params (from LSP detail)
            - detail: Additional type info from LSP
            - children: Nested symbols (methods in classes, etc.)
    """
    ide = await get_ide_server()
    result = await ide.get_symbols(file, symbol_types)
    return _to_dict(result)


# ============================================================================
# Refactoring Tools
# ============================================================================


@mcp.tool()
async def rename_symbol(
    file: str, line: int, column: int, new_name: str, preview: bool = True
) -> Dict[str, Any]:
    """Safely rename a symbol across all references using LSP.

    Rename symbols with preview mode to see changes before applying. Provide the
    file and position where the symbol appears to give LSP context.

    Args:
        file: File path where the symbol is located
        line: Line number (1-indexed) where the symbol appears
        column: Column number (0-indexed) of the symbol start
        new_name: New name for the symbol
        preview: If True, returns preview without applying changes (default: True)

    Returns:
        RenamePreview (if preview=True) showing all changes, or 
        RenameResult (if preview=False) with changes applied

    Example:
        # Preview renaming a class
        rename_symbol("models.py", line=45, column=6, new_name="UserAuth")
        
        # Apply rename directly
        rename_symbol("config.rs", line=10, column=11, new_name="AppConfig", preview=False)
    """
    ide = await get_ide_server()
    result = await ide.rename_symbol(file, line, column, new_name, preview)
    return _to_dict(result)


@mcp.tool()
async def extract_function(
    file: str,
    start_line: int,
    end_line: int,
    function_name: str,
    target_line: int | None = None,
) -> Dict[str, Any]:
    """Extract code into a new function.

    Extract a block of code into a new function and replace with a call.

    Args:
        file: File path containing the code
        start_line: Start line of code to extract
        end_line: End line of code to extract
        function_name: Name for the new function
        target_line: Optional line number where to insert the new function

    Returns:
        Extract result with new function name and changes made
    """
    ide = await get_ide_server()
    result = await ide.extract_function(
        file, start_line, end_line, function_name, target_line
    )
    return _to_dict(result)


# ============================================================================
# AI-Powered Analysis Tools (Context Compression)
# ============================================================================


@mcp.tool()
async def summarize_code(
    file: str,
    detail_level: Literal["brief", "detailed"] = "brief",
) -> Dict[str, Any]:
    """Summarize code to save context window space.
    
    Use this when you need to understand large files without reading all the code.
    Provides massive context savings (500 lines → 50 words for brief summaries).
    
    Just provide the file path - we read it for you!
    
    Args:
        file: File path to summarize (we read it for you)
        detail_level: "brief" (1-3 sentences) or "detailed" (with key components)
    
    Returns:
        CodeSummary with summary text and metadata
    
    Example:
        # Summarize a large file
        summary = summarize_code(
            "payment_processor.py",
            detail_level="brief"
        )
        # → "Payment processing service integrating Stripe and PayPal..."
    """
    ide = await get_ide_server()
    result = await ide.summarize_code(file, detail_level)
    return _to_dict(result)


@mcp.tool()
async def summarize_changes(
    file: str,
    git_ref: str = "HEAD~1",
) -> Dict[str, Any]:
    """Summarize code changes (diff) for quick review.
    
    Compresses diffs into actionable summaries. Use this to understand
    what changed without reading full diffs.
    
    Just provide file path and git ref - we handle the diff!
    
    Args:
        file: File path
        git_ref: Git reference to compare against (default: HEAD~1 = previous commit)
                Can be: "HEAD~1", "main", commit hash, etc.
    
    Returns:
        ChangeSummary with summary, change types, and breaking changes
    
    Example:
        summary = summarize_changes(
            "auth.py",
            git_ref="main"  # Compare current vs main branch
        )
        # → "Added JWT authentication. Removed /v1/users endpoint (breaking)"
    """
    ide = await get_ide_server()
    result = await ide.summarize_changes(file, git_ref)
    return _to_dict(result)


@mcp.tool()
async def quick_review(
    file: str,
    focus: List[str] | None = None,
) -> Dict[str, Any]:
    """Quick code review for sanity checks.
    
    Fast, single-shot review focusing on obvious issues. Use this for:
    - Quick sanity check of generated code
    - Catching obvious bugs before committing
    - Second opinion on security issues
    
    NOT a replacement for proper code review or testing.
    Just provide file path - we read it for you!
    
    Args:
        file: File path to review (we read it for you)
        focus: Optional focus areas (e.g., ["security", "performance", "bugs"])
    
    Returns:
        ReviewResult with issues found and overall assessment
    
    Example:
        review = quick_review(
            "auth.py",
            focus=["security"]
        )
        # → Finds: "critical: Password stored in plaintext (line 45)"
    """
    ide = await get_ide_server()
    result = await ide.quick_review(file, focus)
    return _to_dict(result)


@mcp.tool()
async def explain_error(
    error_message: str,
    context_file: str | None = None,
    context_content: str | None = None,
    context_line_start: int | None = None,
    context_line_end: int | None = None,
) -> Dict[str, Any]:
    """Explain a cryptic error message.
    
    Interprets error messages and provides actionable fixes. Use this when:
    - Error message is cryptic or unclear
    - Want to understand root cause quickly
    - Need suggestions for fixing the error
    
    Args:
        error_message: The error message/traceback
        context_file: Optional file where error occurred
        context_content: Optional code content around error
        context_line_start: Optional start line of context
        context_line_end: Optional end line of context
    
    Returns:
        ErrorExplanation with explanation, causes, and fixes
    
    Example:
        explanation = explain_error(
            "TypeError: 'NoneType' object is not subscriptable",
            context_file="app.py",
            context_content=code_snippet
        )
        # → "You're trying to access an index on a None value..."
    """
    ide = await get_ide_server()
    
    # Build context_lines tuple if both are provided
    context_lines = None
    if context_line_start is not None and context_line_end is not None:
        context_lines = (context_line_start, context_line_end)
    
    result = await ide.explain_error(
        error_message, context_file, context_content, context_lines
    )
    return _to_dict(result)


@mcp.tool()
async def explain_symbol(
    file: str,
    line: int,
    character: int,
    include_references: bool = True,
) -> Dict[str, Any]:
    """Explain a symbol using LSP + LLM (semantic understanding).
    
    This is the SMART way to understand code:
    - Uses LSP to find symbol definition
    - Optionally finds all references to show usage
    - LLM explains what it is, what it does, and how it's used
    
    Much better than just reading code - provides semantic context!
    
    Args:
        file: File path
        line: Line number (0-indexed)
        character: Character position (0-indexed) 
        include_references: Whether to include usage examples from references (default: True)
    
    Returns:
        CodeSummary with comprehensive explanation including:
        - What the symbol is (function/class/variable)
        - What it does / its purpose
        - How and where it's used in the codebase
        - Important patterns or conventions
    
    Example:
        explanation = explain_symbol(
            "server.py",
            line=45,
            character=10,
            include_references=True
        )
        # → "handle_request() is the main request handler middleware.
        #    Called by 15 routes in the API layer. Handles authentication,
        #    logging, and error wrapping."
    """
    ide = await get_ide_server()
    result = await ide.explain_symbol(file, line, character, include_references)
    return _to_dict(result)


# ============================================================================
# Analysis & Diagnostics Tools
# ============================================================================


@mcp.tool()
async def get_diagnostics(
    file: str | None = None,
    severity: List[str] | None = None,
    include_fixes: bool = False,
) -> List[Dict[str, Any]]:
    """Get linting and type checking results.

    Retrieve diagnostics from LSP servers (errors, warnings, hints).

    Args:
        file: Optional file path to get diagnostics for (None = all files)
        severity: Optional list to filter by severity (e.g., ["error", "warning"])
        include_fixes: Whether to include suggested fixes

    Returns:
        List of diagnostics with severity, message, location, and optional fixes
    """
    ide = await get_ide_server()
    result = await ide.get_diagnostics(file, severity, include_fixes)
    return _to_dict(result)


@mcp.tool()
async def analyze_dependencies(
    file: str, direction: Literal["imports", "imported_by", "both"] = "both"
) -> Dict[str, Any]:
    """Understand module relationships and dependencies.

    Analyze what a file imports and what imports it.

    Args:
        file: File path to analyze
        direction: Analysis direction - "imports", "imported_by", or "both"

    Returns:
        Dependency graph showing imports and reverse dependencies
    """
    ide = await get_ide_server()
    result = await ide.analyze_dependencies(file, direction)
    return _to_dict(result)


# ============================================================================
# Debugging Tools (DAP-Powered)
# ============================================================================


@mcp.tool()
async def start_debug_session(
    file: str,
    configuration: str | None = None,
    breakpoints: List[int] | None = None,
    args: List[str] | None = None,
) -> Dict[str, Any]:
    """Start a debug session for a file.

    Uses Neovim's DAP client with language-specific debug adapters:
    - Python: debugpy
    - JavaScript/TypeScript: node-debug2
    - Rust: lldb-vscode
    - Go: delve

    Args:
        file: File path to debug (relative to project root)
        configuration: Debug config name ("Launch file", "pytest: current file", etc.)
                      Defaults to first available config for file type
        breakpoints: Optional list of line numbers for breakpoints
        args: Optional command-line arguments for the program

    Returns:
        DebugSession with session_id, status, file, configuration, and breakpoints

    Example:
        Start debugging a Python file with breakpoints:
        {"file": "src/main.py", "breakpoints": [10, 25, 42]}

        Debug with pytest configuration:
        {"file": "tests/test_app.py", "configuration": "pytest: current file"}
    """
    ide = await get_ide_server()
    result = await ide.start_debug_session(file, configuration, breakpoints, args)
    return _to_dict(result)


@mcp.tool()
async def control_execution(
    action: Literal["continue", "step_over", "step_into", "step_out", "pause", "stop"],
    session_id: str | None = None,
) -> Dict[str, Any]:
    """Control debug execution flow.

    Args:
        action: Control action to perform:
            - continue: Resume execution until next breakpoint
            - step_over: Execute current line, don't enter functions
            - step_into: Execute current line, enter function calls
            - step_out: Execute until returning from current function
            - pause: Pause execution at current point
            - stop: Terminate debug session
        session_id: Optional session ID (uses active session if not provided)

    Returns:
        ExecutionState with session_id, status, reason, thread_id, and stack_frames

    Example:
        Step through code:
        {"action": "step_over"}

        Continue until next breakpoint:
        {"action": "continue"}

        Stop debugging:
        {"action": "stop"}
    """
    ide = await get_ide_server()
    result = await ide.control_execution(action, session_id)
    return _to_dict(result)


@mcp.tool()
async def inspect_state(
    frame_id: int | None = None,
    expression: str | None = None,
) -> Dict[str, Any]:
    """Inspect program state during debugging.

    Get call stack, variables in scope, and evaluate expressions at the
    current breakpoint or paused state.

    Args:
        frame_id: Optional stack frame ID (uses top frame if not provided)
        expression: Optional expression to evaluate (Python/JS code)

    Returns:
        Dictionary containing:
        - stack_frames: List of StackFrame objects (call stack)
        - scopes: List of Scope objects (Locals, Globals, etc.)
        - variables: Dict mapping scope names to Variable lists
        - evaluation: EvaluateResult (if expression provided)

    Example:
        Get all variables in current scope:
        {}

        Evaluate an expression:
        {"expression": "user.name"}

        Inspect specific stack frame:
        {"frame_id": 1}
    """
    ide = await get_ide_server()
    result = await ide.inspect_state(frame_id, expression)
    return _to_dict(result)


@mcp.tool()
async def set_breakpoints(
    file: str,
    lines: List[int],
    conditions: Dict[int, str] | None = None,
) -> Dict[str, Any]:
    """Set or update breakpoints in a file.

    Args:
        file: File path (relative to project root)
        lines: Line numbers for breakpoints (1-indexed)
        conditions: Optional conditions for breakpoints {line: condition}
                   Only break when condition is true (e.g., "x > 10")

    Returns:
        List of BreakpointInfo objects with id, file, line, verified, condition

    Example:
        Set breakpoints at lines 10 and 25:
        {"file": "src/app.py", "lines": [10, 25]}

        Set conditional breakpoint:
        {"file": "src/app.py", "lines": [42], "conditions": {42: "count > 100"}}
    """
    ide = await get_ide_server()
    result = await ide.set_breakpoints(file, lines, conditions)
    return {"breakpoints": _to_dict(result)}


@mcp.tool()
async def get_debug_session_info() -> Dict[str, Any]:
    """Get information about the current debug session.

    Returns:
        DebugSession if active, or {"status": "no_session"} if not debugging

    Example:
        Check if debugging is active and get current state:
        {}
    """
    ide = await get_ide_server()
    result = await ide.get_session_info()
    if result:
        return _to_dict(result)
    return {"status": "no_session"}


# ============================================================================
# REMOVED: Low-Value Testing & Execution Tools
# ============================================================================
# run_tests: Agents can run `pytest`, `cargo test`, `go test` directly
# trace_execution: Agents can use `python -m pdb` or debugger directly


# ============================================================================
# REMOVED: Low-Value Workspace Management Tools
# ============================================================================
# mark_position/diff_since_mark: Agents can use `git stash`/`git diff` directly
# vim_command: Low-value escape hatch, no real use case
# shell: Agents already have direct shell access


# ============================================================================
# Resources
# ============================================================================


@mcp.resource("project://info")
def get_project_info_resource() -> str:
    """Get information about the project being analyzed by this IDE server."""
    project_path = get_project_path()
    project_name = Path(project_path).name

    info = f"""# IDE Server Information

**Project Name:** {project_name}
**Project Path:** {project_path}

This MCP server provides AI-powered IDE capabilities for this project, including:
- Semantic code navigation (find definitions, references, search)
- Code intelligence (hover info, completions, symbols)
- Language-agnostic debugging (Python, JS/TS, Rust, Go via DAP)
- Refactoring tools (rename, extract function)
- AI-powered analysis (explain code, suggest improvements, semantic diff)
- Diagnostics and dependency analysis
- Workspace management

All file paths in tool calls are relative to the project root above.
"""
    return info


# ============================================================================
# Entry Point
# ============================================================================


def main():
    """Run the MCP server.

    The project path can be set via:
    1. IDE_PROJECT_PATH environment variable
    2. Current working directory (default)

    Example:
        IDE_PROJECT_PATH=/path/to/project python -m cli_ide.mcp_server
    """
    import sys

    # Allow setting project path from command line argument
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        project_path = sys.argv[1]
        set_project_path(project_path)
        # Remove the argument so FastMCP doesn't see it
        sys.argv = [sys.argv[0]] + sys.argv[2:]

    # Determine project path and update server info
    project_path = get_project_path()
    project_name = Path(project_path).name
    if not _project_path:
        set_project_path(project_path)

    # Print server info to stderr (stdout is used for MCP protocol)
    print("🚀 Starting CLI IDE MCP Server", file=sys.stderr)
    print(f"📁 Project: {project_name}", file=sys.stderr)
    print(f"📂 Path: {project_path}", file=sys.stderr)
    print("", file=sys.stderr)

    # FastMCP handles the server lifecycle and stdio communication
    # Just run mcp.run() which will start the server
    mcp.run()


if __name__ == "__main__":
    main()
