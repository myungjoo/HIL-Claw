import copy
import json

import pytest

from hilclaw import events, journal, keys
from hilclaw.journal import EMPTY, Identity, SpendView
from hilclaw.run_state import (
    SCHEMA_VERSION,
    InvalidStateError,
    RunState,
    UnsupportedVersionError,
    dump,
    from_stored,
    parse,
    to_stored,
    validate,
)

# Synthetic values only: no step name, axis or member of a real run.
STEP = "example_step"
AXIS = "example_axis"
OTHER_AXIS = "other_example_axis"
MAX = keys.MAX_INTEGER
TOO_LONG = 10**5000

# The Example of ADR-0012, as written in the record.
START = (
    b'{"schema_version": 1, "round": 0, "budget_spent":'
    b' {"totals": {}, "position": 0, "open_steps": []}}\n'
)
AFTER = (
    b'{"schema_version": 1, "round": 4, "budget_spent": {"totals": {"example_axis": 7},'
    b' "position": 3, "open_steps": [{"round": 3, "candidate": 1, "attempt": 1,'
    b' "step": "example_step", "execution": 1}]}}\n'
)
AFTER_VIEW = SpendView({AXIS: 7}, 3, frozenset({Identity(STEP, 1, 3, 1, 1)}))

# The Example of ADR-0011, as written in the record.
LINES = [
    json.loads(text)
    for text in (
        (
            '{"schema_version": 1, "time": "2026-01-01T00:00:00Z", "kind": "step_started",'
            ' "round": 3, "candidate": 2, "attempt": 1,'
            ' "data": {"step": "example_step", "execution": 1}}'
        ),
        (
            '{"schema_version": 1, "time": "2026-01-01T00:04:10Z", "kind": "step_ended",'
            ' "round": 3, "candidate": 2, "attempt": 1,'
            ' "data": {"step": "example_step", "execution": 1,'
            ' "spend": {"example_axis": 7}, "result": {"example_member": 1}}}'
        ),
    )
]

# One identity of each level, then one that differs from the last in each member.
IDENTITIES = [
    Identity("b_step", 1),
    Identity(STEP, 1, 0),
    Identity(STEP, 1, 3, 1),
    Identity(STEP, 1, 3, 1, 1),
    Identity(STEP, 2, 3, 1, 1),
    Identity("f_step", 1, 3, 1, 1),
    Identity(STEP, 1, 3, 1, 2),
    Identity(STEP, 1, 3, 2, 1),
    Identity(STEP, 1, 4, 1, 1),
]
WRITTEN_ORDER = [
    {"step": "b_step", "execution": 1},
    {"round": 0, "step": STEP, "execution": 1},
    {"round": 3, "candidate": 1, "step": STEP, "execution": 1},
    {"round": 3, "candidate": 1, "attempt": 1, "step": STEP, "execution": 1},
    {"round": 3, "candidate": 1, "attempt": 1, "step": STEP, "execution": 2},
    {"round": 3, "candidate": 1, "attempt": 1, "step": "f_step", "execution": 1},
    {"round": 3, "candidate": 1, "attempt": 2, "step": STEP, "execution": 1},
    {"round": 3, "candidate": 2, "attempt": 1, "step": STEP, "execution": 1},
    {"round": 4, "candidate": 1, "attempt": 1, "step": STEP, "execution": 1},
]


def step(**changes):
    members = {"round": 3, "candidate": 1, "attempt": 1, "step": STEP, "execution": 1}
    members.update(changes)
    return {name: value for name, value in members.items() if value is not ...}


def spent(**changes):
    stored = {"totals": {AXIS: 7}, "position": 3, "open_steps": [step()]}
    stored.update(changes)
    return {name: value for name, value in stored.items() if value is not ...}


def doc(**changes):
    document = {"schema_version": 1, "round": 4, "budget_spent": spent()}
    document.update(changes)
    return {name: value for name, value in document.items() if value is not ...}


def content(document):
    return json.dumps(document).encode("utf-8")


def raw(budget_spent='{"totals": {}, "position": 0, "open_steps": []}', rest=""):
    text = f'{{"schema_version": 1, "round": 0, "budget_spent": {budget_spent}{rest}}}'
    return text.encode("utf-8")


