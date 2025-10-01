"""Integration tests for get_completions feature (language-agnostic).

This test suite runs across Python, JavaScript, and Rust to verify that
get_completions works consistently across all supported languages.

Note: Completions are highly dependent on LSP server implementation and state,
so tests focus on structure and basic functionality rather than exact results.
"""

import pytest

from src.otter.models.responses import Completion, CompletionsResult
from src.otter.neovim.client import NeovimClient
from src.otter.services.navigation import NavigationService
from tests.fixtures.language_configs import LanguageTestConfig


@pytest.mark.asyncio
class TestGetCompletionsParameterized:
    """Language-agnostic integration tests for get_completions."""

    @pytest.fixture
    async def navigation_service(self, language_project_dir, language_config: LanguageTestConfig):
        """Create NavigationService with a real Neovim instance for the test language."""
        nvim_client = NeovimClient(project_path=str(language_project_dir))
        service = NavigationService(
            nvim_client=nvim_client, project_path=str(language_project_dir)
        )

        await nvim_client.start()
        
        # Wait for LSP to analyze and index
        import asyncio
        await asyncio.sleep(3)  # Completions need more time than other features
        
        yield service
        await nvim_client.stop()

    async def test_get_completions_returns_result_object(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that get_completions returns CompletionsResult across all languages."""
        ext = language_config.file_extension
        
        # Request completions at a reasonable location (inside main function)
        # Line number varies by language structure
        line = 7 if language_config.language == "python" else \
               9 if language_config.language == "javascript" else \
               11
        
        result = await navigation_service.get_completions(
            file=f"main{ext}",
            line=line,
            column=10
        )

        assert isinstance(result, CompletionsResult), \
            f"Should return CompletionsResult for {language_config.language}"
        
        # Check required fields
        assert isinstance(result.completions, list), \
            f"completions should be a list for {language_config.language}"
        assert isinstance(result.total_count, int), \
            f"total_count should be int for {language_config.language}"
        assert isinstance(result.returned_count, int), \
            f"returned_count should be int for {language_config.language}"
        assert isinstance(result.truncated, bool), \
            f"truncated should be bool for {language_config.language}"
        
        # Each completion should be a Completion object
        for completion in result.completions:
            assert isinstance(completion, Completion), \
                f"Each item should be Completion for {language_config.language}"

    async def test_completions_have_required_fields(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that completions have required fields across all languages."""
        ext = language_config.file_extension
        
        line = 7 if language_config.language == "python" else \
               9 if language_config.language == "javascript" else \
               11
        
        result = await navigation_service.get_completions(
            file=f"main{ext}",
            line=line,
            column=10
        )

        for completion in result.completions:
            # Required fields
            assert hasattr(completion, "text"), \
                f"Completion should have text for {language_config.language}"
            assert isinstance(completion.text, str), \
                f"Completion text should be string for {language_config.language}"
            assert len(completion.text) > 0, \
                f"Completion text should not be empty for {language_config.language}"
            
            # Optional fields (should exist but may be None)
            assert hasattr(completion, "kind"), \
                f"Completion should have kind field for {language_config.language}"
            assert hasattr(completion, "detail"), \
                f"Completion should have detail field for {language_config.language}"
            assert hasattr(completion, "documentation"), \
                f"Completion should have documentation field for {language_config.language}"
            assert hasattr(completion, "sort_text"), \
                f"Completion should have sort_text field for {language_config.language}"
            
            # Validate optional fields if present
            if completion.kind is not None:
                assert isinstance(completion.kind, str), \
                    f"Completion kind should be string or None for {language_config.language}"
            
            if completion.detail is not None:
                assert isinstance(completion.detail, str), \
                    f"Completion detail should be string or None for {language_config.language}"
            
            if completion.documentation is not None:
                assert isinstance(completion.documentation, str), \
                    f"Completion documentation should be string or None for {language_config.language}"
            
            if completion.sort_text is not None:
                assert isinstance(completion.sort_text, str), \
                    f"Completion sort_text should be string or None for {language_config.language}"

    async def test_completions_text_is_valid(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that completion text values are valid across all languages."""
        ext = language_config.file_extension
        
        line = 7 if language_config.language == "python" else \
               9 if language_config.language == "javascript" else \
               11
        
        result = await navigation_service.get_completions(
            file=f"main{ext}",
            line=line,
            column=10
        )

        for completion in result.completions:
            # Text should be non-empty string
            assert isinstance(completion.text, str), \
                f"Text should be string for {language_config.language}"
            assert len(completion.text) > 0, \
                f"Text should not be empty for {language_config.language}"
            
            # Should not contain weird characters
            assert "\n" not in completion.text, \
                f"Text should not have newlines for {language_config.language}"
            assert "\r" not in completion.text, \
                f"Text should not have carriage returns for {language_config.language}"
            assert "\t" not in completion.text, \
                f"Text should not have tabs for {language_config.language}"

    async def test_completions_at_different_positions(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test completions work at different positions in the file."""
        ext = language_config.file_extension
        
        # Try completions at start of function
        line1 = 6 if language_config.language == "python" else \
                8 if language_config.language == "javascript" else \
                10
        
        result1 = await navigation_service.get_completions(
            file=f"main{ext}",
            line=line1,
            column=5
        )
        
        assert isinstance(result1, CompletionsResult), \
            f"Should return CompletionsResult at position 1 for {language_config.language}"
        
        # Try completions later in function
        line2 = 10 if language_config.language == "python" else \
                12 if language_config.language == "javascript" else \
                14
        
        result2 = await navigation_service.get_completions(
            file=f"main{ext}",
            line=line2,
            column=5
        )
        
        assert isinstance(result2, CompletionsResult), \
            f"Should return CompletionsResult at position 2 for {language_config.language}"

    async def test_completions_in_different_files(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test completions work in different files across all languages."""
        ext = language_config.file_extension
        
        # Test completions in models file
        line = 10 if language_config.language == "python" else \
               12 if language_config.language == "javascript" else \
               11
        
        result = await navigation_service.get_completions(
            file=f"models{ext}",
            line=line,
            column=8
        )
        
        assert isinstance(result, CompletionsResult), \
            f"Should return CompletionsResult in models file for {language_config.language}"
        
        # Test completions in services file
        line2 = 8 if language_config.language == "python" else \
                10 if language_config.language == "javascript" else \
                9
        
        result2 = await navigation_service.get_completions(
            file=f"services{ext}",
            line=line2,
            column=8
        )
        
        assert isinstance(result2, CompletionsResult), \
            f"Should return CompletionsResult in services file for {language_config.language}"

    async def test_no_completions_returns_empty_result(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that positions with no completions return empty result, not error."""
        ext = language_config.file_extension
        
        # Try to get completions at line 1 (comment/empty)
        result = await navigation_service.get_completions(
            file=f"models{ext}",
            line=1,
            column=1
        )

        # Should return CompletionsResult (may be empty or may have some completions)
        assert isinstance(result, CompletionsResult), \
            f"Should return CompletionsResult even with no completions for {language_config.language}"
        assert isinstance(result.completions, list), \
            f"completions should be a list for {language_config.language}"
        # If empty, counts should be zero
        if len(result.completions) == 0:
            assert result.total_count == 0, \
                f"total_count should be 0 when empty for {language_config.language}"
            assert result.returned_count == 0, \
                f"returned_count should be 0 when empty for {language_config.language}"

    async def test_completions_without_nvim_raises_error(
        self, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that get_completions without Neovim raises error."""
        ext = language_config.file_extension
        service = NavigationService(nvim_client=None, project_path=str(language_project_dir))

        with pytest.raises(RuntimeError) as exc_info:
            await service.get_completions(file=f"main{ext}", line=5, column=9)

        assert "neovim" in str(exc_info.value).lower(), \
            f"Error should mention Neovim for {language_config.language}"

    async def test_completions_with_relative_path(
        self, navigation_service, language_config: LanguageTestConfig
    ):
        """Test completions work with relative file paths across all languages."""
        ext = language_config.file_extension
        
        line = 7 if language_config.language == "python" else \
               9 if language_config.language == "javascript" else \
               11
        
        # Use relative path
        result = await navigation_service.get_completions(
            file=f"main{ext}",
            line=line,
            column=9
        )

        assert isinstance(result, CompletionsResult), \
            f"Relative path should work for {language_config.language}"

    async def test_completions_structure_consistency(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that completion structure is consistent across all languages."""
        ext = language_config.file_extension
        
        line = 7 if language_config.language == "python" else \
               9 if language_config.language == "javascript" else \
               11
        
        result = await navigation_service.get_completions(
            file=f"main{ext}",
            line=line,
            column=10
        )

        # All completions should have same structure
        for completion in result.completions:
            # Check all expected attributes exist
            assert hasattr(completion, "text"), \
                f"Missing text attribute for {language_config.language}"
            assert hasattr(completion, "kind"), \
                f"Missing kind attribute for {language_config.language}"
            assert hasattr(completion, "detail"), \
                f"Missing detail attribute for {language_config.language}"
            assert hasattr(completion, "documentation"), \
                f"Missing documentation attribute for {language_config.language}"
            assert hasattr(completion, "sort_text"), \
                f"Missing sort_text attribute for {language_config.language}"
            
            # Verify types
            assert isinstance(completion.text, str), \
                f"text should be str for {language_config.language}"
            assert completion.kind is None or isinstance(completion.kind, str), \
                f"kind should be str or None for {language_config.language}"
            assert completion.detail is None or isinstance(completion.detail, str), \
                f"detail should be str or None for {language_config.language}"
            assert completion.documentation is None or isinstance(completion.documentation, str), \
                f"documentation should be str or None for {language_config.language}"
            assert completion.sort_text is None or isinstance(completion.sort_text, str), \
                f"sort_text should be str or None for {language_config.language}"

    async def test_completions_with_longer_wait(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that completions work after LSP has fully initialized."""
        ext = language_config.file_extension
        
        # Give LSP extra time to fully initialize
        import asyncio
        await asyncio.sleep(2)
        
        line = 7 if language_config.language == "python" else \
               9 if language_config.language == "javascript" else \
               11
        
        result = await navigation_service.get_completions(
            file=f"main{ext}",
            line=line,
            column=10
        )

        assert isinstance(result, CompletionsResult), \
            f"Should return CompletionsResult after init for {language_config.language}"
        
        # After proper initialization, structure should be correct
        for completion in result.completions:
            assert isinstance(completion, Completion), \
                f"Should return Completion objects for {language_config.language}"
            assert len(completion.text) > 0, \
                f"Completion text should not be empty for {language_config.language}"

    async def test_completions_max_results_limit(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that max_results parameter limits returned completions."""
        ext = language_config.file_extension
        
        line = 7 if language_config.language == "python" else \
               9 if language_config.language == "javascript" else \
               11
        
        # Request with small limit
        result = await navigation_service.get_completions(
            file=f"main{ext}",
            line=line,
            column=10,
            max_results=10
        )

        assert isinstance(result, CompletionsResult), \
            f"Should return CompletionsResult for {language_config.language}"
        
        # Check that limit was respected
        assert result.returned_count <= 10, \
            f"Should return at most 10 completions for {language_config.language}"
        assert len(result.completions) == result.returned_count, \
            f"returned_count should match actual list length for {language_config.language}"
        
        # If truncated, total should be greater than returned
        if result.truncated:
            assert result.total_count > result.returned_count, \
                f"If truncated, total should exceed returned for {language_config.language}"

    async def test_completions_metadata_consistency(
        self, navigation_service, language_project_dir, language_config: LanguageTestConfig
    ):
        """Test that CompletionsResult metadata is consistent."""
        ext = language_config.file_extension
        
        line = 7 if language_config.language == "python" else \
               9 if language_config.language == "javascript" else \
               11
        
        result = await navigation_service.get_completions(
            file=f"main{ext}",
            line=line,
            column=10
        )

        # Metadata should be consistent
        assert result.returned_count == len(result.completions), \
            f"returned_count should match list length for {language_config.language}"
        
        assert result.returned_count <= result.total_count, \
            f"returned_count should not exceed total_count for {language_config.language}"
        
        # truncated should be True if returned < total
        if result.returned_count < result.total_count:
            assert result.truncated, \
                f"truncated should be True when counts differ for {language_config.language}"
        
        # If not truncated, counts should match
        if not result.truncated:
            assert result.returned_count == result.total_count, \
                f"If not truncated, counts should match for {language_config.language}"

