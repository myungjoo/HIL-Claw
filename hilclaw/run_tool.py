"""The tool function of ``sim.run`` and ``board.run``, for the part of a call the records fix.

``ARCHITECTURE/decisions/ADR-0062-od18-run-tools-call-identity.md``
decision 6 is the order of a call, with
``ARCHITECTURE/decisions/ADR-0067-od18-run-tools-admission-kinds.md``
decision 5 for the order of moment ④ and the place of the draw (ADR-0064
decisions 2 and 3). ADR-0061 decisions 3, 4 and 6 are the split between the
tool function and the operation, ADR-0183 decision 4 the result (the v2
result of ADR-0063's members, which ADR-0196 decision 2 keeps for the v3
result the tools write), ADR-0065 the form of an answer, ADR-0068 a
tool failure an operation raises and ADR-0108 the compiler's log of the
timing build. :func:`tool_function` joins the modules
that render them, over :func:`hilclaw.hw_tool.stepped_tool_function`:

1. ① The request is checked: the frame, then the member list
   (:func:`hilclaw.run_definition.check`; ADR-0106 decision 3). The
   ``step`` is the tool's one value, its v3 value
   (:func:`hilclaw.run_identity.step_of`; ADR-0062 decision 3, ADR-0196
   decision 2), at every target.
2. ②, ⓢ and ③: the data root, the layout version stamp and the lookup, as
   :mod:`hilclaw.hw_tool` has them. An ended identity is answered with what
   its end line holds and an open one with ``step_open``; nothing runs.
3. ④ For an identity with no line ``instance.json`` is read once, by
   :func:`hilclaw.instance.read` and, for a file of another version, by
   :func:`hilclaw.instance.read_kinded`, so a run of either candidate kind is
   read (ADR-0198 decision 8, row 6); the backend is selected for the
   hw_profile of that read (``no_backend``, ``not_offered``). Then
   :func:`hilclaw.run_admission.admit` gives one of its five answers or what
   the call takes from the same read (ADR-0067 decision 5, steps 3 to 7).
   Where the ``accelerator`` of that hw_profile has a
   :class:`hilclaw.targets.Target`, the predicate it is handed answers
   ``True`` only when ``covers`` does and the target serves the record's
   entry (:func:`hilclaw.contract_table.served_at`; ADR-0193 decision 4),
   so a record of a contract the target does not serve is
   ``op_signature_not_covered``; for the mock it is ``covers`` itself.
4. The source of seeds is asked once, by :func:`hilclaw.run_seed.draw`
   (ADR-0064 decisions 2 to 4; ADR-0067 decision 5).
5. ⑤ The start line is appended.
6. ⑥ The output path (ADR-0061 decision 3) and the path of the file of the
   compiler's log (ADR-0108 decision 3) are formed, a new log keeper is
   made, and :func:`hilclaw.run_operation.ask` calls the operation with the
   request, the hw_profile, the timing parameters (ADR-0065 decision 2 for
   fp32 ``gemm``, ADR-0181 decision 4 for a bf16 kind), the output path and
   the keeper (ADR-0108 decision 5), and writes the log it handed over, if
   any (ADR-0108 decision 7). An answer of the form (A) is judged with
   :func:`hilclaw.harness.timing.judge_report` for the sample form and
   ``n_max`` handed over (ADR-0061 decision 3): completed, converged or not
   converged, or broken with the condition of ADR-0063 decision 3 for the
   judgement. An answer of the form (B) is broken with that condition. The
   verdict is computed where a ``bound`` is stated (ADR-0063 decision 7), by
   :mod:`hilclaw.run_result`, which is handed the covering entry and the
   dimensions of the admitted run and, for a completed run, the unit and
   the judgement's resolution and intervals (ADR-0183 decision 4). The unit
   is the ``unit`` of the :class:`hilclaw.targets.Target` of the run's
   ``accelerator`` (ADR-0193 decision 4, ADR-0196 decision 3), and ``"ns"``
   for an ``accelerator`` with no target, the mock. After the judgement in
   ``ns``, which fixes ``outcome`` and ``condition``, the resolution and
   every interval are multiplied by the target's ``units_per_ns``, in
   integers and in their order (ADR-0196 decision 5); the mock's factor is
   1. ``memory_bytes`` is not converted. A raised request to end passes
   through, and nothing is written.
7. ⑦ The end line is appended with the result, or with the ``failure`` of a
   call that made none: ``operation_answer_invalid`` for an answer of
   neither form (ADR-0065 decision 7), the pair
   :func:`hilclaw.run_failure.ended_with` gives for a raised tool failure
   (ADR-0068 decision 4), or :data:`KIND_BUILD_LOG_UNWRITABLE` for a log
   handed over that could not be written, in place of every other answer
   (ADR-0108 decision 7); in all cases with the empty ``spend`` (ADR-0062
   decision 5).

In a run whose candidate kind is ``compile_settings`` (ADR-0198 decisions 2,
5 and 6) the attempt's spec is read in ⑥, after the start line, by
:func:`hilclaw.build_record.evaluated`, as :mod:`hilclaw.check_tool` does: a
version-2 spec is evaluated as in a C kernel run, and so is every attempt of
a ``c_kernel`` run, whose spec is not read; for a version-3 spec the output
path is that of the attempt the spec names, the operation is called with the
spec's :class:`hilclaw.build_record.CandidateBuild` current, and when the
operation came back, by returning or by raising an :class:`Exception`, the
build is written to the attempt's ``build.json`` if a build ended and the
name is free, before the end line. A spec or a named attempt that gives no
kernel ends the call with the kind of
:class:`hilclaw.build_record.KernelRefused` and calls no operation.

:data:`KIND_BUILD_LOG_UNWRITABLE` is the run tools' own kind of ADR-0108
decision 7, "defined again by this contract" with the spelling and the
meaning of the kind of ``correctness.check``
(:data:`hilclaw.build_log.KIND_BUILD_LOG_UNWRITABLE`); the tests hold the
two equal.

Choices that are this module's own and no rule of a record:

* The names and the signature. One builder serves both tools, which follow
  one contract (ADR-0061 decision 1); the tool is its first parameter. The
  source of seeds and the predicate "covered" are parameters without a
  default, as in :func:`hilclaw.check_tool.tool_function`.
* One module, not two in the manner of :mod:`hilclaw.check_tool` and
  :mod:`hilclaw.check_ending`: :func:`hilclaw.run_operation.ask` already
  writes the log and tells the forms apart, and
  :func:`hilclaw.run_failure.ended_with` maps a raised tool failure, so what
  is left between the operation and the end line is short.
* The builder refuses a tool that is not exactly ``"sim.run"`` or
  ``"board.run"`` as :func:`hilclaw.run_identity.step_of` does, before
  anything else, and a ``seeds`` or a ``covers`` that is not callable last.
* What the place before the start line hands to the step is an object of a
  private class with five slots, alive for that call only. Its ``repr``
  shows none of them.
* The output path is the :class:`pathlib.Path` that
  :func:`hilclaw.layout.attempt_artefact` returns for the data root of the
  call, the members ``run_id``, ``round``, ``candidate`` and ``attempt`` of
  the request (of the named attempt, for a version-3 spec) and the name
  ``output``, as it is: not resolved and not made absolute. The path of the
  log file is the :class:`pathlib.Path` that
  :func:`hilclaw.layout.build_log_file` returns for the same data root and
  four members, the tool's ``step`` and the member ``execution``. Both are
  formed once for a call, after the start line, and handed on as they are.
  The keeper is a new :class:`hilclaw.build_log.LogKeeper`, one for each
  call that reaches the operation; a call answered before the start line
  makes none.
* The five members are read from the request without a check of this
  module: the frame has checked their presence, types and bounds before the
  start line, and those bounds are the ones the two paths accept.
* A tool failure out of :func:`hilclaw.run_operation.ask` is taken as the
  operation's: that module raises none of its own. An
  :class:`hilclaw.run_operation.OperationAnswerInvalid` and a
  :class:`hilclaw.build_log.BuildLogUnwritable` out of it are taken as the
  ones it raised. The step is ended by
  :class:`hilclaw.journaled_step.StepFailed`, raised after the handler has
  been left, so it holds nothing of what was raised but the kind and the
  message.
* :mod:`hilclaw.harness.timing` is imported with the module: it imports no
  NumPy, and a test pins that.
* The type of the timing parameters is chosen from the covering entry: a
  :class:`hilclaw.run_parameters.TimingParameters` for the fp32 ``gemm``
  entry, a :class:`hilclaw.run_parameters.Bf16TimingParameters` for any
  other, by the ``KIND`` and ``DTYPE`` of its contract. Which
  entries reach the operation is the ``covers`` handed in:
  :func:`hilclaw.contract_table.run_covers` admits an entry only once it is
  ``timed``.

What the module does not do: it registers nothing and defines no tool
definition; the input schema and the descriptions are those of
:mod:`hilclaw.run_definition`. It binds no default table, source of seeds or
predicate (left to a later task), has no ``cpu_standin`` operation, states
no spend axis and bounds no size of a log (ADR-0108 decision 6). It hands
the operation no setting, no ``bound`` and no objective (ADR-0061
decision 3); a candidate's flags reach the operation through
:mod:`hilclaw.build_record`. Of the kernel of the attempt it forms the
output path and hands it on; but for the reads of
:func:`hilclaw.build_record.evaluated` in a ``compile_settings`` run it
reads nothing there, and it composes no message that holds the path.
It writes the file of the compiler's log only through
:func:`hilclaw.run_operation.ask`, by :func:`hilclaw.build_log.write`, whose
message shows no path, no text of an error and no byte of the log. It
composes the message of no tool failure and names no kind but
:data:`KIND_BUILD_LOG_UNWRITABLE`. It composes no message that holds a seed
(ADR-0064 decision 5) and puts the seed in no result (ADR-0061 decision 7).
The end line holds the message of a backend kind an operation raised as it
was raised (ADR-0068 decision 4); by ADR-0068 decision 6 it shows no path
and nothing of the seed, and nothing detects one that does. It keeps
nothing between calls.
"""

