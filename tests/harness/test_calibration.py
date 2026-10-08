"""Three-state calibration of the verification harness for gemm (ADR-0003; ADR-0017 decision 8)."""

import os
import secrets
import shutil
from pathlib import Path

import pytest

from hilclaw.harness.verification import Verdict, run_verification
from hilclaw.harness.verification_build import build_verification_executable

KERNELS = Path(__file__).parent / "calibration"
FLAGS = ("-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2")
BUILD_TIMEOUT = 120
RUN_TIMEOUT = 60

# The inputs gemm_violating.c is written for: draw 0 of this seed at this shape.
SHAPE = {"m": 3, "k": 4, "n": 5}
KNOWN_SEED = 2026
# Test values, not tolerances of the harness.
TOLERANCE = {"rtol": 1e-5, "atol": 1e-3}

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
    directory = tmp_path_factory.mktemp("calibration")
    built = {}
    for state in STATES:
        built[state] = directory / state
        result = build_verification_executable(
            KERNELS / f"gemm_{state}.c",
            built[state],
            timeout_s=BUILD_TIMEOUT,
            flags=FLAGS,
        )
        assert result.ok, result.log
    return built


def verdict(executable, draws, seed):
    result = run_verification(
        executable,
        **SHAPE,
        draws=draws,
        seed=seed,
        **TOLERANCE,
        timeout_s=RUN_TIMEOUT,
    )
    shown = (seed, result.broken, result.run.returncode, result.run.stderr)
    assert result.broken is None, shown
    return result.verdict, f"seed {seed}, counts {result.counts}"


def seed_taken_at_run_time():
    seed = secrets.randbits(64)
    while seed == KNOWN_SEED:
        seed = secrets.randbits(64)
    return seed


@pytest.mark.parametrize("draws", [1, 3])
@pytest.mark.parametrize("state", STATES)
def test_functional_test_and_contract_run_give_the_verdicts_of_the_state(
    executables, state, draws
):
    functional, contract = STATES[state]
    given, shown = verdict(executables[state], 1, KNOWN_SEED)
    assert given is functional, shown
    given, shown = verdict(executables[state], draws, seed_taken_at_run_time())
    assert given is contract, shown
