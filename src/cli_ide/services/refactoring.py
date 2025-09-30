from __future__ import annotations

from typing import Any, List, Optional, Union

from ..models.responses import ExtractResult, RenamePreview, RenameResult


class RefactoringService:
    def __init__(self, nvim_client: Optional[Any] = None) -> None:
        self.nvim_client = nvim_client

    async def rename_symbol(
        self, old_name: str, new_name: str, preview: bool = True
    ) -> Union[RenamePreview, RenameResult]:
        raise NotImplementedError("Stub: rename_symbol")

    async def extract_function(
        self,
        file: str,
        start_line: int,
        end_line: int,
        function_name: str,
        target_line: Optional[int] = None,
    ) -> ExtractResult:
        raise NotImplementedError("Stub: extract_function")
