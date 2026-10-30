import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from hilclaw import bring_in, coder_runtime, coder_tool, local_run
from hilclaw.coder_call import CoderNotStartedError
from hilclaw.coder_runtime import (
    ALLOWED_TOOLS,
    CONTAINER_SCRATCH,
    ENV_IMAGE,
    ENV_TOKEN,
    NAME_PREFIX,
    NOT_GONE_STATUS,
    NOT_STARTED_STATUSES,
    PROMPT,
    REMOVAL_TIMEOUT_S,
    TOKEN_NAME,
    VERSION_TIMEOUT_S,
    DockerRuntime,
)

TOKEN = "sk-ant-oat01-SENTINEL-TOKEN-7f3a"
ENV_DATA = "HILCLAW_DATA_REPO_LOCAL_PATH"
IMAGE = "registry.example/coder:1"
MODEL = "claude-sentinel-model-9"
CLIENT = "/usr/bin/docker"
SCRATCH = os.path.abspath(os.path.join(os.sep, "tmp", "hilclaw-scratch-q1"))
NAME = re.compile(re.escape(NAME_PREFIX) + r"[0-9a-f]{32}")
FORBIDDEN = {
    "--privileged",
    "--cap-add",
    "--device",
    "-v",
    "--volume",
    "--env-file",
    "--network",
    "--pid",
    "--ipc",
    "--userns",
    "-i",
    "--interactive",
    "-t",
    "--tty",
    "--dangerously-skip-permissions",
    "--allow-dangerously-skip-permissions",
    "bypassPermissions",
    "--bare",
    "--mcp-config",
}


def result(returncode=0, *, timed_out=False, stdout=b"", stderr=b""):
    def make(command):
        return local_run.RunResult(
            returncode=None if timed_out else returncode,
            timed_out=timed_out,
            stdout=stdout,
            stderr=stderr,
            command=tuple(command),
            duration_s=0.1,
        )

    return make


class Starts:
    def __init__(self):
        self.calls = []
        self.answers = []

    def __call__(self, command, **options):
        self.calls.append((list(command), options))
        answer = self.answers.pop(0) if self.answers else result()
        if isinstance(answer, BaseException):
            raise answer
        return answer(command)


class Process:
    def __init__(self, status, error):
        self.status = status
        self.error = error
        self.killed = 0
        self.waits = 0

    def wait(self):
        self.waits += 1
        if self.error is not None and self.waits == 1:
            raise self.error
        return self.status

    def kill(self):
        self.killed += 1


class Pipe:
    def __init__(self, data, size, error_after):
        self.data = data
        self.size = size
        self.error_after = error_after
        self.reads = 0
        self.closed = False
        self.drained = False

    def read1(self, limit):
        if self.error_after is not None and self.reads == self.error_after:
            raise KeyboardInterrupt
        self.reads += 1
        chunk, self.data = (
            self.data[: min(self.size, limit)],
            self.data[min(self.size, limit) :],
        )
        self.drained = not chunk
        return chunk

    def close(self):
        self.closed = True


class Popens:
    def __init__(self):
        self.calls = []
        self.processes = []
        self.status = 0
        self.wait_error = None
        self.start_error = None
        self.output = b""
        self.read_size = 65536
        self.read_error_after = None

    def __call__(self, command, **options):
        self.calls.append((list(command), options))
        if self.start_error is not None:
            raise self.start_error
        process = Process(self.status, self.wait_error)
        if options.get("stdout") is subprocess.PIPE:
            process.stdout = Pipe(self.output, self.read_size, self.read_error_after)
        self.processes.append(process)
        return process


@pytest.fixture(autouse=True)
def starts(monkeypatch):
    stub = Starts()
    monkeypatch.setattr(local_run, "run", stub)
    return stub


@pytest.fixture(autouse=True)
def popens(monkeypatch):
    stub = Popens()
    monkeypatch.setattr(subprocess, "Popen", stub)
    return stub


@pytest.fixture(autouse=True)
def ids(monkeypatch):
    monkeypatch.setattr(os, "getuid", lambda: 1000, raising=False)
    monkeypatch.setattr(os, "getgid", lambda: 1001, raising=False)


