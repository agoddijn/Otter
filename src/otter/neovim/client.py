from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pynvim  # type: ignore

from ..config import OtterConfig, load_config, get_effective_languages
from ..bootstrap import check_and_install_lsp_servers


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
        
        # Load configuration
        self.config = load_config(self.project_path)
        self.enabled_languages = get_effective_languages(self.config)

    def _create_socket_path(self) -> str:
        """Create a unique socket path for this Neovim instance."""
        temp_dir = tempfile.gettempdir()
        return os.path.join(temp_dir, f"nvim_ide_{os.getpid()}.sock")

    async def start(self) -> None:
        """Start the headless Neovim instance."""
        if self._started:
            return

        # Bootstrap: Check and install missing LSP servers
        if self.config.lsp.enabled and self.config.lsp.auto_install and self.enabled_languages:
            await check_and_install_lsp_servers(
                self.enabled_languages,
                self.config.lsp.language_configs,
                auto_install=self.config.lsp.auto_install,
            )

        # Get the config directory (configs/ in project root)
        config_dir = Path(__file__).parent.parent.parent.parent / "configs"
        init_lua = config_dir / "init.lua"

        if not init_lua.exists():
            raise FileNotFoundError(f"Neovim config not found: {init_lua}")
        
        # Generate runtime config file BEFORE starting Neovim
        # This eliminates the race condition
        self._generate_runtime_config(config_dir)

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

        self._started = True

    def _generate_runtime_config(self, config_dir: Path) -> None:
        """Generate runtime_config.lua with all settings.
        
        This file is created BEFORE Neovim starts, eliminating race conditions.
        It contains all configuration needed for LSP, DAP, and plugins.
        """
        # Build enabled languages dict
        enabled_langs = {lang: True for lang in self.enabled_languages}
        
        # Build LSP server configs
        lsp_servers = {}
        for lang in self.enabled_languages:
            if lang in self.config.lsp.language_configs:
                lang_config = self.config.lsp.language_configs[lang]
                lsp_servers[lang] = {
                    'enabled': lang_config.enabled,
                    'server': lang_config.server,
                    'python_path': self.config.resolve_path(lang_config.python_path) if lang_config.python_path else None,
                    'settings': lang_config.settings or {},
                }
            else:
                # Use defaults
                lsp_servers[lang] = {
                    'enabled': True,
                    'server': self._get_default_server(lang),
                    'python_path': None,
                    'settings': {},
                }
        
        # Build DAP adapter configs
        dap_adapters = {}
        for lang in self.enabled_languages:
            if lang in self.config.dap.language_configs:
                lang_config = self.config.dap.language_configs[lang]
                dap_adapters[lang] = {
                    'enabled': lang_config.enabled,
                    'python_path': self.config.resolve_path(lang_config.python_path) if hasattr(lang_config, 'python_path') and lang_config.python_path else None,
                    'adapter': getattr(lang_config, 'adapter', None),
                    'configurations': lang_config.configurations or [],
                }
            else:
                # Use defaults - enable DAP for this language
                dap_adapters[lang] = {
                    'enabled': True,
                    'python_path': None,
                    'adapter': None,
                    'configurations': [],
                }
        
        # Build config structure
        runtime_config = {
            'enabled_languages': enabled_langs,
            'lsp': {
                'enabled': self.config.lsp.enabled,
                'servers': lsp_servers,
            },
            'dap': {
                'enabled': self.config.dap.enabled,
                'adapters': dap_adapters,
            },
            'test_mode': os.getenv('OTTER_TEST_MODE') == '1',
        }
        
        # Generate Lua code
        lua_code = f"""-- Auto-generated by Otter (DO NOT EDIT MANUALLY)
-- This file is regenerated each time Otter starts
-- Project: {self.project_path}

_G.otter_runtime_config = {self._lua_repr(runtime_config)}

-- Debug helper
function _G.otter_debug_config()
    print("Otter Runtime Config:")
    print(vim.inspect(_G.otter_runtime_config))
end
"""
        
        # Write to runtime_config.lua
        runtime_config_path = config_dir / "runtime_config.lua"
        runtime_config_path.write_text(lua_code)
    
    def _get_default_server(self, lang: str) -> str:
        """Get default LSP server name for a language."""
        defaults = {
            'python': 'pyright',
            'javascript': 'tsserver',
            'typescript': 'tsserver',
            'rust': 'rust_analyzer',
            'go': 'gopls',
            'lua': 'lua_ls',
        }
        return defaults.get(lang, lang)
    
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

    async def _send_config_to_nvim(self) -> None:
        """Send Otter configuration to Neovim."""
        if not self.nvim:
            return
        
        loop = asyncio.get_event_loop()
        
        try:
            # Prepare config data to send to Lua
            enabled_langs = {lang: True for lang in self.enabled_languages}
            
            # Build config dict matching Lua expectations
            config_data = {
                'enabled_languages': enabled_langs,
                'lsp': {
                    'enabled': self.config.lsp.enabled,
                    'lazy_load': self.config.lsp.lazy_load,
                    'timeout_ms': self.config.lsp.timeout_ms,
                    'language_configs': {}
                },
                'dap': {
                    'enabled': self.config.dap.enabled,
                    'lazy_load': self.config.dap.lazy_load,
                    'language_configs': {}
                },
                'plugins': {
                    'treesitter_config': {
                        'ensure_installed': self.config.plugins.treesitter_ensure_installed,
                        'auto_install': self.config.plugins.treesitter_auto_install,
                    }
                }
            }
            
            # Add language-specific LSP configs
            for lang, lang_config in self.config.lsp.language_configs.items():
                config_data['lsp']['language_configs'][lang] = {
                    'enabled': lang_config.enabled,
                    'server': lang_config.server,
                    'python_path': self.config.resolve_path(lang_config.python_path) if lang_config.python_path else None,
                    'node_path': lang_config.node_path,
                    'settings': lang_config.settings,
                }
            
            # Add language-specific DAP configs
            for lang, lang_config in self.config.dap.language_configs.items():
                config_data['dap']['language_configs'][lang] = {
                    'enabled': lang_config.enabled,
                    'adapter': lang_config.adapter,
                    'python_path': self.config.resolve_path(lang_config.python_path) if lang_config.python_path else None,
                    'configurations': lang_config.configurations,
                }
            
            # Send config to Neovim's global scope
            await loop.run_in_executor(
                None,
                lambda: self.nvim.lua.exec(f"_G.otter_config = {self._lua_repr(config_data)}")
                if self.nvim
                else None
            )
        except Exception as e:
            # Config sending is best-effort, don't fail startup
            pass
    
    def _lua_repr(self, obj: Any) -> str:
        """Convert Python object to Lua table representation."""
        if obj is None:
            return 'nil'
        elif isinstance(obj, bool):
            return 'true' if obj else 'false'
        elif isinstance(obj, (int, float)):
            return str(obj)
        elif isinstance(obj, str):
            # Escape quotes and backslashes
            escaped = obj.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            return f'"{escaped}"'
        elif isinstance(obj, list):
            items = [self._lua_repr(item) for item in obj]
            return '{' + ', '.join(items) + '}'
        elif isinstance(obj, dict):
            items = []
            for key, value in obj.items():
                # Use bracket notation for string keys
                lua_key = f'["{key}"]' if isinstance(key, str) else f'[{key}]'
                items.append(f'{lua_key} = {self._lua_repr(value)}')
            return '{' + ', '.join(items) + '}'
        else:
            return 'nil'

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

    async def open_file(self, filepath: str, create_if_missing: bool = False) -> int:
        """Open a file in a Neovim buffer.

        Args:
            filepath: Path to the file (relative to project root or absolute)
            create_if_missing: If True, create a new buffer even if file doesn't exist

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

        # Check if already open (check this BEFORE checking if file exists)
        if filepath_str in self._buffers:
            return self._buffers[filepath_str]
        
        # Check if file exists
        if not file_path.exists():
            if not create_if_missing:
                raise RuntimeError(f"Failed to open file {filepath}: File not found")
            # Will create new buffer for non-existent file
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

        # Open the file (or create new buffer)
        try:
            if not self.nvim:
                raise RuntimeError("Neovim not connected")

            # Run file opening in executor
            loop = asyncio.get_event_loop()

            def _open_file():
                if not self.nvim:
                    raise RuntimeError("Neovim not connected")
                # 'edit' command works for both existing and new files
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
        self,
        filepath: Optional[str] = None,
        module: Optional[str] = None,
        config_name: Optional[str] = None,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        stop_on_entry: bool = False,
        just_my_code: bool = True,
        runtime_path: Optional[str] = None,
        breakpoints: Optional[List[int]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Start a debug session for a file or module.

        Args:
            filepath: Path to the file to debug (mutually exclusive with module)
            module: Module name to debug (e.g., "uvicorn")
            config_name: Name of debug configuration (defaults to first available)
            args: Optional command-line arguments
            env: Optional environment variables
            cwd: Optional working directory
            stop_on_entry: Whether to stop at first line
            just_my_code: Whether to debug only user code
            runtime_path: Path to language runtime (Python interpreter, Node.js, etc.)
            breakpoints: List of line numbers to set breakpoints at

        Returns:
            Session info dict or None if failed
        """
        # Determine filetype from file extension or default to python for modules
        filetype = "python"  # Default for modules
        buf_num = None
        
        if filepath:
            buf_num = await self.open_file(filepath)
            await asyncio.sleep(0.5)  # Wait for DAP to be ready
            
            # Get filetype from buffer
            loop = asyncio.get_event_loop()
            try:
                filetype = await loop.run_in_executor(
                    None,
                    lambda: self.nvim.eval(f'getbufvar({buf_num}, "&filetype")') if self.nvim else "python"
                )
            except Exception:
                # Fallback: detect from extension
                if filepath.endswith('.py'):
                    filetype = 'python'
                elif filepath.endswith(('.js', '.ts', '.jsx', '.tsx')):
                    filetype = 'javascript'
                elif filepath.endswith('.rs'):
                    filetype = 'rust'
                elif filepath.endswith('.go'):
                    filetype = 'go'

        # Build configuration dict
        # Escape strings for Lua
        def lua_escape(s: str) -> str:
            return s.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
        
        # Build args list for Lua
        args_lua = "nil"
        if args:
            escaped_args = [f"'{lua_escape(arg)}'" for arg in args]
            args_lua = "{" + ", ".join(escaped_args) + "}"
        
        # Build env dict for Lua
        env_lua = "nil"
        if env:
            env_pairs = [f"['{lua_escape(k)}'] = '{lua_escape(v)}'" for k, v in env.items()]
            env_lua = "{" + ", ".join(env_pairs) + "}"
        
        # Build config
        cwd_lua = f"'{lua_escape(cwd)}'" if cwd else "nil"
        config_name_lua = f"'{lua_escape(config_name)}'" if config_name else "nil"
        module_lua = f"'{lua_escape(module)}'" if module else "nil"
        filepath_lua = f"'{lua_escape(filepath)}'" if filepath else "nil"
        
        # Build breakpoints list for Lua
        breakpoint_lines_lua = "nil"
        if breakpoints and filepath:
            breakpoint_lines_lua = "{" + ", ".join(str(line) for line in breakpoints) + "}"

        lua_code = f"""
        local dap = require('dap')
        local filetype = '{filetype}'
        
        -- Check if DAP is configured for this filetype
        -- DAP should already be set up via dap_config.setup() during initialization
        if not dap.configurations[filetype] then
            local config_status = _G.otter_runtime_config and 'loaded' or 'not loaded'
            local enabled_langs = _G.otter_runtime_config and vim.inspect(_G.otter_runtime_config.enabled_languages) or 'none'
            return {{ error = 'No debug configuration available for filetype: ' .. filetype .. 
                    '\\nRuntime config: ' .. config_status .. 
                    '\\nEnabled languages: ' .. enabled_langs }}
        end
        
        -- Build custom configuration
        local config = {{
            type = filetype,
            request = 'launch',
            name = 'Otter Debug Session',
        }}
        
        -- Set program/module
        if {module_lua} then
            config.module = {module_lua}
        elseif {filepath_lua} then
            config.program = {filepath_lua}
        else
            return {{ error = 'Must specify either file or module' }}
        end
        
        -- Add optional parameters
        if {args_lua} then
            config.args = {args_lua}
        end
        
        if {env_lua} then
            config.env = {env_lua}
        end
        
        if {cwd_lua} then
            config.cwd = {cwd_lua}
        end
        
        -- 🎯 CRITICAL: If breakpoints are provided, ALWAYS stop on entry
        -- This gives us time to set breakpoints before execution continues
        local has_breakpoints = {breakpoint_lines_lua} ~= nil
        config.stopOnEntry = {str(stop_on_entry).lower()} or has_breakpoints
        config.justMyCode = {str(just_my_code).lower()}
        
        -- Language-specific runtime configuration
        if filetype == 'python' then
            -- Python: Set Python interpreter path
            {f"config.pythonPath = '{lua_escape(runtime_path)}'" if runtime_path else "config.pythonPath = vim.fn.exepath('python')"}
        elseif filetype == 'javascript' or filetype == 'typescript' then
            -- Node.js: Set runtime executable
            {f"config.runtimeExecutable = '{lua_escape(runtime_path)}'" if runtime_path else "config.runtimeExecutable = 'node'"}
        elseif filetype == 'rust' then
            -- Rust: Typically uses cargo
            -- Runtime path would point to cargo if specified
            if {f"'{lua_escape(runtime_path)}'" if runtime_path else "nil"} then
                config.cargo = {f"'{lua_escape(runtime_path)}'"}
            end
        elseif filetype == 'go' then
            -- Go: Set dlv path if specified
            if {f"'{lua_escape(runtime_path)}'" if runtime_path else "nil"} then
                config.dlvToolPath = {f"'{lua_escape(runtime_path)}'"}
            end
        end
        
        -- Console configuration
        -- Use 'internalConsole' to capture output via DAP events
        -- 'integratedTerminal' opens a separate terminal and doesn't send output events
        config.console = 'internalConsole'
        
        -- 🎯 Set up event listeners to capture PID and output
        -- Store in global namespace so we can access from listeners
        _G.otter_dap_capture = _G.otter_dap_capture or {{}}
        local capture_id = tostring(os.time() .. math.random(1000, 9999))
        _G.otter_dap_capture[capture_id] = {{
            pid = nil,
            output = {{}},
        }}
        
        local capture = _G.otter_dap_capture[capture_id]
        
        -- Listener for process event (contains real PID)
        local process_listener_name = 'otter_process_' .. capture_id
        dap.listeners.after.event_process[process_listener_name] = function(session, body)
            if body and body.systemProcessId then
                capture.pid = body.systemProcessId
            end
        end
        
        -- Listener for output events (stdout/stderr)
        local output_listener_name = 'otter_output_' .. capture_id
        dap.listeners.after.event_output[output_listener_name] = function(session, body)
            if body and body.output then
                table.insert(capture.output, body.output)
            end
        end
        
        -- Start debugging (will stop on entry if breakpoints provided)
        dap.run(config)
        
        -- 🎯 CRITICAL FIX: Set breakpoints AFTER starting but BEFORE continuing
        -- The session is stopped on entry, giving us time to set breakpoints
        local breakpoint_lines = {breakpoint_lines_lua}
        local should_auto_continue = breakpoint_lines and not {str(stop_on_entry).lower()}
        
        if breakpoint_lines and {filepath_lua} then
            -- Wait for session to be stopped on entry
            vim.wait(500, function()
                local session = dap.session()
                return session and session.stopped_thread_id ~= nil
            end)
            
            -- Open the file buffer
            vim.cmd('edit ' .. {filepath_lua})
            local bufnr = vim.fn.bufnr({filepath_lua})
            
            -- Set breakpoints using dap.set_breakpoints (sends to adapter!)
            local breakpoints_to_set = {{}}
            for _, line in ipairs(breakpoint_lines) do
                table.insert(breakpoints_to_set, {{ line = line }})
            end
            
            dap.set_breakpoints(bufnr, breakpoints_to_set)
            
            -- If user didn't request stop_on_entry, continue execution
            -- (we only stopped to set breakpoints)
            if should_auto_continue then
                vim.wait(100)  -- Give breakpoints time to register
                dap.continue()
            end
        end
        
        -- Wait for session to initialize AND process to start
        -- We need both the session and the real PID
        local session = nil
        local wait_result = vim.wait(3000, function()
            session = dap.session()
            return session ~= nil and capture.pid ~= nil
        end, 100)  -- Check every 100ms
        
        -- Clean up listeners
        dap.listeners.after.event_process[process_listener_name] = nil
        dap.listeners.after.event_output[output_listener_name] = nil
        
        if session then
            -- Get captured data
            local pid = capture.pid
            local output = table.concat(capture.output, '')
            
            -- 🎯 CRITICAL: Transfer initial capture to persistent storage
            -- This ensures get_session_status can access the PID/output captured during startup
            _G.otter_dap_persistent_output = _G.otter_dap_persistent_output or {{}}
            local session_key = tostring(session.id)
            _G.otter_dap_persistent_output[session_key] = {{
                pid = pid,
                output = capture.output,  -- Keep as array for appending
            }}
            
            -- Set up persistent listeners for future output
            local process_listener_name = 'otter_persistent_process_' .. session_key
            dap.listeners.after.event_process[process_listener_name] = function(s, body)
                local session_data = _G.otter_dap_persistent_output[session_key]
                if body and body.systemProcessId and session_data then
                    session_data.pid = body.systemProcessId
                end
            end
            
            local output_listener_name = 'otter_persistent_output_' .. session_key
            dap.listeners.after.event_output[output_listener_name] = function(s, body)
                local session_data = _G.otter_dap_persistent_output[session_key]
                if body and body.output and session_data and session_data.output then
                    table.insert(session_data.output, body.output)
                end
            end
            
            -- Clean up listeners when session terminates
            local terminated_listener_name = 'otter_persistent_cleanup_' .. session_key
            dap.listeners.after.event_terminated[terminated_listener_name] = function(s, body)
                dap.listeners.after.event_process[process_listener_name] = nil
                dap.listeners.after.event_output[output_listener_name] = nil
                dap.listeners.after.event_terminated[terminated_listener_name] = nil
                -- Keep the data around briefly so final status can be retrieved
                vim.defer_fn(function()
                    _G.otter_dap_persistent_output[session_key] = nil
                end, 5000)
            end
            
            -- Clean up temporary capture
            _G.otter_dap_capture[capture_id] = nil
            
            -- If we didn't get a PID within timeout, that's suspicious but not fatal
            -- The process might be slow to start
            if not pid then
                -- Fallback: try to get debugpy's PID at least
                if session.client and session.client.server and session.client.server.pid then
                    pid = session.client.server.pid
                end
            end
            
            return {{
                session_id = tostring(session.id or 'unknown'),
                config_name = 'Otter Debug Session',
                file = {filepath_lua},
                module = {module_lua},
                status = 'running',
                pid = pid,
                output = output,
                _capture_id = capture_id,  -- For potential future use
            }}
        else
            -- Clean up global capture on failure
            _G.otter_dap_capture[capture_id] = nil
            
            return {{ error = 'Failed to start debug session (timeout waiting for process)' }}
        end
        """

        try:
            result = await self.execute_lua(lua_code)
            return result
        except Exception as e:
            return {"error": f"Exception starting debug session: {str(e)}"}

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

    async def dap_get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current debug session status with accumulated output and PID.
        
        This queries the running DAP session for updated information including
        output that has been captured since the session started.
        
        Args:
            session_id: Session ID to query
            
        Returns:
            Dict with status, pid, output, etc. or None if session not found
        """
        # The session_id parameter is provided but we need to handle both active and terminated sessions
        lua_code = f"""
        local dap = require('dap')
        _G.otter_dap_persistent_output = _G.otter_dap_persistent_output or {{}}
        
        -- First, try to get the active session
        local session = dap.session()
        local session_key = nil
        local status = 'stopped'
        
        if session and session.id then
            session_key = tostring(session.id)
            status = 'running'
            if session.stopped_thread_id then
                status = 'paused'
            end
        else
            -- Session has terminated, but we might still have cached data
            -- Try all cached sessions (there should only be 1-2 at most)
            for key, _ in pairs(_G.otter_dap_persistent_output) do
                session_key = key
                status = 'stopped'
                break
            end
        end
        
        if not session_key then
            return {{
                status = 'stopped',
                error = 'No session found (active or cached)',
                output = '',
                pid = nil,
            }}
        end
        
        -- Retrieve persistent output
        local session_data = _G.otter_dap_persistent_output[session_key]
        
        if not session_data then
            return {{
                session_id = session_key,
                status = status,
                pid = nil,
                output = '',
                error = 'Session data not found',
            }}
        end
        
        return {{
            session_id = session_key,
            status = status,
            pid = session_data.pid,
            output = table.concat(session_data.output or {{}}, ''),
        }}
        """

        try:
            result = await self.execute_lua(lua_code)
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

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
