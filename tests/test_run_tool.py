import ast
import copy
import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

from hilclaw import (
    build_log,
    events,
    gemm_contract,
    instance,
    keys,
    layout,
    mock_backend,
    mock_run,
    run_admission,
    run_failure,
    run_identity,
    run_objective,
    run_operation,
    run_seed,
    run_state,
    run_tool,
    tools,
)
from hilclaw.backends import Backend, BackendTable
from hilclaw.build_log import HandOverRefused, LogKeeper
from hilclaw.harness.measurement import N_MIN
from hilclaw.journal import EMPTY
from hilclaw.run_parameters import TimingParameters
from hilclaw.run_tool import KIND_BUILD_LOG_UNWRITABLE, tool_function
from hilclaw.tools import ToolFailure

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS = ("sim.run", "board.run")
STEP = {"sim.run": "sim_run_timing_v2", "board.run": "board_run_timing_v2"}

# Test values only: the package defaults to none of them and recommends none.
RUN = "run-a"
ROUND = 3
SEED = 987654321987654321
OTHER_SEED = 123456789123456789
SHAPE = {"m": 2, "k": 3, "n": 4}
CONTRACT_KEY = {"kind": "gemm", "dtype": "fp32", "layout": "row_major"}
N_MAX = 10
FIGURE = 4096
OP = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": SHAPE,
    "dtype": "fp32",
    "layout": "row_major",
}
OBJECTIVE = {"objectives": [{"type": "latency_minimisation"}], "constraints": []}
REQUEST = {"run_id": RUN, "round": ROUND, "candidate": 2, "attempt": 1, "execution": 1}
NUMBERS = {"round": ROUND, "candidate": 2, "attempt": 1}
LOG = "gemm.c:3:5: warning: unused variable ‘x’\r\nline two"
MARKER = "zq7-marker-zq7"
ABSENT = object()
DEFAULT_REPORT = (
    b"resolution_ns 1\n" + b"interval_ns 1000000\n" * N_MIN + b"stop converged\n"
)
CONVERGED = {
    "outcome": "converged",
    "contract_key": CONTRACT_KEY,
    "shape": SHAPE,
    "n_max": N_MAX,
    "sample_form": "interval",
    "unit": "ns",
    "resolution": 1,
    "intervals": [1000000] * N_MIN,
    "ceiling": "not_stated",
}


def profile(accelerator=mock_backend.NAME):
    return {
        "schema_version": 1,
        "accelerator": accelerator,
        "revision": "test-revision",
        "toolchain": {"cc": "test"},
        "host": {"cpu": "test", "os": "test"},
        "hw_source": "external",
    }


def content(op=OP, n_max=N_MAX, objective=OBJECTIVE, accelerator=mock_backend.NAME):
    record = profile(accelerator)
    document = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(record).name, "record": record},
    }
    if op is not ABSENT:
        document["op_signature"] = {"key": keys.op_signature_key(op).name, "record": op}
    if n_max is not ABSENT:
        document["n_max"] = n_max
    if objective is not ABSENT:
        document["objective"] = objective
    return json.dumps(document).encode()


def a_run(root, data=None):
    run = root / "runs" / RUN
    run.mkdir(parents=True, exist_ok=True)
    (run / "instance.json").write_bytes(content() if data is None else data)
    (run / "STATE.json").write_bytes(run_state.dump(ROUND, EMPTY))
    return root


@pytest.fixture
def root(tmp_path):
    return a_run(tmp_path / "data")


def lines(root):
    found = events.read(root, RUN).events
    return [{name: line[name] for name in line if name != "time"} for line in found]


def log_bytes(root):
    path = root / "runs" / RUN / "events.ndjson"
    return path.read_bytes() if path.exists() else b""


def request(**changes):
    return {**REQUEST, **changes}


def attempt_dir(root):
    return layout.attempt_dir(root, RUN, ROUND, "measure", 2, 1)


def log_file(root, tool, execution=1):
    return layout.build_log_file(root, RUN, ROUND, 2, 1, STEP[tool], execution)


