"""The hw_profile record of the local ``cuda_gpu`` (ADR-0207 decision 2).

``ARCHITECTURE/decisions/ADR-0207-od33-cuda-target-demonstration.md``
decision 2 says which strings the key fields of a hw_profile hold when its
``accelerator`` is ``cuda_gpu``, the one GPU of the machine the package runs
on. :func:`local_record` reads them and returns the record. Under WSL that
machine is the Linux environment.

* ``accelerator`` is :data:`ACCELERATOR` (:data:`hilclaw.targets.CUDA_GPU`).
* ``revision`` is ``<product name> sm_<major><minor>`` of the one line of the
  device query ``nvidia-smi --query-gpu=name,compute_cap,driver_version
  --format=csv,noheader`` (:data:`DEVICE_QUERY`), always run on the host. The
  line is split at its last two commas into the product name, the compute
  capability and the driver version; the compute capability must be
  ``<major>.<minor>`` in decimal digits without a leading zero. A device query with no line or with
  more than one line has no record (a line here is one that is not empty
  after the spelling's run and end rule).
* ``toolchain`` has exactly three members. ``nvcc`` is the release line of
  ``nvcc --version``: the first line that, after the spelling's run and end
  rule, begins with ``Cuda compilation tools, release``, the prefix
  :func:`hilclaw.cuda_adapter.interpret_probe` looks for (on the output of
  ``nvcc`` both pick the same line; lines here end at a line feed only). ``gcc`` is the first
  line of ``gcc --version``. ``nvidia_driver`` is the driver version of the
  device query's line. When the caller names an image, ``nvcc --version`` and
  ``gcc --version`` are each run as the program of one new container of it
  through :func:`hilclaw.standin_container.run_in_container`, as ADR-0186
  reads ``clang``; otherwise on the host. The device query is never run in a
  container: the driver is the host's.
* ``host`` and ``hw_source`` follow the rules of ``cpu_standin``
  (ADR-0035 decisions 4 and 8), read by :mod:`hilclaw.standin_profile`.

Every fact uses the line and spelling rules of :mod:`hilclaw.standin_profile`,
which this module reuses. A fact that cannot be read is a
:class:`hilclaw.standin_profile.UnreadableFactError` and no record is
returned; nothing is substituted.

What the module does not do: it registers and stores nothing, is bound to no
tool and has no command-line entry and no caller in the package yet. It does
not choose a device on a machine with several GPUs (ADR-0207 Boundaries) and
reads no GPU memory figure (HQ-0090). The kernel name is read first; then, in
this order, ``nvcc``, ``gcc``, the device query and the host members are
read, each at every call, through :func:`hilclaw.local_run.run` (without a
shell, found on ``PATH``). It writes no file; with an image it makes one empty
temporary directory per container and removes it.
"""

import functools
import re
import reprlib

from hilclaw import cuda_adapter, keys, standin_container, targets
from hilclaw.cuda_adapter import _RELEASE
from hilclaw.standin_profile import (
    _RUN,
    UnreadableFactError,
    _host,
    _output,
    _ruled_kernel,
    _run,
    _run_in_image,
    _spelling,
)

ACCELERATOR = targets.CUDA_GPU
GCC = "gcc"
DEVICE_QUERY = ("--query-gpu=name,compute_cap,driver_version", "--format=csv,noheader")

