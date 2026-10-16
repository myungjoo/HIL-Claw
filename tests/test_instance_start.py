import ast
import copy
import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

from hilclaw import (
    gemm_contract,
    instance,
    instance_start,
    keys,
    mock_backend,
    standin_profile,
)
from hilclaw.harness import measurement
from hilclaw.instance import InvalidInstanceError, UnsupportedVersionError
from hilclaw.instance_start import (
    REPORT_ORDER,
    MissingMembersError,
    OutOfScopeError,
    prepare,
)

ABSENT = object()
MARKER = "zq7-marker-zq7"
# Test values only: none is a default or a recommended value.
TEST_N_MAX = 12
TEST_CANDIDATES = 2
TEST_DRAWS = 3
TEST_TOLERANCE = {"rtol": 0.25, "atol": 3.0}
OBJECTIVE = {"objectives": [{"type": "latency_minimisation"}], "constraints": []}
RECORD = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": {"m": 1, "k": 2048, "n": 8192},
    "dtype": "fp32",
    "layout": "row_major",
}
ACCELERATORS = (standin_profile.ACCELERATOR, mock_backend.NAME)


def op_record(**changes):
    changed = copy.deepcopy(RECORD)
    for name, value in changes.items():
        target = changed["shape"] if name in changed["shape"] else changed
        target[name] = value
    return changed


def op_member(record):
    return {"key": keys.op_signature_key(record).name, "record": record}


def document(
    accelerator=standin_profile.ACCELERATOR,
    op_signature=RECORD,
    objective=OBJECTIVE,
    candidates_per_round=TEST_CANDIDATES,
    n_max=TEST_N_MAX,
    draws=TEST_DRAWS,
    tolerance=TEST_TOLERANCE,
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
    made = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(profile).name, "record": profile},
    }
    stated = {
        "op_signature": op_signature
        if op_signature is ABSENT
        else op_member(op_signature),
        "objective": objective,
        "candidates_per_round": candidates_per_round,
        "n_max": n_max,
        "draws": draws,
        "tolerance": tolerance,
    }
    made.update(
        {
            name: copy.deepcopy(value)
            for name, value in stated.items()
            if value is not ABSENT
        }
    )
    made.update(others)
    return made


def call(given, accelerators=ACCELERATORS, covers=gemm_contract.covers):
    return prepare(given, accelerators=accelerators, covers=covers)


class Recorder:
    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def __call__(self, handed):
        self.calls.append(handed)
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer


def without(*names, **changes):
    return document(**{name: ABSENT for name in names}, **changes)


def refused(given):
    before = copy.deepcopy(given)
    with pytest.raises(MissingMembersError) as caught:
        call(given)
    assert given == before
    return caught.value


@pytest.mark.parametrize("accelerator", ACCELERATORS)
def test_a_document_stating_all_six_is_returned_equal_as_a_new_object(accelerator):
    given = document(accelerator)
    before = copy.deepcopy(given)
    prepared = call(given)
    assert prepared == before
    assert prepared is not given
    assert type(prepared) is dict
    assert prepared["n_max"] == TEST_N_MAX
    assert given == before
    instance.validate(prepared)


@pytest.mark.parametrize("accelerator", ACCELERATORS)
def test_without_n_max_the_default_of_measurement_is_filled_in(accelerator):
    given = without("n_max", accelerator=accelerator)
    prepared = call(given)
    assert prepared["n_max"] == measurement.N_MAX_DEFAULT
    assert type(prepared["n_max"]) is int
    assert "n_max" not in given
    assert {name: value for name, value in prepared.items() if name != "n_max"} == given
    instance.validate(prepared)
    assert (
        instance.parse(json.dumps(prepared).encode()).n_max == measurement.N_MAX_DEFAULT
    )


def test_nested_values_are_shared_and_not_copied():
    given = document()
    prepared = call(given)
    assert all(prepared[name] is given[name] for name in given)


def test_a_member_instance_does_not_define_is_kept_as_given():
    extra = {"anything": [1, {"x": None}]}
    given = document(task=extra, tolerence="kept")
    prepared = call(given)
    assert prepared["task"] is extra
    assert prepared["tolerence"] == "kept"
    assert set(prepared) == set(given)


def test_members_the_record_leaves_open_are_neither_required_nor_checked():
    given = document(
        round_budget=1,
        wall_clock_budget_s=1,
        owner="o",
        project="p",
        source_commit="a" * 40,
    )
    assert call(given) == given


def test_report_order_is_that_of_adr_0076_decision_3():
    assert REPORT_ORDER == (
        "op_signature",
        "objective",
        "candidates_per_round",
        "draws",
        "tolerance",
    )
    assert type(REPORT_ORDER) is tuple
    assert "n_max" not in REPORT_ORDER


@pytest.mark.parametrize("accelerator", ACCELERATORS)
@pytest.mark.parametrize("name", REPORT_ORDER)
def test_each_member_missing_alone_is_reported_alone(name, accelerator):
    error = refused(without(name, accelerator=accelerator))
    assert error.missing == (name,)
    assert type(error.missing) is tuple
    assert name in str(error)


