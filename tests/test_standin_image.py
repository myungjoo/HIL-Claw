import pytest

from hilclaw import standin_container, standin_image
from hilclaw.standin_container import check_image
from hilclaw.standin_image import ENV_IMAGE, ImageRefusedError, read_image

DIGEST = "example/standin@sha256:" + "0123456789abcdef" * 4


def test_variable_name():
    assert ENV_IMAGE == "HILCLAW_STANDIN_IMAGE"


@pytest.mark.parametrize(
    "value",
    ["example/standin:1", DIGEST, "Registry.Example:5000/Std-In:V1"],
)
def test_value_returned_unchanged(value):
    assert read_image({ENV_IMAGE: value, "OTHER": "-x"}) == value


def test_default_reads_os_environ(monkeypatch):
    monkeypatch.setenv(ENV_IMAGE, "example/standin:2")
    assert read_image() == "example/standin:2"
    assert read_image(None) == "example/standin:2"


def test_default_unset(monkeypatch):
    monkeypatch.delenv(ENV_IMAGE, raising=False)
    assert read_image() is None


@pytest.mark.parametrize("environ", [{}, {ENV_IMAGE: ""}, {"OTHER": "image:1"}])
def test_not_named(environ):
    assert read_image(environ) is None


@pytest.mark.parametrize(
    "value",
    [
        "--privileged",
        "-example/standin:1",
        "example/ standin:1",
        "example/standin:1 ",
        " example/standin:1",
        "example/\tstandin:1",
        "example/standin:1\n",
        "example/\0standin:1",
        " example",
    ],
)
def test_refused_without_quoting(value):
    with pytest.raises(ImageRefusedError) as raised:
        read_image({ENV_IMAGE: value})
    assert isinstance(raised.value, ValueError)
    text = str(raised.value)
    assert ENV_IMAGE in text
    assert value.strip() not in text
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None


def test_refusal_text_is_fixed():
    texts = {
        str(_refusal(value)) for value in ("--privileged", "a b", "a\0b", "-secret")
    }
    assert len(texts) == 1


def _refusal(value):
    with pytest.raises(ImageRefusedError) as raised:
        read_image({ENV_IMAGE: value})
    return raised.value


@pytest.mark.parametrize("environ", [["HILCLAW_STANDIN_IMAGE"], "x", 3, object()])
def test_environ_not_a_mapping(environ):
    with pytest.raises(TypeError, match="mapping"):
        read_image(environ)


@pytest.mark.parametrize("value", [b"example/standin:1", 7, ["a"]])
def test_value_not_str(value):
    with pytest.raises(TypeError) as raised:
        read_image({ENV_IMAGE: value})
    assert not isinstance(raised.value, ImageRefusedError)


def test_uses_the_shared_check(monkeypatch):
    seen = []
    monkeypatch.setattr(standin_container, "check_image", seen.append)
    assert read_image({ENV_IMAGE: "--anything"}) == "--anything"
    assert seen == ["--anything"]
    assert standin_image.standin_container is standin_container


@pytest.mark.parametrize("value", ["example/standin:1", DIGEST, "a"])
def test_check_image_passes(value):
    assert check_image(value) is None


@pytest.mark.parametrize(
    ("value", "kind"),
    [
        (None, TypeError),
        (b"image", TypeError),
        ("", ValueError),
        ("-image", ValueError),
        ("--privileged", ValueError),
        ("a b", ValueError),
        ("a\tb", ValueError),
        ("a\nb", ValueError),
        ("a\0b", ValueError),
    ],
)
def test_check_image_refuses(value, kind):
    with pytest.raises(kind):
        check_image(value)
