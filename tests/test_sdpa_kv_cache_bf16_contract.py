import ast
import copy
import inspect
import json
import math
import struct
from pathlib import Path

import pytest

from hilclaw import (
    elementwise_add_bf16_contract,
    gemm_bf16_contract,
    gemm_contract,
    keys,
    rmsnorm_bf16_contract,
    rope_bf16_contract,
    sdpa_kv_cache_bf16_contract,
    spec,
    swiglu_bf16_contract,
)
from hilclaw.keys import MAX_INTEGER, InvalidRecordError, op_signature_key
from hilclaw.sdpa_kv_cache_bf16_contract import (
    DTYPE,
    INPUT_PATTERNS,
    KIND,
    LANGUAGE,
    LAYOUT,
    PROTOTYPE,
    SHAPES,
    covers,
    op_signature_record,
    task_contract,
)

# ADR-0162 decision 9, copied from the record.
ADR_PROTOTYPE = "void hilclaw_sdpa_kv_cache_bf16(size_t m, size_t l, size_t h, size_t h_kv, size_t d, const uint16_t *restrict q, const uint16_t *restrict k_new, const uint16_t *restrict v_new, uint16_t *restrict cache_k, uint16_t *restrict cache_v, uint16_t *restrict out);"

# ADR-0162 decision 10, copied from the record.
ADR_CONTRACT = json.loads(
    """
{
  "language": "c",
  "prototype": "void hilclaw_sdpa_kv_cache_bf16(size_t m, size_t l, size_t h, size_t h_kv, size_t d, const uint16_t *restrict q, const uint16_t *restrict k_new, const uint16_t *restrict v_new, uint16_t *restrict cache_k, uint16_t *restrict cache_v, uint16_t *restrict out);",
  "operands": [
    {"name": "q", "role": "input", "dtype": "bf16", "shape": [1, 32, 64]},
    {"name": "k_new", "role": "input", "dtype": "bf16", "shape": [1, 8, 64]},
    {"name": "v_new", "role": "input", "dtype": "bf16", "shape": [1, 8, 64]},
    {"name": "cache_k", "role": "inout", "dtype": "bf16", "shape": [128, 8, 64]},
    {"name": "cache_v", "role": "inout", "dtype": "bf16", "shape": [128, 8, 64]},
    {"name": "out", "role": "output", "dtype": "bf16", "shape": [1, 32, 64]}
  ]
}
"""
)

# ADR-0162 decision 14, copied from the record.
ADR_RECORD = json.loads(
    '{"schema_version": 1, "kind": "sdpa_kv_cache", "shape": {"m": 1, "l": 128, '
    '"h": 32, "h_kv": 8, "d": 64}, "dtype": "bf16", "layout": "row_major"}'
)
ADR_CANONICAL = b'{"dtype":"bf16","kind":"sdpa_kv_cache","layout":"row_major","schema_version":1,"shape":{"d":64,"h":32,"h_kv":8,"l":128,"m":1}}'
ADR_DIGEST = "9f8c153fbe19c8ee934d21fd64dd8d20e788b76208c8e0f03b8117a754bb4361"
ADR_TABLE = [
    ((128, 128, 32, 8, 64), "sdpa_kv_cache-3a4be50bca85d0dc"),
    ((1, 128, 32, 8, 64), "sdpa_kv_cache-9f8c153fbe19c8ee"),
    ((2048, 2048, 32, 8, 64), "sdpa_kv_cache-e9326c7e4ba5e1c7"),
    ((1, 2048, 32, 8, 64), "sdpa_kv_cache-50b3bf3bcc1ad96d"),
]

RECORD = {
    "schema_version": 1,
    "kind": "sdpa_kv_cache",
    "shape": {"m": 1, "l": 128, "h": 32, "h_kv": 8, "d": 64},
    "dtype": "bf16",
    "layout": "row_major",
}
GEMM_RECORD = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": {"m": 1, "k": 2048, "n": 2048},
    "dtype": "bf16",
    "layout": "row_major",
}
MN_RECORD = dict(RECORD, shape={"m": 1, "n": 2048})
RMSNORM_RECORD = dict(MN_RECORD, kind="rmsnorm")
ADD_RECORD = dict(MN_RECORD, kind="elementwise_add")
SWIGLU_RECORD = dict(MN_RECORD, kind="swiglu", shape={"m": 1, "n": 8192})
ROPE_RECORD = dict(RECORD, kind="rope", shape={"m": 1, "h": 8, "d": 64})

