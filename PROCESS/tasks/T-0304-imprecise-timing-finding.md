---
id: T-0304
title: Add the derived imprecise-timing finding of a measurement and of a run as pure functions (ADR-0103, ADR-0104)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [NFR-3, OD-13, FR-10, C-7, "ADR-0103", "ADR-0104"]
dependsOn: [T-0302, T-0303]
touchesFiles: [hilclaw/harness/timing_finding.py, tests/harness/test_timing_finding.py]
estimatedSize: {loc: 140, files: 1}
hq: []
---
## Why

ADR-0103 decides when a measurement of `sim.run`/`board.run` counts as taken in an imprecise timing environment. It has a measured ground (decision 3), with the constant `resolution_share_max` = 1 % (decision 7), and a run finding (decision 5). ADR-0104 decides that nothing is stored. Both findings are derived. The finding of a measurement comes from the `result` of its run tools' end line (decision 3). The finding of a run is a fold over those lines in log order (decision 4). Both records name this as the follow-up code task: "a pure function of an end line's `result` and the constant, and a run's finding as a fold over the run tools' end lines. It writes nothing for either" (ADR-0104 Consequences; ADR-0103 Consequences). This task adds that code and nothing else. No tool, no event kind, no `step` value, no stored member and no data-plane schema change.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time cap) and §5 (task format, naming convention, size cap, test rules D12).
- `CLAUDE.md`, "상시 규칙": comment minimisation, test rules ①-⑤, layer-2 language policy, branch/merge procedure (code mode).
- `ARCHITECTURE/decisions/ADR-0103-od13-imprecise-timing-detection.md`: decisions 1, 3, 5, 6 and 7 (lines 25-30, 37-48, 58-79). Decision 4 (lines 49-57) only for the statement that the class ground never holds until its input exists.
- `ARCHITECTURE/decisions/ADR-0104-od13-imprecise-timing-mark.md`: decisions 1 to 5 (lines 24-71) and Consequences (lines 97-111).
- `ARCHITECTURE/decisions/ADR-0063-od18-run-tools-result-members.md`: decisions 2, 4 and 9 (lines 37-44, 66-76, 113-144). These give the members `outcome`, `resolution_ns` and `intervals_ns` and when each is present.
- `ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md`: decision 3 (lines 42-60), for the `data` of a `step_ended` line (`step`, `execution`, `spend`, exactly one of `result`/`failure`).
- `ARCHITECTURE/decisions/ADR-0062-od18-run-tools-call-identity.md`: decision 3 (lines 53-65), for the two `step` values.
- `hilclaw/run_identity.py` (whole file; `STEPS`, `STEP_SIM_RUN`, `STEP_BOARD_RUN`).
- `hilclaw/run_result.py` (lines 1-80; `CONVERGED`, `NOT_CONVERGED`, `BROKEN`; the refusal conventions).
- `hilclaw/journal.py` (lines 1-50 and 95-210; `STEP_ENDED`, `check_step`, and the line-checking convention of `fold`).
- `hilclaw/events.py` (lines 1-53 and `read`, lines 181-229; what a parsed line looks like).
- `hilclaw/harness/measurement.py` (lines 1-60; how a policy constant of the harness is written).

## Acceptance Criteria

