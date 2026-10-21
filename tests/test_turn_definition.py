import os
import re
from pathlib import Path

import pytest

from hilclaw import mcp_front, turn_definition, turn_loop
from hilclaw import tools as tools_module
from hilclaw.turn_definition import DIRECTORIES, LAYOUT, PROMPT, SOURCE, put

EVALUATOR = "evaluator.md"
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
    "mcp__hilclaw__timings_compare",
}
CODER_DRIVER = "coder-driver.md"
CODER_DRIVER_TOOLS = {"mcp__hilclaw__spec_write", "mcp__hilclaw__coder_run"}

UNKNOWN = "the definition holds an entry that is not in the layout"
WRONG_KIND = "an entry of the definition is of the wrong kind"
NO_PROMPT = "the definition holds no round-manager.md"
MARKER = "the definition holds an instruction file or a .claude"
LINK = "the definition holds a symbolic link or a junction"
OTHER = "the definition holds an entry that is neither a file nor a directory"
SESSION_CLAUDE = "the session directory holds a .claude that is no plain directory"
SESSION_LINK = "the session directory holds a link where the definition goes"
FOLDS = os.path.normcase("A") == os.path.normcase("a")


@pytest.fixture
def session(tmp_path):
    directory = tmp_path / "session"
    directory.mkdir()
    return directory


@pytest.fixture
def source(tmp_path):
    directory = tmp_path / "orchestration"
    directory.mkdir()
    (directory / PROMPT).write_bytes(b"# prompt\r\nline\n")
    return directory


def full(source):
    for name in ("agents", "skills"):
        (source / name / "nested").mkdir(parents=True)
        (source / name / "top.md").write_bytes(f"{name} top".encode())
        (source / name / "nested" / "deep.md").write_bytes(f"{name} deep".encode())
    (source / "settings.json").write_bytes(b'{"hooks": {}}')
    return source


def tree(root):
    found = {}
    for directory, _, files in os.walk(root):
        for name in files:
            path = Path(directory) / name
            found[path.relative_to(root).as_posix()] = path.read_bytes()
    return found


def symlink(link, target, *, directory=False):
    try:
        os.symlink(target, link, target_is_directory=directory)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links cannot be created here")


def junction(link, target):
    try:
        import _winapi
    except ImportError:
        pytest.skip("junctions exist only on Windows")
    _winapi.CreateJunction(str(target), str(link))


def refused(session, text, **arguments):
    before = tree(session)
    listing = sorted(os.listdir(session))
    with pytest.raises(ValueError) as caught:
        put(session, **arguments)
    assert str(caught.value) == text
    assert tree(session) == before
    assert sorted(os.listdir(session)) == listing


def test_public_names():
    assert turn_definition.__doc__
    assert (
        SOURCE
        == Path(turn_definition.__file__).resolve().parent.parent / "orchestration"
    )
    assert LAYOUT == {
        "round-manager.md": ("CLAUDE.md",),
        "agents": (".claude", "agents"),
        "skills": (".claude", "skills"),
        "settings.json": (".claude", "settings.json"),
    }
    assert DIRECTORIES == {"agents", "skills"}
    assert put.__doc__


def test_the_repository_definition_by_default(session):
    assert put(session) is None
    assert tree(session) == {
        "CLAUDE.md": (SOURCE / PROMPT).read_bytes(),
        ".claude/agents/evaluator.md": (SOURCE / "agents" / EVALUATOR).read_bytes(),
        ".claude/agents/coder-driver.md": (
            SOURCE / "agents" / CODER_DRIVER
        ).read_bytes(),
    }
    assert sorted(os.listdir(session)) == [".claude", "CLAUDE.md"]
    assert os.listdir(session / ".claude") == ["agents"]


def test_the_repository_definition_holds_the_prompt_and_the_two_agents():
    assert sorted(os.listdir(SOURCE)) == ["agents", PROMPT]
    assert (SOURCE / "agents").is_dir()
    assert sorted(os.listdir(SOURCE / "agents")) == sorted([EVALUATOR, CODER_DRIVER])


def frontmatter(text):
    lines = text.splitlines()
    assert lines and lines[0] == "---", "the text holds no frontmatter"
    assert "---" in lines[1:], "the frontmatter is not closed"
    found = {}
    for line in lines[1 : lines.index("---", 1)]:
        key, separator, value = line.partition(":")
        assert separator and key == key.strip() and key, f"not a key: {line!r}"
        assert key not in found, f"a key twice: {key!r}"
        found[key] = value.strip()
    return found


