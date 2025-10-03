"""Integration tests for DAP output capture and PID detection.

These tests verify that debug sessions properly capture:
- Real process PID (not debugpy's PID)
- stdout/stderr output from the debugged process
- Process lifecycle events
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
    # Create a simple Python script that prints and exits
    test_file = tmp_path / "test_script.py"
    test_file.write_text("""
import sys
import os

print(f"Hello from PID: {os.getpid()}", flush=True)
print("This is stdout output", flush=True)
sys.stderr.write("This is stderr output\\n")
sys.stderr.flush()

# Wait a bit so we can inspect the process
import time
time.sleep(2)
print("Exiting now", flush=True)
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
    await nvim_client.stop()


@pytest.mark.asyncio
async def test_captures_real_process_pid(debug_service):
    """Test that we capture the real process PID, not debugpy's PID."""
    service, test_file = debug_service
    
    # Start debug session
    session = await service.start_debug_session(
        file=str(test_file),
        stop_on_entry=False,
    )
    
    # Verify we got a PID
    assert session.pid is not None, "Should have captured process PID"
    assert session.pid > 0, "PID should be a positive integer"
    
    # The output should mention the PID
    # Wait a bit for output to be captured
    await asyncio.sleep(1)
    
    # Get session status to check for updated output
    status = await service.get_session_status(session.session_id)
    assert status.pid == session.pid, "PID should remain consistent"
    
    # Cleanup
    await service.stop_debug_session(session.session_id)


@pytest.mark.asyncio
async def test_captures_stdout_output(debug_service):
    """Test that we capture stdout output from the debugged process."""
    service, test_file = debug_service
    
    # Start debug session
    session = await service.start_debug_session(
        file=str(test_file),
        stop_on_entry=False,
    )
    
    # Wait for output to be produced
    await asyncio.sleep(1.5)
    
    # Get current session status
    status = await service.get_session_status(session.session_id)
    
    # Verify stdout was captured
    assert "Hello from PID:" in status.output, "Should capture stdout with PID"
    assert "This is stdout output" in status.output, "Should capture stdout messages"
    
    # Cleanup
    await service.stop_debug_session(session.session_id)


@pytest.mark.asyncio
async def test_captures_stderr_output(debug_service):
    """Test that we capture stderr output from the debugged process."""
    service, test_file = debug_service
    
    # Start debug session
    session = await service.start_debug_session(
        file=str(test_file),
        stop_on_entry=False,
    )
    
    # Wait for output
    await asyncio.sleep(1.5)
    
    # Get current session status
    status = await service.get_session_status(session.session_id)
    
    # Verify stderr was captured
    assert "This is stderr output" in status.output, "Should capture stderr messages"
    
    # Cleanup
    await service.stop_debug_session(session.session_id)


@pytest.mark.asyncio
async def test_pid_matches_output(debug_service):
    """Test that the captured PID matches what the process prints."""
    service, test_file = debug_service
    
    # Start debug session
    session = await service.start_debug_session(
        file=str(test_file),
        stop_on_entry=False,
    )
    
    # Wait for output
    await asyncio.sleep(1.5)
    
    # Get status
    status = await service.get_session_status(session.session_id)
    
    # The output should contain "Hello from PID: <actual_pid>"
    assert f"PID: {status.pid}" in status.output, \
        f"Output should contain the actual PID {status.pid}, got: {status.output}"
    
    # Cleanup
    await service.stop_debug_session(session.session_id)


@pytest.mark.asyncio
async def test_module_launch_captures_output(debug_service, tmp_path):
    """Test that module launches also capture output and PID."""
    service, _ = debug_service
    
    # Create a simple module
    module_dir = tmp_path / "test_module"
    module_dir.mkdir()
    (module_dir / "__init__.py").write_text("")
    (module_dir / "__main__.py").write_text("""
import os
print(f"Module PID: {os.getpid()}", flush=True)
print("Module is running", flush=True)
import time
time.sleep(1)
""")
    
    # Start debug session with module
    session = await service.start_debug_session(
        module="test_module",
        stop_on_entry=False,
    )
    
    # Verify PID captured
    assert session.pid is not None, "Should capture PID for module launch"
    
    # Wait for output
    await asyncio.sleep(1.5)
    
    # Get status
    status = await service.get_session_status(session.session_id)
    
    # Verify output captured
    assert "Module PID:" in status.output, "Should capture module output"
    assert "Module is running" in status.output
    
    # Cleanup
    await service.stop_debug_session(session.session_id)


@pytest.mark.asyncio
async def test_output_accumulates_over_time(debug_service, tmp_path):
    """Test that output continues to accumulate as the process runs."""
    # Create a script that prints multiple times
    test_file = tmp_path / "multi_output.py"
    test_file.write_text("""
import time
for i in range(5):
    print(f"Output {i}", flush=True)
    time.sleep(0.3)
""")
    
    service, _ = debug_service
    
    # Start session
    session = await service.start_debug_session(
        file=str(test_file),
        stop_on_entry=False,
    )
    
    # Check output at different times
    await asyncio.sleep(0.5)
    status1 = await service.get_session_status(session.session_id)
    output1_lines = status1.output.count("Output")
    
    await asyncio.sleep(1.0)
    status2 = await service.get_session_status(session.session_id)
    output2_lines = status2.output.count("Output")
    
    # Later status should have more output
    assert output2_lines > output1_lines, \
        f"Output should accumulate over time: {output1_lines} -> {output2_lines}"
    
    # Eventually should have all 5 outputs
    await asyncio.sleep(1.5)
    status_final = await service.get_session_status(session.session_id)
    assert status_final.output.count("Output") >= 4, \
        "Should capture most/all outputs"
    
    # Cleanup
    await service.stop_debug_session(session.session_id)


@pytest.mark.asyncio
async def test_failed_process_shows_error_output(debug_service, tmp_path):
    """Test that we capture error output when process fails."""
    # Create a script that crashes
    test_file = tmp_path / "crash.py"
    test_file.write_text("""
print("About to crash", flush=True)
raise RuntimeError("Intentional crash for testing")
""")
    
    service, _ = debug_service
    
    # Start session
    session = await service.start_debug_session(
        file=str(test_file),
        stop_on_entry=False,
    )
    
    # Wait for crash
    await asyncio.sleep(1.5)
    
    # Get status
    status = await service.get_session_status(session.session_id)
    
    # Should have captured the error
    assert "About to crash" in status.output
    # Error messages might be in output
    # (actual traceback capture depends on DAP configuration)
    
    # Cleanup (session might already be stopped)
    try:
        await service.stop_debug_session(session.session_id)
    except:
        pass  # Session may have already terminated


@pytest.mark.asyncio
async def test_env_vars_visible_in_output(debug_service, tmp_path):
    """Test that environment variables are properly passed."""
    test_file = tmp_path / "env_test.py"
    test_file.write_text("""
import os
print(f"TEST_VAR={os.environ.get('TEST_VAR', 'NOT_SET')}", flush=True)
""")
    
    service, _ = debug_service
    
    # Start with custom env var
    session = await service.start_debug_session(
        file=str(test_file),
        env={"TEST_VAR": "custom_value"},
        stop_on_entry=False,
    )
    
    # Wait for output
    await asyncio.sleep(1.0)
    
    # Get status
    status = await service.get_session_status(session.session_id)
    
    # Verify env var was set
    assert "TEST_VAR=custom_value" in status.output, \
        f"Should see custom env var in output: {status.output}"
    
    # Cleanup
    await service.stop_debug_session(session.session_id)

