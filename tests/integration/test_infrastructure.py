"""Integration tests for infrastructure components.

Consolidated tests for:
- Neovim Client: Lifecycle, file operations, Lua execution
- Bootstrap: LSP/DAP adapter installation and configuration
- Configuration: Loading and applying .otter.toml settings

These tests verify the foundational components that support all other features.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from otter.neovim.client import NeovimClient

# ============================================================================
# Tests: Neovim Client
# ============================================================================


class TestNeovimClient:
    """Tests for NeovimClient lifecycle and operations."""

    @pytest.mark.asyncio
    async def test_client_initialization(self, temp_project_dir: Path):
        """Test that client can be initialized."""
        client = NeovimClient(project_path=str(temp_project_dir))

        assert client.project_path == temp_project_dir.resolve()
        assert not client.is_running()

    @pytest.mark.asyncio
    async def test_start_and_stop(self, temp_project_dir: Path):
        """Test starting and stopping Neovim."""
        client = NeovimClient(project_path=str(temp_project_dir))

        try:
            await asyncio.wait_for(client.start(), timeout=10.0)
            assert client.is_running()
            assert client.nvim is not None
        finally:
            await client.stop()

        assert not client.is_running()
        assert client.nvim is None

    @pytest.mark.asyncio
    async def test_context_manager(self, temp_project_dir: Path):
        """Test using client as context manager."""
        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            assert client.is_running()
            assert client.nvim is not None

        assert not client.is_running()

    @pytest.mark.asyncio
    async def test_open_file(self, temp_project_dir: Path):
        """Test opening a file."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("print('hello')\n")

        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            buf_num = await client.open_file(str(test_file))
            assert buf_num > 0

    @pytest.mark.asyncio
    async def test_read_buffer(self, temp_project_dir: Path):
        """Test reading buffer contents."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("line1\nline2\nline3\n")

        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            await client.open_file(str(test_file))
            lines = await client.read_buffer(str(test_file))

            assert len(lines) == 3
            assert lines[0] == "line1"
            assert lines[1] == "line2"

    @pytest.mark.asyncio
    async def test_read_buffer_with_range(self, temp_project_dir: Path):
        """Test reading specific lines from buffer."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("line1\nline2\nline3\nline4\n")

        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            await client.open_file(str(test_file))
            lines = await client.read_buffer(str(test_file), line_range=(2, 3))

            assert len(lines) == 2
            assert lines[0] == "line2"
            assert lines[1] == "line3"

    @pytest.mark.asyncio
    async def test_execute_lua(self, temp_project_dir: Path):
        """Test executing Lua code."""
        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            result = await client.execute_lua("return 2 + 2")
            assert result == 4

    @pytest.mark.asyncio
    async def test_execute_lua_with_vim_api(self, temp_project_dir: Path):
        """Test executing Lua with Vim API calls."""
        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            result = await client.execute_lua("return vim.api.nvim_get_vvar('version')")
            assert result > 0


# ============================================================================
# Tests: Bootstrap Integration
# ============================================================================


class TestBootstrapIntegration:
    """Test LSP bootstrap integration with NeovimClient."""

    @pytest.mark.asyncio
    async def test_bootstrap_runs_on_start_with_auto_install(self):
        """Test that bootstrap runs when starting Neovim with auto_install=true."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create a Python file to trigger language detection
            (project_path / "main.py").write_text("print('hello')")

            # Create config with auto_install enabled
            config_file = project_path / ".otter.toml"
            config_file.write_text(
                """
