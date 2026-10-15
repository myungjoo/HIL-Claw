---
id: T-0200
title: Carry the member table of ADR-0063 decision 9 into the code as one new pure module `hilclaw/run_result.py` - two functions that build the result object of a call of `sim.run` / `board.run` (a completed run from its outcome, intervals, resolution and figure; a broken run from its condition), with the `ceiling` verdict or not_stated and the `bound`, exactly the ten members and their presence rules, refusing what the table does not admit - with its tests; bound to no tool
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, NFR-2, OD-18, OD-13]
dependsOn: [T-0199]
touchesFiles: [hilclaw/run_result.py, tests/test_run_result.py]
estimatedSize: {loc: 240, files: 1}   # non-test: one new module, about 80-100 code lines plus docstrings; tests/test_run_result.py is excluded from the cap (D4)
hq: []   # implements a landed record (ADR-0063 decisions 1 to 9); closes no OD, writes no ADR, no new dependency, no data-plane file. Independent of HQ-0013, HQ-0014, HQ-0016..HQ-0019 (runtime-acceptance): a new module and a new test file only
---
## Why
PLAN P1-1 (the FR-10 tool contracts, the mock backend, the conformance tests) is open. For `sim.run` and `board.run`, ADR-0063 (T-0199, landed as `582cc5a`) fixed the members of a result and closed the member list (its decision 9): "A result has the members of the table below and no other." Its Consequences name the code slice that is possible now:

> *Possible now*: a function of the package that builds the result object of either run tool from the outcome or condition, the intervals and resolution, the figure or its absence, the verdict or that no ceiling is stated, the dimensions, `n_max`, the sample form and the `bound`, refusing what the table does not admit - as `hilclaw/check_result.py` is for the check - with its tests.

**This task adds exactly that, and nothing more**: a pure builder from plain values, carried into the package ahead of the tool functions, so that the later tool functions, the mock's script and the conformance tests of P1-1 share one rendering of the table. It is the same kind of slice as T-0130 (`hilclaw/check_result.py` for ADR-0042). **No tool function, no registration, no mapping from `Judgement` / `Broken` / `TimingResult`, no reader of `instance.json`.** The task ticks **no PLAN checkbox**: P1-1 stays open.

