import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from hilclaw import (
    checkout_boundary,
    clang_build,
    model_build,
    model_execute,
    model_run,
)
from hilclaw.clang_build import BuildResult
from hilclaw.local_run import RunResult
from hilclaw.model_execute import PREFIX, BuildFailed, ModelExecution, execute
from hilclaw.model_run import ModelProgramResult, RunFailed, encode_input, output_shapes

BUILD_TIMEOUT = 120
RUN_TIMEOUT = 60


def matrices(m, k, n, seed):
    generator = np.random.default_rng(seed)
    a = generator.integers(-4, 5, size=(m, k)).astype(np.float32)
    b = generator.integers(-4, 5, size=(k, n)).astype(np.float32)
    return a, b


def kernel(name, flags=("-O2",)):
    return SimpleNamespace(sources=(f"/src/{name}.c",), flags=flags)


def build_result(output, ok=True, log=""):
    return BuildResult(ok, 0 if ok else 1, False, Path(output), log, ("cc",), 0.1)


def run_result(failed=None, outputs=None, returncode=0, timed_out=False):
    run = RunResult(returncode, timed_out, b"", b"", ("prog",), 0.2)
    return ModelProgramResult(failed, outputs, run)


class Recorder:
    def __init__(self, failing_kernel=None, failing_program=False, run=None):
        self.events = []
        self.failing_kernel = failing_kernel
        self.failing_program = failing_program
        self.run = run
        self.input_bytes = None
        self.directory_listing = None

    def kernel_library(self, sources, output, **options):
        self.events.append(("kernel", sources, output, options))
        index = sum(1 for event in self.events if event[0] == "kernel") - 1
        assert os.path.isdir(os.path.dirname(output))
        Path(output).write_bytes(b"library")
        return build_result(output, ok=index != self.failing_kernel, log=f"log {index}")

    def model_program(self, output, **options):
        self.events.append(("program", output, options))
        Path(output).write_bytes(b"program")
        return build_result(output, ok=not self.failing_program, log="program log")

    def run_program(self, program, input_file, libraries, **options):
        self.events.append(("run", program, input_file, libraries, options))
        self.input_bytes = Path(input_file).read_bytes()
        self.directory_listing = sorted(os.listdir(os.path.dirname(input_file)))
        if isinstance(self.run, BaseException):
            raise self.run
        return self.run if self.run is not None else run_result(outputs=("out",))


@pytest.fixture
def recorder(monkeypatch):
    made = Recorder()
    monkeypatch.setattr(model_build, "build_kernel_library", made.kernel_library)
    monkeypatch.setattr(model_build, "build_model_program", made.model_program)
    monkeypatch.setattr(model_run, "run_model_program", made.run_program)
    return made


@pytest.fixture
def parent(tmp_path):
    if checkout_boundary.meets_checkout(
        os.path.realpath(tmp_path), [], containing=False
    ):
        pytest.skip("the temporary directory of pytest lies inside the repository")
    return tmp_path


def three_calls():
    return [
        (0, *matrices(2, 3, 4, 1)),
        (2, *matrices(1, 1, 1, 2)),
        (1, *matrices(5, 2, 3, 3)),
    ]


def run_execute(parent, kernels=None, calls=None, **options):
    options.setdefault("build_timeout_s", 30)
    options.setdefault("run_timeout_s", 7)
    return execute(
        kernels if kernels is not None else [kernel("k0"), kernel("k1"), kernel("k2")],
        calls if calls is not None else three_calls(),
        parent=parent,
        **options,
    )


