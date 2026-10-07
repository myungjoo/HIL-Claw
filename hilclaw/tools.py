"""Tool registry, tool failure and the request / result checks shared by the fronts.

The level below the fronts of ADR-0010 (decisions 2 to 4 and 7). A *tool
function* takes one request and returns one result or raises
:class:`ToolFailure`. A request and a result are each one JSON object in the
strict sense: a ``dict`` whose member names are ``str`` and whose values are,
recursively, ``dict``, ``list``, ``str``, ``int``, finite ``float``, ``bool``
or ``None``, each of exactly that type, as :func:`json.loads` returns them.

A front decodes a request, calls :func:`call` and encodes the outcome; it holds
no tool logic. Nothing here keeps state between calls, reads configuration or
the data plane, or writes to a standard stream.
"""

import json
import math
import re

KIND_TOOL_CRASHED = "tool_crashed"
KIND_BAD_RESULT = "bad_result"

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
    """The input is not a request; no tool function was called."""


class Registry:
    """The table from tool name to tool function."""

    def __init__(self):
        self._tools = {}

    def register(self, name, function):
        """Add a tool function under ``name``.

        ``name`` is lowercase words (a letter, then letters and digits) joined
        by single ``.``. Raises :class:`TypeError` when ``name`` is not a
        ``str`` or ``function`` is not callable, and :class:`ValueError` when
        ``name`` breaks the rule or is registered already.
        """
        if type(name) is not str:
            raise TypeError("a tool name must be a str")
        if not _TOOL_NAME.fullmatch(name):
            raise ValueError(f"{name!r} is not a tool name ({_TOOL_NAME.pattern})")
        if not callable(function):
            raise TypeError(f"the tool function of {name} is not callable")
        if name in self._tools:
            raise ValueError(f"the tool {name} is registered already")
        self._tools[name] = function

    def get(self, name):
        """Return the tool function of ``name``; raise :class:`UnknownToolError` if there is none."""
        if type(name) is not str or name not in self._tools:
            raise UnknownToolError(f"unknown tool {name!r}")
        return self._tools[name]

    def names(self):
        """Return the registered tool names as a sorted tuple."""
        return tuple(sorted(self._tools))


def default_registry():
    """Return a new registry holding the fixed tool set of the package.

    The set is empty. A tool is added here, in the source, and in no other way:
    no option, environment variable, entry point or plugin registers one.
    """
    return Registry()


def check_json_object(value):
    """Raise :class:`ValueError` unless ``value`` is one JSON object in the strict sense.

    A value nested too deeply for this interpreter, or cyclic, is refused too.
    """
    try:
        _check_object(value, "$")
        # A depth the walk passes can still be too deep for the encoder.
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
