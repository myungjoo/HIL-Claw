import ast
import builtins
import copy
import inspect
import io
import json
import os
import struct
from pathlib import Path

import pytest

from hilclaw import (
    backends,
    build_log,
    check_admission,
    check_definition,
    check_seed,
    check_tool,
    contract_table,
    events,
    gemm_contract,
    instance,
    journaled_step,
    keys,
    layout,
    mock_backend,
    mock_check,
    run_state,
    tools,
)
from hilclaw.backends import Backend, BackendTable
from hilclaw.check_parameters import Bf16CheckParameters, CheckParameters
from hilclaw.check_tool import tool_function
from hilclaw.journal import EMPTY
from hilclaw.tools import Registry, ToolFailure

# Test values only: the package defaults to none of them and recommends none.
TOOL = "correctness.check"
RUN = "run-a"
FILE = f"runs/{RUN}/instance.json"
ROUND = 3
SEED = 987654321987654321
OTHER_SEED = 123456789123456789
SHAPE = {"m": 2, "k": 3, "n": 4}
DRAWS = 2
TOLERANCE = {"rtol": 0.25, "atol": 3.0}
OP = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": SHAPE,
    "dtype": "fp32",
    "layout": "row_major",
}
REQUEST = {
    "run_id": RUN,
    "round": ROUND,
    "candidate": 2,
    "attempt": 1,
    "execution": 1,
    "point": "sim",
}
ABSENT = object()


def profile(accelerator=mock_backend.NAME):
    return {
        "schema_version": 1,
        "accelerator": accelerator,
        "revision": "test-revision",
        "toolchain": {"cc": "test"},
        "host": {"cpu": "test", "os": "test"},
        "hw_source": "external",
    }


def content(op=OP, draws=DRAWS, tolerance=TOLERANCE, accelerator=mock_backend.NAME):
    record = profile(accelerator)
    document = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(record).name, "record": record},
    }
    if op is not ABSENT:
        document["op_signature"] = {"key": keys.op_signature_key(op).name, "record": op}
    if draws is not ABSENT:
        document["draws"] = draws
    if tolerance is not ABSENT:
        document["tolerance"] = tolerance
    return json.dumps(document).encode()


def place(root, data, relative=FILE):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def a_run(root, run_id=RUN):
    place(root, content(), f"runs/{run_id}/instance.json")
    place(root, run_state.dump(ROUND, EMPTY), f"runs/{run_id}/STATE.json")
    return root


@pytest.fixture
def root(tmp_path):
    return a_run(tmp_path / "data")


def lines(root):
    found = events.read(root, RUN).events
    return [{name: line[name] for name in line if name != "time"} for line in found]


def log_bytes(root):
    path = root / f"runs/{RUN}/events.ndjson"
    return path.read_bytes() if path.exists() else b""


def request(**changes):
    return {**REQUEST, **changes}


FORM = layout.attempt_artefact


def output_of(root, asked):
    numbers = (asked[name] for name in ("run_id", "round", "candidate", "attempt"))
    return FORM(root, *numbers, "output")


def wrong_product(tool, asked, hw_profile, parameters, output_path, keeper):
    report = bytearray(
        mock_check.default_script(
            tool, asked, hw_profile, parameters, output_path, keeper
        )
    )
    (element,) = struct.unpack_from("=f", report, 4)
    struct.pack_into("=f", report, 4, element + 1000.0)
    return bytes(report)


class Bench:
    """The function under test over a table that holds the mock, with every party recorded."""

    def __init__(
        self,
        root,
        *,
        script=mock_check.default_script,
        seeds=(SEED,),
        covers=gemm_contract.covers,
        offered=True,
    ):
        self.root, self.script_answer, self.covered = root, script, covers
        self.order, self.asked, self.sources = [], [], 0
        self.keepers = []
        self.answers = list(seeds)
        operations = {TOOL: mock_check.operation(self.script)} if offered else {}
        self.backend = Backend(mock_backend.NAME, operations)
        self.table = BackendTable([self.backend])
        self.function = tool_function(
            source=self.source, table=self.table, seeds=self.seeds, covers=self.covers
        )

    def source(self):
        self.sources += 1
        if isinstance(self.root, BaseException):
            raise self.root
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
        if isinstance(self.script_answer, BaseException):
            raise self.script_answer
        if callable(self.script_answer):
            return self.script_answer(
                tool, asked, hw_profile, parameters, output_path, keeper
            )
        return self.script_answer

    def count(self, name):
        return self.order.count(name)

    def failure(self, asked=None):
        with pytest.raises(ToolFailure) as caught:
            self.function(request() if asked is None else asked)
        assert type(caught.value) is ToolFailure
        return caught.value


@pytest.fixture
def recorded(monkeypatch):
    """Record the reads of ``instance.json``, the selections and the appends in ``order``."""
    order = []
    read, select, append = instance.read, backends.select, events.append

    def recording_read(data_root, run_id):
        order.append("read")
        return read(data_root, run_id)

    def recording_select(table, hw_profile, tool):
        order.append("select")
        return select(table, hw_profile, tool)

    def recording_append(data_root, run_id, kind, data, **numbers):
        order.append(kind)
        return append(data_root, run_id, kind, data, **numbers)

    monkeypatch.setattr(instance, "read", recording_read)
    monkeypatch.setattr(backends, "select", recording_select)
    monkeypatch.setattr(events, "append", recording_append)
    return order


@pytest.fixture
def formed(monkeypatch):
    """Record every path of an attempt's artefact that is formed."""
    paths = []

    def recording_form(*args):
        paths.append(FORM(*args))
        return paths[-1]

    monkeypatch.setattr(layout, "attempt_artefact", recording_form)
    return paths


