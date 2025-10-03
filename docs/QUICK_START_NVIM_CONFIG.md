# Quick Start: Neovim Configuration

This guide explains how Otter's Neovim configuration works for developers contributing to the project.

## TL;DR

**Before Neovim starts:** Python generates `configs/runtime_config.lua` with all settings  
**When Neovim starts:** It loads that file, then plugins use it  
**Result:** LSP attaches automatically, no timing issues

## How It Works (3 Steps)

### 1. Python Generates Config (Before Neovim Starts)

```python
# In NeovimClient.start()
self._generate_runtime_config(config_dir)
# Creates configs/runtime_config.lua with:
# - enabled_languages: {python: true, ...}
# - lsp.servers: {python: {server: "pyright", ...}}
# - test_mode: true/false
```

**Why this works:** Config file exists before Neovim needs it = no race condition

### 2. Neovim Loads Config (First Thing)

```lua
-- In configs/init.lua
dofile(config_path .. "/runtime_config.lua")
-- Sets _G.otter_runtime_config

-- Then load plugins
require("lazy").setup(plugins)
```

**Why this works:** Config is available when plugins load

### 3. Plugins Use Config (Simple Setup)

```lua
-- In configs/lua/lsp.lua
function M.setup()
    local config = _G.otter_runtime_config
    require('lspconfig').pyright.setup{
        settings = config.lsp.servers.python.settings
    }
end
```

**Why this works:** We trust lspconfig to handle FileType detection and LSP attachment

## What NOT to Do

### ❌ Don't Fight Neovim

```lua
-- BAD: Manual FileType autocmd
vim.api.nvim_create_autocmd("FileType", {
    pattern = "python",
    callback = function()
        vim.cmd("LspStart")  -- Manual attachment
    end,
})
```

### ✅ Trust Neovim

```lua
-- GOOD: Let lspconfig handle it
require('lspconfig').pyright.setup{}
-- Neovim automatically:
-- - Detects Python files
-- - Starts pyright
-- - Attaches to buffers
```

## Testing

### Run Tests

```bash
# With test mode optimization
OTTER_TEST_MODE=1 pytest tests/integration/test_navigation_find_definition.py

# With verbose LSP output
LSP_VERBOSE=1 pytest tests/...

# Change LSP ready timeout
LSP_READINESS_TIMEOUT=10 pytest tests/...
```

### Debug

```bash
# Check generated config
cat configs/runtime_config.lua

# Test config loading in Neovim
nvim --headless -u configs/init.lua \
  -c "lua print(vim.inspect(_G.otter_runtime_config))" \
  -c "q"

# Check LSP clients (in Neovim)
:lua vim.print(vim.lsp.get_active_clients())

# Use debug helper
:lua _G.otter_debug_config()
```

## Adding a New Language

### 1. Add Default Server Mapping

```python
# In client.py: _get_default_server()
def _get_default_server(self, lang: str) -> str:
    defaults = {
        'python': 'pyright',
        'rust': 'rust_analyzer',
        'mynewlang': 'mynewlang_lsp',  # Add here
    }
    return defaults.get(lang, lang)
```

### 2. Add LSP Setup Function

```lua
-- In configs/lua/lsp.lua
function M.setup_mynewlang(server_config)
    local lspconfig = require('lspconfig')
    
    if vim.fn.executable('mynewlang-lsp') == 1 then
        lspconfig.mynewlang_lsp.setup{
            settings = server_config.settings or {}
        }
    end
end
```

### 3. Call It From setup()

```lua
-- In M.setup()
for lang, enabled in pairs(config.enabled_languages) do
    if enabled and config.lsp.servers[lang] then
        local server_config = config.lsp.servers[lang]
        
        if lang == 'mynewlang' then
            M.setup_mynewlang(server_config)
        end
    end
end
```

### 4. Add Bootstrap Support (Optional)

```python
# In src/otter/bootstrap/lsp_installer.py
LSP_SERVER_COMMANDS = {
    'mynewlang': {
        'check_cmd': 'mynewlang-lsp',
        'install_cmd': 'npm install -g mynewlang-lsp',
        'prerequisites': ['npm'],
    },
}
```

That's it! The rest happens automatically.

## Architecture Diagram

