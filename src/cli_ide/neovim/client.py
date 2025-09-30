from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pynvim  # type: ignore


class NeovimClient:
    """Async wrapper over a headless Neovim instance.

    Manages a persistent Neovim instance with LSP servers for code intelligence.
    """

    def __init__(self, project_path: str, socket_path: Optional[str] = None) -> None:
        """Initialize the Neovim client.

        Args:
            project_path: Root path of the project to analyze
            socket_path: Optional custom socket path for Neovim communication
        """
        self.project_path = Path(project_path).resolve()
        self.socket_path = socket_path or self._create_socket_path()
        self.nvim: Optional[pynvim.Nvim] = None
        self._process: Optional[asyncio.subprocess.Process] = None
        self._buffers: Dict[str, int] = {}  # filepath -> buffer number
        self._lsp_clients: Dict[str, Any] = {}  # filetype -> LSP client info
        self._started = False

    def _create_socket_path(self) -> str:
        """Create a unique socket path for this Neovim instance."""
        temp_dir = tempfile.gettempdir()
        return os.path.join(temp_dir, f"nvim_ide_{os.getpid()}.sock")

    async def start(self) -> None:
        """Start the headless Neovim instance."""
        if self._started:
            return

        # Get the config directory (configs/ in project root)
        config_dir = Path(__file__).parent.parent.parent.parent / "configs"
        init_lua = config_dir / "init.lua"

        if not init_lua.exists():
            raise FileNotFoundError(f"Neovim config not found: {init_lua}")

        # Start headless Neovim with our config
        cmd = [
            "nvim",
            "--headless",
            "--listen",
            self.socket_path,
            "-u",
            str(init_lua),
            "--cmd",
            "set noswapfile",
            "--cmd",
            f"cd {self.project_path}",  # Set working directory to project
        ]

        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Give Neovim time to start and create the socket
        # Wait for socket file to exist
        socket_timeout = 3.0
        socket_start = asyncio.get_event_loop().time()
        while not os.path.exists(self.socket_path):
            if asyncio.get_event_loop().time() - socket_start > socket_timeout:
                await self.stop()
                raise RuntimeError(f"Socket file not created: {self.socket_path}")
            await asyncio.sleep(0.1)

        # Give it a bit more time to be ready
        await asyncio.sleep(0.2)

        # Connect to the Neovim instance (run in executor to avoid event loop conflicts)
        loop = asyncio.get_event_loop()
        try:
            self.nvim = await asyncio.wait_for(
                loop.run_in_executor(
                    None, lambda: pynvim.attach("socket", path=self.socket_path)
                ),
                timeout=5.0,
            )
        except asyncio.TimeoutError:
            await self.stop()
            raise RuntimeError(
                f"Timeout connecting to Neovim socket: {self.socket_path}"
            )
        except Exception as e:
            await self.stop()
            raise RuntimeError(f"Failed to connect to Neovim: {e}")

        # Wait for config to load
        await self._wait_for_config()

        # Initialize LSP servers for the project
        await self._initialize_lsp()

        self._started = True

    async def _wait_for_config(self, timeout: float = 5.0) -> None:
        """Wait for Neovim config to finish loading."""
        loop = asyncio.get_event_loop()
        start_time = loop.time()

        while True:
            try:
                if not self.nvim:
                    raise RuntimeError("Neovim not connected")
                # Run eval in executor to avoid blocking, with timeout
                loaded = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: self.nvim.eval("get(g:, 'ide_config_loaded', 0)")
                        if self.nvim
                        else 0,
                    ),
                    timeout=1.0,  # 1 second timeout per check
                )
                if loaded:
                    break
            except asyncio.TimeoutError:
                # If individual check times out, continue trying
                pass
            except Exception:
                pass

            if loop.time() - start_time > timeout:
                # For now, just log and continue - config might not set the flag
                # This makes it work even if lazy.nvim isn't fully loaded
                break

            await asyncio.sleep(0.1)

    async def _initialize_lsp(self) -> None:
        """Initialize LSP servers for the project."""
        # This will be called by our Lua config
        # For now, just ensure LSP is ready
        try:
            # Check if LSP is available (run in executor with timeout)
            if self.nvim:
                loop = asyncio.get_event_loop()
                has_lsp = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: self.nvim.eval("vim.fn.exists('*vim.lsp.get_clients')")
                        if self.nvim
                        else 0,
                    ),
                    timeout=2.0,
                )
                if not has_lsp:
                    # LSP not available in this Neovim version
                    pass
        except asyncio.TimeoutError:
            # LSP check timed out, continue anyway
            pass
        except Exception:
            # If LSP check fails, continue anyway
            pass

    async def stop(self) -> None:
        """Stop the Neovim instance and clean up."""
        if self.nvim:
            try:
                # Run quit command in executor
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, lambda: self.nvim.command("qa!") if self.nvim else None
                )
            except Exception:
                pass

            # Close the Neovim connection
            try:
                if hasattr(self.nvim, "close"):
                    await loop.run_in_executor(None, self.nvim.close)
            except Exception:
                pass

            self.nvim = None

        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
            except Exception:
                pass
            self._process = None

        # Clean up socket file
        if self.socket_path and os.path.exists(self.socket_path):
            try:
                os.remove(self.socket_path)
            except OSError:
                pass

        self._started = False
        self._buffers.clear()

    async def open_file(self, filepath: str) -> int:
        """Open a file in a Neovim buffer.

        Args:
            filepath: Path to the file (relative to project root or absolute)

        Returns:
            Buffer number
        """
        if not self._started:
            raise RuntimeError("Neovim not started. Call start() first.")

        # Resolve path
        if os.path.isabs(filepath):
            file_path = Path(filepath)
        else:
            file_path = self.project_path / filepath

        file_path = file_path.resolve()
        filepath_str = str(file_path)

        # Check if file exists
        if not file_path.exists():
            raise RuntimeError(f"Failed to open file {filepath}: File not found")

        # Check if already open
        if filepath_str in self._buffers:
            return self._buffers[filepath_str]

        # Open the file
        try:
            if not self.nvim:
                raise RuntimeError("Neovim not connected")

            # Run file opening in executor
            loop = asyncio.get_event_loop()

            def _open_file():
                if not self.nvim:
                    raise RuntimeError("Neovim not connected")
                self.nvim.command(f"edit {filepath_str}")
                return self.nvim.current.buffer.number

            buf_num = await loop.run_in_executor(None, _open_file)
            self._buffers[filepath_str] = buf_num

            # Give LSP time to attach
            await asyncio.sleep(0.1)

            return buf_num
        except Exception as e:
            raise RuntimeError(f"Failed to open file {filepath}: {e}")

    async def read_buffer(
        self, filepath: str, line_range: Optional[Tuple[int, int]] = None
    ) -> List[str]:
        """Read lines from a buffer.

        Args:
            filepath: Path to the file
            line_range: Optional (start, end) line range (1-indexed, inclusive)

        Returns:
            List of lines from the buffer
        """
        buf_num = await self.open_file(filepath)

        if not self.nvim:
            raise RuntimeError("Neovim not connected")

        # Get buffer contents in executor
        loop = asyncio.get_event_loop()

        def _read_buffer():
            if not self.nvim:
                raise RuntimeError("Neovim not connected")

            # Get the buffer
            buf = None
            for b in self.nvim.buffers:
                if b.number == buf_num:
                    buf = b
                    break

            if not buf:
                raise RuntimeError(f"Buffer {buf_num} not found")

            # Get lines
            if line_range:
                start, end = line_range
                # Neovim uses 0-indexed lines
                return buf[start - 1 : end]
            else:
                return buf[:]

        lines = await loop.run_in_executor(None, _read_buffer)
        return lines

    async def execute_lua(self, lua_code: str, *args: Any) -> Any:
        """Execute Lua code in Neovim.

        Args:
            lua_code: Lua code to execute
            *args: Arguments to pass to the Lua code (accessed via ... in Lua)

        Returns:
            Result from Lua execution
        """
        if not self._started:
            raise RuntimeError("Neovim not started. Call start() first.")

        if not self.nvim:
            raise RuntimeError("Neovim not connected")

        # Run Lua execution in executor
        # Convert args tuple to list (pynvim expects a list)
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: self.nvim.exec_lua(lua_code, list(args)) if self.nvim else None,
            )
            return result
        except Exception as e:
            raise RuntimeError(f"Lua execution failed: {e}")

    async def get_diagnostics(self, filepath: str) -> List[Dict[str, Any]]:
        """Get LSP diagnostics for a file.

        Args:
            filepath: Path to the file

        Returns:
            List of diagnostic dictionaries
        """
        buf_num = await self.open_file(filepath)

        lua_code = f"""
        local bufnr = {buf_num}
        local diagnostics = vim.diagnostic.get(bufnr)
        return diagnostics
        """

        try:
            diagnostics = await self.execute_lua(lua_code)
            return diagnostics or []
        except Exception:
            # Diagnostics not available
            return []

    async def lsp_definition(
        self, filepath: str, line: int, column: int
    ) -> Optional[List[Dict[str, Any]]]:
        """Get LSP definition for a symbol at a position.

        Args:
            filepath: Path to the file
            line: Line number (1-indexed)
            column: Column number (0-indexed)

        Returns:
            List of definition locations, or None if not found
        """
        buf_num = await self.open_file(filepath)

        # Wait for LSP to attach and be ready
        await asyncio.sleep(0.5)

        # Use pynvim to call Lua helper (LSP is Lua-native in Neovim)
        # We still need Lua because vim.lsp.* is a Lua API, not exposed via pynvim
        try:
            result = await self._lsp_request(
                buf_num, "textDocument/definition", line - 1, column
            )
            return result if result else None
        except Exception:
            return None

    async def lsp_references(
        self, filepath: str, line: int, column: int, include_declaration: bool = True
    ) -> Optional[List[Dict[str, Any]]]:
        """Get LSP references for a symbol at a position.

        Args:
            filepath: Path to the file
            line: Line number (1-indexed)
            column: Column number (0-indexed)
            include_declaration: Whether to include the declaration in results

        Returns:
            List of reference locations, or None if not found
        """
        buf_num = await self.open_file(filepath)

        # Wait for LSP to attach and be ready
        await asyncio.sleep(0.5)

        try:
            # textDocument/references needs a special context parameter
            result = await self._lsp_request_with_context(
                buf_num,
                "textDocument/references",
                line - 1,
                column,
                include_declaration,
            )
            return result if result else None
        except Exception:
            return None

    async def lsp_document_symbols(
        self, filepath: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get document symbols (outline) for a file.

        Args:
            filepath: Path to the file

        Returns:
            List of document symbols with hierarchy, or None if not found
        """
        buf_num = await self.open_file(filepath)

        # Wait for LSP to attach and be ready
        await asyncio.sleep(0.5)

        lua_code = f"""
        local bufnr = {buf_num}
        
        -- Check for LSP clients
        local clients = vim.lsp.get_clients({{ bufnr = bufnr }})
        if #clients == 0 then
            return nil
        end
        
        -- Build params for document symbols
        local params = {{
            textDocument = vim.lsp.util.make_text_document_params(bufnr)
        }}
        
        -- Synchronous request
        local result = vim.lsp.buf_request_sync(bufnr, 'textDocument/documentSymbol', params, 2000)
        
        if not result or vim.tbl_isempty(result) then
            return nil
        end
        
        -- Collect symbols from all LSP clients (usually just one responds)
        for _, response in pairs(result) do
            if response.result and type(response.result) == 'table' and #response.result > 0 then
                return response.result
            end
        end
        
        return nil
        """

        try:
            result = await self.execute_lua(lua_code)
            return result if result else None
        except Exception:
            return None

    async def lsp_hover(
        self, filepath: str, line: int, column: int
    ) -> Optional[Dict[str, Any]]:
        """Get hover information for a symbol at a position.

        Args:
            filepath: Path to the file
            line: Line number (1-indexed)
            column: Column number (0-indexed)

        Returns:
            Hover information dictionary, or None if not found
        """
        buf_num = await self.open_file(filepath)

        # Wait for LSP to attach and be ready
        await asyncio.sleep(0.5)

        lua_code = f"""
        local bufnr = {buf_num}
        local line = {line - 1}  -- Convert to 0-indexed
        local col = {column}
        
        -- Check for LSP clients
        local clients = vim.lsp.get_clients({{ bufnr = bufnr }})
        if #clients == 0 then
            return nil
        end
        
        -- Build params
        local params = {{
            textDocument = vim.lsp.util.make_text_document_params(bufnr),
            position = {{ line = line, character = col }}
        }}
        
        -- Synchronous request
        local result = vim.lsp.buf_request_sync(bufnr, 'textDocument/hover', params, 2000)
        
        if not result or vim.tbl_isempty(result) then
            return nil
        end
        
        -- Extract hover result from first responding client
        for _, response in pairs(result) do
            if response.result then
                return response.result
            end
        end
        
        return nil
        """

        try:
            result = await self.execute_lua(lua_code)
            return result if result else None
        except Exception:
            return None

    async def _lsp_request(
        self, bufnr: int, method: str, line: int, column: int, timeout_ms: int = 2000
    ) -> Optional[List[Dict[str, Any]]]:
        """Generic LSP request helper.

        Note: We use Lua because Neovim's LSP client (vim.lsp.*) is Lua-native.
        pynvim doesn't provide direct LSP bindings, so Lua is the right layer.
        """
        # Use f-strings for now - simpler and more reliable than varargs
        lua_code = f"""
        local bufnr = {bufnr}
        local method = '{method}'
        local line = {line}
        local col = {column}
        local timeout = {timeout_ms}
        
        -- Check for LSP clients
        local clients = vim.lsp.get_clients({{ bufnr = bufnr }})
        if #clients == 0 then
            return nil
        end
        
        -- Build params
        local params = {{
            textDocument = vim.lsp.util.make_text_document_params(bufnr),
            position = {{ line = line, character = col }}
        }}
        
        -- Synchronous request
        local result = vim.lsp.buf_request_sync(bufnr, method, params, timeout)
        
        if not result or vim.tbl_isempty(result) then
            return nil
        end
        
        -- Collect locations from all LSP clients
        local locations = {{}}
        for _, response in pairs(result) do
            if response.result then
                local res = response.result
                if res.uri or res.targetUri then
                    table.insert(locations, res)
                elseif type(res) == 'table' and #res > 0 then
                    for _, loc in ipairs(res) do
                        table.insert(locations, loc)
                    end
                end
            end
        end
        
        return #locations > 0 and locations or nil
        """

        result = await self.execute_lua(lua_code)
        return result

    async def _lsp_request_with_context(
        self,
        bufnr: int,
        method: str,
        line: int,
        column: int,
        include_declaration: bool,
        timeout_ms: int = 2000,
    ) -> Optional[List[Dict[str, Any]]]:
        """LSP request helper for textDocument/references.

        References require a special context parameter.
        """
        lua_code = f"""
        local bufnr = {bufnr}
        local method = '{method}'
        local line = {line}
        local col = {column}
        local include_declaration = {"true" if include_declaration else "false"}
        local timeout = {timeout_ms}
        
        -- Check for LSP clients
        local clients = vim.lsp.get_clients({{ bufnr = bufnr }})
        if #clients == 0 then
            return nil
        end
        
        -- Build params with context for references
        local params = {{
            textDocument = vim.lsp.util.make_text_document_params(bufnr),
            position = {{ line = line, character = col }},
            context = {{ includeDeclaration = include_declaration }}
        }}
        
        -- Synchronous request
        local result = vim.lsp.buf_request_sync(bufnr, method, params, timeout)
        
        if not result or vim.tbl_isempty(result) then
            return nil
        end
        
        -- Collect locations from all LSP clients
        local locations = {{}}
        for _, response in pairs(result) do
            if response.result then
                local res = response.result
                if res.uri or res.targetUri then
                    table.insert(locations, res)
                elseif type(res) == 'table' and #res > 0 then
                    for _, loc in ipairs(res) do
                        table.insert(locations, loc)
                    end
                end
            end
        end
        
        return #locations > 0 and locations or nil
        """

        result = await self.execute_lua(lua_code)
        return result

    def is_running(self) -> bool:
        """Check if Neovim instance is running."""
        return self._started and self.nvim is not None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
