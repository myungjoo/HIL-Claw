"""The mock's side of ``correctness.check``: its operation and the default script's answer.

``ARCHITECTURE/decisions/ADR-0044-od18-correctness-check-mock-script.md`` is
the rule; a decision cited by its number alone is one of that record. The
module renders its decisions 2 to 4, with the check parameters of ADR-0043
decision 2 (:class:`hilclaw.check_parameters.CheckParameters`):

* :func:`operation`: the mock's operation of this tool bound to a script
  (decision 2). The script is asked once for each call, with the called tool
  and the three things the operation was called with, as they are, and its
  answer is the operation's answer. The operation does not look at it.
* :func:`default_script`: what the default script answers for this tool
  (decision 3), a complete report that holds for each draw the right product
  by the rule of decision 4.

Choices that are this module's own and no rule of a record:

* A script of this tool is asked with four positional things:
  ``script("correctness.check", request, hw_profile, parameters)``. An
  operation is called with three positional things and no keyword.
* :func:`default_script` has the four parameters of a script and reads the
  last one only.
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

The limit of sharing that code is that of decision 7: a defect of the
generator, of the check function or of the float64 product that this script
and the judging share is not seen by a check answered by this script.

What the module does not do: it builds no backend and no backend table and is
bound to no registry. It is not the whole default script of the default
registry: it says nothing of the other three HW tools. It injects no fault
(OD-18 sub-question 8, open). It is handed no tolerance and judges nothing.
It gives no value or default of a number of draws, a seed or a dimension. It
says nothing of what a call answers when the answer of a script has neither
form of ADR-0043 decision 4 or when the default script raises. It reads no
clock, random source, counter, file or environment variable, starts no
process and keeps nothing between calls.
"""

import struct

import numpy as np

from hilclaw import check_parameters
from hilclaw.harness import verification, verification_arrays

_TOOL = "correctness.check"


class _Operation:
    __slots__ = ("_script",)

    def __init__(self, script):
        self._script = script

    def __call__(self, request, hw_profile, parameters, /):
        return self._script(_TOOL, request, hw_profile, parameters)

    def __repr__(self):
        return f"<operation of the mock backend for {_TOOL!r}>"


def operation(script):
    """Return the mock's operation of ``correctness.check`` bound to ``script``.

    - ``script``: a callable asked as
      ``script("correctness.check", request, hw_profile, parameters)``.

    The operation returned is called as
    ``operation(request, hw_profile, parameters)``, with exactly these three
    positional arguments: the request, the hw_profile of the call and the
    check parameters (ADR-0043 decision 2). It asks the script once with the
    three objects as they are and returns the object the script returned,
    whatever it is. It looks at none of the three and not at the answer, and
    it catches nothing: whatever the script raises passes through unchanged,
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


def default_script(tool, request, hw_profile, parameters):
    """Return the default script's answer for ``correctness.check``, as ``bytes``.

    - ``tool``, ``request``, ``hw_profile``: what a script is asked with
      before the check parameters. They are not read, checked or modified.
    - ``parameters``: the check parameters, exactly a
      :class:`hilclaw.check_parameters.CheckParameters`.

    The answer is a complete report for the ``m``, ``n`` and ``draws`` of
    ``parameters``, ``draws * (4 + 4*m*n) + 4`` bytes. For each draw in
    order it holds the check value of the inputs drawn for the seed, the
    draw and the dimensions, then the ``m*n`` fp32 elements of their product
    in row-major order as the bytes they have on the host: each element is
    the fp32 value nearest to the corresponding element of the float64
    product of the inputs widened to float64, a tie going to the value whose
    last significand bit is 0. After the last draw it holds the end mark, and
    nothing else (decision 4).

    The answer follows from ``parameters`` alone. It is never one of the two
    strings of ADR-0043 decision 4 and never anything but ``bytes``.

    Raised, in this order and before any input is drawn: :class:`TypeError`
    for ``parameters`` that are not exactly a ``CheckParameters``;
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
    if type(parameters) is not check_parameters.CheckParameters:
        raise TypeError(
            f"parameters: must be CheckParameters, got {type(parameters).__name__}"
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
