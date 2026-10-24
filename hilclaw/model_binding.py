"""Host-side binding check of the model executor for the GEMM call sites (ADR-0153, code slice 1, first half).

``ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`` is the rule. Before
anything is built, the host side derives the shapes of every kernel call of a
generation from the model dimensions and the run settings and checks the
binding against them (decision 5). This module does that for the six GEMM
call sites of ADR-0152 decision 2 (:data:`CALL_SITES`). The model's dtype
(``ARCHITECTURE/decisions/ADR-0157-od31-executor-call-site-dtype.md``,
decisions 1 to 4) selects the ``gemm`` contract every entry is fitted
against: ADR-0008's (:mod:`hilclaw.gemm_contract`) for ``fp32`` and
ADR-0156's (:mod:`hilclaw.gemm_bf16_contract`) for ``bf16``
(:data:`DTYPES`). Its parts:

* :class:`ModelDimensions` and :func:`check_dimensions`: the model parameters
  of ADR-0153 decision 3 (a) that the GEMM shapes use. No value is a default
  and none of Llama 3.2 1B is assumed (decision 6).
* :func:`gemm_shape`: the ``(m, k, n)`` of one call site in a pass of ``rows``
  rows, from Meta's ``model.py`` as ADR-0152 (Context, decision 5) reads it.
* :func:`generation_calls`: the distinct shapes of each call site over one
  generation (ADR-0153 decision 4).
* :class:`KernelReference`, :class:`BindingEntry`: a binding entry (decision 3).
* :func:`check`: the outcomes ``"invalid_input"``, ``"no_kernel"`` and
  ``"kernel_unfit"`` (decision 5, whose spelling is left to the code slice),
  and the calls of the generation with the kernel each one is bound to.

Readings of this module:

* A generation is one prefill pass with ``prompt_length`` rows, which gives
  the first token after the prompt, then ``generation_length - 1`` decode
  passes of one row, one for each further token (decision 4). In the
  given-sequence mode the passes are the same; the given tokens only have to
  be valid token ids.
* Two entries of one call site that cover a common shape make the binding
  malformed, and an ``"every"`` entry overlaps every other entry of its call
  site: the executor never chooses between kernels (decision 3).
* A listed shape other than the shape of the kernel's own spec, and an
  ``"every"`` entry, are accepted at both dtypes: a kernel of either
  ``gemm`` contract must compute the product for the values it is called with
  (ADR-0008 decision 6, ADR-0156 decision 7, ADR-0157 decision 3). So the
  operand shapes of a ``task.contract`` are not compared.

What this module does not do: it builds, loads and starts nothing and runs no
process; it reads and writes no file; it has no command-line entry, registry
or MCP tool; it knows no call site of RMSNorm, RoPE, SDPA, SwiGLU or
elementwise add, no contract other than the fp32 and bf16 ``gemm`` contracts
and no dtype outside :data:`DTYPES`; it reads no weight and adds no cast; it
does not interpret the build flags of a kernel reference; and it
derives no binding from a key's best (OD-20, OD-7).

Every :class:`TypeError` or :class:`ValueError` raised here for an argument
carries the attribute ``parameter``, the name of that argument. Arguments are
not modified.
"""

import contextlib
import os
import re
from collections.abc import Mapping, Sequence
from typing import NamedTuple

from hilclaw import gemm_bf16_contract, gemm_contract, keys

CALL_SITES = ("qkv", "o", "gate", "up", "down", "lm_head")
"""The GEMM call sites, ADR-0152 decision 2 rows 3, 8, 11 (gate and up), 13 and 16."""

DTYPES = (gemm_contract.DTYPE, gemm_bf16_contract.DTYPE)
"""The dtypes at which the ``gemm`` contract is known, the range of the model's dtype (ADR-0157 decision 4)."""

LM_HEAD_ROWS = ("all", "last")

INVALID_INPUT = "invalid_input"
NO_KERNEL = "no_kernel"
KERNEL_UNFIT = "kernel_unfit"

_CONTRACTS = dict(zip(DTYPES, (gemm_contract, gemm_bf16_contract)))
_DTYPE_NAME = re.compile(r"[a-z][a-z0-9_]{0,31}")


class ModelDimensions(NamedTuple):
    """The model parameters the GEMM shapes depend on (ADR-0153 decision 3 (a))."""

    hidden: int
    intermediate: int
    vocabulary: int
    layers: int
    heads: int
    kv_heads: int
    head_dim: int


