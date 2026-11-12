"""Remote process runner for the owner's LAN aarch64 machine (ADR-0204; PLAN P3-17).

:func:`run` runs one argument list on the ssh destination named by the
environment variable :data:`DESTINATION_VARIABLE` and reports what happened in
a :class:`RemoteResult`, which mirrors :class:`hilclaw.local_run.RunResult`
and adds ``ssh_failed``. :func:`make_task_directory`,
:func:`remove_task_directory`, :func:`put` and :func:`get` keep files in the
one remote directory of a task, ``hilclaw-driver/T-NNNN/`` under the account's
home, through the same ssh call.

The means is the ssh client already on the caller's machine with the
authentication already set up there (ADR-0204 decision 2): every call passes
``BatchMode=yes`` and nothing that weakens host-key checking. Each argument is
quoted for the remote POSIX shell, so it reaches the remote program as one
word with no expansion.

No address, account, key path or destination value appears in a result, an
error text or the reported command: the command holds :data:`PLACEHOLDER`
in place of the destination, and the output of a call that ssh itself failed
(status 255) is dropped, since ssh's own messages name the host. A remote
program that itself exits with 255 is reported as an ssh failure.

Known limits: at the time limit only the local ssh process is killed; whether
the remote program ends is not known. Copies are held in memory.
"""

import math
import os
import re
from typing import NamedTuple

from hilclaw import local_run

DESTINATION_VARIABLE = "HILCLAW_AARCH64_SSH"
PLACEHOLDER = "<destination>"
SSH = ("ssh",)
CONNECT_TIMEOUT_S = 15
SSH_FAILURE = 255
TASK_ROOT = "hilclaw-driver"

_OPTIONS = (
    "-q",
    "-T",
    "-o",
    "BatchMode=yes",
    "-o",
    f"ConnectTimeout={CONNECT_TIMEOUT_S}",
    "--",
)
_TASK = re.compile(r"T-[0-9]{4}")
_COMPONENT = re.compile(r"[A-Za-z0-9._-]+")
_WRITE = ("sh", "-c", 'cat > "$1"', "sh")


class RemoteResult(NamedTuple):
    """Outcome of one remote call.

    ``returncode`` is the remote program's exit status, ``None`` when the call
    timed out or ssh itself failed. ``timed_out`` is true when the time limit
    was reached. ``stdout`` and ``stderr`` are the remote program's output,
    not decoded, and empty when ``ssh_failed``. ``command`` is the local
    argument list with :data:`PLACEHOLDER` in place of the destination, and
    ``duration_s`` the wall-clock time of the call in seconds. ``ssh_failed``
    is true when ssh exited with :data:`SSH_FAILURE`.
    """

    returncode: int | None
    timed_out: bool
    stdout: bytes
    stderr: bytes
    command: tuple[str, ...]
    duration_s: float
    ssh_failed: bool


class NotConfiguredError(LookupError):
    """:data:`DESTINATION_VARIABLE` is unset or empty; nothing was started."""


def destination(environ=None):
    """Return the destination named by :data:`DESTINATION_VARIABLE` in ``environ``.

    ``environ`` defaults to :data:`os.environ`. Raises
    :class:`NotConfiguredError` when the variable is unset or empty, and
    :class:`ValueError` when its value begins with ``-`` or holds a character
    outside 0x21 to 0x7E. No error text repeats the value.
    """
    value = (os.environ if environ is None else environ).get(DESTINATION_VARIABLE)
    if not value:
        raise NotConfiguredError(f"{DESTINATION_VARIABLE} is not configured")
    if value.startswith("-") or any(not 0x21 <= ord(c) <= 0x7E for c in value):
        raise ValueError(f"{DESTINATION_VARIABLE} does not hold a usable destination")
    return value


def configured(environ=None):
    """Return whether :data:`DESTINATION_VARIABLE` names a usable destination."""
    try:
        destination(environ)
    except (NotConfiguredError, ValueError):
        return False
    return True


def quote(argument):
    """Return ``argument`` quoted as one word for a POSIX shell."""
    return "'" + argument.replace("'", "'\"'\"'") + "'"


def _check_timeout(timeout_s):
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)):
        raise TypeError(f"timeout_s must be a number, not {type(timeout_s).__name__}")
    if not 0 < timeout_s < math.inf:
        raise ValueError(f"timeout_s must be positive and finite: {timeout_s!r}")


def _check_arguments(arguments):
    if isinstance(arguments, (str, bytes)):
        raise TypeError("arguments must be a sequence of str, not one string")
    arguments = tuple(arguments)
    if not arguments:
        raise ValueError("arguments is empty")
    for argument in arguments:
        if not isinstance(argument, str):
            raise TypeError(f"an argument must be str, not {type(argument).__name__}")
        if "\0" in argument:
            raise ValueError("an argument contains a NUL character")
    return arguments


