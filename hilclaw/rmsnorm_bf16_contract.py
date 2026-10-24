"""Op-side values of a spec for the bf16 ``rmsnorm`` contract on ``cpu_standin`` (ADR-0158).

``ARCHITECTURE/decisions/ADR-0158-od31-bf16-rmsnorm-contract.md``, built on
ADR-0008 (the fp32 ``gemm`` contract whose call rules it reads with its own
kind, symbol and operands), ADR-0037 (no shape that holds a 0) and ADR-0156
(the bf16 ``gemm`` contract: ``uint16_t`` operands holding bf16 bit patterns,
the symbol form and the value set of the verification inputs), defines one
operational contract. It is bound to the kind ``rmsnorm``, the dtype ``bf16``,
the layout ``row_major`` and the kernel language ``c``, on the target
``cpu_standin`` (decisions 1 and 2). This module returns the values that
record fixes for a shape ``m``, ``n``: ``m`` rows of ``n`` elements each are
normalised and scaled by a weight of ``n`` elements. For a shape that holds a
0 it returns no values: ADR-0037's reading carries over to this contract
(decision 7). The values, and one test of a record:

* :data:`KIND`, :data:`DTYPE`, :data:`LAYOUT` and :data:`LANGUAGE`: the binding
  of the contract (decisions 1 and 2).
* :data:`PROTOTYPE`: the declaration of the entry point
  ``hilclaw_rmsnorm_bf16`` with its ``float`` parameter ``eps`` and its
  ``uint16_t`` arrays, the text of ``task.contract.prototype`` in every spec
  of this contract (decision 5).
* :func:`op_signature_record`: the op_signature record of a shape (the rule of
  decision 10).
* :func:`task_contract`: the ``task.contract`` object of a shape, with the
  three operand entries in the order of the parameters (decision 6).
* :data:`SHAPES`: the three shapes of the table of decision 10, in its order.
* :data:`INPUT_PATTERNS`: the 256 bf16 bit patterns of the value set of the
  verification inputs ``x`` and ``w`` (decision 9).
* :data:`EPS`: the ``eps`` of every verification call, the binary32 value
  nearest to 1e-05 (decision 9).
* :func:`covers`: whether an op_signature record is covered by this contract.

What the module does not do: it builds no spec and no other part of one - no
``task`` object, no ``task.objective``, no ``task.build`` and so no build
setting, no ``hw_profile``, no ``id``, no ``guidance`` and no ``feedback``. It
binds no kernel to a call site, is bound to no tool or registry, reads and
writes no file, starts no process, stores and registers nothing and has no
command-line entry. For :data:`INPUT_PATTERNS` and :data:`EPS` it holds the
values only: the generator, the seed, the number of draws, the content of
``y`` before a call, the ``eps`` the reference uses and the widening for the
reference belong to the P2-12 harness record (decision 9), and no tolerance
is chosen. It knows no other contract: no other kind, dtype, layout, language
or target.

The operation and its precision (decision 3), the rounding of the output
(decision 4), the guarantees and obligations of a call (decision 7) and what
the kernel source provides (decision 8) are not represented in any value
returned here, beyond what the prototype text itself states (``restrict``
states the no-overlap guarantee).
"""

import reprlib

from hilclaw import keys

KIND = "rmsnorm"
DTYPE = "bf16"
LAYOUT = "row_major"
LANGUAGE = "c"
PROTOTYPE = (
    "void hilclaw_rmsnorm_bf16(size_t m, size_t n, float eps, "
    "const uint16_t *restrict x, const uint16_t *restrict w, "
    "uint16_t *restrict y);"
)
SHAPES = ((1, 2048), (32, 2048), (512, 2048))
INPUT_PATTERNS = (*range(0x3F00, 0x3F80), *range(0xBF00, 0xBF80))
EPS = 9.999999747378752e-06


