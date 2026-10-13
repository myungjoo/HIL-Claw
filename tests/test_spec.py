import copy
import enum
import json
from types import MappingProxyType

import pytest

from hilclaw import keys, spec
from hilclaw.spec import InvalidSpecError, validate

REMOVE = object()

# The example of ADR-0002 decision 8, copied from the record.
ADR_EXAMPLE = json.loads(
    """
{
  "schema_version": 1,
  "id": {"run_id": "NOT-DECIDED-HERE", "round": 1, "candidate": 1, "attempt": 1,
         "candidates": 1, "relation": "single"},
  "hw_profile": {"key": "cpu_standin-b0d8610d8f470856",
    "record": {"schema_version": 1, "accelerator": "cpu_standin",
               "revision": "NOT-DECIDED-HERE", "toolchain": {"clang": "NOT-DECIDED-HERE"},
               "host": {"cpu": "NOT-DECIDED-HERE", "os": "NOT-DECIDED-HERE"},
               "hw_source": "NOT-DECIDED-HERE"}},
  "task": {
    "op_signature": {"key": "gemm-c43e96fb16cc3f35",
      "record": {"schema_version": 1, "kind": "gemm",
                 "shape": {"m": 1, "k": 2048, "n": 8192}, "dtype": "fp32",
                 "layout": "NOT-DECIDED-HERE"}},
    "contract": {"language": "c", "prototype": "NOT-DECIDED-HERE",
                 "operands": "NOT-DECIDED-HERE"},
    "objective": "NOT-DECIDED-HERE"},
  "guidance": {"techniques": [{"id": "NOT-DECIDED-HERE", "text": "NOT-DECIDED-HERE"}]},
  "feedback": {"attempts": []}
}
"""
)

# The example of ADR-0050 ("The example of ADR-0002 decision 8, restated"),
# copied from the record.
ADR_0050_EXAMPLE = json.loads(
    """
{
  "schema_version": 2,
  "id": {"run_id": "20261009t012331z-9f3a6c1e0b7d4a52", "round": 1, "candidate": 1, "attempt": 1, "candidates": 1, "relation": "single"},
  "hw_profile": {"key": "cpu_standin-8c0be275e5925ab0",
    "record": {"schema_version": 1, "accelerator": "cpu_standin", "revision": "host",
               "toolchain": {"clang": "Example clang version 0.0.0 (fictitious-build 1)"},
               "host": {"cpu": "Example(R) Fictitious(TM) X-0000 CPU @ 0.00GHz", "os": "linux exampleos 0.0"}, "hw_source": "external"}},
  "task": {
    "op_signature": {"key": "gemm-485b9bc494d477eb",
      "record": {"schema_version": 1, "kind": "gemm", "shape": {"m": 1, "k": 2048, "n": 8192}, "dtype": "fp32", "layout": "row_major"}},
    "contract": {"language": "c",
      "prototype": "void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c);",
      "operands": [
        {"name": "a", "role": "input", "dtype": "fp32", "shape": [1, 2048]},
        {"name": "b", "role": "input", "dtype": "fp32", "shape": [2048, 8192]},
        {"name": "c", "role": "output", "dtype": "fp32", "shape": [1, 8192]}]},
    "objective": {"objectives": [{"type": "latency_minimisation"}], "constraints": []}},
  "guidance": {"techniques": [{"id": "NOT-DECIDED-HERE", "text": "NOT-DECIDED-HERE"}]},
  "feedback": {"attempts": []}
}
"""
)
# The `task.objective` of the first case, copied from ADR-0050 (Example).
ADR_0050_OBJECTIVE = json.loads(
    '{"objectives": [{"type": "latency_minimisation"}], "constraints": []}'
)
# The memory-ceiling entry of ADR-0050 (Example, "Form only").
ADR_0050_CEILING = json.loads('{"type": "memory_ceiling", "bound": 123456789}')

BAD_NAMES = ["", "Upper", "1digit", "with-hyphen", "a" * 33, "name\n", 7, None]
BAD_STRINGS = ["", "s" * 256, "line\nbreak", "café", 7, None, True, ["s"]]
BAD_INTEGERS = [-1, 2**53, True, False, 1.0, "1", None, [1]]
BAD_POSITIVE_INTEGERS = [0, *BAD_INTEGERS]
NOT_OBJECTS = [None, "text", 1, 1.5, True, ["a"], [("a", 1)]]
NOT_ARRAYS = [None, "text", 1, True, {"a": 1}, ("a",)]
BAD_MEMBER_NAMES = ["", "Upper", "1digit", "with-hyphen", "a" * 33, 1, None]


class StrEnum(str, enum.Enum):
    SINGLE = "single"


class IntEnum(int, enum.Enum):
    ONE = 1
    TWO = 2


