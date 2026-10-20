from pathlib import Path

import pytest

from hilclaw import mcp_front, turn_definition, turn_permissions
from hilclaw import tools as tools_module
from hilclaw.turn_permissions import (
    AGENTS_DIRECTORY,
    BUILT_IN_TOOLS,
    DELEGATION_TOOL,
    OPT_ALLOWED_TOOLS,
    OPT_PERMISSION_MODE,
    OPT_SETTING_SOURCES,
    OPT_TOOLS,
    PERMISSION_MODE,
    ROUND_MANAGER_TOOLS,
    SETTING_SOURCES,
    TOOLS_SEPARATOR,
    options,
)

FIXED = (
    "mcp__hilclaw__state_read",
    "mcp__hilclaw__instance_read",
    "mcp__hilclaw__run_fresh",
    "mcp__hilclaw__state_write",
    "mcp__hilclaw__run_commit",
    "mcp__hilclaw__key_store",
    "mcp__hilclaw__case_write",
    "mcp__hilclaw__round_end",
)
EVALUATOR = (
    "---\n"
    "name: evaluator\n"
    'description: "Evaluator of a first-case turn: it checks."\n'
    "tools: Read, Grep, Glob, mcp__hilclaw__correctness_check, "
    "mcp__hilclaw__state_read, mcp__hilclaw__instance_read, "
    "mcp__hilclaw__run_fresh, mcp__hilclaw__verdicts_write, "
    "mcp__hilclaw__hypotheses_read, mcp__hilclaw__checks_read\n"
    "---\n"
    "# Evaluator\n"
)
EVALUATOR_TOOLS = {
    "Read",
    "Grep",
    "Glob",
    "mcp__hilclaw__correctness_check",
    "mcp__hilclaw__state_read",
    "mcp__hilclaw__instance_read",
    "mcp__hilclaw__run_fresh",
    "mcp__hilclaw__verdicts_write",
    "mcp__hilclaw__hypotheses_read",
    "mcp__hilclaw__checks_read",
}
BYPASS = (
    "--dangerously-skip-permissions",
    "--allow-dangerously-skip-permissions",
    "bypassPermissions",
    "acceptEdits",
    "auto",
)
NO_DIRECTORY = "the agents entry of the session directory is no directory"
NOT_UTF8 = "an agent file is not UTF-8"
NO_FRONTMATTER = "an agent file has no frontmatter"
NOT_A_KEY = "an agent file has a frontmatter line that is no 'key: value'"
KEY_TWICE = "an agent file has a frontmatter key twice"
BAD_NAME = "an agent file has no valid name"
NO_TOOLS = "an agent file has no tools list"
BAD_TOOL = "an agent file names a tool that is not admitted"
PERMISSION = "an agent file sets permissionMode"


def agents(session):
    directory = session.joinpath(*AGENTS_DIRECTORY)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def agent(name, tools, extra=""):
    return f"---\nname: {name}\n{extra}tools: {tools}\n---\nbody\n"


def split(found):
    assert len(found) == 8
    assert found[0::2] == (
        OPT_SETTING_SOURCES,
        OPT_TOOLS,
        OPT_PERMISSION_MODE,
        OPT_ALLOWED_TOOLS,
    )
    assert found[1] == SETTING_SOURCES
    assert found[5] == PERMISSION_MODE
    return found[3], found[7].split(TOOLS_SEPARATOR)


def test_public_constants():
    assert OPT_SETTING_SOURCES == "--setting-sources"
    assert SETTING_SOURCES == "project"
    assert OPT_TOOLS == "--tools"
    assert OPT_PERMISSION_MODE == "--permission-mode"
    assert PERMISSION_MODE == "dontAsk"
    assert OPT_ALLOWED_TOOLS == "--allowedTools"
    assert TOOLS_SEPARATOR == ","
    assert DELEGATION_TOOL == "Agent"
    assert BUILT_IN_TOOLS == ("Glob", "Grep", "Read")
    assert AGENTS_DIRECTORY == (".claude", "agents")
    assert ROUND_MANAGER_TOOLS == FIXED
    assert turn_permissions.__doc__


def test_fixed_list_names_registered_tools():
    registered = tools_module.default_registry(lambda: None).names()
    prefix = f"mcp__{mcp_front.SERVER_NAME}__"
    served = {prefix + mcp_front.mcp_name(name) for name in registered}
    assert set(ROUND_MANAGER_TOOLS) <= served
    assert len(set(ROUND_MANAGER_TOOLS)) == len(ROUND_MANAGER_TOOLS)


