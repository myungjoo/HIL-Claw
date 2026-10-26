import io
import json
import os
import subprocess
import sys

import pytest

from hilclaw import caller_check, checkout_boundary, turn_definition, turn_permissions
from hilclaw.caller_check import (
    ENV_PROJECT_DIR,
    EVENT,
    EXIT_PASS,
    EXIT_REFUSE,
    REFUSAL,
    START,
    TOOL_PREFIX,
    main,
)
from hilclaw.turn_permissions import AGENTS_DIRECTORY, ROUND_MANAGER_TOOLS

GENERIC = (
    "caller check: the call was refused because the calling agent "
    "does not hold the tool or could not be checked"
)
EVALUATOR_ID = {"agent_id": "a1b2", "agent_type": "evaluator"}
CODER_ID = {"agent_id": "c3d4", "agent_type": "coder-driver"}
EVALUATOR_HELD = (
    "mcp__hilclaw__correctness_check",
    "mcp__hilclaw__state_read",
    "mcp__hilclaw__instance_read",
    "mcp__hilclaw__run_fresh",
    "mcp__hilclaw__verdicts_write",
    "mcp__hilclaw__hypotheses_read",
    "mcp__hilclaw__checks_read",
    "mcp__hilclaw__timings_compare",
)
CODER_HELD = ("mcp__hilclaw__spec_write", "mcp__hilclaw__coder_run")


def named(tool):
    return REFUSAL.format(f" of {tool}")


@pytest.fixture
def session(tmp_path):
    turn_definition.put(tmp_path)
    return tmp_path


def payload(tool, **fields):
    found = {
        "session_id": "s",
        "transcript_path": "t",
        "cwd": "c",
        "permission_mode": "dontAsk",
        "hook_event_name": EVENT,
        "tool_name": tool,
        "tool_input": {},
        "tool_use_id": "u",
    }
    found.update(fields)
    return json.dumps(found).encode("utf-8")


def run(data, directory):
    stderr = io.StringIO()
    environ = {} if directory is None else {ENV_PROJECT_DIR: str(directory)}
    status = main(data, stderr, environ)
    return status, stderr.getvalue()


def passes(data, directory):
    assert run(data, directory) == (EXIT_PASS, "")


def refuses(data, directory, line=GENERIC):
    status, text = run(data, directory)
    assert status == EXIT_REFUSE
    assert text == line + "\n"


def write_agent(session, file, name, tools):
    directory = session.joinpath(*AGENTS_DIRECTORY)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / file).write_text(
        f"---\nname: {name}\ntools: {tools}\n---\nbody\n", encoding="utf-8"
    )


def test_public_constants():
    assert EXIT_PASS == 0
    assert EXIT_REFUSE == 2
    assert EVENT == "PreToolUse"
    assert ENV_PROJECT_DIR == "CLAUDE_PROJECT_DIR"
    assert TOOL_PREFIX == "mcp__hilclaw__"
    assert REFUSAL.format("") == GENERIC
    assert "allow" not in REFUSAL
    assert "hilclaw.caller_check" in START
    assert caller_check.__doc__


@pytest.mark.parametrize("tool", ROUND_MANAGER_TOOLS)
def test_main_session_holds_its_tools(session, tool):
    passes(payload(tool), session)


@pytest.mark.parametrize("tool", EVALUATOR_HELD)
def test_evaluator_holds_its_tools(session, tool):
    passes(payload(tool, **EVALUATOR_ID), session)


@pytest.mark.parametrize("tool", CODER_HELD)
def test_coder_driver_holds_its_tools(session, tool):
    passes(payload(tool, **CODER_ID), session)


@pytest.mark.parametrize(
    "tool",
    [
        "mcp__hilclaw__verdicts_write",
        "mcp__hilclaw__coder_run",
        "mcp__hilclaw__correctness_check",
        "mcp__hilclaw__checks_read",
        "mcp__hilclaw__spec_write",
        "mcp__hilclaw__blob_push",
        "mcp__hilclaw__blob_fetch",
        "mcp__hilclaw__board_run",
    ],
)
def test_main_session_refused_what_it_does_not_hold(session, tool):
    refuses(payload(tool), session, named(tool))


