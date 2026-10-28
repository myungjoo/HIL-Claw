import ast
import copy
import inspect
import io
import json
import re
import tokenize
import typing
from pathlib import Path

import pytest

from hilclaw import (
    check_admission,
    check_failure,
    check_operation,
    contract_table,
    gemm_contract,
    instance,
    keys,
    tools,
)
from hilclaw.check_admission import (
    KIND_DRAWS_NOT_STATED,
    KIND_OP_SIGNATURE_NOT_COVERED,
    KIND_OP_SIGNATURE_NOT_STATED,
    KIND_TOLERANCE_NOT_STATED,
    KINDS,
    Admitted,
    Bf16Admitted,
    admit,
    admit_for_step,
)

MARKER = "zq7-marker-zq7"
MESSAGE_LIMIT = 200
ABSENT = object()
MEMBER = {
    "op_signature_not_stated": "op_signature",
    "op_signature_not_covered": "op_signature",
    "draws_not_stated": "draws",
    "tolerance_not_stated": "tolerance",
}
# Test values of a number of draws and of a tolerance: none is a default or a recommended value.
TEST_DRAWS, OTHER_TEST_DRAWS = 3, 7
TEST_TOLERANCE = {"rtol": 0.25, "atol": 3.0}
OTHER_TEST_TOLERANCE = {"rtol": 0.5, "atol": 7.0}
# The record of the Example of ADR-0031.
RECORD = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": {"m": 1, "k": 2048, "n": 8192},
    "dtype": "fp32",
    "layout": "row_major",
}
NOT_COVERED = [
    {"dtype": "fp16"},
    {"layout": "col_major"},
    {"m": 0},
    {"k": 0},
    {"n": 0},
]


def record(**changes):
    changed = copy.deepcopy(RECORD)
    for name, value in changes.items():
        target = changed["shape"] if name in changed["shape"] else changed
        target[name] = value
    return changed


def content(
    op=RECORD,
    draws=TEST_DRAWS,
    tolerance=TEST_TOLERANCE,
    accelerator="cpu_standin",
    **others,
):
    profile = {
        "schema_version": 1,
        "accelerator": accelerator,
        "revision": "test-revision",
        "toolchain": {"clang": "test"},
        "host": {"cpu": "test", "os": "test"},
        "hw_source": "external",
    }
    document = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(profile).name, "record": profile},
        **others,
    }
    if op is not ABSENT:
        document["op_signature"] = {
            "key": keys.op_signature_key(op).name,
            "record": op,
        }
    if draws is not ABSENT:
        document["draws"] = draws
    if tolerance is not ABSENT:
        document["tolerance"] = tolerance
    return instance.parse(json.dumps(document).encode())


def refused(stated, kind, covers=gemm_contract.covers):
    with pytest.raises(tools.ToolFailure) as caught:
        admit(stated, covers=covers)
    failure = caught.value
    assert type(failure) is tools.ToolFailure
    assert failure.kind == kind
    assert type(failure.message) is str
    assert failure.message.startswith(MEMBER[kind] + ": ")
    assert len(failure.message) <= MESSAGE_LIMIT
    assert MARKER not in failure.message
    return failure.message


class Recorder:
    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def __call__(self, handed):
        self.calls.append(handed)
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer


def imported_modules(path):
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def test_the_kinds_are_names_of_this_tool():
    assert KIND_OP_SIGNATURE_NOT_STATED == "op_signature_not_stated"
    assert KIND_OP_SIGNATURE_NOT_COVERED == "op_signature_not_covered"
    assert KIND_DRAWS_NOT_STATED == "draws_not_stated"
    assert KIND_TOLERANCE_NOT_STATED == "tolerance_not_stated"
    for kind in KINDS:
        assert type(kind) is str
        assert re.fullmatch(r"[a-z][a-z0-9_]{0,31}", kind)
        assert kind not in tools.RESERVED_KINDS
        assert kind != check_operation.KIND_OPERATION_ANSWER_INVALID
        assert kind != check_failure.KIND_OPERATION_FAILURE_INVALID


