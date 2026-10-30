import inspect
import os
import shutil
from pathlib import Path

import numpy as np
import pytest
import test_model_forward as forward
import test_model_forward_run as forward_run

from hilclaw import (
    checkout_boundary,
    clang_build,
    elementwise_add_bf16_contract,
    gemm_bf16_contract,
    model_build,
    model_execute,
    model_forward_check,
    model_forward_execute,
    model_forward_run,
    rmsnorm_bf16_contract,
    rope_bf16_contract,
    sdpa_kv_cache_bf16_contract,
    swiglu_bf16_contract,
)
from hilclaw.clang_build import BuildResult
from hilclaw.local_run import RunResult
from hilclaw.model_binding import (
    INVALID_INPUT,
    KERNEL_UNFIT,
    NO_KERNEL,
    BindingEntry,
    KernelReference,
)
from hilclaw.model_execute import BuildFailed
from hilclaw.model_forward_execute import PREFIX, ForwardExecution, execute
from hilclaw.model_forward_run import CALL_SITES, ForwardProgramResult, encode_input
from hilclaw.model_run import RunFailed

BUILD_TIMEOUT = 120
RUN_TIMEOUT = 60
DIMENSIONS = forward_run.DIMENSIONS
ROPE = forward_run.ROPE
EPS = forward_run.EPS
D, V = forward.D, forward.V
S, G = 3, 3
KINDS = forward.KINDS
CONTRACTS = {
    "gemm": gemm_bf16_contract.task_contract(1, 1, 1),
    "rmsnorm": rmsnorm_bf16_contract.task_contract(1, 1),
    "add": elementwise_add_bf16_contract.task_contract(1, 1),
    "swiglu": swiglu_bf16_contract.task_contract(1, 1),
    "rope": rope_bf16_contract.task_contract(1, 1, 2),
    "sdpa": sdpa_kv_cache_bf16_contract.task_contract(1, 1, 1, 1, 1),
}
KIND_OF = dict(zip(CALL_SITES, forward.KIND_OF_SITE, strict=True))


def reference(kind, name=None, flags=forward.KERNEL_FLAGS):
    return KernelReference((f"/src/{name or kind}.c",), CONTRACTS[kind], flags)


def binding_of(kernels):
    return {
        site: [BindingEntry(kernels[KIND_OF[site]], "every")] for site in CALL_SITES
    }


def separate_binding():
    return binding_of({kind: reference(kind) for kind in KINDS})


def model_arguments(model, **changes):
    tokens = [int(token) for token in model["tokens"]]
    values = {
        "eps": EPS,
        "rope": ROPE,
        "weights": forward_run.weights_of(model),
        "prompt": tokens[: model["S"]],
        "given": tokens[model["S"] :],
        "generation_length": model["G"],
        "lm_head_rows": "all",
    }
    values.update(changes)
    return values


def build_result(output, ok=True, log=""):
    return BuildResult(ok, 0 if ok else 1, False, Path(output), log, ("cc",), 0.1)


def program_result(failed=None):
    run = RunResult(0 if failed is None else 1, False, b"", b"", ("prog",), 0.2)
    report = None if failed else forward_run.ForwardReport(np.zeros(1), np.zeros(1))
    return ForwardProgramResult(failed, report, run)


class Recorder:
    def __init__(self, failing_kernel=None, failing_program=False):
        self.events = []
        self.failing_kernel = failing_kernel
        self.failing_program = failing_program
        self.run = program_result()
        self.input_bytes = None
        self.listing = None

    def kernel_library(self, sources, output, **options):
        self.events.append(("kernel", sources, output, options))
        index = sum(1 for event in self.events if event[0] == "kernel") - 1
        Path(output).write_bytes(b"library")
        return build_result(output, ok=index != self.failing_kernel, log=f"log {index}")

    def forward_program(self, output, **options):
        self.events.append(("program", output, options))
        Path(output).write_bytes(b"program")
        return build_result(output, ok=not self.failing_program, log="program log")

    def run_program(self, program, input_file, libraries, **options):
        self.events.append(("run", program, input_file, libraries, options))
        self.input_bytes = Path(input_file).read_bytes()
        self.listing = sorted(os.listdir(os.path.dirname(input_file)))
        if isinstance(self.run, BaseException):
            raise self.run
        return self.run

    def install(self, monkeypatch):
        monkeypatch.setattr(model_build, "build_kernel_library", self.kernel_library)
        monkeypatch.setattr(model_build, "build_forward_program", self.forward_program)
        monkeypatch.setattr(model_forward_run, "run_forward_program", self.run_program)
        return self

    def kinds(self):
        return [event[0] for event in self.events]

    def built_names(self):
        return [Path(event[1][0]).stem for event in self.events if event[0] == "kernel"]

    def table(self, passes):
        count = len(CALL_SITES) * passes
        words = np.frombuffer(self.input_bytes, dtype=np.uint64, count=count, offset=84)
        return {
            site: [int(word) for word in words[s * passes : (s + 1) * passes]]
            for s, site in enumerate(CALL_SITES)
        }