from hilclaw import (
    build_log,
    build_record,
    contract_table,
    hw_tool,
    instance,
    journaled_step,
    layout,
    run_admission,
    run_definition,
    run_failure,
    run_identity,
    run_operation,
    run_parameters,
    run_result,
    run_seed,
    targets,
    tools,
)
from hilclaw.harness import measurement, timing

#: The kind of ADR-0108 decision 7: the run tools' own, not reserved, spelt as ``correctness.check``'s.
KIND_BUILD_LOG_UNWRITABLE = "build_log_unwritable"

_OUTCOMES = {
    measurement.State.CONVERGED: run_result.CONVERGED,
    measurement.State.NOT_CONVERGED: run_result.NOT_CONVERGED,
}
_MOCK_UNIT = "ns"
_FP32_GEMM = ("gemm", "fp32")
_C_KERNEL = "c_kernel"
_CONDITIONS = {
    timing.Broken.REPORT_FORM: "report_form",
    timing.Broken.ZERO_INTERVAL: "zero_interval",
    timing.Broken.REPLAY: "replay",
}


class _Drawn:
    __slots__ = ("admitted", "kind", "seed", "unit", "units_per_ns")

    def __init__(self, admitted, seed, unit, units_per_ns, kind):
        self.admitted = admitted
        self.seed = seed
        self.unit = unit
        self.units_per_ns = units_per_ns
        self.kind = kind


