import json
import os
import shutil
import signal
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

from hilclaw.harness import bf16_verification, verification
from hilclaw.harness.bf16_verification import (
    END_MARK,
    Broken,
    Judgement,
    Verdict,
    VerificationResult,
    judge_report,
    program_arguments,
    run_bf16_verification,
)
from hilclaw.harness.bf16_verification_arrays import (
    KINDS,
    check_value,
    draw_inputs,
    reference,
    widen,
)
from hilclaw.harness.bf16_verification_build import build_bf16_verification_executable
from hilclaw.harness.verification_arrays import Counts, VerificationArgumentError
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
SEED = 7
LAST = 2**64 - 1
M, K, N = 3, 4, 5
DIMS = {kind: (M, K, N) if kind == "gemm" else (M, N) for kind in KINDS}
# Test values, not tolerances of the harness: a relative 2**-8 covers bf16 rounding.
TOLERANCE = {"rtol": 2**-8, "atol": 1e-6}
FILL = 0x7FC0
NAN, POSITIVE_INFINITY, NEGATIVE_INFINITY = 0x7FC0, 0x7F80, 0xFF80


def rounded(values):
    bits = np.ascontiguousarray(values, dtype=np.float64).astype(np.float32)
    bits = bits.view(np.uint32)
    return ((bits + np.uint32(0x7FFF) + ((bits >> 16) & 1)) >> 16).astype(np.uint16)


def rounded_references(kind, dims, draws, seed):
    outputs = []
    for draw in range(draws):
        first, second = draw_inputs(kind, dims, seed=seed, draw=draw)
        outputs.append(rounded(reference(kind, first, second)))
    return outputs


def report_of(kind, dims, seed, outputs, wrong_check=()):
    parts = []
    for draw, output in enumerate(outputs):
        value = check_value(*draw_inputs(kind, dims, seed=seed, draw=draw))
        if draw in wrong_check:
            value ^= 1
        parts.append(struct.pack("=I", value))
        parts.append(np.ascontiguousarray(output, dtype=np.uint16).tobytes())
    return b"".join(parts) + END_MARK


def passing_report(kind, dims, draws, seed):
    return report_of(kind, dims, seed, rounded_references(kind, dims, draws, seed))


GOOD = {kind: passing_report(kind, DIMS[kind], 3, SEED) for kind in KINDS}
BLOCK = 4 + 2 * M * N


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


def verify(
    executable, kind="elementwise_add", dims=None, draws=3, seed=SEED, **changes
):
    dims = DIMS[kind] if dims is None else dims
    arguments = {"draws": draws, "seed": seed, **TOLERANCE, "timeout_s": TIMEOUT}
    return run_bf16_verification(executable, kind, dims, **{**arguments, **changes})


def judge(report, kind="elementwise_add", dims=None, draws=3, seed=SEED, **changes):
    dims = DIMS[kind] if dims is None else dims
    arguments = {"draws": draws, "seed": seed, **TOLERANCE}
    return judge_report(report, kind, dims, **{**arguments, **changes})


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


@pytest.mark.parametrize(
    "name", ["END_MARK", "Broken", "Judgement", "Verdict", "VerificationResult"]
)
def test_result_types_and_end_mark_are_those_of_the_first_case(name):
    assert getattr(bf16_verification, name) is getattr(verification, name)
    assert name in bf16_verification.__all__


def test_public_names():
    assert sorted(bf16_verification.__all__) == sorted(
        [
            "END_MARK",
            "Broken",
            "Judgement",
            "Verdict",
            "VerificationResult",
            "judge_report",
            "program_arguments",
            "run_bf16_verification",
        ]
    )


# --- program_arguments ---


def test_program_arguments_order_and_spelling_per_kind():
    assert program_arguments("gemm", (2048, 1, 96), draws=3, seed=7) == (
        "2048",
        "1",
        "96",
        "3",
        "7",
    )
    for kind in ("rmsnorm", "elementwise_add", "swiglu"):
        arguments = program_arguments(kind, (512, 2048), draws=2, seed=0)
        assert arguments == ("512", "2048", "2", "0")
        assert type(arguments) is tuple
        assert all(type(argument) is str for argument in arguments)


