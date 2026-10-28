"""The mock's side of ``correctness.check``: its operation and the default script's answer.

``ARCHITECTURE/decisions/ADR-0044-od18-correctness-check-mock-script.md`` is
the rule; a decision cited by its number alone is one of that record. The
module renders its decisions 2 to 4, with the check parameters of ADR-0043
decision 2 (:class:`hilclaw.check_parameters.CheckParameters`), the output
path of ADR-0056 decision 3 and the log keeper of
``ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md``
decision 6, which extend decision 2 by two things:

* :func:`operation`: the mock's operation of this tool bound to a script
  (decision 2). The script is asked once for each call, with the called tool
  and the five things the operation was called with, as they are, and its
  answer is the operation's answer. The operation does not look at it. A
  script may hand a log to the keeper, which the tool function then writes
  as any other (ADR-0078 decisions 2 and 6).
* :func:`default_script`: what the default script answers for this tool
  (decision 3), a complete report that holds for each draw the right product
  by the rule of decision 4. It hands over no log (ADR-0078 decisions 2
  and 6), so a run at the mock with it leaves no file of a compiler's log.

For a check of a bf16 kind
(``ARCHITECTURE/decisions/ADR-0177-od18-od6-contract-table.md`` decision 3,
"The mock") the operation is handed a
:class:`hilclaw.check_parameters.Bf16CheckParameters` and asks its script
with it in the same way, and :func:`default_script` answers for it the
complete report of ADR-0163 decision 8 of a conforming kernel of that
contract, computed with :mod:`hilclaw.harness.bf16_verification_arrays`: per
draw the check value of the drawn operands and each output element the bf16
value nearest to the float64 reference of the kind, a tie going to the even
one. Of all bf16 values it is the nearest, so a tolerance under which a
conforming kernel passes (ADR-0163 decision 9) passes it as well. For
``sdpa_kv_cache`` it is the complete report of ADR-0165 decision 8, computed
with :mod:`hilclaw.harness.bf16_sdpa_kv_cache_arrays` in the same way
(ADR-0177 decision 3): per draw the check value of the drawn inputs and the
two allocations before the call, ``out`` as the bf16 values nearest to the
float64 reference, and the two allocations as a conforming kernel leaves
them, so the cache comparison finds no difference. For ``rope`` it is the
complete report of ADR-0164 decision 10, computed with
:mod:`hilclaw.harness.bf16_rope_arrays` at the start position
:func:`hilclaw.harness.bf16_rope_verification.start_position` gives for the
dims and the seed (ADR-0180 decision 1): per draw the check value of ``x``
and those rows and ``out`` as the bf16 values nearest to the float64
reference.

Choices that are this module's own and no rule of a record:

* A script of this tool is asked with six positional things:
  ``script("correctness.check", request, hw_profile, parameters,
  output_path, keeper)``. An operation is called with five positional things
  and no keyword; the output path is the fourth of them and the keeper the
  last.
* :func:`default_script` has the six parameters of a script and reads the
  check parameters only. The output path is not read, checked or converted,
  whatever its type is (ADR-0056 decision 3), and the keeper is handed
  nothing and not looked at.
* The report is computed with the harness of the same source commit:
  :func:`hilclaw.harness.verification_arrays.draw_inputs`, ``check_value``
  and ``reference`` give the inputs, the check value and the float64 product
  of a draw, NumPy's conversion to ``float32`` rounds each element to the
  nearest value with a tie going to the even one under the default rounding
  mode, and the check value is written with ``struct`` format ``=I`` and
  followed after the last draw by
  :data:`hilclaw.harness.verification.END_MARK`, as
  :func:`hilclaw.harness.verification.judge_report` reads them.
* What :func:`default_script` raises, and in which order: see there.
* The nearest bf16 value is found in float64 without passing through
  ``float32``, which would round twice: the element is scaled by a power of
  two so that its last kept bit is the unit, rounded with ``numpy.rint``,
  scaled back and converted exactly.

The limit of sharing that code is that of decision 7: a defect of the
generator, of the check function or of the float64 product that this script
and the judging share is not seen by a check answered by this script.

What the module does not do: it builds no backend and no backend table and
registers nothing; the default registry binds :func:`operation` and
:func:`default_script` (ADR-0070). It is not the whole default script of the default
registry: it says nothing of the other three HW tools. It injects no fault
(OD-18 sub-question 8, open). It is handed no tolerance and judges nothing.
It gives no value or default of a number of draws, a seed or a dimension. It
says nothing of what a call answers when the answer of a script has neither
form of ADR-0043 decision 4 or when the default script raises. It reads no
clock, random source, counter, file or environment variable, starts no
process and keeps nothing between calls. It looks at nothing at the output
path, writes no file and hands no log over of its own.
"""

