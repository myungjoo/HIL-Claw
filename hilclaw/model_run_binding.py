"""The model executor's binding, derived from the incumbents of runs the caller names (ADR-0189).

``ARCHITECTURE/decisions/ADR-0189-od31-binding-from-run-incumbents.md`` is the
rule; a decision cited by its number alone is one of that record.
:func:`binding_from_runs` takes, for each call site, the run whose incumbent
it binds (decision 3). For each distinct run it does this, in order, and the
first refusal ends the call:

1. Reads the run's ``instance.json`` with :func:`hilclaw.instance.read` and
   refuses a run outside the scope of decision 1 or the objective of decision 4.
2. Reads the incumbent with :func:`hilclaw.spec_feedback.incumbent`, the rule
   of ADR-0184 decision 2 over all rounds of the run (decision 2).
3. Refuses a run whose journal holds a timing step of an attempt whose
   ``spec.json`` is gone: the incumbent read does not see that attempt, so the
   choice might otherwise fall silently on another one (decision 2).
4. Reads the kernel with :func:`hilclaw.attempt_kernel.kernel_reference`, with
   the build settings the caller gives (decision 6).

The entry of a call site is one :class:`hilclaw.model_binding.BindingEntry`
for :data:`EVERY` shape (decision 5). One run named at several call sites is
read once and gives them one reference. Whether a kernel fits its call site is
not looked at here: :mod:`hilclaw.model_binding` does that when the executor
runs (ADR-0153 decision 3).

Outcomes:

* A malformed argument raises :class:`TypeError` or :class:`ValueError` with
  the attribute ``parameter``, the name of the argument, before anything is
  read. ``data_root`` and ``flags`` are checked as by
  :func:`hilclaw.attempt_kernel.kernel_reference`. ``runs`` must be a mapping
  from names of :data:`hilclaw.model_forward_run.CALL_SITES` to names that
  :func:`hilclaw.layout.check_run_id` accepts; a bad run id is its
  :class:`hilclaw.layout.InvalidPathValueError`, a :class:`ValueError`.
* Every other outcome but the answer raises :class:`RunBindingError`, whose
  ``reason`` is one of :data:`REASONS`; the original error, where one exists,
  is its ``__cause__``. Besides the names of this module, a ``reason`` is the
  kind of the :class:`hilclaw.tools.ToolFailure` of the incumbent read
  (:data:`READ_FAILURES`) or the ``reason`` of the
  :class:`hilclaw.attempt_kernel.AttemptKernelError`.

What this module does not do: it writes nothing, starts no build, container or
process, reads and writes no ``best.json`` and no ``best_ref``, is no tool, and
never falls back on another attempt or run. It does not look at whether a run
has ended: the answer is the incumbent of what the journal holds at the call
(decision 7).
"""

import os
from collections.abc import Mapping

from hilclaw import (
    attempt_kernel,
    checks_tool,
    instance,
    journal,
    layout,
    model_forward_run,
    run_identity,
    spec_feedback,
    tools,
)
from hilclaw.attempt_kernel import _check_data_root, _check_flags, _parameter
from hilclaw.model_binding import BindingEntry

TARGET = "cpu_standin"
"""The one ``accelerator`` of a run this module takes (decision 1)."""

EVERY = "every"
"""The ``shapes`` of every entry: each kind's contract obliges correctness at every shape (decision 5)."""

RUN_MISSING = "run_missing"
INSTANCE_UNREADABLE = "instance_unreadable"
INSTANCE_INVALID = "instance_invalid"
INSTANCE_OTHER_VERSION = "instance_other_version"
OTHER_TARGET = "other_target"
NOT_ONE_CANDIDATE = "not_one_candidate"
NO_OP_SIGNATURE = "no_op_signature"
NO_OBJECTIVE = "no_objective"
OBJECTIVE_UNSUPPORTED = "objective_unsupported"
ATTEMPT_WITHOUT_SPEC = "attempt_without_spec"
NO_INCUMBENT = "no_incumbent"
READ_FAILURES = (
    spec_feedback.KIND_FEEDBACK_UNREADABLE,
    tools.KIND_RUN_FILE_MISSING,
    tools.KIND_RUN_FILE_UNREADABLE,
    tools.KIND_RUN_FILE_INVALID,
    tools.KIND_RUN_FILE_UNSUPPORTED,
    checks_tool.KIND_CHECK_RESULT_INVALID,
)
"""Each kind of :class:`hilclaw.tools.ToolFailure` the incumbent read raises."""

REASONS = (
    RUN_MISSING,
    INSTANCE_UNREADABLE,
    INSTANCE_INVALID,
    INSTANCE_OTHER_VERSION,
    OTHER_TARGET,
    NOT_ONE_CANDIDATE,
    NO_OP_SIGNATURE,
    NO_OBJECTIVE,
    OBJECTIVE_UNSUPPORTED,
    *READ_FAILURES,
    ATTEMPT_WITHOUT_SPEC,
    NO_INCUMBENT,
    *attempt_kernel.REASONS,
)
"""Every ``reason`` of :class:`RunBindingError`, in the order of the checks."""

