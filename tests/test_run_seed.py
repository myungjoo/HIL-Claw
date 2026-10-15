import ast
import inspect
import io
import re
import tokenize
from pathlib import Path

import pytest

from hilclaw import check_seed, run_objective, run_seed, tools
from hilclaw.harness import seed_source
from hilclaw.run_seed import KIND_SEED_NOT_DRAWN, draw

LAST = 2**64 - 1
SEEDS = [0, 2**63 + 12345, LAST]
MARKER = "zq7_marker_zq7"
MESSAGE_LIMIT = 200
# A stand-in of this file: no record gives the name a meaning.
EXAMPLE_KIND = "example_kind"


class Whole(int):
    pass


class Source:
    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer


def needs_an_argument(wanted):
    return 7


def held_by_the_module(error):
    held = []
    traceback = error.__traceback__
    while traceback is not None:
        frame = traceback.tb_frame
        if frame.f_code.co_filename == run_seed.__file__:
            held.extend(frame.f_locals.values())
            for value in frame.f_locals.values():
                for cell in getattr(value, "__closure__", None) or ():
                    held.append(cell.cell_contents)
        traceback = traceback.tb_next
    return held


def not_drawn(source, kept_out=()):
    with pytest.raises(tools.ToolFailure) as caught:
        draw(source)
    failure = caught.value
    assert type(failure) is tools.ToolFailure
    assert failure.kind == KIND_SEED_NOT_DRAWN
    assert type(failure.message) is str
    assert len(failure.message) <= MESSAGE_LIMIT
    assert MARKER not in failure.message
    assert failure.args == (KIND_SEED_NOT_DRAWN, failure.message)
    assert failure.error_object() == {
        "error": {"kind": KIND_SEED_NOT_DRAWN, "message": failure.message}
    }
    assert failure.__cause__ is None
    assert failure.__context__ is None
    held = held_by_the_module(failure)
    assert not [value for value in held if isinstance(value, BaseException)]
    for value in kept_out:
        assert not [found for found in held if found is value]
    return failure.message


def message_of_a_failed_source():
    return not_drawn(Source(RuntimeError()))


def message_of_no_seed():
    return not_drawn(Source(-1))


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


def test_the_kind_is_the_run_tools_own_with_the_checks_spelling():
    assert KIND_SEED_NOT_DRAWN == "seed_not_drawn" == check_seed.KIND_SEED_NOT_DRAWN
    assert type(KIND_SEED_NOT_DRAWN) is str
    assert re.fullmatch(r"[a-z][a-z0-9_]{0,31}", KIND_SEED_NOT_DRAWN)
    assert KIND_SEED_NOT_DRAWN not in tools.RESERVED_KINDS
    assert KIND_SEED_NOT_DRAWN not in run_objective.KINDS


@pytest.mark.parametrize("seed", SEEDS)
def test_a_seed_is_returned_as_the_same_object_and_the_source_asked_once(seed):
    source = Source(seed)
    drawn = draw(source)
    assert drawn is seed
    assert type(drawn) is int
    assert source.calls == [((), {})]


def test_two_draws_ask_twice_and_keep_nothing():
    answers = iter(SEEDS)
    calls = []

    def source():
        calls.append(None)
        return next(answers)

    assert draw(source) is SEEDS[0]
    assert draw(source) is SEEDS[1]
    assert len(calls) == 2
    assert not_drawn(Source(None)) == message_of_no_seed()
    assert draw(source) is SEEDS[2]


def test_the_source_of_the_package_yields_a_seed():
    drawn = draw(seed_source.system)
    assert type(drawn) is int
    assert 0 <= drawn < seed_source.SEED_LIMIT


@pytest.mark.parametrize(
    "raised",
    [
        OSError(5, MARKER),
        ValueError(MARKER),
        RuntimeError(MARKER),
        tools.ToolFailure(EXAMPLE_KIND, MARKER),
        tools.ToolFailure(KIND_SEED_NOT_DRAWN, MARKER),
        seed_source.SeedSourceError(MARKER),
        type(MARKER, (Exception,), {})(MARKER),
    ],
    ids=[
        "os-error",
        "value-error",
        "runtime-error",
        "tool-failure",
        "tool-failure-of-the-kind",
        "seed-source-error",
        "marked-class",
    ],
)
def test_a_source_that_raises_an_error_is_not_drawn(raised):
    source = Source(raised)
    message = not_drawn(source, kept_out=[raised])
    assert message == message_of_a_failed_source()
    assert source.calls == [((), {})]
    assert type(raised).__name__ not in message


def test_a_source_that_needs_an_argument_is_a_source_that_fails():
    assert not_drawn(needs_an_argument) == message_of_a_failed_source()


