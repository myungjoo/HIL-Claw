"""The ``feedback.attempts`` of the spec of a first-case round >= 1 coder call (ADR-0151 decision 2 (d)).

``ARCHITECTURE/decisions/ADR-0151-od6-first-case-later-round-spec.md`` is the
rule; a decision or check cited by its number alone is one of that record.
:func:`attempts` returns the list of entries that decision 2 (d) shows in the
spec of ``(round, candidate 1, attempt 1)`` of a run, by checks ⑧ to ⑩ of
decision 3:

* ⑧ every attempt of candidate 1 of each round 0 to ``round`` - 1 whose
  ``spec.json`` exists is found by listing ``runs/<run_id>/rounds/`` and each
  round's ``coder/candidates/01/attempts/``. A directory that is not there
  gives no attempt and is no failure. Each spec found must be accepted by
  :func:`hilclaw.spec_file.parse` and its ``id`` must format, by
  :func:`hilclaw.spec_file.final_name`, to its own path
  (:data:`KIND_FEEDBACK_UNREADABLE` otherwise). The attempts are looked at in
  ascending ``(round, attempt)``, and the first failure decides.
* ⑨ only when ⑧ found one, the run's log is read by
  :func:`hilclaw.checks_tool.log_lines` and its step lines passed by
  :func:`hilclaw.checks_tool.checks_in_order` for the found attempts at the
  two points, with the kinds of ADR-0131 decision 3; each attempt's standing
  at each point is :func:`hilclaw.check_standing.point_standing`. The lines of
  a point are those of its one ``step`` value in
  :data:`hilclaw.check_standing.STEPS_OF`, ``correctness_check_sim_v2`` or
  ``correctness_check_board_v2``, the value of every contract
  (``ARCHITECTURE/decisions/ADR-0183-od18-tool-result-format-v2.md``
  decision 8, in place of the two values per point of ADR-0178 decision 1);
  a line under a value ADR-0183 retired is neither read nor refused.
* An attempt undetermined at the sim point is not shown. Each other one gives
  ``{"round", "candidate": 1, "attempt", "techniques"}``, ``techniques`` being
  the ids of its own spec's ``guidance.techniques`` in their order, and
  ``failure`` exactly when it is not verified at the sim point, or verified
  there and not verified at the board point. The deciding result is the first
  ended check of that point, in line order, whose
  ``outcome`` is ``"fail"`` or ``"broken"``; ``stage`` is ``"compile"`` for a
  broken one with ``condition`` ``build_exit_status`` or
  ``build_time_limit``, else the point's name. No entry has ``profile``.
* ⑩ after all of ⑨, for each ``compile`` failure, the compiler log of the
  deciding check (ADR-0078 decision 3), named by the ``step`` of its line
  (ADR-0183 decision 7: ``build-log-correctness_check_sim_v2-<EE>.txt`` at
  the sim point), is
  appended to the report when that file exists and is not empty; a missing
  file is no failure.

``ARCHITECTURE/decisions/ADR-0184-od20-first-case-incumbent-base.md``
decision 2 adds ``feedback.base``, which :func:`feedback` returns beside the
entries: the incumbent, the shown attempt verified at both points whose
measurement at the step :data:`hilclaw.run_identity.STEP_BOARD_RUN` has the
lowest median of its intervals, the earliest ``(round, attempt)`` on a tie.
An attempt has a measurement by the rule of ``timings.compare``
(:mod:`hilclaw.timings_tool`): exactly one end line at that step whose
``result`` is an admitted timing result with the ``outcome`` ``"converged"``
or ``"not_converged"``, and no end line holding a ``failure`` and no start
line without an end line. A step line of that step that
:func:`hilclaw.journal.identity_of` refuses, or an end line whose ``result``
is not admitted, makes its attempt no incumbent and fails nothing. With no
incumbent there is no ``base``.

Choices that are this module's own and no rule of the record:

* Of a listing, only a name that is exactly what :mod:`hilclaw.layout` formats
  for a round below ``round``, or for an attempt number, is taken; every other
  name (``tmp``, ``1``, ``001``) is ignored. An attempt directory without an
  entry named ``spec.json`` is ignored. An entry named ``spec.json`` that is no
  regular file, a symbolic link among them, is :data:`KIND_FEEDBACK_UNREADABLE`.
* The report is one fixed English sentence naming the stage, the point, the
  ``outcome`` and, for a broken result, a fixed phrase for its ``condition``.
  A condition missing, of another type or outside
  :data:`hilclaw.check_result.CONDITIONS` gets one generic phrase and is not
  echoed. Nothing else of the result is read. A compiler log follows the
  sentence after a line feed and the line ``Compiler log:``.
* A compiler log is decoded strictly as UTF-8; one that starts with a byte
  order mark or holds bytes that are no UTF-8 is
  :data:`KIND_FEEDBACK_UNREADABLE`, as is any other failure of its read.
* Each message of :data:`KIND_FEEDBACK_UNREADABLE` starts with the path
  concerned relative to the data root; an :class:`OSError` is reported by its
  class and the text of the system, without the absolute path.

The files read are the listed directories, the found ``spec.json`` files,
``events.ndjson`` and the compiler logs; ``STATE.json``, ``instance.json``,
``decision/hypotheses.json`` and ``decision.md`` are not. Nothing is created,
written or kept between calls. ``spec.write`` (:mod:`hilclaw.spec_tool`)
calls :func:`feedback`.
:data:`KIND_FEEDBACK_UNREADABLE` is a name of the tool layer and not reserved.
"""

