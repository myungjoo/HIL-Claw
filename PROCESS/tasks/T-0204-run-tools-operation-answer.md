---
id: T-0204
title: Add hilclaw/run_parameters.py and hilclaw/run_operation.py, the timing parameters and the check of an operation's answer of sim.run / board.run (ADR-0065 decisions 2, 4, 6 and 7)
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: [T-0203]
touchesFiles:
  - hilclaw/run_parameters.py
  - hilclaw/run_operation.py
  - tests/test_run_parameters.py
  - tests/test_run_operation.py
estimatedSize: {loc: 260, files: 2}
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts) is open. The run tools `sim.run` / `board.run` now have five records: ADR-0061 (split), ADR-0062 (call identity), ADR-0063 (result members), ADR-0064 (timing seed) and ADR-0065 (the form between the tool function and an operation, and the answer of neither form; landed by T-0203 as `593c186`). Code exists for the objective admission (`hilclaw/run_objective.py`), the step values (`hilclaw/run_identity.py`), the result builder (`hilclaw/run_result.py`), the seed draw (`hilclaw/run_seed.py`) and the judging of a report (`hilclaw/harness/timing.py` `judge_report`).

ADR-0065 Consequences, "Code slice made possible", names the next code slice: **the run tools' check of an operation's answer — form (A), (B) or neither — and its tests**: a function that calls an operation once with the four things, tells (A), (B) and an answer of neither form apart by decision 4, raises a failure of the kind `operation_answer_invalid` with the message of decision 7 for a returned value or a raised error of neither form, and lets a raised request to end pass, as `hilclaw/check_operation.py` is for the check. Names and modules are the code task's. T-0203 Follow-ups and the 2026-10-15 journal name this as the next task.

This task adds that slice as two new modules: `hilclaw/run_parameters.py` (the Python type of the timing parameters of ADR-0065 decision 2, in the manner of `hilclaw/check_parameters.py`) and `hilclaw/run_operation.py` (the call of an operation and the establishment of its answer's form, in the manner of `hilclaw/check_operation.py`). No ADR is needed: every design point is fixed by ADR-0065 or left to the code by it. The module does **not** judge a report (that is `judge_report` and the tool function, later), appends no line and states no spend.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention: branch `claude/T-0204-<slug>`, `Task: T-0204` trailer in commits and as the last line of the PR body, size cap, D12 test rules).
- `CLAUDE.md` sections "상시 규칙" — the test rule (D12 ①-⑤), the language policy (record the language choice and its reason in one line of the commit body), the branch/merge procedure (code mode: Draft PR, review cycle, CI green, self squash-merge, delete branch), the comment-minimisation rule, and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole).
- `ARCHITECTURE/decisions/ADR-0065-od18-run-tools-operation-form.md`: Status, Decision §1 to §8 (lines 22-115; §2 the timing parameters table, §4 the forms (A)/(B) and "How the forms are told apart", §6 and §7 the neither-form answer, its kind, the message rule, "A raised request to end is not answered", §8), the Walk-through (lines 125-143), Limits (lines 145-153), Consequences ("Code slice made possible") and Boundaries.
- `ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md` decisions 1, 5 and 6 (the three ways into the case and the message rule ADR-0065 decision 7 takes).
- `ARCHITECTURE/decisions/ADR-0063-od18-run-tools-result-members.md` decisions 3 and 6 (the seven values of `condition`; `memory_bytes` and its lack of an upper bound).
- `hilclaw/check_operation.py` (whole; the analogue: `ask`, `KIND_OPERATION_ANSWER_INVALID`, `OperationAnswerInvalid`, the message words, how `__cause__` / `__context__` and the frame are kept clean).
- `hilclaw/check_parameters.py` (whole; the analogue of the parameters type).
- `hilclaw/run_result.py` lines 1-80 (`CONDITIONS`, `SAMPLE_FORMS`).
- `hilclaw/run_seed.py` lines 1-70 (how a kind of the run tools' contract is declared and documented beside the check's).
- `hilclaw/tools.py` lines 60-90 (`ToolFailure`).
- `tests/test_check_operation.py` (skim the structure: the case tables, the clean-traceback tests, the import check and the public-names check) and `tests/test_check_parameters.py` (whole).

## Acceptance Criteria

