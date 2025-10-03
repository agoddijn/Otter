"""Data types for runtime resolution."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RuntimeInfo:
    """Information about a resolved language runtime.
    
    Attributes:
        language: Language name (e.g., "python", "javascript")
        path: Absolute path to runtime executable
        source: How the runtime was resolved
        version: Runtime version string (if available)
    """
    
    language: str
    path: str
    source: str  # "explicit_config", "auto_detect_venv", "system", etc.
    version: Optional[str] = None
    
    def __repr__(self) -> str:
        version_str = f" v{self.version}" if self.version else ""
        return f"<RuntimeInfo {self.language}{version_str} @ {self.path} ({self.source})>"