def invalid(place, call, *arguments):
    with pytest.raises(InvalidStateError) as caught:
        call(*arguments)
    assert str(caught.value).startswith(place), str(caught.value)


def invalid_both(place, document):
    before = copy.deepcopy(document)
    invalid(place, validate, document)
    invalid(place, parse, content(document))
    assert document == before


def test_example_files_of_the_record_read_to_their_values():
    assert parse(START) == RunState(0, EMPTY, {})
    assert parse(AFTER) == RunState(4, AFTER_VIEW, {})
    for example in (START, AFTER):
        assert validate(json.loads(example)) is None


def test_example_files_are_what_dump_writes_for_their_values():
    for example, written in ((START, dump(0, EMPTY)), (AFTER, dump(4, AFTER_VIEW))):
        ordered = json.loads(written, object_pairs_hook=list)
        assert ordered == json.loads(example, object_pairs_hook=list)


def test_parse_returns_the_view_of_the_journal_module():
    state = parse(AFTER)
    assert type(state) is RunState
    assert type(state.round) is int
    assert type(state.budget_spent) is SpendView
    assert type(state.budget_spent.open_steps) is frozenset
    assert all(type(identity) is Identity for identity in state.budget_spent.open_steps)
    with pytest.raises(TypeError):
        state.budget_spent.totals[AXIS] = 0
    assert journal.fold((), state.budget_spent) == (AFTER_VIEW, ())


@pytest.mark.parametrize("count", [0, 1, 2])
def test_views_of_the_adr_0011_example_convert_without_loss(count):
    view, _ = journal.fold(LINES[:count])
    stored = to_stored(view)
    assert from_stored(stored) == view
    assert from_stored(json.loads(json.dumps(stored))) == view
    assert parse(dump(3, view)) == RunState(3, view, {})
    tail, _ = journal.fold(LINES[count:], from_stored(stored))
    assert tail == journal.fold(LINES)[0]


def test_stored_form_of_the_folded_example():
    assert to_stored(journal.fold(LINES[:1])[0]) == {
        "totals": {},
        "position": 1,
        "open_steps": [
            {"round": 3, "candidate": 2, "attempt": 1, "step": STEP, "execution": 1}
        ],
    }
    assert to_stored(journal.fold(LINES)[0]) == {
        "totals": {AXIS: 7},
        "position": 2,
        "open_steps": [],
    }
    assert to_stored(EMPTY) == {"totals": {}, "position": 0, "open_steps": []}


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        0,
        -1,
        1.5,
        "text",
        [],
        [1, [2, {"a": None}]],
        {"round": "x", "b": {}},
    ],
)
def test_undefined_top_level_member_comes_back_uninterpreted(value):
    document = doc(example_member=value, other_example_member={"example_member": 1})
    assert validate(document) is None
    state = parse(content(document))
    assert state.round == 4
    assert state.budget_spent == AFTER_VIEW
    assert state.others == {
        "example_member": value,
        "other_example_member": {"example_member": 1},
    }
    assert parse(dump(4, AFTER_VIEW, state.others)) == state


def test_validate_does_not_look_at_undefined_members():
    assert validate(doc(example_member=object(), **{"Example Member": {1, 2}})) is None


def test_number_beyond_the_float_range_in_an_undefined_member_is_an_infinity():
    state = parse(raw(rest=', "example_member": [1e999, -1e999]'))
    assert state.others == {"example_member": [float("inf"), float("-inf")]}


def test_no_rule_between_round_and_the_open_steps():
    document = doc(round=0, budget_spent=spent(open_steps=[step(round=9)]))
    assert validate(document) is None
    state = parse(content(document))
    assert state.round == 0
    assert state.budget_spent.open_steps == {Identity(STEP, 1, 9, 1, 1)}


