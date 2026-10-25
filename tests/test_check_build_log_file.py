import json
import threading
from pathlib import Path

import pytest

from hilclaw import (
    build_log,
    check_answer,
    check_definition,
    check_ending,
    check_operation,
    check_seed,
    events,
    gemm_contract,
    keys,
    mock_backend,
    mock_check,
    run_state,
)
from hilclaw.backends import Backend, BackendTable
from hilclaw.build_log import BuildLogUnwritable, HandOverRefused, LogKeeper
from hilclaw.check_admission import Admitted
from hilclaw.check_ending import EndedWithoutOutcome
from hilclaw.check_operation import OperationAnswerInvalid
from hilclaw.check_parameters import CheckParameters
from hilclaw.check_tool import tool_function
from hilclaw.harness.verification_arrays import VerificationArgumentError
from hilclaw.journal import EMPTY
from hilclaw.tools import ToolFailure

# Test values only: the names of the Walk-through of ADR-0078.
TOOL = "correctness.check"
RUN = "r1"
SEED = 987654321987654321
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
    "round": 3,
    "candidate": 2,
    "attempt": 1,
    "execution": 1,
    "point": "sim",
}
ATTEMPT = "runs/r1/rounds/0003/measure/candidates/02/attempts/01"
WALK_THROUGH = f"{ATTEMPT}/build-log-correctness_check_sim-01.txt"
LOG = "gemm.c:3:5: warning: unused variable ‘x’ ünïcode\r\nline two without newline"
UNWRITABLE = "build_log_unwritable"


def profile():
    return {
        "schema_version": 1,
        "accelerator": mock_backend.NAME,
        "revision": "test-revision",
        "toolchain": {"cc": "test"},
        "host": {"cpu": "test", "os": "test"},
        "hw_source": "external",
    }


def a_run(root):
    record = profile()
    document = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(record).name, "record": record},
        "op_signature": {"key": keys.op_signature_key(OP).name, "record": OP},
        "draws": DRAWS,
        "tolerance": TOLERANCE,
    }
    run = root / "runs" / RUN
    run.mkdir(parents=True)
    (run / "instance.json").write_bytes(json.dumps(document).encode())
    (run / "STATE.json").write_bytes(run_state.dump(3, EMPTY))
    return root


@pytest.fixture
def root(tmp_path):
    return a_run(tmp_path / "data")


@pytest.fixture
def other_root(tmp_path):
    return a_run(tmp_path / "other")


def request(**changes):
    return {**REQUEST, **changes}


def lines(root):
    found = events.read(root, RUN).events
    return [{name: line[name] for name in line if name != "time"} for line in found]


def log_bytes(root):
    path = root / f"runs/{RUN}/events.ndjson"
    return path.read_bytes() if path.exists() else b""


def build_logs(root):
    return sorted(
        path.relative_to(root).as_posix() for path in root.rglob("build-log-*")
    )


def handing(answer, log=LOG):
    """A script that hands ``log`` over and then answers with ``answer``."""

    def script(tool, asked, hw_profile, parameters, output_path, keeper):
        keeper.hand_over(log)
        if isinstance(answer, BaseException):
            raise answer
        if callable(answer):
            return answer(tool, asked, hw_profile, parameters, output_path, keeper)
        return answer

    return script


def silent(answer):
    def script(tool, asked, hw_profile, parameters, output_path, keeper):
        if isinstance(answer, BaseException):
            raise answer
        if callable(answer):
            return answer(tool, asked, hw_profile, parameters, output_path, keeper)
        return answer

    return script


def function_of(root, script, seeds=None):
    table = BackendTable(
        [Backend(mock_backend.NAME, {TOOL: mock_check.operation(script)})]
    )
    answers = [SEED] if seeds is None else list(seeds)
    return tool_function(
        source=lambda: root,
        table=table,
        seeds=lambda: answers.pop(0),
        covers=gemm_contract.covers,
    )


def outcome(root, script, asked=None):
    """Return ``("result", result)`` or ``("failure", kind, message)`` of one call."""
    try:
        return ("result", function_of(root, script)(asked or request()))
    except ToolFailure as failure:
        return ("failure", failure.kind, failure.message)


def wrong_product(tool, asked, hw_profile, parameters, output_path, keeper):
    report = bytearray(
        mock_check.default_script(
            tool, asked, hw_profile, parameters, output_path, keeper
        )
    )
    report[4] ^= 0x40
    return bytes(report)


# Tool level: the happy path.


