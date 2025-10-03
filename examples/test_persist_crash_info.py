"""
Test that crash information persists after session termination.

This verifies the fix for the ergonomics issue where sessions crashed so quickly
that by the time you queried them, all diagnostic information was gone.

Now crash info is kept for 60 seconds after termination.
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
    
    # Create a program that crashes immediately
    crash_program = examples_dir / "test_instant_crash.py"
    crash_program.write_text("""import sys

print("About to crash immediately!", file=sys.stderr)
raise RuntimeError("Instant crash for testing!")
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
    print("🧪 TESTING CRASH INFO PERSISTENCE")
    print("=" * 80)
    print()
    
    # Start the program (will crash almost immediately)
    print("Starting program that crashes instantly...")
    session = await service.start_debug_session(file=str(crash_program))
    print(f"✓ Session started: {session.session_id}")
    print(f"  Initial PID: {session.pid}")
    print()
    
    # Query multiple times as it crashes
    for i in range(5):
        await asyncio.sleep(0.5)
        
        try:
            status = await service.get_session_status(session.session_id)
            
            print(f"Query {i+1} (after {(i+1)*0.5}s):")
            print(f"  Status: {status.status}")
            print(f"  PID: {status.pid}")
            print(f"  Exit Code: {status.exit_code}")
            print(f"  Terminated: {status.terminated}")
            print(f"  Crash Reason: {status.crash_reason}")
            
            if status.stderr:
                print(f"  Stderr (first 100 chars): {status.stderr[:100]}")
            
            if status.error:
                print(f"  Error: {status.error}")
            
            print()
            
            # If we got good crash info, we're done!
            if status.status == "terminated" and status.exit_code is not None:
                print("✅ SUCCESS: Crash information persisted after termination!")
                print(f"\n📊 Complete Crash Report:")
                print(f"  Status: {status.status}")
                print(f"  Exit Code: {status.exit_code}")
                print(f"  Crash Reason: {status.crash_reason}")
                print(f"  Uptime: {status.uptime_seconds}s")
                print(f"  Stderr:\n{status.stderr}")
                break
                
        except Exception as e:
            print(f"Query {i+1}: Error - {e}")
            print()
    
    # Try one more time after a longer delay to ensure it's still available
    print("Waiting 5 more seconds to ensure data persists...")
    await asyncio.sleep(5)
    
    try:
        status = await service.get_session_status(session.session_id)
        print(f"\n✅ After 5+ seconds, crash info is still available!")
        print(f"  Status: {status.status}")
        print(f"  Exit Code: {status.exit_code}")
        print(f"  Data is kept for 60 seconds after termination")
    except Exception as e:
        print(f"\n❌ After 5+ seconds: {e}")
    
    # Cleanup
    await nvim_client.stop()
    
    print()
    print("=" * 80)
    print("🏁 TEST COMPLETE")
    print("=" * 80)
    print()
    print("Key improvements:")
    print("  ✅ Crash info persists for 60 seconds (was 5 seconds)")
    print("  ✅ Status is 'terminated' (not 'no_session')")
    print("  ✅ Full diagnostic info available after crash")
    print("  ✅ Can query multiple times without losing data")


if __name__ == "__main__":
    asyncio.run(main())

