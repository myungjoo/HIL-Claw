import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import test_model_forward_container as container
from test_model_forward_container import (  # noqa: F401
    INSIDE,
    OPTIONS,
    client,
    ended,
    image,
    leftovers,
    mount_source,
    parent,
    raises,
    run_result,
    started,
    timed_out,
    user,
)
from test_model_gemm import SOURCES, bf16_matrices, clang, matrices  # noqa: F401

from hilclaw import (
    clang_build,
    local_run,
    model_build,
    model_container,
    model_execute,
    model_forward_container,
    model_run,
    standin_check,
    standin_container,
    standin_copies,
    standin_image,
)
from hilclaw.clang_build import BuildResult
from hilclaw.model_binding import KernelReference
from hilclaw.model_container import (
    PREFIX,
    ContainerRun,
    ModelContainerExecution,
    execute,
)
from hilclaw.model_execute import BuildFailed
from hilclaw.model_forward_container import (
    IMAGE_REFUSED,
    NO_CLIENT,
    NO_IMAGE,
    NO_NUMERIC_USER,
    RUNTIME_STATUS,
    Unavailable,
)
from hilclaw.model_run import END_MARK, RunFailed, encode_input, output_shapes

IMAGE = container.IMAGE
BUILD_TIMEOUT = 30
RUN_TIMEOUT = 7
PROGRAM_FLAGS = ("-O2",)
TRAILING_FLAGS = ("-ldl",)
KERNEL_FLAGS = ("-O1", "-march=x")
COUNT = 2
PROCESS = COUNT + 1


def calls_at(dtype):
    make = bf16_matrices if dtype == "bf16" else matrices
    return [(1, *make(2, 3, 4, 1)), (0, *make(1, 2, 5, 2))]


def report_at(dtype):
    element = np.uint16 if dtype == "bf16" else np.float32
    first = np.arange(8, dtype=element).reshape(2, 4)
    second = np.arange(10, 15, dtype=element).reshape(1, 5)
    return first.tobytes() + second.tobytes() + END_MARK


@pytest.fixture(autouse=True)
def fp32_report(client):  # noqa: F811
    client.report = report_at("fp32")


@pytest.fixture
def references(tmp_path):
    directory = tmp_path / "src"
    directory.mkdir()
    made = []
    for index in range(COUNT):
        source = directory / f"k{index}.c"
        source.write_bytes(f"/* k{index} */\n".encode())
        made.append(KernelReference((source,), None, KERNEL_FLAGS))
    return made


def run(parent, kernels, calls=None, **options):  # noqa: F811
    options.setdefault("dtype", "fp32")
    options.setdefault("build_timeout_s", BUILD_TIMEOUT)
    options.setdefault("run_timeout_s", RUN_TIMEOUT)
    options.setdefault("program_flags", PROGRAM_FLAGS)
    options.setdefault("program_trailing_flags", TRAILING_FLAGS)
    calls = calls if calls is not None else calls_at(options["dtype"])
    return execute(kernels, calls, parent=parent, **options)


