"""The placement of the given code as attempt ``(0, 1, 1)`` and the tool ``given.place`` (ADR-0200 decisions 4 (a), 5 and 7).

In a run whose ``instance.json`` (version 3) states ``given_code``, round 0
makes no coder call: its one attempt ``(0, 1, 1)`` is the given code, whose
``output/`` holds :data:`GIVEN_NAME` written from the blob after
:func:`hilclaw.cas.verify_blob` confirmed its hash, and which has no
``spec.json`` (ADR-0200 decision 4 (a)). :func:`place` is that placement. The
command of ADR-0200 decision 5 calls it as a function, and the Round-Manager
of a live turn calls it through the tool ``given.place`` that
:func:`definition` returns.

**Decided by ADR-0201 decision 2** (ADR-0200 leaves how the Round-Manager
reaches the placement open): the Round-Manager has no file tools, so the
placement is a tool of the registry beside ``instance.read`` and
``key.store``, admitted for the Round-Manager only (:data:`hilclaw.turn_permissions.ROUND_MANAGER_TOOLS`), and called in
step 2 of round 0 in place of the delegation to ``coder-driver``
(``orchestration/round-manager.md``). Like the run-file tools of ADR-0124 and
``key.store`` it is not an FR-10 tool: it is not journaled, appends no line
to ``events.ndjson``, selects no backend and keeps nothing between calls.

The request of ``given.place`` is exactly ``{"run_id": ...}``; the data root
comes from the data-root source, asked at each call after the request was
checked (ADR-0015 decision 3). The result is ``{"given_code": <hash>}``.

The checks of :func:`place`, in this order, each with its kind; the first
that fails decides and nothing is written before the last:

1. the run's ``instance.json`` read once by
   :func:`hilclaw.run_file_tools.read` (the four ``run_file_*`` kinds of
   ADR-0019);
2. a ``given_code`` stated, so a version-3 file
   (:data:`KIND_GIVEN_CODE_NOT_STATED` for a file of version 1 or 2);
3. no entry ``output`` of any kind in the directory of the attempt
   ``(0, 1, 1)``, as a coder call refuses it (:data:`KIND_OUTPUT_EXISTS`; a
   directory that cannot be listed :data:`KIND_OUTPUT_NOT_WRITTEN`);
4. :func:`hilclaw.cas.verify_blob` of the hash: no blob
   (:data:`KIND_GIVEN_CODE_MISSING`), a blob whose content is not its hash
   (:data:`KIND_GIVEN_CODE_CORRUPT`), an :class:`OSError` of the read
   (:data:`KIND_GIVEN_CODE_UNREADABLE`);
5. the blob read once more: an :class:`OSError` is
   :data:`KIND_GIVEN_CODE_UNREADABLE`, bytes whose hash is not the one stated
   :data:`KIND_GIVEN_CODE_CORRUPT`, more than
   :data:`hilclaw.bring_in.MAX_FILE_BYTES` bytes, the bound of a kernel file
   (ADR-0055 decision 6), :data:`KIND_GIVEN_CODE_TOO_LARGE`;
6. the write: the attempt directory and its missing parents are created as
   the bring-in of a coder call creates them, then ``output/`` (a name taken
   meanwhile is :data:`KIND_OUTPUT_EXISTS`), then :data:`GIVEN_NAME` as a new
   file holding exactly the bytes of 5; any other :class:`OSError` is
   :data:`KIND_OUTPUT_NOT_WRITTEN`, and what was created before it stays,
   as after a failed bring-in.

The candidate kind is not checked: the start writes version 3 for a
``c_kernel`` run only (ADR-0200 decision 6), and the readers of a given
attempt refuse another kind until ADR-0200 slice 5. Nothing writes a
``spec.json``, ``STATE.json`` or ``artifacts.json`` here. Each message starts
with the path concerned relative to the data root; an :class:`OSError` is
reported by its class and the text of the system.
"""

import hashlib
import os

from hilclaw import (
    bring_in,
    cas,
    coder_call,
    data_root_source,
    instance,
    layout,
    run_file_tools,
    run_files,
    tools,
)

