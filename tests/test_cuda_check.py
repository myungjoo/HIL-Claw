import dataclasses
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

from hilclaw import (
    backends,
    build_log,
    check_definition,
    check_failure,
    check_operation,
    clang_build,
    cuda_adapter,
    cuda_check,
    cuda_run,
    targets,
    tools,
    vendor_adapter,
)
from hilclaw.check_parameters import Bf16CheckParameters, CheckParameters
from hilclaw.harness import cuda_programs
from hilclaw.keys import SCHEMA_VERSION
from hilclaw.vendor_adapter import PRESENT

FIXTURES = Path(__file__).resolve().parent / "cuda_fixtures"
TOOL = "correctness.check"
PARAMETERS = CheckParameters(seed=987654321, draws=2, m=5, k=33, n=7)
TOLERANCE = {"rtol": 1e-4, "atol": 1e-4}
REPORT = "a report of the stub program\n"
LIMIT = 300
posix_only = pytest.mark.skipif(os.name != "posix", reason="stub programs are POSIX")

STUB = """#!{python}
import json, os, pathlib, sys, time
here = pathlib.Path(__file__).resolve().parent
name = pathlib.Path(sys.argv[0]).name
with open(here / "calls.ndjson", "a", encoding="utf-8") as log:
    log.write(json.dumps([name, *sys.argv[1:]]) + "\\n")
conf = json.loads((here / (name + ".json")).read_text(encoding="utf-8"))
sys.stdout.write(conf.get("stdout", ""))
sys.stderr.write(conf.get("stderr", ""))
sys.stdout.flush()
if "program" in conf:
    out = pathlib.Path(sys.argv[sys.argv.index("-o") + 1])
    out.write_text(conf["program"].format(python=sys.executable, here=here))
    out.chmod(conf.get("mode", 0o755))
time.sleep(conf.get("sleep", 0))
sys.exit(conf.get("status", 0))
"""

PROGRAM = """#!{python}
import json, pathlib, sys, time
here = pathlib.Path("{here}")
with open(here / "calls.ndjson", "a", encoding="utf-8") as log:
    log.write(json.dumps(["program", *sys.argv]) + "\\n")
time.sleep(%(sleep)s)
sys.stdout.write(%(stdout)r)
sys.exit(%(status)s)
"""


def program(stdout=REPORT, status=0, sleep=0):
    return PROGRAM % {"stdout": stdout, "status": status, "sleep": sleep}


class Stubs:
    def __init__(self, directory):
        self.directory = directory

    def set(self, name, **conf):
        path = self.directory / name
        path.write_text(STUB.format(python=sys.executable), encoding="utf-8")
        path.chmod(0o755)
        (self.directory / f"{name}.json").write_text(json.dumps(conf), encoding="utf-8")

    def remove(self, name):
        (self.directory / name).unlink()

    def calls(self):
        log = self.directory / "calls.ndjson"
        if not log.exists():
            return []
        return [
            json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()
        ]

    def names(self):
        return [call[0] for call in self.calls()]


@pytest.fixture
def stubs(tmp_path, monkeypatch):
    directory = tmp_path / "bin"
    directory.mkdir()
    monkeypatch.setenv("PATH", str(directory))
    found = Stubs(directory)
    found.set("nvidia-smi", stdout="Stub GPU, 1.0\n")
    found.set("nvcc", program=program())
    return found


@pytest.fixture
def build_root(tmp_path, monkeypatch):
    root = tmp_path / "temporary"
    root.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(root))
    return root


@pytest.fixture
def kernel(tmp_path):
    path = tmp_path / "output" / "kernel.cu"
    path.parent.mkdir()
    path.write_text("// a kernel\n", encoding="utf-8")
    return path


def the_target(**changes):
    return dataclasses.replace(targets.target(targets.CUDA_GPU), **changes)


