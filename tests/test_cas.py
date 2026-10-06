import hashlib
import os
from pathlib import Path

import pytest

from hilclaw import cas
from hilclaw.cas import (
    BlobNotFoundError,
    BlobRef,
    blob_path,
    has_blob,
    put_bytes,
    put_file,
    verify_blob,
)

EMPTY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
DATA = b"HIL-Claw blob \x00\xff\n"
DIGEST = hashlib.sha256(DATA).hexdigest()
MALFORMED = [
    "",
    "a" * 63,
    "a" * 65,
    "A" * 64,
    DIGEST.upper(),
    "g" * 64,
    "a" * 64 + "\n",
    " " + "a" * 63,
    "０" * 64,
    "../../etc/passwd",
    "../" + "a" * 61,
    "a" * 31 + "/" + "a" * 32,
    "a" * 31 + "\\" + "a" * 32,
    None,
    b"a" * 64,
    int("1" * 64),
    Path("a" * 64),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stored_files(root):
    store = Path(root) / "blobs" / "sha256"
    return sorted(
        p.relative_to(store).as_posix() for p in store.rglob("*") if p.is_file()
    )


def expected_files(*contents):
    return sorted({f"{sha(c)[:2]}/{sha(c)}" for c in contents})


@pytest.fixture(params=["bytes", "file"])
def put(request, tmp_path_factory):
    if request.param == "bytes":
        return put_bytes
    source = tmp_path_factory.mktemp("source") / "source.bin"

    def via_file(root, data):
        source.write_bytes(data)
        return put_file(root, source)

    return via_file


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "data"
    path.mkdir()
    return path


def test_put_bytes_stores_the_content_under_its_digest(root):
    ref = put_bytes(root, DATA)

    assert ref == BlobRef(DIGEST, len(DATA))
    assert (ref.digest, ref.size) == (DIGEST, len(DATA))
    path = root / "blobs" / "sha256" / DIGEST[:2] / DIGEST
    assert path.read_bytes() == DATA
    assert blob_path(root, DIGEST) == path
    assert stored_files(root) == [f"{DIGEST[:2]}/{DIGEST}"]


def test_put_bytes_accepts_a_bytearray(root):
    assert put_bytes(root, bytearray(DATA)) == BlobRef(DIGEST, len(DATA))
    assert blob_path(root, DIGEST).read_bytes() == DATA


def test_put_file_larger_than_one_chunk_matches_put_bytes(root, tmp_path):
    content = bytes(range(256)) * (cas.CHUNK_SIZE // 128) + b"tail"
    assert len(content) > 2 * cas.CHUNK_SIZE
    source = tmp_path / "source.bin"
    source.write_bytes(content)
    other = tmp_path / "other"
    other.mkdir()

    ref = put_file(root, source)

    assert ref == BlobRef(sha(content), len(content))
    assert ref == put_bytes(other, content)
    assert blob_path(root, ref.digest).read_bytes() == content
    assert source.read_bytes() == content
    assert stored_files(root) == expected_files(content)


def test_put_file_of_exactly_one_chunk(root, tmp_path):
    content = b"\x5a" * cas.CHUNK_SIZE
    source = tmp_path / "source.bin"
    source.write_bytes(content)

    assert put_file(root, source) == BlobRef(sha(content), cas.CHUNK_SIZE)
    assert verify_blob(root, sha(content)) is True


def test_the_empty_blob_is_valid(root, put):
    assert put(root, b"") == BlobRef(EMPTY, 0)
    assert blob_path(root, EMPTY).read_bytes() == b""
    assert verify_blob(root, EMPTY) is True
    assert stored_files(root) == [f"e3/{EMPTY}"]


def test_str_and_path_arguments_give_the_same_result(root, tmp_path):
    source = tmp_path / "source.bin"
    source.write_bytes(DATA)

    refs = {
        put_bytes(str(root), DATA),
        put_bytes(root, DATA),
        put_file(str(root), str(source)),
        put_file(root, source),
    }

    assert refs == {BlobRef(DIGEST, len(DATA))}
    assert blob_path(str(root), DIGEST) == blob_path(root, DIGEST)
    assert has_blob(str(root), DIGEST) is True
    assert verify_blob(str(root), DIGEST) is True
    assert stored_files(root) == [f"{DIGEST[:2]}/{DIGEST}"]


def test_has_blob_and_verify_blob_follow_a_put(root):
    assert has_blob(root, DIGEST) is False

    put_bytes(root, DATA)

    assert has_blob(root, DIGEST) is True
    assert verify_blob(root, DIGEST) is True
    assert has_blob(root, EMPTY) is False


def test_has_blob_is_false_for_a_directory_with_a_blob_name(root):
    blob_path(root, DIGEST).mkdir(parents=True)

    assert has_blob(root, DIGEST) is False


def test_blob_path_is_pure(tmp_path):
    absent = tmp_path / "absent"

    path = blob_path(absent, DIGEST)

    assert path == absent / "blobs" / "sha256" / DIGEST[:2] / DIGEST
    assert isinstance(path, Path)
    assert blob_path(str(absent), DIGEST) == path
    assert list(tmp_path.iterdir()) == []
    assert has_blob(absent, DIGEST) is False
    assert list(tmp_path.iterdir()) == []


def test_a_repeated_put_keeps_the_stored_file(root, put):
    first = put(root, DATA)
    path = blob_path(root, DIGEST)
    path.write_bytes(b"marker")
    os.utime(path, (1_000_000_000, 1_000_000_000))

    second = put(root, DATA)

    assert second == first == BlobRef(DIGEST, len(DATA))
    assert path.read_bytes() == b"marker"
    assert path.stat().st_mtime == 1_000_000_000
    assert stored_files(root) == [f"{DIGEST[:2]}/{DIGEST}"]
    assert verify_blob(root, DIGEST) is False


def test_blobs_with_different_and_equal_prefixes(root):
    by_prefix = {}
    for i in range(2000):
        content = b"blob-%d" % i
        by_prefix.setdefault(sha(content)[:2], []).append(content)
    first, second = next(group for group in by_prefix.values() if len(group) > 1)[:2]
    third = next(
        group[0] for prefix, group in by_prefix.items() if prefix != sha(first)[:2]
    )

    refs = [put_bytes(root, content) for content in (first, second, third)]

    assert [ref.digest for ref in refs] == [sha(first), sha(second), sha(third)]
    assert refs[0].digest[:2] == refs[1].digest[:2] != refs[2].digest[:2]
    assert stored_files(root) == expected_files(first, second, third)
    assert all(verify_blob(root, ref.digest) for ref in refs)
    store = root / "blobs" / "sha256"
    assert sorted(p.name for p in store.iterdir()) == sorted(
        {r.digest[:2] for r in refs}
    )


def test_put_into_an_existing_store_layout(root):
    (root / "blobs" / "sha256" / DIGEST[:2]).mkdir(parents=True)
    (root / "unrelated.txt").write_text("keep")

    assert put_bytes(root, DATA) == BlobRef(DIGEST, len(DATA))
    assert sorted(p.name for p in root.iterdir()) == ["blobs", "unrelated.txt"]
    assert (root / "unrelated.txt").read_text() == "keep"


@pytest.mark.parametrize("digest", MALFORMED)
@pytest.mark.parametrize("function", [blob_path, has_blob, verify_blob])
def test_malformed_digests_are_rejected(root, function, digest):
    with pytest.raises(ValueError, match="not a lowercase SHA-256 hex digest"):
        function(root, digest)
    assert list(root.iterdir()) == []


def test_verify_blob_detects_altered_content(root):
    put_bytes(root, DATA)
    path = blob_path(root, DIGEST)

    path.write_bytes(DATA + b"x")
    assert verify_blob(root, DIGEST) is False
    path.write_bytes(b"")
    assert verify_blob(root, DIGEST) is False
    path.write_bytes(DATA)
    assert verify_blob(root, DIGEST) is True


def test_verify_blob_of_an_absent_blob(root, tmp_path):
    with pytest.raises(BlobNotFoundError, match=DIGEST) as info:
        verify_blob(root, DIGEST)
    assert isinstance(info.value, LookupError)
    assert not isinstance(info.value, OSError)

    put_bytes(root, DATA)
    with pytest.raises(BlobNotFoundError, match=EMPTY):
        verify_blob(root, EMPTY)
    with pytest.raises(BlobNotFoundError):
        verify_blob(tmp_path / "absent", DIGEST)


def test_verify_blob_agrees_with_has_blob_when_the_path_is_not_a_file(root, tmp_path):
    blob_path(root, DIGEST).mkdir(parents=True)
    root_file = tmp_path / "file"
    root_file.write_bytes(b"not a directory")

    for data_root in (root, root_file):
        assert has_blob(data_root, DIGEST) is False
        with pytest.raises(BlobNotFoundError, match=DIGEST):
            verify_blob(data_root, DIGEST)


def test_put_file_with_a_missing_source(root, tmp_path):
    with pytest.raises(FileNotFoundError):
        put_file(root, tmp_path / "absent.bin")
    assert list(root.iterdir()) == []


def test_put_file_with_a_directory_as_source(root, tmp_path):
    source = tmp_path / "directory"
    source.mkdir()
    (source / "inner.bin").write_bytes(DATA)

    with pytest.raises(OSError):
        put_file(root, source)
    assert list(root.iterdir()) == []
    assert (source / "inner.bin").read_bytes() == DATA


def test_put_with_a_root_that_does_not_exist(tmp_path, put):
    absent = tmp_path / "typo" / "data"

    with pytest.raises(FileNotFoundError, match="data root"):
        put(absent, DATA)
    assert not (tmp_path / "typo").exists()


def test_put_with_a_root_that_is_a_regular_file(tmp_path, put):
    parent = tmp_path / "parent"
    parent.mkdir()
    root_file = parent / "data"
    root_file.write_bytes(b"not a directory")

    with pytest.raises(NotADirectoryError, match="data root"):
        put(root_file, DATA)
    assert root_file.read_bytes() == b"not a directory"
    assert [p.name for p in parent.iterdir()] == ["data"]


def test_a_failed_move_into_place_leaves_no_temporary_file(root, put, monkeypatch):
    moves = []

    def failing_replace(src, dst):
        moves.append((Path(src), Path(dst)))
        assert Path(src).parent == root / "blobs" / "sha256"
        assert Path(src).read_bytes() == DATA
        raise OSError("injected failure")

    monkeypatch.setattr(cas.os, "replace", failing_replace)
    with pytest.raises(OSError, match="injected failure"):
        put(root, DATA)
    monkeypatch.undo()

    assert [dst for _, dst in moves] == [blob_path(root, DIGEST)]
    assert stored_files(root) == []
    assert has_blob(root, DIGEST) is False
    assert put(root, DATA) == BlobRef(DIGEST, len(DATA))
    assert stored_files(root) == [f"{DIGEST[:2]}/{DIGEST}"]


def test_a_failed_read_of_the_source_leaves_no_temporary_file(
    root, tmp_path, monkeypatch
):
    source = tmp_path / "source.bin"
    source.write_bytes(b"x" * (cas.CHUNK_SIZE + 1))
    reads = []

    def failing_chunks(f):
        reads.append(f.name)
        yield f.read(cas.CHUNK_SIZE)
        raise OSError("injected read failure")

    monkeypatch.setattr(cas, "_chunks", failing_chunks)
    with pytest.raises(OSError, match="injected read failure"):
        put_file(root, source)

    assert reads == [str(source)]
    assert stored_files(root) == []


def test_a_blob_path_occupied_by_a_directory_is_an_error(root):
    blob_path(root, DIGEST).mkdir(parents=True)

    with pytest.raises(OSError):
        put_bytes(root, DATA)
    assert stored_files(root) == []
    assert blob_path(root, DIGEST).is_dir()


@pytest.mark.parametrize("data", ["text", None, 7, [1, 2], memoryview(b"abc")])
def test_put_bytes_rejects_other_types(root, data):
    with pytest.raises(TypeError, match="bytes or bytearray"):
        put_bytes(root, data)
    assert list(root.iterdir()) == []
