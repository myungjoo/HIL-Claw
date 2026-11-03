"""The Qualcomm QNN adapter of PLAN P3-10 on the frame of ADR-0194: build, HTP-emulator run, timing run and SDK version probe.

The form is a C program against QNN's C interface (the headers under the
SDK's ``include/QNN``): it loads the QNN HTP backend library, whose host
build (x86_64) is the HTP emulator, builds a graph and executes it
(ADR-0194 decision 8: a harness is C against the vendor runtime's C
interface). Each job has the three parts of :mod:`hilclaw.vendor_adapter`:

* **build**: :func:`assemble_build` and :func:`build` are those of
  :mod:`hilclaw.clang_adapter` with the program :data:`BUILD_PROGRAM`
  (``clang``), whose command takes the form of
  :func:`hilclaw.clang_build.build`
  (``<program> <flags> <sources> <trailing_flags> -o <output>``). The
  adapter adds no flag: the SDK's include directory, the loader library
  (``-ldl``), the optimisation level and any other flag are the target's
  ``flags`` and ``trailing_flags``.
* **run**: :func:`assemble_run` and :func:`run` are those of
  :mod:`hilclaw.clang_adapter`: one host process of the built program with
  the run's ``arguments`` (for example the path of the HTP backend library),
  the target's ``env`` (for example the library search path) and a time
  limit capped by its ``process_time_limit_cap_s``. A run that ends with a
  non-zero status or by a signal, an allocation failure the program reports
  by its status included, is broken ``exit_status`` (ADR-0194 decision 3,
  the "Run failure" row). The emulator is a library the built program
  loads, so a missing emulator is read from no status or output of that
  process (ADR-0194 decision 3; ADR-0110 decision 3): it is the program's
  failure, and the SDK is reported by the probe and the environment check
  of :mod:`hilclaw.toolchain_check`.
* **measure**: :func:`assemble_timing` and :func:`measure`: one host process
  of a built timing program with the backend library path followed by the
  eight arguments of :func:`hilclaw.harness.timing.driver_arguments`, the
  target's ``env`` and the run's time limit; :func:`measure` hands the ended
  process to :func:`hilclaw.vendor_adapter.measure`, which gives the form (A)
  ``(stdout, None)`` or (B) of :mod:`hilclaw.run_operation`. No memory figure
  is given (HQ-0090 holds the figure of a vendor target), and a program that
  cannot start is not an ended process: the exception of
  :func:`hilclaw.local_run.run` is raised unchanged, and the caller may place
  it with :func:`hilclaw.vendor_adapter.interpret_run`.
* **probe**: :func:`assemble_probe` gives ``<program> --version``
  (:data:`VERSION_PROGRAM` is ``qnn-net-run``); :func:`interpret_probe`
  (host) and :func:`interpret_container_probe` (image) read it as
  :mod:`hilclaw.clang_adapter` does, except for the version: it is the first
  line, of standard output and then of standard error, that begins with
  ``QNN SDK v`` (for example ``QNN SDK v2.37.0.250724175447_124859``),
  stripped; ``qnn-net-run`` writes it to standard error after a line naming
  its process id on standard output. Status 0 with no such line is
  :data:`~hilclaw.vendor_adapter.UNREADABLE`. :func:`probe` joins the pair.

The program of a build or a probe is the argument ``program``, whose default
is the module's constant, as in :mod:`hilclaw.clang_adapter`; a test points
it at a fault-injection script there (ADR-0194 decision 6). Argument checks
raise :class:`TypeError` or :class:`ValueError` with the attribute
``parameter`` naming the argument. No ``Target`` entry, backend or tool is
attached here, no HTP architecture, SoC or optimisation value is fixed, and
no version is written anywhere.
"""

import os

from hilclaw import clang_adapter, local_run, run_parameters, vendor_adapter
from hilclaw.harness import timing

BUILD_PROGRAM = "clang"
VERSION_PROGRAM = "qnn-net-run"

_VERSION = "QNN SDK v"
_NO_VERSION = "the version query printed no SDK version line"
_VERSION_FOUND = "the version query gave an SDK version line"


def assemble_build(target, sources, output, *, program=BUILD_PROGRAM):
    """Return the :class:`hilclaw.vendor_adapter.BuildCall` of one build of a QNN program at ``target``.

    As :func:`hilclaw.clang_adapter.assemble_build`, with ``program``
    defaulting to :data:`BUILD_PROGRAM`.
    """
    return clang_adapter.assemble_build(target, sources, output, program=program)


def build(target, sources, output, *, program=BUILD_PROGRAM):
    """Build ``sources`` into ``output`` at ``target`` and return its :class:`hilclaw.vendor_adapter.Outcome`.

    As :func:`hilclaw.clang_adapter.build`, with ``program`` defaulting to
    :data:`BUILD_PROGRAM`.
    """
    return clang_adapter.build(target, sources, output, program=program)


def assemble_run(target, executable, arguments=(), *, timeout_s):
    """Return the :class:`hilclaw.vendor_adapter.RunCall` of one run of ``executable`` at ``target``.

    As :func:`hilclaw.clang_adapter.assemble_run`.
    """
    return clang_adapter.assemble_run(
        target, executable, arguments, timeout_s=timeout_s
    )


