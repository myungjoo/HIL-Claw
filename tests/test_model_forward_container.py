import os
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np
import pytest
import test_attempt_kernel as attempts
import test_model_forward as forward
import test_model_forward_execute as forward_execute
import test_model_forward_run as forward_run
import test_model_reference as reference
from test_model_reference import clang  # noqa: F401

from hilclaw import (
    checkout_boundary,
    local_run,
    model_build,
    model_execute,
    model_forward_check,
    model_forward_container,
    model_forward_execute,
    model_forward_run,
    standin_check,
    standin_container,
    standin_copies,
    standin_image,
)
from hilclaw.clang_build import BuildResult
from hilclaw.model_binding import KernelReference
from hilclaw.model_execute import BuildFailed
from hilclaw.model_forward_container import (
    IMAGE_REFUSED,
    NO_CLIENT,
    NO_IMAGE,
    NO_NUMERIC_USER,
    PREFIX,
    REASONS,
    RUNTIME_STATUS,
    ContainerRun,
    ForwardContainerExecution,
    Unavailable,
    execute,
)
from hilclaw.model_forward_run import CALL_SITES, encode_input
from hilclaw.model_reference import compare, reference_logits
from hilclaw.model_run import RunFailed

IMAGE = "registry.example/hilclaw-clang:2"
DIMENSIONS = forward_run.DIMENSIONS
S, G = 3, 3
KINDS = forward.KINDS
BUILD_TIMEOUT = 30
RUN_TIMEOUT = 7
PROGRAM_FLAGS = ("-O2",)
TRAILING_FLAGS = ("-ldl",)
INSIDE = standin_container.CONTAINER_BUILD_DIR
OPTIONS = [
    "--workdir",
    INSIDE,
    "--network",
    "none",
    "--pull",
    "never",
    "--user",
    "1234:567",
    "--cap-drop",
    "ALL",
    "--security-opt",
    "no-new-privileges=true",
    "--entrypoint=",
]


def run_result(command, returncode=0, *, timed_out=False, stdout=b"", stderr=b""):
    return local_run.RunResult(
        returncode=None if timed_out else returncode,
        timed_out=timed_out,
        stdout=stdout,
        stderr=stderr,
        command=tuple(command),
        duration_s=0.25,
        max_rss=None,
    )


def mount_source(command):
    option = command[command.index("--mount") + 1]
    fields = dict(field.split("=", 1) for field in option.split(","))
    assert fields["type"] == "bind"
    assert fields["target"] == INSIDE
    return fields["source"]


def started(command):
    position = command.index("--entrypoint=") + 1
    return command[position], command[position + 1], command[position + 2 :]


def on_host(command, path):
    assert path.startswith(INSIDE + "/")
    return os.path.join(mount_source(command), path[len(INSIDE) + 1 :])


def model_of():
    return forward_run.model_of(41, prompt=S, given=G)


def good_report(model):
    rows = S + G - 1
    logits = np.arange(rows * forward.V, dtype=np.uint16).reshape(rows, forward.V)
    return forward.report(model, logits)


def built(command, stdout=b"compiled\n", stderr=b"warning\n"):
    _, _, arguments = started(command)
    output = arguments[arguments.index("-o") + 1]
    Path(on_host(command, output)).write_bytes(b"\x7fELF")
    return run_result(command, 0, stdout=stdout, stderr=stderr)


def ended(returncode, stdout=b"", stderr=b""):
    return lambda command: run_result(command, returncode, stdout=stdout, stderr=stderr)


def timed_out(command):
    return run_result(command, timed_out=True, stdout=b"part", stderr=b"ial")


def raises(error):
    def act(command):
        raise error

    return act


class Client:
    def __init__(self):
        self.calls = []
        self.script = {}
        self.removal = ended(0)
        self.report = good_report(model_of())
        self.seen = None

    def __call__(self, command, *, timeout_s, env=None, **options):
        command = list(command)
        self.calls.append((command, timeout_s, env, options))
        if command[1] == "rm":
            return self.removal(command)
        index = len(self.runs()) - 1
        act = self.script.get(index)
        if act is not None:
            return act(command)
        _, program, _ = started(command)
        if program == "clang":
            return built(command)
        self.seen = snapshot(mount_source(command))
        return run_result(command, 0, stdout=self.report, stderr=b"said")

    def runs(self):
        return [call[0] for call in self.calls if call[0][1] == "run"]

    def removals(self):
        return [call for call in self.calls if call[0][1] == "rm"]


