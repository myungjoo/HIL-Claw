import contextlib
import copy
import inspect
import json
from datetime import UTC, datetime

import pytest

from hilclaw import events, keys, layout
from hilclaw.events import (
    CorruptEventsError,
    InvalidEventError,
    Log,
    PositionBeyondLogError,
    UnsupportedVersionError,
    append,
    read,
    remove_torn_tail,
    validate,
)
from hilclaw.journal import fold

# Synthetic values only: no kind, payload member or time of a real run.
RUN = "run-a"
FILE = f"runs/{RUN}/events.ndjson"
KIND = "example_kind"
START = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
TIME = "2026-01-01T00:00:00Z"
ORDER = ["schema_version", "time", "kind", "round", "candidate", "attempt", "data"]

# The Example of ADR-0006, as written in the record.
EXAMPLE = (
    b'{"schema_version": 1, "time": "2026-01-01T00:00:00Z", "kind": "example_kind",'
    b' "data": {}}\n'
    b'{"schema_version": 1, "time": "2026-01-01T00:00:05Z", "kind": "example_kind",'
    b' "round": 0, "data": {"example_member": 1}}\n'
    b'{"schema_version": 1, "time": "2026-01-01T00:07:30Z",'
    b' "kind": "other_example_kind", "round": 3, "candidate": 2, "attempt": 1,'
    b' "data": {"example_member": "x"}}\n'
)


def ev(**changes):
    members = {"schema_version": 1, "time": TIME, "kind": KIND, "data": {}} | changes
    known = [name for name in ORDER if name in members]
    other = [name for name in members if name not in ORDER]
    return {name: members[name] for name in known + other}


def without(member, **changes):
    event = ev(**changes)
    del event[member]
    return event


def line(**changes):
    return json.dumps(ev(**changes)).encode() + b"\n"


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "data"
    path.mkdir()
    return path


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    now = [START]
    monkeypatch.setattr(events, "_utc_now", lambda: now[0])
    return now


def snapshot(tmp_path):
    return {
        path.relative_to(tmp_path).as_posix(): (
            (path.read_bytes(), path.stat().st_mtime_ns) if path.is_file() else None
        )
        for path in tmp_path.rglob("*")
    }


def place(root, content, relative=FILE):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def failing(error):
    def fail(*args, **kwargs):
        raise error

    return fail


class Proxy:
    def __init__(self, f):
        self.f = f

    def __getattr__(self, name):
        return getattr(self.f, name)


def opening(proxy):
    @contextlib.contextmanager
    def proxied(path, mode):
        with open(path, mode) as f:
            yield proxy(f)

    return proxied


# --- happy ---


def test_append_creates_exactly_the_file(root, tmp_path):
    result = append(root, RUN, KIND, {})

    assert sorted(snapshot(tmp_path)) == [
        "data",
        "data/runs",
        f"data/runs/{RUN}",
        f"data/{FILE}",
    ]
    content = (root / FILE).read_bytes()
    assert content == EXAMPLE.split(b"\n")[0] + b"\n"
    assert not content.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in content
    assert content.count(b"\n") == 1 and content.endswith(b"}\n")
    assert list(json.loads(content)) == ["schema_version", "time", "kind", "data"]
    assert result == ev()
    assert len(result["time"]) == 20
    assert read(root, RUN) == Log([result], 0)
    assert layout.run_file(root, RUN, "events.ndjson") == root / FILE


def test_the_time_is_the_reading_of_the_clock(root, clock):
    clock[0] = datetime(987, 6, 5, 4, 3, 2, 999999, tzinfo=UTC)

    assert append(root, RUN, KIND, {})["time"] == "0987-06-05T04:03:02Z"

    clock[0] = datetime(9999, 12, 31, 23, 59, 59, tzinfo=UTC)

    assert append(root, RUN, KIND, {})["time"] == "9999-12-31T23:59:59Z"


