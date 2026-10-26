import ast
import inspect
import os
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from hilclaw import local_run, standin_profile
from hilclaw.keys import HW_SOURCES, SCHEMA_VERSION, InvalidRecordError, hw_profile_key
from hilclaw.local_run import ProgramNotFoundError, RunResult
from hilclaw.standin_profile import (
    ACCELERATOR,
    REVISION,
    UnreadableFactError,
    local_record,
)

CLANG = "Example clang version 0.0.0 (fictitious-build 1)"
CPU = "Example(R) Fictitious(TM) X-0000 CPU @ 0.00GHz"
EXAMPLE = {
    "schema_version": 1,
    "accelerator": "cpu_standin",
    "revision": "host",
    "toolchain": {"clang": CLANG},
    "host": {"cpu": CPU, "os": "linux exampleos 0.0"},
    "hw_source": "external",
}
EXAMPLE_KEY = "cpu_standin-8c0be275e5925ab0"
CLANG_001_KEY = "cpu_standin-d77e9423bfc2a90c"
VERSION_01_KEY = "cpu_standin-9238984cf1643768"
WSL_KEY = "cpu_standin-d3b1abbab96cb59c"

CPUINFO_PATH = "/proc/cpuinfo"
OS_RELEASE_PATH = "/etc/os-release"
SYSCTL = ("sysctl", "-n", "machdep.cpu.brand_string")
SW_VERS = ("sw_vers", "-productVersion")
LINUX = ("Linux", "0.0.0-0-generic")
WSL = ("Linux", "0.0.0.0-microsoft-standard-WSL2")
DARWIN = ("Darwin", "0.0.0")

CPU_BYTES = CPU.encode("ascii")
CLANG_BYTES = CLANG.encode("ascii")
CPUINFO = (
    b"processor\t: 0\nvendor_id\t: ExampleVendor\nmodel name\t: "
    + CPU_BYTES
    + b"\nflags\t\t: a b c\n\nprocessor\t: 1\nmodel name\t: Another(R) CPU\n"
)
OS_RELEASE = (
    b'NAME="Example OS"\nID=exampleos\nVERSION_ID="0.0"\n'
    b'PRETTY_NAME="Example OS 0.0 (Fictitious)"\n'
)
CLANG_OUTPUT = CLANG_BYTES + b"\nTarget: nowhere-none-none\nThread model: none\n"
TIMEOUT = 60

BAD_TEXT = {
    "letter outside ASCII": b"caf\xc3\xa9",
    "invalid UTF-8": b"abc\xffdef",
    "NUL": b"abc\x00def",
    "form feed": b"abc\x0cdef",
    "vertical tab": b"abc\x0bdef",
    "lone carriage return": b"abc\rdef",
    "next line U+0085": b"abc\xc2\x85def",
    "line separator U+2028": b"abc\xe2\x80\xa8def",
    "file separator": b"abc\x1cdef",
    "DEL": b"abc\x7fdef",
    "escape": b"\x1b[1mabc",
    "256 characters": b"a" * 256,
}
BAD_TIMEOUT_VALUES = [0, -1, -0.5, 0.0, float("nan"), float("inf")]
BAD_TIMEOUT_TYPES = [None, True, False, "10", [1], 1 + 0j]

# ADR-0036 walk-through, copied from the record.
ADR_0036_LINES = [
    (b"0.0", "macos 0.0"),
    (b"\t0.0  ", "macos 0.0"),
    (b"0.0 beta", "macos 0.0 beta"),
    (b"0.0\tbeta", "macos 0.0 beta"),
    (b"0.0 \t beta  1", "macos 0.0 beta 1"),
]


def done(returncode, stdout=b""):
    return RunResult(returncode, returncode is None, stdout, b"", ("x",), 0.0)


class Machine:
    def __init__(self):
        self.kernel = LINUX
        self.files = {CPUINFO_PATH: CPUINFO, OS_RELEASE_PATH: OS_RELEASE}
        self.clang = CLANG_OUTPUT
        self.sysctl = CPU_BYTES + b"\n"
        self.sw_vers = b"0.0\n"
        self.asked = []
        self.timeouts = []

    def read_kernel(self):
        self.asked.append("kernel")
        return self.kernel

    def read(self, path):
        self.asked.append(path)
        content = self.files.get(path, FileNotFoundError(path))
        if isinstance(content, Exception):
            raise content
        return content

    def run(self, command, timeout_s):
        command = tuple(command)
        self.asked.append(command)
        self.timeouts.append(timeout_s)
        outcome = {SYSCTL: self.sysctl, SW_VERS: self.sw_vers}.get(command, self.clang)
        if isinstance(outcome, Exception):
            raise outcome
        return done(0, outcome) if isinstance(outcome, bytes) else outcome

    def set_command(self, name, outcome):
        setattr(self, name, outcome)

    def nothing_stands_in(self):
        allowed = {"kernel", (standin_default(), "--version")}
        if self.kernel[0] == "Linux":
            allowed |= {CPUINFO_PATH, OS_RELEASE_PATH}
        if self.kernel[0] == "Darwin":
            allowed |= {SYSCTL, SW_VERS}
        return set(self.asked) <= allowed and len(self.asked) == len(set(self.asked))


def standin_default():
    return standin_profile.clang_build.DEFAULT_COMPILER


def beside_the_seam(*args, **kwargs):
    raise AssertionError("local_run.run was called beside the seam")


@pytest.fixture
def machine(monkeypatch):
    fake = Machine()
    monkeypatch.setattr(standin_profile, "_kernel", fake.read_kernel)
    monkeypatch.setattr(standin_profile, "_read", fake.read)
    monkeypatch.setattr(standin_profile, "_run", fake.run)
    monkeypatch.setattr(local_run, "run", beside_the_seam)
    return fake


