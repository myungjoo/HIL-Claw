import copy
import inspect
import math
import struct
from pathlib import Path

import pytest

from hilclaw import (
    elementwise_add_bf16_contract,
    gemm_bf16_contract,
    gemm_contract,
    rmsnorm_bf16_contract,
    rope_bf16_contract,
    sdpa_kv_cache_bf16_contract,
    swiglu_bf16_contract,
)
from hilclaw.keys import MAX_INTEGER
from hilclaw.model_binding import (
    CALL_SITES,
    DTYPES,
    ELEMENTWISE_ADD_CALL_SITES,
    ELEMENTWISE_ADD_DTYPES,
    RMSNORM_CALL_SITES,
    RMSNORM_DTYPES,
    ROPE_CALL_SITES,
    ROPE_DTYPES,
    SDPA_CALL_SITES,
    SDPA_DTYPES,
    SWIGLU_CALL_SITES,
    SWIGLU_DTYPES,
    BindingCheck,
    BindingEntry,
    KernelReference,
    ModelDimensions,
    Outcome,
    check,
    check_dimensions,
    check_elementwise_add,
    check_rmsnorm,
    check_rope,
    check_sdpa,
    check_swiglu,
    elementwise_add_generation_calls,
    elementwise_add_shape,
    gemm_shape,
    generation_calls,
    rmsnorm_eps,
    rmsnorm_generation_calls,
    rmsnorm_shape,
    rope_generation_calls,
    rope_shape,
    sdpa_generation_calls,
    sdpa_shape,
    swiglu_generation_calls,
    swiglu_shape,
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
    assert KernelReference._fields == ("sources", "contract", "flags", "headers")
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


class _Headers(tuple):
    pass


@pytest.mark.parametrize(
    "headers",
    [
        [Path("o.h")],
        (b"o.h",),
        ("o.h", 3),
        (None,),
        _Headers(("o.h",)),
        "o.h",
        None,
    ],
)
def test_binding_kernel_headers_refused(headers):
    reference = KernelReference(("o.c",), {}, (), headers)
    error = bad_binding(TypeError, with_entry("o", BindingEntry(reference, "every")))
    assert str(error).startswith("o: ")
    assert "header" in str(error)


def test_kernel_reference_headers_default_to_empty():
    reference = KernelReference(("o.c",), {}, ())
    assert reference.headers == ()
    assert KernelReference._field_defaults == {"headers": ()}


def test_check_accepts_kernel_headers():
    binding = every_binding()
    binding["o"] = (
        BindingEntry(
            KernelReference(
                ("o.c",),
                gemm_contract.task_contract(1, 1, 1),
                (),
                (Path("o.h"), "p.h"),
            ),
            "every",
        ),
    )
    assert run(binding).ok
    binding["o"] = (
        BindingEntry(
            KernelReference(("o.c",), gemm_contract.task_contract(1, 1, 1), (), ()),
            "every",
        ),
    )
    assert run(binding).ok


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


def test_elementwise_add_call_sites():
    assert ELEMENTWISE_ADD_CALL_SITES == ("attention_residual", "ffn_residual")
    assert not set(ELEMENTWISE_ADD_CALL_SITES) & set(CALL_SITES)
    assert not set(ELEMENTWISE_ADD_CALL_SITES) & set(RMSNORM_CALL_SITES)


def test_elementwise_add_dtypes():
    assert ELEMENTWISE_ADD_DTYPES == ("bf16",)
    assert ELEMENTWISE_ADD_DTYPES == (elementwise_add_bf16_contract.DTYPE,)


@pytest.mark.parametrize("site", ELEMENTWISE_ADD_CALL_SITES)
@pytest.mark.parametrize("rows", [1, 7, MAX_INTEGER])
def test_elementwise_add_shape_small(site, rows):
    assert elementwise_add_shape(SMALL, site, rows) == (rows, 8)


def test_elementwise_add_shape_at_llama_values_is_the_contract_table():
    llama = ModelDimensions(2048, 8192, 128256, 16, 32, 8, 64)
    for site in ELEMENTWISE_ADD_CALL_SITES:
        shapes = tuple(elementwise_add_shape(llama, site, m) for m in (1, 32, 512))
        assert shapes == elementwise_add_bf16_contract.SHAPES


@pytest.mark.parametrize(
    "site",
    ["o", "down", "attention_norm", "ffn_norm", "residual", "", None, 3],
)
def test_elementwise_add_shape_unknown_call_site(site):
    error = raises(ValueError, "call_site", elementwise_add_shape, SMALL, site, 1)
    assert str(ELEMENTWISE_ADD_CALL_SITES) in str(error)


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
def test_elementwise_add_shape_bad_rows(rows, kind):
    raises(kind, "rows", elementwise_add_shape, SMALL, "ffn_residual", rows)


def test_elementwise_add_shape_argument_order():
    raises(
        ValueError, "dimensions", elementwise_add_shape, SMALL._replace(heads=3), "x", 0
    )
    raises(TypeError, "dimensions", elementwise_add_shape, None, "ffn_residual", 1)
    raises(ValueError, "call_site", elementwise_add_shape, SMALL, "norm", 0)


def add_shapes(rows):
    return tuple((r, 8) for r in rows)


def test_elementwise_add_generation_calls_prefill_and_decode():
    calls = elementwise_add_generation_calls(
        SMALL, prompt_length=5, generation_length=3
    )
    assert calls == tuple(
        (site, add_shapes((1, 5))) for site in ELEMENTWISE_ADD_CALL_SITES
    )


def test_elementwise_add_generation_calls_one_token_has_no_decode():
    calls = elementwise_add_generation_calls(
        SMALL, prompt_length=5, generation_length=1
    )
    assert calls == tuple(
        (site, add_shapes((5,))) for site in ELEMENTWISE_ADD_CALL_SITES
    )


def test_elementwise_add_generation_calls_prompt_of_one_row():
    calls = elementwise_add_generation_calls(
        SMALL, prompt_length=1, generation_length=4
    )
    assert calls == tuple(
        (site, add_shapes((1,))) for site in ELEMENTWISE_ADD_CALL_SITES
    )


def test_elementwise_add_generation_calls_rows_match_the_rmsnorm_passes():
    for prompt_length, generation_length in ((6, 2), (1, 1), (9, 1), (4, 7)):
        lengths = {
            "prompt_length": prompt_length,
            "generation_length": generation_length,
        }
        norm = dict(rmsnorm_generation_calls(SMALL, **lengths))
        add = dict(elementwise_add_generation_calls(SMALL, **lengths))
        for site in ELEMENTWISE_ADD_CALL_SITES:
            assert add[site] == norm["attention_norm"]


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
def test_elementwise_add_generation_calls_refuses(name, value, kind):
    arguments = {"prompt_length": 2, "generation_length": 2}
    arguments[name] = value
    raises(kind, name, elementwise_add_generation_calls, SMALL, **arguments)


def test_elementwise_add_generation_calls_argument_order():
    raises(
        TypeError,
        "dimensions",
        elementwise_add_generation_calls,
        None,
        prompt_length=0,
        generation_length=0,
    )
    raises(
        ValueError,
        "prompt_length",
        elementwise_add_generation_calls,
        SMALL,
        prompt_length=0,
        generation_length=None,
    )


def test_elementwise_add_generation_calls_lengths_are_keyword_only():
    with pytest.raises(TypeError):
        elementwise_add_generation_calls(SMALL, 2, 2)


def add_kernel(name="r", contract=_DEFAULT):
    if contract is _DEFAULT:
        contract = elementwise_add_bf16_contract.task_contract(3, 5)
    return KernelReference((f"{name}.c",), contract, ("-O2",))


def add_binding():
    return {
        site: [BindingEntry(add_kernel(site), "every")]
        for site in ELEMENTWISE_ADD_CALL_SITES
    }


def run_add(binding=None, **settings):
    arguments = {"dtype": "bf16", "prompt_length": 3, "generation_length": 4}
    arguments.update(settings)
    binding = add_binding() if binding is None else binding
    return check_elementwise_add(SMALL, binding, **arguments)


def expected_add_calls(binding, rows):
    return tuple(
        (site, (r, 8), binding[site][0].kernel)
        for site in ELEMENTWISE_ADD_CALL_SITES
        for r in rows
    )


def test_check_elementwise_add_every_binding_is_ok():
    binding = add_binding()
    result = run_add(binding)
    assert result == BindingCheck(True, (), expected_add_calls(binding, (1, 3)))
    assert isinstance(result, BindingCheck)


def test_check_elementwise_add_listed_shapes_cover_exactly():
    binding = {
        site: [BindingEntry(add_kernel(site), add_shapes((1, 3)))]
        for site in ELEMENTWISE_ADD_CALL_SITES
    }
    result = run_add(binding)
    assert result.ok
    assert result.calls == expected_add_calls(binding, (1, 3))


def test_check_elementwise_add_listed_shape_other_than_the_spec_own():
    spec_own = elementwise_add_bf16_contract.task_contract(512, 2048)
    binding = {
        site: [BindingEntry(add_kernel(site, spec_own), add_shapes((1, 3, 7)))]
        for site in ELEMENTWISE_ADD_CALL_SITES
    }
    result = run_add(binding)
    assert result.ok
    assert result.calls == expected_add_calls(binding, (1, 3))


def test_check_elementwise_add_several_entries_disjoint_shapes():
    binding = add_binding()
    decode = add_kernel("decode")
    prefill = add_kernel("prefill")
    binding["attention_residual"] = (
        BindingEntry(decode, add_shapes((1,))),
        BindingEntry(prefill, add_shapes((3, 9))),
    )
    result = run_add(binding)
    assert result.ok
    assert [call[0] for call in result.calls] == [
        "attention_residual",
        "attention_residual",
        "ffn_residual",
        "ffn_residual",
    ]
    assert result.calls[:2] == (
        ("attention_residual", (1, 8), decode),
        ("attention_residual", (3, 8), prefill),
    )


def test_check_elementwise_add_generation_length_one():
    result = run_add(generation_length=1)
    assert result.ok
    assert [call[1] for call in result.calls] == [(3, 8)] * len(
        ELEMENTWISE_ADD_CALL_SITES
    )


def test_check_elementwise_add_accepts_path_sources():
    binding = add_binding()
    contract = elementwise_add_bf16_contract.task_contract(1, 1)
    reference = KernelReference((Path("a.c"), "b.c"), contract, ())
    binding["ffn_residual"] = [BindingEntry(reference, "every")]
    assert run_add(binding).ok


@pytest.mark.parametrize("unknown", ["fp32", "fp16", "int8"])
def test_check_elementwise_add_unknown_dtype_is_invalid_input(unknown):
    reason = f"dtype: no elementwise_add contract is known at the dtype {unknown!r}"
    assert run_add(dtype=unknown) == BindingCheck(False, invalid(reason), ())
    assert unknown in reason and "elementwise_add" in reason


@pytest.mark.parametrize("unknown", ["fp32", "fp16"])
def test_check_elementwise_add_unknown_dtype_gives_no_unfit_and_no_kernel(unknown):
    reason = f"dtype: no elementwise_add contract is known at the dtype {unknown!r}"
    binding = {
        "attention_residual": [BindingEntry(add_kernel(contract={}), add_shapes((3,)))]
    }
    assert run_add(binding, dtype=unknown) == BindingCheck(False, invalid(reason), ())


def test_check_elementwise_add_invalid_lengths():
    assert run_add(prompt_length=0).outcomes == invalid(
        "prompt_length: must be from 1 to 2**53 - 1, got 0"
    )
    assert run_add(generation_length=MAX_INTEGER + 1).outcomes == invalid(
        f"generation_length: must be from 1 to 2**53 - 1, got {MAX_INTEGER + 1}"
    )
    assert run_add(prompt_length=-2).calls == ()


def test_check_elementwise_add_invalid_input_order_and_no_shape_check():
    binding = {"ffn_residual": [BindingEntry(add_kernel(contract=None), "every")]}
    result = run_add(binding, prompt_length=0, generation_length=-1)
    assert [(o.kind, o.call_site) for o in result.outcomes] == [
        ("invalid_input", None),
        ("invalid_input", None),
        ("kernel_unfit", "ffn_residual"),
    ]
    assert result.outcomes[0].reason.startswith("prompt_length:")
    assert result.outcomes[1].reason.startswith("generation_length:")
    assert result.calls == ()
    result = run_add(binding, dtype="fp32", prompt_length=0, generation_length=0)
    assert [o.reason.split(":")[0] for o in result.outcomes] == [
        "dtype",
        "prompt_length",
        "generation_length",
    ]
    assert {o.kind for o in result.outcomes} == {"invalid_input"}


def test_check_elementwise_add_missing_call_site():
    binding = add_binding()
    del binding["ffn_residual"]
    assert run_add(binding) == BindingCheck(
        False,
        tuple(
            Outcome(
                "no_kernel",
                "ffn_residual",
                shape,
                "no entry of the binding covers the shape",
            )
            for shape in add_shapes((1, 3))
        ),
        (),
    )


def test_check_elementwise_add_unlisted_shape():
    binding = add_binding()
    binding["attention_residual"] = [BindingEntry(add_kernel(), add_shapes((1, 7)))]
    result = run_add(binding)
    assert [(o.kind, o.call_site, o.shape) for o in result.outcomes] == [
        ("no_kernel", "attention_residual", (3, 8))
    ]
    assert run_add({}).outcomes == tuple(
        Outcome("no_kernel", site, shape, "no entry of the binding covers the shape")
        for site in ELEMENTWISE_ADD_CALL_SITES
        for shape in add_shapes((1, 3))
    )


def add_unfit_reason(contract):
    binding = add_binding()
    binding["ffn_residual"] = [BindingEntry(add_kernel(contract=contract), "every")]
    result = run_add(binding)
    assert not result.ok and result.calls == ()
    (outcome,) = result.outcomes
    assert outcome.kind == "kernel_unfit"
    assert outcome.call_site == "ffn_residual" and outcome.shape is None
    assert outcome.reason.startswith("entry 0: ")
    return outcome.reason


def good_add_contract():
    return elementwise_add_bf16_contract.task_contract(2, 4)


ADD_PROTOTYPE_UNFIT = (
    "entry 0: contract.prototype is not that of the bf16 elementwise_add contract"
)


def test_check_elementwise_add_rmsnorm_kernel_is_unfit():
    contract = rmsnorm_bf16_contract.task_contract(2, 4)
    assert add_unfit_reason(contract) == ADD_PROTOTYPE_UNFIT


@pytest.mark.parametrize("dtype", ["bf16", "fp32"])
def test_check_elementwise_add_gemm_kernel_is_unfit(dtype):
    contract = CONTRACTS[dtype].task_contract(2, 4, 4)
    assert add_unfit_reason(contract) == ADD_PROTOTYPE_UNFIT


def test_check_elementwise_add_unfit_wrong_prototype():
    contract = good_add_contract()
    contract["prototype"] = contract["prototype"].replace("restrict c", "c")
    assert add_unfit_reason(contract) == ADD_PROTOTYPE_UNFIT


def test_check_elementwise_add_unfit_wrong_language():
    contract = good_add_contract()
    contract["language"] = "cpp"
    assert add_unfit_reason(contract) == (
        "entry 0: contract.language is not that of the bf16 elementwise_add contract"
    )


@pytest.mark.parametrize(
    ("index", "member", "value"),
    [
        (0, "name", "b"),
        (1, "name", "a"),
        (2, "name", "out"),
        (1, "role", "output"),
        (2, "role", "input"),
        (0, "dtype", "fp32"),
        (2, "dtype", "fp16"),
        (1, "dtype", None),
    ],
)
def test_check_elementwise_add_unfit_wrong_operand(index, member, value):
    contract = good_add_contract()
    contract["operands"][index][member] = value
    assert add_unfit_reason(contract) == (
        f"entry 0: contract.operands[{index}].{member} is not that of the bf16 "
        "elementwise_add contract"
    )


@pytest.mark.parametrize("contract", [None, "c", ["language"], 3])
def test_check_elementwise_add_unfit_non_mapping(contract):
    assert "not a mapping" in add_unfit_reason(contract)


@pytest.mark.parametrize("member", ["language", "prototype", "operands"])
def test_check_elementwise_add_unfit_missing_member(member):
    contract = good_add_contract()
    del contract[member]
    assert repr(member) in add_unfit_reason(contract)


def test_check_elementwise_add_unfit_operands_forms():
    contract = good_add_contract()
    contract["operands"] = "abc"
    assert "not a sequence" in add_unfit_reason(contract)
    contract["operands"] = good_add_contract()["operands"][:2]
    assert "2 entries, not 3" in add_unfit_reason(contract)
    contract["operands"] = [*good_add_contract()["operands"], {}]
    assert "4 entries, not 3" in add_unfit_reason(contract)
    contract["operands"] = [*good_add_contract()["operands"][:2], None]
    assert "operands[2] is not a mapping" in add_unfit_reason(contract)
    contract["operands"] = good_add_contract()["operands"]
    del contract["operands"][0]["name"]
    assert "operands[0] lacks the member 'name'" in add_unfit_reason(contract)


def test_check_elementwise_add_fit_ignores_operand_shapes_and_extra_members():
    contract = good_add_contract()
    contract["operands"][0]["shape"] = [99, 99]
    contract["operands"][2]["note"] = "x"
    contract["note"] = "x"
    binding = add_binding()
    binding["ffn_residual"] = [BindingEntry(add_kernel(contract=contract), "every")]
    assert run_add(binding).ok


def test_check_elementwise_add_reference_comes_from_the_contract_module(monkeypatch):
    binding = add_binding()
    changed = good_add_contract()
    changed["prototype"] = "void other(void);"
    monkeypatch.setattr(
        elementwise_add_bf16_contract,
        "task_contract",
        lambda m, n: copy.deepcopy(changed),
    )
    result = run_add(binding)
    assert [(o.kind, o.call_site) for o in result.outcomes] == [
        ("kernel_unfit", site) for site in ELEMENTWISE_ADD_CALL_SITES
    ]
    binding = {
        site: [BindingEntry(add_kernel(contract=changed), "every")]
        for site in ELEMENTWISE_ADD_CALL_SITES
    }
    assert run_add(binding).ok
    assert run_norm().ok


def test_check_elementwise_add_outcome_order():
    binding = {
        "attention_residual": [
            BindingEntry(add_kernel(), add_shapes((3,))),
            BindingEntry(add_kernel(contract={}), add_shapes((7,))),
        ],
        "ffn_residual": [BindingEntry(add_kernel(contract=None), add_shapes((1,)))],
    }
    result = run_add(binding)
    assert [(o.kind, o.call_site, o.shape) for o in result.outcomes] == [
        ("kernel_unfit", "attention_residual", None),
        ("no_kernel", "attention_residual", (1, 8)),
        ("kernel_unfit", "ffn_residual", None),
        ("no_kernel", "ffn_residual", (3, 8)),
    ]
    assert result.outcomes[0].reason.startswith("entry 1: ")


def test_check_elementwise_add_arguments_are_keyword_only_without_default():
    parameters = inspect.signature(check_elementwise_add).parameters
    assert list(parameters) == [
        "dimensions",
        "binding",
        "dtype",
        "prompt_length",
        "generation_length",
    ]
    for name in ("dtype", "prompt_length", "generation_length"):
        assert parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
        assert parameters[name].default is inspect.Parameter.empty
    with pytest.raises(TypeError, match="dtype"):
        check_elementwise_add(
            SMALL, add_binding(), prompt_length=1, generation_length=1
        )


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
def test_check_elementwise_add_argument_errors(name, value, kind):
    raises(kind, name, run_add, **{name: value})


def test_check_elementwise_add_argument_order():
    raises(
        TypeError,
        "dimensions",
        check_elementwise_add,
        tuple(SMALL),
        None,
        dtype=None,
        prompt_length=None,
        generation_length=None,
    )
    raises(
        ValueError,
        "dimensions",
        check_elementwise_add,
        SMALL._replace(kv_heads=3),
        add_binding(),
        dtype="bf16",
        prompt_length=1,
        generation_length=1,
    )
    raises(ValueError, "dtype", run_add, None, dtype="Bf16", prompt_length=None)
    raises(
        TypeError,
        "prompt_length",
        run_add,
        [],
        prompt_length=None,
        generation_length=None,
    )
    raises(TypeError, "generation_length", run_add, [], generation_length=None)
    raises(TypeError, "binding", run_add, [], prompt_length=0, dtype="fp32")


def bad_add_binding(kind, binding):
    return raises(kind, "binding", run_add, binding)


def with_add_entry(site, *entries):
    binding = add_binding()
    binding[site] = list(entries)
    return binding


def test_check_elementwise_add_binding_not_mapping():
    bad_add_binding(TypeError, [("ffn_residual", [])])
    raises(
        TypeError,
        "binding",
        check_elementwise_add,
        SMALL,
        None,
        dtype="bf16",
        prompt_length=1,
        generation_length=1,
    )


@pytest.mark.parametrize(
    "key", [*CALL_SITES, *RMSNORM_CALL_SITES, "residual", "FFN_RESIDUAL", 1, None]
)
def test_check_elementwise_add_binding_unknown_key(key):
    binding = add_binding()
    binding[key] = [BindingEntry(add_kernel(), "every")]
    error = bad_add_binding(ValueError, binding)
    assert str(ELEMENTWISE_ADD_CALL_SITES) in str(error)


def test_check_elementwise_add_binding_entries_forms():
    binding = add_binding()
    for entries, kind in (
        (BindingEntry(add_kernel(), "every"), TypeError),
        ("every", TypeError),
        ([], ValueError),
        (None, TypeError),
        ([(add_kernel(), "every")], TypeError),
        ([BindingEntry(("r.c",), "every")], TypeError),
    ):
        binding["ffn_residual"] = entries
        bad_add_binding(kind, binding)


@pytest.mark.parametrize(
    ("reference", "kind"),
    [
        (KernelReference([Path("r.c")], {}, ()), TypeError),
        (KernelReference((), {}, ()), ValueError),
        (KernelReference((b"r.c",), {}, ()), TypeError),
        (KernelReference(("r.c",), {}, ["-O2"]), TypeError),
        (KernelReference(("r.c",), {}, ("-O2", 3)), TypeError),
    ],
)
def test_check_elementwise_add_binding_kernel_reference_refused(reference, kind):
    binding = with_add_entry("attention_residual", BindingEntry(reference, "every"))
    bad_add_binding(kind, binding)


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
def test_check_elementwise_add_binding_shapes_refused(shapes, kind):
    binding = with_add_entry("ffn_residual", BindingEntry(add_kernel(), shapes))
    bad_add_binding(kind, binding)


def test_check_elementwise_add_binding_triple_shape_message():
    error = bad_add_binding(
        ValueError,
        with_add_entry("ffn_residual", BindingEntry(add_kernel(), ((1, 8, 8),))),
    )
    assert str(error) == "ffn_residual: a shape has 3 members, not 2"
    error = bad_add_binding(
        TypeError,
        with_add_entry("ffn_residual", BindingEntry(add_kernel(), ([1, 8],))),
    )
    assert str(error) == "ffn_residual: a shape is not a tuple (m, n)"


def test_check_elementwise_add_binding_overlapping_entries():
    error = bad_add_binding(
        ValueError,
        with_add_entry(
            "attention_residual",
            BindingEntry(add_kernel(), ((1, 8), (3, 8))),
            BindingEntry(add_kernel(), ((3, 8),)),
        ),
    )
    assert str(error) == "attention_residual: two entries cover the shape (3, 8)"


def test_check_elementwise_add_binding_every_beside_another_entry():
    for entries in (
        (BindingEntry(add_kernel(), ((5, 8),)), BindingEntry(add_kernel(), "every")),
        (BindingEntry(add_kernel(), "every"), BindingEntry(add_kernel(), "every")),
    ):
        error = bad_add_binding(ValueError, with_add_entry("ffn_residual", *entries))
        assert "'every' entry overlaps" in str(error)


def test_check_elementwise_add_malformed_binding_refused_even_with_invalid_input():
    binding = with_add_entry(
        "ffn_residual",
        BindingEntry(add_kernel(), "every"),
        BindingEntry(add_kernel(), "every"),
    )
    raises(ValueError, "binding", run_add, binding, prompt_length=0, dtype="fp32")


def test_check_elementwise_add_does_not_modify_arguments():
    binding = add_binding()
    binding["attention_residual"] = [
        BindingEntry(add_kernel(), add_shapes((1,))),
        BindingEntry(add_kernel(), add_shapes((3,))),
    ]
    binding["ffn_residual"] = [
        BindingEntry(add_kernel(contract={"language": "c"}), "every")
    ]
    before = copy.deepcopy(binding)
    for dtype in ("bf16", "fp32"):
        run_add(binding, dtype=dtype)
    run_add(binding, prompt_length=0)
    assert binding == before


def test_check_and_check_rmsnorm_refuse_an_elementwise_add_call_site_key():
    for site in ELEMENTWISE_ADD_CALL_SITES:
        binding = every_binding()
        binding[site] = [BindingEntry(add_kernel(), "every")]
        error = bad_binding(ValueError, binding)
        assert str(CALL_SITES) in str(error)
        binding = norm_binding()
        binding[site] = [BindingEntry(add_kernel(), "every")]
        error = bad_norm_binding(ValueError, binding)
        assert str(RMSNORM_CALL_SITES) in str(error)


def test_check_rmsnorm_refuses_an_elementwise_add_kernel():
    binding = norm_binding()
    binding["norm"] = [BindingEntry(add_kernel(), "every")]
    (outcome,) = run_norm(binding).outcomes
    assert outcome == Outcome(
        "kernel_unfit",
        "norm",
        None,
        "entry 0: contract.prototype is not that of the bf16 rmsnorm contract",
    )


def test_swiglu_call_sites():
    assert SWIGLU_CALL_SITES == ("ffn_activation",)
    assert not set(SWIGLU_CALL_SITES) & set(CALL_SITES)
    assert not set(SWIGLU_CALL_SITES) & set(RMSNORM_CALL_SITES)
    assert not set(SWIGLU_CALL_SITES) & set(ELEMENTWISE_ADD_CALL_SITES)


def test_swiglu_dtypes():
    assert SWIGLU_DTYPES == ("bf16",)
    assert SWIGLU_DTYPES == (swiglu_bf16_contract.DTYPE,)


@pytest.mark.parametrize("rows", [1, 7, MAX_INTEGER])
def test_swiglu_shape_small_is_the_intermediate_width(rows):
    assert swiglu_shape(SMALL, "ffn_activation", rows) == (rows, 16)
    assert swiglu_shape(SMALL, "ffn_activation", rows) != (rows, SMALL.hidden)


def test_swiglu_shape_follows_intermediate_only():
    dimensions = SMALL._replace(intermediate=MAX_INTEGER, hidden=3)
    assert swiglu_shape(dimensions, "ffn_activation", 5) == (5, MAX_INTEGER)
    assert rmsnorm_shape(dimensions, "norm", 5) == (5, 3)
    assert elementwise_add_shape(dimensions, "ffn_residual", 5) == (5, 3)


def test_swiglu_shape_at_llama_values_is_the_contract_table():
    llama = ModelDimensions(2048, 8192, 128256, 16, 32, 8, 64)
    shapes = tuple(swiglu_shape(llama, "ffn_activation", m) for m in (1, 32, 512))
    assert shapes == swiglu_bf16_contract.SHAPES


@pytest.mark.parametrize(
    "site",
    [
        "gate",
        "up",
        "down",
        "ffn_norm",
        "ffn_residual",
        "attention_residual",
        "activation",
        "FFN_ACTIVATION",
        "",
        None,
        3,
    ],
)
def test_swiglu_shape_unknown_call_site(site):
    error = raises(ValueError, "call_site", swiglu_shape, SMALL, site, 1)
    assert str(SWIGLU_CALL_SITES) in str(error)


@pytest.mark.parametrize(
    ("rows", "kind"),
    [
        (True, TypeError),
        (1.0, TypeError),
        (None, TypeError),
        ("1", TypeError),
        (0, ValueError),
        (-1, ValueError),
        (MAX_INTEGER + 1, ValueError),
    ],
)
def test_swiglu_shape_bad_rows(rows, kind):
    raises(kind, "rows", swiglu_shape, SMALL, "ffn_activation", rows)


def test_swiglu_shape_argument_order():
    raises(ValueError, "dimensions", swiglu_shape, SMALL._replace(heads=3), "x", 0)
    raises(TypeError, "dimensions", swiglu_shape, None, "ffn_activation", 1)
    raises(
        ValueError,
        "dimensions",
        swiglu_shape,
        SMALL._replace(intermediate=0),
        "ffn_activation",
        1,
    )
    raises(ValueError, "call_site", swiglu_shape, SMALL, "gate", 0)


def swiglu_shapes(rows):
    return tuple((r, 16) for r in rows)


def test_swiglu_generation_calls_prefill_and_decode():
    calls = swiglu_generation_calls(SMALL, prompt_length=5, generation_length=3)
    assert calls == (("ffn_activation", swiglu_shapes((1, 5))),)


def test_swiglu_generation_calls_one_token_has_no_decode():
    calls = swiglu_generation_calls(SMALL, prompt_length=5, generation_length=1)
    assert calls == (("ffn_activation", swiglu_shapes((5,))),)


def test_swiglu_generation_calls_prompt_of_one_row():
    calls = swiglu_generation_calls(SMALL, prompt_length=1, generation_length=4)
    assert calls == (("ffn_activation", swiglu_shapes((1,))),)


def test_swiglu_generation_calls_rows_match_the_elementwise_add_passes():
    for prompt_length, generation_length in ((6, 2), (1, 1), (9, 1), (4, 7)):
        lengths = {
            "prompt_length": prompt_length,
            "generation_length": generation_length,
        }
        add = dict(elementwise_add_generation_calls(SMALL, **lengths))
        swiglu = dict(swiglu_generation_calls(SMALL, **lengths))
        assert [m for m, _ in swiglu["ffn_activation"]] == [
            m for m, _ in add["ffn_residual"]
        ]
        assert {n for _, n in swiglu["ffn_activation"]} == {SMALL.intermediate}
        assert {n for _, n in add["ffn_residual"]} == {SMALL.hidden}


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
def test_swiglu_generation_calls_refuses(name, value, kind):
    arguments = {"prompt_length": 2, "generation_length": 2}
    arguments[name] = value
    raises(kind, name, swiglu_generation_calls, SMALL, **arguments)


def test_swiglu_generation_calls_argument_order():
    raises(
        TypeError,
        "dimensions",
        swiglu_generation_calls,
        None,
        prompt_length=0,
        generation_length=0,
    )
    raises(
        ValueError,
        "prompt_length",
        swiglu_generation_calls,
        SMALL,
        prompt_length=0,
        generation_length=None,
    )


def test_swiglu_generation_calls_lengths_are_keyword_only():
    with pytest.raises(TypeError):
        swiglu_generation_calls(SMALL, 2, 2)


def swiglu_kernel(name="s", contract=_DEFAULT):
    if contract is _DEFAULT:
        contract = swiglu_bf16_contract.task_contract(3, 5)
    return KernelReference((f"{name}.c",), contract, ("-O2",))


def swiglu_binding():
    return {
        site: [BindingEntry(swiglu_kernel(site), "every")] for site in SWIGLU_CALL_SITES
    }


def run_swiglu(binding=None, **settings):
    arguments = {"dtype": "bf16", "prompt_length": 3, "generation_length": 4}
    arguments.update(settings)
    binding = swiglu_binding() if binding is None else binding
    return check_swiglu(SMALL, binding, **arguments)


def expected_swiglu_calls(binding, rows):
    return tuple(
        ("ffn_activation", (r, 16), binding["ffn_activation"][0].kernel) for r in rows
    )


def test_check_swiglu_every_binding_is_ok():
    binding = swiglu_binding()
    result = run_swiglu(binding)
    assert result == BindingCheck(True, (), expected_swiglu_calls(binding, (1, 3)))
    assert isinstance(result, BindingCheck)


def test_check_swiglu_listed_shapes_cover_exactly():
    binding = {"ffn_activation": [BindingEntry(swiglu_kernel(), swiglu_shapes((1, 3)))]}
    result = run_swiglu(binding)
    assert result.ok
    assert result.calls == expected_swiglu_calls(binding, (1, 3))


def test_check_swiglu_listed_shape_other_than_the_spec_own():
    spec_own = swiglu_bf16_contract.task_contract(512, 8192)
    binding = {
        "ffn_activation": [
            BindingEntry(swiglu_kernel(contract=spec_own), swiglu_shapes((1, 3, 7)))
        ]
    }
    result = run_swiglu(binding)
    assert result.ok
    assert result.calls == expected_swiglu_calls(binding, (1, 3))


def test_check_swiglu_several_entries_disjoint_shapes():
    decode = swiglu_kernel("decode")
    prefill = swiglu_kernel("prefill")
    binding = {
        "ffn_activation": (
            BindingEntry(prefill, swiglu_shapes((3, 9))),
            BindingEntry(decode, swiglu_shapes((1,))),
        )
    }
    result = run_swiglu(binding)
    assert result == BindingCheck(
        True,
        (),
        (
            ("ffn_activation", (1, 16), decode),
            ("ffn_activation", (3, 16), prefill),
        ),
    )


def test_check_swiglu_generation_length_one():
    result = run_swiglu(generation_length=1)
    assert result.ok
    assert [call[1] for call in result.calls] == [(3, 16)]


def test_check_swiglu_accepts_path_sources():
    contract = swiglu_bf16_contract.task_contract(1, 1)
    reference = KernelReference((Path("a.c"), "b.c"), contract, ())
    assert run_swiglu({"ffn_activation": [BindingEntry(reference, "every")]}).ok


def test_check_swiglu_hidden_width_shapes_give_no_kernel():
    binding = {
        "ffn_activation": [BindingEntry(swiglu_kernel(), tuple((r, 8) for r in (1, 3)))]
    }
    assert run_swiglu(binding) == BindingCheck(
        False,
        tuple(
            Outcome(
                "no_kernel",
                "ffn_activation",
                shape,
                "no entry of the binding covers the shape",
            )
            for shape in swiglu_shapes((1, 3))
        ),
        (),
    )


@pytest.mark.parametrize("unknown", ["fp32", "fp16", "int8"])
def test_check_swiglu_unknown_dtype_is_invalid_input(unknown):
    reason = f"dtype: no swiglu contract is known at the dtype {unknown!r}"
    assert run_swiglu(dtype=unknown) == BindingCheck(False, invalid(reason), ())
    assert unknown in reason and "swiglu" in reason


@pytest.mark.parametrize("unknown", ["fp32", "fp16"])
def test_check_swiglu_unknown_dtype_gives_no_unfit_and_no_kernel(unknown):
    reason = f"dtype: no swiglu contract is known at the dtype {unknown!r}"
    binding = {"ffn_activation": [BindingEntry(swiglu_kernel(contract={}), ((3, 99),))]}
    assert run_swiglu(binding, dtype=unknown) == BindingCheck(
        False, invalid(reason), ()
    )


def test_check_swiglu_invalid_lengths():
    assert run_swiglu(prompt_length=0).outcomes == invalid(
        "prompt_length: must be from 1 to 2**53 - 1, got 0"
    )
    assert run_swiglu(generation_length=MAX_INTEGER + 1).outcomes == invalid(
        f"generation_length: must be from 1 to 2**53 - 1, got {MAX_INTEGER + 1}"
    )
    assert run_swiglu(prompt_length=-2).calls == ()


def test_check_swiglu_invalid_input_order_and_no_shape_check():
    binding = {"ffn_activation": [BindingEntry(swiglu_kernel(contract=None), "every")]}
    result = run_swiglu(binding, prompt_length=0, generation_length=-1)
    assert [(o.kind, o.call_site) for o in result.outcomes] == [
        ("invalid_input", None),
        ("invalid_input", None),
        ("kernel_unfit", "ffn_activation"),
    ]
    assert result.outcomes[0].reason.startswith("prompt_length:")
    assert result.outcomes[1].reason.startswith("generation_length:")
    assert result.calls == ()
    unlisted = {"ffn_activation": [BindingEntry(swiglu_kernel(), ((7, 16),))]}
    assert run_swiglu(unlisted, prompt_length=0).outcomes == invalid(
        "prompt_length: must be from 1 to 2**53 - 1, got 0"
    )
    result = run_swiglu(binding, dtype="fp32", prompt_length=0, generation_length=0)
    assert [o.reason.split(":")[0] for o in result.outcomes] == [
        "dtype",
        "prompt_length",
        "generation_length",
    ]
    assert {o.kind for o in result.outcomes} == {"invalid_input"}


def test_check_swiglu_missing_call_site():
    assert run_swiglu({}) == BindingCheck(
        False,
        tuple(
            Outcome(
                "no_kernel",
                "ffn_activation",
                shape,
                "no entry of the binding covers the shape",
            )
            for shape in swiglu_shapes((1, 3))
        ),
        (),
    )


def test_check_swiglu_unlisted_shape():
    binding = {"ffn_activation": [BindingEntry(swiglu_kernel(), swiglu_shapes((1, 7)))]}
    result = run_swiglu(binding)
    assert [(o.kind, o.call_site, o.shape) for o in result.outcomes] == [
        ("no_kernel", "ffn_activation", (3, 16))
    ]
    assert result.calls == ()


def swiglu_unfit_reason(contract):
    binding = {
        "ffn_activation": [BindingEntry(swiglu_kernel(contract=contract), "every")]
    }
    result = run_swiglu(binding)
    assert not result.ok and result.calls == ()
    (outcome,) = result.outcomes
    assert outcome.kind == "kernel_unfit"
    assert outcome.call_site == "ffn_activation" and outcome.shape is None
    assert outcome.reason.startswith("entry 0: ")
    return outcome.reason


def good_swiglu_contract():
    return swiglu_bf16_contract.task_contract(2, 4)


SWIGLU_PROTOTYPE_UNFIT = (
    "entry 0: contract.prototype is not that of the bf16 swiglu contract"
)


def test_check_swiglu_elementwise_add_kernel_is_unfit():
    contract = elementwise_add_bf16_contract.task_contract(2, 4)
    assert [(o["role"], o["dtype"]) for o in contract["operands"]] == [
        (o["role"], o["dtype"]) for o in good_swiglu_contract()["operands"]
    ]
    assert swiglu_unfit_reason(contract) == SWIGLU_PROTOTYPE_UNFIT


def test_check_swiglu_rmsnorm_kernel_is_unfit():
    contract = rmsnorm_bf16_contract.task_contract(2, 4)
    assert swiglu_unfit_reason(contract) == SWIGLU_PROTOTYPE_UNFIT


@pytest.mark.parametrize("dtype", ["bf16", "fp32"])
def test_check_swiglu_gemm_kernel_is_unfit(dtype):
    contract = CONTRACTS[dtype].task_contract(2, 4, 4)
    assert swiglu_unfit_reason(contract) == SWIGLU_PROTOTYPE_UNFIT


def test_check_swiglu_unfit_wrong_prototype():
    contract = good_swiglu_contract()
    contract["prototype"] = contract["prototype"].replace("restrict out", "out")
    assert swiglu_unfit_reason(contract) == SWIGLU_PROTOTYPE_UNFIT


def test_check_swiglu_unfit_wrong_language():
    contract = good_swiglu_contract()
    contract["language"] = "cpp"
    assert swiglu_unfit_reason(contract) == (
        "entry 0: contract.language is not that of the bf16 swiglu contract"
    )


@pytest.mark.parametrize(
    ("index", "member", "value"),
    [
        (0, "name", "a"),
        (1, "name", "gate"),
        (2, "name", "c"),
        (1, "role", "output"),
        (2, "role", "input"),
        (0, "dtype", "fp32"),
        (2, "dtype", "fp16"),
        (1, "dtype", None),
    ],
)
def test_check_swiglu_unfit_wrong_operand(index, member, value):
    contract = good_swiglu_contract()
    contract["operands"][index][member] = value
    assert swiglu_unfit_reason(contract) == (
        f"entry 0: contract.operands[{index}].{member} is not that of the bf16 "
        "swiglu contract"
    )


def test_check_swiglu_unfit_gate_and_up_swapped():
    contract = good_swiglu_contract()
    operands = contract["operands"]
    operands[0], operands[1] = operands[1], operands[0]
    assert swiglu_unfit_reason(contract) == (
        "entry 0: contract.operands[0].name is not that of the bf16 swiglu contract"
    )


@pytest.mark.parametrize("contract", [None, "c", ["language"], 3])
def test_check_swiglu_unfit_non_mapping(contract):
    assert "not a mapping" in swiglu_unfit_reason(contract)


@pytest.mark.parametrize("member", ["language", "prototype", "operands"])
def test_check_swiglu_unfit_missing_member(member):
    contract = good_swiglu_contract()
    del contract[member]
    assert repr(member) in swiglu_unfit_reason(contract)


def test_check_swiglu_unfit_operands_forms():
    contract = good_swiglu_contract()
    contract["operands"] = "abc"
    assert "not a sequence" in swiglu_unfit_reason(contract)
    contract["operands"] = good_swiglu_contract()["operands"][:2]
    assert "2 entries, not 3" in swiglu_unfit_reason(contract)
    contract["operands"] = [*good_swiglu_contract()["operands"], {}]
    assert "4 entries, not 3" in swiglu_unfit_reason(contract)
    contract["operands"] = [*good_swiglu_contract()["operands"][:2], None]
    assert "operands[2] is not a mapping" in swiglu_unfit_reason(contract)
    contract["operands"] = good_swiglu_contract()["operands"]
    del contract["operands"][1]["role"]
    assert "operands[1] lacks the member 'role'" in swiglu_unfit_reason(contract)


def test_check_swiglu_fit_ignores_operand_shapes_and_extra_members():
    contract = good_swiglu_contract()
    contract["operands"][0]["shape"] = [99, 99]
    del contract["operands"][2]["shape"]
    contract["operands"][1]["note"] = "x"
    contract["note"] = "x"
    binding = {
        "ffn_activation": [BindingEntry(swiglu_kernel(contract=contract), "every")]
    }
    assert run_swiglu(binding).ok


def test_check_swiglu_reference_comes_from_the_contract_module(monkeypatch):
    binding = swiglu_binding()
    changed = good_swiglu_contract()
    changed["prototype"] = "void other(void);"
    monkeypatch.setattr(
        swiglu_bf16_contract,
        "task_contract",
        lambda m, n: copy.deepcopy(changed),
    )
    result = run_swiglu(binding)
    assert [(o.kind, o.call_site) for o in result.outcomes] == [
        ("kernel_unfit", "ffn_activation")
    ]
    binding = {
        "ffn_activation": [BindingEntry(swiglu_kernel(contract=changed), "every")]
    }
    assert run_swiglu(binding).ok
    assert run_add().ok
    assert run_norm().ok


def test_check_swiglu_outcome_order():
    binding = {
        "ffn_activation": [
            BindingEntry(swiglu_kernel(), swiglu_shapes((3,))),
            BindingEntry(swiglu_kernel(contract={}), swiglu_shapes((7,))),
            BindingEntry(swiglu_kernel(contract=None), swiglu_shapes((9,))),
        ],
    }
    result = run_swiglu(binding)
    assert [(o.kind, o.call_site, o.shape) for o in result.outcomes] == [
        ("kernel_unfit", "ffn_activation", None),
        ("kernel_unfit", "ffn_activation", None),
        ("no_kernel", "ffn_activation", (1, 16)),
    ]
    assert result.outcomes[0].reason.startswith("entry 1: ")
    assert result.outcomes[1].reason.startswith("entry 2: ")


def test_check_swiglu_arguments_are_keyword_only_without_default():
    parameters = inspect.signature(check_swiglu).parameters
    assert list(parameters) == [
        "dimensions",
        "binding",
        "dtype",
        "prompt_length",
        "generation_length",
    ]
    for name in ("dtype", "prompt_length", "generation_length"):
        assert parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
        assert parameters[name].default is inspect.Parameter.empty
    with pytest.raises(TypeError, match="dtype"):
        check_swiglu(SMALL, swiglu_binding(), prompt_length=1, generation_length=1)


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
def test_check_swiglu_argument_errors(name, value, kind):
    raises(kind, name, run_swiglu, **{name: value})


def test_check_swiglu_argument_order():
    raises(
        TypeError,
        "dimensions",
        check_swiglu,
        tuple(SMALL),
        None,
        dtype=None,
        prompt_length=None,
        generation_length=None,
    )
    raises(
        ValueError,
        "dimensions",
        check_swiglu,
        SMALL._replace(kv_heads=3),
        swiglu_binding(),
        dtype="bf16",
        prompt_length=1,
        generation_length=1,
    )
    raises(ValueError, "dtype", run_swiglu, None, dtype="Bf16", prompt_length=None)
    raises(
        TypeError,
        "prompt_length",
        run_swiglu,
        [],
        prompt_length=None,
        generation_length=None,
    )
    raises(TypeError, "generation_length", run_swiglu, [], generation_length=None)
    raises(TypeError, "binding", run_swiglu, [], prompt_length=0, dtype="fp32")


def bad_swiglu_binding(kind, binding):
    return raises(kind, "binding", run_swiglu, binding)


def with_swiglu_entry(*entries):
    return {"ffn_activation": list(entries)}


def test_check_swiglu_binding_not_mapping():
    bad_swiglu_binding(TypeError, [("ffn_activation", [])])
    raises(
        TypeError,
        "binding",
        check_swiglu,
        SMALL,
        None,
        dtype="bf16",
        prompt_length=1,
        generation_length=1,
    )


@pytest.mark.parametrize(
    "key",
    [
        *CALL_SITES,
        *RMSNORM_CALL_SITES,
        *ELEMENTWISE_ADD_CALL_SITES,
        "activation",
        "FFN_ACTIVATION",
        1,
        None,
    ],
)
def test_check_swiglu_binding_unknown_key(key):
    binding = swiglu_binding()
    binding[key] = [BindingEntry(swiglu_kernel(), "every")]
    error = bad_swiglu_binding(ValueError, binding)
    assert str(SWIGLU_CALL_SITES) in str(error)


def test_check_swiglu_binding_entries_forms():
    for entries, kind in (
        (BindingEntry(swiglu_kernel(), "every"), TypeError),
        ("every", TypeError),
        ([], ValueError),
        (None, TypeError),
        ([(swiglu_kernel(), "every")], TypeError),
        ([BindingEntry(("s.c",), "every")], TypeError),
    ):
        bad_swiglu_binding(kind, {"ffn_activation": entries})


@pytest.mark.parametrize(
    ("reference", "kind"),
    [
        (KernelReference([Path("s.c")], {}, ()), TypeError),
        (KernelReference((), {}, ()), ValueError),
        (KernelReference((b"s.c",), {}, ()), TypeError),
        (KernelReference(("s.c",), {}, ["-O2"]), TypeError),
        (KernelReference(("s.c",), {}, ("-O2", 3)), TypeError),
    ],
)
def test_check_swiglu_binding_kernel_reference_refused(reference, kind):
    bad_swiglu_binding(kind, with_swiglu_entry(BindingEntry(reference, "every")))


@pytest.mark.parametrize(
    ("shapes", "kind"),
    [
        ("all", ValueError),
        ([(1, 16)], TypeError),
        ((), ValueError),
        (None, TypeError),
        (([1, 16],), TypeError),
        (((1, 8, 16),), ValueError),
        (((1,),), ValueError),
        (((0, 16),), ValueError),
        (((1, MAX_INTEGER + 1),), ValueError),
        (((True, 16),), TypeError),
        (((1, 16.0),), TypeError),
    ],
)
def test_check_swiglu_binding_shapes_refused(shapes, kind):
    bad_swiglu_binding(kind, with_swiglu_entry(BindingEntry(swiglu_kernel(), shapes)))


def test_check_swiglu_binding_triple_shape_message():
    error = bad_swiglu_binding(
        ValueError, with_swiglu_entry(BindingEntry(swiglu_kernel(), ((1, 8, 16),)))
    )
    assert str(error) == "ffn_activation: a shape has 3 members, not 2"
    error = bad_swiglu_binding(
        TypeError, with_swiglu_entry(BindingEntry(swiglu_kernel(), ([1, 16],)))
    )
    assert str(error) == "ffn_activation: a shape is not a tuple (m, n)"


def test_check_swiglu_binding_overlapping_entries():
    error = bad_swiglu_binding(
        ValueError,
        with_swiglu_entry(
            BindingEntry(swiglu_kernel(), ((1, 16), (3, 16))),
            BindingEntry(swiglu_kernel(), ((3, 16),)),
        ),
    )
    assert str(error) == "ffn_activation: two entries cover the shape (3, 16)"


def test_check_swiglu_binding_every_beside_another_entry():
    for entries in (
        (
            BindingEntry(swiglu_kernel(), ((5, 16),)),
            BindingEntry(swiglu_kernel(), "every"),
        ),
        (
            BindingEntry(swiglu_kernel(), "every"),
            BindingEntry(swiglu_kernel(), "every"),
        ),
    ):
        error = bad_swiglu_binding(ValueError, with_swiglu_entry(*entries))
        assert "'every' entry overlaps" in str(error)


def test_check_swiglu_malformed_binding_refused_even_with_invalid_input():
    binding = with_swiglu_entry(
        BindingEntry(swiglu_kernel(), "every"),
        BindingEntry(swiglu_kernel(), "every"),
    )
    raises(ValueError, "binding", run_swiglu, binding, prompt_length=0, dtype="fp32")


def test_check_swiglu_does_not_modify_arguments():
    binding = with_swiglu_entry(
        BindingEntry(swiglu_kernel(), swiglu_shapes((1,))),
        BindingEntry(swiglu_kernel(contract={"language": "c"}), swiglu_shapes((3,))),
    )
    dimensions = SMALL
    before = copy.deepcopy(binding)
    for dtype in ("bf16", "fp32"):
        run_swiglu(binding, dtype=dtype)
    run_swiglu(binding, prompt_length=0)
    assert binding == before
    assert dimensions == SMALL


def test_check_check_rmsnorm_and_check_elementwise_add_refuse_an_ffn_activation_key():
    for site in SWIGLU_CALL_SITES:
        binding = every_binding()
        binding[site] = [BindingEntry(swiglu_kernel(), "every")]
        error = bad_binding(ValueError, binding)
        assert str(CALL_SITES) in str(error)
        binding = norm_binding()
        binding[site] = [BindingEntry(swiglu_kernel(), "every")]
        error = bad_norm_binding(ValueError, binding)
        assert str(RMSNORM_CALL_SITES) in str(error)
        binding = add_binding()
        binding[site] = [BindingEntry(swiglu_kernel(), "every")]
        error = bad_add_binding(ValueError, binding)
        assert str(ELEMENTWISE_ADD_CALL_SITES) in str(error)


def test_check_elementwise_add_and_check_rmsnorm_refuse_a_swiglu_kernel():
    binding = add_binding()
    binding["ffn_residual"] = [BindingEntry(swiglu_kernel(), "every")]
    (outcome,) = run_add(binding).outcomes
    assert outcome.reason == ADD_PROTOTYPE_UNFIT
    binding = norm_binding()
    binding["ffn_norm"] = [BindingEntry(swiglu_kernel(), "every")]
    (outcome,) = run_norm(binding).outcomes
    assert outcome.reason == (
        "entry 0: contract.prototype is not that of the bf16 rmsnorm contract"
    )


def test_rope_call_sites():
    assert ROPE_CALL_SITES == ("rope_q", "rope_k")
    for others in (
        CALL_SITES,
        RMSNORM_CALL_SITES,
        ELEMENTWISE_ADD_CALL_SITES,
        SWIGLU_CALL_SITES,
    ):
        assert not set(ROPE_CALL_SITES) & set(others)


def test_rope_dtypes():
    assert ROPE_DTYPES == ("bf16",)
    assert ROPE_DTYPES == (rope_bf16_contract.DTYPE,)


@pytest.mark.parametrize("rows", [1, 7, MAX_INTEGER])
def test_rope_shape_small_follows_the_head_counts(rows):
    assert rope_shape(SMALL, "rope_q", rows) == (rows, 4, 2)
    assert rope_shape(SMALL, "rope_k", rows) == (rows, 2, 2)


def test_rope_shape_each_call_site_follows_its_own_head_field():
    dimensions = SMALL._replace(heads=12, kv_heads=3, head_dim=6)
    assert rope_shape(dimensions, "rope_q", 5) == (5, 12, 6)
    assert rope_shape(dimensions, "rope_k", 5) == (5, 3, 6)
    same = SMALL._replace(heads=2, kv_heads=2)
    assert rope_shape(same, "rope_q", 5) == rope_shape(same, "rope_k", 5) == (5, 2, 2)
    wide = SMALL._replace(hidden=MAX_INTEGER, intermediate=3, vocabulary=5)
    assert rope_shape(wide, "rope_q", 5) == (5, 4, 2)


def test_rope_shape_at_llama_values_is_the_contract_table():
    llama = ModelDimensions(2048, 8192, 128256, 16, 32, 8, 64)
    shapes = tuple(
        rope_shape(llama, site, m) for site in ROPE_CALL_SITES for m in (1, 128, 2048)
    )
    assert shapes == rope_bf16_contract.SHAPES


@pytest.mark.parametrize(
    "site",
    [
        "qkv",
        "o",
        "attention_norm",
        "attention_residual",
        "ffn_activation",
        "rope",
        "ROPE_Q",
        "rope_v",
        "",
        None,
        3,
        ("rope_q",),
    ],
)
def test_rope_shape_unknown_call_site(site):
    error = raises(ValueError, "call_site", rope_shape, SMALL, site, 1)
    assert str(ROPE_CALL_SITES) in str(error)


@pytest.mark.parametrize(
    ("rows", "kind"),
    [
        (True, TypeError),
        (1.0, TypeError),
        (None, TypeError),
        ("1", TypeError),
        (0, ValueError),
        (-1, ValueError),
        (MAX_INTEGER + 1, ValueError),
    ],
)
def test_rope_shape_bad_rows(rows, kind):
    for site in ROPE_CALL_SITES:
        raises(kind, "rows", rope_shape, SMALL, site, rows)


@pytest.mark.parametrize("head_dim", [1, 3, 63])
def test_rope_shape_odd_head_dim_is_refused(head_dim):
    dimensions = SMALL._replace(head_dim=head_dim)
    check_dimensions(dimensions)
    for site in ROPE_CALL_SITES:
        error = raises(ValueError, "dimensions", rope_shape, dimensions, site, 1)
        assert str(error) == (
            f"head_dim must be even for a rope call site, got {head_dim}"
        )


def test_rope_shape_argument_order():
    raises(TypeError, "dimensions", rope_shape, None, "rope_q", 1)
    raises(ValueError, "dimensions", rope_shape, SMALL._replace(heads=3), "x", 0)
    raises(
        ValueError, "dimensions", rope_shape, SMALL._replace(head_dim=0), "rope_q", 1
    )
    error = raises(
        ValueError,
        "dimensions",
        rope_shape,
        SMALL._replace(kv_heads=3, head_dim=3),
        "x",
        0,
    )
    assert "multiple of kv_heads" in str(error)
    raises(ValueError, "dimensions", rope_shape, SMALL._replace(head_dim=3), "x", 0)
    raises(ValueError, "call_site", rope_shape, SMALL, "rope", 0)
    assert list(inspect.signature(rope_shape).parameters) == [
        "dimensions",
        "call_site",
        "rows",
    ]


def rope_shapes(site, rows, dimensions=SMALL):
    heads = dimensions.heads if site == "rope_q" else dimensions.kv_heads
    return tuple((r, heads, dimensions.head_dim) for r in rows)


def test_rope_generation_calls_prefill_and_decode():
    calls = rope_generation_calls(SMALL, prompt_length=5, generation_length=3)
    assert calls == (
        ("rope_q", rope_shapes("rope_q", (1, 5))),
        ("rope_k", rope_shapes("rope_k", (1, 5))),
    )
    assert calls[0][1] == ((1, 4, 2), (5, 4, 2))
    assert calls[1][1] == ((1, 2, 2), (5, 2, 2))


def test_rope_generation_calls_one_token_has_no_decode():
    calls = rope_generation_calls(SMALL, prompt_length=5, generation_length=1)
    assert calls == (
        ("rope_q", rope_shapes("rope_q", (5,))),
        ("rope_k", rope_shapes("rope_k", (5,))),
    )


def test_rope_generation_calls_prompt_of_one_row():
    calls = rope_generation_calls(SMALL, prompt_length=1, generation_length=4)
    assert calls == (
        ("rope_q", rope_shapes("rope_q", (1,))),
        ("rope_k", rope_shapes("rope_k", (1,))),
    )


def test_rope_generation_calls_rows_match_the_swiglu_passes():
    dimensions = SMALL._replace(heads=6, kv_heads=3, head_dim=4)
    for prompt_length, generation_length in ((6, 2), (1, 1), (9, 1), (4, 7)):
        lengths = {
            "prompt_length": prompt_length,
            "generation_length": generation_length,
        }
        swiglu = dict(swiglu_generation_calls(dimensions, **lengths))
        rope = dict(rope_generation_calls(dimensions, **lengths))
        rows = [m for m, _ in swiglu["ffn_activation"]]
        assert list(rope) == list(ROPE_CALL_SITES)
        for site in ROPE_CALL_SITES:
            assert [m for m, _, _ in rope[site]] == rows
            assert rope[site] == rope_shapes(site, rows, dimensions)


@pytest.mark.parametrize("head_dim", [1, 3, 63])
def test_rope_generation_calls_odd_head_dim_is_refused(head_dim):
    raises(
        ValueError,
        "dimensions",
        rope_generation_calls,
        SMALL._replace(head_dim=head_dim),
        prompt_length=2,
        generation_length=2,
    )


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
def test_rope_generation_calls_refuses(name, value, kind):
    arguments = {"prompt_length": 2, "generation_length": 2}
    arguments[name] = value
    raises(kind, name, rope_generation_calls, SMALL, **arguments)


def test_rope_generation_calls_argument_order():
    raises(
        TypeError,
        "dimensions",
        rope_generation_calls,
        None,
        prompt_length=0,
        generation_length=0,
    )
    raises(
        ValueError,
        "dimensions",
        rope_generation_calls,
        SMALL._replace(head_dim=3),
        prompt_length=0,
        generation_length=None,
    )
    raises(
        ValueError,
        "prompt_length",
        rope_generation_calls,
        SMALL,
        prompt_length=0,
        generation_length=None,
    )


def test_rope_generation_calls_lengths_are_keyword_only():
    with pytest.raises(TypeError):
        rope_generation_calls(SMALL, 2, 2)


def rope_kernel(name="p", contract=_DEFAULT):
    if contract is _DEFAULT:
        contract = rope_bf16_contract.task_contract(3, 5, 4)
    return KernelReference((f"{name}.c",), contract, ("-O2",))


def rope_binding():
    return {
        site: [BindingEntry(rope_kernel(site), "every")] for site in ROPE_CALL_SITES
    }


def run_rope(binding=None, dimensions=SMALL, **settings):
    arguments = {"dtype": "bf16", "prompt_length": 3, "generation_length": 4}
    arguments.update(settings)
    binding = rope_binding() if binding is None else binding
    return check_rope(dimensions, binding, **arguments)


def expected_rope_calls(binding, rows):
    return tuple(
        (site, shape, binding[site][0].kernel)
        for site in ROPE_CALL_SITES
        for shape in rope_shapes(site, rows)
    )


def test_check_rope_every_binding_is_ok():
    binding = rope_binding()
    result = run_rope(binding)
    assert result == BindingCheck(True, (), expected_rope_calls(binding, (1, 3)))
    assert isinstance(result, BindingCheck)
    assert [call[0] for call in result.calls] == [
        "rope_q",
        "rope_q",
        "rope_k",
        "rope_k",
    ]


def test_check_rope_listed_shapes_cover_exactly():
    binding = {
        site: [BindingEntry(rope_kernel(site), rope_shapes(site, (1, 3)))]
        for site in ROPE_CALL_SITES
    }
    result = run_rope(binding)
    assert result.ok
    assert result.calls == expected_rope_calls(binding, (1, 3))


def test_check_rope_listed_shape_other_than_the_spec_own():
    spec_own = rope_bf16_contract.task_contract(2048, 32, 64)
    binding = {
        site: [
            BindingEntry(
                rope_kernel(contract=spec_own),
                (*rope_shapes(site, (1, 3, 7)), (2048, 32, 64)),
            )
        ]
        for site in ROPE_CALL_SITES
    }
    result = run_rope(binding)
    assert result.ok
    assert result.calls == expected_rope_calls(binding, (1, 3))


def test_check_rope_several_entries_disjoint_shapes():
    decode = rope_kernel("decode")
    prefill = rope_kernel("prefill")
    query = rope_kernel("query")
    binding = {
        "rope_q": [BindingEntry(query, "every")],
        "rope_k": (
            BindingEntry(prefill, ((3, 2, 2), (9, 2, 2))),
            BindingEntry(decode, ((1, 2, 2),)),
        ),
    }
    assert run_rope(binding) == BindingCheck(
        True,
        (),
        (
            ("rope_q", (1, 4, 2), query),
            ("rope_q", (3, 4, 2), query),
            ("rope_k", (1, 2, 2), decode),
            ("rope_k", (3, 2, 2), prefill),
        ),
    )


def test_check_rope_generation_length_one():
    result = run_rope(generation_length=1)
    assert result.ok
    assert [call[:2] for call in result.calls] == [
        ("rope_q", (3, 4, 2)),
        ("rope_k", (3, 2, 2)),
    ]


def test_check_rope_accepts_path_sources():
    contract = rope_bf16_contract.task_contract(1, 1, 2)
    reference = KernelReference((Path("a.c"), "b.c"), contract, ())
    binding = {site: [BindingEntry(reference, "every")] for site in ROPE_CALL_SITES}
    assert run_rope(binding).ok


def test_check_rope_query_and_key_shapes_swapped_give_no_kernel():
    binding = {
        "rope_q": [BindingEntry(rope_kernel(), rope_shapes("rope_k", (1, 3)))],
        "rope_k": [BindingEntry(rope_kernel(), rope_shapes("rope_q", (1, 3)))],
    }
    assert SMALL.heads != SMALL.kv_heads
    assert run_rope(binding) == BindingCheck(
        False,
        tuple(
            Outcome(
                "no_kernel", site, shape, "no entry of the binding covers the shape"
            )
            for site in ROPE_CALL_SITES
            for shape in rope_shapes(site, (1, 3))
        ),
        (),
    )


def test_check_rope_one_kernel_listing_both_head_counts():
    shapes = (*rope_shapes("rope_q", (1, 3)), *rope_shapes("rope_k", (1, 3)))
    kernel = rope_kernel()
    binding = {site: [BindingEntry(kernel, shapes)] for site in ROPE_CALL_SITES}
    assert run_rope(binding).ok


@pytest.mark.parametrize("unknown", ["fp32", "fp16", "int8"])
def test_check_rope_unknown_dtype_is_invalid_input(unknown):
    reason = f"dtype: no rope contract is known at the dtype {unknown!r}"
    assert run_rope(dtype=unknown) == BindingCheck(False, invalid(reason), ())
    assert unknown in reason and "rope" in reason


@pytest.mark.parametrize("unknown", ["fp32", "fp16"])
def test_check_rope_unknown_dtype_gives_no_unfit_and_no_kernel(unknown):
    reason = f"dtype: no rope contract is known at the dtype {unknown!r}"
    binding = {"rope_q": [BindingEntry(rope_kernel(contract={}), ((3, 99, 2),))]}
    assert run_rope(binding, dtype=unknown) == BindingCheck(False, invalid(reason), ())


def test_check_rope_invalid_lengths():
    assert run_rope(prompt_length=0).outcomes == invalid(
        "prompt_length: must be from 1 to 2**53 - 1, got 0"
    )
    assert run_rope(generation_length=MAX_INTEGER + 1).outcomes == invalid(
        f"generation_length: must be from 1 to 2**53 - 1, got {MAX_INTEGER + 1}"
    )
    assert run_rope(prompt_length=-2).calls == ()


def test_check_rope_invalid_input_order_and_no_shape_check():
    binding = {
        "rope_q": [BindingEntry(rope_kernel(contract=None), "every")],
        "rope_k": [BindingEntry(rope_kernel(contract=[]), "every")],
    }
    result = run_rope(binding, prompt_length=0, generation_length=-1)
    assert [(o.kind, o.call_site) for o in result.outcomes] == [
        ("invalid_input", None),
        ("invalid_input", None),
        ("kernel_unfit", "rope_q"),
        ("kernel_unfit", "rope_k"),
    ]
    assert result.outcomes[0].reason.startswith("prompt_length:")
    assert result.outcomes[1].reason.startswith("generation_length:")
    assert result.calls == ()
    unlisted = {"rope_q": [BindingEntry(rope_kernel(), ((7, 4, 2),))]}
    assert run_rope(unlisted, prompt_length=0).outcomes == invalid(
        "prompt_length: must be from 1 to 2**53 - 1, got 0"
    )
    result = run_rope(binding, dtype="fp32", prompt_length=0, generation_length=0)
    assert [o.reason.split(":")[0] for o in result.outcomes] == [
        "dtype",
        "prompt_length",
        "generation_length",
    ]
    assert {o.kind for o in result.outcomes} == {"invalid_input"}


def test_check_rope_missing_call_site():
    binding = rope_binding()
    del binding["rope_k"]
    assert run_rope(binding) == BindingCheck(
        False,
        tuple(
            Outcome(
                "no_kernel", "rope_k", shape, "no entry of the binding covers the shape"
            )
            for shape in rope_shapes("rope_k", (1, 3))
        ),
        (),
    )
    result = run_rope({})
    assert [(o.kind, o.call_site) for o in result.outcomes] == [
        ("no_kernel", "rope_q"),
        ("no_kernel", "rope_q"),
        ("no_kernel", "rope_k"),
        ("no_kernel", "rope_k"),
    ]


def test_check_rope_unlisted_shape():
    binding = rope_binding()
    binding["rope_q"] = [BindingEntry(rope_kernel(), ((1, 4, 2), (7, 4, 2)))]
    result = run_rope(binding)
    assert [(o.kind, o.call_site, o.shape) for o in result.outcomes] == [
        ("no_kernel", "rope_q", (3, 4, 2))
    ]
    assert result.calls == ()


def test_check_rope_shape_of_another_head_dim_gives_no_kernel():
    binding = rope_binding()
    binding["rope_k"] = [BindingEntry(rope_kernel(), ((1, 2, 4), (3, 2, 4)))]
    result = run_rope(binding)
    assert [(o.kind, o.call_site, o.shape) for o in result.outcomes] == [
        ("no_kernel", "rope_k", (1, 2, 2)),
        ("no_kernel", "rope_k", (3, 2, 2)),
    ]


def rope_unfit_reason(contract, site="rope_q"):
    binding = rope_binding()
    binding[site] = [BindingEntry(rope_kernel(contract=contract), "every")]
    result = run_rope(binding)
    assert not result.ok and result.calls == ()
    (outcome,) = result.outcomes
    assert outcome.kind == "kernel_unfit"
    assert outcome.call_site == site and outcome.shape is None
    assert outcome.reason.startswith("entry 0: ")
    return outcome.reason


def good_rope_contract():
    return rope_bf16_contract.task_contract(2, 4, 6)


ROPE_PROTOTYPE_UNFIT = (
    "entry 0: contract.prototype is not that of the bf16 rope contract"
)


@pytest.mark.parametrize(
    "contract",
    [
        swiglu_bf16_contract.task_contract(2, 4),
        elementwise_add_bf16_contract.task_contract(2, 4),
        rmsnorm_bf16_contract.task_contract(2, 4),
        gemm_bf16_contract.task_contract(2, 4, 4),
        gemm_contract.task_contract(2, 4, 4),
    ],
)
def test_check_rope_kernel_of_another_contract_is_unfit(contract):
    for site in ROPE_CALL_SITES:
        assert rope_unfit_reason(copy.deepcopy(contract), site) == ROPE_PROTOTYPE_UNFIT


def test_check_rope_unfit_wrong_prototype():
    contract = good_rope_contract()
    contract["prototype"] = contract["prototype"].replace(
        "const float", "const uint16_t"
    )
    assert rope_unfit_reason(contract) == ROPE_PROTOTYPE_UNFIT


def test_check_rope_unfit_wrong_language():
    contract = good_rope_contract()
    contract["language"] = "cpp"
    assert rope_unfit_reason(contract, "rope_k") == (
        "entry 0: contract.language is not that of the bf16 rope contract"
    )


@pytest.mark.parametrize(
    ("index", "member", "value"),
    [
        (0, "name", "xq"),
        (1, "name", "freqs"),
        (2, "name", "x"),
        (1, "role", "output"),
        (2, "role", "input"),
        (0, "dtype", "fp32"),
        (2, "dtype", "fp16"),
        (1, "dtype", None),
    ],
)
def test_check_rope_unfit_wrong_operand(index, member, value):
    contract = good_rope_contract()
    contract["operands"][index][member] = value
    assert rope_unfit_reason(contract) == (
        f"entry 0: contract.operands[{index}].{member} is not that of the bf16 "
        "rope contract"
    )


def test_check_rope_unfit_table_in_bf16():
    contract = good_rope_contract()
    assert contract["operands"][1]["dtype"] == "fp32"
    contract["operands"][1]["dtype"] = "bf16"
    assert rope_unfit_reason(contract, "rope_k") == (
        "entry 0: contract.operands[1].dtype is not that of the bf16 rope contract"
    )


def test_check_rope_unfit_x_and_freqs_cis_swapped():
    contract = good_rope_contract()
    operands = contract["operands"]
    operands[0], operands[1] = operands[1], operands[0]
    assert rope_unfit_reason(contract) == (
        "entry 0: contract.operands[0].name is not that of the bf16 rope contract"
    )


@pytest.mark.parametrize("contract", [None, "c", ["language"], 3])
def test_check_rope_unfit_non_mapping(contract):
    assert "not a mapping" in rope_unfit_reason(contract)


@pytest.mark.parametrize("member", ["language", "prototype", "operands"])
def test_check_rope_unfit_missing_member(member):
    contract = good_rope_contract()
    del contract[member]
    assert repr(member) in rope_unfit_reason(contract)


def test_check_rope_unfit_operands_forms():
    contract = good_rope_contract()
    contract["operands"] = "abc"
    assert "not a sequence" in rope_unfit_reason(contract)
    contract["operands"] = [good_rope_contract()["operands"][i] for i in (0, 2)]
    assert "2 entries, not 3" in rope_unfit_reason(contract)
    contract["operands"] = [*good_rope_contract()["operands"], {}]
    assert "4 entries, not 3" in rope_unfit_reason(contract)
    contract["operands"] = [*good_rope_contract()["operands"][:2], None]
    assert "operands[2] is not a mapping" in rope_unfit_reason(contract)
    contract["operands"] = good_rope_contract()["operands"]
    del contract["operands"][1]["role"]
    assert "operands[1] lacks the member 'role'" in rope_unfit_reason(contract)


def test_check_rope_fit_ignores_operand_shapes_and_extra_members():
    contract = good_rope_contract()
    contract["operands"][0]["shape"] = [99, 99]
    contract["operands"][1]["shape"] = [1, 3]
    del contract["operands"][2]["shape"]
    contract["operands"][1]["note"] = "x"
    contract["note"] = "x"
    binding = {
        site: [BindingEntry(rope_kernel(contract=contract), "every")]
        for site in ROPE_CALL_SITES
    }
    assert run_rope(binding).ok


def test_check_rope_reference_comes_from_the_contract_module(monkeypatch):
    binding = rope_binding()
    changed = good_rope_contract()
    changed["prototype"] = "void other(void);"
    seen = []

    def task_contract(m, h, d):
        seen.append((m, h, d))
        return copy.deepcopy(changed)

    monkeypatch.setattr(rope_bf16_contract, "task_contract", task_contract)
    result = run_rope(binding)
    assert [(o.kind, o.call_site) for o in result.outcomes] == [
        ("kernel_unfit", "rope_q"),
        ("kernel_unfit", "rope_k"),
    ]
    assert seen and all(d % 2 == 0 for _, _, d in seen)
    binding = {
        site: [BindingEntry(rope_kernel(contract=changed), "every")]
        for site in ROPE_CALL_SITES
    }
    assert run_rope(binding).ok
    assert run_swiglu().ok
    assert run_add().ok
    assert run_norm().ok


def test_check_rope_outcome_order():
    binding = {
        "rope_q": [
            BindingEntry(rope_kernel(), ((3, 4, 2),)),
            BindingEntry(rope_kernel(contract={}), ((7, 4, 2),)),
        ],
        "rope_k": [
            BindingEntry(rope_kernel(contract=None), ((9, 2, 2),)),
            BindingEntry(rope_kernel(), ((1, 2, 2),)),
        ],
    }
    result = run_rope(binding)
    assert [(o.kind, o.call_site, o.shape) for o in result.outcomes] == [
        ("kernel_unfit", "rope_q", None),
        ("no_kernel", "rope_q", (1, 4, 2)),
        ("kernel_unfit", "rope_k", None),
        ("no_kernel", "rope_k", (3, 2, 2)),
    ]
    assert result.outcomes[0].reason.startswith("entry 1: ")
    assert result.outcomes[2].reason.startswith("entry 0: ")


def test_check_rope_arguments_are_keyword_only_without_default():
    parameters = inspect.signature(check_rope).parameters
    assert list(parameters) == [
        "dimensions",
        "binding",
        "dtype",
        "prompt_length",
        "generation_length",
    ]
    for name in ("dtype", "prompt_length", "generation_length"):
        assert parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
        assert parameters[name].default is inspect.Parameter.empty
    with pytest.raises(TypeError, match="dtype"):
        check_rope(SMALL, rope_binding(), prompt_length=1, generation_length=1)


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
def test_check_rope_argument_errors(name, value, kind):
    raises(kind, name, run_rope, **{name: value})


@pytest.mark.parametrize("head_dim", [1, 3, 63])
def test_check_rope_odd_head_dim_is_refused(head_dim):
    error = raises(
        ValueError, "dimensions", run_rope, dimensions=SMALL._replace(head_dim=head_dim)
    )
    assert str(error) == f"head_dim must be even for a rope call site, got {head_dim}"


def test_check_rope_argument_order():
    raises(
        TypeError,
        "dimensions",
        check_rope,
        tuple(SMALL),
        None,
        dtype=None,
        prompt_length=None,
        generation_length=None,
    )
    raises(
        ValueError,
        "dimensions",
        check_rope,
        SMALL._replace(kv_heads=3),
        rope_binding(),
        dtype="bf16",
        prompt_length=1,
        generation_length=1,
    )
    raises(
        ValueError,
        "dimensions",
        check_rope,
        SMALL._replace(head_dim=3),
        None,
        dtype=None,
        prompt_length=None,
        generation_length=None,
    )
    raises(ValueError, "dtype", run_rope, None, dtype="Bf16", prompt_length=None)
    raises(
        TypeError,
        "prompt_length",
        run_rope,
        [],
        prompt_length=None,
        generation_length=None,
    )
    raises(TypeError, "generation_length", run_rope, [], generation_length=None)
    raises(TypeError, "binding", run_rope, [], prompt_length=0, dtype="fp32")


def bad_rope_binding(kind, binding):
    return raises(kind, "binding", run_rope, binding)


def with_rope_entry(*entries, site="rope_q"):
    binding = rope_binding()
    binding[site] = list(entries)
    return binding


def test_check_rope_binding_not_mapping():
    bad_rope_binding(TypeError, [("rope_q", [])])
    raises(
        TypeError,
        "binding",
        check_rope,
        SMALL,
        None,
        dtype="bf16",
        prompt_length=1,
        generation_length=1,
    )


@pytest.mark.parametrize(
    "key",
    [
        *CALL_SITES,
        *RMSNORM_CALL_SITES,
        *ELEMENTWISE_ADD_CALL_SITES,
        *SWIGLU_CALL_SITES,
        "rope",
        "ROPE_Q",
        "rope_v",
        1,
        None,
    ],
)
def test_check_rope_binding_unknown_key(key):
    binding = rope_binding()
    binding[key] = [BindingEntry(rope_kernel(), "every")]
    error = bad_rope_binding(ValueError, binding)
    assert str(ROPE_CALL_SITES) in str(error)


def test_check_rope_binding_entries_forms():
    for entries, kind in (
        (BindingEntry(rope_kernel(), "every"), TypeError),
        ("every", TypeError),
        ([], ValueError),
        (None, TypeError),
        ([(rope_kernel(), "every")], TypeError),
        ([BindingEntry(("p.c",), "every")], TypeError),
    ):
        bad_rope_binding(kind, {"rope_k": entries})


@pytest.mark.parametrize(
    ("reference", "kind"),
    [
        (KernelReference([Path("p.c")], {}, ()), TypeError),
        (KernelReference((), {}, ()), ValueError),
        (KernelReference((b"p.c",), {}, ()), TypeError),
        (KernelReference(("p.c",), {}, ["-O2"]), TypeError),
        (KernelReference(("p.c",), {}, ("-O2", 3)), TypeError),
    ],
)
def test_check_rope_binding_kernel_reference_refused(reference, kind):
    bad_rope_binding(kind, with_rope_entry(BindingEntry(reference, "every")))


@pytest.mark.parametrize(
    ("shapes", "kind"),
    [
        ("all", ValueError),
        ([(1, 4, 2)], TypeError),
        ((), ValueError),
        (None, TypeError),
        (([1, 4, 2],), TypeError),
        (((1, 4),), ValueError),
        (((1, 4, 2, 1),), ValueError),
        (((1,),), ValueError),
        (((0, 4, 2),), ValueError),
        (((1, 0, 2),), ValueError),
        (((1, 4, MAX_INTEGER + 1),), ValueError),
        (((True, 4, 2),), TypeError),
        (((1, 4, 2.0),), TypeError),
    ],
)
def test_check_rope_binding_shapes_refused(shapes, kind):
    bad_rope_binding(kind, with_rope_entry(BindingEntry(rope_kernel(), shapes)))


def test_check_rope_binding_shape_member_messages():
    error = bad_rope_binding(
        ValueError, with_rope_entry(BindingEntry(rope_kernel(), ((1, 4),)))
    )
    assert str(error) == "rope_q: a shape has 2 members, not 3"
    error = bad_rope_binding(
        ValueError,
        with_rope_entry(BindingEntry(rope_kernel(), ((1, 2, 2, 1),)), site="rope_k"),
    )
    assert str(error) == "rope_k: a shape has 4 members, not 3"
    error = bad_rope_binding(
        TypeError, with_rope_entry(BindingEntry(rope_kernel(), ([1, 4, 2],)))
    )
    assert str(error) == "rope_q: a shape is not a tuple (m, h, d)"


def test_check_rope_binding_overlapping_entries():
    error = bad_rope_binding(
        ValueError,
        with_rope_entry(
            BindingEntry(rope_kernel(), ((1, 2, 2), (3, 2, 2))),
            BindingEntry(rope_kernel(), ((3, 2, 2),)),
            site="rope_k",
        ),
    )
    assert str(error) == "rope_k: two entries cover the shape (3, 2, 2)"


def test_check_rope_binding_every_beside_another_entry():
    for entries in (
        (
            BindingEntry(rope_kernel(), ((5, 4, 2),)),
            BindingEntry(rope_kernel(), "every"),
        ),
        (
            BindingEntry(rope_kernel(), "every"),
            BindingEntry(rope_kernel(), "every"),
        ),
    ):
        error = bad_rope_binding(ValueError, with_rope_entry(*entries))
        assert "'every' entry overlaps" in str(error)


def test_check_rope_malformed_binding_refused_even_with_invalid_input():
    binding = with_rope_entry(
        BindingEntry(rope_kernel(), "every"),
        BindingEntry(rope_kernel(), "every"),
    )
    raises(ValueError, "binding", run_rope, binding, prompt_length=0, dtype="fp32")


def test_check_rope_does_not_modify_arguments():
    binding = {
        "rope_q": [
            BindingEntry(rope_kernel(), ((1, 4, 2),)),
            BindingEntry(rope_kernel(contract={"language": "c"}), ((3, 4, 2),)),
        ],
        "rope_k": (BindingEntry(rope_kernel(), "every"),),
    }
    dimensions = SMALL
    before = copy.deepcopy(binding)
    for dtype in ("bf16", "fp32"):
        run_rope(binding, dtype=dtype)
    run_rope(binding, prompt_length=0)
    assert binding == before
    assert dimensions == SMALL


def test_other_checks_still_accept_an_odd_head_dim():
    odd = SMALL._replace(head_dim=3)
    check_dimensions(odd)
    lengths = {"prompt_length": 3, "generation_length": 4}
    assert check_rmsnorm(odd, norm_binding(), dtype="bf16", **lengths).ok
    assert check_elementwise_add(odd, add_binding(), dtype="bf16", **lengths).ok
    assert check_swiglu(odd, swiglu_binding(), dtype="bf16", **lengths).ok
    assert check(
        odd,
        every_binding(),
        dtype="fp32",
        prompt=[1, 2, 3],
        generation_length=4,
        lm_head_rows="all",
    ).ok
    assert gemm_shape(odd, "o", 1) == (1, 12, 8)


def test_other_checks_refuse_a_rope_call_site_key():
    for site in ROPE_CALL_SITES:
        binding = every_binding()
        binding[site] = [BindingEntry(rope_kernel(), "every")]
        error = bad_binding(ValueError, binding)
        assert str(CALL_SITES) in str(error)
        binding = norm_binding()
        binding[site] = [BindingEntry(rope_kernel(), "every")]
        error = bad_norm_binding(ValueError, binding)
        assert str(RMSNORM_CALL_SITES) in str(error)
        binding = add_binding()
        binding[site] = [BindingEntry(rope_kernel(), "every")]
        error = bad_add_binding(ValueError, binding)
        assert str(ELEMENTWISE_ADD_CALL_SITES) in str(error)
        binding = swiglu_binding()
        binding[site] = [BindingEntry(rope_kernel(), "every")]
        error = bad_swiglu_binding(ValueError, binding)
        assert str(SWIGLU_CALL_SITES) in str(error)


def test_other_checks_refuse_a_rope_kernel():
    binding = swiglu_binding()
    binding["ffn_activation"] = [BindingEntry(rope_kernel(), "every")]
    (outcome,) = run_swiglu(binding).outcomes
    assert outcome.reason == SWIGLU_PROTOTYPE_UNFIT
    binding = add_binding()
    binding["ffn_residual"] = [BindingEntry(rope_kernel(), "every")]
    (outcome,) = run_add(binding).outcomes
    assert outcome.reason == ADD_PROTOTYPE_UNFIT


LLAMA = ModelDimensions(2048, 8192, 128256, 16, 32, 8, 64)
OTHER_CALL_SITES = (
    *CALL_SITES,
    *RMSNORM_CALL_SITES,
    *ELEMENTWISE_ADD_CALL_SITES,
    *SWIGLU_CALL_SITES,
    *ROPE_CALL_SITES,
)


def test_sdpa_call_sites():
    assert SDPA_CALL_SITES == ("sdpa",)
    assert not set(SDPA_CALL_SITES) & set(OTHER_CALL_SITES)


def test_sdpa_dtypes():
    assert SDPA_DTYPES == ("bf16",)
    assert SDPA_DTYPES == (sdpa_kv_cache_bf16_contract.DTYPE,)


@pytest.mark.parametrize(
    ("rows", "positions"),
    [(1, 1), (1, 7), (7, 7), (3, 9), (1, MAX_INTEGER), (MAX_INTEGER, MAX_INTEGER)],
)
def test_sdpa_shape_small(rows, positions):
    assert sdpa_shape(SMALL, "sdpa", rows, positions) == (rows, positions, 4, 2, 2)


def test_sdpa_shape_each_member_follows_its_own_field():
    dimensions = SMALL._replace(heads=12, kv_heads=3, head_dim=6)
    assert sdpa_shape(dimensions, "sdpa", 5, 9) == (5, 9, 12, 3, 6)
    same = SMALL._replace(heads=2, kv_heads=2)
    assert sdpa_shape(same, "sdpa", 2, 3) == (2, 3, 2, 2, 2)
    wide = SMALL._replace(hidden=MAX_INTEGER, intermediate=3, vocabulary=5)
    assert sdpa_shape(wide, "sdpa", 2, 3) == (2, 3, 4, 2, 2)


@pytest.mark.parametrize("head_dim", [1, 3, 63])
def test_sdpa_shape_odd_head_dim_is_accepted(head_dim):
    dimensions = SMALL._replace(head_dim=head_dim)
    assert sdpa_shape(dimensions, "sdpa", 1, 2) == (1, 2, 4, 2, head_dim)


def test_sdpa_shape_at_llama_values_is_the_contract_table():
    pairs = ((128, 128), (1, 128), (2048, 2048), (1, 2048))
    shapes = tuple(sdpa_shape(LLAMA, "sdpa", m, l) for m, l in pairs)
    assert shapes == sdpa_kv_cache_bf16_contract.SHAPES


def test_sdpa_shape_positions_below_rows_is_refused():
    assert sdpa_shape(SMALL, "sdpa", 5, 5) == (5, 5, 4, 2, 2)
    error = raises(ValueError, "positions", sdpa_shape, SMALL, "sdpa", 5, 4)
    assert str(error) == "must be at least rows (5), got 4"
    raises(ValueError, "positions", sdpa_shape, SMALL, "sdpa", MAX_INTEGER, 1)


@pytest.mark.parametrize(
    "site",
    [
        *OTHER_CALL_SITES,
        "sdpa_kv_cache",
        "SDPA",
        "attention",
        "sdpa ",
        "",
        None,
        3,
        ("sdpa",),
    ],
)
def test_sdpa_shape_unknown_call_site(site):
    error = raises(ValueError, "call_site", sdpa_shape, SMALL, site, 1, 1)
    assert str(SDPA_CALL_SITES) in str(error)


BAD_COUNTS = [
    (True, TypeError),
    (1.0, TypeError),
    (None, TypeError),
    ("1", TypeError),
    (0, ValueError),
    (-1, ValueError),
    (MAX_INTEGER + 1, ValueError),
]


@pytest.mark.parametrize(("rows", "kind"), BAD_COUNTS)
def test_sdpa_shape_bad_rows(rows, kind):
    error = raises(kind, "rows", sdpa_shape, SMALL, "sdpa", rows, MAX_INTEGER)
    assert str(error).startswith("rows: ")


@pytest.mark.parametrize(("positions", "kind"), BAD_COUNTS)
def test_sdpa_shape_bad_positions(positions, kind):
    error = raises(kind, "positions", sdpa_shape, SMALL, "sdpa", 1, positions)
    assert str(error).startswith("positions: ")


def test_sdpa_shape_argument_order():
    raises(TypeError, "dimensions", sdpa_shape, None, "x", 0, 0)
    raises(ValueError, "dimensions", sdpa_shape, SMALL._replace(heads=3), "x", 0, 0)
    raises(ValueError, "dimensions", sdpa_shape, SMALL._replace(head_dim=0), "x", 0, 0)
    raises(ValueError, "call_site", sdpa_shape, SMALL, "rope_q", 0, None)
    raises(ValueError, "rows", sdpa_shape, SMALL, "sdpa", 0, None)
    raises(TypeError, "positions", sdpa_shape, SMALL, "sdpa", 5, 4.0)
    error = raises(ValueError, "positions", sdpa_shape, SMALL, "sdpa", 5, 0)
    assert str(error).startswith("positions: must be from 1")
    assert list(inspect.signature(sdpa_shape).parameters) == [
        "dimensions",
        "call_site",
        "rows",
        "positions",
    ]


def sdpa_shapes(pairs, dimensions=SMALL):
    return tuple(
        (m, l, dimensions.heads, dimensions.kv_heads, dimensions.head_dim)
        for m, l in pairs
    )


SDPA_PAIRS = ((1, 4), (1, 5), (1, 6), (3, 3))


def test_sdpa_generation_calls_prefill_and_one_decode_shape_per_pass():
    calls = sdpa_generation_calls(SMALL, prompt_length=3, generation_length=4)
    assert calls == (("sdpa", sdpa_shapes(SDPA_PAIRS)),)
    assert calls[0][1] == (
        (1, 4, 4, 2, 2),
        (1, 5, 4, 2, 2),
        (1, 6, 4, 2, 2),
        (3, 3, 4, 2, 2),
    )


def test_sdpa_generation_calls_one_token_has_no_decode():
    calls = sdpa_generation_calls(SMALL, prompt_length=5, generation_length=1)
    assert calls == (("sdpa", sdpa_shapes(((5, 5),))),)


def test_sdpa_generation_calls_prompt_of_one_row():
    calls = sdpa_generation_calls(SMALL, prompt_length=1, generation_length=4)
    assert calls == (("sdpa", sdpa_shapes(((1, 1), (1, 2), (1, 3), (1, 4)))),)


@pytest.mark.parametrize(
    ("prompt_length", "generation_length"), [(1, 1), (2, 2), (4, 7), (9, 3)]
)
def test_sdpa_generation_calls_has_one_shape_per_pass(prompt_length, generation_length):
    dimensions = SMALL._replace(heads=6, kv_heads=3, head_dim=5)
    ((site, shapes),) = sdpa_generation_calls(
        dimensions, prompt_length=prompt_length, generation_length=generation_length
    )
    assert site == "sdpa"
    assert len(shapes) == generation_length
    assert list(shapes) == sorted(shapes)
    expected = {sdpa_shape(dimensions, "sdpa", prompt_length, prompt_length)}
    expected |= {
        sdpa_shape(dimensions, "sdpa", 1, prompt_length + k)
        for k in range(1, generation_length)
    }
    assert set(shapes) == expected


def test_sdpa_generation_calls_at_llama_values():
    calls = sdpa_generation_calls(LLAMA, prompt_length=127, generation_length=2)
    assert calls == (("sdpa", ((1, 128, 32, 8, 64), (127, 127, 32, 8, 64))),)


def test_sdpa_generation_calls_largest_l_at_the_bound_is_accepted():
    calls = sdpa_generation_calls(SMALL, prompt_length=MAX_INTEGER, generation_length=1)
    assert calls == (("sdpa", sdpa_shapes(((MAX_INTEGER, MAX_INTEGER),))),)
    calls = sdpa_generation_calls(
        SMALL, prompt_length=MAX_INTEGER - 1, generation_length=2
    )
    assert calls == (
        (
            "sdpa",
            sdpa_shapes(((1, MAX_INTEGER), (MAX_INTEGER - 1, MAX_INTEGER - 1))),
        ),
    )


@pytest.mark.parametrize(
    ("prompt_length", "generation_length"),
    [(MAX_INTEGER, 2), (2, MAX_INTEGER), (MAX_INTEGER, MAX_INTEGER)],
)
def test_sdpa_generation_calls_largest_l_above_the_bound_is_refused(
    prompt_length, generation_length
):
    error = raises(
        ValueError,
        "generation_length",
        sdpa_generation_calls,
        SMALL,
        prompt_length=prompt_length,
        generation_length=generation_length,
    )
    assert str(error) == (
        "generation_length: prompt_length + generation_length - 1 must be at most "
        f"2**53 - 1, got {prompt_length} + {generation_length} - 1"
    )


@pytest.mark.parametrize(
    ("name", "value", "kind"),
    [
        ("prompt_length", 0, ValueError),
        ("prompt_length", True, TypeError),
        ("prompt_length", 2.0, TypeError),
        ("prompt_length", MAX_INTEGER + 1, ValueError),
        ("generation_length", 0, ValueError),
        ("generation_length", -3, ValueError),
        ("generation_length", MAX_INTEGER + 1, ValueError),
        ("generation_length", None, TypeError),
    ],
)
def test_sdpa_generation_calls_refuses(name, value, kind):
    arguments = {"prompt_length": 2, "generation_length": 2}
    arguments[name] = value
    error = raises(kind, name, sdpa_generation_calls, SMALL, **arguments)
    assert "prompt_length + generation_length" not in str(error)


def test_sdpa_generation_calls_argument_order():
    raises(
        TypeError,
        "dimensions",
        sdpa_generation_calls,
        None,
        prompt_length=0,
        generation_length=0,
    )
    raises(
        ValueError,
        "dimensions",
        sdpa_generation_calls,
        SMALL._replace(kv_heads=3),
        prompt_length=0,
        generation_length=None,
    )
    raises(
        ValueError,
        "prompt_length",
        sdpa_generation_calls,
        SMALL,
        prompt_length=0,
        generation_length=None,
    )
    raises(
        TypeError,
        "generation_length",
        sdpa_generation_calls,
        SMALL,
        prompt_length=MAX_INTEGER,
        generation_length=None,
    )
    error = raises(
        ValueError,
        "generation_length",
        sdpa_generation_calls,
        SMALL,
        prompt_length=MAX_INTEGER,
        generation_length=MAX_INTEGER + 1,
    )
    assert str(error).startswith("generation_length: must be from 1")


def test_sdpa_generation_calls_lengths_are_keyword_only():
    with pytest.raises(TypeError):
        sdpa_generation_calls(SMALL, 2, 2)
    parameters = inspect.signature(sdpa_generation_calls).parameters
    assert list(parameters) == ["dimensions", "prompt_length", "generation_length"]
    for name in ("prompt_length", "generation_length"):
        assert parameters[name].kind is inspect.Parameter.KEYWORD_ONLY


def sdpa_kernel(name="s", contract=_DEFAULT):
    if contract is _DEFAULT:
        contract = sdpa_kv_cache_bf16_contract.task_contract(1, 128, 32, 8, 64)
    return KernelReference((f"{name}.c",), contract, ("-O2",))


def sdpa_binding():
    return {"sdpa": [BindingEntry(sdpa_kernel("sdpa"), "every")]}


def run_sdpa(binding=None, dimensions=SMALL, **settings):
    arguments = {"dtype": "bf16", "prompt_length": 3, "generation_length": 4}
    arguments.update(settings)
    binding = sdpa_binding() if binding is None else binding
    return check_sdpa(dimensions, binding, **arguments)


def expected_sdpa_calls(binding, pairs):
    kernel = binding["sdpa"][0].kernel
    return tuple(("sdpa", shape, kernel) for shape in sdpa_shapes(pairs))


def sdpa_no_kernel(pairs):
    return tuple(
        Outcome("no_kernel", "sdpa", shape, "no entry of the binding covers the shape")
        for shape in sdpa_shapes(pairs)
    )


def test_check_sdpa_every_binding_is_ok():
    binding = sdpa_binding()
    result = run_sdpa(binding)
    assert result == BindingCheck(True, (), expected_sdpa_calls(binding, SDPA_PAIRS))
    assert isinstance(result, BindingCheck)
    assert [call[1][:2] for call in result.calls] == list(SDPA_PAIRS)


def test_check_sdpa_listed_shapes_cover_exactly():
    binding = {"sdpa": [BindingEntry(sdpa_kernel(), sdpa_shapes(SDPA_PAIRS))]}
    result = run_sdpa(binding)
    assert result.ok
    assert result.calls == expected_sdpa_calls(binding, SDPA_PAIRS)


def test_check_sdpa_listed_shape_other_than_the_spec_own():
    spec_own = sdpa_kv_cache_bf16_contract.task_contract(2048, 2048, 32, 8, 64)
    shapes = (*sdpa_shapes(((1, 7), *SDPA_PAIRS)), (2048, 2048, 32, 8, 64))
    binding = {"sdpa": [BindingEntry(sdpa_kernel(contract=spec_own), shapes)]}
    result = run_sdpa(binding)
    assert result.ok
    assert result.calls == expected_sdpa_calls(binding, SDPA_PAIRS)


def test_check_sdpa_several_entries_disjoint_shapes():
    prefill = sdpa_kernel("prefill")
    decode = sdpa_kernel("decode")
    binding = {
        "sdpa": (
            BindingEntry(prefill, sdpa_shapes(((3, 3), (9, 9)))),
            BindingEntry(decode, sdpa_shapes(((1, 4), (1, 5), (1, 6)))),
        )
    }
    assert run_sdpa(binding) == BindingCheck(
        True,
        (),
        (
            ("sdpa", (1, 4, 4, 2, 2), decode),
            ("sdpa", (1, 5, 4, 2, 2), decode),
            ("sdpa", (1, 6, 4, 2, 2), decode),
            ("sdpa", (3, 3, 4, 2, 2), prefill),
        ),
    )


def test_check_sdpa_generation_length_one():
    result = run_sdpa(generation_length=1)
    assert result.ok
    assert [call[:2] for call in result.calls] == [("sdpa", (3, 3, 4, 2, 2))]


def test_check_sdpa_accepts_path_sources():
    contract = sdpa_kv_cache_bf16_contract.task_contract(1, 1, 1, 1, 1)
    reference = KernelReference((Path("a.c"), "b.c"), contract, ())
    assert run_sdpa({"sdpa": [BindingEntry(reference, "every")]}).ok


@pytest.mark.parametrize("head_dim", [1, 3, 63])
def test_check_sdpa_accepts_an_odd_head_dim(head_dim):
    dimensions = SMALL._replace(head_dim=head_dim)
    result = run_sdpa(dimensions=dimensions)
    assert result.ok
    assert [call[1] for call in result.calls] == list(
        sdpa_shapes(SDPA_PAIRS, dimensions)
    )


def test_check_sdpa_decode_shapes_only_miss_the_prefill():
    binding = {"sdpa": [BindingEntry(sdpa_kernel(), sdpa_shapes(SDPA_PAIRS[:3]))]}
    assert run_sdpa(binding) == BindingCheck(False, sdpa_no_kernel(((3, 3),)), ())


def test_check_sdpa_prefill_shape_only_misses_every_decode_pass():
    binding = {"sdpa": [BindingEntry(sdpa_kernel(), sdpa_shapes(((3, 3),)))]}
    assert run_sdpa(binding) == BindingCheck(False, sdpa_no_kernel(SDPA_PAIRS[:3]), ())


def test_check_sdpa_shapes_of_one_pass_too_many_or_too_few_positions():
    binding = {
        "sdpa": [
            BindingEntry(sdpa_kernel(), sdpa_shapes(((1, 3), (1, 4), (1, 5), (3, 3))))
        ]
    }
    assert run_sdpa(binding).outcomes == sdpa_no_kernel(((1, 6),))


@pytest.mark.parametrize("unknown", ["fp32", "fp16", "int8"])
def test_check_sdpa_unknown_dtype_is_invalid_input(unknown):
    reason = f"dtype: no sdpa_kv_cache contract is known at the dtype {unknown!r}"
    assert run_sdpa(dtype=unknown) == BindingCheck(False, invalid(reason), ())
    assert unknown in reason and "sdpa_kv_cache" in reason


@pytest.mark.parametrize("unknown", ["fp32", "fp16"])
def test_check_sdpa_unknown_dtype_gives_no_unfit_and_no_kernel(unknown):
    reason = f"dtype: no sdpa_kv_cache contract is known at the dtype {unknown!r}"
    binding = {"sdpa": [BindingEntry(sdpa_kernel(contract={}), ((3, 3, 99, 1, 2),))]}
    assert run_sdpa(binding, dtype=unknown) == BindingCheck(False, invalid(reason), ())


def test_check_sdpa_invalid_lengths():
    assert run_sdpa(prompt_length=0).outcomes == invalid(
        "prompt_length: must be from 1 to 2**53 - 1, got 0"
    )
    assert run_sdpa(generation_length=MAX_INTEGER + 1).outcomes == invalid(
        f"generation_length: must be from 1 to 2**53 - 1, got {MAX_INTEGER + 1}"
    )
    assert run_sdpa(prompt_length=-2).calls == ()


OVERLONG = (
    "generation_length: prompt_length + generation_length - 1 must be at most "
    f"2**53 - 1, got {MAX_INTEGER} + 2 - 1"
)


def test_check_sdpa_overlong_generation_is_invalid_input():
    result = run_sdpa(prompt_length=MAX_INTEGER, generation_length=2)
    assert result == BindingCheck(False, invalid(OVERLONG), ())
    result = run_sdpa(prompt_length=2, generation_length=MAX_INTEGER)
    assert result.outcomes == invalid(
        "generation_length: prompt_length + generation_length - 1 must be at most "
        f"2**53 - 1, got 2 + {MAX_INTEGER} - 1"
    )


def test_check_sdpa_largest_l_at_the_bound_is_ok():
    result = run_sdpa(prompt_length=MAX_INTEGER, generation_length=1)
    assert result.ok
    assert [call[1] for call in result.calls] == [(MAX_INTEGER, MAX_INTEGER, 4, 2, 2)]
    result = run_sdpa(prompt_length=MAX_INTEGER - 1, generation_length=2)
    assert result.ok
    assert [call[1][:2] for call in result.calls] == [
        (1, MAX_INTEGER),
        (MAX_INTEGER - 1, MAX_INTEGER - 1),
    ]


def test_check_sdpa_overlong_generation_is_not_looked_for_with_a_length_out_of_range():
    assert run_sdpa(prompt_length=MAX_INTEGER + 1, generation_length=2).outcomes == (
        invalid(f"prompt_length: must be from 1 to 2**53 - 1, got {MAX_INTEGER + 1}")
    )
    assert run_sdpa(
        prompt_length=MAX_INTEGER, generation_length=MAX_INTEGER + 1
    ).outcomes == invalid(
        f"generation_length: must be from 1 to 2**53 - 1, got {MAX_INTEGER + 1}"
    )
    assert run_sdpa(prompt_length=MAX_INTEGER, generation_length=0).outcomes == (
        invalid("generation_length: must be from 1 to 2**53 - 1, got 0")
    )


def test_check_sdpa_invalid_input_order_and_no_shape_check():
    binding = {
        "sdpa": [
            BindingEntry(sdpa_kernel(contract=None), sdpa_shapes(((7, 7),))),
            BindingEntry(sdpa_kernel(contract=[]), sdpa_shapes(((1, 9),))),
        ]
    }
    result = run_sdpa(binding, prompt_length=0, generation_length=-1)
    assert [(o.kind, o.call_site) for o in result.outcomes] == [
        ("invalid_input", None),
        ("invalid_input", None),
        ("kernel_unfit", "sdpa"),
        ("kernel_unfit", "sdpa"),
    ]
    assert result.outcomes[0].reason.startswith("prompt_length:")
    assert result.outcomes[1].reason.startswith("generation_length:")
    assert result.calls == ()
    result = run_sdpa(binding, prompt_length=MAX_INTEGER, generation_length=2)
    assert [(o.kind, o.reason[:8]) for o in result.outcomes] == [
        ("invalid_input", "generati"),
        ("kernel_unfit", "entry 0:"),
        ("kernel_unfit", "entry 1:"),
    ]
    unlisted = {"sdpa": [BindingEntry(sdpa_kernel(), ((7, 7, 4, 2, 2),))]}
    assert run_sdpa(unlisted, prompt_length=0).outcomes == invalid(
        "prompt_length: must be from 1 to 2**53 - 1, got 0"
    )
    assert run_sdpa(
        unlisted, prompt_length=MAX_INTEGER, generation_length=2
    ).outcomes == invalid(OVERLONG)
    result = run_sdpa(binding, dtype="fp32", prompt_length=0, generation_length=0)
    assert [o.reason.split(":")[0] for o in result.outcomes] == [
        "dtype",
        "prompt_length",
        "generation_length",
    ]
    result = run_sdpa(
        binding, dtype="fp16", prompt_length=MAX_INTEGER, generation_length=2
    )
    assert [o.reason for o in result.outcomes] == [
        "dtype: no sdpa_kv_cache contract is known at the dtype 'fp16'",
        OVERLONG,
    ]
    assert {o.kind for o in result.outcomes} == {"invalid_input"}


def test_check_sdpa_missing_call_site():
    assert run_sdpa({}) == BindingCheck(False, sdpa_no_kernel(SDPA_PAIRS), ())


def test_check_sdpa_unlisted_shape():
    binding = {
        "sdpa": [BindingEntry(sdpa_kernel(), sdpa_shapes(((1, 4), (1, 5), (3, 3))))]
    }
    result = run_sdpa(binding)
    assert [(o.kind, o.call_site, o.shape) for o in result.outcomes] == [
        ("no_kernel", "sdpa", (1, 6, 4, 2, 2))
    ]
    assert result.calls == ()


def test_check_sdpa_shape_of_other_head_counts_gives_no_kernel():
    shapes = tuple((m, l, 2, 2, 2) for m, l in SDPA_PAIRS)
    binding = {"sdpa": [BindingEntry(sdpa_kernel(), shapes)]}
    assert run_sdpa(binding).outcomes == sdpa_no_kernel(SDPA_PAIRS)


def sdpa_unfit_reason(contract):
    binding = {"sdpa": [BindingEntry(sdpa_kernel(contract=contract), "every")]}
    result = run_sdpa(binding)
    assert not result.ok and result.calls == ()
    (outcome,) = result.outcomes
    assert outcome.kind == "kernel_unfit"
    assert outcome.call_site == "sdpa" and outcome.shape is None
    assert outcome.reason.startswith("entry 0: ")
    return outcome.reason


def good_sdpa_contract():
    return sdpa_kv_cache_bf16_contract.task_contract(2, 5, 4, 2, 6)


SDPA_PROTOTYPE_UNFIT = (
    "entry 0: contract.prototype is not that of the bf16 sdpa_kv_cache contract"
)


@pytest.mark.parametrize(
    "contract",
    [
        rope_bf16_contract.task_contract(2, 4, 2),
        swiglu_bf16_contract.task_contract(2, 4),
        elementwise_add_bf16_contract.task_contract(2, 4),
        rmsnorm_bf16_contract.task_contract(2, 4),
        gemm_bf16_contract.task_contract(2, 4, 4),
        gemm_contract.task_contract(2, 4, 4),
    ],
)
def test_check_sdpa_kernel_of_another_contract_is_unfit(contract):
    assert sdpa_unfit_reason(copy.deepcopy(contract)) == SDPA_PROTOTYPE_UNFIT


def test_check_sdpa_unfit_wrong_prototype():
    contract = good_sdpa_contract()
    contract["prototype"] = contract["prototype"].replace("_bf16(", "(")
    assert sdpa_unfit_reason(contract) == SDPA_PROTOTYPE_UNFIT
    contract = good_sdpa_contract()
    contract["prototype"] = contract["prototype"].replace(
        "uint16_t *restrict cache_k", "const uint16_t *restrict cache_k"
    )
    assert sdpa_unfit_reason(contract) == SDPA_PROTOTYPE_UNFIT


def test_check_sdpa_unfit_wrong_language():
    contract = good_sdpa_contract()
    contract["language"] = "cpp"
    assert sdpa_unfit_reason(contract) == (
        "entry 0: contract.language is not that of the bf16 sdpa_kv_cache contract"
    )


@pytest.mark.parametrize(
    ("index", "member", "value"),
    [
        (0, "name", "xq"),
        (1, "name", "k"),
        (2, "name", "v"),
        (3, "name", "cache"),
        (4, "name", "cache_k"),
        (5, "name", "o"),
        (0, "role", "inout"),
        (3, "role", "input"),
        (3, "role", "output"),
        (4, "role", "input"),
        (4, "role", "output"),
        (5, "role", "inout"),
        (0, "dtype", "fp32"),
        (3, "dtype", "fp16"),
        (5, "dtype", None),
    ],
)
def test_check_sdpa_unfit_wrong_operand(index, member, value):
    contract = good_sdpa_contract()
    contract["operands"][index][member] = value
    assert sdpa_unfit_reason(contract) == (
        f"entry 0: contract.operands[{index}].{member} is not that of the bf16 "
        "sdpa_kv_cache contract"
    )


def test_check_sdpa_unfit_caches_are_inout():
    contract = good_sdpa_contract()
    assert [o["role"] for o in contract["operands"]] == [
        "input",
        "input",
        "input",
        "inout",
        "inout",
        "output",
    ]
    for role in ("input", "output"):
        contract = good_sdpa_contract()
        contract["operands"][3]["role"] = role
        assert sdpa_unfit_reason(contract) == (
            "entry 0: contract.operands[3].role is not that of the bf16 "
            "sdpa_kv_cache contract"
        )


def test_check_sdpa_unfit_k_new_and_v_new_swapped():
    contract = good_sdpa_contract()
    operands = contract["operands"]
    operands[1], operands[2] = operands[2], operands[1]
    assert sdpa_unfit_reason(contract) == (
        "entry 0: contract.operands[1].name is not that of the bf16 "
        "sdpa_kv_cache contract"
    )


def test_check_sdpa_unfit_five_operands():
    contract = good_sdpa_contract()
    del contract["operands"][4]
    assert sdpa_unfit_reason(contract) == (
        "entry 0: contract.operands has 5 entries, not 6"
    )


@pytest.mark.parametrize("contract", [None, "c", ["language"], 3])
def test_check_sdpa_unfit_non_mapping(contract):
    assert "not a mapping" in sdpa_unfit_reason(contract)


@pytest.mark.parametrize("member", ["language", "prototype", "operands"])
def test_check_sdpa_unfit_missing_member(member):
    contract = good_sdpa_contract()
    del contract[member]
    assert repr(member) in sdpa_unfit_reason(contract)


def test_check_sdpa_unfit_operands_forms():
    contract = good_sdpa_contract()
    contract["operands"] = "abcdef"
    assert "not a sequence" in sdpa_unfit_reason(contract)
    contract["operands"] = [*good_sdpa_contract()["operands"], {}]
    assert "7 entries, not 6" in sdpa_unfit_reason(contract)
    contract["operands"] = [*good_sdpa_contract()["operands"][:5], None]
    assert "operands[5] is not a mapping" in sdpa_unfit_reason(contract)
    contract["operands"] = good_sdpa_contract()["operands"]
    del contract["operands"][4]["dtype"]
    assert "operands[4] lacks the member 'dtype'" in sdpa_unfit_reason(contract)


def test_check_sdpa_fit_ignores_operand_shapes_and_extra_members():
    contract = good_sdpa_contract()
    contract["operands"][3]["shape"] = [256, 8, 64]
    contract["operands"][4]["shape"] = [256, 8, 64]
    contract["operands"][0]["shape"] = [99]
    del contract["operands"][5]["shape"]
    contract["operands"][1]["note"] = "x"
    contract["note"] = "x"
    binding = {"sdpa": [BindingEntry(sdpa_kernel(contract=contract), "every")]}
    assert run_sdpa(binding).ok


def test_check_sdpa_reference_comes_from_the_contract_module(monkeypatch):
    binding = sdpa_binding()
    changed = good_sdpa_contract()
    changed["prototype"] = "void other(void);"
    seen = []

    def task_contract(m, l, h, h_kv, d):
        seen.append((m, l, h, h_kv, d))
        return copy.deepcopy(changed)

    monkeypatch.setattr(sdpa_kv_cache_bf16_contract, "task_contract", task_contract)
    result = run_sdpa(binding)
    assert [(o.kind, o.call_site) for o in result.outcomes] == [
        ("kernel_unfit", "sdpa")
    ]
    assert seen
    binding = {"sdpa": [BindingEntry(sdpa_kernel(contract=changed), "every")]}
    assert run_sdpa(binding).ok
    assert run_rope().ok
    assert run_swiglu().ok
    assert run_add().ok
    assert run_norm().ok


def test_check_sdpa_outcome_order():
    binding = {
        "sdpa": [
            BindingEntry(sdpa_kernel(), sdpa_shapes(((3, 3), (1, 5)))),
            BindingEntry(sdpa_kernel(contract={}), sdpa_shapes(((1, 9),))),
            BindingEntry(sdpa_kernel(contract=None), sdpa_shapes(((1, 6),))),
        ]
    }
    result = run_sdpa(binding)
    assert [(o.kind, o.call_site, o.shape) for o in result.outcomes] == [
        ("kernel_unfit", "sdpa", None),
        ("kernel_unfit", "sdpa", None),
        ("no_kernel", "sdpa", (1, 4, 4, 2, 2)),
    ]
    assert result.outcomes[0].reason.startswith("entry 1: ")
    assert result.outcomes[1].reason.startswith("entry 2: ")
    assert result.calls == ()


def test_check_sdpa_arguments_are_keyword_only_without_default():
    parameters = inspect.signature(check_sdpa).parameters
    assert list(parameters) == [
        "dimensions",
        "binding",
        "dtype",
        "prompt_length",
        "generation_length",
    ]
    for name in ("dtype", "prompt_length", "generation_length"):
        assert parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
        assert parameters[name].default is inspect.Parameter.empty
    with pytest.raises(TypeError, match="dtype"):
        check_sdpa(SMALL, sdpa_binding(), prompt_length=1, generation_length=1)


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
def test_check_sdpa_argument_errors(name, value, kind):
    raises(kind, name, run_sdpa, **{name: value})


def test_check_sdpa_argument_order():
    raises(
        TypeError,
        "dimensions",
        check_sdpa,
        tuple(SMALL),
        None,
        dtype=None,
        prompt_length=None,
        generation_length=None,
    )
    raises(
        ValueError,
        "dimensions",
        check_sdpa,
        SMALL._replace(kv_heads=3),
        None,
        dtype=None,
        prompt_length=None,
        generation_length=None,
    )
    raises(ValueError, "dtype", run_sdpa, None, dtype="Bf16", prompt_length=None)
    raises(
        TypeError,
        "prompt_length",
        run_sdpa,
        [],
        prompt_length=None,
        generation_length=None,
    )
    raises(TypeError, "generation_length", run_sdpa, [], generation_length=None)
    raises(TypeError, "binding", run_sdpa, [], prompt_length=0, dtype="fp32")
    raises(
        TypeError,
        "binding",
        run_sdpa,
        [],
        prompt_length=MAX_INTEGER,
        generation_length=2,
    )


def bad_sdpa_binding(kind, binding):
    return raises(kind, "binding", run_sdpa, binding)


def with_sdpa_entry(*entries):
    return {"sdpa": list(entries)}


def test_check_sdpa_binding_not_mapping():
    bad_sdpa_binding(TypeError, [("sdpa", [])])
    raises(
        TypeError,
        "binding",
        check_sdpa,
        SMALL,
        None,
        dtype="bf16",
        prompt_length=1,
        generation_length=1,
    )


@pytest.mark.parametrize(
    "key",
    [*OTHER_CALL_SITES, "sdpa_kv_cache", "SDPA", "attention", 1, None],
)
def test_check_sdpa_binding_unknown_key(key):
    binding = sdpa_binding()
    binding[key] = [BindingEntry(sdpa_kernel(), "every")]
    error = bad_sdpa_binding(ValueError, binding)
    assert str(SDPA_CALL_SITES) in str(error)


def test_check_sdpa_binding_entries_forms():
    for entries, kind in (
        (BindingEntry(sdpa_kernel(), "every"), TypeError),
        ("every", TypeError),
        ([], ValueError),
        (None, TypeError),
        ([(sdpa_kernel(), "every")], TypeError),
        ([BindingEntry(("s.c",), "every")], TypeError),
    ):
        bad_sdpa_binding(kind, {"sdpa": entries})


@pytest.mark.parametrize(
    ("reference", "kind"),
    [
        (KernelReference([Path("s.c")], {}, ()), TypeError),
        (KernelReference((), {}, ()), ValueError),
        (KernelReference((b"s.c",), {}, ()), TypeError),
        (KernelReference(("s.c",), {}, ["-O2"]), TypeError),
        (KernelReference(("s.c",), {}, ("-O2", 3)), TypeError),
    ],
)
def test_check_sdpa_binding_kernel_reference_refused(reference, kind):
    bad_sdpa_binding(kind, with_sdpa_entry(BindingEntry(reference, "every")))


@pytest.mark.parametrize(
    ("shapes", "kind"),
    [
        ("all", ValueError),
        ([(1, 4, 4, 2, 2)], TypeError),
        ((), ValueError),
        (None, TypeError),
        (([1, 4, 4, 2, 2],), TypeError),
        (((1, 4, 4),), ValueError),
        (((1, 4, 4, 2),), ValueError),
        (((1, 4, 4, 2, 2, 1),), ValueError),
        (((0, 4, 4, 2, 2),), ValueError),
        (((1, 0, 4, 2, 2),), ValueError),
        (((1, 4, 4, 0, 2),), ValueError),
        (((1, 4, 4, 2, MAX_INTEGER + 1),), ValueError),
        (((True, 4, 4, 2, 2),), TypeError),
        (((1, 4, 4, 2.0, 2),), TypeError),
    ],
)
def test_check_sdpa_binding_shapes_refused(shapes, kind):
    bad_sdpa_binding(kind, with_sdpa_entry(BindingEntry(sdpa_kernel(), shapes)))


def test_check_sdpa_binding_shape_member_messages():
    error = bad_sdpa_binding(
        ValueError, with_sdpa_entry(BindingEntry(sdpa_kernel(), ((1, 4, 2),)))
    )
    assert str(error) == "sdpa: a shape has 3 members, not 5"
    error = bad_sdpa_binding(
        ValueError, with_sdpa_entry(BindingEntry(sdpa_kernel(), ((1, 4, 4, 2),)))
    )
    assert str(error) == "sdpa: a shape has 4 members, not 5"
    error = bad_sdpa_binding(
        TypeError, with_sdpa_entry(BindingEntry(sdpa_kernel(), ([1, 4, 4, 2, 2],)))
    )
    assert str(error) == "sdpa: a shape is not a tuple (m, l, h, h_kv, d)"


def test_check_sdpa_binding_overlapping_entries():
    error = bad_sdpa_binding(
        ValueError,
        with_sdpa_entry(
            BindingEntry(sdpa_kernel(), ((1, 4, 4, 2, 2), (3, 3, 4, 2, 2))),
            BindingEntry(sdpa_kernel(), ((3, 3, 4, 2, 2),)),
        ),
    )
    assert str(error) == "sdpa: two entries cover the shape (3, 3, 4, 2, 2)"


def test_check_sdpa_binding_every_beside_another_entry():
    for entries in (
        (
            BindingEntry(sdpa_kernel(), ((5, 5, 4, 2, 2),)),
            BindingEntry(sdpa_kernel(), "every"),
        ),
        (
            BindingEntry(sdpa_kernel(), "every"),
            BindingEntry(sdpa_kernel(), "every"),
        ),
    ):
        error = bad_sdpa_binding(ValueError, with_sdpa_entry(*entries))
        assert "'every' entry overlaps" in str(error)


def test_check_sdpa_malformed_binding_refused_even_with_invalid_input():
    binding = with_sdpa_entry(
        BindingEntry(sdpa_kernel(), "every"),
        BindingEntry(sdpa_kernel(), "every"),
    )
    raises(ValueError, "binding", run_sdpa, binding, prompt_length=0, dtype="fp32")
    raises(
        ValueError,
        "binding",
        run_sdpa,
        binding,
        prompt_length=MAX_INTEGER,
        generation_length=2,
    )


def test_check_sdpa_does_not_modify_arguments():
    binding = {
        "sdpa": [
            BindingEntry(sdpa_kernel(), ((1, 4, 4, 2, 2),)),
            BindingEntry(sdpa_kernel(contract={"language": "c"}), ((3, 3, 4, 2, 2),)),
        ]
    }
    dimensions = SMALL
    before = copy.deepcopy(binding)
    for dtype in ("bf16", "fp32"):
        run_sdpa(binding, dtype=dtype)
    run_sdpa(binding, prompt_length=0)
    run_sdpa(binding, prompt_length=MAX_INTEGER, generation_length=2)
    assert binding == before
    assert dimensions == SMALL


def test_other_checks_refuse_an_sdpa_call_site_key():
    for site in SDPA_CALL_SITES:
        binding = every_binding()
        binding[site] = [BindingEntry(sdpa_kernel(), "every")]
        error = bad_binding(ValueError, binding)
        assert str(CALL_SITES) in str(error)
        binding = norm_binding()
        binding[site] = [BindingEntry(sdpa_kernel(), "every")]
        error = bad_norm_binding(ValueError, binding)
        assert str(RMSNORM_CALL_SITES) in str(error)
        binding = add_binding()
        binding[site] = [BindingEntry(sdpa_kernel(), "every")]
        error = bad_add_binding(ValueError, binding)
        assert str(ELEMENTWISE_ADD_CALL_SITES) in str(error)
        binding = swiglu_binding()
        binding[site] = [BindingEntry(sdpa_kernel(), "every")]
        error = bad_swiglu_binding(ValueError, binding)
        assert str(SWIGLU_CALL_SITES) in str(error)
        binding = rope_binding()
        binding[site] = [BindingEntry(sdpa_kernel(), "every")]
        error = bad_rope_binding(ValueError, binding)
        assert str(ROPE_CALL_SITES) in str(error)


def test_other_checks_refuse_an_sdpa_kernel():
    sdpa = BindingEntry(sdpa_kernel(), "every")
    binding = every_binding("bf16")
    binding["qkv"] = [sdpa]
    (outcome,) = run(binding, dtype="bf16").outcomes
    assert outcome.reason == (
        "entry 0: contract.prototype is not that of the bf16 gemm contract"
    )
    binding = norm_binding()
    binding["norm"] = [sdpa]
    (outcome,) = run_norm(binding).outcomes
    assert outcome.reason == (
        "entry 0: contract.prototype is not that of the bf16 rmsnorm contract"
    )
    binding = add_binding()
    binding["ffn_residual"] = [sdpa]
    (outcome,) = run_add(binding).outcomes
    assert outcome.reason == ADD_PROTOTYPE_UNFIT
    binding = swiglu_binding()
    binding["ffn_activation"] = [sdpa]
    (outcome,) = run_swiglu(binding).outcomes
    assert outcome.reason == SWIGLU_PROTOTYPE_UNFIT
    binding = rope_binding()
    binding["rope_k"] = [sdpa]
    (outcome,) = run_rope(binding).outcomes
    assert outcome.reason == ROPE_PROTOTYPE_UNFIT
