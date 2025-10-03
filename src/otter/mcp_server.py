"""MCP Server for CLI IDE.

Exposes IDE functionality as MCP tools using FastMCP.
"""

from __future__ import annotations

import asyncio
import atexit
import os
import signal
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


def _cleanup_server() -> None:
    """Clean up the IDE server on exit.
    
    This ensures the Neovim process is properly terminated when Claude Desktop closes.
    """
    global _ide_server
    if _ide_server is not None:
        try:
            # Run cleanup in a new event loop since we might be called from atexit
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_ide_server.stop())
            finally:
                loop.close()
        except Exception:
            # Best effort cleanup - ignore errors during shutdown
            pass
        finally:
            _ide_server = None


def _setup_cleanup_handlers() -> None:
    """Set up signal handlers and atexit hooks for cleanup."""
    # Register atexit handler for normal exit
    atexit.register(_cleanup_server)
    
    # Register signal handlers for SIGTERM and SIGINT
    def signal_handler(signum, frame):
        _cleanup_server()
        # Re-raise the signal to allow normal termination
        signal.signal(signum, signal.SIG_DFL)
        signal.raise_signal(signum)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


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
# QUICK START GUIDE
# ============================================================================
#
# 🔍 CODE NAVIGATION
#     find_definition      - Jump to where a symbol is defined
#     find_references      - Find all usages of a symbol
#     get_hover_info       - Get type info and documentation
#     get_completions      - Get autocomplete suggestions
#
# 📖 UNDERSTANDING CODE
#     read_file            - Read file from disk (NOT buffer!)
#     get_symbols          - List all functions/classes in a file
#     get_project_structure - Browse directory tree
#     explain_symbol       - AI explanation of what a symbol does
#     summarize_code       - AI summary of file purpose
#
# ✏️  MAKING CHANGES
#     edit_buffer          - Line-based edits (preview first!)
#     find_and_replace     - Text-based substitutions
#     rename_symbol        - LSP-powered refactoring
#     extract_function     - Extract code into new function
#
# ✅ VERIFICATION & REVIEW
#     get_buffer_diff      - **PRIMARY TOOL** - Shows buffer vs disk
#     save_buffer          - Write changes to disk
#     discard_buffer       - Revert unsaved changes
#     get_diagnostics      - Get linter errors/warnings
#     quick_review         - AI code review
#
# 🐛 DEBUGGING
#     start_debug_session  - Start debugger with breakpoints
#     control_execution    - Step, continue, pause
#     inspect_state        - View variables and call stack
#
# ⚙️  ANALYSIS
#     analyze_dependencies - Find what a file depends on
#     summarize_changes    - Summarize uncommitted git changes
#     explain_error        - AI explanation of error messages
#
# 🔧 CONFIGURATION
#     get_otter_config     - See current project and detected runtimes
#     get_runtime_info     - Preview runtimes for other projects
#
# ============================================================================
# CORE CONCEPTS
# ============================================================================
#
# 📝 BUFFER vs DISK (Critical Distinction!)
#
#   DISK (saved state)
#     ↑ read_file() - Always reads saved version
#     ↑ save_buffer() - Writes buffer to disk
#     ↓ discard_buffer() - Reloads from disk
#
#   BUFFER (in-memory edits)
#     ↑ edit_buffer() - Modifies buffer
#     ↑ find_and_replace() - Modifies buffer
#
#   VERIFICATION
#     → get_buffer_diff() - Shows BUFFER vs DISK difference
#     → has_changes=false means buffer matches disk ✓
#
# 📋 TYPICAL WORKFLOWS
#
#   Safe Editing:
#     1. edit_buffer(preview=true) → review diff
#     2. edit_buffer(preview=false) → apply changes
#     3. get_buffer_diff() → verify all changes
#     4. save_buffer() → commit to disk
#
#   Experimental Editing:
#     1. find_and_replace(...) → make changes
#     2. get_buffer_diff() → review
#     3. discard_buffer() → revert if not satisfied
#     4. get_buffer_diff() → verify has_changes=false
#
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
    """Read file from disk with optional import/diagnostic analysis.

    **⚠️ READS FROM DISK, NOT BUFFER** - Use get_buffer_diff() to see unsaved edits.

    Args:
        path: File path (relative to project root or absolute)
        line_range: (start, end) tuple for specific range (1-indexed, inclusive)
        include_imports: Detect import statements (signatures not yet implemented)
        include_diagnostics: Include LSP diagnostics (errors, warnings, etc.)
        context_lines: Extra lines around line_range

    Returns:
        - content: File with line numbers "LINE_NUMBER|CONTENT"
        - total_lines, language, expanded_imports, diagnostics
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
) -> Dict[str, Any]:
    """Get linting and type checking results.

    Retrieve diagnostics from LSP servers (errors, warnings, hints).

    Args:
        file: Optional file path to get diagnostics for (None = all files)
        severity: Optional list to filter by severity (e.g., ["error", "warning"])
        include_fixes: Whether to include suggested fixes

    Returns:
        DiagnosticsResult containing:
            - diagnostics: List of diagnostics with severity, message, location, and optional fixes
            - total_count: Total number of diagnostics found
            - file: File that was analyzed (if specific file was requested)
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
    file: str | None = None,
    module: str | None = None,
    configuration: str | None = None,
    breakpoints: List[int] | None = None,
    args: List[str] | None = None,
    env: Dict[str, str] | None = None,
    stop_on_entry: bool = False,
    just_my_code: bool = True,
) -> Dict[str, Any]:
    """Start a debug session for a file or module.

    Uses Neovim's DAP client with language-specific debug adapters:
    - Python: debugpy
    - JavaScript/TypeScript: node-debug2
    - Rust: lldb-vscode
    - Go: delve

    Args:
        file: File path to debug (relative to project root). Mutually exclusive with module.
        module: Module name to debug (e.g., "uvicorn" for `python -m uvicorn`).
                Mutually exclusive with file.
        configuration: Debug config name ("Launch file", "pytest: current file", etc.)
                      Defaults to first available config for file type
        breakpoints: Optional list of line numbers for breakpoints (requires file parameter)
        args: Optional command-line arguments for the program
        env: Optional environment variables to set for the debug session
             Example: {"DOPPLER_ENV": "1", "DEBUG": "true"}
        stop_on_entry: Whether to stop at the first line of the program (default: False)
        just_my_code: Whether to debug only user code, skipping library code (default: True)
        
    Note:
        The debugger runs in Otter's current project (same as LSP, file operations, etc).
        Runtime (Python/Node/etc) is auto-detected from the project's venv.
        To debug a different project, start a separate Otter instance for that project.

    Returns:
        DebugSession with session_id, status, file/module, configuration, breakpoints,
        output, pid, and launch details

    Examples:
        Debug a Python file with breakpoints:
        {"file": "src/main.py", "breakpoints": [10, 25, 42]}

        Debug uvicorn server with environment variables:
        {
            "module": "uvicorn",
            "args": ["app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
            "env": {"DOPPLER_ENV": "1"}
        }

        Debug pytest tests:
        {
            "module": "pytest",
            "args": ["tests/test_app.py", "-v"]
        }

        Debug with configuration:
        {"file": "tests/test_app.py", "configuration": "pytest: current file"}
    """
    ide = await get_ide_server()
    result = await ide.start_debug_session(
        file, module, configuration, breakpoints, args, env, stop_on_entry, just_my_code
    )
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
async def get_debug_session_info(session_id: str | None = None) -> Dict[str, Any]:
    """Get information about a debug session (current, past, or specific).

    Args:
        session_id: Optional session ID to query. If not provided, gets the currently
                   active session. If provided, can query terminated sessions (kept
                   for 5 minutes for crashes, 30 seconds for clean exits).

    Returns:
        DebugSession with detailed information:
        - status: "running" | "paused" | "terminated" | "no_session"
        - session_id: UUID of the session
        - pid: Process ID (if running)
        - stdout: Standard output from the process
        - stderr: Standard error (separate from stdout!)
        - exit_code: Exit code (if terminated)
        - crash_reason: Human-readable reason for termination
        - uptime_seconds: How long the process ran
        - launch_args: Command-line arguments used
        - launch_env: Environment variables used
        - launch_cwd: Working directory used

    Examples:
        # Get current session
        >>> info = get_debug_session_info()
        
        # Query a specific session (even if terminated)
        >>> session = start_debug_session(file="app.py")
        >>> # Program crashes...
        >>> info = get_debug_session_info(session_id=session["session_id"])
        >>> print(info["stderr"])  # See crash details
        >>> print(info["crash_reason"])  # "Process exited with code 1"
        
        # Crashed sessions persist for 5 minutes for diagnosis!
    """
    ide = await get_ide_server()
    result = await ide.get_session_info(session_id)
    if result:
        return _to_dict(result)
    return {"status": "no_session"}


