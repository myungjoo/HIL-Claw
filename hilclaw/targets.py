"""The target table: what each ``accelerator`` builds and runs with (ADR-0193 decision 3).

``ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md`` decision 3
places the description of a target in a table in the package source, one
:class:`Target` per ``accelerator`` value. This module is that table,
:data:`TABLE`, with :func:`target` to look one up,
:func:`instance_start_accelerators` for the names an instance may start on and
:func:`covers_at` for a predicate "covered" read at the target of an
``accelerator`` (ADR-0197 decision 3).

* A :class:`Target` holds the build flags, trailing flags and waiter flags,
  the environment, the build time limit and the cap of the process time
  limits, the contract-table keys it serves, a memory limit or ``None``, the
  measurement unit and the integer factor its figures are its ``ns`` figures
  times (ADR-0196 decisions 3 and 5), and whether the model executor may
  take its runs (``model_run``) and an instance may start on it (``instance_start``).
* The entry :data:`CPU_STANDIN` (:data:`hilclaw.standin_profile.ACCELERATOR`).
  Its values are read from :mod:`hilclaw.standin_settings` each time the entry
  is read, so those constants stay the source of its build settings and time
  limits (ADR-0116 decision 2 (a); ADR-0117; ADR-0188). It serves every key of
  :data:`hilclaw.contract_table.TABLE`, has no memory limit, the unit ``ns``
  with the factor 1, and both booleans true.
* The entry :data:`VIRTUAL_NPU`, the virtual NPU of ADR-0193 decision 4: a
  check backend on the development machine whose values exist to make
  first-case assumptions fail and are no fact about any real NPU. Its flags
  are :data:`VIRTUAL_NPU_FLAGS`; its trailing and waiter flags, environment,
  build time limit and process time-limit cap are those of ``cpu_standin``,
  read from the same constants. It serves the six bf16 keys of
  :data:`hilclaw.contract_table.TABLE` (not fp32 ``gemm``), bounds each
  process container to :data:`VIRTUAL_NPU_MEMORY_LIMIT_BYTES`, has the unit
  ``cycles`` with the factor :data:`VIRTUAL_NPU_CYCLES_PER_NS` (HQ-0090 (a);
  ADR-0196 decision 5: a check value, no fact about the cycles of any real
  NPU), ``model_run`` false and ``instance_start`` true: an instance of a
  contract it serves may start on it, checked with the bf16 contracts'
  reference and the user's tolerance (HQ-0091 ① (a); ADR-0197 decisions 1
  and 2).
* The mock (:data:`hilclaw.mock_backend.NAME`) builds nothing and has no
  :class:`Target`.

A target is linked to a hw_profile by its ``accelerator`` alone (ADR-0016
decision 4); none of its values is a key field, a member of a hw_profile,
``instance.json``, spec or result, or a value stored in the data plane. The
table changes only by a commit of this repository. This module reads no file,
environment variable or hw_profile and starts no process.
"""

import dataclasses
import math
import types
from collections.abc import Mapping

from hilclaw import contract_table, run_result, standin_profile, standin_settings


class NoTargetError(LookupError):
    """:func:`target` was asked for a name the table holds no :class:`Target` for; ``name`` is that name."""

    def __init__(self, name):
        super().__init__(f"no target is described for the accelerator {name!r}")
        self.name = name