@pytest.mark.parametrize(
    "named",
    [-1, 2**64, True, 1.0, "7", MARKER, None, Whole(7), type(MARKER, (), {})()],
    ids=[
        "negative",
        "too-large",
        "bool",
        "float",
        "digits",
        "marker",
        "none",
        "int-subclass",
        "marked-class",
    ],
)
def test_a_source_that_names_no_seed_is_not_drawn(named):
    source = Source(named)
    kept_out = [] if named is None or named is True else [named]
    message = not_drawn(source, kept_out=kept_out)
    assert message == message_of_no_seed()
    assert source.calls == [((), {})]
    assert type(named).__name__ not in message
    assert "7" not in message


def test_the_two_messages_differ_name_the_timing_seed_and_show_no_value():
    failed = message_of_a_failed_source()
    no_seed = message_of_no_seed()
    assert failed != no_seed
    assert failed == run_seed._SOURCE_FAILED
    assert no_seed == run_seed._NAMED_NO_SEED
    assert "timing seed" in failed and "timing seed" in no_seed
    assert "raised" in failed and "raised" not in no_seed
    assert "returned" in no_seed and "returned" not in failed
    assert failed != check_seed._SOURCE_FAILED
    assert no_seed != check_seed._NAMED_NO_SEED
    assert not any(character.isdigit() for character in failed + no_seed)


def test_a_draw_inside_a_handler_shows_only_the_outer_error():
    outer = LookupError()
    for source in (Source(ValueError(MARKER)), Source(MARKER)):
        with pytest.raises(tools.ToolFailure) as caught:
            try:
                raise outer
            except LookupError:
                draw(source)
        assert caught.value.kind == KIND_SEED_NOT_DRAWN
        assert caught.value.__cause__ is None
        assert caught.value.__context__ is outer


@pytest.mark.parametrize(
    "raised",
    [KeyboardInterrupt(), SystemExit(3), GeneratorExit()],
    ids=["keyboard-interrupt", "system-exit", "generator-exit"],
)
def test_a_request_to_end_out_of_the_source_passes_as_the_same_object(raised):
    source = Source(raised)
    with pytest.raises(BaseException) as caught:
        draw(source)
    assert caught.value is raised
    assert len(source.calls) == 1


@pytest.mark.parametrize("source", [None, "source", 7], ids=["none", "str", "int"])
def test_what_is_no_source_is_a_type_error_and_never_the_kind(source):
    with pytest.raises(TypeError) as caught:
        draw(source)
    assert type(caught.value) is TypeError


def test_the_call_of_draw_is_checked_by_python():
    source = Source(7)
    for args, kwargs in (((), {}), ((source, source), {}), ((source,), {"other": 1})):
        with pytest.raises(TypeError) as caught:
            draw(*args, **kwargs)
        assert type(caught.value) is TypeError
    assert source.calls == []


def test_calls_write_no_file_and_print_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    draw(Source(7))
    draw(seed_source.system)
    not_drawn(Source(ValueError(MARKER)))
    not_drawn(Source(MARKER))
    with pytest.raises(SystemExit):
        draw(Source(SystemExit(3)))
    with pytest.raises(TypeError):
        draw(None)
    assert list(tmp_path.iterdir()) == []
    assert capsys.readouterr() == ("", "")


def test_module_imports_the_two_its_docstring_names_and_has_no_entry():
    own = Path(run_seed.__file__)
    assert imported_modules(own) == {
        "hilclaw",
        "hilclaw.tools",
        "hilclaw.harness",
        "hilclaw.harness.seed_source",
    }
    assert ":mod:`hilclaw.harness.seed_source` and :mod:`hilclaw.tools`" in (
        " ".join(run_seed.__doc__.split())
    )
    assert not hasattr(run_seed, "main")
    assert "__main__" not in own.read_text(encoding="utf-8")


def test_the_code_binds_no_source_and_names_one_kind():
    text = Path(run_seed.__file__).read_text(encoding="utf-8")
    code = [
        token.string
        for token in tokenize.generate_tokens(io.StringIO(text).readline)
        if token.type in (tokenize.NAME, tokenize.STRING)
        and not token.string.startswith('"""')
    ]
    for kept_out in (
        "secrets",
        "randbits",
        "system",
        "check_seed",
        "print",
        "open",
        "write",
        "tool_crashed",
        "start_line_failed",
        "objective_not_",
    ):
        assert not [string for string in code if kept_out in string], kept_out
    assert len([string for string in code if KIND_SEED_NOT_DRAWN in string]) == 1


def test_public_names_of_the_module_and_no_default():
    public = {
        name
        for name, value in vars(run_seed).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {"KIND_SEED_NOT_DRAWN", "draw"}
    parameters = list(inspect.signature(draw).parameters.values())
    assert [parameter.name for parameter in parameters] == ["source"]
    assert parameters[0].default is inspect.Parameter.empty
    assert parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
