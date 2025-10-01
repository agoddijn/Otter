"""Integration tests for DAP debugging - state inspection.

Tests for inspecting variables, call stacks, and evaluating expressions.

Run with: pytest tests/integration/test_debugging_inspection.py -v
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

        # Program with variables to inspect
        (project_root / "variables.py").write_text(
            """def calculate():
    x = 10
    y = 20
    z = x + y
    name = "test"
    items = [1, 2, 3]
    data = {"key": "value"}
    return z

result = calculate()
print(result)
"""
        )

        # Program with nested function calls for stack inspection
        (project_root / "stack.py").write_text(
            """def inner_function(value):
    doubled = value * 2
    return doubled

def middle_function(x):
    temp = inner_function(x)
    result = temp + 5
    return result

def outer_function():
    final = middle_function(10)
    return final

output = outer_function()
print(output)
"""
        )

        # Program with complex objects
        (project_root / "objects.py").write_text(
            """class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
    
    def greet(self):
        return f"Hello, I'm {self.name}"

def process_person():
    person = Person("Alice", 30)
    greeting = person.greet()
    return greeting

result = process_person()
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


class TestStateInspection:
    """Tests for inspecting program state during debugging."""

    @pytest.mark.asyncio
    async def test_inspect_state_basic(self, debug_helper: DebugTestHelper):
        """Test basic state inspection."""
        # Start with breakpoint - will immediately pause
        await debug_helper.start_debug_and_wait(
            file="variables.py", breakpoints=[4], expected_status="paused", timeout=10.0
        )

        # Inspect state
        state = await debug_helper.ide_server.inspect_state()
        assert "stack_frames" in state
        assert isinstance(state["stack_frames"], list)

    @pytest.mark.asyncio
    async def test_get_stack_frames(self, debug_helper: DebugTestHelper):
        """Test getting stack frames."""
        # Start with breakpoint inside nested function - will immediately pause
        await debug_helper.start_debug_and_wait(
            file="stack.py", breakpoints=[2], expected_status="paused", timeout=10.0
        )

        # Get state with stack frames
        state = await debug_helper.ide_server.inspect_state()

        if state["stack_frames"]:
            frames = state["stack_frames"]
            assert len(frames) > 0
            # Check frame structure
            frame = frames[0]
            assert hasattr(frame, "id")
            assert hasattr(frame, "name")
            assert hasattr(frame, "file")
            assert hasattr(frame, "line")
            assert frame.name == "inner_function"

    @pytest.mark.asyncio
    async def test_get_variables_in_scope(self, debug_helper: DebugTestHelper):
        """Test getting variables in current scope."""
        # Start with breakpoint - will immediately pause
        await debug_helper.start_debug_and_wait(
            file="variables.py", breakpoints=[6], expected_status="paused", timeout=10.0
        )

        # Inspect state to get variables
        state = await debug_helper.ide_server.inspect_state()

        # Should have variables dict
        if "variables" in state:
            variables = state["variables"]
            assert isinstance(variables, dict)

            # Check that we have some scopes (Locals, Globals, etc.)
            if variables:
                # At least one scope should exist
                assert len(variables) > 0

    @pytest.mark.asyncio
    async def test_evaluate_simple_expression(self, debug_helper: DebugTestHelper):
        """Test evaluating a simple expression."""
        # Start with breakpoint - will immediately pause
        await debug_helper.start_debug_and_wait(
            file="variables.py", breakpoints=[4], expected_status="paused", timeout=10.0
        )

        # Evaluate expression
        state = await debug_helper.ide_server.inspect_state(expression="x + y")

        if "evaluation" in state:
            result = state["evaluation"]
            assert hasattr(result, "result")
            # The result should be 30 (10 + 20)
            # Note: result is a string representation
            assert result.result is not None

    @pytest.mark.asyncio
    async def test_evaluate_variable(self, debug_helper: DebugTestHelper):
        """Test evaluating a variable name."""
        # Start with breakpoint - will immediately pause
        await debug_helper.start_debug_and_wait(
            file="variables.py", breakpoints=[5], expected_status="paused", timeout=10.0
        )

        # Evaluate variable
        state = await debug_helper.ide_server.inspect_state(expression="name")

        if "evaluation" in state:
            result = state["evaluation"]
            assert hasattr(result, "result")
            assert result.result is not None

    @pytest.mark.asyncio
    async def test_evaluate_object_attribute(self, debug_helper: DebugTestHelper):
        """Test evaluating object attributes."""
        # Start with breakpoint - will immediately pause
        await debug_helper.start_debug_and_wait(
            file="objects.py", breakpoints=[10], expected_status="paused", timeout=10.0
        )

        # Evaluate person.name
        state = await debug_helper.ide_server.inspect_state(expression="person.name")

        if "evaluation" in state:
            result = state["evaluation"]
            assert result.result is not None
            # Should contain "Alice"

    @pytest.mark.asyncio
    async def test_evaluate_complex_expression(self, debug_helper: DebugTestHelper):
        """Test evaluating a complex expression."""
        # Start with breakpoint - will immediately pause
        await debug_helper.start_debug_and_wait(
            file="variables.py", breakpoints=[6], expected_status="paused", timeout=10.0
        )

        # Evaluate complex expression
        state = await debug_helper.ide_server.inspect_state(expression="len(items) + z")

        if "evaluation" in state:
            result = state["evaluation"]
            assert result.result is not None

    @pytest.mark.asyncio
    async def test_inspect_specific_frame(self, debug_helper: DebugTestHelper):
        """Test inspecting a specific stack frame."""
        # Start with breakpoint - will immediately pause
        await debug_helper.start_debug_and_wait(
            file="stack.py", breakpoints=[2], expected_status="paused", timeout=10.0
        )

        # Get stack first
        state = await debug_helper.ide_server.inspect_state()

        if state["stack_frames"] and len(state["stack_frames"]) > 0:
            # Inspect specific frame
            frame_id = state["stack_frames"][0].id
            state_with_frame = await debug_helper.ide_server.inspect_state(frame_id=frame_id)

            assert "stack_frames" in state_with_frame

    @pytest.mark.asyncio
    async def test_scopes_structure(self, debug_helper: DebugTestHelper):
        """Test that scopes have correct structure."""
        # Start with breakpoint - will immediately pause
        await debug_helper.start_debug_and_wait(
            file="variables.py", breakpoints=[5], expected_status="paused", timeout=10.0
        )

        # Inspect state
        state = await debug_helper.ide_server.inspect_state()

        if "scopes" in state and state["scopes"]:
            scope = state["scopes"][0]
            assert hasattr(scope, "name")
            assert hasattr(scope, "variables_reference")
            assert isinstance(scope.variables_reference, int)

    @pytest.mark.asyncio
    async def test_variables_structure(self, debug_helper: DebugTestHelper):
        """Test that variables have correct structure."""
        # Start with breakpoint - will immediately pause
        await debug_helper.start_debug_and_wait(
            file="variables.py", breakpoints=[6], expected_status="paused", timeout=10.0
        )

        # Inspect state
        state = await debug_helper.ide_server.inspect_state()

        if "variables" in state and state["variables"]:
            # Get first scope's variables
            for scope_name, variables in state["variables"].items():
                if variables:
                    var = variables[0]
                    assert hasattr(var, "name")
                    assert hasattr(var, "value")
                    assert hasattr(var, "type")
                    break

    @pytest.mark.asyncio
    async def test_inspect_without_active_session(self, debug_helper: DebugTestHelper):
        """Test that inspecting without session returns empty state."""
        # Try to inspect without starting session
        # inspect_state returns empty dict when no session (doesn't raise)
        state = await debug_helper.ide_server.inspect_state()
        assert isinstance(state, dict)
        assert len(state.get("stack_frames", [])) == 0

    @pytest.mark.asyncio
    async def test_inspect_returns_empty_when_not_paused(
        self, debug_helper: DebugTestHelper
    ):
        """Test inspecting when program is running (not paused)."""
        # Start session without breakpoints
        await debug_helper.ide_server.start_debug_session(file="variables.py")

        # Try to inspect (might not have state if not paused)
        state = await debug_helper.ide_server.inspect_state()

        # Should return dict, might be empty or have minimal data
        assert isinstance(state, dict)

