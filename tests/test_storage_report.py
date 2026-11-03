import hashlib
import io
import json
import os
import sys

import pytest

from hilclaw import (
    clang_adapter,
    local_run,
    standin_container,
    storage_report,
    toolchain_check,
)
from hilclaw.storage_report import (
    CLIENT,
    EXIT_FAULT,
    EXIT_READ,
    EXIT_UNREADABLE,
    EXIT_USAGE,
    INSPECT_TIME_LIMIT_S,
    USAGE,
    exit_status,
    file_duplicates,
    image_duplicates,
    inspect_image,
    main,
    read_directory,
    read_tool_tag,
    report,
    retirement_candidates,
)
from hilclaw.toolchain_check import Component

posix_only = pytest.mark.skipif(os.name != "posix", reason="POSIX behaviour")
USAGE_LINE = f"hilclaw.storage_report: {USAGE}\n".encode()


def _id(n):
    return "sha256:" + f"{n:02x}" * 32


def component(program):
    return Component(
        assemble=clang_adapter.assemble_probe,
        interpret=clang_adapter.interpret_probe,
        interpret_container=clang_adapter.interpret_container_probe,
        program=program,
    )


COMPONENTS = {"clang": component("clang"), "nvcc": component("nvcc")}


def _result(status, stdout=b"", timed_out=False, command=()):
    return local_run.RunResult(
        returncode=None if timed_out else status,
        timed_out=timed_out,
        stdout=stdout,
        stderr=b"",
        command=tuple(command),
        duration_s=0.0,
    )


class FakeClient:
    """Stands for the container client: answers ``image inspect`` and ``run``."""

    def __init__(self):
        self.inspect = {}
        self.probe = {}
        self.calls = []

    def image(self, reference, n, tags, size=100):
        self.inspect[reference] = {"Id": _id(n), "RepoTags": tags, "Size": size}

    def holds(self, reference, program, version):
        self.probe[(reference, program)] = (0, f"{version}\n".encode())

    def run(self, command, *, timeout_s, env=None, **options):
        command = list(command)
        self.calls.append(command)
        if command[1:3] == ["image", "inspect"]:
            assert command[1:5] == ["image", "inspect", "--format", "{{json .}}"]
            assert timeout_s == INSPECT_TIME_LIMIT_S and env is None
            answer = self.inspect.get(command[5])
            if answer is None:
                return _result(1, command=command)
            if answer == "timeout":
                return _result(None, timed_out=True, command=command)
            if isinstance(answer, bytes):
                return _result(0, answer, command=command)
            return _result(0, json.dumps(answer).encode(), command=command)
        at = command.index("--entrypoint=")
        image, program = command[at + 1], command[at + 2]
        status, out = self.probe.get((image, program), (127, b""))
        return _result(status, out, command=command)

    def inspected(self):
        return [c[5] for c in self.calls if c[1:3] == ["image", "inspect"]]

    def started(self):
        return [c for c in self.calls if c[1] == "run"]


