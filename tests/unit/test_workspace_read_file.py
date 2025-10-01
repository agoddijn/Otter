"""Unit tests for WorkspaceService.read_file."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from otter.models.responses import FileContent
from otter.services.workspace import WorkspaceService


class TestReadFile:
    """Tests for read_file method."""

    @pytest.mark.asyncio
    async def test_read_entire_file_without_nvim(self, temp_project_dir: Path):
        """Test reading entire file without Neovim client."""
        # Create a test file
        test_file = temp_project_dir / "test.py"
        content = "line1\nline2\nline3\n"
        test_file.write_text(content)

        # Create service without nvim client
        service = WorkspaceService(project_path=str(temp_project_dir))

        # Read file
        result = await service.read_file("test.py")

        assert isinstance(result, FileContent)
        # Should include line numbers
        assert result.content == "1|line1\n2|line2\n3|line3"
        assert result.total_lines == 3
        assert result.language == "python"
        assert result.expanded_imports is None
        assert result.diagnostics is None

    @pytest.mark.asyncio
    async def test_read_file_with_line_range_without_nvim(self, temp_project_dir: Path):
        """Test reading specific line range without Neovim."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("line1\nline2\nline3\nline4\nline5\n")

        service = WorkspaceService(project_path=str(temp_project_dir))

        # Read lines 2-4
        result = await service.read_file("test.py", line_range=(2, 4))

        # Should include line numbers starting from line 2
        assert result.content == "2|line2\n3|line3\n4|line4"
        assert result.total_lines == 5

    @pytest.mark.asyncio
    async def test_read_file_with_context_lines_without_nvim(
        self, temp_project_dir: Path
    ):
        """Test reading with context lines without Neovim."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("line1\nline2\nline3\nline4\nline5\nline6\nline7\n")

        service = WorkspaceService(project_path=str(temp_project_dir))

        # Read lines 3-4 with 1 line of context
        result = await service.read_file("test.py", line_range=(3, 4), context_lines=1)

        # Should get lines 2-5 (3-4 ± 1) with line numbers
        assert result.content == "2|line2\n3|line3\n4|line4\n5|line5"
        assert result.total_lines == 7

    @pytest.mark.asyncio
    async def test_read_file_with_context_at_file_start(self, temp_project_dir: Path):
        """Test context lines don't go below line 1."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("line1\nline2\nline3\n")

        service = WorkspaceService(project_path=str(temp_project_dir))

        # Read line 1 with context - shouldn't try to read line 0
        result = await service.read_file("test.py", line_range=(1, 1), context_lines=5)

        # Should start at line 1 with line number
        assert result.content.startswith("1|line1")
        assert result.total_lines == 3

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, temp_project_dir: Path):
        """Test error when file doesn't exist."""
        service = WorkspaceService(project_path=str(temp_project_dir))

        with pytest.raises(FileNotFoundError, match="File not found"):
            await service.read_file("nonexistent.py")

    @pytest.mark.asyncio
    async def test_read_file_with_absolute_path(self, temp_project_dir: Path):
        """Test reading file with absolute path."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("absolute path test\n")

        service = WorkspaceService(project_path=str(temp_project_dir))

        # Use absolute path
        result = await service.read_file(str(test_file))

        # Should have line numbers
        assert result.content == "1|absolute path test"
        assert result.total_lines == 1

    @pytest.mark.asyncio
    async def test_read_file_with_nvim(self, temp_project_dir: Path):
        """Test reading file through Neovim client."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("nvim test\nline2\n")

        # Mock nvim client
        mock_nvim = AsyncMock()
        mock_nvim.is_running.return_value = True
        mock_nvim.read_buffer.return_value = ["nvim test", "line2"]

        service = WorkspaceService(
            project_path=str(temp_project_dir), nvim_client=mock_nvim
        )

        # Read without special features (should use direct read, not nvim)
        result = await service.read_file("test.py")

        # Should NOT have called nvim since no special features requested
        mock_nvim.read_buffer.assert_not_called()
        # Should have line numbers
        assert result.content == "1|nvim test\n2|line2"
        assert result.total_lines == 2

    @pytest.mark.asyncio
    async def test_line_range_exceeds_file_length(self, temp_project_dir: Path):
        """Test error when line range start exceeds file length."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("line1\nline2\nline3\n")

        service = WorkspaceService(project_path=str(temp_project_dir))

        # Try to read starting at line 100 of a 3-line file
        with pytest.raises(ValueError, match="exceeds file length"):
            await service.read_file("test.py", line_range=(100, 200))

    @pytest.mark.asyncio
    async def test_invalid_line_range_start_greater_than_end(self, temp_project_dir: Path):
        """Test error when line range start > end."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("line1\nline2\nline3\n")

        service = WorkspaceService(project_path=str(temp_project_dir))

        # Invalid range: start > end
        with pytest.raises(ValueError, match="must be >= start"):
            await service.read_file("test.py", line_range=(10, 5))

    @pytest.mark.asyncio
    async def test_line_range_end_exceeds_file_is_capped(self, temp_project_dir: Path):
        """Test that end line exceeding file length is capped (not an error)."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("line1\nline2\nline3\n")

        service = WorkspaceService(project_path=str(temp_project_dir))

        # Request lines 2-100, should return lines 2-3
        result = await service.read_file("test.py", line_range=(2, 100))

        assert result.content == "2|line2\n3|line3"
        assert result.total_lines == 3

    @pytest.mark.asyncio
    async def test_extract_imports_python(self, temp_project_dir: Path):
        """Test extracting Python imports (detection only, not expansion).

        NOTE: This currently only tests that import statements are detected.
        Full expansion with signatures (e.g., "User(id, name, email)") is not
        yet implemented and would require LSP hover/definition integration.
        """
        test_file = temp_project_dir / "test.py"
        test_file.write_text(
            "import os\nfrom pathlib import Path\nimport sys\nprint('hello')\n"
        )

        # Mock nvim client - is_running is NOT async!
        mock_nvim = MagicMock()
        mock_nvim.is_running = MagicMock(return_value=False)  # Not running initially
        mock_nvim.start = AsyncMock()
        mock_nvim.read_buffer = AsyncMock(
            return_value=[
                "import os",
                "from pathlib import Path",
                "import sys",
                "print('hello')",
            ]
        )

        service = WorkspaceService(
            project_path=str(temp_project_dir), nvim_client=mock_nvim
        )

        # Read with imports
        result = await service.read_file("test.py", include_imports=True)

        # Should have started nvim and read the file
        mock_nvim.start.assert_called_once()
        mock_nvim.read_buffer.assert_called_once()

        # Check imports were detected (but not expanded yet)
        assert result.expanded_imports is not None
        assert "import os" in result.expanded_imports
        assert "from pathlib import Path" in result.expanded_imports
        assert "import sys" in result.expanded_imports

        # Currently returns empty lists (expansion not implemented)
        assert result.expanded_imports["import os"] == []
        assert result.expanded_imports["from pathlib import Path"] == []

        # TODO: When LSP expansion is implemented, test should verify:
        # assert "os.path" in result.expanded_imports["import os"]
        # assert "Path(...)" in result.expanded_imports["from pathlib import Path"]

    @pytest.mark.asyncio
    async def test_include_diagnostics(self, temp_project_dir: Path):
        """Test including LSP diagnostics."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("def foo(\npass\n")  # Intentionally bad syntax

        # Mock nvim client with diagnostics
        mock_nvim = MagicMock()
        mock_nvim.is_running = MagicMock(return_value=True)
        mock_nvim.start = AsyncMock()
        mock_nvim.read_buffer = AsyncMock(return_value=["def foo(", "pass"])
        mock_nvim.get_diagnostics = AsyncMock(
            return_value=[
                {
                    "lnum": 0,  # Line 1 (0-indexed)
                    "col": 8,
                    "message": 'Expected ":"',
                    "severity": 1,  # Error
                    "source": "pyright",
                }
            ]
        )

        service = WorkspaceService(
            project_path=str(temp_project_dir), nvim_client=mock_nvim
        )

        # Read with diagnostics
        result = await service.read_file("test.py", include_diagnostics=True)

        # Should have diagnostics
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

        # Mock nvim with diagnostics on different lines
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

        # Read lines 2-3 with diagnostics
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

    @pytest.mark.asyncio
    async def test_nvim_starts_if_not_running(self, temp_project_dir: Path):
        """Test that Neovim is started if needed and not running."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("import os\n")

        # Mock nvim that's not running initially
        mock_nvim = MagicMock()
        mock_nvim.is_running = MagicMock(return_value=False)
        mock_nvim.start = AsyncMock()
        mock_nvim.read_buffer = AsyncMock(return_value=["import os"])

        service = WorkspaceService(
            project_path=str(temp_project_dir), nvim_client=mock_nvim
        )

        # Read with imports (requires nvim)
        await service.read_file("test.py", include_imports=True)

        # Should have started nvim
        mock_nvim.start.assert_called_once()
