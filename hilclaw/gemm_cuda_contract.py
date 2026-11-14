"""The fp32 ``gemm`` contract in the language ``cuda`` (ADR-0207 decision 4).

``ARCHITECTURE/decisions/ADR-0207-od33-cuda-target-demonstration.md``
decision 4 adds a second entry to the contract table for the kind ``gemm``,
the dtype ``fp32`` and the layout ``row_major``: the kernel is CUDA C++ and
its entry point takes **device pointers**. Everything else is the contract of
ADR-0008 as :mod:`hilclaw.gemm_contract` gives it, reused and not copied: the
shapes, the operands, the inputs and the reference, what a record covers and
the op_signature record of a shape. The values:

* :data:`KIND`, :data:`DTYPE` and :data:`LAYOUT`: those of
  :mod:`hilclaw.gemm_contract`; :data:`LANGUAGE` is ``cuda``.
* :data:`PROTOTYPE`: the declaration of decision 4, the text of
  ``task.contract.prototype``. ``a``, ``b`` and ``c`` are device pointers;
  the kernel launches its work on the default stream, may return before it
  completes, keeps no device memory past the call and copies nothing between
  host and device. The harness owns the context, the allocations, the copies
  and the waits (:mod:`hilclaw.harness.cuda_programs`).
* :data:`FIRST_SHAPES`, :func:`op_signature_record` and :func:`covers`: those
  of :mod:`hilclaw.gemm_contract`.
* :func:`task_contract`: :func:`hilclaw.gemm_contract.task_contract` with
  :data:`LANGUAGE` and :data:`PROTOTYPE` in place of its own.

The op_signature record states no language (ADR-0031 decision 2), so which
of the two fp32 ``gemm`` entries answers a record is the contract table's
(:mod:`hilclaw.contract_table`): this entry is served at ``cuda_gpu`` alone
(ADR-0207 decision 3), and a record asked without a target is answered by
the ``c`` entry, which comes first.

What the module does not do: it builds no spec, generates no program, reads
and writes no file, starts no process and has no command-line entry.
"""

from hilclaw import gemm_contract

KIND = gemm_contract.KIND
DTYPE = gemm_contract.DTYPE
LAYOUT = gemm_contract.LAYOUT
LANGUAGE = "cuda"
PROTOTYPE = (
    'extern "C" void hilclaw_gemm(size_t m, size_t k, size_t n, '
    "const float *a, const float *b, float *c);"
)
FIRST_SHAPES = gemm_contract.FIRST_SHAPES

op_signature_record = gemm_contract.op_signature_record
covers = gemm_contract.covers


def task_contract(m, k, n):
    """Return the ``task.contract`` object of the shape ``m``, ``k``, ``n`` under this contract.

    The result is that of :func:`hilclaw.gemm_contract.task_contract` for the
    same shape, a new ``dict`` with ``language`` :data:`LANGUAGE` and
    ``prototype`` :data:`PROTOTYPE` and the same three operand entries, in
    the same member order. A refused dimension raises
    :class:`hilclaw.keys.InvalidRecordError` as that function raises it.
    """
    return gemm_contract.task_contract(m, k, n) | {
        "language": LANGUAGE,
        "prototype": PROTOTYPE,
    }
