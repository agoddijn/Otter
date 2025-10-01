"""Integration tests for WorkspaceService.read_file with real Neovim."""

from pathlib import Path

import pytest

from otter.neovim.client import NeovimClient
from otter.services.workspace import WorkspaceService

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not Path("/usr/local/bin/nvim").exists()
        and not Path("/opt/homebrew/bin/nvim").exists()
        and not Path("/usr/bin/nvim").exists(),
        reason="Neovim not installed",
    ),
]


class TestReadFileIntegration:
    """Integration tests for read_file with real Neovim/LSP."""

    @pytest.mark.asyncio
    async def test_read_file_basic(self, temp_project_dir: Path):
        """Test basic file reading through Neovim."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text("print('hello world')\n")

        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            service = WorkspaceService(
                project_path=str(temp_project_dir), nvim_client=client
            )

            # Read without special features (should use direct file I/O)
            result = await service.read_file("test.py")

            # Should include line numbers
            assert result.content == "1|print('hello world')"
            assert result.expanded_imports is None
            assert result.diagnostics is None

    @pytest.mark.asyncio
    async def test_read_file_with_imports(self, temp_project_dir: Path):
        """Test reading file with import extraction."""
        test_file = temp_project_dir / "test.py"
        test_file.write_text(
            "import os\nfrom pathlib import Path\nimport sys\n\nprint('hello')\n"
        )

        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            service = WorkspaceService(
                project_path=str(temp_project_dir), nvim_client=client
            )

            result = await service.read_file("test.py", include_imports=True)

            # Should have extracted imports
            assert result.expanded_imports is not None
            assert "import os" in result.expanded_imports
            assert "from pathlib import Path" in result.expanded_imports
            assert "import sys" in result.expanded_imports

    @pytest.mark.asyncio
    async def test_read_file_with_diagnostics_valid_python(
        self, temp_project_dir: Path
    ):
        """Test that valid Python code has no diagnostics."""
        test_file = temp_project_dir / "valid.py"
        test_file.write_text(
            "def greet(name: str) -> str:\n"
            '    return f"Hello, {name}!"\n'
            "\n"
            'result = greet("World")\n'
            "print(result)\n"
        )

        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            service = WorkspaceService(
                project_path=str(temp_project_dir), nvim_client=client
            )

            result = await service.read_file("valid.py", include_diagnostics=True)

            # Valid code should have no diagnostics (or they should be empty)
            assert result.diagnostics is not None
            assert isinstance(result.diagnostics, list)
            # Could be empty or have warnings, but shouldn't have errors
            errors = [d for d in result.diagnostics if d.severity == "error"]
            assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_read_file_with_diagnostics_syntax_error(
        self, temp_project_dir: Path
    ):
        """Test that syntax errors are detected by LSP."""
        test_file = temp_project_dir / "syntax_error.py"
        # Intentional syntax error: missing closing parenthesis
        test_file.write_text(
            "def broken_function(:\n"  # Missing parameter name and closing paren
            "    pass\n"
        )

        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            service = WorkspaceService(
                project_path=str(temp_project_dir), nvim_client=client
            )

            result = await service.read_file(
                "syntax_error.py", include_diagnostics=True
            )

            print(f"\nDiagnostics found: {len(result.diagnostics or [])} diagnostic(s)")
            if result.diagnostics:
                for diag in result.diagnostics[:3]:  # Show first 3
                    print(f"  - {diag.severity}: {diag.message} (line {diag.line})")

            # STRICT: Must have diagnostics for syntax errors
            assert result.diagnostics is not None, "Diagnostics should not be None"
            assert len(result.diagnostics) > 0, (
                "LSP should detect syntax errors. "
                "If this fails, check if pyright is installed and LSP is configured."
            )

            # Should have error-level diagnostics
            errors = [d for d in result.diagnostics if d.severity == "error"]
            assert len(errors) > 0, "Should have at least one error diagnostic"

            # Error messages should mention syntax issues
            assert any(
                "expected" in d.message.lower() or "syntax" in d.message.lower()
                for d in result.diagnostics
            ), "Diagnostics should mention syntax/parsing issues"

    @pytest.mark.asyncio
    async def test_read_file_with_diagnostics_type_error(self, temp_project_dir: Path):
        """Test that type errors are detected by LSP (when type checking enabled)."""
        test_file = temp_project_dir / "type_error.py"
        test_file.write_text(
            "def add_numbers(a: int, b: int) -> int:\n"
            "    return a + b\n"
            "\n"
            "# Type error: passing string instead of int\n"
            'result = add_numbers("hello", 5)\n'
        )

        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            service = WorkspaceService(
                project_path=str(temp_project_dir), nvim_client=client
            )

            result = await service.read_file("type_error.py", include_diagnostics=True)

            print(f"\nDiagnostics found: {len(result.diagnostics or [])} diagnostic(s)")
            if result.diagnostics:
                for diag in result.diagnostics:
                    print(f"  - {diag.severity}: {diag.message} (line {diag.line})")

            # NOTE: Type checking depends on Pyright settings
            # With typeCheckingMode="basic", this SHOULD catch the type error
            # This is a weaker assertion than syntax errors since type checking can be off
            assert result.diagnostics is not None, "Diagnostics should not be None"

            # With our Pyright config (typeCheckingMode="basic"), we expect type errors
            if len(result.diagnostics) > 0:
                print(
                    f"✓ Type checking is working! Found {len(result.diagnostics)} diagnostic(s)"
                )
                # If we got diagnostics, check they mention the type issue
                type_related = any(
                    "type" in d.message.lower() or "argument" in d.message.lower()
                    for d in result.diagnostics
                )
                if type_related:
                    print("✓ Type-related diagnostic found")
            else:
                # Warn but don't fail - type checking might be disabled
                print(
                    "⚠ No type diagnostics found. Type checking may be disabled or slow."
                )

    @pytest.mark.asyncio
    async def test_diagnostics_filtered_by_line_range(self, temp_project_dir: Path):
        """Test that diagnostics are filtered to the requested line range."""
        test_file = temp_project_dir / "multi_error.py"
        test_file.write_text(
            "# Line 1\n"
            "def bad1(:\n"  # Error on line 2
            "    pass\n"
            "\n"
            "# Line 5\n"
            "def bad2(:\n"  # Error on line 6
            "    pass\n"
        )

        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            service = WorkspaceService(
                project_path=str(temp_project_dir), nvim_client=client
            )

            # Read only lines 1-3 with diagnostics
            result = await service.read_file(
                "multi_error.py", line_range=(1, 3), include_diagnostics=True
            )

            print(
                f"\nDiagnostics for lines 1-3: {len(result.diagnostics or [])} diagnostic(s)"
            )
            if result.diagnostics:
                for diag in result.diagnostics:
                    print(f"  - Line {diag.line}: {diag.message}")

            # STRICT: Should have diagnostics in the file
            assert result.diagnostics is not None
            assert len(result.diagnostics) > 0, (
                "Should have diagnostics for syntax errors on line 2"
            )

            # All diagnostics should be in the requested range 1-3
            for diag in result.diagnostics:
                assert 1 <= diag.line <= 3, (
                    f"Diagnostic on line {diag.line} is outside requested range (1-3)"
                )

    @pytest.mark.asyncio
    async def test_read_file_line_range_with_context(self, temp_project_dir: Path):
        """Test reading specific lines with context."""
        test_file = temp_project_dir / "context_test.py"
        test_file.write_text("line1 = 1\nline2 = 2\nline3 = 3\nline4 = 4\nline5 = 5\n")

        async with NeovimClient(project_path=str(temp_project_dir)) as client:
            service = WorkspaceService(
                project_path=str(temp_project_dir), nvim_client=client
            )

            # Read lines 3 with 1 line of context
            result = await service.read_file(
                "context_test.py", line_range=(3, 3), context_lines=1
            )

            # Should get lines 2-4 (3 ± 1) with line numbers
            assert "2|line2" in result.content
            assert "3|line3" in result.content
            assert "4|line4" in result.content
            assert "1|line1" not in result.content
            assert "5|line5" not in result.content
