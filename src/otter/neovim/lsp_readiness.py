"""LSP readiness checking for robust test initialization.

This module provides utilities to poll for LSP server readiness instead
of using arbitrary sleep delays.
"""

import asyncio
import sys
from typing import List
from pathlib import Path


async def wait_for_lsp_ready(
    nvim_client,
    file_path: str,
    timeout: float = 30.0,
    poll_interval: float = 0.5,
    verbose: bool = False,
) -> bool:
    """Wait for LSP server to be ready for a specific file.
    
    This checks that:
    1. File is opened in Neovim
    2. LSP client(s) are attached to the buffer
    3. LSP client is initialized
    
    Args:
        nvim_client: The NeovimClient instance
        file_path: Path to a file that should be analyzed by LSP
        timeout: Maximum time to wait in seconds
        poll_interval: Time between polls in seconds
        verbose: Print debug information to stderr
        
    Returns:
        True if LSP is ready, False if timeout reached
    """
    if not nvim_client.nvim:
        if verbose:
            print("LSP check failed: nvim_client.nvim is None", file=sys.stderr)
        return False
    
    start_time = asyncio.get_event_loop().time()
    loop = asyncio.get_event_loop()
    
    # Ensure file is opened in a buffer with correct filetype
    try:
        await nvim_client.open_file(file_path)
        if verbose:
            print(f"Opened file: {file_path}", file=sys.stderr)
        
        # Give Neovim a moment to detect filetype and attach LSP
        await asyncio.sleep(1.0)
        
        # Verify filetype is set and trigger LSP if needed
        await loop.run_in_executor(
            None,
            lambda: nvim_client.nvim.exec_lua(
                """
                local filepath = ...
                local bufnr = vim.fn.bufnr(filepath)
                if bufnr ~= -1 then
                    -- Ensure filetype is detected
                    vim.api.nvim_buf_call(bufnr, function()
                        if vim.bo.filetype == '' then
                            vim.cmd('filetype detect')
                        end
                    end)
                end
                """,
                file_path
            )
        )
        
        # Give LSP a moment to attach after filetype detection
        await asyncio.sleep(0.5)
        
        if verbose:
            # Check what filetype was detected
            ft_result = await loop.run_in_executor(
                None,
                lambda: nvim_client.nvim.exec_lua(
                    """
                    local filepath = ...
                    local bufnr = vim.fn.bufnr(filepath)
                    if bufnr == -1 then
                        return {error = "buffer not found"}
                    end
                    return {filetype = vim.api.nvim_buf_get_option(bufnr, 'filetype')}
                    """,
                    file_path
                )
            )
            if isinstance(ft_result, dict) and ft_result.get('filetype'):
                print(f"Detected filetype: {ft_result['filetype']}", file=sys.stderr)
        
    except Exception as e:
        if verbose:
            print(f"Failed to open file {file_path}: {e}", file=sys.stderr)
        return False
    
    while True:
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed >= timeout:
            if verbose:
                print(f"LSP readiness timeout after {timeout}s for {file_path}", file=sys.stderr)
            return False
        
        try:
            # Check LSP client status using Neovim API
            result = await loop.run_in_executor(
                None,
                lambda: nvim_client.nvim.exec_lua(
                    """
                    local filepath = ...
                    local bufnr = vim.fn.bufnr(filepath)
                    
                    if bufnr == -1 then
                        return {error = "buffer not found"}
                    end
                    
                    -- Get attached LSP clients
                    local clients = vim.lsp.get_active_clients({bufnr = bufnr})
                    
                    if #clients == 0 then
                        return {clients = 0, ready = false}
                    end
                    
                    -- Check if any client is initialized
                    local ready_count = 0
                    for _, client in ipairs(clients) do
                        if client.initialized then
                            ready_count = ready_count + 1
                        end
                    end
                    
                    return {
                        clients = #clients,
                        ready = ready_count > 0,
                        ready_count = ready_count
                    }
                    """,
                    file_path
                )
            )
            
            if isinstance(result, dict):
                if result.get("error"):
                    if verbose:
                        print(f"LSP check: {result['error']}", file=sys.stderr)
                elif result.get("ready"):
                    if verbose:
                        print(
                            f"LSP ready for {file_path}: "
                            f"{result.get('ready_count', 0)}/{result.get('clients', 0)} clients initialized",
                            file=sys.stderr
                        )
                    # Give LSP a moment to settle after initialization
                    await asyncio.sleep(0.5)
                    return True
                elif verbose:
                    clients = result.get("clients", 0)
                    if clients > 0:
                        print(
                            f"LSP clients attached but not initialized yet: {clients} client(s)",
                            file=sys.stderr
                        )
                    else:
                        print("No LSP clients attached yet to buffer", file=sys.stderr)
                    
        except Exception as e:
            if verbose:
                print(f"LSP check error: {e}", file=sys.stderr)
        
        await asyncio.sleep(poll_interval)


