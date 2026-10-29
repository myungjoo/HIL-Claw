import threading
from pathlib import Path

import pytest

from hilclaw import build_log, check_operation, layout, once_write, tools
from hilclaw.build_log import (
    KIND_BUILD_LOG_UNWRITABLE,
    BuildLogUnwritable,
    HandOverRefused,
    LogKeeper,
    write,
)
from hilclaw.check_parameters import CheckParameters

# Synthetic values only: no log of a real compiler.
SIM = "correctness_check_sim_v2"
LOGS = [
    "x.c:1:1: error: synthetic\n",
    "x.c:2: warning: é ü 漢字 \U0001f600",
    "replaced � byte",
    "crlf\r\nlf\ncr\rend",
    "no trailing newline",
    "",
]
SECRET = "SYNTHETIC-LOG-BYTES-7f3a"


class StrSubclass(str):
    pass


def final(root, execution=1):
    return layout.build_log_file(root, "r1", 3, 2, 1, SIM, execution)


def leftovers(root):
    return sorted(p.name for p in root.rglob("*.tmp"))


def refusal(keeper, value):
    with pytest.raises(HandOverRefused) as caught:
        keeper.hand_over(value)
    return caught.value


def test_kind_is_that_of_adr_0078():
    assert KIND_BUILD_LOG_UNWRITABLE == "build_log_unwritable"
    assert BuildLogUnwritable.kind == KIND_BUILD_LOG_UNWRITABLE


def test_errors_are_exceptions_and_no_tool_failures():
    for error in (HandOverRefused, BuildLogUnwritable):
        assert issubclass(error, Exception)
        assert not issubclass(error, tools.ToolFailure)


def test_unwritable_error_carries_kind_and_message():
    error = BuildLogUnwritable("synthetic message")
    assert error.kind == "build_log_unwritable"
    assert error.message == "synthetic message"
    assert tools.ToolFailure(error.kind, error.message).kind == error.kind


@pytest.mark.parametrize("message", [None, b"m", 1, StrSubclass("m")])
def test_unwritable_error_refuses_a_message_that_is_no_str(message):
    with pytest.raises(TypeError):
        BuildLogUnwritable(message)


@pytest.mark.parametrize("log", LOGS)
def test_keeper_holds_what_was_handed_over(log):
    keeper = LogKeeper()
    assert keeper.hand_over(log) is None
    keeper.close()
    assert keeper.held() is log


def test_nothing_handed_over_is_none_and_empty_is_a_log():
    keeper = LogKeeper()
    keeper.close()
    assert keeper.held() is None
    keeper = LogKeeper()
    keeper.hand_over("")
    assert keeper.held() == ""
    assert keeper.held() is not None


def test_second_hand_over_is_refused_and_changes_nothing():
    keeper = LogKeeper()
    keeper.hand_over("first")
    error = refusal(keeper, "second")
    assert keeper.held() == "first"
    assert "second" not in error.message
    keeper = LogKeeper()
    keeper.hand_over("")
    refusal(keeper, "")
    assert keeper.held() == ""


@pytest.mark.parametrize(
    "value", [b"bytes", bytearray(b"x"), None, 1, 1.0, StrSubclass(SECRET), [SECRET]]
)
def test_value_that_is_no_str_is_refused(value):
    keeper = LogKeeper()
    error = refusal(keeper, value)
    assert SECRET not in str(error)
    assert keeper.held() is None


def test_lone_surrogate_is_refused_without_showing_it():
    keeper = LogKeeper()
    error = refusal(keeper, SECRET + "\ud800")
    assert SECRET not in str(error)
    assert "ud800" not in str(error)
    assert error.__cause__ is None
    assert error.__context__ is None
    assert keeper.held() is None


def test_a_refused_hand_over_leaves_room_for_one_log():
    keeper = LogKeeper()
    refusal(keeper, b"bytes")
    refusal(keeper, "\udfff")
    keeper.hand_over("accepted")
    assert keeper.held() == "accepted"


