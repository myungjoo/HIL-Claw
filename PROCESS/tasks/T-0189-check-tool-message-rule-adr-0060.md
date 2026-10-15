---
id: T-0189
title: Bring the `hilclaw/check_tool.py` sentence on what a backend kind's message may show in line with ADR-0060 decision 5
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, OD-18, "#5 D12"]
dependsOn: [T-0176, T-0188]
touchesFiles: [hilclaw/check_tool.py]
estimatedSize: {loc: 8, files: 1}   # docstring sentences only; no code line, no test file expected
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts, `correctness.check` included) is open. T-0188 (PR #131, `1a3abf5`) added the six build backend kinds of ADR-0060 decision 4 to `hilclaw.check_failure.BACKEND_KINDS`. Its `## Result` names one sentence in an unedited module that the change made less exact, and its reviewer R1 found it:

> `hilclaw/check_tool.py` module docstring, "By the records such a message shows no path (ADR-0056 decision 6)" - true of the two kinds of ADR-0056 only; the message rule of the six is ADR-0060 decision 5.

State of `main` at `3ba76c5`: `hilclaw/check_tool.py` (180 lines), module docstring lines 61-66: "The end line holds the message of a backend kind an operation raised, where it is exactly a ``str``, as it was raised (ADR-0047 decision 4), so a path or a seed in that message reaches ``events.ndjson``. By the records such a message shows no path (ADR-0056 decision 6) and has no content that holds the seed (ADR-0047 decision 4, citing ADR-0021 decision 3); nothing detects a message that breaks this."

Since ADR-0060 a backend kind is one of eight. The two of ADR-0056 have their message rule in ADR-0056 decision 6 ("It shows no path, no name of an entry, no byte of a file and no text of an error"). The six of ADR-0060 have theirs in ADR-0060 decision 5 ("It shows no path, no name of an entry, no byte of a file, no text of an error, no value of a setting and no part of the compiler's log"; "A message that breaks this is not detected"). The sentence cites only the first record. This task cites both, which makes it exact again. It is a docstring-only change of a `hilclaw/` module, so code mode (precedent: T-0175).

It ticks **no PLAN checkbox** (P1-1 stays open) and changes no OD.

Planner's judgements (the reviewer is asked to re-check each):
- **No undecided design.** Both message rules are quoted from landed records. The sentence only describes them; no code checks a message (both records: "not detected").
- **A-13 (data plane)**: nothing of the data plane changes; no code line changes.
- **D16**: nothing here needs the `claude` program, a compiler, a container runtime, a board or an API key.
- **Other modules checked by the planner (2026-10-15, `main` at `3ba76c5`)**: `hilclaw/check_seed.py` lines 73-78 speak only of the seed (ADR-0047 decision 4 citing ADR-0021 decision 3) and stay exact. `hilclaw/check_ending.py` line 66 ("whatever it shows") stays exact. `hilclaw/check_operation.py`, `check_failure.py`, `check_answer.py`, `check_result.py`, `check_judging.py` and `mock_check.py` were brought in line by T-0177, T-0187 and T-0188. The T-0175/T-0176 follow-up on the `check_operation.py` "decision 8 / sub-question ⑩, third clause" sentence was already closed by T-0177 (`50f6b7e`): that sentence is no longer in the module. Say so in `## Result` so that the follow-up is not carried on.
- **Session entry check (planner)**: `gh pr list --state open` is empty. No owner comment on issue #5 after the ADR-0060 notice (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6184597227) objects to ADR-0056, ADR-0047 or ADR-0060. HQ-0013, 0014, 0016..0019 are `runtime-acceptance` notices and block nothing. The task touches no `ARCHITECTURE/` file.

## Required Reading

Line numbers are those of `main` at `3ba76c5`; the text wins. Read long ARCHITECTURE lines with `fold` or `cut`. Read Python with `PYTHONIOENCODING=utf-8`.

- **PROCESS/DRIVER.md §3-5** (line 72: executor procedure, landed check, resume rule, `T-NNNN` naming, the 2h30m limit) and **§5** (lines 86-114: task format, naming and trailers, size cap D4, language line, test rules ① to ⑤). These are mandatory for every task (§6). Also read §1-5 (forbidden actions; a denied or failed tool call is BLOCKED) and the "BLOCKED 사유" paragraph after §3-7.
- CLAUDE.md, the whole file. Above all: "코멘트 최소화", "미결은 발명하지 않는다", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (code mode), "테스트 규칙".
- .claude/skills/dev-item-address/SKILL.md (code mode path); .claude/skills/dev-code-review/SKILL.md.
- ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md: decision 4 (lines 68-102; line 98, "Any backend may raise the six kinds ..."), **decision 5, first bullet (line 106)**, Consequences line 157 ("Not edited and now less exact").
- ARCHITECTURE/decisions/ADR-0056-od18-correctness-check-verification-executable.md decision 6, "The message" (line 124).
- ARCHITECTURE/decisions/ADR-0047-od18-correctness-check-operation-tool-failure.md decision 4 (lines 67-88; line 70 on what the message of a backend kind may hold).
- PROCESS/tasks/T-0188-check-failure-build-backend-kinds.md `## Result` ("Less exact sentences left in unedited modules").
- **Code to edit**: `hilclaw/check_tool.py`. Read the whole module docstring (lines 1-75) and the sentence at lines 61-66.
- **Code to read and not to edit**: `hilclaw/check_failure.py` (module docstring and the eight constants), `hilclaw/check_seed.py` (lines 66-82), `hilclaw/check_ending.py` (lines 15-25, 60-75).
- `tests/test_check_tool.py`: read it to confirm that no test asserts the docstring text. Do not edit it unless such an assertion exists.

## Acceptance Criteria

### The change
1. In the module docstring of `hilclaw/check_tool.py`, the sentence "By the records such a message shows no path (ADR-0056 decision 6) and has no content that holds the seed (ADR-0047 decision 4, citing ADR-0021 decision 3); nothing detects a message that breaks this." is made exact for all eight backend kinds:
   - it cites ADR-0056 decision 6 for the two kinds of that record and ADR-0060 decision 5 for the six of that record;
   - it keeps the seed clause (ADR-0047 decision 4, citing ADR-0021 decision 3);
   - it keeps "nothing detects a message that breaks this".
   The wording is the executor's. The sentence may say that the six's rule also excludes a value of a setting and any part of the compiler's log, as long as each statement is traceable to the record it cites. Keep it short (CLAUDE.md "코멘트 최소화").
2. Read the rest of the `check_tool.py` module docstring and the `tool_function` / `_perform` docstrings for any other sentence that ADR-0060 (the eight kinds, the six `condition` values, form (B) of four strings) made less exact, and bring it in line in the same way. Example: the sentence "It says nothing of flags or of time limits" (line 57) is still true of the module and stays. List each sentence you changed, and each you checked and left, in `## Result`.
3. **No code line changes.** No signature, constant, import, message or behaviour of `hilclaw/check_tool.py` changes. `git diff` shows changes inside docstrings only.

### Do not invent
- No new rule for a message, no check of a message, no wording of a message of any kind.
- No edit of any module other than `hilclaw/check_tool.py`. A less exact sentence found elsewhere is listed in `## Result` as a follow-up, not edited.
- No ARCHITECTURE, PLAN, DRIVER, README or `.claude/` edit.
- No new external dependency.
- **Guarded exit**: if making a sentence exact seems to need a decision that no record holds, stop and return BLOCKED (`requirement-unclear`). Quote the sentence and write the question for an HQ.

### Tests (CLAUDE.md test rules, D12; DRIVER §5)
- This is a docstring-only change. No new test is required. The existing tests of `hilclaw/check_tool.py` cover every public function of the touched module (rule ③) with happy, error, branch and negative cases. Confirm this in `## Result` by naming the test file and the tests of `tool_function`.
- No test targets test code, the CI workflow or a script (D12 rule ⑤).
- `hilclaw/` line and function coverage stay >= 80% (CI gate).

### Gates
- `python -m pytest` passes locally. `python -m ruff check .` and `python -m ruff format --check .` exit 0.
- CI is green on the PR, all jobs. Put the coverage figures from the CI gate in `## Result`.
- `git diff --stat origin/main` lists only `hilclaw/check_tool.py`. `git diff --check` is clean.

### Process
- Work only in the driver's dedicated clone. First run the §3-5 landed check: `git log origin/main --grep='^Task: T-0189'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0189 --state all`. Then run `gh pr list --repo myungjoo/HIL-Claw --state open`. An open PR that touches `hilclaw/check_tool.py` makes the task BLOCKED ("open PR conflict"). None was open at planning time.
- Read the comments on issue #5 after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6184597227 and skip comments ending `— posted by driver`. An owner comment that objects to ADR-0060 decision 5, ADR-0056 decision 6 or ADR-0047 decision 4 makes the task BLOCKED ("requirement-unclear"); quote it. An answer to HQ-0013, 0014, 0016..0019 does not stop this task; name it in `## Result`.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Reviewers are spawned with the session's own agent tool and told to write no file and to start no `claude` process.
- **Code mode** (CLAUDE.md A-13):
  - Branch `claude/T-0189-check-tool-message-rule` from `origin/main`.
  - Open a Draft PR with `T-0189` in its title and `Task: T-0189` as the last line of its body.
  - Run the reviewer cycle with a fresh-context `dev-reviewer` each round, given the PR and this task file's path. At most 7 rounds; past the cap without Approve: BLOCKED. A result starting with `SECURITY`: BLOCKED. If no reviewer can be spawned: BLOCKED; do not self-review.
  - Ask the reviewer to (a) check each edited sentence word for word against ADR-0056 decision 6, ADR-0060 decision 5 and ADR-0047 decision 4; (b) confirm that no code line changed; (c) look for any other less exact sentence in `hilclaw/check_tool.py`, and name any in other modules.
- **Merge**: when the last review is an Approve and CI is green on the head, run `gh pr merge --squash --body` with the PR body whose last line is `Task: T-0189` (then any attribution trailer the session requires). Delete the branch, then check out `main` at `origin/main`.
- **Commit and PR text**: write it in English. Executor commits end with the trailer `Task: T-0189`. The commit body has one line on the language (Python, as the rest of the `hilclaw` package; docstring only).
- **CI**: three consecutive failing runs are BLOCKED (`ci-3-consecutive-failures`). A run that starts no job counts as a failure and is reported, not worked around.
- **Prohibitions**: never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`. No edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around. A rejected push of the task branch: one rebase and one retry, then BLOCKED (`branch-contention`). Past 2h30m of wall-clock: write the state into `## Result` and return BLOCKED (`task-timeout`).
- **`## Result`**: fill it in on `main` after the merge and leave it uncommitted for the driver (DRIVER §3-6). Include:
  - the PR and the squash commit;
  - the review rounds and findings;
  - the CI run and coverage;
  - the language line;
  - the sentences changed and the sentences checked and left;
  - the closed state of the `check_operation.py` follow-up;
  - follow-ups.

  `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters (result, PR/commit, BLOCKED or not).

## Out of Scope

- The operation of `cpu_standin` for `correctness.check`. It stays blocked on OD-14 (setting values, container ①) and OD-18 ⑱ (나)(라)(마) (ADR-0060 Consequences).
- Any change to `hilclaw/check_failure.py`, `check_ending.py`, `check_seed.py`, `check_operation.py`, `check_answer.py`, `check_result.py`, `check_judging.py`, `mock_check.py`, `hilclaw/harness/`.
- The "now less exact" sentences of earlier ADRs listed in ADR-0060 Consequences (document mode; not edited by ADR rule).
- Anything HQ-0013, 0014, 0016..0019 ask.

## Follow-ups

- (planner, document mode, small; candidate for the next task) The R7 nits of T-0176 on ADR-0060 (T-0176 `## Result` Follow-ups): narrow `NotADirectoryError` in decision 4 to the output path only; give one line of reason why a wrongly typed setting is `settings_refused` while a wrongly typed argument the operation formed is `operation_answer_invalid`; make the Status list "Single sentences rest on" match References, or mark it as not exhaustive; optionally mention the keeping of the log (⑱ (나)) in the ⑥ row of decision 6.
- (planner, document mode, §9) The run-tool contracts of PLAN P1-1 (OD-13 sub-question ⑩), taking the build answers from ADR-0060 and O3.

## Result

- **Landed**: PR #132, squash commit `da4f83a` on `main`. Landed check before work: no commit `Task: T-0189` on `origin/main`, no PR for T-0189, no open PR at all. No comment on issue #5 after the ADR-0060 notice (so no objection and no HQ answer to name).
- **Review**: 1 round, fresh-context `dev-reviewer`, Approve. Findings: (Nit) "its" in "the six of its decision 4" refers to ADR-0060 while "it names" refers to ADR-0056 decision 6 - grammatically right, left as is; (Info) the setting value / compiler log exclusions of ADR-0060 decision 5 are not repeated, optional under AC 1 and the sentence speaks of path and seed only; (Info) CI was still running at review time; (Info) PR body ends with `Task: T-0189`. Reviewer confirmed word for word against ADR-0056 decision 6 (line 124), ADR-0060 decision 5 (first bullet), ADR-0047 decision 4 (line 70), that only docstring lines changed, and the planner's judgements.
- **CI**: run 38686824020 on head `eb29cf7`, all six jobs green (Python 3.11 / 3.14, Coverage, C, sh, Test presence). Coverage gate: lines 5211/5230 = 99.63%, functions 517/517 = 100.00%. Local: `python -m pytest` 19402 passed, 354 skipped; `ruff check` and `ruff format --check` exit 0; `git diff --check` clean; diff stat lists only `hilclaw/check_tool.py` (+2/-1).
- **Language line** (commit body): "Python, as the rest of the hilclaw package; docstring only."
- **Changed** (module docstring): "By the records such a message shows no path (ADR-0056 decision 6) and has no content ..." became "By the records such a message shows no path (ADR-0056 decision 6 for the two kinds it names, ADR-0060 decision 5 for the six of its decision 4) and has no content that holds the seed (ADR-0047 decision 4, citing ADR-0021 decision 3); nothing detects a message that breaks this."
- **Checked and left** (still exact under ADR-0060's eight kinds, six `condition` values, four strings of form (B)): the order of a call, items 1-7 (item 6 "(ADR-0056 decision 3)", item 7 "(ADR-0045 decision 3, ADR-0047 decision 3)"); item 3 "one of its four answers" (admission, ADR-0046); "It says nothing of flags or of time limits"; "It binds no source of seeds, no predicate, no backend, no table and no script"; "It names no kind, no `step` value and no member of its own, and composes the message of no tool failure"; "The end line holds the message of a backend kind an operation raised, where it is exactly a `str`, as it was raised (ADR-0047 decision 4), so a path or a seed in that message reaches `events.ndjson`"; the `tool_function` docstring ("the kind of the `failure` an end line holds", "returns the result of the check, a `dict` (ADR-0042)"). `_perform` has no docstring.
- **Tests**: no new test (docstring-only). `tests/test_check_tool.py` covers `tool_function`, the module's one public function: happy (`test_a_check_of_a_right_product_reports_pass_and_writes_two_lines`, `test_a_wrong_product_reports_fail`), branch (`test_a_condition_of_the_operation_reports_broken`, `test_an_ended_identity_is_answered_from_the_log_and_nothing_is_asked`, `test_a_backend_kind_a_script_raises_is_the_failure_of_the_end_line`), error and negative (`test_a_refused_request_is_invalid_request_before_anything_is_asked`, `test_building_refuses_each_bad_argument_in_the_stated_order`, `test_a_draw_that_yields_no_seed_is_seed_not_drawn_and_can_be_repeated`, `test_a_backend_kind_whose_message_shows_the_output_path_is_not_detected`). No test asserts the docstring text; `test_the_module_holds_what_it_joins_and_nothing_of_its_own` scans the source for some words, none of which the new text holds.
- **`check_operation.py` follow-up of T-0175/T-0176** ("decision 8 / sub-question ⑩, third clause" sentence): closed by T-0177 (`50f6b7e`); the sentence is no longer in the module. Not to be carried on.
- **Follow-ups**: none new. Reviewer found no less exact sentence in other modules (`check_failure.py` already cites "(ADR-0056 decision 6; ADR-0060 decision 5)"; `check_ending.py` lines 20 and 66 and `check_seed.py` lines 73-78 exact). The planner's follow-ups in `## Follow-ups` above stand.
