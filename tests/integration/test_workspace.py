"""Integration tests for workspace operations.

Consolidated tests for:
- File operations: Create, read, save files
- Symbol extraction: Get document symbols with filtering
- Diagnostics: LSP diagnostics and error reporting

All tests run across Python, JavaScript, and Rust to verify language-agnostic behavior.
"""

from pathlib import Path

import pytest

from src.otter.neovim.client import NeovimClient
from src.otter.services.editing import EditingService
from src.otter.services.workspace import WorkspaceService
from tests.fixtures.language_configs import LanguageTestConfig

# ============================================================================
# Tests: File Operations
# ============================================================================


@pytest.mark.asyncio
class TestFileOperations:
    """Tests for creating, reading, and saving files."""

    @pytest.fixture
    async def editing_service(self, tmp_path):
        """Create editing service for file operations."""
        nvim_client = NeovimClient(project_path=str(tmp_path))
        await nvim_client.start()

        service = EditingService(nvim_client=nvim_client, project_path=str(tmp_path))

        yield service

        await nvim_client.stop()

    async def test_create_new_file_basic(self, editing_service, tmp_path):
        """Test creating a new file with content."""
        new_file = tmp_path / "new_file.py"

        result = await editing_service.create_new_file(
            file_path=str(new_file), content="print('Hello, World!')\n"
        )

        assert result.success
        assert result.file == str(new_file)
        assert new_file.exists()
        assert new_file.read_text() == "print('Hello, World!')\n"

    async def test_create_new_file_nested_directories(self, editing_service, tmp_path):
        """Test creating a file in nested directories (auto-creates dirs)."""
        new_file = tmp_path / "src" / "utils" / "helper.py"

        result = await editing_service.create_new_file(
            file_path=str(new_file), content="# Helper functions\n"
        )

        assert result.success
        assert new_file.exists()
        assert new_file.parent.exists()

    async def test_create_new_file_absolute_path(self, editing_service, tmp_path):
        """Test creating a file with absolute path."""
        new_file = tmp_path / "absolute.py"

        result = await editing_service.create_new_file(
            file_path=str(new_file.absolute()), content="# Absolute\n"
        )

        assert result.success
        assert new_file.exists()

    async def test_read_file_basic(self, temp_project_dir: Path):
        """Test reading a file."""
        # Create a test file
        test_file = temp_project_dir / "test.py"
        test_file.write_text("line1\nline2\nline3\n")

        nvim_client = NeovimClient(project_path=str(temp_project_dir))
        await nvim_client.start()

        workspace = WorkspaceService(
            nvim_client=nvim_client, project_path=str(temp_project_dir)
        )

        content = await workspace.read_file(str(test_file))

        assert content.total_lines == 3
        assert "line1" in content.content
        assert "line2" in content.content

        await nvim_client.stop()

    async def test_read_file_line_range(self, temp_project_dir: Path):
        """Test reading a specific line range."""
        test_file = temp_project_dir / "multiline.py"
        test_file.write_text("line1\nline2\nline3\nline4\nline5\n")

        nvim_client = NeovimClient(project_path=str(temp_project_dir))
        await nvim_client.start()

        workspace = WorkspaceService(
            nvim_client=nvim_client, project_path=str(temp_project_dir)
        )

        content = await workspace.read_file(str(test_file), start_line=2, end_line=4)

        assert "line2" in content.content
        assert "line3" in content.content
        assert "line4" in content.content
        assert "line1" not in content.content
        assert "line5" not in content.content

        await nvim_client.stop()


# ============================================================================
# Tests: Symbol Extraction
# ============================================================================


