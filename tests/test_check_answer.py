import ast
import copy
import inspect
import json
import struct
from pathlib import Path

import numpy as np
import pytest

from hilclaw import check_answer, check_judging, check_result, tools
from hilclaw.check_answer import NeitherFormError, from_answer
from hilclaw.harness.verification import END_MARK, Broken
from hilclaw.harness.verification_arrays import (
    VerificationArgumentError,
    check_value,
    draw_inputs,
    reference,
)
from hilclaw.journaled_step import StepFailed

# The record's example values (ADR-0042 decision 7); its draws are a placeholder.
EXAMPLE_DRAWS = 2
EXAMPLE = {
    "m": 1,
    "k": 2048,
    "n": 8192,
    "draws": EXAMPLE_DRAWS,
    "rtol": 1e-4,
    "atol": 0.01,
}
ADR_BROKEN = {
    "outcome": "broken",
    "condition": "time_limit",
    "shape": {"m": 1, "k": 2048, "n": 8192},
    "draws": 2,
    "tolerance": {"rtol": 1e-4, "atol": 0.01},
}
COMPLETED_MEMBERS = {"outcome", "shape", "draws", "tolerance", "counts"}
BROKEN_MEMBERS = {"outcome", "condition", "shape", "draws", "tolerance"}

# Test values, not tolerances, dimensions, draws or a seed of the package.
SHAPE = (3, 4, 5)
DRAWS = 3
SEED = 7
SMALL = {"m": 3, "k": 4, "n": 5, "draws": DRAWS, "rtol": 1e-5, "atol": 1e-6}
CALL = {**SMALL, "seed": SEED}
SMALL_SHAPE = {"m": 3, "k": 4, "n": 5}
SMALL_TOLERANCE = {"rtol": 1e-5, "atol": 1e-6}

BAD_INTEGERS = [(0, ValueError), (True, TypeError), (1.0, TypeError)]
BAD_NUMBERS = [(-0.1, ValueError), (float("nan"), ValueError), ("0", TypeError)]
BAD_BESIDE_A_CONDITION = [
    (name, value, expected)
    for name in ("m", "k", "n", "draws")
    for value, expected in BAD_INTEGERS
] + [
    (name, value, expected)
    for name in ("rtol", "atol")
    for value, expected in BAD_NUMBERS
]
BAD_BESIDE_A_REPORT = [
    ("m", 0),
    ("k", True),
    ("n", 1.0),
    ("draws", 0),
    ("draws", 2**64),
    ("seed", -1),
    ("seed", 2**64),
    ("seed", None),
    ("rtol", -0.1),
    ("atol", float("nan")),
]


class Text(str):
    pass


class Octets(bytes):
    pass


def rounded_references(m, k, n, draws, seed):
    outputs = []
    for draw in range(draws):
        a, b = draw_inputs(m, k, n, seed=seed, draw=draw)
        outputs.append(reference(a, b).astype(np.float32))
    return outputs


def report_of(m, k, n, seed, outputs, wrong_check=()):
    parts = []
    for draw, output in enumerate(outputs):
        value = check_value(*draw_inputs(m, k, n, seed=seed, draw=draw))
        if draw in wrong_check:
            value ^= 1
        parts.append(struct.pack("=I", value))
        parts.append(np.ascontiguousarray(output, dtype=np.float32).tobytes())
    return b"".join(parts) + END_MARK


def passing_report(m, k, n, draws, seed):
    return report_of(m, k, n, seed, rounded_references(m, k, n, draws, seed))


def failing_report():
    outputs = rounded_references(*SHAPE, DRAWS, SEED)
    outputs[1][2, 4] += np.float32(0.25)
    return report_of(*SHAPE, SEED, outputs)


GOOD = passing_report(*SHAPE, DRAWS, SEED)

NEITHER_FORM = [
    "report_form",
    "check_value",
    "pass",
    "fail",
    "broken",
    "",
    "TIME_LIMIT",
    "time_limit ",
    " time_limit",
    "timeout",
    None,
    0,
    1,
    True,
    1.5,
    ("time_limit",),
    ["exit_status"],
    (b"", "exit_status"),
    check_result.broken("time_limit", **SMALL),
    Broken.TIMEOUT,
    bytearray(GOOD),
    memoryview(GOOD),
    Text("time_limit"),
    Octets(GOOD),
]


def assert_sound(result, members):
    assert type(result) is dict
    assert set(result) == members
    tools.check_json_object(result)
    assert json.loads(tools.encode(result)) == result


def neither_form(answer, **arguments):
    with pytest.raises(NeitherFormError) as caught:
        from_answer(answer, **arguments)
    assert type(caught.value) is NeitherFormError
    return caught.value


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


def test_a_report_of_rounded_references_passes():
    result = from_answer(GOOD, **CALL)
    assert result == {
        "outcome": "pass",
        "shape": SMALL_SHAPE,
        "draws": DRAWS,
        "tolerance": SMALL_TOLERANCE,
        "counts": [{"failed": 0, "non_finite": 0}] * DRAWS,
    }
    assert result == check_judging.from_report(GOOD, **CALL)
    assert_sound(result, COMPLETED_MEMBERS)


