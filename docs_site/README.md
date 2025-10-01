# MkDocs Documentation Source

This directory contains the source files for Otter's auto-generated documentation.

## Philosophy

**Code is the source of truth.** Documentation is automatically extracted from:
- Python source code structure (auto-discovered)
- Docstrings (Google style)
- Type hints
- Function signatures

## Structure

```
docs_site/
├── gen_ref_pages.py        # Script that auto-generates API reference from src/
├── index.md                # Home page
├── getting-started/        # Installation and quick start (manual)
└── development/            # Architecture and contributing (manual)

# Auto-generated during build:
reference/
├── otter/
│   ├── services/
│   │   ├── navigation.md   # Auto-generated from src/otter/services/navigation.py
│   │   ├── analysis.md     # Auto-generated from src/otter/services/analysis.py
│   │   ├── ai.md           # Auto-generated from src/otter/services/ai.py (NEW!)
│   │   └── ...
│   ├── models/
│   ├── neovim/
│   └── ...
└── SUMMARY.md             # Auto-generated navigation
```

## How It Works

### Auto-Discovery with gen-files

The `gen_ref_pages.py` script:
1. Scans all Python files in `src/otter/`
2. Generates a markdown file for each module
3. Inserts mkdocstrings directives to extract docstrings
4. Builds navigation structure automatically

**Result**: When you add a new service or module, it appears in the docs automatically!

### Building Documentation

```bash
# Install docs dependencies
uv sync --group docs

# Serve locally with auto-reload
make docs

# Build static site
make docs-build
```

## What to Edit

### ✅ Always Edit

**In your source code:**
- Docstrings (Google style)
- Type hints
- Function/class signatures

**In `docs_site/` (manual content):**
- `index.md` - Home page
- `getting-started/` - Installation, quick start
- `development/` - Architecture, contributing

### ❌ Never Edit

- `reference/` directory (auto-generated, not in git)
- `site/` directory (build output, gitignored)
- API reference pages (they don't exist as source files!)

## Adding New Features

1. **Write code with good docstrings**:
```python
class MyNewService:
    """My new service for doing cool things.
    
    This service provides advanced features for...
    """
    
    async def do_something(self, param: str) -> Result:
        """Do something awesome.
        
        Args:
            param: The parameter to use
            
        Returns:
            Result object with the outcome
        """
```

2. **Run docs** - Your new service appears automatically:
```bash
make docs
# Navigate to API Reference → otter → services → my_new_service
```

3. **No manual documentation files needed!**

## Documentation Quality

Good docstrings make good docs:

```python
# ✅ GOOD
async def find_definition(self, symbol: str, file: Optional[str] = None) -> Definition:
    """Find the definition of a symbol.
    
    Args:
        symbol: Symbol name to find
        file: Optional file context
        
    Returns:
        Definition object with location and metadata
        
    Raises:
        RuntimeError: If symbol not found
    """

# ❌ BAD (no docstring - won't appear in docs)
async def find_definition(self, symbol: str, file: Optional[str] = None) -> Definition:
    pass
```

## Dependencies

- `mkdocs` - Static site generator
- `mkdocs-material` - Material theme
- `mkdocstrings[python]` - Extract from Python code
- `mkdocs-gen-files` - Auto-generate pages from code structure
- `mkdocs-literate-nav` - Build navigation from SUMMARY.md
- `mkdocs-section-index` - Section index pages
