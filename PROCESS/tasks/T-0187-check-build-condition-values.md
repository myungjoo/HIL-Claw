---
id: T-0187
title: Add the owner's two build values of `condition` (`build_time_limit`, `build_exit_status`) to the result and the form (B) answer of `correctness.check`, ADR-0060 decision 4, code slice (1)
phase: P1
status: DONE
commitMode: code
coversReq: [FR-9, FR-10, OD-18, "#5 D12"]
dependsOn: [T-0176]
touchesFiles: [hilclaw/check_result.py, hilclaw/check_answer.py, hilclaw/check_judging.py, hilclaw/check_operation.py, hilclaw/check_ending.py, tests/test_check_result.py, tests/test_check_answer.py, tests/test_check_judging.py, tests/test_check_operation.py, tests/test_check_ending.py, tests/test_check_tool.py, tests/test_mock_check.py]
estimatedSize: {loc: 90, files: 5}   # excluding tests: a few lines of code each in check_result/check_answer/check_judging, the rest docstrings and one message in check_operation/check_ending
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts, `correctness.check` included) is open. T-0176 landed ADR-0060 (4060d70, owner notice https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6184597227, objection window until 2026-10-22). Its Consequences name two code slices that can be cut now (line 155): "(1) The two values in `hilclaw/check_result.py` (`CONDITIONS`, in the order of decision 4) and the two strings of form (B) where the tool function tests for it (`hilclaw/check_answer.py`, which takes `CONDITIONS[:2]`), with their tests. Two places pair the values by position today — that one and `hilclaw/check_judging.py`, which zips `verification.Broken` with `CONDITIONS` — so new values put first, as decision 4 orders them, break both unless the code task changes them" and "(2) The six kinds in `hilclaw.check_failure.BACKEND_KINDS`, with their tests."

This task is slice (1). Slice (2) is the next task (it touches `hilclaw/check_failure.py` only and is kept apart so that each stays inside the D4 file cap).

**Why this item now.** No lock, no TODO/INTERRUPTED/BLOCKED task, no open PR (checked 2026-10-15 at `0d89b20`). The open HQs (HQ-0013, HQ-0014, HQ-0016..HQ-0019) are `runtime-acceptance` and block nothing here. **A-13**: the two values are a data-plane change (a member value of a result stored in the end line of `events.ndjson`), but the owner approved exactly these two in the HQ-0020 answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6183004538: "One each: `build_exit_status` for S7 and `build_time_limit` for S8."), and ADR-0060 "adds those two values and nothing else of the data plane" (line 158). So the A-13 "data-plane schema change" reason does not apply to this task as long as nothing beyond these two values is added. Code may follow an accepted record inside its objection window (as T-0180 after ADR-0058, T-0185 after ADR-0059); an objection reverts both. No `claude` process, board or API key is needed (D16).

## Required Reading

Line numbers are those of `main` at `0d89b20`; the text wins. Read long ARCHITECTURE lines with `fold` or `cut`. Read Python with `PYTHONIOENCODING=utf-8`.

