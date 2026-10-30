import copy
import inspect
import math
from pathlib import Path

import numpy
import pytest

from hilclaw import (
    elementwise_add_bf16_contract,
    gemm_bf16_contract,
    gemm_contract,
    model_binding,
    model_forward_check,
    rmsnorm_bf16_contract,
    rope_bf16_contract,
    sdpa_kv_cache_bf16_contract,
    swiglu_bf16_contract,
)
from hilclaw.keys import MAX_INTEGER
from hilclaw.model_binding import (
    BindingCheck,
    BindingEntry,
    KernelReference,
    ModelDimensions,
    Outcome,
)
from hilclaw.model_forward_check import RopeConstants, Weights, check

SMALL = ModelDimensions(
    hidden=8, intermediate=16, vocabulary=11, layers=2, heads=4, kv_heads=2, head_dim=2
)
ROPE = RopeConstants(
    theta=10000,
    scale_factor=2.5,
    low_freq_factor=1,
    high_freq_factor=8,
    old_context_len=1000,
)
PROMPT = (1, 2, 3)
GIVEN = (4, 5, 6, 7)

CONTRACTS = (
    (model_binding.CALL_SITES, gemm_bf16_contract.task_contract(1, 1, 1)),
    (model_binding.RMSNORM_CALL_SITES, rmsnorm_bf16_contract.task_contract(1, 1)),
    (
        model_binding.ELEMENTWISE_ADD_CALL_SITES,
        elementwise_add_bf16_contract.task_contract(1, 1),
    ),
    (model_binding.SWIGLU_CALL_SITES, swiglu_bf16_contract.task_contract(1, 1)),
    (model_binding.ROPE_CALL_SITES, rope_bf16_contract.task_contract(1, 1, 2)),
    (
        model_binding.SDPA_CALL_SITES,
        sdpa_kv_cache_bf16_contract.task_contract(1, 1, 1, 1, 1),
    ),
)
ALL_SITES = tuple(site for sites, _ in CONTRACTS for site in sites)


def every_binding(fp32_gemm=False):
    binding = {}
    for sites, contract in CONTRACTS:
        if fp32_gemm and sites == model_binding.CALL_SITES:
            contract = gemm_contract.task_contract(1, 1, 1)
        for site in sites:
            binding[site] = [
                BindingEntry(KernelReference((f"{site}.c",), contract, ()), "every")
            ]
    return binding


def weights(dimensions=SMALL, dtype=numpy.uint16, **changes):
    d = dimensions
    width = (d.heads + 2 * d.kv_heads) * d.head_dim

    def array(*shape):
        return numpy.zeros(shape, dtype=dtype)

    def layers(*shape):
        return [array(*shape) for _ in range(d.layers)]

    fields = {
        "embedding": array(d.vocabulary, d.hidden),
        "attention_norm": layers(d.hidden),
        "qkv": layers(d.hidden, width),
        "o": layers(d.heads * d.head_dim, d.hidden),
        "ffn_norm": layers(d.hidden),
        "gate": layers(d.hidden, d.intermediate),
        "up": layers(d.hidden, d.intermediate),
        "down": layers(d.intermediate, d.hidden),
        "norm": array(d.hidden),
        "lm_head": array(d.hidden, d.vocabulary),
    }
    fields.update(changes)
    return Weights(**fields)


def run(dimensions=SMALL, binding=None, **changes):
    arguments = {
        "dtype": "bf16",
        "eps": 1e-5,
        "rope": ROPE,
        "weights": weights(),
        "prompt": PROMPT,
        "given": GIVEN,
        "generation_length": len(GIVEN),
        "lm_head_rows": "all",
    }
    arguments.update(changes)
    if binding is None:
        binding = every_binding()
    return check(dimensions, binding, **arguments)


