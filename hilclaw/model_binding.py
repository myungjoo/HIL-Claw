"""Host-side binding checks of the model executor for the GEMM, RMSNorm, elementwise add, SwiGLU, RoPE and SDPA call sites (ADR-0153, ADR-0158 to ADR-0162).

``ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`` is the rule. Before
anything is built, the host side derives the shapes of every kernel call of a
generation from the model dimensions and the run settings and checks the
binding against them (decision 5). This module does that for the six GEMM
call sites of ADR-0152 decision 2 (:data:`CALL_SITES`) and, separately, for
its three RMSNorm call sites (:data:`RMSNORM_CALL_SITES`), its two
elementwise add call sites (:data:`ELEMENTWISE_ADD_CALL_SITES`), its
SwiGLU call site (:data:`SWIGLU_CALL_SITES`), its two RoPE call sites
(:data:`ROPE_CALL_SITES`) and its SDPA call site (:data:`SDPA_CALL_SITES`).
The model's dtype
(``ARCHITECTURE/decisions/ADR-0157-od31-executor-call-site-dtype.md``,
decisions 1 to 4) selects the contract every entry is fitted against: for the
GEMM call sites ADR-0008's ``gemm`` contract (:mod:`hilclaw.gemm_contract`)
for ``fp32`` and ADR-0156's (:mod:`hilclaw.gemm_bf16_contract`) for ``bf16``
(:data:`DTYPES`); for the RMSNorm call sites ADR-0158's ``rmsnorm`` contract
(:mod:`hilclaw.rmsnorm_bf16_contract`) for ``bf16``, the only dtype at which
one is defined (:data:`RMSNORM_DTYPES`); for the elementwise add call sites
ADR-0159's ``elementwise_add`` contract
(:mod:`hilclaw.elementwise_add_bf16_contract`) for ``bf16``, likewise the only
one (:data:`ELEMENTWISE_ADD_DTYPES`); for the SwiGLU call site ADR-0160's
``swiglu`` contract (:mod:`hilclaw.swiglu_bf16_contract`) for ``bf16``,
likewise the only one (:data:`SWIGLU_DTYPES`); for the RoPE call sites
ADR-0161's ``rope`` contract (:mod:`hilclaw.rope_bf16_contract`) for
``bf16``, likewise the only one (:data:`ROPE_DTYPES`); for the SDPA call site
ADR-0162's ``sdpa_kv_cache`` contract
(:mod:`hilclaw.sdpa_kv_cache_bf16_contract`) for ``bf16``, likewise the only
one (:data:`SDPA_DTYPES`). Its parts:

* :class:`ModelDimensions` and :func:`check_dimensions`: the model parameters
  of ADR-0153 decision 3 (a) that the shapes use. No value is a default and
  none of Llama 3.2 1B is assumed (decision 6).
* :func:`gemm_shape`: the ``(m, k, n)`` of one GEMM call site in a pass of
  ``rows`` rows, from Meta's ``model.py`` as ADR-0152 (Context, decision 5)
  reads it. :func:`rmsnorm_shape`, :func:`elementwise_add_shape` and
  :func:`swiglu_shape`: the ``(m, n)`` of one RMSNorm call site (ADR-0158
  decision 2) and of one elementwise add call site (ADR-0159 decision 2),
  whose ``n`` is the hidden width, and of the SwiGLU call site (ADR-0160
  decision 2), whose ``n`` is the intermediate width. :func:`rope_shape`:
  the ``(m, h, d)`` of one RoPE call site (ADR-0161 decisions 2 and 3),
  whose ``h`` is the query head count for ``rope_q`` and the KV head count
  for ``rope_k`` and whose ``d`` is ``head_dim``. :func:`sdpa_shape`: the
  ``(m, l, h, h_kv, d)`` of the SDPA call site (ADR-0162 decision 3), ``m``
  new rows attending ``l`` positions, with ``h`` the query head count,
  ``h_kv`` the KV head count and ``d`` the ``head_dim``.
* :func:`generation_calls`, :func:`rmsnorm_generation_calls`,
  :func:`elementwise_add_generation_calls`, :func:`swiglu_generation_calls`,
  :func:`rope_generation_calls` and :func:`sdpa_generation_calls`: the
  distinct shapes of each call site over one generation (ADR-0153 decision
  4). The SDPA shape is the first whose ``l`` changes from one decode pass
  to the next: the prefill gives ``(m, l)`` = (``prompt_length``,
  ``prompt_length``) and decode pass k gives (1, ``prompt_length`` + k)
  (ADR-0162 decision 15), so a generation of length G has G ``sdpa``
  shapes.
* :class:`KernelReference`, :class:`BindingEntry`: a binding entry (decision 3).
* :func:`check`, :func:`check_rmsnorm`, :func:`check_elementwise_add`,
  :func:`check_swiglu`, :func:`check_rope` and :func:`check_sdpa`: the
  outcomes ``"invalid_input"``, ``"no_kernel"`` and ``"kernel_unfit"``
  (decision 5, whose spelling is left to the code slice), and the calls of
  the generation with the kernel each one is bound to.
* :func:`rmsnorm_eps`: the binary32 value nearest to the model's ``eps``, the
  value the caller passes to an RMSNorm kernel (ADR-0158 decision 5).

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
  ``"every"`` entry, are accepted for each of the seven contracts: a kernel
  of either ``gemm`` contract must compute the product for the values it is
  called with (ADR-0008 decision 6, ADR-0156 decision 7, ADR-0157 decision
  3), a kernel of the ``rmsnorm`` contract (ADR-0158 decision 7), of the
  ``elementwise_add`` contract (ADR-0159 decision 8) or of the ``swiglu``
  contract (ADR-0160 decision 8) must be correct for every ``m``, ``n`` of at
  least 1, a kernel of the ``rope`` contract for every ``m``, ``h`` of at
  least 1 and every even ``d`` of at least 2 (ADR-0161 decision 11), and a
  kernel of the ``sdpa_kv_cache`` contract for every set of dimensions the
  caller guarantees (ADR-0162 decision 11). So the operand shapes of a
  ``task.contract`` are not compared.
* An odd ``head_dim`` is refused by the RoPE functions only, as
  :func:`check_dimensions` refuses other well-typed dimensions the contracts
  cannot run: the ``rope`` contract needs an even ``d`` (ADR-0161 decision
  11), and placing that refusal here is a convention of this module, not a
  rule of the record. :func:`check_dimensions` and the other checks accept an
  odd ``head_dim``.
* The largest ``l`` of a generation is ``prompt_length + generation_length -
  1``. A shape member above :data:`hilclaw.keys.MAX_INTEGER` cannot be a key
  value (ADR-0001), so the SDPA functions refuse a generation whose largest
  ``l`` exceeds 2**53 - 1 as a run setting outside its range, the
  ``"invalid_input"`` of ADR-0153 decision 5. This refusal is a reading of
  this module, not a rule of the records; it sets no capacity and no longest
  sequence.

What this module does not do: it builds, loads and starts nothing and runs no
process; it reads and writes no file; it has no command-line entry, registry
or MCP tool; it knows no contract other than the fp32 and bf16 ``gemm``
contracts and the bf16 ``rmsnorm``, ``elementwise_add``, ``swiglu``, ``rope``
and ``sdpa_kv_cache`` contracts, and no dtype outside :data:`DTYPES` for a
GEMM call site, outside :data:`RMSNORM_DTYPES` for an RMSNorm call site,
outside :data:`ELEMENTWISE_ADD_DTYPES` for an elementwise add call site,
outside :data:`SWIGLU_DTYPES` for the SwiGLU call site, outside
:data:`ROPE_DTYPES` for a RoPE call site or outside :data:`SDPA_DTYPES` for
the SDPA call site; it does not join the six checks into one check of a
generation (the full pass, ADR-0153 code slice 2), and it does not check
which arrays a call passes as its operands (ADR-0159 decision 12, ADR-0160
decision 12, ADR-0161 decision 15, ADR-0162 decision 15); it builds, holds
and slices no RoPE frequency table, knows no position and no RoPE constant
(the table is the host-side table builder's, ADR-0161 decision 4); it
allocates, sizes and checks no KV cache buffer and knows no capacity
(ADR-0162 decision 4; OD-31 sub-question 6), and it makes no V copy; it reads
no weight, passes ``eps`` to nothing and adds no cast; it does not interpret
the build flags of a kernel reference; and it derives no binding from a key's
best (OD-20, OD-7).

Every :class:`TypeError` or :class:`ValueError` raised here for an argument
carries the attribute ``parameter``, the name of that argument. Arguments are
not modified.
"""