def served_names():
    registered = tools_module.default_registry(lambda: None).names()
    prefix = f"mcp__{mcp_front.SERVER_NAME}__"
    return {prefix + mcp_front.mcp_name(name) for name in registered}


def test_the_evaluator_frontmatter():
    text = (SOURCE / "agents" / EVALUATOR).read_text(encoding="utf-8")
    found = frontmatter(text)
    assert set(found) == {"name", "description", "tools"}
    assert found["name"] == "evaluator"
    assert "model" not in found
    assert found["description"]
    tools = [name.strip() for name in found["tools"].split(",")]
    assert len(tools) == len(set(tools))
    assert set(tools) == EVALUATOR_TOOLS
    served = served_names()
    for name in tools:
        if name.startswith("mcp__hilclaw__"):
            assert name in served


def test_the_evaluator_names_no_removed_kind():
    text = (SOURCE / "agents" / EVALUATOR).read_text(encoding="utf-8")
    assert "comparison_not_given" not in text
    assert "comparison_unverified" in text


def test_a_given_source_as_str(session, source):
    put(str(session), source=str(source))
    assert tree(session) == {"CLAUDE.md": b"# prompt\r\nline\n"}


def test_a_full_source(session, source):
    full(source)
    put(session, source=source)
    assert tree(session) == {
        "CLAUDE.md": b"# prompt\r\nline\n",
        ".claude/agents/top.md": b"agents top",
        ".claude/agents/nested/deep.md": b"agents deep",
        ".claude/skills/top.md": b"skills top",
        ".claude/skills/nested/deep.md": b"skills deep",
        ".claude/settings.json": b'{"hooks": {}}',
    }


def test_targets_present_are_replaced(session, source):
    full(source)
    (session / "CLAUDE.md").write_bytes(b"old")
    (session / ".claude" / "agents").mkdir(parents=True)
    (session / ".claude" / "agents" / "stale.md").write_bytes(b"stale")
    (session / ".claude" / "settings.json").write_bytes(b"old settings")
    put(session, source=source)
    found = tree(session)
    assert found["CLAUDE.md"] == b"# prompt\r\nline\n"
    assert ".claude/agents/stale.md" not in found
    assert found[".claude/agents/top.md"] == b"agents top"
    assert found[".claude/settings.json"] == b'{"hooks": {}}'


def test_a_target_of_the_other_kind_is_replaced(session, source):
    (session / "CLAUDE.md").mkdir()
    (session / "CLAUDE.md" / "inner").write_bytes(b"x")
    full(source)
    (session / ".claude").mkdir()
    (session / ".claude" / "skills").write_bytes(b"a file")
    put(session, source=source)
    found = tree(session)
    assert found["CLAUDE.md"] == b"# prompt\r\nline\n"
    assert found[".claude/skills/top.md"] == b"skills top"


def test_stale_targets_of_absent_entries_are_removed(session, source):
    (session / ".claude" / "skills").mkdir(parents=True)
    (session / ".claude" / "skills" / "old.md").write_bytes(b"old")
    (session / ".claude" / "agents").mkdir()
    (session / ".claude" / "settings.json").write_bytes(b"{}")
    put(session, source=source)
    assert tree(session) == {"CLAUDE.md": b"# prompt\r\nline\n"}
    assert os.listdir(session / ".claude") == []


def test_other_entries_stay_untouched(session, source):
    (session / turn_loop.CONFIG_FILE).write_bytes(b"config")
    (session / "unrelated.txt").write_bytes(b"mine")
    (session / ".claude").mkdir()
    (session / ".claude" / "agent-memory").mkdir()
    (session / ".claude" / "agent-memory" / "note.md").write_bytes(b"memory")
    put(session, source=full(source))
    found = tree(session)
    assert found[turn_loop.CONFIG_FILE] == b"config"
    assert found["unrelated.txt"] == b"mine"
    assert found[".claude/agent-memory/note.md"] == b"memory"


def test_put_twice_gives_the_same_tree(session, source):
    full(source)
    put(session, source=source)
    first = tree(session)
    put(session, source=source)
    assert tree(session) == first


def test_passes_the_callable_check_of_the_turn_loop(tmp_path):
    with pytest.raises(ValueError, match="the prompt"):
        turn_loop.run(
            further_turn=lambda previous: False,
            put_definition=put,
            prompt="",
            data_root=tmp_path,
        )


