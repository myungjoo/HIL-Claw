import functools
import os
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np
import pytest
import test_model_forward as forward
import test_model_graph_execute as graph_execute
import test_model_graph_program as program_tests

from hilclaw import (
    checkout_boundary,
    local_run,
    model_build,
    model_forward_container,
    model_graph,
    model_graph_container,
    model_graph_execute,
    standin_container,
    standin_image,
    standin_run,
    standin_settings,
    targets,
)
from hilclaw.model_binding import INVALID_INPUT, NO_KERNEL
from hilclaw.model_execute import BuildFailed
from hilclaw.model_forward_container import (
    IMAGE_REFUSED,
    NO_CLIENT,
    NO_IMAGE,
    RUNTIME_STATUS,
    ContainerRun,
    Unavailable,
)
from hilclaw.model_graph_container import (
    PREFIX,
    GraphContainerExecution,
    TimedContainerExecution,
    TimedContainerRun,
    TimedRunFailed,
    execute,
    execute_timed,
)
from hilclaw.model_run import RunFailed

IMAGE = "registry.example/hilclaw-clang:3"
HOST_RUN = local_run.run
S, G = graph_execute.S, graph_execute.G
KINDS = tuple(program_tests.LIBRARY_OF_KIND)
BUILDS = len(KINDS) + 1
WAITER_FLAGS = ("-std=gnu11", "-O2")
INSIDE = standin_container.CONTAINER_BUILD_DIR
WAITER = f"{INSIDE}/waiter"
PROGRAM = f"{INSIDE}/model_graph"
LINE = b"\nwaiter_max_rss_kib 2048\n"
NAMESPACE = ("--user", "--pid", "--fork", "--mount-proc", "--kill-child")


def run_result(command, returncode=0, *, timed_out=False, stdout=b"", stderr=b""):
    return local_run.RunResult(
        None if timed_out else returncode,
        timed_out,
        stdout,
        stderr,
        tuple(command),
        0.25,
        None,
    )


def mount_source(command):
    option = command[command.index("--mount") + 1]
    fields = dict(field.split("=", 1) for field in option.split(","))
    return fields["source"]


def started(command):
    position = command.index("--entrypoint=") + 1
    return command[position], command[position + 1], command[position + 2 :]


def on_host(command, path):
    return os.path.join(mount_source(command), path[len(INSIDE) + 1 :])


def built(command):
    _, _, arguments = started(command)
    output = arguments[arguments.index("-o") + 1]
    Path(on_host(command, output)).write_bytes(b"\x7fELF")
    return run_result(command, 0, stdout=b"compiled\n")


def ended(returncode, stdout=b"", stderr=b""):
    return lambda command: run_result(command, returncode, stdout=stdout, stderr=stderr)


def timed_out(command):
    return run_result(command, timed_out=True, stdout=b"part")


def raises(error):
    def act(command):
        raise error

    return act


class Client:
    def __init__(self):
        self.calls = []
        self.script = {}
        self.report = graph_execute.report_bytes()
        self.timed = [graph_execute.timed_bytes(100 * r) + LINE for r in range(1, 9)]
        self.seen = None

    def __call__(self, command, *, timeout_s, env=None, **options):
        command = list(command)
        self.calls.append((command, timeout_s, env, options))
        if command[1] == "rm":
            return run_result(command, 0)
        index = len(self.runs()) - 1
        act = self.script.get(index)
        if act is not None:
            return act(command)
        _, program, _ = started(command)
        if program == "clang":
            return built(command)
        self.seen = snapshot(mount_source(command))
        if program == WAITER:
            stdout = self.timed[len(self.processes()) - 1]
            return run_result(command, 0, stdout=stdout, stderr=b"said")
        return run_result(command, 0, stdout=self.report, stderr=b"said")

    def runs(self):
        return [call[0] for call in self.calls if call[0][1] == "run"]

    def processes(self):
        return [c for c in self.runs() if started(c)[1] != "clang"]

    def removals(self):
        return [call for call in self.calls if call[0][1] == "rm"]


def snapshot(directory):
    found = {}
    for root, _, files in os.walk(directory):
        for name in files:
            path = os.path.join(root, name)
            relative = os.path.relpath(path, directory).replace(os.sep, "/")
            found[relative] = Path(path).read_bytes()
    return found


@pytest.fixture(autouse=True)
def client(monkeypatch):
    stub = Client()
    monkeypatch.setattr(local_run, "run", stub)
    return stub


