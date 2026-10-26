"""Tool registry, tool failure and the request / result checks shared by the fronts.

The level below the fronts of ADR-0010 (decisions 2 to 4 and 7) and the tool
definition of ADR-0015 (decision 2). A *tool function* takes one request and
returns one result or raises :class:`ToolFailure`. A request and a result are
each one JSON object in the strict sense: a ``dict`` whose member names are
``str`` and whose values are, recursively, ``dict``, ``list``, ``str``,
``int``, finite ``float``, ``bool`` or ``None``, each of exactly that type, as
:func:`json.loads` returns them.

A *tool definition* is what the registry holds for one tool: its name, its
tool function, a description and an input schema, both written for the caller.
No request is checked against the schema here or in a front: the tool function
checks its own request.

A front decodes a request, calls :func:`call` and encodes the outcome; it holds
no tool logic. Nothing here keeps state between calls, reads configuration or
the data plane, or writes to a standard stream; what a tool of
:func:`default_registry` reads is stated in the module that defines it.
"""

import copy
import json
import math
import re
import typing

#: The reserved kinds (ADR-0015 decision 2, ADR-0016 decision 3, ADR-0019 decision 2, ADR-0026 decision 3): one meaning in every tool, not enforced.
KIND_INVALID_REQUEST = "invalid_request"  #: the tool function refused the request
KIND_NO_DATA_ROOT = "no_data_root"  #: the data root could not be obtained
KIND_STEP_OPEN = "step_open"  #: the journaled step of this identity is open
KIND_TOOL_CRASHED = "tool_crashed"  #: the tool function raised what is no tool failure
KIND_BAD_RESULT = "bad_result"  #: the tool function returned no result object
KIND_NO_BACKEND = "no_backend"  #: the backend table has no entry for the accelerator
KIND_NOT_OFFERED = "not_offered"  #: the selected backend has no operation for the tool
KIND_RUN_FILE_MISSING = "run_file_missing"  #: a frame file the call needs is not there
KIND_RUN_FILE_UNREADABLE = "run_file_unreadable"  #: the read of a frame file failed for a reason other than its not being there; its content was not judged
KIND_RUN_FILE_INVALID = "run_file_invalid"  #: a frame file, a complete line of the log or the stored position is invalid, or the place of a frame file holds no regular file
KIND_RUN_FILE_UNSUPPORTED = "run_file_unsupported"  #: a frame file or a line of the log has another schema_version; nothing of it was interpreted
KIND_START_LINE_FAILED = "start_line_failed"  #: the append of the start line of this call failed; this call did not call the step
KIND_END_LINE_FAILED = "end_line_failed"  #: the append of the end line of this call failed; this call ran the step to its end and the answer carries no outcome
RESERVED_KINDS = frozenset(
    {
        KIND_INVALID_REQUEST,
        KIND_NO_DATA_ROOT,
        KIND_STEP_OPEN,
        KIND_TOOL_CRASHED,
        KIND_BAD_RESULT,
        KIND_NO_BACKEND,
        KIND_NOT_OFFERED,
        KIND_RUN_FILE_MISSING,
        KIND_RUN_FILE_UNREADABLE,
        KIND_RUN_FILE_INVALID,
        KIND_RUN_FILE_UNSUPPORTED,
        KIND_START_LINE_FAILED,
        KIND_END_LINE_FAILED,
    }
)

_KIND = re.compile(r"[a-z][a-z0-9_]{0,31}")
_TOOL_NAME = re.compile(r"[a-z][a-z0-9]*(?:\.[a-z][a-z0-9]*)*")
_SCALARS = (str, int, bool, type(None))


class ToolFailure(Exception):
    """A call that established no outcome: the request was refused or the tool could not work.

    ``kind`` is a name (``[a-z][a-z0-9_]{0,31}``, ADR-0001) and ``message`` a
    ``str``. Raises :class:`TypeError` when either is not exactly a ``str`` and
    :class:`ValueError` when ``kind`` is not a name.
    """

    def __init__(self, kind, message):
        if type(kind) is not str or type(message) is not str:
            raise TypeError("the kind and the message of a tool failure must be str")
        if not _KIND.fullmatch(kind):
            raise ValueError(f"{kind!r} is not a name matching {_KIND.pattern}")
        super().__init__(kind, message)
        self.kind = kind
        self.message = message

    def error_object(self):
        """Return ``{"error": {"kind": ..., "message": ...}}``, the form both fronts report."""
        return {"error": {"kind": self.kind, "message": self.message}}