def forbid_host(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("a host path was used")

    monkeypatch.setattr(clang_build, "build", refused)
    monkeypatch.setattr(model_run, "run_model_program", refused)


@pytest.mark.parametrize("dtype", ["fp32", "bf16"])
def test_happy_path_has_the_exact_command_lines_and_outputs(
    client,  # noqa: F811
    monkeypatch,
    parent,  # noqa: F811
    references,
    dtype,
):
    forbid_host(monkeypatch)
    client.report = report_at(dtype)
    result = run(parent, references, dtype=dtype)

    assert type(result) is ModelContainerExecution
    assert result._fields == ("unavailable", "build_failed", "run", "removed")
    assert result.unavailable is None and result.build_failed is None
    assert type(result.run) is ContainerRun
    assert result.run.failed is None
    expected = model_run.parse_report(
        report_at(dtype), output_shapes(calls_at(dtype), dtype=dtype), dtype=dtype
    )
    assert len(result.run.outputs) == 2
    for output, want in zip(result.run.outputs, expected, strict=True):
        assert output.dtype == want.dtype
        assert np.array_equal(output, want)
    assert result.run.container.stdout == b""
    assert result.run.container.stderr == b"said"
    assert type(result.run.container) is standin_container.ContainerResult
    assert result.removed is True
    assert leftovers(parent) == []
    assert client.removals() == []

    runs = client.runs()
    assert len(runs) == COUNT + 2
    directory = mount_source(runs[0])
    assert os.path.basename(directory).startswith(PREFIX)
    assert os.path.dirname(directory) == os.path.realpath(parent)
    names = set()
    for command, _, env, options in client.calls:
        assert command[:3] == ["docker", "run", "--rm"]
        assert command[3] == "--name"
        names.add(command[4])
        assert command[5:7] == [
            "--mount",
            f"type=bind,source={directory},target={INSIDE}",
        ]
        assert command[7:20] == OPTIONS
        assert command[20] == IMAGE
        assert env is None
        assert options == {}
    assert len(names) == len(runs)

    for index in range(COUNT):
        command, timeout_s, _, _ = client.calls[index]
        assert timeout_s == BUILD_TIMEOUT
        assert started(command)[1:] == (
            "clang",
            [
                *KERNEL_FLAGS,
                *model_build.LIBRARY_FLAGS,
                f"{INSIDE}/kernel-{index}/k{index}.c",
                "-o",
                f"{INSIDE}/kernel-{index}.so",
            ],
        )
    command, timeout_s, _, _ = client.calls[COUNT]
    assert timeout_s == BUILD_TIMEOUT
    assert started(command)[1:] == (
        "clang",
        [
            *PROGRAM_FLAGS,
            *model_build.PROGRAM_DTYPE_FLAGS[dtype],
            f"{INSIDE}/model_program.c",
            *TRAILING_FLAGS,
            "-o",
            f"{INSIDE}/model_program",
        ],
    )
    command, timeout_s, _, _ = client.calls[PROCESS]
    assert timeout_s == RUN_TIMEOUT
    assert started(command)[1:] == (
        f"{INSIDE}/model_program",
        [
            f"{INSIDE}/input.bin",
            f"{INSIDE}/kernel-0.so",
            f"{INSIDE}/kernel-1.so",
        ],
    )


@pytest.mark.parametrize("dtype", ["fp32", "bf16"])
def test_the_copies_and_the_input_lie_in_the_build_directory(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
    tmp_path,
    dtype,
):
    header = tmp_path / "src" / "own.h"
    header.write_bytes(b"#define OWN 1\n")
    kernels = [references[0]._replace(headers=(header,)), references[1]]
    client.report = report_at(dtype)
    calls = calls_at(dtype)
    result = run(parent, kernels, calls, dtype=dtype)
    assert result.run.failed is None
    assert client.seen == {
        "model_program.c": model_build.PROGRAM_SOURCE.read_bytes(),
        "model_program": b"\x7fELF",
        "input.bin": encode_input(calls, dtype=dtype),
        "kernel-0/k0.c": b"/* k0 */\n",
        "kernel-0/own.h": b"#define OWN 1\n",
        "kernel-1/k1.c": b"/* k1 */\n",
        "kernel-0.so": b"\x7fELF",
        "kernel-1.so": b"\x7fELF",
    }
    for command in client.runs():
        assert not any(argument.endswith(".h") for argument in command)


def test_the_input_is_written_after_the_last_build(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
):
    seen = []

    def program_build(command):
        seen.append(os.path.exists(os.path.join(mount_source(command), "input.bin")))
        return container.built(command)

    client.script[COUNT] = program_build
    result = run(parent, references)
    assert result.run.failed is None
    assert seen == [False]


def test_a_list_form_of_kernel_is_accepted(client, parent, tmp_path):  # noqa: F811
    source = tmp_path / "one.c"
    source.write_bytes(b"/* one */\n")
    kernels = [SimpleNamespace(sources=[source], flags=["-O1"], headers=[])]
    calls = [(0, *matrices(2, 3, 4, 1)), (0, *matrices(1, 2, 5, 2))]
    result = run(parent, kernels, calls)
    assert result.run.failed is None
    assert client.seen["kernel-0/one.c"] == b"/* one */\n"
    assert len(client.runs()) == 3


def test_the_environ_argument_names_the_image(
    client,  # noqa: F811
    monkeypatch,
    parent,  # noqa: F811
    references,
):
    monkeypatch.delenv(standin_image.ENV_IMAGE)
    other = "other.example/clang:1"
    result = run(parent, references, environ={standin_image.ENV_IMAGE: other})
    assert result.run.failed is None
    assert all(command[20] == other for command in client.runs())


def test_no_image_named_is_container_unavailable(
    client,  # noqa: F811
    monkeypatch,
    parent,  # noqa: F811
    references,
):
    monkeypatch.setenv(standin_image.ENV_IMAGE, "")
    result = run(parent, references)
    assert result == ModelContainerExecution(
        Unavailable(NO_IMAGE, None), None, None, None
    )
    assert client.calls == []
    assert leftovers(parent) == []


def test_a_refused_image_is_container_unavailable(
    client,  # noqa: F811
    monkeypatch,
    parent,  # noqa: F811
    references,
):
    monkeypatch.setenv(standin_image.ENV_IMAGE, "--privileged")
    result = run(parent, references)
    assert result.unavailable.reason == IMAGE_REFUSED
    assert type(result.unavailable.detail) is standin_image.ImageRefusedError
    assert result.removed is None
    assert client.calls == []
    assert leftovers(parent) == []


@pytest.mark.parametrize("at", [0, COUNT, PROCESS])
def test_a_client_not_found_is_container_unavailable(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
    at,
):
    error = local_run.ProgramNotFoundError("docker")
    client.script[at] = raises(error)
    result = run(parent, references)
    assert result.unavailable == Unavailable(NO_CLIENT, error)
    assert result.build_failed is None and result.run is None
    assert result.removed is True
    assert len(client.runs()) == at + 1
    assert leftovers(parent) == []


def test_no_numeric_user_is_container_unavailable(
    client,  # noqa: F811
    monkeypatch,
    parent,  # noqa: F811
    references,
):
    monkeypatch.delattr(os, "getuid", raising=False)
    result = run(parent, references)
    assert result.unavailable.reason == NO_NUMERIC_USER
    assert type(result.unavailable.detail) is standin_container.NoNumericUserError
    assert result.removed is True
    assert client.calls == []
    assert leftovers(parent) == []


@pytest.mark.parametrize("status", [125, 126, 127])
@pytest.mark.parametrize("at", [0, COUNT])
def test_a_runtime_status_of_a_build_is_container_unavailable(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
    status,
    at,
):
    client.script[at] = ended(status, stderr=b"docker: Error")
    result = run(parent, references)
    assert result.unavailable.reason == RUNTIME_STATUS
    assert result.unavailable.detail.returncode == status
    assert result.build_failed is None and result.run is None
    assert len(client.runs()) == at + 1
    assert result.removed is True


@pytest.mark.parametrize("status", [125, 126, 127])
def test_a_runtime_status_of_the_process_is_run_failed(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
    status,
):
    client.script[PROCESS] = ended(status, stdout=report_at("fp32"))
    result = run(parent, references)
    assert result.unavailable is None
    assert result.run.failed is RunFailed.EXIT_STATUS
    assert result.run.outputs is None
    assert result.run.container.returncode == status
    assert result.run.container.stdout == b""


def test_a_failing_kernel_build_stops_before_the_rest(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
):
    client.script[1] = ended(1, stdout=b"out \xff", stderr=b"error: x")
    result = run(parent, references)
    assert result.unavailable is None and result.run is None
    failed = result.build_failed
    assert type(failed) is BuildFailed
    assert failed.kernel == 1
    assert type(failed.build) is BuildResult
    assert failed.build.ok is False
    assert failed.build.returncode == 1
    assert failed.build.log == "out �error: x"
    assert failed.build.output == Path(mount_source(client.runs()[0])) / "kernel-1.so"
    assert failed.build.command == tuple(client.runs()[1])
    assert len(client.runs()) == 2
    assert result.removed is True
    assert leftovers(parent) == []


def test_a_failing_program_build_names_no_kernel_and_nothing_follows(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
):
    client.script[COUNT] = ended(2)
    result = run(parent, references)
    assert result.build_failed.kernel is None
    assert result.build_failed.build.returncode == 2
    assert result.build_failed.build.output.name == "model_program"
    assert len(client.runs()) == COUNT + 1
    assert result.run is None


@pytest.mark.parametrize("at", [0, COUNT])
def test_a_build_with_status_0_and_no_output_failed(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
    at,
):
    client.script[at] = ended(0, stdout=b"fine")
    result = run(parent, references)
    assert result.build_failed.kernel == (None if at == COUNT else at)
    assert result.build_failed.build.returncode == 0
    assert result.build_failed.build.ok is False
    assert result.build_failed.build.log == "fine"
    assert result.run is None
    assert len(client.runs()) == at + 1


def test_a_build_past_its_limit_is_removed_by_force(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
):
    client.script[0] = timed_out
    result = run(parent, references)
    assert result.build_failed.build.timed_out is True
    (removal,) = client.removals()
    assert removal[0] == ["docker", "rm", "--force", client.runs()[0][4]]
    assert removal[1] == standin_check.REMOVAL_TIMEOUT_S
    assert result.removed is True
    assert leftovers(parent) == []


@pytest.mark.parametrize(
    "removal",
    [ended(1), lambda command: run_result(command, timed_out=True)],
)
@pytest.mark.parametrize("at", [0, PROCESS])
def test_a_forced_removal_not_shown_to_succeed_keeps_the_directory(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
    removal,
    at,
):
    client.script[at] = timed_out
    client.removal = removal
    result = run(parent, references)
    assert result.removed is False
    (left,) = leftovers(parent)
    assert left.startswith(PREFIX)


def test_a_run_past_its_limit_is_run_failed(client, parent, references):  # noqa: F811
    client.script[PROCESS] = timed_out
    result = run(parent, references)
    assert result.run.failed is RunFailed.TIMEOUT
    assert result.run.outputs is None
    assert result.run.container.stdout == b""
    assert result.run.container.removal.returncode == 0
    assert len(client.removals()) == 1
    assert result.removed is True


def test_a_run_with_another_status_is_run_failed(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
):
    client.script[PROCESS] = ended(1, stdout=report_at("fp32"))
    result = run(parent, references)
    assert result.run.failed is RunFailed.EXIT_STATUS
    assert result.run.outputs is None


@pytest.mark.parametrize("cut", [1, 4])
def test_a_run_without_a_complete_report_is_run_failed(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
    cut,
):
    client.report = report_at("fp32")[:-cut]
    result = run(parent, references)
    assert result.run.failed is RunFailed.REPORT_FORM
    assert result.run.outputs is None
    assert result.removed is True


def test_an_os_error_of_the_client_passes_and_leaves_the_directory(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
):
    error = PermissionError("client not executable")
    client.script[PROCESS] = raises(error)
    with pytest.raises(PermissionError) as raised:
        run(parent, references)
    assert raised.value is error
    (left,) = leftovers(parent)
    assert left.startswith(PREFIX)


def test_a_request_to_end_passes_after_the_forced_removal(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
):
    client.script[1] = raises(KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        run(parent, references)
    assert len(client.removals()) == 1
    assert leftovers(parent) == []


def test_two_files_of_one_basename_raise_entry_exists(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
    tmp_path,
):
    other = tmp_path / "other"
    other.mkdir()
    (other / "k0.c").write_bytes(b"/* again */\n")
    kernels = [references[0]._replace(headers=(other / "k0.c",)), references[1]]
    with pytest.raises(standin_copies.CopyError) as raised:
        run(parent, kernels)
    assert raised.value.failure == standin_copies.ENTRY_EXISTS
    assert client.calls == []
    assert leftovers(parent) == []


def test_a_source_that_is_a_symbolic_link_is_refused_by_the_copy(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
    tmp_path,
):
    link = tmp_path / "src" / "link.c"
    try:
        link.symlink_to(references[0].sources[0])
    except OSError:
        pytest.skip("this system makes no symbolic link")
    kernels = [references[0]._replace(sources=(link,)), references[1]]
    with pytest.raises(standin_copies.CopyError) as raised:
        run(parent, kernels)
    assert raised.value.failure == standin_copies.KERNEL_FILE_CHANGED
    assert client.calls == []
    assert leftovers(parent) == []


def test_a_missing_source_raises_the_copy_error(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
):
    Path(references[1].sources[0]).unlink()
    with pytest.raises(standin_copies.CopyError) as raised:
        run(parent, references)
    assert raised.value.failure == standin_copies.KERNEL_FILE_UNREADABLE
    assert client.calls == []
    assert leftovers(parent) == []


def test_a_failed_input_encoding_passes_after_removal(
    client,  # noqa: F811
    monkeypatch,
    parent,  # noqa: F811
    references,
):
    def refused(*args, **kwargs):
        raise MemoryError("too big")

    monkeypatch.setattr(model_run, "encode_input", refused)
    with pytest.raises(MemoryError):
        run(parent, references)
    assert len(client.runs()) == COUNT + 1
    assert leftovers(parent) == []


def test_missing_parent_raises_the_os_error(client, tmp_path, references):  # noqa: F811
    with pytest.raises(OSError):
        run(tmp_path / "missing", references)
    assert client.calls == []


def test_parent_none_uses_the_system_temporary_directory(
    client,  # noqa: F811
    monkeypatch,
    parent,  # noqa: F811
    references,
):
    monkeypatch.setattr(model_execute.tempfile, "tempdir", str(parent))
    result = run(None, references)
    assert result.removed is True
    assert os.path.dirname(mount_source(client.runs()[0])) == os.path.realpath(parent)


def kernel_without(attribute, source):
    fields = {"sources": (source,), "flags": (), "headers": ()}
    del fields[attribute]
    return SimpleNamespace(**fields)


@pytest.mark.parametrize(
    ("change", "error", "text"),
    [
        ({"dtype": 1}, TypeError, "dtype"),
        ({"dtype": "fp16"}, ValueError, "dtype"),
        ({"kernels": "k.c"}, TypeError, "kernels"),
        ({"kernels": ()}, ValueError, "kernels"),
        ({"calls": ()}, ValueError, "calls"),
        ({"calls": "x"}, TypeError, "calls"),
        ({"keep_out": "/x"}, TypeError, "keep_out"),
        ({"keep_out": 1}, TypeError, "keep_out"),
        ({"parent": b"/tmp"}, TypeError, "parent"),
        ({"program_flags": "-O2"}, TypeError, "program_flags"),
        ({"program_flags": ("-O2", 2)}, TypeError, "program_flags"),
        (
            {"program_flags": ("-DHILCLAW_MODEL_BF16",)},
            ValueError,
            r"program_flags\[0\]",
        ),
        (
            {"program_flags": ("-O2", "-UHILCLAW_MODEL_BF16")},
            ValueError,
            r"program_flags\[1\]",
        ),
        ({"program_trailing_flags": "-ldl"}, TypeError, "program_trailing_flags"),
        ({"program_trailing_flags": [None]}, TypeError, "program_trailing_flags"),
        ({"build_timeout_s": None}, TypeError, "build_timeout_s"),
        ({"build_timeout_s": True}, TypeError, "build_timeout_s"),
        ({"build_timeout_s": "7"}, TypeError, "build_timeout_s"),
        ({"build_timeout_s": 0}, ValueError, "build_timeout_s"),
        ({"build_timeout_s": -1}, ValueError, "build_timeout_s"),
        ({"build_timeout_s": float("inf")}, ValueError, "build_timeout_s"),
        ({"build_timeout_s": float("nan")}, ValueError, "build_timeout_s"),
        ({"run_timeout_s": None}, TypeError, "run_timeout_s"),
        ({"run_timeout_s": 0}, ValueError, "run_timeout_s"),
        ({"run_timeout_s": -1}, ValueError, "run_timeout_s"),
        ({"run_timeout_s": float("inf")}, ValueError, "run_timeout_s"),
        ({"run_timeout_s": float("nan")}, ValueError, "run_timeout_s"),
        ({"environ": [("HILCLAW_STANDIN_IMAGE", IMAGE)]}, TypeError, "environ"),
    ],
)
def test_a_refused_argument_raises_before_anything_is_made(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
    change,
    error,
    text,
):
    change = dict(change)
    kernels = change.pop("kernels", references)
    where = change.pop("parent", parent)
    calls = change.pop("calls", None)
    with pytest.raises(error, match=text):
        if calls is None:
            run(where, kernels, **change)
        else:
            run(where, kernels, calls, **change)
    assert client.calls == []
    assert leftovers(parent) == []


@pytest.mark.parametrize("attribute", ["sources", "flags", "headers"])
def test_a_kernel_without_an_attribute_names_its_position(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
    attribute,
):
    kernels = [references[0], kernel_without(attribute, references[1].sources[0])]
    with pytest.raises(TypeError, match=rf"kernels\[1\].*{attribute}"):
        run(parent, kernels)
    assert client.calls == []
    assert leftovers(parent) == []


@pytest.mark.parametrize(
    ("change", "error", "text"),
    [
        ({"sources": "k.c"}, TypeError, "sources"),
        ({"flags": "-O2"}, TypeError, "flags"),
        ({"flags": ("-O2", 1)}, TypeError, "flags"),
        ({"headers": "k.h"}, TypeError, "headers"),
        ({"sources": ()}, ValueError, "no source"),
        ({"sources": (b"k.c",)}, TypeError, r"sources\[0\]"),
        ({"headers": (1,)}, TypeError, r"headers\[0\]"),
        ({"headers": ("k\0.h",)}, ValueError, r"headers\[0\]"),
    ],
)
def test_a_kernel_of_the_wrong_form_is_refused(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
    change,
    error,
    text,
):
    kernels = [references[0]._replace(**change), references[1]]
    with pytest.raises(error, match=rf"kernels\[0\].*{text}"):
        run(parent, kernels)
    assert client.calls == []
    assert leftovers(parent) == []


def test_a_call_index_too_large_is_refused(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
):
    calls = [(COUNT, *matrices(2, 3, 4, 1))]
    with pytest.raises(ValueError, match=r"calls\[0\].*not below"):
        run(parent, references, calls)
    assert client.calls == []
    assert leftovers(parent) == []


def test_arrays_of_the_wrong_dtype_are_refused(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
):
    with pytest.raises(ValueError, match=r"calls\[0\]"):
        run(parent, references, calls_at("fp32"), dtype="bf16")
    assert client.calls == []
    assert leftovers(parent) == []


def test_a_parent_inside_keep_out_is_refused(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
):
    with pytest.raises(ValueError, match="parent"):
        run(parent, references, keep_out=[parent])
    assert client.calls == []
    assert leftovers(parent) == []


def test_a_parent_inside_the_checkout_is_refused(client, references):  # noqa: F811
    inside = Path(model_container.__file__).parent
    with pytest.raises(ValueError, match="parent"):
        run(inside, references)
    assert client.calls == []


@pytest.mark.parametrize("name", ["compiler", "env", "prefix"])
def test_there_is_no_host_parameter(
    client,  # noqa: F811
    parent,  # noqa: F811
    references,
    name,
):
    with pytest.raises(TypeError, match=name):
        run(parent, references, **{name: None})
    assert client.calls == []


def test_public_names_and_fields():
    public = {name for name in vars(model_container) if not name.startswith("_")}
    imported = {
        "os",
        "tempfile",
        "NamedTuple",
        "BuildFailed",
        "Unavailable",
        "model_build",
        "model_run",
        "standin_check",
        "standin_container",
        "standin_copies",
    }
    assert public - imported == {
        "PREFIX",
        "ContainerRun",
        "ModelContainerExecution",
        "execute",
    }
    assert PREFIX == "hilclaw-model-container-"
    assert PREFIX not in (model_execute.PREFIX, model_forward_container.PREFIX)
    assert ContainerRun._fields == ("failed", "outputs", "container")
    assert model_container.Unavailable is model_forward_container.Unavailable
    assert model_container.BuildFailed is model_execute.BuildFailed


def real_kernels(directory, names):
    made = []
    for name in names:
        source = directory / f"{name}.c"
        source.write_text(SOURCES[name], encoding="ascii", newline="\n")
        made.append(KernelReference((source,), None, ("-O2",)))
    return made


@pytest.mark.parametrize(
    ("dtype", "names"),
    [("fp32", ("plain", "plus_one")), ("bf16", ("bf16_plain", "bf16_plus_one"))],
)
def test_outputs_through_a_stub_client_equal_the_host_path_bit_for_bit(
    clang,  # noqa: F811
    monkeypatch,
    tmp_path,
    dtype,
    names,
):
    calls = calls_at(dtype)
    kernels = real_kernels(tmp_path, names)
    limits = {"build_timeout_s": 120, "run_timeout_s": 60}
    flags = {"program_flags": ("-O2",), "program_trailing_flags": ("-ldl",)}
    monkeypatch.setattr(local_run, "run", container.HOST_RUN)
    host_parent = tmp_path / "host"
    host_parent.mkdir()
    host = model_execute.execute(
        kernels, calls, dtype=dtype, parent=host_parent, **limits, **flags
    )
    assert host.run.failed is None, host.run.run.stderr

    monkeypatch.setattr(
        local_run,
        "run",
        container.real_client(shutil.which("clang"), container.HOST_RUN),
    )
    builds = tmp_path / "builds"
    builds.mkdir()
    result = execute(kernels, calls, dtype=dtype, parent=builds, **limits, **flags)
    assert result.unavailable is None, result.unavailable
    assert result.build_failed is None, result.build_failed
    assert result.run.failed is None, result.run.container.stderr
    assert result.removed is True
    assert list(builds.iterdir()) == []
    for ours, theirs in zip(result.run.outputs, host.run.outputs, strict=True):
        assert ours.dtype == theirs.dtype
        assert ours.tobytes() == theirs.tobytes()
