"""The CUDA adapter of PLANs P3-9 and P3-13 on the frame of ADR-0194: ``nvcc`` build, run, timing run and probe, and the ``nvidia-smi`` device query.

Each job has the three parts of :mod:`hilclaw.vendor_adapter`:

* **build**: :func:`assemble_build` and :func:`build` are those of
  :mod:`hilclaw.clang_adapter` with the program :data:`PROGRAM`
  (``nvcc``), whose command takes the form of
  :func:`hilclaw.clang_build.build`
  (``<program> <flags> <sources> <trailing_flags> -o <output>``). The
  adapter adds no flag: ``-arch``, ``-gencode``, the optimisation level and
  any other flag are the target's ``flags`` and ``trailing_flags``.
* **run**: :func:`assemble_run` and :func:`run` are those of
  :mod:`hilclaw.clang_adapter`: one host process of the built executable with
  the target's ``env`` and a time limit capped by its
  ``process_time_limit_cap_s``. A CUDA program that reports an error (a device
  out of memory included) by a non-zero status is broken ``exit_status``
  (ADR-0194 decision 3, the "Run failure" row).
* **measure**: :func:`assemble_timing` and :func:`measure`: one host process
  of a built timing program with the eight arguments of
  :func:`hilclaw.harness.timing.driver_arguments`, the target's ``env`` and
  the run's time limit; :func:`measure` hands the ended process to
  :func:`hilclaw.vendor_adapter.measure`, which gives the form (A)
  ``(stdout, None)`` or (B) of :mod:`hilclaw.run_operation`. Where the
  interval starts and ends (launch and completion inside, transfers outside,
  ADR-0194 decision 4) is the timing program's; no GPU memory figure is given
  (HQ-0090), and a program that cannot start is not an ended process: the
  exception of :func:`hilclaw.local_run.run` is raised unchanged, and the
  caller may place it with :func:`hilclaw.vendor_adapter.interpret_run`.
* **probe**: :func:`assemble_probe` gives ``<program> --version``;
  :func:`interpret_probe` (host) and :func:`interpret_container_probe`
  (image) read it as :mod:`hilclaw.clang_adapter` does, except for the
  version: it is the first line of standard output that begins with
  ``Cuda compilation tools, release`` (for example
  ``Cuda compilation tools, release 13.1, V13.1.115``), stripped; ``nvcc``
  prints a banner before it. Status 0 with no such line is
  :data:`~hilclaw.vendor_adapter.UNREADABLE`. :func:`probe` joins the pair.
* **device query** (host only, ADR-0194 decisions 3 and 7):
  :func:`assemble_device_probe` gives
  ``<device program> --query-gpu=name,driver_version --format=csv,noheader``
  (:data:`DEVICE_PROGRAM` is ``nvidia-smi``); :func:`interpret_device_probe`
  reads it into one of four outcomes, each a
  :class:`hilclaw.vendor_adapter.Probe`: a usable device
  (:data:`~hilclaw.vendor_adapter.PRESENT`, the version naming each device
  and its driver version); **no device**, the tool ran and found no GPU or
  could not talk to the driver, which is
  :data:`~hilclaw.vendor_adapter.ABSENT` with the message :data:`NO_DEVICE`;
  the tool absent, :data:`~hilclaw.vendor_adapter.ABSENT` with another
  message; or :data:`~hilclaw.vendor_adapter.UNREADABLE`.
  :func:`device_probe` joins the pair. The query holds no code of an attempt;
  no status or output of an attempt's process is read as no device. "No
  device" is a value of this module only: no condition or failure kind
  carries it (ADR-0194 decision 3, V6 (a)).

The program of a build, a probe or a device query is the argument
``program``, whose default is the module's constant, as in
:mod:`hilclaw.clang_adapter`; a test points it at a fault-injection script
there (ADR-0194 decision 6). Argument checks raise :class:`TypeError` or
:class:`ValueError` with the attribute ``parameter`` naming the argument.
No ``Target`` entry, backend or tool is attached here, and no version is
written anywhere.
"""

from hilclaw import clang_adapter, local_run, run_parameters, vendor_adapter
from hilclaw.harness import timing

PROGRAM = "nvcc"
DEVICE_PROGRAM = "nvidia-smi"

NO_DEVICE = "the device query found no GPU or could not reach the driver"

_RELEASE = "Cuda compilation tools, release"
_NO_RELEASE = "the version query printed no release line"
_RELEASE_FOUND = "the version query gave a release line"
_DEVICE_QUERY = ("--query-gpu=name,driver_version", "--format=csv,noheader")
_NO_DEVICE_STATUSES = (6, 9, 12)
_DEVICE_FOUND = "the device query named a device and its driver"
_DEVICE_ABSENT = "the device query program was not found or could not be started"
_DEVICE_NO_LINE = "the device query printed no device line it could read"
_DEVICE_FAILED = {
    vendor_adapter.TIME_LIMIT: "the device query did not end within its time limit",
    vendor_adapter.EXIT_STATUS: "the device query ended with another non-zero status or by a signal",
}