@pytest.fixture(autouse=True)
def user(monkeypatch, tmp_path):  # tmp_path first: pytest checks its owner uid
    monkeypatch.setattr(os, "getuid", lambda: 1234, raising=False)
    monkeypatch.setattr(os, "getgid", lambda: 567, raising=False)


@pytest.fixture(autouse=True)
def image(monkeypatch):
    monkeypatch.setenv(standin_image.ENV_IMAGE, IMAGE)


@pytest.fixture
def parent(tmp_path):
    if checkout_boundary.meets_checkout(
        os.path.realpath(tmp_path), [], containing=False
    ):
        pytest.skip("the temporary directory of pytest lies inside the repository")
    directory = tmp_path / "builds"
    directory.mkdir()
    return directory


@pytest.fixture
def stub_sources(tmp_path):
    directory = tmp_path / "src"
    directory.mkdir()
    names = {}
    for kind in KINDS:
        path = directory / f"{kind}.c"
        path.write_bytes(f"/* {kind} */\n".encode())
        names[kind] = str(path)
    return names


def leftovers(parent):
    return sorted(os.listdir(parent))


def untimed(parent, names, **options):
    arguments = graph_execute.inputs()
    for name in tuple(options):
        if name in arguments:
            arguments[name] = options.pop(name)
    options.setdefault("build_timeout_s", 30)
    options.setdefault("run_timeout_s", 7)
    options.setdefault("program_trailing_flags", ("-ldl",))
    return execute(
        options.pop("graph", program_tests.LLAMA),
        program_tests.LLAMA_DIMENSIONS,
        options.pop("binding", None) or graph_execute.binding_of(names, ("-O2",)),
        parent=parent,
        **arguments,
        **options,
    )


def timed(parent, names, **options):
    arguments = graph_execute.inputs()
    del arguments["given"], arguments["lm_head_rows"]
    for name in tuple(options):
        if name in arguments:
            arguments[name] = options.pop(name)
    options.setdefault("build_timeout_s", 30)
    options.setdefault("run_timeout_s", 7)
    options.setdefault("repetitions", 3)
    options.setdefault("waiter_flags", WAITER_FLAGS)
    options.setdefault("program_trailing_flags", ("-ldl",))
    return execute_timed(
        options.pop("graph", program_tests.LLAMA),
        program_tests.LLAMA_DIMENSIONS,
        options.pop("binding", None) or graph_execute.binding_of(names, ("-O2",)),
        parent=parent,
        **arguments,
        **options,
    )


def kernel_order(check):
    order = []
    for kernel in model_graph.libraries(check):
        order.append(Path(kernel.sources[0]).stem)
    return order


def test_untimed_happy_path_builds_and_runs_in_containers(client, parent, stub_sources):
    result = untimed(parent, stub_sources)
    assert type(result) is GraphContainerExecution
    assert result.check.ok
    assert (result.unavailable, result.build_failed) == (None, None)
    assert type(result.run) is ContainerRun
    assert result.run.failed is None
    expected = [int(t) for t in graph_execute.inputs()["prompt"]]
    expected += graph_execute.inputs()["given"]
    assert [int(t) for t in result.run.report.tokens] == expected
    assert result.run.container.stdout == b""
    assert result.run.container.stderr == b"said"
    assert result.removed is True
    assert leftovers(parent) == []

    runs = client.runs()
    assert len(runs) == BUILDS + 1
    directory = mount_source(runs[0])
    assert os.path.basename(directory).startswith(PREFIX)
    for command, _, env, options in client.calls:
        assert command[:3] == ["docker", "run", "--rm"]
        assert IMAGE in command
        assert env is None and options == {}
    order = kernel_order(result.check)
    assert sorted(order) == sorted(KINDS)
    for index, kind in enumerate(order):
        command, timeout_s, _, _ = client.calls[index]
        assert timeout_s == 30
        assert started(command)[1:] == (
            "clang",
            [
                "-O2",
                *model_build.LIBRARY_FLAGS,
                f"{INSIDE}/kernel-{index}/{kind}.c",
                "-o",
                f"{INSIDE}/kernel-{index}.so",
            ],
        )
    assert started(runs[len(KINDS)])[1:] == (
        "clang",
        [f"{INSIDE}/model_graph.c", "-ldl", "-o", PROGRAM],
    )
    command, timeout_s, _, _ = client.calls[-1]
    assert timeout_s == 7
    assert started(command)[1:] == (
        PROGRAM,
        [
            f"{INSIDE}/input.bin",
            *(f"{INSIDE}/kernel-{i}.so" for i in range(len(KINDS))),
        ],
    )
    seen = client.seen
    assert seen["model_graph.c"] == model_build.GRAPH_PROGRAM_SOURCE.read_bytes()
    assert "timing_waiter.c" not in seen and "waiter" not in seen
    plan = result.plan
    arguments = graph_execute.inputs()
    del arguments["generation_length"], arguments["lm_head_rows"]
    assert seen["input.bin"] == model_graph.encode(plan, result.check, **arguments)


