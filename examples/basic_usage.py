#!/usr/bin/env python3
"""
Example: Basic Otter Usage - Navigation & Code Intelligence

This demonstrates core IDE features:
- Go to definition
- Find references
- Hover information
- Code completions
- Symbol search

Usage:
    python examples/basic_usage.py
"""

import asyncio
from pathlib import Path
from otter.server import CliIdeServer


async def main():
    # Initialize Otter pointing to your project
    project_path = Path(".").resolve()  # Current directory
    
    print(f"📂 Opening project: {project_path}")
    server = CliIdeServer(project_path=str(project_path))
    await server.start()
    
    try:
        print("\n" + "="*70)
        print("🔍 OTTER IDE FEATURES DEMO")
        print("="*70)
        
        # Example file to analyze
        example_file = "src/otter/server.py"
        
        # 1. Go to Definition
        print("\n1️⃣  GO TO DEFINITION")
        print("-" * 70)
        print(f"Finding definition of 'CliIdeServer' in {example_file}...")
        
        definitions = await server.find_definition(
            file=example_file,
            line=20,  # Line with CliIdeServer reference
            column=10
        )
        
        if definitions:
            for defn in definitions[:3]:  # Show first 3
                print(f"   ✅ Found: {defn.file}:{defn.line}")
                print(f"      {defn.context_before}")
                print(f"   → {defn.target_line}")
                print(f"      {defn.context_after}\n")
        
        # 2. Find References
        print("\n2️⃣  FIND REFERENCES")
        print("-" * 70)
        print("Finding all references to 'start_debug_session'...")
        
        references = await server.find_references(
            file="src/otter/services/debugging.py",
            line=85,  # Line with function definition
            column=15
        )
        
        print(f"   ✅ Found {len(references)} references:")
        for ref in references[:5]:  # Show first 5
            ref_type = "📍 Definition" if ref.is_definition else "📎 Reference"
            print(f"   {ref_type}: {ref.file}:{ref.line}")
        
        # 3. Hover Information
        print("\n3️⃣  HOVER INFORMATION")
        print("-" * 70)
        print("Getting hover info for 'DebugService'...")
        
        hover_info = await server.get_hover_info(
            file="src/otter/services/debugging.py",
            line=20,
            column=10
        )
        
        if hover_info:
            print(f"   Symbol: {hover_info.symbol}")
            print(f"   Type: {hover_info.type_info}")
            if hover_info.documentation:
                doc_preview = hover_info.documentation[:100] + "..."
                print(f"   Docs: {doc_preview}")
        
        # 4. Code Completions
        print("\n4️⃣  CODE COMPLETIONS")
        print("-" * 70)
        print("Getting completions for 'self.' in a service...")
        
        completions = await server.get_completions(
            file="src/otter/services/debugging.py",
            line=100,
            column=20
        )
        
        if completions:
            print(f"   ✅ Found {len(completions)} completions:")
            for comp in completions[:10]:  # Show first 10
                kind_icon = "🔧" if comp.kind == "method" else "📦"
                print(f"   {kind_icon} {comp.label}: {comp.kind}")
        
        # 5. Workspace Symbols
        print("\n5️⃣  WORKSPACE SYMBOLS")
        print("-" * 70)
        print("Searching for symbols matching 'Debug'...")
        
        symbols = await server.get_symbols(
            file="src/otter/services/debugging.py",
            symbol_type=["class", "function"]
        )
        
        if symbols:
            print(f"   ✅ Found {len(symbols)} symbols:")
            for sym in symbols[:10]:  # Show first 10
                type_icon = "🏛️" if sym.type == "class" else "⚡"
                print(f"   {type_icon} {sym.name} ({sym.type}) at line {sym.line}")
        
        # 6. Diagnostics
        print("\n6️⃣  DIAGNOSTICS (Linter Errors)")
        print("-" * 70)
        
        file_content = await server.read_file(
            file=example_file,
            include_diagnostics=True
        )
        
        if file_content.diagnostics:
            print(f"   ⚠️  Found {len(file_content.diagnostics)} issues:")
            for diag in file_content.diagnostics[:5]:
                severity_icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(diag.severity, "•")
                print(f"   {severity_icon} Line {diag.line}: {diag.message}")
        else:
            print("   ✅ No issues found!")
        
        print("\n" + "="*70)
        print("✨ DEMO COMPLETE!")
        print("="*70)
        print("\n💡 Tip: Try these features on your own codebase:")
        print("   1. Change project_path to your project")
        print("   2. Update file paths to your source files")
        print("   3. Adjust line/column numbers to your code")
        print("\n🚀 Otter is now ready for MCP integration!")
        print("   Use with Claude Desktop, Cline, or other MCP clients")
        
    finally:
        await server.stop()
        print("\n✅ Session ended\n")


if __name__ == "__main__":
    asyncio.run(main())

