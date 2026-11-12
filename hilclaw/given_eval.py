"""The command that evaluates given code out of the loop (ADR-0200 decisions 4 (b) and 5, slice 4).

Command line: ``python -m hilclaw.given_eval <request> <c-file>``. ``<request>``
is the path of a file whose content is an instance start request of the form
of :mod:`hilclaw.new_run` (ADR-0155), decoded under its rules; ``<c-file>`` is
the path of the one C source file of the given code (ADR-0200 decision 2).
Exactly these two arguments are accepted, and nothing is read from standard
input. A person runs it; it is no FR-10 tool, has no registry entry and no
MCP name, and starts no ``claude`` (ADR-0200 decision 5; ADR-0192 decision 1).
The choices ADR-0200 leaves to this command are recorded in
``ARCHITECTURE/decisions/ADR-0202-od33-given-attempt-in-feedback.md``
decision 2.

**One evaluation**, in the order of ADR-0200 decision 5, stopping at the
first failure:

1. Standard output must exist; exactly two arguments.
2. The request: the file is read and decoded as by :mod:`hilclaw.new_run`. A
   request whose ``hw_profile.record.accelerator`` is a ``str`` other than a
   name of :func:`hilclaw.targets.instance_start_accelerators` is
   ``target_refused``; one whose ``round_budget`` is anything but exactly the
   ``int`` 1 is ``round_budget_refused``. A request that states no
   ``round_budget`` is started with ``round_budget`` 1, the last member; it
   is the only change made to the request (ADR-0200 decision 4 (b): the run's
   budget is 1, so round 0 alone).
3. The data root, once, from the source (by default
   :func:`hilclaw.data_root_source.configured`).
4. The start: :func:`hilclaw.start_instance.start` with the request and the C
   file as ``code_file``. It reads the file once and writes the blob,
   ``instance.json`` of version 3 and the ``artifacts.json`` record of the
   given code (ADR-0200 decisions 5 and 6, T-0561); its refusals are told as
   :mod:`hilclaw.new_run` tells them.
5. The entry of round 0 as the Round-Manager's entry steps 1 and 2 make it
   for a fresh run (``orchestration/round-manager.md``; ADR-0120, ADR-0201
   decision 1): ``run.fresh`` must answer ``true`` (``not_fresh``
   otherwise), then ``state.write`` writes the first ``STATE.json``. The
   entry's ``run.commit`` and ``state.read`` are not made: the run was made
   by step 4 of this call, so nothing is owed and no ``STATE.json`` exists.
6. ``key.store``; a failure is told and the steps go on, as round step 1
   says (ADR-0134 decisions 5 and 6).
7. The placement of ``(0, 1, 1)`` by :func:`hilclaw.given_attempt.place`
   (ADR-0201 decision 2).
8. ``correctness.check`` at ``sim``, then at ``board``, each followed by
   ``checks.read`` for the standing, then ``board.run``, each with
   ``execution`` 1, as the evaluator and the experiment-runner make them in
   round 0 (ADR-0142 decisions 3 and 4; ADR-0131 decision 6).
9. ``round.end`` of round 0, which ends the run (``run_status`` ``"over"``).
10. ``run.commit``.

Every tool of steps 5, 6 and 8 to 10 is called through
:func:`hilclaw.tools.call` on :func:`hilclaw.tools.default_registry` bound to
the data root of step 3, so each step is journaled exactly as a live round
0's is. As in round 0 (ADR-0185 decision 2; ADR-0200 decision 4 (a)): a
placement that fails with a kind other than ``output_exists``, and a check
that does not give the standing ``"verified"``, skip the later steps of 8 and
go to ``round.end``; a ``board.run`` of any answer goes to ``round.end``.
``output_exists`` is a stop, as in round 0 (ADR-0201 decision 2).

**What the person is told**, through the process only. When ``run.commit``
of step 10 has answered, standard output gets exactly one line, a compact
JSON object in ASCII ended by one LF: ``outcome``, ``run_id``, ``place``,
``sim``, ``board`` and ``timing``. ``place`` is ``{"given_code": hash}`` or
``{"failure": kind}``; ``sim`` and ``board`` are ``{"outcome", "standing"}``
of the check and of ``checks.read``, either replaced by ``failure`` and
``standing_failure`` for a failure kind; ``timing`` is ``{"outcome"}`` of
``board.run`` with ``median`` (the median of its ``intervals``) and ``unit``
when it has them, or ``condition`` when it is broken, or ``{"failure":
kind}``. A step not reached is left out. ``outcome`` is ``measured`` when
the given attempt was verified at both points and ``board.run`` gave the
``outcome`` ``converged`` or ``not_converged``, and ``not_measured``
otherwise.

Every refusal and failure goes to standard error as one compact JSON line
with ``outcome``, the kind of this command, ``run_id`` once a run exists,
and the members the kind has (``reason``, ``missing``, ``step``, ``kind``,
``message``, ``fault``). A failure inside step 6, 7 or 8 that round 0
survives is told on standard error when it happens; the summary follows when
step 10 answered, and the status is that of the first such failure. No
traceback reaches the person, and :class:`KeyboardInterrupt` and
:class:`SystemExit` are not caught.

=========================  ======  ============================================
``outcome``                status  when
=========================  ======  ============================================
``measured``               0       summary, as above
``not_measured``           10      summary, as above
``given_run_id``           11      the request gives a ``run_id``
``missing_members``        12      the start's required members are missing
``invalid``                13      the request is invalid or of another version
``out_of_scope``           14      outside ADR-0076 decision 1
``run_id_in_use``          15      the built id was taken (``run_id``)
``file_system``            16      the start failed in the file system
``unwritable_value``       17      a value that JSON text cannot hold
``given_code_refused``     18      ``compile_settings``, or N other than 1
``bad_given_code``         19      the C file cannot be read or is too large
``bad_usage``              20      not exactly two arguments
``unreadable_input``       21      the request cannot be read
``bad_input``              22      the request is no JSON object
``no_data_root``           23      the data root cannot be obtained
``fault``                  24      an unexpected exception, or no standard output
``target_refused``         25      a target outside ``instance_start``
``round_budget_refused``   26      a ``round_budget`` other than 1
``given_code_unrecorded``  27      the record was not written (``run_id``)
``not_fresh``              30      ``run.fresh`` answered ``false``
``state_write_failed``     31      ``run.fresh`` or ``state.write`` failed
``key_store_failed``       32      ``key.store`` failed
``place_failed``           33      the placement failed
``check_failed``           34      ``correctness.check`` or ``checks.read`` failed
``board_run_failed``       35      ``board.run`` failed
``round_end_failed``       36      ``round.end`` failed
``run_commit_failed``      37      ``run.commit`` failed
=========================  ======  ============================================

Only ``measured`` has 0 and no status is 1 or 2. ``reason`` and ``message``
are free text and are never parsed.

**The record** (ADR-0200 decision 4 (b)): the outcome is the run's own files
(``instance.json``, ``artifacts.json``, ``STATE.json``, ``events.ndjson``,
the attempt's ``output/`` and the tools' results) committed by
``run.commit``; this command writes no file, member, ``step`` value or kind
of the data plane of its own. A run stopped by a failure after step 4 stays
as the failure left it and is not committed by this command.
"""

