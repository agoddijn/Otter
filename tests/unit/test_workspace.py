"""Unit tests for workspace service."""

import pytest
from pathlib import Path

from otter.services.workspace import WorkspaceService
from otter.models.responses import ProjectTree


class TestGetProjectStructure:
    """Tests for get_project_structure method."""
    
    @pytest.mark.asyncio
    async def test_basic_structure(self, temp_project_dir: Path):
        """Test basic project structure retrieval."""
        workspace = WorkspaceService(project_path=str(temp_project_dir))
        
        result = await workspace.get_project_structure(
            path=".",
            max_depth=3,
            show_hidden=False,
            include_sizes=True
        )
        
        assert isinstance(result, ProjectTree)
        assert result.root == str(temp_project_dir.resolve())
        assert isinstance(result.tree, dict)
        
        # Check metadata
        assert result.file_count > 0
        assert result.directory_count > 0
        assert result.total_size > 0
        
        # Tree should contain direct children (no root wrapper)
        assert "src" in result.tree
        assert "tests" in result.tree
        assert "README.md" in result.tree
        
        # Check directory structure
        assert result.tree["src"]["type"] == "directory"
        assert "children" in result.tree["src"]
    
    @pytest.mark.asyncio
    async def test_hides_pycache(self, temp_project_dir: Path):
        """Test that __pycache__ directories are excluded."""
        workspace = WorkspaceService(project_path=str(temp_project_dir))
        
        result = await workspace.get_project_structure(
            path=".",
            max_depth=3,
            show_hidden=False,
            include_sizes=False
        )
        
        # Navigate to src directory
        src = result.tree["src"]
        
        # Verify __pycache__ is NOT in the children
        assert "__pycache__" not in src["children"]
    
    @pytest.mark.asyncio
    async def test_respects_max_depth(self, temp_project_dir: Path):
        """Test that max_depth is respected."""
        workspace = WorkspaceService(project_path=str(temp_project_dir))
        
        # With depth 1, should only see top level
        result = await workspace.get_project_structure(
            path=".",
            max_depth=1,
            show_hidden=False,
            include_sizes=False
        )
        
        # Should see src, tests, README.md but not contents of src
        assert "src" in result.tree
        assert "tests" in result.tree
        assert "README.md" in result.tree
        
        # src should be truncated
        src_entry = result.tree["src"]
        assert src_entry["type"] == "directory"
        assert "children_truncated" in src_entry
        assert src_entry["children_truncated"] is True
    
    @pytest.mark.asyncio
    async def test_includes_file_sizes(self, temp_project_dir: Path):
        """Test that file sizes are included when requested."""
        workspace = WorkspaceService(project_path=str(temp_project_dir))
        
        result = await workspace.get_project_structure(
            path=".",
            max_depth=2,
            show_hidden=False,
            include_sizes=True
        )
        
        readme = result.tree["README.md"]
        
        assert readme["type"] == "file"
        assert "size" in readme
        assert isinstance(readme["size"], int)
        assert readme["size"] > 0
        
        # Check metadata total_size is populated
        assert result.total_size > 0
    
    @pytest.mark.asyncio
    async def test_excludes_file_sizes(self, temp_project_dir: Path):
        """Test that file sizes are excluded when not requested."""
        workspace = WorkspaceService(project_path=str(temp_project_dir))
        
        result = await workspace.get_project_structure(
            path=".",
            max_depth=2,
            show_hidden=False,
            include_sizes=False
        )
        
        readme = result.tree["README.md"]
        
        assert readme["type"] == "file"
        assert "size" not in readme
        
        # Check metadata total_size is 0 when sizes not included
        assert result.total_size == 0
    
    @pytest.mark.asyncio
    async def test_hides_hidden_files(self, temp_project_dir: Path):
        """Test that hidden files are excluded by default."""
        workspace = WorkspaceService(project_path=str(temp_project_dir))
        
        result = await workspace.get_project_structure(
            path=".",
            max_depth=2,
            show_hidden=False,
            include_sizes=False
        )
        
        # .gitignore should NOT be present
        assert ".gitignore" not in result.tree
    
    @pytest.mark.asyncio
    async def test_shows_hidden_files(self, temp_project_dir: Path):
        """Test that hidden files are included when requested."""
        workspace = WorkspaceService(project_path=str(temp_project_dir))
        
        result = await workspace.get_project_structure(
            path=".",
            max_depth=2,
            show_hidden=True,
            include_sizes=False
        )
        
        # .gitignore SHOULD be present
        assert ".gitignore" in result.tree
        assert result.tree[".gitignore"]["type"] == "file"
    
    @pytest.mark.asyncio
    async def test_nested_directories(self, temp_project_dir: Path):
        """Test that nested directories are properly represented."""
        workspace = WorkspaceService(project_path=str(temp_project_dir))
        
        result = await workspace.get_project_structure(
            path=".",
            max_depth=3,
            show_hidden=False,
            include_sizes=False
        )
        
        src = result.tree["src"]
        
        # Should have utils directory
        assert "utils" in src["children"]
        utils = src["children"]["utils"]
        
        assert utils["type"] == "directory"
        assert "children" in utils
        assert "helper.py" in utils["children"]
        assert utils["children"]["helper.py"]["type"] == "file"
    
    @pytest.mark.asyncio
    async def test_empty_directory(self, empty_project_dir: Path):
        """Test handling of empty directory."""
        workspace = WorkspaceService(project_path=str(empty_project_dir))
        
        result = await workspace.get_project_structure(
            path=".",
            max_depth=2,
            show_hidden=False,
            include_sizes=False
        )
        
        assert isinstance(result, ProjectTree)
        assert result.root == str(empty_project_dir.resolve())
        
        # Should have empty tree
        assert result.tree == {}
        assert result.file_count == 0
        assert result.directory_count == 0
    
    @pytest.mark.asyncio
    async def test_relative_path(self, temp_project_dir: Path):
        """Test getting structure of a subdirectory."""
        workspace = WorkspaceService(project_path=str(temp_project_dir))
        
        result = await workspace.get_project_structure(
            path="src",
            max_depth=2,
            show_hidden=False,
            include_sizes=False
        )
        
        # Root should be the src directory, tree contains its children
        assert result.root.endswith("/src")
        
        # Tree should contain direct children of src (no wrapper)
        assert "main.py" in result.tree
        assert "utils" in result.tree
        assert result.tree["main.py"]["type"] == "file"
        assert result.tree["utils"]["type"] == "directory"
    
    @pytest.mark.asyncio
    async def test_exclude_patterns(self, temp_project_dir: Path):
        """Test that exclude patterns work."""
        workspace = WorkspaceService(project_path=str(temp_project_dir))
        
        result = await workspace.get_project_structure(
            path=".",
            max_depth=3,
            show_hidden=False,
            include_sizes=False,
            exclude_patterns=["*.md"]
        )
        
        # README.md should be excluded
        assert "README.md" not in result.tree
        
        # Other files should still be present
        assert "src" in result.tree