def test_happy_path_builds_in_order_runs_once_and_removes(recorder, parent):
    kernels = [kernel("k0", ("-O1",)), kernel("k1", ["-O2"]), kernel("k2", ())]
    calls = three_calls()
    result = run_execute(
        parent,
        kernels,
        calls,
        program_flags=("-O3",),
        program_trailing_flags=("-ldl",),
        compiler=("clang-x",),
        env={"A": "1"},
    )
    assert isinstance(result, ModelExecution)
    assert result.build_failed is None
    assert result.run == run_result(outputs=("out",))
    assert result.removed is True
    assert [event[0] for event in recorder.events] == [
        "kernel",
        "kernel",
        "kernel",
        "program",
        "run",
    ]
    directory = os.path.dirname(recorder.events[0][2])
    assert os.path.isabs(directory)
    assert os.path.dirname(directory) == os.path.realpath(parent)
    assert os.path.basename(directory).startswith(PREFIX)
    assert not os.path.lexists(directory)
    assert os.listdir(parent) == []
    libraries = []
    for index, kernel_ in enumerate(kernels):
        _, sources, output, options = recorder.events[index]
        assert sources is kernel_.sources
        assert os.path.dirname(output) == directory
        assert options == {
            "timeout_s": 30,
            "flags": kernel_.flags,
            "compiler": ("clang-x",),
            "env": {"A": "1"},
        }
        assert options["flags"] is kernel_.flags
        libraries.append(output)
    assert len(set(libraries)) == 3
    _, program, options = recorder.events[3]
    assert os.path.dirname(program) == directory
    assert program not in libraries
    assert options == {
        "timeout_s": 30,
        "flags": ("-O3",),
        "trailing_flags": ("-ldl",),
        "compiler": ("clang-x",),
        "env": {"A": "1"},
    }
    _, started, input_file, run_libraries, options = recorder.events[4]
    assert started == program
    assert os.path.isabs(input_file)
    assert os.path.dirname(input_file) == directory
    assert input_file not in libraries and input_file != program
    assert list(run_libraries) == libraries
    assert options == {
        "shapes": output_shapes(calls),
        "timeout_s": 7,
        "env": {"A": "1"},
    }
    assert recorder.input_bytes == encode_input(calls)
    assert len(recorder.directory_listing) == 5


def test_defaults_hand_over_empty_flags_and_none(recorder, parent):
    result = run_execute(parent, [kernel("k0")], [(0, *matrices(1, 2, 1, 4))])
    assert result.build_failed is None
    assert recorder.events[0][3] == {
        "timeout_s": 30,
        "flags": ("-O2",),
        "compiler": None,
        "env": None,
    }
    assert recorder.events[1][2] == {
        "timeout_s": 30,
        "flags": (),
        "trailing_flags": (),
        "compiler": None,
        "env": None,
    }
    assert recorder.events[2][4]["env"] is None


def test_parent_none_uses_the_system_temporary_directory(recorder, monkeypatch, parent):
    monkeypatch.setattr(model_execute.tempfile, "gettempdir", lambda: str(parent))
    result = execute(
        [kernel("k0")],
        [(0, *matrices(1, 1, 1, 1))],
        build_timeout_s=1,
        run_timeout_s=1,
    )
    assert result.removed
    directory = os.path.dirname(recorder.events[0][2])
    assert os.path.dirname(directory) == os.path.realpath(parent)


def test_empty_prefix_starts_the_program_by_its_path(recorder, parent):
    run_execute(parent, prefix=[])
    program = recorder.events[3][1]
    assert recorder.events[4][1] == program
    assert isinstance(recorder.events[4][1], str)


def test_non_empty_prefix_is_put_in_front(recorder, parent):
    run_execute(parent, prefix=["podman", Path("run")])
    program = recorder.events[3][1]
    assert recorder.events[4][1] == ("podman", "run", program)


def test_failed_kernel_build_stops_before_the_rest(monkeypatch, parent):
    recorder = Recorder(failing_kernel=1)
    monkeypatch.setattr(model_build, "build_kernel_library", recorder.kernel_library)
    monkeypatch.setattr(model_build, "build_model_program", recorder.model_program)
    monkeypatch.setattr(model_run, "run_model_program", recorder.run_program)
    result = run_execute(parent)
    assert [event[0] for event in recorder.events] == ["kernel", "kernel"]
    failed_output = recorder.events[1][2]
    assert result.build_failed == BuildFailed(
        1, build_result(failed_output, ok=False, log="log 1")
    )
    assert result.build_failed.kernel == 1
    assert result.build_failed.build.log == "log 1"
    assert result.run is None
    assert result.removed is True
    assert os.listdir(parent) == []