import contextlib
import math
import os
import re
import struct
from collections.abc import Mapping, Sequence
from typing import NamedTuple

from hilclaw import (
    elementwise_add_bf16_contract,
    gemm_bf16_contract,
    gemm_contract,
    keys,
    rmsnorm_bf16_contract,
    rope_bf16_contract,
    sdpa_kv_cache_bf16_contract,
    swiglu_bf16_contract,
)

CALL_SITES = ("qkv", "o", "gate", "up", "down", "lm_head")
"""The GEMM call sites, ADR-0152 decision 2 rows 3, 8, 11 (gate and up), 13 and 16."""

DTYPES = (gemm_contract.DTYPE, gemm_bf16_contract.DTYPE)
"""The dtypes at which the ``gemm`` contract is known, the range of the model's dtype (ADR-0157 decision 4)."""

RMSNORM_CALL_SITES = ("attention_norm", "ffn_norm", "norm")
"""The RMSNorm call sites, ADR-0152 decision 2 rows 2, 10 and 15."""

RMSNORM_DTYPES = (rmsnorm_bf16_contract.DTYPE,)
"""The dtypes at which the ``rmsnorm`` contract is known (ADR-0157 decision 4, ADR-0158 decision 1)."""

ELEMENTWISE_ADD_CALL_SITES = ("attention_residual", "ffn_residual")
"""The elementwise add call sites, ADR-0152 decision 2 rows 9 and 14, named and ordered as ADR-0159 decision 12."""

ELEMENTWISE_ADD_DTYPES = (elementwise_add_bf16_contract.DTYPE,)
"""The dtypes at which the ``elementwise_add`` contract is known (ADR-0157 decision 4, ADR-0159 decision 1)."""

SWIGLU_CALL_SITES = ("ffn_activation",)
"""The SwiGLU call site, ADR-0152 decision 2 row 12, named as ADR-0160 decision 12."""

SWIGLU_DTYPES = (swiglu_bf16_contract.DTYPE,)
"""The dtypes at which the ``swiglu`` contract is known (ADR-0157 decision 4, ADR-0160 decision 1)."""

ROPE_CALL_SITES = ("rope_q", "rope_k")
"""The RoPE call sites, ADR-0152 decision 2 row 5, named and ordered as ADR-0161 decision 15."""

ROPE_DTYPES = (rope_bf16_contract.DTYPE,)
"""The dtypes at which the ``rope`` contract is known (ADR-0157 decision 4, ADR-0161 decision 1)."""

SDPA_CALL_SITES = ("sdpa",)
"""The SDPA call site, ADR-0152 decision 2 rows 6 and 7, named as ADR-0162 decision 15."""

SDPA_DTYPES = (sdpa_kv_cache_bf16_contract.DTYPE,)
"""The dtypes at which the ``sdpa_kv_cache`` contract is known (ADR-0157 decision 4, ADR-0162 decision 1)."""

LM_HEAD_ROWS = ("all", "last")

