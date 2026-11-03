"""The reference adapter of ADR-0194 for ``clang`` on the host: build, run and probe.

It checks the frame of :mod:`hilclaw.vendor_adapter` with the tool CI has
(ADR-0194 decision 2, last bullet). Each job has three parts:

* **build**: :func:`assemble_build` turns a :class:`hilclaw.targets.Target`
  (``flags``, ``trailing_flags``, ``env``, ``build_time_limit_s``), the
  sources and the output path into a :class:`hilclaw.vendor_adapter.BuildCall`;
  :func:`build` hands it to :func:`hilclaw.clang_build.build` and the outcome
  to :func:`hilclaw.vendor_adapter.interpret_build`.
* **run**: :func:`assemble_run` turns the built executable and its arguments
  into a :class:`hilclaw.vendor_adapter.RunCall` with the target's ``env``
  and a time limit capped by its ``process_time_limit_cap_s``; :func:`run`
  hands it to :func:`hilclaw.local_run.run` and the outcome to
  :func:`hilclaw.vendor_adapter.interpret_run`.
* **probe**: :func:`assemble_probe` gives the version query
  ``<program> --version`` as a :class:`hilclaw.vendor_adapter.RunCall`;
  :func:`interpret_probe` reads what :func:`hilclaw.local_run.run` gave as a
  :class:`hilclaw.vendor_adapter.Probe`; :func:`probe` joins the two. The
  version is the first line of standard output, stripped, as
  :func:`hilclaw.clang_build.compiler_version` reads it. In an image the same
  query runs through :func:`hilclaw.standin_container.run_in_container` and
  :func:`interpret_container_probe` reads it (the environment check of
  :mod:`hilclaw.toolchain_check`, ADR-0194 decision 7).

The program started by a build or a probe is the argument ``program``,
whose default is :data:`PROGRAM`, as :func:`hilclaw.clang_build.build`
takes ``compiler``: a ``str`` or :class:`os.PathLike`, or a non-empty
sequence of ``str`` used as a command prefix. A test points it at a
fault-injection script there (ADR-0194 decision 6); no environment variable,
configuration or ``PATH`` change names a program.

The assemble parts are pure: they start no process and read no file, clock
or environment variable. Their argument checks raise :class:`TypeError` or
:class:`ValueError` with the attribute ``parameter`` naming the argument;
what they pass through unchecked (sources, output) is checked by the
executor. The execute parts call the executor and the interpret part and
nothing else; an exception no row of the interpret part holds is raised
unchanged. No ``Target`` entry, backend or tool is attached here.
"""

import os

from hilclaw import clang_build, local_run, standin_container, targets, vendor_adapter

PROGRAM = "clang"

_ABSENT = "the program was not found or could not be started"
_NO_LINE = "the version query printed no version line"
_PRESENT = "the version query gave a version line"
_FAILED = {
    vendor_adapter.TIME_LIMIT: "the version query did not end within its time limit",
    vendor_adapter.EXIT_STATUS: "the version query ended with a non-zero status or by a signal",
}
_CLIENT_FAILED = 125
_NOT_IN_IMAGE = (126, 127)


def _refuse(error, parameter):
    error.parameter = parameter
    raise error


def _check_target(target):
    if type(target) is not targets.Target:
        _refuse(
            TypeError(f"target must be a targets.Target, not {type(target).__name__}"),
            "target",
        )


def _path_text(value, parameter):
    if not isinstance(value, (str, os.PathLike)):
        _refuse(
            TypeError(
                f"{parameter} must be str or os.PathLike, not {type(value).__name__}"
            ),
            parameter,
        )
    text = os.fspath(value)
    if not isinstance(text, str):
        _refuse(TypeError(f"{parameter} must be a str path, not bytes"), parameter)
    if not text:
        _refuse(ValueError(f"{parameter} is empty"), parameter)
    return text


def _program(program):
    if isinstance(program, (str, os.PathLike)):
        return (_path_text(program, "program"),)
    if isinstance(program, (bytes, bytearray)) or not hasattr(program, "__iter__"):
        _refuse(
            TypeError(
                "program must be str, os.PathLike or a sequence of str, "
                f"not {type(program).__name__}"
            ),
            "program",
        )
    parts = tuple(program)
    if not parts:
        _refuse(ValueError("program is an empty sequence"), "program")
    for part in parts:
        if type(part) is not str:
            _refuse(
                TypeError(f"a part of program must be str, not {type(part).__name__}"),
                "program",
            )
        if not part:
            _refuse(ValueError("a part of program is empty"), "program")
    return parts


