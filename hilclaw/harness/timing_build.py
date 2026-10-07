"""Build step of a timing run of ADR-0009: the driver program and one kernel, one executable.

``ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md`` is the rule
(decisions 2 and 9). :func:`build_timing_executable` hands the driver source of
the harness and the source files of one kernel to one call of
:func:`hilclaw.clang_build.build`; the executable it builds is what
:func:`hilclaw.harness.timing.run_timing` starts. The command is that of
``clang_build``, with the driver source first among the sources::

    <compiler...> <flags...> <driver source> <kernel sources...>
        <trailing_flags...> -o <temporary output>

The harness adds no flag. Flags, trailing flags, the compiler, the time limit
of the build and the path of the executable are the caller's, and they apply to
the driver source as well. Flags that do not produce an executable (an object,
a shared library) are not corrected: what was built is not looked at.

Conventions of this module (not rules of the record):

- The driver source is first, as the command above shows.
- The kernel sources are not compared with one another or with the driver
  source. A file given twice, or the driver source given as a kernel source, is
  compiled twice and the build fails at the linker.

What this module does not do: it chooses no flag, compiler, time limit or
output path; it runs nothing that it built; it does not retry, repair or store
a failed build; and it reads no configuration and no environment variable of
its own.
"""

import os
from pathlib import Path

from hilclaw import clang_build

DRIVER_SOURCE = Path(__file__).with_name("timing_driver.c")
"""Path of the C source of the driver program, next to this module."""


def build_timing_executable(
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
    """Build :data:`DRIVER_SOURCE` and the sources of one kernel into ``output``.

    ``kernel_sources`` is one path (``str`` or :class:`os.PathLike`) or a
    non-empty iterable of paths: all source files of one kernel. Every other
    argument is that of :func:`hilclaw.clang_build.build`, with the same
    defaults, and is handed over unchanged. The call is made once and its
    :class:`hilclaw.clang_build.BuildResult` is returned as it is: a compile
    failure, a link failure or a timeout is a result with ``ok`` false.

    Raised before anything is started: :class:`ValueError` for no kernel
    source, tested before every other argument; :class:`TypeError` for
    ``kernel_sources`` that is neither a path nor iterable; and whatever
    :func:`hilclaw.clang_build.build` raises, unchanged. That includes
    :class:`FileNotFoundError` for a driver source that is missing from the
    installation and :class:`TypeError` for a ``bytes`` path (an empty one is
    no kernel source).
    """
    if isinstance(kernel_sources, (str, os.PathLike)):
        kernel_sources = (kernel_sources,)
    kernel_sources = tuple(kernel_sources)
    if not kernel_sources:
        raise ValueError("no kernel source file given")
    return clang_build.build(
        (DRIVER_SOURCE, *kernel_sources),
        output,
        timeout_s=timeout_s,
        flags=flags,
        trailing_flags=trailing_flags,
        compiler=compiler,
        cwd=cwd,
        env=env,
    )
