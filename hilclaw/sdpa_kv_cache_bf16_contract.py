"""Op-side values of a spec for the bf16 ``sdpa_kv_cache`` contract on ``cpu_standin`` (ADR-0162).

``ARCHITECTURE/decisions/ADR-0162-od31-bf16-sdpa-kv-cache-contract.md``, built
on ADR-0008 (the fp32 ``gemm`` contract whose call rules it reads with its own
kind, symbol and operands), ADR-0037 (no shape that holds a 0) and ADR-0156
(the bf16 ``gemm`` contract: ``uint16_t`` operands holding bf16 bit patterns,
the symbol form and the value set of the verification inputs), defines one
operational contract. It is bound to the kind ``sdpa_kv_cache``, the dtype
``bf16``, the layout ``row_major`` and the kernel language ``c``, on the target
``cpu_standin`` (decisions 1 and 3). This module returns the values that record
fixes for a shape ``m``, ``l``, ``h``, ``h_kv``, ``d``: scaled dot-product
attention of ``m`` new tokens of ``h`` query heads over ``l`` positions of
``h_kv`` KV heads of ``d`` elements, with the KV cache as two operands the call
updates (decisions 2 to 5 and 10). Every operand shape is that of the operand
itself; the cache operands ``cache_k`` and ``cache_v`` are the first ``l`` rows
of the model program's buffers, never a capacity (decisions 4 and 10). For a
shape that holds a 0, with ``l`` less than ``m`` or with ``h`` not a multiple
of ``h_kv``, it returns no values: ADR-0037's reading carries over and those
are the "Dimensions" row of decision 11. The values, and one test of a record:

* :data:`KIND`, :data:`DTYPE`, :data:`LAYOUT` and :data:`LANGUAGE`: the binding
  of the contract (decisions 1, 3, 4 and 10); :data:`DTYPE` is that of every
  operand.
* :data:`PROTOTYPE`: the declaration of the entry point
  ``hilclaw_sdpa_kv_cache_bf16`` with its ``uint16_t`` arrays, the text of
  ``task.contract.prototype`` in every spec of this contract (decision 9).
* :func:`op_signature_record`: the op_signature record of a shape (the rule of
  decision 14).
* :func:`task_contract`: the ``task.contract`` object of a shape, with the six
  operand entries in the order of the parameters (decision 10).
* :data:`SHAPES`: the four shapes of the table of decision 14, prefill then
  decode step at S = 128, then the same at S = 2048.
* :data:`INPUT_PATTERNS`: the 256 bf16 bit patterns of the value set of
  verification, every bf16 value of magnitude in [0.5, 1) with either sign,
  the set of ADR-0156 decision 9 (decision 13). It applies to every element of
  ``q``, ``k_new``, ``v_new`` and of cache rows 0 ... P - 1, P = l - m.
* :func:`covers`: whether an op_signature record is covered by this contract.

What the module does not do: it holds no scale constant, no position, no
capacity, no constant of the accuracy bound and no bound of its domain; the
scale follows from ``d`` and P from ``m`` and ``l``, and the kernel is told no
capacity (decisions 3, 4 and 7). It builds no spec and no other part of one -
no ``task`` object, no ``task.objective``, no ``task.build`` and so no build
setting, no ``hw_profile``, no ``id``, no ``guidance`` and no ``feedback``. It
binds no kernel to a call site, is bound to no tool or registry, reads and
writes no file, starts no process, stores and registers nothing and has no
command-line entry. For :data:`INPUT_PATTERNS` it holds the values only: the
generator, the seed, the draws, the content of cache rows P ... l - 1 and of
``out`` before a call, guard rows, the cache comparison and the widening belong
to the P2-12 harness record (decision 13), and no tolerance is chosen. It knows
no other contract: no other kind, dtype, layout, language or target.

The operation (decision 6), its precision and the accuracy bound (decision 7),
the rounding of the output (decision 8), the cache write and the other
guarantees and obligations of a call (decisions 4 and 11) and what the kernel
source provides (decision 12) are not represented in any value returned here,
beyond what the prototype text itself states (``restrict`` states the
no-overlap guarantee) and the rules that ``l`` is at least ``m`` and ``h`` a
multiple of ``h_kv``.
"""

