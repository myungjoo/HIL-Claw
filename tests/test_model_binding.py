import copy
import inspect
import math
import struct
from pathlib import Path

import pytest

from hilclaw import gemm_bf16_contract, gemm_contract, rmsnorm_bf16_contract
from hilclaw.keys import MAX_INTEGER
from hilclaw.model_binding import (
    CALL_SITES,
    DTYPES,
    RMSNORM_CALL_SITES,
    RMSNORM_DTYPES,
    BindingCheck,
    BindingEntry,
    KernelReference,
    ModelDimensions,
    Outcome,
    check,
    check_dimensions,
    check_rmsnorm,
    gemm_shape,
    generation_calls,
    rmsnorm_eps,
    rmsnorm_generation_calls,
    rmsnorm_shape,
)

SMALL = ModelDimensions(
    hidden=8, intermediate=16, vocabulary=11, layers=2, heads=4, kv_heads=2, head_dim=2
)
SMALL_KN = {
    "qkv": (8, 16),
    "o": (8, 8),
    "gate": (8, 16),
    "up": (8, 16),
    "down": (16, 8),
    "lm_head": (8, 11),
}


_DEFAULT = object()
CONTRACTS = {"fp32": gemm_contract, "bf16": gemm_bf16_contract}


def kernel(name="k", contract=_DEFAULT, dtype="fp32"):
    if contract is _DEFAULT:
        contract = CONTRACTS[dtype].task_contract(3, 4, 5)
    return KernelReference((f"{name}.c",), contract, ("-O2",))


def every_binding(dtype="fp32"):
    return {
        site: [BindingEntry(kernel(site, dtype=dtype), "every")] for site in CALL_SITES
    }


@pytest.fixture(params=["fp32", "bf16"])
def dtype(request):
    return request.param


def run(binding=None, **settings):
    arguments = {
        "dtype": "fp32",
        "prompt": [1, 2, 3],
        "generation_length": 4,
        "lm_head_rows": "all",
    }
    arguments.update(settings)
    return check(SMALL, every_binding() if binding is None else binding, **arguments)


def raises(kind, parameter, function, *args, **kwargs):
    with pytest.raises(kind) as info:
        function(*args, **kwargs)
    assert info.value.parameter == parameter
    return info.value


def test_call_sites():
    assert CALL_SITES == ("qkv", "o", "gate", "up", "down", "lm_head")


def test_named_tuples():
    assert ModelDimensions._fields == (
        "hidden",
        "intermediate",
        "vocabulary",
        "layers",
        "heads",
        "kv_heads",
        "head_dim",
    )
    assert KernelReference._fields == ("sources", "contract", "flags")
    assert BindingEntry._fields == ("kernel", "shapes")
    assert Outcome._fields == ("kind", "call_site", "shape", "reason")
    assert BindingCheck._fields == ("ok", "outcomes", "calls")


def test_dimensions_have_no_defaults():
    with pytest.raises(TypeError):
        ModelDimensions()
    assert ModelDimensions._field_defaults == {}


def test_check_dimensions_accepts():
    assert check_dimensions(SMALL) is None
    check_dimensions(ModelDimensions(*([MAX_INTEGER] * 4), 1, 1, 1))


@pytest.mark.parametrize("field", ModelDimensions._fields)
@pytest.mark.parametrize("value", [True, 2.0, "2", None])
def test_check_dimensions_refuses_types(field, value):
    raises(TypeError, "dimensions", check_dimensions, SMALL._replace(**{field: value}))


@pytest.mark.parametrize("field", ModelDimensions._fields)
@pytest.mark.parametrize("value", [0, -1, MAX_INTEGER + 1])
def test_check_dimensions_refuses_range(field, value):
    raises(ValueError, "dimensions", check_dimensions, SMALL._replace(**{field: value}))


def test_check_dimensions_refuses_non_dimensions():
    raises(TypeError, "dimensions", check_dimensions, tuple(SMALL))
    raises(TypeError, "dimensions", check_dimensions, None)


def test_check_dimensions_heads_multiple_of_kv_heads():
    error = raises(ValueError, "dimensions", check_dimensions, SMALL._replace(heads=3))
    assert "multiple" in str(error)