def test_failed_program_build_names_no_kernel(monkeypatch, parent):
    recorder = Recorder(failing_program=True)
    monkeypatch.setattr(model_build, "build_kernel_library", recorder.kernel_library)
    monkeypatch.setattr(model_build, "build_model_program", recorder.model_program)
    monkeypatch.setattr(model_run, "run_model_program", recorder.run_program)
    result = run_execute(parent)
    assert [event[0] for event in recorder.events][-1] == "program"
    assert "run" not in [event[0] for event in recorder.events]
    assert result.build_failed.kernel is None
    assert result.build_failed.build.ok is False
    assert result.build_failed.build.log == "program log"
    assert result.run is None
    assert result.removed is True
    assert os.listdir(parent) == []


def test_run_failed_is_returned_unchanged(recorder, parent):
    failed = run_result(failed=RunFailed.TIMEOUT, returncode=None, timed_out=True)
    recorder.run = failed
    result = run_execute(parent)
    assert result.build_failed is None
    assert result.run is failed
    assert result.removed is True


@pytest.mark.parametrize("stage", ["kernel", "program"])
def test_build_exception_reaches_the_caller_after_removal(monkeypatch, parent, stage):
    seen = []

    def raising(*args, **options):
        seen.append(args)
        raise clang_build.CompilerNotFoundError("no compiler")

    recorder = Recorder()
    monkeypatch.setattr(
        model_build,
        "build_kernel_library",
        raising if stage == "kernel" else recorder.kernel_library,
    )
    monkeypatch.setattr(
        model_build,
        "build_model_program",
        raising if stage == "program" else recorder.model_program,
    )
    monkeypatch.setattr(model_run, "run_model_program", recorder.run_program)
    with pytest.raises(clang_build.CompilerNotFoundError):
        run_execute(parent)
    assert seen
    assert os.listdir(parent) == []


def test_run_exception_reaches_the_caller_after_removal(recorder, parent):
    recorder.run = OSError("cannot start")
    with pytest.raises(OSError, match="cannot start"):
        run_execute(parent)
    assert recorder.input_bytes is not None
    assert os.listdir(parent) == []


def test_failed_removal_is_reported_and_raises_nothing(recorder, monkeypatch, parent):
    calls = []

    def refusing(directory, *, keep_out):
        calls.append((directory, keep_out))
        raise model_execute.scratch.InvalidScratchArgumentError("scratch: refused")

    monkeypatch.setattr(model_execute.scratch, "remove", refusing)
    result = run_execute(parent, keep_out=[str(parent / "data")])
    assert result.removed is False
    assert calls[0][1] == [str(parent / "data")]
    directory = calls[0][0]
    assert os.path.isdir(directory)
    shutil.rmtree(directory)


def test_removal_result_false_is_passed_on(recorder, monkeypatch, parent):
    monkeypatch.setattr(model_execute.scratch, "remove", lambda directory, **_: False)
    result = run_execute(parent)
    assert result.removed is False
    for name in os.listdir(parent):
        shutil.rmtree(parent / name)


class _NoFlags:
    sources = ("a.c",)


class _BytesPath:
    def __fspath__(self):
        return b"/bin/podman"


@pytest.mark.parametrize(
    ("kernels", "error", "text"),
    [
        ([], ValueError, "kernels: no kernel"),
        ("k0", TypeError, "kernels: must be a sequence"),
        (b"k0", TypeError, "kernels: must be a sequence"),
        (iter([kernel("k0")]), TypeError, "kernels: must be a sequence"),
        ([kernel("k0"), _NoFlags()], TypeError, "kernels[1]: has no attribute 'flags'"),
        (
            [SimpleNamespace(flags=())],
            TypeError,
            "kernels[0]: has no attribute 'sources'",
        ),
    ],
)
def test_refused_kernels(recorder, parent, kernels, error, text):
    with pytest.raises(error) as caught:
        run_execute(parent, kernels, [(0, *matrices(1, 1, 1, 1))])
    assert str(caught.value).startswith(text)
    assert recorder.events == []
    assert os.listdir(parent) == []