def test_a_report_with_one_element_off_fails_with_the_count_of_its_draw():
    report = failing_report()
    result = from_answer(report, **CALL)
    assert result["outcome"] == "fail"
    assert result["counts"] == [
        {"failed": 0, "non_finite": 0},
        {"failed": 1, "non_finite": 0},
        {"failed": 0, "non_finite": 0},
    ]
    assert result == check_judging.from_report(report, **CALL)
    assert_sound(result, COMPLETED_MEMBERS)


def test_the_smallest_check_is_judged():
    one = {"m": 1, "k": 1, "n": 1, "draws": 1, "seed": SEED}
    report = passing_report(**one)
    result = from_answer(report, **one, rtol=1e-5, atol=1e-6)
    assert result["outcome"] == "pass"
    assert result["shape"] == {"m": 1, "k": 1, "n": 1}
    assert result["counts"] == [{"failed": 0, "non_finite": 0}]
    assert_sound(result, COMPLETED_MEMBERS)


@pytest.mark.parametrize("condition", ["time_limit", "exit_status"])
def test_one_of_the_two_strings_gives_the_broken_result(condition):
    result = from_answer(condition, **CALL)
    assert result == {
        "outcome": "broken",
        "condition": condition,
        "shape": SMALL_SHAPE,
        "draws": DRAWS,
        "tolerance": SMALL_TOLERANCE,
    }
    assert result == check_result.broken(condition, **SMALL)
    assert_sound(result, BROKEN_MEMBERS)
    assert "counts" not in result
    assert "seed" not in result


def test_the_two_strings_are_the_first_two_conditions_of_the_builder():
    assert check_result.CONDITIONS[:2] == ("time_limit", "exit_status")


def test_time_limit_gives_the_third_example_of_the_record():
    result = from_answer("time_limit", **EXAMPLE, seed=SEED)
    assert result == ADR_BROKEN
    assert list(result) == list(ADR_BROKEN)
    assert_sound(result, BROKEN_MEMBERS)


@pytest.mark.parametrize(
    "report",
    [
        b"",
        GOOD[:-1],
        GOOD + b"\x00",
        GOOD[: -len(END_MARK)],
        GOOD[: -len(END_MARK)] + b"END\n",
        b"time_limit",
        b"exit_status",
    ],
)
def test_a_byte_string_of_any_content_is_a_report(report):
    result = from_answer(report, **CALL)
    assert result == check_result.broken("report_form", **SMALL)
    assert result == check_judging.from_report(report, **CALL)
    assert_sound(result, BROKEN_MEMBERS)


def test_a_report_with_a_wrong_check_value_is_broken_by_it():
    outputs = rounded_references(*SHAPE, DRAWS, SEED)
    report = report_of(*SHAPE, SEED, outputs, wrong_check={1})
    result = from_answer(report, **CALL)
    assert result == check_result.broken("check_value", **SMALL)
    assert_sound(result, BROKEN_MEMBERS)


@pytest.mark.parametrize("seed", [-1, 2**64, None, "7", True])
def test_the_seed_is_not_checked_beside_a_condition(seed):
    result = from_answer("exit_status", **SMALL, seed=seed)
    assert result == check_result.broken("exit_status", **SMALL)


@pytest.mark.parametrize(
    "answer", NEITHER_FORM, ids=lambda answer: type(answer).__name__
)
def test_an_answer_of_neither_form_makes_no_result(answer):
    error = neither_form(answer, **CALL)
    assert not isinstance(error, (tools.ToolFailure, StepFailed))
    assert not hasattr(error, "kind")
    assert not hasattr(error, "spend")
    assert type(answer).__name__ in str(error)


def test_the_message_names_the_type_and_shows_a_str():
    expected = "answer: must be bytes or one of ('time_limit', 'exit_status'), got "
    assert str(neither_form(None, **CALL)) == expected + "NoneType"
    assert str(neither_form("pass", **CALL)) == expected + "the str 'pass'"
    assert str(neither_form(Text("time_limit"), **CALL)) == expected + "Text"
    assert str(neither_form(Broken.TIMEOUT, **CALL)) == expected + "Broken"


def test_the_message_stays_short_and_holds_no_byte_of_a_report():
    expected = "answer: must be bytes or one of ('time_limit', 'exit_status'), got "
    long = str(neither_form("x" * 10_000, **CALL))
    assert long.startswith(expected + "the str 'xxx")
    assert len(long) < len(expected) + 50
    for answer in (bytearray(GOOD), memoryview(GOOD), Octets(GOOD)):
        error = neither_form(answer, **CALL)
        assert str(error) == expected + type(answer).__name__
        assert error.args == (str(error),)
        assert vars(error) == {}


@pytest.mark.parametrize(
    ("name", "value"),
    [("m", 0), ("rtol", float("nan")), ("seed", -1), ("draws", None)],
)
@pytest.mark.parametrize("answer", ["report_form", None, bytearray(GOOD)])
def test_the_form_comes_before_the_other_arguments(answer, name, value):
    neither_form(answer, **{**CALL, name: value})