def assemble_build(target, sources, output, *, program=PROGRAM):
    """Return the :class:`hilclaw.vendor_adapter.BuildCall` of one ``nvcc`` build at ``target``.

    As :func:`hilclaw.clang_adapter.assemble_build`, with ``program``
    defaulting to :data:`PROGRAM`.
    """
    return clang_adapter.assemble_build(target, sources, output, program=program)


def build(target, sources, output, *, program=PROGRAM):
    """Build ``sources`` into ``output`` with ``nvcc`` at ``target`` and return its :class:`hilclaw.vendor_adapter.Outcome`.

    As :func:`hilclaw.clang_adapter.build`, with ``program`` defaulting to
    :data:`PROGRAM`.
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


def _driver_arguments(parameters):
    if type(parameters) is not run_parameters.TimingParameters:
        error = TypeError(
            "parameters must be a run_parameters.TimingParameters, "
            f"not {type(parameters).__name__}"
        )
        error.parameter = "parameters"
        raise error
    try:
        return timing.driver_arguments(**parameters._asdict())
    except timing.TimingArgumentError as error:
        error.parameter = "parameters"
        raise


def assemble_timing(target, executable, parameters, *, timeout_s):
    """Return the :class:`hilclaw.vendor_adapter.RunCall` of one timing run of ``executable`` at ``target``.

    The command is ``executable`` and the eight arguments
    :func:`hilclaw.harness.timing.driver_arguments` gives for ``parameters``,
    exactly a :class:`hilclaw.run_parameters.TimingParameters`; the rest is
    :func:`assemble_run`'s. Raises :class:`TypeError` or :class:`ValueError`
    with ``parameter`` ``"parameters"`` (a
    :class:`hilclaw.harness.timing.TimingArgumentError` for a value
    ``driver_arguments`` refuses included), ``"target"``, ``"executable"`` or
    ``"timeout_s"`` for a refused argument.
    """
    arguments = _driver_arguments(parameters)
    return assemble_run(target, executable, arguments, timeout_s=timeout_s)


def measure(target, executable, parameters, *, timeout_s):
    """Run one timing process at ``target`` and return the form (A) or (B) of :mod:`hilclaw.run_operation`.

    Arguments as :func:`assemble_timing`, all checked before anything starts.
    The ended process is handed to :func:`hilclaw.vendor_adapter.measure`
    with no figure: status 0 gives ``(stdout, None)``, a time limit
    ``"time_limit"`` and any other status ``"exit_status"``. An exception of
    :func:`hilclaw.local_run.run` is raised unchanged. The report is not
    judged here (ADR-0061 decision 3: that is the tool function's).
    """
    call = assemble_timing(target, executable, parameters, timeout_s=timeout_s)
    result = local_run.run(call.command, timeout_s=call.timeout_s, env=call.env)
    return vendor_adapter.measure(result)


def assemble_probe(*, timeout_s, program=PROGRAM):
    """Return the :class:`hilclaw.vendor_adapter.RunCall` of ``<program> --version``.

    As :func:`hilclaw.clang_adapter.assemble_probe`, with ``program``
    defaulting to :data:`PROGRAM`.
    """
    return clang_adapter.assemble_probe(timeout_s=timeout_s, program=program)


def _release(stdout):
    for line in stdout.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith(_RELEASE):
            return vendor_adapter.Probe(vendor_adapter.PRESENT, line, _RELEASE_FOUND)
    return vendor_adapter.Probe(vendor_adapter.UNREADABLE, None, _NO_RELEASE)


def interpret_probe(answer, program):
    """Return the :class:`hilclaw.vendor_adapter.Probe` of what the host version query gave.

    As :func:`hilclaw.clang_adapter.interpret_probe` (its argument checks,
    :data:`~hilclaw.vendor_adapter.ABSENT`, the
    :data:`~hilclaw.vendor_adapter.UNREADABLE` of a time limit or a non-zero
    status, and ``None`` for an exception no row holds), except that status 0
    is :data:`~hilclaw.vendor_adapter.PRESENT` with the release line of the
    module's reading and :data:`~hilclaw.vendor_adapter.UNREADABLE` without
    one.
    """
    found = clang_adapter.interpret_probe(answer, program)
    if found is None or isinstance(answer, BaseException):
        return found
    if answer.timed_out or answer.returncode != 0:
        return found
    return _release(answer.stdout)


def interpret_container_probe(answer):
    """Return the :class:`hilclaw.vendor_adapter.Probe` of the version query run in a container.

    As :func:`hilclaw.clang_adapter.interpret_container_probe` (126 or 127
    :data:`~hilclaw.vendor_adapter.ABSENT`, 125 and any exception ``None``,
    its argument checks), except that status 0 is read for the release line
    as :func:`interpret_probe` reads it.
    """
    found = clang_adapter.interpret_container_probe(answer)
    if found is None or answer.timed_out or answer.returncode != 0:
        return found
    return _release(answer.stdout)


def probe(*, timeout_s, program=PROGRAM):
    """Query the version of ``nvcc`` and return its :class:`hilclaw.vendor_adapter.Probe`.

    Arguments as :func:`assemble_probe`. An exception of
    :func:`hilclaw.local_run.run` that :func:`interpret_probe` does not place
    is raised unchanged.
    """
    call = assemble_probe(timeout_s=timeout_s, program=program)
    return _query(call, interpret_probe)


def assemble_device_probe(*, timeout_s, program=DEVICE_PROGRAM):
    """Return the :class:`hilclaw.vendor_adapter.RunCall` of the device query.

    The command is ``program`` followed by
    ``--query-gpu=name,driver_version`` and ``--format=csv,noheader``: one
    line per GPU, its product name and its display driver version separated
    by a comma, no header. The environment is inherited (``None``). Raises
    :class:`TypeError` or :class:`ValueError` with ``parameter``
    ``"timeout_s"`` or ``"program"`` for a refused argument.
    """
    call = clang_adapter.assemble_probe(timeout_s=timeout_s, program=program)
    return call._replace(command=(*call.command[:-1], *_DEVICE_QUERY))


def _devices(stdout):
    lines = [
        line.strip()
        for line in stdout.decode("utf-8", errors="replace").splitlines()
        if line.strip()
    ]
    named = []
    for line in lines:
        name, _, driver = line.rpartition(",")
        name, driver = name.strip(), driver.strip()
        if not name or not driver:
            return vendor_adapter.Probe(
                vendor_adapter.UNREADABLE, None, _DEVICE_NO_LINE
            )
        named.append(f"{name} (driver {driver})")
    if not named:
        return vendor_adapter.Probe(vendor_adapter.UNREADABLE, None, _DEVICE_NO_LINE)
    return vendor_adapter.Probe(vendor_adapter.PRESENT, "; ".join(named), _DEVICE_FOUND)


def interpret_device_probe(answer, program):
    """Return the :class:`hilclaw.vendor_adapter.Probe` of what the device query gave.

    ``answer`` is the :class:`hilclaw.local_run.RunResult` or the exception
    of :func:`hilclaw.local_run.run`; ``program`` is the first element of the
    query's command. Read by :func:`hilclaw.vendor_adapter.interpret_run`:
    the program not found or unable to start,
    :data:`~hilclaw.vendor_adapter.ABSENT`; status 6 (no GPU found), 9 (the
    driver is not loaded) or 12 (the NVML library could not be found or
    loaded), the return codes NVIDIA documents for ``nvidia-smi``,
    :data:`~hilclaw.vendor_adapter.ABSENT` with the message
    :data:`NO_DEVICE`; a time limit, a signal or any other non-zero status,
    :data:`~hilclaw.vendor_adapter.UNREADABLE`. Status 0 with at least one
    non-blank line, each a name and a driver version around its last comma,
    neither blank, is :data:`~hilclaw.vendor_adapter.PRESENT` with the
    version ``"<name> (driver <version>)"``, joined by ``"; "`` for several
    devices; any other output, :data:`~hilclaw.vendor_adapter.UNREADABLE`.
    Any other exception gives ``None``. Raises :class:`TypeError` or
    :class:`ValueError` as :func:`~hilclaw.vendor_adapter.interpret_run`
    does.
    """
    outcome = vendor_adapter.interpret_run(answer, program)
    if outcome is None:
        return None
    if outcome.form == vendor_adapter.TOOL_FAILURE:
        return vendor_adapter.Probe(vendor_adapter.ABSENT, None, _DEVICE_ABSENT)
    if outcome.form == vendor_adapter.BROKEN:
        if (
            outcome.condition == vendor_adapter.EXIT_STATUS
            and answer.returncode in _NO_DEVICE_STATUSES
        ):
            return vendor_adapter.Probe(vendor_adapter.ABSENT, None, NO_DEVICE)
        return vendor_adapter.Probe(
            vendor_adapter.UNREADABLE, None, _DEVICE_FAILED[outcome.condition]
        )
    return _devices(outcome.carried)


def device_probe(*, timeout_s, program=DEVICE_PROGRAM):
    """Query the GPUs and their driver and return the :class:`hilclaw.vendor_adapter.Probe`.

    Arguments as :func:`assemble_device_probe`. An exception of
    :func:`hilclaw.local_run.run` that :func:`interpret_device_probe` does
    not place is raised unchanged.
    """
    call = assemble_device_probe(timeout_s=timeout_s, program=program)
    return _query(call, interpret_device_probe)


def _query(call, interpret):
    try:
        result = local_run.run(call.command, timeout_s=call.timeout_s, env=call.env)
    except Exception as error:
        found = interpret(error, call.command[0])
        if found is None:
            raise
        return found
    return interpret(result, call.command[0])
