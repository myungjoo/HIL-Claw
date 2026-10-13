import ast
import copy
import inspect
import io
import json
import re
import struct
import tokenize
from pathlib import Path

import pytest

from hilclaw import (
    check_admission,
    check_ending,
    check_failure,
    check_operation,
    check_seed,
    gemm_contract,
    instance,
    keys,
    mock_check,
    tools,
)
from hilclaw.check_admission import Admitted
from hilclaw.check_ending import EndedWithoutOutcome
from hilclaw.check_parameters import CheckParameters
from hilclaw.check_seed import KIND_SEED_NOT_DRAWN, check, draw
from hilclaw.harness import seed_source
from hilclaw.harness.verification_arrays import VerificationArgumentError

# Test values: none is a seed, a number of draws, a dimension or a tolerance
# that the package defaults to or recommends.
SEED = 7
LAST = 2**64 - 1
SEEDS = [0, 2**63 + 12345, LAST]
ADMITTED = Admitted(m=3, k=4, n=5, draws=3, rtol=0.5, atol=3.0)
TIGHT = ADMITTED._replace(rtol=1e-5, atol=1e-6)
REQUEST = {"run_id": "r1", "execution": 1}
HW_PROFILE = {"accelerator": "mock"}
MARKER = "zq7_marker_zq7"
MESSAGE_LIMIT = 200
# A stand-in of this file: no record gives the name a meaning.
EXAMPLE_KIND = "example_kind"


class Whole(int):
    pass


class Wider(Admitted):
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


class Recording:
    def __init__(self, answer=None, error=None):
        self.answer = answer
        self.error = error
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.error is not None:
            raise self.error
        return self.answer


def needs_an_argument(wanted):
    return SEED


def parameters_of(admitted=ADMITTED, seed=SEED):
    return CheckParameters(seed, admitted.draws, admitted.m, admitted.k, admitted.n)


def good_report(admitted=ADMITTED, seed=SEED):
    return mock_check.default_script(
        "correctness.check", None, None, parameters_of(admitted, seed)
    )


def off_by_a_quarter():
    report = bytearray(good_report())
    (element,) = struct.unpack_from("=f", report, 4)
    struct.pack_into("=f", report, 4, element + 0.25)
    return bytes(report)


def checked(operation, admitted=ADMITTED, seed=SEED):
    return check(operation, REQUEST, HW_PROFILE, admitted, seed)


def carried(operation, admitted=ADMITTED, seed=SEED):
    return check_ending.carry_out(
        operation,
        REQUEST,
        HW_PROFILE,
        parameters_of(admitted, seed),
        rtol=admitted.rtol,
        atol=admitted.atol,
    )


def ending_of(call, operation):
    with pytest.raises(EndedWithoutOutcome) as caught:
        call(operation)
    assert type(caught.value) is EndedWithoutOutcome
    return caught.value.kind, caught.value.message


def held_by_the_module(error):
    held = []
    traceback = error.__traceback__
    while traceback is not None:
        frame = traceback.tb_frame
        if frame.f_code.co_filename == check_seed.__file__:
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
    assert vars(failure) == {"kind": failure.kind, "message": failure.message}
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


def admitted_in_memory():
    profile = {
        "schema_version": 1,
        "accelerator": "mock",
        "revision": "test-revision",
        "toolchain": {"clang": "test"},
        "host": {"cpu": "test", "os": "test"},
        "hw_source": "external",
    }
    record = {
        "schema_version": 1,
        "kind": "gemm",
        "shape": {"m": ADMITTED.m, "k": ADMITTED.k, "n": ADMITTED.n},
        "dtype": "fp32",
        "layout": "row_major",
    }
    document = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(profile).name, "record": profile},
        "op_signature": {"key": keys.op_signature_key(record).name, "record": record},
        "draws": ADMITTED.draws,
        "tolerance": {"rtol": ADMITTED.rtol, "atol": ADMITTED.atol},
    }
    stated = instance.parse(json.dumps(document).encode())
    return check_admission.admit(stated, covers=gemm_contract.covers)