# ============================================================================
# Buffer Editing Tools
# ============================================================================
# See CORE CONCEPTS section at top of file for buffer vs disk mental model.
# ============================================================================


@mcp.tool()
async def get_buffer_info(file: str) -> Dict[str, Any]:
    """Get information about a buffer's current state.
    
    Use this before editing to check if the buffer is already open and has
    unsaved changes.
    
    Args:
        file: Path to file (relative to project root or absolute)
    
    Returns:
        Buffer information:
        - is_open: Whether file is open in a buffer
        - is_modified: Whether buffer has unsaved changes
        - line_count: Number of lines in the buffer
        - language: File type/language
    
    Example:
        Check buffer state before editing:
        {
          "file": "src/models.py"
        }
    """
    server = await get_ide_server()
    result = await server.get_buffer_info(file)
    return _to_dict(result)


@mcp.tool()
async def edit_buffer(
    file: str,
    edits: List[Dict[str, Any]],
    preview: bool = True
) -> Dict[str, Any]:
    """Edit lines in a buffer.
    
    Make line-based changes to a file. Can preview changes as a unified diff
    before applying them.
    
    Args:
        file: Path to file (relative to project root or absolute)
        edits: List of edit operations, each with:
            - line_start: Starting line number (1-indexed)
            - line_end: Ending line number (1-indexed, inclusive)
            - new_text: Replacement text (may contain \\n for multiple lines)
        preview: If true, return diff without applying. If false, apply changes.
    
    Returns:
        If preview=true:
        - preview: Unified diff showing changes
        - applied: false
        
        If preview=false:
        - applied: true
        - success: Whether edits were successful
        - line_count: New line count after edits
        - is_modified: Whether buffer is now modified
    
    Example:
        Preview changes first:
        {
          "file": "src/models.py",
          "edits": [
            {
              "line_start": 10,
              "line_end": 12,
              "new_text": "def new_function():\\n    pass\\n"
            }
          ],
          "preview": true
        }
        
        Then apply if satisfied:
        {
          "file": "src/models.py",
          "edits": [...],
          "preview": false
        }
    """
    from .models.responses import BufferEdit
    
    server = await get_ide_server()
    
    # Convert dict edits to BufferEdit objects
    buffer_edits = [
        BufferEdit(
            line_start=edit["line_start"],
            line_end=edit["line_end"],
            new_text=edit["new_text"]
        )
        for edit in edits
    ]
    
    result = await server.edit_buffer(file, buffer_edits, preview)
    return _to_dict(result)