INVALID_INPUT = "invalid_input"
NO_KERNEL = "no_kernel"
KERNEL_UNFIT = "kernel_unfit"

_CONTRACTS = dict(zip(DTYPES, (gemm_contract, gemm_bf16_contract)))
_DTYPE_NAME = re.compile(r"[a-z][a-z0-9_]{0,31}")
_GEMM_SHAPE = ("m", "k", "n")
_ROW_SHAPE = ("m", "n")
_ROPE_SHAPE = ("m", "h", "d")
_ROPE_HEADS = {"rope_q": "heads", "rope_k": "kv_heads"}
_SDPA_SHAPE = ("m", "l", "h", "h_kv", "d")


class ModelDimensions(NamedTuple):
    """The model parameters the GEMM, RMSNorm, elementwise add, SwiGLU, RoPE and SDPA shapes depend on (ADR-0153 decision 3 (a)).

    The RoPE shapes use ``heads`` (``rope_q``), ``kv_heads`` (``rope_k``) and
    ``head_dim`` (ADR-0161 decisions 2 and 3); the SDPA shape uses ``heads``,
    ``kv_heads`` and ``head_dim`` as its ``h``, ``h_kv`` and ``d`` (ADR-0162
    decision 3).
    """

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
    """A kernel bound for ``shapes``: ``"every"`` or a non-empty tuple of shapes.

    A shape is ``(m, k, n)`` for a GEMM call site, ``(m, n)`` for an
    RMSNorm, elementwise add or SwiGLU call site, ``(m, h, d)`` for a RoPE
    call site and ``(m, l, h, h_kv, d)`` for the SDPA call site.
    """

    kernel: KernelReference
    shapes: object


class Outcome(NamedTuple):
    """One outcome of :func:`check`, :func:`check_rmsnorm`, :func:`check_elementwise_add`, :func:`check_swiglu`, :func:`check_rope` or :func:`check_sdpa`; ``reason`` is always a ``str``."""

    kind: str
    call_site: object
    shape: object
    reason: str


class BindingCheck(NamedTuple):
    """The result of :func:`check`, :func:`check_rmsnorm`, :func:`check_elementwise_add`, :func:`check_swiglu`, :func:`check_rope` or :func:`check_sdpa`: ``ok`` exactly when ``outcomes`` is empty."""

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
    _lengths(prompt_length, generation_length)
    with _parameter("lm_head_rows"):
        _lm_head_rows(lm_head_rows)
        if lm_head_rows not in LM_HEAD_ROWS:
            raise ValueError(f"must be one of {LM_HEAD_ROWS}, got {lm_head_rows!r}")
    rows = _pass_rows(prompt_length, generation_length)
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
    binding = _binding(binding, CALL_SITES, _GEMM_SHAPE)

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
    if known:
        reference = _CONTRACTS[dtype].task_contract(1, 1, 1)
        _bind(CALL_SITES, binding, shapes, reference, f"{dtype} gemm", outcomes, calls)
    ok = not outcomes
    return BindingCheck(ok, tuple(outcomes), tuple(calls) if ok else ())


def rmsnorm_shape(dimensions, call_site, rows):
    """Return the ``(m, n)`` of the RMSNorm ``call_site`` in a pass of ``rows`` rows.

    ``m`` is ``rows`` and ``n`` is ``hidden``, for each of the three call
    sites: each normalises T rows of the hidden width with a weight of that
    width (ADR-0152 decisions 2 and 5, ADR-0158 decision 2). Raises as
    :func:`check_dimensions` does, then :class:`ValueError` with ``parameter``
    ``"call_site"`` for a call site not in :data:`RMSNORM_CALL_SITES`, then
    :class:`TypeError` or :class:`ValueError` with ``parameter`` ``"rows"``
    for ``rows`` that is not an ``int`` from 1 to 2**53 - 1.
    """
    return _row_shape(dimensions, call_site, rows, RMSNORM_CALL_SITES, "hidden")


def rmsnorm_generation_calls(dimensions, *, prompt_length, generation_length):
    """Return, per call site in :data:`RMSNORM_CALL_SITES` order, the sorted tuple of distinct shapes of a generation.

    The passes are those of :func:`generation_calls`: one prefill pass of
    ``prompt_length`` rows and then ``generation_length - 1`` decode passes of
    one row. The result is a tuple of ``(call_site, shapes)`` pairs, each
    shape an ``(m, n)`` of :func:`rmsnorm_shape`. Raises as
    :func:`check_dimensions`, then :class:`TypeError` or :class:`ValueError`
    with the argument's name as ``parameter``: ``prompt_length`` and
    ``generation_length`` are ``int`` from 1 to 2**53 - 1.
    """
    return _row_generation_calls(
        dimensions, prompt_length, generation_length, RMSNORM_CALL_SITES, "hidden"
    )


