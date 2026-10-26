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
EXPERIMENT_RUNNER = "experiment-runner.md"
TECHNIQUE_SELECTOR = "technique-selector.md"
TECHNIQUE_SELECTOR_TOOLS = {
    "Read",
    "Grep",
    "Glob",
    "mcp__hilclaw__state_read",
    "mcp__hilclaw__instance_read",
    "mcp__hilclaw__hypotheses_read",
    "mcp__hilclaw__checks_read",
    "mcp__hilclaw__hypotheses_write",
    "mcp__hilclaw__catalog_read",
    "mcp__hilclaw__cases_lookup",
}

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
        ".claude/agents/experiment-runner.md": (
            SOURCE / "agents" / EXPERIMENT_RUNNER
        ).read_bytes(),
        ".claude/agents/technique-selector.md": (
            SOURCE / "agents" / TECHNIQUE_SELECTOR
        ).read_bytes(),
    }
    assert sorted(os.listdir(session)) == [".claude", "CLAUDE.md"]
    assert os.listdir(session / ".claude") == ["agents"]


def test_the_repository_definition_holds_the_prompt_and_the_four_agents():
    assert sorted(os.listdir(SOURCE)) == ["agents", PROMPT]
    assert (SOURCE / "agents").is_dir()
    assert sorted(os.listdir(SOURCE / "agents")) == sorted(
        [EVALUATOR, CODER_DRIVER, EXPERIMENT_RUNNER, TECHNIQUE_SELECTOR]
    )


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
            run_id="run-a",
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
        run_id="run-a",
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


def test_the_coder_driver_carries_the_techniques():
    data = (SOURCE / "agents" / CODER_DRIVER).read_text(encoding="utf-8")
    assert "round-0 coder call" not in frontmatter(data)["description"]
    body = " ".join(data.split()).split("---", 2)[2]
    given = between(body, "## What you are given", "## Fixed rule")
    assert "For a round ≥ 1 the message also names the technique ids" in given
    assert "in their order, or that there are none" in given
    assert "judge nothing and compose nothing" in given
    rule = between(body, "1. With the run id", " 2. If it succeeds")
    assert (
        "In a round ≥ 1 the request also carries `techniques`: the message's ids "
        "in their order, or an empty array for none." in rule
    )
    assert "In round 0 it carries no `techniques` member" in rule
    assert "ADR-0151 decision 3" in rule
    assert (
        "If a round ≥ 1 delegation gives no list, request nothing and report that"
        in rule
    )
    assert "ADR-0171 decision 5" in rule
    assert "is the interim rule of ADR-0141 decision 5" in body


def test_the_experiment_runner_frontmatter():
    data = (SOURCE / "agents" / EXPERIMENT_RUNNER).read_bytes()
    assert b"\r" not in data
    found = frontmatter(data.decode("utf-8"))
    assert set(found) == {"name", "description", "tools"}
    assert found["name"] == "experiment-runner"
    assert found["description"]
    tools = [name.strip() for name in found["tools"].split(",")]
    assert tools == ["mcp__hilclaw__board_run"]
    served = served_names()
    for name in tools:
        if name.startswith("mcp__hilclaw__"):
            assert name in served
    for name in (
        "Bash",
        "Read",
        "Grep",
        "Glob",
        "Write",
        "Edit",
        "Agent",
        "mcp__hilclaw__sim_run",
    ):
        assert name not in tools


def test_the_experiment_runner_body():
    text = " ".join(
        (SOURCE / "agents" / EXPERIMENT_RUNNER).read_text(encoding="utf-8").split()
    )
    body = text.split("---", 2)[2]
    for word in ("`outcome`", "`condition`", "`execution` 1", '`"broken"`'):
        assert word in body
    assert "Call `mcp__hilclaw__board_run` once" in body
    assert "Never call it twice in one delegation" in body
    assert "never state another `execution`" in body
    assert "Copy no interval or figure" in body
    assert "Write nothing by any means" in body
    assert "ADR-0142 decision 4" in body
    assert "sim_run" not in text


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


def test_the_prompt_keeps_the_stop_in_later_rounds_after_steps_7_and_8_only():
    text = prompt_text()
    assert "not yet defined" not in text
    assert "In other rounds it follows step 7" in the_stop()
    assert "Later slices of the definition" not in text


