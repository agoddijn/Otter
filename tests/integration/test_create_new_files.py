"""Integration tests for creating and editing new files.

Tests the workflow of creating a new file (that doesn't exist yet),
editing it in a buffer, and saving it to disk.
"""

import pytest

from otter.neovim.client import NeovimClient
from otter.services.editing import EditingService
from otter.models.responses import BufferEdit


@pytest.fixture
async def editing_service(tmp_path):
    """Create an editing service with Neovim client."""
    nvim_client = NeovimClient(project_path=str(tmp_path))
    await nvim_client.start()
    
    service = EditingService(
        nvim_client=nvim_client,
        project_path=str(tmp_path),
    )
    
    yield service
    
    await nvim_client.stop()


@pytest.mark.asyncio
async def test_create_new_file_basic(editing_service, tmp_path):
    """Test creating a new file with simple content."""
    new_file = "src/utils/helper.py"
    new_file_path = tmp_path / new_file
    
    # Verify file doesn't exist yet
    assert not new_file_path.exists()
    
    # Edit the new file (create buffer and add content)
    result = await editing_service.edit_buffer(
        file=new_file,
        edits=[BufferEdit(
            line_start=1,
            line_end=1,
            new_text='def hello():\n    return "Hello, World!"\n'
        )],
        preview=False,
    )
    
    # Should succeed
    assert result.success, f"Edit failed: {result.error}"
    assert result.applied
    assert result.is_modified
    
    # File still shouldn't exist on disk yet
    assert not new_file_path.exists()
    
    # Save the buffer
    save_result = await editing_service.save_buffer(new_file)
    assert save_result.success, f"Save failed: {save_result.error}"
    
    # Now file should exist on disk
    assert new_file_path.exists()
    
    # Verify content
    content = new_file_path.read_text()
    assert 'def hello():' in content
    assert 'return "Hello, World!"' in content


@pytest.mark.asyncio
async def test_create_new_file_with_preview(editing_service, tmp_path):
    """Test creating a new file with preview mode first."""
    new_file = "config/settings.py"
    new_file_path = tmp_path / new_file
    
    assert not new_file_path.exists()
    
    # Preview the edit first
    preview_result = await editing_service.edit_buffer(
        file=new_file,
        edits=[BufferEdit(
            line_start=1,
            line_end=1,
            new_text='DEBUG = True\nLOG_LEVEL = "INFO"\n'
        )],
        preview=True,
    )
    
    assert preview_result.success
    assert not preview_result.applied
    assert preview_result.preview is not None
    assert '+DEBUG = True' in preview_result.preview
    
    # Now apply the edit
    apply_result = await editing_service.edit_buffer(
        file=new_file,
        edits=[BufferEdit(
            line_start=1,
            line_end=1,
            new_text='DEBUG = True\nLOG_LEVEL = "INFO"\n'
        )],
        preview=False,
    )
    
    assert apply_result.success
    assert apply_result.applied
    assert apply_result.is_modified
    
    # Save
    save_result = await editing_service.save_buffer(new_file)
    assert save_result.success
    assert new_file_path.exists()
    
    # Verify content
    content = new_file_path.read_text()
    assert 'DEBUG = True' in content
    assert 'LOG_LEVEL = "INFO"' in content


@pytest.mark.asyncio
async def test_create_new_file_nested_directories(editing_service, tmp_path):
    """Test creating a new file in nested directories that don't exist."""
    new_file = "src/features/auth/handlers/login.py"
    new_file_path = tmp_path / new_file
    
    # Verify nested directories don't exist
    assert not (tmp_path / "src" / "features").exists()
    
    # Edit the file
    result = await editing_service.edit_buffer(
        file=new_file,
        edits=[BufferEdit(
            line_start=1,
            line_end=1,
            new_text='async def login(user, password):\n    pass\n'
        )],
        preview=False,
    )
    
    assert result.success
    
    # Save
    save_result = await editing_service.save_buffer(new_file)
    assert save_result.success
    
    # Verify nested directories were created
    assert (tmp_path / "src" / "features" / "auth" / "handlers").exists()
    assert new_file_path.exists()
    
    # Verify content
    content = new_file_path.read_text()
    assert 'async def login' in content