@dataclasses.dataclass(frozen=True)
class Target:
    """The description of one target (ADR-0193 decision 3); every member is checked when it is built.

    @param flags the flags of every kernel build, given before the sources, a
        ``tuple`` of ``str``.
    @param trailing_flags the flags given after the sources, a ``tuple`` of ``str``.
    @param waiter_flags the flags of the build of the waiter (ADR-0145), a
        ``tuple`` of ``str``.
    @param env the environment of every build and process: ``None`` for the
        inherited one, or a mapping of ``str`` to ``str``, kept as a read-only copy.
    @param build_time_limit_s the time limit in seconds of every build, an
        ``int`` or ``float`` above 0 (not a ``bool``).
    @param process_time_limit_cap_s the cap in seconds of every process time
        limit (ADR-0117 decision 4), as ``build_time_limit_s`` and finite.
    @param contracts the keys of :data:`hilclaw.contract_table.TABLE` the target
        serves, a ``tuple`` with no key twice.
    @param memory_limit_bytes ``None`` for no bound, or an ``int`` above 0 (not a ``bool``).
    @param unit the measurement unit, one of :data:`hilclaw.run_result.UNITS`.
    @param units_per_ns the factor every figure in ``unit`` is the ``ns``
        figure times (ADR-0196 decision 5): an ``int`` of at least 1 (not a
        ``bool``), exactly 1 when ``unit`` is ``ns``.
    @param model_run exactly a ``bool``: the model executor may take this target's runs.
    @param instance_start exactly a ``bool``: an instance may start on this target.
    @throws TypeError for a member of the wrong type.
    @throws ValueError for a member of the right type and a refused value.
    """

    flags: tuple
    trailing_flags: tuple
    waiter_flags: tuple
    env: object
    build_time_limit_s: object
    process_time_limit_cap_s: object
    contracts: tuple
    memory_limit_bytes: object
    unit: str
    units_per_ns: int
    model_run: bool
    instance_start: bool

    def __post_init__(self):
        for name in ("flags", "trailing_flags", "waiter_flags"):
            _check_flags(name, getattr(self, name))
        object.__setattr__(self, "env", _checked_env(self.env))
        _check_seconds("build_time_limit_s", self.build_time_limit_s)
        _check_seconds("process_time_limit_cap_s", self.process_time_limit_cap_s)
        if not self.process_time_limit_cap_s < math.inf:
            raise ValueError("process_time_limit_cap_s must be finite")
        _check_contracts(self.contracts)
        _check_memory_limit(self.memory_limit_bytes)
        if type(self.unit) is not str:
            raise TypeError(f"unit must be a str, not {type(self.unit).__name__}")
        if self.unit not in run_result.UNITS:
            raise ValueError(f"unit must be one of {', '.join(run_result.UNITS)}")
        _check_units_per_ns(self.unit, self.units_per_ns)
        for name in ("model_run", "instance_start"):
            value = getattr(self, name)
            if type(value) is not bool:
                raise TypeError(f"{name} must be a bool, not {type(value).__name__}")


def _check_flags(name, flags):
    if type(flags) is not tuple:
        raise TypeError(f"{name} must be a tuple, not {type(flags).__name__}")
    for flag in flags:
        if type(flag) is not str:
            raise TypeError(f"{name} must hold str only, not {type(flag).__name__}")


def _checked_env(env):
    if env is None:
        return None
    if not isinstance(env, Mapping):
        raise TypeError(f"env must be None or a mapping, not {type(env).__name__}")
    for key, value in env.items():
        if type(key) is not str or type(value) is not str:
            raise TypeError("env must map str to str")
    return types.MappingProxyType(dict(env))


