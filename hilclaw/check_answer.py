"""From what an operation of ``correctness.check`` returned to the result of the check.

``ARCHITECTURE/decisions/ADR-0043-od18-correctness-check-operation-form.md``
fixes what an operation returns (decision 4): a byte string, which is the
report, or one of the two strings ``"time_limit"`` and ``"exit_status"``,
which says that there is no report and which condition failed. An answer of
neither form "is never made into a result" (decision 5). This module renders
the two decisions:

* :func:`from_answer`: the result for one answer. A byte string is judged by
  :func:`hilclaw.check_judging.from_report`, whatever its bytes are; one of
  the two strings becomes a broken result by
  :func:`hilclaw.check_result.broken`, with the string as its ``condition``
  and without any judging.
* :class:`NeitherFormError`: raised for an answer of neither form.

Choices that are this module's own and no rule of a record:

* A byte string is exactly ``bytes``, which is what
  :func:`hilclaw.harness.verification.judge_report` takes, and a string is
  exactly ``str``, as :func:`hilclaw.check_result.broken` takes its
  condition. A ``bytearray``, a ``memoryview`` and an instance of a subclass
  of ``bytes`` or of ``str`` are neither form.
* The two strings are the first two items of
  :data:`hilclaw.check_result.CONDITIONS` and are compared as they are. The
  other two items are values of ``condition`` that only the judging of a
  report finds; as an answer they are neither form.
* An answer of neither form raises :class:`NeitherFormError`, a class of this
  module. It is no tool failure and holds no kind and no amount: ADR-0043
  decision 5 gives the case no tool-failure kind and leaves open what follows
  it, so this module names none. It is no :class:`TypeError` or
  :class:`ValueError` either, which a refused argument raises.
* The form of the answer is established before any other argument is looked
  at, so an answer of neither form raises :class:`NeitherFormError` also when
  another argument would be refused. The checks that follow are those of the
  function called and are made in its order.
* Beside one of the two strings ``seed`` is neither used nor checked: nothing
  is judged, and no result holds a seed (ADR-0042 decision 6).

The form is established, not the truth (ADR-0043 decision 5 and Limits): an
answer of the right form is taken as it is.

What the module does not do: it is no tool and is bound to none. It calls no
operation and handles nothing an operation raised. It defines no type for
what an operation is handed. It draws no seed and reads no random source or
clock. It reads no file of a run and writes none. It gives no default of any
value: no number of draws, no tolerance, no dimension and no seed. It stores
nothing, keeps nothing between calls and has no command-line entry. It says
nothing of what a call answers for an answer of neither form. It imports
:mod:`hilclaw.check_judging`, :mod:`hilclaw.check_result` and ``reprlib`` of
the standard library and nothing else.
"""

import reprlib

from hilclaw import check_judging, check_result

_NO_REPORT = check_result.CONDITIONS[:2]


class NeitherFormError(Exception):
    """The answer has neither form of ADR-0043 decision 4, so no result was made.

    Raised by :func:`from_answer` for a value that is neither exactly
    ``bytes`` nor exactly one of the two strings ``"time_limit"`` and
    ``"exit_status"``. The message names the type of the answer and, for a
    ``str``, shows it shortened by ``reprlib``; it holds no byte of a report.
    The instance does not hold the answer and has no attribute beyond those
    of :class:`Exception`.
    """


def from_answer(answer, *, m, k, n, draws, seed, rtol, atol):
    """Return the result of a check for ``answer``, as a new ``dict``.

    ``answer`` is what an operation returned. ``m``, ``k``, ``n``, ``draws``
    and ``seed`` are the dimensions, the number of draws and the seed of the
    check, and ``rtol`` and ``atol`` its tolerance. All but ``answer`` are
    keyword-only and none has a default.

    The form of ``answer`` is established first:

    1. Exactly ``bytes``: the answer is a report, also when it is empty,
       short, long or malformed, or spells one of the two strings. The result
       is that of :func:`hilclaw.check_judging.from_report` with all eight
       arguments. What each of the other arguments must be, the order of
       their checks and what is raised are those of that function and are
       passed on unchanged.
    2. Exactly a ``str`` that is ``"time_limit"`` or ``"exit_status"``: the
       result is that of :func:`hilclaw.check_result.broken` with the answer
       as its condition and ``m``, ``k``, ``n``, ``draws``, ``rtol`` and
       ``atol``. Nothing is judged, and ``seed`` is neither used nor checked.
       What that function raises for the six is passed on unchanged.
    3. Anything else: :class:`NeitherFormError`, whatever the other arguments
       are. Nothing is returned then. A ``str`` that differs from the two in
       any character, ``"report_form"`` and ``"check_value"`` included, is
       not made into a broken result.

    An answer of the right form is taken as it is. No argument is modified or
    kept. Apart from what the judging of a report computes the function is
    pure: equal arguments give equal results.
    """
    if type(answer) is bytes:
        return check_judging.from_report(
            answer, m=m, k=k, n=n, draws=draws, seed=seed, rtol=rtol, atol=atol
        )
    if type(answer) is str:
        if answer in _NO_REPORT:
            return check_result.broken(
                answer, m=m, k=k, n=n, draws=draws, rtol=rtol, atol=atol
            )
        shown = f"the str {reprlib.repr(answer)}"
    else:
        shown = type(answer).__name__
    raise NeitherFormError(f"answer: must be bytes or one of {_NO_REPORT}, got {shown}")