import struct

import numpy as np

from hilclaw import check_parameters
from hilclaw.harness import (
    bf16_rope_arrays,
    bf16_rope_verification,
    bf16_sdpa_kv_cache_arrays,
    bf16_sdpa_kv_cache_verification,
    bf16_verification,
    bf16_verification_arrays,
    verification,
    verification_arrays,
)

_TOOL = "correctness.check"
_SDPA = "sdpa_kv_cache"
_ROPE = "rope"


class _Operation:
    __slots__ = ("_script",)

    def __init__(self, script):
        self._script = script

    def __call__(self, request, hw_profile, parameters, output_path, keeper, /):
        return self._script(_TOOL, request, hw_profile, parameters, output_path, keeper)

    def __repr__(self):
        return f"<operation of the mock backend for {_TOOL!r}>"


def operation(script):
    """Return the mock's operation of ``correctness.check`` bound to ``script``.

    - ``script``: a callable asked as
      ``script("correctness.check", request, hw_profile, parameters,
      output_path, keeper)``.

    The operation returned is called as
    ``operation(request, hw_profile, parameters, output_path, keeper)``,
    with exactly these five positional arguments: the request, the
    hw_profile of the call, the check parameters, the output path (ADR-0056
    decision 3) and the log keeper (ADR-0078 decision 6). It asks the script
    once with the five objects as they are and returns the object the script
    returned, whatever it is. It looks at none of the five, at nothing at
    the output path and not at the answer, hands the keeper nothing itself
    and catches nothing: whatever the script raises passes through unchanged,
    a :class:`hilclaw.tools.ToolFailure` of any kind as well as any other
    :class:`BaseException`.

    The operation can be given to :class:`hilclaw.backends.Backend` as the
    operation of this tool; this function builds no backend.

    Raises :class:`TypeError` when ``script`` is not callable. Building asks
    the script nothing.
    """
    if not callable(script):
        raise TypeError("the script of a mock operation must be callable")
    return _Operation(script)


