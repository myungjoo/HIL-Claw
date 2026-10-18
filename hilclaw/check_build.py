"""Which answer of ``correctness.check`` one build of the verification executable is.

``ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md``
decision 4 gives the answer of each situation S3 to S10 of a build: a tool
failure of a backend kind of :mod:`hilclaw.check_failure`, or a value of
``condition`` of the form (B) of ADR-0043 decision 4. The records ADR-0079 to
ADR-0094 place what :func:`hilclaw.harness.verification_build.build_verification_executable`
returns or raises, which is what :func:`hilclaw.clang_build.build` returns or
raises, in those rows. This module renders, ahead of the operation of
``cpu_standin``, those rows and nothing else:

* :func:`read_build`: the answer of a :class:`hilclaw.clang_build.BuildResult`
  that was returned, by the reading of a build of ADR-0060 decision 4:

  * ``ok`` true: :data:`BUILT`, an ok build, after which the operation starts
    the executable;
  * ``timed_out`` true: ``"build_time_limit"`` (S8);
  * a ``returncode`` other than 0, a negative one (a signal on POSIX)
    included: ``"build_exit_status"`` (S7);
  * ``returncode`` 0: ``build_output_missing`` (S9).

* :func:`place_error`: the answer of what was raised, by the first test that
  holds:

  1. no :class:`Exception`, a request to end such as :class:`KeyboardInterrupt`
     or :class:`SystemExit`: not placed (ADR-0045 decisions 1 and 5; ADR-0083
     decision 2);
  2. :class:`~hilclaw.clang_build.TemporaryNotRemovedError`: the answer of its
     carried build ``result`` by :func:`read_build`, :data:`BUILT` included
     (ADR-0079 decision 3);
  3. :class:`~hilclaw.clang_build.ArtefactNotPlacedError` or
     :class:`~hilclaw.clang_build.ArtefactNotCheckedError`:
     ``build_output_missing`` (S9; ADR-0079 decision 2; ADR-0080 decision 3);
  4. :class:`~hilclaw.clang_build.CompilerNotStartedError`:
     ``compiler_unavailable`` (S6; ADR-0079 decision 4; ADR-0080 decision 2);
  5. :class:`~hilclaw.clang_build.CompilerRunError`: ``timed_out`` true,
     ``"build_time_limit"`` (S8; ADR-0082 decision 2; ADR-0084 decision 2);
     else ``returncode`` ``None``, not placed (ADR-0082 decision 4);
     ``returncode`` 0, ``build_output_missing`` (S9; ADR-0085 decision 5); any
     other ``returncode``, ``"build_exit_status"`` (S7; ADR-0085 decision 3);
  6. :class:`~hilclaw.clang_build.CompilerNotFoundError`:
     ``compiler_unavailable`` (S6; ADR-0060 decision 4);
  7. any other :class:`OSError`, by ``path_role``: ``"source"``,
     ``build_input_missing`` (S5; ADR-0086 decision 3); ``"output"``,
     ``build_directory_unusable`` (S3; ADR-0086 decision 4); none and a
     :class:`NotADirectoryError`, ``build_directory_unusable`` (S3; ADR-0060
     decision 4; ADR-0086 decision 6); otherwise not placed (ADR-0083 decision
     3; ADR-0086 decision 6);
  8. a :class:`TypeError` or :class:`ValueError`, a subclass such as
     :class:`UnicodeEncodeError` included, by ``parameter``: ``"timeout_s"``,
     ``"flags"``, ``"trailing_flags"``, ``"compiler"`` or ``"env"``,
     ``settings_refused`` (S4; ADR-0087 decision 3; ADR-0089 decision 2;
     ADR-0090 decision 2; ADR-0094 decision 2); any other value, none
     included, not placed (ADR-0087 decisions 4 and 5; ADR-0089 decisions 3 to
     5; ADR-0091 decisions 2 and 3; ADR-0092 decision 2; ADR-0093 decision 2);
  9. anything else: not placed.

``None`` from either function means "not placed: let it pass". The operation
then lets the error pass, and the landed rules answer it
``operation_answer_invalid`` (ADR-0045 decisions 4 and 5); that is no answer of
this module.

``place_error`` reads the class and the documented members ``result``,
``timed_out``, ``returncode``, ``path_role`` and ``parameter``, the last two as
``getattr(error, name, None)``. It reads no message, no ``args``, no exception
chain, no ``errno`` and no private state, and changes nothing of the object.

Choices that are this module's own and no rule of a record: a ``returncode``
counts as a status only when its type is exactly :class:`int`, so a value
:func:`hilclaw.clang_build.build` never gives is not placed; and a value that
is not exactly a :class:`~hilclaw.clang_build.BuildResult`, a carried build
included, raises :class:`TypeError` naming its type and not the value.

What the module does not do: it calls no build, starts no process, removes no
directory and raises no tool failure. It hands no log to the keeper of
ADR-0078 and writes no message of a kind (ADR-0060 decision 5). It keeps
nothing between calls.
"""

