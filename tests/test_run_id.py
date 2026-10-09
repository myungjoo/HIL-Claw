import builtins
import datetime
import functools
import importlib
import inspect
import os
import random
import re
import secrets
import types

import pytest

from hilclaw import layout, run_id

pytestmark = pytest.mark.filterwarnings("error")

UTC = datetime.UTC
SHAPE = re.compile("[0-9]{8}t[0-9]{6}z-[0-9a-f]{16}")
LAST = 2**64 - 1
EXAMPLE_TIME = datetime.datetime(2026, 10, 9, 1, 23, 31, tzinfo=UTC)
EXAMPLE_BITS = 0x9F3A6C1E0B7D4A52
EXAMPLE = "20261009t012331z-9f3a6c1e0b7d4a52"
NAIVE = EXAMPLE_TIME.replace(tzinfo=None)

NO_TIME = "time must be a datetime.datetime"
NO_UTC = "time must have an offset of zero from UTC"
NO_INT = "bits must be an int"
OUTSIDE = "bits must be an int with 0 <= bits < 2**64"


class Whole(int):
    pass


class Moment(datetime.datetime):
    pass


class Zone(datetime.tzinfo):
    def __init__(self, offset):
        self.offset = offset

    def utcoffset(self, when):
        if isinstance(self.offset, BaseException):
            raise self.offset
        return self.offset

    def dst(self, when):
        return None

    def tzname(self, when):
        return "GMT"


class Bits:
    def __init__(self, *answers):
        self.answers = answers
        self.widths = []

    def randbits(self, width):
        self.widths.append(width)
        answer = self.answers[len(self.widths) - 1]
        if isinstance(answer, BaseException):
            raise answer
        return answer


class Clock:
    def __init__(self, *readings):
        self.readings = readings
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.readings[self.calls - 1]


def utc(*fields):
    return datetime.datetime(*fields, tzinfo=UTC)


def fail(*args, **kwargs):
    raise AssertionError("a name the module must not use was called")


def refused(kind, message, time, bits):
    with pytest.raises(kind) as caught:
        run_id.compose(time, bits)
    assert type(caught.value) is kind
    assert caught.value.args == (message,)


# --- the module ---


def test_the_public_names_are_the_two_functions():
    held = vars(run_id).items()
    modules = {n: v for n, v in held if isinstance(v, types.ModuleType)}
    public = {n for n, v in held if not n.startswith("_") and n not in modules}
    assert public == {"compose", "new"}
    assert modules == {
        "datetime": datetime,
        "functools": functools,
        "secrets": secrets,
    }


def test_the_signatures():
    assert list(inspect.signature(run_id.compose).parameters) == ["time", "bits"]
    assert not inspect.signature(run_id.new).parameters


def test_the_module_keeps_nothing_between_calls():
    before = dict(vars(run_id))
    run_id.new()
    run_id.compose(EXAMPLE_TIME, EXAMPLE_BITS)
    with pytest.raises(ValueError):
        run_id.compose(EXAMPLE_TIME, -1)
    run_id.new()
    after = dict(vars(run_id))
    assert after.keys() == before.keys()
    assert all(after[name] is before[name] for name in before)


def test_importing_and_calling_opens_and_lists_nothing(monkeypatch, capsys):
    monkeypatch.setattr(builtins, "open", fail)
    for name in ("listdir", "scandir", "mkdir", "makedirs", "stat"):
        monkeypatch.setattr(os, name, fail)
    try:
        importlib.reload(run_id)
        assert SHAPE.fullmatch(run_id.new())
        assert run_id.compose(EXAMPLE_TIME, EXAMPLE_BITS) == EXAMPLE
    finally:
        monkeypatch.undo()
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")


# --- compose: the form ---


def test_the_example_of_the_record():
    built = run_id.compose(EXAMPLE_TIME, EXAMPLE_BITS)
    assert built == EXAMPLE
    assert type(built) is str
    assert len(built) == 33
    assert SHAPE.fullmatch(built)
    assert layout.check_run_id(built) is built