@pytest.mark.asyncio
class TestSymbols:
    """Tests for extracting and filtering document symbols."""

    @pytest.fixture
    async def workspace_service(self, nvim_client_with_lsp, language_project_dir):
        """Create workspace service with LSP ready."""
        return WorkspaceService(
            nvim_client=nvim_client_with_lsp, project_path=str(language_project_dir)
        )

    async def test_get_all_symbols(
        self,
        workspace_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test getting all symbols from a file."""
        ext = language_config.file_extension

        result = await workspace_service.get_symbols(
            file=str(language_project_dir / f"models{ext}")
        )

        assert result.total_count > 0
        assert len(result.symbols) > 0
        assert result.file.endswith(f"models{ext}")
        assert result.language == language_config.language

    async def test_symbols_have_correct_types(
        self,
        workspace_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test that symbols have correct types."""
        ext = language_config.file_extension

        result = await workspace_service.get_symbols(
            file=str(language_project_dir / f"models{ext}")
        )

        for symbol in result.symbols:
            assert symbol.name
            assert symbol.type in [
                "class",
                "function",
                "method",
                "struct",
                "module",
                "variable",
                "field",
                "impl",
            ]
            assert symbol.line > 0

    async def test_symbols_include_children(
        self,
        workspace_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test that class symbols include methods as children."""
        ext = language_config.file_extension

        result = await workspace_service.get_symbols(
            file=str(language_project_dir / f"models{ext}")
        )

        # Find User class
        user_symbols = [s for s in result.symbols if s.name == "User"]
        if user_symbols:
            user = user_symbols[0]
            # User class should have children (methods)
            if hasattr(user, "children"):
                assert len(user.children) > 0

    async def test_filter_by_symbol_type_class(
        self,
        workspace_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test filtering symbols by type (class)."""
        ext = language_config.file_extension
        symbol_type = "struct" if language_config.language == "rust" else "class"

        result = await workspace_service.get_symbols(
            file=str(language_project_dir / f"models{ext}"),
            symbol_types=[symbol_type],
        )

        for symbol in result.symbols:
            assert symbol.type in ["class", "struct"]

    async def test_filter_by_multiple_types(
        self,
        workspace_service,
        language_project_dir,
        language_config: LanguageTestConfig,
    ):
        """Test filtering by multiple symbol types."""
        ext = language_config.file_extension

        if language_config.language == "rust":
            types = ["struct", "function"]
        else:
            types = ["class", "function"]

        result = await workspace_service.get_symbols(
            file=str(language_project_dir / f"models{ext}"), symbol_types=types
        )

        assert result.total_count > 0
        found_types = {s.type for s in result.symbols}
        assert len(found_types.intersection(set(types))) > 0

    async def test_relative_path_works(
        self,
        workspace_service,
        language_config: LanguageTestConfig,
    ):
        """Test that relative paths work for getting symbols."""
        ext = language_config.file_extension

        result = await workspace_service.get_symbols(file=f"models{ext}")

        assert len(result.symbols) > 0

    async def test_empty_file_returns_empty_list(
        self, workspace_service, tmp_path, language_config: LanguageTestConfig
    ):
        """Test that empty files return empty symbol list."""
        ext = language_config.file_extension
        empty_file = tmp_path / f"empty{ext}"
        empty_file.write_text("")

        result = await workspace_service.get_symbols(file=str(empty_file))

        assert result.total_count == 0
        assert len(result.symbols) == 0


# ============================================================================
# Tests: Diagnostics
# ============================================================================


@pytest.mark.asyncio
class TestDiagnostics:
    """Tests for LSP diagnostics."""

    async def test_read_file_with_diagnostics_valid_code(self, temp_project_dir: Path):
        """Test reading a valid Python file with diagnostics."""
        test_file = temp_project_dir / "valid.py"
        test_file.write_text("def hello():\n    return 'hello'\n")

        nvim_client = NeovimClient(project_path=str(temp_project_dir))
        await nvim_client.start()

        workspace = WorkspaceService(
            nvim_client=nvim_client, project_path=str(temp_project_dir)
        )

        content = await workspace.read_file(str(test_file), include_diagnostics=True)

        # Valid code should have no diagnostics
        assert len(content.diagnostics) == 0

        await nvim_client.stop()

    async def test_read_file_with_diagnostics_syntax_error(
        self, temp_project_dir: Path
    ):
        """Test that LSP detects syntax errors."""
        test_file = temp_project_dir / "broken.py"
        test_file.write_text("def broken_function(:\n    pass")

        nvim_client = NeovimClient(project_path=str(temp_project_dir))
        await nvim_client.start()

        # Wait for LSP to analyze
        import asyncio

        await asyncio.sleep(2.0)

        workspace = WorkspaceService(
            nvim_client=nvim_client, project_path=str(temp_project_dir)
        )

        content = await workspace.read_file(str(test_file), include_diagnostics=True)

        # Should have at least one diagnostic for syntax error
        assert len(content.diagnostics) > 0, (
            "LSP should detect syntax errors. If this fails, check if pyright is installed and LSP is configured."
        )

        await nvim_client.stop()

    async def test_diagnostics_filtered_by_line_range(self, temp_project_dir: Path):
        """Test that diagnostics are filtered by line range."""
        test_file = temp_project_dir / "multi_error.py"
        test_file.write_text(
            "# Line 1\ndef bad1(:\n    pass\n\n# Line 5\ndef bad2(:\n    pass\n"
        )

        nvim_client = NeovimClient(project_path=str(temp_project_dir))
        await nvim_client.start()

        import asyncio

        await asyncio.sleep(2.0)

        workspace = WorkspaceService(
            nvim_client=nvim_client, project_path=str(temp_project_dir)
        )

        # Read only lines 1-3
        content = await workspace.read_file(
            str(test_file), start_line=1, end_line=3, include_diagnostics=True
        )

        # Should have diagnostics for syntax errors on line 2
        assert len(content.diagnostics) > 0, (
            "Should have diagnostics for syntax errors on line 2"
        )

        # Diagnostics should only be for lines 1-3
        for diag in content.diagnostics:
            assert 1 <= diag.line <= 3

        await nvim_client.stop()
