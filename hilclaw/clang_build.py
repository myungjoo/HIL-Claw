"""Build wrapper around clang for stand-in kernels (issue #5 A-7; Requirements FR-1 ``compile``).

:func:`build` turns C sources into one artefact with a single compiler process
and reports what the compiler said. It adds no flag of its own: optimisation
level, OpenMP, target and the kind of artefact (object, shared library,
executable) are the caller's ``flags``, and the time limit is a required
argument. The command is::

    <compiler...> <flags...> <sources...> <trailing_flags...> -o <temporary output>

The compiler is started without a shell, with no standard input. Sources and
the output are handed to it as absolute paths, so ``cwd`` does not change what
is compiled. The artefact is written under a temporary name next to ``output``
(same suffix) and moved into place with :func:`os.replace` only when the build
succeeded, so ``ok`` means that the file at ``output`` was produced by this
call; a failed build leaves a file that was already there untouched.

This module builds and never runs the artefact. It reads no configuration and
no environment variable of its own, and writes nothing but the artefact and its
temporary file. On a timeout only the process it started is killed, not that
process's children (the compiler behind a ``ccache`` prefix, a linker): a
survivor can still write the temporary file after the call has returned, and
where it keeps the output pipe open the call can last longer than the limit.
"""

import contextlib
import math
import os
import secrets
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import NamedTuple

DEFAULT_COMPILER = "clang"
_WINDOWS = sys.platform == "win32"
_MAX_TIMEOUT_S = (2**31 - 1) / 1000


class BuildResult(NamedTuple):
    """Outcome of one :func:`build` call.

    ``ok`` is true only when the compiler exited with 0 and the artefact is at
    ``output``. ``returncode`` is ``None`` when the build timed out. ``output``
    is the path as the caller gave it. ``log`` is everything the compiler wrote
    to stdout and stderr, decoded as UTF-8 with invalid bytes replaced.
    ``command`` is the exact argument list that was run and ``duration_s`` the
    wall-clock time of the compiler process in seconds.
    """

    ok: bool
    returncode: int | None
    timed_out: bool
    output: Path
    log: str
    command: tuple[str, ...]
    duration_s: float


class CompilerNotFoundError(LookupError):
    """The compiler executable could not be found; nothing was started."""


class _CopiedOSError(OSError):
    def __init__(self, error):
        super().__init__(*error.args)
        for name in ("errno", "strerror", "filename", "filename2"):
            if getattr(error, name) is not None:
                setattr(self, name, getattr(error, name))

    def _copy(self):
        error = OSError(*self.args)
        if self.filename is not None:
            error.filename, error.filename2 = self.filename, self.filename2
        return error


class _UnendedBuildError(_CopiedOSError):
    def __init__(self, error, removal_error=None):
        super().__init__(error)
        self.removal_error = removal_error

    def __reduce__(self):
        return type(self), (self._copy(),), self.__dict__


class CompilerNotStartedError(_UnendedBuildError):
    """Creating the compiler process failed; no compiler process exists.

    Raised by :func:`build` from the :class:`OSError` of creating the process,
    whose ``errno``, ``strerror``, ``filename`` and ``filename2`` it carries.
    It has no ``result``: there is no log. ``removal_error`` is the
    :class:`OSError` from removing the temporary file afterwards, or ``None``
    when that removal did not fail.
    """


class CompilerRunError(_UnendedBuildError):
    """Talking to the started compiler process, or timing it once ended, failed.

    Raised by :func:`build` from an :class:`OSError` raised after creating the
    compiler process returned, whose ``errno``, ``strerror``, ``filename`` and
    ``filename2`` it carries: before the process's return code was known, for
    example from reading its output or killing it, or, once the call had ended
    the process, from reading the clock for the build's duration. It has no
    ``result``. ``timed_out`` is true when the time limit had passed before the
    error: the error came from killing the compiler for its time limit, from
    reading or waiting for it after that kill, from closing the process
    afterwards, or from reading the clock after such a kill. It is false for an
    error from the first read, from killing the compiler after that read failed,
    or from closing the process or reading the clock after a read that ended.
    ``log`` is the output the call held when the error was raised, decoded as
    :attr:`BuildResult.log` is: after the time limit, the output read before it
    and anything read after the kill; after a read that ended, all of it. A
    failed read of the clock leaves ``log`` as the steps before it left it. It is
    ``None`` when the call held no output: after the first read failed, or when
    the time limit passed before any output was read and nothing was read after
    the kill. On Windows the output is read only after the kill, so a failed
    kill or a failed read after it leaves ``None``. ``None`` does not mean that
    the compiler wrote nothing. ``removal_error`` is the :class:`OSError` from
    removing the temporary file afterwards, or ``None`` when that removal did
    not fail. ``returncode`` is the return code of the compiler process when the
    error came from reading the clock after the process had ended by itself, the
    value :attr:`BuildResult.returncode` would have held: 0, a non-zero status,
    or a negative signal number on POSIX. It is ``None`` for every other source,
    including reading the clock after a kill for the time limit; ``None`` does
    not mean that the process did not end.
    """

    def __init__(
        self, error, removal_error=None, *, timed_out=False, log=None, returncode=None
    ):
        super().__init__(error, removal_error)
        self.timed_out = timed_out
        self.log = log
        self.returncode = returncode


