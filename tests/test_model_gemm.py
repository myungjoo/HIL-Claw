import copy
import os
import shutil
from pathlib import Path

import numpy as np
import pytest

from hilclaw import gemm_bf16_contract, gemm_contract, model_execute, model_gemm
from hilclaw.clang_build import BuildResult
from hilclaw.local_run import RunResult
from hilclaw.model_binding import (
    CALL_SITES,
    KERNEL_UNFIT,
    NO_KERNEL,
    BindingEntry,
    KernelReference,
    ModelDimensions,
)
from hilclaw.model_execute import BuildFailed, ModelExecution
from hilclaw.model_gemm import GemmRun, run
from hilclaw.model_run import ModelProgramResult, RunFailed

SMALL = ModelDimensions(
    hidden=8, intermediate=16, vocabulary=11, layers=2, heads=4, kv_heads=2, head_dim=2
)
TINY = ModelDimensions(
    hidden=3, intermediate=5, vocabulary=7, layers=1, heads=2, kv_heads=1, head_dim=1
)
OPTIONS = {
    "dtype": "fp32",
    "build_timeout_s": 30,
    "run_timeout_s": 7,
    "program_flags": ("-O1",),
    "program_trailing_flags": ("-ldl",),
    "compiler": "clang-x",
    "env": {"A": "1"},
    "prefix": ("/bin/wrap",),
    "parent": "/some/parent",
    "keep_out": ("/keep",),
}


def kernel(name, contract=None):
    if contract is None:
        contract = gemm_contract.task_contract(3, 4, 5)
    return KernelReference((f"{name}.c",), contract, ("-O2",))


def every_binding():
    return {site: [BindingEntry(kernel(site), "every")] for site in CALL_SITES}


def settings(**changes):
    values = {"prompt": [1, 2, 3], "generation_length": 4, "lm_head_rows": "all"}
    values.update(changes)
    return values


def matrices(m, k, n, seed):
    generator = np.random.default_rng(seed)
    a = generator.integers(-4, 5, size=(m, k)).astype(np.float32)
    b = generator.integers(-4, 5, size=(k, n)).astype(np.float32)
    return a, b


def widened(patterns):
    return (patterns.astype(np.uint32) << 16).view(np.float32)


def bf16_of(values):
    exact = np.asarray(values, dtype=np.float32)
    patterns = (exact.view(np.uint32) >> 16).astype(np.uint16)
    assert np.array_equal(widened(patterns), exact), "not exact in bf16"
    return patterns


def bf16_matrices(m, k, n, seed):
    a, b = matrices(m, k, n, seed)
    return bf16_of(a), bf16_of(b)


def nearest_bf16(values):
    words = np.asarray(values, dtype=np.float32).view(np.uint32).astype(np.uint64)
    return ((words + 0x7FFF + ((words >> 16) & 1)) >> 16).astype(np.uint16)


def operands_for(dimensions, binding, **changes):
    check = model_gemm.model_binding.check(
        dimensions, binding, dtype="fp32", **settings(**changes)
    )
    assert check.ok
    return {
        (site, shape): matrices(*shape, seed)
        for seed, (site, shape, _) in enumerate(check.calls)
    }


class Recorder:
    def __init__(self, result=None):
        self.calls = []
        self.result = result

    def __call__(self, kernels, calls, **options):
        self.calls.append((kernels, calls, options))
        if isinstance(self.result, BaseException):
            raise self.result
        return (
            self.result if self.result is not None else ModelExecution(None, None, True)
        )


@pytest.fixture
def recorder(monkeypatch):
    made = Recorder()
    monkeypatch.setattr(model_execute, "execute", made)
    return made


def recorded_run(binding, operands=None, dimensions=SMALL, **changes):
    if operands is None:
        operands = operands_for(dimensions, binding, **changes)
    return run(dimensions, binding, operands, **settings(**changes), **OPTIONS)


