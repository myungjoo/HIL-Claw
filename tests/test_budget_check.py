import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hilclaw import (
    budget_check,
    caller_check,
    checkout_boundary,
    keys,
    mcp_front,
    run_file_tools,
    tools,
)
from hilclaw.budget_check import (
    EXIT_PASS,
    EXIT_REFUSE,
    REFUSAL,
    SPENDING_TOOLS,
    START,
    main,
)
from hilclaw.instance_file import write
from hilclaw.journal import EMPTY
from hilclaw.run_state_file import replace

RUN = "run-a"
OTHER = "run-b"
CODER = "mcp__hilclaw__coder_run"
CHECK = "mcp__hilclaw__correctness_check"
GENERIC = (
    "budget check: the call was refused because the run is over, "
    "is at its round budget, or could not be checked"
)
PROFILE = {
    "schema_version": 1,
    "accelerator": "acc_a",
    "revision": "rev 1",
    "toolchain": {"cc": "1.0"},
    "host": {"cpu": "cpu x", "os": "os y"},
    "hw_source": "external",
}
OP = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": {"m": 4, "k": 4, "n": 4},
    "dtype": "fp32",
    "layout": "row_major",
}
UNKNOWN_VALUES = ["over", "stopped", "Over", "", None, 0, 1, True, {}, [], {"x": 1}]
OTHER_TOOLS = [
    "mcp__hilclaw__state_read",
    "mcp__hilclaw__round_end",
    "mcp__hilclaw__run_commit",
    "mcp__hilclaw__board_run",
    "mcp__hilclaw__sim_run",
    "mcp__hilclaw__coder_run_",
    "mcp__hilclaw__Coder_run",
    "mcp__other__coder_run",
    "coder_run",
    "coder.run",
    "Bash",
    "Agent",
    "",
    None,
    1,
    [CODER],
    {CODER: CODER},
]


def named(tool):
    return REFUSAL.format(f" of {tool}")


def instance_bytes(**members):
    document = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(PROFILE).name, "record": PROFILE},
        "op_signature": {"key": keys.op_signature_key(OP).name, "record": OP},
        **members,
    }
    return json.dumps(document, indent=2).encode() + b"\n"


@pytest.fixture
def root(tmp_path):
    directory = tmp_path / "data"
    directory.mkdir()
    return directory


def stated(root, round=0, others=None, budget=5, run_id=RUN, **members):
    if budget is not None:
        members["round_budget"] = budget
    write(root, run_id, instance_bytes(**members))
    replace(root, run_id, round, EMPTY, others)
    return root / "runs" / run_id


def payload(tool=CHECK, tool_input=None, **fields):
    found = {
        "session_id": "s",
        "transcript_path": "t",
        "cwd": "c",
        "permission_mode": "dontAsk",
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": {"run_id": RUN} if tool_input is None else tool_input,
        "tool_use_id": "u",
    }
    found.update(fields)
    return json.dumps(found).encode("utf-8")


def decided(data, args):
    stream = io.StringIO()
    status = main(data, stream, args)
    return status, stream.getvalue()


def passes(data, root):
    assert decided(data, [str(root)]) == (EXIT_PASS, "")


def refused(data, args, line=None):
    status, text = decided(data, args)
    assert status == EXIT_REFUSE
    assert text == (GENERIC if line is None else line) + "\n"
    return text


def test_spending_tools_are_the_mcp_names_of_coder_run_and_correctness_check():
    assert isinstance(SPENDING_TOOLS, tuple)
    assert len(SPENDING_TOOLS) == len(set(SPENDING_TOOLS)) == 2
    registered = tools.default_registry(lambda: ".").names()
    by_mcp = {
        caller_check.TOOL_PREFIX + mcp_front.mcp_name(name): name for name in registered
    }
    assert all(tool in by_mcp for tool in SPENDING_TOOLS)
    assert {by_mcp[tool] for tool in SPENDING_TOOLS} == {
        "coder.run",
        "correctness.check",
    }
    assert SPENDING_TOOLS == (CODER, CHECK)