def operation(kernel, target=None, **kwargs):
    selection = kwargs.pop("sources", lambda output_path: (kernel,))
    return cuda_check.operation_for(
        the_target() if target is None else target, sources=selection
    )


def call(op, parameters=PARAMETERS, keeper=None, output_path="output-path"):
    keeper = build_log.LogKeeper() if keeper is None else keeper
    return op("request", "hw_profile", parameters, output_path, keeper)


def failure_of(op, kind, **kwargs):
    with pytest.raises(tools.ToolFailure) as raised:
        call(op, **kwargs)
    assert raised.value.kind == kind
    return raised.value


# The module


def test_the_public_names_of_the_module():
    public = {name for name in vars(cuda_check) if not name.startswith("_")}
    imported = {
        "os",
        "stat",
        "build_log",
        "check_build",
        "check_failure",
        "check_parameters",
        "clang_build",
        "cuda_adapter",
        "standin_check",
        "standin_settings",
        "targets",
        "tools",
        "vendor_adapter",
        "cuda_programs",
    }
    assert public - imported == {
        "DEVICE_QUERY_TIMEOUT_S",
        "EXECUTABLE_NAME",
        "BUILD_DIR_PREFIX",
        "operation_for",
        "check_target",
        "check_sources",
        "check_keeper",
        "confirm_device",
        "select_sources",
        "build_executable",
        "carry_out",
    }


def test_the_module_reads_no_attempt_file_name():
    assert not {"kernel_source", "attempt_kernel"} & set(vars(cuda_check))
    assert "HQ-0104" in cuda_check.__doc__
    assert "test-only" in cuda_check.__doc__


def test_the_default_table_has_no_cuda_gpu_entry():
    table = check_definition.default_table()
    assert targets.CUDA_GPU not in table.names()
    record = {
        "schema_version": SCHEMA_VERSION,
        "accelerator": targets.CUDA_GPU,
        "revision": "Example GPU sm_89",
        "toolchain": {"nvcc": "x", "gcc": "y", "nvidia_driver": "1"},
        "host": {"cpu": "c", "os": "o"},
        "hw_source": "external",
    }
    for tool in backends.HW_TOOLS:
        with pytest.raises(tools.ToolFailure) as raised:
            backends.select(table, record, tool)
        assert raised.value.kind == tools.KIND_NO_BACKEND


# operation_for


def test_operation_for_refuses_a_target_that_is_no_target(kernel):
    with pytest.raises(TypeError, match="target must be a Target"):
        cuda_check.operation_for("cuda_gpu", sources=lambda path: (kernel,))


@pytest.mark.parametrize("sources", [None, (), "kernel.cu"])
def test_operation_for_refuses_a_selection_that_is_not_callable(sources):
    with pytest.raises(TypeError, match="sources must be a callable"):
        cuda_check.operation_for(the_target(), sources=sources)


def test_operation_for_needs_the_selection_by_name():
    with pytest.raises(TypeError):
        cuda_check.operation_for(the_target())
    with pytest.raises(TypeError):
        cuda_check.operation_for(the_target(), lambda path: ())


def test_check_target_check_sources_and_check_keeper_pass_good_values():
    assert cuda_check.check_target(the_target()) is None
    assert cuda_check.check_sources(len) is None
    assert cuda_check.check_keeper(build_log.LogKeeper()) is None
    with pytest.raises(TypeError, match="keeper must be a LogKeeper"):
        cuda_check.check_keeper(object())