def _check_seconds(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be an int or float, not {type(value).__name__}")
    if not value > 0:
        raise ValueError(f"{name} must be above 0")


def _check_contracts(contracts):
    if type(contracts) is not tuple:
        raise TypeError(f"contracts must be a tuple, not {type(contracts).__name__}")
    for key in contracts:
        try:
            known = key in contract_table.TABLE
        except TypeError:
            known = False
        if not known:
            raise ValueError(f"contracts: {key!r} is no key of the contract table")
    if len(set(contracts)) != len(contracts):
        raise ValueError("contracts must hold each key once")


def _check_memory_limit(value):
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(
            f"memory_limit_bytes must be None or an int, not {type(value).__name__}"
        )
    if value < 1:
        raise ValueError("memory_limit_bytes must be above 0")


def _check_units_per_ns(unit, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"units_per_ns must be an int, not {type(value).__name__}")
    if value < 1:
        raise ValueError("units_per_ns must be at least 1")
    if unit == "ns" and value != 1:
        raise ValueError("units_per_ns must be 1 for the unit ns")


def _bf16_contracts():
    return tuple(key for key in contract_table.TABLE if key[1] == "bf16")


def _virtual_npu():
    return Target(
        flags=VIRTUAL_NPU_FLAGS,
        trailing_flags=standin_settings.TRAILING_FLAGS,
        waiter_flags=standin_settings.WAITER_FLAGS,
        env=standin_settings.ENV,
        build_time_limit_s=standin_settings.BUILD_TIME_LIMIT_S,
        process_time_limit_cap_s=standin_settings.PROCESS_TIME_LIMIT_CAP_S,
        contracts=_bf16_contracts(),
        memory_limit_bytes=VIRTUAL_NPU_MEMORY_LIMIT_BYTES,
        unit="cycles",
        units_per_ns=VIRTUAL_NPU_CYCLES_PER_NS,
        model_run=False,
        instance_start=True,
    )


def _cpu_standin():
    return Target(
        flags=standin_settings.FLAGS,
        trailing_flags=standin_settings.TRAILING_FLAGS,
        waiter_flags=standin_settings.WAITER_FLAGS,
        env=standin_settings.ENV,
        build_time_limit_s=standin_settings.BUILD_TIME_LIMIT_S,
        process_time_limit_cap_s=standin_settings.PROCESS_TIME_LIMIT_CAP_S,
        contracts=tuple(contract_table.TABLE),
        memory_limit_bytes=None,
        unit="ns",
        units_per_ns=1,
        model_run=True,
        instance_start=True,
    )


CPU_STANDIN = standin_profile.ACCELERATOR
"""The name of the ``cpu_standin`` entry, :data:`hilclaw.standin_profile.ACCELERATOR`."""

VIRTUAL_NPU = standin_profile.VIRTUAL_NPU
"""The name of the ``virtual_npu`` entry, :data:`hilclaw.standin_profile.VIRTUAL_NPU` (ADR-0193 decision 4)."""

VIRTUAL_NPU_FLAGS = (
    "-std=gnu11",
    "-O1",
    "-ffp-contract=off",
    "-fno-vectorize",
    "-fno-slp-vectorize",
)
"""The flags of every kernel build at ``virtual_npu`` (ADR-0193 decision 4)."""

VIRTUAL_NPU_MEMORY_LIMIT_BYTES = 268435456
"""The memory bound in bytes of each ``virtual_npu`` process container (ADR-0193 decision 4)."""

VIRTUAL_NPU_CYCLES_PER_NS = 3
"""The factor of ``virtual_npu``'s ``cycles``: its ``ns`` figures times 3, a check value (ADR-0196 decision 5)."""


class _Table(Mapping):
    def __init__(self, builders):
        self._builders = types.MappingProxyType(dict(builders))

    def __getitem__(self, name):
        return self._builders[name]()

    def __contains__(self, name):
        return name in self._builders

    def __iter__(self):
        return iter(self._builders)

    def __len__(self):
        return len(self._builders)

    def __repr__(self):
        return f"<target table: {', '.join(self._builders)}>"


TABLE = _Table({CPU_STANDIN: _cpu_standin, VIRTUAL_NPU: _virtual_npu})
"""The target table: a read-only mapping from ``accelerator`` to :class:`Target`, each entry built when it is read."""


def target(name, table=TABLE):
    """Return the :class:`Target` of the ``accelerator`` ``name`` in ``table``.

    @param name the ``accelerator`` value.
    @param table a mapping from ``accelerator`` to :class:`Target`, by default
        :data:`TABLE`.
    @throws NoTargetError when ``table`` holds no entry for ``name``, a name
        it cannot look up included. What building the entry raises, such as
        the :class:`TypeError` or :class:`ValueError` of a refused member,
        passes unchanged.
    """
    try:
        held = name in table
    except TypeError:
        held = False
    if not held:
        raise NoTargetError(name)
    return table[name]


def instance_start_accelerators(table=TABLE):
    """Return the names of ``table`` whose :class:`Target` has ``instance_start`` true, in its order, as a ``tuple``."""
    return tuple(name for name, entry in table.items() if entry.instance_start)


def covers_at(covers, accelerator, table=TABLE):
    """Return the predicate ``covers`` read at the target of ``accelerator`` (ADR-0197 decision 3).

    Where ``table`` holds a :class:`Target` for ``accelerator``, the result
    answers ``True`` for a record only when ``covers`` does and the target
    serves the record's entry (:func:`hilclaw.contract_table.served_at`), so
    a record of a contract the target does not serve is not covered there;
    any other answer of ``covers`` is returned as it is. The target is read
    from ``table`` here, once. Where ``table`` holds none, the mock or an
    unknown name, the result is ``covers`` itself.

    @param covers a predicate "covered", handed an op_signature record.
    @param accelerator the ``accelerator`` value of the run's hw_profile.
    @param table a mapping from ``accelerator`` to :class:`Target`, by default
        :data:`TABLE`.
    @throws TypeError when ``covers`` is not callable. What building the
        entry raises passes unchanged, as in :func:`target`; what ``covers``
        and ``served_at`` raise passes unchanged from the result.
    """
    if not callable(covers):
        raise TypeError("covers: must be callable")
    try:
        held = target(accelerator, table)
    except NoTargetError:
        return covers

    def covered_at_target(record):
        covered = covers(record)
        if covered is not True:
            return covered
        return contract_table.served_at(record, held)

    return covered_at_target