@pytest.fixture
def real_commands(monkeypatch):
    fake = Machine()
    monkeypatch.setattr(standin_profile, "_kernel", fake.read_kernel)
    monkeypatch.setattr(standin_profile, "_read", fake.read)
    return fake


@pytest.fixture
def stub(tmp_path):
    directory = tmp_path / "stub"
    directory.mkdir()

    def make(body):
        script = directory / "cc.py"
        script.write_text("import sys, time\n" + body + "\n", encoding="utf-8")
        return (sys.executable, str(script))

    return make


def example(**host):
    record = dict(EXAMPLE, toolchain=dict(EXAMPLE["toolchain"]))
    record["host"] = dict(EXAMPLE["host"], **host)
    return record


def fails(fake, fact, **arguments):
    fake.asked.clear()
    with pytest.raises(UnreadableFactError) as caught:
        local_record("external", timeout_s=TIMEOUT, **arguments)
    assert str(caught.value).startswith(fact + ": ")
    assert fake.nothing_stands_in()
    return str(caught.value)


def cpuinfo(value):
    return b"processor\t: 0\nmodel name\t: " + value + b"\nflags\t\t: a b\n"


def test_example_machine_gives_the_example_record(machine):
    record = local_record("external", timeout_s=TIMEOUT)
    assert record == EXAMPLE
    assert type(record) is dict
    assert list(record) == [
        "schema_version",
        "accelerator",
        "revision",
        "toolchain",
        "host",
        "hw_source",
    ]
    assert hw_profile_key(record).name == EXAMPLE_KEY
    command = ("clang", "--version")
    assert machine.asked == ["kernel", command, CPUINFO_PATH, OS_RELEASE_PATH]
    assert machine.timeouts == [TIMEOUT]


def test_constants_are_those_of_the_record():
    assert ACCELERATOR == "cpu_standin"
    assert REVISION == "host"
    assert EXAMPLE["schema_version"] == SCHEMA_VERSION
    assert standin_profile._CPUINFO == CPUINFO_PATH
    assert standin_profile._OS_RELEASE == OS_RELEASE_PATH
    assert standin_profile._CPU_COMMAND == SYSCTL
    assert standin_profile._OS_COMMAND == SW_VERS


def test_walk_through_two_spaces_before_cpu_is_the_same_key(machine):
    spaced = CPU_BYTES.replace(b" CPU", b"  CPU")
    machine.files[CPUINFO_PATH] = cpuinfo(spaced)
    record = local_record("external", timeout_s=TIMEOUT)
    assert record == EXAMPLE
    assert hw_profile_key(record).name == EXAMPLE_KEY


def test_walk_through_in_house_is_the_same_key(machine):
    record = local_record("in_house", timeout_s=TIMEOUT)
    assert record == dict(EXAMPLE, hw_source="in_house")
    assert hw_profile_key(record).name == EXAMPLE_KEY


def test_walk_through_clang_upgrade_is_a_new_key(machine):
    line = "Example clang version 0.0.1 (fictitious-build 1)"
    machine.clang = line.encode("ascii") + b"\n"
    record = local_record("external", timeout_s=TIMEOUT)
    assert record == dict(EXAMPLE, toolchain={"clang": line})
    assert hw_profile_key(record).name == CLANG_001_KEY


def test_walk_through_new_version_id_is_a_new_key(machine):
    machine.files[OS_RELEASE_PATH] = OS_RELEASE.replace(b'"0.0"', b'"0.1"')
    record = local_record("external", timeout_s=TIMEOUT)
    assert record == example(os="linux exampleos 0.1")
    assert hw_profile_key(record).name == VERSION_01_KEY


def test_walk_through_wsl_is_a_new_key(machine):
    machine.kernel = WSL
    record = local_record("external", timeout_s=TIMEOUT)
    assert record == example(os="wsl exampleos 0.0")
    assert hw_profile_key(record).name == WSL_KEY
    assert machine.nothing_stands_in()


def test_macos_branch(machine):
    machine.kernel = DARWIN
    record = local_record("external", timeout_s=TIMEOUT)
    assert record == example(os="macos 0.0")
    assert hw_profile_key(record).name.startswith("cpu_standin-")
    assert machine.asked == ["kernel", ("clang", "--version"), SYSCTL, SW_VERS]
    assert machine.timeouts == [TIMEOUT, TIMEOUT, TIMEOUT]


def test_macos_facts_are_spelt_and_later_lines_ignored(machine):
    machine.kernel = DARWIN
    machine.sysctl = (
        b" \tExample(R)  Fictitious(TM)\tX-0000 CPU @ 0.00GHz \r\nmore\xff\n"
    )
    machine.sw_vers = b"\t0.0  \r\nBuild \xff\n"
    assert local_record("external", timeout_s=TIMEOUT) == example(os="macos 0.0")


def test_macos_version_of_several_words_is_kept(machine):
    machine.kernel = DARWIN
    machine.sw_vers = b"0.0 \t beta\n"
    record = local_record("external", timeout_s=TIMEOUT)
    assert record["host"]["os"] == "macos 0.0 beta"


def macos(fake, line):
    fake.kernel = DARWIN
    fake.sw_vers = line + b"\n"
    fake.asked.clear()
    return local_record("external", timeout_s=TIMEOUT)


@pytest.mark.parametrize(("line", "expected"), ADR_0036_LINES)
def test_adr_0036_walk_through_line_gives_its_host_os(machine, line, expected):
    assert macos(machine, line) == example(os=expected)


def test_macos_line_left_with_three_words_gives_a_host_os_of_four(machine):
    record = macos(machine, ADR_0036_LINES[4][0])
    assert record == example(os="macos 0.0 beta 1")
    assert record["host"]["os"].split(" ") == ["macos", "0.0", "beta", "1"]
    assert hw_profile_key(record).name.startswith("cpu_standin-")
    assert machine.asked == ["kernel", ("clang", "--version"), SYSCTL, SW_VERS]


