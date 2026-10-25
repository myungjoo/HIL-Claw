import ast
import copy
import inspect
from pathlib import Path

import pytest

from hilclaw import mock_backend, mock_run
from hilclaw.backends import Backend, BackendTable, select
from hilclaw.build_log import LogKeeper
from hilclaw.harness import measurement
from hilclaw.harness.measurement import N_MIN, State
from hilclaw.harness.timing import SAMPLE_FORMS, judge_report, parse_report
from hilclaw.mock_run import default_script, operation
from hilclaw.run_operation import OperationAnswerInvalid, Reported, ask
from hilclaw.run_parameters import TimingParameters
from hilclaw.tools import ToolFailure

TOOLS = ("sim.run", "board.run")

# Test values, not dimensions, a bound, a seed or a figure of the package.
PARAMETERS = TimingParameters(
    m=3, k=4, n=5, n_max=10, sample_form="interval", seed=918273645546372819
)
REQUEST = {"run_id": "r1", "execution": 1, "candidate": 2}
PATH_MARKER = "zq7-path-zq7"
# A test value: nothing lies there, and no test makes it.
OUTPUT_PATH = Path(PATH_MARKER) / "runs" / "r1" / "output"
LOG_PATH = Path(PATH_MARKER) / "runs" / "r1" / "build-log.txt"
KEEPER = LogKeeper()
EXPECTED_REPORT = (
    b"resolution_ns 1\n" + b"interval_ns 1000000\n" * N_MIN + b"stop converged\n"
)


class Asked:
    def __init__(self, answer=None):
        self.answer = answer
        self.calls = []

    def __call__(self, tool, request, hw_profile, parameters, output_path, keeper):
        self.calls.append((tool, request, hw_profile, parameters, output_path, keeper))
        return self.answer


class Untouchable:
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        raise AssertionError(f"looked at: {name}")

    def __eq__(self, other):
        raise AssertionError("compared")

    __hash__ = None


def record(accelerator=mock_backend.NAME):
    return {
        "schema_version": 1,
        "accelerator": accelerator,
        "revision": "rev 1",
        "toolchain": {"cc": "1.0"},
        "host": {"cpu": "cpu x", "os": "os y"},
        "hw_source": "external",
    }


def raising(error):
    def script(tool, request, hw_profile, parameters, output_path, keeper):
        raise error

    return script


def imported_modules(path):
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        if isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            found.add(module)
            found |= {f"{module}.{alias.name}" for alias in node.names}
    return found


# The operation: what the script is asked with, and when


@pytest.mark.parametrize("tool", TOOLS)
def test_the_script_is_asked_once_with_the_tool_and_the_very_five_objects(tool):
    script = Asked(object())
    request, hw_profile = dict(REQUEST), record()
    parameters = TimingParameters(*PARAMETERS)
    output_path = Path(OUTPUT_PATH)
    keeper = LogKeeper()
    answer = operation(tool, script)(
        request, hw_profile, parameters, output_path, keeper
    )
    assert answer is script.answer
    ((asked_tool, *asked),) = script.calls
    assert asked_tool == tool
    assert type(asked_tool) is str
    assert asked[0] is request
    assert asked[1] is hw_profile
    assert asked[2] is parameters
    assert asked[3] is output_path
    assert asked[4] is keeper
    assert keeper.held() is None


@pytest.mark.parametrize("tool", TOOLS)
@pytest.mark.parametrize(
    "answer",
    [
        (b"a report of the tests", None),
        (b"", 72351744),
        "build_exit_status",
        "time_limit",
        b"a report alone",
        None,
        "pass",
        object(),
    ],
    ids=lambda answer: repr(answer)[:24],
)
def test_the_operation_returns_the_very_object_the_script_returned(tool, answer):
    made = operation(tool, Asked(answer))
    assert made(REQUEST, record(), PARAMETERS, OUTPUT_PATH, KEEPER) is answer


@pytest.mark.parametrize(
    "things",
    [
        (None, None, None, None, None),
        (Untouchable(), Untouchable(), Untouchable(), Untouchable(), Untouchable()),
        ("a str", b"bytes", 17, PATH_MARKER, "no keeper"),
    ],
    ids=["None", "untouchable", "other types"],
)
def test_five_things_of_any_kind_reach_the_script_unlooked_at(things):
    script = Asked("an answer")
    assert operation("sim.run", script)(*things) == "an answer"
    asked = script.calls[0][1:]
    assert all(a is b for a, b in zip(asked, things, strict=True))


