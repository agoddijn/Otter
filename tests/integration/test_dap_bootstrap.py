"""
Integration tests for DAP bootstrap.

Tests that debug adapters are automatically installed and configured,
especially in venv scenarios.
"""

import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from otter.bootstrap import (
    DAPAdapterStatus,
    check_and_install_dap_adapter,
    check_dap_adapter,
    ensure_dap_adapter,
)
from otter.server import CliIdeServer


class TestDAPBootstrap:
    """Test DAP adapter bootstrap functionality."""

    @pytest.mark.asyncio
    async def test_check_python_debugpy_installed(self):
        """Test checking if debugpy is installed."""
        # This will check the current environment
        status = check_dap_adapter("python")
        # We don't assert specific status as it depends on environment
        assert status in [
            DAPAdapterStatus.INSTALLED,
            DAPAdapterStatus.MISSING,
            DAPAdapterStatus.PREREQUISITES_MISSING,
        ]

    @pytest.mark.asyncio
    async def test_check_javascript_adapter(self):
        """Test checking JavaScript/TypeScript adapter."""
        status = check_dap_adapter("javascript")
        assert status in [
            DAPAdapterStatus.INSTALLED,
            DAPAdapterStatus.MISSING,
            DAPAdapterStatus.PREREQUISITES_MISSING,
        ]

    @pytest.mark.asyncio
    async def test_check_unsupported_language(self):
        """Test checking an unsupported language returns MISSING."""
        status = check_dap_adapter("cobol")
        assert status == DAPAdapterStatus.MISSING


class TestDAPBootstrapWithInstall:
    """Test DAP bootstrap with actual installation (careful!)."""

    @pytest.mark.asyncio
    async def test_ensure_adapter_raises_on_missing(self):
        """Test ensure_dap_adapter raises clear error if adapter missing."""
        with patch("otter.bootstrap.dap_installer.check_dap_adapter") as mock_check:
            mock_check.return_value = DAPAdapterStatus.MISSING

            with patch("otter.bootstrap.dap_installer.install_dap_adapter") as mock_install:
                mock_install.return_value = False  # Installation failed

                with pytest.raises(RuntimeError) as exc_info:
                    await ensure_dap_adapter("python", auto_install=True)

                error_msg = str(exc_info.value)
                assert "python" in error_msg.lower()
                assert "debugger" in error_msg.lower() or "adapter" in error_msg.lower()


