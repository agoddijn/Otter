from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from ..models.responses import Change, ExtractResult, RenamePreview, RenameResult
from ..utils.path import resolve_workspace_path


class RefactoringService:
    def __init__(self, project_path: str, nvim_client: Optional[Any] = None) -> None:
        """Initialize RefactoringService.

        Args:
            project_path: Root path of the project (required for path resolution)
            nvim_client: NeovimClient instance for LSP operations
        """
        self.project_path = project_path
        self.nvim_client = nvim_client

    async def rename_symbol(
        self,
        file: str,
        line: int,
        column: int,
        new_name: str,
        preview: bool = True,
    ) -> Union[RenamePreview, RenameResult]:
        """Rename a symbol using LSP.

        Args:
            file: File path where the symbol is located (relative to project root or absolute)
            line: Line number (1-indexed)
            column: Column number (0-indexed)
            new_name: New name for the symbol
            preview: If True, returns preview without applying changes

        Returns:
            RenamePreview or RenameResult depending on preview mode
        """
        if not self.nvim_client:
            raise RuntimeError("NeovimClient not initialized")

        # Resolve the file path relative to project root
        file_path = str(resolve_workspace_path(file, self.project_path))

        # Get WorkspaceEdit from LSP
        workspace_edit = await self.nvim_client.lsp_rename(
            file_path, line, column, new_name
        )

        if not workspace_edit:
            # No changes - symbol might not exist or LSP doesn't support rename
            if preview:
                return RenamePreview(changes=[], affected_files=0, total_changes=0)
            else:
                return RenameResult(changes_applied=0, files_updated=0)

        # Parse the WorkspaceEdit
        changes_list = self._parse_workspace_edit(workspace_edit)

        if preview:
            # Return preview without applying
            affected_files = len(set(change.file for change in changes_list))
            return RenamePreview(
                changes=changes_list,
                affected_files=affected_files,
                total_changes=len(changes_list),
            )
        else:
            # Apply changes using Neovim
            await self._apply_workspace_edit(workspace_edit)

            affected_files = len(set(change.file for change in changes_list))
            return RenameResult(
                changes_applied=len(changes_list), files_updated=affected_files
            )

    def _parse_workspace_edit(self, workspace_edit: Dict[str, Any]) -> List[Change]:
        """Parse LSP WorkspaceEdit into our Change objects.

        Args:
            workspace_edit: LSP WorkspaceEdit dictionary

        Returns:
            List of Change objects
        """
        changes: List[Change] = []

        # WorkspaceEdit can have "changes" (dict) or "documentChanges" (list)
        # Handle "documentChanges" format (modern LSP servers use this)
        if "documentChanges" in workspace_edit:
            for doc_change in workspace_edit["documentChanges"]:
                # Get the file URI
                uri = doc_change["textDocument"]["uri"]
                # Convert file:// URI to path
                file_path = uri.replace("file://", "")

                # Process each edit in this document
                for edit in doc_change["edits"]:
                    # Get the line number from the range
                    start_line = edit["range"]["start"]["line"] + 1  # 1-indexed

                    # For preview, we show old and new text
                    # LSP only gives us new text, so we'll use placeholders
                    old_text = edit.get("oldText", "[symbol]")
                    new_text = edit["newText"]

                    changes.append(
                        Change(
                            file=file_path,
                            line=start_line,
                            before=old_text,
                            after=new_text,
                        )
                    )

        # Handle "changes" format (legacy/simpler format)
        elif "changes" in workspace_edit:
            for uri, text_edits in workspace_edit["changes"].items():
                # Convert file:// URI to path
                file_path = uri.replace("file://", "")

                for edit in text_edits:
                    # Get the line number from the range
                    start_line = edit["range"]["start"]["line"] + 1  # 1-indexed

                    # For preview, we show old and new text
                    # LSP only gives us new text, so we'll use placeholders
                    old_text = edit.get("oldText", "[symbol]")
                    new_text = edit["newText"]

                    changes.append(
                        Change(
                            file=file_path,
                            line=start_line,
                            before=old_text,
                            after=new_text,
                        )
                    )

        return changes

    async def _apply_workspace_edit(self, workspace_edit: Dict[str, Any]) -> None:
        """Apply a WorkspaceEdit using Neovim's LSP client.

        Args:
            workspace_edit: LSP WorkspaceEdit dictionary
        """
        if not self.nvim_client:
            raise RuntimeError("NeovimClient not initialized")

        # Use Neovim's built-in function to apply workspace edits
        lua_code = """
        local workspace_edit = vim.json.decode(vim.api.nvim_eval('g:workspace_edit'))
        vim.lsp.util.apply_workspace_edit(workspace_edit, 'utf-8')
        """

        # Set the workspace_edit as a global variable for Lua to access
        await self.nvim_client.nvim.command(
            f"let g:workspace_edit = '{self._escape_json(workspace_edit)}'"
        )
        await self.nvim_client.execute_lua(lua_code)

    def _escape_json(self, obj: Any) -> str:
        """Escape JSON for Vim command."""
        import json

        return json.dumps(obj).replace("'", "''")

    async def extract_function(
        self,
        file: str,
        start_line: int,
        end_line: int,
        function_name: str,
        target_line: Optional[int] = None,
    ) -> ExtractResult:
        raise NotImplementedError("Stub: extract_function")