def test_untimed_generation_mode_reads_a_generation_report(
    client, parent, stub_sources
):
    tokens = graph_execute.inputs()["prompt"] + [1, 2, 3]
    logits = np.ones((G, forward.V), np.uint16)
    client.report = forward.generated_report(np.array(tokens, np.uint64), S, logits)
    result = untimed(parent, stub_sources, given=None, lm_head_rows="last")
    assert result.run.failed is None
    assert [int(t) for t in result.run.report.tokens] == tokens
    assert np.array_equal(result.run.report.logits, logits)


@pytest.mark.parametrize(
    ("act", "failed"),
    [
        (timed_out, RunFailed.TIMEOUT),
        (ended(1, stdout=b"x"), RunFailed.EXIT_STATUS),
        (ended(126), RunFailed.EXIT_STATUS),
        (ended(0, stdout=b"short"), RunFailed.REPORT_FORM),
    ],
)
def test_untimed_run_failed(client, parent, stub_sources, act, failed):
    client.script[BUILDS] = act
    result = untimed(parent, stub_sources)
    assert result.run.failed is failed
    assert result.run.report is None
    assert result.run.container.stdout == b""
    assert result.removed is True
    assert leftovers(parent) == []


def test_untimed_check_that_is_not_ok_starts_nothing(
    client, monkeypatch, parent, stub_sources
):
    monkeypatch.delenv(standin_image.ENV_IMAGE)
    binding = graph_execute.binding_of(stub_sources)
    del binding["lm_head"]
    result = untimed(parent, stub_sources, binding=binding)
    assert not result.check.ok
    assert {o.kind for o in result.check.outcomes} == {NO_KERNEL}
    assert result[2:] == (None, None, None, None)
    assert client.calls == []
    assert leftovers(parent) == []


def test_untimed_invalid_input_starts_nothing(client, parent, stub_sources):
    result = untimed(parent, stub_sources, prompt=[0, 1, forward.V])
    assert result.check.outcomes[0].kind == INVALID_INPUT
    assert result.check.outcomes[0].reason.startswith("prompt: token id")
    assert client.calls == []


@pytest.mark.parametrize("run", [untimed, timed])
def test_no_image_named_is_container_unavailable(
    client, monkeypatch, parent, stub_sources, run
):
    monkeypatch.setenv(standin_image.ENV_IMAGE, "")
    result = run(parent, stub_sources)
    assert result.check.ok
    assert result.unavailable == Unavailable(NO_IMAGE, None)
    assert all(value is None for value in result[3:])
    assert client.calls == []
    assert leftovers(parent) == []


@pytest.mark.parametrize("run", [untimed, timed])
def test_a_refused_image_is_container_unavailable(
    client, monkeypatch, parent, stub_sources, run
):
    monkeypatch.setenv(standin_image.ENV_IMAGE, "--privileged")
    result = run(parent, stub_sources)
    assert result.unavailable.reason == IMAGE_REFUSED
    assert type(result.unavailable.detail) is standin_image.ImageRefusedError
    assert all(value is None for value in result[3:])
    assert client.calls == []


def test_the_environ_argument_names_the_image(
    client, monkeypatch, parent, stub_sources
):
    monkeypatch.delenv(standin_image.ENV_IMAGE)
    other = "other.example/clang:9"
    result = timed(parent, stub_sources, environ={standin_image.ENV_IMAGE: other})
    assert result.failed is None
    assert all(other in command for command in client.runs())


def waiter_line(value):
    return f"\nwaiter_max_rss_kib {value}\n".encode()