1. **Module and language.** One new module `hilclaw/harness/timing_finding.py`, in Python. Python is the language of `hilclaw/harness/measurement.py` and of the parsed lines it reads; record this in `## Result` and in the commit body as one line. One new test file `tests/harness/test_timing_finding.py`. Nothing else under `hilclaw/`, `tests/`, `ARCHITECTURE/` or `.github/` changes. The module docstring is in the style of the sibling modules. It names ADR-0103 and ADR-0104 as the rules, lists which choices are this module's own, and says what the module does not do (see criterion 7).
2. **The constant.** A public module constant `RESOLUTION_SHARE_MAX` stands for `resolution_share_max` = 1 % (ADR-0103 decision 7). It is a policy constant in the harness source. It is not a parameter of any function. The executor picks its representation. The coarse-clock comparison must be exact for every admitted integer, with no float rounding. The specified form is 100 × `resolution_ns` > smallest entry of `intervals_ns` (for example, integer arithmetic or `fractions.Fraction(1, 100)`). The docstring states the representation chosen.
3. **Finding of a measurement from a result.** A public function, for example `measurement_found(result)`, takes one result object of `sim.run`/`board.run` as a parsed `dict` and returns `True` or `False` (ADR-0103 decision 3; ADR-0104 decision 3):
   - `outcome` `"not_converged"` → `True`.
   - `outcome` `"converged"` → `True` exactly when `resolution_ns` × 100 > min(`intervals_ns`), and `False` otherwise. `resolution_ns` 0 never gives `True`.
   - `outcome` `"broken"` → `False`. No other member is read.
   - It reads only `outcome`, plus `resolution_ns` and `intervals_ns` when the outcome is `"converged"` or `"not_converged"`. It does not check any other member against ADR-0063's table, and it says so in its docstring.
   - Refusals (ADR-0104 decision 5 leaves open what a reader does with a result that breaks the presence rules, so the function gives no finding for one). It raises `TypeError` when `result` is not exactly a `dict`, or when a member it reads has the wrong type: not exactly `str` for `outcome`, not exactly `int` (no `bool`, no `float`) for `resolution_ns` and the interval entries, not exactly a `list` or `tuple` for `intervals_ns`. It raises `ValueError` for an `outcome` outside the three values, for a member it needs that is absent, for `resolution_ns` < 0, for an interval entry < 1, and for an empty `intervals_ns` when the outcome is `"converged"` (no smallest entry). An empty `intervals_ns` with `"not_converged"` gives `True`. The message starts with the member name. The function modifies no argument. Document the refusals as this module's own choice.
4. **Finding of a measurement from a line.** A public function, for example `line_finding(event)`, takes one parsed line as `hilclaw.events.read` returns it:
   - It returns `None` when the line is not a run tools' end line, that is, when `kind` is not `step_ended` or `data.step` is not in `hilclaw.run_identity.STEPS`. Lines under any other `step` value are not read (ADR-0104 decision 3).
   - For a run tools' end line, the line is checked as `hilclaw.journal.check_step` checks it, and errors pass through. The function returns `False` when the line holds `failure` and no `result`. Otherwise it returns the value of criterion 3 for `data.result`.
5. **Finding of a run.** A public function, for example `run_found_at(lines)`, takes any iterable of parsed lines in file order, reads it once, and folds over it (ADR-0103 decision 5 (a); ADR-0104 decision 4):
   - It returns the 1-based number, within `lines`, of the first line for which criterion 4 gives `True`. It returns `None` when there is no such line.
   - Both tools' lines count. A second end line of one identity, or one without a start line, counts like any other (ADR-0104 decision 3, last bullets).
   - Each line is checked as `hilclaw.journal.fold` checks lines: `hilclaw.events.validate`, plus `check_step` for a step line. The first line that fails raises with `line <number>:` in front, and nothing is returned.
   - The docstring states three things. The class ground (b) never holds here until a later record produces its input (ADR-0103 decision 4, ADR-0104 decision 4). The caller decides whether the run is in scope, from the hw_profile of its `instance.json` (ADR-0104 decision 1). A prefix of the log gives the finding at that moment.
   - Whether lines after the first finding are still read and checked is the executor's choice, stated in the docstring. For a valid log the returned number is the same either way.
