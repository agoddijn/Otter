"""Configuration file parser for Otter IDE."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for Python 3.10


@dataclass
class LSPLanguageConfig:
    """Configuration for a specific language's LSP."""

    enabled: bool = True
    server: Optional[str] = None
    python_path: Optional[str] = None  # For Python
    node_path: Optional[str] = None  # For JavaScript/TypeScript
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DAPLanguageConfig:
    """Configuration for a specific language's DAP."""

    enabled: bool = True
    adapter: Optional[str] = None
    python_path: Optional[str] = None  # For Python
    configurations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class LSPConfig:
    """Global LSP configuration."""

    enabled: bool = True
    auto_detect: bool = True
    lazy_load: bool = True
    auto_install: bool = True  # Auto-install missing LSP servers
    timeout_ms: int = 2000
    languages: Optional[List[str]] = None
    disabled_languages: List[str] = field(default_factory=list)
    # Language-specific configs
    language_configs: Dict[str, LSPLanguageConfig] = field(default_factory=dict)


@dataclass
class DAPConfig:
    """Global DAP configuration."""

    enabled: bool = True
    auto_detect: bool = True
    lazy_load: bool = True
    # Language-specific configs
    language_configs: Dict[str, DAPLanguageConfig] = field(default_factory=dict)


@dataclass
class PerformanceConfig:
    """Performance-related configuration."""

    max_lsp_clients: int = 5
    max_dap_sessions: int = 2
    file_change_debounce_ms: int = 300


@dataclass
class PluginsConfig:
    """Plugin configuration."""

    treesitter: bool = True
    lsp: bool = True
    dap: bool = True
    treesitter_ensure_installed: List[str] = field(default_factory=list)
    treesitter_auto_install: bool = True


@dataclass
class ProjectConfig:
    """Project-level configuration."""

    name: Optional[str] = None


