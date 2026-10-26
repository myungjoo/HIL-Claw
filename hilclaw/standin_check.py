"""The ``cpu_standin`` operation of ``correctness.check`` in two containers (ADR-0144 slice (4), first part; ADR-0169).

``ARCHITECTURE/decisions/ADR-0169-od18-standin-build-log-and-removal.md``
decides what the compiler's log of a build container is, which build
containers have one, and the time limit of a forced removal; a decision cited
by its number alone is one of that record. :func:`operation` is the operation
of ``correctness.check`` at a run of ADR-0144 decision 1, called as
:func:`hilclaw.check_operation.ask` calls an operation, with five positional
things: the request, the hw_profile, the check parameters, the output path
and the log keeper. In the order of ADR-0056 decision 7 and the Walk-through
of ADR-0168 it:

1. checks its own arguments and computes the process's arguments
   (ADR-0017 decision 2) and time limit
   (:func:`hilclaw.standin_settings.verification_process_time_limit_s`);
2. reads the image (:func:`hilclaw.standin_image.read_image`; C1, C2);
3. makes the build directory of the call (ADR-0056 decision 4; ADR-0096
   decision 3; S3);
4. copies the kernel files and :data:`hilclaw.harness.verification_build.PROGRAM_SOURCE`
   into it (:func:`hilclaw.standin_copies.place_copies`; C12, C13, C15);
5. runs the verification build in one container (ADR-0144 decision 3):
   :data:`COMPILER` with :data:`hilclaw.standin_settings.FLAGS`, the program
   source first and the kernel's compiled set in the reader's order, the
   trailing flags and ``-o`` the executable :data:`EXECUTABLE_NAME` in
   :data:`hilclaw.standin_container.CONTAINER_BUILD_DIR`, within
   :data:`hilclaw.standin_settings.BUILD_TIME_LIMIT_S`; hands the keeper the
   log where decision 3 says so (decision 2: the client's standard output,
   then its standard error, each decoded as UTF-8 with invalid bytes
   replaced, nothing between them); reads the result with
   :func:`hilclaw.standin_answer.read_build`; answers a status 0 that left no
   regular file at the executable's path ``build_output_missing`` (S9, C7);
6. runs the executable in a second container with ``m k n draws seed``, reads
   it with :func:`hilclaw.standin_answer.read_process`, and returns its
   standard output, as ``bytes``, after status 0 (ADR-0017 decision 7);
7. removes the build directory before it returns or raises, where
   :func:`hilclaw.standin_answer.build_dir_removable` allows it after every
   container of the call (ADR-0168 decision 5).

Every :class:`hilclaw.standin_answer.Failure` is raised as
:class:`hilclaw.tools.ToolFailure` with its kind and message, a value of
``condition`` is returned as its string, and what a step raises is placed by
:func:`hilclaw.standin_answer.place_error`; what no row places (C14, C16) and
every request to end (C18) passes as it is. A failed removal of the build
directory changes no answer and raises nothing; a request to end during it
passes (ADR-0096 decision 2). Every forced removal of a container is given
:data:`REMOVAL_TIMEOUT_S` (decision 5).

Choices that are this module's own and no rule of a record:

* The build directory is :func:`tempfile.mkdtemp` with the prefix
  :data:`BUILD_DIR_PREFIX` in the temporary directory of the system. It is
  refused, removed and answered ``build_directory_unusable`` when its real
  path lies in the directory that holds this package
  (:data:`hilclaw.checkout_boundary.PACKAGE_DIRECTORY`) or below any
  directory that holds an entry ``.git``: the operation is not handed the
  data root (ADR-0056 decision 3), so "outside both checkouts and inside
  neither's ``.git/``" is kept as "inside no checkout of any repository".
  The cost: a temporary directory below the work tree of any repository (a
  home directory kept in git, for example) makes every call answer
  ``build_directory_unusable``.
  An :class:`OSError` of making it is answered the same way (S3).
* The executable is :data:`EXECUTABLE_NAME` directly in the build directory;
  every path handed to the compiler and the process is an absolute path
  inside the container, below :data:`hilclaw.standin_container.CONTAINER_BUILD_DIR`.
* The removal of the build directory is :func:`shutil.rmtree`, which removes
  a link met below the root as a name and does not descend into it, tried
  again after the pauses of :data:`REMOVE_PAUSES_S` (about two seconds in
  all); no step before a retry changes any permission. Where
  ``shutil.rmtree.avoids_symlink_attacks`` is false a name swapped for a link
  during the removal is a race this module does not close; that is a
  platform without ``os.getuid`` (Windows), on which no container is started
  (C4), so nothing the attempt made lies in the directory then.
* A status the client hands back that is not exactly an ``int`` (which
  :func:`hilclaw.local_run.run` never gives) is not placed: the operation
  raises :class:`RuntimeError`, and no log is handed over for it.
* Before anything is read or made, :class:`TypeError` is raised for check
  parameters that are not exactly a
  :class:`hilclaw.check_parameters.CheckParameters` or a keeper that is not
  exactly a :class:`hilclaw.build_log.LogKeeper`, and :class:`TypeError` or
  :class:`ValueError` for a value the process limit refuses or a seed that is
  not an ``int`` from 0 to below ``2**64`` (C16: no row; the tool function
  admits these values before the call).

It hands the compiler nothing derived from the seed (ADR-0078 decision 5),
imports no NumPy (the judging is the tool function's, ADR-0021 decision 2),
reads no environment variable of its own (the image's is read by
:func:`hilclaw.standin_image.read_image`, and :mod:`tempfile` reads the
variables that name the temporary directory of the system), and keeps
nothing between calls.
The process's standard error is read by nothing (OD-16 sub-question 5). The
operation is the ``correctness.check`` operation of the ``cpu_standin``
entry of :func:`hilclaw.check_definition.default_table`.

:class:`Answered`, :func:`carry_out`, :func:`container_image`,
:func:`make_build_dir`, :func:`in_container`, :func:`run_build`,
:func:`run_container`, :func:`settled` and :func:`remove_build_dir` are the
steps this operation shares with the ``cpu_standin`` operation of the run
tools, :func:`hilclaw.standin_run.operation` (ADR-0170).
"""

