"""Bootstrap utilities for setting up Otter's environment."""

from .lsp_installer import (
    check_and_install_lsp_servers,
    check_lsp_server,
    check_prerequisites,
    print_missing_prerequisites,
    LSPServerStatus,
)

from .dap_installer import (
    DAPAdapterStatus,
    check_dap_adapter,
    check_and_install_dap_adapter,
    ensure_dap_adapter,
    DAP_ADAPTER_INFO,
)

__all__ = [
    # LSP
    "check_and_install_lsp_servers",
    "check_lsp_server",
    "check_prerequisites",
    "print_missing_prerequisites",
    "LSPServerStatus",
    # DAP
    "DAPAdapterStatus",
    "check_dap_adapter",
    "check_and_install_dap_adapter",
    "ensure_dap_adapter",
    "DAP_ADAPTER_INFO",
]