@posix_only
@pytest.mark.parametrize(
    ("parameters", "keeper", "error"),
    [
        (Bf16CheckParameters(1, 1, "gemm", "bf16", {}), None, TypeError),
        (tuple(PARAMETERS), None, TypeError),
        (PARAMETERS, object(), TypeError),
        (PARAMETERS._replace(seed=True), None, TypeError),
        (PARAMETERS._replace(seed="1"), None, TypeError),
        (PARAMETERS._replace(seed=-1), None, ValueError),
        (PARAMETERS._replace(seed=2**64), None, ValueError),
        (PARAMETERS._replace(m=0), None, ValueError),
        (PARAMETERS._replace(draws=1.5), None, TypeError),
    ],
)
def test_refused_arguments_start_nothing(
    stubs, build_root, kernel, parameters, keeper, error
):
    selected = []
    op = cuda_check.operation_for(
        the_target(), sources=lambda path: selected.append(path) or (kernel,)
    )
    with pytest.raises(error):
        op(
            "r",
            "h",
            parameters,
            "out",
            build_log.LogKeeper() if keeper is None else keeper,
        )
    assert stubs.calls() == [] and selected == []
    assert list(build_root.iterdir()) == []


# The device check


@posix_only
@pytest.mark.parametrize(
    "conf",
    [
        {"status": 6, "stderr": "No devices were found\n"},
        {"status": 9},
        {"status": 12},
        {"status": 0, "stdout": "no line it reads\n"},
        {"status": 4},
    ],
    ids=["no-device", "no-driver", "no-nvml", "unreadable", "other-status"],
)
def test_no_usable_device_is_device_unavailable_before_anything_else(
    stubs, build_root, kernel, conf
):
    stubs.set("nvidia-smi", **conf)
    selected = []
    op = cuda_check.operation_for(
        the_target(), sources=lambda path: selected.append(path) or (kernel,)
    )
    keeper = build_log.LogKeeper()
    failure = failure_of(op, check_failure.KIND_DEVICE_UNAVAILABLE, keeper=keeper)
    assert failure.message
    assert stubs.names() == ["nvidia-smi"]
    assert selected == [] and keeper.held() is None
    assert list(build_root.iterdir()) == []


@posix_only
def test_an_absent_device_query_program_is_device_unavailable(
    stubs, build_root, kernel
):
    stubs.remove("nvidia-smi")
    failure_of(operation(kernel), check_failure.KIND_DEVICE_UNAVAILABLE)
    assert stubs.names() == []
    assert list(build_root.iterdir()) == []


@pytest.mark.parametrize(
    "found",
    [
        vendor_adapter.Probe(vendor_adapter.ABSENT, None, cuda_adapter.NO_DEVICE),
        vendor_adapter.Probe(vendor_adapter.UNREADABLE, None, "unreadable"),
    ],
)
def test_confirm_device_raises_device_unavailable_without_a_usable_device(
    monkeypatch, found
):
    monkeypatch.setattr(
        cuda_adapter,
        "check_device",
        lambda *, timeout_s: cuda_adapter.device_outcome(found),
    )
    with pytest.raises(tools.ToolFailure) as raised:
        cuda_check.confirm_device()
    assert raised.value.kind == check_failure.KIND_DEVICE_UNAVAILABLE
    assert raised.value.message == found.message


def test_confirm_device_goes_on_for_a_usable_device(monkeypatch):
    seen = []

    def check_device(*, timeout_s):
        seen.append(timeout_s)
        return cuda_adapter.device_outcome(vendor_adapter.Probe(PRESENT, "GPU", "m"))

    monkeypatch.setattr(cuda_adapter, "check_device", check_device)
    assert cuda_check.confirm_device() is None
    assert seen == [cuda_check.DEVICE_QUERY_TIMEOUT_S]


def test_confirm_device_lets_pass_what_the_check_lets_pass(monkeypatch):
    def check_device(*, timeout_s):
        raise PermissionError("not placed")

    monkeypatch.setattr(cuda_adapter, "check_device", check_device)
    with pytest.raises(PermissionError):
        cuda_check.confirm_device()


# The selection


def test_select_sources_returns_the_selected_paths_as_a_tuple(kernel):
    seen = []
    selected = cuda_check.select_sources(
        lambda path: seen.append(path) or [kernel, str(kernel)], "the-output"
    )
    assert selected == (kernel, str(kernel)) and seen == ["the-output"]


