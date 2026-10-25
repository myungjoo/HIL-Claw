import json
import os
import shutil
import signal
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

from hilclaw import rope_bf16_contract
from hilclaw.harness import bf16_rope_arrays, bf16_rope_verification, verification
from hilclaw.harness.bf16_rope_arrays import (
    check_value,
    draw_x,
    reference,
    table_rows,
)
from hilclaw.harness.bf16_rope_verification import (
    END_MARK,
    Broken,
    Judgement,
    Verdict,
    VerificationResult,
    judge_report,
    program_arguments,
    run_bf16_rope_verification,
)
from hilclaw.harness.bf16_verification_build import build_bf16_verification_executable
from hilclaw.harness.verification_arrays import Counts, VerificationArgumentError
from hilclaw.local_run import ProgramNotFoundError, RunResult

STAND_IN = """\
import json, os, sys, time
from pathlib import Path
here = Path(__file__).parent
plan = json.loads((here / "plan.json").read_text(encoding="utf-8"))
received = None if plan["skip_stdin"] else sys.stdin.buffer.read()
call = {
    "argv": sys.argv[1:],
    "cwd": os.getcwd(),
    "mark": os.environ.get("HILCLAW_TEST_MARK"),
    "stdin": None if received is None else received.hex(),
}
(here / "started.json").write_text(json.dumps(call), encoding="utf-8")
sys.stderr.buffer.write(bytes.fromhex(plan["stderr"]))
sys.stderr.buffer.flush()
sys.stdout.buffer.write(bytes.fromhex(plan["stdout"]))
sys.stdout.buffer.flush()
time.sleep(plan["sleep"])
if plan["signal"]:
    os.kill(os.getpid(), plan["signal"])
sys.exit(plan["status"])
"""

TIMEOUT = 60
SEED = 7
LAST = 2**64 - 1
DIMS = (3, 2, 4)
START = 5
# Test values, not tolerances of the harness: the absolute bound of ADR-0164 decision 10.
TOLERANCE = {"rtol": 0.0, "atol": 2**-8 + 2**-21}
NAN = 0x7FC0


def rounded(values):
    bits = np.ascontiguousarray(values, dtype=np.float64).astype(np.float32)
    bits = bits.view(np.uint32)
    return ((bits + np.uint32(0x7FFF) + ((bits >> 16) & 1)) >> 16).astype(np.uint16)


def rounded_references(dims, start, draws, seed):
    rows = table_rows(dims, start=start)
    return [
        rounded(reference(draw_x(dims, seed=seed, draw=draw), rows))
        for draw in range(draws)
    ]


def report_of(dims, start, seed, outputs, wrong_check=()):
    rows = table_rows(dims, start=start)
    parts = []
    for draw, output in enumerate(outputs):
        value = check_value(draw_x(dims, seed=seed, draw=draw), rows)
        if draw in wrong_check:
            value ^= 1
        parts.append(struct.pack("=I", value))
        parts.append(np.ascontiguousarray(output, dtype=np.uint16).tobytes())
    return b"".join(parts) + END_MARK


def passing_report(dims, start, draws, seed):
    return report_of(dims, start, seed, rounded_references(dims, start, draws, seed))


GOOD = passing_report(DIMS, START, 3, SEED)
BLOCK = 4 + 2 * 3 * 2 * 4