def test_macos_lines_that_differ_in_their_runs_only_give_one_key(machine):
    one_space = macos(machine, ADR_0036_LINES[2][0])
    one_tab = macos(machine, ADR_0036_LINES[3][0])
    three_words = macos(machine, ADR_0036_LINES[4][0])
    assert one_space["host"]["os"] == one_tab["host"]["os"]
    assert hw_profile_key(one_space).name == hw_profile_key(one_tab).name
    assert hw_profile_key(three_words).name != hw_profile_key(one_space).name
    spread = macos(machine, b" \t0.0\t\t beta \t 1 \t")
    assert spread == macos(machine, b"0.0 beta 1") == three_words


@pytest.mark.parametrize(
    "line",
    [
        b"0.0 beta\x0c1",
        b"0.0 beta \x0c 1",
        b"0.0 beta \xff 1",
        b"0.0 be\x7fta 1",
        b"0.0\x0bbeta 1",
        b"0.0 beta\xc2\xa01",
        b"0.0 beta\r1",
        b"0.0 \x00 beta 1",
    ],
)
def test_macos_line_of_several_words_with_a_character_out_of_range(machine, line):
    machine.kernel = DARWIN
    machine.sw_vers = line + b"\n"
    assert "outside 0x20 to 0x7E" in fails(machine, "host.os")


def test_macos_line_of_several_words_is_counted_after_the_spelling(machine):
    spelt = b" ".join([b"v" * 100, b"w" * 100, b"x" * 47])
    assert len(spelt) == 249
    record = macos(machine, spelt)
    assert record == example(os="macos " + spelt.decode("ascii"))
    assert len(record["host"]["os"]) == 255
    assert len(record["host"]["os"].split(" ")) == 4
    assert hw_profile_key(record).name.startswith("cpu_standin-")
    padded = b" \t" * 9 + spelt.replace(b" ", b" \t " * 40) + b"\t " * 9
    assert len(padded) > 249
    assert macos(machine, padded) == record
    longer = b" ".join([b"v" * 100, b"w" * 100, b"x" * 48])
    assert len(longer) == 250
    machine.sw_vers = longer + b"\n"
    assert "longer than 255 characters" in fails(machine, "host.os")
    machine.sw_vers = b"\t" + longer.replace(b" ", b"  ") + b" \n"
    assert "longer than 255 characters" in fails(machine, "host.os")


def test_macos_failures_of_a_line_of_several_words_hold_no_text_of_it(machine):
    machine.kernel = DARWIN
    machine.sw_vers = b"SECRETMARK beta\x0c1\n"
    assert "SECRETMARK" not in fails(machine, "host.os")
    machine.sw_vers = b"SECRETMARK " + b"v" * 250 + b"\n"
    assert "SECRETMARK" not in fails(machine, "host.os")


@pytest.mark.parametrize("word", ["linux", "wsl"])
def test_no_version_id_gives_the_two_word_form(machine, word):
    machine.kernel = WSL if word == "wsl" else LINUX
    machine.files[OS_RELEASE_PATH] = b"NAME=Example\nID=exampleos\nVERSION=rolling\n"
    record = local_record("external", timeout_s=TIMEOUT)
    assert record["host"]["os"] == f"{word} exampleos"
    hw_profile_key(record)


@pytest.mark.parametrize("hw_source", HW_SOURCES)
@pytest.mark.parametrize("kernel", [LINUX, WSL, DARWIN])
def test_record_has_exactly_the_six_members_and_a_key(machine, kernel, hw_source):
    machine.kernel = kernel
    record = local_record(hw_source, timeout_s=TIMEOUT)
    assert set(record) == {
        "schema_version",
        "accelerator",
        "revision",
        "toolchain",
        "host",
        "hw_source",
    }
    assert record["schema_version"] == SCHEMA_VERSION
    assert record["accelerator"] == "cpu_standin"
    assert record["revision"] == "host"
    assert list(record["toolchain"]) == ["clang"]
    assert list(record["host"]) == ["cpu", "os"]
    assert record["hw_source"] == hw_source
    assert hw_profile_key(record).name.startswith("cpu_standin-")


def test_each_call_returns_a_new_record(machine):
    first = local_record("external", timeout_s=TIMEOUT)
    second = local_record("external", timeout_s=TIMEOUT)
    assert first == second
    assert first is not second
    assert first["host"] is not second["host"]
    assert first["toolchain"] is not second["toolchain"]


def test_a_fact_changed_between_two_calls_is_seen(machine):
    assert local_record("external", timeout_s=TIMEOUT) == EXAMPLE
    machine.clang = b"Example clang version 0.0.1 (fictitious-build 1)\n"
    machine.files[CPUINFO_PATH] = cpuinfo(b"Example(R) Other CPU")
    machine.files[OS_RELEASE_PATH] = b"ID=otheros\n"
    machine.kernel = WSL
    record = local_record("external", timeout_s=TIMEOUT)
    assert record["toolchain"] == {
        "clang": "Example clang version 0.0.1 (fictitious-build 1)"
    }
    assert record["host"] == {"cpu": "Example(R) Other CPU", "os": "wsl otheros"}
    assert machine.asked.count(CPUINFO_PATH) == 2
    assert machine.asked.count("kernel") == 2


@pytest.mark.parametrize(
    "release",
    [
        "0.0.0.0-microsoft-standard-WSL2",
        "0.0.0-0-Microsoft",
        "MICROSOFT-0.0",
        "0.0-MiCrOsOfT-x",
        "xmicrosofty",
        "microsoft",
    ],
)
def test_release_with_microsoft_in_any_case_is_wsl(machine, release):
    machine.kernel = ("Linux", release)
    record = local_record("external", timeout_s=TIMEOUT)
    assert record["host"]["os"] == "wsl exampleos 0.0"