@pytest.mark.parametrize(
    ("selection", "kind"),
    [
        (lambda path: (), check_failure.KIND_NO_KERNEL_SOURCE),
        (lambda path: [], check_failure.KIND_NO_KERNEL_SOURCE),
        (lambda path: 1 / 0, check_failure.KIND_KERNEL_SOURCE_UNREADABLE),
        (lambda path: (Path(path),), check_failure.KIND_BUILD_INPUT_MISSING),
        (
            lambda path: (Path(path) / "absent.cu",),
            check_failure.KIND_BUILD_INPUT_MISSING,
        ),
        (lambda path: ("bad\0name.cu",), check_failure.KIND_BUILD_INPUT_MISSING),
    ],
    ids=["empty-tuple", "empty-list", "raises", "a-directory", "absent", "nul"],
)
def test_select_sources_answers_a_selection_that_names_no_regular_file(
    tmp_path, selection, kind
):
    with pytest.raises(tools.ToolFailure) as raised:
        cuda_check.select_sources(selection, str(tmp_path))
    assert raised.value.kind == kind
    assert str(tmp_path) not in raised.value.message


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="no symbolic links")
def test_select_sources_answers_a_link_as_no_regular_file(tmp_path, kernel):
    link = tmp_path / "link.cu"
    try:
        link.symlink_to(kernel)
    except OSError:
        pytest.skip("symbolic links cannot be made here")
    with pytest.raises(tools.ToolFailure) as raised:
        cuda_check.select_sources(lambda path: (link,), "out")
    assert raised.value.kind == check_failure.KIND_BUILD_INPUT_MISSING


@pytest.mark.parametrize(
    "selection",
    [
        lambda path: "kernel.cu",
        lambda path: None,
        lambda path: (1,),
        lambda path: [b"k"],
    ],
)
def test_select_sources_refuses_a_value_of_another_type(selection):
    with pytest.raises(TypeError):
        cuda_check.select_sources(selection, "out")


def test_select_sources_lets_a_request_to_end_pass():
    def selection(path):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        cuda_check.select_sources(selection, "out")


@posix_only
def test_a_failed_selection_starts_no_build(stubs, build_root):
    op = cuda_check.operation_for(the_target(), sources=lambda path: ())
    failure_of(op, check_failure.KIND_NO_KERNEL_SOURCE)
    assert stubs.names() == ["nvidia-smi"]
    assert list(build_root.iterdir()) == []


# The build and the run, with stub programs


@posix_only
def test_a_built_program_is_run_and_its_report_returned(stubs, build_root, kernel):
    stubs.set("nvcc", program=program(), stdout="nvcc says\n", stderr="a warning\n")
    keeper = build_log.LogKeeper()
    assert call(operation(kernel), keeper=keeper) == REPORT.encode()
    device, build, run = stubs.calls()
    assert device[0] == "nvidia-smi"
    target = the_target()
    assert build[0] == "nvcc"
    assert tuple(build[1 : 1 + len(target.flags)]) == target.flags
    sources = build[1 + len(target.flags) : -2]
    assert sources == [str(cuda_programs.VERIFICATION_PROGRAM_SOURCE), str(kernel)]
    assert build[-2] == "-o"
    assert run[0] == "program"
    assert Path(run[1]).name == cuda_check.EXECUTABLE_NAME
    assert Path(run[1]).parent.parent == build_root
    assert Path(run[1]).parent.name.startswith(cuda_check.BUILD_DIR_PREFIX)
    assert run[2:] == ["5", "33", "7", "2", "987654321"]
    assert "nvcc says" in keeper.held() and "a warning" in keeper.held()
    assert list(build_root.iterdir()) == []


