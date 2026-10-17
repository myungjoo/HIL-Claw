"""Local process runner for built stand-in artefacts (issue #5 A-7; Requirements FR-1 ``run``).

:func:`run` starts one local process from an argument list, waits for it up to
a required time limit and reports what happened: exit status, whether the limit
was reached, the raw bytes written to stdout and to stderr, the exact command
and the wall-clock time of the process. Where the platform has
:func:`os.wait4` (POSIX), the process is waited for through it and the
``ru_maxrss`` of the resource usage it returns is handed on as the operating
system reported it, unconverted and in the platform's unit, because ADR-0052
decision 4 takes the memory figure of a run from that usage; on native Windows
nothing is handed on.

Everything else is the caller's. The runner knows nothing about kernels and
decides no policy: it sets no environment variable, pins no CPU, sets no
priority and no resource limit, repeats nothing, computes no statistic and
interprets neither the output nor the exit status. It reads no configuration
and no environment variable of its own and writes no file.

The process is started without a shell, with no standard input.

Known limits. On a timeout only the process that was started is killed, not
that process's children. A survivor that keeps an output pipe open makes the
run count as timed out at the limit even where the started process ended, and
on native Windows can make the call last longer than the limit. The output is
held in memory without a size limit. The process is not sandboxed and its
environment is not scrubbed. On Windows the program lookup also searches the
current directory.
"""

import contextlib
import errno
import math
import os
import selectors
import shutil
import signal
import stat
import subprocess
import time
from typing import NamedTuple

_READ_SIZE = 32768
_ERROR_DIRECTORY = 267
_Selector = getattr(selectors, "PollSelector", selectors.SelectSelector)