def check_rmsnorm(dimensions, binding, *, dtype, prompt_length, generation_length):
    """Check ``binding`` against every RMSNorm call of a generation; return a :class:`BindingCheck`.

    ``binding`` maps call sites of :data:`RMSNORM_CALL_SITES` to non-empty
    sequences of :class:`BindingEntry`. ``dtype`` is the model's dtype
    (ADR-0157 decision 1); it has no default. This check stands beside
    :func:`check`, :func:`check_elementwise_add`, :func:`check_swiglu`,
    :func:`check_rope` and :func:`check_sdpa` and is not joined with them.

    Arguments are first refused, in the order ``dimensions``, ``dtype``,
    ``prompt_length``, ``generation_length``, ``binding``, with
    :class:`TypeError` for a wrong type (``dtype`` is exactly a ``str``,
    ``prompt_length`` and ``generation_length`` exactly an ``int``) and, for
    ``dimensions``, a ``dtype`` that is not a name of ADR-0001's ``dtype``
    field (``[a-z][a-z0-9_]{0,31}``) and a malformed ``binding``,
    :class:`ValueError`; ``parameter`` is the argument's name. ``binding`` is
    malformed as for :func:`check`, with :data:`RMSNORM_CALL_SITES` as its
    keys and ``(m, n)`` pairs of ``int`` from 1 to 2**53 - 1 as its shapes.

    The outcomes then come in this order:

    1. ``"invalid_input"`` (``call_site`` and ``shape`` ``None``): a
       ``dtype`` not in :data:`RMSNORM_DTYPES`, at which no ``rmsnorm``
       contract is known (ADR-0157 decision 4, ADR-0158 decision 1);
       ``prompt_length`` outside 1 to 2**53 - 1; ``generation_length``
       outside 1 to 2**53 - 1.
    2. Per call site in :data:`RMSNORM_CALL_SITES` order: ``"kernel_unfit"``
       (``shape`` ``None``) for each entry, in order, whose ``contract`` is
       not the bf16 ``rmsnorm`` contract, compared on ``language``,
       ``prototype`` and the operands' ``(name, role, dtype)`` (ADR-0153
       decision 3 "Fit"; reference values from
       :func:`hilclaw.rmsnorm_bf16_contract.task_contract`, never from the
       entry's own contract); then ``"no_kernel"`` for each shape of
       :func:`rmsnorm_generation_calls`, in order, that no entry covers. The
       ``"no_kernel"`` outcomes are not looked for when there is an
       ``"invalid_input"``, and neither kind is when ``dtype`` is not in
       :data:`RMSNORM_DTYPES`.

    A listed shape other than the kernel's own spec shape, and an ``"every"``
    entry, are accepted (ADR-0158 decision 7). ``calls`` holds ``(call_site,
    shape, kernel)`` for every call of :func:`rmsnorm_generation_calls`, in
    its order, only when ``ok``; it is empty otherwise. Nothing is built,
    started or read.
    """
    return _check_rows(
        dimensions,
        binding,
        dtype,
        prompt_length,
        generation_length,
        RMSNORM_CALL_SITES,
        RMSNORM_DTYPES,
        rmsnorm_bf16_contract,
        rmsnorm_generation_calls,
    )


def elementwise_add_shape(dimensions, call_site, rows):
    """Return the ``(m, n)`` of the elementwise add ``call_site`` in a pass of ``rows`` rows.

    ``m`` is ``rows`` and ``n`` is ``hidden``, for both call sites: each adds
    two arrays of T rows of the hidden width into a third of that shape
    (ADR-0152 decisions 2 and 5, ADR-0159 decision 2). Raises as
    :func:`check_dimensions` does, then :class:`ValueError` with
    ``parameter`` ``"call_site"`` for a call site not in
    :data:`ELEMENTWISE_ADD_CALL_SITES`, then :class:`TypeError` or
    :class:`ValueError` with ``parameter`` ``"rows"`` for ``rows`` that is not
    an ``int`` from 1 to 2**53 - 1.
    """
    return _row_shape(dimensions, call_site, rows, ELEMENTWISE_ADD_CALL_SITES, "hidden")


def elementwise_add_generation_calls(dimensions, *, prompt_length, generation_length):
    """Return, per call site in :data:`ELEMENTWISE_ADD_CALL_SITES` order, the sorted tuple of distinct shapes of a generation.

    The passes are those of :func:`generation_calls`: one prefill pass of
    ``prompt_length`` rows and then ``generation_length - 1`` decode passes of
    one row. The result is a tuple of ``(call_site, shapes)`` pairs, each
    shape an ``(m, n)`` of :func:`elementwise_add_shape`. Raises as
    :func:`rmsnorm_generation_calls` does.
    """
    return _row_generation_calls(
        dimensions,
        prompt_length,
        generation_length,
        ELEMENTWISE_ADD_CALL_SITES,
        "hidden",
    )


def check_elementwise_add(
    dimensions, binding, *, dtype, prompt_length, generation_length
):
    """Check ``binding`` against every elementwise add call of a generation; return a :class:`BindingCheck`.

    ``binding`` maps call sites of :data:`ELEMENTWISE_ADD_CALL_SITES` to
    non-empty sequences of :class:`BindingEntry`. ``dtype`` is the model's
    dtype (ADR-0157 decision 1); it has no default. This check stands beside
    :func:`check`, :func:`check_rmsnorm`, :func:`check_swiglu`,
    :func:`check_rope` and :func:`check_sdpa` and is not joined with them.

    Arguments are refused as by :func:`check_rmsnorm`, in the same order and
    with the same errors, with :data:`ELEMENTWISE_ADD_CALL_SITES` as the keys
    of ``binding`` and ``(m, n)`` pairs as its shapes.

    The outcomes then come in this order:

    1. ``"invalid_input"`` (``call_site`` and ``shape`` ``None``): a
       ``dtype`` not in :data:`ELEMENTWISE_ADD_DTYPES`, at which no
       ``elementwise_add`` contract is known (ADR-0157 decision 4, ADR-0159
       decision 1); ``prompt_length`` outside 1 to 2**53 - 1;
       ``generation_length`` outside 1 to 2**53 - 1.
    2. Per call site in :data:`ELEMENTWISE_ADD_CALL_SITES` order:
       ``"kernel_unfit"`` (``shape`` ``None``) for each entry, in order,
       whose ``contract`` is not the bf16 ``elementwise_add`` contract,
       compared on ``language``, ``prototype`` and the operands' ``(name,
       role, dtype)`` (ADR-0153 decision 3 "Fit"; reference values from
       :func:`hilclaw.elementwise_add_bf16_contract.task_contract`, never
       from the entry's own contract); then ``"no_kernel"`` for each shape
       of :func:`elementwise_add_generation_calls`, in order, that no entry
       covers. The ``"no_kernel"`` outcomes are not looked for when there is
       an ``"invalid_input"``, and neither kind is when ``dtype`` is not in
       :data:`ELEMENTWISE_ADD_DTYPES`.

    A listed shape other than the kernel's own spec shape, and an ``"every"``
    entry, are accepted (ADR-0159 decision 8). ``calls`` holds ``(call_site,
    shape, kernel)`` for every call of :func:`elementwise_add_generation_calls`,
    in its order, only when ``ok``; it is empty otherwise. Which arrays a call
    passes as ``a``, ``b`` and ``c`` (ADR-0159 decision 12) is not checked.
    Nothing is built, started or read.
    """
    return _check_rows(
        dimensions,
        binding,
        dtype,
        prompt_length,
        generation_length,
        ELEMENTWISE_ADD_CALL_SITES,
        ELEMENTWISE_ADD_DTYPES,
        elementwise_add_bf16_contract,
        elementwise_add_generation_calls,
    )


