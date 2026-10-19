import os
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
    }
    assert sorted(os.listdir(session)) == [".claude", "CLAUDE.md"]
    assert os.listdir(session / ".claude") == ["agents"]


def test_the_repository_definition_holds_the_prompt_and_the_evaluator():
    assert sorted(os.listdir(SOURCE)) == ["agents", PROMPT]
    assert (SOURCE / "agents").is_dir()
    assert os.listdir(SOURCE / "agents") == [EVALUATOR]


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
    registered = tools_module.default_registry(lambda: None).names()
    prefix = f"mcp__{mcp_front.SERVER_NAME}__"
    served = {prefix + mcp_front.mcp_name(name) for name in registered}
    for name in tools:
        if name.startswith("mcp__hilclaw__"):
            assert name in served


@pytest.mark.parametrize(
    "text",
    [
        "",
        "# Evaluator\n",
        "---\nname: evaluator\n",
        "---\nname evaluator\n---\n",
        "---\nname: a\nname: b\n---\n",
        "---\n name: a\n---\n",
        "---\n: a\n---\n",
    ],
)
def test_a_text_without_valid_frontmatter_is_refused(text):
    with pytest.raises(AssertionError):
        frontmatter(text)


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
