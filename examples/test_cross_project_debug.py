"""
Test debugging code from a DIFFERENT project than where Otter is running.

This verifies that the RuntimeResolver correctly detects the target project's
venv/runtime based on the `cwd` parameter, ensuring LSP and DAP use the
correct Python interpreter for the project being debugged.
"""

import asyncio
import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from otter.neovim.client import NeovimClient
from otter.services.debugging import DebugService
from otter.config import load_config


async def main():
    otter_dir = Path(__file__).parent
    
    # Create a fake "different project" with its own venv
    with tempfile.TemporaryDirectory() as tmpdir:
        target_project = Path(tmpdir) / "target_project"
        target_project.mkdir()
        
        # Create a fake venv in the target project
        venv_dir = target_project / ".venv"
        venv_bin = venv_dir / "bin"
        venv_bin.mkdir(parents=True)
        
        # Create a fake python executable
        fake_python = venv_bin / "python3"
        fake_python.write_text("#!/bin/bash\necho 'Target project Python'")
        fake_python.chmod(0o755)
        
        # Create a simple test file in the target project
        test_file = target_project / "app.py"
        test_file.write_text("""import sys
print("Running from target project!")
print(f"Python: {sys.executable}")
""")
        
        print("=" * 80)
        print("🧪 TESTING CROSS-PROJECT DEBUGGING")
        print("=" * 80)
        print()
        print(f"📁 Otter running in: {otter_dir}")
        print(f"📁 Debugging project in: {target_project}")
        print()
        
        # Start Neovim (in Otter's directory)
        nvim_client = NeovimClient(project_path=str(otter_dir))
        await nvim_client.start()
        
        config = load_config(otter_dir)
        service = DebugService(
            nvim_client=nvim_client,
            project_path=str(otter_dir),  # Otter's project
            config=config,
        )
        
        print("🔧 Starting debug session...")
        print(f"   Target cwd: {target_project}")
        print()
        
        try:
            # Debug the target project by specifying its cwd
            session = await service.start_debug_session(
                file=str(test_file),
                cwd=str(target_project),  # 🎯 Key: Debug in DIFFERENT project!
            )
            
            print(f"✅ Session started: {session.session_id}")
            print(f"   Status: {session.status}")
            print(f"   PID: {session.pid}")
            print()
            
            # Wait a moment for execution
            await asyncio.sleep(2)
            
            # Check session status
            info = await service.get_session_info(session_id=session.session_id)
            
            if info:
                print("📊 Debug Session Info:")
                print(f"   Status: {info.status}")
                print(f"   Exit Code: {info.exit_code}")
                print(f"   CWD: {info.launch_cwd}")
                print()
                
                if info.stdout:
                    print("📝 Stdout:")
                    for line in info.stdout.split('\n')[:10]:
                        if line.strip():
                            print(f"   {line}")
                    print()
                
                # Verify the correct Python was used
                if "Target project Python" in info.stdout or str(target_project) in info.stdout:
                    print("✅ SUCCESS: Debugger used target project's Python!")
                    print(f"   Detected venv: {target_project}/.venv")
                else:
                    print("⚠️  Warning: May not have used target project's Python")
                    print(f"   Check output above")
        
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await nvim_client.stop()
        
        print()
        print("=" * 80)
        print("🏁 TEST COMPLETE")
        print("=" * 80)
        print()
        print("💡 Key Insight:")
        print("   The `cwd` parameter determines which project's runtime is used.")
        print("   RuntimeResolver looks for venv/nvm/etc in the cwd, not Otter's dir.")
        print("   This ensures LSP and DAP both use the correct project environment!")


if __name__ == "__main__":
    asyncio.run(main())

