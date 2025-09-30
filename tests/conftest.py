"""Pytest configuration and shared fixtures."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_project_dir() -> Generator[Path, None, None]:
    """Create a temporary project directory with test structure.
    
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