@pytest.mark.parametrize(
    "release",
    ["0.0.0-0-generic", "", "0.0-micro-soft", "0.0-msft", "0.0-m\u0131crosoft"],
)
def test_release_without_microsoft_is_linux(machine, release):
    machine.kernel = ("Linux", release)
    record = local_record("external", timeout_s=TIMEOUT)
    assert record["host"]["os"] == "linux exampleos 0.0"


def test_darwin_release_with_microsoft_is_still_macos(machine):
    machine.kernel = ("Darwin", "0.0-microsoft")
    record = local_record("external", timeout_s=TIMEOUT)
    assert record["host"]["os"] == "macos 0.0"


@pytest.mark.parametrize(
    "name",
    ["Windows", "FreeBSD", "linux", "LINUX", "darwin", "", "Linux ", " Linux", "Linu"],
)
def test_kernel_name_without_a_rule(machine, name):
    machine.kernel = (name, "0.0.0-microsoft")
    message = fails(machine, "kernel name")
    assert machine.asked == ["kernel"]
    assert name == "" or name not in message


@pytest.mark.parametrize(
    "content",
    [
        b"model name\t: " + CPU_BYTES + b"\n",
        b"model name: " + CPU_BYTES + b"\n",
        b"model name:" + CPU_BYTES + b"\n",
        b"model name : " + CPU_BYTES + b"\n",
        b"  model name  :   " + CPU_BYTES + b"  \n",
        b"\tmodel name\t:\t" + CPU_BYTES + b"\t\n",
        b" \t model name \t :" + CPU_BYTES + b"\n",
        b"model name\t: " + CPU_BYTES,
        b"model name\t: " + CPU_BYTES + b"\r\n",
        b"processor\t: 0\r\nmodel name\t: " + CPU_BYTES + b"\r\nflags\t: a\r\n",
        b"model name\t: " + CPU_BYTES + b"\nmodel name\t: Another CPU\n",
        b"model name\t: " + CPU_BYTES + b"\nmodel name\t: caf\xc3\xa9\n",
        b"model name\t: " + CPU_BYTES + b"\nmodel name\t:\n",
        b"no colon here\n\nmodel name\nmodel name\t: " + CPU_BYTES + b"\n",
        b"Model name: Wrong\nmodel  name: Wrong\nmodel name x: Wrong\n"
        b"model\tname: Wrong\nmodel name\t: " + CPU_BYTES + b"\n",
        b"other: model name: Wrong\nmodel name\t: " + CPU_BYTES + b"\n",
        b"vendor_id\t: caf\xc3\xa9 \xff\x00\x0c\nmodel name\t: "
        + CPU_BYTES
        + b"\nx: \xff\n",
        b"model name\t: Example(R) \t Fictitious(TM)\tX-0000   CPU\t@ 0.00GHz \t \n",
    ],
)
def test_cpuinfo_forms_that_give_the_example_cpu(machine, content):
    machine.files[CPUINFO_PATH] = content
    assert local_record("external", timeout_s=TIMEOUT) == EXAMPLE


def test_cpuinfo_value_keeps_everything_after_the_first_colon(machine):
    machine.files[CPUINFO_PATH] = b"model name\t: Example: X:0 : CPU\n"
    record = local_record("external", timeout_s=TIMEOUT)
    assert record["host"]["cpu"] == "Example: X:0 : CPU"


def test_cpuinfo_value_is_not_changed_beyond_the_spelling(machine):
    machine.files[CPUINFO_PATH] = b"model name\t: eXAMPLE(r)\t\t(tm) cpu @ 0.00ghz~!\n"
    record = local_record("external", timeout_s=TIMEOUT)
    assert record["host"]["cpu"] == "eXAMPLE(r) (tm) cpu @ 0.00ghz~!"


@pytest.mark.parametrize(
    "content",
    [
        None,
        b"",
        b"\n",
        PermissionError("denied"),
        IsADirectoryError("directory"),
        OSError("input/output error"),
        b"model name\n",
        b"model name " + CPU_BYTES + b"\n",
        b"Model name\t: " + CPU_BYTES + b"\n",
        b"MODEL NAME\t: " + CPU_BYTES + b"\n",
        b"model  name\t: " + CPU_BYTES + b"\n",
        b"model\tname\t: " + CPU_BYTES + b"\n",
        b"model name x\t: " + CPU_BYTES + b"\n",
        b"model_name\t: " + CPU_BYTES + b"\n",
        b"Hardware\t: Example board\nProcessor\t: Example processor\n",
        b"model name\t:\n",
        b"model name\t:",
        b"model name\t: \t \n",
        b"model name\t: " + CPU_BYTES + b"\r",
        b"model name\t:\nmodel name\t: " + CPU_BYTES + b"\n",
        b"model name\t: caf\xc3\xa9\nmodel name\t: " + CPU_BYTES + b"\n",
        *(cpuinfo(text) for text in BAD_TEXT.values()),
    ],
)
def test_cpuinfo_that_cannot_be_read(machine, content):
    if content is None:
        del machine.files[CPUINFO_PATH]
    else:
        machine.files[CPUINFO_PATH] = content
    fails(machine, "host.cpu")
    assert OS_RELEASE_PATH not in machine.asked


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (b"ID=exampleos\nVERSION_ID=0.0\n", "linux exampleos 0.0"),
        (b'ID="exampleos"\nVERSION_ID="0.0"\n', "linux exampleos 0.0"),
        (b"ID='exampleos'\nVERSION_ID='0.0'\n", "linux exampleos 0.0"),
        (b"ID='exampleos'\nVERSION_ID=\"0.0\"\n", "linux exampleos 0.0"),
        (b"VERSION_ID=0.0\nID=exampleos\n", "linux exampleos 0.0"),
        (b'ID=exampleos\r\nVERSION_ID="0.0"\r\n', "linux exampleos 0.0"),
        (b"ID=exampleos\nVERSION_ID=0.0", "linux exampleos 0.0"),
        (b"ID=exampleos", "linux exampleos"),
        (b"ID_LIKE=other\nID=exampleos\n", "linux exampleos"),
        (b'ID_LIKE="a b"\nID=exampleos\nVERSION_ID=0.0\n', "linux exampleos 0.0"),
        (b" ID=wrong\n\tID=wrong\nID=exampleos\n", "linux exampleos"),
        (b"#ID=wrong\nid=wrong\nId=wrong\nID=exampleos\n", "linux exampleos"),
        (
            b"ID=exampleos\nID=second\nVERSION_ID=0.0\nVERSION_ID=9.9\n",
            "linux exampleos 0.0",
        ),
        (b"ID=exampleos\nID=\nVERSION_ID=0.0\nVERSION_ID=a b\n", "linux exampleos 0.0"),
        (
            b"ID=exampleos\n VERSION_ID=9.9\nVERSION_ID_X=9\nVERSION=9\n",
            "linux exampleos",
        ),
        (b"ID=exampleos\nVERSION_CODENAME=none\nBUILD_ID=9\n", "linux exampleos"),
        (
            b'NAME="caf\xc3\xa9 \xff\x00"\nID=exampleos\nVERSION_ID=0.0\n',
            "linux exampleos 0.0",
        ),
        (
            b"ID=example-os_0.x\nVERSION_ID=0.0~rc1+b\n",
            "linux example-os_0.x 0.0~rc1+b",
        ),
        (b"ID=ExampleOS\nVERSION_ID=0.0\n", "linux ExampleOS 0.0"),
        (b"ID=a=b\n", "linux a=b"),
        (b'ID="x\n', 'linux "x'),
        (b'ID=x"\n', 'linux x"'),
        (b'ID=""x""\n', 'linux "x"'),
        (b"ID=''x''\n", "linux 'x'"),
        (b"ID=\"x'\n", "linux \"x'"),
        (b'ID="\n', 'linux "'),
        (b"ID='\n", "linux '"),
        (b'ID=x"y"z\n', 'linux x"y"z'),
    ],
)
def test_os_release_forms(machine, content, expected):
    machine.files[OS_RELEASE_PATH] = content
    record = local_record("external", timeout_s=TIMEOUT)
    assert record == example(os=expected)
    hw_profile_key(record)


