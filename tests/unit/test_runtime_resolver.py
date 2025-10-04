"""Unit tests for generic runtime resolver."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from otter.runtime import RUNTIME_SPECS, RuntimeInfo, RuntimeResolver
from otter.runtime.specs import get_runtime_spec


class TestRuntimeSpecs:
    """Test runtime specifications."""

    def test_all_languages_have_required_fields(self):
        """All language specs should have required fields."""
        required_fields = ["display_name", "executable_name", "config_key"]

        for language, spec in RUNTIME_SPECS.items():
            for field in required_fields:
                assert hasattr(spec, field), f"{language} missing {field}"

    def test_get_runtime_spec_valid_language(self):
        """Should return spec for valid language."""
        spec = get_runtime_spec("python")
        assert spec.display_name == "Python"
        assert spec.executable_name == "python"

    def test_get_runtime_spec_invalid_language(self):
        """Should raise ValueError for invalid language."""
        with pytest.raises(ValueError, match="not supported"):
            get_runtime_spec("invalid_language")

    def test_python_spec_structure(self):
        """Python spec should have correct structure."""
        spec = RUNTIME_SPECS["python"]
        assert spec.config_key == "python_path"
        assert len(spec.auto_detect) > 0
        assert spec.auto_detect[0].type == "venv"
        assert ".venv" in spec.auto_detect[0].patterns


class TestRuntimeInfo:
    """Test RuntimeInfo dataclass."""

    def test_runtime_info_creation(self):
        """Should create RuntimeInfo correctly."""
        info = RuntimeInfo(
            language="python",
            path="/usr/bin/python3",
            source="system",
            version="3.11.0",
        )

        assert info.language == "python"
        assert info.path == "/usr/bin/python3"
        assert info.source == "system"
        assert info.version == "3.11.0"

    def test_runtime_info_repr(self):
        """Should have useful repr."""
        info = RuntimeInfo(
            language="python",
            path="/usr/bin/python3",
            source="system",
            version="3.11.0",
        )

        repr_str = repr(info)
        assert "python" in repr_str
        assert "3.11.0" in repr_str
        assert "/usr/bin/python3" in repr_str


class TestRuntimeResolver:
    """Test RuntimeResolver."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def resolver(self, temp_project):
        """Create a RuntimeResolver instance."""
        return RuntimeResolver(temp_project)

    def test_resolver_initialization(self, temp_project):
        """Should initialize resolver with project path."""
        resolver = RuntimeResolver(temp_project)
        assert resolver.project_path == temp_project

    @patch("shutil.which")
    def test_system_fallback_python(self, mock_which, resolver):
        """Should fall back to system Python."""
        mock_which.return_value = "/usr/bin/python3"

        with patch.object(resolver, "_get_version", return_value="3.11.0"):
            runtime = resolver.resolve_runtime("python")

        assert runtime.language == "python"
        assert runtime.path == "/usr/bin/python3"
        assert runtime.source == "system"
        assert runtime.version == "3.11.0"

    def test_detect_venv_unix(self, temp_project, resolver):
        """Should detect Python venv on Unix."""
        # Create .venv structure
        venv_path = temp_project / ".venv" / "bin"
        venv_path.mkdir(parents=True)
        python_path = venv_path / "python"
        python_path.touch()

        with patch.object(resolver, "_get_version", return_value="3.11.0"):
            runtime = resolver.resolve_runtime("python")

        assert runtime.language == "python"
        assert str(runtime.path).endswith("/.venv/bin/python")
        assert "venv" in runtime.source

    def test_detect_venv_windows(self, temp_project, resolver):
        """Should detect Python venv on Windows."""
        # Create .venv structure
        venv_path = temp_project / ".venv" / "Scripts"
        venv_path.mkdir(parents=True)
        python_path = venv_path / "python.exe"
        python_path.touch()

        with patch.object(resolver, "_get_version", return_value="3.11.0"):
            runtime = resolver.resolve_runtime("python")

        assert runtime.language == "python"
        assert "python.exe" in str(runtime.path)
        assert "venv" in runtime.source

    def test_explicit_config_priority(self, temp_project, resolver):
        """Explicit config should have highest priority."""
        # Create venv
        venv_path = temp_project / ".venv" / "bin"
        venv_path.mkdir(parents=True)
        (venv_path / "python").touch()

        # Create explicit config
        explicit_python = temp_project / "custom" / "python"
        explicit_python.parent.mkdir(parents=True)
        explicit_python.touch()

        # Mock config
        mock_config = MagicMock()
        mock_config.lsp.language_configs.get.return_value = MagicMock(
            python_path=str(explicit_python)
        )
        mock_config.resolve_path.return_value = str(explicit_python)

        with patch.object(resolver, "_get_version", return_value="3.11.0"):
            runtime = resolver.resolve_runtime("python", mock_config)

        assert runtime.path == str(explicit_python)
        assert runtime.source == "explicit_config"

    def test_detect_nvmrc(self, temp_project, resolver):
        """Should detect Node version from .nvmrc."""
        # Create .nvmrc
        nvmrc = temp_project / ".nvmrc"
        nvmrc.write_text("18.16.0")

        # Mock nvm path
        Path.home() / ".nvm" / "versions" / "node" / "v18.16.0" / "bin" / "node"

        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch.object(resolver, "_get_version", return_value="18.16.0"):
                runtime = resolver.resolve_runtime("javascript")

        assert runtime.language == "javascript"
        assert "18.16.0" in runtime.path
        assert runtime.source == "auto_detect_nvm"

    def test_detect_rust_toolchain_toml(self, temp_project, resolver):
        """Should detect Rust toolchain from rust-toolchain.toml."""
        # Create rust-toolchain.toml
        toolchain_file = temp_project / "rust-toolchain.toml"
        toolchain_file.write_text("""
[toolchain]
channel = "stable"
        """)

        runtime = resolver.resolve_runtime("rust")

        assert runtime.language == "rust"
        assert "rustup::stable" in runtime.path
        assert runtime.source == "auto_detect_toolchain"

    def test_detect_go_mod(self, temp_project, resolver):
        """Should detect Go version from go.mod."""
        # Create go.mod
        go_mod = temp_project / "go.mod"
        go_mod.write_text("""
module example.com/myapp

go 1.21
        """)

        with patch("shutil.which", return_value="/usr/bin/go"):
            with patch.object(resolver, "_get_version", return_value="1.21.0"):
                runtime = resolver.resolve_runtime("go")

        assert runtime.language == "go"
        assert runtime.path == "/usr/bin/go"
        assert runtime.source == "auto_detect_go_mod"

    def test_runtime_not_found(self, resolver):
        """Should raise RuntimeError if runtime not found."""
        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="runtime not found"):
                resolver.resolve_runtime("python")

    def test_unsupported_language(self, resolver):
        """Should raise ValueError for unsupported language."""
        with pytest.raises(ValueError, match="not supported"):
            resolver.resolve_runtime("cobol")

    def test_multiple_venv_patterns(self, temp_project, resolver):
        """Should try multiple venv patterns."""
        # Create venv/ instead of .venv/
        venv_path = temp_project / "venv" / "bin"
        venv_path.mkdir(parents=True)
        python_path = venv_path / "python"
        python_path.touch()

        with patch.object(resolver, "_get_version", return_value="3.11.0"):
            runtime = resolver.resolve_runtime("python")

        assert "/venv/bin/python" in str(runtime.path)

    @patch("subprocess.run")
    def test_get_version_success(self, mock_run, resolver):
        """Should extract version from command output."""
        mock_run.return_value = MagicMock(
            stdout="Python 3.11.5",
            stderr="",
        )

        spec = get_runtime_spec("python")
        version = resolver._get_version("/usr/bin/python3", spec)

        assert version == "3.11.5"

    @patch("subprocess.run")
    def test_get_version_failure(self, mock_run, resolver):
        """Should return None if version check fails."""
        mock_run.side_effect = Exception("Command failed")

        spec = get_runtime_spec("python")
        version = resolver._get_version("/usr/bin/python3", spec)

        assert version is None


class TestIntegration:
    """Integration tests with real file system."""

    def test_resolve_all_languages(self):
        """Should be able to resolve all supported languages (or fail gracefully)."""
        resolver = RuntimeResolver(Path.cwd())

        for language in ["python", "javascript", "rust", "go"]:
            try:
                runtime = resolver.resolve_runtime(language)
                print(f"✅ {language}: {runtime}")
                assert runtime.language == language
                assert runtime.path
                assert runtime.source
            except RuntimeError as e:
                # OK if runtime not installed
                print(f"⏭️  {language}: {e}")
                assert language in str(e)
