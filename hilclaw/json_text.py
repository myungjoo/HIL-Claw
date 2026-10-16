"""The JSON text rules that the readers of four data-plane files share.

``ARCHITECTURE/decisions/ADR-0029-od8-spec-file.md`` decision 2 fixes, for the
spec file, that a content is exactly one JSON text with no member name twice
in any object, and that a number at an *integer* place is not written ``-0``;
the tokens ``NaN``, ``Infinity`` and ``-Infinity`` are no JSON.
``ARCHITECTURE/decisions/ADR-0051-od6-spec-file-version-2.md`` carries these
rules over to version 2, and decision 2 of
``ARCHITECTURE/decisions/ADR-0059-od30-round-hypothesis-record.md``,
``ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md`` and
``ARCHITECTURE/decisions/ADR-0072-od30-hypothesis-outcome-case-file.md`` applies them to their
files. This module is the part of those rules that :mod:`hilclaw.spec_file`,
:mod:`hilclaw.hypotheses_file`, :mod:`hilclaw.verdicts_file` and
:mod:`hilclaw.cases_file` would otherwise each repeat: the two parses of one
text and the search for the first place written ``-0``.

What this module does not do: it decodes no bytes, checks no byte order mark
or version, validates no document, knows no file, member or record, and raises
no error class of a caller. Each caller keeps its error classes and messages,
the order of its checks and which members of a text it searches.
"""

import json

MINUS_ZERO = object()


def object_pairs(pairs):
    """Return the ``dict`` of ``pairs``, the members of one JSON object in text order.

    It is the ``object_pairs_hook`` of :func:`json.loads`. Raises
    :class:`ValueError` ``"a JSON object repeats a member name"`` when a name
    occurs twice in ``pairs``.
    """
    members = dict(pairs)
    if len(members) != len(pairs):
        raise ValueError("a JSON object repeats a member name")
    return members


def no_constant(name):
    """Refuse the token ``name`` (``NaN``, ``Infinity`` or ``-Infinity``).

    It is the ``parse_constant`` of :func:`json.loads`. Always raises
    :class:`ValueError` ``"<name> is not a JSON value"``.
    """
    raise ValueError(f"{name} is not a JSON value")


def integer_literal(literal):
    """Return :data:`MINUS_ZERO` when the integer literal ``literal`` is ``"-0"``, else ``None``.

    It is the ``parse_int`` of the spelling parse in :func:`load`.
    """
    return MINUS_ZERO if literal == "-0" else None


def load(text):
    """Return ``(document, spelling)``, the two parses of the JSON text ``text``.

    ``document`` is what :func:`json.loads` gives with :func:`object_pairs` and
    :func:`no_constant`. ``spelling`` is what it gives with
    :func:`integer_literal`: the same shape, with :data:`MINUS_ZERO` for each
    integer literal ``-0`` and ``None`` for every other one.

    The :class:`ValueError` (:class:`json.JSONDecodeError` among them) and the
    :class:`RecursionError` of either parse pass to the caller.
    """
    document = json.loads(
        text, object_pairs_hook=object_pairs, parse_constant=no_constant
    )
    spelling = json.loads(text, parse_int=integer_literal)
    return document, spelling


def minus_zero(path, value, skip=None):
    """Return the path of the first place written ``-0`` in ``value``, or ``None``.

    ``value`` is a part of a spelling of :func:`load` and ``path`` its path.
    The search is in pre-order: ``value`` itself, then the members of an
    object in order, each at ``f"{path}.{name}"`` (``name`` alone when
    ``path`` is ``""``), then the items of an array in order, each at
    ``f"{path}[{index}]"``. ``skip``, when given, is called with each path,
    ``path`` included, and a place for which it returns true is not searched,
    nor anything below it. Nothing is raised for a ``-0``; the caller raises
    its own error.
    """
    if skip is not None and skip(path):
        return None
    if value is MINUS_ZERO:
        return path
    if isinstance(value, dict):
        for name, item in value.items():
            found = minus_zero(f"{path}.{name}" if path else name, item, skip)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found = minus_zero(f"{path}[{index}]", item, skip)
            if found is not None:
                return found
    return None
