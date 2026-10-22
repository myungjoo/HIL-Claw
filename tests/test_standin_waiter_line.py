import sys

import pytest

from hilclaw import standin_waiter_line
from hilclaw.harness import timing
from hilclaw.standin_waiter_line import NONE_LINE, VALUE_KEYWORD, WaiterRead, read

REPORT = (
    b"resolution_ns 1\n"
    b"interval_ns 104200311\n"
    b"interval_ns 99870122\n"
    b"interval_ns 101004517\n"
    b"interval_ns 100310960\n"
    b"interval_ns 102118803\n"
    b"stop converged\n"
)


def value_line(value):
    return VALUE_KEYWORD + b" " + value + b"\n"


def test_spellings():
    assert VALUE_KEYWORD == b"waiter_max_rss_kib"
    assert NONE_LINE == b"waiter_max_rss none"
    for spelling in (VALUE_KEYWORD, NONE_LINE):
        assert spelling.isascii()
        assert b"\n" not in spelling
        head = spelling.split(b" ")[0]
        assert head not in (b"resolution_ns", b"interval_ns", b"stop")


def test_spellings_are_no_report_line():
    for line in (value_line(b"5"), NONE_LINE + b"\n"):
        assert timing.parse_report(REPORT + line) is None


def test_report_and_figure():
    result = read(REPORT + b"\n" + value_line(b"2048"))
    assert result == WaiterRead(REPORT, 2048 * 1024)
    assert type(result.report) is bytes
    assert type(result.memory_bytes) is int
    assert timing.parse_report(result.report) is not None


@pytest.mark.parametrize(
    "report",
    [
        b"",
        b"anything at all\nwith no form",
        b"stop converged",
        b"\x00\xff\r\n \t",
        b"\n\n",
    ],
)
def test_report_returned_byte_exact(report):
    assert read(report + b"\n" + value_line(b"7")) == WaiterRead(report, 7 * 1024)


def test_empty_report():
    assert read(b"\n" + value_line(b"1")) == WaiterRead(b"", 1024)


def test_none_line():
    assert read(REPORT + b"\n" + NONE_LINE + b"\n") == WaiterRead(REPORT, None)


@pytest.mark.parametrize("value", [b"0", b"-5", b"-1", b"-9223372036854775808"])
def test_value_below_one_gives_no_figure(value):
    assert read(REPORT + b"\n" + value_line(value)) == WaiterRead(REPORT, None)


def test_large_value_without_loss():
    big = 9223372036854775807
    result = read(REPORT + b"\n" + value_line(str(big).encode()))
    assert result.memory_bytes == big * 1024


@pytest.mark.parametrize(
    "value",
    [
        b"9223372036854775808",
        b"-9223372036854775809",
        b"9999999999999999999",
        b"10000000000000000000",
        b"1" * 5000,
    ],
)
def test_value_outside_a_long(value):
    assert read(b"\n" + value_line(value)) is None


def test_figure_only_from_last_line():
    forged = REPORT + value_line(b"1") + NONE_LINE + b"\n"
    result = read(forged + b"\n" + value_line(b"300"))
    assert result == WaiterRead(forged, 300 * 1024)
    assert timing.parse_report(result.report) is None


def test_earlier_waiter_line_without_figure_from_it():
    forged = REPORT + value_line(b"999999")
    result = read(forged + b"\n" + NONE_LINE + b"\n")
    assert result == WaiterRead(forged, None)


def test_bytes_left_without_lf_stay_in_report():
    leftover = REPORT + b"waiter_max_rss_kib 1"
    result = read(leftover + b"\n" + value_line(b"40"))
    assert result == WaiterRead(leftover, 40 * 1024)
    assert timing.parse_report(result.report) is None


@pytest.mark.parametrize(
    "stdout",
    [
        b"",
        b"\n",
        REPORT + b"\n" + VALUE_KEYWORD + b" 5",
        REPORT + b"\n" + NONE_LINE,
        REPORT + b"\n\n",
        REPORT + value_line(b"5") + b"\n",
        value_line(b"5"),
        NONE_LINE + b"\n",
        REPORT,
        b"\n" + b"stop converged\n",
    ],
)
def test_no_waiter_line_by_form(stdout):
    assert read(stdout) is None


@pytest.mark.parametrize(
    "line",
    [
        b"stop converged",
        b"interval_ns 5",
        b"waiter_max_rss 5",
        b"waiter_max_rss_kib none",
        b"waiter_max_rss_kib",
        b"waiter_max_rss_kib ",
        b"waiter_max_rss  none",
        b"waiter_max_rss none ",
        b"WAITER_MAX_RSS_KIB 5",
        b" waiter_max_rss_kib 5",
        b"waiter_max_rss_kib 05",
        b"waiter_max_rss_kib 00",
        b"waiter_max_rss_kib -0",
        b"waiter_max_rss_kib +5",
        b"waiter_max_rss_kib 5 ",
        b"waiter_max_rss_kib  5",
        b"waiter_max_rss_kib 5\r",
        b"waiter_max_rss_kib\t5",
        b"waiter_max_rss_kib 5\t",
        b"waiter_max_rss_kib 1_000",
        b"waiter_max_rss_kib 5.0",
        b"waiter_max_rss_kib 0x10",
        b"waiter_max_rss_kib --5",
        b"waiter_max_rss_kib 5 6",
        "waiter_max_rss_kib ٥".encode(),
        "waiter_max_rss_kib ５".encode(),
        b"waiter_max_rss_kib \x00",
        b"waiter_max_rss none\r",
    ],
)
def test_last_line_of_neither_spelling(line):
    assert read(REPORT + b"\n" + line + b"\n") is None


class BytesSub(bytes):
    pass


@pytest.mark.parametrize(
    "stdout",
    [
        bytearray(b"\n" + value_line(b"5")),
        memoryview(b"\n" + value_line(b"5")),
        (b"\n" + value_line(b"5")).decode(),
        BytesSub(b"\n" + value_line(b"5")),
        None,
        5,
    ],
)
def test_not_bytes_raises(stdout):
    with pytest.raises(TypeError, match="stdout: must be bytes"):
        read(stdout)


@pytest.mark.parametrize("platform", ["darwin", "win32", "cygwin", "linux"])
def test_platform_not_consulted(monkeypatch, platform):
    monkeypatch.setattr(sys, "platform", platform)
    assert read(b"\n" + value_line(b"3")) == WaiterRead(b"", 3 * 1024)


def test_uses_shared_unit_rule(monkeypatch):
    calls = []

    def figure(max_rss, platform):
        calls.append((max_rss, platform))
        return 11

    monkeypatch.setattr(standin_waiter_line.memory_ceiling, "figure", figure)
    assert read(b"\n" + value_line(b"-2")) == WaiterRead(b"", 11)
    assert calls == [(-2, "linux")]


def test_keeps_nothing_between_calls():
    first = read(b"a\n" + value_line(b"2"))
    assert read(b"\n" + NONE_LINE + b"\n") == WaiterRead(b"", None)
    assert read(b"a\n" + value_line(b"2")) == first


def test_result_fields():
    result = WaiterRead(b"r", 1)
    assert result._fields == ("report", "memory_bytes")
    assert result.report == b"r"
    assert result.memory_bytes == 1
