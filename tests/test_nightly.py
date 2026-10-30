import datetime
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from hilclaw import keys, nightly, standin_profile

REPOSITORY = Path(__file__).resolve().parent.parent
GIT = shutil.which("git")
NOW = datetime.datetime(2026, 10, 30, 18, 0, 5, tzinfo=datetime.UTC)
FIRING = "20261030T180005Z"
PROFILE = {
    "schema_version": 1,
    "accelerator": "cpu_standin",
    "revision": "host",
    "toolchain": {"clang": "stub clang version 1"},
    "host": {"cpu": "stub cpu", "os": "linux stub"},
    "hw_source": "external",
}
TOKEN = "fake-token-not-a-real-one"
FAKE_ENTRY = r"""
import json, os, sys
scenario = json.load(open(os.environ["NIGHTLY_FAKE"], encoding="utf-8"))
module, argument = sys.argv[2], sys.argv[3]
with open(scenario["log"], "a", encoding="utf-8") as log:
    log.write(json.dumps({
        "argv": sys.argv[1:],
        "cwd": os.getcwd(),
        "env": {name: os.environ.get(name) for name in scenario["watch"]},
    }) + "\n")
answer = scenario[module]
sys.stderr.write(answer.get("stderr", ""))
sys.stdout.write(answer["stdout"])
sys.exit(answer["status"])
"""
WATCH = (
    "HILCLAW_DATA_REPO_LOCAL_PATH",
    "HILCLAW_DATA_REPO_URL",
    "PYTHONPATH",
    "CLAUDECODE",
    "CLAUDE_CODE_ENTRYPOINT",
    "HILCLAW_CODER_OAUTH_TOKEN",
)
STARTED = {"outcome": "started", "run_id": "r-20261030-0001"}
RUN_OVER = {"outcome": "run_over"}

posix = pytest.mark.skipif(
    nightly.fcntl is None, reason="the firing needs fcntl (POSIX host)"
)


def line(value):
    return json.dumps(value) + "\n"


class World:
    def __init__(self, tmp_path):
        self.tmp = tmp_path
        self.base = tmp_path / "base"
        self.bin = tmp_path / "bin"
        self.base.mkdir()
        self.bin.mkdir()
        self.ran = tmp_path / "stub-ran"
        for name in ("claude", "docker"):
            self.stub(name, f'#!/bin/sh\necho "$0" >> "{self.ran}"\nexit 99\n')
        self.log = tmp_path / "entries.ndjson"
        self.scenario = tmp_path / "scenario.json"
        self.fake = tmp_path / "fake_entry.py"
        self.fake.write_text(FAKE_ENTRY, encoding="utf-8")
        self.env = {
            "PATH": os.pathsep.join([str(self.bin), os.path.dirname(GIT)]),
            "HOME": os.environ.get("HOME", str(tmp_path)),
            "HILCLAW_CODER_IMAGE": "stub.invalid/coder:fake",
            "HILCLAW_CODER_OAUTH_TOKEN": TOKEN,
            "HILCLAW_STANDIN_IMAGE": "stub.invalid/standin:fake",
            "CLAUDECODE": "1",
            "CLAUDE_CODE_ENTRYPOINT": "sdk-ts",
            "NIGHTLY_FAKE": str(self.scenario),
            "PYTHONPATH": "/somewhere/else",
        }
        self.answers(new_run=(line(STARTED), 0), turn_start=(line(RUN_OVER), 0))

    def stub(self, name, text):
        path = self.bin / name
        path.write_text(text, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def answers(self, new_run, turn_start, new_run_stderr="", turn_start_stderr=""):
        self.scenario.write_text(
            json.dumps(
                {
                    "log": str(self.log),
                    "watch": list(WATCH),
                    "hilclaw.new_run": {
                        "stdout": new_run[0],
                        "status": new_run[1],
                        "stderr": new_run_stderr,
                    },
                    "hilclaw.turn_start": {
                        "stdout": turn_start[0],
                        "status": turn_start[1],
                        "stderr": turn_start_stderr,
                    },
                }
            ),
            encoding="utf-8",
        )

    def fire(self, profile=None):
        return nightly.fire(
            self.base,
            environ=self.env,
            python=(sys.executable, str(self.fake)),
            profile=profile or (lambda hw_source, *, timeout_s, image: dict(PROFILE)),
            now=lambda: NOW,
        )

    @property
    def firing(self):
        return self.base / FIRING

    def entries(self):
        if not self.log.exists():
            return []
        return [
            json.loads(text)
            for text in self.log.read_text(encoding="utf-8").splitlines()
        ]

    def result(self):
        return json.loads((self.firing / "result.json").read_text(encoding="utf-8"))

    def issue(self):
        title = (self.firing / "issue-title.txt").read_text(encoding="utf-8")
        return title, (self.firing / "issue.md").read_text(encoding="utf-8")


@pytest.fixture
def world(tmp_path):
    if GIT is None:
        pytest.skip("the firing needs git")
    return World(tmp_path)


def test_document_is_the_nightly_configuration():
    given = nightly.document(dict(PROFILE))
    assert given == {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(PROFILE).name, "record": PROFILE},
        "op_signature": {
            "key": keys.op_signature_key(nightly.OP).name,
            "record": {
                "schema_version": 1,
                "kind": "gemm",
                "shape": {"m": 1, "k": 2048, "n": 8192},
                "dtype": "fp32",
                "layout": "row_major",
            },
        },
        "objective": {
            "objectives": [{"type": "latency_minimisation"}],
            "constraints": [],
        },
        "candidates_per_round": 1,
        "n_max": 10,
        "draws": 1,
        "tolerance": {"rtol": 1e-4, "atol": 5e-7 * 2048},
        "round_budget": 5,
    }