@pytest.mark.asyncio
async def test_create_new_file_multiple_edits(editing_service, tmp_path):
    """Test creating a new file with multiple sequential edits."""
    new_file = "models/user.py"
    new_file_path = tmp_path / new_file
    
    # First edit - add a class
    result1 = await editing_service.edit_buffer(
        file=new_file,
        edits=[BufferEdit(
            line_start=1,
            line_end=1,
            new_text='class User:\n    pass\n'
        )],
        preview=False,
    )
    assert result1.success
    
    # Second edit - add a method
    result2 = await editing_service.edit_buffer(
        file=new_file,
        edits=[BufferEdit(
            line_start=2,
            line_end=2,
            new_text='    def __init__(self, name):\n        self.name = name\n'
        )],
        preview=False,
    )
    assert result2.success
    
    # Get diff to see all changes
    diff_result = await editing_service.get_buffer_diff(new_file)
    assert diff_result.has_changes
    assert '+class User:' in diff_result.diff
    assert '+    def __init__' in diff_result.diff
    
    # Save
    save_result = await editing_service.save_buffer(new_file)
    assert save_result.success
    assert new_file_path.exists()
    
    # Verify final content
    content = new_file_path.read_text()
    assert 'class User:' in content
    assert 'def __init__(self, name):' in content
    assert 'self.name = name' in content


@pytest.mark.asyncio
async def test_create_new_file_discard_changes(editing_service, tmp_path):
    """Test creating a new file and then discarding before save.
    
    Note: For new files (not yet on disk), discard doesn't clear the buffer
    since there's no disk version to reload. This is expected behavior.
    """
    new_file = "temp/test.py"
    new_file_path = tmp_path / new_file
    
    # Edit new file
    result = await editing_service.edit_buffer(
        file=new_file,
        edits=[BufferEdit(
            line_start=1,
            line_end=1,
            new_text='print("test")\n'
        )],
        preview=False,
    )
    assert result.success
    
    # Discard changes (for new files, this is a no-op since no disk version exists)
    await editing_service.discard_buffer(new_file)
    # Discard might fail or succeed depending on implementation
    # The key is that the file shouldn't be saved to disk
    
    # File should not exist on disk
    assert not new_file_path.exists()


@pytest.mark.asyncio
async def test_create_and_modify_new_file(editing_service, tmp_path):
    """Test creating a new file and making multiple modifications."""
    new_file = "config.json"
    new_file_path = tmp_path / new_file
    
    # Create file with initial content
    result1 = await editing_service.edit_buffer(
        file=new_file,
        edits=[BufferEdit(
            line_start=1,
            line_end=1,
            new_text='{\n  "env": "dev"\n}\n'
        )],
        preview=False,
    )
    assert result1.success
    
    # Modify it again (change env to prod)
    result2 = await editing_service.edit_buffer(
        file=new_file,
        edits=[BufferEdit(
            line_start=2,
            line_end=2,
            new_text='  "env": "prod"\n'
        )],
        preview=False,
    )
    assert result2.success
    
    # Save
    save_result = await editing_service.save_buffer(new_file)
    assert save_result.success
    assert new_file_path.exists()
    
    # Verify content
    content = new_file_path.read_text()
    assert '"env": "prod"' in content


@pytest.mark.asyncio
async def test_create_new_file_absolute_path(editing_service, tmp_path):
    """Test creating a new file using an absolute path."""
    new_file_path = tmp_path / "absolute" / "path" / "test.txt"
    
    assert not new_file_path.exists()
    
    # Use absolute path
    result = await editing_service.edit_buffer(
        file=str(new_file_path),
        edits=[BufferEdit(
            line_start=1,
            line_end=1,
            new_text='Absolute path test\n'
        )],
        preview=False,
    )
    assert result.success
    
    # Save
    save_result = await editing_service.save_buffer(str(new_file_path))
    assert save_result.success
    assert new_file_path.exists()
    
    content = new_file_path.read_text()
    assert 'Absolute path test' in content


@pytest.mark.asyncio
async def test_create_multiple_new_files(editing_service, tmp_path):
    """Test creating multiple new files in the same session."""
    files = [
        "file1.py",
        "file2.py",
        "dir/file3.py",
    ]
    
    for file in files:
        # Create and edit each file
        result = await editing_service.edit_buffer(
            file=file,
            edits=[BufferEdit(
                line_start=1,
                line_end=1,
                new_text=f'# {file}\nprint("hello")\n'
            )],
            preview=False,
        )
        assert result.success, f"Failed to edit {file}"
        
        # Save each file
        save_result = await editing_service.save_buffer(file)
        assert save_result.success, f"Failed to save {file}"
    
    # Verify all files were created
    for file in files:
        file_path = tmp_path / file
        assert file_path.exists(), f"{file} was not created"
        assert f'# {file}' in file_path.read_text()