@mcp.tool()
async def save_buffer(file: str) -> Dict[str, Any]:
    """Write buffer to disk (persists changes).

    **💡 Best practice:** Always call get_buffer_diff() first to review changes.

    Args:
        file: Path to file

    Returns:
        - success: true if saved
        - is_modified: false after successful save
        - error: Error message if failed

    Note: Buffer must be open (via edit_buffer or find_and_replace).
    """
    server = await get_ide_server()
    result = await server.save_buffer(file)
    return _to_dict(result)


@mcp.tool()
async def discard_buffer(file: str) -> Dict[str, Any]:
    """Revert unsaved changes (reload from disk).

    **⚠️ Destructive** - All unsaved changes permanently lost. Buffer stays open.

    Args:
        file: Path to file

    Returns:
        - success: true if discarded
        - is_modified: false after successful discard
        - error: Error message if failed

    **💡 Verify:** Call get_buffer_diff() after - should show has_changes=false.
    """
    server = await get_ide_server()
    result = await server.discard_buffer(file)
    return _to_dict(result)


@mcp.tool()
async def get_buffer_diff(file: str) -> Dict[str, Any]:
    """**PRIMARY VERIFICATION TOOL** - Shows buffer vs disk diff.

    **When to use:**
    - Before save_buffer() - review what will be written to disk
    - After discard_buffer() - verify has_changes=false (success indicator)
    - After multiple edits - see accumulated changes

    Args:
        file: Path to file

    Returns:
        - has_changes: true if buffer differs from disk
        - diff: Unified diff string (null if no changes)
        - error: Error message if failed

    Example:
        get_buffer_diff(file="src/models.py")
        → {"has_changes": true, "diff": "--- a/src/models.py..."}
        
        After discard_buffer():
        → {"has_changes": false}  # Success!
    """
    server = await get_ide_server()
    result = await server.get_buffer_diff(file)
    return _to_dict(result)


