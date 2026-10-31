"""Runtime state of one run, the content of ``runs/<run_id>/STATE.json`` (ADR-0012).

``ARCHITECTURE/decisions/ADR-0012-od8-runtime-state-file.md`` fixes the file as
a whole (decision 2), the round pointer ``round`` (3), the stored spend view
``budget_spent`` (4) and what makes a content invalid (6). This module is those
rules as pure functions of the bytes of a content and of values in memory. It
is not :mod:`hilclaw.driver_state`, which checks ``PROCESS/STATE.json``.

Conventions of this module, which ADR-0012 does not fix:

- A content is exactly ``bytes`` (:class:`TypeError` otherwise: the encoding is
  part of validity). Values are as :func:`json.loads` returns them, an integer
  exactly an ``int``: ``true`` and ``1.0`` are none.
- Every other broken rule, of a content or of an argument, raises
  :class:`InvalidStateError` naming the place. Another version raises
  :class:`UnsupportedVersionError` of this module, not that of the log.
- The rules for the whole text come first, whatever the version. A content this
  interpreter cannot read (an integer too long for it anywhere in the text,
  nesting too deep) raises the same error, though it is a limit of this reader
  and not damage: nothing is rounded, and the limits stay as the interpreter
  has them, so they differ between interpreters and platforms. A number beyond
  the float range in a member not defined here is read as an infinity, which
  :func:`dump` does not write.
- ``-0`` is read as the integer 0, as :mod:`hilclaw.events` reads it, except as
  a total: decision 4 writes a total without a sign, so :func:`parse`, which
  sees the text, refuses it there.
- :func:`dump` writes as :func:`json.dumps` does with an indent of one space:
  one value per line for line-wise diffs, every character outside ASCII
  escaped. The members not defined here follow in ascending order of their
  names, also inside nested objects, so the bytes are a function of the values.

It reads and writes no file and knows no path: it says nothing of a missing
file or of how a file is replaced. It defines no member besides the three,
relates ``round`` to no open step, compares no total with a limit, checks no
view against a log and reads no other version (OD-11, OD-19, OD-23,
sub-questions 10 to 13 of ADR-0012).
"""

import codecs
import json
import re
import reprlib
from types import MappingProxyType
from typing import NamedTuple

from hilclaw import journal, json_text, keys, tools

SCHEMA_VERSION = 1

_NAME = re.compile(r"[a-z][a-z0-9_]{0,31}")
_MAX = keys.MAX_INTEGER
_DEFINED = ("schema_version", "round", "budget_spent")
_VIEW = ("totals", "position", "open_steps")
_NUMBERS = ("round", "candidate", "attempt")
_IDENTITY = (*_NUMBERS, "step", "execution")


class InvalidStateError(ValueError):
    """A content, a document or an argument breaks a rule of ADR-0012; the message names it."""


class UnsupportedVersionError(Exception):
    """``schema_version`` is an integer other than 1: not damage, and nothing is interpreted."""


class RunState(NamedTuple):
    """Result of :func:`parse`: the round pointer, the spend view, the members not defined."""

    round: int
    budget_spent: journal.SpendView
    others: dict


def parse(content):
    """Return the :class:`RunState` of ``content``, the bytes of a ``STATE.json`` (decision 6).

    ``budget_spent`` is the view :func:`from_stored` returns; ``others`` holds
    every top-level member this record does not define, as parsed and not
    interpreted. Any order of members and any white space of JSON are accepted.

    Raises :class:`InvalidStateError` when ``content`` is not UTF-8 without a
    byte order mark, is not exactly one JSON text (``NaN`` and the infinities
    are none), holds a member name twice in any object or is a document
    :func:`validate` refuses, and :class:`UnsupportedVersionError` as that
    function does. Nothing is returned then, and nothing is repaired.
    """
    if type(content) is not bytes:
        raise TypeError(f"content must be bytes, got {type(content).__name__}")
    if content.startswith(codecs.BOM_UTF8):
        raise InvalidStateError("content: starts with a byte order mark")
    try:
        text = content.decode("utf-8")
        document = json.loads(
            text,
            object_pairs_hook=json_text.distinct_members,
            parse_constant=json_text.no_constant,
        )
    except RecursionError:
        raise InvalidStateError("content: is nested too deeply to parse") from None
    except ValueError as error:
        reason = f"content: cannot be read as one JSON text: {error}"
        raise InvalidStateError(reason) from None
    state = _checked(document)
    tokens = json.loads(text, parse_int=str)["budget_spent"]["totals"]
    for axis, token in tokens.items():
        if token == "-0":
            raise InvalidStateError(f"budget_spent.totals.{axis}: has a sign")
    return state


