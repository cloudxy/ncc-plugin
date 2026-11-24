import base64

import pytest

from ncc_shared.serialization import digest
from ncc_shared.workspace import MARKER, STATE, read_metadata, scan_files, write_metadata, write_snapshot


def snapshot(path="chapter.md", body=b"synthetic"):
    return {
        "version": 1,
        "files": [{"path": path, "base64": base64.b64encode(body).decode(), "sha256": digest(body)}],
    }


@pytest.mark.parametrize(
    "bad", ["../outside.txt", "/outside.txt", ".env", ".env.local", MARKER, ".git/config"]
)
def test_all_paths_validated_before_any_write_or_delete(tmp_path, bad):
    root = tmp_path / "book"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("preserved")
    with pytest.raises(ValueError):
        write_snapshot(root, snapshot(), [bad])
    assert outside.read_text() == "preserved" and not (root / "chapter.md").exists()
    with pytest.raises(ValueError):
        write_snapshot(root, snapshot(bad))


@pytest.mark.parametrize("metadata", [MARKER, STATE])
def test_metadata_symlinks_never_read_or_overwrite_outside(tmp_path, metadata):
    root = tmp_path / "book"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.write_text('"original"')
    (root / metadata).symlink_to(outside)
    for action in (
        lambda: scan_files(root),
        lambda: write_snapshot(root, snapshot()),
        lambda: write_metadata(root, metadata, {}),
        lambda: read_metadata(root, metadata),
    ):
        with pytest.raises(ValueError, match="软链"):
            action()
    assert outside.read_text() == '"original"'
    assert not (root / "chapter.md").exists()


def test_shared_snapshot_pull_preserves_private_files_and_deletes_only_baseline(tmp_path):
    (tmp_path / ".env").write_text("private")
    (tmp_path / "obsolete.md").write_text("old")
    write_snapshot(tmp_path, snapshot(), ["obsolete.md"])
    assert not (tmp_path / "obsolete.md").exists()
    assert (tmp_path / ".env").read_text() == "private"
    assert set(scan_files(tmp_path)) == {"chapter.md"}
    assert read_metadata(tmp_path, STATE)["hashes"] == {"chapter.md": digest(b"synthetic")}


def test_directory_link_and_corrupt_hash_leave_originals_intact(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    book = tmp_path / "book"
    book.mkdir()
    (book / "linked").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        write_snapshot(book, snapshot("linked/file"))
    assert not (outside / "file").exists()
    value = snapshot()
    value["files"][0]["sha256"] = "bad"
    with pytest.raises(ValueError):
        write_snapshot(book, value)
    assert not (book / "chapter.md").exists()