def separate(binding, dimensions=SMALL, dtype="bf16", lm_head_rows="all"):
    results = []
    for function, sites in (
        (model_binding.check, model_binding.CALL_SITES),
        (model_binding.check_rmsnorm, model_binding.RMSNORM_CALL_SITES),
        (model_binding.check_elementwise_add, model_binding.ELEMENTWISE_ADD_CALL_SITES),
        (model_binding.check_swiglu, model_binding.SWIGLU_CALL_SITES),
        (model_binding.check_rope, model_binding.ROPE_CALL_SITES),
        (model_binding.check_sdpa, model_binding.SDPA_CALL_SITES),
    ):
        part = {site: binding[site] for site in sites if site in binding}
        if function is model_binding.check:
            results.append(
                function(
                    dimensions,
                    part,
                    dtype=dtype,
                    prompt=PROMPT,
                    given=GIVEN,
                    generation_length=len(GIVEN),
                    lm_head_rows=lm_head_rows,
                )
            )
        else:
            results.append(
                function(
                    dimensions,
                    part,
                    dtype=dtype,
                    prompt_length=len(PROMPT),
                    generation_length=len(GIVEN),
                )
            )
    return results


def invalid(reason):
    return Outcome("invalid_input", None, None, reason)


def reasons(result):
    return [outcome.reason for outcome in result.outcomes]


@pytest.mark.parametrize("lm_head_rows", ["all", "last"])
def test_a_valid_model_gives_the_calls_of_the_six_checks(lm_head_rows):
    result = run(lm_head_rows=lm_head_rows)
    assert isinstance(result, BindingCheck)
    assert result.ok
    assert result.outcomes == ()
    expected = tuple(
        call
        for part in separate(every_binding(), lm_head_rows=lm_head_rows)
        for call in part.calls
    )
    assert result.calls == expected
    assert [call[0] for call in result.calls[:1]] == ["qkv"]
    assert result.calls[-1][0] == "sdpa"
    assert {call[0] for call in result.calls} == set(ALL_SITES)


def test_one_generated_token_and_float_constants():
    rope = RopeConstants(10000.0, 3.0, 1.5, 5.0, 20.0)
    result = run(rope=rope, given=(9,), generation_length=1, prompt=(0,))
    assert result.ok


def test_all_not_first():
    binding = every_binding()
    unfit = BindingEntry(KernelReference(("x.c",), {"language": "c"}, ()), "every")
    binding["ffn_norm"] = [unfit]
    binding["rope_k"] = [
        BindingEntry(binding["rope_k"][0].kernel, ((1, 2, 2),)),
    ]
    result = run(binding=binding, eps=0.0)
    assert not result.ok
    assert result.calls == ()
    kinds = [(o.kind, o.call_site) for o in result.outcomes]
    assert kinds == [
        ("invalid_input", None),
        ("kernel_unfit", "ffn_norm"),
        ("no_kernel", "rope_k"),
    ]
    assert result.outcomes[0].reason.startswith("eps: ")
    assert result.outcomes[1].reason == "entry 0: contract lacks the member 'prototype'"
    assert [o.shape for o in result.outcomes[2:]] == [(3, 2, 2)]


def test_an_empty_prompt_gives_each_distinct_reason_once():
    result = run(prompt=())
    length = "prompt_length: must be from 1 to 2**53 - 1, got 0"
    assert reasons(result) == ["prompt: is empty", length]
    assert all(o.kind == "invalid_input" for o in result.outcomes)


def test_own_outcomes_come_first_and_duplicates_are_dropped():
    result = run(
        given=None,
        generation_length=0,
        weights=weights(norm=numpy.zeros((7,), dtype=numpy.uint16)),
    )
    assert reasons(result) == [
        "weights.norm: has the shape (7,), not (8,)",
        "generation_length: must be from 1 to 2**53 - 1, got 0",
    ]


@pytest.mark.parametrize("lm_head_rows", ["all", "last"])
def test_the_generation_mode_gives_the_calls_of_the_given_sequence_mode(lm_head_rows):
    result = run(given=None, lm_head_rows=lm_head_rows)
    assert result.ok is True
    assert result.outcomes == ()
    assert result.calls == run(lm_head_rows=lm_head_rows).calls
    longer = run(given=None, generation_length=len(GIVEN) + 2)
    assert longer.ok is True
    assert len(longer.calls) > len(result.calls)


