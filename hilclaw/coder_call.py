"""The coder call of a first-case turn: one function performing the whole call (ADR-0126 decision 3).

``ARCHITECTURE/decisions/ADR-0126-od23-coder-call-issuer.md`` decision 3 fixes
that one deterministic function of this package performs a coder call in the
order of ADR-0049: the checks, the scratch with the copy of the spec
(:func:`hilclaw.scratch.create`, slice (a)), the container and the coder
process (slice (d)), the bring-in (:func:`hilclaw.bring_in.bring_in`, slice
(b)) and the removal of the scratch (:func:`hilclaw.scratch.remove`, slice
(c)); it also fixes the request, the result and the failure kinds in the order
of their checks. :func:`call` is that function. Nothing calls it yet.

The container and the coder process stand behind *the runtime*, the seam of
slice (d), an object with two methods:

- ``runtime.available()`` returns whether a container runtime is there;
- ``runtime.run(scratch_root)`` starts the container with the scratch as the
  coder's working directory (ADR-0126 decision 5), waits for the coder process
  to end, removes the container before it returns (ADR-0049 P4) and returns
  the exit status of the coder process as an ``int``; it raises
  :class:`CoderNotStartedError` when the container or the process could not be
  started.

The runtime also composes the coder prompt, which names ``spec.json`` and
``output`` relatively (ADR-0126 decision 5); this module writes no prompt text
and no ``claude`` flag, and it starts no process itself.

What this module is not: slice (d), the real runtime with its image, flags and
prompt; either front of ADR-0126 decision 3 (Q1); anything about a call that
does not end normally beyond the interim rule of decision 3, which is OD-19;
time limits (OD-14); more than one call or candidate (OD-23 ① (가), OD-29).
The call is not journaled and writes nothing of the data plane but what
``bring_in`` writes below ``output/`` (ADR-0126 decision 7).
"""

import os
import stat
from pathlib import Path

from hilclaw import bring_in, data_root_source, layout, scratch, spec_file, tools
from hilclaw.kernel_source import OUTPUT_NAME

KIND_OUTPUT_EXISTS = "output_exists"
KIND_SPEC_INVALID = "spec_invalid"
KIND_SPEC_UNSUPPORTED = "spec_unsupported"
KIND_NO_CONTAINER_RUNTIME = "no_container_runtime"
KIND_CODER_NOT_STARTED = "coder_not_started"
KIND_CODER_NOT_ENDED = "coder_not_ended"
KIND_OUTPUT_NOT_WRITTEN = "output_not_written"
#: Every kind :func:`call` raises, in the order of its checks (ADR-0126 decision 3).
FAILURE_KINDS = (
    tools.KIND_INVALID_REQUEST,
    tools.KIND_NO_DATA_ROOT,
    KIND_OUTPUT_EXISTS,
    scratch.SPEC_UNREADABLE,
    scratch.SPEC_NOT_REGULAR_FILE,
    KIND_SPEC_INVALID,
    KIND_SPEC_UNSUPPORTED,
    KIND_NO_CONTAINER_RUNTIME,
    scratch.SPEC_CHANGED,
    KIND_CODER_NOT_STARTED,
    KIND_CODER_NOT_ENDED,
    *bring_in.BRING_IN_FAILURES,
    KIND_OUTPUT_NOT_WRITTEN,
)

_MEMBERS = ("run_id", "round", "candidate", "attempt")
_READ_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_NONBLOCK", 0)
    | getattr(os, "O_BINARY", 0)
)


class CoderNotStartedError(Exception):
    """Raised by ``runtime.run`` when the container or the coder process could not be started."""