@pytest.fixture(autouse=True)
def which(monkeypatch):
    def find(program):
        return CLIENT if program == "docker" else None

    monkeypatch.setattr(shutil, "which", find)


def environ(**changes):
    values = {"PATH": "/usr/bin", "LANG": "C", ENV_IMAGE: IMAGE, ENV_TOKEN: TOKEN}
    for key, value in changes.items():
        if value is None:
            values.pop(key, None)
        else:
            values[key] = value
    return values


def run(env=None, *, scratch=SCRATCH, model=MODEL):
    runtime = DockerRuntime(environ=environ() if env is None else env)
    return runtime.run(scratch, coder_model=model)


def expected(name):
    return [
        CLIENT,
        "run",
        "--name",
        name,
        "--rm",
        "--pull",
        "never",
        "--mount",
        f"type=bind,source={SCRATCH},target=/scratch",
        "--workdir",
        "/scratch",
        "--user",
        "1000:1001",
        "--entrypoint=",
        "--env",
        "HOME=/tmp",
        "--env",
        "CLAUDE_CODE_OAUTH_TOKEN",
        "--env",
        "DISABLE_UPDATES=1",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges=true",
        IMAGE,
        "claude",
        "-p",
        PROMPT,
        "--model",
        MODEL,
        "--permission-mode",
        "dontAsk",
        "--allowedTools",
        "Bash,Read,Edit,Write",
        "--setting-sources",
        "project",
        "--no-session-persistence",
    ]


def removal(name):
    return [CLIENT, "container", "rm", "--force", name]


def text_of(error):
    parts = [str(error), repr(error), *getattr(error, "__notes__", [])]
    if error.__cause__ is not None:
        parts.append(str(error.__cause__))
    return "\n".join(parts)


def test_constants():
    assert ENV_IMAGE == "HILCLAW_CODER_IMAGE"
    assert ENV_TOKEN == "HILCLAW_CODER_OAUTH_TOKEN"
    assert TOKEN_NAME == "CLAUDE_CODE_OAUTH_TOKEN"
    assert NAME_PREFIX == "hilclaw-coder-"
    assert CONTAINER_SCRATCH == "/scratch"
    assert ALLOWED_TOOLS == "Bash,Read,Edit,Write"
    assert NOT_STARTED_STATUSES == {125, 126, 127}
    assert isinstance(NOT_GONE_STATUS, int) and NOT_GONE_STATUS != 0
    assert NOT_GONE_STATUS not in NOT_STARTED_STATUSES
    assert 0 < VERSION_TIMEOUT_S < 60 and 0 < REMOVAL_TIMEOUT_S <= 60


def test_run_happy_vector_environment_streams_and_removal(starts, popens):
    assert run() == 0
    [(command, options)] = popens.calls
    name = command[3]
    assert NAME.fullmatch(name)
    assert command == expected(name)
    assert options["stdin"] is subprocess.DEVNULL
    assert options["stdout"] is subprocess.DEVNULL
    assert options["stderr"] is subprocess.DEVNULL
    assert not options.get("shell", False)
    assert "timeout" not in options
    env = options["env"]
    assert env[TOKEN_NAME] == TOKEN
    assert env["LANG"] == "C" and env["PATH"] == "/usr/bin"
    assert env[ENV_IMAGE] == IMAGE
    assert starts.calls == [
        (removal(name), {"timeout_s": REMOVAL_TIMEOUT_S, "env": environ()})
    ]


def test_run_token_overrides_existing_child_variable(popens):
    run(environ(**{TOKEN_NAME: "host-token"}))
    assert popens.calls[0][1]["env"][TOKEN_NAME] == TOKEN


def test_run_name_is_new_per_call(popens):
    run()
    run()
    first, second = (command[3] for command, _ in popens.calls)
    assert first != second


def test_run_accepts_pathlike(popens):
    run(scratch=Path(SCRATCH))
    assert popens.calls[0][0] == expected(popens.calls[0][0][3])


@pytest.mark.parametrize("status", [1, 143, -9, 2])
def test_run_returns_nonzero_status(popens, status):
    popens.status = status
    assert run() == status


