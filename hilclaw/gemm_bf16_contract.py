"""Op-side values of a spec for the bf16 ``gemm`` contract on ``cpu_standin`` (ADR-0156).

``ARCHITECTURE/decisions/ADR-0156-od31-bf16-gemm-contract.md``, built on
ADR-0008 (the fp32 ``gemm`` contract it reads with ``float`` as ``uint16_t``
and ``fp32`` as ``bf16``) and ADR-0037 (no shape that holds a 0), defines one
operational contract. It is bound to the kind ``gemm``, the dtype ``bf16``,
the layout ``row_major`` and the kernel language ``c``, on the target
``cpu_standin`` (decisions 1 and 2). This module returns the values that
record fixes for a shape ``m``, ``k``, ``n``, where the product of an m x k
and a k x n matrix is an m x n matrix. For a shape that holds a 0 it returns
no values: the record reads ADR-0037 (decision 2) as holding for this contract
as well (decision 7). The values, and one test of a record:

* :data:`KIND`, :data:`DTYPE`, :data:`LAYOUT` and :data:`LANGUAGE`: the binding
  of the contract (decisions 1 and 2).
* :data:`PROTOTYPE`: the declaration of the entry point
  ``hilclaw_gemm_bf16`` over ``uint16_t`` arrays, the text of
  ``task.contract.prototype`` in every spec of this contract (decision 5).
* :func:`op_signature_record`: the op_signature record of a shape (the rule of
  decision 10).
* :func:`task_contract`: the ``task.contract`` object of a shape, with the
  three operand entries in the order of the parameters (decision 6).
* :data:`SHAPES`: the fifteen shapes of the table of decision 10, in its
  order.
* :data:`INPUT_PATTERNS`: the 256 bf16 bit patterns of the value set of the
  verification inputs (decision 9).
* :func:`covers`: whether an op_signature record is covered by this contract.

What the module does not do: it builds no spec and no other part of one - no
``task`` object, no ``task.objective``, no ``task.build`` and so no build
setting, no ``hw_profile``, no ``id``, no ``guidance`` and no ``feedback``. It
binds no kernel to a call site, is bound to no tool or registry, reads and
writes no file, starts no process, stores and registers nothing and has no
command-line entry. For :data:`INPUT_PATTERNS` it holds the value set only:
the generator, the seed, the number of draws and the widening for the
reference belong to the P2-12 harness record (decision 9), and no tolerance is
chosen. It knows no other contract: no other kind, dtype, layout, language or
target.

The rounding, accumulation and call obligations of decisions 3, 4, 7 and 8 are
not represented in any value returned here, beyond what the prototype text
itself states (``restrict`` states the no-overlap guarantee).
"""

import reprlib

from hilclaw import keys

KIND = "gemm"
DTYPE = "bf16"
LAYOUT = "row_major"
LANGUAGE = "c"
PROTOTYPE = (
    "void hilclaw_gemm_bf16(size_t m, size_t k, size_t n, "
    "const uint16_t *restrict a, const uint16_t *restrict b, "
    "uint16_t *restrict c);"
)
SHAPES = tuple(
    (m, k, n)
    for k, n in ((2048, 8192), (8192, 2048), (2048, 3072), (2048, 2048), (2048, 128256))
    for m in (1, 32, 512)
)
INPUT_PATTERNS = (*range(0x3F00, 0x3F80), *range(0xBF00, 0xBF80))


def op_signature_record(m, k, n):
    """Return the op_signature record of the shape ``m``, ``k``, ``n`` under this contract.

    The result is a new ``dict`` with exactly the members ``schema_version``
    (:data:`hilclaw.keys.SCHEMA_VERSION`), ``kind`` (:data:`KIND`), ``shape``
    (a new ``dict`` ``{"m": m, "k": k, "n": n}``), ``dtype`` (:data:`DTYPE`)
    and ``layout`` (:data:`LAYOUT`), the rule of ADR-0156 decision 10. It has
    no ``label`` and no ``ext``. It is a record
    :func:`hilclaw.keys.op_signature_key` accepts; the key is not returned.

    Each of ``m``, ``k`` and ``n`` is exactly an ``int`` (``bool`` and other
    subclasses are refused, as in :mod:`hilclaw.keys`) from 1 to
    :data:`hilclaw.keys.MAX_INTEGER`. The lower bound of 1 is the rule of
    ADR-0037 (decision 2) as ADR-0156 decision 7 reads it: the contract covers
    no shape that holds a 0, so there is no op_signature record of it under
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
        "shape": _shape(m, k, n),
        "dtype": DTYPE,
        "layout": LAYOUT,
    }


def covers(record):
    """Return whether this contract covers the op_signature ``record``.

    ``record`` is an op_signature record, one that
    :func:`hilclaw.keys.op_signature_key` accepts. The result is ``True`` when
    its ``kind`` is :data:`KIND`, its ``dtype`` is :data:`DTYPE`, its
    ``layout`` is :data:`LAYOUT` and each of ``shape.m``, ``shape.k`` and
    ``shape.n`` is at least 1, and ``False`` otherwise; an fp32 record is not
    covered. It is exactly a ``bool``. An ``ext`` and a ``label`` are not
    looked at for the answer. No bound is added to that of a valid record
    (:data:`hilclaw.keys.MAX_INTEGER`). ``True`` says that the record is one
    of this contract, not that a kernel, a build or a target exists for it.

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
    return all(record["shape"][name] >= 1 for name in ("m", "k", "n"))


def task_contract(m, k, n):
    """Return the ``task.contract`` object of the shape ``m``, ``k``, ``n`` under this contract.

    The result is a new ``dict`` with exactly the members ``language``
    (:data:`LANGUAGE`), ``prototype`` (:data:`PROTOTYPE`) and ``operands``: a
    new ``list`` of three new ``dict`` objects in the order of the parameters
    (ADR-0156 decision 6), each with exactly ``name``, ``role``, ``dtype``
    (:data:`DTYPE`) and ``shape`` (a new ``list`` of two integers, rows then
    columns):

    ====  ==========  ==========
    name  role        shape
    ====  ==========  ==========
    a     ``input``   ``[m, k]``
    b     ``input``   ``[k, n]``
    c     ``output``  ``[m, n]``
    ====  ==========  ==========

    The dimensions follow the rule of :func:`op_signature_record`, and a
    refused one raises :class:`hilclaw.keys.InvalidRecordError` in the same
    way. Nothing is returned then. For a shape that holds a 0 the contract
    has no ``task.contract`` and nothing is substituted.
    """
    _shape(m, k, n)
    return {
        "language": LANGUAGE,
        "prototype": PROTOTYPE,
        "operands": [
            _operand("a", "input", m, k),
            _operand("b", "input", k, n),
            _operand("c", "output", m, n),
        ],
    }


def _shape(m, k, n):
    shape = {"m": m, "k": k, "n": n}
    for name, value in shape.items():
        if type(value) is not int or not 1 <= value <= keys.MAX_INTEGER:
            got = reprlib.repr(value)
            raise keys.InvalidRecordError(
                f"shape.{name}: must be an integer from 1 to 2**53 - 1, got {got}"
            )
    return shape


def _operand(name, role, rows, columns):
    return {"name": name, "role": role, "dtype": DTYPE, "shape": [rows, columns]}
