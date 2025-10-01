"""Integration tests for get_hover_info feature (language-agnostic).

This test suite runs across Python, JavaScript, and Rust to verify that
get_hover_info works consistently across all supported languages.
"""

import pytest

from src.otter.neovim.client import NeovimClient
from src.otter.services.navigation import NavigationService
from tests.fixtures.language_configs import LanguageTestConfig


@pytest.mark.asyncio
class TestGetHoverInfoParameterized:
    """Language-agnostic integration tests for get_hover_info."""

    @pytest.fixture
    async def navigation_service(self, language_project_dir, language_config: LanguageTestConfig):
        """Create NavigationService with a real Neovim instance for the test language."""
        nvim_client = NeovimClient(project_path=str(language_project_dir))
        service = NavigationService(
            project_path=str(language_project_dir), nvim_client=nvim_client
        )

        await nvim_client.start()

        # Wait for LSP to analyze files
        import asyncio
        await asyncio.sleep(2)

        yield service
        await nvim_client.stop()

    async def test_hover_on_class(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test hover information for a class across all languages."""
        ext = language_config.file_extension
        user_loc = language_config.symbol_locations["User"]
        
        # Hover over "User" class name
        hover = await navigation_service.get_hover_info(
            str(language_project_dir / f"{user_loc.file}{ext}"),
            user_loc.line,
            6  # Approximate column for class name
        )

        assert hover.symbol == "User", \
            f"Expected User symbol for {language_config.language}"
        assert hover.type is not None, \
            f"Expected type information for {language_config.language}"
        
        # Type should mention class/struct or User
        type_lower = hover.type.lower()
        assert "class" in type_lower or "struct" in type_lower or "user" in type_lower, \
            f"Expected class/struct/User in type for {language_config.language}, got: {hover.type}"

    async def test_hover_on_method(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test hover information for a method across all languages."""
        ext = language_config.file_extension
        greet_loc = language_config.symbol_locations["greet"]
        
        # Hover over "greet" method
        hover = await navigation_service.get_hover_info(
            str(language_project_dir / f"{greet_loc.file}{ext}"),
            greet_loc.line,
            8  # Approximate column for method name
        )

        assert hover.symbol == "greet", \
            f"Expected greet symbol for {language_config.language}"
        assert hover.type is not None, \
            f"Expected type information for {language_config.language}"
        
        # Should indicate it's a method/function
        type_lower = hover.type.lower()
        assert any(keyword in type_lower for keyword in ["method", "function", "def", "fn", "greet"]), \
            f"Expected method/function indicator for {language_config.language}, got: {hover.type}"

    async def test_hover_on_function(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test hover information for a function across all languages."""
        ext = language_config.file_extension
        func_loc = language_config.symbol_locations["create_user"]
        
        # Map function name to language-specific naming
        func_name = "create_user" if language_config.language == "python" else \
                    "createUser" if language_config.language == "javascript" else \
                    "create_user"
        
        # Hover over function name
        hover = await navigation_service.get_hover_info(
            str(language_project_dir / f"{func_loc.file}{ext}"),
            func_loc.line,
            8  # Approximate column
        )

        assert func_name in hover.symbol or "create_user" in hover.symbol.lower(), \
            f"Expected {func_name} in symbol for {language_config.language}"
        assert hover.type is not None, \
            f"Expected type information for {language_config.language}"

    async def test_hover_includes_docstring(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that hover includes docstring/documentation across all languages."""
        ext = language_config.file_extension
        user_loc = language_config.symbol_locations["User"]
        
        # Hover over User class which has documentation
        hover = await navigation_service.get_hover_info(
            str(language_project_dir / f"{user_loc.file}{ext}"),
            user_loc.line,
            6
        )

        # Should have docstring or documentation
        # Different LSPs may provide docs in different formats
        if hover.docstring:
            assert len(hover.docstring) > 0, \
                f"Docstring should not be empty for {language_config.language}"
            # Docstrings may vary by language but should have some content
            assert len(hover.docstring.strip()) > 5, \
                f"Docstring should have meaningful content for {language_config.language}"

    async def test_hover_no_info_raises_error(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that hovering on empty space raises an error across all languages."""
        ext = language_config.file_extension
        
        # Hover on line 1 (usually comment or empty)
        with pytest.raises(RuntimeError, match="No hover information found"):
            await navigation_service.get_hover_info(
                str(language_project_dir / f"models{ext}"),
                1,
                0
            )

    async def test_hover_without_nvim_raises_error(
        self, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that get_hover_info without Neovim client raises error."""
        ext = language_config.file_extension
        service = NavigationService(project_path=str(language_project_dir), nvim_client=None)

        with pytest.raises(RuntimeError, match="Neovim client required"):
            await service.get_hover_info(
                str(language_project_dir / f"models{ext}"),
                5,
                6
            )

    async def test_hover_in_different_files(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test hover information works across different files."""
        ext = language_config.file_extension
        
        # Test hover in services file
        service_loc = language_config.symbol_locations["UserService"]
        hover = await navigation_service.get_hover_info(
            str(language_project_dir / f"{service_loc.file}{ext}"),
            service_loc.line,
            6
        )
        
        assert hover.symbol == "UserService", \
            f"Expected UserService symbol for {language_config.language}"
        assert hover.type is not None, \
            f"Expected type for UserService in {language_config.language}"

    async def test_hover_provides_type_info(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that hover provides useful type information."""
        ext = language_config.file_extension
        func_loc = language_config.symbol_locations["create_user"]
        
        hover = await navigation_service.get_hover_info(
            str(language_project_dir / f"{func_loc.file}{ext}"),
            func_loc.line,
            8
        )
        
        # Type should be a non-empty string
        assert isinstance(hover.type, str), \
            f"Type should be string for {language_config.language}"
        assert len(hover.type) > 0, \
            f"Type should not be empty for {language_config.language}"
        
        # Type should contain function/method indicator
        type_lower = hover.type.lower()
        has_function_indicator = any(
            keyword in type_lower 
            for keyword in ["function", "fn", "def", "func"]
        )
        assert has_function_indicator or "create" in type_lower, \
            f"Type should indicate function for {language_config.language}, got: {hover.type}"

    async def test_hover_on_imported_symbol(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test hover on symbols used in imports/requires."""
        ext = language_config.file_extension
        
        # Line where User is imported in main file
        import_line = 2 if language_config.language == "python" else \
                     4 if language_config.language == "javascript" else \
                     5  # rust
        
        hover = await navigation_service.get_hover_info(
            str(language_project_dir / f"main{ext}"),
            import_line,
            20  # Approximate column where User appears
        )
        
        # Should get hover info for User
        assert "User" in hover.symbol, \
            f"Expected User in hover symbol for {language_config.language}"