@pytest.mark.parametrize(
    ("ids", "tool"),
    [
        (EVALUATOR_ID, "mcp__hilclaw__run_commit"),
        (EVALUATOR_ID, "mcp__hilclaw__state_write"),
        (EVALUATOR_ID, "mcp__hilclaw__coder_run"),
        (EVALUATOR_ID, "mcp__hilclaw__blob_push"),
        (EVALUATOR_ID, "mcp__hilclaw__blob_fetch"),
        (CODER_ID, "mcp__hilclaw__verdicts_write"),
        (CODER_ID, "mcp__hilclaw__state_read"),
        (CODER_ID, "mcp__hilclaw__blob_push"),
        (CODER_ID, "mcp__hilclaw__blob_fetch"),
    ],
)
def test_sub_agent_refused_what_it_does_not_hold(session, ids, tool):
    refuses(payload(tool, **ids), session, named(tool))


@pytest.mark.parametrize("tool", ["Read", "Grep", "Glob", "Agent", "Bash"])
def test_built_in_tool_refused(session, tool):
    refuses(payload(tool), session)
    refuses(payload(tool, **EVALUATOR_ID), session)


@pytest.mark.parametrize(
    "tool", ["mcp__other__state_read", "mcp__hilclawx__state_read", "mcp__hilclaw", ""]
)
def test_other_server_refused(session, tool):
    refuses(payload(tool), session)


@pytest.mark.parametrize("name", ["general-purpose", "Explore", "Plan", "nobody"])
def test_agent_type_naming_no_file(session, name):
    data = payload("mcp__hilclaw__state_read", agent_id="x", agent_type=name)
    refuses(data, session, named("mcp__hilclaw__state_read"))


@pytest.mark.parametrize(
    "fields",
    [
        {"agent_id": "x"},
        {"agent_type": "evaluator"},
        {"agent_id": None},
        {"agent_type": None},
        {"agent_id": "x", "agent_type": ""},
        {"agent_id": "x", "agent_type": None},
        {"agent_id": "x", "agent_type": 1},
        {"agent_id": "x", "agent_type": ["evaluator"]},
        {"agent_id": "", "agent_type": "evaluator"},
        {"agent_id": None, "agent_type": "evaluator"},
        {"agent_id": 7, "agent_type": "evaluator"},
        {"agent_id": {}, "agent_type": "evaluator"},
    ],
)
def test_caller_it_cannot_tell(session, fields):
    refuses(
        payload("mcp__hilclaw__state_read", **fields),
        session,
        named("mcp__hilclaw__state_read"),
    )


def test_agent_type_names_two_files(session):
    write_agent(session, "zz.md", "evaluator", "mcp__hilclaw__blob_push")
    tool = "mcp__hilclaw__verdicts_write"
    refuses(payload(tool, **EVALUATOR_ID), session, named(tool))
    refuses(
        payload("mcp__hilclaw__blob_push", **EVALUATOR_ID),
        session,
        named("mcp__hilclaw__blob_push"),
    )
    refuses(
        payload("mcp__hilclaw__state_write"),
        session,
        named("mcp__hilclaw__state_write"),
    )


@pytest.mark.parametrize(
    ("file", "text"),
    [
        ("bad.md", "---\nname: x\ntools: Bash\n---\n"),
        ("bad.md", "---\nname: general-purpose\ntools: Read\n---\n"),
        ("bad.md", "no frontmatter"),
        ("bad.md", "---\nname: x\npermissionMode: auto\ntools: Read\n---\n"),
    ],
)
def test_refused_definition_refuses_every_caller(session, file, text):
    (session.joinpath(*AGENTS_DIRECTORY) / file).write_text(text, encoding="utf-8")
    refuses(
        payload("mcp__hilclaw__state_write"),
        session,
        named("mcp__hilclaw__state_write"),
    )
    refuses(
        payload("mcp__hilclaw__verdicts_write", **EVALUATOR_ID),
        session,
        named("mcp__hilclaw__verdicts_write"),
    )


