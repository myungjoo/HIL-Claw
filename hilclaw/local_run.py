"""Local process runner for built stand-in artefacts (issue #5 A-7; Requirements FR-1 ``run``).

:func:`run` starts one local process from an argument list, waits for it up to
a required time limit and reports what happened: exit status, whether the limit
was reached, the raw bytes written to stdout and to stderr, the exact command
and the wall-clock time of the process.

Everything else is the caller's. The runner knows nothing about kernels and
decides no policy: it sets no environment variable, pins no CPU, sets no
priority and no resource limit, repeats nothing, computes no statistic and
interprets neither the output nor the exit status. It reads no configuration
and no environment variable of its own and writes no file.

The process is started without a shell, with no standard input.

Known limits. On a timeout only the process that was started is killed, not
that process's children: a survivor that keeps an output pipe open can make the
call last longer than the limit. The output is held in memory without a size
limit. The process is not sandboxed and its environment is not scrubbed. On
Windows the program lookup also searches the current directory.
"""

import math
import os
import shutil
import subprocess
import time
from typing import NamedTuple


class RunResult(NamedTuple):
    """Outcome of one :func:`run` call.

    ``returncode`` is the exit status of the process, negative when a signal
    ended it on POSIX, and ``None`` when the run timed out. ``stdout`` and
    ``stderr`` are what the process wrote, kept apart and not decoded; after a
    timeout they hold what was captured until the process was killed.
    ``command`` is the exact argument list that was run and ``duration_s`` the
    wall-clock time of the process in seconds as seen by the caller. Whether a
    non-zero ``returncode`` is a failure is the caller's judgement.
    """

    returncode: int | None
    timed_out: bool
    stdout: bytes
    stderr: bytes
    command: tuple[str, ...]
    duration_s: float


class ProgramNotFoundError(LookupError):
    """The program to run could not be found; nothing was started."""


def run(command, *, timeout_s, cwd=None, env=None):
    """Run ``command`` as one local process and return a :class:`RunResult`.

    ``command`` is a non-empty sequence: the program (``str`` or
    :class:`os.PathLike`) followed by ``str`` arguments passed through in
    order. The program is looked up with :func:`shutil.which` on the ``PATH``
    of the calling process and made absolute, so a relative program path is
    resolved against the working directory of the calling process, not against
    ``cwd``. ``cwd`` and ``env`` are handed to the process unchanged (``None``
    inherits). ``timeout_s`` is the limit in seconds; when it is reached the
    process is killed.

    A non-zero exit, a signal or a timeout is a result, not an exception.
    Raised before anything is started: :class:`TypeError` for a ``command``
    that is one ``str`` or ``bytes``, a program that is not ``str`` or
    :class:`os.PathLike`, an argument that is not ``str`` or a ``timeout_s``
    that is not a number; :class:`ValueError` for an empty ``command`` or a
    ``timeout_s`` that is not positive and finite; and
    :class:`ProgramNotFoundError`, which includes a file that exists but is not
    executable. An :class:`OSError` from starting the process (a file the
    system cannot execute, a ``cwd`` that does not exist) is passed on.
    """
    _check_timeout(timeout_s)
    resolved = _resolve(command)
    started = time.monotonic()
    try:
        done = subprocess.run(
            resolved,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            cwd=cwd,
            env=env,
            timeout=timeout_s,
            check=False,
        )
        returncode, stdout, stderr = done.returncode, done.stdout, done.stderr
    except subprocess.TimeoutExpired as expired:
        returncode = None
        stdout, stderr = expired.stdout or b"", expired.stderr or b""
    duration_s = time.monotonic() - started
    return RunResult(
        returncode=returncode,
        timed_out=returncode is None,
        stdout=stdout,
        stderr=stderr,
        command=resolved,
        duration_s=duration_s,
    )


def _check_timeout(timeout_s):
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)):
        raise TypeError(f"timeout_s must be a number, not {type(timeout_s).__name__}")
    if not 0 < timeout_s < math.inf:
        raise ValueError(f"timeout_s must be positive and finite: {timeout_s!r}")


def _resolve(command):
    if isinstance(command, (str, bytes)):
        raise TypeError(
            f"command must be a sequence of arguments, not one {type(command).__name__}"
        )
    command = tuple(command)
    if not command:
        raise ValueError("command is empty")
    program, *arguments = command
    if not isinstance(program, (str, os.PathLike)):
        raise TypeError(
            f"the program must be str or os.PathLike, not {type(program).__name__}"
        )
    program = os.fspath(program)
    if not isinstance(program, str):
        raise TypeError("the program path must be str, not bytes")
    for argument in arguments:
        if not isinstance(argument, str):
            raise TypeError(f"an argument must be str, not {type(argument).__name__}")
    found = shutil.which(program)
    if found is None:
        raise ProgramNotFoundError(f"program not found or not executable: {program!r}")
    return (os.path.abspath(found), *arguments)
