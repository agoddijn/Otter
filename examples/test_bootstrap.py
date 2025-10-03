#!/usr/bin/env python3
"""Demo script to test the LSP bootstrap functionality.

This script demonstrates Otter's auto-install feature by checking
for LSP servers and showing what would be installed.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from otter.bootstrap import (
    check_and_install_lsp_servers,
    check_lsp_server,
    check_prerequisites,
    print_missing_prerequisites,
)


async def main():
    print("=" * 60)
    print("Otter LSP Bootstrap Demo")
    print("=" * 60)
    print()
    
    # Check prerequisites
    print("📋 Checking prerequisites...")
    prereqs = check_prerequisites()
    for tool, available in prereqs.items():
        status = "✅" if available else "❌"
        print(f"   {status} {tool}")
    print()
    
    if not all(prereqs.values()):
        print_missing_prerequisites()
    
    # Check LSP servers for common languages
    print("🔍 Checking LSP servers...")
    languages = ["python", "javascript", "rust", "go"]
    
    for lang in languages:
        server = check_lsp_server(lang)
        status = "✅" if server.status.value == "installed" else "⚠️ "
        print(f"   {status} {lang}: {server.name} ({server.status.value})")
        if server.status.value == "missing":
            print(f"      Install with: {server.install_method}")
    print()
    
    # Simulate what would happen on Otter startup
    print("🚀 Simulating Otter startup (auto_install=False)...")
    results = await check_and_install_lsp_servers(
        ["python", "javascript"],
        {},
        auto_install=False  # Don't actually install
    )
    
    print()
    print("📊 Results:")
    for lang, status in results.items():
        emoji = "✅" if status.value == "installed" else "⚠️ "
        print(f"   {emoji} {lang}: {status.value}")
    
    print()
    print("=" * 60)
    print("Demo complete!")
    print()
    print("To enable auto-install, add to your .otter.toml:")
    print("  [lsp]")
    print("  auto_install = true")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