@pytest.mark.parametrize(
    ("members", "identity"),
    [
        ({"step": STEP, "execution": 1}, Identity(STEP, 1)),
        ({"step": STEP, "execution": 2, "round": 0}, Identity(STEP, 2, 0)),
        (
            {"round": 3, "candidate": 1, "step": STEP, "execution": 1},
            Identity(STEP, 1, 3, 1),
        ),
        (
            {
                "attempt": MAX,
                "candidate": MAX,
                "round": MAX,
                "execution": MAX,
                "step": STEP,
            },
            Identity(STEP, MAX, MAX, MAX, MAX),
        ),
    ],
)
def test_identity_of_every_level(members, identity):
    view = from_stored(spent(open_steps=[members]))
    assert view.open_steps == {identity}
    assert to_stored(view)["open_steps"] == [
        {
            name: members[name]
            for name in ("round", "candidate", "attempt", "step", "execution")
            if name in members
        }
    ]
    assert (
        parse(content(doc(budget_spent=spent(open_steps=[members])))).budget_spent
        == view
    )


def test_total_above_the_integer_range_is_exact():
    view = SpendView({AXIS: 2**64, OTHER_AXIS: 0}, MAX, frozenset())
    assert to_stored(view) == {
        "totals": {AXIS: 2**64, OTHER_AXIS: 0},
        "position": MAX,
        "open_steps": [],
    }
    written = dump(0, view)
    assert b"18446744073709551616" in written
    assert parse(written).budget_spent == view
    state = parse(
        raw(
            '{"totals": {"example_axis": 18446744073709551617}, "position": 0, "open_steps": []}'
        )
    )
    assert state.budget_spent.totals == {AXIS: 2**64 + 1}
    assert type(state.budget_spent.totals[AXIS]) is int


def test_axis_with_total_zero_and_empty_members_are_kept():
    view = from_stored({"totals": {AXIS: 0}, "position": 0, "open_steps": []})
    assert view == SpendView({AXIS: 0}, 0, frozenset())
    assert to_stored(view)["totals"] == {AXIS: 0}
    assert dump(0, EMPTY) == (
        b'{\n "schema_version": 1,\n "round": 0,\n "budget_spent": {\n'
        b'  "totals": {},\n  "position": 0,\n  "open_steps": []\n }\n}\n'
    )


def test_any_order_of_members_axes_and_open_steps_is_read():
    text = (
        b'{"example_member": 1, "budget_spent": {"open_steps": ['
        b'{"execution": 1, "step": "example_step", "attempt": 1, "candidate": 1, "round": 3},'
        b' {"step": "a_step", "execution": 1}], "position": 3,'
        b' "totals": {"other_example_axis": 1, "example_axis": 7}},'
        b' "round": 4, "schema_version": 1}'
    )
    view = SpendView(
        {AXIS: 7, OTHER_AXIS: 1},
        3,
        frozenset({Identity(STEP, 1, 3, 1, 1), Identity("a_step", 1)}),
    )
    assert parse(text) == RunState(4, view, {"example_member": 1})


@pytest.mark.parametrize(
    "text",
    [
        AFTER.replace(b"\n", b""),
        AFTER.replace(b", ", b",\r\n").replace(b"\n", b"\r\n"),
        b" \t\r\n" + AFTER + b"\n\n \t\r\n",
        AFTER.replace(b" ", b""),
        dump(4, AFTER_VIEW).replace(b"\n", b"\r\n"),
    ],
)
def test_line_ends_and_white_space_bind_the_writer_only(text):
    assert parse(text) == RunState(4, AFTER_VIEW, {})


def test_written_form():
    view = SpendView(
        {OTHER_AXIS: 2**64, AXIS: 7, "a_axis": 0}, 3, {IDENTITIES[3], IDENTITIES[0]}
    )
    others = {
        "z_member": [1, {"b": None, "a": "\u00e9"}],
        "example_member": {"y": 1.5, "x": True},
    }
    assert dump(4, view, others).decode("ascii") == (
        "{\n"
        ' "schema_version": 1,\n'
        ' "round": 4,\n'
        ' "budget_spent": {\n'
        '  "totals": {\n'
        '   "a_axis": 0,\n'
        '   "example_axis": 7,\n'
        '   "other_example_axis": 18446744073709551616\n'
        "  },\n"
        '  "position": 3,\n'
        '  "open_steps": [\n'
        "   {\n"
        '    "step": "b_step",\n'
        '    "execution": 1\n'
        "   },\n"
        "   {\n"
        '    "round": 3,\n'
        '    "candidate": 1,\n'
        '    "attempt": 1,\n'
        '    "step": "example_step",\n'
        '    "execution": 1\n'
        "   }\n"
        "  ]\n"
        " },\n"
        ' "example_member": {\n'
        '  "x": true,\n'
        '  "y": 1.5\n'
        " },\n"
        ' "z_member": [\n'
        "  1,\n"
        "  {\n"
        '   "a": "\\u00e9",\n'
        '   "b": null\n'
        "  }\n"
        " ]\n"
        "}\n"
    )


