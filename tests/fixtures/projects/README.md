# Test Project Fixtures

This directory contains mini test projects for each supported language. These are used by the language-agnostic integration tests.

## Structure

```
projects/
├── python/          # Python test project
│   ├── models.py
│   ├── services.py
│   └── main.py
├── javascript/      # JavaScript test project
│   ├── models.js
│   ├── services.js
│   ├── main.js
│   └── package.json
└── rust/            # Rust test project
    ├── models.rs
    ├── services.rs
    ├── main.rs
    └── Cargo.toml
```

## Purpose

Each project contains equivalent code in different languages:

- **models** - Defines `User` class/struct and `create_user` function
- **services** - Defines `UserService` class/struct that uses User
- **main** - Entry point that demonstrates usage

The tests use these projects to verify that language server features work correctly across all supported languages.

## Usage

Tests automatically reference these directories via the `language_project_dir` fixture in `conftest.py`:

```python
async def test_my_feature(
    self, my_service, language_project_dir, language_config: LanguageTestConfig
):
    # language_project_dir points to python/, javascript/, or rust/
    ext = language_config.file_extension
    result = await my_service.do_something(
        file=str(language_project_dir / f"models{ext}")
    )
```

## Adding a New Language

1. Create a new directory: `projects/newlang/`
2. Add equivalent `models`, `services`, and `main` files
3. Add any language-specific config files (package.json, Cargo.toml, etc.)
4. Update `tests/fixtures/language_configs.py` with the new language config
5. Tests will automatically run for the new language!

## Modifying Test Projects

⚠️ **Warning**: These files are used by all integration tests. Changes here affect all tests.

When modifying:
1. Keep the structure consistent across languages
2. Update symbol locations in `language_configs.py` if line numbers change
3. Run all tests to verify changes don't break anything:
   ```bash
   pytest tests/integration/
   ```

## Symbol Locations

The `language_configs.py` file contains expected line numbers for symbols:

- `User` class/struct
- `create_user` function
- `greet` method
- `UserService` class/struct

If you modify these files, update the line numbers in the configs.

