local M = {}

function M.setup()
    local lspconfig = require('lspconfig')

    lspconfig.pyright.setup {
        settings = {
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
            local path = client.workspace_folders and client.workspace_folders[1] and client.workspace_folders[1].name or nil
            local venv_path = nil
            if path then
                local venv_patterns = { '/venv/', '/.venv/', '/env/', '/.env/' }
                for _, pattern in ipairs(venv_patterns) do
                    local test_path = path .. pattern
                    if vim.fn.isdirectory(test_path) == 1 then
                        venv_path = test_path
                        break
                    end
                end
            end
            if venv_path then
                local python_path = venv_path .. 'bin/python'
                if vim.fn.executable(python_path) == 1 then
                    client.config.settings.python.pythonPath = python_path
                end
            end
        end,
    }

    if vim.fn.executable('ruff-lsp') == 1 then
        lspconfig.ruff_lsp.setup {}
    end
end

return M