@dataclass
class OtterConfig:
    """Complete Otter IDE configuration."""

    project: ProjectConfig = field(default_factory=ProjectConfig)
    lsp: LSPConfig = field(default_factory=LSPConfig)
    dap: DAPConfig = field(default_factory=DAPConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    plugins: PluginsConfig = field(default_factory=PluginsConfig)

    # Project root for resolving paths
    project_root: Path = field(default_factory=Path.cwd)

    def resolve_path(self, path_template: str) -> str:
        """Resolve template variables in paths.

        Supports:
            ${PROJECT_ROOT} - absolute path to project root
            ${VENV} - auto-detected virtualenv path
        """
        result = path_template

        # ${PROJECT_ROOT}
        result = result.replace("${PROJECT_ROOT}", str(self.project_root))

        # ${VENV} - auto-detect virtualenv
        if "${VENV}" in result:
            venv_path = self._detect_venv()
            if venv_path:
                result = result.replace("${VENV}", venv_path)
            else:
                # Fallback to project root if no venv found
                result = result.replace("${VENV}", str(self.project_root))

        return result

    def _detect_venv(self) -> Optional[str]:
        """Auto-detect virtualenv in project root."""
        venv_patterns = [".venv", "venv", "env", ".env"]
        for pattern in venv_patterns:
            venv_path = self.project_root / pattern
            if venv_path.is_dir():
                # Check if it's actually a venv (has bin/python or Scripts/python.exe)
                if (venv_path / "bin" / "python").exists() or (
                    venv_path / "Scripts" / "python.exe"
                ).exists():
                    return str(venv_path)
        return None


def find_config_file(project_path: Path) -> Optional[Path]:
    """Find .otter.toml in project root.

    Args:
        project_path: Root path of the project

    Returns:
        Path to .otter.toml if found, None otherwise
    """
    config_file = project_path / ".otter.toml"
    if config_file.exists():
        return config_file
    return None


def load_config(project_path: Path) -> OtterConfig:
    """Load configuration from .otter.toml or use defaults.

    Args:
        project_path: Root path of the project

    Returns:
        OtterConfig with loaded or default configuration
    """
    config = OtterConfig(project_root=project_path)

    config_file = find_config_file(project_path)
    if not config_file:
        # No config file, use defaults with auto-detection
        return config

    # Parse TOML file
    try:
        with open(config_file, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        # If TOML parsing fails, return defaults
        return config

    # Parse project config
    if "project" in data:
        project_data = data["project"]
        config.project.name = project_data.get("name")

    # Parse LSP config
    if "lsp" in data:
        lsp_data = data["lsp"]
        config.lsp.enabled = lsp_data.get("enabled", True)
        config.lsp.auto_detect = lsp_data.get("auto_detect", True)
        config.lsp.lazy_load = lsp_data.get("lazy_load", True)
        config.lsp.auto_install = lsp_data.get("auto_install", True)
        config.lsp.timeout_ms = lsp_data.get("timeout_ms", 2000)
        config.lsp.languages = lsp_data.get("languages")
        config.lsp.disabled_languages = lsp_data.get("disabled_languages", [])

        # Parse language-specific LSP configs
        # TOML sections use dotted keys: [lsp.python] creates nested dicts
        lsp_section = data.get("lsp", {})
        for lang in ["python", "javascript", "typescript", "rust", "go"]:
            if lang in lsp_section and isinstance(lsp_section[lang], dict):
                lang_data = lsp_section[lang]
                lang_config = LSPLanguageConfig(
                    enabled=lang_data.get("enabled", True),
                    server=lang_data.get("server"),
                    python_path=lang_data.get("python_path"),
                    node_path=lang_data.get("node_path"),
                    settings=lang_data.get("settings", {}),
                )
                config.lsp.language_configs[lang] = lang_config

    # Parse DAP config
    if "dap" in data:
        dap_data = data["dap"]
        config.dap.enabled = dap_data.get("enabled", True)
        config.dap.auto_detect = dap_data.get("auto_detect", True)
        config.dap.lazy_load = dap_data.get("lazy_load", True)

        # Parse language-specific DAP configs
        # TOML sections use dotted keys: [dap.python] creates nested dicts
        dap_section = data.get("dap", {})
        for lang in ["python", "javascript", "typescript", "rust", "go"]:
            if lang in dap_section and isinstance(dap_section[lang], dict):
                lang_data = dap_section[lang]
                lang_config = DAPLanguageConfig(
                    enabled=lang_data.get("enabled", True),
                    adapter=lang_data.get("adapter"),
                    python_path=lang_data.get("python_path"),
                    configurations=lang_data.get("configurations", []),
                )
                config.dap.language_configs[lang] = lang_config

    # Parse performance config
    if "performance" in data:
        perf_data = data["performance"]
        config.performance.max_lsp_clients = perf_data.get("max_lsp_clients", 5)
        config.performance.max_dap_sessions = perf_data.get("max_dap_sessions", 2)
        config.performance.file_change_debounce_ms = perf_data.get(
            "file_change_debounce_ms", 300
        )

    # Parse plugins config
    if "plugins" in data:
        plugins_data = data["plugins"]
        
        # Handle treesitter: can be bool or dict (when [plugins.treesitter] exists)
        treesitter_value = plugins_data.get("treesitter", True)
        if isinstance(treesitter_value, dict):
            # [plugins.treesitter] section exists, enable by default
            config.plugins.treesitter = True
            ts_data = treesitter_value
            config.plugins.treesitter_ensure_installed = ts_data.get(
                "ensure_installed", []
            )
            config.plugins.treesitter_auto_install = ts_data.get("auto_install", True)
        else:
            # Boolean value
            config.plugins.treesitter = treesitter_value
        
        config.plugins.lsp = plugins_data.get("lsp", True)
        config.plugins.dap = plugins_data.get("dap", True)

    return config


def detect_project_languages(project_path: Path) -> List[str]:
    """Auto-detect languages used in the project.

    Args:
        project_path: Root path of the project

    Returns:
        List of detected language names
    """
    # File extension to language mapping
    extension_map = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".rs": "rust",
        ".go": "go",
        ".lua": "lua",
    }

    detected = set()

    # Walk through project (limit depth to avoid deep traversal)
    max_depth = 3
    for root, dirs, files in os.walk(project_path):
        # Calculate current depth
        depth = root[len(str(project_path)) :].count(os.sep)
        if depth >= max_depth:
            dirs.clear()  # Don't traverse deeper
            continue

        # Skip common directories to ignore
        dirs[:] = [
            d
            for d in dirs
            if d
            not in {
                ".git",
                "node_modules",
                "__pycache__",
                ".venv",
                "venv",
                "env",
                "target",
                "build",
                "dist",
                ".next",
                ".cache",
            }
        ]

        for file in files:
            ext = Path(file).suffix
            if ext in extension_map:
                detected.add(extension_map[ext])

    return sorted(detected)


def get_effective_languages(config: OtterConfig) -> List[str]:
    """Get the effective list of languages to enable LSP/DAP for.

    Takes into account:
    - Explicit config.lsp.languages
    - Auto-detected languages (if auto_detect=True)
    - Disabled languages

    Args:
        config: Otter configuration

    Returns:
        List of language names to enable
    """
    if config.lsp.languages is not None:
        # Explicit list provided
        languages = set(config.lsp.languages)
    elif config.lsp.auto_detect:
        # Auto-detect
        languages = set(detect_project_languages(config.project_root))
    else:
        # Nothing specified and auto-detect disabled - use empty set
        languages = set()

    # Remove disabled languages
    languages -= set(config.lsp.disabled_languages)

    return sorted(languages)