@pytest.mark.parametrize("tool", SPENDING_TOOLS)
def test_round_zero_below_its_budget_gets_no_decision(root, tool, capsys):
    stated(root, 0, budget=5)
    passes(payload(tool), root)
    assert capsys.readouterr() == ("", "")


def test_round_below_its_budget_gets_no_decision(root):
    stated(root, 4, budget=5)
    passes(payload(CODER), root)


@pytest.mark.parametrize("round", [0, 3, 50])
def test_a_run_stating_no_round_budget_gets_no_decision(root, round):
    stated(root, round, budget=None)
    passes(payload(CODER), root)
    passes(payload(CHECK), root)


@pytest.mark.parametrize(("round", "budget"), [(5, 5), (6, 5), (1, 1), (2, 1)])
def test_a_run_at_or_beyond_its_round_budget_is_refused(root, round, budget):
    stated(root, round, budget=budget)
    refused(payload(CODER), [str(root)], named(CODER))
    refused(payload(CHECK), [str(root)], named(CHECK))


@pytest.mark.parametrize("value", UNKNOWN_VALUES)
def test_any_run_status_is_refused(root, value):
    stated(root, 1, {"run_status": value}, budget=5)
    refused(payload(CHECK), [str(root)], named(CHECK))


@pytest.mark.parametrize("value", UNKNOWN_VALUES)
def test_instance_json_is_not_read_when_a_run_status_is_held(root, value, monkeypatch):
    replace(root, RUN, 0, EMPTY, {"run_status": value})
    read = run_file_tools.read
    names = []

    def recording(data_root, run_id, name):
        names.append(name)
        return read(data_root, run_id, name)

    monkeypatch.setattr(run_file_tools, "read", recording)
    refused(payload(CODER), [str(root)], named(CODER))
    assert names == ["STATE.json"]


def test_unknown_members_are_passed_over(root):
    stated(
        root, 2, {"note": "x", "budget_note": {"round": 9}}, budget=5, extra_member=[1]
    )
    passes(payload(CODER), root)


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"\xff\xfe",
        payload().replace(b'"cwd": "c"', b'"cwd": "\xe9"'),
        b"not json",
        b"[]",
        b'"PreToolUse"',
        b"null",
        b"1",
        payload() + b"{}",
        "{}".encode("utf-16"),
    ],
)
def test_input_that_is_not_one_utf8_json_object_is_refused(root, data):
    stated(root)
    refused(data, [str(root)])


@pytest.mark.parametrize(
    "data",
    [
        payload()[:-1] + b', "tool_name": "mcp__hilclaw__correctness_check"}',
        payload(tool_input={"run_id": RUN}).replace(
            b'{"run_id": "run-a"}', b'{"run_id": "run-a", "run_id": "run-a"}'
        ),
        payload(tool_input={"run_id": RUN, "x": {"a": 1}}).replace(
            b'{"a": 1}', b'{"a": 1, "a": 1}'
        ),
    ],
)
def test_a_repeated_key_at_any_depth_is_refused(root, data):
    stated(root)
    refused(data, [str(root)])


@pytest.mark.parametrize(
    "event", ["PostToolUse", "pretooluse", "PreToolUse ", "", None, 1, ["PreToolUse"]]
)
def test_another_hook_event_is_refused(root, event):
    stated(root)
    refused(payload(CHECK, hook_event_name=event), [str(root)], named(CHECK))


def test_a_missing_hook_event_is_refused(root):
    stated(root)
    data = json.loads(payload(CHECK))
    del data["hook_event_name"]
    refused(json.dumps(data).encode(), [str(root)], named(CHECK))


@pytest.mark.parametrize("tool", OTHER_TOOLS)
def test_a_tool_that_is_not_a_spending_tool_is_refused(root, tool):
    stated(root)
    refused(payload(tool), [str(root)])


def test_a_missing_tool_name_is_refused(root):
    stated(root)
    data = json.loads(payload())
    del data["tool_name"]
    refused(json.dumps(data).encode(), [str(root)])


