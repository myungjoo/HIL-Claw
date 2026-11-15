import pytest

from hilclaw import cuda_image, standin_image
from hilclaw.cuda_image import ENV_IMAGE, ImageRefusedError, read_image

DIGEST = "nvidia/cuda@sha256:" + "0123456789abcdef" * 4


def test_variable_name():
    assert ENV_IMAGE == "HILCLAW_CUDA_IMAGE"
    assert ENV_IMAGE != standin_image.ENV_IMAGE


@pytest.mark.parametrize("value", ["cuda:13.1.2", DIGEST, "Registry:5000/Cu-Da:V1"])
def test_value_returned_unchanged(value):
    environ = {ENV_IMAGE: value, standin_image.ENV_IMAGE: "-x"}
    assert read_image(environ) == value


def test_default_reads_os_environ(monkeypatch):
    monkeypatch.setenv(ENV_IMAGE, "cuda:13.1.2")
    assert read_image() == "cuda:13.1.2"
    assert read_image(None) == "cuda:13.1.2"


def test_default_unset(monkeypatch):
    monkeypatch.delenv(ENV_IMAGE, raising=False)
    assert read_image() is None


@pytest.mark.parametrize(
    "environ",
    [{}, {ENV_IMAGE: ""}, {standin_image.ENV_IMAGE: "cuda:13.1.2"}],
)
def test_not_named(environ):
    assert read_image(environ) is None


@pytest.mark.parametrize(
    "value",
    [
        "--gpus",
        "-cuda:13.1.2",
        "cuda: 13.1.2",
        "cuda:13.1.2 ",
        " cuda",
        "cuda:\t13",
        "cuda:13.1.2\n",
        "cuda\0:13",
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


@pytest.mark.parametrize("value", [3, b"cuda:13.1.2", ["cuda"]])
def test_a_value_that_is_not_str_names_only_its_type(value):
    with pytest.raises(TypeError) as raised:
        read_image({ENV_IMAGE: value})
    assert type(value).__name__ in str(raised.value)
    assert repr(value) not in str(raised.value)


@pytest.mark.parametrize("environ", [[(ENV_IMAGE, "cuda:1")], "x", 3])
def test_a_non_mapping_environ_is_refused(environ):
    with pytest.raises(TypeError):
        read_image(environ)


def test_the_module_names_no_image():
    texts = [
        value
        for name, value in vars(cuda_image).items()
        if not name.startswith("__") and isinstance(value, str)
    ]
    assert all("cuda:" not in text and "nvidia/" not in text for text in texts)
