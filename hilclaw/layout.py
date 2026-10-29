"""Paths of the data plane, as fixed by ADR-0004 (layout version 1).

``ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`` fixes the directory
tree of the data repository: the run tree ``runs/<run_id>/`` with its rounds,
writer roles, candidates and attempts (decisions 1 to 4) and the knowledge tree
``db/<hw_profile_key>/<op_signature>/`` (decision 5). This module turns the
tuple (``run_id``, ``round``, ``candidate``, ``attempt``) of ADR-0002 and the
two key directory names of ADR-0001 into those paths by formatting alone.
:func:`build_log_file` adds the file of a compiler's log of ADR-0078
decision 3, and of ADR-0108 decision 3 for the timing build of ``sim.run``
and ``board.run``, which is not one of :data:`ATTEMPT_ARTEFACTS`.

Every function is pure and returns a :class:`pathlib.Path` below
``Path(data_root)``, as :func:`hilclaw.cas.blob_path` does for
``blobs/sha256/``, which is not repeated here. ``data_root`` is given by the
caller and is used as it is: it is not resolved, made absolute or checked.
Every other component is checked against a closed pattern, taken from a fixed
list or formatted from an integer, so no separator, ``.`` or ``..`` can enter
and no result leaves ``data_root``. A value that breaks a rule raises
:class:`InvalidPathValueError`; nothing is truncated, normalised or corrected.
Strings and integers are exactly ``str`` and ``int``, as in :mod:`hilclaw.keys`.

What this module does not do: it reads, writes, creates, lists and checks no
file or directory; it defines no field or content of any file named here; it
builds no ``run_id`` and does not know whether one is unique; it does not
verify that a key directory name belongs to a record; and it enforces neither
the single writer of a directory nor any isolation (ADR-0004 decision 10).
It reads no stamp of a run: :data:`LAYOUT_VERSION` is the layout this module
builds and not what a run states (ADR-0024 decisions 4 and 5).
"""

import re
import reprlib
from pathlib import Path

from hilclaw import keys

LAYOUT_VERSION = 1
RUN_FILES = ("STATE.json", "instance.json", "events.ndjson", "artifacts.json")
ROLES = ("decision", "coder", "measure", "eval")
ATTEMPT_ROLES = ("coder", "measure", "eval")
OP_SIGNATURE_FILES = ("op_signature.json", "best.json", "technique_stats.json")

_ARTEFACT_ROLE = {
    "spec.json": "coder",
    "output": "coder",
    "build.json": "measure",
    "sim.json": "measure",
    "board.json": "measure",
    "profile.json": "measure",
    "eval.json": "eval",
}
ATTEMPT_ARTEFACTS = tuple(_ARTEFACT_ROLE)
BUILD_LOG_STEPS = (
    "correctness_check_sim_v2",
    "correctness_check_board_v2",
    "sim_run_timing",
    "board_run_timing",
)

_RUN_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
_KEY_NAME = re.compile(rf"[a-z][a-z0-9_]{{0,31}}-[0-9a-f]{{{keys.NAME_DIGEST_LENGTH}}}")


class InvalidPathValueError(ValueError):
    """A value cannot be part of a path of ADR-0004; the message names the argument and the rule."""


def check_run_id(value):
    """Return ``value`` when it is a valid ``run_id`` directory name (ADR-0004 decision 8).

    A ``run_id`` is a ``str`` that matches ``[a-z0-9][a-z0-9_-]{0,63}`` as a
    whole. Only this constraint is checked: the form of an id that a component
    of the system builds, which :mod:`hilclaw.run_id` writes, is ADR-0027
    decision 2 and no rule of validity (ADR-0027 decision 1), so it is not
    checked here.
    Raises :class:`InvalidPathValueError` otherwise.
    """
    if type(value) is not str or not _RUN_ID.fullmatch(value):
        _fail("run_id", f"a str matching {_RUN_ID.pattern}", value)
    return value


def run_dir(data_root, run_id):
    """Return ``runs/<run_id>``, the directory of one run."""
    return Path(data_root) / "runs" / check_run_id(run_id)


