"""Host side's run of the model program of ADR-0153: input file, one process, report.

``ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`` is the rule
(decisions 1, 3 and 5). The header comment of ``model_program.c`` defines the
program's command line, its input file, its report, the end mark and its exit
statuses; this module speaks to exactly that. :func:`encode_input` turns a
list of ``gemm`` calls, each ``(index, a, b)`` with in-memory arrays, into
the bytes of the input file; :func:`output_shapes` gives the ``(m, n)``
of each call; :func:`run_model_program` starts the program once with its
libraries under a time limit; and :func:`parse_report` reads a complete
report into one output array per call. A run that times out, ends with a
status other than 0 or leaves no complete report is the outcome **run
failed** of decision 5, named by :class:`RunFailed`.

Each of the four functions takes the dtype of the generation, one of
:data:`DTYPES`, as the required keyword argument ``dtype``, with no default:
it is never assumed (ADR-0157 decision 1). The program comes in one build
per dtype (the header comment of ``model_program.c``), and the dtype selects
the element type of the arrays, of the input file and of the report as in
the table of ADR-0157 decision 3: ``float32`` for ``fp32``, and ``uint16``
for ``bf16``, each element the bit pattern of a bf16 value.
:func:`run_model_program` does not know which build of the program it
starts; the caller passes the dtype that matches it.

The command is::

    <program or command prefix...> <input file> <library> [<library> ...]

Conventions of this module (not rules of the record):

- The conditions of a run are tested in the order of :class:`RunFailed`, and
  the first that fails is the one reported. A signal is not told apart from a
  non-zero exit status; ``run.returncode`` shows it.
- The length of a complete report is computed from the shapes alone and
  compared before any byte is read; nothing is allocated from the report's
  length. Each output is a fresh array that owns its memory, and its elements
  are passed through as they are, NaN included.
- ``run`` of a :class:`ModelProgramResult` is what the runner captured apart
  from the report: its ``stdout`` is replaced by ``b""``.
- ``program`` is a path or a sequence used as a command prefix, as in
  :func:`hilclaw.harness.verification.run_verification`, so a caller can put
  the start of an isolated environment in front of the program.
- ``dtype`` is checked first, before any other argument: a ``dtype`` that is
  not a ``str`` raises :class:`TypeError` and one outside :data:`DTYPES`
  :class:`ValueError`, with a message that starts with ``dtype:``.
- Arguments outside what is stated raise :class:`TypeError` or
  :class:`ValueError` before anything is built or started, and the message
  names the position of the offending entry. What :func:`hilclaw.local_run.run`
  raises is passed on.

What this module does not do: it checks no binding of a kernel to a call and
builds nothing; it places no directory and chooses no input path; it chooses
no container or environment; it gives the time limit no default; it compares
nothing and holds no reference or tolerance; it casts no array to another
dtype; and it does not store or retry anything.
"""

import enum
import os
from collections.abc import Sequence
from typing import NamedTuple

import numpy as np

from hilclaw import local_run

END_MARK = b"end\n"
"""The 4 bytes that end a complete report."""

DTYPES = ("fp32", "bf16")
"""The dtypes the model program is built for, by their ``dtype`` names."""

_UINT64_LIMIT = 2**64
_ELEMENTS = {"fp32": np.dtype(np.float32), "bf16": np.dtype(np.uint16)}


class RunFailed(enum.Enum):
    """The condition of a run that failed first (ADR-0153 decision 5, run failed)."""

    TIMEOUT = enum.auto()
    EXIT_STATUS = enum.auto()
    REPORT_FORM = enum.auto()


class ModelProgramResult(NamedTuple):
    """Outcome of one :func:`run_model_program` call.

    For a run that did not time out, ended with status 0 and left a complete
    report, ``failed`` is ``None`` and ``outputs`` holds one array of shape
    ``(m, n)`` per entry of ``shapes``, in order, of the element dtype of the
    run's ``dtype``: ``float32`` for ``fp32``, and ``uint16`` bf16 bit
    patterns for ``bf16`` (ADR-0157 decision 3, the report). For any other run
    ``failed`` names the failed condition and ``outputs`` is ``None``,
    whatever the report holds. ``run`` is what the runner captured with an
    empty ``stdout``, in both cases.
    """

    failed: RunFailed | None
    outputs: tuple[np.ndarray, ...] | None
    run: local_run.RunResult


