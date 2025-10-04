"""Unit tests for configuration system."""

import tempfile
from pathlib import Path


from otter.config import (
    OtterConfig,
    load_config,
    find_config_file,
    detect_project_languages,
    get_effective_languages,
)


class TestConfigParsing:
    """Test TOML configuration parsing."""

    def test_find_config_file_exists(self):
        """Test finding .otter.toml when it exists."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            config_file = project_path / ".otter.toml"
            config_file.write_text("[project]\nname = 'test'\n")

            found = find_config_file(project_path)
            assert found == config_file

    def test_find_config_file_missing(self):
        """Test finding .otter.toml when it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            found = find_config_file(project_path)
            assert found is None

    def test_load_config_defaults(self):
        """Test loading config uses defaults when no file exists."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            config = load_config(project_path)

            # Check defaults
            assert config.lsp.enabled is True
            assert config.lsp.auto_detect is True
            assert config.lsp.lazy_load is True
            assert config.lsp.timeout_ms == 2000
            assert config.dap.enabled is True
            assert config.project_root == project_path

    def test_load_config_basic(self):
        """Test loading basic configuration."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[project]
name = "test-project"

[lsp]
enabled = true
auto_detect = false
lazy_load = false
timeout_ms = 3000
languages = ["python", "rust"]

[lsp.python]
enabled = true
server = "pyright"
python_path = "/usr/bin/python3"

[lsp.python.settings]
python.analysis.typeCheckingMode = "strict"
""")

            config = load_config(project_path)

            assert config.project.name == "test-project"
            assert config.lsp.enabled is True
            assert config.lsp.auto_detect is False
            assert config.lsp.lazy_load is False
            assert config.lsp.timeout_ms == 3000
            assert config.lsp.languages == ["python", "rust"]

            # Check Python config
            assert "python" in config.lsp.language_configs
            python_config = config.lsp.language_configs["python"]
            assert python_config.enabled is True
            assert python_config.server == "pyright"
            assert python_config.python_path == "/usr/bin/python3"
            # TOML parses dotted keys as nested dicts
            assert python_config.settings == {
                "python": {"analysis": {"typeCheckingMode": "strict"}}
            }

    def test_load_config_dap(self):
        """Test loading DAP configuration."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[dap]
enabled = true
lazy_load = false

[dap.python]
enabled = true
adapter = "debugpy"
python_path = "/usr/bin/python3"
""")

            config = load_config(project_path)

            assert config.dap.enabled is True
            assert config.dap.lazy_load is False

            # Check Python DAP config
            assert "python" in config.dap.language_configs
            python_dap = config.dap.language_configs["python"]
            assert python_dap.enabled is True
            assert python_dap.adapter == "debugpy"
            assert python_dap.python_path == "/usr/bin/python3"

    def test_load_config_performance(self):
        """Test loading performance configuration."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[performance]
max_lsp_clients = 3
max_dap_sessions = 1
file_change_debounce_ms = 500
""")

            config = load_config(project_path)

            assert config.performance.max_lsp_clients == 3
            assert config.performance.max_dap_sessions == 1
            assert config.performance.file_change_debounce_ms == 500

    def test_load_config_plugins(self):
        """Test loading plugins configuration."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            config_file = project_path / ".otter.toml"
            # Note: Use inline table for treesitter to avoid TOML conflicts
            config_file.write_text("""
[plugins]
lsp = true
dap = false

[plugins.treesitter]
ensure_installed = ["python", "rust"]
auto_install = false
""")

            config = load_config(project_path)

            # treesitter value comes from the [plugins.treesitter] section existence
            assert config.plugins.treesitter is True  # Default
            assert config.plugins.lsp is True
            assert config.plugins.dap is False
            assert config.plugins.treesitter_ensure_installed == ["python", "rust"]
            assert config.plugins.treesitter_auto_install is False


