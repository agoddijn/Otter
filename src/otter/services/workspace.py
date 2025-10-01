from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from ..models.responses import (
    Diagnostic,
    FileContent,
    ProjectTree,
    Symbol,
)


class WorkspaceService:
    def __init__(
        self, project_path: Optional[str] = None, nvim_client: Optional[Any] = None
    ) -> None:
        self.project_path = project_path or os.getcwd()
        self.nvim_client = nvim_client

    async def read_file(
        self,
        path: str,
        line_range: Optional[Tuple[int, int]] = None,
        include_imports: bool = False,
        include_diagnostics: bool = False,
        context_lines: int = 0,
    ) -> FileContent:
        """Read a file with intelligent context inclusion.

        Args:
            path: Path to file (relative to project root or absolute)
            line_range: Optional (start, end) line range (1-indexed, inclusive)
            include_imports: Whether to expand and include import information
            include_diagnostics: Whether to include LSP diagnostics
            context_lines: Number of additional context lines around line_range

        Returns:
            FileContent with content and optional imports/diagnostics

        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If Neovim client not available and advanced features requested
        """
        # Resolve path relative to project root
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = Path(self.project_path) / path

        file_path = file_path.resolve()

        # Check if file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        # If we need advanced features, we must use Neovim
        use_nvim = self.nvim_client and (include_imports or include_diagnostics)

        # Determine the actual line range to read
        actual_range = line_range
        if line_range and context_lines > 0:
            start, end = line_range
            actual_range = (max(1, start - context_lines), end + context_lines)

        # Read file content
        if use_nvim and self.nvim_client is not None:
            # Ensure Neovim is started
            if not self.nvim_client.is_running():
                await self.nvim_client.start()

            # Read through Neovim
            lines = await self.nvim_client.read_buffer(
                str(file_path), line_range=actual_range
            )
            # Add line numbers to content
            start_line = actual_range[0] if actual_range else 1
            numbered_lines = [
                f"{start_line + i}|{line}" for i, line in enumerate(lines)
            ]
            content = "\n".join(numbered_lines)
        else:
            # Direct file read (fallback)
            with open(file_path, "r", encoding="utf-8") as f:
                all_lines = f.readlines()

            if actual_range:
                start, end = actual_range
                # Convert to 0-indexed
                lines = all_lines[start - 1 : end]
                start_line = start
            else:
                lines = all_lines
                start_line = 1

            # Add line numbers to content
            numbered_lines = [
                f"{start_line + i}|{line.rstrip()}" for i, line in enumerate(lines)
            ]
            content = "\n".join(numbered_lines)

        # Collect expanded imports if requested
        expanded_imports: Optional[Dict[str, List[str]]] = None
        if include_imports and self.nvim_client:
            expanded_imports = await self._extract_imports(file_path, content)

        # Collect diagnostics if requested
        diagnostics: Optional[List[Diagnostic]] = None
        if include_diagnostics and self.nvim_client:
            # Wait for LSP to analyze the file (LSP is async and needs time)
            await asyncio.sleep(1.5)
            diagnostics = await self._get_file_diagnostics(file_path, line_range)

        return FileContent(
            content=content, expanded_imports=expanded_imports, diagnostics=diagnostics
        )

    async def _extract_imports(
        self, file_path: Path, content: str
    ) -> Dict[str, List[str]]:
        """Extract and expand import statements.

        This detects import statements and attempts to expand them with
        signatures/definitions from LSP if available.

        Args:
            file_path: Path to the file being analyzed
            content: File content with line numbers (format: "N|line content")

        Returns:
            Dict mapping import statements to lists of signatures.
            Currently returns empty lists as expansion is not yet implemented.

        TODO: Implement LSP-based expansion using textDocument/hover or
              textDocument/definition to get actual signatures like:
              "from .models import User": ["User(id, name, email, created_at)"]
        """
        imports: Dict[str, List[str]] = {}

        # Extract import statements (basic detection)
        for line in content.split("\n"):
            # Strip line number prefix (format: "N|content")
            if "|" in line:
                line_content = line.split("|", 1)[1].strip()
            else:
                line_content = line.strip()

            # Python imports
            if line_content.startswith("import ") or line_content.startswith("from "):
                # For now, just record the import without expansion
                # Future: Use LSP to get signatures for each imported symbol
                imports[line_content] = []

                # TODO: Parse the import to extract symbol names
                # TODO: For each symbol, call LSP hover/definition
                # TODO: Extract signature from hover info
                # Example:
                #   if "from foo import Bar, Baz" in line_content:
                #       - Get hover for "Bar" -> extract signature
                #       - Get hover for "Baz" -> extract signature
                #       - imports[line_content] = ["Bar(...)", "Baz(...)"]

            # JavaScript/TypeScript imports
            elif line_content.startswith("import ") and " from " in line_content:
                imports[line_content] = []

        return imports

    async def _get_file_diagnostics(
        self, file_path: Path, line_range: Optional[Tuple[int, int]] = None
    ) -> List[Diagnostic]:
        """Get LSP diagnostics for a file.

        Args:
            file_path: Path to the file
            line_range: Optional line range to filter diagnostics

        Returns:
            List of Diagnostic objects
        """
        if not self.nvim_client or not self.nvim_client.is_running():
            return []

        try:
            # Get diagnostics from Neovim/LSP
            nvim_diagnostics = await self.nvim_client.get_diagnostics(str(file_path))

            diagnostics = []
            for diag in nvim_diagnostics:
                # Convert from 0-indexed to 1-indexed line numbers
                line = diag.get("lnum", 0) + 1

                # Filter by line range if specified
                if line_range:
                    start, end = line_range
                    if line < start or line > end:
                        continue

                diagnostics.append(
                    Diagnostic(
                        file=str(file_path),
                        line=line,
                        column=diag.get("col", 0) + 1,  # Also 1-indexed
                        message=diag.get("message", ""),
                        severity=self._map_diagnostic_severity(diag.get("severity", 1)),
                        source=diag.get("source", "lsp"),
                    )
                )

            return diagnostics
        except Exception:
            # If diagnostics fail, return empty list rather than failing the whole request
            return []

    def _map_diagnostic_severity(
        self, severity: int
    ) -> Literal["error", "warning", "info", "hint"]:
        """Map LSP severity codes to strings."""
        # LSP severity: 1=Error, 2=Warning, 3=Information, 4=Hint
        severity_map: Dict[int, Literal["error", "warning", "info", "hint"]] = {
            1: "error",
            2: "warning",
            3: "info",
            4: "hint",
        }
        return severity_map.get(severity, "info")

    async def get_project_structure(
        self,
        path: str = ".",
        max_depth: int = 3,
        show_hidden: bool = False,
        include_sizes: bool = True,
    ) -> ProjectTree:
        """Get the project directory structure.
        
        NOTE: This is a low-value feature - agents can use `tree` or `ls -R` directly.
        Kept for backward compatibility but may be removed in future.

        Args:
            path: Root path to analyze (relative to project root)
            max_depth: Maximum directory depth to traverse
            show_hidden: Whether to include hidden files/directories
            include_sizes: Whether to include file sizes

        Returns:
            ProjectTree with root path and nested tree structure
        """
        # Resolve the path relative to project root
        if os.path.isabs(path):
            root_path = Path(path)
        else:
            root_path = Path(self.project_path) / path

        root_path = root_path.resolve()

        # Build the tree structure
        tree = self._build_tree(
            root_path,
            current_depth=0,
            max_depth=max_depth,
            show_hidden=show_hidden,
            include_sizes=include_sizes,
        )

        return ProjectTree(root=str(root_path), tree=tree)

    def _build_tree(
        self,
        path: Path,
        current_depth: int,
        max_depth: int,
        show_hidden: bool,
        include_sizes: bool,
    ) -> Dict[str, Any]:
        """Recursively build directory tree structure.

        Returns a dictionary where:
        - Keys are file/directory names
        - Values are either:
          - Dict with 'type', 'size' (for files)
          - Dict with 'type', 'children' (for directories)
        """
        if not path.exists():
            return {}

        if not path.is_dir():
            # It's a file
            result: Dict[str, Any] = {"type": "file"}
            if include_sizes:
                try:
                    result["size"] = path.stat().st_size
                except (OSError, PermissionError):
                    result["size"] = 0
            return {path.name: result}

        # It's a directory - if we've reached max depth, don't recurse further
        if current_depth >= max_depth:
            return {path.name: {"type": "directory", "children": {}, "truncated": True}}

        try:
            entries = sorted(
                path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
            )
        except (OSError, PermissionError):
            return {
                path.name: {
                    "type": "directory",
                    "children": {},
                    "error": "Permission denied",
                }
            }

        children: Dict[str, Any] = {}

        for entry in entries:
            # Skip hidden files if requested
            if not show_hidden and entry.name.startswith("."):
                continue

            # Skip common directories that should always be ignored
            if entry.name in {
                "__pycache__",
                ".git",
                "node_modules",
                ".venv",
                "venv",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
            }:
                continue

            if entry.is_dir():
                # Recursively build subtree
                subtree = self._build_tree(
                    entry, current_depth + 1, max_depth, show_hidden, include_sizes
                )
                # Merge the subtree (it will have the directory name as key)
                children.update(subtree)
            else:
                # Add file
                file_info: Dict[str, Any] = {"type": "file"}
                if include_sizes:
                    try:
                        file_info["size"] = entry.stat().st_size
                    except (OSError, PermissionError):
                        file_info["size"] = 0
                children[entry.name] = file_info

        return {path.name: {"type": "directory", "children": children}}

    async def get_symbols(
        self, file: str, symbol_types: Optional[List[str]] = None
    ) -> List[Symbol]:
        """Extract all symbols (classes, functions, etc.) from a file.

        Args:
            file: Path to file (relative to project root or absolute)
            symbol_types: Optional list to filter by symbol type
                         (e.g., ["class", "function", "method"])

        Returns:
            List of Symbol objects with hierarchy

        Raises:
            RuntimeError: If Neovim client not available
            FileNotFoundError: If file doesn't exist
        """
        if not self.nvim_client:
            raise RuntimeError("Neovim client required for get_symbols")

        # Resolve path relative to project root
        file_path = Path(file)
        if not file_path.is_absolute():
            file_path = Path(self.project_path) / file

        file_path = file_path.resolve()

        # Check if file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file}")

        # Ensure Neovim is running
        if not self.nvim_client.is_running():
            await self.nvim_client.start()

        # Get document symbols from LSP
        lsp_symbols = await self.nvim_client.lsp_document_symbols(str(file_path))

        if not lsp_symbols:
            return []

        # Parse LSP symbols into our Symbol model
        symbols = self._parse_lsp_symbols(lsp_symbols, symbol_types)

        return symbols

    def _parse_lsp_symbols(
        self,
        lsp_symbols: List[Dict[str, Any]],
        filter_types: Optional[List[str]] = None,
    ) -> List[Symbol]:
        """Parse LSP DocumentSymbol into our Symbol model.

        LSP returns symbols in a hierarchical structure. We need to flatten it
        while preserving parent-child relationships.
        """
        result = []

        def parse_symbol(
            lsp_sym: Dict[str, Any], parent_name: Optional[str] = None
        ) -> Optional[Symbol]:
            """Recursively parse a symbol and its children."""
            # Get symbol info
            name = lsp_sym.get("name", "")
            kind = lsp_sym.get("kind", 0)

            # Convert LSP SymbolKind to our type strings
            symbol_type = self._lsp_kind_to_type(kind)

            # Get line number (LSP uses 0-indexed, we use 1-indexed)
            range_data = lsp_sym.get("range") or lsp_sym.get("location", {}).get(
                "range"
            )
            if range_data:
                line = range_data["start"]["line"] + 1
            else:
                line = 0

            # Filter by type if requested
            if filter_types and symbol_type not in filter_types:
                # Still process children in case they match
                children_list = lsp_sym.get("children", [])
                for child in children_list:
                    child_symbol = parse_symbol(child, parent_name)
                    if child_symbol:
                        result.append(child_symbol)
                return None

            # Parse children recursively
            children = []
            children_list = lsp_sym.get("children", [])
            for child in children_list:
                child_symbol = parse_symbol(child, name)
                if child_symbol:
                    children.append(child_symbol)

            return Symbol(
                name=name,
                type=symbol_type,
                line=line,
                children=children if children else None,
                parent=parent_name,
            )

        # Parse all top-level symbols
        for lsp_sym in lsp_symbols:
            symbol = parse_symbol(lsp_sym)
            if symbol:
                result.append(symbol)

        return result

    def _lsp_kind_to_type(self, kind: int) -> str:
        """Convert LSP SymbolKind integer to our string type.

        LSP SymbolKind values from the spec:
        1=File, 2=Module, 3=Namespace, 4=Package, 5=Class, 6=Method,
        7=Property, 8=Field, 9=Constructor, 10=Enum, 11=Interface,
        12=Function, 13=Variable, 14=Constant, etc.
        """
        kind_map = {
            1: "file",
            2: "module",
            3: "namespace",
            4: "package",
            5: "class",
            6: "method",
            7: "property",
            8: "field",
            9: "constructor",
            10: "enum",
            11: "interface",
            12: "function",
            13: "variable",
            14: "constant",
            15: "string",
            16: "number",
            17: "boolean",
            18: "array",
        }
        return kind_map.get(kind, "unknown")

    async def get_diagnostics(
        self,
        file: Optional[str] = None,
        severity: Optional[List[str]] = None,
        include_fixes: bool = False,
    ) -> List[Diagnostic]:
        """Get LSP diagnostics for files in the project.

        Args:
            file: Optional path to specific file. If None, gets diagnostics for all open buffers.
            severity: Optional list of severity levels to filter by (error, warning, info, hint)
            include_fixes: Whether to include fix suggestions (currently not implemented)

        Returns:
            List of Diagnostic objects

        Raises:
            RuntimeError: If Neovim client not available
        """
        if not self.nvim_client:
            raise RuntimeError("Neovim client required for diagnostics")

        # Ensure Neovim is running
        if not self.nvim_client.is_running():
            await self.nvim_client.start()

        diagnostics: List[Diagnostic] = []

        if file:
            # Get diagnostics for specific file
            file_path = Path(file)
            if not file_path.is_absolute():
                file_path = Path(self.project_path) / file
            file_path = file_path.resolve()

            # Wait a bit for LSP to analyze
            await asyncio.sleep(1.5)

            file_diagnostics = await self._get_file_diagnostics(
                file_path, line_range=None
            )
            diagnostics.extend(file_diagnostics)
        else:
            # Get diagnostics for all open buffers
            diagnostics = await self._get_all_diagnostics()

        # Filter by severity if requested
        if severity:
            severity_set = set(severity)
            diagnostics = [d for d in diagnostics if d.severity in severity_set]

        # TODO: Add fixes when LSP code actions are implemented
        # if include_fixes:
        #     for diag in diagnostics:
        #         diag.fix = await self._get_diagnostic_fix(diag)

        return diagnostics

    async def _get_all_diagnostics(self) -> List[Diagnostic]:
        """Get diagnostics from all open buffers in Neovim.

        Returns:
            List of all Diagnostic objects across all buffers
        """
        if not self.nvim_client or not self.nvim_client.is_running():
            return []

        try:
            # Get all diagnostics from Neovim
            all_diags = await self.nvim_client.execute_lua("""
                local all_diagnostics = vim.diagnostic.get()
                return all_diagnostics
            """)

            diagnostics = []
            for diag in all_diags:
                # Get buffer path
                bufnr = diag.get("bufnr", 0)
                if bufnr == 0:
                    continue

                # Get buffer name (file path)
                buf_path = await self.nvim_client.execute_lua(f"""
                    return vim.api.nvim_buf_get_name({bufnr})
                """)

                if not buf_path:
                    continue

                # Convert to 1-indexed
                line = diag.get("lnum", 0) + 1

                diagnostics.append(
                    Diagnostic(
                        file=buf_path,
                        line=line,
                        column=diag.get("col", 0) + 1,
                        message=diag.get("message", ""),
                        severity=self._map_diagnostic_severity(diag.get("severity", 1)),
                        source=diag.get("source", "lsp"),
                    )
                )

            return diagnostics
        except Exception as e:
            # If getting all diagnostics fails, return empty list
            print(f"Warning: Failed to get diagnostics: {e}")
            return []

    # ========================================================================
    # LOW-VALUE FEATURES REMOVED
    # ========================================================================
    # The following features have been removed as they provide minimal value
    # over direct shell/git commands that agents can already execute:
    #
    # - run_tests: Use `pytest`, `cargo test`, `go test` directly
    # - trace_execution: Use `python -m pdb` or debugger directly  
    # - mark_position/diff_since_mark: Use `git stash`/`git diff` directly
    # - vim_command: Low-value escape hatch
    # - shell: Agents already have shell access
    # - get_project_structure: Use `tree` or `ls -R` directly
    #
    # Focus remains on LSP/TreeSitter features that agents cannot easily access.
    # ========================================================================
