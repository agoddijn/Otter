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
]