def call(request, *, source, runtime):
    """Perform one coder call for the tuple of ``request``; return its result.

    ``request`` is a ``dict`` of exactly ``run_id``, ``round``, ``candidate``
    and ``attempt`` (ADR-0015 decision 4), checked as
    :func:`hilclaw.layout.attempt_artefact` checks them. ``source`` is the
    data-root source (:mod:`hilclaw.data_root_source`) and ``runtime`` the
    seam of the module docstring; there is no default runtime.

    The spec file is ``layout.attempt_artefact(..., "spec.json")`` of the
    tuple and the output ``layout.attempt_artefact(..., "output")``. Returns
    ``{"taken": [...], "scratch_removed": bool}``: the names
    :func:`hilclaw.bring_in.bring_in` returned, in its order (possibly none),
    and what :func:`hilclaw.scratch.remove` reported.

    Raises :class:`hilclaw.tools.ToolFailure` with one kind of
    :data:`FAILURE_KINDS`, checked in that order: ``invalid_request`` before
    the source is asked; ``no_data_root`` as
    :func:`hilclaw.data_root_source.obtain` raises it; :data:`KIND_OUTPUT_EXISTS`
    when the attempt directory lists an entry ``output``, or
    ``attempt_directory_unlistable`` when it exists but cannot be listed (the
    value ``bring_in`` gives then; this module's reading); ``spec_unreadable``
    (a missing spec file included) and ``spec_not_regular_file`` for the spec
    file read without following a link; :data:`KIND_SPEC_INVALID` when
    :func:`hilclaw.spec_file.parse` refuses it or its ``id`` is not the tuple
    (``final_name`` is not the path read); :data:`KIND_SPEC_UNSUPPORTED` for
    another version; :data:`KIND_NO_CONTAINER_RUNTIME`. Nothing is created and
    the runtime is not run before this point. Then the value of a
    :class:`hilclaw.scratch.ScratchError`; :data:`KIND_CODER_NOT_STARTED`;
    :data:`KIND_CODER_NOT_ENDED` for a status other than 0, with no bring-in;
    the value of a :class:`hilclaw.bring_in.BringInError`;
    :data:`KIND_OUTPUT_EXISTS` for its :class:`hilclaw.bring_in.OutputExistsError`
    (the name taken during the call: this module's reading of "what
    ``bring_in`` would refuse after it"); :data:`KIND_OUTPUT_NOT_WRITTEN` for
    its :class:`OSError`. No text holds a path of the data root.

    Once the scratch is made it is removed whatever follows, once and with no
    later retry (ADR-0049 ㉝ (나)); a removal that fails on a failure path is
    added to the failure's text, and the kind stays.

    Propagated unchanged, with no kind of ADR-0126: :class:`TypeError` for a
    ``source`` that is not callable; any exception of ``runtime.available``;
    :class:`hilclaw.scratch.InvalidScratchArgumentError` and the
    :class:`OSError` of :func:`hilclaw.scratch.create` or ``remove``; any
    exception of ``runtime.run`` but :class:`CoderNotStartedError`, and a
    :class:`TypeError` for a status that is no ``int``; and
    :class:`hilclaw.bring_in.InvalidBringInArgumentError`. Those raised after
    the scratch was made come after its removal was tried.
    """
    run_id, numbers = _checked(request)
    data_root = data_root_source.obtain(source)
    spec_path = layout.attempt_artefact(data_root, run_id, *numbers, "spec.json")
    output_path = layout.attempt_artefact(data_root, run_id, *numbers, "output")
    _refuse_existing_output(output_path)
    _check_spec(data_root, spec_path, _read_spec(spec_path))
    if not runtime.available():
        raise tools.ToolFailure(
            KIND_NO_CONTAINER_RUNTIME, "no container runtime is available"
        )
    try:
        scratch_root = scratch.create(spec_path, keep_out=(data_root,))
    except scratch.ScratchError as e:
        raise _fail(e.failure, "the spec file could not be copied") from e
    try:
        taken = _run_and_bring_in(runtime, scratch_root, output_path)
    except tools.ToolFailure as e:
        if scratch.remove(scratch_root, keep_out=(data_root,)):
            raise
        raise _fail(e.kind, f"{e.message}; the scratch was not removed") from e
    except BaseException:
        scratch.remove(scratch_root, keep_out=(data_root,))
        raise
    removed = scratch.remove(scratch_root, keep_out=(data_root,))
    return {"taken": list(taken), "scratch_removed": removed}


def _fail(kind, message):
    return tools.ToolFailure(kind, message)


