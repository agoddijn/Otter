"""
DAP (Debug Adapter Protocol) Bootstrap

Automatically installs and configures debug adapters for various languages.
Similar to LSP bootstrap, ensures "batteries included" debugging experience.
"""

import asyncio
import shutil
import subprocess
from enum import Enum
from typing import Dict, List, Optional


class DAPAdapterStatus(Enum):
    """Status of a DAP adapter."""
    INSTALLED = "installed"
    MISSING = "missing"
    PREREQUISITES_MISSING = "prerequisites_missing"


# Mapping of language -> debug adapter info
DAP_ADAPTER_INFO = {
    "python": {
        "name": "debugpy",
        "check_import": "debugpy",  # Python import name
        "install_cmd": ["pip", "install", "debugpy"],
        "prerequisites": ["pip"],
        "description": "Python debugger (debugpy)",
    },
    "javascript": {
        "name": "node-debug2",
        "check_cmd": "node-debug2",
        "install_cmd": ["npm", "install", "-g", "node-debug2"],
        "prerequisites": ["npm"],
        "description": "Node.js debugger (node-debug2)",
    },
    "typescript": {
        "name": "node-debug2",
        "check_cmd": "node-debug2",
        "install_cmd": ["npm", "install", "-g", "node-debug2"],
        "prerequisites": ["npm"],
        "description": "TypeScript debugger (node-debug2)",
    },
    "rust": {
        "name": "lldb-vscode",
        "check_cmd": "lldb-vscode",
        "install_cmd": None,  # Usually comes with lldb
        "prerequisites": ["lldb"],
        "description": "Rust debugger (lldb-vscode or codelldb)",
        "install_note": "Install via: rustup component add lldb-preview",
    },
    "go": {
        "name": "delve",
        "check_cmd": "dlv",
        "install_cmd": ["go", "install", "github.com/go-delve/delve/cmd/dlv@latest"],
        "prerequisites": ["go"],
        "description": "Go debugger (delve)",
    },
}


def check_command_availability(cmd: str) -> bool:
    """Check if a command is available in PATH."""
    return shutil.which(cmd) is not None