def test_index_equal_to_the_number_of_kernels_is_refused(recorder, parent):
    calls = [(0, *matrices(1, 1, 1, 1)), (2, *matrices(1, 1, 1, 1))]
    with pytest.raises(ValueError, match=r"^calls\[1\]: index 2 is not below"):
        run_execute(parent, [kernel("k0"), kernel("k1")], calls)
    assert recorder.events == []
    assert os.listdir(parent) == []


@pytest.mark.parametrize(
    ("calls", "error"),
    [
        ([(0, np.ones((1, 1)), np.ones((1, 1), dtype=np.float32))], ValueError),
        ([], ValueError),
        ("calls", TypeError),
        ([(0, *matrices(2, 3, 4, 1))[:2]], TypeError),
    ],
)
def test_refused_calls_pass_the_error_of_model_run(recorder, parent, calls, error):
    with pytest.raises(error) as caught:
        run_execute(parent, calls=calls)
    with pytest.raises(error) as expected:
        output_shapes(calls)
    assert str(caught.value) == str(expected.value)
    assert recorder.events == []
    assert os.listdir(parent) == []


@pytest.mark.parametrize(
    ("options", "error", "text"),
    [
        ({"prefix": "podman"}, TypeError, "prefix: must be a sequence"),
        ({"prefix": None}, TypeError, "prefix: must be a sequence"),
        ({"prefix": ["podman", 3]}, TypeError, "prefix[1]: must be str"),
        ({"prefix": [b"podman"]}, TypeError, "prefix[0]: must be str"),
        ({"prefix": [_BytesPath()]}, TypeError, "prefix[0]: must be str"),
        ({"keep_out": "/data"}, TypeError, "keep_out must be a sequence"),
        ({"keep_out": Path("/data")}, TypeError, "keep_out must be a sequence"),
        ({"keep_out": 5}, TypeError, "keep_out: must be a sequence"),
        ({"keep_out": ["/data", None]}, TypeError, "keep_out[1]: must be str"),
        ({"prefix": ["pod\0man"]}, ValueError, "prefix[0]: holds a NUL"),
        ({"keep_out": ["/da\0ta"]}, ValueError, "keep_out[0]: holds a NUL"),
    ],
)
def test_refused_prefix_and_keep_out(recorder, parent, options, error, text):
    with pytest.raises(error) as caught:
        run_execute(parent, **options)
    assert str(caught.value).startswith(text)
    assert recorder.events == []
    assert os.listdir(parent) == []


@pytest.mark.parametrize("value", [3, b"/tmp"])
def test_refused_parent_type(recorder, parent, value):
    with pytest.raises(TypeError, match=r"^parent: must be str"):
        run_execute(value)
    assert recorder.events == []
    assert os.listdir(parent) == []


def test_parent_with_a_nul_character_is_refused(recorder, parent):
    with pytest.raises(ValueError, match=r"^parent: holds a NUL character"):
        run_execute(str(parent) + "\0x")
    assert recorder.events == []
    assert os.listdir(parent) == []


def test_parent_inside_the_repository_is_refused(recorder, parent):
    inside = os.path.join(checkout_boundary.PACKAGE_DIRECTORY, "hilclaw")
    before = sorted(os.listdir(inside))
    for place in (checkout_boundary.PACKAGE_DIRECTORY, inside):
        with pytest.raises(ValueError, match=r"^parent: must not be or lie inside"):
            run_execute(place)
    assert sorted(os.listdir(inside)) == before
    assert recorder.events == []


def test_parent_named_in_keep_out_is_refused(recorder, parent):
    data = parent / "data"
    data.mkdir()
    for place in (data, data / "."):
        with pytest.raises(ValueError, match=r"^parent: must not be or lie inside"):
            run_execute(place, keep_out=(str(parent),))
    with pytest.raises(ValueError, match=r"^parent: must not be or lie inside"):
        run_execute(data, keep_out=[data])
    assert os.listdir(data) == []
    assert recorder.events == []


