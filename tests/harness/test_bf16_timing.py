import json
import os
import signal
import subprocess
import sys
import types
from pathlib import Path

import pytest

import hilclaw
from hilclaw import local_run
from hilclaw.harness import bf16_rope_arrays, bf16_timing, timing
from hilclaw.harness.bf16_timing import KINDS, program_arguments, run_bf16_timing
from hilclaw.harness.measurement import CV_MAX, N_MAX_DEFAULT, N_MIN, State
from hilclaw.harness.timing import (
    SEED_LIMIT,
    Broken,
    TimingArgumentError,
    TimingResult,
    driver_arguments,
)
from hilclaw.local_run import RunResult

STAND_IN = """\
import json, os, sys, time
from pathlib import Path
here = Path(__file__).parent
plan = json.loads((here / "plan.json").read_text(encoding="utf-8"))
call = {"argv": sys.argv[1:], "cwd": os.getcwd(), "mark": os.environ.get("HILCLAW_TEST_MARK")}
(here / "started.json").write_text(json.dumps(call), encoding="utf-8")
sys.stderr.buffer.write(plan["stderr"].encode())
sys.stderr.buffer.flush()
sys.stdout.buffer.write(bytes.fromhex(plan["stdout"]))
sys.stdout.buffer.flush()
time.sleep(plan["sleep"])
if plan["signal"]:
    os.kill(os.getpid(), plan["signal"])
sys.exit(plan["status"])
"""

WORKED = (104200311, 99870122, 101004517, 100310960, 102118803)
NOISY = (90, 110) * 6
TIMEOUT = 60
DIMS = {
    "gemm": (2, 3, 4),
    "rmsnorm": (5, 6),
    "elementwise_add": (5, 6),
    "swiglu": (5, 6),
    "rope": (2, 3, 4),
    "sdpa_kv_cache": (3, 5, 4, 2, 6),
}


class Count(int):
    pass


class Word(str):
    pass


NOT_AN_INT = [True, False, 1.0, "1", None, [1], 1 + 0j, Count(7)]


def report(intervals, stop="converged", resolution=1):
    lines = [f"resolution_ns {resolution}"]
    lines += [f"interval_ns {interval}" for interval in intervals]
    lines.append(f"stop {stop}")
    return "".join(line + "\n" for line in lines).encode("ascii")


