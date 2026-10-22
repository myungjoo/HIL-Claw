"""The start and end of one ``cpu_standin`` build or process container (ADR-0144 slice (1)).

``ARCHITECTURE/decisions/ADR-0144-od14-first-case-build-run-container.md``
decides that each build and each process of a first-case run (decision 1: the
verification build and process of ``correctness.check``, the timing build and
process of ``sim.run`` and ``board.run``) runs in a new Docker container, and
names four code slices. :func:`run_in_container` is slice (1): it starts one
container for one build or one process through the container runtime's
command-line program, waits for it and hands back what the program reported.
It is bound to no tool and no backend operation; nothing calls it yet.

The one program it starts is the client (default ``docker``), through
:func:`hilclaw.local_run.run` looked up at call time, with the properties of
ADR-0144 decision 6 as Docker options (E2 to E6, E11, E12). The build
directory is the one writable mount, given with ``--mount type=bind``, which
unlike ``-v`` does not create a missing source, at :data:`CONTAINER_BUILD_DIR`;
``--entrypoint=`` empties the image's entrypoint so that the program after the
image is the one started. No variable, other host path, privilege or resource
bound is given. At the time limit the container is removed by its name, by
force (``rm --force``, E5).

What this module does not decide: what a tool answers where no container
runtime, no image or no container can be had (ADR-0144 decision 7, OD-18
sub-questions 18 and 19), so each such situation reaches the caller as a plain
fact (an exception passed on, a status, a removal result); how the client's
statuses 125 to 127 are read (decision 3), which are handed back like any
other; the memory figure inside a container (OD-14 1 (ma)), so no resource
usage is handed on; the leftovers of ADR-0144 Boundaries, among them a
container created after the client was ended at the limit, so whether the
forced removal found a container is not judged; and whether the start fixes
the daemon the client reaches (OD-14 1 (ra)), so no option chooses a daemon.
The time limits are the caller's. The module reads no environment variable and
no configuration of its own, names no image and writes no file.
"""

import contextlib
import errno
import math
import os
import secrets
import stat
from typing import NamedTuple

from hilclaw import local_run

CONTAINER_BUILD_DIR = "/build"
NAME_PREFIX = "hilclaw-standin-"
_MOUNT_UNSAFE = (",", '"', "\n", "\r", "\0")


class Removal(NamedTuple):
    """The forced removal's client run: a :class:`hilclaw.local_run.RunResult`
    without ``max_rss``, uninterpreted (a removal that found no container is
    not told apart)."""

    returncode: int | None
    timed_out: bool
    stdout: bytes
    stderr: bytes
    command: tuple[str, ...]
    duration_s: float


class ContainerResult(NamedTuple):
    """Outcome of one :func:`run_in_container` call, uninterpreted.

    The first six fields are the client run's (``returncode`` ``None`` on a
    timeout; 125 to 127 handed back like any status), without ``max_rss``.
    ``name`` is :data:`NAME_PREFIX` and 32 hexadecimal digits of
    :func:`secrets.token_hex`; ``removal`` is ``None`` after a normal end.
    """

    returncode: int | None
    timed_out: bool
    stdout: bytes
    stderr: bytes
    command: tuple[str, ...]
    duration_s: float
    name: str
    removal: Removal | None


class NoNumericUserError(RuntimeError):
    """The platform has no ``os.getuid`` or ``os.getgid``; nothing was started."""


def run_in_container(
    image,
    build_dir,
    program,
    arguments=(),
    *,
    timeout_s,
    removal_timeout_s,
    client="docker",
):
    """Run ``program`` with ``arguments`` in one new container of ``image``.

    ``image`` is the image reference, handed to the client as given.
    ``build_dir`` is the absolute host path of an existing directory, bind
    mounted writable at :data:`CONTAINER_BUILD_DIR`, the working directory
    inside. ``program`` is started inside in place of the image's entrypoint,
    with ``arguments`` (a sequence of ``str``) in order. ``timeout_s`` is the
    time limit of the client run and ``removal_timeout_s`` that of the forced
    removal after a timeout; neither has a default. ``client`` is the
    container runtime's command-line program, looked up by
    :func:`hilclaw.local_run.run` on ``PATH``.

    The client runs with the environment of the calling process. After a
    normal end, whatever the status, the client removed the container
    (``--rm``) and nothing else is started. After a timeout exactly one
    ``<client> rm --force <name>`` is run through
    :func:`hilclaw.local_run.run` with ``removal_timeout_s``; its outcome is
    :attr:`ContainerResult.removal`, and an exception of its start is passed
    on.

    Raised before anything is started, each :class:`TypeError` and
    :class:`ValueError` with an attribute ``parameter`` naming the argument:
    an ``image`` that is not ``str``, is empty, begins with ``-`` (the client
    would read it as an option) or holds whitespace or NUL; a ``build_dir``
    that is not ``str`` or a ``str`` :class:`os.PathLike`, is not absolute or
    holds ``,``, ``"``, a newline, a carriage return or NUL (the mount option
    could not carry it); a ``program`` or ``client`` that is not ``str``, is
    empty or holds NUL; ``arguments`` that are one ``str`` or ``bytes`` or
    hold an item that is not ``str`` or holds NUL; a ``timeout_s`` or
    ``removal_timeout_s`` that is not a number or not positive and finite.
    Then :class:`NoNumericUserError` where the platform has no ``os.getuid``
    or ``os.getgid``: a precondition of this function for the POSIX machines
    of C-7 1, not an answer of any tool. Then the :class:`OSError` of
    :func:`os.stat` on ``build_dir``, or :class:`NotADirectoryError`.

    :class:`hilclaw.local_run.ProgramNotFoundError` (no client on ``PATH``),
    an :class:`OSError` of the client's start and the other
    :class:`TypeError` or :class:`ValueError` :func:`hilclaw.local_run.run`
    raises before its start are passed on unchanged with no removal. Any
    other exception of the client run (for example :class:`OverflowError`
    for a limit the platform cannot wait for, or :class:`KeyboardInterrupt`)
    may leave the container running, so before it is passed on one forced
    removal is run as after a timeout, and the exception gets the attributes
    ``container_name`` and ``removal`` (the :class:`Removal`, or ``None``
    with a note added when the removal raised an :class:`OSError`,
    :class:`LookupError` or :class:`ArithmeticError`). What a tool answers
    for any of these, for a status of 125 to 127 or for a failed removal is
    ADR-0144 decision 7's open question.
    """
    source, arguments = _check(
        image, build_dir, program, arguments, timeout_s, removal_timeout_s, client
    )
    user = _numeric_user()
    _check_directory(source)
    name = NAME_PREFIX + secrets.token_hex(16)
    command = [
        client,
        "run",
        "--rm",
        "--name",
        name,
        "--mount",
        f"type=bind,source={source},target={CONTAINER_BUILD_DIR}",
        "--workdir",
        CONTAINER_BUILD_DIR,
        "--network",
        "none",
        "--pull",
        "never",
        "--user",
        user,
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges=true",
        "--entrypoint=",
        image,
        program,
        *arguments,
    ]
    try:
        ran = local_run.run(command, timeout_s=timeout_s, env=None)
    except (local_run.ProgramNotFoundError, OSError, TypeError, ValueError):
        raise
    except BaseException as error:
        error.container_name = name
        error.removal = None
        try:
            error.removal = _remove(client, name, removal_timeout_s)
        except (OSError, LookupError, ArithmeticError) as failed:
            error.add_note(f"the forced removal of {name} raised {failed!r}")
        raise
    removal = _remove(client, name, removal_timeout_s) if ran.timed_out else None
    return ContainerResult(
        returncode=ran.returncode,
        timed_out=ran.timed_out,
        stdout=ran.stdout,
        stderr=ran.stderr,
        command=ran.command,
        duration_s=ran.duration_s,
        name=name,
        removal=removal,
    )