def test_kinds_holds_the_four_in_the_order_of_adr_0046_decision_8():
    assert type(KINDS) is tuple
    assert KINDS == (
        "op_signature_not_stated",
        "op_signature_not_covered",
        "draws_not_stated",
        "tolerance_not_stated",
    )
    assert len(set(KINDS)) == 4


def test_a_tool_failure_can_be_built_from_each_kind_and_its_message():
    messages = {
        KIND_OP_SIGNATURE_NOT_STATED: refused(
            content(op=ABSENT), KIND_OP_SIGNATURE_NOT_STATED
        ),
        KIND_OP_SIGNATURE_NOT_COVERED: refused(
            content(op=record(dtype="fp16")), KIND_OP_SIGNATURE_NOT_COVERED
        ),
        KIND_DRAWS_NOT_STATED: refused(content(draws=ABSENT), KIND_DRAWS_NOT_STATED),
        KIND_TOLERANCE_NOT_STATED: refused(
            content(tolerance=ABSENT), KIND_TOLERANCE_NOT_STATED
        ),
    }
    assert set(messages) == set(KINDS)
    assert len(set(messages.values())) == 4
    for kind, message in messages.items():
        built = tools.ToolFailure(kind, message)
        assert built.error_object() == {"error": {"kind": kind, "message": message}}


@pytest.mark.parametrize(
    ("op", "draws", "tolerance", "expected"),
    [
        (record(), TEST_DRAWS, TEST_TOLERANCE, (1, 2048, 8192, 3, 0.25, 3.0)),
        (
            record(m=32),
            OTHER_TEST_DRAWS,
            OTHER_TEST_TOLERANCE,
            (32, 2048, 8192, 7, 0.5, 7.0),
        ),
        (
            record(m=5, k=6, n=7),
            1,
            {"rtol": 0.0, "atol": 0.0},
            (5, 6, 7, 1, 0.0, 0.0),
        ),
        (
            record(m=keys.MAX_INTEGER, k=keys.MAX_INTEGER, n=keys.MAX_INTEGER),
            keys.MAX_INTEGER,
            {"rtol": 1e300, "atol": 1e300},
            (keys.MAX_INTEGER,) * 4 + (1e300, 1e300),
        ),
    ],
)
def test_a_content_that_states_all_three_is_admitted_with_its_values(
    op, draws, tolerance, expected
):
    stated = content(op=op, draws=draws, tolerance=tolerance)
    before = copy.deepcopy(stated)
    admitted = admit(stated, covers=gemm_contract.covers)
    assert type(admitted) is Admitted
    assert admitted == expected
    shape = stated.op_signature.record["shape"]
    assert admitted.m is shape["m"]
    assert admitted.k is shape["k"]
    assert admitted.n is shape["n"]
    assert admitted.draws is stated.draws
    assert admitted.rtol is stated.tolerance.rtol
    assert admitted.atol is stated.tolerance.atol
    assert [type(value) for value in admitted] == [int] * 4 + [float] * 2
    assert stated == before


def test_admitted_has_six_fields_and_no_default():
    assert Admitted._fields == ("m", "k", "n", "draws", "rtol", "atol")
    assert Admitted._field_defaults == {}
    assert issubclass(Admitted, tuple)
    value = Admitted(1, 2, 3, 4, 0.5, 0.25)
    assert value == Admitted(m=1, k=2, n=3, draws=4, rtol=0.5, atol=0.25)
    with pytest.raises(AttributeError):
        value.draws = 5
    with pytest.raises(TypeError):
        Admitted(1, 2, 3, 4, 0.5)
    with pytest.raises(TypeError):
        Admitted(1, 2, 3, 4, 0.5, 0.25, 6)