@pytest.mark.parametrize("kind", KINDS)
def test_program_arguments_bounds(kind):
    ones = (1,) * len(DIMS[kind])
    assert program_arguments(kind, ones, draws=1, seed=0) == (
        *("1",) * len(ones),
        "1",
        "0",
    )
    large = (10**30,) * len(ones)
    arguments = program_arguments(kind, large, draws=LAST, seed=LAST)
    assert arguments == (
        *("1" + "0" * 30,) * len(ones),
        "18446744073709551615",
        "18446744073709551615",
    )


class StrSubclass(str):
    pass


BAD_KINDS = [StrSubclass("gemm"), "GEMM", "rope", "", b"gemm", None, 0]
BAD_DIMS = {
    "gemm": [(3, 5), (3, 4, 5, 6), [3, 4, 5], (3, 0, 5), (3, -1, 5), (3, True, 5)]
    + [(3, 4.0, 5), (3, "4", 5), (3, None, 5), (3, 4, 10**5000), None, 3],
    "other": [(3,), (3, 4, 5), [3, 5], (0, 5), (3, -1), (True, 5), (3.0, 5)]
    + [("3", 5), (None, 5), (10**5000, 5), (), None, 5],
}
BAD_DRAWS = [0, -1, 2**64, 10**5000, True, 1.0, "1", None]
BAD_SEEDS = [-1, 2**64, 10**5000, 1.5, True, "7", None]
BAD_TOLERANCES = [
    (name, value)
    for name in ("rtol", "atol")
    for value in [-1e-9, -1, float("nan"), float("inf"), -float("inf"), True, "0.1"]
    + [None, 10**400]
]


def bad_arguments():
    cases = [("kind", "kind", value, "gemm") for value in BAD_KINDS]
    for kind in KINDS:
        group = "gemm" if kind == "gemm" else "other"
        cases += [("dims", kind, value, kind) for value in BAD_DIMS[group]]
    cases += [("draws", "draws", value, "swiglu") for value in BAD_DRAWS]
    cases += [("seed", "seed", value, "rmsnorm") for value in BAD_SEEDS]
    return cases


BAD_ARGUMENTS = bad_arguments()
BAD_IDS = [f"{case[0]}-{case[3]}-{n}" for n, case in enumerate(BAD_ARGUMENTS)]


def arguments_with(parameter, value, kind):
    arguments = {"kind": kind, "dims": DIMS[kind], "draws": 3, "seed": SEED}
    arguments[parameter] = value
    return arguments


@pytest.mark.parametrize(
    ("parameter", "_", "value", "kind"), BAD_ARGUMENTS, ids=BAD_IDS
)
def test_program_arguments_refuses(parameter, _, value, kind):
    arguments = arguments_with(parameter, value, kind)
    with pytest.raises(VerificationArgumentError, match=f"^{parameter}"):
        program_arguments(
            arguments["kind"],
            arguments["dims"],
            draws=arguments["draws"],
            seed=arguments["seed"],
        )


def test_program_arguments_refuses_in_the_order_of_the_parameters():
    with pytest.raises(VerificationArgumentError, match="^kind: "):
        program_arguments("GEMM", (0,), draws=0, seed=-1)
    with pytest.raises(VerificationArgumentError, match="^dims: "):
        program_arguments("gemm", (3, 5), draws=0, seed=-1)
    with pytest.raises(VerificationArgumentError, match=r"^dims\[1\]: "):
        program_arguments("gemm", (3, 0, 5), draws=0, seed=-1)
    with pytest.raises(VerificationArgumentError, match=r"^dims\[0\]: "):
        program_arguments("rmsnorm", (10**5000, 5), draws=0, seed=-1)
    with pytest.raises(VerificationArgumentError, match="^draws: "):
        program_arguments("swiglu", (3, 5), draws=0, seed=-1)
    with pytest.raises(VerificationArgumentError, match="^seed: "):
        program_arguments("swiglu", (3, 5), draws=1, seed=-1)


def test_program_arguments_error_is_the_one_of_the_array_side():
    with pytest.raises(ValueError) as caught:
        program_arguments("gemm", (3, 4, 5), draws=0, seed=0)
    assert type(caught.value) is VerificationArgumentError
    assert "int 0" in str(caught.value)


