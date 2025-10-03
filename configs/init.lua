-- Minimal headless Neovim config for LSP integration
vim.opt.swapfile = false
vim.opt.backup = false
vim.opt.writebackup = false
vim.opt.updatetime = 100

-- Add our config directory to the Lua package path
local config_path = vim.fn.fnamemodify(debug.getinfo(1).source:sub(2), ":h")
package.path = package.path .. ";" .. config_path .. "/lua/?.lua"

-- CRITICAL: Load runtime config BEFORE plugins
-- This eliminates race conditions - config is guaranteed to exist
local runtime_config_path = config_path .. "/runtime_config.lua"
local runtime_config_ok, err = pcall(dofile, runtime_config_path)
if not runtime_config_ok then
    print("Warning: Failed to load runtime_config.lua: " .. tostring(err))
    print("LSP features may not work correctly")
    -- Create empty config so plugins don't error
    _G.otter_runtime_config = {
        enabled_languages = {},
        lsp = { enabled = false, servers = {} },
        test_mode = false,
    }
end

-- Bootstrap lazy.nvim
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
    vim.fn.system({
        "git",
        "clone",
        "--filter=blob:none",
        "https://github.com/folke/lazy.nvim.git",
        "--branch=stable",
        lazypath,
    })
end
vim.opt.rtp:prepend(lazypath)

-- Plugin setup (runtime_config is now available)
local plugins_ok, plugins = pcall(require, "plugins")
if plugins_ok then
    require("lazy").setup(plugins)
else
    print("Failed to load plugins: " .. tostring(plugins))
end

-- Signal that configuration is loaded
vim.g.ide_config_loaded = true

-- Load IDE API and expose globally
local ide_ok, ide = pcall(require, "ide")
if ide_ok then
    _G.ide_api = ide
end