def swiglu_shape(dimensions, call_site, rows):
    """Return the ``(m, n)`` of the SwiGLU ``call_site`` in a pass of ``rows`` rows.

    ``m`` is ``rows`` and ``n`` is ``intermediate``, not ``hidden``: the call
    takes two arrays of T rows of the intermediate width into a third of that
    shape (ADR-0152 decisions 2 and 5, ADR-0160 decision 2). Raises as
    :func:`check_dimensions` does, then :class:`ValueError` with
    ``parameter`` ``"call_site"`` for a call site not in
    :data:`SWIGLU_CALL_SITES`, then :class:`TypeError` or :class:`ValueError`
    with ``parameter`` ``"rows"`` for ``rows`` that is not an ``int`` from 1
    to 2**53 - 1.
    """
    return _row_shape(dimensions, call_site, rows, SWIGLU_CALL_SITES, "intermediate")


def swiglu_generation_calls(dimensions, *, prompt_length, generation_length):
    """Return, per call site in :data:`SWIGLU_CALL_SITES` order, the sorted tuple of distinct shapes of a generation.

    The passes are those of :func:`generation_calls`: one prefill pass of
    ``prompt_length`` rows and then ``generation_length - 1`` decode passes of
    one row. The result is a tuple of ``(call_site, shapes)`` pairs, each
    shape an ``(m, n)`` of :func:`swiglu_shape`. Raises as
    :func:`rmsnorm_generation_calls` does.
    """
    return _row_generation_calls(
        dimensions,
        prompt_length,
        generation_length,
        SWIGLU_CALL_SITES,
        "intermediate",
    )


def check_swiglu(dimensions, binding, *, dtype, prompt_length, generation_length):
    """Check ``binding`` against every SwiGLU call of a generation; return a :class:`BindingCheck`.

    ``binding`` maps call sites of :data:`SWIGLU_CALL_SITES` to non-empty
    sequences of :class:`BindingEntry`. ``dtype`` is the model's dtype
    (ADR-0157 decision 1); it has no default. This check stands beside
    :func:`check`, :func:`check_rmsnorm`, :func:`check_elementwise_add`,
    :func:`check_rope` and :func:`check_sdpa` and is not joined with them.

    Arguments are refused as by :func:`check_rmsnorm`, in the same order and
    with the same errors, with :data:`SWIGLU_CALL_SITES` as the keys of
    ``binding`` and ``(m, n)`` pairs as its shapes.

    The outcomes then come in this order:

    1. ``"invalid_input"`` (``call_site`` and ``shape`` ``None``): a
       ``dtype`` not in :data:`SWIGLU_DTYPES`, at which no ``swiglu``
       contract is known (ADR-0157 decision 4, ADR-0160 decision 1);
       ``prompt_length`` outside 1 to 2**53 - 1; ``generation_length``
       outside 1 to 2**53 - 1.
    2. Per call site in :data:`SWIGLU_CALL_SITES` order: ``"kernel_unfit"``
       (``shape`` ``None``) for each entry, in order, whose ``contract`` is
       not the bf16 ``swiglu`` contract, compared on ``language``,
       ``prototype`` and the operands' ``(name, role, dtype)`` (ADR-0153
       decision 3 "Fit"; reference values from
       :func:`hilclaw.swiglu_bf16_contract.task_contract`, never from the
       entry's own contract); then ``"no_kernel"`` for each shape of
       :func:`swiglu_generation_calls`, in order, that no entry covers. The
       ``"no_kernel"`` outcomes are not looked for when there is an
       ``"invalid_input"``, and neither kind is when ``dtype`` is not in
       :data:`SWIGLU_DTYPES`.

    A listed shape other than the kernel's own spec shape, and an ``"every"``
    entry, are accepted (ADR-0160 decision 8). ``calls`` holds ``(call_site,
    shape, kernel)`` for every call of :func:`swiglu_generation_calls`, in
    its order, only when ``ok``; it is empty otherwise. Which arrays a call
    passes as ``gate``, ``up`` and ``out`` (ADR-0160 decision 12) is not
    checked. Nothing is built, started or read.
    """
    return _check_rows(
        dimensions,
        binding,
        dtype,
        prompt_length,
        generation_length,
        SWIGLU_CALL_SITES,
        SWIGLU_DTYPES,
        swiglu_bf16_contract,
        swiglu_generation_calls,
    )


