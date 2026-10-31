"""The JSON text rules that several file readers of the package repeat.

The readers of :mod:`hilclaw.spec_file`, :mod:`hilclaw.hypotheses_file`,
:mod:`hilclaw.verdicts_file`, :mod:`hilclaw.cases_file`,
:mod:`hilclaw.artifacts`, :mod:`hilclaw.events`, :mod:`hilclaw.instance`,
:mod:`hilclaw.key_records` and :mod:`hilclaw.run_state` give their text to
:func:`json.loads`. This module is what those calls have in common, once. It
adds no rule; each rule belongs to the records of the reader that applies it
(for a spec file, ``ARCHITECTURE/decisions/ADR-0029-od8-spec-file.md``
decision 2):

- no member name twice in any object (:func:`distinct_members`);
- ``NaN``, ``Infinity`` and ``-Infinity`` are no JSON (:func:`no_constant`);
- the integer literal ``-0`` is found in a second parse of the text, because an
  interpreter reads it as the ``int`` 0 (:func:`mark_minus_zero`,
  :func:`refuse_minus_zero`).

What stays in the readers: which of these rules a reader applies, the decoding,
the byte order mark, the version rule, the wrapping of a ``ValueError`` into a
reader's own error, the error class of a ``-0``, which paths a walk starts from
and which it skips. It reads no file and is no tool.
"""

_MINUS_ZERO = object()


def distinct_members(pairs):
    """Return the ``dict`` of ``pairs``, in order; for ``object_pairs_hook``.

    Raises :class:`ValueError` when a member name occurs twice.
    """
    members = dict(pairs)
    if len(members) != len(pairs):
        raise ValueError("a JSON object repeats a member name")
    return members


def no_constant(name):
    """Refuse the literal ``name``; for ``parse_constant``.

    Always raises :class:`ValueError`, since :func:`json.loads` calls this only
    for ``NaN``, ``Infinity`` and ``-Infinity``.
    """
    raise ValueError(f"{name} is not a JSON value")


def mark_minus_zero(literal):
    """Return a mark for the literal ``-0`` and ``None`` for any other; for ``parse_int``.

    The result of such a parse holds no integer value and is only good for
    :func:`refuse_minus_zero`.
    """
    return _MINUS_ZERO if literal == "-0" else None


def refuse_minus_zero(path, value, error, skip=None):
    """Raise ``error`` for the first mark of :func:`mark_minus_zero` in ``value``.

    ``value`` is a parse with :func:`mark_minus_zero` and ``path`` the non-empty
    path of ``value``. The walk is in pre-order: object members in order, array
    items in order. The message is ``<path>: is written as -0, which is no
    integer``, where a member adds ``.<name>`` and an item ``[<index>]`` to the
    path.

    ``skip``, when given, is called with each path before its value is looked
    at; a true result leaves out that value and all below it.

    Returns ``None`` when no mark is found.
    """
    if skip is not None and skip(path):
        return
    if value is _MINUS_ZERO:
        raise error(f"{path}: is written as -0, which is no integer")
    if isinstance(value, dict):
        for name, item in value.items():
            refuse_minus_zero(f"{path}.{name}", item, error, skip)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            refuse_minus_zero(f"{path}[{index}]", item, error, skip)
