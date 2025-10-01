"""Language-specific test configurations and fixture data.

This module provides test data for multiple languages to enable parameterized testing
across Python, JavaScript, and Rust.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class SymbolLocation:
    """Expected location of a symbol in test code."""
    name: str
    symbol_type: str  # class, function, method, variable, etc.
    line: int
    file: str


@dataclass
class LanguageTestConfig:
    """Configuration for language-specific tests.
    
    Each configuration corresponds to a physical test project directory:
    - tests/fixtures/projects/python/
    - tests/fixtures/projects/javascript/
    - tests/fixtures/projects/rust/
    """
    language: str
    file_extension: str
    lsp_server: str
    
    # Expected symbols for symbol tests
    expected_classes: List[str]
    expected_functions: List[str]
    expected_methods: List[str]
    
    # Symbol locations for navigation tests
    symbol_locations: Dict[str, SymbolLocation]


# Python test configuration
# Corresponds to: tests/fixtures/projects/python/
PYTHON_CONFIG = LanguageTestConfig(
    language="python",
    file_extension=".py",
    lsp_server="pyright",
    expected_classes=["User", "UserService"],
    expected_functions=["create_user", "main"],
    expected_methods=["__init__", "greet", "get_user", "process_user"],
    symbol_locations={
        "User": SymbolLocation("User", "class", 3, "models"),
        "create_user": SymbolLocation("create_user", "function", 13, "models"),
        "greet": SymbolLocation("greet", "method", 9, "models"),
        "UserService": SymbolLocation("UserService", "class", 4, "services"),
    }
)


# JavaScript test configuration
# Corresponds to: tests/fixtures/projects/javascript/
JAVASCRIPT_CONFIG = LanguageTestConfig(
    language="javascript",
    file_extension=".js",
    lsp_server="typescript-language-server",
    expected_classes=["User", "UserService"],
    expected_functions=["createUser", "main"],
    expected_methods=["constructor", "greet", "getUser", "processUser"],
    symbol_locations={
        "User": SymbolLocation("User", "class", 5, "models"),
        "createUser": SymbolLocation("createUser", "function", 31, "models"),
        "greet": SymbolLocation("greet", "method", 19, "models"),
        "UserService": SymbolLocation("UserService", "class", 6, "services"),
    }
)


# Rust test configuration
# Corresponds to: tests/fixtures/projects/rust/
RUST_CONFIG = LanguageTestConfig(
    language="rust",
    file_extension=".rs",
    lsp_server="rust-analyzer",
    expected_classes=["User", "UserService"],  # structs in Rust
    expected_functions=["create_user", "main"],
    expected_methods=["new", "greet", "get_user", "process_user"],
    symbol_locations={
        "User": SymbolLocation("User", "struct", 4, "models"),
        "create_user": SymbolLocation("create_user", "function", 21, "models"),
        "greet": SymbolLocation("greet", "method", 15, "models"),
        "UserService": SymbolLocation("UserService", "struct", 4, "services"),
    }
)


# Map of all language configurations
LANGUAGE_CONFIGS = {
    "python": PYTHON_CONFIG,
    "javascript": JAVASCRIPT_CONFIG,
    "rust": RUST_CONFIG,
}


def get_language_config(language: str) -> LanguageTestConfig:
    """Get the test configuration for a specific language."""
    if language not in LANGUAGE_CONFIGS:
        raise ValueError(f"Unsupported language: {language}")
    return LANGUAGE_CONFIGS[language]


def get_all_languages() -> List[str]:
    """Get list of all supported languages for parameterized testing."""
    return list(LANGUAGE_CONFIGS.keys())

