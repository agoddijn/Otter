from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class IDEConfig:
    project_root: str = "."
    neovim_socket: Optional[str] = None


def load_config(path: Optional[str] = None) -> IDEConfig:
    return IDEConfig()