def _sources(sources):
    if isinstance(sources, (str, os.PathLike)):
        return (sources,)
    try:
        return tuple(sources)
    except TypeError as error:
        _refuse(error, "sources")


def _arguments(arguments):
    if isinstance(arguments, (str, bytes)):
        _refuse(
            TypeError(
                f"arguments must be a sequence of str, not one {type(arguments).__name__}"
            ),
            "arguments",
        )
    try:
        parts = tuple(arguments)
    except TypeError as error:
        _refuse(error, "arguments")
    for part in parts:
        if type(part) is not str:
            _refuse(
                TypeError(f"an argument must be str, not {type(part).__name__}"),
                "arguments",
            )
    return parts


def assemble_build(target, sources, output, *, program=PROGRAM):
    """Return the :class:`hilclaw.vendor_adapter.BuildCall` of one build at ``target``.

    ``sources`` is one path or a sequence of paths and ``output`` the
    artefact path, handed to :func:`hilclaw.clang_build.build` as given (it
    checks them). ``flags``, ``trailing_flags``, ``env`` and ``timeout_s``
    are the target's ``flags``, ``trailing_flags``, ``env`` and
    ``build_time_limit_s``; no file is placed. Raises :class:`TypeError` or
    :class:`ValueError` with ``parameter`` ``"target"``, ``"sources"`` or
    ``"program"`` for a refused argument.
    """
    _check_target(target)
    compiler = _program(program)
    return vendor_adapter.BuildCall(
        compiler=compiler,
        flags=target.flags,
        sources=_sources(sources),
        trailing_flags=target.trailing_flags,
        output=output,
        env=target.env,
        timeout_s=target.build_time_limit_s,
    )


def assemble_run(target, executable, arguments=(), *, timeout_s):
    """Return the :class:`hilclaw.vendor_adapter.RunCall` of one run of ``executable`` at ``target``.

    The command is ``executable`` followed by ``arguments`` (a sequence of
    ``str``); ``env`` is the target's; the time limit is the smaller of
    ``timeout_s`` and the target's ``process_time_limit_cap_s``. Raises
    :class:`TypeError` or :class:`ValueError` with ``parameter``
    ``"target"``, ``"executable"``, ``"arguments"`` or ``"timeout_s"`` for a
    refused argument.
    """
    _check_target(target)
    command = (_path_text(executable, "executable"), *_arguments(arguments))
    vendor_adapter.check_timeout(timeout_s)
    return vendor_adapter.RunCall(
        command=command,
        env=target.env,
        timeout_s=min(timeout_s, target.process_time_limit_cap_s),
    )


def assemble_probe(*, timeout_s, program=PROGRAM):
    """Return the :class:`hilclaw.vendor_adapter.RunCall` of the version query ``<program> --version``.

    The environment is inherited (``None``). Raises :class:`TypeError` or
    :class:`ValueError` with ``parameter`` ``"timeout_s"`` or ``"program"``
    for a refused argument.
    """
    vendor_adapter.check_timeout(timeout_s)
    return vendor_adapter.RunCall(
        command=(*_program(program), "--version"), env=None, timeout_s=timeout_s
    )


def interpret_probe(answer, program):
    """Return the :class:`hilclaw.vendor_adapter.Probe` of what the version query gave.

    ``answer`` is the :class:`hilclaw.local_run.RunResult` or the exception
    of :func:`hilclaw.local_run.run`; ``program`` is the first element of the
    query's command. Read by :func:`hilclaw.vendor_adapter.interpret_run`:
    the program not found or unable to start, :data:`~hilclaw.vendor_adapter.ABSENT`;
    a time limit or a non-zero status,
    :data:`~hilclaw.vendor_adapter.UNREADABLE`; status 0 with a first stdout
    line that is not blank, :data:`~hilclaw.vendor_adapter.PRESENT` with that
    line stripped, else :data:`~hilclaw.vendor_adapter.UNREADABLE`. Any other
    exception gives ``None``. Raises :class:`TypeError` as
    :func:`~hilclaw.vendor_adapter.interpret_run` does.
    """
    outcome = vendor_adapter.interpret_run(answer, program)
    if outcome is None:
        return None
    if outcome.form == vendor_adapter.TOOL_FAILURE:
        return vendor_adapter.Probe(vendor_adapter.ABSENT, None, _ABSENT)
    if outcome.form == vendor_adapter.BROKEN:
        return vendor_adapter.Probe(
            vendor_adapter.UNREADABLE, None, _FAILED[outcome.condition]
        )
    return _version(outcome.carried)


