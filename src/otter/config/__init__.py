"""Configuration management for Otter IDE."""

from .parser import (
    OtterConfig,
    load_config,
    find_config_file,
    detect_project_languages,
    get_effective_languages,
)

__all__ = [
    "OtterConfig",
    "load_config",
    "find_config_file",
    "detect_project_languages",
    "get_effective_languages",
]
