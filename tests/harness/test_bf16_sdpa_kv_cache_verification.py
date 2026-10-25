import json
import os
import shutil
import signal
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

from hilclaw import sdpa_kv_cache_bf16_contract
from hilclaw.harness import (
    bf16_sdpa_kv_cache_arrays,
    bf16_sdpa_kv_cache_verification,
    verification,
)
from hilclaw.harness.bf16_sdpa_kv_cache_arrays import (
    FILL,
    allocation_after,
    allocation_before,
    check_value,
    draw_inputs,
    reference,
)
from hilclaw.harness.bf16_sdpa_kv_cache_verification import (
    END_MARK,
    Broken,
    DrawCounts,
    Judgement,
    Verdict,
    VerificationResult,
    judge_report,
    program_arguments,
    run_bf16_sdpa_kv_cache_verification,
)
from hilclaw.harness.bf16_verification_build import build_bf16_verification_executable
from hilclaw.harness.verification_arrays import VerificationArgumentError
from hilclaw.local_run import ProgramNotFoundError, RunResult

STAND_IN = """\
import json, os, sys, time
from pathlib import Path
here = Path(__file__).parent
plan = json.loads((here / "plan.json").read_text(encoding="utf-8"))
received = sys.stdin.buffer.read()
call = {
    "argv": sys.argv[1:],
    "cwd": os.getcwd(),
    "mark": os.environ.get("HILCLAW_TEST_MARK"),
    "stdin": received.hex(),
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
# (m, l, h, h_kv, d) with P = 3.
DIMS = (2, 5, 4, 2, 3)
P0 = (2, 2, 4, 2, 3)
ONE = (1, 1, 1, 1, 1)
# A test value, not a tolerance of the harness: above half a bf16 unit of |y| < 1.
TOLERANCE = {"rtol": 0.0, "atol": 2**-6}
MARK = 0x3F80


def rounded(values):
    bits = np.ascontiguousarray(values, dtype=np.float64).astype(np.float32)
    bits = bits.view(np.uint32)
    return ((bits + np.uint32(0x7FFF) + ((bits >> 16) & 1)) >> 16).astype(np.uint16)


def parts_of(dims, seed, draw):
    inputs = draw_inputs(dims, seed=seed, draw=draw)
    before_k = allocation_before(dims, inputs.cached_k)
    before_v = allocation_before(dims, inputs.cached_v)
    return {
        "check": check_value(
            dims, inputs.q, inputs.k_new, inputs.v_new, before_k, before_v
        ),
        "out": rounded(reference(dims, *inputs)),
        "cache_k": allocation_after(dims, inputs.cached_k, inputs.k_new),
        "cache_v": allocation_after(dims, inputs.cached_v, inputs.v_new),
    }


def all_parts(dims, draws, seed):
    return [parts_of(dims, seed, draw) for draw in range(draws)]


def pack(blocks):
    data = []
    for parts in blocks:
        data.append(struct.pack("=I", parts["check"]))
        for name in ("out", "cache_k", "cache_v"):
            data.append(np.ascontiguousarray(parts[name], dtype=np.uint16).tobytes())
    return b"".join(data) + END_MARK


def passing_report(dims, draws, seed):
    return pack(all_parts(dims, draws, seed))


def complete_length(dims, draws):
    m, l, h, h_kv, d = dims
    return draws * (4 + 2 * m * h * d + 4 * (l + 2 * m) * h_kv * d) + 4


GOOD = passing_report(DIMS, 3, SEED)


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


@pytest.fixture
def no_draw(monkeypatch):
    def refuse(*args, **kwargs):
        pytest.fail("a draw was regenerated")

    for name in ("draw_inputs", "allocation_before", "check_value", "reference"):
        monkeypatch.setattr(bf16_sdpa_kv_cache_arrays, name, refuse)


@pytest.fixture
def draws_made(monkeypatch):
    calls = []
    original = bf16_sdpa_kv_cache_arrays.draw_inputs

    def counting(dims, *, seed, draw):
        calls.append(draw)
        return original(dims, seed=seed, draw=draw)

    monkeypatch.setattr(bf16_sdpa_kv_cache_arrays, "draw_inputs", counting)
    return calls


def verify(executable, dims=DIMS, draws=3, seed=SEED, **changes):
    arguments = {"draws": draws, "seed": seed, **TOLERANCE, "timeout_s": TIMEOUT}
    return run_bf16_sdpa_kv_cache_verification(
        executable, dims, **{**arguments, **changes}
    )


def judge(report, dims=DIMS, draws=3, seed=SEED, **changes):
    arguments = {"draws": draws, "seed": seed, **TOLERANCE}
    return judge_report(report, dims, **{**arguments, **changes})


def assert_judged(judgement, verdict, counts):
    assert type(judgement) is Judgement
    assert judgement.broken is None
    assert judgement.verdict is verdict
    assert type(judgement.counts) is tuple
    assert all(type(count) is DrawCounts for count in judgement.counts)
    assert all(type(value) is int for count in judgement.counts for value in count)
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
    assert all(type(count) is DrawCounts for count in result.counts)
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
    assert getattr(bf16_sdpa_kv_cache_verification, name) is getattr(verification, name)
    assert name in bf16_sdpa_kv_cache_verification.__all__


def test_public_names():
    assert sorted(bf16_sdpa_kv_cache_verification.__all__) == sorted(
        [
            "END_MARK",
            "Broken",
            "DrawCounts",
            "Judgement",
            "Verdict",
            "VerificationResult",
            "judge_report",
            "program_arguments",
            "run_bf16_sdpa_kv_cache_verification",
        ]
    )


def test_draw_counts_fields():
    assert DrawCounts._fields == ("failed", "non_finite", "cache_differences")
    assert DrawCounts(1, 2, 3) == (1, 2, 3)
    assert DrawCounts(1, 2, 3).cache_differences == 3


# --- program_arguments ---


def test_program_arguments_order_and_spelling():
    arguments = program_arguments(DIMS, draws=2, seed=LAST)
    assert arguments == ("2", "5", "4", "2", "3", "2", "18446744073709551615")
    assert type(arguments) is tuple
    assert all(type(argument) is str for argument in arguments)
    assert program_arguments((2048, 2048, 32, 8, 64), draws=1, seed=0) == (
        "2048",
        "2048",
        "32",
        "8",
        "64",
        "1",
        "0",
    )


def test_program_arguments_bounds():
    assert program_arguments(ONE, draws=1, seed=0) == ("1",) * 6 + ("0",)
    large = (10**30, 10**30, 2 * 10**30, 10**30, 10**30)
    assert program_arguments(large, draws=LAST, seed=LAST) == (
        "1" + "0" * 30,
        "1" + "0" * 30,
        "2" + "0" * 30,
        "1" + "0" * 30,
        "1" + "0" * 30,
        "18446744073709551615",
        "18446744073709551615",
    )


BAD_DIMS = [
    ([2, 5, 4, 2, 3], "dims"),
    ((2, 5, 4, 2), "dims"),
    ((2, 5, 4, 2, 3, 1), "dims"),
    ((), "dims"),
    (None, "dims"),
    (3, "dims"),
    ((True, 5, 4, 2, 3), r"dims\[0\]"),
    ((2, 0, 4, 2, 3), r"dims\[1\]"),
    ((2, 5, -4, 2, 3), r"dims\[2\]"),
    ((2, 5, 4, 2.0, 3), r"dims\[3\]"),
    ((2, 5, 4, 2, "3"), r"dims\[4\]"),
    ((3, 2, 4, 2, 3), r"dims\[1\]"),
    ((2, 5, 3, 2, 3), r"dims\[2\]"),
    ((10**5000, 10**5000, 4, 2, 3), r"dims\[0\]"),
]
BAD_DRAWS = [0, -1, 2**64, 10**5000, True, 1.0, "1", None]
BAD_SEEDS = [-1, 2**64, 10**5000, 1.5, True, "7", None]
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
        program_arguments((2, 5, 4, 2), draws=0, seed=-1)
    with pytest.raises(VerificationArgumentError, match=r"^dims\[1\]: "):
        program_arguments((3, 2, 4, 2, 3), draws=0, seed=-1)
    with pytest.raises(VerificationArgumentError, match=r"^dims\[2\]: "):
        program_arguments((2, 5, 3, 2, 3), draws=0, seed=-1)
    with pytest.raises(VerificationArgumentError, match=r"^dims\[4\]: "):
        program_arguments((2, 5, 4, 2, 10**5000), draws=0, seed=-1)
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
        program_arguments(DIMS, start=3, draws=3, seed=7)


def test_program_arguments_draws_and_seed_are_keyword_only():
    with pytest.raises(TypeError):
        program_arguments(DIMS, 3, 7)
    with pytest.raises(TypeError):
        program_arguments(DIMS, 3, seed=7)
    assert program_arguments(dims=DIMS, draws=3, seed=7)[-2:] == ("3", "7")


# --- judge_report: pass ---


@pytest.mark.parametrize("dims", [DIMS, P0, ONE, (1, 4, 4, 1, 2), (3, 4, 8, 2, 1)])
@pytest.mark.parametrize("draws", [1, 4])
def test_judge_report_passes_a_conforming_report(dims, draws):
    report = passing_report(dims, draws, SEED)
    assert len(report) == complete_length(dims, draws)
    judgement = judge(report, dims, draws)
    assert_judged(judgement, Verdict.PASS, [(0, 0, 0)] * draws)


def test_judge_report_regenerates_each_draw_once_in_order(draws_made):
    assert_judged(judge(GOOD), Verdict.PASS, [(0, 0, 0)] * 3)
    assert draws_made == [0, 1, 2]


# --- judge_report: fail through out ---


def test_one_element_outside_the_tolerance_fails_its_draw_only():
    blocks = all_parts(DIMS, 3, SEED)
    blocks[1]["out"][1, 2, 0] = rounded(np.array([9.0]))[0]
    judgement = judge(pack(blocks))
    assert_judged(judgement, Verdict.FAIL, [(0, 0, 0), (1, 0, 0), (0, 0, 0)])


def test_fill_elements_in_out_are_failed_and_non_finite():
    blocks = all_parts(DIMS, 3, SEED)
    blocks[0]["out"][0, 0, 0] = FILL
    blocks[2]["out"][...] = FILL
    judgement = judge(pack(blocks))
    assert_judged(judgement, Verdict.FAIL, [(1, 1, 0), (0, 0, 0), (24, 24, 0)])


def test_tolerance_applies_to_out_only():
    blocks = all_parts(DIMS, 1, SEED)
    blocks[0]["cache_k"][0, 0, 0] = MARK
    judgement = judge(pack(blocks), draws=1, rtol=1e300, atol=1e300)
    assert_judged(judgement, Verdict.FAIL, [(0, 0, 1)])


# --- judge_report: fail through the cache ---


def m_and_p(dims):
    m, l = dims[0], dims[1]
    return m, l - m


def region_row(dims, region):
    m, p = m_and_p(dims)
    l = dims[1]
    return {
        "leading-guard-first": 0,
        "leading-guard-last": m - 1,
        "drawn-first": m,
        "drawn-last": m + p - 1,
        "written-first": m + p,
        "written-last": m + l - 1,
        "trailing-guard-first": m + l,
        "trailing-guard-last": 2 * m + l - 1,
    }[region]


REGIONS = [
    "leading-guard-first",
    "leading-guard-last",
    "drawn-first",
    "drawn-last",
    "written-first",
    "written-last",
    "trailing-guard-first",
    "trailing-guard-last",
]


@pytest.mark.parametrize("cache", ["cache_k", "cache_v"])
@pytest.mark.parametrize("region", REGIONS)
def test_one_cache_element_that_differs_fails_in_every_region(cache, region):
    blocks = all_parts(DIMS, 3, SEED)
    row = region_row(DIMS, region)
    allocation = blocks[1][cache]
    if region.startswith("written"):
        allocation[row, 1, 2] = FILL
    elif region.startswith("drawn"):
        allocation[row, 1, 2] ^= 1
    else:
        assert allocation[row, 1, 2] == FILL
        allocation[row, 1, 2] = MARK
    judgement = judge(pack(blocks))
    assert_judged(judgement, Verdict.FAIL, [(0, 0, 0), (0, 0, 1), (0, 0, 0)])


@pytest.mark.parametrize("cache", ["cache_k", "cache_v"])
def test_a_cache_left_unwritten_fails_with_every_written_element(cache):
    m, p = m_and_p(DIMS)
    _, _, _, h_kv, d = DIMS
    blocks = all_parts(DIMS, 2, SEED)
    for parts in blocks:
        parts[cache][m + p : m + DIMS[1]] = FILL
    judgement = judge(pack(blocks), draws=2)
    assert_judged(judgement, Verdict.FAIL, [(0, 0, m * h_kv * d)] * 2)


def shifted(dims, parts, cache, by):
    m, p = m_and_p(dims)
    l = dims[1]
    allocation = parts[cache]
    new = allocation[m + p : m + l].copy()
    allocation[m + p : m + l] = FILL
    allocation[m + p + by : m + l + by] = new
    return allocation


@pytest.mark.parametrize("cache", ["cache_k", "cache_v"])
@pytest.mark.parametrize("dims", [DIMS, P0])
@pytest.mark.parametrize("by", [1, -1], ids=["late", "early"])
def test_a_block_written_one_row_off_fails(cache, dims, by):
    blocks = all_parts(dims, 2, SEED)
    expected = blocks[0][cache].copy()
    allocation = shifted(dims, blocks[0], cache, by)
    differences = int(np.count_nonzero(allocation != expected))
    assert differences > 0
    judgement = judge(pack(blocks), dims, draws=2)
    assert_judged(judgement, Verdict.FAIL, [(0, 0, differences), (0, 0, 0)])


def test_a_block_written_one_row_late_reaches_the_trailing_guard():
    m, p = m_and_p(DIMS)
    l, h_kv, d = DIMS[1], DIMS[3], DIMS[4]
    blocks = all_parts(DIMS, 1, SEED)
    allocation = shifted(DIMS, blocks[0], "cache_k", 1)
    assert (allocation[m + l] != FILL).all()
    assert (allocation[m + p] == FILL).all()
    count = judge(pack(blocks), draws=1).counts[0].cache_differences
    assert count >= 2 * h_kv * d


def test_cache_differences_are_summed_over_elements_and_allocations():
    blocks = all_parts(DIMS, 2, SEED)
    blocks[0]["cache_k"][0, 0, 0] = MARK
    blocks[0]["cache_k"][8, 1, 2] = MARK
    blocks[0]["cache_v"][2, 0, 1] ^= 1
    blocks[0]["cache_v"][5, 1, 0] = FILL
    blocks[0]["cache_v"][7, 0, 0] = 0
    blocks[1]["cache_v"][6, 1, 1] = FILL
    blocks[1]["out"][0, 0, 0] = FILL
    judgement = judge(pack(blocks), draws=2)
    assert_judged(judgement, Verdict.FAIL, [(0, 0, 5), (1, 1, 1)])


def test_a_cache_difference_at_p_zero_and_the_smallest_shape_fails():
    blocks = all_parts(ONE, 1, SEED)
    blocks[0]["cache_v"][1, 0, 0] = FILL
    assert_judged(judge(pack(blocks), ONE, 1), Verdict.FAIL, [(0, 0, 1)])


def test_caches_left_at_the_fill_fail_in_every_operand_row():
    blocks = all_parts(DIMS, 1, SEED)
    for cache in ("cache_k", "cache_v"):
        blocks[0][cache][...] = FILL
    judgement = judge(pack(blocks), draws=1)
    _, l, _, h_kv, d = DIMS
    assert_judged(judgement, Verdict.FAIL, [(0, 0, 2 * l * h_kv * d)])


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
        "one-draw-more": passing_report(DIMS, 4, SEED),
        "another-l": passing_report((2, 6, 4, 2, 3), 3, SEED),
        "another-h-kv": passing_report((2, 5, 4, 4, 3), 3, SEED),
        "out-only": GOOD[: 4 + 2 * 2 * 4 * 3] + END_MARK,
    }


@pytest.mark.parametrize("name", bad_forms())
def test_judge_report_of_another_form_is_broken_before_any_draw(name, no_draw):
    assert_judged_broken(judge(bad_forms()[name]), Broken.REPORT_FORM)


def test_judge_report_takes_the_form_from_dims_and_draws_alone(no_draw):
    assert_judged_broken(judge(GOOD, draws=2), Broken.REPORT_FORM)
    assert_judged_broken(judge(GOOD, draws=LAST), Broken.REPORT_FORM)
    assert_judged_broken(judge(GOOD, (2, 5, 4, 2, 2**40)), Broken.REPORT_FORM)
    assert_judged_broken(judge(GOOD, (2, 6, 4, 2, 3)), Broken.REPORT_FORM)


def test_judge_report_of_another_shape_of_the_same_length_is_broken():
    made, judged = (2, 3, 2, 1, 1), (1, 1, 6, 2, 1)
    assert complete_length(made, 2) == complete_length(judged, 2)
    report = passing_report(made, 2, SEED)
    assert_judged_broken(judge(report, judged, 2), Broken.CHECK_VALUE)


@pytest.mark.parametrize("draw", [0, 1, 2])
@pytest.mark.parametrize("passing", [True, False])
def test_judge_report_with_a_check_value_that_disagrees_is_broken(passing, draw):
    blocks = all_parts(DIMS, 3, SEED)
    if not passing:
        blocks[0]["out"][0, 0, 0] = FILL
        blocks[0]["cache_k"][0, 0, 0] = MARK
    blocks[draw]["check"] ^= 1
    assert_judged_broken(judge(pack(blocks)), Broken.CHECK_VALUE)


def test_judge_report_of_another_seed_is_broken():
    report = passing_report(DIMS, 3, SEED + 1)
    assert_judged_broken(judge(report), Broken.CHECK_VALUE)


@pytest.mark.parametrize("cache", ["cache_k", "cache_v"])
@pytest.mark.parametrize("row", [0, 1, 7, 8, 5])
def test_an_allocation_that_differed_before_the_call_is_broken_not_failed(cache, row):
    inputs = draw_inputs(DIMS, seed=SEED, draw=0)
    blocks = all_parts(DIMS, 1, SEED)
    before = {
        "cache_k": allocation_before(DIMS, inputs.cached_k),
        "cache_v": allocation_before(DIMS, inputs.cached_v),
    }
    before[cache][row] = 0
    blocks[0]["check"] = check_value(
        DIMS, inputs.q, inputs.k_new, inputs.v_new, before["cache_k"], before["cache_v"]
    )
    if row not in (5, 6):
        blocks[0][cache][row] = 0
    assert_judged_broken(judge(pack(blocks), draws=1), Broken.CHECK_VALUE)


def test_counts_taken_before_a_disagreeing_check_value_are_dropped():
    blocks = all_parts(DIMS, 3, SEED)
    blocks[0]["cache_v"][0, 0, 0] = MARK
    blocks[1]["out"][0, 0, 0] = FILL
    blocks[2]["check"] ^= 0x80000000
    assert_judged_broken(judge(pack(blocks)), Broken.CHECK_VALUE)


def test_judge_report_stops_at_the_first_disagreeing_draw(draws_made):
    blocks = all_parts(DIMS, 3, SEED)
    blocks[1]["check"] ^= 1
    assert_judged_broken(judge(pack(blocks)), Broken.CHECK_VALUE)
    assert draws_made == [0, 1]


# --- judge_report: refusals ---


@pytest.mark.parametrize(("parameter", "value", "match"), BAD_ARGUMENTS, ids=BAD_IDS)
@pytest.mark.parametrize("report", ["good", b"", None], ids=["good", "empty", "none"])
def test_judge_report_refuses_arguments_before_the_report(
    report, parameter, value, match, no_draw
):
    arguments = arguments_with(parameter, value)
    report = GOOD if report == "good" else report
    with pytest.raises(VerificationArgumentError, match=f"^{match}: "):
        judge_report(
            report,
            arguments["dims"],
            draws=arguments["draws"],
            seed=arguments["seed"],
            **TOLERANCE,
        )


@pytest.mark.parametrize(("name", "value"), BAD_TOLERANCES)
@pytest.mark.parametrize("report", ["good", None], ids=["good", "none"])
def test_judge_report_refuses_tolerances_before_the_report(
    report, name, value, no_draw
):
    report = GOOD if report == "good" else report
    with pytest.raises(VerificationArgumentError, match=f"^{name}: "):
        judge(report, **{name: value})


@pytest.mark.parametrize(
    "report", [bytearray(GOOD), memoryview(GOOD), GOOD.hex(), None, list(GOOD[:8])]
)
def test_judge_report_refuses_a_report_that_is_not_bytes(report, no_draw):
    with pytest.raises(TypeError, match="^report: must be bytes, got ") as caught:
        judge(report)
    assert str(caught.value).endswith(f"got {type(report).__name__}")


def test_judge_report_refuses_in_the_order_of_the_parameters(no_draw):
    with pytest.raises(VerificationArgumentError, match="^dims: "):
        judge(None, (2, 5), draws=0, seed=-1, rtol=-1.0)
    with pytest.raises(VerificationArgumentError, match=r"^dims\[1\]: "):
        judge(None, (3, 2, 4, 2, 3), draws=0, seed=-1, rtol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^draws: "):
        judge(None, draws=0, seed=-1, rtol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^seed: "):
        judge(None, seed=-1, rtol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^rtol: "):
        judge(None, rtol=-1.0, atol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^atol: "):
        judge(None, atol=-1.0)
    with pytest.raises(TypeError, match="^report: "):
        judge(None)


@pytest.mark.parametrize("missing", ["dims", "draws", "seed", "rtol", "atol"])
def test_judge_report_has_no_default_for(missing):
    arguments = {"dims": DIMS, "draws": 3, "seed": SEED, **TOLERANCE}
    del arguments[missing]
    with pytest.raises(TypeError, match=missing):
        judge_report(GOOD, **arguments)


def test_judge_report_parameters_are_keyword_only():
    with pytest.raises(TypeError):
        judge_report(GOOD, DIMS, 3, SEED, 0.0, 2**-6)
    with pytest.raises(TypeError):
        judge_report(GOOD, DIMS, 3, seed=SEED, **TOLERANCE)


def test_judge_report_has_no_start():
    with pytest.raises(TypeError, match="start"):
        judge(GOOD, start=3)


def test_judge_report_starts_nothing(monkeypatch):
    def refuse(*args, **kwargs):
        pytest.fail("judge_report started a process")

    monkeypatch.setattr("hilclaw.local_run.run", refuse)
    monkeypatch.setattr("subprocess.Popen", refuse)
    assert judge(GOOD) == judge(bytes(bytearray(GOOD)))


# --- run_bf16_sdpa_kv_cache_verification with a stand-in ---


def test_run_passes_a_conforming_report(stand_in):
    result = verify(stand_in(GOOD))
    assert_completed(result, Verdict.PASS, [(0, 0, 0)] * 3)
    assert result._fields == ("broken", "verdict", "counts", "run")


@pytest.mark.parametrize("dims", [DIMS, P0, ONE])
def test_the_process_gets_the_arguments_and_no_standard_input(dims, stand_in):
    executable = stand_in(passing_report(dims, 2, LAST))
    result = verify(executable, dims, draws=2, seed=LAST)
    assert_completed(result, Verdict.PASS, [(0, 0, 0)] * 2)
    expected = list(program_arguments(dims, draws=2, seed=LAST))
    call = stand_in.call()
    assert call["argv"] == expected
    assert result.run.command[1:] == (executable[1], *expected)
    assert call["stdin"] == ""


def test_p_is_not_on_the_command_line(stand_in):
    dims = (2, 99, 4, 2, 3)
    verify(stand_in(passing_report(dims, 1, SEED)), dims, draws=1)
    assert "97" not in stand_in.call()["argv"]
    assert len(stand_in.call()["argv"]) == 7


def test_cwd_and_env_reach_the_process(stand_in, tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    env = {**os.environ, "HILCLAW_TEST_MARK": "handed over"}
    result = verify(stand_in(GOOD), cwd=work, env=env)
    assert_completed(result, Verdict.PASS, [(0, 0, 0)] * 3)
    call = stand_in.call()
    assert os.path.samefile(call["cwd"], work)
    assert call["mark"] == "handed over"


def test_result_holds_the_capture_of_the_runner_without_the_report(stand_in):
    noise = GOOD[:9] + "café\n".encode()
    result = verify(stand_in(GOOD, stderr=noise))
    assert_completed(result, Verdict.PASS, [(0, 0, 0)] * 3)
    assert result.run.stderr == noise
    assert type(result.run.duration_s) is float


def test_run_fails_on_a_cache_difference_alone(stand_in):
    blocks = all_parts(DIMS, 3, SEED)
    blocks[2]["cache_k"][DIMS[0] + DIMS[1], 0, 0] = MARK
    result = verify(stand_in(pack(blocks)))
    assert_completed(result, Verdict.FAIL, [(0, 0, 0), (0, 0, 0), (0, 0, 1)])


def test_run_fails_on_out(stand_in):
    blocks = all_parts(DIMS, 3, SEED)
    blocks[0]["out"][...] = FILL
    result = verify(stand_in(pack(blocks)))
    assert_completed(result, Verdict.FAIL, [(24, 24, 0), (0, 0, 0), (0, 0, 0)])


def test_executable_prefix_may_be_a_list(stand_in):
    assert_completed(verify(list(stand_in(GOOD))), Verdict.PASS, [(0, 0, 0)] * 3)


def test_executable_as_one_path_is_the_whole_prefix(tmp_path):
    for executable in (sys.executable, Path(sys.executable)):
        result = verify(executable, cwd=tmp_path)
        assert_broken(result, Broken.EXIT_STATUS)
        assert result.run.command[1:] == ("2", "5", "4", "2", "3", "3", "7")


@pytest.mark.parametrize("stdout", ["good", b"end"], ids=["passing", "other"])
def test_timeout_is_broken_whatever_was_written(stdout, stand_in):
    stdout = GOOD if stdout == "good" else stdout
    result = verify(stand_in(stdout, sleep=30), timeout_s=2)
    assert_broken(result, Broken.TIMEOUT)
    assert result.run.timed_out is True


@pytest.mark.parametrize("status", [2, 3, 1])
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


def wrong_reports():
    blocks = all_parts(DIMS, 3, SEED)
    blocks[1]["check"] ^= 1
    failing = all_parts(DIMS, 3, SEED)
    failing[1]["cache_v"][0, 0, 0] = MARK
    return {
        "wrong-form": GOOD[:-1],
        "wrong-check-value": pack(blocks),
        "another-seed": passing_report(DIMS, 3, SEED + 1),
        "fail": pack(failing),
    }


@pytest.mark.parametrize("name", wrong_reports())
def test_run_and_judge_report_agree(name, stand_in):
    report = wrong_reports()[name]
    result = verify(stand_in(report))
    assert result[:3] == judge(report)
    assert result.run.returncode == 0
    if name == "fail":
        assert result.verdict is Verdict.FAIL
    else:
        assert result.broken is not None


@pytest.mark.parametrize(("parameter", "value", "match"), BAD_ARGUMENTS, ids=BAD_IDS)
def test_bad_arguments_raise_and_start_nothing(
    parameter, value, match, stand_in, no_draw
):
    arguments = arguments_with(parameter, value)
    with pytest.raises(VerificationArgumentError, match=f"^{match}: "):
        run_bf16_sdpa_kv_cache_verification(
            stand_in(GOOD),
            arguments["dims"],
            draws=arguments["draws"],
            seed=arguments["seed"],
            **TOLERANCE,
            timeout_s=TIMEOUT,
        )
    assert not stand_in.started


@pytest.mark.parametrize(("name", "value"), BAD_TOLERANCES)
def test_bad_tolerances_raise_and_start_nothing(name, value, stand_in, no_draw):
    with pytest.raises(VerificationArgumentError, match=f"^{name}: "):
        verify(stand_in(GOOD), **{name: value})
    assert not stand_in.started


def test_run_refuses_in_the_order_of_the_parameters(no_draw):
    with pytest.raises(VerificationArgumentError, match="^dims: "):
        verify((), (2, 5), seed=-1, rtol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^seed: "):
        verify((), seed=-1, rtol=-1.0)
    with pytest.raises(VerificationArgumentError, match="^atol: "):
        verify(7, atol=-1.0, timeout_s=0)
    with pytest.raises(TypeError):
        verify(7, timeout_s=0)
    with pytest.raises(ValueError, match="empty"):
        verify((), timeout_s=0)


@pytest.mark.parametrize("executable", [(), []])
def test_empty_executable_prefix(executable, no_draw):
    with pytest.raises(ValueError, match="empty"):
        verify(executable)


@pytest.mark.parametrize("executable", [7, None, 1.5])
def test_executable_of_the_wrong_type(executable, no_draw):
    with pytest.raises(TypeError):
        verify(executable)


@pytest.mark.parametrize(
    "missing", ["dims", "draws", "seed", "rtol", "atol", "timeout_s"]
)
def test_run_has_no_default_for(missing, stand_in):
    arguments = {"dims": DIMS, "draws": 3, "seed": SEED}
    arguments |= {**TOLERANCE, "timeout_s": TIMEOUT}
    del arguments[missing]
    with pytest.raises(TypeError, match=missing):
        run_bf16_sdpa_kv_cache_verification(stand_in(GOOD), **arguments)
    assert not stand_in.started


def test_run_parameters_are_keyword_only(stand_in):
    with pytest.raises(TypeError):
        run_bf16_sdpa_kv_cache_verification(
            stand_in(GOOD), DIMS, 3, SEED, 0.0, 2**-6, TIMEOUT
        )
    with pytest.raises(TypeError, match="start"):
        verify(stand_in(GOOD), start=3)
    assert not stand_in.started


def test_executable_that_does_not_exist():
    with pytest.raises(ProgramNotFoundError):
        verify("hilclaw-no-such-bf16-sdpa-kv-cache-verification-executable")


def test_time_limit_errors_are_those_of_the_runner(stand_in):
    with pytest.raises(ValueError, match="timeout_s"):
        verify(stand_in(GOOD), timeout_s=0)
    assert not stand_in.started


# --- real clang ---

BUILD_TIMEOUT = 120
STRICT = ("-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2")
# A test value, not a tolerance of the harness: above ADR-0165 decision 9's 2.154e-3.
DECODE_TOLERANCE = {"rtol": 0.0, "atol": 2.2e-3}

KERNEL = """\
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
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
    size_t cached = l - m, group = h / h_kv;
    float scale = 1.0f / sqrtf((float)d), *w = malloc(l * sizeof *w);
    memcpy(cache_k + cached * h_kv * d, k_new, m * h_kv * d * sizeof(uint16_t));
    memcpy(cache_v + cached * h_kv * d, v_new, m * h_kv * d * sizeof(uint16_t));
