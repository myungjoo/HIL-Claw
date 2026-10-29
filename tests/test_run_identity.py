import ast
import inspect
import io
import re
import tokenize
from pathlib import Path

import pytest

from hilclaw import (
    backends,
    check_identity,
    journal,
    journaled_tool,
    run_identity,
    tools,
)
from hilclaw.run_identity import NUMBERS, STEP_BOARD_RUN, STEP_SIM_RUN, STEPS, step_of

MARKER = "zq7-marker-zq7"
MESSAGE_LIMIT = 100
TOOLS = ("sim.run", "board.run")
FRAME = {"run_id": "r1", "round": 3, "candidate": 2, "attempt": 1, "execution": 1}
OTHER_STRINGS = [
    *(name for name in backends.HW_TOOLS if name not in TOOLS),
    "sim_run",
    "board_run",
    "SIM.RUN",
    "Sim.run",
    " sim.run",
    "sim.run ",
    "",
    "sim_run_timing",
    "board_run_timing",
    "sim_run_timing_v2",
    "board_run_timing_v2",
]


class Called(Exception):
    pass


class Hostile:
    def __eq__(self, other):
        raise Called("__eq__")

    def __hash__(self):
        raise Called("__hash__")

    def __str__(self):
        raise Called("__str__")

    def __repr__(self):
        raise Called("__repr__")


class Text(str):
    pass


class HostileText(str):
    def __eq__(self, other):
        raise Called("__eq__")

    def __hash__(self):
        raise Called("__hash__")

    def __str__(self):
        raise Called("__str__")

    def __repr__(self):
        raise Called("__repr__")


NO_STRINGS = [
    None,
    0,
    True,
    b"sim.run",
    ["sim.run"],
    Text("sim.run"),
    HostileText("sim.run"),
    Hostile(),
]


def refusal(error_type, tool):
    with pytest.raises(error_type) as caught:
        step_of(tool)
    error = caught.value
    assert type(error) is error_type
    assert len(error.args) == 1
    message = error.args[0]
    assert type(message) is str
    assert 0 < len(message) <= MESSAGE_LIMIT
    assert "sim.run" in message and "board.run" in message
    return message


def imported_modules(path):
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def code_strings(text):
    pieces = getattr(tokenize, "FSTRING_MIDDLE", tokenize.STRING)
    return [
        token.string
        for token in tokenize.generate_tokens(io.StringIO(text).readline)
        if token.type in (tokenize.NAME, tokenize.STRING, pieces)
        and not token.string.startswith('"""')
    ]


@pytest.mark.parametrize(
    ("step", "literal"),
    [(STEP_SIM_RUN, "sim_run_timing_v2"), (STEP_BOARD_RUN, "board_run_timing_v2")],
)
def test_a_step_value_is_a_name_of_its_own(step, literal):
    assert step == literal
    assert type(step) is str
    assert re.fullmatch(r"[a-z][a-z0-9_]{0,31}", step)
    assert "." not in step
    assert step not in tools.RESERVED_KINDS
    assert journal.step_identity(step, 1, 0, 1, 1).step == step
    assert step not in ("sim.run", "board.run", "sim_run", "board_run")
    assert step not in check_identity.STEPS


def test_the_step_values_and_the_numbers_are_tuples():
    assert type(STEPS) is tuple
    assert STEPS == (STEP_SIM_RUN, STEP_BOARD_RUN)
    assert len(set(STEPS)) == 2
    assert type(NUMBERS) is tuple
    assert NUMBERS == ("round", "candidate", "attempt")


def test_the_step_follows_from_the_tool():
    assert step_of("sim.run") == STEP_SIM_RUN
    assert step_of("board.run") == STEP_BOARD_RUN
    assert all(tool in backends.HW_TOOLS for tool in TOOLS)
    assert {step_of(tool) for tool in TOOLS} == set(STEPS)


def checked(step, asked):
    def carry_out(data_root, run_id, identity, request):
        raise AssertionError("carry_out was called")

    def source():
        asked.append(1)
        raise Called("the source was asked")

    return journaled_tool.checked_function(
        step=step,
        numbers=NUMBERS,
        carry_out=carry_out,
        source=source,
        check=lambda request: None,
    )


