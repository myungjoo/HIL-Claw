"""The command line the owner runs for P2-15 (ADR-0192; HQ-0084 (4), HQ-0071).

Command line: ``python -m hilclaw.model_check <file>``. The one argument is the
path of a JSON file, decoded under the rules of :mod:`hilclaw.new_run`; no
option exists and nothing is read from standard input. A person runs it; it is
no FR-10 tool, has no registry entry and no MCP name, and starts no ``claude``.
A coder's kernel runs only through :mod:`hilclaw.model_forward_container`.

**The document's members**, all required but ``parent``, none with a default
(HQ-0071; ADR-0176 decision 6): ``model_directory``; ``runs``, an object from
each of the fifteen call sites to a run id; ``flags``, the build settings of
those runs (ADR-0189 decision 6); ``prompt``, the text; ``n``, the number of
greedy tokens; ``rtol`` and ``atol``; ``build_timeout_s`` and ``run_timeout_s``
(ADR-0182 decision 5); ``program_flags`` and ``program_trailing_flags``
(:mod:`hilclaw.model_build`); and ``parent``, the directory the build directory
is made in. An unknown or missing member is ``refused_document``.

**One check**, stopping at the first failure so that a long step is not spent on
a doomed call: the document; the optional packages; ``model_files.read``; the
tokenizer; the data root (``data_root_source.configured``, as ``new_run``);
``binding_from_runs``; :func:`hilclaw.model_forward_container.execute` in the
generation mode with G = ``n``, ``lm_head_rows`` ``"all"`` and ``keep_out``
naming the model directory and the data root; the reference; the comparison.

**The verdict** (owner, HQ-0071): ``match`` only when
:func:`hilclaw.model_reference.compare` passes every row and the executor's
``n`` tokens equal the reference's.

**What the owner is told**, through the process only. Standard output gets one
line, a compact JSON object in ASCII ended by one LF, whose member ``outcome``
names the kind:

=========================  ======  ==========================================
``outcome``                status  further members
=========================  ======  ==========================================
``match``                  0       the verdict's members, below
``no_match``               10      the verdict's members, below
``refused_document``       11      ``reason``
``missing_package``        12      ``package``, ``reason``
``model_file``             13      ``reason``, ``detail``
``tokenizer_failed``       14      ``reason``
``empty_prompt``           15      none
``no_data_root``           16      ``reason``
``run_binding``            17      ``reason``, ``call_site``, ``run_id``
``binding_check``          18      ``outcomes``: ``kind``, ``call_site``, ``reason``
``bad_usage``              20      ``reason``
``unreadable_input``       21      ``reason``
``bad_input``              22      ``reason``
``refused_parent``         23      ``reason``
``fault``                  24      ``fault``: the class name of the exception
``container_unavailable``  30      ``reason``, ``removed``
``build_failed``           31      ``kernel``, ``returncode``, ``timed_out``, ``log``, ``removed``
``run_failed``             32      ``failed``, ``returncode``, ``stderr``, ``removed``
``copy_failed``            33      ``reason``
``file_system``            34      ``reason``
``reference_failed``       35      ``reason``, ``detail``
=========================  ======  ==========================================

For ``model_file`` ``reason`` is a constant of :mod:`hilclaw.model_files`; for
``run_binding`` one of :data:`hilclaw.model_run_binding.REASONS`; for
``reference_failed`` one of :data:`hilclaw.model_hf_reference.REASONS`; for
``container_unavailable`` one of :data:`hilclaw.model_forward_container.REASONS`;
for ``copy_failed`` one of :data:`hilclaw.standin_copies.COPY_FAILURES`. Elsewhere
``reason`` and ``detail`` are free text. ``removed`` is whether the build
directory is gone.

The verdict's members: ``prompt_tokens``, ``executor_tokens`` and
``reference_tokens``, lists of ``int``; ``prompt_text``, ``executor_text`` and
``reference_text``, decoded with special tokens kept; ``first_differing_token``,
the index among the ``n`` tokens or ``null``; ``logits``, the fields of
:class:`hilclaw.model_reference.LogitComparison`; and ``removed``.

Standard error gets nothing for a kind, with two exceptions as in ``new_run``: a
process without a standard output, and a line that cannot be written, are said
there with the status 24. :class:`KeyboardInterrupt` and :class:`SystemExit` are
not caught.

**The record** (ADR-0192 decision 7): the answer goes to standard output only.
No file of the data plane, CAS or the checkout is written, and the model
directory is only read. The one directory made is the executor's build directory.
"""

import contextlib
import sys

from hilclaw import (
    data_root_source,
    model_files,
    model_forward_container,
    model_forward_run,
    model_hf_reference,
    model_reference,
    model_run_binding,
    standin_copies,
    tools,
)
from hilclaw.attempt_kernel import _check_flags
from hilclaw.model_execute import _checked_keep_out, _checked_parent
from hilclaw.model_reference import _tolerance
from hilclaw.model_run_binding import _check_runs
from hilclaw.new_run import _described, _parsed, _standard, _told
from hilclaw.standin_container import _check_limit

