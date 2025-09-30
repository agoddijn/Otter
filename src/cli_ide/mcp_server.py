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
    methods, and nested references.

    Args:
        symbol: The symbol name to find the definition for
        file: Optional file path for context-aware resolution
        line: Optional line number for context-aware resolution

    Returns:
        Definition information including file, line, type, docstring, etc.
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
) -> List[Dict[str, Any]]:
    """Find all usages of a symbol.

    Find all references to a symbol with contextual snippets. For best results,
    provide the file and line number where the symbol appears.

    Args:
        symbol: The symbol name to find references for
        file: Optional file path for context-aware resolution
        line: Optional line number for position-based search
        scope: Search scope - "file", "package", or "project"

    Returns:
        List of references with file, line, column, and context information

    Example:
        find_references("UserModel", file="models.py", line=5)
    """
    ide = await get_ide_server()
    result = await ide.find_references(symbol, file, line, scope)
    return _to_dict(result)


@mcp.tool()
async def search(
    query: str,
    search_type: Literal["text", "regex", "semantic"] = "text",
    file_pattern: str | None = None,
    scope: str | None = None,
) -> List[Dict[str, Any]]:
    """Search codebase with varying levels of sophistication.

    Supports text search, regex patterns, and semantic code understanding.

    Args:
        query: Search query string
        search_type: Type of search - "text", "regex", or "semantic"
        file_pattern: Optional glob pattern to filter files
        scope: Optional directory scope to limit search

    Returns:
        List of search results with file, line, match, and context
    """
    ide = await get_ide_server()
    result = await ide.search(query, search_type, file_pattern, scope)
    return _to_dict(result)


# ============================================================================
# Code Intelligence Tools
# ============================================================================


@mcp.tool()
async def get_hover_info(file: str, line: int, column: int) -> Dict[str, Any]:
    """Get type information and documentation for a symbol.

    Get type information, docstrings, and method signatures at a position.

    Args:
        file: File path
        line: Line number (1-indexed)
        column: Column number (1-indexed)

    Returns:
        Hover information including symbol name, type, docstring, and source
    """
    ide = await get_ide_server()
    result = await ide.get_hover_info(file, line, column)
    return _to_dict(result)


@mcp.tool()
async def get_completions(
    file: str, line: int, column: int, context_lines: int = 10
) -> List[Dict[str, Any]]:
    """Get context-aware code completions.

    Get intelligent code completion suggestions at a specific position.

    Args:
        file: File path
        line: Line number (1-indexed)
        column: Column number (1-indexed)
        context_lines: Number of context lines to include

    Returns:
        List of completion suggestions with text, kind, and details
    """
    ide = await get_ide_server()
    result = await ide.get_completions(file, line, column, context_lines)
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

    Read files with optional import expansion, diagnostics, and context lines.

    Args:
        path: File path to read
        line_range: Optional tuple of (start_line, end_line) to read specific range
        include_imports: Whether to expand and include import information
        include_diagnostics: Whether to include linter/type errors inline
        context_lines: Number of context lines to include around the range

    Returns:
        File content with optional expanded imports and diagnostics
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
) -> Dict[str, Any]:
    """Get organized view of project layout.

    Explore project structure with configurable depth and detail.

    Args:
        path: Root path to analyze (defaults to current directory)
        max_depth: Maximum directory depth to traverse
        show_hidden: Whether to include hidden files/directories
        include_sizes: Whether to include file sizes

    Returns:
        Project tree structure with metadata
    """
    ide = await get_ide_server()
    result = await ide.get_project_structure(
        path, max_depth, show_hidden, include_sizes
    )
    return _to_dict(result)


@mcp.tool()
async def get_symbols(
    file: str, symbol_types: List[str] | None = None
) -> List[Dict[str, Any]]:
    """Extract all symbols from a file.

    Get classes, functions, methods, and other symbols from a file.

    Args:
        file: File path to analyze
        symbol_types: Optional list to filter by symbol type
                     (e.g., ["class", "function", "method"])

    Returns:
        List of symbols with name, type, line number, and hierarchy
    """
    ide = await get_ide_server()
    result = await ide.get_symbols(file, symbol_types)
    return _to_dict(result)


# ============================================================================
# Refactoring Tools
# ============================================================================


@mcp.tool()
async def rename_symbol(
    old_name: str, new_name: str, preview: bool = True
) -> Dict[str, Any]:
    """Safely rename a symbol across all references.

    Rename symbols with preview mode to see changes before applying.

    Args:
        old_name: Current symbol name
        new_name: New symbol name
        preview: If True, returns preview without applying changes

    Returns:
        RenamePreview (if preview=True) or RenameResult with changes made
    """
    ide = await get_ide_server()
    result = await ide.rename_symbol(old_name, new_name, preview)
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
# Smart/Semantic Analysis Tools
# ============================================================================


