from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import unquote, urlparse

from ..models.responses import (
    Completion,
    Definition,
    HoverInfo,
    Reference,
    SearchResult,
)


class NavigationService:
    def __init__(
        self, nvim_client: Optional[Any] = None, project_path: Optional[str] = None
    ) -> None:
        self.nvim_client = nvim_client
        self.project_path = Path(project_path) if project_path else Path.cwd()

    async def find_definition(
        self, symbol: str, file: Optional[str] = None, line: Optional[int] = None
    ) -> Definition:
        """Find the definition of a symbol.

        Args:
            symbol: Symbol name to find
            file: Optional file context (if provided with line, searches at that position)
            line: Optional line number (1-indexed) for context-aware search

        Returns:
            Definition object with location and metadata

        Raises:
            RuntimeError: If Neovim client not available or symbol not found
        """
        if not self.nvim_client:
            raise RuntimeError("Neovim client required for find_definition")

        # If file and line provided, use position-based search
        if file and line is not None:
            # Find the symbol on the line to get the correct column
            column = await self._find_symbol_column(file, line, symbol)
            return await self._find_definition_at_position(file, line, column)

        # Otherwise, search for symbol by name (grep-based fallback)
        raise NotImplementedError(
            "Symbol search without file context not yet implemented. "
            "Please provide file and line for position-based search."
        )

    async def _find_symbol_column(self, file: str, line: int, symbol: str) -> int:
        """Find the column position of a symbol on a given line."""
        file_path = Path(file) if Path(file).is_absolute() else self.project_path / file

        with open(file_path, "r") as f:
            lines = f.readlines()

        if line > len(lines):
            return 0

        line_text = lines[line - 1]
        # Find the symbol in the line
        col = line_text.find(symbol)
        if col == -1:
            # Symbol not found on line, return 0
            return 0

        return col

    async def _find_definition_at_position(
        self, file: str, line: int, column: int
    ) -> Definition:
        """Find definition at a specific file position using LSP.

        This is the main implementation - uses LSP textDocument/definition.
        """
        if not self.nvim_client:
            raise RuntimeError("Neovim client required")

        # Get definition from LSP
        lsp_result = await self.nvim_client.lsp_definition(file, line, column)

        if not lsp_result or len(lsp_result) == 0:
            raise RuntimeError(
                f"Definition not found for position {file}:{line}:{column}"
            )

        # Take first result (LSP can return multiple)
        location = lsp_result[0]

        # Parse LSP location
        uri = location.get("uri") or location.get("targetUri")
        range_data = location.get("range") or location.get("targetRange")

        if not uri or not range_data:
            raise RuntimeError("Invalid LSP definition response")

        # Convert URI to file path
        def_file = self._uri_to_path(uri)
        def_line = range_data["start"]["line"] + 1  # Convert to 1-indexed
        def_column = range_data["start"]["character"]

        # Read the file to get context and extract symbol info
        def_file_path = Path(def_file)
        if not def_file_path.exists():
            raise RuntimeError(f"Definition file not found: {def_file}")

        with open(def_file_path, "r") as f:
            lines = f.readlines()

        # Get symbol at definition line
        if def_line > len(lines):
            raise RuntimeError(f"Definition line {def_line} out of range")

        def_line_text = lines[def_line - 1].strip()

        # Extract symbol name and type from the definition line
        symbol_name, symbol_type = self._parse_symbol_info(def_line_text)

        # Get context lines (3 before, 3 after)
        context_start = max(0, def_line - 4)
        context_end = min(len(lines), def_line + 3)
        context_lines = [line.rstrip() for line in lines[context_start:context_end]]

        # Try to extract docstring (next few lines if they're comments/docstrings)
        docstring = self._extract_docstring(lines, def_line)

        # Try to extract signature (for functions/methods)
        signature = self._extract_signature(lines, def_line)

        # Make file path relative to project if possible
        try:
            # Resolve both paths to handle symlinks (macOS /var vs /private/var)
            resolved_def_file = Path(def_file).resolve()
            resolved_project = self.project_path.resolve()
            rel_file = str(resolved_def_file.relative_to(resolved_project))
        except ValueError:
            rel_file = def_file

        return Definition(
            file=rel_file,
            line=def_line,
            column=def_column,
            symbol_name=symbol_name,
            symbol_type=symbol_type,
            docstring=docstring,
            signature=signature,
            context_lines=context_lines,
        )

    def _uri_to_path(self, uri: str) -> str:
        """Convert LSP URI to file path."""
        if uri.startswith("file://"):
            parsed = urlparse(uri)
            return unquote(parsed.path)
        return uri

    def _parse_symbol_info(
        self, line: str
    ) -> tuple[
        str, Literal["function", "class", "variable", "module", "method", "property"]
    ]:
        """Extract symbol name and type from definition line.

        Returns:
            Tuple of (symbol_name, symbol_type)
        """
        line = line.strip()

        # Class definition
        if line.startswith("class "):
            match = re.match(r"class\s+(\w+)", line)
            if match:
                return match.group(1), "class"

        # Function/method definition
        if line.startswith("def ") or line.startswith("async def "):
            match = re.match(r"(?:async\s+)?def\s+(\w+)", line)
            if match:
                name = match.group(1)
                # Heuristic: __init__ or methods with self are methods
                if "__init__" in line or "self" in line:
                    return name, "method"
                return name, "function"

        # Variable/constant
        if "=" in line:
            match = re.match(r"(\w+)\s*=", line)
            if match:
                return match.group(1), "variable"

        # Fallback: extract first word-like token
        match = re.search(r"\b([a-zA-Z_]\w*)\b", line)
        if match:
            return match.group(1), "variable"

        return "unknown", "variable"

    def _extract_docstring(self, lines: List[str], def_line: int) -> Optional[str]:
        """Extract docstring from lines following definition."""
        if def_line >= len(lines):
            return None

        # Check next line for docstring
        next_line_idx = def_line  # def_line is 1-indexed, but we need 0-indexed
        if next_line_idx >= len(lines):
            return None

        next_line = lines[next_line_idx].strip()

        # Python docstring (""" or ''')
        if next_line.startswith('"""') or next_line.startswith("'''"):
            quote = '"""' if next_line.startswith('"""') else "'''"

            # Single-line docstring
            if next_line.count(quote) >= 2:
                return next_line.strip(quote).strip()

            # Multi-line docstring
            docstring_lines = [next_line.strip(quote)]
            for i in range(next_line_idx + 1, min(next_line_idx + 20, len(lines))):
                line = lines[i].strip()
                if quote in line:
                    docstring_lines.append(line.replace(quote, ""))
                    break
                docstring_lines.append(line)

            return " ".join(docstring_lines).strip()

        return None

    def _extract_signature(self, lines: List[str], def_line: int) -> Optional[str]:
        """Extract function/method signature."""
        if def_line > len(lines):
            return None

        line = lines[def_line - 1].strip()

        # Function signature
        if "def " in line:
            # Extract everything from 'def' to ':'
            match = re.search(
                r"((?:async\s+)?def\s+\w+\([^)]*\)(?:\s*->\s*[^:]+)?)", line
            )
            if match:
                return match.group(1).strip()

        return None

    async def find_references(
        self,
        symbol: str,
        file: Optional[str] = None,
        line: Optional[int] = None,
        scope: Literal["file", "package", "project"] = "project",
    ) -> List[Reference]:
        """Find all references to a symbol.

        Args:
            symbol: Symbol name to find references for
            file: Optional file context (required for LSP-based search)
            line: Optional line number (1-indexed) for position-based search
            scope: Scope of search (currently only 'project' is fully supported via LSP)

        Returns:
            List of Reference objects

        Raises:
            RuntimeError: If Neovim client not available or file/line not provided
        """
        if not self.nvim_client:
            raise RuntimeError("Neovim client required for find_references")

        if not file or line is None:
            raise NotImplementedError(
                "Symbol search without file context not yet implemented. "
                "Please provide file and line for position-based search."
            )

        # Find the symbol on the line to get the correct column
        column = await self._find_symbol_column(file, line, symbol)

        # Get references from LSP
        lsp_result = await self.nvim_client.lsp_references(file, line, column)

        if not lsp_result or len(lsp_result) == 0:
            return []

        references = []
        for location in lsp_result:
            try:
                # Parse LSP location
                uri = location.get("uri") or location.get("targetUri")
                range_data = location.get("range") or location.get("targetRange")

                if not uri or not range_data:
                    continue

                # Convert URI to file path
                ref_file = self._uri_to_path(uri)
                ref_line = range_data["start"]["line"] + 1  # Convert to 1-indexed
                ref_column = range_data["start"]["character"]

                # Read the file to get context
                ref_file_path = Path(ref_file)
                if not ref_file_path.exists():
                    continue

                with open(ref_file_path, "r") as f:
                    lines = f.readlines()

                if ref_line > len(lines):
                    continue

                context = lines[ref_line - 1].strip()

                # Make file path relative to project if possible
                try:
                    resolved_ref_file = Path(ref_file).resolve()
                    resolved_project = self.project_path.resolve()
                    rel_file = str(resolved_ref_file.relative_to(resolved_project))
                except ValueError:
                    rel_file = ref_file

                references.append(
                    Reference(
                        file=rel_file, line=ref_line, column=ref_column, context=context
                    )
                )
            except Exception:
                # Skip malformed locations
                continue

        # Apply scope filtering if needed
        if scope == "file" and file:
            # Filter to only references in the same file
            file_path = (
                Path(file) if Path(file).is_absolute() else self.project_path / file
            )
            resolved_file = file_path.resolve()
            try:
                rel_file = str(resolved_file.relative_to(self.project_path.resolve()))
            except ValueError:
                rel_file = str(file)

            references = [ref for ref in references if ref.file == rel_file]

        return references

    async def search(
        self,
        query: str,
        search_type: Literal["text", "regex", "semantic"] = "text",
        file_pattern: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> List[SearchResult]:
        """REMOVED: Low-value feature - agents can use ripgrep directly.
        
        For text/regex search, agents should use ripgrep directly:
            rg "pattern" --type py
            rg -e "regex" --glob "*.ts"
        
        Semantic search (using TreeSitter to find code patterns) may be added in future.
        """
        raise NotImplementedError(
            "Search removed - use ripgrep directly for text/regex search. "
            "Semantic search (TreeSitter-based) may be added in future."
        )

    async def get_hover_info(self, file: str, line: int, column: int) -> HoverInfo:
        """Get hover information (type, docstring) for a symbol at a position.

        Args:
            file: File path
            line: Line number (1-indexed)
            column: Column number (0-indexed or 1-indexed, we normalize)

        Returns:
            HoverInfo with symbol name, type, docstring, and source file

        Raises:
            RuntimeError: If Neovim client not available or hover info not found
        """
        if not self.nvim_client:
            raise RuntimeError("Neovim client required for get_hover_info")

        # Get hover info from LSP
        lsp_result = await self.nvim_client.lsp_hover(file, line, column)

        if not lsp_result:
            raise RuntimeError(f"No hover information found at {file}:{line}:{column}")

        # Parse LSP hover response
        hover_info = self._parse_hover_response(lsp_result, file, line, column)

        return hover_info

    def _parse_hover_response(
        self, lsp_hover: Dict[str, Any], file: str, line: int, column: int
    ) -> HoverInfo:
        """Parse LSP Hover response into our HoverInfo model.

        LSP Hover contains:
        - contents: MarkedString | MarkedString[] | MarkupContent
        - range: optional range
        """
        contents = lsp_hover.get("contents", {})

        # Extract text from various LSP hover formats
        hover_text = ""
        if isinstance(contents, str):
            # Simple string
            hover_text = contents
        elif isinstance(contents, dict):
            # MarkupContent: {kind: "markdown" | "plaintext", value: string}
            if "value" in contents:
                hover_text = contents["value"]
            # MarkedString: {language: string, value: string}
            elif "language" in contents:
                hover_text = contents.get("value", "")
        elif isinstance(contents, list):
            # Array of MarkedString
            parts = []
            for item in contents:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(item.get("value", ""))
            hover_text = "\n".join(parts)

        # Try to extract symbol name, type, and docstring from hover text
        symbol_name, type_info, docstring = self._extract_hover_parts(
            hover_text, file, line, column
        )

        # Try to get source file if it's an external symbol
        source_file = self._extract_source_file(hover_text)

        return HoverInfo(
            symbol=symbol_name,
            type=type_info,
            docstring=docstring,
            source_file=source_file,
        )

    def _extract_hover_parts(
        self, hover_text: str, file: str, line: int, column: int
    ) -> tuple[str, Optional[str], Optional[str]]:
        """Extract symbol name, type, and docstring from hover text.

        LSP often returns markdown like:
        ```python
        (class) MyClass
        ```
        ---
        Docstring here

        Returns:
            Tuple of (symbol_name, type_info, docstring)
        """
        # Split by separator (--- is common in markdown hover)
        parts = hover_text.split("---")
        code_part = parts[0].strip()
        doc_part = parts[1].strip() if len(parts) > 1 else None

        # Remove markdown code fences
        lines = code_part.split("\n")
        clean_lines = []
        for text_line in lines:
            text_line = text_line.strip()
            # Skip code fence markers
            if text_line.startswith("```"):
                continue
            if text_line:
                clean_lines.append(text_line)

        if not clean_lines:
            return "unknown", None, None

        # Join all code lines for full type info
        full_type = "\n".join(clean_lines)

        # Try to extract symbol name from various formats
        symbol_name = "unknown"

        # Try all lines to find the symbol
        for text_line in clean_lines:
            # Pattern: "(class) ClassName" or "(method) def method_name"
            match = re.search(
                r"\((class|method|function|variable|parameter)\)\s+(?:def\s+)?(\w+)",
                text_line,
            )
            if match:
                symbol_name = match.group(2)
                break

            # Pattern: "def function_name(...)" or "async def function_name(...)"
            match = re.match(r"(?:async\s+)?def\s+(\w+)", text_line)
            if match:
                symbol_name = match.group(1)
                break

            # Pattern: "class ClassName"
            match = re.match(r"class\s+(\w+)", text_line)
            if match:
                symbol_name = match.group(1)
                break

            # Pattern: "name: type" (for variables/parameters)
            match = re.search(r"^(\w+)\s*:", text_line)
            if match:
                symbol_name = match.group(1)
                break

        # If still unknown, try to extract any identifier
        if symbol_name == "unknown":
            for text_line in clean_lines:
                match = re.search(r"\b([a-zA-Z_]\w*)\b", text_line)
                if match and match.group(1) not in [
                    "class",
                    "def",
                    "async",
                    "return",
                    "self",
                ]:
                    symbol_name = match.group(1)
                    break

        return symbol_name, full_type, doc_part

    def _extract_source_file(self, hover_text: str) -> Optional[str]:
        """Try to extract source file path from hover text."""
        # Some LSP servers include file paths in hover text
        # Look for common patterns like "Defined in: /path/to/file.py"
        match = re.search(r"(?:Defined in|From):\s*([^\s]+\.py)", hover_text)
        if match:
            return match.group(1)
        return None

    async def get_completions(
        self, file: str, line: int, column: int, context_lines: int = 10
    ) -> List[Completion]:
        """Get context-aware code completions at a position.
        
        Args:
            file: File path
            line: Line number (1-indexed)
            column: Column number (0-indexed, cursor position)
            context_lines: Number of context lines (not used, kept for API compatibility)
            
        Returns:
            List of Completion objects with suggestions
            
        Raises:
            RuntimeError: If Neovim client not available or no completions found
        """
        if not self.nvim_client:
            raise RuntimeError("Neovim client required for get_completions")
        
        # Resolve file path
        file_path = Path(file) if Path(file).is_absolute() else self.project_path / file
        
        # Get completions from LSP
        lsp_completions = await self.nvim_client.lsp_completion(str(file_path), line, column)
        
        if not lsp_completions or len(lsp_completions) == 0:
            # Return empty list rather than raising error - no completions is valid
            return []
        
        # Parse LSP completion items into our Completion model
        completions = []
        for item in lsp_completions:
            # LSP CompletionItem structure:
            # - label: str (the text to insert)
            # - kind: int (CompletionItemKind enum)
            # - detail: Optional[str] (additional info)
            # - documentation: Optional[str | MarkupContent]
            # - insertText: Optional[str] (text to insert, defaults to label)
            
            label = item.get("label", "")
            if not label:
                continue
                
            # Get the text to insert (prefer insertText, fallback to label)
            text = item.get("insertText", label)
            
            # Map LSP CompletionItemKind to human-readable strings
            kind_int = item.get("kind")
            kind = self._lsp_completion_kind_to_string(kind_int) if kind_int else None
            
            # Get detail text
            detail = item.get("detail")
            
            completions.append(
                Completion(
                    text=text,
                    kind=kind,
                    detail=detail
                )
            )
        
        return completions
    
    def _lsp_completion_kind_to_string(self, kind: int) -> str:
        """Convert LSP CompletionItemKind integer to string.
        
        LSP CompletionItemKind values:
        1=Text, 2=Method, 3=Function, 4=Constructor, 5=Field, 6=Variable,
        7=Class, 8=Interface, 9=Module, 10=Property, 11=Unit, 12=Value,
        13=Enum, 14=Keyword, 15=Snippet, 16=Color, 17=File, 18=Reference,
        19=Folder, 20=EnumMember, 21=Constant, 22=Struct, 23=Event,
        24=Operator, 25=TypeParameter
        """
        kind_map = {
            1: "text",
            2: "method",
            3: "function",
            4: "constructor",
            5: "field",
            6: "variable",
            7: "class",
            8: "interface",
            9: "module",
            10: "property",
            11: "unit",
            12: "value",
            13: "enum",
            14: "keyword",
            15: "snippet",
            16: "color",
            17: "file",
            18: "reference",
            19: "folder",
            20: "enum_member",
            21: "constant",
            22: "struct",
            23: "event",
            24: "operator",
            25: "type_parameter",
        }
        return kind_map.get(kind, "unknown")