@pytest.mark.parametrize(
    "content",
    [
        None,
        b"",
        b"\n\n",
        PermissionError("denied"),
        IsADirectoryError("directory"),
        b"NAME=Example\nVERSION_ID=0.0\n",
        b"ID_LIKE=exampleos\nVERSION_ID=0.0\n",
        b" ID=exampleos\n",
        b"id=exampleos\n",
        b"ID exampleos\n",
        b"ID =exampleos\n",
        b"ID=\n",
        b"ID=",
        b'ID=""\n',
        b"ID=''\n",
        b"ID=example os\n",
        b'ID="example os"\n',
        b"ID=example\tos\n",
        b"ID=exampleos \n",
        b"ID= exampleos\n",
        b'ID=" "\n',
        b"ID=\t\n",
        b"ID=\nID=exampleos\n",
        b"ID=a b\nID=exampleos\n",
        b"ID=exampleos\nVERSION_ID=\n",
        b'ID=exampleos\nVERSION_ID=""\n',
        b"ID=exampleos\nVERSION_ID=''\n",
        b"ID=exampleos\nVERSION_ID=0.0 beta\n",
        b'ID=exampleos\nVERSION_ID="0.0 beta"\n',
        b"ID=exampleos\nVERSION_ID=0.0\tbeta\n",
        b"ID=exampleos\nVERSION_ID=0.0 \n",
        b"ID=exampleos\nVERSION_ID=\nVERSION_ID=0.0\n",
        b"VERSION_ID=\nID=exampleos\n",
        b"ID=exampleos\r",
        b"ID=caf\xc3\xa9\nID=exampleos\n",
        *(b"ID=" + text + b"\nVERSION_ID=0.0\n" for text in BAD_TEXT.values()),
        *(b'ID=exampleos\nVERSION_ID="' + text + b'"\n' for text in BAD_TEXT.values()),
    ],
)
def test_os_release_that_cannot_be_read(machine, content):
    if content is None:
        del machine.files[OS_RELEASE_PATH]
    else:
        machine.files[OS_RELEASE_PATH] = content
    fails(machine, "host.os")


@pytest.mark.parametrize("kernel", [LINUX, WSL])
def test_no_default_stands_in_for_a_missing_id(machine, kernel):
    machine.kernel = kernel
    machine.files[OS_RELEASE_PATH] = (
        b'NAME="Example"\nPRETTY_NAME="Example 0.0"\nID_LIKE=other\nVERSION_ID=0.0\n'
    )
    message = fails(machine, "host.os")
    assert "ID" in message


@pytest.mark.parametrize(
    "output",
    [
        CLANG_BYTES + b"\n",
        CLANG_BYTES + b"\r\n",
        CLANG_BYTES,
        CLANG_BYTES + b"\nTarget: nowhere\n",
        CLANG_BYTES + b"\r\nTarget: nowhere\r\n",
        CLANG_BYTES + b"\n\xff caf\xc3\xa9 \x00\x0c\n",
        CLANG_BYTES + b"\n" + b"a" * 300 + b"\n",
        b"  \t" + CLANG_BYTES + b"\t  \r\n",
        b"Example  clang\tversion \t 0.0.0  (fictitious-build\t1)\n",
    ],
)
def test_clang_outputs_that_give_the_example_line(machine, output):
    machine.clang = output
    assert local_record("external", timeout_s=TIMEOUT) == EXAMPLE