class KernelReference(NamedTuple):
    """A kernel: its source paths, the ``task.contract`` of its spec, and its build flags (not interpreted)."""

    sources: tuple
    contract: object
    flags: tuple


class BindingEntry(NamedTuple):
    """A kernel bound for ``shapes``: ``"every"`` or a non-empty tuple of ``(m, k, n)``."""

    kernel: KernelReference
    shapes: object


class Outcome(NamedTuple):
    """One outcome of :func:`check`; ``reason`` is always a ``str``."""

    kind: str
    call_site: object
    shape: object
    reason: str


class BindingCheck(NamedTuple):
    """The result of :func:`check`: ``ok`` exactly when ``outcomes`` is empty."""

    ok: bool
    outcomes: tuple
    calls: tuple


def check_dimensions(dimensions):
    """Refuse ``dimensions`` that are not valid model dimensions; return ``None``.

    ``dimensions`` is a :class:`ModelDimensions` whose every field is exactly
    an ``int`` (``bool`` refused) from 1 to :data:`hilclaw.keys.MAX_INTEGER`,
    with ``heads`` a multiple of ``kv_heads`` (ADR-0153 decision 6; Meta's
    assert, ADR-0152 Context), and with the QKV width ``(heads + 2 * kv_heads)
    * head_dim`` no larger than that bound either (so ``heads * head_dim``,
    the O width, is no larger as well).
    Raises :class:`TypeError` for a wrong type and :class:`ValueError`
    otherwise, with ``parameter`` ``"dimensions"``.
    """
    with _parameter("dimensions"):
        if not isinstance(dimensions, ModelDimensions):
            raise TypeError(
                f"must be a ModelDimensions, got {type(dimensions).__name__}"
            )
        for name, value in zip(ModelDimensions._fields, dimensions):
            _integer(value, name)
        if dimensions.heads % dimensions.kv_heads:
            raise ValueError("heads must be a multiple of kv_heads")
        qkv_width = (dimensions.heads + 2 * dimensions.kv_heads) * dimensions.head_dim
        if qkv_width > keys.MAX_INTEGER:
            raise ValueError("(heads + 2 * kv_heads) * head_dim exceeds 2**53 - 1")


def gemm_shape(dimensions, call_site, rows):
    """Return the ``(m, k, n)`` of ``call_site`` in a pass of ``rows`` rows, with ``m`` = ``rows``.

    ``(k, n)`` is ``(hidden, (heads + 2 * kv_heads) * head_dim)`` for
    ``"qkv"``, ``(heads * head_dim, hidden)`` for ``"o"``, ``(hidden,
    intermediate)`` for ``"gate"`` and ``"up"``, ``(intermediate, hidden)``
    for ``"down"`` and ``(hidden, vocabulary)`` for ``"lm_head"``. Raises as
    :func:`check_dimensions` does, then :class:`ValueError` with ``parameter``
    ``"call_site"`` for a call site not in :data:`CALL_SITES`, then
    :class:`TypeError` or :class:`ValueError` with ``parameter`` ``"rows"``
    for ``rows`` that is not an ``int`` from 1 to 2**53 - 1.
    """
    check_dimensions(dimensions)
    with _parameter("call_site"):
        if call_site not in CALL_SITES:
            raise ValueError(f"must be one of {CALL_SITES}, got {call_site!r}")
    with _parameter("rows"):
        _integer(rows, "rows")
    d = dimensions
    k, n = {
        "qkv": (d.hidden, (d.heads + 2 * d.kv_heads) * d.head_dim),
        "o": (d.heads * d.head_dim, d.hidden),
        "gate": (d.hidden, d.intermediate),
        "up": (d.hidden, d.intermediate),
        "down": (d.intermediate, d.hidden),
        "lm_head": (d.hidden, d.vocabulary),
    }[call_site]
    return (rows, k, n)


