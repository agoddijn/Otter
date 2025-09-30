-- Minimal headless Neovim config for LSP integration
vim.opt.swapfile = false
vim.opt.backup = false
vim.opt.writebackup = false
vim.opt.updatetime = 100

-- Add our config directory to the Lua package path
local config_path = vim.fn.fnamemodify(debug.getinfo(1).source:sub(2), ":h")
package.path = package.path .. ";" .. config_path .. "/lua/?.lua"

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

-- Plugin setup
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