def test_a_call_leaves_its_five_objects_as_they_are():
    request, hw_profile = dict(REQUEST), record()
    before = copy.deepcopy((request, hw_profile))
    operation("board.run", default_script)(
        request, hw_profile, PARAMETERS, OUTPUT_PATH, KEEPER
    )
    assert (request, hw_profile) == before


def test_building_asks_nothing_and_each_call_asks_once():
    script = Asked()
    made = operation("sim.run", script)
    assert script.calls == []
    made(REQUEST, record(), PARAMETERS, OUTPUT_PATH, KEEPER)
    made(REQUEST, record(), PARAMETERS, OUTPUT_PATH, KEEPER)
    assert len(script.calls) == 2


def test_one_script_serves_both_tools_and_is_told_the_called_one():
    script = Asked("an answer")
    sim, board = operation("sim.run", script), operation("board.run", script)
    board(REQUEST, record(), PARAMETERS, OUTPUT_PATH, KEEPER)
    sim(REQUEST, record(), PARAMETERS, OUTPUT_PATH, KEEPER)
    assert [call[0] for call in script.calls] == ["board.run", "sim.run"]


def test_the_operation_has_a_readable_repr_and_is_selected_through_a_backend():
    script = Asked("an answer")
    sim, board = operation("sim.run", script), operation("board.run", script)
    assert repr(sim) == "<operation of the mock backend for 'sim.run'>"
    assert repr(board) == "<operation of the mock backend for 'board.run'>"
    table = BackendTable(
        [Backend(mock_backend.NAME, {"sim.run": sim, "board.run": board})]
    )
    assert select(table, record(), "sim.run") is sim
    assert select(table, record(), "board.run") is board
    assert script.calls == []


ERRORS = [
    ToolFailure("invalid_request", "zq7"),
    ToolFailure("some_kind", "zq7"),
    ValueError("zq7"),
    KeyboardInterrupt(),
    SystemExit(3),
]


@pytest.mark.parametrize("tool", TOOLS)
@pytest.mark.parametrize("error", ERRORS, ids=lambda error: type(error).__name__)
def test_what_the_script_raises_passes_through_as_the_same_object(tool, error):
    made = operation(tool, raising(error))
    with pytest.raises(BaseException) as caught:
        made(REQUEST, record(), PARAMETERS, OUTPUT_PATH, KEEPER)
    assert caught.value is error


# The operation: what is refused


@pytest.mark.parametrize("script", [None, "a script", b"x", 3, ("sim.run",)])
def test_a_script_that_is_not_callable_is_refused_at_building(script):
    with pytest.raises(TypeError, match="callable"):
        operation("sim.run", script)


@pytest.mark.parametrize("tool", [None, b"sim.run", 1, ("sim.run",), Untouchable()])
def test_a_tool_that_is_no_str_is_a_type_error(tool):
    script = Asked()
    with pytest.raises(TypeError, match="tool"):
        operation(tool, script)
    assert script.calls == []


class Name(str):
    pass


@pytest.mark.parametrize(
    "tool",
    ["", "sim", "SIM.RUN", "sim.run ", "correctness.check", "profiler.collect"],
)
def test_a_str_that_is_no_run_tool_is_a_value_error(tool):
    script = Asked()
    with pytest.raises(ValueError, match="tool"):
        operation(tool, script)
    assert script.calls == []


def test_a_subclass_of_str_is_a_type_error():
    with pytest.raises(TypeError, match="tool"):
        operation(Name("sim.run"), Asked())


def test_the_tool_is_looked_at_before_the_script():
    with pytest.raises(TypeError, match="tool"):
        operation(None, None)
    with pytest.raises(ValueError, match="tool"):
        operation("correctness.check", None)


@pytest.mark.parametrize(
    "call",
    [
        lambda made: made(REQUEST, record(), PARAMETERS, OUTPUT_PATH),
        lambda made: made(REQUEST, record(), PARAMETERS, OUTPUT_PATH, KEEPER, None),
        lambda made: made(REQUEST, record(), PARAMETERS, OUTPUT_PATH, keeper=KEEPER),
        lambda made: made(),
    ],
    ids=["four", "six", "a keyword", "none"],
)
def test_an_operation_takes_five_positional_things_and_nothing_else(call):
    script = Asked()
    with pytest.raises(TypeError):
        call(operation("board.run", script))
    assert script.calls == []


# The default script


@pytest.mark.parametrize("tool", TOOLS)
def test_the_default_answer_is_the_report_of_n_min_intervals_and_no_figure(tool):
    answer = default_script(tool, REQUEST, record(), PARAMETERS, OUTPUT_PATH, KEEPER)
    assert type(answer) is tuple
    assert len(answer) == 2
    report, figure = answer
    assert type(report) is bytes
    assert report == EXPECTED_REPORT
    assert figure is None