FUNCTIONS = [op_signature_record, task_contract]
DIMENSIONS = ["m", "l", "h", "h_kv", "d"]
SHAPE = {"m": 2, "l": 3, "h": 4, "h_kv": 2, "d": 5}
SMALL_SHAPES = [(1, 1, 1, 1, 1), (2, 3, 4, 2, 5), (3, 3, 4, 4, 7), (1, 9, 6, 3, 2)]
OTHER_CONTRACTS = [
    gemm_contract,
    gemm_bf16_contract,
    rmsnorm_bf16_contract,
    elementwise_add_bf16_contract,
    swiglu_bf16_contract,
    rope_bf16_contract,
]
OTHER_MODULE_NAMES = [
    "gemm_contract",
    "gemm_bf16_contract",
    "rmsnorm_bf16_contract",
    "elementwise_add_bf16_contract",
    "swiglu_bf16_contract",
    "rope_bf16_contract",
]


class IntSubclass(int):
    pass


BAD_DIMENSIONS = [
    0,
    -1,
    -2,
    -(2**53),
    MAX_INTEGER + 1,
    True,
    False,
    1.0,
    2.0,
    "2",
    None,
    IntSubclass(2),
    [2],
    b"2",
]


def synthetic_spec(m, l, h, h_kv, d):
    hw = {
        "schema_version": 1,
        "accelerator": "synthetic_accel",
        "revision": "synthetic-rev-A",
        "toolchain": {"synthetic_cc": "0.0.1-synthetic"},
        "host": {"cpu": "synthetic cpu", "os": "synthetic os"},
        "hw_source": "in_house",
    }
    op = op_signature_record(m, l, h, h_kv, d)
    return {
        "schema_version": 2,
        "id": {
            "run_id": "synthetic-run-1",
            "round": 1,
            "candidate": 1,
            "attempt": 1,
            "candidates": 1,
            "relation": "single",
        },
        "hw_profile": {"key": keys.hw_profile_key(hw).name, "record": hw},
        "task": {
            "op_signature": {"key": op_signature_key(op).name, "record": op},
            "contract": task_contract(m, l, h, h_kv, d),
            "objective": {
                "objectives": [{"type": "latency_minimisation"}],
                "constraints": [],
            },
        },
        "guidance": {"techniques": []},
        "feedback": {"attempts": []},
    }


def imported_modules(path):
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        if isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            found.add(module)
            found |= {f"{module}.{alias.name}" for alias in node.names}
    return found


def widened(pattern):
    return struct.unpack("<f", struct.pack("<I", pattern << 16))[0]


def sdpa_record(m, l, h, h_kv, d, **members):
    shape = {"m": m, "l": l, "h": h, "h_kv": h_kv, "d": d}
    return dict(RECORD, shape=shape, **members)


def test_constants_are_those_of_the_record():
    assert (KIND, DTYPE, LAYOUT, LANGUAGE) == (
        "sdpa_kv_cache",
        "bf16",
        "row_major",
        "c",
    )
    assert PROTOTYPE == ADR_PROTOTYPE
    assert type(PROTOTYPE) is str
    assert "\n" not in PROTOTYPE and "  " not in PROTOTYPE
    assert PROTOTYPE.endswith(");")
    assert PROTOTYPE == ADR_CONTRACT["prototype"]
    assert PROTOTYPE.count("restrict") == 6
    assert PROTOTYPE.count("const") == 3
    names = ["q", "k_new", "v_new", "cache_k", "cache_v", "out"]
    positions = [PROTOTYPE.index(f"*restrict {name}") for name in names]
    assert positions == sorted(positions)
    for name in names[:3]:
        assert f"const uint16_t *restrict {name}," in PROTOTYPE
    for name in names[3:]:
        assert f", uint16_t *restrict {name}" in PROTOTYPE