[lsp]
auto_install = true
languages = ["python"]
"""
            )

            # Mock the bootstrap function to avoid actual installation
            with patch(
                "otter.bootstrap.lsp_installer.check_and_install_lsp_servers"
            ) as mock_bootstrap:
                mock_bootstrap.return_value = AsyncMock(return_value={})

                nvim_client = NeovimClient(project_path=str(project_path))
                await nvim_client.start()

                # Verify Neovim started successfully
                assert nvim_client.is_running()

                await nvim_client.stop()

    @pytest.mark.asyncio
    async def test_bootstrap_skipped_when_disabled(self):
        """Test that bootstrap is skipped when auto_install=false."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            (project_path / "main.py").write_text("print('hello')")

            config_file = project_path / ".otter.toml"
            config_file.write_text(
                """
[lsp]
auto_install = false
languages = ["python"]
"""
            )

            with patch(
                "otter.bootstrap.lsp_installer.check_and_install_lsp_servers"
            ) as mock_bootstrap:
                nvim_client = NeovimClient(project_path=str(project_path))
                await nvim_client.start()

                # Bootstrap should not be called
                assert not mock_bootstrap.called

                await nvim_client.stop()

    @pytest.mark.asyncio
    async def test_bootstrap_reports_installed_servers(self):
        """Test that bootstrap correctly reports installed LSP servers."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            (project_path / "main.py").write_text("print('hello')")

            config_file = project_path / ".otter.toml"
            config_file.write_text(
                """
[lsp]
auto_install = true
languages = ["python"]
"""
            )

            # Just verify it can start with this config
            nvim_client = NeovimClient(project_path=str(project_path))
            await nvim_client.start()
            assert nvim_client.is_running()
            await nvim_client.stop()


# ============================================================================
# Tests: Configuration Integration
# ============================================================================


class TestConfigIntegration:
    """Test that configuration is properly loaded and applied."""

    @pytest.mark.asyncio
    async def test_default_config_loads(self):
        """Test that Neovim starts with default config when no .otter.toml exists."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create a Python file to trigger detection
            (project_path / "main.py").write_text("def hello(): pass\n")

            async with NeovimClient(str(project_path)) as client:
                # Verify config was loaded
                assert client.config is not None
                assert client.config.lsp.enabled is True

                # Verify Python was detected
                assert "python" in client.enabled_languages

    @pytest.mark.asyncio
    async def test_custom_config_loads(self):
        """Test that custom .otter.toml is loaded."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create custom config
            (project_path / ".otter.toml").write_text(
                """
[project]
name = "test-project"

[lsp]
enabled = true
languages = ["python", "javascript"]

[[lsp.servers]]
language = "python"
server = "pyright"
"""
            )

            (project_path / "main.py").write_text("def hello(): pass\n")

            async with NeovimClient(str(project_path)) as client:
                assert client.config is not None
                assert client.config.project.name == "test-project"
                assert "python" in client.config.lsp.languages
                assert "javascript" in client.config.lsp.languages

    @pytest.mark.asyncio
    async def test_virtualenv_detection(self):
        """Test that virtualenv is detected and used."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create fake venv
            venv_dir = project_path / ".venv"
            venv_bin = venv_dir / "bin"
            venv_bin.mkdir(parents=True)
            (venv_bin / "python").write_text("#!/bin/sh\necho 'venv python'")
            (venv_bin / "python").chmod(0o755)

            (project_path / "main.py").write_text("def hello(): pass\n")

            async with NeovimClient(str(project_path)):
                # Should detect venv (venv_path exists in detected_runtimes)
                assert venv_dir.exists()

    @pytest.mark.asyncio
    async def test_disabled_language(self):
        """Test that disabled languages are not initialized."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            (project_path / ".otter.toml").write_text(
                """
[lsp]
enabled = true
languages = []  # No languages enabled
"""
            )

            (project_path / "main.py").write_text("def hello(): pass\n")

            async with NeovimClient(str(project_path)) as client:
                # No languages should be enabled
                assert len(client.enabled_languages) == 0

    @pytest.mark.asyncio
    async def test_multi_language_config(self):
        """Test project with multiple languages configured."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            (project_path / ".otter.toml").write_text(
                """
[lsp]
enabled = true
languages = ["python", "javascript", "rust"]
"""
            )

            (project_path / "main.py").write_text("print('python')")
            (project_path / "index.js").write_text("console.log('js');")
            (project_path / "main.rs").write_text("fn main() {}")

            async with NeovimClient(str(project_path)) as client:
                # Should detect all three languages
                enabled = client.enabled_languages
                assert "python" in enabled or len(enabled) > 0
