import dataclasses
import io
import json
import os
import shutil
import subprocess

import first_run_stubs as stubs
import openmp_clang
import pytest

from hilclaw import (
    artifacts,
    bring_in,
    cas,
    events,
    given_attempt,
    given_eval,
    instance,
    keys,
    layout,
    mock_backend,
    run_state,
    standin_image,
    standin_profile,
    start_instance,
    targets,
    tools,
)
from hilclaw.given_eval import EXIT_STATUS, main

KERNEL = b"""#include <stddef.h>

void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a,
                  const float *restrict b, float *restrict c)
{
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < n; j++) {
            float sum = 0.0f;
            for (size_t p = 0; p < k; p++)
                sum += a[i * k + p] * b[p * n + j];
            c[i * n + j] = sum;
        }
}
"""
WRONG_KERNEL = KERNEL.replace(b"= sum;", b"= sum + 1.0f;")
PROFILE = {
    "schema_version": 1,
    "accelerator": standin_profile.ACCELERATOR,
    "revision": "test-revision",
    "toolchain": {"clang": "test"},
    "host": {"cpu": "test", "os": "test"},
    "hw_source": "external",
}
OP = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": {"m": 4, "k": 8, "n": 4},
    "dtype": "fp32",
    "layout": "row_major",
}
IDENTITY = {
    "GIT_AUTHOR_NAME": "Test Author",
    "GIT_AUTHOR_EMAIL": "author@example.invalid",
    "GIT_COMMITTER_NAME": "Test Committer",
    "GIT_COMMITTER_EMAIL": "committer@example.invalid",
}
GIT = shutil.which("git")
ATTEMPT = {"round": 0, "candidate": 1, "attempt": 1}
VERIFIED = {"attempts": [{"attempt": 1, "standing": "verified", "checks": []}]}
NOT_VERIFIED = {"attempts": [{"attempt": 1, "standing": "not_verified", "checks": []}]}
UNDETERMINED = {"attempts": [{"attempt": 1, "standing": "undetermined", "checks": []}]}
TIMING = {"outcome": "converged", "unit": "ns", "intervals": [30, 10, 20, 40]}


def request(profile=PROFILE, **members):
    made = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(profile).name, "record": profile},
        "op_signature": {"key": keys.op_signature_key(OP).name, "record": OP},
        "objective": {
            "objectives": [{"type": "latency_minimisation"}],
            "constraints": [],
        },
        "candidates_per_round": 1,
        "n_max": 6,
        "draws": 1,
        "tolerance": {"rtol": 1e-4, "atol": 1e-5},
        "round_budget": 1,
    }
    made.update(members)
    return {name: value for name, value in made.items() if value is not None}


def git(root, *args):
    return subprocess.run(
        [GIT, "-C", str(root), *args], capture_output=True, check=True
    ).stdout.decode()


class Bench:
    def __init__(self, tmp_path, monkeypatch, repository=True):
        self.tmp = tmp_path
        self.root = tmp_path / "data"
        self.root.mkdir()
        for name, value in IDENTITY.items():
            monkeypatch.setenv(name, value)
        if repository:
            git(self.root, "init", "-q", "-b", "main")
        self.request = tmp_path / "request.json"
        self.code = tmp_path / "given.c"
        self.out = io.BytesIO()
        self.err = io.BytesIO()
        self.write(request(), KERNEL)

    def write(self, document, code=KERNEL):
        self.request.write_text(json.dumps(document), encoding="utf-8")
        if code is not None:
            self.code.write_bytes(code)

    def main(self, *args, source=None):
        argv = [self.request, self.code] if not args else args
        status = main(
            [str(a) for a in argv],
            source=source or (lambda: self.root),
            stdout=self.out,
            stderr=self.err,
        )
        return status

    def summary(self):
        return json.loads(self.out.getvalue())

    def told(self):
        return [json.loads(line) for line in self.err.getvalue().splitlines()]

    def runs(self):
        directory = self.root / "runs"
        return sorted(p.name for p in directory.iterdir()) if directory.exists() else []

    def files(self):
        return sorted(
            p.relative_to(self.root).as_posix()
            for p in self.root.rglob("*")
            if ".git" not in p.relative_to(self.root).parts
        )


@pytest.fixture
def bench(tmp_path, monkeypatch):
    return Bench(tmp_path, monkeypatch)