import contextlib
import os
import posixpath
import shutil
import stat
import tempfile
import time

from hilclaw import (
    build_log,
    check_failure,
    check_parameters,
    checkout_boundary,
    standin_answer,
    standin_container,
    standin_copies,
    standin_image,
    standin_settings,
    tools,
)
from hilclaw.harness import verification_build

#: Time limit in seconds of every forced removal of a container (ADR-0169 decision 5).
REMOVAL_TIMEOUT_S = 60

COMPILER = "clang"
EXECUTABLE_NAME = "verification"
BUILD_DIR_PREFIX = "hilclaw-standin-check-"
REMOVE_PAUSES_S = (0.0, 0.2, 0.6, 1.2)

_SEED_LIMIT = 2**64
_UNUSABLE = standin_answer.Failure(
    check_failure.KIND_BUILD_DIRECTORY_UNUSABLE,
    "the build directory could not be made outside every checkout",
)
_NO_EXECUTABLE = standin_answer.Failure(
    check_failure.KIND_BUILD_OUTPUT_MISSING,
    "the build ended with status 0 and left no executable",
)
_NO_STATUS = "the container's client handed back no status"
_EXECUTABLE = posixpath.join(standin_container.CONTAINER_BUILD_DIR, EXECUTABLE_NAME)


class Answered(Exception):
    """A :class:`hilclaw.standin_answer.Failure` met inside :func:`carry_out`, as ``answer``."""

    def __init__(self, answer):
        super().__init__()
        self.answer = answer


def operation(request, hw_profile, parameters, output_path, keeper, /):
    """Carry out one check at ``cpu_standin`` in two containers; return the report or a condition.

    ``request`` and ``hw_profile`` are not read. ``parameters`` are the check
    parameters, exactly a :class:`hilclaw.check_parameters.CheckParameters`;
    ``output_path`` is handed to :func:`hilclaw.standin_copies.place_copies`
    as it is; ``keeper`` is the call's :class:`hilclaw.build_log.LogKeeper`,
    handed at most one log (ADR-0169 decision 3).

    Returns the verification process's standard output as ``bytes`` after
    status 0, or one of ``"build_time_limit"``, ``"build_exit_status"``,
    ``"time_limit"`` and ``"exit_status"``. Raises
    :class:`hilclaw.tools.ToolFailure` of a backend kind of
    :mod:`hilclaw.check_failure` for every row of ADR-0168 that is one, with
    a message that shows no path, image reference, container name, stream
    byte or error text. Lets pass what no row places and every request to
    end. See the module docstring for the order and the module's own choices.
    """
    arguments, process_limit = _checked(parameters, keeper)
    image = container_image()
    build_dir = make_build_dir(BUILD_DIR_PREFIX)
    return carry_out(
        build_dir,
        lambda outcomes: _carry_out(
            image, build_dir, output_path, keeper, arguments, process_limit, outcomes
        ),
    )