class StrSubclass(str):
    pass


BAD_TEXTS = ["", 7, None, True, ["text"], {"text": "t"}, b"text", StrSubclass("t")]


def synthetic_hw():
    return {
        "schema_version": 1,
        "accelerator": "synthetic_accel",
        "revision": "synthetic-rev-A",
        "toolchain": {"synthetic_cc": "0.0.1-synthetic"},
        "host": {"cpu": "synthetic cpu", "os": "synthetic os"},
        "hw_source": "in_house",
    }


def synthetic_op():
    return {
        "schema_version": 1,
        "kind": "gemm",
        "shape": {"m": 3, "k": 5, "n": 7},
        "dtype": "synthetic_dtype",
        "layout": "synthetic_layout",
    }


def operand(name="synthetic_a", role="input", shape=(3, 5)):
    return {
        "name": name,
        "role": role,
        "dtype": "synthetic_dtype",
        "shape": list(shape),
    }


def first_objective():
    return {"objectives": [{"type": "latency_minimisation"}], "constraints": []}


def minimal():
    hw, op = synthetic_hw(), synthetic_op()
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
            "op_signature": {"key": keys.op_signature_key(op).name, "record": op},
            "contract": {
                "language": "synthetic_lang",
                "prototype": "synthetic prototype text",
                "operands": [operand()],
            },
            "objective": first_objective(),
        },
        "guidance": {"techniques": []},
        "feedback": {"attempts": []},
    }


def attempt_entry(**members):
    return {"round": 1, "candidate": 1, "attempt": 1, "techniques": [], **members}


def failure_entry(attempt=1, stage="compile"):
    return {"attempt": attempt, "stage": stage, "report": "synthetic failure report"}


def changed(document, path, value):
    result = copy.deepcopy(document)
    target = result
    for part in path[:-1]:
        target = target[part]
    if value is REMOVE:
        del target[path[-1]]
    else:
        target[path[-1]] = value
    return result


def full():
    result = minimal()
    result["id"].update(round=4, candidate=2, candidates=3, relation="same_technique")
    result["id"]["variant"] = "synthetic variant: the second of three"
    result["task"]["contract"]["operands"] = [
        operand("synthetic_a", "input", (3, 5)),
        operand("synthetic_b", "input", (5, 7)),
        operand("synthetic_c", "output", (3, 7)),
        operand("synthetic_s", "inout", ()),
    ]
    result["task"]["build"] = {
        "synthetic_flag": "-synthetic",
        "synthetic_threads": 4,
        "synthetic_list": ["a", "b"],
        "synthetic_empty": [],
    }
    result["guidance"]["techniques"] = [
        {"id": "synthetic-technique-1", "text": "synthetic guidance one"},
        {"id": "synthetic-technique-2", "text": "synthetic guidance two"},
    ]
    report = "synthetic report"
    result["feedback"] = {
        "base": {"round": 3, "candidate": 1, "attempt": 2},
        "attempts": [
            attempt_entry(round=0, failure={"stage": "compile", "report": report}),
            attempt_entry(round=2, profile={"synthetic_metric": [1, 2.5, None]}),
            attempt_entry(
                round=3,
                attempt=2,
                techniques=["synthetic-technique-1", "synthetic-technique-2"],
                failure={"stage": "board", "report": report},
                profile={},
            ),
            attempt_entry(round=3, candidate=2),
            attempt_entry(failure={"stage": "sim", "report": report}),
        ],
    }
    result["ext"] = {"synthetic_ext": {"anything": [1.5, None, True]}, "other": None}
    return result


def repair(attempt=3, failures=None):
    result = minimal()
    result["id"]["attempt"] = attempt
    if failures is None:
        failures = [failure_entry(1, "compile"), failure_entry(2, "sim")]
    result["repair"] = {"failures": failures}
    return result


def rejects(document, match=None):
    with pytest.raises(InvalidSpecError, match=match) as info:
        validate(document)
    assert isinstance(info.value, ValueError)
    return str(info.value)


def test_schema_version_is_independent_of_the_key_schema():
    assert spec.SCHEMA_VERSION == 2
    assert spec.SCHEMA_VERSION != keys.SCHEMA_VERSION
    assert type(spec.SCHEMA_VERSION) is int


def test_invalid_spec_error_is_a_value_error():
    assert issubclass(InvalidSpecError, ValueError)


def test_minimal_first_call_spec_is_valid():
    assert validate(minimal()) is None


def test_full_spec_with_every_optional_member_is_valid():
    assert validate(full()) is None


def test_spec_parsed_from_json_text_is_valid():
    assert validate(json.loads(json.dumps(full()))) is None