def test_the_clock_is_the_utc_clock_of_the_process(root, monkeypatch):
    monkeypatch.undo()
    before = datetime.now(UTC).replace(microsecond=0)

    written = append(root, RUN, KIND, {})["time"]

    stamp = datetime.strptime(written, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    assert before <= stamp <= datetime.now(UTC)
    assert validate(read(root, RUN).events[0]) is None


def test_the_caller_cannot_state_the_time(root):
    parameters = list(inspect.signature(append).parameters)

    assert parameters == [
        "data_root",
        "run_id",
        "kind",
        "data",
        "round",
        "candidate",
        "attempt",
    ]
    with pytest.raises(TypeError):
        append(root, RUN, KIND, {}, time=TIME)
    assert not (root / "runs").exists()


LEVELS = {
    "run": {},
    "round 0": {"round": 0},
    "round": {"round": 7},
    "candidate": {"round": 0, "candidate": 1},
    "attempt": {"round": 3, "candidate": 2, "attempt": 1},
    "largest": dict.fromkeys(("round", "candidate", "attempt"), keys.MAX_INTEGER),
}


@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("data", [{}, {"example_member": 1}])
def test_append_at_every_level(root, level, data):
    numbers = LEVELS[level]

    result = append(root, RUN, KIND, data, **numbers)

    assert result == ev(data=data, **numbers)
    assert list(result) == [name for name in ORDER if name in result]
    content = (root / FILE).read_bytes()
    assert content == line(data=data, **numbers)
    assert list(json.loads(content)) == list(result)
    for name in ("round", "candidate", "attempt"):
        assert (name in numbers) == (f'"{name}"'.encode() in content)
    assert b"null" not in content
    assert read(root, RUN).events == [result]


def test_the_writer_writes_the_lines_of_the_adr_example(root, clock):
    append(root, RUN, "example_kind", {})
    clock[0] = datetime(2026, 1, 1, 0, 0, 5, tzinfo=UTC)
    append(root, RUN, "example_kind", {"example_member": 1}, round=0)
    clock[0] = datetime(2026, 1, 1, 0, 7, 30, tzinfo=UTC)
    append(
        root,
        RUN,
        "other_example_kind",
        {"example_member": "x"},
        round=3,
        candidate=2,
        attempt=1,
    )

    assert (root / FILE).read_bytes() == EXAMPLE


def test_appends_are_read_back_in_their_order(root):
    written = []
    content = b""
    for number in range(3):
        written.append(append(root, RUN, KIND, {"example_member": number}))
        longer = (root / FILE).read_bytes()
        assert longer.startswith(content) and longer.count(b"\n") == number + 1
        content = longer

    assert read(root, RUN) == Log(written, 0)
    assert [event["data"]["example_member"] for event in written] == [0, 1, 2]


def test_validate_accepts_the_example_of_adr_0006():
    lines = EXAMPLE.split(b"\n")[:-1]
    assert len(lines) == 3

    for written in lines:
        assert validate(json.loads(written)) is None


@pytest.mark.parametrize(
    "event",
    [
        ev(kind="a_kind_nobody_listed"),
        ev(kind="a"),
        ev(kind="a" * 32),
        ev(kind="k9_"),
        ev(round=0),
        ev(round=keys.MAX_INTEGER, candidate=keys.MAX_INTEGER, attempt=1),
        ev(time="0001-01-01T00:00:00Z"),
        ev(time="9999-12-31T23:59:59Z"),
        ev(time="2024-02-29T12:00:00Z"),
        ev(data={"example_member": None, "nested": {"": [None, 1.5, {}]}}),
        dict(reversed(ev(round=1, candidate=1, attempt=1).items())),
    ],
)
def test_validate_accepts(event):
    before = copy.deepcopy(event)

    assert validate(event) is None
    assert event == before


def test_read_accepts_another_valid_form(root, tmp_path):
    first = b'{"data":{},"kind":"example_kind","time":"2026-01-01T00:00:00Z","schema_version":1}'
    second = (
        b' \t{ "round" : 4 ,\r "schema_version" : 1 , "kind" : "example_kind" ,'
        b' "data" : { "example_member" : [ 1 , "\xc3\xa9\xe2\x80\xa8\xc2\x85" ] } ,'
        b' "time" : "2026-01-01T00:00:00Z" } \t'
    )
    place(root, first + b"\n" + second + b"\r\n" + first + b"\r\n")
    before = snapshot(tmp_path)

    log = read(root, RUN)

    assert log == Log(
        [ev(), ev(round=4, data={"example_member": [1, "\u00e9\u2028\u0085"]}), ev()], 0
    )
    assert list(log.events[0]) == ["data", "kind", "time", "schema_version"]
    assert snapshot(tmp_path) == before


def test_a_number_beyond_the_float_range_is_read_as_an_infinity(root, tmp_path):
    place(root, line(data={"example_member": 0}).replace(b"0}", b"1e999}"))

    (event,) = read(root, RUN).events

    assert event["data"] == {"example_member": float("inf")}
    before = snapshot(tmp_path)
    with pytest.raises(InvalidEventError, match="data.example_member: must be "):
        append(root, RUN, KIND, event["data"])
    assert snapshot(tmp_path) == before


def test_the_file_is_split_at_the_line_feed_only(root):
    data = {"example_member": "a\rb\x0bc\x0cd\x1ce\x1df\x1eg\x85h\u2028i\u2029j"}
    raw = json.dumps(ev(data=data), ensure_ascii=False).encode()
    assert all(mark in raw for mark in (b"\xc2\x85", b"\xe2\x80\xa8", b"\xe2\x80\xa9"))
    place(root, raw + b"\n")

    append(root, RUN, KIND, data)

    assert read(root, RUN) == Log([ev(data=data), ev(data=data)], 0)
    assert (root / FILE).read_bytes().count(b"\n") == 2


# --- branch ---


@pytest.mark.parametrize("prepare", ["nothing", "runs", "run", "empty", "file as runs"])
def test_no_event_recorded(root, tmp_path, prepare):
    if prepare == "runs":
        (root / "runs").mkdir()
    elif prepare == "run":
        (root / "runs" / RUN).mkdir(parents=True)
    elif prepare == "empty":
        place(root, b"")
    elif prepare == "file as runs":
        place(root, b"synthetic", "runs")
    before = snapshot(tmp_path)

    assert read(root, RUN) == Log([], 0)
    assert read(root, RUN).events == [] and read(root, RUN).torn_tail == 0
    assert remove_torn_tail(root, RUN) == 0
    assert snapshot(tmp_path) == before


def test_a_file_in_the_place_of_the_run_directory(root, tmp_path):
    place(root, b"synthetic", f"runs/{RUN}")
    before = snapshot(tmp_path)

    assert read(root, RUN) == Log([], 0)
    assert remove_torn_tail(root, RUN) == 0
    with pytest.raises(OSError):
        append(root, RUN, KIND, {})
    assert snapshot(tmp_path) == before


def test_append_to_an_empty_file(root):
    place(root, b"")

    append(root, RUN, KIND, {})

    assert (root / FILE).read_bytes() == line()


COMPLETE = line() + line(round=2, data={"example_member": "x"})
TAILS = {
    "partial line": line(round=5)[:17],
    "one byte": b"{",
    "parses as an event": line(round=5)[:-1],
    "ends with a carriage return": line(round=5)[:-1] + b"\r",
    "white space": b" \t",
    "longer than one chunk": b'{"synthetic": "' + b"x" * (events._CHUNK + 1000),
    "two chunks exactly": b"x" * (2 * events._CHUNK),
}


@pytest.mark.parametrize("complete", [COMPLETE, b""], ids=["after lines", "no LF"])
@pytest.mark.parametrize("case", TAILS)
def test_a_torn_tail(root, tmp_path, complete, case):
    tail = TAILS[case]
    expected = [ev(), ev(round=2, data={"example_member": "x"})] if complete else []
    place(root, complete + tail)
    before = snapshot(tmp_path)

    assert read(root, RUN) == Log(expected, len(tail))
    assert snapshot(tmp_path) == before

    added = append(root, RUN, KIND, {}, round=9)

    assert (root / FILE).read_bytes() == complete + line(round=9)
    assert read(root, RUN) == Log([*expected, added], 0)

    place(root, complete + tail)

    assert remove_torn_tail(root, RUN) == len(tail)
    assert (root / FILE).read_bytes() == complete
    after = snapshot(tmp_path)
    assert remove_torn_tail(root, RUN) == 0
    assert snapshot(tmp_path) == after
    assert read(root, RUN) == Log(expected, 0)


@pytest.mark.parametrize("chunk", [1, 2, 3, 4, 5, 64])
@pytest.mark.parametrize("length", range(8))
def test_the_end_of_the_file_is_found_across_chunks(root, monkeypatch, chunk, length):
    monkeypatch.setattr(events, "_CHUNK", chunk)
    tail = b"x" * length
    for complete in (b"", b"\n", b"ab\n", b"ab\ncd\n", b"\n\n"):
        place(root, complete + tail)

        assert remove_torn_tail(root, RUN) == length
        assert (root / FILE).read_bytes() == complete

        place(root, complete + tail)
        append(root, RUN, KIND, {})

        assert (root / FILE).read_bytes() == complete + line()


def test_the_writer_reads_the_end_of_the_file_only(root, monkeypatch):
    place(root, line() * 5000 + b"torn")
    seen = []

    class Watched(Proxy):
        def read(self, size):
            seen.append(size)
            return self.f.read(size)

    with monkeypatch.context() as patch:
        patch.setattr(events, "open", opening(Watched), raising=False)
        append(root, RUN, KIND, {})
        assert remove_torn_tail(root, RUN) == 0

    assert seen == [events._CHUNK, events._CHUNK]
    assert (root / FILE).read_bytes() == line() * 5001


def test_a_line_is_written_by_one_write_that_ends_with_the_line_feed(root, monkeypatch):
    place(root, line() + b"torn")
    written = []

    class Watched(Proxy):
        def write(self, content):
            written.append(content)
            return self.f.write(content)

    with monkeypatch.context() as patch:
        patch.setattr(events, "open", opening(Watched), raising=False)
        append(root, RUN, KIND, {}, round=1)

    assert written == [line(round=1)]
    assert (root / FILE).read_bytes() == line() + line(round=1)


def test_the_writer_does_not_look_for_damage(root):
    damaged = b"not json\n" + line(schema_version=2) + b"\xff\n"
    place(root, damaged)

    append(root, RUN, KIND, {})
    assert remove_torn_tail(root, RUN) == 0

    assert (root / FILE).read_bytes() == damaged + line()
    with pytest.raises(CorruptEventsError) as excinfo:
        read(root, RUN)
    assert str(excinfo.value).startswith(f"{FILE}: line 1: is damaged")


def test_data_is_written_as_given(root):
    data = {
        "z": {"nested": {"deeper": [1, [2, [3, {}]], {"a": None}]}},
        "a": [1.5, -0.0, 1e300, True, False, None, "", 2**70, -3],
        "example_member": '\u00e9\u2028\U0001f600\ud800\x00"\\',
        "": {},
    }
    before = copy.deepcopy(data)

    result = append(root, RUN, KIND, data, round=1)

    assert data == before
    assert result["data"] == data and list(result["data"]) == [
        "z",
        "a",
        "example_member",
        "",
    ]
    content = (root / FILE).read_bytes()
    assert content.isascii() and content.count(b"\n") == 1
    (stored,) = read(root, RUN).events
    assert stored == result
    assert list(stored["data"]) == list(data)
    assert [type(value) for value in stored["data"]["a"]] == [
        float,
        float,
        float,
        bool,
        bool,
        type(None),
        str,
        int,
        int,
    ]


def test_the_returned_event_is_independent_of_the_argument(root):
    data = {"example_member": [1, {"inner": 2}]}

    result = append(root, RUN, KIND, data)
    data["example_member"][1]["inner"] = 3
    data["later"] = True

    assert result == ev(data={"example_member": [1, {"inner": 2}]})
    assert read(root, RUN).events == [result]


def test_data_root_as_str(root):
    first = append(str(root), RUN, KIND, {})
    place(root, (root / FILE).read_bytes() + b"torn")

    assert read(str(root), RUN) == Log([first], 4)
    assert remove_torn_tail(str(root), RUN) == 4
    assert read(str(root), RUN) == read(root, RUN) == Log([first], 0)


def test_the_time_need_not_increase(root, clock):
    later = append(root, RUN, KIND, {})
    clock[0] = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)
    earlier = append(root, RUN, KIND, {})

    assert earlier["time"] == "2025-12-31T23:59:59Z" < later["time"]
    assert read(root, RUN).events == [later, earlier]


