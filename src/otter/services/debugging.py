from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..bootstrap import ensure_dap_adapter
from ..runtime import RuntimeResolver
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
        self,
        nvim_client: Optional[Any] = None,
        project_path: Optional[str] = None,
        config: Optional[Any] = None,  # OtterConfig
    ) -> None:
        self.nvim_client = nvim_client
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.config = config  # Unified config for LSP and DAP
        self._active_sessions: Dict[str, Dict[str, Any]] = {}  # session_id -> metadata
        
        # 🎯 Generic runtime resolver - works for ALL languages!
        self.runtime_resolver = RuntimeResolver(self.project_path)

    async def start_debug_session(
        self,
        file: Optional[str] = None,
        module: Optional[str] = None,
        configuration: Optional[str] = None,
        breakpoints: Optional[List[int]] = None,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        stop_on_entry: bool = False,
        just_my_code: bool = True,
    ) -> DebugSession:
        """Start a debug session for a file or module.
        
        Must provide either `file` OR `module` parameter.

        Args:
            file: File path to debug (mutually exclusive with module)
            module: Module name to debug (e.g., "uvicorn" for python -m uvicorn)
            configuration: Debug configuration name (e.g., "Launch file", "pytest: current file")
                         If not provided, uses first available config for file type
            breakpoints: Optional list of line numbers to set breakpoints (requires file)
            args: Optional command-line arguments for the program
            env: Optional environment variables to set for the debug session
            cwd: Optional working directory (defaults to project root)
            stop_on_entry: Whether to stop at the first line of the program
            just_my_code: Whether to debug only user code (skip library code)

        Returns:
            DebugSession object with session info

        Raises:
            RuntimeError: If Neovim client not available or debugging fails
            ValueError: If both file and module are provided, or neither is provided
        """
        if not self.nvim_client:
            raise RuntimeError("Neovim client required for debugging")

        # Validate launch specification
        if file and module:
            raise ValueError("Cannot specify both 'file' and 'module' - choose one")
        if not file and not module:
            raise ValueError("Must specify either 'file' or 'module'")
        
        # Determine language from file extension or assume Python for modules
        language = "python"  # Default
        if file:
            file_path_obj = Path(file)
            ext = file_path_obj.suffix.lower()
            if ext == '.py':
                language = 'python'
            elif ext in ['.js', '.ts', '.jsx', '.tsx']:
                language = 'javascript' if ext in ['.js', '.jsx'] else 'typescript'
            elif ext == '.rs':
                language = 'rust'
            elif ext == '.go':
                language = 'go'
        
        # Resolve paths
        file_path = None
        if file:
            file_path = Path(file) if Path(file).is_absolute() else self.project_path / file
            if not file_path.exists():
                raise RuntimeError(f"File not found: {file_path}")

        # 🔋 CRITICAL: Resolve runtime using GENERIC resolver
        # Use the SAME project path as LSP and all other Otter tools
        # LSP and DAP use the EXACT SAME runtime!
        runtime_path = None
        if language in ["python", "javascript", "typescript", "rust", "go"]:
            try:
                runtime = self.runtime_resolver.resolve_runtime(language, self.config)
                
                # 🔑 CRITICAL: For symlinks (UV venvs), use the ORIGINAL path, not resolved!
                # Why: UV venvs work via pyvenv.cfg which is found relative to the symlink
                # Using the resolved path bypasses the venv structure
                if runtime.is_symlink and runtime.original_path:
                    runtime_path = runtime.original_path  # Use .venv/bin/python
                else:
                    runtime_path = runtime.path  # Use resolved path
                
                # 📢 EXPLICIT: Log which runtime we're using
                # This is critical for debugging and transparency
                display_name = {
                    "python": "Python",
                    "javascript": "Node.js",
                    "typescript": "Node.js",
                    "rust": "Rust",
                    "go": "Go",
                }.get(language, language)
                
                icon = {
                    "python": "🐍",
                    "javascript": "📦",
                    "typescript": "📦",
                    "rust": "🦀",
                    "go": "🐹",
                }.get(language, "🔧")
                
                version_str = f" v{runtime.version}" if runtime.version else ""
                print(f"\n{icon} Using {display_name} runtime: {runtime_path}{version_str}")
                print(f"   Source: {runtime.source}")
                
                # Show symlink info for transparency
                if runtime.is_symlink and runtime.original_path:
                    print(f"   (Symlink to: {runtime.path})")
                
                print(f"   (This is the same runtime used by LSP servers)")
            
            except RuntimeError as e:
                # Runtime resolution failed
                raise RuntimeError(
                    f"❌ Could not resolve {language} runtime.\n\n"
                    f"{str(e)}\n\n"
                    f"💡 This runtime is needed for both LSP and DAP.\n"
                    f"   Configure it in .otter.toml or install it system-wide."
                )

        # 🔋 BATTERIES INCLUDED: Ensure debug adapter is available IN THE TARGET RUNTIME
        # CRITICAL: Pass runtime_path so we check/install in the PROJECT's venv, not Otter's!
        try:
            await ensure_dap_adapter(language, auto_install=True, runtime_path=runtime_path)
        except RuntimeError as e:
            # Provide clear, actionable error message
            raise RuntimeError(
                f"❌ Debug adapter not available for {language}.\n\n"
                f"Error: {str(e)}\n\n"
                f"💡 This usually means the debug adapter needs to be installed.\n"
                f"   Otter attempted to install it automatically but failed.\n"
                f"   Please check the error above for details."
            )

        # 🎯 Generate session ID FIRST - Python is the source of truth
        # This ID will be used to track the session in both Python and Lua
        session_id = str(uuid4())
        
        # Start debug session with breakpoints
        # ⚠️  CRITICAL: Breakpoints are now passed to dap_start_session
        # They will be set AFTER the adapter starts but BEFORE execution continues
        result = await self.nvim_client.dap_start_session(
            session_id=session_id,  # 🔑 Pass our session ID to Lua
            filepath=str(file_path) if file_path else None,
            module=module,
            config_name=configuration,
            args=args,
            env=env,
            cwd=str(self.project_path),  # Always use Otter's project
            stop_on_entry=stop_on_entry,
            just_my_code=just_my_code,
            runtime_path=runtime_path,  # 🔋 Generic runtime path (works for all languages!)
            breakpoints=breakpoints if breakpoints and file_path else None,  # 🎯 NEW!
        )
        
        # Build breakpoint info for response
        bp_infos: List[BreakpointInfo] = []
        if breakpoints and file_path:
            bp_infos = [
                BreakpointInfo(
                    id=i,
                    file=str(file_path),
                    line=line,
                    verified=True,  # Assume verified (adapter will confirm)
                    condition=None,
                )
                for i, line in enumerate(breakpoints)
            ]

        if not result or "error" in result:
            error_msg = result.get("error") if result else "Unknown error"
            raise RuntimeError(f"Failed to start debug session: {error_msg}")

        # Session ID was generated above and passed to Lua
        # Lua confirms it in the result
        config_name = result.get("config_name", configuration or "default")

        # Separate stdout and stderr if available
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        combined_output = stdout + stderr if (stdout or stderr) else result.get("output", "")
        
        session = DebugSession(
            session_id=session_id,
            status="running",
            file=str(file_path) if file_path else None,
            module=module,
            configuration=config_name,
            breakpoints=bp_infos,
            output=combined_output,  # Combined for backwards compatibility
            stdout=stdout,
            stderr=stderr,
            pid=result.get("pid"),
            exit_code=None,  # Session just started
            terminated=False,
            uptime_seconds=0.0,
            crash_reason=None,
            launch_args=args,
            launch_env=env,
            launch_cwd=str(self.project_path),  # Always Otter's project
            diagnostic_info=result.get("diagnostic_info", []),  # Include diagnostic logs
        )

        # Track session metadata
        self._active_sessions[session_id] = {
            "file": str(file_path) if file_path else None,
            "module": module,
            "config": config_name,
            "cwd": str(self.project_path),  # Always Otter's project
            "args": args,
            "env": env,
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

    async def get_session_info(
        self, 
        session_id: Optional[str] = None,
        max_output_lines: int = 50
    ) -> Optional[DebugSession]:
        """Get debug session information (current or specific session by ID).

        Args:
            session_id: Optional session ID to query. If None, gets current active session.
                       If provided, can query any session (active or terminated).
            max_output_lines: Maximum lines of stdout/stderr to return (default 50).
                             Set to 0 for all output, -1 for no output.

        Returns:
            DebugSession if found, None otherwise
        """
        if not self.nvim_client:
            return None

        # If session_id provided, use get_session_status (can query any session)
        if session_id:
            try:
                return await self.get_session_status(session_id, max_output_lines)
            except Exception:
                return None

        # Otherwise, get the current active session
        info = await self.nvim_client.dap_get_session_info()
        if not info or info.get("status") == "stopped":
            return None

        found_session_id = info.get("session_id", "unknown")
        metadata = self._active_sessions.get(found_session_id, {})

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

    async def stop_debug_session(self, session_id: str) -> None:
        """Stop a debug session.
        
        Args:
            session_id: Session ID to stop
            
        Raises:
            RuntimeError: If session not found or stop fails
        """
        try:
            await self.control_execution("stop", session_id=session_id)
        except RuntimeError as e:
            # If the session is already stopped, that's fine
            if "No active debug session" in str(e):
                # Clean up tracking anyway
                if session_id in self._active_sessions:
                    del self._active_sessions[session_id]
            else:
                raise

    async def get_session_status(
        self, 
        session_id: str,
        max_output_lines: int = 50
    ) -> DebugSession:
        """Get current debug session status with updated output and PID.
        
        This fetches the latest session state including accumulated output
        from the debugged process.
        
        Args:
            session_id: Session ID to query
            max_output_lines: Maximum lines of stdout/stderr to return (default 50, last N lines).
                             Set to 0 for all output, -1 for no output at all.
            
        Returns:
            DebugSession with current status, PID, and accumulated output
            
        Raises:
            RuntimeError: If session not found or client not available
        """
        if not self.nvim_client:
            raise RuntimeError("Neovim client required")
        
        if session_id not in self._active_sessions:
            raise RuntimeError(f"Session {session_id} not found")
        
        # Get current session state from Neovim
        info = await self.nvim_client.dap_get_session_status(session_id, max_output_lines)
        if not info:
            raise RuntimeError(f"Could not get status for session {session_id}")
        
        metadata = self._active_sessions[session_id]
        
        # Combine stdout and stderr for backwards compatibility
        stdout = info.get("stdout", "")
        stderr = info.get("stderr", "")
        combined_output = stdout + stderr
        
        return DebugSession(
            session_id=session_id,
            status=info.get("status", "unknown"),
            file=metadata.get("file"),
            module=metadata.get("module"),
            configuration=metadata.get("config", "unknown"),
            output=combined_output,  # Combined for backwards compatibility
            stdout=stdout,  # Separate stdout
            stderr=stderr,  # Separate stderr
            stdout_lines_total=info.get("stdout_lines_total", 0),
            stderr_lines_total=info.get("stderr_lines_total", 0),
            stdout_truncated=info.get("stdout_truncated", False),
            stderr_truncated=info.get("stderr_truncated", False),
            pid=info.get("pid"),
            exit_code=info.get("exit_code"),
            terminated=info.get("terminated", False),
            uptime_seconds=info.get("uptime_seconds"),
            crash_reason=info.get("crash_reason"),
            error=info.get("error"),  # Include any error messages
            launch_args=metadata.get("args"),
            launch_env=metadata.get("env"),
            launch_cwd=metadata.get("cwd"),
            diagnostic_info=info.get("diagnostic_info", []),  # Include diagnostic logs
        )

    def list_active_sessions(self) -> List[str]:
        """List active debug session IDs.

        Returns:
            List of session IDs
        """
        return list(self._active_sessions.keys())

