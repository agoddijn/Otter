"""
Test the generalized get_debug_session_info() MCP tool.

This demonstrates how agents can query session information flexibly:
1. Get current session: get_debug_session_info()
2. Query specific session: get_debug_session_info(session_id="...")
3. Query terminated sessions (persist for 5 minutes on crashes!)
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
    crash_program = examples_dir / "test_crash_for_query.py"
    crash_program.write_text("""import sys
print("Starting program...")
print("About to crash!", file=sys.stderr)
sys.exit(1)
""")
    
    success_program = examples_dir / "test_success_for_query.py"
    success_program.write_text("""import sys
print("Success!")
sys.exit(0)
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
    print("🧪 TESTING GENERALIZED get_debug_session_info()")
    print("=" * 80)
    print()
    
    # Use Case 1: Start session and query by ID
    print("📊 Use Case 1: Query Specific Session by ID")
    print("-" * 40)
    
    session1 = await service.start_debug_session(file=str(crash_program))
    session_id = session1.session_id
    print(f"✓ Started session: {session_id}")
    print()
    
    # Wait for crash
    await asyncio.sleep(2)
    
    # Query by session ID (even though it's terminated!)
    info = await service.get_session_info(session_id=session_id)
    print(f"✅ Queried by session ID: {session_id[:8]}...")
    print(f"   Status: {info.status}")
    print(f"   Exit Code: {info.exit_code}")
    print(f"   Crash Reason: {info.crash_reason}")
    print(f"   Stderr: {info.stderr[:50]}...")
    print(f"   📝 Data persists for 5 minutes (crash)")
    print()
    print()
    
    # Use Case 2: Query "current" session
    print("📊 Use Case 2: Query Current Active Session")
    print("-" * 40)
    
    session2 = await service.start_debug_session(
        file=str(success_program),
        stop_on_entry=True  # Keep it paused
    )
    print(f"✓ Started session: {session2.session_id}")
    
    # Wait for it to start
    await asyncio.sleep(1)
    
    # Query without session_id (gets current active session)
    current_info = await service.get_session_info()
    if current_info and current_info.session_id:
        print(f"✅ Queried current session (no ID needed)")
        print(f"   Status: {current_info.status}")
        print(f"   PID: {current_info.pid}")
        print(f"   Session ID: {current_info.session_id[:8]}...")
    else:
        print(f"❌ No current session found")
    print()
    print()
    
    # Use Case 3: Query old session while new one is active
    print("📊 Use Case 3: Query Old Session While New One Active")
    print("-" * 40)
    
    # Can still query the first (crashed) session!
    old_info = await service.get_session_info(session_id=session_id)
    if old_info:
        print(f"✅ Old crashed session still available:")
        print(f"   Session ID: {old_info.session_id[:8]}...")
        print(f"   Status: {old_info.status}")
        print(f"   Exit Code: {old_info.exit_code}")
        print(f"   Uptime: {old_info.uptime_seconds}s")
        print()
    
    if current_info and current_info.session_id:
        print(f"✅ Current running session:")
        print(f"   Session ID: {current_info.session_id[:8]}...")
        print(f"   Status: {current_info.status}")
        print(f"   PID: {current_info.pid}")
    else:
        print(f"⚠️  Current session info not available (try querying by ID)")
    print()
    print()
    
    # Cleanup
    await nvim_client.stop()
    
    print("=" * 80)
    print("🏁 MCP TOOL USAGE SUMMARY")
    print("=" * 80)
    print()
    print("✅ ONE generalized tool instead of many specific ones:")
    print()
    print("   # Get current active session")
    print('   get_debug_session_info()')
    print()
    print("   # Query specific session (active or terminated)")
    print('   get_debug_session_info(session_id="uuid-1234...")')
    print()
    print("💡 Benefits:")
    print("   • Can query terminated sessions (5min for crashes!)")
    print("   • Single tool handles all use cases")
    print("   • Clear, self-documenting API")
    print("   • Works for agent workflows (crash diagnosis)")


if __name__ == "__main__":
    asyncio.run(main())

