"""LSP server installation and verification.

Automatically installs missing LSP servers when Otter starts up.
"""

import asyncio
import shutil
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class LSPServerStatus(Enum):
    """Status of an LSP server."""

    INSTALLED = "installed"
    MISSING = "missing"
    INSTALLING = "installing"
    FAILED = "failed"


@dataclass
class LSPServerInfo:
    """Information about an LSP server."""

    name: str
    command: str  # Command to check if installed
    install_method: str  # How to install it
    status: LSPServerStatus = LSPServerStatus.MISSING


# LSP server configurations
LSP_SERVERS = {
    "python": {
        "pyright": LSPServerInfo(
            name="pyright",
            command="pyright-langserver",
            install_method="npm install -g pyright",
        ),
        "pylsp": LSPServerInfo(
            name="pylsp",
            command="pylsp",
            install_method="pip install python-lsp-server",
        ),
        "ruff_lsp": LSPServerInfo(
            name="ruff-lsp",
            command="ruff-lsp",
            install_method="pip install ruff-lsp",
        ),
    },
    "javascript": {
        "tsserver": LSPServerInfo(
            name="typescript-language-server",
            command="typescript-language-server",
            install_method="npm install -g typescript typescript-language-server",
        ),
    },
    "typescript": {
        "tsserver": LSPServerInfo(
            name="typescript-language-server",
            command="typescript-language-server",
            install_method="npm install -g typescript typescript-language-server",
        ),
    },
    "rust": {
        "rust_analyzer": LSPServerInfo(
            name="rust-analyzer",
            command="rust-analyzer",
            install_method="rustup component add rust-analyzer",
        ),
    },
    "go": {
        "gopls": LSPServerInfo(
            name="gopls",
            command="gopls",
            install_method="go install golang.org/x/tools/gopls@latest",
        ),
    },
}


def is_command_available(command: str) -> bool:
    """Check if a command is available in PATH."""
    return shutil.which(command) is not None


def check_lsp_server(language: str, server_name: Optional[str] = None) -> LSPServerInfo:
    """Check if an LSP server is installed.

    Args:
        language: Language name (python, javascript, etc.)
        server_name: Specific server to check, or None for default

    Returns:
        LSPServerInfo with status updated
    """
    if language not in LSP_SERVERS:
        # Unknown language, assume no LSP needed
        return LSPServerInfo(
            name="unknown",
            command="unknown",
            install_method="",
            status=LSPServerStatus.INSTALLED,
        )

    servers = LSP_SERVERS[language]

    # If specific server requested, check only that one
    if server_name and server_name in servers:
        server = servers[server_name]
    else:
        # Use first server as default
        server = list(servers.values())[0]

    # Check if installed
    if is_command_available(server.command):
        server.status = LSPServerStatus.INSTALLED
    else:
        server.status = LSPServerStatus.MISSING

    return server


async def install_lsp_server(server: LSPServerInfo) -> bool:
    """Install an LSP server.

    Args:
        server: LSP server to install

    Returns:
        True if installation succeeded, False otherwise
    """
    print(f"📦 Installing {server.name}...", file=sys.stderr)
    print(f"   Command: {server.install_method}", file=sys.stderr)

    server.status = LSPServerStatus.INSTALLING

    # Parse install command
    parts = server.install_method.split()
    if not parts:
        return False

    try:
        # Run installation command
        process = await asyncio.create_subprocess_exec(
            *parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            print(f"✅ Successfully installed {server.name}", file=sys.stderr)
            server.status = LSPServerStatus.INSTALLED
            return True
        else:
            print(f"❌ Failed to install {server.name}", file=sys.stderr)
            if stderr:
                error_msg = stderr.decode()[:200]  # First 200 chars
                print(f"   Error: {error_msg}", file=sys.stderr)
            server.status = LSPServerStatus.FAILED
            return False

    except Exception as e:
        print(f"❌ Failed to install {server.name}: {e}", file=sys.stderr)
        server.status = LSPServerStatus.FAILED
        return False


async def check_and_install_lsp_servers(
    languages: List[str],
    language_configs: Dict[str, Any],
    auto_install: bool = True,
) -> Dict[str, LSPServerStatus]:
    """Check and optionally install missing LSP servers.

    Args:
        languages: List of languages to check
        language_configs: Language-specific configurations
        auto_install: Whether to automatically install missing servers

    Returns:
        Dict mapping language to LSP server status
    """
    if not languages:
        return {}

    print("🔍 Checking LSP servers...", file=sys.stderr)

    results = {}
    servers_to_install = []

    # Check which servers are installed
    for language in languages:
        # Get configured server name for this language
        server_name = None
        if language in language_configs:
            lang_config = language_configs[language]
            if hasattr(lang_config, "server") and lang_config.server:
                server_name = lang_config.server

        server = check_lsp_server(language, server_name)

        if server.status == LSPServerStatus.INSTALLED:
            print(f"✅ {language}: {server.name} is installed", file=sys.stderr)
            results[language] = LSPServerStatus.INSTALLED
        else:
            print(f"⚠️  {language}: {server.name} is not installed", file=sys.stderr)
            results[language] = LSPServerStatus.MISSING
            servers_to_install.append((language, server))

    # Install missing servers if auto_install is enabled
    if auto_install and servers_to_install:
        print(
            f"\n📦 Installing {len(servers_to_install)} missing LSP server(s)...",
            file=sys.stderr,
        )
        print("   (This may take a minute on first run)\n", file=sys.stderr)

        for language, server in servers_to_install:
            success = await install_lsp_server(server)

            if success:
                results[language] = LSPServerStatus.INSTALLED
            else:
                results[language] = LSPServerStatus.FAILED
                print(f"\n⚠️  {language} LSP features may not work", file=sys.stderr)
                print(
                    f"   You can manually install with: {server.install_method}",
                    file=sys.stderr,
                )

    elif servers_to_install:
        print("\n⚠️  Auto-install is disabled. Missing LSP servers:", file=sys.stderr)
        for language, server in servers_to_install:
            print(f"   {language}: {server.install_method}", file=sys.stderr)

    print("", file=sys.stderr)  # Blank line for readability
    return results


def check_prerequisites() -> Dict[str, bool]:
    """Check if prerequisite tools are available for installing LSP servers.

    Returns:
        Dict mapping tool name to availability
    """
    prerequisites = {
        "npm": is_command_available("npm"),
        "pip": is_command_available("pip") or is_command_available("pip3"),
        "rustup": is_command_available("rustup"),
        "go": is_command_available("go"),
    }
    return prerequisites


def print_missing_prerequisites() -> None:
    """Print information about missing prerequisite tools."""
    prereqs = check_prerequisites()
    missing = [name for name, available in prereqs.items() if not available]

    if not missing:
        return

    print("⚠️  Some prerequisite tools are missing:", file=sys.stderr)

    for tool in missing:
        if tool == "npm":
            print("   npm: Install Node.js from https://nodejs.org/", file=sys.stderr)
        elif tool == "pip":
            print("   pip: Install Python package manager", file=sys.stderr)
        elif tool == "rustup":
            print("   rustup: Install from https://rustup.rs/", file=sys.stderr)
        elif tool == "go":
            print("   go: Install from https://golang.org/", file=sys.stderr)

    print("", file=sys.stderr)
