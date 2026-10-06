import json
import os
import sys
from pathlib import Path

import pytest

from hilclaw.harness import measurement
from hilclaw.harness.measurement import CV_MAX, N_MAX_DEFAULT, N_MIN, State
from hilclaw.harness.timing import (
    SAMPLE_FORMS,
    SEED_LIMIT,
    Broken,
    Report,
    TimingArgumentError,
    TimingResult,
    driver_arguments,
    parse_report,
    run_timing,
)
from hilclaw.local_run import ProgramNotFoundError, RunResult

STAND_IN = """\
import json, os, sys, time
from pathlib import Path
here = Path(__file__).parent
plan = json.loads((here / "plan.json").read_text(encoding="utf-8"))
call = {"argv": sys.argv[1:], "cwd": os.getcwd(), "mark": os.environ.get("HILCLAW_TEST_MARK")}
(here / "started.json").write_text(json.dumps(call), encoding="utf-8")
sys.stderr.write(plan["stderr"])
sys.stderr.flush()
sys.stdout.buffer.write(bytes.fromhex(plan["stdout"]))
sys.stdout.buffer.flush()
time.sleep(plan["sleep"])
sys.exit(plan["status"])
"""

# The worked report of ADR-0009 decision 8.
WORKED = (104200311, 99870122, 101004517, 100310960, 102118803)
WORKED_REPORT = (
    b"resolution_ns 1\n"
    b"interval_ns 104200311\n"
    b"interval_ns 99870122\n"
    b"interval_ns 101004517\n"
    b"interval_ns 100310960\n"
    b"interval_ns 102118803\n"
    b"stop converged\n"
)

# Synthetic lengths. NOISY never meets the rule under either form. SPLIT meets
# it at n = 5 as reciprocals but not as lengths; SPLIT + (100,) meets it at
# n = 6 as lengths.
NOISY = (90, 110) * 6
SPLIT = (100, 100, 100, 100, 112)

TIMEOUT = 60
PARAMETERS = {"m": 2, "k": 3, "n": 4, "sample_form": "interval", "seed": 7}

NOT_AN_INT = [True, False, 1.0, "1", None, [1], 1 + 0j]
BAD_ARGUMENTS = (
    [(name, value) for name in "mkn" for value in [0, -1, 10**5000, *NOT_AN_INT]]
    + [("n_max", value) for value in [N_MIN - 1, 0, -10, 10**5000, *NOT_AN_INT]]
    + [("seed", value) for value in [-1, SEED_LIMIT, 10**5000, *NOT_AN_INT]]
    + [
        ("sample_form", value)
        for value in ["Interval", "interval ", "", "time", "rate", None, 0, True]
        + [b"interval", ("interval",), ["reciprocal"], SAMPLE_FORMS]
    ]
)

BAD_ARGUMENT_IDS = [
    f"{name}-{type(value).__name__}-{position}"
    for position, (name, value) in enumerate(BAD_ARGUMENTS)
]

GOOD_REPORTS = {
    "worked": (WORKED_REPORT, Report(1, WORKED, State.CONVERGED)),
    "not-converged": (
        b"resolution_ns 41\ninterval_ns 7\nstop not_converged\n",
        Report(41, (7,), State.NOT_CONVERGED),
    ),
    "no-interval-converged": (
        b"resolution_ns 1\nstop converged\n",
        Report(1, (), State.CONVERGED),
    ),
    "no-interval-not-converged": (
        b"resolution_ns 1\nstop not_converged\n",
        Report(1, (), State.NOT_CONVERGED),
    ),
    "resolution-zero": (
        b"resolution_ns 0\ninterval_ns 10\nstop converged\n",
        Report(0, (10,), State.CONVERGED),
    ),
    "interval-zero": (
        b"resolution_ns 1\ninterval_ns 0\ninterval_ns 3\nstop converged\n",
        Report(1, (0, 3), State.CONVERGED),
    ),
    "many-intervals": (
        b"resolution_ns 1\n" + b"interval_ns 100\n" * 40 + b"stop converged\n",
        Report(1, (100,) * 40, State.CONVERGED),
    ),
    "long-integers": (
        b"resolution_ns 18446744073709551616\n"
        + b"interval_ns 1"
        + b"0" * 400
        + b"\nstop converged\n",
        Report(2**64, (10**400,), State.CONVERGED),
    ),
}