def test_run_options_forbidden_and_counted(popens):
    run()
    command = popens.calls[0][0]
    assert FORBIDDEN.isdisjoint(command)
    assert not any(part.startswith(("--network", "--privileged")) for part in command)
    assert command.count("--mount") == 1
    assert command.count("--env") == 3


def test_run_with_os_environ_default(monkeypatch, popens, starts):
    monkeypatch.setenv(ENV_IMAGE, IMAGE)
    monkeypatch.setenv(ENV_TOKEN, TOKEN)
    runtime = DockerRuntime()
    monkeypatch.setenv("HILCLAW_LATE", "late")
    assert runtime.run(SCRATCH, coder_model=MODEL) == 0
    env = popens.calls[0][1]["env"]
    assert env["HILCLAW_LATE"] == "late" and env[TOKEN_NAME] == TOKEN
    assert starts.calls[0][1]["env"] is None


@pytest.mark.parametrize("status", sorted(NOT_STARTED_STATUSES))
def test_run_not_started_statuses(starts, popens, status):
    popens.status = status
    with pytest.raises(CoderNotStartedError, match=str(status)) as caught:
        run()
    name = popens.calls[0][0][3]
    assert [command for command, _ in starts.calls] == [removal(name)]
    assert not getattr(caught.value, "__notes__", [])


def test_run_not_started_status_and_not_gone_adds_note(starts, popens):
    popens.status = 125
    starts.answers = [result(1, stderr=b"daemon down")]
    with pytest.raises(CoderNotStartedError) as caught:
        run()
    assert "not shown gone" in caught.value.__notes__[0]


@pytest.mark.parametrize(
    "answer",
    [
        result(0),
        result(1, stderr=b"Error: No such container: hilclaw-coder-x\n"),
        result(1, stderr=b"Error response from daemon: No such container: x\n"),
    ],
)
def test_removal_shown_gone(starts, popens, answer):
    popens.status = 3
    starts.answers = [answer]
    assert run() == 3


@pytest.mark.parametrize(
    "answer",
    [
        result(1, stderr=b"Error response from daemon: removal in progress"),
        result(2),
        result(timed_out=True, stderr=b"No such container"),
        OSError("gone"),
        local_run.ProgramNotFoundError("docker"),
        OverflowError("limit"),
    ],
)
def test_removal_not_shown_gone_after_success(starts, popens, answer):
    starts.answers = [answer]
    assert run() == NOT_GONE_STATUS


def test_wait_cut_off_removes_reaps_and_reraises(starts, popens):
    popens.wait_error = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt) as caught:
        run()
    name = popens.calls[0][0][3]
    assert [command for command, _ in starts.calls] == [removal(name)]
    process = popens.processes[0]
    assert process.killed == 1 and process.waits == 2
    assert not getattr(caught.value, "__notes__", [])


def test_wait_cut_off_removal_raises_adds_note(starts, popens):
    popens.wait_error = KeyboardInterrupt()
    starts.answers = [OSError(TOKEN)]
    with pytest.raises(KeyboardInterrupt) as caught:
        run()
    [note] = caught.value.__notes__
    assert "OSError" in note and TOKEN not in note
    assert popens.processes[0].killed == 1


def test_wait_cut_off_removal_not_gone_adds_note(starts, popens):
    popens.wait_error = RuntimeError("wait failed")
    starts.answers = [result(timed_out=True)]
    with pytest.raises(RuntimeError, match="wait failed") as caught:
        run()
    assert "not shown gone" in caught.value.__notes__[0]


def test_wait_cut_off_kill_of_ended_process(starts, popens, monkeypatch):
    popens.wait_error = KeyboardInterrupt()

    def kill(self):
        raise ProcessLookupError()

    monkeypatch.setattr(Process, "kill", kill)
    with pytest.raises(KeyboardInterrupt):
        run()
    assert popens.processes[0].waits == 2


def test_start_oserror_becomes_not_started(starts, popens):
    popens.start_error = PermissionError(13, "denied", CLIENT)
    with pytest.raises(CoderNotStartedError) as caught:
        run()
    assert isinstance(caught.value.__cause__, PermissionError)
    assert TOKEN not in text_of(caught.value)
    assert starts.calls == []


