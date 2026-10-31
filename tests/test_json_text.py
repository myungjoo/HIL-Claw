import ast
import inspect
import json
import re

import pytest

from hilclaw import json_text


class Found(Exception):
    pass


def spelling(text):
    return json.loads(text, parse_int=json_text.mark_minus_zero)


def refuse(path, text, skip=None):
    return json_text.refuse_minus_zero(path, spelling(text), Found, skip)


def found(path, text, skip=None):
    with pytest.raises(Found) as caught:
        refuse(path, text, skip)
    assert type(caught.value) is Found
    assert caught.value.__cause__ is None
    return str(caught.value)


def message(path):
    return f"{path}: is written as -0, which is no integer"


# --- happy ---


def test_distinct_names_give_a_dict_in_order():
    made = json_text.distinct_members([("b", 1), ("a", 2), ("c", 3)])
    assert type(made) is dict
    assert list(made.items()) == [("b", 1), ("a", 2), ("c", 3)]


def test_no_pairs_give_an_empty_dict():
    assert json_text.distinct_members([]) == {}


def test_the_hooks_work_inside_a_parse():
    text = '{"b": {"x": 1.5, "y": [true, null]}, "a": 2}'
    document = json.loads(
        text,
        object_pairs_hook=json_text.distinct_members,
        parse_constant=json_text.no_constant,
    )
    assert document == {"b": {"x": 1.5, "y": [True, None]}, "a": 2}
    assert list(document) == ["b", "a"]


@pytest.mark.parametrize("literal", ["0", "1", "-1", "00", "-00", "10", ""])
def test_literals_other_than_minus_zero_are_not_marked(literal):
    assert json_text.mark_minus_zero(literal) is None


def test_the_mark_is_one_object_and_no_value_of_json():
    mark = json_text.mark_minus_zero("-0")
    assert mark is json_text.mark_minus_zero("-0")
    assert type(mark) is object


def test_a_spelling_with_no_minus_zero_gives_no_finding():
    text = '{"a": 0, "b": [1, {"c": -1}], "d": "x", "e": null, "f": true, "g": 1.5}'
    assert refuse("top", text) is None


# --- error ---


def test_a_repeated_name_gives_the_exact_message():
    with pytest.raises(ValueError) as caught:
        json_text.distinct_members([("a", 1), ("b", 2), ("a", 3)])
    assert type(caught.value) is ValueError
    assert str(caught.value) == "a JSON object repeats a member name"


def test_a_name_repeated_with_the_same_value_is_refused():
    with pytest.raises(ValueError, match="repeats a member name"):
        json_text.distinct_members([("a", 1), ("a", 1)])


@pytest.mark.parametrize("name", ["NaN", "Infinity", "-Infinity"])
def test_each_constant_gives_the_exact_message(name):
    with pytest.raises(ValueError) as caught:
        json.loads(name, parse_constant=json_text.no_constant)
    assert type(caught.value) is ValueError
    assert str(caught.value) == f"{name} is not a JSON value"


def test_a_minus_zero_gives_the_exact_path():
    assert found("a", '{"b": [{"c": -0}]}') == message("a.b[0].c")


def test_the_error_class_is_the_one_given():
    class Other(ValueError):
        pass

    with pytest.raises(Other) as caught:
        json_text.refuse_minus_zero("a", spelling("-0"), Other)
    assert type(caught.value) is Other


# --- branch ---


@pytest.mark.parametrize(
    ("text", "path"),
    [
        ("-0", "top"),
        ('{"a": -0}', "top.a"),
        ("[1, -0]", "top[1]"),
        ('[{"a": 1}, {"b": -0}]', "top[1].b"),
        ('{"a": [[-0]]}', "top.a[0][0]"),
    ],
)
def test_each_place_of_a_minus_zero(text, path):
    assert found("top", text) == message(path)


@pytest.mark.parametrize(
    ("text", "path"),
    [
        ('{"b": -0, "a": -0}', "top.b"),
        ('{"a": [-0], "b": -0}', "top.a[0]"),
        ('{"a": {"z": -0}, "b": -0}', "top.a.z"),
        ("[-0, -0]", "top[0]"),
        ('[{"a": -0}, -0]', "top[0].a"),
    ],
)
def test_the_first_in_pre_order_wins(text, path):
    assert found("top", text) == message(path)


def test_a_skipped_path_hides_what_is_below_it():
    assert refuse("top", '{"free": {"a": [-0]}}', "top.free".__eq__) is None


def test_a_skipped_path_hides_a_minus_zero_at_that_path():
    assert refuse("top", '{"free": -0}', "top.free".__eq__) is None


def test_a_skipped_path_does_not_hide_what_is_beside_it():
    text = '{"free": -0, "beside": -0}'
    assert found("top", text, "top.free".__eq__) == message("top.beside")


def test_a_skipped_path_does_not_hide_what_is_before_it():
    text = '{"before": -0, "free": 1}'
    assert found("top", text, "top.free".__eq__) == message("top.before")


def test_skip_may_be_a_full_match_of_a_pattern():
    skip = re.compile(r"top\[[0-9]+\]\.free").fullmatch
    text = '[{"free": -0}, {"free": [-0], "kept": -0}]'
    assert found("top", text, skip) == message("top[1].kept")


def test_skip_sees_each_path_in_pre_order_before_its_value():
    seen = []

    def skip(path):
        seen.append(path)
        return False

    assert refuse("top", '{"a": [1, {"b": 2}], "c": 3}', skip) is None
    assert seen == ["top", "top.a", "top.a[0]", "top.a[1]", "top.a[1].b", "top.c"]


# --- negative ---


@pytest.mark.parametrize(
    "text",
    [
        "0",
        "-0.0",
        "-0e0",
        '"-0"',
        "false",
        '{"-0": 1}',
        '{"a": "-0"}',
        "[0, -0.0, false]",
    ],
)
def test_what_is_no_minus_zero_literal_is_not_reported(text):
    assert refuse("top", text) is None


@pytest.mark.parametrize("value", [0, -0.0, "-0", False, None, {"-0": 0}, [0, "-0"]])
def test_values_built_in_memory_are_not_reported(value):
    assert json_text.refuse_minus_zero("top", value, Found) is None


def test_a_member_named_minus_zero_with_a_minus_zero_value_gives_its_path():
    assert found("top", '{"-0": -0}') == message("top.-0")


def test_a_minus_zero_parsed_without_the_hook_is_not_seen():
    assert json_text.refuse_minus_zero("top", json.loads("-0"), Found) is None


# --- the module ---


def test_the_module_imports_nothing():
    tree = ast.parse(inspect.getsource(json_text))
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Import | ast.ImportFrom)]


def test_the_public_names():
    public = {
        name
        for name, value in vars(json_text).items()
        if getattr(value, "__module__", None) == json_text.__name__
        and not name.startswith("_")
    }
    assert public == {
        "distinct_members",
        "mark_minus_zero",
        "no_constant",
        "refuse_minus_zero",
    }
    for name in public:
        assert getattr(json_text, name).__doc__
