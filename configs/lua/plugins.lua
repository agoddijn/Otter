return {
    -- LSP Configuration
    {
        'neovim/nvim-lspconfig',
        config = function()
            require('lsp').setup()
        end,
    },
    
    -- TreeSitter for language-agnostic parsing
    {
        'nvim-treesitter/nvim-treesitter',
        build = ':TSUpdate',
        config = function()
            require('nvim-treesitter.configs').setup({
                -- Install parsers for languages we support
                ensure_installed = {
                    "python",
                    "javascript",
                    "typescript",
                    "tsx",
                    "rust",
                    "go",
                    "lua",
                    "json",
                    "yaml",
                    "markdown",
                    "bash",
                },
                
                -- Auto-install missing parsers when entering buffer
                auto_install = true,
                
                -- Enable syntax highlighting
                highlight = {
                    enable = true,
                    additional_vim_regex_highlighting = false,
                },
                
                -- Enable incremental selection
                incremental_selection = {
                    enable = true,
                },
                
                -- Enable indentation
                indent = {
                    enable = true,
                },
            })
        end,
    },
}
