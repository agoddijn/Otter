"""
Minimal reproducible example for DAP breakpoint debugging.

This script tests breakpoint functionality with a real file (not temp),
outside of the pytest framework, to isolate the issue.

Usage:
    python examples/minimal_debug_test.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from otter.neovim.client import NeovimClient
from otter.services.debugging import DebugService
from otter.config import load_config


async def main():
    # Create a simple test file in examples/
    test_file = Path(__file__).parent / "test_simple.py"
    test_file.write_text("""# Simple test program
print("Starting")
x = 1
print(f"x = {x}")
y = 2
print(f"y = {y}")
z = x + y
print(f"z = {z}")
print("Done")
""")
    
    print("=" * 80)
    print("🔍 MINIMAL DAP BREAKPOINT TEST")
    print("=" * 80)
    print(f"\nTest file: {test_file}")
    print(f"Test file exists: {test_file.exists()}")
    print(f"Test file size: {test_file.stat().st_size} bytes")
    print()
    
    # Start Neovim client
    print("Starting Neovim client...")
    nvim_client = NeovimClient(project_path=str(test_file.parent))
    await nvim_client.start()
    print("✅ Neovim client started")
    print()
    
    # Create debug service
    config = load_config(test_file.parent)
    service = DebugService(
        nvim_client=nvim_client,
        project_path=str(test_file.parent),
        config=config,
    )
    print("✅ Debug service created")
    print()
    
    try:
        # Test 1: Stop on entry (simplest case)
        print("=" * 80)
        print("TEST 1: Stop on Entry (no breakpoints)")
        print("=" * 80)
        
        session1 = await service.start_debug_session(
            file=str(test_file),
            stop_on_entry=True,
        )
        
        print(f"Session ID: {session1.session_id}")
        print(f"Status: {session1.status}")
        print(f"PID: {session1.pid}")
        print()
        
        # Wait a moment for it to settle
        await asyncio.sleep(0.5)
        
        # Check if we're actually stopped
        session_info = await service.get_session_status(session1.session_id)
        print(f"Current status: {session_info.status}")
        print(f"Current PID: {session_info.pid}")
        print()
        
        # Try to get stack frames
        state1 = await service.inspect_state()
        print(f"Stack frames: {len(state1.get('stack_frames', []))}")
        if state1.get('stack_frames'):
            for i, frame in enumerate(state1['stack_frames']):
                print(f"  Frame {i}: {frame.name} at {frame.file}:{frame.line}")
        else:
            print("  ❌ NO STACK FRAMES!")
        print()
        
        # Stop the session
        await service.stop_debug_session(session1.session_id)
        print("✅ Test 1 complete")
        print()
        
        # Wait a bit between tests
        await asyncio.sleep(1.0)
        
        # Test 2: Breakpoint at line 7 (z = x + y)
        print("=" * 80)
        print("TEST 2: Breakpoint at line 7")
        print("=" * 80)
        
        session2 = await service.start_debug_session(
            file=str(test_file),
            breakpoints=[7],
            stop_on_entry=False,
        )
        
        print(f"Session ID: {session2.session_id}")
        print(f"Status: {session2.status}")
        print(f"PID: {session2.pid}")
        print(f"Breakpoints: {session2.breakpoints}")
        print()
        
        # Wait for it to hit the breakpoint
        print("Waiting for breakpoint to be hit...")
        await asyncio.sleep(2.0)
        
        # Check status
        session_info2 = await service.get_session_status(session2.session_id)
        print(f"Current status: {session_info2.status}")
        print(f"Current PID: {session_info2.pid}")
        print(f"Output: {session_info2.output[:200] if session_info2.output else 'None'}")
        print()
        
        # Try to get stack frames
        state2 = await service.inspect_state()
        print(f"Stack frames: {len(state2.get('stack_frames', []))}")
        if state2.get('stack_frames'):
            for i, frame in enumerate(state2['stack_frames']):
                print(f"  Frame {i}: {frame.name} at {frame.file}:{frame.line}")
            print("  ✅ BREAKPOINT HIT!")
        else:
            print("  ❌ NO STACK FRAMES - breakpoint not hit")
        print()
        
        # Stop the session
        try:
            await service.stop_debug_session(session2.session_id)
        except:
            pass
        print("✅ Test 2 complete")
        print()
        
    finally:
        # Cleanup
        print("Cleaning up...")
        await nvim_client.stop()
        print("✅ Neovim client stopped")
    
    print()
    print("=" * 80)
    print("🏁 TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