def tool_function(tool, *, source, table, seeds, covers):
    """Return the tool function of ``tool``, ``sim.run`` or ``board.run``, that these five state.

    - ``tool``: ``"sim.run"`` or ``"board.run"``.
    - ``source``: the data-root source, as
      :func:`hilclaw.hw_tool.stepped_tool_function` takes it.
    - ``table``: the :class:`hilclaw.backends.BackendTable` the tool is bound
      to.
    - ``seeds``: the source of seeds, a callable without arguments
      (:mod:`hilclaw.harness.seed_source`).
    - ``covers``: the predicate of ADR-0041 decision 5, handed to
      :func:`hilclaw.run_admission.admit` as it is (ADR-0067 decision 3).

    No parameter has a default. Raises, in this order: what
    :func:`hilclaw.run_identity.step_of` raises for ``tool``
    (:class:`TypeError` when it is not exactly a ``str``,
    :class:`ValueError` for another ``str``); :class:`TypeError` when
    ``table`` is no ``BackendTable`` and when ``source`` is not callable;
    :class:`TypeError` when ``seeds`` and then when ``covers`` is not
    callable. Building calls none of the three, reads no file and asks the
    table nothing.

    The function returned takes one request and returns the result of the
    call, a ``dict`` (ADR-0183 decision 4). The module docstring has the
    order of a call. It raises :class:`hilclaw.tools.ToolFailure` as the function of
    :func:`hilclaw.hw_tool.stepped_tool_function` does, ``invalid_request``
    for a member no record names included; of one of
    :data:`hilclaw.run_admission.KINDS` and then of
    :data:`hilclaw.run_seed.KIND_SEED_NOT_DRAWN`, each with no line appended
    and no operation called, so that the same request can be repeated; and
    of the kind of the ``failure`` an end line holds, for a call that made no
    result. For none of the answers before the draw is ``seeds`` called.

    Everything else passes through unchanged, whatever it is: what
    ``covers`` raises and what ``seeds`` raises that is no
    :class:`Exception`, with no line appended; and what the step raises
    after the start line that is not answered above, which leaves the
    identity open (:mod:`hilclaw.journaled_step`); a request to end the
    operation raises is among them, and no log is written for it.

    The function does not modify the request or the table and keeps nothing
    between calls.
    """
    step = run_identity.step_of(tool)

    def admit(request, read):
        run, kind = read
        target = _target_of(run.hw_profile["accelerator"])
        admitted = run_admission.admit(run, covers=_at_target(covers, target))
        if target is None:
            unit, factor = _MOCK_UNIT, 1
        else:
            unit, factor = target.unit, target.units_per_ns
        return _Drawn(admitted, run_seed.draw(seeds), unit, factor, kind)

    def perform(data_root, request, hw_profile, operation, drawn):
        return _perform(step, data_root, request, hw_profile, operation, drawn)

    function = hw_tool.stepped_tool_function(
        tool=tool,
        steps=(step,),
        step_of=lambda request: step,
        numbers=run_identity.NUMBERS,
        source=source,
        table=table,
        read=_read,
        hw_profile_in=_hw_profile,
        check=run_definition.check,
        admit=admit,
        perform=perform,
    )
    for name, value in (("seeds", seeds), ("covers", covers)):
        if not callable(value):
            raise TypeError(f"{name}: must be callable")
    return function