def test_decode_record_at_l_128_has_the_canonical_form_and_digest_of_the_record():
    record = op_signature_record(1, 128, 32, 8, 64)
    assert record == RECORD == ADR_RECORD
    assert type(record) is dict and type(record["shape"]) is dict
    assert list(record) == ["schema_version", "kind", "shape", "dtype", "layout"]
    assert list(record["shape"]) == DIMENSIONS
    assert record["schema_version"] == keys.SCHEMA_VERSION
    key = op_signature_key(record)
    assert key.canonical == ADR_CANONICAL
    assert key.digest == ADR_DIGEST
    assert key.name == "sdpa_kv_cache-9f8c153fbe19c8ee"


def test_shapes_give_the_four_names_of_the_record_in_its_order():
    assert list(SHAPES) == [shape for shape, _ in ADR_TABLE]
    names = [op_signature_key(op_signature_record(*shape)).name for shape in SHAPES]
    assert names == [name for _, name in ADR_TABLE]


def test_shapes_are_four_different_shapes():
    assert type(SHAPES) is tuple
    assert len(SHAPES) == 4
    assert len(set(SHAPES)) == 4
    for shape in SHAPES:
        assert type(shape) is tuple and len(shape) == 5
        assert all(type(value) is int for value in shape)
        assert shape[2:] == (32, 8, 64)
    assert [(m, l) for m, l, _, _, _ in SHAPES] == [
        (128, 128),
        (1, 128),
        (2048, 2048),
        (1, 2048),
    ]


def test_decode_record_at_l_128_has_the_task_contract_of_the_record():
    contract = task_contract(1, 128, 32, 8, 64)
    assert contract == ADR_CONTRACT
    assert type(contract) is dict and type(contract["operands"]) is list
    assert list(contract) == ["language", "prototype", "operands"]
    for entry in contract["operands"]:
        assert type(entry) is dict and type(entry["shape"]) is list
        assert list(entry) == ["name", "role", "dtype", "shape"]


def test_each_dimension_is_placed_in_its_operand_position():
    assert op_signature_record(2, 3, 4, 2, 5)["shape"] == SHAPE
    assert task_contract(2, 3, 4, 2, 5)["operands"] == [
        {"name": "q", "role": "input", "dtype": "bf16", "shape": [2, 4, 5]},
        {"name": "k_new", "role": "input", "dtype": "bf16", "shape": [2, 2, 5]},
        {"name": "v_new", "role": "input", "dtype": "bf16", "shape": [2, 2, 5]},
        {"name": "cache_k", "role": "inout", "dtype": "bf16", "shape": [3, 2, 5]},
        {"name": "cache_v", "role": "inout", "dtype": "bf16", "shape": [3, 2, 5]},
        {"name": "out", "role": "output", "dtype": "bf16", "shape": [2, 4, 5]},
    ]


def test_arguments_may_be_given_by_name():
    assert op_signature_record(**SHAPE) == op_signature_record(2, 3, 4, 2, 5)
    assert task_contract(d=5, h_kv=2, h=4, l=3, m=2) == task_contract(2, 3, 4, 2, 5)


@pytest.mark.parametrize(
    "shape",
    [
        *SMALL_SHAPES,
        (MAX_INTEGER, MAX_INTEGER, MAX_INTEGER, MAX_INTEGER, MAX_INTEGER),
        *SHAPES,
    ],
)
def test_spec_built_from_the_returned_values_is_valid(shape):
    document = synthetic_spec(*shape)
    spec.validate(document)
    assert document["task"]["contract"]["prototype"] == ADR_PROTOTYPE
    m, l, h, h_kv, d = shape
    operands = document["task"]["contract"]["operands"]
    assert [entry["shape"] for entry in operands] == [
        [m, h, d],
        [m, h_kv, d],
        [m, h_kv, d],
        [l, h_kv, d],
        [l, h_kv, d],
        [m, h, d],
    ]
    assert [entry["role"] for entry in operands] == [
        "input",
        "input",
        "input",
        "inout",
        "inout",
        "output",
    ]


def test_spec_with_a_capacity_shape_of_the_record_refusal_is_refused():
    document = synthetic_spec(1, 128, 32, 8, 64)
    document["task"]["contract"]["operands"][3]["shape"] = [256, 8, 64]
    with pytest.raises(
        spec.InvalidSpecError,
        match=r"^task\.contract\.operands\[3\]\.shape\[0\]: must be a value of "
        r"task\.op_signature\.record\.shape, got 256",
    ):
        spec.validate(document)


