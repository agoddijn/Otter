"""Pytest configuration and shared fixtures."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest

from tests.fixtures.language_configs import (
    LANGUAGE_CONFIGS,
    LanguageTestConfig,
    get_all_languages,
)


def pytest_generate_tests(metafunc):
    """Generate parameterized tests for all supported languages.
    
    If a test has a 'language_config' fixture, it will be parameterized
    to run once for each supported language (Python, JavaScript, Rust).
    """
    if "language_config" in metafunc.fixturenames:
        languages = get_all_languages()
        metafunc.parametrize(
            "language_config",
            [LANGUAGE_CONFIGS[lang] for lang in languages],
            ids=languages,
            indirect=True,
        )


@pytest.fixture
def language_config(request) -> LanguageTestConfig:
    """Provide language-specific configuration for parameterized tests.
    
    This fixture is automatically parameterized by pytest_generate_tests
    to run tests across all supported languages.
    """
    return request.param


@pytest.fixture
def language_project_dir(language_config: LanguageTestConfig) -> Path:
    """Get the path to the language-specific test project directory.
    
    Returns the path to a physical test project directory for the given language:
        - tests/fixtures/projects/python/
        - tests/fixtures/projects/javascript/
        - tests/fixtures/projects/rust/
    
    Each directory contains a complete mini test project in that language.
    """
    test_dir = Path(__file__).parent
    project_dir = test_dir / "fixtures" / "projects" / language_config.language
    
    if not project_dir.exists():
        raise RuntimeError(
            f"Test project directory not found for {language_config.language}: {project_dir}"
        )
    
    return project_dir


@pytest.fixture
def temp_project_dir() -> Generator[Path, None, None]:
    """Create a temporary project directory with test structure (Python-specific).
    
    Creates:
        temp_dir/
            src/
                main.py
                utils/
                    helper.py
            tests/
                test_main.py
            README.md
            .gitignore
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_root = Path(tmp_dir)
        
        # Create directory structure
        src_dir = project_root / "src"
        utils_dir = src_dir / "utils"
        tests_dir = project_root / "tests"
        
        src_dir.mkdir()
        utils_dir.mkdir()
        tests_dir.mkdir()
        
        # Create files with content
        (src_dir / "main.py").write_text("def main():\n    print('Hello')\n")
        (utils_dir / "helper.py").write_text("def help():\n    pass\n")
        (tests_dir / "test_main.py").write_text("def test_main():\n    assert True\n")
        (project_root / "README.md").write_text("# Test Project\n")
        (project_root / ".gitignore").write_text("__pycache__/\n*.pyc\n")
        
        # Create a __pycache__ directory that should be ignored
        pycache_dir = src_dir / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "main.cpython-311.pyc").write_text("binary")
        
        yield project_root


@pytest.fixture
def empty_project_dir() -> Generator[Path, None, None]:
    """Create an empty temporary directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)