def generation_calls(dimensions, *, prompt_length, generation_length, lm_head_rows):
    """Return, per call site in :data:`CALL_SITES` order, the sorted tuple of distinct shapes of a generation.

    The generation is one prefill pass of ``prompt_length`` rows and then
    ``generation_length - 1`` decode passes of one row (the module's reading of
    ADR-0153 decision 4). ``lm_head_rows`` ``"all"`` gives lm_head the rows of
    each pass, ``"last"`` one row in every pass. The result is a tuple of
    ``(call_site, shapes)`` pairs. Raises as :func:`check_dimensions`, then
    :class:`TypeError` or :class:`ValueError` with the argument's name as
    ``parameter``: ``prompt_length`` and ``generation_length`` are ``int``
    from 1 to 2**53 - 1, ``lm_head_rows`` is ``"all"`` or ``"last"``.
    """
    check_dimensions(dimensions)
    for name, value in (
        ("prompt_length", prompt_length),
        ("generation_length", generation_length),
    ):
        with _parameter(name):
            _integer(value, name)
    with _parameter("lm_head_rows"):
        _lm_head_rows(lm_head_rows)
        if lm_head_rows not in LM_HEAD_ROWS:
            raise ValueError(f"must be one of {LM_HEAD_ROWS}, got {lm_head_rows!r}")
    rows = {prompt_length, 1} if generation_length > 1 else {prompt_length}
    result = []
    for site in CALL_SITES:
        site_rows = {1} if site == "lm_head" and lm_head_rows == "last" else rows
        result.append(
            (site, tuple(sorted(gemm_shape(dimensions, site, r) for r in site_rows)))
        )
    return tuple(result)


def check(
    dimensions, binding, *, dtype, prompt, generation_length, lm_head_rows, given=None
):
    """Check ``binding`` against every GEMM call of a generation; return a :class:`BindingCheck`.

    ``prompt`` is a sequence of token ids; ``given`` is ``None`` (generation
    mode) or a sequence of ``generation_length`` token ids (given-sequence
    mode). ``binding`` maps call sites of :data:`CALL_SITES` to non-empty
    sequences of :class:`BindingEntry`. A token id is exactly an ``int``.
    ``dtype`` is the model's dtype (ADR-0157 decision 1); it has no default.

    Arguments are first refused, in the order ``dimensions``, ``dtype``,
    ``prompt``, ``given``, ``generation_length``, ``lm_head_rows``,
    ``binding``, with :class:`TypeError` for a wrong type (``dtype`` is
    exactly a ``str``; a ``str`` or ``bytes`` is no sequence here) and, for
    ``dimensions``, a ``dtype`` that is not a name of ADR-0001's ``dtype``
    field (``[a-z][a-z0-9_]{0,31}``) and a malformed ``binding``,
    :class:`ValueError`; ``parameter`` is the argument's name. ``binding`` is
    malformed when a key is not in :data:`CALL_SITES`, a sequence of entries
    is empty, a kernel reference has no source or a source that is not a
    ``str`` or :class:`os.PathLike`, a flag is not a ``str``, ``shapes`` is
    neither ``"every"`` nor a non-empty tuple of ``(m, k, n)`` triples of
    ``int`` from 1 to 2**53 - 1, or two entries of one call site overlap.

    The outcomes then come in this order:

    1. ``"invalid_input"`` (``call_site`` and ``shape`` ``None``): a
       ``dtype`` not in :data:`DTYPES`, at which no ``gemm`` contract is
       known (ADR-0157 decision 4); an empty ``prompt``; each token id of
       ``prompt`` outside 0 to ``vocabulary - 1``, in order;
       ``generation_length`` outside 1 to 2**53 - 1; ``lm_head_rows`` not
       ``"all"`` or ``"last"``; ``given`` of a length other than
       ``generation_length`` (looked at only when that is valid); each token
       id of ``given`` outside the vocabulary, in order.
    2. Per call site in :data:`CALL_SITES` order: ``"kernel_unfit"``
       (``shape`` ``None``) for each entry, in order, whose ``contract`` is
       not the ``gemm`` contract ``dtype`` selects, compared on ``language``,
       ``prototype`` and the operands' ``(name, role, dtype)`` (ADR-0153
       decision 3 "Fit", ADR-0008 decision 8, ADR-0157 decisions 2 and 3;
       reference values from :func:`hilclaw.gemm_contract.task_contract` for
       ``fp32`` and :func:`hilclaw.gemm_bf16_contract.task_contract` for
       ``bf16``, never from the entry's own contract); then ``"no_kernel"``
       for each shape of :func:`generation_calls`, in order, that no entry
       covers. The ``"no_kernel"`` outcomes are not looked for when there is
       an ``"invalid_input"``, and neither kind is when ``dtype`` is not in
       :data:`DTYPES`.

    ``calls`` holds ``(call_site, shape, kernel)`` for every call of
    :func:`generation_calls`, in its order, only when ``ok``; it is empty
    otherwise. Nothing is built, started or read.
    """
    check_dimensions(dimensions)
    with _parameter("dtype"):
        _dtype(dtype)
    prompt = _token_ids(prompt, "prompt")
    if given is not None:
        given = _token_ids(given, "given")
    with _parameter("generation_length"):
        if type(generation_length) is not int:
            raise TypeError(f"must be an int, got {type(generation_length).__name__}")
    with _parameter("lm_head_rows"):
        _lm_head_rows(lm_head_rows)
    binding = _binding(binding)

    known = dtype in DTYPES
    invalid = [] if known else [_no_contract(dtype)]
    invalid += _invalid_inputs(
        dimensions, prompt, generation_length, lm_head_rows, given
    )
    outcomes = [Outcome(INVALID_INPUT, None, None, reason) for reason in invalid]
    shapes = {}
    if not invalid:
        shapes = dict(
            generation_calls(
                dimensions,
                prompt_length=len(prompt),
                generation_length=generation_length,
                lm_head_rows=lm_head_rows,
            )
        )
    calls = []
    for site in CALL_SITES if known else ():
        entries = binding.get(site, ())
        for index, entry in enumerate(entries):
            reason = _unfit(entry.kernel.contract, dtype)
            if reason is not None:
                outcomes.append(
                    Outcome(KERNEL_UNFIT, site, None, f"entry {index}: {reason}")
                )
        for shape in shapes.get(site, ()):
            kernel = next(
                (e.kernel for e in entries if e.shapes == "every" or shape in e.shapes),
                None,
            )
            if kernel is None:
                outcomes.append(
                    Outcome(
                        NO_KERNEL,
                        site,
                        shape,
                        "no entry of the binding covers the shape",
                    )
                )
            else:
                calls.append((site, shape, kernel))
    ok = not outcomes
    return BindingCheck(ok, tuple(outcomes), tuple(calls) if ok else ())