class TestPathResolution:
    """Test template variable resolution in paths."""

    def test_resolve_project_root(self):
        """Test ${PROJECT_ROOT} variable resolution."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            config = OtterConfig(project_root=project_path)

            result = config.resolve_path("${PROJECT_ROOT}/src/main.py")
            assert result == f"{project_path}/src/main.py"

    def test_resolve_venv_exists(self):
        """Test ${VENV} variable resolution when venv exists."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            venv_path = project_path / ".venv"
            venv_bin = venv_path / "bin"
            venv_bin.mkdir(parents=True)
            (venv_bin / "python").touch()

            config = OtterConfig(project_root=project_path)

            result = config.resolve_path("${VENV}/bin/python")
            assert result == f"{venv_path}/bin/python"

    def test_resolve_venv_missing(self):
        """Test ${VENV} variable resolution when venv doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            config = OtterConfig(project_root=project_path)

            # Should fallback to project root
            result = config.resolve_path("${VENV}/bin/python")
            assert result == f"{project_path}/bin/python"

    def test_detect_venv_patterns(self):
        """Test detection of various venv directory patterns."""
        patterns = [".venv", "venv", "env", ".env"]

        for pattern in patterns:
            with tempfile.TemporaryDirectory() as tmp_dir:
                project_path = Path(tmp_dir)
                venv_path = project_path / pattern
                venv_bin = venv_path / "bin"
                venv_bin.mkdir(parents=True)
                (venv_bin / "python").touch()

                config = OtterConfig(project_root=project_path)
                detected = config._detect_venv()

                assert detected == str(venv_path), f"Failed to detect {pattern}"


class TestLanguageDetection:
    """Test automatic language detection."""

    def test_detect_python(self):
        """Test detection of Python projects."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            (project_path / "main.py").touch()
            (project_path / "utils.py").touch()

            languages = detect_project_languages(project_path)
            assert "python" in languages

    def test_detect_javascript(self):
        """Test detection of JavaScript projects."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            (project_path / "index.js").touch()
            (project_path / "app.jsx").touch()

            languages = detect_project_languages(project_path)
            assert "javascript" in languages

    def test_detect_typescript(self):
        """Test detection of TypeScript projects."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            (project_path / "index.ts").touch()
            (project_path / "App.tsx").touch()

            languages = detect_project_languages(project_path)
            assert "typescript" in languages

    def test_detect_rust(self):
        """Test detection of Rust projects."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            (project_path / "main.rs").touch()
            (project_path / "lib.rs").touch()

            languages = detect_project_languages(project_path)
            assert "rust" in languages

    def test_detect_go(self):
        """Test detection of Go projects."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            (project_path / "main.go").touch()
            (project_path / "utils.go").touch()

            languages = detect_project_languages(project_path)
            assert "go" in languages

    def test_detect_multiple_languages(self):
        """Test detection of multi-language projects."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            (project_path / "backend.py").touch()
            (project_path / "frontend.js").touch()
            (project_path / "lib.rs").touch()

            languages = detect_project_languages(project_path)
            assert "python" in languages
            assert "javascript" in languages
            assert "rust" in languages

    def test_detect_ignores_common_dirs(self):
        """Test that detection ignores common directories."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create files in directories that should be ignored
            ignored_dirs = [
                "node_modules",
                ".git",
                "__pycache__",
                ".venv",
                "target",
                "build",
                "dist",
            ]

            for dir_name in ignored_dirs:
                dir_path = project_path / dir_name
                dir_path.mkdir()
                (dir_path / "file.py").touch()

            # Only create one valid file
            (project_path / "main.py").touch()

            languages = detect_project_languages(project_path)
            # Should only detect Python from main.py, not from ignored dirs
            assert languages == ["python"]

    def test_detect_nested_structure(self):
        """Test detection in nested directory structure."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            src_dir = project_path / "src" / "api"
            src_dir.mkdir(parents=True)
            (src_dir / "handler.py").touch()

            languages = detect_project_languages(project_path)
            assert "python" in languages


class TestEffectiveLanguages:
    """Test computation of effective language list."""

    def test_explicit_languages(self):
        """Test explicit language list takes precedence."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            # Create Python and JS files
            (project_path / "main.py").touch()
            (project_path / "app.js").touch()

            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[lsp]
languages = ["python"]
""")

            config = load_config(project_path)
            languages = get_effective_languages(config)

            # Should only get Python, not JavaScript
            assert languages == ["python"]

    def test_auto_detect_enabled(self):
        """Test auto-detection when enabled."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            (project_path / "main.py").touch()
            (project_path / "app.js").touch()

            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[lsp]
auto_detect = true
""")

            config = load_config(project_path)
            languages = get_effective_languages(config)

            assert "python" in languages
            assert "javascript" in languages

    def test_disabled_languages(self):
        """Test disabled_languages removes from detected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            (project_path / "main.py").touch()
            (project_path / "app.js").touch()
            (project_path / "lib.rs").touch()

            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[lsp]
auto_detect = true
disabled_languages = ["javascript", "rust"]
""")

            config = load_config(project_path)
            languages = get_effective_languages(config)

            assert languages == ["python"]
            assert "javascript" not in languages
            assert "rust" not in languages

    def test_auto_detect_disabled_no_languages(self):
        """Test that disabling auto-detect with no languages gives empty list."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            (project_path / "main.py").touch()

            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[lsp]
auto_detect = false
""")

            config = load_config(project_path)
            languages = get_effective_languages(config)

            assert languages == []


class TestConfigIntegration:
    """Test complete configuration scenarios."""

    def test_python_project_config(self):
        """Test typical Python project configuration."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create Python project structure
            (project_path / "main.py").touch()
            venv_path = project_path / ".venv" / "bin"
            venv_path.mkdir(parents=True)
            (venv_path / "python").touch()

            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[lsp.python]
python_path = "${VENV}/bin/python"
server = "pyright"

[lsp.python.settings]
python.analysis.typeCheckingMode = "strict"
""")

            config = load_config(project_path)

            # Verify Python is detected
            languages = get_effective_languages(config)
            assert "python" in languages

            # Verify Python config
            python_config = config.lsp.language_configs["python"]
            assert python_config.server == "pyright"

            # Verify path resolution
            resolved_path = config.resolve_path(python_config.python_path)
            assert "/.venv/bin/python" in resolved_path

    def test_monorepo_config(self):
        """Test monorepo with multiple languages."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create multi-language structure
            (project_path / "backend.py").touch()
            (project_path / "frontend.ts").touch()
            (project_path / "cli.go").touch()

            config_file = project_path / ".otter.toml"
            config_file.write_text("""
[lsp]
languages = ["python", "typescript", "go"]

[lsp.python]
python_path = "backend/.venv/bin/python"

[performance]
max_lsp_clients = 3
""")

            config = load_config(project_path)

            # Verify explicit languages
            languages = get_effective_languages(config)
            assert set(languages) == {"go", "python", "typescript"}

            # Verify performance settings
            assert config.performance.max_lsp_clients == 3
