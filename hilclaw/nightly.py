"""The entry point of the nightly end-to-end routine (``PROCESS/NIGHTLY.md``, DRIVER D17).

Command line: ``python -m hilclaw.nightly <base>``. The one argument names an
existing directory, the routine's work folder outside every checkout. One
call is one **firing**: it makes the directory ``<base>/<firing id>``, where
the firing id is the UTC start time as ``YYYYMMDDTHHMMSSZ``, and drives one
first-case run of the nightly configuration through the two runtime entries,
``python -m hilclaw.new_run`` and ``python -m hilclaw.turn_start``, each started
once. This is runtime code: on the nightly machine the turn start starts the
real ``claude``. It is tested only against a stub ``claude`` and fake entries
that the tests write (D16); besides the nightly routine, only an executor's
test run (DRIVER D25) starts it for real.

**The configuration** (HQ-0076 (1), the P2-5 configuration as it is): the
local ``cpu_standin`` (:func:`hilclaw.standin_profile.local_record`,
``hw_source`` ``external``) x GEMM fp32 ``row_major`` m=8 k=16 n=8,
``latency_minimisation``, one candidate per round, ``n_max`` 6, one draw,
``rtol`` 1e-4 and ``atol`` 1e-5, ``round_budget`` 5. Nothing else bounds the
firing: no timeout and no turn count (HQ-0076 (4)).

**One firing**, in this order; the first step that fails ends it:

1. the lock ``<base>/nightly.lock`` (``flock``, released when the process
   ends): held by another firing -> ``prepare/overlap``; a host without
   ``fcntl`` -> ``prepare/no_posix_host``;
2. the environment: ``HILCLAW_CODER_IMAGE``, ``HILCLAW_CODER_OAUTH_TOKEN`` and
   ``HILCLAW_STANDIN_IMAGE`` non-empty, ``claude``, ``clang``, ``docker`` and ``git`` on
   ``PATH`` -> ``prepare/missing:<names>``;
3. the data root ``<firing>/data``, a new git repository of this firing only,
   never pushed (``prepare/data_root``), and the hw_profile record
   (``prepare/hw_profile``);
4. ``new_run`` on ``<firing>/instance.json``; anything but ``started`` fails;
5. ``turn_start`` on the run id of the ``started`` line; ``run_over`` passes,
   anything else fails.

The children run with the caller's environment, without ``CLAUDECODE`` and
``CLAUDE_CODE_ENTRYPOINT`` (the marks of a host Claude Code session), with
``HILCLAW_DATA_REPO_LOCAL_PATH`` set to the firing's data root,
``HILCLAW_DATA_REPO_URL`` set to :data:`DATA_REPO_URL` and this checkout first
on ``PYTHONPATH``; their working directory is the firing directory.

**The cause** of a failure, a hint for whoever fixes it: ``environment``
(the machine lacks something the run needs: the outcomes above under
``prepare``, ``new_run`` ``no_data_root`` and ``file_system``, ``turn_start``
errors ``no_claude`` and ``no_data_root``, a check stopped at ``no_claude``,
``not_logged_in`` or ``login_unreadable``), ``undetermined`` (``failed_turn``
and a check stopped at ``session_failed``: a usage limit or an expired login
looks the same from the outcome line) and ``code`` (everything else). The
**signature** ``<stage>/<outcome>[/<datum>]`` names the failure for
de-duplication.

**What it writes** into the firing directory: ``instance.json``, the standard
error of each entry (``new_run.stderr``, ``turn_start.stderr``, the turn
sessions' output included), ``result.json`` (the record below) and, after a
failure, ``issue-title.txt`` (``nightly: <signature>``) and ``issue.md``, the
issue body: the report marker, signature, cause, commit, steps and at most
:data:`TAIL_LINES` last lines of the failing entry's standard error, with the
values of secret-looking environment variables and the home directory
replaced. ``result.json`` holds ``firing``, ``commit``, ``verdict``
(``pass``/``fail``), ``cause``, ``signature``, ``detail``, ``run_id`` and
``steps`` (one ``{stage, exit_status, line}`` per entry started).

**What the caller is told**: one line on standard output, a compact JSON
object with ``verdict``, and for a firing also ``signature``, ``cause`` and
``firing`` (the directory). Status 0 for a pass, 10 for a failure, 20 for
bad usage (not exactly one argument, or no existing directory), when nothing
is written. It registers no issue, pushes nothing, writes nothing into this
checkout and keeps no state between firings.
"""