def faked(monkeypatch, answers):
    real = tools.call
    asked = []

    def call(registry, name, req):
        asked.append(name)
        if name in answers:
            answer = answers[name]
            if isinstance(answer, Exception):
                raise answer
            return answer
        return real(registry, name, req)

    monkeypatch.setattr(tools, "call", call)
    return asked


def default_answers(**more):
    answers = {
        "correctness.check": {"outcome": "pass"},
        "checks.read": VERIFIED,
        "board.run": TIMING,
    }
    answers.update(more)
    return answers


def state_of(root, run_id):
    return json.loads(layout.run_file(root, run_id, "STATE.json").read_bytes())


# The command with the real clang at cpu_standin (D29), through a stub docker.


@pytest.fixture
def real_clang(tmp_path, monkeypatch):
    if not hasattr(os, "getuid") or shutil.which("clang") is None or GIT is None:
        pytest.skip("the stand-in build needs a host clang, git and os.getuid")
    openmp_clang.need()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "docker.ndjson"
    stubs.install(
        bin_dir,
        {
            "docker_log": str(log),
            "clang": shutil.which("clang"),
            "unshare": working_unshare(),
            "git": GIT,
        },
    )
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv(standin_image.ENV_IMAGE, "registry.example/hilclaw-clang:1")
    return log


def working_unshare():
    path = shutil.which("unshare")
    if path is None:
        return None
    probe = subprocess.run(
        [path, *stubs.NAMESPACE, "/bin/sh", "-c", 'test "$$" -eq 1'],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        timeout=60,
    )
    return path if probe.returncode == 0 else None


def test_a_right_given_kernel_is_measured_with_the_real_clang(
    real_clang, bench, tmp_path
):
    assert bench.main() == 0
    summary = bench.summary()
    (run_id,) = bench.runs()
    digest = instance.given_code_of(bench.root, run_id)
    assert summary["outcome"] == "measured"
    assert summary["run_id"] == run_id
    assert summary["place"] == {"given_code": digest}
    assert summary["sim"] == {"outcome": "pass", "standing": "verified"}
    assert summary["board"] == {"outcome": "pass", "standing": "verified"}
    assert summary["timing"]["outcome"] in ("converged", "not_converged")
    assert summary["timing"]["unit"] == "ns"
    assert summary["timing"]["median"] > 0
    assert bench.err.getvalue() == b""
    state = state_of(bench.root, run_id)
    assert (state["round"], state["run_status"]) == (1, "over")
    steps = [line["data"]["step"] for line in events.read(bench.root, run_id).events]
    assert steps == [
        "correctness_check_sim_v2",
        "correctness_check_sim_v2",
        "correctness_check_board_v2",
        "correctness_check_board_v2",
        "board_run_timing_v3",
        "board_run_timing_v3",
    ]
    attempt = layout.attempt_artefact(bench.root, run_id, 0, 1, 1, "output").parent
    assert sorted(p.name for p in attempt.iterdir()) == ["output"]
    assert (attempt / "output" / "given.c").read_bytes() == KERNEL
    assert git(bench.root, "status", "--porcelain", "--", "runs") == ""
    assert "runs/" + run_id + "/STATE.json" in git(bench.root, "ls-files", "runs", "db")
    builds = [e for e in stubs.read_log(real_clang) if e["container"] == "build"]
    assert builds


def test_a_wrong_given_kernel_fails_at_sim_and_still_ends_the_run(real_clang, bench):
    bench.write(request(), WRONG_KERNEL)
    assert bench.main() == EXIT_STATUS["not_measured"]
    summary = bench.summary()
    run_id = summary["run_id"]
    assert summary["sim"] == {"outcome": "fail", "standing": "not_verified"}
    assert "board" not in summary
    assert "timing" not in summary
    assert bench.err.getvalue() == b""
    assert state_of(bench.root, run_id)["run_status"] == "over"
    steps = {line["data"]["step"] for line in events.read(bench.root, run_id).events}
    assert steps == {"correctness_check_sim_v2"}
    assert git(bench.root, "status", "--porcelain", "--", "runs") == ""


# The steps, with the evaluation tools answered by a fake (no clang needed).


