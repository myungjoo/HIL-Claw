import inspect
import os
import random
import re
import secrets
import time
import types

import numpy as np
import pytest

from hilclaw.harness import seed_source, verification_arrays
from hilclaw.harness.seed_source import SeedSourceError, draw, system
from hilclaw.harness.verification import program_arguments
from hilclaw.harness.verification_arrays import (
    VerificationArgumentError,
    draw_inputs,
)

pytestmark = pytest.mark.filterwarnings("error")

LAST = 2**64 - 1
SEEDS = [0, 1, 2**63 + 12345, LAST]

NOT_AN_INT = "the seed source named no seed: got {}, not an int"
OUTSIDE = "the seed source named no seed: an int outside 0 <= seed < 2**64"
FAILED = "the seed source failed: {}"


class Whole(int):
    pass


class Source:
    def __init__(self, *answers):
        self.answers = answers
        self.calls = 0

    def __call__(self):
        self.calls += 1
        answer = self.answers[min(self.calls, len(self.answers)) - 1]
        if isinstance(answer, BaseException):
            raise answer
        return answer


class Bits:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.widths = []

    def randbits(self, width):
        self.widths.append(width)
        return self.answers[len(self.widths) - 1]


def harness_accepts(seed):
    accepted = []
    for call in (
        lambda: program_arguments(m=1, k=1, n=1, draws=1, seed=seed),
        lambda: draw_inputs(1, 1, 1, seed=seed, draw=0),
    ):
        try:
            call()
        except VerificationArgumentError:
            accepted.append(False)
        else:
            accepted.append(True)
    assert accepted[0] == accepted[1]
    return accepted[0]


def module_accepts(seed):
    try:
        return draw(lambda: seed) is seed
    except SeedSourceError:
        return False


def fail(*args, **kwargs):
    raise AssertionError("the default generator of random was used")


def texts_of(error):
    return [str(error), repr(error), *(repr(arg) for arg in error.args)]


OUT_OF_RANGE = [-1, 2**64, 2**64 + 1, -(2**64), 2**200]
NOT_INTS = [
    True,
    False,
    1.0,
    "1",
    None,
    b"\x01",
    [1],
    np.uint64(7),
    np.int64(7),
    Whole(7),
]
LONG_VALUES = [
    -(2**70 + 918273645),
    2**64 + 987654321987,
    2**90 + 135792468,
    123456789012.25,
    "9182736455463728",
    b"7766554433221100",
    [5544332211009988],
    np.uint64(18446744073709551557),
    Whole(1357924680135792),
]


# --- system ---


def test_system_returns_exactly_an_int_inside_the_range_on_each_call():
    for _ in range(500):
        seed = system()
        assert type(seed) is int
        assert 0 <= seed < 2**64


def test_system_takes_no_parameter():
    assert not inspect.signature(system).parameters
    with pytest.raises(TypeError):
        system(1)
    with pytest.raises(TypeError):
        system(seed=1)


def test_system_gives_the_whole_range_of_the_generator_unchanged(monkeypatch):
    bits = Bits(0, LAST, 2**63)
    monkeypatch.setattr(seed_source, "secrets", bits)
    assert [system(), system(), system()] == [0, LAST, 2**63]
    assert bits.widths == [64, 64, 64]


def test_system_does_not_use_the_default_generator_of_random(monkeypatch):
    for name in ("random", "getrandbits", "randrange", "randint", "randbytes"):
        monkeypatch.setattr(random, name, fail)
    assert 0 <= system() < 2**64


@pytest.mark.parametrize(
    "environment",
    [{}, {"HILCLAW_SEED": "7", "SEED": "7", "RANDOM_SEED": "7", "PYTHONHASHSEED": "7"}],
    ids=["emptied", "filled"],
)
def test_system_follows_no_variable_no_reseeding_and_no_clock(monkeypatch, environment):
    for name in list(os.environ):
        monkeypatch.delenv(name)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    for name in ("time", "monotonic", "perf_counter"):
        monkeypatch.setattr(time, name, lambda: 1234.5)
        monkeypatch.setattr(time, f"{name}_ns", lambda: 1234500000000)
    seeds = set()
    for _ in range(4):
        random.seed(20261009)
        seeds.add(system())
    # four equal draws of a working generator have probability 2**-192
    assert len(seeds) > 1


def test_the_module_keeps_nothing_between_calls():
    before = dict(vars(seed_source))
    first, second = draw(system), draw(system)
    system()
    after = dict(vars(seed_source))
    assert after.keys() == before.keys()
    assert all(after[name] is before[name] for name in before)
    assert type(first) is int and type(second) is int


def test_the_module_holds_no_module_but_secrets():
    held = {
        name: value
        for name, value in vars(seed_source).items()
        if isinstance(value, types.ModuleType)
    }
    assert held == {"secrets": secrets}


# --- draw ---


@pytest.mark.parametrize("seed", SEEDS)
def test_draw_returns_exactly_what_the_source_named(seed):
    source = Source(seed)
    assert draw(source) is seed
    assert source.calls == 1


def test_draw_of_the_system_source_gives_a_seed_the_harness_accepts():
    for _ in range(20):
        seed = draw(system)
        assert type(seed) is int
        assert harness_accepts(seed)


def test_two_draws_ask_twice_and_return_the_two_answers_in_order():
    source = Source(11, 2**64 - 2)
    assert [draw(source), draw(source)] == [11, 2**64 - 2]
    assert source.calls == 2