COMMAND_FAILURES = {
    "not found": ProgramNotFoundError("program not found"),
    "cannot be started": PermissionError("denied"),
    "exec format": OSError("exec format error"),
    "status 1 with a valid-looking output": done(1, CLANG_OUTPUT),
    "status 2": done(2, CPU_BYTES + b"\n"),
    "ended by a signal": done(-9, CLANG_OUTPUT),
    "timeout with a valid-looking output": done(None, CLANG_OUTPUT),
    "timeout": done(None),
    "no output": b"",
    "only a line end": b"\n",
    "empty first line followed by text": b"\n" + CLANG_BYTES + b"\n",
    "empty first line with CR LF": b"\r\n" + CLANG_BYTES + b"\r\n",
    "blank first line": b" \t \n" + CLANG_BYTES + b"\n",
    "carriage return without a line feed at the end": CLANG_BYTES + b"\r",
    **{name: text + b"\n" + CLANG_BYTES + b"\n" for name, text in BAD_TEXT.items()},
}


@pytest.mark.parametrize("failure", COMMAND_FAILURES)
def test_clang_line_that_cannot_be_read(machine, failure):
    machine.clang = COMMAND_FAILURES[failure]
    fails(machine, "toolchain.clang")
    assert machine.asked == ["kernel", ("clang", "--version")]


@pytest.mark.parametrize("failure", COMMAND_FAILURES)
@pytest.mark.parametrize(
    ("command", "fact"), [("sysctl", "host.cpu"), ("sw_vers", "host.os")]
)
def test_macos_command_that_cannot_be_read(machine, command, fact, failure):
    machine.kernel = DARWIN
    machine.set_command(command, COMMAND_FAILURES[failure])
    fails(machine, fact)
    assert CPUINFO_PATH not in machine.asked
    assert OS_RELEASE_PATH not in machine.asked


def test_length_limit_is_255_characters_for_every_fact(machine):
    machine.clang = b"c" * 255 + b"\n"
    machine.files[CPUINFO_PATH] = cpuinfo(b"  " + b"p" * 255 + b"\t")
    machine.files[OS_RELEASE_PATH] = b"ID=" + b"i" * 245 + b"\nVERSION_ID=0.0\n"
    record = local_record("external", timeout_s=TIMEOUT)
    assert record["toolchain"]["clang"] == "c" * 255
    assert record["host"]["cpu"] == "p" * 255
    assert record["host"]["os"] == "linux " + "i" * 245 + " 0.0"
    assert len(record["host"]["os"]) == 255
    hw_profile_key(record)


def test_host_os_of_256_characters_is_not_cut(machine):
    machine.files[OS_RELEASE_PATH] = b"ID=" + b"i" * 246 + b"\nVERSION_ID=0.0\n"
    fails(machine, "host.os")


def test_reason_of_a_long_value_outside_ascii_is_the_character(machine):
    machine.clang = b"\xc3\xa9" * 200 + b"\n"
    assert "outside 0x20 to 0x7E" in fails(machine, "toolchain.clang")
    machine.clang = b"c" * 256 + b"\n"
    assert "longer than 255 characters" in fails(machine, "toolchain.clang")


@pytest.mark.parametrize("compiler", [7, 3.5, object()])
def test_compiler_that_cannot_be_iterated(machine, compiler):
    with pytest.raises(TypeError):
        local_record("external", timeout_s=TIMEOUT, compiler=compiler)
    assert machine.asked == []


def test_macos_host_os_length_limit(machine):
    machine.kernel = DARWIN
    machine.sw_vers = b"v" * 249 + b"\n"
    record = local_record("external", timeout_s=TIMEOUT)
    assert record["host"]["os"] == "macos " + "v" * 249
    machine.sw_vers = b"v" * 250 + b"\n"
    fails(machine, "host.os")


def test_messages_hold_no_text_read_from_the_machine(machine):
    marker = b"SECRETMARK"
    machine.clang = marker + b"\x0c\n"
    assert "SECRETMARK" not in fails(machine, "toolchain.clang")
    machine.clang = done(3, marker)
    assert "SECRETMARK" not in fails(machine, "toolchain.clang")
    machine.clang = CLANG_OUTPUT
    machine.files[CPUINFO_PATH] = cpuinfo(marker + b"\xff")
    assert "SECRETMARK" not in fails(machine, "host.cpu")
    machine.files[CPUINFO_PATH] = CPUINFO
    machine.files[OS_RELEASE_PATH] = b"ID=SECRETMARK x\n"
    assert "SECRETMARK" not in fails(machine, "host.os")
    machine.kernel = ("SECRETMARK", "0.0")
    assert "SECRETMARK" not in fails(machine, "kernel name")


@pytest.mark.parametrize(
    ("compiler", "prefix"),
    [
        (None, ("clang",)),
        ("example-clang", ("example-clang",)),
        ("/opt/example/bin/clang", ("/opt/example/bin/clang",)),
        (Path("example") / "clang", (Path("example") / "clang",)),
        (("ccache", "clang"), ("ccache", "clang")),
        (["wrapper", "--", "clang-0"], ("wrapper", "--", "clang-0")),
        (iter(["ccache", "clang"]), ("ccache", "clang")),
    ],
)
def test_compiler_forms(machine, compiler, prefix):
    assert local_record("external", timeout_s=7, compiler=compiler) == EXAMPLE
    assert machine.asked[1] == (*prefix, "--version")
    assert machine.timeouts == [7]


def test_default_compiler_is_that_of_clang_build(machine, monkeypatch):
    monkeypatch.setattr(standin_profile.clang_build, "DEFAULT_COMPILER", "other-cc")
    local_record("external", timeout_s=TIMEOUT)
    assert machine.asked[1] == ("other-cc", "--version")


@pytest.mark.parametrize("compiler", [(), [], iter(())])
def test_empty_compiler_prefix(machine, compiler):
    with pytest.raises(ValueError, match="prefix is empty"):
        local_record("external", timeout_s=TIMEOUT, compiler=compiler)
    assert machine.asked == []


@pytest.mark.parametrize(
    "compiler", [(1,), ("clang", 1), b"clang", (None,), (b"clang",), 3.5, 7]
)
def test_compiler_of_the_wrong_type(real_commands, compiler):
    with pytest.raises(TypeError):
        local_record("external", timeout_s=TIMEOUT, compiler=compiler)
    assert set(real_commands.asked) <= {"kernel"}