@pytest.mark.parametrize("point", ["sim", "board"])
def test_a_handed_log_is_written_at_its_path_and_changes_no_result(
    root, other_root, point
):
    asked = request(point=point)
    script = handing(mock_check.default_script)
    result = function_of(root, script)(asked)
    expected = function_of(other_root, silent(mock_check.default_script))(asked)
    assert result == expected
    assert result["outcome"] == "pass"
    name = f"{ATTEMPT}/build-log-correctness_check_{point}-01.txt"
    assert build_logs(root) == [name]
    assert (root / name).read_bytes() == LOG.encode("utf-8")
    assert build_logs(other_root) == []
    assert [line["data"] for line in lines(root)] == [
        line["data"] for line in lines(other_root)
    ]


def test_the_walk_through_path_is_the_one_of_adr_0078(root):
    function_of(root, handing(mock_check.default_script))(request())
    assert (root / WALK_THROUGH).read_bytes() == LOG.encode("utf-8")


def test_an_empty_log_is_written_as_an_empty_file(root):
    function_of(root, handing(mock_check.default_script, log=""))(request())
    assert build_logs(root) == [WALK_THROUGH]
    assert (root / WALK_THROUGH).read_bytes() == b""


def test_no_log_handed_writes_no_file_and_makes_no_directory(root):
    result = function_of(root, silent(mock_check.default_script))(request())
    assert result["outcome"] == "pass"
    assert build_logs(root) == []
    assert not (root / "runs" / RUN / "rounds").exists()


def test_a_further_execution_writes_its_own_name(root):
    function_of(root, handing(mock_check.default_script))(request())
    function_of(root, handing(mock_check.default_script, log="second"))(
        request(execution=2)
    )
    second = f"{ATTEMPT}/build-log-correctness_check_sim-02.txt"
    assert build_logs(root) == [WALK_THROUGH, second]
    assert (root / second).read_bytes() == b"second"
    assert (root / WALK_THROUGH).read_bytes() == LOG.encode("utf-8")


def test_the_log_is_written_before_the_judging_and_before_the_end_line(
    root, monkeypatch
):
    seen = []
    judge, append = check_answer.from_answer, events.append

    def judging(*args, **kwargs):
        seen.append(("judge", (root / WALK_THROUGH).exists()))
        return judge(*args, **kwargs)

    def appending(data_root, run_id, kind, data, **numbers):
        seen.append((kind, (root / WALK_THROUGH).exists()))
        return append(data_root, run_id, kind, data, **numbers)

    monkeypatch.setattr(check_answer, "from_answer", judging)
    monkeypatch.setattr(events, "append", appending)
    function_of(root, handing(mock_check.default_script))(request())
    assert seen == [("step_started", False), ("judge", True), ("step_ended", True)]


# Tool level: each answer form with a handed log.

FORMS = [
    ("report", mock_check.default_script),
    ("failing report", wrong_product),
    ("condition", "build_exit_status"),
    ("neither form", 17),
    ("raised error", ValueError("raised by a script")),
    ("backend kind", ToolFailure("compiler_unavailable", "raised by a script")),
    ("kind outside", ToolFailure("example_kind", "raised by a script")),
]


@pytest.mark.parametrize(("form", "answer"), FORMS, ids=[form for form, _ in FORMS])
def test_each_answer_form_writes_the_log_and_keeps_its_answer(
    root, other_root, form, answer
):
    got = outcome(root, handing(answer))
    assert got == outcome(other_root, silent(answer))
    assert got[0] != "failure" or got[1] != UNWRITABLE
    assert (root / WALK_THROUGH).read_bytes() == LOG.encode("utf-8")
    assert build_logs(other_root) == []
    assert [line["data"] for line in lines(root)] == [
        line["data"] for line in lines(other_root)
    ]


# Tool level: a write that fails.


def unwritable_call(root, script):
    function = function_of(root, script)
    with pytest.raises(ToolFailure) as caught:
        function(request())
    failure = caught.value
    assert type(failure) is ToolFailure
    assert failure.kind == UNWRITABLE
    assert failure.__cause__ is None
    started, ended = lines(root)
    assert started["kind"] == "step_started"
    assert ended["kind"] == "step_ended"
    assert ended["data"] == {
        "step": "correctness_check_sim",
        "execution": 1,
        "spend": {},
        "failure": {"kind": UNWRITABLE, "message": failure.message},
    }
    for word in (str(root), root.as_posix(), "rounds", "build-log", "warning", RUN):
        assert word not in failure.message
    assert "warning" not in log_bytes(root).decode("utf-8")
    before = log_bytes(root)
    asked = []

    def never(*args):
        asked.append(args)
        raise AssertionError("must not be asked")

    again = function_of(root, never, seeds=())
    with pytest.raises(ToolFailure) as repeated:
        again(request())
    assert (repeated.value.kind, repeated.value.message) == (
        UNWRITABLE,
        failure.message,
    )
    assert asked == []
    assert log_bytes(root) == before
    return failure