@pytest.mark.parametrize("missing", ["kind", "dims", "draws", "seed"])
def test_program_arguments_has_no_default_for(missing):
    arguments = {"kind": "gemm", "dims": (3, 4, 5), "draws": 3, "seed": 7}
    del arguments[missing]
    with pytest.raises(TypeError, match=missing):
        program_arguments(**arguments)


def test_program_arguments_draws_and_seed_are_keyword_only():
    with pytest.raises(TypeError):
        program_arguments("gemm", (3, 4, 5), 3, 7)
    with pytest.raises(TypeError):
        program_arguments("gemm", (3, 4, 5), 3, seed=7)
    assert program_arguments(kind="gemm", dims=(3, 4, 5), draws=3, seed=7)


# --- judge_report: pass ---


@pytest.mark.parametrize("draws", [1, 3])
@pytest.mark.parametrize("kind", KINDS)
def test_judge_report_passes_rounded_references(kind, draws):
    report = passing_report(kind, DIMS[kind], draws, SEED)
    judgement = judge(report, kind, draws=draws)
    assert_judged(judgement, Verdict.PASS, [(0, 0)] * draws)
    assert judgement._fields == ("broken", "verdict", "counts")


@pytest.mark.parametrize("seed", [0, LAST])
@pytest.mark.parametrize("kind", KINDS)
def test_judge_report_takes_the_whole_range_of_seeds(kind, seed):
    report = passing_report(kind, DIMS[kind], 2, seed)
    assert_judged(judge(report, kind, draws=2, seed=seed), Verdict.PASS, [(0, 0)] * 2)


SMALL_DIMS = {
    "gemm": [(1, 4, 5), (3, 1, 5), (3, 4, 1), (1, 1, 1)],
    "other": [(1, 5), (3, 1), (1, 1)],
}
SMALL = [
    (kind, dims)
    for kind in KINDS
    for dims in SMALL_DIMS["gemm" if kind == "gemm" else "other"]
]


@pytest.mark.parametrize(("kind", "dims"), SMALL)
def test_judge_report_of_shapes_with_a_dimension_of_one(kind, dims):
    m, n = dims[0], dims[-1]
    judgement = judge(passing_report(kind, dims, 2, SEED), kind, dims, 2)
    assert_judged(judgement, Verdict.PASS, [(0, 0)] * 2)
    outputs = rounded_references(kind, dims, 2, SEED)
    outputs[1][m - 1, n - 1] = rounded(np.array([9.0]))[0]
    judgement = judge(report_of(kind, dims, SEED, outputs), kind, dims, 2)
    assert_judged(judgement, Verdict.FAIL, [(0, 0), (1, 0)])


# --- judge_report: fail ---


@pytest.mark.parametrize("kind", KINDS)
def test_judge_report_fails_one_element_outside_the_tolerance(kind):
    outputs = rounded_references(kind, DIMS[kind], 3, SEED)
    outputs[1][2, 4] = rounded(widen(outputs[1][2:3, 4:5]) + 0.75)[0, 0]
    judgement = judge(report_of(kind, DIMS[kind], SEED, outputs), kind)
    assert_judged(judgement, Verdict.FAIL, [(0, 0), (1, 0), (0, 0)])


@pytest.mark.parametrize("kind", KINDS)
def test_judge_report_counts_failing_draws_apart(kind):
    nine = rounded(np.array([9.0]))[0]
    outputs = rounded_references(kind, DIMS[kind], 3, SEED)
    outputs[0][0, :] = nine
    outputs[2][:, 0] = nine | 0x8000
    judgement = judge(report_of(kind, DIMS[kind], SEED, outputs), kind)
    assert_judged(judgement, Verdict.FAIL, [(N, 0), (0, 0), (M, 0)])


@pytest.mark.parametrize("kind", KINDS)
def test_judge_report_fails_and_counts_non_finite_patterns(kind):
    outputs = rounded_references(kind, DIMS[kind], 3, SEED)
    outputs[0][1, 1] = NAN
    outputs[0][2, 2] = POSITIVE_INFINITY
    outputs[0][0, 0] = rounded(np.array([70.0]))[0]
    outputs[2][0, 3] = NEGATIVE_INFINITY
    report = report_of(kind, DIMS[kind], SEED, outputs)
    judgement = judge(report, kind, rtol=1.0, atol=1.0)
    assert_judged(judgement, Verdict.FAIL, [(3, 2), (0, 0), (1, 1)])