@mcp.tool()
async def find_and_replace(
    file: str,
    find: str,
    replace: str,
    occurrence: str = "all",
    preview: bool = True
) -> Dict[str, Any]:
    """Find and replace text in a file (convenience tool).
    
    Text-based alternative to edit_buffer. More natural for simple substitutions
    like changing configuration values or fixing typos.
    
    Args:
        file: Path to file (relative to project root or absolute)
        find: Text to find (exact match, whitespace-sensitive)
        replace: Text to replace with
        occurrence: Which occurrences to replace:
            - "all": Replace all occurrences (default)
            - "first": Replace only the first occurrence
            - "2", "3", etc.: Replace specific occurrence (1-indexed)
        preview: If true, return preview diff. If false, apply changes.
    
    Returns:
        Find/replace result:
        - success: Whether operation succeeded
        - preview: Unified diff (if preview=true)
        - applied: Whether changes were applied
        - replacements_made: Number of replacements
        - line_count: Line count after changes (if applied)
        - is_modified: Modified status (if applied)
        - error: Error message if failed
    
    Example (preview):
        Change log level:
        {
          "file": "config.py",
          "find": "log_level = \\"INFO\\"",
          "replace": "log_level = \\"DEBUG\\"",
          "occurrence": "all",
          "preview": true
        }
    
    Example (apply):
        Fix typo (first occurrence only):
        {
          "file": "README.md",
          "find": "teh",
          "replace": "the",
          "occurrence": "first",
          "preview": false
        }
    
    When to use vs edit_buffer:
        - find_and_replace: Simple text substitutions, config changes
        - edit_buffer: Structural changes, inserting lines, precise edits
    
    Note:
        - Whitespace-sensitive (spaces/tabs must match exactly)
        - For complex edits, use edit_buffer with line numbers
        - Internally uses edit_buffer for actual modifications
    """
    server = await get_ide_server()
    result = await server.find_and_replace(file, find, replace, occurrence, preview)
    return _to_dict(result)


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
# Documentation Resources
# ============================================================================
# These resources provide structured guidance to LLM agents using Otter.
# Agents can query these to understand concepts and workflows.