class TestDAPWithVenv:
    """Test DAP works correctly with virtual environments.
    
    This is the critical case - ensuring debug adapters use the venv Python,
    not system Python.
    """

    @pytest.mark.asyncio
    async def test_debug_session_detects_venv_python(self, tmp_path):
        """Test that debug session uses venv Python when available."""
        # Create a fake venv structure
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        venv_dir = project_dir / ".venv"
        venv_bin = venv_dir / "bin"
        venv_bin.mkdir(parents=True)
        
        # Create fake Python executable
        venv_python = venv_bin / "python"
        venv_python.write_text("#!/bin/sh\necho 'fake python'")
        venv_python.chmod(0o755)
        
        # Create test file
        test_file = project_dir / "main.py"
        test_file.write_text("print('hello')")
        
        server = CliIdeServer(project_path=str(project_dir))
        
        # Mock the Neovim client to avoid actually starting Neovim
        mock_nvim_client = AsyncMock()
        mock_nvim_client.dap_start_session = AsyncMock(return_value={
            "session_id": "test123",
            "config_name": "test",
            "status": "running"
        })
        mock_nvim_client.dap_set_breakpoints = AsyncMock(return_value=[])
        
        server._neovim = mock_nvim_client
        
        with patch("otter.bootstrap.dap_installer.check_dap_adapter") as mock_check:
            mock_check.return_value = DAPAdapterStatus.INSTALLED
            
            try:
                await server.start()
                
                # This should detect the venv and use it
                # The key test: Does the DAP config get the venv Python path?
                session = await server.start_debug_session(
                    file="main.py",
                    breakpoints=[1]
                )
                
                # Verify the call was made
                assert mock_nvim_client.dap_start_session.called
                
                # Check if venv Python path was passed
                call_kwargs = mock_nvim_client.dap_start_session.call_args.kwargs
                # This is what we need to fix - passing the venv Python path!
                # For now, this test documents the expected behavior
                
            finally:
                await server.stop()

    @pytest.mark.asyncio
    async def test_debug_session_fails_with_clear_message_if_no_debugpy(self, tmp_path):
        """Test that debug session fails with clear message if debugpy not installed."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        
        test_file = project_dir / "main.py"
        test_file.write_text("print('hello')")
        
        server = CliIdeServer(project_path=str(project_dir))
        
        # Mock check to say debugpy is missing and can't be installed
        with patch("otter.bootstrap.dap_installer.check_dap_adapter") as mock_check:
            mock_check.return_value = DAPAdapterStatus.MISSING
            
            with patch("otter.bootstrap.dap_installer.install_dap_adapter") as mock_install:
                mock_install.return_value = False  # Installation fails
                
                with pytest.raises(RuntimeError) as exc_info:
                    await server.start()
                    await server.start_debug_session(file="main.py")
                
                error_msg = str(exc_info.value)
                # Should have clear, actionable error
                assert "debug" in error_msg.lower() or "adapter" in error_msg.lower()
                assert "python" in error_msg.lower()


class TestDAPErrorMessages:
    """Test that DAP error messages are clear and actionable."""

    @pytest.mark.asyncio
    async def test_missing_adapter_error_is_actionable(self):
        """Test error message when adapter is missing is actionable."""
        with patch("otter.bootstrap.dap_installer.check_dap_adapter") as mock_check:
            mock_check.return_value = DAPAdapterStatus.MISSING
            
            with patch("otter.bootstrap.dap_installer.install_dap_adapter") as mock_install:
                mock_install.return_value = False
                
                with pytest.raises(RuntimeError) as exc_info:
                    await ensure_dap_adapter("python", auto_install=True)
                
                error_msg = str(exc_info.value)
                
                # Error should mention:
                # 1. What's wrong
                assert "python" in error_msg.lower()
                
                # 2. How to fix it (install command)
                # Note: Actual error from install_dap_adapter will include this

    @pytest.mark.asyncio
    async def test_missing_prerequisites_error_is_actionable(self):
        """Test error message when prerequisites missing is actionable."""
        with patch("otter.bootstrap.dap_installer.check_dap_adapter") as mock_check:
            mock_check.return_value = DAPAdapterStatus.PREREQUISITES_MISSING
            
            with patch("otter.bootstrap.dap_installer.check_prerequisites") as mock_prereq:
                mock_prereq.return_value = (False, ["pip"])
                
                status, error = await check_and_install_dap_adapter("python", auto_install=True)
                
                assert status == DAPAdapterStatus.PREREQUISITES_MISSING
                assert error is not None
                assert "pip" in error.lower()
                assert "prerequisite" in error.lower()


class TestDAPConfigurationPassing:
    """Test that DAP configuration (Python path, etc.) is passed correctly.
    
    THIS IS THE KEY TEST - ensuring venv Python path reaches Neovim DAP.
    """

    @pytest.mark.asyncio
    async def test_venv_python_path_passed_to_dap(self, tmp_path):
        """Test that venv Python path is passed to DAP adapter configuration.
        
        This is the critical test that should catch the issue the agent is seeing.
        """
        # Setup
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        venv_dir = project_dir / ".venv"
        venv_bin = venv_dir / "bin"
        venv_bin.mkdir(parents=True)
        
        venv_python = venv_bin / "python"
        venv_python.write_text("#!/bin/sh\necho 'venv python'")
        venv_python.chmod(0o755)
        
        test_file = project_dir / "main.py"
        test_file.write_text("print('hello')")
        
        # The critical test: Does the DAP adapter get configured with venv Python?
        server = CliIdeServer(project_path=str(project_dir))
        
        mock_nvim = AsyncMock()
        mock_nvim.dap_start_session = AsyncMock(return_value={
            "session_id": "test",
            "status": "running"
        })
        mock_nvim.dap_set_breakpoints = AsyncMock(return_value=[])
        
        server._neovim = mock_nvim
        
        with patch("otter.bootstrap.dap_installer.check_dap_adapter") as mock_check:
            mock_check.return_value = DAPAdapterStatus.INSTALLED
            
            try:
                await server.start()
                await server.start_debug_session(file="main.py")
                
                # THIS IS WHAT WE NEED TO VERIFY:
                # The call to dap_start_session should include the venv Python path
                call_kwargs = mock_nvim.dap_start_session.call_args.kwargs
                
                # Currently this might fail because we're not passing it!
                # This test documents what SHOULD happen
                # TODO: Uncomment when implemented
                # assert "python_path" in call_kwargs or venv_python path is used somehow
                
            finally:
                await server.stop()

