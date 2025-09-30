from __future__ import annotations

from typing import Any, Dict, List


class JavaScriptLanguageSupport:
    @property
    def lsp_server(self) -> str:
        return "typescript-language-server"

    def get_test_commands(self, file: str) -> List[str]:
        return [f"npm test -- {file}"]

    def semantic_analyze(self, code: str) -> Dict[str, Any]:
        raise NotImplementedError("Stub: semantic_analyze")