HEAD = b"resolution_ns 1\n"
TAIL = b"stop converged\n"
FIVE = b"interval_ns 100\n" * 5


def odd_integer(digits):
    return HEAD + b"interval_ns " + digits + b"\n" + TAIL


BAD_REPORTS = {
    "empty": b"",
    "only-lf": b"\n",
    "only-resolution": HEAD,
    "only-stop": TAIL,
    "only-intervals": FIVE,
    "missing-stop": HEAD + FIVE,
    "missing-resolution": FIVE + TAIL,
    "interval-before-resolution": b"interval_ns 100\n" + HEAD + FIVE + TAIL,
    "stop-first": TAIL + HEAD + FIVE,
    "resolution-last": FIVE + TAIL + HEAD,
    "resolution-twice": HEAD + HEAD + FIVE + TAIL,
    "resolution-among-intervals": HEAD + FIVE + HEAD + TAIL,
    "stop-twice": HEAD + FIVE + TAIL + TAIL,
    "stop-among-intervals": HEAD + TAIL + FIVE + TAIL,
    "interval-after-stop": HEAD + FIVE + TAIL + b"interval_ns 100\n",
    "text-after-stop": HEAD + FIVE + TAIL + b"done\n",
    "blank-after-stop": HEAD + FIVE + TAIL + b"\n",
    "blank-first": b"\n" + HEAD + FIVE + TAIL,
    "blank-between": HEAD + b"\n" + FIVE + TAIL,
    "crlf": (HEAD + FIVE + TAIL).replace(b"\n", b"\r\n"),
    "one-cr": HEAD + b"interval_ns 100\r\n" + TAIL,
    "cr-only": (HEAD + FIVE + TAIL).replace(b"\n", b"\r"),
    "no-final-lf": HEAD + FIVE + b"stop converged",
    "foreign-line": HEAD + b"interval_ns 100\nhello from the kernel\n" + TAIL,
    "foreign-first": b"hello from the kernel\n" + HEAD + FIVE + TAIL,
    "other-keyword": HEAD + b"interval_us 100\n" + TAIL,
    "keyword-case": HEAD + b"Interval_ns 100\n" + TAIL,
    "resolution-keyword": b"resolution 1\n" + FIVE + TAIL,
    "resolution-not-integer": b"resolution_ns 1.0\n" + FIVE + TAIL,
    "resolution-missing-value": b"resolution_ns\n" + FIVE + TAIL,
    "stop-other-word": HEAD + FIVE + b"stop done\n",
    "stop-bare": HEAD + FIVE + b"stop\n",
    "stop-no-word": HEAD + FIVE + b"stop \n",
    "stop-case": HEAD + FIVE + b"stop Converged\n",
    "stop-trailing-space": HEAD + FIVE + b"stop converged \n",
    "stop-two-spaces": HEAD + FIVE + b"stop  converged\n",
    "stop-both-words": HEAD + FIVE + b"stop converged not_converged\n",
    "stop-continue": HEAD + FIVE + b"stop continue\n",
    "negative": odd_integer(b"-100"),
    "plus-sign": odd_integer(b"+100"),
    "fraction": odd_integer(b"100.5"),
    "fraction-zero": odd_integer(b"100.0"),
    "exponent": odd_integer(b"1e3"),
    "hexadecimal": odd_integer(b"0x10"),
    "underscore": odd_integer(b"1_000"),
    "leading-zero": odd_integer(b"0100"),
    "double-zero": odd_integer(b"00"),
    "empty-integer": odd_integer(b""),
    "no-space": HEAD + b"interval_ns\n" + TAIL,
    "glued": HEAD + b"interval_ns100\n" + TAIL,
    "two-spaces": odd_integer(b" 100"),
    "trailing-space": odd_integer(b"100 "),
    "two-values": odd_integer(b"100 100"),
    "tab": HEAD + b"interval_ns\t100\n" + TAIL,
    "leading-space": HEAD + b" interval_ns 100\n" + TAIL,
    "5000-digits": odd_integer(b"1" * 5000),
    "non-ascii-digit": odd_integer("١٠٠".encode()),
    "full-width-digit": odd_integer("１００".encode()),
    "non-ascii-text": HEAD + "간격 100\n".encode() + TAIL,
    "invalid-utf8": odd_integer(b"1\xff0"),
    "invalid-utf8-line": HEAD + b"\xff\xfe\n" + TAIL,
    "nul": odd_integer(b"1\x000"),
    "bom": b"\xef\xbb\xbf" + HEAD + FIVE + TAIL,
}

