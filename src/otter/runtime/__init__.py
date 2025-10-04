"""Generic runtime resolver for language runtimes (Python, Node, etc.)."""

from .resolver import RuntimeResolver
from .specs import RUNTIME_SPECS
from .types import RuntimeInfo

__all__ = [
    "RuntimeResolver",
    "RuntimeInfo",
    "RUNTIME_SPECS",
]
