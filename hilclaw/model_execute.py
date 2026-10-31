"""Build-and-run path of the model executor of ADR-0153: build directory, builds, one run.

``ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`` is the rule
(decision 3 "Loading", decision 5 and Consequences "A-13 reading"). This
module joins :mod:`hilclaw.model_build` and :mod:`hilclaw.model_run`:
:func:`execute` makes a build directory of its own outside both checkouts,
builds each fp32 ``gemm`` kernel into a shared library of its own and the
model program into it, and either returns the outcome **build failed** of
decision 5 (:class:`BuildFailed`) for the first failed build or writes the
input file and runs the program once; the directory is then removed on every
path. A run that failed is the outcome **run failed**, carried by the
:class:`hilclaw.model_run.ModelProgramResult` returned as it is. It builds
the program of the caller's ``dtype``, with that dtype's
:data:`hilclaw.model_build.PROGRAM_DTYPE_FLAGS`, and hands the same ``dtype``
to each function of :mod:`hilclaw.model_run` it calls.

Conventions of this module (not rules of the record):

- A kernel is any object with the attributes ``sources`` and ``flags``,
  handed to :func:`hilclaw.model_build.build_kernel_library` unchanged.
  Kernel ``i`` is library ``i`` of the program's command line, the index of
  the calls that use it.
- The build directory is made by :func:`tempfile.mkdtemp` with the name
  prefix :data:`PREFIX` under ``parent``; "outside both checkouts" is the
  test of :mod:`hilclaw.checkout_boundary` on the real path of ``parent``.
  Every path handed to a build or to the run is absolute. The directory is
  removed with :func:`hilclaw.scratch.remove`, which follows no symbolic link
  or junction; a removal that fails or is refused raises nothing and shows
  as ``removed`` false.
- Arguments outside what is stated raise :class:`TypeError` or
  :class:`ValueError` before anything is made, and the message names the
  argument and the position of an offending entry.

What this module does not do: it makes no binding check and no fit check of a
kernel to a call; it chooses no container or environment; it gives no time
limit a default; it chooses no flag beyond the dtype's
:data:`hilclaw.model_build.PROGRAM_DTYPE_FLAGS`; it compares nothing and holds no
reference or tolerance; it casts no array; it stores, keeps or retries
nothing; and it writes nothing outside the build directory.

Where it may be used (``ARCHITECTURE/decisions/ADR-0182-od14-model-executor-container.md``
decision 7): every build and the run of this module are host processes, so it
is only for kernels the caller wrote itself, as the driver's tests write them.
A kernel an instance or a coder wrote is built and run in containers by
:func:`hilclaw.model_container.execute`, never by this module; nothing here
checks who wrote a kernel.
"""

import os
import tempfile
from collections.abc import Sequence
from typing import NamedTuple

from hilclaw import checkout_boundary, clang_build, model_build, model_run, scratch

PREFIX = "hilclaw-model-"
"""Name prefix of every build directory this module makes."""

_PROGRAM_NAME = "model_program"
_INPUT_NAME = "input.bin"
_DTYPE_MACRO = "HILCLAW_MODEL_BF16"


class BuildFailed(NamedTuple):
    """The first failed build (ADR-0153 decision 5, build failed).

    ``kernel`` is the index of the kernel whose library failed, or ``None``
    for the model program; ``build`` is that build's
    :class:`hilclaw.clang_build.BuildResult`, whose ``log`` is the compiler
    output.
    """

    kernel: int | None
    build: clang_build.BuildResult


class ModelExecution(NamedTuple):
    """Outcome of one :func:`execute` call.

    ``build_failed`` is ``None`` or a :class:`BuildFailed`; ``run`` is
    ``None`` when a build failed, else the
    :class:`hilclaw.model_run.ModelProgramResult` of the run as returned;
    ``removed`` is whether the build directory no longer exists afterwards.
    """

    build_failed: BuildFailed | None
    run: model_run.ModelProgramResult | None
    removed: bool