@pytest.mark.parametrize(("form", "answer"), FORMS, ids=[form for form, _ in FORMS])
def test_a_taken_name_ends_the_step_with_build_log_unwritable(root, form, answer):
    taken = root / WALK_THROUGH
    taken.parent.mkdir(parents=True)
    taken.write_bytes(b"found there\n")
    unwritable_call(root, handing(answer))
    assert taken.read_bytes() == b"found there\n"
    assert build_logs(root) == [WALK_THROUGH]


def test_a_refused_directory_ends_the_step_with_build_log_unwritable(root):
    blocking = root / "runs" / RUN / "rounds" / "0003" / "measure"
    blocking.parent.mkdir(parents=True)
    blocking.write_bytes(b"a file where a directory must be")
    unwritable_call(root, handing(mock_check.default_script))
    assert blocking.read_bytes() == b"a file where a directory must be"
    assert build_logs(root) == []


def test_a_write_that_raises_ends_the_step_with_its_message(root, monkeypatch):
    def refuse(path, log):
        raise BuildLogUnwritable("refused by the test")

    monkeypatch.setattr(build_log, "write", refuse)
    failure = unwritable_call(root, handing(mock_check.default_script))
    assert failure.message == "refused by the test"


# Tool level: negative cases.


def test_a_hand_over_through_a_kept_reference_after_the_call_is_refused(root):
    kept = []

    def keeping(tool, asked, hw_profile, parameters, output_path, keeper):
        kept.append(keeper)
        return mock_check.default_script(
            tool, asked, hw_profile, parameters, output_path, keeper
        )

    result = function_of(root, keeping)(request())
    assert result["outcome"] == "pass"
    (keeper,) = kept
    with pytest.raises(HandOverRefused):
        keeper.hand_over(LOG)
    assert keeper.held() is None
    assert build_logs(root) == []


def test_a_hand_over_from_a_thread_after_the_call_is_refused(root):
    go, refused = threading.Event(), []

    def late(keeper):
        go.wait(10)
        try:
            keeper.hand_over(LOG)
        except HandOverRefused as error:
            refused.append(error)

    threads = []

    def spawning(tool, asked, hw_profile, parameters, output_path, keeper):
        threads.append(threading.Thread(target=late, args=(keeper,)))
        threads[0].start()
        return mock_check.default_script(
            tool, asked, hw_profile, parameters, output_path, keeper
        )

    result = function_of(root, spawning)(request())
    go.set()
    threads[0].join(10)
    assert result["outcome"] == "pass"
    assert len(refused) == 1
    assert build_logs(root) == []


def test_a_second_hand_over_let_pass_is_an_invalid_answer_with_the_first_written(
    root,
):
    def twice(tool, asked, hw_profile, parameters, output_path, keeper):
        keeper.hand_over("first")
        keeper.hand_over("second")
        return mock_check.default_script(
            tool, asked, hw_profile, parameters, output_path, keeper
        )

    got = outcome(root, twice)
    assert got[:2] == ("failure", "operation_answer_invalid")
    assert (root / WALK_THROUGH).read_bytes() == b"first"


def test_a_bytes_log_let_pass_is_an_invalid_answer_and_writes_no_file(root):
    def in_bytes(tool, asked, hw_profile, parameters, output_path, keeper):
        keeper.hand_over(LOG.encode("utf-8"))
        return mock_check.default_script(
            tool, asked, hw_profile, parameters, output_path, keeper
        )

    got = outcome(root, in_bytes)
    assert got[:2] == ("failure", "operation_answer_invalid")
    assert build_logs(root) == []


def test_a_request_to_end_after_a_hand_over_writes_nothing_and_leaves_it_open(root):
    interrupt = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt) as caught:
        function_of(root, handing(interrupt))(request())
    assert caught.value is interrupt
    assert [line["kind"] for line in lines(root)] == ["step_started"]
    assert build_logs(root) == []
    assert not (root / "runs" / RUN / "rounds").exists()


def test_the_default_registry_at_the_mock_leaves_no_build_log(root):
    definition = check_definition.definition(lambda: root)
    result = definition.function(request())
    assert result["outcome"] == "pass"
    assert build_logs(root) == []


# Function level: ask.

PARAMETERS = CheckParameters(seed=7, draws=2, m=2, k=3, n=4)
ASK_TOLERANCE = {"rtol": 1e-5, "atol": 1e-6}