def test_read_only_mappings_are_accepted():
    document = full()
    document["id"] = MappingProxyType(document["id"])
    document["ext"] = MappingProxyType(document["ext"])
    assert validate(MappingProxyType(document)) is None


def test_read_only_mappings_are_accepted_inside_the_objective():
    document = minimal()
    entry = MappingProxyType({"type": "latency_minimisation"})
    objective = MappingProxyType({"objectives": [entry], "constraints": []})
    document["task"]["objective"] = objective
    assert validate(document) is None
    assert document["task"]["objective"] is objective
    assert objective == {"objectives": [entry], "constraints": []}
    assert objective["objectives"][0] is entry
    assert entry == {"type": "latency_minimisation"}


@pytest.mark.parametrize("build", [minimal, full, repair])
def test_spec_is_not_modified(build):
    document = build()
    before = copy.deepcopy(document)
    validate(document)
    assert document == before


def test_same_technique_with_variant():
    document = minimal()
    document["id"].update(candidates=2, relation="same_technique", variant="synthetic")
    validate(document)


def test_different_techniques():
    document = minimal()
    document["id"].update(candidate=5, candidates=5, relation="different_techniques")
    validate(document)


def test_round_zero_is_valid():
    validate(changed(minimal(), ["id", "round"], 0))


@pytest.mark.parametrize("value", [1, 2**53 - 1])
def test_integer_bounds_are_valid(value):
    document = minimal()
    document["id"].update(candidates=value, relation="different_techniques")
    if value == 1:
        document["id"]["relation"] = "single"
    validate(changed(document, ["id", "round"], 2**53 - 1))


def test_repair_spec_is_valid():
    validate(repair())


def test_repair_spec_with_one_failure_is_valid():
    validate(repair(2, [failure_entry(1, "sim")]))


def test_repair_failures_need_not_report_every_earlier_attempt():
    validate(repair(5, [failure_entry(2), failure_entry(4)]))


def test_restated_example_of_adr_0050_is_a_valid_spec():
    assert validate(copy.deepcopy(ADR_0050_EXAMPLE)) is None


def test_objective_of_the_first_case_is_valid():
    assert ADR_0050_OBJECTIVE == first_objective()
    assert ADR_0050_EXAMPLE["task"]["objective"] == ADR_0050_OBJECTIVE
    validate(changed(minimal(), ["task", "objective"], ADR_0050_OBJECTIVE))


OBJECTIVE = "task.objective"
OBJECTIVES = "task.objective.objectives"
ENTRY = "task.objective.objectives[0]"
CONSTRAINTS = "task.objective.constraints"
ONE = {"type": "latency_minimisation"}


@pytest.mark.parametrize(
    ("objective", "message"),
    [
        (None, f"{OBJECTIVE}: must be an object, got None"),
        ("synthetic", f"{OBJECTIVE}: must be an object, got 'synthetic'"),
        ("latency_minimisation", f"{OBJECTIVE}: must be an object, got "),
        (1.5, f"{OBJECTIVE}: must be an object, got 1.5"),
        (0, f"{OBJECTIVE}: must be an object, got 0"),
        (True, f"{OBJECTIVE}: must be an object, got True"),
        ([], f"{OBJECTIVE}: must be an object, got []"),
        ([ONE], f"{OBJECTIVE}: must be an object, got "),
        ({}, f"{OBJECTIVES}: required member is missing"),
        ({"constraints": []}, f"{OBJECTIVES}: required member is missing"),
        ({"objectives": [ONE]}, f"{CONSTRAINTS}: required member is missing"),
        (
            {"objectives": [ONE], "constraints": [], "synthetic": 1},
            f"{OBJECTIVE}: unknown member 'synthetic'",
        ),
        (
            {"objectives": [ONE], "constraints": [], "direction": "lower"},
            f"{OBJECTIVE}: unknown member 'direction'",
        ),
        ({"synthetic": {"a": [1]}}, f"{OBJECTIVE}: unknown member 'synthetic'"),
        ({"synthetic_target": 1.5}, f"{OBJECTIVE}: unknown member 'synthetic_target'"),
    ],
)
def test_objective_that_is_not_the_object_of_two_members_is_rejected(
    objective, message
):
    document = changed(minimal(), ["task", "objective"], objective)
    assert rejects(document).startswith(message)