def execute(
    kernels,
    calls,
    *,
    dtype,
    build_timeout_s,
    run_timeout_s,
    program_flags=(),
    program_trailing_flags=(),
    compiler=None,
    env=None,
    prefix=(),
    parent=None,
    keep_out=(),
):
    """Build ``kernels`` and the model program, run ``calls`` once, return a :class:`ModelExecution`.

    ``dtype`` is the generation's dtype, one of
    :data:`hilclaw.model_run.DTYPES`, with no default (ADR-0157 decision 1).
    ``kernels`` is a non-empty sequence (not ``str`` or ``bytes``) of objects
    with the attributes ``sources`` and ``flags``. ``calls`` is the argument
    of :func:`hilclaw.model_run.encode_input` at ``dtype``; every call's
    index must be below ``len(kernels)``. ``prefix`` is a sequence of paths
    put in front of the built program's path; empty, the program is started
    by its path.
    ``parent`` is the existing directory the build directory is made in
    (``None``: :func:`tempfile.gettempdir`); it must not be or lie inside the
    directory that holds this package or a directory of the sequence of paths
    ``keep_out``.

    Kernel 0, 1, ... are built in order with
    :func:`hilclaw.model_build.build_kernel_library` (their own ``sources``
    and ``flags``, ``build_timeout_s``, ``compiler``, ``env``), then the
    program with :func:`hilclaw.model_build.build_model_program`
    (``program_flags`` followed by
    ``hilclaw.model_build.PROGRAM_DTYPE_FLAGS[dtype]``,
    ``program_trailing_flags``, ``build_timeout_s``, ``compiler``, ``env``);
    no dtype flag goes to a kernel build. The first build whose ``ok`` is
    false stops the path: nothing after it is built or run. Otherwise the
    input file is written and :func:`hilclaw.model_run.run_model_program` is
    called with the libraries in index order, ``dtype``, ``run_timeout_s``
    and ``env``.

    Raised before anything is made, ``dtype`` first: :class:`TypeError` for
    a ``dtype`` that is not a ``str`` and :class:`ValueError` for one outside
    :data:`hilclaw.model_run.DTYPES`, each message starting with ``dtype:``.
    Then :class:`TypeError` for ``kernels`` that is no sequence, an entry
    without ``sources`` or ``flags``, a ``prefix`` that is no sequence or
    holds an entry that is not ``str`` or :class:`os.PathLike` of ``str``, a
    ``parent`` or ``keep_out`` entry of that kind, or a ``keep_out`` that is
    one path or no sequence; :class:`ValueError` for no kernels, a call index
    not below ``len(kernels)``, a path of ``prefix``, ``parent`` or
    ``keep_out`` with a NUL character, or a ``parent`` inside a checkout; and
    what :func:`hilclaw.model_run.output_shapes` raises for ``calls``,
    unchanged. Last, :class:`TypeError` for ``program_flags`` that is not a
    ``tuple`` or ``list`` of ``str``, and :class:`ValueError` for an item of
    it that contains ``HILCLAW_MODEL_BF16``, naming its position: ``dtype``
    alone selects the program's build. The :class:`OSError` of making the
    directory (a missing ``parent``) is raised as it is. What a build, the
    input file's writing or the run raises is passed on unchanged after the
    directory was removed.
    """
    _checked_dtype(dtype)
    kernels = _checked_kernels(kernels)
    shapes = model_run.output_shapes(calls, dtype=dtype)
    _check_indices(calls, kernels)
    prefix = _checked_prefix(prefix)
    roots = _checked_keep_out(keep_out)
    place = _checked_parent(parent, roots)
    program_flags = (
        *_checked_program_flags(program_flags),
        *model_build.PROGRAM_DTYPE_FLAGS[dtype],
    )
    directory = tempfile.mkdtemp(prefix=PREFIX, dir=place)
    try:
        build_failed, run = _build_and_run(
            directory,
            kernels,
            calls,
            shapes,
            prefix,
            dtype=dtype,
            build_timeout_s=build_timeout_s,
            run_timeout_s=run_timeout_s,
            program_flags=program_flags,
            program_trailing_flags=program_trailing_flags,
            compiler=compiler,
            env=env,
        )
    except BaseException:
        _remove(directory, roots)
        raise
    return ModelExecution(build_failed, run, _remove(directory, roots))


