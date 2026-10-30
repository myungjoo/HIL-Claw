"""Build step of a bf16 timing run of ADR-0181: the timing program of one kind and one kernel, one executable.

``ARCHITECTURE/decisions/ADR-0181-od13-bf16-timing-run.md`` is the rule
(decisions 2 and 3), with ADR-0009 decision 2 for the build. There is one
timing program per kind, and :data:`PROGRAM_SOURCES` maps each kind of this
slice to the C source of its program. :func:`build_bf16_timing_executable`
hands the program of the kind the caller names and the source files of one
kernel of that kind to one call of :func:`hilclaw.clang_build.build`; the
executable it builds is what :func:`hilclaw.harness.bf16_timing.run_bf16_timing`
starts. The command is that of ``clang_build``, with the kind's program source
first among the sources::

    <compiler...> <flags...> <program source of the kind> <kernel sources...>
        <trailing_flags...> -o <temporary output>

The harness adds no flag: no define, no ``-I`` and no library. Flags, trailing
flags, the compiler, the time limit of the build, the path of the executable,
the environment and the working directory are the caller's, and they apply to
the program source as well. The programs need no math library, but a kernel
may: a SwiGLU kernel that calls ``expf`` or an RMSNorm kernel that uses
``<math.h>`` needs the caller's ``-lm`` among the ``trailing_flags``. Each
program includes the shared header ``bf16_timing.h`` with quotes, which
includes ``bf16_verification.h`` the same way; the compiler finds both next to
the program sources, so no include directory is needed. Flags that do not
produce an executable (an object, a shared library) are not corrected: what
was built is not looked at.

Conventions of this module (not rules of the record):

- The program source is first, as the command above shows.
- The kernel sources are not compared with one another or with the program
  source. A file given twice, or a program source given as a kernel source,
  is compiled twice; a symbol it defines twice fails the build at the linker.
  A kernel of another kind leaves the program's symbol undefined, which also
  fails the build at the linker.

What this module does not do: it chooses no flag, compiler, time limit or
output path; it runs nothing that it built; it does not retry, repair or store
a failed build; it reads no configuration and no environment variable of its
own; it relates this build to no verification build; and it registers no kind
with ``sim.run``, ``board.run`` or the instance start (ADR-0181 decision 8).
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
"""Read-only mapping from each kind to the path of its timing program, next to this module."""


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

    ``kind`` is exactly a ``str`` that is a key of :data:`PROGRAM_SOURCES`.
    ``kernel_sources`` is one path (``str`` or :class:`os.PathLike`) or a
    non-empty iterable of paths: all source files of one kernel of that kind.
    Every other argument is that of :func:`hilclaw.clang_build.build`, with the
    same defaults, and is handed over unchanged. The call is made once and its
    :class:`hilclaw.clang_build.BuildResult` is returned as it is: a compile
    failure, a link failure or a timeout is a result with ``ok`` false.

    Raised before anything is started, in this order: :class:`ValueError` for
    a ``kind`` that is not such a key (a ``str`` subclass, ``bytes`` and
    ``None`` included), with the attribute ``parameter`` set to ``"kind"``;
    :class:`TypeError` for ``kernel_sources`` that is neither a path nor
    iterable; and :class:`ValueError` for no kernel source. That
    :class:`TypeError`, and any :class:`TypeError` or :class:`ValueError`
    (including a subclass) raised while iterating ``kernel_sources``, carries
    the attribute ``parameter`` set to ``"kernel_sources"``; the
    :class:`ValueError` for no kernel source carries none. Whatever
    :func:`hilclaw.clang_build.build` raises is passed on unchanged.
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