def _checked(request):
    if type(request) is not dict:
        raise _fail(
            tools.KIND_INVALID_REQUEST,
            f"the request must be an object, got {type(request).__name__}",
        )
    others = sorted(repr(name) for name in request if name not in _MEMBERS)
    if others:
        raise _fail(
            tools.KIND_INVALID_REQUEST,
            f"the request takes the members {', '.join(_MEMBERS)} only, "
            f"not {', '.join(others)}",
        )
    for name in _MEMBERS:
        if name not in request:
            raise _fail(
                tools.KIND_INVALID_REQUEST, f"the request lacks the member {name}"
            )
    run_id = request["run_id"]
    numbers = request["round"], request["candidate"], request["attempt"]
    try:
        layout.attempt_artefact(Path(), run_id, *numbers, "spec.json")
    except layout.InvalidPathValueError as e:
        raise _fail(tools.KIND_INVALID_REQUEST, f"the request's {e}") from e
    return run_id, numbers


def _refuse_existing_output(output_path):
    try:
        listed = os.listdir(output_path.parent)
    except (FileNotFoundError, NotADirectoryError):
        return
    except OSError as e:
        raise _fail(
            bring_in.ATTEMPT_DIRECTORY_UNLISTABLE,
            "the attempt directory cannot be listed",
        ) from e
    if OUTPUT_NAME in listed:
        raise _fail(KIND_OUTPUT_EXISTS, "the attempt already has an entry output")


def _read_spec(spec_path):
    try:
        examined = os.lstat(spec_path)
    except OSError as e:
        raise _fail(scratch.SPEC_UNREADABLE, "the spec file cannot be read") from e
    if not stat.S_ISREG(examined.st_mode):
        raise _fail(scratch.SPEC_NOT_REGULAR_FILE, "the spec file is no regular file")
    try:
        descriptor = os.open(spec_path, _READ_FLAGS)
    except OSError as e:
        raise _fail(scratch.SPEC_UNREADABLE, "the spec file cannot be opened") from e
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
            examined.st_dev,
            examined.st_ino,
        ):
            raise _fail(
                scratch.SPEC_UNREADABLE, "the spec file changed while it was opened"
            )
        chunks = []
        while chunk := os.read(descriptor, 65536):
            chunks.append(chunk)
    except OSError as e:
        raise _fail(scratch.SPEC_UNREADABLE, "the spec file cannot be read") from e
    finally:
        os.close(descriptor)
    return b"".join(chunks)


def _check_spec(data_root, spec_path, content):
    try:
        document = spec_file.parse(content)
    except spec_file.InvalidSpecFileError as e:
        raise _fail(KIND_SPEC_INVALID, f"the spec file is invalid: {e}") from e
    except spec_file.UnsupportedVersionError as e:
        raise _fail(KIND_SPEC_UNSUPPORTED, f"the spec file is unsupported: {e}") from e
    try:
        named = spec_file.final_name(data_root, document)
    except layout.InvalidPathValueError as e:
        raise _fail(KIND_SPEC_INVALID, f"the spec file's id has no path: {e}") from e
    if named != spec_path:
        raise _fail(
            KIND_SPEC_INVALID, "the spec file's id is not the tuple of the request"
        )


def _run_and_bring_in(runtime, scratch_root, output_path):
    try:
        status = runtime.run(scratch_root)
    except CoderNotStartedError as e:
        raise _fail(KIND_CODER_NOT_STARTED, "the coder could not be started") from e
    if type(status) is not int:
        raise TypeError(f"the runtime returned a {type(status).__name__}, not an int")
    if status != 0:
        raise _fail(
            KIND_CODER_NOT_ENDED,
            f"the coder process ended with status {status}; nothing was brought in",
        )
    try:
        return bring_in.bring_in(scratch_root, output_path)
    except bring_in.BringInError as e:
        raise _fail(e.failure, "the bring-in could not see what it has to see") from e
    except bring_in.OutputExistsError as e:
        raise _fail(KIND_OUTPUT_EXISTS, "output was taken during the call") from e
    except OSError as e:
        raise _fail(
            KIND_OUTPUT_NOT_WRITTEN,
            f"output could not be written ({type(e).__name__})",
        ) from e