class _EndedBuildError(_CopiedOSError):
    def __init__(self, error, result):
        super().__init__(error)
        self.result = result

    def __reduce__(self):
        return type(self), (self._copy(), self.result), self.__dict__


class ArtefactNotPlacedError(_EndedBuildError):
    """The compiler exited with 0 and left its output, but moving it to ``output`` failed.

    Raised by :func:`build` from the :class:`OSError` of :func:`os.replace`,
    whose ``errno``, ``strerror``, ``filename`` and ``filename2`` it carries.
    ``result`` is the :class:`BuildResult` of the ended compiler process, with
    ``ok`` false and the compiler's ``log``. ``removal_error`` is the
    :class:`OSError` from removing the temporary file afterwards, or ``None``
    when that removal did not fail.
    """

    def __init__(self, error, result, removal_error=None):
        super().__init__(error, result)
        self.removal_error = removal_error


class ArtefactNotCheckedError(_EndedBuildError):
    """The compiler exited with 0, but testing whether it left its output failed.

    Raised by :func:`build` from the :class:`OSError` of testing whether the
    temporary file exists and is a regular file, other than one that means it
    is absent, whose ``errno``, ``strerror``, ``filename`` and ``filename2`` it
    carries. Nothing is moved to ``output``. ``result`` is the
    :class:`BuildResult` of the ended compiler process, with ``ok`` false and
    the compiler's ``log``. ``removal_error`` is the :class:`OSError` from
    removing the temporary file afterwards, or ``None`` when that removal did
    not fail.
    """

    def __init__(self, error, result, removal_error=None):
        super().__init__(error, result)
        self.removal_error = removal_error


class TemporaryNotRemovedError(_EndedBuildError):
    """Removing the temporary file failed after the compiler process had ended.

    Raised by :func:`build` from the :class:`OSError` of that removal, whose
    ``errno``, ``strerror``, ``filename`` and ``filename2`` it carries, when
    neither :class:`ArtefactNotPlacedError` nor :class:`ArtefactNotCheckedError`
    is raised. ``result`` is the :class:`BuildResult` the call would otherwise
    have returned, ``ok`` included.
    """