class Text(str):
    pass


@pytest.mark.parametrize(
    "hw_source",
    [
        None,
        "",
        "External",
        "EXTERNAL",
        "vendor",
        "external ",
        "in-house",
        "inhouse",
        "cpu_standin",
        True,
        False,
        0,
        1,
        ["external"],
        ("external",),
        {"external"},
        {"external": 1},
        b"external",
        Text("external"),
        HW_SOURCES,
    ],
)
@pytest.mark.parametrize("state", ["example", "unreadable", "no rule"])
def test_hw_source_is_never_derived(machine, state, hw_source):
    if state == "unreadable":
        machine.files.clear()
        machine.clang = ProgramNotFoundError("program not found")
    if state == "no rule":
        machine.kernel = ("Windows", "0")
    with pytest.raises(InvalidRecordError, match="^hw_source: must be external or"):
        local_record(hw_source, timeout_s=TIMEOUT)
    assert machine.asked == []


def test_hw_source_error_is_the_one_of_keys(machine):
    with pytest.raises(InvalidRecordError) as mine:
        local_record("vendor", timeout_s=TIMEOUT)
    with pytest.raises(InvalidRecordError) as theirs:
        hw_profile_key(dict(EXAMPLE, hw_source="vendor"))
    assert str(mine.value) == str(theirs.value)


def test_hw_source_and_timeout_are_required(machine):
    with pytest.raises(TypeError):
        local_record(timeout_s=TIMEOUT)
    with pytest.raises(TypeError):
        local_record("external")
    with pytest.raises(TypeError):
        local_record("external", TIMEOUT)
    with pytest.raises(TypeError):
        local_record("external", timeout_s=TIMEOUT, label="x")
    assert machine.asked == []


