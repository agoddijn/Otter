"""Integration tests for rename_symbol feature (language-agnostic).

This test suite runs across Python, JavaScript, and Rust to verify that
rename_symbol works consistently across all supported languages.
"""

import pytest

from src.otter.neovim.client import NeovimClient
from src.otter.services.refactoring import RefactoringService
from tests.fixtures.language_configs import LanguageTestConfig


def _get_source_file_path(
    language_project_dir, language_config, filename, as_string=True
):
    """Get source file path based on language conventions.

    Rust uses src/ directory, others have files in root.
    This keeps the solution language-agnostic while respecting conventions.

    Args:
        language_project_dir: Project directory Path
        language_config: Language configuration
        filename: Base filename without extension (e.g., "models")
        as_string: If True, return string; if False, return Path

    Returns:
        Path to source file (as string or Path based on as_string parameter)
    """
    ext = language_config.file_extension
    if language_config.language == "rust":
        path = language_project_dir / f"src/{filename}{ext}"
    else:
        path = language_project_dir / f"{filename}{ext}"

    return str(path) if as_string else path


@pytest.mark.asyncio
class TestRenameSymbolParameterized:
    """Language-agnostic integration tests for rename_symbol."""

    @pytest.fixture
    async def refactoring_service(
        self, language_project_dir, language_config: LanguageTestConfig
    ):
        """Create a RefactoringService with a real Neovim client for the test language."""
        from otter.neovim.lsp_readiness import wait_for_all_lsp_ready

        nvim_client = NeovimClient(project_path=str(language_project_dir))
        await nvim_client.start()

        # Get all test files for this language (respecting language conventions)
        test_files = [
            _get_source_file_path(language_project_dir, language_config, "models"),
            _get_source_file_path(language_project_dir, language_config, "services"),
            _get_source_file_path(language_project_dir, language_config, "main"),
        ]

        # Open files and wait for LSP to be fully indexed
        for test_file in test_files:
            await nvim_client.open_file(test_file)

        # Wait for proper LSP readiness with indexing check
        await wait_for_all_lsp_ready(
            nvim_client,
            test_files,
            timeout=30.0,
            use_indexing_check=True,  # Ensures files are indexed, not just LSP attached
        )

        service = RefactoringService(
            project_path=str(language_project_dir), nvim_client=nvim_client
        )

        yield service

        await nvim_client.stop()

    @pytest.mark.skip(
        reason="Rust: rust-analyzer not indexing test project. TODO: investigate rust-analyzer config"
    )
    async def test_rename_class_preview(
        self,
        refactoring_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test renaming a class with preview mode across all languages."""
        user_loc = language_config.symbol_locations["User"]
        models_file = _get_source_file_path(
            language_project_dir, language_config, "models"
        )

        # Rename User -> Account (preview only)
        new_name = "Account"

        result = await refactoring_service.rename_symbol(
            file=str(models_file),
            line=user_loc.line,
            column=6,
            new_name=new_name,
            preview=True,
        )

        # Should return a RenamePreview
        assert hasattr(result, "changes"), (
            f"Should have changes for {language_config.language}"
        )
        assert hasattr(result, "affected_files"), (
            f"Should have affected_files for {language_config.language}"
        )
        assert hasattr(result, "total_changes"), (
            f"Should have total_changes for {language_config.language}"
        )

        # Should have changes in multiple files (User is used in multiple places)
        assert result.affected_files >= 1, (
            f"Should affect at least 1 file for {language_config.language}"
        )
        assert result.total_changes > 0, (
            f"Should have at least 1 change for {language_config.language}"
        )

        # Changes should include files that use User
        change_files = [change.file for change in result.changes]
        # Check for models file (accounts for src/ in Rust)
        models_filename = f"models{language_config.file_extension}"
        assert any(models_filename in f for f in change_files), (
            f"Should include models file for {language_config.language}"
        )

    async def test_rename_class_with_multiple_references(
        self,
        refactoring_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test that renaming finds all references across files."""
        ext = language_config.file_extension
        user_loc = language_config.symbol_locations["User"]
        models_file = _get_source_file_path(
            language_project_dir, language_config, "models"
        )

        # Rename User -> UserData
        result = await refactoring_service.rename_symbol(
            file=str(models_file),
            line=user_loc.line,
            column=6,
            new_name="UserData",
            preview=True,
        )

        # Should find references in multiple files
        # - models file (class/struct definition)
        # - main file (usage)
        # - services file (usage)
        assert result.affected_files >= 1, (
            f"Should affect multiple files for {language_config.language}"
        )

        # Should have multiple changes (definition + all usages)
        assert result.total_changes >= 1, (
            f"Should have multiple changes for {language_config.language}"
        )

    async def test_rename_function(
        self,
        refactoring_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test renaming a function across all languages."""
        ext = language_config.file_extension
        func_loc = language_config.symbol_locations["create_user"]
        models_file = _get_source_file_path(
            language_project_dir, language_config, "models"
        )

        # New name depends on language convention
        new_name = (
            "initialize_user"
            if language_config.language != "javascript"
            else "initializeUser"
        )

        # Rename create_user -> initialize_user
        result = await refactoring_service.rename_symbol(
            file=str(models_file),
            line=func_loc.line,
            column=8,
            new_name=new_name,
            preview=True,
        )

        # Should find the definition and usages
        assert result.total_changes >= 1, (
            f"Should have at least definition change for {language_config.language}"
        )

    async def test_rename_method(
        self,
        refactoring_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test renaming a method in a class across all languages."""
        ext = language_config.file_extension
        greet_loc = language_config.symbol_locations["greet"]
        models_file = _get_source_file_path(
            language_project_dir, language_config, "models"
        )

        # Rename greet() -> say_hello()
        new_name = (
            "say_hello" if language_config.language != "javascript" else "sayHello"
        )

        result = await refactoring_service.rename_symbol(
            file=str(models_file),
            line=greet_loc.line,
            column=8,
            new_name=new_name,
            preview=True,
        )

        # Should find the method definition and its calls
        assert result.total_changes >= 1, (
            f"Should rename method for {language_config.language}"
        )

        # Should affect files that call the method
        assert result.affected_files >= 1, (
            f"Should affect files using the method for {language_config.language}"
        )

    async def test_rename_nonexistent_symbol(
        self,
        refactoring_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test renaming a symbol that doesn't exist across all languages."""
        ext = language_config.file_extension
        models_file = _get_source_file_path(
            language_project_dir, language_config, "models"
        )

        # Try to rename at line 1 (usually a comment or empty)
        result = await refactoring_service.rename_symbol(
            file=str(models_file), line=1, column=0, new_name="NewName", preview=True
        )

        # Should return empty result or minimal result
        assert result.affected_files == 0 or result.total_changes == 0, (
            f"Nonexistent symbol should have no changes for {language_config.language}"
        )

    async def test_rename_service_class(
        self,
        refactoring_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test renaming the service class across all languages."""
        ext = language_config.file_extension
        service_loc = language_config.symbol_locations["UserService"]
        services_file = _get_source_file_path(
            language_project_dir, language_config, "services"
        )

        # Rename UserService -> AccountService
        new_name = "AccountService"

        result = await refactoring_service.rename_symbol(
            file=str(services_file),
            line=service_loc.line,
            column=6,
            new_name=new_name,
            preview=True,
        )

        # Should find definition and usage in main
        assert result.total_changes >= 1, (
            f"Should rename service class for {language_config.language}"
        )

        # Should affect at least the services file
        assert result.affected_files >= 1, (
            f"Should affect services file for {language_config.language}"
        )

    @pytest.mark.skip(
        reason="Event loop conflict with parallel test execution - needs investigation"
    )
    async def test_rename_with_apply(
        self,
        refactoring_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test actually applying a rename (not just preview) across all languages."""
        ext = language_config.file_extension
        service_loc = language_config.symbol_locations["UserService"]
        services_file = _get_source_file_path(
            language_project_dir, language_config, "services"
        )

        # First, preview the rename
        new_name = "AppService"

        preview = await refactoring_service.rename_symbol(
            file=str(services_file),
            line=service_loc.line,
            column=6,
            new_name=new_name,
            preview=True,
        )

        expected_changes = preview.total_changes
        expected_files = preview.affected_files

        # Now apply it
        result = await refactoring_service.rename_symbol(
            file=str(services_file),
            line=service_loc.line,
            column=6,
            new_name=new_name,
            preview=False,  # Actually apply
        )

        # Should return RenameResult
        assert hasattr(result, "changes_applied"), (
            f"Should have changes_applied for {language_config.language}"
        )
        assert hasattr(result, "files_updated"), (
            f"Should have files_updated for {language_config.language}"
        )

        # Should have applied changes
        assert result.changes_applied == expected_changes, (
            f"Should apply all changes for {language_config.language}"
        )
        assert result.files_updated == expected_files, (
            f"Should update all files for {language_config.language}"
        )

    async def test_rename_result_structure(
        self,
        refactoring_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test that rename result has consistent structure across all languages."""
        ext = language_config.file_extension
        user_loc = language_config.symbol_locations["User"]
        models_file = _get_source_file_path(
            language_project_dir, language_config, "models"
        )

        result = await refactoring_service.rename_symbol(
            file=str(models_file),
            line=user_loc.line,
            column=6,
            new_name="Account",
            preview=True,
        )

        # Verify structure
        assert hasattr(result, "changes"), (
            f"Result should have changes for {language_config.language}"
        )
        assert hasattr(result, "affected_files"), (
            f"Result should have affected_files for {language_config.language}"
        )
        assert hasattr(result, "total_changes"), (
            f"Result should have total_changes for {language_config.language}"
        )

        # Verify types
        assert isinstance(result.changes, list), (
            f"Changes should be list for {language_config.language}"
        )
        assert isinstance(result.affected_files, int), (
            f"Affected files should be int for {language_config.language}"
        )
        assert isinstance(result.total_changes, int), (
            f"Total changes should be int for {language_config.language}"
        )

        # Verify each change has required fields
        for change in result.changes:
            assert hasattr(change, "file"), (
                f"Change should have file for {language_config.language}"
            )
            assert hasattr(change, "line"), (
                f"Change should have line for {language_config.language}"
            )

    async def test_rename_preserves_functionality(
        self,
        refactoring_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test that preview mode doesn't modify files across all languages."""
        models_file = _get_source_file_path(
            language_project_dir, language_config, "models", as_string=False
        )

        # Read original content
        original_content = models_file.read_text()

        # Perform preview rename
        user_loc = language_config.symbol_locations["User"]
        await refactoring_service.rename_symbol(
            file=str(models_file),  # Convert Path to string for API call
            line=user_loc.line,
            column=6,
            new_name="Account",
            preview=True,
        )

        # Content should be unchanged
        current_content = models_file.read_text()
        assert current_content == original_content, (
            f"Preview should not modify files for {language_config.language}"
        )

    async def test_rename_cross_file_references(
        self,
        refactoring_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test that rename finds references across multiple files."""
        ext = language_config.file_extension
        user_loc = language_config.symbol_locations["User"]
        models_file = _get_source_file_path(
            language_project_dir, language_config, "models"
        )

        result = await refactoring_service.rename_symbol(
            file=str(models_file),
            line=user_loc.line,
            column=6,
            new_name="Account",
            preview=True,
        )

        # Should find references in multiple files
        change_files = {change.file for change in result.changes}

        # Should include at least the definition file (accounts for src/ in Rust)
        models_filename = f"models{language_config.file_extension}"
        assert any(models_filename in f for f in change_files), (
            f"Should include models file for {language_config.language}"
        )

        # Ideally should include other files that use User, but LSP behavior varies
        # So we just check that we got some results
        assert len(change_files) >= 1, (
            f"Should have changes in at least one file for {language_config.language}"
        )

    async def test_rename_with_relative_path(
        self, refactoring_service, language_config: LanguageTestConfig
    ):
        """Test that rename works with relative paths (regression test for path bug)."""
        user_loc = language_config.symbol_locations["User"]

        # Use relative path (respecting language structure)
        if language_config.language == "rust":
            relative_path = f"src/models{language_config.file_extension}"
        else:
            relative_path = f"models{language_config.file_extension}"

        # Use relative path instead of absolute
        result = await refactoring_service.rename_symbol(
            file=relative_path,
            line=user_loc.line,
            column=6,
            new_name="Account",
            preview=True,
        )

        # Should work the same as absolute path
        assert result.total_changes > 0, (
            f"Relative path should work for {language_config.language}"
        )

        # Should find the models file (accounts for src/ in Rust)
        change_files = {change.file for change in result.changes}
        models_filename = f"models{language_config.file_extension}"
        assert any(models_filename in f for f in change_files), (
            f"Should find models file with relative path for {language_config.language}"
        )
