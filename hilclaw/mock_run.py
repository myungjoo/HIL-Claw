"""The mock's side of ``sim.run`` and ``board.run``: their operations and the default script.

``ARCHITECTURE/decisions/ADR-0066-od18-run-tools-mock-script.md`` is the
rule; a decision cited by its number alone is one of that record. The module
renders its decisions 2 to 4, with the five things an operation of either
run tool is called with: the four of ADR-0065 decision 2 and the log keeper
of ``ARCHITECTURE/decisions/ADR-0108-od18-run-tools-timing-build-compiler-log.md``
decision 5, which its decision 8 adds to the things a script is asked with:

* :func:`operation`: the mock's operation of one of the two tools bound to a
  script (decision 2). The script is asked once for each call, with the
  called tool and the five things the operation was called with, as they
  are, and its answer is the operation's answer. The operation does not look
  at it. A script may hand a log to the keeper, which the tool function then
  writes as any other (ADR-0108 decision 8).
* :func:`default_script`: what the default script answers for either tool
  (decisions 3 and 4): the pair of a report of ``n_min`` equal intervals
  that is converged, and ``None`` as the figure, alike for both tools. It
  hands over no log (ADR-0108 decision 8), so a run at the mock with it
  leaves no file of a compiler's log.

Choices that are this module's own and no rule of a record:

* The tool is named when an operation is built: ``operation("sim.run",
  script)`` or ``operation("board.run", script)``. A ``tool`` that is not
  exactly a ``str`` raises :class:`TypeError`; a ``str`` other than these
  two raises :class:`ValueError`, the names of the other HW tools included.
* One script callable may serve both tools; the called tool tells them
  apart. A script is asked with six positional things:
  ``script(tool, request, hw_profile, parameters, output_path, keeper)``,
  the keeper last. An operation is called with the five positional things
  of :func:`hilclaw.run_operation.ask` and no keyword.
* ``n_min`` is read from :data:`hilclaw.harness.measurement.N_MIN` of the
  same source commit (decision 4) when this module is imported, and the
  report is built once then. ``CV_MAX`` is not read.
* The report is spelt with the one digit spelling of
  :func:`hilclaw.harness.timing.parse_report`. Each call returns a new
  ``tuple`` holding the one report object.

What the module does not do: it builds no backend and no backend table and
is bound to no registry; the default registry holds these operations with
the default script through :func:`hilclaw.check_definition.default_table`
(ADR-0167 decision 3). It injects no fault (OD-18 sub-question 8, open).
It has no tool function and registers nothing. It
judges nothing, builds no result, appends no line and records no spend. It
looks at nothing at the output path, writes no file and hands no log over of
its own. It reads no clock, random source, counter, file or environment
variable, starts no process and keeps nothing between calls. It imports
:mod:`hilclaw.harness.measurement` and nothing else.
"""

from hilclaw.harness import measurement

_TOOLS = ("sim.run", "board.run")

_REPORT = (
    b"resolution_ns 1\n"
    + b"interval_ns 1000000\n" * measurement.N_MIN
    + b"stop converged\n"
)


class _Operation:
    __slots__ = ("_script", "_tool")

    def __init__(self, tool, script):
        self._tool = tool
        self._script = script

    def __call__(self, request, hw_profile, parameters, output_path, keeper, /):
        return self._script(
            self._tool, request, hw_profile, parameters, output_path, keeper
        )

    def __repr__(self):
        return f"<operation of the mock backend for {self._tool!r}>"


def operation(tool, script):
    """Return the mock's operation of ``tool`` bound to ``script``.

    - ``tool``: ``"sim.run"`` or ``"board.run"``.
    - ``script``: a callable asked as
      ``script(tool, request, hw_profile, parameters, output_path, keeper)``.

    The operation returned is called as
    ``operation(request, hw_profile, parameters, output_path, keeper)``, with
    exactly these five positional arguments: the request, the hw_profile of
    the call, the timing parameters and the output path (ADR-0065
    decision 2) and the log keeper (ADR-0108 decision 5). It asks the script
    once with ``tool`` and the five objects as they are, none derived,
    replaced, left out or added (ADR-0108 decision 8), and returns the object
    the script returned, whatever it is. It looks at none of the five, at
    nothing at the output path and not at the answer, and it catches
    nothing: whatever the script raises passes through unchanged, a
    :class:`hilclaw.tools.ToolFailure` of any kind as well as any other
    :class:`BaseException`.

    The operation can be given to :class:`hilclaw.backends.Backend` as the
    operation of ``tool``; this function builds no backend.

    Raised before anything is built, in this order: :class:`TypeError` when
    ``tool`` is not exactly a ``str``; :class:`ValueError` when it is a
    ``str`` other than the two; :class:`TypeError` when ``script`` is not
    callable. Building asks the script nothing.
    """
    if type(tool) is not str:
        raise TypeError(f"tool: must be a str, got {type(tool).__name__}")
    if tool not in _TOOLS:
        raise ValueError(f"tool: must be one of {_TOOLS}")
    if not callable(script):
        raise TypeError("the script of a mock operation must be callable")
    return _Operation(tool, script)


def default_script(tool, request, hw_profile, parameters, output_path, keeper):
    """Return the default script's answer for ``sim.run`` or ``board.run``.

    The six parameters are those a script is asked with. None of them is
    read, checked, converted or modified, whatever its type, and nothing at
    the output path is looked at (decision 3). The keeper is handed no log
    and not looked at (ADR-0108 decision 8).

    The answer is the pair ``(report, None)`` of the form (A) of ADR-0065
    decision 4, a ``tuple`` of length 2. ``report`` is ``bytes`` holding the
    ASCII lines ``resolution_ns 1``, then
    :data:`hilclaw.harness.measurement.N_MIN` lines
    ``interval_ns 1000000``, then ``stop converged``, each ended by one LF,
    and nothing else; ``None`` says that no figure was obtained (decision 4).
    The answer is the same for every call and both tools, a bf16 call
    included (ADR-0181 decision 9). It is never one of
    the strings of the form (B), and the function raises nothing.
    """
    return (_REPORT, None)