def _invalid_inputs(dimensions, prompt, generation_length, lm_head_rows, given):
    vocabulary = dimensions.vocabulary
    reasons = [] if prompt else ["prompt: is empty"]
    reasons += _out_of_vocabulary(prompt, vocabulary, "prompt")
    length_valid = 1 <= generation_length <= keys.MAX_INTEGER
    if not length_valid:
        reasons.append(
            f"generation_length: must be from 1 to 2**53 - 1, got {generation_length}"
        )
    if lm_head_rows not in LM_HEAD_ROWS:
        reasons.append(
            f"lm_head_rows: must be one of {LM_HEAD_ROWS}, got {lm_head_rows!r}"
        )
    if given is not None:
        if length_valid and len(given) != generation_length:
            reasons.append(
                f"given: has {len(given)} token ids, generation_length is {generation_length}"
            )
        reasons += _out_of_vocabulary(given, vocabulary, "given")
    return reasons


def _out_of_vocabulary(token_ids, vocabulary, name):
    return [
        f"{name}[{index}]: token id {token} is outside 0 to {vocabulary - 1}"
        for index, token in enumerate(token_ids)
        if not 0 <= token < vocabulary
    ]


def _no_contract(dtype):
    return f"dtype: no gemm contract is known at the dtype {dtype!r}"


def _unfit(contract, dtype):
    reference = _CONTRACTS[dtype].task_contract(1, 1, 1)
    if not isinstance(contract, Mapping):
        return f"contract is not a mapping, got {type(contract).__name__}"
    for member in ("language", "prototype", "operands"):
        if member not in contract:
            return f"contract lacks the member {member!r}"
    for member in ("language", "prototype"):
        if not _same_text(contract[member], reference[member]):
            return f"contract.{member} is not that of the {dtype} gemm contract"
    operands = contract["operands"]
    if not isinstance(operands, Sequence) or isinstance(operands, (str, bytes)):
        return "contract.operands is not a sequence"
    if len(operands) != len(reference["operands"]):
        return f"contract.operands has {len(operands)} entries, not {len(reference['operands'])}"
    for index, (operand, expected) in enumerate(zip(operands, reference["operands"])):
        if not isinstance(operand, Mapping):
            return f"contract.operands[{index}] is not a mapping"
        for member in ("name", "role", "dtype"):
            if member not in operand:
                return f"contract.operands[{index}] lacks the member {member!r}"
            if not _same_text(operand[member], expected[member]):
                return f"contract.operands[{index}].{member} is not that of the {dtype} gemm contract"
    return None


