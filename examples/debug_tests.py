#!/usr/bin/env python3
"""
Example: Debug pytest with environment variables and working directory

This demonstrates debugging a test suite with:
- Module launching (python -m pytest)
- Test selection arguments
- Environment variables (DATABASE_URL, etc.)
- Custom working directory

Usage:
    python examples/debug_pytest.py
"""

import asyncio
from pathlib import Path
from otter.server import CliIdeServer


async def main():
    # Initialize Otter pointing to your project
    project_path = Path("/Users/you/project")  # Change this
    
    server = CliIdeServer(project_path=str(project_path))
    await server.start()
    
    try:
        print("🧪 Starting pytest in debug mode...")
        
        # Start debug session with pytest
        session = await server.start_debug_session(
            module="pytest",
            args=[
                "tests/test_database.py::test_user_creation",  # Specific test
                "-v",   # Verbose
                "-s",   # Don't capture output
                "-x",   # Stop on first failure
            ],
            env={
                "DATABASE_URL": "postgresql://localhost/test_db",
                "TEST_MODE": "1",
                "LOG_LEVEL": "DEBUG",
            },
            cwd=str(project_path),
            just_my_code=True,  # Don't debug into pytest itself
        )
        
        print(f"✅ Debug session started!")
        print(f"   Session ID: {session.session_id}")
        print(f"   Module: {session.module}")
        print(f"   Status: {session.status}")
        print(f"   PID: {session.pid}")
        print(f"   Test: {session.launch_args[0]}")
        
        print(f"\n💡 Typical debug workflow:")
        print(f"   1. Set breakpoint in test file")
        print(f"   2. Continue execution (test runs)")
        print(f"   3. Pauses at breakpoint")
        print(f"   4. Inspect variables")
        print(f"   5. Step through assertions")
        
        # Example: Set breakpoint in test file
        print(f"\n📍 Setting breakpoint at line 42...")
        await server.set_breakpoints(
            "tests/test_database.py",
            lines=[42],
        )
        
        # Continue execution (test will run until breakpoint)
        print(f"▶️  Continuing execution...")
        result = await server.control_execution("continue")
        
        print(f"\n⏸️  Execution status: {result.status}")
        
        if result.status == "paused":
            print(f"   Paused at: {result.stack_frames[0].file}:{result.stack_frames[0].line}")
            print(f"   Function: {result.stack_frames[0].name}")
            
            # Inspect variables
            print(f"\n🔍 Inspecting variables...")
            state = await server.inspect_state()
            print(f"   Variables: {list(state.get('variables', {}).keys())}")
            
            # Step through
            print(f"\n👟 Stepping over...")
            await server.control_execution("step_over")
            
            print(f"\n✅ Step complete! Inspect again or continue")
        
        print(f"\n👉 Press Enter to stop debugging")
        input()
        
    finally:
        await server.control_execution("stop")
        await server.stop()
        print("✅ Debug session ended")


if __name__ == "__main__":
    asyncio.run(main())

