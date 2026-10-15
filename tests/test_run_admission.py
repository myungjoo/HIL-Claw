import ast
import copy
import inspect
import itertools
import json
import typing
from pathlib import Path

import pytest

from hilclaw import (
    check_admission,
    gemm_contract,
    instance,
    keys,
    run_admission,
    run_objective,
    run_parameters,
    tools,
)
from hilclaw.run_admission import (
    KIND_N_MAX_NOT_STATED,
    KIND_OP_SIGNATURE_NOT_COVERED,
    KIND_OP_SIGNATURE_NOT_STATED,
    KINDS,
    Admitted,
    admit,
)

MARKER = "zq7-marker-zq7"
MESSAGE_LIMIT = 200
ABSENT = object()
MEMBER = {
    "op_signature_not_stated": "op_signature",
    "op_signature_not_covered": "op_signature",
    "objective_not_stated": "objective",
    "objective_not_covered": "objective",
    "n_max_not_stated": "n_max",
}
# The Walk-through of ADR-0067: n_max 10 is what a file states, not a default.
TEST_N_MAX = 10
RECORD = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": {"m": 1, "k": 2048, "n": 8192},
    "dtype": "fp32",
    "layout": "row_major",
}
OBJECTIVE = {"objectives": [{"type": "latency_minimisation"}], "constraints": []}
# Hand-built: no valid file holds a memory_ceiling entry today (ADR-0053 decision 4). A test value.
TEST_BOUND = 123456789
CEILING_OBJECTIVE = {
    "objectives": [{"type": "latency_minimisation"}],
    "constraints": [{"type": "memory_ceiling", "bound": TEST_BOUND}],
}
NOT_COVERED_OBJECTIVE = {
    "objectives": [{"type": "throughput_maximisation"}],
    "constraints": [],
}
NOT_COVERED = [{"dtype": "fp16"}, {"layout": "col_major"}, {"m": 0}, {"k": 0}, {"n": 0}]


def record(**changes):
    changed = copy.deepcopy(RECORD)
    for name, value in changes.items():
        target = changed["shape"] if name in changed["shape"] else changed
        target[name] = value
    return changed