@pytest.mark.parametrize("repetitions", [1, 3])
def test_timed_runs_are_new_waiter_containers(
    client, parent, stub_sources, repetitions
):
    client.timed = [
        graph_execute.timed_bytes(100 * r) + waiter_line(1000 + r)
        for r in range(1, repetitions + 1)
    ]
    result = timed(parent, stub_sources, repetitions=repetitions)
    assert type(result) is TimedContainerExecution
    assert result.check.ok
    assert (result.unavailable, result.build_failed, result.failed) == (
        None,
        None,
        None,
    )
    assert result.removed is True
    assert leftovers(parent) == []
    assert len(result.runs) == repetitions
    for r, one in enumerate(result.runs, 1):
        assert type(one) is TimedContainerRun
        assert one.failed is None
        assert one.report.intervals == (10,) * G
        assert one.report.readings[0] == 100 * r
        assert one.report.resolution == 1
        assert one.memory_bytes == (1000 + r) * 1024
        assert one.container.stdout == b""
    runs = client.runs()
    assert len(runs) == BUILDS + 1 + repetitions
    assert started(runs[BUILDS])[1:] == (
        "clang",
        [*WAITER_FLAGS, f"{INSIDE}/timing_waiter.c", "-o", WAITER],
    )
    names = set()
    for command in runs[BUILDS + 1 :]:
        names.add(command[4])
        assert started(command)[1:] == (
            WAITER,
            [
                PROGRAM,
                f"{INSIDE}/input.bin",
                *(f"{INSIDE}/kernel-{i}.so" for i in range(len(KINDS))),
            ],
        )
    assert len(names) == repetitions
    for _, timeout_s, _, _ in client.calls[BUILDS + 1 :]:
        assert timeout_s == 7
    seen = client.seen
    assert seen["timing_waiter.c"] == standin_run.WAITER_SOURCE.read_bytes()
    words = np.frombuffer(seen["input.bin"][:64], np.uint64)
    assert int(words[5]) == 2


@pytest.mark.parametrize(
    "line",
    [
        waiter_line(0),
        waiter_line(-4),
        b"\nwaiter_max_rss none\n",
    ],
)
def test_a_waiter_value_that_is_not_positive_is_no_figure(
    client, parent, stub_sources, line
):
    client.timed = [graph_execute.timed_bytes() + line]
    result = timed(parent, stub_sources, repetitions=1)
    (one,) = result.runs
    assert one.failed is None
    assert one.memory_bytes is None


@pytest.mark.parametrize(
    ("act", "failed"),
    [
        (timed_out, TimedRunFailed.TIMEOUT),
        (
            ended(1, stdout=graph_execute.timed_bytes() + LINE),
            TimedRunFailed.EXIT_STATUS,
        ),
        (ended(4), TimedRunFailed.EXIT_STATUS),
        (ended(125, stderr=b"docker: Error"), TimedRunFailed.EXIT_STATUS),
        (ended(126), TimedRunFailed.EXIT_STATUS),
        (ended(127), TimedRunFailed.EXIT_STATUS),
        (ended(0, stdout=graph_execute.timed_bytes()), TimedRunFailed.WAITER_LINE),
        (ended(0, stdout=b""), TimedRunFailed.WAITER_LINE),
        (ended(0, stdout=b"short" + LINE), TimedRunFailed.REPORT_FORM),
        (
            ended(0, stdout=graph_execute.timed_bytes(step=0) + LINE),
            TimedRunFailed.NOT_INCREASING,
        ),
    ],
)
@pytest.mark.parametrize("at", [0, 1])
def test_the_first_failed_timed_run_ends_with_no_figures(
    client, parent, stub_sources, act, failed, at
):
    client.script[BUILDS + 1 + at] = act
    result = timed(parent, stub_sources, repetitions=3)
    assert result.runs is None
    assert type(result.failed) is TimedContainerRun
    assert result.failed.failed is failed
    assert (result.failed.report, result.failed.memory_bytes) == (None, None)
    assert result.failed.container.stdout == b""
    assert len(client.processes()) == at + 1
    assert result.removed is True
    assert leftovers(parent) == []


@pytest.mark.parametrize("status", [125, 126, 127])
@pytest.mark.parametrize("at", [0, len(KINDS), BUILDS])
def test_a_runtime_status_of_a_build_container_is_container_unavailable(
    client, parent, stub_sources, status, at
):
    client.script[at] = ended(status)
    result = timed(parent, stub_sources)
    assert result.unavailable.reason == RUNTIME_STATUS
    assert result.unavailable.detail.returncode == status
    assert (result.build_failed, result.runs, result.failed) == (None, None, None)
    assert len(client.runs()) == at + 1
    assert result.removed is True
    assert leftovers(parent) == []