@mcp.resource("otter://docs/quick-start")
async def get_quick_start_guide() -> str:
    """Quick start guide showing all available tools by category."""
    return """# Otter Quick Start Guide

## 🔍 Code Navigation
- **find_definition** - Jump to where a symbol is defined
- **find_references** - Find all usages of a symbol
- **get_hover_info** - Get type info and documentation
- **get_completions** - Get autocomplete suggestions

## 📖 Understanding Code
- **read_file** - Read file from disk (NOT buffer!)
- **get_symbols** - List all functions/classes in a file
- **get_project_structure** - Browse directory tree
- **explain_symbol** - AI explanation of what a symbol does
- **summarize_code** - AI summary of file purpose

## ✏️ Making Changes
- **edit_buffer** - Line-based edits (preview first!)
- **find_and_replace** - Text-based substitutions
- **rename_symbol** - LSP-powered refactoring
- **extract_function** - Extract code into new function

## ✅ Verification & Review
- **get_buffer_diff** - **PRIMARY TOOL** - Shows buffer vs disk
- **save_buffer** - Write changes to disk
- **discard_buffer** - Revert unsaved changes
- **get_diagnostics** - Get linter errors/warnings
- **quick_review** - AI code review

## 🐛 Debugging
- **start_debug_session** - Start debugger with breakpoints
- **control_execution** - Step, continue, pause
- **inspect_state** - View variables and call stack

## ⚙️ Analysis
- **analyze_dependencies** - Find what a file depends on
- **summarize_changes** - Summarize uncommitted git changes
- **explain_error** - AI explanation of error messages
"""


@mcp.resource("otter://docs/buffer-vs-disk")
async def get_buffer_vs_disk_guide() -> str:
    """Critical explanation of the buffer vs disk distinction."""
    return """# Buffer vs Disk - CRITICAL CONCEPT

This is the **most important concept** to understand when using Otter.

## The Mental Model

```
DISK (saved state)
  ↑ read_file() - Always reads saved version
  ↑ save_buffer() - Writes buffer to disk
  ↓ discard_buffer() - Reloads from disk

BUFFER (in-memory edits)
  ↑ edit_buffer() - Modifies buffer
  ↑ find_and_replace() - Modifies buffer

VERIFICATION
  → get_buffer_diff() - Shows BUFFER vs DISK difference
  → has_changes=false means buffer matches disk ✓
```

## Key Rules

1. **read_file() ALWAYS reads from DISK** - It never shows buffer contents
   - If you've made edits that haven't been saved, read_file() won't show them
   - To see pending edits, use get_buffer_diff()

2. **Edits are in-memory until save_buffer()**
   - edit_buffer() and find_and_replace() modify the buffer
   - Changes are NOT on disk until you call save_buffer()

3. **get_buffer_diff() is your verification tool**
   - Shows what's different between buffer and disk
   - Use before save_buffer() to review what will be written
   - Use after discard_buffer() to verify it worked (should show has_changes=false)

4. **has_changes=false is the success indicator**
   - After save_buffer() - buffer should match disk
   - After discard_buffer() - buffer should match disk

## Common Mistakes

### ❌ Mistake 1: Using read_file() to check edits
```
edit_buffer(file="src/models.py", ...)
read_file("src/models.py")  # Still shows old version!
```

### ✅ Correct:
```
edit_buffer(file="src/models.py", ...)
get_buffer_diff("src/models.py")  # Shows pending changes
```

### ❌ Mistake 2: Saving without review
```
edit_buffer(preview=false, ...)
save_buffer(...)  # What did I just save?
```

### ✅ Correct:
```
edit_buffer(preview=false, ...)
get_buffer_diff(...)  # Review all changes
save_buffer(...)  # Now I know what I'm saving
```

### ❌ Mistake 3: Not verifying discard
```
discard_buffer(...)
# Hope it worked!
```

### ✅ Correct:
```
discard_buffer(...)
diff = get_buffer_diff(...)
# diff.has_changes should be false - verified!
```
"""