import contextlib
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from hilclaw import (
    keys,
    new_run,
    selfcheck_login,
    selfcheck_outcome,
    standin_profile,
    turn_start,
)

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

REPOSITORY = Path(__file__).resolve().parent.parent
DATA_REPO_URL = "nightly.invalid/no-remote"
ROUND_BUDGET = 5
OP = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": {"m": 8, "k": 16, "n": 8},
    "dtype": "fp32",
    "layout": "row_major",
}
REQUIRED_VARIABLES = (
    "HILCLAW_CODER_IMAGE",
    "HILCLAW_CODER_OAUTH_TOKEN",
    "HILCLAW_STANDIN_IMAGE",
)
REQUIRED_PROGRAMS = ("claude", "clang", "docker", "git")
HOST_SESSION_MARKS = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")
PROFILE_TIMEOUT_S = 60
TAIL_LINES = 40
TAIL_WIDTH = 400
LINE_LIMIT = 2000

PASS = "pass"
FAIL = "fail"
CODE = "code"
ENVIRONMENT = "environment"
UNDETERMINED = "undetermined"
EXIT_PASS = 0
EXIT_FAIL = 10
EXIT_USAGE = 20

_ENVIRONMENT_NEW_RUN = (new_run.NO_DATA_ROOT, new_run.FILE_SYSTEM)
_ENVIRONMENT_ERRORS = (turn_start.NO_CLAUDE, turn_start.NO_DATA_ROOT)
_ENVIRONMENT_CHECKS = (
    selfcheck_login.NO_CLAUDE,
    selfcheck_login.NOT_LOGGED_IN,
    selfcheck_login.LOGIN_UNREADABLE,
)
_SECRET_NAME = re.compile(r"TOKEN|KEY|SECRET|PASSWORD", re.IGNORECASE)
_UNSAFE = re.compile(r"[^A-Za-z0-9_=.:,-]")


class _Stop(Exception):
    def __init__(self, cause, signature, detail=None):
        super().__init__(signature)
        self.cause = cause
        self.signature = signature
        self.detail = detail


def document(hw_profile):
    """Return the ``instance.json`` document of the nightly run for ``hw_profile``."""
    return {
        "schema_version": 1,
        "hw_profile": {
            "key": keys.hw_profile_key(hw_profile).name,
            "record": hw_profile,
        },
        "op_signature": {"key": keys.op_signature_key(OP).name, "record": OP},
        "objective": {
            "objectives": [{"type": "latency_minimisation"}],
            "constraints": [],
        },
        "candidates_per_round": 1,
        "n_max": 6,
        "draws": 1,
        "tolerance": {"rtol": 1e-4, "atol": 1e-5},
        "round_budget": ROUND_BUDGET,
    }


def classify(stage, told):
    """Return ``(cause, signature)`` for the outcome line ``told`` of ``stage``.

    ``stage`` is ``"new_run"`` or ``"turn_start"``; ``told`` is the parsed line,
    or anything that is no ``dict`` with a string ``outcome`` for a line that
    could not be read. Not meant for ``started`` and ``run_over``.
    """
    if not isinstance(told, dict) or not isinstance(told.get("outcome"), str):
        return CODE, f"{stage}/unreadable_outcome"
    outcome = told["outcome"]
    if stage == "new_run":
        cause = ENVIRONMENT if outcome in _ENVIRONMENT_NEW_RUN else CODE
        return cause, _signature(stage, outcome)
    if outcome == turn_start.FAILED_TURN:
        return UNDETERMINED, _signature(
            stage, outcome, f"exit_status={told.get('exit_status')}"
        )
    if outcome == turn_start.OPEN_STATE:
        return CODE, _signature(stage, outcome, told.get("reason"))
    if outcome == turn_start.ERROR:
        error = told.get("error")
        return (ENVIRONMENT if error in _ENVIRONMENT_ERRORS else CODE), _signature(
            stage, outcome, error
        )
    if outcome == turn_start.STOPPED_AT_CHECK:
        check = told.get("check")
        word = (
            check.get("outcome")
            if isinstance(check, dict)
            else f"check_fault={told.get('check_fault')}"
        )
        if word in _ENVIRONMENT_CHECKS:
            cause = ENVIRONMENT
        elif word == selfcheck_outcome.SESSION_FAILED:
            cause = UNDETERMINED
        else:
            cause = CODE
        return cause, _signature(stage, outcome, word)
    return CODE, _signature(stage, outcome)


