"""Unit tests for LSP bootstrapping."""

from otter.bootstrap.lsp_installer import (
    LSPServerStatus,
    check_lsp_server,
    is_command_available,
    check_prerequisites,
)


class TestCommandAvailability:
    """Test command availability checking."""

    def test_python_is_available(self):
        """Test that python is available (since we're running tests)."""
        assert is_command_available("python") or is_command_available("python3")

    def test_nonexistent_command(self):
        """Test that nonexistent commands return False."""
        assert not is_command_available("this_command_definitely_does_not_exist_12345")


class TestPrerequisites:
    """Test prerequisite checking."""

    def test_check_prerequisites_returns_dict(self):
        """Test that prerequisite check returns proper dict."""
        prereqs = check_prerequisites()

        assert isinstance(prereqs, dict)
        assert "npm" in prereqs
        assert "pip" in prereqs
        assert "rustup" in prereqs
        assert "go" in prereqs

        # All values should be boolean
        for value in prereqs.values():
            assert isinstance(value, bool)


class TestLSPServerChecking:
    """Test LSP server status checking."""

    def test_check_python_lsp(self):
        """Test checking Python LSP server."""
        server = check_lsp_server("python")

        assert server.name == "pyright"
        assert server.status in [LSPServerStatus.INSTALLED, LSPServerStatus.MISSING]

    def test_check_javascript_lsp(self):
        """Test checking JavaScript LSP server."""
        server = check_lsp_server("javascript")

        assert server.name == "typescript-language-server"
        assert server.status in [LSPServerStatus.INSTALLED, LSPServerStatus.MISSING]

    def test_check_rust_lsp(self):
        """Test checking Rust LSP server."""
        server = check_lsp_server("rust")

        assert server.name == "rust-analyzer"
        assert server.status in [LSPServerStatus.INSTALLED, LSPServerStatus.MISSING]

    def test_check_specific_server(self):
        """Test checking a specific server by name."""
        # Python has multiple servers, check pylsp specifically
        server = check_lsp_server("python", "pylsp")

        assert server.name == "pylsp"
        assert server.status in [LSPServerStatus.INSTALLED, LSPServerStatus.MISSING]

    def test_unknown_language(self):
        """Test checking unknown language returns installed status."""
        server = check_lsp_server("unknown_language_xyz")

        assert server.status == LSPServerStatus.INSTALLED


class TestAutoInstallConfig:
    """Test auto-install configuration."""

    def test_can_disable_auto_install(self):
        """Test that auto-install can be disabled in config."""
        from otter.config import load_config
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[lsp]
auto_install = false
""")

            config = load_config(project_path)
            assert config.lsp.auto_install is False

    def test_auto_install_defaults_to_true(self):
        """Test that auto-install defaults to true."""
        from otter.config import load_config
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            config = load_config(project_path)
            assert config.lsp.auto_install is True