def test_the_form_comes_first_when_every_other_argument_is_bad():
    bad = dict.fromkeys(("m", "k", "n", "draws", "seed", "rtol", "atol"))
    neither_form("pass", **bad)


@pytest.mark.parametrize(("name", "value"), BAD_BESIDE_A_REPORT)
def test_a_bad_argument_beside_a_report_raises_what_the_judging_raises(name, value):
    arguments = {**CALL, name: value}
    with pytest.raises(VerificationArgumentError) as caught:
        from_answer(GOOD, **arguments)
    assert type(caught.value) is VerificationArgumentError
    with pytest.raises(VerificationArgumentError) as direct:
        check_judging.from_report(GOOD, **arguments)
    assert str(caught.value) == str(direct.value)


@pytest.mark.parametrize(("name", "value", "expected"), BAD_BESIDE_A_CONDITION)
@pytest.mark.parametrize("condition", ["time_limit", "exit_status"])
def test_a_bad_argument_beside_a_condition_raises_what_the_builder_raises(
    condition, name, value, expected
):
    with pytest.raises(expected) as caught:
        from_answer(condition, **{**CALL, name: value})
    assert type(caught.value) is expected
    assert str(caught.value).startswith(f"{name}: ")


@pytest.mark.parametrize("answer", [GOOD, "time_limit", None])
def test_the_call_itself_is_checked_by_python(answer):
    for name in CALL:
        missing = {key: value for key, value in CALL.items() if key != name}
        with pytest.raises(TypeError) as caught:
            from_answer(answer, **missing)
        assert type(caught.value) is TypeError
    with pytest.raises(TypeError) as caught:
        from_answer(answer, **CALL, counts=())
    assert type(caught.value) is TypeError
    with pytest.raises(TypeError) as caught:
        from_answer(answer, 3, **CALL)
    assert type(caught.value) is TypeError
    with pytest.raises(TypeError) as caught:
        from_answer(**CALL)
    assert type(caught.value) is TypeError


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from_answer(GOOD, **CALL)
    from_answer(GOOD[:-1], **CALL)
    from_answer("time_limit", **CALL)
    neither_form("report_form", **CALL)
    neither_form(None, **CALL)
    with pytest.raises(ValueError):
        from_answer("exit_status", **{**CALL, "m": 0})
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("answer", [GOOD, failing_report(), b"", "exit_status"])
def test_equal_arguments_give_equal_and_distinct_results(answer):
    arguments = copy.deepcopy(CALL)
    first = from_answer(answer, **arguments)
    second = from_answer(answer, **arguments)
    assert first == second
    assert first is not second
    kept = copy.deepcopy(second)
    first["shape"]["m"] = 99
    first["tolerance"]["rtol"] = 99.0
    first["outcome"] = "changed"
    first.pop("condition", None)
    for entry in first.get("counts", []):
        entry["failed"] = 99
    assert second == kept
    assert arguments == CALL
    assert check_result.CONDITIONS == (
        "time_limit",
        "exit_status",
        "report_form",
        "check_value",
    )
    assert from_answer(answer, **arguments) == kept


def test_an_answer_is_not_modified():
    report = bytes(GOOD)
    from_answer(report, **CALL)
    assert report == GOOD
    answer = bytearray(GOOD)
    neither_form(answer, **CALL)
    assert answer == GOOD


def test_module_imports_the_judging_and_the_builder_only_and_has_no_entry():
    own = Path(check_answer.__file__)
    imported = imported_modules(own)
    assert imported == {
        "reprlib",
        "hilclaw",
        "hilclaw.check_judging",
        "hilclaw.check_result",
    }
    assert not imported & {
        "secrets",
        "random",
        "os",
        "time",
        "hilclaw.tools",
        "hilclaw.journaled_step",
    }
    assert not hasattr(check_answer, "main")
    assert "__main__" not in own.read_text(encoding="utf-8")


def test_public_names_of_the_module_and_no_default():
    public = {
        name
        for name, value in vars(check_answer).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {"from_answer", "NeitherFormError"}
    parameters = list(inspect.signature(from_answer).parameters.values())
    assert [parameter.name for parameter in parameters] == [
        "answer",
        "m",
        "k",
        "n",
        "draws",
        "seed",
        "rtol",
        "atol",
    ]
    for parameter in parameters:
        assert parameter.default is inspect.Parameter.empty, parameter
    assert parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    keyword_only = inspect.Parameter.KEYWORD_ONLY
    assert all(parameter.kind is keyword_only for parameter in parameters[1:])


def test_the_exception_is_the_modules_own_and_no_tool_failure():
    assert NeitherFormError.__bases__ == (Exception,)
    assert not issubclass(NeitherFormError, (tools.ToolFailure, StepFailed))
    assert not issubclass(NeitherFormError, (TypeError, ValueError))
    assert NeitherFormError.__module__ == "hilclaw.check_answer"
    assert not hasattr(NeitherFormError, "kind")
    assert not hasattr(NeitherFormError, "spend")