def test_hand_over_after_close_is_refused_and_changes_nothing():
    keeper = LogKeeper()
    keeper.close()
    refusal(keeper, "late")
    assert keeper.held() is None
    keeper = LogKeeper()
    keeper.hand_over("kept")
    keeper.close()
    keeper.close()
    refusal(keeper, "late")
    assert keeper.held() == "kept"


def test_refusal_passed_by_an_operation_is_answered_operation_answer_invalid():
    def operation(request, hw_profile, parameters, output_path, keeper):
        keeper.hand_over(b"no text")

    parameters = CheckParameters(seed=1, draws=1, m=1, k=1, n=1)
    with pytest.raises(check_operation.OperationAnswerInvalid) as caught:
        check_operation.ask(
            operation,
            {},
            {},
            parameters,
            None,
            LogKeeper(),
            log_path=Path("zq7-log-zq7") / "build-log.txt",
            rtol=0.0,
            atol=0.0,
        )
    assert caught.value.kind == "operation_answer_invalid"


def test_keeper_accepts_one_log_among_threads():
    keeper = LogKeeper()
    accepted = []

    def hand(number):
        try:
            keeper.hand_over(str(number))
            accepted.append(number)
        except HandOverRefused:
            pass

    threads = [threading.Thread(target=hand, args=(n,)) for n in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(accepted) == 1
    assert keeper.held() == str(accepted[0])


def test_repr_of_keeper_hides_the_log():
    keeper = LogKeeper()
    keeper.hand_over(SECRET)
    assert SECRET not in repr(keeper)
    keeper.close()
    assert SECRET not in repr(keeper)
    assert "LogKeeper" in repr(keeper)


def test_keeper_touches_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    keeper = LogKeeper()
    keeper.hand_over("log")
    keeper.close()
    keeper.held()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("log", LOGS)
def test_write_gives_exactly_the_utf8_bytes(tmp_path, log):
    path = final(tmp_path)
    assert write(path, log) is None
    assert path.read_bytes() == log.encode("utf-8")
    assert not path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert leftovers(tmp_path) == []


def test_empty_log_gives_an_empty_file(tmp_path):
    path = final(tmp_path)
    write(path, "")
    assert path.is_file()
    assert path.stat().st_size == 0


def test_write_creates_only_the_measure_attempt_chain(tmp_path):
    path = final(tmp_path)
    write(path, "log")
    created = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    assert created == [
        "runs",
        "runs/r1",
        "runs/r1/rounds",
        "runs/r1/rounds/0003",
        "runs/r1/rounds/0003/measure",
        "runs/r1/rounds/0003/measure/candidates",
        "runs/r1/rounds/0003/measure/candidates/02",
        "runs/r1/rounds/0003/measure/candidates/02/attempts",
        "runs/r1/rounds/0003/measure/candidates/02/attempts/01",
        final(tmp_path).relative_to(tmp_path).as_posix(),
    ]


def test_write_into_an_existing_directory_and_a_str_path(tmp_path):
    path = final(tmp_path)
    path.parent.mkdir(parents=True)
    (path.parent / "build.json").write_bytes(b"{}\n")
    write(str(final(tmp_path, 2)), "second")
    assert final(tmp_path, 2).read_bytes() == b"second"
    assert (path.parent / "build.json").read_bytes() == b"{}\n"


def assert_hides(error, path, *texts):
    message = str(error)
    assert error.kind == KIND_BUILD_LOG_UNWRITABLE
    assert error.message == message
    assert str(path) not in message
    assert path.name not in message
    assert "runs" not in message
    for text in texts:
        assert text not in message
    assert error.__cause__ is None
    assert error.__context__ is None


def test_taken_name_is_unwritable_and_left_as_found(tmp_path):
    path = final(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"of another writer")
    with pytest.raises(BuildLogUnwritable) as caught:
        write(path, SECRET)
    assert_hides(caught.value, path, SECRET)
    assert path.read_bytes() == b"of another writer"
    assert leftovers(tmp_path) == []


def test_same_log_twice_is_unwritable_the_second_time(tmp_path):
    path = final(tmp_path)
    write(path, "same")
    with pytest.raises(BuildLogUnwritable):
        write(path, "same")
    assert path.read_bytes() == b"same"


def test_file_where_a_directory_is_needed_is_unwritable(tmp_path):
    path = final(tmp_path)
    blocker = tmp_path / "runs" / "r1" / "rounds"
    blocker.parent.mkdir(parents=True)
    blocker.write_bytes(b"not a directory")
    with pytest.raises(BuildLogUnwritable) as caught:
        write(path, SECRET)
    assert_hides(caught.value, path, SECRET, "rounds")
    assert blocker.read_bytes() == b"not a directory"


def test_directory_under_the_final_name_is_unwritable(tmp_path):
    path = final(tmp_path)
    path.mkdir(parents=True)
    with pytest.raises(BuildLogUnwritable):
        write(path, "log")
    assert path.is_dir()
    assert list(path.iterdir()) == []


@pytest.mark.parametrize(
    "error",
    [
        PermissionError(13, "SYNTHETIC-OS-TEXT"),
        OSError(28, "SYNTHETIC-OS-TEXT"),
        FileExistsError(17, "SYNTHETIC-OS-TEXT"),
    ],
)
def test_os_error_of_the_write_is_unwritable_and_hidden(tmp_path, monkeypatch, error):
    def fail(path, content):
        raise error

    monkeypatch.setattr(once_write, "write_once", fail)
    path = final(tmp_path)
    with pytest.raises(BuildLogUnwritable) as caught:
        write(path, SECRET)
    assert_hides(caught.value, path, SECRET, "SYNTHETIC-OS-TEXT")
    assert not path.exists()


def test_os_error_of_mkdir_is_unwritable_and_hidden(tmp_path, monkeypatch):
    def fail(self, *arguments, **named):
        raise PermissionError(13, "SYNTHETIC-OS-TEXT", str(self))

    monkeypatch.setattr(build_log.Path, "mkdir", fail)
    path = final(tmp_path)
    with pytest.raises(BuildLogUnwritable) as caught:
        write(path, SECRET)
    assert_hides(caught.value, path, SECRET, "SYNTHETIC-OS-TEXT")


def test_taken_and_refused_messages_differ(tmp_path, monkeypatch):
    path = final(tmp_path)
    write(path, "x")
    with pytest.raises(BuildLogUnwritable) as taken:
        write(path, "x")

    def fail(path, content):
        raise OSError

    monkeypatch.setattr(once_write, "write_once", fail)
    with pytest.raises(BuildLogUnwritable) as refused:
        write(final(tmp_path, 2), "x")
    assert taken.value.message != refused.value.message


@pytest.mark.parametrize("log", [b"bytes", None, 1, StrSubclass("log")])
def test_write_refuses_a_log_that_is_no_str(tmp_path, log):
    with pytest.raises(TypeError):
        write(final(tmp_path), log)
    assert list(tmp_path.iterdir()) == []


def test_write_refuses_a_lone_surrogate_without_touching_files(tmp_path):
    with pytest.raises(ValueError) as caught:
        write(final(tmp_path), SECRET + "\ud800")
    assert not isinstance(caught.value, BuildLogUnwritable)
    assert SECRET not in str(caught.value)
    assert caught.value.__context__ is None
    assert list(tmp_path.iterdir()) == []


def test_interrupt_passes_through(tmp_path, monkeypatch):
    def interrupt(path, content):
        raise KeyboardInterrupt

    monkeypatch.setattr(once_write, "write_once", interrupt)
    with pytest.raises(KeyboardInterrupt):
        write(final(tmp_path), "log")