def _target_of(accelerator):
    try:
        return targets.target(accelerator)
    except targets.NoTargetError:
        return None


def _at_target(covers, target):
    if target is None:
        return covers

    def covered_at_target(record):
        covered = covers(record)
        if covered is not True:
            return covered
        return contract_table.served_at(record, target)

    return covered_at_target


def _read(data_root, run_id):
    try:
        return instance.read(data_root, run_id), _C_KERNEL
    except instance.UnsupportedVersionError:
        kinded = instance.read_kinded(data_root, run_id)
        return kinded.instance, kinded.candidate_kind


def _hw_profile(read):
    return read[0].hw_profile


def _perform(step, data_root, request, hw_profile, operation, drawn):
    attempt = (
        data_root,
        request["run_id"],
        request["round"],
        request["candidate"],
        request["attempt"],
    )
    log_path = layout.build_log_file(*attempt, step, request["execution"])
    admitted = drawn.admitted
    parameters = _parameters(admitted, drawn.seed)
    try:
        evaluated = _evaluated(drawn.kind, attempt)
    except build_record.KernelRefused as refused:
        raise journaled_step.StepFailed({}, refused.kind, refused.message) from None
    with build_record.building(evaluated.build):
        try:
            answer = run_operation.ask(
                operation,
                request,
                hw_profile,
                parameters,
                evaluated.output_path,
                build_log.LogKeeper(),
                log_path=log_path,
            )
        except tools.ToolFailure as raised:
            kind, message = run_failure.ended_with(raised)
        except run_operation.OperationAnswerInvalid as invalid:
            kind, message = invalid.kind, invalid.message
        except build_log.BuildLogUnwritable as unwritable:
            kind, message = KIND_BUILD_LOG_UNWRITABLE, unwritable.message
        else:
            kind = None
    if evaluated.build is not None:
        evaluated.build.write()
    if kind is None:
        return {}, _result(answer, admitted, drawn.unit, drawn.units_per_ns)
    raise journaled_step.StepFailed({}, kind, message)


def _evaluated(kind, attempt):
    if kind == _C_KERNEL:
        return build_record.Evaluated(layout.attempt_artefact(*attempt, "output"), None)
    return build_record.evaluated(*attempt)


def _parameters(admitted, seed):
    contract = admitted.entry.contract
    common = (admitted.n_max, admitted.sample_form, seed)
    if (contract.KIND, contract.DTYPE) == _FP32_GEMM:
        return run_parameters.TimingParameters(*admitted.dims, *common)
    return run_parameters.Bf16TimingParameters(
        contract.KIND, contract.DTYPE, admitted.dims, *common
    )


def _result(answer, admitted, unit, units_per_ns):
    contract = (admitted.entry, admitted.dims)
    common = {
        "n_max": admitted.n_max,
        "sample_form": admitted.sample_form,
        "bound": admitted.bound,
    }
    if type(answer) is str:
        return run_result.broken(answer, *contract, **common)
    judgement = timing.judge_report(
        answer.report, sample_form=admitted.sample_form, n_max=admitted.n_max
    )
    if judgement.broken is not None:
        return run_result.broken(_CONDITIONS[judgement.broken], *contract, **common)
    return run_result.completed(
        _OUTCOMES[judgement.state],
        *contract,
        unit=unit,
        resolution=judgement.resolution_ns * units_per_ns,
        intervals=[interval * units_per_ns for interval in judgement.intervals_ns],
        memory_bytes=answer.memory_bytes,
        **common,
    )
