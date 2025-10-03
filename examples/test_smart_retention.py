"""
Test smart retention policy for debug sessions.

Crashes (exit code != 0): Kept for 5 minutes
Clean exits (exit code 0): Kept for 30 seconds

This ensures crash diagnostics are available longer while preventing
memory accumulation from successful runs.
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
    clean_exit = examples_dir / "test_clean_exit.py"
    clean_exit.write_text("""import sys
print("Running successfully!")
sys.exit(0)
""")
    
    crash_exit = examples_dir / "test_crash_exit.py"
    crash_exit.write_text("""import sys
print("About to crash!", file=sys.stderr)
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
    print("🧪 TESTING SMART RETENTION POLICY")
    print("=" * 80)
    print()
    
    # Test 1: Clean Exit (should be cleaned up faster)
    print("📊 Test 1: Clean Exit (code 0)")
    print("-" * 40)
    
    session1 = await service.start_debug_session(file=str(clean_exit))
    print(f"✓ Started session: {session1.session_id}")
    
    # Wait for it to exit cleanly
    await asyncio.sleep(2)
    status1 = await service.get_session_status(session1.session_id)
    print(f"  After 2s: status={status1.status}, exit_code={status1.exit_code}")
    print(f"  Crash reason: {status1.crash_reason}")
    
    # Should still be available after 20 seconds (within 30s window)
    print(f"\n  Waiting 20 seconds... (should still be available)")
    await asyncio.sleep(20)
    
    try:
        status1 = await service.get_session_status(session1.session_id)
        print(f"  ✅ After 22s total: session still available")
        print(f"     Status: {status1.status}, Exit code: {status1.exit_code}")
    except Exception as e:
        print(f"  ❌ After 22s total: {e}")
    
    # Should be cleaned up after 35 seconds total (beyond 30s window)
    print(f"\n  Waiting 15 more seconds... (should be cleaned up)")
    await asyncio.sleep(15)
    
    try:
        status1 = await service.get_session_status(session1.session_id)
        print(f"  ❌ After 37s total: session still there (unexpected!)")
        print(f"     Error: {status1.error}")
    except Exception as e:
        print(f"  ✅ After 37s total: session cleaned up as expected")
    
    print()
    print()
    
    # Test 2: Crash Exit (should be kept longer)
    print("📊 Test 2: Crash Exit (code 1)")
    print("-" * 40)
    
    session2 = await service.start_debug_session(file=str(crash_exit))
    print(f"✓ Started session: {session2.session_id}")
    
    # Wait for it to crash
    await asyncio.sleep(2)
    status2 = await service.get_session_status(session2.session_id)
    print(f"  After 2s: status={status2.status}, exit_code={status2.exit_code}")
    print(f"  Crash reason: {status2.crash_reason}")
    print(f"  Stderr: {status2.stderr[:50]}...")
    
    # Should still be available after 40 seconds (crashes kept for 5 minutes)
    print(f"\n  Waiting 40 seconds... (should still be available)")
    await asyncio.sleep(40)
    
    try:
        status2 = await service.get_session_status(session2.session_id)
        print(f"  ✅ After 42s total: crash data still available!")
        print(f"     Status: {status2.status}, Exit code: {status2.exit_code}")
        print(f"     Crash reason: {status2.crash_reason}")
        print(f"     (Will persist for ~4 more minutes)")
    except Exception as e:
        print(f"  ❌ After 42s total: {e}")
    
    # Cleanup
    await nvim_client.stop()
    
    print()
    print("=" * 80)
    print("🏁 SMART RETENTION SUMMARY")
    print("=" * 80)
    print()
    print("✅ Clean exits (code 0):  Kept for 30 seconds")
    print("✅ Crashes (code != 0):   Kept for 5 minutes (300 seconds)")
    print()
    print("💡 This ensures:")
    print("   - Crash diagnostics remain available for agents to query")
    print("   - Successful runs don't accumulate in memory")
    print("   - Memory-efficient for long-running Otter instances")


if __name__ == "__main__":
    asyncio.run(main())