@pytest.mark.parametrize("tool_input", [[], "run-a", None, 1, [{"run_id": RUN}]])
def test_a_tool_input_that_is_not_an_object_is_refused(root, tool_input):
    stated(root)
    data = json.loads(payload(CODER))
    data["tool_input"] = tool_input
    refused(json.dumps(data).encode(), [str(root)], named(CODER))


def test_a_missing_tool_input_is_refused(root):
    stated(root)
    data = json.loads(payload(CODER))
    del data["tool_input"]
    refused(json.dumps(data).encode(), [str(root)], named(CODER))


@pytest.mark.parametrize(
    "tool_input",
    [
        {},
        {"runid": RUN},
        {"run_id": None},
        {"run_id": 1},
        {"run_id": [RUN]},
        {"run_id": ""},
        {"run_id": "Run-A"},
        {"run_id": "-run"},
        {"run_id": "../run-a"},
        {"run_id": "run-a/.."},
        {"run_id": "a" * 65},
    ],
)
def test_a_run_id_missing_not_a_string_or_not_a_run_id_is_refused(root, tool_input):
    stated(root)
    refused(payload(CODER, tool_input), [str(root)], named(CODER))


def test_another_run_that_is_not_over_gets_no_decision(root):
    stated(root, 5, {"run_status": "over"}, budget=5)
    stated(root, 1, budget=5, run_id=OTHER)
    passes(payload(CHECK, {"run_id": OTHER, "attempt": "x"}), root)
    refused(payload(CHECK, {"run_id": RUN}), [str(root)], named(CHECK))


def test_a_missing_data_root_argument_is_refused(root):
    stated(root)
    refused(payload(CODER), [], named(CODER))


def test_more_than_one_argument_is_refused(root):
    stated(root)
    refused(payload(CODER), [str(root), str(root)], named(CODER))


@pytest.mark.parametrize("argument", [None, 1, b"data", ""])
def test_an_argument_that_is_no_path_string_is_refused(root, argument):
    stated(root)
    refused(payload(CODER), [argument], named(CODER))


def test_a_data_root_naming_no_directory_is_refused(root, tmp_path):
    stated(root)
    refused(payload(CODER), [str(tmp_path / "absent")], named(CODER))
    plain = tmp_path / "plain"
    plain.write_bytes(b"")
    refused(payload(CODER), [str(plain)], named(CODER))


def test_a_relative_data_root_is_used_as_given(root, tmp_path, monkeypatch):
    stated(root)
    monkeypatch.chdir(tmp_path)
    assert decided(payload(CODER), ["data"]) == (EXIT_PASS, "")
    monkeypatch.chdir(root)
    refused(payload(CODER), ["data"], named(CODER))


def test_the_data_root_comes_only_from_the_argument(root, tmp_path, monkeypatch):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    stated(elsewhere, 5, {"run_status": "over"})
    stated(root, 0)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(elsewhere))
    monkeypatch.setenv("HILCLAW_DATA_REPO_LOCAL_PATH", str(elsewhere))
    monkeypatch.chdir(elsewhere)
    passes(payload(CODER), root)
    refused(payload(CODER), [str(elsewhere)], named(CODER))
    monkeypatch.setenv("HILCLAW_DATA_REPO_LOCAL_PATH", str(root))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    refused(payload(CODER), [], named(CODER))


def other_version():
    return b'{"schema_version": 2}\n'


def not_regular(path):
    path.mkdir(parents=True)


def unreadable(monkeypatch, name):
    original = Path.read_bytes

    def failing(self):
        if self.name == name:
            raise PermissionError(13, "denied", str(self))
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", failing)


def assert_kind(root, name, kind):
    with pytest.raises(tools.ToolFailure) as failure:
        run_file_tools.read(str(root), RUN, name)
    assert failure.value.kind == kind


def test_a_missing_state_file_is_refused(root):
    write(root, RUN, instance_bytes(round_budget=5))
    assert_kind(root, "STATE.json", "run_file_missing")
    refused(payload(CODER), [str(root)], named(CODER))


def test_a_missing_run_directory_is_refused(root):
    refused(payload(CODER), [str(root)], named(CODER))