def snapshot(directory):
    found = {}
    for root, _, files in os.walk(directory):
        for name in files:
            path = os.path.join(root, name)
            found[os.path.relpath(path, directory).replace(os.sep, "/")] = Path(
                path
            ).read_bytes()
    return found


@pytest.fixture(autouse=True)
def client(monkeypatch):
    stub = Client()
    monkeypatch.setattr(local_run, "run", stub)
    return stub


@pytest.fixture(autouse=True)
def user(monkeypatch):
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


def kernel_order(check):
    order = []
    for _, _, kernel in check.calls:
        kind = Path(kernel.sources[0]).stem
        if kind not in order:
            order.append(kind)
    return order


@pytest.fixture
def sources(tmp_path):
    directory = tmp_path / "src"
    directory.mkdir()
    for kind in KINDS:
        (directory / f"{kind}.c").write_bytes(f"/* {kind} */\n".encode())
    return directory


def binding_in(directory, flags=forward.KERNEL_FLAGS):
    return forward_execute.binding_of(
        {
            kind: KernelReference(
                (directory / f"{kind}.c",), forward_execute.CONTRACTS[kind], flags
            )
            for kind in KINDS
        }
    )


def run(parent, binding, model=None, **options):
    model = model if model is not None else model_of()
    arguments = forward_execute.model_arguments(model)
    for name in tuple(options):
        if name in arguments:
            arguments[name] = options.pop(name)
    options.setdefault("build_timeout_s", BUILD_TIMEOUT)
    options.setdefault("run_timeout_s", RUN_TIMEOUT)
    options.setdefault("program_flags", PROGRAM_FLAGS)
    options.setdefault("program_trailing_flags", TRAILING_FLAGS)
    return execute(DIMENSIONS, binding, parent=parent, **arguments, **options)


def leftovers(parent):
    return sorted(os.listdir(parent))


def test_happy_path_builds_each_kernel_and_the_program_and_runs_once_in_containers(
    client, parent, sources
):
    model = model_of()
    result = run(parent, binding_in(sources), model)

    assert type(result) is ForwardContainerExecution
    assert result.check == forward_execute.expected_check(binding_in(sources), model)
    assert result.unavailable is None
    assert result.build_failed is None
    assert type(result.run) is ContainerRun
    assert result.run.failed is None
    assert np.array_equal(result.run.report.tokens, model["tokens"])
    assert result.run.container.stdout == b""
    assert result.run.container.stderr == b"said"
    assert result.removed is True
    assert leftovers(parent) == []
    assert client.removals() == []

    runs = client.runs()
    assert len(runs) == len(KINDS) + 2
    directory = mount_source(runs[0])
    assert os.path.basename(directory).startswith(PREFIX)
    assert os.path.dirname(directory) == os.path.realpath(parent)
    names = set()
    for command, timeout_s, env, options in client.calls:
        assert command[:3] == ["docker", "run", "--rm"]
        assert command[3] == "--name"
        assert command[4].startswith(standin_container.NAME_PREFIX)
        names.add(command[4])
        assert command[5:7] == [
            "--mount",
            f"type=bind,source={directory},target={INSIDE}",
        ]
        assert command[7:20] == OPTIONS
        assert command[20] == IMAGE
        assert env is None
        assert options == {}
        assert mount_source(command) == directory
    assert len(names) == len(runs)

    order = kernel_order(result.check)
    assert sorted(order) == sorted(KINDS)
    for index, kind in enumerate(order):
        command, timeout_s, _, _ = client.calls[index]
        assert timeout_s == BUILD_TIMEOUT
        assert started(command)[1:] == (
            "clang",
            [
                *forward.KERNEL_FLAGS,
                *model_build.LIBRARY_FLAGS,
                f"{INSIDE}/kernel-{index}/{kind}.c",
                "-o",
                f"{INSIDE}/kernel-{index}.so",
            ],
        )
    command, timeout_s, _, _ = client.calls[len(KINDS)]
    assert timeout_s == BUILD_TIMEOUT
    assert started(command)[1:] == (
        "clang",
        [
            *PROGRAM_FLAGS,
            f"{INSIDE}/model_forward.c",
            *TRAILING_FLAGS,
            "-o",
            f"{INSIDE}/model_forward",
        ],
    )
    command, timeout_s, _, _ = client.calls[-1]
    assert timeout_s == RUN_TIMEOUT
    assert started(command)[1:] == (
        f"{INSIDE}/model_forward",
        [
            f"{INSIDE}/input.bin",
            *(f"{INSIDE}/kernel-{index}.so" for index in range(len(KINDS))),
        ],
    )