async def wait_for_lsp_indexed(
    nvim_client,
    file_path: str,
    timeout: float = 30.0,
    poll_interval: float = 0.5,
    verbose: bool = False,
) -> bool:
    """Wait for LSP server to fully index a file.
    
    This checks that the LSP can provide document symbols, which indicates
    the file has been parsed and indexed. This is more thorough than just
    checking if LSP is attached.
    
    Args:
        nvim_client: The NeovimClient instance
        file_path: Path to a file that should be indexed
        timeout: Maximum time to wait in seconds
        poll_interval: Time between polls in seconds
        verbose: Print debug information to stderr
        
    Returns:
        True if file is indexed, False if timeout reached
    """
    if not nvim_client.nvim:
        if verbose:
            print("LSP indexed check failed: nvim_client.nvim is None", file=sys.stderr)
        return False
    
    # First wait for LSP to be ready (initialized)
    if not await wait_for_lsp_ready(nvim_client, file_path, timeout, poll_interval, verbose):
        if verbose:
            print(f"LSP not ready for {file_path}, cannot check indexing", file=sys.stderr)
        return False
    
    if verbose:
        print(f"LSP ready, now checking if {file_path} is indexed...", file=sys.stderr)
    
    start_time = asyncio.get_event_loop().time()
    loop = asyncio.get_event_loop()
    
    while True:
        elapsed = asyncio.get_event_loop().time() - start_time
        remaining_time = timeout - elapsed
        
        if remaining_time <= 0:
            if verbose:
                print(f"LSP indexing timeout for {file_path}", file=sys.stderr)
            return False
        
        try:
            # Try to get document symbols - this indicates the file is indexed
            result = await loop.run_in_executor(
                None,
                lambda: nvim_client.nvim.exec_lua(
                    """
                    local filepath = ...
                    local bufnr = vim.fn.bufnr(filepath)
                    
                    if bufnr == -1 then
                        return {error = "buffer not found"}
                    end
                    
                    local clients = vim.lsp.get_active_clients({bufnr = bufnr})
                    if #clients == 0 then
                        return {error = "no clients"}
                    end
                    
                    -- Get the first initialized client
                    local client = nil
                    for _, c in ipairs(clients) do
                        if c.initialized then
                            client = c
                            break
                        end
                    end
                    
                    if not client then
                        return {error = "no initialized clients"}
                    end
                    
                    -- Check if client supports documentSymbol
                    if not client.server_capabilities.documentSymbolProvider then
                        -- Some servers don't provide symbols, consider it ready anyway
                        return {ready = true, no_symbols = true}
                    end
                    
                    -- Request document symbols with a timeout
                    local params = {
                        textDocument = {
                            uri = vim.uri_from_fname(filepath)
                        }
                    }
                    
                    local success = false
                    local response = nil
                    local err_msg = nil
                    
                    client.request(
                        "textDocument/documentSymbol",
                        params,
                        function(err, result)
                            if err then
                                err_msg = err.message or "unknown error"
                            else
                                response = result
                                success = true
                            end
                        end,
                        bufnr
                    )
                    
                    -- Wait for response (up to 2 seconds)
                    local start = vim.loop.now()
                    while (vim.loop.now() - start) < 2000 do
                        if success or err_msg then
                            break
                        end
                        vim.wait(50, function() return success or err_msg ~= nil end)
                    end
                    
                    if success and response then
                        return {ready = true, symbol_count = #response}
                    elseif err_msg then
                        return {error = err_msg}
                    else
                        return {error = "timeout waiting for symbols"}
                    end
                    """,
                    file_path
                )
            )
            
            if isinstance(result, dict):
                if result.get("ready"):
                    if verbose:
                        if result.get("no_symbols"):
                            print(f"{file_path}: LSP doesn't provide symbols (considered ready)", file=sys.stderr)
                        else:
                            print(f"{file_path}: Indexed with {result.get('symbol_count', 0)} symbols", file=sys.stderr)
                    return True
                elif result.get("error"):
                    if verbose:
                        print(f"{file_path}: LSP check error: {result['error']}", file=sys.stderr)
                    # Continue polling - some errors are transient
                
        except Exception as e:
            if verbose:
                print(f"LSP indexing check exception: {e}", file=sys.stderr)
        
        await asyncio.sleep(poll_interval)


async def wait_for_all_lsp_ready(
    nvim_client,
    file_paths: List[str],
    timeout: float = 30.0,
    use_indexing_check: bool = True,
    verbose: bool = False,
) -> bool:
    """Wait for LSP to be ready for multiple files.
    
    Opens all files and waits for LSP to be ready. Can optionally wait
    for full indexing (document symbols available).
    
    Args:
        nvim_client: The NeovimClient instance
        file_paths: List of file paths to check
        timeout: Maximum time to wait in seconds (per file)
        use_indexing_check: If True, wait for full indexing; if False, just wait for LSP attachment
        verbose: Print debug information to stderr
        
    Returns:
        True if all files are ready, False if any timeout
    """
    if not file_paths:
        return True
    
    if verbose:
        print(f"Waiting for LSP readiness for {len(file_paths)} file(s)...", file=sys.stderr)
    
    check_func = wait_for_lsp_indexed if use_indexing_check else wait_for_lsp_ready
    
    # Process files sequentially to avoid overwhelming LSP
    # (opening many files at once can cause issues)
    for i, path in enumerate(file_paths, 1):
        if verbose:
            print(f"[{i}/{len(file_paths)}] Checking {Path(path).name}...", file=sys.stderr)
        
        ready = await check_func(nvim_client, path, timeout, verbose=verbose)
        
        if not ready:
            if verbose:
                print(f"LSP not ready for {path} after {timeout}s", file=sys.stderr)
            return False
    
    if verbose:
        print(f"✅ All {len(file_paths)} file(s) ready", file=sys.stderr)
    
    return True