def _remove(client, name, removal_timeout_s):
    removed = local_run.run(
        [client, "rm", "--force", name], timeout_s=removal_timeout_s, env=None
    )
    return Removal(
        returncode=removed.returncode,
        timed_out=removed.timed_out,
        stdout=removed.stdout,
        stderr=removed.stderr,
        command=removed.command,
        duration_s=removed.duration_s,
    )


def _check(image, build_dir, program, arguments, timeout_s, removal_timeout_s, client):
    with _parameter("image"):
        _check_image(image)
    with _parameter("build_dir"):
        source = _check_build_dir(build_dir)
    with _parameter("program"):
        _check_text(program, "program")
    with _parameter("arguments"):
        arguments = _check_arguments(arguments)
    with _parameter("timeout_s"):
        _check_limit(timeout_s, "timeout_s")
    with _parameter("removal_timeout_s"):
        _check_limit(removal_timeout_s, "removal_timeout_s")
    with _parameter("client"):
        _check_text(client, "client")
    return source, arguments


@contextlib.contextmanager
def _parameter(name):
    try:
        yield
    except (TypeError, ValueError) as error:
        error.parameter = name
        raise


def _check_image(image):
    if not isinstance(image, str):
        raise TypeError(f"image must be str, not {type(image).__name__}")
    if not image:
        raise ValueError("image is empty")
    if image.startswith("-"):
        raise ValueError(f"image must not begin with '-': {image!r}")
    if "\0" in image or any(character.isspace() for character in image):
        raise ValueError(f"image contains whitespace or a NUL character: {image!r}")


def _check_build_dir(build_dir):
    if not isinstance(build_dir, (str, os.PathLike)):
        raise TypeError(
            f"build_dir must be str or os.PathLike, not {type(build_dir).__name__}"
        )
    source = os.fspath(build_dir)
    if not isinstance(source, str):
        raise TypeError("build_dir must be a str path, not bytes")
    if any(character in source for character in _MOUNT_UNSAFE):
        raise ValueError(
            f"build_dir contains a character a mount cannot carry: {source!r}"
        )
    if not os.path.isabs(source):
        raise ValueError(f"build_dir must be absolute: {source!r}")
    return source


def _check_text(value, what):
    if not isinstance(value, str):
        raise TypeError(f"{what} must be str, not {type(value).__name__}")
    if not value:
        raise ValueError(f"{what} is empty")
    if "\0" in value:
        raise ValueError(f"{what} contains a NUL character")


def _check_arguments(arguments):
    if isinstance(arguments, (str, bytes)):
        raise TypeError(
            f"arguments must be a sequence, not one {type(arguments).__name__}"
        )
    arguments = tuple(arguments)
    for argument in arguments:
        if not isinstance(argument, str):
            raise TypeError(f"an argument must be str, not {type(argument).__name__}")
        if "\0" in argument:
            raise ValueError("an argument contains a NUL character")
    return arguments


def _check_limit(value, what):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{what} must be a number, not {type(value).__name__}")
    if not 0 < value < math.inf:
        raise ValueError(f"{what} must be positive and finite: {value!r}")


def _numeric_user():
    getuid = getattr(os, "getuid", None)
    getgid = getattr(os, "getgid", None)
    if getuid is None or getgid is None:
        raise NoNumericUserError(
            "this platform has no os.getuid or os.getgid; a POSIX host is required"
        )
    return f"{getuid()}:{getgid()}"


def _check_directory(source):
    if not stat.S_ISDIR(os.stat(source).st_mode):
        raise NotADirectoryError(errno.ENOTDIR, os.strerror(errno.ENOTDIR), source)
