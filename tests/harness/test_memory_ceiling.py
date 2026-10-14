import pytest

from hilclaw.harness import memory_ceiling
from hilclaw.harness.memory_ceiling import (
    BOUND_MAX,
    MemoryCeilingError,
    Verdict,
    figure,
    verdict,
)


class Count(int):
    pass


class Word(str):
    pass


PLATFORMS_WITHOUT_RULE = [
    "win32",
    "cygwin",
    "msys",
    "freebsd13",
    "openbsd7",
    "sunos5",
    "aix",
    "emscripten",
    "wasi",
    "linux2",
    "Linux",
    "LINUX",
    " linux",
    "darwin ",
    "Darwin",
    "",
    Word("linux"),
    None,
    b"linux",
    ["linux"],
    {"linux": 1},
]
NOT_A_FIGURE = [None, 0, -1, -1024, True, False, 1.0, 5.0, "5", b"5", [5], Count(5)]
BAD_BOUNDS = [-1, -(2**53), 2**53, 2**64, True, False, 1.0, None, "1", [1], Count(1)]
BAD_FIGURES = [0, -1, True, False, 1.0, "1", b"1", [1], Count(1)]


def test_linux_value_is_in_kibibytes():
    assert figure(5, "linux") == 5120
    assert figure(1, "linux") == 1024
    assert figure(2**53, "linux") == 2**63


def test_darwin_value_is_in_bytes():
    assert figure(5, "darwin") == 5
    assert figure(1, "darwin") == 1
    assert figure(123456789, "darwin") == 123456789


@pytest.mark.parametrize("platform", ["linux", "darwin"])
def test_figure_is_exactly_an_int(platform):
    assert type(figure(7, platform)) is int


@pytest.mark.parametrize("platform", PLATFORMS_WITHOUT_RULE, ids=repr)
def test_no_rule_no_figure(platform):
    assert figure(5, platform) is None


@pytest.mark.parametrize("platform", ["linux", "darwin"])
@pytest.mark.parametrize("max_rss", NOT_A_FIGURE, ids=repr)
def test_a_value_that_is_no_positive_int_gives_no_figure(max_rss, platform):
    assert figure(max_rss, platform) is None


def test_figure_needs_the_platform():
    with pytest.raises(TypeError):
        figure(5)


def test_equality_is_within():
    assert verdict(5120, 5120) is Verdict.WITHIN
    assert verdict(1, 1) is Verdict.WITHIN
    assert verdict(BOUND_MAX, BOUND_MAX) is Verdict.WITHIN


def test_below_the_bound_is_within():
    assert verdict(1, 2) is Verdict.WITHIN
    assert verdict(4096, BOUND_MAX) is Verdict.WITHIN


def test_one_byte_over_is_over():
    assert verdict(5121, 5120) is Verdict.OVER
    assert verdict(BOUND_MAX + 1, BOUND_MAX) is Verdict.OVER
    assert verdict(10**5000, BOUND_MAX) is Verdict.OVER


def test_a_bound_of_zero():
    assert verdict(1, 0) is Verdict.OVER
    assert verdict(None, 0) is Verdict.NOT_JUDGED


@pytest.mark.parametrize("bound", [0, 1, 5120, BOUND_MAX])
def test_no_figure_is_not_judged(bound):
    assert verdict(None, bound) is Verdict.NOT_JUDGED
    assert verdict(None, bound) is not Verdict.WITHIN


def test_the_largest_bound_is_accepted():
    assert BOUND_MAX == 2**53 - 1
    assert verdict(None, BOUND_MAX) is Verdict.NOT_JUDGED
    assert verdict(None, BOUND_MAX) is not Verdict.WITHIN


def test_a_figure_through_the_verdict():
    assert verdict(figure(5, "linux"), 5120) is Verdict.WITHIN
    assert verdict(figure(5, "linux"), 5119) is Verdict.OVER
    assert verdict(figure(5, "win32"), BOUND_MAX) is Verdict.NOT_JUDGED
    assert verdict(figure(0, "linux"), BOUND_MAX) is Verdict.NOT_JUDGED


def test_verdict_has_exactly_three_outcomes():
    assert [outcome.name for outcome in Verdict] == ["WITHIN", "OVER", "NOT_JUDGED"]
    assert len(set(Verdict)) == 3


@pytest.mark.parametrize("figure_bytes", [None, 1, 5120])
@pytest.mark.parametrize("bound", BAD_BOUNDS, ids=repr)
def test_a_bound_outside_its_domain_raises(bound, figure_bytes):
    with pytest.raises(MemoryCeilingError, match="^bound: must be "):
        verdict(figure_bytes, bound)


@pytest.mark.parametrize("bound", [0, 1, BOUND_MAX])
@pytest.mark.parametrize("figure_bytes", BAD_FIGURES, ids=repr)
def test_a_figure_outside_its_domain_raises(figure_bytes, bound):
    with pytest.raises(MemoryCeilingError, match="^figure_bytes: must be "):
        verdict(figure_bytes, bound)


def test_the_error_is_a_value_error_and_names_the_value():
    assert issubclass(MemoryCeilingError, ValueError)
    with pytest.raises(MemoryCeilingError, match="got bool True$"):
        verdict(1, True)
    with pytest.raises(MemoryCeilingError, match="got float 1.0$"):
        verdict(1.0, 5)
    with pytest.raises(MemoryCeilingError, match="got int of 16610 bits$"):
        verdict(1, 10**5000)


def test_verdict_needs_both_values():
    with pytest.raises(TypeError):
        verdict(None)


def test_the_module_reads_no_platform(monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    assert figure(5, "linux") == 5120
    monkeypatch.setattr("sys.platform", "linux")
    assert figure(5, "win32") is None
    assert "sys" not in vars(memory_ceiling)