@pytest.mark.parametrize("step", STEPS)
@pytest.mark.parametrize(
    "request_",
    [
        {name: value for name, value in FRAME.items() if name != "attempt"},
        {name: value for name, value in FRAME.items() if name != "execution"},
        FRAME | {"execution": 0},
        {name: value for name, value in FRAME.items() if name != "round"},
        {name: value for name, value in FRAME.items() if name != "candidate"},
    ],
    ids=["no-attempt", "no-execution", "execution-0", "no-round", "no-candidate"],
)
def test_the_frame_refuses_before_the_source(step, request_):
    asked = []
    function = checked(step, asked)
    with pytest.raises(tools.ToolFailure) as caught:
        function(request_)
    assert caught.value.kind == tools.KIND_INVALID_REQUEST
    assert asked == []


@pytest.mark.parametrize("step", STEPS)
def test_round_zero_passes_the_frame(step):
    asked = []
    function = checked(step, asked)
    with pytest.raises(tools.ToolFailure) as caught:
        function(FRAME | {"round": 0})
    assert caught.value.kind == tools.KIND_NO_DATA_ROOT
    assert asked == [1]


def test_the_steps_are_taken_as_steps():
    def fail(*args):
        raise AssertionError("called")

    function = journaled_tool.stepped_function(
        steps=STEPS,
        step_of=fail,
        numbers=NUMBERS,
        carry_out=fail,
        source=fail,
        check=fail,
    )
    assert callable(function)


@pytest.mark.parametrize("tool", OTHER_STRINGS, ids=repr)
def test_another_string_is_a_value_error(tool):
    refusal(ValueError, tool)


@pytest.mark.parametrize("tool", NO_STRINGS, ids=lambda value: type(value).__name__)
def test_a_value_that_is_no_exact_str_is_a_type_error(tool):
    refusal(TypeError, tool)


def test_the_message_does_not_show_the_value():
    long = MARKER * 5000
    assert MARKER not in refusal(ValueError, long)
    assert MARKER not in refusal(ValueError, MARKER)
    assert MARKER not in refusal(TypeError, [long])
    assert MARKER not in refusal(TypeError, Text(long))


def test_a_missing_or_surplus_argument_is_a_type_error():
    with pytest.raises(TypeError):
        step_of()
    with pytest.raises(TypeError):
        step_of("sim.run", "board.run")


def test_step_of_returns_a_step_value_or_refuses():
    returned = []
    for tool in [*OTHER_STRINGS, *NO_STRINGS, *TOOLS]:
        try:
            returned.append(step_of(tool))
        except (TypeError, ValueError) as error:
            assert type(error) in (TypeError, ValueError)
    assert returned == [STEP_SIM_RUN, STEP_BOARD_RUN]
    assert set(returned) <= set(STEPS)


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for tool in TOOLS:
        assert step_of(tool) in STEPS
    refusal(ValueError, "profiler.collect")
    refusal(TypeError, None)
    assert list(tmp_path.iterdir()) == []


def test_module_imports_nothing_and_has_no_entry():
    own = Path(run_identity.__file__)
    assert imported_modules(own) == set()
    assert not hasattr(run_identity, "main")
    assert "__main__" not in own.read_text(encoding="utf-8")


def test_the_text_and_the_code_hold_none_of_the_kept_out_strings():
    text = Path(run_identity.__file__).read_text(encoding="utf-8")
    assert "gemm_contract" not in text
    assert "standin_profile" not in text
    code = code_strings(text)
    assert [string for string in code if "got another string" in string]
    for kept_out in (
        "point",
        "correctness_check",
        "profiler",
        "invalid_request",
        "step_open",
        "objective",
        "bound",
        "seed",
        "run_id",
        "execution",
    ):
        assert not [string for string in code if kept_out in string], kept_out
    for spelt_once in ("sim_run_timing_v2", "board_run_timing_v2"):
        spelt = [string for string in code if spelt_once in string]
        assert spelt == [f'"{spelt_once}"']
    for retired in ('"sim_run_timing"', '"board_run_timing"'):
        assert retired not in code


def test_public_names_of_the_module_and_no_default():
    public = {
        name
        for name, value in vars(run_identity).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {"STEP_SIM_RUN", "STEP_BOARD_RUN", "STEPS", "NUMBERS", "step_of"}
    parameters = list(inspect.signature(step_of).parameters.values())
    assert [parameter.name for parameter in parameters] == ["tool"]
    assert parameters[0].default is inspect.Parameter.empty
    assert parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
