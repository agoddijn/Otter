"""Integration tests for get_symbols feature (language-agnostic).

This test suite runs across Python, JavaScript, and Rust to verify that
get_symbols works consistently across all supported languages.
"""

import pytest

from src.otter.neovim.client import NeovimClient
from src.otter.services.workspace import WorkspaceService
from tests.fixtures.language_configs import LanguageTestConfig


@pytest.mark.asyncio
class TestGetSymbolsParameterized:
    """Language-agnostic integration tests for get_symbols."""

    @pytest.fixture
    async def workspace_service(self, language_project_dir, language_config: LanguageTestConfig):
        """Create WorkspaceService with a real Neovim instance for the test language."""
        nvim_client = NeovimClient(project_path=str(language_project_dir))
        service = WorkspaceService(
            project_path=str(language_project_dir), nvim_client=nvim_client
        )

        await nvim_client.start()

        # Wait for LSP to analyze files
        import asyncio
        await asyncio.sleep(2)

        yield service
        await nvim_client.stop()

    async def test_get_all_symbols(
        self, workspace_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test getting all symbols from a file across all languages."""
        ext = language_config.file_extension
        result = await workspace_service.get_symbols(str(language_project_dir / f"models{ext}"))

        # Check result structure
        assert result.file.endswith(f"models{ext}"), "File path should be in result"
        assert result.total_count > 0, "Should have total count"
        assert result.language is not None, "Should detect language"
        
        symbols = result.symbols
        # Should have classes, functions, and possibly module-level items
        assert len(symbols) > 0, f"Expected symbols for {language_config.language}"

        # Check we have expected top-level symbols
        symbol_names = {s.name for s in symbols}
        
        # Should have at least User class and create_user function
        # (naming convention may vary by language)
        has_user = "User" in symbol_names
        has_create = any(name in symbol_names for name in ["create_user", "createUser"])
        
        assert has_user or has_create, \
            f"Expected User class or create_user function in {language_config.language} symbols: {symbol_names}"

    async def test_symbols_have_correct_types(
        self, workspace_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that symbols have correct type information across all languages."""
        ext = language_config.file_extension
        result = await workspace_service.get_symbols(str(language_project_dir / f"models{ext}"))
        symbols = result.symbols

        # Find specific symbols and verify their types
        for symbol in symbols:
            # Class/struct types
            if symbol.name == "User":
                assert symbol.type in ["class", "struct"], \
                    f"User should be class/struct in {language_config.language}"
            
            # Function types
            elif symbol.name in ["create_user", "createUser"]:
                assert symbol.type == "function", \
                    f"create_user should be function in {language_config.language}"
            
            # Constant/variable types
            elif symbol.name in ["DEFAULT_NAME"]:
                assert symbol.type in ["variable", "constant", "const"], \
                    f"DEFAULT_NAME should be variable/constant in {language_config.language}"

    async def test_symbols_have_line_numbers(
        self, workspace_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that symbols include line numbers across all languages."""
        ext = language_config.file_extension
        result = await workspace_service.get_symbols(str(language_project_dir / f"models{ext}"))
        symbols = result.symbols

        # All symbols should have positive line numbers
        for symbol in symbols:
            assert symbol.line > 0, \
                f"Symbol {symbol.name} should have positive line number in {language_config.language}"

    async def test_symbols_include_children(
        self, workspace_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that class symbols include their methods as children."""
        ext = language_config.file_extension
        result = await workspace_service.get_symbols(str(language_project_dir / f"models{ext}"))
        symbols = result.symbols

        # Find the User class/struct symbol
        user_symbol = None
        for symbol in symbols:
            if symbol.name == "User":
                user_symbol = symbol
                break

        if user_symbol:
            # Should have children (methods)
            assert user_symbol.children is not None, \
                f"User should have children in {language_config.language}"
            assert len(user_symbol.children) > 0, \
                f"User should have methods in {language_config.language}"

            # Children should be methods/functions
            method_names = {child.name for child in user_symbol.children}
            
            # Different languages have different constructor/method names
            expected_methods = {
                "python": ["__init__", "greet"],
                "javascript": ["constructor", "greet"],
                "rust": ["new", "greet"],
            }
            
            expected = expected_methods[language_config.language]
            has_expected = any(method in method_names for method in expected)
            
            assert has_expected, \
                f"Expected methods {expected} in {language_config.language}, got {method_names}"

    async def test_child_symbols_have_parent(
        self, workspace_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that child symbols reference their parent across all languages."""
        ext = language_config.file_extension
        result = await workspace_service.get_symbols(str(language_project_dir / f"models{ext}"))
        symbols = result.symbols

        # Find a class with children
        for symbol in symbols:
            if symbol.children and len(symbol.children) > 0:
                for child in symbol.children:
                    # Child should reference parent
                    assert child.parent == symbol.name, \
                        f"Child {child.name} should have parent {symbol.name} in {language_config.language}"
                break

    async def test_filter_by_symbol_type_class(
        self, workspace_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test filtering symbols by type (class) across all languages."""
        ext = language_config.file_extension
        
        # Rust uses "struct" instead of "class"
        symbol_types = ["class"] if language_config.language != "rust" else ["struct", "class"]
        
        result = await workspace_service.get_symbols(
            str(language_project_dir / f"models{ext}"), symbol_types=symbol_types
        )
        symbols = result.symbols

        # Should only have class/struct symbols
        for symbol in symbols:
            assert symbol.type in symbol_types, \
                f"Expected {symbol_types} but got {symbol.type} in {language_config.language}"

    async def test_filter_by_symbol_type_function(
        self, workspace_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test filtering symbols by type (function) across all languages."""
        ext = language_config.file_extension
        result = await workspace_service.get_symbols(
            str(language_project_dir / f"models{ext}"), symbol_types=["function"]
        )
        symbols = result.symbols

        # Should only have function symbols (not methods)
        for symbol in symbols:
            assert symbol.type == "function", \
                f"Expected function but got {symbol.type} in {language_config.language}"
            # Should not have a parent (top-level functions)
            assert symbol.parent is None, \
                f"Top-level function should not have parent in {language_config.language}"

    async def test_filter_by_multiple_types(
        self, workspace_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test filtering by multiple symbol types across all languages."""
        ext = language_config.file_extension
        
        # Adjust for Rust's use of "struct" instead of "class"
        symbol_types = ["class", "function"] if language_config.language != "rust" \
                      else ["struct", "function", "class"]
        
        result = await workspace_service.get_symbols(
            str(language_project_dir / f"models{ext}"), symbol_types=symbol_types
        )
        symbols = result.symbols

        # Should have both classes/structs and functions
        types = {s.type for s in symbols}
        assert len(types.intersection(set(symbol_types))) > 0, \
            f"Expected types {symbol_types} in {language_config.language}, got {types}"

        # Should not have other types at top level
        for symbol in symbols:
            assert symbol.type in symbol_types, \
                f"Unexpected type {symbol.type} in {language_config.language}"

    async def test_empty_file_returns_empty_list(
        self, workspace_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that an empty file returns an empty list across all languages."""
        ext = language_config.file_extension
        empty_file = language_project_dir / f"empty{ext}"
        empty_file.write_text("")

        import asyncio
        await asyncio.sleep(1)

        result = await workspace_service.get_symbols(str(empty_file))
        assert result.symbols == [], f"Empty file should return empty list in {language_config.language}"
        assert result.total_count == 0, "Empty file should have 0 total count"

    async def test_file_not_found_raises_error(
        self, workspace_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that non-existent file raises FileNotFoundError across all languages."""
        ext = language_config.file_extension
        with pytest.raises(FileNotFoundError):
            await workspace_service.get_symbols(str(language_project_dir / f"nonexistent{ext}"))

    async def test_symbols_without_nvim_raises_error(
        self, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that get_symbols without Neovim client raises error."""
        service = WorkspaceService(project_path=str(language_project_dir), nvim_client=None)
        ext = language_config.file_extension

        with pytest.raises(RuntimeError, match="Neovim client required"):
            await service.get_symbols(str(language_project_dir / f"models{ext}"))

    async def test_relative_path_works(
        self, workspace_service, language_config: LanguageTestConfig
    ):
        """Test that relative paths work correctly across all languages."""
        ext = language_config.file_extension
        result = await workspace_service.get_symbols(f"models{ext}")

        # Should work the same as absolute path
        assert len(result.symbols) > 0, f"Relative path should work in {language_config.language}"

