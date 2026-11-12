"""The tool function of ``correctness.check``, for the part of a call the records fix.

``ARCHITECTURE/decisions/ADR-0048-od18-correctness-check-seed-draw.md``
decision 10 is the order of a call; ADR-0021 and ADR-0040 to ADR-0047 are the
rules of its moments, ADR-0056 decision 3 is the rule of the output path,
and ADR-0078 decisions 6 and 7 are the rules of the compiler's log.
:func:`tool_function` joins the modules that render them, over
:func:`hilclaw.hw_tool.stepped_tool_function`:

1. The request is checked: the frame, then the member list and ``point``
   (:func:`hilclaw.check_identity.check`; ADR-0040 decisions 4 and 5,
   ADR-0069 decisions 2 and 3). The ``step`` follows from ``point`` alone
   (:func:`hilclaw.check_identity.step_of`; ADR-0183 decision 2), whatever
   contract the run states.
2. The data root and the layout version stamp, as :mod:`hilclaw.hw_tool`
   has them, and the lookup under the ``step``. An identity open under a
   value ADR-0183 retired is a line of another step and is not taken as
   open (ADR-0100 decision 5).
3. For an identity with no line ``instance.json`` is read, by
   :func:`hilclaw.instance.read` and, for a file of another version, by
   :func:`hilclaw.instance.read_given`, so a run of the candidate kind
   ``c_kernel`` or ``compile_settings`` is read (ADR-0198 decision 8, row 6)
   and a run of any other kind is ``run_file_unsupported``. A version-3 run,
   which states given code, is read when its kind is ``c_kernel`` and is
   ``run_file_unsupported`` otherwise (ADR-0200 decision 7, row 3); its
   attempts are evaluated as those of any C kernel run, from their
   ``output/``, the given attempt ``(0, 1, 1)`` among them; the backend is
   selected for the hw_profile of that read. Then :func:`hilclaw.check_admission.admit`
   gives one of its four answers or what the check takes from the same
   read (ADR-0046 decision 8): a record ``covers`` answers ``True`` for is
   admitted whatever its ``dtype`` (ADR-0183 decision 2). ``covers`` is read
   at the target of the hw_profile's ``accelerator``
   (:func:`hilclaw.targets.covers_at`; ADR-0197 decision 3): where that
   ``accelerator`` has a :class:`hilclaw.targets.Target`, a record of a
   contract the target does not serve is ``op_signature_not_covered``; for
   the mock it is ``covers`` itself.
4. The source of seeds is asked once, by :func:`hilclaw.check_seed.draw`
   (ADR-0048 decisions 3 to 5).
5. The start line is appended.
6. The output path and the path of the file of the compiler's log are
   formed (for a ``compile_settings`` run see below), a new log keeper is
   made, and :func:`hilclaw.check_seed.check`
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
   (ADR-0040 decision 6). The result is the v2 result of ADR-0183
   decision 3 for every contract (:mod:`hilclaw.check_answer`).

In a run whose candidate kind is ``compile_settings`` (ADR-0198 decisions 2,
5 and 6) the attempt's spec is read in 6, after the start line, by
:func:`hilclaw.build_record.evaluated`. A version-2 spec is evaluated as in a
C kernel run, and so is every attempt of a ``c_kernel`` run, whose spec is
not read. For a version-3 spec the output path is that of the attempt the
spec names, the operation is called with the spec's
:class:`hilclaw.build_record.CandidateBuild` current
(:func:`hilclaw.build_record.building`), so that an operation that builds
adds the candidate's flags after the target's, and when the operation came
back, by returning or by a tool failure, the build is written to the
attempt's ``build.json`` if a build ended and the name is free
(:meth:`hilclaw.build_record.CandidateBuild.write`), before the end line. A
spec or a named attempt that gives no kernel ends the step with the kind and
the message of :class:`hilclaw.build_record.KernelRefused`, a backend kind
of a missing or unreadable kernel, and no operation is called; a refused
candidate flag is the operation's ``settings_refused``. Neither writes a
``build.json``, and neither does a call whose operation builds nothing.

Choices that are this module's own and no rule of a record:

* The names and the signature. The source of seeds and the predicate
  "covered" are parameters without a default (ADR-0021 decision 3 and
  ADR-0048 decision 9 leave to the code how a source is bound).
* What the place before the start line hands to the step is an object of a
  private class with three slots, the admitted check, the seed and the
  ``step`` of the call, alive for that call only. Its ``repr`` shows none of
  them.
* A ``seeds`` or a ``covers`` that is not callable is refused at building.
* The output path is the :class:`pathlib.Path` that
  :func:`hilclaw.layout.attempt_artefact` returns for the data root of the
  call, the members ``run_id``, ``round``, ``candidate`` and ``attempt`` of
  the request (of the named attempt, for a version-3 spec) and the name
  ``output``, as it is: not resolved and not made
  absolute, so that it does not depend on the working directory. It is
  formed once for a call, after the start line, and handed on as that one
  object.
* The path of the log file is the :class:`pathlib.Path` that
  :func:`hilclaw.layout.build_log_file` returns for the same data root and
  four members, the ``step`` of the identity of the call and the member
  ``execution``, formed with the output path and handed on as
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
output path and hands it on; but for the reads of
:func:`hilclaw.build_record.evaluated` in a ``compile_settings`` run it reads
nothing there, does not test whether the path or anything above it exists,
and composes no message that holds the path.
It writes the file of the compiler's log only through
:func:`hilclaw.check_seed.check`, which writes it by
:func:`hilclaw.build_log.write`; the message of ``build_log_unwritable`` is
that module's and shows no path, no text of an error and no byte of the log.
It says nothing of flags or of time limits; a candidate's flags reach the
operation through :mod:`hilclaw.build_record`. It binds no source of seeds, no
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
:mod:`hilclaw.build_record`, :mod:`hilclaw.check_admission`,
:mod:`hilclaw.check_ending`, :mod:`hilclaw.check_identity`,
:mod:`hilclaw.check_seed`, :mod:`hilclaw.hw_tool`, :mod:`hilclaw.instance`,
:mod:`hilclaw.journaled_step`, :mod:`hilclaw.layout` and
:mod:`hilclaw.targets` and nothing else.
"""