6. **Tests** (`tests/harness/test_timing_finding.py`, D12 ①-④). Cover every public function and the constant, with happy, error, branch and negative cases, including at least:
   - not converged with a fine clock → `True`; converged with 100 × resolution exactly equal to the smallest interval → `False`; one more nanosecond of resolution → `True`; resolution 0 → `False`; converged with a large integer beyond float precision where float rounding would give the wrong answer → the exact answer; broken → `False`, even with stray members;
   - each refusal of criterion 3 (non-`dict`; `bool` and `float` in place of `int`; a `str` subclass for `outcome`; unknown outcome; missing `resolution_ns` or `intervals_ns`; negative resolution; interval 0; empty intervals when converged), and that the argument is unmodified;
   - `line_finding`: a non-step kind, a `step_started` line, a `step_ended` line under another `step` (for example `correctness.check`'s or a made-up name) → `None`; a `failure` end line → `False`; a malformed run tools' end line (both `result` and `failure`, missing `spend`) → the `journal` error;
   - `run_found_at`: an empty iterable → `None`; a log with only clean results → `None`; a log whose first found line is a `board_run_timing` line after clean `sim_run_timing` lines → its number; a generator is read once; a damaged line before a finding → the error with its line number.
   Lines are built in memory. No test writes a file unless an existing helper requires it, starts a process, reads a clock or uses a compiler. Line and function coverage of `hilclaw/` stays at least 80 %.
7. **What the module does not do** (stated in its docstring, and true of the code). It reads or writes no file, appends no line, and calls no `events.read`. It reads no `instance.json` and no `source_commit`. It starts no process and reads no clock. It is no tool and is registered nowhere. It shows no warning (OD-13 ⑪ (라), OD-27). It adds nothing to the data plane. It does not decide reuse across runs or absolute-target judgement (⑪ (다)), and it does not establish the class input or OD-14 ①. It does not replay the stopping rule: `outcome` is believed as stored (ADR-0104 decision 3 table; ADR-0063 Limit 2). It does not change `hilclaw/harness/measurement.py`, `hilclaw/run_result.py`, `hilclaw/run_identity.py` or `hilclaw/journal.py`.
8. **Mode and landing.** Code mode (CLAUDE.md A-13):
   - branch `claude/T-0304-imprecise-timing-finding`; Draft PR whose title contains `T-0304`;
   - reviewer cycle (dev-code-review, at most 7 rounds); CI green; `ruff` and `pytest` pass locally;
   - squash-merge with `gh pr merge --squash --body` so that the PR body's last line `Task: T-0304` reaches the squash message; delete the branch; no force push.
   Files use LF only and `git diff --check` is clean.
9. **D16.** Nothing here needs a runtime machine. No `claude`, container, compiler run or timing run is started. If the work shows a fact that only a runtime machine can establish, list it in `## Result` as a runtime-acceptance item and do not try it.

## Out of Scope

- Any ADR, register (`ARCHITECTURE/Requirements.md`, `OpenDecisionProposals.md`, `StandardScenarios.md`), `EventKinds.md`, `StepValues.md` or `README.md` edit. This includes T-0303's two optional round-7 nits on ADR-0104.
- The class ground's input and its producing (ADR-0103 decision 4, OD-14 ①); scope selection by hw_profile; reading `instance.json` or `source_commit`.
- Building the `sim.run`/`board.run` tool functions, or wiring this module into any tool, report or Round-Manager prompt (⑪ (라), OD-27).
- Any change to `hilclaw/clang_build.py` or `tests/test_clang_build.py` (open PR #179).

## Follow-ups

- (doc, optional) T-0303's two round-7 nits on ADR-0104, decision 5 and the Consequences quote of ADR-0061 Limit 3 (see T-0303 `## Result`).
- (later) Use of these functions where the warning is shown, once ⑪ (라) / OD-27 is answered.

## Result

- PR #183 (squash-merged; merge commit: see `git log origin/main --grep='^Task: T-0304'`). Reviewer rounds: REVIEW_ROUNDS, final verdict Approve.
- Added `hilclaw/harness/timing_finding.py` (`RESOLUTION_SHARE_MAX = Fraction(1, 100)`, `measurement_found`, `line_finding`, `run_found_at`) and `tests/harness/test_timing_finding.py` (100 tests; module coverage 100 %). Full `pytest`, `ruff check` and `ruff format --check` pass locally.
- Language: Python, the language of `hilclaw/harness/measurement.py` and of the parsed lines that `hilclaw.events.read` returns.
- Executor choices stated in the module docstring: `run_found_at` reads and checks every line, also after the first finding (as `journal.fold`); `resolution_ns` and `intervals_ns` are checked for `not_converged` as well; refusal messages show nothing of the value; the three `outcome` values are spelled locally because `tests/test_run_result.py` forbids any other package module to import `hilclaw.run_result`.
- Runtime-acceptance items: none.
- Follow-ups: none new.
