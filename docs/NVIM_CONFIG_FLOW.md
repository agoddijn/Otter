# Neovim Configuration Flow Documentation

This document explains how Otter's Neovim configuration works and how LSP servers are initialized.

## Architecture Overview

```
Python (otter/neovim/client.py)
    ↓
Neovim Headless Instance
    ↓
init.lua → lazy.nvim → plugins.lua → lsp.lua
    ↓
LSP Servers Attach via FileType Autocmds
```

## Detailed Flow

### 1. Python Initialization (`NeovimClient.start()`)

```python
async def start(self):
    # Step 1: Bootstrap LSP servers
    await check_and_install_lsp_servers(...)
    
    # Step 2: Start Neovim
    nvim --headless --listen socket -u configs/init.lua
    
    # Step 3: Connect to socket
    self.nvim = pynvim.attach("socket", path=socket_path)
    
    # Step 4: Wait for config loaded signal
    await self._wait_for_config()  # Waits for vim.g.ide_config_loaded
    
    # Step 5: Send configuration
    await self._send_config_to_nvim()  # Sets _G.otter_config
    
    # Step 6: Initialize LSP (placeholder)
    await self._initialize_lsp()
```

### 2. Neovim Startup (`init.lua`)

```lua
-- Bootstrap lazy.nvim plugin manager
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
-- Clone if not exists...

-- Load plugins (this loads plugins.lua)
require("lazy").setup(plugins)

-- Signal that config is loaded
vim.g.ide_config_loaded = true
```

**ISSUE**: Plugins are loaded **before** `vim.g.ide_config_loaded` is set, so Python sends config **after** plugins have already initialized!

### 3. Plugin Configuration (`plugins.lua`)

```lua
return {
    {
        'neovim/nvim-lspconfig',
        config = function()
            local lsp = require('lsp')
            
            -- Read config from Python
            local lsp_config = _G.otter_config.lsp or default
            local enabled_langs = _G.otter_config.enabled_languages or {}
            
            -- Initialize LSP module
            lsp.init(lsp_config, enabled_langs)
            lsp.setup()  -- Sets up FileType autocmds
        end,
    },
    ...
}
```

**ISSUE**: `_G.otter_config` might not be set yet when this runs!

### 4. LSP Setup (`lsp.lua`)

```lua
function M.setup()
    if M.config.lazy_load == false then
        -- Setup all LSPs immediately
        M.setup_python()
        M.setup_javascript()
        ...
    else
        -- Setup FileType autocmds for lazy loading
        vim.api.nvim_create_autocmd("FileType", {
            pattern = "python",
            callback = function()
                M.setup_python()  -- Calls lspconfig.pyright.setup{}
            end,
        })
    end
end

function M.setup_python()
    local lspconfig = require('lspconfig')
    lspconfig.pyright.setup {
        settings = ...,
        on_init = ...,
    }
end
```

When a Python file is opened:
1. Neovim detects filetype = "python"
2. FileType autocmd fires
3. `M.setup_python()` is called
4. `lspconfig.pyright.setup{}` configures the server
5. LSP client **should** attach to the buffer

## The Race Condition

```
Timeline:
T0: Python starts Neovim
T1: init.lua loads
T2: lazy.setup() runs
T3: plugins.lua config functions run  ◄─ _G.otter_config may not exist!
T4: FileType autocmds are registered
T5: vim.g.ide_config_loaded = true
T6: Python detects loaded flag
T7: Python sends _G.otter_config      ◄─ TOO LATE!
```

## Solutions

### Option 1: Send Config Before Plugins Load (PREFERRED)

Modify init.lua to wait for config before loading plugins:

```lua
-- Wait for config from Python
local timeout = 5000  -- 5 seconds
local start = vim.loop.now()
while not _G.otter_config and (vim.loop.now() - start) < timeout do
    vim.wait(50)
end

-- Now load plugins with config available
require("lazy").setup(plugins)
vim.g.ide_config_loaded = true
```

**Problem**: Circular wait - Python waits for `ide_config_loaded`, Neovim waits for `otter_config`

### Option 2: Defer LSP Setup (CURRENT APPROACH)

Keep current flow but fix LSP attachment:

1. Let plugins load with empty config
2. After Python sends config, explicitly trigger LSP setup
3. Manually attach LSP to already-open buffers

### Option 3: Two-Phase Initialization

1. Phase 1: Load plugins with minimal config
2. Phase 2: After Python sends full config, reinitialize LSP

## Current Status

We're using **Option 2** with LSP readiness polling to ensure:
1. Config is sent from Python
2. Files are opened with correct filetype
3. LSP clients attach (this part is failing)
4. Poll for LSP readiness before running tests

## Debugging Checklist

When LSP isn't attaching:

- [ ] Is `_G.otter_config` set in Neovim? → Check with `:lua vim.print(_G.otter_config)`
- [ ] Are enabled_languages populated? → Check `_G.otter_config.enabled_languages`
- [ ] Is lazy_load true or false? → Check `_G.otter_config.lsp.lazy_load`
- [ ] Are FileType autocmds registered? → Check with `:autocmd FileType python`
- [ ] Is filetype detected? → Check with `:set filetype?` in buffer
- [ ] Does lspconfig have the server? → Check with `:lua vim.print(require('lspconfig').pyright)`
- [ ] Are clients attaching? → Check with `:lua vim.print(vim.lsp.get_active_clients())`

## Next Steps

The fix requires ensuring LSP servers actually attach when FileType autocmds fire. This might need:
1. Explicit buffer attachment after lspconfig.setup()
2. Manual trigger of LSP attachment for existing buffers
3. Or fixing the config timing so it's available when plugins load