#: The name of the file of the given code in the attempt's ``output/`` (ADR-0200 decision 2).
GIVEN_NAME = "given.c"
#: The tuple ``(round, candidate, attempt)`` of the given attempt (ADR-0200 decision 4 (a)).
GIVEN_ATTEMPT = (0, 1, 1)

#: ``instance.json`` states no given code (version 1 or 2); nothing was placed.
KIND_GIVEN_CODE_NOT_STATED = "given_code_not_stated"
#: The store holds no blob of the stated hash; nothing was placed.
KIND_GIVEN_CODE_MISSING = "given_code_missing"
#: The blob's content is not the stated hash; nothing was placed.
KIND_GIVEN_CODE_CORRUPT = "given_code_corrupt"
#: The blob could not be read; nothing was placed.
KIND_GIVEN_CODE_UNREADABLE = "given_code_unreadable"
#: The blob is larger than a kernel file may be (ADR-0055 decision 6); nothing was placed.
KIND_GIVEN_CODE_TOO_LARGE = "given_code_too_large"
#: The attempt ``(0, 1, 1)`` already has an entry ``output``; nothing was placed.
KIND_OUTPUT_EXISTS = coder_call.KIND_OUTPUT_EXISTS
#: The attempt's directory could not be listed, or the file could not be written.
KIND_OUTPUT_NOT_WRITTEN = coder_call.KIND_OUTPUT_NOT_WRITTEN

NAME = "given.place"

_WRITE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
_DESCRIPTION = (
    "Place the given code of the run run_id as its round-0 attempt (round 0, "
    "candidate 1, attempt 1): the blob whose hash the run's instance.json "
    "states as given_code is verified and written as output/given.c of that "
    "attempt. No spec is written and no coder is called. Call it in round 0 "
    "of a run whose instance.json holds given_code, in place of the coder "
    'call. The result is {"given_code": the hash}. The data root is never '
    "part of the request; the tool knows it. It fails, checked in this "
    "order, with invalid_request for a request that is not exactly run_id; "
    "no_data_root when the data root cannot be obtained; run_file_missing, "
    "run_file_invalid, run_file_unsupported or run_file_unreadable when the "
    "run's instance.json is not there, is invalid or no regular file, has "
    "another schema_version or cannot be read; given_code_not_stated when it "
    "states no given_code; output_exists when the attempt already has an "
    "entry output; given_code_missing when the store holds no such blob, "
    "given_code_corrupt when its content is not its hash, "
    "given_code_unreadable when it cannot be read and given_code_too_large "
    "when it is larger than 262144 bytes, nothing being written in each of "
    "these; and output_not_written when the attempt's directory cannot be "
    "listed or the file cannot be written."
)
_MEMBERS = ("run_id",)


def place(data_root, run_id):
    """Place the given code of the run ``run_id`` below ``data_root`` as ``output/given.c`` of attempt ``(0, 1, 1)``.

    ``data_root`` is a path; ``run_id`` is checked by
    :func:`hilclaw.layout.run_file` before the file system is touched, a
    value that is none raising :class:`hilclaw.layout.InvalidPathValueError`.
    Returns the hash of the given code, the ``given_code`` of the run's
    ``instance.json``. Raises :class:`hilclaw.tools.ToolFailure` of the kinds
    of the module docstring, checked in its order; before step 6 nothing is
    created.
    """
    _, content = run_file_tools.read(data_root, run_id, "instance.json")
    digest = _stated(run_id, content)
    output = layout.attempt_artefact(data_root, run_id, *GIVEN_ATTEMPT, "output")
    _refuse_existing_output(data_root, output)
    data = _verified(data_root, digest)
    _write(data_root, output, data)
    return digest


def definition(source):
    """Return the tool definition of ``given.place``, bound to the data-root source ``source``.

    The result is one :class:`hilclaw.tools.ToolDefinition`. ``source`` is
    the data-root source of ADR-0015 decision 3; it is asked once at each
    call, after the request was checked, and not here. Raises
    :class:`TypeError` when it is not callable.

    The tool function raises :class:`hilclaw.tools.ToolFailure` of kind
    ``invalid_request`` for a request that is not exactly ``run_id`` or whose
    ``run_id`` :func:`hilclaw.layout.check_run_id` refuses; ``no_data_root``
    as :func:`hilclaw.data_root_source.obtain` does; and what :func:`place`
    raises.
    """
    if not callable(source):
        raise TypeError("the data-root source must be callable")

    def place_given(request):
        run_id = _checked(request)
        return {"given_code": place(data_root_source.obtain(source), run_id)}

    return tools.ToolDefinition(NAME, place_given, _DESCRIPTION, _input_schema())


