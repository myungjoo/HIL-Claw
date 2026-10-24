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
    spec,
    swiglu_bf16_contract,
)
from hilclaw.keys import MAX_INTEGER, InvalidRecordError, op_signature_key
from hilclaw.swiglu_bf16_contract import (
    DTYPE,
    GATE_PATTERNS,
    KIND,
    LANGUAGE,
    LAYOUT,
    PROTOTYPE,
    SHAPES,
    UP_PATTERNS,
    covers,
    op_signature_record,
    task_contract,
)

# ADR-0160 decision 6, copied from the record.
ADR_PROTOTYPE = "void hilclaw_swiglu_bf16(size_t m, size_t n, const uint16_t *restrict gate, const uint16_t *restrict up, uint16_t *restrict out);"

# ADR-0160 decision 7, copied from the record.
ADR_CONTRACT = json.loads(
    """
{
  "language": "c",
  "prototype": "void hilclaw_swiglu_bf16(size_t m, size_t n, const uint16_t *restrict gate, const uint16_t *restrict up, uint16_t *restrict out);",
  "operands": [
    {"name": "gate", "role": "input", "dtype": "bf16", "shape": [1, 8192]},
    {"name": "up", "role": "input", "dtype": "bf16", "shape": [1, 8192]},
    {"name": "out", "role": "output", "dtype": "bf16", "shape": [1, 8192]}
  ]
}
"""
)

# ADR-0160 decision 11, copied from the record.
ADR_RECORD = json.loads(
    '{"schema_version": 1, "kind": "swiglu", "shape": {"m": 1, "n": 8192}, '
    '"dtype": "bf16", "layout": "row_major"}'
)
ADR_CANONICAL = b'{"dtype":"bf16","kind":"swiglu","layout":"row_major","schema_version":1,"shape":{"m":1,"n":8192}}'
ADR_DIGEST = "7b82bc7d69cda1e0fd3794adbe3bce2274830ff1c53b3c20997ae095e352dc29"
ADR_TABLE = [
    ((1, 8192), "swiglu-7b82bc7d69cda1e0"),
    ((32, 8192), "swiglu-ee76c0d3e36f20f7"),
    ((512, 8192), "swiglu-a1d727f15ac574e0"),
]