EXIT_STATUS = {
    "match": 0,
    "no_match": 10,
    "refused_document": 11,
    "missing_package": 12,
    "model_file": 13,
    "tokenizer_failed": 14,
    "empty_prompt": 15,
    "no_data_root": 16,
    "run_binding": 17,
    "binding_check": 18,
    "bad_usage": 20,
    "unreadable_input": 21,
    "bad_input": 22,
    "refused_parent": 23,
    "fault": 24,
    "container_unavailable": 30,
    "build_failed": 31,
    "run_failed": 32,
    "copy_failed": 33,
    "file_system": 34,
    "reference_failed": 35,
}

_REQUIRED = frozenset(
    [
        "model_directory",
        "runs",
        "flags",
        "prompt",
        "n",
        "rtol",
        "atol",
        "build_timeout_s",
        "run_timeout_s",
        "program_flags",
        "program_trailing_flags",
    ]
)
_OPTIONAL = frozenset(("parent",))


class _Stop(Exception):
    def __init__(self, told):
        super().__init__()
        self.told = told


def _text(value):
    if type(value) is not str:
        raise TypeError(f"must be a string, got {type(value).__name__}")


def _positive_int(value):
    if type(value) is not int or value < 1:
        raise ValueError(f"must be a positive integer, got {value!r}")


def _all_call_sites(runs):
    _check_runs(runs)
    missing = [site for site in model_forward_run.CALL_SITES if site not in runs]
    if missing:
        raise ValueError(f"names no run for the call sites {missing}")


def _document_refusal(document):
    names = set(document)
    if names - _REQUIRED - _OPTIONAL:
        return f"unknown members: {sorted(names - _REQUIRED - _OPTIONAL)}"
    if _REQUIRED - names:
        return f"missing members: {sorted(_REQUIRED - names)}"
    checks = {
        "model_directory": _text,
        "runs": _all_call_sites,
        "flags": _check_flags,
        "prompt": _text,
        "n": _positive_int,
        "rtol": lambda value: _tolerance("rtol", value),
        "atol": lambda value: _tolerance("atol", value),
        "build_timeout_s": lambda value: _check_limit(value, "build_timeout_s"),
        "run_timeout_s": lambda value: _check_limit(value, "run_timeout_s"),
        "program_flags": _check_flags,
        "program_trailing_flags": _check_flags,
        "parent": _text,
    }
    for name, check in checks.items():
        if name not in document:
            continue
        try:
            check(document[name])
        except (TypeError, ValueError) as error:
            return f"{name}: {_described(error)}"
    return None


def _prompt_tokens(directory, text):
    tokenizer = model_hf_reference.read_tokenizer(directory)
    tokens = tokenizer.encode(text)
    if not tokens:
        raise _Stop({"outcome": "empty_prompt"})
    return tokenizer, tokens


def _keep_out(document, root):
    keep_out = (document["model_directory"], str(root))
    try:
        _checked_parent(document.get("parent"), _checked_keep_out(keep_out))
    except (TypeError, ValueError) as error:
        raise _Stop(_told("refused_parent", _described(error))) from error
    return keep_out


def _executed(document, files, binding, prompt, keep_out):
    return model_forward_container.execute(
        files.dimensions,
        binding,
        eps=files.eps,
        rope=files.rope,
        weights=files.weights,
        prompt=prompt,
        given=None,
        generation_length=document["n"],
        lm_head_rows="all",
        build_timeout_s=document["build_timeout_s"],
        run_timeout_s=document["run_timeout_s"],
        program_flags=document["program_flags"],
        program_trailing_flags=document["program_trailing_flags"],
        parent=document.get("parent"),
        keep_out=keep_out,
    )


def _report_of(execution):
    if not execution.check.ok:
        raise _Stop(
            {
                "outcome": "binding_check",
                "outcomes": [
                    {
                        "kind": outcome.kind,
                        "call_site": outcome.call_site,
                        "reason": outcome.reason,
                    }
                    for outcome in execution.check.outcomes
                ],
            }
        )
    removed = {"removed": execution.removed}
    if execution.unavailable is not None:
        reason = execution.unavailable.reason
        raise _Stop({"outcome": "container_unavailable", "reason": reason, **removed})
    if execution.build_failed is not None:
        build = execution.build_failed.build
        raise _Stop(
            {
                "outcome": "build_failed",
                "kernel": execution.build_failed.kernel,
                "returncode": build.returncode,
                "timed_out": build.timed_out,
                "log": build.log,
                **removed,
            }
        )
    if execution.run.failed is not None:
        container = execution.run.container
        raise _Stop(
            {
                "outcome": "run_failed",
                "failed": execution.run.failed.name.lower(),
                "returncode": container.returncode,
                "stderr": container.stderr.decode("utf-8", "replace"),
                **removed,
            }
        )
    return execution.run.report