# The Walk-throughs: ADR-0041 rows 2, 3, 4 and 6; ADR-0046 rows 2, 3, 4 and 5.
ORDER = [
    # ADR-0041 row 2
    (ABSENT, TEST_DRAWS, TEST_TOLERANCE, "op_signature_not_stated"),
    # ADR-0041 row 3
    (ABSENT, TEST_DRAWS, ABSENT, "op_signature_not_stated"),
    # ADR-0046 row 5
    (ABSENT, ABSENT, TEST_TOLERANCE, "op_signature_not_stated"),
    (ABSENT, ABSENT, ABSENT, "op_signature_not_stated"),
    # ADR-0041 row 6
    (record(dtype="fp16"), TEST_DRAWS, TEST_TOLERANCE, "op_signature_not_covered"),
    (record(dtype="fp16"), TEST_DRAWS, ABSENT, "op_signature_not_covered"),
    (record(dtype="fp16"), ABSENT, TEST_TOLERANCE, "op_signature_not_covered"),
    (record(dtype="fp16"), ABSENT, ABSENT, "op_signature_not_covered"),
    # ADR-0046 row 2
    (RECORD, ABSENT, TEST_TOLERANCE, "draws_not_stated"),
    # ADR-0046 row 3
    (RECORD, ABSENT, ABSENT, "draws_not_stated"),
    # ADR-0041 row 4 and ADR-0046 row 4
    (RECORD, TEST_DRAWS, ABSENT, "tolerance_not_stated"),
    (RECORD, TEST_DRAWS, TEST_TOLERANCE, None),
]


@pytest.mark.parametrize(("op", "draws", "tolerance", "kind"), ORDER)
def test_a_content_has_the_first_answer_whose_condition_holds(
    op, draws, tolerance, kind
):
    stated = content(op=op, draws=draws, tolerance=tolerance)
    before = copy.deepcopy(stated)
    if kind is None:
        assert type(admit(stated, covers=gemm_contract.covers)) is Admitted
    else:
        refused(stated, kind)
    assert stated == before


@pytest.mark.parametrize("change", NOT_COVERED)
@pytest.mark.parametrize("draws", [TEST_DRAWS, ABSENT])
def test_a_valid_record_the_contract_does_not_cover_is_not_covered(change, draws):
    refused(
        content(op=record(**change), draws=draws),
        KIND_OP_SIGNATURE_NOT_COVERED,
    )


@pytest.mark.parametrize(
    "change",
    [{"ext": {"variant": MARKER}}, {"label": MARKER}, {"ext": {"n": 0}, "label": "x"}],
)
def test_a_covered_record_with_an_ext_or_a_label_is_admitted(change):
    admitted = admit(content(op=record(**change)), covers=gemm_contract.covers)
    assert admitted == (1, 2048, 8192, TEST_DRAWS, 0.25, 3.0)


@pytest.mark.parametrize("accelerator", ["cpu_standin", "mock", "another_name"])
@pytest.mark.parametrize(("op", "draws", "tolerance", "kind"), ORDER)
def test_the_rest_of_the_instance_changes_no_answer(
    accelerator, op, draws, tolerance, kind
):
    stated = content(
        op=op,
        draws=draws,
        tolerance=tolerance,
        accelerator=accelerator,
        n_max=5,
        some_other_member={"draws": 99, "tolerance": MARKER},
    )
    assert stated.hw_profile["accelerator"] == accelerator
    assert stated.others == {"some_other_member": {"draws": 99, "tolerance": MARKER}}
    if kind is None:
        admitted = admit(stated, covers=gemm_contract.covers)
        assert admitted == (1, 2048, 8192, TEST_DRAWS, 0.25, 3.0)
    else:
        refused(stated, kind)