@mcp.resource("otter://docs/workflows")
async def get_common_workflows() -> str:
    """Common workflows for editing, reviewing, and saving code."""
    return """# Common Workflows

## Safe Editing (Recommended)

Always preview before applying, then verify before saving:

```
1. edit_buffer(preview=true, ...)
   → Review the diff to make sure it's correct

2. edit_buffer(preview=false, ...)
   → Apply the changes to buffer

3. get_buffer_diff(...)
   → Verify all accumulated changes

4. save_buffer(...)
   → Commit to disk
```

**Why this works:**
- Preview catches mistakes before applying
- get_buffer_diff() shows the complete picture
- You always know exactly what you're saving

## Experimental Editing

Try changes and revert if not satisfied:

```
1. find_and_replace(...)
   → Make experimental changes

2. get_buffer_diff(...)
   → Review what changed

3. discard_buffer(...)
   → Revert if not satisfied

4. get_buffer_diff(...)
   → Verify has_changes=false (success!)
```

**When to use:**
- Exploring different approaches
- Not sure if change will work
- Want to try something without commitment

## Multiple Edits Before Save

Accumulate several changes, then review all at once:

```
1. edit_buffer(...)
   → First change

2. find_and_replace(...)
   → Second change

3. edit_buffer(...)
   → Third change

4. get_buffer_diff(...)
   → Review ALL changes together

5. save_buffer() or discard_buffer()
   → Commit all or revert all
```

**Why this is powerful:**
- Changes accumulate in buffer
- Single diff shows complete picture
- All-or-nothing commit

## Tool Selection

**Simple text replacement:**
```
find_and_replace(
    file="config.py",
    find='log_level = "INFO"',
    replace='log_level = "DEBUG"',
    occurrence="all",
    preview=true
)
```

**Structural changes:**
```
edit_buffer(
    file="src/models.py",
    edits=[{
        "line_start": 10,
        "line_end": 15,
        "new_text": "def new_function():\\n    pass\\n"
    }],
    preview=true
)
```

**See pending edits:**
```
get_buffer_diff(file="src/models.py")
# NOT read_file() - that shows disk!
```

## Best Practices

### ✅ Always DO:
- Preview edits first (preview=true)
- Call get_buffer_diff() before save_buffer()
- Verify after discard_buffer() (has_changes=false)
- Use find_and_replace for simple substitutions
- Use edit_buffer for structural changes

### ❌ Never DO:
- Use read_file() to check pending edits
- Save without reviewing
- Assume discard worked without checking
- Mix up buffer state with disk state
"""


@mcp.resource("otter://docs/troubleshooting")
async def get_troubleshooting_guide() -> str:
    """Solutions to common problems and confusions."""
    return """# Troubleshooting Guide

## Problem: My edits aren't showing in read_file()

**Symptoms:**
- Called edit_buffer() or find_and_replace()
- read_file() still shows old content

**Cause:**
read_file() reads from DISK, not BUFFER.

**Solution:**
Use get_buffer_diff() to see pending edits:
```
get_buffer_diff(file="src/models.py")
→ Shows buffer vs disk difference
```

## Problem: I'm not sure what I'm about to save

**Symptoms:**
- Made several edits
- Don't remember all the changes
- Afraid to call save_buffer()

**Solution:**
Always call get_buffer_diff() before saving:
```
diff = get_buffer_diff(file="src/models.py")
print(diff.diff)  # Review unified diff
# If satisfied:
save_buffer(file="src/models.py")
```

## Problem: Did discard_buffer() work?

**Symptoms:**
- Called discard_buffer()
- Not sure if it reverted correctly

**Solution:**
Verify with get_buffer_diff():
```
discard_buffer(file="src/models.py")
diff = get_buffer_diff(file="src/models.py")
# diff.has_changes should be false!
```

## Problem: Changes disappeared after reading file

**Symptoms:**
- Made edits
- read_file() shows old version
- Worried changes were lost

**Cause:**
Changes are still in buffer! read_file() just shows disk.

**Solution:**
Your changes are safe in buffer:
```
get_buffer_diff(...)  # See your changes
save_buffer(...)      # Save them to disk
```

## Problem: Getting confused about state

**Symptoms:**
- Don't know if file is modified
- Not sure what's in buffer vs disk

**Solution:**
Use get_buffer_info() and get_buffer_diff():
```
info = get_buffer_info(file="src/models.py")
print(info.is_modified)  # Is buffer modified?

diff = get_buffer_diff(file="src/models.py")
print(diff.has_changes)  # Does buffer differ from disk?
```

## Success Indicators

You'll know things worked when:

- ✅ save_buffer() → is_modified=false
- ✅ discard_buffer() → has_changes=false (check with get_buffer_diff)
- ✅ edit_buffer(preview=true) → shows expected diff
- ✅ get_buffer_diff() after save → has_changes=false

## Quick Reference

**See saved content:** read_file()
**See pending edits:** get_buffer_diff()
**Review before save:** get_buffer_diff() (REQUIRED!)
**Verify discard:** get_buffer_diff() (should be has_changes=false)
**Check buffer state:** get_buffer_info()
"""