class UnknownToolError(LookupError):
    """The registry has no tool of that name; each front answers it in its own way."""


class InvalidRequestError(ValueError):
    """The input is not a request; no tool function was called.

    It is not the reserved kind ``invalid_request``, the tool failure with
    which a tool function refuses a request it was called with.
    """


class ToolDefinition(typing.NamedTuple):
    """What the registry holds for one tool (ADR-0015 decision 2)."""

    name: str
    function: typing.Callable
    description: str
    input_schema: dict


class Registry:
    """The table from tool name to tool definition."""

    def __init__(self):
        self._tools = {}

    def register(self, name, function, description, input_schema):
        """Add the tool definition of ``name``; all four parts are required.

        ``name`` is lowercase words (a letter, then letters and digits) joined
        by single ``.``. ``description`` is a ``str`` with a character that is
        not whitespace. ``input_schema`` is one JSON object in the strict sense
        whose member ``type`` is ``"object"``; nothing else of it is checked.
        The registry keeps a copy of the schema.

        Raises :class:`TypeError` when ``name`` or ``description`` is not a
        ``str``, ``function`` is not callable or ``input_schema`` is not a
        ``dict``, and :class:`ValueError` when ``name`` breaks the rule or is
        registered already, ``description`` is blank or ``input_schema`` is
        not such an object. A refused registration adds nothing.
        """
        if type(name) is not str:
            raise TypeError("a tool name must be a str")
        if not _TOOL_NAME.fullmatch(name):
            raise ValueError(f"{name!r} is not a tool name ({_TOOL_NAME.pattern})")
        if not callable(function):
            raise TypeError(f"the tool function of {name} is not callable")
        if name in self._tools:
            raise ValueError(f"the tool {name} is registered already")
        if type(description) is not str:
            raise TypeError(f"the description of {name} must be a str")
        if not description.strip():
            raise ValueError(f"the description of {name} is empty")
        if type(input_schema) is not dict:
            raise TypeError(f"the input schema of {name} must be a dict")
        try:
            check_json_object(input_schema)
            schema = copy.deepcopy(input_schema)
        except RecursionError:
            raise ValueError(
                f"the input schema of {name} is nested too deeply"
            ) from None
        except ValueError as e:
            raise ValueError(f"the input schema of {name} is not JSON: {e}") from e
        if schema.get("type") != "object":
            raise ValueError(f'the input schema of {name} must have the type "object"')
        self._tools[name] = ToolDefinition(name, function, description, schema)

    def _held(self, name):
        if type(name) is not str or name not in self._tools:
            raise UnknownToolError(f"unknown tool {name!r}")
        return self._tools[name]

    def get(self, name):
        """Return the tool function of ``name``; raise :class:`UnknownToolError` if there is none."""
        return self._held(name).function

    def definition(self, name):
        """Return the :class:`ToolDefinition` of ``name``, its schema as a new copy.

        Raises :class:`UnknownToolError` if there is none, as :meth:`get` does.
        How deeply a schema may be nested depends on the interpreter and on the
        depth of the call: a reading from a deeper call than the registration
        can fail to copy it with a ``RecursionError``, which the MCP front does
        not catch when it lists the tools.
        """
        held = self._held(name)
        return held._replace(input_schema=copy.deepcopy(held.input_schema))

    def names(self):
        """Return the registered tool names as a sorted tuple."""
        return tuple(sorted(self._tools))