from hilclaw import check_failure, check_result, clang_build

#: The answer of an ok build: the operation goes on to start the executable.
BUILT = object()

_BUILD_TIME_LIMIT, _BUILD_EXIT_STATUS = check_result.CONDITIONS[:2]
_SETTINGS = ("timeout_s", "flags", "trailing_flags", "compiler", "env")


def _read_status(returncode):
    if type(returncode) is not int:
        return None
    if returncode == 0:
        return check_failure.KIND_BUILD_OUTPUT_MISSING
    return _BUILD_EXIT_STATUS


def read_build(result):
    """Return the answer of the returned build ``result``.

    The answer is :data:`BUILT`, ``"build_time_limit"``, ``"build_exit_status"``,
    :data:`hilclaw.check_failure.KIND_BUILD_OUTPUT_MISSING`, or ``None`` for a
    build that is not ok, not timed out and has no ``returncode``. Raises
    :class:`TypeError` when ``result`` is not exactly a
    :class:`hilclaw.clang_build.BuildResult`.
    """
    if type(result) is not clang_build.BuildResult:
        raise TypeError(
            f"result must be a clang_build.BuildResult, not {type(result).__name__}"
        )
    if result.ok:
        return BUILT
    if result.timed_out:
        return _BUILD_TIME_LIMIT
    return _read_status(result.returncode)


def place_error(error):
    """Return the answer of ``error``, raised by one build, or ``None`` when no row holds it.

    The answer is :data:`BUILT` (only for a
    :class:`hilclaw.clang_build.TemporaryNotRemovedError` whose carried build
    is ok), ``"build_time_limit"``, ``"build_exit_status"``, one of the backend
    kinds ``build_directory_unusable``, ``settings_refused``,
    ``build_input_missing``, ``compiler_unavailable`` and
    ``build_output_missing``, or ``None``. Raises :class:`TypeError` as
    :func:`read_build` does when the carried build of a
    :class:`hilclaw.clang_build.TemporaryNotRemovedError` is not exactly a
    :class:`hilclaw.clang_build.BuildResult`.
    """
    if not isinstance(error, Exception):
        return None
    if isinstance(error, clang_build.TemporaryNotRemovedError):
        return read_build(error.result)
    if isinstance(
        error, (clang_build.ArtefactNotPlacedError, clang_build.ArtefactNotCheckedError)
    ):
        return check_failure.KIND_BUILD_OUTPUT_MISSING
    if isinstance(error, clang_build.CompilerNotStartedError):
        return check_failure.KIND_COMPILER_UNAVAILABLE
    if isinstance(error, clang_build.CompilerRunError):
        if error.timed_out:
            return _BUILD_TIME_LIMIT
        return _read_status(error.returncode)
    if isinstance(error, clang_build.CompilerNotFoundError):
        return check_failure.KIND_COMPILER_UNAVAILABLE
    if isinstance(error, OSError):
        role = getattr(error, "path_role", None)
        if role == "source":
            return check_failure.KIND_BUILD_INPUT_MISSING
        if role == "output":
            return check_failure.KIND_BUILD_DIRECTORY_UNUSABLE
        if role is None and isinstance(error, NotADirectoryError):
            return check_failure.KIND_BUILD_DIRECTORY_UNUSABLE
        return None
    if (
        isinstance(error, (TypeError, ValueError))
        and getattr(error, "parameter", None) in _SETTINGS
    ):
        return check_failure.KIND_SETTINGS_REFUSED
    return None