@pytest.mark.skipif(GIT is None, reason="run.commit needs git")
def test_the_steps_are_made_in_round_zero_s_order(bench, monkeypatch):
    asked = faked(monkeypatch, default_answers())
    assert bench.main() == 0
    assert asked == [
        "run.fresh",
        "state.write",
        "key.store",
        "correctness.check",
        "checks.read",
        "correctness.check",
        "checks.read",
        "board.run",
        "round.end",
        "run.commit",
    ]
    summary = bench.summary()
    assert summary["timing"] == {"outcome": "converged", "median": 25, "unit": "ns"}
    assert list(summary) == ["outcome", "run_id", "place", "sim", "board", "timing"]
    run_id = summary["run_id"]
    assert state_of(bench.root, run_id) == {
        **given_eval.FIRST_STATE,
        "round": 1,
        "run_status": "over",
    }
    stored = json.loads(
        layout.run_file(bench.root, run_id, "instance.json").read_bytes()
    )
    assert (stored["schema_version"], stored["round_budget"]) == (3, 1)
    assert bench.out.getvalue().endswith(b"\n")


@pytest.mark.skipif(GIT is None, reason="run.commit needs git")
def test_a_request_without_round_budget_is_started_with_one(bench, monkeypatch):
    faked(monkeypatch, default_answers())
    bench.write(request(round_budget=None))
    assert bench.main() == 0
    run_id = bench.summary()["run_id"]
    stored = json.loads(
        layout.run_file(bench.root, run_id, "instance.json").read_bytes()
    )
    assert stored["round_budget"] == 1
    assert list(stored).index("round_budget") > list(stored).index("tolerance")


@pytest.mark.skipif(GIT is None, reason="run.commit needs git")
@pytest.mark.parametrize(
    ("answers", "summary"),
    [
        (
            {"board.run": {"outcome": "broken", "condition": "exit_status"}},
            {"timing": {"outcome": "broken", "condition": "exit_status"}},
        ),
        (
            {"checks.read": NOT_VERIFIED},
            {"sim": {"outcome": "pass", "standing": "not_verified"}},
        ),
        (
            {"checks.read": {"attempts": []}},
            {"sim": {"outcome": "pass", "standing": None}},
        ),
    ],
    ids=["broken-timing", "not-verified", "no-entry"],
)
def test_an_attempt_that_does_not_stand_is_not_measured(
    bench, monkeypatch, answers, summary
):
    faked(monkeypatch, default_answers(**answers))
    status = bench.main()
    made = bench.summary()
    for name, value in summary.items():
        assert made[name] == value
    assert status == EXIT_STATUS["not_measured"]
    assert state_of(bench.root, made["run_id"])["run_status"] == "over"


@pytest.mark.skipif(GIT is None, reason="run.commit needs git")
def test_a_timing_without_intervals_is_measured_with_no_median(bench, monkeypatch):
    faked(monkeypatch, default_answers(**{"board.run": {"outcome": "converged"}}))
    assert bench.main() == 0
    assert bench.summary()["timing"] == {"outcome": "converged"}


def failure(kind="tool_kind"):
    return tools.ToolFailure(kind, "injected")


@pytest.mark.skipif(GIT is None, reason="run.commit needs git")
@pytest.mark.parametrize(
    ("answers", "outcome", "step", "point"),
    [
        (
            {"correctness.check": failure(), "checks.read": UNDETERMINED},
            "check_failed",
            "correctness.check",
            "sim",
        ),
        ({"checks.read": failure()}, "check_failed", "checks.read", "sim"),
        ({"board.run": failure()}, "board_run_failed", "board.run", None),
    ],
    ids=["check", "checks-read", "board-run"],
)
def test_an_evaluation_failure_is_told_and_the_round_still_ends(
    bench, monkeypatch, answers, outcome, step, point
):
    asked = faked(monkeypatch, default_answers(**answers))
    assert bench.main() == EXIT_STATUS[outcome]
    summary = bench.summary()
    run_id = summary["run_id"]
    assert bench.told() == [
        {
            "outcome": outcome,
            "run_id": run_id,
            "step": step,
            "kind": "tool_kind",
            "message": "injected",
        }
    ]
    assert asked[-2:] == ["round.end", "run.commit"]
    if point is None:
        assert summary["timing"] == {"failure": "tool_kind"}
    elif step == "checks.read":
        assert summary[point] == {"outcome": "pass", "standing_failure": "tool_kind"}
        assert "board" not in summary
    else:
        assert summary[point] == {"failure": "tool_kind", "standing": "undetermined"}
        assert "board" not in summary
    assert state_of(bench.root, run_id)["run_status"] == "over"