@pytest.mark.parametrize("name", REPORT_ORDER)
def test_a_missing_member_is_reported_also_without_n_max(name):
    assert refused(without(name, "n_max")).missing == (name,)


def test_walk_through_row_4_a_mock_stating_only_objective_and_tolerance():
    given = without(
        "op_signature",
        "candidates_per_round",
        "n_max",
        "draws",
        accelerator=mock_backend.NAME,
    )
    error = refused(given)
    assert error.missing == ("op_signature", "candidates_per_round", "draws")
    assert "n_max" not in given


def test_all_five_missing_are_reported_in_report_order():
    error = refused(without(*REPORT_ORDER, "n_max"))
    assert error.missing == REPORT_ORDER
    message = str(error)
    positions = [message.index(name) for name in REPORT_ORDER]
    assert positions == sorted(positions)
    assert "n_max" not in message


def test_the_report_order_does_not_follow_the_order_of_the_document():
    given = without("op_signature", "draws", "tolerance")
    reordered = dict(reversed(list(given.items())))
    assert refused(reordered).missing == ("op_signature", "draws", "tolerance")


def test_the_message_shows_no_value_of_the_document():
    given = without("draws", "tolerance", **{MARKER: MARKER})
    given["hw_profile"]["record"]["revision"] = MARKER
    given["hw_profile"]["key"] = keys.hw_profile_key(given["hw_profile"]["record"]).name
    message = str(refused(given))
    assert MARKER not in message
    assert message.index("draws") < message.index("tolerance")


@pytest.mark.parametrize("accelerator", ["acc_other", "mocks", "cpu_standin2"])
@pytest.mark.parametrize("missing", [(), ("n_max",), REPORT_ORDER + ("n_max",)])
def test_another_accelerator_is_out_of_scope_and_nothing_is_filled_in(
    accelerator, missing
):
    given = without(*missing, accelerator=accelerator)
    before = copy.deepcopy(given)
    with pytest.raises(OutOfScopeError) as caught:
        call(given)
    assert "accelerator" in str(caught.value)
    assert accelerator not in str(caught.value)
    assert given == before


@pytest.mark.parametrize("accelerator", ACCELERATORS)
@pytest.mark.parametrize(
    "change",
    [{"dtype": "fp16"}, {"layout": "col_major"}, {"m": 0}, {"k": 0}, {"n": 0}],
)
@pytest.mark.parametrize("missing", [(), ("objective", "draws", "tolerance", "n_max")])
def test_an_uncovered_op_signature_is_out_of_scope(accelerator, change, missing):
    given = without(*missing, accelerator=accelerator, op_signature=op_record(**change))
    before = copy.deepcopy(given)
    with pytest.raises(OutOfScopeError) as caught:
        call(given)
    assert str(caught.value).startswith("op_signature: ")
    assert given == before


def test_out_of_scope_is_no_value_error_and_missing_is_none_either():
    assert not issubclass(OutOfScopeError, ValueError)
    assert not issubclass(MissingMembersError, ValueError)
    assert not issubclass(OutOfScopeError, MissingMembersError)
    assert not issubclass(MissingMembersError, OutOfScopeError)


@pytest.mark.parametrize("accelerator", ACCELERATORS)
def test_no_op_signature_with_an_accelerator_in_scope_is_in_scope_and_refused(
    accelerator,
):
    assert refused(without("op_signature", accelerator=accelerator)).missing == (
        "op_signature",
    )


@pytest.mark.parametrize(
    "given",
    [None, b"{}", [], (), "{}", 1, json.dumps(document()).encode()],
    ids=["none", "bytes", "list", "tuple", "str", "int", "bytes_of_valid_content"],
)
def test_a_document_that_is_not_a_dict_is_a_type_error(given):
    with pytest.raises(TypeError):
        call(given)


def test_a_dict_subclass_is_a_type_error():
    class Sub(dict):
        pass

    given = Sub(document())
    with pytest.raises(TypeError):
        call(given)


@pytest.mark.parametrize(
    "value", [4, 0, -1, True, False, 10.0, "10", None, keys.MAX_INTEGER + 1]
)
def test_an_invalid_n_max_is_refused_and_never_replaced(value):
    given = document(n_max=value)
    before = copy.deepcopy(given)
    with pytest.raises(InvalidInstanceError) as caught:
        call(given)
    assert "n_max" in str(caught.value)
    assert given == before


@pytest.mark.parametrize(
    "given",
    [
        {"schema_version": 1},
        {"schema_version": 1, "hw_profile": {"key": "x", "record": {}}},
        document(draws=0),
        document(tolerance={"rtol": -1.0, "atol": 0.0}),
        without(
            "op_signature",
            "candidates_per_round",
            "draws",
            "tolerance",
            "n_max",
            accelerator="acc_other",
            objective={"objectives": [], "constraints": []},
        ),
    ],
    ids=[
        "no_hw_profile",
        "bad_hw_profile",
        "bad_draws",
        "bad_tolerance",
        "invalid_before_scope",
    ],
)
def test_an_invalid_document_raises_invalid_instance_error_before_anything_else(given):
    before = copy.deepcopy(given)
    with pytest.raises(InvalidInstanceError):
        call(given)
    assert given == before


