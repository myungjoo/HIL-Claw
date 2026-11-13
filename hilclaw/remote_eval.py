"""Given-code evaluation on the owner's LAN aarch64 machine (ADR-0205; PLAN P3-17).

The development driver's means of running ``python -m hilclaw.given_eval``
(ADR-0200 decision 5) on that one machine, through :mod:`hilclaw.remote_run`
only. Everything happens in the remote directory of a task,
``hilclaw-driver/T-NNNN/`` under the account's home:

* :func:`prepare` makes the directory, unpacks a snapshot of the package
  (a ``tar`` archive, by default :func:`snapshot` of the checkout's ``HEAD``)
  into ``package/`` and makes a fresh data root ``data/`` with ``git init``
  and a repository-local commit identity (no global git configuration).
* :func:`hw_profile` reads the ``cpu_standin`` hw_profile record of that
  machine there, with :func:`hilclaw.standin_profile.local_record` and the
  named image.
* :func:`evaluate` copies the request and the C file there and runs the
  given-code evaluation with the host's ``python3`` against ``data/``, with
  ``HILCLAW_STANDIN_IMAGE`` naming the image, so every build and process runs
  in a container of that image on that machine (ADR-0144).
* :func:`fetch` brings the data root back as one ``git bundle``.

Every argument is checked before anything is started. A remote call ends in
one of four states, told apart: :data:`OK`, :data:`REMOTE_STATUS` (a non-zero
status of the remote program), :data:`SSH_FAILED` and :data:`TIMED_OUT`. No
result, message or file names the destination; the commands reported hold
:data:`hilclaw.remote_run.PLACEHOLDER`.

The machine is no backend of a run: this module is no FR-10 tool, has no
registry entry, and starts no ``claude``.
"""

import json
import math
import os
import subprocess
from pathlib import Path
from typing import NamedTuple

from hilclaw import remote_run, standin_container

OK = "ok"
REMOTE_STATUS = "remote_status"
SSH_FAILED = "ssh_failed"
TIMED_OUT = "timed_out"
PACKAGE = "package"
DATA = "data"
REQUEST = "request.json"
CODE = "given.c"
BUNDLE = "data.bundle"
PYTHON = ("python3",)
SNAPSHOT_PATHS = ("hilclaw", "catalog", "hilclaw.config.json")
IDENTITY = ("hilclaw-driver", "hilclaw-driver@example.invalid")
REPOSITORY = Path(__file__).resolve().parent.parent

_IMAGE_VARIABLE = "HILCLAW_STANDIN_IMAGE"
_DATA_VARIABLE = "HILCLAW_DATA_REPO_LOCAL_PATH"
_IN_PACKAGE = 'cd "$1" && shift && exec env "$@"'
_UNPACK = 'mkdir -p "$1" && tar -xf - -C "$1"'
_INIT = (
    'git init -q "$1" && git -C "$1" config user.name "$2"'
    ' && git -C "$1" config user.email "$3"'
)
_PROFILE = (
    "import json, sys\n"
    "from hilclaw import standin_profile\n"
    "record = standin_profile.local_record("
    "sys.argv[1], timeout_s=float(sys.argv[2]), image=sys.argv[3])\n"
    "print(json.dumps(record, sort_keys=True))\n"
)


class Outcome(NamedTuple):
    """The end of one remote call.

    ``state`` is :data:`OK`, :data:`REMOTE_STATUS`, :data:`SSH_FAILED` or
    :data:`TIMED_OUT`; ``returncode`` the remote status (``None`` unless the
    remote program ended); ``stdout`` and ``stderr`` its output decoded as
    UTF-8 with replacement (empty after an ssh failure); ``command`` the
    reported command with the placeholder in place of the destination.
    """

    state: str
    returncode: int | None
    stdout: str
    stderr: str
    command: tuple[str, ...]


class RemoteStepError(RuntimeError):
    """A step of :func:`prepare`, :func:`hw_profile` or :func:`fetch` did not end with status 0.

    ``step`` names the step and ``outcome`` is its :class:`Outcome`. The
    message names the step and the state, never the destination.
    """

    def __init__(self, step, outcome):
        detail = (
            f"status {outcome.returncode}"
            if outcome.state == REMOTE_STATUS
            else outcome.state
        )
        super().__init__(f"remote step {step} failed: {detail}")
        self.step = step
        self.outcome = outcome


def snapshot(*, revision="HEAD", repository=REPOSITORY, timeout_s=120):
    """Return a ``tar`` archive of :data:`SNAPSHOT_PATHS` at ``revision`` of ``repository`` (``git archive``; no ``.git``)."""
    done = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "archive",
            "--format=tar",
            revision,
            "--",
            *SNAPSHOT_PATHS,
        ],
        capture_output=True,
        check=True,
        timeout=timeout_s,
    )
    return done.stdout


def prepare(task, *, timeout_s, archive=None, environ=None, ssh=remote_run.SSH):
    """Make the remote directory of ``task`` with the package snapshot and a fresh data root.

    ``archive`` is the ``tar`` bytes of the package (default :func:`snapshot`).
    Refuses ``task``, ``timeout_s`` and the destination as :func:`evaluate`
    does, before anything is started, and raises :class:`RemoteStepError` for
    a step that did not end with status 0.
    """
    _check(task, timeout_s, environ)
    if archive is None:
        archive = snapshot()
    if not isinstance(archive, bytes):
        raise TypeError(f"archive must be bytes, not {type(archive).__name__}")
    base = remote_run.task_directory(task)
    common = {"timeout_s": timeout_s, "environ": environ, "ssh": ssh}
    _step("mkdir", remote_run.make_task_directory(task, **common))
    package = remote_run.remote_path(task, PACKAGE)
    _step(
        "unpack",
        remote_run.run(
            ("sh", "-c", _UNPACK, "sh", package), stdin_data=archive, **common
        ),
    )
    _step(
        "init",
        remote_run.run(
            ("sh", "-c", _INIT, "sh", f"{base}/{DATA}", *IDENTITY), **common
        ),
    )