@pytest.mark.skipif(GIT is None, reason="run.commit needs git")
def test_a_key_store_failure_is_told_and_round_zero_goes_on(bench, monkeypatch):
    asked = faked(
        monkeypatch,
        default_answers(**{"key.store": failure(), "board.run": failure("late")}),
    )
    assert bench.main() == EXIT_STATUS["key_store_failed"]
    summary = bench.summary()
    assert asked == [
        "run.fresh",
        "state.write",
        "key.store",
        "correctness.check",
        "checks.read",
        "correctness.check",
        "checks.read",
        "board.run",
        "round.end",
        "run.commit",
    ]
    assert [(t["outcome"], t["step"], t["kind"]) for t in bench.told()] == [
        ("key_store_failed", "key.store", "tool_kind"),
        ("board_run_failed", "board.run", "late"),
    ]
    assert summary["sim"] == {"outcome": "pass", "standing": "verified"}
    assert summary["timing"] == {"failure": "late"}


@pytest.mark.skipif(GIT is None, reason="run.commit needs git")
def test_a_placement_that_fails_goes_to_round_end(bench, monkeypatch):
    asked = faked(monkeypatch, default_answers())
    real_start = given_eval._started

    def started(document, root, code_file):
        told = real_start(document, root, code_file)
        digest = instance.given_code_of(root, told["run_id"])
        cas.blob_path(root, digest).unlink()
        return told

    monkeypatch.setattr(given_eval, "_started", started)
    assert bench.main() == EXIT_STATUS["place_failed"]
    summary = bench.summary()
    assert summary["place"] == {"failure": given_attempt.KIND_GIVEN_CODE_MISSING}
    assert "sim" not in summary
    assert asked == ["run.fresh", "state.write", "key.store", "round.end", "run.commit"]
    (told,) = bench.told()
    assert (told["outcome"], told["step"], told["run_id"]) == (
        "place_failed",
        "given.place",
        summary["run_id"],
    )


def test_an_existing_output_is_a_stop(bench, monkeypatch):
    asked = faked(monkeypatch, default_answers())

    def place(root, run_id):
        raise failure(given_attempt.KIND_OUTPUT_EXISTS)

    monkeypatch.setattr(given_attempt, "place", place)
    assert bench.main() == EXIT_STATUS["place_failed"]
    assert bench.out.getvalue() == b""
    (told,) = bench.told()
    assert told["kind"] == "output_exists"
    assert told["run_id"] == bench.runs()[0]
    assert asked == ["run.fresh", "state.write", "key.store"]


@pytest.mark.parametrize(
    ("name", "outcome", "before"),
    [
        ("run.fresh", "state_write_failed", []),
        ("state.write", "state_write_failed", ["run.fresh"]),
        ("round.end", "round_end_failed", None),
        ("run.commit", "run_commit_failed", None),
    ],
)
def test_a_failure_of_a_round_step_stops_with_its_status_and_run_id(
    bench, monkeypatch, name, outcome, before
):
    asked = faked(monkeypatch, default_answers(**{name: failure()}))
    assert bench.main() == EXIT_STATUS[outcome]
    assert bench.out.getvalue() == b""
    (told,) = bench.told()
    assert told == {
        "outcome": outcome,
        "run_id": bench.runs()[0],
        "step": name,
        "kind": "tool_kind",
        "message": "injected",
    }
    assert asked[-1] == name
    if before is not None:
        assert asked[:-1] == before


def test_a_run_that_is_not_fresh_is_not_entered(bench, monkeypatch):
    asked = faked(monkeypatch, {"run.fresh": {"fresh": False}})
    assert bench.main() == EXIT_STATUS["not_fresh"]
    assert bench.told() == [{"outcome": "not_fresh", "run_id": bench.runs()[0]}]
    assert asked == ["run.fresh"]
    assert not layout.run_file(bench.root, bench.runs()[0], "STATE.json").exists()


def test_a_run_commit_in_a_data_root_without_git_fails(tmp_path, monkeypatch):
    bench = Bench(tmp_path, monkeypatch, repository=False)
    faked(monkeypatch, default_answers())
    assert bench.main() == EXIT_STATUS["run_commit_failed"]
    (told,) = bench.told()
    assert (told["step"], told["kind"]) == ("run.commit", "no_repository")
    assert state_of(bench.root, told["run_id"])["run_status"] == "over"


def test_an_unexpected_exception_after_the_start_is_a_fault_with_the_run_id(
    bench, monkeypatch
):
    faked(monkeypatch, default_answers(**{"key.store": RuntimeError("boom")}))
    assert bench.main() == EXIT_STATUS["fault"]
    assert bench.told() == [
        {"outcome": "fault", "fault": "RuntimeError", "run_id": bench.runs()[0]}
    ]