def test_a_refused_answer_does_not_change_the_next_draw():
    source = Source(-5, 42, "no seed", 43)
    with pytest.raises(SeedSourceError):
        draw(source)
    assert draw(source) == 42
    with pytest.raises(SeedSourceError):
        draw(source)
    assert draw(source) == 43
    assert source.calls == 4


@pytest.mark.parametrize("value", OUT_OF_RANGE)
def test_an_int_outside_the_range_is_refused_and_not_repaired(value):
    source = Source(value)
    with pytest.raises(SeedSourceError) as caught:
        draw(source)
    assert str(caught.value) == OUTSIDE
    assert caught.value.args == (OUTSIDE,)
    assert caught.value.__cause__ is None
    assert source.calls == 1


@pytest.mark.parametrize("value", NOT_INTS, ids=lambda value: type(value).__name__)
def test_what_is_not_exactly_an_int_is_refused_and_not_converted(value):
    source = Source(value)
    with pytest.raises(SeedSourceError) as caught:
        draw(source)
    expected = NOT_AN_INT.format(type(value).__name__)
    assert str(caught.value) == expected
    assert caught.value.args == (expected,)
    assert source.calls == 1


@pytest.mark.parametrize("value", LONG_VALUES, ids=lambda value: type(value).__name__)
def test_nothing_raised_shows_a_value_a_source_returned(value):
    shown = re.findall(r"[0-9]{6,}", repr(value))
    if isinstance(value, (int, np.integer)):
        number = abs(int(value))
        shown += [format(number, "x"), format(number, "X")]
    assert shown
    with pytest.raises(SeedSourceError) as caught:
        draw(Source(value))
    for text in texts_of(caught.value):
        assert not any(digits in text for digits in shown)
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None


def test_nothing_is_printed_and_no_file_appears(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    system()
    draw(system)
    draw(Source(7))
    for source in (Source(-1), Source("1"), Source(ValueError("9182736455"))):
        with pytest.raises(SeedSourceError):
            draw(source)
    with pytest.raises(TypeError):
        draw(None)
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "error",
    [ValueError("9182736455"), OSError(5, "no random source"), NotImplementedError()],
    ids=lambda error: type(error).__name__,
)
def test_a_source_that_raises_is_reported_with_its_cause(error):
    source = Source(error)
    with pytest.raises(SeedSourceError) as caught:
        draw(source)
    expected = FAILED.format(type(error).__name__)
    assert str(caught.value) == expected
    assert caught.value.args == (expected,)
    assert caught.value.__cause__ is error
    assert source.calls == 1


def test_a_callable_that_needs_an_argument_is_a_source_that_raises():
    with pytest.raises(SeedSourceError) as caught:
        draw(lambda seed: seed)
    assert str(caught.value) == FAILED.format("TypeError")
    assert isinstance(caught.value.__cause__, TypeError)


def test_a_failing_system_generator_is_reported_with_its_cause(monkeypatch):
    error = NotImplementedError("no random source on this platform")

    class Dry:
        def randbits(self, width):
            raise error

    monkeypatch.setattr(seed_source, "secrets", Dry())
    with pytest.raises(NotImplementedError) as passed_on:
        system()
    assert passed_on.value is error
    with pytest.raises(SeedSourceError) as caught:
        draw(system)
    assert caught.value.__cause__ is error


@pytest.mark.parametrize("kind", [KeyboardInterrupt, SystemExit, GeneratorExit])
def test_what_is_no_exception_passes_through_untouched(kind):
    error = kind()
    source = Source(error)
    with pytest.raises(kind) as caught:
        draw(source)
    assert caught.value is error
    assert source.calls == 1


@pytest.mark.parametrize("source", [None, 7, "system", 1.5, [system]])
def test_what_is_not_callable_is_a_type_error(source):
    with pytest.raises(TypeError) as caught:
        draw(source)
    assert not isinstance(caught.value, SeedSourceError)
    assert str(caught.value) == "the seed source must be callable"


def test_draw_takes_exactly_one_source():
    with pytest.raises(TypeError):
        draw()
    with pytest.raises(TypeError):
        draw(system, system)


def test_the_error_is_no_tool_failure_and_no_argument_error():
    assert SeedSourceError.__mro__ == (
        SeedSourceError,
        Exception,
        BaseException,
        object,
    )


# --- with the harness: the same range and the same rule ---


def test_the_range_is_the_range_of_the_harness():
    assert seed_source.SEED_LIMIT == verification_arrays.SEED_LIMIT
    assert seed_source.SEED_LIMIT == 2**seed_source.SEED_BITS == 2**64


@pytest.mark.parametrize(
    "value",
    [*SEEDS, 2**64 - 2, *OUT_OF_RANGE, *NOT_INTS, 0.0, "0", -0.0],
    ids=repr,
)
def test_a_value_is_a_seed_here_exactly_when_the_harness_accepts_it(value):
    assert module_accepts(value) == harness_accepts(value)


def test_the_last_seed_and_the_first_value_above_are_the_same_for_all():
    assert module_accepts(LAST) and harness_accepts(LAST)
    assert not module_accepts(LAST + 1) and not harness_accepts(LAST + 1)
    assert module_accepts(0) and harness_accepts(0)
    assert not module_accepts(-1) and not harness_accepts(-1)
