import io
import json
import shutil
import subprocess

import pytest
import test_cuda_check as checks

from hilclaw import cuda_profile, events, given_eval, instance, keys, layout
from hilclaw.harness import timing

GIT = shutil.which("git")
IDENTITY = {
    "GIT_AUTHOR_NAME": "Test Author",
    "GIT_AUTHOR_EMAIL": "author@example.invalid",
    "GIT_COMMITTER_NAME": "Test Committer",
    "GIT_COMMITTER_EMAIL": "committer@example.invalid",
}
OP = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": {"m": 5, "k": 33, "n": 7},
    "dtype": "fp32",
    "layout": "row_major",
}
N_MAX = 20
STEPS = [
    "correctness_check_sim_v2",
    "correctness_check_sim_v2",
    "correctness_check_board_v2",
    "correctness_check_board_v2",
    "board_run_timing_v3",
    "board_run_timing_v3",
]
gpu = checks.gpu


def git(root, *args):
    return subprocess.run(
        [GIT, "-C", str(root), *args], capture_output=True, check=True
    ).stdout.decode()


def request(profile):
    return {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(profile).name, "record": profile},
        "op_signature": {"key": keys.op_signature_key(OP).name, "record": OP},
        "objective": {
            "objectives": [{"type": "latency_minimisation"}],
            "constraints": [],
        },
        "candidates_per_round": 1,
        "n_max": N_MAX,
        "draws": 2,
        "tolerance": dict(checks.TOLERANCE),
    }


class Demonstration:
    def __init__(self, tmp_path, monkeypatch):
        if GIT is None:
            pytest.skip("run.commit needs git")
        for name, value in IDENTITY.items():
            monkeypatch.setenv(name, value)
        self.tmp = tmp_path
        self.root = tmp_path / "data"
        self.root.mkdir()
        git(self.root, "init", "-q", "-b", "main")
        profile = cuda_profile.local_record(
            "external", timeout_s=checks.LIMIT, image=checks.real_image()
        )
        self.request = tmp_path / "request.json"
        self.request.write_text(json.dumps(request(profile)), encoding="utf-8")
        self.judged = []
        real = timing.judge_report

        def judge_report(report, **kwargs):
            judgement = real(report, **kwargs)
            self.judged.append(judgement)
            return judgement

        monkeypatch.setattr(timing, "judge_report", judge_report)
        self.out = io.BytesIO()
        self.err = io.BytesIO()

    def main(self, code):
        return given_eval.main(
            [str(self.request), str(code)],
            source=lambda: self.root,
            stdout=self.out,
            stderr=self.err,
        )

    def summary(self):
        return json.loads(self.out.getvalue())

    def ended(self, run_id, step):
        return [
            line["data"]
            for line in events.read(self.root, run_id).events
            if line["kind"] == "step_ended" and line["data"]["step"] == step
        ]

    def committed(self, run_id):
        assert git(self.root, "status", "--porcelain", "--", "runs") == ""
        held = git(self.root, "ls-files", "runs")
        for name in ("instance.json", "STATE.json", "events.ndjson"):
            assert f"runs/{run_id}/{name}" in held


@pytest.fixture
def demonstration(gpu, tmp_path, monkeypatch):
    return Demonstration(tmp_path, monkeypatch)


def test_a_given_cuda_gemm_is_checked_measured_and_committed_on_the_gpu(
    demonstration,
):
    kernel = checks.FIXTURES / "gemm.cu"
    assert demonstration.main(kernel) == 0, demonstration.err.getvalue()
    assert demonstration.err.getvalue() == b""
    summary = demonstration.summary()
    run_id = summary["run_id"]
    root = demonstration.root
    stored = json.loads(layout.run_file(root, run_id, "instance.json").read_bytes())
    assert stored["schema_version"] == 3
    assert "given_code" in stored and "candidate_kind" not in stored
    assert stored["hw_profile"]["record"]["accelerator"] == "cuda_gpu"
    output = layout.attempt_artefact(root, run_id, 0, 1, 1, "output")
    assert sorted(p.name for p in output.iterdir()) == ["given.cu"]
    assert (output / "given.cu").read_bytes() == kernel.read_bytes()
    assert summary["outcome"] == "measured"
    assert summary["sim"] == {"outcome": "pass", "standing": "verified"}
    assert summary["board"] == {"outcome": "pass", "standing": "verified"}
    assert summary["timing"]["outcome"] in ("converged", "not_converged")
    assert summary["timing"]["unit"] == "ns"
    assert summary["timing"]["median"] > 0
    steps = [line["data"]["step"] for line in events.read(root, run_id).events]
    assert steps == STEPS
    (judged,) = demonstration.judged
    assert judged.broken is None
    (timed,) = demonstration.ended(run_id, "board_run_timing_v3")
    result = timed["result"]
    assert result["outcome"] == summary["timing"]["outcome"]
    assert type(result["memory_bytes"]) is int and result["memory_bytes"] > 0
    state = json.loads(layout.run_file(root, run_id, "STATE.json").read_bytes())
    assert (state["round"], state["run_status"]) == (1, "over")
    assert instance.read_given(root, run_id).given_code == stored["given_code"]
    demonstration.committed(run_id)


def test_a_wrong_given_cuda_gemm_is_not_verified_and_not_timed(demonstration):
    wrong = demonstration.tmp / "gemm_wrong.cu"
    text = (checks.FIXTURES / "gemm.cu").read_text(encoding="utf-8")
    wrong.write_text("#define GEMM_WRONG 1\n" + text, encoding="utf-8")
    assert demonstration.main(wrong) == given_eval.EXIT_STATUS["not_measured"]
    assert demonstration.err.getvalue() == b""
    summary = demonstration.summary()
    run_id = summary["run_id"]
    assert summary["sim"] == {"outcome": "fail", "standing": "not_verified"}
    assert "board" not in summary and "timing" not in summary
    steps = {
        line["data"]["step"] for line in events.read(demonstration.root, run_id).events
    }
    assert steps == {"correctness_check_sim_v2"}
    assert demonstration.judged == []
    state = json.loads(
        layout.run_file(demonstration.root, run_id, "STATE.json").read_bytes()
    )
    assert state["run_status"] == "over"
    demonstration.committed(run_id)
