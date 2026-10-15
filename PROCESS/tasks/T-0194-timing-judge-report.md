---
id: T-0194
title: Make the judging half of `run_timing` a public function of `hilclaw/harness/timing.py` (ADR-0061 code slice (2)) - it takes the report of a timing run with the sample form and `n_max` and judges it (form, zero interval, replay, completed with its state / broken with its condition) without starting anything - and keep `run_timing` unchanged in behaviour on top of it
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-9, FR-10, OD-18, OD-13, "#5 A-12", "#5 D12"]
dependsOn: [T-0191]
touchesFiles: [hilclaw/harness/timing.py, tests/harness/test_timing.py]
estimatedSize: {loc: 110, files: 1}   # non-test: about 30 statement lines and about 60 docstring lines in timing.py (279 lines today); the test file is excluded from the cap (D4)
hq: []   # implements a closed decision (ADR-0061 decision 3, Consequences "Code slices" (2)); closes no OD, writes no ADR, no new dependency, no data-plane file, registers no tool, names no member of a request or a result of a tool
---
## Why
ADR-0061 (landed as `8f971f1`, T-0191; accepted 2026-10-15 under DRIVER §9, objection window on issue #5 until 2026-10-22) placed the cut of `sim.run` / `board.run` for the runs of its decision 1: the operation of a backend builds and starts the timing run and returns **(A) the report, unchanged, with the figure or that there is none**, or **(B) that there is no report and which condition failed first**; the tool function carries out **all of the judging of the run** - the form of ADR-0009 decision 8, an interval of 0, the replay of the stopping rule with the sample form and `n_max` it handed over, and so completed (converged or not converged) or broken - "carried out by the code of the harness, in the process of the tool function" (decision 3).

Its Consequences ("Code slices", *possible now*) name two slices. Slice (1) landed as `139ac1a` (T-0192, `hilclaw/run_objective.py`). This task is **slice (2)**:

> the judging half of a timing run as a function of the harness that takes what an operation returns - the report, or the condition - with the sample form and `n_max`, and gives completed (with the state) or broken (with the condition), the parsing and the replay that are inside `run_timing` today; each with its tests.

Today `hilclaw.harness.timing.run_timing` does both halves in one function (lines 173-237): it starts the process, then judges. `parse_report` is public, but **the zero-interval test, the replay (`_replay_agrees`) and the order of the three conditions of the judging exist only inside `run_timing`**, behind a process start. A tool function handed a report by an operation cannot call them, and a second copy elsewhere would be a second harness (FR-9: one). ADR-0061 decision 3 itself observes: "`run_timing` does both halves in one function today, as `run_verification` did when ADR-0021 split the check; the code task splits it in the same way."

**The precedent is T-0074** (`7f5feea`, #63), which made the judging half of `run_verification` the public `judge_report` of `hilclaw/harness/verification.py` and kept `run_verification` on top of it. Follow its shape.

It serves PLAN P1-1. It ticks **no PLAN checkbox**: P1-1 stays open (the identity, result members and seed of the run tools, their tool functions, the mock's operation, the conformance tests).

Planner's judgements (2026-10-15 UTC, from the files; the reviewer is asked to re-check each):
- **No record is needed.** The function is inner structure of the harness that ADR-0061 decision 3 describes and its Consequences name as a slice; "The spelling of what is handed and returned is the next slices' and the code's" (decision 3). Its name, parameters and return form are this task's and provisional.
- **The function is bound nowhere.** No tool, registry, backend, table or front is touched; `hilclaw.backends.HW_TOOLS` and `tools.default_registry` stay as they are. Nothing here says whether a run tool is journaled, its `step`, what a request or a result holds, or where the seed comes from.
- **It judges a report (class A) and defines no type for class (B).** The two run conditions of (B) are `Broken.TIMEOUT` and `Broken.EXIT_STATUS`, which exist and need no computation; the two build conditions of (B) (build past its time limit, compiler's non-zero status - ADR-0061 decision 7's order) have no member of `timing.Broken` today, and how an operation says (B) is ADR-0061 Consequences item (4) ("the form of what crosses the cut"), a later slice. So, as in T-0074, the new function takes a report and can only find the three conditions the tool function finds: `REPORT_FORM`, `ZERO_INTERVAL`, `REPLAY`. **Do not add build conditions to `Broken`** (the check kept them out of `verification.Broken` too: `check_result.CONDITIONS` adds them above the harness). If you find the slice cannot be cut without a type for (B), do not invent one silently: choose the smallest form, mark it provisional and say so in `## Result`.
- **The memory figure stays out of the judging.** ADR-0061 decision 3 has the figure converted on the operation's side ("its unit rule depends on the platform") and "used only if the tool function finds the run completed". The judging function reads no `sys.platform`, takes no `max_rss` and returns no figure; `run_timing` keeps computing `memory_bytes` for a completed run exactly as today.
- **The behaviour of `run_timing` does not change**, and it stays public with its signature (including its `n_max=N_MAX_DEFAULT` default), `TimingResult` and its six fields, and the order in which it raises: it is still used by `tests/harness/test_timing_build.py`, `tests/harness/test_timing_driver.py` and the calibration path. Every existing test passes without an edit of its assertions.

Why this item now: no lock, no unresolved HQ blocking a selectable task (HQ-0013/14/16/17/18/19 are runtime-acceptance items of DONE tasks), no TODO / INTERRUPTED / IN_PROGRESS / BLOCKED task file and no open PR at planning time (`main` at `dcf2e49`). T-0192 and T-0193 both name this slice as the next candidate in their Follow-ups. The other follow-up (the second document slice of the run tools' contract, the identity of a call) does not depend on this one and is the candidate after it.

A-13 check (planner's reading - the reviewer is asked to re-check it):
- No new external dependency; `pyproject.toml` unchanged.
- No data-plane schema change: the function reads and writes no file and names no member of any file.
- No design-level OD is decided: no seed, no `n_max` source, no sample-form source (that is `run_objective`), no kind of tool failure, nothing of identity or execution point.

Known risk, accepted: ADR-0061 is inside its objection window (until 2026-10-22). Code slices were carried out inside such windows before (T-0074, T-0192). An objection creates a reverting task and this change is revisited with it.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) - mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED, never worked around), §2 last bullet (the driver's `PROCESS/STATE.json` - never touch it), §3 "BLOCKED 사유" paragraph, §9
- **ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md**: Status; Context bullet "What the code has today" (line 25); **decision 3 (lines 49-58: the tool function's part, what the operation returns - classes (A) and (B), why the judging is the tool function's and the figure the operation's, the observation on `run_timing`)**; **decision 7 (lines 86-96: the order of the conditions of broken; what a result must let a caller tell apart)**; Limit 7 (line 121); **Consequences (lines 148-155: "Code slices" (2); the `timing.py` docstring sentence that becomes less exact)**; Boundaries
- **ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md**: decision 7 (lines 65-72: the replay, "The Python side is the authority"), **decision 8 (lines 74-93: the report form, completed / broken)**, decision 9 (lines 94-110: the parameter table)
- ARCHITECTURE/decisions/ADR-0052-od13-memory-ceiling-measurement.md decision 4 (a run that is not completed yields no figure) - only to confirm the figure stays out of the judging
- **`hilclaw/harness/timing.py`** (279 lines, all of it: module docstring and conventions, `SAMPLE_FORMS`, `Broken`, `Report`, `TimingResult`, `driver_arguments`, `parse_report`, `run_timing`, `_replay_agrees`, `_integer`, `_digits`, `_fail`)
- **`tests/harness/test_timing.py`** (773 lines): lines 1-282 (imports, constants, `GOOD_REPORTS`, `BAD_REPORTS`, `THROUGH_A_RUN`, `report`, `StandIn`, `timed`, `assert_completed`, `assert_broken`), 400-470 (`parse_report` and `driver_arguments` cases), 473-655 (broken conditions, replay disagreements, argument errors, no-default and keyword-only cases), 657-773 (the memory-figure cases)
- **The precedent**: `git show 7f5feea` (T-0074: `judge_report` / `Judgement` in `hilclaw/harness/verification.py` and its tests); read `hilclaw/harness/verification.py` lines 1-160 and `judge_report` / `run_verification` / `_judgement` for the shape and the docstring style
- `hilclaw/harness/measurement.py` (`stopping_state`, `State`, `N_MIN`, `N_MAX_DEFAULT`, `InvalidSamplesError` - read only); `hilclaw/harness/memory_ceiling.py` docstring (read only; it names `run_timing` "for a completed run only" - stays true); `hilclaw/harness/__init__.py` (the docstring - read; edit it only if a sentence becomes false, and then count it in the diff); `hilclaw/local_run.py` (`RunResult` - read only)
- Callers of `run_timing` that must keep working unchanged (read only): `tests/harness/test_timing_build.py` around lines 440-460, `tests/harness/test_timing_driver.py` around lines 200-230
- PROCESS/tasks/T-0191-adr-od18-run-tools-split-and-memory-call.md `## Result` ("The split as landed"); PROCESS/tasks/T-0192-run-objective-admission.md `## Result` (slice (1), the module's own choices)
- CLAUDE.md - 상시 규칙: "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" 1 to 5, "코멘트 최소화", "미결은 발명하지 않는다"
- .claude/skills/dev-item-address/SKILL.md (procedure); .claude/skills/dev-code-review/SKILL.md (what the reviewer checks)
- `.github/workflows/ci.yml` - read only (the six jobs; `Coverage gate (hilclaw)` holds the package total at 80 % lines and functions)
- Issue #5: every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6186830791 (`gh issue view 5 --repo myungjoo/HIL-Claw --json comments`; it was the last comment at planning time). If the owner has objected to ADR-0061 or ADR-0009 in a way that changes the cut or a rule used here, do not start: return BLOCKED ("requirement unclear") quoting the comment

## Acceptance Criteria
ADR-0061 decisions 3 and 7 and ADR-0009 decisions 7 and 8 fix the rules. Names, the return form and the cases the records do not mention are **this task's choices, provisional**: state each with one line of reason in the commit body, the PR body and `## Result`. Where a criterion below and a record disagree, **the record wins**: follow it and say so in `## Result`.

### Files
- `hilclaw/harness/timing.py` (edit) and `tests/harness/test_timing.py` (edit). **Nothing else** under `hilclaw/` or `tests/` (the one allowed exception: a sentence of `hilclaw/harness/__init__.py` that the change makes false). `timing_build.py`, `timing_driver.c`, `measurement.py`, `memory_ceiling.py`, `run_objective.py`, `instance.py`, `backends.py`, `hw_tool.py`, `mock_backend.py`, `tools.py`, `pyproject.toml`, `.github/`, every ADR and the OD register stay as they are.
- No new module (so no new test file; test rule 4).
- Python, because the module exists in Python - one line in the commit body and `## Result`.

### The judging function
Recommended shape (names yours): a public **`judge_report(report, *, sample_form, n_max)`** returning a public `NamedTuple` **`Judgement(broken, state, intervals_ns, resolution_ns)`** - the first four fields of `TimingResult`, with the same meaning, and no `run` and no `memory_bytes`.
- It **starts no process, reads and writes no file, reads no environment variable, clock, `sys.platform` or random source, and keeps nothing between calls**. Its outcome is a function of its arguments alone.
- It takes the report as the bytes a timing process wrote on its standard output (the form of the module docstring) and carries out exactly what `run_timing` does today after the exit-status test, in the same order: the form (`parse_report`), then an interval of 0, then the replay with `sample_form` and `n_max`. The first that fails is the condition: `Broken.REPORT_FORM`, `Broken.ZERO_INTERVAL`, `Broken.REPLAY`; otherwise completed with the reported state, intervals and resolution.
- It never returns `Broken.TIMEOUT` or `Broken.EXIT_STATUS`: those are found by whoever ran the process (ADR-0061 decision 3 (B)). `Broken` keeps its five members, names and order; no member is added.
- For a broken judgement the three other fields are `None`: no interval of a broken run is offered (as `TimingResult` today).
- **All parameters besides the report are keyword-only and none has a default**: the tool function hands the `n_max` it read (ADR-0061 decision 3), so the judging must not fall back on `N_MAX_DEFAULT` silently. (`run_timing` keeps its own default unchanged.)
- Arguments are refused before any byte of the report is looked at: `sample_form` and `n_max` by the rules `driver_arguments` already applies (one of `SAMPLE_FORMS`, exactly `str`; an `int`, not a `bool`, of at least `measurement.N_MIN`), as `TimingArgumentError`, in an order you state. What is accepted as a report (exactly `bytes` recommended) and what a value of another type raises (recommended `TypeError`) is yours to choose; state it in the docstring and test it. **A wrong type must not come out as `Broken.REPORT_FORM`**: that condition is a statement about a process.

### `run_timing` over it
- `run_timing` starts the process as today and obtains its judgement from the new function (or from one private core both share - **one** implementation of the three judging conditions and of the replay in the module, not two).
- **Unchanged**: its signature and defaults, `TimingResult` and its six fields, `driver_arguments`, `parse_report`, the order of the conditions (`TIMEOUT`, `EXIT_STATUS`, then the three of the judging), the order of what it raises before anything is started (arguments, the executable's type, the empty prefix, the runner's errors), `run` as captured, that a timed-out or failed process is broken whatever it wrote, and `memory_bytes` (computed only for a completed run, from `run.max_rss` and the `sys.platform` read at the call).
- Every existing test of `tests/harness/test_timing.py`, `test_timing_build.py` and `test_timing_driver.py` passes with **no assertion changed**. If one would have to change, stop and say why in `## Result` before changing it.

### Docstrings (CLAUDE.md "코멘트 최소화": no multi-line comments; docstrings of the public API may be as long as needed)
- The module docstring names the new function and says that it is the judging half ADR-0061 decision 3 gives to the tool function, and that `run_timing` is kept for a timing run about no call (the build and driver tests, calibration). "What this module does not do" stays true (no default to the sample form, the seed or the time limit; no verdict on the memory figure).
- `judge_report` and `Judgement` docstrings: what is taken, the order of the conditions, what is never returned (`TIMEOUT`, `EXIT_STATUS`, a figure), that nothing is started or read, and what is raised in which order.

### Tests (D12; `tests/harness/test_timing.py`)
- **happy**: the worked report of ADR-0009 judged completed under both sample forms; a not-converged report ended at `n_max`; a larger `n_max`; `n_max == N_MIN`; every entry of `GOOD_REPORTS` that is completed through `run_timing` today is completed through the new function with the same fields.
- **branch / error**: each of `REPORT_FORM` (every entry of `BAD_REPORTS`), `ZERO_INTERVAL` and `REPLAY` (every entry of `REPLAY_DISAGREEMENTS`, both sample forms); the form before the zero interval; the caller's `n_max` is the one replayed; `TIMEOUT` and `EXIT_STATUS` are never returned.
- **equivalence**: for the same report and parameters, `run_timing` over a stand-in and the new function give the same first four fields (a parametrised case over the existing report tables is enough).
- **negative**: each bad `sample_form` and `n_max` (reuse `BAD_ARGUMENTS` where it fits) raises `TimingArgumentError` and looks at no byte of the report; a report of another type (`str`, `bytearray`, `memoryview`, `None`, `list`) raises the chosen error and never yields `REPORT_FORM`; no default for `sample_form` or `n_max`; parameters other than `report` are keyword-only.
- **purity**: the judgement does not depend on `sys.platform` (monkeypatched) and carries no figure.
- Local: `python -m pytest`, `ruff check`, `ruff format --check` green; `hilclaw/harness/timing.py` line and branch coverage reported in `## Result` (expected 100 %).

## Out of Scope
- Any type for class (B) of ADR-0061 decision 3 (the form of what crosses the cut is ADR-0061 Consequences item (4)); build conditions in `Broken`.
- The tool functions of `sim.run` / `board.run`, their identity, request and result members, the seed, the mock's operation, the `cpu_standin` operation, registration, check 4 of ADR-0050 in `hilclaw/spec.py`.
- The memory verdict (`memory_ceiling.verdict`) and joining it with the judgement; any use of `run_objective`.
- Any change to `driver_arguments`, `parse_report`, `timing_driver.c` or `timing_build.py`.
- Editing any ADR, the OD register, StandardScenarios or PLAN.md (the ADR-0061 "less exact" docstring note is satisfied by the module docstring of `timing.py` alone).
- Starting `claude`, a container or anything that needs a board or API key (D16). The existing tests that compile the driver with `clang` stay as they are.

## Follow-ups
- (planner, document mode, §9, P1-1; candidate for the next task) The second slice of the run tools' contract: the identity of a call (journaled or not, `step` values per tool, the meaning of `execution`, the request members, input schema and description), in the manner of ADR-0040 (ADR-0061 Consequences item (1); T-0191, T-0192, T-0193 Follow-ups).
- (planner, later, document mode) The result members (ADR-0061 Consequences item (2), the third clause of OD-13 sub-question ⑩ - may need a data-plane reading under A-13), the timing seed (OD-13 sub-question ⑦), and the form of what crosses the cut (item (4)).

## Result
