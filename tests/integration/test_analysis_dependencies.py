"""Integration tests for analyze_dependencies with real project files.

Note: These tests verify the tool runs correctly. Actual import detection
depends on TreeSitter parsers being installed in Neovim, which happens
automatically on first run via lazy.nvim.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from cli_ide.neovim.client import NeovimClient
from cli_ide.services.analysis import AnalysisService


class TestAnalyzeDependenciesIntegration:
    """Integration tests using the actual project structure."""

    @pytest.fixture
    async def nvim_client(self):
        """Create and start a Neovim client for testing."""
        project_root = Path(__file__).parent.parent.parent
        client = NeovimClient(project_path=str(project_root))
        await client.start()
        yield client
        await client.stop()

    @pytest.fixture
    def service(self, nvim_client):
        """Create AnalysisService with the actual project path and Neovim client."""
        # Use the actual project root
        project_root = Path(__file__).parent.parent.parent
        return AnalysisService(nvim_client=nvim_client, project_path=str(project_root))

    @pytest.mark.asyncio
    async def test_analyze_server_dependencies(self, service):
        """Test analyzing the main server.py file - verifies tool runs without error."""
        result = await service.analyze_dependencies(
            "src/cli_ide/server.py", direction="both"
        )

        assert result.file == "src/cli_ide/server.py"
        assert isinstance(result.imports, list)
        assert isinstance(result.imported_by, list)

    @pytest.mark.asyncio
    async def test_analyze_responses_dependencies(self, service):
        """Test analyzing the models/responses.py file - verifies tool runs."""
        result = await service.analyze_dependencies(
            "src/cli_ide/models/responses.py", direction="both"
        )

        assert result.file == "src/cli_ide/models/responses.py"
        assert isinstance(result.imports, list)
        assert isinstance(result.imported_by, list)

    @pytest.mark.asyncio
    async def test_analyze_analysis_service(self, service):
        """Test analyzing the analysis service itself."""
        result = await service.analyze_dependencies(
            "src/cli_ide/services/analysis.py", direction="imports"
        )

        assert result.file == "src/cli_ide/services/analysis.py"
        assert isinstance(result.imports, list)

    @pytest.mark.asyncio
    async def test_analyze_neovim_client(self, service):
        """Test analyzing neovim client dependencies."""
        result = await service.analyze_dependencies(
            "src/cli_ide/neovim/client.py", direction="imported_by"
        )

        assert result.file == "src/cli_ide/neovim/client.py"
        assert isinstance(result.imported_by, list)

    @pytest.mark.asyncio
    async def test_imports_only_excludes_imported_by(self, service):
        """Test that direction='imports' doesn't include imported_by."""
        result = await service.analyze_dependencies(
            "src/cli_ide/models/responses.py", direction="imports"
        )

        assert result.imported_by == []

    @pytest.mark.asyncio
    async def test_imported_by_only_excludes_imports(self, service):
        """Test that direction='imported_by' doesn't include imports."""
        result = await service.analyze_dependencies(
            "src/cli_ide/models/responses.py", direction="imported_by"
        )

        assert result.imports == []

    @pytest.mark.asyncio
    async def test_analyze_with_relative_path(self, service):
        """Test analyzing with a relative path from project root."""
        result = await service.analyze_dependencies("src/cli_ide/__init__.py")

        assert result.file == "src/cli_ide/__init__.py"

    @pytest.mark.asyncio
    async def test_nonexistent_file_raises_error(self, service):
        """Test that analyzing a nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            await service.analyze_dependencies("src/nonexistent.py")

    @pytest.mark.asyncio
    async def test_without_nvim_client_raises_error(self):
        """Test that analyzing without running Neovim client raises RuntimeError."""
        # Create a mock nvim client that's not running
        from unittest.mock import MagicMock

        mock_nvim = MagicMock()
        mock_nvim.is_running.return_value = False

        service = AnalysisService(nvim_client=mock_nvim, project_path="/tmp")

        with pytest.raises(RuntimeError, match="Neovim client not running"):
            await service.analyze_dependencies("some_file.py")

    @pytest.mark.asyncio
    async def test_temp_project_with_imports(self, nvim_client):
        """Test with a temporary project - verifies tool runs without crashing.

        Note: Actual import detection depends on TreeSitter parsers being installed.
        """
        with TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create test files
            (project_path / "main.py").write_text(
                "import os\nimport sys\nfrom pathlib import Path\n"
            )

            (project_path / "utils.py").write_text("from main import something\n")

            service = AnalysisService(
                nvim_client=nvim_client, project_path=str(project_path)
            )

            # Test imports detection - should run without crashing
            result = await service.analyze_dependencies(
                str(project_path / "main.py"), direction="imports"
            )

            assert isinstance(result.imports, list)
            assert isinstance(result.file, str)

            # Test imported_by detection - should run without crashing
            result = await service.analyze_dependencies(
                str(project_path / "main.py"), direction="imported_by"
            )

            assert isinstance(result.imported_by, list)