import reprlib

from hilclaw import keys

KIND = "sdpa_kv_cache"
DTYPE = "bf16"
LAYOUT = "row_major"
LANGUAGE = "c"
PROTOTYPE = (
    "void hilclaw_sdpa_kv_cache_bf16(size_t m, size_t l, size_t h, size_t h_kv, "
    "size_t d, const uint16_t *restrict q, const uint16_t *restrict k_new, "
    "const uint16_t *restrict v_new, uint16_t *restrict cache_k, "
    "uint16_t *restrict cache_v, uint16_t *restrict out);"
)
SHAPES = (
    (128, 128, 32, 8, 64),
    (1, 128, 32, 8, 64),
    (2048, 2048, 32, 8, 64),
    (1, 2048, 32, 8, 64),
)
INPUT_PATTERNS = (*range(0x3F00, 0x3F80), *range(0xBF00, 0xBF80))

_DIMENSIONS = ("m", "l", "h", "h_kv", "d")


def op_signature_record(m, l, h, h_kv, d):
    """Return the op_signature record of the shape ``m``, ``l``, ``h``, ``h_kv``, ``d`` under this contract.

    The result is a new ``dict`` with exactly the members ``schema_version``
    (:data:`hilclaw.keys.SCHEMA_VERSION`), ``kind`` (:data:`KIND`), ``shape``
    (a new ``dict`` ``{"m": m, "l": l, "h": h, "h_kv": h_kv, "d": d}``),
    ``dtype`` (:data:`DTYPE`) and ``layout`` (:data:`LAYOUT`), the rule of
    ADR-0162 decision 14. It has no ``label`` and no ``ext``. It is a record
    :func:`hilclaw.keys.op_signature_key` accepts; the key is not returned.

    Each of ``m``, ``l``, ``h``, ``h_kv`` and ``d`` is exactly an ``int``
    (``bool`` and other subclasses are refused, as in :mod:`hilclaw.keys`)
    from 1 to :data:`hilclaw.keys.MAX_INTEGER`; then ``l`` is at least ``m``
    and ``h`` is a multiple of ``h_kv`` (ADR-0162 decision 11, "Dimensions").
    The lower bound of 1 is the rule of ADR-0037 as decision 11 carries it
    over: the contract covers no shape that breaks one of these rules, so
    there is no op_signature record of it under this contract to return. Such
    a record is still valid for :func:`hilclaw.keys.op_signature_key`: the
    refusal says that the contract does not cover the shape, not that the
    record is invalid.

    Raises :class:`hilclaw.keys.InvalidRecordError` for the first rule found
    broken, the dimensions in the order of the parameters before the two
    rules between them; the message starts with ``shape.`` and the name of
    the dimension (``l`` for the first rule, ``h`` for the second). Nothing is
    returned then.
    """
    return {
        "schema_version": keys.SCHEMA_VERSION,
        "kind": KIND,
        "shape": _shape(m, l, h, h_kv, d),
        "dtype": DTYPE,
        "layout": LAYOUT,
    }