@pytest.mark.parametrize(
    ("generation_length", "reason"),
    [
        (0, "generation_length: must be from 1 to 2**53 - 1, got 0"),
        (-1, "generation_length: must be from 1 to 2**53 - 1, got -1"),
        (2**53, "generation_length: must be from 1 to 2**53 - 1, got 9007199254740992"),
    ],
)
def test_the_generation_mode_still_reports_an_invalid_length(generation_length, reason):
    result = run(given=None, generation_length=generation_length)
    assert result.ok is False
    assert reason in reasons(result)
    assert result.calls == ()


def test_the_generation_mode_reports_a_prompt_token_outside_the_vocabulary():
    result = run(given=None, prompt=(0, SMALL.vocabulary))
    assert result.ok is False
    assert any("prompt[1]" in reason for reason in reasons(result))


@pytest.mark.parametrize("generation_length", [None, "4", 4.0, True])
def test_the_generation_mode_refuses_a_length_of_another_type(generation_length):
    with pytest.raises(TypeError) as caught:
        run(given=None, generation_length=generation_length)
    assert caught.value.parameter == "generation_length"


def test_given_of_another_length_is_the_gemm_check_s():
    result = run(given=(1, 2))
    assert reasons(result) == ["given: has 2 token ids, generation_length is 4"]


@pytest.mark.parametrize("lm_head_rows", ["all", "last"])
def test_the_join_equals_the_separate_checks_on_an_unknown_dtype(lm_head_rows):
    result = run(dtype="fp16", lm_head_rows=lm_head_rows, weights=weights(dtype=float))
    expected = [
        o for part in separate(every_binding(), dtype="fp16") for o in part.outcomes
    ]
    assert list(result.outcomes) == expected
    assert len(expected) == 6
    assert all(o.reason.startswith("dtype: no ") for o in expected)


def test_fp32_accepts_any_element_type_and_checks_shapes():
    binding = every_binding(fp32_gemm=True)
    result = run(
        binding=binding,
        dtype="fp32",
        weights=weights(dtype=numpy.float32, embedding=numpy.zeros((11, 7))),
    )
    assert reasons(result) == [
        "weights.embedding: has the shape (11, 7), not (11, 8)",
        "dtype: no rmsnorm contract is known at the dtype 'fp32'",
        "dtype: no elementwise_add contract is known at the dtype 'fp32'",
        "dtype: no swiglu contract is known at the dtype 'fp32'",
        "dtype: no rope contract is known at the dtype 'fp32'",
        "dtype: no sdpa_kv_cache contract is known at the dtype 'fp32'",
    ]


def test_a_wrong_element_type_at_bf16():
    changed = weights()._replace(
        embedding=numpy.zeros((11, 8), dtype=numpy.float32),
        up=[
            numpy.zeros((8, 16), dtype=numpy.uint16),
            numpy.zeros((8, 16), dtype=numpy.int16),
        ],
    )
    assert reasons(run(weights=changed)) == [
        "weights.embedding: has the element type float32, not uint16",
        "weights.up[1]: has the element type int16, not uint16",
    ]


def test_every_weight_has_its_shape():
    expected = {
        "embedding": (11, 8),
        "attention_norm": (8,),
        "qkv": (8, 16),
        "o": (8, 8),
        "ffn_norm": (8,),
        "gate": (8, 16),
        "up": (8, 16),
        "down": (16, 8),
        "norm": (8,),
        "lm_head": (8, 11),
    }
    for name, value in zip(Weights._fields, weights()):
        arrays = value if isinstance(value, list) else [value]
        assert all(array.shape == expected[name] for array in arrays)
    for name in Weights._fields:
        wrong = numpy.zeros((3, 3), dtype=numpy.uint16)
        if name in model_forward_check._PER_LAYER:
            changed = weights(**{name: [getattr(weights(), name)[0], wrong]})
            label = f"weights.{name}[1]"
        else:
            changed = weights(**{name: wrong})
            label = f"weights.{name}"
        assert reasons(run(weights=changed)) == [
            f"{label}: has the shape (3, 3), not {expected[name]}"
        ]


def test_qkv_width_with_grouped_heads():
    dimensions = SMALL._replace(heads=4, kv_heads=1, head_dim=4, hidden=16)
    assert run(dimensions=dimensions, weights=weights(dimensions)).ok
    wrong = weights(dimensions, qkv=[numpy.zeros((16, 32), dtype=numpy.uint16)] * 2)
    assert reasons(run(dimensions=dimensions, weights=wrong)) == [
        "weights.qkv[0]: has the shape (16, 32), not (16, 24)",
        "weights.qkv[1]: has the shape (16, 32), not (16, 24)",
    ]


