import dataclasses
import math
import types
from collections.abc import Mapping

import pytest

from hilclaw import (
    contract_table,
    gemm_bf16_contract,
    gemm_contract,
    keys,
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
    "units_per_ns": 1,
    "model_run": False,
    "instance_start": False,
    "coder_loop": False,
}


def made(**changes):
    return Target(**(GOOD | changes))


def test_the_table_holds_cpu_standin_virtual_npu_and_cuda_gpu_and_not_the_mock():
    assert isinstance(TABLE, Mapping)
    assert tuple(TABLE) == (standin_profile.ACCELERATOR, "virtual_npu", "cuda_gpu")
    assert len(TABLE) == 3
    assert mock_backend.NAME not in TABLE
    assert repr(TABLE) == "<target table: cpu_standin, virtual_npu, cuda_gpu>"


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
    assert standin.units_per_ns == 1
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


@pytest.mark.parametrize(
    "name", ["mock", "synthetic_npu", "", 3, None, ["cpu_standin"]]
)
def test_a_name_with_no_target_is_refused(name):
    with pytest.raises(NoTargetError) as caught:
        targets.target(name)
    assert isinstance(caught.value, LookupError)
    assert caught.value.name == name


def test_an_error_of_building_the_entry_is_not_masked(monkeypatch):
    monkeypatch.setattr(standin_settings, "FLAGS", ["-O2"])
    with pytest.raises(TypeError, match="^flags must be a tuple"):
        targets.target(targets.CPU_STANDIN)
    assert targets.CPU_STANDIN in TABLE
    monkeypatch.undo()
    monkeypatch.setattr(standin_settings, "BUILD_TIME_LIMIT_S", 0)
    with pytest.raises(ValueError, match="^build_time_limit_s"):
        targets.target(targets.CPU_STANDIN)


def test_the_name_of_the_cpu_standin_entry():
    assert targets.CPU_STANDIN == standin_profile.ACCELERATOR == "cpu_standin"


def test_a_given_table_is_looked_up():
    other = made()
    assert targets.target("synthetic", {"synthetic": other}) is other
    with pytest.raises(NoTargetError):
        targets.target(standin_profile.ACCELERATOR, {"synthetic": other})


def test_instance_start_accelerators_reads_the_boolean():
    assert targets.instance_start_accelerators() == (
        standin_profile.ACCELERATOR,
        targets.VIRTUAL_NPU,
    )
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
    ("value", "error"),
    [("cycle", ValueError), ("us", ValueError), ("", ValueError), (None, TypeError)],
)
def test_a_unit_outside_the_units_is_refused(value, error):
    assert value not in run_result.UNITS
    with pytest.raises(error):
        made(unit=value)


@pytest.mark.parametrize("factor", [1, 3, 1000])
def test_a_cycles_target_keeps_its_factor(factor):
    target = made(unit="cycles", units_per_ns=factor)
    assert target.unit == "cycles"
    assert target.units_per_ns == factor


@pytest.mark.parametrize("unit", ["ns", "cycles"])
@pytest.mark.parametrize(
    ("value", "error"),
    [
        (0, ValueError),
        (-1, ValueError),
        (-3, ValueError),
        (True, TypeError),
        (False, TypeError),
        (3.0, TypeError),
        (1.0, TypeError),
        ("3", TypeError),
        (None, TypeError),
    ],
)
def test_a_factor_that_is_no_int_of_at_least_1_is_refused(unit, value, error):
    with pytest.raises(error, match="^units_per_ns"):
        made(unit=unit, units_per_ns=value)


@pytest.mark.parametrize("value", [2, 3, 1000])
def test_a_factor_other_than_1_with_the_unit_ns_is_refused(value):
    with pytest.raises(ValueError, match="^units_per_ns must be 1 for the unit ns"):
        made(unit="ns", units_per_ns=value)


def test_the_unit_is_checked_before_the_factor():
    with pytest.raises(ValueError, match="^unit must be one of ns, cycles"):
        made(unit="us", units_per_ns=0)


@pytest.mark.parametrize("member", ["model_run", "instance_start"])
@pytest.mark.parametrize("value", [1, 0, None, "true"])
def test_a_boolean_that_is_no_bool_is_refused(member, value):
    with pytest.raises(TypeError):
        made(**{member: value})


