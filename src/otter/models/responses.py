from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


# Core navigation
@dataclass
class Definition:
    file: str
    line: int
    column: int
    symbol_name: str
    symbol_type: Literal[
        "function", "class", "variable", "module", "method", "property"
    ]
    docstring: Optional[str] = None
    signature: Optional[str] = (
        None  # Present for functions/methods, null for classes/variables
    )
    context_lines: List[str] = field(
        default_factory=list
    )  # Lines with format "LINE_NUM|CONTENT"
    source_module: Optional[str] = None
    has_alternatives: bool = False  # True if LSP returned multiple possible definitions


@dataclass
class Reference:
    file: str
    line: int
    column: int
    context: str
    is_definition: bool = False
    reference_type: Optional[str] = None  # e.g., "import", "usage", "type_hint"


@dataclass
class FileReferences:
    """References grouped by file."""

    file: str
    count: int
    references: List[Reference] = field(default_factory=list)


@dataclass
class ReferencesResult:
    """Structured result for find_references with grouping and metadata."""

    references: List[Reference]
    total_count: int
    grouped_by_file: List[FileReferences] = field(default_factory=list)


@dataclass
class SearchResult:
    file: str
    line: int
    match: str
    context: str


# Code intelligence
@dataclass
class CompletionsResult:
    """Structured result for code completions with metadata."""

    completions: List[Completion]
    total_count: int  # Total completions found
    returned_count: int  # Number returned (may be less if truncated)
    truncated: bool  # True if results were limited by max_results


@dataclass
class HoverInfo:
    symbol: str
    type: Optional[str]
    docstring: Optional[str]
    source_file: Optional[str]
    line: Optional[int] = None  # Position where hover was requested
    column: Optional[int] = None  # Position where hover was requested


@dataclass
class Completion:
    text: str
    kind: Optional[str] = None
    detail: Optional[str] = None
    documentation: Optional[str] = None  # Docstring or description from LSP
    sort_text: Optional[str] = None  # For ranking/sorting (internal use)


# Files & projects
@dataclass
class FileContent:
    content: str
    total_lines: int  # Total number of lines in the file
    expanded_imports: Optional[Dict[str, List[str]]] = None
    diagnostics: Optional[List["Diagnostic"]] = None
    language: Optional[str] = None  # File language (e.g., "python", "javascript")


@dataclass
class ProjectTree:
    """Directory tree structure with metadata.

    Tree structure no longer wraps root directory - returns children directly.

    Migration from v0.4.x:
        # Old format (v0.4.x):
        tree = {"project_name": {"type": "directory", "children": {...}}}

        # New format (v0.5.0+):
        tree = {"src": {...}, "tests": {...}, "README.md": {...}}
        # Root directory name already provided in 'root' field
    """

    root: str  # Absolute path to the root directory
    tree: Dict[str, Any]  # Directory contents (no wrapper for root)
    file_count: int = 0  # Total number of files
    directory_count: int = 0  # Total number of directories
    total_size: int = 0  # Total size of all files in bytes (0 if include_sizes=False)


@dataclass
class Symbol:
    """Symbol information from LSP document symbols.

    Represents a code symbol (class, function, method, variable, etc.)
    extracted from a source file via LSP.
    """

    name: str  # Symbol name
    type: str  # Symbol type: "class", "function", "method", "variable", etc.
    line: int  # Line number (1-indexed)
    column: int = 0  # Column number (0-indexed, matching LSP)
    children: Optional[List["Symbol"]] = None  # Nested symbols (methods in class, etc.)
    parent: Optional[str] = None  # Parent symbol name for hierarchy
    signature: Optional[str] = (
        None  # Function/method signature with params and return type
    )
    docstring: Optional[str] = None  # Extracted docstring/documentation
    detail: Optional[str] = (
        None  # Additional detail from LSP (type info, modifiers, etc.)
    )


@dataclass
class SymbolsResult:
    """Result of get_symbols with metadata.

    Wraps symbol list with file context and counts.
    """

    symbols: List[Symbol]  # List of symbols found
    file: str  # File path analyzed
    total_count: int  # Total symbols found (including filtered out)
    language: Optional[str] = None  # Detected language


# Refactoring
@dataclass
class Change:
    file: str
    line: int
    before: str
    after: str


@dataclass
class RenamePreview:
    changes: List[Change]
    affected_files: int
    total_changes: int


