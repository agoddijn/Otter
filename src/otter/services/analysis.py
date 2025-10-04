from __future__ import annotations

from pathlib import Path
from typing import Any, List, Literal, Optional

from ..models.responses import (
    CodeExplanation,
    DependencyGraph,
    Improvement,
    SemanticDiff,
)
from ..utils.path import normalize_path_for_response, resolve_workspace_path


class AnalysisService:
    def __init__(self, nvim_client: Any, project_path: Optional[str] = None) -> None:
        """Initialize AnalysisService.

        Args:
            nvim_client: NeovimClient instance (required for all analysis operations)
            project_path: Root path of the project
        """
        self.nvim_client = nvim_client
        self.project_path = Path(project_path) if project_path else Path.cwd()

        # TreeSitter queries for finding imports across different languages
        # These capture the MODULE NAME directly, not the whole statement!
        # This makes downstream processing language-agnostic.
        self._import_queries = {
            "python": """
                ; Capture module name from: import foo
                (import_statement
                  name: (dotted_name) @module)
                ; Capture module name from: from foo import bar
                (import_from_statement
                  module_name: (dotted_name) @module)
            """,
            "javascript": """
                ; Capture from: import X from 'foo'
                (import_statement
                  source: (string) @module)
                ; Capture from: require('foo')
                (call_expression
                  function: (identifier) @fn (#eq? @fn "require")
                  arguments: (arguments (string) @module))
            """,
            "typescript": """
                ; Capture from: import X from 'foo'
                (import_statement
                  source: (string) @module)
                ; Capture from: require('foo')
                (call_expression
                  function: (identifier) @fn (#eq? @fn "require")
                  arguments: (arguments (string) @module))
            """,
            "rust": """
                ; Capture from: use foo::bar
                (use_declaration
                  argument: (scoped_identifier
                    path: (identifier) @module))
                ; Also capture simple: use foo
                (use_declaration
                  argument: (identifier) @module)
            """,
            "go": """
                ; Capture from: import "foo"
                (import_spec
                  path: (interpreted_string_literal) @module)
            """,
        }

    async def explain_code(
        self,
        file: str,
        line_range: Optional[tuple[int, int]] = None,
        detail_level: Literal["brief", "normal", "detailed"] = "normal",
    ) -> CodeExplanation:
        raise NotImplementedError("Stub: explain_code")

    async def suggest_improvements(
        self, file: str, focus_areas: Optional[List[str]] = None
    ) -> List[Improvement]:
        raise NotImplementedError("Stub: suggest_improvements")

    async def semantic_diff(
        self,
        file: str,
        from_revision: Optional[str] = "HEAD~1",
        to_revision: Optional[str] = "HEAD",
    ) -> SemanticDiff:
        raise NotImplementedError("Stub: semantic_diff")

    async def analyze_dependencies(
        self, file: str, direction: Literal["imports", "imported_by", "both"] = "both"
    ) -> DependencyGraph:
        """Analyze module dependencies using TreeSitter (language-agnostic).

        This is a pure wrapper around Neovim's TreeSitter - all parsing is done
        by TreeSitter parsers, making this work for any language with TreeSitter support.

        Args:
            file: Path to file to analyze (relative to project root or absolute)
            direction: What to analyze - "imports" (what this file imports),
                      "imported_by" (what imports this file), or "both"

        Returns:
            DependencyGraph with imports and imported_by lists

        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If Neovim client not running
        """
        if not self.nvim_client.is_running():
            raise RuntimeError("Neovim client not running for dependency analysis")

        # Resolve file path (workspace-relative or absolute)
        file_path = resolve_workspace_path(file, self.project_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file}")

        # Initialize result
        imports: List[str] = []
        imported_by: List[str] = []

        # Get imports from the file using TreeSitter
        if direction in ("imports", "both"):
            imports = await self._get_imports_via_treesitter(file_path)

        # Find files that import this file using workspace search
        if direction in ("imported_by", "both"):
            imported_by = await self._get_imported_by_via_search(file_path)

        # Normalize path for response (workspace-relative if inside, absolute if outside)
        normalized_file = normalize_path_for_response(file_path, self.project_path)

        return DependencyGraph(
            file=normalized_file, imports=imports, imported_by=imported_by
        )

    async def _get_imports_via_treesitter(self, file_path: Path) -> List[str]:
        """Extract import module names using TreeSitter via Neovim (language-agnostic).

        Pure wrapper around TreeSitter - delegates all parsing to Neovim's TreeSitter.
        Our queries capture @module names directly, making downstream processing language-agnostic.
        """
        try:
            # Open the file in Neovim
            await self.nvim_client.open_file(str(file_path))

            # Get the filetype from Neovim
            filetype = await self.nvim_client.execute_lua("return vim.bo.filetype")

            # Get the appropriate TreeSitter query for this language
            query = self._import_queries.get(filetype)
            if not query:
                # No TreeSitter query for this language - return empty
                return []

            # Execute TreeSitter query to find module names
            # This is pure delegation to Neovim's TreeSitter
            # The query captures @module, so we get module names directly!
            lua_code = f"""
            local bufnr = vim.fn.bufnr('{file_path}')
            local parser = vim.treesitter.get_parser(bufnr, '{filetype}')
            if not parser then
                return {{}}
            end
            
            local tree = parser:parse()[1]
            local root = tree:root()
            
            local query = vim.treesitter.query.parse('{filetype}', [[{query}]])
            local modules = {{}}
            
            for id, node in query:iter_captures(root, bufnr, 0, -1) do
                local text = vim.treesitter.get_node_text(node, bufnr)
                table.insert(modules, text)
            end
            
            return modules
            """

            module_names = await self.nvim_client.execute_lua(lua_code)

            # Clean the module names (remove quotes, etc.)
            imports = self._extract_module_names(module_names, filetype)

            return sorted(set(imports))  # Remove duplicates and sort

        except Exception as e:
            # TreeSitter not available or failed - raise descriptive exception
            raise RuntimeError(
                f"Unable to extract imports from {file_path}. "
                f"TreeSitter parser may not be installed for this file type, "
                f"or the file has syntax errors. "
                f"Error: {str(e)}"
            )

    def _extract_module_names(
        self, module_names: List[str], filetype: str
    ) -> List[str]:
        """Clean module names captured by TreeSitter (language-agnostic).
        
        TreeSitter now captures module names directly, we just need to clean them up:
        - Remove quotes from JavaScript/TypeScript strings: 'foo' -> foo
        - Remove quotes from Go strings: "foo" -> foo
        - Python and Rust module names come clean from TreeSitter
        
        Args:
            module_names: Module names captured by TreeSitter @module captures
            filetype: File type (for any language-specific cleanup if needed)
            
        Returns:
            Cleaned module names
        """
        
        cleaned = []
        for name in module_names:
            # Strip surrounding whitespace
            name = name.strip()
            
            # Remove surrounding quotes (single or double) if present
            # This handles JavaScript/TypeScript: 'foo', "foo"
            # And Go: "foo"
            if name.startswith(("'", '"')) and name.endswith(("'", '"')):
                name = name[1:-1]
            
            if name:  # Only add non-empty names
                cleaned.append(name)
        
        return cleaned

    async def _get_imported_by_via_search(self, target_file: Path) -> List[str]:
        """Find files that import the target file using ripgrep (language-agnostic).

        Uses a generic regex pattern that matches common import/require/use syntax
        across most programming languages.
        
        Instead of having separate patterns for each language, we use a broad pattern
        that captures the common structure:
        - Import keyword: import, from, require, use, include, etc.
        - Module reference: the filename/module we're looking for
        """
        try:
            # Get the module/file name to search for
            file_stem = target_file.stem  # filename without extension
            import re as regex_module
            escaped_stem = regex_module.escape(file_stem)

            # Generic pattern that matches import statements across languages
            # This covers:
            # - Python: import foo, from foo import
            # - JavaScript/TypeScript: import ... from 'foo', require('foo')
            # - Rust: use foo::
            # - Go: import "foo"
            # - Ruby: require 'foo'
            # - PHP: use foo, include 'foo'
            # - Java: import foo
            # - C/C++: #include "foo"
            # - And many more!
            
            # Pattern explanation:
            # Look for common import keywords followed by the module name
            # The module name can appear:
            # - As a bare identifier: import foo
            # - In quotes: require('foo'), import "foo"
            # - With path separators: use foo::bar, import foo.bar
            patterns = [
                # Match import-like keywords followed by our module name
                f"\\b(import|from|require|use|include|#include)\\b.*\\b{escaped_stem}\\b",
                # Match module name in quotes (for path-based imports)
                f"(import|require|include).*['\"].*{escaped_stem}",
            ]

            # Combine patterns with OR
            combined_pattern = "|".join(patterns)
            # Escape single quotes for Lua string (use [[...]] for raw string)

            # Use ripgrep with regex and file list output
            lua_code = f"""
            local pattern = [[{combined_pattern}]]
            local project_path = '{self.project_path}'
            local target = '{target_file}'
            
            -- Build and execute ripgrep command (language-agnostic)
            -- Use vim.fn.shellescape to properly escape the pattern
            -- Search all source code files (use ripgrep's built-in type filtering)
            -- This covers Python, JS, TS, Rust, Go, Ruby, PHP, Java, C, C++, and more!
            local cmd = string.format(
                "rg -e %s -l -t py -t js -t ts -t rust -t go -t ruby -t php -t java -t cpp -t c -g '!**/node_modules/**' -g '!**/.git/**' -g '!**/venv/**' -g '!**/__pycache__/**' -g '!**/target/**' -g '!**/build/**' -g '!**/dist/**' %s",
                vim.fn.shellescape(pattern),
                vim.fn.shellescape(project_path)
            )
            
            local results = vim.fn.systemlist(cmd)
            
            -- Check for errors (ripgrep returns 1 if no matches, which is ok)
            local v_shell_error = vim.v.shell_error
            if v_shell_error > 1 then
                -- Error other than "no matches found"
                return {{}}
            end
            
            -- Filter out the target file itself and make paths relative
            local filtered = {{}}
            for _, path in ipairs(results) do
                -- Skip empty lines and error messages
                if path and path ~= '' and not path:match('^rg:') and not path:match('^zsh:') then
                    local resolved_path = vim.fn.fnamemodify(path, ':p')
                    local target_resolved = vim.fn.fnamemodify(target, ':p')
                    
                    if resolved_path ~= target_resolved then
                        -- Make path relative to project
                        local rel = path:gsub('^' .. project_path .. '/', '')
                        table.insert(filtered, rel)
                    end
                end
            end
            
            return filtered
            """

            imported_by = await self.nvim_client.execute_lua(lua_code)

            return sorted(set(imported_by)) if imported_by else []
        except Exception as e:
            # If ripgrep or search fails, raise descriptive exception
            raise RuntimeError(
                f"Unable to search for files importing {target_file}. "
                f"Ripgrep may not be installed or accessible. "
                f"Error: {str(e)}"
            )