@pytest.mark.parametrize(
    "objectives",
    [
        None,
        "latency_minimisation",
        1,
        ONE,
        (ONE,),
        [],
        [ONE, ONE],
        [ONE, {"type": "throughput_maximisation"}],
        [ONE, None],
        [None, ONE],
        [ONE, ONE, ONE],
    ],
)
def test_objectives_that_is_not_an_array_of_exactly_one_entry_is_rejected(objectives):
    document = changed(minimal(), ["task", "objective", "objectives"], objectives)
    message = rejects(document)
    assert message.startswith(f"{OBJECTIVES}: must be an array of exactly one entry, ")


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        (None, f"{ENTRY}: must be an object, got None"),
        ("latency_minimisation", f"{ENTRY}: must be an object, got "),
        (["latency_minimisation"], f"{ENTRY}: must be an object, got "),
        (1, f"{ENTRY}: must be an object, got 1"),
        ({}, f"{ENTRY}.type: required member is missing"),
        ({"Type": "latency_minimisation"}, f"{ENTRY}: unknown member 'Type'"),
        ({**ONE, "weight": 1}, f"{ENTRY}: unknown member 'weight'"),
        ({**ONE, "weight": None}, f"{ENTRY}: unknown member 'weight'"),
        ({**ONE, "priority": 1}, f"{ENTRY}: unknown member 'priority'"),
        ({**ONE, "priority": 0}, f"{ENTRY}: unknown member 'priority'"),
        ({**ONE, "direction": "lower"}, f"{ENTRY}: unknown member 'direction'"),
        ({**ONE, "bound": 1}, f"{ENTRY}: unknown member 'bound'"),
        ({"weight": 1}, f"{ENTRY}: unknown member 'weight'"),
    ],
)
def test_objective_entry_that_is_not_the_object_of_type_alone_is_rejected(
    entry, message
):
    document = changed(minimal(), ["task", "objective", "objectives"], [entry])
    assert rejects(document).startswith(message)


@pytest.mark.parametrize(
    "value",
    [
        "throughput_maximisation",
        "memory_ceiling",
        "latency",
        "latency_minimization",
        "Latency_minimisation",
        "latency_minimisation ",
        "",
        StrSubclass("latency_minimisation"),
        StrEnum.SINGLE,
        b"latency_minimisation",
        ["latency_minimisation"],
        {"name": "latency_minimisation"},
        1,
        None,
        True,
    ],
)
def test_objective_type_other_than_latency_minimisation_is_rejected(value):
    document = changed(minimal(), ["task", "objective", "objectives", 0, "type"], value)
    message = rejects(document)
    assert message.startswith(f"{ENTRY}.type: must be latency_minimisation, got ")


@pytest.mark.parametrize(
    "value", [None, {}, ("a",), (), "", 0, False, ADR_0050_CEILING]
)
def test_constraints_that_is_not_an_array_is_rejected(value):
    document = changed(minimal(), ["task", "objective", "constraints"], value)
    assert rejects(document).startswith(f"{CONSTRAINTS}: must be an array, got ")


@pytest.mark.parametrize(
    "entries",
    [
        [ADR_0050_CEILING],
        [{"type": "memory_ceiling", "bound": 0}],
        [{"type": "memory_ceiling"}],
        [{"type": "latency_minimisation"}],
        [{}],
        [None],
        ["memory_ceiling"],
        [[]],
        [ADR_0050_CEILING, ADR_0050_CEILING],
    ],
)
def test_no_constraint_entry_is_admitted(entries):
    document = changed(minimal(), ["task", "objective", "constraints"], entries)
    message = rejects(document, "no constraint type is admitted")
    assert message.startswith(f"{CONSTRAINTS}[0]: must be absent: ")


def test_objective_is_checked_after_the_contract_and_before_build():
    document = changed(full(), ["task", "objective"], None)
    document["task"]["build"] = {}
    rejects(document, r"^task\.objective: ")
    document["task"]["contract"]["language"] = "Upper"
    rejects(document, r"^task\.contract\.language: ")


TEXT_PATHS = [
    ["task", "contract", "prototype"],
    ["id", "variant"],
    ["guidance", "techniques", 0, "text"],
    ["feedback", "attempts", 0, "failure", "report"],
    ["repair", "failures", 0, "report"],
]


def text_document(path):
    return repair() if path[0] == "repair" else full()


@pytest.mark.parametrize("path", TEXT_PATHS)
@pytest.mark.parametrize(
    "value", ["x", "synthétique ✓ 합성", "line\nbreak\ttab", "t" * 4000]
)
def test_text_has_no_character_or_length_restriction(path, value):
    validate(changed(text_document(path), path, value))


@pytest.mark.parametrize("path", TEXT_PATHS)
@pytest.mark.parametrize("value", BAD_TEXTS)
def test_bad_text_is_rejected(path, value):
    message = rejects(changed(text_document(path), path, value), "a text")
    assert message.startswith(path[0])


def test_operand_shape_and_build_array_may_be_empty():
    document = minimal()
    document["task"]["contract"]["operands"] = [operand(shape=())]
    document["task"]["build"] = {"synthetic_list": []}
    validate(document)


