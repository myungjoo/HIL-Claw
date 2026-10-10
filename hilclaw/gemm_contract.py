"""Op-side values of a spec for the first ``gemm`` contract (ADR-0008 decisions 1, 2, 4, 5 and 9).

``ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md``, built on
ADR-0001 (the fields of an op_signature) and ADR-0002 (the members of
``task.contract``), defines one operational contract. It is bound to the kind
``gemm``, the dtype ``fp32`` (the record cites #5 B-4), the layout
``row_major`` and the kernel language ``c`` (the record cites #5 A-7). This
module returns the values that record fixes for a shape ``m``, ``k``, ``n``,
where the product of an m x k and a k x n matrix is an m x n matrix. For a
shape that holds a 0 it returns none: by
``ARCHITECTURE/decisions/ADR-0037-od6-gemm-contract-zero-dimension.md``
(decision 2) the contract of ADR-0008 covers no such shape. The values:

* :data:`KIND`, :data:`DTYPE`, :data:`LAYOUT` and :data:`LANGUAGE`: the binding
  of the contract (decisions 1 and 2).
* :data:`PROTOTYPE`: the declaration of the entry point, the text of
  ``task.contract.prototype`` in every spec of this contract (decision 4).
* :func:`op_signature_record`: the op_signature record of a shape (the rule of
  decision 9).
* :func:`task_contract`: the ``task.contract`` object of a shape, with the
  three operand entries in the order of the parameters (decision 5).
* :data:`FIRST_SHAPES`: the shapes of the twelve first instances, in the order
  of the table of decision 9 (the record cites #5 B-4 for them).

What the module does not do: it builds no spec and no other part of one - no
``task`` object, no ``task.objective``, no ``task.build`` and so no build
setting, no ``hw_profile``, no ``id``, no ``guidance`` and no ``feedback``. It
does not check that the ``task.contract`` of a spec is the one of this record.
It knows no other contract: no other kind, dtype, layout or language. It reads
and writes no file, starts no process, stores and registers nothing, is bound
to no tool and has no command-line entry.

The guarantees and obligations of a call and what the source of a kernel
provides (decisions 6 and 7) are not represented in any value returned here,
beyond what the prototype text itself states (``restrict`` states the
no-overlap guarantee, decision 4): of the contract, only the language, the
prototype text and the operand entries travel in a spec (decision 8).
"""

import reprlib

from hilclaw import keys

KIND = "gemm"
DTYPE = "fp32"
LAYOUT = "row_major"
LANGUAGE = "c"
PROTOTYPE = (
    "void hilclaw_gemm(size_t m, size_t k, size_t n, "
    "const float *restrict a, const float *restrict b, float *restrict c);"
)
FIRST_SHAPES = tuple(
    (m, k, n)
    for k, n in ((2048, 8192), (8192, 2048), (2048, 3072), (2048, 2048))
    for m in (1, 32, 512)
)


def op_signature_record(m, k, n):
    """Return the op_signature record of the shape ``m``, ``k``, ``n`` under this contract.

    The result is a new ``dict`` with exactly the members ``schema_version``
    (:data:`hilclaw.keys.SCHEMA_VERSION`), ``kind`` (:data:`KIND`), ``shape``
    (a new ``dict`` ``{"m": m, "k": k, "n": n}``), ``dtype`` (:data:`DTYPE`)
    and ``layout`` (:data:`LAYOUT`). It has no ``label`` and no ``ext``. It is
    a record :func:`hilclaw.keys.op_signature_key` accepts; the key is not
    returned.

    Each of ``m``, ``k`` and ``n`` is exactly an ``int`` (``bool`` and other
    subclasses are refused, as in :mod:`hilclaw.keys`) from 1 to
    :data:`hilclaw.keys.MAX_INTEGER`. The lower bound of 1 is the rule of
    ADR-0037 (decision 2): the contract of ADR-0008 covers no shape that
    holds a 0, so the contract has no op-side values for such a shape and
    there is no op_signature record of it under this contract to return.
    ADR-0001 lets a shape value be 0, and ADR-0008 decision 6 has the caller
    of a kernel pass dimensions of at least 1, so a shape with a 0 describes a
    call this contract never has.

    A record with these members whose shape holds a 0 is still a valid
    op_signature record with a key for :func:`hilclaw.keys.op_signature_key`
    (ADR-0001, unchanged): the refusal says that the contract does not cover
    the shape, not that the record is invalid.

    Raises :class:`hilclaw.keys.InvalidRecordError` for a dimension outside
    that rule; the message starts with ``shape.`` and the name of the
    dimension. Nothing is returned then. The class is reused for a dimension
    of 0, which breaks no rule of ADR-0001: the rule refused there is the one
    of ADR-0037.
    """
    return {
        "schema_version": keys.SCHEMA_VERSION,
        "kind": KIND,
        "shape": _shape(m, k, n),
        "dtype": DTYPE,
        "layout": LAYOUT,
    }


def task_contract(m, k, n):
    """Return the ``task.contract`` object of the shape ``m``, ``k``, ``n`` under this contract.

    The result is a new ``dict`` with exactly the members ``language``
    (:data:`LANGUAGE`), ``prototype`` (:data:`PROTOTYPE`) and ``operands``: a
    new ``list`` of three new ``dict`` objects in the order of the parameters,
    each with exactly ``name``, ``role``, ``dtype`` (:data:`DTYPE`) and
    ``shape`` (a new ``list`` of two integers, rows then columns):

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
    has no ``task.contract`` and nothing is substituted (ADR-0037 decision 2).
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
