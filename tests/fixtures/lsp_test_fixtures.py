"""Shared fixtures for LSP-dependent integration tests.

This module provides robust fixtures for LSP-dependent tests using
smart LSP readiness polling instead of arbitrary delays.
"""

import asyncio
import os
import pytest
from pathlib import Path

from otter.neovim.client import NeovimClient
from otter.neovim.lsp_readiness import wait_for_all_lsp_ready


# Configuration
LSP_READINESS_TIMEOUT = float(os.getenv("LSP_READINESS_TIMEOUT", "15.0"))  # Per file timeout
LSP_VERBOSE = os.getenv("LSP_VERBOSE", "0") == "1"  # Set LSP_VERBOSE=1 for debug output


@pytest.fixture
async def nvim_client_with_lsp(language_project_dir, language_config):
    """Create a Neovim client with LSP fully initialized and indexed.
    
    This fixture uses smart polling to wait for LSP readiness:
    1. Starts Neovim with the project
    2. Opens all test files
    3. Polls LSP status until clients are attached and initialized
    4. Verifies files are indexed (can provide document symbols)
    
    The polling approach is deterministic and adapts to different system speeds.
    Set LSP_VERBOSE=1 environment variable to see detailed progress.
    
    Args:
        language_project_dir: Path to the language-specific test project
        language_config: Language test configuration
        
    Yields:
        NeovimClient with LSP fully initialized and files indexed
    """
    nvim_client = NeovimClient(project_path=str(language_project_dir))
    
    try:
        await nvim_client.start()
        
        # Get all test files for this language
        ext = language_config.file_extension
        test_files = [
            str(language_project_dir / f"models{ext}"),
            str(language_project_dir / f"services{ext}"),
            str(language_project_dir / f"main{ext}"),
        ]
        
        # Wait for LSP to be ready for all files (with polling)
        lsp_ready = await wait_for_all_lsp_ready(
            nvim_client,
            test_files,
            timeout=LSP_READINESS_TIMEOUT,
            use_indexing_check=True,  # Verify files are indexed
            verbose=LSP_VERBOSE,
        )
        
        if not lsp_ready:
            pytest.skip(
                f"LSP server for {language_config.language} not ready within {LSP_READINESS_TIMEOUT}s timeout. "
                f"Server: {language_config.lsp_server}. "
                f"Set LSP_VERBOSE=1 to see detailed polling output."
            )
        
        yield nvim_client
        
    finally:
        await nvim_client.stop()


@pytest.fixture
async def nvim_client_with_lsp_basic(language_project_dir):
    """Create a Neovim client with basic LSP readiness check.
    
    This is a lighter-weight version that just checks LSP is attached,
    without waiting for full file indexing.
    
    Args:
        language_project_dir: Path to the language-specific test project
        
    Yields:
        NeovimClient with LSP attached
    """
    from otter.neovim.lsp_readiness import wait_for_lsp_ready
    
    nvim_client = NeovimClient(project_path=str(language_project_dir))
    
    try:
        await nvim_client.start()
        
        # Just check that LSP is attached to at least one file
        # Find any source file
        source_files = list(language_project_dir.glob("*.py")) + \
                      list(language_project_dir.glob("*.js")) + \
                      list(language_project_dir.glob("*.rs"))
        
        if source_files:
            lsp_ready = await wait_for_lsp_ready(
                nvim_client,
                str(source_files[0]),
                timeout=15.0
            )
            
            if not lsp_ready:
                pytest.skip("LSP server not ready within timeout")
        
        yield nvim_client
        
    finally:
        await nvim_client.stop()

