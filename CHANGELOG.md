# Changelog

All notable changes to Otter will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- GitHub Actions CI workflows
  - `test.yml` - Full test suite on PRs to main/dev
  - `lint.yml` - Quick lint and type checking
- Documentation cleanup for open source release
  - Reduced 54 markdown files to 9 (83% reduction)
  - Created focused docs answering What/Why/How
  - Enhanced example configurations with comprehensive comments

### Changed
- Simplified examples directory to only include `.otter.toml` configuration files
- Removed programmatic examples (not needed for MCP consumption)
- Increased LSP readiness timeouts for CI environments (45s vs 15s locally)
- Auto-enable verbose LSP logging in CI for better debugging
- Consolidated integration tests: 18 files (4911 lines) → 6 files (2428 lines)
  - Merged navigation tests (4 files → 1)
  - Merged debugging tests (6 files → 1)
  - Merged workspace tests (3 files → 1)
  - Merged infrastructure tests (3 files → 1)
  - Removed duplicate fixtures and arbitrary delays
  - Better organized by feature domain
- Consolidated unit tests: 7 files (1680 lines) → 4 files (1269 lines)
  - Merged workspace tests (3 files → 1)
  - Removed duplicate test patterns

### Fixed
- 74 linting issues (unused imports, f-strings, bare excepts, etc.)
- CI test reliability with longer LSP indexing timeouts
- LSP server readiness detection using deterministic request-based checks
  - Now uses actual LSP requests (documentSymbol, hover) to verify readiness
  - Removed arbitrary sleep delays in favor of vim.wait() and buf_request_sync
  - Verifies LSP responses are non-empty and useful, not just present

### Removed
- Historical evolution documentation (20+ files)
- mkdocs infrastructure
- Cleanup planning files

---

## Release Notes

Releases will be documented here once the first version is published.
