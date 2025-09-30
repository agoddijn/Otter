"""Path resolution utilities for workspace-relative paths."""

from __future__ import annotations

from pathlib import Path
from typing import Union


def resolve_workspace_path(
    path: Union[str, Path],
    project_root: Union[str, Path],
) -> Path:
    """Resolve a path relative to the project workspace.

    Handles both absolute and relative paths correctly:
    - Absolute paths: returned as-is (resolved to canonical form)
    - Relative paths: resolved relative to project_root
    - Already-absolute workspace paths: returned as-is

    Args:
        path: Path to resolve (can be absolute or relative)
        project_root: Root directory of the project workspace

    Returns:
        Resolved absolute Path object

    Examples:
        >>> # Relative path
        >>> resolve_workspace_path("src/main.py", "/project")
        Path("/project/src/main.py")

        >>> # Absolute path
        >>> resolve_workspace_path("/abs/path/file.py", "/project")
        Path("/abs/path/file.py")

        >>> # Workspace-relative path (common in MCP calls)
        >>> resolve_workspace_path("main.py", "/fern_mono")
        Path("/fern_mono/main.py")
    """
    path_obj = Path(path)
    project_root_obj = Path(project_root).resolve()

    # If path is absolute, resolve and return
    if path_obj.is_absolute():
        return path_obj.resolve()

    # Path is relative - resolve relative to project root
    resolved = (project_root_obj / path_obj).resolve()

    return resolved


def make_relative_to_workspace(
    path: Union[str, Path],
    project_root: Union[str, Path],
) -> Path:
    """Convert an absolute path to be relative to the workspace.

    Args:
        path: Absolute path to convert
        project_root: Root directory of the project workspace

    Returns:
        Path relative to project_root

    Raises:
        ValueError: If path is not within project_root

    Examples:
        >>> make_relative_to_workspace("/project/src/main.py", "/project")
        Path("src/main.py")
    """
    path_obj = Path(path).resolve()
    project_root_obj = Path(project_root).resolve()

    try:
        return path_obj.relative_to(project_root_obj)
    except ValueError as e:
        # Path is outside project root
        raise ValueError(
            f"Path {path_obj} is not within project root {project_root_obj}"
        ) from e


def normalize_path_for_response(
    path: Union[str, Path],
    project_root: Union[str, Path],
) -> str:
    """Normalize a path for returning in API responses.

    Converts absolute paths to workspace-relative when possible,
    keeps absolute paths for files outside workspace.

    Handles macOS symlinks (/var vs /private/var) correctly.

    Args:
        path: Path to normalize
        project_root: Root directory of the project workspace

    Returns:
        Normalized path as string (relative to workspace if inside it)

    Examples:
        >>> normalize_path_for_response("/project/src/main.py", "/project")
        "src/main.py"

        >>> normalize_path_for_response("/outside/file.py", "/project")
        "/outside/file.py"
    """
    path_obj = Path(path).resolve()
    project_root_obj = Path(project_root).resolve()

    try:
        # Try to make relative - works for files inside workspace
        relative = path_obj.relative_to(project_root_obj)
        return str(relative)
    except ValueError:
        # File is outside workspace - return absolute path
        return str(path_obj)