def run_file(data_root, run_id, name):
    """Return the run-level file ``name``, one of :data:`RUN_FILES`, in :func:`run_dir`."""
    return run_dir(data_root, run_id) / _one_of("name", name, RUN_FILES)


def round_dir(data_root, run_id, round):
    """Return ``runs/<run_id>/rounds/<RRRR>``.

    ``round`` is an integer from 0 to :data:`hilclaw.keys.MAX_INTEGER`, written
    in decimal and zero-padded to at least four digits (decision 2).
    """
    return run_dir(data_root, run_id) / "rounds" / _number("round", round, 0, 4)


def role_dir(data_root, run_id, round, role):
    """Return ``<round_dir>/<role>``, the write prefix of ``role``, one of :data:`ROLES`."""
    return round_dir(data_root, run_id, round) / _one_of("role", role, ROLES)


def decision_log(data_root, run_id, round):
    """Return ``<round_dir>/decision/decision.md``, the narrative of the round's decision log."""
    return role_dir(data_root, run_id, round, "decision") / "decision.md"


def hypothesis_record(data_root, run_id, round):
    """Return ``<round_dir>/decision/hypotheses.json``, the hypothesis record of the round.

    The file is the structured part of the round's decision log (ADR-0059
    decision 1). ``round`` is an integer from 1 to
    :data:`hilclaw.keys.MAX_INTEGER`: round 0 has no hypothesis record
    (ADR-0059 decision 5). Every other rule is that of :func:`round_dir`.
    """
    _number("round", round, 1, 4)
    return role_dir(data_root, run_id, round, "decision") / "hypotheses.json"


def verdict_record(data_root, run_id, round):
    """Return ``<round_dir>/eval/verdicts.json``, the verdicts of the hypotheses of the round.

    The file is the evaluation role's, one per round (ADR-0071 decision 1).
    ``round`` is an integer from 1 to :data:`hilclaw.keys.MAX_INTEGER`: round 0
    has no verdicts file (ADR-0071 decision 6). Every other rule is that of
    :func:`round_dir`.
    """
    _number("round", round, 1, 4)
    return role_dir(data_root, run_id, round, "eval") / "verdicts.json"


def attempt_dir(data_root, run_id, round, role, candidate, attempt):
    """Return ``<round_dir>/<role>/candidates/<CC>/attempts/<AA>``.

    ``role`` is one of :data:`ATTEMPT_ROLES`: ADR-0004 fixes no candidate level
    for ``decision``. ``candidate`` and ``attempt`` are integers from 1 to
    :data:`hilclaw.keys.MAX_INTEGER`, written in decimal and zero-padded to at
    least two digits (decision 3).
    """
    return (
        round_dir(data_root, run_id, round)
        / _one_of("role", role, ATTEMPT_ROLES)
        / "candidates"
        / _number("candidate", candidate, 1, 2)
        / "attempts"
        / _number("attempt", attempt, 1, 2)
    )


def attempt_artefact(data_root, run_id, round, candidate, attempt, name):
    """Return the artefact ``name`` of an attempt, below the role that writes it.

    ``name`` is one of :data:`ATTEMPT_ARTEFACTS` and selects the role:
    ``spec.json`` and ``output`` (a directory) are below ``coder/``,
    ``build.json``, ``sim.json``, ``board.json`` and ``profile.json`` below
    ``measure/``, and ``eval.json`` below ``eval/``.
    """
    role = _ARTEFACT_ROLE[_one_of("name", name, ATTEMPT_ARTEFACTS)]
    return attempt_dir(data_root, run_id, round, role, candidate, attempt) / name


