# Documentation Inventory

## Current State: 25 markdown files (280KB)

### High-Level Docs (Keep & Consolidate)
- **README.md** ✅ - Main project README
- **ROADMAP.md** ⚠️ - Check if outdated
- **CONTRIBUTING.md** ✅ - Keep for open source

### User-Facing Docs (Consolidate)
- **USER_GUIDE.md** ✅ → Needs review
- **QUICK_START_NVIM_CONFIG.md** ⚠️ → Consolidate into Quick Start
- **CONFIGURATION.md** ✅ → Needs review
- **DEPENDENCIES.md** ⚠️ → Move to installation docs

### Technical/Architecture Docs (Keep Best, Archive Rest)
- **ARCHITECTURE.md** ✅ - Core architecture
- **TECHNICAL_GUIDE.md** ✅ - Deep dive

**Neovim Config Evolution** (DELETE - Historical):
- ❌ NVIM_CONFIG_FLOW.md
- ❌ NVIM_CONFIG_REDESIGN.md
- ❌ NVIM_CONFIG_SIMPLIFIED.md
- ❌ NVIM_SIMPLIFICATION_SUMMARY.md
→ Keep only final state in ARCHITECTURE.md

**Config Evolution** (DELETE - Historical):
- ❌ UNIFIED_CONFIG.md
- ❌ LANGUAGE_RUNTIME_CONFIG.md
- ❌ GENERIC_RUNTIME_RESOLVER.md
- ❌ RUNTIME_RESOLVER_IMPLEMENTATION.md
→ Keep only final state in CONFIGURATION.md

**Debug System Evolution** (DELETE - Historical):
- ❌ DEBUG_TOOLS_ENHANCED.md
- ❌ DEBUG_ENHANCEMENTS_SUMMARY.md
- ❌ DEBUG_TRANSPARENCY.md
- ❌ DEBUG_SESSION_TRACKING.md
- ❌ DAP_BOOTSTRAP.md
- ❌ DAP_BREAKPOINT_FIX.md
→ Keep only final state in TECHNICAL_GUIDE.md

**Testing Docs** (DELETE - Already in /tests):
- ❌ TEST_IMPROVEMENTS.md
- ❌ TESTING.md (duplicate - also in /tests)

## docs_site/ Structure (mkdocs - Keep & Improve)
```
docs_site/
├── index.md
├── getting-started/
│   ├── installation.md
│   └── quick-start.md
├── development/
│   ├── architecture.md
│   └── contributing.md
├── changelog.md
└── gen_ref_pages.py
```

## Proposed Final Structure

### /docs (Developer/Contributor Docs)
```
docs/
├── ARCHITECTURE.md (comprehensive, consolidated)
├── CONTRIBUTING.md
├── DEVELOPMENT.md (setup, testing, releasing)
└── HISTORY/ (archive of evolution docs)
    ├── nvim_config_evolution.md
    ├── debug_system_evolution.md
    └── runtime_resolver_evolution.md
```

### /docs_site (User-Facing Docs - mkdocs)
```
docs_site/
├── index.md
├── getting-started/
│   ├── installation.md
│   ├── quick-start.md
│   └── configuration.md
├── guides/
│   ├── lsp-features.md (navigation, hover, etc.)
│   ├── debugging.md (DAP features)
│   ├── ai-analysis.md
│   └── configuration.md (detailed config guide)
├── reference/
│   ├── mcp-tools.md (auto-generated)
│   ├── configuration-schema.md
│   └── api/ (auto-generated API docs)
├── development/
│   ├── architecture.md
│   ├── contributing.md
│   └── testing.md
└── changelog.md
```

### Root Level
- **README.md** - Project overview, badges, quick links
- **CHANGELOG.md** - Version history
- **LICENSE** - License file

## Consolidation Tasks

### 1. Merge Neovim Config Docs → ARCHITECTURE.md
- Take final state from NVIM_CONFIG_SIMPLIFIED
- Add diagram showing config flow
- Explain runtime_config.lua generation

### 2. Merge Runtime Config Docs → guides/configuration.md
- Take final state from GENERIC_RUNTIME_RESOLVER
- Show examples for each language
- Explain auto-detection logic

### 3. Merge Debug Docs → guides/debugging.md
- Take final state from DEBUG_SESSION_TRACKING
- Document all debug features
- Show examples

### 4. Create New User Guides
- Split USER_GUIDE.md into focused guides
- Create tutorial-style walkthroughs
- Add more examples and screenshots

## Questions for User (Priority 3)
1. Do you want mkdocs for docs or something else?
2. Should we publish docs to GitHub Pages or elsewhere?
3. Do you want API reference docs auto-generated?
4. Should HISTORY/ docs be committed or just deleted?
5. Target audience balance: developers vs. end-users?

## Expected Outcome
- **From:** 25 fragmented docs (280KB)
- **To:** ~10-12 focused docs (similar size, better organized)
- Clear separation: developer docs vs user docs
- Remove historical/evolution docs
- Better navigation and discoverability

