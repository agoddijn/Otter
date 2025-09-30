"""Integration tests for find_definition feature."""

import tempfile
from pathlib import Path

import pytest

from src.cli_ide.neovim.client import NeovimClient
from src.cli_ide.services.navigation import NavigationService


@pytest.mark.asyncio
class TestFindDefinitionIntegration:
    """Integration tests for find_definition with real Neovim instance."""

    @pytest.fixture
    async def temp_project(self):
        """Create a temporary project with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create a test module with various symbols
            test_file = project_path / "example.py"
            test_file.write_text('''"""Example module for testing."""

class UserModel:
    """User data model."""
    
    def __init__(self, name: str, email: str):
        """Initialize user."""
        self.name = name
        self.email = email
    
    def save(self) -> bool:
        """Save user to database."""
        return True

def process_user(user: UserModel) -> str:
    """Process a user and return status."""
    return f"Processed {user.name}"

# Module-level constant
DEFAULT_TIMEOUT = 30
''')

            # Create a file that uses the module
            usage_file = project_path / "main.py"
            usage_file.write_text("""from example import UserModel, process_user

def main():
    user = UserModel("Alice", "alice@example.com")
    user.save()
    result = process_user(user)
    print(result)
""")

            yield project_path

    @pytest.fixture
    async def navigation_service(self, temp_project):
        """Create NavigationService with a real Neovim instance."""
        nvim_client = NeovimClient(project_path=str(temp_project))
        service = NavigationService(
            nvim_client=nvim_client, project_path=str(temp_project)
        )

        await nvim_client.start()
        yield service
        await nvim_client.stop()

    async def test_find_class_definition(self, navigation_service, temp_project):
        """Test finding a class definition."""
        # Wait for LSP to analyze the files
        import asyncio

        await asyncio.sleep(2)

        # Find definition of UserModel when cursor is on it in main.py
        # "from example import UserModel, process_user"
        #                     ^-- column 24 (U in UserModel)
        result = await navigation_service.find_definition(
            symbol="UserModel",
            file=str(temp_project / "main.py"),
            line=1,  # Line with "from example import UserModel"
        )

        assert result.file == "example.py"
        assert result.symbol_name == "UserModel"
        assert result.symbol_type == "class"
        assert result.line == 3  # Class defined on line 3
        assert result.docstring == "User data model."
        assert len(result.context_lines) > 0
        assert "class UserModel:" in "\n".join(result.context_lines)

    async def test_find_function_definition(self, navigation_service, temp_project):
        """Test finding a function definition."""
        import asyncio

        await asyncio.sleep(2)

        # "from example import UserModel, process_user"
        #                                 ^-- column 36 (p in process_user)
        result = await navigation_service.find_definition(
            symbol="process_user",
            file=str(temp_project / "main.py"),
            line=1,  # Line with import
        )

        assert result.file == "example.py"
        assert result.symbol_name == "process_user"
        assert result.symbol_type == "function"
        assert result.line == 15  # Function defined on line 15
        assert result.signature is not None
        assert "def process_user" in result.signature
        assert result.docstring == "Process a user and return status."

    async def test_find_method_definition(self, navigation_service, temp_project):
        """Test finding a method definition."""
        import asyncio

        await asyncio.sleep(2)

        # Find definition of save() method when called
        # "    user.save()"
        #           ^-- column 9 (s in save)
        result = await navigation_service.find_definition(
            symbol="save",
            file=str(temp_project / "main.py"),
            line=5,  # Line with "user.save()"
        )

        assert result.file == "example.py"
        assert result.symbol_name == "save"
        assert result.symbol_type == "method"
        assert result.line == 11  # Method defined on line 11
        assert result.signature is not None
        assert "def save" in result.signature
        assert "Save user to database" in (result.docstring or "")

    async def test_find_definition_in_same_file(self, navigation_service, temp_project):
        """Test finding definition within the same file."""
        import asyncio

        await asyncio.sleep(2)

        # Find UserModel definition from within example.py
        # "def process_user(user: UserModel) -> str:"
        #                         ^-- column 24 (U in UserModel)
        result = await navigation_service.find_definition(
            symbol="UserModel",
            file=str(temp_project / "example.py"),
            line=15,  # Line in process_user function
        )

        assert result.file == "example.py"
        assert result.symbol_name == "UserModel"
        assert result.symbol_type == "class"

    async def test_definition_not_found(self, navigation_service, temp_project):
        """Test error handling when definition is not found."""
        with pytest.raises(RuntimeError, match="Definition not found"):
            await navigation_service.find_definition(
                symbol="NonExistent",
                file=str(temp_project / "main.py"),
                line=10,  # Empty line or invalid position
            )

    async def test_definition_without_context_raises_error(self, navigation_service):
        """Test that finding definition without file/line context raises error."""
        with pytest.raises(
            NotImplementedError, match="Symbol search without file context"
        ):
            await navigation_service.find_definition(symbol="UserModel")

    async def test_definition_provides_context_lines(
        self, navigation_service, temp_project
    ):
        """Test that definition includes surrounding context lines."""
        import asyncio

        await asyncio.sleep(2)

        result = await navigation_service.find_definition(
            symbol="UserModel",
            file=str(temp_project / "main.py"),
            line=1,
        )

        assert len(result.context_lines) > 3  # Should have several context lines
        # Context should include the class definition and some surrounding code
        context_text = "\n".join(result.context_lines)
        assert "class UserModel:" in context_text