def test_adr_example_is_not_a_valid_spec():
    rejects(copy.deepcopy(ADR_EXAMPLE))


# "Exactly when" rules, both directions.


def test_repair_with_attempt_one_is_rejected():
    document = repair()
    document["id"]["attempt"] = 1
    assert rejects(document).startswith("repair: must be present exactly when")


@pytest.mark.parametrize("attempt", [2, 3])
def test_missing_repair_with_a_later_attempt_is_rejected(attempt):
    document = changed(minimal(), ["id", "attempt"], attempt)
    assert rejects(document).startswith("repair: must be present exactly when")


def test_single_with_two_candidates_is_rejected():
    rejects(changed(minimal(), ["id", "candidates"], 2), r"^id\.relation: ")


@pytest.mark.parametrize("relation", ["same_technique", "different_techniques"])
def test_other_relation_with_one_candidate_is_rejected(relation):
    document = changed(minimal(), ["id", "relation"], relation)
    document["id"]["variant"] = "synthetic"
    rejects(document, r"^id\.relation: ")


@pytest.mark.parametrize("relation", ["single", "different_techniques"])
def test_variant_without_same_technique_is_rejected(relation):
    document = minimal()
    candidates = 1 if relation == "single" else 2
    document["id"].update(relation=relation, candidates=candidates, variant="synthetic")
    rejects(document, r"^id\.variant: must be present exactly when")


def test_missing_variant_with_same_technique_is_rejected():
    document = minimal()
    document["id"].update(relation="same_technique", candidates=2)
    rejects(document, r"^id\.variant: must be present exactly when")


def test_candidate_equal_to_candidates_is_valid():
    document = minimal()
    document["id"].update(candidate=2, candidates=2, relation="different_techniques")
    validate(document)


def test_candidate_greater_than_candidates_is_rejected():
    document = minimal()
    document["id"].update(candidate=3, candidates=2, relation="different_techniques")
    rejects(document, r"^id\.candidate: must be at most id\.candidates \(2\), got 3$")


@pytest.mark.parametrize("value", [3, 5, 7])
def test_operand_shape_value_of_the_op_signature_shape_is_valid(value):
    document = minimal()
    document["task"]["contract"]["operands"] = [operand(shape=(value, value))]
    validate(document)


@pytest.mark.parametrize("value", [0, 1, 4, 15, 35])
def test_operand_shape_value_outside_the_op_signature_shape_is_rejected(value):
    document = minimal()
    document["task"]["contract"]["operands"] = [operand(), operand(shape=(3, value))]
    message = rejects(document, "a value of task.op_signature.record.shape")
    assert message.startswith("task.contract.operands[1].shape[1]: ")


@pytest.mark.parametrize("last", [1, 3, 4])
def test_repair_failures_whose_last_entry_is_not_attempt_minus_one(last):
    document = repair(3, [failure_entry(last)])
    rejects(document, r"^repair\.failures\[0\]\.attempt: must be id\.attempt - 1 \(2\)")


# Negative cases.


@pytest.mark.parametrize("value", [*NOT_OBJECTS, b"{}", object()])
def test_spec_that_is_not_a_mapping_is_rejected(value):
    assert rejects(value).startswith("spec: must be an object")


REQUIRED = {
    (): ["schema_version", "id", "hw_profile", "task", "guidance", "feedback"],
    ("id",): ["run_id", "round", "candidate", "attempt", "candidates", "relation"],
    ("hw_profile",): ["key", "record"],
    ("task",): ["op_signature", "contract", "objective"],
    ("task", "op_signature"): ["key", "record"],
    ("task", "contract"): ["language", "prototype", "operands"],
    ("task", "contract", "operands", 1): ["name", "role", "dtype", "shape"],
    ("task", "objective"): ["objectives", "constraints"],
    ("task", "objective", "objectives", 0): ["type"],
    ("guidance",): ["techniques"],
    ("guidance", "techniques", 1): ["id", "text"],
    ("feedback",): ["attempts"],
    ("feedback", "base"): ["round", "candidate", "attempt"],
    ("feedback", "attempts", 2): ["round", "candidate", "attempt", "techniques"],
    ("feedback", "attempts", 2, "failure"): ["stage", "report"],
    ("repair",): ["failures"],
    ("repair", "failures", 1): ["attempt", "stage", "report"],
}


def document_for(path):
    return repair() if path[:1] == ("repair",) else full()


def dotted(path):
    text = ""
    for part in path:
        text += f"[{part}]" if isinstance(part, int) else f".{part}"
    return text.lstrip(".")


@pytest.mark.parametrize(
    ("where", "member"),
    [(where, member) for where, members in REQUIRED.items() for member in members],
)
def test_missing_required_member_is_rejected(where, member):
    document = changed(document_for(where), [*where, member], REMOVE)
    message = rejects(document, "required member is missing")
    assert message.startswith(dotted([*where, member]) + ": ")


