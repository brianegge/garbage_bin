from PIL import Image

import garbage_bin.detect as detect
from garbage_bin.detect import save, sync_local_to_remote

DATE_DIR = "20260207"


def test_save_returns_true_on_nfs(tmp_path):
    img = Image.new("RGB", (10, 10))
    result = save(str(tmp_path), img, {"car": 0.9, "something": 0.5})
    assert result is True


def test_save_returns_false_on_unwritable_nfs(tmp_path, monkeypatch):
    local = tmp_path / "local"
    local.mkdir()
    monkeypatch.setattr(detect, "LOCAL_FALLBACK", str(local))

    nfs_path = tmp_path / "nfs"
    nfs_path.mkdir()
    nfs_path.chmod(0o555)

    img = Image.new("RGB", (10, 10))
    try:
        result = save(str(nfs_path), img, {"car": 0.9, "something": 0.5})
        assert result is False
        # Verify files were written to local fallback
        files = list(local.rglob("*.jpg"))
        assert len(files) == 1
    finally:
        nfs_path.chmod(0o755)


def test_save_returns_false_when_both_paths_fail(tmp_path, monkeypatch):
    nfs_path = tmp_path / "nfs"
    nfs_path.mkdir()
    nfs_path.chmod(0o555)

    local_path = tmp_path / "local"
    local_path.mkdir()
    local_path.chmod(0o555)

    monkeypatch.setattr(detect, "LOCAL_FALLBACK", str(local_path))
    img = Image.new("RGB", (10, 10))
    try:
        result = save(str(nfs_path), img, {"car": 0.9, "something": 0.5})
        assert result is False
    finally:
        nfs_path.chmod(0o755)
        local_path.chmod(0o755)


def test_sync_local_to_remote_moves_files(tmp_path, monkeypatch):
    local = tmp_path / "local"
    datedir = local / DATE_DIR
    datedir.mkdir(parents=True)
    (datedir / "test.jpg").write_text("image data")
    monkeypatch.setattr(detect, "LOCAL_FALLBACK", str(local))

    remote = tmp_path / "remote"
    remote.mkdir()
    result = sync_local_to_remote(str(remote))
    assert result is True
    assert (remote / DATE_DIR / "test.jpg").exists()
    assert not (datedir / "test.jpg").exists()


def test_sync_local_to_remote_returns_false_on_unwritable(tmp_path, monkeypatch):
    local = tmp_path / "local"
    datedir = local / DATE_DIR
    datedir.mkdir(parents=True)
    (datedir / "test.jpg").write_text("image data")
    monkeypatch.setattr(detect, "LOCAL_FALLBACK", str(local))

    remote = tmp_path / "remote"
    remote.mkdir()
    remote.chmod(0o555)

    try:
        result = sync_local_to_remote(str(remote))
        assert result is False
        # File should still be in local
        assert (datedir / "test.jpg").exists()
    finally:
        remote.chmod(0o755)


def test_sync_local_to_remote_handles_collision(tmp_path, monkeypatch):
    local = tmp_path / "local"
    datedir = local / DATE_DIR
    datedir.mkdir(parents=True)
    (datedir / "test.jpg").write_text("new data")
    monkeypatch.setattr(detect, "LOCAL_FALLBACK", str(local))

    remote = tmp_path / "remote"
    remote_datedir = remote / DATE_DIR
    remote_datedir.mkdir(parents=True)
    (remote_datedir / "test.jpg").write_text("existing data")

    result = sync_local_to_remote(str(remote))
    assert result is True
    # Original should be preserved
    assert (remote_datedir / "test.jpg").read_text() == "existing data"
    # New file should be renamed
    assert (remote_datedir / "test_1.jpg").read_text() == "new data"


def test_sync_returns_true_when_no_local_fallback(tmp_path, monkeypatch):
    nonexistent = tmp_path / "nonexistent_fallback"
    monkeypatch.setattr(detect, "LOCAL_FALLBACK", str(nonexistent))
    result = sync_local_to_remote(str(tmp_path / "some_remote"))
    assert result is True
