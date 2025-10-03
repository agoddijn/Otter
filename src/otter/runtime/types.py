"""Data types for runtime resolution."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RuntimeInfo:
    """Information about a resolved language runtime.
    
    Attributes:
        language: Language name (e.g., "python", "javascript")
        path: Absolute path to runtime executable (resolved if symlink)
        source: How the runtime was resolved
        version: Runtime version string (if available)
        original_path: Original path before symlink resolution (if different)
        is_symlink: Whether the path is a symlink
    """
    
    language: str
    path: str
    source: str  # "explicit_config", "auto_detect_venv", "system", etc.
    version: Optional[str] = None
    original_path: Optional[str] = None  # Path before resolving symlinks
    is_symlink: bool = False
    
    def __repr__(self) -> str:
        version_str = f" v{self.version}" if self.version else ""
        symlink_note = " (symlink)" if self.is_symlink else ""
        return f"<RuntimeInfo {self.language}{version_str} @ {self.path}{symlink_note} ({self.source})>"