def default_registry(data_root_source):
    """Return a new registry holding the fixed tool set of the package.

    ``data_root_source`` is the callable without arguments (ADR-0015
    decision 3) to which every tool of the set that needs the data plane is
    bound; building the registry does not call it, and imports no module of
    the operation of ``correctness.check``, ``sim.run`` or ``board.run`` and
    so no NumPy. Raises :class:`TypeError` when it is not callable.

    The set is ``blob.fetch`` and ``blob.push`` (:mod:`hilclaw.blob_tools`,
    ADR-0039), ``correctness.check`` (:func:`hilclaw.check_definition.definition`,
    ADR-0070) and ``sim.run`` and ``board.run``
    (:func:`hilclaw.run_definition.definitions`, ADR-0167). The three HW
    tools are bound to one default table, whose entries are the mock,
    offering the three with the default scripts of ADR-0044 and ADR-0066,
    and ``cpu_standin``, offering the three with its operations
    (:mod:`hilclaw.standin_check`, :mod:`hilclaw.standin_run`). Their
    source of seeds is the generator of the operating system. Their
    predicate "covered" is that of ADR-0041 decision 5. Beside these FR-10 tools it holds ``state.read``,
    ``instance.read``, ``run.fresh`` and ``state.write``
    (:mod:`hilclaw.run_file_tools`, ADR-0124), with which the Round-Manager
    reads and writes its run's ``STATE.json`` and reads its ``instance.json``,
    and ``run.commit`` (:func:`hilclaw.run_commit.definition`, ADR-0127), with
    which it commits an owed round end of its run; and ``verdicts.write``
    (:func:`hilclaw.verdicts_tool.definition`, ADR-0128 decision 6), with
    which the evaluator writes a round's ``eval/verdicts.json``, and
    ``hypotheses.read`` (:func:`hilclaw.hypotheses_tool.definition`, ADR-0129
    decision 3), with which it reads a round's ``decision/hypotheses.json``,
    and ``checks.read`` (:func:`hilclaw.checks_tool.definition`, ADR-0131
    decision 3), with which it reads the ``correctness.check`` lines of an
    attempt or a candidate at one point and their standing. It holds
    ``hypotheses.write`` (:func:`hilclaw.hypotheses_write_tool.definition`,
    ADR-0132 decision 4), with which the technique-selector writes a round's
    ``decision/hypotheses.json``. It holds
    ``case.write`` (:func:`hilclaw.case_tool.definition`, ADR-0133 decision
    3), with which the Round-Manager writes a round's case, ``key.store``
    (:func:`hilclaw.key_store_tool.definition`, ADR-0134 decision 3), with
    which it stores its run's two key record files, and ``round.end``
    (:func:`hilclaw.round_end_tool.definition`, ADR-0135 decision 2), with
    which it makes the write that ends its round. It holds ``spec.write``
    (:func:`hilclaw.spec_tool.definition`, ADR-0138 decision 3), with which
    the coder-driver has the spec of the first coder call of round 0 written,
    and that of the first coder call of a round >= 1 (ADR-0151 decision 3),
    and ``timings.compare`` (:func:`hilclaw.timings_tool.definition`,
    ADR-0140 decision 3), with which the evaluator gets the ``difference`` of
    a comparison of two attempts at one point. It holds ``coder.run``
    (:func:`hilclaw.coder_tool.definition`, ADR-0141 decisions 2 and 3), with
    which the coder-driver performs the round-0 coder call, bound to
    :class:`hilclaw.coder_runtime.DockerRuntime` with its defaults
    (ADR-0137 code slice 2): a call that passes the checks before
    ``no_container_runtime`` fails with that kind when no container server
    answers, and with ``coder_not_started`` when the image or the token of
    ADR-0137 decisions 4 and 5 is missing. Building the registry starts no
    process.
    A tool is added here, in the source, and in no other way: no option,
    environment variable, entry point or plugin registers one or chooses what
    it is bound to.
    """
    from hilclaw import (
        blob_tools,
        case_tool,
        check_definition,
        checks_tool,
        coder_runtime,
        coder_tool,
        hypotheses_tool,
        hypotheses_write_tool,
        key_store_tool,
        round_end_tool,
        run_commit,
        run_definition,
        run_file_tools,
        spec_tool,
        timings_tool,
        verdicts_tool,
    )

    if not callable(data_root_source):
        raise TypeError("the data-root source must be callable")
    registry = Registry()
    for definition in blob_tools.definitions(data_root_source):
        registry.register(*definition)
    registry.register(*check_definition.definition(data_root_source))
    for definition in run_definition.definitions(data_root_source):
        registry.register(*definition)
    for definition in run_file_tools.definitions(data_root_source):
        registry.register(*definition)
    registry.register(*run_commit.definition(data_root_source))
    registry.register(*verdicts_tool.definition(data_root_source))
    registry.register(*hypotheses_tool.definition(data_root_source))
    registry.register(*hypotheses_write_tool.definition(data_root_source))
    registry.register(*checks_tool.definition(data_root_source))
    registry.register(*case_tool.definition(data_root_source))
    registry.register(*key_store_tool.definition(data_root_source))
    registry.register(*round_end_tool.definition(data_root_source))
    registry.register(*spec_tool.definition(data_root_source))
    registry.register(*timings_tool.definition(data_root_source))
    registry.register(
        *coder_tool.definition(data_root_source, coder_runtime.DockerRuntime())
    )
    return registry