Planner's judgements (from the files at `main` `acea825`, 2026-10-15; **the reviewer is asked to re-check each**):
- **Selectable without the repository owner (DRIVER §9).** Every member name, type, value and presence rule is ADR-0063 decisions 2 to 7 and 9; "this record binds no code" (ADR-0063 Consequences). The task decides only the module and function names, parameters, what a refused argument raises, the member order of the returned `dict` and docstring texts. Nothing of #5 A/B items, C-6, OD-25 or OD-3 is needed.
- **Plain values, not the harness's types.** The form of what crosses the cut is open (ADR-0063 decision 10; ADR-0061 Consequences item (4)). A builder that takes the result's own strings decides nothing of it; the mapping from `Broken` / `State` / `Verdict` is the tool function's later task. The `ceiling` derivation (below) is the one place where ADR-0052 decision 5's rule is applied.
- **Two kinds of integer in the table.** `shape.m/k/n`, `n_max` and `bound` are *integers* of ADR-0001 (0 to 2^53 - 1, with the table's lower bounds). `resolution_ns`, the entries of `intervals_ns` and `memory_bytes` are "JSON integers ... no upper bound" and "not *integers* of ADR-0001" (ADR-0063 decision 4). The module must keep this distinction.
- **No `memory_ceiling` is admitted by this task.** `bound` other than `None` describes results after a later admission (ADR-0063 decision 7, "What every result carries today"); the builder accepts it because the table admits it, but `hilclaw/instance.py` still refuses every constraint entry (check 4 of ADR-0050 is unchanged) and this task touches neither that nor `hilclaw/run_objective.py`. Condition (c) of ADR-0052 decision 7 is **not** met by this task: no tool function returns `ceiling` after it. No docstring may say otherwise.
- **New module name.** `run_result` occurs nowhere in `hilclaw/` or `tests/` (searched 2026-10-15). Two existing tests scan every file under `hilclaw/`: `tests/test_gemm_contract.py::test_module_is_bound_nowhere_and_imports_keys_only` refuses the string `gemm_contract` and `tests/test_standin_profile.py::test_module_is_bound_nowhere_and_imports_no_store` the string `standin_profile`; the new module contains neither.
- **A-13 reading**: code mode. No new external dependency (`pyproject.toml` unchanged). "데이터 plane 스키마 변경" does not apply: no data-plane file is read or written and the members are those ADR-0063 landed with its own A-13 reading (ADR-0063 Consequences, "A-13 reading"). A reviewer result starting with `SECURITY` is BLOCKED.
- **Why this item now**: no lock, no TODO / INTERRUPTED task file, no open PR. T-0199's Follow-ups name this as the first candidate; the second (the timing seed, OD-13 sub-question 7) is a document task that can follow.

Known risk, accepted: ADR-0063 is inside its objection window until 2026-10-22, and ADR-0061 / ADR-0062 / ADR-0052 on which it rests are inside theirs. Code slices were carried out inside such windows before (T-0130, T-0192, T-0196); an objection creates a task that changes this module with it. Say so in one line of the commit body.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, time limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) - mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED, never worked around), §2 (never touch `PROCESS/STATE.json`), §3 "BLOCKED 사유" paragraph, §9
- **ARCHITECTURE/decisions/ADR-0063-od18-run-tools-result-members.md**: lines 28-36 (decision 1: one list for both tools, form rules - strict JSON, no `null`, absent member left out), 37-44 (decision 2, `outcome`), 45-65 (decision 3, `condition` and its seven values in order; a broken result carries no measurement), 66-76 (decision 4, `intervals_ns` / `resolution_ns`, no upper bound, not ADR-0001 *integers*, no summary), 77-86 (decision 5, `shape`, `n_max`, `sample_form`; present in a broken result too; what is not in a result), 87-94 (decision 6, `memory_bytes`), 95-106 (decision 7, `ceiling` and `bound`, the derivation and "What follows from the cited definitions"), 107-112 (decision 8, what a result never holds), **113-144 (decision 9: the table, the closed list, the four JSON examples)**, 145-152 (decision 10), and the Consequences bullet "Code slices" (around line 212)
- PROCESS/tasks/T-0199-adr-od18-run-tools-result-members.md `## Result`, "Result members as landed" and the deviation note (seven conditions, not nine)
- ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md line 34 (the definition of an *integer*: 0 to 2^53 - 1)
- The model to follow, read only: `hilclaw/check_result.py` (whole file) and `tests/test_check_result.py` (whole file, in particular `imported_modules` at line 126 and the module tests), PROCESS/tasks/T-0130-correctness-check-result-builder.md `## Result` "The interface as landed"
- Read only, not edited: `hilclaw/harness/memory_ceiling.py` lines 1-80 (`BOUND_MAX`, `Verdict`, `verdict`: equality is within; a `None` figure is not judged); `hilclaw/harness/timing.py` lines 80-170 (`SAMPLE_FORMS`, `Broken`, `Judgement`, `TimingResult`: what a later caller holds) and 214-254 (`judge_report`); `hilclaw/harness/measurement.py` (`N_MIN`); `hilclaw/run_objective.py` (`Admitted.bound`: `None` means no ceiling stated); `hilclaw/tools.py` lines 204-275 (`check_json_object`, `encode`)
- `tests/test_gemm_contract.py` lines 141-150 and 386-411, `tests/test_standin_profile.py` lines 1032-1060 - read only, **not edited**
- CLAUDE.md - 상시 규칙: "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" 1 to 5, "코멘트 최소화", "미결은 발명하지 않는다", "개발 드라이버와 런타임의 구분"
- .claude/skills/dev-item-address/SKILL.md (procedure); .claude/skills/dev-code-review/SKILL.md
- `.github/workflows/ci.yml` and `pyproject.toml` - read only (test presence; coverage gate at 80 % lines and functions; ruff rules)
- Issue #5: every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6190947723 (the ADR-0063 notice; `gh issue view 5 --repo myungjoo/HIL-Claw --json comments`). If the repository owner has objected to ADR-0063, ADR-0061, ADR-0062, ADR-0052 or ADR-0042, or has answered a notice in a way that changes a member, a value or a presence rule of the table, do not start: return BLOCKED ("requirement unclear") quoting the comment. An answer to HQ-0013..HQ-0019 does not stop this task

## Acceptance Criteria
ADR-0063 fixes the members. The module name, names and parameters of functions and constants, what a refused argument raises, the member order and the docstring texts are **this task's choices**: state each with one line of reason in the commit body, the PR body and `## Result`. Where a criterion below and the record disagree, **the record wins**: follow it and say so in `## Result`.