def _input_schema():
    return {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
        },
        "required": list(_MEMBERS),
        "additionalProperties": False,
    }


def _checked(request):
    others = sorted(name for name in request if name not in _MEMBERS)
    if others:
        raise _invalid(
            f"the request takes the member run_id only, not {', '.join(map(repr, others))}"
        )
    if "run_id" not in request:
        raise _invalid("the request lacks the member run_id")
    try:
        return layout.check_run_id(request["run_id"])
    except layout.InvalidPathValueError as e:
        raise _invalid(f"the request's {e}") from e


def _invalid(message):
    return tools.ToolFailure(tools.KIND_INVALID_REQUEST, message)


def _stated(run_id, content):
    given = instance.parse_given(content)
    if given.given_code is None:
        file = run_files.relative(run_id, "instance.json")
        raise tools.ToolFailure(
            KIND_GIVEN_CODE_NOT_STATED,
            f"{file}: states no given_code (schema_version "
            f"{given.schema_version}); nothing was placed",
        )
    return given.given_code


def _refuse_existing_output(data_root, output):
    try:
        listed = os.listdir(output.parent)
    except run_files.NOT_THERE:
        return
    except OSError as e:
        raise tools.ToolFailure(
            KIND_OUTPUT_NOT_WRITTEN,
            f"{_relative(output.parent, data_root)}: could not be listed: "
            f"{_reported(e, data_root)}",
        ) from e
    if output.name in listed:
        raise _output_exists(data_root, output)


def _output_exists(data_root, output):
    return tools.ToolFailure(
        KIND_OUTPUT_EXISTS,
        f"{_relative(output, data_root)}: the attempt already has an entry "
        "output; nothing was placed",
    )


def _verified(data_root, digest):
    path = cas.blob_path(data_root, digest)
    file = _relative(path, data_root)
    try:
        intact = cas.verify_blob(data_root, digest)
        data = None if not intact else path.read_bytes()
    except cas.BlobNotFoundError as e:
        raise tools.ToolFailure(
            KIND_GIVEN_CODE_MISSING,
            f"{file}: the store holds no blob of the given code; nothing was placed",
        ) from e
    except OSError as e:
        raise tools.ToolFailure(
            KIND_GIVEN_CODE_UNREADABLE,
            f"{file}: could not be read: {_reported(e, data_root)}; nothing was placed",
        ) from e
    if data is None or hashlib.sha256(data).hexdigest() != digest:
        raise tools.ToolFailure(
            KIND_GIVEN_CODE_CORRUPT,
            f"{file}: its content is not its hash; nothing was placed",
        )
    if len(data) > bring_in.MAX_FILE_BYTES:
        raise tools.ToolFailure(
            KIND_GIVEN_CODE_TOO_LARGE,
            f"{file}: holds {len(data)} bytes, more than the "
            f"{bring_in.MAX_FILE_BYTES} of a kernel file; nothing was placed",
        )
    return data


def _write(data_root, output, data):
    target = output / GIVEN_NAME
    try:
        os.makedirs(output.parent, exist_ok=True)
        try:
            os.mkdir(output)
        except FileExistsError as e:
            raise _output_exists(data_root, output) from e
        descriptor = os.open(target, _WRITE_FLAGS, 0o666)
        try:
            view = memoryview(data)
            while view:
                view = view[os.write(descriptor, view) :]
        finally:
            os.close(descriptor)
    except OSError as e:
        raise tools.ToolFailure(
            KIND_OUTPUT_NOT_WRITTEN,
            f"{_relative(target, data_root)}: was not written: "
            f"{_reported(e, data_root)}",
        ) from e


def _relative(path, data_root):
    return path.relative_to(data_root).as_posix()


def _reported(error, data_root):
    reported = ": ".join(filter(None, (type(error).__name__, error.strerror)))
    if isinstance(error, run_files.NOT_THERE) and not run_files.data_root_is_there(
        data_root
    ):
        reported += ": the data root is not an existing directory"
    return reported
