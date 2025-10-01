from __future__ import annotations

import os
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from .models.responses import (
    BreakpointInfo,
    ChangeSummary,
    CodeSummary,
    Completion,
    CompletionsResult,
    DebugSession,
    Definition,
    DependencyGraph,
    Diagnostic,
    ErrorExplanation,
    ExecutionState,
    ExtractResult,
    FileContent,
    HoverInfo,
    ProjectTree,
    Reference,
    ReferencesResult,
    RenamePreview,
    RenameResult,
    ReviewResult,
    SearchResult,
    Symbol,
    SymbolsResult,
)
from .neovim.client import NeovimClient
from .services.ai import AIService
from .services.analysis import AnalysisService
from .services.debugging import DebugService
from .services.navigation import NavigationService
from .services.refactoring import RefactoringService
from .services.workspace import WorkspaceService


class CliIdeServer:
    """Server facade delegating requests to service layers.

    Manages a persistent Neovim instance for LSP-powered code intelligence.
    """

    def __init__(self, project_path: Optional[str] = None) -> None:
        self.project_path = project_path or os.getcwd()

        # Initialize Neovim client
        self.nvim_client = NeovimClient(project_path=self.project_path)

        # Initialize services with Neovim client
        self.navigation = NavigationService(
            nvim_client=self.nvim_client, project_path=self.project_path
        )  # type: ignore
        self.refactoring = RefactoringService(
            project_path=self.project_path, nvim_client=self.nvim_client
        )  # type: ignore
        self.analysis = AnalysisService(
            nvim_client=self.nvim_client, project_path=self.project_path
        )  # type: ignore
        self.workspace = WorkspaceService(  # type: ignore
            project_path=self.project_path, nvim_client=self.nvim_client
        )
        self.debugging = DebugService(  # type: ignore
            nvim_client=self.nvim_client, project_path=self.project_path
        )
        self.ai = AIService(nvim_client=self.nvim_client)  # Pass nvim_client for LSP integration

    async def start(self) -> None:
        """Start the Neovim instance and initialize LSP servers.

        Raises:
            DependencyError: If required system dependencies are missing
        """
        # Check system dependencies before starting
        from .utils.dependencies import check_dependencies_or_raise

        check_dependencies_or_raise(verbose=False)

        await self.nvim_client.start()

    async def stop(self) -> None:
        """Stop the Neovim instance and clean up resources."""
        await self.nvim_client.stop()

    # Navigation & Discovery
    async def find_definition(
        self, symbol: str, file: Optional[str] = None, line: Optional[int] = None
    ) -> Definition:
        return await self.navigation.find_definition(symbol, file, line)

    async def find_references(
        self,
        symbol: str,
        file: Optional[str] = None,
        line: Optional[int] = None,
        scope: Literal["file", "package", "project"] = "project",
        exclude_definition: bool = False,
    ) -> ReferencesResult:
        return await self.navigation.find_references(symbol, file, line, scope, exclude_definition)

    async def search(
        self,
        query: str,
        search_type: Literal["text", "regex", "semantic"] = "text",
        file_pattern: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> List[SearchResult]:
        return await self.navigation.search(query, search_type, file_pattern, scope)

    # Code Intelligence
    async def get_hover_info(
        self,
        file: str,
        symbol: Optional[str] = None,
        line: Optional[int] = None,
        column: Optional[int] = None,
    ) -> HoverInfo:
        return await self.navigation.get_hover_info(file, symbol, line, column)

    async def get_completions(
        self, file: str, line: int, column: int, max_results: int = 50
    ) -> CompletionsResult:
        return await self.navigation.get_completions(file, line, column, max_results)

    # File & Project
    async def read_file(
        self,
        path: str,
        line_range: Optional[Tuple[int, int]] = None,
        include_imports: bool = False,
        include_diagnostics: bool = False,
        context_lines: int = 0,
    ) -> FileContent:
        return await self.workspace.read_file(
            path, line_range, include_imports, include_diagnostics, context_lines
        )

    async def get_project_structure(
        self,
        path: str = ".",
        max_depth: int = 3,
        show_hidden: bool = False,
        include_sizes: bool = True,
        exclude_patterns: Optional[List[str]] = None,
    ) -> ProjectTree:
        return await self.workspace.get_project_structure(
            path, max_depth, show_hidden, include_sizes, exclude_patterns
        )

    async def get_symbols(
        self, file: str, symbol_types: Optional[List[str]] = None
    ) -> SymbolsResult:
        return await self.workspace.get_symbols(file, symbol_types)

    # Refactoring
    async def rename_symbol(
        self, file: str, line: int, column: int, new_name: str, preview: bool = True
    ) -> Union[RenamePreview, RenameResult]:
        return await self.refactoring.rename_symbol(file, line, column, new_name, preview)

    async def extract_function(
        self,
        file: str,
        start_line: int,
        end_line: int,
        function_name: str,
        target_line: Optional[int] = None,
    ) -> ExtractResult:
        return await self.refactoring.extract_function(
            file, start_line, end_line, function_name, target_line
        )

    # Analysis & Diagnostics
    async def get_diagnostics(
        self,
        file: Optional[str] = None,
        severity: Optional[List[str]] = None,
        include_fixes: bool = False,
    ) -> List[Diagnostic]:
        return await self.workspace.get_diagnostics(file, severity, include_fixes)

    async def analyze_dependencies(
        self, file: str, direction: Literal["imports", "imported_by", "both"] = "both"
    ) -> DependencyGraph:
        return await self.analysis.analyze_dependencies(file, direction)

    # Debugging (DAP-Powered)
    async def start_debug_session(
        self,
        file: str,
        configuration: Optional[str] = None,
        breakpoints: Optional[List[int]] = None,
        args: Optional[List[str]] = None,
    ) -> DebugSession:
        return await self.debugging.start_debug_session(
            file, configuration, breakpoints, args
        )

    async def control_execution(
        self,
        action: str,
        session_id: Optional[str] = None,
    ) -> ExecutionState:
        return await self.debugging.control_execution(action, session_id)

    async def inspect_state(
        self,
        frame_id: Optional[int] = None,
        expression: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self.debugging.inspect_state(frame_id, expression)

    async def set_breakpoints(
        self,
        file: str,
        lines: List[int],
        conditions: Optional[Dict[int, str]] = None,
    ) -> List[BreakpointInfo]:
        return await self.debugging.set_breakpoints(file, lines, conditions)

    async def get_session_info(self) -> Optional[DebugSession]:
        return await self.debugging.get_session_info()

    # AI-Powered Analysis (Context Compression)
    async def summarize_code(
        self,
        file: str,
        detail_level: Literal["brief", "detailed"] = "brief",
    ) -> CodeSummary:
        return await self.ai.summarize_code(file, detail_level)

    async def summarize_changes(
        self,
        file: str,
        git_ref: str = "HEAD~1",
    ) -> ChangeSummary:
        return await self.ai.summarize_changes(file, git_ref)

    async def quick_review(
        self,
        file: str,
        focus: Optional[List[str]] = None,
    ) -> ReviewResult:
        return await self.ai.quick_review(file, focus)

    async def explain_error(
        self,
        error_message: str,
        context_file: Optional[str] = None,
        context_content: Optional[str] = None,
        context_lines: Optional[Tuple[int, int]] = None,
    ) -> ErrorExplanation:
        return await self.ai.explain_error(
            error_message, context_file, context_content, context_lines
        )
    
    async def explain_symbol(
        self,
        file: str,
        line: int,
        character: int,
        include_references: bool = True,
    ) -> CodeSummary:
        return await self.ai.explain_symbol(file, line, character, include_references)

    # Low-value features removed (agents can use shell commands directly)


__all__ = ["CliIdeServer"]