def test_open_steps_are_written_in_the_order_of_decision_4():
    for steps in (IDENTITIES, IDENTITIES[::-1], IDENTITIES[4:] + IDENTITIES[:4]):
        view = SpendView({}, 0, frozenset(steps))
        assert to_stored(view)["open_steps"] == WRITTEN_ORDER
        assert [list(members) for members in to_stored(view)["open_steps"]] == [
            list(members) for members in WRITTEN_ORDER
        ]
    stored = json.loads(dump(0, SpendView({}, 0, set(IDENTITIES))))
    assert stored["budget_spent"]["open_steps"] == WRITTEN_ORDER


def test_step_names_are_ordered_by_code_point():
    names = ["a_", "a0", "aa", "a", "z", "b9"]
    view = SpendView({}, 0, {Identity(name, 1) for name in names})
    written = [members["step"] for members in to_stored(view)["open_steps"]]
    assert written == ["a", "a0", "a_", "aa", "b9", "z"]


def test_bytes_are_a_function_of_the_values():
    one = SpendView({AXIS: 7, OTHER_AXIS: 1}, 3, frozenset(IDENTITIES))
    other = SpendView({OTHER_AXIS: 1, AXIS: 7}, 3, {*IDENTITIES[4:], *IDENTITIES[:4]})
    assert one == other
    first = dump(4, one, {"b_member": {"y": 1, "x": 2}, "a_member": 0})
    second = dump(4, other, {"a_member": 0, "b_member": {"x": 2, "y": 1}})
    assert first == second
    assert first == dump(4, one, {"b_member": {"y": 1, "x": 2}, "a_member": 0})
    assert list(json.loads(first)) == [
        "schema_version",
        "round",
        "budget_spent",
        "a_member",
        "b_member",
    ]
    assert list(json.loads(first)["budget_spent"]) == [
        "totals",
        "position",
        "open_steps",
    ]
    assert list(json.loads(first)["budget_spent"]["totals"]) == [AXIS, OTHER_AXIS]


def test_written_form_reads_back_to_the_values():
    view = SpendView({AXIS: 2**70, OTHER_AXIS: 0}, MAX, set(IDENTITIES))
    others = {"example_member": {"a": [1, 2.5, None, "\ud800 \u00e9 \n"]}, "b": False}
    written = dump(MAX, view, others)
    assert type(written) is bytes
    assert written.endswith(b"}\n")
    assert b"\r" not in written
    assert written.decode("ascii")
    assert parse(written) == RunState(MAX, view, others)
    assert validate(json.loads(written)) is None
    assert dump(*parse(written)) == written
    assert json.loads(dump(0, EMPTY, None)) == json.loads(dump(0, EMPTY, {}))


def test_arguments_are_not_modified_and_nothing_is_shared():
    totals = {OTHER_AXIS: 1, AXIS: 7}
    steps = {IDENTITIES[3], IDENTITIES[0]}
    view = SpendView(totals, 3, steps)
    others = {"example_member": {"b": [1], "a": 2}}
    kept = copy.deepcopy(others)
    stored = to_stored(view)
    dump(4, view, others)
    assert list(totals) == [OTHER_AXIS, AXIS]
    assert steps == {IDENTITIES[3], IDENTITIES[0]}
    assert others == kept
    assert list(others["example_member"]) == ["b", "a"]
    stored["totals"][AXIS] = 0
    stored["open_steps"].clear()
    assert view == SpendView(
        {OTHER_AXIS: 1, AXIS: 7}, 3, {IDENTITIES[3], IDENTITIES[0]}
    )

    given = spent()
    before = copy.deepcopy(given)
    read = from_stored(given)
    assert given == before
    given["totals"][AXIS] = 0
    given["open_steps"].clear()
    assert read == AFTER_VIEW

    document = doc(example_member=[1])
    before = copy.deepcopy(document)
    validate(document)
    assert document == before