@pytest.mark.parametrize("kind", KINDS)
def test_judge_report_fails_an_unwritten_output_in_every_draw(kind):
    fill = np.full((M, N), FILL, dtype=np.uint16)
    report = report_of(kind, DIMS[kind], SEED, [fill] * 3)
    assert_judged(judge(report, kind), Verdict.FAIL, [(M * N, M * N)] * 3)


def exact_seed():
    for seed in range(1000):
        first, second = draw_inputs("elementwise_add", (1, 1), seed=seed, draw=0)
        exact = reference("elementwise_add", first, second)
        if abs(exact[0, 0]) >= 1 and (widen(rounded(exact)) == exact).all():
            return seed, rounded(exact)
    pytest.fail("no seed below 1000 gives an exact sum of at least 1")


def test_judge_report_with_a_zero_tolerance():
    seed, output = exact_seed()
    dims = (1, 1)
    report = report_of("elementwise_add", dims, seed, [output])
    for zero in (0.0, 0):
        judgement = judge(
            report, "elementwise_add", dims, 1, seed, rtol=zero, atol=zero
        )
        assert_judged(judgement, Verdict.PASS, [(0, 0)])
    off = report_of("elementwise_add", dims, seed, [output + np.uint16(1)])
    judgement = judge(off, "elementwise_add", dims, 1, seed, rtol=0.0, atol=0.0)
    assert_judged(judgement, Verdict.FAIL, [(1, 0)])


def test_judge_report_with_integer_tolerances():
    zeros = [np.zeros((M, N), dtype=np.uint16)] * 3
    report = report_of("rmsnorm", DIMS["rmsnorm"], SEED, zeros)
    assert_judged(judge(report, "rmsnorm", rtol=1, atol=0), Verdict.PASS, [(0, 0)] * 3)
    assert_judged(judge(report, "rmsnorm", rtol=0, atol=4), Verdict.PASS, [(0, 0)] * 3)
    judgement = judge(report, "rmsnorm", rtol=0, atol=0)
    assert_judged(judgement, Verdict.FAIL, [(M * N, 0)] * 3)


# --- judge_report: broken ---


def bad_forms(kind):
    good = GOOD[kind]
    dims = DIMS[kind]
    return {
        "empty": b"",
        "end-mark-alone": END_MARK,
        "first-draw-only": good[:BLOCK],
        "first-draw-and-end-mark": good[:BLOCK] + END_MARK,
        "no-end-mark": good[:-4],
        "one-byte-short": good[:-1],
        "first-byte-missing": good[1:],
        "one-byte-long": good + b"\n",
        "byte-before": b"\n" + good,
        "second-end-mark": good + END_MARK,
        "one-draw-more": passing_report(kind, dims, 4, SEED),
        "one-draw-less": passing_report(kind, dims, 2, SEED),
        "other-end-mark": good[:-4] + b"END\n",
        "end-mark-without-lf": good[:-4] + b"end\0",
        "shifted-end-mark": good[:-5] + END_MARK + b"\n",
        "wrong-check-value-too": report_of(
            kind, dims, SEED, rounded_references(kind, dims, 3, SEED), wrong_check={0}
        )[:-1],
    }


FORM_CASES = [(kind, name) for kind in KINDS for name in bad_forms("gemm")]


@pytest.mark.parametrize(("kind", "name"), FORM_CASES)
def test_judge_report_of_another_form_is_broken(kind, name):
    assert_judged_broken(judge(bad_forms(kind)[name], kind), Broken.REPORT_FORM)


def test_judge_report_takes_the_form_from_m_n_and_draws_alone():
    good = GOOD["gemm"]
    assert_judged(judge(good, "gemm"), Verdict.PASS, [(0, 0)] * 3)
    assert_judged_broken(judge(good, "gemm", draws=2), Broken.REPORT_FORM)
    assert_judged_broken(judge(good, "gemm", draws=LAST), Broken.REPORT_FORM)
    assert_judged_broken(judge(good, "gemm", (3, 2, 5)), Broken.CHECK_VALUE)
    assert_judged_broken(judge(good, "gemm", (3, 40, 5)), Broken.CHECK_VALUE)
    assert judge(good, "gemm", (5, 4, 3)).broken is None
    assert_judged_broken(judge(good, "gemm", (4, 3, 5)), Broken.REPORT_FORM)
    assert_judged_broken(judge(good, "gemm", (3, 5, 4)), Broken.REPORT_FORM)
    huge = (2**40, 4, 2**40)
    assert_judged_broken(judge(good, "gemm", huge), Broken.REPORT_FORM)
    rmsnorm = GOOD["rmsnorm"]
    assert_judged_broken(judge(rmsnorm, "rmsnorm", (5, 3)), Broken.CHECK_VALUE)
    assert_judged_broken(judge(rmsnorm, "rmsnorm", (2**40, 2**40)), Broken.REPORT_FORM)


