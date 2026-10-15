import ast
import copy
import json
import typing
from pathlib import Path

import pytest

from hilclaw import instance, keys, run_objective, tools
from hilclaw.harness import memory_ceiling, timing
from hilclaw.run_objective import (
    KIND_OBJECTIVE_NOT_COVERED,
    KIND_OBJECTIVE_NOT_STATED,
    KINDS,
    Admitted,
    admit,
)

MESSAGE_LIMIT = 200
RUN = "run-a"
LATENCY = {"type": "latency_minimisation"}
# The one value ADR-0053 decision 4 gives today.
TODAY = {"objectives": [{"type": "latency_minimisation"}], "constraints": []}
# Hand-built, invalid in a file today (ADR-0053 decision 4); test values, not recommended bounds.
TEST_BOUND = 123456789
CEILING = {"type": "memory_ceiling", "bound": TEST_BOUND}
OTHER = {"type": "zq7_other_type", "bound": 7}


def objective(objectives=(LATENCY,), constraints=()):
    return {
        "objectives": [copy.deepcopy(entry) for entry in objectives],
        "constraints": [copy.deepcopy(entry) for entry in constraints],
    }


NOT_COVERED = {
    "other_type": objective(objectives=[{"type": "throughput_maximisation"}]),
    "two_objectives": objective(objectives=[LATENCY, LATENCY]),
    "zero_objectives": objective(objectives=[]),
    "weight": objective(objectives=[{"type": "latency_minimisation", "weight": 1}]),
    "priority": objective(objectives=[{"type": "latency_minimisation", "priority": 1}]),
    "other_constraint": objective(constraints=[OTHER]),
    "other_constraint_beside_ceiling": objective(constraints=[CEILING, OTHER]),
    "ceiling_and_other_type_objective": objective(
        objectives=[{"type": "throughput_maximisation"}], constraints=[CEILING]
    ),
}

MALFORMED = {
    "list": [TODAY],
    "str": "latency_minimisation",
    "int": 0,
    "dict_subclass": type("D", (dict,), {})(TODAY),
    "missing_objectives": {"constraints": []},
    "missing_constraints": {"objectives": [LATENCY]},
    "empty": {},
    "third_member": {**TODAY, "extra": 1},
    "objectives_tuple": {"objectives": (LATENCY,), "constraints": []},
    "constraints_none": {"objectives": [LATENCY], "constraints": None},
    "objective_entry_str": {"objectives": ["latency_minimisation"], "constraints": []},
    "constraint_entry_list": {
        "objectives": [LATENCY],
        "constraints": [["memory_ceiling"]],
    },
    "constraint_without_type": {"objectives": [LATENCY], "constraints": [{"bound": 1}]},
    "constraint_type_int": {
        "objectives": [LATENCY],
        "constraints": [{"type": 1, "bound": 1}],
    },
    "two_ceilings": objective(constraints=[CEILING, CEILING]),
    "ceiling_without_bound": objective(constraints=[{"type": "memory_ceiling"}]),
    "ceiling_extra_member": objective(constraints=[{**CEILING, "unit": "bytes"}]),
    "bound_float": objective(constraints=[{"type": "memory_ceiling", "bound": 5.0}]),
    "bound_bool": objective(constraints=[{"type": "memory_ceiling", "bound": True}]),
    "bound_str": objective(constraints=[{"type": "memory_ceiling", "bound": "5"}]),
}


def failure_of(value):
    with pytest.raises(tools.ToolFailure) as caught:
        admit(value)
    return caught.value


def test_the_kinds_and_their_order():
    assert KIND_OBJECTIVE_NOT_STATED == "objective_not_stated"
    assert KIND_OBJECTIVE_NOT_COVERED == "objective_not_covered"
    assert KINDS == (KIND_OBJECTIVE_NOT_STATED, KIND_OBJECTIVE_NOT_COVERED)
    for kind in KINDS:
        tools.ToolFailure(kind, "x")


def test_today_s_only_value_gives_interval_and_no_ceiling_stated():
    value = copy.deepcopy(TODAY)

    admitted = admit(value)

    assert admitted == Admitted("interval", None)
    assert type(admitted) is Admitted
    assert admitted.sample_form == "interval" and admitted.bound is None
    assert admitted.sample_form in timing.SAMPLE_FORMS
    assert value == TODAY


@pytest.mark.parametrize("bound", [0, 1, TEST_BOUND, memory_ceiling.BOUND_MAX])
def test_a_memory_ceiling_entry_gives_its_bound_as_stated(bound):
    value = objective(constraints=[{"type": "memory_ceiling", "bound": bound}])
    before = copy.deepcopy(value)

    admitted = admit(value)

    assert admitted == Admitted("interval", bound)
    assert admitted.sample_form in timing.SAMPLE_FORMS
    assert value == before


