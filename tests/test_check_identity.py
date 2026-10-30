import ast
import copy
import inspect
import io
import re
import tokenize
from pathlib import Path

import pytest

from hilclaw import check_identity, journal, journaled_tool, tools
from hilclaw.check_identity import (
    BOARD,
    MEMBER,
    MEMBERS,
    NUMBERS,
    SIM,
    STEP_BOARD,
    STEP_SIM,
    STEPS,
    check,
    step_of,
)

MARKER = "zq7-marker-zq7"
MESSAGE_LIMIT = 100
UNNAMED_LIMIT = 160
NOT_SHOWN = "(a name not shown)"
FRAME = {"run_id": "r1", "round": 3, "candidate": 2, "attempt": 1, "execution": 1}
ANOTHER_VALUE = [
    "Sim",
    "SIM",
    "BOARD",
    "Board",
    " sim",
    "sim ",
    "sim\n",
    "",
    "sim.run",
    "board.run",
    "correctness_check_sim",
    "compile",
    True,
    False,
    0,
    1,
    1.0,
    None,
    ["sim"],
    {"sim": 1},
    b"sim",
]
NO_OBJECT = [None, [], [("point", "sim")], "sim", '{"point": "sim"}', 0, 1]
UNNAMED = [
    "draws",
    "seed",
    "tolerance",
    "m",
    "k",
    "n",
    "shape",
    "op_signature",
    "step",
    "hw_profile",
    "data_root",
    "Point",
    "POINT",
    "run-id",
    "Execution",
    "flags",
    "time_limit",
    "a" * 32,
]
NOT_SHOWABLE = [
    "",
    "point ",
    " point",
    "dra\nws",
    "draws\n",
    "\x00",
    "seed\x00",
    "\x1b[31m",
    "a b",
    "draws'",
    'draws"',
    "p\u00f6int",
    "\u202epoint",
    "a" * 33,
    MARKER * 5000,
]
UNNAMED_VALUES = [None, 0, 1000, 1.5, True, "sim", MARKER, [MARKER], {MARKER: MARKER}]


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


class HostileKey:
    def __eq__(self, other):
        raise Called("__eq__")

    def __hash__(self):
        return hash("point")

    def __repr__(self):
        raise Called("__repr__")


class HostileTextKey(str):
    def __eq__(self, other):
        raise Called("__eq__")

    def __hash__(self):
        return hash("point")


class Mapping(dict):
    pass


def refusal(function, request, start="point", limit=MESSAGE_LIMIT):
    with pytest.raises(tools.ToolFailure) as caught:
        function(request)
    error = caught.value
    assert type(error) is tools.ToolFailure
    assert error.kind == tools.KIND_INVALID_REQUEST == "invalid_request"
    assert type(error.message) is str
    assert error.message.startswith(start)
    assert 0 < len(error.message) <= limit
    return error.message


def refused_alike(request):
    message = refusal(check, request)
    assert refusal(step_of, request) == message
    return message


def unnamed_alike(request, start=NOT_SHOWN):
    message = refusal(check, request, start + ": ", UNNAMED_LIMIT)
    assert refusal(step_of, request, start + ": ", UNNAMED_LIMIT) == message
    assert message.isascii() and message.isprintable()
    assert MARKER not in message
    for member in MEMBERS:
        assert member in message
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


def test_the_member_and_its_two_values():
    assert MEMBER == "point"
    assert SIM == "sim"
    assert BOARD == "board"
    assert all(type(value) is str for value in (MEMBER, SIM, BOARD))
    assert MEMBER not in ("run_id", "round", "candidate", "attempt", "execution")


@pytest.mark.parametrize(
    ("step", "literal", "point"),
    [
        (STEP_SIM, "correctness_check_sim_v2", SIM),
        (STEP_BOARD, "correctness_check_board_v2", BOARD),
    ],
)
def test_a_step_value_is_a_name_formed_from_its_point(step, literal, point):
    assert step == literal
    assert type(step) is str
    assert re.fullmatch(r"[a-z][a-z0-9_]{0,31}", step)
    assert "." not in step
    assert step not in tools.RESERVED_KINDS
    assert step == "correctness_check_" + point + "_v2"
    assert journal.step_identity(step, 1, 0, 1, 1).step == step