def carry_out(build_dir, steps):
    """Return ``steps(outcomes)``, then remove ``build_dir`` where every outcome allows it.

    ``outcomes`` is a new list that :func:`run_container` fills with what
    each container gave. An :class:`Answered` that ``steps`` raises is raised
    as :class:`hilclaw.tools.ToolFailure` with its kind and message, and
    holds no chained error; anything else passes as it is. ``build_dir`` is
    removed by :func:`remove_build_dir` before this returns or raises, only
    where :func:`hilclaw.standin_answer.build_dir_removable` is true of every
    outcome (ADR-0168 decision 5).
    """
    outcomes = []
    try:
        return steps(outcomes)
    except Answered as answered:
        answer = answered.answer
    finally:
        if all(standin_answer.build_dir_removable(outcome) for outcome in outcomes):
            remove_build_dir(build_dir)
    raise tools.ToolFailure(answer.kind, answer.message)


def _checked(parameters, keeper):
    if type(parameters) is not check_parameters.CheckParameters:
        raise TypeError(
            f"parameters must be CheckParameters, not {type(parameters).__name__}"
        )
    if type(keeper) is not build_log.LogKeeper:
        raise TypeError(f"keeper must be a LogKeeper, not {type(keeper).__name__}")
    seed, draws, m, k, n = parameters
    limit = standin_settings.verification_process_time_limit_s(m, k, n, draws)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError(f"seed must be an int, not {type(seed).__name__}")
    if not 0 <= seed < _SEED_LIMIT:
        raise ValueError("seed must be an int from 0 to below 2**64")
    return tuple(str(int(value)) for value in (m, k, n, draws, seed)), limit


def container_image():
    """Return the image reference :func:`hilclaw.standin_image.read_image` gives (C1, C2).

    Raises :class:`hilclaw.tools.ToolFailure` ``compiler_unavailable`` where
    no image is named or the value is refused; lets pass what no row places.
    """
    try:
        value = standin_image.read_image()
    except Exception as error:
        answer = standin_answer.place_error(error, standin_answer.IMAGE)
        if answer is None:
            raise
    else:
        answer = standin_answer.read_image_value(value)
        if answer is standin_answer.GO_ON:
            return value
    raise tools.ToolFailure(answer.kind, answer.message)


def make_build_dir(prefix):
    """Make and return a new build directory with ``prefix`` outside every checkout (S3).

    The directory is :func:`tempfile.mkdtemp` in the temporary directory of
    the system; one that cannot be made, or whose real path lies inside a
    checkout (the module docstring), is removed where it was made and
    answered with :class:`hilclaw.tools.ToolFailure` ``build_directory_unusable``.
    """
    try:
        directory = tempfile.mkdtemp(prefix=prefix)
    except OSError:
        directory = None
    if directory is not None and not _inside_checkout(directory):
        return directory
    if directory is not None:
        remove_build_dir(directory)
    raise tools.ToolFailure(_UNUSABLE.kind, _UNUSABLE.message)


def _inside_checkout(directory):
    real = os.path.realpath(directory)
    if checkout_boundary.meets_checkout(real, (), containing=False):
        return True
    current = real
    while True:
        if os.path.lexists(os.path.join(current, ".git")):
            return True
        parent = os.path.dirname(current)
        if parent == current:
            return False
        current = parent


def _carry_out(image, build_dir, output_path, keeper, arguments, limit, outcomes):
    copies = _placed_copies(output_path, build_dir)
    built = _build(image, build_dir, copies, keeper, outcomes)
    if built is not standin_answer.GO_ON:
        return built
    ran = run_container(
        outcomes,
        standin_answer.PROCESS,
        image,
        build_dir,
        _EXECUTABLE,
        arguments,
        limit,
    )
    if type(ran) is str:
        return ran
    answer = standin_answer.read_process(ran)
    if answer is standin_answer.GO_ON:
        return ran.stdout
    return settled(answer)


def _placed_copies(output_path, build_dir):
    try:
        copies = standin_copies.place_copies(
            output_path, verification_build.PROGRAM_SOURCE, build_dir
        )
    except Exception as error:
        answer = standin_answer.place_error(error, standin_answer.COPIES)
        if type(answer) is not standin_answer.Failure:
            raise
        raise Answered(answer) from None
    answer = standin_answer.read_copies(copies)
    if answer is not standin_answer.GO_ON:
        raise Answered(answer)
    return copies