from hilclaw import (
    build_log,
    build_record,
    check_admission,
    check_ending,
    check_identity,
    check_seed,
    hw_tool,
    instance,
    journaled_step,
    layout,
    targets,
)

_TOOL = "correctness.check"
_C_KERNEL = "c_kernel"
_EVALUATED_KINDS = (_C_KERNEL, "compile_settings")


class _Drawn:
    __slots__ = ("admitted", "kind", "seed", "step")

    def __init__(self, admitted, seed, step, kind):
        self.admitted = admitted
        self.seed = seed
        self.step = step
        self.kind = kind


def tool_function(*, source, table, seeds, covers):
    """Return the tool function of ``correctness.check`` that these four state.

    - ``source``: the data-root source, as
      :func:`hilclaw.hw_tool.stepped_tool_function` takes it.
    - ``table``: the :class:`hilclaw.backends.BackendTable` the tool is bound
      to.
    - ``seeds``: the source of seeds, a callable without arguments
      (:mod:`hilclaw.harness.seed_source`).
    - ``covers``: the predicate of ADR-0041 decision 5, handed to
      :func:`hilclaw.check_admission.admit` read at the target of the run
      (:func:`hilclaw.targets.covers_at`).

    No parameter has a default. Raises :class:`TypeError`, in this order: when
    ``table`` is no ``BackendTable``; when ``source`` is not callable; when
    ``seeds`` is not callable; when ``covers`` is not callable. Building calls
    none of the three, reads no file and asks the table nothing.

    The function returned takes one request and returns the result of the
    check, a ``dict`` (ADR-0183 decision 3). The module docstring has the order of a
    call. It raises :class:`hilclaw.tools.ToolFailure` as the function of
    :func:`hilclaw.hw_tool.stepped_tool_function` does, ``invalid_request``
    for the member ``point`` included; of one of
    :data:`hilclaw.check_admission.KINDS` and then of
    :data:`hilclaw.check_seed.KIND_SEED_NOT_DRAWN`, each with no line appended
    and no operation called, so that the same request can be repeated; and of
    the kind of the ``failure`` an end line holds, for a check that made no
    result, ``build_log_unwritable`` among them. For none of the answers
    before the draw is ``seeds`` called.

    Everything else passes through unchanged, whatever it is: what
    ``covers`` raises, what building the run's target raises and what
    ``seeds`` raises that is no :class:`Exception`, with no line appended;
    and what
    :func:`hilclaw.check_seed.check` raises that is no
    :class:`hilclaw.check_ending.EndedWithoutOutcome`, after the start line,
    which leaves the identity open (:mod:`hilclaw.journaled_step`); a
    request to end the operation raises is among them, and no log is
    written for it.

    The function does not modify the request or the table and keeps nothing
    between calls.
    """

    def admit(request, read):
        run, kind = read
        at_target = targets.covers_at(covers, run.hw_profile["accelerator"])
        admitted = check_admission.admit(run, covers=at_target)
        step = check_identity.step_of(request)
        return _Drawn(admitted, check_seed.draw(seeds), step, kind)

    function = hw_tool.stepped_tool_function(
        tool=_TOOL,
        steps=check_identity.STEPS,
        step_of=check_identity.step_of,
        numbers=check_identity.NUMBERS,
        source=source,
        table=table,
        read=_read,
        hw_profile_in=_hw_profile,
        check=check_identity.check,
        admit=admit,
        perform=_perform,
    )
    for name, value in (("seeds", seeds), ("covers", covers)):
        if not callable(value):
            raise TypeError(f"{name}: must be callable")
    return function