def test_document_refuses_an_invalid_profile():
    with pytest.raises(keys.InvalidRecordError):
        nightly.document({"accelerator": "cpu_standin"})


@pytest.mark.parametrize(
    ("stage", "told", "cause", "signature"),
    [
        (
            "new_run",
            {"outcome": "no_data_root", "reason": "x"},
            "environment",
            "new_run/no_data_root",
        ),
        (
            "new_run",
            {"outcome": "file_system", "reason": "x"},
            "environment",
            "new_run/file_system",
        ),
        ("new_run", {"outcome": "invalid", "reason": "x"}, "code", "new_run/invalid"),
        ("new_run", {"outcome": "fault", "fault": "KeyError"}, "code", "new_run/fault"),
        (
            "turn_start",
            {"outcome": "failed_turn", "exit_status": 1},
            "undetermined",
            "turn_start/failed_turn/exit_status=1",
        ),
        (
            "turn_start",
            {"outcome": "open_state", "reason": "state_invalid", "exit_status": 3},
            "code",
            "turn_start/open_state/state_invalid",
        ),
        (
            "turn_start",
            {"outcome": "error", "error": "no_claude"},
            "environment",
            "turn_start/error/no_claude",
        ),
        (
            "turn_start",
            {"outcome": "error", "error": "no_data_root"},
            "environment",
            "turn_start/error/no_data_root",
        ),
        (
            "turn_start",
            {"outcome": "error", "error": "fault"},
            "code",
            "turn_start/error/fault",
        ),
        (
            "turn_start",
            {"outcome": "stopped_at_check", "check": {"outcome": "not_logged_in"}},
            "environment",
            "turn_start/stopped_at_check/not_logged_in",
        ),
        (
            "turn_start",
            {"outcome": "stopped_at_check", "check": {"outcome": "no_claude"}},
            "environment",
            "turn_start/stopped_at_check/no_claude",
        ),
        (
            "turn_start",
            {"outcome": "stopped_at_check", "check": {"outcome": "login_unreadable"}},
            "environment",
            "turn_start/stopped_at_check/login_unreadable",
        ),
        (
            "turn_start",
            {"outcome": "stopped_at_check", "check": {"outcome": "session_failed"}},
            "undetermined",
            "turn_start/stopped_at_check/session_failed",
        ),
        (
            "turn_start",
            {"outcome": "stopped_at_check", "check": {"outcome": "front_refused"}},
            "code",
            "turn_start/stopped_at_check/front_refused",
        ),
        (
            "turn_start",
            {"outcome": "stopped_at_check", "check_fault": "RuntimeError"},
            "code",
            "turn_start/stopped_at_check/check_fault=RuntimeError",
        ),
        (
            "turn_start",
            {"outcome": "unchanged_turn"},
            "code",
            "turn_start/unchanged_turn",
        ),
        (
            "turn_start",
            {"outcome": "unknown_run_status", "run_status": "odd"},
            "code",
            "turn_start/unknown_run_status",
        ),
        ("turn_start", None, "code", "turn_start/unreadable_outcome"),
        ("turn_start", ["run_over"], "code", "turn_start/unreadable_outcome"),
        ("new_run", {"outcome": 3}, "code", "new_run/unreadable_outcome"),
    ],
)
def test_classify(stage, told, cause, signature):
    assert nightly.classify(stage, told) == (cause, signature)


