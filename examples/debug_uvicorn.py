#!/usr/bin/env python3
"""
Example: Debug a Uvicorn server with environment variables

This demonstrates the enhanced debug tools with:
- Module launching (python -m uvicorn)
- Environment variables (DOPPLER_ENV)
- Custom arguments (host, port, reload)

Usage:
    python examples/debug_uvicorn.py
"""

import asyncio
from pathlib import Path
from otter.server import CliIdeServer


async def main():
    # Initialize Otter pointing to your project
    project_path = Path("/Users/you/fern-mono")  # Change this
    
    server = CliIdeServer(project_path=str(project_path))
    await server.start()
    
    try:
        print("🚀 Starting Uvicorn server in debug mode...")
        
        # Start debug session with module launching
        session = await server.start_debug_session(
            module="uvicorn",
            args=[
                "fern_mono.main:app",  # Your app module
                "--host", "127.0.0.1",
                "--port", "8000",
                "--reload"  # Hot reload on file changes
            ],
            env={
                "DOPPLER_ENV": "1",  # Enable Doppler environment
                "DEBUG": "true",      # Enable debug mode
            },
            cwd=str(project_path)
        )
        
        print(f"✅ Debug session started!")
        print(f"   Session ID: {session.session_id}")
        print(f"   Module: {session.module}")
        print(f"   Status: {session.status}")
        print(f"   PID: {session.pid}")
        print(f"   Working Dir: {session.launch_cwd}")
        print(f"   Arguments: {session.launch_args}")
        print(f"   Environment: {list(session.launch_env.keys() if session.launch_env else [])}")
        print(f"\n🌐 Server should be running at http://127.0.0.1:8000")
        print(f"\n📍 Set breakpoints in your code with:")
        print(f"   await server.set_breakpoints('fern_mono/api/routes.py', [45, 67])")
        print(f"\n⏸️  Control execution with:")
        print(f"   await server.control_execution('continue')")
        print(f"   await server.control_execution('step_over')")
        print(f"\n🔍 Inspect state with:")
        print(f"   await server.inspect_state()")
        
        # Keep running until interrupted
        print(f"\n👉 Press Ctrl+C to stop debugging\n")
        
        # In a real scenario, you'd now:
        # 1. Set breakpoints in your API routes
        # 2. Make HTTP requests to trigger them
        # 3. Inspect variables when paused
        # 4. Step through code
        
        # Wait for user interrupt
        await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping debug session...")
        await server.control_execution("stop")
    
    finally:
        await server.stop()
        print("✅ Debug session ended")


if __name__ == "__main__":
    asyncio.run(main())