def hw_profile(
    task,
    image,
    hw_source,
    *,
    timeout_s,
    python=PYTHON,
    environ=None,
    ssh=remote_run.SSH,
):
    """Return the ``cpu_standin`` hw_profile record that machine gives for ``image``, as a ``dict``.

    Runs :func:`hilclaw.standin_profile.local_record` in the prepared package
    with the host's ``python``; ``timeout_s`` is both the remote call's limit
    and that of each command the record starts. Raises :class:`RemoteStepError`
    when the call does not end with status 0, and :class:`ValueError` when
    its standard output is no JSON object.
    """
    _check(task, timeout_s, environ)
    standin_container.check_image(image)
    outcome = _in_package(
        task,
        (*python, "-c", _PROFILE, hw_source, str(timeout_s), image),
        timeout_s,
        environ,
        ssh,
    )
    _step("hw_profile", outcome)
    record = json.loads(outcome.stdout)
    if isinstance(record, dict):
        return record
    raise ValueError("the remote hw_profile output is no JSON object")


def evaluate(
    request,
    code,
    *,
    task,
    image,
    timeout_s,
    python=PYTHON,
    environ=None,
    ssh=remote_run.SSH,
):
    """Run the given-code evaluation of ``request`` and ``code`` in the prepared directory of ``task``.

    ``request`` and ``code`` are local files, copied to :data:`REQUEST` and
    :data:`CODE`; ``image`` is the arm64 ``cpu_standin`` image named in
    ``HILCLAW_STANDIN_IMAGE``; ``timeout_s`` (required, positive and finite)
    is the limit of each remote call. Returns the :class:`Outcome` of the
    evaluation; its one summary line, when written, is the last line of
    ``stdout`` (:func:`summary`). A copy that does not end with status 0
    raises :class:`RemoteStepError`.

    Refused before anything is started, as by every function here: a ``task``
    not of the form ``T-NNNN`` (:class:`ValueError`, :class:`TypeError`), a
    ``timeout_s`` that is no positive finite number, and an unset
    (:class:`hilclaw.remote_run.NotConfiguredError`) or refused destination.
    Here also an ``image`` :func:`hilclaw.standin_container.check_image`
    refuses, and a ``request`` or ``code`` that is no existing file
    (:class:`FileNotFoundError`).
    """
    _check(task, timeout_s, environ)
    standin_container.check_image(image)
    for path in (request, code):
        if not os.path.isfile(path):
            raise FileNotFoundError(f"not a file: {os.fspath(path)}")
    common = {"timeout_s": timeout_s, "environ": environ, "ssh": ssh}
    _step("put_request", remote_run.put(request, task, REQUEST, **common))
    _step("put_code", remote_run.put(code, task, CODE, **common))
    return _in_package(
        task,
        (
            f"{_IMAGE_VARIABLE}={image}",
            f"{_DATA_VARIABLE}=../{DATA}",
            *python,
            "-m",
            "hilclaw.given_eval",
            f"../{REQUEST}",
            f"../{CODE}",
        ),
        timeout_s,
        environ,
        ssh,
    )


def summary(outcome):
    """Return the summary object of an evaluation's :class:`Outcome`, or ``None`` when it wrote none."""
    lines = outcome.stdout.splitlines()
    if not lines:
        return None
    try:
        value = json.loads(lines[-1])
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def fetch(task, local_path, *, timeout_s, environ=None, ssh=remote_run.SSH):
    """Bundle the remote data root of ``task`` (``git bundle --all``) and copy it to ``local_path``.

    Raises :class:`RemoteStepError` when the bundle or the copy does not end
    with status 0; ``local_path`` is written only on success.
    """
    _check(task, timeout_s, environ)
    base = remote_run.task_directory(task)
    common = {"timeout_s": timeout_s, "environ": environ, "ssh": ssh}
    _step(
        "bundle",
        remote_run.run(
            (
                "git",
                "-C",
                f"{base}/{DATA}",
                "bundle",
                "create",
                "-q",
                f"../{BUNDLE}",
                "--all",
            ),
            **common,
        ),
    )
    _step("get_bundle", remote_run.get(task, BUNDLE, local_path, **common))


def _check(task, timeout_s, environ):
    remote_run.task_directory(task)
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)):
        raise TypeError(f"timeout_s must be a number, not {type(timeout_s).__name__}")
    if not 0 < timeout_s < math.inf:
        raise ValueError(f"timeout_s must be positive and finite: {timeout_s!r}")
    remote_run.destination(environ)


def _in_package(task, arguments, timeout_s, environ, ssh):
    package = remote_run.remote_path(task, PACKAGE)
    return _outcome(
        remote_run.run(
            ("sh", "-c", _IN_PACKAGE, "sh", package, *arguments),
            timeout_s=timeout_s,
            environ=environ,
            ssh=ssh,
        )
    )


def _outcome(result):
    if result.timed_out:
        state = TIMED_OUT
    elif result.ssh_failed:
        state = SSH_FAILED
    elif result.returncode != 0:
        state = REMOTE_STATUS
    else:
        state = OK
    return Outcome(
        state,
        result.returncode,
        result.stdout.decode("utf-8", "replace"),
        result.stderr.decode("utf-8", "replace"),
        result.command,
    )


def _step(step, outcome):
    if not isinstance(outcome, Outcome):
        outcome = _outcome(outcome)
    if outcome.state != OK:
        raise RemoteStepError(step, outcome)
    return outcome
