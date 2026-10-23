import copy
from pathlib import Path

import pytest

from hilclaw import gemm_contract
from hilclaw.keys import MAX_INTEGER
from hilclaw.model_binding import (
    CALL_SITES,
    BindingCheck,
    BindingEntry,
    KernelReference,
    ModelDimensions,
    Outcome,
    check,
    check_dimensions,
    gemm_shape,
    generation_calls,
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


def kernel(name="k", contract=_DEFAULT):
    if contract is _DEFAULT:
        contract = gemm_contract.task_contract(3, 4, 5)
    return KernelReference((f"{name}.c",), contract, ("-O2",))


def every_binding():
    return {site: [BindingEntry(kernel(site), "every")] for site in CALL_SITES}


def run(binding=None, **settings):
    arguments = {"prompt": [1, 2, 3], "generation_length": 4, "lm_head_rows": "all"}
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


def unfit_reason(contract):
    binding = every_binding()
    binding["qkv"] = [BindingEntry(kernel(contract=contract), "every")]
    result = run(binding)
    assert not result.ok and result.calls == ()
    (outcome,) = result.outcomes
    assert outcome.kind == "kernel_unfit"
    assert outcome.call_site == "qkv" and outcome.shape is None
    assert outcome.reason.startswith("entry 0: ")
    return outcome.reason


def good_contract():
    return gemm_contract.task_contract(2, 3, 4)


def test_unfit_wrong_prototype():
    contract = good_contract()
    contract["prototype"] = contract["prototype"].replace("restrict a", "a")
    assert "prototype" in unfit_reason(contract)


def test_unfit_wrong_language():
    contract = good_contract()
    contract["language"] = "cpp"
    assert "language" in unfit_reason(contract)


def test_unfit_wrong_role():
    contract = good_contract()
    contract["operands"][1]["role"] = "output"
    assert "operands[1].role" in unfit_reason(contract)


def test_unfit_wrong_dtype():
    contract = good_contract()
    contract["operands"][2]["dtype"] = "fp16"
    assert "operands[2].dtype" in unfit_reason(contract)


def test_unfit_wrong_name():
    contract = good_contract()
    contract["operands"][0]["name"] = "x"
    assert "operands[0].name" in unfit_reason(contract)


def test_unfit_non_string_value():
    contract = good_contract()
    contract["language"] = None
    assert "language" in unfit_reason(contract)


@pytest.mark.parametrize("contract", [None, "c", ["language"], 3])
def test_unfit_non_mapping(contract):
    assert "not a mapping" in unfit_reason(contract)


@pytest.mark.parametrize("member", ["language", "prototype", "operands"])
def test_unfit_missing_member(member):
    contract = good_contract()
    del contract[member]
    assert repr(member) in unfit_reason(contract)


def test_unfit_operands_forms():
    contract = good_contract()
    contract["operands"] = "abc"
    assert "not a sequence" in unfit_reason(contract)
    contract["operands"] = good_contract()["operands"][:2]
    assert "2 entries" in unfit_reason(contract)
    contract["operands"] = [None, *good_contract()["operands"][1:]]
    assert "operands[0] is not a mapping" in unfit_reason(contract)
    contract["operands"] = good_contract()["operands"]
    del contract["operands"][2]["dtype"]
    assert "operands[2] lacks" in unfit_reason(contract)


def test_fit_ignores_operand_shapes_and_extra_members():
    contract = good_contract()
    contract["operands"][0]["shape"] = [99, 99]
    contract["note"] = "x"
    binding = every_binding()
    binding["qkv"] = [BindingEntry(kernel(contract=contract), "every")]
    assert run(binding).ok


def test_fit_reference_comes_from_gemm_contract(monkeypatch):
    binding = every_binding()
    changed = good_contract()
    changed["prototype"] = "void other(void);"
    monkeypatch.setattr(
        gemm_contract, "task_contract", lambda m, k, n: copy.deepcopy(changed)
    )
    result = run(binding)
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
    arguments = {"prompt": [1], "generation_length": 1, "lm_head_rows": "all"}
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
    arguments = {"prompt": [1], "generation_length": 1, "lm_head_rows": "all"}
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