def default_script(tool, request, hw_profile, parameters, output_path, keeper):
    """Return the default script's answer for ``correctness.check``, as ``bytes``.

    - ``tool``, ``request``, ``hw_profile``: what a script is asked with
      before the check parameters. They are not read, checked or modified.
    - ``parameters``: the check parameters, exactly a
      :class:`hilclaw.check_parameters.CheckParameters`.
    - ``output_path``: the output path a script is asked with after the
      check parameters. It is not read, checked or modified, and nothing at
      it is looked at.
    - ``keeper``: the log keeper a script is asked with last. It is handed
      no log and not looked at (ADR-0078 decision 6).

    For a ``CheckParameters`` the answer is a complete report for the
    ``m``, ``n`` and ``draws`` of ``parameters``, ``draws * (4 + 4*m*n) + 4``
    bytes. For each draw in order it holds the check value of the inputs
    drawn for the seed, the draw and the dimensions, then the ``m*n`` fp32
    elements of their product in row-major order as the bytes they have on
    the host: each element is the fp32 value nearest to the corresponding
    element of the float64 product of the inputs widened to float64, a tie
    going to the value whose last significand bit is 0. After the last draw
    it holds the end mark, and nothing else (decision 4).

    The answer follows from ``parameters`` alone. It is never one of the four
    strings of the form (B) of ADR-0043 decision 4, as ADR-0060 decision 4
    has it, and never anything but ``bytes``.

    For a :class:`hilclaw.check_parameters.Bf16CheckParameters` the answer
    is the complete report of ADR-0163 decision 8 for its kind, dims and
    draws, ``draws * (4 + 2*m*n) + 4`` bytes with ``m`` and ``n`` the first
    and the last dimension: for each draw the check value of the operands
    :func:`hilclaw.harness.bf16_verification_arrays.draw_inputs` gives for
    the seed, the draw, the kind and the dims, then the ``m*n`` bf16
    patterns, as the bytes they have on the host, of the values nearest to
    the elements of the float64 reference of the kind
    (:func:`hilclaw.harness.bf16_verification_arrays.reference`), a tie
    going to the value whose last significand bit is 0; then the end mark.
    For the kind ``sdpa_kv_cache`` the answer is the complete report of
    ADR-0165 decision 8 for its dims ``(m, l, h, h_kv, d)`` and draws,
    ``draws * (4 + 2*m*h*d + 4*(l + 2*m)*h_kv*d) + 4`` bytes: for each draw
    the check value of the inputs
    :func:`hilclaw.harness.bf16_sdpa_kv_cache_arrays.draw_inputs` gives and
    of the two allocations before the call, then the ``m*h*d`` patterns of
    the bf16 values nearest to the elements of its float64 reference, a tie
    going to the even one, then the ``cache_k`` and the ``cache_v``
    allocation as
    :func:`hilclaw.harness.bf16_sdpa_kv_cache_arrays.allocation_after`
    gives them; then the end mark. For the kind ``rope`` the answer is the
    complete report of ADR-0164 decision 10 for its dims ``(m, h, d)`` and
    draws, ``draws * (4 + 2*m*h*d) + 4`` bytes: the rows
    :func:`hilclaw.harness.bf16_rope_arrays.table_rows` gives at the start
    position of
    :func:`hilclaw.harness.bf16_rope_verification.start_position` are built
    once, and for each draw the answer holds the check value of the ``x``
    :func:`hilclaw.harness.bf16_rope_arrays.draw_x` gives and of those
    rows, then the ``m*h*d`` patterns of the bf16 values nearest to the
    elements of their float64 reference, a tie going to the even one; then
    the end mark.
    Raised first for it: :class:`ValueError` for a ``dtype`` that is not
    :data:`hilclaw.check_parameters.BF16`, then, unchanged, the
    ``VerificationArgumentError`` of
    :func:`hilclaw.harness.bf16_verification.program_arguments`, or for
    ``sdpa_kv_cache`` of
    :func:`hilclaw.harness.bf16_sdpa_kv_cache_verification.program_arguments`,
    or for ``rope`` of
    :func:`hilclaw.harness.bf16_rope_verification.program_arguments` and
    then of ``start_position``, for a kind, dims, draws or seed it refuses.

    Raised, in this order and before any input is drawn: :class:`TypeError`
    for ``parameters`` that are neither exactly a ``CheckParameters`` nor
    exactly a ``Bf16CheckParameters``;
    :class:`hilclaw.harness.verification_arrays.VerificationArgumentError`,
    unchanged, for five values that
    :func:`hilclaw.harness.verification.program_arguments` refuses; what
    Python raises for a report of a size it cannot hold. What NumPy raises
    for arrays it cannot allocate is passed on as well. The function puts no
    bound of its own on any of the five values.

    The whole report is held twice at the end, once as it was filled and once
    as the ``bytes`` returned; the arrays of one draw are not kept for the
    next.
    """
    if type(parameters) is check_parameters.Bf16CheckParameters:
        return _bf16_report(parameters)
    if type(parameters) is not check_parameters.CheckParameters:
        raise TypeError(
            "parameters: must be CheckParameters or Bf16CheckParameters,"
            f" got {type(parameters).__name__}"
        )
    seed, draws, m, k, n = parameters
    verification.program_arguments(m=m, k=k, n=n, draws=draws, seed=seed)
    block = 4 + 4 * m * n
    report = bytearray(draws * block + len(verification.END_MARK))
    for draw in range(draws):
        a, b = verification_arrays.draw_inputs(m, k, n, seed=seed, draw=draw)
        start = draw * block
        struct.pack_into("=I", report, start, verification_arrays.check_value(a, b))
        product = verification_arrays.reference(a, b).astype(np.float32)
        report[start + 4 : start + block] = product.tobytes()
    report[draws * block :] = verification.END_MARK
    return bytes(report)


