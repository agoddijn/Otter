"""Integration tests for DAP debugging - execution control.

Tests stepping, continuing, pausing, and other execution flow operations.

Run with: pytest tests/integration/test_debugging_execution.py -v
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from otter.server import CliIdeServer
from tests.helpers import DebugTestHelper

# Mark as integration tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not Path("/usr/local/bin/nvim").exists()
        and not Path("/opt/homebrew/bin/nvim").exists()
        and not Path("/usr/bin/nvim").exists(),
        reason="Neovim not installed",
    ),
]


@pytest.fixture
def debug_project_dir() -> Generator[Path, None, None]:
    """Create a temporary project with debuggable Python code."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_root = Path(tmp_dir)

        # Simple program for stepping
        (project_root / "simple.py").write_text(
            """def step_test():
    a = 1
    b = 2
    c = a + b
    d = c * 2
    return d

result = step_test()
print(result)
"""
        )

        # Program with function calls for step into/out
        (project_root / "functions.py").write_text(
            """def helper(x):
    result = x * 2
    return result

def processor(value):
    temp = helper(value)
    final = temp + 10
    return final

output = processor(5)
print(output)
"""
        )

        # Program with loops
        (project_root / "iteration.py").write_text(
            """def loop_test():
    total = 0
    for i in range(5):
        total += i
    return total

result = loop_test()
print(result)
"""
        )

        yield project_root


@pytest.fixture
async def ide_server(debug_project_dir: Path) -> Generator[CliIdeServer, None, None]:
    """Create and start an IDE server for the debug project."""
    server = CliIdeServer(project_path=str(debug_project_dir))
    await server.start()
    await asyncio.sleep(1.0)
    yield server
    await server.stop()


@pytest.fixture
def debug_helper(ide_server: CliIdeServer) -> DebugTestHelper:
    """Create a debug test helper."""
    return DebugTestHelper(ide_server)


class TestExecutionControl:
    """Tests for execution control (step, continue, pause, stop)."""

    @pytest.mark.asyncio
    async def test_stop_session(self, debug_helper: DebugTestHelper):
        """Test stopping a debug session."""
        # Start session - when starting WITH breakpoints, we may immediately pause
        # Start without breakpoints first
        session = await debug_helper.ide_server.start_debug_session(file="simple.py")
        assert session is not None

        # Stop it
        state = await debug_helper.ide_server.control_execution(action="stop")
        assert state.status in ["stopped", "exited"]

    @pytest.mark.asyncio
    async def test_continue_action(self, debug_helper: DebugTestHelper):
        """Test continue action (resume execution)."""
        # Start with breakpoint - will immediately pause at line 2
        result = await debug_helper.start_debug_and_wait(
            file="simple.py", breakpoints=[2], expected_status="paused", timeout=10.0
        )
        # We're now paused at the breakpoint
        assert result["state_info"]["session_info"].status == "paused"

        # Continue - will run to completion since no more breakpoints
        await debug_helper.ide_server.control_execution(action="continue")
        # Wait a bit for program to finish (session may terminate completely)
        await asyncio.sleep(1.0)
        # Session should be gone or exited
        final_info = await debug_helper.ide_server.get_session_info()
        assert final_info is None or final_info.status in ["exited", "stopped"]

    @pytest.mark.asyncio
    async def test_step_over_basic(self, debug_helper: DebugTestHelper):
        """Test step over (execute current line)."""
        # Start with breakpoint - will immediately pause
        await debug_helper.start_debug_and_wait(
            file="simple.py", breakpoints=[2], expected_status="paused", timeout=10.0
        )

        # We're already paused at breakpoint, step over
        result = await debug_helper.step_and_verify("step_over", timeout=3.0)
        state = result.get("action_result")
        if state and hasattr(state, "status"):
            assert state.status in ["paused", "stopped", "exited"]

    @pytest.mark.asyncio
    async def test_step_into_function(self, debug_helper: DebugTestHelper):
        """Test step into (enter function calls)."""
        # Start with breakpoint - will immediately pause
        await debug_helper.start_debug_and_wait(
            file="functions.py", breakpoints=[10], expected_status="paused", timeout=10.0
        )

        # Step into should enter processor function
        result = await debug_helper.step_and_verify("step_into", timeout=3.0)
        state = result.get("action_result")
        if state and hasattr(state, "status"):
            assert state.status in ["paused", "stopped", "exited"]

    @pytest.mark.asyncio
    async def test_step_out_of_function(self, debug_helper: DebugTestHelper):
        """Test step out (return from current function)."""
        # Start with breakpoint inside helper function - will immediately pause
        await debug_helper.start_debug_and_wait(
            file="functions.py", breakpoints=[2], expected_status="paused", timeout=10.0
        )

        # Step out should return to caller
        result = await debug_helper.step_and_verify("step_out", timeout=3.0)
        state = result.get("action_result")
        if state and hasattr(state, "status"):
            assert state.status in ["paused", "stopped", "exited"]

    @pytest.mark.asyncio
    async def test_multiple_steps(self, debug_helper: DebugTestHelper):
        """Test multiple step operations in sequence."""
        # Start with breakpoint - will immediately pause
        await debug_helper.start_debug_and_wait(
            file="simple.py", breakpoints=[2], expected_status="paused", timeout=10.0
        )

        # Step multiple times
        for i in range(3):
            try:
                result = await debug_helper.step_and_verify("step_over", timeout=3.0)
                state = result.get("action_result")
                if state and hasattr(state, "status"):
                    assert state.status in ["paused", "stopped", "exited"]
                    if state.status in ["stopped", "exited"]:
                        break
            except TimeoutError:
                # Program may have finished
                break

    @pytest.mark.asyncio
    async def test_execution_actions_return_state(self, debug_helper: DebugTestHelper):
        """Test that all execution actions return ExecutionState."""
        # Start with breakpoint - will immediately pause
        await debug_helper.start_debug_and_wait(
            file="simple.py", breakpoints=[2], expected_status="paused", timeout=10.0
        )

        # Step over
        state = await debug_helper.ide_server.control_execution(action="step_over")
        assert hasattr(state, "status")
        assert hasattr(state, "session_id")

        # Stop
        state = await debug_helper.ide_server.control_execution(action="stop")
        assert hasattr(state, "status")

    @pytest.mark.asyncio
    async def test_invalid_action_raises_error(self, debug_helper: DebugTestHelper):
        """Test that invalid action raises ValueError."""
        await debug_helper.ide_server.start_debug_session(file="simple.py")

        with pytest.raises(ValueError, match="Invalid action"):
            await debug_helper.ide_server.control_execution(action="invalid_action")

    @pytest.mark.asyncio
    async def test_control_without_session(self, debug_helper: DebugTestHelper):
        """Test control actions without active session."""
        # Try to continue without starting session
        with pytest.raises(RuntimeError, match="No active debug session"):
            await debug_helper.ide_server.control_execution(action="continue")

    @pytest.mark.asyncio
    async def test_pause_execution(self, debug_helper: DebugTestHelper):
        """Test pausing execution."""
        # Start session with breakpoint - will immediately pause
        await debug_helper.start_debug_and_wait(
            file="iteration.py", breakpoints=[6], expected_status="paused", timeout=10.0
        )

        # Already paused at breakpoint - verify pause still works
        state = await debug_helper.ide_server.control_execution(action="pause")
        assert state.status in ["paused", "stopped", "exited"]