def op_signature_record(m, n):
    """Return the op_signature record of the shape ``m``, ``n`` under this contract.

    The result is a new ``dict`` with exactly the members ``schema_version``
    (:data:`hilclaw.keys.SCHEMA_VERSION`), ``kind`` (:data:`KIND`), ``shape``
    (a new ``dict`` ``{"m": m, "n": n}``), ``dtype`` (:data:`DTYPE`) and
    ``layout`` (:data:`LAYOUT`), the rule of ADR-0158 decision 10. It has no
    ``label`` and no ``ext``. It is a record
    :func:`hilclaw.keys.op_signature_key` accepts; the key is not returned.

    Each of ``m`` and ``n`` is exactly an ``int`` (``bool`` and other
    subclasses are refused, as in :mod:`hilclaw.keys`) from 1 to
    :data:`hilclaw.keys.MAX_INTEGER`. The lower bound of 1 is the rule of
    ADR-0037 as ADR-0158 decision 7 carries it over: the contract covers no
    shape that holds a 0, so there is no op_signature record of it under this
    contract to return. Such a record is still valid for
    :func:`hilclaw.keys.op_signature_key`: the refusal says that the contract
    does not cover the shape, not that the record is invalid.

    Raises :class:`hilclaw.keys.InvalidRecordError` for a dimension that is
    not such an integer; the message starts with ``shape.`` and the name of
    the dimension. Nothing is returned then.
    """
    return {
        "schema_version": keys.SCHEMA_VERSION,
        "kind": KIND,
        "shape": _shape(m, n),
        "dtype": DTYPE,
        "layout": LAYOUT,
    }


def covers(record):
    """Return whether this contract covers the op_signature ``record``.

    ``record`` is an op_signature record, one that
    :func:`hilclaw.keys.op_signature_key` accepts. The result is ``True`` when
    its ``kind`` is :data:`KIND`, its ``dtype`` is :data:`DTYPE`, its
    ``layout`` is :data:`LAYOUT` and each of ``shape.m`` and ``shape.n`` is at
    least 1, and ``False`` otherwise; a record of another dtype, fp32
    included, is not covered. It is exactly a ``bool``. An ``ext`` and a
    ``label`` are not looked at for the answer. No bound is added to that of
    a valid record (:data:`hilclaw.keys.MAX_INTEGER`). ``True`` says that the
    record is one of this contract, not that a kernel, a build or a target
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
    return all(record["shape"][name] >= 1 for name in ("m", "n"))


def task_contract(m, n):
    """Return the ``task.contract`` object of the shape ``m``, ``n`` under this contract.

    The result is a new ``dict`` with exactly the members ``language``
    (:data:`LANGUAGE`), ``prototype`` (:data:`PROTOTYPE`) and ``operands``: a
    new ``list`` of three new ``dict`` objects in the order of the array
    parameters (ADR-0158 decision 6), each with exactly ``name``, ``role``,
    ``dtype`` (:data:`DTYPE`) and ``shape`` (a new ``list`` of integers; rows
    then columns for ``x`` and ``y``, the length for the rank-1 ``w``):

    ====  ==========  ==========
    name  role        shape
    ====  ==========  ==========
    x     ``input``   ``[m, n]``
    w     ``input``   ``[n]``
    y     ``output``  ``[m, n]``
    ====  ==========  ==========

    The dimensions and ``eps`` have no entry. The dimensions follow the rule
    of :func:`op_signature_record`, and a refused one raises
    :class:`hilclaw.keys.InvalidRecordError` in the same way. Nothing is
    returned then. For a shape that holds a 0 the contract has no
    ``task.contract`` and nothing is substituted.
    """
    _shape(m, n)
    return {
        "language": LANGUAGE,
        "prototype": PROTOTYPE,
        "operands": [
            _operand("x", "input", [m, n]),
            _operand("w", "input", [n]),
            _operand("y", "output", [m, n]),
        ],
    }


def _shape(m, n):
    shape = {"m": m, "n": n}
    for name, value in shape.items():
        if type(value) is not int or not 1 <= value <= keys.MAX_INTEGER:
            got = reprlib.repr(value)
            raise keys.InvalidRecordError(
                f"shape.{name}: must be an integer from 1 to 2**53 - 1, got {got}"
            )
    return shape


def _operand(name, role, shape):
    return {"name": name, "role": role, "dtype": DTYPE, "shape": shape}
