# Contributing

## Core Principles

### 1. We're a Wrapper, Not a Reimplementer

✅ **DO**: Use TreeSitter, LSP, DAP, ripgrep  
❌ **DON'T**: Implement language-specific parsers in Python

### 2. Language-Agnostic by Design

Define language-specific queries, use universal execution.

### 3. Type-Safe & Well-Tested

- Dataclasses for all responses
- Mypy strict mode (zero errors)
- Integration tests with real LSP/DAP
- Parameterized tests across languages

### 4. Documentation from Code

- Code is source of truth
- Docstrings → API docs (auto-generated)
- Update existing docs, don't create new ones
- Use `tmp/` for temporary notes (gitignored)

## Development Setup

```bash
git clone <repository-url>
cd otter
make check-deps
make install-deps
make install
make test
```

## Code Patterns

See the repository's `docs/CONTRIBUTING.md` for:
- Service organization
- Path handling
- Async operations
- LSP integration
- TreeSitter queries
- DAP debugging
- Testing patterns

## Documentation Guidelines

### Update, Don't Create

✅ **Update existing docs**:
- `docs/USER_GUIDE.md` - Add tool docs
- `docs/ARCHITECTURE.md` - Design changes
- `docs/CONTRIBUTING.md` - New patterns
- `CHANGELOG.md` - Version history

❌ **Never create**:
- Completion reports
- Analysis documents
- Summary documents
- Personal TODOs

### Temporary Work

Use `tmp/` directory (gitignored) for notes during development.

## Pull Request Process

1. Run linting: `make lint`
2. Run tests: `make test`
3. Check types: `mypy --strict src/`
4. Update docs if needed
5. Add to CHANGELOG.md

## Adding New Features

Checklist:
- [ ] Add to appropriate service
- [ ] Use `resolve_workspace_path()` for paths
- [ ] Wrap pynvim calls in executor
- [ ] Add timeouts to async operations
- [ ] Write parameterized integration tests
- [ ] Update USER_GUIDE.md
- [ ] Add to CHANGELOG.md

For complete details, see `docs/CONTRIBUTING.md` in the repository.