@pytest.mark.parametrize("count", [0, 1, 3])
def test_a_wrong_layer_count(count):
    arrays = tuple(numpy.zeros((8, 16), dtype=numpy.uint16) for _ in range(count))
    assert reasons(run(weights=weights(gate=arrays))) == [
        f"weights.gate: has {count} arrays, layers is 2"
    ]


def test_a_wrong_count_and_a_wrong_array_are_both_reported():
    arrays = [numpy.zeros((8, 16), dtype=numpy.int8)]
    assert reasons(run(weights=weights(gate=arrays))) == [
        "weights.gate: has 1 arrays, layers is 2",
        "weights.gate[0]: has the element type int8, not uint16",
    ]


@pytest.mark.parametrize("name", Weights._fields)
@pytest.mark.parametrize("value", [None, [[0]], "x", 1.0])
def test_a_weight_that_is_not_an_array_raises(name, value):
    if name in model_forward_check._PER_LAYER:
        value = [numpy.zeros((1,), dtype=numpy.uint16), value]
    with pytest.raises(TypeError) as raised:
        run(weights=weights(**{name: value}))
    assert raised.value.parameter == f"weights.{name}"


@pytest.mark.parametrize("name", model_forward_check._PER_LAYER)
@pytest.mark.parametrize(
    "make",
    [lambda: numpy.zeros((2, 8), dtype=numpy.uint16), lambda: "ab", lambda: None],
)
def test_a_per_layer_weight_that_is_not_a_sequence_raises(name, make):
    with pytest.raises(TypeError) as raised:
        run(weights=weights(**{name: make()}))
    assert raised.value.parameter == f"weights.{name}"


@pytest.mark.parametrize("value", [None, (), tuple(weights())])
def test_weights_of_a_wrong_type_raise(value):
    with pytest.raises(TypeError) as raised:
        run(weights=value)
    assert raised.value.parameter == "weights"


@pytest.mark.parametrize(
    "eps", [0.0, -1e-5, math.inf, -math.inf, math.nan, 1e-50, 1e300]
)
def test_eps_refusals(eps):
    result = run(eps=eps)
    assert len(result.outcomes) == 1
    assert result.outcomes[0].kind == "invalid_input"
    with pytest.raises(ValueError) as raised:
        model_binding.rmsnorm_eps(eps)
    assert result.outcomes[0].reason == f"eps: {raised.value}"


@pytest.mark.parametrize("eps", [None, 1, True, "1e-5", numpy.float32(1e-5)])
def test_eps_of_a_wrong_type_raises(eps):
    with pytest.raises(TypeError) as raised:
        run(eps=eps)
    assert raised.value.parameter == "eps"


@pytest.mark.parametrize("name", RopeConstants._fields)
@pytest.mark.parametrize("value", [0, -1, 0.0, -2.5, math.inf, math.nan])
def test_each_rope_constant_refused(name, value):
    result = run(rope=ROPE._replace(**{name: value}))
    expected = [f"rope.{name}: must be finite and greater than 0, got {value!r}"]
    assert reasons(result) == expected


@pytest.mark.parametrize("high", [1, 1.0, 0.5])
def test_high_freq_factor_not_above_low(high):
    result = run(rope=ROPE._replace(high_freq_factor=high))
    assert reasons(result) == [
        "rope.high_freq_factor: must be greater than low_freq_factor"
    ]


def test_every_bad_rope_constant_is_reported():
    rope = RopeConstants(0, -1, 2, 1, math.inf)
    assert reasons(run(rope=rope)) == [
        "rope.theta: must be finite and greater than 0, got 0",
        "rope.scale_factor: must be finite and greater than 0, got -1",
        "rope.high_freq_factor: must be greater than low_freq_factor",
        "rope.old_context_len: must be finite and greater than 0, got inf",
    ]