def rope_shape(dimensions, call_site, rows):
    """Return the ``(m, h, d)`` of the RoPE ``call_site`` in a pass of ``rows`` rows.

    ``m`` is ``rows`` and ``d`` is ``head_dim``; ``h`` is ``heads`` for
    ``"rope_q"`` and ``kv_heads`` for ``"rope_k"``: each call rotates T rows
    of one tensor, Q then K (ADR-0152 decision 5, ADR-0161 decisions 2 and 3).
    Raises as :func:`check_dimensions` does, then :class:`ValueError` with
    ``parameter`` ``"dimensions"`` for an odd ``head_dim`` (ADR-0161 decision
    11; refused here by this module's convention), then :class:`ValueError`
    with ``parameter`` ``"call_site"`` for a call site not in
    :data:`ROPE_CALL_SITES`, then :class:`TypeError` or :class:`ValueError`
    with ``parameter`` ``"rows"`` for ``rows`` that is not an ``int`` from 1
    to 2**53 - 1.
    """
    _check_rope_dimensions(dimensions)
    with _parameter("call_site"):
        if call_site not in ROPE_CALL_SITES:
            raise ValueError(f"must be one of {ROPE_CALL_SITES}, got {call_site!r}")
    with _parameter("rows"):
        _integer(rows, "rows")
    heads = getattr(dimensions, _ROPE_HEADS[call_site])
    return (rows, heads, dimensions.head_dim)


def rope_generation_calls(dimensions, *, prompt_length, generation_length):
    """Return, per call site in :data:`ROPE_CALL_SITES` order, the sorted tuple of distinct shapes of a generation.

    The passes are those of :func:`generation_calls`: one prefill pass of
    ``prompt_length`` rows and then ``generation_length - 1`` decode passes of
    one row. The result is a tuple of ``(call_site, shapes)`` pairs, each
    shape an ``(m, h, d)`` of :func:`rope_shape`. Raises as
    :func:`check_dimensions`, then :class:`ValueError` with ``parameter``
    ``"dimensions"`` for an odd ``head_dim``, then as
    :func:`rmsnorm_generation_calls` does for the lengths.
    """
    _check_rope_dimensions(dimensions)
    _lengths(prompt_length, generation_length)
    rows = _pass_rows(prompt_length, generation_length)
    return tuple(
        (site, tuple(sorted(rope_shape(dimensions, site, r) for r in rows)))
        for site in ROPE_CALL_SITES
    )


def check_rope(dimensions, binding, *, dtype, prompt_length, generation_length):
    """Check ``binding`` against every RoPE call of a generation; return a :class:`BindingCheck`.

    ``binding`` maps call sites of :data:`ROPE_CALL_SITES` to non-empty
    sequences of :class:`BindingEntry`. ``dtype`` is the model's dtype
    (ADR-0157 decision 1); it has no default. This check stands beside
    :func:`check`, :func:`check_rmsnorm`, :func:`check_elementwise_add`,
    :func:`check_swiglu` and :func:`check_sdpa` and is not joined with them.

    Arguments are refused as by :func:`check_rmsnorm`, in the same order and
    with the same errors, with :data:`ROPE_CALL_SITES` as the keys of
    ``binding`` and ``(m, h, d)`` triples as its shapes; ``dimensions`` with
    an odd ``head_dim`` is refused too (:class:`ValueError`, ``parameter``
    ``"dimensions"``; ADR-0161 decision 11, by this module's convention).

    The outcomes then come in this order:

    1. ``"invalid_input"`` (``call_site`` and ``shape`` ``None``): a
       ``dtype`` not in :data:`ROPE_DTYPES`, at which no ``rope`` contract is
       known (ADR-0157 decision 4, ADR-0161 decision 1); ``prompt_length``
       outside 1 to 2**53 - 1; ``generation_length`` outside 1 to 2**53 - 1.
    2. Per call site in :data:`ROPE_CALL_SITES` order: ``"kernel_unfit"``
       (``shape`` ``None``) for each entry, in order, whose ``contract`` is
       not the bf16 ``rope`` contract, compared on ``language``,
       ``prototype`` and the operands' ``(name, role, dtype)`` (ADR-0153
       decision 3 "Fit", ADR-0161 decision 10; reference values from
       :func:`hilclaw.rope_bf16_contract.task_contract`, never from the
       entry's own contract); then ``"no_kernel"`` for each shape of
       :func:`rope_generation_calls`, in order, that no entry covers. The
       ``"no_kernel"`` outcomes are not looked for when there is an
       ``"invalid_input"``, and neither kind is when ``dtype`` is not in
       :data:`ROPE_DTYPES`.

    A listed shape other than the kernel's own spec shape, and an ``"every"``
    entry, are accepted (ADR-0161 decision 11). ``calls`` holds
    ``(call_site, shape, kernel)`` for every call of
    :func:`rope_generation_calls`, in its order, only when ``ok``; it is
    empty otherwise. Which arrays a call passes as ``x``, ``freqs_cis`` and
    ``out`` (ADR-0161 decision 15), the frequency table and its rows for a
    position are not checked. Nothing is built, started or read.
    """
    _check_rope_dimensions(dimensions)
    return _check_rows(
        dimensions,
        binding,
        dtype,
        prompt_length,
        generation_length,
        ROPE_CALL_SITES,
        ROPE_DTYPES,
        rope_bf16_contract,
        rope_generation_calls,
        members=_ROPE_SHAPE,
        reference_shape=(1, 1, 2),
    )


def sdpa_shape(dimensions, call_site, rows, positions):
    """Return the ``(m, l, h, h_kv, d)`` of the SDPA ``call_site`` for ``rows`` new rows attending ``positions`` positions.

    The result is ``(rows, positions, heads, kv_heads, head_dim)``: ``m`` is
    T, ``l`` is L, ``h`` the query heads, ``h_kv`` the KV heads and ``d`` the
    ``head_dim`` (ADR-0162 decision 3). Raises as :func:`check_dimensions`
    does, then :class:`ValueError` with ``parameter`` ``"call_site"`` for a
    call site not in :data:`SDPA_CALL_SITES`, then :class:`TypeError` or
    :class:`ValueError` with ``parameter`` ``"rows"`` for ``rows`` that is not
    an ``int`` from 1 to 2**53 - 1, then the same with ``parameter``
    ``"positions"`` for ``positions``, then :class:`ValueError` with
    ``parameter`` ``"positions"`` when ``positions`` is less than ``rows``
    (ADR-0162 decision 11, l at least m). An odd ``head_dim`` is accepted.
    """
    check_dimensions(dimensions)
    with _parameter("call_site"):
        if call_site not in SDPA_CALL_SITES:
            raise ValueError(f"must be one of {SDPA_CALL_SITES}, got {call_site!r}")
    with _parameter("rows"):
        _integer(rows, "rows")
    with _parameter("positions"):
        _integer(positions, "positions")
        if positions < rows:
            raise ValueError(f"must be at least rows ({rows}), got {positions}")
    return (rows, positions, dimensions.heads, dimensions.kv_heads, dimensions.head_dim)


