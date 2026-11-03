"""Two measuring points of one test-built QNN target kept apart (ADR-0194 decision 5; PLAN P3-10).

The binding here is test-only and assigns no point (HQ-0095 (1) asks which
execution is which point): the accelerator ``ACCELERATOR`` is in no
``targets.TABLE`` entry, and its one backend lives in a table this module
builds (ADR-0016 decision 5). Its ``sim.run`` operation runs the timing
fixture ``tests/qnn_fixtures/timing.c.in`` with the QNN HTP backend library,
the HTP emulator, and its ``board.run`` operation runs the same fixture with
the QNN CPU backend library. The CPU backend stands in for "another means"
only to show the separation; its intervals, like the emulator's, are host
figures and no device figure (FR-19 (4)).
"""

import os
from pathlib import Path

import pytest
import test_qnn_adapter as qnn_tests
import test_run_tool as run_tests
from test_qnn_adapter import qnn, qnn_sdk  # noqa: F401

from hilclaw import (
    checks_tool,
    events,
    gemm_contract,
    qnn_adapter,
    run_result,
    timings_tool,
)
from hilclaw.backends import Backend, BackendTable
from hilclaw.run_parameters import TimingParameters
from hilclaw.run_tool import tool_function
from hilclaw.tools import KIND_NOT_OFFERED, ToolFailure

ACCELERATOR = "test_qnn_two_points"
TOOLS = ("sim.run", "board.run")
STEP = run_tests.STEP
N_MAX = 20
LIMIT = qnn_tests.LIMIT
ENTERING = (run_result.CONVERGED, run_result.NOT_CONVERGED)


class Means:
    """The operation of one point: the timing fixture run with one backend library, every call recorded."""

    def __init__(self, target, executable, library):
        self.target, self.executable, self.library = target, executable, library
        self.handed = []

    def __call__(self, request, hw_profile, parameters, output_path, keeper):
        self.handed.append((self.library, parameters))
        return qnn_adapter.measure(
            self.target, self.executable, self.library, parameters, timeout_s=LIMIT
        )


@pytest.fixture
def means(qnn, tmp_path):  # noqa: F811
    target, compiler, htp = qnn
    executable = tmp_path / ("timing" + qnn_tests.EXE)
    built = qnn_adapter.build(
        target, qnn_tests.source(tmp_path, "timing"), executable, program=compiler
    )
    assert built.form == "go_on"
    cpu = str(Path(htp).with_name("QnnCpu.dll" if os.name == "nt" else "libQnnCpu.so"))
    return target, executable, htp, cpu


@pytest.fixture
def root(tmp_path):
    data = tmp_path / "data"
    return run_tests.a_run(
        data, run_tests.content(n_max=N_MAX, accelerator=ACCELERATOR)
    )


def functions(root, operations):
    table = BackendTable([Backend(ACCELERATOR, operations)])
    return {
        tool: tool_function(
            tool,
            source=lambda: root,
            table=table,
            seeds=lambda: run_tests.SEED,
            covers=gemm_contract.covers,
        )
        for tool in TOOLS
    }


def ended_lines(root, tool):
    return [
        line
        for line in events.read(root, run_tests.RUN).events
        if line["kind"] == "step_ended" and line["data"]["step"] == STEP[tool]
    ]


def test_each_point_ends_with_its_own_step_from_its_own_operation(root, means):
    target, executable, htp, cpu = means
    sim, board = Means(target, executable, htp), Means(target, executable, cpu)
    called = functions(root, {"sim.run": sim, "board.run": board})
    results = {tool: called[tool](run_tests.request()) for tool in TOOLS}
    parameters = TimingParameters(2, 3, 4, N_MAX, "interval", run_tests.SEED)
    assert sim.handed == [(htp, parameters)]
    assert board.handed == [(cpu, parameters)]
    for tool in TOOLS:
        result = results[tool]
        assert result["outcome"] in ENTERING
        assert result["unit"] == "ns"
        assert len(result["intervals"]) >= qnn_tests.N_MIN
        (line,) = ended_lines(root, tool)
        assert line["data"]["result"] == result
    assert {
        line["data"]["step"] for line in events.read(root, run_tests.RUN).events
    } == {
        "sim_run_timing_v2",
        "board_run_timing_v2",
    }

    lines = checks_tool.log_lines(root, run_tests.RUN)
    for point, tool in (("sim", "sim.run"), ("board", "board.run")):
        found = timings_tool.timing_lines(run_tests.RUN, lines, point, lambda n: True)
        (held,) = found.values()
        assert held.entering == [(1, results[tool])]
        assert timings_tool.measurement_problem(held) is None


def test_a_board_run_without_its_means_is_broken_and_takes_nothing_of_sim(root, means):
    target, executable, htp, cpu = means
    missing = str(Path(cpu).with_name("hilclaw-no-such-backend.dll"))
    sim, board = Means(target, executable, htp), Means(target, executable, missing)
    called = functions(root, {"sim.run": sim, "board.run": board})
    first = called["sim.run"](run_tests.request())
    assert first["outcome"] in ENTERING
    result = called["board.run"](run_tests.request())
    assert (result["outcome"], result["condition"]) == ("broken", "exit_status")
    assert "intervals" not in result
    assert [library for library, _ in board.handed] == [missing]
    assert [library for library, _ in sim.handed] == [htp]
    assert called["sim.run"](run_tests.request()) == first
    assert len(sim.handed) == 1
    (line,) = ended_lines(root, "sim.run")
    assert line["data"]["result"] == first
    (line,) = ended_lines(root, "board.run")
    assert line["data"]["result"] == result


def test_a_point_with_no_means_is_not_offered(root, means):
    target, executable, htp, _ = means
    sim = Means(target, executable, htp)
    called = functions(root, {"sim.run": sim})
    with pytest.raises(ToolFailure) as caught:
        called["board.run"](run_tests.request())
    assert caught.value.kind == KIND_NOT_OFFERED
    assert ended_lines(root, "board.run") == []
    assert called["sim.run"](run_tests.request())["outcome"] in ENTERING
    assert [library for library, _ in sim.handed] == [htp]