RECORD = {
    "schema_version": 1,
    "kind": "swiglu",
    "shape": {"m": 1, "n": 8192},
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
RMSNORM_RECORD = dict(RECORD, kind="rmsnorm")
ADD_RECORD = dict(RECORD, kind="elementwise_add")

FUNCTIONS = [op_signature_record, task_contract]
DIMENSIONS = ["m", "n"]
SHAPE = {"m": 3, "n": 7}
OTHER_CONTRACTS = [
    gemm_contract,
    gemm_bf16_contract,
    rmsnorm_bf16_contract,
    elementwise_add_bf16_contract,
]
OTHER_MODULE_NAMES = [
    "gemm_contract",
    "gemm_bf16_contract",
    "rmsnorm_bf16_contract",
    "elementwise_add_bf16_contract",
]


class IntSubclass(int):
    pass


BAD_DIMENSIONS = [
    0,
    -1,
    -(2**53),
    MAX_INTEGER + 1,
    True,
    False,
    1.0,
    "1",
    None,
    IntSubclass(1),
    [1],
    b"1",
]


def synthetic_spec(m, n):
    hw = {
        "schema_version": 1,
        "accelerator": "synthetic_accel",
        "revision": "synthetic-rev-A",
        "toolchain": {"synthetic_cc": "0.0.1-synthetic"},
        "host": {"cpu": "synthetic cpu", "os": "synthetic os"},
        "hw_source": "in_house",
    }
    op = op_signature_record(m, n)
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
            "contract": task_contract(m, n),
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


def swiglu_record(m, n, **members):
    return dict(RECORD, shape={"m": m, "n": n}, **members)


def test_constants_are_those_of_the_record():
    assert (KIND, DTYPE, LAYOUT, LANGUAGE) == (
        "swiglu",
        "bf16",
        "row_major",
        "c",
    )
    assert PROTOTYPE == ADR_PROTOTYPE
    assert type(PROTOTYPE) is str
    assert "\n" not in PROTOTYPE and "  " not in PROTOTYPE
    assert PROTOTYPE.endswith(");")
    assert PROTOTYPE == ADR_CONTRACT["prototype"]
    assert "float" not in PROTOTYPE


def test_first_shape_has_the_canonical_form_and_digest_of_the_record():
    record = op_signature_record(1, 8192)
    assert record == RECORD == ADR_RECORD
    assert type(record) is dict and type(record["shape"]) is dict
    assert list(record) == ["schema_version", "kind", "shape", "dtype", "layout"]
    assert record["schema_version"] == keys.SCHEMA_VERSION
    key = op_signature_key(record)
    assert key.canonical == ADR_CANONICAL
    assert key.digest == ADR_DIGEST
    assert key.name == "swiglu-7b82bc7d69cda1e0"


def test_shapes_give_the_three_names_of_the_record_in_its_order():
    assert list(SHAPES) == [shape for shape, _ in ADR_TABLE]
    names = [op_signature_key(op_signature_record(*shape)).name for shape in SHAPES]
    assert names == [name for _, name in ADR_TABLE]


def test_shapes_are_three_different_shapes():
    assert type(SHAPES) is tuple
    assert len(SHAPES) == 3
    assert len(set(SHAPES)) == 3
    for shape in SHAPES:
        assert type(shape) is tuple and len(shape) == 2
        assert all(type(value) is int for value in shape)
    assert [m for m, _ in SHAPES] == [1, 32, 512]
    assert {n for _, n in SHAPES} == {8192}


def test_first_shape_has_the_task_contract_of_the_record():
    contract = task_contract(1, 8192)
    assert contract == ADR_CONTRACT
    assert type(contract) is dict and type(contract["operands"]) is list
    assert list(contract) == ["language", "prototype", "operands"]
    for entry in contract["operands"]:
        assert type(entry) is dict and type(entry["shape"]) is list
        assert list(entry) == ["name", "role", "dtype", "shape"]


def test_each_dimension_is_placed_in_its_operand_position():
    assert op_signature_record(3, 7)["shape"] == SHAPE
    assert task_contract(3, 7)["operands"] == [
        {"name": "gate", "role": "input", "dtype": "bf16", "shape": [3, 7]},
        {"name": "up", "role": "input", "dtype": "bf16", "shape": [3, 7]},
        {"name": "out", "role": "output", "dtype": "bf16", "shape": [3, 7]},
    ]


def test_arguments_may_be_given_by_name():
    assert op_signature_record(n=7, m=3) == op_signature_record(3, 7)
    assert task_contract(n=7, m=3) == task_contract(3, 7)


@pytest.mark.parametrize("shape", [(1, 1), (3, 7), (MAX_INTEGER, MAX_INTEGER), *SHAPES])
def test_spec_built_from_the_returned_values_is_valid(shape):
    document = synthetic_spec(*shape)
    spec.validate(document)
    assert document["task"]["contract"]["prototype"] == ADR_PROTOTYPE
    m, n = shape
    shapes = [entry["shape"] for entry in document["task"]["contract"]["operands"]]
    assert shapes == [[m, n], [m, n], [m, n]]


def test_spec_with_a_wrong_operand_shape_is_refused():
    document = synthetic_spec(1, 8192)
    document["task"]["contract"]["operands"][1]["shape"] = [1, 8193]
    with pytest.raises(
        spec.InvalidSpecError, match=r"^task\.contract\.operands\[1\]\.shape\[1\]: "
    ):
        spec.validate(document)


def assert_ascending_distinct_16_bit_integers(patterns, count):
    assert type(patterns) is tuple
    assert len(patterns) == count
    assert len(set(patterns)) == count
    assert list(patterns) == sorted(patterns)
    for pattern in patterns:
        assert type(pattern) is int
        assert 0 <= pattern <= 0xFFFF


def assert_both_signs_of_every_magnitude(values):
    for magnitude in {abs(value) for value in values}:
        assert magnitude in values and -magnitude in values


def test_gate_patterns_are_1024_ascending_distinct_16_bit_integers():
    assert_ascending_distinct_16_bit_integers(GATE_PATTERNS, 1024)
    assert GATE_PATTERNS[0] == 0x3F00 and GATE_PATTERNS[-1] == 0xC0FF
    assert set(GATE_PATTERNS) == set(range(0x3F00, 0x4100)) | set(range(0xBF00, 0xC100))


def test_gate_patterns_are_the_value_set_of_the_record():
    values = [widened(pattern) for pattern in GATE_PATTERNS]
    for value in values:
        assert math.isfinite(value)
        assert 0.5 <= abs(value) < 8
    assert max(abs(value) for value in values) == 7.96875
    assert min(abs(value) for value in values) == 0.5
    assert_both_signs_of_every_magnitude(values)
    assert len({abs(value) for value in values}) == 512


def test_gate_patterns_hold_every_bf16_value_of_their_range():
    in_range = {
        pattern
        for pattern in range(0x10000)
        if math.isfinite(widened(pattern)) and 0.5 <= abs(widened(pattern)) < 8
    }
    assert set(GATE_PATTERNS) == in_range
    for outside in (0x3EFF, 0x4100, 0xBEFF, 0xC100):
        assert outside not in GATE_PATTERNS
    for pattern in range(0x3F00, 0x4100):
        assert pattern in GATE_PATTERNS and pattern | 0x8000 in GATE_PATTERNS


def test_up_patterns_are_256_ascending_distinct_16_bit_integers():
    assert_ascending_distinct_16_bit_integers(UP_PATTERNS, 256)
    assert UP_PATTERNS[0] == 0x3F00 and UP_PATTERNS[-1] == 0xBF7F
    assert set(UP_PATTERNS) == set(range(0x3F00, 0x3F80)) | set(range(0xBF00, 0xBF80))


def test_up_patterns_are_the_value_set_of_the_record():
    values = [widened(pattern) for pattern in UP_PATTERNS]
    for value in values:
        assert math.isfinite(value)
        assert 0.5 <= abs(value) < 1
    expected = {sign * (0.5 + j / 256) for sign in (1, -1) for j in range(128)}
    assert set(values) == expected
    assert len({abs(value) for value in values}) == 128
    assert_both_signs_of_every_magnitude(values)


def test_up_patterns_are_a_subset_of_gate_patterns():
    assert set(UP_PATTERNS) < set(GATE_PATTERNS)


@pytest.mark.parametrize("function", FUNCTIONS)
def test_two_calls_give_equal_and_separate_results(function):
    first, second = function(3, 7), function(3, 7)
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
    operands = task_contract(3, 7)["operands"]
    shapes = [entry["shape"] for entry in operands]
    assert len({id(shape) for shape in shapes}) == 3
    shapes[0].append(1)
    assert operands[1]["shape"] == [3, 7] and operands[2]["shape"] == [3, 7]


def test_changing_returned_values_changes_nothing_else():
    record = op_signature_record(3, 7)
    record["shape"]["m"] = 9
    record["dtype"] = "fp32"
    contract = task_contract(3, 7)
    expected = task_contract(3, 7)
    contract["operands"][0]["shape"][0] = 9
    contract["operands"][1]["shape"].append(1)
    contract["operands"][1]["dtype"] = "fp32"
    contract["operands"].pop()
    contract["prototype"] = "changed"
    assert op_signature_record(3, 7)["shape"] == SHAPE
    assert op_signature_record(3, 7)["dtype"] == "bf16"
    assert task_contract(3, 7) == expected
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
def test_first_bad_dimension_is_the_one_named(function):
    with pytest.raises(InvalidRecordError, match=r"^shape\.m: "):
        function(0, 0)
    with pytest.raises(InvalidRecordError, match=r"^shape\.n: "):
        function(1, 0)


@pytest.mark.parametrize("function", FUNCTIONS)
def test_long_bad_value_is_shortened_in_the_message(function):
    with pytest.raises(InvalidRecordError) as caught:
        function(3, "x" * 10_000)
    assert len(str(caught.value)) < 200


@pytest.mark.parametrize("function", FUNCTIONS)
@pytest.mark.parametrize(
    ("args", "kwargs"),
    [
        ((), {}),
        ((3,), {}),
        ((3,), {"m": 3}),
        ((3, 7, 9), {}),
        ((3, 7), {"eps": 1e-05}),
        ((3, 7), {"k": 5}),
    ],
)
def test_missing_or_surplus_argument_is_a_type_error(function, args, kwargs):
    with pytest.raises(TypeError):
        function(*args, **kwargs)


def test_zero_is_accepted_by_keys_and_refused_here():
    record = swiglu_record(0, 1)
    assert op_signature_key(record).name.startswith("swiglu-")
    assert covers(record) is False
    with pytest.raises(InvalidRecordError):
        op_signature_record(0, 1)
    with pytest.raises(InvalidRecordError):
        task_contract(1, 0)


NOT_COVERED = [
    swiglu_record(3, 7, dtype="fp32"),
    swiglu_record(3, 7, dtype="fp16"),
    swiglu_record(3, 7, dtype="bfloat16"),
    swiglu_record(3, 7, layout="col_major"),
    swiglu_record(3, 7, layout="bf16"),
    swiglu_record(0, 7),
    swiglu_record(3, 0),
    swiglu_record(0, 0),
    swiglu_record(0, MAX_INTEGER),
    swiglu_record(3, 7, dtype="fp32", layout="col_major"),
    swiglu_record(0, 7, dtype="fp32"),
]
OPTIONAL_MEMBERS = [
    {"ext": {"variant": "a"}},
    {"ext": {"m": 0, "dtype": "fp32", "kind": "other", "k": 1}},
    {"label": "ffn activation at T = 1"},
    {"ext": {"variant": "a"}, "label": "x"},
]
REFUSED = [
    None,
    [],
    "swiglu",
    {},
    {k: v for k, v in RECORD.items() if k != "dtype"},
    dict(RECORD, unknown=1),
    dict(RECORD, schema_version=2),
    dict(RECORD, dtype="BF16"),
    dict(RECORD, layout="row-major"),
    dict(RECORD, kind="rope"),
    dict(RECORD, kind="silu"),
    dict(RECORD, kind="swiglu_activation"),
    dict(RECORD, kind="SwiGLU"),
    dict(RECORD, shape={"m": 3}),
    dict(RECORD, shape={"m": 3, "k": 5, "n": 7}),
    swiglu_record(True, 7),
    swiglu_record(3, -1),
    swiglu_record(MAX_INTEGER + 1, 7),
    swiglu_record(3, 7.0),
    dict(RECORD, ext={}),
    dict(RECORD, label=""),
]


@pytest.mark.parametrize("shape", [*SHAPES, (1, 1), (3, 7), (MAX_INTEGER, MAX_INTEGER)])
def test_record_of_this_contract_is_covered(shape):
    assert covers(op_signature_record(*shape)) is True


@pytest.mark.parametrize("record", NOT_COVERED, ids=repr)
def test_record_failing_a_condition_is_valid_and_not_covered(record):
    assert op_signature_key(record).name.startswith("swiglu-")
    assert covers(record) is False


@pytest.mark.parametrize("record", [GEMM_RECORD, RMSNORM_RECORD, ADD_RECORD], ids=repr)
@pytest.mark.parametrize("dtype", ["bf16", "fp32"])
def test_record_of_another_known_kind_is_not_covered(record, dtype):
    record = dict(record, dtype=dtype)
    assert op_signature_key(record).name.startswith(record["kind"] + "-")
    assert covers(record) is False


@pytest.mark.parametrize(
    "contract", OTHER_CONTRACTS, ids=lambda module: module.__name__
)
@pytest.mark.parametrize("shape", [*SHAPES, (1, 1), (3, 7)])
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
    "record", [RECORD, GEMM_RECORD, RMSNORM_RECORD, ADD_RECORD, *NOT_COVERED], ids=repr
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
    for args, kwargs in [((), {}), ((RECORD, RECORD), {}), ((3, 7), {})]:
        with pytest.raises(TypeError):
            covers(*args, **kwargs)


def test_public_names_of_the_module():
    public = {
        name
        for name, value in vars(swiglu_bf16_contract).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {
        "KIND",
        "DTYPE",
        "LAYOUT",
        "LANGUAGE",
        "PROTOTYPE",
        "SHAPES",
        "GATE_PATTERNS",
        "UP_PATTERNS",
        "covers",
        "op_signature_record",
        "task_contract",
    }
    for function in FUNCTIONS:
        assert list(inspect.signature(function).parameters) == DIMENSIONS


def test_module_imports_keys_only_and_is_bound_by_the_model_binding_only():
    own = Path(swiglu_bf16_contract.__file__)
    text = own.read_text(encoding="utf-8")
    binders = (own.parent / "model_binding.py",)
    assert imported_modules(own) == {"reprlib", "hilclaw", "hilclaw.keys"}
    for name in OTHER_MODULE_NAMES:
        assert name not in text
    assert "__main__" not in text
    assert not hasattr(swiglu_bf16_contract, "main")
    for binder in binders:
        assert "swiglu_bf16_contract" in binder.read_text(encoding="utf-8")
    for path in sorted(own.parent.rglob("*.py")):
        if path != own and path not in binders:
            assert "swiglu_bf16_contract" not in path.read_text(encoding="utf-8"), path


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    op_signature_record(3, 7)
    task_contract(3, 7)
    covers(RECORD)
    for function in FUNCTIONS:
        with pytest.raises(InvalidRecordError):
            function(0, 7)
    with pytest.raises(InvalidRecordError):
        covers({})
    assert list(tmp_path.iterdir()) == []