@dataclass
class RenameResult:
    changes_applied: int
    files_updated: int


@dataclass
class ExtractResult:
    new_function_name: str
    changes: List[Change]


# Smart/Semantic
@dataclass
class CodeExplanation:
    summary: str
    key_operations: List[str] = field(default_factory=list)
    complexity: Optional[str] = None
    potential_issues: Optional[List[str]] = None


@dataclass
class Improvement:
    line: int
    issue: str
    suggestion: str
    example: Optional[str] = None


@dataclass
class SemanticDiff:
    summary: str
    changes: List[str] = field(default_factory=list)


# Diagnostics & analysis
@dataclass
class Fix:
    description: str
    edit: Any


@dataclass
class RelatedInfo:
    message: str
    file: Optional[str] = None
    line: Optional[int] = None


@dataclass
class Diagnostic:
    severity: Literal["error", "warning", "info", "hint"]
    message: str
    file: str
    line: int
    column: int
    source: Optional[str] = None
    fix: Optional[Fix] = None
    related_information: List[RelatedInfo] = field(default_factory=list)


@dataclass
class DiagnosticsResult:
    """Result containing diagnostics with metadata.

    Wraps diagnostic list to ensure proper MCP protocol serialization
    and provide additional context.
    """

    diagnostics: List[Diagnostic]
    total_count: int
    file: Optional[str] = None  # File that was analyzed, if specific file requested


@dataclass
class DependencyGraph:
    file: str
    imports: List[str] = field(default_factory=list)
    imported_by: List[str] = field(default_factory=list)


@dataclass
class TestResults:
    total: int
    passed: int
    failed: int
    output: Optional[str] = None


@dataclass
class ExecutionTrace:
    calls: List[Dict[str, Any]]
    variables: Dict[str, Any]
    duration_ms: Optional[float] = None


@dataclass
class WorkspaceDiff:
    added: List[str] = field(default_factory=list)
    modified: List[str] = field(default_factory=list)
    deleted: List[str] = field(default_factory=list)


@dataclass
class ShellResult:
    command: str
    return_code: int
    stdout: str
    stderr: str


@dataclass
class IDEError:
    error_type: str
    message: str
    suggestions: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


# Debugging (DAP)
@dataclass
class BreakpointInfo:
    id: int
    file: str
    line: int
    verified: bool
    condition: Optional[str] = None
    hit_condition: Optional[str] = None
    log_message: Optional[str] = None


@dataclass
class StackFrame:
    id: int
    name: str
    file: str
    line: int
    column: int
    source: Optional[str] = None


@dataclass
class Variable:
    name: str
    value: str
    type: Optional[str] = None
    variables_reference: int = 0  # For nested objects


@dataclass
class Scope:
    name: str
    variables_reference: int
    expensive: bool = False


@dataclass
class ExecutionState:
    session_id: str
    status: Literal["running", "paused", "stopped", "exited"]
    reason: Optional[str] = None  # For paused: "breakpoint", "step", "exception", etc.
    thread_id: Optional[int] = None
    stack_frames: List[StackFrame] = field(default_factory=list)
    breakpoint_id: Optional[int] = None


@dataclass
class DebugSession:
    session_id: str
    status: Literal[
        "running", "paused", "stopped", "terminated", "no_session", "exited"
    ]
    file: Optional[str] = None  # File being debugged (None for module launches)
    module: Optional[str] = None  # Module being debugged (e.g., "uvicorn")
    configuration: Optional[str] = None  # Name of the debug configuration used
    breakpoints: List[BreakpointInfo] = field(default_factory=list)
    current_line: Optional[int] = None
    current_file: Optional[str] = None
    output: str = ""  # Combined stdout+stderr (for backwards compatibility)
    stdout: str = ""  # Standard output from the debugged process (may be truncated)
    stderr: str = ""  # Standard error from the debugged process (may be truncated)
    stdout_lines_total: int = (
        0  # Total lines of stdout captured (for truncation awareness)
    )
    stderr_lines_total: int = (
        0  # Total lines of stderr captured (for truncation awareness)
    )
    stdout_truncated: bool = False  # True if stdout was truncated in this response
    stderr_truncated: bool = False  # True if stderr was truncated in this response
    pid: Optional[int] = None  # Process ID of the debugged process
    exit_code: Optional[int] = None  # Process exit code (None if still running)
    terminated: bool = False  # True if the process has terminated
    uptime_seconds: Optional[float] = None  # How long the process has been running
    crash_reason: Optional[str] = None  # Human-readable reason for crash/termination
    error: Optional[str] = None  # Error message if session lookup failed
    launch_args: Optional[List[str]] = None  # Command-line arguments used
    launch_env: Optional[Dict[str, str]] = None  # Environment variables used
    launch_cwd: Optional[str] = None  # Working directory used
    diagnostic_info: List[str] = field(
        default_factory=list
    )  # Diagnostic logs (DAP config, initialization events, etc.)


