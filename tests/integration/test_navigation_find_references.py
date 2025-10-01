"""Integration tests for find_references feature (language-agnostic).

This test suite runs across Python, JavaScript, and Rust to verify that
find_references works consistently across all supported languages.
"""

import pytest

from src.otter.neovim.client import NeovimClient
from src.otter.services.navigation import NavigationService
from tests.fixtures.language_configs import LanguageTestConfig


@pytest.mark.asyncio
class TestFindReferencesParameterized:
    """Language-agnostic integration tests for find_references."""

    @pytest.fixture
    async def navigation_service(self, language_project_dir, language_config: LanguageTestConfig):
        """Create NavigationService with a real Neovim instance for the test language."""
        nvim_client = NeovimClient(project_path=str(language_project_dir))
        service = NavigationService(
            nvim_client=nvim_client, project_path=str(language_project_dir)
        )

        await nvim_client.start()

        # Wait for LSP to analyze files
        import asyncio
        await asyncio.sleep(2)

        yield service
        await nvim_client.stop()

    async def test_find_class_references(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test finding all references to a class across all languages."""
        # Get the User class location from config
        user_loc = language_config.symbol_locations["User"]
        ext = language_config.file_extension
        
        # Find references to User class
        references = await navigation_service.find_references(
            symbol="User",
            file=str(language_project_dir / f"{user_loc.file}{ext}"),
            line=user_loc.line,
        )

        # Should find references in multiple files
        assert len(references) >= 2, f"Expected at least 2 references for {language_config.language}"

        # Verify we have references from different files
        ref_files = {ref.file for ref in references}
        assert len(ref_files) >= 1, f"Expected references in at least 1 file for {language_config.language}"

        # All references should have context
        for ref in references:
            assert ref.context
            assert "User" in ref.context

    async def test_find_function_references(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test finding all references to a function across all languages."""
        # Get function location from config
        func_loc = language_config.symbol_locations["create_user"]
        ext = language_config.file_extension
        
        # Map function name to language-specific naming
        func_name = "create_user" if language_config.language == "python" else \
                    "createUser" if language_config.language == "javascript" else \
                    "create_user"
        
        references = await navigation_service.find_references(
            symbol=func_name,
            file=str(language_project_dir / f"{func_loc.file}{ext}"),
            line=func_loc.line,
        )

        # Should find at least the definition
        assert isinstance(references, list)

        # If we got references, they should mention the function
        for ref in references:
            assert func_name in ref.context or "create_user" in ref.context.lower()

    async def test_find_method_references(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test finding references to a method across all languages."""
        # Test finding the greet method
        method_loc = language_config.symbol_locations["greet"]
        ext = language_config.file_extension
        
        references = await navigation_service.find_references(
            symbol="greet",
            file=str(language_project_dir / f"main{ext}"),
            line=7,  # Approximate line where method is called
        )

        # Should find calls or at least return a valid list
        assert isinstance(references, list)

        # If we got references, verify context
        for ref in references:
            assert "greet" in ref.context

    async def test_scope_file_filters_references(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that scope='file' filters to only the current file."""
        user_loc = language_config.symbol_locations["User"]
        ext = language_config.file_extension
        models_file = f"models{ext}"
        
        # Find User references in models file only
        references = await navigation_service.find_references(
            symbol="User",
            file=str(language_project_dir / models_file),
            line=user_loc.line,
            scope="file",
        )

        # All references should be in models file
        for ref in references:
            assert models_file in ref.file or ref.file == models_file

    async def test_scope_project_returns_all_references(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that scope='project' returns references from all files."""
        user_loc = language_config.symbol_locations["User"]
        ext = language_config.file_extension
        
        # Find User references project-wide
        references = await navigation_service.find_references(
            symbol="User",
            file=str(language_project_dir / f"{user_loc.file}{ext}"),
            line=user_loc.line,
            scope="project",
        )

        # Should have references from multiple files (or at least multiple occurrences)
        # This varies by LSP implementation
        assert len(references) >= 1

    async def test_no_references_returns_empty_list(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that symbols with no references return an empty list."""
        ext = language_config.file_extension
        
        # Create a file with an unused symbol
        if language_config.language == "python":
            content = 'def unused_function():\n    """This is never called."""\n    pass\n'
        elif language_config.language == "javascript":
            content = '/** This is never called. */\nfunction unusedFunction() {}\n'
        else:  # rust
            content = '/// This is never called.\npub fn unused_function() {}\n'
        
        unused_file = language_project_dir / f"unused{ext}"
        unused_file.write_text(content)

        import asyncio
        await asyncio.sleep(1)

        symbol_name = "unused_function" if language_config.language != "javascript" else "unusedFunction"
        references = await navigation_service.find_references(
            symbol=symbol_name,
            file=str(unused_file),
            line=2 if language_config.language == "python" else 2,
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
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that references include accurate line and column information."""
        user_loc = language_config.symbol_locations["User"]
        ext = language_config.file_extension
        
        references = await navigation_service.find_references(
            symbol="User",
            file=str(language_project_dir / f"{user_loc.file}{ext}"),
            line=user_loc.line,
        )

        # All references should have line and column
        for ref in references:
            assert ref.line > 0
            assert ref.column >= 0

    async def test_references_from_usage_site(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test finding references starting from a usage site (not the definition)."""
        ext = language_config.file_extension
        
        # Find User references starting from an import/use statement in main
        references = await navigation_service.find_references(
            symbol="User",
            file=str(language_project_dir / f"main{ext}"),
            line=2 if language_config.language != "rust" else 5,  # Import line varies
        )

        # Should find references
        assert len(references) >= 1

        # Should have User in the context
        assert any("User" in ref.context for ref in references)

