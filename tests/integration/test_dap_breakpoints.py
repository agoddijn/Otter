"""Integration tests for DAP breakpoint functionality.

These tests verify that breakpoints actually pause execution and allow
inspection of program state.
"""

import asyncio
import pytest
from pathlib import Path

from otter.neovim.client import NeovimClient
from otter.services.debugging import DebugService
from otter.config import load_config


@pytest.fixture
async def debug_service(tmp_path):
    """Create a debug service with Neovim client."""
    # Create a simple Python script with clear breakpoint locations
    test_file = tmp_path / "test_breakpoints.py"
    test_file.write_text("""
# Line 1
x = 1
# Line 3
y = 2
# Line 5
z = x + y
# Line 7
print(f"Result: {z}")
# Line 9
print("Done")
""")
    
    # Start Neovim client
    nvim_client = NeovimClient(project_path=str(tmp_path))
    await nvim_client.start()
    
    # Create debug service
    config = load_config(tmp_path)
    service = DebugService(
        nvim_client=nvim_client,
        project_path=str(tmp_path),
        config=config,
    )
    
    yield service, test_file
    
    # Cleanup
    try:
        await service.stop_debug_session(session_id="1")
    except:
        pass
    await nvim_client.stop()


@pytest.mark.asyncio
async def test_breakpoint_pauses_execution(debug_service):
    """Test that a breakpoint actually pauses execution at the specified line.
    
    This is the CORE functionality - if this fails, the debugger is broken.
    """
    service, test_file = debug_service
    
    # Start debug session with a breakpoint at line 6 (z = x + y)
    session = await service.start_debug_session(
        file=str(test_file),
        breakpoints=[6],
        stop_on_entry=False,
    )
    
    # Verify session started
    assert session.status == "running"
    assert session.pid is not None, "Should have captured process PID"
    
    # Wait a moment for execution to hit the breakpoint
    # In reality, it should pause immediately, but give it time to settle
    await asyncio.sleep(1.0)
    
    # Check session status
    session_status = await service.get_session_status(session.session_id)
    
    # CRITICAL ASSERTIONS
    assert session_status.status == "paused", f"Should be paused at breakpoint, got: {session_status.status}"
    assert session_status.pid is not None, f"Should still have PID when paused, got: {session_status.pid}"
    
    # Get stack frames via inspect_state
    state = await service.inspect_state()
    
    assert "stack_frames" in state, "Should have stack_frames in state"
    assert len(state["stack_frames"]) > 0, f"Should have at least one stack frame, got: {len(state.get('stack_frames', []))}"
    
    # The top frame should be at a breakpoint line
    # (debugpy may adjust the breakpoint to the nearest executable line)
    top_frame = state["stack_frames"][0]
    
    # Breakpoint was set at line 7, but debugpy may have moved it
    # The important thing is that we're stopped BEFORE the final print statements
    assert top_frame.line in [5, 6, 7], f"Top frame should be near our breakpoint, got line: {top_frame.line}"


@pytest.mark.asyncio
async def test_multiple_breakpoints(debug_service):
    """Test that multiple breakpoints work and execution pauses at each one."""
    service, test_file = debug_service
    
    # Start with breakpoints at lines 4, 6, and 8
    session = await service.start_debug_session(
        file=str(test_file),
        breakpoints=[4, 6, 8],
        stop_on_entry=False,
    )
    
    assert session.status == "running"
    
    # Wait for first breakpoint (line 4)
    await asyncio.sleep(0.5)
    state1 = await service.inspect_state(session.session_id)
    
    assert state1.status == "paused", "Should pause at first breakpoint"
    assert state1.current_line == 4, f"Should be at line 4, got: {state1.current_line}"
    assert len(state1.stack_frames) > 0, "Should have stack frames"
    
    # Continue to next breakpoint (line 6)
    await service.control_execution("continue", session.session_id)
    await asyncio.sleep(0.5)
    state2 = await service.inspect_state(session.session_id)
    
    assert state2.status == "paused", "Should pause at second breakpoint"
    assert state2.current_line == 6, f"Should be at line 6, got: {state2.current_line}"
    
    # Continue to next breakpoint (line 8)
    await service.control_execution("continue", session.session_id)
    await asyncio.sleep(0.5)
    state3 = await service.inspect_state(session.session_id)
    
    assert state3.status == "paused", "Should pause at third breakpoint"
    assert state3.current_line == 8, f"Should be at line 8, got: {state3.current_line}"


