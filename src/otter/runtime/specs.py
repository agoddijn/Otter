"""Declarative runtime specifications for all supported languages.

This is DATA, not code. To add a new language, just add its spec here.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Union


@dataclass(frozen=True)
class VersionCheck:
    """Configuration for checking runtime version."""
    args: List[str]
    parse: str  # Regex pattern to extract version


@dataclass(frozen=True)
class VenvDetection:
    """Virtual environment detection strategy."""
    type: Literal["venv"] = "venv"
    patterns: List[str] = field(default_factory=list)
    executable_path: str = "bin/python"
    executable_path_win: str = "Scripts/python.exe"
    priority: int = 10


@dataclass(frozen=True)
class CondaDetection:
    """Conda environment detection strategy."""
    type: Literal["conda"] = "conda"
    patterns: List[str] = field(default_factory=list)
    executable_path: str = "bin/python"
    priority: int = 5


@dataclass(frozen=True)
class NvmDetection:
    """NVM (Node Version Manager) detection strategy."""
    type: Literal["nvm"] = "nvm"
    version_file: str = ".nvmrc"
    path_template: str = "~/.nvm/versions/node/v{version}/bin/node"
    priority: int = 10


@dataclass(frozen=True)
class LocalNodeModulesDetection:
    """Local node_modules detection strategy."""
    type: Literal["local_node_modules"] = "local_node_modules"
    patterns: List[str] = field(default_factory=list)
    executable_path: str = "node"
    priority: int = 8


@dataclass(frozen=True)
class ToolchainTomlDetection:
    """Rust toolchain.toml detection strategy."""
    type: Literal["toolchain_toml"] = "toolchain_toml"
    version_file: str = "rust-toolchain.toml"
    toml_key: str = "toolchain.channel"
    default: str = "stable"
    priority: int = 10


@dataclass(frozen=True)
class ToolchainTextDetection:
    """Rust toolchain text file detection strategy."""
    type: Literal["toolchain_text"] = "toolchain_text"
    version_file: str = "rust-toolchain"
    priority: int = 9


@dataclass(frozen=True)
class GoModDetection:
    """Go module (go.mod) detection strategy."""
    type: Literal["go_mod"] = "go_mod"
    version_file: str = "go.mod"
    parse: str = r"go\s+(\d+\.\d+)"
    priority: int = 10


# Union of all detection strategies
AutoDetectStrategy = Union[
    VenvDetection,
    CondaDetection,
    NvmDetection,
    LocalNodeModulesDetection,
    ToolchainTomlDetection,
    ToolchainTextDetection,
    GoModDetection,
]


@dataclass(frozen=True)
class RuntimeSpec:
    """Complete runtime specification for a language."""
    display_name: str
    executable_name: str
    config_key: str
    auto_detect: List[AutoDetectStrategy]
    system_commands: List[str]
    version_check: VersionCheck


# Declarative runtime specifications
# To add a new language, just add its RuntimeSpec here
RUNTIME_SPECS: Dict[str, RuntimeSpec] = {
    "python": RuntimeSpec(
        display_name="Python",
        executable_name="python",
        config_key="python_path",
        auto_detect=[
            VenvDetection(
                patterns=[".venv", "venv", "env", ".env"],
                executable_path="bin/python",  # Unix/Mac
                executable_path_win="Scripts/python.exe",  # Windows
                priority=10,  # Higher = checked first
            ),
            CondaDetection(
                patterns=["conda", ".conda", "miniconda", "anaconda"],
                executable_path="bin/python",
                priority=5,
            ),
        ],
        system_commands=["python3", "python"],  # Try in order
        version_check=VersionCheck(
            args=["--version"],
            parse=r"Python (\d+\.\d+\.\d+)",
        ),
    ),
    
    "javascript": RuntimeSpec(
        display_name="Node.js",
        executable_name="node",
        config_key="node_path",
        auto_detect=[
            NvmDetection(
                version_file=".nvmrc",  # Read version from here
                path_template="~/.nvm/versions/node/v{version}/bin/node",
                priority=10,
            ),
            LocalNodeModulesDetection(
                patterns=["node_modules/.bin"],
                executable_path="node",
                priority=8,
            ),
        ],
        system_commands=["node"],
        version_check=VersionCheck(
            args=["--version"],
            parse=r"v(\d+\.\d+\.\d+)",
        ),
    ),
    
    "typescript": RuntimeSpec(
        # TypeScript uses Node runtime
        display_name="TypeScript (Node.js)",
        executable_name="node",
        config_key="node_path",
        auto_detect=[
            NvmDetection(
                version_file=".nvmrc",
                path_template="~/.nvm/versions/node/v{version}/bin/node",
                priority=10,
            ),
        ],
        system_commands=["node"],
        version_check=VersionCheck(
            args=["--version"],
            parse=r"v(\d+\.\d+\.\d+)",
        ),
    ),
    
    "rust": RuntimeSpec(
        display_name="Rust",
        executable_name="cargo",
        config_key="rust_toolchain",
        auto_detect=[
            ToolchainTomlDetection(
                version_file="rust-toolchain.toml",
                toml_key="toolchain.channel",
                default="stable",
                priority=10,
            ),
            ToolchainTextDetection(
                version_file="rust-toolchain",
                priority=9,
            ),
        ],
        system_commands=["cargo"],
        version_check=VersionCheck(
            args=["--version"],
            parse=r"cargo (\d+\.\d+\.\d+)",
        ),
    ),
    
    "go": RuntimeSpec(
        display_name="Go",
        executable_name="go",
        config_key="go_path",
        auto_detect=[
            GoModDetection(
                version_file="go.mod",
                parse=r"go\s+(\d+\.\d+)",
                priority=10,
            ),
        ],
        system_commands=["go"],
        version_check=VersionCheck(
            args=["version"],
            parse=r"go(\d+\.\d+\.\d+)",
        ),
    ),
}


def get_runtime_spec(language: str) -> RuntimeSpec:
    """Get runtime spec for a language.
    
    Args:
        language: Language name
        
    Returns:
        Runtime specification (typed dataclass)
        
    Raises:
        ValueError: If language not supported
    """
    if language not in RUNTIME_SPECS:
        supported = ", ".join(RUNTIME_SPECS.keys())
        raise ValueError(
            f"Language '{language}' not supported. "
            f"Supported languages: {supported}"
        )
    
    return RUNTIME_SPECS[language]