import contextlib
import statistics
import sys

from hilclaw import data_root_source, given_attempt, targets, tools
from hilclaw.new_run import _described, _parsed, _standard, _started, _told

MEASURED = "measured"
NOT_MEASURED = "not_measured"

EXIT_STATUS = {
    MEASURED: 0,
    NOT_MEASURED: 10,
    "given_run_id": 11,
    "missing_members": 12,
    "invalid": 13,
    "out_of_scope": 14,
    "run_id_in_use": 15,
    "file_system": 16,
    "unwritable_value": 17,
    "given_code_refused": 18,
    "bad_given_code": 19,
    "bad_usage": 20,
    "unreadable_input": 21,
    "bad_input": 22,
    "no_data_root": 23,
    "fault": 24,
    "target_refused": 25,
    "round_budget_refused": 26,
    "given_code_unrecorded": 27,
    "not_fresh": 30,
    "state_write_failed": 31,
    "key_store_failed": 32,
    "place_failed": 33,
    "check_failed": 34,
    "board_run_failed": 35,
    "round_end_failed": 36,
    "run_commit_failed": 37,
}

FIRST_STATE = {
    "schema_version": 1,
    "round": 0,
    "budget_spent": {"totals": {}, "position": 0, "open_steps": []},
}

_ATTEMPT = {"round": 0, "candidate": 1, "attempt": 1}
_ENTERING = ("converged", "not_converged")
_VERIFIED = "verified"
_SURVIVED = ("key_store_failed", "check_failed", "board_run_failed")