def test_the_kind_is_a_name_of_its_own():
    assert KIND_SEED_NOT_DRAWN == "seed_not_drawn"
    assert type(KIND_SEED_NOT_DRAWN) is str
    assert re.fullmatch(r"[a-z][a-z0-9_]{0,31}", KIND_SEED_NOT_DRAWN)
    assert KIND_SEED_NOT_DRAWN not in tools.RESERVED_KINDS
    assert KIND_SEED_NOT_DRAWN not in check_admission.KINDS
    assert KIND_SEED_NOT_DRAWN != check_operation.KIND_OPERATION_ANSWER_INVALID
    assert KIND_SEED_NOT_DRAWN != check_failure.KIND_OPERATION_FAILURE_INVALID


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
        NotImplementedError(MARKER),
        tools.ToolFailure(EXAMPLE_KIND, MARKER),
        tools.ToolFailure(KIND_SEED_NOT_DRAWN, MARKER),
        seed_source.SeedSourceError(MARKER),
        type(MARKER, (Exception,), {})(MARKER),
    ],
    ids=[
        "os-error",
        "value-error",
        "runtime-error",
        "not-implemented",
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
    [
        -1,
        2**64,
        True,
        1.0,
        "7",
        MARKER,
        None,
        b"x",
        [MARKER],
        Whole(7),
        type(MARKER, (), {})(),
    ],
    ids=[
        "negative",
        "too-large",
        "bool",
        "float",
        "digits",
        "marker",
        "none",
        "bytes",
        "list",
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


def test_the_two_messages_differ_and_show_no_value():
    failed = message_of_a_failed_source()
    no_seed = message_of_no_seed()
    assert failed != no_seed
    assert not_drawn(Source(2**64)) == no_seed
    assert not any(character.isdigit() for character in failed + no_seed)


def test_a_draw_inside_a_handler_shows_only_the_outer_error():
    outer = LookupError()
    for source in (Source(ValueError(MARKER)), Source(MARKER)):
        with pytest.raises(tools.ToolFailure) as caught:
            try:
                raise outer
            except LookupError:
                draw(source)
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
    source = Source(SEED)
    for args, kwargs in (((), {}), ((source, source), {}), ((source,), {"other": 1})):
        with pytest.raises(TypeError) as caught:
            draw(*args, **kwargs)
        assert type(caught.value) is TypeError
    assert source.calls == []


def test_the_operation_is_called_once_with_the_three_and_the_five():
    request = dict(REQUEST)
    hw_profile = dict(HW_PROFILE)
    seed = LAST - 12345
    admitted = Admitted(m=3, k=4, n=5, draws=3, rtol=0.5, atol=3.0)
    operation = Recording(answer=good_report(admitted, seed))
    result = check(operation, request, hw_profile, admitted, seed)
    assert type(result) is dict
    assert result["outcome"] == "pass"
    assert len(operation.calls) == 1
    args, kwargs = operation.calls[0]
    assert kwargs == {}
    assert len(args) == 3
    assert args[0] is request
    assert args[1] is hw_profile
    assert type(args[2]) is CheckParameters
    assert args[2].seed is seed
    assert args[2].draws is admitted.draws
    assert args[2].m is admitted.m
    assert args[2].k is admitted.k
    assert args[2].n is admitted.n
    assert request == REQUEST
    assert hw_profile == HW_PROFILE
    assert admitted == ADMITTED


def test_the_six_values_and_the_seed_reach_carry_out_and_its_object_is_returned(
    monkeypatch,
):
    made = {"outcome": "pass"}
    stand_in = Recording(answer=made)
    monkeypatch.setattr(check_ending, "carry_out", stand_in)
    operation = Recording()
    seed = LAST - 12345
    assert check(operation, REQUEST, HW_PROFILE, ADMITTED, seed) is made
    assert operation.calls == []
    assert len(stand_in.calls) == 1
    args, kwargs = stand_in.calls[0]
    assert len(args) == 4
    assert args[0] is operation
    assert args[1] is REQUEST
    assert args[2] is HW_PROFILE
    assert type(args[3]) is CheckParameters
    assert args[3].seed is seed
    assert args[3] == parameters_of(ADMITTED, seed)
    assert set(kwargs) == {"rtol", "atol"}
    assert kwargs["rtol"] is ADMITTED.rtol
    assert kwargs["atol"] is ADMITTED.atol


def test_the_tolerance_of_the_admitted_check_is_the_one_that_judges():
    report = off_by_a_quarter()
    wide = checked(Recording(answer=report), ADMITTED)
    tight = checked(Recording(answer=report), TIGHT)
    assert wide["outcome"] == "pass"
    assert tight["outcome"] == "fail"
    assert wide["tolerance"] == {"rtol": ADMITTED.rtol, "atol": ADMITTED.atol}
    assert tight["tolerance"] == {"rtol": TIGHT.rtol, "atol": TIGHT.atol}
    assert wide == carried(Recording(answer=report), ADMITTED)
    assert tight == carried(Recording(answer=report), TIGHT)


@pytest.mark.parametrize("condition", ["time_limit", "exit_status"])
def test_a_condition_gives_the_broken_result_of_carry_out(condition):
    result = checked(Recording(answer=condition))
    assert result["outcome"] == "broken"
    assert result["condition"] == condition
    assert result["shape"] == {"m": ADMITTED.m, "k": ADMITTED.k, "n": ADMITTED.n}
    assert result["draws"] == ADMITTED.draws
    assert result == carried(Recording(answer=condition))


def test_the_default_script_of_the_mock_passes():
    operation = mock_check.operation(mock_check.default_script)
    result = checked(operation)
    assert result["outcome"] == "pass"
    assert result == carried(operation)


@pytest.mark.parametrize(
    "make",
    [
        lambda: Recording(answer=None),
        lambda: Recording(error=ValueError(MARKER)),
        lambda: Recording(error=tools.ToolFailure(EXAMPLE_KIND, MARKER)),
    ],
    ids=["neither-form", "error", "tool-failure"],
)
def test_an_ending_is_the_one_carry_out_gives(make):
    operation = make()
    kind, message = ending_of(checked, operation)
    assert len(operation.calls) == 1
    assert (kind, message) == ending_of(carried, make())
    assert MARKER not in message


def test_an_operation_that_raises_the_kind_of_the_draw_is_ended_with_another_kind():
    operation = Recording(error=tools.ToolFailure(KIND_SEED_NOT_DRAWN, MARKER))
    kind, message = ending_of(checked, operation)
    assert kind == check_failure.KIND_OPERATION_FAILURE_INVALID
    assert kind != KIND_SEED_NOT_DRAWN
    assert MARKER not in message


@pytest.mark.parametrize(
    "raised",
    [KeyboardInterrupt(), SystemExit(3), GeneratorExit()],
    ids=["keyboard-interrupt", "system-exit", "generator-exit"],
)
def test_a_request_to_end_out_of_the_operation_passes_as_the_same_object(raised):
    operation = Recording(error=raised)
    with pytest.raises(BaseException) as caught:
        checked(operation)
    assert caught.value is raised
    assert len(operation.calls) == 1


@pytest.mark.parametrize(
    "raised",
    [
        EndedWithoutOutcome(EXAMPLE_KIND, "some text"),
        tools.ToolFailure(EXAMPLE_KIND, "some text"),
        TypeError("some text"),
        VerificationArgumentError("some text"),
        SystemExit(3),
    ],
    ids=["ending", "tool-failure", "type-error", "refused-value", "system-exit"],
)
def test_what_carry_out_raises_passes_as_the_same_object(monkeypatch, raised):
    monkeypatch.setattr(check_ending, "carry_out", Recording(error=raised))
    with pytest.raises(BaseException) as caught:
        checked(Recording())
    assert caught.value is raised


@pytest.mark.parametrize(
    "admitted",
    [
        None,
        tuple(ADMITTED),
        ADMITTED._asdict(),
        parameters_of(),
        Wider(*ADMITTED),
    ],
    ids=["none", "tuple", "dict", "check-parameters", "subclass"],
)
def test_an_admitted_of_another_type_is_refused_before_the_call(admitted):
    operation = Recording(answer="time_limit")
    with pytest.raises(TypeError) as caught:
        checked(operation, admitted)
    assert type(caught.value) is TypeError
    assert operation.calls == []


@pytest.mark.parametrize("operation", [None, "time_limit", 3])
def test_an_operation_that_is_not_callable_raises_what_carry_out_raises(operation):
    with pytest.raises(TypeError) as caught:
        checked(operation)
    assert type(caught.value) is TypeError
    with pytest.raises(TypeError) as direct:
        carried(operation)
    assert str(caught.value) == str(direct.value)


@pytest.mark.parametrize(
    "seed",
    [-1, 2**64, True, "7", None],
    ids=["negative", "large", "bool", "str", "none"],
)
def test_a_seed_that_is_no_seed_is_not_checked_here(seed):
    operation = Recording(answer=good_report())
    with pytest.raises(VerificationArgumentError) as caught:
        checked(operation, seed=seed)
    with pytest.raises(VerificationArgumentError) as direct:
        carried(Recording(answer=good_report()), seed=seed)
    assert str(caught.value) == str(direct.value)
    assert len(operation.calls) == 1
    assert operation.calls[0][0][2].seed is seed
    # Observed, no rule: a condition is judged without the seed being looked at.
    condition = Recording(answer="time_limit")
    assert checked(condition, seed=seed) == carried(condition, seed=seed)
    assert ending_of(lambda made: checked(made, seed=seed), Recording()) == ending_of(
        carried, Recording()
    )


def test_the_call_of_check_is_checked_by_python():
    operation = Recording(answer="time_limit")
    four = (operation, REQUEST, HW_PROFILE, ADMITTED)
    for args, kwargs in (
        (four, {}),
        ((*four, SEED, SEED), {}),
        ((*four, SEED), {"rtol": 0.5}),
        ((), {}),
    ):
        with pytest.raises(TypeError) as caught:
            check(*args, **kwargs)
        assert type(caught.value) is TypeError
    assert operation.calls == []


def test_the_arguments_are_left_as_they_were():
    request = copy.deepcopy(REQUEST)
    hw_profile = copy.deepcopy(HW_PROFILE)
    admitted = Admitted(*ADMITTED)
    checked_with = (request, hw_profile, admitted, SEED)
    check(Recording(answer="time_limit"), *checked_with)
    with pytest.raises(EndedWithoutOutcome):
        check(Recording(error=ValueError(MARKER)), *checked_with)
    assert request == REQUEST
    assert hw_profile == HW_PROFILE
    assert admitted == ADMITTED


def test_admit_then_draw_then_check_ends_in_a_result():
    admitted = admitted_in_memory()
    assert admitted == ADMITTED
    source = Source(SEED)
    seed = draw(source)
    operation = mock_check.operation(mock_check.default_script)
    result = check(operation, REQUEST, HW_PROFILE, admitted, seed)
    assert result["outcome"] == "pass"
    assert len(source.calls) == 1


def test_when_the_source_fails_the_operation_is_never_called():
    admitted = admitted_in_memory()
    operation = Recording(answer="time_limit")
    source = Source(OSError(5, MARKER))
    with pytest.raises(tools.ToolFailure) as caught:
        seed = draw(source)
        check(operation, REQUEST, HW_PROFILE, admitted, seed)
    assert caught.value.kind == KIND_SEED_NOT_DRAWN
    assert operation.calls == []
    assert len(source.calls) == 1


def test_calls_write_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    draw(Source(SEED))
    draw(seed_source.system)
    not_drawn(Source(ValueError(MARKER)))
    not_drawn(Source(MARKER))
    with pytest.raises(SystemExit):
        draw(Source(SystemExit(3)))
    with pytest.raises(TypeError):
        draw(None)
    checked(Recording(answer=good_report()))
    checked(Recording(answer="time_limit"))
    ending_of(checked, Recording())
    ending_of(checked, Recording(error=tools.ToolFailure(EXAMPLE_KIND, MARKER)))
    with pytest.raises(TypeError):
        checked(Recording(), None)
    with pytest.raises(VerificationArgumentError):
        checked(Recording(answer=good_report()), seed=-1)
    assert list(tmp_path.iterdir()) == []


def test_module_imports_the_five_only_and_has_no_entry():
    own = Path(check_seed.__file__)
    assert imported_modules(own) == {
        "hilclaw",
        "hilclaw.check_admission",
        "hilclaw.check_ending",
        "hilclaw.check_parameters",
        "hilclaw.tools",
        "hilclaw.harness",
        "hilclaw.harness.seed_source",
    }
    assert not hasattr(check_seed, "main")
    assert "__main__" not in own.read_text(encoding="utf-8")


def test_the_text_and_the_code_hold_none_of_the_kept_out_strings():
    text = Path(check_seed.__file__).read_text(encoding="utf-8")
    assert "gemm_contract" not in text
    assert "standin_profile" not in text
    code = [
        token.string
        for token in tokenize.generate_tokens(io.StringIO(text).readline)
        if token.type in (tokenize.NAME, tokenize.STRING)
        and not token.string.startswith('"""')
    ]
    for kept_out in (
        "invalid_request",
        "no_backend",
        "not_offered",
        "run_file_",
        "step_open",
        "start_line_failed",
        "tool_crashed",
        "op_signature_not_",
        "draws_not_stated",
        "tolerance_not_stated",
        "operation_answer_invalid",
        "operation_failure_invalid",
        "correctness_check_",
        "secrets",
        "randbits",
        "system",
    ):
        assert not [string for string in code if kept_out in string], kept_out
    assert len([string for string in code if KIND_SEED_NOT_DRAWN in string]) == 1


def test_public_names_of_the_module_and_no_default():
    public = {
        name
        for name, value in vars(check_seed).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {"KIND_SEED_NOT_DRAWN", "draw", "check"}
    positional = inspect.Parameter.POSITIONAL_OR_KEYWORD
    for function, names in (
        (draw, ["source"]),
        (check, ["operation", "request", "hw_profile", "admitted", "seed"]),
    ):
        parameters = list(inspect.signature(function).parameters.values())
        assert [parameter.name for parameter in parameters] == names
        for parameter in parameters:
            assert parameter.default is inspect.Parameter.empty, parameter
            assert parameter.kind is positional, parameter