@pytest.mark.parametrize("at", [0, len(KINDS)])
def test_a_runtime_status_of_an_untimed_build_is_container_unavailable(
    client, parent, stub_sources, at
):
    client.script[at] = ended(125)
    result = untimed(parent, stub_sources)
    assert result.unavailable.reason == RUNTIME_STATUS
    assert (result.build_failed, result.run) == (None, None)
    assert len(client.runs()) == at + 1
    assert result.removed is True
    assert leftovers(parent) == []


@pytest.mark.parametrize("run", [untimed, timed])
def test_a_failed_kernel_build_ends_with_no_figures(client, parent, stub_sources, run):
    client.script[2] = ended(1, stderr=b"error: x")
    result = run(parent, stub_sources)
    assert type(result.build_failed) is BuildFailed
    assert result.build_failed.kernel == 2
    assert result.build_failed.build.log == "error: x"
    assert result.build_failed.build.output.name == "kernel-2.so"
    assert all(value is None for value in result[4:-1])
    assert len(client.runs()) == 3
    assert result.removed is True
    assert leftovers(parent) == []


@pytest.mark.parametrize(
    ("at", "name"), [(len(KINDS), "model_graph"), (BUILDS, "waiter")]
)
def test_a_failed_program_or_waiter_build_names_no_kernel(
    client, parent, stub_sources, at, name
):
    client.script[at] = ended(0)
    result = timed(parent, stub_sources)
    assert result.build_failed.kernel is None
    assert result.build_failed.build.output.name == name
    assert result.runs is None and result.failed is None
    assert client.processes() == []
    assert leftovers(parent) == []


def test_a_timed_out_build_is_removed_by_force(client, parent, stub_sources):
    client.script[BUILDS] = timed_out
    result = timed(parent, stub_sources)
    assert result.build_failed.build.timed_out
    assert len(client.removals()) == 1
    assert result.removed is True


@pytest.mark.parametrize("at", [0, BUILDS + 2])
def test_a_client_not_found_is_container_unavailable(client, parent, stub_sources, at):
    error = local_run.ProgramNotFoundError("docker")
    client.script[at] = raises(error)
    result = timed(parent, stub_sources)
    assert result.unavailable == Unavailable(NO_CLIENT, error)
    assert result.runs is None and result.failed is None
    assert result.removed is True
    assert leftovers(parent) == []


@pytest.mark.parametrize("run", [untimed, timed])
def test_what_a_container_raises_passes_after_removal(
    client, parent, stub_sources, run
):
    client.script[BUILDS + 1] = raises(KeyboardInterrupt())
    client.script[len(KINDS) + 1] = raises(KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        run(parent, stub_sources)
    assert leftovers(parent) == []


@pytest.mark.parametrize("repetitions", [0, 2, 4, -1, 1.0, True, "3", None])
def test_repetitions_are_refused_before_anything_is_made(
    client, monkeypatch, parent, stub_sources, repetitions, tmp_path
):
    monkeypatch.delenv(standin_image.ENV_IMAGE)
    error = TypeError if type(repetitions) is not int else ValueError
    with pytest.raises(error) as raised:
        timed(
            parent,
            stub_sources,
            repetitions=repetitions,
            graph=tmp_path / "no-such-graph.json",
        )
    assert raised.value.parameter == "repetitions"
    assert client.calls == []
    assert leftovers(parent) == []


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ({"waiter_flags": "-O2"}, TypeError),
        ({"waiter_flags": None}, TypeError),
        ({"waiter_flags": (1,)}, TypeError),
        ({"program_trailing_flags": "-ldl"}, TypeError),
        ({"program_flags": [3]}, TypeError),
        ({"build_timeout_s": 0}, ValueError),
        ({"run_timeout_s": "7"}, TypeError),
        ({"environ": ["x"]}, TypeError),
        ({"keep_out": "x"}, TypeError),
    ],
)
def test_refused_arguments_whatever_the_check(
    client, parent, stub_sources, change, error
):
    binding = graph_execute.binding_of(stub_sources)
    del binding["lm_head"]
    for binding_value in (None, binding):
        with pytest.raises(error):
            timed(parent, stub_sources, binding=binding_value, **change)
    assert client.calls == []
    assert leftovers(parent) == []