import codecs
import os
import stat
import statistics
from pathlib import Path

from hilclaw import (
    check_identity,
    check_result,
    check_standing,
    checks_tool,
    journal,
    keys,
    layout,
    run_files,
    run_identity,
    spec_file,
    timings_tool,
    tools,
)

#: An earlier attempt's spec, a listing or a compiler log of the feedback cannot be used.
KIND_FEEDBACK_UNREADABLE = "feedback_unreadable"

_COMPILE_CONDITIONS = ("build_exit_status", "build_time_limit")
_PHRASES = {
    "build_time_limit": "the build of the verification executable passed its time limit",
    "build_exit_status": "the compiler or the linker ended with a failure status",
    "time_limit": "the verification executable passed its time limit",
    "exit_status": "the verification executable ended with a failure status",
    "report_form": "the report of the verification executable was not of its form",
    "check_value": "the check value of the verification executable did not match",
}
_GENERIC_PHRASE = "a condition this report does not name"
_FAILED = (check_result.FAIL, check_result.BROKEN)
_ENTERING = ("converged", "not_converged")
_STEP_KINDS = (journal.STEP_STARTED, journal.STEP_ENDED)


def attempts(data_root, run_id, round):
    """Return the ``feedback.attempts`` of the spec of ``(round, 1, 1)`` of the run ``run_id``.

    The ``attempts`` member of :func:`feedback`, with its parameters and
    exceptions.
    """
    return feedback(data_root, run_id, round)["attempts"]