def test_no_agents_directory(tmp_path):
    built_in, allowed = split(options(tmp_path))
    assert built_in == ""
    assert allowed == sorted(FIXED)


def test_empty_agents_directory(tmp_path):
    agents(tmp_path)
    built_in, allowed = split(options(tmp_path))
    assert built_in == ""
    assert allowed == sorted(FIXED)


def test_the_order_of_the_arguments(tmp_path):
    found = options(str(tmp_path))
    assert found == (
        "--setting-sources",
        "project",
        "--tools",
        "",
        "--permission-mode",
        "dontAsk",
        "--allowedTools",
        ",".join(sorted(FIXED)),
    )
    assert all(type(item) is str for item in found)


def test_the_evaluator(tmp_path):
    (agents(tmp_path) / "evaluator.md").write_text(EVALUATOR, encoding="utf-8")
    built_in, allowed = split(options(tmp_path))
    assert built_in == "Agent,Glob,Grep,Read"
    assert allowed == sorted({*FIXED, *EVALUATOR_TOOLS, "Agent(evaluator)"})
    assert len(allowed) == len(set(allowed))
    assert not any("*" in entry for entry in allowed)


def test_no_bypass_option(tmp_path):
    (agents(tmp_path) / "evaluator.md").write_text(EVALUATOR, encoding="utf-8")
    for argument in options(tmp_path):
        for word in BYPASS:
            assert word not in argument


def test_two_agents_overlapping(tmp_path):
    directory = agents(tmp_path)
    (directory / "b-agent.md").write_text(
        agent("b-agent", "Read, mcp__hilclaw__state_read, mcp__hilclaw__blob_push"),
        encoding="utf-8",
    )
    (directory / "a-agent.md").write_text(
        agent("a-agent", "Read,mcp__hilclaw__blob_push , Grep"), encoding="utf-8"
    )
    built_in, allowed = split(options(tmp_path))
    assert built_in == "Agent,Grep,Read"
    assert allowed == sorted(
        {
            *FIXED,
            "Agent(a-agent)",
            "Agent(b-agent)",
            "Read",
            "Grep",
            "mcp__hilclaw__blob_push",
        }
    )
    assert len(allowed) == len(set(allowed))


def test_agent_with_mcp_tools_only(tmp_path):
    (agents(tmp_path) / "x.md").write_text(
        agent("x1", "mcp__hilclaw__blob_fetch"), encoding="utf-8"
    )
    built_in, allowed = split(options(tmp_path))
    assert built_in == "Agent"
    assert allowed == sorted({*FIXED, "Agent(x1)", "mcp__hilclaw__blob_fetch"})


def test_nested_agent_file_is_read(tmp_path):
    nested = agents(tmp_path) / "group" / "deeper"
    nested.mkdir(parents=True)
    (nested / "inner.md").write_text(agent("inner", "Glob"), encoding="utf-8")
    built_in, allowed = split(options(tmp_path))
    assert built_in == "Agent,Glob"
    assert "Agent(inner)" in allowed


def test_non_md_files_and_md_directories_are_ignored(tmp_path):
    directory = agents(tmp_path)
    (directory / "notes.txt").write_text("not an agent", encoding="utf-8")
    (directory / "README").write_text("---\nbad", encoding="utf-8")
    (directory / "folder.md").mkdir()
    built_in, allowed = split(options(tmp_path))
    assert built_in == ""
    assert allowed == sorted(FIXED)


def test_crlf_line_ends(tmp_path):
    text = EVALUATOR.replace("\n", "\r\n")
    (agents(tmp_path) / "evaluator.md").write_bytes(text.encode("utf-8"))
    built_in, allowed = split(options(tmp_path))
    assert built_in == "Agent,Glob,Grep,Read"
    assert set(allowed) == {*FIXED, *EVALUATOR_TOOLS, "Agent(evaluator)"}


def test_frontmatter_closed_at_the_end(tmp_path):
    (agents(tmp_path) / "a.md").write_text(
        "---\nname: a\ntools: Read\n---", encoding="utf-8"
    )
    assert split(options(tmp_path))[0] == "Agent,Read"


