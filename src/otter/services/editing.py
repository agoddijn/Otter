"""Buffer editing service.

This service provides tools for modifying code in Neovim buffers.
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import List

from ..neovim.client import NeovimClient
from ..models.responses import (
    BufferEdit,
    BufferInfo,
    EditResult,
    SaveResult,
    DiscardResult,
    BufferDiff,
    FindReplaceResult,
)
from ..utils.path import resolve_workspace_path


class EditingService:
    """Service for buffer editing operations."""

    def __init__(self, nvim_client: NeovimClient, project_path: str):
        """Initialize the editing service.

        Args:
            nvim_client: Neovim client instance
            project_path: Root path of the project
        """
        self.nvim_client = nvim_client
        self.project_path = Path(project_path)

    async def get_buffer_info(self, file: str) -> BufferInfo:
        """Get information about a buffer.

        Args:
            file: Path to the file (relative to project root or absolute)

        Returns:
            BufferInfo with current buffer state

        Example:
            >>> info = await service.get_buffer_info("src/models.py")
            >>> if info.is_modified:
            >>>     print("Buffer has unsaved changes")
        """
        # Resolve path
        file_path = resolve_workspace_path(file, self.project_path)

        # Get buffer info from Neovim
        info = await self.nvim_client.get_buffer_info(str(file_path))

        return BufferInfo(
            file=file,
            is_open=info["is_open"],
            is_modified=info["is_modified"],
            line_count=info["line_count"],
            language=info["language"],
        )

    async def edit_buffer(
        self, file: str, edits: List[BufferEdit], preview: bool = True
    ) -> EditResult:
        """Edit a buffer with one or more line-based changes.

        Args:
            file: Path to the file (relative to project root or absolute)
            edits: List of BufferEdit operations to apply
            preview: If True, return a diff without applying changes.
                    If False, apply changes immediately.

        Returns:
            EditResult with preview diff (if preview=True) or success status

        Example:
            >>> # Preview changes first
            >>> result = await service.edit_buffer(
            >>>     "src/models.py",
            >>>     [BufferEdit(
            >>>         line_start=10,
            >>>         line_end=12,
            >>>         new_text="def new_function():\\n    pass\\n"
            >>>     )],
            >>>     preview=True
            >>> )
            >>> print(result.preview)  # Shows unified diff
            >>>
            >>> # Apply changes
            >>> result = await service.edit_buffer(
            >>>     "src/models.py",
            >>>     [BufferEdit(...)],
            >>>     preview=False
            >>> )
        """
        # Resolve path
        file_path = resolve_workspace_path(file, self.project_path)

        try:
            # Open or create the buffer
            # For new files, this will create an empty buffer
            await self.nvim_client.open_file(str(file_path), create_if_missing=True)

            # Read current buffer content (will be empty for new files)
            current_lines = await self.nvim_client.read_buffer(str(file_path))

            if preview:
                # Generate preview diff
                modified_lines = current_lines.copy()

                # Apply edits to a copy (sorted in reverse order to avoid offset issues)
                sorted_edits = sorted(edits, key=lambda e: e.line_start, reverse=True)

                for edit in sorted_edits:
                    start_idx = edit.line_start - 1  # Convert to 0-indexed
                    end_idx = edit.line_end  # Exclusive end

                    # Validate line range
                    if start_idx < 0 or end_idx > len(modified_lines):
                        return EditResult(
                            file=file,
                            success=False,
                            error=f"Invalid line range: {edit.line_start}-{edit.line_end} (file has {len(current_lines)} lines)",
                        )

                    # Split new text into lines
                    new_lines = edit.new_text.split("\n")
                    # Remove last empty line if text doesn't end with newline
                    if new_lines and new_lines[-1] == "":
                        new_lines = new_lines[:-1]

                    # Replace lines
                    modified_lines[start_idx:end_idx] = new_lines

                # Generate unified diff
                diff = difflib.unified_diff(
                    current_lines,
                    modified_lines,
                    fromfile=f"a/{file}",
                    tofile=f"b/{file}",
                    lineterm="",
                )
                diff_text = "\n".join(diff)

                return EditResult(
                    file=file, preview=diff_text, applied=False, success=True
                )
            else:
                # Apply edits directly
                # Convert BufferEdit objects to tuples for Neovim client
                edit_tuples = []
                for edit in edits:
                    # Split new text into lines
                    new_lines = edit.new_text.split("\n")
                    # Remove last empty line if text doesn't end with newline
                    if new_lines and new_lines[-1] == "":
                        new_lines = new_lines[:-1]

                    edit_tuples.append((edit.line_start, edit.line_end, new_lines))

                result = await self.nvim_client.edit_buffer_lines(
                    str(file_path), edit_tuples
                )

                return EditResult(
                    file=file,
                    applied=True,
                    success=result["success"],
                    line_count=result["line_count"],
                    is_modified=result["is_modified"],
                )

        except FileNotFoundError:
            return EditResult(file=file, success=False, error=f"File not found: {file}")
        except ValueError as e:
            return EditResult(file=file, success=False, error=str(e))
        except Exception as e:
            return EditResult(
                file=file, success=False, error=f"Failed to edit buffer: {e}"
            )

    async def save_buffer(self, file: str) -> SaveResult:
        """Save a buffer to disk.

        Args:
            file: Path to the file (relative to project root or absolute)

        Returns:
            SaveResult with success status

        Example:
            >>> # Edit buffer
            >>> await service.edit_buffer("src/models.py", edits, preview=False)
            >>> # Save changes to disk
            >>> result = await service.save_buffer("src/models.py")
            >>> if result.success:
            >>>     print("File saved!")
        """
        # Resolve path
        file_path = resolve_workspace_path(file, self.project_path)

        try:
            # Save the buffer
            result = await self.nvim_client.save_buffer(str(file_path))

            return SaveResult(
                file=file,
                success=result["success"],
                is_modified=result["is_modified"],
                error=result.get("error"),
            )

        except RuntimeError as e:
            return SaveResult(
                file=file,
                success=False,
                is_modified=True,  # Unknown state
                error=str(e),
            )
        except Exception as e:
            return SaveResult(
                file=file,
                success=False,
                is_modified=True,  # Unknown state
                error=f"Failed to save buffer: {e}",
            )

    async def discard_buffer(self, file: str) -> DiscardResult:
        """Discard changes in a buffer (reload from disk).

        Args:
            file: Path to the file (relative to project root or absolute)

        Returns:
            DiscardResult with success status

        Example:
            >>> # Made some edits, want to undo them
            >>> result = await service.discard_buffer("src/models.py")
            >>> if result.success:
            >>>     print("Changes discarded!")
        """
        # Resolve path
        file_path = resolve_workspace_path(file, self.project_path)

        try:
            # Discard the buffer changes
            result = await self.nvim_client.discard_buffer(str(file_path))

            return DiscardResult(
                file=file,
                success=result["success"],
                is_modified=result["is_modified"],
                error=result.get("error"),
            )

        except RuntimeError as e:
            return DiscardResult(
                file=file,
                success=False,
                is_modified=True,  # Unknown state
                error=str(e),
            )
        except Exception as e:
            return DiscardResult(
                file=file,
                success=False,
                is_modified=True,  # Unknown state
                error=f"Failed to discard buffer: {e}",
            )

    async def get_buffer_diff(self, file: str) -> BufferDiff:
        """Get diff between buffer and disk version.

        Args:
            file: Path to the file (relative to project root or absolute)

        Returns:
            BufferDiff showing what changed

        Example:
            >>> # Check what changed before saving
            >>> diff = await service.get_buffer_diff("src/models.py")
            >>> if diff.has_changes:
            >>>     print(diff.diff)  # Shows unified diff
        """
        # Resolve path
        file_path = resolve_workspace_path(file, self.project_path)

        try:
            # Get the diff
            result = await self.nvim_client.get_buffer_diff(str(file_path))

            return BufferDiff(
                file=file,
                has_changes=result["has_changes"],
                diff=result.get("diff"),
                error=result.get("error"),
            )

        except RuntimeError as e:
            return BufferDiff(file=file, has_changes=False, error=str(e))
        except Exception as e:
            return BufferDiff(
                file=file, has_changes=False, error=f"Failed to get buffer diff: {e}"
            )

    async def find_and_replace(
        self,
        file: str,
        find: str,
        replace: str,
        occurrence: str = "all",  # "all", "first", or a number like "2"
        preview: bool = True,
    ) -> FindReplaceResult:
        """Find and replace text in a file (convenience wrapper).

        This is a text-based alternative to line-based edit_buffer.
        More natural for simple substitutions.

        Args:
            file: Path to the file (relative to project root or absolute)
            find: Text to find (exact match, whitespace-sensitive)
            replace: Text to replace with
            occurrence: Which occurrences to replace:
                - "all": Replace all occurrences (default)
                - "first": Replace only the first occurrence
                - "1", "2", etc.: Replace specific occurrence (1-indexed)
            preview: If True, return preview diff. If False, apply changes.

        Returns:
            FindReplaceResult with preview or application results

        Example:
            >>> # Preview replacing all "INFO" with "DEBUG"
            >>> result = await service.find_and_replace(
            ...     "config.py",
            ...     find='log_level = "INFO"',
            ...     replace='log_level = "DEBUG"',
            ...     occurrence="all",
            ...     preview=True
            ... )
            >>> print(result.preview)  # Shows diff

        Note:
            - Whitespace-sensitive (spaces and tabs must match exactly)
            - For complex edits, use edit_buffer with line numbers
            - Cannot insert new lines; use edit_buffer for structural changes
        """
        # Resolve path
        file_path = resolve_workspace_path(file, self.project_path)

        try:
            # Check if buffer is open, if so read from buffer instead of disk
            buffer_info = await self.get_buffer_info(file)
            if buffer_info.is_open:
                # Read from buffer (get current in-memory content)
                buffer_content = await self.nvim_client.get_buffer_content(
                    str(file_path)
                )
                if buffer_content is not None:
                    original_content = buffer_content
                else:
                    # Buffer not found, read from disk
                    with open(file_path, "r") as f:
                        original_content = f.read()
            else:
                # Read from disk if buffer not open
                with open(file_path, "r") as f:
                    original_content = f.read()

            # Perform replacement
            if occurrence == "all":
                new_content = original_content.replace(find, replace)
                replacements_made = original_content.count(find)
            elif occurrence == "first" or occurrence == "1":
                new_content = original_content.replace(find, replace, 1)
                replacements_made = 1 if find in original_content else 0
            else:
                # Specific occurrence number
                try:
                    occ_num = int(occurrence)
                    if occ_num < 1:
                        raise ValueError("Occurrence must be >= 1")

                    # Find all occurrences
                    parts = original_content.split(find)
                    if len(parts) <= occ_num:
                        # Not enough occurrences
                        new_content = original_content
                        replacements_made = 0
                    else:
                        # Replace only the Nth occurrence
                        new_content = (
                            find.join(parts[:occ_num])
                            + replace
                            + find.join(parts[occ_num:])
                        )
                        replacements_made = 1
                except ValueError:
                    return FindReplaceResult(
                        file=file,
                        success=False,
                        error=f"Invalid occurrence value: {occurrence}. Use 'all', 'first', or a number.",
                    )

            # If no changes, return early
            if new_content == original_content:
                return FindReplaceResult(
                    file=file,
                    success=True,
                    applied=False,
                    replacements_made=0,
                    preview="No matches found." if preview else None,
                    error=None if replacements_made == 0 else None,
                )

            # Preview mode: generate diff
            if preview:
                original_lines = original_content.splitlines()
                new_lines = new_content.splitlines()

                diff = difflib.unified_diff(
                    original_lines,
                    new_lines,
                    fromfile=f"a/{file}",
                    tofile=f"b/{file}",
                    lineterm="",
                )
                diff_str = "\n".join(diff)

                return FindReplaceResult(
                    file=file,
                    success=True,
                    preview=diff_str,
                    applied=False,
                    replacements_made=replacements_made,
                )

            # Apply mode: write to buffer using edit_buffer
            # Convert text replacement to line-based edit
            new_lines = new_content.splitlines(keepends=True)
            if not new_content.endswith("\n") and new_lines:
                # Last line doesn't have newline
                new_lines[-1] = new_lines[-1].rstrip("\n")

            # Read file to get line count
            with open(file_path, "r") as f:
                original_line_count = len(f.readlines())

            # Create a single edit that replaces the entire file
            edits = [
                BufferEdit(
                    line_start=1, line_end=original_line_count, new_text=new_content
                )
            ]

            # Apply via edit_buffer
            edit_result = await self.edit_buffer(file, edits, preview=False)

            return FindReplaceResult(
                file=file,
                success=edit_result.success,
                applied=edit_result.applied,
                replacements_made=replacements_made,
                line_count=edit_result.line_count,
                is_modified=edit_result.is_modified,
                error=edit_result.error,
            )

        except FileNotFoundError:
            return FindReplaceResult(
                file=file, success=False, error=f"File not found: {file}"
            )
        except Exception as e:
            return FindReplaceResult(
                file=file, success=False, error=f"Failed to find/replace: {e}"
            )
