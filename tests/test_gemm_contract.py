import ast
import copy
import inspect
import json
from pathlib import Path

import pytest

import hilclaw
from hilclaw import gemm_contract, keys, spec
from hilclaw.gemm_contract import (
    DTYPE,
    FIRST_SHAPES,
    KIND,
    LANGUAGE,
    LAYOUT,
    PROTOTYPE,
    covers,
    op_signature_record,
    task_contract,
)
from hilclaw.keys import MAX_INTEGER, InvalidRecordError, op_signature_key

# ADR-0008 decision 4, copied from the record.
ADR_PROTOTYPE = "void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c);"

# ADR-0008 decision 5, copied from the record.
ADR_CONTRACT = json.loads(
    """
{
  "language": "c",
  "prototype": "void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c);",
  "operands": [
    {"name": "a", "role": "input", "dtype": "fp32", "shape": [1, 2048]},
    {"name": "b", "role": "input", "dtype": "fp32", "shape": [2048, 8192]},
    {"name": "c", "role": "output", "dtype": "fp32", "shape": [1, 8192]}
  ]
}
"""
)

# ADR-0008 decision 9, copied from the record.
ADR_CANONICAL = b'{"dtype":"fp32","kind":"gemm","layout":"row_major","schema_version":1,"shape":{"k":2048,"m":1,"n":8192}}'
ADR_DIGEST = "485b9bc494d477ebc8c9f02f861c3795beadacfb4cf690680cfaecba09f2d431"
ADR_TABLE = [
    ((1, 2048, 8192), "gemm-485b9bc494d477eb"),
    ((32, 2048, 8192), "gemm-a463eb52b19cfa97"),
    ((512, 2048, 8192), "gemm-19d14734352e3486"),
    ((1, 8192, 2048), "gemm-d79390d121a2056a"),
    ((32, 8192, 2048), "gemm-f5de54ee1d6995e0"),
    ((512, 8192, 2048), "gemm-4b417959d34765af"),
    ((1, 2048, 3072), "gemm-446c3b3c15273a6a"),
    ((32, 2048, 3072), "gemm-e71a433ce31c1a8f"),
    ((512, 2048, 3072), "gemm-41e8dce9901bff41"),
    ((1, 2048, 2048), "gemm-a11d79d7b957a0af"),
    ((32, 2048, 2048), "gemm-dc8beaf05ddb998c"),
    ((512, 2048, 2048), "gemm-66f7a94f78826a41"),
]

# ADR-0037 walk-through, copied from the record.
ADR_0037_NO_ZERO = ((1, 2048, 8192), "gemm-485b9bc494d477eb")
ADR_0037_NOT_COVERED = [
    ((0, 2048, 8192), "gemm-d765fb955295628a"),
    ((1, 0, 8192), "gemm-ae3e9e269ea6e812"),
    ((0, 0, 0), "gemm-f5ed2636b2d123a9"),
]

# ADR-0041 walk-through, copied from the record.
ADR_0041_RECORD = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": {"m": 1, "k": 2048, "n": 8192},
    "dtype": "fp32",
    "layout": "row_major",
}
ADR_0041_NOT_COVERED = [
    {"dtype": "fp16"},
    {"layout": "col_major"},
    {"shape": {"m": 0, "k": 2048, "n": 8192}},
]

FUNCTIONS = [op_signature_record, task_contract]
DIMENSIONS = ["m", "k", "n"]
SHAPE = {"m": 3, "k": 5, "n": 7}


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


def synthetic_spec(m, k, n):
    hw = {
        "schema_version": 1,
        "accelerator": "synthetic_accel",
        "revision": "synthetic-rev-A",
        "toolchain": {"synthetic_cc": "0.0.1-synthetic"},
        "host": {"cpu": "synthetic cpu", "os": "synthetic os"},
        "hw_source": "in_house",
    }
    op = op_signature_record(m, k, n)
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
            "contract": task_contract(m, k, n),
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


def test_constants_are_those_of_the_record():
    assert (KIND, DTYPE, LAYOUT, LANGUAGE) == ("gemm", "fp32", "row_major", "c")
    assert PROTOTYPE == ADR_PROTOTYPE
    assert type(PROTOTYPE) is str
    assert "\n" not in PROTOTYPE and "  " not in PROTOTYPE
    assert PROTOTYPE.endswith(");")
    assert PROTOTYPE == ADR_CONTRACT["prototype"]