def validate(document):
    """Check ``document``, a parsed ``STATE.json``, against ADR-0012 decisions 2 to 4 and 6.

    ``document`` must be a ``dict`` with ``schema_version`` and ``round`` (each
    an ``int`` from 0 to :data:`hilclaw.keys.MAX_INTEGER`) and ``budget_spent``
    (as :func:`from_stored` accepts it); its other members are not looked at.
    The rules for the text (the encoding, a member name twice, the sign of a
    total) cannot be checked on a parsed value. Raises
    :class:`InvalidStateError` for the first rule found broken, naming the
    place (for example ``budget_spent.open_steps[2].candidate``). The version
    comes first: an integer other than :data:`SCHEMA_VERSION` raises
    :class:`UnsupportedVersionError` before any other member is looked at.
    """
    _checked(document)


def from_stored(budget_spent):
    """Return the :class:`hilclaw.journal.SpendView` of a stored ``budget_spent`` (decision 4).

    ``budget_spent`` must be a ``dict`` with exactly ``totals`` (an object from
    an axis name to an ``int`` from 0, of any size), ``position`` (an ``int``
    from 0 to :data:`hilclaw.keys.MAX_INTEGER`) and ``open_steps`` (a ``list``
    of identity objects: ``step``, ``execution`` and optionally ``round``,
    ``candidate`` only with ``round``, ``attempt`` only with ``candidate``; no
    other member, no ``null``, no identity twice). The view has a read-only
    mapping and a ``frozenset`` of :class:`hilclaw.journal.Identity`, an absent
    number as ``None``. Raises :class:`InvalidStateError`.
    """
    return _view("budget_spent", budget_spent)


def to_stored(view):
    """Return the ``budget_spent`` object of ``view``, in the order of decisions 2 and 4.

    A new ``dict``: the axes in ascending order of their names with their exact
    totals; the identities in ascending order of ``round``, ``candidate``,
    ``attempt``, ``step`` and ``execution``, an absent number first and left
    out of its object. Raises :class:`InvalidStateError` for a view
    :func:`hilclaw.journal.fold` refuses and for a ``position`` above
    :data:`hilclaw.keys.MAX_INTEGER`, which the stored form cannot hold.
    """
    try:
        (totals, position, open_steps), _ = journal.fold((), view)
    except ValueError as error:
        raise InvalidStateError(str(error)) from None
    return {
        "totals": dict(sorted(totals.items())),
        "position": _integer("view.position", position),
        "open_steps": list(map(_stored, sorted(open_steps, key=_order))),
    }


