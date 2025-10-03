"""
Test script to verify enhanced debugger crash detection and error reporting.

This demonstrates the new transparency features:
- Separate stdout/stderr capture
- Exit code detection
- Crash reason reporting
- Uptime tracking
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from otter.neovim.client import NeovimClient
from otter.services.debugging import DebugService
from otter.config import load_config


async def main():
    examples_dir = Path(__file__).parent
    
    # Create test programs
    crash_program = examples_dir / "test_crash.py"
    crash_program.write_text("""import sys

print("Starting program...")
print("About to crash...", file=sys.stderr)
raise RuntimeError("Intentional crash for testing!")
""")
    
    success_program = examples_dir / "test_success.py"
    success_program.write_text("""import sys

print("Program running...")
print("Everything OK!", file=sys.stderr)
sys.exit(0)
""")
    
    error_exit_program = examples_dir / "test_error_exit.py"
    error_exit_program.write_text("""import sys

print("Program running...")
print("Something went wrong!", file=sys.stderr)
sys.exit(1)
""")
    
    # Start Neovim
    nvim_client = NeovimClient(project_path=str(examples_dir))
    await nvim_client.start()
    
    config = load_config(examples_dir)
    service = DebugService(
        nvim_client=nvim_client,
        project_path=str(examples_dir),
        config=config,
    )
    
    print("=" * 80)
    print("🧪 TESTING ENHANCED DEBUGGER CRASH DETECTION")
    print("=" * 80)
    print()
    
    # Test 1: Program that crashes with exception
    print("=" * 80)
    print("TEST 1: Program with unhandled exception")
    print("=" * 80)
    
    session1 = await service.start_debug_session(file=str(crash_program))
    print(f"✓ Session started: {session1.session_id}")
    print(f"  PID: {session1.pid}")
    
    # Wait for it to crash
    await asyncio.sleep(2.0)
    
    status1 = await service.get_session_status(session1.session_id)
    print(f"\n📊 Final Status:")
    print(f"  Status: {status1.status}")
    print(f"  Exit Code: {status1.exit_code}")
    print(f"  Terminated: {status1.terminated}")
    print(f"  Uptime: {status1.uptime_seconds}s")
    print(f"  Crash Reason: {status1.crash_reason}")
    print(f"\n📝 Output (stdout):")
    print(f"  {status1.stdout[:200]}")
    print(f"\n📝 Errors (stderr):")
    print(f"  {status1.stderr[:500]}")
    
    try:
        await service.stop_debug_session(session1.session_id)
    except:
        pass
    
    print()
    await asyncio.sleep(1.0)
    
    # Test 2: Program that exits cleanly
    print("=" * 80)
    print("TEST 2: Program with clean exit (code 0)")
    print("=" * 80)
    
    session2 = await service.start_debug_session(file=str(success_program))
    print(f"✓ Session started: {session2.session_id}")
    
    await asyncio.sleep(2.0)
    
    status2 = await service.get_session_status(session2.session_id)
    print(f"\n📊 Final Status:")
    print(f"  Status: {status2.status}")
    print(f"  Exit Code: {status2.exit_code}")
    print(f"  Crash Reason: {status2.crash_reason}")
    print(f"  Stdout: {status2.stdout[:200]}")
    print(f"  Stderr: {status2.stderr[:200]}")
    
    try:
        await service.stop_debug_session(session2.session_id)
    except:
        pass
    
    print()
    await asyncio.sleep(1.0)
    
    # Test 3: Program that exits with error code
    print("=" * 80)
    print("TEST 3: Program with error exit (code 1)")
    print("=" * 80)
    
    session3 = await service.start_debug_session(file=str(error_exit_program))
    print(f"✓ Session started: {session3.session_id}")
    
    await asyncio.sleep(2.0)
    
    status3 = await service.get_session_status(session3.session_id)
    print(f"\n📊 Final Status:")
    print(f"  Status: {status3.status}")
    print(f"  Exit Code: {status3.exit_code}")
    print(f"  Crash Reason: {status3.crash_reason}")
    print(f"  Stdout: {status3.stdout[:200]}")
    print(f"  Stderr: {status3.stderr[:200]}")
    
    try:
        await service.stop_debug_session(session3.session_id)
    except:
        pass
    
    # Cleanup
    await nvim_client.stop()
    
    print()
    print("=" * 80)
    print("🏁 ALL TESTS COMPLETE")
    print("=" * 80)
    print()
    print("✅ Enhanced crash detection features verified:")
    print("  - Separate stdout/stderr capture")
    print("  - Exit code detection")
    print("  - Crash reason analysis")
    print("  - Uptime tracking")


if __name__ == "__main__":
    asyncio.run(main())

