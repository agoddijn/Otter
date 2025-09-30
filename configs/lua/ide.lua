local M = {}

M.get_diagnostics = function(bufnr)
    if bufnr then
        return vim.diagnostic.get(bufnr)
    else
        local all_diags = {}
        for _, buf in ipairs(vim.api.nvim_list_bufs()) do
            if vim.api.nvim_buf_is_loaded(buf) then
                local fname = vim.api.nvim_buf_get_name(buf)
                if fname ~= "" then
                    all_diags[fname] = vim.diagnostic.get(buf)
                end
            end
        end
        return all_diags
    end
end

M.lsp_request_sync = function(bufnr, method, params, timeout_ms)
    timeout_ms = timeout_ms or 5000
    local results = vim.lsp.buf_request_sync(bufnr, method, params, timeout_ms)
    for _, result in pairs(results or {}) do
        if result.result then
            return result.result
        end
    end
    return nil
end

M.is_lsp_ready = function(bufnr)
    local clients = vim.lsp.get_active_clients({ bufnr = bufnr })
    for _, client in ipairs(clients) do
        if client.initialized and client.server_capabilities then
            return true
        end
    end
    return false
end

M.get_lsp_clients = function(bufnr)
    return vim.lsp.get_active_clients({ bufnr = bufnr })
end

M.format_buffer = function(bufnr)
    vim.lsp.buf.format({ bufnr = bufnr, async = false })
end

M.get_hover = function(bufnr, line, col)
    vim.api.nvim_win_set_cursor(0, { line, col })
    local params = vim.lsp.util.make_position_params(0, nil)
    return M.lsp_request_sync(bufnr, 'textDocument/hover', params)
end

M.get_completions = function(bufnr, line, col)
    vim.api.nvim_win_set_cursor(0, { line, col })
    local params = vim.lsp.util.make_position_params(0, nil)
    return M.lsp_request_sync(bufnr, 'textDocument/completion', params)
end

M.execute_code_action = function(bufnr, line, col, action_kind)
    vim.api.nvim_win_set_cursor(0, { line, col })
    local params = vim.lsp.util.make_range_params(0, nil)
    params.context = {
        diagnostics = vim.diagnostic.get(bufnr, { lnum = line - 1 }),
        only = action_kind and { action_kind } or nil
    }
    return M.lsp_request_sync(bufnr, 'textDocument/codeAction', params)
end

return M

