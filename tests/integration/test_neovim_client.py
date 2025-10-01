"""Integration tests for Neovim client.

Note: These are integration tests because they require a running Neovim instance.
They are currently skipped in unit tests due to pynvim async event loop conflicts.
Run them separately with: pytest tests/integration/ -v
"""

import pytest
from pathlib import Path
import asyncio

from otter.neovim.client import NeovimClient


# Mark as integration tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not Path("/usr/local/bin/nvim").exists() and not Path("/opt/homebrew/bin/nvim").exists() and not Path("/usr/bin/nvim").exists(),
        reason="Neovim not installed"
    )
]


class TestNeovimClient:
    """Tests for NeovimClient."""
    
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
            # Set a timeout for the entire test
            await asyncio.wait_for(client.start(), timeout=10.0)
            assert client.is_running()
            assert client.nvim is not None
        finally:
            await client.stop()
        
        assert not client.is_running()
        assert client.nvim is None
    
    @pytest.mark.asyncio
    async def test_context_manager(self, temp_project_dir: Path):
        """Test using client as async context manager."""
        # Use timeout to prevent hanging
        async def _test():
            async with NeovimClient(project_path=str(temp_project_dir)) as client:
                assert client.is_running()
            # Should be stopped after exiting context
            assert not client.is_running()
        
        await asyncio.wait_for(_test(), timeout=15.0)
    
    @pytest.mark.asyncio
    async def test_open_file(self, temp_project_dir: Path):
        """Test opening a file in Neovim."""
        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            buf_num = await client.open_file("README.md")
            
            assert isinstance(buf_num, int)
            assert buf_num > 0
    
    @pytest.mark.asyncio
    async def test_open_file_twice(self, temp_project_dir: Path):
        """Test that opening the same file twice returns the same buffer."""
        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            buf_num1 = await client.open_file("README.md")
            buf_num2 = await client.open_file("README.md")
            
            assert buf_num1 == buf_num2
    
    @pytest.mark.asyncio
    async def test_read_buffer(self, temp_project_dir: Path):
        """Test reading buffer contents."""
        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            lines = await client.read_buffer("README.md")
            
            assert isinstance(lines, list)
            assert len(lines) > 0
            assert "# Test Project" in lines[0]
    
    @pytest.mark.asyncio
    async def test_read_buffer_with_range(self, temp_project_dir: Path):
        """Test reading specific line range from buffer."""
        # Create a multi-line file
        test_file = temp_project_dir / "multi.txt"
        test_file.write_text("line1\nline2\nline3\nline4\nline5\n")
        
        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            lines = await client.read_buffer("multi.txt", line_range=(2, 4))
            
            assert len(lines) == 3  # lines 2-4 inclusive
            assert "line2" in lines[0]
            assert "line4" in lines[2]
    
    @pytest.mark.asyncio
    async def test_execute_lua(self, temp_project_dir: Path):
        """Test executing Lua code."""
        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            result = await client.execute_lua("return 2 + 2")
            
            assert result == 4
    
    @pytest.mark.asyncio
    async def test_execute_lua_with_vim_api(self, temp_project_dir: Path):
        """Test executing Lua code that uses Vim API."""
        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            result = await client.execute_lua("return vim.fn.getcwd()")
            
            # Should return the project path
            assert str(temp_project_dir) in result
    
    @pytest.mark.asyncio
    async def test_get_diagnostics_empty(self, temp_project_dir: Path):
        """Test getting diagnostics for a file (should be empty for simple file)."""
        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            diagnostics = await client.get_diagnostics("README.md")
            
            # README.md should have no diagnostics
            assert isinstance(diagnostics, list)
    
    @pytest.mark.asyncio
    async def test_file_not_found_error(self, temp_project_dir: Path):
        """Test error when trying to open non-existent file."""
        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            with pytest.raises(RuntimeError, match="Failed to open file"):
                await client.open_file("nonexistent.txt")
    
    @pytest.mark.asyncio
    async def test_multiple_files(self, temp_project_dir: Path):
        """Test opening multiple files."""
        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            buf1 = await client.open_file("README.md")
            buf2 = await client.open_file("src/main.py")
            
            assert buf1 != buf2
            assert buf1 > 0
            assert buf2 > 0
