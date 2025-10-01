"""Integration tests for find_definition feature (language-agnostic).

This test suite runs across Python, JavaScript, and Rust to verify that
find_definition works consistently across all supported languages.
"""

import pytest

from src.otter.neovim.client import NeovimClient
from src.otter.services.navigation import NavigationService
from tests.fixtures.language_configs import LanguageTestConfig


@pytest.mark.asyncio
class TestFindDefinitionParameterized:
    """Language-agnostic integration tests for find_definition."""

    @pytest.fixture
    async def navigation_service(self, language_project_dir, language_config: LanguageTestConfig):
        """Create NavigationService with a real Neovim instance for the test language."""
        nvim_client = NeovimClient(project_path=str(language_project_dir))
        service = NavigationService(
            nvim_client=nvim_client, project_path=str(language_project_dir)
        )

        await nvim_client.start()

        # Wait for LSP to analyze the files
        import asyncio
        await asyncio.sleep(2)

        yield service
        await nvim_client.stop()

    async def test_find_class_definition(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test finding a class definition across all languages."""
        ext = language_config.file_extension
        user_loc = language_config.symbol_locations["User"]
        
        # Find definition of User when cursor is on it in main file
        # The line number where User is imported/used varies by language
        import_line = 2 if language_config.language == "python" else \
                     4 if language_config.language == "javascript" else \
                     5  # rust
        
        result = await navigation_service.find_definition(
            symbol="User",
            file=str(language_project_dir / f"main{ext}"),
            line=import_line,
        )

        assert f"models{ext}" in result.file or result.file == f"models{ext}", \
            f"User should be defined in models file for {language_config.language}"
        assert result.symbol_name == "User", \
            f"Symbol name should be User for {language_config.language}"
        
        # Type might be "class" or "struct" (Rust)
        assert result.symbol_type in ["class", "struct"], \
            f"User should be class/struct in {language_config.language}"
        
        # Line should be approximately where User is defined
        assert result.line > 0, f"Line should be positive for {language_config.language}"
        
        # Should have context lines
        assert len(result.context_lines) > 0, \
            f"Should have context lines for {language_config.language}"
        
        # Context should mention User
        context_text = "\n".join(result.context_lines)
        assert "User" in context_text, \
            f"Context should mention User in {language_config.language}"

    async def test_find_function_definition(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test finding a function definition across all languages."""
        ext = language_config.file_extension
        func_loc = language_config.symbol_locations["create_user"]
        
        # Map function name to language-specific naming
        func_name = "create_user" if language_config.language == "python" else \
                    "createUser" if language_config.language == "javascript" else \
                    "create_user"
        
        # Line where function is imported/used in main
        import_line = 2 if language_config.language == "python" else \
                     4 if language_config.language == "javascript" else \
                     5  # rust
        
        result = await navigation_service.find_definition(
            symbol=func_name,
            file=str(language_project_dir / f"main{ext}"),
            line=import_line,
        )

        assert f"models{ext}" in result.file or result.file == f"models{ext}", \
            f"Function should be defined in models file for {language_config.language}"
        assert func_name in result.symbol_name or "create_user" in result.symbol_name.lower(), \
            f"Symbol name should be {func_name} for {language_config.language}"
        assert result.symbol_type == "function", \
            f"Symbol type should be function for {language_config.language}"
        
        # Line should be approximately where function is defined
        assert result.line > 0, f"Line should be positive for {language_config.language}"
        
        # Should have signature
        if result.signature:
            assert func_name in result.signature or "create_user" in result.signature.lower(), \
                f"Signature should mention {func_name} in {language_config.language}"

    async def test_find_method_definition(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test finding a method definition across all languages."""
        ext = language_config.file_extension
        
        # Find definition of greet() method when called
        # Line where method is called varies, but should be around line 7-11 in main
        call_line = 8 if language_config.language == "python" else \
                    9 if language_config.language == "javascript" else \
                    11
        
        result = await navigation_service.find_definition(
            symbol="greet",
            file=str(language_project_dir / f"main{ext}"),
            line=call_line,
        )

        assert f"models{ext}" in result.file or result.file == f"models{ext}", \
            f"Method should be defined in models file for {language_config.language}"
        assert result.symbol_name == "greet", \
            f"Symbol name should be greet for {language_config.language}"
        assert result.symbol_type in ["method", "function"], \
            f"Symbol type should be method/function for {language_config.language}"
        
        # Should have signature
        if result.signature:
            assert "greet" in result.signature, \
                f"Signature should mention greet in {language_config.language}"

    async def test_find_definition_in_same_file(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test finding definition within the same file across all languages."""
        ext = language_config.file_extension
        user_loc = language_config.symbol_locations["User"]
        
        # Find User definition from within models file
        # Look for where User is used in the create_user function
        search_line = 13 if language_config.language == "python" else \
                     31 if language_config.language == "javascript" else \
                     22
        
        result = await navigation_service.find_definition(
            symbol="User",
            file=str(language_project_dir / f"models{ext}"),
            line=search_line,
        )

        assert f"models{ext}" in result.file or result.file == f"models{ext}", \
            f"User should be defined in models file for {language_config.language}"
        assert result.symbol_name == "User", \
            f"Symbol name should be User for {language_config.language}"
        assert result.symbol_type in ["class", "struct"], \
            f"Symbol type should be class/struct for {language_config.language}"

    async def test_definition_not_found(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test error handling when definition is not found across all languages."""
        ext = language_config.file_extension
        
        with pytest.raises(RuntimeError, match="Definition not found"):
            await navigation_service.find_definition(
                symbol="NonExistent",
                file=str(language_project_dir / f"main{ext}"),
                line=1,
            )

    async def test_definition_without_context_raises_error(self, navigation_service):
        """Test that finding definition without file/line context raises error."""
        with pytest.raises(
            NotImplementedError, match="Symbol search without file context"
        ):
            await navigation_service.find_definition(symbol="User")

    async def test_definition_provides_context_lines(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that definition includes surrounding context lines across all languages."""
        ext = language_config.file_extension
        import_line = 2 if language_config.language != "rust" else 5
        
        result = await navigation_service.find_definition(
            symbol="User",
            file=str(language_project_dir / f"main{ext}"),
            line=import_line,
        )

        # Should have several context lines
        assert len(result.context_lines) > 3, \
            f"Should have context lines for {language_config.language}"
        
        # Context should include the class/struct definition
        context_text = "\n".join(result.context_lines)
        assert "User" in context_text, \
            f"Context should mention User in {language_config.language}"
        
        # Should include the class/struct keyword
        has_class_keyword = any(
            keyword in context_text 
            for keyword in ["class User", "struct User", "class User {"]
        )
        assert has_class_keyword, \
            f"Context should include class/struct definition in {language_config.language}"

    async def test_find_service_class_definition(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test finding UserService class definition across all languages."""
        ext = language_config.file_extension
        service_loc = language_config.symbol_locations["UserService"]
        
        # Line where UserService is imported/used in main
        import_line = 3 if language_config.language == "python" else \
                     5 if language_config.language == "javascript" else \
                     6  # rust
        
        result = await navigation_service.find_definition(
            symbol="UserService",
            file=str(language_project_dir / f"main{ext}"),
            line=import_line,
        )

        assert f"services{ext}" in result.file or result.file == f"services{ext}", \
            f"UserService should be defined in services file for {language_config.language}"
        assert result.symbol_name == "UserService", \
            f"Symbol name should be UserService for {language_config.language}"
        assert result.symbol_type in ["class", "struct"], \
            f"UserService should be class/struct in {language_config.language}"

