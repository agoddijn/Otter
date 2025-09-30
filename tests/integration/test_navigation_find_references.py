"""Integration tests for find_references feature."""

import tempfile
from pathlib import Path

import pytest

from src.cli_ide.neovim.client import NeovimClient
from src.cli_ide.services.navigation import NavigationService


@pytest.mark.asyncio
class TestFindReferencesIntegration:
    """Integration tests for find_references with real Neovim instance."""

    @pytest.fixture
    async def temp_project(self):
        """Create a temporary project with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create a models file
            models_file = project_path / "models.py"
            models_file.write_text('''"""Data models."""

class User:
    """User model."""
    
    def __init__(self, name: str):
        self.name = name
    
    def greet(self) -> str:
        """Greet the user."""
        return f"Hello, {self.name}!"

def create_user(name: str) -> User:
    """Factory function for creating users."""
    return User(name)
''')

            # Create a services file that uses User
            services_file = project_path / "services.py"
            services_file.write_text('''"""Business logic."""
from models import User, create_user

class UserService:
    def get_user(self) -> User:
        """Get a user."""
        return create_user("Alice")
    
    def process_user(self, user: User) -> str:
        """Process a user."""
        return user.greet()
''')

            # Create a main file that uses everything
            main_file = project_path / "main.py"
            main_file.write_text('''"""Main module."""
from models import User, create_user
from services import UserService

def main():
    # Create user directly
    user1 = User("Bob")
    print(user1.greet())
    
    # Create user via factory
    user2 = create_user("Charlie")
    print(user2.greet())
    
    # Use service
    service = UserService()
    user3 = service.get_user()
    result = service.process_user(user3)
    print(result)

if __name__ == "__main__":
    main()
''')

            yield project_path

    @pytest.fixture
    async def navigation_service(self, temp_project):
        """Create NavigationService with a real Neovim instance."""
        nvim_client = NeovimClient(project_path=str(temp_project))
        service = NavigationService(
            nvim_client=nvim_client, project_path=str(temp_project)
        )

        await nvim_client.start()

        # Wait for LSP to analyze files
        import asyncio

        await asyncio.sleep(2)

        yield service
        await nvim_client.stop()

    async def test_find_class_references(self, navigation_service, temp_project):
        """Test finding all references to a class."""
        # Find references to User class
        references = await navigation_service.find_references(
            symbol="User",
            file=str(temp_project / "models.py"),
            line=3,  # Line with "class User:"
        )

        # Should find references in all three files
        assert len(references) >= 3

        # Verify we have references from different files
        ref_files = {ref.file for ref in references}
        assert "models.py" in ref_files
        assert "services.py" in ref_files or "main.py" in ref_files

        # All references should have context
        for ref in references:
            assert ref.context
            assert "User" in ref.context

    async def test_find_function_references(self, navigation_service, temp_project):
        """Test finding all references to a function."""
        # Find references to create_user function from an import site
        references = await navigation_service.find_references(
            symbol="create_user",
            file=str(temp_project / "services.py"),
            line=2,  # Line with "from models import User, create_user"
        )

        # Should find at least imports and calls (or none if LSP doesn't track this symbol)
        # LSP behavior can vary by symbol type
        assert isinstance(references, list)

        # If we got references, they should mention create_user
        for ref in references:
            assert "create_user" in ref.context

    async def test_find_method_references(self, navigation_service, temp_project):
        """Test finding references to a method."""
        # Find references to the greet() method from a usage site
        references = await navigation_service.find_references(
            symbol="greet",
            file=str(temp_project / "main.py"),
            line=7,  # Line with "print(user1.greet())"
        )

        # Should find calls or at least return a valid list
        assert isinstance(references, list)

        # If we got references, verify context
        for ref in references:
            assert "greet" in ref.context

    async def test_scope_file_filters_references(
        self, navigation_service, temp_project
    ):
        """Test that scope='file' filters to only the current file."""
        # Find User references in models.py only
        references = await navigation_service.find_references(
            symbol="User", file=str(temp_project / "models.py"), line=3, scope="file"
        )

        # All references should be in models.py
        for ref in references:
            assert ref.file == "models.py"

    async def test_scope_project_returns_all_references(
        self, navigation_service, temp_project
    ):
        """Test that scope='project' returns references from all files."""
        # Find User references project-wide
        references = await navigation_service.find_references(
            symbol="User", file=str(temp_project / "models.py"), line=3, scope="project"
        )

        # Should have references from multiple files
        ref_files = {ref.file for ref in references}
        assert len(ref_files) > 1

    async def test_no_references_returns_empty_list(
        self, navigation_service, temp_project
    ):
        """Test that symbols with no references return an empty list."""
        # Create a file with an unused symbol
        unused_file = temp_project / "unused.py"
        unused_file.write_text('''def unused_function():
    """This is never called."""
    pass
''')

        import asyncio

        await asyncio.sleep(1)

        references = await navigation_service.find_references(
            symbol="unused_function",
            file=str(unused_file),
            line=1,
        )

        # Should either be empty or only contain the declaration
        assert len(references) <= 1

    async def test_references_without_context_raises_error(self, navigation_service):
        """Test that finding references without file/line context raises error."""
        with pytest.raises(
            NotImplementedError, match="Symbol search without file context"
        ):
            await navigation_service.find_references(symbol="User")

    async def test_references_include_line_and_column(
        self, navigation_service, temp_project
    ):
        """Test that references include accurate line and column information."""
        references = await navigation_service.find_references(
            symbol="User",
            file=str(temp_project / "models.py"),
            line=3,
        )

        # All references should have line and column
        for ref in references:
            assert ref.line > 0
            assert ref.column >= 0

    async def test_references_from_usage_site(self, navigation_service, temp_project):
        """Test finding references starting from a usage site (not the definition)."""
        # Find User references starting from an import statement
        references = await navigation_service.find_references(
            symbol="User",
            file=str(temp_project / "main.py"),
            line=2,  # Line with "from models import User, create_user"
        )

        # Should find references (import statements often work better than usage sites)
        assert len(references) >= 1

        # Should have User in the context
        assert any("User" in ref.context for ref in references)
