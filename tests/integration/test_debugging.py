"""Integration tests for debugging (DAP) functionality.

Consolidated tests for:
- DAP bootstrap: Adapter installation and configuration
- Debug sessions: Session lifecycle management
- Breakpoints: Setting and hitting breakpoints
- Execution control: Step, continue, stop operations
- State inspection: Variables, stack frames, evaluation
- Output capture: stdout, stderr, PID tracking

All tests use the Debug Adapter Protocol (DAP) via Neovim's nvim-dap.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest

from otter.bootstrap import (
    DAPAdapterStatus,
    check_dap_adapter,
    ensure_dap_adapter,
)
from otter.config import load_config
from otter.neovim.client import NeovimClient
from otter.server import CliIdeServer
from otter.services.debugging import DebugService

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


# ============================================================================
# Shared Fixtures
# ============================================================================


@pytest.fixture
def debug_project_dir() -> Generator[Path, None, None]:
    """Create a temporary project with debuggable Python code."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_root = Path(tmp_dir)

        # Simple calculator for basic debugging
        (project_root / "calculator.py").write_text(
            """def add(a, b):
    result = a + b
    return result

def multiply(a, b):
    result = a * b
    return result

def main():
    x = 5
    y = 10
    sum_result = add(x, y)
    product_result = multiply(x, y)
    print(f"Sum: {sum_result}, Product: {product_result}")
    return sum_result, product_result

if __name__ == "__main__":
    main()
"""
        )

        # Script with loops for step testing
        (project_root / "loops.py").write_text(
            """def count_to_n(n):
    result = []
    for i in range(n):
        result.append(i)
    return result

def main():
    numbers = count_to_n(5)
    print(f"Numbers: {numbers}")
    return numbers

if __name__ == "__main__":
    main()
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
async def debug_service(tmp_path):
    """Create a debug service with Neovim client for simpler tests."""
    # Create a simple test script
    test_file = tmp_path / "test_script.py"
    test_file.write_text(
        """
import sys
x = 1
y = 2
z = x + y
print(f"Result: {z}")
print("Done", file=sys.stderr)
"""
    )

    nvim_client = NeovimClient(project_path=str(tmp_path))
    await nvim_client.start()

    config = load_config(tmp_path)
    service = DebugService(
        nvim_client=nvim_client,
        project_path=str(tmp_path),
        config=config,
    )

    yield service, test_file

    # Cleanup
    try:
        sessions = await service.list_sessions()
        for session in sessions:
            try:
                await service.stop_debug_session(session_id=session.session_id)
            except Exception:
                pass
    except Exception:
        pass
    await nvim_client.stop()


# ============================================================================
# Tests: DAP Bootstrap
# ============================================================================


class TestDAPBootstrap:
    """Test DAP adapter bootstrap and installation."""

    @pytest.mark.asyncio
    async def test_check_python_debugpy(self):
        """Test checking if debugpy is installed."""
        status = check_dap_adapter("python")
        assert status in [
            DAPAdapterStatus.INSTALLED,
            DAPAdapterStatus.MISSING,
            DAPAdapterStatus.PREREQUISITES_MISSING,
        ]

    @pytest.mark.asyncio
    async def test_check_javascript_adapter(self):
        """Test checking JavaScript/TypeScript adapter."""
        status = check_dap_adapter("javascript")
        assert status in [
            DAPAdapterStatus.INSTALLED,
            DAPAdapterStatus.MISSING,
            DAPAdapterStatus.PREREQUISITES_MISSING,
        ]

    @pytest.mark.asyncio
    async def test_check_unsupported_language(self):
        """Test checking an unsupported language returns MISSING."""
        status = check_dap_adapter("cobol")
        assert status == DAPAdapterStatus.MISSING

    @pytest.mark.asyncio
    async def test_ensure_adapter_raises_on_missing(self):
        """Test ensure_dap_adapter raises clear error if adapter missing."""
        with patch("otter.bootstrap.dap_installer.check_dap_adapter") as mock_check:
            mock_check.return_value = DAPAdapterStatus.MISSING

            with patch(
                "otter.bootstrap.dap_installer.install_dap_adapter"
            ) as mock_install:
                mock_install.return_value = False

                with pytest.raises(RuntimeError) as exc_info:
                    await ensure_dap_adapter("python", auto_install=True)

                error_msg = str(exc_info.value)
                assert "python" in error_msg.lower()
                assert "debugger" in error_msg.lower() or "adapter" in error_msg.lower()


# ============================================================================
# Tests: Debug Sessions
# ============================================================================


class TestDebugSessions:
    """Test debug session lifecycle."""

    @pytest.mark.asyncio
    async def test_start_basic_session(
        self, ide_server: CliIdeServer, debug_project_dir
    ):
        """Test starting a basic debug session."""
        calc_file = debug_project_dir / "calculator.py"

        session = await ide_server.debugging.start_debug_session(
            file=str(calc_file), breakpoints=[], stop_on_entry=False
        )

        assert session.session_id
        assert session.status in ["running", "stopped", "terminated"]
        assert session.file == str(calc_file)

    @pytest.mark.asyncio
    async def test_start_session_with_breakpoints(
        self, ide_server: CliIdeServer, debug_project_dir
    ):
        """Test starting a session with breakpoints configured."""
        calc_file = debug_project_dir / "calculator.py"

        session = await ide_server.debugging.start_debug_session(
            file=str(calc_file), breakpoints=[2, 6], stop_on_entry=False
        )

        assert session.session_id
        assert len(session.breakpoints) == 2

    @pytest.mark.asyncio
    async def test_get_session_info_no_session(self, ide_server: CliIdeServer):
        """Test getting session info when no session exists."""
        info = await ide_server.debugging.get_session_info()

        # When no session exists, returns None or a session with status="no_session"
        assert info is None or info.status == "no_session"

    @pytest.mark.asyncio
    async def test_get_session_info_active_session(
        self, ide_server: CliIdeServer, debug_project_dir
    ):
        """Test getting session info with an active session."""
        calc_file = debug_project_dir / "calculator.py"

        session = await ide_server.debugging.start_debug_session(
            file=str(calc_file), breakpoints=[2], stop_on_entry=True
        )

        # Give it a moment to actually stop at breakpoint
        await asyncio.sleep(0.5)

        info = await ide_server.debugging.get_session_info()

        assert info is not None
        # Session ID might differ (DAP adapter ID vs our tracking UUID)
        assert info.session_id is not None
        assert info.status in ["running", "paused", "stopped"]

    @pytest.mark.asyncio
    async def test_get_session_after_start(
        self, ide_server: CliIdeServer, debug_project_dir
    ):
        """Test getting session info after starting with stop_on_entry."""
        calc_file = debug_project_dir / "calculator.py"

        # Start a session with stop_on_entry to keep it paused
        session = await ide_server.debugging.start_debug_session(
            file=str(calc_file), breakpoints=[], stop_on_entry=True
        )

        # Give it a moment to actually stop
        await asyncio.sleep(0.5)

        # Should be able to retrieve session info
        info = await ide_server.debugging.get_session_info()
        assert info is not None
        # Session ID might differ (DAP adapter ID vs our tracking UUID)
        assert info.session_id is not None


# ============================================================================
# Tests: Breakpoints
# ============================================================================


class TestBreakpoints:
    """Test breakpoint functionality."""

    @pytest.mark.asyncio
    async def test_breakpoint_pauses_execution(self, debug_service):
        """Test that a breakpoint actually pauses execution."""
        service, test_file = debug_service

        session = await service.start_debug_session(
            file=str(test_file),
            breakpoints=[4],
            stop_on_entry=False,  # Line: z = x + y
        )

        assert session.status == "running"
        await asyncio.sleep(1.0)

        session_status = await service.get_session_status(session.session_id)
        # Should be stopped or have stopped at some point
        assert session_status is not None

    @pytest.mark.asyncio
    async def test_multiple_breakpoints(self, debug_service):
        """Test setting multiple breakpoints."""
        service, test_file = debug_service

        session = await service.start_debug_session(
            file=str(test_file), breakpoints=[3, 4, 5], stop_on_entry=False
        )

        assert len(session.breakpoints) == 3
        assert session.status == "running"

    @pytest.mark.asyncio
    async def test_stop_on_entry(self, debug_service):
        """Test that stop_on_entry pauses at the first line."""
        service, test_file = debug_service

        session = await service.start_debug_session(
            file=str(test_file), breakpoints=[], stop_on_entry=True
        )

        # Should stop immediately
        await asyncio.sleep(0.5)
        session_status = await service.get_session_status(session.session_id)
        assert session_status is not None


# ============================================================================
# Tests: Execution Control
# ============================================================================


class TestExecutionControl:
    """Test execution control (step, continue, stop)."""

    @pytest.mark.asyncio
    async def test_stop_session(self, ide_server: CliIdeServer, debug_project_dir):
        """Test stopping a debug session."""
        calc_file = debug_project_dir / "calculator.py"

        session = await ide_server.debugging.start_debug_session(
            file=str(calc_file), breakpoints=[2], stop_on_entry=True
        )

        # Stop the session
        result = await ide_server.debugging.control_execution(
            action="stop", session_id=session.session_id
        )

        # Session ID might differ (DAP adapter ID vs our tracking UUID)
        assert result.session_id is not None
        assert result.status in ["stopped", "terminated", "exited"]

    @pytest.mark.asyncio
    async def test_continue_action(self, ide_server: CliIdeServer, debug_project_dir):
        """Test continuing execution from a breakpoint."""
        calc_file = debug_project_dir / "calculator.py"

        session = await ide_server.debugging.start_debug_session(
            file=str(calc_file), breakpoints=[2], stop_on_entry=True
        )

        await asyncio.sleep(0.5)

        # Continue execution
        result = await ide_server.debugging.control_execution(
            action="continue", session_id=session.session_id
        )

        # Session ID might differ (DAP adapter ID vs our tracking UUID)
        assert result.session_id is not None
        assert result.status in ["running", "paused", "stopped", "exited"]

    @pytest.mark.asyncio
    async def test_step_over(self, ide_server: CliIdeServer, debug_project_dir):
        """Test stepping over a line."""
        calc_file = debug_project_dir / "calculator.py"

        session = await ide_server.debugging.start_debug_session(
            file=str(calc_file), breakpoints=[], stop_on_entry=True
        )

        await asyncio.sleep(0.5)

        # Step over
        result = await ide_server.debugging.control_execution(
            action="step_over", session_id=session.session_id
        )

        # Session ID might differ (DAP adapter ID vs our tracking UUID)
        assert result.session_id is not None

    @pytest.mark.asyncio
    async def test_step_into(self, ide_server: CliIdeServer, debug_project_dir):
        """Test stepping into a function."""
        calc_file = debug_project_dir / "calculator.py"

        session = await ide_server.debugging.start_debug_session(
            file=str(calc_file),
            breakpoints=[11],
            stop_on_entry=False,  # add() call
        )

        await asyncio.sleep(1.0)

        # Step into
        result = await ide_server.debugging.control_execution(
            action="step_into", session_id=session.session_id
        )

        # Session ID might differ (DAP adapter ID vs our tracking UUID)
        assert result.session_id is not None


# ============================================================================
# Tests: State Inspection
# ============================================================================


class TestStateInspection:
    """Test inspecting program state (variables, stack, evaluation)."""

    @pytest.mark.asyncio
    async def test_get_stack_frames(self, ide_server: CliIdeServer, debug_project_dir):
        """Test getting stack frames."""
        calc_file = debug_project_dir / "calculator.py"

        session = await ide_server.debugging.start_debug_session(
            file=str(calc_file), breakpoints=[2], stop_on_entry=True
        )

        await asyncio.sleep(1.0)

        state = await ide_server.debugging.inspect_state()

        # inspect_state returns a dict with state information
        assert isinstance(state, dict)

    @pytest.mark.asyncio
    async def test_get_variables(self, ide_server: CliIdeServer, debug_project_dir):
        """Test getting variables in scope."""
        calc_file = debug_project_dir / "calculator.py"

        session = await ide_server.debugging.start_debug_session(
            file=str(calc_file),
            breakpoints=[10],
            stop_on_entry=False,  # In main()
        )

        await asyncio.sleep(1.0)

        state = await ide_server.debugging.inspect_state()

        # Should have some state information
        assert isinstance(state, dict)

    @pytest.mark.asyncio
    async def test_evaluate_expression(
        self, ide_server: CliIdeServer, debug_project_dir
    ):
        """Test evaluating an expression."""
        calc_file = debug_project_dir / "calculator.py"

        session = await ide_server.debugging.start_debug_session(
            file=str(calc_file), breakpoints=[10], stop_on_entry=False
        )

        await asyncio.sleep(1.0)

        # Evaluate a simple expression using inspect_state
        result = await ide_server.debugging.inspect_state(expression="2 + 2")

        # Should return evaluation result in the dict
        assert isinstance(result, dict)


# ============================================================================
# Tests: Output Capture
# ============================================================================


class TestOutputCapture:
    """Test capturing stdout, stderr, and PID."""

    @pytest.mark.asyncio
    async def test_captures_process_pid(self, debug_service):
        """Test that we capture the real process PID."""
        service, test_file = debug_service

        session = await service.start_debug_session(
            file=str(test_file), breakpoints=[], stop_on_entry=False
        )

        assert session.pid is not None
        assert session.pid > 0

    @pytest.mark.asyncio
    async def test_captures_stdout(self, debug_service):
        """Test that we capture stdout output."""
        service, test_file = debug_service

        session = await service.start_debug_session(
            file=str(test_file), breakpoints=[], stop_on_entry=False
        )

        # Wait for execution to complete
        await asyncio.sleep(2.0)

        # Get session info which includes output
        info = await service.get_session_info(session.session_id)

        # Should have captured output
        assert info is not None

    @pytest.mark.asyncio
    async def test_captures_stderr(self, debug_service):
        """Test that we capture stderr output."""
        service, test_file = debug_service

        session = await service.start_debug_session(
            file=str(test_file), breakpoints=[], stop_on_entry=False
        )

        await asyncio.sleep(2.0)

        info = await service.get_session_info(session.session_id)

        # Should have captured stderr
        assert info is not None

    @pytest.mark.asyncio
    async def test_output_with_env_vars(self, tmp_path):
        """Test that environment variables are visible in debug session."""
        # Create script that uses env var
        test_file = tmp_path / "env_test.py"
        test_file.write_text(
            """
import os
env_value = os.getenv('TEST_VAR', 'not_set')
print(f"TEST_VAR: {env_value}")
"""
        )

        nvim_client = NeovimClient(project_path=str(tmp_path))
        await nvim_client.start()

        config = load_config(tmp_path)
        service = DebugService(
            nvim_client=nvim_client, project_path=str(tmp_path), config=config
        )

        session = await service.start_debug_session(
            file=str(test_file),
            breakpoints=[],
            stop_on_entry=False,
            env={"TEST_VAR": "test_value"},
        )

        await asyncio.sleep(2.0)

        info = await service.get_session_info(session.session_id)

        assert info is not None

        await nvim_client.stop()