@EXTRA@
    if (w == NULL)
        abort();
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < h; j++) {
            size_t g = j / group, n = cached + i + 1;
            const uint16_t *qr = &q[(i * h + j) * d];
            float top = -INFINITY, sum = 0.0f;
            for (size_t t = 0; t < n; t++) {
                float dot = 0.0f;
                for (size_t e = 0; e < d; e++)
                    dot += widened(qr[e]) * widened(cache_k[(t * h_kv + g) * d + e]);
                w[t] = dot * scale;
                top = w[t] > top ? w[t] : top;
            }
            for (size_t t = 0; t < n; t++) {
                w[t] = expf(w[t] - top);
                sum += w[t];
            }
            for (size_t e = 0; e < d; e++) {
                float acc = 0.0f;
                for (size_t t = 0; t < n; t++)
                    acc += w[t] * widened(cache_v[(t * h_kv + g) * d + e]);
                out[(i * h + j) * d + e] = rounded(acc / sum);
            }
        }
    free(w);
}
"""

KERNELS = {
    "plain": "",
    "guard-write": "    cache_k[l * h_kv * d] = 0x3F80;",
}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    if os.name != "posix":
        pytest.skip("a verification executable needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    directory = tmp_path_factory.mktemp("bf16_sdpa_kv_cache_verification")
    signature = sdpa_kv_cache_bf16_contract.PROTOTYPE.removesuffix(";")
    paths = {}
    for name, extra in KERNELS.items():
        source = directory / f"{name}.c"
        text = KERNEL.replace("@SIGNATURE@", signature).replace("@EXTRA@", extra)
        source.write_text(text, encoding="ascii", newline="\n")
        output = directory / name
        result = build_bf16_verification_executable(
            "sdpa_kv_cache",
            source,
            output,
            timeout_s=BUILD_TIMEOUT,
            flags=STRICT,
            trailing_flags=("-lm",),
        )
        assert result.ok, result.log
        paths[name] = output
    return paths


@pytest.mark.parametrize("dims", [DIMS, (3, 7, 4, 2, 8), P0])
def test_real_clang_plain_kernel_passes(built, dims):
    result = verify(built["plain"], dims, draws=2)
    assert_completed(result, Verdict.PASS, [(0, 0, 0)] * 2)
    assert result.run.command[0] == str(built["plain"])


@pytest.mark.parametrize(
    ("dims", "draws"), [((1, 128, 32, 8, 64), 2), ((128, 128, 32, 8, 64), 1)]
)
def test_real_clang_plain_kernel_passes_at_the_s128_shapes(built, dims, draws):
    result = verify(built["plain"], dims, draws=draws, **DECODE_TOLERANCE)
    assert_completed(result, Verdict.PASS, [(0, 0, 0)] * draws)


@pytest.mark.parametrize("dims", [DIMS, (1, 128, 32, 8, 64)])
def test_real_clang_kernel_writing_a_trailing_guard_fails(built, dims):
    result = verify(built["guard-write"], dims, draws=2)
    assert_completed(result, Verdict.FAIL, [(0, 0, 1)] * 2)
