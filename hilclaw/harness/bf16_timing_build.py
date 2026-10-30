"""Build step of a bf16 timing run of ADR-0181: the timing program of one kind and one kernel, one executable.

``ARCHITECTURE/decisions/ADR-0181-od13-bf16-timing-run.md`` decisions 2 and 3
are the rule, with ADR-0009 decision 2 for the build. :data:`PROGRAM_SOURCES`
maps each kind to its timing program, which includes ``bf16_timing.h`` and,
through it, ``bf16_verification.h``, both found next to it.
:func:`build_bf16_timing_executable` builds as
:func:`hilclaw.harness.bf16_verification_build.build_bf16_verification_executable`
does: the kind's program first, then the kernel sources, in one call of
:func:`hilclaw.clang_build.build` to which the harness adds no flag. A kernel
that needs ``-lm`` needs it among the caller's ``trailing_flags``.
"""

import os
import types
from pathlib import Path

from hilclaw import clang_build

_HERE = Path(__file__).parent

PROGRAM_SOURCES = types.MappingProxyType(
    {
        kind: _HERE / f"bf16_timing_{kind}.c"
        for kind in ("gemm", "rmsnorm", "elementwise_add", "swiglu")
    }
)


def build_bf16_timing_executable(
    kind,
    kernel_sources,
    output,
    *,
    timeout_s,
    flags=(),
    trailing_flags=(),
    compiler=None,
    cwd=None,
    env=None,
):
    """Build the timing program of ``kind`` and the sources of one kernel into ``output``.

    The arguments, the result and what is raised are those of
    :func:`hilclaw.harness.bf16_verification_build.build_bf16_verification_executable`
    with :data:`PROGRAM_SOURCES` of this module: a ``kind`` that is not
    exactly a ``str`` key of it raises :class:`ValueError` with ``parameter``
    ``"kind"`` before anything is started.
    """
    if type(kind) is not str or kind not in PROGRAM_SOURCES:
        error = ValueError(
            f"kind must be one of {', '.join(map(repr, PROGRAM_SOURCES))}, not {kind!r}"
        )
        error.parameter = "kind"
        raise error
    if isinstance(kernel_sources, (str, os.PathLike)):
        kernel_sources = (kernel_sources,)
    try:
        kernel_sources = tuple(kernel_sources)
    except (TypeError, ValueError) as error:
        error.parameter = "kernel_sources"
        raise
    if not kernel_sources:
        raise ValueError("no kernel source file given")
    return clang_build.build(
        (PROGRAM_SOURCES[kind], *kernel_sources),
        output,
        timeout_s=timeout_s,
        flags=flags,
        trailing_flags=trailing_flags,
        compiler=compiler,
        cwd=cwd,
        env=env,
    )