@pytest.fixture
def recorder(monkeypatch):
    return Recorder().install(monkeypatch)


@pytest.fixture
def parent(tmp_path):
    if checkout_boundary.meets_checkout(
        os.path.realpath(tmp_path), [], containing=False
    ):
        pytest.skip("the temporary directory of pytest lies inside the repository")
    return tmp_path


def run_execute(parent, binding=None, model=None, **options):
    model = model if model is not None else forward_run.model_of(41, prompt=S, given=G)
    arguments = model_arguments(model)
    for name in tuple(options):
        if name in arguments:
            arguments[name] = options.pop(name)
    options.setdefault("build_timeout_s", 30)
    options.setdefault("run_timeout_s", 7)
    return execute(
        DIMENSIONS,
        binding if binding is not None else separate_binding(),
        parent=parent,
        **arguments,
        **options,
    )


def expected_check(binding, model, **changes):
    arguments = model_arguments(model, **changes)
    return model_forward_check.check(DIMENSIONS, binding, dtype="bf16", **arguments)


def test_happy_path_checks_builds_each_kernel_runs_once_and_removes(recorder, parent):
    model = forward_run.model_of(41, prompt=S, given=G)
    binding = separate_binding()
    env = {"A": "1"}
    result = run_execute(
        parent,
        binding,
        model,
        program_flags=("-O3",),
        program_trailing_flags=("-ldl",),
        compiler=("clang-x",),
        env=env,
    )
    assert isinstance(result, ForwardExecution)
    assert result.check == expected_check(binding, model)
    assert result.check.ok is True
    assert result.build_failed is None
    assert result.run is recorder.run
    assert result.removed is True
    assert recorder.kinds() == ["kernel"] * 6 + ["program", "run"]
    assert recorder.built_names() == list(KINDS)
    directory = os.path.dirname(recorder.events[0][2])
    assert os.path.isabs(directory)
    assert os.path.dirname(directory) == os.path.realpath(parent)
    assert os.path.basename(directory).startswith(PREFIX)
    assert not os.path.lexists(directory)
    assert os.listdir(parent) == []
    libraries = []
    for index, kind in enumerate(KINDS):
        _, sources, output, options = recorder.events[index]
        kernel = binding[next(s for s in CALL_SITES if KIND_OF[s] == kind)][0].kernel
        assert sources is kernel.sources
        assert os.path.dirname(output) == directory
        assert options == {
            "timeout_s": 30,
            "flags": forward.KERNEL_FLAGS,
            "compiler": ("clang-x",),
            "env": env,
        }
        libraries.append(output)
    assert len(set(libraries)) == 6
    _, program, options = recorder.events[6]
    assert os.path.dirname(program) == directory
    assert program not in libraries
    assert options == {
        "timeout_s": 30,
        "flags": ("-O3",),
        "trailing_flags": ("-ldl",),
        "compiler": ("clang-x",),
        "env": env,
    }
    _, started, input_file, run_libraries, options = recorder.events[7]
    assert started == program
    assert os.path.dirname(input_file) == directory
    assert list(run_libraries) == libraries
    assert options == {
        "dimensions": DIMENSIONS,
        "prompt_length": S,
        "generation_length": G,
        "lm_head_rows": "all",
        "mode": "given",
        "timeout_s": 7,
        "env": env,
    }
    assert options["env"] is env
    expected_input = encode_input(
        DIMENSIONS,
        **model_arguments(model),
        libraries=forward_run.libraries_of(G),
        library_count=6,
    )
    assert recorder.input_bytes == expected_input
    assert len(recorder.listing) == 8