@pytest.mark.parametrize(
    "text",
    [
        b'{"schema_version": -0, "round": 0}',
        b'{"schema_version": 0}',
    ],
)
def test_version_zero_is_unsupported(text):
    with pytest.raises(
        UnsupportedVersionError, match="schema_version: 0 is not supported"
    ):
        parse(text)


def test_minus_zero_is_the_integer_zero_except_as_a_total():
    text = raw(
        '{"totals": {}, "position": -0,'
        ' "open_steps": [{"round": -0, "step": "example_step", "execution": 1}]}',
        ', "example_member": -0',
    ).replace(b'"round": 0', b'"round": -0')
    state = parse(text)
    assert state == RunState(
        0, SpendView({}, 0, {Identity(STEP, 1, 0)}), {"example_member": 0}
    )
    assert type(state.round) is int
    signed = raw(
        '{"totals": {"a_axis": 0, "example_axis": -0}, "position": 0, "open_steps": []}'
    )
    invalid("budget_spent.totals.example_axis: has a sign", parse, signed)
    assert validate(json.loads(signed)) is None


@pytest.mark.parametrize("version", [2, 0, MAX])
def test_unsupported_version_is_not_invalidity(version):
    for document in (
        doc(schema_version=version),
        {"schema_version": version},
        {"schema_version": version, "round": "x", "budget_spent": None},
    ):
        for call, argument in ((validate, document), (parse, content(document))):
            with pytest.raises(UnsupportedVersionError) as caught:
                call(argument)
            assert str(caught.value) == f"schema_version: {version} is not supported"
            assert not isinstance(caught.value, ValueError)
            assert not isinstance(caught.value, events.UnsupportedVersionError)


def test_text_rules_come_before_the_version():
    invalid("content: ", parse, b'{"schema_version": 2, "a": 1, "a": 2}')
    invalid("content: ", parse, b'{"schema_version": 2, "a": NaN}')
    invalid("content: ", parse, b'\xef\xbb\xbf{"schema_version": 2}')


BROKEN_TEXTS = {
    "not_utf8": b"\xff",
    "encoded_surrogate": b'{"schema_version": 1, "round": 0, "example_member": "\xed\xa0\x80"}',
    "utf16": START.decode("ascii").encode("utf-16"),
    "byte_order_mark": b"\xef\xbb\xbf" + START,
    "empty": b"",
    "white_space_only": b" \r\n\t",
    "two_texts": START + START,
    "trailing_bytes": START + b"x",
    "cut_off": START[:-2],
    "single_quotes": b"{'schema_version': 1}",
    "nan": raw(rest=', "example_member": NaN'),
    "infinity": raw(rest=', "example_member": [Infinity]'),
    "minus_infinity": raw(rest=', "example_member": {"a": -Infinity}'),
    "name_twice_at_the_top": raw(rest=', "round": 0'),
    "undefined_name_twice": raw(rest=', "example_member": 1, "example_member": 1'),
    "name_twice_in_an_undefined_member": raw(
        rest=', "example_member": [{"a": 1, "a": 2}]'
    ),
    "name_twice_in_budget_spent": raw(
        '{"totals": {}, "position": 0, "open_steps": [], "position": 0}'
    ),
    "axis_twice": raw(
        '{"totals": {"example_axis": 1, "example_axis": 1}, "position": 0, "open_steps": []}'
    ),
    "name_twice_in_an_identity": raw(
        '{"totals": {}, "position": 0, "open_steps":'
        ' [{"step": "example_step", "execution": 1, "step": "example_step"}]}'
    ),
    "integer_too_long_in_an_undefined_member": raw(
        rest=', "example_member": ' + "9" * 5000
    ),
    "total_too_long": raw(
        '{"totals": {"example_axis": '
        + "9" * 5000
        + '}, "position": 0, "open_steps": []}'
    ),
}