def no_start(env, starts, popens, words):
    with pytest.raises(CoderNotStartedError) as caught:
        run(env)
    assert popens.calls == [] and starts.calls == []
    text = text_of(caught.value)
    for word in words:
        assert word in text
    assert TOKEN not in text
    return text


@pytest.mark.parametrize("image", [None, "", "-x", "a b", "x\0y", 7])
def test_image_refused(starts, popens, image):
    text = no_start(environ(**{ENV_IMAGE: image}), starts, popens, [ENV_IMAGE])
    if isinstance(image, str) and image:
        assert repr(image) not in text and image not in text.replace(ENV_IMAGE, "")


@pytest.mark.parametrize("token", [None, "", "${HILCLAW_CODER_OAUTH_TOKEN}", "a\0b", 7])
def test_token_refused(starts, popens, token):
    text = no_start(environ(**{ENV_TOKEN: token}), starts, popens, [ENV_TOKEN])
    if isinstance(token, str) and token:
        assert token not in text


def test_token_with_nul_never_quoted(starts, popens):
    secret = TOKEN + "\0"
    with pytest.raises(CoderNotStartedError) as caught:
        run(environ(**{ENV_TOKEN: secret}))
    assert TOKEN not in text_of(caught.value)


def test_client_not_on_path(starts, popens):
    runtime = DockerRuntime(environ=environ(), client="podman-absent")
    with pytest.raises(CoderNotStartedError, match="podman-absent"):
        runtime.run(SCRATCH, coder_model=MODEL)
    assert popens.calls == [] and starts.calls == []


@pytest.mark.parametrize("missing", ["getuid", "getgid"])
def test_no_numeric_ids(monkeypatch, starts, popens, missing):
    monkeypatch.delattr(os, missing, raising=False)
    no_start(environ(), starts, popens, ["getuid"])


@pytest.mark.parametrize(
    ("scratch", "error"),
    [
        (7, TypeError),
        (b"/tmp/x", TypeError),
        ("relative/scratch", ValueError),
        (SCRATCH + ",x", ValueError),
        (SCRATCH + '"', ValueError),
        (SCRATCH + "\n", ValueError),
        (SCRATCH + "\r", ValueError),
        (SCRATCH + "\0", ValueError),
    ],
)
def test_scratch_root_refused(starts, popens, scratch, error):
    with pytest.raises(error, match="scratch_root"):
        run(scratch=scratch)
    assert popens.calls == [] and starts.calls == []


def test_scratch_root_bytes_pathlike_refused(popens):
    class BytesPath:
        def __fspath__(self):
            return b"/tmp/x"

    with pytest.raises(TypeError, match="scratch_root"):
        run(scratch=BytesPath())


@pytest.mark.parametrize(
    ("model", "error"),
    [
        (None, TypeError),
        (1, TypeError),
        ("", ValueError),
        ("-x", ValueError),
        ("claude opus", ValueError),
        ("claude\topus", ValueError),
        ("claude\0", ValueError),
    ],
)
def test_coder_model_refused(starts, popens, model, error):
    with pytest.raises(error, match="coder_model"):
        run(model=model)
    assert popens.calls == [] and starts.calls == []


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"environ": ["PATH"]}, TypeError),
        ({"environ": "PATH=/bin"}, TypeError),
        ({"client": None}, TypeError),
        ({"client": b"docker"}, TypeError),
        ({"client": ""}, ValueError),
        ({"client": "dock\0er"}, ValueError),
    ],
)
def test_construction_refused(kwargs, error):
    with pytest.raises(error):
        DockerRuntime(**kwargs)


def test_secret_never_leaks(starts, popens):
    statuses = []
    for status in (0, 1):
        popens.status = status
        statuses.append(run())
    popens.status = 126
    with pytest.raises(CoderNotStartedError) as caught:
        run()
    assert TOKEN not in text_of(caught.value)
    popens.status = 0
    popens.wait_error = KeyboardInterrupt()
    starts.answers = [OSError("x")]
    with pytest.raises(KeyboardInterrupt) as cut:
        run()
    assert TOKEN not in text_of(cut.value)
    for command, options in popens.calls + starts.calls:
        assert all(TOKEN not in part for part in command)
    assert TOKEN not in repr(statuses)


