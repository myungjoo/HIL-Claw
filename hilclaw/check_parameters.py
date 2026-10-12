"""The check parameters of ``correctness.check`` (ADR-0043 decision 2).

``ARCHITECTURE/decisions/ADR-0043-od18-correctness-check-operation-form.md``
decision 2 has an operation of this tool called with three things: the
request, the hw_profile of the call and the check parameters. The check
parameters are "one value that holds exactly these five values and nothing
else": the seed of the call, the number of draws and the dimensions ``m``,
``k`` and ``n``. :class:`CheckParameters` is the Python type of that value.

The type has a module of its own so that the tool function and an operation
of any backend build and read one type without importing a module of a
backend.

Choices that are this module's own and no rule of a record:

* The type is a :class:`typing.NamedTuple`: an instance cannot be changed,
  and two instances of equal values are equal.
* The field names ``seed``, ``draws``, ``m``, ``k`` and ``n`` and their
  order. The record uses the five words to say which value is meant and does
  not make them names of code.

What the module does not do: it validates nothing. No kind and no bound of a
value is checked, so no upper bound of a harness is adopted here; whoever
uses the value checks it. It gives no field a default and names no source of
a seed or of a number of draws. It holds no tolerance, no reference, no
expected output and no member of a request, and nothing of class (iii) of
ADR-0021 decision 2. It imports ``typing`` and nothing else.
"""

import typing


class CheckParameters(typing.NamedTuple):
    """The five values an operation of ``correctness.check`` is handed beside
    the request and the hw_profile (ADR-0043 decision 2).

    - ``seed``: the seed of the call.
    - ``draws``: the number of draws of the check.
    - ``m``, ``k``, ``n``: the dimensions of the check.

    All five are given, by position in this order or by name; none has a
    default. Nothing is checked when an instance is built.
    """

    seed: int
    draws: int
    m: int
    k: int
    n: int