def test_two_runs_have_two_files(root):
    append(root, RUN, KIND, {}, round=1)
    append(root, "run-b", KIND, {}, round=2)

    assert read(root, RUN).events == [ev(round=1)]
    assert read(root, "run-b").events == [ev(round=2)]


def test_error_types():
    assert issubclass(InvalidEventError, ValueError)
    for error in (CorruptEventsError, UnsupportedVersionError):
        assert not issubclass(error, (ValueError, LookupError, OSError))
    assert not issubclass(UnsupportedVersionError, CorruptEventsError)
    assert not issubclass(CorruptEventsError, UnsupportedVersionError)
    assert events.SCHEMA_VERSION == 1
    assert Log._fields == ("events", "torn_tail")


# --- negative: validate ---

BAD_TIME = {
    "second 60": "2026-01-01T00:00:60Z",
    "minute 60": "2026-01-01T00:60:00Z",
    "hour 24": "2026-01-01T24:00:00Z",
    "february 30": "2026-02-30T00:00:00Z",
    "february 29 of a common year": "2026-02-29T00:00:00Z",
    "month 13": "2026-13-01T00:00:00Z",
    "month 0": "2026-00-01T00:00:00Z",
    "day 0": "2026-01-00T00:00:00Z",
    "year 0": "0000-01-01T00:00:00Z",
    "lower case t": "2026-01-01t00:00:00Z",
    "lower case z": "2026-01-01T00:00:00z",
    "space": "2026-01-01 00:00:00Z",
    "fraction": "2026-01-01T00:00:00.5Z",
    "offset": "2026-01-01T00:00:00+00:00",
    "no zone": "2026-01-01T00:00:00",
    "five digit year": "12026-01-01T00:00:00Z",
    "short year": "026-01-01T00:00:00Z",
    "no padding": "2026-1-1T0:0:0Z",
    "non-ASCII digits": "２０２６-01-01T00:00:00Z",
    "arabic-indic digit": "2026-01-0\u0661T00:00:00Z",
    "trailing newline": "2026-01-01T00:00:00Z\n",
    "leading space": " 2026-01-01T00:00:00Z",
    "date only": "2026-01-01",
    "empty": "",
    "epoch seconds": 1767225600,
    "float": 1767225600.0,
    "bytes": TIME.encode(),
    "none": None,
}
BAD_KIND = {
    "empty": "",
    "upper case": "Example_kind",
    "33 characters": "a" * 33,
    "hyphen": "example-kind",
    "leading digit": "1kind",
    "leading underscore": "_kind",
    "dot": "example.kind",
    "trailing newline": "example_kind\n",
    "integer": 1,
    "list": ["example_kind"],
    "none": None,
}
BAD_INTEGER = {
    "negative": -1,
    "2^53": 2**53,
    "float": 1.0,
    "true": True,
    "false": False,
    "string": "1",
    "none": None,
}
BAD_FROM_ONE = BAD_INTEGER | {"zero": 0}
BAD_DATA = {
    "none": None,
    "list": [],
    "string": "{}",
    "integer": 0,
    "tuple of pairs": (("example_member", 1),),
}
BAD_MEMBERS = {
    "time": BAD_TIME,
    "kind": BAD_KIND,
    "round": BAD_INTEGER,
    "candidate": BAD_FROM_ONE,
    "attempt": BAD_FROM_ONE,
    "data": BAD_DATA,
}
ALL = {"round": 3, "candidate": 2, "attempt": 1}
INVALID_EVENTS = {
    "a list": ([], "event: must be an object"),
    "a string": ("synthetic", "event: must be an object"),
    "a number": (1, "event: must be an object"),
    "none": (None, "event: must be an object"),
    "a list of pairs": (list(ev().items()), "event: must be an object"),
    "empty": ({}, "schema_version: must be an int"),
    "no schema_version": (without("schema_version"), "schema_version: must be an int"),
    "schema_version string": (ev(schema_version="1"), "schema_version: must be an int"),
    "schema_version float": (ev(schema_version=1.0), "schema_version: must be an int"),
    "schema_version true": (ev(schema_version=True), "schema_version: must be an int"),
    "schema_version none": (ev(schema_version=None), "schema_version: must be an int"),
    "schema_version negative": (
        ev(schema_version=-1),
        "schema_version: must be an int",
    ),
    "schema_version 2^53": (ev(schema_version=2**53), "schema_version: must be an int"),
    "schema_version list": (ev(schema_version=[1]), "schema_version: must be an int"),
    "member name not a str": (
        ev() | {1: 1},
        "event: must be without the unknown member, got int 1",
    ),
    "round an integer too long": (ev(round=10**5000), "round: must be an int"),
    "kind holding an integer too long": (ev(kind=[10**5000]), "kind: must be a str"),
    "member name an integer too long": (
        ev() | {10**5000: 1},
        "event: must be without the unknown member, got ",
    ),
    "candidate without round": (
        ev(candidate=1),
        "candidate: is given only together with round",
    ),
    "attempt without candidate": (
        ev(round=0, attempt=1),
        "attempt: is given only together with candidate",
    ),
    "attempt alone": (ev(attempt=1), "attempt: is given only together with candidate"),
    "candidate and attempt without round": (
        ev(candidate=1, attempt=1),
        "candidate: is given only together with round",
    ),
}
for _member in ("time", "kind", "data"):
    INVALID_EVENTS[f"no {_member}"] = (
        without(_member, **ALL),
        f"event: lacks the member {_member}",
    )