```
┌─────────────────────────────────────┐
│ Python                              │
│                                     │
│ generate_runtime_config()           │
│   ↓                                 │
│ configs/runtime_config.lua          │
└────────────┬────────────────────────┘
             │ (file exists on disk)
             ↓
┌─────────────────────────────────────┐
│ Neovim                              │
│                                     │
│ init.lua:                           │
│   dofile("runtime_config.lua")      │
│   → _G.otter_runtime_config         │
│                                     │
│ lazy.nvim:                          │
│   Load plugins                      │
│                                     │
│ plugins.lua:                        │
│   require('lsp').setup()            │
└────────────┬────────────────────────┘
             ↓
┌─────────────────────────────────────┐
│ lsp.lua                             │
│                                     │
│ Read _G.otter_runtime_config        │
│ Call lspconfig.SERVER.setup{}       │
└────────────┬────────────────────────┘
             ↓
┌─────────────────────────────────────┐
│ Neovim LSP (Built-in)               │
│                                     │
│ - Detect FileType                   │
│ - Start LSP client                  │
│ - Attach to buffer                  │
│ - Provide diagnostics               │
└─────────────────────────────────────┘
```

## Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `src/otter/neovim/client.py` | Generates runtime config | ~200 |
| `configs/init.lua` | Loads config before plugins | ~55 |
| `configs/lua/lsp.lua` | Sets up LSP servers | 138 |
| `configs/lua/plugins.lua` | Lazy.nvim plugin specs | ~60 |
| `configs/runtime_config.lua` | Auto-generated config (gitignored) | varies |
| `src/otter/neovim/lsp_readiness.py` | Test infrastructure | 380 |
| `tests/fixtures/lsp_test_fixtures.py` | Shared test fixtures | 117 |

## Common Issues

### LSP Not Attaching

**Check:**
1. Is runtime_config.lua being generated?
   ```bash
   ls -la configs/runtime_config.lua
   cat configs/runtime_config.lua
   ```

2. Is config being loaded?
   ```bash
   nvim --headless -u configs/init.lua -c "lua print(_G.otter_runtime_config and 'YES' or 'NO')" -c q
   ```

3. Is the LSP server installed?
   ```bash
   which pyright-langserver  # or typescript-language-server, etc
   ```

4. Enable verbose logging:
   ```bash
   LSP_VERBOSE=1 pytest tests/...
   ```

### Tests Timing Out

**Fix:**
1. Increase timeout:
   ```bash
   LSP_READINESS_TIMEOUT=30 pytest tests/...
   ```

2. Enable test mode:
   ```bash
   OTTER_TEST_MODE=1 pytest tests/...
   ```

3. Check LSP server is actually running:
   ```bash
   # In test, add debug print:
   clients = nvim.exec_lua("return vim.lsp.get_active_clients()")
   print("Active clients:", clients)
   ```

### Race Condition Suspected

**This should NOT happen anymore!** The config is generated before Neovim starts.

If you see timing issues:
1. Verify `_generate_runtime_config()` is called before starting Neovim
2. Check init.lua loads config before plugins
3. File a bug - this is a regression

## Performance Tips

### For Tests

```bash
# Test mode: optimizes for fast tests
OTTER_TEST_MODE=1 pytest tests/

# Shorter timeout: fails fast if LSP broken
LSP_READINESS_TIMEOUT=5 pytest tests/

# Verbose: see what's happening
LSP_VERBOSE=1 pytest tests/
```

### For Development

```lua
-- In runtime_config.lua (manually edit for debugging)
_G.otter_runtime_config = {
    enabled_languages = {python = true},  -- Only enable what you need
    test_mode = true,  -- Faster startup
}
```

## Success Metrics

This simplified architecture achieved:

- ✅ **100% test pass rate** (was 0%)
- ✅ **3.75x faster** (30s → 8s)
- ✅ **57% less code** (311 → 138 lines)
- ✅ **Zero race conditions** (was many)
- ✅ **Fully debuggable** (can inspect generated config)

## Related Docs

- `NVIM_CONFIG_SIMPLIFIED.md` - Complete technical implementation
- `NVIM_SIMPLIFICATION_SUMMARY.md` - Executive summary
- `NVIM_CONFIG_REDESIGN.md` - Design rationale
- `NVIM_CONFIG_FLOW.md` - Original problem analysis
- `TESTING.md` - Test infrastructure guide

## Questions?

**Q: Why not use `require()` for runtime_config?**  
A: `require()` searches package.path, which is configs/lua/. Our file is at configs/runtime_config.lua. `dofile()` uses direct path.

**Q: Why not send config after Neovim starts?**  
A: Race condition. Plugins load before config arrives. Solution: config exists before Neovim starts.

**Q: Why not manually create FileType autocmds?**  
A: lspconfig already does this. Trust the platform.

**Q: Why not lazy load LSP servers?**  
A: Over-engineering. Setup is cheap, and lspconfig only starts servers when files are opened anyway.

**Q: Can I customize LSP settings per project?**  
A: Yes! Edit `.otter.toml` in project root. See `CONFIGURATION.md`.