def test_virtual_npu_has_the_values_of_adr_0193_decision_4():
    virtual = targets.target(targets.VIRTUAL_NPU)
    assert targets.VIRTUAL_NPU == standin_profile.VIRTUAL_NPU == "virtual_npu"
    assert type(virtual) is Target
    assert virtual.flags == (
        "-std=gnu11",
        "-O1",
        "-ffp-contract=off",
        "-fno-vectorize",
        "-fno-slp-vectorize",
    )
    assert virtual.flags == targets.VIRTUAL_NPU_FLAGS
    assert "-fopenmp" not in virtual.flags
    assert virtual.trailing_flags == standin_settings.TRAILING_FLAGS
    assert virtual.waiter_flags == standin_settings.WAITER_FLAGS
    assert virtual.env is None is standin_settings.ENV
    assert virtual.build_time_limit_s == standin_settings.BUILD_TIME_LIMIT_S
    assert virtual.process_time_limit_cap_s == standin_settings.PROCESS_TIME_LIMIT_CAP_S
    assert virtual.contracts == tuple(
        key for key in contract_table.TABLE if key != ("gemm", "fp32", "row_major", "c")
    )
    assert len(virtual.contracts) == 6
    assert {key[1] for key in virtual.contracts} == {"bf16"}
    assert virtual.memory_limit_bytes == 268435456
    assert virtual.memory_limit_bytes == targets.VIRTUAL_NPU_MEMORY_LIMIT_BYTES
    assert virtual.unit == "cycles"
    assert virtual.units_per_ns == 3
    assert virtual.units_per_ns == targets.VIRTUAL_NPU_CYCLES_PER_NS
    assert type(targets.VIRTUAL_NPU_CYCLES_PER_NS) is int
    assert virtual.model_run is False
    assert virtual.instance_start is True


def test_virtual_npu_reads_the_shared_constants_each_time_it_is_read(monkeypatch):
    monkeypatch.setattr(standin_settings, "BUILD_TIME_LIMIT_S", 7)
    monkeypatch.setattr(standin_settings, "PROCESS_TIME_LIMIT_CAP_S", 9)
    monkeypatch.setattr(standin_settings, "TRAILING_FLAGS", ("-lfoo",))
    monkeypatch.setattr(standin_settings, "WAITER_FLAGS", ("-O3",))
    monkeypatch.setattr(standin_settings, "ENV", {"A": "1"})
    monkeypatch.setattr(standin_settings, "FLAGS", ("-O0",))
    virtual = TABLE[targets.VIRTUAL_NPU]
    assert virtual.build_time_limit_s == 7
    assert virtual.process_time_limit_cap_s == 9
    assert virtual.trailing_flags == ("-lfoo",)
    assert virtual.waiter_flags == ("-O3",)
    assert dict(virtual.env) == {"A": "1"}
    assert virtual.flags == targets.VIRTUAL_NPU_FLAGS


def test_an_error_of_building_virtual_npu_is_not_masked(monkeypatch):
    monkeypatch.setattr(standin_settings, "PROCESS_TIME_LIMIT_CAP_S", math.inf)
    with pytest.raises(ValueError, match="^process_time_limit_cap_s"):
        targets.target(targets.VIRTUAL_NPU)


def test_virtual_npu_takes_an_instance_start_and_no_model_run():
    assert targets.instance_start_accelerators() == (
        targets.CPU_STANDIN,
        targets.VIRTUAL_NPU,
    )
    assert targets.target(targets.VIRTUAL_NPU).model_run is False


@pytest.mark.parametrize("value", [1, 0, None, "true", "false"])
def test_a_coder_loop_that_is_no_bool_is_refused(value):
    with pytest.raises(TypeError, match="coder_loop must be a bool"):
        made(coder_loop=value)


def test_coder_loop_has_no_default():
    values = {name: value for name, value in GOOD.items() if name != "coder_loop"}
    with pytest.raises(TypeError):
        Target(**values)


@pytest.mark.parametrize("value", [True, False])
def test_a_good_coder_loop_is_kept(value):
    assert made(coder_loop=value).coder_loop is value