for _member in ("run_id", "seq", "id", "type", "ts", "Kind", "payload", ""):
    INVALID_EVENTS[f"unknown member {_member!r}"] = (
        ev(**{_member: "synthetic"}),
        f"event: must be without the unknown member, got str '{_member}'",
    )
for _member, _values in BAD_MEMBERS.items():
    for _case, _value in _values.items():
        INVALID_EVENTS[f"{_member} {_case}"] = (
            ev(**(ALL | {_member: _value})),
            f"{_member}: must be ",
        )


@pytest.mark.parametrize("case", INVALID_EVENTS)
def test_validate_rejects(case):
    event, message = INVALID_EVENTS[case]
    before = copy.deepcopy(event)

    with pytest.raises(InvalidEventError) as excinfo:
        validate(event)

    assert str(excinfo.value).startswith(message)
    assert event == before


UNSUPPORTED = {
    "version 0": ev(schema_version=0),
    "version 2": ev(schema_version=2),
    "largest integer": ev(schema_version=keys.MAX_INTEGER),
    "with an invalid member": ev(schema_version=2, kind="Not A Name", time=None),
    "with an unknown member": ev(schema_version=2, seq=1),
    "with a member missing": without("data", schema_version=2),
    "alone": {"schema_version": 3},
    "attempt without candidate": ev(schema_version=0, attempt=0),
}


@pytest.mark.parametrize("case", UNSUPPORTED)
def test_validate_reports_an_unsupported_version(case):
    event = UNSUPPORTED[case]

    with pytest.raises(UnsupportedVersionError) as excinfo:
        validate(event)

    version = event["schema_version"]
    assert str(excinfo.value) == f"schema_version: {version} is not supported"


def test_an_error_message_shows_a_bounded_value():
    with pytest.raises(InvalidEventError) as excinfo:
        validate(ev(kind="x" * 100_000))

    assert len(str(excinfo.value)) < 200
    assert "got str 'xxx" in str(excinfo.value)

    with pytest.raises(InvalidEventError) as excinfo:
        validate(ev(**{"y" * 100_000: 1}))

    assert len(str(excinfo.value)) < 200


def test_a_value_that_cannot_be_shown(monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(events.reprlib, "repr", failing(ValueError("synthetic")))
        with pytest.raises(InvalidEventError) as excinfo:
            validate(ev(round="1"))

    rule = f"round: must be an int from 0 to {keys.MAX_INTEGER}"
    assert str(excinfo.value) == f"{rule}, got str too long to show"


# --- negative: append ---

LOOP = {}
LOOP["example_member"] = LOOP
DEEP = []
for _ in range(100_000):
    DEEP = [DEEP]
NOT_JSON = {
    "nan": ({"example_member": float("nan")}, "data.example_member: must be "),
    "infinity": ({"example_member": [float("inf")]}, "data.example_member[0]: must "),
    "negative infinity": ({"a": {"b": -float("inf")}}, "data.a.b: must be "),
    "set": ({"example_member": {1}}, "data.example_member: must be "),
    "bytes": ({"example_member": b"x"}, "data.example_member: must be "),
    "tuple": ({"example_member": (1, 2)}, "data.example_member: must be "),
    "object": ({"example_member": object()}, "data.example_member: must be "),
    "datetime": ({"example_member": [0, START]}, "data.example_member[1]: must be "),
    "integer member name": ({1: "x"}, "data: member name: must be a str, got int 1"),
    "none member name": ({None: "x"}, "data: member name: must be a str, got NoneT"),
    "nested member name": ({"a": [{2.5: 1}]}, "data.a[0]: member name: must be a str"),
    "contains itself": (LOOP, "data: is not strict JSON: RecursionError"),
    "nested too deeply": ({"example_member": DEEP}, "data: is not strict JSON: Recur"),
    "integer too long": ({"example_member": 10**5000}, "data: is not strict JSON: Val"),
    "integer member name too long": ({10**5000: 1}, "data: member name: must be a "),
    "below a long member name": ({"y" * 100_000: {1}}, "data.yyyyyyyy"),
    "a long member name below a long one": (
        {"y" * 100_000: {"z" * 100_000: 1, 2: 1}},
        "data.yyyyyyyy",
    ),
}
INVALID_APPENDS = {
    case: ({"data": data}, message) for case, (data, message) in NOT_JSON.items()
}
for _case, _value in BAD_KIND.items():
    INVALID_APPENDS[f"kind {_case}"] = ({"kind": _value}, "kind: must be ")
for _case, _value in BAD_DATA.items():
    INVALID_APPENDS[f"data {_case}"] = ({"data": _value}, "data: must be an object")
for _member, _values in (
    ("round", BAD_INTEGER),
    ("candidate", BAD_FROM_ONE),
    ("attempt", BAD_FROM_ONE),
):
    for _case, _value in _values.items():
        if _value is not None:
            INVALID_APPENDS[f"{_member} {_case}"] = (
                ALL | {_member: _value},
                f"{_member}: must be ",
            )
INVALID_APPENDS["round an integer too long"] = ({"round": 10**5000}, "round: must be ")
INVALID_APPENDS["candidate without round"] = (
    {"candidate": 1},
    "candidate: is given only together with round",
)
INVALID_APPENDS["attempt without candidate"] = (
    {"round": 0, "attempt": 1},
    "attempt: is given only together with candidate",
)


@pytest.mark.parametrize("existing", [False, True], ids=["fresh", "existing"])
@pytest.mark.parametrize("case", INVALID_APPENDS)
def test_append_rejects_an_invalid_argument(root, tmp_path, case, existing):
    changes, message = INVALID_APPENDS[case]
    arguments = {"kind": KIND, "data": {}} | changes
    if existing:
        place(root, line() + b"torn")
    before = snapshot(tmp_path)

    with pytest.raises(InvalidEventError) as excinfo:
        append(root, RUN, **arguments)

    assert str(excinfo.value).startswith(message)
    assert len(str(excinfo.value)) < 400
    assert snapshot(tmp_path) == before


def test_a_long_place_keeps_what_the_message_is_about(root, tmp_path):
    before = snapshot(tmp_path)

    with pytest.raises(InvalidEventError) as excinfo:
        append(root, RUN, KIND, {"y" * 100_000: {"z": 1, 2: 1}})

    message = str(excinfo.value)
    assert message.startswith("data.yyyy")
    assert message.endswith("yyyy: member name: must be a str, got int 2")
    assert len(message) < 300
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "run_id", ["..", ".", "a/b", "a\\b", "Run-a", "", "-a", "a" * 65, None, 1]
)
def test_an_invalid_run_id(root, tmp_path, run_id):
    before = snapshot(tmp_path)

    with pytest.raises(layout.InvalidPathValueError, match="run_id"):
        append(root, run_id, KIND, {})
    with pytest.raises(layout.InvalidPathValueError, match="run_id"):
        read(root, run_id)
    with pytest.raises(layout.InvalidPathValueError, match="run_id"):
        remove_torn_tail(root, run_id)
    with pytest.raises(layout.InvalidPathValueError, match="run_id"):
        append(tmp_path / "missing", run_id, "Not A Name", None)

    assert snapshot(tmp_path) == before


