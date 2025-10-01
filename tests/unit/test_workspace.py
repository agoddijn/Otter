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
        
        # Check that we have the root directory
        assert len(result.tree) == 1
        root_name = temp_project_dir.name
        assert root_name in result.tree
        
        # Check that it's a directory
        root_entry = result.tree[root_name]
        assert root_entry["type"] == "directory"
        assert "children" in root_entry
    
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
        root_name = temp_project_dir.name
        src = result.tree[root_name]["children"]["src"]
        
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
        
        root_name = temp_project_dir.name
        children = result.tree[root_name]["children"]
        
        # Should see src, tests, README.md but not contents of src
        assert "src" in children
        assert "tests" in children
        assert "README.md" in children
        
        # src should be truncated
        src_entry = children["src"]
        assert src_entry["type"] == "directory"
        assert "truncated" in src_entry
        assert src_entry["truncated"] is True
    
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
        
        root_name = temp_project_dir.name
        readme = result.tree[root_name]["children"]["README.md"]
        
        assert readme["type"] == "file"
        assert "size" in readme
        assert isinstance(readme["size"], int)
        assert readme["size"] > 0
    
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
        
        root_name = temp_project_dir.name
        readme = result.tree[root_name]["children"]["README.md"]
        
        assert readme["type"] == "file"
        assert "size" not in readme
    
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
        
        root_name = temp_project_dir.name
        children = result.tree[root_name]["children"]
        
        # .gitignore should NOT be present
        assert ".gitignore" not in children
    
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
        
        root_name = temp_project_dir.name
        children = result.tree[root_name]["children"]
        
        # .gitignore SHOULD be present
        assert ".gitignore" in children
        assert children[".gitignore"]["type"] == "file"
    
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
        
        root_name = temp_project_dir.name
        src = result.tree[root_name]["children"]["src"]
        
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
        
        # Should have empty children
        root_name = empty_project_dir.name
        assert root_name in result.tree
        assert result.tree[root_name]["type"] == "directory"
        assert result.tree[root_name]["children"] == {}
    
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
        
        # Should start from src directory
        assert "src" in result.tree
        src = result.tree["src"]
        
        assert src["type"] == "directory"
        assert "main.py" in src["children"]
        assert "utils" in src["children"]