def test_cpu_standin_and_virtual_npu_take_the_coder_loop():
    assert targets.target(targets.CPU_STANDIN).coder_loop is True
    assert targets.target(targets.VIRTUAL_NPU).coder_loop is True
    assert targets.coder_loop_accelerators() == (
        targets.CPU_STANDIN,
        targets.VIRTUAL_NPU,
    )


def test_coder_loop_accelerators_reads_both_booleans():
    table = {
        "both": made(instance_start=True, coder_loop=True),
        "start_only": made(instance_start=True, coder_loop=False),
        "loop_only": made(instance_start=False, coder_loop=True),
        "neither": made(),
        "again": made(instance_start=True, coder_loop=True),
    }
    assert targets.coder_loop_accelerators(table) == ("both", "again")
    assert targets.instance_start_accelerators(table) == (
        "both",
        "start_only",
        "again",
    )
    assert targets.coder_loop_accelerators({}) == ()


def test_coder_loop_accelerators_passes_an_error_of_building_the_entry(monkeypatch):
    monkeypatch.setattr(standin_settings, "FLAGS", "-O2")
    with pytest.raises(TypeError):
        targets.coder_loop_accelerators()


# The cuda_gpu entry (ADR-0207 decision 3)


def test_cuda_gpu_has_the_values_of_adr_0207_decision_3():
    cuda = targets.target(targets.CUDA_GPU)
    assert targets.CUDA_GPU == "cuda_gpu"
    assert type(cuda) is Target
    assert cuda.flags == ("-O2", "-arch=native") == targets.CUDA_GPU_FLAGS
    assert cuda.trailing_flags == ()
    assert cuda.waiter_flags == ("-O2",) == targets.CUDA_GPU_WAITER_FLAGS
    assert cuda.env is None
    assert cuda.build_time_limit_s == 120 == targets.CUDA_GPU_BUILD_TIME_LIMIT_S
    assert cuda.process_time_limit_cap_s == standin_settings.PROCESS_TIME_LIMIT_CAP_S
    assert cuda.contracts == ()
    assert cuda.memory_limit_bytes is None
    assert (cuda.unit, cuda.units_per_ns) == ("ns", 1)
    assert cuda.model_run is False
    assert cuda.instance_start is False
    assert cuda.coder_loop is False


def test_cuda_gpu_reads_the_process_cap_each_time_it_is_read(monkeypatch):
    monkeypatch.setattr(standin_settings, "PROCESS_TIME_LIMIT_CAP_S", 9)
    monkeypatch.setattr(standin_settings, "FLAGS", ("-O0",))
    cuda = TABLE[targets.CUDA_GPU]
    assert cuda.process_time_limit_cap_s == 9
    assert cuda.flags == targets.CUDA_GPU_FLAGS


def test_no_instance_and_no_coder_loop_starts_at_cuda_gpu():
    assert targets.CUDA_GPU not in targets.instance_start_accelerators()
    assert targets.CUDA_GPU not in targets.coder_loop_accelerators()


@pytest.mark.parametrize("tool", ["correctness.check", "sim.run", "board.run"])
def test_a_call_about_cuda_gpu_stays_no_backend(tool):
    from hilclaw import backends, check_definition, tools

    record = {
        "schema_version": keys.SCHEMA_VERSION,
        "accelerator": targets.CUDA_GPU,
        "revision": "Example GPU sm_00",
        "toolchain": {"nvcc": "n", "gcc": "g", "nvidia_driver": "d"},
        "host": {"cpu": "c", "os": "o"},
        "hw_source": "external",
    }
    with pytest.raises(tools.ToolFailure) as caught:
        backends.select(check_definition.default_table(), record, tool)
    assert caught.value.kind == tools.KIND_NO_BACKEND


def test_covers_at_cuda_gpu_admits_no_contract():
    covers = targets.covers_at(lambda record: True, targets.CUDA_GPU)
    assert covers(FP32_GEMM) is False
    assert covers(BF16_GEMM) is False


# covers_at (ADR-0197 decision 3)

FP32_GEMM = gemm_contract.op_signature_record(2, 3, 4)
BF16_GEMM = gemm_bf16_contract.op_signature_record(*gemm_bf16_contract.SHAPES[0])


class Asked:
    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def __call__(self, record):
        self.calls.append(record)
        return self.answer