class _Stop(Exception):
    def __init__(self, told):
        super().__init__(told["outcome"])
        self.told = told


class _Evaluation:
    def __init__(self, root, run_id, say):
        self.root = root
        self.run_id = run_id
        self.say = say
        self.registry = tools.default_registry(lambda: root)
        self.summary = {"outcome": NOT_MEASURED, "run_id": run_id}
        self.failed = None

    def call(self, name, request, outcome):
        try:
            return tools.call(self.registry, name, {"run_id": self.run_id, **request})
        except tools.ToolFailure as failure:
            told = self.failure(outcome, name, failure)
            if outcome in _SURVIVED:
                self.survived(told)
                return failure
            raise _Stop(told) from failure

    def failure(self, outcome, step, failure):
        return {
            "outcome": outcome,
            "run_id": self.run_id,
            "step": step,
            "kind": failure.kind,
            "message": failure.message,
        }

    def survived(self, told):
        self.say(told)
        if self.failed is None:
            self.failed = told["outcome"]

    def run(self):
        fresh = self.call("run.fresh", {}, "state_write_failed")
        if fresh.get("fresh") is not True:
            raise _Stop({"outcome": "not_fresh", "run_id": self.run_id})
        self.call("state.write", {"state": FIRST_STATE}, "state_write_failed")
        self.call("key.store", {}, "key_store_failed")
        if self.placed() and self.checked("sim") and self.checked("board"):
            self.timed()
        self.call("round.end", {"round": 0}, "round_end_failed")
        self.call("run.commit", {}, "run_commit_failed")
        return self.summary

    def placed(self):
        try:
            digest = given_attempt.place(self.root, self.run_id)
        except tools.ToolFailure as failure:
            told = self.failure("place_failed", given_attempt.NAME, failure)
            if failure.kind == given_attempt.KIND_OUTPUT_EXISTS:
                raise _Stop(told) from failure
            self.survived(told)
            self.summary["place"] = {"failure": failure.kind}
            return False
        self.summary["place"] = {"given_code": digest}
        return True

    def checked(self, point):
        asked = {**_ATTEMPT, "point": point}
        made = {}
        answer = self.call(
            "correctness.check", {**asked, "execution": 1}, "check_failed"
        )
        if isinstance(answer, tools.ToolFailure):
            made["failure"] = answer.kind
        else:
            made["outcome"] = answer.get("outcome")
        read = self.call("checks.read", asked, "check_failed")
        if isinstance(read, tools.ToolFailure):
            made["standing_failure"] = read.kind
        else:
            made["standing"] = _standing(read)
        self.summary[point] = made
        return made.get("standing") == _VERIFIED

    def timed(self):
        answer = self.call(
            "board.run", {**_ATTEMPT, "execution": 1}, "board_run_failed"
        )
        if isinstance(answer, tools.ToolFailure):
            self.summary["timing"] = {"failure": answer.kind}
            return
        timing = {"outcome": answer.get("outcome")}
        if "condition" in answer:
            timing["condition"] = answer["condition"]
        intervals = answer.get("intervals")
        if intervals and "unit" in answer:
            timing["median"] = statistics.median(intervals)
            timing["unit"] = answer["unit"]
        self.summary["timing"] = timing
        if timing["outcome"] in _ENTERING:
            self.summary["outcome"] = MEASURED