def test_the_members_of_an_entry_may_come_in_any_order():
    value = objective(constraints=[{"bound": TEST_BOUND, "type": "memory_ceiling"}])
    assert admit(value) == Admitted("interval", TEST_BOUND)


def test_none_is_not_stated():
    caught = failure_of(None)
    assert caught.kind == KIND_OBJECTIVE_NOT_STATED
    assert caught.error_object()["error"]["kind"] == "objective_not_stated"


@pytest.mark.parametrize("value", NOT_COVERED.values(), ids=NOT_COVERED.keys())
def test_each_shape_that_is_not_covered(value):
    before = copy.deepcopy(value)
    assert failure_of(value).kind == KIND_OBJECTIVE_NOT_COVERED
    assert value == before


@pytest.mark.parametrize("value", MALFORMED.values(), ids=MALFORMED.keys())
def test_a_value_read_cannot_return_is_a_type_error_and_never_covered(value):
    with pytest.raises(TypeError):
        admit(value)


@pytest.mark.parametrize(
    "bound", [-1, memory_ceiling.BOUND_MAX + 1, 10**5000], ids=["neg", "max1", "huge"]
)
def test_a_bound_outside_its_written_form_is_a_value_error(bound):
    with pytest.raises(ValueError):
        admit(objective(constraints=[{"type": "memory_ceiling", "bound": bound}]))


def test_a_malformed_value_is_rejected_before_coverage():
    value = {"objectives": [LATENCY, LATENCY], "constraints": [{"bound": 1}]}
    with pytest.raises(TypeError):
        admit(value)


def test_coverage_is_answered_before_the_ceiling_entry_is_checked():
    value = objective(
        objectives=[], constraints=[{"type": "memory_ceiling", "bound": -1}]
    )
    assert failure_of(value).kind == KIND_OBJECTIVE_NOT_COVERED


def test_not_stated_wins_and_is_the_first_kind():
    assert failure_of(None).kind == KINDS[0]
    assert failure_of(NOT_COVERED["two_objectives"]).kind == KINDS[1]


def test_the_messages_are_short_name_the_member_and_show_no_value():
    marker = "zq7-marker-zq7"
    values = [
        None,
        objective(objectives=[{"type": marker}]),
        objective(constraints=[{"type": marker, "bound": 987654321}]),
    ]
    for value in values:
        caught = failure_of(value)
        assert len(caught.message) <= MESSAGE_LIMIT
        assert caught.message.startswith("objective")
        assert marker not in caught.message and "987654321" not in caught.message
    for kind in KINDS:
        assert len(run_objective._MESSAGES[kind]) <= MESSAGE_LIMIT
    for value in MALFORMED.values():
        with pytest.raises(TypeError) as caught:
            admit(value)
        assert len(str(caught.value)) <= MESSAGE_LIMIT
        assert str(caught.value).startswith("objective")


def test_admit_has_no_default_and_keeps_nothing():
    with pytest.raises(TypeError):
        admit()
    assert admit(copy.deepcopy(TODAY)) == admit(copy.deepcopy(TODAY))
    first = objective(constraints=[CEILING])
    assert admit(first).bound == TEST_BOUND
    assert admit(copy.deepcopy(TODAY)).bound is None


def test_public_names_and_imports():
    public = {name for name in vars(run_objective) if not name.startswith("_")}
    assert public == {
        "Admitted",
        "KINDS",
        "KIND_OBJECTIVE_NOT_COVERED",
        "KIND_OBJECTIVE_NOT_STATED",
        "admit",
        "memory_ceiling",
        "tools",
        "typing",
    }
    assert Admitted._fields == ("sample_form", "bound")
    assert Admitted._field_defaults == {}
    assert issubclass(Admitted, tuple) and typing.NamedTuple in Admitted.__orig_bases__
    tree = ast.parse(Path(run_objective.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
    assert imported == {"typing", "hilclaw.tools", "hilclaw.harness.memory_ceiling"}


# --- through a real instance.json and objective_of ---


def write_instance(root, **members):
    profile = {
        "schema_version": 1,
        "accelerator": "zq7_acc",
        "revision": "rev 1",
        "toolchain": {"cc": "1.0"},
        "host": {"cpu": "cpu x", "os": "os y"},
        "hw_source": "external",
    }
    content = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(profile).name, "record": profile},
        **members,
    }
    path = root / "runs" / RUN / "instance.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(content), encoding="utf-8")


def test_a_valid_file_with_the_member_is_covered(tmp_path):
    write_instance(tmp_path, objective=TODAY)

    assert admit(instance.objective_of(tmp_path, RUN)) == Admitted("interval", None)


def test_a_valid_file_without_the_member_is_not_stated(tmp_path):
    write_instance(tmp_path)

    assert (
        failure_of(instance.objective_of(tmp_path, RUN)).kind
        == KIND_OBJECTIVE_NOT_STATED
    )
