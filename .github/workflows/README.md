# GitHub Actions Workflows

This directory contains CI/CD workflows for Otter.

## Workflows

### `test.yml` - Full Test Suite
**Runs on**: PRs and pushes to `main` and `dev` branches

**What it does**:
- Installs system dependencies (Neovim, Node.js, etc.)
- Sets up Python 3.12
- Installs Python dependencies and LSP servers
- Runs the complete test suite
- Checks type safety with mypy
- Lints code with ruff

**Duration**: ~5-10 minutes (includes LSP server installation)

**When it fails**: 
- Tests are failing
- Type errors detected
- Linting issues found

### `lint.yml` - Quick Lint Check
**Runs on**: PRs and pushes to `main` and `dev` branches

**What it does**:
- Checks code formatting with ruff
- Checks code style with ruff
- Checks type safety with mypy

**Duration**: ~1-2 minutes

**When it fails**:
- Code formatting issues
- Linting violations
- Type errors

**Tip**: Run `make lint` locally before pushing to catch issues early!

## Adding New Workflows

When adding new workflows:
1. Create a new `.yml` file in this directory
2. Follow the naming convention: `{purpose}.yml`
3. Document it in this README
4. Test it on a PR before merging

## Status Badges

Add to README.md:

```markdown
[![Tests](https://github.com/your-org/otter/actions/workflows/test.yml/badge.svg)](https://github.com/your-org/otter/actions/workflows/test.yml)
[![Lint](https://github.com/your-org/otter/actions/workflows/lint.yml/badge.svg)](https://github.com/your-org/otter/actions/workflows/lint.yml)
```

Replace `your-org` with your GitHub organization/username.

