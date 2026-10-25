"""Three-state calibration of the bf16 verification run per kind (ADR-0163 decision 9; ADR-0003)."""

import os
import secrets
import shutil
from pathlib import Path

import pytest

from hilclaw.harness.bf16_rope_verification import run_bf16_rope_verification
from hilclaw.harness.bf16_verification import Verdict, run_bf16_verification
from hilclaw.harness.bf16_verification_build import build_bf16_verification_executable

KERNELS = Path(__file__).parent / "calibration"
FLAGS = ("-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2")
TRAILING_FLAGS = ("-lm",)
BUILD_TIMEOUT = 120
RUN_TIMEOUT = 60

# kind: (dims, known seed, tolerance). The violating kernels hold draw 0 of the
# known seed at these dims. Test values, not tolerances of the harness.
KINDS = {
    # |c| < 4: conforming within 2**-8 |ref| (half the bound); a left-out term misses by > 0.23, bound < 0.033.
    "gemm": ((3, 4, 5), 2026, {"rtol": 2**-7, "atol": 1e-3}),
    # conforming 0 or 2**-8 at |ref| >= 1 (half the bound); a - b misses by >= 1 - 2**-8, bound < 0.017.
    "elementwise_add": ((3, 5), 2026, {"rtol": 2**-7, "atol": 1e-3}),
    # |ref| in [0.25, 2]: conforming within 2**-8 |ref| plus fp32 steps; a left-out w moves by |1/w - 1|, verdict only.
    "rmsnorm": ((3, 5), 2026, {"rtol": 2**-7, "atol": 1e-3}),
    # conforming within 0.00437 |ref| (ADR-0160 d5), atol for |ref| >= 0.00138; sigma(-g) misses by >= 0.39 |ref|.
    "swiglu": ((3, 5), 2026, {"rtol": 2**-7, "atol": 1e-3}),
}

# rope: (dims (m, h, d), known seed, start position P, tolerance). The violating
# kernel holds draw 0 of the known seed at these dims and P. Test values.
# conforming within 2**-8 + 2**-21 (ADR-0164 d10, half the bound); at row 0 swapped cos and sin miss by >= 1.
ROPE = ((3, 2, 4), 2026, 0, {"rtol": 0.0, "atol": 2**-7})

# state: (verdict of the functional test, verdict of the contract run)
STATES = {
    "conforming": (Verdict.PASS, Verdict.PASS),
    "failing": (Verdict.FAIL, Verdict.FAIL),
    "violating": (Verdict.PASS, Verdict.FAIL),
}


@pytest.fixture(scope="session")
def executables(tmp_path_factory):
    if os.name != "posix":
        pytest.skip("a verification executable needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    directory = tmp_path_factory.mktemp("bf16_calibration")
    built = {}
    for kind in KINDS:
        for state in STATES:
            built[kind, state] = directory / f"{kind}_{state}"
            result = build_bf16_verification_executable(
                kind,
                KERNELS / f"{kind}_bf16_{state}.c",
                built[kind, state],
                timeout_s=BUILD_TIMEOUT,
                flags=FLAGS,
                trailing_flags=TRAILING_FLAGS,
            )
            assert result.ok, result.log
    return built


def verdict(executable, kind, draws, seed):
    dims, _, tolerance = KINDS[kind]
    result = run_bf16_verification(
        executable,
        kind,
        dims,
        draws=draws,
        seed=seed,
        **tolerance,
        timeout_s=RUN_TIMEOUT,
    )
    shown = (seed, result.broken, result.run.returncode, result.run.stderr)
    assert result.broken is None, shown
    return result.verdict, f"seed {seed}, counts {result.counts}"


def seed_taken_at_run_time(known):
    seed = secrets.randbits(64)
    while seed == known:
        seed = secrets.randbits(64)
    return seed


@pytest.mark.parametrize("draws", [1, 3])
@pytest.mark.parametrize("state", STATES)
@pytest.mark.parametrize("kind", KINDS)
def test_functional_test_and_contract_run_give_the_verdicts_of_the_state(
    executables, kind, state, draws
):
    functional, contract = STATES[state]
    executable = executables[kind, state]
    known = KINDS[kind][1]
    given, shown = verdict(executable, kind, 1, known)
    assert given is functional, shown
    given, shown = verdict(executable, kind, draws, seed_taken_at_run_time(known))
    assert given is contract, shown


@pytest.fixture(scope="session")
def rope_executables(tmp_path_factory):
    if os.name != "posix":
        pytest.skip("a verification executable needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    directory = tmp_path_factory.mktemp("bf16_rope_calibration")
    built = {}
    for state in STATES:
        built[state] = directory / f"rope_{state}"
        result = build_bf16_verification_executable(
            "rope",
            KERNELS / f"rope_bf16_{state}.c",
            built[state],
            timeout_s=BUILD_TIMEOUT,
            flags=FLAGS,
        )
        assert result.ok, result.log
    return built


def rope_verdict(executable, draws, seed):
    dims, _, start, tolerance = ROPE
    result = run_bf16_rope_verification(
        executable,
        dims,
        start=start,
        draws=draws,
        seed=seed,
        **tolerance,
        timeout_s=RUN_TIMEOUT,
    )
    shown = (seed, result.broken, result.run.returncode, result.run.stderr)
    assert result.broken is None, shown
    return result.verdict, f"seed {seed}, counts {result.counts}"


@pytest.mark.parametrize("draws", [1, 3])
@pytest.mark.parametrize("state", STATES)
def test_rope_functional_test_and_contract_run_give_the_verdicts_of_the_state(
    rope_executables, state, draws
):
    functional, contract = STATES[state]
    executable = rope_executables[state]
    known = ROPE[1]
    given, shown = rope_verdict(executable, 1, known)
    assert given is functional, shown
    given, shown = rope_verdict(executable, draws, seed_taken_at_run_time(known))
    assert given is contract, shown