@pytest.mark.parametrize("kind", KINDS)
def test_judge_report_tests_the_form_before_any_check_value(kind):
    outputs = rounded_references(kind, DIMS[kind], 3, SEED)
    report = report_of(kind, DIMS[kind], SEED, outputs, wrong_check={0, 1, 2})
    assert_judged_broken(judge(report, kind), Broken.CHECK_VALUE)
    assert_judged_broken(judge(report[:-4] + b"END\n", kind), Broken.REPORT_FORM)
    assert_judged_broken(judge(report + b"\n", kind), Broken.REPORT_FORM)


@pytest.mark.parametrize("draw", [0, 1, 2])
@pytest.mark.parametrize("passing", [True, False])
@pytest.mark.parametrize("kind", KINDS)
def test_judge_report_with_a_check_value_that_disagrees_is_broken(kind, passing, draw):
    outputs = rounded_references(kind, DIMS[kind], 3, SEED)
    if not passing:
        outputs[0][0, 0] = NAN
        outputs[2][1, 1] = rounded(np.array([9.0]))[0]
    report = report_of(kind, DIMS[kind], SEED, outputs, wrong_check={draw})
    assert_judged_broken(judge(report, kind), Broken.CHECK_VALUE)


@pytest.mark.parametrize("kind", KINDS)
def test_judge_report_of_another_seed_is_broken(kind):
    report = passing_report(kind, DIMS[kind], 3, SEED + 1)
    assert_judged_broken(judge(report, kind), Broken.CHECK_VALUE)


OTHER_KINDS = [(made, judged) for made in KINDS for judged in KINDS if made != judged]


@pytest.mark.parametrize(("made", "judged"), OTHER_KINDS)
def test_judge_report_of_another_kind_of_the_same_length_is_broken(made, judged):
    report = GOOD[made]
    assert len(report) == len(GOOD[judged])
    assert_judged_broken(judge(report, judged), Broken.CHECK_VALUE)


# --- judge_report: refusals ---


@pytest.mark.parametrize(
    ("parameter", "_", "value", "kind"), BAD_ARGUMENTS, ids=BAD_IDS
)
@pytest.mark.parametrize("report", ["good", b"", None], ids=["good", "empty", "none"])
def test_judge_report_refuses_arguments_before_the_report(
    report, parameter, _, value, kind
):
    arguments = arguments_with(parameter, value, kind)
    report = GOOD[kind] if report == "good" else report
    with pytest.raises(VerificationArgumentError, match=f"^{parameter}"):
        judge_report(
            report,
            arguments["kind"],
            arguments["dims"],
            draws=arguments["draws"],
            seed=arguments["seed"],
            **TOLERANCE,
        )


@pytest.mark.parametrize(("name", "value"), BAD_TOLERANCES)
@pytest.mark.parametrize("report", ["good", b"", None], ids=["good", "empty", "none"])
def test_judge_report_refuses_tolerances_before_the_report(report, name, value):
    report = GOOD["elementwise_add"] if report == "good" else report
    with pytest.raises(VerificationArgumentError, match=f"^{name}: "):
        judge(report, **{name: value})