def test_the_copies_and_the_input_lie_in_the_build_directory(client, parent, sources):
    model = model_of()
    result = run(parent, binding_in(sources), model)
    order = kernel_order(result.check)
    seen = client.seen
    expected = {
        "model_forward.c": model_build.FORWARD_PROGRAM_SOURCE.read_bytes(),
        "model_forward": b"\x7fELF",
        "input.bin": None,
    }
    for index, kind in enumerate(order):
        expected[f"kernel-{index}/{kind}.c"] = f"/* {kind} */\n".encode()
        expected[f"kernel-{index}.so"] = b"\x7fELF"
    assert set(seen) == set(expected)
    for name, data in expected.items():
        if data is not None:
            assert seen[name] == data
    tables = {
        site: [order.index(forward_execute.KIND_OF[site])] * G for site in CALL_SITES
    }
    assert seen["input.bin"] == encode_input(
        DIMENSIONS,
        **forward_execute.model_arguments(model),
        libraries=tables,
        library_count=len(KINDS),
    )


@pytest.mark.parametrize("last", [False, True])
def test_the_generation_mode_reads_a_generation_report(client, parent, sources, last):
    model = model_of()
    rows = "last" if last else "all"
    count = G if last else S + G - 1
    logits = np.ones((count, forward.V), dtype=np.uint16)
    client.report = forward.generated_report(model["tokens"], S, logits)
    result = run(parent, binding_in(sources), model, given=None, lm_head_rows=rows)
    assert result.run.failed is None
    assert np.array_equal(result.run.report.tokens, model["tokens"])
    assert np.array_equal(result.run.report.logits, logits)


def test_equal_kernels_are_built_once(client, parent, sources):
    binding = binding_in(sources)
    run(parent, binding)
    assert len(client.runs()) == len(KINDS) + 2


def test_the_environ_argument_names_the_image(client, monkeypatch, parent, sources):
    monkeypatch.delenv(standin_image.ENV_IMAGE)
    other = "other.example/clang@sha256:" + "a" * 64
    result = run(parent, binding_in(sources), environ={standin_image.ENV_IMAGE: other})
    assert result.run.failed is None
    assert all(command[20] == other for command in client.runs())


@pytest.mark.parametrize(
    "change",
    [
        {"prompt": [0, forward.V, 1]},
        {"weights": None},
    ],
)
def test_a_check_that_is_not_ok_reads_makes_and_starts_nothing(
    client, monkeypatch, parent, sources, change
):
    monkeypatch.delenv(standin_image.ENV_IMAGE)
    model = model_of()
    if "weights" in change:
        weights = forward_run.weights_of(model)
        change = {"weights": weights._replace(norm=weights.norm[:-1])}
    result = run(parent, binding_in(sources), model, **change)
    assert not result.check.ok
    assert result == ForwardContainerExecution(result.check, None, None, None, None)
    assert client.calls == []
    assert leftovers(parent) == []


def test_no_kernel_starts_nothing(client, parent, sources):
    binding = binding_in(sources)
    del binding["lm_head"]
    result = run(parent, binding)
    assert not result.check.ok
    assert result.removed is None
    assert client.calls == []


def test_no_image_named_is_container_unavailable(client, monkeypatch, parent, sources):
    monkeypatch.setenv(standin_image.ENV_IMAGE, "")
    result = run(parent, binding_in(sources))
    assert result.check.ok
    assert result.unavailable == Unavailable(NO_IMAGE, None)
    assert (result.build_failed, result.run, result.removed) == (None, None, None)
    assert client.calls == []
    assert leftovers(parent) == []


