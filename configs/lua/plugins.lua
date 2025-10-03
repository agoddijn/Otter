-- Plugin configuration (simplified)
-- Config is loaded from runtime_config.lua before plugins load

return {
    -- LSP Configuration
    {
        'neovim/nvim-lspconfig',
        config = function()
            -- Simply call setup - config is already loaded!
            require('lsp').setup()
        end,
    },
    
    -- TreeSitter for language-agnostic parsing
    {
        'nvim-treesitter/nvim-treesitter',
        build = ':TSUpdate',
        config = function()
            local config = _G.otter_runtime_config or {}
            
            -- Install parsers for enabled languages
            local ensure_installed = {}
            for lang, _ in pairs(config.enabled_languages or {}) do
                table.insert(ensure_installed, lang)
            end
            
            -- Add common utilities
            vim.list_extend(ensure_installed, {"lua", "json", "yaml", "markdown"})
            
            require('nvim-treesitter.configs').setup({
                ensure_installed = ensure_installed,
                auto_install = true,
                
                highlight = {
                    enable = true,
                    additional_vim_regex_highlighting = false,
                },
                
                incremental_selection = {
                    enable = true,
                },
                
                indent = {
                    enable = true,
                },
            })
        end,
    },
    
    -- DAP (Debug Adapter Protocol) for language-agnostic debugging
    {
        'mfussenegger/nvim-dap',
        config = function()
            -- DAP configuration remains as-is for now
            -- Can be simplified later
            require('dap_config').setup()
        end,
    },
}