1. **New module `hilclaw/run_parameters.py`** (Python, as the other run tools' modules). Its module docstring cites ADR-0065 decision 2 and, in the manner of `check_parameters.py`, states its own choices and what it does not do. It holds one public type, e.g. `TimingParameters`, a `typing.NamedTuple` with exactly six fields for `m`, `k`, `n`, `n_max`, the sample form and the seed (field names and order are the module's own choice and are stated as such; the record's words are not names of code). It validates nothing (kinds and bounds are checked by whoever uses the value), gives no field a default, and holds nothing else — in particular not the output path, the `bound`, the `objective`, `n_min`, `cv_max` or any setting (ADR-0065 decision 2 "Never handed"). It imports `typing` and nothing else.
2. **New module `hilclaw/run_operation.py`** (Python). Its module docstring cites ADR-0065, says what the module renders (decisions 4, 6 and the part of 7 that needs no log) and what it does not (no line appended, no spend, no judging of a report, no backend selected, no seed drawn, nothing read at the output path, nothing kept between calls; nothing about what the tool function does with a tool failure an operation raises, which is OD-18 ⑲ (나) and bound by ADR-0065 decision 8), and lists every choice that is the module's own. It has:
   - `KIND_OPERATION_ANSWER_INVALID = "operation_answer_invalid"`: the run tools' own kind of ADR-0065 decision 7, not reserved, with the spelling and meaning of `check_operation.KIND_OPERATION_ANSWER_INVALID`. Define it in this module; a test asserts the two are equal.
   - A public tuple of the four (B) strings in the order of ADR-0065 decision 4, taken from or asserted equal to `run_result.CONDITIONS[:4]` (executor's choice; a test asserts the tie).
   - An exception class of this module for the neither-form answer (e.g. `OperationAnswerInvalid`) with `kind` always the constant above and `message` exactly a `str`, holding nothing of the answer. Whether it is this module's own class or `check_operation.OperationAnswerInvalid` reused is the executor's choice; if reused, its docstring's reference to the check's conditions must still be true, and `hilclaw/check_operation.py` must not change. State the choice in the docstring.
   - A public type for an answer of the form (A), e.g. a `NamedTuple` `Reported(report, memory_bytes)`, which is what the function returns for (A); for (B) it returns the condition string itself (or another documented shape of the executor's choice).
   - `ask(operation, request, hw_profile, parameters, output_path)` (name the executor's): `TypeError` before the call when `operation` is not callable or `parameters` is not exactly the timing parameters type. Calls `operation(request, hw_profile, parameters, output_path)` exactly once, with the four objects as they are (ADR-0065 decisions 2 and 3: nothing else, no point, no tool name). Then:
     - returned exactly a `tuple` of length 2 whose first value is exactly `bytes` (any content, empty included — "Every byte string in the first place is a report") and whose second is exactly an `int` (no `bool`, no `int` subclass) of at least 1 with no upper bound, or `None`: form (A), returned as the (A) type. Whether a `tuple` subclass (for example the module's own `NamedTuple`) counts as a pair is the executor's documented choice;
     - returned exactly a `str` equal to one of the four strings: form (B), returned as that string;
     - returned anything else (`None`, a number, `bytes` not in a pair, a pair with a figure of 0, a negative figure, a `bool` or `float` figure, a non-`bytes` first value, a tuple of another length, a list, `"report_form"`, `"replay"`, `"zero_interval"`, any other string, a `str` subclass): the neither-form exception, "returned" case;
     - raised an `Exception` that is no `hilclaw.tools.ToolFailure`: the neither-form exception, "raised" case;
     - raised a `ToolFailure` of any kind: handed on as the same object (the module's own choice; what the tool function does with it is ⑲ (나), bound by ADR-0065 decision 8 — say so);
     - raised a `BaseException` that is no `Exception`: not caught, the same object passes through (ADR-0065 decision 7).
   - Messages (ADR-0065 decision 7, by ADR-0045 decision 6): constants of the module, exactly `str`, built at import; they say the answer had neither form and which of the two ways it was, may name the kind of value or error with a word of the module's own from a closed list matched by exact type (as `check_operation._VALUES` / `_ERRORS`), and carry nothing taken from the answer: no byte of a report, no figure, no text or argument of an error, no type name read from the answer, and nothing of the output path or the seed. Neither `__cause__` nor `__context__` of the raised exception is the operation's error, and the frame of `ask` in its traceback holds neither that error nor the returned value.
   - No argument is modified or kept; no file is read or written; nothing is printed.
3. **New test files `tests/test_run_parameters.py` and `tests/test_run_operation.py`** (D12 ②-④), covering at least:
   - `run_parameters`: the six fields in order, by position and by name; no defaults (missing field → `TypeError`); immutability; equality of equal instances; no validation (odd values accepted); imports and public names exactly as documented.
   - happy: (A) with a report and a figure, with `None`, with an empty report, with a very large figure (> 2**53); (B) with each of the four strings; the operation called exactly once with the four objects as the same objects and nothing more.
   - error/negative: every neither-form value listed in criterion 2 → the exception in the "returned" case; `ValueError`, `TypeError`, `OSError` and an `Exception` subclass of the module's unknown list → the "raised" case; a non-callable operation and wrong parameters type → `TypeError` and the operation is not called.
   - branch: a `ToolFailure` of any kind (including `seed_not_drawn`, `objective_not_stated`) passes as the same object; `KeyboardInterrupt` / `SystemExit` pass as the same object; the "returned" and "raised" messages differ; messages hold no marker byte, figure or error text from the answer and no type name of a custom class (including a class with a hostile metaclass `__name__` / `__repr__`); clean `__cause__` / `__context__` (also when `ask` is called inside an `except` block, only the outer error may appear) and a traceback frame without the answer.
   - `KIND_OPERATION_ANSWER_INVALID == check_operation.KIND_OPERATION_ANSWER_INVALID`, and it is none of `run_objective.KINDS` nor `run_seed.KIND_SEED_NOT_DRAWN`; the four (B) strings equal `run_result.CONDITIONS[:4]`.
   - No file written (`tmp_path` + `monkeypatch.chdir`); the modules' imports are exactly the ones their docstrings name; their public names are exactly the documented ones.
4. `ruff check`, `ruff format --check` and the full `pytest` suite pass locally; the coverage gate of `hilclaw/` (line >= 80%, function >= 80%) holds; CI green on the PR.
5. Size: non-test change <= 300 LOC and <= 5 files (expected about 260 LOC in two non-test files, most of it docstrings). If it is exceeded, split per DRIVER §5 and record the split in Follow-ups.
6. No data-plane schema change: no member of a result, a line of `events.ndjson`, `STATE.json`, `instance.json`, a spec or a result file is added, removed or changed. If the design seems to need one, stop and return BLOCKED.
7. Nothing in this task starts `claude`, builds or runs a kernel, or needs a board or an API key (D16).
8. Code mode per CLAUDE.md A-13: branch `claude/T-0204-run-tools-operation-answer`, Draft PR whose title contains `T-0204` and whose body ends with `Task: T-0204`, fresh-context reviewer cycle (dev-code-review), CI green, `gh pr merge --squash --body <PR body>`, branch deleted. Fill `## Result` with the commit/PR, review rounds, the language line and any follow-ups.

## Out of Scope

- The tool functions of `sim.run` / `board.run`, their registration, the start and end lines, the call order (ADR-0062 decision 6), appending the end line with `operation_answer_invalid` and `end_line_failed` (ADR-0065 decision 7's log half), and the lookup of an ended identity.
- Judging a report (`judge_report`) and building a result (`run_result`) from an answer; using or dropping the figure.
- What the tool function does with a `ToolFailure` an operation raises and which backend kinds may stand on an end line (OD-18 ⑲ (나), ADR-0061 Consequences item (6)), including the guard of ADR-0065 decision 8.
- The operations of `cpu_standin` and of the mock, their scripts (ADR-0061 Consequences item (5)); the spend (OD-2, OD-19).
- Any change to `hilclaw/check_operation.py`, `hilclaw/check_parameters.py`, `hilclaw/run_result.py`, `hilclaw/run_seed.py`, `hilclaw/run_objective.py`, `hilclaw/harness/timing.py`, `hilclaw/tools.py` or any ADR / `ARCHITECTURE/` file; the integrator's "less exact" sentence list of ADR-0065 Consequences.
- Any new dependency.

## Follow-ups

## Result

- **DONE.** PR #139, squash-merged as `8ab70a9`; branch `claude/T-0204-run-tools-operation-answer` deleted.
- **Review:** 1 round (dev-reviewer, Approve; one Info and one Nit, neither asking for a change).
- **CI green:** Python 3.11/3.14, Coverage gate, C, sh, Test presence. Local: ruff check/format clean; pytest 20196 passed, 354 skipped; `hilclaw/` coverage 99%, new modules 100%.
- Added `hilclaw/run_parameters.py` (`TimingParameters`: m, k, n, n_max, sample_form, seed) and `hilclaw/run_operation.py` (`ask`, `Reported`, `CONDITIONS`, `OperationAnswerInvalid`, `KIND_OPERATION_ANSWER_INVALID`), plus `tests/test_run_parameters.py` and `tests/test_run_operation.py`. Non-test change: 288 LOC in 2 files.
- Choices: only an exact tuple counts as a pair, so a tuple subclass (`Reported` included) is neither form; the exception class is this module's own; a `ToolFailure` is handed on as the same object (OD-18 ⑲ (나), bound by ADR-0065 decision 8).
- `CONDITIONS` is spelt in the module rather than imported, because the existing `test_run_result` guard forbids any package module from importing `run_result`; a test ties it to `run_result.CONDITIONS[:4]`.
- Language: Python, the same as the other run-tool modules and `check_operation`.
- No schema change, no new dependency, nothing starts `claude` (D16). Follow-ups: none.
