import json
import os
from pathlib import Path

import pytest

from hilclaw import config
from hilclaw.config import (
    DEFAULT_CONFIG_PATH,
    ENV_LOCAL_PATH,
    ENV_URL,
    ConfigError,
    DataRepo,
    load_data_repo,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
URL = "https://example.invalid/owner/data.git"
NOT_A_STRING = [123, 1.5, None, [], {}, True, False, ""]
NOT_AN_OBJECT = [[], "text", 7, None, True]


def write(directory, document):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "hilclaw.config.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def data_repo(**values):
    return {"data_repo": values}


@pytest.fixture
def conf(tmp_path):
    return write(tmp_path / "src", data_repo(url=URL, local_path="../data"))


def test_file_values_with_empty_environment(conf, tmp_path):
    repo = load_data_repo(conf, {})
    assert isinstance(repo, DataRepo)
    assert repo == (URL, tmp_path / "data")
    assert repo.url == URL
    assert isinstance(repo.local_path, Path)
    assert repo.local_path.is_absolute()


def test_committed_file_through_default_path(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert DEFAULT_CONFIG_PATH == REPO_ROOT / "hilclaw.config.json"
    repo = load_data_repo(environ={})
    assert repo.url == "https://github.com/myungjoo/HIL-Claw-data"
    assert repo.local_path == REPO_ROOT.parent / "HIL-Claw-data"


def test_str_and_path_config_path_agree(conf):
    assert load_data_repo(str(conf), {}) == load_data_repo(conf, {})


def test_relative_config_path_gives_absolute_result(conf, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    relative = os.path.join("src", "hilclaw.config.json")
    assert load_data_repo(relative, {}).local_path == Path(os.getcwd()) / "data"


def test_file_relative_path_ignores_working_directory(conf, tmp_path, monkeypatch):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert load_data_repo(conf, {}).local_path == tmp_path / "data"


def test_file_path_is_normalised(tmp_path):
    conf = write(tmp_path, data_repo(url=URL, local_path="a/./b/../c"))
    assert load_data_repo(conf, {}).local_path == tmp_path / "a" / "c"


def test_file_absolute_path_is_kept(tmp_path):
    target = tmp_path / "abs" / "data"
    conf = write(tmp_path / "src", data_repo(url=URL, local_path=str(target)))
    assert load_data_repo(conf, {}).local_path == target


def test_tilde_is_expanded(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    conf = write(tmp_path / "src", data_repo(url=URL, local_path="~/data"))
    assert load_data_repo(conf, {}).local_path == home / "data"
    assert load_data_repo(conf, {ENV_LOCAL_PATH: "~/other"}).local_path == (
        home / "other"
    )


def test_local_path_need_not_exist_and_nothing_is_written(conf, tmp_path):
    repo = load_data_repo(conf, {})
    assert not repo.local_path.exists()
    assert sorted(p.name for p in tmp_path.rglob("*")) == ["hilclaw.config.json", "src"]


def test_environment_variable_names():
    assert ENV_URL == "HILCLAW_DATA_REPO_URL"
    assert ENV_LOCAL_PATH == "HILCLAW_DATA_REPO_LOCAL_PATH"


def test_url_override_alone(conf, tmp_path):
    repo = load_data_repo(conf, {ENV_URL: "git@example.invalid:o/d.git"})
    assert repo == ("git@example.invalid:o/d.git", tmp_path / "data")


def test_local_path_override_alone(conf, tmp_path):
    target = tmp_path / "override"
    assert load_data_repo(conf, {ENV_LOCAL_PATH: str(target)}) == (URL, target)


def test_both_overrides(conf, tmp_path):
    target = tmp_path / "override"
    environ = {ENV_URL: "/srv/git/data.git", ENV_LOCAL_PATH: str(target)}
    assert load_data_repo(conf, environ) == ("/srv/git/data.git", target)


def test_environment_relative_path_uses_working_directory(conf, tmp_path, monkeypatch):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    repo = load_data_repo(conf, {ENV_LOCAL_PATH: os.path.join("x", "..", "rel")})
    assert repo.local_path == Path(os.getcwd()) / "rel"
    assert repo.local_path != tmp_path / "src" / "rel"


def test_empty_variables_do_not_override(conf, tmp_path):
    environ = {ENV_URL: "", ENV_LOCAL_PATH: ""}
    assert load_data_repo(conf, environ) == (URL, tmp_path / "data")


@pytest.mark.parametrize(
    ("present", "variable", "value"),
    [
        ({"local_path": "d"}, ENV_URL, URL),
        ({"url": URL}, ENV_LOCAL_PATH, "d"),
    ],
)
def test_absent_key_supplied_by_environment(
    tmp_path, monkeypatch, present, variable, value
):
    monkeypatch.chdir(tmp_path)
    conf = write(tmp_path, data_repo(**present))
    assert load_data_repo(conf, {variable: value}) == (URL, Path(os.getcwd()) / "d")


def test_absent_section_supplied_by_environment(tmp_path):
    conf = write(tmp_path, {})
    target = tmp_path / "d"
    environ = {ENV_URL: URL, ENV_LOCAL_PATH: str(target)}
    assert load_data_repo(conf, environ) == (URL, target)


def test_unknown_keys_are_ignored(tmp_path):
    document = {
        "schema_version": 9,
        "backends": {"sim": []},
        "data_repo": {"url": URL, "local_path": "d", "branch": "main", "x": None},
    }
    conf = write(tmp_path, document)
    assert load_data_repo(conf, {"UNRELATED": "1"}) == (URL, tmp_path / "d")


def test_default_environment_is_the_process_environment(conf, tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_URL, raising=False)
    monkeypatch.delenv(ENV_LOCAL_PATH, raising=False)
    assert load_data_repo(conf) == (URL, tmp_path / "data")
    target = tmp_path / "from-env"
    monkeypatch.setenv(ENV_URL, "ssh://example.invalid/d.git")
    monkeypatch.setenv(ENV_LOCAL_PATH, str(target))
    assert load_data_repo(conf) == ("ssh://example.invalid/d.git", target)
    assert load_data_repo(conf, None) == load_data_repo(conf, os.environ)


def test_no_state_is_kept_between_calls(tmp_path):
    conf = write(tmp_path, data_repo(url=URL, local_path="one"))
    assert load_data_repo(conf, {}).local_path == tmp_path / "one"
    write(tmp_path, data_repo(url=URL, local_path="two"))
    assert load_data_repo(conf, {}).local_path == tmp_path / "two"


def test_config_error_is_a_value_error():
    assert issubclass(ConfigError, ValueError)


def test_missing_file(tmp_path):
    path = tmp_path / "absent.json"
    with pytest.raises(ConfigError) as caught:
        load_data_repo(path, {ENV_URL: URL, ENV_LOCAL_PATH: "d"})
    assert str(path) in str(caught.value)
    assert isinstance(caught.value.__cause__, FileNotFoundError)


def test_missing_default_file(tmp_path, monkeypatch):
    path = tmp_path / "hilclaw.config.json"
    monkeypatch.setattr(config, "DEFAULT_CONFIG_PATH", path)
    with pytest.raises(ConfigError) as caught:
        load_data_repo(environ={})
    assert str(path) in str(caught.value)


def test_directory_as_config_path(tmp_path):
    with pytest.raises(ConfigError) as caught:
        load_data_repo(tmp_path, {})
    assert str(tmp_path) in str(caught.value)
    assert isinstance(caught.value.__cause__, OSError)


def test_config_path_with_a_nul_character(tmp_path):
    path = tmp_path / "a\0b.json"
    with pytest.raises(ConfigError) as caught:
        load_data_repo(path, {ENV_URL: URL, ENV_LOCAL_PATH: "d"})
    assert "cannot read" in str(caught.value)
    assert isinstance(caught.value.__cause__, ValueError)


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"{",
        b'{"data_repo": {"url": "u", "local_path": "d",}}',
        b"not json",
        b'\xef\xbb\xbf{"data_repo": {"url": "u", "local_path": "d"}}',
    ],
)
def test_not_json(tmp_path, raw):
    path = tmp_path / "hilclaw.config.json"
    path.write_bytes(raw)
    with pytest.raises(ConfigError) as caught:
        load_data_repo(path, {ENV_URL: URL, ENV_LOCAL_PATH: "d"})
    assert str(path) in str(caught.value)
    assert "not valid JSON" in str(caught.value)
    assert isinstance(caught.value.__cause__, json.JSONDecodeError)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"data_repo": {"url": "\xff", "local_path": "d"}}',
        b"\xff\xfe{\x00}\x00",
    ],
)
def test_not_utf8(tmp_path, raw):
    path = tmp_path / "hilclaw.config.json"
    path.write_bytes(raw)
    with pytest.raises(ConfigError) as caught:
        load_data_repo(path, {ENV_URL: URL, ENV_LOCAL_PATH: "d"})
    assert str(path) in str(caught.value)
    assert "not valid UTF-8" in str(caught.value)
    assert isinstance(caught.value.__cause__, UnicodeDecodeError)