def test_a_check_of_a_right_product_reports_pass_and_writes_two_lines(root):
    bench = Bench(root)
    asked = request()
    kept = copy.deepcopy(asked)
    result = bench.function(asked)
    assert asked == kept
    assert result == {
        "outcome": "pass",
        "shape": SHAPE,
        "draws": DRAWS,
        "tolerance": TOLERANCE,
        "counts": [{"failed": 0, "non_finite": 0}] * DRAWS,
    }
    numbers = {"round": ROUND, "candidate": 2, "attempt": 1}
    step = {"step": "correctness_check_sim", "execution": 1}
    assert lines(root) == [
        {"schema_version": 1, "kind": "step_started", **numbers, "data": step},
        {
            "schema_version": 1,
            "kind": "step_ended",
            **numbers,
            "data": {**step, "spend": {}, "result": result},
        },
    ]
    ((tool, handed, hw_profile, parameters, output_path),) = bench.asked
    assert tool == TOOL
    assert handed is asked
    assert hw_profile == profile()
    assert type(parameters) is CheckParameters
    assert parameters == CheckParameters(SEED, DRAWS, **SHAPE)
    assert output_path == root / "runs" / RUN / "rounds" / "0003" / "coder" / (
        "candidates/02/attempts/01/output"
    )
    assert (bench.sources, bench.count("seeds"), bench.count("covers")) == (1, 1, 1)
    (keeper,) = bench.keepers
    assert type(keeper) is build_log.LogKeeper


NUMBERS = [
    {},
    {"round": 0, "candidate": 1, "attempt": 1},
    {"round": 12345, "candidate": 7, "attempt": 123},
    {name: keys.MAX_INTEGER for name in ("round", "candidate", "attempt")},
]


@pytest.mark.parametrize("numbers", NUMBERS, ids=["example", "least", "padded", "most"])
@pytest.mark.parametrize("point", ["sim", "board"])
def test_the_script_is_handed_the_path_of_the_output_of_the_attempt(
    root, formed, point, numbers
):
    bench = Bench(root)
    asked = request(point=point, **numbers)
    rounds = root / "runs" / RUN / "rounds"
    assert not rounds.exists()
    assert bench.function(asked)["outcome"] == "pass"
    assert not rounds.exists()
    ((*_, output_path),) = bench.asked
    assert output_path == output_of(root, asked)
    assert type(output_path) is type(root)
    assert formed == [output_path]
    assert formed[0] is output_path
    assert output_path.name == "output"
    assert output_path.parents[4].name == "coder"
    assert output_path.is_relative_to(rounds)


def test_the_padding_of_the_path_is_that_of_the_layout(root):
    bench = Bench(root, seeds=(SEED, OTHER_SEED))
    bench.function(request(round=0, candidate=7, attempt=123))
    bench.function(request(round=12345, candidate=7, attempt=123))
    below = root / "runs" / RUN / "rounds"
    assert [asked[4] for asked in bench.asked] == [
        below / "0000" / "coder" / "candidates" / "07" / "attempts" / "123" / "output",
        below / "12345" / "coder" / "candidates" / "07" / "attempts" / "123" / "output",
    ]


def test_the_longest_run_id_forms_a_path(tmp_path):
    run_id = "r" * 64
    bench = Bench(a_run(tmp_path, run_id))
    asked = request(run_id=run_id)
    assert bench.function(asked)["outcome"] == "pass"
    assert bench.asked[0][4] == output_of(tmp_path, asked)


def test_the_data_root_of_the_path_is_the_one_of_the_call_as_it_is(root):
    (root / "sub").mkdir()
    unresolved = root / "sub" / ".."
    bench = Bench(unresolved)
    assert bench.function(request())["outcome"] == "pass"
    output_path = bench.asked[0][4]
    assert output_path == output_of(unresolved, request())
    assert ".." in output_path.parts
    assert output_path != output_of(root, request())


def test_requests_that_differ_in_the_point_or_the_execution_are_handed_equal_paths(
    root,
):
    bench = Bench(root, seeds=(SEED, OTHER_SEED, SEED))
    for asked in (request(), request(point="board"), request(execution=2)):
        bench.function(asked)
    first, second, third = (asked[4] for asked in bench.asked)
    assert first == second == third == output_of(root, request())
    other = Bench(root, seeds=(SEED,))
    other.function(request(attempt=2))
    assert other.asked[0][4] != first


def test_a_frame_accepted_request_is_one_the_layout_forms_a_path_for(root, formed):
    for name, least in (("round", 0), ("candidate", 1), ("attempt", 1)):
        for value in (least - 1, keys.MAX_INTEGER + 1, True, "1", 1.0, None):
            bench = Bench(root, seeds=())
            failure = bench.failure(request(**{name: value}))
            assert failure.kind == tools.KIND_INVALID_REQUEST
            assert name in failure.message
            with pytest.raises(layout.InvalidPathValueError):
                output_of(root, request(**{name: value}))
        for value in (least, keys.MAX_INTEGER):
            assert output_of(root, request(**{name: value})).name == "output"
    for run_id in ("", "R", "a/b", "..", "r" * 65, 7, None):
        failure = Bench(root, seeds=()).failure(request(run_id=run_id))
        assert failure.kind == tools.KIND_INVALID_REQUEST
        with pytest.raises(layout.InvalidPathValueError):
            output_of(root, request(run_id=run_id))
    assert formed == []
    assert lines(root) == []


def below_the_rounds(root, monkeypatch):
    """Make every look at the file system below ``rounds`` of the run fail."""
    rounds = os.path.join(str(root), "runs", RUN, "rounds")
    looked = []

    def guarded(function):
        def guard(path, *args, **kwargs):
            try:
                name = os.fspath(path)
            except TypeError:
                name = ""
            if isinstance(name, bytes):
                name = os.fsdecode(name)
            if name and os.path.abspath(name).startswith(rounds):
                looked.append(name)
                raise AssertionError(f"looked at {name}")
            return function(path, *args, **kwargs)

        return guard

    for name in ("stat", "lstat", "listdir", "scandir", "open", "readlink"):
        monkeypatch.setattr(os, name, guarded(getattr(os, name)))
    for name in ("exists", "lexists", "isdir", "isfile", "islink"):
        monkeypatch.setattr(os.path, name, guarded(getattr(os.path, name)))
    for module in (builtins, io):
        monkeypatch.setattr(module, "open", guarded(module.open))
    return looked


SCRIPTS = [
    mock_check.default_script,
    wrong_product,
    "time_limit",
    "exit_status",
    "build_time_limit",
    "build_exit_status",
    17,
]