def good_report():
    return mock_check.default_script(TOOL, None, None, PARAMETERS, None, LogKeeper())


def ask(operation, keeper, log_path, parameters=PARAMETERS, **tolerance):
    return check_operation.ask(
        operation,
        {"run_id": RUN},
        {"accelerator": "mock"},
        parameters,
        Path("output"),
        keeper,
        log_path=log_path,
        **(tolerance or ASK_TOLERANCE),
    )


class Handing:
    def __init__(self, answer, log=LOG):
        self.answer, self.log, self.keepers = answer, log, []

    def __call__(self, request, hw_profile, parameters, output_path, keeper):
        self.keepers.append(keeper)
        if self.log is not None:
            keeper.hand_over(self.log)
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer


@pytest.mark.parametrize(
    "keeper", [None, object(), "keeper", type("Kept", (LogKeeper,), {})()]
)
def test_ask_refuses_a_keeper_of_another_type_before_the_call(tmp_path, keeper):
    operation = Handing(good_report())
    with pytest.raises(TypeError):
        ask(operation, keeper, tmp_path / "log.txt")
    assert operation.keepers == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "answer",
    [b"", "time_limit", 17, ValueError("x"), ToolFailure("compiler_unavailable", "m")],
)
def test_ask_closes_the_keeper_and_writes_the_log_whatever_came_back(tmp_path, answer):
    keeper = LogKeeper()
    path = tmp_path / "a" / "log.txt"
    try:
        ask(Handing(answer), keeper, path)
    except (OperationAnswerInvalid, ToolFailure, VerificationArgumentError):
        pass
    assert path.read_bytes() == LOG.encode("utf-8")
    with pytest.raises(HandOverRefused):
        keeper.hand_over("late")
    assert keeper.held() == LOG


def test_ask_writes_before_it_judges_and_returns_the_usual_result(
    tmp_path, monkeypatch
):
    path = tmp_path / "log.txt"
    seen = []
    judge = check_answer.from_answer

    def judging(*args, **kwargs):
        seen.append(path.read_bytes())
        return judge(*args, **kwargs)

    monkeypatch.setattr(check_answer, "from_answer", judging)
    report = good_report()
    result = ask(Handing(report), LogKeeper(), path)
    assert seen == [LOG.encode("utf-8")]
    assert result == judge(report, **PARAMETERS._asdict(), **ASK_TOLERANCE)


def test_ask_writes_nothing_and_reads_no_path_when_nothing_was_handed():
    keeper = LogKeeper()
    result = ask(Handing(good_report(), log=None), keeper, object())
    assert result["outcome"] == "pass"
    with pytest.raises(HandOverRefused):
        keeper.hand_over("late")


def test_ask_closes_the_keeper_on_a_request_to_end_and_writes_nothing(tmp_path):
    keeper = LogKeeper()
    path = tmp_path / "log.txt"
    interrupt = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt) as caught:
        ask(Handing(interrupt), keeper, path)
    assert caught.value is interrupt
    assert not path.exists()
    with pytest.raises(HandOverRefused):
        keeper.hand_over("late")


def test_ask_writes_the_log_before_a_refused_value_of_the_judging_passes(tmp_path):
    path = tmp_path / "log.txt"
    with pytest.raises(VerificationArgumentError):
        ask(Handing(good_report()), LogKeeper(), path, rtol=-0.1, atol=1e-6)
    assert path.read_bytes() == LOG.encode("utf-8")


@pytest.mark.parametrize(
    "answer",
    [b"", "time_limit", 17, ValueError("x"), ToolFailure("compiler_unavailable", "m")],
)
def test_ask_raises_a_fresh_unwritable_in_place_of_any_answer(tmp_path, answer):
    path = tmp_path / "log.txt"
    path.write_bytes(b"taken")
    with pytest.raises(BuildLogUnwritable) as caught:
        ask(Handing(answer), LogKeeper(), path)
    error = caught.value
    assert type(error) is BuildLogUnwritable
    assert error.kind == UNWRITABLE
    assert error.__cause__ is None
    assert error.__context__ is None
    assert str(tmp_path) not in error.message
    assert path.read_bytes() == b"taken"


def test_an_unwritable_the_operation_raises_is_an_invalid_answer(tmp_path):
    path = tmp_path / "log.txt"
    raised = BuildLogUnwritable("raised by the operation")
    with pytest.raises(OperationAnswerInvalid):
        ask(Handing(raised, log=None), LogKeeper(), path)
    assert not path.exists()