def test_a_refused_image_is_container_unavailable(client, monkeypatch, parent, sources):
    monkeypatch.setenv(standin_image.ENV_IMAGE, "--privileged")
    result = run(parent, binding_in(sources))
    assert result.unavailable.reason == IMAGE_REFUSED
    assert type(result.unavailable.detail) is standin_image.ImageRefusedError
    assert "--privileged" not in str(result.unavailable.detail)
    assert result.removed is None
    assert client.calls == []
    assert leftovers(parent) == []


@pytest.mark.parametrize("at", [0, len(KINDS) + 1])
def test_a_client_not_found_is_container_unavailable(client, parent, sources, at):
    error = local_run.ProgramNotFoundError("docker")
    client.script[at] = raises(error)
    result = run(parent, binding_in(sources))
    assert result.unavailable == Unavailable(NO_CLIENT, error)
    assert result.build_failed is None and result.run is None
    assert result.removed is True
    assert len(client.runs()) == at + 1
    assert client.removals() == []
    assert leftovers(parent) == []


def test_no_numeric_user_is_container_unavailable(client, monkeypatch, parent, sources):
    monkeypatch.delattr(os, "getuid", raising=False)
    result = run(parent, binding_in(sources))
    assert result.unavailable.reason == NO_NUMERIC_USER
    assert type(result.unavailable.detail) is standin_container.NoNumericUserError
    assert result.removed is True
    assert client.calls == []
    assert leftovers(parent) == []


@pytest.mark.parametrize("status", [125, 126, 127])
@pytest.mark.parametrize("at", [0, 2, len(KINDS)])
def test_a_runtime_status_of_a_build_container_is_container_unavailable(
    client, parent, sources, status, at
):
    client.script[at] = ended(status, stderr=b"docker: Error response from daemon")
    result = run(parent, binding_in(sources))
    assert result.unavailable.reason == RUNTIME_STATUS
    container = result.unavailable.detail
    assert type(container) is standin_container.ContainerResult
    assert container.returncode == status
    assert result.build_failed is None and result.run is None
    assert len(client.runs()) == at + 1
    assert result.removed is True


@pytest.mark.parametrize("at", [0, 3])
def test_a_failed_kernel_build_stops_before_the_rest(client, parent, sources, at):
    client.script[at] = ended(1, stdout=b"out \xff", stderr=b"error: x")
    result = run(parent, binding_in(sources))
    assert result.unavailable is None and result.run is None
    failed = result.build_failed
    assert type(failed) is BuildFailed
    assert failed.kernel == at
    build = failed.build
    assert type(build) is BuildResult
    assert build.ok is False
    assert build.returncode == 1
    assert build.timed_out is False
    assert build.log == "out �error: x"
    assert build.output == Path(mount_source(client.runs()[0])) / f"kernel-{at}.so"
    assert build.command == tuple(client.runs()[at])
    assert build.duration_s == 0.25
    assert len(client.runs()) == at + 1
    assert result.removed is True
    assert leftovers(parent) == []


def test_a_failed_program_build_names_no_kernel(client, parent, sources):
    client.script[len(KINDS)] = ended(2)
    result = run(parent, binding_in(sources))
    assert result.build_failed.kernel is None
    assert result.build_failed.build.returncode == 2
    assert result.build_failed.build.output.name == "model_forward"
    assert len(client.runs()) == len(KINDS) + 1


@pytest.mark.parametrize("at", [1, len(KINDS)])
def test_a_build_that_leaves_no_output_failed(client, parent, sources, at):
    client.script[at] = ended(0, stdout=b"fine")
    result = run(parent, binding_in(sources))
    failed = result.build_failed
    assert failed.kernel == (None if at == len(KINDS) else at)
    assert failed.build.returncode == 0
    assert failed.build.ok is False
    assert failed.build.log == "fine"
    assert result.run is None


def test_a_build_past_its_limit_is_removed_by_force(client, parent, sources):
    client.script[0] = timed_out
    result = run(parent, binding_in(sources))
    build = result.build_failed.build
    assert build.timed_out is True
    assert build.returncode is None
    assert build.log == "partial"
    (removal,) = client.removals()
    name = client.runs()[0][4]
    assert removal[0] == ["docker", "rm", "--force", name]
    assert removal[1] == standin_check.REMOVAL_TIMEOUT_S == 60
    assert result.removed is True
    assert leftovers(parent) == []