def test_classify_keeps_the_signature_safe_and_short():
    cause, signature = nightly.classify(
        "turn_start", {"outcome": "open_state", "reason": "a b`c\n" + "x" * 200}
    )
    assert cause == "code"
    stage, outcome, datum = signature.split("/")
    assert (stage, outcome) == ("turn_start", "open_state")
    assert datum.startswith("a_b_c_") and len(datum) == 80


@posix
def test_a_run_over_passes(world):
    record = world.fire()
    assert record == world.result()
    assert record["verdict"] == "pass"
    assert (record["cause"], record["signature"], record["detail"]) == (
        None,
        None,
        None,
    )
    assert record["firing"] == FIRING
    assert record["run_id"] == STARTED["run_id"]
    assert [step["stage"] for step in record["steps"]] == ["new_run", "turn_start"]
    assert record["steps"][1] == {
        "stage": "turn_start",
        "exit_status": 0,
        "line": RUN_OVER,
    }
    assert not (world.firing / "issue.md").exists()
    assert not (world.firing / "issue-title.txt").exists()
    given = json.loads((world.firing / "instance.json").read_text(encoding="utf-8"))
    assert given == nightly.document(PROFILE)
    assert (world.base / "data" / ".git").is_dir()
    assert not (world.firing / "data").exists()
    first, second = world.entries()
    instance_path = str(world.firing / "instance.json")
    assert first["argv"] == ["-m", "hilclaw.new_run", instance_path]
    assert second["argv"] == ["-m", "hilclaw.turn_start", STARTED["run_id"]]
    for entry in (first, second):
        assert Path(entry["cwd"]).resolve() == world.firing.resolve()
        env = entry["env"]
        assert env["HILCLAW_DATA_REPO_LOCAL_PATH"] == str(world.base / "data")
        assert env["HILCLAW_DATA_REPO_URL"] == nightly.DATA_REPO_URL
        assert env["PYTHONPATH"] == os.pathsep.join(
            [str(REPOSITORY), "/somewhere/else"]
        )
        assert env["CLAUDECODE"] is None and env["CLAUDE_CODE_ENTRYPOINT"] is None
        assert env["HILCLAW_CODER_OAUTH_TOKEN"] == TOKEN
    assert not world.ran.exists()


@posix
def test_the_children_get_this_checkout_alone_on_pythonpath_when_none_is_given(world):
    del world.env["PYTHONPATH"]
    world.fire()
    assert {entry["env"]["PYTHONPATH"] for entry in world.entries()} == {
        str(REPOSITORY)
    }