def covers(record):
    """Return whether this contract covers the op_signature ``record``.

    ``record`` is an op_signature record, one that
    :func:`hilclaw.keys.op_signature_key` accepts. The result is ``True`` when
    its ``kind`` is :data:`KIND`, its ``dtype`` is :data:`DTYPE`, its
    ``layout`` is :data:`LAYOUT`, each of ``shape.m``, ``shape.l``,
    ``shape.h``, ``shape.h_kv`` and ``shape.d`` is at least 1, ``shape.l`` is
    at least ``shape.m`` and ``shape.h`` is a multiple of ``shape.h_kv``, and
    ``False`` otherwise; a record of another dtype, fp32 included, is not
    covered. It is exactly a ``bool``. An ``ext`` and a ``label`` are not
    looked at for the answer. No bound is added to that of a valid record
    (:data:`hilclaw.keys.MAX_INTEGER`). ``True`` says that the record is one
    of this contract, not that a kernel, a build, a cache buffer or a target
    exists for it.

    ``record`` is first validated with :func:`hilclaw.keys.op_signature_key`,
    so ``False`` always says that a valid record is not covered. Raises
    :class:`hilclaw.keys.InvalidRecordError`, as that function raises it, for
    an argument it refuses, which includes a ``kind`` it does not know.
    Nothing is returned then. ``record`` is not modified.
    """
    keys.op_signature_key(record)
    if record["kind"] != KIND:
        return False
    if record["dtype"] != DTYPE or record["layout"] != LAYOUT:
        return False
    shape = record["shape"]
    if not all(shape[name] >= 1 for name in _DIMENSIONS):
        return False
    return shape["l"] >= shape["m"] and shape["h"] % shape["h_kv"] == 0


def task_contract(m, l, h, h_kv, d):
    """Return the ``task.contract`` object of the shape ``m``, ``l``, ``h``, ``h_kv``, ``d`` under this contract.

    The result is a new ``dict`` with exactly the members ``language``
    (:data:`LANGUAGE`), ``prototype`` (:data:`PROTOTYPE`) and ``operands``: a
    new ``list`` of six new ``dict`` objects in the order of the array
    parameters (ADR-0162 decision 10), each with exactly ``name``, ``role``,
    ``dtype`` and ``shape`` (a new ``list`` of integers, outermost dimension
    first):

    =======  ==========  =============  ================
    name     role        dtype          shape
    =======  ==========  =============  ================
    q        ``input``   :data:`DTYPE`  ``[m, h, d]``
    k_new    ``input``   :data:`DTYPE`  ``[m, h_kv, d]``
    v_new    ``input``   :data:`DTYPE`  ``[m, h_kv, d]``
    cache_k  ``inout``   :data:`DTYPE`  ``[l, h_kv, d]``
    cache_v  ``inout``   :data:`DTYPE`  ``[l, h_kv, d]``
    out      ``output``  :data:`DTYPE`  ``[m, h, d]``
    =======  ==========  =============  ================

    The shape of a cache operand is that of its first ``l`` rows, never the
    capacity of the buffer (ADR-0162 decision 4). The dimensions have no
    entry. They follow the rules of :func:`op_signature_record`, and a refused
    shape raises :class:`hilclaw.keys.InvalidRecordError` in the same way.
    Nothing is returned then, and nothing is substituted.
    """
    _shape(m, l, h, h_kv, d)
    return {
        "language": LANGUAGE,
        "prototype": PROTOTYPE,
        "operands": [
            _operand("q", "input", [m, h, d]),
            _operand("k_new", "input", [m, h_kv, d]),
            _operand("v_new", "input", [m, h_kv, d]),
            _operand("cache_k", "inout", [l, h_kv, d]),
            _operand("cache_v", "inout", [l, h_kv, d]),
            _operand("out", "output", [m, h, d]),
        ],
    }


def _shape(m, l, h, h_kv, d):
    shape = {"m": m, "l": l, "h": h, "h_kv": h_kv, "d": d}
    for name, value in shape.items():
        if type(value) is not int or not 1 <= value <= keys.MAX_INTEGER:
            got = reprlib.repr(value)
            raise keys.InvalidRecordError(
                f"shape.{name}: must be an integer from 1 to 2**53 - 1, got {got}"
            )
    if l < m:
        raise keys.InvalidRecordError(f"shape.l: must be at least m ({m}), got {l}")
    if h % h_kv:
        raise keys.InvalidRecordError(
            f"shape.h: must be a multiple of h_kv ({h_kv}), got {h}"
        )
    return shape


def _operand(name, role, shape):
    return {"name": name, "role": role, "dtype": DTYPE, "shape": shape}
