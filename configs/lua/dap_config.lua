-- DAP (Debug Adapter Protocol) Configuration
-- Language-agnostic debugging via Neovim's DAP client
--
-- Similar to how we use Neovim's LSP client for language servers,
-- we use Neovim's DAP client for debug adapters.
--
-- This provides debugging for multiple languages without reimplementing
-- the DAP protocol in Python.

local M = {}

function M.setup()
    local dap = require('dap')
    
    -- ========================================================================
    -- Python Configuration (debugpy)
    -- ========================================================================
    
    dap.adapters.python = function(callback, config)
        if config.request == 'attach' then
            ---@diagnostic disable-next-line: undefined-field
            local port = (config.connect or config).port
            ---@diagnostic disable-next-line: undefined-field
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
            callback({
                type = 'executable',
                command = 'python',
                args = { '-m', 'debugpy.adapter' },
                options = {
                    source_filetype = 'python',
                },
            })
        end
    end
    
    dap.configurations.python = {
        {
            type = 'python',
            request = 'launch',
            name = 'Launch file',
            program = '${file}',
            pythonPath = function()
                -- Use virtual environment if available
                local cwd = vim.fn.getcwd()
                if vim.fn.executable(cwd .. '/.venv/bin/python') == 1 then
                    return cwd .. '/.venv/bin/python'
                elseif vim.fn.executable(cwd .. '/venv/bin/python') == 1 then
                    return cwd .. '/venv/bin/python'
                else
                    return 'python'
                end
            end,
        },
        {
            type = 'python',
            request = 'launch',
            name = 'Launch module',
            module = '${input:module}',
            pythonPath = function()
                local cwd = vim.fn.getcwd()
                if vim.fn.executable(cwd .. '/.venv/bin/python') == 1 then
                    return cwd .. '/.venv/bin/python'
                elseif vim.fn.executable(cwd .. '/venv/bin/python') == 1 then
                    return cwd .. '/venv/bin/python'
                else
                    return 'python'
                end
            end,
        },
        {
            type = 'python',
            request = 'launch',
            name = 'pytest: current file',
            module = 'pytest',
            args = { '${file}', '-v' },
            pythonPath = function()
                local cwd = vim.fn.getcwd()
                if vim.fn.executable(cwd .. '/.venv/bin/python') == 1 then
                    return cwd .. '/.venv/bin/python'
                elseif vim.fn.executable(cwd .. '/venv/bin/python') == 1 then
                    return cwd .. '/venv/bin/python'
                else
                    return 'python'
                end
            end,
            console = 'integratedTerminal',
        },
    }
    
    -- ========================================================================
    -- JavaScript/TypeScript Configuration (node-debug2 or vscode-js-debug)
    -- ========================================================================
    
    dap.adapters.node2 = {
        type = 'executable',
        command = 'node',
        args = {
            vim.fn.stdpath('data') .. '/mason/packages/node-debug2-adapter/out/src/nodeDebug.js'
        },
    }
    
    dap.configurations.javascript = {
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
    
    dap.configurations.typescript = dap.configurations.javascript
    
    -- ========================================================================
    -- Rust Configuration (lldb-vscode or codelldb)
    -- ========================================================================
    
    dap.adapters.lldb = {
        type = 'executable',
        command = 'lldb-vscode', -- or 'codelldb'
        name = 'lldb'
    }
    
    dap.configurations.rust = {
        {
            type = 'lldb',
            request = 'launch',
            name = 'Launch',
            program = function()
                return vim.fn.input('Path to executable: ', vim.fn.getcwd() .. '/target/debug/', 'file')
            end,
            cwd = '${workspaceFolder}',
            stopOnEntry = false,
            args = {},
        },
    }
    
    -- ========================================================================
    -- Go Configuration (delve)
    -- ========================================================================
    
    dap.adapters.go = {
        type = 'executable',
        command = 'dlv',
        args = { 'dap', '-l', '127.0.0.1:38697' }
    }
    
    dap.configurations.go = {
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
    
    -- ========================================================================
    -- DAP Signs (visual indicators in editor)
    -- ========================================================================
    
    vim.fn.sign_define('DapBreakpoint', { text='🔴', texthl='', linehl='', numhl='' })
    vim.fn.sign_define('DapBreakpointCondition', { text='🟠', texthl='', linehl='', numhl='' })
    vim.fn.sign_define('DapLogPoint', { text='📝', texthl='', linehl='', numhl='' })
    vim.fn.sign_define('DapStopped', { text='▶️', texthl='', linehl='', numhl='' })
    vim.fn.sign_define('DapBreakpointRejected', { text='❌', texthl='', linehl='', numhl='' })
end

return M