class Recording(dict):
    def __init__(self, *args):
        super().__init__(*args)
        self.read = []

    def get(self, key, default=None):
        self.read.append(key)
        return super().get(key, default)

    def __getitem__(self, key):
        self.read.append(key)
        return super().__getitem__(key)


def test_available_true(starts):
    starts.answers = [result(0, stdout=b"27.3.1\n")]
    env = Recording({"PATH": "/usr/bin"})
    assert DockerRuntime(environ=env).available() is True
    [(command, options)] = starts.calls
    assert command == ["docker", "version", "--format", "{{.Server.Version}}"]
    assert options == {"timeout_s": VERSION_TIMEOUT_S, "env": {"PATH": "/usr/bin"}}
    assert ENV_IMAGE not in env.read and ENV_TOKEN not in env.read


def test_available_ignores_the_variables(starts, monkeypatch):
    monkeypatch.delenv(ENV_IMAGE, raising=False)
    monkeypatch.delenv(ENV_TOKEN, raising=False)
    starts.answers = [result(0, stdout=b"27.3.1\n")]
    assert DockerRuntime().available() is True
    assert starts.calls[0][1]["env"] is None
    starts.answers = [result(0, stdout=b"27.3.1\n")]
    bad = environ(**{ENV_IMAGE: "-x", ENV_TOKEN: "${HILCLAW_CODER_OAUTH_TOKEN}"})
    assert DockerRuntime(environ=bad).available() is True


@pytest.mark.parametrize(
    "answer",
    [
        local_run.ProgramNotFoundError("docker"),
        OSError("exec format"),
        OverflowError("limit"),
        result(1, stdout=b"27.3.1\n"),
        result(0, stdout=b""),
        result(0, stdout=b" \n\t\n"),
        result(timed_out=True),
    ],
)
def test_available_false(starts, answer):
    starts.answers = [answer]
    assert DockerRuntime(environ={}).available() is False


def test_prompt():
    assert "spec.json" in PROMPT and "output" in PROMPT
    assert str(bring_in.MAX_FILES) in PROMPT
    assert str(bring_in.MAX_FILE_BYTES) in PROMPT
    assert (bring_in.MAX_FILES, bring_in.MAX_FILE_BYTES) == (16, 262_144)
    for word in ("con", "prn", "aux", "nul", "com1", "lpt9", "diff", "subdirector"):
        assert word in PROMPT
    assert not PROMPT.startswith("-")
    assert SCRATCH not in PROMPT and "hilclaw-scratch" not in PROMPT
    assert "/tmp" not in PROMPT and "\\" not in PROMPT
    assert MODEL not in PROMPT and "claude-" not in PROMPT
    assert "run_id" not in PROMPT and TOKEN not in PROMPT
    assert "\0" not in PROMPT


def test_definition_accepts_runtime():
    definition = coder_tool.definition(lambda: None, DockerRuntime())
    assert definition.name == "coder.run"