def test_input_patterns_are_256_ascending_distinct_16_bit_integers():
    assert type(INPUT_PATTERNS) is tuple
    assert len(INPUT_PATTERNS) == 256
    assert len(set(INPUT_PATTERNS)) == 256
    assert list(INPUT_PATTERNS) == sorted(INPUT_PATTERNS)
    for pattern in INPUT_PATTERNS:
        assert type(pattern) is int
        assert 0 <= pattern <= 0xFFFF
    assert INPUT_PATTERNS[0] == 0x3F00 and INPUT_PATTERNS[-1] == 0xBF7F
    assert set(INPUT_PATTERNS) == set(range(0x3F00, 0x3F80)) | set(
        range(0xBF00, 0xBF80)
    )


def test_input_patterns_are_the_value_set_of_the_record():
    values = [widened(pattern) for pattern in INPUT_PATTERNS]
    for value in values:
        assert math.isfinite(value)
        assert 0.5 <= abs(value) < 1
    expected = {sign * (0.5 + j / 256) for sign in (1, -1) for j in range(128)}
    assert set(values) == expected
    assert len({abs(value) for value in values}) == 128
    for magnitude in {abs(value) for value in values}:
        assert magnitude in values and -magnitude in values


def test_input_patterns_hold_every_bf16_value_of_their_range():
    in_range = {
        pattern
        for pattern in range(0x10000)
        if math.isfinite(widened(pattern)) and 0.5 <= abs(widened(pattern)) < 1
    }
    assert set(INPUT_PATTERNS) == in_range
    for outside in (0x3EFF, 0x3F80, 0xBEFF, 0xBF80):
        assert outside not in INPUT_PATTERNS


@pytest.mark.parametrize("function", FUNCTIONS)
def test_two_calls_give_equal_and_separate_results(function):
    first, second = function(2, 3, 4, 2, 5), function(2, 3, 4, 2, 5)
    assert first == second
    assert first is not second
    if function is op_signature_record:
        assert first["shape"] is not second["shape"]
    else:
        assert first["operands"] is not second["operands"]
        for one, other in zip(first["operands"], second["operands"], strict=True):
            assert one is not other
            assert one["shape"] is not other["shape"]


def test_operand_shapes_of_one_result_are_separate_lists():
    operands = task_contract(2, 3, 4, 2, 5)["operands"]
    shapes = [entry["shape"] for entry in operands]
    assert len({id(shape) for shape in shapes}) == 6
    shapes[1].append(1)
    shapes[3].append(1)
    assert operands[2]["shape"] == [2, 2, 5] and operands[4]["shape"] == [3, 2, 5]


def test_changing_returned_values_changes_nothing_else():
    record = op_signature_record(2, 3, 4, 2, 5)
    record["shape"]["l"] = 9
    record["dtype"] = "fp32"
    contract = task_contract(2, 3, 4, 2, 5)
    expected = task_contract(2, 3, 4, 2, 5)
    contract["operands"][0]["shape"][0] = 9
    contract["operands"][3]["shape"].append(1)
    contract["operands"][3]["role"] = "output"
    contract["operands"][4]["dtype"] = "fp32"
    contract["operands"].pop()
    contract["prototype"] = "changed"
    assert op_signature_record(2, 3, 4, 2, 5)["shape"] == SHAPE
    assert op_signature_record(2, 3, 4, 2, 5)["dtype"] == "bf16"
    assert task_contract(2, 3, 4, 2, 5) == expected
    assert (LANGUAGE, PROTOTYPE, DTYPE) == ("c", ADR_PROTOTYPE, "bf16")


@pytest.mark.parametrize("function", FUNCTIONS)
@pytest.mark.parametrize("dimension", DIMENSIONS)
@pytest.mark.parametrize("value", BAD_DIMENSIONS, ids=repr)
def test_bad_dimension_is_refused(function, dimension, value):
    with pytest.raises(InvalidRecordError) as caught:
        function(**dict(SHAPE, **{dimension: value}))
    message = str(caught.value)
    assert message.startswith(f"shape.{dimension}: must be an integer from 1 to ")
    assert type(caught.value) is InvalidRecordError