def run(target, executable, arguments=(), *, timeout_s):
    """Run ``executable`` at ``target`` and return its :class:`hilclaw.vendor_adapter.Outcome`.

    As :func:`hilclaw.clang_adapter.run`.
    """
    return clang_adapter.run(target, executable, arguments, timeout_s=timeout_s)


def _refuse(error, parameter):
    error.parameter = parameter
    raise error


def _backend(backend):
    if not isinstance(backend, (str, os.PathLike)):
        _refuse(
            TypeError(
                f"backend must be str or os.PathLike, not {type(backend).__name__}"
            ),
            "backend",
        )
    text = os.fspath(backend)
    if not isinstance(text, str):
        _refuse(TypeError("backend must be a str path, not bytes"), "backend")
    if not text:
        _refuse(ValueError("backend is empty"), "backend")
    return text


def _driver_arguments(parameters):
    if type(parameters) is not run_parameters.TimingParameters:
        _refuse(
            TypeError(
                "parameters must be a run_parameters.TimingParameters, "
                f"not {type(parameters).__name__}"
            ),
            "parameters",
        )
    try:
        return timing.driver_arguments(**parameters._asdict())
    except timing.TimingArgumentError as error:
        _refuse(error, "parameters")


def assemble_timing(target, executable, backend, parameters, *, timeout_s):
    """Return the :class:`hilclaw.vendor_adapter.RunCall` of one timing run of ``executable`` at ``target``.

    The command is ``executable``, the path of the QNN backend library
    ``backend`` (a non-empty ``str`` or :class:`os.PathLike` of ``str``) and
    the eight arguments :func:`hilclaw.harness.timing.driver_arguments` gives
    for ``parameters``, exactly a
    :class:`hilclaw.run_parameters.TimingParameters`; the rest is
    :func:`assemble_run`'s. Raises :class:`TypeError` or :class:`ValueError`
    with ``parameter`` ``"backend"``, ``"parameters"`` (a
    :class:`hilclaw.harness.timing.TimingArgumentError` for a value
    ``driver_arguments`` refuses included), ``"target"``, ``"executable"`` or
    ``"timeout_s"`` for a refused argument.
    """
    arguments = (_backend(backend), *_driver_arguments(parameters))
    return assemble_run(target, executable, arguments, timeout_s=timeout_s)


def measure(target, executable, backend, parameters, *, timeout_s):
    """Run one timing process at ``target`` and return the form (A) or (B) of :mod:`hilclaw.run_operation`.

    Arguments as :func:`assemble_timing`, all checked before anything starts.
    The ended process is handed to :func:`hilclaw.vendor_adapter.measure`
    with no figure: status 0 gives ``(stdout, None)``, a time limit
    ``"time_limit"`` and any other status ``"exit_status"``. An exception of
    :func:`hilclaw.local_run.run` is raised unchanged. The report is not
    judged here (ADR-0061 decision 3: that is the tool function's).
    """
    call = assemble_timing(target, executable, backend, parameters, timeout_s=timeout_s)
    result = local_run.run(call.command, timeout_s=call.timeout_s, env=call.env)
    return vendor_adapter.measure(result)


def assemble_probe(*, timeout_s, program=VERSION_PROGRAM):
    """Return the :class:`hilclaw.vendor_adapter.RunCall` of ``<program> --version``.

    As :func:`hilclaw.clang_adapter.assemble_probe`, with ``program``
    defaulting to :data:`VERSION_PROGRAM`.
    """
    return clang_adapter.assemble_probe(timeout_s=timeout_s, program=program)


def _version(stdout, stderr):
    for stream in (stdout, stderr):
        for line in stream.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith(_VERSION):
                return vendor_adapter.Probe(
                    vendor_adapter.PRESENT, line, _VERSION_FOUND
                )
    return vendor_adapter.Probe(vendor_adapter.UNREADABLE, None, _NO_VERSION)


def interpret_probe(answer, program):
    """Return the :class:`hilclaw.vendor_adapter.Probe` of what the host version query gave.

    As :func:`hilclaw.clang_adapter.interpret_probe` (its argument checks,
    :data:`~hilclaw.vendor_adapter.ABSENT`, the
    :data:`~hilclaw.vendor_adapter.UNREADABLE` of a time limit or a non-zero
    status, and ``None`` for an exception no row holds), except that status 0
    is :data:`~hilclaw.vendor_adapter.PRESENT` with the SDK version line of
    the module's reading and :data:`~hilclaw.vendor_adapter.UNREADABLE`
    without one.
    """
    found = clang_adapter.interpret_probe(answer, program)
    if found is None or isinstance(answer, BaseException):
        return found
    if answer.timed_out or answer.returncode != 0:
        return found
    return _version(answer.stdout, answer.stderr)


def interpret_container_probe(answer):
    """Return the :class:`hilclaw.vendor_adapter.Probe` of the version query run in a container.

    As :func:`hilclaw.clang_adapter.interpret_container_probe` (126 or 127
    :data:`~hilclaw.vendor_adapter.ABSENT`, 125 and any exception ``None``,
    its argument checks), except that status 0 is read for the SDK version
    line as :func:`interpret_probe` reads it.
    """
    found = clang_adapter.interpret_container_probe(answer)
    if found is None or answer.timed_out or answer.returncode != 0:
        return found
    return _version(answer.stdout, answer.stderr)


def probe(*, timeout_s, program=VERSION_PROGRAM):
    """Query the version of the QNN SDK and return its :class:`hilclaw.vendor_adapter.Probe`.

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