CALLS = {
    "append": lambda root: append(root, RUN, KIND, {}),
    "read": lambda root: read(root, RUN),
    "remove_torn_tail": lambda root: remove_torn_tail(root, RUN),
}


@pytest.mark.parametrize("call", CALLS)
def test_data_root_must_be_an_existing_directory(tmp_path, call):
    occupied = tmp_path / "occupied"
    occupied.write_bytes(b"synthetic")
    before = snapshot(tmp_path)

    with pytest.raises(FileNotFoundError, match="data root is not an existing"):
        CALLS[call](tmp_path / "missing")
    with pytest.raises(NotADirectoryError, match="data root is not an existing"):
        CALLS[call](occupied)
    with pytest.raises(FileNotFoundError):
        CALLS[call](str(tmp_path / "missing"))

    assert snapshot(tmp_path) == before


def test_arguments_are_checked_before_the_data_root(tmp_path):
    with pytest.raises(InvalidEventError, match="kind: must be "):
        append(tmp_path / "missing", RUN, "Not A Name", {})
    with pytest.raises(InvalidEventError, match="data.example_member: must be "):
        append(tmp_path / "missing", RUN, KIND, {"example_member": {1}})

    assert snapshot(tmp_path) == {}


@pytest.mark.parametrize("call", CALLS)
def test_a_directory_in_the_place_of_the_file(root, tmp_path, call):
    (root / FILE).mkdir(parents=True)
    before = snapshot(tmp_path)

    with pytest.raises(CorruptEventsError) as excinfo:
        CALLS[call](root)

    assert str(excinfo.value) == f"{FILE}: is not a regular file"
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("call", CALLS)
@pytest.mark.parametrize("target", ["a file", "nothing"])
def test_a_symbolic_link_is_not_followed(root, tmp_path, call, target):
    elsewhere = tmp_path / "elsewhere.ndjson"
    if target == "a file":
        elsewhere.write_bytes(line() + b"torn")
    (root / FILE).parent.mkdir(parents=True)
    try:
        (root / FILE).symlink_to(elsewhere)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links cannot be created here")

    with pytest.raises(CorruptEventsError, match="is not a regular file"):
        CALLS[call](root)

    if target == "a file":
        assert elsewhere.read_bytes() == line() + b"torn"
    else:
        assert not elsewhere.exists()


# --- negative: read ---