def feedback(data_root, run_id, round):
    """Return the ``feedback`` of the spec of ``(round, 1, 1)`` of the run ``run_id``.

    A new ``dict`` with ``attempts``, as below, and ``base``, the
    ``{"round", "candidate": 1, "attempt"}`` of the incumbent, exactly when
    there is one (ADR-0184 decision 2).

    @param data_root the data root, used as ``Path(data_root)``.
    @param run_id the run, a name :func:`hilclaw.layout.check_run_id` accepts.
    @param round the round of the spec, an ``int`` (no ``bool``) from 1 to
        :data:`hilclaw.keys.MAX_INTEGER`.
    @return the ``dict``, whose ``attempts`` is a new ``list`` of new
        ``dict`` entries in ascending ``(round, attempt)``, each ``{"round",
        "candidate": 1, "attempt", "techniques"}`` and, for a failed attempt,
        ``"failure": {"stage", "report"}``; possibly empty.
    @throws TypeError, ValueError for a ``round`` of another type or value.
    @throws hilclaw.layout.InvalidPathValueError for a bad ``run_id``.
    @throws hilclaw.tools.ToolFailure of kind :data:`KIND_FEEDBACK_UNREADABLE`
        for a listing that fails other than by not being there, a found
        ``spec.json`` that is no regular file, cannot be read, is refused by
        :func:`hilclaw.spec_file.parse` or whose ``id`` is not its attempt's,
        and a compiler log that is no regular file, cannot be read or is no
        UTF-8 without a byte order mark; of kind ``run_file_missing``,
        ``run_file_unreadable``, ``run_file_invalid`` or
        ``run_file_unsupported`` as :func:`hilclaw.checks_tool.log_lines`
        raises them; of kind ``run_file_invalid`` or ``check_result_invalid``
        as :func:`hilclaw.checks_tool.checks_in_order` raises them.
    """
    if type(round) is not int:
        raise TypeError(f"round: must be an int, got {type(round).__name__}")
    if not 1 <= round <= keys.MAX_INTEGER:
        raise ValueError(f"round: must be from 1 to {keys.MAX_INTEGER}, got {round}")
    layout.check_run_id(run_id)
    root = Path(data_root)
    found = _found(root, run_id, round)
    if not found:
        return {"attempts": []}
    lines = checks_tool.log_lines(root, run_id)
    numbers = {(q, a) for q, a, _ in found}

    def inside(key):
        step, q, candidate, a = key
        return step in check_identity.STEPS and candidate == 1 and (q, a) in numbers

    checks = checks_tool.checks_in_order(run_id, lines, inside)
    shown = []
    for q, a, techniques in found:
        entry = {"round": q, "candidate": 1, "attempt": a, "techniques": techniques}
        sim = check_standing.point_standing(lines, check_identity.SIM, q, 1, a)
        if sim is check_standing.Standing.UNDETERMINED:
            continue
        point = None
        if sim is check_standing.Standing.NOT_VERIFIED:
            point = check_identity.SIM
        else:
            board = check_standing.point_standing(lines, check_identity.BOARD, q, 1, a)
            if board is check_standing.Standing.NOT_VERIFIED:
                point = check_identity.BOARD
        deciding = None
        if point is not None:
            steps = check_standing.STEPS_OF[point]
            deciding = next(
                (key[0], element)
                for key, element in checks
                if key[0] in steps
                and key[1:] == (q, 1, a)
                and "result" in element
                and element["result"]["outcome"] in _FAILED
            )
        shown.append((entry, point, deciding))
    for entry, point, deciding in shown:
        if deciding is not None:
            entry["failure"] = _failure(root, run_id, entry, point, *deciding)
    made = {"attempts": [entry for entry, _, _ in shown]}
    timed = []
    for entry, point, _ in shown:
        if point is None:
            median = _board_median(lines, entry["round"], entry["attempt"])
            if median is not None:
                timed.append((median, entry["round"], entry["attempt"]))
    if timed:
        _, q, a = min(timed)
        made["base"] = {"round": q, "candidate": 1, "attempt": a}
    return made


def _board_median(lines, q, a):
    entering, started, ended = [], set(), set()
    for event in lines:
        if event["kind"] not in _STEP_KINDS:
            continue
        try:
            identity = journal.identity_of(event)
        except journal.JournalError:
            return None
        if identity.step != run_identity.STEP_BOARD_RUN or (
            identity.round,
            identity.candidate,
            identity.attempt,
        ) != (q, 1, a):
            continue
        if event["kind"] == journal.STEP_STARTED:
            started.add(identity.execution)
            continue
        ended.add(identity.execution)
        data = event["data"]
        if "failure" in data or timings_tool.timing_problem(data["result"]):
            return None
        if data["result"]["outcome"] in _ENTERING:
            entering.append(data["result"]["intervals"])
    if len(entering) != 1 or started - ended:
        return None
    return statistics.median(entering[0])