@pytest.mark.parametrize(
    "removal",
    [ended(1), lambda command: run_result(command, timed_out=True)],
)
def test_a_forced_removal_not_shown_to_succeed_leaves_the_directory(
    client, parent, sources, removal
):
    client.script[0] = timed_out
    client.removal = removal
    result = run(parent, binding_in(sources))
    assert result.build_failed.build.timed_out
    assert result.removed is False
    (left,) = leftovers(parent)
    assert left.startswith(PREFIX)


def test_a_run_past_its_limit_is_run_failed(client, parent, sources):
    client.script[len(KINDS) + 1] = timed_out
    result = run(parent, binding_in(sources))
    assert result.run.failed is RunFailed.TIMEOUT
    assert result.run.report is None
    assert result.run.container.stdout == b""
    assert result.run.container.removal.returncode == 0
    assert len(client.removals()) == 1
    assert result.removed is True


@pytest.mark.parametrize("status", [1, -9, 125, 126, 127])
def test_a_run_with_another_status_is_run_failed(client, parent, sources, status):
    client.script[len(KINDS) + 1] = ended(status, stdout=good_report(model_of()))
    result = run(parent, binding_in(sources))
    assert result.unavailable is None
    assert result.run.failed is RunFailed.EXIT_STATUS
    assert result.run.container.returncode == status
    assert result.run.container.stdout == b""
    assert result.removed is True


@pytest.mark.parametrize("cut", [1, 4])
def test_a_run_without_a_complete_report_is_run_failed(client, parent, sources, cut):
    client.report = good_report(model_of())[:-cut]
    result = run(parent, binding_in(sources))
    assert result.run.failed is RunFailed.REPORT_FORM
    assert result.run.report is None


def test_an_os_error_of_the_client_passes_and_leaves_the_directory(
    client, parent, sources
):
    error = PermissionError("client not executable")
    client.script[len(KINDS) + 1] = raises(error)
    with pytest.raises(PermissionError) as raised:
        run(parent, binding_in(sources))
    assert raised.value is error
    (left,) = leftovers(parent)
    assert left.startswith(PREFIX)


def test_a_request_to_end_passes_after_the_forced_removal(client, parent, sources):
    client.script[1] = raises(KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt) as raised:
        run(parent, binding_in(sources))
    assert raised.value.container_name == client.runs()[1][4]
    assert len(client.removals()) == 1
    assert leftovers(parent) == []


def test_a_missing_kernel_source_raises_the_copy_error_and_starts_nothing(
    client, parent, sources
):
    (sources / "rope.c").unlink()
    with pytest.raises(standin_copies.CopyError) as raised:
        run(parent, binding_in(sources))
    assert raised.value.failure == standin_copies.KERNEL_FILE_UNREADABLE
    assert client.calls == []
    assert leftovers(parent) == []


def test_two_sources_of_one_name_raise_entry_exists(client, parent, sources):
    other = sources / "other"
    other.mkdir()
    (other / "gemm.c").write_bytes(b"/* again */\n")
    kernels = {
        kind: KernelReference(
            (sources / f"{kind}.c",),
            forward_execute.CONTRACTS[kind],
            forward.KERNEL_FLAGS,
        )
        for kind in KINDS
    }
    kernels["gemm"] = kernels["gemm"]._replace(
        sources=(sources / "gemm.c", other / "gemm.c")
    )
    with pytest.raises(standin_copies.CopyError) as raised:
        run(parent, forward_execute.binding_of(kernels))
    assert raised.value.failure == standin_copies.ENTRY_EXISTS
    assert client.calls == []
    assert leftovers(parent) == []