### Files
- New: `hilclaw/run_result.py` and `tests/test_run_result.py`. **Nothing else**: every other file under `hilclaw/` and `tests/`, `pyproject.toml`, `.github/`, `README.md`, every ADR and the OD register stay as they are. If another file must change, return BLOCKED with the reason.
- Language: Python (the callers to come are Python and a result is a `dict` that `hilclaw.tools.call` checks); one line of reason in the commit body and `## Result`.
- The module text contains neither `gemm_contract` nor `standin_profile`. It imports the standard library and, at most, `hilclaw.harness.memory_ceiling` (pure standard library, already imported by `hilclaw/run_objective.py`). It does not import `hilclaw.harness.timing`, `hilclaw.harness.verification*`, `hilclaw.instance`, `hilclaw.tools`, `hilclaw.hw_tool`, `hilclaw.journaled_tool` or `hilclaw.run_objective`, and no other file under `hilclaw/` comes to import it.

### The module
- **Public constants** for the values the record fixes, so no caller spells them again (names are the task's choice; recommended): `CONVERGED` (`"converged"`), `NOT_CONVERGED` (`"not_converged"`), `BROKEN` (`"broken"`); `CONDITIONS`, the tuple of the **seven** values in the order of ADR-0063 decision 3 (`"build_time_limit"`, `"build_exit_status"`, `"time_limit"`, `"exit_status"`, `"report_form"`, `"zero_interval"`, `"replay"`); `SAMPLE_FORMS` (`"interval"`, `"reciprocal"`); `WITHIN`, `OVER`, `NOT_JUDGED`, `NOT_STATED` (the four values of `ceiling`). Do not import `timing.SAMPLE_FORMS` (the import restriction above); a test may assert that the two tuples are equal.
- **Two public functions** (recommended names and parameters; another shape is the task's choice as long as every rule holds; no parameter has a default):
  - `completed(outcome, *, intervals_ns, resolution_ns, memory_bytes, m, k, n, n_max, sample_form, bound)` - `outcome` is `"converged"` or `"not_converged"`; `memory_bytes` is `None` (the run yielded no figure) or the figure; `bound` is `None` (no ceiling stated) or the `bound` read. Returns exactly `outcome`, `shape`, `n_max`, `sample_form`, `resolution_ns`, `intervals_ns`, `memory_bytes` (only when not `None`), `ceiling`, `bound` (only when not `None`).
  - `broken(condition, *, m, k, n, n_max, sample_form, bound)` - returns exactly `outcome` (`"broken"`), `condition`, `shape`, `n_max`, `sample_form`, `ceiling`, `bound` (only when not `None`). It takes no intervals, resolution or figure (ADR-0063 decision 3: "A broken result carries no measurement").
- **`ceiling` is derived, never an argument** (recommended, as `check_result.completed` derives `outcome`), so no call can state a verdict its figure contradicts:
  - `bound` is `None` -> `"not_stated"`, whatever `memory_bytes` is (decision 7: "with `"not_stated"` `memory_bytes` may or may not be present").
  - broken with a `bound` -> `"not_judged"`.
  - completed with a `bound`: `memory_bytes` is `None` -> `"not_judged"`; `memory_bytes <= bound` -> `"within"` (equality is within); otherwise `"over"` (ADR-0052 decision 5 as ADR-0063 decision 7 cites it). Recommended: obtain the three-way verdict from `hilclaw.harness.memory_ceiling.verdict` and map `Verdict` to the strings, so the rule is stated once in the package; the executor may write the comparison itself and say why. `verdict` takes any `int` figure of at least 1 and refuses a `bound` above `BOUND_MAX` with `MemoryCeilingError`; since `memory_bytes` has no upper bound in the table, check that an admitted large figure is not refused by the path chosen and that `MemoryCeilingError` never leaks.
  - If the executor takes a `ceiling` argument instead, a value that disagrees with the derivation is refused.
- **`shape`** is a new `dict` with exactly `m`, `k`, `n`; `intervals_ns` is a new `list` in the order given (a `tuple` argument is returned as a `list`). The result shares no mutable object with an argument.
- **What is admitted** (each parameter by the table; anything else refused, nothing returned):
  - `m`, `k`, `n`: exactly an `int` (`bool` and subclasses refused), 1 to 2^53 - 1. `n_max`: exactly an `int`, 5 to 2^53 - 1. `bound`: `None` or exactly an `int`, 0 to 2^53 - 1 (the *integer* of ADR-0001, the form of ADR-0050 decision 4; equal to `memory_ceiling.BOUND_MAX`).
  - `resolution_ns`: exactly an `int` >= 0, no upper bound. `intervals_ns`: exactly a `list` or a `tuple` whose entries are exactly `int` >= 1, no upper bound. `memory_bytes`: `None` or exactly an `int` >= 1, no upper bound. As in `check_result`, an `int` the interpreter does not convert to decimal text is refused with `ValueError` (`check_json_object` would refuse the object); say so in the docstring.
  - Whether an empty `intervals_ns` is admitted: the table says "array of JSON integers >= 1" and states no length. Recommended: admit it and add no relation between `intervals_ns`, `n_max` and `outcome` (the replay is `judge_report`'s, not the builder's; no record states a length rule for the result). If the executor refuses an empty array or a length relation, it must cite the record sentence that makes the refused value impossible, in the docstring and in `## Result`; otherwise return BLOCKED ("requirement unclear") rather than invent one.
  - `outcome` (of `completed`): exactly a `str`, `"converged"` or `"not_converged"` (`"broken"` refused there). `condition`: exactly a `str`, one of the seven. `sample_form`: exactly a `str`, one of the two. A member of an enumeration (the harness's `Broken`, `State`, `Verdict`) is refused like any non-`str`.
- **What a refused argument raises**: recommended `TypeError` for a type not accepted and `ValueError` for a value of an accepted type that the table does not admit, the message starting with the parameter name (`intervals_ns[2]: ...`), in the manner of `check_result`. Determinate for every argument: no `KeyError`, `IndexError`, `AttributeError`, `OverflowError` or `MemoryCeilingError` leaking. A missing or surplus keyword is Python's own `TypeError`.
- **Member order** of the returned `dict` (the module's choice, said so in the docstring): recommended the order of the table, `outcome`, `condition`, `shape`, `n_max`, `sample_form`, `resolution_ns`, `intervals_ns`, `memory_bytes`, `ceiling`, `bound`; within `shape` `m`, `k`, `n`. The four examples of ADR-0063 decision 9 use this order.
- Pure: no argument is modified or kept, no file read or written, no process started, no state kept; equal arguments give equal results.
- Docstrings: the module docstring says what it renders (ADR-0063 decision 9, by decision number), what each function is for, the choices that are the module's own, and what the module does not do (no judging, no replay, no mapping from the harness's types or from an operation, no tool, no registration, no check of a stored result, no default of any value, no admission of `memory_ceiling`). Doxygen-style docstrings for public functions in the manner of `hilclaw/check_result.py`. No sentence states a rule the records do not hold (nothing on who calls, on the result files `sim.json` / `board.json`, on the seed, on condition (c) being met). Comments follow CLAUDE.md "코멘트 최소화".

### Tests (CLAUDE.md "테스트 규칙" / DRIVER §5 D12), all in the new `tests/test_run_result.py`
- Rule 1: package total of `hilclaw/` stays >= 80 % lines and functions; every line of the new module executed. Rule 3: every public function tested. Rule 4: the test file is the module's counterpart. Rule 5: no test whose subject is test code, CI, a hook or a driver helper.
- happy: the four JSON examples of ADR-0063 decision 9, written out as literals, equal what the functions return for the corresponding arguments (member sets compared exactly; the fourth example with `bound=80000000`); each passes `hilclaw.tools.check_json_object` and `json.loads(hilclaw.tools.encode(result))` equals it; the encoded member order is that of the examples. Name the `n_max` 10 constant so it reads as an example, not a default.
- branch, `ceiling`: all reachable combinations - completed with `bound=None` and a figure / no figure (`"not_stated"`, `memory_bytes` present / absent); completed with a bound and a figure below, equal to (`"within"`) and above (`"over"`) it; completed with a bound and no figure (`"not_judged"`, no `memory_bytes`); broken with no bound (`"not_stated"`, no `bound`) and with a bound (`"not_judged"`, `bound` present); `bound=0` with a figure of 1 (`"over"`); `bound=2**53 - 1`.
- branch, values: each of the seven conditions gives a broken result with it; both outcomes of `completed`; both sample forms; the constant tuples equal the record's values in its order; `SAMPLE_FORMS` equals `hilclaw.harness.timing.SAMPLE_FORMS`.
- presence rules (parametrised over the happy and branch cases): `condition` exactly in a broken result; `resolution_ns` / `intervals_ns` exactly in a completed one; `memory_bytes` never in a broken one; `bound` exactly when `ceiling` is not `"not_stated"`; `outcome`, `shape`, `n_max`, `sample_form`, `ceiling` always; no value anywhere is `None`; the member set is a subset of the ten and nothing else.
- bounds: `m = k = n = 1`, `n_max = 5`, `resolution_ns = 0`, an interval of 1; `2**53 - 1` for each *integer* parameter; an interval, `resolution_ns` and `memory_bytes` above `2**53` are admitted (no upper bound) and round-trip through `encode` / `json.loads`.
- negative, each raising the documented exception type and returning nothing: `m`, `k`, `n` as `0`, `-1`, `2**53`, `True`, `1.0`, `"1"`, `None`; `n_max` as `4`, `2**53`, `True`, `5.0`, `None`; `bound` as `-1`, `2**53`, `True`, `1.0`, `"0"`; `resolution_ns` as `-1`, `True`, `1.0`, `None`; `intervals_ns` as `None`, a `str`, a `dict`, a generator, an entry `0`, `-1`, `True`, `1.0`, `None`; `memory_bytes` as `0`, `-1`, `True`, `1.0`; `outcome` as `"broken"`, `"CONVERGED"`, `""`, `None`, an `enum.Enum` member defined in the test; `condition` as `"converged"`, `"check_value"`, `"TIMEOUT"`, `"timeout"`, `""`, `None`, `1`, an `enum.Enum` member; `sample_form` as `"Interval"`, `""`, `None`; a `str` subclass instance for each string parameter; an `int` beyond `sys.get_int_max_str_digits()` for a no-upper-bound parameter (skip where the limit is switched off); a missing and a surplus keyword; `intervals_ns` handed to `broken` and `condition` to `completed`.
- purity: arguments compare equal to deep copies made before the call; mutating the returned `shape` / `intervals_ns` changes neither the arguments nor a second result; a call writes no file (`monkeypatch.chdir(tmp_path)`, then the directory is empty).
- module: the import set is the documented one (an `imported_modules` helper of this test file's own, as in `tests/test_check_result.py`); the public names are exactly the documented ones; no `main`, no `__main__` in the text.
- **Permitted edits of existing tests: none expected.** If an existing assertion fails **solely because a new module file exists under `hilclaw/`**, a minimal edit of that one assertion is permitted: list it in `## Result`. Any other failing existing test: return BLOCKED with the output.
- Local run before the PR: `python -m ruff check .`, `python -m ruff format --check .`, `python -m pytest`; coverage from the CI run if `coverage` is not installed locally (install nothing). Tests must pass on Windows and Linux.

### Do not invent
- No tool function, registration, input schema, description, failure kind or `ToolFailure`, no `step` value, no reader of `instance.json`, no mapping from `Judgement` / `TimingResult` / `Broken` / `State` / operation answers, no summary (trimmed mean), no replay, no seed, no request member, no `point`, no `n_min` / `cv_max`, no text or version member, no member outside the table. No admission of `memory_ceiling` and no edit of `hilclaw/instance.py`, `hilclaw/spec.py` or `hilclaw/run_objective.py`. No checker of a stored result. No default of any value.
- If a point needs a decision the records do not hold and that is more than names, parameters, texts, exception types or member order, return BLOCKED ("requirement unclear") with the exact question.
- No real `claude` process, no board, no API key (D16): this task needs none.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0200'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0200 --state all`. Then `gh pr list --repo myungjoo/HIL-Claw --state open`: an open PR that adds or edits a file of `touchesFiles` is BLOCKED ("open PR conflict").
- Code mode (CLAUDE.md A-13): branch `claude/T-0200-run-tools-result-builder`; Draft PR with `T-0200` in the title and `Task: T-0200` as the last line of the body; reviewer cycle of dev-item-address with a fresh-context `dev-reviewer` each round (at most 7 rounds; past the cap without Approve, BLOCKED; if no reviewer can be spawned, BLOCKED - do not self-review). Tell the reviewer to write no file. Ask it explicitly to (a) compare returned objects and docstrings with ADR-0063 decisions 2 to 7 and 9 member by member - names, types, values, the order of the seven conditions, every presence rule, the two kinds of integer and the `ceiling` derivation; (b) check no argument yields a result the table does not admit and none leaks an undocumented exception; (c) check nothing on "Do not invent" entered `hilclaw/` and no docstring says more than its record (in particular nothing claims condition (c) of ADR-0052 decision 7 is met); (d) check no existing file was edited and the module text holds neither scanned string; (e) re-check the planner's judgements under "Why".
- Merge only when every CI check is green (`gh pr checks`; three consecutive CI failures are BLOCKED): `gh pr merge --squash --body` with the PR body so `Task: T-0200` is in the squash message; then delete the branch, remote and local, in separate commands. English commit messages, with one line on the language and one on the objection windows.
- Never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around.
- `## Result`: fill it in after the merge, on `main`, uncommitted for the driver (DRIVER §3-6). No fenced code block. Record: PR and squash commit, review rounds and findings, language and reason, **the public names, each function's signature, accepted argument types and what a refused argument raises, how `ceiling` is derived, the member order** (the tool functions and the mock's script are written against them), any argument the table admits but the module refuses, any existing assertion edited, coverage numbers, non-test diff size, follow-ups. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- The tool functions of `sim.run` / `board.run`, their registration, the operation of `cpu_standin`, the mock's operation and script, the conformance tests of P1-1.
- The mapping from `Judgement`, `TimingResult`, `Broken`, `State`, `Verdict` or an operation's answer to this module's arguments; the form of what crosses the cut.
- The timing seed (OD-13 sub-question 7), the result files `sim.json` / `board.json`, the admission of `memory_ceiling` (check 4 of ADR-0050), condition (c) of ADR-0052 decision 7.
- Any change of an existing module, test, README or ARCHITECTURE document; the integrator's list of less-exact sentences in ADR-0063 Consequences.
- Tests of test helpers, CI workflows, hooks or driver helpers.

## Follow-ups
- (planner - document mode, §9, P1-1) The timing seed (ADR-0061 Consequences item (3), OD-13 sub-question 7), in the manner of ADR-0048; then the form of what crosses the cut and the neither-form answer (ADR-0061 Consequences item (4)).
- (planner - code mode, after the seed and the cut records) The tool functions of `sim.run` / `board.run`: map `Judgement` / the operation's answer / `run_objective.Admitted` to this module's arguments and return what it builds.
- (integrator - document mode) The less-exact sentences listed in ADR-0063 Consequences.

## Result
DONE. PR #137 (https://github.com/myungjoo/HIL-Claw/pull/137), squash-merged as `43dfb77` (squash message ends `Task: T-0200`). Branch commits `24ed50b` (module and tests) and `914b03f` (review nit). The remote and local branches are deleted.

- **Review**: 2 rounds with a fresh-context `dev-reviewer` (opus). Round 1 approved with two non-blocking nits. (1) An unrelated `CONDITIONS` assertion at the end of the purity test: removed in `914b03f`. (2) The `decimal_limit` fixture sets the limit to 4300 instead of skipping where the limit is switched off: kept, as in `tests/test_check_result.py`, so the case runs on every interpreter and the limit is restored at teardown; the reviewer accepted this. Round 2 approved with no findings. Both reviewers re-checked the planner's judgements under "Why" and found them sound. No comment on Issue #5 after the ADR-0063 notice, so there is no objection.
- **CI**: all six checks green on `914b03f` (Python 3.11 / 3.14, coverage, test presence, shellcheck, clang); no failures. Locally: `ruff check` and `ruff format --check` clean; full `pytest` gives 20030 passed, 354 skipped (Windows, Python 3.14).
- **Coverage** (CI coverage gate): `hilclaw/` lines 5347/5366 = 99.64 %, functions 530/530 = 100 %; `hilclaw/run_result.py` 65/65 statements = 100 %.
- **Language**: Python, because the callers to come are Python and a result is a `dict` that `hilclaw.tools.call` checks.
- **Files**: new `hilclaw/run_result.py` (247 lines, most of them docstrings; non-test diff only this file) and `tests/test_run_result.py`. No existing file was edited and no existing assertion changed. Imports are `reprlib` and `hilclaw.harness.memory_ceiling` only. The module text contains neither `gemm_contract` nor `standin_profile`, and no other module imports it.

The interface as landed (the tool functions and the mock's script are to be written against it):
- **Public names**:
  - `CONVERGED = "converged"`, `NOT_CONVERGED = "not_converged"`, `BROKEN = "broken"`.
  - `CONDITIONS = ("build_time_limit", "build_exit_status", "time_limit", "exit_status", "report_form", "zero_interval", "replay")`, the order of ADR-0063 decision 3.
  - `SAMPLE_FORMS = ("interval", "reciprocal")`, restated rather than imported from `timing`; a test asserts that it equals `timing.SAMPLE_FORMS`.
  - `WITHIN = "within"`, `OVER = "over"`, `NOT_JUDGED = "not_judged"`, `NOT_STATED = "not_stated"`.
  - `completed` and `broken`.
  - Reason: callers then never spell a value again.
- **`completed(outcome, *, intervals_ns, resolution_ns, memory_bytes, m, k, n, n_max, sample_form, bound)`**:
  - Returns `outcome`, `shape`, `n_max`, `sample_form`, `resolution_ns`, `intervals_ns` (a new `list`), `memory_bytes` (only when not `None`), `ceiling` and `bound` (only when not `None`).
  - Accepted arguments:
    - `outcome`: exactly a `str`, `"converged"` or `"not_converged"`.
    - `intervals_ns`: exactly a `list` or `tuple` of exactly-`int` entries, each >= 1, no upper bound; it may be empty.
    - `resolution_ns`: exactly an `int` >= 0, no upper bound.
    - `memory_bytes`: `None`, or exactly an `int` >= 1 with no upper bound.
- **`broken(condition, *, m, k, n, n_max, sample_form, bound)`**:
  - Returns `outcome` (`"broken"`), `condition`, `shape`, `n_max`, `sample_form`, `ceiling` and `bound` (only when not `None`).
  - Takes no measurement, because ADR-0063 decision 3 says "A broken result carries no measurement".
- **Common parameters** (both functions; no parameter has a default):
  - `m`, `k`, `n`: exactly an `int` from 1 to 2**53 - 1.
  - `n_max`: exactly an `int` from 5 to 2**53 - 1.
  - `sample_form`: exactly a `str`, one of `SAMPLE_FORMS`.
  - `bound`: `None` (no ceiling stated), or exactly an `int` from 0 to 2**53 - 1.
  - These are the ADR-0001 integers. Only `resolution_ns`, the intervals and `memory_bytes` have no upper bound (ADR-0063 decision 4).
- **What a refused argument raises**:
  - `TypeError` for a type that is not accepted, including `bool`, subclasses of `int` / `str`, enum members, generators and `None` where it is not admitted.
  - `ValueError` for a value of an accepted type that is not admitted.
  - The message starts with the parameter name, for example `intervals_ns[2]: ...`.
  - An `int` beyond `sys.get_int_max_str_digits()` raises `ValueError` even where the table states no upper bound, because `check_json_object` / `encode` could not write it.
  - A missing or surplus keyword raises Python's own `TypeError`.
  - No other exception leaks; in particular `MemoryCeilingError` cannot, because `bound` is checked before `verdict` is called.
- **`ceiling` is derived, never an argument**:
  - `bound is None` gives `"not_stated"`, whatever `memory_bytes` is.
  - Otherwise it is `memory_ceiling.verdict(memory_bytes, bound)` mapped to `"within"` / `"over"` / `"not_judged"`. Equality counts as within; a broken run passes the figure `None`, which gives `"not_judged"`.
  - Reason: no call can state a verdict that its figure contradicts, and the comparison rule is written once in the package.
- **Member order**: the order of the table — `outcome`, `condition`, `shape`, `n_max`, `sample_form`, `resolution_ns`, `intervals_ns`, `memory_bytes`, `ceiling`, `bound`; within `shape`, `m`, `k`, `n`. This is the order of the four examples in the record.
- **Pure**: no argument is modified or kept, the result shares no mutable object with an argument, and no file, process or state is used.
- **Admitted by the table but refused by the module**: only an `int` without decimal text on this interpreter, as described above. No length relation was added, and an empty `intervals_ns` is admitted.
- **Conflicts**: none between the acceptance criteria and the record.
- **Not done here**: condition (c) of ADR-0052 decision 7 is not met by this change. `memory_ceiling` is still not admitted.

Follow-ups: as listed in `## Follow-ups` (the timing seed, then the tool functions of `sim.run` / `board.run`, and the integrator's list of less-exact sentences). This task adds none.

Language of this Result: English.