def handing(answer, log=LOG):
    def script(tool, asked, hw_profile, parameters, output_path, keeper):
        keeper.hand_over(log)
        if isinstance(answer, BaseException):
            raise answer
        return answer

    return script


class Bench:
    """The tool function of one run tool over a table that holds the mock, with every party recorded."""

    def __init__(
        self,
        root,
        tool="sim.run",
        *,
        script=mock_run.default_script,
        seeds=(SEED,),
        covers=gemm_contract.covers,
        offered=True,
    ):
        self.root, self.tool, self.answer, self.covered = root, tool, script, covers
        self.order, self.asked, self.keepers, self.sources = [], [], [], 0
        self.answers = list(seeds)
        operations = (
            {name: mock_run.operation(name, self.script) for name in TOOLS}
            if offered
            else {}
        )
        self.table = BackendTable([Backend(mock_backend.NAME, operations)])
        self.function = tool_function(
            tool,
            source=self.source,
            table=self.table,
            seeds=self.seeds,
            covers=self.covers,
        )

    def source(self):
        self.sources += 1
        return self.root

    def seeds(self):
        self.order.append("seeds")
        answer = self.answers.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return answer

    def covers(self, record):
        self.order.append("covers")
        return self.covered(record)

    def script(self, tool, asked, hw_profile, parameters, output_path, keeper):
        self.order.append("operation")
        self.asked.append((tool, asked, hw_profile, parameters, output_path))
        self.keepers.append(keeper)
        return self.answer(tool, asked, hw_profile, parameters, output_path, keeper)

    def count(self, name):
        return self.order.count(name)

    def failure(self, asked=None):
        with pytest.raises(ToolFailure) as caught:
            self.function(request() if asked is None else asked)
        assert type(caught.value) is ToolFailure
        return caught.value


def answering(answer):
    def script(tool, asked, hw_profile, parameters, output_path, keeper):
        if isinstance(answer, BaseException):
            raise answer
        return answer

    return script


@pytest.fixture
def stated(monkeypatch):
    """Let a test state an objective no valid file can hold today (ADR-0053 decision 4)."""
    objective = {}
    read = instance.read

    def reading(data_root, run_id):
        found = read(data_root, run_id)
        if "value" in objective:
            found = found._replace(objective=objective["value"])
        return found

    monkeypatch.setattr(instance, "read", reading)
    return objective


def ceiling(bound):
    return {
        "objectives": [{"type": "latency_minimisation"}],
        "constraints": [{"type": "memory_ceiling", "bound": bound}],
    }


def ended(root, tool, outcome):
    step = {"step": STEP[tool], "execution": 1}
    return [
        {"schema_version": 1, "kind": "step_started", **NUMBERS, "data": step},
        {
            "schema_version": 1,
            "kind": "step_ended",
            **NUMBERS,
            "data": {**step, "spend": {}, **outcome},
        },
    ]


# Happy


@pytest.mark.parametrize("tool", TOOLS)
def test_the_default_script_gives_a_converged_result_and_two_lines(root, tool):
    bench = Bench(root, tool)
    asked = request()
    kept = copy.deepcopy(asked)
    result = bench.function(asked)
    assert asked == kept
    assert result == CONVERGED
    assert lines(root) == ended(root, tool, {"result": result})
    ((called, handed, hw_profile, parameters, output_path),) = bench.asked
    assert called == tool
    assert handed is asked
    assert hw_profile == profile()
    assert type(parameters) is TimingParameters
    assert parameters == TimingParameters(
        SHAPE["m"], SHAPE["k"], SHAPE["n"], N_MAX, "interval", SEED
    )
    assert output_path == layout.attempt_artefact(root, RUN, ROUND, 2, 1, "output")
    assert type(output_path) is type(root)
    assert bench.order == ["covers", "seeds", "operation"]
    (keeper,) = bench.keepers
    assert type(keeper) is LogKeeper
    with pytest.raises(HandOverRefused):
        keeper.hand_over("late")
    assert not attempt_dir(root).exists()