- **PROCESS/DRIVER.md §3-5** (line 72: executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (lines 86-114: task format, naming, trailers, size cap D4, **test rules ① to ⑤ at line 113**, language line at 112).
- CLAUDE.md, the whole file; above all "개발 드라이버와 런타임의 구분", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙", "코멘트 최소화".
- .claude/skills/dev-item-address/SKILL.md (code mode); .claude/skills/dev-code-review/SKILL.md.
- **ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md**: Status (3-14), **decision 4 (68-102)** - above all lines 70-83 (the two values, form (B) as "one of four strings", the six-row order table and "Why there"), decision 6 (109-120), **Consequences (153-160)**: line 155 (slice (1)), line 157 ("Not edited and now less exact", the code docstrings named there), line 158 (A-13 reading).
- ARCHITECTURE/decisions/ADR-0042-od18-correctness-check-result-members.md decision 3 (46-61) and decision 7 (105-131): the `condition` table and the member list ADR-0060 amends.
- ARCHITECTURE/decisions/ADR-0043-od18-correctness-check-operation-form.md decision 4 (75-92) and decision 5 (93-105): form (B) and an answer of neither form.
- ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md decision 6 (85-93): what the message of `operation_answer_invalid` may say (the wording is the code's).
- ARCHITECTURE/decisions/ADR-0021-od18-correctness-check-split.md decisions 2 and 5 (the order of the run conditions; `Broken` stays the four conditions of a completed run).
- **hilclaw/check_result.py** (193 lines), **hilclaw/check_answer.py** (115), **hilclaw/check_judging.py** (184; `_CONDITIONS` at line 58), hilclaw/check_operation.py (227; `_RETURNED` at 81-83, `OperationAnswerInvalid` docstring at 121-135), hilclaw/check_ending.py lines 1-40, hilclaw/harness/verification.py lines 98-105 (`Broken`), hilclaw/mock_check.py lines 115-135.
- Their tests: tests/test_check_result.py (158-159, 519, 546), tests/test_check_answer.py (222, 378), tests/test_check_judging.py (145-165), tests/test_check_tool.py (392, 443-455, 884), tests/test_mock_check.py (around 147), tests/test_check_operation.py, tests/test_check_ending.py.

## Acceptance Criteria

### `hilclaw/check_result.py`

- `CONDITIONS` holds exactly six values in the order of ADR-0060 decision 4: `("build_time_limit", "build_exit_status", "time_limit", "exit_status", "report_form", "check_value")`. Still a `tuple`.
- `broken(...)` accepts each of the six and refuses any other `str` with `ValueError` as today (its docstring's "none of the four values" corrected). No member, default or other value is added; `completed` is unchanged.
- The module docstring names ADR-0060 decision 4 as the amendment of ADR-0042 decision 3 (one line, no re-telling).

### `hilclaw/check_answer.py`

- Form (B) is **one of four strings**: `"time_limit"`, `"exit_status"`, `"build_time_limit"`, `"build_exit_status"` (ADR-0060 decision 4, amending ADR-0043 decision 4). Each becomes `check_result.broken(answer, ...)` without judging, `seed` neither used nor checked, as for the first two today.
- `"report_form"` and `"check_value"` stay **neither form** (`NeitherFormError`), as does every other `str`, a near-miss spelling included.
- The set of form-(B) strings is no longer taken as `CONDITIONS[:2]` (that slice would now give the two build values only). How the code names the set is the executor's choice (for example the four values found by the operation, `CONDITIONS[:4]`, or an explicit tuple checked against `CONDITIONS`), with the reason in the commit body. The `NeitherFormError` message still lists the admitted strings.
- Module, class and function docstrings: "two strings" → the four strings, citing ADR-0060 decision 4.

### `hilclaw/check_judging.py`

- `condition_of` still maps the four members of `verification.Broken` to `"time_limit"`, `"exit_status"`, `"report_form"`, `"check_value"` - unchanged values - but no longer by a positional `zip` with the whole of `CONDITIONS` (which would now pair `Broken.TIMEOUT` with `"build_time_limit"` or fail `strict=True` at import). The executor chooses the pairing (for example by position with the last four items, or explicitly by name) and states it in the module docstring's "own choices" item, which today says the four members and four values are paired by position.
- `Broken` in `hilclaw/harness/verification.py` is **not** changed: the two build values are found by an operation and never by `judge_report` (ADR-0060 decision 4 table, "Found by").

### `hilclaw/check_operation.py` and `hilclaw/check_ending.py`

- The message of `operation_answer_invalid` for a returned value of neither form no longer says "one of the two conditions" (it is now four). The wording is the code's (ADR-0045 decision 6); it still shows nothing of the answer beyond the name of its type.
- The `OperationAnswerInvalid` docstring and `check_ending.py` line 10 ("a report or one of the two conditions") are corrected to match. No other change in these two modules.

### Tests (CLAUDE.md test rule; DRIVER §5 line 113)

- Update the existing assertions that pin four values / two strings (test_check_result 158-159 and 519, test_check_answer 222 and 378, test_check_judging 162, and any message text in test_check_operation / test_check_ending).
- Happy: `broken` with each of the six values gives `outcome` `broken` with that `condition`, `shape`, `draws`, `tolerance` and no `counts`; `from_answer` with `"build_time_limit"` and `"build_exit_status"` gives that broken result and does not check `seed` (an invalid seed beside them is not refused); through the tool, a mock script returning each of the two new strings gives the broken result with that `condition` (extend the parametrization at test_check_tool line 443) and a repeated call answers the stored result.
- Branch: `condition_of` over all of `Broken` still gives the four run conditions in order, and none of them is a build value.
- Negative: `"report_form"`, `"check_value"`, `"build_time_limit "`, `"BUILD_EXIT_STATUS"`, `"build_exit"`, `"build_status"` and a `str` subclass holding a new value are neither form; `broken` refuses a near-miss of a new value with `ValueError` and a non-`str` with `TypeError`; the `operation_answer_invalid` message for a returned `str` shows no part of it.
- `hilclaw/` line and function coverage stay ≥ 80% (CI gate). ruff check and format clean.

### Process

- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0187'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0187 --state all`. Then `gh pr list --repo myungjoo/HIL-Claw --state open`: an open PR touching a file of `touchesFiles` makes the task BLOCKED ("open PR conflict"); none was open at planning time.
- Read the comments on issue #5 after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6184597227 (the ADR-0060 notice). Skip comments ending `— posted by driver`. An owner comment that objects to ADR-0060 decision 4 (the order, the class of S7/S8, or the reading of a signal as S7) makes the task BLOCKED ("requirement-unclear"); quote it. An answer to HQ-0013, HQ-0014, HQ-0016..HQ-0019 does not stop this task; name it in `## Result`.
- **Guarded exit**: add no value, member, kind or file of the data plane beyond the two values (A-13). If the change seems to need one, stop and return BLOCKED ("data-plane-schema-change") with the question written for an HQ.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Nothing here needs it. Tell each reviewer to write no file and start no `claude` process.
- **Code mode** (CLAUDE.md A-13): branch `claude/T-0187-check-build-condition-values` from `origin/main`; Draft PR titled with `T-0187`; reviewer cycle with a fresh-context `dev-reviewer` each round (at most 7 rounds; past the cap without Approve: BLOCKED; a result starting with `SECURITY`: BLOCKED; if no reviewer can be spawned: BLOCKED, do not review your own work). Ask the reviewer to check the six values and their order against ADR-0060 decision 4, that form (B) is exactly the four strings, that `Broken` still maps to the four run conditions, and that nothing else of the data plane changed. CI green on all jobs before merge; `gh pr merge --squash --body` with the PR body whose last line is `Task: T-0187`; delete the branch.
- Commit messages in English; executor commits end with the trailer `Task: T-0187` and any attribution trailer the session requires; the commit body has one line on the language (Python, as the package) and the reasons for how form (B) and the `Broken` pairing are named.
- **Prohibitions**: never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around. If the task-branch push is rejected, rebase and retry once, then BLOCKED (`branch-contention`). Past 2h30m of wall-clock time, return BLOCKED (`task-timeout`) with the state in `## Result`.
- **`## Result`**: fill it in on `main` after the merge and leave it uncommitted for the driver (DRIVER §3-6): PR and merge commit, review rounds, CI run, coverage, the choices made, the language line, follow-ups. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters.

## Out of Scope

- Slice (2): the six backend kinds in `hilclaw/check_failure.py` `BACKEND_KINDS` (next task).
- The operation of `cpu_standin` for `correctness.check`, mapping `BuildResult` or raised errors to rows, the compiler's log file, any setting value, the container, the tool's registration (blocked on OD-14, OD-18 ⑱ (나)(라)(마); ADR-0060 Consequences).
- `hilclaw/harness/verification.py` (`Broken`), `hilclaw/mock_check.py` (its "never one of the two strings" docstring line may be noted as a follow-up only), `hilclaw/check_failure.py`, `hilclaw/harness/verification_build.py`.
- Any ARCHITECTURE, PLAN, DRIVER, README or `.claude/` edit; the "now less exact" ADR sentences of ADR-0060 Consequences.

## Follow-ups

- (planner, code mode, next) ADR-0060 slice (2): the six kinds `build_directory_unusable`, `settings_refused`, `build_input_missing`, `compiler_unavailable`, `build_output_missing`, `executable_unstartable` in `hilclaw.check_failure.BACKEND_KINDS`, with the module and `check_ending.py` docstrings ("today one of the two of ADR-0056 decision 6") and tests.
- (planner, document mode, small) The R7 nits of T-0176 on ADR-0060 (T-0176 Follow-ups).
- (planner, document mode, §9) The run-tool contracts of PLAN P1-1, taking the build answers from ADR-0060 and O3.

## Result

- **Outcome**: DONE. PR https://github.com/myungjoo/HIL-Claw/pull/130, squash-merged as `2c58b93` (branch deleted). Commits on the branch: `070a2a2`, `2d6f3f1`.
- **Landed check / entry checks**: no `Task: T-0187` commit, no PR, no open PR at start; no comment on #5 after the ADR-0060 notice (no objection, no HQ answer).
- **Review**: 2 rounds, fresh-context `dev-reviewer` each (R1 Approve with 3 nits: the 97-character `_RETURNED` line wrapped; the two build strings added to the pass-through test of `tests/test_mock_check.py`; the `hilclaw/mock_check.py` "two strings" docstring left out of scope, see follow-ups. R2 Approve, no findings).
- **CI**: run 38684090723 on `2d6f3f1`, all jobs green (Python 3.11/3.14, coverage, C, sh, test presence). Local: ruff check/format clean; 19239 passed, 354 skipped; `hilclaw/` line coverage 99%, functions 583/587.
- **Choices**: form (B) is `check_result.CONDITIONS[:4]` (in the amended table the first four values are exactly those found by the operation, so one source of the values remains and the `NeitherFormError` message lists them); `check_judging` pairs `verification.Broken` with `CONDITIONS[-4:]` by position (both in ADR-0021 decision 5 order; the build values stand for no member). `Broken` unchanged. The `operation_answer_invalid` message now says "one of the four conditions". Nothing else of the data plane changed.
- **Language**: Python, as the rest of the `hilclaw` package.
- **Follow-ups**: (code mode, small, may join slice (2)) the `hilclaw/mock_check.py` `default_script` docstring "never one of the two strings of ADR-0043 decision 4" is now less exact (four strings since ADR-0060 decision 4).