@pytest.mark.asyncio
async def test_can_inspect_variables_at_breakpoint(debug_service):
    """Test that we can inspect variable values when paused at a breakpoint."""
    service, test_file = debug_service
    
    # Start with breakpoint at line 6 (after x=1 and y=2)
    session = await service.start_debug_session(
        file=str(test_file),
        breakpoints=[6],
        stop_on_entry=False,
    )
    
    # Wait for breakpoint
    await asyncio.sleep(1.0)
    
    state = await service.inspect_state(session.session_id)
    
    # Should be paused
    assert state.status == "paused"
    assert state.current_line == 6
    
    # Should be able to see variables x and y
    assert len(state.scopes) > 0, "Should have at least one scope (locals)"
    
    local_scope = next((s for s in state.scopes if s.name.lower() == "locals"), None)
    assert local_scope is not None, "Should have a 'Locals' scope"
    
    # Should be able to get variables from the scope
    variables = await service.get_variables(session.session_id, local_scope.reference)
    
    # Should find x and y
    var_names = {v.name for v in variables}
    assert "x" in var_names, f"Should have variable 'x', got: {var_names}"
    assert "y" in var_names, f"Should have variable 'y', got: {var_names}"
    
    # Check values
    x_var = next(v for v in variables if v.name == "x")
    y_var = next(v for v in variables if v.name == "y")
    
    assert x_var.value == "1", f"x should be 1, got: {x_var.value}"
    assert y_var.value == "2", f"y should be 2, got: {y_var.value}"


@pytest.mark.asyncio
async def test_stop_on_entry(debug_service):
    """Test that stop_on_entry pauses at the first line."""
    service, test_file = debug_service
    
    # Start with stop_on_entry=True
    session = await service.start_debug_session(
        file=str(test_file),
        stop_on_entry=True,
    )
    
    # Should immediately be paused at first executable line
    # Give it a moment to settle
    await asyncio.sleep(0.5)
    
    state = await service.inspect_state(session.session_id)
    
    assert state.status == "paused", "Should be paused on entry"
    assert state.current_line is not None, "Should have a current line"
    assert len(state.stack_frames) > 0, "Should have stack frames"
    
    # Should be at first line with actual code (line 2: x = 1)
    assert state.current_line in [2, 3], f"Should be at start of file, got line {state.current_line}"


@pytest.mark.asyncio
async def test_step_over(debug_service):
    """Test that step_over advances to the next line."""
    service, test_file = debug_service
    
    # Start with stop_on_entry
    session = await service.start_debug_session(
        file=str(test_file),
        stop_on_entry=True,
    )
    
    await asyncio.sleep(0.5)
    state1 = await service.inspect_state(session.session_id)
    
    line1 = state1.current_line
    assert line1 is not None, "Should have starting line"
    
    # Step over to next line
    await service.control_execution("step_over", session.session_id)
    await asyncio.sleep(0.5)
    
    state2 = await service.inspect_state(session.session_id)
    
    assert state2.status == "paused", "Should still be paused after step"
    assert state2.current_line is not None, "Should have current line after step"
    assert state2.current_line > line1, f"Should advance to next line: {line1} -> {state2.current_line}"
    assert len(state2.stack_frames) > 0, "Should still have stack frames"


@pytest.mark.asyncio
async def test_breakpoint_without_stop_on_entry(debug_service):
    """Test breakpoint with stop_on_entry=False (most common use case)."""
    service, test_file = debug_service
    
    # This is the typical workflow - start and let it run to the first breakpoint
    session = await service.start_debug_session(
        file=str(test_file),
        breakpoints=[6],
        stop_on_entry=False,  # Don't stop at entry, just at breakpoints
    )
    
    assert session.status == "running"
    assert session.pid is not None
    
    # Give it time to reach the breakpoint
    await asyncio.sleep(1.0)
    
    # Should now be paused at the breakpoint
    state = await service.inspect_state(session.session_id)
    
    # These are the critical assertions for normal debugging workflow
    assert state.status == "paused", f"Expected paused, got: {state.status}"
    assert state.current_line == 6, f"Expected line 6, got: {state.current_line}"
    assert len(state.stack_frames) > 0, f"Expected stack frames, got: {len(state.stack_frames)}"
    assert state.current_file is not None, f"Expected current file, got: {state.current_file}"


@pytest.mark.asyncio
async def test_evaluate_expression_at_breakpoint(debug_service):
    """Test that we can evaluate expressions when paused."""
    service, test_file = debug_service
    
    # Start with breakpoint at line 6 (after x=1, y=2, z=x+y)
    session = await service.start_debug_session(
        file=str(test_file),
        breakpoints=[6],
        stop_on_entry=False,
    )
    
    await asyncio.sleep(1.0)
    
    state = await service.inspect_state(session.session_id)
    assert state.status == "paused"
    
    # Evaluate expression
    result = await service.evaluate_expression(
        session.session_id,
        expression="x + y",
        frame_id=state.stack_frames[0].id if state.stack_frames else None,
    )
    
    assert result.success, f"Evaluation should succeed: {result.error}"
    assert result.result == "3", f"x + y should equal 3, got: {result.result}"