def test_board_run_with_the_same_request_is_another_identity(root):
    sim, board = Bench(root, "sim.run"), Bench(root, "board.run")
    assert sim.function(request()) == CONVERGED
    assert board.function(request()) == CONVERGED
    assert [line["data"]["step"] for line in lines(root)] == [
        "sim_run_timing_v2",
        "sim_run_timing_v2",
        "board_run_timing_v2",
        "board_run_timing_v2",
    ]
    assert (sim.count("operation"), board.count("operation")) == (1, 1)


@pytest.mark.parametrize("tool", TOOLS)
def test_the_same_request_again_returns_the_stored_result_and_runs_nothing(root, tool):
    bench = Bench(root, tool)
    first = bench.function(request())
    before = log_bytes(root)
    assert bench.function(request()) == first
    assert log_bytes(root) == before
    assert bench.order == ["covers", "seeds", "operation"]


def test_a_further_execution_runs_again_with_a_new_seed(root):
    bench = Bench(root, seeds=(SEED, OTHER_SEED))
    bench.function(request())
    assert bench.function(request(execution=2)) == CONVERGED
    assert bench.count("operation") == 2
    assert [asked[3].seed for asked in bench.asked] == [SEED, OTHER_SEED]
    assert [line["data"]["execution"] for line in lines(root)] == [1, 1, 2, 2]


# Branch: the judging and the verdict


def report(intervals, state):
    body = b"".join(b"interval_ns %d\n" % interval for interval in intervals)
    return b"resolution_ns 7\n" + body + b"stop " + state + b"\n"


