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
temporary file. On a timeout only the compiler process itself is killed, not
processes it started.
"""

import math
import os
import secrets
import shutil
import subprocess
import time
from pathlib import Path
from typing import NamedTuple

DEFAULT_COMPILER = "clang"


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
    ``timeout_s`` that is not a positive finite number, an empty compiler
    prefix, or a flag that sets the output (any flag that starts with ``-o`` or
    ``--output``); :class:`TypeError` for arguments of
    the wrong type, including a bare ``str`` as flags; and
    :class:`CompilerNotFoundError`. An :class:`OSError` from starting the
    process or from moving the artefact into place is passed on.
    """
    _check_timeout(timeout_s)
    flags = _checked_flags(flags, "flags")
    trailing_flags = _checked_flags(trailing_flags, "trailing_flags")
    source_paths = _checked_sources(sources)
    target = Path(os.path.abspath(output))
    if not target.parent.is_dir():
        error = NotADirectoryError if target.parent.exists() else FileNotFoundError
        raise error(f"output directory is not an existing directory: {target.parent}")
    if target.is_dir():
        raise IsADirectoryError(f"output is a directory: {target}")
    prefix = _resolve(compiler)
    temporary = target.with_name(
        f"{target.stem}.tmp-{os.getpid()}-{secrets.token_hex(8)}{target.suffix}"
    )
    command = (*prefix, *flags, *source_paths, *trailing_flags, "-o", str(temporary))
    started = time.monotonic()
    try:
        try:
            done = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                env=env,
                timeout=timeout_s,
                check=False,
            )
            returncode, raw = done.returncode, done.stdout
        except subprocess.TimeoutExpired as expired:
            returncode, raw = None, expired.stdout or b""
        duration_s = time.monotonic() - started
        ok = returncode == 0 and temporary.is_file()
        if ok:
            os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return BuildResult(
        ok=ok,
        returncode=returncode,
        timed_out=returncode is None,
        output=Path(output),
        log=raw.decode("utf-8", errors="replace"),
        command=command,
        duration_s=duration_s,
    )


def compiler_version(compiler=None, *, timeout_s):
    """Return the first line that ``<compiler> --version`` writes to stdout, stripped.

    ``compiler`` and ``timeout_s`` are as in :func:`build`, with the same
    errors. Raises :class:`RuntimeError` when the command exits with a non-zero
    status, does not finish within ``timeout_s`` or prints no version line.
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


def _check_timeout(timeout_s):
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)):
        raise TypeError(f"timeout_s must be a number, not {type(timeout_s).__name__}")
    if not 0 < timeout_s < math.inf:
        raise ValueError(f"timeout_s must be positive and finite: {timeout_s!r}")


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
    return flags


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
        if not path.is_file():
            error = IsADirectoryError if path.is_dir() else FileNotFoundError
            raise error(f"source is not an existing regular file: {path}")
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
    found = shutil.which(prefix[0])
    if found is None:
        raise CompilerNotFoundError(f"compiler executable not found: {prefix[0]!r}")
    return (os.path.abspath(found), *prefix[1:])