def check_json_object(value):
    """Raise :class:`ValueError` unless ``value`` is one JSON object in the strict sense.

    A value nested too deeply for this interpreter to walk or to encode, or
    cyclic, is refused too.
    """
    try:
        _check_object(value, "$")
        json.dumps(value, allow_nan=False)
    except RecursionError:
        raise ValueError("nested too deeply") from None


def _check_object(value, path):
    if type(value) is not dict:
        raise ValueError(f"{path}: expected an object, got {type(value).__name__}")
    for name, member in value.items():
        if type(name) is not str:
            raise ValueError(f"{path}: member name {name!r} is not a str")
        _check_value(member, f"{path}.{name}")


def _check_value(value, path):
    if type(value) is dict:
        _check_object(value, path)
    elif type(value) is list:
        for i, item in enumerate(value):
            _check_value(item, f"{path}[{i}]")
    elif type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{path}: {value} is not a finite number")
    elif type(value) not in _SCALARS:
        raise ValueError(f"{path}: {type(value).__name__} is not a JSON type")


def _unique_members(pairs):
    members = dict(pairs)
    if len(members) != len(pairs):
        raise ValueError(f"a member name is given twice among {list(members)}")
    return members


def decode_request(data):
    """Return the request that ``data`` (``bytes``) holds as UTF-8 JSON text.

    Raises :class:`InvalidRequestError` unless the text is exactly one JSON
    object with at most whitespace around it. Refused are: not UTF-8, a byte
    order mark, not JSON, another JSON value, ``NaN`` or ``Infinity``, a number
    too large for a ``float``, a member name given twice, nesting too deep.
    Raises :class:`TypeError` when ``data`` is not ``bytes``.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("the encoded request must be bytes")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_members)
        check_json_object(value)
    except RecursionError:
        raise InvalidRequestError("not a request: nested too deeply") from None
    except ValueError as e:
        raise InvalidRequestError(f"not a request: {e}") from e
    return value


def encode(value):
    """Return ``value`` as one line of JSON text in ASCII bytes, ended by one LF.

    ``value`` is a result that :func:`call` returned or an error object. The
    line is compact, in the member order of ``value``, non-ASCII escaped.
    """
    text = json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    return text.encode("ascii") + b"\n"


def call(registry, name, request):
    """Call the tool ``name`` of ``registry`` with ``request`` and return its result.

    Raises :class:`UnknownToolError` for a name the registry does not hold and
    :class:`InvalidRequestError` for a ``request`` that is not a JSON object;
    the tool function is called in neither case. The request is handed over
    as it is, not copied. A :class:`ToolFailure` of the tool function passes
    through. Any other :class:`Exception` it raises becomes a ``ToolFailure``
    of kind ``tool_crashed``, and a return value that is not a JSON object one
    of kind ``bad_result``, each chained to its cause.
    """
    function = registry.get(name)
    try:
        check_json_object(request)
    except ValueError as e:
        raise InvalidRequestError(f"not a request: {e}") from e
    try:
        result = function(request)
    except ToolFailure:
        raise
    except Exception as e:
        raise ToolFailure(KIND_TOOL_CRASHED, f"{type(e).__name__}: {e}") from e
    try:
        check_json_object(result)
    except ValueError as e:
        raise ToolFailure(KIND_BAD_RESULT, f"not a result: {e}") from e
    return result