def test_untimed_refuses_bad_arguments(client, parent, stub_sources):
    with pytest.raises(ValueError):
        untimed(parent, stub_sources, run_timeout_s=-1)
    with pytest.raises(TypeError):
        untimed(parent, stub_sources, environ=3)
    assert client.calls == []


def test_timed_check_that_is_not_ok_starts_nothing(
    client, monkeypatch, parent, stub_sources
):
    monkeypatch.delenv(standin_image.ENV_IMAGE)
    graph = program_tests.LLAMA
    result = timed(parent, stub_sources, prompt=[0, 1, forward.V], graph=graph)
    assert result.check.outcomes[0].kind == INVALID_INPUT
    assert result[2:] == (None, None, None, None, None)
    assert client.calls == []


def test_public_names_and_fields():
    public = {name for name in vars(model_graph_container) if not name.startswith("_")}
    imported = {
        "enum",
        "os",
        "tempfile",
        "NamedTuple",
        "BuildFailed",
        "ContainerRun",
        "Unavailable",
        "model_binding",
        "model_build",
        "model_graph",
        "model_run",
        "standin_check",
        "standin_container",
        "standin_copies",
        "standin_run",
        "standin_waiter_line",
    }
    assert public - imported == {
        "PREFIX",
        "TimedRunFailed",
        "GraphContainerExecution",
        "TimedContainerRun",
        "TimedContainerExecution",
        "execute",
        "execute_timed",
    }
    assert PREFIX == "hilclaw-graph-container-"
    assert PREFIX not in (model_graph_execute.PREFIX, model_forward_container.PREFIX)
    assert [m.name for m in TimedRunFailed] == [
        "TIMEOUT",
        "EXIT_STATUS",
        "WAITER_LINE",
        "REPORT_FORM",
        "NOT_INCREASING",
    ]
    assert GraphContainerExecution._fields == (
        "plan",
        "check",
        "unavailable",
        "build_failed",
        "run",
        "removed",
    )
    assert TimedContainerRun._fields == (
        "failed",
        "report",
        "memory_bytes",
        "container",
    )
    assert TimedContainerExecution._fields == (
        "plan",
        "check",
        "unavailable",
        "build_failed",
        "runs",
        "failed",
        "removed",
    )


@functools.cache
def pid_namespace():
    unshare = shutil.which("unshare")
    if unshare is None:
        return None
    command = [unshare, *NAMESPACE]
    probe = [*command, "/bin/sh", "-c", 'test "$$" -eq 1']
    try:
        done = subprocess.run(probe, capture_output=True, timeout=10, check=False)
    except OSError:
        return None
    return command if done.returncode == 0 else None


def real_client(clang_program):
    def act(command, *, timeout_s, env=None, **options):
        command = list(command)
        if command[0] != "docker":
            return HOST_RUN(command, timeout_s=timeout_s, env=env, **options)
        if command[1] == "rm":
            return run_result(command, 0)
        source = mount_source(command)
        _, program, arguments = started(command)

        def mapped(value):
            if value == INSIDE or value.startswith(INSIDE + "/"):
                return source + value[len(INSIDE) :]
            return value

        line = b""
        if program == "clang":
            argv = [clang_program, *(mapped(a) for a in arguments)]
        elif program == WAITER and pid_namespace() is not None:
            argv = [*pid_namespace(), mapped(program), *(mapped(a) for a in arguments)]
        elif program == WAITER:
            argv = [mapped(a) for a in arguments]
            line = LINE
        else:
            argv = [mapped(program), *(mapped(a) for a in arguments)]
        begun = time.monotonic()
        done = subprocess.run(
            argv, cwd=source, capture_output=True, timeout=timeout_s, check=False
        )
        status = done.returncode
        if line:
            status = 0 if status == 0 else 1
        return local_run.RunResult(
            status,
            False,
            done.stdout + line,
            done.stderr,
            tuple(command),
            time.monotonic() - begun,
            None,
        )

    return act


