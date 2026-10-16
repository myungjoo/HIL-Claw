import json
import re

import pytest

from hilclaw import json_text


def spelling(text):
    return json_text.load(text)[1]


def test_an_object_with_distinct_names_is_returned_as_a_dict_in_order():
    members = json_text.object_pairs([("b", 1), ("a", 2), ("c", 3)])
    assert type(members) is dict
    assert list(members.items()) == [("b", 1), ("a", 2), ("c", 3)]


def test_an_empty_object_is_an_empty_dict():
    assert json_text.object_pairs([]) == {}


def test_a_repeated_member_name_is_refused():
    with pytest.raises(ValueError) as caught:
        json_text.object_pairs([("a", 1), ("b", 2), ("a", 1)])
    assert str(caught.value) == "a JSON object repeats a member name"


@pytest.mark.parametrize("name", ["NaN", "Infinity", "-Infinity"])
def test_a_non_finite_token_is_refused(name):
    with pytest.raises(ValueError) as caught:
        json_text.no_constant(name)
    assert str(caught.value) == f"{name} is not a JSON value"


def test_the_literal_minus_zero_gives_the_sentinel():
    assert json_text.integer_literal("-0") is json_text.MINUS_ZERO


@pytest.mark.parametrize("literal", ["0", "7", "-1", "-00", "1" * 5000])
def test_any_other_integer_literal_gives_none(literal):
    assert json_text.integer_literal(literal) is None


def test_load_gives_the_document_and_the_spelling_of_one_text():
    text = '{"a": -0, "b": [1, -0, 2.5, "-0"], "c": {"d": true}}'
    document, spelled = json_text.load(text)
    assert document == {"a": 0, "b": [1, 0, 2.5, "-0"], "c": {"d": True}}
    assert type(document["a"]) is int
    assert spelled["a"] is json_text.MINUS_ZERO
    assert spelled["b"][0] is None
    assert spelled["b"][1] is json_text.MINUS_ZERO
    assert spelled["b"][2:] == [2.5, "-0"]
    assert spelled["c"] == {"d": True}


def test_load_refuses_a_repeated_member_name_in_the_document_parse():
    with pytest.raises(ValueError, match="^a JSON object repeats a member name$"):
        json_text.load('{"a": {"b": 1, "b": 1}}')


@pytest.mark.parametrize("name", ["NaN", "Infinity", "-Infinity"])
def test_load_refuses_a_non_finite_token(name):
    with pytest.raises(ValueError, match=f"^{re.escape(name)} is not a JSON value$"):
        json_text.load(f'{{"a": [{name}]}}')


@pytest.mark.parametrize("text", ["", "{} {}", "{", "[1,]"])
def test_load_passes_a_decode_error_through(text):
    with pytest.raises(json.JSONDecodeError):
        json_text.load(text)


def test_load_passes_a_recursion_error_through():
    depth = 1_000_000
    with pytest.raises(RecursionError):
        json_text.load("[" * depth + "]" * depth)


def test_load_does_not_refuse_what_is_no_object():
    assert json_text.load("[1, -0]") == ([1, 0], [None, json_text.MINUS_ZERO])


def test_a_spelling_without_minus_zero_gives_no_finding():
    assert json_text.minus_zero("", spelling('{"a": [1, {"b": 0}], "c": "x"}')) is None


def test_a_minus_zero_at_the_top_level_is_reported_at_its_path():
    assert json_text.minus_zero("", json_text.MINUS_ZERO) == ""
    assert json_text.minus_zero("round", json_text.MINUS_ZERO) == "round"


def test_a_minus_zero_in_a_nested_object_has_a_dotted_path():
    value = spelling('{"a": {"b": {"c": -0}}}')
    assert json_text.minus_zero("", value) == "a.b.c"
    assert json_text.minus_zero("top", value) == "top.a.b.c"


def test_a_minus_zero_in_an_array_has_an_indexed_path():
    assert json_text.minus_zero("", spelling('{"a": [1, 2, -0]}')) == "a[2]"
    assert json_text.minus_zero("", spelling("[[0], [1, -0]]")) == "[1][1]"


def test_a_minus_zero_in_an_array_of_objects():
    value = spelling('{"a": [{"b": 1}, {"c": [0, {"d": -0}]}]}')
    assert json_text.minus_zero("", value) == "a[1].c[1].d"


def test_the_first_minus_zero_in_pre_order_is_reported():
    value = spelling('{"z": {"y": [3, -0]}, "a": -0, "b": [-0]}')
    assert json_text.minus_zero("", value) == "z.y[1]"
    assert json_text.minus_zero("", spelling("[[1, [-0]], -0]")) == "[0][1][0]"


def test_a_skipped_path_hides_a_minus_zero_below_it_but_not_beside_it():
    skip = re.compile(r"ext|a\[[0-9]+\]\.free").fullmatch
    assert json_text.minus_zero("", spelling('{"ext": {"x": -0}}'), skip) is None
    hidden = spelling('{"a": [{"free": [-0]}, {"free": -0}]}')
    assert json_text.minus_zero("", hidden, skip) is None
    beside = spelling('{"ext": -0, "a": [{"free": -0, "kept": [-0]}]}')
    assert json_text.minus_zero("", beside, skip) == "a[0].kept[0]"


def test_skip_is_asked_for_the_starting_path_too():
    asked = []

    def skip(path):
        asked.append(path)
        return path == "start"

    assert json_text.minus_zero("start", json_text.MINUS_ZERO, skip) is None
    assert asked == ["start"]


def test_skip_is_asked_for_each_path_in_pre_order():
    asked = []

    def skip(path):
        asked.append(path)
        return False

    json_text.minus_zero("", spelling('{"a": [1, {"b": 2}], "c": 3}'), skip)
    assert asked == ["", "a", "a[0]", "a[1]", "a[1].b", "c"]


@pytest.mark.parametrize(
    "value",
    [0, -0.0, 0.0, "-0", False, True, None, "", [], {}, [0, -0.0, "-0", False]],
)
def test_values_close_to_minus_zero_are_not_reported(value):
    assert json_text.minus_zero("", value) is None


def test_a_member_named_minus_zero_is_not_reported():
    assert json_text.minus_zero("", spelling('{"-0": 1}')) is None
    assert json_text.minus_zero("", {"-0": "-0"}) is None


def test_a_minus_zero_float_in_a_text_is_not_reported():
    assert json_text.minus_zero("", spelling('{"a": -0.0, "b": -0e0}')) is None