@pytest.mark.parametrize(
    ("content", "kind"),
    [
        (b"", "run_file_invalid"),
        (b"{}\n", "run_file_invalid"),
        (b'{"schema_version": 1, "round": -1}\n', "run_file_invalid"),
        (b"\xff", "run_file_invalid"),
        (other_version(), "run_file_unsupported"),
    ],
)
def test_an_invalid_or_other_version_state_file_is_refused(root, content, kind):
    stated(root)
    (root / "runs" / RUN / "STATE.json").write_bytes(content)
    assert_kind(root, "STATE.json", kind)
    refused(payload(CODER), [str(root)], named(CODER))


def test_a_state_file_that_is_no_regular_file_is_refused(root):
    write(root, RUN, instance_bytes(round_budget=5))
    not_regular(root / "runs" / RUN / "STATE.json")
    assert_kind(root, "STATE.json", "run_file_invalid")
    refused(payload(CODER), [str(root)], named(CODER))


def test_an_unreadable_state_file_is_refused(root, monkeypatch):
    stated(root)
    unreadable(monkeypatch, "STATE.json")
    assert_kind(root, "STATE.json", "run_file_unreadable")
    refused(payload(CODER), [str(root)], named(CODER))


def test_a_missing_instance_file_is_refused(root):
    replace(root, RUN, 0, EMPTY)
    assert_kind(root, "instance.json", "run_file_missing")
    refused(payload(CODER), [str(root)], named(CODER))


@pytest.mark.parametrize(
    ("content", "kind"),
    [
        (b"", "run_file_invalid"),
        (b"{}\n", "run_file_invalid"),
        (b'{"schema_version": 1}\n', "run_file_invalid"),
        (instance_bytes(round_budget=-1), "run_file_invalid"),
        (instance_bytes(round_budget="5"), "run_file_invalid"),
        (other_version(), "run_file_unsupported"),
    ],
)
def test_an_invalid_or_other_version_instance_file_is_refused(root, content, kind):
    replace(root, RUN, 0, EMPTY)
    (root / "runs" / RUN / "instance.json").write_bytes(content)
    assert_kind(root, "instance.json", kind)
    refused(payload(CODER), [str(root)], named(CODER))


def test_an_instance_file_that_is_no_regular_file_is_refused(root):
    replace(root, RUN, 0, EMPTY)
    not_regular(root / "runs" / RUN / "instance.json")
    assert_kind(root, "instance.json", "run_file_invalid")
    refused(payload(CODER), [str(root)], named(CODER))


def test_an_unreadable_instance_file_is_refused(root, monkeypatch):
    stated(root)
    unreadable(monkeypatch, "instance.json")
    assert_kind(root, "instance.json", "run_file_unreadable")
    refused(payload(CODER), [str(root)], named(CODER))


@pytest.mark.parametrize(
    "error", [RuntimeError("boom"), OSError("disk"), KeyError("k"), ValueError("v")]
)
def test_any_exception_of_the_reader_is_refused(root, monkeypatch, error):
    stated(root)

    def raising(*_):
        raise error

    monkeypatch.setattr(run_file_tools, "read", raising)
    text = refused(payload(CODER), [str(root)], named(CODER))
    assert str(error) not in text.replace(named(CODER), "")


def test_an_exception_of_the_run_id_check_is_refused(root, monkeypatch):
    stated(root)

    def raising(_):
        raise RuntimeError("check")

    monkeypatch.setattr(budget_check.layout, "check_run_id", raising)
    refused(payload(CODER), [str(root)], named(CODER))


def test_a_failing_stdin_is_refused(root, monkeypatch, capsys):
    stated(root)
    monkeypatch.setattr(sys, "stdin", io.StringIO("no buffer"))
    assert main(None, None, [str(root)]) == EXIT_REFUSE
    assert capsys.readouterr() == ("", GENERIC + "\n")


def test_a_failing_stderr_still_refuses(root):
    class Broken(io.StringIO):
        def write(self, _):
            raise OSError("closed")

    assert main(b"not json", Broken(), [str(root)]) == EXIT_REFUSE