def _first_difference(ours, theirs):
    for index, (mine, other) in enumerate(zip(ours, theirs, strict=True)):
        if mine != other:
            return index
    return None


def _verdict(tokenizer, prompt, selected, greedy, comparison, removed):
    differing = _first_difference(selected, greedy)
    return {
        "outcome": "match" if comparison.ok and differing is None else "no_match",
        "prompt_tokens": prompt,
        "executor_tokens": selected,
        "reference_tokens": list(greedy),
        "prompt_text": tokenizer.decode(prompt),
        "executor_text": tokenizer.decode(selected),
        "reference_text": tokenizer.decode(greedy),
        "first_differing_token": differing,
        "logits": comparison._asdict(),
        "removed": removed,
    }


def _checked(document, source):
    directory = document["model_directory"]
    model_hf_reference.check_packages()
    files = model_files.read(directory)
    tokenizer, prompt = _prompt_tokens(directory, document["prompt"])
    root = data_root_source.obtain(source)
    keep_out = _keep_out(document, root)
    binding = model_run_binding.binding_from_runs(
        root, document["runs"], flags=document["flags"]
    )
    execution = _executed(document, files, binding, prompt, keep_out)
    report = _report_of(execution)
    vocabulary = files.dimensions.vocabulary
    # The reference loads its own float64 copy; the bf16 arrays are not kept beside it.
    del files
    selected = [int(token) for token in report.tokens[len(prompt) :]]
    outputs = model_hf_reference.reference_outputs(
        directory, prompt, selected, vocabulary=vocabulary
    )
    comparison = model_reference.compare(
        report, outputs.logits, rtol=document["rtol"], atol=document["atol"]
    )
    return _verdict(
        tokenizer, prompt, selected, outputs.greedy, comparison, execution.removed
    )


def _reference_failure(error):
    if error.reason == model_hf_reference.MISSING_PACKAGE:
        return {
            "outcome": "missing_package",
            "package": error.package,
            "reason": str(error),
        }
    if error.reason == model_hf_reference.TOKENIZER_FAILED:
        return _told("tokenizer_failed", str(error))
    return {"outcome": "reference_failed", "reason": error.reason, "detail": str(error)}


def _answer(args, source):
    if len(args) != 1:
        return _told(
            "bad_usage", f"usage: expected one file, got {len(args)} arguments"
        )
    document, refused = _parsed(args[0])
    if refused is not None:
        return refused
    refusal = _document_refusal(document)
    if refusal is not None:
        return _told("refused_document", refusal)
    try:
        return _checked(document, source)
    except _Stop as stop:
        return stop.told
    except model_hf_reference.HfReferenceError as error:
        return _reference_failure(error)
    except model_files.ModelFileError as error:
        return {"outcome": "model_file", "reason": error.reason, "detail": str(error)}
    except tools.ToolFailure as error:
        return _told("no_data_root", error.message)
    except model_run_binding.RunBindingError as error:
        return {
            "outcome": "run_binding",
            "reason": error.reason,
            "call_site": error.call_site,
            "run_id": error.run_id,
        }
    except standin_copies.CopyError as error:
        return _told("copy_failed", error.failure)
    except OSError as error:
        return _told("file_system", _described(error))
    except Exception as error:  # noqa: BLE001
        return {"outcome": "fault", "fault": type(error).__name__}


def _say(stderr, text):
    with contextlib.suppress(Exception):
        if stderr is not None:
            line = f"hilclaw.model_check: {text}".replace("\r", " ").replace("\n", " ")
            stderr.write((line + "\n").encode("utf-8", "backslashreplace"))
            stderr.flush()


def main(argv=None, *, source=data_root_source.configured, stdout=None, stderr=None):
    """Run the check of the file named by the one argument; return the exit status.

    ``argv`` defaults to ``sys.argv[1:]``. ``source`` is the data-root source
    (:mod:`hilclaw.data_root_source`), asked once. ``stdout`` and ``stderr`` are
    binary streams and default to the standard ones. Returns the status of the
    module docstring's table; no :class:`Exception` leaves the call.
    """
    args = sys.argv[1:] if argv is None else list(argv)
    stdout = _standard("stdout") if stdout is None else stdout
    stderr = _standard("stderr") if stderr is None else stderr
    if stdout is None:
        _say(stderr, "fault: there is no standard output; nothing was checked")
        return EXIT_STATUS["fault"]
    told = _answer(args, source)
    try:
        line = tools.encode(told)
        if stdout.write(line) != len(line):
            raise OSError("it took a part of the line")
        stdout.flush()
    except Exception as error:  # noqa: BLE001
        text = f"cannot write standard output after {told['outcome']}: "
        _say(stderr, text + _described(error))
        return EXIT_STATUS["fault"]
    return EXIT_STATUS[told["outcome"]]


if __name__ == "__main__":
    raise SystemExit(main())