def sdpa_generation_calls(dimensions, *, prompt_length, generation_length):
    """Return, for the call site of :data:`SDPA_CALL_SITES`, the sorted tuple of distinct shapes of a generation.

    The passes are those of :func:`generation_calls`, with the positions each
    one attends (ADR-0162 decision 15, ADR-0153 decision 4): the prefill
    gives :func:`sdpa_shape` with ``prompt_length`` rows over
    ``prompt_length`` positions and decode pass k, for k from 1 to
    ``generation_length - 1``, one row over ``prompt_length + k`` positions.
    So a generation of length G has G shapes. The result is ``(("sdpa",
    shapes),)``. Raises as :func:`check_dimensions`, then as
    :func:`rmsnorm_generation_calls` does for the lengths, then
    :class:`ValueError` with ``parameter`` ``"generation_length"`` when
    ``prompt_length + generation_length - 1``, the largest ``l``, exceeds
    2**53 - 1 (this module's reading: no key holds a larger member).
    """
    check_dimensions(dimensions)
    _lengths(prompt_length, generation_length)
    with _parameter("generation_length"):
        reason = _overlong(prompt_length, generation_length)
        if reason is not None:
            raise ValueError(reason)
    tail = (dimensions.heads, dimensions.kv_heads, dimensions.head_dim)
    shapes = [(1, prompt_length + k, *tail) for k in range(1, generation_length)]
    shapes.append((prompt_length, prompt_length, *tail))
    return ((SDPA_CALL_SITES[0], tuple(sorted(shapes))),)


def check_sdpa(dimensions, binding, *, dtype, prompt_length, generation_length):
    """Check ``binding`` against every SDPA call of a generation; return a :class:`BindingCheck`.

    ``binding`` maps the call site of :data:`SDPA_CALL_SITES` to a non-empty
    sequence of :class:`BindingEntry`. ``dtype`` is the model's dtype
    (ADR-0157 decision 1); it has no default. This check stands beside
    :func:`check`, :func:`check_rmsnorm`, :func:`check_elementwise_add`,
    :func:`check_swiglu` and :func:`check_rope` and is not joined with them.

    Arguments are refused as by :func:`check_rmsnorm`, in the same order and
    with the same errors, with :data:`SDPA_CALL_SITES` as the keys of
    ``binding`` and ``(m, l, h, h_kv, d)`` tuples as its shapes. An odd
    ``head_dim`` is accepted.

    The outcomes then come in this order:

    1. ``"invalid_input"`` (``call_site`` and ``shape`` ``None``): a
       ``dtype`` not in :data:`SDPA_DTYPES`, at which no ``sdpa_kv_cache``
       contract is known (ADR-0157 decision 4, ADR-0162 decision 1);
       ``prompt_length`` outside 1 to 2**53 - 1; ``generation_length``
       outside 1 to 2**53 - 1; then, only when both are in that range,
       ``prompt_length + generation_length - 1`` above 2**53 - 1 (this
       module's reading, see the module docstring).
    2. For the call site ``"sdpa"``: ``"kernel_unfit"`` (``shape`` ``None``)
       for each entry, in order, whose ``contract`` is not the bf16
       ``sdpa_kv_cache`` contract, compared on ``language``, ``prototype``
       and the operands' ``(name, role, dtype)`` (ADR-0153 decision 3 "Fit",
       ADR-0162 decision 10; reference values from
       :func:`hilclaw.sdpa_kv_cache_bf16_contract.task_contract`, never from
       the entry's own contract); then ``"no_kernel"`` for each shape of
       :func:`sdpa_generation_calls`, in order, that no entry covers. The
       ``"no_kernel"`` outcomes are not looked for when there is an
       ``"invalid_input"``, and neither kind is when ``dtype`` is not in
       :data:`SDPA_DTYPES`.

    A listed shape other than the kernel's own spec shape, and an ``"every"``
    entry, are accepted (ADR-0162 decision 11). ``calls`` holds
    ``(call_site, shape, kernel)`` for every call of
    :func:`sdpa_generation_calls`, in its order, only when ``ok``; it is
    empty otherwise. Which arrays a call passes as its six operands (ADR-0162
    decision 15), the cache buffers, their capacity and the V copy are not
    checked. Nothing is built, started or read.
    """
    return _check_rows(
        dimensions,
        binding,
        dtype,
        prompt_length,
        generation_length,
        SDPA_CALL_SITES,
        SDPA_DTYPES,
        sdpa_kv_cache_bf16_contract,
        sdpa_generation_calls,
        members=_SDPA_SHAPE,
        reference_shape=(1, 1, 1, 1, 1),
        bound=_overlong,
    )


