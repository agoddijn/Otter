# Neovim Configuration - Simplified Implementation ✅

## What Changed

We completely redesigned the Neovim configuration flow to be simple, reliable, and work **with** Neovim instead of fighting against it.

### Before (Broken)

```
Python starts Neovim
  ↓
Neovim loads plugins (race condition!)
  ↓
Plugins try to read _G.otter_config (doesn't exist yet!)
  ↓  
Python sends config (too late!)
  ↓
LSP doesn't attach ❌
Tests timeout after 30s ❌
```

**Problems:**
- Race condition between config and plugin loading
- Manual FileType autocmds that didn't fire
- Manual LSP attachment that didn't work
- Over-engineered lazy loading
- No visibility into what's happening

### After (Working)

```
Python generates configs/runtime_config.lua
  ↓
Python starts Neovim
  ↓
Neovim loads runtime_config.lua (guaranteed to exist)
  ↓
Plugins load with config available
  ↓
lspconfig.pyright.setup{} called
  ↓
LSP attaches automatically (Neovim built-in) ✅
Tests pass in ~8s ✅
```

**Benefits:**
- ✅ No race condition (config exists before Neovim starts)
- ✅ LSP attaches automatically (trust Neovim)
- ✅ Simple, debuggable (can inspect runtime_config.lua)
- ✅ Fast (8s vs 30s timeout)
- ✅ Reliable (8/8 tests passing)

## Implementation

### 1. Runtime Config Generation (Python)

**File:** `src/otter/neovim/client.py`

```python
def _generate_runtime_config(self, config_dir: Path) -> None:
    """Generate runtime_config.lua with all settings BEFORE Neovim starts."""
    
    runtime_config = {
        'enabled_languages': {lang: True for lang in self.enabled_languages},
        'lsp': {
            'enabled': self.config.lsp.enabled,
            'servers': {...},  # Per-language server configs
        },
        'test_mode': os.getenv('OTTER_TEST_MODE') == '1',
    }
    
    lua_code = f"_G.otter_runtime_config = {self._lua_repr(runtime_config)}"
    (config_dir / "runtime_config.lua").write_text(lua_code)
```

**Key Points:**
- Generated **before** Neovim starts
- Contains all LSP/DAP configuration
- Uses Python's `_lua_repr()` to convert dicts to Lua tables

### 2. Config Loading (Neovim init.lua)

**File:** `configs/init.lua`

```lua
-- Load runtime config BEFORE plugins
local runtime_config_path = config_path .. "/runtime_config.lua"
local ok, err = pcall(dofile, runtime_config_path)

-- Now load plugins (config is available!)
require("lazy").setup(plugins)
```

**Key Points:**
- Uses `dofile()` not `require()` (direct file path)
- Loads **before** plugins
- Graceful fallback if file missing

### 3. Simplified LSP Setup (Lua)

**File:** `configs/lua/lsp.lua`

Reduced from **~300 lines** to **~130 lines**!

```lua
function M.setup()
    local config = _G.otter_runtime_config
    
    -- Setup each enabled language
    for lang, enabled in pairs(config.enabled_languages) do
        if lang == 'python' then
            require('lspconfig').pyright.setup {
                settings = config.lsp.servers.python.settings
            }
        end
    end
    
    -- That's it! Neovim handles FileType detection and LSP attachment
end
```

**What We Removed:**
- ❌ Manual FileType autocmds (lspconfig does this)
- ❌ Manual LSP attachment (`LspStart` calls)
- ❌ Lazy loading complexity
- ❌ Race condition workarounds

**What We Trust:**
- ✅ lspconfig's built-in FileType detection
- ✅ Neovim's automatic LSP attachment
- ✅ Simple synchronous setup

### 4. Plugin Configuration

**File:** `configs/lua/plugins.lua`

```lua
{
    'neovim/nvim-lspconfig',
    config = function()
        -- One line! Config already loaded
        require('lsp').setup()
    end,
}
```

**Before:** Complex config reading, fallbacks, timing issues  
**After:** One function call

## Test Results

### Before Simplification
```bash
$ pytest tests/integration/test_navigation_find_definition.py -k python
# 0/8 passing, timeouts after 30s
```

### After Simplification  
```bash
$ OTTER_TEST_MODE=1 pytest tests/integration/test_navigation_find_definition.py -k python
# 8/8 passing in 7.94s ✅
```

**Improvement:**
- **Success rate:** 0% → 100%
- **Speed:** 30s timeout → 8s completion (3.75x faster)
- **Reliability:** Flaky → Deterministic