def dump(round, view, others=None):
    """Return the bytes of a ``STATE.json`` holding these values, in the written form.

    UTF-8, LF line ends and a final line feed; ``schema_version``, ``round``,
    ``budget_spent`` as :func:`to_stored` gives it, then the members of
    ``others``: a strict JSON object (:func:`hilclaw.tools.check_json_object`)
    without the three names, written and never interpreted. Exactly what is
    given is written; whether a writer keeps a member it does not know is its
    caller's matter (sub-question 12). :func:`parse` reads the result back to
    equal values. Raises :class:`InvalidStateError` for a ``round`` that is no
    integer of ADR-0001, a view :func:`to_stored` refuses, ``others`` that
    break the rule above and a total too long for this interpreter to write.
    """
    document = {"schema_version": SCHEMA_VERSION, "round": _integer("round", round)}
    document["budget_spent"] = to_stored(view)
    others = {} if others is None else others
    try:
        tools.check_json_object(others)
        further = json.loads(json.dumps(others, sort_keys=True))
    except (ValueError, RecursionError) as error:
        raise InvalidStateError(f"others: is not strict JSON: {error}") from None
    for name in _DEFINED:
        if name in further:
            raise InvalidStateError(f"others: must not hold the member {name}")
    try:
        text = json.dumps(document | further, indent=1)
    except ValueError as error:
        raise InvalidStateError(f"view.totals: is too long to write: {error}") from None
    return (text + "\n").encode("ascii")


def _fail(place, rule, value):
    try:
        got = f"{type(value).__name__} {reprlib.repr(value)}"
    except ValueError:
        got = f"{type(value).__name__} too long to show"
    raise InvalidStateError(f"{place}: must be {rule}, got {got}")


def _integer(place, value):
    if type(value) is not int or not 0 <= value <= _MAX:
        _fail(place, f"an int from 0 to {_MAX}", value)
    return value


def _lacks(place, value, required):
    for name in required:
        if name not in value:
            raise InvalidStateError(f"{place}: lacks the member {name}")


def _members(place, value, required, optional=()):
    if type(value) is not dict:
        _fail(place, "an object", value)
    for name in value:
        if name not in required and name not in optional:
            _fail(place, "an object without the member", name)
    _lacks(place, value, required)


def _checked(document):
    if type(document) is not dict:
        _fail("document", "an object", document)
    _lacks("document", document, _DEFINED[:1])
    version = _integer("schema_version", document["schema_version"])
    if version != SCHEMA_VERSION:
        raise UnsupportedVersionError(f"schema_version: {version} is not supported")
    _lacks("document", document, _DEFINED)
    round = _integer("round", document["round"])
    view = _view("budget_spent", document["budget_spent"])
    others = {name: value for name, value in document.items() if name not in _DEFINED}
    return RunState(round, view, others)


def _view(place, stored):
    _members(place, stored, _VIEW)
    if type(stored["totals"]) is not dict:
        _fail(f"{place}.totals", "an object", stored["totals"])
    for axis, total in stored["totals"].items():
        if type(axis) is not str or not _NAME.fullmatch(axis):
            _fail(f"{place}.totals: member name", f"a name ({_NAME.pattern})", axis)
        if type(total) is not int or total < 0:
            _fail(f"{place}.totals.{axis}", "an int from 0", total)
    _integer(f"{place}.position", stored["position"])
    if type(stored["open_steps"]) is not list:
        _fail(f"{place}.open_steps", "an array", stored["open_steps"])
    seen = {}
    for index, value in enumerate(stored["open_steps"]):
        where = f"{place}.open_steps[{index}]"
        first = seen.setdefault(_identity(where, value), index)
        if first != index:
            raise InvalidStateError(f"{where}: repeats open_steps[{first}]")
    totals = MappingProxyType(dict(stored["totals"]))
    return journal.SpendView(totals, stored["position"], frozenset(seen))


def _identity(place, value):
    _members(place, value, _IDENTITY[3:], _NUMBERS)
    for name, member in value.items():
        if member is None:
            _fail(f"{place}.{name}", "left out when absent, never null", member)
    try:
        return journal.step_identity(**value)
    except ValueError as error:
        message = str(error).removeprefix("data.")
        raise InvalidStateError(f"{place}.{message}") from None


def _stored(identity):
    members = zip(_IDENTITY, (*identity[2:], *identity[:2]))
    return {name: value for name, value in members if value is not None}


def _order(identity):
    numbers = (-1 if number is None else number for number in identity[2:])
    return (*numbers, identity.step, identity.execution)
