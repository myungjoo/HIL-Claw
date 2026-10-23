"""Model executor's GEMM path of ADR-0153 code slice 1: binding check joined with build and run.

``ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`` is the rule
(decisions 3 and 5). :func:`run` checks a binding of the GEMM call sites
against one generation with :func:`hilclaw.model_binding.check` and, when the
check is ok, builds the bound kernels and the model program and runs one call
per checked ``(call_site, shape)`` with :func:`hilclaw.model_execute.execute`.
The five outcomes of decision 5 are told apart from the returned
:class:`GemmRun` alone:

- ``"invalid_input"``, ``"no_kernel"`` and ``"kernel_unfit"``: ``check.ok``
  is false and ``check.outcomes`` names them; ``calls`` is ``()`` and
  ``execution`` is ``None``.
- **build failed**: ``execution.build_failed``; its ``kernel`` index ``i``
  belongs to every entry of ``calls`` whose index is ``i`` (``None`` is the
  model program).
- **run failed**: ``execution.run.failed``.

When the run succeeded, ``execution.run.outputs[i]`` is the output of
``calls[i]``.

Readings of this module (not rules of the record):

- Decision 3 gives each kernel "a shared library of its own". Two kernel
  references that compare equal (``==``) are read as one kernel: the kernel
  list holds the distinct kernels of ``check.calls`` in order of first use,
  one library each, and the calls that use one share its index.
- Slice 2's forward pass does not exist yet, so the caller supplies the
  operands of every call; this module chooses no array, weight, dtype, cast,
  reference or tolerance, compares nothing and has no fallback for a missing
  kernel (decision 5).

What this module does not do: no forward pass, embedding, KV cache or token
selection; no file outside the build directory of
:func:`hilclaw.model_execute.execute`; no data-plane file, registry entry,
MCP name or command-line entry. Arguments are not modified.
"""

from collections.abc import Mapping
from typing import NamedTuple

from hilclaw import model_binding, model_execute


class GemmRun(NamedTuple):
    """Outcome of one :func:`run` call.

    ``check`` is the :class:`hilclaw.model_binding.BindingCheck` as returned;
    ``calls`` holds ``(call_site, shape, index)`` per call in program order,
    ``index`` the kernel's position in the kernel list, and is ``()`` when the
    check is not ok; ``execution`` is the
    :class:`hilclaw.model_execute.ModelExecution` as returned, or ``None``
    when the check is not ok.
    """

    check: model_binding.BindingCheck
    calls: tuple
    execution: model_execute.ModelExecution | None


def run(
    dimensions,
    binding,
    operands,
    *,
    prompt,
    generation_length,
    lm_head_rows,
    given=None,
    build_timeout_s,
    run_timeout_s,
    program_flags=(),
    program_trailing_flags=(),
    compiler=None,
    env=None,
    prefix=(),
    parent=None,
    keep_out=(),
):
    """Check ``binding`` for one generation and, if ok, build and run its GEMM calls; return a :class:`GemmRun`.

    ``dimensions``, ``binding``, ``prompt``, ``generation_length``,
    ``lm_head_rows`` and ``given`` go to
    :func:`hilclaw.model_binding.check`; what it raises is passed on
    unchanged. If the check is not ok, the result is ``GemmRun(check, (),
    None)``: nothing is built, started or made, and ``operands`` is not looked
    at.

    If the check is ok, ``operands`` maps each ``(call_site, shape)`` of
    ``check.calls``, ``shape`` the ``(m, k, n)`` tuple, to a pair ``(a, b)``
    (a ``tuple`` or ``list`` of two items). It is looked at after the check,
    and refused before anything is made, in this order: :class:`TypeError`
    for an ``operands`` that is not a :class:`collections.abc.Mapping`; then
    per call in program order :class:`ValueError` for a missing key,
    :class:`TypeError` for a value that is not a pair and :class:`ValueError`
    for an ``a`` or ``b`` whose ``shape`` is a pair other than ``(m, k)`` or
    ``(k, n)``; then :class:`ValueError` for a key that is no call of the
    check. Each message names the key. An array of another dtype, of another
    number of dimensions or that is no :class:`numpy.ndarray` reaches
    :func:`hilclaw.model_execute.execute`, whose error is passed on unchanged.

    ``execute`` gets the kernel list, one ``(index, a, b)`` per entry of
    ``check.calls`` in its order, and every remaining keyword unchanged; what
    it raises is passed on unchanged.
    """
    check = model_binding.check(
        dimensions,
        binding,
        prompt=prompt,
        generation_length=generation_length,
        lm_head_rows=lm_head_rows,
        given=given,
    )
    if not check.ok:
        return GemmRun(check, (), None)
    pairs = _checked_operands(operands, check.calls)
    kernels = []
    calls = []
    program_calls = []
    for (call_site, shape, kernel), (a, b) in zip(check.calls, pairs, strict=True):
        index = next((i for i, known in enumerate(kernels) if known == kernel), None)
        if index is None:
            index = len(kernels)
            kernels.append(kernel)
        calls.append((call_site, shape, index))
        program_calls.append((index, a, b))
    execution = model_execute.execute(
        kernels,
        program_calls,
        build_timeout_s=build_timeout_s,
        run_timeout_s=run_timeout_s,
        program_flags=program_flags,
        program_trailing_flags=program_trailing_flags,
        compiler=compiler,
        env=env,
        prefix=prefix,
        parent=parent,
        keep_out=keep_out,
    )
    return GemmRun(check, tuple(calls), execution)


def _checked_operands(operands, checked_calls):
    if not isinstance(operands, Mapping):
        raise TypeError(f"operands: must be a mapping, got {type(operands).__name__}")
    pairs = []
    keys = set()
    for call_site, shape, _ in checked_calls:
        key = (call_site, shape)
        keys.add(key)
        if key not in operands:
            raise ValueError(f"operands[{key!r}]: is missing")
        pair = operands[key]
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise TypeError(
                f"operands[{key!r}]: must be a pair (a, b), got {type(pair).__name__}"
            )
        m, k, n = shape
        for name, array, expected in (("a", pair[0], (m, k)), ("b", pair[1], (k, n))):
            actual = getattr(array, "shape", None)
            if isinstance(actual, tuple) and len(actual) == 2 and actual != expected:
                raise ValueError(
                    f"operands[{key!r}]: {name} has shape {actual}, not {expected}"
                )
        pairs.append(tuple(pair))
    for key in operands:
        if key not in keys:
            raise ValueError(f"operands[{key!r}]: is no call of the check")
    return pairs