def test_first_instance_has_the_canonical_form_and_digest_of_the_record():
    record = op_signature_record(1, 2048, 8192)
    assert record == {
        "schema_version": 1,
        "kind": "gemm",
        "shape": {"m": 1, "k": 2048, "n": 8192},
        "dtype": "fp32",
        "layout": "row_major",
    }
    assert type(record) is dict and type(record["shape"]) is dict
    assert list(record) == ["schema_version", "kind", "shape", "dtype", "layout"]
    assert record["schema_version"] == keys.SCHEMA_VERSION
    key = op_signature_key(record)
    assert key.canonical == ADR_CANONICAL
    assert key.digest == ADR_DIGEST
    assert key.name == "gemm-485b9bc494d477eb"


def test_first_shapes_give_the_twelve_names_of_the_record_in_its_order():
    assert list(FIRST_SHAPES) == [shape for shape, _ in ADR_TABLE]
    names = [
        op_signature_key(op_signature_record(*shape)).name for shape in FIRST_SHAPES
    ]
    assert names == [name for _, name in ADR_TABLE]


def test_first_shapes_are_twelve_different_shapes_with_different_keys():
    assert type(FIRST_SHAPES) is tuple
    assert len(FIRST_SHAPES) == 12
    assert len(set(FIRST_SHAPES)) == 12
    for shape in FIRST_SHAPES:
        assert type(shape) is tuple and len(shape) == 3
        assert all(type(value) is int for value in shape)
    digests = {
        op_signature_key(op_signature_record(*shape)).digest for shape in FIRST_SHAPES
    }
    assert len(digests) == 12
    assert {m for m, _, _ in FIRST_SHAPES} == {1, 32, 512}
    assert {(k, n) for _, k, n in FIRST_SHAPES} == {
        (2048, 8192),
        (8192, 2048),
        (2048, 3072),
        (2048, 2048),
    }


def test_first_instance_has_the_task_contract_of_the_record():
    contract = task_contract(1, 2048, 8192)
    assert contract == ADR_CONTRACT
    assert type(contract) is dict and type(contract["operands"]) is list
    assert list(contract) == ["language", "prototype", "operands"]
    assert [entry["name"] for entry in contract["operands"]] == ["a", "b", "c"]
    for entry in contract["operands"]:
        assert type(entry) is dict and type(entry["shape"]) is list
        assert list(entry) == ["name", "role", "dtype", "shape"]


def test_each_dimension_is_placed_in_its_operand_position():
    assert op_signature_record(3, 5, 7)["shape"] == {"m": 3, "k": 5, "n": 7}
    assert task_contract(3, 5, 7)["operands"] == [
        {"name": "a", "role": "input", "dtype": "fp32", "shape": [3, 5]},
        {"name": "b", "role": "input", "dtype": "fp32", "shape": [5, 7]},
        {"name": "c", "role": "output", "dtype": "fp32", "shape": [3, 7]},
    ]


def test_arguments_may_be_given_by_name():
    assert op_signature_record(n=7, m=3, k=5) == op_signature_record(3, 5, 7)
    assert task_contract(n=7, m=3, k=5) == task_contract(3, 5, 7)


@pytest.mark.parametrize(
    "shape",
    [
        (2048, 2048, 2048),
        (1, 1, 1),
        (MAX_INTEGER, MAX_INTEGER, MAX_INTEGER),
        (1, MAX_INTEGER, 2),
        (MAX_INTEGER, 1, 2),
        (2, 1, MAX_INTEGER),
    ],
)
def test_equal_smallest_and_largest_dimensions_are_accepted(shape):
    m, k, n = shape
    record = op_signature_record(m, k, n)
    assert record["shape"] == {"m": m, "k": k, "n": n}
    assert op_signature_key(record).name.startswith("gemm-")
    shapes = [entry["shape"] for entry in task_contract(m, k, n)["operands"]]
    assert shapes == [[m, k], [k, n], [m, n]]
    spec.validate(synthetic_spec(m, k, n))


