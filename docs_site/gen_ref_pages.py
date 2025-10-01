"""Generate API reference pages from source code structure."""

from pathlib import Path
import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()
src = Path("src")

# Scan all Python files in src/otter
for path in sorted(src.rglob("*.py")):
    module_path = path.relative_to(src).with_suffix("")
    doc_path = path.relative_to(src).with_suffix(".md")
    full_doc_path = Path("reference", doc_path)

    parts = tuple(module_path.parts)

    # Skip __pycache__ and private modules
    if "__pycache__" in parts or any(p.startswith("_") for p in parts[1:]):
        continue

    # Skip __init__.py files (we'll reference the package instead)
    if parts[-1] == "__init__":
        parts = parts[:-1]
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")
    
    if not parts:
        continue

    # Add to navigation
    nav[parts] = doc_path.as_posix()

    # Generate the markdown file with mkdocstrings reference
    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        identifier = ".".join(parts)
        print(f"# {identifier}", file=fd)
        print(f"\n::: {identifier}", file=fd)

    # Set edit path
    mkdocs_gen_files.set_edit_path(full_doc_path, path)

# Generate the navigation file
with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())