@posix
def test_a_failed_turn_fails_with_an_issue_body(world):
    noise = "".join(f"line {n} {TOKEN} {Path.home()}\n" for n in range(60)) + "```end"
    world.answers(
        new_run=(line(STARTED), 0),
        turn_start=(line({"outcome": "failed_turn", "exit_status": 1}), 11),
        turn_start_stderr=noise,
    )
    record = world.fire()
    assert record["verdict"] == "fail"
    assert record["cause"] == "undetermined"
    assert record["signature"] == "turn_start/failed_turn/exit_status=1"
    assert record["steps"][1]["exit_status"] == 11
    title, body = world.issue()
    assert title == "nightly: turn_start/failed_turn/exit_status=1\n"
    head = body.splitlines()[:3]
    assert head == [
        f"nightly-report: {FIRING}",
        "signature: turn_start/failed_turn/exit_status=1",
        "cause: undetermined",
    ]
    assert f"- commit: `{record['commit']}`" in body
    assert f"- run id: `{STARTED['run_id']}`" in body
    assert TOKEN not in body and str(Path.home()) not in body
    assert "line 59 [redacted] ~" in body
    assert "line 20 " not in body and "line 21 " in body
    assert "'''end" in body
    assert body.count("```") == 2
    assert (world.firing / "turn_start.stderr").read_text(encoding="utf-8") == noise
    assert not world.ran.exists()


@posix
def test_a_turn_start_error_of_the_environment(world):
    world.answers(
        new_run=(line(STARTED), 0),
        turn_start=(line({"outcome": "error", "error": "no_claude"}), 20),
    )
    record = world.fire()
    assert (record["verdict"], record["cause"]) == ("fail", "environment")
    assert record["signature"] == "turn_start/error/no_claude"


@posix
def test_a_new_run_that_does_not_start_fails_before_any_turn(world):
    world.answers(
        new_run=(line({"outcome": "invalid", "reason": "bad"}), 12),
        turn_start=(line(RUN_OVER), 0),
        new_run_stderr="new_run said this\n",
    )
    record = world.fire()
    assert (record["verdict"], record["cause"], record["signature"]) == (
        "fail",
        "code",
        "new_run/invalid",
    )
    assert record["run_id"] is None
    assert [entry["argv"][1] for entry in world.entries()] == ["hilclaw.new_run"]
    _, body = world.issue()
    assert "new_run said this" in body
    assert "- new_run: exit status 12" in body


@posix
def test_a_new_run_without_a_data_root_is_the_environment(world):
    world.answers(
        new_run=(line({"outcome": "no_data_root", "reason": "x"}), 23),
        turn_start=(line(RUN_OVER), 0),
    )
    record = world.fire()
    assert (record["cause"], record["signature"]) == (
        "environment",
        "new_run/no_data_root",
    )


@posix
def test_an_unreadable_outcome_line_is_a_code_failure(world):
    world.answers(new_run=(line(STARTED), 0), turn_start=("not json at all\n", 0))
    record = world.fire()
    assert (record["cause"], record["signature"]) == (
        "code",
        "turn_start/unreadable_outcome",
    )
    assert record["steps"][1]["line"] == "not json at all\n"


@posix
def test_missing_variables_and_programs_start_nothing(world):
    del world.env["HILCLAW_CODER_IMAGE"]
    world.env["HILCLAW_STANDIN_IMAGE"] = ""
    (world.bin / "claude").unlink()
    record = world.fire()
    assert (record["verdict"], record["cause"]) == ("fail", "environment")
    assert (
        record["signature"]
        == "prepare/missing:HILCLAW_CODER_IMAGE,HILCLAW_STANDIN_IMAGE,claude"
    )
    assert record["steps"] == []
    assert world.entries() == []
    assert not (world.firing / "instance.json").exists()
    title, body = world.issue()
    assert (
        title
        == "nightly: prepare/missing:HILCLAW_CODER_IMAGE,HILCLAW_STANDIN_IMAGE,claude\n"
    )
    assert "Last lines of standard error" not in body


