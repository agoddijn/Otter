"""LSP readiness checking for robust test initialization.

This module provides utilities to wait for LSP server readiness using
actual LSP requests instead of arbitrary delays.

The key insight: An LSP server is "ready" when it can successfully respond
to real requests with useful data, not just when it reports "initialized".
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, List


async def wait_for_lsp_ready(
    nvim_client: Any,
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
        buf_num = await nvim_client.open_file(file_path)
        if verbose:
            print(f"Opened {Path(file_path).name} in buffer {buf_num}", file=sys.stderr)
    except Exception as e:
        if verbose:
            print(f"Failed to open file: {e}", file=sys.stderr)
        return False

    while True:
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed >= timeout:
            if verbose:
                print(
                    f"LSP readiness timeout after {timeout}s for {file_path}",
                    file=sys.stderr,
                )
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
                    file_path,
                ),
            )

            if isinstance(result, dict):
                if result.get("error"):
                    if verbose:
                        print(f"LSP check: {result['error']}", file=sys.stderr)
                elif result.get("ready"):
                    if verbose:
                        print(
                            f"LSP initialized for {file_path}: "
                            f"{result.get('ready_count', 0)}/{result.get('clients', 0)} clients",
                            file=sys.stderr,
                        )
                    return True
                elif verbose:
                    clients = result.get("clients", 0)
                    if clients > 0:
                        print(
                            f"LSP clients attached but not initialized yet: {clients} client(s)",
                            file=sys.stderr,
                        )
                    else:
                        print("No LSP clients attached yet to buffer", file=sys.stderr)

        except Exception as e:
            if verbose:
                print(f"LSP check error: {e}", file=sys.stderr)

        await asyncio.sleep(poll_interval)


async def wait_for_lsp_indexed(
    nvim_client: Any,
    file_path: str,
    timeout: float = 30.0,
    poll_interval: float = 0.5,
    verbose: bool = False,
) -> bool:
    """Wait for LSP server to fully index a file using actual LSP requests.

    This is more deterministic than arbitrary delays. We verify that the LSP
    can actually respond with useful data by making real requests:
    1. documentSymbol - returns file structure (classes, functions)
    2. If symbols are empty, try hover on first line to verify semantic analysis

    Args:
        nvim_client: The NeovimClient instance
        file_path: Path to file that should be indexed
        timeout: Maximum time to wait
        poll_interval: Time between attempts
        verbose: Print debug info

    Returns:
        True if LSP is fully ready with non-empty responses
    """
    if not nvim_client.nvim:
        if verbose:
            print(
                "LSP indexing check failed: nvim_client.nvim is None", file=sys.stderr
            )
        return False

    # First ensure LSP client is initialized
    lsp_attached = await wait_for_lsp_ready(
        nvim_client, file_path, timeout=timeout / 2, verbose=verbose
    )

    if not lsp_attached:
        if verbose:
            print(f"LSP not attached for {file_path}", file=sys.stderr)
        return False

    if verbose:
        print("LSP attached, now waiting for indexing...", file=sys.stderr)

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
            # Make actual LSP requests to verify indexing
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
                    
                    -- Strategy: Make multiple request types to verify full readiness
                    local checks = {}
                    
                    -- Check 1: Server capabilities
                    local has_symbols = client.server_capabilities.documentSymbolProvider
                    local has_hover = client.server_capabilities.hoverProvider
                    checks.has_symbols = has_symbols
                    checks.has_hover = has_hover
                    
                    -- Check 2: Request document symbols (proves semantic analysis ready)
                    if has_symbols then
                        local symbol_params = {
                            textDocument = { uri = vim.uri_from_fname(filepath) }
                        }
                        
                        local symbols = nil
                        local symbol_err = nil
                        
                        -- Use buf_request_sync with a short timeout (deterministic!)
                        local responses = vim.lsp.buf_request_sync(
                            bufnr,
                            "textDocument/documentSymbol",
                            symbol_params,
                            2000  -- 2 second timeout per request
                        )
                        
                        if responses then
                            for client_id, resp in pairs(responses) do
                                if resp.result then
                                    symbols = resp.result
                                    break
                                elseif resp.err then
                                    symbol_err = resp.err.message
                                end
                            end
                        end
                        
                        if symbols and #symbols > 0 then
                            checks.symbols_ready = true
                            checks.symbol_count = #symbols
                            -- Success! We got symbols, LSP is fully indexed
                            return {ready = true, checks = checks}
                        elseif symbols then
                            checks.symbols_ready = true
                            checks.symbol_count = 0
                            checks.symbols_empty = true
                        else
                            checks.symbols_ready = false
                            checks.symbol_error = symbol_err or "no response"
                        end
                    end
                    
                    -- Check 3: If no symbols, try hover to verify semantic analysis
                    -- (Some files legitimately have no symbols but LSP should still work)
                    if has_hover then
                        -- Try hover on first line to test semantic analysis
                        local hover_params = {
                            textDocument = { uri = vim.uri_from_fname(filepath) },
                            position = { line = 0, character = 0 }
                        }
                        
                        local hover_responses = vim.lsp.buf_request_sync(
                            bufnr,
                            "textDocument/hover",
                            hover_params,
                            2000
                        )
                        
                        if hover_responses then
                            for client_id, resp in pairs(hover_responses) do
                                if resp.result and resp.result.contents then
                                    checks.hover_ready = true
                                    -- If hover works, consider it ready even without symbols
                                    if not checks.symbols_ready or checks.symbols_empty then
                                        return {ready = true, checks = checks}
                                    end
                                end
                            end
                        end
                    end
                    
                    -- Not ready yet, return status for debugging
                    return {ready = false, checks = checks}
                    """,
                    file_path,
                ),
            )

            if isinstance(result, dict):
                if result.get("ready"):
                    if verbose:
                        checks = result.get("checks", {})
                        symbol_count = checks.get("symbol_count", 0)
                        hover_ready = checks.get("hover_ready", False)
                        print(
                            f"✅ LSP fully indexed {Path(file_path).name}: "
                            f"{symbol_count} symbols, hover={'✓' if hover_ready else '✗'}",
                            file=sys.stderr,
                        )
                    return True
                elif result.get("error"):
                    if verbose:
                        print(f"LSP indexing check: {result['error']}", file=sys.stderr)
                else:
                    if verbose:
                        checks = result.get("checks", {})
                        print(
                            f"LSP not ready yet: symbols={checks.get('symbols_ready', False)}, "
                            f"hover={checks.get('hover_ready', False)}",
                            file=sys.stderr,
                        )

        except Exception as e:
            if verbose:
                print(f"LSP indexing check error: {e}", file=sys.stderr)

        await asyncio.sleep(poll_interval)


async def wait_for_all_lsp_ready(
    nvim_client: Any,
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
        print(
            f"Waiting for LSP readiness for {len(file_paths)} file(s)...",
            file=sys.stderr,
        )

    check_func = wait_for_lsp_indexed if use_indexing_check else wait_for_lsp_ready

    # Process files sequentially to avoid overwhelming LSP
    # (opening many files at once can cause issues)
    for i, path in enumerate(file_paths, 1):
        if verbose:
            print(
                f"[{i}/{len(file_paths)}] Checking {Path(path).name}...",
                file=sys.stderr,
            )

        ready = await check_func(nvim_client, path, timeout, verbose=verbose)

        if not ready:
            if verbose:
                print(f"LSP not ready for {path} after {timeout}s", file=sys.stderr)
            return False

    if verbose:
        print(f"✅ All {len(file_paths)} file(s) ready", file=sys.stderr)

    return True
