import os
from pathlib import Path

import pytest

from hilclaw import checkout_boundary
from hilclaw.checkout_boundary import (
    PACKAGE_DIRECTORY,
    meets_checkout,
    refuse_one_path,
    within,
)

WINDOWS_ONLY = pytest.mark.skipif(os.name != "nt", reason="drive letters")


@pytest.fixture
def data(tmp_path):
    directory = tmp_path / "outer" / "data"
    (directory / "inner").mkdir(parents=True)
    return directory


def link_or_skip(link, target):
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"cannot make a symbolic link: {error}")


# --- PACKAGE_DIRECTORY ---


def test_the_package_directory_holds_this_package():
    holder = Path(PACKAGE_DIRECTORY)
    assert holder.is_absolute()
    assert (holder / "hilclaw" / "checkout_boundary.py").is_file()


# --- refuse_one_path ---


@pytest.mark.parametrize("keep_out", ["data", b"data", Path("data")])
def test_one_path_as_keep_out_is_refused(keep_out):
    with pytest.raises(TypeError) as caught:
        refuse_one_path(keep_out)
    assert str(caught.value) == "keep_out must be a sequence of paths, not one path"


@pytest.mark.parametrize("keep_out", [(), [], ["data"], ("a", "b"), iter(["a"])])
def test_a_sequence_of_paths_as_keep_out_is_accepted(keep_out):
    assert refuse_one_path(keep_out) is None


# --- within ---


@pytest.mark.parametrize(
    ("inner", "outer", "expected"),
    [
        (os.path.join("a", "data"), os.path.join("a", "data"), True),
        (os.path.join("a", "data", "x"), os.path.join("a", "data"), True),
        (os.path.join("a", "data"), os.path.join("a", "data", "x"), False),
        (os.path.join("a", "data2"), os.path.join("a", "data"), False),
        (os.path.join("a", "data"), os.path.join("a", "data2"), False),
        (os.path.join("a", "other"), os.path.join("a", "data"), False),
    ],
)
def test_within_compares_whole_components(inner, outer, expected):
    assert within(inner, outer) is expected


def test_paths_on_different_drives_are_not_within_each_other(monkeypatch):
    def fail(paths):
        raise ValueError("different drives")

    monkeypatch.setattr(checkout_boundary.os.path, "commonpath", fail)
    assert within("a", "b") is False


@WINDOWS_ONLY
def test_paths_on_two_real_drives_are_not_within_each_other():
    assert within("c:\\data", "d:\\data") is False
    assert within("c:\\data", "d:\\") is False


def test_an_absolute_and_a_relative_path_are_not_within_each_other():
    assert within(os.path.abspath("data"), "data") is False


# --- meets_checkout ---


def test_a_path_beside_every_root_meets_no_checkout(tmp_path, data):
    beside = tmp_path / "beside"
    beside.mkdir()
    roots = [str(data), str(tmp_path / "other")]
    assert meets_checkout(str(beside), roots, containing=False) is False
    assert meets_checkout(str(beside), roots, containing=True) is False


@pytest.mark.parametrize("containing", [False, True])
@pytest.mark.parametrize("where", ["equal", "inside", "absent below"])
def test_a_path_that_is_or_lies_inside_a_root_meets_it(data, where, containing):
    path = {
        "equal": data,
        "inside": data / "inner",
        "absent below": data / "absent" / "deeper",
    }[where]
    assert meets_checkout(str(path), [str(data)], containing=containing) is True


def test_a_path_containing_a_root_meets_it_only_when_containing_counts(data):
    outer = str(data.parent)
    assert meets_checkout(outer, [str(data)], containing=True) is True
    assert meets_checkout(outer, [str(data)], containing=False) is False


@pytest.mark.parametrize(
    "path",
    [
        PACKAGE_DIRECTORY,
        os.path.join(PACKAGE_DIRECTORY, "hilclaw"),
        os.path.join(PACKAGE_DIRECTORY, "absent"),
    ],
)
def test_the_package_directory_is_always_a_root(path):
    assert meets_checkout(path, [], containing=False) is True


def test_a_path_containing_the_package_directory():
    above = os.path.dirname(PACKAGE_DIRECTORY)
    assert meets_checkout(above, [], containing=True) is True
    assert meets_checkout(above, [], containing=False) is False


def test_a_root_that_is_the_file_system_root_holds_every_path(tmp_path):
    top = os.path.abspath(os.sep)
    assert meets_checkout(str(tmp_path), [top], containing=False) is True


def test_a_common_name_prefix_is_not_containment(tmp_path):
    data = tmp_path / "data"
    data2 = tmp_path / "data2"
    data.mkdir()
    data2.mkdir()
    assert meets_checkout(str(data2), [str(data)], containing=True) is False
    assert meets_checkout(str(data), [str(data2)], containing=True) is False


@pytest.mark.skipif(
    os.path.normcase("Aa") == "Aa", reason="normcase does not fold case here"
)
def test_a_path_that_differs_in_case_only_meets_the_root(data):
    path = str(data / "inner").swapcase()
    assert meets_checkout(path, [str(data)], containing=False) is True


@pytest.mark.skipif(os.path.normcase("Aa") != "Aa", reason="normcase folds case here")
def test_a_path_that_differs_in_case_only_is_not_recognised_without_folding(
    tmp_path,
):
    data = tmp_path / "data"
    data.mkdir()
    assert (
        meets_checkout(str(tmp_path / "DATA"), [str(data)], containing=False) is False
    )


def test_paths_on_different_drives_meet_no_checkout(monkeypatch, data):
    def fail(paths):
        raise ValueError("different drives")

    monkeypatch.setattr(checkout_boundary.os.path, "commonpath", fail)
    assert meets_checkout(str(data), [str(data)], containing=True) is False


@WINDOWS_ONLY
def test_a_path_on_another_drive_meets_no_checkout(data):
    drive = os.path.splitdrive(str(data))[0].lower()
    other = "z:" if drive != "z:" else "y:"
    assert meets_checkout(other + "\\data", [str(data)], containing=True) is False


def test_a_link_that_resolves_into_a_root_meets_it(tmp_path, data):
    link = tmp_path / "link"
    link_or_skip(link, data / "inner")
    assert meets_checkout(str(link), [str(data)], containing=False) is True


def test_a_root_given_as_a_link_is_compared_by_its_target(tmp_path, data):
    link = tmp_path / "link"
    link_or_skip(link, data)
    assert meets_checkout(str(data / "inner"), [str(link)], containing=False) is True


def test_roots_are_read_only_up_to_the_first_checkout_met(data):
    read = []

    def roots():
        for root in (str(data), "never read"):
            read.append(root)
            yield root

    assert meets_checkout(str(data), roots(), containing=False) is True
    assert read == [str(data)]


def test_a_path_inside_the_package_directory_stops_before_any_root_is_read():
    def roots():
        raise AssertionError("read")
        yield

    path = os.path.join(PACKAGE_DIRECTORY, "hilclaw")
    assert meets_checkout(path, roots(), containing=False) is True