@posix
def test_the_profile_is_given_the_standin_image(world):
    asked = []

    def reader(hw_source, *, timeout_s, image):
        asked.append(image)
        return dict(PROFILE)

    record = world.fire(profile=reader)
    assert record["verdict"] == "pass"
    assert asked == [world.env["HILCLAW_STANDIN_IMAGE"]]


@posix
def test_a_firing_needs_no_host_clang(world, tmp_path):
    only_git = tmp_path / "only-git"
    only_git.mkdir()
    (only_git / "git").symlink_to(GIT)
    world.env["PATH"] = os.pathsep.join([str(world.bin), str(only_git)])
    assert shutil.which("clang", path=world.env["PATH"]) is None
    record = world.fire()
    assert record["verdict"] == "pass"


@posix
def test_the_coder_output_directory_is_named_to_the_entries(world):
    record = world.fire()
    assert record["verdict"] == "pass"
    directory = world.firing / "coder-output"
    assert directory.is_dir()
    assert directory.stat().st_mode & 0o777 == 0o700
    for entry in world.entries():
        assert entry["env"]["HILCLAW_CODER_LOG_DIR"] == str(directory)


@posix
def test_an_image_the_profile_refuses_is_the_environment(world):
    def refused(hw_source, *, timeout_s, image):
        raise ValueError("image must not begin with '-'")

    record = world.fire(profile=refused)
    assert (record["cause"], record["signature"], record["detail"]) == (
        "environment",
        "prepare/hw_profile",
        "ValueError",
    )
    assert world.entries() == []


@posix
def test_an_unreadable_machine_fact_is_the_environment(world):
    def unreadable(hw_source, *, timeout_s, image):
        assert (hw_source, timeout_s) == ("external", nightly.PROFILE_TIMEOUT_S)
        assert image == "stub.invalid/standin:fake"
        raise standin_profile.UnreadableFactError("host.cpu: no model name line")

    record = world.fire(profile=unreadable)
    assert (record["cause"], record["signature"]) == (
        "environment",
        "prepare/hw_profile",
    )
    assert record["detail"] == "UnreadableFactError"
    assert "- detail: UnreadableFactError" in world.issue()[1]
    assert world.entries() == []


@posix
def test_a_failing_git_init_is_the_environment(world):
    world.env["PATH"] = str(world.bin)
    world.stub("git", "#!/bin/sh\nexit 7\n")
    record = world.fire()
    assert (record["cause"], record["signature"]) == (
        "environment",
        "prepare/data_root",
    )
    assert record["detail"] == "git init exited 7"
    assert world.entries() == []


@posix
def test_a_held_lock_is_an_overlap(world):
    with open(world.base / "nightly.lock", "a", encoding="utf-8") as handle:
        nightly.fcntl.flock(handle, nightly.fcntl.LOCK_EX | nightly.fcntl.LOCK_NB)
        script = (
            "import sys, json, datetime; sys.path.insert(0, sys.argv[1]); "
            "from hilclaw import nightly; "
            "r = nightly.fire(sys.argv[2], environ={}, now=lambda: datetime.datetime(2026, 1, 1, "
            "tzinfo=datetime.UTC)); print(json.dumps(r))"
        )
        done = subprocess.run(
            [sys.executable, "-c", script, str(REPOSITORY), str(world.base)],
            capture_output=True,
            check=True,
        )
    record = json.loads(done.stdout)
    assert (record["cause"], record["signature"]) == ("environment", "prepare/overlap")
    assert world.entries() == []


def test_a_host_without_fcntl_starts_nothing(world, monkeypatch):
    monkeypatch.setattr(nightly, "fcntl", None)
    record = world.fire()
    assert (record["verdict"], record["cause"]) == ("fail", "environment")
    assert record["signature"] == "prepare/no_posix_host"
    assert world.entries() == []
    assert (world.firing / "issue.md").exists()