@pytest.fixture
def client(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(local_run, "run", fake.run)
    monkeypatch.setattr(os, "getuid", lambda: 1000, raising=False)
    monkeypatch.setattr(os, "getgid", lambda: 1000, raising=False)
    return fake


def _images(fake, references, environ=None):
    return report(
        images=references, environ=environ or {}, components=COMPONENTS, client="docker"
    )["images"]


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _symlink(target, link):
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links cannot be made here")


class Stream:
    def __init__(self, take=None, fail=None):
        self.data = b""
        self.take = take
        self.fail = fail

    def write(self, data):
        if self.fail is not None:
            raise self.fail
        taken = data if self.take is None else data[: self.take]
        self.data += taken
        return len(taken)

    def flush(self):
        pass


def test_constants():
    assert (EXIT_READ, EXIT_UNREADABLE, EXIT_USAGE, EXIT_FAULT) == (0, 10, 20, 21)
    assert CLIENT == toolchain_check.CLIENT == "docker"
    assert INSPECT_TIME_LIMIT_S == 30


@pytest.mark.parametrize(
    ("tag", "reading"),
    [
        ("nvcc:13.1", ("nvcc", (13, 1))),
        ("qnn:2.37.0.250724", ("qnn", (2, 37, 0, 250724))),
        ("localhost:5000/tools/nvcc:12", ("localhost:5000/tools/nvcc", (12,))),
        ("nvcc:latest", None),
        ("hilclaw-standin:2026-10-29", None),
        ("nvcc:13.", None),
        ("nvcc:v13", None),
        ("nvcc", None),
        (":13", None),
        ("localhost:5000/nvcc", None),
        (13, None),
    ],
)
def test_read_tool_tag(tag, reading):
    assert read_tool_tag(tag) == reading


# Files


def test_identical_files_in_two_directories_are_one_duplicate_group(tmp_path):
    _write(tmp_path / "a" / "setup.run", b"same")
    _write(tmp_path / "b" / "sub" / "copy.run", b"same")
    _write(tmp_path / "b" / "other.zip", b"other")
    a, b = str(tmp_path / "a"), str(tmp_path / "b")
    files = report([a, b], environ={})["files"]
    digest = hashlib.sha256(b"same").hexdigest()
    assert files["duplicates"] == [
        {
            "sha256": digest,
            "size": 4,
            "files": [
                {"directory": a, "path": "setup.run"},
                {"directory": b, "path": "sub/copy.run"},
            ],
        }
    ]
    second = files["directories"][1]
    assert second == {
        "directory": b,
        "state": "read",
        "message": None,
        "files": [
            {
                "path": "other.zip",
                "size": 5,
                "sha256": hashlib.sha256(b"other").hexdigest(),
            },
            {"path": "sub/copy.run", "size": 4, "sha256": digest},
        ],
        "skipped": [],
        "unreadable": [],
    }


def test_a_directory_named_twice_is_read_once_and_holds_no_duplicate(tmp_path):
    _write(tmp_path / "a" / "x", b"1")
    a = str(tmp_path / "a")
    files = report([a, a], environ={})["files"]
    assert len(files["directories"]) == 1
    assert files["duplicates"] == []


def test_two_names_of_one_file_are_no_duplicate(tmp_path):
    _write(tmp_path / "a" / "x", b"1")
    try:
        os.link(tmp_path / "a" / "x", tmp_path / "a" / "y")
    except OSError:
        pytest.skip("hard links cannot be made here")
    files = report([str(tmp_path / "a")], environ={})["files"]
    assert [f["path"] for f in files["directories"][0]["files"]] == ["x", "y"]
    assert files["duplicates"] == []


def test_a_symbolic_link_is_skipped_and_not_followed(tmp_path):
    _write(tmp_path / "a" / "x", b"1")
    _write(tmp_path / "outside" / "y", b"1")
    _symlink(tmp_path / "a" / "x", tmp_path / "a" / "link")
    _symlink(tmp_path / "outside", tmp_path / "a" / "dirlink")
    document = report([str(tmp_path / "a")], environ={})
    directory = document["files"]["directories"][0]
    assert [f["path"] for f in directory["files"]] == ["x"]
    assert directory["skipped"] == [
        {"path": "dirlink", "reason": "symbolic link"},
        {"path": "link", "reason": "symbolic link"},
    ]
    assert document["files"]["duplicates"] == []
    assert exit_status(document) == EXIT_READ


def test_an_entry_that_is_no_regular_file_is_skipped(tmp_path, monkeypatch):
    _write(tmp_path / "a" / "x", b"1")
    real = os.scandir

    class Odd:
        name = "fifo"
        path = str(tmp_path / "a" / "fifo")

        def is_symlink(self):
            return False

        def is_junction(self):
            return False

        def is_dir(self, follow_symlinks=True):
            return False

        def is_file(self, follow_symlinks=True):
            return False

    class Listing:
        def __init__(self, path):
            self.entries = list(real(path)) + [Odd()]

        def __enter__(self):
            return iter(self.entries)

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(os, "scandir", Listing)
    directory = read_directory(str(tmp_path / "a"))
    assert directory["skipped"] == [{"path": "fifo", "reason": "not a regular file"}]


def test_a_missing_directory_is_unreadable_and_the_others_are_read(tmp_path):
    _write(tmp_path / "a" / "x", b"1")
    missing = str(tmp_path / "missing")
    not_dir = str(tmp_path / "a" / "x")
    document = report([missing, not_dir, str(tmp_path / "a")], environ={})
    first, second, third = document["files"]["directories"]
    assert (first["state"], first["message"]) == (
        "unreadable",
        "the directory could not be listed",
    )
    assert first["files"] == first["skipped"] == first["unreadable"] == []
    assert second["state"] == "unreadable"
    assert third["state"] == "read" and len(third["files"]) == 1
    assert exit_status(document) == EXIT_UNREADABLE


def test_an_unreadable_file_and_subdirectory_are_listed_and_the_walk_goes_on(
    tmp_path, monkeypatch
):
    _write(tmp_path / "a" / "bad", b"1")
    _write(tmp_path / "a" / "good", b"2")
    _write(tmp_path / "a" / "locked" / "z", b"3")
    real_hash = storage_report._sha256_and_identity
    real_scandir = os.scandir

    def hashing(path):
        if os.path.basename(path) == "bad":
            raise PermissionError("no")
        return real_hash(path)

    def listing(path):
        if os.path.basename(path) == "locked":
            raise PermissionError("no")
        return real_scandir(path)

    monkeypatch.setattr(storage_report, "_sha256_and_identity", hashing)
    monkeypatch.setattr(os, "scandir", listing)
    document = report([str(tmp_path / "a")], environ={})
    directory = document["files"]["directories"][0]
    assert directory["state"] == "read"
    assert [f["path"] for f in directory["files"]] == ["good"]
    assert directory["unreadable"] == [
        {"path": "bad", "message": "the file could not be read"},
        {"path": "locked", "message": "the directory could not be listed"},
    ]
    assert exit_status(document) == EXIT_UNREADABLE


def test_a_file_that_is_no_regular_file_when_opened_is_unreadable(
    tmp_path, monkeypatch
):
    _write(tmp_path / "a" / "x", b"1")

    class Status:
        st_mode = 0o010644

    monkeypatch.setattr(os, "fstat", lambda fd: Status())
    directory = read_directory(str(tmp_path / "a"))
    monkeypatch.undo()
    assert directory["unreadable"] == [
        {"path": "x", "message": "the file could not be read"}
    ]


def test_read_directory_refuses_a_directory_that_is_not_str(tmp_path):
    with pytest.raises(TypeError):
        read_directory(tmp_path)
    with pytest.raises(TypeError):
        report([tmp_path], environ={})


def test_file_duplicates_without_identities_counts_each_entry():
    entry = {"path": "x", "size": 1, "sha256": "ab"}
    directories = [
        {"directory": "d", "files": [entry, {**entry, "path": "y"}]},
        {"directory": "e", "files": [{**entry, "sha256": "cd"}]},
    ]
    assert file_duplicates(directories) == [
        {
            "sha256": "ab",
            "size": 1,
            "files": [{"directory": "d", "path": "x"}, {"directory": "d", "path": "y"}],
        }
    ]
    same = {("d", "x"): (1, 2), ("d", "y"): (1, 2)}
    assert file_duplicates(directories, same) == []


# Images


def test_two_image_ids_holding_one_nvcc_version_are_a_duplicate(client):
    client.image("a:1", 1, ["a:1"])
    client.image("b:1", 2, ["b:1"])
    for reference in ("a:1", "b:1"):
        client.holds(reference, "nvcc", "Cuda compilation tools, release 13.1")
    client.holds("a:1", "clang", "clang version 14")
    client.holds("b:1", "clang", "clang version 18")
    images = _images(client, ["a:1", "b:1"])
    assert images["duplicates"] == [
        {
            "component": "nvcc",
            "version": "Cuda compilation tools, release 13.1",
            "images": [_id(1), _id(2)],
        }
    ]
    first = images["images"][0]
    assert first["references"] == ["a:1"]
    assert (first["id"], first["size"], first["tags"]) == (_id(1), 100, ["a:1"])
    assert (first["state"], first["message"]) == ("read", None)
    assert first["components"]["clang"] == {
        "state": "present",
        "version": "clang version 14",
        "message": None,
    }
    assert first["components"]["nvcc"]["state"] == "present"


def test_two_tags_of_one_image_id_are_one_image_and_no_duplicate(client):
    client.image("a:1", 1, ["a:1", "a:latest"])
    client.image("a:latest", 1, ["a:1", "a:latest"])
    client.holds("a:1", "nvcc", "13.1")
    images = _images(client, ["a:1", "a:latest", "a:1"])
    assert len(images["images"]) == 1
    assert images["images"][0]["references"] == ["a:1", "a:latest"]
    assert images["duplicates"] == []
    assert client.inspected() == ["a:1", "a:latest"]
    assert len(client.started()) == len(COMPONENTS)


def _tools(client):
    client.image("nvcc:12.4", 1, ["nvcc:12.4"], size=111)
    client.image("nvcc:13.1", 2, ["nvcc:13.1", "nvcc:latest"])
    client.holds("nvcc:12.4", "nvcc", "12.4")
    client.holds("nvcc:13.1", "nvcc", "13.1")
    client.holds("nvcc:13.1", "clang", "clang 18")


def test_an_older_tool_image_beside_a_newer_one_holding_all_is_a_candidate(client):
    _tools(client)
    images = _images(client, ["nvcc:12.4", "nvcc:13.1"])
    assert images["retirement_candidates"] == [
        {
            "id": _id(1),
            "tag": "nvcc:12.4",
            "size": 111,
            "replaced_by": {"id": _id(2), "tag": "nvcc:13.1"},
        }
    ]
    assert images["duplicates"] == []


def test_the_newest_of_three_replaces_and_the_middle_is_a_candidate_too(client):
    _tools(client)
    client.image("nvcc:11", 3, ["nvcc:11"])
    client.holds("nvcc:11", "nvcc", "11")
    images = _images(client, ["nvcc:11", "nvcc:12.4", "nvcc:13.1"])
    candidates = images["retirement_candidates"]
    assert [c["tag"] for c in candidates] == ["nvcc:11", "nvcc:12.4"]
    assert {c["replaced_by"]["tag"] for c in candidates} == {"nvcc:13.1"}


def test_an_image_holding_the_newest_version_is_never_a_candidate(client):
    _tools(client)
    client.image("nvcc:13.2", 3, ["nvcc:12.9", "nvcc:13.2"])
    client.holds("nvcc:13.2", "nvcc", "13.2")
    client.holds("nvcc:13.2", "clang", "clang 18")
    images = _images(client, ["nvcc:12.4", "nvcc:13.1", "nvcc:13.2"])
    candidates = images["retirement_candidates"]
    assert [c["tag"] for c in candidates] == ["nvcc:12.4", "nvcc:13.1"]
    assert {c["replaced_by"]["tag"] for c in candidates} == {"nvcc:13.2"}


@pytest.mark.parametrize("variable", ["HILCLAW_STANDIN_IMAGE", "HILCLAW_CODER_IMAGE"])
def test_an_image_a_runtime_variable_names_is_never_a_candidate(client, variable):
    _tools(client)
    images = _images(client, ["nvcc:12.4", "nvcc:13.1"], {variable: "nvcc:12.4"})
    assert images["retirement_candidates"] == []


def test_a_runtime_variable_is_matched_by_the_id_the_client_gives(client):
    _tools(client)
    client.image("registry.example/nvcc-old", 1, ["nvcc:12.4"])
    environ = {"HILCLAW_CODER_IMAGE": "registry.example/nvcc-old"}
    images = _images(client, ["nvcc:12.4", "nvcc:13.1"], environ)
    assert images["retirement_candidates"] == []
    assert "registry.example/nvcc-old" in client.inspected()


def test_a_runtime_variable_without_tag_matches_its_latest_tag(client):
    _tools(client)
    client.image("nvcc:12.4", 1, ["nvcc:12.4", "old:latest"])
    environ = {"HILCLAW_STANDIN_IMAGE": "old"}
    images = _images(client, ["nvcc:12.4", "nvcc:13.1"], environ)
    assert images["retirement_candidates"] == []


@pytest.mark.parametrize(
    "environ",
    [
        {"HILCLAW_STANDIN_IMAGE": "-bad", "HILCLAW_CODER_IMAGE": "a b"},
        {"HILCLAW_STANDIN_IMAGE": "", "HILCLAW_CODER_IMAGE": ""},
        {"HILCLAW_CODER_IMAGE": "gone:1"},
    ],
)
def test_a_refused_empty_or_unknown_runtime_variable_names_nothing(client, environ):
    _tools(client)
    images = _images(client, ["nvcc:12.4", "nvcc:13.1"], environ)
    assert [c["tag"] for c in images["retirement_candidates"]] == ["nvcc:12.4"]


def test_an_older_image_holding_a_component_the_newer_lacks_is_no_candidate(client):
    _tools(client)
    client.holds("nvcc:12.4", "clang", "clang 14")
    client.probe.pop(("nvcc:13.1", "clang"))
    images = _images(client, ["nvcc:12.4", "nvcc:13.1"])
    assert images["retirement_candidates"] == []


def test_images_holding_no_component_are_no_candidates(client):
    client.image("ubuntu:22.04", 1, ["ubuntu:22.04"])
    client.image("ubuntu:24.04", 2, ["ubuntu:24.04"])
    images = _images(client, ["ubuntu:22.04", "ubuntu:24.04"])
    assert images["retirement_candidates"] == []


def test_tags_that_do_not_read_as_tool_and_version_give_no_candidate(client):
    client.image("hilclaw-standin:2026-10-29", 1, ["hilclaw-standin:2026-10-29"])
    client.image("hilclaw-standin:local", 2, ["hilclaw-standin:local"])
    client.holds("hilclaw-standin:2026-10-29", "clang", "clang 18")
    client.holds("hilclaw-standin:local", "clang", "clang 18")
    images = _images(client, ["hilclaw-standin:2026-10-29", "hilclaw-standin:local"])
    assert images["retirement_candidates"] == []


def test_an_image_with_an_unreadable_component_is_no_candidate(client):
    _tools(client)
    client.probe[("nvcc:12.4", "clang")] = (1, b"x\n")
    document = report(
        images=["nvcc:12.4", "nvcc:13.1"],
        environ={},
        components=COMPONENTS,
        client="docker",
    )
    assert document["images"]["retirement_candidates"] == []
    assert exit_status(document) == EXIT_UNREADABLE


@pytest.mark.parametrize(
    "answer",
    [
        None,
        "timeout",
        b"not json",
        b"[]",
        {"Id": "", "RepoTags": [], "Size": 1},
        {"Id": _id(9), "RepoTags": "x:1", "Size": 1},
        {"Id": _id(9), "RepoTags": [1], "Size": 1},
        {"Id": _id(9), "RepoTags": [], "Size": True},
        {"Id": _id(9), "RepoTags": [], "Size": -1},
    ],
)
def test_an_image_the_client_cannot_read_is_unreadable_and_the_others_are_read(
    client, answer
):
    _tools(client)
    if answer is not None:
        client.inspect["bad:1"] = answer
    document = report(
        images=["bad:1", "nvcc:12.4", "nvcc:13.1"],
        environ={},
        components=COMPONENTS,
        client="docker",
    )
    bad, *others = document["images"]["images"]
    assert bad["references"] == ["bad:1"]
    assert (bad["id"], bad["size"], bad["tags"], bad["components"]) == (
        None,
        None,
        [],
        {},
    )
    assert bad["state"] == "unreadable"
    assert bad["message"] in (
        "the client could not read the image",
        "the client's answer could not be read",
    )
    assert [o["state"] for o in others] == ["read", "read"]
    assert len(document["images"]["retirement_candidates"]) == 1
    assert exit_status(document) == EXIT_UNREADABLE


def test_null_repo_tags_read_as_no_tags(client):
    client.inspect["x"] = {"Id": _id(1), "RepoTags": None, "Size": 0}
    assert _images(client, ["x"])["images"][0]["tags"] == []


def test_an_image_no_container_of_can_be_used_is_unreadable(client):
    client.image("a:1", 1, ["a:1"])
    client.probe[("a:1", "clang")] = (125, b"")
    document = report(
        images=["a:1"], environ={}, components=COMPONENTS, client="docker"
    )
    image = document["images"]["images"][0]
    assert (image["state"], image["components"]) == ("unreadable", {})
    assert image["id"] == _id(1)
    assert exit_status(document) == EXIT_UNREADABLE


def test_an_exception_in_a_probe_makes_that_image_unreadable(client, monkeypatch):
    _tools(client)
    real = toolchain_check.image_entry

    def probing(reference, **options):
        if reference == "nvcc:12.4":
            raise RuntimeError("boom")
        return real(reference, **options)

    monkeypatch.setattr(toolchain_check, "image_entry", probing)
    document = report(
        images=["nvcc:12.4", "nvcc:13.1"],
        environ={},
        components=COMPONENTS,
        client="docker",
    )
    first, second = document["images"]["images"]
    assert (first["state"], first["message"]) == (
        "unreadable",
        "the components of the image could not be read",
    )
    assert second["state"] == "read"
    assert document["images"]["retirement_candidates"] == []
    assert exit_status(document) == EXIT_UNREADABLE


def test_an_absent_client_makes_every_image_unreadable(tmp_path):
    missing = str(tmp_path / "no-such-client")
    found, message = inspect_image("a:1", client=missing)
    assert (found, message) == (None, "the client could not read the image")
    document = report(images=["a:1"], environ={}, client=missing)
    assert document["images"]["images"][0]["state"] == "unreadable"


def test_inspect_image_reads_one_answer(client):
    client.image("a:1", 1, ["a:1"], size=7)
    assert inspect_image("a:1") == ({"id": _id(1), "size": 7, "tags": ["a:1"]}, None)
    assert client.calls == [
        ["docker", "image", "inspect", "--format", "{{json .}}", "a:1"]
    ]


@pytest.mark.parametrize(("reference", "error"), [("-x", ValueError), (1, TypeError)])
def test_inspect_image_and_report_refuse_a_bad_reference_before_starting(
    client, reference, error
):
    with pytest.raises(error):
        inspect_image(reference)
    with pytest.raises(error):
        report(images=["ok:1", reference], environ={})
    assert client.calls == []


@pytest.mark.parametrize("given", ["a:1", b"a:1"])
def test_report_refuses_one_str_for_a_sequence(given):
    with pytest.raises(TypeError):
        report(images=given, environ={})
    with pytest.raises(TypeError):
        report(directories=given, environ={})


def test_image_duplicates_skip_unread_images_and_count_an_id_once():
    present = {"state": "present", "version": "1", "message": None}
    images = [
        {"id": None, "components": {"c": present}},
        {"id": "i", "components": {"c": present}},
        {"id": "i", "components": {"c": present}},
        {"id": "j", "components": {"c": {**present, "state": "absent"}}},
    ]
    assert image_duplicates(images) == []


def test_retirement_candidates_with_no_named_set():
    def image(n, tag, state="read", empty=False):
        return {
            "id": _id(n),
            "size": 1,
            "tags": [tag],
            "state": state,
            "components": {} if empty else {"c": present},
        }

    present = {"state": "present", "version": "1", "message": None}
    old, new = image(1, "t:1"), image(2, "t:2")
    assert [c["id"] for c in retirement_candidates([old, new])] == [_id(1)]
    assert retirement_candidates([image(1, "t:1", empty=True), new]) == []
    assert retirement_candidates([old, new], {_id(1)}) == []
    assert retirement_candidates([image(1, "t:1", "unreadable"), new]) == []
    assert retirement_candidates([old, image(2, "t:2", "unreadable")]) == []


def test_exit_status_is_read_for_a_clean_report():
    assert exit_status(report(environ={})) == EXIT_READ


# The command line


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["--image"],
        ["--file-dir"],
        ["--image", "-x"],
        ["--file-dir", "-x"],
        ["--file-dir", "--image"],
        ["--file-dir", ""],
        ["--image", "a b"],
        ["--bogus", "x"],
        ["positional"],
        ["--help"],
        ["--image", "a:1", "--file-dir"],
    ],
)
def test_usage_errors_start_nothing(argv, client, monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("nothing may be read")

    monkeypatch.setattr(storage_report, "report", refused)
    stdout, stderr = Stream(), Stream()
    assert main(argv, stdout=stdout, stderr=stderr, environ={}) == EXIT_USAGE
    assert stdout.data == b""
    assert stderr.data == USAGE_LINE
    assert client.calls == []


def test_main_writes_one_ascii_document_for_files_only(tmp_path):
    _write(tmp_path / "a" / "é.run", b"1")
    stdout, stderr = Stream(), Stream()
    status = main(
        ["--file-dir", str(tmp_path / "a")], stdout=stdout, stderr=stderr, environ={}
    )
    assert status == EXIT_READ
    assert stderr.data == b""
    assert stdout.data.endswith(b"}\n") and stdout.data.count(b"\n") == 1
    stdout.data.decode("ascii")
    document = json.loads(stdout.data)
    assert list(document) == ["files", "images"]
    assert list(document["files"]) == ["directories", "duplicates"]
    assert list(document["images"]) == [
        "images",
        "duplicates",
        "retirement_candidates",
    ]
    assert document["images"]["images"] == []
    assert "schema_version" not in json.dumps(document)


def test_main_reads_images_only_and_reports_no_environment_value(client):
    _tools(client)
    client.image("hidden:9", 9, ["hidden:9"])
    environ = {
        "HILCLAW_CODER_IMAGE": "hidden:9",
        "HILCLAW_CODER_OAUTH_TOKEN": "secret-token",
    }
    stdout, stderr = Stream(), Stream()
    status = main(
        ["--image", "nvcc:12.4", "--image", "nvcc:13.1"],
        stdout=stdout,
        stderr=stderr,
        environ=environ,
        components=COMPONENTS,
        client="docker",
    )
    assert status == EXIT_READ
    assert b"hidden" not in stdout.data and b"secret-token" not in stdout.data
    document = json.loads(stdout.data)
    assert document["files"] == {"directories": [], "duplicates": []}
    assert len(document["images"]["retirement_candidates"]) == 1


def test_main_returns_unreadable_after_writing_the_report(tmp_path):
    stdout = Stream()
    status = main(
        ["--file-dir", str(tmp_path / "missing")],
        stdout=stdout,
        stderr=Stream(),
        environ={},
    )
    assert status == EXIT_UNREADABLE
    assert json.loads(stdout.data)["files"]["directories"][0]["state"] == "unreadable"


@pytest.mark.parametrize(
    "stdout", [Stream(fail=OSError("closed")), Stream(take=3), None]
)
def test_a_standard_output_that_cannot_take_the_report_is_a_fault(
    tmp_path, monkeypatch, stdout
):
    monkeypatch.setattr(storage_report, "_standard", lambda name: None)
    stderr = Stream()
    argv = ["--file-dir", str(tmp_path)]
    assert main(argv, stdout=stdout, stderr=stderr, environ={}) == EXIT_FAULT
    assert stderr.data == b"hilclaw.storage_report: fault: OSError\n"


def test_an_exception_of_the_command_is_a_fault(tmp_path, monkeypatch):
    def failing(*args, **kwargs):
        raise RuntimeError("secret text")

    monkeypatch.setattr(storage_report, "report", failing)
    stdout, stderr = Stream(), Stream()
    argv = ["--file-dir", str(tmp_path)]
    assert main(argv, stdout=stdout, stderr=stderr, environ={}) == EXIT_FAULT
    assert stdout.data == b""
    assert stderr.data == b"hilclaw.storage_report: fault: RuntimeError\n"


def test_main_defaults_to_the_process_streams_and_arguments(tmp_path, monkeypatch):
    out = io.BytesIO()

    class Std:
        buffer = out

    monkeypatch.setattr(sys, "stdout", Std())
    monkeypatch.setattr(sys, "argv", ["x", "--file-dir", str(tmp_path)])
    monkeypatch.delenv("HILCLAW_STANDIN_IMAGE", raising=False)
    monkeypatch.delenv("HILCLAW_CODER_IMAGE", raising=False)
    assert main() == EXIT_READ
    assert json.loads(out.getvalue())["files"]["directories"][0]["state"] == "read"


def test_a_stderr_that_fails_is_ignored(monkeypatch):
    assert main(["--bogus"], stdout=Stream(), stderr=Stream(fail=OSError())) == (
        EXIT_USAGE
    )


# A stub container client the test writes; it stands for the runtime's
# client, not for a tool. Run through the real local_run on POSIX.
CLIENT_STUB = """#!{python}
import json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "calls.jsonl"), "a", encoding="utf-8") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
with open(os.path.join(here, "answers.json"), encoding="utf-8") as f:
    answers = json.load(f)
if sys.argv[1:3] == ["image", "inspect"]:
    found = answers["inspect"].get(sys.argv[-1])
    if found is None:
        sys.exit(1)
    sys.stdout.write(json.dumps(found) + "\\n")
    sys.exit(0)
at = sys.argv.index("--entrypoint=")
key = sys.argv[at + 1] + " " + sys.argv[at + 2]
if key in answers["probe"]:
    sys.stdout.write(answers["probe"][key] + "\\n")
    sys.exit(0)
sys.exit(127)
"""


@posix_only
def test_a_stub_client_through_the_real_runner(tmp_path):
    directory = tmp_path / "client"
    directory.mkdir()
    program = directory / "docker"
    program.write_text(CLIENT_STUB.format(python=sys.executable), encoding="utf-8")
    program.chmod(0o755)
    answers = {
        "inspect": {
            "nvcc:12.4": {"Id": _id(1), "RepoTags": ["nvcc:12.4"], "Size": 10},
            "nvcc:13.1": {"Id": _id(2), "RepoTags": ["nvcc:13.1"], "Size": 20},
        },
        "probe": {"nvcc:12.4 nvcc": "release 12.4", "nvcc:13.1 nvcc": "release 13.1"},
    }
    (directory / "answers.json").write_text(json.dumps(answers), encoding="utf-8")
    stdout = Stream()
    status = main(
        ["--image", "nvcc:12.4", "--image", "nvcc:13.1", "--image", "gone:1"],
        stdout=stdout,
        stderr=Stream(),
        environ={},
        components={"nvcc": component("nvcc")},
        client=str(program),
    )
    assert status == EXIT_UNREADABLE
    document = json.loads(stdout.data)
    assert [i["state"] for i in document["images"]["images"]] == [
        "read",
        "read",
        "unreadable",
    ]
    assert [c["tag"] for c in document["images"]["retirement_candidates"]] == [
        "nvcc:12.4"
    ]
    calls = [
        json.loads(line)
        for line in (directory / "calls.jsonl").read_text().splitlines()
    ]
    assert [c[0] for c in calls].count("run") == 2
    assert all(c[0] in ("image", "run") for c in calls)


def test_check_image_is_the_reference_check(monkeypatch):
    seen = []
    monkeypatch.setattr(standin_container, "check_image", seen.append)
    monkeypatch.setattr(local_run, "run", lambda *a, **k: _result(1))
    inspect_image("anything")
    assert seen == ["anything"]