_LATENCY_ONLY = {"objectives": [{"type": "latency_minimisation"}], "constraints": []}
_STEP_KINDS = (journal.STEP_STARTED, journal.STEP_ENDED)


class RunBindingError(Exception):
    """A named run gives no binding entry; ``reason`` is one of :data:`REASONS`, with ``call_site`` and ``run_id``."""

    def __init__(self, reason, call_site, run_id):
        super().__init__(f"{call_site}: run {run_id}: {reason}")
        self.reason = reason
        self.call_site = call_site
        self.run_id = run_id


def binding_from_runs(data_root, runs, *, flags):
    """Return the binding whose entry for each call site is the incumbent of the run named for it.

    @param data_root the data root, a ``str`` or an :class:`os.PathLike` of ``str``.
    @param runs a mapping from call site to run id; the first refusal in its
        order is the one raised.
    @param flags the build settings the kernels were built with, a ``tuple`` or
        ``list`` of ``str``, for example
        :data:`hilclaw.standin_settings.FLAGS`; required.
    @return a new ``dict`` from call site to a ``tuple`` of one
        :class:`hilclaw.model_binding.BindingEntry`, the form
        :func:`hilclaw.model_binding.check` and its siblings take.
    @throws TypeError, ValueError for a malformed argument, as the module
        docstring lists.
    @throws RunBindingError for a run that gives no entry.
    """
    with _parameter("data_root"):
        _check_data_root(data_root)
    with _parameter("runs"):
        _check_runs(runs)
    with _parameter("flags"):
        _check_flags(flags)
    kernels = {}
    binding = {}
    for call_site, run_id in runs.items():
        if run_id not in kernels:
            kernels[run_id] = _incumbent_kernel(data_root, call_site, run_id, flags)
        binding[call_site] = (BindingEntry(kernels[run_id], EVERY),)
    return binding


def _check_runs(runs):
    if not isinstance(runs, Mapping):
        raise TypeError(f"must be a mapping, got {type(runs).__name__}")
    for call_site, run_id in runs.items():
        if call_site not in model_forward_run.CALL_SITES:
            raise ValueError(f"key {call_site!r} is no call site")
        layout.check_run_id(run_id)


def _incumbent_kernel(data_root, call_site, run_id, flags):
    def refused(reason):
        return RunBindingError(reason, call_site, run_id)

    reason = _out_of_scope(_stated(data_root, run_id, refused))
    if reason is not None:
        raise refused(reason)
    try:
        found = spec_feedback.incumbent(data_root, run_id)
        if _timed_attempt_without_spec(data_root, run_id):
            raise refused(ATTEMPT_WITHOUT_SPEC)
    except tools.ToolFailure as error:
        raise refused(error.kind) from error
    if found is None:
        raise refused(NO_INCUMBENT)
    try:
        return attempt_kernel.kernel_reference(
            data_root, run_id, found["round"], 1, found["attempt"], flags=flags
        )
    except attempt_kernel.AttemptKernelError as error:
        raise refused(error.reason) from error


def _stated(data_root, run_id, refused):
    try:
        return instance.read(data_root, run_id)
    except (
        instance.MissingInstanceError,
        FileNotFoundError,
        NotADirectoryError,
    ) as error:
        raise refused(RUN_MISSING) from error
    except instance.InvalidInstanceError as error:
        raise refused(INSTANCE_INVALID) from error
    except instance.UnsupportedVersionError as error:
        raise refused(INSTANCE_OTHER_VERSION) from error
    except OSError as error:
        raise refused(INSTANCE_UNREADABLE) from error


def _out_of_scope(stated):
    if stated.hw_profile["accelerator"] != TARGET:
        return OTHER_TARGET
    if stated.candidates_per_round != 1:
        return NOT_ONE_CANDIDATE
    if stated.op_signature is None:
        return NO_OP_SIGNATURE
    if stated.objective is None:
        return NO_OBJECTIVE
    if stated.objective != _LATENCY_ONLY:
        return OBJECTIVE_UNSUPPORTED
    return None


def _timed_attempt_without_spec(data_root, run_id):
    for event in checks_tool.log_lines(data_root, run_id):
        if event["kind"] not in _STEP_KINDS:
            continue
        try:
            identity = journal.identity_of(event)
        except journal.JournalError as error:
            message = f"{run_id}: a step line of the journal is refused"
            raise tools.ToolFailure(tools.KIND_RUN_FILE_INVALID, message) from error
        if (
            identity.step == run_identity.STEP_BOARD_RUN
            and identity.candidate == 1
            and identity.attempt is not None
            and not os.path.lexists(
                layout.attempt_artefact(
                    data_root, run_id, identity.round, 1, identity.attempt, "spec.json"
                )
            )
        ):
            return True
    return False