@dataclass
class EvaluateResult:
    result: str
    type: Optional[str] = None
    variables_reference: int = 0


# AI-Powered Analysis
@dataclass
class CodeSummary:
    """Summary of code content."""

    file: str
    summary: str  # Full LLM response - structured by prompt
    detail_level: Literal["brief", "detailed"]


@dataclass
class ChangeSummary:
    """Summary of code changes (diff)."""

    file: str
    summary: str  # Full LLM response - structured by prompt
    git_ref: Optional[str] = None


@dataclass
class ReviewResult:
    """Result of quick code review."""

    file: str
    review: str  # Full LLM response - structured by prompt
    focus_areas: List[str]  # What was reviewed


@dataclass
class ErrorExplanation:
    """Explanation of an error message."""

    explanation: str  # Full LLM response - structured by prompt
    error_message: str  # Original error for reference
    context_file: Optional[str] = None
    context_line: Optional[int] = None


# Buffer Editing
@dataclass
class BufferEdit:
    """Single edit operation."""

    line_start: int  # 1-indexed start line
    line_end: int  # 1-indexed end line (inclusive)
    new_text: str  # Replacement text (may contain multiple lines)


@dataclass
class BufferInfo:
    """Information about a buffer."""

    file: str
    is_open: bool
    is_modified: bool
    line_count: int
    language: str


@dataclass
class EditResult:
    """Result of buffer editing operation."""

    file: str
    preview: Optional[str] = None  # Unified diff if preview=True
    applied: bool = False  # Whether changes were applied
    success: bool = True
    line_count: Optional[int] = None  # Line count after edits
    is_modified: Optional[bool] = None  # Modified status after edits
    error: Optional[str] = None


@dataclass
class SaveResult:
    """Result of saving a buffer to disk."""

    file: str
    success: bool
    is_modified: bool  # Should be False after successful save
    error: Optional[str] = None


@dataclass
class DiscardResult:
    """Result of discarding buffer changes."""

    file: str
    success: bool
    is_modified: bool  # Should be False after successful discard
    error: Optional[str] = None


@dataclass
class BufferDiff:
    """Diff between buffer and disk version."""

    file: str
    has_changes: bool
    diff: Optional[str] = None  # Unified diff if has_changes
    error: Optional[str] = None


@dataclass
class FindReplaceResult:
    """Result of find-and-replace operation."""

    file: str
    success: bool
    preview: Optional[str] = None  # Unified diff if preview=True
    applied: bool = False  # Whether changes were applied
    replacements_made: int = 0  # Number of replacements
    line_count: Optional[int] = None  # Line count after replacements
    is_modified: Optional[bool] = None  # Modified status after replacements
    error: Optional[str] = None


__all__ = [
    "Definition",
    "Reference",
    "FileReferences",
    "ReferencesResult",
    "SearchResult",
    "CompletionsResult",
    "HoverInfo",
    "Completion",
    "FileContent",
    "ProjectTree",
    "Symbol",
    "SymbolsResult",
    "Change",
    "RenamePreview",
    "RenameResult",
    "ExtractResult",
    "CodeExplanation",
    "Improvement",
    "SemanticDiff",
    "Fix",
    "RelatedInfo",
    "Diagnostic",
    "DiagnosticsResult",
    "DependencyGraph",
    "TestResults",
    "ExecutionTrace",
    "WorkspaceDiff",
    "ShellResult",
    "IDEError",
    "BreakpointInfo",
    "StackFrame",
    "Variable",
    "Scope",
    "ExecutionState",
    "DebugSession",
    "EvaluateResult",
    "CodeSummary",
    "ChangeSummary",
    "ReviewResult",
    "ErrorExplanation",
    "BufferEdit",
    "BufferInfo",
    "EditResult",
    "SaveResult",
    "DiscardResult",
    "BufferDiff",
    "FindReplaceResult",
]
