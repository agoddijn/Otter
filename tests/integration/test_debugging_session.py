"""Integration tests for DAP debugging - session management.

Note: These are integration tests requiring:
- Neovim with nvim-dap installed
- debugpy installed (pip install debugpy)

Run with: pytest tests/integration/test_debugging_session.py -v
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from otter.server import CliIdeServer

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

        # Create a simple debuggable Python file
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

        # Create a file with loops and conditions for step testing
        (project_root / "loops.py").write_text(
            """def count_to_n(n):
    result = []
    for i in range(n):
        result.append(i)
    return result

def conditional_logic(value):
    if value > 10:
        return "high"
    elif value > 5:
        return "medium"
    else:
        return "low"

def main():
    numbers = count_to_n(5)
    classification = conditional_logic(7)
    print(f"Numbers: {numbers}, Class: {classification}")
    return numbers, classification

if __name__ == "__main__":
    main()
"""
        )

        # Create a file that raises an exception
        (project_root / "errors.py").write_text(
            """def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def main():
    try:
        result = divide(10, 0)
        print(result)
    except ValueError as e:
        print(f"Error: {e}")
        raise

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
    # Give LSP and DAP time to initialize
    await asyncio.sleep(1.0)
    yield server
    await server.stop()


class TestDebugSession:
    """Tests for debug session management."""

    @pytest.mark.asyncio
    async def test_start_debug_session_basic(self, ide_server: CliIdeServer):
        """Test starting a basic debug session."""
        # Start debug session without breakpoints
        session = await ide_server.start_debug_session(file="calculator.py")

        assert session is not None
        assert session.session_id is not None
        assert session.file.endswith("calculator.py")
        assert session.status in ["running", "stopped", "exited"]
        assert session.configuration is not None

    @pytest.mark.asyncio
    async def test_start_debug_session_with_breakpoints(
        self, ide_server: CliIdeServer
    ):
        """Test starting a debug session with breakpoints."""
        # Start with breakpoints at lines 2 and 6
        session = await ide_server.start_debug_session(
            file="calculator.py", breakpoints=[2, 6]
        )

        assert session is not None
        assert len(session.breakpoints) == 2
        assert session.breakpoints[0].line == 2
        assert session.breakpoints[0].verified is True
        assert session.breakpoints[1].line == 6

    @pytest.mark.asyncio
    async def test_set_breakpoints_after_start(self, ide_server: CliIdeServer):
        """Test setting breakpoints after session starts."""
        # Start session first
        await ide_server.start_debug_session(file="calculator.py")

        # Set breakpoints dynamically
        breakpoints = await ide_server.set_breakpoints(
            file="calculator.py", lines=[10, 11, 12]
        )

        assert len(breakpoints) == 3
        assert all(bp.verified for bp in breakpoints)
        assert [bp.line for bp in breakpoints] == [10, 11, 12]

    @pytest.mark.asyncio
    async def test_conditional_breakpoint(self, ide_server: CliIdeServer):
        """Test setting a conditional breakpoint."""
        # Start session
        await ide_server.start_debug_session(file="loops.py")

        # Set conditional breakpoint
        breakpoints = await ide_server.set_breakpoints(
            file="loops.py", lines=[3], conditions={3: "i > 2"}
        )

        assert len(breakpoints) == 1
        assert breakpoints[0].condition == "i > 2"
        assert breakpoints[0].verified is True

    @pytest.mark.asyncio
    async def test_get_session_info_no_session(self, ide_server: CliIdeServer):
        """Test getting session info when no session is active."""
        info = await ide_server.get_session_info()
        assert info is None

    @pytest.mark.asyncio
    async def test_get_session_info_active_session(self, ide_server: CliIdeServer):
        """Test getting session info for active session."""
        # Start session
        await ide_server.start_debug_session(file="calculator.py", breakpoints=[2])

        # Get session info
        info = await ide_server.get_session_info()
        assert info is not None
        assert info.session_id is not None
        assert info.status in ["running", "paused", "stopped", "exited"]

    @pytest.mark.asyncio
    async def test_debug_different_file_types(self, ide_server: CliIdeServer):
        """Test that we can start sessions for different files."""
        # Test with calculator
        session1 = await ide_server.start_debug_session(file="calculator.py")
        assert session1.file.endswith("calculator.py")

        # Stop first session
        await ide_server.control_execution(action="stop")

        # Test with loops
        session2 = await ide_server.start_debug_session(file="loops.py")
        assert session2.file.endswith("loops.py")

    @pytest.mark.asyncio
    async def test_session_lifecycle(self, ide_server: CliIdeServer):
        """Test complete session lifecycle: start -> run -> stop."""
        # Start
        session = await ide_server.start_debug_session(file="calculator.py")
        assert session.status in ["running", "stopped", "exited"]

        # Get info
        info = await ide_server.get_session_info()
        assert info is not None

        # Stop
        state = await ide_server.control_execution(action="stop")
        assert state.status in ["stopped", "exited"]

        # Verify session ended
        info_after = await ide_server.get_session_info()
        # Session might still exist briefly or be gone
        if info_after:
            assert info_after.status in ["stopped", "exited"]