def test_a_kernel_with_several_sources_is_built_from_all_of_them(
    client, parent, sources
):
    (sources / "helper.c").write_bytes(b"int helper;\n")
    kernels = {
        kind: KernelReference(
            (sources / f"{kind}.c",),
            forward_execute.CONTRACTS[kind],
            (),
        )
        for kind in KINDS
    }
    kernels["gemm"] = kernels["gemm"]._replace(
        sources=(sources / "gemm.c", sources / "helper.c")
    )
    result = run(parent, forward_execute.binding_of(kernels))
    assert result.run.failed is None
    assert started(client.runs()[0])[2] == [
        *model_build.LIBRARY_FLAGS,
        f"{INSIDE}/kernel-0/gemm.c",
        f"{INSIDE}/kernel-0/helper.c",
        "-o",
        f"{INSIDE}/kernel-0.so",
    ]
    assert client.seen["kernel-0/helper.c"] == b"int helper;\n"


def test_a_failed_input_encoding_passes_after_removal(
    client, monkeypatch, parent, sources
):
    def refused(*args, **kwargs):
        raise MemoryError("too big")

    monkeypatch.setattr(model_forward_run, "encode_input", refused)
    with pytest.raises(MemoryError):
        run(parent, binding_in(sources))
    assert len(client.runs()) == len(KINDS) + 1
    assert leftovers(parent) == []


def test_a_failed_removal_of_the_directory_is_reported_and_raises_nothing(
    client, monkeypatch, parent, sources
):
    monkeypatch.setattr(model_forward_container, "_remove", lambda *args: False)
    result = run(parent, binding_in(sources))
    assert result.run.failed is None
    assert result.removed is False


def test_parent_none_uses_the_system_temporary_directory(
    client, monkeypatch, parent, sources
):
    monkeypatch.setattr(model_execute.tempfile, "tempdir", str(parent))
    monkeypatch.setattr(model_forward_container.tempfile, "tempdir", str(parent))
    result = run(None, binding_in(sources))
    assert result.removed is True
    assert os.path.dirname(mount_source(client.runs()[0])) == os.path.realpath(parent)


@pytest.mark.parametrize(
    ("options", "error", "text"),
    [
        ({"program_flags": "-O2"}, TypeError, "program_flags"),
        ({"program_flags": ("-O2", 2)}, TypeError, "program_flags"),
        ({"program_trailing_flags": "-ldl"}, TypeError, "program_trailing_flags"),
        ({"program_trailing_flags": [None]}, TypeError, "program_trailing_flags"),
        ({"build_timeout_s": None}, TypeError, "build_timeout_s"),
        ({"build_timeout_s": True}, TypeError, "build_timeout_s"),
        ({"build_timeout_s": 0}, ValueError, "build_timeout_s"),
        ({"build_timeout_s": float("inf")}, ValueError, "build_timeout_s"),
        ({"run_timeout_s": "7"}, TypeError, "run_timeout_s"),
        ({"run_timeout_s": -1}, ValueError, "run_timeout_s"),
        ({"run_timeout_s": float("nan")}, ValueError, "run_timeout_s"),
        ({"environ": [("HILCLAW_STANDIN_IMAGE", IMAGE)]}, TypeError, "environ"),
        ({"keep_out": "/x"}, TypeError, "keep_out"),
        ({"parent": b"/tmp"}, TypeError, "parent"),
    ],
)
@pytest.mark.parametrize("ok", [True, False])
def test_refused_arguments_whatever_the_check(
    client, parent, sources, options, error, text, ok
):
    binding = binding_in(sources)
    if not ok:
        del binding["qkv"]
    if "parent" in options:
        options = dict(options)
        parent = options.pop("parent")
    with pytest.raises(error, match=text):
        run(parent, binding, **options)
    assert client.calls == []
    if isinstance(parent, Path):
        assert leftovers(parent) == []


def test_a_parent_inside_keep_out_is_refused(client, parent, sources):
    with pytest.raises(ValueError, match="parent"):
        run(parent, binding_in(sources), keep_out=[parent])
    assert client.calls == []


def test_what_the_check_raises_comes_first(client, parent, sources):
    with pytest.raises(TypeError) as expected:
        model_forward_check.check(
            DIMENSIONS,
            binding_in(sources),
            dtype="bf16",
            **forward_execute.model_arguments(model_of(), eps=1),
        )
    with pytest.raises(TypeError) as raised:
        run(parent, binding_in(sources), eps=1, build_timeout_s=None)
    assert str(raised.value) == str(expected.value)


def test_missing_parent_raises_the_os_error(client, tmp_path, sources):
    with pytest.raises(OSError):
        run(tmp_path / "missing", binding_in(sources))
    assert client.calls == []


