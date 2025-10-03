-- Simplified LSP configuration
-- This module sets up LSP servers based on runtime_config.lua
-- No manual FileType autocmds needed - lspconfig handles everything!

local M = {}

-- Get runtime config (guaranteed to exist thanks to init.lua)
local function get_config()
    return _G.otter_runtime_config or {
        enabled_languages = {},
        lsp = { enabled = false, servers = {} },
        test_mode = false,
    }
end

-- Helper to resolve Python path
local function get_python_path(server_config)
    -- Use configured path if provided
    if server_config.python_path and vim.fn.executable(server_config.python_path) == 1 then
        return server_config.python_path
    end
    
    -- Auto-detect venv
    local cwd = vim.fn.getcwd()
    local venv_patterns = { '/.venv/', '/venv/', '/env/', '/.env/' }
    for _, pattern in ipairs(venv_patterns) do
        local python_path = cwd .. pattern .. 'bin/python'
        if vim.fn.executable(python_path) == 1 then
            return python_path
        end
    end
    
    -- Fallback to system python
    return 'python'
end

-- Setup Python LSP
function M.setup_python(server_config)
    local lspconfig = require('lspconfig')
    local server = server_config.server or 'pyright'
    
    if server == 'pyright' and vim.fn.executable('pyright-langserver') == 1 then
        lspconfig.pyright.setup {
            settings = server_config.settings or {
                python = {
                    analysis = {
                        autoSearchPaths = true,
                        useLibraryCodeForTypes = true,
                        diagnosticMode = "workspace",
                        typeCheckingMode = "basic",
                    }
                }
            },
            on_init = function(client)
                local python_path = get_python_path(server_config)
                if python_path ~= 'python' then
                    client.config.settings.python.pythonPath = python_path
                end
            end,
        }
    elseif server == 'pylsp' and vim.fn.executable('pylsp') == 1 then
        lspconfig.pylsp.setup {
            settings = server_config.settings or {}
        }
    elseif server == 'ruff_lsp' and vim.fn.executable('ruff-lsp') == 1 then
        lspconfig.ruff_lsp.setup {
            settings = server_config.settings or {}
        }
    end
end

-- Setup JavaScript/TypeScript LSP
function M.setup_javascript(server_config)
    local lspconfig = require('lspconfig')
    
    if vim.fn.executable('typescript-language-server') == 1 then
        lspconfig.tsserver.setup {
            settings = server_config.settings or {}
        }
    end
end

-- Setup Rust LSP
function M.setup_rust(server_config)
    local lspconfig = require('lspconfig')
    
    if vim.fn.executable('rust-analyzer') == 1 then
        lspconfig.rust_analyzer.setup {
            settings = server_config.settings or {
                ['rust-analyzer'] = {}
            }
        }
    end
end

-- Setup Go LSP
function M.setup_go(server_config)
    local lspconfig = require('lspconfig')
    
    if vim.fn.executable('gopls') == 1 then
        lspconfig.gopls.setup {
            settings = server_config.settings or {}
        }
    end
end

-- Main setup function
function M.setup()
    local config = get_config()
    
    -- Don't setup if LSP is disabled
    if not config.lsp.enabled then
        return
    end
    
    -- Setup each enabled language
    -- In test mode or production, we setup immediately
    -- lspconfig handles FileType detection and attachment automatically!
    for lang, enabled in pairs(config.enabled_languages) do
        if enabled and config.lsp.servers[lang] then
            local server_config = config.lsp.servers[lang]
            
            if server_config.enabled ~= false then
                if lang == 'python' then
                    M.setup_python(server_config)
                elseif lang == 'javascript' or lang == 'typescript' then
                    M.setup_javascript(server_config)
                elseif lang == 'rust' then
                    M.setup_rust(server_config)
                elseif lang == 'go' then
                    M.setup_go(server_config)
                end
            end
        end
    end
end

return M