class StandIn:
    def __init__(self, directory):
        self.directory = directory
        self.record = directory / "started.json"

    def __call__(self, stdout=b"", *, status=0, stderr="", sleep=0, kill=0):
        plan = {
            "stdout": stdout.hex(),
            "status": status,
            "stderr": stderr,
            "sleep": sleep,
            "signal": kill,
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


def timed(executable, kind="gemm", **changes):
    dims = changes.pop("dims", DIMS.get(kind))
    keywords = {"sample_form": "interval", "seed": 7, "timeout_s": TIMEOUT, **changes}
    return run_bf16_timing(executable, kind, dims, **keywords)


def assert_completed(result, state, intervals, resolution=1):
    assert isinstance(result, TimingResult)
    assert result.broken is None
    assert result.state is state
    assert result.intervals_ns == tuple(intervals)
    assert result.resolution_ns == resolution
    assert isinstance(result.run, RunResult)
    assert result.run.returncode == 0


def assert_broken(result, condition):
    assert isinstance(result, TimingResult)
    assert result.broken is condition
    assert result.state is None
    assert result.intervals_ns is None
    assert result.resolution_ns is None
    assert result.memory_bytes is None
    assert isinstance(result.run, RunResult)


def platform(monkeypatch, name):
    monkeypatch.setattr(bf16_timing, "sys", types.SimpleNamespace(platform=name))


def usage(monkeypatch, max_rss):
    original = local_run.run

    def run(*arguments, **keywords):
        return original(*arguments, **keywords)._replace(max_rss=max_rss)

    monkeypatch.setattr(bf16_timing.local_run, "run", run)


def test_kinds_are_the_six_of_adr_0181():
    assert KINDS == (
        "gemm",
        "rmsnorm",
        "elementwise_add",
        "swiglu",
        "rope",
        "sdpa_kv_cache",
    )
    assert bf16_timing.__all__ == [
        "KINDS",
        "program_arguments",
        "rope_rows",
        "run_bf16_timing",
    ]


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("sample_form", ["interval", "reciprocal"])
def test_program_arguments_are_the_dims_then_those_of_driver_arguments(
    kind, sample_form
):
    dims = DIMS[kind]
    arguments = program_arguments(
        kind, dims, n_max=12, sample_form=sample_form, seed=SEED_LIMIT - 1
    )
    tail = driver_arguments(
        m=1, k=1, n=1, n_max=12, sample_form=sample_form, seed=SEED_LIMIT - 1
    )[3:]
    assert arguments == (*map(str, dims), *tail)
    assert arguments[len(dims) :] == (
        str(N_MIN),
        "12",
        repr(CV_MAX),
        sample_form,
        str(SEED_LIMIT - 1),
    )
    assert type(arguments) is tuple
    assert all(type(argument) is str for argument in arguments)


def test_program_arguments_take_large_dims_and_the_smallest_values():
    assert program_arguments(
        "swiglu", (1, 10**30), n_max=N_MIN, sample_form="interval", seed=0
    ) == ("1", "1" + "0" * 30, str(N_MIN), str(N_MIN), repr(CV_MAX), "interval", "0")


BAD_KINDS = ["fp16", "GEMM", "", "gemm ", b"gemm", None, 1]
BAD_KINDS += [Word("gemm"), ("gemm",)]


@pytest.mark.parametrize("kind", BAD_KINDS, ids=lambda value: repr(value))
def test_program_arguments_refuse_a_kind_outside_the_six(kind):
    with pytest.raises(TimingArgumentError, match=r"^kind: must be one of"):
        program_arguments(kind, (2, 3), n_max=10, sample_form="interval", seed=7)


BAD_DIMS = [
    ("gemm", (2, 3), "dims"),
    ("gemm", (2, 3, 4, 5), "dims"),
    ("rmsnorm", (2, 3, 4), "dims"),
    ("rmsnorm", (2,), "dims"),
    ("swiglu", [2, 3], "dims"),
    ("swiglu", None, "dims"),
    ("swiglu", "23", "dims"),
    ("rope", (2, 4), "dims"),
    ("rope", (2, 3, 4, 5), "dims"),
    ("rope", (2, 3, 3), r"dims\[2\]"),
    ("rope", (0, 3, 4), r"dims\[0\]"),
    ("sdpa_kv_cache", (2, 3, 4), "dims"),
    ("sdpa_kv_cache", (2, 3, 4, 2, 6, 7), "dims"),
    ("sdpa_kv_cache", (3, 2, 4, 2, 6), r"dims\[1\]"),
    ("sdpa_kv_cache", (2, 3, 5, 2, 6), r"dims\[2\]"),
    ("sdpa_kv_cache", (2, 3, 4, 0, 6), r"dims\[3\]"),
    ("elementwise_add", (0, 3), r"dims\[0\]"),
    ("elementwise_add", (3, -1), r"dims\[1\]"),
    ("gemm", (1, 0, 1), r"dims\[1\]"),
    ("gemm", (1, 1, 10**5000), r"dims\[2\]"),
] + [("rmsnorm", (value, 3), r"dims\[0\]") for value in NOT_AN_INT]


@pytest.mark.parametrize(
    "kind, dims, name",
    BAD_DIMS,
    ids=[f"{kind}-{index}" for index, (kind, _, _) in enumerate(BAD_DIMS)],
)
def test_program_arguments_refuse_wrong_dims(kind, dims, name):
    with pytest.raises(TimingArgumentError, match=rf"^{name}: must be"):
        program_arguments(kind, dims, n_max=10, sample_form="interval", seed=7)


BAD_REST = (
    [("n_max", value) for value in [N_MIN - 1, 0, -10, 10**5000, *NOT_AN_INT]]
    + [("seed", value) for value in [-1, SEED_LIMIT, 10**5000, *NOT_AN_INT]]
    + [
        ("sample_form", value)
        for value in ["Interval", "interval ", "", "time", None, 0, True, b"interval"]
        + [("interval",), Word("interval")]
    ]
)


@pytest.mark.parametrize(
    "name, value",
    BAD_REST,
    ids=[f"{name}-{index}" for index, (name, _) in enumerate(BAD_REST)],
)
def test_program_arguments_refuse_what_driver_arguments_refuses(name, value):
    keywords = {"n_max": 10, "sample_form": "interval", "seed": 7, name: value}
    with pytest.raises(TimingArgumentError, match=rf"^{name}: must be"):
        program_arguments("elementwise_add", (2, 3), **keywords)
    with pytest.raises(TimingArgumentError, match=rf"^{name}: must be"):
        driver_arguments(m=1, k=1, n=1, **keywords)


def test_program_arguments_test_kind_then_dims_then_the_rest():
    with pytest.raises(TimingArgumentError, match="^kind"):
        program_arguments("fp16", None, n_max=0, sample_form=None, seed=-1)
    with pytest.raises(TimingArgumentError, match="^dims"):
        program_arguments("gemm", (1, 1), n_max=0, sample_form=None, seed=-1)
    with pytest.raises(TimingArgumentError, match="^n_max"):
        program_arguments("gemm", (1, 1, 1), n_max=0, sample_form=None, seed=-1)


@pytest.mark.parametrize("kind", KINDS)
def test_a_report_of_the_form_is_completed_with_the_kinds_command_line(kind, stand_in):
    result = timed(stand_in(report(WORKED)), kind)
    assert_completed(result, State.CONVERGED, WORKED)
    assert stand_in.call()["argv"] == list(
        program_arguments(
            kind, DIMS[kind], n_max=N_MAX_DEFAULT, sample_form="interval", seed=7
        )
    )


def test_n_max_and_the_reciprocal_form_reach_the_judging(stand_in):
    result = timed(
        stand_in(report(NOISY, "not_converged")),
        "swiglu",
        n_max=len(NOISY),
        sample_form="reciprocal",
    )
    assert_completed(result, State.NOT_CONVERGED, NOISY)
    assert stand_in.call()["argv"][2:4] == [str(N_MIN), str(len(NOISY))]


def test_cwd_and_env_are_handed_to_the_runner(stand_in, tmp_path):
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    env = {**os.environ, "HILCLAW_TEST_MARK": "from the caller"}
    result = timed(stand_in(report(WORKED)), "rmsnorm", cwd=cwd, env=env)
    assert result.broken is None
    call = stand_in.call()
    assert os.path.samefile(call["cwd"], cwd)
    assert call["mark"] == "from the caller"


def test_a_path_executable_is_one_argument(stand_in, monkeypatch):
    commands = []
    original = local_run.run

    def run(command, **keywords):
        commands.append(command)
        return original(stand_in(report(WORKED)), **keywords)

    monkeypatch.setattr(bf16_timing.local_run, "run", run)
    timed("/opt/timing", "elementwise_add")
    assert commands[0][0] == "/opt/timing"
    assert commands[0][1:] == program_arguments(
        "elementwise_add", (5, 6), n_max=N_MAX_DEFAULT, sample_form="interval", seed=7
    )


@pytest.mark.parametrize("kind", KINDS)
def test_a_completed_run_takes_the_memory_figure(kind, stand_in, monkeypatch):
    usage(monkeypatch, 4096)
    for system, expected in [("linux", 4096 * 1024), ("darwin", 4096), ("win32", None)]:
        platform(monkeypatch, system)
        result = timed(stand_in(report(WORKED)), kind)
        assert result.broken is None
        assert result.memory_bytes == expected


BROKEN_RUNS = {
    "timeout": (
        {"stdout": b"resolution_ns 1\ninterval_ns 100\n", "sleep": 30},
        {"timeout_s": 2},
        Broken.TIMEOUT,
    ),
    "exit-status": ({"stdout": report(WORKED), "status": 3}, {}, Broken.EXIT_STATUS),
    "signal": (
        {"stdout": report(WORKED), "kill": getattr(signal, "SIGABRT", 6)},
        {},
        Broken.EXIT_STATUS,
    ),
    "report-form": (
        {"stdout": report(WORKED).replace(b"\n", b"\r\n")},
        {},
        Broken.REPORT_FORM,
    ),
    "malformed": (
        {"stdout": b"resolution_ns 1\ninterval_ns x\nstop converged\n"},
        {},
        Broken.REPORT_FORM,
    ),
    "empty": ({"stdout": b""}, {}, Broken.REPORT_FORM),
    "zero-interval": ({"stdout": report((0,) * 5)}, {}, Broken.ZERO_INTERVAL),
    "replay": ({"stdout": report(WORKED, "not_converged")}, {}, Broken.REPLAY),
}


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("name", BROKEN_RUNS)
def test_a_broken_run_has_the_value_of_run_timing_and_no_figure(
    name, kind, stand_in, monkeypatch
):
    if name == "signal" and os.name != "posix":
        pytest.skip("a signal ends a process on POSIX only")
    plan, changes, condition = BROKEN_RUNS[name]
    usage(monkeypatch, 4096)
    platform(monkeypatch, "linux")
    result = timed(stand_in(**plan), kind, **changes)
    assert_broken(result, condition)
    assert result.run.max_rss == 4096
    fp32 = timing.run_timing(
        stand_in(**plan),
        m=1,
        k=1,
        n=1,
        sample_form="interval",
        seed=7,
        timeout_s=changes.get("timeout_s", TIMEOUT),
    )
    assert fp32.broken is condition


def test_standard_error_is_captured_and_not_parsed(stand_in):
    result = timed(stand_in(report(WORKED), stderr="stop not_converged\n"))
    assert_completed(result, State.CONVERGED, WORKED)
    assert result.run.stderr == b"stop not_converged\n"


def test_arguments_are_refused_before_anything_starts(stand_in):
    executable = stand_in(report(WORKED))
    with pytest.raises(TimingArgumentError, match="^kind"):
        timed(executable, "fp16", dims=(2, 3))
    with pytest.raises(TimingArgumentError, match="^dims"):
        timed(executable, "gemm", dims=(2, 3))
    with pytest.raises(TimingArgumentError, match="^seed"):
        timed(executable, "gemm", seed=-1)
    with pytest.raises(TimingArgumentError, match="^sample_form"):
        timed(executable, "gemm", sample_form="time")
    with pytest.raises(TimingArgumentError, match="^n_max"):
        timed(executable, "gemm", n_max=True)
    assert not stand_in.started


def test_a_bad_executable_is_refused_before_anything_starts(stand_in):
    with pytest.raises(ValueError, match="empty"):
        timed(())
    with pytest.raises(TypeError):
        timed(7)


def test_sample_form_seed_and_time_limit_have_no_default(stand_in):
    executable = stand_in(report(WORKED))
    with pytest.raises(TypeError):
        run_bf16_timing(executable, "gemm", (2, 3, 4), seed=7, timeout_s=TIMEOUT)
    with pytest.raises(TypeError):
        run_bf16_timing(
            executable, "gemm", (2, 3, 4), sample_form="interval", timeout_s=TIMEOUT
        )
    with pytest.raises(TypeError):
        run_bf16_timing(executable, "gemm", (2, 3, 4), sample_form="interval", seed=7)
    assert not stand_in.started


def rows_seen(monkeypatch):
    seen = []
    original = local_run.run

    def run(command, **keywords):
        seen.append(keywords["stdin_data"])
        return original(command, **keywords)

    monkeypatch.setattr(bf16_timing.local_run, "run", run)
    return seen


@pytest.mark.parametrize(
    "dims, seed, start",
    [((1, 2, 4), 6, 127), ((1, 2, 4), 7, 2047), ((3, 2, 4), 7, 0), ((3, 2, 4), 6, 0)],
)
def test_a_rope_run_hands_the_rows_at_the_start_position_of_its_seed(
    dims, seed, start, stand_in, monkeypatch
):
    seen = rows_seen(monkeypatch)
    result = timed(stand_in(report(WORKED)), "rope", dims=dims, seed=seed)
    assert_completed(result, State.CONVERGED, WORKED)
    assert seen == [bf16_rope_arrays.table_rows(dims, start=start).tobytes()]
    assert len(seen[0]) == 4 * dims[0] * dims[2]


@pytest.mark.parametrize("kind", [kind for kind in KINDS if kind != "rope"])
def test_no_other_kind_gets_standard_input(kind, stand_in, monkeypatch):
    seen = rows_seen(monkeypatch)
    assert timed(stand_in(report(WORKED)), kind).broken is None
    assert seen == [None]


def test_a_start_position_the_table_cannot_have_is_refused_before_anything_starts(
    stand_in,
):
    executable = stand_in(report(WORKED))
    with pytest.raises(TimingArgumentError, match="^start: must be"):
        timed(executable, "rope", dims=(1, 1, 2**52), seed=1)
    assert not stand_in.started


@pytest.mark.parametrize(
    ("dims", "seed", "start"),
    [((3, 2, 6), 11, 0), ((1, 2, 4), 10, 127), ((1, 2, 4), 11, 2047)],
)
def test_rope_rows_are_those_of_the_seeds_start_position(dims, seed, start):
    rows = bf16_timing.rope_rows(dims, seed)
    assert type(rows) is bytes
    assert rows == bf16_rope_arrays.table_rows(dims, start=start).tobytes()


def test_rope_rows_of_a_position_the_table_cannot_have_are_refused():
    with pytest.raises(timing.TimingArgumentError):
        bf16_timing.rope_rows((1, 1, 2**52), 1)


def test_a_bad_executable_is_refused_before_the_rows_are_built(monkeypatch):
    def refuse(*arguments, **keywords):
        pytest.fail("the rows were built")

    monkeypatch.setattr(bf16_rope_arrays, "table_rows", refuse)
    with pytest.raises(ValueError, match="empty"):
        timed((), "rope")


def test_importing_the_module_and_running_another_kind_import_no_numpy():
    code = (
        "import sys\n"
        "from hilclaw import local_run\n"
        "from hilclaw.harness import bf16_timing, bf16_timing_build\n"
        "bf16_timing.program_arguments('rope', (1, 1, 2), n_max=10,"
        " sample_form='interval', seed=7)\n"
        "bf16_timing.run_bf16_timing((sys.executable, '-c', 'pass'), 'gemm',"
        " (1, 1, 1), sample_form='interval', seed=7, timeout_s=60)\n"
        "print('numpy' in sys.modules)\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        cwd=Path(hilclaw.__file__).parent.parent,
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == b"False"