@pytest.mark.parametrize(
    ("time", "written"),
    [
        (utc(1, 1, 1), "00010101t000000z"),
        (utc(999, 12, 31, 23, 59, 59), "09991231t235959z"),
        (utc(9999, 12, 31, 23, 59, 59), "99991231t235959z"),
        (utc(2026, 1, 2, 3, 4, 5), "20260102t030405z"),
        (utc(2026, 10, 9, 23, 59, 59), "20261009t235959z"),
        (utc(2024, 2, 29, 0, 0, 0), "20240229t000000z"),
    ],
)
def test_the_time_part_is_fixed_in_width_with_leading_zeros(time, written):
    built = run_id.compose(time, 0)
    assert built == written + "-0000000000000000"
    assert layout.check_run_id(built) is built


@pytest.mark.parametrize(
    ("bits", "written"),
    [
        (0, "0000000000000000"),
        (1, "0000000000000001"),
        (0xABCDEF, "0000000000abcdef"),
        (2**63, "8000000000000000"),
        (LAST, "ffffffffffffffff"),
    ],
)
def test_the_random_part_is_padded_lower_case_hexadecimal(bits, written):
    built = run_id.compose(EXAMPLE_TIME, bits)
    assert built == "20261009t012331z-" + written
    assert len(built) == 33
    assert layout.check_run_id(built) is built


@pytest.mark.parametrize("microsecond", [1, 499999, 500000, 999999])
def test_a_fraction_of_a_second_is_dropped_and_not_rounded(microsecond):
    time = utc(9999, 12, 31, 23, 59, 59, microsecond)
    assert run_id.compose(time, 0) == "99991231t235959z-0000000000000000"


@pytest.mark.parametrize(
    "zone",
    [
        UTC,
        datetime.timezone(datetime.timedelta(0)),
        datetime.timezone(datetime.timedelta(0), "Z"),
        Zone(datetime.timedelta(0)),
    ],
    ids=["utc", "zero", "named", "tzinfo"],
)
def test_another_spelling_of_an_offset_of_zero_is_the_same_time(zone):
    time = datetime.datetime(2026, 10, 9, 1, 23, 31, tzinfo=zone)
    assert run_id.compose(time, EXAMPLE_BITS) == EXAMPLE


def test_the_second_of_a_repeated_hour_does_not_change_the_digits():
    time = EXAMPLE_TIME.replace(fold=1)
    assert run_id.compose(time, EXAMPLE_BITS) == EXAMPLE


def test_compose_asks_no_clock_and_no_random_source(monkeypatch):
    monkeypatch.setattr(run_id, "_utc_now", fail)
    monkeypatch.setattr(run_id, "secrets", None)
    assert run_id.compose(EXAMPLE_TIME, EXAMPLE_BITS) == EXAMPLE
    assert run_id.compose(EXAMPLE_TIME, EXAMPLE_BITS) == EXAMPLE


# --- compose: order (ADR-0027 decision 4) ---


def test_ids_of_increasing_times_are_in_the_byte_order_of_the_times():
    times = [
        utc(1, 1, 1),
        utc(999, 12, 31, 23, 59, 59),
        utc(1000, 1, 1),
        utc(2026, 9, 30, 23, 59, 59),
        utc(2026, 10, 1),
        utc(2026, 10, 9, 1, 23, 31),
        utc(2026, 10, 9, 1, 23, 32),
        utc(2026, 10, 9, 10, 0, 0),
        utc(9999, 12, 31, 23, 59, 59),
    ]
    bits = [LAST, 2**63, 77, LAST - 1, 0, 2**40, 1, 2**64 - 2**60, 0]
    built = [run_id.compose(time, drawn) for time, drawn in zip(times, bits)]
    encoded = [name.encode("ascii") for name in built]
    assert sorted(encoded) == encoded
    assert sorted(encoded, reverse=True) != encoded


