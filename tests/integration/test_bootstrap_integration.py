"""Integration tests for LSP bootstrapping."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from otter.bootstrap import LSPServerStatus
from otter.neovim.client import NeovimClient


@pytest.mark.asyncio
class TestBootstrapIntegration:
    """Test bootstrap integration with NeovimClient."""
    
    async def test_bootstrap_runs_on_start_with_auto_install(self):
        """Test that bootstrap runs when starting Neovim with auto_install=true."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            
            # Create a Python file to trigger language detection
            (project_path / "main.py").write_text("print('hello')")
            
            # Create config with auto_install enabled
            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[lsp]
auto_install = true
languages = ["python"]
""")
            
            # Mock the bootstrap function to avoid actual installation
            with patch("otter.neovim.client.check_and_install_lsp_servers", new_callable=AsyncMock) as mock_bootstrap:
                mock_bootstrap.return_value = {"python": LSPServerStatus.INSTALLED}
                
                # Mock Neovim process to avoid starting actual Neovim
                with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock):
                    client = NeovimClient(str(project_path))
                    
                    # Verify config is loaded and languages detected
                    assert client.config.lsp.auto_install is True
                    assert "python" in client.enabled_languages
                    
                    # Start should trigger bootstrap
                    try:
                        await client.start()
                    except Exception:
                        # Ignore Neovim connection errors, we're just testing bootstrap
                        pass
                    
                    # Verify bootstrap was called
                    mock_bootstrap.assert_called_once()
                    call_args = mock_bootstrap.call_args
                    
                    # Check it was called with correct languages
                    assert "python" in call_args[0][0]  # First positional arg: languages
                    # Check auto_install was passed
                    assert call_args[1]["auto_install"] is True
    
    async def test_bootstrap_skipped_when_disabled(self):
        """Test that bootstrap is skipped when auto_install=false."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            
            # Create config with auto_install disabled
            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[lsp]
auto_install = false
languages = ["python"]
""")
            
            # Mock the bootstrap function
            with patch("otter.neovim.client.check_and_install_lsp_servers", new_callable=AsyncMock) as mock_bootstrap:
                # Mock Neovim process
                with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock):
                    client = NeovimClient(str(project_path))
                    
                    # Verify config is loaded
                    assert client.config.lsp.auto_install is False
                    
                    # Start should NOT trigger bootstrap
                    try:
                        await client.start()
                    except Exception:
                        pass
                    
                    # Verify bootstrap was NOT called (because auto_install=false)
                    mock_bootstrap.assert_not_called()
    
    async def test_bootstrap_skipped_when_lsp_disabled(self):
        """Test that bootstrap is skipped when LSP is disabled."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            
            # Create config with LSP disabled
            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[lsp]
enabled = false
""")
            
            # Mock the bootstrap function
            with patch("otter.neovim.client.check_and_install_lsp_servers", new_callable=AsyncMock) as mock_bootstrap:
                # Mock Neovim process
                with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock):
                    client = NeovimClient(str(project_path))
                    
                    # Start should NOT trigger bootstrap
                    try:
                        await client.start()
                    except Exception:
                        pass
                    
                    # Verify bootstrap was NOT called
                    mock_bootstrap.assert_not_called()
    
    async def test_bootstrap_skipped_when_no_languages(self):
        """Test that bootstrap is skipped when no languages detected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            
            # Don't create any language files
            # Config has auto_install=true but no languages
            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[lsp]
auto_install = true
""")
            
            # Mock the bootstrap function
            with patch("otter.neovim.client.check_and_install_lsp_servers", new_callable=AsyncMock) as mock_bootstrap:
                # Mock Neovim process
                with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock):
                    client = NeovimClient(str(project_path))
                    
                    # Verify no languages detected
                    assert len(client.enabled_languages) == 0
                    
                    # Start should NOT trigger bootstrap (no languages)
                    try:
                        await client.start()
                    except Exception:
                        pass
                    
                    # Verify bootstrap was NOT called
                    mock_bootstrap.assert_not_called()


@pytest.mark.asyncio
class TestBootstrapBehavior:
    """Test actual bootstrap behavior (without Neovim)."""
    
    async def test_bootstrap_reports_installed_servers(self):
        """Test that bootstrap correctly reports already-installed servers."""
        from otter.bootstrap import check_and_install_lsp_servers
        
        # Mock is_command_available to simulate installed servers
        with patch("otter.bootstrap.lsp_installer.is_command_available") as mock_available:
            mock_available.return_value = True
            
            results = await check_and_install_lsp_servers(
                ["python"],
                {},
                auto_install=False  # Don't try to install
            )
            
            assert "python" in results
            assert results["python"] == LSPServerStatus.INSTALLED
    
    async def test_bootstrap_detects_missing_servers(self):
        """Test that bootstrap correctly detects missing servers."""
        from otter.bootstrap import check_and_install_lsp_servers
        
        # Mock is_command_available to simulate missing servers
        with patch("otter.bootstrap.lsp_installer.is_command_available") as mock_available:
            mock_available.return_value = False
            
            results = await check_and_install_lsp_servers(
                ["python"],
                {},
                auto_install=False  # Don't try to install
            )
            
            assert "python" in results
            assert results["python"] == LSPServerStatus.MISSING