def fire(base, *, environ=None, python=None, profile=None, now=None):
    """Carry out one firing under the existing directory ``base`` and return its record.

    ``environ`` (default ``os.environ``) is the environment the children start
    from; ``python`` the command prefix that runs a module (default
    ``(sys.executable,)``); ``profile`` the hw_profile reader (default
    :func:`hilclaw.standin_profile.local_record`); ``now`` a callable that
    returns the aware UTC start time. Writes the files the module docstring
    lists and returns the ``result.json`` record.
    """
    environ = dict(os.environ if environ is None else environ)
    python = tuple(python or (sys.executable,))
    profile = profile or standin_profile.local_record
    started = (now or _utc_now)()
    firing = Path(base) / started.strftime("%Y%m%dT%H%M%SZ")
    firing.mkdir()
    record = {
        "firing": firing.name,
        "commit": _commit(),
        "verdict": FAIL,
        "cause": None,
        "signature": None,
        "detail": None,
        "run_id": None,
        "steps": [],
    }
    tail_of = None
    with _locked(Path(base) / "nightly.lock") as held:
        try:
            if held is None:
                raise _Stop(
                    ENVIRONMENT, "prepare/no_posix_host", "this host has no fcntl"
                )
            if not held:
                raise _Stop(
                    ENVIRONMENT, "prepare/overlap", "another firing holds the lock"
                )
            env = _child_environment(environ, firing / "data")
            _check_environment(env)
            _make_data_root(env, firing / "data")
            given = firing / "instance.json"
            given.write_text(
                json.dumps(document(_profile(profile)), indent=2), encoding="utf-8"
            )
            tail_of = firing / "new_run.stderr"
            told = _entry(record, "new_run", python, given, env, firing, tail_of)
            if not isinstance(told, dict) or told.get("outcome") != new_run.STARTED:
                raise _Stop(*classify("new_run", told))
            record["run_id"] = told.get("run_id")
            tail_of = firing / "turn_start.stderr"
            told = _entry(
                record, "turn_start", python, record["run_id"], env, firing, tail_of
            )
            if not isinstance(told, dict) or told.get("outcome") != turn_start.RUN_OVER:
                raise _Stop(*classify("turn_start", told))
            record["verdict"] = PASS
            tail_of = None
        except _Stop as stop:
            record.update(
                cause=stop.cause, signature=stop.signature, detail=stop.detail
            )
    (firing / "result.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    if record["verdict"] == FAIL:
        (firing / "issue-title.txt").write_text(
            f"nightly: {record['signature']}\n", encoding="utf-8"
        )
        (firing / "issue.md").write_text(
            issue_body(record, tail_of, environ), encoding="utf-8"
        )
    return record


def issue_body(record, tail_of, environ):
    """Return the issue body for the failed firing ``record``.

    ``tail_of`` names the standard-error file of the failing entry, or ``None``;
    ``environ`` gives the values that are replaced before anything is quoted.
    """
    lines = [
        f"nightly-report: {record['firing']}",
        f"signature: {record['signature']}",
        f"cause: {record['cause']}",
        "",
        f"- commit: `{record['commit']}`",
        f"- run id: `{record['run_id']}`",
    ]
    if record["detail"]:
        lines.append(f"- detail: {record['detail']}")
    for step in record["steps"]:
        line = json.dumps(step["line"])[:LINE_LIMIT]
        lines.append(
            f"- {step['stage']}: exit status {step['exit_status']}, line `{line}`"
        )
    tail = _tail(tail_of)
    if tail:
        lines += ["", "Last lines of standard error:", "", "```text", *tail, "```"]
    lines += [
        "",
        "Registered by the nightly routine (PROCESS/NIGHTLY.md); a regression signal only (D17).",
    ]
    return _redacted("\n".join(lines) + "\n", environ)


def main(argv=None):
    """Run the command line and return the exit status."""
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or not os.path.isdir(argv[0]):
        _say({"verdict": "bad_usage", "reason": "give one existing directory"})
        return EXIT_USAGE
    record = fire(argv[0])
    _say(
        {
            "verdict": record["verdict"],
            "signature": record["signature"],
            "cause": record["cause"],
            "firing": str(Path(argv[0]) / record["firing"]),
        }
    )
    return EXIT_PASS if record["verdict"] == PASS else EXIT_FAIL


def _signature(stage, outcome, datum=None):
    parts = [stage, outcome] if datum is None else [stage, outcome, str(datum)]
    return "/".join(_UNSAFE.sub("_", part)[:80] for part in parts)


def _utc_now():
    return datetime.datetime.now(datetime.UTC)


def _commit():
    git = shutil.which("git")
    if git is None:
        return "unknown"
    done = subprocess.run(
        [git, "-C", str(REPOSITORY), "rev-parse", "HEAD"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
    )
    return (
        done.stdout.decode("ascii", "replace").strip()
        if done.returncode == 0
        else "unknown"
    )


@contextlib.contextmanager
def _locked(path):
    if fcntl is None:
        yield None
        return
    with open(path, "a", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            held = False
        else:
            held = True
        yield held


def _child_environment(environ, data):
    env = {
        name: value for name, value in environ.items() if name not in HOST_SESSION_MARKS
    }
    env["HILCLAW_DATA_REPO_LOCAL_PATH"] = str(data)
    env["HILCLAW_DATA_REPO_URL"] = DATA_REPO_URL
    given = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(REPOSITORY) + (os.pathsep + given if given else "")
    return env


def _check_environment(env):
    missing = [name for name in REQUIRED_VARIABLES if not env.get(name)]
    missing += [
        name
        for name in REQUIRED_PROGRAMS
        if shutil.which(name, path=env.get("PATH")) is None
    ]
    if missing:
        raise _Stop(ENVIRONMENT, "prepare/missing:" + ",".join(missing))


def _make_data_root(env, data):
    git = shutil.which("git", path=env.get("PATH"))
    done = subprocess.run(
        [git, "init", "-q", "-b", "main", str(data)],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
    )
    if done.returncode != 0:
        raise _Stop(
            ENVIRONMENT, "prepare/data_root", f"git init exited {done.returncode}"
        )


def _profile(profile):
    try:
        return profile("external", timeout_s=PROFILE_TIMEOUT_S)
    except (standin_profile.UnreadableFactError, OSError) as e:
        raise _Stop(ENVIRONMENT, "prepare/hw_profile", type(e).__name__) from e


def _entry(record, stage, python, argument, env, firing, errors):
    with open(errors, "wb") as sink:
        done = subprocess.run(
            [*python, "-m", f"hilclaw.{stage}", str(argument)],
            cwd=firing,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=sink,
            check=False,
        )
    text = done.stdout.decode("utf-8", "replace")
    try:
        told = json.loads(text)
    except ValueError:
        told = None
    record["steps"].append(
        {
            "stage": stage,
            "exit_status": done.returncode,
            "line": told if told is not None else text[:LINE_LIMIT],
        }
    )
    return told


def _tail(path):
    if path is None or not path.is_file():
        return []
    text = path.read_bytes().decode("utf-8", "replace").replace("```", "'''")
    return [line[:TAIL_WIDTH] for line in text.splitlines()[-TAIL_LINES:]]


def _redacted(text, environ):
    secrets = sorted(
        (
            value
            for name, value in environ.items()
            if _SECRET_NAME.search(name) and len(value) >= 8
        ),
        key=len,
        reverse=True,
    )
    for value in secrets:
        text = text.replace(value, "[redacted]")
    home = str(Path.home())
    if len(home) > 1:
        text = text.replace(home, "~")
    return text


def _say(line):
    sys.stdout.write(json.dumps(line, separators=(",", ":")) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    sys.exit(main())