def build(
    sources,
    output,
    *,
    timeout_s,
    flags=(),
    trailing_flags=(),
    compiler=None,
    cwd=None,
    env=None,
):
    """Compile ``sources`` into the file ``output`` and return a :class:`BuildResult`.

    ``sources`` is one path or a non-empty sequence of paths (``str`` or
    :class:`os.PathLike`) of existing regular files. ``output`` is the artefact
    path; its directory must exist. ``flags`` go before the sources and
    ``trailing_flags`` after them (libraries such as ``-lm``, whose position
    matters to the linker); both are sequences of ``str`` passed through in
    order. ``compiler`` is ``None`` for ``clang`` on ``PATH``, the name or path
    of another executable, or a sequence of ``str`` used as a command prefix
    such as ``("ccache", "clang")``. ``cwd`` and ``env`` are handed to the
    process unchanged (``None`` inherits). ``timeout_s`` is the limit in seconds
    for the compiler process.

    A compile failure or a timeout is a result (``ok`` false), not an exception.
    Raised before anything is started: :class:`FileNotFoundError`,
    :class:`IsADirectoryError` or :class:`NotADirectoryError` for a source or
    output path that cannot be used; :class:`ValueError` for no source, a
    ``timeout_s`` that is not a positive finite number or is longer than
    (2**31 - 1) / 1000 seconds, about 24.8 days, an empty compiler prefix, a
    flag that sets the output (any flag that starts with ``-o`` or
    ``--output``, which includes unrelated options with that prefix such as
    ``-objcmt-*``), or a NUL character in a flag or in a part of the compiler
    prefix after the first; :class:`TypeError` for arguments of the wrong type,
    including a bare ``str`` as flags; and :class:`CompilerNotFoundError`. On
    POSIX, each such flag or part must also convert with :func:`os.fsencode`,
    else the :class:`UnicodeEncodeError` it raises is passed on. These two
    checks give the class :mod:`subprocess` would raise for the same single
    defect; the first part of the prefix is left to the lookup, and the
    flags and parts are handed on unchanged. Once the output path has
    passed its tests, its absolute path is checked the same way: on POSIX it
    must convert with :func:`os.fsencode`, else its :class:`UnicodeEncodeError`
    is passed on, and a NUL character in it raises :class:`ValueError`.
    After the compiler is found, and still before anything is started, ``env``
    and ``cwd`` are checked as :mod:`subprocess` would refuse them, with the
    class it would raise for the same single defect, with one exception: an
    ``env`` that is not ``None`` and has no ``items`` method is refused with
    :class:`TypeError`, as :mod:`subprocess` has no single class for it (the
    class differs by platform and start path). When ``env`` has an ``items``
    method, each key and value must convert as on the platform
    (:func:`os.fsencode` on POSIX, ``str`` only on Windows; else
    :class:`TypeError`), and :class:`ValueError` is raised for a NUL character
    in either or a ``=`` after the first character of a key, with a message
    that may name the key but never the value. A ``cwd`` that is not ``None``
    must convert as on the platform (:func:`os.fsdecode` on Windows,
    :func:`os.fsencode` on POSIX; else :class:`TypeError`, or a
    :class:`ValueError` such as :class:`UnicodeEncodeError`), and
    :class:`ValueError` is raised for a NUL character in it. Whether ``cwd``
    exists is not tested here: a missing one fails the start, as
    :class:`CompilerNotStartedError` below. Any
    :class:`TypeError` or :class:`ValueError` (including a subclass such as
    :class:`UnicodeEncodeError`) from the checks of ``timeout_s``, ``flags``,
    ``trailing_flags``, ``sources``, ``output``, ``compiler``, ``env`` and
    ``cwd``, including the one for no source and one that Python or the code
    of a handed object raises inside a check, such as for a value that cannot
    be iterated or a path object whose ``__fspath__`` fails, is raised with
    the attribute ``parameter`` set to the name of that parameter:
    ``"timeout_s"``, ``"flags"``, ``"trailing_flags"``, ``"sources"``,
    ``"output"``, ``"compiler"``, ``"env"`` or ``"cwd"``. The check of
    ``output`` forms its absolute path and, after the tests of that path
    below, which are not part of it, checks it on POSIX with
    :func:`os.fsencode` and then for a NUL character; after the check of
    ``cwd``, forming the temporary name beside that path is part of it too.
    A :class:`TypeError` or :class:`ValueError` from anywhere else, such as
    binding the call or creating the compiler process, carries no
    ``parameter``. Any
    :class:`OSError` from testing a source path or the output path, including one
    that the test itself raises such as a :class:`PermissionError`, is raised with
    the attribute ``path_role`` set to ``"source"`` or ``"output"``; an
    :class:`OSError` from anywhere else, such as forming the absolute path from the
    working directory, carries no ``path_role``. An
    :class:`OSError` from creating the compiler process is raised as
    :class:`CompilerNotStartedError`, an :class:`OSError` subclass without
    ``result``; when removing the temporary file then fails too, the removal's
    error is its ``removal_error``. Any other :class:`OSError` raised while the
    process runs, or from reading the clock for the build's duration once the
    process has ended, is raised as :class:`CompilerRunError`, an :class:`OSError`
    subclass without ``result`` whose ``timed_out`` says whether the time limit
    had passed before the error, whose ``log`` is the output read so far, or
    ``None`` when none was held, and whose ``returncode`` is the compiler's
    return code when the clock failed after the compiler ended by itself, and
    ``None`` otherwise; when removing the temporary file then fails too, the
    removal's error is its ``removal_error``. Once the compiler process has
    ended, an :class:`OSError` from moving the artefact into place is raised
    as :class:`ArtefactNotPlacedError`, and one from removing the temporary file
    as :class:`TemporaryNotRemovedError`; both are :class:`OSError` subclasses
    whose ``result`` holds the :class:`BuildResult` with the compiler's log.
    When both fail, :class:`ArtefactNotPlacedError` is raised and the removal's
    error is its ``removal_error``. After the compiler exited with 0, only a
    :class:`FileNotFoundError` or :class:`NotADirectoryError` from testing
    whether the temporary file exists reads as no artefact; any other
    :class:`OSError` of that test is raised as :class:`ArtefactNotCheckedError`,
    an :class:`OSError` subclass whose ``result`` holds the :class:`BuildResult`
    with the compiler's log, and nothing is moved. When removing the temporary
    file then fails too, :class:`ArtefactNotCheckedError` is raised and the
    removal's error is its ``removal_error``. An exception that is not an
    :class:`OSError` and leaves the build early, such as
    :class:`KeyboardInterrupt`, is passed on unchanged; when removing the
    temporary file then fails, the removal's error is not raised but added to
    that exception as a note naming the temporary path.
    """
    with _parameter("timeout_s"):
        _check_timeout(timeout_s)
    with _parameter("flags"):
        flags = _checked_flags(flags, "flags")
    with _parameter("trailing_flags"):
        trailing_flags = _checked_flags(trailing_flags, "trailing_flags")
    with _parameter("sources"):
        source_paths = _checked_sources(sources)
    with _parameter("output"):
        target = Path(os.path.abspath(output))
    try:
        if not target.parent.is_dir():
            error = NotADirectoryError if target.parent.exists() else FileNotFoundError
            raise error(
                f"output directory is not an existing directory: {target.parent}"
            )
        if target.is_dir():
            raise IsADirectoryError(f"output is a directory: {target}")
    except OSError as raised:
        raised.path_role = "output"
        raise
    with _parameter("output"):
        _check_argument(str(target), "output contains a NUL character")
    with _parameter("compiler"):
        prefix = _resolve(compiler)
    with _parameter("env"):
        _check_env(env)
    with _parameter("cwd"):
        _check_cwd(cwd)
    token = f"{os.getpid()}-{secrets.token_hex(8)}"
    with _parameter("output"):
        temporary = target.with_name(f"{target.stem}.tmp-{token}{target.suffix}")
    command = (*prefix, *flags, *source_paths, *trailing_flags, "-o", str(temporary))
    start_error = run_error = check_error = move_error = removal_error = None
    escaping = None
    started = time.monotonic()
    try:
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                env=env,
            )
        except OSError as error:
            start_error = error
        else:
            held = _Held()
            returncode = None
            try:
                returncode, raw = _communicate(process, timeout_s, held)
                duration_s = time.monotonic() - started
            except OSError as error:
                run_error = error
            else:
                ok = False
                if returncode == 0:
                    try:
                        ok = stat.S_ISREG(os.stat(temporary).st_mode)
                    except (FileNotFoundError, NotADirectoryError):
                        pass
                    except OSError as error:
                        check_error = error
                if ok:
                    try:
                        os.replace(temporary, target)
                    except OSError as error:
                        ok, move_error = False, error
    except BaseException as error:
        escaping = error
        raise
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError as error:
            if escaping is None:
                removal_error = error
            else:
                escaping.add_note(f"removing {temporary} failed: {error!r}")
    if start_error is not None:
        raise CompilerNotStartedError(start_error, removal_error) from start_error
    if run_error is not None:
        raise CompilerRunError(
            run_error,
            removal_error,
            timed_out=held.timed_out,
            log=held.decoded(),
            returncode=returncode,
        ) from run_error
    result = BuildResult(
        ok=ok,
        returncode=returncode,
        timed_out=returncode is None,
        output=Path(output),
        log=raw.decode("utf-8", errors="replace"),
        command=command,
        duration_s=duration_s,
    )
    if check_error is not None:
        raise ArtefactNotCheckedError(
            check_error, result, removal_error
        ) from check_error
    if move_error is not None:
        raise ArtefactNotPlacedError(move_error, result, removal_error) from move_error
    if removal_error is not None:
        raise TemporaryNotRemovedError(removal_error, result) from removal_error
    return result