def test_the_report_agrees_with_the_constant_of_the_source():
    report, _ = default_script("sim.run", None, None, None, None, None)
    lines = report.split(b"\n")
    assert lines[0] == b"resolution_ns 1"
    assert lines[1:-2] == [b"interval_ns 1000000"] * measurement.N_MIN
    assert lines[-2:] == [b"stop converged", b""]
    report.decode("ascii")
    assert b"\r" not in report


@pytest.mark.parametrize("tool", TOOLS)
def test_the_default_answer_through_ask_is_reported(tool):
    reported = ask(
        operation(tool, default_script),
        REQUEST,
        record(),
        PARAMETERS,
        OUTPUT_PATH,
        LogKeeper(),
        log_path=LOG_PATH,
    )
    assert type(reported) is Reported
    assert reported == Reported(EXPECTED_REPORT, None)


def test_parse_report_reads_the_default_report():
    report, _ = default_script(
        "sim.run", REQUEST, record(), PARAMETERS, OUTPUT_PATH, KEEPER
    )
    parsed = parse_report(report)
    assert parsed.resolution_ns == 1
    assert parsed.intervals_ns == (1000000,) * N_MIN
    assert parsed.state is State.CONVERGED


@pytest.mark.parametrize("sample_form", SAMPLE_FORMS)
@pytest.mark.parametrize("n_max", [N_MIN, N_MIN + 1, 10, 2**40])
def test_the_default_report_is_judged_completed_and_converged(sample_form, n_max):
    parameters = PARAMETERS._replace(n_max=n_max, sample_form=sample_form)
    report, _ = default_script(
        "board.run", REQUEST, record(), parameters, OUTPUT_PATH, KEEPER
    )
    judged = judge_report(report, sample_form=sample_form, n_max=n_max)
    assert judged.broken is None
    assert judged.state is State.CONVERGED
    assert judged.intervals_ns == (1000000,) * N_MIN
    assert judged.resolution_ns == 1


ASKED_WITH = [
    ("sim.run", REQUEST, record(), PARAMETERS, OUTPUT_PATH, KEEPER),
    ("board.run", REQUEST, record(), PARAMETERS, OUTPUT_PATH, KEEPER),
    (
        "sim.run",
        {"run_id": "r9", "execution": 7, "candidate": 3},
        record(),
        PARAMETERS,
        OUTPUT_PATH,
        KEEPER,
    ),
    ("sim.run", REQUEST, record("another"), PARAMETERS, OUTPUT_PATH, KEEPER),
    ("sim.run", REQUEST, record(), PARAMETERS._replace(seed=0), OUTPUT_PATH, KEEPER),
    (
        "sim.run",
        REQUEST,
        record(),
        PARAMETERS._replace(m=4096, k=1, n=2**40),
        OUTPUT_PATH,
        KEEPER,
    ),
    ("sim.run", REQUEST, record(), PARAMETERS._replace(n_max=5), OUTPUT_PATH, KEEPER),
    (
        "sim.run",
        REQUEST,
        record(),
        PARAMETERS._replace(sample_form="reciprocal"),
        OUTPUT_PATH,
        KEEPER,
    ),
    ("sim.run", REQUEST, record(), PARAMETERS, Path(PATH_MARKER) / "elsewhere", KEEPER),
    (None, None, None, None, None, None),
    (Untouchable(),) * 6,
    ("correctness.check", "no request", 3, (1, 2), b"no path", "no keeper"),
]


@pytest.mark.parametrize("asked", ASKED_WITH, ids=range(len(ASKED_WITH)))
def test_the_default_answer_depends_on_nothing_it_is_asked_with(asked):
    assert default_script(*asked) == (EXPECTED_REPORT, None)


def test_the_default_answer_is_the_same_whatever_lies_at_the_output_path(tmp_path):
    present = tmp_path / "output"
    present.mkdir()
    (present / "kernel.c").write_text("int x;\n", encoding="utf-8")
    absent = tmp_path / "absent"
    for path in (present, absent, str(present)):
        assert default_script(
            "sim.run", REQUEST, record(), PARAMETERS, path, KEEPER
        ) == (
            EXPECTED_REPORT,
            None,
        )
    assert [entry.name for entry in present.iterdir()] == ["kernel.c"]
    assert not absent.exists()


# Answers of a script of a test, through the operation and ask


