"""Example demonstrating buffer editing capabilities.

This example shows the complete editing workflow:
1. Get buffer info
2. Preview edits (unified diff)
3. Apply edits
4. Get buffer diff (buffer vs disk)
5. Option to discard or save changes
6. Save changes to disk
"""

import asyncio
from pathlib import Path
import sys
import tempfile

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from otter.server import CliIdeServer


async def example_buffer_editing():
    """Demonstrate buffer editing workflow."""
    # Create a temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""# Test file for editing
def old_function():
    '''Old implementation'''
    return 42

def another_function():
    return old_function()
""")
        test_file = f.name
    
    try:
        # Initialize server
        project_path = str(Path(test_file).parent)
        server = CliIdeServer(project_path=project_path)
        await server.start()
        
        print("=" * 60)
        print("BUFFER EDITING DEMONSTRATION")
        print("=" * 60)
        
        # 1. Get buffer info
        print("\n1. Getting buffer info...")
        info = await server.get_buffer_info(test_file)
        print(f"   File: {test_file}")
        print(f"   Is open: {info.is_open}")
        print(f"   Is modified: {info.is_modified}")
        print(f"   Line count: {info.line_count}")
        print(f"   Language: {info.language}")
        
        # 2. Preview an edit
        print("\n2. Previewing edit (refactor function)...")
        from otter.models.responses import BufferEdit
        
        edits = [
            BufferEdit(
                line_start=2,
                line_end=4,
                new_text="def new_function():\n    '''New implementation'''\n    return 100\n"
            )
        ]
        
        preview_result = await server.edit_buffer(test_file, edits, preview=True)
        
        if preview_result.preview:
            print("\n   Preview (unified diff):")
            print("   " + "\n   ".join(preview_result.preview.split("\n")))
        
        # 3. Apply the edit
        print("\n3. Applying edit...")
        apply_result = await server.edit_buffer(test_file, edits, preview=False)
        
        print(f"   Applied: {apply_result.applied}")
        print(f"   Success: {apply_result.success}")
        print(f"   New line count: {apply_result.line_count}")
        print(f"   Is modified: {apply_result.is_modified}")
        
        # 4. Verify with buffer info again
        print("\n4. Verifying changes...")
        final_info = await server.get_buffer_info(test_file)
        print(f"   Line count: {final_info.line_count}")
        print(f"   Is modified: {final_info.is_modified}")
        
        # 5. Get diff between buffer and disk
        print("\n5. Getting diff (buffer vs disk)...")
        diff_result = await server.get_buffer_diff(test_file)
        print(f"   Has changes: {diff_result.has_changes}")
        if diff_result.has_changes and diff_result.diff:
            diff_lines = diff_result.diff.split("\n")[:15]  # First 15 lines
            print("   Diff preview:")
            for line in diff_lines:
                print(f"   {line}")
        
        # 6. Demonstrate discard (optional - commented out)
        # Uncomment to test reverting changes:
        # print("\n6. Testing discard_buffer (reverting changes)...")
        # discard_result = await server.discard_buffer(test_file)
        # print(f"   Discarded: {discard_result.success}")
        # print(f"   Is modified: {discard_result.is_modified} (should be False)")
        
        # 7. Save the buffer to disk
        print("\n6. Saving buffer to disk...")
        save_result = await server.save_buffer(test_file)
        print(f"   Success: {save_result.success}")
        print(f"   Is modified: {save_result.is_modified} (should be False)")
        
        # 8. Verify diff is empty after save
        print("\n7. Checking diff after save...")
        final_diff = await server.get_buffer_diff(test_file)
        print(f"   Has changes: {final_diff.has_changes} (should be False)")
        
        # 9. Verify with buffer info after save
        print("\n8. Verifying buffer state...")
        post_save_info = await server.get_buffer_info(test_file)
        print(f"   Is modified: {post_save_info.is_modified} (should be False)")
        
        # 10. Read the saved file content from disk
        print("\n9. Reading saved file from disk:")
        with open(test_file, 'r') as f:
            disk_content = f.read()
        print("   " + "\n   ".join(disk_content.split("\n")[:10]))
        
        print("\n" + "=" * 60)
        print("✅ Buffer editing demonstration complete!")
        print("=" * 60)
        
        await server.stop()
    
    finally:
        # Clean up
        Path(test_file).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(example_buffer_editing())