def _version(stdout):
    lines = stdout.decode("utf-8", errors="replace").splitlines()
    if not lines or not lines[0].strip():
        return vendor_adapter.Probe(vendor_adapter.UNREADABLE, None, _NO_LINE)
    return vendor_adapter.Probe(vendor_adapter.PRESENT, lines[0].strip(), _PRESENT)


def interpret_container_probe(answer):
    """Return the :class:`hilclaw.vendor_adapter.Probe` of the version query run in a container.

    ``answer`` is the :class:`hilclaw.standin_container.ContainerResult` or
    the exception of :func:`hilclaw.standin_container.run_in_container` for
    the command of :func:`assemble_probe`. Past the limit,
    :data:`~hilclaw.vendor_adapter.UNREADABLE`; status 0, as
    :func:`interpret_probe` reads the first line; 126 or 127, the client's
    statuses for a program it could not start or find in the image,
    :data:`~hilclaw.vendor_adapter.ABSENT` (the query holds no code of an
    attempt, so these are no status of the program's, ADR-0194 decision 3);
    any other status, :data:`~hilclaw.vendor_adapter.UNREADABLE`. Status 125,
    the client's own failure, and any exception give ``None``: no container
    was used, which is a fact of the image and not of the program. A status
    that is not exactly an ``int`` raises :class:`ValueError`; any other
    value raises :class:`TypeError` with ``parameter`` ``"answer"``.
    """
    if isinstance(answer, BaseException):
        return None
    if type(answer) is not standin_container.ContainerResult:
        _refuse(
            TypeError(
                "answer must be ContainerResult or an exception, "
                f"not {type(answer).__name__}"
            ),
            "answer",
        )
    if answer.timed_out:
        return vendor_adapter.Probe(
            vendor_adapter.UNREADABLE, None, _FAILED[vendor_adapter.TIME_LIMIT]
        )
    status = answer.returncode
    if type(status) is not int:
        raise ValueError(
            "no row holds a container that did not time out and has no status"
        )
    if status == _CLIENT_FAILED:
        return None
    if status in _NOT_IN_IMAGE:
        return vendor_adapter.Probe(vendor_adapter.ABSENT, None, _ABSENT)
    if status != 0:
        return vendor_adapter.Probe(
            vendor_adapter.UNREADABLE, None, _FAILED[vendor_adapter.EXIT_STATUS]
        )
    return _version(answer.stdout)


def build(target, sources, output, *, program=PROGRAM):
    """Build ``sources`` into ``output`` at ``target`` and return its :class:`hilclaw.vendor_adapter.Outcome`.

    Arguments as :func:`assemble_build`. An exception of
    :func:`hilclaw.clang_build.build` that
    :func:`hilclaw.vendor_adapter.interpret_build` does not place is raised
    unchanged.
    """
    call = assemble_build(target, sources, output, program=program)
    try:
        result = clang_build.build(
            call.sources,
            call.output,
            timeout_s=call.timeout_s,
            flags=call.flags,
            trailing_flags=call.trailing_flags,
            compiler=call.compiler,
            env=call.env,
        )
    except Exception as error:
        outcome = vendor_adapter.interpret_build(error)
        if outcome is None:
            raise
        return outcome
    return vendor_adapter.interpret_build(result)


def run(target, executable, arguments=(), *, timeout_s):
    """Run ``executable`` at ``target`` and return its :class:`hilclaw.vendor_adapter.Outcome`.

    Arguments as :func:`assemble_run`. An exception of
    :func:`hilclaw.local_run.run` that
    :func:`hilclaw.vendor_adapter.interpret_run` does not place is raised
    unchanged.
    """
    call = assemble_run(target, executable, arguments, timeout_s=timeout_s)
    try:
        result = local_run.run(call.command, timeout_s=call.timeout_s, env=call.env)
    except Exception as error:
        outcome = vendor_adapter.interpret_run(error, call.command[0])
        if outcome is None:
            raise
        return outcome
    return vendor_adapter.interpret_run(result, call.command[0])


def probe(*, timeout_s, program=PROGRAM):
    """Query the version of ``program`` and return its :class:`hilclaw.vendor_adapter.Probe`.

    Arguments as :func:`assemble_probe`. An exception of
    :func:`hilclaw.local_run.run` that :func:`interpret_probe` does not place
    is raised unchanged.
    """
    call = assemble_probe(timeout_s=timeout_s, program=program)
    try:
        result = local_run.run(call.command, timeout_s=call.timeout_s, env=call.env)
    except Exception as error:
        found = interpret_probe(error, call.command[0])
        if found is None:
            raise
        return found
    return interpret_probe(result, call.command[0])