@pytest.mark.parametrize("shape", FIRST_SHAPES)
def test_spec_built_from_the_returned_values_is_valid(shape):
    document = synthetic_spec(*shape)
    spec.validate(document)
    assert document["task"]["contract"]["prototype"] == ADR_PROTOTYPE
    assert sorted(document["task"]) == ["contract", "objective", "op_signature"]


@pytest.mark.parametrize("name", ["timing_driver.c", "verification_program.c"])
def test_prototype_is_a_line_of_the_harness_file(name):
    path = Path(hilclaw.__file__).parent / "harness" / name
    assert PROTOTYPE in path.read_text(encoding="utf-8").splitlines()


@pytest.mark.parametrize("function", FUNCTIONS)
def test_two_calls_give_equal_and_separate_results(function):
    first, second = function(3, 5, 7), function(3, 5, 7)
    assert first == second
    assert first is not second
    if function is op_signature_record:
        assert first["shape"] is not second["shape"]
    else:
        assert first["operands"] is not second["operands"]
        for one, other in zip(first["operands"], second["operands"], strict=True):
            assert one is not other
            assert one["shape"] is not other["shape"]


def test_changing_a_returned_record_changes_nothing_else():
    record = op_signature_record(3, 5, 7)
    expected = op_signature_record(3, 5, 7)
    record["shape"]["m"] = 9
    record["shape"]["extra"] = 1
    record["kind"] = "changed"
    record["label"] = "changed"
    del record["layout"]
    assert op_signature_record(3, 5, 7) == expected
    assert (KIND, DTYPE, LAYOUT) == ("gemm", "fp32", "row_major")


def test_changing_a_returned_contract_changes_nothing_else():
    contract = task_contract(3, 5, 7)
    expected = task_contract(3, 5, 7)
    contract["operands"][0]["shape"][0] = 9
    contract["operands"][1]["shape"].append(1)
    contract["operands"][1]["name"] = "changed"
    contract["operands"][2]["extra"] = "changed"
    contract["operands"].pop()
    contract["prototype"] = "changed"
    contract["build"] = {}
    del contract["language"]
    assert task_contract(3, 5, 7) == expected
    assert op_signature_record(3, 5, 7)["shape"] == SHAPE
    assert (LANGUAGE, PROTOTYPE, DTYPE) == ("c", ADR_PROTOTYPE, "fp32")
    assert FIRST_SHAPES[0] == (1, 2048, 8192)


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
        function(0, 0, 0)
    with pytest.raises(InvalidRecordError, match=r"^shape\.k: "):
        function(1, 0, 0)


@pytest.mark.parametrize("function", FUNCTIONS)
def test_long_bad_value_is_shortened_in_the_message(function):
    with pytest.raises(InvalidRecordError) as caught:
        function(3, "x" * 10_000, 7)
    assert len(str(caught.value)) < 200


@pytest.mark.parametrize("function", FUNCTIONS)
@pytest.mark.parametrize(
    ("args", "kwargs"),
    [
        ((), {}),
        ((3,), {}),
        ((3, 5), {}),
        ((3, 5), {"m": 3}),
        ((3, 5, 7, 9), {}),
        ((3, 5, 7), {"label": "x"}),
        ((), {"m": 3, "k": 5}),
    ],
)
def test_missing_or_surplus_argument_is_a_type_error(function, args, kwargs):
    with pytest.raises(TypeError):
        function(*args, **kwargs)


def test_zero_is_accepted_by_keys_and_refused_here():
    record = dict(op_signature_record(1, 1, 1), shape={"m": 0, "k": 1, "n": 1})
    assert op_signature_key(record).name.startswith("gemm-")
    with pytest.raises(InvalidRecordError):
        op_signature_record(0, 1, 1)


def test_walk_through_shape_without_a_zero_has_the_values_of_the_contract():
    shape, name = ADR_0037_NO_ZERO
    assert op_signature_key(op_signature_record(*shape)).name == name
    assert task_contract(*shape) == ADR_CONTRACT


@pytest.mark.parametrize(("shape", "name"), ADR_0037_NOT_COVERED)
def test_walk_through_shape_with_a_zero_has_a_key_and_is_not_covered(shape, name):
    record = {
        "schema_version": keys.SCHEMA_VERSION,
        "kind": KIND,
        "shape": dict(zip(DIMENSIONS, shape, strict=True)),
        "dtype": DTYPE,
        "layout": LAYOUT,
    }
    assert op_signature_key(record).name == name
    first_zero = DIMENSIONS[shape.index(0)]
    for function in FUNCTIONS:
        with pytest.raises(InvalidRecordError) as caught:
            function(*shape)
        assert type(caught.value) is InvalidRecordError
        assert str(caught.value).startswith(f"shape.{first_zero}: ")


