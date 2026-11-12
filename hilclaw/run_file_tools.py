"""The tools ``state.read``, ``instance.read``, ``run.fresh`` and ``state.write`` (ADR-0124).

Through these four tools the Round-Manager reads its run's ``STATE.json`` and
``instance.json``, tells a fresh run directory (ADR-0120 decision 4) and
writes its run's ``STATE.json`` by the steps of ADR-0013 (ADR-0124 decisions
2 and 3). They are tools of the registry beside the FR-10 tools, not FR-10
tools: none is journaled, appends a line to ``events.ndjson`` or selects a
backend.

Every request is ``{"run_id": ...}``, and for ``state.write`` also
``"state"``: the whole new content as one JSON object; any other member is
refused. The data root comes from the data-root source, asked at each call
after the request was checked, and never from the request (ADR-0015
decision 3).

- ``state.read`` and ``instance.read`` read their file once and return
  ``{"state": ...}`` or ``{"instance": ...}``: the JSON object parsed from the
  bytes that :func:`hilclaw.run_state.parse` or
  :func:`hilclaw.instance.parse_given` accepted, members as stored, so an
  ``instance.json`` of version 1, 2 or 3 (ADR-0198 decision 8, ADR-0200
  decision 7) with, at version 2, its ``candidate_kind`` and, at version 3,
  its ``given_code``. A missing, invalid, other-version or unreadable
  file is the ``run_file_*`` kind of ADR-0019 decision 3, as widened by
  ADR-0124 decision 3. A number beyond the float range in a member neither
  validator defines is read as an infinity, which no result can hold: the call
  then fails with ``bad_result``. Their read is :func:`read`, which is also
  the read of these two files by ``case.write`` (:mod:`hilclaw.case_tool`)
  and of ``instance.json`` by the other tools of a round. It reads a
  version-2 or version-3 ``instance.json`` as its version-1 twin; a tool
  that reads only C kernel runs without given code refuses the others with
  :func:`c_kernel_only`.
- ``run.fresh`` returns ``{"fresh": bool}`` of :func:`hilclaw.fresh_run.is_fresh`
  and reads no file.
- ``state.write`` refuses a ``state`` that is not valid at version 1 before
  the source is asked, then writes exactly that content with
  :func:`hilclaw.run_state_file.replace` and returns ``{}``. Nothing is read
  or carried over (ADR-0013 decision 7).

Only ``state.write`` creates anything: ``STATE.json``, the temporary file of
its replacement and, when missing, ``runs/`` and the run directory. Nothing is
kept between calls.
"""

import json
import os
import stat

from hilclaw import (
    data_root_source,
    fresh_run,
    instance,
    layout,
    run_files,
    run_state,
    run_state_file,
    tools,
)

#: Telling a fresh run directory failed in the file system for a reason other than an entry's not being there.
KIND_RUN_DIR_UNREADABLE = "run_dir_unreadable"
#: A step of the replacement failed in the file system; ``STATE.json`` holds what it held.
KIND_STATE_NOT_WRITTEN = "state_not_written"