def encode_input(calls, *, dtype):
    """Return the bytes of the program's input file for ``calls`` at ``dtype``.

    ``dtype`` is one of :data:`DTYPES`; its element dtype is ``float32`` for
    ``fp32`` and ``uint16`` for ``bf16``. ``calls`` is a non-empty sequence
    of ``(index, a, b)``, a tuple or a list of three items each: ``index`` an
    ``int`` (not ``bool``) with ``0 <= index < 2**64``, and ``a`` and ``b``
    two-dimensional :class:`numpy.ndarray` of exactly that element dtype,
    every dimension at least 1 and ``a.shape[1] == b.shape[0]``; no array is
    cast or reinterpreted. The bytes are the number of calls, then for each
    call ``index``, ``m``, ``k``, ``n`` and the elements of ``a`` and ``b``
    in row-major order whatever their memory order, as ``uint64`` and the
    element dtype (4 or 2 bytes) in host byte order.

    Raised before any byte is built, ``dtype`` first: :class:`TypeError` for
    a ``dtype`` that is not a ``str``, a ``calls`` that is no sequence (a
    ``str`` or ``bytes`` included), an entry that is not a tuple or list of
    three items, an ``index`` that is not an ``int`` or an array that is not
    an ``ndarray``; :class:`ValueError` for a ``dtype`` outside
    :data:`DTYPES`, no calls, an ``index`` out of range, an array dtype other
    than the element dtype of ``dtype``, a number of dimensions other than 2,
    a zero dimension or inner dimensions that differ.
    """
    element = _checked_dtype(dtype)
    checked = _checked_calls(calls, dtype, element)
    parts = [np.array([len(checked)], dtype=np.uint64).tobytes()]
    for index, a, b in checked:
        m, k = a.shape
        n = b.shape[1]
        parts.append(np.array([index, m, k, n], dtype=np.uint64).tobytes())
        parts.append(a.tobytes(order="C"))
        parts.append(b.tobytes(order="C"))
    return b"".join(parts)


def output_shapes(calls, *, dtype):
    """Return the tuple of ``(m, n)`` of each call, after the checks of :func:`encode_input`."""
    element = _checked_dtype(dtype)
    checked = _checked_calls(calls, dtype, element)
    return tuple((a.shape[0], b.shape[1]) for _, a, b in checked)


def parse_report(report, shapes, *, dtype):
    """Return the outputs of a complete report for ``shapes`` at ``dtype``, or ``None``.

    ``dtype`` is one of :data:`DTYPES`; E is the size of its element dtype,
    4 bytes for ``float32`` (``fp32``) and 2 for ``uint16`` (``bf16``).
    ``shapes`` is a non-empty sequence of ``(m, n)`` pairs of ``int`` of at
    least 1 (not ``bool``). A complete report is exactly the sum of
    ``E*m*n`` bytes over ``shapes`` followed by :data:`END_MARK`; for it the
    result is one fresh array of the element dtype and of shape ``(m, n)``
    per entry, in order, and for any other report ``None``. Nothing is
    started or written.

    Raised before any byte of ``report`` is looked at: :class:`TypeError` or
    :class:`ValueError` for ``dtype`` and ``shapes`` as in
    :func:`run_model_program`, and :class:`TypeError` for a ``report`` that
    is not exactly ``bytes`` (a ``bytearray``, a ``memoryview`` and a
    subclass included).
    """
    element = _checked_dtype(dtype)
    checked = _checked_shapes(shapes)
    if type(report) is not bytes:
        raise TypeError(f"report: must be bytes, got {type(report).__name__}")
    return _outputs(report, checked, element)


def run_model_program(
    program, input_file, libraries, *, dtype, shapes, timeout_s, cwd=None, env=None
):
    """Run the model program once and return a :class:`ModelProgramResult`.

    One process ``(*prefix, input_file, *libraries)`` is started with
    :func:`hilclaw.local_run.run`; ``timeout_s``, ``cwd`` and ``env`` are
    handed over unchanged. ``prefix`` is ``(program,)`` for a ``str`` or
    :class:`os.PathLike` ``program``, or else ``program`` itself, a non-empty
    sequence. Every path is handed over as the ``str`` of :func:`os.fspath`.
    ``libraries`` is a non-empty sequence of ``str`` or :class:`os.PathLike`;
    library ``i`` is the kernel of index ``i``. ``shapes`` holds the
    ``(m, n)`` of each call of the input file, in order, as
    :func:`output_shapes` gives them. ``dtype``, one of :data:`DTYPES`, must
    be the dtype of the program's build, which this function cannot see; it
    gives the element dtype of the report and of the outputs, as in
    :func:`parse_report`.

    The run failed with :attr:`RunFailed.TIMEOUT` if it timed out, else with
    :attr:`RunFailed.EXIT_STATUS` if its status is not 0, else with
    :attr:`RunFailed.REPORT_FORM` if :func:`parse_report` finds no complete
    report in its standard output.

    Raised before anything is started, ``dtype`` first: for ``dtype``
    :class:`TypeError` for a type other than ``str`` and :class:`ValueError`
    for a name outside :data:`DTYPES`; for ``shapes`` :class:`TypeError` for
    a type other than stated and :class:`ValueError` for an empty sequence or
    a dimension below 1; for ``program``, ``input_file`` and ``libraries``
    :class:`TypeError` for a ``bytes`` path, a path that is neither ``str``
    nor :class:`os.PathLike`, a ``program`` that is neither a path nor a
    sequence or a ``libraries`` that is one ``str`` or no sequence, and
    :class:`ValueError` for an empty ``program`` sequence or no libraries.
    What :func:`hilclaw.local_run.run` raises is passed on unchanged.
    """
    element = _checked_dtype(dtype)
    checked = _checked_shapes(shapes)
    if isinstance(program, (str, os.PathLike)):
        prefix = (_path(program, "program"),)
    else:
        if not _is_sequence(program):
            raise TypeError(
                f"program: must be a path or a sequence, got {type(program).__name__}"
            )
        if not program:
            raise ValueError("program: command prefix is empty")
        prefix = tuple(
            _path(part, f"program[{position}]") for position, part in enumerate(program)
        )
    input_path = _path(input_file, "input_file")
    if not _is_sequence(libraries):
        raise TypeError(
            f"libraries: must be a sequence of paths, got {type(libraries).__name__}"
        )
    if not libraries:
        raise ValueError("libraries: no library")
    library_paths = tuple(
        _path(library, f"libraries[{position}]")
        for position, library in enumerate(libraries)
    )
    run = local_run.run(
        (*prefix, input_path, *library_paths), timeout_s=timeout_s, cwd=cwd, env=env
    )
    report = run.stdout
    run = run._replace(stdout=b"")
    if run.timed_out:
        return ModelProgramResult(RunFailed.TIMEOUT, None, run)
    if run.returncode != 0:
        return ModelProgramResult(RunFailed.EXIT_STATUS, None, run)
    outputs = _outputs(report, checked, element)
    if outputs is None:
        return ModelProgramResult(RunFailed.REPORT_FORM, None, run)
    return ModelProgramResult(None, outputs, run)


