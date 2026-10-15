"""The timing parameters of ``sim.run`` and ``board.run`` (ADR-0065 decision 2).

``ARCHITECTURE/decisions/ADR-0065-od18-run-tools-operation-form.md``
decision 2 has an operation of either run tool called with four things: the
request, the hw_profile of the call, the timing parameters and the output
path. The timing parameters are "one value that holds exactly these six
values and nothing else": the dimensions ``m``, ``k`` and ``n``, ``n_max``,
the sample form and the seed. :class:`TimingParameters` is the Python type
of that value.

The type has a module of its own so that the tool functions and an operation
of any backend build and read one type without importing a module of a
backend.

Choices that are this module's own and no rule of a record:

* The type is a :class:`typing.NamedTuple`: an instance cannot be changed,
  and two instances of equal values are equal.
* The field names ``m``, ``k``, ``n``, ``n_max``, ``sample_form`` and
  ``seed`` and their order. The record uses its words to say which value is
  meant and does not make them names of code.

What the module does not do: it validates nothing. No kind and no bound of a
value is checked; whoever uses the value checks it. It gives no field a
default and names no source of a seed. It holds no output path, no
``bound``, no ``objective``, no ``n_min``, no ``cv_max`` and no setting, and
nothing for the point or the name of the tool: none of them is in the timing
parameters (ADR-0065 decisions 2 and 3). It imports ``typing`` and nothing
else.
"""

import typing


class TimingParameters(typing.NamedTuple):
    """The six values an operation of ``sim.run`` or ``board.run`` is handed beside
    the request, the hw_profile and the output path (ADR-0065 decision 2).

    - ``m``, ``k``, ``n``: the dimensions of the run.
    - ``n_max``: the run's bound of the repeats of one measurement.
    - ``sample_form``: the sample form the tool function derived.
    - ``seed``: the timing seed of the call.

    All six are given, by position in this order or by name; none has a
    default. Nothing is checked when an instance is built.
    """

    m: int
    k: int
    n: int
    n_max: int
    sample_form: str
    seed: int
