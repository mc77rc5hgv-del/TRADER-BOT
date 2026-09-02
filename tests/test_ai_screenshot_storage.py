from pathlib import Path

from app.ai.screenshot_storage import LocalFilesystemStorage


async def test_save_and_delete_roundtrip(tmp_path: Path) -> None:
    storage = LocalFilesystemStorage(tmp_path)

    await storage.save("user1/abc.jpg", b"fake-image-bytes")
    saved_path = tmp_path / "user1" / "abc.jpg"
    assert saved_path.exists()
    assert saved_path.read_bytes() == b"fake-image-bytes"

    await storage.delete("user1/abc.jpg")
    assert not saved_path.exists()


async def test_delete_missing_key_is_a_noop(tmp_path: Path) -> None:
    storage = LocalFilesystemStorage(tmp_path)
    await storage.delete("does/not/exist.jpg")  # must not raise


def test_base_dir_created_on_init(tmp_path: Path) -> None:
    nested = tmp_path / "nested" / "dir"
    LocalFilesystemStorage(nested)
    assert nested.exists()