def test_every_binding_six_kernels_in_first_use_order(recorder):
    binding = every_binding()
    operands = operands_for(SMALL, binding)
    result = recorded_run(binding, operands)
    assert result.check.ok
    [(kernels, program_calls, options)] = recorder.calls
    assert kernels == [binding[site][0].kernel for site in CALL_SITES]
    assert options == OPTIONS
    assert len(result.check.calls) == 12
    expected = tuple(
        (site, shape, CALL_SITES.index(site)) for site, shape, _ in result.check.calls
    )
    assert result.calls == expected
    for (site, shape, index), (call_index, a, b) in zip(
        result.calls, program_calls, strict=True
    ):
        assert call_index == index
        assert a is operands[(site, shape)][0]
        assert b is operands[(site, shape)][1]
    assert result.execution == ModelExecution(None, None, True)


def test_one_reference_at_several_sites_and_equal_references_share_an_index(recorder):
    shared = kernel("shared")
    binding = {site: [BindingEntry(shared, "every")] for site in CALL_SITES[:3]}
    binding.update(
        {site: [BindingEntry(kernel("same"), "every")] for site in CALL_SITES[3:]}
    )
    result = recorded_run(binding)
    [(kernels, _, _)] = recorder.calls
    assert kernels == [shared, kernel("same")]
    assert {index for site, _, index in result.calls if site in CALL_SITES[:3]} == {0}
    assert {index for site, _, index in result.calls if site in CALL_SITES[3:]} == {1}


def test_disjoint_listed_shapes_of_one_site_get_distinct_indices(recorder):
    binding = every_binding()
    binding["qkv"] = [
        BindingEntry(kernel("decode"), ((1, 8, 16),)),
        BindingEntry(kernel("prefill"), ((3, 8, 16),)),
    ]
    result = recorded_run(binding)
    [(kernels, _, _)] = recorder.calls
    assert kernels[:2] == [kernel("decode"), kernel("prefill")]
    assert result.calls[:2] == (("qkv", (1, 8, 16), 0), ("qkv", (3, 8, 16), 1))
    assert len(kernels) == 7


def test_generation_length_one_and_last_rows_give_fewer_calls(recorder):
    result = recorded_run(every_binding(), generation_length=1)
    assert [shape[0] for _, shape, _ in result.calls] == [3] * 6
    result = recorded_run(every_binding(), lm_head_rows="last")
    assert len(result.calls) == 11
    assert result.calls[-1] == ("lm_head", (1, 8, 11), 5)
    assert [len(calls) for _, calls, _ in recorder.calls] == [6, 11]


@pytest.mark.parametrize("operands", [{}, {"x": 1}, None, "bad"])
def test_invalid_input_builds_nothing(recorder, operands):
    result = run(
        SMALL, every_binding(), operands, **settings(prompt=[1, 11]), **OPTIONS
    )
    assert not result.check.ok
    assert result.check.outcomes[0].kind == "invalid_input"
    assert result == GemmRun(result.check, (), None)
    assert recorder.calls == []


def test_no_kernel_builds_nothing(recorder):
    binding = every_binding()
    binding["down"] = [BindingEntry(kernel("prefill"), ((3, 16, 8),))]
    result = run(SMALL, binding, {}, **settings(), **OPTIONS)
    assert [(o.kind, o.call_site, o.shape) for o in result.check.outcomes] == [
        (NO_KERNEL, "down", (1, 16, 8))
    ]
    assert result.calls == () and result.execution is None
    assert recorder.calls == []


def test_kernel_unfit_builds_nothing(recorder):
    binding = every_binding()
    contract = gemm_contract.task_contract(3, 4, 5)
    contract["prototype"] = "void other(void);"
    binding["o"] = [BindingEntry(kernel("o", contract), "every")]
    result = run(SMALL, binding, object(), **settings(), **OPTIONS)
    assert [o.kind for o in result.check.outcomes] == [KERNEL_UNFIT]
    assert result.calls == () and result.execution is None
    assert recorder.calls == []


def bf16_binding():
    contract = gemm_bf16_contract.task_contract(3, 4, 5)
    return {
        site: [BindingEntry(kernel(site, contract), "every")] for site in CALL_SITES
    }


def bf16_operands_for(dimensions, binding, **changes):
    check = model_gemm.model_binding.check(
        dimensions, binding, dtype="bf16", **settings(**changes)
    )
    assert check.ok
    return {
        (site, shape): bf16_matrices(*shape, seed)
        for seed, (site, shape, _) in enumerate(check.calls)
    }