@posix
def test_the_lock_is_released_after_a_firing(world):
    world.fire()
    with open(world.base / "nightly.lock", "a", encoding="utf-8") as handle:
        nightly.fcntl.flock(handle, nightly.fcntl.LOCK_EX | nightly.fcntl.LOCK_NB)


def test_an_existing_firing_directory_is_refused(world):
    world.firing.mkdir()
    with pytest.raises(FileExistsError):
        world.fire()


def test_issue_body_redacts_secret_values_only():
    record = {
        "firing": FIRING,
        "signature": "prepare/overlap",
        "cause": "environment",
        "commit": "abc",
        "run_id": None,
        "detail": "uses sk-1234567890 and short1 and plain-value-1234",
        "steps": [],
    }
    environ = {
        "API_KEY": "sk-1234567890",
        "MY_SECRET": "short1",
        "PLAIN": "plain-value-1234",
    }
    body = nightly.issue_body(record, None, environ)
    assert "uses [redacted] and short1 and plain-value-1234" in body
    assert body.endswith("a regression signal only (D17).\n")


def test_issue_body_reads_no_missing_tail(tmp_path):
    record = {
        "firing": FIRING,
        "signature": "s",
        "cause": "code",
        "commit": "abc",
        "run_id": "r",
        "detail": None,
        "steps": [
            {
                "stage": "turn_start",
                "exit_status": 12,
                "line": {"outcome": "unchanged_turn"},
            }
        ],
    }
    body = nightly.issue_body(record, tmp_path / "absent.stderr", {})
    assert '- turn_start: exit status 12, line `{"outcome": "unchanged_turn"}`' in body
    assert "```" not in body


def test_commit_is_unknown_without_git(monkeypatch):
    monkeypatch.setattr(nightly.shutil, "which", lambda name, path=None: None)
    assert nightly._commit() == "unknown"


def test_commit_is_unknown_outside_a_checkout(monkeypatch, tmp_path):
    if GIT is None:
        pytest.skip("needs git")
    monkeypatch.setattr(nightly, "REPOSITORY", tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    assert nightly._commit() == "unknown"


def test_commit_names_this_checkout():
    if GIT is None or not (REPOSITORY / ".git").exists():
        pytest.skip("needs a git checkout")
    commit = nightly._commit()
    assert len(commit) >= 40 and set(commit) <= set("0123456789abcdef")


@pytest.mark.parametrize("argv", [[], ["a", "b"], ["/no/such/directory/at/all"]])
def test_main_refuses_bad_usage(argv, capsys, monkeypatch):
    monkeypatch.setattr(nightly, "fire", lambda base: pytest.fail("fired"))
    assert nightly.main(argv) == nightly.EXIT_USAGE
    assert json.loads(capsys.readouterr().out) == {
        "verdict": "bad_usage",
        "reason": "give one existing directory",
    }


@pytest.mark.parametrize(("verdict", "status"), [("pass", 0), ("fail", 10)])
def test_main_tells_the_verdict(verdict, status, capsys, monkeypatch, tmp_path):
    record = {"verdict": verdict, "signature": "s", "cause": "c", "firing": FIRING}
    monkeypatch.setattr(nightly, "fire", lambda base: record)
    assert nightly.main([str(tmp_path)]) == status
    out = capsys.readouterr().out
    assert out.count("\n") == 1
    assert json.loads(out) == {
        "verdict": verdict,
        "signature": "s",
        "cause": "c",
        "firing": str(tmp_path / FIRING),
    }


def test_the_module_runs_as_a_command():
    done = subprocess.run(
        [sys.executable, "-m", "hilclaw.nightly"],
        cwd=REPOSITORY,
        capture_output=True,
        check=False,
    )
    assert done.returncode == nightly.EXIT_USAGE
    assert json.loads(done.stdout)["verdict"] == "bad_usage"


def test_the_document_starts_a_run_through_the_real_new_run(tmp_path):
    if GIT is None:
        pytest.skip("needs git")
    root = tmp_path / "data"
    subprocess.run([GIT, "init", "-q", "-b", "main", str(root)], check=True)
    given = tmp_path / "instance.json"
    given.write_text(json.dumps(nightly.document(dict(PROFILE))), encoding="utf-8")
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("CLAUDE")
    }
    env.update(
        HILCLAW_DATA_REPO_LOCAL_PATH=str(root),
        HILCLAW_DATA_REPO_URL=nightly.DATA_REPO_URL,
        PYTHONPATH=str(REPOSITORY),
    )
    done = subprocess.run(
        [sys.executable, "-m", "hilclaw.new_run", str(given)],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
    )
    told = json.loads(done.stdout)
    assert (done.returncode, told["outcome"]) == (0, "started"), done
    stored = json.loads(
        (root / "runs" / told["run_id"] / "instance.json").read_text(encoding="utf-8")
    )
    assert stored["round_budget"] == 5
    assert stored["op_signature"]["record"] == nightly.OP