def _standing(read):
    entries = read.get("attempts", [])
    return entries[0].get("standing") if entries else None


def _accelerator(document):
    hw_profile = document.get("hw_profile")
    record = hw_profile.get("record") if type(hw_profile) is dict else None
    return record.get("accelerator") if type(record) is dict else None


def _request_refusal(document):
    accelerator = _accelerator(document)
    accepted = targets.instance_start_accelerators()
    if type(accelerator) is str and accelerator not in accepted:
        return _told(
            "target_refused",
            f"hw_profile.record.accelerator: given code is evaluated at "
            f"{', '.join(accepted)} only (ADR-0200 decision 5)",
        )
    if "round_budget" in document and not (
        type(document["round_budget"]) is int and document["round_budget"] == 1
    ):
        return _told(
            "round_budget_refused",
            "round_budget: an evaluation of given code is a run of round 0 "
            "alone, so it states 1 or nothing (ADR-0200 decision 4 (b))",
        )
    return None


def _start(args, source):
    if len(args) != 2:
        return (
            None,
            None,
            _told(
                "bad_usage",
                f"usage: expected a request file and a C file, got {len(args)} arguments",
            ),
        )
    document, refused = _parsed(args[0])
    if refused is None:
        refused = _request_refusal(document)
    if refused is not None:
        return None, None, refused
    if "round_budget" not in document:
        document = {**document, "round_budget": 1}
    try:
        root = data_root_source.obtain(source)
    except tools.ToolFailure as e:
        return None, None, _told("no_data_root", e.message)
    told = _started(document, root, args[1])
    if told["outcome"] != "started":
        return root, told.get("run_id"), told
    return root, told["run_id"], None


def _evaluate(args, source, say):
    run_id = None
    try:
        root, run_id, refused = _start(args, source)
        if refused is not None:
            return None, refused
        evaluation = _Evaluation(root, run_id, say)
        summary = evaluation.run()
    except _Stop as stop:
        return None, stop.told
    except Exception as e:  # noqa: BLE001
        told = {"outcome": "fault", "fault": type(e).__name__}
        if run_id is not None:
            told["run_id"] = run_id
        return None, told
    return summary, evaluation.failed


def _writer(stderr):
    def say(told):
        with contextlib.suppress(Exception):
            if stderr is not None:
                stderr.write(tools.encode(told))
                stderr.flush()

    return say


def main(argv=None, *, source=data_root_source.configured, stdout=None, stderr=None):
    """Evaluate the given code of the two arguments; return the exit status.

    ``argv`` defaults to ``sys.argv[1:]``. ``source`` is the data-root source
    (:mod:`hilclaw.data_root_source`), asked once, after the request was read
    and checked. ``stdout`` and ``stderr`` are binary streams and default to
    the standard ones; a standard stream that the process does not have, or
    that has no binary layer, is missing. Returns the status of the module
    docstring's table; no :class:`Exception` leaves the call.
    """
    args = sys.argv[1:] if argv is None else list(argv)
    stdout = _standard("stdout") if stdout is None else stdout
    stderr = _standard("stderr") if stderr is None else stderr
    say = _writer(stderr)
    if stdout is None:
        say({"outcome": "fault", "reason": "there is no standard output"})
        return EXIT_STATUS["fault"]
    summary, failed = _evaluate(args, source, say)
    if summary is None:
        say(failed)
        return EXIT_STATUS[failed["outcome"]]
    try:
        line = tools.encode(summary)
        if stdout.write(line) != len(line):
            raise OSError("it took a part of the line")
        stdout.flush()
    except Exception as e:  # noqa: BLE001
        say(
            {
                "outcome": "fault",
                "run_id": summary["run_id"],
                "reason": f"cannot write standard output: {_described(e)}",
            }
        )
        return EXIT_STATUS["fault"]
    return EXIT_STATUS[failed or summary["outcome"]]


if __name__ == "__main__":
    raise SystemExit(main())
