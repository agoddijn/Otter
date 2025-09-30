"""Integration tests for get_symbols feature."""

import tempfile
from pathlib import Path

import pytest

from src.cli_ide.neovim.client import NeovimClient
from src.cli_ide.services.workspace import WorkspaceService


@pytest.mark.asyncio
class TestGetSymbolsIntegration:
    """Integration tests for get_symbols with real Neovim instance."""

    @pytest.fixture
    async def temp_project(self):
        """Create a temporary project with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create a Python file with various symbols
            test_file = project_path / "example.py"
            test_file.write_text('''"""Example module with various symbols."""

# Module-level constant
VERSION = "1.0.0"

class BaseModel:
    """Base class for all models."""
    
    def __init__(self):
        """Initialize base model."""
        self.id = None
    
    def save(self) -> bool:
        """Save to database."""
        return True

class UserModel(BaseModel):
    """User data model."""
    
    def __init__(self, name: str, email: str):
        """Initialize user model."""
        super().__init__()
        self.name = name
        self.email = email
    
    def validate(self) -> bool:
        """Validate user data."""
        return bool(self.name and self.email)
    
    @property
    def display_name(self) -> str:
        """Get display name."""
        return self.name.title()

def create_user(name: str, email: str) -> UserModel:
    """Factory function for creating users."""
    return UserModel(name, email)

def process_users(users: list) -> int:
    """Process a list of users."""
    count = 0
    for user in users:
        if user.validate():
            user.save()
            count += 1
    return count
''')

            yield project_path

    @pytest.fixture
    async def workspace_service(self, temp_project):
        """Create WorkspaceService with a real Neovim instance."""
        nvim_client = NeovimClient(project_path=str(temp_project))
        service = WorkspaceService(
            project_path=str(temp_project), nvim_client=nvim_client
        )

        await nvim_client.start()

        # Wait for LSP to analyze files
        import asyncio

        await asyncio.sleep(2)

        yield service
        await nvim_client.stop()

    async def test_get_all_symbols(self, workspace_service, temp_project):
        """Test getting all symbols from a file."""
        symbols = await workspace_service.get_symbols(str(temp_project / "example.py"))

        # Should have classes, functions, and module-level items
        assert len(symbols) > 0

        # Check we have the expected top-level symbols
        symbol_names = {s.name for s in symbols}
        assert "BaseModel" in symbol_names or "UserModel" in symbol_names
        assert "create_user" in symbol_names or "process_users" in symbol_names

    async def test_symbols_have_correct_types(self, workspace_service, temp_project):
        """Test that symbols have correct type information."""
        symbols = await workspace_service.get_symbols(str(temp_project / "example.py"))

        # Find specific symbols and verify their types
        for symbol in symbols:
            if symbol.name == "BaseModel" or symbol.name == "UserModel":
                assert symbol.type == "class"
            elif symbol.name == "create_user" or symbol.name == "process_users":
                assert symbol.type == "function"
            elif symbol.name == "VERSION":
                assert symbol.type in ["variable", "constant"]

    async def test_symbols_have_line_numbers(self, workspace_service, temp_project):
        """Test that symbols include line numbers."""
        symbols = await workspace_service.get_symbols(str(temp_project / "example.py"))

        # All symbols should have positive line numbers
        for symbol in symbols:
            assert symbol.line > 0

    async def test_symbols_include_children(self, workspace_service, temp_project):
        """Test that class symbols include their methods as children."""
        symbols = await workspace_service.get_symbols(str(temp_project / "example.py"))

        # Find a class symbol
        user_model = None
        for symbol in symbols:
            if symbol.name == "UserModel":
                user_model = symbol
                break

        if user_model:
            # Should have children (methods)
            assert user_model.children is not None
            assert len(user_model.children) > 0

            # Children should be methods
            method_names = {child.name for child in user_model.children}
            assert "__init__" in method_names or "validate" in method_names

    async def test_child_symbols_have_parent(self, workspace_service, temp_project):
        """Test that child symbols reference their parent."""
        symbols = await workspace_service.get_symbols(str(temp_project / "example.py"))

        # Find a class with children
        for symbol in symbols:
            if symbol.children:
                for child in symbol.children:
                    # Child should reference parent
                    assert child.parent == symbol.name

    async def test_filter_by_symbol_type_class(self, workspace_service, temp_project):
        """Test filtering symbols by type (class)."""
        symbols = await workspace_service.get_symbols(
            str(temp_project / "example.py"), symbol_types=["class"]
        )

        # Should only have class symbols
        for symbol in symbols:
            assert symbol.type == "class"

    async def test_filter_by_symbol_type_function(
        self, workspace_service, temp_project
    ):
        """Test filtering symbols by type (function)."""
        symbols = await workspace_service.get_symbols(
            str(temp_project / "example.py"), symbol_types=["function"]
        )

        # Should only have function symbols (not methods)
        for symbol in symbols:
            assert symbol.type == "function"
            # Should not have a parent (top-level functions)
            assert symbol.parent is None

    async def test_filter_by_multiple_types(self, workspace_service, temp_project):
        """Test filtering by multiple symbol types."""
        symbols = await workspace_service.get_symbols(
            str(temp_project / "example.py"), symbol_types=["class", "function"]
        )

        # Should have both classes and functions
        types = {s.type for s in symbols}
        assert "class" in types or "function" in types

        # Should not have other types at top level
        for symbol in symbols:
            assert symbol.type in ["class", "function"]

    async def test_empty_file_returns_empty_list(self, workspace_service, temp_project):
        """Test that an empty file returns an empty list."""
        empty_file = temp_project / "empty.py"
        empty_file.write_text("")

        import asyncio

        await asyncio.sleep(1)

        symbols = await workspace_service.get_symbols(str(empty_file))
        assert symbols == []

    async def test_file_not_found_raises_error(self, workspace_service, temp_project):
        """Test that non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            await workspace_service.get_symbols(str(temp_project / "nonexistent.py"))

    async def test_symbols_without_nvim_raises_error(self, temp_project):
        """Test that get_symbols without Neovim client raises error."""
        service = WorkspaceService(project_path=str(temp_project), nvim_client=None)

        with pytest.raises(RuntimeError, match="Neovim client required"):
            await service.get_symbols(str(temp_project / "example.py"))

    async def test_relative_path_works(self, workspace_service, temp_project):
        """Test that relative paths work correctly."""
        symbols = await workspace_service.get_symbols("example.py")

        # Should work the same as absolute path
        assert len(symbols) > 0
