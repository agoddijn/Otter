"""Helper utilities for DAP debugging integration tests.

Provides robust polling and state verification to avoid race conditions.
"""

import asyncio
from typing import Any, Callable, Dict, Optional, TypeVar
from dataclasses import dataclass

T = TypeVar("T")


@dataclass
class PollConfig:
    """Configuration for polling operations."""

    max_attempts: int = 20  # Maximum polling attempts
    initial_delay: float = 0.1  # Initial delay in seconds
    max_delay: float = 2.0  # Maximum delay between attempts
    backoff_factor: float = 1.5  # Exponential backoff multiplier


class DebugTestHelper:
    """Helper class for robust debug testing.

    Provides utilities to:
    - Poll for expected states with exponential backoff
    - Verify state transitions
    - Wait for debugger readiness
    - Provide clear error messages on timeout
    """

    def __init__(self, ide_server: Any, poll_config: Optional[PollConfig] = None):
        """Initialize helper with IDE server instance.

        Args:
            ide_server: CliIdeServer instance
            poll_config: Optional polling configuration
        """
        self.ide_server = ide_server
        self.config = poll_config or PollConfig()

    async def wait_for_state(
        self,
        expected_status: str,
        timeout: float = 5.0,
        context: str = "operation",
    ) -> Dict[str, Any]:
        """Wait for debugger to reach a specific state.

        Args:
            expected_status: Expected status ("paused", "running", "stopped", "exited")
            timeout: Maximum time to wait in seconds
            context: Description for error messages

        Returns:
            Session info when expected state is reached

        Raises:
            TimeoutError: If state is not reached within timeout
        """
        start_time = asyncio.get_event_loop().time()
        delay = self.config.initial_delay
        attempts = 0

        while True:
            attempts += 1
            elapsed = asyncio.get_event_loop().time() - start_time

            if elapsed > timeout:
                # Get final state for error message
                try:
                    final_state = await self.ide_server.get_session_info()
                    state_desc = (
                        f"status={final_state.status}" if final_state else "no session"
                    )
                except Exception as e:
                    state_desc = f"error getting state: {e}"

                raise TimeoutError(
                    f"Timeout waiting for state '{expected_status}' during {context}. "
                    f"Attempts: {attempts}, Elapsed: {elapsed:.2f}s, Final state: {state_desc}"
                )

            # Check current state
            try:
                session_info = await self.ide_server.get_session_info()
                if session_info and session_info.status == expected_status:
                    return {
                        "session_info": session_info,
                        "attempts": attempts,
                        "elapsed": elapsed,
                    }
            except Exception:
                # Session might not exist yet, continue polling
                pass

            # Exponential backoff
            await asyncio.sleep(delay)
            delay = min(delay * self.config.backoff_factor, self.config.max_delay)

    async def wait_for_session_ready(self, timeout: float = 3.0) -> Dict[str, Any]:
        """Wait for a debug session to be created and ready.

        Args:
            timeout: Maximum time to wait

        Returns:
            Session info

        Raises:
            TimeoutError: If session not ready within timeout
        """
        start_time = asyncio.get_event_loop().time()
        delay = self.config.initial_delay

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(
                    f"Timeout waiting for debug session to be ready. Elapsed: {elapsed:.2f}s"
                )

            try:
                session_info = await self.ide_server.get_session_info()
                if session_info is not None:
                    return {"session_info": session_info, "elapsed": elapsed}
            except Exception:
                pass

            await asyncio.sleep(delay)
            delay = min(delay * self.config.backoff_factor, self.config.max_delay)

    async def poll_until(
        self,
        condition: Callable[[], bool],
        timeout: float = 5.0,
        context: str = "condition",
    ) -> bool:
        """Poll until a condition is met.

        Args:
            condition: Callable that returns True when condition is met
            timeout: Maximum time to wait
            context: Description for error messages

        Returns:
            True if condition met

        Raises:
            TimeoutError: If condition not met within timeout
        """
        start_time = asyncio.get_event_loop().time()
        delay = self.config.initial_delay

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(
                    f"Timeout waiting for {context}. Elapsed: {elapsed:.2f}s"
                )

            if condition():
                return True

            await asyncio.sleep(delay)
            delay = min(delay * self.config.backoff_factor, self.config.max_delay)

    async def execute_with_state_verification(
        self,
        action: Callable,
        expected_status: str,
        timeout: float = 5.0,
        context: str = "action",
    ) -> Dict[str, Any]:
        """Execute an action and verify the resulting state.

        Args:
            action: Async callable to execute
            expected_status: Expected status after action
            timeout: Maximum time to wait for expected state
            context: Description for error messages

        Returns:
            Dict with action result and final state
        """
        # Execute action
        action_result = await action()

        # Wait for expected state
        state_info = await self.wait_for_state(
            expected_status, timeout=timeout, context=context
        )

        return {
            "action_result": action_result,
            "state_info": state_info,
        }

    async def start_debug_and_wait(
        self,
        file: str,
        breakpoints: Optional[list] = None,
        expected_status: str = "running",
        timeout: float = 5.0,
    ) -> Dict[str, Any]:
        """Start a debug session and wait for it to be ready.

        Args:
            file: File to debug
            breakpoints: Optional breakpoint lines
            expected_status: Expected status after start
            timeout: Maximum time to wait

        Returns:
            Dict with session and state info
        """
        # Start session
        session = await self.ide_server.start_debug_session(
            file=file, breakpoints=breakpoints
        )

        # Wait for ready state
        state_info = await self.wait_for_state(
            expected_status, timeout=timeout, context=f"start_debug_session({file})"
        )

        return {
            "session": session,
            "state_info": state_info,
        }

    async def continue_and_wait_for_breakpoint(
        self, timeout: float = 5.0
    ) -> Dict[str, Any]:
        """Continue execution and wait for breakpoint to be hit.

        Args:
            timeout: Maximum time to wait

        Returns:
            Execution state
        """
        # Continue execution
        await self.ide_server.control_execution(action="continue")

        # Wait for paused state (breakpoint hit)
        state_info = await self.wait_for_state(
            "paused", timeout=timeout, context="continue_and_wait_for_breakpoint"
        )

        return state_info

    async def step_and_verify(
        self, action: str, timeout: float = 3.0
    ) -> Dict[str, Any]:
        """Execute a step action and verify it completes.

        Args:
            action: Step action ("step_over", "step_into", "step_out")
            timeout: Maximum time to wait

        Returns:
            Execution state
        """
        # Execute step
        state = await self.ide_server.control_execution(action=action)

        # Verify we're in paused state (or finished)
        if state.status not in ["paused", "stopped", "exited"]:
            # Wait for state to settle
            state_info = await self.wait_for_state(
                "paused",
                timeout=timeout,
                context=f"step_and_verify({action})",
            )
            return state_info

        return {"action_result": state}