def test_the_data_root_is_kept_until_the_last_day_of_case_storage(tmp_path):
    firing = tmp_path / "f"
    last = datetime.datetime(2026, 11, 30, 14, 59, 59, tzinfo=datetime.UTC)
    after = datetime.datetime(2026, 11, 30, 15, 0, tzinfo=datetime.UTC)
    assert nightly.data_root(tmp_path, firing, NOW) == tmp_path / "data"
    assert nightly.data_root(tmp_path, firing, last) == tmp_path / "data"
    assert nightly.data_root(tmp_path, firing, after) == firing / "data"


def test_the_data_root_follows_the_kst_date():
    kst = datetime.timezone(datetime.timedelta(hours=9))
    first = datetime.datetime(2026, 12, 1, 3, 0, tzinfo=kst)
    last = datetime.datetime(2026, 11, 30, 3, 0, tzinfo=kst)
    assert nightly.data_root(Path("b"), Path("f"), first) == Path("f/data")
    assert nightly.data_root(Path("b"), Path("f"), last) == Path("b/data")


@posix
def test_a_second_firing_reuses_the_kept_data_root(world):
    world.fire()
    marker = world.base / "data" / "case-of-the-first-firing"
    marker.write_text("kept", encoding="utf-8")
    world.stub("git", "#!/bin/sh\nexit 7\n")
    world.env["PATH"] = str(world.bin)
    record = nightly.fire(
        world.base,
        environ=world.env,
        python=(sys.executable, str(world.fake)),
        profile=lambda hw_source, *, timeout_s, image: dict(PROFILE),
        now=lambda: NOW + datetime.timedelta(days=1),
    )
    assert record["verdict"] == "pass"
    assert marker.read_text(encoding="utf-8") == "kept"
    third = world.entries()[2]
    assert third["env"]["HILCLAW_DATA_REPO_LOCAL_PATH"] == str(world.base / "data")


@posix
def test_a_firing_after_case_storage_makes_its_own_data_root(world):
    later = datetime.datetime(2026, 12, 1, 3, 0, tzinfo=datetime.UTC)
    record = nightly.fire(
        world.base,
        environ=world.env,
        python=(sys.executable, str(world.fake)),
        profile=lambda hw_source, *, timeout_s, image: dict(PROFILE),
        now=lambda: later,
    )
    assert record["verdict"] == "pass"
    firing = world.base / record["firing"]
    assert (firing / "data" / ".git").is_dir()
    assert not (world.base / "data").exists()
    (entry, _) = world.entries()
    assert entry["env"]["HILCLAW_DATA_REPO_LOCAL_PATH"] == str(firing / "data")


@posix
def test_a_kept_data_root_without_a_repository_is_made_one(world):
    (world.base / "data").mkdir()
    record = world.fire()
    assert record["verdict"] == "pass"
    assert (world.base / "data" / ".git").is_dir()
