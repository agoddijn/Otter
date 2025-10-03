#!/usr/bin/env python3
"""Install LSP servers required for running tests.

This script ensures all LSP servers needed for tests are installed
before running the test suite. It's used both locally and in CI.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from otter.bootstrap import (
    check_and_install_lsp_servers,
    check_prerequisites,
    print_missing_prerequisites,
    LSPServerStatus,
)


async def main():
    """Install all LSP servers needed for tests."""
    print("=" * 70)
    print("Installing LSP servers for Otter tests")
    print("=" * 70)
    print()
    
    # Check prerequisites first
    print("📋 Checking prerequisites...")
    prereqs = check_prerequisites()
    
    missing_prereqs = [name for name, available in prereqs.items() if not available]
    
    if missing_prereqs:
        print()
        print_missing_prerequisites()
        print()
        print("⚠️  Some prerequisites are missing. Tests for those languages may fail.")
        print()
    
    # Languages we need for tests
    test_languages = ["python", "javascript", "rust"]
    
    print(f"📦 Installing LSP servers for: {', '.join(test_languages)}")
    print()
    
    # Install with auto_install enabled
    results = await check_and_install_lsp_servers(
        test_languages,
        {},  # Use default configs
        auto_install=True
    )
    
    print()
    print("=" * 70)
    print("Installation Summary")
    print("=" * 70)
    
    installed = []
    failed = []
    
    for lang, status in results.items():
        if status == LSPServerStatus.INSTALLED:
            installed.append(lang)
            print(f"✅ {lang}: Ready")
        else:
            failed.append(lang)
            print(f"❌ {lang}: Not available")
    
    print()
    
    if installed:
        print(f"✅ {len(installed)} language(s) ready: {', '.join(installed)}")
    
    if failed:
        print(f"⚠️  {len(failed)} language(s) not available: {', '.join(failed)}")
        print("   Tests for these languages may be skipped or fail.")
        print()
        return 1
    
    print()
    print("🎉 All test LSP servers are installed!")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

