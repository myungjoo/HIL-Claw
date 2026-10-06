"""Local content-addressed blob store of the data repository (Requirements C-3).

A blob is a file named after the SHA-256 of its content, kept outside git at
``<data_root>/blobs/sha256/<hh>/<digest>``, where ``<digest>`` is 64 lowercase
hexadecimal characters and ``<hh>`` its first two. ``data_root`` is always given
by the caller and must be an existing directory; this module reads no
configuration, runs no ``git`` and writes nowhere else.

Blobs are only ever added. A blob is written to a temporary file inside
``blobs/sha256/`` and moved into place with :func:`os.replace`, so a reader
never sees a partial blob under its final name. Storing content that is already
present keeps the stored file as it is.
"""

import hashlib
import os
import re
import secrets
from pathlib import Path
from typing import NamedTuple

CHUNK_SIZE = 1024 * 1024

_DIGEST = re.compile(r"[0-9a-f]{64}")


class BlobRef(NamedTuple):
    """Reference to a stored blob: its SHA-256 hex digest and its size in bytes."""

    digest: str
    size: int


class BlobNotFoundError(LookupError):
    """The store holds no blob with the requested digest."""


def blob_path(data_root, digest):
    """Return the path of the blob ``digest`` under ``data_root`` without touching the file system.

    Raises :class:`ValueError` unless ``digest`` is a ``str`` of exactly 64
    lowercase hexadecimal characters, so the result is always inside the store.
    """
    if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
        raise ValueError(f"not a lowercase SHA-256 hex digest: {digest!r}")
    return Path(data_root) / "blobs" / "sha256" / digest[:2] / digest


def put_bytes(data_root, data):
    """Store ``data`` (``bytes`` or ``bytearray``) and return its :class:`BlobRef`.

    Raises :class:`TypeError` for any other type, and :class:`FileNotFoundError`
    or :class:`NotADirectoryError` when ``data_root`` is not an existing directory.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError(f"data must be bytes or bytearray, not {type(data).__name__}")
    return _store(data_root, [data] if data else [])


def put_file(data_root, source):
    """Store the content of the file ``source`` and return its :class:`BlobRef`.

    The file is read in chunks of ``CHUNK_SIZE`` bytes and is left untouched.
    Raises the underlying :class:`OSError` when ``source`` cannot be read, and
    the same errors as :func:`put_bytes` for ``data_root``.
    """
    with open(source, "rb") as f:
        return _store(data_root, _chunks(f))


def has_blob(data_root, digest):
    """Return whether the blob ``digest`` is in the store (:class:`ValueError` if malformed)."""
    return blob_path(data_root, digest).is_file()


def verify_blob(data_root, digest):
    """Re-hash the stored blob ``digest`` and return whether the content matches its name.

    Raises :class:`BlobNotFoundError` when :func:`has_blob` is false for it and
    :class:`ValueError` when ``digest`` is malformed.
    """
    path = blob_path(data_root, digest)
    if not path.is_file():
        raise BlobNotFoundError(f"blob {digest} is not in the store")
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in _chunks(f):
            sha.update(chunk)
    return sha.hexdigest() == digest


def _chunks(f):
    return iter(lambda: f.read(CHUNK_SIZE), b"")


def _store(data_root, chunks):
    root = Path(data_root)
    if not root.is_dir():
        error = NotADirectoryError if root.exists() else FileNotFoundError
        raise error(f"data root is not an existing directory: {root}")
    store = root / "blobs" / "sha256"
    store.mkdir(parents=True, exist_ok=True)
    temporary = store / f"tmp-{os.getpid()}-{secrets.token_hex(8)}"
    sha = hashlib.sha256()
    size = 0
    try:
        with open(temporary, "xb") as f:
            for chunk in chunks:
                sha.update(chunk)
                f.write(chunk)
                size += len(chunk)
            f.flush()
            os.fsync(f.fileno())
        target = blob_path(root, sha.hexdigest())
        if not target.is_file():
            target.parent.mkdir(exist_ok=True)
            os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return BlobRef(sha.hexdigest(), size)
