"""The Hugging Face transformers reference of the P2-15 check (ADR-0192).

``ARCHITECTURE/decisions/ADR-0192-od31-model-check-command.md`` is the rule; a
decision cited by its number alone is one of that record. ``transformers`` and
``torch`` are optional packages of the runtime machine (HQ-0084 (3), HQ-0071):
they are imported only inside a call, so importing this module never needs
them, and no ``torch`` object leaves it.

**Loading** (decision 2): only from the named directory, offline, from
safetensors, with no remote code, at ``torch.float64`` and with the ``eager``
attention implementation.

**Greedy** (decision 5, the owner's rule of HQ-0071): an explicit loop of one
whole pass per token, with no cache. The next token is the first index of the
largest value of the last row, so the smallest token id on ties. There is no
sampling, repetition penalty or stop at an end token, as in the forward program.

What this module does not do: it writes nothing, compares nothing, holds no
tolerance, prompt or length, and is registered as no tool.
"""

import importlib
from typing import NamedTuple

import numpy as np

MISSING_PACKAGE = "missing_package"
TOKENIZER_FAILED = "tokenizer_failed"
LOAD_FAILED = "load_failed"
PASS_FAILED = "pass_failed"
WRONG_DTYPE = "wrong_dtype"
WRONG_SHAPE = "wrong_shape"
NAN_ROW = "nan_row"
REASONS = (
    MISSING_PACKAGE,
    TOKENIZER_FAILED,
    LOAD_FAILED,
    PASS_FAILED,
    WRONG_DTYPE,
    WRONG_SHAPE,
    NAN_ROW,
)
"""Every ``reason`` of :class:`HfReferenceError`."""

PACKAGES = ("torch", "transformers")
"""The optional packages, in the order they are looked for."""


class HfReferenceError(Exception):
    """A failure of the reference; ``reason`` is one of :data:`REASONS`, ``package`` the missing package's name or ``None``."""

    def __init__(self, reason, message, package=None):
        super().__init__(f"{reason}: {message}")
        self.reason = reason
        self.package = package


class ReferenceOutputs(NamedTuple):
    """What :func:`reference_outputs` returns.

    ``logits`` is a ``numpy.float64`` array of shape (S + G - 1, V), in the
    order of a :class:`hilclaw.model_forward_run.ForwardReport` at
    ``lm_head_rows`` ``"all"``. ``greedy`` is a ``tuple`` of G ``int`` token ids.
    """

    logits: np.ndarray
    greedy: tuple


class Tokenizer:
    """The directory's tokenizer: text to token ids and back, as plain Python values."""

    def __init__(self, backend):
        self._backend = backend

    def encode(self, text):
        """Return the ``list`` of ``int`` ids of ``text``, special tokens added by the directory's rule (decision 4)."""
        try:
            return [
                int(token)
                for token in self._backend.encode(text, add_special_tokens=True)
            ]
        except Exception as error:
            raise HfReferenceError(TOKENIZER_FAILED, _named(error)) from error

    def decode(self, tokens):
        """Return the text of a sequence of ``int`` ids, special tokens kept."""
        try:
            return str(self._backend.decode(list(tokens), skip_special_tokens=False))
        except Exception as error:
            raise HfReferenceError(TOKENIZER_FAILED, _named(error)) from error


def check_packages():
    """Import both optional packages; raise :class:`HfReferenceError` naming the first that is missing."""
    _packages()


def read_tokenizer(directory):
    """Return the :class:`Tokenizer` of a model directory on this machine.

    Raises :class:`HfReferenceError`: :data:`MISSING_PACKAGE` or
    :data:`TOKENIZER_FAILED`, for anything the reading raises.
    """
    _, transformers = _packages()
    try:
        return Tokenizer(
            transformers.PreTrainedTokenizerFast.from_pretrained(
                directory, local_files_only=True, trust_remote_code=False
            )
        )
    except Exception as error:
        raise HfReferenceError(TOKENIZER_FAILED, _named(error)) from error


def reference_outputs(directory, prompt, selected, *, vocabulary):
    """Load the model once and return its :class:`ReferenceOutputs`.

    ``prompt`` and ``selected`` are non-empty sequences of ``int`` token ids, S
    and G of them; ``selected`` holds the tokens the executor chose, and all but
    the last are fed after the prompt for the teacher-forced ``logits`` (ADR-0176
    decision 5). ``greedy`` starts from the prompt alone and reads nothing of
    ``selected`` but its length. ``vocabulary`` is V, each row's length.

    Raises :class:`ValueError` for an empty ``prompt`` or ``selected``, and
    :class:`HfReferenceError` for a missing package (:data:`MISSING_PACKAGE`), a
    failed load (:data:`LOAD_FAILED`), a failed pass (:data:`PASS_FAILED`),
    logits that are not ``torch.float64`` (:data:`WRONG_DTYPE`) or not of the
    expected shape (:data:`WRONG_SHAPE`), and a NaN in a row the greedy rule reads
    (:data:`NAN_ROW`), since the rule is defined over values (ADR-0176 decision 5).
    """
    if not prompt or not selected:
        raise ValueError("prompt and selected must each hold a token")
    torch, transformers = _packages()
    try:
        model = transformers.LlamaForCausalLM.from_pretrained(
            directory,
            dtype=torch.float64,
            attn_implementation="eager",
            use_safetensors=True,
            local_files_only=True,
            trust_remote_code=False,
        )
        model.eval()
    except Exception as error:
        raise HfReferenceError(LOAD_FAILED, _named(error)) from error
    fed = [*prompt, *selected[:-1]]
    logits = _rows(torch, model, fed, vocabulary)
    greedy = _greedy(torch, model, prompt, len(selected), vocabulary)
    return ReferenceOutputs(logits, greedy)


def _packages():
    found = []
    for name in PACKAGES:
        try:
            found.append(importlib.import_module(name))
        except (ImportError, OSError) as error:
            raise HfReferenceError(
                MISSING_PACKAGE,
                f"the optional package {name} cannot be imported: {_named(error)}",
                package=name,
            ) from error
    return found


def _rows(torch, model, tokens, vocabulary):
    try:
        with torch.no_grad():
            logits = model(
                input_ids=torch.tensor([tokens], dtype=torch.long), use_cache=False
            ).logits
        dtype = logits.dtype
        array = logits.detach().cpu().numpy()
    except Exception as error:
        raise HfReferenceError(PASS_FAILED, _named(error)) from error
    if dtype != torch.float64:
        raise HfReferenceError(WRONG_DTYPE, f"logits of {dtype}, not float64")
    expected = (1, len(tokens), vocabulary)
    if array.shape != expected:
        raise HfReferenceError(WRONG_SHAPE, f"logits {array.shape}, not {expected}")
    return np.array(array[0], dtype=np.float64)


def _greedy(torch, model, prompt, count, vocabulary):
    tokens = list(prompt)
    for _ in range(count):
        row = _rows(torch, model, tokens, vocabulary)[-1]
        if np.isnan(row).any():
            raise HfReferenceError(NAN_ROW, f"in the row before token {len(tokens)}")
        tokens.append(int(np.argmax(row)))
    return tuple(tokens[len(prompt) :])


def _named(error):
    return f"{type(error).__name__}: {error}"