def compiler_version(compiler=None, *, timeout_s):
    """Return the first line that ``<compiler> --version`` writes to stdout, stripped.

    ``compiler`` and ``timeout_s`` are as in :func:`build`, with the same
    errors, except that they carry no ``parameter``. Raises
    :class:`RuntimeError` when the command exits with a non-zero status, does
    not finish within ``timeout_s`` or prints no version line.
    """
    _check_timeout(timeout_s)
    command = (*_resolve(compiler), "--version")
    try:
        done = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as expired:
        raise RuntimeError(
            f"{command} did not finish within {timeout_s} s"
        ) from expired
    if done.returncode != 0:
        detail = done.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"{command} exited with {done.returncode}: {detail}")
    lines = done.stdout.decode("utf-8", errors="replace").splitlines()
    if not lines or not lines[0].strip():
        raise RuntimeError(f"{command} printed no version line")
    return lines[0].strip()


class _Held:
    def __init__(self):
        self.timed_out = False
        self.raw = None

    def decoded(self):
        return None if self.raw is None else self.raw.decode("utf-8", errors="replace")


def _communicate(process, timeout_s, held):
    with process:
        try:
            held.raw, _ = process.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired as expired:
            held.timed_out, held.raw = True, expired.output
            process.kill()
            if _WINDOWS:
                held.raw, _ = process.communicate()
            else:
                process.wait()
            return None, held.raw or b""
        except BaseException:
            process.kill()
            raise
        return process.poll(), held.raw