@pytest.mark.parametrize("function", FUNCTIONS)
@pytest.mark.parametrize(
    ("m", "l"), [(2, 1), (3, 2), (MAX_INTEGER, MAX_INTEGER - 1), (128, 1)]
)
def test_l_less_than_m_is_refused(function, m, l):
    with pytest.raises(InvalidRecordError) as caught:
        function(m, l, 4, 2, 5)
    assert str(caught.value) == f"shape.l: must be at least m ({m}), got {l}"
    assert type(caught.value) is InvalidRecordError


@pytest.mark.parametrize("function", FUNCTIONS)
@pytest.mark.parametrize(
    ("h", "h_kv"), [(6, 4), (1, 2), (32, 3), (7, 2), (MAX_INTEGER, 2)]
)
def test_h_not_a_multiple_of_h_kv_is_refused(function, h, h_kv):
    with pytest.raises(InvalidRecordError) as caught:
        function(1, 1, h, h_kv, 2)
    assert str(caught.value) == f"shape.h: must be a multiple of h_kv ({h_kv}), got {h}"
    assert type(caught.value) is InvalidRecordError


@pytest.mark.parametrize("function", FUNCTIONS)
def test_first_broken_rule_is_the_one_named(function):
    with pytest.raises(InvalidRecordError, match=r"^shape\.m: "):
        function(0, 0, 0, 0, 0)
    with pytest.raises(InvalidRecordError, match=r"^shape\.l: must be an integer"):
        function(1, 0, 0, 0, 0)
    with pytest.raises(InvalidRecordError, match=r"^shape\.h: must be an integer"):
        function(1, 1, 0, 0, 0)
    with pytest.raises(InvalidRecordError, match=r"^shape\.h_kv: "):
        function(1, 1, 1, 0, 0)
    with pytest.raises(InvalidRecordError, match=r"^shape\.d: "):
        function(1, 1, 1, 1, 0)
    with pytest.raises(InvalidRecordError, match=r"^shape\.d: "):
        function(2, 1, 6, 4, 0)
    with pytest.raises(InvalidRecordError, match=r"^shape\.l: must be at least m"):
        function(2, 1, 6, 4, 2)
    with pytest.raises(InvalidRecordError, match=r"^shape\.h: must be a multiple"):
        function(1, 1, 6, 4, 2)


@pytest.mark.parametrize("function", FUNCTIONS)
def test_long_bad_value_is_shortened_in_the_message(function):
    with pytest.raises(InvalidRecordError) as caught:
        function(2, 3, 4, 2, "x" * 10_000)
    assert len(str(caught.value)) < 200


@pytest.mark.parametrize("function", FUNCTIONS)
@pytest.mark.parametrize(
    ("args", "kwargs"),
    [
        ((), {}),
        ((2,), {}),
        ((2, 3, 4, 2), {}),
        ((2, 3, 4, 2), {"m": 2}),
        ((2, 3, 4, 2, 5, 9), {}),
        ((2, 3, 4, 2, 5), {"p": 1}),
        ((2, 3, 4, 2, 5), {"capacity": 256}),
        ((2, 3, 4, 2, 5), {"scale": 0.125}),
        ((2, 4, 2, 5), {"n": 3}),
    ],
)
def test_missing_or_surplus_argument_is_a_type_error(function, args, kwargs):
    with pytest.raises(TypeError):
        function(*args, **kwargs)


def test_contract_rules_are_accepted_by_keys_and_refused_here():
    for record in (
        sdpa_record(0, 3, 4, 2, 5),
        sdpa_record(3, 2, 4, 2, 5),
        sdpa_record(1, 1, 6, 4, 2),
    ):
        assert op_signature_key(record).name.startswith("sdpa_kv_cache-")
        assert covers(record) is False
        with pytest.raises(InvalidRecordError):
            op_signature_record(**record["shape"])
        with pytest.raises(InvalidRecordError):
            task_contract(**record["shape"])