def run(arguments, *, timeout_s, environ=None, ssh=SSH, stdin_data=None):
    """Run ``arguments`` on the configured destination and return a :class:`RemoteResult`.

    ``arguments`` is a non-empty sequence of ``str``: the remote program and
    its arguments. ``timeout_s`` is required, a positive finite number of
    seconds. ``environ`` is where :data:`DESTINATION_VARIABLE` is read
    (default :data:`os.environ`); ``ssh`` is the local ssh program as a
    sequence of ``str`` (default :data:`SSH`); ``stdin_data`` is ``None`` or
    the bytes the remote program reads on its standard input.

    Raised before anything is started: :class:`TypeError` or
    :class:`ValueError` for a refused argument, ``timeout_s`` or destination,
    :class:`NotConfiguredError` for an unset destination, and
    :class:`hilclaw.local_run.ProgramNotFoundError` when ``ssh`` cannot be
    found. A non-zero status, a timeout or an ssh failure is a result.
    """
    _check_timeout(timeout_s)
    arguments = _check_arguments(arguments)
    if isinstance(ssh, (str, bytes)):
        raise TypeError("ssh must be a sequence of str, not one string")
    ssh = tuple(ssh)
    target = destination(environ)
    remote = " ".join(quote(argument) for argument in arguments)
    shown = (*ssh, *_OPTIONS, PLACEHOLDER, remote)
    done = local_run.run(
        (*ssh, *_OPTIONS, target, remote), timeout_s=timeout_s, stdin_data=stdin_data
    )
    failed = not done.timed_out and done.returncode == SSH_FAILURE
    return RemoteResult(
        returncode=None if failed else done.returncode,
        timed_out=done.timed_out,
        stdout=b"" if failed else done.stdout,
        stderr=b"" if failed else done.stderr,
        command=shown,
        duration_s=done.duration_s,
        ssh_failed=failed,
    )


def task_directory(task):
    """Return the remote directory of ``task``, ``hilclaw-driver/T-NNNN``, relative to the account's home.

    Raises :class:`TypeError` for a ``task`` that is no ``str`` and
    :class:`ValueError` for one not of the form ``T-NNNN``.
    """
    if not isinstance(task, str):
        raise TypeError(f"task must be str, not {type(task).__name__}")
    if not _TASK.fullmatch(task):
        raise ValueError(f"task must have the form T-NNNN: {task!r}")
    return f"{TASK_ROOT}/{task}"


def remote_path(task, relative):
    """Return the remote path of ``relative`` inside the directory of ``task``.

    ``relative`` is one or more components of letters, digits, ``.``, ``_``
    and ``-`` joined by ``/``, none of them ``.`` or ``..``; anything else
    (an absolute path, an empty component, a backslash) raises
    :class:`ValueError`, and a value that is no ``str`` :class:`TypeError`.
    """
    base = task_directory(task)
    if not isinstance(relative, str):
        raise TypeError(f"relative must be str, not {type(relative).__name__}")
    for component in relative.split("/"):
        if component in (".", "..") or not _COMPONENT.fullmatch(component):
            raise ValueError(
                f"path leaves the task directory or is refused: {relative!r}"
            )
    return f"{base}/{relative}"


def make_task_directory(task, *, timeout_s, environ=None, ssh=SSH):
    """Create the remote directory of ``task`` (``mkdir -p``) and return the :class:`RemoteResult`."""
    return run(
        ("mkdir", "-p", "--", task_directory(task)),
        timeout_s=timeout_s,
        environ=environ,
        ssh=ssh,
    )


def remove_task_directory(task, *, timeout_s, environ=None, ssh=SSH):
    """Remove the remote directory of ``task`` with ``rm -r`` and return the :class:`RemoteResult`."""
    return run(
        ("rm", "-r", "--", task_directory(task)),
        timeout_s=timeout_s,
        environ=environ,
        ssh=ssh,
    )


def put(local_path, task, relative, *, timeout_s, environ=None, ssh=SSH):
    """Copy the local file ``local_path`` to ``relative`` in the remote directory of ``task``.

    The remote path is checked before the file is read. The file's bytes are
    the standard input of ``sh -c 'cat > "$1"'``; the remote directory must
    exist. Returns the :class:`RemoteResult`; an :class:`OSError` reading the
    file is passed on.
    """
    target = remote_path(task, relative)
    with open(local_path, "rb") as source:
        data = source.read()
    return run(
        (*_WRITE, target),
        timeout_s=timeout_s,
        environ=environ,
        ssh=ssh,
        stdin_data=data,
    )


def get(task, relative, local_path, *, timeout_s, environ=None, ssh=SSH):
    """Copy ``relative`` in the remote directory of ``task`` to the local file ``local_path``.

    The remote file is read with ``cat``; ``local_path`` is written only when
    the remote status is 0. Returns the :class:`RemoteResult`, whose
    ``stdout`` holds the bytes read.
    """
    done = run(
        ("cat", "--", remote_path(task, relative)),
        timeout_s=timeout_s,
        environ=environ,
        ssh=ssh,
    )
    if done.returncode == 0:
        with open(local_path, "wb") as target:
            target.write(done.stdout)
    return done