@pytest.mark.parametrize("dtype", ["fp32", "bf16"])
def test_check_and_execute_get_the_callers_dtype(recorder, monkeypatch, dtype):
    seen = []
    original = model_gemm.model_binding.check

    def spy(*args, **options):
        seen.append(options["dtype"])
        return original(*args, **options)

    monkeypatch.setattr(model_gemm.model_binding, "check", spy)
    binding = bf16_binding() if dtype == "bf16" else every_binding()
    make = bf16_operands_for if dtype == "bf16" else operands_for
    operands = make(SMALL, binding)
    seen.clear()
    result = run(SMALL, binding, operands, **settings(), **{**OPTIONS, "dtype": dtype})
    assert seen == [dtype]
    assert result.check.ok
    [(_, _, options)] = recorder.calls
    assert options == {**OPTIONS, "dtype": dtype}


def test_missing_dtype_is_refused(recorder):
    options = {key: value for key, value in OPTIONS.items() if key != "dtype"}
    with pytest.raises(TypeError, match="dtype"):
        run(SMALL, every_binding(), {}, **settings(), **options)
    assert recorder.calls == []


class _Untouchable:
    def __getattr__(self, name):
        raise AssertionError(f"operands looked at: {name}")


def test_dtype_without_contract_is_invalid_input(recorder):
    result = run(
        SMALL,
        every_binding(),
        _Untouchable(),
        **settings(),
        **{**OPTIONS, "dtype": "fp16"},
    )
    assert not result.check.ok
    assert [o.kind for o in result.check.outcomes] == ["invalid_input"]
    assert "fp16" in result.check.outcomes[0].reason
    assert result == GemmRun(result.check, (), None)
    assert recorder.calls == []


def test_fp32_kernels_at_bf16_are_unfit(recorder):
    result = run(
        SMALL, every_binding(), object(), **settings(), **{**OPTIONS, "dtype": "bf16"}
    )
    assert not result.check.ok
    assert [(o.kind, o.call_site) for o in result.check.outcomes] == [
        (KERNEL_UNFIT, site) for site in CALL_SITES
    ]
    assert result.calls == () and result.execution is None
    assert recorder.calls == []


def test_bf16_kernels_at_fp32_are_unfit(recorder):
    result = run(SMALL, bf16_binding(), object(), **settings(), **OPTIONS)
    assert not result.check.ok
    assert [(o.kind, o.call_site) for o in result.check.outcomes] == [
        (KERNEL_UNFIT, site) for site in CALL_SITES
    ]
    assert all("fp32 gemm contract" in o.reason for o in result.check.outcomes)
    assert result.calls == () and result.execution is None
    assert recorder.calls == []


@pytest.mark.parametrize("dtype", [1, None, b"bf16"])
def test_malformed_dtype_passes_on_what_check_raises(recorder, dtype):
    with pytest.raises(TypeError) as caught:
        run(SMALL, every_binding(), {}, **settings(), **{**OPTIONS, "dtype": dtype})
    with pytest.raises(TypeError) as expected:
        model_gemm.model_binding.check(
            SMALL, every_binding(), dtype=dtype, **settings()
        )
    assert str(caught.value) == str(expected.value)
    assert caught.value.parameter == "dtype"
    assert recorder.calls == []


def test_float32_arrays_at_bf16_reach_execute_uncast(recorder):
    binding = bf16_binding()
    operands = operands_for(SMALL, every_binding())
    run(SMALL, binding, operands, **settings(), **{**OPTIONS, "dtype": "bf16"})
    [(_, program_calls, options)] = recorder.calls
    assert options["dtype"] == "bf16"
    for _, a, b in program_calls:
        assert a.dtype == np.float32 and b.dtype == np.float32
    assert {id(x) for _, a, b in program_calls for x in (a, b)} == {
        id(x) for pair in operands.values() for x in pair
    }


def test_malformed_binding_is_passed_on(recorder):
    with pytest.raises(ValueError) as info:
        run(SMALL, {"nope": []}, {}, **settings(), **OPTIONS)
    assert info.value.parameter == "binding"
    assert recorder.calls == []