class RunResult(NamedTuple):
    """Outcome of one :func:`run` call.

    ``returncode`` is the exit status of the process, negative when a signal
    ended it on POSIX, and ``None`` when the run timed out. ``stdout`` and
    ``stderr`` are what the process wrote, kept apart and not decoded; after a
    timeout they hold what was captured until the process was killed.
    ``command`` is the exact argument list that was run and ``duration_s`` the
    wall-clock time of the process in seconds as seen by the caller. Whether a
    non-zero ``returncode`` is a failure is the caller's judgement.

    ``max_rss`` is the ``ru_maxrss`` of the resource usage :func:`os.wait4`
    returned for the process, an ``int`` in the platform's unit that the
    runner does not convert, also for a run that failed, was killed by a signal
    or timed out; it is ``None`` where no usage was obtained (no
    :func:`os.wait4` on the platform, or the process was reaped by someone
    else). Whether the value is a figure is the caller's (ADR-0052 decision 4).
    """

    returncode: int | None
    timed_out: bool
    stdout: bytes
    stderr: bytes
    command: tuple[str, ...]
    duration_s: float
    max_rss: int | None = None


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
    that is not a number; :class:`ValueError` for an empty ``command``, an
    argument that contains a NUL character, on POSIX an argument that
    :func:`os.fsencode` cannot convert (the :class:`UnicodeEncodeError` it
    raises; on Windows such an argument is not refused) or a ``timeout_s``
    that is not positive and finite; and :class:`ProgramNotFoundError`, which
    includes a file that exists but is not executable.

    An ``env`` that is not ``None`` and has ``items`` is checked before the
    start, by the rules :mod:`subprocess` hands an environment over with, and
    refused with the class :mod:`subprocess` would raise: :class:`TypeError`
    for a key or a value of a type the platform cannot hand over (on Windows
    anything that is not ``str``; on POSIX anything :func:`os.fsencode`
    refuses, so ``str``, ``bytes`` and :class:`os.PathLike` pass), and
    :class:`ValueError` for a key with ``=`` after its first character or a
    NUL character in a key or a value. The check refuses nothing that one of
    the ways :mod:`subprocess` starts a process accepts: an empty key, a key
    whose only ``=`` is its first character and an ``env`` that is not a
    mapping are left to :mod:`subprocess`. ``env`` itself is handed on as
    given.

    A ``cwd`` that is not ``None`` is checked after ``env``, before the start,
    and refused with the class :mod:`subprocess` would raise for it: it is
    converted as :mod:`subprocess` converts it (:func:`os.fsencode` on POSIX,
    :func:`os.fsdecode` on Windows, so ``str``, ``bytes`` and
    :class:`os.PathLike` pass), which raises :class:`TypeError` for another
    type, and a NUL character in it is refused with :class:`ValueError`. It is
    then tested with :func:`os.stat`: a path that cannot be tested or is not a
    directory raises the :class:`OSError` a start in that ``cwd`` raises on
    the platform. On POSIX that is the error :func:`os.stat` raised, as the
    same object, or :class:`NotADirectoryError` for a path that is no
    directory; on native Windows it is :class:`NotADirectoryError` with
    ``winerror`` 267 in both cases, chained from the :func:`os.stat` error if
    there is one. Each such :class:`OSError` has ``cwd`` as its ``filename``
    (one :func:`os.stat` raised has the ``str`` or ``bytes`` of ``cwd``) and
    carries an attribute ``path_role`` with the value ``"cwd"``; read it as
    ``getattr(error, "path_role", None)``. ``cwd`` itself is handed on as
    given.

    What :mod:`subprocess` raises is passed on: an :class:`OSError` from
    starting the process (a file the system cannot execute, a ``cwd`` that
    was removed or changed after the test above or that the test passes but
    the start refuses, such as a directory without search permission), what
    it raises for an ``env`` the check above leaves to it, and an
    :class:`OverflowError` for a finite ``timeout_s`` longer than the platform
    can wait for (a bound that depends on the platform and can be a matter of
    weeks), which arrives after the process was started and killed. None of
    these, and no other error of :func:`run`, carries ``path_role``.

    Every :class:`TypeError` and :class:`ValueError` raised by the checks
    before the start, including one Python raises inside them, carries an
    attribute ``parameter`` naming the parameter of :func:`run` it is about:
    ``"timeout_s"`` for the time limit, ``"command"`` for the command, the
    program or an argument (including a NUL character in an argument and,
    on POSIX, an argument :func:`os.fsencode` cannot convert),
    ``"env"`` for the environment and ``"cwd"`` for the working directory.
    The time limit is checked first, then the command (so
    :class:`ProgramNotFoundError` comes before an ``env`` or ``cwd`` error),
    then ``env``, then ``cwd``. An error from anywhere else, including what
    :mod:`subprocess` raises, :class:`ProgramNotFoundError`, an
    :class:`OSError` of the program lookup and the :class:`OSError` of the
    ``cwd`` test, carries no ``parameter``; read it as
    ``getattr(error, "parameter", None)``.

    Where :func:`os.wait4` is used and it finds the process already reaped by
    someone else (for example with ``SIGCHLD`` ignored), the exit status is
    unknown and is reported as ``0``, as :mod:`subprocess` does, with
    ``max_rss`` ``None``.
    """
    with _parameter("timeout_s"):
        _check_timeout(timeout_s)
    with _parameter("command"):
        resolved = _resolve(command)
    with _parameter("env"):
        _check_env(env)
    _check_cwd(cwd)
    wait = _run_with_usage if hasattr(os, "wait4") else _run_without_usage
    started = time.monotonic()
    returncode, stdout, stderr, max_rss = wait(resolved, timeout_s, cwd, env)
    duration_s = time.monotonic() - started
    return RunResult(
        returncode=returncode,
        timed_out=returncode is None,
        stdout=stdout,
        stderr=stderr,
        command=resolved,
        duration_s=duration_s,
        max_rss=max_rss,
    )


def _run_without_usage(command, timeout_s, cwd, env):
    try:
        done = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            cwd=cwd,
            env=env,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as expired:
        return None, expired.stdout or b"", expired.stderr or b"", None
    return done.returncode, done.stdout, done.stderr, None


def _run_with_usage(command, timeout_s, cwd, env):
    with subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=env,
    ) as process:
        try:
            deadline = time.monotonic() + timeout_s
            stdout, stderr, drained = _drain(process, deadline)
            ended = _reap(process.pid, deadline) if drained else None
            timed_out = ended is None
            status, usage = _kill_and_reap(process.pid) if timed_out else ended
            process.returncode = os.waitstatus_to_exitcode(status)
        except BaseException:
            process.kill()
            raise
    max_rss = None if usage is None else usage.ru_maxrss
    return None if timed_out else process.returncode, stdout, stderr, max_rss


def _drain(process, deadline):
    chunks = {process.stdout: [], process.stderr: []}
    with _Selector() as selector:
        for pipe in chunks:
            selector.register(pipe, selectors.EVENT_READ)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            for key, _ in selector.select(remaining):
                data = os.read(key.fd, _READ_SIZE)
                if data:
                    chunks[key.fileobj].append(data)
                else:
                    selector.unregister(key.fileobj)
        drained = not selector.get_map()
    return b"".join(chunks[process.stdout]), b"".join(chunks[process.stderr]), drained


def _reap(pid, deadline):
    delay = 0.0005
    while True:
        try:
            reaped, status, usage = os.wait4(pid, os.WNOHANG)
        except ChildProcessError:
            return 0, None
        if reaped:
            return status, usage
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        delay = min(delay * 2, remaining, 0.05)
        time.sleep(delay)


def _kill_and_reap(pid):
    with contextlib.suppress(ProcessLookupError):
        os.kill(pid, signal.SIGKILL)
    try:
        _, status, usage = os.wait4(pid, 0)
    except ChildProcessError:
        return 0, None
    return status, usage


@contextlib.contextmanager
def _parameter(name):
    try:
        yield
    except (TypeError, ValueError) as error:
        error.parameter = name
        raise


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
        if os.name != "nt":
            os.fsencode(argument)
        if "\0" in argument:
            raise ValueError("an argument contains a NUL character")
    found = shutil.which(program)
    if found is None:
        raise ProgramNotFoundError(f"program not found or not executable: {program!r}")
    return (os.path.abspath(found), *arguments)


def _check_env(env):
    items = getattr(env, "items", None)
    if items is None:
        return
    for key, value in items():
        key, value = _env_text(key), _env_text(value)
        nul, equals = ("\0", "=") if isinstance(key, str) else (b"\0", b"=")
        if nul in key or nul in value:
            raise ValueError(f"an env key or value contains a NUL character: {key!r}")
        if equals in key[1:]:
            raise ValueError(
                f"an env key contains '=' after its first character: {key!r}"
            )


def _env_text(item):
    if os.name != "nt":
        return os.fsencode(item)
    if not isinstance(item, str):
        raise TypeError(f"env keys and values must be str, not {type(item).__name__}")
    return item


def _check_cwd(cwd):
    if cwd is None:
        return
    with _parameter("cwd"):
        path = os.fsdecode(cwd) if os.name == "nt" else os.fsencode(cwd)
        if ("\0" if isinstance(path, str) else b"\0") in path:
            raise ValueError("cwd contains a NUL character")
    try:
        try:
            is_directory = stat.S_ISDIR(os.stat(cwd).st_mode)
        except OSError as error:
            if os.name != "nt" or getattr(error, "winerror", None) == _ERROR_DIRECTORY:
                raise
            raise _not_a_directory(cwd) from error
        if not is_directory:
            raise _not_a_directory(cwd)
    except OSError as error:
        error.path_role = "cwd"
        raise


def _not_a_directory(cwd):
    winerror = (_ERROR_DIRECTORY,) if os.name == "nt" else ()
    return OSError(errno.ENOTDIR, os.strerror(errno.ENOTDIR), cwd, *winerror)