def test_check_dimensions_refuses_too_wide_heads():
    wide = SMALL._replace(heads=2, kv_heads=2, head_dim=MAX_INTEGER // 4)
    raises(ValueError, "dimensions", check_dimensions, wide)


@pytest.mark.parametrize("site", CALL_SITES)
@pytest.mark.parametrize("rows", [1, 7, MAX_INTEGER])
def test_gemm_shape_small(site, rows):
    assert gemm_shape(SMALL, site, rows) == (rows, *SMALL_KN[site])


def test_gemm_shape_at_llama_values_is_adr_0152_table():
    llama = ModelDimensions(2048, 8192, 128256, 16, 32, 8, 64)
    table = {
        "qkv": (2048, 3072),
        "o": (2048, 2048),
        "gate": (2048, 8192),
        "up": (2048, 8192),
        "down": (8192, 2048),
        "lm_head": (2048, 128256),
    }
    for site in CALL_SITES:
        for m in (1, 32, 512):
            assert gemm_shape(llama, site, m) == (m, *table[site])


@pytest.mark.parametrize("site", ["QKV", "rmsnorm", "", None, 3])
def test_gemm_shape_unknown_call_site(site):
    raises(ValueError, "call_site", gemm_shape, SMALL, site, 1)


@pytest.mark.parametrize(
    ("rows", "kind"),
    [
        (True, TypeError),
        (1.0, TypeError),
        (None, TypeError),
        (0, ValueError),
        (MAX_INTEGER + 1, ValueError),
    ],
)
def test_gemm_shape_bad_rows(rows, kind):
    raises(kind, "rows", gemm_shape, SMALL, "o", rows)


def test_gemm_shape_checks_dimensions():
    raises(ValueError, "dimensions", gemm_shape, SMALL._replace(hidden=0), "o", 1)


def shapes_of(rows, site):
    return tuple((r, *SMALL_KN[site]) for r in rows)


def test_generation_calls_prefill_and_decode():
    calls = generation_calls(
        SMALL, prompt_length=5, generation_length=3, lm_head_rows="all"
    )
    assert calls == tuple((site, shapes_of((1, 5), site)) for site in CALL_SITES)


def test_generation_calls_one_token_has_no_decode():
    calls = generation_calls(
        SMALL, prompt_length=5, generation_length=1, lm_head_rows="all"
    )
    assert calls == tuple((site, shapes_of((5,), site)) for site in CALL_SITES)


def test_generation_calls_lm_head_last():
    calls = dict(
        generation_calls(
            SMALL, prompt_length=5, generation_length=1, lm_head_rows="last"
        )
    )
    assert calls["lm_head"] == shapes_of((1,), "lm_head")
    assert calls["down"] == shapes_of((5,), "down")


def test_generation_calls_prompt_of_one_row():
    calls = dict(
        generation_calls(
            SMALL, prompt_length=1, generation_length=4, lm_head_rows="all"
        )
    )
    assert calls["qkv"] == shapes_of((1,), "qkv")


@pytest.mark.parametrize(
    ("name", "value", "kind"),
    [
        ("prompt_length", 0, ValueError),
        ("prompt_length", True, TypeError),
        ("prompt_length", 2.0, TypeError),
        ("generation_length", 0, ValueError),
        ("generation_length", MAX_INTEGER + 1, ValueError),
        ("generation_length", None, TypeError),
        ("lm_head_rows", "first", ValueError),
        ("lm_head_rows", None, TypeError),
        ("lm_head_rows", ["all"], TypeError),
    ],
)
def test_generation_calls_refuses(name, value, kind):
    arguments = {"prompt_length": 2, "generation_length": 2, "lm_head_rows": "all"}
    arguments[name] = value
    raises(kind, name, generation_calls, SMALL, **arguments)


def test_generation_calls_checks_dimensions():
    raises(
        TypeError,
        "dimensions",
        generation_calls,
        None,
        prompt_length=1,
        generation_length=1,
        lm_head_rows="all",
    )


def expected_calls(binding, rows):
    return tuple(
        (site, (r, *SMALL_KN[site]), binding[site][0].kernel)
        for site in CALL_SITES
        for r in rows
    )


def test_check_every_binding_is_ok():
    binding = every_binding()
    result = run(binding)
    assert result == BindingCheck(True, (), expected_calls(binding, (1, 3)))
    assert isinstance(result, BindingCheck)


def test_check_listed_shapes_cover_exactly():
    binding = {
        site: [BindingEntry(kernel(site), shapes_of((1, 3), site))]
        for site in CALL_SITES
    }
    result = run(binding)
    assert result.ok
    assert result.calls == expected_calls(binding, (1, 3))


def test_check_several_entries_disjoint_shapes():
    binding = every_binding()
    decode = kernel("decode")
    prefill = kernel("prefill")
    binding["down"] = [
        BindingEntry(decode, shapes_of((1,), "down")),
        BindingEntry(prefill, shapes_of((3, 9), "down")),
    ]
    result = run(binding)
    assert result.ok
    down = [call for call in result.calls if call[0] == "down"]
    assert down == [("down", (1, 16, 8), decode), ("down", (3, 16, 8), prefill)]


def test_check_generation_length_one():
    result = run(generation_length=1)
    assert result.ok
    assert [call[1][0] for call in result.calls] == [3] * len(CALL_SITES)


def test_check_lm_head_last():
    result = run(lm_head_rows="last")
    lm_head = [call[1] for call in result.calls if call[0] == "lm_head"]
    assert lm_head == [(1, 8, 11)]


def test_check_given_sequence_mode():
    assert run(given=[0, 10, 5, 2]) == run()
    assert run(given=(4,), generation_length=1).ok


def test_check_accepts_path_sources_and_tuple_entries():
    binding = every_binding()
    binding["o"] = (
        BindingEntry(
            KernelReference(
                (Path("a.c"), "b.c"), gemm_contract.task_contract(1, 1, 1), ()
            ),
            "every",
        ),
    )
    assert run(binding).ok


def invalid(*reasons):
    return tuple(Outcome("invalid_input", None, None, reason) for reason in reasons)


def test_check_invalid_prompt_token():
    result = run(prompt=[1, 11, -1])
    assert result == BindingCheck(
        False,
        invalid(
            "prompt[1]: token id 11 is outside 0 to 10",
            "prompt[2]: token id -1 is outside 0 to 10",
        ),
        (),
    )


def test_check_empty_prompt():
    assert run(prompt=()).outcomes == invalid("prompt: is empty")


def test_check_generation_length_below_one():
    result = run(generation_length=0)
    assert result.outcomes == invalid(
        "generation_length: must be from 1 to 2**53 - 1, got 0"
    )


def test_check_generation_length_above_bound():
    result = run(generation_length=MAX_INTEGER + 1, given=[1])
    assert [o.reason[:18] for o in result.outcomes] == ["generation_length:"]


def test_check_lm_head_rows_outside():
    result = run(lm_head_rows="first")
    assert [o.kind for o in result.outcomes] == ["invalid_input"]
    assert result.outcomes[0].reason.startswith("lm_head_rows:")


def test_check_given_wrong_length():
    result = run(given=[1, 2])
    assert result.outcomes == invalid("given: has 2 token ids, generation_length is 4")
    assert not result.ok and result.calls == ()


def test_check_given_length_not_compared_when_generation_length_invalid():
    result = run(given=[1], generation_length=0)
    assert result.outcomes == invalid(
        "generation_length: must be from 1 to 2**53 - 1, got 0"
    )


def test_check_given_token_outside():
    result = run(given=[1, 2, 3, 99])
    assert result.outcomes == invalid("given[3]: token id 99 is outside 0 to 10")


def test_check_invalid_input_order_and_no_shape_check():
    binding = every_binding()
    del binding["qkv"]
    binding["o"] = [BindingEntry(kernel(contract={}), "every")]
    result = run(binding, prompt=[], generation_length=0, lm_head_rows="x", given=[12])
    assert [o.kind for o in result.outcomes] == [
        "invalid_input",
        "invalid_input",
        "invalid_input",
        "invalid_input",
        "kernel_unfit",
    ]
    reasons = [o.reason for o in result.outcomes]
    assert reasons[0] == "prompt: is empty"
    assert reasons[1].startswith("generation_length:")
    assert reasons[2].startswith("lm_head_rows:")
    assert reasons[3].startswith("given[0]:")
    assert result.outcomes[4].call_site == "o"
    assert result.calls == ()


def test_check_missing_call_site():
    binding = every_binding()
    del binding["gate"]
    result = run(binding)
    assert not result.ok
    assert result.calls == ()
    assert result.outcomes == tuple(
        Outcome("no_kernel", "gate", shape, "no entry of the binding covers the shape")
        for shape in shapes_of((1, 3), "gate")
    )


def test_check_unlisted_shape():
    binding = every_binding()
    binding["up"] = [BindingEntry(kernel(), shapes_of((3,), "up"))]
    result = run(binding)
    assert [(o.kind, o.call_site, o.shape) for o in result.outcomes] == [
        ("no_kernel", "up", (1, 8, 16))
    ]


def unfit_reason(contract, dtype="fp32"):
    binding = every_binding(dtype)
    binding["qkv"] = [BindingEntry(kernel(contract=contract), "every")]
    result = run(binding, dtype=dtype)
    assert not result.ok and result.calls == ()
    (outcome,) = result.outcomes
    assert outcome.kind == "kernel_unfit"
    assert outcome.call_site == "qkv" and outcome.shape is None
    assert outcome.reason.startswith("entry 0: ")
    return outcome.reason


def good_contract(dtype="fp32"):
    return CONTRACTS[dtype].task_contract(2, 3, 4)


def test_unfit_wrong_prototype(dtype):
    contract = good_contract(dtype)
    contract["prototype"] = contract["prototype"].replace("restrict a", "a")
    reason = unfit_reason(contract, dtype)
    assert reason == (
        f"entry 0: contract.prototype is not that of the {dtype} gemm contract"
    )


def test_unfit_wrong_language(dtype):
    contract = good_contract(dtype)
    contract["language"] = "cpp"
    reason = unfit_reason(contract, dtype)
    assert reason == (
        f"entry 0: contract.language is not that of the {dtype} gemm contract"
    )


def test_unfit_wrong_role(dtype):
    contract = good_contract(dtype)
    contract["operands"][1]["role"] = "output"
    reason = unfit_reason(contract, dtype)
    assert f"operands[1].role is not that of the {dtype} gemm contract" in reason


def test_unfit_wrong_dtype(dtype):
    contract = good_contract(dtype)
    contract["operands"][2]["dtype"] = "fp16"
    reason = unfit_reason(contract, dtype)
    assert f"operands[2].dtype is not that of the {dtype} gemm contract" in reason


def test_unfit_wrong_name(dtype):
    contract = good_contract(dtype)
    contract["operands"][0]["name"] = "x"
    reason = unfit_reason(contract, dtype)
    assert f"operands[0].name is not that of the {dtype} gemm contract" in reason


def test_unfit_non_string_value(dtype):
    contract = good_contract(dtype)
    contract["language"] = None
    assert "language" in unfit_reason(contract, dtype)


@pytest.mark.parametrize("contract", [None, "c", ["language"], 3])
def test_unfit_non_mapping(contract, dtype):
    assert "not a mapping" in unfit_reason(contract, dtype)


@pytest.mark.parametrize("member", ["language", "prototype", "operands"])
def test_unfit_missing_member(member, dtype):
    contract = good_contract(dtype)
    del contract[member]
    assert repr(member) in unfit_reason(contract, dtype)


def test_unfit_operands_forms(dtype):
    contract = good_contract(dtype)
    contract["operands"] = "abc"
    assert "not a sequence" in unfit_reason(contract, dtype)
    contract["operands"] = good_contract(dtype)["operands"][:2]
    assert "2 entries" in unfit_reason(contract, dtype)
    contract["operands"] = [None, *good_contract(dtype)["operands"][1:]]
    assert "operands[0] is not a mapping" in unfit_reason(contract, dtype)
    contract["operands"] = good_contract(dtype)["operands"]
    del contract["operands"][2]["dtype"]
    assert "operands[2] lacks" in unfit_reason(contract, dtype)


def test_fit_ignores_operand_shapes_and_extra_members(dtype):
    contract = good_contract(dtype)
    contract["operands"][0]["shape"] = [99, 99]
    contract["note"] = "x"
    binding = every_binding(dtype)
    binding["qkv"] = [BindingEntry(kernel(contract=contract), "every")]
    assert run(binding, dtype=dtype).ok


def test_fit_reference_comes_from_the_selected_contract(monkeypatch, dtype):
    binding = every_binding(dtype)
    changed = good_contract(dtype)
    changed["prototype"] = "void other(void);"
    monkeypatch.setattr(
        CONTRACTS[dtype], "task_contract", lambda m, k, n: copy.deepcopy(changed)
    )
    result = run(binding, dtype=dtype)
    assert len(result.outcomes) == len(CALL_SITES)
    assert {o.kind for o in result.outcomes} == {"kernel_unfit"}


def test_check_outcome_order():
    binding = every_binding()
    binding["qkv"] = [
        BindingEntry(kernel(), shapes_of((3,), "qkv")),
        BindingEntry(kernel(contract=None), shapes_of((7,), "qkv")),
    ]
    del binding["o"]
    binding["lm_head"] = [BindingEntry(kernel(contract={}), "every")]
    result = run(binding)
    assert [(o.kind, o.call_site, o.shape) for o in result.outcomes] == [
        ("kernel_unfit", "qkv", None),
        ("no_kernel", "qkv", (1, 8, 16)),
        ("no_kernel", "o", (1, 8, 8)),
        ("no_kernel", "o", (3, 8, 8)),
        ("kernel_unfit", "lm_head", None),
    ]
    assert result.outcomes[0].reason.startswith("entry 1: ")


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("prompt", "abc"),
        ("prompt", b"ab"),
        ("prompt", 3),
        ("prompt", {1, 2}),
        ("prompt", [1, True]),
        ("prompt", [1, 2.0]),
        ("given", "abcd"),
        ("given", 4),
        ("given", [1, 2, 3, None]),
        ("given", [False, 1, 2, 3]),
        ("generation_length", True),
        ("generation_length", 4.0),
        ("generation_length", None),
        ("lm_head_rows", None),
        ("lm_head_rows", 1),
    ],
)
def test_check_type_errors(name, value):
    raises(TypeError, name, run, **{name: value})