def test_accepted_as_put_definition_by_the_turn_loop(tmp_path, session):
    own = (Path.home() / ".claude").resolve()
    for directory in session.resolve().parents:
        for name in turn_loop.MARKERS:
            found = directory / name
            if os.path.lexists(found) and found.resolve() != own:
                pytest.skip("a directory above the test's directory holds a marker")
    data = tmp_path / "data"
    data.mkdir()
    asked = []

    def further_turn(previous):
        asked.append(previous)
        return False

    found = turn_loop.run(
        further_turn=further_turn,
        put_definition=put,
        prompt="Run the next turn.",
        data_root=data,
        parent=session,
    )
    assert found == ()
    assert asked == [None]


@pytest.mark.parametrize("value", [None, 1, b"bytes", ["a"]])
def test_session_dir_of_a_wrong_type(source, value):
    with pytest.raises(TypeError):
        put(value, source=source)


@pytest.mark.parametrize("value", [1, b"bytes", ["a"]])
def test_source_of_a_wrong_type(session, value):
    with pytest.raises(TypeError):
        put(session, source=value)
    assert os.listdir(session) == []


def test_a_missing_session_dir(tmp_path, source):
    with pytest.raises(ValueError):
        put(tmp_path / "missing", source=source)
    assert not (tmp_path / "missing").exists()


def test_a_session_dir_that_is_a_file(tmp_path, source):
    file = tmp_path / "file"
    file.write_bytes(b"x")
    with pytest.raises(ValueError):
        put(file, source=source)
    assert file.read_bytes() == b"x"


def test_a_missing_source(tmp_path, session):
    with pytest.raises(FileNotFoundError):
        put(session, source=tmp_path / "missing")
    assert os.listdir(session) == []


def test_a_source_that_is_a_file(tmp_path, session):
    file = tmp_path / "file"
    file.write_bytes(b"x")
    with pytest.raises(ValueError):
        put(session, source=file)
    assert os.listdir(session) == []


@pytest.mark.parametrize("name", ["notes.md", "hooks", "Settings.JSON"])
def test_an_unknown_top_level_entry(session, source, name):
    (source / name).write_bytes(b"x")
    refused(session, UNKNOWN, source=source)


def test_an_unknown_top_level_directory(session, source):
    (source / "commands").mkdir()
    refused(session, UNKNOWN, source=source)


def test_agents_as_a_file(session, source):
    (source / "agents").write_bytes(b"x")
    refused(session, WRONG_KIND, source=source)


def test_settings_as_a_directory(session, source):
    (source / "settings.json").mkdir()
    refused(session, WRONG_KIND, source=source)


def test_the_prompt_as_a_directory(session, source):
    (source / PROMPT).unlink()
    (source / PROMPT).mkdir()
    refused(session, WRONG_KIND, source=source)


def test_a_missing_prompt(session, source):
    (source / PROMPT).unlink()
    full(source)
    refused(session, NO_PROMPT, source=source)