@pytest.mark.parametrize("document", NOT_AN_OBJECT)
def test_top_level_is_not_an_object(tmp_path, document):
    conf = write(tmp_path, document)
    with pytest.raises(ConfigError) as caught:
        load_data_repo(conf, {ENV_URL: URL, ENV_LOCAL_PATH: "d"})
    assert str(conf) in str(caught.value)
    assert "top level" in str(caught.value)


@pytest.mark.parametrize("section", NOT_AN_OBJECT)
def test_data_repo_is_not_an_object(tmp_path, section):
    conf = write(tmp_path, {"data_repo": section})
    with pytest.raises(ConfigError) as caught:
        load_data_repo(conf, {ENV_URL: URL, ENV_LOCAL_PATH: "d"})
    assert str(conf) in str(caught.value)
    assert "data_repo:" in str(caught.value)


@pytest.mark.parametrize(
    ("document", "environ", "key", "variable"),
    [
        (data_repo(local_path="d"), {}, "url", ENV_URL),
        (data_repo(url=URL), {}, "local_path", ENV_LOCAL_PATH),
        (data_repo(local_path="d"), {ENV_URL: ""}, "url", ENV_URL),
        (data_repo(url=URL), {ENV_URL: "u"}, "local_path", ENV_LOCAL_PATH),
        (data_repo(), {ENV_LOCAL_PATH: "d"}, "url", ENV_URL),
        (data_repo(), {ENV_URL: URL}, "local_path", ENV_LOCAL_PATH),
        ({}, {}, "url", ENV_URL),
        ({"other": {"url": URL, "local_path": "d"}}, {}, "url", ENV_URL),
    ],
)
def test_missing_key_without_override(tmp_path, document, environ, key, variable):
    conf = write(tmp_path, document)
    with pytest.raises(ConfigError) as caught:
        load_data_repo(conf, environ)
    message = str(caught.value)
    assert str(conf) in message
    assert f"data_repo.{key}:" in message
    assert variable in message


@pytest.mark.parametrize("key", ["url", "local_path"])
@pytest.mark.parametrize("value", NOT_A_STRING)
def test_value_is_not_a_non_empty_string(tmp_path, key, value):
    values = {"url": URL, "local_path": "d", key: value}
    conf = write(tmp_path, data_repo(**values))
    with pytest.raises(ConfigError) as caught:
        load_data_repo(conf, {})
    assert str(conf) in str(caught.value)
    assert f"data_repo.{key}:" in str(caught.value)


@pytest.mark.parametrize(
    ("key", "variable"), [("url", ENV_URL), ("local_path", ENV_LOCAL_PATH)]
)
@pytest.mark.parametrize("value", [123, None, ""])
def test_malformed_file_value_is_an_error_even_when_overridden(
    tmp_path, key, variable, value
):
    values = {"url": URL, "local_path": "d", key: value}
    conf = write(tmp_path, data_repo(**values))
    with pytest.raises(ConfigError) as caught:
        load_data_repo(conf, {variable: "override"})
    assert f"data_repo.{key}:" in str(caught.value)
