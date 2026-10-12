"""The tools ``blob.push`` and ``blob.fetch`` of the MVP's local implementation (ADR-0039).

On one machine the local store ``blobs/sha256/`` under the data root is the
only store, so the two tools do the same thing: each looks whether a regular
file is at the place of a hash (:func:`hilclaw.cas.blob_path`, symbolic links
followed) and, when one is, re-hashes its content. Nothing is copied.

The request is ``{"sha256": <64 characters of 0-9 a-f>}`` and nothing else.
The result is ``{"sha256": ..., "present": bool}`` and, only when ``present``
is true, ``"intact": bool`` (whether the content read is the content of that
hash). A hash the store does not hold is a result, not a tool failure.

A call writes nothing, creates no directory, reads no file but the one at the
place of the hash, runs no process and keeps nothing between calls.
"""

import hashlib
import os
import re
import stat

from hilclaw import cas, data_root_source, tools

#: The look or the read failed in the file system for a reason other than there being no file.
KIND_BLOB_UNREADABLE = "blob_unreadable"

_SHA256 = re.compile(r"[0-9a-f]{64}")
_NO_FILE = (FileNotFoundError, NotADirectoryError)
_RESULT = (
    'The result is {"sha256": the hash asked for, "present": whether a regular '
    'file is at the place of that hash in the local store, "intact": whether '
    'the content of that file has that SHA-256}; "intact" is given only when '
    '"present" is true. A hash that is not there is a result, not an error.'
)
_DESCRIPTIONS = {
    "blob.fetch": (
        "Look whether the blob of a SHA-256 hash is in the local blob store of "
        "this machine and re-hash it. In this implementation the local store is "
        "the only store: nothing is copied and a blob that is not there is not "
        "obtained. " + _RESULT
    ),
    "blob.push": (
        "Look whether the blob of a SHA-256 hash is in the local blob store of "
        "this machine and re-hash it. In this implementation the local store is "
        "the only store: nothing is copied and the blob gets no second copy. " + _RESULT
    ),
}


def definitions(source):
    """Return the tool definitions of ``blob.fetch`` and ``blob.push`` bound to ``source``.

    The result is a tuple of two :class:`hilclaw.tools.ToolDefinition`, in
    that order, each with a schema of its own. ``source`` is the data-root
    source, the callable without arguments of ADR-0015 decision 3; it is
    asked at each call, after the request was checked, and not here. Raises
    :class:`TypeError` when it is not callable.

    Each tool function raises :class:`hilclaw.tools.ToolFailure` of kind
    ``invalid_request`` for a request that is not exactly one ``sha256`` of
    the form above, ``no_data_root`` as :func:`hilclaw.data_root_source.obtain`
    does, and :data:`KIND_BLOB_UNREADABLE` when the look or the read fails for
    a reason other than there being no file.
    """
    if not callable(source):
        raise TypeError("the data-root source must be callable")

    def look(request):
        return _look(source, request)

    return tuple(
        tools.ToolDefinition(name, look, description, _input_schema())
        for name, description in _DESCRIPTIONS.items()
    )


def _input_schema():
    return {
        "type": "object",
        "properties": {"sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}},
        "required": ["sha256"],
        "additionalProperties": False,
    }


def _look(source, request):
    sha256 = _checked(request)
    path = cas.blob_path(data_root_source.obtain(source), sha256)
    try:
        found = _content_hash(path)
    except OSError as e:
        raise tools.ToolFailure(
            KIND_BLOB_UNREADABLE,
            f"the blob {sha256} could not be looked at or read: {type(e).__name__}: {e}",
        ) from e
    if found is None:
        return {"sha256": sha256, "present": False}
    return {"sha256": sha256, "present": True, "intact": found == sha256}


def _checked(request):
    others = sorted(name for name in request if name != "sha256")
    if others:
        raise tools.ToolFailure(
            tools.KIND_INVALID_REQUEST,
            f"the request takes the member sha256 only, not {', '.join(map(repr, others))}",
        )
    sha256 = request.get("sha256")
    if type(sha256) is not str or not _SHA256.fullmatch(sha256):
        raise tools.ToolFailure(
            tools.KIND_INVALID_REQUEST,
            "the request needs sha256, a string of exactly 64 characters 0-9 a-f",
        )
    return sha256


def _content_hash(path):
    f = _opened(path)
    if f is None:
        return None
    with f:
        sha = hashlib.sha256()
        for chunk in iter(lambda: f.read(cas.CHUNK_SIZE), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _opened(path):
    try:
        if not stat.S_ISREG(os.stat(path).st_mode):
            return None
        return open(path, "rb")
    except _NO_FILE:
        return None
