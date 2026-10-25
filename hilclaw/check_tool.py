"""The tool function of ``correctness.check``, for the part of a call the records fix.

``ARCHITECTURE/decisions/ADR-0048-od18-correctness-check-seed-draw.md``
decision 10 is the order of a call; ADR-0021 and ADR-0040 to ADR-0047 are the
rules of its moments, ADR-0056 decision 3 is the rule of the output path,
and ADR-0078 decisions 6 and 7 are the rules of the compiler's log.
:func:`tool_function` joins the modules that render them, over
:func:`hilclaw.hw_tool.stepped_tool_function`:

1. The request is checked: the frame, then the member list and ``point``
   (:func:`hilclaw.check_identity.check`), and the ``step`` follows from
   ``point`` (ADR-0040 decisions 3 to 5, ADR-0069 decisions 2 and 3).
2. The data root, the layout version stamp and the lookup, as
   :mod:`hilclaw.hw_tool` has them.
3. For an identity with no line ``instance.json`` is read once, by
   :func:`hilclaw.instance.read`, and the backend is selected for the
   hw_profile of that read. Then :func:`hilclaw.check_admission.admit` gives
   one of its four answers or what the check takes from the same read
   (ADR-0046 decision 8).
4. The source of seeds is asked once, by :func:`hilclaw.check_seed.draw`
   (ADR-0048 decisions 3 to 5).
5. The start line is appended.
6. The output path and the path of the file of the compiler's log are
   formed, a new log keeper is made, and :func:`hilclaw.check_seed.check`
   calls the operation with the request, the hw_profile, the check
   parameters, the seed among them, the output path (ADR-0056 decision 3)
   and the keeper (ADR-0078 decision 6). When the operation came back, by
   returning or by raising an error, and handed over a log, the log is
   written to its file before the answer is judged (ADR-0078 decision 7).
   A raised request to end passes through, and nothing is written.
7. The end line is appended with the result, or with the ``failure`` of a
   check that made none (ADR-0045 decision 3, ADR-0047 decision 3), that of
   ``build_log_unwritable`` included when the write of the log failed
   (ADR-0078 decision 7), and in all cases with the empty ``spend``
   (ADR-0040 decision 6).

Choices that are this module's own and no rule of a record:

* The names and the signature. The source of seeds and the predicate
  "covered" are parameters without a default (ADR-0021 decision 3 and
  ADR-0048 decision 9 leave to the code how a source is bound).
* What the place before the start line hands to the step is an object of a
  private class with two slots, alive for that call only. Its ``repr`` shows
  neither slot.
* A ``seeds`` or a ``covers`` that is not callable is refused at building.
* The output path is the :class:`pathlib.Path` that
  :func:`hilclaw.layout.attempt_artefact` returns for the data root of the
  call, the members ``run_id``, ``round``, ``candidate`` and ``attempt`` of
  the request and the name ``output``, as it is: not resolved and not made
  absolute, so that it does not depend on the working directory. It is
  formed once for a call, after the start line, and handed on as that one
  object.
* The path of the log file is the :class:`pathlib.Path` that
  :func:`hilclaw.layout.build_log_file` returns for the same data root and
  four members, the ``step`` of :func:`hilclaw.check_identity.step_of` and
  the member ``execution``, formed with the output path and handed on as
  it is. The keeper is a new :class:`hilclaw.build_log.LogKeeper`, made
  there too, one for each call that reaches the operation; a call answered
  before the start line makes none.
* The five members are read from the request without a check of this
  module. It relies on the frame, which has checked their presence, types
  and bounds before the start line, and those bounds are the ones
  ``attempt_artefact`` and ``build_log_file`` accept.

What the module does not do: it registers nothing and defines no tool. The
member list of a request is closed at six (ADR-0069 decisions 2 and 3), and
the input schema and the description of the tool are those of
:mod:`hilclaw.check_definition`, which this module does not import. The
function becomes the tool a registry offers once a backend table, a source of
seeds and a predicate "covered" are bound; the default registry binds them
(ADR-0070), this module does not. It looks at no value but that of
``point`` and of the five the two paths are formed from, and hands the
request on as the caller gave it. Of the kernel of the attempt it forms the
output path and hands it on; it reads nothing there, does not test whether the
path or anything above it exists, and composes no message that holds the path.
It writes the file of the compiler's log only through
:func:`hilclaw.check_seed.check`, which writes it by
:func:`hilclaw.build_log.write`; the message of ``build_log_unwritable`` is
that module's and shows no path, no text of an error and no byte of the log.
It says nothing of flags or of time limits. It binds no source of seeds, no
predicate, no backend, no table and no script, and no parameter has a default.
It names no kind, no ``step`` value and no member of its own, and composes the
message of no tool failure. It composes no message that holds a seed. The end
line holds the message of a backend kind an operation raised, where it is
exactly a ``str``, as it was raised (ADR-0047 decision 4), so a path or a seed
in that message reaches ``events.ndjson``. By the records such a message shows
no path (ADR-0056 decision 6 for the two kinds it names, ADR-0060 decision 5
for the six of its decision 4) and has no content that holds the seed
(ADR-0047 decision 4, citing ADR-0021 decision 3); nothing detects a message
that breaks this. It gives no rule for another HW tool and keeps nothing
between calls. It imports :mod:`hilclaw.build_log`,
:mod:`hilclaw.check_admission`,
:mod:`hilclaw.check_ending`, :mod:`hilclaw.check_identity`,
:mod:`hilclaw.check_seed`, :mod:`hilclaw.hw_tool`, :mod:`hilclaw.instance`,
:mod:`hilclaw.journaled_step` and :mod:`hilclaw.layout` and nothing else.
"""