def test_public_names_and_fields():
    public = {
        name for name in vars(model_forward_container) if not name.startswith("_")
    }
    imported = {
        "os",
        "tempfile",
        "Mapping",
        "Path",
        "NamedTuple",
        "BuildFailed",
        "clang_build",
        "local_run",
        "model_binding",
        "model_build",
        "model_forward_check",
        "model_forward_run",
        "model_run",
        "standin_answer",
        "standin_check",
        "standin_container",
        "standin_copies",
        "standin_image",
    }
    assert public - imported == {
        "PREFIX",
        "NO_IMAGE",
        "IMAGE_REFUSED",
        "NO_CLIENT",
        "NO_NUMERIC_USER",
        "RUNTIME_STATUS",
        "REASONS",
        "Unavailable",
        "ContainerRun",
        "ForwardContainerExecution",
        "execute",
    }
    assert PREFIX == "hilclaw-forward-container-"
    assert PREFIX not in (model_execute.PREFIX, model_forward_execute.PREFIX)
    assert REASONS == (
        "no_image",
        "image_refused",
        "no_client",
        "no_numeric_user",
        "runtime_status",
    )
    assert Unavailable._fields == ("reason", "detail")
    assert ContainerRun._fields == ("failed", "report", "container")
    assert ForwardContainerExecution._fields == (
        "check",
        "unavailable",
        "build_failed",
        "run",
        "removed",
    )
    assert model_forward_container.BuildFailed is model_execute.BuildFailed


def real_client(clang_program):
    def act(command, *, timeout_s, env=None, **options):
        command = list(command)
        if command[1] == "rm":
            return run_result(command, 0)
        source = mount_source(command)
        _, program, arguments = started(command)

        def mapped(value):
            if value == INSIDE or value.startswith(INSIDE + "/"):
                return source + value[len(INSIDE) :]
            return value

        start = clang_program if program == "clang" else mapped(program)
        begun = time.monotonic()
        done = subprocess.run(
            [start, *(mapped(argument) for argument in arguments)],
            cwd=source,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
        return local_run.RunResult(
            done.returncode,
            False,
            done.stdout,
            done.stderr,
            tuple(command),
            time.monotonic() - begun,
            None,
        )

    return act


@pytest.mark.parametrize("last", [False, True])
def test_a_greedy_generation_from_attempts_through_a_stub_client(
    clang,  # noqa: F811
    monkeypatch,
    tmp_path,
    last,
):
    monkeypatch.setattr(local_run, "run", real_client(shutil.which("clang")))
    root = tmp_path / "data"
    root.mkdir()
    attempts.write_forward_attempts(root)
    binding = attempts.attempt_binding(root)
    seed, prompt, passes = 73, 3, 3
    model = reference.sharp_model(seed, prompt, passes)
    rows = "last" if last else "all"
    builds = tmp_path / "builds"
    builds.mkdir()
    result = execute(
        reference.DIMENSIONS,
        binding,
        **reference.arguments(model, lm_head_rows=rows, given=None),
        generation_length=model["G"],
        build_timeout_s=forward.BUILD_TIMEOUT,
        run_timeout_s=forward.RUN_TIMEOUT,
        program_flags=("-O2",),
        program_trailing_flags=("-ldl",),
        parent=builds,
    )
    assert result.check.ok, result.check.outcomes
    assert result.unavailable is None, result.unavailable
    assert result.build_failed is None, result.build_failed
    assert result.run.failed is None, result.run.container.stderr
    assert result.removed is True
    assert list(builds.iterdir()) == []
    report = result.run.report
    selected = [int(token) for token in report.tokens[prompt:]]
    assert len(set(selected)) > 1
    expected = reference_logits(
        reference.DIMENSIONS,
        **reference.arguments(model, given=selected, lm_head_rows=rows),
    )
    rtol, atol = reference.tolerance(expected)
    assert compare(report, expected, rtol=rtol, atol=atol).ok
    host = tmp_path / "host"
    host.mkdir()
    by_hand = reference.executed(host, model, rows, given=None)
    assert np.array_equal(report.tokens, by_hand.tokens)
    assert np.array_equal(report.logits, by_hand.logits)
