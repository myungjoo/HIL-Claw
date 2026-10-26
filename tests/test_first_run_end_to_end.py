import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import first_run_stubs as stubs
import pytest

from hilclaw import (
    check_standing,
    checks_tool,
    events,
    key_records,
    keys,
    run_commit,
    run_file_tools,
    run_state,
    spec,
    spec_file,
    standin_profile,
    timings_tool,
)
from hilclaw.journal import EMPTY
from hilclaw.run_state_file import replace

REPOSITORY = Path(__file__).resolve().parent.parent
GIT = shutil.which("git")
CLANG = shutil.which("clang")
SHAPE = {"m": 8, "k": 16, "n": 8}
OP = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": SHAPE,
    "dtype": "fp32",
    "layout": "row_major",
}
PROFILE = {
    "schema_version": 1,
    "accelerator": standin_profile.ACCELERATOR,
    "revision": "stub-revision",
    "toolchain": {"clang": "stub"},
    "host": {"cpu": "stub", "os": "stub"},
    "hw_source": "external",
}
KERNEL = """#include <stddef.h>

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
FAKE = {
    "HILCLAW_CODER_IMAGE": "stub.invalid/coder:fake",
    "HILCLAW_CODER_OAUTH_TOKEN": "fake-token-not-a-real-one",
    "HILCLAW_STANDIN_IMAGE": "stub.invalid/standin:fake",
}
IDENTITY = {
    "GIT_AUTHOR_NAME": "Test Author",
    "GIT_AUTHOR_EMAIL": "author@example.invalid",
    "GIT_COMMITTER_NAME": "Test Committer",
    "GIT_COMMITTER_EMAIL": "committer@example.invalid",
}
LOCATING = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_COMMON_DIR",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CONFIG",
    "GIT_CONFIG_PARAMETERS",
    "GIT_CONFIG_COUNT",
    "EMAIL",
)
CHECK = {
    "auth_output": json.dumps({"loggedIn": True, "authMethod": "claude.ai"}),
    "auth_exit": 0,
    "upto": "call",
    "status": "connected",
    "exit": 0,
}

if not hasattr(os, "getuid"):
    pytest.skip(
        "the coder runtime and the stand-in containers need os.getuid (no native Windows)",
        allow_module_level=True,
    )
if GIT is None:
    pytest.skip("these tests need git on PATH", allow_module_level=True)
if CLANG is None:
    pytest.skip(
        "these tests need a host clang for the stand-in builds", allow_module_level=True
    )


def unshare_path():
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


UNSHARE = unshare_path()


def document(budget=1):
    return {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(PROFILE).name, "record": PROFILE},
        "op_signature": {"key": keys.op_signature_key(OP).name, "record": OP},
        "objective": {
            "objectives": [{"type": "latency_minimisation"}],
            "constraints": [],
        },
        "candidates_per_round": 1,
        "n_max": 6,
        "draws": 1,
        "tolerance": {"rtol": 1e-4, "atol": 1e-5},
        "round_budget": budget,
    }


class World:
    def __init__(self, tmp_path):
        self.tmp = tmp_path
        self.root = tmp_path / "data"
        self.bin = tmp_path / "bin"
        self.sessions = tmp_path / "sessions"
        self.work = tmp_path / "work"
        for directory in (self.root, self.bin, self.sessions, self.work):
            directory.mkdir()
        global_config = tmp_path / "git-global"
        global_config.write_text("", encoding="utf-8")
        self.env = {
            name: value
            for name, value in os.environ.items()
            if name not in LOCATING and not name.startswith("CLAUDE")
        }
        self.env.update(IDENTITY)
        self.env.update(FAKE)
        self.env.update(
            {
                "PATH": str(self.bin),
                "TMPDIR": str(self.sessions),
                "PYTHONPATH": str(REPOSITORY),
                "GIT_CONFIG_GLOBAL": str(global_config),
                "GIT_CONFIG_NOSYSTEM": "1",
                "HILCLAW_DATA_REPO_URL": "stub.invalid/data",
                "HILCLAW_DATA_REPO_LOCAL_PATH": str(self.root),
            }
        )
        self.git("init", "-q", "-b", "main")
        self.log = tmp_path / "session.ndjson"
        self.docker_log = tmp_path / "docker.ndjson"

    def git(self, *args):
        return subprocess.run(
            [GIT, "-C", str(self.root), *args],
            env=self.env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=True,
        ).stdout.decode()

    def install(self, kernel=KERNEL, turns=({},)):
        scenario = {
            "repo": str(REPOSITORY),
            "git": GIT,
            "clang": CLANG,
            "unshare": UNSHARE,
            "log": str(self.log),
            "docker_log": str(self.docker_log),
            "check": CHECK,
            "turns": list(turns),
            "kernel": None if kernel is None else {"gemm.c": kernel},
        }
        stubs.install(self.bin, scenario)

    def entry(self, module, argument):
        done = subprocess.run(
            [sys.executable, "-m", module, str(argument)],
            cwd=self.work,
            env=self.env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            timeout=600,
        )
        return done

    def new_run(self, document):
        given = self.tmp / "instance.json"
        given.write_text(json.dumps(document), encoding="utf-8")
        done = self.entry("hilclaw.new_run", given)
        told = json.loads(done.stdout)
        assert done.returncode == 0, done
        assert told["outcome"] == "started"
        return told["run_id"]

    def turn_start(self, run_id):
        return self.entry("hilclaw.turn_start", run_id)

    def session_log(self):
        return stubs.read_log(self.log)

    def docker_runs(self):
        return stubs.read_log(self.docker_log)

    def run_dir(self, run_id):
        return self.root / "runs" / run_id


@pytest.fixture
def world(tmp_path, monkeypatch):
    for directory in Path(tmp_path).resolve().parents:
        for name in ("CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", ".claude"):
            found = directory / name
            if (
                found.exists()
                and found.resolve() != (Path.home() / ".claude").resolve()
            ):
                pytest.skip(
                    "a directory above the test's temporary directory holds a marker"
                )
    made = World(tmp_path)
    real = subprocess.run

    def checked(command, **options):
        program = Path(command[0]).name
        assert program in (Path(sys.executable).name, "git"), command
        return real(command, **options)

    monkeypatch.setattr(subprocess, "run", checked)
    return made


WRONG_KERNEL = KERNEL.replace("c[i * n + j] = sum;", "c[i * n + j] = sum + 1.0f;")
SPENDING = {"coder_run", "correctness_check", "board_run"}
ROUND_ZERO = [
    ("round-manager", "run_commit"),
    ("round-manager", "state_read"),
    ("round-manager", "run_fresh"),
    ("round-manager", "state_write"),
    ("round-manager", "key_store"),
    ("round-manager", "Agent", "coder-driver"),
    ("coder-driver", "spec_write"),
    ("coder-driver", "coder_run"),
    ("round-manager", "Agent", "evaluator"),
    ("evaluator", "correctness_check"),
    ("evaluator", "checks_read"),
    ("round-manager", "Agent", "evaluator"),
    ("evaluator", "correctness_check"),
    ("evaluator", "checks_read"),
    ("round-manager", "Agent", "experiment-runner"),
    ("experiment-runner", "board_run"),
    ("round-manager", "round_end"),
    ("round-manager", "run_commit"),
]
ATTEMPT = "rounds/0000/coder/candidates/01/attempts/01"
MEASURE = "rounds/0000/measure/candidates/01/attempts/01"
COMMIT_SUBJECT = "Commit the owed files of a run (run.commit)"


def told(done, outcome, status, **members):
    assert done.returncode == status, done
    line = json.loads(done.stdout.decode("ascii").splitlines()[-1])
    assert line.pop("check")["outcome"] == "passed"
    assert line == {"outcome": outcome, **members}


def requests(log, turn=None):
    return [
        entry
        for entry in log
        if ("tool" in entry or "delegate" in entry)
        and (turn is None or entry["turn"] == turn)
    ]


def step(entry):
    if "delegate" in entry:
        return (entry["agent"], "Agent", entry["delegate"])
    return (entry["agent"], entry["tool"].removeprefix(stubs.PREFIX))


def steps(log, turn=None):
    return [step(entry) for entry in requests(log, turn)]


def turns(log):
    return [entry["turn"] for entry in log if entry.get("started")]


def assert_hooks_ran_and_passed(entries):
    calls = [entry for entry in entries if "tool" in entry]
    assert calls
    for entry in calls:
        name = entry["tool"].removeprefix(stubs.PREFIX)
        expected = [0, 1] if name in SPENDING else [0]
        assert [hook["entry"] for hook in entry["hooks"]] == expected, entry
        assert all(hook["status"] == 0 for hook in entry["hooks"]), entry
        assert entry["refused"] is False
        assert (entry["agent_id"] is None) == (entry["agent"] == "round-manager")
    for entry in entries:
        if "delegate" in entry:
            assert entry["defined"] is True
            assert entry["hooks"] == []


def assert_each_delegation_its_own_agent(log):
    kinds = {}
    for entry in requests(log):
        if "tool" in entry and entry["agent"] != "round-manager":
            kinds.setdefault(entry["agent_id"], set()).add(entry["agent"])
    assert kinds
    assert all(len(found) == 1 for found in kinds.values())


def assert_stopped_once(log, turn):
    (stop,) = [entry for entry in log if entry.get("stop") and entry["turn"] == turn]
    assert stop["stop_hook_active"] is False
    assert [hook["status"] for hook in stop["hooks"]] == [0]


def assert_committed_clean(world, run_id):
    assert world.git("status", "--porcelain", "--", f"runs/{run_id}", "db") == ""
    assert run_commit.commit_owed(world.root, run_id) is False


def state_of(world, run_id):
    found, _ = run_file_tools.read(world.root, run_id, "STATE.json")
    return found


def test_round_zero_of_a_first_run_ends_the_run_over(world):
    world.install()
    run_id = world.new_run(document())
    run = world.run_dir(run_id)

    done = world.turn_start(run_id)

    told(done, "run_over", 0)
    raw = (run / "STATE.json").read_bytes()
    state = run_state.parse(raw)
    assert (state.round, state.others) == (1, {"run_status": "over"})
    assert state_of(world, run_id).round == 1
    stated, _ = run_file_tools.read(world.root, run_id, "instance.json")
    assert (stated.round_budget, stated.candidates_per_round) == (1, 1)

    attempt = run / ATTEMPT
    content = spec_file.parse((attempt / "spec.json").read_bytes())
    spec.validate(content)
    assert (content["id"]["round"], content["id"]["candidate"]) == (0, 1)
    assert [path.name for path in (attempt / "output").iterdir()] == ["gemm.c"]
    assert (attempt / "output/gemm.c").read_text(encoding="utf-8") == KERNEL

    lines = events.read(world.root, run_id).events
    for line in lines:
        events.validate(line)
    assert [line["kind"] for line in lines] == ["step_started", "step_ended"] * 3
    assert [line["data"]["step"] for line in lines[1::2]] == [
        "correctness_check_sim",
        "correctness_check_board",
        "board_run_timing",
    ]
    assert {(line["round"], line["candidate"], line["attempt"]) for line in lines} == {
        (0, 1, 1)
    }
    checks = checks_tool.checks_of(
        run_id,
        checks_tool.log_lines(world.root, run_id),
        lambda key: key[0].startswith("correctness_check"),
    )
    for name in ("correctness_check_sim", "correctness_check_board"):
        (ended,) = checks[(name, 0, 1, 1)]
        assert ended["result"]["outcome"] == "pass"
        assert ended["result"]["counts"] == [{"failed": 0, "non_finite": 0}]
        assert (
            check_standing.standing(lines, name, 0, 1, 1)
            is check_standing.Standing.VERIFIED
        )
    baseline = lines[-1]["data"]["result"]
    assert timings_tool.timing_problem(baseline) is None
    assert baseline["outcome"] in ("converged", "not_converged")
    assert baseline["shape"] == SHAPE
    assert sorted(path.name for path in (run / MEASURE).iterdir()) == [
        "build-log-board_run_timing-01.txt",
        "build-log-correctness_check_board-01.txt",
        "build-log-correctness_check_sim-01.txt",
    ]
    for absent in ("artifacts.json", "rounds/0000/eval", "rounds/0000/decision"):
        assert not (run / absent).exists()

    hw_key = keys.hw_profile_key(PROFILE).name
    op_key = keys.op_signature_key(OP).name
    assert key_records.load_hw_profile(world.root, hw_key) == PROFILE
    assert key_records.load_op_signature(world.root, hw_key, op_key) == OP

    assert world.git("log", "--format=%s").splitlines() == [COMMIT_SUBJECT] * 2
    assert_committed_clean(world, run_id)

    log = world.session_log()
    assert turns(log) == [1]
    assert steps(log) == ROUND_ZERO
    for entry in requests(log):
        given = entry["message"] if "delegate" in entry else entry["arguments"]
        assert given["run_id"] == run_id
    assert [entry["error"] for entry in requests(log) if "tool" in entry] == [
        name == "state_read" for _, name in [s for s in ROUND_ZERO if len(s) == 2]
    ]
    assert_hooks_ran_and_passed(requests(log))
    assert_each_delegation_its_own_agent(log)
    assert_stopped_once(log, 1)

    runs = world.docker_runs()
    assert [entry.get("container") for entry in runs] == [
        None,
        "coder",
        None,
        "build",
        "process",
        "build",
        "process",
        "build",
        "build",
        "timing",
    ]
    assert all(entry["status"] == 0 for entry in runs)
    (coder,) = [entry for entry in runs if entry.get("container") == "coder"]
    assert coder["token_passed"] is True
    assert coder["image"] == FAKE["HILCLAW_CODER_IMAGE"]
    assert {entry["image"] for entry in runs if "image" in entry} - {
        coder["image"]
    } == {FAKE["HILCLAW_STANDIN_IMAGE"]}
    assert list(world.sessions.iterdir()) == []


@pytest.mark.xfail(
    strict=True,
    reason=(
        "gap: turn_loop gives a turn session the entry's own standard output, so "
        "the reply a -p session writes there comes before the entry's one line; "
        "where a session's output should go instead is a choice no record makes"
    ),
)
def test_the_entry_writes_one_line_on_standard_output(world):
    world.install()
    run_id = world.new_run(document())

    done = world.turn_start(run_id)

    assert done.returncode == 0
    assert len(done.stdout.decode("ascii").splitlines()) == 1


@pytest.mark.parametrize("kernel", [None, WRONG_KERNEL], ids=["no_kernel", "wrong"])
def test_round_zero_stops_without_an_attempt_that_stands(world, kernel):
    world.install(kernel=kernel)
    run_id = world.new_run(document())
    run = world.run_dir(run_id)

    done = world.turn_start(run_id)

    told(done, "unchanged_turn", 12)
    state = state_of(world, run_id)
    assert (state.round, state.others) == (0, {})
    assert (run / ATTEMPT / "spec.json").is_file()
    lines = events.read(world.root, run_id).events
    log = world.session_log()
    assert turns(log) == [1, 2]
    stop = [("round-manager", "run_commit")]
    if kernel is None:
        assert steps(log, 1) == ROUND_ZERO[:8] + stop
        assert requests(log, 1)[7]["answer"]["taken"] == []
        assert not (run / ATTEMPT / "output").exists()
        assert lines == []
    else:
        assert steps(log, 1) == ROUND_ZERO[:11] + stop
        assert (run / ATTEMPT / "output/gemm.c").is_file()
        assert [line["data"]["step"] for line in lines] == ["correctness_check_sim"] * 2
        assert lines[-1]["data"]["result"]["outcome"] == "fail"
        found = check_standing.standing(lines, "correctness_check_sim", 0, 1, 1)
        assert found is check_standing.Standing.NOT_VERIFIED
    assert steps(log, 2) == [
        ("round-manager", "run_commit"),
        ("round-manager", "state_read"),
        ("round-manager", "instance_read"),
        ("round-manager", "key_store"),
        ("round-manager", "Agent", "coder-driver"),
        ("coder-driver", "spec_write"),
        *stop,
    ]
    assert requests(log, 2)[5]["answer"]["error"]["kind"] == "spec_exists"
    assert_hooks_ran_and_passed(requests(log))
    assert_stopped_once(log, 1)
    assert_stopped_once(log, 2)
    assert not (run / "rounds/0000/eval").exists()
    assert not (run / MEASURE / "build-log-board_run_timing-01.txt").exists()
    coders = [
        entry for entry in world.docker_runs() if entry.get("container") == "coder"
    ]
    assert len(coders) == 1
    assert_committed_clean(world, run_id)


def test_a_round_manager_call_of_coder_run_is_refused_by_the_caller_check(world):
    world.install(turns=({"rogue": "coder_run"},))
    run_id = world.new_run(document())

    done = world.turn_start(run_id)

    told(done, "run_over", 0)
    log = world.session_log()
    rogue = requests(log)[5]
    assert step(rogue) == ("round-manager", "coder_run")
    assert rogue["refused"] is True
    assert "answer" not in rogue
    assert [(hook["entry"], hook["status"]) for hook in rogue["hooks"]] == [
        (0, 2),
        (1, 0),
    ]
    assert "caller check" in rogue["hooks"][0]["stderr"]
    rest = [entry for entry in requests(log) if entry is not rogue]
    assert [step(entry) for entry in rest] == ROUND_ZERO
    assert_hooks_ran_and_passed(rest)
    coders = [
        entry for entry in world.docker_runs() if entry.get("container") == "coder"
    ]
    assert len(coders) == 1


def test_a_turn_that_fails_before_progress_ends_the_start_failed_turn(world):
    world.install(turns=({"exit_first": 3},))
    run_id = world.new_run(document())
    run = world.run_dir(run_id)

    done = world.turn_start(run_id)

    told(done, "failed_turn", 11, exit_status=3)
    assert [path.name for path in run.iterdir()] == ["instance.json"]
    log = world.session_log()
    assert turns(log) == [1]
    assert requests(log) == []
    assert world.docker_runs() == []


def test_a_run_at_its_round_budget_at_entry_goes_over_with_no_round_begun(world):
    world.install()
    run_id = world.new_run(document())
    replace(world.root, run_id, 1, EMPTY)
    run = world.run_dir(run_id)

    done = world.turn_start(run_id)

    told(done, "run_over", 0)
    state = run_state.parse((run / "STATE.json").read_bytes())
    assert (state.round, state.others) == (1, {"run_status": "over"})
    log = world.session_log()
    assert steps(log) == [
        ("round-manager", "run_commit"),
        ("round-manager", "state_read"),
        ("round-manager", "instance_read"),
        ("round-manager", "state_write"),
        ("round-manager", "run_commit"),
    ]
    assert requests(log)[3]["arguments"]["state"] == {
        **json.loads(run_state.dump(1, EMPTY)),
        "run_status": "over",
    }
    assert_hooks_ran_and_passed(requests(log))
    assert_stopped_once(log, 1)
    assert not (run / "rounds").exists()
    assert not (world.root / "db").exists()
    assert world.docker_runs() == []
    assert_committed_clean(world, run_id)