def test_a_refused_hand_over_let_pass_is_an_invalid_answer(tmp_path):
    path = tmp_path / "log.txt"
    with pytest.raises(OperationAnswerInvalid):
        ask(Handing(good_report(), log="\ud800"), LogKeeper(), path)
    assert not path.exists()


# Function level: carry_out and check.


def carry_out(operation, keeper, log_path):
    return check_ending.carry_out(
        operation,
        {"run_id": RUN},
        {"accelerator": "mock"},
        PARAMETERS,
        Path("output"),
        keeper,
        log_path=log_path,
        **ASK_TOLERANCE,
    )


@pytest.mark.parametrize(
    "answer",
    [b"", 17, ValueError("x"), ToolFailure("compiler_unavailable", "m")],
)
def test_carry_out_ends_with_build_log_unwritable_for_a_failed_write(tmp_path, answer):
    path = tmp_path / "log.txt"
    path.write_bytes(b"taken")
    with pytest.raises(EndedWithoutOutcome) as caught:
        carry_out(Handing(answer), LogKeeper(), path)
    ended = caught.value
    assert ended.kind == UNWRITABLE
    assert type(ended.message) is str
    assert ended.__cause__ is None
    assert ended.__context__ is None
    assert str(tmp_path) not in ended.message


def test_carry_out_hands_the_very_keeper_and_writes_with_a_tool_failure(tmp_path):
    keeper = LogKeeper()
    path = tmp_path / "log.txt"
    operation = Handing(ToolFailure("compiler_unavailable", "raised"))
    with pytest.raises(EndedWithoutOutcome) as caught:
        carry_out(operation, keeper, path)
    assert (caught.value.kind, caught.value.message) == (
        "compiler_unavailable",
        "raised",
    )
    assert operation.keepers == [keeper]
    assert path.read_bytes() == LOG.encode("utf-8")


def test_carry_out_answers_an_unwritable_the_operation_raises_as_invalid(tmp_path):
    raised = BuildLogUnwritable("raised by the operation")
    with pytest.raises(EndedWithoutOutcome) as caught:
        carry_out(Handing(raised, log=None), LogKeeper(), tmp_path / "log.txt")
    assert caught.value.kind == "operation_answer_invalid"


def test_check_writes_the_handed_log_and_returns_the_result(tmp_path):
    admitted = Admitted(draws=2, m=2, k=3, n=4, **ASK_TOLERANCE)
    path = tmp_path / "log.txt"
    keeper = LogKeeper()
    operation = Handing(good_report())
    result = check_seed.check(
        operation,
        {"run_id": RUN},
        {"accelerator": "mock"},
        admitted,
        7,
        Path("output"),
        keeper,
        log_path=path,
    )
    assert result["outcome"] == "pass"
    assert operation.keepers == [keeper]
    assert path.read_bytes() == LOG.encode("utf-8")


def test_check_ends_with_build_log_unwritable_for_a_failed_write(tmp_path):
    admitted = Admitted(draws=2, m=2, k=3, n=4, **ASK_TOLERANCE)
    path = tmp_path / "log.txt"
    path.write_bytes(b"taken")
    with pytest.raises(EndedWithoutOutcome) as caught:
        check_seed.check(
            Handing(good_report()),
            {"run_id": RUN},
            {"accelerator": "mock"},
            admitted,
            7,
            Path("output"),
            LogKeeper(),
            log_path=path,
        )
    assert caught.value.kind == UNWRITABLE


# Function level: the mock.


def test_the_mock_operation_hands_the_keeper_to_the_script_which_may_hand_a_log():
    keeper = LogKeeper()
    asked = []

    def script(tool, request, hw_profile, parameters, output_path, kept):
        asked.append((tool, kept))
        kept.hand_over("from the script")
        return b"answer"

    assert mock_check.operation(script)({}, {}, PARAMETERS, None, keeper) == b"answer"
    assert asked == [(TOOL, keeper)]
    assert keeper.held() == "from the script"


def test_the_default_script_hands_nothing_and_answers_as_before():
    keeper = LogKeeper()
    answer = mock_check.default_script(TOOL, None, None, PARAMETERS, None, keeper)
    assert keeper.held() is None
    other = mock_check.default_script(TOOL, None, None, PARAMETERS, None, LogKeeper())
    assert answer == other
    result = check_answer.from_answer(answer, **PARAMETERS._asdict(), **ASK_TOLERANCE)
    assert result["outcome"] == "pass"


def test_the_mock_operation_refuses_four_things():
    operation = mock_check.operation(lambda *args: b"")
    with pytest.raises(TypeError):
        operation({}, {}, PARAMETERS, None)