def test_value_with_colons_and_extra_keys(tmp_path):
    text = agent("a", "Read", extra="description: a: b: c\nmodel: x\n")
    (agents(tmp_path) / "a.md").write_text(text, encoding="utf-8")
    assert "Agent(a)" in split(options(tmp_path))[1]


def test_the_real_definition(tmp_path):
    turn_definition.put(tmp_path)
    built_in, allowed = split(options(tmp_path))
    assert "Agent(evaluator)" in allowed
    assert EVALUATOR_TOOLS <= set(allowed)
    assert set(FIXED) <= set(allowed)
    assert built_in == "Agent,Glob,Grep,Read"


def test_session_dir_as_str_and_path(tmp_path):
    assert options(str(tmp_path)) == options(Path(tmp_path))


class BytesPath:
    def __fspath__(self):
        return b"/tmp"


@pytest.mark.parametrize("value", [None, 1, b"/tmp", ["x"], BytesPath()])
def test_session_dir_wrong_type(value):
    with pytest.raises(TypeError, match="session directory"):
        options(value)


def test_agents_entry_is_a_file(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "agents").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match=NO_DIRECTORY):
        options(tmp_path)


def refused(tmp_path, data, text):
    (agents(tmp_path) / "agent.md").write_bytes(data)
    with pytest.raises(ValueError) as caught:
        options(tmp_path)
    assert str(caught.value) == text


def test_not_utf8(tmp_path):
    refused(tmp_path, b"---\nname: a\xff\ntools: Read\n---\n", NOT_UTF8)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "name: a\ntools: Read\n",
        "\n---\nname: a\ntools: Read\n---\n",
        "---\nname: a\ntools: Read\n",
        "--- \nname: a\ntools: Read\n---\n",
        "﻿---\nname: a\ntools: Read\n---\n",
        "---\nname: a\ntools: Read\n----\n",
    ],
)
def test_no_frontmatter(tmp_path, text):
    refused(tmp_path, text.encode("utf-8"), NO_FRONTMATTER)


@pytest.mark.parametrize(
    "line",
    ["", "no separator", " name: a", "na me: a", ": a", "1key: a", "key :a"],
)
def test_line_not_a_key(tmp_path, line):
    text = f"---\nname: a\n{line}\ntools: Read\n---\n"
    refused(tmp_path, text.encode("utf-8"), NOT_A_KEY)


def test_key_twice(tmp_path):
    text = "---\nname: a\ntools: Read\nname: b\n---\n"
    refused(tmp_path, text.encode("utf-8"), KEY_TWICE)


@pytest.mark.parametrize(
    "line", ["", "name:", "name: ", "name: Eval", "name: 1a", "name: a_b", "name: a b"]
)
def test_bad_name(tmp_path, line):
    text = f"---\n{line}\ntools: Read\n---\n" if line else "---\ntools: Read\n---\n"
    refused(tmp_path, text.encode("utf-8"), BAD_NAME)


@pytest.mark.parametrize("line", ["", "tools:", "tools:   "])
def test_no_tools(tmp_path, line):
    text = f"---\nname: a\n{line}\n---\n" if line else "---\nname: a\n---\n"
    refused(tmp_path, text.encode("utf-8"), NO_TOOLS)


@pytest.mark.parametrize(
    "tools",
    [
        "*",
        "mcp__hilclaw",
        "mcp__hilclaw__*",
        "mcp__hilclaw__",
        "mcp__hilclaw__State_read",
        "mcp__hilclaw__1x",
        "mcp__other__state_read",
        "mcp__hilclaw__state-read",
        "Bash",
        "Bash(make *)",
        "Write",
        "Edit",
        "Agent",
        "Agent(evaluator)",
        "read",
        "Read(*)",
        "Read,",
        "Read,,Grep",
        "Read Grep",
    ],
)
def test_bad_tool_entry(tmp_path, tools):
    refused(tmp_path, agent("a", tools).encode("utf-8"), BAD_TOOL)


def test_permission_mode(tmp_path):
    text = agent("a", "Read", extra="permissionMode: dontAsk\n")
    refused(tmp_path, text.encode("utf-8"), PERMISSION)


def test_a_refused_file_among_good_ones(tmp_path):
    directory = agents(tmp_path)
    (directory / "a.md").write_text(EVALUATOR, encoding="utf-8")
    (directory / "z.md").write_text(agent("z", "Bash"), encoding="utf-8")
    with pytest.raises(ValueError, match=BAD_TOOL):
        options(tmp_path)