@pytest.mark.parametrize("script", SCRIPTS)
@pytest.mark.parametrize("lies", ["a_kernel", "a_file_for_the_attempt"])
def test_a_call_is_answered_alike_whatever_lies_at_the_output_path(
    tmp_path, monkeypatch, script, lies
):
    def answer_in(name, prepare):
        root = a_run(tmp_path / name / "data")
        prepare(root)
        bench = Bench(root, script=script)
        with monkeypatch.context() as patch:
            looked = below_the_rounds(root, patch)
            try:
                answer = bench.function(request())
            except ToolFailure as failure:
                answer = (failure.kind, failure.message)
        assert looked == []
        return answer, lines(root), bench.asked[0][4]

    def a_kernel(root):
        place(output_of(root, request()), b"int kernel;\n", "kernel.c")

    def a_file_for_the_attempt(root):
        attempt = output_of(root, request()).parent
        place(attempt.parent, b"no directory", attempt.name)

    prepare = {"a_kernel": a_kernel, "a_file_for_the_attempt": a_file_for_the_attempt}
    bare, bare_lines, bare_path = answer_in("bare", lambda root: None)
    assert bare_path.parents[6].name == "rounds"
    assert not bare_path.parents[6].exists()
    answer, written, output_path = answer_in(lies, prepare[lies])
    assert (answer, written) == (bare, bare_lines)
    assert output_path.relative_to(tmp_path / lies) == bare_path.relative_to(
        tmp_path / "bare"
    )
    if lies == "a_kernel":
        assert [entry.name for entry in output_path.iterdir()] == ["kernel.c"]
    else:
        assert output_path.parent.read_bytes() == b"no directory"


def test_a_wrong_product_reports_fail(root):
    result = Bench(root, script=wrong_product).function(request())
    assert result["outcome"] == "fail"
    assert result["counts"][0]["failed"] >= 1
    assert "condition" not in result
    assert lines(root)[1]["data"]["spend"] == {}


@pytest.mark.parametrize(
    "condition", ["time_limit", "exit_status", "build_time_limit", "build_exit_status"]
)
def test_a_condition_of_the_operation_reports_broken(root, condition):
    result = Bench(root, script=condition).function(request())
    assert result == {
        "outcome": "broken",
        "condition": condition,
        "shape": SHAPE,
        "draws": DRAWS,
        "tolerance": TOLERANCE,
    }
    assert lines(root)[1]["data"] == {
        "step": "correctness_check_sim",
        "execution": 1,
        "spend": {},
        "result": result,
    }
    before = log_bytes(root)
    again = Bench(root, seeds=(), script=RuntimeError("must not be asked"))
    assert again.function(request()) == result
    assert (again.asked, log_bytes(root)) == ([], before)


def test_the_order_of_a_call(root, recorded):
    bench = Bench(root)
    bench.order = recorded
    bench.function(request())
    # The first read is that of the layout version stamp, the second the one read of moment 4.
    assert recorded == [
        "read",
        "read",
        "select",
        "covers",
        "seeds",
        "step_started",
        "operation",
        "step_ended",
    ]


def test_the_two_points_are_two_identities_each_with_its_own_draw(root):
    bench = Bench(root, seeds=(SEED, OTHER_SEED))
    sim = bench.function(request(point="sim"))
    board = bench.function(request(point="board"))
    assert sim["outcome"] == board["outcome"] == "pass"
    written = lines(root)
    assert [line["kind"] for line in written] == ["step_started", "step_ended"] * 2
    assert [line["data"]["step"] for line in written] == [
        "correctness_check_sim",
        "correctness_check_sim",
        "correctness_check_board",
        "correctness_check_board",
    ]
    assert [asked[3].seed for asked in bench.asked] == [SEED, OTHER_SEED]
    assert bench.count("seeds") == 2


def test_an_ended_identity_is_answered_from_the_log_and_nothing_is_asked(
    root, recorded, formed
):
    first = Bench(root)
    result = first.function(request())
    before = log_bytes(root)
    del recorded[:]
    assert len(formed) == 1
    second = Bench(root, seeds=(), script=RuntimeError("must not be asked"))
    second.order = recorded
    assert second.function(request()) == result
    # The one read is that of the layout version stamp.
    assert recorded == ["read"]
    assert log_bytes(root) == before
    assert (second.asked, len(formed)) == ([], 1)