def test_module_is_bound_by_the_default_registry_and_the_start_only_and_imports_keys_only():
    own = Path(gemm_contract.__file__)
    binders = (
        own.parent / "check_definition.py",
        own.parent / "spec_tool.py",
        own.parent / "start_instance.py",
    )
    assert imported_modules(own) == {"reprlib", "hilclaw", "hilclaw.keys"}
    for binder in binders:
        assert "gemm_contract" in binder.read_text(encoding="utf-8")
    for path in sorted(own.parent.rglob("*.py")):
        if path != own and path not in binders:
            assert "gemm_contract" not in path.read_text(encoding="utf-8"), path.name
    assert not hasattr(gemm_contract, "main")
    assert "__main__" not in own.read_text(encoding="utf-8")


def test_public_names_of_the_module():
    public = {
        name
        for name, value in vars(gemm_contract).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {
        "KIND",
        "DTYPE",
        "LAYOUT",
        "LANGUAGE",
        "PROTOTYPE",
        "FIRST_SHAPES",
        "covers",
        "op_signature_record",
        "task_contract",
    }
    for function in FUNCTIONS:
        assert list(inspect.signature(function).parameters) == DIMENSIONS


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    op_signature_record(3, 5, 7)
    task_contract(3, 5, 7)
    for function in FUNCTIONS:
        with pytest.raises(InvalidRecordError):
            function(0, 5, 7)
    assert list(tmp_path.iterdir()) == []


def gemm_record(m, k, n, **members):
    shape = {"m": m, "k": k, "n": n}
    return dict(ADR_0041_RECORD, shape=shape, **members)


NOT_COVERED = [
    gemm_record(3, 5, 7, dtype="fp16"),
    gemm_record(3, 5, 7, dtype="fp64"),
    gemm_record(3, 5, 7, dtype="row_major"),
    gemm_record(3, 5, 7, layout="col_major"),
    gemm_record(3, 5, 7, layout="fp32"),
    gemm_record(0, 5, 7),
    gemm_record(3, 0, 7),
    gemm_record(3, 5, 0),
    gemm_record(0, 0, 0),
    gemm_record(0, MAX_INTEGER, MAX_INTEGER),
    gemm_record(3, 5, 7, dtype="fp16", layout="col_major"),
    gemm_record(0, 5, 7, dtype="fp16"),
    gemm_record(3, 5, 0, layout="col_major"),
    gemm_record(0, 0, 0, dtype="row_major", layout="fp32"),
]
OPTIONAL_MEMBERS = [
    {"ext": {"variant": "a"}},
    {"ext": {"n": 1}},
    {"ext": {"m": 0, "dtype": "fp16", "kind": "other"}},
    {"label": "gate/up at M = 1"},
    {"ext": {"variant": "a"}, "label": "x"},
]
REFUSED = [
    None,
    [],
    "gemm",
    1,
    {},
    list(ADR_0041_RECORD.items()),
    {k: v for k, v in ADR_0041_RECORD.items() if k != "shape"},
    {k: v for k, v in ADR_0041_RECORD.items() if k != "kind"},
    dict(ADR_0041_RECORD, unknown=1),
    dict(ADR_0041_RECORD, schema_version=2),
    dict(ADR_0041_RECORD, schema_version=True),
    dict(ADR_0041_RECORD, dtype="FP32"),
    dict(ADR_0041_RECORD, dtype=None),
    dict(ADR_0041_RECORD, layout="row-major"),
    dict(ADR_0041_RECORD, kind="conv"),
    dict(ADR_0041_RECORD, kind=["gemm"]),
    dict(ADR_0041_RECORD, shape=None),
    dict(ADR_0041_RECORD, shape=[1, 2048, 8192]),
    gemm_record(True, 5, 7),
    gemm_record(3, -1, 7),
    gemm_record(3, 5, 1.0),
    gemm_record(MAX_INTEGER + 1, 5, 7),
    gemm_record(3, "5", 7),
    dict(ADR_0041_RECORD, shape={"m": 3, "k": 5}),
    dict(ADR_0041_RECORD, shape={"m": 3, "k": 5, "n": 7, "p": 1}),
    dict(ADR_0041_RECORD, ext={}),
    dict(ADR_0041_RECORD, ext={"variant": 1.5}),
    dict(ADR_0041_RECORD, label=""),
    dict(ADR_0041_RECORD, label=1),
]


@pytest.mark.parametrize(
    "shape", [*FIRST_SHAPES, (1, 1, 1), (MAX_INTEGER, MAX_INTEGER, MAX_INTEGER)]
)
def test_record_of_this_contract_is_covered(shape):
    assert covers(op_signature_record(*shape)) is True


def test_walk_through_record_of_adr_0041_is_covered():
    assert covers(ADR_0041_RECORD) is True
    assert op_signature_key(ADR_0041_RECORD).name == "gemm-485b9bc494d477eb"


@pytest.mark.parametrize("change", ADR_0041_NOT_COVERED, ids=repr)
def test_walk_through_records_of_adr_0041_are_valid_and_not_covered(change):
    record = dict(ADR_0041_RECORD, **change)
    assert op_signature_key(record).name.startswith("gemm-")
    assert covers(record) is False


@pytest.mark.parametrize(("shape", "name"), ADR_0037_NOT_COVERED)
def test_walk_through_shape_with_a_zero_is_a_record_not_covered(shape, name):
    record = gemm_record(*shape)
    assert op_signature_key(record).name == name
    assert covers(record) is False


@pytest.mark.parametrize("record", NOT_COVERED, ids=repr)
def test_record_failing_a_condition_is_valid_and_not_covered(record):
    assert op_signature_key(record).name.startswith("gemm-")
    assert covers(record) is False


def test_record_of_another_kind_is_not_covered(monkeypatch):
    members = {"gemm": frozenset(DIMENSIONS), "other": frozenset(DIMENSIONS)}
    monkeypatch.setattr(keys, "_SHAPE_MEMBERS", members)
    record = dict(ADR_0041_RECORD, kind="other")
    assert op_signature_key(record).name.startswith("other-")
    assert covers(record) is False
    assert covers(ADR_0041_RECORD) is True


def test_record_of_another_kind_with_other_shape_members_is_not_covered(monkeypatch):
    members = {"gemm": frozenset(DIMENSIONS), "other": frozenset({"h", "w"})}
    monkeypatch.setattr(keys, "_SHAPE_MEMBERS", members)
    record = dict(ADR_0041_RECORD, kind="other", shape={"h": 1, "w": 1})
    assert op_signature_key(record).name.startswith("other-")
    assert covers(record) is False


@pytest.mark.parametrize("members", OPTIONAL_MEMBERS, ids=repr)
def test_ext_and_label_do_not_change_the_answer(members):
    assert covers(dict(ADR_0041_RECORD, **members)) is True
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


@pytest.mark.parametrize("record", [ADR_0041_RECORD, *NOT_COVERED], ids=repr)
def test_covers_does_not_modify_its_argument_and_repeats_its_answer(record):
    argument = dict(copy.deepcopy(record), ext={"variant": "a"}, label="x")
    before = copy.deepcopy(argument)
    first = covers(argument)
    assert argument == before
    assert covers(argument) is first
    assert covers(copy.deepcopy(before)) is first


def test_covers_takes_one_argument_by_position_or_by_name():
    assert list(inspect.signature(covers).parameters) == ["record"]
    assert covers(record=ADR_0041_RECORD) is True
    assert covers(record=gemm_record(0, 5, 7)) is False
    for args, kwargs in [
        ((), {}),
        ((ADR_0041_RECORD, ADR_0041_RECORD), {}),
        ((ADR_0041_RECORD,), {"record": ADR_0041_RECORD}),
        ((), {"op_signature": ADR_0041_RECORD}),
        ((3, 5, 7), {}),
    ]:
        with pytest.raises(TypeError):
            covers(*args, **kwargs)


def test_a_call_of_covers_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert covers(ADR_0041_RECORD) is True
    assert covers(gemm_record(0, 5, 7)) is False
    with pytest.raises(InvalidRecordError):
        covers({})
    assert list(tmp_path.iterdir()) == []