def test_the_step_values_the_numbers_and_the_members_are_tuples():
    assert type(STEPS) is tuple
    assert STEPS == (STEP_SIM, STEP_BOARD)
    assert STEP_SIM != STEP_BOARD
    assert type(NUMBERS) is tuple
    assert NUMBERS == ("round", "candidate", "attempt")
    assert type(MEMBERS) is tuple
    assert MEMBERS == ("run_id", "round", "candidate", "attempt", "execution", "point")
    assert all(type(member) is str for member in MEMBERS)
    assert len(set(MEMBERS)) == len(MEMBERS)
    assert set(MEMBERS) == set(FRAME) | {MEMBER}


@pytest.mark.parametrize(("point", "step"), [("sim", STEP_SIM), ("board", STEP_BOARD)])
def test_a_request_with_a_valid_point(point, step):
    request = FRAME | {"point": point}
    before = copy.deepcopy(request)
    assert check(request) is None
    assert step_of(request) == step
    assert step_of(request) in STEPS
    assert request == before


@pytest.mark.parametrize(("point", "step"), [("sim", STEP_SIM), ("board", STEP_BOARD)])
def test_no_value_of_another_named_member_is_looked_at(point, step):
    alone = {"point": point}
    hostile = {"point": point, "run_id": Hostile(), "execution": HostileText("1")}
    for request in (alone, hostile):
        assert check(request) is None
        assert step_of(request) == step
    assert alone == {"point": point}


@pytest.mark.parametrize("value", UNNAMED_VALUES, ids=repr)
@pytest.mark.parametrize("name", UNNAMED)
def test_a_member_no_record_names_is_refused_whatever_its_value(name, value):
    for point in (SIM, BOARD):
        request = FRAME | {"point": point, name: value}
        before = copy.deepcopy(request)
        unnamed_alike(request, name)
        assert request == before


@pytest.mark.parametrize("name", NOT_SHOWABLE, ids=lambda name: repr(name)[:40])
def test_a_name_that_is_not_shown_is_replaced_by_the_fixed_text(name):
    message = unnamed_alike(FRAME | {"point": SIM, name: None})
    assert "\n" not in message and "\x00" not in message


def test_the_message_names_a_short_name_as_it_is_and_is_bounded():
    message = unnamed_alike({"point": SIM, "a" * 32: 1}, "a" * 32)
    assert len(message) <= UNNAMED_LIMIT
    assert unnamed_alike({"point": SIM, "a" * 33: 1}).startswith(NOT_SHOWN)


@pytest.mark.parametrize(
    "hostile",
    [Hostile(), HostileText("x"), HostileText("sim")],
    ids=["any", "str", "sim"],
)
def test_no_code_of_a_hostile_value_of_an_unnamed_member_is_called(hostile):
    unnamed_alike(FRAME | {"point": SIM, "draws": hostile}, "draws")
    unnamed_alike({"Point": hostile}, "Point")


@pytest.mark.parametrize(
    "key",
    [
        HostileKey,
        lambda: HostileTextKey("point"),
        lambda: HostileTextKey("draws"),
        lambda: Text("point"),
        lambda: Text("draws"),
        lambda: 1,
        lambda: None,
        lambda: b"point",
        lambda: ("point",),
    ],
    ids=[
        "any",
        "hostile-point",
        "hostile-draws",
        "point",
        "draws",
        "int",
        "none",
        "bytes",
        "tuple",
    ],
)
def test_a_key_that_is_not_exactly_a_str_is_a_member_no_record_names(key):
    unnamed_alike({key(): "sim"})
    unnamed_alike(FRAME | {key(): None})


def test_the_first_fault_in_the_stated_order_is_named():
    assert unnamed_alike(FRAME | {"Point": "sim"}, "Point")
    assert unnamed_alike(FRAME | {"point": "Sim", "draws": 1}, "draws")
    assert unnamed_alike(FRAME | {"point": None, "seed": 7}, "seed")
    assert unnamed_alike({"draws": 1, "point": "sim", "seed": 7}, "draws")
    assert unnamed_alike({"seed": 7, "point": "sim", "draws": 1}, "seed")
    assert unnamed_alike({HostileKey(): 1, "draws": 1}, NOT_SHOWN)
    refused_alike(Mapping(draws=1))