def build_log_file(data_root, run_id, round, candidate, attempt, step, execution):
    """Return ``<measure attempt_dir>/build-log-<step>-<EE>.txt``, the file of a compiler's log.

    The file keeps the log of the build of one check of ``correctness.check``
    (ADR-0078 decision 3) or of the timing build of one call of ``sim.run``
    or ``board.run`` (ADR-0108 decision 3). It is not one of
    :data:`ATTEMPT_ARTEFACTS`: it is no record of a result. ``step`` is one
    of :data:`BUILD_LOG_STEPS`: ``correctness_check_sim_v2`` and
    ``correctness_check_board_v2``, the two ``step`` values of
    ``correctness.check`` (ADR-0183 decisions 2 and 7), then
    ``sim_run_timing`` and ``board_run_timing``, the one of each run tool
    (ADR-0062 decision 3). Any other value is refused, the four check values
    ADR-0183 retired included. ``execution`` is an
    integer from 1 to :data:`hilclaw.keys.MAX_INTEGER`, written in decimal and
    zero-padded to at least two digits, never truncated. ``run_id``,
    ``round``, ``candidate`` and ``attempt`` are checked as
    :func:`attempt_dir` checks them.
    """
    directory = attempt_dir(data_root, run_id, round, "measure", candidate, attempt)
    step = _one_of("step", step, BUILD_LOG_STEPS)
    return directory / f"build-log-{step}-{_number('execution', execution, 1, 2)}.txt"


def hw_profile_dir(data_root, hw_profile_key):
    """Return ``db/<hw_profile_key>``.

    ``hw_profile_key`` is a directory name of the form ADR-0001 decision 3
    produces (:attr:`hilclaw.keys.Key.name`): a name, a hyphen and
    :data:`hilclaw.keys.NAME_DIGEST_LENGTH` lowercase hexadecimal characters.
    Only the form is checked; the digest is not recomputed.
    """
    return Path(data_root) / "db" / _key_name("hw_profile_key", hw_profile_key)


def hw_profile_record(data_root, hw_profile_key):
    """Return ``db/<hw_profile_key>/hw_profile.json``, the full hw_profile record."""
    return hw_profile_dir(data_root, hw_profile_key) / "hw_profile.json"


def op_signature_dir(data_root, hw_profile_key, op_signature):
    """Return ``db/<hw_profile_key>/<op_signature>``; both names as in :func:`hw_profile_dir`."""
    hw_dir = hw_profile_dir(data_root, hw_profile_key)
    return hw_dir / _key_name("op_signature", op_signature)


def op_signature_file(data_root, hw_profile_key, op_signature, name):
    """Return the file ``name``, one of :data:`OP_SIGNATURE_FILES`, in :func:`op_signature_dir`."""
    key_dir = op_signature_dir(data_root, hw_profile_key, op_signature)
    return key_dir / _one_of("name", name, OP_SIGNATURE_FILES)


def case_record(data_root, hw_profile_key, op_signature, run_id, round):
    """Return ``db/<hw_profile_key>/<op_signature>/case-<run_id>-<RRRR>.json``, a stored case.

    The file is the hypothesis-outcome case of round ``round`` of run
    ``run_id`` (ADR-0072 decision 1). ``run_id`` is checked by
    :func:`check_run_id` and ``round`` is an integer from 1 to
    :data:`hilclaw.keys.MAX_INTEGER`, written as in :func:`round_dir`: round 0
    has no case (ADR-0072 decision 3). Both key names are as in
    :func:`op_signature_dir`.
    """
    key_dir = op_signature_dir(data_root, hw_profile_key, op_signature)
    number = _number("round", round, 1, 4)
    return key_dir / f"case-{check_run_id(run_id)}-{number}.json"


def _fail(argument, rule, value):
    got = f"{type(value).__name__} {reprlib.repr(value)}"
    raise InvalidPathValueError(f"{argument}: must be {rule}, got {got}")


def _one_of(argument, value, allowed):
    if type(value) is not str or value not in allowed:
        _fail(argument, "one of " + ", ".join(allowed), value)
    return value


def _number(argument, value, minimum, width):
    if type(value) is not int or not minimum <= value <= keys.MAX_INTEGER:
        _fail(argument, f"an int from {minimum} to {keys.MAX_INTEGER}", value)
    return f"{value:0{width}d}"


def _key_name(argument, value):
    if type(value) is not str or not _KEY_NAME.fullmatch(value):
        _fail(argument, f"a str matching {_KEY_NAME.pattern}", value)
    return value