NOT_COVERED = [
    sdpa_record(1, 128, 32, 8, 64, dtype="fp32"),
    sdpa_record(1, 128, 32, 8, 64, dtype="fp16"),
    sdpa_record(1, 128, 32, 8, 64, dtype="bfloat16"),
    sdpa_record(1, 128, 32, 8, 64, layout="col_major"),
    sdpa_record(1, 128, 32, 8, 64, layout="bf16"),
    sdpa_record(0, 128, 32, 8, 64),
    sdpa_record(1, 0, 32, 8, 64),
    sdpa_record(1, 128, 0, 8, 64),
    sdpa_record(1, 128, 32, 0, 64),
    sdpa_record(1, 128, 32, 8, 0),
    sdpa_record(0, 0, 0, 0, 0),
    sdpa_record(0, MAX_INTEGER, 32, 8, 64),
    sdpa_record(2, 1, 32, 8, 64),
    sdpa_record(128, 127, 32, 8, 64),
    sdpa_record(MAX_INTEGER, MAX_INTEGER - 1, 1, 1, 1),
    sdpa_record(1, 1, 6, 4, 2),
    sdpa_record(1, 1, 1, 2, 1),
    sdpa_record(1, 128, 32, 3, 64),
    sdpa_record(2, 1, 6, 4, 2),
    sdpa_record(1, 128, 32, 8, 64, dtype="fp32", layout="col_major"),
    sdpa_record(2, 1, 32, 8, 64, dtype="fp32"),
]
OPTIONAL_MEMBERS = [
    {"ext": {"variant": "a"}},
    {"ext": {"m": 0, "l": 1, "capacity": 4096, "kind": "other", "position": 127}},
    {"label": "sdpa at T = 1, L = 128"},
    {"ext": {"variant": "a"}, "label": "x"},
]
REFUSED = [
    None,
    [],
    "sdpa_kv_cache",
    {},
    {k: v for k, v in RECORD.items() if k != "dtype"},
    dict(RECORD, unknown=1),
    dict(RECORD, schema_version=2),
    dict(RECORD, dtype="BF16"),
    dict(RECORD, layout="row-major"),
    dict(RECORD, kind="sdpa"),
    dict(RECORD, kind="attention"),
    dict(RECORD, kind="sdpa_kv_cache_bf16"),
    dict(RECORD, kind="SDPA_KV_CACHE"),
    dict(RECORD, shape={"m": 1, "h": 32, "h_kv": 8, "d": 64}),
    dict(RECORD, shape={"m": 1, "capacity": 128, "h": 32, "h_kv": 8, "d": 64}),
    dict(RECORD, shape={"m": 1, "l": 128, "h": 32, "h_kv": 8, "d": 64, "p": 127}),
    dict(RECORD, shape={"m": 1, "h": 32, "d": 64}),
    sdpa_record(True, 128, 32, 8, 64),
    sdpa_record(1, -1, 32, 8, 64),
    sdpa_record(MAX_INTEGER + 1, 128, 32, 8, 64),
    sdpa_record(1, 128, 32, 8.0, 64),
    dict(RECORD, ext={}),
    dict(RECORD, label=""),
]


@pytest.mark.parametrize(
    "shape",
    [
        *SHAPES,
        *SMALL_SHAPES,
        (MAX_INTEGER, MAX_INTEGER, MAX_INTEGER, MAX_INTEGER, MAX_INTEGER),
    ],
)
def test_record_of_this_contract_is_covered(shape):
    assert covers(op_signature_record(*shape)) is True


@pytest.mark.parametrize("record", NOT_COVERED, ids=repr)
def test_record_failing_a_condition_is_valid_and_not_covered(record):
    assert op_signature_key(record).name.startswith("sdpa_kv_cache-")
    assert covers(record) is False


@pytest.mark.parametrize(
    "record",
    [GEMM_RECORD, RMSNORM_RECORD, ADD_RECORD, SWIGLU_RECORD, ROPE_RECORD],
    ids=repr,
)
@pytest.mark.parametrize("dtype", ["bf16", "fp32"])
def test_record_of_another_known_kind_is_not_covered(record, dtype):
    record = dict(record, dtype=dtype)
    assert op_signature_key(record).name.startswith(record["kind"] + "-")
    assert covers(record) is False