def test_wrong_dimensions_type_is_passed_on(recorder):
    with pytest.raises(TypeError) as info:
        run(tuple(SMALL), every_binding(), {}, **settings(), **OPTIONS)
    assert info.value.parameter == "dimensions"
    assert recorder.calls == []


KEY = ("down", (1, 16, 8))


def refused(recorder, kind, change):
    operands = operands_for(SMALL, every_binding())
    operands = change(operands)
    with pytest.raises(kind) as info:
        recorded_run(every_binding(), operands)
    assert recorder.calls == []
    return str(info.value)


def test_missing_key_is_refused(recorder):
    message = refused(
        recorder, ValueError, lambda o: {k: v for k, v in o.items() if k != KEY}
    )
    assert repr(KEY) in message and "missing" in message


def test_extra_key_is_refused(recorder):
    extra = ("down", (2, 16, 8))
    message = refused(recorder, ValueError, lambda o: {**o, extra: o[KEY]})
    assert repr(extra) in message and "no call" in message


@pytest.mark.parametrize("value", [None, (1,), [1, 2, 3], "ab"])
def test_value_that_is_not_a_pair_is_refused(recorder, value):
    message = refused(recorder, TypeError, lambda o: {**o, KEY: value})
    assert repr(KEY) in message and "pair" in message


def test_wrong_a_shape_is_refused(recorder):
    message = refused(
        recorder,
        ValueError,
        lambda o: {**o, KEY: (np.zeros((2, 16), np.float32), o[KEY][1])},
    )
    assert repr(KEY) in message and "a has shape (2, 16)" in message


def test_wrong_b_shape_is_refused(recorder):
    message = refused(
        recorder,
        ValueError,
        lambda o: {**o, KEY: [o[KEY][0], np.zeros((16, 9), np.float32)]},
    )
    assert repr(KEY) in message and "b has shape (16, 9)" in message


def test_non_mapping_operands_is_refused(recorder):
    with pytest.raises(TypeError) as info:
        recorded_run(every_binding(), [("qkv", 1)])
    assert "operands" in str(info.value)
    assert recorder.calls == []


@pytest.mark.parametrize(
    "replace, kind",
    [
        (lambda a: a.astype(np.float64), ValueError),
        (lambda a: a.reshape(-1), ValueError),
        (lambda a: a.tolist(), TypeError),
    ],
)
def test_arrays_refused_by_model_run_reach_execute(tmp_path, replace, kind):
    operands = operands_for(TINY, every_binding(), prompt=[1], generation_length=1)
    key = next(iter(operands))
    operands[key] = (replace(operands[key][0]), operands[key][1])
    with pytest.raises(kind) as info:
        run(
            TINY,
            every_binding(),
            operands,
            **settings(prompt=[1], generation_length=1),
            dtype="fp32",
            build_timeout_s=30,
            run_timeout_s=7,
            parent=tmp_path,
        )
    assert "calls[0]" in str(info.value)
    assert os.listdir(tmp_path) == []


def test_float32_arrays_at_bf16_pass_the_error_of_model_run(tmp_path):
    options = settings(prompt=[1], generation_length=1)
    binding = bf16_binding()
    operands = operands_for(TINY, every_binding(), prompt=[1], generation_length=1)
    calls = [(index, *pair) for index, pair in enumerate(operands.values())]
    with pytest.raises(ValueError) as caught:
        run(
            TINY,
            binding,
            operands,
            **options,
            dtype="bf16",
            build_timeout_s=30,
            run_timeout_s=7,
            parent=tmp_path,
        )
    with pytest.raises(ValueError) as expected:
        model_execute.model_run.output_shapes(calls, dtype="bf16")
    assert str(caught.value) == str(expected.value)
    assert os.listdir(tmp_path) == []


def test_build_failed_and_run_failed_are_returned_unchanged(recorder):
    build = BuildResult(False, 1, False, Path("x.so"), "log", ("cc",), 0.1)
    recorder.result = ModelExecution(BuildFailed(2, build), None, True)
    result = recorded_run(every_binding())
    assert result.execution is recorder.result
    failed = result.execution.build_failed.kernel
    assert {site for site, _, index in result.calls if index == failed} == {"gate"}
    runner = RunResult(1, False, b"", b"", ("prog",), 0.2)
    recorder.result = ModelExecution(
        None, ModelProgramResult(RunFailed.EXIT_STATUS, None, runner), True
    )
    result = recorded_run(every_binding())
    assert result.execution is recorder.result
    assert result.execution.run.failed is RunFailed.EXIT_STATUS