@pytest.mark.parametrize("tool", TOOLS)
@pytest.mark.parametrize(
    "answer,expected",
    [
        ("exit_status", "exit_status"),
        ("build_time_limit", "build_time_limit"),
        ((b"resolution_ns 1\nstop converged\n", 72351744), None),
    ],
    ids=["exit_status", "build_time_limit", "a figure"],
)
def test_an_answer_of_a_test_passes_through_and_ask_classifies_it(
    tool, answer, expected
):
    got = ask(
        operation(tool, Asked(answer)),
        REQUEST,
        record(),
        PARAMETERS,
        OUTPUT_PATH,
        LogKeeper(),
        log_path=LOG_PATH,
    )
    if expected is None:
        assert got == Reported(*answer)
    else:
        assert got is answer


@pytest.mark.parametrize(
    "answer",
    [b"a report alone", (b"r", 0), ("r", None), "pass", None, [b"r", None]],
    ids=repr,
)
def test_an_answer_of_neither_form_passes_through_and_ask_refuses_it(answer):
    with pytest.raises(OperationAnswerInvalid):
        ask(
            operation("board.run", Asked(answer)),
            REQUEST,
            record(),
            PARAMETERS,
            OUTPUT_PATH,
            LogKeeper(),
            log_path=LOG_PATH,
        )


@pytest.mark.parametrize(
    "error",
    [ToolFailure("some_kind", "zq7"), KeyboardInterrupt(), SystemExit(1)],
    ids=lambda error: type(error).__name__,
)
def test_a_failure_or_a_request_to_end_reaches_ask_as_the_same_object(error):
    with pytest.raises(BaseException) as caught:
        ask(
            operation("sim.run", raising(error)),
            REQUEST,
            record(),
            PARAMETERS,
            OUTPUT_PATH,
            LogKeeper(),
            log_path=LOG_PATH,
        )
    assert caught.value is error


# Purity and the module


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for tool in TOOLS:
        operation(tool, default_script)(
            REQUEST, record(), PARAMETERS, OUTPUT_PATH, KEEPER
        )
        default_script(tool, None, None, None, tmp_path / "output", KEEPER)
    assert list(tmp_path.iterdir()) == []


def test_the_module_imports_the_measurement_constants_only_and_has_no_entry():
    own = Path(mock_run.__file__)
    imported = imported_modules(own)
    assert imported == {"hilclaw.harness", "hilclaw.harness.measurement"}
    assert not hasattr(mock_run, "main")
    assert "__main__" not in own.read_text(encoding="utf-8")
    names = {
        node.attr if isinstance(node, ast.Attribute) else node.id
        for node in ast.walk(ast.parse(own.read_text(encoding="utf-8")))
        if isinstance(node, ast.Attribute | ast.Name)
    }
    assert "N_MIN" in names
    assert "CV_MAX" not in names


def test_public_names_of_the_module_and_no_default():
    public = {
        name
        for name, value in vars(mock_run).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {"operation", "default_script"}
    parameters = inspect.signature(default_script).parameters
    assert list(parameters) == [
        "tool",
        "request",
        "hw_profile",
        "parameters",
        "output_path",
        "keeper",
    ]
    for parameter in parameters.values():
        assert parameter.default is inspect.Parameter.empty, parameter
    assert list(inspect.signature(operation).parameters) == ["tool", "script"]


# The keeper (ADR-0108 decision 8)


@pytest.mark.parametrize("tool", TOOLS)
def test_the_default_script_hands_over_no_log_and_ask_writes_none(tool, tmp_path):
    keeper = LogKeeper()
    log_path = tmp_path / "attempt" / "build-log.txt"
    reported = ask(
        operation(tool, default_script),
        REQUEST,
        record(),
        PARAMETERS,
        OUTPUT_PATH,
        keeper,
        log_path=log_path,
    )
    assert reported == Reported(EXPECTED_REPORT, None)
    assert keeper.held() is None
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("tool", TOOLS)
def test_a_script_of_a_test_hands_a_log_to_the_very_keeper(tool, tmp_path):
    def handing(called, request, hw_profile, parameters, output_path, keeper):
        keeper.hand_over(f"log of {called}")
        return "build_exit_status"

    keeper = LogKeeper()
    log_path = tmp_path / "attempt" / "build-log.txt"
    answer = ask(
        operation(tool, handing),
        REQUEST,
        record(),
        PARAMETERS,
        OUTPUT_PATH,
        keeper,
        log_path=log_path,
    )
    assert answer == "build_exit_status"
    assert keeper.held() == f"log of {tool}"
    assert log_path.read_text(encoding="utf-8") == f"log of {tool}"