def test_an_empty_source(session, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    refused(session, NO_PROMPT, source=empty)


@pytest.mark.parametrize("name", ["CLAUDE.md", "AGENTS.md", "CLAUDE.local.md"])
def test_an_instruction_file_at_depth(session, source, name):
    full(source)
    (source / "skills" / "nested" / name).write_bytes(b"x")
    refused(session, MARKER, source=source)


def test_a_claude_directory_at_depth(session, source):
    full(source)
    (source / "agents" / "nested" / ".claude").mkdir()
    refused(session, MARKER, source=source)


def test_an_instruction_file_at_the_top(session, source):
    (source / "CLAUDE.md").write_bytes(b"x")
    refused(session, MARKER, source=source)


@pytest.mark.skipif(not FOLDS, reason="names are not folded on this system")
@pytest.mark.parametrize("name", ["claude.md", "Agents.MD", ".Claude"])
def test_a_case_variant_marker(session, source, name):
    full(source)
    (source / "agents" / name).write_bytes(b"x")
    refused(session, MARKER, source=source)


@pytest.mark.skipif(FOLDS, reason="names are folded on this system")
def test_a_case_variant_is_no_marker_where_names_are_not_folded(session, source):
    full(source)
    (source / "agents" / "claude.md").write_bytes(b"x")
    put(session, source=source)
    assert (session / ".claude" / "agents" / "claude.md").read_bytes() == b"x"


def test_a_file_link_at_depth(session, source, tmp_path):
    full(source)
    outside = tmp_path / "outside.md"
    outside.write_bytes(b"x")
    symlink(source / "agents" / "nested" / "linked.md", outside)
    refused(session, LINK, source=source)


def test_a_directory_link_at_the_top(session, source, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    symlink(source / "skills", outside, directory=True)
    refused(session, LINK, source=source)


def test_the_prompt_as_a_link(session, source, tmp_path):
    outside = tmp_path / "outside.md"
    outside.write_bytes(b"x")
    (source / PROMPT).unlink()
    symlink(source / PROMPT, outside)
    refused(session, LINK, source=source)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs os.mkfifo")
def test_an_entry_neither_file_nor_directory(session, source):
    full(source)
    os.mkfifo(source / "agents" / "pipe")
    refused(session, OTHER, source=source)


def test_a_session_claude_that_is_a_file(session, source):
    (session / ".claude").write_bytes(b"x")
    (session / "CLAUDE.md").write_bytes(b"old")
    refused(session, SESSION_CLAUDE, source=source)


def test_a_session_claude_that_is_a_link(session, source, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    symlink(session / ".claude", outside, directory=True)
    refused(session, SESSION_CLAUDE, source=full(source))
    assert os.listdir(outside) == []


def test_a_session_target_that_is_a_link(session, source, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.md").write_bytes(b"keep")
    (session / ".claude").mkdir()
    symlink(session / ".claude" / "agents", outside, directory=True)
    refused(session, SESSION_LINK, source=full(source))
    assert tree(outside) == {"keep.md": b"keep"}


def test_a_session_prompt_target_that_is_a_link(session, source, tmp_path):
    outside = tmp_path / "outside.md"
    outside.write_bytes(b"keep")
    symlink(session / "CLAUDE.md", outside)
    refused(session, SESSION_LINK, source=source)
    assert outside.read_bytes() == b"keep"


def test_a_junction_at_depth(session, source, tmp_path):
    full(source)
    outside = tmp_path / "outside"
    outside.mkdir()
    junction(source / "skills" / "nested" / "joined", outside)
    refused(session, LINK, source=source)


def test_a_session_target_that_is_a_junction(session, source, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.md").write_bytes(b"keep")
    (session / ".claude").mkdir()
    junction(session / ".claude" / "skills", outside)
    refused(session, SESSION_LINK, source=full(source))
    assert tree(outside) == {"keep.md": b"keep"}


def test_the_coder_driver_frontmatter():
    data = (SOURCE / "agents" / CODER_DRIVER).read_bytes()
    assert b"\r" not in data
    found = frontmatter(data.decode("utf-8"))
    assert set(found) == {"name", "description", "tools"}
    assert found["name"] == "coder-driver"
    assert found["description"]
    tools = [name.strip() for name in found["tools"].split(",")]
    assert len(tools) == len(set(tools))
    assert set(tools) == CODER_DRIVER_TOOLS
    served = served_names()
    for name in tools:
        if name.startswith("mcp__hilclaw__"):
            assert name in served
    for name in ("Bash", "Read", "Grep", "Glob", "Write", "Edit", "Agent"):
        assert name not in tools


def test_the_coder_driver_names_the_kind_and_the_result():
    text = (SOURCE / "agents" / CODER_DRIVER).read_text(encoding="utf-8")
    for word in ("spec_exists", "taken", "scratch_removed"):
        assert word in text


def prompt_text():
    return " ".join((SOURCE / PROMPT).read_text(encoding="utf-8").split())


def only_forbidden(text, word):
    naming = [s for s in re.split(r"(?<=\.) ", text) if word in s]
    for sentence in naming:
        assert sentence.startswith("Do not call ")
    return naming


def test_the_prompt_delegates_to_the_coder_driver():
    text = prompt_text()
    assert "`coder-driver`" in text
    assert (SOURCE / "agents" / CODER_DRIVER).is_file()
    assert "Use only `mcp__hilclaw__coder_run`" not in text
    assert only_forbidden(text, "coder_run")


def test_the_prompt_delegates_both_checks_to_the_evaluator():
    text = prompt_text()
    assert "`evaluator`" in text
    assert (SOURCE / "agents" / EVALUATOR).is_file()
    assert "`sim`" in text
    assert "`board`" in text


def test_the_prompt_keeps_the_stop_in_later_rounds():
    assert "not yet defined" in prompt_text()


def test_the_prompt_names_no_measurement_step():
    text = prompt_text()
    for word in ("board_run", "sim_run", "experiment-runner"):
        assert word not in text


def test_the_prompt_makes_no_check_of_its_own():
    text = prompt_text()
    assert "Use only `mcp__hilclaw__correctness_check`" not in text
    assert "Use only `mcp__hilclaw__checks_read`" not in text
    only_forbidden(text, "correctness_check")
    only_forbidden(text, "checks_read")


def test_the_prompt_reaches_no_closing_steps_yet():
    heading = "### The closing steps of a round"
    text = prompt_text()
    assert heading in text
    closing = text.split(heading, 1)[1]
    assert "reached only once later slices" in closing


def between(text, start, end):
    assert start in text
    part = text.split(start, 1)[1]
    assert end in part
    return part.split(end, 1)[0]


def end_rule():
    return between(prompt_text(), "## The end of a session", "## The entry of a turn")


def entry_steps():
    section = between(prompt_text(), "## The entry of a turn", "## The round steps")
    parts = re.split(r" (\d)\. (?=[A-Z])", section)
    return dict(zip(map(int, parts[1::2]), parts[2::2]))


def the_stop():
    return between(prompt_text(), "The stop:", "Later slices")


def closing_step(number):
    closing = prompt_text().split("### The closing steps of a round", 1)[1]
    following = f" {number + 1}. **" if number < 3 else None
    part = closing.split(f" {number}. **", 1)[1]
    return part.split(following, 1)[0] if following else part


def test_the_prompt_uses_run_commit_for_every_commit():
    text = prompt_text()
    naming = [
        s
        for s in re.split(r"(?<=\.) ", text)
        if s.startswith("Use only `mcp__hilclaw__run_commit`")
    ]
    assert len(naming) == 1
    assert "every commit of your run" in naming[0]
    assert "round ends" not in naming[0]
    assert "ADR-0143 decision 2" in naming[0]


def test_the_stop_commits_and_leaves_round_0_open():
    stop = the_stop()
    assert "call `mcp__hilclaw__run_commit`" in stop
    assert "Round 0 is not ended: no `round.end`" in stop
    assert "no `run.commit`" not in stop
    assert "No turn goes past this stop" in stop
    assert "ADR-0143 decisions 2 and 7" in stop
    assert stop.index("once the report") < stop.index("mcp__hilclaw__run_commit")
    assert stop.index("mcp__hilclaw__run_commit") < stop.index("end the session")
    assert "Later slices of the definition replace this stop" in prompt_text()


def test_the_end_rule_covers_entry_steps_2_to_7():
    rule = end_rule()
    assert "Once entry step 0 has succeeded, call `mcp__hilclaw__run_commit`" in rule
    assert "the ends of entry steps 2, 3, 4, 5, 6 and 7" in rule
    assert "the stop" in rule
    assert "a failed `round.end` in closing step 2" in rule
    assert "ADR-0143 decision 2" in rule
    assert "do not report the value" in rule
    assert "This call is not a write into the run" in rule
    steps = entry_steps()
    assert sorted(steps) == list(range(8))
    ending = sorted(n for n, step in steps.items() if "end the session" in step)
    assert ending == [0, 2, 3, 4, 5, 6, 7]
    assert 'ends it as "The end of a session" says' in between(
        prompt_text(), "## The entry of a turn", " 0. "
    )


def test_the_step_0_failure_still_ends_the_session():
    step = entry_steps()[0]
    assert (
        "If the call fails with any kind, report the kind in one line and end the session"
        in step
    )
    assert "only a commit that ends no round" in step
    assert "write nothing into the run" in step


def test_a_failed_run_commit_is_not_called_again():
    rule = end_rule()
    assert "at entry step 0 or at an end, do not call it again in this turn" in rule
    assert "ADR-0127 decision 5" in rule


def test_the_closing_steps_commit_after_a_failed_round_end():
    step = closing_step(2)
    failure = step.split("If the call fails with any kind", 1)[1]
    assert failure.index("call `mcp__hilclaw__run_commit`") < failure.index(
        "end the session"
    )
    assert "Do not call `mcp__hilclaw__round_end` again in this turn" in failure
    assert "do not write `STATE.json` with `mcp__hilclaw__state_write`" in failure
    assert "ADR-0143 decision 2, revising ADR-0135 decision 5" in failure
    assert closing_step(3) == (
        "`run.commit`.** Call `mcp__hilclaw__run_commit`. Whether `committed` is "
        "`true` or `false`, do not report the value. If the call fails with any "
        "kind, report the kind in one line. In either case end the session "
        "(ADR-0127 decisions 3 and 5; ADR-0118 decision 2 (i))."
    )


def test_the_prompt_forbids_run_commit_nowhere_else():
    text = prompt_text()
    lowered = text.lower()
    assert "no `run.commit`" not in lowered
    assert "do not call `mcp__hilclaw__run_commit`" not in lowered
    assert "HQ-0043" not in text
    for word in ("retry", "push", "index.lock"):
        assert word not in lowered


def test_an_invalid_run_id_makes_no_request():
    bullet = between(
        prompt_text(), "If your prompt holds no run id", "Otherwise that run"
    )
    assert "report that in one line and end the session" in bullet
    assert "make no tool request that names a run" in bullet
    assert "run_commit" not in bullet