@pytest.mark.parametrize("where", list(REQUIRED))
@pytest.mark.parametrize("member", ["synthetic_unknown", "Variant", 1, None])
def test_unknown_member_is_rejected(where, member):
    document = changed(document_for(where), [*where, member], "synthetic")
    message = rejects(document, "unknown member")
    assert message.startswith((dotted(where) or "spec") + ": ")


def test_member_name_that_is_a_str_subclass_is_rejected():
    document = minimal()
    document[StrSubclass("ext")] = {"synthetic_ext": 1}
    rejects(document, "^spec: unknown member")
    document = changed(minimal(), ["id", "candidates"], 2)
    document["id"].update(relation="same_technique")
    document["id"][StrSubclass("variant")] = "synthetic"
    rejects(document, "^id: unknown member")


@pytest.mark.parametrize(
    "where",
    [
        ("id",),
        ("hw_profile",),
        ("task",),
        ("task", "op_signature"),
        ("task", "contract"),
        ("task", "contract", "operands", 0),
        ("task", "objective"),
        ("task", "objective", "objectives", 0),
        ("guidance",),
        ("guidance", "techniques", 0),
        ("feedback",),
        ("feedback", "base"),
        ("feedback", "attempts", 0),
        ("feedback", "attempts", 0, "failure"),
        ("feedback", "attempts", 1, "profile"),
        ("repair",),
        ("repair", "failures", 0),
    ],
)
@pytest.mark.parametrize("value", NOT_OBJECTS)
def test_value_that_is_not_an_object_is_rejected(where, value):
    document = changed(document_for(where), list(where), value)
    message = rejects(document, "must be an object")
    assert message.startswith(dotted(where) + ": ")


@pytest.mark.parametrize(
    "value", [1, 0, 3, True, "2", 2.0, None, IntEnum.TWO, IntEnum.ONE, [2], -2]
)
def test_schema_version_other_than_the_integer_two_is_rejected(value):
    document = changed(minimal(), ["schema_version"], value)
    rejects(document, "^schema_version: must be the integer 2, got ")


def test_version_one_document_is_refused_as_any_other_wrong_value():
    document = changed(minimal(), ["schema_version"], 1)
    document["task"]["objective"] = None
    rejects(document, "^schema_version: must be the integer 2, got 1$")


@pytest.mark.parametrize(
    "path",
    [
        ("id", "round"),
        ("feedback", "base", "round"),
        ("feedback", "attempts", 2, "round"),
    ],
)
@pytest.mark.parametrize("value", [*BAD_INTEGERS, IntEnum.ONE])
def test_bad_integer_is_rejected(path, value):
    document = changed(full(), list(path), value)
    message = rejects(document, r"an integer from 0 to 2\*\*53 - 1")
    assert message.startswith(dotted(path) + ": ")


@pytest.mark.parametrize(
    "path",
    [
        ("id", "candidate"),
        ("id", "attempt"),
        ("id", "candidates"),
        ("feedback", "base", "candidate"),
        ("feedback", "base", "attempt"),
        ("feedback", "attempts", 2, "candidate"),
        ("feedback", "attempts", 2, "attempt"),
        ("repair", "failures", 0, "attempt"),
    ],
)
@pytest.mark.parametrize("value", BAD_POSITIVE_INTEGERS)
def test_bad_positive_integer_is_rejected(path, value):
    document = changed(document_for(path), list(path), value)
    message = rejects(document, r"an integer from 1 to 2\*\*53 - 1")
    assert message.startswith(dotted(path) + ": ")


@pytest.mark.parametrize(
    "path",
    [
        ("id", "run_id"),
        ("hw_profile", "key"),
        ("task", "op_signature", "key"),
        ("task", "contract", "operands", 0, "name"),
        ("guidance", "techniques", 0, "id"),
        ("feedback", "attempts", 2, "techniques", 1),
        ("task", "build", "synthetic_list", 1),
    ],
)
@pytest.mark.parametrize("value", [*BAD_STRINGS, StrEnum.SINGLE])
def test_bad_string_is_rejected(path, value):
    document = changed(full(), list(path), value)
    message = rejects(document, "a string of 1 to 255 printable ASCII characters")
    assert message.startswith(dotted(path) + ": ")


@pytest.mark.parametrize("value", ["", "s" * 256, "café", "line\nbreak"])
def test_bad_string_as_a_build_value_is_rejected(value):
    document = changed(full(), ["task", "build", "synthetic_flag"], value)
    rejects(document, r"^task\.build\.synthetic_flag: must be a string of 1 to 255")