def check_python_package(package: str, python_path: Optional[str] = None) -> bool:
    """Check if a Python package is importable in a specific Python runtime.
    
    Args:
        package: Package name to check
        python_path: Path to Python executable. If None, uses current Python.
        
    Returns:
        True if package is available, False otherwise
    """
    if python_path:
        # Check in the specified Python runtime (e.g., project venv)
        try:
            result = subprocess.run(
                [python_path, "-c", f"import {package}"],
                capture_output=True,
                timeout=5.0,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    else:
        # Fallback: check in current Python
        try:
            __import__(package)
            return True
        except ImportError:
            return False


def check_dap_adapter(language: str, runtime_path: Optional[str] = None) -> DAPAdapterStatus:
    """Check if a DAP adapter is installed for a language.
    
    Args:
        language: Language name (e.g., "python", "javascript")
        runtime_path: Path to language runtime (e.g., Python executable) to check packages in.
                     For Python, this ensures we check debugpy in the PROJECT's venv, not Otter's.
        
    Returns:
        DAPAdapterStatus indicating if adapter is installed
    """
    if language not in DAP_ADAPTER_INFO:
        return DAPAdapterStatus.MISSING
    
    info = DAP_ADAPTER_INFO[language]
    
    # Check prerequisites first
    for prereq in info.get("prerequisites", []):
        if not check_command_availability(prereq):
            return DAPAdapterStatus.PREREQUISITES_MISSING
    
    # Check adapter availability
    if "check_import" in info:
        # Python package check - use the target runtime's Python
        if check_python_package(info["check_import"], python_path=runtime_path):
            return DAPAdapterStatus.INSTALLED
    elif "check_cmd" in info:
        # Command check (for non-Python languages)
        if check_command_availability(info["check_cmd"]):
            return DAPAdapterStatus.INSTALLED
    
    return DAPAdapterStatus.MISSING


def check_prerequisites(language: str) -> tuple[bool, List[str]]:
    """Check if prerequisites are available for a language's DAP adapter.
    
    Returns:
        (all_available, missing_prerequisites)
    """
    if language not in DAP_ADAPTER_INFO:
        return False, []
    
    info = DAP_ADAPTER_INFO[language]
    missing = []
    
    for prereq in info.get("prerequisites", []):
        if not check_command_availability(prereq):
            missing.append(prereq)
    
    return len(missing) == 0, missing


def print_missing_prerequisites(language: str, missing: List[str]) -> None:
    """Print helpful message about missing prerequisites."""
    print(f"\n⚠️  Cannot install {language} debugger - missing prerequisites:")
    for prereq in missing:
        print(f"   - {prereq}")
    
    # Language-specific install instructions
    if "pip" in missing:
        print(f"\n💡 Install pip:")
        print(f"   curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py")
        print(f"   python get-pip.py")
    elif "npm" in missing:
        print(f"\n💡 Install Node.js and npm:")
        print(f"   https://nodejs.org/")
    elif "go" in missing:
        print(f"\n💡 Install Go:")
        print(f"   https://golang.org/dl/")


async def install_dap_adapter(language: str, runtime_path: Optional[str] = None) -> bool:
    """Install a DAP adapter for a language.
    
    Args:
        language: Language name
        runtime_path: Path to language runtime (e.g., Python executable).
                     For Python, this ensures we install debugpy in the PROJECT's venv.
        
    Returns:
        True if installation successful, False otherwise
    """
    if language not in DAP_ADAPTER_INFO:
        return False
    
    info = DAP_ADAPTER_INFO[language]
    install_cmd = info.get("install_cmd")
    
    if not install_cmd:
        # No automatic install available
        print(f"\n⚠️  {info['description']} cannot be auto-installed")
        if "install_note" in info:
            print(f"   {info['install_note']}")
        return False
    
    # For Python packages, use the target Python's pip
    if language == "python" and runtime_path and install_cmd[0] == "pip":
        # Use python -m pip instead of system pip
        install_cmd = [runtime_path, "-m", "pip"] + install_cmd[1:]
    
    print(f"\n📦 Installing {info['description']}...")
    print(f"   Command: {' '.join(install_cmd)}")
    
    try:
        result = subprocess.run(
            install_cmd,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
        )
        
        if result.returncode == 0:
            print(f"✅ Successfully installed {info['name']}")
            return True
        else:
            print(f"❌ Failed to install {info['name']}")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ Installation timed out for {info['name']}")
        return False
    except Exception as e:
        print(f"❌ Installation error: {e}")
        return False


async def check_and_install_dap_adapter(
    language: str,
    auto_install: bool = True,
    runtime_path: Optional[str] = None,
) -> tuple[DAPAdapterStatus, Optional[str]]:
    """Check and optionally install a DAP adapter.
    
    Args:
        language: Language to check/install adapter for
        auto_install: Whether to auto-install if missing
        runtime_path: Path to language runtime (e.g., Python executable).
                     Ensures we check/install in the correct environment.
        
    Returns:
        (status, error_message)
    """
    print(f"\n🔍 Checking {language} debugger...")
    
    status = check_dap_adapter(language, runtime_path=runtime_path)
    
    if status == DAPAdapterStatus.INSTALLED:
        info = DAP_ADAPTER_INFO.get(language, {})
        print(f"✅ {language}: {info.get('name', 'debugger')} is installed")
        return status, None
    
    if status == DAPAdapterStatus.PREREQUISITES_MISSING:
        has_prereqs, missing = check_prerequisites(language)
        print_missing_prerequisites(language, missing)
        
        error_msg = (
            f"Cannot install {language} debugger: missing prerequisites {missing}. "
            f"Please install them first."
        )
        return status, error_msg
    
    # Status is MISSING
    info = DAP_ADAPTER_INFO.get(language, {})
    print(f"⚠️  {language}: {info.get('description', 'debugger')} is not installed")
    
    if not auto_install:
        error_msg = (
            f"{language} debugger not installed. "
            f"Install with: {' '.join(info.get('install_cmd', []))}"
        )
        return status, error_msg
    
    # Auto-install
    print(f"\n📦 Auto-installing {language} debugger...")
    print(f"   (This may take a minute)")
    
    success = await install_dap_adapter(language, runtime_path=runtime_path)
    
    if success:
        # Verify installation
        final_status = check_dap_adapter(language, runtime_path=runtime_path)
        if final_status == DAPAdapterStatus.INSTALLED:
            return final_status, None
        else:
            error_msg = f"Installation appeared to succeed but {language} debugger still not found"
            return DAPAdapterStatus.MISSING, error_msg
    else:
        # Installation failed - provide helpful fallback guidance
        install_cmd_str = ' '.join(info.get('install_cmd', []))
        
        # For Python, check if debugpy is available in system Python
        # (Can't use it directly, but can guide user to install in their venv)
        fallback_note = ""
        if language == "python":
            # Check if debugpy exists in system Python
            system_has_debugpy = check_python_package("debugpy", python_path=None)
            if system_has_debugpy and runtime_path:
                fallback_note = (
                    f"\n\n💡 NOTE: debugpy is installed in your system Python, "
                    f"but it needs to be in your project's venv.\n"
                    f"   Install it manually:\n"
                    f"     {runtime_path} -m pip install debugpy"
                )
        
        error_msg = (
            f"Failed to install {language} debugger. "
            f"Please install manually: {install_cmd_str}"
            f"{fallback_note}"
        )
        return DAPAdapterStatus.MISSING, error_msg


async def ensure_dap_adapter(
    language: str, 
    auto_install: bool = True,
    runtime_path: Optional[str] = None,
) -> None:
    """Ensure a DAP adapter is available, installing if needed.
    
    Args:
        language: Language to ensure adapter for
        auto_install: Whether to auto-install if missing
        runtime_path: Path to language runtime (e.g., Python executable).
                     Ensures we check/install in the correct environment.
    
    Raises:
        RuntimeError: If adapter is not available and cannot be installed
    """
    status, error_msg = await check_and_install_dap_adapter(
        language, 
        auto_install,
        runtime_path=runtime_path
    )
    
    if status != DAPAdapterStatus.INSTALLED:
        raise RuntimeError(error_msg or f"{language} debugger not available")


# Export main functions
__all__ = [
    "DAPAdapterStatus",
    "check_dap_adapter",
    "check_and_install_dap_adapter",
    "ensure_dap_adapter",
    "DAP_ADAPTER_INFO",
]

