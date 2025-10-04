from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import unquote, urlparse

from ..models.responses import (
    Completion,
    CompletionsResult,
    Definition,
    FileReferences,
    HoverInfo,
    Reference,
    ReferencesResult,
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
            file: Optional file path for context-aware resolution. Recommended when the symbol
                  appears in multiple places or to ensure accurate resolution of imports.
            line: Optional line number (1-indexed) for precise position-based search. When provided
                  with file, uses LSP to find the definition at that exact location.

        Returns:
            Definition object with location and metadata including:
            - file, line, column: Location of the definition
            - symbol_name, symbol_type: Identified symbol information
            - signature: Function/method signatures (null for classes, variables, properties)
            - docstring: Extracted documentation if available
            - context_lines: Surrounding code with line numbers for better understanding
            - has_alternatives: True if multiple definitions were found (returns first)

        Raises:
            RuntimeError: If Neovim client not available or symbol not found
            NotImplementedError: If file and line are not provided (name-only search not yet supported)
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

        # Track if there are multiple definitions (e.g., overloaded functions, multiple declarations)
        has_alternatives = len(lsp_result) > 1

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

        # 🎯 100% Language-agnostic: Get ALL info from LSP!
        # The LSP knows the language and provides:
        # - Symbol name and type
        # - Signature (for functions/methods)
        # - Documentation/docstring
        # No text parsing needed!
        symbol_info = await self._get_complete_symbol_info_from_lsp(
            def_file, def_line, def_column, def_line_text
        )

        symbol_name = symbol_info["name"]
        symbol_type = symbol_info["type"]
        signature = symbol_info.get("signature")
        docstring = symbol_info.get("docstring")

        # Get context lines (3 before, 3 after) with line numbers
        context_start = max(0, def_line - 4)
        context_end = min(len(lines), def_line + 3)
        context_lines = [
            f"{context_start + i + 1}|{line.rstrip()}"
            for i, line in enumerate(lines[context_start:context_end])
        ]

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
            has_alternatives=has_alternatives,
        )

    def _uri_to_path(self, uri: str) -> str:
        """Convert LSP URI to file path."""
        if uri.startswith("file://"):
            parsed = urlparse(uri)
            return unquote(parsed.path)
        return uri

    async def _get_symbol_info_from_lsp(
        self, file: str, line: int, column: int, fallback_line_text: str
    ) -> tuple[
        str,
        Literal[
            "function", "class", "variable", "module", "method", "property", "struct"
        ],
    ]:
        """Get symbol information using LSP (backward compatibility wrapper).

        This is a simplified version of _get_complete_symbol_info_from_lsp
        that only returns name and type for backward compatibility.

        New code should use _get_complete_symbol_info_from_lsp instead.

        Args:
            file: File path
            line: Line number (1-indexed)
            column: Column position
            fallback_line_text: Unused (kept for API compatibility)

        Returns:
            Tuple of (symbol_name, symbol_type)

        Raises:
            RuntimeError: If LSP server unavailable or no symbol at position
        """
        info = await self._get_complete_symbol_info_from_lsp(
            file, line, column, fallback_line_text
        )
        return info["name"], info["type"]

    def _parse_hover_text(
        self, hover_text: str, fallback_line_text: str
    ) -> Optional[
        tuple[
            str,
            Literal[
                "function",
                "class",
                "variable",
                "module",
                "method",
                "property",
                "struct",
            ],
        ]
    ]:
        """Extract symbol info from LSP hover text.

        LSP hover typically includes markdown with code blocks that show
        the symbol definition in a language-agnostic way.
        """
        # Look for markdown code blocks (```language\ncode\n```)
        code_block_match = re.search(r"```(?:\w+)?\n(.+?)```", hover_text, re.DOTALL)
        if code_block_match:
            code = code_block_match.group(1).strip()

            # Parse the code block (which is usually the symbol definition)
            # This is more reliable than parsing the raw source

            # Class/struct
            if re.search(r"\b(?:class|struct)\s+(\w+)", code):
                match = re.search(r"\b(?:class|struct)\s+(\w+)", code)
                name = match.group(1)  # type: ignore
                symbol_type = "struct" if "struct" in code else "class"
                return (name, symbol_type)

            # Function
            if re.search(r"\b(?:function|fn|def)\s+(\w+)", code):
                match = re.search(r"\b(?:function|fn|def)\s+(\w+)", code)
                return (match.group(1), "function")  # type: ignore

            # Method (has 'this', 'self', or is indented/in a class context)
            if any(keyword in code for keyword in ["(this", "(self", "self.", "this."]):
                match = re.search(r"(?:function|fn|def)\s+(\w+)", code)
                if match:
                    return (match.group(1), "method")
                # Try extracting method name without keywords
                match = re.search(r"(\w+)\s*\(", code)
                if match:
                    return (match.group(1), "method")

            # Variable/constant
            if re.search(r"\b(?:const|let|var)\s+(\w+)", code):
                match = re.search(r"\b(?:const|let|var)\s+(\w+)", code)
                return (match.group(1), "variable")  # type: ignore

        # If no code block, try to extract from plain text
        # Look for patterns like "class User" or "function createUser"
        type_match = re.search(
            r"\b(class|struct|function|fn|def|const|let|var)\s+(\w+)", hover_text
        )
        if type_match:
            type_keyword, name = type_match.groups()
            if type_keyword in ("class",):
                return (name, "class")
            elif type_keyword in ("struct",):
                return (name, "struct")
            elif type_keyword in ("function", "fn", "def"):
                return (name, "function")
            elif type_keyword in ("const", "let", "var"):
                return (name, "variable")

        return None

    async def _get_complete_symbol_info_from_lsp(
        self, file: str, line: int, column: int, fallback_line_text: str
    ) -> Dict[str, Any]:
        """Get complete symbol information from LSP (name, type, signature, docstring).

        This is the 100% language-agnostic way to get ALL symbol info at once!
        The LSP knows the language and provides rich semantic information.

        Args:
            file: File path
            line: Line number (1-indexed)
            column: Column position
            fallback_line_text: Text to parse if LSP unavailable

        Returns:
            Dict with keys: name, type, signature (Optional), docstring (Optional)
        """
        result = {
            "name": "unknown",
            "type": "variable",
            "signature": None,
            "docstring": None,
        }

        try:
            # Get hover information - this contains signature + docstring
            hover_result = await self.nvim_client.lsp_hover(file, line, column)  # type: ignore

            if hover_result and "contents" in hover_result:
                contents = hover_result["contents"]

                # Extract hover text
                hover_text = ""
                if isinstance(contents, str):
                    hover_text = contents
                elif isinstance(contents, dict):
                    hover_text = contents.get("value", "")
                elif isinstance(contents, list) and len(contents) > 0:
                    if isinstance(contents[0], str):
                        hover_text = contents[0]
                    elif isinstance(contents[0], dict):
                        hover_text = contents[0].get("value", "")

                if hover_text:
                    # Parse signature and docstring from hover
                    parsed = self._parse_complete_hover_info(hover_text)
                    result.update(parsed)

        except Exception:
            pass

        try:
            # Get symbol name and type from document symbols (most accurate for name/type)
            symbols = await self.nvim_client.lsp_document_symbols(file)  # type: ignore

            if symbols:
                symbol = self._find_symbol_at_position(symbols, line, column)
                if symbol:
                    result["name"] = symbol.get("name", result["name"])
                    kind = symbol.get("kind")
                    result["type"] = self._lsp_kind_to_type(kind)

        except Exception as e:
            # If we got some info from hover, return partial data
            if result["name"] != "unknown":
                return result

            # Otherwise, raise descriptive exception
            raise RuntimeError(
                f"Unable to get symbol information at {file}:{line}:{column}. "
                f"LSP server may not be running or the position may not contain a symbol. "
                f"Error: {str(e)}"
            )

        # If we still don't have a name, raise descriptive exception
        if result["name"] == "unknown":
            raise RuntimeError(
                f"No symbol found at {file}:{line}:{column}. "
                f"The position may be between symbols or in whitespace. "
                f"LSP hover and documentSymbol both returned no results."
            )

        return result

    def _parse_complete_hover_info(self, hover_text: str) -> Dict[str, Any]:
        """Parse LSP hover text to extract signature and docstring.

        LSP hover typically returns markdown like:
        ```python
        def create_user(name: str, email: str) -> User
        ```
        Creates a new user with the given name and email.

        Returns:
            Dict with name, type, signature, docstring
        """
        result = {
            "name": None,
            "type": None,
            "signature": None,
            "docstring": None,
        }

        # Extract code blocks (usually contain signature)
        code_block_match = re.search(r"```(?:\w+)?\n(.+?)```", hover_text, re.DOTALL)
        if code_block_match:
            code = code_block_match.group(1).strip()

            # The first line of the code block is usually the signature
            first_line = code.split("\n")[0].strip()

            # Detect function/method signatures
            if any(
                keyword in code
                for keyword in ["def ", "function ", "fn ", "=>", "func "]
            ):
                result["signature"] = first_line  # type: ignore[assignment]
                result["type"] = "function"  # type: ignore[assignment]

                # Extract function name
                match = re.search(r"\b(?:def|function|fn|func)\s+(\w+)", first_line)
                if match:
                    result["name"] = match.group(1)  # type: ignore[assignment]
                else:
                    # Try method name without keyword (e.g., "greet()" in JavaScript)
                    match = re.search(r"(\w+)\s*\(", first_line)
                    if match:
                        result["name"] = match.group(1)  # type: ignore[assignment]

            # Detect class/struct signatures
            elif any(
                keyword in code for keyword in ["class ", "struct ", "interface "]
            ):
                result["signature"] = first_line  # type: ignore[assignment]
                result["type"] = "class" if "class" in code else "struct"  # type: ignore[assignment]

                # Extract class/struct name
                match = re.search(r"\b(?:class|struct|interface)\s+(\w+)", first_line)
                if match:
                    result["name"] = match.group(1)  # type: ignore[assignment]

            # Extract docstring (text after code block)
            text_after_code = hover_text.split("```", 2)
            if len(text_after_code) > 2:
                docstring = text_after_code[2].strip()
                if docstring:
                    # Clean up markdown formatting
                    docstring = re.sub(r"\*\*(.+?)\*\*", r"\1", docstring)  # Bold
                    docstring = re.sub(r"\*(.+?)\*", r"\1", docstring)  # Italic
                    docstring = re.sub(r"`(.+?)`", r"\1", docstring)  # Inline code
                    result["docstring"] = docstring  # type: ignore[assignment]

        return result

    def _find_symbol_at_position(
        self,
        symbols: List[Dict],
        target_line: int,
        target_column: int,  # type: ignore[assignment]
    ) -> Optional[Dict]:  # type: ignore[assignment]
        """Find the symbol at a specific position (recursive, language-agnostic).

        LSP document symbols are hierarchical, so we need to search recursively
        to find the most specific symbol at the given position.

        Args:
            symbols: List of LSP document symbols
            target_line: Line number (1-indexed)
            target_column: Column number (0-indexed)

        Returns:
            The symbol at the position, or None if not found
        """
        for symbol in symbols:
            # Check if the symbol range contains our position
            symbol_range = symbol.get("range", {})
            start = symbol_range.get("start", {})
            end = symbol_range.get("end", {})

            start_line = start.get("line", -1) + 1  # Convert to 1-indexed
            start_col = start.get("character", -1)
            end_line = end.get("line", -1) + 1
            end_col = end.get("character", -1)

            # Check if position is within range
            if start_line <= target_line <= end_line:
                # Check column bounds
                if target_line == start_line and target_column < start_col:
                    continue
                if target_line == end_line and target_column > end_col:
                    continue

                # Position is within this symbol's range
                # Check if there's a more specific child symbol
                children = symbol.get("children", [])
                if children:
                    child_symbol = self._find_symbol_at_position(
                        children, target_line, target_column
                    )
                    if child_symbol:
                        return child_symbol

                # No more specific symbol, return this one
                return symbol

        return None

    def _lsp_kind_to_type(
        self, kind: Optional[int]
    ) -> Literal[
        "function", "class", "variable", "module", "method", "property", "struct"
    ]:
        """Convert LSP SymbolKind to our symbol type (language-agnostic).

        LSP SymbolKind enumeration is standardized across all languages:
        https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#symbolKind

        Args:
            kind: LSP SymbolKind integer

        Returns:
            Our symbol type string
        """
        if kind is None:
            return "variable"

        # LSP SymbolKind enumeration
        kind_map = {
            1: "module",  # File
            2: "module",  # Module
            3: "module",  # Namespace
            4: "module",  # Package
            5: "class",  # Class
            6: "method",  # Method
            7: "property",  # Property
            8: "variable",  # Field
            9: "function",  # Constructor
            10: "function",  # Enum
            11: "function",  # Interface
            12: "function",  # Function
            13: "variable",  # Variable
            14: "variable",  # Constant
            15: "variable",  # String
            16: "variable",  # Number
            17: "variable",  # Boolean
            18: "variable",  # Array
            19: "variable",  # Object
            20: "variable",  # Key
            21: "variable",  # Null
            22: "variable",  # EnumMember
            23: "struct",  # Struct
            24: "variable",  # Event
            25: "function",  # Operator
            26: "variable",  # TypeParameter
        }

        return kind_map.get(kind, "variable")  # type: ignore[return-value]

    # ========================================================================
    # DEPRECATED METHODS - NO LONGER USED
    # ========================================================================
    # The following methods used language-specific text parsing and have been
    # replaced with LSP-first approach. They are kept for backward compatibility
    # but should not be used in new code.
    # ========================================================================

    def _parse_symbol_info(
        self, line: str
    ) -> tuple[
        str,
        Literal[
            "function", "class", "variable", "module", "method", "property", "struct"
        ],
    ]:
        """Extract symbol name and type from definition line.

        Language-agnostic parser supporting Python, JavaScript, Rust, and more.

        Returns:
            Tuple of (symbol_name, symbol_type)
        """
        line = line.strip()

        # Python class definition
        if line.startswith("class "):
            match = re.match(r"class\s+(\w+)", line)
            if match:
                return match.group(1), "class"

        # JavaScript/TypeScript class definition
        # Matches: class User {, export class User {, export default class User {
        if re.match(r"(?:export\s+(?:default\s+)?)?class\s+\w+", line):
            match = re.search(r"class\s+(\w+)", line)
            if match:
                return match.group(1), "class"

        # Rust struct definition
        # Matches: pub struct User {, struct User {
        if re.match(r"(?:pub\s+)?struct\s+\w+", line):
            match = re.search(r"struct\s+(\w+)", line)
            if match:
                return match.group(1), "struct"

        # Python function/method definition
        if line.startswith("def ") or line.startswith("async def "):
            match = re.match(r"(?:async\s+)?def\s+(\w+)", line)
            if match:
                name = match.group(1)
                # Heuristic: __init__ or methods with self are methods
                if "__init__" in line or "self" in line:
                    return name, "method"
                return name, "function"

        # JavaScript/TypeScript function definition
        # Matches: function createUser(, async function createUser(, export function createUser(
        if re.match(r"(?:export\s+)?(?:async\s+)?function\s+\w+", line):
            match = re.search(r"function\s+(\w+)", line)
            if match:
                return match.group(1), "function"

        # JavaScript method definition (within class)
        # Matches: greet() {, async greet() {, constructor(
        if re.match(r"(?:async\s+)?(\w+)\s*\(", line) and not line.startswith(
            "function"
        ):
            match = re.match(r"(?:async\s+)?(\w+)\s*\(", line)
            if match:
                return match.group(1), "method"

        # Rust function definition
        # Matches: pub fn create_user(, fn create_user(, pub async fn create_user(
        if re.match(r"(?:pub\s+)?(?:async\s+)?fn\s+\w+", line):
            match = re.search(r"fn\s+(\w+)", line)
            if match:
                # Check if it's in an impl block (method) or standalone (function)
                # This is a heuristic - we can't easily tell from a single line
                return match.group(1), "function"

        # JavaScript arrow function or const function
        # Matches: const createUser = (, const createUser = async (
        if re.match(r"const\s+(\w+)\s*=\s*(?:async\s*)?\(", line):
            match = re.match(r"const\s+(\w+)", line)
            if match:
                return match.group(1), "function"

        # JavaScript module.exports - extract the first exported symbol
        # Matches: module.exports = { User, createUser }, exports.User = User
        if "module.exports" in line or line.startswith("exports."):
            # Try to extract from destructured export: { User, ... }
            match = re.search(r"\{\s*(\w+)", line)
            if match:
                # Return the first symbol in the export
                # Note: This is a heuristic - the LSP should ideally give us the exact position
                return match.group(
                    1
                ), "class"  # Assume exported items are important (class/function)
            # Try exports.Name = ...
            match = re.match(r"exports\.(\w+)", line)
            if match:
                return match.group(1), "variable"

        # Variable/constant (Python, JavaScript, Rust)
        # Matches: user = User(, const user = new User(, let user = User::new(
        if "=" in line:
            # Try to match the variable name before =
            match = re.match(r"(?:const|let|var|pub\s+const)?\s*(\w+)\s*=", line)
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

    # ========================================================================
    # END OF DEPRECATED METHODS
    # ========================================================================

    async def find_references(
        self,
        symbol: str,
        file: Optional[str] = None,
        line: Optional[int] = None,
        scope: Literal["file", "package", "project"] = "project",
        exclude_definition: bool = False,
    ) -> ReferencesResult:
        """Find all references to a symbol with enhanced formatting and grouping.

        Args:
            symbol: Symbol name to find references for
            file: Optional file context (required for LSP-based search)
            line: Optional line number (1-indexed) for position-based search
            scope: Search scope:
                - "file": Only references in the same file as the symbol
                - "package": Only references in the same package/module (Note: currently treated as "project")
                - "project": All references across the entire workspace (default)
            exclude_definition: If True, exclude the definition itself from results

        Returns:
            ReferencesResult with:
                - references: List of all Reference objects with context line numbers
                - total_count: Total number of references found
                - grouped_by_file: References grouped by file with per-file counts

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

        # Normalize the input file path for comparison
        input_file_path = (
            Path(file) if Path(file).is_absolute() else self.project_path / file
        )
        resolved_input_file = input_file_path.resolve()
        try:
            rel_input_file = str(
                resolved_input_file.relative_to(self.project_path.resolve())
            )
        except ValueError:
            rel_input_file = str(file)

        # Find the symbol on the line to get the correct column
        column = await self._find_symbol_column(file, line, symbol)

        # Get references from LSP
        lsp_result = await self.nvim_client.lsp_references(file, line, column)

        if not lsp_result or len(lsp_result) == 0:
            return ReferencesResult(references=[], total_count=0, grouped_by_file=[])

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

                # Get context with line number
                context_line = lines[ref_line - 1].rstrip()
                context = f"Line {ref_line}: {context_line}"

                # Make file path relative to project if possible
                try:
                    resolved_ref_file = Path(ref_file).resolve()
                    resolved_project = self.project_path.resolve()
                    rel_file = str(resolved_ref_file.relative_to(resolved_project))
                except ValueError:
                    rel_file = ref_file

                # Determine if this is the definition
                is_definition = rel_file == rel_input_file and ref_line == line

                # Detect reference type based on context
                ref_type = self._detect_reference_type(context_line, symbol)

                references.append(
                    Reference(
                        file=rel_file,
                        line=ref_line,
                        column=ref_column,
                        context=context,
                        is_definition=is_definition,
                        reference_type=ref_type,
                    )
                )
            except Exception:
                # Skip malformed locations
                continue

        # Apply scope filtering if needed
        if scope == "file":
            references = [ref for ref in references if ref.file == rel_input_file]

        # Filter out definition if requested
        if exclude_definition:
            references = [ref for ref in references if not ref.is_definition]

        # Group references by file
        file_groups: Dict[str, List[Reference]] = {}
        for ref in references:
            if ref.file not in file_groups:
                file_groups[ref.file] = []
            file_groups[ref.file].append(ref)

        grouped_by_file = [
            FileReferences(file=file_path, count=len(refs), references=refs)
            for file_path, refs in sorted(file_groups.items())
        ]

        return ReferencesResult(
            references=references,
            total_count=len(references),
            grouped_by_file=grouped_by_file,
        )

    def _detect_reference_type(self, context_line: str, symbol: str) -> Optional[str]:
        """Detect the type of reference based on context (language-agnostic).

        Args:
            context_line: The line of code containing the reference
            symbol: The symbol being referenced

        Returns:
            Type of reference: "import", "type_hint", "usage", or None
        """
        context_stripped = context_line.strip()

        # Language-agnostic patterns for imports
        # Most languages use some form of import/from/require/use/include
        import_patterns = [
            r"\bimport\b",  # Python, JavaScript, TypeScript, Java, Rust
            r"\bfrom\b",  # Python, JavaScript, TypeScript
            r"\brequire\b",  # Node.js, Ruby
            r"\buse\b",  # Rust, PHP
            r"\binclude\b",  # C, C++, PHP
            r"\bimport_module\b",  # Erlang
        ]
        if any(re.search(pattern, context_stripped) for pattern in import_patterns):
            return "import"

        # Language-agnostic patterns for type hints/annotations
        # Look for symbol in type position (after :, ->, <>, implements, extends, etc.)
        type_patterns = [
            rf":\s*{re.escape(symbol)}\b",  # Python, TypeScript: var: Type
            rf"->\s*{re.escape(symbol)}\b",  # Python, Rust: -> Type
            rf"<\s*{re.escape(symbol)}\s*>",  # Java, TypeScript, Rust: List<Type>
            rf"\bextends\s+{re.escape(symbol)}\b",  # Java, TypeScript: class X extends Y
            rf"\bimplements\s+{re.escape(symbol)}\b",  # Java, TypeScript: class X implements Y
            rf"\bas\s+{re.escape(symbol)}\b",  # TypeScript: import { X as Y }
        ]
        if any(re.search(pattern, context_stripped) for pattern in type_patterns):
            return "type_hint"

        # Default to usage (function call, variable use, etc.)
        return "usage"

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

    async def get_hover_info(
        self,
        file: str,
        symbol: Optional[str] = None,
        line: Optional[int] = None,
        column: Optional[int] = None,
    ) -> HoverInfo:
        """Get hover information (type, docstring) for a symbol.

        Supports two usage patterns:
        1. Symbol-based: Provide symbol name, optionally with line hint for disambiguation
        2. Position-based: Provide exact line and column position

        Args:
            file: File path
            symbol: Symbol name to find (e.g., "CliIdeServer", "find_definition")
            line: Line number (1-indexed), required if symbol not provided, optional hint if symbol provided
            column: Column number (0-indexed), required if symbol not provided

        Returns:
            HoverInfo with symbol name, type, docstring, and source file

        Raises:
            ValueError: If neither symbol nor (line, column) provided
            RuntimeError: If Neovim client not available or hover info not found

        Examples:
            # Symbol-based (agent-friendly)
            hover = await service.get_hover_info(file="server.py", symbol="CliIdeServer")

            # Position-based (precise)
            hover = await service.get_hover_info(file="server.py", line=83, column=15)

            # Disambiguated (symbol near specific line)
            hover = await service.get_hover_info(file="server.py", symbol="User", line=45)
        """
        if not self.nvim_client:
            raise RuntimeError("Neovim client required for get_hover_info")

        # Validate inputs
        if symbol is None and (line is None or column is None):
            raise ValueError(
                "Must provide either 'symbol' or both 'line' and 'column'. "
                "Examples: get_hover_info(file='x.py', symbol='MyClass') or "
                "get_hover_info(file='x.py', line=10, column=5)"
            )

        # If symbol provided, find its position
        if symbol is not None:
            line, column = await self._find_symbol_position(file, symbol, line)

        # Now we have line and column, proceed with position-based lookup
        # Get hover info from LSP - try exact position first
        lsp_result = await self.nvim_client.lsp_hover(file, line, column)

        # If no result at exact position, try nearby positions on the same line
        if not lsp_result:
            lsp_result = await self._try_nearby_columns(file, line, column)  # type: ignore[arg-type]

        if not lsp_result:
            # Provide more specific error message
            symbol_hint = f" for symbol '{symbol}'" if symbol else ""
            raise RuntimeError(
                f"No symbol found at {file}:{line}:{column}{symbol_hint}. "
                f"Try positioning cursor directly on the symbol name. "
                f"If the LSP server is still starting up, wait a moment and try again."
            )

        # Parse LSP hover response
        hover_info = await self._parse_hover_response(lsp_result, file, line, column)  # type: ignore[arg-type]

        return hover_info

    async def _find_symbol_position(
        self, file: str, symbol: str, line_hint: Optional[int] = None
    ) -> tuple[int, int]:
        """Find the position of a symbol in a file.

        Uses LSP document symbols to find the symbol. If line_hint is provided,
        prefers symbols near that line for disambiguation.

        Args:
            file: File path
            symbol: Symbol name to find
            line_hint: Optional line number hint for disambiguation (1-indexed)

        Returns:
            Tuple of (line, column) for the symbol (1-indexed line, 0-indexed column)

        Raises:
            RuntimeError: If symbol not found or multiple matches without line hint
        """
        # Get all symbols in the file using LSP
        symbols = await self.nvim_client.lsp_document_symbols(file)  # type: ignore[union-attr]

        if not symbols:
            raise RuntimeError(
                f"No symbols found in {file}. "
                f"File may not be indexed yet or LSP server not ready."
            )

        # Find matching symbols (search recursively through nested symbols)
        matches = self._find_matching_symbols(symbols, symbol)

        if not matches:
            raise RuntimeError(
                f"Symbol '{symbol}' not found in {file}. "
                f"Make sure the symbol name is spelled correctly."
            )

        # If line hint provided, find closest match to that line
        if line_hint is not None:
            # Find the match closest to the line hint
            matches.sort(key=lambda m: abs(m["line"] - line_hint))
            best_match = matches[0]
        elif len(matches) == 1:
            best_match = matches[0]
        else:
            # Multiple matches, no hint - use first one but warn in error if it fails
            best_match = matches[0]

        return best_match["line"], best_match["column"]

    def _find_matching_symbols(
        self, symbols: List[Dict[str, Any]], target_name: str
    ) -> List[Dict[str, int]]:
        """Recursively search for symbols matching the target name.

        Args:
            symbols: List of LSP DocumentSymbol dictionaries
            target_name: Symbol name to match

        Returns:
            List of dicts with 'line' and 'column' keys for each match
        """
        matches = []

        for symbol in symbols:
            # Get symbol name
            name = symbol.get("name", "")

            # Check if this symbol matches
            if name == target_name:
                # Extract position from range or location
                if "range" in symbol:
                    # DocumentSymbol format
                    start = symbol["range"]["start"]
                    matches.append(
                        {
                            "line": start["line"] + 1,  # Convert to 1-indexed
                            "column": start["character"],  # Keep 0-indexed
                        }
                    )
                elif "location" in symbol:
                    # SymbolInformation format
                    start = symbol["location"]["range"]["start"]
                    matches.append(
                        {
                            "line": start["line"] + 1,
                            "column": start["character"],
                        }
                    )

            # Recursively search children
            if "children" in symbol:
                matches.extend(
                    self._find_matching_symbols(symbol["children"], target_name)
                )

        return matches

    async def _try_nearby_columns(
        self, file: str, line: int, column: int
    ) -> Optional[Dict[str, Any]]:
        """Try to find a symbol near the specified column.

        This makes hover more forgiving when the cursor is close but not exactly
        on a symbol.

        Args:
            file: File path
            line: Line number (1-indexed)
            column: Column number (0-indexed)

        Returns:
            LSP hover result if found nearby, None otherwise
        """
        # Try a few positions to the left and right
        for offset in [1, 2, -1, 3, -2, 4, -3]:
            nearby_col = max(0, column + offset)
            result = await self.nvim_client.lsp_hover(file, line, nearby_col)  # type: ignore[union-attr]
            if result:
                return result
        return None

    async def _parse_hover_response(
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
        source_file = await self._get_source_file(hover_text, file, line, column)

        return HoverInfo(
            symbol=symbol_name,
            type=type_info,
            docstring=docstring,
            source_file=source_file,
            line=line,
            column=column,
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
            # Match async keyword separately to avoid capturing it
            match = re.match(r"async\s+def\s+(\w+)", text_line)
            if match:
                symbol_name = match.group(1)
                break

            # Try regular function definition
            match = re.match(r"def\s+(\w+)", text_line)
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

    async def _get_source_file(
        self, hover_text: str, file: str, line: int, column: int
    ) -> Optional[str]:
        """Get source file for a symbol, trying multiple methods.

        First tries to extract from hover text, then uses LSP definition
        as a fallback for imported symbols.

        Args:
            hover_text: The hover text from LSP
            file: Current file path
            line: Line number (1-indexed)
            column: Column number (0-indexed)

        Returns:
            Source file path if found, None otherwise
        """
        # Try extracting from hover text first
        match = re.search(
            r"(?:Defined in|From):\s*([^\s]+\.(?:py|js|ts|rs))", hover_text
        )
        if match:
            return match.group(1)

        # Fallback: Try to get definition location via LSP
        # This helps for imported symbols
        if self.nvim_client:
            try:
                definition = await self.nvim_client.lsp_definition(file, line, column)
                if definition and len(definition) > 0:
                    # Get the first definition's file
                    def_file = definition[0].get("targetUri", "")
                    if def_file:
                        # Convert URI to file path
                        if def_file.startswith("file://"):
                            def_file = def_file[7:]  # Remove file:// prefix
                        # Only return if it's different from current file (external symbol)
                        if def_file != file:
                            # Normalize path for response
                            from otter.utils.path import normalize_path_for_response

                            return normalize_path_for_response(
                                def_file, self.project_path
                            )
            except Exception:
                # If definition lookup fails, just return None
                pass

        return None

    async def get_completions(
        self, file: str, line: int, column: int, max_results: int = 50
    ) -> CompletionsResult:
        """Get context-aware code completions at a position.

        Returns intelligent code completion suggestions with proper ranking and filtering.
        By default, limits results to top 50 most relevant completions to avoid overwhelming output.

        Args:
            file: File path
            line: Line number (1-indexed)
            column: Column number (0-indexed, cursor position - where the cursor would be for typing)
            max_results: Maximum number of completions to return (default 50, 0 for unlimited)

        Returns:
            CompletionsResult with:
                - completions: List of Completion objects, sorted by relevance
                - total_count: Total number of completions available
                - returned_count: Number of completions returned (may be less than total if truncated)
                - truncated: True if results were limited by max_results

        Raises:
            RuntimeError: If Neovim client not available

        Examples:
            # Get completions after typing "self."
            result = await service.get_completions("file.py", line=10, column=9)
            # Returns top 50 most relevant completions

            # Get unlimited completions (use with caution)
            result = await service.get_completions("file.py", line=10, column=9, max_results=0)
        """
        if not self.nvim_client:
            raise RuntimeError("Neovim client required for get_completions")

        # Resolve file path
        file_path = Path(file) if Path(file).is_absolute() else self.project_path / file

        # Get completions from LSP
        lsp_completions = await self.nvim_client.lsp_completion(
            str(file_path), line, column
        )

        if not lsp_completions or len(lsp_completions) == 0:
            # Return empty result rather than raising error - no completions is valid
            return CompletionsResult(
                completions=[], total_count=0, returned_count=0, truncated=False
            )

        total_count = len(lsp_completions)

        # Parse LSP completion items into our Completion model
        completions = []
        for item in lsp_completions:
            # LSP CompletionItem structure:
            # - label: str (the text to insert)
            # - kind: int (CompletionItemKind enum)
            # - detail: Optional[str] (additional info like type signature)
            # - documentation: Optional[str | MarkupContent] (docstring/description)
            # - insertText: Optional[str] (text to insert, defaults to label)
            # - sortText: Optional[str] (for sorting by relevance)

            label = item.get("label", "")
            if not label:
                continue

            # Get the text to insert (prefer insertText, fallback to label)
            text = item.get("insertText", label)

            # Map LSP CompletionItemKind to human-readable strings
            kind_int = item.get("kind")
            kind = self._lsp_completion_kind_to_string(kind_int) if kind_int else None

            # Get detail text (type info, signature, etc.)
            detail = item.get("detail")

            # Extract documentation
            documentation = self._extract_completion_documentation(
                item.get("documentation")
            )

            # Get sort text for ranking (LSP provides this for relevance ordering)
            sort_text = item.get("sortText", label)

            completions.append(
                Completion(
                    text=text,
                    kind=kind,
                    detail=detail,
                    documentation=documentation,
                    sort_text=sort_text,
                )
            )

        # Sort by LSP-provided sort_text (which reflects relevance)
        # LSP servers use sortText to rank by relevance, with more relevant items having
        # lexicographically smaller sortText values
        completions.sort(key=lambda c: c.sort_text or c.text)

        # Apply max_results limit if specified (0 means unlimited)
        truncated = False
        if max_results > 0 and len(completions) > max_results:
            completions = completions[:max_results]
            truncated = True

        returned_count = len(completions)

        return CompletionsResult(
            completions=completions,
            total_count=total_count,
            returned_count=returned_count,
            truncated=truncated,
        )

    def _extract_completion_documentation(self, doc: Optional[Any]) -> Optional[str]:
        """Extract documentation string from LSP completion documentation field.

        LSP documentation can be:
        - string: Plain text or markdown
        - MarkupContent: {kind: "markdown" | "plaintext", value: string}
        - null/None: No documentation available

        Args:
            doc: Documentation field from LSP CompletionItem

        Returns:
            Extracted documentation string or None
        """
        if not doc:
            return None

        if isinstance(doc, str):
            return doc

        if isinstance(doc, dict):  # type: ignore
            # MarkupContent format
            if "value" in doc:
                return doc["value"]

        return None

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
