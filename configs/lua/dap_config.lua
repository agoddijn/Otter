-- Simplified DAP configuration
-- This module sets up DAP adapters and configurations based on runtime_config.lua
-- Language-agnostic approach matching lsp.lua

local M = {}

-- Get runtime config (guaranteed to exist thanks to init.lua)
local function get_config()
    return _G.otter_runtime_config or {
        enabled_languages = {},
        dap = { enabled = false, adapters = {} },
    }
end

-- Helper to resolve Python path from adapter config
-- ⚠️  CRITICAL: This should ONLY use the python_path from adapter_config
-- Do NOT do auto-detection here - that's RuntimeResolver's job!
local function get_python_path(adapter_config)
    if adapter_config.python_path and vim.fn.executable(adapter_config.python_path) == 1 then
        return adapter_config.python_path
    end
    
    -- If no python_path configured, fall back to system Python
    -- (This should rarely happen - RuntimeResolver should always provide a path)
    return 'python'
end

-- Setup Python DAP
function M.setup_python(adapter_config)
    local dap = require('dap')
    
    -- Setup adapter
    dap.adapters.python = function(callback, config)
        if config.request == 'attach' then
            local port = (config.connect or config).port
            local host = (config.connect or config).host or '127.0.0.1'
            callback({
                type = 'server',
                port = assert(port, '`connect.port` is required for attach'),
                host = host,
                options = {
                    source_filetype = 'python',
                },
            })
        else
            -- 🎯 Use python from CONFIG, not from adapter_config!
            -- The config.pythonPath is set per-session by RuntimeResolver
            local python_path = config.pythonPath or get_python_path(adapter_config)
            callback({
                type = 'executable',
                command = python_path,
                args = { '-m', 'debugpy.adapter' },
                options = {
                    source_filetype = 'python',
                },
            })
        end
    end
    
    -- Setup configurations
    local python_path = get_python_path(adapter_config)
    dap.configurations.python = adapter_config.configurations or {
        {
            type = 'python',
            request = 'launch',
            name = 'Launch file',
            program = '${file}',
            pythonPath = python_path,
        },
    }
end

-- Setup JavaScript/TypeScript DAP
function M.setup_javascript(adapter_config)
    local dap = require('dap')
    
    dap.adapters.node2 = {
        type = 'executable',
        command = 'node',
        args = {
            vim.fn.stdpath('data') .. '/mason/packages/node-debug2-adapter/out/src/nodeDebug.js'
        },
    }
    
    local default_config = {
        {
            type = 'node2',
            request = 'launch',
            name = 'Launch file',
            program = '${file}',
            cwd = vim.fn.getcwd(),
            sourceMaps = true,
            protocol = 'inspector',
            console = 'integratedTerminal',
        },
    }
    
    dap.configurations.javascript = adapter_config.configurations or default_config
    dap.configurations.typescript = adapter_config.configurations or default_config
end

-- Setup Rust DAP
function M.setup_rust(adapter_config)
    local dap = require('dap')
    
    local adapter = adapter_config.adapter or 'lldb'
    
    dap.adapters.lldb = {
        type = 'executable',
        command = adapter == 'codelldb' and 'codelldb' or 'lldb-vscode',
        name = 'lldb'
    }
    
    dap.configurations.rust = adapter_config.configurations or {
        {
            type = 'lldb',
            request = 'launch',
            name = 'Launch',
            program = function()
                return vim.fn.input('Path to executable: ', vim.fn.getcwd() .. '/target/debug/', 'file')
            end,
            cwd = '${workspaceFolder}',
            stopOnEntry = false,
        },
    }
end

-- Setup Go DAP
function M.setup_go(adapter_config)
    local dap = require('dap')
    
    dap.adapters.go = {
        type = 'executable',
        command = 'dlv',
        args = { 'dap', '-l', '127.0.0.1:38697' }
    }
    
    dap.configurations.go = adapter_config.configurations or {
        {
            type = 'go',
            name = 'Debug',
            request = 'launch',
            program = '${file}',
        },
        {
            type = 'go',
            name = 'Debug test',
            request = 'launch',
            mode = 'test',
            program = '${file}',
        },
    }
end

-- Main setup function (language-agnostic!)
function M.setup()
    local config = get_config()
    local dap = require('dap')
    
    -- Setup visual indicators
    vim.fn.sign_define('DapBreakpoint', { text='🔴', texthl='', linehl='', numhl='' })
    vim.fn.sign_define('DapBreakpointCondition', { text='🟠', texthl='', linehl='', numhl='' })
    vim.fn.sign_define('DapLogPoint', { text='📝', texthl='', linehl='', numhl='' })
    vim.fn.sign_define('DapStopped', { text='▶️', texthl='', linehl='', numhl='' })
    vim.fn.sign_define('DapBreakpointRejected', { text='❌', texthl='', linehl='', numhl='' })
    
    -- Don't setup if DAP is disabled
    if not config.dap.enabled then
        return
    end
    
    -- Setup each enabled language
    -- We setup all enabled languages immediately since DAP is explicitly triggered
    for lang, enabled in pairs(config.enabled_languages) do
        if enabled and config.dap.adapters[lang] then
            local adapter_config = config.dap.adapters[lang]
            
            if adapter_config.enabled ~= false then
                if lang == 'python' then
                    M.setup_python(adapter_config)
                elseif lang == 'javascript' or lang == 'typescript' then
                    M.setup_javascript(adapter_config)
                elseif lang == 'rust' then
                    M.setup_rust(adapter_config)
                elseif lang == 'go' then
                    M.setup_go(adapter_config)
                end
            end
        end
    end
end

return M