def test_covers_at_virtual_npu_admits_a_served_contract_only():
    at = targets.covers_at(contract_table.check_covers, targets.VIRTUAL_NPU)
    assert at(BF16_GEMM) is True
    assert at(FP32_GEMM) is False
    assert contract_table.check_covers(FP32_GEMM) is True


def test_covers_at_cpu_standin_answers_as_covers():
    at = targets.covers_at(contract_table.start_covers, targets.CPU_STANDIN)
    for record in (FP32_GEMM, BF16_GEMM):
        assert at(record) is True
    assert at({**FP32_GEMM, "dtype": "fp16"}) is False


@pytest.mark.parametrize("name", [mock_backend.NAME, "acc_other", None, ["x"]])
def test_covers_at_a_name_with_no_target_is_covers_itself(name):
    assert targets.covers_at(contract_table.covers, name) is contract_table.covers


def test_covers_at_returns_an_answer_of_covers_that_is_not_true_unchanged():
    for answer in (False, None, 1):
        asked = Asked(answer)
        at = targets.covers_at(asked, targets.VIRTUAL_NPU)
        assert at(BF16_GEMM) is answer
        assert asked.calls == [BF16_GEMM]


def test_covers_at_reads_the_given_table_once():
    built = []

    def entry():
        built.append(None)
        return made(contracts=(("gemm", "fp32", "row_major", "c"),))

    table = targets._Table({"synthetic": entry})
    at = targets.covers_at(Asked(True), "synthetic", table)
    assert len(built) == 1
    assert at(FP32_GEMM) is True
    assert at(BF16_GEMM) is False
    assert len(built) == 1


def test_covers_at_refuses_a_covers_that_is_not_callable():
    with pytest.raises(TypeError, match="^covers"):
        targets.covers_at(None, targets.VIRTUAL_NPU)


def test_covers_at_passes_an_error_of_building_the_entry(monkeypatch):
    monkeypatch.setattr(standin_settings, "PROCESS_TIME_LIMIT_CAP_S", math.inf)
    with pytest.raises(ValueError, match="^process_time_limit_cap_s"):
        targets.covers_at(contract_table.covers, targets.VIRTUAL_NPU)


def test_covers_at_passes_what_covers_and_served_at_raise():
    def broken(record):
        raise RuntimeError("covers")

    with pytest.raises(RuntimeError, match="^covers$"):
        targets.covers_at(broken, targets.VIRTUAL_NPU)(BF16_GEMM)
    at = targets.covers_at(Asked(True), targets.VIRTUAL_NPU)
    with pytest.raises(keys.InvalidRecordError):
        at({**BF16_GEMM, "kind": "unknown_kind"})


# --- a candidate's flags (ADR-0198 decision 6) ---


@pytest.mark.parametrize("name", [targets.CPU_STANDIN, targets.VIRTUAL_NPU])
@pytest.mark.parametrize("flags", [("-O3", "-funroll-loops"), ["-O1"], ()])
def test_with_candidate_flags_puts_them_after_the_targets(name, flags):
    target = targets.target(name)
    widened = targets.with_candidate_flags(target, flags)
    assert type(widened) is Target
    assert widened.flags == (*target.flags, *flags)
    assert dataclasses.replace(widened, flags=target.flags) == target
    assert targets.target(name) == target


@pytest.mark.parametrize(
    "flag", ["-o", "-ofile", "-objcmt-migrate-all", "--output", "--output=x", "-O\0"]
)
def test_with_candidate_flags_refuses_what_the_build_refuses(flag):
    with pytest.raises(ValueError) as raised:
        targets.with_candidate_flags(targets.target(targets.CPU_STANDIN), ("-O2", flag))
    assert flag not in str(raised.value)


@pytest.mark.parametrize(
    ("target", "flags"),
    [
        ("cpu_standin", ()),
        (None, ()),
        ("standin", "-O3"),
        ("standin", ("-O3", 3)),
        ("standin", None),
        ("standin", iter(("-O3",))),
    ],
)
def test_with_candidate_flags_refuses_a_bad_argument(target, flags):
    if target == "standin":
        target = targets.target(targets.CPU_STANDIN)
    with pytest.raises(TypeError):
        targets.with_candidate_flags(target, flags)
