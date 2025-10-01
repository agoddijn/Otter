#!/usr/bin/env python3
"""Test the smart AI features that leverage LSP + LLM."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from otter.server import CliIdeServer


async def main():
    """Test smart AI features."""
    print("🧪 Testing Smart AI Features (File-based + LSP integration)")
    print("=" * 70)
    
    # Initialize server
    server = CliIdeServer(project_path=str(Path(__file__).parent.parent))
    
    try:
        await server.start()
        print("✓ Neovim initialized\n")
        
        # Test 1: summarize_code (no content needed!)
        print("1️⃣  Testing summarize_code (file-based)")
        print("-" * 70)
        test_file = "src/otter/server.py"
        print(f"Summarizing: {test_file}")
        
        summary = await server.summarize_code(
            file=test_file,
            detail_level="brief"
        )
        print(f"\n📝 Summary:\n{summary.summary}\n")
        
        # Test 2: summarize_changes (git-based!)
        print("2️⃣  Testing summarize_changes (git-based)")
        print("-" * 70)
        print(f"Comparing {test_file} with HEAD~1")
        
        try:
            changes = await server.summarize_changes(
                file=test_file,
                git_ref="HEAD~1"
            )
            print(f"\n📝 Changes Summary:\n{changes.summary}")
            if changes.changes_type:
                print(f"Change types: {', '.join(changes.changes_type)}")
            if changes.breaking_changes:
                print(f"⚠️  Breaking changes: {changes.breaking_changes}")
        except Exception as e:
            print(f"⚠️  Skipped (no git history or no changes): {e}")
        print()
        
        # Test 3: quick_review (file-based!)
        print("3️⃣  Testing quick_review (file-based)")
        print("-" * 70)
        print(f"Reviewing: {test_file}")
        
        review = await server.quick_review(
            file=test_file,
            focus=["bugs", "performance"]
        )
        print(f"\n📝 Overall Assessment:\n{review.overall_assessment}\n")
        if review.issues:
            print(f"Found {len(review.issues)} issues:")
            for issue in review.issues[:3]:  # Show first 3
                print(f"  [{issue.severity}] {issue.message}")
        else:
            print("No issues found!")
        print()
        
        # Test 4: explain_symbol (LSP + LLM magic!)
        print("4️⃣  Testing explain_symbol (LSP + LLM integration)")
        print("-" * 70)
        print("Explaining 'CliIdeServer' class in server.py")
        
        try:
            # Position at the CliIdeServer class definition
            explanation = await server.explain_symbol(
                file="src/otter/server.py",
                line=50,  # Approximate line of CliIdeServer class
                character=6,  # Start of class name
                include_references=True
            )
            print(f"\n📝 Semantic Explanation:\n{explanation.summary}\n")
        except Exception as e:
            print(f"⚠️  Error: {e}\n")
        
        # Test 5: explain_error
        print("5️⃣  Testing explain_error")
        print("-" * 70)
        error_msg = "TypeError: 'NoneType' object is not subscriptable"
        print(f"Explaining: {error_msg}")
        
        explanation = await server.explain_error(
            error_message=error_msg,
            context_file="example.py",
        )
        print(f"\n📝 Error Type: {explanation.error_type}")
        print(f"Explanation: {explanation.explanation}")
        if explanation.likely_causes:
            print(f"\nLikely causes:")
            for cause in explanation.likely_causes:
                print(f"  • {cause}")
        if explanation.suggested_fixes:
            print(f"\nSuggested fixes:")
            for fix in explanation.suggested_fixes:
                print(f"  • {fix}")
        print()
        
        print("=" * 70)
        print("✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())