def test_an_invalid_document_missing_members_is_invalid_not_missing():
    given = without("op_signature", "draws", "n_max")
    given["hw_profile"]["key"] = "wrong-key"
    with pytest.raises(InvalidInstanceError):
        call(given)
    assert "n_max" not in given


def test_a_document_of_another_version_is_unsupported():
    given = without(*REPORT_ORDER, "n_max")
    given["schema_version"] = 2
    before = copy.deepcopy(given)
    with pytest.raises(UnsupportedVersionError):
        call(given)
    assert given == before


def test_the_module_imports_no_numpy():
    code = "import sys, hilclaw.instance_start; print('numpy' in sys.modules)"
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "False"


def test_the_module_holds_no_number_of_its_own():
    with open(instance_start.__file__, encoding="utf-8") as source:
        tree = ast.parse(source.read())
    numbers = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and type(node.value) is int
    ]
    assert numbers == []


def test_public_names_of_the_module():
    public = {name for name in vars(instance_start) if not name.startswith("_")}
    assert {
        "REPORT_ORDER",
        "OutOfScopeError",
        "MissingMembersError",
        "prepare",
    } <= public


def test_the_arguments_are_one_document_and_two_by_name_without_default():
    parameters = inspect.signature(prepare).parameters
    assert list(parameters) == ["document", "accelerators", "covers"]
    assert parameters["document"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    for name in ("accelerators", "covers"):
        assert parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
        assert parameters[name].default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        prepare(document())


@pytest.mark.parametrize(
    "accelerators",
    [
        list(ACCELERATORS),
        set(ACCELERATORS),
        None,
        standin_profile.ACCELERATOR,
        (b"mock",),
        (1,),
    ],
    ids=["list", "set", "none", "str", "bytes_item", "int_item"],
)
def test_accelerators_that_are_not_a_tuple_of_str_are_a_type_error(accelerators):
    with pytest.raises(TypeError):
        call(document(), accelerators=accelerators)


def test_an_accelerator_name_of_a_str_subclass_is_a_type_error():
    class Name(str):
        pass

    with pytest.raises(TypeError):
        call(document(), accelerators=(Name(standin_profile.ACCELERATOR),))


@pytest.mark.parametrize("covers", [None, True, "covers"])
def test_a_covers_that_is_not_callable_is_a_type_error(covers):
    with pytest.raises(TypeError):
        call(document(), covers=covers)


def test_the_type_errors_come_before_validity():
    invalid = {"schema_version": 1}
    with pytest.raises(TypeError):
        call(invalid, accelerators=None)
    with pytest.raises(TypeError):
        call(invalid, covers=None)


def test_the_accelerators_handed_over_are_the_scope():
    given = document(accelerator="acc_other")
    assert call(given, accelerators=("acc_other",)) == given
    with pytest.raises(OutOfScopeError):
        call(document(), accelerators=())
    with pytest.raises(OutOfScopeError):
        call(document(), accelerators=(mock_backend.NAME,))


def test_covers_is_called_once_with_the_record_the_document_holds():
    given = document()
    recorder = Recorder(True)
    assert call(given, covers=recorder) == given
    assert len(recorder.calls) == 1
    assert recorder.calls[0] is given["op_signature"]["record"]


def test_a_false_answer_of_covers_is_out_of_scope():
    with pytest.raises(OutOfScopeError):
        call(document(), covers=Recorder(False))


@pytest.mark.parametrize(
    "given",
    [without("op_signature"), document(accelerator="acc_other")],
    ids=["no_op", "other"],
)
def test_covers_is_not_called_without_op_signature_or_for_another_accelerator(given):
    recorder = Recorder(True)
    with pytest.raises((MissingMembersError, OutOfScopeError)):
        call(given, covers=recorder)
    assert recorder.calls == []


def test_covers_is_not_called_for_an_invalid_document():
    recorder = Recorder(True)
    with pytest.raises(InvalidInstanceError):
        call(document(n_max=4), covers=recorder)
    assert recorder.calls == []


@pytest.mark.parametrize("raised", [RuntimeError("x"), keys.InvalidRecordError("y")])
def test_what_covers_raises_passes_through_as_the_same_object(raised):
    with pytest.raises(type(raised)) as caught:
        call(document(), covers=Recorder(raised))
    assert caught.value is raised


@pytest.mark.parametrize("answer", [1, 0, None, "True", [True]])
def test_an_answer_of_covers_that_is_no_bool_is_a_type_error(answer):
    given = document()
    before = copy.deepcopy(given)
    with pytest.raises(TypeError):
        call(given, covers=Recorder(answer))
    assert given == before


def test_the_module_imports_neither_the_standin_nor_the_contract_module():
    with open(instance_start.__file__, encoding="utf-8") as source:
        tree = ast.parse(source.read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
    assert imported == {"hilclaw.instance", "hilclaw.harness.measurement"}
