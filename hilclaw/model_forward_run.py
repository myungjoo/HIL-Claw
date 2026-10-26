"""Host side's input, run and report of the forward program of ADR-0166.

``ARCHITECTURE/decisions/ADR-0166-od31-bf16-forward-pass.md`` is the rule:
decision 4 says what the host side hands over and who makes it, and decision 7
fixes the given-sequence mode and the report. The header comment of
``model_forward.c`` defines the program's command line, its input file, its
library table, its report, the end mark and its exit statuses; this module
speaks exactly that form. :func:`encode_input` turns the dimensions, ``eps``,
the RoPE constants, the weights, the prompt, the given tokens, ``lm_head_rows``
and the per-pass library table into the bytes of the input file, building the
RoPE table with :func:`hilclaw.rope_table.build` for positions 0 to S + G - 2
and converting ``eps`` with :func:`hilclaw.model_binding.rmsnorm_eps`;
:func:`run_forward_program` starts the program once with its libraries under
a time limit; and :func:`parse_report` reads a complete report into the token
ids and the logits rows. A run that times out, ends with a status other than 0
or leaves no complete report is the outcome **run failed** of ADR-0153
decision 5, named by :class:`hilclaw.model_run.RunFailed`, which this module
reuses.

The command is::

    <program or command prefix...> <input file> <library> [<library> ...]

Conventions of this module (not rules of the record):

- ``libraries`` of :func:`encode_input` maps each of the fifteen names of
  :data:`CALL_SITES` to its library index at each pass, pass 0 the prefill:
  the table of ``model_forward.c`` as it is, not a per-shape mapping.
  Turning a binding into it is left to the caller.
- The arguments :func:`encode_input` shares with
  :func:`hilclaw.model_forward_check.check` are checked by that function, at
  the dtype ``"bf16"``, with ``generation_length`` the length of ``given``
  and no binding: what it raises is passed on, and its ``"invalid_input"``
  reasons, joined with ``"; "``, are raised as one :class:`ValueError`. Its
  outcomes for the missing binding are not looked at.
- The length of a complete report is computed from the arguments alone and
  compared before any byte is read; nothing is allocated from the report's
  length. Each array of a :class:`ForwardReport` is fresh and owns its memory.
- ``run`` of a :class:`ForwardProgramResult` is what the runner captured
  apart from the report: its ``stdout`` is replaced by ``b""``.
- ``program`` is a path or a sequence used as a command prefix, as in
  :func:`hilclaw.model_run.run_model_program`.
- Arguments outside what is stated raise :class:`TypeError` or
  :class:`ValueError` before anything is encoded or started, with a message
  that names the argument. What :func:`hilclaw.local_run.run` raises is
  passed on.

What this module does not do: it checks no binding of a kernel to a call site
and builds nothing; it has no generation mode or token selection rule (ADR-0176
decision 5, a later code slice) and no model-level reference or tolerance,
which are :mod:`hilclaw.model_reference`'s (ADR-0176); it gives no
RoPE constant, model parameter or time limit a default (HQ-0070); it places no
directory and chooses no input path, container or environment; it casts no
array; and it stores or retries nothing.
"""

import os
from collections.abc import Mapping
from typing import NamedTuple

import numpy as np

from hilclaw import local_run, model_binding, model_forward_check, rope_table
from hilclaw.model_run import END_MARK, RunFailed, _is_sequence, _path

CALL_SITES = (
    model_binding.CALL_SITES
    + model_binding.RMSNORM_CALL_SITES
    + model_binding.ELEMENTWISE_ADD_CALL_SITES
    + model_binding.SWIGLU_CALL_SITES
    + model_binding.ROPE_CALL_SITES
    + model_binding.SDPA_CALL_SITES
)
"""The fifteen call sites in the order of the library table of ``model_forward.c``."""

_UINT64_LIMIT = 2**64
_PER_LAYER = ("attention_norm", "qkv", "o", "ffn_norm", "gate", "up", "down")


class ForwardReport(NamedTuple):
    """A complete report: ``tokens``, the S + G token ids as ``numpy.uint64``, and ``logits``, a ``numpy.uint16`` array of bf16 patterns of shape (rows, V).

    The rows are those of each pass in pass order: S + G - 1 for ``"all"``,
    G for ``"last"``.
    """

    tokens: np.ndarray
    logits: np.ndarray


class ForwardProgramResult(NamedTuple):
    """Outcome of one :func:`run_forward_program` call.

    For a run that did not time out, ended with status 0 and left a complete
    report, ``failed`` is ``None`` and ``report`` is its
    :class:`ForwardReport`. For any other run ``failed`` names the failed
    condition and ``report`` is ``None``. ``run`` is what the runner captured
    with an empty ``stdout``, in both cases.
    """

    failed: RunFailed | None
    report: ForwardReport | None
    run: local_run.RunResult


