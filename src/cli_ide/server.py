from __future__ import annotations

import os
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from .models.responses import (
    CodeExplanation,
    Completion,
    Definition,
    DependencyGraph,
    Diagnostic,
    ExecutionTrace,
    ExtractResult,
    FileContent,
    HoverInfo,
    Improvement,
    ProjectTree,
    Reference,
    RenamePreview,
    RenameResult,
    SearchResult,
    SemanticDiff,
    ShellResult,
    Symbol,
    TestResults,
    WorkspaceDiff,
)
from .neovim.client import NeovimClient
from .services.analysis import AnalysisService
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
        self.refactoring = RefactoringService(nvim_client=self.nvim_client)  # type: ignore
        self.analysis = AnalysisService(
            nvim_client=self.nvim_client, project_path=self.project_path
        )  # type: ignore
        self.workspace = WorkspaceService(  # type: ignore
            project_path=self.project_path, nvim_client=self.nvim_client
        )

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
    ) -> List[Reference]:
        return await self.navigation.find_references(symbol, file, line, scope)

    async def search(
        self,
        query: str,
        search_type: Literal["text", "regex", "semantic"] = "text",
        file_pattern: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> List[SearchResult]:
        return await self.navigation.search(query, search_type, file_pattern, scope)

    # Code Intelligence
    async def get_hover_info(self, file: str, line: int, column: int) -> HoverInfo:
        return await self.navigation.get_hover_info(file, line, column)

    async def get_completions(
        self, file: str, line: int, column: int, context_lines: int = 10
    ) -> List[Completion]:
        return await self.navigation.get_completions(file, line, column, context_lines)

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
    ) -> ProjectTree:
        return await self.workspace.get_project_structure(
            path, max_depth, show_hidden, include_sizes
        )

    async def get_symbols(
        self, file: str, symbol_types: Optional[List[str]] = None
    ) -> List[Symbol]:
        return await self.workspace.get_symbols(file, symbol_types)

    # Refactoring
    async def rename_symbol(
        self, old_name: str, new_name: str, preview: bool = True
    ) -> Union[RenamePreview, RenameResult]:
        return await self.refactoring.rename_symbol(old_name, new_name, preview)

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

    # Smart/Semantic
    async def explain_code(
        self,
        file: str,
        line_range: Optional[Tuple[int, int]] = None,
        detail_level: Literal["brief", "normal", "detailed"] = "normal",
    ) -> CodeExplanation:
        return await self.analysis.explain_code(file, line_range, detail_level)

    async def suggest_improvements(
        self, file: str, focus_areas: Optional[List[str]] = None
    ) -> List[Improvement]:
        return await self.analysis.suggest_improvements(file, focus_areas)

    async def semantic_diff(
        self,
        file: str,
        from_revision: Optional[str] = "HEAD~1",
        to_revision: Optional[str] = "HEAD",
    ) -> SemanticDiff:
        return await self.analysis.semantic_diff(file, from_revision, to_revision)

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

    # Execution & Testing
    async def run_tests(
        self,
        file_or_pattern: Optional[str] = None,
        test_name: Optional[str] = None,
        verbose: bool = False,
    ) -> TestResults:
        return await self.workspace.run_tests(file_or_pattern, test_name, verbose)

    async def trace_execution(
        self,
        function_or_file: str,
        arguments: Optional[Dict[str, Any]] = None,
        max_depth: int = 5,
    ) -> ExecutionTrace:
        return await self.workspace.trace_execution(
            function_or_file, arguments, max_depth
        )

    # Workspace management & escape hatches
    async def mark_position(self, name: str) -> None:
        return await self.workspace.mark_position(name)

    async def diff_since_mark(self, name: str) -> WorkspaceDiff:
        return await self.workspace.diff_since_mark(name)

    async def vim_command(self, command: str) -> str:
        return await self.workspace.vim_command(command)

    async def shell(
        self, command: str, working_dir: Optional[str] = None
    ) -> ShellResult:
        return await self.workspace.shell(command, working_dir)


__all__ = ["CliIdeServer"]
