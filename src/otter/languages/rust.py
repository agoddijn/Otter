from __future__ import annotations

from typing import Any, Dict, List


class RustLanguageSupport:
    @property
    def lsp_server(self) -> str:
        return "rust-analyzer"

    def get_test_commands(self, file: str) -> List[str]:
        return ["cargo test"]

    def semantic_analyze(self, code: str) -> Dict[str, Any]:
        raise NotImplementedError("Stub: semantic_analyze")