# ============================================================================
# Configuration & Runtime Management
# ============================================================================


@mcp.tool()
async def get_otter_config() -> Dict[str, Any]:
    """Get Otter's current configuration and runtime detection info.
    
    Shows the current project's configuration including:
    - Project path that Otter is operating on
    - Detected runtimes (Python, Node, Rust, Go) for THIS project
    - Configuration from .otter.toml (if present)
    - LSP and DAP status
    
    ⚠️  NOTE: All Otter tools (LSP, DAP, file operations) operate on this same project.
    To work on a different project, start a separate Otter instance for it.
    Use get_runtime_info() to check runtimes for other projects (read-only).
    
    Returns:
        Configuration including:
        - project_path: Current project Otter is configured for
        - project_name: Name of the project directory
        - config_file: Path to .otter.toml (if exists)
        - runtimes: Detected runtimes for THIS project
          - path: Resolved path to runtime executable
          - version: Version string
          - source: How it was detected (venv, system, etc.)
          - is_symlink: True if the runtime is a symlink (e.g., UV venvs)
          - symlink_path: Original symlink path (e.g., .venv/bin/python)
          - resolved_path: Where the symlink points to
        - lsp_enabled: Whether LSP is enabled
        - dap_enabled: Whether DAP is enabled
    
    Examples:
        # Check what project Otter is working on
        >>> config = get_otter_config()
        >>> print(f"Working on: {config['project_name']}")
        >>> print(f"Python: {config['runtimes']['python']['path']}")
        
        # Check if Python is a symlink (e.g., UV venv)
        >>> python = config['runtimes']['python']
        >>> if python.get('is_symlink'):
        ...     print(f"Using venv: {python['symlink_path']}")
        ...     print(f"Points to: {python['resolved_path']}")
        "Using venv: /path/to/project/.venv/bin/python"
        "Points to: /path/to/uv/python/cpython-.../python3.12"
        
        # Verify configuration before starting work
        >>> config = get_otter_config()
        >>> if not config['runtimes']['python']['available']:
        ...     print("Warning: No Python runtime detected!")
    """
    from otter.runtime import RuntimeResolver
    from otter.config import load_config
    
    project_path = get_project_path()
    config = load_config(Path(project_path))
    
    # Check if .otter.toml exists
    config_file = Path(project_path) / ".otter.toml"
    has_config_file = config_file.exists()
    
    # Detect runtimes for this project
    resolver = RuntimeResolver(Path(project_path))
    runtimes = {}
    
    for language in ["python", "javascript", "typescript", "rust", "go"]:
        try:
            runtime = resolver.resolve_runtime(language, config)
            runtime_dict = {
                "path": str(runtime.path),
                "version": runtime.version,
                "source": runtime.source,
                "available": True,
            }
            
            # Add symlink info for transparency
            if runtime.is_symlink and runtime.original_path:
                runtime_dict["is_symlink"] = True
                runtime_dict["symlink_path"] = runtime.original_path
                runtime_dict["resolved_path"] = runtime.path
            
            runtimes[language] = runtime_dict
        except Exception as e:
            runtimes[language] = {
                "available": False,
                "error": str(e),
            }
    
    result = {
        "project_path": project_path,
        "project_name": Path(project_path).name,
        "config_file": str(config_file) if has_config_file else None,
        "has_config_file": has_config_file,
        "runtimes": runtimes,
        "lsp_enabled": config.lsp.enabled if config else True,
        "dap_enabled": config.dap.enabled if config else True,
    }
    
    # Add explicit config values if .otter.toml exists
    if has_config_file and config:
        # Add any explicit runtime overrides from config
        explicit_runtimes = {}
        if hasattr(config, 'python_path') and config.python_path:
            explicit_runtimes['python'] = config.python_path
        
        if explicit_runtimes:
            result['explicit_runtime_overrides'] = explicit_runtimes
    
    return result