def test_the_prompt_names_board_run_only_in_the_prohibition():
    text = prompt_text()
    prohibition = (
        "Do not call `mcp__hilclaw__board_run` yourself (ADR-0142 decision 4; "
        "ADR-0139 decision 5)."
    )
    assert only_forbidden(text, "board_run") == [prohibition]
    assert "sim_run" not in text
    assert "sim.run" not in text
    assert "waits on `board.run`" not in text
    assert "ADR-0142 decision 7" not in text


def round_step(number):
    steps = between(prompt_text(), "## The round steps", "The stop:")
    part = steps.split(f" {number}. **", 1)[1]
    return part.split(f" {number + 1}. **", 1)[0]


def test_the_prompt_delegates_the_measurement_to_the_experiment_runner():
    text = prompt_text()
    assert (SOURCE / "agents" / EXPERIMENT_RUNNER).is_file()
    assert "to `experiment-runner`" in text
    assert "steps 2, 3, 4 and 5" in text
    step = round_step(5)
    assert step.startswith("Round 0 only.** Delegate to `experiment-runner`")
    assert "`round` 0, `candidate` 1, `attempt` 1, and no place" in step
    assert "`execution`" not in step
    for word in ('`"converged"`', '`"not_converged"`', '`"broken"`'):
        assert word in step
    going = step.split('When the report gives the `outcome` `"converged"`', 1)[1]
    going = going.split("On any other report", 1)[0]
    assert 'go to "The closing steps of a round"' in going
    assert "no `case.write`, then `round.end`, then `run.commit`" in going
    other = step.split("On any other report", 1)[1]
    assert '`"broken"`' in other
    assert "a failure kind" in other
    assert "no report you can read" in other
    assert "come to the stop" in other
    for cited in ("ADR-0142 decision 4", "ADR-0142 decision 6", "ADR-0119 decisions 2"):
        assert cited in step


def test_step_4_goes_on_to_step_5_only_when_verified_at_board():
    step = round_step(4)
    going = 'Go on to step 5 only when it gives the standing `"verified"` at `board`'
    assert going in step
    assert "On any other report come to the stop" in step
    assert "waits on" not in step


def test_the_prompt_makes_no_check_of_its_own():
    text = prompt_text()
    assert "Use only `mcp__hilclaw__correctness_check`" not in text
    assert "Use only `mcp__hilclaw__checks_read`" not in text
    only_forbidden(text, "correctness_check")
    only_forbidden(text, "checks_read")