class StandIn:
    def __init__(self, directory):
        self.directory = directory
        self.record = directory / "started.json"

    def __call__(
        self, stdout=b"", *, status=0, stderr=b"", sleep=0, kill=0, skip_stdin=False
    ):
        plan = {
            "stdout": stdout.hex(),
            "status": status,
            "stderr": stderr.hex(),
            "sleep": sleep,
            "signal": kill,
            "skip_stdin": skip_stdin,
        }
        (self.directory / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        script = self.directory / "verification.py"
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


@pytest.fixture
def builds(monkeypatch):
    calls = []
    original = bf16_rope_arrays.table_rows

    def counting(dims, *, start):
        calls.append((dims, start))
        return original(dims, start=start)

    monkeypatch.setattr(bf16_rope_arrays, "table_rows", counting)
    return calls


@pytest.fixture
def no_build(monkeypatch):
    def refuse(*args, **kwargs):
        pytest.fail("the table was built")

    monkeypatch.setattr(bf16_rope_arrays, "table_rows", refuse)
    monkeypatch.setattr(bf16_rope_arrays, "check_value", refuse)


def verify(executable, dims=DIMS, start=START, draws=3, seed=SEED, **changes):
    arguments = {"start": start, "draws": draws, "seed": seed, **TOLERANCE}
    arguments["timeout_s"] = TIMEOUT
    return run_bf16_rope_verification(executable, dims, **{**arguments, **changes})


def judge(report, dims=DIMS, start=START, draws=3, seed=SEED, **changes):
    arguments = {"start": start, "draws": draws, "seed": seed, **TOLERANCE}
    return judge_report(report, dims, **{**arguments, **changes})


def assert_judged(judgement, verdict, counts):
    assert type(judgement) is Judgement
    assert judgement.broken is None
    assert judgement.verdict is verdict
    assert type(judgement.counts) is tuple
    assert all(type(count) is Counts for count in judgement.counts)
    assert judgement.counts == tuple(counts)


def assert_judged_broken(judgement, condition):
    assert type(judgement) is Judgement
    assert judgement.broken is condition
    assert judgement.verdict is None
    assert judgement.counts is None


def assert_completed(result, verdict, counts):
    assert isinstance(result, VerificationResult)
    assert result.broken is None
    assert result.verdict is verdict
    assert result.counts == tuple(counts)
    assert isinstance(result.run, RunResult)
    assert result.run.returncode == 0
    assert result.run.timed_out is False
    assert result.run.stdout == b""


def assert_broken(result, condition):
    assert isinstance(result, VerificationResult)
    assert result.broken is condition
    assert result.verdict is None
    assert result.counts is None
    assert isinstance(result.run, RunResult)
    assert result.run.stdout == b""


# --- public names ---


@pytest.mark.parametrize(
    "name", ["END_MARK", "Broken", "Judgement", "Verdict", "VerificationResult"]
)
def test_result_types_and_end_mark_are_those_of_the_first_case(name):
    assert getattr(bf16_rope_verification, name) is getattr(verification, name)
    assert name in bf16_rope_verification.__all__


def test_public_names():
    assert sorted(bf16_rope_verification.__all__) == sorted(
        [
            "END_MARK",
            "Broken",
            "Judgement",
            "Verdict",
            "VerificationResult",
            "judge_report",
            "program_arguments",
            "run_bf16_rope_verification",
        ]
    )


# --- program_arguments ---


def test_program_arguments_order_and_spelling():
    arguments = program_arguments((3, 2, 4), draws=2, seed=LAST)
    assert arguments == ("3", "2", "4", "2", "18446744073709551615")
    assert type(arguments) is tuple
    assert all(type(argument) is str for argument in arguments)
    assert program_arguments((2048, 32, 64), draws=1, seed=0) == (
        "2048",
        "32",
        "64",
        "1",
        "0",
    )


def test_program_arguments_bounds():
    assert program_arguments((1, 1, 2), draws=1, seed=0) == ("1", "1", "2", "1", "0")
    large = (10**30, 10**30, 2 * 10**30)
    assert program_arguments(large, draws=LAST, seed=LAST) == (
        "1" + "0" * 30,
        "1" + "0" * 30,
        "2" + "0" * 30,
        "18446744073709551615",
        "18446744073709551615",
    )


BAD_DIMS = [
    ([3, 2, 4], "dims"),
    ((3, 4), "dims"),
    ((3, 2, 4, 1), "dims"),
    ((), "dims"),
    (None, "dims"),
    (3, "dims"),
    ((True, 2, 4), r"dims\[0\]"),
    ((3, 0, 4), r"dims\[1\]"),
    ((3, 2, -4), r"dims\[2\]"),
    ((3.0, 2, 4), r"dims\[0\]"),
    ((3, "2", 4), r"dims\[1\]"),
    ((3, 2, 5), r"dims\[2\]"),
    ((10**5000, 2, 4), r"dims\[0\]"),
]
BAD_DRAWS = [0, -1, 2**64, 10**5000, True, 1.0, "1", None]
BAD_SEEDS = [-1, 2**64, 10**5000, 1.5, True, "7", None]
BAD_STARTS = [-1, True, False, 1.0, 0.0, "0", None, 2**53]
BAD_TOLERANCES = [
    (name, value)
    for name in ("rtol", "atol")
    for value in [-1e-9, -1, float("nan"), float("inf"), True, "0.1", None, 10**400]
]


def bad_arguments():
    cases = [("dims", value, match) for value, match in BAD_DIMS]
    cases += [("draws", value, "draws") for value in BAD_DRAWS]
    cases += [("seed", value, "seed") for value in BAD_SEEDS]
    return cases


BAD_ARGUMENTS = bad_arguments()
BAD_IDS = [f"{case[0]}-{n}" for n, case in enumerate(BAD_ARGUMENTS)]


def arguments_with(parameter, value):
    arguments = {"dims": DIMS, "draws": 3, "seed": SEED}
    arguments[parameter] = value
    return arguments


@pytest.mark.parametrize(("parameter", "value", "match"), BAD_ARGUMENTS, ids=BAD_IDS)
def test_program_arguments_refuses(parameter, value, match):
    arguments = arguments_with(parameter, value)
    with pytest.raises(VerificationArgumentError, match=f"^{match}: "):
        program_arguments(
            arguments["dims"], draws=arguments["draws"], seed=arguments["seed"]
        )


def test_program_arguments_refuses_in_the_order_of_the_parameters():
    with pytest.raises(VerificationArgumentError, match="^dims: "):
        program_arguments((3, 4), draws=0, seed=-1)
    with pytest.raises(VerificationArgumentError, match=r"^dims\[2\]: "):
        program_arguments((3, 2, 5), draws=0, seed=-1)
    with pytest.raises(VerificationArgumentError, match=r"^dims\[0\]: "):
        program_arguments((10**5000, 2, 4), draws=0, seed=-1)
    with pytest.raises(VerificationArgumentError, match="^draws: "):
        program_arguments(DIMS, draws=0, seed=-1)
    with pytest.raises(VerificationArgumentError, match="^seed: "):
        program_arguments(DIMS, draws=1, seed=-1)


@pytest.mark.parametrize("missing", ["dims", "draws", "seed"])
def test_program_arguments_has_no_default_for(missing):
    arguments = {"dims": DIMS, "draws": 3, "seed": 7}
    del arguments[missing]
    with pytest.raises(TypeError, match=missing):
        program_arguments(**arguments)


def test_program_arguments_has_no_start():
    with pytest.raises(TypeError, match="start"):
        program_arguments(DIMS, start=0, draws=3, seed=7)


def test_program_arguments_draws_and_seed_are_keyword_only():
    with pytest.raises(TypeError):
        program_arguments(DIMS, 3, 7)
    with pytest.raises(TypeError):
        program_arguments(DIMS, 3, seed=7)
    assert program_arguments(dims=DIMS, draws=3, seed=7) == ("3", "2", "4", "3", "7")


# --- judge_report: pass and fail ---


@pytest.mark.parametrize(
    ("dims", "start"), [(DIMS, 0), (DIMS, START), ((1, 2, 64), 127), ((1, 1, 2), 0)]
)
@pytest.mark.parametrize("draws", [1, 4])
def test_judge_report_passes_rounded_references(dims, start, draws):
    report = passing_report(dims, start, draws, SEED)
    judgement = judge(report, dims, start, draws)
    assert_judged(judgement, Verdict.PASS, [(0, 0)] * draws)


def test_output_equal_to_x_at_row_zero_passes():
    dims = (1, 2, 4)
    outputs = [draw_x(dims, seed=SEED, draw=draw) for draw in range(2)]
    report = report_of(dims, 0, SEED, outputs)
    judgement = judge(report, dims, 0, 2, rtol=0.0, atol=0.0)
    assert_judged(judgement, Verdict.PASS, [(0, 0)] * 2)


def test_output_equal_to_x_off_row_zero_fails():
    outputs = [draw_x(DIMS, seed=SEED, draw=draw) for draw in range(3)]
    judgement = judge(report_of(DIMS, 0, SEED, outputs), start=0)
    assert judgement.verdict is Verdict.FAIL
    assert all(count.failed > 0 for count in judgement.counts)
    assert all(count.non_finite == 0 for count in judgement.counts)


def test_one_element_outside_the_tolerance_fails_its_draw_only():
    outputs = rounded_references(DIMS, START, 3, SEED)
    outputs[1][2, 1, 3] = rounded(np.array([9.0]))[0]
    judgement = judge(report_of(DIMS, START, SEED, outputs))
    assert_judged(judgement, Verdict.FAIL, [(0, 0), (1, 0), (0, 0)])


def test_fill_elements_are_failed_and_non_finite():
    outputs = rounded_references(DIMS, START, 3, SEED)
    outputs[0][0, 0, 0] = NAN
    outputs[2][...] = NAN
    judgement = judge(report_of(DIMS, START, SEED, outputs))
    assert_judged(judgement, Verdict.FAIL, [(1, 1), (0, 0), (24, 24)])


# --- judge_report: broken ---


def bad_forms():
    return {
        "empty": b"",
        "end-mark-alone": END_MARK,
        "one-byte-short": GOOD[:-1],
        "one-byte-long": GOOD + b"\n",
        "no-end-mark": GOOD[:-4],
        "other-end-mark": GOOD[:-4] + b"END\n",
        "first-byte-missing": GOOD[1:],
        "one-draw-more": passing_report(DIMS, START, 4, SEED),
        "another-h": passing_report((3, 3, 4), START, 3, SEED),
        "wrong-check-value-too": report_of(
            DIMS, START, SEED, rounded_references(DIMS, START, 3, SEED), {0}
        )[:-1],
    }


@pytest.mark.parametrize("name", bad_forms())
def test_judge_report_of_another_form_is_broken_before_any_check_value(name, no_build):
    assert_judged_broken(judge(bad_forms()[name]), Broken.REPORT_FORM)


def test_judge_report_takes_the_form_from_dims_and_draws_alone():
    assert_judged_broken(judge(GOOD, draws=2), Broken.REPORT_FORM)
    assert_judged_broken(judge(GOOD, draws=LAST), Broken.REPORT_FORM)
    assert_judged_broken(judge(GOOD, (3, 3, 4)), Broken.REPORT_FORM)
    assert_judged_broken(judge(GOOD, (3, 2**40, 4)), Broken.REPORT_FORM)
    assert_judged_broken(judge(GOOD, (2, 3, 4)), Broken.CHECK_VALUE)
    assert_judged_broken(judge(GOOD, (6, 1, 4)), Broken.CHECK_VALUE)


@pytest.mark.parametrize("draw", [0, 1, 2])
@pytest.mark.parametrize("passing", [True, False])
def test_judge_report_with_a_check_value_that_disagrees_is_broken(passing, draw):
    outputs = rounded_references(DIMS, START, 3, SEED)
    if not passing:
        outputs[0][0, 0, 0] = NAN
    report = report_of(DIMS, START, SEED, outputs, wrong_check={draw})
    assert_judged_broken(judge(report), Broken.CHECK_VALUE)


def test_judge_report_of_another_seed_is_broken():
    report = passing_report(DIMS, START, 3, SEED + 1)
    assert_judged_broken(judge(report), Broken.CHECK_VALUE)


@pytest.mark.parametrize(("made", "judged"), [(START, START + 1), (0, 127), (1, 0)])
def test_judge_report_of_another_start_is_broken(made, judged):
    report = passing_report(DIMS, made, 3, SEED)
    assert len(report) == len(GOOD)
    assert_judged_broken(judge(report, start=judged), Broken.CHECK_VALUE)


def test_judge_report_builds_the_table_once_after_the_form(builds):
    assert_judged(judge(GOOD), Verdict.PASS, [(0, 0)] * 3)
    assert builds == [(DIMS, START)]


# --- judge_report: refusals ---


@pytest.mark.parametrize(("parameter", "value", "match"), BAD_ARGUMENTS, ids=BAD_IDS)
@pytest.mark.parametrize("report", ["good", b"", None], ids=["good", "empty", "none"])
def test_judge_report_refuses_arguments_before_the_report(
    report, parameter, value, match, no_build
):
    arguments = arguments_with(parameter, value)
    report = GOOD if report == "good" else report
    with pytest.raises(VerificationArgumentError, match=f"^{match}: "):
        judge_report(
            report,
            arguments["dims"],
            start=START,
            draws=arguments["draws"],
            seed=arguments["seed"],
            **TOLERANCE,
        )


@pytest.mark.parametrize("start", BAD_STARTS)
@pytest.mark.parametrize("report", ["good", None], ids=["good", "none"])
def test_judge_report_refuses_a_start_before_the_report(report, start, no_build):
    report = GOOD if report == "good" else report
    with pytest.raises(VerificationArgumentError, match="^start: "):
        judge(report, start=start)


def test_judge_report_refuses_a_start_past_the_integer_limit(no_build):
    dims = (1, 1, 2**52)
    judge(b"", dims, start=0, draws=1, seed=0)
    with pytest.raises(VerificationArgumentError, match=r"^start: .*2\*\*53 - 1"):
        judge(b"", dims, start=1, draws=1, seed=0)


@pytest.mark.parametrize(("name", "value"), BAD_TOLERANCES)
@pytest.mark.parametrize("report", ["good", None], ids=["good", "none"])
def test_judge_report_refuses_tolerances_before_the_report(
    report, name, value, no_build
):
    report = GOOD if report == "good" else report
    with pytest.raises(VerificationArgumentError, match=f"^{name}: "):
        judge(report, **{name: value})


@pytest.mark.parametrize(
    "report", [bytearray(GOOD), memoryview(GOOD), GOOD.hex(), None, list(GOOD)]
)
def test_judge_report_refuses_a_report_that_is_not_bytes(report, no_build):
    with pytest.raises(TypeError, match="^report: must be bytes, got ") as caught:
        judge(report)
    assert str(caught.value).endswith(f"got {type(report).__name__}")


def test_judge_report_refuses_in_the_order_of_the_parameters(no_build):
    with pytest.raises(VerificationArgumentError, match="^dims: "):
        judge(None, (3, 4), start=-1, draws=0, rtol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^draws: "):
        judge(None, start=-1, draws=0, rtol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^start: "):
        judge(None, start=-1, rtol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^rtol: "):
        judge(None, rtol=-1.0)


@pytest.mark.parametrize("missing", ["dims", "start", "draws", "seed", "rtol", "atol"])
def test_judge_report_has_no_default_for(missing):
    arguments = {"dims": DIMS, "start": START, "draws": 3, "seed": SEED, **TOLERANCE}
    del arguments[missing]
    with pytest.raises(TypeError, match=missing):
        judge_report(GOOD, **arguments)


def test_judge_report_parameters_are_keyword_only():
    with pytest.raises(TypeError):
        judge_report(GOOD, DIMS, START, 3, SEED, 0.0, 2**-8)
    with pytest.raises(TypeError):
        judge_report(GOOD, DIMS, START, draws=3, seed=SEED, **TOLERANCE)


def test_judge_report_starts_nothing(monkeypatch):
    def refuse(*args, **kwargs):
        pytest.fail("judge_report started a process")

    monkeypatch.setattr("hilclaw.local_run.run", refuse)
    monkeypatch.setattr("subprocess.Popen", refuse)
    assert judge(GOOD) == judge(bytes(bytearray(GOOD)))


# --- run_bf16_rope_verification with a stand-in ---


def test_run_passes_a_report_of_rounded_references(stand_in):
    result = verify(stand_in(GOOD))
    assert_completed(result, Verdict.PASS, [(0, 0)] * 3)
    assert result._fields == ("broken", "verdict", "counts", "run")


@pytest.mark.parametrize(
    ("dims", "start"), [(DIMS, 0), (DIMS, START), ((1, 2, 64), 127)]
)
def test_the_process_gets_the_arguments_and_the_rows(dims, start, stand_in):
    executable = stand_in(passing_report(dims, start, 2, LAST))
    result = verify(executable, dims, start, draws=2, seed=LAST)
    assert_completed(result, Verdict.PASS, [(0, 0)] * 2)
    expected = list(program_arguments(dims, draws=2, seed=LAST))
    call = stand_in.call()
    assert call["argv"] == expected
    assert result.run.command[1:] == (executable[1], *expected)
    assert bytes.fromhex(call["stdin"]) == table_rows(dims, start=start).tobytes()
    assert len(bytes.fromhex(call["stdin"])) == 4 * dims[0] * dims[2]


def test_the_start_is_not_on_the_command_line(stand_in):
    start = 97
    verify(stand_in(passing_report(DIMS, start, 3, SEED)), start=start)
    assert str(start) not in stand_in.call()["argv"]


def test_cwd_and_env_reach_the_process(stand_in, tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    env = {**os.environ, "HILCLAW_TEST_MARK": "handed over"}
    result = verify(stand_in(GOOD), cwd=work, env=env)
    assert_completed(result, Verdict.PASS, [(0, 0)] * 3)
    call = stand_in.call()
    assert os.path.samefile(call["cwd"], work)
    assert call["mark"] == "handed over"


def test_result_holds_the_capture_of_the_runner_without_the_report(stand_in):
    noise = GOOD[:9] + "café\n".encode()
    result = verify(stand_in(GOOD, stderr=noise))
    assert_completed(result, Verdict.PASS, [(0, 0)] * 3)
    assert result.run.stderr == noise
    assert type(result.run.duration_s) is float


def test_run_builds_the_table_once_and_judges_with_it(stand_in, builds):
    result = verify(stand_in(GOOD))
    assert_completed(result, Verdict.PASS, [(0, 0)] * 3)
    assert builds == [(DIMS, START)]


def test_executable_prefix_may_be_a_list(stand_in):
    assert_completed(verify(list(stand_in(GOOD))), Verdict.PASS, [(0, 0)] * 3)


def test_executable_as_one_path_is_the_whole_prefix(tmp_path):
    for executable in (sys.executable, Path(sys.executable)):
        result = verify(executable, cwd=tmp_path)
        assert_broken(result, Broken.EXIT_STATUS)
        assert result.run.command[1:] == ("3", "2", "4", "3", "7")


@pytest.mark.parametrize("stdout", ["good", b"end"], ids=["passing", "other"])
def test_timeout_is_broken_whatever_was_written(stdout, stand_in):
    stdout = GOOD if stdout == "good" else stdout
    result = verify(stand_in(stdout, sleep=30), timeout_s=2)
    assert_broken(result, Broken.TIMEOUT)
    assert result.run.timed_out is True


@pytest.mark.parametrize("status", [5, 1])
@pytest.mark.parametrize("stdout", ["good", b""], ids=["passing", "empty"])
def test_non_zero_exit_is_broken_whatever_was_written(stdout, status, stand_in):
    stdout = GOOD if stdout == "good" else stdout
    result = verify(stand_in(stdout, status=status, stderr=b"a line\n"))
    assert_broken(result, Broken.EXIT_STATUS)
    assert result.run.returncode == status
    assert result.run.stderr == b"a line\n"


@pytest.mark.skipif(os.name == "nt", reason="POSIX signals")
def test_death_by_signal_after_a_passing_report_is_broken(stand_in):
    result = verify(stand_in(GOOD, kill=signal.SIGKILL))
    assert_broken(result, Broken.EXIT_STATUS)
    assert result.run.returncode == -signal.SIGKILL


def test_process_that_does_not_read_its_input_gives_a_result(stand_in):
    dims, start = (100, 1, 64), 28
    report = passing_report(dims, start, 1, SEED)
    result = verify(stand_in(report, skip_stdin=True), dims, start, draws=1)
    assert_completed(result, Verdict.PASS, [(0, 0)])
    assert stand_in.call()["stdin"] is None
    result = verify(stand_in(b"", status=5, skip_stdin=True), dims, start, draws=1)
    assert_broken(result, Broken.EXIT_STATUS)


@pytest.mark.parametrize(
    "name", ["wrong-form", "wrong-check-value", "another-start", "fail"]
)
def test_run_and_judge_report_agree(name, stand_in):
    outputs = rounded_references(DIMS, START, 3, SEED)
    outputs[1][0, 0, 0] = NAN
    report = {
        "wrong-form": GOOD[:-1],
        "wrong-check-value": report_of(DIMS, START, SEED, outputs, {2}),
        "another-start": passing_report(DIMS, START + 1, 3, SEED),
        "fail": report_of(DIMS, START, SEED, outputs),
    }[name]
    result = verify(stand_in(report))
    assert result[:3] == judge(report)
    assert result.run.returncode == 0
    if name != "fail":
        assert result.broken is not None


@pytest.mark.parametrize(("parameter", "value", "match"), BAD_ARGUMENTS, ids=BAD_IDS)
def test_bad_arguments_raise_and_start_nothing(
    parameter, value, match, stand_in, no_build
):
    arguments = arguments_with(parameter, value)
    with pytest.raises(VerificationArgumentError, match=f"^{match}: "):
        run_bf16_rope_verification(
            stand_in(GOOD),
            arguments["dims"],
            start=START,
            draws=arguments["draws"],
            seed=arguments["seed"],
            **TOLERANCE,
            timeout_s=TIMEOUT,
        )
    assert not stand_in.started


@pytest.mark.parametrize("start", [*BAD_STARTS, 2**60])
def test_bad_starts_raise_and_start_nothing(start, stand_in, no_build):
    with pytest.raises(VerificationArgumentError, match="^start: "):
        verify(stand_in(GOOD), start=start)
    assert not stand_in.started


@pytest.mark.parametrize(("name", "value"), BAD_TOLERANCES)
def test_bad_tolerances_raise_and_start_nothing(name, value, stand_in, no_build):
    with pytest.raises(VerificationArgumentError, match=f"^{name}: "):
        verify(stand_in(GOOD), **{name: value})
    assert not stand_in.started


def test_run_refuses_in_the_order_of_the_parameters(no_build):
    with pytest.raises(VerificationArgumentError, match="^dims: "):
        verify((), (3, 4), start=-1, seed=-1, rtol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^seed: "):
        verify((), start=-1, seed=-1, rtol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^start: "):
        verify((), start=-1, rtol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^atol: "):
        verify(7, atol=-1.0, timeout_s=0)
    with pytest.raises(TypeError):
        verify(7, timeout_s=0)
    with pytest.raises(ValueError, match="empty"):
        verify((), timeout_s=0)


@pytest.mark.parametrize("executable", [(), []])
def test_empty_executable_prefix(executable, no_build):
    with pytest.raises(ValueError, match="empty"):
        verify(executable)


@pytest.mark.parametrize("executable", [7, None, 1.5])
def test_executable_of_the_wrong_type(executable, no_build):
    with pytest.raises(TypeError):
        verify(executable)


@pytest.mark.parametrize(
    "missing", ["dims", "start", "draws", "seed", "rtol", "atol", "timeout_s"]
)
def test_run_has_no_default_for(missing, stand_in):
    arguments = {"dims": DIMS, "start": START, "draws": 3, "seed": SEED}
    arguments |= {**TOLERANCE, "timeout_s": TIMEOUT}
    del arguments[missing]
    with pytest.raises(TypeError, match=missing):
        run_bf16_rope_verification(stand_in(GOOD), **arguments)
    assert not stand_in.started


def test_run_parameters_are_keyword_only(stand_in):
    with pytest.raises(TypeError):
        run_bf16_rope_verification(
            stand_in(GOOD), DIMS, START, 3, SEED, 0.0, 2**-8, TIMEOUT
        )
    assert not stand_in.started


def test_executable_that_does_not_exist():
    with pytest.raises(ProgramNotFoundError):
        verify("hilclaw-no-such-bf16-rope-verification-executable")


def test_time_limit_errors_are_those_of_the_runner(stand_in):
    with pytest.raises(ValueError, match="timeout_s"):
        verify(stand_in(GOOD), timeout_s=0)
    assert not stand_in.started


# --- real clang ---

BUILD_TIMEOUT = 120
STRICT = ("-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2")

KERNEL = """\
#include <stddef.h>
#include <stdint.h>
#include <string.h>

static float widened(uint16_t pattern)
{
    uint32_t bits = (uint32_t)pattern << 16;
    float value;
    memcpy(&value, &bits, sizeof value);
    return value;
}

static uint16_t rounded(float value)
{
    uint32_t bits;
    memcpy(&bits, &value, sizeof bits);
    return (uint16_t)((bits + UINT32_C(0x7FFF) + ((bits >> 16) & 1)) >> 16);
}

@SIGNATURE@
{
    (void)widened;
    (void)rounded;
    (void)freqs_cis;
@BODY@
}
"""

KERNELS = {
    "conforming": """\
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < h; j++)
            for (size_t p = 0; p < d / 2; p++) {
                size_t e = (i * h + j) * d + 2 * p;
                float c = freqs_cis[i * d + 2 * p], s = freqs_cis[i * d + 2 * p + 1];
                float x0 = widened(x[e]), x1 = widened(x[e + 1]);
                out[e] = rounded(x0 * c - x1 * s);
                out[e + 1] = rounded(x0 * s + x1 * c);
            }""",
    "copy-x": """\
    for (size_t i = 0; i < m * h * d; i++)
        out[i] = x[i];""",
}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    if os.name != "posix":
        pytest.skip("a verification executable needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    directory = tmp_path_factory.mktemp("bf16_rope_verification")
    signature = rope_bf16_contract.PROTOTYPE.removesuffix(";")
    paths = {}
    for name, body in KERNELS.items():
        source = directory / f"{name}.c"
        text = KERNEL.replace("@SIGNATURE@", signature).replace("@BODY@", body)
        source.write_text(text, encoding="ascii", newline="\n")
        output = directory / name
        result = build_bf16_verification_executable(
            "rope", source, output, timeout_s=BUILD_TIMEOUT, flags=STRICT
        )
        assert result.ok, result.log
        paths[name] = output
    return paths


@pytest.mark.parametrize(("dims", "start"), [((3, 2, 4), 0), ((1, 2, 64), 127)])
def test_real_clang_conforming_kernel_passes(built, dims, start):
    result = verify(built["conforming"], dims, start, draws=2)
    assert_completed(result, Verdict.PASS, [(0, 0)] * 2)
    assert result.run.command[0] == str(built["conforming"])


def test_real_clang_copying_kernel_fails(built):
    result = verify(built["copy-x"], (3, 2, 4), 0, draws=2)
    assert result.broken is None
    assert result.verdict is Verdict.FAIL
    assert all(count.failed > 0 for count in result.counts)