def test_ids_of_one_time_are_ordered_by_their_bits_alone():
    low = run_id.compose(EXAMPLE_TIME, 9)
    high = run_id.compose(EXAMPLE_TIME, 10)
    assert low[:17] == high[:17]
    assert low.encode("ascii") < high.encode("ascii")


# --- compose: what is refused ---


@pytest.mark.parametrize(
    "time",
    [
        None,
        "20261009t012331z",
        "2026-10-09T01:23:31Z",
        1791508411,
        1791508411.0,
        datetime.date(2026, 10, 9),
        datetime.time(1, 23, 31, tzinfo=UTC),
        (2026, 10, 9, 1, 23, 31),
        Moment(2026, 10, 9, 1, 23, 31, tzinfo=UTC),
    ],
    ids=lambda value: type(value).__name__,
)
def test_what_is_not_exactly_a_datetime_is_no_time(time):
    refused(TypeError, NO_TIME, time, EXAMPLE_BITS)


def test_a_time_without_a_zone_is_refused_and_not_read_as_utc():
    assert NAIVE.tzinfo is None
    refused(ValueError, NO_UTC, NAIVE, 0)
    refused(ValueError, NO_UTC, datetime.datetime(2026, 10, 9, tzinfo=Zone(None)), 0)


@pytest.mark.parametrize(
    "offset",
    [
        datetime.timedelta(hours=9),
        datetime.timedelta(hours=-8),
        datetime.timedelta(minutes=1),
        datetime.timedelta(seconds=1),
        datetime.timedelta(seconds=-1),
        datetime.timedelta(microseconds=1),
    ],
    ids=str,
)
def test_a_time_with_another_offset_is_refused_and_not_converted(offset):
    zone = datetime.timezone(offset)
    refused(ValueError, NO_UTC, datetime.datetime(2026, 10, 9, 1, tzinfo=zone), 0)
    refused(ValueError, NO_UTC, datetime.datetime(1, 1, 1, tzinfo=zone), 0)
    refused(ValueError, NO_UTC, datetime.datetime(9999, 12, 31, tzinfo=zone), 0)
    refused(ValueError, NO_UTC, datetime.datetime(2026, 10, 9, tzinfo=Zone(offset)), 0)


def test_what_a_zone_raises_is_passed_on():
    error = RuntimeError("no offset")
    time = datetime.datetime(2026, 10, 9, tzinfo=Zone(error))
    with pytest.raises(RuntimeError) as caught:
        run_id.compose(time, 0)
    assert caught.value is error


@pytest.mark.parametrize(
    "bits",
    [None, "9f3a6c1e0b7d4a52", b"\x01", 1.0, 0.0, True, False, [1], Whole(7)],
    ids=lambda value: type(value).__name__,
)
def test_what_is_not_exactly_an_int_is_no_bits(bits):
    refused(TypeError, NO_INT, EXAMPLE_TIME, bits)


@pytest.mark.parametrize("bits", [-1, -(2**64), 2**64, 2**64 + 987654321987, 2**200])
def test_bits_outside_the_range_are_refused_and_not_wrapped(bits):
    refused(ValueError, OUTSIDE, EXAMPLE_TIME, bits)


def test_the_time_is_judged_before_the_bits():
    refused(TypeError, NO_TIME, None, None)
    refused(ValueError, NO_UTC, NAIVE, None)
    refused(ValueError, NO_UTC, NAIVE, -1)
    refused(TypeError, NO_INT, EXAMPLE_TIME, -1.0)


def test_compose_takes_exactly_two_values():
    with pytest.raises(TypeError):
        run_id.compose()
    with pytest.raises(TypeError):
        run_id.compose(EXAMPLE_TIME)
    with pytest.raises(TypeError):
        run_id.compose(EXAMPLE_TIME, EXAMPLE_BITS, None)


# --- new ---