def encode_input(
    dimensions,
    *,
    eps,
    rope,
    weights,
    prompt,
    given,
    lm_head_rows,
    libraries,
    library_count,
):
    """Return the bytes of the forward program's input file for one generation.

    ``dimensions`` is a :class:`hilclaw.model_binding.ModelDimensions`;
    ``eps`` is exactly a ``float``; ``rope`` is a
    :class:`hilclaw.model_forward_check.RopeConstants`; ``weights`` is a
    :class:`hilclaw.model_forward_check.Weights` of ``numpy.uint16`` arrays;
    ``prompt`` and ``given`` are sequences of ``int`` token ids, G the length
    of ``given``; ``lm_head_rows`` is ``"all"`` or ``"last"``;
    ``library_count`` is the number of libraries the program will be given,
    an ``int`` from 1 to 2**64 - 1; ``libraries`` maps each name of
    :data:`CALL_SITES`, and no other key, to a sequence of G ``int`` library
    indices from 0 to ``library_count`` - 1, entry p for pass p. No argument
    has a default.

    The bytes are those of the header comment of ``model_forward.c``: the ten
    header integers, ``rmsnorm_eps(eps)`` as binary32, the library table
    (entry s*G + p for call site s at pass p), the RoPE table of
    ``rope_table.build(head_dim=d, positions=S + G - 1, ...)``, the prompt and
    the given tokens, then the weights in the order of that comment, each in
    row-major order whatever its memory order.

    Raised before any byte is built: :class:`ValueError` for ``given`` that
    is ``None`` (the generation mode) and :class:`TypeError` for ``given``
    that is no sequence; then what :func:`hilclaw.model_forward_check.check`
    raises, and :class:`ValueError` with its ``"invalid_input"`` reasons;
    then :class:`TypeError` or :class:`ValueError` for ``library_count`` and
    for ``libraries``: not a mapping, a missing or unknown call site, a value
    that is no sequence or not of G entries, an entry that is not an ``int``
    or out of range.
    """
    if given is None:
        raise ValueError(
            "given: is None; the generation mode has no token selection rule "
            "(OD-31 sub-question 6)"
        )
    if not _is_sequence(given):
        raise TypeError(f"given: must be a sequence, got {type(given).__name__}")
    passes = len(given)
    result = model_forward_check.check(
        dimensions,
        {},
        dtype="bf16",
        eps=eps,
        rope=rope,
        weights=weights,
        prompt=prompt,
        given=given,
        generation_length=passes,
        lm_head_rows=lm_head_rows,
    )
    reasons = [
        outcome.reason
        for outcome in result.outcomes
        if outcome.kind == model_binding.INVALID_INPUT
    ]
    if reasons:
        raise ValueError("; ".join(reasons))
    table = _library_table(libraries, passes, library_count)
    d = dimensions
    header = (
        d.hidden,
        d.intermediate,
        d.vocabulary,
        d.layers,
        d.heads,
        d.kv_heads,
        d.head_dim,
        len(prompt),
        passes,
        0 if lm_head_rows == "all" else 1,
    )
    table_of_rope = rope_table.build(
        head_dim=d.head_dim, positions=len(prompt) + passes - 1, **rope._asdict()
    )
    parts = [
        np.array(header, dtype=np.uint64).tobytes(),
        np.array([model_binding.rmsnorm_eps(eps)], dtype=np.float32).tobytes(),
        np.array(table, dtype=np.uint64).tobytes(),
        table_of_rope.tobytes(),
        np.array([*prompt, *given], dtype=np.uint64).tobytes(),
        weights.embedding.tobytes(order="C"),
    ]
    for layer in range(d.layers):
        for name in _PER_LAYER:
            parts.append(getattr(weights, name)[layer].tobytes(order="C"))
    parts += [weights.norm.tobytes(order="C"), weights.lm_head.tobytes(order="C")]
    return b"".join(parts)


def parse_report(report, dimensions, *, prompt_length, generation_length, lm_head_rows):
    """Return the :class:`ForwardReport` of a complete report, or ``None``.

    With S = ``prompt_length``, G = ``generation_length``, V the vocabulary
    and rows S + G - 1 for ``lm_head_rows`` ``"all"`` and G for ``"last"``, a
    complete report is exactly 8*(S + G) + 2*rows*V bytes followed by
    :data:`hilclaw.model_run.END_MARK`. Any other report gives ``None``.
    Nothing is started or written.

    Raised before any byte of ``report`` is looked at: what
    :func:`hilclaw.model_binding.generation_calls` raises for ``dimensions``,
    ``prompt_length``, ``generation_length`` and ``lm_head_rows``, then
    :class:`TypeError` for a ``report`` that is not exactly ``bytes``.
    """
    rows = _rows(dimensions, prompt_length, generation_length, lm_head_rows)
    if type(report) is not bytes:
        raise TypeError(f"report: must be bytes, got {type(report).__name__}")
    return _report(report, prompt_length + generation_length, rows, dimensions)


