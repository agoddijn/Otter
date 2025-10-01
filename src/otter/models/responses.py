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
    signature: Optional[str] = None
    context_lines: List[str] = field(default_factory=list)
    source_module: Optional[str] = None


@dataclass
class Reference:
    file: str
    line: int
    column: int
    context: str


@dataclass
class SearchResult:
    file: str
    line: int
    match: str
    context: str


# Code intelligence
@dataclass
class HoverInfo:
    symbol: str
    type: Optional[str]
    docstring: Optional[str]
    source_file: Optional[str]


@dataclass
class Completion:
    text: str
    kind: Optional[str] = None
    detail: Optional[str] = None


# Files & projects
@dataclass
class FileContent:
    content: str
    expanded_imports: Optional[Dict[str, List[str]]] = None
    diagnostics: Optional[List["Diagnostic"]] = None


@dataclass
class ProjectTree:
    root: str
    tree: Dict[str, Any]


@dataclass
class Symbol:
    name: str
    type: str
    line: int
    children: Optional[List["Symbol"]] = None
    parent: Optional[str] = None


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
    status: Literal["running", "paused", "stopped", "exited"]
    file: str
    configuration: str  # Name of the debug configuration used
    breakpoints: List[BreakpointInfo] = field(default_factory=list)
    current_line: Optional[int] = None
    current_file: Optional[str] = None


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
    summary: str
    detail_level: Literal["brief", "detailed"]
    key_components: Optional[List[str]] = None  # For detailed summaries
    complexity: Optional[Literal["low", "medium", "high"]] = None


@dataclass
class ChangeSummary:
    """Summary of code changes (diff)."""
    file: str
    summary: str
    changes_type: List[str]  # e.g., ["refactor", "bugfix", "feature"]
    breaking_changes: List[str] = field(default_factory=list)
    affected_functionality: List[str] = field(default_factory=list)


@dataclass
class ReviewIssue:
    """Issue found during code review."""
    severity: Literal["critical", "warning", "suggestion"]
    category: str  # e.g., "security", "performance", "bugs", "style"
    line: Optional[int]
    message: str
    suggestion: Optional[str] = None


@dataclass
class ReviewResult:
    """Result of quick code review."""
    file: str
    overall_assessment: str
    issues: List[ReviewIssue]
    focus_areas: List[str]  # What was reviewed


@dataclass
class ErrorExplanation:
    """Explanation of an error message."""
    error_type: str
    explanation: str
    likely_causes: List[str]
    suggested_fixes: List[str]
    context_file: Optional[str] = None
    context_line: Optional[int] = None


__all__ = [
    "Definition",
    "Reference",
    "SearchResult",
    "HoverInfo",
    "Completion",
    "FileContent",
    "ProjectTree",
    "Symbol",
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
    "ReviewIssue",
    "ReviewResult",
    "ErrorExplanation",
]