def test_unreadable_agent_file_refuses_every_caller(session, monkeypatch):
    real = open

    def failing(path, *args, **kwargs):
        if str(path).endswith(".md"):
            raise PermissionError("denied /secret/path")
        return real(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", failing)
    status, text = run(payload("mcp__hilclaw__state_write"), session)
    assert status == EXIT_REFUSE
    assert "secret" not in text
    assert text == named("mcp__hilclaw__state_write") + "\n"


def test_agents_entry_is_a_file(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "agents").write_text("x", encoding="utf-8")
    refuses(
        payload("mcp__hilclaw__state_write"),
        tmp_path,
        named("mcp__hilclaw__state_write"),
    )


def test_no_agents_directory(tmp_path):
    passes(payload("mcp__hilclaw__state_write"), tmp_path)
    refuses(
        payload("mcp__hilclaw__verdicts_write"),
        tmp_path,
        named("mcp__hilclaw__verdicts_write"),
    )
    refuses(
        payload("mcp__hilclaw__state_read", **EVALUATOR_ID),
        tmp_path,
        named("mcp__hilclaw__state_read"),
    )


def test_agent_with_built_in_tools_only(tmp_path):
    write_agent(tmp_path, "r.md", "reader", "Read, Grep")
    refuses(
        payload("mcp__hilclaw__state_read", agent_id="r", agent_type="reader"),
        tmp_path,
        named("mcp__hilclaw__state_read"),
    )
    refuses(payload("Read", agent_id="r", agent_type="reader"), tmp_path)


def test_a_new_agent_is_held_with_no_change(tmp_path):
    write_agent(tmp_path, "e.md", "experiment-runner", "mcp__hilclaw__board_run")
    passes(
        payload(
            "mcp__hilclaw__board_run", agent_id="e", agent_type="experiment-runner"
        ),
        tmp_path,
    )
    refuses(
        payload("mcp__hilclaw__board_run"), tmp_path, named("mcp__hilclaw__board_run")
    )


def test_the_real_experiment_runner_holds_board_run(session):
    tool = "mcp__hilclaw__board_run"
    passes(payload(tool, agent_id="e5f6", agent_type="experiment-runner"), session)
    refuses(payload(tool), session, named(tool))
    refuses(payload(tool, **EVALUATOR_ID), session, named(tool))
    refuses(payload(tool, **CODER_ID), session, named(tool))
    refuses(
        payload(
            "mcp__hilclaw__sim_run", agent_id="e5f6", agent_type="experiment-runner"
        ),
        session,
        named("mcp__hilclaw__sim_run"),
    )


def test_the_real_technique_selector_holds_catalog_read(session):
    tool = "mcp__hilclaw__catalog_read"
    passes(payload(tool, agent_id="g7h8", agent_type="technique-selector"), session)
    refuses(payload(tool), session, named(tool))
    refuses(payload(tool, **EVALUATOR_ID), session, named(tool))
    refuses(payload(tool, **CODER_ID), session, named(tool))
    refuses(
        payload(tool, agent_id="e5f6", agent_type="experiment-runner"),
        session,
        named(tool),
    )


def test_the_real_technique_selector_alone_holds_cases_lookup(session):
    tool = "mcp__hilclaw__cases_lookup"
    passes(payload(tool, agent_id="g7h8", agent_type="technique-selector"), session)
    refuses(payload(tool), session, named(tool))
    refuses(payload(tool, **EVALUATOR_ID), session, named(tool))
    refuses(payload(tool, **CODER_ID), session, named(tool))
    refuses(
        payload(tool, agent_id="e5f6", agent_type="experiment-runner"),
        session,
        named(tool),
    )


@pytest.mark.parametrize("value", [None, ""])
def test_project_dir_missing_or_empty(session, value):
    environ = {} if value is None else {ENV_PROJECT_DIR: value}
    stderr = io.StringIO()
    assert main(payload("mcp__hilclaw__state_write"), stderr, environ) == EXIT_REFUSE
    assert stderr.getvalue() == named("mcp__hilclaw__state_write") + "\n"


def test_project_dir_not_a_directory(tmp_path):
    file = tmp_path / "file"
    file.write_text("x", encoding="utf-8")
    refuses(
        payload("mcp__hilclaw__state_write"), file, named("mcp__hilclaw__state_write")
    )
    refuses(
        payload("mcp__hilclaw__state_write"),
        tmp_path / "absent",
        named("mcp__hilclaw__state_write"),
    )


def test_cwd_of_the_input_is_not_used(session, tmp_path_factory):
    other = tmp_path_factory.mktemp("other")
    data = payload("mcp__hilclaw__verdicts_write", cwd=str(session), **EVALUATOR_ID)
    refuses(data, other, named("mcp__hilclaw__verdicts_write"))
    refuses(data, None, named("mcp__hilclaw__verdicts_write"))


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"not json",
        b"\xff\xfe{}",
        "﻿".encode() + payload("mcp__hilclaw__state_write"),
        payload("mcp__hilclaw__state_write").decode().encode("utf-16"),
        b"[]",
        b'"x"',
        b"null",
        payload("mcp__hilclaw__state_write") + payload("mcp__hilclaw__state_write"),
    ],
)
def test_input_not_one_json_object(session, data):
    status, text = run(data, session)
    assert status == EXIT_REFUSE
    assert text.count("\n") == 1


