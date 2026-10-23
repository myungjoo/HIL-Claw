"""Build step of the model executor of ADR-0153: one kernel into a shared library, and the model program.

``ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`` is the rule
(decisions 1 (ii), 2 and 3 "Loading"). Each bound fp32 ``gemm`` kernel of
ADR-0008 is built into a shared library of its own with
:func:`build_kernel_library`, and the model program of fixed source,
:data:`PROGRAM_SOURCE`, into an executable with :func:`build_model_program`.
The program loads each library with ``dlopen`` and calls its ``hilclaw_gemm``
(its header comment states its command line, input file and report). Each
function makes one call of :func:`hilclaw.clang_build.build`, whose command
is::

    <compiler...> <flags...> <sources...> <trailing_flags...> -o <temporary output>

The only flags this module adds are what a shared library needs,
:data:`LIBRARY_FLAGS`, after the caller's flags of a kernel build.

What this module does not do: it checks no binding of a kernel to a call; it
places no directory and chooses no output path, compiler or time limit; it runs
nothing that it built and writes no input file of the program; it chooses no
flag beyond :data:`LIBRARY_FLAGS`, and in particular adds no ``-ldl`` to the
program build (that is the caller's ``trailing_flags``); it does not retry,
repair or store a failed build; and it reads no configuration and no
environment variable of its own.
"""

import os
from pathlib import Path

from hilclaw import clang_build

PROGRAM_SOURCE = Path(__file__).with_name("model_program.c")
"""Path of the C source of the model program, next to this module."""

LIBRARY_FLAGS = ("-shared", "-fPIC")
"""Flags that make a kernel build a shared library, after the caller's flags."""


def build_kernel_library(
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
    """Build the sources of one kernel into the shared library ``output``.

    ``kernel_sources`` is one path (``str`` or :class:`os.PathLike`) or a
    non-empty iterable of paths: all source files of one kernel. ``flags`` is
    a ``tuple`` or ``list`` of ``str``; the build gets those flags followed by
    :data:`LIBRARY_FLAGS`. Every other argument is that of
    :func:`hilclaw.clang_build.build`, with the same defaults, and is handed
    over unchanged. The call is made once and its
    :class:`hilclaw.clang_build.BuildResult` is returned as it is: a compile
    failure, a link failure or a timeout is a result with ``ok`` false.

    Raised before anything is started, in this order: :class:`TypeError` for
    ``flags`` that is not a ``tuple`` or ``list`` or holds an item that is not
    ``str``, with the attribute ``parameter`` set to ``"flags"``;
    :class:`TypeError` for ``kernel_sources`` that is neither a path nor
    iterable, which, like any :class:`TypeError` or :class:`ValueError`
    (including a subclass) raised while iterating ``kernel_sources``, carries
    ``parameter`` set to ``"kernel_sources"``; and :class:`ValueError` for no
    kernel source, which carries none. Read the attribute as
    ``getattr(error, "parameter", None)``. Whatever
    :func:`hilclaw.clang_build.build` raises is passed on unchanged, with its
    own attributes.
    """
    if not isinstance(flags, (tuple, list)) or not all(
        isinstance(flag, str) for flag in flags
    ):
        error = TypeError("flags must be a tuple or list of str")
        error.parameter = "flags"
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
        kernel_sources,
        output,
        timeout_s=timeout_s,
        flags=(*flags, *LIBRARY_FLAGS),
        trailing_flags=trailing_flags,
        compiler=compiler,
        cwd=cwd,
        env=env,
    )


def build_model_program(
    output,
    *,
    timeout_s,
    flags=(),
    trailing_flags=(),
    compiler=None,
    cwd=None,
    env=None,
):
    """Build :data:`PROGRAM_SOURCE` alone into the executable ``output``.

    Every argument is that of :func:`hilclaw.clang_build.build`, with the same
    defaults, and is handed over unchanged; no flag is added. Whether the C
    library needs ``-ldl`` for ``dlopen`` is the caller's ``trailing_flags``.
    The call is made once and its :class:`hilclaw.clang_build.BuildResult` is
    returned as it is. Whatever :func:`hilclaw.clang_build.build` raises is
    passed on unchanged, including :class:`FileNotFoundError` for a program
    source missing from the installation.
    """
    return clang_build.build(
        (PROGRAM_SOURCE,),
        output,
        timeout_s=timeout_s,
        flags=flags,
        trailing_flags=trailing_flags,
        compiler=compiler,
        cwd=cwd,
        env=env,
    )
