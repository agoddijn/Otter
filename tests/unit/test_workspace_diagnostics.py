"""Unit tests for WorkspaceService.get_diagnostics."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from cli_ide.models.responses import Diagnostic
from cli_ide.services.workspace import WorkspaceService


class TestGetDiagnostics:
    """Tests for get_diagnostics method."""

    @pytest.mark.asyncio
    async def test_get_diagnostics_no_nvim_client(self, temp_project_dir: Path):
        """Test that get_diagnostics requires Neovim client."""
        service = WorkspaceService(project_path=str(temp_project_dir))

        with pytest.raises(RuntimeError, match="Neovim client required"):
            await service.get_diagnostics()

    @pytest.mark.asyncio
    async def test_get_diagnostics_for_specific_file(self, temp_project_dir: Path):
        """Test getting diagnostics for a specific file."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("def broken(:\n    pass\n")

        # Mock nvim client
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

        assert len(result) > 0
        assert all(isinstance(d, Diagnostic) for d in result)
        assert result[0].severity == "error"
        # Resolve both paths to handle symlinks (e.g., /var vs /private/var on macOS)
        assert Path(result[0].file).resolve() == test_file.resolve()

    @pytest.mark.asyncio
    async def test_get_diagnostics_filter_by_severity(self, temp_project_dir: Path):
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

        assert len(result) == 1
        assert result[0].severity == "error"

    @pytest.mark.asyncio
    async def test_get_diagnostics_multiple_severities(self, temp_project_dir: Path):
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

        assert len(result) == 2
        assert result[0].severity == "error"
        assert result[1].severity == "warning"

    @pytest.mark.asyncio
    async def test_get_all_diagnostics(self, temp_project_dir: Path):
        """Test getting diagnostics from all buffers."""
        mock_nvim = MagicMock()
        mock_nvim.is_running = MagicMock(return_value=True)
        # Mock execute_lua to return diagnostics from multiple buffers
        mock_nvim.execute_lua = AsyncMock(
            side_effect=[
                # First call: get all diagnostics
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
                # Subsequent calls: buffer names
                str(temp_project_dir / "file1.py"),
                str(temp_project_dir / "file2.py"),
            ]
        )

        service = WorkspaceService(
            project_path=str(temp_project_dir), nvim_client=mock_nvim
        )

        # Get diagnostics from all buffers (file=None)
        result = await service.get_diagnostics(file=None)

        assert len(result) == 2
        assert "file1.py" in result[0].file
        assert "file2.py" in result[1].file

    @pytest.mark.asyncio
    async def test_get_diagnostics_starts_nvim_if_not_running(
        self, temp_project_dir: Path
    ):
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

    @pytest.mark.asyncio
    async def test_get_diagnostics_handles_relative_path(self, temp_project_dir: Path):
        """Test that relative paths are resolved correctly."""
        test_file = temp_project_dir / "src" / "test.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
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
                }
            ]
        )

        service = WorkspaceService(
            project_path=str(temp_project_dir), nvim_client=mock_nvim
        )

        # Use relative path
        result = await service.get_diagnostics(file="src/test.py")

        assert len(result) > 0
        # Resolve both paths to handle symlinks
        assert Path(result[0].file).resolve() == test_file.resolve()