def rmsnorm_eps(eps):
    """Return the binary32 value nearest to the model parameter ``eps``, as a ``float``.

    The caller of an RMSNorm kernel passes this value as its ``float eps``
    (ADR-0158 decision 5). The result is exactly a binary32 value, rounded
    to nearest with ties to even. ``eps`` is exactly a ``float`` (``bool``,
    ``int`` and other types refused): :class:`TypeError`. A value that is
    not finite or not greater than 0 (ADR-0158 decision 7), or whose nearest
    binary32 value is 0 or not finite, raises :class:`ValueError`. Both carry
    ``parameter`` ``"eps"``. No default ``eps`` is assumed.
    """
    with _parameter("eps"):
        if type(eps) is not float:
            raise TypeError(f"must be a float, got {type(eps).__name__}")
        if not math.isfinite(eps) or not eps > 0:
            raise ValueError(f"must be finite and greater than 0, got {eps!r}")
        try:
            nearest = struct.unpack("<f", struct.pack("<f", eps))[0]
        except OverflowError:
            raise ValueError(
                f"its nearest binary32 value is not finite, got {eps!r}"
            ) from None
        if nearest == 0:
            raise ValueError(f"its nearest binary32 value is 0, got {eps!r}")
        return nearest


def _row_shape(dimensions, call_site, rows, sites, width):
    check_dimensions(dimensions)
    with _parameter("call_site"):
        if call_site not in sites:
            raise ValueError(f"must be one of {sites}, got {call_site!r}")
    with _parameter("rows"):
        _integer(rows, "rows")
    return (rows, getattr(dimensions, width))


def _row_generation_calls(dimensions, prompt_length, generation_length, sites, width):
    check_dimensions(dimensions)
    _lengths(prompt_length, generation_length)
    rows = _pass_rows(prompt_length, generation_length)
    return tuple(
        (
            site,
            tuple(sorted(_row_shape(dimensions, site, r, sites, width) for r in rows)),
        )
        for site in sites
    )


def _check_rows(
    dimensions,
    binding,
    dtype,
    prompt_length,
    generation_length,
    sites,
    dtypes,
    contract,
    site_calls,
    members=_ROW_SHAPE,
    reference_shape=(1, 1),
    bound=None,
):
    check_dimensions(dimensions)
    with _parameter("dtype"):
        _dtype(dtype)
    lengths = (
        ("prompt_length", prompt_length),
        ("generation_length", generation_length),
    )
    for name, value in lengths:
        with _parameter(name):
            if type(value) is not int:
                raise TypeError(f"must be an int, got {type(value).__name__}")
    binding = _binding(binding, sites, members)

    known = dtype in dtypes
    invalid = [] if known else [_no_contract(dtype, contract.KIND)]
    out_of_range = [
        f"{name}: must be from 1 to 2**53 - 1, got {value}"
        for name, value in lengths
        if not 1 <= value <= keys.MAX_INTEGER
    ]
    invalid += out_of_range
    if bound is not None and not out_of_range:
        reason = bound(prompt_length, generation_length)
        invalid += [] if reason is None else [reason]
    outcomes = [Outcome(INVALID_INPUT, None, None, reason) for reason in invalid]
    shapes = {}
    if not invalid:
        shapes = dict(
            site_calls(
                dimensions,
                prompt_length=prompt_length,
                generation_length=generation_length,
            )
        )
    calls = []
    if known:
        reference = contract.task_contract(*reference_shape)
        label = f"{dtype} {contract.KIND}"
        _bind(sites, binding, shapes, reference, label, outcomes, calls)
    ok = not outcomes
    return BindingCheck(ok, tuple(outcomes), tuple(calls) if ok else ())


def _check_rope_dimensions(dimensions):
    check_dimensions(dimensions)
    with _parameter("dimensions"):
        if dimensions.head_dim % 2:
            raise ValueError(
                f"head_dim must be even for a rope call site, got {dimensions.head_dim}"
            )


def _overlong(prompt_length, generation_length):
    if prompt_length + generation_length - 1 <= keys.MAX_INTEGER:
        return None
    return (
        "generation_length: prompt_length + generation_length - 1 must be at "
        f"most 2**53 - 1, got {prompt_length} + {generation_length} - 1"
    )


def _bind(sites, binding, shapes, reference, label, outcomes, calls):
    for site in sites:
        entries = binding.get(site, ())
        for index, entry in enumerate(entries):
            reason = _unfit(entry.kernel.contract, reference, label)
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


def _no_contract(dtype, kind="gemm"):
    return f"dtype: no {kind} contract is known at the dtype {dtype!r}"


def _unfit(contract, reference, label):
    if not isinstance(contract, Mapping):
        return f"contract is not a mapping, got {type(contract).__name__}"
    for member in ("language", "prototype", "operands"):
        if member not in contract:
            return f"contract lacks the member {member!r}"
    for member in ("language", "prototype"):
        if not _same_text(contract[member], reference[member]):
            return f"contract.{member} is not that of the {label} contract"
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
                return f"contract.operands[{index}].{member} is not that of the {label} contract"
    return None


def _same_text(value, expected):
    return isinstance(value, str) and value == expected


def _binding(binding, sites, members):
    with _parameter("binding"):
        if not isinstance(binding, Mapping):
            raise TypeError(f"must be a mapping, got {type(binding).__name__}")
        result = {}
        for site, entries in binding.items():
            if site not in sites:
                raise ValueError(f"key {site!r} is not a call site of {sites}")
            if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
                raise TypeError(f"{site}: must be a sequence of BindingEntry")
            entries = tuple(entries)
            if not entries:
                raise ValueError(f"{site}: has no entry")
            for entry in entries:
                _entry(entry, site, members)
            _no_overlap(entries, site)
            result[site] = entries
        return result


def _entry(entry, site, members):
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
            raise TypeError(f"{site}: a shape is not a tuple ({', '.join(members)})")
        if len(shape) != len(members):
            raise ValueError(
                f"{site}: a shape has {len(shape)} members, not {len(members)}"
            )
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


def _lengths(prompt_length, generation_length):
    for name, value in (
        ("prompt_length", prompt_length),
        ("generation_length", generation_length),
    ):
        with _parameter(name):
            _integer(value, name)


def _pass_rows(prompt_length, generation_length):
    return {prompt_length, 1} if generation_length > 1 else {prompt_length}


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
