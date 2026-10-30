import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import first_run_stubs as stubs
import pytest

from hilclaw import (
    cases,
    cases_file,
    check_standing,
    checks_tool,
    events,
    hypotheses,
    hypotheses_file,
    key_records,
    keys,
    layout,
    run_commit,
    run_file_tools,
    run_state,
    spec,
    spec_file,
    standin_profile,
    timings_tool,
    verdicts,
    verdicts_file,
    verdicts_hypotheses,
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
HEADER = """#include <stddef.h>

"""
SIGNATURE = """void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a,
                  const float *restrict b, float *restrict c)
"""
IKJ_KERNEL = (
    HEADER
    + SIGNATURE
    + """{
    for (size_t i = 0; i < m; i++) {
        float *restrict row = c + i * n;
        for (size_t j = 0; j < n; j++)
            row[j] = 0.0f;
        for (size_t p = 0; p < k; p++) {
            const float x = a[i * k + p];
            const float *restrict across = b + p * n;
            for (size_t j = 0; j < n; j++)
                row[j] += x * across[j];
        }
    }
}
"""
)
BLOCKED_KERNEL = (
    HEADER
    + "enum { MB = 4, KB = 4, NB = 4 };\n\n"
    + SIGNATURE
    + """{
    for (size_t x = 0; x < m * n; x++)
        c[x] = 0.0f;
    for (size_t j0 = 0; j0 < n; j0 += NB) {
        size_t j1 = (n - j0 < NB) ? n : j0 + NB;
        for (size_t p0 = 0; p0 < k; p0 += KB) {
            size_t p1 = (k - p0 < KB) ? k : p0 + KB;
            for (size_t i0 = 0; i0 < m; i0 += MB) {
                size_t i1 = (m - i0 < MB) ? m : i0 + MB;
                for (size_t i = i0; i < i1; i++)
                    for (size_t p = p0; p < p1; p++) {
                        const float x = a[i * k + p];
                        for (size_t j = j0; j < j1; j++)
                            c[i * n + j] += x * b[p * n + j];
                    }
            }
        }
    }
}
"""
)
REGISTER_KERNEL = (
    HEADER
    + """enum { MR = 4, NR = 4 };

static float dot(size_t k, size_t n, const float *restrict row,
                 const float *restrict column)
{
    float sum = 0.0f;
    for (size_t p = 0; p < k; p++)
        sum += row[p] * column[p * n];
    return sum;
}

"""
    + SIGNATURE
    + """{
    size_t mf = m - m % MR, nf = n - n % NR;
    for (size_t i0 = 0; i0 < mf; i0 += MR)
        for (size_t j0 = 0; j0 < nf; j0 += NR) {
            float sum[MR][NR] = {{0.0f}};
            for (size_t p = 0; p < k; p++)
                for (size_t r = 0; r < MR; r++) {
                    const float x = a[(i0 + r) * k + p];
                    for (size_t s = 0; s < NR; s++)
                        sum[r][s] += x * b[p * n + j0 + s];
                }
            for (size_t r = 0; r < MR; r++)
                for (size_t s = 0; s < NR; s++)
                    c[(i0 + r) * n + j0 + s] = sum[r][s];
        }
    for (size_t i = 0; i < mf; i++)
        for (size_t j = nf; j < n; j++)
            c[i * n + j] = dot(k, n, a + i * k, b + j);
    for (size_t i = mf; i < m; i++)
        for (size_t j = 0; j < n; j++)
            c[i * n + j] = dot(k, n, a + i * k, b + j);
}
"""
)
UNROLLED_KERNEL = (
    HEADER
    + SIGNATURE
    + """{
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < n; j++) {
            float sum = 0.0f;
            size_t p = 0;
            for (; p + 4 <= k; p += 4) {
                sum += a[i * k + p] * b[p * n + j];
                sum += a[i * k + p + 1] * b[(p + 1) * n + j];
                sum += a[i * k + p + 2] * b[(p + 2) * n + j];
                sum += a[i * k + p + 3] * b[(p + 3) * n + j];
            }
            for (; p < k; p++)
                sum += a[i * k + p] * b[p * n + j];
            c[i * n + j] = sum;
        }
}
"""
)
ROUND_KERNELS = {
    1: IKJ_KERNEL,
    2: BLOCKED_KERNEL,
    3: REGISTER_KERNEL,
    4: UNROLLED_KERNEL,
}
CHOICES = {
    "1": {
        "techniques": ["loop_order_ikj"],
        "statement": "Running the loops in the order i, p, j lowers the board "
        "latency against the round-0 baseline.",
        "direction": "lower",
    },
    "2": {
        "techniques": ["cache_blocking"],
        "statement": "Splitting the i, p, j loops into blocks lowers the board "
        "latency against the round-0 baseline.",
        "direction": "lower",
    },
    "3": {
        "techniques": ["register_blocking"],
        "statement": "Keeping a 4 by 4 tile of c in registers lowers the board "
        "latency against the round-0 baseline.",
        "direction": "lower",
    },
    "4": {
        "techniques": [],
        "statement": "Unrolling the loop over k by four lowers the board "
        "latency against the round-0 baseline.",
        "direction": "lower",
    },
}
CHOICES["default"] = CHOICES["1"]
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

    def install(self, kernel=KERNEL, turns=({},), kernels=None, choices=None):
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
            "kernels": {
                str(round_): None if text is None else {"gemm.c": text}
                for round_, text in (kernels or {}).items()
            },
            "choices": CHOICES if choices is None else choices,
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
        "correctness_check_sim_v2",
        "correctness_check_board_v2",
        "board_run_timing_v2",
    ]
    assert {(line["round"], line["candidate"], line["attempt"]) for line in lines} == {
        (0, 1, 1)
    }
    checks = checks_tool.checks_of(
        run_id,
        checks_tool.log_lines(world.root, run_id),
        lambda key: key[0].startswith("correctness_check"),
    )
    for name in ("correctness_check_sim_v2", "correctness_check_board_v2"):
        (ended,) = checks[(name, 0, 1, 1)]
        assert ended["result"]["outcome"] == "pass"
        assert ended["result"]["counts"] == {"c": [{"failed": 0, "non_finite": 0}]}
        assert ended["result"]["contract_key"] == {
            "kind": "gemm",
            "dtype": "fp32",
            "layout": "row_major",
        }
        assert (
            check_standing.standing(lines, name, 0, 1, 1)
            is check_standing.Standing.VERIFIED
        )
    baseline = lines[-1]["data"]["result"]
    assert timings_tool.timing_problem(baseline) is None
    assert baseline["outcome"] in ("converged", "not_converged")
    assert baseline["shape"] == SHAPE
    assert baseline["contract_key"] == {
        "kind": "gemm",
        "dtype": "fp32",
        "layout": "row_major",
    }
    assert baseline["unit"] == "ns"
    assert sorted(path.name for path in (run / MEASURE).iterdir()) == [
        "build-log-board_run_timing_v2-01.txt",
        "build-log-correctness_check_board_v2-01.txt",
        "build-log-correctness_check_sim_v2-01.txt",
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


def last_replies(log):
    replies = {}
    for entry in log:
        if entry.get("started"):
            replies[entry["turn"]] = ""
        elif "report" in entry:
            replies[entry["turn"]] = entry["report"]
    return [replies[turn] for turn in sorted(replies)]


def test_the_entry_writes_one_line_on_standard_output(world):
    world.install()
    run_id = world.new_run(document())

    done = world.turn_start(run_id)

    assert done.returncode == 0
    assert len(done.stdout.decode("ascii").splitlines()) == 1
    assert json.loads(done.stdout)["outcome"] == "run_over"
    replies = last_replies(world.session_log())
    assert replies and all(replies)
    assert done.stderr.decode("utf-8") == "".join(f"{text}\n" for text in replies)


@pytest.mark.parametrize("kernel", [None, WRONG_KERNEL], ids=["no_kernel", "wrong"])
def test_round_zero_without_an_attempt_that_stands_ends_its_round(world, kernel):
    world.install(kernel=kernel)
    run_id = world.new_run(document())
    run = world.run_dir(run_id)

    done = world.turn_start(run_id)

    told(done, "run_over", 0)
    state = state_of(world, run_id)
    assert (state.round, state.others) == (1, {"run_status": "over"})
    assert (run / ATTEMPT / "spec.json").is_file()
    lines = events.read(world.root, run_id).events
    log = world.session_log()
    assert turns(log) == [1]
    closing = [("round-manager", "round_end"), ("round-manager", "run_commit")]
    if kernel is None:
        assert steps(log, 1) == ROUND_ZERO[:8] + closing
        assert requests(log, 1)[7]["answer"]["taken"] == []
        assert not (run / ATTEMPT / "output").exists()
        assert lines == []
    else:
        assert steps(log, 1) == ROUND_ZERO[:11] + closing
        assert (run / ATTEMPT / "output/gemm.c").is_file()
        assert [line["data"]["step"] for line in lines] == [
            "correctness_check_sim_v2"
        ] * 2
        assert lines[-1]["data"]["result"]["outcome"] == "fail"
        found = check_standing.standing(lines, "correctness_check_sim_v2", 0, 1, 1)
        assert found is check_standing.Standing.NOT_VERIFIED
    assert_hooks_ran_and_passed(requests(log))
    assert_stopped_once(log, 1)
    assert not (run / "rounds/0000/eval").exists()
    assert not (run / MEASURE / "build-log-board_run_timing_v2-01.txt").exists()
    coders = [
        entry for entry in world.docker_runs() if entry.get("container") == "coder"
    ]
    assert len(coders) == 1
    assert_committed_clean(world, run_id)


def test_the_round_after_a_failed_round_zero_retries_with_its_failure(world):
    world.install(kernel=WRONG_KERNEL)
    run_id = world.new_run(document(budget=2))
    run = world.run_dir(run_id)

    done = world.turn_start(run_id)

    told(done, "run_over", 0)
    assert state_of(world, run_id).round == 2
    later = run / ATTEMPT.replace("rounds/0000", "rounds/0001") / "spec.json"
    content = spec_file.parse(later.read_bytes())
    spec.validate(content)
    (shown,) = content["feedback"]["attempts"]
    assert (shown["round"], shown["failure"]["stage"]) == (0, "sim")
    assert "base" not in content["feedback"]
    assert turns(world.session_log()) == [1, 2]
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


VERDICT_OF = {
    "lower": "supported",
    "higher": "refuted",
    "not_different": "inconclusive",
}
ENTRY = [
    ("round-manager", "run_commit"),
    ("round-manager", "state_read"),
    ("round-manager", "instance_read"),
    ("round-manager", "key_store"),
]
CODER = [
    ("round-manager", "Agent", "coder-driver"),
    ("coder-driver", "spec_write"),
    ("coder-driver", "coder_run"),
]
CHECK_STEP = [
    ("round-manager", "Agent", "evaluator"),
    ("evaluator", "correctness_check"),
    ("evaluator", "checks_read"),
]
CLOSING = [
    ("round-manager", "case_write"),
    ("round-manager", "round_end"),
    ("round-manager", "run_commit"),
]


def selection(round_):
    return [
        ("round-manager", "Agent", "technique-selector"),
        ("technique-selector", "cases_lookup"),
        *[("technique-selector", "verdicts_read")] * (round_ - 1),
        ("technique-selector", "catalog_read"),
        ("technique-selector", "checks_read"),
        ("technique-selector", "hypotheses_write"),
        ("round-manager", "hypotheses_read"),
    ]


def judging(compared=True):
    return [
        ("round-manager", "Agent", "evaluator"),
        ("evaluator", "hypotheses_read"),
        *[("evaluator", "checks_read")] * 3,
        *([("evaluator", "timings_compare")] if compared else []),
        ("evaluator", "verdicts_write"),
    ]


MEASURING = [
    ("round-manager", "Agent", "experiment-runner"),
    ("experiment-runner", "board_run"),
]


def later_round(round_):
    return [
        *ENTRY,
        *selection(round_),
        *CODER,
        *CHECK_STEP,
        *CHECK_STEP,
        *MEASURING,
        *judging(),
        *CLOSING,
    ]


def round_paths(world, run_id, round_):
    hw_key = keys.hw_profile_key(PROFILE).name
    op_key = keys.op_signature_key(OP).name
    root = world.root
    spec_path = layout.attempt_artefact(root, run_id, round_, 1, 1, "spec.json")
    return {
        "hypotheses": layout.hypothesis_record(root, run_id, round_),
        "verdicts": layout.verdict_record(root, run_id, round_),
        "case": layout.case_record(root, hw_key, op_key, run_id, round_),
        "attempt": spec_path.parent,
    }


def stored_round(world, run_id, round_):
    paths = round_paths(world, run_id, round_)
    record = hypotheses_file.parse(paths["hypotheses"].read_bytes())
    hypotheses.validate(record)
    judged = verdicts_file.parse(paths["verdicts"].read_bytes())
    verdicts.validate(judged)
    verdicts_hypotheses.check(judged, record)
    case = cases_file.parse(paths["case"].read_bytes())
    cases.validate(case)
    assert case == cases.build(record, judged)
    content = spec_file.parse((paths["attempt"] / "spec.json").read_bytes())
    spec.validate(content)
    assert (content["id"]["round"], content["id"]["candidate"]) == (round_, 1)
    return record, judged, content


def assert_verdict_follows_its_comparison(entry, record):
    (hypothesis,) = [h for h in record["hypotheses"] if h["id"] == entry["hypothesis"]]
    (wanted,) = hypothesis["expected"]
    assert wanted["direction"] == "lower"
    compared = [e for e in entry["evidence"] if e["kind"] == "comparison"]
    if not compared:
        assert entry["verdict"] == "inconclusive"
        return
    (comparison,) = compared
    assert entry["verdict"] == VERDICT_OF[comparison["difference"]]
    assert comparison["against"] == {"round": 0, "candidate": 1, "attempt": 1}
    checked = {
        (e["ref"]["round"], e["point"]): e["outcome"]
        for e in entry["evidence"]
        if e["kind"] == "check"
    }
    assert checked[(0, "board")] == checked[(record["round"], "board")] == "pass"


def selector_requests(log, turn):
    return [
        entry for entry in requests(log, turn) if entry["agent"] == "technique-selector"
    ]


def test_five_rounds_of_a_first_run_end_the_run_over(world):
    world.install(kernels=ROUND_KERNELS)
    run_id = world.new_run(document(budget=5))
    run = world.run_dir(run_id)

    done = world.turn_start(run_id)

    told(done, "run_over", 0)
    state = run_state.parse((run / "STATE.json").read_bytes())
    assert (state.round, state.others) == (5, {"run_status": "over"})
    log = world.session_log()
    assert turns(log) == [1, 2, 3, 4, 5]
    assert steps(log, 1) == ROUND_ZERO
    for turn in range(2, 6):
        assert steps(log, turn) == later_round(turn - 1), turn
    for turn in range(1, 6):
        (ended,) = [
            entry
            for entry in requests(log, turn)
            if step(entry) == ("round-manager", "round_end")
        ]
        assert ended["arguments"]["round"] == turn - 1
        assert ended["answer"]["over"] is (turn == 5)
        assert_stopped_once(log, turn)
    errors = [entry for entry in requests(log) if entry.get("error")]
    assert [(entry["turn"], step(entry)) for entry in errors] == [
        (1, ("round-manager", "state_read"))
    ]
    assert_hooks_ran_and_passed(requests(log))
    assert_each_delegation_its_own_agent(log)

    lines = events.read(world.root, run_id).events
    for line in lines:
        events.validate(line)
    for round_ in range(1, 5):
        record, judged, content = stored_round(world, run_id, round_)
        chosen = CHOICES[str(round_)]
        named = [entry["id"] for entry in content["guidance"]["techniques"]]
        assert named == chosen["techniques"]
        attempt = round_paths(world, run_id, round_)["attempt"]
        kernel = (attempt / "output/gemm.c").read_text(encoding="utf-8")
        assert kernel == ROUND_KERNELS[round_]
        (hypothesis,) = record["hypotheses"]
        assert hypothesis["statement"] == chosen["statement"]
        assert record["cases_read"] == []
        assert [b["kind"] for b in hypothesis["basis"]] == ["attempt"] * min(round_, 2)
        ids = {h["id"] for h in record["hypotheses"]}
        assert [entry["hypothesis"] for entry in judged["verdicts"]] == sorted(ids)
        for entry in judged["verdicts"]:
            assert_verdict_follows_its_comparison(entry, record)
        mine = [
            line
            for line in lines
            if (line["round"], line["candidate"], line["attempt"]) == (round_, 1, 1)
        ]
        assert [line["data"]["step"] for line in mine[1::2]] == [
            "correctness_check_sim_v2",
            "correctness_check_board_v2",
            "board_run_timing_v2",
        ]
        for name, line in zip(
            ("correctness_check_sim_v2", "correctness_check_board_v2"), mine[1:4:2]
        ):
            assert line["data"]["result"]["outcome"] == "pass"
            found = check_standing.standing(lines, name, round_, 1, 1)
            assert found is check_standing.Standing.VERIFIED
        timing = mine[-1]["data"]["result"]
        assert timings_tool.timing_problem(timing) is None
        assert timing["outcome"] in ("converged", "not_converged")

    assert "verdicts_read" not in [step(e)[1] for e in selector_requests(log, 2)]
    for turn in range(3, 6):
        asked = selector_requests(log, turn)
        names = [step(entry)[1] for entry in asked]
        reads = [e for e in asked if step(e)[1] == "verdicts_read"]
        assert [e["arguments"]["round"] for e in reads] == list(range(1, turn - 1))
        assert [e["answer"]["record"]["round"] for e in reads] == list(
            range(1, turn - 1)
        )
        last_read = max(i for i, name in enumerate(names) if name == "verdicts_read")
        assert names.index("hypotheses_write") > last_read

    assert not (run / "artifacts.json").exists()
    subjects = world.git("log", "--format=%s").splitlines()
    assert len(subjects) >= 5
    assert set(subjects) == {COMMIT_SUBJECT}
    assert_committed_clean(world, run_id)
    runs = world.docker_runs()
    coders = [entry for entry in runs if entry.get("container") == "coder"]
    assert [entry["round"] for entry in coders] == [0, 1, 2, 3, 4]
    assert all(entry["status"] == 0 for entry in runs)
    assert list(world.sessions.iterdir()) == []


def test_a_second_run_of_the_same_key_reads_the_first_runs_cases(world):
    cite = {**CHOICES["1"], "cite_case": True}
    world.install(kernels=ROUND_KERNELS, choices={"default": cite})
    first = world.new_run(document(budget=2))
    told(world.turn_start(first), "run_over", 0)
    first_record, _, _ = stored_round(world, first, 1)
    first_case = cases_file.parse(round_paths(world, first, 1)["case"].read_bytes())

    second = world.new_run(document(budget=2))
    done = world.turn_start(second)

    told(done, "run_over", 0)
    log = world.session_log()
    assert turns(log) == [1, 2, 3, 4]
    assert steps(log, 3) == ROUND_ZERO
    assert steps(log, 4) == later_round(1)
    (first_looked,) = [
        e for e in selector_requests(log, 2) if step(e)[1] == "cases_lookup"
    ]
    assert first_looked["answer"]["cases"] == []
    (looked,) = [e for e in selector_requests(log, 4) if step(e)[1] == "cases_lookup"]
    assert looked["arguments"] == {"run_id": second}
    assert looked["answer"]["cases"] == [first_case]
    assert looked["answer"]["cases_read"] == [{"run_id": first, "round": 1}]
    assert looked["answer"]["reports"] == []

    record, judged, _ = stored_round(world, second, 1)
    assert record["cases_read"] == [{"run_id": first, "round": 1}]
    (hypothesis,) = record["hypotheses"]
    (cited,) = [b for b in hypothesis["basis"] if b["kind"] == "case"]
    assert cited["case"] == {
        "run_id": first,
        "round": 1,
        "hypothesis": first_record["hypotheses"][0]["id"],
    }
    assert [b["kind"] for b in first_record["hypotheses"][0]["basis"]] == ["attempt"]
    for entry in judged["verdicts"]:
        assert_verdict_follows_its_comparison(entry, record)
    assert_hooks_ran_and_passed(requests(log))
    assert_committed_clean(world, first)
    assert_committed_clean(world, second)


@pytest.mark.parametrize("kernel", [None, WRONG_KERNEL], ids=["no_kernel", "wrong"])
def test_a_round_whose_attempt_does_not_stand_still_gets_its_verdicts(world, kernel):
    world.install(kernels={1: kernel})
    run_id = world.new_run(document(budget=2))
    run = world.run_dir(run_id)

    done = world.turn_start(run_id)

    told(done, "run_over", 0)
    state = run_state.parse((run / "STATE.json").read_bytes())
    assert (state.round, state.others) == (2, {"run_status": "over"})
    log = world.session_log()
    assert turns(log) == [1, 2]
    attempt = round_paths(world, run_id, 1)["attempt"]
    checks = [] if kernel is None else CHECK_STEP
    assert steps(log, 2) == [
        *ENTRY,
        *selection(1),
        *CODER,
        *checks,
        *judging(compared=False),
        *CLOSING,
    ]
    lines = [line for line in events.read(world.root, run_id).events if line["round"]]
    if kernel is None:
        (coded,) = [
            e for e in requests(log, 2) if step(e) == ("coder-driver", "coder_run")
        ]
        assert coded["answer"]["taken"] == []
        assert not (attempt / "output").exists()
        assert lines == []
        evidence = []
    else:
        assert [line["data"]["step"] for line in lines] == [
            "correctness_check_sim_v2"
        ] * 2
        found = check_standing.standing(lines, "correctness_check_sim_v2", 1, 1, 1)
        assert found is check_standing.Standing.NOT_VERIFIED
        ref = {"round": 1, "candidate": 1, "attempt": 1}
        evidence = [{"kind": "check", "ref": ref, "point": "sim", "outcome": "fail"}]
    record, judged, _ = stored_round(world, run_id, 1)
    (entry,) = judged["verdicts"]
    assert entry["hypothesis"] == record["hypotheses"][0]["id"]
    assert entry["verdict"] == "inconclusive"
    assert entry["evidence"] == evidence
    timings = [e for e in world.docker_runs() if e.get("container") == "timing"]
    assert len(timings) == 1
    assert_hooks_ran_and_passed(requests(log))
    assert_committed_clean(world, run_id)


def test_a_selector_call_of_verdicts_write_is_refused_by_the_caller_check(world):
    world.install(turns=({}, {"selector_rogue": "verdicts_write"}))
    run_id = world.new_run(document(budget=2))

    done = world.turn_start(run_id)

    told(done, "run_over", 0)
    log = world.session_log()
    rogue = selector_requests(log, 2)[0]
    assert step(rogue) == ("technique-selector", "verdicts_write")
    assert rogue["refused"] is True
    assert "answer" not in rogue
    assert [(hook["entry"], hook["status"]) for hook in rogue["hooks"]] == [(0, 2)]
    assert "caller check" in rogue["hooks"][0]["stderr"]
    rest = [entry for entry in requests(log, 2) if entry is not rogue]
    assert [step(entry) for entry in rest] == later_round(1)
    assert_hooks_ran_and_passed(rest)
    sent = [
        e for e in requests(log) if step(e)[1] == "verdicts_write" and "answer" in e
    ]
    assert [entry["agent"] for entry in sent] == ["evaluator"]


def test_a_round_whose_verdicts_are_not_written_comes_to_the_stop(world):
    world.install(turns=({}, {"verdicts": "unreadable"}))
    run_id = world.new_run(document(budget=2))

    done = world.turn_start(run_id)

    told(done, "unchanged_turn", 12)
    state = state_of(world, run_id)
    assert (state.round, state.others) == (1, {})
    log = world.session_log()
    assert turns(log) == [1, 2]
    assert steps(log, 2) == [
        *ENTRY,
        *selection(1),
        *CODER,
        *CHECK_STEP,
        *CHECK_STEP,
        *MEASURING,
        ("round-manager", "Agent", "evaluator"),
        ("evaluator", "hypotheses_read"),
        ("round-manager", "run_commit"),
    ]
    paths = round_paths(world, run_id, 1)
    hypotheses.validate(hypotheses_file.parse(paths["hypotheses"].read_bytes()))
    assert (paths["attempt"] / "spec.json").is_file()
    assert (paths["attempt"] / "output/gemm.c").is_file()
    assert not paths["verdicts"].exists()
    assert not paths["case"].exists()
    assert_hooks_ran_and_passed(requests(log))
    assert_stopped_once(log, 2)
    assert_committed_clean(world, run_id)