@pytest.mark.parametrize("name", RopeConstants._fields)
@pytest.mark.parametrize("value", [None, True, "1", 1j])
def test_a_rope_constant_of_a_wrong_type_raises(name, value):
    with pytest.raises(TypeError) as raised:
        run(rope=ROPE._replace(**{name: value}))
    assert raised.value.parameter == f"rope.{name}"


@pytest.mark.parametrize("value", [None, tuple(ROPE), dict(ROPE._asdict())])
def test_rope_of_a_wrong_type_raises(value):
    with pytest.raises(TypeError) as raised:
        run(rope=value)
    assert raised.value.parameter == "rope"


def test_an_odd_head_dim_raises_from_the_rope_check():
    dimensions = SMALL._replace(head_dim=3)
    with pytest.raises(ValueError) as raised:
        run(dimensions=dimensions, weights=weights(dimensions))
    assert raised.value.parameter == "dimensions"
    assert "head_dim must be even" in str(raised.value)


def test_a_table_size_over_the_bound(monkeypatch):
    calls = []

    def fake(*args, **kwargs):
        calls.append(kwargs)
        return BindingCheck(True, (), ())

    for name, _ in model_forward_check._CHECKS:
        monkeypatch.setattr(model_binding, name, fake)
    generation = MAX_INTEGER // 2 - len(PROMPT) + 2
    result = run(generation_length=generation)
    assert reasons(result) == [
        f"rope: positions * head_dim must be at most 2**53 - 1, got {MAX_INTEGER // 2 + 1} * 2"
    ]
    assert len(calls) == 6
    assert run(generation_length=generation - 1).ok
    assert run(generation_length=MAX_INTEGER + 1).ok
    assert run(generation_length=0).ok
    assert run(prompt=()).ok


def test_the_six_checks_get_the_split_and_the_prompt_length(monkeypatch):
    seen = []

    def recorder(name):
        def fake(dimensions, binding, **kwargs):
            seen.append((name, dict(binding), kwargs))
            return BindingCheck(True, (), ((name,),))

        return fake

    for name, _ in model_forward_check._CHECKS:
        monkeypatch.setattr(model_binding, name, recorder(name))
    binding = every_binding()
    del binding["o"], binding["sdpa"]
    result = run(binding=binding)
    assert [name for name, _, _ in seen] == [
        "check",
        "check_rmsnorm",
        "check_elementwise_add",
        "check_swiglu",
        "check_rope",
        "check_sdpa",
    ]
    assert result.calls == tuple((name,) for name, _, _ in seen)
    for (name, part, kwargs), (sites, _) in zip(seen, CONTRACTS):
        assert set(part) == set(sites) - {"o", "sdpa"}
        assert kwargs["dtype"] == "bf16"
        assert kwargs["generation_length"] == 4
    assert seen[-1][1] == {}
    assert seen[0][2]["prompt"] == PROMPT
    assert seen[0][2]["given"] == GIVEN
    assert seen[0][2]["lm_head_rows"] == "all"
    for _, _, kwargs in seen[1:]:
        assert kwargs["prompt_length"] == 3


def test_an_absent_call_site_is_no_kernel():
    binding = every_binding()
    del binding["sdpa"], binding["o"]
    result = run(binding=binding)
    assert [(o.kind, o.call_site) for o in result.outcomes] == [
        ("no_kernel", "o"),
        ("no_kernel", "o"),
    ] + [("no_kernel", "sdpa")] * 4
    assert run(binding={}).outcomes[0] == Outcome(
        "no_kernel", "qkv", (1, 8, 16), "no entry of the binding covers the shape"
    )


@pytest.mark.parametrize("key", ["attention", "QKV", 1, None])
def test_a_key_outside_the_fifteen_call_sites_raises(key):
    binding = every_binding()
    binding[key] = binding["qkv"]
    with pytest.raises(ValueError) as raised:
        run(binding=binding)
    assert raised.value.parameter == "binding"


@pytest.mark.parametrize("binding", [None, [("qkv", [])], "qkv"])
def test_a_binding_that_is_not_a_mapping_raises(binding):
    with pytest.raises(TypeError) as raised:
        check(
            SMALL,
            binding,
            dtype="bf16",
            eps=1e-5,
            rope=ROPE,
            weights=weights(),
            prompt=PROMPT,
            given=GIVEN,
            generation_length=4,
            lm_head_rows="all",
        )
    assert raised.value.parameter == "binding"