@posix_only
def test_the_kernel_files_are_handed_in_the_selection_s_order(
    stubs, build_root, tmp_path
):
    first, second = tmp_path / "b.cu", tmp_path / "a.cu"
    for path in (first, second):
        path.write_text("//\n", encoding="utf-8")
    op = cuda_check.operation_for(the_target(), sources=lambda path: (first, second))
    call(op)
    build = stubs.calls()[1]
    assert build[-4:-2] == [str(first), str(second)]


@posix_only
@pytest.mark.parametrize(
    ("conf", "answer"),
    [
        ({"status": 2, "stderr": "kernel.cu(1): error\n"}, "build_exit_status"),
        ({"sleep": 5, "stderr": "slow\n"}, "build_time_limit"),
    ],
)
def test_a_build_that_fails_is_its_condition_with_the_log_kept(
    stubs, build_root, kernel, conf, answer
):
    stubs.set("nvcc", **conf)
    keeper = build_log.LogKeeper()
    op = operation(kernel, target=the_target(build_time_limit_s=1))
    assert call(op, keeper=keeper) == answer
    assert stubs.names() == ["nvidia-smi", "nvcc"]
    assert type(keeper.held()) is str
    if answer == "build_exit_status":
        assert "kernel.cu(1): error" in keeper.held()
    assert list(build_root.iterdir()) == []


@posix_only
def test_a_build_with_status_0_and_no_executable_is_build_output_missing(
    stubs, build_root, kernel
):
    stubs.set("nvcc", stdout="said nothing wrong\n")
    keeper = build_log.LogKeeper()
    failure = failure_of(
        operation(kernel), check_failure.KIND_BUILD_OUTPUT_MISSING, keeper=keeper
    )
    assert str(build_root) not in failure.message
    assert "said nothing wrong" in keeper.held()
    assert list(build_root.iterdir()) == []


@posix_only
def test_an_absent_compiler_is_compiler_unavailable_with_no_log(
    stubs, build_root, kernel
):
    stubs.remove("nvcc")
    keeper = build_log.LogKeeper()
    failure_of(
        operation(kernel), check_failure.KIND_COMPILER_UNAVAILABLE, keeper=keeper
    )
    assert keeper.held() is None
    assert list(build_root.iterdir()) == []


@posix_only
@pytest.mark.parametrize(
    ("conf", "answer"),
    [({"status": 3}, "exit_status"), ({"sleep": 5}, "time_limit")],
)
def test_a_process_that_fails_is_broken_and_never_a_tool_failure(
    stubs, build_root, kernel, conf, answer
):
    stubs.set("nvcc", program=program(stdout="part of a rep", **conf))
    op = operation(kernel, target=the_target(process_time_limit_cap_s=1))
    assert call(op) == answer
    assert list(build_root.iterdir()) == []


@posix_only
def test_an_incomplete_report_with_status_0_is_returned_for_the_judging(
    stubs, build_root, kernel
):
    stubs.set("nvcc", program=program(stdout="part"))
    keeper = build_log.LogKeeper()
    answer = check_operation.ask(
        operation(kernel),
        "r",
        "h",
        PARAMETERS,
        "out",
        keeper,
        log_path=build_root.parent / "log.txt",
        **TOLERANCE,
    )
    assert answer["outcome"] == "broken"
    assert list(build_root.iterdir()) == []


@posix_only
def test_an_executable_that_cannot_start_is_executable_unstartable(
    stubs, build_root, kernel
):
    stubs.set("nvcc", program=program(), mode=0o644)
    failure_of(operation(kernel), check_failure.KIND_EXECUTABLE_UNSTARTABLE)
    assert list(build_root.iterdir()) == []


@posix_only
def test_an_unusable_build_directory_starts_no_build(
    stubs, tmp_path, kernel, monkeypatch
):
    checkout = tmp_path / "checkout"
    (checkout / ".git").mkdir(parents=True)
    monkeypatch.setattr(tempfile, "tempdir", str(checkout))
    failure_of(operation(kernel), check_failure.KIND_BUILD_DIRECTORY_UNUSABLE)
    assert stubs.names() == ["nvidia-smi"]
    assert [path.name for path in checkout.iterdir()] == [".git"]