def test_missing_parent_raises_the_os_error(recorder, parent):
    with pytest.raises(FileNotFoundError):
        run_execute(parent / "missing")
    assert recorder.events == []
    assert os.listdir(parent) == []


def test_public_names_and_fields():
    public = {name for name in vars(model_execute) if not name.startswith("_")}
    imported = {
        "os",
        "tempfile",
        "Sequence",
        "NamedTuple",
        "checkout_boundary",
        "clang_build",
        "model_build",
        "model_run",
        "scratch",
    }
    assert public - imported == {"PREFIX", "BuildFailed", "ModelExecution", "execute"}
    assert PREFIX == "hilclaw-model-"
    assert BuildFailed._fields == ("kernel", "build")
    assert ModelExecution._fields == ("build_failed", "run", "removed")
    text = Path(model_execute.__file__).read_text(encoding="utf-8")
    assert "gemm_contract" not in text
    assert "model_binding" not in text


PRODUCT = """\
#include <stddef.h>
void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c)
{
    size_t i, j, p;

    for (i = 0; i < m; i++)
        for (j = 0; j < n; j++) {
            float sum = @START@;

            for (p = 0; p < k; p++)
                sum += a[i * k + p] * b[p * n + j];
            c[i * n + j] = sum;
        }
}
"""

SOURCES = {
    "plain": PRODUCT.replace("@START@", "0.0f"),
    "plus_one": PRODUCT.replace("@START@", "1.0f"),
    "no_entry": "int other_entry(int x)\n{\n    return x + 1;\n}\n",
    "broken": "void hilclaw_gemm(\n",
}


@pytest.fixture(scope="session")
def clang():
    if os.name != "posix":
        pytest.skip("the model program needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")


def real_kernels(directory, names):
    kernels = []
    for name in names:
        source = directory / f"{name}.c"
        source.write_text(SOURCES[name], encoding="ascii", newline="\n")
        kernels.append(SimpleNamespace(sources=(source,), flags=("-O2",)))
    return kernels


def real_execute(tmp_path, names, calls):
    sources = tmp_path / "sources"
    sources.mkdir()
    builds = tmp_path / "builds"
    builds.mkdir()
    result = execute(
        real_kernels(sources, names),
        calls,
        build_timeout_s=BUILD_TIMEOUT,
        run_timeout_s=RUN_TIMEOUT,
        program_flags=("-O2",),
        program_trailing_flags=("-ldl",),
        parent=builds,
    )
    assert result.removed is True
    assert os.listdir(builds) == []
    return result


def test_real_two_kernels_several_shapes(clang, tmp_path):
    shapes = [(2, 3, 4), (1, 1, 1), (5, 7, 3), (3, 2, 6)]
    calls = [
        (position % 2, *matrices(m, k, n, 10 + position))
        for position, (m, k, n) in enumerate(shapes)
    ]
    result = real_execute(tmp_path, ["plain", "plus_one"], calls)
    assert result.build_failed is None
    assert result.run.failed is None, result.run.run.stderr
    assert len(result.run.outputs) == len(calls)
    for (index, a, b), output in zip(calls, result.run.outputs, strict=True):
        assert output.dtype == np.float32
        assert np.array_equal(output, a @ b + np.float32(index))


def test_real_build_failed(clang, tmp_path):
    result = real_execute(
        tmp_path, ["plain", "broken", "plus_one"], [(0, *matrices(1, 1, 1, 1))]
    )
    assert result.build_failed.kernel == 1
    assert result.build_failed.build.ok is False
    assert result.build_failed.build.log
    assert result.run is None


def test_real_run_failed_for_a_library_without_entry(clang, tmp_path):
    result = real_execute(tmp_path, ["plain", "no_entry"], [(0, *matrices(2, 2, 2, 1))])
    assert result.build_failed is None
    assert result.run.failed is RunFailed.EXIT_STATUS
    assert result.run.run.returncode == 6
    assert result.run.outputs is None