from hilclaw import (
    build_log,
    check_admission,
    check_ending,
    check_identity,
    check_seed,
    hw_tool,
    instance,
    journaled_step,
    layout,
)

_TOOL = "correctness.check"


class _Drawn:
    __slots__ = ("admitted", "seed")

    def __init__(self, admitted, seed):
        self.admitted = admitted
        self.seed = seed


def tool_function(*, source, table, seeds, covers):
    """Return the tool function of ``correctness.check`` that these four state.

    - ``source``: the data-root source, as
      :func:`hilclaw.hw_tool.stepped_tool_function` takes it.
    - ``table``: the :class:`hilclaw.backends.BackendTable` the tool is bound
      to.
    - ``seeds``: the source of seeds, a callable without arguments
      (:mod:`hilclaw.harness.seed_source`).
    - ``covers``: the predicate of ADR-0041 decision 5, handed to
      :func:`hilclaw.check_admission.admit` as it is.

    No parameter has a default. Raises :class:`TypeError`, in this order: when
    ``table`` is no ``BackendTable``; when ``source`` is not callable; when
    ``seeds`` is not callable; when ``covers`` is not callable. Building calls
    none of the three, reads no file and asks the table nothing.

    The function returned takes one request and returns the result of the
    check, a ``dict`` (ADR-0042). The module docstring has the order of a
    call. It raises :class:`hilclaw.tools.ToolFailure` as the function of
    :func:`hilclaw.hw_tool.stepped_tool_function` does, ``invalid_request``
    for the member ``point`` included; of one of
    :data:`hilclaw.check_admission.KINDS` and then of
    :data:`hilclaw.check_seed.KIND_SEED_NOT_DRAWN`, each with no line
    appended and no operation called, so that the same request can be
    repeated; and of the kind of the ``failure`` an end line holds, for a
    check that made no result, ``build_log_unwritable`` among them. For none of the answers before the draw is
    ``seeds`` called.

    Everything else passes through unchanged, whatever it is: what
    ``covers`` raises and what ``seeds`` raises that is no
    :class:`Exception`, with no line appended; and what
    :func:`hilclaw.check_seed.check` raises that is no
    :class:`hilclaw.check_ending.EndedWithoutOutcome`, after the start line,
    which leaves the identity open (:mod:`hilclaw.journaled_step`); a
    request to end the operation raises is among them, and no log is
    written for it.

    The function does not modify the request or the table and keeps nothing
    between calls.
    """

    def admit(request, read):
        admitted = check_admission.admit(read, covers=covers)
        return _Drawn(admitted, check_seed.draw(seeds))

    function = hw_tool.stepped_tool_function(
        tool=_TOOL,
        steps=check_identity.STEPS,
        step_of=check_identity.step_of,
        numbers=check_identity.NUMBERS,
        source=source,
        table=table,
        read=instance.read,
        hw_profile_in=_hw_profile,
        check=check_identity.check,
        admit=admit,
        perform=_perform,
    )
    for name, value in (("seeds", seeds), ("covers", covers)):
        if not callable(value):
            raise TypeError(f"{name}: must be callable")
    return function


def _hw_profile(read):
    return read.hw_profile


def _perform(data_root, request, hw_profile, operation, drawn):
    attempt = (
        data_root,
        request["run_id"],
        request["round"],
        request["candidate"],
        request["attempt"],
    )
    output_path = layout.attempt_artefact(*attempt, "output")
    log_path = layout.build_log_file(
        *attempt, check_identity.step_of(request), request["execution"]
    )
    try:
        result = check_seed.check(
            operation,
            request,
            hw_profile,
            drawn.admitted,
            drawn.seed,
            output_path,
            build_log.LogKeeper(),
            log_path=log_path,
        )
    except check_ending.EndedWithoutOutcome as ended:
        kind, message = ended.kind, ended.message
    else:
        return {}, result
    raise journaled_step.StepFailed({}, kind, message)
