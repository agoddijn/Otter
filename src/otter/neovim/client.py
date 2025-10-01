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

    async def get_buffer_info(self, filepath: str) -> Dict[str, Any]:
        """Get information about a buffer.

        Args:
            filepath: Path to the file

        Returns:
            Dictionary with buffer information:
            - is_open: Whether the file is open in a buffer
            - is_modified: Whether the buffer has unsaved changes
            - line_count: Number of lines in the buffer
            - language: File type/language
        """
        # Resolve path
        if os.path.isabs(filepath):
            file_path = Path(filepath)
        else:
            file_path = self.project_path / filepath
        
        file_path = file_path.resolve()
        filepath_str = str(file_path)
        
        # Check if file is in our buffers cache
        is_open = filepath_str in self._buffers
        
        if not is_open:
            # File not open, return basic info
            if file_path.exists():
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                line_count = len(lines)
            else:
                line_count = 0
            
            return {
                "is_open": False,
                "is_modified": False,
                "line_count": line_count,
                "language": file_path.suffix.lstrip('.') if file_path.suffix else "unknown"
            }
        
        # File is open, get buffer info from Neovim
        buf_num = self._buffers[filepath_str]
        
        if not self.nvim:
            raise RuntimeError("Neovim not connected")
        
        loop = asyncio.get_event_loop()
        
        def _get_info():
            if not self.nvim:
                raise RuntimeError("Neovim not connected")
            
            # Find the buffer
            buf = None
            for b in self.nvim.buffers:
                if b.number == buf_num:
                    buf = b
                    break
            
            if not buf:
                raise RuntimeError(f"Buffer {buf_num} not found")
            
            # Get buffer info
            is_modified = buf.options.get('modified', False)
            line_count = len(buf)
            filetype = buf.options.get('filetype', 'unknown')
            
            return {
                "is_open": True,
                "is_modified": is_modified,
                "line_count": line_count,
                "language": filetype
            }
        
        info = await loop.run_in_executor(None, _get_info)
        return info

    async def edit_buffer_lines(
        self, filepath: str, edits: List[Tuple[int, int, List[str]]]
    ) -> Dict[str, Any]:
        """Edit lines in a buffer.

        Args:
            filepath: Path to the file
            edits: List of (start_line, end_line, new_lines) tuples
                  - start_line: 1-indexed start line
                  - end_line: 1-indexed end line (inclusive)
                  - new_lines: List of new line strings to replace with

        Returns:
            Dictionary with edit results:
            - success: Whether all edits were applied
            - line_count: New line count after edits
            - is_modified: Whether buffer is now modified
        """
        # Open file if not already open
        buf_num = await self.open_file(filepath)
        
        if not self.nvim:
            raise RuntimeError("Neovim not connected")
        
        loop = asyncio.get_event_loop()
        
        def _apply_edits():
            if not self.nvim:
                raise RuntimeError("Neovim not connected")
            
            # Find the buffer
            buf = None
            for b in self.nvim.buffers:
                if b.number == buf_num:
                    buf = b
                    break
            
            if not buf:
                raise RuntimeError(f"Buffer {buf_num} not found")
            
            # Sort edits by line number (descending) to avoid offset issues
            sorted_edits = sorted(edits, key=lambda e: e[0], reverse=True)
            
            # Apply each edit
            for start_line, end_line, new_lines in sorted_edits:
                # Convert to 0-indexed
                start_idx = start_line - 1
                end_idx = end_line  # nvim_buf_set_lines is exclusive on end
                
                # Validate line range
                if start_idx < 0:
                    raise ValueError(f"Invalid start line: {start_line} (must be >= 1)")
                if end_idx > len(buf):
                    raise ValueError(f"Invalid end line: {end_line} (buffer has {len(buf)} lines)")
                
                # Set lines in buffer
                buf[start_idx:end_idx] = new_lines
            
            # Get updated buffer info
            is_modified = buf.options.get('modified', False)
            line_count = len(buf)
            
            return {
                "success": True,
                "line_count": line_count,
                "is_modified": is_modified
            }
        
        result = await loop.run_in_executor(None, _apply_edits)
        return result

    async def save_buffer(self, filepath: str) -> Dict[str, Any]:
        """Save a buffer to disk.

        Args:
            filepath: Path to the file

        Returns:
            Dictionary with save results:
            - success: Whether save was successful
            - is_modified: Whether buffer is still modified (should be False after save)
            - file: Absolute path to saved file
        """
        # Resolve path
        if os.path.isabs(filepath):
            file_path = Path(filepath)
        else:
            file_path = self.project_path / filepath
        
        file_path = file_path.resolve()
        filepath_str = str(file_path)
        
        # Check if file is open
        if filepath_str not in self._buffers:
            # File not open, nothing to save
            return {
                "success": False,
                "is_modified": False,
                "file": filepath_str,
                "error": "Buffer not open"
            }
        
        buf_num = self._buffers[filepath_str]
        
        if not self.nvim:
            raise RuntimeError("Neovim not connected")
        
        loop = asyncio.get_event_loop()
        
        def _save_buffer():
            if not self.nvim:
                raise RuntimeError("Neovim not connected")
            
            # Find the buffer
            buf = None
            for b in self.nvim.buffers:
                if b.number == buf_num:
                    buf = b
                    break
            
            if not buf:
                raise RuntimeError(f"Buffer {buf_num} not found")
            
            # Execute write command for this buffer
            # Use :write to save the buffer
            try:
                self.nvim.command(f'buffer {buf_num}')
                self.nvim.command('write')
                
                # Check if buffer is still modified (should be False after save)
                is_modified = buf.options.get('modified', False)
                
                return {
                    "success": True,
                    "is_modified": is_modified,
                    "file": filepath_str
                }
            except Exception as e:
                return {
                    "success": False,
                    "is_modified": buf.options.get('modified', False),
                    "file": filepath_str,
                    "error": str(e)
                }
        
        result = await loop.run_in_executor(None, _save_buffer)
        return result

    async def discard_buffer(self, filepath: str) -> Dict[str, Any]:
        """Discard changes in a buffer (reload from disk).

        Args:
            filepath: Path to the file

        Returns:
            Dictionary with discard results:
            - success: Whether discard was successful
            - is_modified: Whether buffer is still modified (should be False after discard)
            - file: Absolute path to file
        """
        # Resolve path
        if os.path.isabs(filepath):
            file_path = Path(filepath)
        else:
            file_path = self.project_path / filepath
        
        file_path = file_path.resolve()
        filepath_str = str(file_path)
        
        # Check if file is open
        if filepath_str not in self._buffers:
            return {
                "success": False,
                "is_modified": False,
                "file": filepath_str,
                "error": "Buffer not open"
            }
        
        buf_num = self._buffers[filepath_str]
        
        if not self.nvim:
            raise RuntimeError("Neovim not connected")
        
        loop = asyncio.get_event_loop()
        
        def _discard_buffer():
            if not self.nvim:
                raise RuntimeError("Neovim not connected")
            
            # Find the buffer
            buf = None
            for b in self.nvim.buffers:
                if b.number == buf_num:
                    buf = b
                    break
            
            if not buf:
                raise RuntimeError(f"Buffer {buf_num} not found")
            
            # Reload buffer from disk using :edit!
            try:
                self.nvim.command(f'buffer {buf_num}')
                self.nvim.command('edit!')  # Force reload from disk
                
                # Check modified status (should be False after reload)
                is_modified = buf.options.get('modified', False)
                
                return {
                    "success": True,
                    "is_modified": is_modified,
                    "file": filepath_str
                }
            except Exception as e:
                return {
                    "success": False,
                    "is_modified": buf.options.get('modified', False),
                    "file": filepath_str,
                    "error": str(e)
                }
        
        result = await loop.run_in_executor(None, _discard_buffer)
        return result

    async def get_buffer_content(self, filepath: str) -> Optional[str]:
        """Get raw buffer content as string.

        Args:
            filepath: Path to the file

        Returns:
            Buffer content as string, or None if buffer not open
        """
        # Resolve path
        if os.path.isabs(filepath):
            file_path = Path(filepath)
        else:
            file_path = self.project_path / filepath
        
        file_path = file_path.resolve()
        filepath_str = str(file_path)
        
        # Check if file is open
        if filepath_str not in self._buffers:
            return None
        
        buf_num = self._buffers[filepath_str]
        
        if not self.nvim:
            raise RuntimeError("Neovim not connected")
        
        loop = asyncio.get_event_loop()
        
        def _get_content():
            if not self.nvim:
                raise RuntimeError("Neovim not connected")
            
            # Find the buffer
            buf = None
            for b in self.nvim.buffers:
                if b.number == buf_num:
                    buf = b
                    break
            
            if not buf:
                return None
            
            # Get buffer lines and join
            lines = buf[:]
            return "\n".join(lines)
        
        return await loop.run_in_executor(None, _get_content)

    async def get_buffer_diff(self, filepath: str) -> Dict[str, Any]:
        """Get diff between buffer and disk version.

        Args:
            filepath: Path to the file

        Returns:
            Dictionary with diff information:
            - has_changes: Whether buffer differs from disk
            - diff: Unified diff string (if has_changes)
            - file: Absolute path to file
        """
        # Resolve path
        if os.path.isabs(filepath):
            file_path = Path(filepath)
        else:
            file_path = self.project_path / filepath
        
        file_path = file_path.resolve()
        filepath_str = str(file_path)
        
        # Check if file is open
        if filepath_str not in self._buffers:
            return {
                "has_changes": False,
                "file": filepath_str,
                "error": "Buffer not open"
            }
        
        buf_num = self._buffers[filepath_str]
        
        if not self.nvim:
            raise RuntimeError("Neovim not connected")
        
        loop = asyncio.get_event_loop()
        
        def _get_diff():
            if not self.nvim:
                raise RuntimeError("Neovim not connected")
            
            # Find the buffer
            buf = None
            for b in self.nvim.buffers:
                if b.number == buf_num:
                    buf = b
                    break
            
            if not buf:
                raise RuntimeError(f"Buffer {buf_num} not found")
            
            try:
                # Get buffer content
                buffer_lines = buf[:]
                
                # Read disk content
                if not file_path.exists():
                    # New file not yet saved
                    import difflib
                    diff = difflib.unified_diff(
                        [],
                        buffer_lines,
                        fromfile=f"a/{filepath_str}",
                        tofile=f"b/{filepath_str}",
                        lineterm=""
                    )
                    return {
                        "has_changes": True,
                        "diff": "\n".join(diff),
                        "file": filepath_str
                    }
                
                with open(file_path, 'r') as f:
                    disk_lines = f.read().splitlines()
                
                # Compare
                if buffer_lines == disk_lines:
                    return {
                        "has_changes": False,
                        "file": filepath_str
                    }
                
                # Generate unified diff
                import difflib
                diff = difflib.unified_diff(
                    disk_lines,
                    buffer_lines,
                    fromfile=f"a/{filepath_str}",
                    tofile=f"b/{filepath_str}",
                    lineterm=""
                )
                
                return {
                    "has_changes": True,
                    "diff": "\n".join(diff),
                    "file": filepath_str
                }
            
            except Exception as e:
                return {
                    "has_changes": False,
                    "file": filepath_str,
                    "error": str(e)
                }
        
        result = await loop.run_in_executor(None, _get_diff)
        return result

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

    async def lsp_completion(
        self, filepath: str, line: int, column: int
    ) -> Optional[List[Dict[str, Any]]]:
        """Get code completion suggestions at a position.

        Args:
            filepath: Path to the file
            line: Line number (1-indexed)
            column: Column number (0-indexed, position of cursor)

        Returns:
            List of completion items, or None if no completions available
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
            position = {{ line = line, character = col }},
            context = {{
                triggerKind = 1  -- Invoked (1 = invoked, 2 = trigger character, 3 = reopen)
            }}
        }}
        
        -- Synchronous request
        local result = vim.lsp.buf_request_sync(bufnr, 'textDocument/completion', params, 3000)
        
        if not result or vim.tbl_isempty(result) then
            return nil
        end
        
        -- Extract completion items from first responding client
        for _, response in pairs(result) do
            if response.result then
                -- LSP can return CompletionList or CompletionItem[]
                if response.result.items then
                    -- CompletionList format
                    return response.result.items
                elseif type(response.result) == 'table' and #response.result > 0 then
                    -- CompletionItem[] format
                    return response.result
                end
            end
        end
        
        return nil
        """

        try:
            result = await self.execute_lua(lua_code)
            return result if result else None
        except Exception:
            return None

    async def lsp_rename(
        self, filepath: str, line: int, column: int, new_name: str
    ) -> Optional[Dict[str, Any]]:
        """Rename a symbol at a position using LSP.

        Args:
            filepath: Path to the file
            line: Line number (1-indexed)
            column: Column number (0-indexed)
            new_name: The new name for the symbol

        Returns:
            WorkspaceEdit dictionary with changes, or None if rename not supported
        """
        buf_num = await self.open_file(filepath)

        # Wait for LSP to attach and be ready
        await asyncio.sleep(0.5)

        # Escape special characters in new_name for Lua string
        new_name_escaped = new_name.replace("\\", "\\\\").replace("'", "\\'")

        lua_code = f"""
        local bufnr = {buf_num}
        local line = {line - 1}  -- Convert to 0-indexed
        local col = {column}
        local new_name = '{new_name_escaped}'
        
        -- Check for LSP clients
        local clients = vim.lsp.get_clients({{ bufnr = bufnr }})
        if #clients == 0 then
            return {{ error = 'No LSP clients attached' }}
        end
        
        -- Build rename params
        local params = {{
            textDocument = vim.lsp.util.make_text_document_params(bufnr),
            position = {{ line = line, character = col }},
            newName = new_name
        }}
        
        -- Synchronous request
        local result = vim.lsp.buf_request_sync(bufnr, 'textDocument/rename', params, 5000)
        
        if not result or vim.tbl_isempty(result) then
            return {{ error = 'No rename results from LSP' }}
        end
        
        -- Collect WorkspaceEdit from first successful response
        for _, response in pairs(result) do
            if response.result then
                return response.result
            end
            if response.error then
                return {{ error = response.error.message or 'Rename failed' }}
            end
        end
        
        return {{ error = 'LSP rename request failed' }}
        """

        try:
            result = await self.execute_lua(lua_code)
            if result and isinstance(result, dict) and "error" in result:
                return None
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

    # ========================================================================
    # DAP (Debug Adapter Protocol) Methods
    # ========================================================================

    async def dap_start_session(
        self, filepath: str, config_name: Optional[str] = None, args: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Start a debug session for a file.

        Args:
            filepath: Path to the file to debug
            config_name: Name of debug configuration (defaults to first available)
            args: Optional command-line arguments

        Returns:
            Session info dict or None if failed
        """
        buf_num = await self.open_file(filepath)
        await asyncio.sleep(0.5)  # Wait for DAP to be ready

        lua_code = f"""
        local dap = require('dap')
        local bufnr = {buf_num}
        
        -- Get filetype to find appropriate configuration
        local filetype = vim.bo[bufnr].filetype
        
        if not dap.configurations[filetype] then
            return {{ error = 'No debug configuration for filetype: ' .. filetype }}
        end
        
        -- Select configuration
        local config = nil
        if '{config_name or ""}' ~= '' then
            for _, c in ipairs(dap.configurations[filetype]) do
                if c.name == '{config_name or ""}' then
                    config = c
                    break
                end
            end
        else
            config = dap.configurations[filetype][1]
        end
        
        if not config then
            return {{ error = 'Configuration not found' }}
        end
        
        -- Override args if provided
        local args_str = '{",".join(args or [])}'
        if args_str ~= '' then
            config.args = vim.split(args_str, ',')
        end
        
        -- Start debugging
        dap.run(config)
        
        -- Wait a bit for session to initialize
        vim.wait(500)
        
        local session = dap.session()
        if session then
            return {{
                session_id = tostring(session.id or 'unknown'),
                config_name = config.name,
                file = '{filepath}',
                status = 'running'
            }}
        else
            return {{ error = 'Failed to start debug session' }}
        end
        """

        try:
            result = await self.execute_lua(lua_code)
            return result
        except Exception:
            return None

    async def dap_set_breakpoints(
        self, filepath: str, lines: List[int], conditions: Optional[Dict[int, str]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Set breakpoints in a file.

        Args:
            filepath: File path
            lines: Line numbers for breakpoints (1-indexed)
            conditions: Optional conditions for breakpoints (line -> condition)

        Returns:
            List of breakpoint info dicts
        """
        buf_num = await self.open_file(filepath)

        conditions_str = "{}"
        if conditions:
            # Build Lua table: {[line] = condition}
            pairs = [f"[{line}] = '{cond}'" for line, cond in conditions.items()]
            conditions_str = "{" + ", ".join(pairs) + "}"

        lines_str = "{" + ", ".join(str(line) for line in lines) + "}"

        lua_code = f"""
        local dap = require('dap')
        local breakpoints = require('dap.breakpoints')
        local bufnr = {buf_num}
        local lines = {lines_str}
        local conditions = {conditions_str}
        
        -- Set breakpoints
        local result = {{}}
        for _, line in ipairs(lines) do
            local bp = {{
                line = line,
                condition = conditions[line]
            }}
            breakpoints.set(bp, bufnr, line)
            table.insert(result, {{
                line = line,
                verified = true,
                condition = conditions[line]
            }})
        end
        
        return result
        """

        try:
            result = await self.execute_lua(lua_code)
            return result if result else []
        except Exception:
            return []

    async def dap_continue(self) -> Optional[Dict[str, Any]]:
        """Continue execution until next breakpoint or completion."""
        lua_code = """
        local dap = require('dap')
        local session = dap.session()
        
        if not session then
            return {error = 'No active debug session'}
        end
        
        dap.continue()
        
        -- Wait for state change
        vim.wait(200)
        
        return {status = 'running'}
        """

        try:
            result = await self.execute_lua(lua_code)
            return result
        except Exception:
            return None

    async def dap_step_over(self) -> Optional[Dict[str, Any]]:
        """Step over current line."""
        lua_code = """
        local dap = require('dap')
        local session = dap.session()
        
        if not session then
            return {error = 'No active debug session'}
        end
        
        dap.step_over()
        vim.wait(200)
        
        return {status = 'paused'}
        """

        try:
            result = await self.execute_lua(lua_code)
            return result
        except Exception:
            return None

    async def dap_step_into(self) -> Optional[Dict[str, Any]]:
        """Step into function."""
        lua_code = """
        local dap = require('dap')
        local session = dap.session()
        
        if not session then
            return {error = 'No active debug session'}
        end
        
        dap.step_into()
        vim.wait(200)
        
        return {status = 'paused'}
        """

        try:
            result = await self.execute_lua(lua_code)
            return result
        except Exception:
            return None

    async def dap_step_out(self) -> Optional[Dict[str, Any]]:
        """Step out of current function."""
        lua_code = """
        local dap = require('dap')
        local session = dap.session()
        
        if not session then
            return {error = 'No active debug session'}
        end
        
        dap.step_out()
        vim.wait(200)
        
        return {status = 'paused'}
        """

        try:
            result = await self.execute_lua(lua_code)
            return result
        except Exception:
            return None

    async def dap_pause(self) -> Optional[Dict[str, Any]]:
        """Pause execution."""
        lua_code = """
        local dap = require('dap')
        local session = dap.session()
        
        if not session then
            return {error = 'No active debug session'}
        end
        
        dap.pause()
        vim.wait(200)
        
        return {status = 'paused'}
        """

        try:
            result = await self.execute_lua(lua_code)
            return result
        except Exception:
            return None

    async def dap_stop(self) -> Optional[Dict[str, Any]]:
        """Stop debug session."""
        lua_code = """
        local dap = require('dap')
        local session = dap.session()
        
        if not session then
            return {error = 'No active debug session'}
        end
        
        dap.terminate()
        dap.close()
        
        return {status = 'stopped'}
        """

        try:
            result = await self.execute_lua(lua_code)
            return result
        except Exception:
            return None

    async def dap_get_stack_frames(self) -> Optional[List[Dict[str, Any]]]:
        """Get current call stack."""
        lua_code = """
        local dap = require('dap')
        local session = dap.session()
        
        if not session then
            return nil
        end
        
        -- Get current thread
        local thread_id = session.current_thread_id
        if not thread_id then
            return nil
        end
        
        -- Request stack trace
        local result = {}
        session:request('stackTrace', {threadId = thread_id}, function(err, response)
            if not err and response then
                result = response.stackFrames or {}
            end
        end)
        
        -- Wait for response
        vim.wait(500)
        
        -- Convert to our format
        local frames = {}
        for _, frame in ipairs(result) do
            table.insert(frames, {
                id = frame.id,
                name = frame.name,
                file = frame.source and frame.source.path or 'unknown',
                line = frame.line,
                column = frame.column
            })
        end
        
        return frames
        """

        try:
            result = await self.execute_lua(lua_code)
            return result if result else []
        except Exception:
            return []

    async def dap_get_scopes(self, frame_id: int) -> Optional[List[Dict[str, Any]]]:
        """Get variable scopes for a stack frame.

        Args:
            frame_id: Stack frame ID

        Returns:
            List of scope dicts
        """
        lua_code = f"""
        local dap = require('dap')
        local session = dap.session()
        
        if not session then
            return nil
        end
        
        local result = nil
        session:request('scopes', {{frameId = {frame_id}}}, function(err, response)
            if not err and response then
                result = response.scopes or {{}}
            end
        end)
        
        vim.wait(500)
        
        if not result then
            return nil
        end
        
        local scopes = {{}}
        for _, scope in ipairs(result) do
            table.insert(scopes, {{
                name = scope.name,
                variables_reference = scope.variablesReference,
                expensive = scope.expensive or false
            }})
        end
        
        return scopes
        """

        try:
            result = await self.execute_lua(lua_code)
            return result if result else []
        except Exception:
            return []

    async def dap_get_variables(self, variables_reference: int) -> Optional[List[Dict[str, Any]]]:
        """Get variables for a scope or parent variable.

        Args:
            variables_reference: Reference ID for variables

        Returns:
            List of variable dicts
        """
        lua_code = f"""
        local dap = require('dap')
        local session = dap.session()
        
        if not session then
            return nil
        end
        
        local result = nil
        session:request('variables', {{variablesReference = {variables_reference}}}, function(err, response)
            if not err and response then
                result = response.variables or {{}}
            end
        end)
        
        vim.wait(500)
        
        if not result then
            return nil
        end
        
        local variables = {{}}
        for _, var in ipairs(result) do
            table.insert(variables, {{
                name = var.name,
                value = var.value,
                type = var.type,
                variables_reference = var.variablesReference or 0
            }})
        end
        
        return variables
        """

        try:
            result = await self.execute_lua(lua_code)
            return result if result else []
        except Exception:
            return []

    async def dap_evaluate(
        self, expression: str, frame_id: Optional[int] = None, context: str = "repl"
    ) -> Optional[Dict[str, Any]]:
        """Evaluate an expression in debug context.

        Args:
            expression: Expression to evaluate
            frame_id: Optional stack frame ID
            context: Evaluation context ('repl', 'watch', 'hover')

        Returns:
            Evaluation result dict
        """
        frame_id_str = str(frame_id) if frame_id is not None else "nil"

        # Escape single quotes in expression
        expression_escaped = expression.replace("'", "\\'")

        lua_code = f"""
        local dap = require('dap')
        local session = dap.session()
        
        if not session then
            return {{error = 'No active debug session'}}
        end
        
        local result = nil
        session:request('evaluate', {{
            expression = '{expression_escaped}',
            frameId = {frame_id_str},
            context = '{context}'
        }}, function(err, response)
            if err then
                result = {{error = err.message or 'Evaluation failed'}}
            elseif response then
                result = {{
                    result = response.result,
                    type = response.type,
                    variables_reference = response.variablesReference or 0
                }}
            end
        end)
        
        vim.wait(500)
        
        return result
        """

        try:
            result = await self.execute_lua(lua_code)
            return result
        except Exception:
            return None

    async def dap_get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get current debug session information."""
        lua_code = """
        local dap = require('dap')
        local session = dap.session()
        
        if not session then
            return {status = 'stopped'}
        end
        
        local thread_id = session.current_thread_id
        local stopped = session.stopped_thread_id
        
        return {
            session_id = tostring(session.id or 'unknown'),
            status = stopped and 'paused' or 'running',
            thread_id = thread_id,
            stopped_thread_id = stopped
        }
        """

        try:
            result = await self.execute_lua(lua_code)
            return result
        except Exception:
            return None

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
