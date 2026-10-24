"""Op-side values of a spec for the bf16 ``rope`` contract on ``cpu_standin`` (ADR-0161).

``ARCHITECTURE/decisions/ADR-0161-od31-bf16-rope-contract.md``, built on
ADR-0008 (the fp32 ``gemm`` contract whose call rules it reads with its own
kind, symbol and operands), ADR-0037 (no shape that holds a 0) and ADR-0156
(the bf16 ``gemm`` contract: ``uint16_t`` operands holding bf16 bit patterns,
the symbol form and the value set of the verification input ``x``), defines
one operational contract. It is bound to the kind ``rope``, the dtype
``bf16``, the layout ``row_major`` and the kernel language ``c``, on the target
``cpu_standin`` (decisions 1 and 3). This module returns the values that record
fixes for a shape ``m``, ``h``, ``d``: the rotary position embedding of an
array ``x`` of ``m`` tokens of ``h`` heads of ``d`` elements, with the ``m``
rows of ``d`` binary32 values of the frequency table ``freqs_cis``, into an
array ``out`` of the shape of ``x`` (decisions 2, 6 and 10). For a shape that
holds a 0, or an odd ``d``, it returns no values: ADR-0037's reading carries
over and ``d`` is even and at least 2 (decision 11). The values, and one test
of a record:

* :data:`KIND`, :data:`DTYPE`, :data:`LAYOUT` and :data:`LANGUAGE`: the binding
  of the contract (decisions 1 and 3); :data:`DTYPE` is that of ``x`` and
  ``out``.
* :data:`TABLE_DTYPE`: the dtype of the operand ``freqs_cis`` (decisions 6
  and 10).
* :data:`PROTOTYPE`: the declaration of the entry point ``hilclaw_rope_bf16``
  with its ``uint16_t`` arrays and its ``float`` table, the text of
  ``task.contract.prototype`` in every spec of this contract (decision 9).
* :func:`op_signature_record`: the op_signature record of a shape (the rule of
  decision 14).
* :func:`task_contract`: the ``task.contract`` object of a shape, with the
  three operand entries in the order of the parameters (decision 10).
* :data:`SHAPES`: the six shapes of the table of decision 14, the Q row then
  the K row, each in the order of T.
* :data:`X_PATTERNS`: the 256 bf16 bit patterns of the value set of the
  verification input ``x``, every bf16 value of magnitude in [0.5, 1) with
  either sign, the set of ADR-0156 decision 9 (decision 13). The value set of
  ``freqs_cis`` is rows of the frequency table and is not here.
* :func:`covers`: whether an op_signature record is covered by this contract.

What the module does not do: it holds no frequency table, builds none and
holds no ``rope_theta``, no scaling constant, no scale factor and no position;
the table is built outside the kernels, by the host side (decisions 3 and 4).
It builds no spec and no other part of one - no ``task`` object, no
``task.objective``, no ``task.build`` and so no build setting, no
``hw_profile``, no ``id``, no ``guidance`` and no ``feedback``. It binds no
kernel to a call site, is bound to no tool or registry, reads and writes no
file, starts no process, stores and registers nothing and has no command-line
entry. For :data:`X_PATTERNS` it holds the values only: the generator, the
seed, the number of draws, which T = 1 row a draw uses, the content of ``out``
before a call and the widening belong to the P2-12 harness record (decision
13), and no tolerance is chosen. It knows no other contract: no other kind,
dtype, layout, language or target.

The operation, its precision and the accuracy bound (decision 7), the rounding
of the output (decision 8), the guarantees and obligations of a call (decision
11) and what the kernel source provides (decision 12) are not represented in
any value returned here, beyond what the prototype text itself states
(``restrict`` states the no-overlap guarantee) and the rule that ``d`` is even.
"""

import reprlib

from hilclaw import keys

KIND = "rope"
DTYPE = "bf16"
TABLE_DTYPE = "fp32"
LAYOUT = "row_major"
LANGUAGE = "c"
PROTOTYPE = (
    "void hilclaw_rope_bf16(size_t m, size_t h, size_t d, "
    "const uint16_t *restrict x, const float *restrict freqs_cis, "
    "uint16_t *restrict out);"
)
SHAPES = (
    (1, 32, 64),
    (128, 32, 64),
    (2048, 32, 64),
    (1, 8, 64),
    (128, 8, 64),
    (2048, 8, 64),
)
X_PATTERNS = (*range(0x3F00, 0x3F80), *range(0xBF00, 0xBF80))


