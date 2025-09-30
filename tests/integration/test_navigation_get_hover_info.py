"""Integration tests for get_hover_info feature."""

import tempfile
from pathlib import Path

import pytest

from src.cli_ide.neovim.client import NeovimClient
from src.cli_ide.services.navigation import NavigationService


@pytest.mark.asyncio
class TestGetHoverInfoIntegration:
    """Integration tests for get_hover_info with real Neovim instance."""

    @pytest.fixture
    async def temp_project(self):
        """Create a temporary project with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create a simple Python file for hover testing
            example_file = project_path / "example.py"
            example_file.write_text('''
class MyClass:
    """A simple class."""
    
    def my_method(self, x: int) -> str:
        """A simple method."""
        return str(x)

def my_function(a: str, b: int) -> bool:
    """A simple function."""
    return len(a) > b

COUNT = 42
''')

            yield project_path

    @pytest.fixture
    async def navigation_service(self, temp_project):
        """Create NavigationService with a real Neovim instance."""
        nvim_client = NeovimClient(project_path=str(temp_project))
        service = NavigationService(
            project_path=str(temp_project), nvim_client=nvim_client
        )

        await nvim_client.start()

        # Wait for LSP to analyze files
        import asyncio

        await asyncio.sleep(2)

        yield service
        await nvim_client.stop()

    async def test_hover_on_class(self, navigation_service, temp_project):
        """Test hover information for a class."""
        example_file = str(temp_project / "example.py")

        # Hover over "MyClass" class name (line 2, col 6 is on 'MyClass')
        hover = await navigation_service.get_hover_info(example_file, 2, 6)

        assert hover.symbol == "MyClass"
        assert hover.type is not None
        assert "class" in hover.type.lower() or "MyClass" in hover.type

    async def test_hover_on_method(self, navigation_service, temp_project):
        """Test hover information for a method."""
        example_file = str(temp_project / "example.py")

        # Hover over "my_method" method (line 5, col 8 is on 'my_method')
        hover = await navigation_service.get_hover_info(example_file, 5, 8)

        assert hover.symbol == "my_method"
        assert hover.type is not None
        # Should indicate it's a method with signature
        assert (
            "method" in hover.type.lower()
            or "def" in hover.type
            or "my_method" in hover.type
        )

    async def test_hover_includes_docstring(self, navigation_service, temp_project):
        """Test that hover includes docstring for documented symbols."""
        example_file = str(temp_project / "example.py")

        # Hover over "MyClass" which has a docstring
        hover = await navigation_service.get_hover_info(example_file, 2, 6)

        # Should have docstring
        if hover.docstring:
            assert len(hover.docstring) > 0
            assert "simple" in hover.docstring.lower()

    async def test_hover_no_info_raises_error(self, navigation_service, temp_project):
        """Test that hovering on empty space raises an error."""
        example_file = str(temp_project / "example.py")

        # Hover on an empty line
        with pytest.raises(RuntimeError, match="No hover information found"):
            await navigation_service.get_hover_info(example_file, 1, 0)

    async def test_hover_without_nvim_raises_error(self, temp_project):
        """Test that get_hover_info without Neovim client raises error."""
        service = NavigationService(project_path=str(temp_project), nvim_client=None)

        with pytest.raises(RuntimeError, match="Neovim client required"):
            await service.get_hover_info(str(temp_project / "example.py"), 2, 6)