@pytest.mark.parametrize(
    "stated",
    [
        content(op=ABSENT),
        content(op=ABSENT, draws=ABSENT, tolerance=ABSENT),
    ],
)
def test_the_predicate_is_not_called_when_no_op_signature_is_stated(stated):
    for answer in (True, False, "yes", ValueError(MARKER)):
        covers = Recorder(answer)
        refused(stated, KIND_OP_SIGNATURE_NOT_STATED, covers)
        assert covers.calls == []


@pytest.mark.parametrize(
    ("draws", "tolerance", "kind"),
    [
        (TEST_DRAWS, TEST_TOLERANCE, None),
        (ABSENT, TEST_TOLERANCE, "draws_not_stated"),
        (TEST_DRAWS, ABSENT, "tolerance_not_stated"),
        (ABSENT, ABSENT, "draws_not_stated"),
    ],
)
def test_the_predicate_is_called_once_with_the_record_the_instance_holds(
    draws, tolerance, kind
):
    stated = content(op=record(label=MARKER), draws=draws, tolerance=tolerance)
    held = stated.op_signature.record
    before = copy.deepcopy(held)
    covers = Recorder(True)
    if kind is None:
        admit(stated, covers=covers)
    else:
        refused(stated, kind, covers)
    assert len(covers.calls) == 1
    assert covers.calls[0] is held
    assert held == before
    refusing = Recorder(False)
    refused(stated, KIND_OP_SIGNATURE_NOT_COVERED, refusing)
    assert len(refusing.calls) == 1
    assert refusing.calls[0] is held
    assert held == before


def test_the_module_holds_no_reading_of_covered_of_its_own():
    covered = content()
    assert gemm_contract.covers(covered.op_signature.record) is True
    refused(covered, KIND_OP_SIGNATURE_NOT_COVERED, Recorder(False))
    for change in NOT_COVERED:
        other = content(op=record(**change))
        assert gemm_contract.covers(other.op_signature.record) is False
        admitted = admit(other, covers=Recorder(True))
        assert admitted[:3] == tuple(other.op_signature.record["shape"].values())


@pytest.mark.parametrize(
    "raised",
    [
        ValueError(MARKER),
        keys.InvalidRecordError(MARKER),
        tools.ToolFailure("example_kind", MARKER),
        KeyboardInterrupt(),
    ],
)
def test_what_the_predicate_raises_passes_through_as_the_same_object(raised):
    covers = Recorder(raised)
    with pytest.raises(type(raised)) as caught:
        admit(content(), covers=covers)
    assert caught.value is raised
    assert len(covers.calls) == 1


@pytest.mark.parametrize("answer", [1, 0, "yes", "", None, [], [True], 1.0])
@pytest.mark.parametrize("draws", [TEST_DRAWS, ABSENT])
def test_an_answer_of_the_predicate_that_is_no_bool_is_a_type_error(answer, draws):
    covers = Recorder(answer)
    with pytest.raises(TypeError):
        admit(content(draws=draws), covers=covers)
    assert len(covers.calls) == 1


def instance_like():
    stated = content()
    other = typing.NamedTuple(
        "Other", [(name, typing.Any) for name in instance.Instance._fields]
    )

    class Derived(instance.Instance):
        pass

    return [
        None,
        stated._asdict(),
        tuple(stated),
        list(stated),
        other(*stated),
        Derived(*stated),
        instance.Instance,
        stated.op_signature,
        json.dumps(RECORD),
    ]


@pytest.mark.parametrize("not_an_instance", instance_like())
def test_an_instance_of_another_type_is_a_type_error(not_an_instance):
    covers = Recorder(True)
    with pytest.raises(TypeError):
        admit(not_an_instance, covers=covers)
    assert covers.calls == []
    with pytest.raises(TypeError):
        admit(not_an_instance, covers=None)


@pytest.mark.parametrize("covers", [None, "covers", 1, True, RECORD])
@pytest.mark.parametrize(
    "stated",
    [
        content(),
        content(op=ABSENT),
        content(op=record(dtype="fp16")),
        content(draws=ABSENT),
        content(tolerance=ABSENT),
    ],
)
def test_a_predicate_that_is_not_callable_is_a_type_error_before_any_answer(
    covers, stated
):
    with pytest.raises(TypeError):
        admit(stated, covers=covers)