_RUN_ID_SCHEMA = {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"}
_DEFINED = ("schema_version", "round", "budget_spent")
_NO_ROOT = "The data root is never part of the request; the tool knows it. "
_READ_FAILURES = (
    "It fails with run_file_missing when the file is not there, run_file_invalid "
    "when it is invalid or no regular file, run_file_unsupported for another "
    "schema_version and run_file_unreadable when it cannot be read."
)
_DESCRIPTIONS = {
    "state.read": (
        "Read the STATE.json of the run run_id: the run's round pointer, stored "
        'spend view and other members. The result is {"state": the content of '
        "the file as one JSON object, its members as stored}. "
        + _NO_ROOT
        + "A missing STATE.json is a failure, not a result. "
        + _READ_FAILURES
    ),
    "instance.read": (
        "Read the instance.json of the run run_id: the instance record the run "
        'was started with. The result is {"instance": the content of the file '
        "as one JSON object, its members as stored}. " + _NO_ROOT + _READ_FAILURES
    ),
    "run.fresh": (
        "Tell whether the directory of the run run_id is fresh: it holds "
        "instance.json as a regular file and none of STATE.json, events.ndjson, "
        'artifacts.json and rounds. The result is {"fresh": true or false}; no '
        "file is read. " + _NO_ROOT + "It fails with run_dir_unreadable when an "
        "entry cannot be looked at."
    ),
    "state.write": (
        "Replace the STATE.json of the run run_id with state, the whole new "
        "content as one JSON object (schema_version 1, round, budget_spent and "
        "any other members), or write the first one. Exactly what is given is "
        "written; nothing is read from the previous file or carried over. A state "
        "that is not valid is refused with invalid_request before anything is "
        "written. The result is {}. " + _NO_ROOT + "It fails with "
        "state_not_written when a step of the replacement fails; STATE.json then "
        "holds what it held."
    ),
}


def definitions(source):
    """Return the tool definitions of ``state.read``, ``instance.read``, ``run.fresh`` and ``state.write``.

    The result is a tuple of four :class:`hilclaw.tools.ToolDefinition`, in
    that order, each bound to ``source``, the data-root source of ADR-0015
    decision 3; it is asked at each call, after the request was checked, and
    not here. Raises :class:`TypeError` when it is not callable.

    Each tool function raises :class:`hilclaw.tools.ToolFailure` of kind
    ``invalid_request`` for a request that is not exactly the members above,
    or whose ``run_id`` :func:`hilclaw.layout.check_run_id` refuses, or, for
    ``state.write``, whose ``state`` :func:`hilclaw.run_state.validate`
    refuses or :func:`hilclaw.run_state.dump` cannot write; and
    ``no_data_root`` as :func:`hilclaw.data_root_source.obtain` does. The two
    reads raise the four ``run_file_*`` kinds, ``run.fresh``
    :data:`KIND_RUN_DIR_UNREADABLE` and ``state.write``
    :data:`KIND_STATE_NOT_WRITTEN`, each for an :class:`OSError`.
    """
    if not callable(source):
        raise TypeError("the data-root source must be callable")

    def read_state(request):
        return {"state": _read(source, request, "STATE.json")}

    def read_instance(request):
        return {"instance": _read(source, request, "instance.json")}

    def fresh(request):
        return _fresh(source, request)

    def write_state(request):
        return _write(source, request)

    functions = {
        "state.read": read_state,
        "instance.read": read_instance,
        "run.fresh": fresh,
        "state.write": write_state,
    }
    return tuple(
        tools.ToolDefinition(
            name, functions[name], _DESCRIPTIONS[name], _input_schema(name)
        )
        for name in functions
    )


def _input_schema(name):
    properties = {"run_id": dict(_RUN_ID_SCHEMA)}
    if name == "state.write":
        properties["state"] = {"type": "object"}
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def _invalid(message):
    return tools.ToolFailure(tools.KIND_INVALID_REQUEST, message)


def _run_id(request, members):
    others = sorted(name for name in request if name not in members)
    if others:
        raise _invalid(
            f"the request takes the members {', '.join(members)} only, "
            f"not {', '.join(map(repr, others))}"
        )
    for name in members:
        if name not in request:
            raise _invalid(f"the request lacks the member {name}")
    try:
        return layout.check_run_id(request["run_id"])
    except layout.InvalidPathValueError as e:
        raise _invalid(f"the request's {e}") from e


_STATE_FILE = (
    run_state.parse,
    {
        run_state.InvalidStateError: tools.KIND_RUN_FILE_INVALID,
        run_state.UnsupportedVersionError: tools.KIND_RUN_FILE_UNSUPPORTED,
    },
)


def _instance(content):
    return instance.parse_given(content).instance


_INSTANCE_FILE = (
    _instance,
    {
        instance.InvalidInstanceError: tools.KIND_RUN_FILE_INVALID,
        instance.UnsupportedVersionError: tools.KIND_RUN_FILE_UNSUPPORTED,
    },
)


_PARSING = {"STATE.json": _STATE_FILE, "instance.json": _INSTANCE_FILE}


def read(data_root, run_id, name):
    """Read the frame file ``name`` of the run ``run_id`` below ``data_root`` once, as ``state.read`` and ``instance.read`` do.

    ``name`` is ``"STATE.json"`` or ``"instance.json"``; ``data_root`` is a
    path and ``run_id`` is checked by :func:`hilclaw.layout.run_file`. The
    result is the pair of what :func:`hilclaw.run_state.parse` returned for
    the bytes, or for ``instance.json`` the ``instance`` of what
    :func:`hilclaw.instance.parse_given` returned, and the bytes themselves.
    An ``instance.json`` of version 1, 2 or 3 is read, and the
    :class:`hilclaw.instance.Instance` of a version-2 or version-3 file is
    that of its version-1 twin, its ``candidate_kind`` and ``given_code``
    left out (ADR-0198 decision 8, ADR-0200 decision 7). Nothing is created
    or kept.

    Raises :class:`ValueError` for another ``name`` and
    :class:`hilclaw.layout.InvalidPathValueError` for a ``run_id`` that is
    none, before the file system is touched; then
    :class:`hilclaw.tools.ToolFailure` of the four ``run_file_*`` kinds, each
    message starting with the file's path relative to ``data_root``: the
    place holding no regular file or bytes the parser refuses
    ``run_file_invalid`` (a version-1 ``instance.json`` holding
    ``candidate_kind``, a version-2 one stating no ``candidate_kind`` or
    ``c_kernel`` and a version-3 one stating no valid ``given_code`` among
    them), another ``schema_version`` (for ``instance.json`` one other than
    1, 2 and 3) ``run_file_unsupported``, and
    an :class:`OSError` as :func:`hilclaw.run_files.read_failure` answers it.
    """
    if name not in _PARSING:
        raise ValueError(f"name must be one of {', '.join(_PARSING)}, got {name!r}")
    parse, kinds = _PARSING[name]
    invalid = next(iter(kinds))
    path = layout.run_file(data_root, run_id, name)
    file = run_files.relative(run_id, name)
    with run_files.reading(data_root, run_id, name, kinds):
        if not stat.S_ISREG(os.lstat(path).st_mode):
            raise invalid(f"{file}: is not a regular file")
        content = path.read_bytes()
        try:
            parsed = parse(content)
        except tuple(kinds) as error:
            raise type(error)(f"{file}: {error}") from None
    return parsed, content


def c_kernel_only(run_id, content):
    """Refuse the run ``run_id`` unless its ``instance.json`` states the candidate kind ``c_kernel`` and no given code.

    ``content`` is the bytes :func:`read` returned for the run's
    ``instance.json``. A version-1 file states ``c_kernel`` and no given
    code, and nothing is raised for it. For a version-2 file, whose kind is
    another (ADR-0198 decision 4), and for a version-3 file, which states
    given code (ADR-0200 decision 6), it raises
    :class:`hilclaw.tools.ToolFailure` of kind ``run_file_unsupported``, its
    message starting with the file's path relative to the data root and
    naming the kind or the given code: the tool calling it does not read
    such a run (ADR-0198 decision 8, the rows that refuse in slice 2b;
    ADR-0200 decision 7, the last row of its reader table). Nothing is
    read, created or kept. Raises what :func:`hilclaw.instance.parse_given`
    raises for other bytes.
    """
    given = instance.parse_given(content)
    file = run_files.relative(run_id, "instance.json")
    if given.given_code is not None:
        raise tools.ToolFailure(
            tools.KIND_RUN_FILE_UNSUPPORTED,
            f"{file}: states given code (schema_version "
            f"{given.schema_version}); this tool does not read a given-code run",
        )
    kind = given.candidate_kind
    if kind != instance.CANDIDATE_KINDS[0]:
        raise tools.ToolFailure(
            tools.KIND_RUN_FILE_UNSUPPORTED,
            f"{file}: states the candidate kind {kind}; this tool reads "
            f"{instance.CANDIDATE_KINDS[0]} runs only",
        )


def _read(source, request, name):
    run_id = _run_id(request, ("run_id",))
    data_root = data_root_source.obtain(source)
    return json.loads(read(data_root, run_id, name)[1])


def _fresh(source, request):
    run_id = _run_id(request, ("run_id",))
    data_root = data_root_source.obtain(source)
    try:
        return {"fresh": fresh_run.is_fresh(data_root, run_id)}
    except OSError as e:
        raise tools.ToolFailure(
            KIND_RUN_DIR_UNREADABLE,
            f"runs/{run_id}: could not be looked at: {_reported(e, data_root)}",
        ) from e


def _write(source, request):
    run_id = _run_id(request, ("run_id", "state"))
    state = request["state"]
    if type(state) is not dict:
        raise _invalid(f"state: must be an object, got {type(state).__name__}")
    try:
        run_state.validate(state)
        view = run_state.from_stored(state["budget_spent"])
        others = {k: v for k, v in state.items() if k not in _DEFINED}
        run_state.dump(state["round"], view, others)
    except (run_state.InvalidStateError, run_state.UnsupportedVersionError) as e:
        raise _invalid(f"state: {e}") from e
    data_root = data_root_source.obtain(source)
    try:
        run_state_file.replace(data_root, run_id, state["round"], view, others)
    except OSError as e:
        file = run_files.relative(run_id, "STATE.json")
        raise tools.ToolFailure(
            KIND_STATE_NOT_WRITTEN,
            f"{file}: was not written: {_reported(e, data_root)}",
        ) from e
    return {}


def _reported(error, data_root):
    reported = ": ".join(filter(None, (type(error).__name__, error.strerror)))
    if isinstance(error, run_files.NOT_THERE) and not run_files.data_root_is_there(
        data_root
    ):
        reported += ": the data root is not an existing directory"
    return reported