def test_the_defaults_are_the_process_own(root, monkeypatch, capsys):
    stated(root)
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(payload(CODER))))
    monkeypatch.setattr(sys, "argv", ["-c", str(root)])
    assert main() == EXIT_PASS
    assert capsys.readouterr() == ("", "")
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(payload(CODER))))
    monkeypatch.setattr(sys, "argv", ["-c"])
    assert main() == EXIT_REFUSE
    assert capsys.readouterr() == ("", named(CODER) + "\n")


def test_nothing_is_printed_on_stdout_and_no_allow_is_given(root, capsys):
    stated(root, 0)
    for data in (payload(CODER), payload(CHECK), payload("Bash"), b"x"):
        decided(data, [str(root)])
    stated(root, 9, run_id=OTHER)
    decided(payload(CODER, {"run_id": OTHER}), [str(root)])
    out, _ = capsys.readouterr()
    assert out == ""


def test_the_line_shows_no_run_id_path_argument_or_value(root, tmp_path):
    distinctive = tmp_path / "zq-distinctive-root"
    distinctive.mkdir()
    stated(distinctive, 7, budget=5)
    lines = [
        refused(payload(CODER), [str(distinctive)], named(CODER)),
        refused(
            payload(CODER, {"run_id": "../../etc/passwd"}),
            [str(distinctive)],
            named(CODER),
        ),
        refused(
            payload(CODER, {"run_id": "..\\zq-secret"}),
            [str(distinctive)],
            named(CODER),
        ),
        refused(payload("mcp__hilclaw__zq_tool"), [str(distinctive)]),
        refused(payload(CODER), [str(distinctive / "zq-absent")], named(CODER)),
    ]
    for text in lines:
        assert text.count("\n") == 1
        for fragment in (
            "zq",
            "etc",
            "passwd",
            "run-a",
            "7",
            "5",
            os.sep,
            "STATE",
            "instance",
        ):
            assert fragment not in text
        assert "allow" not in text


def test_the_line_is_fixed():
    assert REFUSAL.format("") == GENERIC
    assert named(CODER) == (
        "budget check: the call of mcp__hilclaw__coder_run was refused because the run is over, "
        "is at its round budget, or could not be checked"
    )


def test_walk_through_over_written_in_the_same_turn_refuses_a_later_coder_run(root):
    stated(root, 2, budget=5)
    passes(payload(CODER), root)
    replace(root, RUN, 3, EMPTY, {"run_status": "over"})
    refused(payload(CODER), [str(root)], named(CODER))


def test_walk_through_a_fresh_run_with_an_invalid_instance_file_refuses_coder_run(root):
    replace(root, RUN, 0, EMPTY)
    (root / "runs" / RUN / "instance.json").write_bytes(b"{")
    refused(payload(CODER), [str(root)], named(CODER))


def test_walk_through_coder_run_with_no_run_id_is_refused(root):
    stated(root)
    refused(payload(CODER, {"spec": "x"}), [str(root)], named(CODER))


def started(data, *args):
    return subprocess.run(
        [sys.executable, "-I", "-c", START, checkout_boundary.PACKAGE_DIRECTORY, *args],
        input=data,
        capture_output=True,
        timeout=120,
        check=False,
    )


def test_started_as_the_turn_loop_will(root):
    stated(root, 0, budget=5)
    stated(root, 5, {"run_status": "over"}, run_id=OTHER)
    below = started(payload(CODER), str(root))
    assert (below.returncode, below.stdout, below.stderr) == (EXIT_PASS, b"", b"")
    over = started(payload(CODER, {"run_id": OTHER}), str(root))
    assert over.returncode == EXIT_REFUSE
    assert over.stdout == b""
    assert over.stderr.decode("utf-8").replace("\r\n", "\n") == named(CODER) + "\n"


def test_started_without_the_data_root_argument_is_refused(root):
    stated(root, 0, budget=5)
    missing = started(payload(CODER))
    assert missing.returncode == EXIT_REFUSE
    assert missing.stdout == b""
    assert missing.stderr.decode("utf-8").replace("\r\n", "\n") == named(CODER) + "\n"
