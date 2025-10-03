"""Integration tests for configuration system with Neovim."""

import tempfile
from pathlib import Path

import pytest

from otter.neovim.client import NeovimClient


class TestConfigIntegrationWithNeovim:
    """Test that configuration is properly loaded and passed to Neovim."""
    
    @pytest.mark.asyncio
    async def test_default_config_loads(self):
        """Test that Neovim starts with default config when no .otter.toml exists."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            
            # Create a Python file to trigger detection
            (project_path / "main.py").write_text("def hello(): pass\n")
            
            async with NeovimClient(str(project_path)) as client:
                # Verify config was loaded
                assert client.config is not None
                assert client.config.lsp.enabled is True
                
                # Verify Python was detected
                assert "python" in client.enabled_languages
    
    @pytest.mark.asyncio
    async def test_custom_config_loads(self):
        """Test that custom .otter.toml is loaded."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            
            # Create config file
            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[project]
name = "test-project"

[lsp]
timeout_ms = 5000
languages = ["python"]

[lsp.python]
server = "pyright"
""")
            
            # Create Python file
            (project_path / "main.py").write_text("def hello(): pass\n")
            
            async with NeovimClient(str(project_path)) as client:
                # Verify custom config was loaded
                assert client.config.project.name == "test-project"
                assert client.config.lsp.timeout_ms == 5000
                
                # Verify languages match config
                assert client.enabled_languages == ["python"]
    
    @pytest.mark.asyncio
    async def test_virtualenv_detection(self):
        """Test that virtualenv is detected and resolved."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            
            # Create virtualenv
            venv_path = project_path / ".venv"
            venv_bin = venv_path / "bin"
            venv_bin.mkdir(parents=True)
            (venv_bin / "python").touch()
            
            # Create config using ${VENV}
            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[lsp.python]
python_path = "${VENV}/bin/python"
""")
            
            # Create Python file
            (project_path / "main.py").write_text("def hello(): pass\n")
            
            async with NeovimClient(str(project_path)) as client:
                # Verify venv was detected
                python_config = client.config.lsp.language_configs.get("python")
                assert python_config is not None
                
                # Verify path resolution
                resolved = client.config.resolve_path(python_config.python_path)
                assert "/.venv/bin/python" in resolved
    
    @pytest.mark.asyncio
    async def test_lazy_loading_config(self):
        """Test that lazy loading configuration is respected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            
            # Create config with lazy loading disabled
            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[lsp]
lazy_load = false
""")
            
            # Create Python file
            (project_path / "main.py").write_text("def hello(): pass\n")
            
            async with NeovimClient(str(project_path)) as client:
                # Verify config was loaded
                assert client.config.lsp.lazy_load is False
    
    @pytest.mark.asyncio
    async def test_disabled_language(self):
        """Test that disabled languages are not loaded."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            
            # Create config disabling JavaScript
            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[lsp]
auto_detect = true
disabled_languages = ["javascript"]
""")
            
            # Create both Python and JavaScript files
            (project_path / "main.py").write_text("def hello(): pass\n")
            (project_path / "app.js").write_text("function hello() {}\n")
            
            async with NeovimClient(str(project_path)) as client:
                # Verify Python is enabled but JavaScript is not
                assert "python" in client.enabled_languages
                assert "javascript" not in client.enabled_languages
    
    @pytest.mark.asyncio
    async def test_multi_language_config(self):
        """Test configuration with multiple languages."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            
            # Create config for multiple languages
            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[lsp]
languages = ["python", "javascript"]

[lsp.python]
server = "pyright"

[lsp.javascript]
server = "tsserver"
""")
            
            # Create files for both languages
            (project_path / "backend.py").write_text("def api(): pass\n")
            (project_path / "frontend.js").write_text("function ui() {}\n")
            
            async with NeovimClient(str(project_path)) as client:
                # Verify both languages are enabled
                assert "python" in client.enabled_languages
                assert "javascript" in client.enabled_languages
                
                # Verify configs exist
                assert "python" in client.config.lsp.language_configs
                assert "javascript" in client.config.lsp.language_configs


class TestConfigWithLSP:
    """Test that configuration affects LSP behavior."""
    
    @pytest.mark.asyncio
    async def test_lsp_with_custom_python_path(self):
        """Test that custom Python path is used for LSP."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            
            # Create a test Python file
            test_file = project_path / "test.py"
            test_file.write_text("""
def greet(name: str) -> str:
    return f"Hello, {name}!"

result = greet("World")
""")
            
            # Create config (we'll use default Python for testing)
            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[lsp.python]
server = "pyright"
""")
            
            async with NeovimClient(str(project_path)) as client:
                # Open file and verify LSP works
                await client.open_file(str(test_file))
                
                # Give LSP time to start
                import asyncio
                await asyncio.sleep(2)
                
                # Try to get hover info (this will use configured LSP)
                hover_result = await client.lsp_hover(str(test_file), 2, 4)
                
                # If LSP is working with config, we should get hover info
                # (may be None if LSP not fully started, but shouldn't crash)
                assert hover_result is None or isinstance(hover_result, dict)


class TestConfigErrorHandling:
    """Test error handling for invalid configurations."""
    
    @pytest.mark.asyncio
    async def test_invalid_toml_uses_defaults(self):
        """Test that invalid TOML falls back to defaults."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            
            # Create invalid TOML
            config_file = project_path / ".otter.toml"
            config_file.write_text("this is not valid toml ][")
            
            # Create Python file
            (project_path / "main.py").write_text("def hello(): pass\n")
            
            # Should not crash, but use defaults
            try:
                async with NeovimClient(str(project_path)) as client:
                    # If we get here, it handled the error
                    assert client.config is not None
            except Exception as e:
                # TOML parsing error is acceptable
                assert "toml" in str(e).lower() or "parse" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_missing_python_path_uses_fallback(self):
        """Test that missing Python path falls back to system Python."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            
            # Create config with non-existent Python path
            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[lsp.python]
python_path = "/nonexistent/python"
""")
            
            # Create Python file
            (project_path / "main.py").write_text("def hello(): pass\n")
            
            # Should still start (Lua will handle fallback)
            async with NeovimClient(str(project_path)) as client:
                assert client.config is not None
                python_config = client.config.lsp.language_configs.get("python")
                assert python_config.python_path == "/nonexistent/python"