def _failure(root, run_id, entry, point, step, deciding):
    result = deciding["result"]
    outcome = result["outcome"]
    condition = result.get("condition")
    named = type(condition) is str and condition in _PHRASES
    compiled = outcome == check_result.BROKEN and condition in _COMPILE_CONDITIONS
    stage = "compile" if named and compiled else point
    sentence = (
        f"Stage {stage}: the correctness check at the {point} point ended with "
        f"the outcome {outcome}"
    )
    if outcome == check_result.BROKEN:
        sentence += f": {_PHRASES[condition] if named else _GENERIC_PHRASE}"
    report = sentence + "."
    if stage == "compile":
        directory = layout.attempt_dir(
            root, run_id, entry["round"], "measure", 1, entry["attempt"]
        )
        name = f"build-log-{step}-{deciding['execution']:02d}.txt"
        text = _compiler_log(root, directory / name)
        if text:
            report += f"\nCompiler log:\n{text}"
    return {"stage": stage, "report": report}


def _found(root, run_id, round):
    found = []
    rounds = layout.run_dir(root, run_id) / "rounds"
    for q in _listed(root, rounds, range(round), _round_name(root, run_id)):
        directory = layout.attempt_dir(root, run_id, q, "coder", 1, 1).parent
        numbers = range(1, keys.MAX_INTEGER + 1)
        for a in _listed(root, directory, numbers, _attempt_name(root, run_id, q)):
            path = layout.attempt_artefact(root, run_id, q, 1, a, "spec.json")
            document = _spec(root, path)
            if document is not None:
                techniques = [t["id"] for t in document["guidance"]["techniques"]]
                found.append((q, a, techniques))
    return found


def _listed(root, directory, numbers, name_of):
    try:
        names = os.listdir(directory)
    except run_files.NOT_THERE:
        return []
    except OSError as error:
        raise _unreadable(root, directory, "could not be listed", error) from error
    taken = []
    for name in names:
        if name.isascii() and name.isdigit():
            n = int(name)
            if n in numbers and name_of(n) == name:
                taken.append(n)
    return sorted(taken)


def _round_name(root, run_id):
    return lambda n: layout.round_dir(root, run_id, n).name


def _attempt_name(root, run_id, q):
    return lambda n: layout.attempt_dir(root, run_id, q, "coder", 1, n).name


def _spec(root, path):
    try:
        mode = os.lstat(path).st_mode
    except run_files.NOT_THERE:
        return None
    except OSError as error:
        raise _unreadable(root, path, "could not be read", error) from error
    if not stat.S_ISREG(mode):
        raise _refused(root, path, "is no regular file")
    try:
        content = path.read_bytes()
    except OSError as error:
        raise _unreadable(root, path, "could not be read", error) from error
    try:
        document = spec_file.parse(content)
        named = spec_file.final_name(root, document)
    except (
        spec_file.InvalidSpecFileError,
        spec_file.UnsupportedVersionError,
        layout.InvalidPathValueError,
    ) as error:
        raise _refused(root, path, str(error)) from error
    if named != path:
        raise _refused(root, path, "its id is not the tuple and run of its path")
    return document


def _compiler_log(root, path):
    try:
        mode = os.lstat(path).st_mode
    except run_files.NOT_THERE:
        return ""
    except OSError as error:
        raise _unreadable(root, path, "could not be read", error) from error
    if not stat.S_ISREG(mode):
        raise _refused(root, path, "is no regular file")
    try:
        content = path.read_bytes()
    except OSError as error:
        raise _unreadable(root, path, "could not be read", error) from error
    if content.startswith(codecs.BOM_UTF8):
        raise _refused(root, path, "starts with a byte order mark")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise _refused(root, path, f"is no UTF-8 at byte {error.start}") from error


def _relative(root, path):
    return path.relative_to(root).as_posix()


def _refused(root, path, problem):
    message = f"{_relative(root, path)}: {problem}"
    return tools.ToolFailure(KIND_FEEDBACK_UNREADABLE, message)


def _unreadable(root, path, what, error):
    reported = ": ".join(filter(None, (type(error).__name__, error.strerror)))
    return _refused(root, path, f"{what}: {reported}")