def test_the_arguments_are_one_instance_and_the_predicate_by_name():
    stated = content()
    with pytest.raises(TypeError):
        admit()
    with pytest.raises(TypeError):
        admit(stated)
    with pytest.raises(TypeError):
        admit(covers=gemm_contract.covers)
    with pytest.raises(TypeError):
        admit(stated, gemm_contract.covers)
    with pytest.raises(TypeError):
        admit(stated, covers=gemm_contract.covers, tolerance=TEST_TOLERANCE)
    assert admit(instance=stated, covers=gemm_contract.covers) == admit(
        stated, covers=gemm_contract.covers
    )


def test_none_alone_says_not_stated_and_no_value_is_validated_again():
    stated = content()._replace(draws=0, tolerance=instance.Tolerance(0.0, -1.0))
    assert admit(stated, covers=gemm_contract.covers) == (1, 2048, 8192, 0, 0.0, -1.0)


def test_no_message_shows_anything_of_the_content():
    long = MARKER * 18
    stated = {
        "op": record(label=long, ext={"variant": long}),
        "accelerator": "cpu_standin",
        "owner": long,
        "project": long,
        "some_other_member": long,
    }
    messages = [
        refused(content(**(stated | {"op": ABSENT})), KIND_OP_SIGNATURE_NOT_STATED),
        refused(
            content(**(stated | {"op": record(label=long, dtype="fp16")})),
            KIND_OP_SIGNATURE_NOT_COVERED,
        ),
        refused(content(**stated), KIND_OP_SIGNATURE_NOT_COVERED, Recorder(False)),
        refused(content(draws=ABSENT, **stated), KIND_DRAWS_NOT_STATED),
        refused(content(tolerance=ABSENT, **stated), KIND_TOLERANCE_NOT_STATED),
    ]
    assert messages[1] == messages[2]
    assert messages == [
        refused(content(op=ABSENT), KIND_OP_SIGNATURE_NOT_STATED),
        refused(content(op=record(m=0)), KIND_OP_SIGNATURE_NOT_COVERED),
        refused(content(), KIND_OP_SIGNATURE_NOT_COVERED, Recorder(False)),
        refused(content(draws=ABSENT), KIND_DRAWS_NOT_STATED),
        refused(content(tolerance=ABSENT), KIND_TOLERANCE_NOT_STATED),
    ]


def test_a_call_writes_no_file_and_keeps_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for _ in range(2):
        refused(content(op=ABSENT), KIND_OP_SIGNATURE_NOT_STATED)
        refused(content(op=record(n=0)), KIND_OP_SIGNATURE_NOT_COVERED)
        refused(content(draws=ABSENT), KIND_DRAWS_NOT_STATED)
        refused(content(tolerance=ABSENT), KIND_TOLERANCE_NOT_STATED)
        admitted = admit(content(), covers=gemm_contract.covers)
        assert admitted == (1, 2048, 8192, TEST_DRAWS, 0.25, 3.0)
        with pytest.raises(TypeError):
            admit(None, covers=gemm_contract.covers)
        with pytest.raises(TypeError):
            admit(content(), covers=Recorder(None))
    assert list(tmp_path.iterdir()) == []


def test_module_imports_three_modules_and_has_no_entry():
    own = Path(check_admission.__file__)
    assert imported_modules(own) == {
        "inspect",
        "typing",
        "hilclaw",
        "hilclaw.check_parameters",
        "hilclaw.check_result",
        "hilclaw.contract_table",
        "hilclaw.instance",
        "hilclaw.tools",
    }
    assert not hasattr(check_admission, "main")
    assert "__main__" not in own.read_text(encoding="utf-8")