@pytest.mark.parametrize("event", [None, "PostToolUse", "pretooluse", "PreToolUse ", 1])
def test_event_not_pre_tool_use(session, event):
    data = payload("mcp__hilclaw__state_write", hook_event_name=event)
    refuses(data, session, named("mcp__hilclaw__state_write"))


def test_event_missing(session):
    found = json.loads(payload("mcp__hilclaw__state_write"))
    del found["hook_event_name"]
    refuses(json.dumps(found).encode(), session, named("mcp__hilclaw__state_write"))


@pytest.mark.parametrize("tool", [None, 1, ["mcp__hilclaw__state_write"], {}])
def test_tool_name_not_a_string(session, tool):
    refuses(payload(tool), session)


def test_tool_name_missing(session):
    found = json.loads(payload("x"))
    del found["tool_name"]
    refuses(json.dumps(found).encode(), session)


@pytest.mark.parametrize(
    "extra",
    [
        ', "agent_id": "x", "agent_type": "evaluator", "agent_type": "evaluator"}',
        ', "agent_id": "x", "agent_id": "y", "agent_type": "evaluator"}',
        ', "tool_name": "mcp__hilclaw__state_read"}',
        ', "hook_event_name": "PreToolUse"}',
        ', "tool_input": {"a": 1, "a": 2}}',
    ],
)
def test_repeated_key_refused(session, extra):
    text = payload("mcp__hilclaw__state_read").decode()
    refuses((text[:-1] + extra).encode(), session)


def test_mcp_server_is_not_read(session):
    data = payload("mcp__hilclaw__state_write", mcp_server={"name": "other"})
    passes(data, session)


def test_line_shows_nothing_of_the_input(session):
    junk = "mcp__hilclaw__" + "x" * 5000 + "/etc/passwd"
    agent_type = os.path.join("..", "..", "secret", "evaluator")
    status, text = run(payload(junk, agent_id="i", agent_type=agent_type), session)
    assert status == EXIT_REFUSE
    assert text == GENERIC + "\n"
    assert "secret" not in text
    assert "passwd" not in text
    assert "xxxx" not in text
    assert str(session) not in text


@pytest.mark.parametrize(
    "tool",
    [
        "mcp__hilclaw__State_write",
        "mcp__hilclaw__state-write",
        "mcp__hilclaw__state_write\n",
        "mcp__hilclaw__state_write/x",
    ],
)
def test_line_names_no_tool_of_another_form(session, tool):
    refuses(payload(tool), session)


def test_named_form_is_the_readers_tool_form():
    assert caller_check._NAMED.pattern == turn_permissions._MCP_TOOL.pattern


