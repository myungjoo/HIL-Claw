import json
import os
import shutil
import signal
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

import hilclaw.harness
from hilclaw import clang_build
from hilclaw.harness.verification import (
    END_MARK,
    Broken,
    Judgement,
    Verdict,
    VerificationResult,
    judge_report,
    program_arguments,
    run_verification,
)
from hilclaw.harness.verification_arrays import (
    Counts,
    VerificationArgumentError,
    check_value,
    draw_inputs,
    reference,
)
from hilclaw.local_run import ProgramNotFoundError, RunResult

STAND_IN = """\
import json, os, sys, time
from pathlib import Path
here = Path(__file__).parent
plan = json.loads((here / "plan.json").read_text(encoding="utf-8"))
call = {"argv": sys.argv[1:], "cwd": os.getcwd(), "mark": os.environ.get("HILCLAW_TEST_MARK")}
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
SHAPE = (3, 4, 5)
SEED = 7
LAST = 2**64 - 1
# Test values, not tolerances of the harness.
TOLERANCE = {"rtol": 1e-5, "atol": 1e-6}
# For this seed the product of the 1 x 1 x 1 draw is exact in binary32.
EXACT_SEED = 302510

NOT_AN_INT = [1.0, "1", True, None]
BAD_ARGUMENTS = (
    [(name, value) for name in "mkn" for value in [0, -1, 10**5000, *NOT_AN_INT]]
    + [("draws", value) for value in [0, -1, 2**64, 10**5000, True, 1.0, "1", None]]
    + [("seed", value) for value in [-1, 2**64, 10**5000, 1.5, True, "7", None]]
)
BAD_TOLERANCES = [
    (name, value)
    for name in ("rtol", "atol")
    for value in [-1e-9, -1, float("nan"), float("inf"), -float("inf"), True, "0.1"]
    + [None, 10**400]
]


def ids(pairs):
    return [
        f"{name}-{type(value).__name__}-{position}"
        for position, (name, value) in enumerate(pairs)
    ]


def rounded_references(m, k, n, draws, seed):
    outputs = []
    for draw in range(draws):
        a, b = draw_inputs(m, k, n, seed=seed, draw=draw)
        outputs.append(reference(a, b).astype(np.float32))
    return outputs


def report_of(m, k, n, seed, outputs, wrong_check=()):
    parts = []
    for draw, output in enumerate(outputs):
        value = check_value(*draw_inputs(m, k, n, seed=seed, draw=draw))
        if draw in wrong_check:
            value ^= 1
        parts.append(struct.pack("=I", value))
        parts.append(np.ascontiguousarray(output, dtype=np.float32).tobytes())
    return b"".join(parts) + END_MARK


def passing_report(m, k, n, draws, seed):
    return report_of(m, k, n, seed, rounded_references(m, k, n, draws, seed))


GOOD = passing_report(*SHAPE, 3, SEED)
BLOCK = 4 + 4 * 3 * 5


class StandIn:
    def __init__(self, directory):
        self.directory = directory
        self.record = directory / "started.json"

    def __call__(self, stdout=b"", *, status=0, stderr=b"", sleep=0, kill=0):
        plan = {
            "stdout": stdout.hex(),
            "status": status,
            "stderr": stderr.hex(),
            "sleep": sleep,
            "signal": kill,
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


def verify(executable, shape=SHAPE, draws=3, seed=SEED, **changes):
    m, k, n = shape
    arguments = {"m": m, "k": k, "n": n, "draws": draws, "seed": seed}
    arguments |= {**TOLERANCE, "timeout_s": TIMEOUT, **changes}
    return run_verification(executable, **arguments)


def assert_completed(result, verdict, counts):
    assert isinstance(result, VerificationResult)
    assert result.broken is None
    assert result.verdict is verdict
    assert type(result.counts) is tuple
    assert all(type(count) is Counts for count in result.counts)
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


@pytest.mark.parametrize("draws", [1, 3])
def test_report_of_rounded_references_passes(draws, stand_in):
    result = verify(stand_in(passing_report(*SHAPE, draws, SEED)), draws=draws)
    assert_completed(result, Verdict.PASS, [(0, 0)] * draws)
    assert result._fields == ("broken", "verdict", "counts", "run")


@pytest.mark.parametrize("seed", [0, LAST])
def test_the_process_gets_exactly_the_five_arguments(seed, stand_in):
    executable = stand_in(passing_report(*SHAPE, 2, seed))
    result = verify(executable, draws=2, seed=seed)
    assert_completed(result, Verdict.PASS, [(0, 0)] * 2)
    expected = ["3", "4", "5", "2", str(seed)]
    assert stand_in.call()["argv"] == expected
    assert result.run.command[1:] == (executable[1], *expected)
    assert os.path.samefile(result.run.command[0], sys.executable)


def test_cwd_and_env_reach_the_process(stand_in, tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    env = {**os.environ, "HILCLAW_TEST_MARK": "handed over"}
    result = verify(stand_in(passing_report(*SHAPE, 3, SEED)), cwd=work, env=env)
    assert_completed(result, Verdict.PASS, [(0, 0)] * 3)
    call = stand_in.call()
    assert os.path.samefile(call["cwd"], work)
    assert call["mark"] == "handed over"


def test_no_environment_variable_is_set_by_default(stand_in, monkeypatch):
    monkeypatch.setenv("HILCLAW_TEST_MARK", "inherited")
    verify(stand_in(passing_report(*SHAPE, 3, SEED)))
    call = stand_in.call()
    assert call["mark"] == "inherited"
    assert os.path.samefile(call["cwd"], os.getcwd())


def test_result_holds_the_capture_of_the_runner_without_the_report(stand_in):
    report = passing_report(*SHAPE, 3, SEED)
    noise = report_of(*SHAPE, SEED, [np.zeros((3, 5))] * 3) + "café\n".encode()
    result = verify(stand_in(report, stderr=noise))
    assert_completed(result, Verdict.PASS, [(0, 0)] * 3)
    assert result.run.stderr == noise
    assert result.run.command[2:] == program_arguments(m=3, k=4, n=5, draws=3, seed=7)
    assert type(result.run.duration_s) is float
    assert result.run.duration_s > 0


def test_executable_as_one_path_is_the_whole_prefix(tmp_path):
    for executable in (sys.executable, Path(sys.executable)):
        result = verify(executable, cwd=tmp_path)
        assert_broken(result, Broken.EXIT_STATUS)
        assert result.run.command[1:] == ("3", "4", "5", "3", "7")
        assert result.run.returncode != 0
        assert result.run.stderr


def test_executable_prefix_may_be_a_list(stand_in):
    result = verify(list(stand_in(passing_report(*SHAPE, 3, SEED))))
    assert_completed(result, Verdict.PASS, [(0, 0)] * 3)


def test_program_arguments_order_and_spelling():
    arguments = program_arguments(m=2048, k=1, n=96, draws=3, seed=7)
    assert arguments == ("2048", "1", "96", "3", "7")
    assert type(arguments) is tuple
    assert all(type(argument) is str for argument in arguments)


def test_program_arguments_bounds():
    assert program_arguments(m=1, k=1, n=1, draws=1, seed=0) == ("1",) * 4 + ("0",)
    large = program_arguments(m=10**30, k=2**64, n=7, draws=LAST, seed=LAST)
    assert large == (
        "1" + "0" * 30,
        "18446744073709551616",
        "7",
        "18446744073709551615",
        "18446744073709551615",
    )


def test_one_element_outside_the_tolerance_fails_the_run(stand_in):
    outputs = rounded_references(*SHAPE, 3, SEED)
    outputs[1][2, 4] += np.float32(0.25)
    result = verify(stand_in(report_of(*SHAPE, SEED, outputs)))
    assert_completed(result, Verdict.FAIL, [(0, 0), (1, 0), (0, 0)])


def test_several_failing_draws_are_counted_apart(stand_in):
    outputs = rounded_references(*SHAPE, 3, SEED)
    outputs[0][0, :] = 9.0
    outputs[2][:, 0] = -9.0
    result = verify(stand_in(report_of(*SHAPE, SEED, outputs)))
    assert_completed(result, Verdict.FAIL, [(5, 0), (0, 0), (3, 0)])


def test_non_finite_outputs_fail_and_are_counted(stand_in):
    outputs = rounded_references(*SHAPE, 3, SEED)
    outputs[0][1, 1] = np.nan
    outputs[0][2, 2] = np.inf
    outputs[0][0, 0] = 70.0
    outputs[2][0, 3] = -np.inf
    result = verify(stand_in(report_of(*SHAPE, SEED, outputs)), rtol=1.0, atol=1.0)
    assert_completed(result, Verdict.FAIL, [(3, 2), (0, 0), (1, 1)])


def test_unwritten_outputs_fail_in_every_draw(stand_in):
    fill = np.full(3 * 5, 0x7FC00000, dtype=np.uint32).view(np.float32)
    report = report_of(*SHAPE, SEED, [fill.reshape(3, 5)] * 3)
    result = verify(stand_in(report))
    assert_completed(result, Verdict.FAIL, [(15, 15)] * 3)


def test_zero_tolerance_passes_an_output_equal_to_the_reference(stand_in):
    a, b = draw_inputs(1, 1, 1, seed=EXACT_SEED, draw=0)
    exact = reference(a, b)
    output = exact.astype(np.float32)
    assert output.astype(np.float64) == exact
    shape = (1, 1, 1)
    report = report_of(*shape, EXACT_SEED, [output])
    result = verify(stand_in(report), shape, 1, EXACT_SEED, rtol=0.0, atol=0.0)
    assert_completed(result, Verdict.PASS, [(0, 0)])
    result = verify(stand_in(report), shape, 1, EXACT_SEED, rtol=0, atol=0)
    assert_completed(result, Verdict.PASS, [(0, 0)])
    off = np.nextafter(output, np.float32(2.0))
    report = report_of(*shape, EXACT_SEED, [off])
    result = verify(stand_in(report), shape, 1, EXACT_SEED, rtol=0.0, atol=0.0)
    assert_completed(result, Verdict.FAIL, [(1, 0)])


def test_integer_tolerances(stand_in):
    outputs = [np.zeros((3, 5), dtype=np.float32)] * 3
    executable = stand_in(report_of(*SHAPE, SEED, outputs))
    assert_completed(verify(executable, rtol=1, atol=0), Verdict.PASS, [(0, 0)] * 3)
    assert_completed(verify(executable, rtol=0, atol=4), Verdict.PASS, [(0, 0)] * 3)
    assert_completed(verify(executable, rtol=0, atol=0), Verdict.FAIL, [(15, 0)] * 3)


@pytest.mark.parametrize("shape", [(1, 4, 5), (3, 1, 5), (3, 4, 1), (1, 1, 1)])
def test_shapes_with_a_dimension_of_one(shape, stand_in):
    m, _, n = shape
    result = verify(stand_in(passing_report(*shape, 2, SEED)), shape, 2)
    assert_completed(result, Verdict.PASS, [(0, 0)] * 2)
    outputs = rounded_references(*shape, 2, SEED)
    outputs[1][m - 1, n - 1] = 9.0
    result = verify(stand_in(report_of(*shape, SEED, outputs)), shape, 2)
    assert_completed(result, Verdict.FAIL, [(0, 0), (1, 0)])


@pytest.mark.parametrize("stdout", [GOOD, b"end"], ids=["passing", "other"])
def test_timeout_is_broken_whatever_was_written(stdout, stand_in):
    result = verify(stand_in(stdout, sleep=30), timeout_s=2)
    assert_broken(result, Broken.TIMEOUT)
    assert result.run.timed_out is True
    assert result.run.returncode is None


@pytest.mark.parametrize("stdout", [GOOD, b"end"], ids=["passing", "other"])
def test_non_zero_exit_is_broken_whatever_was_written(stdout, stand_in):
    result = verify(stand_in(stdout, status=3, stderr=b"a line\n"))
    assert_broken(result, Broken.EXIT_STATUS)
    assert result.run.returncode == 3
    assert result.run.stderr == b"a line\n"


@pytest.mark.skipif(os.name == "nt", reason="POSIX signals")
def test_death_by_signal_after_a_passing_report_is_broken(stand_in):
    report = passing_report(*SHAPE, 3, SEED)
    result = verify(stand_in(report, kill=signal.SIGKILL))
    assert_broken(result, Broken.EXIT_STATUS)
    assert result.run.returncode == -signal.SIGKILL


BAD_FORMS = {
    "empty": b"",
    "end-mark-alone": END_MARK,
    "first-draw-only": GOOD[:BLOCK],
    "first-draw-and-end-mark": GOOD[:BLOCK] + END_MARK,
    "no-end-mark": GOOD[:-4],
    "one-byte-short": GOOD[:-1],
    "first-byte-missing": GOOD[1:],
    "one-byte-long": GOOD + b"\n",
    "byte-before": b"\n" + GOOD,
    "second-end-mark": GOOD + END_MARK,
    "one-draw-more": passing_report(*SHAPE, 4, SEED),
    "other-end-mark": GOOD[:-4] + b"END\n",
    "end-mark-without-lf": GOOD[:-4] + b"end\0",
    "shifted-end-mark": GOOD[:-5] + END_MARK + b"\n",
    "exchanged-m-and-k": passing_report(4, 3, 5, 3, SEED),
    "wrong-check-value-too": report_of(
        *SHAPE, SEED, rounded_references(*SHAPE, 3, SEED), wrong_check={0}
    )[:-1],
}


@pytest.mark.parametrize("name", BAD_FORMS)
def test_output_of_another_form_is_broken(name, stand_in):
    result = verify(stand_in(BAD_FORMS[name]))
    assert_broken(result, Broken.REPORT_FORM)
    assert result.run.returncode == 0


def test_the_form_follows_from_the_parameters_alone(stand_in):
    executable = stand_in(GOOD)
    assert_completed(verify(executable), Verdict.PASS, [(0, 0)] * 3)
    assert_broken(verify(executable, draws=2), Broken.REPORT_FORM)
    assert_broken(verify(executable, draws=LAST), Broken.REPORT_FORM)
    assert_broken(verify(executable, (3, 2, 5)), Broken.CHECK_VALUE)
    assert_broken(verify(executable, (2**40, 4, 2**40)), Broken.REPORT_FORM)


@pytest.mark.parametrize("draw", [0, 2])
@pytest.mark.parametrize("passing", [True, False])
def test_check_value_that_disagrees_is_broken(draw, passing, stand_in):
    outputs = rounded_references(*SHAPE, 3, SEED)
    if not passing:
        outputs[0][0, 0] = np.nan
        outputs[2][1, 1] = 9.0
    report = report_of(*SHAPE, SEED, outputs, wrong_check={draw})
    result = verify(stand_in(report))
    assert_broken(result, Broken.CHECK_VALUE)
    assert result.run.returncode == 0


def test_report_of_another_seed_is_broken(stand_in):
    result = verify(stand_in(passing_report(*SHAPE, 3, SEED + 1)))
    assert_broken(result, Broken.CHECK_VALUE)


def test_broken_conditions_and_verdicts_are_closed_sets():
    assert [condition.name for condition in Broken] == [
        "TIMEOUT",
        "EXIT_STATUS",
        "REPORT_FORM",
        "CHECK_VALUE",
    ]
    assert [verdict.name for verdict in Verdict] == ["PASS", "FAIL"]


@pytest.mark.parametrize(("name", "value"), BAD_ARGUMENTS, ids=ids(BAD_ARGUMENTS))
def test_program_arguments_refuses(name, value):
    arguments = {"m": 3, "k": 4, "n": 5, "draws": 3, "seed": 7, name: value}
    with pytest.raises(VerificationArgumentError, match=f"^{name}: "):
        program_arguments(**arguments)


@pytest.mark.parametrize(("name", "value"), BAD_ARGUMENTS, ids=ids(BAD_ARGUMENTS))
def test_bad_arguments_raise_and_start_nothing(name, value, stand_in):
    arguments = {"m": 3, "k": 4, "n": 5, "draws": 3, "seed": 7, name: value}
    arguments |= {**TOLERANCE, "timeout_s": TIMEOUT}
    with pytest.raises(VerificationArgumentError, match=f"^{name}: "):
        run_verification(stand_in(GOOD), **arguments)
    assert not stand_in.started


@pytest.mark.parametrize(("name", "value"), BAD_TOLERANCES, ids=ids(BAD_TOLERANCES))
def test_bad_tolerances_raise_and_start_nothing(name, value, stand_in):
    with pytest.raises(VerificationArgumentError, match=f"^{name}: "):
        verify(stand_in(GOOD), **{name: value})
    assert not stand_in.started


def test_arguments_are_refused_before_the_tolerance_and_the_executable():
    with pytest.raises(VerificationArgumentError, match="^seed: "):
        verify((), seed=-1, rtol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^rtol: "):
        verify((), rtol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^atol: "):
        verify(7, atol=-1.0, timeout_s=0)
    with pytest.raises(ValueError, match="empty"):
        verify((), timeout_s=0)


def test_argument_error_is_the_one_of_the_array_side():
    with pytest.raises(ValueError) as caught:
        program_arguments(m=0, k=1, n=1, draws=1, seed=0)
    assert type(caught.value) is VerificationArgumentError
    assert "int 0" in str(caught.value)


@pytest.mark.parametrize("missing", ["rtol", "atol", "seed", "draws", "timeout_s", "m"])
def test_run_verification_has_no_default_for(missing, stand_in):
    arguments = {"m": 3, "k": 4, "n": 5, "draws": 3, "seed": 7}
    arguments |= {**TOLERANCE, "timeout_s": TIMEOUT}
    del arguments[missing]
    with pytest.raises(TypeError, match=missing):
        run_verification(stand_in(GOOD), **arguments)
    assert not stand_in.started


@pytest.mark.parametrize("missing", ["m", "k", "n", "draws", "seed"])
def test_program_arguments_has_no_default_for(missing):
    arguments = {"m": 3, "k": 4, "n": 5, "draws": 3, "seed": 7}
    del arguments[missing]
    with pytest.raises(TypeError, match=missing):
        program_arguments(**arguments)


def test_parameters_are_keyword_only(stand_in):
    with pytest.raises(TypeError):
        run_verification(stand_in(GOOD), 3, 4, 5, 3, 7, 1e-5, 1e-6, TIMEOUT)
    with pytest.raises(TypeError):
        program_arguments(3, 4, 5, 3, 7)
    assert not stand_in.started


@pytest.mark.parametrize(
    ("timeout_s", "error"),
    [(0, ValueError), (-1, ValueError), (float("inf"), ValueError)]
    + [("60", TypeError), (None, TypeError), (True, TypeError)],
)
def test_time_limit_errors_are_those_of_the_runner(timeout_s, error, stand_in):
    with pytest.raises(error, match="timeout_s"):
        verify(stand_in(GOOD), timeout_s=timeout_s)
    assert not stand_in.started


@pytest.mark.parametrize(
    "executable",
    ["hilclaw-no-such-verification-executable", Path("no-such-directory") / "verify"],
)
def test_executable_that_does_not_exist(executable):
    with pytest.raises(ProgramNotFoundError):
        verify(executable)


@pytest.mark.parametrize("executable", [(), []])
def test_empty_executable_prefix(executable):
    with pytest.raises(ValueError, match="empty"):
        verify(executable)


@pytest.mark.parametrize("executable", [7, None, 1.5])
def test_executable_of_the_wrong_type(executable):
    with pytest.raises(TypeError):
        verify(executable)


def test_prefix_part_of_the_wrong_type_starts_nothing(stand_in):
    program, script = stand_in(GOOD)
    with pytest.raises(TypeError):
        verify((program, Path(script)))
    assert not stand_in.started


def judge(report, shape=SHAPE, draws=3, seed=SEED, **changes):
    m, k, n = shape
    arguments = {"m": m, "k": k, "n": n, "draws": draws, "seed": seed}
    return judge_report(report, **{**arguments, **TOLERANCE, **changes})


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


@pytest.mark.parametrize("draws", [1, 3])
def test_judge_report_passes_a_report_of_rounded_references(draws):
    judgement = judge(passing_report(*SHAPE, draws, SEED), draws=draws)
    assert_judged(judgement, Verdict.PASS, [(0, 0)] * draws)
    assert judgement._fields == ("broken", "verdict", "counts")


@pytest.mark.parametrize("seed", [0, LAST])
def test_judge_report_takes_the_whole_range_of_seeds(seed):
    judgement = judge(passing_report(*SHAPE, 2, seed), draws=2, seed=seed)
    assert_judged(judgement, Verdict.PASS, [(0, 0)] * 2)


def test_judge_report_fails_one_element_outside_the_tolerance():
    outputs = rounded_references(*SHAPE, 3, SEED)
    outputs[1][2, 4] += np.float32(0.25)
    judgement = judge(report_of(*SHAPE, SEED, outputs))
    assert_judged(judgement, Verdict.FAIL, [(0, 0), (1, 0), (0, 0)])


def test_judge_report_counts_several_failing_draws_apart():
    outputs = rounded_references(*SHAPE, 3, SEED)
    outputs[0][0, :] = 9.0
    outputs[2][:, 0] = -9.0
    judgement = judge(report_of(*SHAPE, SEED, outputs))
    assert_judged(judgement, Verdict.FAIL, [(5, 0), (0, 0), (3, 0)])


def test_judge_report_fails_and_counts_non_finite_outputs():
    outputs = rounded_references(*SHAPE, 3, SEED)
    outputs[0][1, 1] = np.nan
    outputs[0][2, 2] = np.inf
    outputs[0][0, 0] = 70.0
    outputs[2][0, 3] = -np.inf
    judgement = judge(report_of(*SHAPE, SEED, outputs), rtol=1.0, atol=1.0)
    assert_judged(judgement, Verdict.FAIL, [(3, 2), (0, 0), (1, 1)])


def test_judge_report_with_a_zero_tolerance():
    a, b = draw_inputs(1, 1, 1, seed=EXACT_SEED, draw=0)
    output = reference(a, b).astype(np.float32)
    shape = (1, 1, 1)
    report = report_of(*shape, EXACT_SEED, [output])
    for zero in (0.0, 0):
        judgement = judge(report, shape, 1, EXACT_SEED, rtol=zero, atol=zero)
        assert_judged(judgement, Verdict.PASS, [(0, 0)])
    off = np.nextafter(output, np.float32(2.0))
    report = report_of(*shape, EXACT_SEED, [off])
    judgement = judge(report, shape, 1, EXACT_SEED, rtol=0.0, atol=0.0)
    assert_judged(judgement, Verdict.FAIL, [(1, 0)])


def test_judge_report_with_integer_tolerances():
    report = report_of(*SHAPE, SEED, [np.zeros((3, 5), dtype=np.float32)] * 3)
    assert_judged(judge(report, rtol=1, atol=0), Verdict.PASS, [(0, 0)] * 3)
    assert_judged(judge(report, rtol=0, atol=4), Verdict.PASS, [(0, 0)] * 3)
    assert_judged(judge(report, rtol=0, atol=0), Verdict.FAIL, [(15, 0)] * 3)


@pytest.mark.parametrize("shape", [(1, 4, 5), (3, 1, 5), (3, 4, 1), (1, 1, 1)])
def test_judge_report_of_shapes_with_a_dimension_of_one(shape):
    m, _, n = shape
    judgement = judge(passing_report(*shape, 2, SEED), shape, 2)
    assert_judged(judgement, Verdict.PASS, [(0, 0)] * 2)
    outputs = rounded_references(*shape, 2, SEED)
    outputs[1][m - 1, n - 1] = 9.0
    judgement = judge(report_of(*shape, SEED, outputs), shape, 2)
    assert_judged(judgement, Verdict.FAIL, [(0, 0), (1, 0)])


@pytest.mark.parametrize("name", BAD_FORMS)
def test_judge_report_of_another_form_is_broken(name):
    assert_judged_broken(judge(BAD_FORMS[name]), Broken.REPORT_FORM)


def test_judge_report_takes_the_form_from_the_parameters_alone():
    assert_judged(judge(GOOD), Verdict.PASS, [(0, 0)] * 3)
    assert_judged_broken(judge(GOOD, draws=2), Broken.REPORT_FORM)
    assert_judged_broken(judge(GOOD, draws=LAST), Broken.REPORT_FORM)
    assert_judged_broken(judge(GOOD, (3, 2, 5)), Broken.CHECK_VALUE)
    assert_judged_broken(judge(GOOD, (2**40, 4, 2**40)), Broken.REPORT_FORM)


def test_judge_report_tests_the_form_before_any_check_value():
    outputs = rounded_references(*SHAPE, 3, SEED)
    report = report_of(*SHAPE, SEED, outputs, wrong_check={0, 1, 2})
    assert_judged_broken(judge(report), Broken.CHECK_VALUE)
    assert_judged_broken(judge(report[:-4] + b"END\n"), Broken.REPORT_FORM)
    assert_judged_broken(judge(report + b"\n"), Broken.REPORT_FORM)


@pytest.mark.parametrize("draw", [0, 1, 2])
@pytest.mark.parametrize("passing", [True, False])
def test_judge_report_with_a_check_value_that_disagrees_is_broken(draw, passing):
    outputs = rounded_references(*SHAPE, 3, SEED)
    if not passing:
        outputs[0][0, 0] = np.nan
        outputs[2][1, 1] = 9.0
    report = report_of(*SHAPE, SEED, outputs, wrong_check={draw})
    assert_judged_broken(judge(report), Broken.CHECK_VALUE)


def test_judge_report_of_another_seed_is_broken():
    report = passing_report(*SHAPE, 3, SEED + 1)
    assert_judged_broken(judge(report), Broken.CHECK_VALUE)


@pytest.mark.parametrize(("name", "value"), BAD_ARGUMENTS, ids=ids(BAD_ARGUMENTS))
@pytest.mark.parametrize("report", [GOOD, b"", None], ids=["good", "empty", "none"])
def test_judge_report_refuses_arguments_before_the_report(report, name, value):
    with pytest.raises(VerificationArgumentError, match=f"^{name}: "):
        judge(report, **{name: value})


@pytest.mark.parametrize(("name", "value"), BAD_TOLERANCES, ids=ids(BAD_TOLERANCES))
@pytest.mark.parametrize("report", [GOOD, b"", None], ids=["good", "empty", "none"])
def test_judge_report_refuses_tolerances_before_the_report(report, name, value):
    with pytest.raises(VerificationArgumentError, match=f"^{name}: "):
        judge(report, **{name: value})


def test_judge_report_refuses_arguments_before_the_tolerance():
    with pytest.raises(VerificationArgumentError, match="^seed: "):
        judge(None, seed=-1, rtol=-1.0, atol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^rtol: "):
        judge(None, rtol=-1.0, atol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^atol: "):
        judge(None, atol=-1.0)


class BytesSubclass(bytes):
    pass


@pytest.mark.parametrize(
    "report",
    [None, GOOD.decode("latin-1"), 0, len(GOOD), list(GOOD), (GOOD,)]
    + [
        bytearray(GOOD),
        memoryview(GOOD),
        BytesSubclass(GOOD),
        np.frombuffer(GOOD, dtype=np.uint8),
    ],
    ids=lambda report: type(report).__name__,
)
def test_judge_report_refuses_a_report_that_is_not_bytes(report):
    with pytest.raises(TypeError, match="^report: must be bytes, got ") as caught:
        judge(report)
    assert str(caught.value).endswith(f"got {type(report).__name__}")


@pytest.mark.parametrize("missing", ["m", "k", "n", "draws", "seed", "rtol", "atol"])
def test_judge_report_has_no_default_for(missing):
    arguments = {"m": 3, "k": 4, "n": 5, "draws": 3, "seed": 7, **TOLERANCE}
    del arguments[missing]
    with pytest.raises(TypeError, match=missing):
        judge_report(GOOD, **arguments)


def test_judge_report_parameters_are_keyword_only():
    with pytest.raises(TypeError):
        judge_report(GOOD, 3, 4, 5, 3, 7, 1e-5, 1e-6)
    with pytest.raises(TypeError):
        judge_report(GOOD, 3, 4, 5, draws=3, seed=7, **TOLERANCE)
    with pytest.raises(TypeError, match="report"):
        judge_report(m=3, k=4, n=5, draws=3, seed=7, **TOLERANCE)


FAILING = rounded_references(*SHAPE, 3, SEED)
FAILING[1][0, 0] = np.inf
JUDGED = {
    "pass": GOOD,
    "fail": report_of(*SHAPE, SEED, FAILING),
    "wrong-form": GOOD[:-1],
    "empty": b"",
    "wrong-check-value": report_of(*SHAPE, SEED, FAILING, wrong_check={2}),
    "another-seed": passing_report(*SHAPE, 3, SEED + 1),
}


@pytest.mark.parametrize("name", JUDGED)
def test_judge_report_starts_nothing_and_depends_on_its_arguments_alone(
    name, monkeypatch
):
    def refuse(*args, **kwargs):
        pytest.fail("judge_report started a process")

    monkeypatch.setattr("hilclaw.local_run.run", refuse)
    monkeypatch.setattr("subprocess.Popen", refuse)
    report = JUDGED[name]
    first = judge(report)
    assert judge(bytes(bytearray(report))) == first
    assert judge(report) == first


@pytest.mark.parametrize("name", JUDGED)
def test_judgement_holds_no_seed_report_or_array(name):
    judgement = judge(JUDGED[name], seed=SEED)
    assert type(judgement.broken) in (Broken, type(None))
    assert type(judgement.verdict) in (Verdict, type(None))
    for count in judgement.counts or ():
        assert count._fields == ("failed", "non_finite")
        assert all(type(value) is int for value in count)


@pytest.mark.parametrize("name", JUDGED)
def test_run_verification_and_judge_report_agree(name, stand_in):
    report = JUDGED[name]
    result = verify(stand_in(report))
    assert result[:3] == judge(report)
    assert result.run.returncode == 0


@pytest.mark.parametrize("report", [GOOD, JUDGED["fail"]], ids=["pass", "fail"])
def test_what_judge_report_cannot_know_stays_with_the_run(report, stand_in):
    assert judge(report).broken is None
    assert_broken(verify(stand_in(report, status=3)), Broken.EXIT_STATUS)


PROGRAM = Path(hilclaw.harness.__file__).parent / "verification_program.c"

STRICT = ("-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Werror")
O2 = (*STRICT, "-O2")
FAST_MATH = (*STRICT, "-O2", "-ffast-math")
BUILD_TIMEOUT = 120
# Test values, not tolerances of the harness.
KERNEL_TOLERANCE = {"rtol": 1e-5, "atol": 1e-3}
SEEDS = [0, 1, 2**63, LAST]
LARGE = (64, 48, 80)

KERNEL = """\
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