def test_check_dimension_errors():
    arguments = {
        "dtype": "fp32",
        "prompt": [1],
        "generation_length": 1,
        "lm_head_rows": "all",
    }
    raises(TypeError, "dimensions", check, tuple(SMALL), every_binding(), **arguments)
    raises(
        ValueError,
        "dimensions",
        check,
        SMALL._replace(kv_heads=3),
        every_binding(),
        **arguments,
    )


def test_check_argument_order():
    raises(
        TypeError,
        "dimensions",
        check,
        tuple(SMALL),
        None,
        dtype=None,
        prompt=None,
        generation_length=None,
        lm_head_rows=None,
    )
    raises(ValueError, "dtype", run, binding=None, dtype="FP32", prompt=None)
    raises(TypeError, "dtype", run, dtype=b"fp32", prompt=None, given=1)
    raises(TypeError, "prompt", run, binding=None, prompt=None, generation_length=None)
    raises(TypeError, "given", run, given=1, generation_length=None)
    raises(
        TypeError, "generation_length", run, generation_length=None, lm_head_rows=None
    )
    raises(TypeError, "lm_head_rows", run, binding=[], lm_head_rows=None)


def with_entry(site, *entries):
    binding = every_binding()
    binding[site] = list(entries)
    return binding


def bad_binding(kind, binding):
    return raises(kind, "binding", run, binding)


def test_binding_not_mapping():
    bad_binding(TypeError, [("qkv", [])])
    arguments = {
        "dtype": "fp32",
        "prompt": [1],
        "generation_length": 1,
        "lm_head_rows": "all",
    }
    raises(TypeError, "binding", check, SMALL, None, **arguments)