def _same_text(value, expected):
    return isinstance(value, str) and value == expected


def _binding(binding):
    with _parameter("binding"):
        if not isinstance(binding, Mapping):
            raise TypeError(f"must be a mapping, got {type(binding).__name__}")
        result = {}
        for site, entries in binding.items():
            if site not in CALL_SITES:
                raise ValueError(f"key {site!r} is not a call site of {CALL_SITES}")
            if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
                raise TypeError(f"{site}: must be a sequence of BindingEntry")
            entries = tuple(entries)
            if not entries:
                raise ValueError(f"{site}: has no entry")
            for entry in entries:
                _entry(entry, site)
            _no_overlap(entries, site)
            result[site] = entries
        return result


def _entry(entry, site):
    if not isinstance(entry, BindingEntry):
        raise TypeError(
            f"{site}: an entry is not a BindingEntry, got {type(entry).__name__}"
        )
    kernel = entry.kernel
    if not isinstance(kernel, KernelReference):
        raise TypeError(
            f"{site}: a kernel is not a KernelReference, got {type(kernel).__name__}"
        )
    if type(kernel.sources) is not tuple or type(kernel.flags) is not tuple:
        raise TypeError(f"{site}: kernel sources and flags must be tuples")
    if not kernel.sources:
        raise ValueError(f"{site}: a kernel has no source")
    if not all(isinstance(path, (str, os.PathLike)) for path in kernel.sources):
        raise TypeError(f"{site}: a kernel source is not a str or os.PathLike")
    if not all(isinstance(flag, str) for flag in kernel.flags):
        raise TypeError(f"{site}: a kernel flag is not a str")
    shapes = entry.shapes
    if isinstance(shapes, str):
        if shapes != "every":
            raise ValueError(
                f"{site}: shapes must be 'every' or a tuple of shapes, got {shapes!r}"
            )
        return
    if type(shapes) is not tuple:
        raise TypeError(f"{site}: shapes must be 'every' or a tuple of shapes")
    if not shapes:
        raise ValueError(f"{site}: shapes is empty")
    for shape in shapes:
        if type(shape) is not tuple:
            raise TypeError(f"{site}: a shape is not a tuple (m, k, n)")
        if len(shape) != 3:
            raise ValueError(f"{site}: a shape has {len(shape)} members, not 3")
        for value in shape:
            _integer(value, f"{site}: a shape member")


def _no_overlap(entries, site):
    if len(entries) == 1:
        return
    if any(entry.shapes == "every" for entry in entries):
        raise ValueError(f"{site}: an 'every' entry overlaps another entry")
    seen = set()
    for entry in entries:
        common = seen.intersection(entry.shapes)
        if common:
            raise ValueError(f"{site}: two entries cover the shape {min(common)}")
        seen.update(entry.shapes)


def _token_ids(token_ids, name):
    with _parameter(name):
        if not isinstance(token_ids, Sequence) or isinstance(token_ids, (str, bytes)):
            raise TypeError(
                f"must be a sequence of token ids, got {type(token_ids).__name__}"
            )
        token_ids = tuple(token_ids)
        for token in token_ids:
            if type(token) is not int:
                raise TypeError(f"a token id is not an int, got {type(token).__name__}")
        return token_ids


def _dtype(value):
    if type(value) is not str:
        raise TypeError(f"must be a str, got {type(value).__name__}")
    if not _DTYPE_NAME.fullmatch(value):
        raise ValueError(f"must match {_DTYPE_NAME.pattern}, got {value!r}")


def _lm_head_rows(value):
    if type(value) is not str:
        raise TypeError(f"must be a str, got {type(value).__name__}")


def _integer(value, name):
    if type(value) is not int:
        raise TypeError(f"{name}: must be an int, got {type(value).__name__}")
    if not 1 <= value <= keys.MAX_INTEGER:
        raise ValueError(f"{name}: must be from 1 to 2**53 - 1, got {value}")


@contextlib.contextmanager
def _parameter(name):
    try:
        yield
    except (TypeError, ValueError) as error:
        error.parameter = name
        raise