def run_forward_program(
    program,
    input_file,
    libraries,
    *,
    dimensions,
    prompt_length,
    generation_length,
    lm_head_rows,
    timeout_s,
    cwd=None,
    env=None,
):
    """Run the forward program once and return a :class:`ForwardProgramResult`.

    One process ``(*prefix, input_file, *libraries)`` is started with
    :func:`hilclaw.local_run.run`; ``timeout_s``, ``cwd`` and ``env`` are
    handed over unchanged. ``prefix`` is ``(program,)`` for a ``str`` or
    :class:`os.PathLike` ``program``, or else ``program`` itself, a non-empty
    sequence. Every path is handed over as the ``str`` of :func:`os.fspath`.
    ``libraries`` is a non-empty sequence of ``str`` or :class:`os.PathLike`;
    library ``i`` has index ``i`` in the input's library table. The input file
    is the caller's, placed before the call. ``dimensions``,
    ``prompt_length``, ``generation_length`` and ``lm_head_rows`` are those
    the input file was encoded with; they give the report's length as in
    :func:`parse_report`.

    The run failed with :attr:`RunFailed.TIMEOUT` if it timed out, else with
    :attr:`RunFailed.EXIT_STATUS` if its status is not 0, else with
    :attr:`RunFailed.REPORT_FORM` if :func:`parse_report` finds no complete
    report in its standard output.

    Raised before anything is started: what :func:`parse_report` raises for
    its arguments; for ``program``, ``input_file`` and ``libraries``
    :class:`TypeError` for a ``bytes`` path, a path that is neither ``str``
    nor :class:`os.PathLike`, a ``program`` that is neither a path nor a
    sequence or a ``libraries`` that is one ``str`` or no sequence, and
    :class:`ValueError` for an empty ``program`` sequence or no libraries.
    What :func:`hilclaw.local_run.run` raises is passed on unchanged.
    """
    rows = _rows(dimensions, prompt_length, generation_length, lm_head_rows)
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
    stdout = run.stdout
    run = run._replace(stdout=b"")
    if run.timed_out:
        return ForwardProgramResult(RunFailed.TIMEOUT, None, run)
    if run.returncode != 0:
        return ForwardProgramResult(RunFailed.EXIT_STATUS, None, run)
    report = _report(stdout, prompt_length + generation_length, rows, dimensions)
    if report is None:
        return ForwardProgramResult(RunFailed.REPORT_FORM, None, run)
    return ForwardProgramResult(None, report, run)


def _library_table(libraries, passes, library_count):
    if isinstance(library_count, bool) or not isinstance(library_count, int):
        raise TypeError(
            f"library_count: must be an int, got {type(library_count).__name__}"
        )
    if not 1 <= library_count < _UINT64_LIMIT:
        raise ValueError(
            f"library_count: must be from 1 to 2**64 - 1, got {library_count}"
        )
    if not isinstance(libraries, Mapping):
        raise TypeError(f"libraries: must be a mapping, got {type(libraries).__name__}")
    for site in libraries:
        if site not in CALL_SITES:
            raise ValueError(f"libraries: key {site!r} is not a call site")
    table = []
    for site in CALL_SITES:
        if site not in libraries:
            raise ValueError(f"libraries: no entry for the call site {site!r}")
        indices = libraries[site]
        if not _is_sequence(indices):
            raise TypeError(
                f"libraries[{site!r}]: must be a sequence, got {type(indices).__name__}"
            )
        if len(indices) != passes:
            raise ValueError(
                f"libraries[{site!r}]: has {len(indices)} entries, not one per pass ({passes})"
            )
        for p, index in enumerate(indices):
            if isinstance(index, bool) or not isinstance(index, int):
                raise TypeError(
                    f"libraries[{site!r}][{p}]: must be an int, got {type(index).__name__}"
                )
            if not 0 <= index < library_count:
                raise ValueError(
                    f"libraries[{site!r}][{p}]: index {index} is outside 0 to {library_count - 1}"
                )
        table.extend(indices)
    return table


def _rows(dimensions, prompt_length, generation_length, lm_head_rows):
    model_binding.generation_calls(
        dimensions,
        prompt_length=prompt_length,
        generation_length=generation_length,
        lm_head_rows=lm_head_rows,
    )
    if lm_head_rows == "last":
        return generation_length
    return prompt_length + generation_length - 1


def _report(report, token_count, rows, dimensions):
    vocabulary = dimensions.vocabulary
    expected = 8 * token_count + 2 * rows * vocabulary + len(END_MARK)
    if len(report) != expected or not report.endswith(END_MARK):
        return None
    tokens = np.frombuffer(report, dtype=np.uint64, count=token_count).copy()
    logits = np.frombuffer(
        report, dtype=np.uint16, count=rows * vocabulary, offset=8 * token_count
    )
    return ForwardReport(tokens, logits.reshape(rows, vocabulary).copy())