@pytest.mark.parametrize("key", ["rmsnorm", "QKV", 1, None])
def test_binding_unknown_key(key):
    binding = every_binding()
    binding[key] = [BindingEntry(kernel(), "every")]
    bad_binding(ValueError, binding)


def test_binding_entries_forms():
    binding = every_binding()
    binding["o"] = BindingEntry(kernel(), "every")
    bad_binding(TypeError, binding)
    binding["o"] = "every"
    bad_binding(TypeError, binding)
    binding["o"] = []
    bad_binding(ValueError, binding)
    binding["o"] = None
    bad_binding(TypeError, binding)


def test_binding_entry_types():
    bad_binding(TypeError, with_entry("o", (kernel(), "every")))
    bad_binding(TypeError, with_entry("o", BindingEntry(("o.c",), "every")))


@pytest.mark.parametrize(
    ("reference", "kind"),
    [
        (KernelReference([Path("o.c")], {}, ()), TypeError),
        (KernelReference((), {}, ()), ValueError),
        (KernelReference((b"o.c",), {}, ()), TypeError),
        (KernelReference(("o.c",), {}, ["-O2"]), TypeError),
        (KernelReference(("o.c",), {}, ("-O2", 3)), TypeError),
    ],
)
def test_binding_kernel_reference_refused(reference, kind):
    bad_binding(kind, with_entry("o", BindingEntry(reference, "every")))


@pytest.mark.parametrize(
    ("shapes", "kind"),
    [
        ("all", ValueError),
        ([(1, 8, 8)], TypeError),
        ((), ValueError),
        (None, TypeError),
        (([1, 8, 8],), TypeError),
        (((1, 8),), ValueError),
        (((1, 8, 8, 1),), ValueError),
        (((0, 8, 8),), ValueError),
        (((1, 8, MAX_INTEGER + 1),), ValueError),
        (((True, 8, 8),), TypeError),
        (((1.0, 8, 8),), TypeError),
    ],
)
def test_binding_shapes_refused(shapes, kind):
    bad_binding(kind, with_entry("o", BindingEntry(kernel(), shapes)))


def test_binding_overlapping_entries():
    error = bad_binding(
        ValueError,
        with_entry(
            "o",
            BindingEntry(kernel(), ((1, 8, 8), (3, 8, 8))),
            BindingEntry(kernel(), ((3, 8, 8),)),
        ),
    )
    assert "(3, 8, 8)" in str(error)


def test_binding_every_beside_another_entry():
    bad_binding(
        ValueError,
        with_entry(
            "o", BindingEntry(kernel(), ((5, 8, 8),)), BindingEntry(kernel(), "every")
        ),
    )
    bad_binding(
        ValueError,
        with_entry(
            "o", BindingEntry(kernel(), "every"), BindingEntry(kernel(), "every")
        ),
    )


def test_binding_malformed_refused_even_with_invalid_input():
    binding = with_entry(
        "o", BindingEntry(kernel(), "every"), BindingEntry(kernel(), "every")
    )
    raises(ValueError, "binding", run, binding, prompt=[])


def test_check_does_not_modify_arguments():
    binding = every_binding()
    binding["down"] = [
        BindingEntry(kernel(), shapes_of((1,), "down")),
        BindingEntry(kernel(), shapes_of((3,), "down")),
    ]
    binding["o"] = [BindingEntry(kernel(contract={"language": "c"}), "every")]
    prompt = [1, 2, 3]
    given = [4, 5, 6, 7]
    before = copy.deepcopy((binding, prompt, given))
    run(binding, prompt=prompt, given=given)
    assert (binding, prompt, given) == before
    binding["qkv"] = [BindingEntry(kernel(dtype="bf16"), "every")]
    before = copy.deepcopy((binding, prompt, given))
    run(binding, dtype="bf16", prompt=prompt, given=given)
    run(binding, dtype="fp16", prompt=prompt, given=given)
    assert (binding, prompt, given) == before


def test_dtypes():
    assert DTYPES == ("fp32", "bf16")
    assert DTYPES == (gemm_contract.DTYPE, gemm_bf16_contract.DTYPE)