@pytest.mark.parametrize(
    "contract", OTHER_CONTRACTS, ids=lambda module: module.__name__
)
@pytest.mark.parametrize("shape", [*SHAPES, *SMALL_SHAPES])
@pytest.mark.parametrize("dtype", ["bf16", "fp32"])
def test_other_contracts_do_not_cover_a_record_of_this_kind(contract, shape, dtype):
    record = dict(op_signature_record(*shape), dtype=dtype)
    assert contract.covers(record) is False


def test_record_of_another_kind_is_not_covered(monkeypatch):
    members = dict(keys._SHAPE_MEMBERS, other=frozenset(DIMENSIONS))
    monkeypatch.setattr(keys, "_SHAPE_MEMBERS", members)
    record = dict(RECORD, kind="other")
    assert op_signature_key(record).name.startswith("other-")
    assert covers(record) is False
    assert covers(RECORD) is True


@pytest.mark.parametrize("members", OPTIONAL_MEMBERS, ids=repr)
def test_ext_and_label_do_not_change_the_answer(members):
    assert covers(dict(RECORD, **members)) is True
    for record in NOT_COVERED:
        assert covers(dict(record, **members)) is False


@pytest.mark.parametrize("argument", REFUSED, ids=repr)
def test_argument_that_is_no_valid_record_is_refused(argument):
    with pytest.raises(InvalidRecordError) as caught:
        op_signature_key(argument)
    expected = str(caught.value)
    with pytest.raises(InvalidRecordError) as caught:
        covers(argument)
    assert type(caught.value) is InvalidRecordError
    assert str(caught.value) == expected


@pytest.mark.parametrize(
    "record",
    [
        RECORD,
        GEMM_RECORD,
        RMSNORM_RECORD,
        ADD_RECORD,
        SWIGLU_RECORD,
        ROPE_RECORD,
        *NOT_COVERED,
    ],
    ids=repr,
)
def test_covers_does_not_modify_its_argument_and_repeats_its_answer(record):
    argument = dict(copy.deepcopy(record), ext={"variant": "a"}, label="x")
    before = copy.deepcopy(argument)
    first = covers(argument)
    assert argument == before
    assert covers(argument) is first


def test_covers_takes_one_argument():
    assert list(inspect.signature(covers).parameters) == ["record"]
    assert covers(record=RECORD) is True
    for args, kwargs in [((), {}), ((RECORD, RECORD), {}), ((2, 3, 4, 2, 5), {})]:
        with pytest.raises(TypeError):
            covers(*args, **kwargs)


def test_public_names_of_the_module():
    public = {
        name
        for name, value in vars(sdpa_kv_cache_bf16_contract).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {
        "KIND",
        "DTYPE",
        "LAYOUT",
        "LANGUAGE",
        "PROTOTYPE",
        "SHAPES",
        "INPUT_PATTERNS",
        "covers",
        "op_signature_record",
        "task_contract",
    }
    for function in FUNCTIONS:
        assert list(inspect.signature(function).parameters) == DIMENSIONS


def test_module_imports_keys_only_and_is_named_by_no_other_module():
    own = Path(sdpa_kv_cache_bf16_contract.__file__)
    text = own.read_text(encoding="utf-8")
    assert imported_modules(own) == {"reprlib", "hilclaw", "hilclaw.keys"}
    for name in OTHER_MODULE_NAMES:
        assert name not in text
    assert "__main__" not in text
    assert not hasattr(sdpa_kv_cache_bf16_contract, "main")
    for path in sorted(own.parent.rglob("*.py")):
        if path != own:
            text = path.read_text(encoding="utf-8")
            assert "sdpa_kv_cache_bf16_contract" not in text, path


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    op_signature_record(2, 3, 4, 2, 5)
    task_contract(2, 3, 4, 2, 5)
    covers(RECORD)
    for function in FUNCTIONS:
        with pytest.raises(InvalidRecordError):
            function(0, 3, 4, 2, 5)
        with pytest.raises(InvalidRecordError):
            function(3, 2, 4, 2, 5)
        with pytest.raises(InvalidRecordError):
            function(1, 1, 6, 4, 2)
    with pytest.raises(InvalidRecordError):
        covers({})
    assert list(tmp_path.iterdir()) == []