def test_an_open_identity_is_step_open_and_nothing_is_asked(root, recorded):
    interrupted = Bench(root, script=KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        interrupted.function(request())
    assert [line["kind"] for line in lines(root)] == ["step_started"]
    before = log_bytes(root)
    del recorded[:]
    bench = Bench(root, seeds=())
    bench.order = recorded
    assert bench.failure().kind == tools.KIND_STEP_OPEN
    assert recorded == ["read"]
    assert log_bytes(root) == before


def test_a_further_execution_is_carried_out_in_full_with_a_fresh_draw(root, recorded):
    bench = Bench(root, seeds=(SEED, OTHER_SEED))
    bench.order = recorded
    bench.function(request())
    del recorded[:]
    assert bench.function(request(execution=2))["outcome"] == "pass"
    assert recorded == [
        "read",
        "read",
        "select",
        "covers",
        "seeds",
        "step_started",
        "operation",
        "step_ended",
    ]
    assert [asked[3].seed for asked in bench.asked] == [SEED, OTHER_SEED]
    assert [line["data"]["execution"] for line in lines(root)] == [1, 1, 2, 2]


@pytest.mark.parametrize(
    "asked,member",
    [
        ({name: REQUEST[name] for name in REQUEST if name != "point"}, "point"),
        (request(point="Sim"), "point"),
        (request(point="sim.run"), "point"),
        (request(point=1), "point"),
        (request(point=None), "point"),
        ({name: REQUEST[name] for name in REQUEST if name != "run_id"}, "run_id"),
        ({name: REQUEST[name] for name in REQUEST if name != "execution"}, "execution"),
        ({name: REQUEST[name] for name in REQUEST if name != "attempt"}, "attempt"),
        ({name: REQUEST[name] for name in REQUEST if name != "round"}, "round"),
    ],
)
def test_a_refused_request_is_invalid_request_before_anything_is_asked(
    root, recorded, formed, asked, member
):
    bench = Bench(root, seeds=())
    bench.order = recorded
    failure = bench.failure(asked)
    assert failure.kind == tools.KIND_INVALID_REQUEST
    assert member in failure.message
    assert (bench.sources, recorded, lines(root)) == (0, [], [])
    assert (bench.asked, formed) == ([], [])


def without_point(**changes):
    return {**{name: REQUEST[name] for name in REQUEST if name != "point"}, **changes}


@pytest.mark.parametrize(
    "asked,start",
    [
        (request(draws=1000), "draws: "),
        (request(seed=7), "seed: "),
        (request(tolerance={"rtol": 0.1}), "tolerance: "),
        (request(m=1), "m: "),
        (request(draws=None), "draws: "),
        (without_point(Point="sim"), "Point: "),
        (request(execution=1.0), "execution"),
        (request(execution=json.loads("1e0")), "execution"),
        (request(round=3.0), "round"),
        (request(point="Sim"), "point: "),
    ],
    ids=[
        "draws",
        "seed",
        "tolerance",
        "m",
        "null",
        "Point",
        "1.0",
        "1e0",
        "round",
        "Sim",
    ],
)
def test_each_refusal_of_the_walk_through_is_made_before_anything_is_asked(
    root, recorded, formed, asked, start
):
    kept = copy.deepcopy(asked)
    bench = Bench(root, seeds=())
    bench.order = recorded
    failure = bench.failure(asked)
    assert failure.kind == tools.KIND_INVALID_REQUEST
    assert failure.message.startswith(start)
    assert "1000" not in failure.message and "rtol" not in failure.message
    assert (bench.sources, recorded, lines(root), log_bytes(root)) == (0, [], [], b"")
    assert (bench.asked, formed) == ([], [])
    assert asked == kept


def test_an_unnamed_member_after_an_ended_call_is_refused_not_answered(root, recorded):
    first = Bench(root)
    result = first.function(request())
    before = log_bytes(root)
    del recorded[:]
    again = Bench(root, seeds=(), script=RuntimeError("must not be asked"))
    again.order = recorded
    assert again.function(request()) == result
    assert recorded == ["read"]
    del recorded[:]
    failure = again.failure(request(draws=1000))
    assert failure.kind == tools.KIND_INVALID_REQUEST
    assert failure.message.startswith("draws: ")
    assert (again.sources, recorded, again.asked) == (1, [], [])
    assert log_bytes(root) == before


def test_the_frame_is_checked_before_the_point(root):
    asked = {name: REQUEST[name] for name in REQUEST if name not in ("run_id", "point")}
    failure = Bench(root).failure(asked)
    assert failure.kind == tools.KIND_INVALID_REQUEST
    assert "run_id" in failure.message


def test_a_failing_data_root_source_is_no_data_root(recorded):
    bench = Bench(RuntimeError("no root"), seeds=())
    bench.order = recorded
    assert bench.failure().kind == tools.KIND_NO_DATA_ROOT
    assert (bench.sources, recorded) == (1, [])


def test_a_missing_instance_file_is_answered_at_the_stamp(root, recorded, formed):
    (root / FILE).unlink()
    bench = Bench(root, seeds=())
    bench.order = recorded
    failure = bench.failure()
    assert failure.kind == tools.KIND_RUN_FILE_MISSING
    assert failure.message.startswith(FILE)
    assert (recorded, lines(root)) == (["read"], [])
    assert (bench.asked, formed) == ([], [])


def test_a_file_that_is_invalid_at_the_one_read_is_answered_there(root, monkeypatch):
    order, read = [], instance.read

    def second_read_finds_damage(data_root, run_id):
        order.append("read")
        if len(order) == 2:
            place(root, b"{")
        return read(data_root, run_id)

    monkeypatch.setattr(instance, "read", second_read_finds_damage)
    bench = Bench(root, seeds=())
    bench.order = order
    failure = bench.failure()
    assert failure.kind == tools.KIND_RUN_FILE_INVALID
    assert failure.message.startswith(FILE)
    assert (order, lines(root)) == (["read", "read"], [])


def test_no_backend_is_answered_before_covers_and_the_draw(root, recorded):
    place(root, content(accelerator="acc_b"))
    bench = Bench(root, seeds=())
    bench.order = recorded
    assert bench.failure().kind == tools.KIND_NO_BACKEND
    assert (recorded, lines(root)) == (["read", "read", "select"], [])


def test_not_offered_is_answered_before_covers_and_the_draw(root, recorded):
    bench = Bench(root, seeds=(), offered=False)
    bench.order = recorded
    assert bench.failure().kind == tools.KIND_NOT_OFFERED
    assert (recorded, lines(root)) == (["read", "read", "select"], [])


NOT_COVERED = {**OP, "dtype": "fp16"}
ONE_FAULT = [
    {"op": ABSENT},
    {"op": NOT_COVERED},
    {"draws": ABSENT},
    {"tolerance": ABSENT},
]
ADMISSION = [
    *zip(ONE_FAULT, check_admission.KINDS, strict=True),
    ({"op": ABSENT, "draws": ABSENT, "tolerance": ABSENT}, "op_signature_not_stated"),
    ({"op": NOT_COVERED, "draws": ABSENT}, "op_signature_not_covered"),
    ({"draws": ABSENT, "tolerance": ABSENT}, "draws_not_stated"),
]


@pytest.mark.parametrize("faults,kind", ADMISSION)
def test_an_answer_of_the_admission_leaves_no_line_and_asks_no_seed(
    root, recorded, formed, faults, kind
):
    place(root, content(**faults))
    bench = Bench(root)
    bench.order = recorded
    assert bench.failure().kind == kind
    assert bench.failure().kind == kind
    assert "seeds" not in recorded
    assert "operation" not in recorded
    assert "step_started" not in recorded
    assert lines(root) == []
    assert (bench.asked, formed) == ([], [])
    place(root, content())
    assert bench.function(request())["outcome"] == "pass"
    assert bench.count("seeds") == 1
    assert [line["data"]["execution"] for line in lines(root)] == [1, 1]


def test_what_covers_raises_passes_through_with_no_line(root):
    error = RuntimeError("covers failed")

    def covers(record):
        raise error

    bench = Bench(root, covers=covers)
    with pytest.raises(RuntimeError) as caught:
        bench.function(request())
    assert caught.value is error
    assert (bench.count("seeds"), bench.asked, lines(root)) == (0, [], [])


@pytest.mark.parametrize(
    "answer", [RuntimeError(str(SEED)), "no seed", -1, 2**64, True, None, float(7)]
)
def test_a_draw_that_yields_no_seed_is_seed_not_drawn_and_can_be_repeated(
    root, recorded, formed, answer
):
    bench = Bench(root, seeds=(answer, SEED))
    bench.order = recorded
    failure = bench.failure()
    assert failure.kind == check_seed.KIND_SEED_NOT_DRAWN == "seed_not_drawn"
    assert failure.__cause__ is None
    assert str(SEED) not in failure.message
    assert recorded == ["read", "read", "select", "covers", "seeds"]
    assert (bench.asked, lines(root), formed) == ([], [], [])
    assert bench.function(request())["outcome"] == "pass"
    assert bench.count("seeds") == 2
    assert bench.asked[0][3].seed == SEED
    assert [line["data"]["execution"] for line in lines(root)] == [1, 1]


def test_a_request_to_end_out_of_the_seed_source_passes_through_with_no_line(root):
    interrupt = KeyboardInterrupt()
    bench = Bench(root, seeds=(interrupt, SEED))
    with pytest.raises(KeyboardInterrupt) as caught:
        bench.function(request())
    assert caught.value is interrupt
    assert (bench.asked, lines(root)) == ([], [])
    assert bench.function(request())["outcome"] == "pass"


def a_path_in_a_tool_failure(tool, asked, hw_profile, parameters, output_path, keeper):
    raise ToolFailure("example_kind", f"nothing lies at {output_path}")


def a_path_in_an_error(tool, asked, hw_profile, parameters, output_path, keeper):
    raise FileNotFoundError(2, "No such file or directory", str(output_path))


def a_path_in_a_backend_kind(tool, asked, hw_profile, parameters, output_path, keeper):
    raise ToolFailure("no_kernel_source", f"nothing lies at {output_path}")


# The two names as ADR-0056 decision 6 spells them.
THE_TWO = ["no_kernel_source", "kernel_source_unreadable"]
# The six names as ADR-0060 decision 4 spells them.
THE_SIX = [
    "build_directory_unusable",
    "settings_refused",
    "build_input_missing",
    "compiler_unavailable",
    "build_output_missing",
    "executable_unstartable",
]
THE_EIGHT = [*THE_TWO, *THE_SIX]
RAISED = "raised by a script"
OUTSIDE = "operation_failure_invalid"
# The third member says whether the message is the raised one; else this side composed it.
ENDINGS = [
    (17, "operation_answer_invalid", False),
    (ToolFailure("example_kind", RAISED), OUTSIDE, False),
    (ToolFailure("seed_not_drawn", RAISED), OUTSIDE, False),
    (ToolFailure("step_open", RAISED), OUTSIDE, False),
    (ToolFailure("no_kernel_sources", RAISED), OUTSIDE, False),
    (ToolFailure("operation_failure_invalid", RAISED), OUTSIDE, False),
    (ToolFailure("no_kernel_source", RAISED), "no_kernel_source", True),
    (
        ToolFailure("kernel_source_unreadable", RAISED),
        "kernel_source_unreadable",
        True,
    ),
    *[(ToolFailure(kind, RAISED), kind, True) for kind in THE_SIX],
    (ToolFailure("settings_refuse", RAISED), OUTSIDE, False),
    (ToolFailure("executable_unstartables", RAISED), OUTSIDE, False),
    (ToolFailure("build_exit_status", RAISED), OUTSIDE, False),
    (ToolFailure("build_time_limit", RAISED), OUTSIDE, False),
    (a_path_in_a_tool_failure, OUTSIDE, False),
    (a_path_in_an_error, "operation_answer_invalid", False),
]


@pytest.mark.parametrize("script,kind,as_raised", ENDINGS)
def test_a_check_without_an_outcome_ends_the_step_with_that_failure(
    root, script, kind, as_raised
):
    bench = Bench(root, script=script)
    failure = bench.failure()
    assert failure.kind == kind
    assert (failure.message == RAISED) is as_raised
    assert (RAISED in failure.message) is as_raised
    started, ended = lines(root)
    assert started["data"] == {"step": "correctness_check_sim", "execution": 1}
    assert ended["data"] == {
        "step": "correctness_check_sim",
        "execution": 1,
        "spend": {},
        "failure": {"kind": kind, "message": failure.message},
    }
    assert ended["data"]["failure"]["message"] == failure.message
    for word in (str(root), root.as_posix(), root.parent.name, "rounds", "candidates"):
        assert word not in failure.message
        assert word.encode() not in log_bytes(root)
    assert failure.__cause__ is None
    before = log_bytes(root)
    again = Bench(root, seeds=(), script=RuntimeError("must not be asked"))
    repeated = again.failure()
    assert (repeated.kind, repeated.message) == (kind, failure.message)
    assert (again.asked, again.order, log_bytes(root)) == ([], [], before)


@pytest.mark.parametrize("point", ["sim", "board"])
@pytest.mark.parametrize("kind", THE_EIGHT)
def test_a_backend_kind_a_script_raises_is_the_failure_of_the_end_line(
    root, recorded, kind, point
):
    asked = request(point=point)
    bench = Bench(root, script=ToolFailure(kind, RAISED))
    failure = bench.failure(asked)
    assert (failure.kind, failure.message) == (kind, RAISED)
    assert failure.__cause__ is None
    assert bench.count("operation") == 1
    started, ended = lines(root)
    assert started["kind"] == "step_started"
    assert ended["data"] == {
        "step": f"correctness_check_{point}",
        "execution": 1,
        "spend": {},
        "failure": {"kind": kind, "message": RAISED},
    }
    before = log_bytes(root)
    del recorded[:]
    again = Bench(root, seeds=(), script=RuntimeError("must not be asked"))
    again.order = recorded
    repeated = again.failure(asked)
    assert (repeated.kind, repeated.message) == (kind, RAISED)
    # The one read is that of the layout version stamp.
    assert recorded == ["read"]
    assert (again.asked, log_bytes(root)) == ([], before)
    further = Bench(root).function(request(point=point, execution=2))
    assert further["outcome"] == "pass"
    assert [line["data"]["execution"] for line in lines(root)] == [1, 1, 2, 2]


def test_a_backend_kind_whose_message_shows_the_output_path_is_not_detected(root):
    bench = Bench(root, script=a_path_in_a_backend_kind)
    failure = bench.failure()
    shown = f"nothing lies at {output_of(root, request())}"
    assert str(root) in shown
    assert (failure.kind, failure.message) == ("no_kernel_source", shown)
    assert lines(root)[1]["data"]["failure"] == {
        "kind": "no_kernel_source",
        "message": shown,
    }
    again = Bench(root, seeds=(), script=RuntimeError("must not be asked"))
    assert again.failure().message == shown
    assert again.asked == []


def test_the_default_script_raises_no_backend_kind(root):
    bench = Bench(root, seeds=(SEED, SEED))
    assert bench.function(request())["outcome"] == "pass"
    assert bench.function(request(point="board"))["outcome"] == "pass"
    assert b"kernel_source" not in log_bytes(root)
    for kind in THE_SIX:
        assert kind.encode() not in log_bytes(root)


def test_a_request_to_end_out_of_the_operation_leaves_the_identity_open(root):
    interrupt = KeyboardInterrupt()
    bench = Bench(root, script=interrupt)
    with pytest.raises(KeyboardInterrupt) as caught:
        bench.function(request())
    assert caught.value is interrupt
    assert [line["kind"] for line in lines(root)] == ["step_started"]
    assert Bench(root, seeds=()).failure().kind == tools.KIND_STEP_OPEN


@pytest.mark.parametrize(
    "refused",
    [
        ValueError("refused on this side"),
        ToolFailure("example_kind", "raised on this side, not by the operation"),
    ],
)
def test_an_error_of_this_side_passes_through_and_leaves_the_identity_open(
    root, monkeypatch, refused
):
    def refuse(*args, **kwargs):
        raise refused

    bench = Bench(root)
    with monkeypatch.context() as patch:
        patch.setattr(check_seed, "check", refuse)
        with pytest.raises(type(refused)) as caught:
            bench.function(request())
    assert caught.value is refused
    assert bench.asked == []
    assert [line["kind"] for line in lines(root)] == ["step_started"]
    assert bench.failure().kind == tools.KIND_STEP_OPEN


def test_a_failed_start_line_after_the_draw_hands_the_seed_to_no_operation(
    root, monkeypatch
):
    append = events.append

    def failing(data_root, run_id, kind, data, **numbers):
        if kind == "step_started":
            raise OSError("the disk is full")
        return append(data_root, run_id, kind, data, **numbers)

    bench = Bench(root, seeds=(SEED, OTHER_SEED))
    with monkeypatch.context() as patch:
        patch.setattr(events, "append", failing)
        failure = bench.failure()
    assert failure.kind == tools.KIND_START_LINE_FAILED
    assert str(SEED) not in failure.message
    assert (bench.count("seeds"), bench.asked, lines(root)) == (1, [], [])
    assert bench.function(request())["outcome"] == "pass"
    assert bench.asked[0][3].seed == OTHER_SEED


@pytest.mark.parametrize(
    "script",
    [mock_check.default_script, wrong_product, "time_limit", 17, ENDINGS[1][0]],
)
def test_the_seed_is_in_no_line_and_in_no_answer(root, script):
    bench = Bench(root, script=script)
    try:
        answer = json.dumps(bench.function(request()))
    except ToolFailure as failure:
        answer = failure.message
    assert bench.asked[0][3].seed == SEED
    assert str(SEED) not in answer
    assert str(SEED).encode() not in log_bytes(root)
    assert b"seed" not in log_bytes(root)


def test_what_the_step_is_handed_shows_no_seed(root, monkeypatch):
    seen = []
    check = check_seed.check

    def looking(
        operation, asked, hw_profile, admitted, seed, output_path, keeper, *, log_path
    ):
        seen.append(seed)
        return check(
            operation,
            asked,
            hw_profile,
            admitted,
            seed,
            output_path,
            keeper,
            log_path=log_path,
        )

    def perform_spy(data_root, asked, hw_profile, operation, drawn):
        seen.append(repr(drawn))
        return perform(data_root, asked, hw_profile, operation, drawn)

    perform = check_tool._perform
    monkeypatch.setattr(check_tool, "_perform", perform_spy)
    monkeypatch.setattr(check_seed, "check", looking)
    Bench(root).function(request())
    shown, seed = seen
    assert seed == SEED
    assert str(SEED) not in shown


def table():
    return BackendTable([Backend(mock_backend.NAME, {})])


def nothing():
    raise AssertionError("building must call nothing")


GOOD = {"source": nothing, "table": None, "seeds": nothing, "covers": nothing}


@pytest.mark.parametrize(
    "changes,named",
    [
        ({"table": [], "source": None, "seeds": None, "covers": None}, "table"),
        ({"table": None, "source": None}, "table"),
        ({"source": None, "seeds": None, "covers": None}, "source"),
        ({"source": "x"}, "source"),
        ({"seeds": None, "covers": None}, "seeds"),
        ({"seeds": 7}, "seeds"),
        ({"covers": None}, "covers"),
        ({"covers": True}, "covers"),
    ],
)
def test_building_refuses_each_bad_argument_in_the_stated_order(changes, named):
    arguments = {**GOOD, "table": table(), **changes}
    with pytest.raises(TypeError) as caught:
        tool_function(**arguments)
    assert named in str(caught.value)


def test_building_calls_nothing_and_takes_keywords_without_defaults():
    assert callable(tool_function(**{**GOOD, "table": table()}))
    parameters = inspect.signature(tool_function).parameters
    assert list(parameters) == ["source", "table", "seeds", "covers"]
    for parameter in parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        tool_function(source=nothing, table=table(), seeds=nothing)


def test_the_table_and_the_request_are_not_modified_and_two_calls_share_nothing(root):
    bench = Bench(root, seeds=(SEED, OTHER_SEED))
    first, second = request(), request(point="board")
    one = bench.function(first)
    two = bench.function(second)
    assert (first, second) == (request(), request(point="board"))
    assert one == two
    assert one is not two
    assert bench.table.names() == (mock_backend.NAME,)
    assert bench.backend.offered() == (TOOL,)
    assert bench.asked[0][3] is not bench.asked[1][3]
    assert bench.asked[0][2] is not bench.asked[1][2]
    other = Bench(root, seeds=(SEED,))
    assert other.function is not bench.function
    assert other.function(first) == one
    assert other.count("seeds") == 0


def test_through_the_frame_of_a_registry_the_test_built(root):
    bench = Bench(root, seeds=(RuntimeError("no entropy"), SEED, OTHER_SEED))
    registry = Registry()
    registry.register(
        TOOL,
        bench.function,
        check_definition.DESCRIPTION,
        check_definition.input_schema(),
    )
    assert registry.definition(TOOL).input_schema == check_definition.input_schema()
    with pytest.raises(ToolFailure) as caught:
        tools.call(registry, TOOL, request())
    assert caught.value.kind == "seed_not_drawn"
    assert lines(root) == []
    assert tools.call(registry, TOOL, request())["outcome"] == "pass"
    assert tools.call(registry, TOOL, request(point="board"))["outcome"] == "pass"


def test_the_module_holds_what_it_joins_and_nothing_of_its_own():
    own = Path(check_tool.__file__)
    text = own.read_text(encoding="utf-8")
    imported = set()
    for node in ast.walk(ast.parse(text)):
        assert not isinstance(node, ast.Import)
        if isinstance(node, ast.ImportFrom):
            assert node.module == "hilclaw"
            imported.update(alias.name for alias in node.names)
    assert imported == {
        "build_log",
        "check_admission",
        "check_ending",
        "check_identity",
        "check_seed",
        "hw_tool",
        "instance",
        "journaled_step",
        "layout",
    }
    kept_out = ("gemm" + "_contract", "standin" + "_profile", "register(")
    for word in (*kept_out, "kernel" + "_source", "resolve(", "absolute("):
        assert word not in text
    public = [name for name in vars(check_tool) if not name.startswith("_")]
    assert sorted(set(public) - imported) == ["tool_function"]


# --- checks of the bf16 kinds (ADR-0177 decision 3) ---

BF16_SHAPES = {
    "gemm": {"m": 2, "k": 3, "n": 4},
    "rmsnorm": {"m": 2, "n": 8},
    "elementwise_add": {"m": 3, "n": 5},
    "swiglu": {"m": 2, "n": 6},
}
BF16_STEP = {
    "sim": "correctness_check_bf16_sim",
    "board": "correctness_check_bf16_board",
}
FP32_STEP = {"sim": "correctness_check_sim", "board": "correctness_check_board"}
A_LOG = "zq7 the log of a build zq7"


def bf16_op(kind, shape=None):
    return {
        "schema_version": 1,
        "kind": kind,
        "shape": dict(BF16_SHAPES[kind] if shape is None else shape),
        "dtype": "bf16",
        "layout": "row_major",
    }


def bf16_run(root, kind="rmsnorm", **changes):
    place(root, content(op=bf16_op(kind), **changes))
    return root


def bf16_failing(tool, asked, hw_profile, parameters, output_path, keeper):
    report = bytearray(
        mock_check.default_script(
            tool, asked, hw_profile, parameters, output_path, keeper
        )
    )
    struct.pack_into("=H", report, 4, 0x7F00)
    return bytes(report)


def logging(tool, asked, hw_profile, parameters, output_path, keeper):
    keeper.hand_over(A_LOG)
    return mock_check.default_script(
        tool, asked, hw_profile, parameters, output_path, keeper
    )


def changing_between_the_reads(monkeypatch, root, later):
    reads = []
    read = instance.read

    def changing(data_root, run_id):
        reads.append(run_id)
        found = read(data_root, run_id)
        if len(reads) == 1:
            place(root, later)
        return found

    monkeypatch.setattr(instance, "read", changing)
    return reads


def steps_looked_up(monkeypatch):
    steps = []
    run_prepared = journaled_step.run_prepared

    def spy(data_root, run_id, identity, *rest, **named):
        steps.append(identity.step)
        return run_prepared(data_root, run_id, identity, *rest, **named)

    monkeypatch.setattr(journaled_step, "run_prepared", spy)
    return steps


@pytest.mark.parametrize("point", ["sim", "board"])
@pytest.mark.parametrize("kind", list(BF16_SHAPES))
def test_a_bf16_check_of_each_kind_at_each_point_passes_under_its_step(
    root, kind, point
):
    bf16_run(root, kind)
    bench = Bench(root, covers=contract_table.covers, script=logging)
    asked = request(point=point)
    result = bench.function(asked)
    assert result == {
        "outcome": "pass",
        "shape": BF16_SHAPES[kind],
        "draws": DRAWS,
        "tolerance": TOLERANCE,
        "counts": [{"failed": 0, "non_finite": 0}] * DRAWS,
    }
    step = {"step": BF16_STEP[point], "execution": 1}
    assert [line["kind"] for line in lines(root)] == ["step_started", "step_ended"]
    assert [line["data"]["step"] for line in lines(root)] == [BF16_STEP[point]] * 2
    assert lines(root)[1]["data"] == {**step, "spend": {}, "result": result}
    ((_, _, _, parameters, _),) = bench.asked
    assert type(parameters) is Bf16CheckParameters
    assert parameters == Bf16CheckParameters(
        SEED, DRAWS, kind, "bf16", tuple(BF16_SHAPES[kind].values())
    )
    log_file = layout.build_log_file(root, RUN, ROUND, 2, 1, BF16_STEP[point], 1)
    assert log_file.name == f"build-log-{BF16_STEP[point]}-01.txt"
    assert log_file.read_text(encoding="utf-8") == A_LOG
    again = bench.function(asked)
    assert again == result
    assert (bench.count("seeds"), bench.count("operation")) == (1, 1)
    assert len(lines(root)) == 2


@pytest.mark.parametrize(
    ("script", "outcome"),
    [(bf16_failing, "fail"), ("time_limit", "broken")],
    ids=["fail", "broken"],
)
def test_a_bf16_check_reports_fail_and_broken(root, script, outcome):
    bf16_run(root, "swiglu")
    bench = Bench(root, covers=contract_table.covers, script=script)
    result = bench.function(request(point="board"))
    assert result["outcome"] == outcome
    assert result["shape"] == BF16_SHAPES["swiglu"]
    if outcome == "fail":
        assert result["counts"][0]["failed"] >= 1
    else:
        assert result["condition"] == "time_limit"
    assert lines(root)[1]["data"]["step"] == "correctness_check_bf16_board"
    assert lines(root)[1]["data"]["result"] == result


def test_an_fp32_check_keeps_its_step_and_its_parameters(root):
    bench = Bench(root, covers=contract_table.check_covers, seeds=(SEED, OTHER_SEED))
    for point in ("sim", "board"):
        assert bench.function(request(point=point))["shape"] == SHAPE
    assert [line["data"]["step"] for line in lines(root)] == [
        FP32_STEP["sim"],
        FP32_STEP["sim"],
        FP32_STEP["board"],
        FP32_STEP["board"],
    ]
    assert [type(asked[3]) for asked in bench.asked] == [CheckParameters] * 2


@pytest.mark.parametrize("point", ["sim", "board"])
def test_a_file_that_becomes_bf16_between_the_reads_is_not_covered(
    root, monkeypatch, point
):
    reads = changing_between_the_reads(monkeypatch, root, content(op=bf16_op("gemm")))
    bench = Bench(root, covers=contract_table.covers)
    failure = bench.failure(request(point=point))
    assert failure.kind == check_admission.KIND_OP_SIGNATURE_NOT_COVERED
    assert len(reads) == 2
    assert (bench.count("seeds"), bench.count("operation")) == (0, 0)
    assert lines(root) == []
    assert bench.function(request(point=point))["shape"] == BF16_SHAPES["gemm"]
    assert lines(root)[0]["data"]["step"] == BF16_STEP[point]


@pytest.mark.parametrize("point", ["sim", "board"])
def test_a_file_that_stops_being_bf16_between_the_reads_is_not_covered(
    root, monkeypatch, point
):
    bf16_run(root, "elementwise_add", draws=ABSENT)
    bench = Bench(root, covers=contract_table.covers)
    changing_between_the_reads(monkeypatch, root, content(draws=ABSENT))
    failure = bench.failure(request(point=point))
    assert failure.kind == check_admission.KIND_OP_SIGNATURE_NOT_COVERED
    assert (bench.count("covers"), bench.count("seeds")) == (1, 0)
    assert lines(root) == []
    assert bench.failure(request(point=point)).kind == "draws_not_stated"


@pytest.mark.parametrize(
    ("kind", "shape"),
    [
        ("rope", {"m": 2, "h": 2, "d": 4}),
        ("sdpa_kv_cache", {"m": 1, "l": 2, "h": 2, "h_kv": 1, "d": 4}),
    ],
)
@pytest.mark.parametrize(
    "covers",
    [contract_table.covers, contract_table.check_covers],
    ids=["any", "checked"],
)
def test_a_bf16_record_with_no_check_is_not_covered_and_writes_no_line(
    root, monkeypatch, kind, shape, covers
):
    record = {**bf16_op("gemm"), "kind": kind, "shape": shape}
    place(root, content(op=record))
    steps = steps_looked_up(monkeypatch)
    bench = Bench(root, covers=covers)
    failure = bench.failure(request(point="board"))
    assert failure.kind == check_admission.KIND_OP_SIGNATURE_NOT_COVERED
    assert steps == ["correctness_check_bf16_board"]
    assert (bench.count("seeds"), bench.count("operation"), lines(root)) == (0, 0, [])


@pytest.mark.parametrize("kind", list(BF16_SHAPES))
def test_a_bf16_record_with_a_shape_outside_its_contract_is_not_covered(root, kind):
    shape = dict.fromkeys(BF16_SHAPES[kind], 1) | {"n": 0}
    place(root, content(op=bf16_op(kind, shape)))
    bench = Bench(root, covers=contract_table.covers)
    failure = bench.failure(request())
    assert failure.kind == check_admission.KIND_OP_SIGNATURE_NOT_COVERED
    assert (bench.count("seeds"), lines(root)) == (0, [])


def test_an_invalid_file_is_answered_at_the_read_of_the_stamp(root, recorded):
    place(root, b"{not json")
    bench = Bench(root, covers=contract_table.covers)
    for point in ("sim", "board"):
        assert bench.failure(request(point=point)).kind == "run_file_invalid"
    assert recorded == ["read", "read"]
    assert (bench.count("covers"), bench.count("seeds"), lines(root)) == (0, 0, [])


@pytest.mark.parametrize("point", ["cpu", "Sim", None])
def test_a_point_that_is_neither_value_is_refused_before_any_read(
    root, recorded, point
):
    bf16_run(root)
    bench = Bench(root, covers=contract_table.covers)
    failure = bench.failure(request(point=point))
    assert failure.kind == "invalid_request"
    assert (recorded, bench.sources, lines(root)) == ([], 0, [])


@pytest.mark.parametrize("kind", list(BF16_SHAPES))
def test_the_default_registry_answers_each_bf16_kind_not_covered_under_its_step(
    root, monkeypatch, kind
):
    bf16_run(root, kind)
    steps = steps_looked_up(monkeypatch)
    registry = tools.default_registry(lambda: root)
    for point in ("sim", "board"):
        with pytest.raises(ToolFailure) as caught:
            tools.call(registry, TOOL, request(point=point))
        assert caught.value.kind == check_admission.KIND_OP_SIGNATURE_NOT_COVERED
    assert steps == [BF16_STEP["sim"], BF16_STEP["board"]]
    assert lines(root) == []