def test_judge_report_refuses_in_order():
    with pytest.raises(VerificationArgumentError, match="^kind: "):
        judge(None, "GEMM", (0,), draws=0, seed=-1, rtol=-1.0, atol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^dims: "):
        judge(None, "gemm", (3, 5), draws=0, seed=-1, rtol=-1.0, atol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^draws: "):
        judge(None, draws=0, seed=-1, rtol=-1.0, atol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^seed: "):
        judge(None, seed=-1, rtol=-1.0, atol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^rtol: "):
        judge(None, rtol=-1.0, atol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^atol: "):
        judge(None, atol=-1.0)
    with pytest.raises(TypeError, match="^report: "):
        judge(None)


class BytesSubclass(bytes):
    pass


GOOD_ADD = GOOD["elementwise_add"]


@pytest.mark.parametrize(
    "report",
    [None, GOOD_ADD.decode("latin-1"), 0, list(GOOD_ADD), (GOOD_ADD,)]
    + [
        bytearray(GOOD_ADD),
        memoryview(GOOD_ADD),
        BytesSubclass(GOOD_ADD),
        np.frombuffer(GOOD_ADD, dtype=np.uint8),
    ],
    ids=lambda report: type(report).__name__,
)
def test_judge_report_refuses_a_report_that_is_not_bytes(report):
    with pytest.raises(TypeError, match="^report: must be bytes, got ") as caught:
        judge(report)
    assert str(caught.value).endswith(f"got {type(report).__name__}")


@pytest.mark.parametrize("missing", ["kind", "dims", "draws", "seed", "rtol", "atol"])
def test_judge_report_has_no_default_for(missing):
    arguments = {"kind": "gemm", "dims": (3, 4, 5), "draws": 3, "seed": 7, **TOLERANCE}
    del arguments[missing]
    with pytest.raises(TypeError, match=missing):
        judge_report(GOOD["gemm"], **arguments)


def test_judge_report_parameters_are_keyword_only():
    with pytest.raises(TypeError):
        judge_report(GOOD["gemm"], "gemm", (3, 4, 5), 3, 7, 2**-8, 1e-6)
    with pytest.raises(TypeError):
        judge_report(GOOD["gemm"], "gemm", (3, 4, 5), 3, seed=7, **TOLERANCE)
    with pytest.raises(TypeError, match="report"):
        judge_report(kind="gemm", dims=(3, 4, 5), draws=3, seed=7, **TOLERANCE)


FAILING = rounded_references("elementwise_add", (M, N), 3, SEED)
FAILING[1][0, 0] = POSITIVE_INFINITY
JUDGED = {
    "pass": GOOD_ADD,
    "fail": report_of("elementwise_add", (M, N), SEED, FAILING),
    "wrong-form": GOOD_ADD[:-1],
    "empty": b"",
    "wrong-check-value": report_of(
        "elementwise_add", (M, N), SEED, FAILING, wrong_check={2}
    ),
    "another-seed": passing_report("elementwise_add", (M, N), 3, SEED + 1),
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
    judgement = judge(JUDGED[name])
    assert type(judgement.broken) in (Broken, type(None))
    assert type(judgement.verdict) in (Verdict, type(None))
    for count in judgement.counts or ():
        assert count._fields == ("failed", "non_finite")
        assert all(type(value) is int for value in count)


# --- run_bf16_verification with a stand-in ---


@pytest.mark.parametrize("kind", KINDS)
def test_run_passes_a_report_of_rounded_references(kind, stand_in):
    result = verify(stand_in(GOOD[kind]), kind)
    assert_completed(result, Verdict.PASS, [(0, 0)] * 3)
    assert result._fields == ("broken", "verdict", "counts", "run")


@pytest.mark.parametrize("kind", KINDS)
def test_the_process_gets_exactly_the_program_arguments(kind, stand_in):
    executable = stand_in(passing_report(kind, DIMS[kind], 2, LAST))
    result = verify(executable, kind, draws=2, seed=LAST)
    assert_completed(result, Verdict.PASS, [(0, 0)] * 2)
    expected = [*(str(value) for value in DIMS[kind]), "2", str(LAST)]
    assert stand_in.call()["argv"] == expected
    assert result.run.command[1:] == (executable[1], *expected)
    assert os.path.samefile(result.run.command[0], sys.executable)


def test_cwd_and_env_reach_the_process(stand_in, tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    env = {**os.environ, "HILCLAW_TEST_MARK": "handed over"}
    result = verify(stand_in(GOOD_ADD), cwd=work, env=env)
    assert_completed(result, Verdict.PASS, [(0, 0)] * 3)
    call = stand_in.call()
    assert os.path.samefile(call["cwd"], work)
    assert call["mark"] == "handed over"


def test_no_environment_variable_is_set_by_default(stand_in, monkeypatch):
    monkeypatch.setenv("HILCLAW_TEST_MARK", "inherited")
    verify(stand_in(GOOD_ADD))
    call = stand_in.call()
    assert call["mark"] == "inherited"
    assert os.path.samefile(call["cwd"], os.getcwd())


def test_result_holds_the_capture_of_the_runner_without_the_report(stand_in):
    noise = GOOD["swiglu"] + "café\n".encode()
    result = verify(stand_in(GOOD_ADD, stderr=noise))
    assert_completed(result, Verdict.PASS, [(0, 0)] * 3)
    assert result.run.stderr == noise
    assert result.run.command[2:] == program_arguments(
        "elementwise_add", (M, N), draws=3, seed=SEED
    )
    assert type(result.run.duration_s) is float
    assert result.run.duration_s > 0


def test_executable_as_one_path_is_the_whole_prefix(tmp_path):
    for executable in (sys.executable, Path(sys.executable)):
        result = verify(executable, "gemm", cwd=tmp_path)
        assert_broken(result, Broken.EXIT_STATUS)
        assert result.run.command[1:] == ("3", "4", "5", "3", "7")
        assert result.run.returncode != 0
        assert result.run.stderr


def test_executable_prefix_may_be_a_list(stand_in):
    result = verify(list(stand_in(GOOD_ADD)))
    assert_completed(result, Verdict.PASS, [(0, 0)] * 3)


@pytest.mark.parametrize("stdout", ["good", b"end"], ids=["passing", "other"])
def test_timeout_is_broken_whatever_was_written(stdout, stand_in):
    stdout = GOOD_ADD if stdout == "good" else stdout
    result = verify(stand_in(stdout, sleep=30), timeout_s=2)
    assert_broken(result, Broken.TIMEOUT)
    assert result.run.timed_out is True
    assert result.run.returncode is None


@pytest.mark.parametrize("stdout", ["good", b"end"], ids=["passing", "other"])
def test_non_zero_exit_is_broken_whatever_was_written(stdout, stand_in):
    stdout = GOOD_ADD if stdout == "good" else stdout
    result = verify(stand_in(stdout, status=3, stderr=b"a line\n"))
    assert_broken(result, Broken.EXIT_STATUS)
    assert result.run.returncode == 3
    assert result.run.stderr == b"a line\n"


@pytest.mark.skipif(os.name == "nt", reason="POSIX signals")
def test_death_by_signal_after_a_passing_report_is_broken(stand_in):
    result = verify(stand_in(GOOD_ADD, kill=signal.SIGKILL))
    assert_broken(result, Broken.EXIT_STATUS)
    assert result.run.returncode == -signal.SIGKILL


@pytest.mark.parametrize("name", JUDGED)
def test_run_and_judge_report_agree(name, stand_in):
    report = JUDGED[name]
    result = verify(stand_in(report))
    assert result[:3] == judge(report)
    assert result.run.returncode == 0


@pytest.mark.parametrize("name", ["pass", "fail"])
def test_what_judge_report_cannot_know_stays_with_the_run(name, stand_in):
    assert judge(JUDGED[name]).broken is None
    assert_broken(verify(stand_in(JUDGED[name], status=3)), Broken.EXIT_STATUS)


@pytest.mark.parametrize(
    ("parameter", "_", "value", "kind"), BAD_ARGUMENTS, ids=BAD_IDS
)
def test_bad_arguments_raise_and_start_nothing(parameter, _, value, kind, stand_in):
    arguments = arguments_with(parameter, value, kind)
    with pytest.raises(VerificationArgumentError, match=f"^{parameter}"):
        run_bf16_verification(
            stand_in(GOOD_ADD),
            arguments["kind"],
            arguments["dims"],
            draws=arguments["draws"],
            seed=arguments["seed"],
            **TOLERANCE,
            timeout_s=TIMEOUT,
        )
    assert not stand_in.started


@pytest.mark.parametrize(("name", "value"), BAD_TOLERANCES)
def test_bad_tolerances_raise_and_start_nothing(name, value, stand_in):
    with pytest.raises(VerificationArgumentError, match=f"^{name}: "):
        verify(stand_in(GOOD_ADD), **{name: value})
    assert not stand_in.started


def test_arguments_are_refused_before_the_tolerance_and_the_executable():
    with pytest.raises(VerificationArgumentError, match="^kind: "):
        verify((), "GEMM", (3, 5), seed=-1, rtol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^dims: "):
        verify((), "gemm", (3, 5), seed=-1, rtol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^seed: "):
        verify((), seed=-1, rtol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^rtol: "):
        verify((), rtol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^atol: "):
        verify(7, atol=-1.0, timeout_s=0)
    with pytest.raises(ValueError, match="empty"):
        verify((), timeout_s=0)


@pytest.mark.parametrize(
    "missing", ["kind", "dims", "draws", "seed", "rtol", "atol", "timeout_s"]
)
def test_run_has_no_default_for(missing, stand_in):
    arguments = {"kind": "gemm", "dims": (3, 4, 5), "draws": 3, "seed": 7}
    arguments |= {**TOLERANCE, "timeout_s": TIMEOUT}
    del arguments[missing]
    with pytest.raises(TypeError, match=missing):
        run_bf16_verification(stand_in(GOOD["gemm"]), **arguments)
    assert not stand_in.started


def test_run_parameters_are_keyword_only(stand_in):
    with pytest.raises(TypeError):
        run_bf16_verification(
            stand_in(GOOD["gemm"]), "gemm", (3, 4, 5), 3, 7, 2**-8, 1e-6, TIMEOUT
        )
    assert not stand_in.started


@pytest.mark.parametrize(
    ("timeout_s", "error"),
    [(0, ValueError), (-1, ValueError), (float("inf"), ValueError)]
    + [("60", TypeError), (None, TypeError), (True, TypeError)],
)
def test_time_limit_errors_are_those_of_the_runner(timeout_s, error, stand_in):
    with pytest.raises(error, match="timeout_s"):
        verify(stand_in(GOOD_ADD), timeout_s=timeout_s)
    assert not stand_in.started


@pytest.mark.parametrize(
    "executable",
    ["hilclaw-no-such-bf16-verification-executable", Path("no-such-dir") / "verify"],
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
    program, script = stand_in(GOOD_ADD)
    with pytest.raises(TypeError):
        verify((program, Path(script)))
    assert not stand_in.started


# --- real clang ---

STRICT = ("-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Werror")
BUILD_TIMEOUT = 120

ADD_KERNEL = """\
#include <stddef.h>
#include <stdint.h>
#include <string.h>

void hilclaw_elementwise_add_bf16(size_t m, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c);

static float widened(uint16_t pattern)
{
    uint32_t bits = (uint32_t)pattern << 16;
    float value;
    memcpy(&value, &bits, sizeof value);
    return value;
}

void hilclaw_elementwise_add_bf16(size_t m, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c)
{
    (void)widened;
    for (size_t i = 0; i < m * n; i++) {
@BODY@
    }
}
"""

ADD_KERNELS = {
    "sum": (
        "        float sum = widened(a[i]) + widened(b[i]);\n"
        "        uint32_t bits;\n"
        "        memcpy(&bits, &sum, sizeof bits);\n"
        "        c[i] = (uint16_t)((bits + UINT32_C(0x7FFF) + ((bits >> 16) & 1)) >> 16);"
    ),
    "copy-first": "        (void)b;\n        c[i] = a[i];",
}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    if os.name != "posix":
        pytest.skip("a verification executable needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    directory = tmp_path_factory.mktemp("bf16_verification")
    paths = {}
    for name, body in ADD_KERNELS.items():
        source = directory / f"{name}.c"
        text = ADD_KERNEL.replace("@BODY@", body)
        source.write_text(text, encoding="ascii", newline="\n")
        output = directory / name
        result = build_bf16_verification_executable(
            "elementwise_add", source, output, timeout_s=BUILD_TIMEOUT, flags=STRICT
        )
        assert result.ok, result.log
        paths[name] = output
    return paths


def test_real_clang_rounded_sum_kernel_passes(built):
    result = verify(built["sum"], dims=(3, 7), draws=2, rtol=2**-8, atol=0)
    assert_completed(result, Verdict.PASS, [(0, 0)] * 2)
    assert result.run.command[0] == str(built["sum"])


def test_real_clang_copying_kernel_fails(built):
    result = verify(built["copy-first"], dims=(3, 7), draws=2, rtol=2**-8, atol=0)
    assert_completed(result, Verdict.FAIL, [(21, 0)] * 2)
