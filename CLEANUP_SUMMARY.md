# Otter Cleanup Plan - Open Source Ready

## 📊 Current State

| Area | Current | Issues |
|------|---------|--------|
| **Tests** | 328 passing / 54 failing | API signature changes, dataclass migration, LSP environment issues |
| **Examples** | 29 files (140KB) | 22 are dev test files, only 7 legitimate examples |
| **Docs** | 25 MD files (280KB) | Many historical/evolution docs, fragmented structure |

## 🎯 Cleanup Priorities

### Priority 1: Tests (READY TO START) ✅

**Estimated Time:** 4-6 hours

**What's Needed:**
1. **Fix Broken Tests** (1-2h)
   - Update API signatures (remove `cwd` parameter)
   - Fix RuntimeSpec dataclass access
   - Mark/skip unimplemented features
   
2. **Consolidate Test Files** (2-3h)
   - Merge 6 debugging test files → 5 logical groups
   - Merge 4 navigation test files → 2 files
   - Reorganize into `dap/` and `lsp/` subdirectories
   
3. **Improve Test Quality** (1h)
   - Add proper pytest markers
   - Improve test documentation
   - Add test organization README

**Expected Outcome:**
- ✅ All tests passing or properly skipped
- ✅ 15-20% fewer test files
- ✅ Better organization and parallelization

**Action:** Ready to execute! Should I start fixing tests?

---

### Priority 2: Examples (READY TO START) ✅

**Estimated Time:** 2-3 hours

**What's Needed:**
1. **Delete Test Files** (15min)
   - Remove 22 `test_*.py` files
   
2. **Polish Existing** (30min)
   - Improve `debug_uvicorn.py` → `debug_server.py`
   - Improve `debug_pytest.py` → `debug_tests.py`
   
3. **Create New Examples** (1-2h)
   - `basic_usage.py` - LSP features walkthrough
   - `examples/README.md` - Overview and index
   - `config_examples/` directory with organized configs
   - `multi_language/` - Real project example

**Expected Outcome:**
- ✅ 29 files → ~15 files
- ✅ All examples are legitimate use cases
- ✅ Well-documented and organized

**Action:** Ready to execute! Should I start cleaning examples?

---

### Priority 3: Documentation (NEEDS CONSULTATION) ⚠️

**Estimated Time:** 6-8 hours

**Key Questions for You:**

1. **Documentation System:**
   - Keep mkdocs (current `docs_site/`)?
   - Or switch to something else (Sphinx, Docusaurus, etc.)?

2. **Publishing:**
   - GitHub Pages?
   - Read the Docs?
   - Self-hosted?

3. **API Reference:**
   - Auto-generate from code (pdoc, sphinx-autodoc)?
   - Manual API docs?
   - Both?

4. **Historical Docs:**
   - Keep evolution docs in `docs/HISTORY/`?
   - Or just delete them (git history has them)?

5. **Target Audience:**
   - Primary: MCP agent developers using Otter?
   - Primary: Contributors to Otter?
   - Equal balance?

**Proposed Structure (Pending Your Input):**

```
/
├── README.md (project overview)
├── CHANGELOG.md
├── docs/ (contributor docs)
│   ├── ARCHITECTURE.md
│   ├── CONTRIBUTING.md
│   └── DEVELOPMENT.md
└── docs_site/ (user docs - mkdocs)
    ├── getting-started/
    ├── guides/
    ├── reference/
    └── development/
```

**Action:** Awaiting your answers to questions above!

---

### Priority 4: CI/CD (AFTER DOCS) ⏳

**Estimated Time:** 3-4 hours

**Dependencies:** Needs Priority 3 decisions

**What's Planned:**
1. **GitHub Actions Workflow:**
   - Run tests on PR
   - Build and publish docs
   - Release to PyPI
   
2. **Doc Building:**
   - Auto-deploy docs on merge to main
   - Version docs with releases
   
3. **Release Automation:**
   - Version bumping
   - Changelog generation
   - PyPI publishing

**Action:** Will plan this after Priority 3 is done!

---

## 🚀 Recommended Execution Order

### Week 1: Get Tests Green ✅
**Days 1-2:** Priority 1 (Tests)
- All tests passing
- Good test organization
- Confidence in codebase

### Week 1-2: Clean Examples ✅
**Day 3:** Priority 2 (Examples)  
- Remove cruft
- Polish legitimate examples
- Good first impression

### Week 2: Documentation Strategy ⚠️
**Days 4-5:** Priority 3 (Docs) - **CONSULT FIRST**
- Make decisions on doc structure
- Consolidate and improve docs
- Professional documentation

### Week 2-3: Automation 🤖
**Days 6-7:** Priority 4 (CI/CD)
- Automated testing
- Automated docs publishing
- Automated releases

---

## 📝 Next Steps

**Immediate:**
1. ✅ Review these plans
2. ✅ Approve Priority 1 (Tests) execution
3. ✅ Approve Priority 2 (Examples) execution
4. ⚠️ Answer Priority 3 (Docs) questions

**Then:**
5. Execute Priorities 1 & 2
6. Plan Priority 4 based on Priority 3 decisions

---

## 📂 Generated Planning Files

I've created detailed plans in:
- `TEST_CLEANUP_PLAN.md` - Comprehensive test cleanup strategy
- `EXAMPLES_CLEANUP_PLAN.md` - Examples cleanup strategy
- `DOCS_INVENTORY.md` - Documentation analysis and questions

Review these for full details!