def test_exception_of_execute_is_passed_on(recorder):
    recorder.result = OSError("no parent")
    with pytest.raises(OSError, match="no parent"):
        recorded_run(every_binding())


def test_arguments_are_not_modified(recorder):
    binding = every_binding()
    operands = operands_for(SMALL, binding)
    prompt = [1, 2, 3]
    given = [0, 1, 2, 3]
    before = copy.deepcopy((binding, operands, prompt, given))
    run(
        SMALL,
        binding,
        operands,
        prompt=prompt,
        generation_length=4,
        lm_head_rows="all",
        given=given,
        **OPTIONS,
    )
    after = (binding, operands, prompt, given)
    assert before[0] == after[0] and before[2:] == after[2:]
    assert before[1].keys() == after[1].keys()
    for key, (a, b) in before[1].items():
        assert np.array_equal(a, after[1][key][0])
        assert np.array_equal(b, after[1][key][1])
    assert len(recorder.calls) == 1


def test_public_names_and_fields():
    public = {name for name in vars(model_gemm) if not name.startswith("_")}
    imported = {"Mapping", "NamedTuple", "model_binding", "model_execute"}
    assert public - imported == {"GemmRun", "run"}
    assert GemmRun._fields == ("check", "calls", "execution")
    text = Path(model_gemm.__file__).read_text(encoding="utf-8")
    assert "gemm_contract" not in text
    assert "__main__" not in text


PRODUCT = """\
#include <stddef.h>
void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c)
{
    size_t i, j, p;

    for (i = 0; i < m; i++)
        for (j = 0; j < n; j++) {
            float sum = @START@;

            for (p = 0; p < k; p++)
                sum += a[i * k + p] * b[p * n + j];
            c[i * n + j] = sum;
        }
}
"""

BF16_PRODUCT = """\
#include <stddef.h>
#include <stdint.h>
#include <string.h>

static float widen(uint16_t bits)
{
    uint32_t word = (uint32_t)bits << 16;
    float value;

    memcpy(&value, &word, sizeof value);
    return value;
}

static uint16_t narrow(float value)
{
    uint32_t word;

    memcpy(&word, &value, sizeof word);
    word += UINT32_C(0x7FFF) + ((word >> 16) & 1u);
    return (uint16_t)(word >> 16);
}

void hilclaw_gemm_bf16(size_t m, size_t k, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c)
{
    size_t i, j, p;

    for (i = 0; i < m; i++)
        for (j = 0; j < n; j++) {
            float sum = @START@;

            for (p = 0; p < k; p++)
                sum += widen(a[i * k + p]) * widen(b[p * n + j]);
            c[i * n + j] = narrow(sum);
        }
}
"""

SOURCES = {
    "plain": PRODUCT.replace("@START@", "0.0f"),
    "plus_one": PRODUCT.replace("@START@", "1.0f"),
    "broken": "void hilclaw_gemm(\n",
    "bf16_plain": BF16_PRODUCT.replace("@START@", "0.0f"),
    "bf16_plus_one": BF16_PRODUCT.replace("@START@", "1.0f"),
}


@pytest.fixture(scope="session")
def clang():
    if os.name != "posix":
        pytest.skip("the model program needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")


def real_kernel(directory, name):
    source = directory / f"{name}.c"
    source.write_text(SOURCES[name], encoding="ascii", newline="\n")
    contract = (
        gemm_bf16_contract.task_contract(3, 4, 5)
        if name.startswith("bf16_")
        else gemm_contract.task_contract(3, 4, 5)
    )
    return KernelReference((str(source),), contract, ("-O2",))