@GLOBALS@
void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c)
{
@BODY@}
"""

GEMM = """\
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < n; j++) {
            float sum = 0.0f;
            for (size_t p = 0; p < k; p++)
                sum += a[i * k + p] * b[p * n + j];
            c[i * n + j] = sum;
        }
"""

UNUSED = "    (void)m;\n    (void)k;\n    (void)n;\n    (void)a;\n    (void)b;\n"
SILENT = UNUSED + "    (void)c;\n"
CALLS = "static int calls;"

# name: (file-scope text, body of the kernel)
KERNELS = {
    "gemm": ("", GEMM),
    "last-term-missing": ("", GEMM.replace("p < k;", "p + 1 < k;")),
    "silent": ("", SILENT),
    "hanging": ("", SILENT + "    for (;;)\n        sleep(1);\n"),
    "aborting": (CALLS, "    if (++calls == 2)\n        abort();\n" + GEMM),
    "exiting": ("", SILENT + "    exit(0);\n"),
    "printing": (
        "",
        '    puts("kernel says hello");\n    fputs("kernel warns\\n", stderr);\n'
        + GEMM,
    ),
}


@pytest.fixture(scope="session")
def executable(tmp_path_factory):
    if os.name != "posix":
        pytest.skip("a verification executable needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    directory = tmp_path_factory.mktemp("verification")
    built = {}

    def build(name, flags=O2):
        if (name, flags) not in built:
            file_scope, body = KERNELS[name]
            text = KERNEL.replace("@GLOBALS@", file_scope).replace("@BODY@", body)
            stem = f"{name}-{len(built)}"
            source = directory / f"{stem}.c"
            source.write_text(text, encoding="ascii", newline="\n")
            output = directory / stem
            result = clang_build.build(
                (PROGRAM, source), output, timeout_s=BUILD_TIMEOUT, flags=flags
            )
            assert result.ok, result.log
            built[name, flags] = output
        return built[name, flags]

    return build


def verify_kernel(path, shape=SHAPE, draws=3, seed=SEED, **changes):
    return verify(path, shape, draws, seed, **{**KERNEL_TOLERANCE, **changes})


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("draws", [1, 3])
def test_the_two_generators_agree_and_a_gemm_kernel_passes(executable, draws, seed):
    result = verify_kernel(executable("gemm"), draws=draws, seed=seed)
    assert_completed(result, Verdict.PASS, [(0, 0)] * draws)
    assert result.run.command[0] == str(executable("gemm"))
    assert result.run.stderr == b""


@pytest.mark.parametrize("flags", [O2, FAST_MATH], ids=["O2", "fast-math"])
def test_a_gemm_kernel_passes_at_a_larger_shape(executable, flags):
    result = verify_kernel(executable("gemm", flags), LARGE, 2, 2**63 + 1)
    assert_completed(result, Verdict.PASS, [(0, 0)] * 2)


def test_a_kernel_that_computes_something_else_fails(executable):
    result = verify_kernel(executable("last-term-missing"))
    assert_completed(result, Verdict.FAIL, [(15, 0)] * 3)


def test_a_kernel_that_writes_nothing_fails(executable):
    result = verify_kernel(executable("silent"))
    assert_completed(result, Verdict.FAIL, [(15, 15)] * 3)


def test_a_kernel_that_never_returns_is_broken(executable):
    result = verify_kernel(executable("hanging"), timeout_s=2)
    assert_broken(result, Broken.TIMEOUT)


def test_a_kernel_that_aborts_is_broken(executable):
    result = verify_kernel(executable("aborting"))
    assert_broken(result, Broken.EXIT_STATUS)
    assert result.run.returncode == -signal.SIGABRT


def test_a_kernel_that_exits_with_status_0_is_broken(executable):
    result = verify_kernel(executable("exiting"))
    assert_broken(result, Broken.REPORT_FORM)
    assert result.run.returncode == 0


def test_what_a_kernel_prints_is_not_part_of_the_report(executable):
    result = verify_kernel(executable("printing"))
    assert_completed(result, Verdict.PASS, [(0, 0)] * 3)
    assert result.run.stderr.count(b"kernel says hello\n") == 3
    assert result.run.stderr.count(b"kernel warns\n") == 3