def test_signature_carries_no_machine_fact():
    parameters = inspect.signature(local_record).parameters
    assert list(parameters) == ["hw_source", "timeout_s", "compiler"]
    assert parameters["hw_source"].default is inspect.Parameter.empty
    assert parameters["timeout_s"].default is inspect.Parameter.empty
    assert parameters["timeout_s"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["compiler"].default is None
    assert parameters["compiler"].kind is inspect.Parameter.KEYWORD_ONLY


@pytest.mark.parametrize("timeout_s", BAD_TIMEOUT_VALUES)
def test_timeout_that_is_not_positive_and_finite(real_commands, stub, timeout_s):
    compiler = stub("print('never started')")
    with pytest.raises(ValueError, match="timeout_s"):
        local_record("external", timeout_s=timeout_s, compiler=compiler)
    assert set(real_commands.asked) <= {"kernel"}


@pytest.mark.parametrize("timeout_s", BAD_TIMEOUT_TYPES)
def test_timeout_that_is_no_number(real_commands, stub, timeout_s):
    compiler = stub("print('never started')")
    with pytest.raises(TypeError, match="timeout_s"):
        local_record("external", timeout_s=timeout_s, compiler=compiler)
    assert set(real_commands.asked) <= {"kernel"}


def test_bad_hw_source_wins_over_a_bad_timeout(real_commands):
    with pytest.raises(InvalidRecordError):
        local_record("vendor", timeout_s=-1, compiler=())


WRITE_LINE = (
    "sys.stdout.buffer.write(b'  Example clang  version\\t0.0.0 "
    "(fictitious-build 1) \\r\\nTarget: \\xff\\r\\n')"
)


def test_started_compiler_gives_the_example_record(real_commands, stub):
    record = local_record("external", timeout_s=TIMEOUT, compiler=stub(WRITE_LINE))
    assert record == EXAMPLE
    assert hw_profile_key(record).name == EXAMPLE_KEY


def test_started_compiler_gets_only_the_version_argument(real_commands, stub):
    compiler = stub("if sys.argv[1:] != ['--version']: sys.exit(9)\n" + WRITE_LINE)
    assert local_record("external", timeout_s=TIMEOUT, compiler=compiler) == EXAMPLE


def test_started_compiler_with_a_non_zero_status(real_commands, stub):
    compiler = stub(WRITE_LINE + "; sys.exit(1)")
    message = fails(real_commands, "toolchain.clang", compiler=compiler)
    assert "status 1" in message
    assert set(real_commands.asked) <= {"kernel"}


def test_started_compiler_that_writes_only_to_standard_error(real_commands, stub):
    compiler = stub("print('Example clang version 0.0.0', file=sys.stderr)")
    fails(real_commands, "toolchain.clang", compiler=compiler)


def test_started_compiler_that_does_not_finish(real_commands, stub):
    compiler = stub(WRITE_LINE + "; sys.stdout.flush(); time.sleep(30)")
    with pytest.raises(UnreadableFactError, match="^toolchain.clang: .*did not finish"):
        local_record("external", timeout_s=1, compiler=compiler)
    assert set(real_commands.asked) <= {"kernel"}


@pytest.mark.parametrize(
    "compiler",
    [
        "hilclaw-no-such-compiler",
        Path("no-such-directory") / "clang",
        ("hilclaw-no-such-compiler", "clang"),
        "",
    ],
)
def test_compiler_that_is_not_found(real_commands, compiler):
    message = fails(real_commands, "toolchain.clang", compiler=compiler)
    assert "not found" in message
    assert set(real_commands.asked) <= {"kernel"}


def test_a_call_writes_no_file(real_commands, stub, tmp_path, monkeypatch):
    compiler = stub(WRITE_LINE)
    empty = tmp_path / "cwd"
    empty.mkdir()
    monkeypatch.chdir(empty)
    assert local_record("external", timeout_s=TIMEOUT, compiler=compiler) == EXAMPLE
    with pytest.raises(UnreadableFactError):
        local_record("external", timeout_s=TIMEOUT, compiler="hilclaw-no-such-compiler")
    assert list(empty.iterdir()) == []


@pytest.fixture
def real_kernel(monkeypatch):
    fake = Machine()
    monkeypatch.setattr(standin_profile, "_read", fake.read)
    monkeypatch.setattr(standin_profile, "_run", fake.run)
    return fake


@pytest.mark.parametrize(
    ("sysname", "release", "expected"),
    [
        ("Linux", "0.0.0-0-generic", "linux exampleos 0.0"),
        ("Linux", "0.0.0-Microsoft", "wsl exampleos 0.0"),
        ("Darwin", "0.0.0", "macos 0.0"),
    ],
)
def test_kernel_name_and_release_come_from_os_uname(
    real_kernel, monkeypatch, sysname, release, expected
):
    calls = []

    def uname():
        calls.append(1)
        return SimpleNamespace(
            sysname=sysname, release=release, nodename="n", version="v", machine="m"
        )

    monkeypatch.setattr(os, "uname", uname, raising=False)
    first = local_record("external", timeout_s=TIMEOUT)
    assert first == example(os=expected)
    local_record("external", timeout_s=TIMEOUT)
    assert len(calls) == 2


def test_platform_without_os_uname_has_no_kernel_name(real_kernel, monkeypatch):
    monkeypatch.delattr(os, "uname", raising=False)
    with pytest.raises(UnreadableFactError, match="^kernel name: "):
        local_record("external", timeout_s=TIMEOUT)
    assert real_kernel.asked == []


@pytest.fixture
def real_files(monkeypatch, tmp_path):
    fake = Machine()
    monkeypatch.setattr(standin_profile, "_kernel", fake.read_kernel)
    monkeypatch.setattr(standin_profile, "_run", fake.run)
    monkeypatch.setattr(standin_profile, "_CPUINFO", str(tmp_path / "cpuinfo"))
    monkeypatch.setattr(standin_profile, "_OS_RELEASE", str(tmp_path / "os-release"))
    (tmp_path / "cpuinfo").write_bytes(CPUINFO.replace(b"\n", b"\r\n"))
    (tmp_path / "os-release").write_bytes(OS_RELEASE + b"X=caf\xc3\xa9 \xff\r\n")
    return tmp_path


def test_files_are_read_as_bytes(real_files):
    assert local_record("external", timeout_s=TIMEOUT) == EXAMPLE
    (real_files / "os-release").write_bytes(b'ID=exampleos\nVERSION_ID="0.1"\n')
    record = local_record("external", timeout_s=TIMEOUT)
    assert record["host"]["os"] == "linux exampleos 0.1"
    assert sorted(path.name for path in real_files.iterdir()) == [
        "cpuinfo",
        "os-release",
    ]


@pytest.mark.parametrize(
    ("name", "fact"), [("cpuinfo", "host.cpu"), ("os-release", "host.os")]
)
@pytest.mark.parametrize("state", ["missing", "directory", "empty"])
def test_file_that_is_missing_a_directory_or_empty(real_files, name, fact, state):
    path = real_files / name
    path.unlink()
    if state == "directory":
        path.mkdir()
    if state == "empty":
        path.write_bytes(b"")
    with pytest.raises(UnreadableFactError, match=f"^{fact}: "):
        local_record("external", timeout_s=TIMEOUT)


def imported_modules(path):
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        if isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            found.add(module)
            found |= {f"{module}.{alias.name}" for alias in node.names}
    return found


def test_module_is_bound_by_the_start_only_and_imports_no_store():
    package = Path(standin_profile.__file__).parent
    own = Path(standin_profile.__file__)
    assert imported_modules(own) == {
        "os",
        "re",
        "reprlib",
        "hilclaw",
        "hilclaw.clang_build",
        "hilclaw.keys",
        "hilclaw.local_run",
    }
    start = package / "start_instance.py"
    assert "standin_profile" in start.read_text(encoding="utf-8")
    table = (package / "check_definition.py").read_text(encoding="utf-8")
    assert "standin_profile.ACCELERATOR" in table
    assert "local_record" not in table
    for path in sorted(package.rglob("*.py")):
        if path not in (own, start, package / "check_definition.py"):
            assert "standin_profile" not in path.read_text(encoding="utf-8"), path.name
    assert not hasattr(standin_profile, "main")
    assert "__main__" not in own.read_text(encoding="utf-8")


def test_public_names_of_the_module():
    public = {
        name
        for name, value in vars(standin_profile).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {"ACCELERATOR", "REVISION", "UnreadableFactError", "local_record"}
    assert issubclass(UnreadableFactError, Exception)
    assert not issubclass(UnreadableFactError, (InvalidRecordError, OSError))


def test_live_record_of_this_machine_has_the_shapes_of_the_record():
    if sys.platform != "linux":
        pytest.skip("the live case runs on Linux only")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    try:
        record = local_record("external", timeout_s=TIMEOUT)
    except UnreadableFactError as error:
        pytest.fail(str(error), pytrace=False)
    try:
        hw_profile_key(record)
        accepted = True
    except InvalidRecordError:
        accepted = False
    shapes = {
        "hw_profile_key accepts the record": accepted,
        "exactly the six members": sorted(record) == sorted(EXAMPLE),
        "revision is host": record["revision"] == "host",
        "accelerator is cpu_standin": record["accelerator"] == "cpu_standin",
        "toolchain has the one member clang": list(record["toolchain"]) == ["clang"],
        "host has cpu and os": sorted(record["host"]) == ["cpu", "os"],
        "host.os starts with linux or wsl": record["host"]["os"].split(" ")[0]
        in ("linux", "wsl"),
        "host.os has two or three words": len(record["host"]["os"].split(" "))
        in (2, 3),
        "hw_source is the caller's": record["hw_source"] == "external",
    }
    broken = sorted(name for name, holds in shapes.items() if not holds)
    assert not broken