def op_signature_record(m, h, d):
    """Return the op_signature record of the shape ``m``, ``h``, ``d`` under this contract.

    The result is a new ``dict`` with exactly the members ``schema_version``
    (:data:`hilclaw.keys.SCHEMA_VERSION`), ``kind`` (:data:`KIND`), ``shape``
    (a new ``dict`` ``{"m": m, "h": h, "d": d}``), ``dtype`` (:data:`DTYPE`)
    and ``layout`` (:data:`LAYOUT`), the rule of ADR-0161 decision 14. It has
    no ``label`` and no ``ext``. It is a record
    :func:`hilclaw.keys.op_signature_key` accepts; the key is not returned.

    Each of ``m``, ``h`` and ``d`` is exactly an ``int`` (``bool`` and other
    subclasses are refused, as in :mod:`hilclaw.keys`) from 1 to
    :data:`hilclaw.keys.MAX_INTEGER`, and ``d`` is even (ADR-0161 decision
    11: ``d`` is even and at least 2). The lower bound of 1 is the rule of
    ADR-0037 as decision 11 carries it over: the contract covers no shape that
    holds a 0 and no odd ``d``, so there is no op_signature record of it under
    this contract to return. Such a record is still valid for
    :func:`hilclaw.keys.op_signature_key`: the refusal says that the contract
    does not cover the shape, not that the record is invalid.

    Raises :class:`hilclaw.keys.InvalidRecordError` for a dimension that is
    not such an integer; the message starts with ``shape.`` and the name of
    the dimension. Nothing is returned then.
    """
    return {
        "schema_version": keys.SCHEMA_VERSION,
        "kind": KIND,
        "shape": _shape(m, h, d),
        "dtype": DTYPE,
        "layout": LAYOUT,
    }


def covers(record):
    """Return whether this contract covers the op_signature ``record``.

    ``record`` is an op_signature record, one that
    :func:`hilclaw.keys.op_signature_key` accepts. The result is ``True`` when
    its ``kind`` is :data:`KIND`, its ``dtype`` is :data:`DTYPE`, its
    ``layout`` is :data:`LAYOUT`, each of ``shape.m``, ``shape.h`` and
    ``shape.d`` is at least 1 and ``shape.d`` is even, and ``False``
    otherwise; a record of another dtype, fp32 included, is not covered. It is
    exactly a ``bool``. An ``ext`` and a ``label`` are not looked at for the
    answer. No bound is added to that of a valid record
    (:data:`hilclaw.keys.MAX_INTEGER`). ``True`` says that the record is one
    of this contract, not that a kernel, a build, a table or a target exists
    for it.

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
    if not all(shape[name] >= 1 for name in ("m", "h", "d")):
        return False
    return shape["d"] % 2 == 0


def task_contract(m, h, d):
    """Return the ``task.contract`` object of the shape ``m``, ``h``, ``d`` under this contract.

    The result is a new ``dict`` with exactly the members ``language``
    (:data:`LANGUAGE`), ``prototype`` (:data:`PROTOTYPE`) and ``operands``: a
    new ``list`` of three new ``dict`` objects in the order of the array
    parameters (ADR-0161 decision 10), each with exactly ``name``, ``role``,
    ``dtype`` and ``shape`` (a new ``list`` of integers, outermost dimension
    first):

    =========  ==========  =====================  =============
    name       role        dtype                  shape
    =========  ==========  =====================  =============
    x          ``input``   :data:`DTYPE`          ``[m, h, d]``
    freqs_cis  ``input``   :data:`TABLE_DTYPE`    ``[m, d]``
    out        ``output``  :data:`DTYPE`          ``[m, h, d]``
    =========  ==========  =====================  =============

    The dimensions have no entry. They follow the rule of
    :func:`op_signature_record`, and a refused one raises
    :class:`hilclaw.keys.InvalidRecordError` in the same way. Nothing is
    returned then. For a shape that holds a 0 or an odd ``d`` the contract has
    no ``task.contract`` and nothing is substituted.
    """
    _shape(m, h, d)
    return {
        "language": LANGUAGE,
        "prototype": PROTOTYPE,
        "operands": [
            _operand("x", "input", DTYPE, [m, h, d]),
            _operand("freqs_cis", "input", TABLE_DTYPE, [m, d]),
            _operand("out", "output", DTYPE, [m, h, d]),
        ],
    }


def _shape(m, h, d):
    shape = {"m": m, "h": h, "d": d}
    for name, value in shape.items():
        if type(value) is not int or not 1 <= value <= keys.MAX_INTEGER:
            got = reprlib.repr(value)
            raise keys.InvalidRecordError(
                f"shape.{name}: must be an integer from 1 to 2**53 - 1, got {got}"
            )
    if d % 2:
        raise keys.InvalidRecordError(f"shape.d: must be even, got {d}")
    return shape


def _operand(name, role, dtype, shape):
    return {"name": name, "role": role, "dtype": dtype, "shape": shape}
