"""The mock backend (ADR-0016 decision 5).

The *mock backend* is a backend (:mod:`hilclaw.backends`) behind which there is
no hardware, no simulator, no other process and no network. Its name,
:data:`NAME`, is reserved for it. A call reaches one of its operations through
:func:`hilclaw.backends.select` with a table that holds it and a hw_profile
record whose ``accelerator`` is that name; this module offers no other way.

A mock backend is told what to produce by a *script*, the callable it is bound
to when it is built. A script is a function from a call - the called tool, the
request and the hw_profile - to what the operation does. It is asked when an
operation is called, once for each call, and at no other moment. The outcome of
the call is the script's: what it returns is returned and what it raises passes
through, and a script that ends the process ends it. The mock adds nothing of
its own - no clock, no random source, no counter, no file - and keeps nothing
between calls.

The kinds ``no_backend`` and ``not_offered`` are no matter of a script. They
come from the selection, before any operation is called: from a table without
the mock, and from a mock built without the operation of the called tool.

The mock of the default registry is not built here: it offers
``correctness.check`` with the operation and default script of
:mod:`hilclaw.mock_check` (ADR-0070), and ``sim.run`` and ``board.run`` with
those of :mod:`hilclaw.mock_run` (ADR-0167), in
:func:`hilclaw.check_definition.default_table`; each of those operations
takes five arguments, the log keeper the last. Fault injection in a live
session is not here either (OD-18 sub-question 8, open). The module defines
no script, no table and no tool, and holds no backend.
"""

from collections.abc import Mapping

from hilclaw import backends

#: The name reserved for the mock backend (ADR-0016 decision 5 (b)).
NAME = "mock"


class _Operation:
    __slots__ = ("_script", "_tool")

    def __init__(self, script, tool):
        self._script = script
        self._tool = tool

    def __call__(self, request, hw_profile, /):
        return self._script(self._tool, request, hw_profile)

    def __repr__(self):
        return f"<operation of the mock backend for {self._tool!r}>"


def backend(script, tools):
    """Return a mock backend bound to ``script`` that offers ``tools``.

    - ``script``: a callable asked as ``script(tool, request, hw_profile)``.
    - ``tools``: an iterable of the HW tools the mock offers, each one of
      :data:`hilclaw.backends.HW_TOOLS`; it may be empty. It is read once.

    The backend returned is a :class:`hilclaw.backends.Backend` named
    :data:`NAME` with one operation for each tool of ``tools``. An operation is
    called as ``operation(request, hw_profile)``, with exactly these two
    positional arguments: the request and the hw_profile of the call (ADR-0016
    decision 2). It asks the script once with its tool and the two objects as
    they are and returns the object the script returned. It catches nothing:
    whatever the script raises passes through unchanged, a
    :class:`hilclaw.tools.ToolFailure` of any kind as well as any other
    :class:`BaseException`.

    Raises :class:`TypeError` when ``script`` is not callable, ``tools`` is a
    ``str``, a mapping or not iterable or a tool is no ``str``, and
    :class:`ValueError` when a tool is no HW tool or is given twice. Building
    asks the script nothing.
    """
    if not callable(script):
        raise TypeError("the script of a mock backend must be callable")
    if isinstance(tools, (str, Mapping)):
        raise TypeError(
            "the tools of a mock backend must be an iterable of names, "
            f"not a {type(tools).__name__}"
        )
    named = list(tools)
    made = backends.Backend(NAME, {tool: _Operation(script, tool) for tool in named})
    if len(made.offered()) != len(named):
        raise ValueError(f"a tool is given twice among {named}")
    return made
