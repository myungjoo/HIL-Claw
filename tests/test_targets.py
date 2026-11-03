import dataclasses
import math
import types
from collections.abc import Mapping

import pytest

from hilclaw import (
    contract_table,
    mock_backend,
    run_result,
    standin_profile,
    standin_settings,
    targets,
)
from hilclaw.targets import TABLE, NoTargetError, Target

GOOD = {
    "flags": ("-O1",),
    "trailing_flags": ("-lm",),
    "waiter_flags": (),
    "env": None,
    "build_time_limit_s": 1.5,
    "process_time_limit_cap_s": 30,
    "contracts": tuple(contract_table.TABLE)[:2],
    "memory_limit_bytes": None,
    "unit": "ns",
    "model_run": False,
    "instance_start": False,
}


def made(**changes):
    return Target(**(GOOD | changes))


def test_the_table_holds_cpu_standin_alone_and_not_the_mock():
    assert isinstance(TABLE, Mapping)
    assert tuple(TABLE) == (standin_profile.ACCELERATOR,)
    assert len(TABLE) == 1
    assert mock_backend.NAME not in TABLE
    assert "cpu_standin" in repr(TABLE)


def test_cpu_standin_keeps_the_constants_of_standin_settings():
    standin = targets.target(standin_profile.ACCELERATOR)
    assert type(standin) is Target
    assert standin.flags == standin_settings.FLAGS
    assert standin.trailing_flags == standin_settings.TRAILING_FLAGS
    assert standin.waiter_flags == standin_settings.WAITER_FLAGS
    assert standin.env is None is standin_settings.ENV
    assert standin.build_time_limit_s == standin_settings.BUILD_TIME_LIMIT_S == 60
    assert (
        standin.process_time_limit_cap_s
        == standin_settings.PROCESS_TIME_LIMIT_CAP_S
        == 1500
    )
    assert standin.contracts == tuple(contract_table.TABLE)
    assert len(standin.contracts) == 7
    assert standin.memory_limit_bytes is None
    assert standin.unit == "ns"
    assert standin.model_run is True
    assert standin.instance_start is True


def test_the_entry_reads_the_constants_each_time_it_is_read(monkeypatch):
    monkeypatch.setattr(standin_settings, "BUILD_TIME_LIMIT_S", 7)
    monkeypatch.setattr(standin_settings, "FLAGS", ("-O0",))
    standin = TABLE[standin_profile.ACCELERATOR]
    assert standin.build_time_limit_s == 7
    assert standin.flags == ("-O0",)


def test_the_table_cannot_be_changed():
    with pytest.raises(TypeError):
        TABLE["virtual_npu"] = made()
    with pytest.raises(dataclasses.FrozenInstanceError):
        targets.target(standin_profile.ACCELERATOR).unit = "cycles"


@pytest.mark.parametrize("name", ["mock", "virtual_npu", "", 3, None, ["cpu_standin"]])
def test_a_name_with_no_target_is_refused(name):
    with pytest.raises(NoTargetError) as caught:
        targets.target(name)
    assert isinstance(caught.value, LookupError)
    assert caught.value.name == name


def test_a_given_table_is_looked_up():
    other = made()
    assert targets.target("synthetic", {"synthetic": other}) is other
    with pytest.raises(NoTargetError):
        targets.target(standin_profile.ACCELERATOR, {"synthetic": other})


def test_instance_start_accelerators_reads_the_boolean():
    assert targets.instance_start_accelerators() == (standin_profile.ACCELERATOR,)
    table = {
        "a": made(instance_start=True),
        "b": made(),
        "c": made(instance_start=True),
    }
    assert targets.instance_start_accelerators(table) == ("a", "c")
    assert targets.instance_start_accelerators({}) == ()


def test_an_infinite_cap_is_refused():
    with pytest.raises(ValueError):
        made(process_time_limit_cap_s=math.inf)
    assert made(process_time_limit_cap_s=2**4000).process_time_limit_cap_s == 2**4000


def test_a_good_target_keeps_its_values():
    target = made(
        env={"A": "1"},
        memory_limit_bytes=268435456,
        build_time_limit_s=math.inf,
        model_run=True,
    )
    assert target.flags == ("-O1",)
    assert type(target.env) is types.MappingProxyType
    assert dict(target.env) == {"A": "1"}
    assert target.memory_limit_bytes == 268435456
    assert target.build_time_limit_s == math.inf
    assert target.model_run is True


def test_the_env_is_a_copy():
    given = {"A": "1"}
    target = made(env=given)
    given["A"] = "2"
    assert target.env["A"] == "1"
    with pytest.raises(TypeError):
        target.env["A"] = "3"


@pytest.mark.parametrize("member", ["flags", "trailing_flags", "waiter_flags"])
@pytest.mark.parametrize("value", [["-O1"], "-O1", None, ("-O1", 1), (b"-O1",)])
def test_flags_that_are_no_tuple_of_str_are_refused(member, value):
    with pytest.raises(TypeError):
        made(**{member: value})


@pytest.mark.parametrize(
    ("value", "error"),
    [
        ([("A", "1")], TypeError),
        ("A=1", TypeError),
        ({"A": 1}, TypeError),
        ({1: "A"}, TypeError),
    ],
)
def test_an_env_that_is_no_mapping_of_str_is_refused(value, error):
    with pytest.raises(error):
        made(env=value)


@pytest.mark.parametrize("member", ["build_time_limit_s", "process_time_limit_cap_s"])
@pytest.mark.parametrize(
    ("value", "error"),
    [
        (0, ValueError),
        (-1, ValueError),
        (-0.5, ValueError),
        (math.nan, ValueError),
        (True, TypeError),
        (False, TypeError),
        ("60", TypeError),
        (None, TypeError),
    ],
)
def test_a_time_limit_that_is_no_positive_number_is_refused(member, value, error):
    with pytest.raises(error):
        made(**{member: value})


@pytest.mark.parametrize(
    ("value", "error"),
    [
        ([("gemm", "fp32", "row_major", "c")], TypeError),
        (None, TypeError),
        ((("gemm", "fp16", "row_major", "c"),), ValueError),
        (("gemm",), ValueError),
        (([1],), ValueError),
        ((next(iter(contract_table.TABLE)),) * 2, ValueError),
    ],
)
def test_contracts_that_are_no_keys_of_the_contract_table_are_refused(value, error):
    with pytest.raises(error):
        made(contracts=value)


def test_no_contract_is_admitted():
    assert made(contracts=()).contracts == ()


@pytest.mark.parametrize(
    ("value", "error"),
    [
        (0, ValueError),
        (-1, ValueError),
        (True, TypeError),
        (1.0, TypeError),
        ("1", TypeError),
    ],
)
def test_a_memory_limit_that_is_not_none_or_a_positive_int_is_refused(value, error):
    with pytest.raises(error):
        made(memory_limit_bytes=value)


@pytest.mark.parametrize(
    ("value", "error"), [("cycles", ValueError), ("", ValueError), (None, TypeError)]
)
def test_a_unit_outside_the_units_is_refused(value, error):
    assert value not in run_result.UNITS
    with pytest.raises(error):
        made(unit=value)


@pytest.mark.parametrize("member", ["model_run", "instance_start"])
@pytest.mark.parametrize("value", [1, 0, None, "true"])
def test_a_boolean_that_is_no_bool_is_refused(member, value):
    with pytest.raises(TypeError):
        made(**{member: value})
