import os

from PIL import Image

import garbage_bin.detect as detect
from garbage_bin.detect import save, sync_local_to_remote

# Permission mode constants
READ_ONLY_DIR_MODE = 0o555  # Read and execute, no write
WRITABLE_DIR_MODE = 0o755  # Read, write, and execute


def test_save_returns_true_on_nfs(tmp_path):
    img = Image.new("RGB", (10, 10))
    result = save(str(tmp_path), img, {"car": 0.9, "something": 0.5})
    assert result is True


def test_save_returns_false_on_unwritable_nfs(tmp_path, monkeypatch):
    local = tmp_path / "local"
    local.mkdir()
    monkeypatch.setattr(detect, "LOCAL_FALLBACK", str(local))

    # Create an unwritable NFS path using tmp_path
    nfs_path = tmp_path / "nfs"
    nfs_path.mkdir()
    os.chmod(nfs_path, READ_ONLY_DIR_MODE)  # Make read-only to prevent file creation

    img = Image.new("RGB", (10, 10))
    try:
        result = save(str(nfs_path), img, {"car": 0.9, "something": 0.5})
        assert result is False
        # Verify files were written to local fallback
        files = list(local.rglob("*.jpg"))
        assert len(files) == 1
    finally:
        # Restore permissions for cleanup
        os.chmod(nfs_path, WRITABLE_DIR_MODE)


def test_save_returns_false_when_both_paths_fail(tmp_path, monkeypatch):
    # Create unwritable paths using tmp_path
    nfs_path = tmp_path / "nfs"
    nfs_path.mkdir()
    os.chmod(nfs_path, READ_ONLY_DIR_MODE)  # Make read-only

    local_path = tmp_path / "local"
    local_path.mkdir()
    os.chmod(local_path, READ_ONLY_DIR_MODE)  # Make read-only

    monkeypatch.setattr(detect, "LOCAL_FALLBACK", str(local_path))
    img = Image.new("RGB", (10, 10))
    try:
        result = save(str(nfs_path), img, {"car": 0.9, "something": 0.5})
        assert result is False
    finally:
        # Restore permissions for cleanup
        os.chmod(nfs_path, WRITABLE_DIR_MODE)
        os.chmod(local_path, WRITABLE_DIR_MODE)


def test_sync_local_to_remote_moves_files(tmp_path, monkeypatch):
    local = tmp_path / "local"
    datedir = local / "20260207"
    datedir.mkdir(parents=True)
    (datedir / "test.jpg").write_text("image data")
    monkeypatch.setattr(detect, "LOCAL_FALLBACK", str(local))

    remote = tmp_path / "remote"
    remote.mkdir()
    result = sync_local_to_remote(str(remote))
    assert result is True
    assert (remote / "20260207" / "test.jpg").exists()
    assert not (datedir / "test.jpg").exists()


def test_sync_local_to_remote_returns_false_on_unwritable(tmp_path, monkeypatch):
    local = tmp_path / "local"
    datedir = local / "20260207"
    datedir.mkdir(parents=True)
    (datedir / "test.jpg").write_text("image data")
    monkeypatch.setattr(detect, "LOCAL_FALLBACK", str(local))

    # Create unwritable remote path
    remote = tmp_path / "remote"
    remote.mkdir()
    os.chmod(remote, READ_ONLY_DIR_MODE)  # Make read-only

    try:
        result = sync_local_to_remote(str(remote))
        assert result is False
        # File should still be in local
        assert (datedir / "test.jpg").exists()
    finally:
        # Restore permissions for cleanup
        os.chmod(remote, WRITABLE_DIR_MODE)


def test_sync_local_to_remote_handles_collision(tmp_path, monkeypatch):
    local = tmp_path / "local"
    datedir = local / "20260207"
    datedir.mkdir(parents=True)
    (datedir / "test.jpg").write_text("new data")
    monkeypatch.setattr(detect, "LOCAL_FALLBACK", str(local))

    remote = tmp_path / "remote"
    remote_datedir = remote / "20260207"
    remote_datedir.mkdir(parents=True)
    (remote_datedir / "test.jpg").write_text("existing data")

    result = sync_local_to_remote(str(remote))
    assert result is True
    # Original should be preserved
    assert (remote_datedir / "test.jpg").read_text() == "existing data"
    # New file should be renamed
    assert (remote_datedir / "test_1.jpg").read_text() == "new data"


def test_sync_returns_true_when_no_local_fallback(tmp_path, monkeypatch):
    # Use a non-existent subdirectory within tmp_path instead of absolute path
    nonexistent = tmp_path / "nonexistent_fallback"
    monkeypatch.setattr(detect, "LOCAL_FALLBACK", str(nonexistent))
    result = sync_local_to_remote(str(tmp_path / "some_remote"))
    assert result is True