DAMAGED = {
    "invalid UTF-8": b'{"schema_version": 1, "kind": "\xff"}',
    "UTF-16": json.dumps(ev()).encode("utf-16"),
    "UTF-16 without a mark": json.dumps(ev()).encode("utf-16-le"),
    "invalid JSON": b'{"schema_version": 1,',
    "single quotes": json.dumps(ev()).encode().replace(b'"', b"'"),
    "trailing comma": line()[:-2] + b",}",
    "a comment": line()[:-1] + b" // synthetic",
    "an array": b"[" + line()[:-1] + b"]",
    "an empty array": b"[]",
    "a string": b'"synthetic"',
    "a number": b"1",
    "null": b"null",
    "true": b"true",
    "two JSON texts": line()[:-1] + b" " + line()[:-1],
    "two JSON texts without a gap": line()[:-1] * 2,
    "a blank line": b"",
    "a carriage return only": b"\r",
    "white space only": b" \t ",
    "a vertical tab": line()[:-1] + b"\x0b",
    "a form feed before": b"\x0c" + line()[:-1],
    "a no-break space": line()[:-1] + b"\xc2\xa0",
    "a NUL": line()[:-1] + b"\x00",
    "a raw control character in a string": line(data={"example_member": "a\tb"})
    .replace(b"\\t", b"\t")
    .strip(b"\n"),
    "a repeated member name": line()[:-2] + b', "kind": "example_kind"}',
    "a repeated member name with the same value": line()[:-2] + b', "data": {}}',
    "a repeated member name inside data": line(data={"a": 1})[:-3] + b', "a": 1}}',
    "a repeated member name deep inside data": (
        b'{"schema_version": 1, "time": "2026-01-01T00:00:00Z", "kind": "example_kind",'
        b' "data": {"example_member": [0, {"inner": {"x": 1, "y": 2, "x": 3}}]}}'
    ),
    "a repeated schema_version of another version": (
        b'{"schema_version": 2, "schema_version": 2}'
    ),
    "NaN": b'{"schema_version": 1, "time": "2026-01-01T00:00:00Z", "kind": "example_kind",'
    b' "data": {"example_member": NaN}}',
    "Infinity": line(data={"example_member": 0})
    .strip(b"\n")
    .replace(b"0}", b"Infinity}"),
    "-Infinity": line(data={"example_member": 0})
    .strip(b"\n")
    .replace(b"0}", b"-Infinity}"),
    "a byte order mark": b"\xef\xbb\xbf" + line()[:-1],
    "nested too deeply": line(data={"example_member": 0})
    .strip(b"\n")
    .replace(b"0}", b"[" * 200_000 + b"]" * 200_000 + b"}"),
    "an integer too long": line(data={"example_member": 0})
    .strip(b"\n")
    .replace(b"0}", b"1" * 5000 + b"}"),
    "an integer too long in a line of another version": (
        b'{"schema_version": 2, "data": ' + b"1" * 5000 + b"}"
    ),
    "no schema_version": json.dumps(without("schema_version")).encode(),
    "schema_version a string": line(schema_version="1")[:-1],
    "schema_version a float": line()[:-1].replace(b'_version": 1', b'_version": 1.0'),
    "schema_version an exponent": line()[:-1].replace(
        b'_version": 1', b'_version": 1e0'
    ),
    "schema_version negative": line(schema_version=-1)[:-1],
    "schema_version null": line(schema_version=None)[:-1],
    "schema_version true": line(schema_version=True)[:-1],
    "schema_version 2^53": line(schema_version=2**53)[:-1],
    "an unknown member": line(seq=1)[:-1],
    "a run_id member": line(run_id=RUN)[:-1],
    "no data": json.dumps(without("data")).encode(),
    "no time": json.dumps(without("time")).encode(),
    "no kind": json.dumps(without("kind")).encode(),
    "an empty object": b"{}",
    "data null": line(data=None)[:-1],
    "data an array": line(data=[])[:-1],
    "round null": line(round=None)[:-1],
    "round a float": line()[:-1].replace(b'"data"', b'"round": 1.0, "data"'),
    "round negative": line(round=-1)[:-1],
    "candidate 0": line(round=0, candidate=0)[:-1],
    "attempt 0": line(round=0, candidate=1, attempt=0)[:-1],
    "candidate without round": line(candidate=1)[:-1],
    "attempt without candidate": line(round=1, attempt=1)[:-1],
    "kind not a name": line(kind="Example Kind")[:-1],
    "time with second 60": line(time="2026-01-01T00:00:60Z")[:-1],
    "time of a date that does not exist": line(time="2026-02-30T00:00:00Z")[:-1],
    "time with an offset": line(time="2026-01-01T00:00:00+00:00")[:-1],
}
POSITIONS = {
    "first": (b"", line(round=1) + line(round=2)),
    "middle": (line(round=1), line(round=2)),
    "last": (line(round=1) + line(round=2), b""),
    "last before a torn tail": (line(round=1) + line(round=2), b'{"torn'),
    "only": (b"", b""),
}


@pytest.mark.parametrize("position", POSITIONS)
@pytest.mark.parametrize("case", DAMAGED)
def test_read_reports_a_damaged_line(root, tmp_path, case, position):
    assert b"\n" not in DAMAGED[case]
    before_it, after_it = POSITIONS[position]
    place(root, before_it + DAMAGED[case] + b"\n" + after_it)
    before = snapshot(tmp_path)

    with pytest.raises(CorruptEventsError) as excinfo:
        read(root, RUN)

    number = before_it.count(b"\n") + 1
    assert str(excinfo.value).startswith(f"{FILE}: line {number}: is damaged: ")
    assert len(str(excinfo.value)) < 400
    assert not isinstance(excinfo.value, (ValueError, UnsupportedVersionError))
    assert snapshot(tmp_path) == before


OTHER_VERSIONS = {
    "version 2": line(schema_version=2)[:-1],
    "version 0": line(schema_version=0)[:-1],
    "the largest integer": line(schema_version=keys.MAX_INTEGER)[:-1],
    "with members of no version 1 line": b'{"seq": 4, "schema_version": 2, "kind": 7}',
    "alone": b'{"schema_version": 2}',
    "with a carriage return": b' {"schema_version" : 3 } \r',
}


@pytest.mark.parametrize("position", POSITIONS)
@pytest.mark.parametrize("case", OTHER_VERSIONS)
def test_read_reports_an_unsupported_version(root, tmp_path, case, position):
    before_it, after_it = POSITIONS[position]
    place(root, before_it + OTHER_VERSIONS[case] + b"\n" + after_it)
    before = snapshot(tmp_path)

    with pytest.raises(UnsupportedVersionError) as excinfo:
        read(root, RUN)

    number = before_it.count(b"\n") + 1
    version = json.loads(OTHER_VERSIONS[case])["schema_version"]
    expected = f"{FILE}: line {number}: schema_version: {version} is not supported"
    assert str(excinfo.value) == expected
    assert snapshot(tmp_path) == before


def test_read_reports_the_first_line_it_cannot_use(root):
    place(root, line() + line(schema_version=2) + b"not json\n")
    with pytest.raises(UnsupportedVersionError, match="line 2: "):
        read(root, RUN)

    place(root, line() + b"not json\n" + line(schema_version=2))
    with pytest.raises(CorruptEventsError, match="line 2: "):
        read(root, RUN)


def test_an_unsupported_version_in_a_torn_tail_is_not_reported(root):
    place(root, line() + line(schema_version=2)[:-1])

    assert read(root, RUN) == Log([ev()], len(line(schema_version=2)) - 1)


# --- negative: a failing write ---


