import contextlib
import subprocess
import sys
import types
from types import SimpleNamespace

import numpy as np
import pytest

from hilclaw import model_hf_reference
from hilclaw.model_hf_reference import (
    LOAD_FAILED,
    MISSING_PACKAGE,
    NAN_ROW,
    PASS_FAILED,
    REASONS,
    TOKENIZER_FAILED,
    WRONG_DTYPE,
    WRONG_SHAPE,
    HfReferenceError,
    ReferenceOutputs,
    Tokenizer,
    check_packages,
    read_tokenizer,
    reference_outputs,
)

DIRECTORY = "some/model"
V = 4
LOADING = {
    "dtype": "float64",
    "attn_implementation": "eager",
    "use_safetensors": True,
    "local_files_only": True,
    "trust_remote_code": False,
}


class FakeTensor:
    def __init__(self, array, dtype="float64"):
        self.array = array
        self.dtype = dtype

    def detach(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return self.array


class FakeBackend:
    def __init__(self, vocabulary=V):
        self.vocabulary = vocabulary

    def encode(self, text, *, add_special_tokens):
        assert add_special_tokens is True
        return [ord(character) % self.vocabulary for character in text]

    def decode(self, tokens, *, skip_special_tokens):
        assert skip_special_tokens is False
        assert type(tokens) is list
        return " ".join(str(token) for token in tokens)


class Packages:
    """Fake ``torch`` and ``transformers``; ``rows`` gives float64 rows for a token list."""

    def __init__(self, rows):
        self.rows = rows
        self.loads = []
        self.tokenizer_loads = []
        self.passes = []
        self.evaluated = False
        self.dtype = "float64"
        self.load_error = None
        self.tokenizer_error = None
        self.backend = FakeBackend()
        self.torch = types.ModuleType("torch")
        self.torch.float64 = "float64"
        self.torch.long = "long"
        self.torch.no_grad = contextlib.nullcontext
        self.torch.tensor = self.tensor
        self.transformers = types.ModuleType("transformers")
        self.transformers.LlamaForCausalLM = SimpleNamespace(from_pretrained=self.load)
        self.transformers.PreTrainedTokenizerFast = SimpleNamespace(
            from_pretrained=self.load_tokenizer
        )

    def tensor(self, data, dtype):
        assert dtype == "long"
        return np.array(data)

    def load(self, directory, **arguments):
        self.loads.append((directory, arguments))
        if self.load_error is not None:
            raise self.load_error
        return self

    def load_tokenizer(self, directory, **arguments):
        self.tokenizer_loads.append((directory, arguments))
        if self.tokenizer_error is not None:
            raise self.tokenizer_error
        return self.backend

    def eval(self):
        self.evaluated = True

    def __call__(self, *, input_ids, use_cache):
        assert use_cache is False
        tokens = input_ids[0].tolist()
        self.passes.append(tokens)
        return SimpleNamespace(
            logits=FakeTensor(np.asarray(self.rows(tokens))[np.newaxis], self.dtype)
        )


def install(monkeypatch, packages):
    monkeypatch.setitem(sys.modules, "torch", packages.torch)
    monkeypatch.setitem(sys.modules, "transformers", packages.transformers)
    return packages


def rows_by_length(tokens):
    """The largest value of each row sits at (position + last token + 1) mod V."""
    rows = np.zeros((len(tokens), V), dtype=np.float64)
    for position, token in enumerate(tokens):
        rows[position, (position + token + 1) % V] = 1.0
    return rows


@pytest.fixture
def packages(monkeypatch):
    return install(monkeypatch, Packages(rows_by_length))


def refused(reason, *arguments, **options):
    with pytest.raises(HfReferenceError) as caught:
        reference_outputs(DIRECTORY, *arguments, vocabulary=V, **options)
    assert caught.value.reason == reason
    assert reason in REASONS
    return caught.value


def test_importing_the_module_needs_neither_package():
    code = (
        "import sys\n"
        "sys.modules['torch'] = None\n"
        "sys.modules['transformers'] = None\n"
        "import hilclaw.model_hf_reference\n"
    )
    done = subprocess.run([sys.executable, "-c", code], check=False)
    assert done.returncode == 0


def test_the_loading_arguments_are_those_of_the_record(packages):
    reference_outputs(DIRECTORY, [1], [2], vocabulary=V)
    assert packages.loads == [(DIRECTORY, LOADING)]
    assert packages.evaluated


def test_the_tokenizer_reads_only_the_directory_and_adds_special_tokens(packages):
    tokenizer = read_tokenizer(DIRECTORY)
    assert packages.tokenizer_loads == [
        (DIRECTORY, {"local_files_only": True, "trust_remote_code": False})
    ]
    assert type(tokenizer) is Tokenizer
    assert tokenizer.encode("\x01\x02") == [1, 2]
    assert tokenizer.decode((1, 2)) == "1 2"


def test_teacher_forcing_feeds_the_prompt_and_all_selected_tokens_but_the_last(
    packages,
):
    outputs = reference_outputs(DIRECTORY, [1, 2], [3, 0, 1], vocabulary=V)
    assert type(outputs) is ReferenceOutputs
    assert packages.passes[0] == [1, 2, 3, 0]
    assert outputs.logits.dtype == np.float64
    assert np.array_equal(outputs.logits, rows_by_length([1, 2, 3, 0]))


def test_greedy_starts_from_the_prompt_alone_and_never_reads_the_selected_tokens(
    packages,
):
    outputs = reference_outputs(DIRECTORY, [1, 2], [3, 3, 3], vocabulary=V)
    tokens = [1, 2]
    for _ in range(3):
        last = rows_by_length(tokens)[-1]
        tokens.append(int(np.flatnonzero(last == last.max())[0]))
    assert outputs.greedy == tuple(tokens[2:])
    assert all(type(token) is int for token in outputs.greedy)
    assert packages.passes[1:] == [[1, 2], [1, 2, tokens[2]], [1, 2, *tokens[2:4]]]


def test_a_tie_goes_to_the_smallest_token_id(monkeypatch):
    def rows(tokens):
        made = np.zeros((len(tokens), V))
        made[-1] = [-1.0, 5.0, -0.0, 5.0]
        return made

    install(monkeypatch, Packages(rows))
    assert reference_outputs(DIRECTORY, [0], [0, 0], vocabulary=V).greedy == (1, 1)


def test_negative_and_signed_zero_rows_follow_values(monkeypatch):
    def rows(tokens):
        made = np.zeros((len(tokens), V))
        made[-1] = [-0.0, 0.0, -1.0, -2.0]
        return made

    install(monkeypatch, Packages(rows))
    assert reference_outputs(DIRECTORY, [0], [0], vocabulary=V).greedy == (0,)


def test_one_token_makes_two_passes_and_no_row_past_the_prompt(packages):
    outputs = reference_outputs(DIRECTORY, [1], [2], vocabulary=V)
    assert packages.passes == [[1], [1]]
    assert outputs.logits.shape == (1, V)
    assert len(outputs.greedy) == 1


def test_the_arrays_do_not_share_memory_with_the_model(monkeypatch):
    held = np.ones((1, V))
    install(monkeypatch, Packages(lambda tokens: held))
    outputs = reference_outputs(DIRECTORY, [1], [2], vocabulary=V)
    assert not np.shares_memory(outputs.logits, held)


@pytest.mark.parametrize("name", model_hf_reference.PACKAGES)
@pytest.mark.parametrize(
    "act",
    [
        check_packages,
        lambda: read_tokenizer(DIRECTORY),
        lambda: reference_outputs(DIRECTORY, [1], [2], vocabulary=V),
    ],
)
def test_an_absent_package_is_named(monkeypatch, packages, name, act):
    monkeypatch.setitem(sys.modules, name, None)
    with pytest.raises(HfReferenceError) as caught:
        act()
    assert caught.value.reason == MISSING_PACKAGE
    assert caught.value.package == name
    assert name in str(caught.value)


def test_a_package_that_cannot_load_its_library_is_named(monkeypatch):
    def fails(name):
        raise OSError("a library is missing")

    monkeypatch.setattr(model_hf_reference.importlib, "import_module", fails)
    with pytest.raises(HfReferenceError) as caught:
        check_packages()
    assert caught.value.package == "torch"


def test_check_packages_returns_nothing_when_both_exist(packages):
    assert check_packages() is None


def test_a_failed_load_is_named(packages):
    packages.load_error = OSError("no such file")
    assert refused(LOAD_FAILED, [1], [2]).__cause__ is packages.load_error


def test_a_failed_pass_is_named(monkeypatch):
    def rows(tokens):
        raise RuntimeError("out of memory")

    install(monkeypatch, Packages(rows))
    refused(PASS_FAILED, [1], [2])


@pytest.mark.parametrize(
    "shape", [(2, V), (1, V), (1, V + 1), (V,)], ids=["rows", "row", "wide", "flat"]
)
def test_a_wrong_shape_is_named(monkeypatch, shape):
    install(monkeypatch, Packages(lambda tokens: np.zeros(shape)))
    refused(WRONG_SHAPE, [1, 2], [3, 0])


def test_logits_of_a_narrower_type_are_named(packages):
    packages.dtype = "float32"
    refused(WRONG_DTYPE, [1], [2])


def test_a_nan_in_a_row_the_rule_reads_is_named(monkeypatch):
    def rows(tokens):
        made = np.zeros((len(tokens), V))
        made[-1, 2] = np.nan
        return made

    install(monkeypatch, Packages(rows))
    refused(NAN_ROW, [1], [2])


@pytest.mark.parametrize(("prompt", "selected"), [([], [1]), ([1], [])])
def test_an_empty_sequence_is_refused_before_anything_is_loaded(
    packages, prompt, selected
):
    with pytest.raises(ValueError):
        reference_outputs(DIRECTORY, prompt, selected, vocabulary=V)
    assert packages.loads == []


def test_a_failed_tokenizer_read_is_named(packages):
    packages.tokenizer_error = ValueError("no tokenizer.json")
    with pytest.raises(HfReferenceError) as caught:
        read_tokenizer(DIRECTORY)
    assert caught.value.reason == TOKENIZER_FAILED


@pytest.mark.parametrize(
    "act", [lambda t: t.encode("x"), lambda t: t.decode([1])], ids=["encode", "decode"]
)
def test_a_failed_encoding_or_decoding_is_named(act):
    backend = SimpleNamespace(encode=None, decode=None)
    with pytest.raises(HfReferenceError) as caught:
        act(Tokenizer(backend))
    assert caught.value.reason == TOKENIZER_FAILED


def test_every_reason_is_distinct():
    assert len(set(REASONS)) == len(REASONS)
    assert ReferenceOutputs._fields == ("logits", "greedy")