@mcp.tool()
async def get_runtime_info(
    project_path: str,
    language: str | None = None
) -> Dict[str, Any]:
    """Preview what runtimes would be detected for a different project.
    
    This is useful BEFORE debugging a different project to verify the correct
    runtime will be used. Does NOT change Otter's configuration.
    
    Args:
        project_path: Path to the project to check runtimes for
        language: Optional specific language to check (python, javascript, typescript, rust, go)
                 If not provided, checks all supported languages
    
    Returns:
        Dict with runtime information for the specified project:
        - path: Resolved path to runtime executable
        - version: Version string
        - source: How it was detected (venv, system, etc.)
        - is_symlink: True if the runtime is a symlink (e.g., UV venvs)
        - symlink_path: Original symlink path before resolution
        - resolved_path: Where the symlink points to
        
        If language not specified: Dict of all detected runtimes
    
    Examples:
        # Check Python runtime for fern-mono BEFORE debugging it
        >>> runtime = get_runtime_info(
        ...     project_path="/Users/user/fern-folder/fern-mono",
        ...     language="python"
        ... )
        >>> print(f"Would use: {runtime['path']}")
        >>> print(f"Source: {runtime['source']}")
        "Would use: /Users/user/fern-folder/fern-mono/.venv/bin/python"
        "Source: venv"
        
        # Check all runtimes for a project
        >>> runtimes = get_runtime_info("/path/to/project")
        >>> for lang, info in runtimes.items():
        ...     if info['available']:
        ...         print(f"{lang}: {info['path']}")
        
        # Check if a different project's venv has required dependencies
        >>> runtime = get_runtime_info(
        ...     project_path="/Users/user/other-project",
        ...     language="python"
        ... )
        >>> print(f"That project uses: {runtime['path']}")
        >>> print(f"Source: {runtime['source']}")
        
        Note: To debug that project, start a separate Otter instance for it.
    """
    from otter.runtime import RuntimeResolver
    from otter.config import load_config
    
    target_path = Path(project_path)
    if not target_path.exists():
        return {
            "error": f"Project path does not exist: {project_path}",
            "project_path": project_path,
        }
    
    config = load_config(target_path)
    resolver = RuntimeResolver(target_path)
    
    # Check specific language or all
    languages = [language] if language else ["python", "javascript", "typescript", "rust", "go"]
    
    results = {}
    for lang in languages:
        try:
            runtime = resolver.resolve_runtime(lang, config)
            runtime_dict = {
                "path": str(runtime.path),
                "version": runtime.version,
                "source": runtime.source,
                "available": True,
            }
            
            # Add symlink info for transparency
            if runtime.is_symlink and runtime.original_path:
                runtime_dict["is_symlink"] = True
                runtime_dict["symlink_path"] = runtime.original_path
                runtime_dict["resolved_path"] = runtime.path
            
            results[lang] = runtime_dict
        except Exception as e:
            results[lang] = {
                "available": False,
                "error": str(e),
            }
    
    # If single language requested, return just that runtime
    if language:
        result = results[language]
        result['project_path'] = project_path
        result['language'] = language
        return result
    
    # Otherwise return all runtimes
    return {
        "project_path": project_path,
        "project_name": target_path.name,
        "runtimes": results,
    }


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

    # Set up cleanup handlers FIRST to ensure proper shutdown
    _setup_cleanup_handlers()

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
    # Cleanup will happen automatically via atexit and signal handlers
    mcp.run()


if __name__ == "__main__":
    main()