def real_run(tmp_path, binding, dtype="fp32"):
    builds = tmp_path / "builds"
    builds.mkdir()
    make = bf16_operands_for if dtype == "bf16" else operands_for
    operands = make(SMALL, binding)
    result = run(
        SMALL,
        binding,
        operands,
        **settings(),
        dtype=dtype,
        build_timeout_s=120,
        run_timeout_s=60,
        program_flags=("-O2",),
        program_trailing_flags=("-ldl",),
        parent=builds,
    )
    assert result.execution.removed is True
    assert os.listdir(builds) == []
    return result, operands


def sources_dir(tmp_path):
    directory = tmp_path / "sources"
    directory.mkdir()
    return directory


def test_real_every_binding_gives_the_products(clang, tmp_path):
    plain = real_kernel(sources_dir(tmp_path), "plain")
    binding = {site: [BindingEntry(plain, "every")] for site in CALL_SITES}
    result, operands = real_run(tmp_path, binding)
    assert result.execution.build_failed is None
    assert result.execution.run.failed is None, result.execution.run.run.stderr
    for (site, shape, index), output in zip(
        result.calls, result.execution.run.outputs, strict=True
    ):
        assert index == 0
        a, b = operands[(site, shape)]
        assert output.dtype == np.float32
        assert np.array_equal(output, a @ b)


def test_real_two_kernels_at_different_sites(clang, tmp_path):
    directory = sources_dir(tmp_path)
    plain = real_kernel(directory, "plain")
    plus_one = real_kernel(directory, "plus_one")
    binding = {
        site: [BindingEntry(plus_one if site in ("o", "down") else plain, "every")]
        for site in CALL_SITES
    }
    result, operands = real_run(tmp_path, binding)
    assert result.execution.run.failed is None, result.execution.run.run.stderr
    for (site, shape, index), output in zip(
        result.calls, result.execution.run.outputs, strict=True
    ):
        a, b = operands[(site, shape)]
        added = np.float32(1 if site in ("o", "down") else 0)
        assert index == (1 if site in ("o", "down") else 0)
        assert np.array_equal(output, a @ b + added)


def test_real_broken_kernel_gives_build_failed(clang, tmp_path):
    directory = sources_dir(tmp_path)
    plain = real_kernel(directory, "plain")
    broken = real_kernel(directory, "broken")
    binding = {
        site: [BindingEntry(broken if site == "up" else plain, "every")]
        for site in CALL_SITES
    }
    result, _ = real_run(tmp_path, binding)
    assert result.execution.build_failed.kernel == 1
    assert result.execution.build_failed.build.log
    assert result.execution.run is None
    assert {site for site, _, index in result.calls if index == 1} == {"up"}


def test_real_bf16_every_binding_gives_the_rounded_products(clang, tmp_path):
    plain = real_kernel(sources_dir(tmp_path), "bf16_plain")
    binding = {site: [BindingEntry(plain, "every")] for site in CALL_SITES}
    result, operands = real_run(tmp_path, binding, "bf16")
    assert result.check.ok
    assert result.execution.build_failed is None
    assert result.execution.run.failed is None, result.execution.run.run.stderr
    assert len(result.execution.run.outputs) == len(result.calls) == 12
    for (site, shape, index), output in zip(
        result.calls, result.execution.run.outputs, strict=True
    ):
        assert index == 0
        a, b = operands[(site, shape)]
        assert a.dtype == np.uint16 and b.dtype == np.uint16
        assert output.dtype == np.uint16
        assert np.array_equal(output, nearest_bf16(widened(a) @ widened(b)))


def test_real_bf16_two_kernels_at_different_sites(clang, tmp_path):
    directory = sources_dir(tmp_path)
    plain = real_kernel(directory, "bf16_plain")
    plus_one = real_kernel(directory, "bf16_plus_one")
    binding = {
        site: [BindingEntry(plus_one if site in ("o", "down") else plain, "every")]
        for site in CALL_SITES
    }
    result, operands = real_run(tmp_path, binding, "bf16")
    assert result.execution.run.failed is None, result.execution.run.run.stderr
    for (site, shape, index), output in zip(
        result.calls, result.execution.run.outputs, strict=True
    ):
        a, b = operands[(site, shape)]
        added = np.float32(1 if site in ("o", "down") else 0)
        assert index == (1 if site in ("o", "down") else 0)
        assert output.dtype == np.uint16
        assert np.array_equal(output, nearest_bf16(widened(a) @ widened(b) + added))