def _build(image, build_dir, copies, keeper, outcomes):
    sources = (copies.harness, *copies.compiled_set)
    command = (
        *standin_settings.FLAGS,
        *(in_container(source) for source in sources),
        *standin_settings.TRAILING_FLAGS,
        "-o",
        _EXECUTABLE,
    )
    return run_build(
        outcomes,
        image,
        build_dir,
        command,
        standin_settings.BUILD_TIME_LIMIT_S,
        keeper=keeper,
        executable=EXECUTABLE_NAME,
        missing=_NO_EXECUTABLE,
    )


def run_build(
    outcomes, image, build_dir, command, timeout_s, *, keeper, executable, missing
):
    """Run :data:`COMPILER` with ``command`` in one build container and read it.

    Returns :data:`hilclaw.standin_answer.GO_ON` when the build ended with
    status 0 and left a regular file ``executable`` directly in
    ``build_dir``, or a value of ``condition``. Where ``keeper`` is not
    ``None`` it is handed the log when ADR-0169 decision 3 says so, before the
    executable is looked for: the client's standard output then its standard
    error, each decoded as UTF-8 with invalid bytes replaced (decision 2).
    Raises :class:`Answered` with ``missing`` for a status 0 that left no
    such file (S9), and as :func:`run_container` and :func:`settled` do.
    """
    result = run_container(
        outcomes, standin_answer.BUILD, image, build_dir, COMPILER, command, timeout_s
    )
    if type(result) is str:
        return result
    answer = standin_answer.read_build(result)
    if keeper is not None and (answer is standin_answer.GO_ON or type(answer) is str):
        keeper.hand_over(_log(result))
    if answer is not standin_answer.GO_ON:
        return settled(answer)
    if not _regular_file(os.path.join(build_dir, executable)):
        raise Answered(missing)
    return standin_answer.GO_ON


def in_container(relative):
    """Return the absolute path inside the container of ``relative`` to the build directory."""
    return posixpath.join(standin_container.CONTAINER_BUILD_DIR, relative)


def run_container(outcomes, step, image, build_dir, program, arguments, timeout_s):
    """Run ``program`` in one container, give its forced removal :data:`REMOVAL_TIMEOUT_S`, and place what it raised.

    What :func:`hilclaw.standin_container.run_in_container` returned or raised
    is appended to ``outcomes``. Returns its
    :class:`hilclaw.standin_container.ContainerResult`, or the value of
    ``condition`` :func:`hilclaw.standin_answer.place_error` gives at
    ``step``; raises :class:`Answered` for a failure it gives, and lets pass
    as it is what it does not place and every request to end.
    """
    try:
        try:
            result = standin_container.run_in_container(
                image,
                build_dir,
                program,
                arguments,
                timeout_s=timeout_s,
                removal_timeout_s=REMOVAL_TIMEOUT_S,
            )
        except BaseException as error:
            outcomes.append(error)
            raise
    except Exception as error:  # noqa: BLE001
        return _place(error, step)
    outcomes.append(result)
    return result


def _place(error, step):
    answer = standin_answer.place_error(error, step)
    if answer is None:
        raise error
    if type(answer) is str:
        return answer
    raise Answered(answer)


def settled(answer):
    """Return a value of ``condition`` as it is; raise :class:`Answered` for a failure.

    ``None``, an answer no row gives, raises :class:`RuntimeError`.
    """
    if type(answer) is str:
        return answer
    if answer is None:
        raise RuntimeError(_NO_STATUS)
    raise Answered(answer)


def _log(result):
    return result.stdout.decode("utf-8", errors="replace") + result.stderr.decode(
        "utf-8", errors="replace"
    )


def _regular_file(path):
    try:
        return stat.S_ISREG(os.lstat(path).st_mode)
    except OSError:
        return False


def remove_build_dir(directory):
    """Remove ``directory`` with retries after :data:`REMOVE_PAUSES_S`; return whether it is gone.

    Raises nothing for a failed removal; a request to end passes.
    """
    for pause in REMOVE_PAUSES_S:
        time.sleep(pause)
        with contextlib.suppress(Exception):
            shutil.rmtree(directory)
        if not os.path.lexists(directory):
            return True
    return False
