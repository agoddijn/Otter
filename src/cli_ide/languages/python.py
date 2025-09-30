from __future__ import annotations

from typing import Any, Dict, List


class PythonLanguageSupport:
    @property
    def lsp_server(self) -> str:
        return "pyright"

    def get_test_commands(self, file: str) -> List[str]:
        return [f"pytest {file}", f"python -m unittest {file}"]

    def semantic_analyze(self, code: str) -> Dict[str, Any]:
        raise NotImplementedError("Stub: semantic_analyze")