def test_an_unexpected_exception_before_the_start_is_a_fault(bench, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(given_eval, "_started", broken)
    assert bench.main() == EXIT_STATUS["fault"]
    assert bench.told() == [{"outcome": "fault", "fault": "RuntimeError"}]


def test_an_unrecorded_given_code_stops_with_the_run_id(bench, monkeypatch):
    def refuse(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(artifacts, "add_record", refuse)
    assert bench.main() == EXIT_STATUS["given_code_unrecorded"]
    (told,) = bench.told()
    assert told["outcome"] == "given_code_unrecorded"
    assert told["run_id"] == bench.runs()[0]
    assert bench.out.getvalue() == b""


# Refusals before anything is written.


def assert_refused(bench, outcome, status=None):
    before = bench.files()
    assert bench.main() == (status or EXIT_STATUS[outcome])
    assert bench.out.getvalue() == b""
    (told,) = bench.told()
    assert told["outcome"] == outcome
    assert "run_id" not in told
    assert bench.files() == before
    return told


@pytest.mark.parametrize("count", [0, 1, 3])
def test_not_two_arguments_is_bad_usage(bench, count):
    args = [bench.request, bench.code, bench.code][:count]
    before = bench.files()
    status = main(
        [str(a) for a in args],
        source=lambda: bench.root,
        stdout=bench.out,
        stderr=bench.err,
    )
    assert status == EXIT_STATUS["bad_usage"]
    assert bench.told()[0]["outcome"] == "bad_usage"
    assert bench.files() == before


def test_a_missing_request_is_unreadable_input(bench):
    bench.request.unlink()
    assert_refused(bench, "unreadable_input")


@pytest.mark.parametrize(
    "content", [b"{", b"[]", b'{"a": 1, "a": 2}', b"\xef\xbb\xbf{}", b"NaN"]
)
def test_a_request_that_is_no_json_object_is_bad_input(bench, content):
    bench.request.write_bytes(content)
    assert_refused(bench, "bad_input")


def test_a_missing_c_file_is_bad_given_code(bench):
    bench.code.unlink()
    assert_refused(bench, "bad_given_code")


def test_an_oversize_c_file_is_bad_given_code(bench):
    bench.code.write_bytes(b" " * (bring_in.MAX_FILE_BYTES + 1))
    told = assert_refused(bench, "bad_given_code")
    assert str(bring_in.MAX_FILE_BYTES) in told["reason"]


def test_a_directory_as_c_file_is_bad_given_code(bench):
    bench.code.unlink()
    bench.code.mkdir()
    assert_refused(bench, "bad_given_code")


@pytest.mark.parametrize("accelerator", [mock_backend.NAME, "vendor_gpu"])
def test_a_target_outside_instance_start_is_refused(bench, accelerator):
    bench.write(request({**PROFILE, "accelerator": accelerator}))
    told = assert_refused(bench, "target_refused")
    assert "cpu_standin" in told["reason"]


def test_a_request_without_an_accelerator_is_left_to_the_start(bench):
    document = request()
    del document["hw_profile"]
    bench.write(document)
    assert_refused(bench, "invalid")


def test_a_request_missing_a_required_member_is_refused(bench):
    bench.write(request(draws=None))
    told = assert_refused(bench, "missing_members")
    assert told["missing"] == ["draws"]


def test_a_value_json_cannot_hold_is_unwritable(bench):
    bench.request.write_text(
        json.dumps(request()).replace('"n_max": 6', '"n_max": 6, "x": 1e400'),
        encoding="utf-8",
    )
    assert_refused(bench, "unwritable_value")


@pytest.mark.parametrize("budget", [2, 0, True, 1.0, "1", None])
def test_a_round_budget_other_than_one_is_refused(bench, budget):
    document = request()
    document["round_budget"] = budget
    bench.write(document)
    assert_refused(bench, "round_budget_refused")


def test_a_compile_settings_request_is_refused(bench):
    bench.write(request(schema_version=2, candidate_kind="compile_settings"))
    assert_refused(bench, "given_code_refused")


def test_more_than_one_candidate_per_round_is_refused(bench):
    bench.write(request(candidates_per_round=2))
    assert_refused(bench, "given_code_refused")


def test_a_request_holding_given_code_is_invalid(bench):
    bench.write(request(given_code="ab" * 32))
    assert_refused(bench, "invalid")


def test_a_request_giving_a_run_id_is_refused(bench):
    bench.write(request(run_id="r1"))
    assert_refused(bench, "given_run_id")


def test_no_data_root_is_refused(bench):
    before = bench.files()
    status = bench.main(source=lambda: bench.tmp / "missing")
    assert status == EXIT_STATUS["no_data_root"]
    assert bench.told()[0]["outcome"] == "no_data_root"
    assert bench.files() == before


def test_the_data_root_is_not_asked_for_a_refused_request(bench):
    asked = []
    bench.write(request(round_budget=2))
    bench.main(source=lambda: asked.append(1) or bench.root)
    assert asked == []


# The streams.


class Short(io.BytesIO):
    def write(self, data):
        super().write(data[:1])
        return 1


class Failing(io.BytesIO):
    def write(self, data):
        raise OSError("closed")


def test_no_standard_output_is_a_fault(bench, monkeypatch):
    monkeypatch.setattr(given_eval, "_standard", lambda name: None)
    status = main([str(bench.request), str(bench.code)], stderr=bench.err)
    assert status == EXIT_STATUS["fault"]
    assert bench.told()[0]["outcome"] == "fault"
    assert bench.runs() == []


@pytest.mark.skipif(GIT is None, reason="run.commit needs git")
@pytest.mark.parametrize("stream", [Short, Failing])
def test_a_summary_that_cannot_be_written_is_a_fault_naming_the_run(
    bench, monkeypatch, stream
):
    faked(monkeypatch, default_answers())
    bench.out = stream()
    assert bench.main() == EXIT_STATUS["fault"]
    (told,) = bench.told()
    assert (told["outcome"], told["run_id"]) == ("fault", bench.runs()[0])


def test_a_failing_standard_error_does_not_raise(bench):
    bench.err = Failing()
    bench.request.unlink()
    assert bench.main() == EXIT_STATUS["unreadable_input"]


def test_the_default_streams_and_arguments_are_the_process_s(bench, monkeypatch):
    out, err = io.BytesIO(), io.BytesIO()
    monkeypatch.setattr(
        given_eval, "_standard", lambda name: out if name == "stdout" else err
    )
    monkeypatch.setattr(given_eval.sys, "argv", ["given_eval", str(bench.request)])
    assert main(source=lambda: bench.root) == EXIT_STATUS["bad_usage"]
    assert json.loads(err.getvalue())["outcome"] == "bad_usage"


# The table.


def test_the_statuses_are_distinct_and_only_measured_is_zero():
    statuses = list(EXIT_STATUS.values())
    assert len(set(statuses)) == len(statuses)
    assert [o for o, s in EXIT_STATUS.items() if s == 0] == ["measured"]
    assert not {1, 2} & set(statuses)


def test_the_command_is_no_tool():
    registry = tools.default_registry(lambda: None)
    assert not [name for name in registry.names() if "eval" in name]


def test_the_first_state_is_that_of_the_round_manager():
    assert given_eval.FIRST_STATE == stubs.FIRST_STATE
    run_state.validate(given_eval.FIRST_STATE)


# coder_loop (ADR-0207 decision 3): given code reads instance_start only


def test_cuda_gpu_is_refused_while_its_instance_start_is_false(bench):
    bench.write(request({**PROFILE, "accelerator": targets.CUDA_GPU}))
    told = assert_refused(bench, "target_refused")
    assert targets.CUDA_GPU not in told["reason"]


@pytest.mark.skipif(GIT is None, reason="run.commit needs git")
def test_a_target_closed_to_the_coder_loop_is_evaluated(bench, monkeypatch):
    standin = targets.TABLE[targets.CPU_STANDIN]
    table = {
        targets.CPU_STANDIN: standin,
        "test_gpu": dataclasses.replace(standin, coder_loop=False),
    }
    real = targets.instance_start_accelerators
    monkeypatch.setattr(targets, "instance_start_accelerators", lambda: real(table))
    monkeypatch.setattr(
        start_instance,
        "_ACCELERATORS",
        (mock_backend.NAME, *targets.coder_loop_accelerators(table)),
    )
    monkeypatch.setattr(
        start_instance, "_GIVEN_ACCELERATORS", (mock_backend.NAME, *real(table))
    )
    faked(monkeypatch, default_answers())
    bench.write(request({**PROFILE, "accelerator": "test_gpu"}))
    assert bench.main() == 0
    (run_id,) = bench.runs()
    assert bench.summary()["outcome"] == "measured"
    assert (
        instance.read_given(bench.root, run_id).instance.hw_profile["accelerator"]
        == "test_gpu"
    )