@mcp.tool()
async def explain_code(
    file: str,
    line_range: Tuple[int, int] | None = None,
    detail_level: Literal["brief", "normal", "detailed"] = "normal",
) -> Dict[str, Any]:
    """Get natural language explanation of code.

    Understand what code does with AI-powered explanations.

    Args:
        file: File path to analyze
        line_range: Optional tuple of (start_line, end_line) to explain specific range
        detail_level: Level of detail - "brief", "normal", or "detailed"

    Returns:
        Code explanation with summary, key operations, complexity, and potential issues
    """
    ide = await get_ide_server()
    result = await ide.explain_code(file, line_range, detail_level)
    return _to_dict(result)


@mcp.tool()
async def suggest_improvements(
    file: str, focus_areas: List[str] | None = None
) -> List[Dict[str, Any]]:
    """Get actionable code improvement suggestions.

    Analyze code for potential improvements in various areas.

    Args:
        file: File path to analyze
        focus_areas: Optional list of areas to focus on
                    (e.g., ["performance", "readability", "type_safety", "error_handling"])

    Returns:
        List of improvement suggestions with line numbers and examples
    """
    ide = await get_ide_server()
    result = await ide.suggest_improvements(file, focus_areas)
    return _to_dict(result)


@mcp.tool()
async def semantic_diff(
    file: str,
    from_revision: str = "HEAD~1",
    to_revision: str = "HEAD",
) -> Dict[str, Any]:
    """Express code changes in natural language.

    Get semantic understanding of what changed between git revisions.

    Args:
        file: File path to analyze
        from_revision: Starting git revision (default: HEAD~1)
        to_revision: Ending git revision (default: HEAD)

    Returns:
        Semantic diff with summary and list of changes in natural language
    """
    ide = await get_ide_server()
    result = await ide.semantic_diff(file, from_revision, to_revision)
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
# Execution & Testing Tools
# ============================================================================


@mcp.tool()
async def run_tests(
    file_or_pattern: str | None = None,
    test_name: str | None = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Execute tests with smart selection.

    Run tests with flexible targeting (file, pattern, or specific test).

    Args:
        file_or_pattern: Optional file path or pattern (None = all tests)
        test_name: Optional specific test name to run
        verbose: Whether to include verbose output

    Returns:
        Test results with counts, pass/fail status, and output
    """
    ide = await get_ide_server()
    result = await ide.run_tests(file_or_pattern, test_name, verbose)
    return _to_dict(result)


@mcp.tool()
async def trace_execution(
    function_or_file: str,
    arguments: Dict[str, Any] | None = None,
    max_depth: int = 5,
) -> Dict[str, Any]:
    """Understand runtime behavior with execution tracing.

    Trace function execution to see call stack and variable values.

    Args:
        function_or_file: Function name or file to trace
        arguments: Optional arguments to pass to the function
        max_depth: Maximum call stack depth to trace

    Returns:
        Execution trace with calls, variables, and timing information
    """
    ide = await get_ide_server()
    result = await ide.trace_execution(function_or_file, arguments, max_depth)
    return _to_dict(result)


# ============================================================================
# Workspace Management & Utility Tools
# ============================================================================


@mcp.tool()
async def mark_position(name: str) -> str:
    """Mark current workspace state for later comparison.

    Create a named checkpoint to track changes during complex operations.

    Args:
        name: Name for this position marker

    Returns:
        Confirmation message
    """
    ide = await get_ide_server()
    await ide.mark_position(name)
    return f"Position marked as '{name}'"


@mcp.tool()
async def diff_since_mark(name: str) -> Dict[str, Any]:
    """Show changes since a marked position.

    Compare current workspace state to a previously marked position.

    Args:
        name: Name of the position marker to compare against

    Returns:
        Workspace diff showing added, modified, and deleted files
    """
    ide = await get_ide_server()
    result = await ide.diff_since_mark(name)
    return _to_dict(result)


@mcp.tool()
async def vim_command(command: str) -> str:
    """Execute raw Neovim command.

    Direct access to Neovim functionality for advanced operations.

    Args:
        command: Neovim command to execute (e.g., ":set relativenumber")

    Returns:
        Command output or confirmation
    """
    ide = await get_ide_server()
    result = await ide.vim_command(command)
    return result


@mcp.tool()
async def shell(command: str, working_dir: str | None = None) -> Dict[str, Any]:
    """Execute shell command in the workspace.

    Run arbitrary shell commands with optional working directory.

    Args:
        command: Shell command to execute
        working_dir: Optional working directory (defaults to project root)

    Returns:
        Shell result with command, return code, stdout, and stderr
    """
    ide = await get_ide_server()
    result = await ide.shell(command, working_dir)
    return _to_dict(result)


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
- Refactoring tools (rename, extract function)
- AI-powered analysis (explain code, suggest improvements, semantic diff)
- Diagnostics and testing
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