@pytest.fixture(scope="module")
def real_sources(tmp_path_factory):
    if os.name != "posix":
        pytest.skip("the graph program needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    directory = tmp_path_factory.mktemp("graph-container-sources")
    names = {}
    for kind, short in program_tests.LIBRARY_OF_KIND.items():
        path = directory / f"{short}.c"
        path.write_text(forward.PRELUDE + forward.KERNEL_SOURCES[short])
        names[kind] = str(path)
    return names


REAL = {"build_timeout_s": 120, "run_timeout_s": 60}


@pytest.mark.parametrize("given", [True, False])
def test_clang_untimed_report_equals_the_host_path(
    monkeypatch, parent, real_sources, given
):
    monkeypatch.setattr(local_run, "run", real_client(shutil.which("clang")))
    binding = graph_execute.binding_of(real_sources, forward.KERNEL_FLAGS)
    arguments = graph_execute.inputs(**({} if given else {"given": None}))
    ours = execute(
        program_tests.LLAMA,
        program_tests.LLAMA_DIMENSIONS,
        binding,
        parent=parent,
        program_trailing_flags=("-ldl",),
        **arguments,
        **REAL,
    )
    assert ours.run.failed is None, ours.run.container.stderr
    assert ours.removed and leftovers(parent) == []
    monkeypatch.setattr(local_run, "run", HOST_RUN)
    host = model_graph_execute.execute(
        program_tests.LLAMA,
        program_tests.LLAMA_DIMENSIONS,
        binding,
        parent=parent,
        program_trailing_flags=("-ldl",),
        **arguments,
        **REAL,
    )
    assert host.run.failed is None
    assert np.array_equal(ours.run.report.tokens, host.run.report.tokens)
    assert np.array_equal(ours.run.report.logits, host.run.report.logits)


@pytest.mark.parametrize("repetitions", [1, 3])
def test_clang_timed_runs_under_the_waiter(
    monkeypatch, parent, real_sources, repetitions
):
    monkeypatch.setattr(local_run, "run", real_client(shutil.which("clang")))
    binding = graph_execute.binding_of(real_sources, forward.KERNEL_FLAGS)
    arguments = graph_execute.inputs(given=None, lm_head_rows="last")
    untimed_run = execute(
        program_tests.LLAMA,
        program_tests.LLAMA_DIMENSIONS,
        binding,
        parent=parent,
        program_trailing_flags=("-ldl",),
        **arguments,
        **REAL,
    )
    assert untimed_run.run.failed is None, untimed_run.run.container.stderr
    del arguments["given"], arguments["lm_head_rows"]
    waiter_flags = targets.target(targets.CPU_STANDIN).waiter_flags
    assert waiter_flags == standin_settings.WAITER_FLAGS
    result = execute_timed(
        program_tests.LLAMA,
        program_tests.LLAMA_DIMENSIONS,
        binding,
        parent=parent,
        repetitions=repetitions,
        waiter_flags=waiter_flags,
        program_trailing_flags=("-ldl",),
        **arguments,
        **REAL,
    )
    assert result.failed is None, result.failed
    assert result.removed and leftovers(parent) == []
    assert len(result.runs) == repetitions
    tokens = tuple(int(t) for t in untimed_run.run.report.tokens)
    for one in result.runs:
        assert one.report.prompt + one.report.tokens == tokens
        assert len(one.report.intervals) == G
        assert one.report.increasing
        assert one.memory_bytes > 0 and one.memory_bytes % 1024 == 0


def test_clang_waiter_outside_process_1_ends_with_exit_status(
    monkeypatch, parent, real_sources
):
    def outside(clang_program):
        inner = real_client(clang_program)

        def act(command, *, timeout_s, env=None, **options):
            command = list(command)
            if command[1] == "run" and started(command)[1] == WAITER:
                source = mount_source(command)
                _, program, arguments = started(command)
                argv = [
                    source + value[len(INSIDE) :] for value in (program, *arguments)
                ]
                done = subprocess.run(
                    argv,
                    cwd=source,
                    capture_output=True,
                    timeout=timeout_s,
                    check=False,
                )
                return run_result(command, done.returncode, stdout=done.stdout)
            return inner(command, timeout_s=timeout_s, env=env, **options)

        return act

    monkeypatch.setattr(local_run, "run", outside(shutil.which("clang")))
    result = timed(
        parent,
        real_sources,
        binding=graph_execute.binding_of(real_sources, forward.KERNEL_FLAGS),
        repetitions=3,
        waiter_flags=standin_settings.WAITER_FLAGS,
        **REAL,
    )
    assert result.failed.failed is TimedRunFailed.EXIT_STATUS
    assert result.failed.container.returncode == 3
    assert result.runs is None
    assert leftovers(parent) == []
