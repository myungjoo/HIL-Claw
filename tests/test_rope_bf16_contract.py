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
    spec,
    swiglu_bf16_contract,
)
from hilclaw.keys import MAX_INTEGER, InvalidRecordError, op_signature_key
from hilclaw.rope_bf16_contract import (
    DTYPE,
    KIND,
    LANGUAGE,
    LAYOUT,
    PROTOTYPE,
    SHAPES,
    TABLE_DTYPE,
    X_PATTERNS,
    covers,
    op_signature_record,
    task_contract,
)

# ADR-0161 decision 9, copied from the record.
ADR_PROTOTYPE = "void hilclaw_rope_bf16(size_t m, size_t h, size_t d, const uint16_t *restrict x, const float *restrict freqs_cis, uint16_t *restrict out);"

# ADR-0161 decision 10, copied from the record.
ADR_CONTRACT = json.loads(
    """
{
  "language": "c",
  "prototype": "void hilclaw_rope_bf16(size_t m, size_t h, size_t d, const uint16_t *restrict x, const float *restrict freqs_cis, uint16_t *restrict out);",
  "operands": [
    {"name": "x", "role": "input", "dtype": "bf16", "shape": [1, 8, 64]},
    {"name": "freqs_cis", "role": "input", "dtype": "fp32", "shape": [1, 64]},
    {"name": "out", "role": "output", "dtype": "bf16", "shape": [1, 8, 64]}
  ]
}
"""
)

# ADR-0161 decision 14, copied from the record.
ADR_RECORD = json.loads(
    '{"schema_version": 1, "kind": "rope", "shape": {"m": 1, "h": 8, "d": 64}, '
    '"dtype": "bf16", "layout": "row_major"}'
)
ADR_CANONICAL = b'{"dtype":"bf16","kind":"rope","layout":"row_major","schema_version":1,"shape":{"d":64,"h":8,"m":1}}'
ADR_DIGEST = "c797475e043d41569f5a69878631c9c59bde735b28fc614aab427b1d9cd4006a"
ADR_TABLE = [
    ((1, 32, 64), "rope-1fafc8411a47dc19"),
    ((128, 32, 64), "rope-9d2410e4438eac67"),
    ((2048, 32, 64), "rope-7e13c7020a9b17fb"),
    ((1, 8, 64), "rope-c797475e043d4156"),
    ((128, 8, 64), "rope-74ab3d4ad2c2e42c"),
    ((2048, 8, 64), "rope-125adcdf54641cca"),
]