def test_guard_turns_an_error_into_a_refusal(session, monkeypatch):
    def broken(session_dir):
        raise RuntimeError("boom at /very/secret")

    monkeypatch.setattr(turn_permissions, "holder_lists", broken)
    status, text = run(payload("mcp__hilclaw__state_write"), session)
    assert status == EXIT_REFUSE
    assert text == named("mcp__hilclaw__state_write") + "\n"
    assert "secret" not in text and "boom" not in text


def test_guard_covers_a_failing_stderr(session):
    class Broken(io.StringIO):
        def write(self, text):
            raise OSError("closed")

    assert (
        main(payload("Bash"), Broken(), {ENV_PROJECT_DIR: str(session)}) == EXIT_REFUSE
    )


def test_defaults_read_the_process_streams(session, monkeypatch, capsys):
    class Stdin:
        buffer = io.BytesIO(payload("mcp__hilclaw__verdicts_write"))

    monkeypatch.setattr(sys, "stdin", Stdin())
    monkeypatch.setenv(ENV_PROJECT_DIR, str(session))
    assert main() == EXIT_REFUSE
    out, err = capsys.readouterr()
    assert out == ""
    assert err == named("mcp__hilclaw__verdicts_write") + "\n"
    Stdin.buffer = io.BytesIO(payload("mcp__hilclaw__state_write"))
    assert main() == EXIT_PASS
    assert capsys.readouterr() == ("", "")


def test_unreadable_stdin_refuses(monkeypatch, capsys):
    class Stdin:
        @property
        def buffer(self):
            raise OSError("no stdin")

    monkeypatch.setattr(sys, "stdin", Stdin())
    assert main(stderr=None, environ={}) == EXIT_REFUSE
    assert capsys.readouterr() == ("", GENERIC + "\n")


def started(data, session):
    environ = dict(os.environ)
    environ[ENV_PROJECT_DIR] = str(session)
    return subprocess.run(
        [sys.executable, "-I", "-c", START, checkout_boundary.PACKAGE_DIRECTORY],
        input=data,
        env=environ,
        capture_output=True,
        timeout=120,
        check=False,
    )


def test_started_as_the_turn_loop_will(session):
    held = started(payload("mcp__hilclaw__verdicts_write", **EVALUATOR_ID), session)
    assert (held.returncode, held.stdout, held.stderr) == (EXIT_PASS, b"", b"")
    refused = started(payload("mcp__hilclaw__verdicts_write"), session)
    assert refused.returncode == EXIT_REFUSE
    assert refused.stdout == b""
    line = named("mcp__hilclaw__verdicts_write")
    assert refused.stderr.decode("utf-8").replace("\r\n", "\n") == line + "\n"


SELECTOR_ID = {"agent_id": "f7a8", "agent_type": "technique-selector"}
RUNNER_ID = {"agent_id": "e5f6", "agent_type": "experiment-runner"}


def test_the_real_technique_selector_holds_hypotheses_write(session):
    tool = "mcp__hilclaw__hypotheses_write"
    passes(payload(tool, **SELECTOR_ID), session)
    refuses(payload(tool), session, named(tool))
    for ids in (EVALUATOR_ID, CODER_ID, RUNNER_ID):
        refuses(payload(tool, **ids), session, named(tool))


@pytest.mark.parametrize(
    "tool",
    [
        "mcp__hilclaw__state_read",
        "mcp__hilclaw__instance_read",
        "mcp__hilclaw__hypotheses_read",
        "mcp__hilclaw__checks_read",
    ],
)
def test_the_real_technique_selector_holds_its_reads(session, tool):
    passes(payload(tool, **SELECTOR_ID), session)


@pytest.mark.parametrize(
    "tool",
    [
        "mcp__hilclaw__timings_compare",
        "mcp__hilclaw__verdicts_write",
        "mcp__hilclaw__state_write",
        "mcp__hilclaw__spec_write",
        "mcp__hilclaw__coder_run",
        "mcp__hilclaw__board_run",
    ],
)
def test_the_real_technique_selector_is_refused_what_it_does_not_hold(session, tool):
    refuses(payload(tool, **SELECTOR_ID), session, named(tool))


def test_the_main_session_now_reads_hypotheses(session):
    passes(payload("mcp__hilclaw__hypotheses_read"), session)