@pytest.mark.parametrize(
    ("changes", "error", "parameter"),
    [
        ({"dimensions": None}, TypeError, "dimensions"),
        ({"dtype": 1}, TypeError, "dtype"),
        ({"dtype": "BF16"}, ValueError, "dtype"),
        ({"prompt": "abc"}, TypeError, "prompt"),
        ({"given": 5}, TypeError, "given"),
        ({"generation_length": 4.0}, TypeError, "generation_length"),
        ({"lm_head_rows": None}, TypeError, "lm_head_rows"),
    ],
)
def test_errors_of_the_six_checks_propagate(changes, error, parameter):
    with pytest.raises(error) as raised:
        run(**changes)
    assert raised.value.parameter == parameter


def test_a_malformed_entry_propagates_from_its_check():
    binding = every_binding()
    binding["ffn_activation"] = []
    with pytest.raises(ValueError) as raised:
        run(binding=binding)
    assert raised.value.parameter == "binding"
    assert "ffn_activation: has no entry" in str(raised.value)


def test_the_checks_raise_before_this_module_looks_at_its_arguments():
    with pytest.raises(TypeError) as raised:
        run(dtype=None, eps=None, rope=None, weights=None)
    assert raised.value.parameter == "dtype"
    with pytest.raises(TypeError) as raised:
        run(eps=None, rope=None, weights=None)
    assert raised.value.parameter == "eps"
    with pytest.raises(TypeError) as raised:
        run(rope=None, weights=None)
    assert raised.value.parameter == "rope"


def test_arguments_are_not_modified():
    binding = every_binding()
    before_binding = copy.deepcopy(binding)
    given = list(GIVEN)
    prompt = list(PROMPT)
    weight_set = weights()
    before = [
        [a.copy() for a in value] if isinstance(value, list) else value.copy()
        for value in weight_set
    ]
    run(binding=binding, weights=weight_set, prompt=prompt, given=given)
    assert binding == before_binding
    assert given == list(GIVEN) and prompt == list(PROMPT)
    for value, old in zip(weight_set, before):
        if isinstance(value, list):
            assert len(value) == len(old)
            assert all(
                numpy.array_equal(a, b) and a.dtype == b.dtype
                for a, b in zip(value, old)
            )
        else:
            assert numpy.array_equal(value, old)


def test_the_public_names_and_signatures():
    public = {name for name in vars(model_forward_check) if not name.startswith("_")}
    imported = {
        "contextlib",
        "Mapping",
        "Sequence",
        "NamedTuple",
        "numpy",
        "keys",
        "model_binding",
        "rope_table",
    }
    assert public - imported == {"RopeConstants", "Weights", "check"}
    assert RopeConstants._fields == (
        "theta",
        "scale_factor",
        "low_freq_factor",
        "high_freq_factor",
        "old_context_len",
    )
    assert RopeConstants._field_defaults == {}
    assert Weights._field_defaults == {}
    parameters = inspect.signature(check).parameters
    assert tuple(parameters) == (
        "dimensions",
        "binding",
        "dtype",
        "eps",
        "rope",
        "weights",
        "prompt",
        "given",
        "generation_length",
        "lm_head_rows",
    )
    for parameter in parameters.values():
        assert parameter.default is inspect.Parameter.empty
    assert set(ALL_SITES) == set(model_forward_check._CALL_SITES)
    assert len(model_forward_check._CALL_SITES) == 15


def test_the_module_text_chooses_no_rule_or_constant():
    text = Path(model_forward_check.__file__).read_text(encoding="utf-8")
    for word in (
        "argmax",
        "greedy",
        "rtol",
        "atol",
        "500000",
        "8192",
        "__main__",
        "build(",
    ):
        assert word not in text


def test_a_call_builds_no_table(monkeypatch, tmp_path):
    from hilclaw import rope_table

    def fail(**kwargs):
        raise AssertionError("built")

    monkeypatch.setattr(rope_table, "build", fail)
    monkeypatch.setattr(rope_table, "frequencies", fail)
    monkeypatch.chdir(tmp_path)
    assert run().ok
    assert list(tmp_path.iterdir()) == []