@posix_only
def test_a_request_to_end_in_the_run_still_removes_the_build_directory(
    stubs, build_root, kernel, monkeypatch
):
    def run(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(cuda_adapter, "run", run)
    with pytest.raises(KeyboardInterrupt):
        call(operation(kernel))
    assert list(build_root.iterdir()) == []


# build_executable, with a stand-in build


def a_result(tmp_path, *, ok=False, returncode=0, timed_out=False, log="the log"):
    return clang_build.BuildResult(
        ok=ok,
        returncode=returncode,
        timed_out=timed_out,
        output=tmp_path / "x",
        log=log,
        command=("nvcc",),
        duration_s=0.1,
    )


def built_with(monkeypatch, tmp_path, kernel, answer):
    def build(*args, **kwargs):
        if isinstance(answer, BaseException):
            raise answer
        return answer

    monkeypatch.setattr(clang_build, "build", build)
    keeper = build_log.LogKeeper()
    return keeper, lambda: cuda_check.build_executable(
        the_target(), (kernel,), tmp_path / "x", keeper
    )


def test_build_executable_returns_none_for_a_built_executable(
    monkeypatch, tmp_path, kernel
):
    keeper, build = built_with(
        monkeypatch, tmp_path, kernel, a_result(tmp_path, ok=True)
    )
    assert build() is None
    assert keeper.held() == "the log"


@pytest.mark.parametrize(
    ("error", "answer", "log"),
    [
        (
            clang_build.TemporaryNotRemovedError(OSError("t"), None),
            None,
            "carried log",
        ),
        (
            clang_build.CompilerRunError(OSError("r"), timed_out=True, log="so far"),
            "build_time_limit",
            "so far",
        ),
        (
            clang_build.CompilerRunError(OSError("r"), returncode=1),
            "build_exit_status",
            None,
        ),
    ],
)
def test_build_executable_places_a_raised_build_and_keeps_its_log(
    monkeypatch, tmp_path, kernel, error, answer, log
):
    if isinstance(error, clang_build.TemporaryNotRemovedError):
        error.result = a_result(tmp_path, ok=True, log="carried log")
    keeper, build = built_with(monkeypatch, tmp_path, kernel, error)
    assert build() == answer
    assert keeper.held() == log


@pytest.mark.parametrize(
    ("error", "kind"),
    [
        (
            clang_build.CompilerNotFoundError("nvcc"),
            check_failure.KIND_COMPILER_UNAVAILABLE,
        ),
        (
            clang_build.CompilerNotStartedError(OSError("s")),
            check_failure.KIND_COMPILER_UNAVAILABLE,
        ),
        (
            clang_build.ArtefactNotPlacedError(OSError("p"), None),
            check_failure.KIND_BUILD_OUTPUT_MISSING,
        ),
    ],
)
def test_build_executable_raises_the_kind_of_a_placed_error(
    monkeypatch, tmp_path, kernel, error, kind
):
    if isinstance(error, clang_build.ArtefactNotPlacedError):
        error.result = a_result(tmp_path, log="placed log")
    keeper, build = built_with(monkeypatch, tmp_path, kernel, error)
    with pytest.raises(tools.ToolFailure) as raised:
        build()
    assert raised.value.kind == kind
    assert raised.value.message == cuda_check._BUILD_MESSAGES[kind]
    expected = (
        "placed log" if isinstance(error, clang_build.ArtefactNotPlacedError) else None
    )
    assert keeper.held() == expected


def test_build_executable_answers_a_refused_setting(monkeypatch, tmp_path, kernel):
    error = ValueError("a flag")
    error.parameter = "flags"
    keeper, build = built_with(monkeypatch, tmp_path, kernel, error)
    with pytest.raises(tools.ToolFailure) as raised:
        build()
    assert raised.value.kind == check_failure.KIND_SETTINGS_REFUSED
    assert keeper.held() is None


def test_build_executable_lets_an_error_no_row_places_pass(
    monkeypatch, tmp_path, kernel
):
    keeper, build = built_with(monkeypatch, tmp_path, kernel, LookupError("x"))
    with pytest.raises(LookupError):
        build()
    assert keeper.held() is None


def test_build_executable_refuses_a_build_no_row_holds(monkeypatch, tmp_path, kernel):
    result = a_result(tmp_path, returncode=None)
    _, build = built_with(monkeypatch, tmp_path, kernel, result)
    with pytest.raises(RuntimeError):
        build()


def test_build_executable_hands_the_command_of_the_adapter(
    monkeypatch, tmp_path, kernel
):
    seen = {}

    def build(sources, output, **kwargs):
        seen.update(kwargs, sources=sources, output=output)
        return a_result(tmp_path, ok=True)

    monkeypatch.setattr(clang_build, "build", build)
    target = the_target(build_time_limit_s=7)
    cuda_check.build_executable(
        target, (kernel,), tmp_path / "x", build_log.LogKeeper()
    )
    assert seen == {
        "sources": (kernel,),
        "output": tmp_path / "x",
        "timeout_s": 7,
        "flags": target.flags,
        "trailing_flags": target.trailing_flags,
        "compiler": ("nvcc",),
        "env": target.env,
    }


# carry_out


def test_carry_out_returns_what_run_returns_and_removes_the_directory(
    monkeypatch, build_root, kernel, tmp_path
):
    monkeypatch.setattr(cuda_check, "confirm_device", lambda: None)
    monkeypatch.setattr(
        cuda_check, "build_executable", lambda target, sources, executable, keeper: None
    )
    seen = []
    answer = cuda_check.carry_out(
        the_target(),
        lambda path: (kernel,),
        "out",
        build_log.LogKeeper(),
        program=tmp_path / "program.c",
        executable_name="exe",
        prefix="p-",
        run=lambda executable: seen.append(executable) or "ran",
    )
    assert answer == "ran"
    assert Path(seen[0]).name == "exe" and Path(seen[0]).parent.name.startswith("p-")
    assert list(build_root.iterdir()) == []


def test_carry_out_does_not_run_after_a_build_condition(
    monkeypatch, build_root, kernel
):
    monkeypatch.setattr(cuda_check, "confirm_device", lambda: None)
    monkeypatch.setattr(
        cuda_check,
        "build_executable",
        lambda target, sources, executable, keeper: "build_exit_status",
    )
    answer = cuda_check.carry_out(
        the_target(),
        lambda path: (kernel,),
        "out",
        build_log.LogKeeper(),
        program="p.c",
        executable_name="exe",
        prefix="p-",
        run=lambda executable: pytest.fail("ran"),
    )
    assert answer == "build_exit_status"
    assert list(build_root.iterdir()) == []


def test_carry_out_removes_the_directory_when_the_build_raises(
    monkeypatch, build_root, kernel
):
    monkeypatch.setattr(cuda_check, "confirm_device", lambda: None)

    def build(target, sources, executable, keeper):
        raise tools.ToolFailure(check_failure.KIND_COMPILER_UNAVAILABLE, "m")

    monkeypatch.setattr(cuda_check, "build_executable", build)
    with pytest.raises(tools.ToolFailure):
        cuda_check.carry_out(
            the_target(),
            lambda path: (kernel,),
            "out",
            build_log.LogKeeper(),
            program="p.c",
            executable_name="exe",
            prefix="p-",
            run=lambda executable: None,
        )
    assert list(build_root.iterdir()) == []


# On the real GPU (FR-19 (5))


@pytest.fixture
def gpu():
    if os.name != "posix":
        pytest.skip("the programs use POSIX descriptors and CLOCK_MONOTONIC")
    if shutil.which("nvcc") is None:
        pytest.skip("nvcc is not on PATH (FR-19 (5): a vendor tool's execution test)")
    if shutil.which("g++") is None:
        pytest.skip("nvcc needs the host compiler g++, which is not on PATH")
    if shutil.which("nvidia-smi") is None:
        pytest.skip("nvidia-smi is not on PATH (FR-19 (5))")
    found = cuda_adapter.device_probe(timeout_s=LIMIT)
    if found.state != PRESENT:
        pytest.skip(f"no usable GPU: {found.message}")


HW_PROFILE = {
    "schema_version": SCHEMA_VERSION,
    "accelerator": targets.CUDA_GPU,
    "revision": "A GPU of the test sm_89",
    "toolchain": {"nvcc": "n", "gcc": "g", "nvidia_driver": "d"},
    "host": {"cpu": "c", "os": "o"},
    "hw_source": "external",
}


def a_table(fixture):
    target = targets.target(targets.CUDA_GPU)

    def selection(output_path):
        return (Path(output_path) / fixture,)

    run = cuda_run.operation_for(target, sources=selection)
    return backends.BackendTable(
        [
            backends.Backend(
                targets.CUDA_GPU,
                {
                    TOOL: cuda_check.operation_for(target, sources=selection),
                    "sim.run": run,
                    "board.run": run,
                },
            )
        ]
    )


def checked_on_the_gpu(tmp_path, fixture, parameters=PARAMETERS):
    log_path = tmp_path / "build-log.txt"
    keeper = build_log.LogKeeper()
    op = backends.select(a_table(fixture), HW_PROFILE, TOOL)
    result = check_operation.ask(
        op,
        {"run_id": "test"},
        HW_PROFILE,
        parameters,
        str(FIXTURES),
        keeper,
        log_path=log_path,
        **TOLERANCE,
    )
    return result, log_path


@pytest.mark.parametrize(
    "parameters",
    [PARAMETERS, CheckParameters(seed=7, draws=3, m=8, k=8, n=8)],
    ids=["5x33x7", "8x8x8"],
)
def test_a_correct_kernel_passes_on_the_gpu(gpu, tmp_path, parameters):
    result, log_path = checked_on_the_gpu(tmp_path, "gemm.cu", parameters)
    assert result["outcome"] == "pass"
    assert log_path.is_file()


def test_a_wrong_kernel_fails_on_the_gpu(gpu, tmp_path):
    result, _ = checked_on_the_gpu(tmp_path, "gemm_wrong.cu")
    assert result["outcome"] == "fail"


def test_a_kernel_that_does_not_compile_is_built_broken_with_its_log(gpu, tmp_path):
    result, log_path = checked_on_the_gpu(tmp_path, "broken.cu")
    assert (result["outcome"], result["condition"]) == ("broken", "build_exit_status")
    assert "broken.cu" in log_path.read_text(encoding="utf-8")


def test_a_kernel_that_exits_non_zero_is_broken(gpu, tmp_path):
    result, _ = checked_on_the_gpu(tmp_path, "gemm_exit.cu")
    assert (result["outcome"], result["condition"]) == ("broken", "exit_status")


def test_a_device_lost_after_the_check_is_a_run_failure(gpu, tmp_path, monkeypatch):
    hidden = {**os.environ, "CUDA_VISIBLE_DEVICES": ""}
    run = cuda_adapter.run

    def without_a_device(target, executable, arguments=(), *, timeout_s):
        target = dataclasses.replace(target, env=hidden)
        return run(target, executable, arguments, timeout_s=timeout_s)

    monkeypatch.setattr(cuda_adapter, "run", without_a_device)
    result, _ = checked_on_the_gpu(tmp_path, "gemm.cu")
    assert (result["outcome"], result["condition"]) == ("broken", "exit_status")
