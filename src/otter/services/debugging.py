from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..models.responses import (
    BreakpointInfo,
    DebugSession,
    EvaluateResult,
    ExecutionState,
    Scope,
    StackFrame,
    Variable,
)


class DebugService:
    """Service for language-agnostic debugging via DAP (Debug Adapter Protocol).
    
    Uses Neovim's nvim-dap client to communicate with debug adapters,
    similar to how we use Neovim's LSP client for language intelligence.
    
    This enables debugging for multiple languages without reimplementing DAP:
    - Python (debugpy)
    - JavaScript/TypeScript (node-debug2, vscode-js-debug)
    - Rust (lldb-vscode, codelldb)
    - Go (delve)
    """

    def __init__(
        self, nvim_client: Optional[Any] = None, project_path: Optional[str] = None
    ) -> None:
        self.nvim_client = nvim_client
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self._active_sessions: Dict[str, Dict[str, Any]] = {}  # session_id -> metadata

    async def start_debug_session(
        self,
        file: str,
        configuration: Optional[str] = None,
        breakpoints: Optional[List[int]] = None,
        args: Optional[List[str]] = None,
    ) -> DebugSession:
        """Start a debug session for a file.

        Args:
            file: File path to debug
            configuration: Debug configuration name (e.g., "Launch file", "pytest: current file")
                         If not provided, uses first available config for file type
            breakpoints: Optional list of line numbers to set breakpoints
            args: Optional command-line arguments

        Returns:
            DebugSession object with session info

        Raises:
            RuntimeError: If Neovim client not available or debugging fails
        """
        if not self.nvim_client:
            raise RuntimeError("Neovim client required for debugging")

        # Resolve file path
        file_path = Path(file) if Path(file).is_absolute() else self.project_path / file
        if not file_path.exists():
            raise RuntimeError(f"File not found: {file_path}")

        # Set breakpoints if provided
        bp_infos: List[BreakpointInfo] = []
        if breakpoints:
            bp_results = await self.nvim_client.dap_set_breakpoints(
                str(file_path), breakpoints
            )
            if bp_results:
                bp_infos = [
                    BreakpointInfo(
                        id=i,
                        file=str(file_path),
                        line=bp["line"],
                        verified=bp.get("verified", True),
                        condition=bp.get("condition"),
                    )
                    for i, bp in enumerate(bp_results)
                ]

        # Start debug session
        result = await self.nvim_client.dap_start_session(
            str(file_path), configuration, args
        )

        if not result or "error" in result:
            error_msg = result.get("error") if result else "Unknown error"
            raise RuntimeError(f"Failed to start debug session: {error_msg}")

        # Create session object
        session_id = result.get("session_id", str(uuid4()))
        config_name = result.get("config_name", configuration or "default")

        session = DebugSession(
            session_id=session_id,
            status="running",
            file=str(file_path),
            configuration=config_name,
            breakpoints=bp_infos,
        )

        # Track session
        self._active_sessions[session_id] = {
            "file": str(file_path),
            "config": config_name,
        }

        return session

    async def control_execution(
        self,
        action: str,
        session_id: Optional[str] = None,
    ) -> ExecutionState:
        """Control debug execution (continue, step, pause, stop).

        Args:
            action: One of "continue", "step_over", "step_into", "step_out", "pause", "stop"
            session_id: Optional session ID (uses active session if not provided)

        Returns:
            ExecutionState with current status

        Raises:
            RuntimeError: If no active session or action fails
        """
        if not self.nvim_client:
            raise RuntimeError("Neovim client required for debugging")

        # Execute action
        result = None
        if action == "continue":
            result = await self.nvim_client.dap_continue()
        elif action == "step_over":
            result = await self.nvim_client.dap_step_over()
        elif action == "step_into":
            result = await self.nvim_client.dap_step_into()
        elif action == "step_out":
            result = await self.nvim_client.dap_step_out()
        elif action == "pause":
            result = await self.nvim_client.dap_pause()
        elif action == "stop":
            result = await self.nvim_client.dap_stop()
            # Clean up session tracking
            if session_id and session_id in self._active_sessions:
                del self._active_sessions[session_id]
        else:
            raise ValueError(
                f"Invalid action: {action}. Must be one of: "
                "continue, step_over, step_into, step_out, pause, stop"
            )

        if not result or "error" in result:
            error_msg = result.get("error") if result else "Unknown error"
            raise RuntimeError(f"Failed to {action}: {error_msg}")

        # Get current execution state
        session_info = await self.nvim_client.dap_get_session_info()
        if not session_info:
            # Session ended
            return ExecutionState(
                session_id=session_id or "unknown",
                status="stopped",
            )

        # Get stack frames if paused
        stack_frames: List[StackFrame] = []
        if session_info.get("status") == "paused":
            frames = await self.nvim_client.dap_get_stack_frames()
            if frames:
                stack_frames = [
                    StackFrame(
                        id=frame["id"],
                        name=frame["name"],
                        file=frame["file"],
                        line=frame["line"],
                        column=frame["column"],
                    )
                    for frame in frames
                ]

        return ExecutionState(
            session_id=session_info.get("session_id", session_id or "unknown"),
            status=session_info.get("status", "running"),
            thread_id=session_info.get("thread_id"),
            stack_frames=stack_frames,
        )

    async def inspect_state(
        self,
        frame_id: Optional[int] = None,
        expression: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Inspect program state (variables, stack, evaluate expression).

        Args:
            frame_id: Optional stack frame ID (uses top frame if not provided)
            expression: Optional expression to evaluate

        Returns:
            Dict with:
            - stack_frames: List[StackFrame] - Call stack
            - scopes: List[Scope] - Variable scopes (if frame_id provided)
            - variables: Dict[str, List[Variable]] - Variables by scope (if frame_id provided)
            - evaluation: EvaluateResult - Evaluation result (if expression provided)

        Raises:
            RuntimeError: If no active session
        """
        if not self.nvim_client:
            raise RuntimeError("Neovim client required for debugging")

        result: Dict[str, Any] = {}

        # Get stack frames
        frames = await self.nvim_client.dap_get_stack_frames()
        if frames:
            result["stack_frames"] = [
                StackFrame(
                    id=frame["id"],
                    name=frame["name"],
                    file=frame["file"],
                    line=frame["line"],
                    column=frame["column"],
                )
                for frame in frames
            ]

            # If no frame_id specified, use top frame
            if frame_id is None and frames:
                frame_id = frames[0]["id"]
        else:
            result["stack_frames"] = []

        # Get scopes and variables if frame specified
        if frame_id is not None:
            scopes = await self.nvim_client.dap_get_scopes(frame_id)
            if scopes:
                result["scopes"] = [
                    Scope(
                        name=scope["name"],
                        variables_reference=scope["variables_reference"],
                        expensive=scope.get("expensive", False),
                    )
                    for scope in scopes
                ]

                # Get variables for each scope
                variables_by_scope: Dict[str, List[Variable]] = {}
                for scope in scopes:
                    scope_name = scope["name"]
                    vars_ref = scope["variables_reference"]
                    if vars_ref > 0:
                        variables = await self.nvim_client.dap_get_variables(vars_ref)
                        if variables:
                            variables_by_scope[scope_name] = [
                                Variable(
                                    name=var["name"],
                                    value=var["value"],
                                    type=var.get("type"),
                                    variables_reference=var.get("variables_reference", 0),
                                )
                                for var in variables
                            ]

                result["variables"] = variables_by_scope

        # Evaluate expression if provided
        if expression:
            eval_result = await self.nvim_client.dap_evaluate(expression, frame_id)
            if eval_result and "error" not in eval_result:
                result["evaluation"] = EvaluateResult(
                    result=eval_result["result"],
                    type=eval_result.get("type"),
                    variables_reference=eval_result.get("variables_reference", 0),
                )
            elif eval_result and "error" in eval_result:
                result["evaluation"] = EvaluateResult(
                    result=f"Error: {eval_result['error']}"
                )

        return result

    async def set_breakpoints(
        self,
        file: str,
        lines: List[int],
        conditions: Optional[Dict[int, str]] = None,
    ) -> List[BreakpointInfo]:
        """Set or update breakpoints in a file.

        Args:
            file: File path
            lines: Line numbers for breakpoints (1-indexed)
            conditions: Optional conditions for breakpoints {line: condition}

        Returns:
            List of BreakpointInfo objects

        Raises:
            RuntimeError: If Neovim client not available
        """
        if not self.nvim_client:
            raise RuntimeError("Neovim client required for debugging")

        file_path = Path(file) if Path(file).is_absolute() else self.project_path / file

        result = await self.nvim_client.dap_set_breakpoints(
            str(file_path), lines, conditions
        )

        if not result:
            return []

        return [
            BreakpointInfo(
                id=i,
                file=str(file_path),
                line=bp["line"],
                verified=bp.get("verified", True),
                condition=bp.get("condition"),
            )
            for i, bp in enumerate(result)
        ]

    async def get_session_info(self) -> Optional[DebugSession]:
        """Get current debug session information.

        Returns:
            DebugSession if active, None otherwise
        """
        if not self.nvim_client:
            return None

        info = await self.nvim_client.dap_get_session_info()
        if not info or info.get("status") == "stopped":
            return None

        session_id = info.get("session_id", "unknown")
        metadata = self._active_sessions.get(session_id, {})

        # Get current stack frames to find current position
        frames = await self.nvim_client.dap_get_stack_frames()
        current_file = None
        current_line = None
        if frames and len(frames) > 0:
            current_file = frames[0].get("file")
            current_line = frames[0].get("line")

        return DebugSession(
            session_id=session_id,
            status=info.get("status", "running"),
            file=metadata.get("file", "unknown"),
            configuration=metadata.get("config", "unknown"),
            current_file=current_file,
            current_line=current_line,
        )

    def list_active_sessions(self) -> List[str]:
        """List active debug session IDs.

        Returns:
            List of session IDs
        """
        return list(self._active_sessions.keys())