_CAPABILITY = re.compile(rb"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
_RELEASE_PREFIX = _RELEASE.encode("ascii")


def local_record(hw_source, *, timeout_s, image=None):
    """Return the hw_profile record of the ``cuda_gpu`` this process runs on.

    The result is a new ``dict`` with exactly the members ``schema_version``
    (:data:`hilclaw.keys.SCHEMA_VERSION`), ``accelerator``
    (:data:`ACCELERATOR`), ``revision``, ``toolchain`` (``{"nvcc": ...,
    "gcc": ..., "nvidia_driver": ...}``), ``host`` (``{"cpu": ..., "os":
    ...}``) and ``hw_source``, read by the rules of the module docstring. It is
    a record :func:`hilclaw.keys.hw_profile_key` accepts; it is neither stored
    nor registered.

    @param hw_source one of :data:`hilclaw.keys.HW_SOURCES`, checked before
        anything else.
    @param timeout_s the limit in seconds of each command that is started, and
        with an image also of each forced removal.
    @param image ``None`` to read ``nvcc`` and ``gcc`` on the host, or the
        reference of the image the kernels are built in, checked by
        :func:`hilclaw.standin_container.check_image` before the machine is read.
    @throws hilclaw.keys.InvalidRecordError for a ``hw_source`` that is not
        one of the two values.
    @throws TypeError or ValueError for an image the check refuses, and as
        :func:`hilclaw.standin_profile.local_record` for a ``timeout_s`` that
        :func:`hilclaw.local_run.run` or
        :func:`hilclaw.standin_container.run_in_container` refuses.
    @throws hilclaw.standin_profile.UnreadableFactError for a fact that cannot
        be read: the cases of :func:`hilclaw.standin_profile.local_record` for
        the kernel name, each command and the host members; ``nvcc`` output
        with no release line; a device query with no line or more than one,
        a line that is not three fields, or a compute capability that is not
        ``<major>.<minor>``.
    """
    if type(hw_source) is not str or hw_source not in keys.HW_SOURCES:
        rule = " or ".join(keys.HW_SOURCES)
        got = reprlib.repr(hw_source)
        raise keys.InvalidRecordError(f"hw_source: must be {rule}, got {got}")
    if image is not None:
        standin_container.check_image(image)
    name, release = _ruled_kernel()
    nvcc = _release_line(
        _version_lines("toolchain.nvcc", cuda_adapter.PROGRAM, image, timeout_s)
    )
    gcc = _spelling(
        "toolchain.gcc", _version_lines("toolchain.gcc", GCC, image, timeout_s)[0]
    )
    revision, driver = _device(timeout_s)
    return {
        "schema_version": keys.SCHEMA_VERSION,
        "accelerator": ACCELERATOR,
        "revision": revision.decode("ascii"),
        "toolchain": {
            "nvcc": nvcc.decode("ascii"),
            "gcc": gcc.decode("ascii"),
            "nvidia_driver": driver.decode("ascii"),
        },
        "host": _host(name, release, timeout_s),
        "hw_source": hw_source,
    }


def _version_lines(fact, program, image, timeout_s):
    if image is None:
        start = functools.partial(_run, (program, "--version"), timeout_s)
        shown = f"{program} --version"
    else:
        start = functools.partial(_run_in_image, image, timeout_s, program)
        shown = f"docker run <image> {program} --version"
    return _output(fact, shown, timeout_s, start)


def _release_line(lines):
    for line in lines:
        if _RUN.sub(b" ", line).strip(b" ").startswith(_RELEASE_PREFIX):
            return _spelling("toolchain.nvcc", line)
    raise UnreadableFactError(
        "toolchain.nvcc: `nvcc --version` printed no release line"
    )


def _device(timeout_s):
    command = (cuda_adapter.DEVICE_PROGRAM, *DEVICE_QUERY)
    shown = " ".join(command)
    start = functools.partial(_run, command, timeout_s)
    lines = [
        line
        for line in _output("revision", shown, timeout_s, start)
        if _RUN.sub(b" ", line).strip(b" ")
    ]
    if not lines:
        raise UnreadableFactError(f"revision: `{shown}` named no GPU")
    if len(lines) > 1:
        raise UnreadableFactError(
            f"revision: `{shown}` named more than one GPU; such a machine has no record"
        )
    fields = lines[0].rsplit(b",", 2)
    if len(fields) != 3:
        raise UnreadableFactError(
            "revision: the device line is not a name, a compute capability "
            "and a driver version"
        )
    name, capability, driver = fields
    found = _CAPABILITY.fullmatch(_spelling("revision", capability))
    if found is None:
        raise UnreadableFactError(
            "revision: the compute capability is not <major>.<minor>"
        )
    revision = _spelling(
        "revision", _spelling("revision", name) + b" sm_" + found[1] + found[2]
    )
    return revision, _spelling("toolchain.nvidia_driver", driver)