def test_the_text_and_the_code_hold_none_of_the_kept_out_strings():
    text = Path(check_admission.__file__).read_text(encoding="utf-8")
    assert "gemm_contract" not in text
    assert "standin_profile" not in text
    code = [
        token.string
        for token in tokenize.generate_tokens(io.StringIO(text).readline)
        if token.type in (tokenize.NAME, tokenize.STRING)
        and not token.string.startswith('"""')
    ]
    for kept_out in (
        "invalid_request",
        "no_backend",
        "not_offered",
        "run_file_",
        "step_open",
        "operation_answer_invalid",
        "operation_failure_invalid",
        "correctness_check_",
        "seed",
        "random",
        "secrets",
        "urandom",
    ):
        assert not [string for string in code if kept_out in string], kept_out
    for kind in KINDS:
        assert [string for string in code if kind in string] == [f'"{kind}"']


def test_public_names_of_the_module_and_no_default():
    public = {
        name
        for name, value in vars(check_admission).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {
        "KIND_OP_SIGNATURE_NOT_STATED",
        "KIND_OP_SIGNATURE_NOT_COVERED",
        "KIND_DRAWS_NOT_STATED",
        "KIND_TOLERANCE_NOT_STATED",
        "KINDS",
        "Admitted",
        "Bf16Admitted",
        "admit",
        "admit_for_step",
    }
    parameters = list(inspect.signature(admit).parameters.values())
    assert [parameter.name for parameter in parameters] == ["instance", "covers"]
    assert [parameter.kind for parameter in parameters] == [
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
    ]
    assert all(parameter.default is inspect.Parameter.empty for parameter in parameters)


# --- bf16 kinds (ADR-0177 decision 3) ---

BF16_SHAPES = {
    "gemm": ({"m": 2, "k": 3, "n": 4}, (2, 3, 4)),
    "rmsnorm": ({"m": 5, "n": 8}, (5, 8)),
    "elementwise_add": ({"m": 6, "n": 7}, (6, 7)),
    "swiglu": ({"m": 3, "n": 9}, (3, 9)),
}


def bf16_record(kind, shape=None, **changes):
    stated = {
        "schema_version": 1,
        "kind": kind,
        "shape": dict(BF16_SHAPES[kind][0] if shape is None else shape),
        "dtype": "bf16",
        "layout": "row_major",
    }
    return stated | changes


def refused_for_step(stated, bf16_step, covers=contract_table.covers):
    with pytest.raises(tools.ToolFailure) as caught:
        admit_for_step(stated, covers=covers, bf16_step=bf16_step)
    assert type(caught.value) is tools.ToolFailure
    return caught.value.kind


def test_bf16_admitted_has_six_fields_and_no_default():
    assert Bf16Admitted._fields == ("kind", "dtype", "dims", "draws", "rtol", "atol")
    assert Bf16Admitted._field_defaults == {}
    assert issubclass(Bf16Admitted, tuple)
    with pytest.raises(TypeError):
        Bf16Admitted("rmsnorm", "bf16", (1, 2), 3, 0.5)


@pytest.mark.parametrize("kind", list(BF16_SHAPES))
def test_a_bf16_record_is_admitted_with_the_members_of_its_kind(kind):
    stated = content(op=bf16_record(kind))
    expected = Bf16Admitted(kind, "bf16", BF16_SHAPES[kind][1], TEST_DRAWS, 0.25, 3.0)
    for admitted in (
        admit(stated, covers=contract_table.covers),
        admit_for_step(stated, covers=contract_table.covers, bf16_step=True),
    ):
        assert type(admitted) is Bf16Admitted
        assert admitted == expected
        assert type(admitted.dims) is tuple


def test_the_dims_follow_the_order_of_task_contract_not_of_the_record():
    shape = {"n": 4, "k": 3, "m": 2}
    stated = content(op=bf16_record("gemm", shape))
    admitted = admit_for_step(stated, covers=contract_table.covers, bf16_step=True)
    assert admitted.dims == (2, 3, 4)


def test_an_fp32_gemm_record_is_admitted_as_before_under_its_step():
    stated = content()
    for covers in (gemm_contract.covers, contract_table.check_covers):
        admitted = admit_for_step(stated, covers=covers, bf16_step=False)
        assert type(admitted) is Admitted
        assert admitted == admit(stated, covers=covers)
        assert admitted == (1, 2048, 8192, TEST_DRAWS, 0.25, 3.0)


@pytest.mark.parametrize("kind", list(BF16_SHAPES))
def test_a_bf16_record_under_an_fp32_step_is_not_covered(kind):
    recorder = Recorder(True)
    stated = content(op=bf16_record(kind), draws=ABSENT, tolerance=ABSENT)
    assert refused_for_step(stated, False, recorder) == KIND_OP_SIGNATURE_NOT_COVERED
    assert len(recorder.calls) == 1


def test_an_fp32_record_under_a_bf16_step_is_not_covered():
    recorder = Recorder(True)
    stated = content(draws=ABSENT)
    assert refused_for_step(stated, True, recorder) == KIND_OP_SIGNATURE_NOT_COVERED
    assert len(recorder.calls) == 1
    other = content(op=record(dtype="fp16"))
    assert refused_for_step(other, True, Recorder(True)) == (
        KIND_OP_SIGNATURE_NOT_COVERED
    )


def test_a_bf16_record_the_predicate_refuses_is_not_covered():
    stated = content(op=bf16_record("rmsnorm"))
    for bf16_step in (True, False):
        kind = refused_for_step(stated, bf16_step, contract_table.check_covers)
        assert kind == KIND_OP_SIGNATURE_NOT_COVERED
    with pytest.raises(tools.ToolFailure) as caught:
        admit(stated, covers=contract_table.check_covers)
    assert caught.value.kind == KIND_OP_SIGNATURE_NOT_COVERED


@pytest.mark.parametrize("kind", list(BF16_SHAPES))
def test_a_bf16_record_with_a_shape_outside_its_contract_is_not_covered(kind):
    shape = dict.fromkeys(BF16_SHAPES[kind][0], 1) | {"m": 0}
    stated = content(op=bf16_record(kind, shape))
    assert refused_for_step(stated, True) == KIND_OP_SIGNATURE_NOT_COVERED


@pytest.mark.parametrize(("kind", "shape"), [("rope", {"m": 2, "h": 2, "d": 4})])
def test_a_bf16_record_of_a_kind_with_no_check_is_not_covered(kind, shape):
    stated_record = {
        "schema_version": 1,
        "kind": kind,
        "shape": shape,
        "dtype": "bf16",
        "layout": "row_major",
    }
    assert contract_table.covers(stated_record)
    stated = content(op=stated_record)
    assert refused_for_step(stated, True) == KIND_OP_SIGNATURE_NOT_COVERED
    assert refused_for_step(stated, True, Recorder(True)) == (
        KIND_OP_SIGNATURE_NOT_COVERED
    )
    with pytest.raises(tools.ToolFailure) as caught:
        admit(stated, covers=contract_table.covers)
    assert caught.value.kind == KIND_OP_SIGNATURE_NOT_COVERED


def test_a_bf16_record_of_a_layout_no_entry_has_is_not_covered():
    stated = content(op=bf16_record("gemm", layout="col_major"))
    assert refused_for_step(stated, True, Recorder(True)) == (
        KIND_OP_SIGNATURE_NOT_COVERED
    )


def test_a_bf16_record_without_draws_or_tolerance_has_those_answers():
    no_draws = content(op=bf16_record("swiglu"), draws=ABSENT, tolerance=ABSENT)
    assert refused_for_step(no_draws, True) == KIND_DRAWS_NOT_STATED
    no_tolerance = content(op=bf16_record("swiglu"), tolerance=ABSENT)
    assert refused_for_step(no_tolerance, True) == KIND_TOLERANCE_NOT_STATED
    unstated = content(op=ABSENT)
    for bf16_step in (True, False):
        recorder = Recorder(True)
        kind = refused_for_step(unstated, bf16_step, recorder)
        assert kind == KIND_OP_SIGNATURE_NOT_STATED
        assert recorder.calls == []


@pytest.mark.parametrize("given", [None, 1, 0, "True", [True]])
def test_admit_for_step_refuses_a_bf16_step_that_is_no_bool(given):
    recorder = Recorder(True)
    with pytest.raises(TypeError, match="^bf16_step: "):
        admit_for_step(content(), covers=recorder, bf16_step=given)
    assert recorder.calls == []


def test_admit_for_step_checks_the_instance_and_covers_first():
    with pytest.raises(TypeError, match="^instance: "):
        admit_for_step(None, covers=gemm_contract.covers, bf16_step=None)
    with pytest.raises(TypeError, match="^covers: "):
        admit_for_step(content(), covers=None, bf16_step=None)
    with pytest.raises(TypeError, match="^covers: "):
        admit_for_step(content(), covers=Recorder(None), bf16_step=False)


def test_admit_for_step_has_no_default_and_named_parameters():
    parameters = list(inspect.signature(admit_for_step).parameters.values())
    assert [parameter.name for parameter in parameters] == [
        "instance",
        "covers",
        "bf16_step",
    ]
    assert [parameter.kind for parameter in parameters] == [
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
        inspect.Parameter.KEYWORD_ONLY,
    ]
    assert all(parameter.default is inspect.Parameter.empty for parameter in parameters)


# An sdpa_kv_cache record (ADR-0177 decision 3)

SDPA_SHAPE = {"m": 1, "l": 2, "h": 4, "h_kv": 2, "d": 4}


@pytest.mark.parametrize(
    "shape",
    [
        SDPA_SHAPE,
        {"d": 4, "h_kv": 2, "h": 4, "l": 2, "m": 1},
        {"m": 2, "l": 3, "h": 3, "h_kv": 3, "d": 2},
    ],
    ids=["h-multiple-of-h_kv", "members-in-another-order", "h-equals-h_kv"],
)
def test_a_covered_sdpa_record_is_admitted_in_the_order_of_task_contract(shape):
    stated = content(
        op={**bf16_record("gemm"), "kind": "sdpa_kv_cache", "shape": shape}
    )
    dims = tuple(shape[name] for name in ("m", "l", "h", "h_kv", "d"))
    expected = Bf16Admitted("sdpa_kv_cache", "bf16", dims, TEST_DRAWS, 0.25, 3.0)
    recorder = Recorder(True)
    for admitted in (
        admit(stated, covers=contract_table.covers),
        admit_for_step(stated, covers=recorder, bf16_step=True),
    ):
        assert type(admitted) is Bf16Admitted
        assert admitted == expected
    assert len(recorder.calls) == 1


def test_an_sdpa_record_is_refused_by_the_registered_predicate_and_an_fp32_step():
    stated = content(
        op={**bf16_record("gemm"), "kind": "sdpa_kv_cache", "shape": SDPA_SHAPE}
    )
    assert refused_for_step(stated, True, contract_table.check_covers) == (
        KIND_OP_SIGNATURE_NOT_COVERED
    )
    assert refused_for_step(stated, False, Recorder(True)) == (
        KIND_OP_SIGNATURE_NOT_COVERED
    )
    assert refused_for_step(stated, True, Recorder(False)) == (
        KIND_OP_SIGNATURE_NOT_COVERED
    )
    missing = content(
        op={**bf16_record("gemm"), "kind": "sdpa_kv_cache", "shape": SDPA_SHAPE},
        draws=ABSENT,
    )
    assert refused_for_step(missing, True, Recorder(True)) == KIND_DRAWS_NOT_STATED