def _is_sequence(value):
    return isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    )


def _path(value, name):
    if isinstance(value, (bytes, bytearray)):
        raise TypeError(f"{name}: a bytes path is refused")
    if not isinstance(value, (str, os.PathLike)):
        raise TypeError(
            f"{name}: must be str or os.PathLike, got {type(value).__name__}"
        )
    path = os.fspath(value)
    if not isinstance(path, str):
        raise TypeError(f"{name}: a bytes path is refused")
    return path


def _checked_dtype(dtype):
    if not isinstance(dtype, str):
        raise TypeError(f"dtype: must be str, got {type(dtype).__name__}")
    if dtype not in DTYPES:
        raise ValueError(f"dtype: {dtype!r} is not one of {DTYPES}")
    return _ELEMENTS[dtype]


def _checked_calls(calls, dtype, element):
    if not _is_sequence(calls):
        raise TypeError(f"calls: must be a sequence, got {type(calls).__name__}")
    if not calls:
        raise ValueError("calls: no call")
    checked = []
    for position, entry in enumerate(calls):
        name = f"calls[{position}]"
        if not isinstance(entry, (tuple, list)) or len(entry) != 3:
            raise TypeError(f"{name}: must be a tuple or list (index, a, b)")
        index, a, b = entry
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError(f"{name}: index must be int, got {type(index).__name__}")
        if not 0 <= index < _UINT64_LIMIT:
            raise ValueError(f"{name}: index {index} is outside [0, 2**64)")
        for label, array in (("a", a), ("b", b)):
            if not isinstance(array, np.ndarray):
                raise TypeError(
                    f"{name}: {label} must be numpy.ndarray, got {type(array).__name__}"
                )
            if array.dtype != element:
                raise ValueError(
                    f"{name}: {label} has dtype {array.dtype}, not {element} "
                    f"of dtype {dtype}"
                )
            if array.ndim != 2:
                raise ValueError(f"{name}: {label} has {array.ndim} dimensions, not 2")
            if 0 in array.shape:
                raise ValueError(f"{name}: {label} has a zero dimension {array.shape}")
        if a.shape[1] != b.shape[0]:
            raise ValueError(
                f"{name}: inner dimensions differ, a {a.shape} and b {b.shape}"
            )
        checked.append((index, a, b))
    return checked


def _checked_shapes(shapes):
    if not _is_sequence(shapes):
        raise TypeError(f"shapes: must be a sequence, got {type(shapes).__name__}")
    if not shapes:
        raise ValueError("shapes: no shape")
    checked = []
    for position, shape in enumerate(shapes):
        name = f"shapes[{position}]"
        if not isinstance(shape, (tuple, list)) or len(shape) != 2:
            raise TypeError(f"{name}: must be a tuple or list (m, n)")
        for dimension in shape:
            if isinstance(dimension, bool) or not isinstance(dimension, int):
                raise TypeError(
                    f"{name}: dimension must be int, got {type(dimension).__name__}"
                )
            if dimension < 1:
                raise ValueError(f"{name}: dimension {dimension} is below 1")
        checked.append((shape[0], shape[1]))
    return tuple(checked)


def _outputs(report, shapes, element):
    size = element.itemsize
    expected = sum(size * m * n for m, n in shapes) + len(END_MARK)
    if len(report) != expected or not report.endswith(END_MARK):
        return None
    outputs = []
    offset = 0
    for m, n in shapes:
        array = np.frombuffer(report, dtype=element, count=m * n, offset=offset)
        outputs.append(array.reshape(m, n).copy())
        offset += size * m * n
    return tuple(outputs)