def content(
    op=RECORD,
    objective=OBJECTIVE,
    n_max=TEST_N_MAX,
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
        document["op_signature"] = {"key": keys.op_signature_key(op).name, "record": op}
    if n_max is not ABSENT:
        document["n_max"] = n_max
    stated = instance.parse(json.dumps(document).encode())
    if objective is not ABSENT:
        stated = stated._replace(objective=copy.deepcopy(objective))
    return stated


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


def test_the_kinds_and_their_order():
    assert KIND_OP_SIGNATURE_NOT_STATED == "op_signature_not_stated"
    assert KIND_OP_SIGNATURE_NOT_COVERED == "op_signature_not_covered"
    assert KIND_N_MAX_NOT_STATED == "n_max_not_stated"
    assert KINDS == (
        "op_signature_not_stated",
        "op_signature_not_covered",
        "objective_not_stated",
        "objective_not_covered",
        "n_max_not_stated",
    )
    assert KINDS[2:4] == run_objective.KINDS
    for kind in KINDS:
        assert kind not in tools.RESERVED_KINDS
        tools.ToolFailure(kind, "x")


def test_the_op_signature_kinds_have_the_spelling_of_the_check():
    assert KIND_OP_SIGNATURE_NOT_STATED == check_admission.KIND_OP_SIGNATURE_NOT_STATED
    assert (
        KIND_OP_SIGNATURE_NOT_COVERED == check_admission.KIND_OP_SIGNATURE_NOT_COVERED
    )


@pytest.mark.parametrize(
    ("objective", "bound"), [(OBJECTIVE, None), (CEILING_OBJECTIVE, TEST_BOUND)]
)
def test_the_walk_through_first_row_is_admitted_with_its_values(objective, bound):
    stated = content(objective=objective)
    before = copy.deepcopy(stated)
    admitted = admit(stated, covers=gemm_contract.covers)
    assert type(admitted) is Admitted
    assert admitted == (1, 2048, 8192, TEST_N_MAX, "interval", bound)
    shape = stated.op_signature.record["shape"]
    assert admitted.m is shape["m"]
    assert admitted.k is shape["k"]
    assert admitted.n is shape["n"]
    assert admitted.n_max is stated.n_max
    assert admitted.bound is run_objective.admit(stated.objective).bound
    assert stated == before


def test_admitted_has_six_fields_and_no_default():
    assert Admitted._fields == ("m", "k", "n", "n_max", "sample_form", "bound")
    assert Admitted._field_defaults == {}
    with pytest.raises(TypeError):
        Admitted(1, 2, 3, 4, "interval")


def test_an_admitted_value_and_a_seed_build_the_timing_parameters():
    admitted = admit(content(op=record(m=5, k=6, n=7)), covers=gemm_contract.covers)
    built = run_parameters.TimingParameters(
        admitted.m,
        admitted.k,
        admitted.n,
        admitted.n_max,
        admitted.sample_form,
        seed=42,
    )
    assert built == (5, 6, 7, TEST_N_MAX, "interval", 42)


OPS = {"absent": ABSENT, "not_covered": record(dtype="fp16"), "covered": RECORD}
OBJECTIVES = {
    "absent": ABSENT,
    "not_covered": NOT_COVERED_OBJECTIVE,
    "covered": OBJECTIVE,
}
N_MAXES = {"absent": ABSENT, "present": TEST_N_MAX}


def first_answer(op, objective, n_max):
    if op == "absent":
        return KIND_OP_SIGNATURE_NOT_STATED
    if op == "not_covered":
        return KIND_OP_SIGNATURE_NOT_COVERED
    if objective == "absent":
        return run_objective.KIND_OBJECTIVE_NOT_STATED
    if objective == "not_covered":
        return run_objective.KIND_OBJECTIVE_NOT_COVERED
    if n_max == "absent":
        return KIND_N_MAX_NOT_STATED
    return None


ORDER = [
    (op, objective, n_max, first_answer(op, objective, n_max))
    for op, objective, n_max in itertools.product(OPS, OBJECTIVES, N_MAXES)
]


def test_the_order_table_spans_every_answer():
    assert {kind for *_, kind in ORDER} == set(KINDS) | {None}
    assert len(ORDER) == 18


@pytest.mark.parametrize(("op", "objective", "n_max", "kind"), ORDER)
def test_a_content_has_the_first_answer_of_decision_5(op, objective, n_max, kind):
    stated = content(op=OPS[op], objective=OBJECTIVES[objective], n_max=N_MAXES[n_max])
    before = copy.deepcopy(stated)
    if kind is None:
        assert type(admit(stated, covers=gemm_contract.covers)) is Admitted
    else:
        refused(stated, kind)
    assert stated == before


@pytest.mark.parametrize(
    ("op", "objective", "n_max", "kind"),
    [
        (RECORD, OBJECTIVE, ABSENT, "n_max_not_stated"),
        (ABSENT, OBJECTIVE, TEST_N_MAX, "op_signature_not_stated"),
        (ABSENT, None, ABSENT, "op_signature_not_stated"),
        (record(dtype="fp16"), OBJECTIVE, TEST_N_MAX, "op_signature_not_covered"),
        (record(m=0), OBJECTIVE, TEST_N_MAX, "op_signature_not_covered"),
        (RECORD, None, ABSENT, "objective_not_stated"),
        (RECORD, NOT_COVERED_OBJECTIVE, ABSENT, "objective_not_covered"),
    ],
)
def test_the_walk_through_rows(op, objective, n_max, kind):
    refused(content(op=op, objective=objective, n_max=n_max), kind)


@pytest.mark.parametrize("change", NOT_COVERED)
def test_each_record_the_contract_does_not_cover(change):
    refused(content(op=record(**change)), KIND_OP_SIGNATURE_NOT_COVERED)


def test_covers_is_not_called_when_no_op_signature_is_stated():
    for answer in (True, False, "yes", ValueError(MARKER)):
        covers = Recorder(answer)
        refused(content(op=ABSENT), KIND_OP_SIGNATURE_NOT_STATED, covers)
        assert covers.calls == []


@pytest.mark.parametrize(
    ("objective", "n_max", "kind"),
    [
        (OBJECTIVE, TEST_N_MAX, None),
        (None, TEST_N_MAX, "objective_not_stated"),
        (OBJECTIVE, ABSENT, "n_max_not_stated"),
    ],
)
def test_covers_is_called_once_with_the_record_the_instance_holds(
    objective, n_max, kind
):
    stated = content(op=record(label=MARKER), objective=objective, n_max=n_max)
    held = stated.op_signature.record
    for answer in (True, False):
        covers = Recorder(answer)
        if answer and kind is None:
            admit(stated, covers=covers)
        else:
            refused(stated, kind if answer else KIND_OP_SIGNATURE_NOT_COVERED, covers)
        assert len(covers.calls) == 1
        assert covers.calls[0] is held


@pytest.mark.parametrize("bad", [{"objectives": []}, "latency_minimisation", 3])
def test_the_objective_is_not_reached_after_an_op_signature_answer(bad):
    refused(content(op=ABSENT, objective=bad), KIND_OP_SIGNATURE_NOT_STATED)
    refused(content(op=record(n=0), objective=bad), KIND_OP_SIGNATURE_NOT_COVERED)
    with pytest.raises(TypeError):
        admit(content(objective=bad), covers=gemm_contract.covers)


@pytest.mark.parametrize(
    ("bad", "error"),
    [
        ({"objectives": []}, TypeError),
        ([OBJECTIVE], TypeError),
        (
            {
                "objectives": [{"type": "latency_minimisation"}],
                "constraints": [{"type": "memory_ceiling", "bound": -1}],
            },
            ValueError,
        ),
    ],
)
@pytest.mark.parametrize("n_max", [TEST_N_MAX, ABSENT])
def test_what_run_objective_raises_passes_through(bad, error, n_max):
    stated = content(objective=bad, n_max=n_max)
    with pytest.raises(error) as caught:
        admit(stated, covers=gemm_contract.covers)
    with pytest.raises(error) as expected:
        run_objective.admit(stated.objective)
    assert str(caught.value) == str(expected.value)


def test_no_bound_is_substituted_and_the_harness_is_not_imported():
    refused(content(n_max=ABSENT), KIND_N_MAX_NOT_STATED)
    tree = ast.parse(Path(run_admission.__file__).read_text(encoding="utf-8"))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    names |= {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not {"harness", "measurement", "N_MAX_DEFAULT"} & names


@pytest.mark.parametrize("accelerator", ["cpu_standin", "mock", "another_name"])
@pytest.mark.parametrize(("op", "objective", "n_max", "kind"), ORDER)
def test_the_rest_of_the_instance_changes_no_answer(
    accelerator, op, objective, n_max, kind
):
    stated = content(
        op=OPS[op],
        objective=OBJECTIVES[objective],
        n_max=N_MAXES[n_max],
        accelerator=accelerator,
        tolerance={"rtol": 0.5, "atol": 1.0},
        draws=3,
        some_other_member={"n_max": 99, "op_signature": MARKER},
    )
    assert stated.others == {"some_other_member": {"n_max": 99, "op_signature": MARKER}}
    if stated.op_signature is not None:
        rekeyed = stated.op_signature._replace(key=MARKER)
        stated = stated._replace(op_signature=rekeyed, hw_profile_key=MARKER)
    if kind is None:
        assert admit(stated, covers=gemm_contract.covers) == (
            1,
            2048,
            8192,
            TEST_N_MAX,
            "interval",
            None,
        )
    else:
        refused(stated, kind)


@pytest.mark.parametrize(
    "raised", [ValueError(MARKER), keys.InvalidRecordError(MARKER), KeyboardInterrupt()]
)
def test_what_covers_raises_passes_through_as_the_same_object(raised):
    covers = Recorder(raised)
    with pytest.raises(type(raised)) as caught:
        admit(content(), covers=covers)
    assert caught.value is raised


@pytest.mark.parametrize("answer", [1, 0, None, "True", 1.0, []])
def test_an_answer_of_covers_that_is_no_bool_is_a_type_error(answer):
    covers = Recorder(answer)
    with pytest.raises(TypeError):
        admit(content(), covers=covers)
    assert len(covers.calls) == 1


def instance_like():
    stated = content()

    class Derived(instance.Instance):
        pass

    return [None, tuple(stated), stated._asdict(), Derived(*stated), instance.Instance]


@pytest.mark.parametrize("not_an_instance", instance_like())
def test_an_instance_of_another_type_is_a_type_error_before_covers(not_an_instance):
    covers = Recorder(True)
    with pytest.raises(TypeError):
        admit(not_an_instance, covers=covers)
    assert covers.calls == []
    with pytest.raises(TypeError):
        admit(not_an_instance, covers=None)


@pytest.mark.parametrize("covers", [None, "covers", 1, True, RECORD])
@pytest.mark.parametrize(
    "stated",
    [content(), content(op=ABSENT), content(objective=None), content(n_max=ABSENT)],
)
def test_a_covers_that_is_not_callable_is_a_type_error_before_any_answer(
    covers, stated
):
    with pytest.raises(TypeError):
        admit(stated, covers=covers)


def test_the_arguments_are_one_instance_and_covers_by_name():
    stated = content()
    with pytest.raises(TypeError):
        admit()
    with pytest.raises(TypeError):
        admit(stated)
    with pytest.raises(TypeError):
        admit(stated, gemm_contract.covers)
    assert admit(instance=stated, covers=gemm_contract.covers) == admit(
        stated, covers=gemm_contract.covers
    )


def test_no_message_shows_anything_of_the_content():
    long = MARKER * 18
    marked = record(label=long, ext={"variant": long})
    messages = [
        refused(content(op=ABSENT, owner=long), KIND_OP_SIGNATURE_NOT_STATED),
        refused(content(op=marked), KIND_OP_SIGNATURE_NOT_COVERED, Recorder(False)),
        refused(content(op=marked, n_max=ABSENT), KIND_N_MAX_NOT_STATED),
    ]
    key = content(op=marked).op_signature.key
    for message in messages:
        assert key not in message
        assert "8192" not in message and "2048" not in message
        assert "check" not in message
    assert len(set(messages)) == 3


def test_a_call_writes_no_file_and_keeps_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for _ in range(2):
        refused(content(op=ABSENT), KIND_OP_SIGNATURE_NOT_STATED)
        refused(content(op=record(n=0)), KIND_OP_SIGNATURE_NOT_COVERED)
        refused(content(n_max=ABSENT), KIND_N_MAX_NOT_STATED)
        assert admit(content(), covers=gemm_contract.covers).n_max == TEST_N_MAX
    assert list(tmp_path.iterdir()) == []


def test_the_module_imports_what_its_docstring_names():
    own = Path(run_admission.__file__)
    names = set()
    for node in ast.walk(ast.parse(own.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    assert names == {
        "typing",
        "hilclaw.instance",
        "hilclaw.run_objective",
        "hilclaw.tools",
    }
    assert not hasattr(run_admission, "main")


def test_public_names_of_the_module_and_no_default():
    public = {
        name
        for name, value in vars(run_admission).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {
        "KIND_OP_SIGNATURE_NOT_STATED",
        "KIND_OP_SIGNATURE_NOT_COVERED",
        "KIND_N_MAX_NOT_STATED",
        "KINDS",
        "Admitted",
        "admit",
    }
    assert typing.NamedTuple in Admitted.__orig_bases__
    parameters = list(inspect.signature(admit).parameters.values())
    assert [parameter.name for parameter in parameters] == ["instance", "covers"]
    assert parameters[1].kind is inspect.Parameter.KEYWORD_ONLY
    assert all(parameter.default is inspect.Parameter.empty for parameter in parameters)