def _bf16_report(parameters):
    seed, draws, kind, dtype, dims = parameters
    if dtype != check_parameters.BF16:
        raise ValueError(f"parameters.dtype: must be {check_parameters.BF16!r}")
    if type(kind) is str and kind == _SDPA:
        return _sdpa_report(dims, draws, seed)
    if type(kind) is str and kind == _ROPE:
        return _rope_report(dims, draws, seed)
    bf16_verification.program_arguments(kind, dims, draws=draws, seed=seed)
    arrays = bf16_verification_arrays
    block = 4 + 2 * dims[0] * dims[-1]
    report = bytearray(draws * block + len(bf16_verification.END_MARK))
    for draw in range(draws):
        first, second = arrays.draw_inputs(kind, dims, seed=seed, draw=draw)
        start = draw * block
        struct.pack_into("=I", report, start, arrays.check_value(first, second))
        output = _nearest_bf16(arrays.reference(kind, first, second))
        report[start + 4 : start + block] = output.tobytes()
    report[draws * block :] = bf16_verification.END_MARK
    return bytes(report)


def _sdpa_report(dims, draws, seed):
    bf16_sdpa_kv_cache_verification.program_arguments(dims, draws=draws, seed=seed)
    arrays = bf16_sdpa_kv_cache_arrays
    m, l, h, h_kv, d = dims
    output = 2 * m * h * d
    block = 4 + output + 4 * (l + 2 * m) * h_kv * d
    report = bytearray(draws * block + len(bf16_verification.END_MARK))
    for draw in range(draws):
        inputs = arrays.draw_inputs(dims, seed=seed, draw=draw)
        before = [
            arrays.allocation_before(dims, cached)
            for cached in (inputs.cached_k, inputs.cached_v)
        ]
        value = arrays.check_value(dims, *inputs[:3], *before)
        start = draw * block
        struct.pack_into("=I", report, start, value)
        out = _nearest_bf16(arrays.reference(dims, *inputs))
        after = [
            arrays.allocation_after(dims, cached, new)
            for cached, new in (
                (inputs.cached_k, inputs.k_new),
                (inputs.cached_v, inputs.v_new),
            )
        ]
        report[start + 4 : start + block] = b"".join(
            part.tobytes() for part in (out, *after)
        )
    report[draws * block :] = bf16_verification.END_MARK
    return bytes(report)


def _rope_report(dims, draws, seed):
    bf16_rope_verification.program_arguments(dims, draws=draws, seed=seed)
    start = bf16_rope_verification.start_position(dims, seed=seed)
    arrays = bf16_rope_arrays
    rows = arrays.table_rows(dims, start=start)
    m, h, d = dims
    block = 4 + 2 * m * h * d
    report = bytearray(draws * block + len(bf16_verification.END_MARK))
    for draw in range(draws):
        x = arrays.draw_x(dims, seed=seed, draw=draw)
        start_of_draw = draw * block
        struct.pack_into("=I", report, start_of_draw, arrays.check_value(x, rows))
        output = _nearest_bf16(arrays.reference(x, rows))
        report[start_of_draw + 4 : start_of_draw + block] = output.tobytes()
    report[draws * block :] = bf16_verification.END_MARK
    return bytes(report)


def _nearest_bf16(values):
    _, exponent = np.frexp(values)
    unit = np.maximum(exponent, -125) - 8
    with np.errstate(over="ignore"):
        rounded = np.ldexp(np.rint(np.ldexp(values, -unit)), unit).astype(np.float32)
    return (rounded.view(np.uint32) >> 16).astype(np.uint16)