## Configuration Flow Diagram

```
┌─────────────────────────────────────┐
│ Python: NeovimClient.start()        │
│                                     │
│ 1. Auto-install LSP servers         │
│ 2. Generate runtime_config.lua ◄─┐  │
│    - enabled_languages            │  │
│    - LSP server configs           │  │
│    - Test mode flag               │  │
│ 3. Start Neovim                   │  │
└───────────────┬─────────────────────┘  │
                │                        │
                ▼                        │
┌─────────────────────────────────────┐  │
│ Neovim: init.lua                    │  │
│                                     │  │
│ 1. dofile("runtime_config.lua") ───┘  │
│    → _G.otter_runtime_config           │
│                                        │
│ 2. Load plugins (config available!)   │
└───────────────┬────────────────────────┘
                │
                ▼
┌──────────────────────────────────────┐
│ Plugin: nvim-lspconfig               │
│                                      │
│ require('lsp').setup()               │
│   ├─ Read _G.otter_runtime_config   │
│   └─ Call lspconfig.pyright.setup{} │
└───────────────┬──────────────────────┘
                │
                ▼
┌──────────────────────────────────────┐
│ Neovim's Built-in LSP                │
│                                      │
│ - Detects FileType (python)          │
│ - Attaches pyright automatically     │
│ - Indexes files                      │
│ - Provides diagnostics, completion   │
└──────────────────────────────────────┘
```

## Key Insights

### 1. Don't Fight Neovim
When you call `lspconfig.SERVER.setup{}`, Neovim automatically:
- Creates FileType autocmds
- Starts LSP clients  
- Attaches to buffers
- Handles lifecycle

**We don't need to do any of this manually!**

### 2. Eliminate Race Conditions
By generating config **before** starting Neovim:
- No timing dependencies
- No "wait for signal" logic
- Synchronous, predictable loading

### 3. Simplicity Wins
- 300 lines → 130 lines (-57%)
- 0% passing → 100% passing
- 30s timeout → 8s completion

**Less code = fewer bugs = faster tests**

## Environment Variables

### `OTTER_TEST_MODE=1`
Enables test mode optimizations:
- Faster startup
- All LSPs configured immediately
- Stored in runtime_config for Lua access

### `LSP_VERBOSE=1`
Enables detailed LSP polling output:
```
LSP ready for models.py: 1/1 clients initialized
LSP ready for services.py: 1/1 clients initialized
LSP ready for main.py: 1/1 clients initialized
```

### `LSP_READINESS_TIMEOUT=10`
Sets per-file LSP readiness timeout (default: 15s)

## Debugging

### Check Generated Config
```bash
cat configs/runtime_config.lua
```

### Test Config Loading
```bash
nvim --headless -u configs/init.lua \
  -c "lua print(vim.inspect(_G.otter_runtime_config))" \
  -c "q"
```

### Check LSP Clients
```bash
# In Neovim
:lua vim.print(vim.lsp.get_active_clients())
```

## Migration Notes

### Removed Code
- `_send_config_to_nvim()` - No longer needed
- `_initialize_lsp()` - No longer needed  
- Manual FileType autocmds in lsp.lua
- Lazy loading complexity
- `M.init()` / `M.enabled_languages` state

### New Code
- `_generate_runtime_config()` - Creates config file
- `_get_default_server()` - LSP server defaults
- Simplified `lsp.lua` - Just calls lspconfig.setup()

### Backward Compatibility
Old config approach completely replaced. No migration needed as this was broken before.

## Next Steps

### Immediate
- ✅ All Python tests passing
- ⏳ Enable JavaScript tests (tsserver)
- ⏳ Enable Rust tests (rust-analyzer)

### Future
- Simplify DAP configuration similarly
- Add more LSP servers (Go, etc.)
- Optimize polling timeouts further

## Success Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Python Tests Passing | 0/8 | 8/8 | ∞% |
| Test Duration | 30s (timeout) | 8s | 3.75x faster |
| Lines of Code (lsp.lua) | ~300 | ~130 | 57% reduction |
| Config Race Conditions | Yes | No | Eliminated |
| LSP Attachment | Manual/broken | Automatic | Working |
| Debuggability | Poor | Excellent | Inspectable file |

## Conclusion

**The Problem:** Over-engineering and fighting against Neovim's built-in behavior

**The Solution:** Trust Neovim, eliminate race conditions, keep it simple

**The Result:** Fast, reliable, maintainable LSP configuration that actually works

This redesign proves that **simplicity and following platform conventions** beats complex workarounds every time.