NOT_CONVERGED_REPORT = report([1, 1000] * (N_MAX // 2), b"not_converged")


def test_a_report_that_does_not_converge_is_not_converged(root):
    bench = Bench(root, script=answering((NOT_CONVERGED_REPORT, None)))
    assert bench.function(request()) == {
        **CONVERGED,
        "outcome": "not_converged",
        "resolution": 7,
        "intervals": [1, 1000] * (N_MAX // 2),
    }


@pytest.mark.parametrize("condition", run_operation.CONDITIONS)
@pytest.mark.parametrize("tool", TOOLS)
def test_each_condition_of_the_form_b_gives_a_broken_result(root, tool, condition):
    bench = Bench(root, tool, script=answering(condition))
    result = bench.function(request())
    assert result == {
        "outcome": "broken",
        "condition": condition,
        "contract_key": CONTRACT_KEY,
        "shape": SHAPE,
        "n_max": N_MAX,
        "sample_form": "interval",
        "ceiling": "not_stated",
    }
    assert lines(root) == ended(root, tool, {"result": result})


@pytest.mark.parametrize(
    ("answered", "condition"),
    [
        (b"", "report_form"),
        (b"not a report", "report_form"),
        (DEFAULT_REPORT.replace(b"\n", b"\r\n"), "report_form"),
        (report([1000, 0, 1000, 1000, 1000], b"converged"), "zero_interval"),
        (report([1000] * N_MIN, b"not_converged"), "replay"),
        (report([1000] * (N_MIN + 1), b"converged"), "replay"),
    ],
    ids=["empty", "text", "crlf", "zero", "replay-state", "replay-length"],
)
def test_a_broken_report_gives_the_condition_of_its_judgement(
    root, answered, condition
):
    bench = Bench(root, script=answering((answered, FIGURE)))
    result = bench.function(request())
    assert result["outcome"] == "broken"
    assert result["condition"] == condition
    assert result["contract_key"] == CONTRACT_KEY
    assert result["shape"] == SHAPE
    for name in ("unit", "resolution", "intervals", "memory_bytes"):
        assert name not in result


def test_a_figure_of_a_completed_run_without_a_bound_is_kept_not_stated(root):
    bench = Bench(root, script=answering((DEFAULT_REPORT, FIGURE)))
    assert bench.function(request()) == {**CONVERGED, "memory_bytes": FIGURE}


@pytest.mark.parametrize(
    ("figure", "bound", "verdict"),
    [
        (FIGURE, FIGURE, "within"),
        (FIGURE, FIGURE + 1, "within"),
        (FIGURE, FIGURE - 1, "over"),
        (None, FIGURE, "not_judged"),
    ],
)
def test_with_a_stated_bound_the_verdict_is_computed(
    root, stated, figure, bound, verdict
):
    stated["value"] = ceiling(bound)
    bench = Bench(root, script=answering((DEFAULT_REPORT, figure)))
    result = bench.function(request())
    assert result["ceiling"] == verdict
    assert result["bound"] == bound
    assert ("memory_bytes" in result) is (figure is not None)


def test_a_broken_run_with_a_stated_bound_is_not_judged(root, stated):
    stated["value"] = ceiling(FIGURE)
    bench = Bench(root, script=answering("exit_status"))
    result = bench.function(request())
    assert (result["ceiling"], result["bound"]) == ("not_judged", FIGURE)


def test_the_bound_is_handed_to_no_operation(root, stated):
    stated["value"] = ceiling(FIGURE)
    bench = Bench(root)
    bench.function(request())
    assert str(FIGURE) not in repr(bench.asked)


# Branch: the log


@pytest.mark.parametrize("tool", TOOLS)
@pytest.mark.parametrize(
    "answer",
    [(DEFAULT_REPORT, None), "build_exit_status"],
    ids=["A", "B"],
)
def test_a_handed_log_is_written_at_its_path_and_the_answer_kept(root, tool, answer):
    bench = Bench(root, tool, script=handing(answer))
    result = bench.function(request())
    assert result["outcome"] in ("converged", "broken")
    path = log_file(root, tool)
    assert path.read_bytes() == LOG.encode("utf-8")
    assert path.parent == attempt_dir(root)
    assert path.name == f"build-log-{STEP[tool]}-01.txt"
    assert list(path.parent.iterdir()) == [path]
    assert lines(root)[-1]["data"]["result"] == result


def test_a_handed_log_is_written_with_a_raised_tool_failure(root):
    raised = ToolFailure(run_failure.KIND_BUILD_OUTPUT_MISSING, "no executable")
    bench = Bench(root, script=handing(raised))
    failure = bench.failure()
    assert (failure.kind, failure.message) == (raised.kind, "no executable")
    assert log_file(root, "sim.run").read_bytes() == LOG.encode("utf-8")


def test_a_further_execution_writes_its_own_file(root):
    bench = Bench(root, script=handing("exit_status"), seeds=(SEED, OTHER_SEED))
    bench.function(request())
    bench.function(request(execution=2))
    assert sorted(path.name for path in attempt_dir(root).iterdir()) == [
        "build-log-sim_run_timing_v2-01.txt",
        "build-log-sim_run_timing_v2-02.txt",
    ]


# Error: what the operation raises or returns, and a log that cannot be written


ENDINGS = [
    (ToolFailure(run_failure.KIND_COMPILER_UNAVAILABLE, "no compiler"), None),
    (ToolFailure(tools.KIND_STEP_OPEN, MARKER), "operation_failure_invalid"),
    (ToolFailure(tools.KIND_INVALID_REQUEST, MARKER), "operation_failure_invalid"),
    (ToolFailure(run_seed.KIND_SEED_NOT_DRAWN, MARKER), "operation_failure_invalid"),
    (
        ToolFailure(run_admission.KIND_N_MAX_NOT_STATED, MARKER),
        "operation_failure_invalid",
    ),
    (ToolFailure(KIND_BUILD_LOG_UNWRITABLE, MARKER), "operation_failure_invalid"),
    (ToolFailure("example_kind", MARKER), "operation_failure_invalid"),
    (ValueError(MARKER), "operation_answer_invalid"),
    (RuntimeError(MARKER), "operation_answer_invalid"),
    (None, "operation_answer_invalid"),
    ((DEFAULT_REPORT, 0), "operation_answer_invalid"),
    (MARKER, "operation_answer_invalid"),
]
ENDING_IDS = [
    "backend",
    "step_open",
    "invalid_request",
    "seed_not_drawn",
    "n_max_not_stated",
    "build_log_unwritable",
    "arbitrary",
    "ValueError",
    "RuntimeError",
    "None",
    "zero-figure",
    "string",
]


@pytest.mark.parametrize(("answer", "kind"), ENDINGS, ids=ENDING_IDS)
@pytest.mark.parametrize("tool", TOOLS)
def test_an_answer_with_no_result_ends_the_step_with_its_failure(
    root, tool, answer, kind
):
    bench = Bench(root, tool, script=answering(answer))
    failure = bench.failure()
    if kind is None:
        assert (failure.kind, failure.message) == (answer.kind, answer.message)
    else:
        assert failure.kind == kind
        assert MARKER not in failure.message
    stored = {"failure": {"kind": failure.kind, "message": failure.message}}
    assert lines(root) == ended(root, tool, stored)
    again = bench.failure()
    assert (again.kind, again.message) == (failure.kind, failure.message)
    assert bench.count("operation") == 1
    assert not attempt_dir(root).exists()


def block_by_a_file(root):
    blocker = attempt_dir(root)
    blocker.parent.mkdir(parents=True)
    blocker.write_bytes(b"a file where the attempt directory belongs")


def take_the_name(root):
    path = log_file(root, "sim.run")
    path.parent.mkdir(parents=True)
    path.write_bytes(b"taken")


@pytest.mark.parametrize("spoil", [block_by_a_file, take_the_name])
@pytest.mark.parametrize(
    "answer",
    [(DEFAULT_REPORT, None), "build_exit_status", *(answer for answer, _ in ENDINGS)],
    ids=["A", "B", *ENDING_IDS],
)
def test_a_log_that_cannot_be_written_ends_the_step_in_place_of_any_answer(
    root, spoil, answer
):
    spoil(root)
    bench = Bench(root, script=handing(answer))
    failure = bench.failure()
    assert failure.kind == KIND_BUILD_LOG_UNWRITABLE
    for kept_out in (str(root), LOG, MARKER, str(SEED), "no compiler"):
        assert kept_out not in failure.message
    stored = {"failure": {"kind": failure.kind, "message": failure.message}}
    assert lines(root) == ended(root, "sim.run", stored)


def test_the_kind_of_an_unwritable_log_is_spelt_as_the_checks():
    assert KIND_BUILD_LOG_UNWRITABLE == build_log.KIND_BUILD_LOG_UNWRITABLE
    assert KIND_BUILD_LOG_UNWRITABLE == "build_log_unwritable"
    assert KIND_BUILD_LOG_UNWRITABLE not in tools.RESERVED_KINDS
    assert KIND_BUILD_LOG_UNWRITABLE not in run_failure.BACKEND_KINDS


@pytest.mark.parametrize("ending", [KeyboardInterrupt(), SystemExit(2)])
def test_a_request_to_end_passes_writes_nothing_and_leaves_the_identity_open(
    root, ending
):
    bench = Bench(root, script=handing(ending))
    with pytest.raises(BaseException) as caught:
        bench.function(request())
    assert caught.value is ending
    assert not attempt_dir(root).exists()
    assert [line["kind"] for line in lines(root)] == ["step_started"]
    assert bench.failure().kind == tools.KIND_STEP_OPEN
    assert bench.count("operation") == 1


def test_a_second_hand_over_is_refused_and_let_pass_is_an_invalid_answer(root):
    def twice(tool, asked, hw_profile, parameters, output_path, keeper):
        keeper.hand_over(LOG)
        keeper.hand_over("second")
        return (DEFAULT_REPORT, None)

    bench = Bench(root, script=twice)
    assert bench.failure().kind == "operation_answer_invalid"
    assert log_file(root, "sim.run").read_bytes() == LOG.encode("utf-8")


@pytest.mark.parametrize("log", [LOG.encode(), None, 7])
def test_a_hand_over_that_is_no_text_is_refused_in_the_operation(root, log):
    refused = []

    def offering(tool, asked, hw_profile, parameters, output_path, keeper):
        try:
            keeper.hand_over(log)
        except HandOverRefused as error:
            refused.append(error)
        return "exit_status"

    bench = Bench(root, script=offering)
    assert bench.function(request())["condition"] == "exit_status"
    assert len(refused) == 1
    assert not attempt_dir(root).exists()


# Negative: answered before the start line


@pytest.mark.parametrize(
    "asked",
    [
        request(point="sim"),
        request(extra=1),
        {name: REQUEST[name] for name in REQUEST if name != "execution"},
        {name: REQUEST[name] for name in REQUEST if name != "attempt"},
        request(execution=0),
        request(execution=True),
        "not an object",
    ],
    ids=["point", "sixth", "no-execution", "no-attempt", "zero", "bool", "string"],
)
@pytest.mark.parametrize("tool", TOOLS)
def test_a_refused_request_is_invalid_request_with_no_line(root, tool, asked):
    bench = Bench(root, tool)
    assert bench.failure(asked).kind == tools.KIND_INVALID_REQUEST
    assert log_bytes(root) == b""
    assert bench.sources == 0
    assert bench.order == []


@pytest.mark.parametrize("accelerator", ["cpu_standin", "another_accelerator"])
def test_a_run_at_another_accelerator_is_no_backend(tmp_path, accelerator):
    root = a_run(tmp_path, content(accelerator=accelerator))
    bench = Bench(root)
    assert bench.failure().kind == tools.KIND_NO_BACKEND
    assert log_bytes(root) == b""
    assert bench.order == []


def test_a_table_without_the_operation_is_not_offered(root):
    bench = Bench(root, offered=False)
    assert bench.failure().kind == tools.KIND_NOT_OFFERED
    assert bench.order == []


UNCOVERED_OP = {**OP, "dtype": "fp16"}
NOT_COVERED_OBJECTIVE = {
    "objectives": [{"type": "throughput_maximisation"}],
    "constraints": [],
}


@pytest.mark.parametrize(
    ("changes", "objective", "kind", "covers_asked"),
    [
        (
            {"op": ABSENT, "n_max": ABSENT, "objective": ABSENT},
            None,
            "op_signature_not_stated",
            0,
        ),
        (
            {"op": UNCOVERED_OP, "n_max": ABSENT, "objective": ABSENT},
            None,
            "op_signature_not_covered",
            1,
        ),
        ({"n_max": ABSENT, "objective": ABSENT}, None, "objective_not_stated", 1),
        ({"n_max": ABSENT}, NOT_COVERED_OBJECTIVE, "objective_not_covered", 1),
        ({"n_max": ABSENT}, None, "n_max_not_stated", 1),
    ],
    ids=["no-op", "uncovered-op", "no-objective", "uncovered-objective", "no-n_max"],
)
def test_an_instance_that_is_not_admitted_is_answered_in_order_with_no_seed(
    tmp_path, stated, changes, objective, kind, covers_asked
):
    root = a_run(tmp_path, content(**changes))
    if objective is not None:
        stated["value"] = objective
    bench = Bench(root)
    failure = bench.failure()
    assert failure.kind == kind
    assert kind in run_admission.KINDS
    assert bench.order == ["covers"] * covers_asked
    assert log_bytes(root) == b""
    assert kind in run_objective.KINDS or failure.message.startswith(
        ("op_signature", "n_max")
    )


@pytest.mark.parametrize(
    "seed",
    [RuntimeError(MARKER), ToolFailure("some_kind", MARKER), "1", -1, 2**64, None],
    ids=["error", "failure", "string", "negative", "too-large", "none"],
)
def test_a_source_of_seeds_that_yields_no_seed_is_seed_not_drawn_with_no_line(
    root, seed
):
    bench = Bench(root, seeds=(seed,))
    failure = bench.failure()
    assert failure.kind == run_seed.KIND_SEED_NOT_DRAWN
    assert MARKER not in failure.message
    assert log_bytes(root) == b""
    assert bench.order == ["covers", "seeds"]


def test_a_request_to_end_out_of_the_source_of_seeds_passes_with_no_line(root):
    ending = KeyboardInterrupt()
    bench = Bench(root, seeds=(ending,))
    with pytest.raises(KeyboardInterrupt) as caught:
        bench.function(request())
    assert caught.value is ending
    assert log_bytes(root) == b""


def test_what_covers_raises_passes_through_with_no_line(root):
    def raising(record):
        raise LookupError(MARKER)

    bench = Bench(root, covers=raising)
    with pytest.raises(LookupError):
        bench.function(request())
    assert log_bytes(root) == b""
    assert bench.order == ["covers"]


# The builder


@pytest.mark.parametrize(
    ("tool", "error"),
    [
        ("correctness.check", ValueError),
        ("profiler.collect", ValueError),
        ("sim", ValueError),
        ("SIM.RUN", ValueError),
        (None, TypeError),
        (b"sim.run", TypeError),
        (type("Name", (str,), {})("sim.run"), TypeError),
    ],
)
def test_the_builder_refuses_a_tool_other_than_the_two(tool, error):
    table = BackendTable([])
    with pytest.raises(error):
        tool_function(
            tool, source=lambda: None, table=table, seeds=lambda: 0, covers=bool
        )


@pytest.mark.parametrize("name", ["source", "seeds", "covers"])
def test_the_builder_refuses_a_party_that_is_not_callable(name):
    parties = {"source": lambda: None, "seeds": lambda: 0, "covers": bool}
    parties[name] = "not callable"
    with pytest.raises(TypeError, match=name):
        tool_function("sim.run", table=BackendTable([]), **parties)


def test_the_builder_refuses_a_table_of_another_type():
    with pytest.raises(TypeError, match="BackendTable"):
        tool_function(
            "board.run", source=lambda: None, table={}, seeds=lambda: 0, covers=bool
        )


def test_building_calls_nothing_and_reads_nothing(tmp_path):
    called = []

    def party(*args):
        called.append(args)

    for tool in TOOLS:
        function = tool_function(
            tool, source=party, table=BackendTable([]), seeds=party, covers=party
        )
        assert callable(function)
    assert called == []
    assert list(tmp_path.iterdir()) == []


def test_the_step_of_each_tool_is_its_one_value():
    assert STEP == {tool: run_identity.step_of(tool) for tool in TOOLS}
    assert all(step in layout.BUILD_LOG_STEPS for step in STEP.values())


# The module


def test_the_module_imports_and_names():
    own = Path(run_tool.__file__)
    found = set()
    for node in ast.walk(ast.parse(own.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            found |= {f"{node.module}.{alias.name}" for alias in node.names}
        assert not isinstance(node, ast.Import)
    assert found == {
        f"hilclaw.{name}"
        for name in (
            "build_log",
            "hw_tool",
            "instance",
            "journaled_step",
            "layout",
            "run_admission",
            "run_definition",
            "run_failure",
            "run_identity",
            "run_operation",
            "run_parameters",
            "run_result",
            "run_seed",
            "tools",
        )
    } | {"hilclaw.harness.measurement", "hilclaw.harness.timing"}
    public = {
        name
        for name, value in vars(run_tool).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {"KIND_BUILD_LOG_UNWRITABLE", "tool_function"}
    parameters = inspect.signature(tool_function).parameters
    assert list(parameters) == ["tool", "source", "table", "seeds", "covers"]
    for parameter in parameters.values():
        assert parameter.default is inspect.Parameter.empty
    assert not hasattr(run_tool, "main")


def test_the_tool_is_registered_in_the_default_registry():
    registry = tools.default_registry(lambda: None)
    for tool in TOOLS:
        assert tool in registry.names()


def test_importing_the_run_tool_modules_imports_no_numpy():
    code = (
        "import sys\n"
        "from hilclaw import run_tool, run_operation, mock_run\n"
        "print('numpy' in sys.modules)\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        cwd=REPO_ROOT,
        timeout=60,
        check=False,
    )
    assert (done.returncode, done.stderr, done.stdout.strip()) == (0, b"", b"False")
