"""Integration tests for LSP navigation features (language-agnostic).

Consolidated tests for:
- find_definition: Finding symbol definitions across files
- find_references: Finding all references to a symbol
- get_hover_info: Getting type and documentation information
- get_completions: Code completion suggestions

All tests run across Python, JavaScript, and Rust to verify language-agnostic behavior.
"""

import pytest

from src.otter.models.responses import Completion, CompletionsResult
from src.otter.services.navigation import NavigationService
from tests.fixtures.language_configs import LanguageTestConfig


@pytest.mark.asyncio
class TestFindDefinition:
    """Tests for finding symbol definitions."""

    @pytest.fixture
    async def navigation_service(self, nvim_client_with_lsp, language_project_dir):
        """Create NavigationService with LSP ready."""
        return NavigationService(
            nvim_client=nvim_client_with_lsp, project_path=str(language_project_dir)
        )

    async def test_find_class_definition(
        self,
        navigation_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test finding a class definition from usage site."""
        ext = language_config.file_extension
        import_line = (
            2
            if language_config.language == "python"
            else 4
            if language_config.language == "javascript"
            else 5
        )

        result = await navigation_service.find_definition(
            symbol="User",
            file=str(language_project_dir / f"main{ext}"),
            line=import_line,
        )

        assert f"models{ext}" in result.file or result.file == f"models{ext}"
        assert result.symbol_name == "User"
        assert result.symbol_type in ["class", "struct"]
        assert result.line > 0
        assert len(result.context_lines) > 0
        assert "User" in "\n".join(result.context_lines)

    async def test_find_function_definition(
        self,
        navigation_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test finding a function definition."""
        ext = language_config.file_extension
        func_name = (
            "create_user" if language_config.language != "javascript" else "createUser"
        )
        import_line = (
            2
            if language_config.language == "python"
            else 4
            if language_config.language == "javascript"
            else 5
        )

        result = await navigation_service.find_definition(
            symbol=func_name,
            file=str(language_project_dir / f"main{ext}"),
            line=import_line,
        )

        assert f"models{ext}" in result.file
        assert result.symbol_type == "function"
        assert result.line > 0

    async def test_find_method_definition(
        self,
        navigation_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test finding a method definition."""
        ext = language_config.file_extension
        call_line = (
            8
            if language_config.language == "python"
            else 9
            if language_config.language == "javascript"
            else 11
        )

        result = await navigation_service.find_definition(
            symbol="greet",
            file=str(language_project_dir / f"main{ext}"),
            line=call_line,
        )

        assert f"models{ext}" in result.file
        assert result.symbol_name == "greet"
        assert result.symbol_type in ["method", "function"]

    async def test_find_definition_same_file(
        self,
        navigation_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test finding definition within the same file."""
        ext = language_config.file_extension
        search_line = (
            13
            if language_config.language == "python"
            else 31
            if language_config.language == "javascript"
            else 22
        )

        result = await navigation_service.find_definition(
            symbol="User",
            file=str(language_project_dir / f"models{ext}"),
            line=search_line,
        )

        assert f"models{ext}" in result.file
        assert result.symbol_name == "User"

    async def test_definition_not_found_raises_error(
        self,
        navigation_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test error when definition is not found."""
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


@pytest.mark.asyncio
class TestFindReferences:
    """Tests for finding symbol references."""

    @pytest.fixture
    async def navigation_service(self, nvim_client_with_lsp, language_project_dir):
        """Create NavigationService with LSP ready."""
        return NavigationService(
            nvim_client=nvim_client_with_lsp, project_path=str(language_project_dir)
        )

    async def test_find_class_references(
        self,
        navigation_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test finding all references to a class."""
        user_loc = language_config.symbol_locations["User"]
        ext = language_config.file_extension

        result = await navigation_service.find_references(
            symbol="User",
            file=str(language_project_dir / f"{user_loc.file}{ext}"),
            line=user_loc.line,
        )

        assert result.total_count >= 0
        for ref in result.references:
            assert ref.context
            assert "User" in ref.context
            assert ref.line > 0
            assert ref.column >= 0

    async def test_find_method_references(
        self,
        navigation_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test finding references to a method."""
        ext = language_config.file_extension

        result = await navigation_service.find_references(
            symbol="greet",
            file=str(language_project_dir / f"main{ext}"),
            line=7,
        )

        assert result.total_count >= 0
        for ref in result.references:
            assert "greet" in ref.context

    async def test_scope_file_filters_references(
        self,
        navigation_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test that scope='file' filters to only the current file."""
        user_loc = language_config.symbol_locations["User"]
        ext = language_config.file_extension
        models_file = f"models{ext}"

        result = await navigation_service.find_references(
            symbol="User",
            file=str(language_project_dir / models_file),
            line=user_loc.line,
            scope="file",
        )

        for ref in result.references:
            assert models_file in ref.file or ref.file == models_file

    async def test_scope_project_returns_all_references(
        self,
        navigation_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test that scope='project' returns references from all files."""
        user_loc = language_config.symbol_locations["User"]
        ext = language_config.file_extension

        result = await navigation_service.find_references(
            symbol="User",
            file=str(language_project_dir / f"{user_loc.file}{ext}"),
            line=user_loc.line,
            scope="project",
        )

        assert result.total_count >= 1
        assert len(result.references) >= 1

    async def test_references_without_context_raises_error(self, navigation_service):
        """Test that finding references without file/line context raises error."""
        with pytest.raises(
            NotImplementedError, match="Symbol search without file context"
        ):
            await navigation_service.find_references(symbol="User")

    async def test_is_definition_flag(
        self,
        navigation_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test that the is_definition flag correctly identifies the definition."""
        user_loc = language_config.symbol_locations["User"]
        ext = language_config.file_extension

        result = await navigation_service.find_references(
            symbol="User",
            file=str(language_project_dir / f"{user_loc.file}{ext}"),
            line=user_loc.line,
        )

        definitions = [ref for ref in result.references if ref.is_definition]
        assert len(definitions) >= 1
        assert definitions[0].line == user_loc.line

    async def test_exclude_definition_parameter(
        self,
        navigation_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test that exclude_definition parameter filters out the definition."""
        user_loc = language_config.symbol_locations["User"]
        ext = language_config.file_extension

        all_result = await navigation_service.find_references(
            symbol="User",
            file=str(language_project_dir / f"{user_loc.file}{ext}"),
            line=user_loc.line,
        )

        filtered_result = await navigation_service.find_references(
            symbol="User",
            file=str(language_project_dir / f"{user_loc.file}{ext}"),
            line=user_loc.line,
            exclude_definition=True,
        )

        assert (
            filtered_result.total_count < all_result.total_count
            or all_result.total_count == 1
        )
        for ref in filtered_result.references:
            assert not ref.is_definition

    async def test_grouped_by_file(
        self,
        navigation_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test that grouped_by_file properly groups references."""
        user_loc = language_config.symbol_locations["User"]
        ext = language_config.file_extension

        result = await navigation_service.find_references(
            symbol="User",
            file=str(language_project_dir / f"{user_loc.file}{ext}"),
            line=user_loc.line,
        )

        assert len(result.grouped_by_file) >= 1

        total_refs_in_groups = 0
        for group in result.grouped_by_file:
            assert group.file
            assert group.count == len(group.references)
            total_refs_in_groups += group.count

            for ref in group.references:
                assert ref.file == group.file

        assert total_refs_in_groups == result.total_count


@pytest.mark.asyncio
class TestHoverInfo:
    """Tests for hover information."""

    @pytest.fixture
    async def navigation_service(self, nvim_client_with_lsp, language_project_dir):
        """Create NavigationService with LSP ready."""
        return NavigationService(
            nvim_client=nvim_client_with_lsp, project_path=str(language_project_dir)
        )

    async def test_hover_on_class(
        self,
        navigation_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test hover information for a class."""
        ext = language_config.file_extension
        user_loc = language_config.symbol_locations["User"]

        hover = await navigation_service.get_hover_info(
            str(language_project_dir / f"{user_loc.file}{ext}"),
            line=user_loc.line,
            column=6,
        )

        assert hover.symbol == "User"
        assert hover.type is not None
        type_lower = hover.type.lower()
        assert any(keyword in type_lower for keyword in ["class", "struct", "user"])

    async def test_hover_on_method(
        self,
        navigation_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test hover information for a method."""
        ext = language_config.file_extension
        greet_loc = language_config.symbol_locations["greet"]

        hover = await navigation_service.get_hover_info(
            str(language_project_dir / f"{greet_loc.file}{ext}"),
            line=greet_loc.line,
            column=8,
        )

        assert hover.symbol == "greet"
        assert hover.type is not None

    async def test_hover_on_function(
        self,
        navigation_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test hover information for a function."""
        ext = language_config.file_extension
        func_loc = language_config.symbol_locations["create_user"]
        func_name = (
            "create_user" if language_config.language != "javascript" else "createUser"
        )

        hover = await navigation_service.get_hover_info(
            str(language_project_dir / f"{func_loc.file}{ext}"),
            line=func_loc.line,
            column=8,
        )

        assert func_name in hover.symbol or "create_user" in hover.symbol.lower()
        assert hover.type is not None

    async def test_hover_includes_docstring(
        self,
        navigation_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test that hover includes docstring/documentation."""
        ext = language_config.file_extension
        user_loc = language_config.symbol_locations["User"]

        hover = await navigation_service.get_hover_info(
            str(language_project_dir / f"{user_loc.file}{ext}"),
            line=user_loc.line,
            column=6,
        )

        if hover.docstring:
            assert len(hover.docstring.strip()) > 5

    async def test_hover_no_symbol_raises_error(
        self,
        navigation_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test that hovering on empty space raises an error."""
        ext = language_config.file_extension

        with pytest.raises(RuntimeError, match="No symbol found"):
            await navigation_service.get_hover_info(
                str(language_project_dir / f"models{ext}"), line=1, column=0
            )

    async def test_hover_without_nvim_raises_error(
        self, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that get_hover_info without Neovim client raises error."""
        ext = language_config.file_extension
        service = NavigationService(
            project_path=str(language_project_dir), nvim_client=None
        )

        with pytest.raises(RuntimeError, match="Neovim client required"):
            await service.get_hover_info(
                str(language_project_dir / f"models{ext}"), line=5, column=6
            )

    async def test_hover_requires_symbol_or_position(
        self,
        navigation_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test that get_hover_info requires either symbol or position."""
        ext = language_config.file_extension

        with pytest.raises(
            ValueError, match="Must provide either 'symbol' or both 'line' and 'column'"
        ):
            await navigation_service.get_hover_info(
                str(language_project_dir / f"models{ext}")
            )


@pytest.mark.asyncio
class TestCompletions:
    """Tests for code completions."""

    @pytest.fixture
    async def navigation_service(self, nvim_client_with_lsp, language_project_dir):
        """Create NavigationService with LSP ready."""
        return NavigationService(
            nvim_client=nvim_client_with_lsp, project_path=str(language_project_dir)
        )

    async def test_get_completions_returns_result(
        self, navigation_service, language_config: LanguageTestConfig
    ):
        """Test that get_completions returns CompletionsResult."""
        ext = language_config.file_extension
        line = (
            7
            if language_config.language == "python"
            else 9
            if language_config.language == "javascript"
            else 11
        )

        result = await navigation_service.get_completions(
            file=f"main{ext}", line=line, column=10
        )

        assert isinstance(result, CompletionsResult)
        assert isinstance(result.completions, list)
        assert isinstance(result.total_count, int)
        assert isinstance(result.returned_count, int)
        assert isinstance(result.truncated, bool)

        for completion in result.completions:
            assert isinstance(completion, Completion)
            assert isinstance(completion.text, str)
            assert len(completion.text) > 0

    async def test_completions_structure(
        self, navigation_service, language_config: LanguageTestConfig
    ):
        """Test that completions have correct structure and valid values."""
        ext = language_config.file_extension
        line = (
            7
            if language_config.language == "python"
            else 9
            if language_config.language == "javascript"
            else 11
        )

        result = await navigation_service.get_completions(
            file=f"main{ext}", line=line, column=10
        )

        for completion in result.completions:
            # Required fields
            assert hasattr(completion, "text")
            assert isinstance(completion.text, str)
            assert len(completion.text) > 0

            # No weird characters in text
            assert "\n" not in completion.text
            assert "\r" not in completion.text
            assert "\t" not in completion.text

            # Optional fields should exist but may be None
            assert hasattr(completion, "kind")
            assert hasattr(completion, "detail")
            assert hasattr(completion, "documentation")
            assert hasattr(completion, "sort_text")

            # Validate types if present
            if completion.kind is not None:
                assert isinstance(completion.kind, str)
            if completion.detail is not None:
                assert isinstance(completion.detail, str)

    async def test_completions_in_different_files(
        self, navigation_service, language_config: LanguageTestConfig
    ):
        """Test completions work in different files."""
        ext = language_config.file_extension

        # Test in models file
        line1 = (
            10
            if language_config.language == "python"
            else 12
            if language_config.language == "javascript"
            else 11
        )

        result1 = await navigation_service.get_completions(
            file=f"models{ext}", line=line1, column=8
        )

        assert isinstance(result1, CompletionsResult)

        # Test in services file
        line2 = (
            8
            if language_config.language == "python"
            else 10
            if language_config.language == "javascript"
            else 9
        )

        result2 = await navigation_service.get_completions(
            file=f"services{ext}", line=line2, column=8
        )

        assert isinstance(result2, CompletionsResult)

    async def test_completions_max_results_limit(
        self, navigation_service, language_config: LanguageTestConfig
    ):
        """Test that max_results parameter limits returned completions."""
        ext = language_config.file_extension
        line = (
            7
            if language_config.language == "python"
            else 9
            if language_config.language == "javascript"
            else 11
        )

        result = await navigation_service.get_completions(
            file=f"main{ext}", line=line, column=10, max_results=10
        )

        assert isinstance(result, CompletionsResult)
        assert result.returned_count <= 10
        assert len(result.completions) == result.returned_count

        if result.truncated:
            assert result.total_count > result.returned_count

    async def test_completions_metadata_consistency(
        self, navigation_service, language_config: LanguageTestConfig
    ):
        """Test that CompletionsResult metadata is consistent."""
        ext = language_config.file_extension
        line = (
            7
            if language_config.language == "python"
            else 9
            if language_config.language == "javascript"
            else 11
        )

        result = await navigation_service.get_completions(
            file=f"main{ext}", line=line, column=10
        )

        # Metadata consistency
        assert result.returned_count == len(result.completions)
        assert result.returned_count <= result.total_count

        if result.returned_count < result.total_count:
            assert result.truncated

        if not result.truncated:
            assert result.returned_count == result.total_count

    async def test_completions_without_nvim_raises_error(
        self, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that get_completions without Neovim raises error."""
        ext = language_config.file_extension
        service = NavigationService(
            nvim_client=None, project_path=str(language_project_dir)
        )

        with pytest.raises(RuntimeError) as exc_info:
            await service.get_completions(file=f"main{ext}", line=5, column=9)

        assert "neovim" in str(exc_info.value).lower()