@pytest.mark.parametrize("text", BROKEN_TEXTS.values(), ids=BROKEN_TEXTS)
def test_content_that_breaks_a_rule_of_the_text(text):
    invalid("content: ", parse, text)


def test_nesting_too_deep_for_the_interpreter_is_reported():
    text = raw(rest=', "example_member": ' + "[" * 2_000_000 + "]" * 2_000_000)
    invalid("content: is nested too deeply to parse", parse, text)


@pytest.mark.parametrize(
    "text", [b"[]", b"1", b'"text"', b"null", b"true", b"[" + START + b"]"]
)
def test_content_that_is_not_an_object(text):
    invalid("document: must be an object", parse, text)


@pytest.mark.parametrize(
    "value", [START.decode("ascii"), bytearray(START), memoryview(START), None, {}]
)
def test_content_must_be_bytes(value):
    with pytest.raises(TypeError, match="content must be bytes"):
        parse(value)


@pytest.mark.parametrize("value", [[], None, 1, "text", (("schema_version", 1),)])
def test_document_must_be_a_dict(value):
    invalid("document: must be an object", validate, value)


@pytest.mark.parametrize(
    ("place", "document"),
    [
        ("document: lacks the member schema_version", doc(schema_version=...)),
        ("document: lacks the member schema_version", {}),
        ("schema_version: ", doc(schema_version=True)),
        ("schema_version: ", doc(schema_version=1.0)),
        ("schema_version: ", doc(schema_version="1")),
        ("schema_version: ", doc(schema_version=-1)),
        ("schema_version: ", doc(schema_version=2**53)),
        ("schema_version: ", doc(schema_version=None)),
        ("schema_version: ", doc(schema_version=[1])),
        ("document: lacks the member round", doc(round=...)),
        ("round: ", doc(round=True)),
        ("round: ", doc(round=-1)),
        ("round: ", doc(round=1.0)),
        ("round: ", doc(round=2**53)),
        ("round: ", doc(round="0")),
        ("round: ", doc(round=None)),
        ("document: lacks the member budget_spent", doc(budget_spent=...)),
        ("budget_spent: must be an object", doc(budget_spent=[])),
        ("budget_spent: must be an object", doc(budget_spent=None)),
        ("budget_spent: must be an object", doc(budget_spent=7)),
        ("budget_spent: lacks the member totals", doc(budget_spent=spent(totals=...))),
        (
            "budget_spent: lacks the member position",
            doc(budget_spent=spent(position=...)),
        ),
        (
            "budget_spent: lacks the member open_steps",
            doc(budget_spent=spent(open_steps=...)),
        ),
        (
            "budget_spent: must be an object without",
            doc(budget_spent=spent(example_member=1)),
        ),
        ("budget_spent: must be an object without", doc(budget_spent=spent(offset=0))),
    ],
)
def test_document_that_breaks_a_rule(place, document):
    invalid_both(place, document)