def test_requests_that_differ_in_anything_else_have_the_same_step():
    first = FRAME | {"point": "sim"}
    for member, value in [
        ("execution", 2),
        ("round", 0),
        ("candidate", 7),
        ("attempt", 2),
        ("run_id", "r2"),
    ]:
        assert step_of(first | {member: value}) == step_of(first) == STEP_SIM
    assert step_of(first | {"point": "board"}) == STEP_BOARD


@pytest.mark.parametrize("step", STEPS)
def test_the_frame_takes_the_check_and_refuses_before_the_source(step):
    asked = []

    def carry_out(data_root, run_id, identity, request):
        raise AssertionError("carry_out was called")

    def source():
        asked.append(1)
        raise AssertionError("the source was asked")

    function = journaled_tool.checked_function(
        step=step, numbers=NUMBERS, carry_out=carry_out, source=source, check=check
    )
    refusal(function, dict(FRAME))
    refusal(function, FRAME | {"point": "Sim"})
    refusal(function, FRAME | {"point": "sim", "draws": 1000}, "draws: ", UNNAMED_LIMIT)
    refusal(function, FRAME | {"Point": "sim"}, "Point: ", UNNAMED_LIMIT)
    assert asked == []


@pytest.mark.parametrize("request_", [{}, dict(FRAME), {"run_id": "r1"}])
def test_a_request_without_the_member_is_refused(request_):
    before = copy.deepcopy(request_)
    refused_alike(request_)
    assert request_ == before


@pytest.mark.parametrize("value", ANOTHER_VALUE, ids=repr)
def test_another_value_is_refused(value):
    request = FRAME | {"point": value}
    before = copy.deepcopy(request)
    refused_alike(request)
    assert request == before


def test_the_message_does_not_show_the_value():
    long = MARKER * 5000
    for value in (long, [long], {long: long}, MARKER):
        assert MARKER not in refused_alike({"point": value})


def test_a_subclass_of_str_is_another_value():
    refused_alike({"point": Text("sim")})
    refused_alike({"point": Text("board")})


@pytest.mark.parametrize("hostile", [HostileText("sim"), Hostile()], ids=["str", "any"])
def test_no_code_of_a_hostile_value_is_called(hostile):
    refused_alike({"point": hostile})
    refused_alike(FRAME | {"point": hostile})


@pytest.mark.parametrize("key", [HostileKey, lambda: HostileTextKey("point")])
def test_no_code_of_a_hostile_key_is_called(key):
    unnamed_alike({key(): "sim"})
    unnamed_alike({"run_id": "r1", key(): "board", "execution": 1})


def test_a_key_that_is_a_subclass_of_str_is_no_member():
    request = {Text("point"): "sim"}
    assert "point" in request
    unnamed_alike(request)


@pytest.mark.parametrize("request_", NO_OBJECT, ids=repr)
def test_a_request_that_is_no_dict_is_refused(request_):
    refused_alike(request_)


def test_a_dict_subclass_is_no_request():
    refused_alike(Mapping(point="sim"))
    refused_alike(Mapping(FRAME | {"point": "board"}))


@pytest.mark.parametrize("function", [check, step_of])
def test_a_missing_or_surplus_argument_is_a_type_error(function):
    with pytest.raises(TypeError):
        function()
    with pytest.raises(TypeError):
        function({"point": "sim"}, {"point": "sim"})