THROUGH_A_RUN = [
    "empty",
    "missing-stop",
    "missing-resolution",
    "interval-before-resolution",
    "crlf",
    "no-final-lf",
    "foreign-line",
    "text-after-stop",
    "stop-other-word",
    "negative",
    "two-spaces",
    "5000-digits",
    "invalid-utf8",
]


def report(intervals, stop="converged", resolution=1):
    lines = [f"resolution_ns {resolution}"]
    lines += [f"interval_ns {interval}" for interval in intervals]
    lines.append(f"stop {stop}")
    return "".join(line + "\n" for line in lines).encode("ascii")


class StandIn:
    def __init__(self, directory):
        self.directory = directory
        self.record = directory / "started.json"

    def __call__(self, stdout=b"", *, status=0, stderr="", sleep=0):
        plan = {
            "stdout": stdout.hex(),
            "status": status,
            "stderr": stderr,
            "sleep": sleep,
        }
        (self.directory / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        script = self.directory / "timing.py"
        script.write_text(STAND_IN, encoding="utf-8")
        return (sys.executable, str(script))

    @property
    def started(self):
        return self.record.exists()

    def call(self):
        return json.loads(self.record.read_text(encoding="utf-8"))


@pytest.fixture
def stand_in(tmp_path):
    directory = tmp_path / "stand-in"
    directory.mkdir()
    return StandIn(directory)


def timed(executable, **changes):
    return run_timing(executable, **{**PARAMETERS, "timeout_s": TIMEOUT, **changes})


def assert_completed(result, state, intervals, resolution=1):
    assert isinstance(result, TimingResult)
    assert result.broken is None
    assert result.state is state
    assert result.intervals_ns == tuple(intervals)
    assert type(result.intervals_ns) is tuple
    assert all(type(interval) is int for interval in result.intervals_ns)
    assert result.resolution_ns == resolution
    assert type(result.resolution_ns) is int
    assert isinstance(result.run, RunResult)
    assert result.run.returncode == 0
    assert result.run.timed_out is False


def assert_broken(result, condition):
    assert isinstance(result, TimingResult)
    assert result.broken is condition
    assert result.state is None
    assert result.intervals_ns is None
    assert result.resolution_ns is None
    assert isinstance(result.run, RunResult)


def test_worked_report_of_the_record_is_completed(stand_in):
    result = timed(stand_in(WORKED_REPORT))
    assert_completed(result, State.CONVERGED, WORKED)
    assert result.run.stdout == WORKED_REPORT
    assert result._fields == (
        "broken",
        "state",
        "intervals_ns",
        "resolution_ns",
        "run",
    )


def test_worked_report_is_completed_under_both_forms(stand_in):
    result = timed(stand_in(WORKED_REPORT), sample_form="reciprocal")
    assert_completed(result, State.CONVERGED, WORKED)


def test_run_ended_at_n_max_is_completed_and_marked(stand_in):
    intervals = NOISY[:N_MAX_DEFAULT]
    result = timed(stand_in(report(intervals, "not_converged", resolution=41)))
    assert_completed(result, State.NOT_CONVERGED, intervals, resolution=41)


def test_run_that_converges_between_n_min_and_n_max(stand_in):
    intervals = (*SPLIT, 100)
    assert N_MIN < len(intervals) < N_MAX_DEFAULT
    assert_completed(timed(stand_in(report(intervals))), State.CONVERGED, intervals)


@pytest.mark.parametrize("sample_form", SAMPLE_FORMS)
def test_larger_n_max(sample_form, stand_in):
    executable = stand_in(report(NOISY, "not_converged"))
    result = timed(executable, n_max=len(NOISY), sample_form=sample_form)
    assert_completed(result, State.NOT_CONVERGED, NOISY)
    assert stand_in.call()["argv"][4] == "12"


def test_n_max_equal_to_n_min(stand_in):
    intervals = NOISY[:N_MIN]
    result = timed(stand_in(report(intervals, "not_converged")), n_max=N_MIN)
    assert_completed(result, State.NOT_CONVERGED, intervals)
    assert stand_in.call()["argv"][3:5] == ["5", "5"]


def test_the_process_gets_exactly_the_driver_arguments(stand_in):
    executable = stand_in(WORKED_REPORT)
    result = run_timing(
        executable, m=2048, k=1, n=2048, sample_form="interval", seed=7, timeout_s=60
    )
    expected = ["2048", "1", "2048", "5", "10", "0.05", "interval", "7"]
    assert stand_in.call()["argv"] == expected
    assert result.run.command[1:] == (executable[1], *expected)
    assert os.path.samefile(result.run.command[0], sys.executable)
    assert tuple(expected) == driver_arguments(
        m=2048, k=1, n=2048, n_max=N_MAX_DEFAULT, sample_form="interval", seed=7
    )


def test_cwd_and_env_reach_the_process(stand_in, tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    env = {**os.environ, "HILCLAW_TEST_MARK": "handed over"}
    result = timed(stand_in(WORKED_REPORT), cwd=work, env=env)
    assert_completed(result, State.CONVERGED, WORKED)
    call = stand_in.call()
    assert os.path.samefile(call["cwd"], work)
    assert call["mark"] == "handed over"


def test_cwd_and_env_are_inherited_by_default(stand_in, monkeypatch):
    monkeypatch.setenv("HILCLAW_TEST_MARK", "inherited")
    timed(stand_in(WORKED_REPORT))
    call = stand_in.call()
    assert os.path.samefile(call["cwd"], os.getcwd())
    assert call["mark"] == "inherited"


def test_standard_error_is_not_parsed(stand_in):
    noise = "interval_ns 0\nstop not_converged\nwarning: café\n"
    result = timed(stand_in(WORKED_REPORT, stderr=noise))
    assert_completed(result, State.CONVERGED, WORKED)
    assert b"stop not_converged" in result.run.stderr


def test_executable_as_one_path_is_the_whole_prefix():
    for executable in (sys.executable, Path(sys.executable)):
        result = timed(executable)
        assert_broken(result, Broken.EXIT_STATUS)
        assert result.run.command[1:] == driver_arguments(
            **PARAMETERS, n_max=N_MAX_DEFAULT
        )


def test_executable_prefix_may_be_a_list(stand_in):
    result = timed(list(stand_in(WORKED_REPORT)))
    assert_completed(result, State.CONVERGED, WORKED)


def test_the_sample_form_is_honoured_at_n_min(stand_in):
    assert measurement.stopping_state(SPLIT) is State.CONTINUE
    reciprocals = [1 / interval for interval in SPLIT]
    assert measurement.stopping_state(reciprocals) is State.CONVERGED
    executable = stand_in(report(SPLIT))
    result = timed(executable, sample_form="reciprocal")
    assert_completed(result, State.CONVERGED, SPLIT)
    assert stand_in.call()["argv"][6] == "reciprocal"
    assert_broken(timed(executable, sample_form="interval"), Broken.REPLAY)
    assert stand_in.call()["argv"][6] == "interval"


def test_the_sample_form_is_honoured_after_n_min(stand_in):
    intervals = (*SPLIT, 100)
    executable = stand_in(report(intervals))
    assert_completed(timed(executable), State.CONVERGED, intervals)
    assert_broken(timed(executable, sample_form="reciprocal"), Broken.REPLAY)


@pytest.mark.parametrize("name", GOOD_REPORTS)
def test_parse_report_accepts_the_form(name):
    stdout, expected = GOOD_REPORTS[name]
    parsed = parse_report(stdout)
    assert isinstance(parsed, Report)
    assert parsed == expected
    assert type(parsed.resolution_ns) is int
    assert type(parsed.intervals_ns) is tuple
    assert all(type(interval) is int for interval in parsed.intervals_ns)


def test_parse_report_reads_the_helper_reports():
    assert parse_report(report(WORKED)) == Report(1, WORKED, State.CONVERGED)
    assert parse_report(report(NOISY, "not_converged", 3)) == Report(
        3, NOISY, State.NOT_CONVERGED
    )


@pytest.mark.parametrize("name", BAD_REPORTS)
def test_parse_report_refuses_every_other_form(name):
    assert parse_report(BAD_REPORTS[name]) is None


def test_parse_report_never_raises_on_bytes():
    pieces = [b"resolution_ns", b"interval_ns", b"stop", b"converged", b" ", b"\n"]
    pieces += [b"0", b"7", b"\r", b"\xff", b"-", b"not_converged", b""]
    for first in pieces:
        for second in pieces:
            for third in pieces:
                stdout = first + second + third + b"\n"
                parsed = parse_report(stdout)
                assert parsed is None or isinstance(parsed, Report)


@pytest.mark.parametrize("sample_form", SAMPLE_FORMS)
def test_driver_arguments_order_and_spelling(sample_form):
    arguments = driver_arguments(
        m=1, k=22, n=333, n_max=17, sample_form=sample_form, seed=20261007
    )
    assert arguments == (
        "1",
        "22",
        "333",
        str(N_MIN),
        "17",
        repr(CV_MAX),
        sample_form,
        "20261007",
    )
    assert arguments[3] == "5"
    assert arguments[5] == "0.05"
    assert type(arguments) is tuple
    assert all(type(argument) is str for argument in arguments)


def test_driver_arguments_bounds():
    low = driver_arguments(m=1, k=1, n=1, n_max=N_MIN, sample_form="interval", seed=0)
    assert low == ("1", "1", "1", "5", "5", "0.05", "interval", "0")
    high = driver_arguments(
        m=10**30, k=2**64, n=1, n_max=10**6, sample_form="reciprocal", seed=2**64 - 1
    )
    assert high[0] == "1" + "0" * 30
    assert high[1] == "18446744073709551616"
    assert high[4] == "1000000"
    assert high[7] == "18446744073709551615"
    assert SEED_LIMIT == 2**64
    assert SAMPLE_FORMS == ("interval", "reciprocal")


def test_driver_arguments_follow_the_policy_constants(monkeypatch):
    monkeypatch.setattr(measurement, "N_MIN", 6)
    monkeypatch.setattr(measurement, "CV_MAX", 0.125)
    arguments = driver_arguments(**PARAMETERS, n_max=6)
    assert arguments[3:6] == ("6", "6", "0.125")
    with pytest.raises(TimingArgumentError, match="n_max"):
        driver_arguments(**PARAMETERS, n_max=5)


def test_timeout_is_broken(stand_in):
    partial = b"resolution_ns 1\ninterval_ns 100\n"
    result = timed(stand_in(partial, sleep=30), timeout_s=2)
    assert_broken(result, Broken.TIMEOUT)
    assert result.run.timed_out is True
    assert result.run.returncode is None


def test_non_zero_exit_after_a_valid_report_is_broken(stand_in):
    result = timed(stand_in(WORKED_REPORT, status=3))
    assert_broken(result, Broken.EXIT_STATUS)
    assert result.run.returncode == 3
    assert result.run.stdout == WORKED_REPORT


def test_non_zero_exit_comes_before_the_form(stand_in):
    result = timed(stand_in(b"interval_ns 0\n", status=1, stderr="cannot allocate\n"))
    assert_broken(result, Broken.EXIT_STATUS)
    assert result.run.stderr.strip() == b"cannot allocate"


@pytest.mark.parametrize("name", THROUGH_A_RUN)
def test_output_of_another_form_is_broken(name, stand_in):
    result = timed(stand_in(BAD_REPORTS[name]))
    assert_broken(result, Broken.REPORT_FORM)
    assert result.run.returncode == 0
    assert result.run.stdout == BAD_REPORTS[name]


def test_the_form_comes_before_a_zero_interval(stand_in):
    result = timed(stand_in(HEAD + b"interval_ns 0\n"))
    assert_broken(result, Broken.REPORT_FORM)


@pytest.mark.parametrize("sample_form", SAMPLE_FORMS)
@pytest.mark.parametrize(
    "intervals",
    [(100, 100, 0, 100, 100), (0,) * 5, (*WORKED, 0), (0,)],
)
def test_zero_interval_is_broken(intervals, sample_form, stand_in):
    result = timed(stand_in(report(intervals)), sample_form=sample_form)
    assert_broken(result, Broken.ZERO_INTERVAL)
    assert result.run.stdout == report(intervals)


REPLAY_DISAGREEMENTS = {
    "repeat-after-the-stop-was-due": ((*WORKED, 100000000), "converged"),
    "converged-reported-as-not": (WORKED, "not_converged"),
    "noisy-reported-as-converged": (NOISY[:N_MIN], "converged"),
    "noisy-at-n-max-reported-as-converged": (NOISY[:N_MAX_DEFAULT], "converged"),
    "stopped-before-n-max": (NOISY[: N_MAX_DEFAULT - 1], "not_converged"),
    "stopped-at-n-min-not-converged": (NOISY[:N_MIN], "not_converged"),
    "fewer-than-n-min": (WORKED[:4], "converged"),
    "fewer-than-n-min-not-converged": (WORKED[:4], "not_converged"),
    "one-interval": ((100,), "converged"),
    "no-interval": ((), "converged"),
    "no-interval-not-converged": ((), "not_converged"),
    "more-than-n-max": (NOISY[: N_MAX_DEFAULT + 1], "not_converged"),
    "more-than-n-max-converged": ((100,) * (N_MAX_DEFAULT + 1), "converged"),
    "far-more-than-n-max": ((90, 110) * 200, "not_converged"),
    "beyond-the-float-range": ((10**400,) * N_MIN, "converged"),
    "one-beyond-the-float-range": ((*WORKED[:4], 10**400), "not_converged"),
}


@pytest.mark.parametrize("sample_form", SAMPLE_FORMS)
@pytest.mark.parametrize("name", REPLAY_DISAGREEMENTS)
def test_replay_disagreement_is_broken(name, sample_form, stand_in):
    intervals, stop = REPLAY_DISAGREEMENTS[name]
    stdout = report(intervals, stop)
    assert parse_report(stdout) is not None
    result = timed(stand_in(stdout), sample_form=sample_form)
    assert_broken(result, Broken.REPLAY)
    assert result.run.returncode == 0
    assert result.run.stdout == stdout


def test_the_caller_n_max_is_the_one_replayed(stand_in):
    executable = stand_in(report(NOISY[:N_MAX_DEFAULT], "not_converged"))
    assert_broken(timed(executable, n_max=N_MAX_DEFAULT + 1), Broken.REPLAY)
    assert_broken(timed(executable, n_max=N_MAX_DEFAULT - 1), Broken.REPLAY)
    assert timed(executable).broken is None


def test_broken_conditions_are_a_closed_set():
    assert [condition.name for condition in Broken] == [
        "TIMEOUT",
        "EXIT_STATUS",
        "REPORT_FORM",
        "ZERO_INTERVAL",
        "REPLAY",
    ]


@pytest.mark.parametrize(("name", "value"), BAD_ARGUMENTS, ids=BAD_ARGUMENT_IDS)
def test_caller_errors_raise_and_start_nothing(name, value, stand_in):
    arguments = {**PARAMETERS, "n_max": N_MAX_DEFAULT, name: value}
    with pytest.raises(TimingArgumentError, match=f"^{name}: must be "):
        driver_arguments(**arguments)
    with pytest.raises(TimingArgumentError, match=f"^{name}: must be "):
        run_timing(stand_in(WORKED_REPORT), **arguments, timeout_s=TIMEOUT)
    assert not stand_in.started


def test_argument_error_is_a_value_error():
    assert issubclass(TimingArgumentError, ValueError)
    with pytest.raises(TimingArgumentError, match="^m: must be .* got bool True$"):
        driver_arguments(**{**PARAMETERS, "m": True}, n_max=N_MAX_DEFAULT)


@pytest.mark.parametrize("missing", ["sample_form", "seed", "timeout_s", "m"])
def test_run_timing_has_no_default_for(missing, stand_in):
    arguments = {**PARAMETERS, "timeout_s": TIMEOUT}
    del arguments[missing]
    with pytest.raises(TypeError, match=missing):
        run_timing(stand_in(WORKED_REPORT), **arguments)
    assert not stand_in.started


@pytest.mark.parametrize("missing", ["sample_form", "seed", "n_max", "k"])
def test_driver_arguments_has_no_default_for(missing):
    arguments = {**PARAMETERS, "n_max": N_MAX_DEFAULT}
    del arguments[missing]
    with pytest.raises(TypeError, match=missing):
        driver_arguments(**arguments)


def test_parameters_are_keyword_only(stand_in):
    with pytest.raises(TypeError):
        run_timing(stand_in(WORKED_REPORT), 2, 3, 4, "interval", 7, TIMEOUT)
    with pytest.raises(TypeError):
        driver_arguments(2, 3, 4, 10, "interval", 7)
    assert not stand_in.started


@pytest.mark.parametrize(
    ("timeout_s", "error"),
    [(0, ValueError), (-1, ValueError), (float("inf"), ValueError)]
    + [("60", TypeError), (None, TypeError), (True, TypeError)],
)
def test_time_limit_errors_are_those_of_the_runner(timeout_s, error, stand_in):
    with pytest.raises(error) as raised:
        timed(stand_in(WORKED_REPORT), timeout_s=timeout_s)
    assert not isinstance(raised.value, TimingArgumentError)
    assert not stand_in.started


@pytest.mark.parametrize(
    "executable",
    ["hilclaw-no-such-timing-executable", ("hilclaw-no-such-timing-executable", "x")]
    + [Path("no-such-directory") / "timing"],
)
def test_executable_that_does_not_exist(executable):
    with pytest.raises(ProgramNotFoundError):
        timed(executable)


@pytest.mark.parametrize("executable", [(), []])
def test_empty_executable_prefix(executable):
    with pytest.raises(ValueError, match="empty") as raised:
        timed(executable)
    assert not isinstance(raised.value, TimingArgumentError)


@pytest.mark.parametrize("executable", [None, 5, b"timing", (b"timing",), (5,)])
def test_executable_of_the_wrong_type(executable):
    with pytest.raises(TypeError):
        timed(executable)


def test_prefix_part_of_the_wrong_type_starts_nothing(stand_in):
    with pytest.raises(TypeError):
        timed((*stand_in(WORKED_REPORT), 5))
    assert not stand_in.started