@pytest.mark.parametrize("value", ["s", "s" * 255, 'with space / " and \\'])
def test_string_bounds_are_valid(value):
    document = changed(full(), ["id", "run_id"], value)
    document["guidance"]["techniques"][0]["id"] = value
    document["task"]["contract"]["operands"][0]["name"] = value
    validate(document)


@pytest.mark.parametrize(
    "path",
    [
        ("task", "contract", "language"),
        ("task", "contract", "operands", 0, "dtype"),
    ],
)
@pytest.mark.parametrize("value", [*BAD_NAMES, StrEnum.SINGLE])
def test_value_that_is_not_a_name_is_rejected(path, value):
    document = changed(full(), list(path), value)
    message = rejects(document, "a name matching")
    assert message.startswith(dotted(path) + ": ")


@pytest.mark.parametrize(
    ("path", "rule"),
    [
        (("id", "relation"), "single or same_technique or different_techniques"),
        (("task", "contract", "operands", 0, "role"), "input or output or inout"),
        (("task", "objective", "objectives", 0, "type"), "latency_minimisation"),
        (("feedback", "attempts", 0, "failure", "stage"), "compile or sim or board"),
        (("repair", "failures", 0, "stage"), "compile or sim"),
    ],
)
@pytest.mark.parametrize(
    "value", ["synthetic_unknown", "Single", "", 1, None, True, ["sim"], StrEnum.SINGLE]
)
def test_value_outside_an_enumeration_is_rejected(path, rule, value):
    document = changed(document_for(path), list(path), value)
    message = rejects(document)
    assert message.startswith(f"{dotted(path)}: must be {rule}, got ")


def test_board_stage_is_rejected_in_repair_and_accepted_in_feedback():
    document = repair(2, [failure_entry(1, "board")])
    rejects(document, r"^repair\.failures\[0\]\.stage: must be compile or sim, got")
    assert full()["feedback"]["attempts"][2]["failure"]["stage"] == "board"


@pytest.mark.parametrize("where", [("hw_profile",), ("task", "op_signature")])
def test_key_that_differs_from_the_derived_name_is_rejected(where):
    document = minimal()
    section = document
    for part in where:
        section = section[part]
    derived = section["key"]
    section["key"] = derived[:-1] + ("0" if derived[-1] != "0" else "1")
    message = rejects(document, "the name derived from")
    assert message.startswith(dotted(where) + ".key: ")
    assert derived in message


def test_keys_of_the_two_records_are_not_interchangeable():
    document = minimal()
    document["hw_profile"]["key"] = document["task"]["op_signature"]["key"]
    rejects(document, r"^hw_profile\.key: ")


def test_key_follows_a_changed_record():
    document = minimal()
    document["task"]["op_signature"]["record"]["shape"]["m"] = 5
    rejects(document, r"^task\.op_signature\.key: ")


@pytest.mark.parametrize(
    ("where", "path", "value", "below"),
    [
        (("hw_profile",), ["hw_source"], "NOT-DECIDED-HERE", "hw_source"),
        (("hw_profile",), ["host", "cpu"], REMOVE, "host.cpu"),
        (("hw_profile",), ["toolchain"], {}, "toolchain"),
        (("hw_profile",), ["synthetic_unknown"], 1, "'synthetic_unknown'"),
        (("hw_profile",), ["schema_version"], 2, "schema_version"),
        (("task", "op_signature"), ["layout"], "NOT-DECIDED-HERE", "layout"),
        (("task", "op_signature"), ["kind"], "synthetic_kind", "kind"),
        (("task", "op_signature"), ["shape", "m"], REMOVE, "shape"),
        (("task", "op_signature"), ["shape", "k"], 1.5, "shape.k"),
        (("task", "op_signature"), ["dtype"], REMOVE, "dtype"),
    ],
)
def test_invalid_embedded_record_is_reported_with_its_path(where, path, value, below):
    document = changed(minimal(), [*where, "record", *path], value)
    with pytest.raises(InvalidSpecError) as info:
        validate(document)
    assert str(info.value).startswith(f"{dotted(where)}.record: {below}: ")
    assert isinstance(info.value.__cause__, keys.InvalidRecordError)


@pytest.mark.parametrize("where", [("hw_profile",), ("task", "op_signature")])
@pytest.mark.parametrize("value", [None, "text", ["a"], 1])
def test_embedded_record_that_is_not_a_map_is_rejected(where, value):
    document = changed(minimal(), [*where, "record"], value)
    message = rejects(document, "must be a map, got")
    assert message.startswith(dotted(where) + ".record: must be a map")


def test_empty_operands_is_rejected():
    document = changed(minimal(), ["task", "contract", "operands"], [])
    rejects(document, r"^task\.contract\.operands: must be an array of at least one")