def test_step_of_returns_a_stated_value_or_refuses():
    values = [*ANOTHER_VALUE, Text("sim"), HostileText("board"), Hostile(), SIM, BOARD]
    returned = []
    for value in values:
        try:
            returned.append(step_of({"point": value}))
        except tools.ToolFailure as error:
            assert error.kind == tools.KIND_INVALID_REQUEST
    assert returned == [STEP_SIM, STEP_BOARD]
    assert set(returned) <= set(STEPS)


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for point in (SIM, BOARD):
        assert check(FRAME | {"point": point}) is None
        assert step_of(FRAME | {"point": point}) in STEPS
    refused_alike(dict(FRAME))
    refused_alike({"point": "Sim"})
    refused_alike({"point": None})
    refused_alike(None)
    unnamed_alike(FRAME | {"point": SIM, "draws": 1}, "draws")
    unnamed_alike({"point": SIM, "x\ny": None})
    assert list(tmp_path.iterdir()) == []


def test_module_imports_re_and_the_tools_only_and_has_no_entry():
    own = Path(check_identity.__file__)
    assert imported_modules(own) == {
        "re",
        "hilclaw",
        "hilclaw.tools",
    }
    assert not hasattr(check_identity, "main")
    assert "__main__" not in own.read_text(encoding="utf-8")


def test_the_text_and_the_code_hold_none_of_the_kept_out_strings():
    text = Path(check_identity.__file__).read_text(encoding="utf-8")
    assert "gemm_contract" not in text
    assert "standin_profile" not in text
    pieces = getattr(tokenize, "FSTRING_MIDDLE", tokenize.STRING)
    code = [
        token.string
        for token in tokenize.generate_tokens(io.StringIO(text).readline)
        if token.type in (tokenize.NAME, tokenize.STRING, pieces)
        and not token.string.startswith('"""')
    ]
    assert [string for string in code if "cannot be read" in string]
    for kept_out in (
        "tolerance_not_stated",
        "draws_not_stated",
        "op_signature_not",
        "operation_answer_invalid",
        "operation_failure_invalid",
        "step_open",
        "invalid_request",
    ):
        assert not [string for string in code if kept_out in string], kept_out
    for spelt_once in ("run_id", "execution"):
        assert [string for string in code if spelt_once in string] == [
            f'"{spelt_once}"'
        ]
    for spelt_once in ("correctness_check_sim_v2", "correctness_check_board_v2"):
        spelt = [string for string in code if spelt_once in string]
        assert spelt == [f'"{spelt_once}"']
    for retired in RETIRED:
        assert not [string for string in code if f'"{retired}"' == string], retired


def test_public_names_of_the_module_and_no_default():
    public = {
        name
        for name, value in vars(check_identity).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {
        "MEMBER",
        "SIM",
        "BOARD",
        "STEP_SIM",
        "STEP_BOARD",
        "STEPS",
        "NUMBERS",
        "MEMBERS",
        "check",
        "step_of",
    }
    for function in (check, step_of):
        parameters = list(inspect.signature(function).parameters.values())
        assert [parameter.name for parameter in parameters] == ["request"]
        assert parameters[0].default is inspect.Parameter.empty
        assert parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD


# --- one value per point for every contract (ADR-0183 decision 2) ---

RETIRED = (
    "correctness_check_sim",
    "correctness_check_board",
    "correctness_check_bf16_sim",
    "correctness_check_bf16_board",
)


def test_the_retired_values_are_none_of_the_steps_and_no_step_of_returns_them():
    assert not set(RETIRED) & set(STEPS)
    assert {step_of(FRAME | {"point": point}) for point in (SIM, BOARD)} == set(STEPS)
    assert not hasattr(check_identity, "step_of_read")
    assert not hasattr(check_identity, "BF16_STEPS")


@pytest.mark.parametrize(("point", "step"), [(SIM, STEP_SIM), (BOARD, STEP_BOARD)])
def test_the_step_follows_from_the_point_alone(point, step):
    request = FRAME | {"point": point}
    before = copy.deepcopy(request)
    assert step_of(request) == step
    for numbers in ({"round": 0}, {"candidate": 9, "attempt": 7}, {"execution": 3}):
        assert step_of(request | numbers) == step
    assert request == before


@pytest.mark.parametrize("value", [*RETIRED, "correctness_check_sim_v2", "sim_v2"])
def test_a_step_value_as_the_point_is_another_value(value):
    assert refusal(step_of, FRAME | {"point": value}) == refused_alike(
        FRAME | {"point": value}
    )
