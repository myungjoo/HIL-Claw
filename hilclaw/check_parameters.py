"""The check parameters of ``correctness.check`` (ADR-0043 decision 2).

``ARCHITECTURE/decisions/ADR-0043-od18-correctness-check-operation-form.md``
decision 2 has an operation of this tool called with the request, the
hw_profile of the call and the check parameters; since ADR-0056 decision 3
it is called with four things, the fourth being the output path, and since
ADR-0078 decision 6 with five, the fifth being the log keeper; neither is a
value of the check parameters. The check parameters are "one value that holds
exactly these five values and nothing else": the seed of the call, the number
of draws and the dimensions ``m``, ``k`` and ``n``. :class:`CheckParameters`
is the Python type of that value.

``ARCHITECTURE/decisions/ADR-0177-od18-od6-contract-table.md`` decision 3
("What the operations are handed") hands an operation of a check of a bf16
kind the seed, the number of draws, the ``kind`` and ``dtype`` of the table
key of the covering entry and the dimensions in the order of the contract's
``task_contract`` parameters, and leaves the Python form to the code,
provided an operation of fp32 ``gemm`` keeps receiving what it receives.
:class:`Bf16CheckParameters` is that form, a second type beside
:class:`CheckParameters`, which is unchanged; :data:`BF16` is the one
``dtype`` it is built for here. No caller of the tool builds it yet.

The types have a module of their own so that the tool function and an
operation of any backend build and read one type without importing a module
of a backend.

Choices that are this module's own and no rule of a record:

* Each type is a :class:`typing.NamedTuple`: an instance cannot be changed,
  and two instances of equal values are equal.
* The field names ``seed``, ``draws``, ``m``, ``k`` and ``n`` and their
  order. The record uses the five words to say which value is meant and does
  not make them names of code.
* A second type for a bf16 kind rather than a widened one, so that every
  existing reader of the five values unpacks the same five; its dimensions
  are one ``tuple`` field, ``dims``, since their number depends on the kind.

What the module does not do: it validates nothing. No kind and no bound of a
value is checked, so no upper bound of a harness is adopted here; whoever
uses the value checks it. It gives no field a default and names no source of
a seed or of a number of draws. It holds no tolerance, no reference, no
expected output and no member of a request, and nothing of class (iii) of
ADR-0021 decision 2: the output path is handed beside the check parameters
and not in them. It imports ``typing`` and nothing else.
"""

import typing


class CheckParameters(typing.NamedTuple):
    """The five values an operation of ``correctness.check`` is handed beside
    the request, the hw_profile and the output path (ADR-0043 decision 2;
    ADR-0056 decision 3).

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


#: The ``dtype`` of the table key that :class:`Bf16CheckParameters` is for.
BF16 = "bf16"


class Bf16CheckParameters(typing.NamedTuple):
    """The values an operation of a check of a bf16 kind is handed beside the
    request, the hw_profile and the output path (ADR-0177 decision 3).

    - ``seed``: the seed of the call.
    - ``draws``: the number of draws of the check.
    - ``kind``, ``dtype``: the ``kind`` and ``dtype`` of the table key of the
      covering entry of :data:`hilclaw.contract_table.TABLE`.
    - ``dims``: the dimensions, a ``tuple`` in the order of the parameters of
      the contract's ``task_contract`` (``(m, k, n)`` for ``gemm``,
      ``(m, n)`` for ``rmsnorm``, ``elementwise_add`` and ``swiglu``).

    All five are given, by position in this order or by name; none has a
    default. Nothing is checked when an instance is built.
    """

    seed: int
    draws: int
    kind: str
    dtype: str
    dims: tuple