@contextlib.contextmanager
def _parameter(name):
    try:
        yield
    except (TypeError, ValueError) as error:
        error.parameter = name
        raise


def _check_env(env):
    if env is None:
        return
    items = getattr(env, "items", None)
    if items is None:
        raise TypeError(
            f"env must be None or have an items method, not {type(env).__name__}"
        )
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
    if not _WINDOWS:
        return os.fsencode(item)
    if not isinstance(item, str):
        raise TypeError(f"env keys and values must be str, not {type(item).__name__}")
    return item


def _check_cwd(cwd):
    if cwd is None:
        return
    path = os.fsdecode(cwd) if _WINDOWS else os.fsencode(cwd)
    if ("\0" if isinstance(path, str) else b"\0") in path:
        raise ValueError("cwd contains a NUL character")


def _check_timeout(timeout_s):
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)):
        raise TypeError(f"timeout_s must be a number, not {type(timeout_s).__name__}")
    if not 0 < timeout_s < math.inf:
        try:
            shown = f": {timeout_s!r}"
        except ValueError:
            shown = ""
        raise ValueError(f"timeout_s must be positive and finite{shown}")
    if timeout_s > _MAX_TIMEOUT_S:
        raise ValueError(f"timeout_s must be at most {_MAX_TIMEOUT_S} s")


def _checked_flags(flags, name):
    if isinstance(flags, (str, bytes)):
        raise TypeError(
            f"{name} must be a sequence of str, not one {type(flags).__name__}"
        )
    flags = tuple(flags)
    for flag in flags:
        if not isinstance(flag, str):
            raise TypeError(f"{name} must contain only str, not {type(flag).__name__}")
        if flag.startswith(("-o", "--output")):
            raise ValueError(f"{name} must not set the output: {flag!r}")
        _check_argument(flag, f"{name} contains a NUL character")
    return flags


def _check_argument(argument, message):
    if not _WINDOWS:
        os.fsencode(argument)
    if "\0" in argument:
        raise ValueError(message)


def _checked_sources(sources):
    if isinstance(sources, (str, os.PathLike)):
        sources = [sources]
    paths = []
    for source in sources:
        if not isinstance(source, (str, os.PathLike)):
            raise TypeError(
                f"a source must be str or os.PathLike, not {type(source).__name__}"
            )
        path = Path(os.path.abspath(source))
        try:
            if not path.is_file():
                error = IsADirectoryError if path.is_dir() else FileNotFoundError
                raise error(f"source is not an existing regular file: {path}")
        except OSError as raised:
            raised.path_role = "source"
            raise
        paths.append(str(path))
    if not paths:
        raise ValueError("no source file given")
    return paths


def _resolve(compiler):
    if compiler is None:
        prefix = (DEFAULT_COMPILER,)
    elif isinstance(compiler, (str, os.PathLike)):
        prefix = (os.fspath(compiler),)
    else:
        prefix = tuple(compiler)
    if not prefix:
        raise ValueError("compiler command prefix is empty")
    for part in prefix:
        if not isinstance(part, str):
            raise TypeError(f"compiler must be given as str, not {type(part).__name__}")
    for part in prefix[1:]:
        _check_argument(
            part, "a compiler part after the first contains a NUL character"
        )
    found = shutil.which(prefix[0])
    if found is None:
        raise CompilerNotFoundError(f"compiler executable not found: {prefix[0]!r}")
    return (os.path.abspath(found), *prefix[1:])