@pytest.mark.skipif(
    sys.platform == "win32", reason="the stub docker is a POSIX sh script"
)
def test_stub_docker_executable(tmp_path, monkeypatch):
    monkeypatch.undo()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "log"
    stub = bin_dir / "docker"
    stub.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$1" >> "{log}"\n'
        f'if [ "$1" = run ]; then printf "%s\\n" "${TOKEN_NAME}" >> "{log}"; exit 7; fi\n'
        "exit 0\n"
    )
    stub.chmod(0o755)
    env = environ(PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("PATH", env["PATH"])
    runtime = DockerRuntime(environ=env)
    assert runtime.run(str(tmp_path), coder_model=MODEL) == 7
    assert log.read_text().splitlines() == ["run", TOKEN, "container"]
    assert coder_runtime.shutil.which("docker") == str(stub)


def test_the_prompt_speaks_of_the_base_and_the_plain_baseline():
    assert "feedback.base" in coder_runtime.PROMPT
    assert "single-threaded" in coder_runtime.PROMPT


def logs_in(directory):
    return sorted(Path(directory).iterdir())


def with_log(directory, **changes):
    return environ(**{coder_runtime.ENV_LOG_DIR: str(directory)}, **changes)


def test_log_dir_constants():
    assert coder_runtime.ENV_LOG_DIR == "HILCLAW_CODER_LOG_DIR"
    assert TOKEN.encode() not in coder_runtime.REDACTED
    assert coder_runtime.READ_SIZE > len(TOKEN)


@pytest.mark.parametrize("value", [None, ""])
def test_no_log_dir_keeps_nothing(popens, value):
    assert run(environ(**{coder_runtime.ENV_LOG_DIR: value})) == 0
    options = popens.calls[0][1]
    assert options["stdout"] is subprocess.DEVNULL
    assert options["stderr"] is subprocess.DEVNULL


def test_log_dir_keeps_the_output_with_the_token_replaced(starts, popens, tmp_path):
    popens.output = b"error: " + TOKEN.encode() + b" expired; again " + TOKEN.encode()
    popens.status = 1
    assert run(with_log(tmp_path)) == 1
    [(command, options)] = popens.calls
    assert options["stdin"] is subprocess.DEVNULL
    assert options["stdout"] is subprocess.PIPE
    assert options["stderr"] is subprocess.STDOUT
    assert popens.processes[0].stdout.closed
    [log] = logs_in(tmp_path)
    assert re.fullmatch(r"\d{8}T\d{6}Z-" + re.escape(command[3]) + r"\.log", log.name)
    assert log.read_bytes() == (
        b"error: "
        + coder_runtime.REDACTED
        + b" expired; again "
        + coder_runtime.REDACTED
    )
    if sys.platform != "win32":
        assert log.stat().st_mode & 0o777 == 0o600
    assert starts.calls == [
        (
            removal(command[3]),
            {"timeout_s": REMOVAL_TIMEOUT_S, "env": with_log(tmp_path)},
        )
    ]


@pytest.mark.parametrize("size", [1, 2, 3, 7, len(TOKEN) - 1, len(TOKEN), 64])
def test_a_token_split_across_reads_is_replaced(popens, tmp_path, size):
    popens.output = (
        b"a" + TOKEN.encode() + b"bc" + TOKEN.encode() + TOKEN.encode() + b"z"
    )
    popens.read_size = size
    run(with_log(tmp_path))
    [log] = logs_in(tmp_path)
    redacted = coder_runtime.REDACTED
    assert log.read_bytes() == b"a" + redacted + b"bc" + redacted + redacted + b"z"


def test_a_one_character_token_is_replaced(popens, tmp_path):
    popens.output = b"xQyQ"
    popens.read_size = 1
    run(with_log(tmp_path, **{ENV_TOKEN: "Q"}))
    [log] = logs_in(tmp_path)
    assert (
        log.read_bytes()
        == b"x" + coder_runtime.REDACTED + b"y" + coder_runtime.REDACTED
    )


def test_log_without_the_token_is_kept_as_written(popens, tmp_path):
    popens.output = b"plain output\n"
    run(with_log(tmp_path))
    [log] = logs_in(tmp_path)
    assert log.read_bytes() == b"plain output\n"


def test_each_call_gets_its_own_log(popens, tmp_path):
    run(with_log(tmp_path))
    run(with_log(tmp_path))
    assert len(logs_in(tmp_path)) == 2


@pytest.mark.parametrize("value", ["relative/dir", "missing", 7, "a\0b"])
def test_log_dir_refused_before_any_process(starts, popens, tmp_path, value):
    if value == "missing":
        value = str(tmp_path / "missing")
    with pytest.raises(CoderNotStartedError) as caught:
        run(environ(**{coder_runtime.ENV_LOG_DIR: value}))
    assert coder_runtime.ENV_LOG_DIR in str(caught.value)
    assert popens.calls == [] and starts.calls == []


@pytest.mark.parametrize("below", ["", "runs", "runs/r-1"])
def test_log_dir_at_or_below_the_data_root_is_refused(starts, popens, tmp_path, below):
    data = tmp_path / "data"
    (data / "runs" / "r-1").mkdir(parents=True)
    env = with_log(data / below if below else data, **{ENV_DATA: str(data)})
    with pytest.raises(CoderNotStartedError) as caught:
        run(env)
    assert "data root" in str(caught.value)
    assert (
        popens.calls == []
        and starts.calls == []
        and logs_in(data / "runs" / "r-1") == []
    )


def test_log_dir_beside_the_data_root_is_taken(popens, tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    beside = tmp_path / "data-logs"
    beside.mkdir()
    run(with_log(beside, **{ENV_DATA: str(data)}))
    assert len(logs_in(beside)) == 1


def test_log_that_cannot_be_made_is_not_started(starts, popens, tmp_path, monkeypatch):
    def refuse(*args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr(os, "open", refuse)
    with pytest.raises(CoderNotStartedError) as caught:
        run(with_log(tmp_path))
    assert "PermissionError" in str(caught.value)
    assert popens.calls == [] and starts.calls == []


def test_start_failure_closes_the_log(popens, tmp_path):
    popens.start_error = OSError("exec format error")
    with pytest.raises(CoderNotStartedError):
        run(with_log(tmp_path))
    [log] = logs_in(tmp_path)
    assert log.read_bytes() == b""


@pytest.mark.parametrize("status", sorted(NOT_STARTED_STATUSES))
def test_not_started_status_with_a_log_removes_and_redacts(
    starts, popens, tmp_path, status
):
    popens.output = b"docker: " + TOKEN.encode()
    popens.status = status
    with pytest.raises(CoderNotStartedError):
        run(with_log(tmp_path))
    name = popens.calls[0][0][3]
    assert [command for command, _ in starts.calls] == [removal(name)]
    [log] = logs_in(tmp_path)
    assert log.read_bytes() == b"docker: " + coder_runtime.REDACTED


def test_cut_off_wait_removes_and_never_wrote_the_token(starts, popens, tmp_path):
    popens.output = TOKEN.encode()
    popens.wait_error = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        run(with_log(tmp_path))
    name = popens.calls[0][0][3]
    assert [command for command, _ in starts.calls] == [removal(name)]
    assert popens.processes[0].killed == 1
    [log] = logs_in(tmp_path)
    assert log.read_bytes() == coder_runtime.REDACTED


def test_cut_off_read_removes_reaps_and_keeps_what_was_redacted(
    starts, popens, tmp_path
):
    popens.output = b"x" * 60 + TOKEN.encode()
    popens.read_size = 25
    popens.read_error_after = 3
    with pytest.raises(KeyboardInterrupt):
        run(with_log(tmp_path))
    name = popens.calls[0][0][3]
    assert [command for command, _ in starts.calls] == [removal(name)]
    assert popens.processes[0].killed == 1
    assert popens.processes[0].stdout.closed
    [log] = logs_in(tmp_path)
    assert TOKEN.encode()[:5] not in log.read_bytes()
    assert log.read_bytes() == b"x" * (75 - (len(TOKEN) - 1))


def test_a_failed_write_ends_the_log_not_the_call(
    starts, popens, tmp_path, monkeypatch
):
    popens.output = b"first part " + b"y" * 100
    popens.read_size = 8
    real_fdopen = os.fdopen

    class Full:
        def __init__(self, handle):
            self.handle = handle
            self.writes = 0

        def write(self, data):
            self.writes += 1
            if self.writes > 1:
                raise OSError("no space left")
            return self.handle.write(data)

        def flush(self):
            self.handle.flush()

        def close(self):
            self.handle.close()

    monkeypatch.setattr(os, "fdopen", lambda fd, mode: Full(real_fdopen(fd, mode)))
    popens.status = 3
    assert run(with_log(tmp_path, **{ENV_TOKEN: "Q"})) == 3
    assert popens.processes[0].stdout.drained
    [log] = logs_in(tmp_path)
    assert log.read_bytes() == b"first pa"


def test_log_dir_on_another_drive_than_the_data_root_is_taken(
    popens, tmp_path, monkeypatch
):
    def other_drive(paths):
        raise ValueError("Paths don't have the same drive")

    monkeypatch.setattr(os.path, "commonpath", other_drive)
    run(with_log(tmp_path, **{ENV_DATA: str(tmp_path / "data")}))
    assert len(logs_in(tmp_path)) == 1
