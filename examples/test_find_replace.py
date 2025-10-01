"""Example demonstrating find_and_replace convenience tool.

This example shows how to use find_and_replace for simple text substitutions,
as an alternative to line-based edit_buffer.
"""

import asyncio
from pathlib import Path
import sys
import tempfile

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from otter.server import CliIdeServer


async def example_find_replace():
    """Demonstrate find_and_replace workflow."""
    # Create a temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""# Configuration file
DEBUG = False
LOG_LEVEL = "INFO"
MAX_RETRIES = 3
TIMEOUT = 30

# More config
LOG_LEVEL = "INFO"  # Duplicate for testing
ENVIRONMENT = "production"
""")
        test_file = f.name
    
    try:
        # Initialize server
        project_path = Path(test_file).parent
        server = CliIdeServer(project_path=str(project_path))
        await server.start()
        
        print("=" * 60)
        print("FIND AND REPLACE DEMONSTRATION")
        print("=" * 60)
        
        # 1. Show original file
        print("\n1. Original file:")
        with open(test_file, 'r') as f:
            print("   " + "\n   ".join(f.read().split("\n")))
        
        # 2. Preview replacing all occurrences
        print("\n2. Preview: Replace all 'INFO' with 'DEBUG'...")
        result = await server.find_and_replace(
            test_file,
            find='LOG_LEVEL = "INFO"',
            replace='LOG_LEVEL = "DEBUG"',
            occurrence="all",
            preview=True
        )
        print(f"   Replacements to be made: {result.replacements_made}")
        if result.preview:
            preview_lines = result.preview.split("\n")[:20]
            print("   Preview diff:")
            for line in preview_lines:
                print(f"   {line}")
        
        # 3. Apply the replacement
        print("\n3. Applying replacement...")
        result = await server.find_and_replace(
            test_file,
            find='LOG_LEVEL = "INFO"',
            replace='LOG_LEVEL = "DEBUG"',
            occurrence="all",
            preview=False
        )
        print(f"   Applied: {result.applied}")
        print(f"   Replacements made: {result.replacements_made}")
        print(f"   Is modified: {result.is_modified}")
        
        # 4. Preview replacing first occurrence only
        print("\n4. Preview: Replace first 'DEBUG' with 'WARNING'...")
        result = await server.find_and_replace(
            test_file,
            find="DEBUG",
            replace="WARNING",
            occurrence="first",
            preview=True
        )
        print(f"   Replacements to be made: {result.replacements_made}")
        
        # 5. Apply first occurrence only
        print("\n5. Applying first occurrence replacement...")
        result = await server.find_and_replace(
            test_file,
            find="DEBUG",
            replace="WARNING",
            occurrence="first",
            preview=False
        )
        print(f"   Applied: {result.applied}")
        print(f"   Replacements made: {result.replacements_made}")
        
        # 6. Check buffer diff
        print("\n6. Checking buffer diff (vs disk)...")
        diff_result = await server.get_buffer_diff(test_file)
        print(f"   Has changes: {diff_result.has_changes}")
        if diff_result.has_changes and diff_result.diff:
            diff_lines = diff_result.diff.split("\n")[:15]
            print("   Current diff:")
            for line in diff_lines:
                print(f"   {line}")
        
        # 7. Save changes
        print("\n7. Saving buffer...")
        save_result = await server.save_buffer(test_file)
        print(f"   Saved: {save_result.success}")
        
        # 8. Final file content
        print("\n8. Final file content:")
        with open(test_file, 'r') as f:
            print("   " + "\n   ".join(f.read().split("\n")))
        
        # 9. Test no matches found
        print("\n9. Testing no matches found...")
        result = await server.find_and_replace(
            test_file,
            find="NONEXISTENT",
            replace="SOMETHING",
            occurrence="all",
            preview=True
        )
        print(f"   Replacements: {result.replacements_made}")
        print(f"   Preview: {result.preview}")
        
        print("\n" + "=" * 60)
        print("✅ Find and replace demonstration complete!")
        print("=" * 60)
        
        await server.stop()
    
    finally:
        # Clean up
        Path(test_file).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(example_find_replace())

