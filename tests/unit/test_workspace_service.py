"""Unit tests for WorkspaceService.

Consolidated tests for:
- get_project_structure: Project tree navigation and filtering
- get_diagnostics: LSP diagnostic retrieval and filtering
- read_file: File reading with line ranges, diagnostics, imports

All tests use mocked Neovim clients to avoid external dependencies.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from otter.models.responses import Diagnostic, FileContent, ProjectTree
from otter.services.workspace import WorkspaceService

# ============================================================================
# Tests: Project Structure
# ============================================================================


class TestProjectStructure:
    """Tests for get_project_structure method."""

    @pytest.mark.asyncio
    async def test_basic_structure(self, temp_project_dir: Path):
        """Test basic project structure retrieval."""
        workspace = WorkspaceService(project_path=str(temp_project_dir))

        result = await workspace.get_project_structure(
            path=".", max_depth=3, show_hidden=False, include_sizes=True
        )

        assert isinstance(result, ProjectTree)
        assert result.root == str(temp_project_dir.resolve())
        assert isinstance(result.tree, dict)
        assert result.file_count > 0
        assert result.directory_count > 0
        assert result.total_size > 0

        # Tree should contain direct children
        assert "src" in result.tree
        assert "tests" in result.tree
        assert "README.md" in result.tree
        assert result.tree["src"]["type"] == "directory"

    @pytest.mark.asyncio
    async def test_hides_pycache(self, temp_project_dir: Path):
        """Test that __pycache__ directories are excluded."""
        workspace = WorkspaceService(project_path=str(temp_project_dir))

        result = await workspace.get_project_structure(
            path=".", max_depth=3, show_hidden=False, include_sizes=False
        )

        src = result.tree["src"]
        assert "__pycache__" not in src["children"]

    @pytest.mark.asyncio
    async def test_respects_max_depth(self, temp_project_dir: Path):
        """Test that max_depth is respected."""
        workspace = WorkspaceService(project_path=str(temp_project_dir))

        result = await workspace.get_project_structure(
            path=".", max_depth=1, show_hidden=False, include_sizes=False
        )

        assert "src" in result.tree
        src_entry = result.tree["src"]
        assert src_entry["type"] == "directory"
        assert "children_truncated" in src_entry
        assert src_entry["children_truncated"] is True

    @pytest.mark.asyncio
    async def test_includes_file_sizes(self, temp_project_dir: Path):
        """Test that file sizes are included when requested."""
        workspace = WorkspaceService(project_path=str(temp_project_dir))

        result = await workspace.get_project_structure(
            path=".", max_depth=2, show_hidden=False, include_sizes=True
        )

        readme = result.tree["README.md"]
        assert readme["type"] == "file"
        assert "size" in readme
        assert isinstance(readme["size"], int)
        assert readme["size"] > 0
        assert result.total_size > 0

    @pytest.mark.asyncio
    async def test_excludes_file_sizes(self, temp_project_dir: Path):
        """Test that file sizes are excluded when not requested."""
        workspace = WorkspaceService(project_path=str(temp_project_dir))

        result = await workspace.get_project_structure(
            path=".", max_depth=2, show_hidden=False, include_sizes=False
        )

        readme = result.tree["README.md"]
        assert readme["type"] == "file"
        assert "size" not in readme
        assert result.total_size == 0

    @pytest.mark.asyncio
    async def test_hidden_files_filtering(self, temp_project_dir: Path):
        """Test hidden file visibility control."""
        workspace = WorkspaceService(project_path=str(temp_project_dir))

        # Hidden files excluded by default
        result1 = await workspace.get_project_structure(
            path=".", max_depth=2, show_hidden=False, include_sizes=False
        )
        assert ".gitignore" not in result1.tree

        # Hidden files included when requested
        result2 = await workspace.get_project_structure(
            path=".", max_depth=2, show_hidden=True, include_sizes=False
        )
        assert ".gitignore" in result2.tree
        assert result2.tree[".gitignore"]["type"] == "file"

    @pytest.mark.asyncio
    async def test_nested_directories(self, temp_project_dir: Path):
        """Test that nested directories are properly represented."""
        workspace = WorkspaceService(project_path=str(temp_project_dir))

        result = await workspace.get_project_structure(
            path=".", max_depth=3, show_hidden=False, include_sizes=False
        )

        src = result.tree["src"]
        assert "utils" in src["children"]
        utils = src["children"]["utils"]
        assert utils["type"] == "directory"
        assert "children" in utils
        assert "helper.py" in utils["children"]

    @pytest.mark.asyncio
    async def test_relative_path(self, temp_project_dir: Path):
        """Test getting structure of a subdirectory."""
        workspace = WorkspaceService(project_path=str(temp_project_dir))

        result = await workspace.get_project_structure(
            path="src", max_depth=2, show_hidden=False, include_sizes=False
        )

        assert result.root.endswith("/src")
        assert "main.py" in result.tree
        assert "utils" in result.tree

    @pytest.mark.asyncio
    async def test_exclude_patterns(self, temp_project_dir: Path):
        """Test that exclude patterns work."""
        workspace = WorkspaceService(project_path=str(temp_project_dir))

        result = await workspace.get_project_structure(
            path=".",
            max_depth=3,
            show_hidden=False,
            include_sizes=False,
            exclude_patterns=["*.md"],
        )

        assert "README.md" not in result.tree
        assert "src" in result.tree  # Other files still present


# ============================================================================
# Tests: Diagnostics
# ============================================================================


class TestDiagnostics:
    """Tests for get_diagnostics method."""

    @pytest.mark.asyncio
    async def test_requires_nvim_client(self, temp_project_dir: Path):
        """Test that get_diagnostics requires Neovim client."""
        service = WorkspaceService(project_path=str(temp_project_dir))

        with pytest.raises(RuntimeError, match="Neovim client required"):
            await service.get_diagnostics()

    @pytest.mark.asyncio
    async def test_get_diagnostics_for_file(self, temp_project_dir: Path):
        """Test getting diagnostics for a specific file."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("def broken(:\n    pass\n")

        mock_nvim = MagicMock()
        mock_nvim.is_running = MagicMock(return_value=True)
        mock_nvim.get_diagnostics = AsyncMock(
            return_value=[
                {
                    "lnum": 0,
                    "col": 11,
                    "message": "Expected parameter name",
                    "severity": 1,
                    "source": "Pyright",
                }
            ]
        )

        service = WorkspaceService(
            project_path=str(temp_project_dir), nvim_client=mock_nvim
        )

        result = await service.get_diagnostics(file="test.py")

        assert result.total_count > 0
        assert len(result.diagnostics) > 0
        assert all(isinstance(d, Diagnostic) for d in result.diagnostics)
        assert result.diagnostics[0].severity == "error"
        assert Path(result.diagnostics[0].file).resolve() == test_file.resolve()

    @pytest.mark.asyncio
    async def test_filter_by_severity(self, temp_project_dir: Path):
        """Test filtering diagnostics by severity."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("code")

        mock_nvim = MagicMock()
        mock_nvim.is_running = MagicMock(return_value=True)
        mock_nvim.get_diagnostics = AsyncMock(
            return_value=[
                {
                    "lnum": 0,
                    "col": 0,
                    "message": "Error",
                    "severity": 1,
                    "source": "lsp",
                },
                {
                    "lnum": 1,
                    "col": 0,
                    "message": "Warning",
                    "severity": 2,
                    "source": "lsp",
                },
                {
                    "lnum": 2,
                    "col": 0,
                    "message": "Info",
                    "severity": 3,
                    "source": "lsp",
                },
            ]
        )

        service = WorkspaceService(
            project_path=str(temp_project_dir), nvim_client=mock_nvim
        )

        # Get only errors
        result = await service.get_diagnostics(file="test.py", severity=["error"])

        assert len(result.diagnostics) == 1
        assert result.diagnostics[0].severity == "error"

    @pytest.mark.asyncio
    async def test_filter_multiple_severities(self, temp_project_dir: Path):
        """Test filtering by multiple severity levels."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("code")

        mock_nvim = MagicMock()
        mock_nvim.is_running = MagicMock(return_value=True)
        mock_nvim.get_diagnostics = AsyncMock(
            return_value=[
                {
                    "lnum": 0,
                    "col": 0,
                    "message": "Error",
                    "severity": 1,
                    "source": "lsp",
                },
                {
                    "lnum": 1,
                    "col": 0,
                    "message": "Warning",
                    "severity": 2,
                    "source": "lsp",
                },
                {
                    "lnum": 2,
                    "col": 0,
                    "message": "Info",
                    "severity": 3,
                    "source": "lsp",
                },
                {
                    "lnum": 3,
                    "col": 0,
                    "message": "Hint",
                    "severity": 4,
                    "source": "lsp",
                },
            ]
        )

        service = WorkspaceService(
            project_path=str(temp_project_dir), nvim_client=mock_nvim
        )

        # Get errors and warnings
        result = await service.get_diagnostics(
            file="test.py", severity=["error", "warning"]
        )

        assert len(result.diagnostics) == 2
        assert result.diagnostics[0].severity == "error"
        assert result.diagnostics[1].severity == "warning"

    @pytest.mark.asyncio
    async def test_get_all_diagnostics(self, temp_project_dir: Path):
        """Test getting diagnostics from all buffers."""
        mock_nvim = MagicMock()
        mock_nvim.is_running = MagicMock(return_value=True)
        mock_nvim.execute_lua = AsyncMock(
            side_effect=[
                [
                    {
                        "bufnr": 1,
                        "lnum": 0,
                        "col": 0,
                        "message": "Error in file1",
                        "severity": 1,
                        "source": "lsp",
                    },
                    {
                        "bufnr": 2,
                        "lnum": 0,
                        "col": 0,
                        "message": "Error in file2",
                        "severity": 1,
                        "source": "lsp",
                    },
                ],
                str(temp_project_dir / "file1.py"),
                str(temp_project_dir / "file2.py"),
            ]
        )

        service = WorkspaceService(
            project_path=str(temp_project_dir), nvim_client=mock_nvim
        )

        result = await service.get_diagnostics(file=None)

        assert len(result.diagnostics) == 2
        assert "file1.py" in result.diagnostics[0].file
        assert "file2.py" in result.diagnostics[1].file

    @pytest.mark.asyncio
    async def test_starts_nvim_if_needed(self, temp_project_dir: Path):
        """Test that Neovim is started if not running."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("code")

        mock_nvim = MagicMock()
        mock_nvim.is_running = MagicMock(return_value=False)
        mock_nvim.start = AsyncMock()
        mock_nvim.get_diagnostics = AsyncMock(return_value=[])

        service = WorkspaceService(
            project_path=str(temp_project_dir), nvim_client=mock_nvim
        )

        await service.get_diagnostics(file="test.py")

        mock_nvim.start.assert_called_once()


# ============================================================================
# Tests: Read File
# ============================================================================


class TestReadFile:
    """Tests for read_file method."""

    @pytest.mark.asyncio
    async def test_read_entire_file(self, temp_project_dir: Path):
        """Test reading entire file without Neovim client."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("line1\nline2\nline3\n")

        service = WorkspaceService(project_path=str(temp_project_dir))
        result = await service.read_file("test.py")

        assert isinstance(result, FileContent)
        assert result.content == "1|line1\n2|line2\n3|line3"
        assert result.total_lines == 3
        assert result.language == "python"
        assert result.expanded_imports is None
        assert result.diagnostics is None

    @pytest.mark.asyncio
    async def test_read_line_range(self, temp_project_dir: Path):
        """Test reading specific line range."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("line1\nline2\nline3\nline4\nline5\n")

        service = WorkspaceService(project_path=str(temp_project_dir))
        result = await service.read_file("test.py", line_range=(2, 4))

        assert result.content == "2|line2\n3|line3\n4|line4"
        assert result.total_lines == 5

    @pytest.mark.asyncio
    async def test_read_with_context_lines(self, temp_project_dir: Path):
        """Test reading with context lines."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("line1\nline2\nline3\nline4\nline5\nline6\nline7\n")

        service = WorkspaceService(project_path=str(temp_project_dir))
        result = await service.read_file("test.py", line_range=(3, 4), context_lines=1)

        # Should get lines 2-5 (3-4 ± 1)
        assert result.content == "2|line2\n3|line3\n4|line4\n5|line5"
        assert result.total_lines == 7

    @pytest.mark.asyncio
    async def test_context_at_file_start(self, temp_project_dir: Path):
        """Test context lines don't go below line 1."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("line1\nline2\nline3\n")

        service = WorkspaceService(project_path=str(temp_project_dir))
        result = await service.read_file("test.py", line_range=(1, 1), context_lines=5)

        assert result.content.startswith("1|line1")
        assert result.total_lines == 3

    @pytest.mark.asyncio
    async def test_nonexistent_file_raises_error(self, temp_project_dir: Path):
        """Test error when file doesn't exist."""
        service = WorkspaceService(project_path=str(temp_project_dir))

        with pytest.raises(FileNotFoundError, match="File not found"):
            await service.read_file("nonexistent.py")

    @pytest.mark.asyncio
    async def test_read_with_absolute_path(self, temp_project_dir: Path):
        """Test reading file with absolute path."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("absolute path test\n")

        service = WorkspaceService(project_path=str(temp_project_dir))
        result = await service.read_file(str(test_file))

        assert result.content == "1|absolute path test"
        assert result.total_lines == 1

    @pytest.mark.asyncio
    async def test_line_range_validations(self, temp_project_dir: Path):
        """Test line range validation errors."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("line1\nline2\nline3\n")

        service = WorkspaceService(project_path=str(temp_project_dir))

        # Line range exceeds file length
        with pytest.raises(ValueError, match="exceeds file length"):
            await service.read_file("test.py", line_range=(100, 200))

        # Start greater than end
        with pytest.raises(ValueError, match="must be >= start"):
            await service.read_file("test.py", line_range=(10, 5))

    @pytest.mark.asyncio
    async def test_line_range_end_capped(self, temp_project_dir: Path):
        """Test that end line exceeding file length is capped."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("line1\nline2\nline3\n")

        service = WorkspaceService(project_path=str(temp_project_dir))
        result = await service.read_file("test.py", line_range=(2, 100))

        assert result.content == "2|line2\n3|line3"
        assert result.total_lines == 3

    @pytest.mark.asyncio
    async def test_include_diagnostics(self, temp_project_dir: Path):
        """Test including LSP diagnostics."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("def foo(\npass\n")

        mock_nvim = MagicMock()
        mock_nvim.is_running = MagicMock(return_value=True)
        mock_nvim.start = AsyncMock()
        mock_nvim.read_buffer = AsyncMock(return_value=["def foo(", "pass"])
        mock_nvim.get_diagnostics = AsyncMock(
            return_value=[
                {
                    "lnum": 0,
                    "col": 8,
                    "message": 'Expected ":"',
                    "severity": 1,
                    "source": "pyright",
                }
            ]
        )

        service = WorkspaceService(
            project_path=str(temp_project_dir), nvim_client=mock_nvim
        )

        result = await service.read_file("test.py", include_diagnostics=True)

        assert result.diagnostics is not None
        assert len(result.diagnostics) > 0
        diag = result.diagnostics[0]
        assert diag.line == 1  # Converted to 1-indexed
        assert diag.severity == "error"
        assert "Expected" in diag.message

    @pytest.mark.asyncio
    async def test_diagnostics_filtered_by_line_range(self, temp_project_dir: Path):
        """Test that diagnostics are filtered to line range."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("line1\nline2\nline3\nline4\n")

        mock_nvim = MagicMock()
        mock_nvim.is_running = MagicMock(return_value=True)
        mock_nvim.start = AsyncMock()
        mock_nvim.read_buffer = AsyncMock(return_value=["line2", "line3"])
        mock_nvim.get_diagnostics = AsyncMock(
            return_value=[
                {"lnum": 0, "col": 0, "message": "Error on line 1", "severity": 1},
                {"lnum": 1, "col": 0, "message": "Error on line 2", "severity": 1},
                {"lnum": 2, "col": 0, "message": "Error on line 3", "severity": 1},
                {"lnum": 3, "col": 0, "message": "Error on line 4", "severity": 1},
            ]
        )

        service = WorkspaceService(
            project_path=str(temp_project_dir), nvim_client=mock_nvim
        )

        result = await service.read_file(
            "test.py", line_range=(2, 3), include_diagnostics=True
        )

        # Should only have diagnostics for lines 2-3
        assert result.diagnostics is not None
        assert len(result.diagnostics) == 2
        assert all(2 <= d.line <= 3 for d in result.diagnostics)

    @pytest.mark.asyncio
    async def test_diagnostic_severity_mapping(self, temp_project_dir: Path):
        """Test LSP severity code mapping."""
        service = WorkspaceService(project_path=str(temp_project_dir))

        assert service._map_diagnostic_severity(1) == "error"
        assert service._map_diagnostic_severity(2) == "warning"
        assert service._map_diagnostic_severity(3) == "info"
        assert service._map_diagnostic_severity(4) == "hint"
        assert (
            service._map_diagnostic_severity(99) == "info"
        )  # Unknown defaults to info