@pytest.mark.parametrize("last", [False, True])
def test_the_generation_mode_is_encoded_and_run_with_its_mode(recorder, parent, last):
    model = forward_run.model_of(44, prompt=S, given=4)
    rows = "last" if last else "all"
    result = run_execute(
        parent, None, model, given=None, generation_length=4, lm_head_rows=rows
    )
    assert result.check == expected_check(
        separate_binding(), model, given=None, generation_length=4, lm_head_rows=rows
    )
    assert result.check.ok is True
    assert result.run is recorder.run
    assert recorder.kinds() == ["kernel"] * 6 + ["program", "run"]
    options = recorder.events[7][4]
    assert options["generation_length"] == 4
    assert options["lm_head_rows"] == rows
    assert options["mode"] == "generation"
    expected_input = encode_input(
        DIMENSIONS,
        **model_arguments(model, given=None, generation_length=4, lm_head_rows=rows),
        libraries=forward_run.libraries_of(4),
        library_count=6,
    )
    assert recorder.input_bytes == expected_input
    assert recorder.table(4) == forward_run.libraries_of(4)


def test_generation_length_has_no_default():
    parameter = inspect.signature(execute).parameters["generation_length"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty


def test_one_source_under_different_contracts_is_one_library_per_contract(
    recorder, parent
):
    kernels = {
        kind: KernelReference(("/src/all.c",), CONTRACTS[kind], ()) for kind in KINDS
    }
    result = run_execute(parent, binding_of(kernels))
    assert result.check.ok
    assert recorder.built_names() == ["all"] * 6
    assert recorder.table(G) == forward_run.libraries_of(G)


def test_kernels_that_compare_equal_are_one_library(recorder, parent):
    kernels = {kind: reference(kind) for kind in KINDS}
    binding = binding_of(kernels)
    twin = KernelReference(
        tuple(kernels["gemm"].sources),
        dict(CONTRACTS["gemm"]),
        tuple(forward.KERNEL_FLAGS),
    )
    assert twin == kernels["gemm"] and twin is not kernels["gemm"]
    binding["down"] = [BindingEntry(twin, "every")]
    result = run_execute(parent, binding)
    assert result.check.ok
    assert recorder.built_names() == list(KINDS)
    assert recorder.table(G) == forward_run.libraries_of(G)


def test_kernels_that_differ_only_in_flags_are_two_libraries(recorder, parent):
    kernels = {kind: reference(kind) for kind in KINDS}
    binding = binding_of(kernels)
    binding["o"] = [BindingEntry(reference("gemm", flags=("-O3",)), "every")]
    result = run_execute(parent, binding)
    assert result.check.ok
    assert recorder.built_names() == ["gemm", "gemm", *KINDS[1:]]
    assert recorder.events[1][3]["flags"] == ("-O3",)
    table = recorder.table(G)
    assert table["qkv"] == [0] * G and table["o"] == [1] * G
    assert table["sdpa"] == [6] * G


def per_shape_binding(last):
    kernels = {kind: reference(kind) for kind in KINDS}
    binding = binding_of(kernels)
    w = (forward.H + 2 * forward.H_KV) * forward.HEAD

    def entry(name, shape, kind="gemm"):
        kernel = KernelReference((f"/src/{name}.c",), CONTRACTS[kind], ())
        return BindingEntry(kernel, (shape,))

    binding["qkv"] = [entry("q0", (S, D, w)), entry("q1", (1, D, w))]
    if last:
        binding["lm_head"] = [entry("B", (1, D, V))]
    else:
        binding["lm_head"] = [entry("A", (S, D, V)), entry("B", (1, D, V))]
    heads = (forward.H, forward.H_KV, forward.HEAD)
    binding["sdpa"] = [
        entry("s0", (S, S, *heads), "sdpa"),
        entry("s1", (1, S + 1, *heads), "sdpa"),
        entry("s2", (1, S + 2, *heads), "sdpa"),
    ]
    return binding


def test_the_table_follows_the_shape_of_each_pass(recorder, parent):
    result = run_execute(parent, per_shape_binding(last=False))
    assert result.check.ok
    names = recorder.built_names()
    assert names == [
        "q1",
        "q0",
        "gemm",
        "B",
        "A",
        "rmsnorm",
        "add",
        "swiglu",
        "rope",
        "s1",
        "s2",
        "s0",
    ]
    table = recorder.table(G)
    named = {site: [names[index] for index in table[site]] for site in CALL_SITES}
    assert named["qkv"] == ["q0", "q1", "q1"]
    assert named["lm_head"] == ["A", "B", "B"]
    assert named["sdpa"] == ["s0", "s1", "s2"]
    for site in ("o", "gate", "up", "down"):
        assert named[site] == ["gemm"] * G
    for site in CALL_SITES[6:14]:
        assert named[site] == [KIND_OF[site]] * G


def test_lm_head_has_one_row_at_every_pass_for_last(recorder, parent):
    result = run_execute(parent, per_shape_binding(last=True), lm_head_rows="last")
    assert result.check.ok
    names = recorder.built_names()
    table = recorder.table(G)
    assert [names[index] for index in table["lm_head"]] == ["B"] * G
    assert [names[index] for index in table["qkv"]] == ["q0", "q1", "q1"]
    assert recorder.events[-1][4]["lm_head_rows"] == "last"


def test_a_prefill_shape_alone_misses_the_decode_passes(recorder, parent):
    binding = per_shape_binding(last=False)
    binding["sdpa"] = binding["sdpa"][:1]
    result = run_execute(parent, binding)
    assert not result.check.ok
    assert [(o.kind, o.call_site, o.shape[:2]) for o in result.check.outcomes] == [
        (NO_KERNEL, "sdpa", (1, S + 1)),
        (NO_KERNEL, "sdpa", (1, S + 2)),
    ]
    assert recorder.events == []


def wrong_weights(model, field, value):
    return forward_run.weights_of(model)._replace(**{field: value})


@pytest.mark.parametrize(
    ("case", "kind", "text"),
    [
        ("no_kernel", NO_KERNEL, "no entry of the binding covers the shape"),
        ("kernel_unfit", KERNEL_UNFIT, "entry 0: "),
        ("weight_shape", INVALID_INPUT, "weights.norm: has the shape"),
        ("weight_element", INVALID_INPUT, "weights.up[1]: has the element type"),
        ("token", INVALID_INPUT, "given[1]: token id"),
        ("eps", INVALID_INPUT, "eps: "),
        ("rope", INVALID_INPUT, "rope.theta: "),
        ("length", INVALID_INPUT, "given: has 3 token ids, generation_length is 4"),
        ("generated", INVALID_INPUT, "generation_length: must be from 1"),
    ],
)
def test_a_check_that_is_not_ok_builds_and_starts_nothing(
    recorder, parent, case, kind, text
):
    model = forward_run.model_of(42, prompt=S, given=G)
    binding = separate_binding()
    changes = {}
    if case == "no_kernel":
        del binding["ffn_activation"]
    elif case == "kernel_unfit":
        binding["o"] = [BindingEntry(reference("rmsnorm"), "every")]
    elif case == "weight_shape":
        changes["weights"] = wrong_weights(model, "norm", model["norm"][:-1])
    elif case == "weight_element":
        up = [layer["up"] for layer in model["layers"]]
        up[1] = up[1].astype(np.float32)
        changes["weights"] = wrong_weights(model, "up", up)
    elif case == "token":
        changes["given"] = [0, V, 1]
    elif case == "eps":
        changes["eps"] = 0.0
    elif case == "rope":
        changes["rope"] = ROPE._replace(theta=-1.0)
    elif case == "length":
        changes["generation_length"] = G + 1
    else:
        changes["given"] = None
        changes["generation_length"] = 0
    result = run_execute(parent, binding, model, **changes)
    check = expected_check(binding, model, **changes)
    assert result == ForwardExecution(check, None, None, None)
    assert check.ok is False and check.calls == ()
    assert any(
        outcome.kind == kind and outcome.reason.startswith(text)
        for outcome in check.outcomes
    ), check.outcomes
    assert recorder.events == []
    assert os.listdir(parent) == []


def test_every_outcome_of_the_check_comes_back(recorder, parent):
    model = forward_run.model_of(43, prompt=S, given=G)
    binding = separate_binding()
    del binding["rope_k"]
    binding["up"] = [BindingEntry(reference("swiglu"), "every")]
    changes = {"eps": -1.0, "given": [0, 1, V]}
    result = run_execute(parent, binding, model, **changes)
    assert result.check == expected_check(binding, model, **changes)
    kinds = {outcome.kind for outcome in result.check.outcomes}
    assert kinds == {INVALID_INPUT, KERNEL_UNFIT, NO_KERNEL}
    assert recorder.events == []


def test_what_the_check_raises_comes_first(recorder, parent):
    with pytest.raises(TypeError) as caught:
        run_execute(parent, binding=[], prefix="podman")
    assert caught.value.parameter == "binding"
    with pytest.raises(TypeError) as caught:
        run_execute(parent, given="abc")
    assert caught.value.parameter == "given"
    with pytest.raises(TypeError) as caught:
        run_execute(parent, given=None, generation_length="3")
    assert caught.value.parameter == "generation_length"
    with pytest.raises(TypeError) as caught:
        run_execute(parent, generation_length=None)
    assert caught.value.parameter == "generation_length"
    with pytest.raises(TypeError) as caught:
        run_execute(parent, eps=1)
    assert caught.value.parameter == "eps"
    assert recorder.events == []
    assert os.listdir(parent) == []


def test_failed_kernel_build_stops_before_the_rest(monkeypatch, parent):
    made = Recorder(failing_kernel=2).install(monkeypatch)
    result = run_execute(parent)
    assert made.kinds() == ["kernel"] * 3
    assert result.check.ok
    assert result.build_failed == BuildFailed(
        2, build_result(made.events[2][2], ok=False, log="log 2")
    )
    assert result.run is None
    assert result.removed is True
    assert os.listdir(parent) == []


def test_failed_program_build_names_no_kernel(monkeypatch, parent):
    made = Recorder(failing_program=True).install(monkeypatch)
    result = run_execute(parent)
    assert made.kinds() == ["kernel"] * 6 + ["program"]
    assert result.build_failed.kernel is None
    assert result.build_failed.build.log == "program log"
    assert result.run is None
    assert result.removed is True
    assert os.listdir(parent) == []


def test_run_failed_is_returned_unchanged(recorder, parent):
    recorder.run = program_result(RunFailed.TIMEOUT)
    result = run_execute(parent)
    assert result.build_failed is None
    assert result.run is recorder.run
    assert result.removed is True


@pytest.mark.parametrize("stage", ["kernel", "program", "run", "encode"])
def test_what_a_step_raises_reaches_the_caller_after_removal(
    recorder, monkeypatch, parent, stage
):
    error = clang_build.CompilerNotFoundError("no compiler")

    def raising(*args, **options):
        raise error

    if stage == "kernel":
        monkeypatch.setattr(model_build, "build_kernel_library", raising)
    elif stage == "program":
        monkeypatch.setattr(model_build, "build_forward_program", raising)
    elif stage == "encode":
        monkeypatch.setattr(model_forward_run, "encode_input", raising)
    else:
        recorder.run = error
    with pytest.raises(clang_build.CompilerNotFoundError) as caught:
        run_execute(parent)
    assert caught.value is error
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
    assert os.path.isdir(calls[0][0])
    shutil.rmtree(calls[0][0])


def test_defaults_hand_over_empty_flags_and_none(recorder, parent):
    run_execute(parent)
    _, program, options = recorder.events[6]
    assert options == {
        "timeout_s": 30,
        "flags": (),
        "trailing_flags": (),
        "compiler": None,
        "env": None,
    }
    assert recorder.events[0][3]["compiler"] is None
    assert recorder.events[7][1] == program
    assert recorder.events[7][4]["env"] is None


def test_parent_none_uses_the_system_temporary_directory(recorder, monkeypatch, parent):
    monkeypatch.setattr(model_forward_execute.tempfile, "tempdir", str(parent))
    result = run_execute(None)
    directory = os.path.dirname(recorder.events[0][2])
    assert os.path.dirname(directory) == os.path.realpath(parent)
    assert result.removed is True


def test_non_empty_prefix_is_put_in_front(recorder, parent):
    run_execute(parent, prefix=["podman", Path("run")])
    program = recorder.events[6][1]
    assert recorder.events[7][1] == ("podman", "run", program)


def test_program_flags_naming_the_bf16_macro_are_handed_over(recorder, parent):
    flags = ["-DHILCLAW_MODEL_BF16", "-O2"]
    result = run_execute(parent, program_flags=flags)
    assert result.build_failed is None
    assert recorder.events[6][2]["flags"] is flags


@pytest.mark.parametrize(
    "program_flags", ["-O2", None, ("-O2", 3), {"-O2"}, iter(["-O2"]), [b"-O2"]]
)
def test_program_flags_of_the_wrong_type_are_refused(recorder, parent, program_flags):
    with pytest.raises(TypeError, match="^program_flags: must be a tuple or list"):
        run_execute(parent, program_flags=program_flags)
    assert recorder.events == []
    assert os.listdir(parent) == []


@pytest.mark.parametrize(
    ("options", "error", "text"),
    [
        ({"prefix": "podman"}, TypeError, "prefix: must be a sequence"),
        ({"prefix": ["podman", 3]}, TypeError, "prefix[1]: must be str"),
        ({"prefix": ["pod\0man"]}, ValueError, "prefix[0]: holds a NUL"),
        ({"keep_out": "/data"}, TypeError, "keep_out must be a sequence"),
        ({"keep_out": 5}, TypeError, "keep_out: must be a sequence"),
        ({"keep_out": ["/da\0ta"]}, ValueError, "keep_out[0]: holds a NUL"),
    ],
)
def test_refused_prefix_and_keep_out(recorder, parent, options, error, text):
    with pytest.raises(error) as caught:
        run_execute(parent, **options)
    assert str(caught.value).startswith(text)
    assert recorder.events == []
    assert os.listdir(parent) == []


def test_argument_refusals_do_not_wait_for_an_ok_check(recorder, parent):
    with pytest.raises(TypeError, match="^prefix: must be a sequence"):
        run_execute(parent, eps=0.0, prefix=None)
    with pytest.raises(TypeError, match="^program_flags: "):
        run_execute(parent, eps=0.0, program_flags="-O2")


@pytest.mark.parametrize(
    ("value", "error", "text"),
    [
        (3, TypeError, "^parent: must be str"),
        (b"/tmp", TypeError, "^parent: must be str"),
        ("/tmp\0x", ValueError, "^parent: holds a NUL character"),
        (checkout_boundary.PACKAGE_DIRECTORY, ValueError, "^parent: must not be"),
    ],
)
def test_refused_parent(recorder, parent, value, error, text):
    with pytest.raises(error, match=text):
        run_execute(value)
    assert recorder.events == []


def test_parent_named_in_keep_out_is_refused(recorder, parent):
    data = parent / "data"
    data.mkdir()
    with pytest.raises(ValueError, match="^parent: must not be or lie inside"):
        run_execute(data, keep_out=[parent])
    assert os.listdir(data) == []
    assert recorder.events == []


def test_missing_parent_raises_the_os_error(recorder, parent):
    with pytest.raises(FileNotFoundError):
        run_execute(parent / "missing")
    assert recorder.events == []
    assert os.listdir(parent) == []


def test_public_names_and_fields():
    public = {name for name in vars(model_forward_execute) if not name.startswith("_")}
    imported = {
        "os",
        "tempfile",
        "NamedTuple",
        "BuildFailed",
        "model_binding",
        "model_build",
        "model_forward_check",
        "model_forward_run",
    }
    assert public - imported == {"PREFIX", "ForwardExecution", "execute"}
    assert PREFIX == "hilclaw-forward-"
    assert PREFIX != model_execute.PREFIX
    assert ForwardExecution._fields == ("check", "build_failed", "run", "removed")
    assert model_forward_execute.BuildFailed is model_execute.BuildFailed


@pytest.fixture(scope="session")
def clang():
    if os.name != "posix":
        pytest.skip("the forward program needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")


def fixture_kernel(directory, kind, name=None, text=None):
    name = name or kind
    source = directory / f"{name}.c"
    if not source.exists():
        body = text if text is not None else "".join(forward.LIBRARIES[name])
        source.write_text(forward.PRELUDE + body, encoding="ascii", newline="\n")
    return KernelReference((source,), CONTRACTS[kind], forward.KERNEL_FLAGS)


def fixture_binding(directory, **names):
    kernels = {kind: fixture_kernel(directory, kind, names.get(kind)) for kind in KINDS}
    return binding_of(kernels)


def real_execute(tmp_path, binding, model, **changes):
    builds = tmp_path / "builds"
    builds.mkdir()
    result = execute(
        DIMENSIONS,
        binding,
        **model_arguments(model, **changes),
        build_timeout_s=BUILD_TIMEOUT,
        run_timeout_s=RUN_TIMEOUT,
        program_flags=("-O2",),
        program_trailing_flags=("-ldl",),
        parent=builds,
    )
    assert result.check.ok, result.check.outcomes
    assert result.removed is True
    assert os.listdir(builds) == []
    return result


@pytest.mark.parametrize("last", [False, True])
@pytest.mark.parametrize(("seed", "prompt", "given"), [(51, 3, 3), (52, 2, 4)])
def test_a_generation_through_execute_equals_the_recomputation_bit_for_bit(
    clang, tmp_path, last, seed, prompt, given
):
    model = forward_run.model_of(seed, prompt=prompt, given=given)
    rows = "last" if last else "all"
    result = real_execute(tmp_path, fixture_binding(tmp_path), model, lm_head_rows=rows)
    assert result.build_failed is None
    assert result.run.failed is None, result.run.run.stderr
    logits = forward.generate(model, last)
    assert logits.shape == ((given if last else prompt + given - 1), V)
    assert not np.any(logits == forward.NAN_BITS)
    assert np.array_equal(result.run.report.tokens, model["tokens"])
    assert np.array_equal(result.run.report.logits, logits)
    assert result.run.run.stderr == b""


@pytest.mark.parametrize("last", [False, True])
def test_a_greedy_generation_through_execute_equals_the_recomputation(
    clang, tmp_path, last
):
    model = forward_run.model_of(57, prompt=3, given=4)
    rows = "last" if last else "all"
    result = real_execute(
        tmp_path, fixture_binding(tmp_path), model, given=None, lm_head_rows=rows
    )
    assert result.run.failed is None, result.run.run.stderr
    logits, tokens = forward.generate(model, last, select=True)
    assert np.array_equal(result.run.report.tokens, tokens)
    assert np.array_equal(result.run.report.logits, logits)
    assert result.run.run.stderr == b""


def test_a_call_site_with_another_kernel_at_the_decode_passes(clang, tmp_path):
    model = forward_run.model_of(53, prompt=3, given=3)
    binding = fixture_binding(tmp_path)
    plain = binding["lm_head"][0].kernel
    offset = fixture_kernel(tmp_path, "gemm", "gemm_offset")
    binding["lm_head"] = [
        BindingEntry(plain, ((3, D, V),)),
        BindingEntry(offset, ((1, D, V),)),
    ]
    result = real_execute(tmp_path, binding, model)
    assert result.run.failed is None, result.run.run.stderr
    expected = forward.generate(model, lm_start=[0.0, 0.25, 0.25])
    assert np.array_equal(result.run.report.logits, expected)
    assert not np.array_equal(expected, forward.generate(model))


def test_one_source_file_for_every_kind(clang, tmp_path):
    model = forward_run.model_of(54, prompt=2, given=3)
    kernels = {kind: fixture_kernel(tmp_path, kind, "all") for kind in KINDS}
    result = real_execute(tmp_path, binding_of(kernels), model, lm_head_rows="last")
    assert result.run.failed is None, result.run.run.stderr
    assert np.array_equal(result.run.report.logits, forward.generate(model, True))


def test_a_kernel_that_does_not_compile_is_build_failed(clang, tmp_path):
    model = forward_run.model_of(55)
    binding = fixture_binding(tmp_path)
    broken = fixture_kernel(tmp_path, "rope", "broken", "this is not C\n")
    for site in ("rope_q", "rope_k"):
        binding[site] = [BindingEntry(broken, "every")]
    result = real_execute(tmp_path, binding, model)
    assert result.build_failed.kernel == KINDS.index("rope")
    assert result.build_failed.build.ok is False
    assert "error" in result.build_failed.build.log
    assert result.run is None


def test_a_kernel_that_aborts_is_run_failed(clang, tmp_path):
    model = forward_run.model_of(56)
    binding = fixture_binding(tmp_path, swiglu="swiglu_abort")
    result = real_execute(tmp_path, binding, model)
    assert result.build_failed is None
    assert result.run.failed is RunFailed.EXIT_STATUS
    assert result.run.report is None