@pytest.mark.parametrize(
    ("place", "changes"),
    [
        ("budget_spent.totals: must be an object", {"totals": []}),
        ("budget_spent.totals: must be an object", {"totals": None}),
        ("budget_spent.totals.example_axis: ", {"totals": {AXIS: True}}),
        ("budget_spent.totals.example_axis: ", {"totals": {AXIS: 1.5}}),
        ("budget_spent.totals.example_axis: ", {"totals": {AXIS: 1.0}}),
        ("budget_spent.totals.example_axis: ", {"totals": {AXIS: -1}}),
        ("budget_spent.totals.example_axis: ", {"totals": {AXIS: "1"}}),
        ("budget_spent.totals.example_axis: ", {"totals": {AXIS: None}}),
        ("budget_spent.totals.example_axis: ", {"totals": {"a_axis": 0, AXIS: [1]}}),
        ("budget_spent.totals: member name", {"totals": {"Example": 1}}),
        ("budget_spent.totals: member name", {"totals": {"": 1}}),
        ("budget_spent.totals: member name", {"totals": {"a" * 33: 1}}),
        ("budget_spent.totals: member name", {"totals": {"1axis": 1}}),
        ("budget_spent.position: ", {"position": 2**53}),
        ("budget_spent.position: ", {"position": -1}),
        ("budget_spent.position: ", {"position": True}),
        ("budget_spent.position: ", {"position": 1.0}),
        ("budget_spent.position: ", {"position": None}),
        ("budget_spent.open_steps: must be an array", {"open_steps": {}}),
        ("budget_spent.open_steps: must be an array", {"open_steps": None}),
        ("budget_spent.open_steps[0]: must be an object", {"open_steps": [[]]}),
        (
            "budget_spent.open_steps[1]: must be an object",
            {"open_steps": [step(), STEP]},
        ),
        (
            "budget_spent.open_steps[0]: lacks the member step",
            {"open_steps": [step(step=...)]},
        ),
        (
            "budget_spent.open_steps[0]: lacks the member execution",
            {"open_steps": [step(execution=...)]},
        ),
        ("budget_spent.open_steps[0].execution: ", {"open_steps": [step(execution=0)]}),
        (
            "budget_spent.open_steps[0].execution: ",
            {"open_steps": [step(execution=True)]},
        ),
        (
            "budget_spent.open_steps[0].execution: ",
            {"open_steps": [step(execution=2**53)]},
        ),
        (
            "budget_spent.open_steps[0].execution: ",
            {"open_steps": [step(execution=1.0)]},
        ),
        ("budget_spent.open_steps[0].step: ", {"open_steps": [step(step="Example")]}),
        ("budget_spent.open_steps[0].step: ", {"open_steps": [step(step=1)]}),
        ("budget_spent.open_steps[0].round: ", {"open_steps": [step(round=-1)]}),
        ("budget_spent.open_steps[0].round: ", {"open_steps": [step(round=2**53)]}),
        ("budget_spent.open_steps[0].round: ", {"open_steps": [step(round="3")]}),
        ("budget_spent.open_steps[0].candidate: ", {"open_steps": [step(candidate=0)]}),
        ("budget_spent.open_steps[0].attempt: ", {"open_steps": [step(attempt=0)]}),
        ("budget_spent.open_steps[0].attempt: ", {"open_steps": [step(attempt=True)]}),
        (
            "budget_spent.open_steps[0].candidate: is given only together with round",
            {"open_steps": [step(round=...)]},
        ),
        (
            "budget_spent.open_steps[2].attempt: is given only together with candidate",
            {"open_steps": [step(), step(execution=2), step(candidate=...)]},
        ),
        ("budget_spent.open_steps[0].round: ", {"open_steps": [step(round=None)]}),
        (
            "budget_spent.open_steps[0].candidate: ",
            {"open_steps": [step(candidate=None)]},
        ),
        ("budget_spent.open_steps[0].attempt: ", {"open_steps": [step(attempt=None)]}),
        ("budget_spent.open_steps[0].step: ", {"open_steps": [step(step=None)]}),
        (
            "budget_spent.open_steps[0].execution: ",
            {"open_steps": [step(execution=None)]},
        ),
        (
            "budget_spent.open_steps[0]: must be an object without",
            {"open_steps": [step(example_member=1)]},
        ),
        (
            "budget_spent.open_steps[0]: must be an object without",
            {"open_steps": [step(data={})]},
        ),
        (
            "budget_spent.open_steps[1]: repeats open_steps[0]",
            {"open_steps": [step(), step()]},
        ),
        (
            "budget_spent.open_steps[3]: repeats open_steps[1]",
            {
                "open_steps": [
                    step(execution=2),
                    step(),
                    {"step": STEP, "execution": 1},
                    dict(reversed(step().items())),
                ]
            },
        ),
        (
            "budget_spent.open_steps[1]: repeats open_steps[0]",
            {
                "open_steps": [
                    {"step": STEP, "execution": 1},
                    {"execution": 1, "step": STEP},
                ]
            },
        ),
    ],
)
def test_budget_spent_that_breaks_a_rule(place, changes):
    stored = spent(**changes)
    before = copy.deepcopy(stored)
    invalid(place, from_stored, stored)
    assert stored == before
    invalid_both(place, doc(budget_spent=stored))


