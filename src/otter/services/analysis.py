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
        # These capture import/require/use statements
        self._import_queries = {
            "python": """
                (import_statement) @import
                (import_from_statement) @import
            """,
            "javascript": """
                (import_statement) @import
                (call_expression
                  function: (identifier) @fn (#eq? @fn "require")
                ) @import
            """,
            "typescript": """
                (import_statement) @import
                (call_expression
                  function: (identifier) @fn (#eq? @fn "require")
                ) @import
            """,
            "rust": """
                (use_declaration) @import
                (extern_crate_declaration) @import
            """,
            "go": """
                (import_declaration) @import
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
        """Extract imports using TreeSitter via Neovim (language-agnostic).

        Pure wrapper around TreeSitter - delegates all parsing to Neovim's TreeSitter.
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

            # Execute TreeSitter query to find import nodes
            # This is pure delegation to Neovim's TreeSitter
            lua_code = f"""
            local bufnr = vim.fn.bufnr('{file_path}')
            local parser = vim.treesitter.get_parser(bufnr, '{filetype}')
            if not parser then
                return {{}}
            end
            
            local tree = parser:parse()[1]
            local root = tree:root()
            
            local query = vim.treesitter.query.parse('{filetype}', [[{query}]])
            local imports = {{}}
            
            for id, node in query:iter_captures(root, bufnr, 0, -1) do
                local text = vim.treesitter.get_node_text(node, bufnr)
                table.insert(imports, text)
            end
            
            return imports
            """

            import_nodes = await self.nvim_client.execute_lua(lua_code)

            # Parse the import statements to extract module names
            imports = self._extract_module_names(import_nodes, filetype)

            return sorted(set(imports))  # Remove duplicates and sort

        except Exception:
            # TreeSitter not available or failed - return empty
            return []

    def _extract_module_names(
        self, import_statements: List[str], filetype: str
    ) -> List[str]:
        """Extract module names from import statement text."""
        import re

        modules = []

        for stmt in import_statements:
            if filetype == "python":
                # "import foo" -> "foo"
                # "from foo import bar" -> "foo"
                match = re.search(r"(?:import|from)\s+(\S+)", stmt)
                if match:
                    modules.append(match.group(1))
            elif filetype in ("javascript", "typescript"):
                # "import X from 'foo'" -> "foo"
                # "require('foo')" -> "foo"
                match = re.search(r'[\'"]([^\'"]+)[\'"]', stmt)
                if match:
                    modules.append(match.group(1))
            elif filetype == "rust":
                # "use foo::bar;" -> "foo"
                match = re.search(r"use\s+(\w+)", stmt)
                if match:
                    modules.append(match.group(1))
            elif filetype == "go":
                # 'import "foo"' -> "foo"
                match = re.search(r'"([^"]+)"', stmt)
                if match:
                    modules.append(match.group(1))

        return modules

    async def _get_imported_by_via_search(self, target_file: Path) -> List[str]:
        """Find files that import the target file using ripgrep.

        Uses ripgrep with regex patterns to find actual import statements.
        Searches for language-specific import patterns (Python, JS/TS, Rust, Go).
        """
        try:
            # Get the module/file name to search for
            file_stem = target_file.stem  # filename without extension

            # Build regex pattern for common import patterns across languages
            # Python: import foo, from foo import, from .foo import, from ..foo
            # JS/TS: import ... from './foo', require('./foo'), require('foo')
            # Rust: use foo::, use crate::foo
            # Go: import "foo", import "path/foo"

            # Build comprehensive regex for import statements
            # This matches lines that look like actual imports, not just any mention
            import re as regex_module

            escaped_stem = regex_module.escape(file_stem)

            patterns = [
                # Python imports
                f"\\b(import|from)\\s+.*\\b{escaped_stem}\\b",
                # JavaScript/TypeScript imports
                f"(import|require).*['\"].*{escaped_stem}",
                # Rust use statements
                f"use\\s+.*\\b{escaped_stem}\\b",
                # Go imports
                f'import\\s+.*"{escaped_stem}"',
            ]

            # Combine patterns with OR
            combined_pattern = "|".join(patterns)
            # Escape single quotes for Lua string (use [[...]] for raw string)

            # Use ripgrep with regex and file list output
            lua_code = f"""
            local pattern = [[{combined_pattern}]]
            local project_path = '{self.project_path}'
            local target = '{target_file}'
            
            -- Build and execute ripgrep command
            -- Use vim.fn.shellescape to properly escape the pattern
            local cmd = string.format(
                "rg -e %s -l -g '*.{{py,js,ts,tsx,jsx,rs,go}}' -g '!**/node_modules/**' -g '!**/.git/**' -g '!**/venv/**' -g '!**/__pycache__/**' %s",
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
        except Exception:
            # If ripgrep or search fails, return empty
            return []