class TornFile(Proxy):
    def write(self, content):
        self.f.write(content[: len(content) // 2])
        raise OSError("synthetic failure")


@pytest.mark.parametrize("existing", [b"", COMPLETE, COMPLETE + b"torn"])
def test_a_write_that_fails_midway_leaves_a_torn_tail(root, monkeypatch, existing):
    if existing:
        place(root, existing)
    with monkeypatch.context() as patch:
        patch.setattr(events, "open", opening(TornFile), raising=False)
        with pytest.raises(OSError, match="synthetic failure"):
            append(root, RUN, KIND, {}, round=9)

    complete = COMPLETE if existing else b""
    half = line(round=9)[: len(line(round=9)) // 2]
    assert (root / FILE).read_bytes() == complete + half
    log = read(root, RUN)
    assert len(log.events) == complete.count(b"\n") and log.torn_tail == len(half)

    retried = append(root, RUN, KIND, {}, round=9)

    assert (root / FILE).read_bytes() == complete + line(round=9)
    assert read(root, RUN).events[-1] == retried


@pytest.mark.parametrize("error", [OSError("synthetic failure"), KeyboardInterrupt()])
@pytest.mark.parametrize("existing", [b"", COMPLETE + b"torn"])
def test_a_failing_fsync_passes_through(root, monkeypatch, existing, error):
    if existing:
        place(root, existing)
    with monkeypatch.context() as patch:
        patch.setattr(events.os, "fsync", failing(error))
        with pytest.raises(type(error)):
            append(root, RUN, KIND, {}, round=9)

    complete = COMPLETE if existing else b""
    content = (root / FILE).read_bytes()
    assert content.startswith(complete)
    assert line(round=9).startswith(content[len(complete) :])


def test_a_file_that_cannot_be_opened(root, tmp_path, monkeypatch):
    place(root, COMPLETE + b"torn")
    before = snapshot(tmp_path)
    refused = failing(PermissionError("synthetic"))

    with monkeypatch.context() as patch:
        patch.setattr(events, "open", refused, raising=False)
        with pytest.raises(PermissionError, match="synthetic"):
            append(root, RUN, KIND, {})
        with pytest.raises(PermissionError, match="synthetic"):
            remove_torn_tail(root, RUN)

    assert snapshot(tmp_path) == before


def test_a_failing_fsync_of_the_tail_removal_passes_through(root, monkeypatch):
    place(root, COMPLETE + b"torn")
    with monkeypatch.context() as patch:
        patch.setattr(events.os, "fsync", failing(OSError("synthetic failure")))
        with pytest.raises(OSError, match="synthetic failure"):
            remove_torn_tail(root, RUN)

    assert (root / FILE).read_bytes().startswith(COMPLETE)
    remove_torn_tail(root, RUN)
    assert (root / FILE).read_bytes() == COMPLETE


# --- read from a position (ADR-0011 decision 6, ADR-0012 decision 5) ---

# The two lines of the Example of ADR-0011 and one more start line (Example of ADR-0012).
STEPS = (
    b'{"schema_version": 1, "time": "2026-01-01T00:00:00Z", "kind": "step_started",'
    b' "round": 3, "candidate": 2, "attempt": 1,'
    b' "data": {"step": "example_step", "execution": 1}}\n'
    b'{"schema_version": 1, "time": "2026-01-01T00:04:10Z", "kind": "step_ended",'
    b' "round": 3, "candidate": 2, "attempt": 1,'
    b' "data": {"step": "example_step", "execution": 1, "spend": {"example_axis": 7},'
    b' "result": {"example_member": 1}}}\n'
    b'{"schema_version": 1, "time": "2026-01-01T00:05:00Z", "kind": "step_started",'
    b' "round": 3, "candidate": 1, "attempt": 1,'
    b' "data": {"step": "example_step", "execution": 1}}\n'
)


def beyond(position, count, file=FILE):
    end = f"the end of the log, complete lines: {count}"
    return f"{file}: position {position} is beyond {end}"


def test_the_position_is_the_third_parameter_and_defaults_to_0():
    parameters = inspect.signature(read).parameters

    assert list(parameters) == ["data_root", "run_id", "position"]
    assert parameters["position"].default == 0
    assert issubclass(PositionBeyondLogError, CorruptEventsError)
    assert not issubclass(PositionBeyondLogError, ValueError)


@pytest.mark.parametrize("position", [0, 1, 2, 3])
def test_read_returns_the_lines_after_the_position(root, tmp_path, position):
    place(root, EXAMPLE)
    before = snapshot(tmp_path)
    whole = read(root, RUN)
    assert len(whole.events) == 3

    assert read(root, RUN, position) == Log(whole.events[position:], 0)
    assert read(root, RUN, position=position) == read(root, RUN, position)
    assert read(str(root), RUN, position) == read(root, RUN, position)
    assert len(read(root, RUN, position).events) == 3 - position
    assert snapshot(tmp_path) == before


def test_position_0_is_the_default(root):
    place(root, EXAMPLE + b'{"torn')

    assert read(root, RUN, 0) == read(root, RUN) == read(root, RUN, position=0)
    assert read(root, RUN, 0).torn_tail == 6


def test_appended_lines_are_read_back_from_a_position(root):
    written = [append(root, RUN, KIND, {"example_member": n}) for n in range(4)]

    for position in range(5):
        assert read(root, RUN, position) == Log(written[position:], 0)

    position = len(read(root, RUN).events)
    later = append(root, RUN, KIND, {}, round=1)

    assert read(root, RUN, position) == Log([later], 0)


@pytest.mark.parametrize("position", [0, 1, 2, 3])
def test_a_fold_of_the_tail_from_the_view_of_the_prefix_is_the_fold_of_the_log(
    root, position
):
    place(root, STEPS)
    whole = read(root, RUN).events
    stored = fold(whole[:position])[0]

    replayed = fold(read(root, RUN, position).events, stored)[0]

    assert stored.position == position
    assert replayed == fold(whole)[0]
    assert replayed.position == 3 and replayed.totals == {"example_axis": 7}
    assert len(replayed.open_steps) == 1


PASSED_OVER = {
    "a damaged line": b"not json",
    "a blank line": b"",
    "white space only": b" \t ",
    "not UTF-8": b'{"schema_version": 1, "kind": "\xff"}',
    "another version": line(schema_version=2)[:-1],
    "a line that parses": line(round=8)[:-1],
}


@pytest.mark.parametrize("end", [b"\n", b"\r\n"])
@pytest.mark.parametrize("case", PASSED_OVER)
def test_lines_before_the_position_are_not_interpreted(root, tmp_path, case, end):
    passed = PASSED_OVER[case] + end
    place(root, passed + line(round=1) + passed + line(round=2))
    before = snapshot(tmp_path)
    unusable = (CorruptEventsError, UnsupportedVersionError)

    assert read(root, RUN, 3) == Log([ev(round=2)], 0)
    assert read(root, RUN, 4) == Log([], 0)
    if case != "a line that parses":
        with pytest.raises(unusable, match="line 1: "):
            read(root, RUN)
        with pytest.raises(unusable, match="line 3: "):
            read(root, RUN, 1)
    assert snapshot(tmp_path) == before


def test_a_carriage_return_before_a_line_feed_changes_no_count(root):
    place(root, EXAMPLE.replace(b"\n", b"\r\n"))
    whole = read(root, RUN).events
    assert len(whole) == 3

    for position in range(4):
        assert read(root, RUN, position) == Log(whole[position:], 0)
    with pytest.raises(PositionBeyondLogError):
        read(root, RUN, 4)


@pytest.mark.parametrize("tail", [b'{"torn', line(round=5)[:-1], b" ", b"\r"])
@pytest.mark.parametrize("position", [0, 1, 2])
def test_a_torn_tail_is_reported_from_every_position(root, tmp_path, position, tail):
    place(root, COMPLETE + tail)
    before = snapshot(tmp_path)
    whole = read(root, RUN).events
    assert len(whole) == 2

    assert read(root, RUN, position) == Log(whole[position:], len(tail))
    assert snapshot(tmp_path) == before


def test_two_runs_have_two_files_from_a_position(root):
    place(root, EXAMPLE)
    place(root, line(round=6), "runs/run-b/events.ndjson")

    assert read(root, "run-b", 0) == Log([ev(round=6)], 0)
    assert read(root, "run-b", 1) == Log([], 0)
    assert len(read(root, RUN, 1).events) == 2
    with pytest.raises(PositionBeyondLogError) as excinfo:
        read(root, "run-b", 2)
    assert str(excinfo.value) == beyond(2, 1, "runs/run-b/events.ndjson")


BEYOND = {
    "no line": (b"", 0),
    "one line": (line(), 1),
    "three lines": (EXAMPLE, 3),
    "three lines with a carriage return": (EXAMPLE.replace(b"\n", b"\r\n"), 3),
    "a torn tail only": (line(round=5)[:-1], 0),
    "a torn tail that parses": (COMPLETE + line(round=5)[:-1], 2),
    "a torn tail of white space": (COMPLETE + b" ", 2),
    "damaged lines only": (b"not json\n\n\xff\n", 3),
}


@pytest.mark.parametrize("excess", [1, 2, keys.MAX_INTEGER])
@pytest.mark.parametrize("case", BEYOND)
def test_a_position_beyond_the_end_of_the_log(root, tmp_path, case, excess):
    content, count = BEYOND[case]
    position = min(count + excess, keys.MAX_INTEGER)
    place(root, content)
    before = snapshot(tmp_path)

    with pytest.raises(PositionBeyondLogError) as excinfo:
        read(root, RUN, position)

    assert str(excinfo.value) == beyond(position, count)
    assert isinstance(excinfo.value, CorruptEventsError)
    assert not isinstance(excinfo.value, (ValueError, UnsupportedVersionError))
    assert read(root, RUN, count).events == []
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "prepare", ["nothing", "runs", "run", "file as runs", "file as run"]
)
def test_a_position_beyond_a_missing_file(root, tmp_path, prepare):
    if prepare == "runs":
        (root / "runs").mkdir()
    elif prepare == "run":
        (root / "runs" / RUN).mkdir(parents=True)
    elif prepare == "file as runs":
        place(root, b"synthetic", "runs")
    elif prepare == "file as run":
        place(root, b"synthetic", f"runs/{RUN}")
    before = snapshot(tmp_path)

    assert read(root, RUN, 0) == Log([], 0)
    with pytest.raises(PositionBeyondLogError) as excinfo:
        read(root, RUN, 1)

    assert str(excinfo.value) == beyond(1, 0)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("position", [0, 1, 2])
@pytest.mark.parametrize(
    "case", ["invalid JSON", "a blank line", "invalid UTF-8", "no time"]
)
def test_damage_after_the_position_keeps_the_line_number_of_the_file(
    root, tmp_path, case, position
):
    place(root, line(round=1) + line(round=2) + DAMAGED[case] + b"\n" + line(round=4))
    before = snapshot(tmp_path)

    with pytest.raises(CorruptEventsError) as excinfo:
        read(root, RUN, position)

    assert str(excinfo.value).startswith(f"{FILE}: line 3: is damaged: ")
    assert not isinstance(excinfo.value, PositionBeyondLogError)
    assert read(root, RUN, 3) == Log([ev(round=4)], 0)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("position", [0, 1, 2])
@pytest.mark.parametrize("case", OTHER_VERSIONS)
def test_another_version_after_the_position_keeps_the_line_number_of_the_file(
    root, tmp_path, case, position
):
    place(root, line(round=1) + line(round=2) + OTHER_VERSIONS[case] + b"\n")
    before = snapshot(tmp_path)

    with pytest.raises(UnsupportedVersionError) as excinfo:
        read(root, RUN, position)

    version = json.loads(OTHER_VERSIONS[case])["schema_version"]
    expected = f"{FILE}: line 3: schema_version: {version} is not supported"
    assert str(excinfo.value) == expected
    assert read(root, RUN, 3) == Log([], 0)
    assert snapshot(tmp_path) == before


INVALID_POSITIONS = {
    "True": True,
    "False": False,
    "a float": 1.0,
    "a str": "1",
    "None": None,
    "a list": [1],
    "negative": -1,
    "2^53": keys.MAX_INTEGER + 1,
}


@pytest.mark.parametrize("case", INVALID_POSITIONS)
def test_an_invalid_position(root, tmp_path, case):
    position = INVALID_POSITIONS[case]
    place(root, EXAMPLE)
    before = snapshot(tmp_path)
    rule = f"position: must be an int from 0 to {keys.MAX_INTEGER}, got "

    with pytest.raises(InvalidEventError) as excinfo:
        read(root, RUN, position)
    assert str(excinfo.value) == rule + f"{type(position).__name__} {position!r}"
    with pytest.raises(InvalidEventError, match="position: must be "):
        read(tmp_path / "missing", RUN, position)
    with pytest.raises(layout.InvalidPathValueError, match="run_id"):
        read(tmp_path / "missing", "Run-a", position)

    assert snapshot(tmp_path) == before


def test_the_largest_position_is_an_argument(root):
    place(root, EXAMPLE)

    with pytest.raises(PositionBeyondLogError) as excinfo:
        read(root, RUN, keys.MAX_INTEGER)

    assert str(excinfo.value) == beyond(keys.MAX_INTEGER, 3)


@pytest.mark.parametrize("position", [1, 5])
def test_a_position_does_not_change_the_other_argument_checks(root, tmp_path, position):
    before = snapshot(tmp_path)

    with pytest.raises(layout.InvalidPathValueError, match="run_id"):
        read(root, "Run-a", position)
    with pytest.raises(FileNotFoundError, match="data root is not an existing"):
        read(tmp_path / "missing", RUN, position)

    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("position", [1, 5])
def test_a_directory_in_the_place_of_the_file_with_a_position(root, tmp_path, position):
    (root / FILE).mkdir(parents=True)
    before = snapshot(tmp_path)

    with pytest.raises(CorruptEventsError) as excinfo:
        read(root, RUN, position)

    assert str(excinfo.value) == f"{FILE}: is not a regular file"
    assert not isinstance(excinfo.value, PositionBeyondLogError)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("position", [1, 5])
@pytest.mark.parametrize("target", ["a file", "nothing"])
def test_a_symbolic_link_is_not_followed_with_a_position(
    root, tmp_path, position, target
):
    elsewhere = tmp_path / "elsewhere.ndjson"
    if target == "a file":
        elsewhere.write_bytes(COMPLETE)
    (root / FILE).parent.mkdir(parents=True)
    try:
        (root / FILE).symlink_to(elsewhere)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links cannot be created here")

    with pytest.raises(CorruptEventsError, match="is not a regular file") as excinfo:
        read(root, RUN, position)

    assert not isinstance(excinfo.value, PositionBeyondLogError)
    assert elsewhere.exists() == (target == "a file")