def test_new_writes_the_reading_of_the_clock_and_the_bits_of_the_source(monkeypatch):
    clock = Clock(EXAMPLE_TIME, utc(1, 1, 1), utc(9999, 12, 31, 23, 59, 59, 999999))
    bits = Bits(EXAMPLE_BITS, 0, LAST)
    monkeypatch.setattr(run_id, "_utc_now", clock)
    monkeypatch.setattr(run_id, "secrets", bits)
    assert run_id.new() == EXAMPLE
    assert (clock.calls, bits.widths) == (1, [64])
    assert run_id.new() == "00010101t000000z-0000000000000000"
    assert run_id.new() == "99991231t235959z-ffffffffffffffff"
    assert (clock.calls, bits.widths) == (3, [64, 64, 64])


def test_new_takes_no_argument():
    for arguments, named in (
        ((EXAMPLE_TIME,), {}),
        ((EXAMPLE_TIME, EXAMPLE_BITS), {}),
        ((), {"seed": 1}),
        ((), {"bits": 1}),
        ((), {"time": EXAMPLE_TIME}),
        ((), {"rng": random.Random(1)}),
    ):
        with pytest.raises(TypeError):
            run_id.new(*arguments, **named)


def test_new_uses_nothing_of_the_module_random(monkeypatch):
    for name in ("random", "getrandbits", "seed", "randrange", "randint", "randbytes"):
        monkeypatch.setattr(random, name, fail)
    monkeypatch.setattr(random, "Random", fail)
    assert SHAPE.fullmatch(run_id.new())


def test_new_does_not_follow_a_seed_of_the_module_random():
    drawn = set()
    for _ in range(4):
        random.seed(20261009)
        drawn.add(run_id.new()[17:])
    # four equal draws of a working source have probability 2**-192
    assert len(drawn) > 1


def test_new_unreplaced_has_the_form_and_a_time_between_two_readings():
    before = datetime.datetime.now(UTC)
    built = run_id.new()
    after = datetime.datetime.now(UTC)
    assert type(built) is str
    assert len(built) == 33
    assert SHAPE.fullmatch(built)
    assert layout.check_run_id(built) is built
    first, last = (run_id.compose(reading, 0)[:16] for reading in (before, after))
    assert first <= built[:16] <= last


def test_a_few_hundred_ids_are_distinct_which_is_a_smoke_check_and_no_proof():
    built = [run_id.new() for _ in range(300)]
    assert len(set(built)) == 300
    assert len({name[17:] for name in built}) == 300


def test_new_does_not_draw_again_for_a_time_it_has_used(monkeypatch):
    clock = Clock(EXAMPLE_TIME, EXAMPLE_TIME)
    bits = Bits(7, 7)
    monkeypatch.setattr(run_id, "_utc_now", clock)
    monkeypatch.setattr(run_id, "secrets", bits)
    assert run_id.new() == run_id.new() == "20261009t012331z-0000000000000007"
    assert (clock.calls, bits.widths) == (2, [64, 64])


@pytest.mark.parametrize(
    "error",
    [NotImplementedError("no random source"), OSError(5, "no random source")],
    ids=lambda error: type(error).__name__,
)
def test_an_error_of_the_random_source_is_passed_on(monkeypatch, error):
    bits = Bits(error)
    monkeypatch.setattr(run_id, "_utc_now", Clock(EXAMPLE_TIME))
    monkeypatch.setattr(run_id, "secrets", bits)
    with pytest.raises(type(error)) as caught:
        run_id.new()
    assert caught.value is error
    assert bits.widths == [64]


@pytest.mark.parametrize(
    ("reading", "drawn", "kind"),
    [
        (NAIVE, 0, ValueError),
        (None, 0, TypeError),
        (EXAMPLE_TIME, 2**64, ValueError),
        (EXAMPLE_TIME, 1.5, TypeError),
    ],
)
def test_new_writes_nothing_the_form_cannot_hold(monkeypatch, reading, drawn, kind):
    monkeypatch.setattr(run_id, "_utc_now", Clock(reading))
    monkeypatch.setattr(run_id, "secrets", Bits(drawn))
    with pytest.raises(kind):
        run_id.new()