RECORD = {
    "schema_version": 1,
    "kind": "rope",
    "shape": {"m": 1, "h": 8, "d": 64},
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

FUNCTIONS = [op_signature_record, task_contract]
DIMENSIONS = ["m", "h", "d"]
SHAPE = {"m": 3, "h": 5, "d": 2}
OTHER_CONTRACTS = [
    gemm_contract,
    gemm_bf16_contract,
    rmsnorm_bf16_contract,
    elementwise_add_bf16_contract,
    swiglu_bf16_contract,
]
OTHER_MODULE_NAMES = [
    "gemm_contract",
    "gemm_bf16_contract",
    "rmsnorm_bf16_contract",
    "elementwise_add_bf16_contract",
    "swiglu_bf16_contract",
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
ODD_D = [1, 3, 63, MAX_INTEGER]


def synthetic_spec(m, h, d):
    hw = {
        "schema_version": 1,
        "accelerator": "synthetic_accel",
        "revision": "synthetic-rev-A",
        "toolchain": {"synthetic_cc": "0.0.1-synthetic"},
        "host": {"cpu": "synthetic cpu", "os": "synthetic os"},
        "hw_source": "in_house",
    }
    op = op_signature_record(m, h, d)
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
            "contract": task_contract(m, h, d),
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


def rope_record(m, h, d, **members):
    return dict(RECORD, shape={"m": m, "h": h, "d": d}, **members)


def test_constants_are_those_of_the_record():
    assert (KIND, DTYPE, TABLE_DTYPE, LAYOUT, LANGUAGE) == (
        "rope",
        "bf16",
        "fp32",
        "row_major",
        "c",
    )
    assert PROTOTYPE == ADR_PROTOTYPE
    assert type(PROTOTYPE) is str
    assert "\n" not in PROTOTYPE and "  " not in PROTOTYPE
    assert PROTOTYPE.endswith(");")
    assert PROTOTYPE == ADR_CONTRACT["prototype"]
    assert PROTOTYPE.count("restrict") == 3
    assert (
        PROTOTYPE.index(" x,") < PROTOTYPE.index("freqs_cis") < PROTOTYPE.index("out)")
    )
    assert "const float *restrict freqs_cis" in PROTOTYPE


def test_k_record_at_t_1_has_the_canonical_form_and_digest_of_the_record():
    record = op_signature_record(1, 8, 64)
    assert record == RECORD == ADR_RECORD
    assert type(record) is dict and type(record["shape"]) is dict
    assert list(record) == ["schema_version", "kind", "shape", "dtype", "layout"]
    assert list(record["shape"]) == DIMENSIONS
    assert record["schema_version"] == keys.SCHEMA_VERSION
    key = op_signature_key(record)
    assert key.canonical == ADR_CANONICAL
    assert key.digest == ADR_DIGEST
    assert key.name == "rope-c797475e043d4156"


def test_shapes_give_the_six_names_of_the_record_in_its_order():
    assert list(SHAPES) == [shape for shape, _ in ADR_TABLE]
    names = [op_signature_key(op_signature_record(*shape)).name for shape in SHAPES]
    assert names == [name for _, name in ADR_TABLE]


def test_shapes_are_six_different_shapes():
    assert type(SHAPES) is tuple
    assert len(SHAPES) == 6
    assert len(set(SHAPES)) == 6
    for shape in SHAPES:
        assert type(shape) is tuple and len(shape) == 3
        assert all(type(value) is int for value in shape)
    assert [m for m, _, _ in SHAPES] == [1, 128, 2048, 1, 128, 2048]
    assert [h for _, h, _ in SHAPES] == [32, 32, 32, 8, 8, 8]
    assert {d for _, _, d in SHAPES} == {64}


def test_k_record_at_t_1_has_the_task_contract_of_the_record():
    contract = task_contract(1, 8, 64)
    assert contract == ADR_CONTRACT
    assert type(contract) is dict and type(contract["operands"]) is list
    assert list(contract) == ["language", "prototype", "operands"]
    for entry in contract["operands"]:
        assert type(entry) is dict and type(entry["shape"]) is list
        assert list(entry) == ["name", "role", "dtype", "shape"]


def test_each_dimension_is_placed_in_its_operand_position():
    assert op_signature_record(3, 5, 2)["shape"] == SHAPE
    assert task_contract(3, 5, 2)["operands"] == [
        {"name": "x", "role": "input", "dtype": "bf16", "shape": [3, 5, 2]},
        {"name": "freqs_cis", "role": "input", "dtype": "fp32", "shape": [3, 2]},
        {"name": "out", "role": "output", "dtype": "bf16", "shape": [3, 5, 2]},
    ]


def test_arguments_may_be_given_by_name():
    assert op_signature_record(d=2, h=5, m=3) == op_signature_record(3, 5, 2)
    assert task_contract(d=2, h=5, m=3) == task_contract(3, 5, 2)


@pytest.mark.parametrize(
    "shape",
    [(1, 1, 2), (3, 5, 2), (MAX_INTEGER, MAX_INTEGER, MAX_INTEGER - 1), *SHAPES],
)
def test_spec_built_from_the_returned_values_is_valid(shape):
    document = synthetic_spec(*shape)
    spec.validate(document)
    assert document["task"]["contract"]["prototype"] == ADR_PROTOTYPE
    m, h, d = shape
    shapes = [entry["shape"] for entry in document["task"]["contract"]["operands"]]
    assert shapes == [[m, h, d], [m, d], [m, h, d]]


def test_spec_with_the_table_shape_of_the_record_refusal_is_refused():
    document = synthetic_spec(1, 8, 64)
    document["task"]["contract"]["operands"][1]["shape"] = [1, 32]
    with pytest.raises(
        spec.InvalidSpecError,
        match=r"^task\.contract\.operands\[1\]\.shape\[1\]: must be a value of "
        r"task\.op_signature\.record\.shape, got 32",
    ):
        spec.validate(document)


def test_x_patterns_are_256_ascending_distinct_16_bit_integers():
    assert type(X_PATTERNS) is tuple
    assert len(X_PATTERNS) == 256
    assert len(set(X_PATTERNS)) == 256
    assert list(X_PATTERNS) == sorted(X_PATTERNS)
    for pattern in X_PATTERNS:
        assert type(pattern) is int
        assert 0 <= pattern <= 0xFFFF
    assert X_PATTERNS[0] == 0x3F00 and X_PATTERNS[-1] == 0xBF7F
    assert set(X_PATTERNS) == set(range(0x3F00, 0x3F80)) | set(range(0xBF00, 0xBF80))


def test_x_patterns_are_the_value_set_of_the_record():
    values = [widened(pattern) for pattern in X_PATTERNS]
    for value in values:
        assert math.isfinite(value)
        assert 0.5 <= abs(value) < 1
    expected = {sign * (0.5 + j / 256) for sign in (1, -1) for j in range(128)}
    assert set(values) == expected
    assert len({abs(value) for value in values}) == 128
    for magnitude in {abs(value) for value in values}:
        assert magnitude in values and -magnitude in values


def test_x_patterns_hold_every_bf16_value_of_their_range():
    in_range = {
        pattern
        for pattern in range(0x10000)
        if math.isfinite(widened(pattern)) and 0.5 <= abs(widened(pattern)) < 1
    }
    assert set(X_PATTERNS) == in_range
    for outside in (0x3EFF, 0x3F80, 0xBEFF, 0xBF80):
        assert outside not in X_PATTERNS


@pytest.mark.parametrize("function", FUNCTIONS)
def test_two_calls_give_equal_and_separate_results(function):
    first, second = function(3, 5, 2), function(3, 5, 2)
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
    operands = task_contract(3, 5, 2)["operands"]
    shapes = [entry["shape"] for entry in operands]
    assert len({id(shape) for shape in shapes}) == 3
    shapes[0].append(1)
    assert operands[1]["shape"] == [3, 2] and operands[2]["shape"] == [3, 5, 2]


def test_changing_returned_values_changes_nothing_else():
    record = op_signature_record(3, 5, 2)
    record["shape"]["m"] = 9
    record["dtype"] = "fp32"
    contract = task_contract(3, 5, 2)
    expected = task_contract(3, 5, 2)
    contract["operands"][0]["shape"][0] = 9
    contract["operands"][1]["shape"].append(1)
    contract["operands"][1]["dtype"] = "bf16"
    contract["operands"].pop()
    contract["prototype"] = "changed"
    assert op_signature_record(3, 5, 2)["shape"] == SHAPE
    assert op_signature_record(3, 5, 2)["dtype"] == "bf16"
    assert task_contract(3, 5, 2) == expected
    assert (LANGUAGE, PROTOTYPE, DTYPE, TABLE_DTYPE) == (
        "c",
        ADR_PROTOTYPE,
        "bf16",
        "fp32",
    )


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
@pytest.mark.parametrize("d", ODD_D)
def test_odd_d_is_refused(function, d):
    with pytest.raises(InvalidRecordError) as caught:
        function(3, 5, d)
    assert str(caught.value) == f"shape.d: must be even, got {d}"
    assert type(caught.value) is InvalidRecordError


@pytest.mark.parametrize("function", FUNCTIONS)
def test_first_bad_dimension_is_the_one_named(function):
    with pytest.raises(InvalidRecordError, match=r"^shape\.m: "):
        function(0, 0, 0)
    with pytest.raises(InvalidRecordError, match=r"^shape\.h: "):
        function(1, 0, 0)
    with pytest.raises(InvalidRecordError, match=r"^shape\.d: must be an integer"):
        function(1, 1, 0)
    with pytest.raises(InvalidRecordError, match=r"^shape\.h: "):
        function(1, 0, 3)
    with pytest.raises(InvalidRecordError, match=r"^shape\.d: must be even"):
        function(1, 1, 3)


@pytest.mark.parametrize("function", FUNCTIONS)
def test_long_bad_value_is_shortened_in_the_message(function):
    with pytest.raises(InvalidRecordError) as caught:
        function(3, 5, "x" * 10_000)
    assert len(str(caught.value)) < 200


@pytest.mark.parametrize("function", FUNCTIONS)
@pytest.mark.parametrize(
    ("args", "kwargs"),
    [
        ((), {}),
        ((3,), {}),
        ((3, 5), {}),
        ((3, 5), {"m": 3}),
        ((3, 5, 2, 9), {}),
        ((3, 5, 2), {"position": 0}),
        ((3, 5, 2), {"rope_theta": 500000.0}),
        ((3, 5), {"n": 2}),
    ],
)
def test_missing_or_surplus_argument_is_a_type_error(function, args, kwargs):
    with pytest.raises(TypeError):
        function(*args, **kwargs)


def test_zero_and_odd_d_are_accepted_by_keys_and_refused_here():
    for record in (rope_record(0, 5, 2), rope_record(3, 5, 63)):
        assert op_signature_key(record).name.startswith("rope-")
        assert covers(record) is False
    with pytest.raises(InvalidRecordError):
        op_signature_record(0, 5, 2)
    with pytest.raises(InvalidRecordError):
        task_contract(3, 5, 63)


NOT_COVERED = [
    rope_record(1, 8, 64, dtype="fp32"),
    rope_record(1, 8, 64, dtype="fp16"),
    rope_record(1, 8, 64, dtype="bfloat16"),
    rope_record(1, 8, 64, layout="col_major"),
    rope_record(1, 8, 64, layout="bf16"),
    rope_record(0, 8, 64),
    rope_record(1, 0, 64),
    rope_record(1, 8, 0),
    rope_record(0, 0, 0),
    rope_record(0, MAX_INTEGER, 64),
    rope_record(1, 8, 1),
    rope_record(1, 8, 63),
    rope_record(1, 8, MAX_INTEGER),
    rope_record(0, 8, 63),
    rope_record(1, 8, 64, dtype="fp32", layout="col_major"),
    rope_record(1, 8, 63, dtype="fp32"),
]
OPTIONAL_MEMBERS = [
    {"ext": {"variant": "a"}},
    {"ext": {"m": 0, "d": 3, "dtype": "fp32", "kind": "other", "position": 127}},
    {"label": "rope_k at T = 1"},
    {"ext": {"variant": "a"}, "label": "x"},
]
REFUSED = [
    None,
    [],
    "rope",
    {},
    {k: v for k, v in RECORD.items() if k != "dtype"},
    dict(RECORD, unknown=1),
    dict(RECORD, schema_version=2),
    dict(RECORD, dtype="BF16"),
    dict(RECORD, layout="row-major"),
    dict(RECORD, kind="sdpa"),
    dict(RECORD, kind="rotary"),
    dict(RECORD, kind="rope_q"),
    dict(RECORD, kind="RoPE"),
    dict(RECORD, shape={"m": 1, "h": 8}),
    dict(RECORD, shape={"m": 1, "n": 64}),
    dict(RECORD, shape={"m": 1, "h": 8, "d": 64, "p": 0}),
    rope_record(True, 8, 64),
    rope_record(1, -1, 64),
    rope_record(MAX_INTEGER + 1, 8, 64),
    rope_record(1, 8, 64.0),
    dict(RECORD, ext={}),
    dict(RECORD, label=""),
]


@pytest.mark.parametrize(
    "shape",
    [*SHAPES, (1, 1, 2), (3, 5, 2), (MAX_INTEGER, MAX_INTEGER, MAX_INTEGER - 1)],
)
def test_record_of_this_contract_is_covered(shape):
    assert covers(op_signature_record(*shape)) is True


@pytest.mark.parametrize("record", NOT_COVERED, ids=repr)
def test_record_failing_a_condition_is_valid_and_not_covered(record):
    assert op_signature_key(record).name.startswith("rope-")
    assert covers(record) is False


@pytest.mark.parametrize(
    "record", [GEMM_RECORD, RMSNORM_RECORD, ADD_RECORD, SWIGLU_RECORD], ids=repr
)
@pytest.mark.parametrize("dtype", ["bf16", "fp32"])
def test_record_of_another_known_kind_is_not_covered(record, dtype):
    record = dict(record, dtype=dtype)
    assert op_signature_key(record).name.startswith(record["kind"] + "-")
    assert covers(record) is False


@pytest.mark.parametrize(
    "contract", OTHER_CONTRACTS, ids=lambda module: module.__name__
)
@pytest.mark.parametrize("shape", [*SHAPES, (1, 1, 2), (3, 5, 2)])
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
    [RECORD, GEMM_RECORD, RMSNORM_RECORD, ADD_RECORD, SWIGLU_RECORD, *NOT_COVERED],
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
    for args, kwargs in [((), {}), ((RECORD, RECORD), {}), ((3, 5, 2), {})]:
        with pytest.raises(TypeError):
            covers(*args, **kwargs)


def test_public_names_of_the_module():
    public = {
        name
        for name, value in vars(rope_bf16_contract).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {
        "KIND",
        "DTYPE",
        "TABLE_DTYPE",
        "LAYOUT",
        "LANGUAGE",
        "PROTOTYPE",
        "SHAPES",
        "X_PATTERNS",
        "covers",
        "op_signature_record",
        "task_contract",
    }
    for function in FUNCTIONS:
        assert list(inspect.signature(function).parameters) == DIMENSIONS


def test_module_imports_keys_only_and_is_bound_by_the_model_binding_only():
    own = Path(rope_bf16_contract.__file__)
    text = own.read_text(encoding="utf-8")
    binders = (own.parent / "model_binding.py",)
    assert imported_modules(own) == {"reprlib", "hilclaw", "hilclaw.keys"}
    for name in OTHER_MODULE_NAMES:
        assert name not in text
    assert "__main__" not in text
    assert not hasattr(rope_bf16_contract, "main")
    for binder in binders:
        assert "rope_bf16_contract" in binder.read_text(encoding="utf-8")
    for path in sorted(own.parent.rglob("*.py")):
        if path != own and path not in binders:
            assert "rope_bf16_contract" not in path.read_text(encoding="utf-8"), path


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    op_signature_record(3, 5, 2)
    task_contract(3, 5, 2)
    covers(RECORD)
    for function in FUNCTIONS:
        with pytest.raises(InvalidRecordError):
            function(0, 5, 2)
        with pytest.raises(InvalidRecordError):
            function(3, 5, 3)
    with pytest.raises(InvalidRecordError):
        covers({})
    assert list(tmp_path.iterdir()) == []