@pytest.mark.parametrize("value", [None, [], "text", 0, AFTER_VIEW])
def test_from_stored_refuses_what_is_not_an_object(value):
    invalid("budget_spent: must be an object", from_stored, value)


def test_integer_too_long_to_show_is_still_named():
    invalid("round: ", validate, doc(round=TOO_LONG))
    invalid("budget_spent.position: ", from_stored, spent(position=TOO_LONG))
    invalid(
        "budget_spent.totals.example_axis: ",
        from_stored,
        spent(totals={AXIS: -TOO_LONG}),
    )
    invalid(
        "budget_spent.open_steps[0].execution: ",
        from_stored,
        spent(open_steps=[step(execution=TOO_LONG)]),
    )
    assert from_stored(spent(totals={AXIS: TOO_LONG})).totals[AXIS] == TOO_LONG


@pytest.mark.parametrize(
    ("place", "view"),
    [
        ("view: ", None),
        ("view: ", ({}, 0, frozenset())),
        ("view: ", {"totals": {}, "position": 0, "open_steps": []}),
        ("view.position: ", SpendView({}, 2**53, frozenset())),
        ("view.position: ", SpendView({}, -1, frozenset())),
        ("view.position: ", SpendView({}, True, frozenset())),
        ("view.position: ", SpendView({}, 1.0, frozenset())),
        ("view.totals: ", SpendView([], 0, frozenset())),
        ("view.totals: member name", SpendView({"Example": 1}, 0, frozenset())),
        ("view.totals.example_axis: ", SpendView({AXIS: -1}, 0, frozenset())),
        ("view.totals.example_axis: ", SpendView({AXIS: True}, 0, frozenset())),
        ("view.totals.example_axis: ", SpendView({AXIS: 1.0}, 0, frozenset())),
        ("view.open_steps: ", SpendView({}, 0, [Identity(STEP, 1)])),
        ("view.open_steps: ", SpendView({}, 0, {(STEP, 1, None, None, None)})),
        ("view.open_steps: ", SpendView({}, 0, {Identity("Example", 1)})),
        ("view.open_steps: ", SpendView({}, 0, {Identity(STEP, 0)})),
        ("view.open_steps: ", SpendView({}, 0, {Identity(STEP, 1, None, 1)})),
        ("view.open_steps: ", SpendView({}, 0, {Identity(STEP, 1, 0, None, 1)})),
    ],
)
def test_view_that_cannot_be_stored(place, view):
    invalid(place, to_stored, view)
    invalid(place, dump, 0, view)


@pytest.mark.parametrize(
    "value", [True, -1, 1.0, 2**53, None, "0", pytest.param(TOO_LONG, id="too_long")]
)
def test_dump_refuses_a_round_that_is_no_integer(value):
    invalid("round: ", dump, value, EMPTY)


def nested(depth):
    value = []
    for _ in range(depth):
        value = [value]
    return {"example_member": value}


CYCLE = {}
CYCLE["example_member"] = CYCLE


@pytest.mark.parametrize(
    "others",
    [
        [],
        "text",
        0,
        (("example_member", 1),),
        {1: 1},
        {"example_member": float("nan")},
        {"example_member": [float("inf")]},
        {"example_member": {1, 2}},
        {"example_member": (1, 2)},
        {"example_member": {"a": b"bytes"}},
        {"example_member": TOO_LONG},
        nested(100000),
        CYCLE,
        {"schema_version": 1},
        {"round": 0},
        {"budget_spent": {"totals": {}, "position": 0, "open_steps": []}},
        {"example_member": 1, "round": None},
    ],
)
def test_dump_refuses_other_members_that_break_the_rule(others):
    invalid("others: ", dump, 0, EMPTY, others)


def test_total_too_long_for_the_interpreter_is_an_error_and_never_rounded():
    view = SpendView({AXIS: TOO_LONG}, 0, frozenset())
    assert to_stored(view)["totals"][AXIS] == TOO_LONG
    invalid("view.totals: is too long to write", dump, 0, view)


def test_public_names():
    assert SCHEMA_VERSION == 1
    assert issubclass(InvalidStateError, ValueError)
    assert not issubclass(UnsupportedVersionError, ValueError)
    assert RunState._fields == ("round", "budget_spent", "others")
