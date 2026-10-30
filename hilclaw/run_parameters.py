"""The timing parameters of ``sim.run`` and ``board.run`` (ADR-0065 decision 2).

``ARCHITECTURE/decisions/ADR-0065-od18-run-tools-operation-form.md``
decision 2 has an operation of either run tool called with four things: the
request, the hw_profile of the call, the timing parameters and the output
path. The timing parameters are "one value that holds exactly these six
values and nothing else": the dimensions ``m``, ``k`` and ``n``, ``n_max``,
the sample form and the seed. :class:`TimingParameters` is the Python type
of that value, for fp32 ``gemm``.

``ARCHITECTURE/decisions/ADR-0181-od13-bf16-timing-run.md`` decision 4 hands
an operation of a bf16 run timing parameters that hold the ``kind`` and
``dtype`` of the covering entry, the dimensions, ``n_max``, the sample form
and the seed, and leaves the Python form to the code, provided an operation
of fp32 ``gemm`` keeps receiving :class:`TimingParameters`.
:class:`Bf16TimingParameters` is that form, a second type beside it.

The types have a module of their own so that the tool functions and an
operation of any backend build and read them without importing a module
of a backend.

Choices that are this module's own and no rule of a record:

* Each type is a :class:`typing.NamedTuple`: an instance cannot be changed,
  and two instances of equal values are equal.
* The field names ``m``, ``k``, ``n``, ``n_max``, ``sample_form`` and
  ``seed`` and their order. The record uses its words to say which value is
  meant and does not make them names of code.
* A second type for a bf16 run rather than a widened one, so that every
  existing reader of the six values unpacks the same six; its dimensions are
  one ``tuple`` field, ``dims``, since their number depends on the kind. Its
  field names and their order are this module's too.

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
    """The six values an operation of a fp32 ``gemm`` run of ``sim.run`` or ``board.run``
    is handed beside the request, the hw_profile and the output path (ADR-0065 decision 2).

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


class Bf16TimingParameters(typing.NamedTuple):
    """The values an operation of a bf16 run of ``sim.run`` or ``board.run`` is handed
    beside the request, the hw_profile and the output path (ADR-0181 decision 4).

    - ``kind``, ``dtype``: the ``kind`` and ``dtype`` of the table key of the
      covering entry of :data:`hilclaw.contract_table.TABLE`.
    - ``dims``: the dimensions, a ``tuple`` in the order of the parameters of
      the contract's ``task_contract`` (``(m, k, n)`` for ``gemm``,
      ``(m, n)`` for ``rmsnorm``, ``elementwise_add`` and ``swiglu``,
      ``(m, h, d)`` for ``rope``, ``(m, l, h, h_kv, d)`` for
      ``sdpa_kv_cache``).
    - ``n_max``: the run's bound of the repeats of one measurement.
    - ``sample_form``: the sample form the tool function derived.
    - ``seed``: the timing seed of the call.

    All six are given, by position in this order or by name; none has a
    default. Nothing is checked when an instance is built.
    """

    kind: str
    dtype: str
    dims: tuple
    n_max: int
    sample_form: str
    seed: int
