"""System dependency checking for the IDE."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class Dependency:
    """Represents a required system dependency."""

    name: str
    command: str
    required: bool
    install_hint: str
    version_command: Optional[str] = None
    min_version: Optional[str] = None


class DependencyError(Exception):
    """Raised when required dependencies are missing."""

    def __init__(self, missing: List[Dependency]):
        self.missing = missing
        message = self._format_error_message(missing)
        super().__init__(message)

    def _format_error_message(self, missing: List[Dependency]) -> str:
        """Format a user-friendly error message."""
        lines = [
            "❌ Missing Required Dependencies",
            "",
            "The following system dependencies are required but not installed:",
            "",
        ]

        for dep in missing:
            lines.append(f"  • {dep.name} ({dep.command})")
            lines.append(f"    Install: {dep.install_hint}")
            lines.append("")

        lines.extend(
            [
                "Please install the missing dependencies and try again.",
                "",
                "💡 Quick setup on macOS:",
                "   make install-deps",
                "",
            ]
        )

        return "\n".join(lines)


# Define all required dependencies
REQUIRED_DEPENDENCIES = [
    Dependency(
        name="Neovim",
        command="nvim",
        required=True,
        install_hint="brew install neovim",
        version_command="nvim --version",
        min_version="0.9.0",
    ),
    Dependency(
        name="Ripgrep",
        command="rg",
        required=True,
        install_hint="brew install ripgrep",
        version_command="rg --version",
    ),
    Dependency(
        name="Node.js",
        command="node",
        required=True,
        install_hint="brew install node",
        version_command="node --version",
        min_version="16.0.0",
    ),
    Dependency(
        name="Git",
        command="git",
        required=True,
        install_hint="brew install git (or install Xcode Command Line Tools)",
        version_command="git --version",
    ),
    Dependency(
        name="C Compiler",
        command="gcc",
        required=False,  # clang is an alternative
        install_hint="xcode-select --install",
        version_command="gcc --version",
    ),
]


def check_command_exists(command: str) -> bool:
    """Check if a command exists in PATH."""
    return shutil.which(command) is not None


def get_command_version(command: str, version_arg: str = "--version") -> Optional[str]:
    """Get version string from a command."""
    try:
        result = subprocess.run(
            [command, version_arg],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0]
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    return None


def check_dependency(dep: Dependency) -> tuple[bool, Optional[str]]:
    """Check if a dependency is installed.

    Returns:
        Tuple of (is_installed, version_string)
    """
    if not check_command_exists(dep.command):
        return False, None

    version = None
    if dep.version_command:
        version = get_command_version(dep.command)

    return True, version


def check_all_dependencies(verbose: bool = False) -> tuple[bool, List[Dependency]]:
    """Check all required dependencies.

    Args:
        verbose: If True, print status for each dependency

    Returns:
        Tuple of (all_ok, missing_dependencies)
    """
    missing = []

    for dep in REQUIRED_DEPENDENCIES:
        is_installed, version = check_dependency(dep)

        if verbose:
            status = "✅" if is_installed else "❌"
            version_str = f" ({version})" if version else ""
            print(f"{status} {dep.name}: {dep.command}{version_str}")

        if not is_installed and dep.required:
            missing.append(dep)

    # Special case: Check for either gcc or clang
    has_compiler = check_command_exists("gcc") or check_command_exists("clang")
    if not has_compiler and verbose:
        print("⚠️  No C compiler found (gcc or clang)")
        print("   TreeSitter parsers may fail to compile")

    return len(missing) == 0, missing


def check_dependencies_or_raise(verbose: bool = False) -> None:
    """Check dependencies and raise DependencyError if any are missing.

    Args:
        verbose: If True, print status for each dependency

    Raises:
        DependencyError: If required dependencies are missing
    """
    all_ok, missing = check_all_dependencies(verbose=verbose)

    if not all_ok:
        raise DependencyError(missing)


def get_dependency_status() -> dict[str, dict[str, Any]]:
    """Get detailed status of all dependencies.

    Returns:
        Dictionary mapping dependency names to their status
    """
    status = {}

    for dep in REQUIRED_DEPENDENCIES:
        is_installed, version = check_dependency(dep)
        status[dep.name] = {
            "command": dep.command,
            "installed": is_installed,
            "version": version,
            "required": dep.required,
            "install_hint": dep.install_hint,
        }

    return status
