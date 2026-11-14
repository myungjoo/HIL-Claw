import os
import shutil
from pathlib import Path

import numpy as np
import pytest
import test_model_forward as forward
import test_model_forward_run as forward_run
import test_model_graph_program as program_tests

from hilclaw import (
    checkout_boundary,
    local_run,
    model_build,
    model_forward_execute,
    model_graph,
    model_graph_execute,
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
from hilclaw.model_graph_execute import (
    PREFIX,
    GraphExecution,
    TimedExecution,
    TimedRun,
    TimedRunFailed,
    execute,
    execute_timed,
)
from hilclaw.model_run import RunFailed

S, G = 3, 3
EPS = float(forward.EPS)


def binding_of(names=None, flags=()):
    names = names or {}
    return {
        site: [
            BindingEntry(
                KernelReference(
                    (names.get(kind, f"/src/{kind}.c"),),
                    program_tests.contract(kind),
                    flags,
                ),
                "every",
            )
        ]
        for site, kind in zip(
            forward.SITES,
            [
                {"add": "elementwise_add", "sdpa": "sdpa_kv_cache"}.get(k, k)
                for k in forward.KIND_OF_SITE
            ],
            strict=True,
        )
    }


def inputs(model=None, **changes):
    model = model or forward_run.model_of(51, prompt=S, given=G)
    tokens = [int(t) for t in model["tokens"]]
    values = {
        "scalars": {"eps": EPS},
        "tables": {"rope": forward_run.ROPE},
        "weights": program_tests.llama_weights(model),
        "prompt": tokens[:S],
        "given": tokens[S:],
        "generation_length": G,
        "lm_head_rows": "all",
    }
    values.update(changes)
    return values


@pytest.fixture
def parent(tmp_path):
    if checkout_boundary.meets_checkout(
        os.path.realpath(tmp_path), [], containing=False
    ):
        pytest.skip("the temporary directory of pytest lies inside the repository")
    return tmp_path


def run_execute(parent, binding=None, graph=None, **options):
    arguments = inputs()
    for name in tuple(options):
        if name in arguments:
            arguments[name] = options.pop(name)
    options.setdefault("build_timeout_s", 30)
    options.setdefault("run_timeout_s", 7)
    return execute(
        program_tests.LLAMA if graph is None else graph,
        program_tests.LLAMA_DIMENSIONS,
        binding_of() if binding is None else binding,
        parent=parent,
        **arguments,
        **options,
    )


class Recorder:
    def __init__(self):
        self.events = []
        self.failing_kernel = None
        self.failing_program = False
        self.result = None

    def kernel_library(self, sources, output, **options):
        index = sum(1 for e in self.events if e[0] == "kernel")
        self.events.append(("kernel", sources, output, options))
        Path(output).write_bytes(b"library")
        return self.build(output, index != self.failing_kernel)

    def graph_program(self, output, **options):
        self.events.append(("program", output, options))
        Path(output).write_bytes(b"program")
        return self.build(output, not self.failing_program)

    def build(self, output, ok):
        return BuildResult(ok, 0 if ok else 1, False, Path(output), "log", ("cc",), 0.1)

    def run(self, command, **options):
        self.events.append(("run", command, options))
        self.input_bytes = Path(command[-1 - len(self.libraries())]).read_bytes()
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result

    def libraries(self):
        return [e for e in self.events if e[0] == "kernel"]

    def kinds(self):
        return [e[0] for e in self.events]


@pytest.fixture
def recorder(monkeypatch):
    recorder = Recorder()
    monkeypatch.setattr(model_build, "build_kernel_library", recorder.kernel_library)
    monkeypatch.setattr(model_build, "build_graph_program", recorder.graph_program)
    monkeypatch.setattr(local_run, "run", recorder.run)
    return recorder


def report_bytes(rows=S + G - 1):
    tokens = np.array(inputs()["prompt"] + inputs()["given"], dtype=np.uint64)
    return tokens.tobytes() + np.zeros(rows * forward.V, np.uint16).tobytes() + b"end\n"


def run_result(returncode=0, timed_out=False, stdout=b""):
    return RunResult(returncode, timed_out, stdout, b"err", ("prog",), 0.2)


def test_module_states_where_it_may_be_used():
    assert "ADR-0182" in model_graph_execute.__doc__
    assert "only for kernels the caller wrote" in model_graph_execute.__doc__
    assert PREFIX == "hilclaw-graph-"


def test_a_run_reads_the_report(parent, recorder):
    recorder.result = run_result(stdout=report_bytes())
    outcome = run_execute(parent)
    assert isinstance(outcome, GraphExecution)
    assert outcome.check.ok and outcome.build_failed is None and outcome.removed
    assert outcome.run.failed is None
    assert outcome.run.report.logits.shape == (S + G - 1, forward.V)
    assert outcome.run.run.stdout == b""
    assert recorder.kinds() == ["kernel"] * 6 + ["program", "run"]
    command = recorder.events[-1][1]
    assert Path(command[0]).name == "model_graph"
    assert Path(command[1]).name == "input.bin"
    assert Path(command[0]).parent.name.startswith(PREFIX)
    assert not Path(command[0]).parent.exists()
    plan = outcome.plan
    check = model_graph.check_binding(plan, binding_of())
    arguments = inputs()
    del arguments["generation_length"], arguments["lm_head_rows"]
    assert recorder.input_bytes == model_graph.encode(plan, check, **arguments)


def test_a_graph_path_and_a_prefix(parent, recorder):
    recorder.result = run_result(stdout=report_bytes(G))
    outcome = run_execute(
        parent,
        graph=model_graph.LLAMA_GRAPH,
        lm_head_rows="last",
        prefix=("env",),
        program_flags=["-O1"],
    )
    assert outcome.run.failed is None
    assert recorder.events[-1][1][0] == "env"
    assert recorder.events[-2][2]["flags"] == ["-O1"]


@pytest.mark.parametrize(
    ("result", "failed"),
    [
        (run_result(timed_out=True, returncode=-9), RunFailed.TIMEOUT),
        (run_result(returncode=7), RunFailed.EXIT_STATUS),
        (run_result(stdout=b"end\n"), RunFailed.REPORT_FORM),
    ],
)
def test_run_failed(parent, recorder, result, failed):
    recorder.result = result
    outcome = run_execute(parent)
    assert outcome.run.failed is failed
    assert outcome.run.report is None
    assert outcome.removed


def test_build_failed_for_a_kernel(parent, recorder):
    recorder.failing_kernel = 1
    outcome = run_execute(parent)
    assert outcome.build_failed.kernel == 1
    assert outcome.run is None and outcome.removed
    assert recorder.kinds() == ["kernel", "kernel"]


def test_build_failed_for_the_program(parent, recorder):
    recorder.failing_program = True
    outcome = run_execute(parent)
    assert outcome.build_failed.kernel is None
    assert outcome.run is None
    assert "run" not in recorder.kinds()


def test_no_kernel(parent, recorder):
    binding = binding_of()
    del binding["sdpa"]
    outcome = run_execute(parent, binding=binding)
    assert not outcome.check.ok
    assert {o.kind for o in outcome.check.outcomes} == {NO_KERNEL}
    assert (outcome.build_failed, outcome.run, outcome.removed) == (None, None, None)
    assert recorder.events == []


def test_kernel_unfit(parent, recorder):
    binding = binding_of()
    binding["norm"] = binding["qkv"]
    outcome = run_execute(parent, binding=binding)
    assert [o.kind for o in outcome.check.outcomes] == [KERNEL_UNFIT]
    assert outcome.check.outcomes[0].call_site == "norm"
    assert recorder.events == []


@pytest.mark.parametrize(
    ("changes", "text"),
    [
        ({"prompt": [0, 1, forward.V]}, "prompt: token id"),
        ({"scalars": {"eps": 0.0}}, "scalars: "),
        ({"given": [0, 1]}, "given: has 2 token ids"),
    ],
)
def test_invalid_input(parent, recorder, changes, text):
    binding = binding_of()
    del binding["o"]
    outcome = run_execute(parent, binding=binding, **changes)
    kinds = [o.kind for o in outcome.check.outcomes]
    assert kinds[0] == INVALID_INPUT and NO_KERNEL in kinds
    assert outcome.check.outcomes[0].reason.startswith(text)
    assert recorder.events == []


@pytest.mark.parametrize(
    ("options", "error"),
    [
        ({"program_flags": "-O2"}, TypeError),
        ({"prefix": "env"}, TypeError),
        ({"given": 3}, TypeError),
        ({"generation_length": 0}, ValueError),
    ],
)
def test_argument_errors_are_raised_before_anything_is_made(
    parent, recorder, options, error
):
    with pytest.raises(error):
        run_execute(parent, **options)
    assert recorder.events == []
    assert not any(p.name.startswith(PREFIX) for p in parent.iterdir())


def test_a_missing_graph_file_is_raised(parent, recorder, tmp_path):
    with pytest.raises(model_graph.GraphFileError):
        run_execute(parent, graph=tmp_path / "missing.json")


def test_what_the_run_raises_is_passed_on_after_removal(parent, recorder):
    recorder.result = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        run_execute(parent)
    assert not any(p.name.startswith(PREFIX) for p in parent.iterdir())


@pytest.fixture(scope="module")
def sources(tmp_path_factory):
    if os.name != "posix":
        pytest.skip("the graph program needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    directory = tmp_path_factory.mktemp("graph-sources")
    names = {}
    for kind, short in program_tests.LIBRARY_OF_KIND.items():
        path = directory / f"{short}.c"
        path.write_text(forward.PRELUDE + forward.KERNEL_SOURCES[short])
        names[kind] = str(path)
    return names


@pytest.mark.parametrize("given", [True, False])
def test_clang_run_equals_the_forward_execution(parent, sources, given):
    binding = binding_of(sources, forward.KERNEL_FLAGS)
    arguments = inputs(**({} if given else {"given": None}))
    options = {
        "build_timeout_s": 120,
        "run_timeout_s": 60,
        "program_trailing_flags": ("-ldl",),
    }
    ours = execute(
        program_tests.LLAMA,
        program_tests.LLAMA_DIMENSIONS,
        binding,
        parent=parent,
        **arguments,
        **options,
    )
    assert ours.run.failed is None, ours.run.run.stderr
    model = forward_run.model_of(51, prompt=S, given=G)
    theirs = model_forward_execute.execute(
        forward_run.DIMENSIONS,
        binding,
        eps=EPS,
        rope=forward_run.ROPE,
        weights=forward_run.weights_of(model),
        prompt=arguments["prompt"],
        given=arguments["given"],
        generation_length=G,
        lm_head_rows="all",
        parent=parent,
        **options,
    )
    assert theirs.run.failed is None
    assert np.array_equal(ours.run.report.tokens, theirs.run.report.tokens)
    assert np.array_equal(ours.run.report.logits, theirs.run.report.logits)
    assert ours.removed


def run_timed(parent, binding=None, graph=None, **options):
    arguments = inputs()
    del arguments["given"], arguments["lm_head_rows"]
    for name in tuple(options):
        if name in arguments:
            arguments[name] = options.pop(name)
    options.setdefault("build_timeout_s", 30)
    options.setdefault("run_timeout_s", 7)
    options.setdefault("repetitions", 3)
    return execute_timed(
        program_tests.LLAMA if graph is None else graph,
        program_tests.LLAMA_DIMENSIONS,
        binding_of() if binding is None else binding,
        parent=parent,
        **arguments,
        **options,
    )


def timed_bytes(start=100, step=10):
    tokens = inputs()["prompt"] + [1, 2, 3]
    readings = [start + step * i for i in range(G + 1)]
    words = np.array([*tokens, *readings, 1], dtype=np.uint64)
    return words.tobytes() + b"end\n"


class Sequence(Recorder):
    def __init__(self, results):
        super().__init__()
        self.results = list(results)

    def run(self, command, **options):
        self.result = self.results.pop(0)
        return super().run(command, **options)


@pytest.fixture
def sequence(monkeypatch):
    def install(results):
        recorder = Sequence(results)
        monkeypatch.setattr(
            model_build, "build_kernel_library", recorder.kernel_library
        )
        monkeypatch.setattr(model_build, "build_graph_program", recorder.graph_program)
        monkeypatch.setattr(local_run, "run", recorder.run)
        return recorder

    return install


@pytest.mark.parametrize("repetitions", [1, 3])
def test_timed_runs_are_new_processes_of_one_input(parent, sequence, repetitions):
    recorder = sequence(
        [run_result(stdout=timed_bytes(100 * r)) for r in range(1, repetitions + 1)]
    )
    outcome = run_timed(parent, repetitions=repetitions)
    assert isinstance(outcome, TimedExecution)
    assert outcome.check.ok and outcome.build_failed is None and outcome.removed
    assert outcome.failed is None
    assert len(outcome.runs) == repetitions
    for r, one in enumerate(outcome.runs, 1):
        assert isinstance(one, TimedRun) and one.failed is None
        assert one.report.intervals == (10,) * G
        assert one.report.readings[0] == 100 * r
        assert one.run.stdout == b""
    assert recorder.kinds() == ["kernel"] * 6 + ["program"] + ["run"] * repetitions
    commands = {tuple(e[1]) for e in recorder.events if e[0] == "run"}
    assert len(commands) == 1
    plan = outcome.plan
    assert all(p.output_rows == 1 for p in plan.passes)
    check = model_graph.check_binding(plan, binding_of())
    arguments = inputs(given=None)
    del arguments["generation_length"], arguments["lm_head_rows"]
    expected = model_graph.encode(plan, check, **arguments, timed=True)
    assert recorder.input_bytes == expected


@pytest.mark.parametrize(
    ("result", "failed"),
    [
        (run_result(timed_out=True, returncode=-9), TimedRunFailed.TIMEOUT),
        (run_result(returncode=7), TimedRunFailed.EXIT_STATUS),
        (run_result(stdout=b"end\n"), TimedRunFailed.REPORT_FORM),
        (run_result(stdout=timed_bytes()[:-1]), TimedRunFailed.REPORT_FORM),
        (run_result(stdout=timed_bytes(step=0)), TimedRunFailed.NOT_INCREASING),
        (run_result(stdout=timed_bytes(step=-1)), TimedRunFailed.NOT_INCREASING),
    ],
)
def test_the_first_failed_run_ends_the_timed_execution(
    parent, sequence, result, failed
):
    good = run_result(stdout=timed_bytes())
    recorder = sequence([good, result, good])
    outcome = run_timed(parent, repetitions=3)
    assert outcome.runs is None
    assert outcome.failed.failed is failed
    assert outcome.failed.report is None
    assert outcome.failed.run.stdout == b""
    assert outcome.removed
    assert recorder.kinds().count("run") == 2


def test_timed_build_failed(parent, sequence):
    recorder = sequence([])
    recorder.failing_program = True
    outcome = run_timed(parent)
    assert outcome.build_failed.kernel is None
    assert (outcome.runs, outcome.failed) == (None, None)
    assert outcome.removed and "run" not in recorder.kinds()


def test_timed_no_kernel_builds_nothing(parent, sequence):
    recorder = sequence([])
    binding = binding_of()
    del binding["sdpa"]
    outcome = run_timed(parent, binding=binding)
    assert {o.kind for o in outcome.check.outcomes} == {NO_KERNEL}
    assert outcome[2:] == (None, None, None, None)
    assert recorder.events == []


def test_timed_invalid_input(parent, sequence):
    recorder = sequence([])
    outcome = run_timed(parent, prompt=[0, 1, forward.V])
    assert outcome.check.outcomes[0].kind == INVALID_INPUT
    assert outcome.check.outcomes[0].reason.startswith("prompt: token id")
    assert outcome[2:] == (None, None, None, None)
    assert recorder.events == []


def test_timed_invalid_input_for_a_graph_of_more_rows(parent, sequence):
    recorder = sequence([])
    text = model_graph.LLAMA_GRAPH.read_text(encoding="utf-8")
    text = text.replace(
        '"logits", "shape": ["R", "V"]', '"logits", "shape": ["T", "V"]'
    )
    text = text.replace('"rows": "R"}', '"rows": "T"}')
    outcome = run_timed(parent, graph=model_graph.read_text(text))
    assert outcome.plan.passes[0].output_rows == S
    assert [o.kind for o in outcome.check.outcomes] == [INVALID_INPUT]
    assert outcome.check.outcomes[0].reason.startswith("timed: ")
    assert outcome[2:] == (None, None, None, None)
    assert recorder.events == []
    assert not any(p.name.startswith(PREFIX) for p in parent.iterdir())


@pytest.mark.parametrize(
    ("repetitions", "error"),
    [
        (0, ValueError),
        (2, ValueError),
        (-1, ValueError),
        (4, ValueError),
        (True, TypeError),
        (3.0, TypeError),
        ("3", TypeError),
        (None, TypeError),
    ],
)
def test_repetitions_are_refused_before_anything_is_built(
    parent, sequence, repetitions, error
):
    recorder = sequence([])
    with pytest.raises(error) as caught:
        run_timed(parent, repetitions=repetitions)
    assert caught.value.parameter == "repetitions"
    assert recorder.events == []
    assert not any(p.name.startswith(PREFIX) for p in parent.iterdir())


@pytest.mark.parametrize(
    ("options", "error"),
    [
        ({"program_flags": "-O2"}, TypeError),
        ({"prompt": [0, 1, 2.0]}, TypeError),
        ({"generation_length": 0}, ValueError),
    ],
)
def test_timed_argument_errors_are_raised_before_anything_is_made(
    parent, sequence, options, error
):
    recorder = sequence([])
    with pytest.raises(error):
        run_timed(parent, **options)
    assert recorder.events == []


def test_what_a_timed_run_raises_is_passed_on_after_removal(parent, sequence):
    sequence([run_result(stdout=timed_bytes()), KeyboardInterrupt()])
    with pytest.raises(KeyboardInterrupt):
        run_timed(parent)
    assert not any(p.name.startswith(PREFIX) for p in parent.iterdir())


@pytest.mark.parametrize("repetitions", [1, 3])
def test_clang_timed_runs_select_the_untimed_tokens(parent, sources, repetitions):
    binding = binding_of(sources, forward.KERNEL_FLAGS)
    arguments = inputs(given=None, lm_head_rows="last")
    options = {
        "build_timeout_s": 120,
        "run_timeout_s": 60,
        "program_trailing_flags": ("-ldl",),
    }
    untimed = execute(
        program_tests.LLAMA,
        program_tests.LLAMA_DIMENSIONS,
        binding,
        parent=parent,
        **arguments,
        **options,
    )
    assert untimed.run.failed is None, untimed.run.run.stderr
    del arguments["given"], arguments["lm_head_rows"]
    timed = execute_timed(
        program_tests.LLAMA,
        program_tests.LLAMA_DIMENSIONS,
        binding,
        parent=parent,
        repetitions=repetitions,
        **arguments,
        **options,
    )
    assert timed.failed is None, timed.failed
    assert len(timed.runs) == repetitions and timed.removed
    tokens = tuple(int(t) for t in untimed.run.report.tokens)
    for one in timed.runs:
        assert one.report.prompt + one.report.tokens == tokens
        assert len(one.report.intervals) == G
        assert one.report.increasing and one.report.resolution >= 0


def test_clang_timed_run_of_a_kernel_that_aborts_is_run_failed(
    parent, sources, tmp_path
):
    source = tmp_path / "swiglu_abort.c"
    source.write_text(
        forward.PRELUDE + "".join(forward.LIBRARIES["swiglu_abort"]), newline="\n"
    )
    binding = binding_of({**sources, "swiglu": str(source)}, forward.KERNEL_FLAGS)
    arguments = inputs()
    del arguments["given"], arguments["lm_head_rows"]
    timed = execute_timed(
        program_tests.LLAMA,
        program_tests.LLAMA_DIMENSIONS,
        binding,
        parent=parent,
        repetitions=3,
        build_timeout_s=120,
        run_timeout_s=60,
        program_trailing_flags=("-ldl",),
        **arguments,
    )
    assert timed.runs is None
    assert timed.failed.failed is TimedRunFailed.EXIT_STATUS
    assert timed.failed.run.returncode != 0
