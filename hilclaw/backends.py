"""Backends of the HW tools, the backend table and the selection (ADR-0016 decisions 2 to 4).

A *HW tool* is one of the four of :data:`HW_TOOLS`. A *backend* has a name,
which is an ``accelerator`` value of a hw_profile record (ADR-0001 decision 1),
and one *operation* for each HW tool it offers; it need offer none. The
*backend table* maps a name to a backend, and a name has one backend. A table
is built in one step from the backends it is handed, and nothing adds to it
afterwards: no option, variable of the front process, entry point or plugin.

Nobody names a backend. :func:`select` returns the operation of a HW tool for
a hw_profile record: the backend is the entry of the table under the
``accelerator`` of that record, and no other field of the record selects. Two
situations are a :class:`hilclaw.tools.ToolFailure` of a reserved kind:
``no_backend`` when the table has no entry for the ``accelerator``, and
``not_offered`` when the backend selected has no operation for the tool. The
selection calls no operation, so a failed selection has called nothing.

A record that is no valid hw_profile record is neither of the two: what
:func:`hilclaw.keys.hw_profile_key` raises for it passes through unchanged and
is none of the four kinds of a frame file of a run (ADR-0019 decision 4).

Limits it does not remove (ADR-0016 decision 6): the target a backend reaches
is not checked against the other key fields of the record, a backend that does
not answer the contract of a tool is not detected, and two processes hold two
tables.

It defines no backend and no tool, holds no table, reads no file, no
configuration and no variable of the process, and keeps nothing between calls.
"""

import re
from collections.abc import Mapping

from hilclaw import keys, tools

#: The four HW experiment tools (FR-10; ADR-0016 decision 1).
HW_TOOLS = ("sim.run", "board.run", "profiler.collect", "correctness.check")

_NAME = re.compile(r"[a-z][a-z0-9_]{0,31}")


def _hw_tool(tool):
    if type(tool) is not str:
        raise TypeError(f"a HW tool name must be a str, got {type(tool).__name__}")
    if tool not in HW_TOOLS:
        raise ValueError(f"{tool!r} is no HW tool; the HW tools are {HW_TOOLS}")
    return tool


class Backend:
    """A backend: its name and one operation for each HW tool it offers.

    - ``name``: the ``accelerator`` value the backend belongs to, a name
      (``[a-z][a-z0-9_]{0,31}``, ADR-0001), exactly a ``str``.
    - ``operations``: a mapping from a HW tool name (one of :data:`HW_TOOLS`)
      to the operation of that tool, a callable. It may be empty. The backend
      keeps a copy of it.

    Raises :class:`TypeError` when ``name`` or the name of a member of
    ``operations`` is no ``str``, ``operations`` no mapping or an operation not
    callable, and :class:`ValueError` when ``name`` is no name or a member of
    ``operations`` is under no HW tool name. Building calls no operation.

    A backend does not change after it is built. Two backends are equal only
    when they are the same object.
    """

    __slots__ = ("_name", "_operations")

    def __init__(self, name, operations):
        if type(name) is not str:
            raise TypeError(f"a backend name must be a str, got {type(name).__name__}")
        if not _NAME.fullmatch(name):
            raise ValueError(f"{name!r} is not a name matching {_NAME.pattern}")
        if not isinstance(operations, Mapping):
            raise TypeError(f"the operations of {name} must be a mapping")
        held = {}
        for tool, operation in operations.items():
            if not callable(operation):
                raise TypeError(f"the operation of {name} for {tool!r} is not callable")
            held[_hw_tool(tool)] = operation
        self._name = name
        self._operations = held

    @property
    def name(self):
        """The name of the backend, an ``accelerator`` value."""
        return self._name

    def offered(self):
        """Return the names of the HW tools the backend offers as a sorted tuple."""
        return tuple(sorted(self._operations))

    def __repr__(self):
        return f"Backend({self._name!r}, offered={self.offered()!r})"


class BackendTable:
    """The backend table: from a name to the one backend of that name.

    ``backends`` is an iterable of :class:`Backend`; it may be empty. Raises
    :class:`TypeError` when it is not iterable or an entry is no ``Backend``
    and :class:`ValueError` when two entries have one name.

    A table does not change after it is built: a later change of ``backends``
    changes nothing, and nothing registers a further backend. Two tables are
    equal only when they are the same object.
    """

    __slots__ = ("_backends",)

    def __init__(self, backends):
        held = {}
        for backend in backends:
            if not isinstance(backend, Backend):
                raise TypeError(
                    f"an entry of a backend table must be a Backend, got {type(backend).__name__}"
                )
            if backend._name in held:
                raise ValueError(f"the backend {backend._name} is given twice")
            held[backend._name] = backend
        self._backends = held

    def names(self):
        """Return the names of the backends of the table as a sorted tuple."""
        return tuple(sorted(self._backends))

    def __repr__(self):
        return f"BackendTable({self.names()!r})"


def select(table, hw_profile, tool):
    """Return the operation of the HW tool ``tool`` of the backend that ``hw_profile`` selects.

    - ``table``: the :class:`BackendTable` to select from.
    - ``hw_profile``: a hw_profile record (ADR-0001 decision 1), validated in
      full by :func:`hilclaw.keys.hw_profile_key`; it is not modified and not
      kept. Only its ``accelerator`` selects.
    - ``tool``: one of :data:`HW_TOOLS`.

    The operation returned is the object the backend was built with; it is not
    called here.

    Raises, in this order: :class:`TypeError` when ``table`` is no
    ``BackendTable`` or ``tool`` no ``str`` and :class:`ValueError` when
    ``tool`` is no HW tool;
    :class:`hilclaw.keys.InvalidRecordError`, unchanged, when ``hw_profile`` is
    no valid record; :class:`hilclaw.tools.ToolFailure` of kind ``no_backend``
    when the table has no entry under the ``accelerator`` of the record, and of
    kind ``not_offered`` when that entry has no operation for ``tool``.
    """
    if not isinstance(table, BackendTable):
        raise TypeError(f"a BackendTable is required, got {type(table).__name__}")
    _hw_tool(tool)
    keys.hw_profile_key(hw_profile)
    accelerator = hw_profile["accelerator"]
    backend = table._backends.get(accelerator)
    if backend is None:
        raise tools.ToolFailure(
            tools.KIND_NO_BACKEND,
            f"the backend table has no entry for the accelerator {accelerator}",
        )
    operation = backend._operations.get(tool)
    if operation is None:
        raise tools.ToolFailure(
            tools.KIND_NOT_OFFERED,
            f"the backend {accelerator} offers no operation for {tool}",
        )
    return operation