def test_check_dtype_is_keyword_only_without_default():
    parameter = inspect.signature(check).parameters["dtype"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty
    with pytest.raises(TypeError, match="dtype"):
        check(
            SMALL, every_binding(), prompt=[1], generation_length=1, lm_head_rows="all"
        )


def test_check_bf16_every_binding_is_ok():
    binding = every_binding("bf16")
    result = run(binding, dtype="bf16")
    assert result == BindingCheck(True, (), expected_calls(binding, (1, 3)))
    fp32 = run(every_binding())
    assert [call[:2] for call in result.calls] == [call[:2] for call in fp32.calls]


def test_check_bf16_listed_shapes_other_than_the_spec_own():
    binding = {
        site: [BindingEntry(kernel(site, dtype="bf16"), shapes_of((1, 3, 7), site))]
        for site in CALL_SITES
    }
    fp32 = {
        site: [BindingEntry(kernel(site), shapes_of((1, 3, 7), site))]
        for site in CALL_SITES
    }
    result = run(binding, dtype="bf16")
    assert result.ok
    assert result.calls == expected_calls(binding, (1, 3))
    expected = run(fp32)
    assert [call[:2] for call in result.calls] == [call[:2] for call in expected.calls]


@pytest.mark.parametrize(("dtype", "other"), [("bf16", "fp32"), ("fp32", "bf16")])
def test_kernel_of_the_other_dtype_is_unfit(dtype, other):
    binding = every_binding(other)
    binding["down"].append(BindingEntry(kernel(dtype=other), ((99, 16, 8),)))
    binding["down"][0] = BindingEntry(
        binding["down"][0].kernel, shapes_of((1, 3), "down")
    )
    result = run(binding, dtype=dtype)
    reason = f"contract.prototype is not that of the {dtype} gemm contract"
    assert result == BindingCheck(
        False,
        tuple(
            Outcome("kernel_unfit", site, None, f"entry {index}: {reason}")
            for site in CALL_SITES
            for index in range(len(binding[site]))
        ),
        (),
    )


def test_mixed_binding_in_a_bf16_generation():
    binding = every_binding("bf16")
    for site in ("o", "down"):
        binding[site] = [BindingEntry(kernel(site), "every")]
    result = run(binding, dtype="bf16")
    assert [(o.kind, o.call_site) for o in result.outcomes] == [
        ("kernel_unfit", "o"),
        ("kernel_unfit", "down"),
    ]
    assert result.calls == ()


@pytest.mark.parametrize("unknown", ["fp16", "int8"])
def test_unknown_dtype_is_invalid_input(unknown):
    reason = f"dtype: no gemm contract is known at the dtype {unknown!r}"
    assert run(dtype=unknown) == BindingCheck(False, invalid(reason), ())
    result = run(dtype=unknown, prompt=[], lm_head_rows="x")
    assert [o.reason for o in result.outcomes][:2] == [reason, "prompt: is empty"]
    assert result.outcomes[2].reason.startswith("lm_head_rows:")
    assert {o.kind for o in result.outcomes} == {"invalid_input"}


@pytest.mark.parametrize("unknown", ["fp16", "int8"])
def test_unknown_dtype_gives_no_unfit_and_no_kernel(unknown):
    reason = f"dtype: no gemm contract is known at the dtype {unknown!r}"
    for binding in (every_binding(), every_binding("bf16")):
        binding["o"] = [BindingEntry(kernel(contract={}), "every")]
        del binding["gate"]
        binding["down"] = [BindingEntry(kernel(), shapes_of((3,), "down"))]
        assert run(binding, dtype=unknown) == BindingCheck(False, invalid(reason), ())


@pytest.mark.parametrize("value", [None, 1, b"fp32", True])
def test_check_dtype_type_errors(value):
    raises(TypeError, "dtype", run, dtype=value)


@pytest.mark.parametrize("value", ["", "FP32", "bf-16", "1fp", "fp32 ", "a" * 33])
def test_check_dtype_value_errors(value):
    raises(ValueError, "dtype", run, dtype=value)


def test_check_dtype_of_32_characters_is_a_name():
    name = "a" * 32
    reason = f"dtype: no gemm contract is known at the dtype {name!r}"
    assert run(dtype=name).outcomes == invalid(reason)


def test_check_refuses_an_rmsnorm_call_site_key_and_a_pair_shape():
    for site in RMSNORM_CALL_SITES:
        binding = every_binding()
        binding[site] = [BindingEntry(norm_kernel(), "every")]
        bad_binding(ValueError, binding)
    error = bad_binding(ValueError, with_entry("o", BindingEntry(kernel(), ((1, 8),))))
    assert "not 3" in str(error)


def test_rmsnorm_call_sites():
    assert RMSNORM_CALL_SITES == ("attention_norm", "ffn_norm", "norm")
    assert not set(RMSNORM_CALL_SITES) & set(CALL_SITES)


def test_rmsnorm_dtypes():
    assert RMSNORM_DTYPES == ("bf16",)
    assert RMSNORM_DTYPES == (rmsnorm_bf16_contract.DTYPE,)


@pytest.mark.parametrize("site", RMSNORM_CALL_SITES)
@pytest.mark.parametrize("rows", [1, 7, MAX_INTEGER])
def test_rmsnorm_shape_small(site, rows):
    assert rmsnorm_shape(SMALL, site, rows) == (rows, 8)


def test_rmsnorm_shape_at_llama_values_is_the_contract_table():
    llama = ModelDimensions(2048, 8192, 128256, 16, 32, 8, 64)
    for site in RMSNORM_CALL_SITES:
        shapes = tuple(rmsnorm_shape(llama, site, m) for m in (1, 32, 512))
        assert shapes == rmsnorm_bf16_contract.SHAPES


@pytest.mark.parametrize("site", ["qkv", "lm_head", "rmsnorm", "Norm", "", None, 3])
def test_rmsnorm_shape_unknown_call_site(site):
    raises(ValueError, "call_site", rmsnorm_shape, SMALL, site, 1)


@pytest.mark.parametrize(
    ("rows", "kind"),
    [
        (True, TypeError),
        (1.0, TypeError),
        (None, TypeError),
        (0, ValueError),
        (-1, ValueError),
        (MAX_INTEGER + 1, ValueError),
    ],
)
def test_rmsnorm_shape_bad_rows(rows, kind):
    raises(kind, "rows", rmsnorm_shape, SMALL, "norm", rows)


def test_rmsnorm_shape_argument_order():
    raises(ValueError, "dimensions", rmsnorm_shape, SMALL._replace(hidden=0), "x", 0)
    raises(TypeError, "dimensions", rmsnorm_shape, None, "norm", 1)
    raises(ValueError, "call_site", rmsnorm_shape, SMALL, "qkv", 0)


def norm_shapes(rows):
    return tuple((r, 8) for r in rows)


def test_rmsnorm_generation_calls_prefill_and_decode():
    calls = rmsnorm_generation_calls(SMALL, prompt_length=5, generation_length=3)
    assert calls == tuple((site, norm_shapes((1, 5))) for site in RMSNORM_CALL_SITES)


def test_rmsnorm_generation_calls_one_token_has_no_decode():
    calls = rmsnorm_generation_calls(SMALL, prompt_length=5, generation_length=1)
    assert calls == tuple((site, norm_shapes((5,))) for site in RMSNORM_CALL_SITES)


def test_rmsnorm_generation_calls_prompt_of_one_row():
    calls = rmsnorm_generation_calls(SMALL, prompt_length=1, generation_length=4)
    assert calls == tuple((site, norm_shapes((1,))) for site in RMSNORM_CALL_SITES)


def test_rmsnorm_generation_calls_rows_match_the_gemm_passes():
    gemm = dict(
        generation_calls(
            SMALL, prompt_length=6, generation_length=2, lm_head_rows="all"
        )
    )
    norm = dict(rmsnorm_generation_calls(SMALL, prompt_length=6, generation_length=2))
    assert [s[0] for s in norm["attention_norm"]] == [s[0] for s in gemm["qkv"]]


@pytest.mark.parametrize(
    ("name", "value", "kind"),
    [
        ("prompt_length", 0, ValueError),
        ("prompt_length", True, TypeError),
        ("prompt_length", 2.0, TypeError),
        ("generation_length", 0, ValueError),
        ("generation_length", MAX_INTEGER + 1, ValueError),
        ("generation_length", None, TypeError),
    ],
)
def test_rmsnorm_generation_calls_refuses(name, value, kind):
    arguments = {"prompt_length": 2, "generation_length": 2}
    arguments[name] = value
    raises(kind, name, rmsnorm_generation_calls, SMALL, **arguments)


def test_rmsnorm_generation_calls_argument_order():
    raises(
        TypeError,
        "dimensions",
        rmsnorm_generation_calls,
        None,
        prompt_length=0,
        generation_length=0,
    )
    raises(
        ValueError,
        "prompt_length",
        rmsnorm_generation_calls,
        SMALL,
        prompt_length=0,
        generation_length=None,
    )


def test_rmsnorm_generation_calls_lengths_are_keyword_only():
    with pytest.raises(TypeError):
        rmsnorm_generation_calls(SMALL, 2, 2)


def norm_kernel(name="n", contract=_DEFAULT):
    if contract is _DEFAULT:
        contract = rmsnorm_bf16_contract.task_contract(3, 5)
    return KernelReference((f"{name}.c",), contract, ("-O2",))


def norm_binding():
    return {
        site: [BindingEntry(norm_kernel(site), "every")] for site in RMSNORM_CALL_SITES
    }


def run_norm(binding=None, **settings):
    arguments = {"dtype": "bf16", "prompt_length": 3, "generation_length": 4}
    arguments.update(settings)
    binding = norm_binding() if binding is None else binding
    return check_rmsnorm(SMALL, binding, **arguments)


def expected_norm_calls(binding, rows):
    return tuple(
        (site, (r, 8), binding[site][0].kernel)
        for site in RMSNORM_CALL_SITES
        for r in rows
    )


def test_check_rmsnorm_every_binding_is_ok():
    binding = norm_binding()
    result = run_norm(binding)
    assert result == BindingCheck(True, (), expected_norm_calls(binding, (1, 3)))
    assert isinstance(result, BindingCheck)


def test_check_rmsnorm_listed_shapes_cover_exactly():
    binding = {
        site: [BindingEntry(norm_kernel(site), norm_shapes((1, 3)))]
        for site in RMSNORM_CALL_SITES
    }
    result = run_norm(binding)
    assert result.ok
    assert result.calls == expected_norm_calls(binding, (1, 3))


def test_check_rmsnorm_listed_shape_other_than_the_spec_own():
    spec_own = rmsnorm_bf16_contract.task_contract(512, 2048)
    binding = {
        site: [BindingEntry(norm_kernel(site, spec_own), norm_shapes((1, 3, 7)))]
        for site in RMSNORM_CALL_SITES
    }
    result = run_norm(binding)
    assert result.ok
    assert result.calls == expected_norm_calls(binding, (1, 3))


def test_check_rmsnorm_several_entries_disjoint_shapes():
    binding = norm_binding()
    decode = norm_kernel("decode")
    prefill = norm_kernel("prefill")
    binding["ffn_norm"] = (
        BindingEntry(decode, norm_shapes((1,))),
        BindingEntry(prefill, norm_shapes((3, 9))),
    )
    result = run_norm(binding)
    assert result.ok
    assert [call[0] for call in result.calls] == [
        site for site in RMSNORM_CALL_SITES for _ in (1, 3)
    ]
    ffn = [call for call in result.calls if call[0] == "ffn_norm"]
    assert ffn == [("ffn_norm", (1, 8), decode), ("ffn_norm", (3, 8), prefill)]


def test_check_rmsnorm_generation_length_one():
    result = run_norm(generation_length=1)
    assert result.ok
    assert [call[1] for call in result.calls] == [(3, 8)] * len(RMSNORM_CALL_SITES)


def test_check_rmsnorm_accepts_path_sources():
    binding = norm_binding()
    contract = rmsnorm_bf16_contract.task_contract(1, 1)
    reference = KernelReference((Path("a.c"), "b.c"), contract, ())
    binding["norm"] = [BindingEntry(reference, "every")]
    assert run_norm(binding).ok


@pytest.mark.parametrize("unknown", ["fp32", "fp16", "int8"])
def test_check_rmsnorm_unknown_dtype_is_invalid_input(unknown):
    reason = f"dtype: no rmsnorm contract is known at the dtype {unknown!r}"
    assert run_norm(dtype=unknown) == BindingCheck(False, invalid(reason), ())
    assert unknown in reason and "rmsnorm" in reason


@pytest.mark.parametrize("unknown", ["fp32", "fp16"])
def test_check_rmsnorm_unknown_dtype_gives_no_unfit_and_no_kernel(unknown):
    reason = f"dtype: no rmsnorm contract is known at the dtype {unknown!r}"
    binding = norm_binding()
    binding["attention_norm"] = [BindingEntry(norm_kernel(contract={}), "every")]
    del binding["ffn_norm"]
    binding["norm"] = [BindingEntry(norm_kernel(), norm_shapes((3,)))]
    assert run_norm(binding, dtype=unknown) == BindingCheck(False, invalid(reason), ())


def test_check_rmsnorm_invalid_lengths():
    assert run_norm(prompt_length=0).outcomes == invalid(
        "prompt_length: must be from 1 to 2**53 - 1, got 0"
    )
    assert run_norm(generation_length=MAX_INTEGER + 1).outcomes == invalid(
        f"generation_length: must be from 1 to 2**53 - 1, got {MAX_INTEGER + 1}"
    )
    assert run_norm(prompt_length=-2).calls == ()


def test_check_rmsnorm_invalid_input_order_and_no_shape_check():
    binding = norm_binding()
    del binding["ffn_norm"]
    binding["norm"] = [BindingEntry(norm_kernel(contract=None), "every")]
    result = run_norm(binding, prompt_length=0, generation_length=-1)
    assert [(o.kind, o.call_site) for o in result.outcomes] == [
        ("invalid_input", None),
        ("invalid_input", None),
        ("kernel_unfit", "norm"),
    ]
    assert result.outcomes[0].reason.startswith("prompt_length:")
    assert result.outcomes[1].reason.startswith("generation_length:")
    assert result.calls == ()
    result = run_norm(binding, dtype="fp16", prompt_length=0, generation_length=0)
    assert [o.reason.split(":")[0] for o in result.outcomes] == [
        "dtype",
        "prompt_length",
        "generation_length",
    ]
    assert {o.kind for o in result.outcomes} == {"invalid_input"}


def test_check_rmsnorm_missing_call_site():
    binding = norm_binding()
    del binding["attention_norm"]
    result = run_norm(binding)
    assert result == BindingCheck(
        False,
        tuple(
            Outcome(
                "no_kernel",
                "attention_norm",
                shape,
                "no entry of the binding covers the shape",
            )
            for shape in norm_shapes((1, 3))
        ),
        (),
    )


def test_check_rmsnorm_unlisted_shape():
    binding = norm_binding()
    binding["norm"] = [BindingEntry(norm_kernel(), norm_shapes((3,)))]
    result = run_norm(binding)
    assert [(o.kind, o.call_site, o.shape) for o in result.outcomes] == [
        ("no_kernel", "norm", (1, 8))
    ]
    assert run_norm({}).outcomes == tuple(
        Outcome("no_kernel", site, shape, "no entry of the binding covers the shape")
        for site in RMSNORM_CALL_SITES
        for shape in norm_shapes((1, 3))
    )


def norm_unfit_reason(contract):
    binding = norm_binding()
    binding["ffn_norm"] = [BindingEntry(norm_kernel(contract=contract), "every")]
    result = run_norm(binding)
    assert not result.ok and result.calls == ()
    (outcome,) = result.outcomes
    assert outcome.kind == "kernel_unfit"
    assert outcome.call_site == "ffn_norm" and outcome.shape is None
    assert outcome.reason.startswith("entry 0: ")
    return outcome.reason


def good_norm_contract():
    return rmsnorm_bf16_contract.task_contract(2, 4)


@pytest.mark.parametrize("dtype", ["bf16", "fp32"])
def test_check_rmsnorm_gemm_kernel_is_unfit(dtype):
    reason = norm_unfit_reason(CONTRACTS[dtype].task_contract(2, 4, 4))
    assert reason == (
        "entry 0: contract.prototype is not that of the bf16 rmsnorm contract"
    )


def test_check_rmsnorm_unfit_wrong_prototype():
    contract = good_norm_contract()
    contract["prototype"] = contract["prototype"].replace("float eps, ", "")
    assert norm_unfit_reason(contract) == (
        "entry 0: contract.prototype is not that of the bf16 rmsnorm contract"
    )


def test_check_rmsnorm_unfit_wrong_language():
    contract = good_norm_contract()
    contract["language"] = "cpp"
    assert norm_unfit_reason(contract) == (
        "entry 0: contract.language is not that of the bf16 rmsnorm contract"
    )


@pytest.mark.parametrize(
    ("index", "member", "value"),
    [
        (0, "name", "a"),
        (1, "name", "x"),
        (1, "role", "output"),
        (2, "role", "input"),
        (0, "dtype", "fp32"),
        (2, "dtype", "fp16"),
        (1, "dtype", None),
    ],
)
def test_check_rmsnorm_unfit_wrong_operand(index, member, value):
    contract = good_norm_contract()
    contract["operands"][index][member] = value
    assert norm_unfit_reason(contract) == (
        f"entry 0: contract.operands[{index}].{member} is not that of the bf16 "
        "rmsnorm contract"
    )


@pytest.mark.parametrize("contract", [None, "c", ["language"], 3])
def test_check_rmsnorm_unfit_non_mapping(contract):
    assert "not a mapping" in norm_unfit_reason(contract)


@pytest.mark.parametrize("member", ["language", "prototype", "operands"])
def test_check_rmsnorm_unfit_missing_member(member):
    contract = good_norm_contract()
    del contract[member]
    assert repr(member) in norm_unfit_reason(contract)


def test_check_rmsnorm_unfit_operands_forms():
    contract = good_norm_contract()
    contract["operands"] = "xwy"
    assert "not a sequence" in norm_unfit_reason(contract)
    contract["operands"] = good_norm_contract()["operands"][:2]
    assert "2 entries, not 3" in norm_unfit_reason(contract)
    contract["operands"] = [*good_norm_contract()["operands"], {}]
    assert "4 entries, not 3" in norm_unfit_reason(contract)
    contract["operands"] = [*good_norm_contract()["operands"][:2], None]
    assert "operands[2] is not a mapping" in norm_unfit_reason(contract)
    contract["operands"] = good_norm_contract()["operands"]
    del contract["operands"][1]["role"]
    assert "operands[1] lacks the member 'role'" in norm_unfit_reason(contract)


def test_check_rmsnorm_fit_ignores_operand_shapes_and_extra_members():
    contract = good_norm_contract()
    contract["operands"][1]["shape"] = [99, 99]
    contract["operands"][2]["note"] = "x"
    contract["note"] = "x"
    binding = norm_binding()
    binding["ffn_norm"] = [BindingEntry(norm_kernel(contract=contract), "every")]
    assert run_norm(binding).ok


def test_check_rmsnorm_reference_comes_from_the_contract_module(monkeypatch):
    binding = norm_binding()
    changed = good_norm_contract()
    changed["prototype"] = "void other(void);"
    monkeypatch.setattr(
        rmsnorm_bf16_contract, "task_contract", lambda m, n: copy.deepcopy(changed)
    )
    result = run_norm(binding)
    assert [(o.kind, o.call_site) for o in result.outcomes] == [
        ("kernel_unfit", site) for site in RMSNORM_CALL_SITES
    ]
    binding = {
        site: [BindingEntry(norm_kernel(contract=changed), "every")]
        for site in RMSNORM_CALL_SITES
    }
    assert run_norm(binding).ok


def test_check_rmsnorm_outcome_order():
    binding = norm_binding()
    binding["attention_norm"] = [
        BindingEntry(norm_kernel(), norm_shapes((3,))),
        BindingEntry(norm_kernel(contract={}), norm_shapes((7,))),
    ]
    del binding["ffn_norm"]
    binding["norm"] = [BindingEntry(norm_kernel(contract=None), "every")]
    result = run_norm(binding)
    assert [(o.kind, o.call_site, o.shape) for o in result.outcomes] == [
        ("kernel_unfit", "attention_norm", None),
        ("no_kernel", "attention_norm", (1, 8)),
        ("no_kernel", "ffn_norm", (1, 8)),
        ("no_kernel", "ffn_norm", (3, 8)),
        ("kernel_unfit", "norm", None),
    ]
    assert result.outcomes[0].reason.startswith("entry 1: ")


def test_check_rmsnorm_arguments_are_keyword_only_without_default():
    for name in ("dtype", "prompt_length", "generation_length"):
        parameter = inspect.signature(check_rmsnorm).parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    with pytest.raises(TypeError, match="dtype"):
        check_rmsnorm(SMALL, norm_binding(), prompt_length=1, generation_length=1)


@pytest.mark.parametrize(
    ("name", "value", "kind"),
    [
        ("dtype", None, TypeError),
        ("dtype", b"bf16", TypeError),
        ("dtype", True, TypeError),
        ("dtype", "BF16", ValueError),
        ("dtype", "", ValueError),
        ("dtype", "a" * 33, ValueError),
        ("prompt_length", True, TypeError),
        ("prompt_length", 3.0, TypeError),
        ("prompt_length", None, TypeError),
        ("generation_length", False, TypeError),
        ("generation_length", "4", TypeError),
    ],
)
def test_check_rmsnorm_argument_errors(name, value, kind):
    raises(kind, name, run_norm, **{name: value})


def test_check_rmsnorm_argument_order():
    raises(
        TypeError,
        "dimensions",
        check_rmsnorm,
        tuple(SMALL),
        None,
        dtype=None,
        prompt_length=None,
        generation_length=None,
    )
    raises(
        ValueError,
        "dimensions",
        check_rmsnorm,
        SMALL._replace(hidden=0),
        norm_binding(),
        dtype="bf16",
        prompt_length=1,
        generation_length=1,
    )
    raises(ValueError, "dtype", run_norm, None, dtype="BF16", prompt_length=None)
    raises(
        TypeError,
        "prompt_length",
        run_norm,
        [],
        prompt_length=None,
        generation_length=None,
    )
    raises(TypeError, "generation_length", run_norm, [], generation_length=None)
    raises(TypeError, "binding", run_norm, [], prompt_length=0, dtype="fp32")


def bad_norm_binding(kind, binding):
    return raises(kind, "binding", run_norm, binding)


def with_norm_entry(site, *entries):
    binding = norm_binding()
    binding[site] = list(entries)
    return binding


def test_check_rmsnorm_binding_not_mapping():
    bad_norm_binding(TypeError, [("norm", [])])
    raises(
        TypeError,
        "binding",
        check_rmsnorm,
        SMALL,
        None,
        dtype="bf16",
        prompt_length=1,
        generation_length=1,
    )


@pytest.mark.parametrize("key", [*CALL_SITES, "rmsnorm", "NORM", 1, None])
def test_check_rmsnorm_binding_unknown_key(key):
    binding = norm_binding()
    binding[key] = [BindingEntry(norm_kernel(), "every")]
    error = bad_norm_binding(ValueError, binding)
    assert str(RMSNORM_CALL_SITES) in str(error)


def test_check_rmsnorm_binding_entries_forms():
    binding = norm_binding()
    for entries, kind in (
        (BindingEntry(norm_kernel(), "every"), TypeError),
        ("every", TypeError),
        ([], ValueError),
        (None, TypeError),
        ([(norm_kernel(), "every")], TypeError),
        ([BindingEntry(("n.c",), "every")], TypeError),
    ):
        binding["norm"] = entries
        bad_norm_binding(kind, binding)


@pytest.mark.parametrize(
    ("reference", "kind"),
    [
        (KernelReference([Path("n.c")], {}, ()), TypeError),
        (KernelReference((), {}, ()), ValueError),
        (KernelReference((b"n.c",), {}, ()), TypeError),
        (KernelReference(("n.c",), {}, ["-O2"]), TypeError),
        (KernelReference(("n.c",), {}, ("-O2", 3)), TypeError),
    ],
)
def test_check_rmsnorm_binding_kernel_reference_refused(reference, kind):
    bad_norm_binding(kind, with_norm_entry("norm", BindingEntry(reference, "every")))


@pytest.mark.parametrize(
    ("shapes", "kind"),
    [
        ("all", ValueError),
        ([(1, 8)], TypeError),
        ((), ValueError),
        (None, TypeError),
        (([1, 8],), TypeError),
        (((1, 8, 8),), ValueError),
        (((1,),), ValueError),
        (((0, 8),), ValueError),
        (((1, MAX_INTEGER + 1),), ValueError),
        (((True, 8),), TypeError),
        (((1, 8.0),), TypeError),
    ],
)
def test_check_rmsnorm_binding_shapes_refused(shapes, kind):
    bad_norm_binding(kind, with_norm_entry("norm", BindingEntry(norm_kernel(), shapes)))


def test_check_rmsnorm_binding_triple_shape_message():
    error = bad_norm_binding(
        ValueError, with_norm_entry("norm", BindingEntry(norm_kernel(), ((1, 8, 8),)))
    )
    assert str(error) == "norm: a shape has 3 members, not 2"
    error = bad_norm_binding(
        TypeError, with_norm_entry("norm", BindingEntry(norm_kernel(), ([1, 8],)))
    )
    assert str(error) == "norm: a shape is not a tuple (m, n)"


def test_check_rmsnorm_binding_overlapping_entries():
    error = bad_norm_binding(
        ValueError,
        with_norm_entry(
            "ffn_norm",
            BindingEntry(norm_kernel(), ((1, 8), (3, 8))),
            BindingEntry(norm_kernel(), ((3, 8),)),
        ),
    )
    assert "(3, 8)" in str(error)


def test_check_rmsnorm_binding_every_beside_another_entry():
    for entries in (
        (BindingEntry(norm_kernel(), ((5, 8),)), BindingEntry(norm_kernel(), "every")),
        (BindingEntry(norm_kernel(), "every"), BindingEntry(norm_kernel(), "every")),
    ):
        bad_norm_binding(ValueError, with_norm_entry("norm", *entries))


def test_check_rmsnorm_malformed_binding_refused_even_with_invalid_input():
    binding = with_norm_entry(
        "norm",
        BindingEntry(norm_kernel(), "every"),
        BindingEntry(norm_kernel(), "every"),
    )
    raises(ValueError, "binding", run_norm, binding, prompt_length=0, dtype="fp32")


def test_check_rmsnorm_does_not_modify_arguments():
    binding = norm_binding()
    binding["ffn_norm"] = [
        BindingEntry(norm_kernel(), norm_shapes((1,))),
        BindingEntry(norm_kernel(), norm_shapes((3,))),
    ]
    binding["norm"] = [BindingEntry(norm_kernel(contract={"language": "c"}), "every")]
    before = copy.deepcopy(binding)
    for dtype in ("bf16", "fp32"):
        run_norm(binding, dtype=dtype)
    run_norm(binding, prompt_length=0)
    assert binding == before


def f32(bits):
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def test_rmsnorm_eps_of_1e_05_is_the_contract_eps():
    eps = rmsnorm_eps(1e-05)
    assert eps == rmsnorm_bf16_contract.EPS
    assert type(eps) is float
    assert struct.unpack("<I", struct.pack("<f", eps))[0] == 0x3727C5AC


@pytest.mark.parametrize(
    "bits", [0x3727C5AC, 0x00000001, 0x00800000, 0x3F800000, 0x7F7FFFFF]
)
def test_rmsnorm_eps_of_a_binary32_value_is_unchanged(bits):
    value = f32(bits)
    assert rmsnorm_eps(value) == value


def test_rmsnorm_eps_rounds_ties_to_even():
    even, odd, next_even = f32(0x3727C5AC), f32(0x3727C5AD), f32(0x3727C5AE)
    assert rmsnorm_eps((even + odd) / 2) == even
    assert rmsnorm_eps((odd + next_even) / 2) == next_even
    assert rmsnorm_eps(math.nextafter((even + odd) / 2, 1.0)) == odd


def test_rmsnorm_eps_rounds_to_nearest_near_the_bounds():
    smallest = f32(0x00000001)
    assert rmsnorm_eps(smallest * 0.75) == smallest
    largest = f32(0x7F7FFFFF)
    assert rmsnorm_eps(math.nextafter(2.0**128 - 2.0**103, 0.0)) == largest


@pytest.mark.parametrize("value", [True, False, 1, 0, "1e-05", None, [1e-05]])
def test_rmsnorm_eps_refuses_types(value):
    raises(TypeError, "eps", rmsnorm_eps, value)


@pytest.mark.parametrize(
    "value",
    [
        0.0,
        -0.0,
        -1e-05,
        math.inf,
        -math.inf,
        math.nan,
        2.0**-150,
        2.0**-151,
        5e-324,
        2.0**128 - 2.0**103,
        1e300,
    ],
)
def test_rmsnorm_eps_refuses_values(value):
    raises(ValueError, "eps", rmsnorm_eps, value)