@pytest.mark.parametrize(
    "path",
    [
        ("task", "contract", "operands"),
        ("task", "contract", "operands", 0, "shape"),
        ("task", "objective", "objectives"),
        ("task", "objective", "constraints"),
        ("guidance", "techniques"),
        ("feedback", "attempts"),
        ("feedback", "attempts", 0, "techniques"),
        ("repair", "failures"),
    ],
)
@pytest.mark.parametrize("value", NOT_ARRAYS)
def test_value_that_is_not_an_array_is_rejected(path, value):
    document = changed(document_for(path), list(path), value)
    message = rejects(document, "must be an array")
    assert message.startswith(dotted(path) + ": ")


@pytest.mark.parametrize("value", [*BAD_INTEGERS, IntEnum.ONE])
def test_bad_operand_shape_entry_is_rejected(value):
    document = changed(full(), ["task", "contract", "operands", 1, "shape", 0], value)
    rejects(document, r"^task\.contract\.operands\[1\]\.shape\[0\]: must be an integer")


@pytest.mark.parametrize(
    "value", [1.5, None, True, {"nested": "map"}, ("a",), [1], ["a", None], [["a"]]]
)
def test_bad_build_value_is_rejected(value):
    document = changed(full(), ["task", "build", "synthetic_flag"], value)
    rejects(document, r"^task\.build\.synthetic_flag")


@pytest.mark.parametrize("value", [-1, 2**53])
def test_build_integer_out_of_range_is_rejected(value):
    document = changed(full(), ["task", "build", "synthetic_threads"], value)
    rejects(document, r"^task\.build\.synthetic_threads: must be an integer from 0")


@pytest.mark.parametrize("section", [("task", "build"), ("ext",)])
@pytest.mark.parametrize("name", BAD_MEMBER_NAMES)
def test_open_map_member_name_that_is_not_a_name_is_rejected(section, name):
    document = changed(full(), [*section, name], "synthetic")
    rejects(document, "^" + dotted(section).replace(".", r"\.") + ": member name: ")


@pytest.mark.parametrize("section", [("task", "build"), ("ext",)])
@pytest.mark.parametrize("value", [{}, None, "text", 1, ["a"], [("a", 1)]])
def test_open_map_that_is_empty_or_not_a_map_is_rejected(section, value):
    document = changed(full(), list(section), value)
    message = rejects(document, "a map with at least one member")
    assert message.startswith(dotted(section) + ": ")


@pytest.mark.parametrize("value", [None, 1.5, True, [1], {"nested": {"a": None}}, "s"])
def test_ext_values_are_not_inspected(value):
    validate(changed(minimal(), ["ext"], {"synthetic_ext": value}))


def test_feedback_base_of_null_is_rejected():
    document = changed(minimal(), ["feedback", "base"], None)
    rejects(document, r"^feedback\.base: must be an object, got None$")


def test_feedback_base_alone_is_valid():
    base = {"round": 0, "candidate": 1, "attempt": 1}
    validate(changed(minimal(), ["feedback", "base"], base))


def test_refs_are_not_compared_with_the_spec_id_or_with_each_other():
    document = minimal()
    later = {"round": 9, "candidate": 9, "attempt": 9}
    document["feedback"] = {
        "base": later,
        "attempts": [attempt_entry(), attempt_entry(), attempt_entry(round=8)],
    }
    validate(document)


@pytest.mark.parametrize(
    "profile", [{}, {"synthetic": None}, {"Any Name": [1.5]}, {1: 2}]
)
def test_profile_members_are_not_inspected(profile):
    document = minimal()
    document["feedback"]["attempts"] = [attempt_entry(profile=profile)]
    validate(document)


def test_empty_repair_failures_is_rejected():
    rejects(repair(2, []), r"^repair\.failures: must be an array of at least one")


@pytest.mark.parametrize("attempts", [[2, 1], [1, 1, 2], [2, 2], [1, 3, 2], [3, 1, 2]])
def test_repair_failures_that_are_not_strictly_ascending_are_rejected(attempts):
    document = repair(3, [failure_entry(attempt) for attempt in attempts])
    rejects(document, r"^repair\.failures\[\d\]\.attempt: must be greater than")


def test_error_message_shows_a_bounded_form_of_the_value():
    deep = []
    for _ in range(10000):
        deep = [deep]
    message = rejects(changed(minimal(), ["id", "round"], deep), r"^id\.round: ")
    assert len(message) < 200
    message = rejects(changed(minimal(), ["id", "run_id"], "s" * 100000))
    assert len(message) < 200


def test_first_problem_is_reported_in_section_order():
    document = minimal()
    document["id"]["round"] = -1
    document["guidance"] = None
    rejects(document, r"^id\.round: ")