def test_the_prompt_reaches_the_closing_steps_from_steps_5_and_12():
    heading = "### The closing steps of a round"
    text = prompt_text()
    assert heading in text
    closing = text.split(heading, 1)[1]
    assert "Round 0 reaches them after step 5" in closing
    assert "a round ≥ 1 after step 12 (ADR-0172 decision 6)" in closing
    assert "only once later slices" not in text


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
    return between(prompt_text(), "The stop:", "### The closing steps of a round")


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
    assert "No turn goes past this stop" not in stop
    assert "it follows step 2, 3, 4 or 5 as they say" in stop
    assert "reaches the closing steps below only through step 5" in stop
    assert "a turn of a round ≥ 1 only through step 12" in stop
    assert "ADR-0143 decisions 2 and 7" in stop
    assert stop.index("once the report") < stop.index("mcp__hilclaw__run_commit")
    assert stop.index("mcp__hilclaw__run_commit") < stop.index("end the session")
    assert "Later slices of the definition" not in prompt_text()


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
    assert closing_step(3).startswith(
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


def test_the_technique_selector_frontmatter():
    data = (SOURCE / "agents" / TECHNIQUE_SELECTOR).read_bytes()
    assert b"\r" not in data
    found = frontmatter(data.decode("utf-8"))
    assert set(found) == {"name", "description", "tools"}
    assert found["name"] == "technique-selector"
    assert found["description"]
    tools = [name.strip() for name in found["tools"].split(",")]
    assert len(tools) == len(set(tools))
    assert set(tools) == TECHNIQUE_SELECTOR_TOOLS
    served = served_names()
    for name in tools:
        if name.startswith("mcp__hilclaw__"):
            assert name in served
    for name in (
        "Bash",
        "Write",
        "Edit",
        "NotebookEdit",
        "Agent",
        "Skill",
        "mcp__hilclaw__timings_compare",
    ):
        assert name not in tools


def test_the_technique_selector_body():
    text = " ".join(
        (SOURCE / "agents" / TECHNIQUE_SELECTOR).read_text(encoding="utf-8").split()
    )
    body = text.split("---", 2)[2]
    assert "names the run id and the round, and no place" in body
    assert "Every tool request carries the run id given in the delegation" in body
    assert "write nothing by any means but `mcp__hilclaw__hypotheses_write`" in body
    on_record = between(body, "On `invalid_request` or `cases_mismatch`", "On any")
    assert "correct the record and send it again" in on_record
    assert "On any other kind, send nothing further, report the kind and end" in body
    assert "Write no `cases_read` and no basis entry of kind `case`" not in body
    assert "no lookup tool is in your list" not in body
    assert "tests at least one system hypothesis" in body
    assert "at least one such input" in body
    assert "Request no check, measurement, spec or coder call" in body
    assert "`tested_by`" in body
    for cited in ("ADR-0112 decision 2", "ADR-0112 decision 3", "ADR-0132 decision 7"):
        assert cited in body


def test_the_prompt_delegates_the_selection_in_later_rounds():
    text = prompt_text()
    assert (SOURCE / "agents" / TECHNIQUE_SELECTOR).is_file()
    assert "to `technique-selector`, only as step 6 says" in text
    assert "In a round ≥ 1 there are no steps 2 to 5: step 6 follows step 1" in (
        round_step(2)
    )
    selection = round_step(6)
    assert selection.startswith(
        "Round ≥ 1 only.** Delegate to `technique-selector` with the `Agent`"
    )
    assert "names your run id and the round, and no place" in selection
    assert "go on to step 7" in selection
    read = round_step(7)
    assert read.startswith("Round ≥ 1 only.** Call `mcp__hilclaw__hypotheses_read`")
    assert "whatever the report of step 6 said" in read
    failed = between(read, "If the call fails with any kind", "If it returns")
    assert "report the kind in one line and come to the stop" in failed
    returned = read.split("If it returns the round's record", 1)[1]
    assert "go on to step 8 (ADR-0171 decision 6)" in returned
    assert "come to the stop" not in returned
    assert "ADR-0132 decision 6" in read


def test_the_stop_follows_the_read_in_later_rounds():
    stop = the_stop()
    later = stop.split("In other rounds it follows step 7", 1)[1]
    assert "after a failed read" in later
    assert "and step 8 or step 12 as they say" in later
    assert "ADR-0172 decisions 2, 5 and 7" in later
    assert "After a report of the coder-driver" not in later
    assert "not yet defined" not in stop
    assert "Nor is a round ≥ 1 (ADR-0171 decision 6; ADR-0172 decision 7)" in later


def test_the_prompt_names_hypotheses_write_only_in_the_prohibition():
    text = prompt_text()
    naming = only_forbidden(text, "hypotheses_write")
    assert len(naming) == 1
    assert "Do not call `mcp__hilclaw__hypotheses_write` yourself" in naming[0]
    reading = [
        s
        for s in re.split(r"(?<=\.) ", text)
        if "Use `mcp__hilclaw__hypotheses_read`" in s
    ]
    assert len(reading) == 1
    assert "only to read the round's hypothesis record in step 7" in reading[0]


def test_only_step_8_of_a_later_round_delegates_the_coder_call():
    for number in (2, 3, 4, 5):
        assert round_step(number).startswith("Round 0 only.**")
    for number in (6, 7, 9, 10, 11, 12):
        step = round_step(number)
        for word in ("coder-driver", "spec_write", "coder_run"):
            assert word not in step
    for number in (6, 7, 8):
        step = round_step(number)
        for word in (
            "evaluator",
            "experiment-runner",
            "case_write",
            "case.write",
            "round_end",
            "round.end",
            "closing steps",
        ):
            assert word not in step
    for number in (9, 10, 11):
        step = round_step(number)
        for word in ("case_write", "case.write", "round_end", "round.end"):
            assert word not in step
        assert "closing steps" not in step
    steps = between(prompt_text(), "## The round steps", "The stop:")
    assert " 12. **" in steps
    assert " 13. **" not in steps
    read = round_step(7)
    failed = between(read, "If the call fails with any kind", "If it returns")
    assert "come to the stop" in failed
    assert "step 8" not in failed
    assert read.index("If the call fails") < read.index("go on to step 8")


def test_step_8_delegates_the_coder_call_with_the_choice():
    step = round_step(8)
    assert step.startswith(
        "Round ≥ 1 only.** If the report of step 6 holds exactly one "
        "`techniques:` line, delegate to `coder-driver` with the `Agent` tool"
    )
    chosen, other = step.split(
        "If the report of step 6 does not hold exactly one `techniques:` line", 1
    )
    assert "`round` the round, `candidate` 1, `attempt` 1" in chosen
    assert "the ids of that line in its order or that there are none" in chosen
    assert "and no place" in chosen
    assert "report it in one line" in chosen
    assert "delegate to `coder-driver` no second time, issue no call yourself" in (
        chosen
    )
    assert "ask for no repair" in chosen
    assert "spec_write" not in step
    assert "coder_run" not in step
    assert "report in one line that no choice was given" in other
    assert "come to the stop, delegating nothing" in other
    assert "coder-driver" not in other
    assert "ADR-0171 decisions 5 and 6" in chosen
    assert "ADR-0171 decision 6" in other
    assert (
        "to `coder-driver`, only as step 8 says (ADR-0171 decision 6)" in prompt_text()
    )


def test_the_stop_names_step_8():
    stop = the_stop()
    assert "step 8 or step 12 as they say" in stop
    assert stop.index("step 8 or step 12") < stop.index("mcp__hilclaw__run_commit")
    assert "not yet defined" not in stop


def selector_body():
    text = " ".join(
        (SOURCE / "agents" / TECHNIQUE_SELECTOR).read_text(encoding="utf-8").split()
    )
    return text.split("---", 2)[2]


def test_the_technique_selector_reads_the_catalog():
    given = between(selector_body(), "## What you are given", "## Fixed rules")
    assert "`mcp__hilclaw__catalog_read` gives the `## When` selection criteria" in (
        given
    )
    assert "and nothing more (ADR-0171 decision 3)" in given


def test_the_technique_selector_is_given_the_case_lookup():
    given = between(selector_body(), "## What you are given", "## Fixed rules")
    assert "`mcp__hilclaw__cases_lookup` gives the lookup of the stored cases" in (
        given
    )
    assert "their `cases_read` value and the lookup's reports" in given
    assert "(ADR-0173 decisions 2 and 3)" in given


def test_the_technique_selector_looks_up_the_cases_before_the_record():
    rules = between(selector_body(), "## Fixed rules", "## The record")
    lookup = between(rules, "Before you send the record", "After a result")
    assert "call `mcp__hilclaw__cases_lookup` (ADR-0173 decision 5)" in lookup
    assert "On `invalid_request`, correct the request and send it again" in lookup
    assert (
        "On any other kind of that call, send no record and no further request, "
        "report the kind and end (ADR-0173 decision 4)"
    ) in lookup
    copy = rules.split("After a result", 1)[1].split("Keep ADR-0112", 1)[0]
    assert "`cases_read` equal to the result's `cases_read`" in copy
    assert "whole and in its order, also when it is empty" in copy
    assert "reports or `key` is `null` does not change this" in copy
    assert "(ADR-0173 decisions 3 and 4)" in copy
    assert rules.index("Before you send the record") < rules.index(
        "Keep ADR-0112 decisions 2 and 3"
    )


def test_the_technique_selector_names_only_cases_of_the_result():
    cases = between(selector_body(), "## The cases", "## The choice of techniques")
    named = "names a case of the result's `cases` by its `run_id` and `round`"
    assert named in cases
    assert "a hypothesis in its `hypothesis_record`" in cases
    assert "A reported file is no case and is not named (ADR-0173 decision 3)" in (
        cases
    )
    assert "a past rejection forbids no retry and past performance is no target" in (
        cases
    )
    assert "(FR-15; FR-18; ADR-0173 decision 5)" in cases
    assert "ADR-0073 decision 2" in cases
    for word in ("best", "rank", "most recent"):
        assert word not in cases.lower()


def test_the_technique_selector_reports_the_lookup():
    report = selector_body().split("## Your report", 1)[1]
    line = between(report, "For the `mcp__hilclaw__cases_lookup` request", "When")
    assert "the number of cases or the failure kind" in line
    assert "one line per report with its `kind` and `path`" in line
    assert "(ADR-0173 decision 5)" in line


def test_the_technique_selector_chooses_the_techniques():
    choice = between(selector_body(), "## The choice of techniques", "## Your report")
    assert "After the round's record exists" in choice
    assert "spec of candidate 1" in choice
    weigh = choice.split("Weigh, in this order:", 1)[1]
    first = weigh.index("the round's hypotheses")
    second = weigh.index("the `## When` sections")
    third = weigh.index("earlier attempts")
    assert first < second < third
    assert "`tested_by` holds candidate 1" in weigh
    assert "The hypotheses name no technique" in choice
    assert "ADR-0059 decision 3" in choice
    assert "Which entries, how many and in what order are your judgement" in choice
    empty = choice.split("Choose an empty list", 1)[1]
    assert "answers `catalog_unusable`" in empty
    assert "its result holds no entry" in empty
    assert "no entry serves the round's hypotheses" in empty
    assert "ADR-0171 decision 2" in choice


def test_the_technique_selector_reports_one_techniques_line():
    body = selector_body()
    line = body.split("## Your report", 1)[1].split(
        "When the round's record exists", 1
    )[1]
    assert "answered `hypotheses_exist`" in line
    assert "returned a result or `catalog_unusable`" in line
    assert "exactly one line `techniques: <id>, <id>, ...`" in line
    assert "`techniques: none` for an empty list" in line
    assert "Otherwise give no such line (ADR-0171 decision 4)" in line
    assert "Request no check, measurement, spec or coder call" in body


def test_step_8_goes_on_by_the_coder_driver_report():
    chosen = round_step(8).split("If the report of step 6 does not hold exactly", 1)[0]
    checks = chosen.split("Go on to step 9 only when", 1)[1]
    checks = checks.split("When it is", 1)[0]
    assert "a result of `coder.run` whose `taken` holds at least one name" in checks
    verdicts = chosen.split("When it is", 1)[1].split("On any other report", 1)[0]
    assert "a result of `coder.run` with an empty `taken`" in verdicts
    assert "a failure kind of `coder.run`" in verdicts
    assert "go on to step 12" in verdicts
    assert "come to the stop" not in verdicts
    other = chosen.split("On any other report", 1)[1]
    for word in (
        "a failure kind of `spec.write`",
        "`spec_exists` among them",
        "the report that no list was given",
        "no report you can read",
    ):
        assert word in other
    assert "come to the stop (ADR-0172 decision 2)" in other
    assert "step 9" not in other
    assert "step 12" not in other
    assert chosen.index("step 9") < chosen.index("step 12")


def test_steps_9_to_12_follow_in_order():
    steps = between(prompt_text(), "## The round steps", "The stop:")
    places = [steps.index(f" {number}. **Round ≥ 1 only.**") for number in range(6, 13)]
    assert places == sorted(places)
    assert round_step(9).startswith("Round ≥ 1 only.** Delegate to `evaluator`")
    assert round_step(10).startswith("Round ≥ 1 only.** Delegate to `evaluator`")
    assert round_step(11).startswith(
        "Round ≥ 1 only.** Delegate to `experiment-runner` with the `Agent`"
    )
    assert round_step(12).startswith(
        "Round ≥ 1 only.** Delegate to `evaluator` with the `Agent` tool for "
        "the verdicts of the round"
    )


def test_step_9_checks_the_attempt_at_sim():
    step = round_step(9)
    assert (
        "the tuple `round` the round, `candidate` 1, `attempt` 1, the point `sim`, "
        "and no place and no `execution`" in step
    )
    assert "Take the standing from the report (ADR-0131 decision 7)" in step
    going = 'Go on to step 10 only when it gives the standing `"verified"` at `sim`'
    assert going in step
    other = step.split("On any other report", 1)[1]
    for word in ('`"not_verified"`', '`"undetermined"`', "no report you can read"):
        assert word in other
    assert "go on to step 12 (ADR-0172 decision 3)" in other
    assert "come to the stop" not in step
    assert "`board`" not in step


def test_step_10_checks_the_attempt_at_board():
    step = round_step(10)
    assert "the message naming the point `board` in place of `sim`" in step
    going = 'Go on to step 11 only when it gives the standing `"verified"` at `board`'
    assert going in step
    assert "On any other report go on to step 12 (ADR-0172 decision 3)" in step
    assert "come to the stop" not in step


def test_step_11_measures_and_always_goes_on_to_the_verdicts():
    step = round_step(11)
    assert (
        "the tuple `round` the round, `candidate` 1, `attempt` 1, and no place" in step
    )
    assert "`execution`" not in step
    for word in ('`"converged"`', '`"not_converged"`', '`"broken"`', "a failure kind"):
        assert word in step
    assert "no report you can read" in step
    assert "go on to step 12 (ADR-0172 decision 4)" in step
    assert "come to the stop" not in step
    assert "ADR-0142 decision 4" in step


def test_step_12_delegates_the_verdicts_and_goes_to_the_closing_steps():
    step = round_step(12)
    assert "names your run id and the round, and no tuple, no point and no place" in (
        step
    )
    assert "`candidate`" not in step
    assert "`sim`" not in step
    assert "Whatever it reports, report it in one line." in step
    written = step.split("When the report says that the verdicts file was written", 1)
    going = written[1].split("On any other report", 1)[0]
    assert "or that `verdicts.write` answered `verdicts_exist`" in going
    assert 'go to "The closing steps of a round"' in going
    assert "`case.write`, then `round.end`, then `run.commit`" in going
    assert "come to the stop" not in going
    other = step.split("On any other report", 1)[1]
    assert "another failure kind, or no report you can read" in other
    assert "come to the stop (ADR-0172 decision 5; FR-17)" in other
    assert "closing steps" not in other
    for cited in ("ADR-0172 decision 5", "ADR-0128 decisions 4 and 7"):
        assert cited in step


def test_round_0_still_skips_case_write():
    assert "no `case.write`, then `round.end`, then `run.commit`" in round_step(5)
    first = closing_step(1)
    assert first.startswith("`case.write`, only in a round ≥ 1.**")
    assert "In round 0, skip this step" in first


def test_no_later_round_step_calls_a_held_tool_itself():
    for number in range(6, 13):
        step = round_step(number)
        for word in (
            "spec_write",
            "coder_run",
            "board_run",
            "sim_run",
            "correctness_check",
            "checks_read",
            "verdicts_write",
            "timings_compare",
        ):
            assert word not in step
    steps = between(prompt_text(), "## The round steps", "The stop:")
    later = steps.split(" 6. **", 1)[1]
    assert len(re.findall(r"[Dd]elegate to `coder-driver` with", later)) == 1
    assert "delegate to `coder-driver` no second time" in later
    assert later.count("to `experiment-runner` with") == 1
    assert later.count("Delegate to `evaluator`") == 3


def test_the_prompt_names_verdicts_write_only_in_the_prohibition():
    prohibition = (
        "Do not call `mcp__hilclaw__verdicts_write` yourself (ADR-0128 decision 6; "
        "ADR-0172 decision 5)."
    )
    assert only_forbidden(prompt_text(), "verdicts_write") == [prohibition]


def test_the_agent_bullet_names_the_later_round_delegations():
    text = prompt_text()
    assert (
        "to `evaluator`, only as steps 9, 10 and 12 say, and to `experiment-runner`, "
        "only as step 11 says (ADR-0172 decisions 3 to 5)" in text
    )


def test_the_experiment_runner_serves_every_round():
    data = (SOURCE / "agents" / EXPERIMENT_RUNNER).read_text(encoding="utf-8")
    description = frontmatter(data)["description"]
    assert "round-0" not in description
    assert "in round 0 and in a round of at least 1" in description
    assert "ADR-0172 decision 4" in " ".join(data.split())