def _read(data_root, run_id):
    try:
        return instance.read(data_root, run_id), _C_KERNEL
    except instance.UnsupportedVersionError:
        given = instance.read_given(data_root, run_id)
    if given.candidate_kind not in _EVALUATED_KINDS:
        raise instance.UnsupportedVersionError(
            f"runs/{run_id}/instance.json: states the candidate kind "
            f"{given.candidate_kind}; this tool evaluates "
            f"{' and '.join(_EVALUATED_KINDS)} runs only"
        )
    if given.given_code is not None and given.candidate_kind != _C_KERNEL:
        raise instance.UnsupportedVersionError(
            f"runs/{run_id}/instance.json: states given code with the candidate "
            f"kind {given.candidate_kind}; this tool evaluates given code of "
            f"{_C_KERNEL} runs only"
        )
    return given.instance, given.candidate_kind


def _hw_profile(read):
    return read[0].hw_profile


def _perform(data_root, request, hw_profile, operation, drawn):
    attempt = (
        data_root,
        request["run_id"],
        request["round"],
        request["candidate"],
        request["attempt"],
    )
    log_path = layout.build_log_file(*attempt, drawn.step, request["execution"])
    try:
        evaluated = _evaluated(drawn.kind, attempt)
    except build_record.KernelRefused as refused:
        raise journaled_step.StepFailed({}, refused.kind, refused.message) from None
    with build_record.building(evaluated.build):
        try:
            result = check_seed.check(
                operation,
                request,
                hw_profile,
                drawn.admitted,
                drawn.seed,
                evaluated.output_path,
                build_log.LogKeeper(),
                log_path=log_path,
            )
        except check_ending.EndedWithoutOutcome as ended:
            kind, message = ended.kind, ended.message
            result = None
    if evaluated.build is not None:
        evaluated.build.write()
    if result is not None:
        return {}, result
    raise journaled_step.StepFailed({}, kind, message)


def _evaluated(kind, attempt):
    if kind == _C_KERNEL:
        return build_record.Evaluated(layout.attempt_artefact(*attempt, "output"), None)
    return build_record.evaluated(*attempt)