def _build_and_run(
    directory,
    kernels,
    calls,
    shapes,
    prefix,
    *,
    dtype,
    build_timeout_s,
    run_timeout_s,
    program_flags,
    program_trailing_flags,
    compiler,
    env,
):
    libraries = []
    for index, kernel in enumerate(kernels):
        library = os.path.join(directory, f"kernel-{index}.so")
        build = model_build.build_kernel_library(
            kernel.sources,
            library,
            timeout_s=build_timeout_s,
            flags=kernel.flags,
            compiler=compiler,
            env=env,
        )
        if not build.ok:
            return BuildFailed(index, build), None
        libraries.append(library)
    program = os.path.join(directory, _PROGRAM_NAME)
    build = model_build.build_model_program(
        program,
        timeout_s=build_timeout_s,
        flags=program_flags,
        trailing_flags=program_trailing_flags,
        compiler=compiler,
        env=env,
    )
    if not build.ok:
        return BuildFailed(None, build), None
    input_file = os.path.join(directory, _INPUT_NAME)
    with open(input_file, "xb") as stream:
        stream.write(model_run.encode_input(calls, dtype=dtype))
    run = model_run.run_model_program(
        (*prefix, program) if prefix else program,
        input_file,
        libraries,
        dtype=dtype,
        shapes=shapes,
        timeout_s=run_timeout_s,
        env=env,
    )
    return None, run


def _remove(directory, roots):
    try:
        return scratch.remove(directory, keep_out=roots)
    except scratch.InvalidScratchArgumentError:
        return not os.path.lexists(directory)


def _is_sequence(value):
    return isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    )


def _path(value, name):
    if isinstance(value, (str, os.PathLike)):
        path = os.fspath(value)
        if isinstance(path, str):
            if "\0" in path:
                raise ValueError(f"{name}: holds a NUL character")
            return path
    raise TypeError(
        f"{name}: must be str or os.PathLike of str, got {type(value).__name__}"
    )


def _checked_dtype(dtype):
    if not isinstance(dtype, str):
        raise TypeError(f"dtype: must be str, got {type(dtype).__name__}")
    if dtype not in model_run.DTYPES:
        raise ValueError(f"dtype: {dtype!r} is not one of {model_run.DTYPES}")


def _checked_program_flags(program_flags):
    if not isinstance(program_flags, (tuple, list)) or not all(
        isinstance(flag, str) for flag in program_flags
    ):
        raise TypeError("program_flags: must be a tuple or list of str")
    for position, flag in enumerate(program_flags):
        if _DTYPE_MACRO in flag:
            raise ValueError(
                f"program_flags[{position}]: names {_DTYPE_MACRO}, which only "
                "dtype selects"
            )
    return program_flags


def _checked_kernels(kernels):
    if not _is_sequence(kernels):
        raise TypeError(f"kernels: must be a sequence, got {type(kernels).__name__}")
    if not kernels:
        raise ValueError("kernels: no kernel")
    for position, kernel in enumerate(kernels):
        for attribute in ("sources", "flags"):
            if not hasattr(kernel, attribute):
                raise TypeError(f"kernels[{position}]: has no attribute {attribute!r}")
    return tuple(kernels)


def _check_indices(calls, kernels):
    for position, (index, _, _) in enumerate(calls):
        if index >= len(kernels):
            raise ValueError(
                f"calls[{position}]: index {index} is not below the number of "
                f"kernels {len(kernels)}"
            )


def _checked_prefix(prefix):
    if not _is_sequence(prefix):
        raise TypeError(f"prefix: must be a sequence, got {type(prefix).__name__}")
    return tuple(
        _path(part, f"prefix[{position}]") for position, part in enumerate(prefix)
    )


def _checked_keep_out(keep_out):
    checkout_boundary.refuse_one_path(keep_out)
    if not _is_sequence(keep_out):
        raise TypeError(
            f"keep_out: must be a sequence of paths, got {type(keep_out).__name__}"
        )
    return [
        _path(root, f"keep_out[{position}]") for position, root in enumerate(keep_out)
    ]


def _checked_parent(parent, roots):
    place = os.path.realpath(
        tempfile.gettempdir() if parent is None else _path(parent, "parent")
    )
    if checkout_boundary.meets_checkout(place, roots, containing=False):
        raise ValueError("parent: must not be or lie inside a checkout")
    return place
