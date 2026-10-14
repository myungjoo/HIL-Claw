---
id: T-0177
title: Bring the module docstring of check_operation.py in line with ADR-0047 on a tool failure an operation raises
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: [T-0159, T-0175]
touchesFiles: [hilclaw/check_operation.py]
estimatedSize: {loc: 15, files: 1}
hq: []
---
## Why

T-0159 `## Result` noted a stale sentence, and T-0175 and T-0176 `## Follow-ups` carried it forward unfixed. The sentence is in the module docstring of `hilclaw/check_operation.py`, lines 46-49, in "Choices that are this module's own and no rule of a record":

> A :class:`hilclaw.tools.ToolFailure` an operation raises is handed on as the same object. That is no rule of a record: what a tool function does with a tool failure an operation raises is open (decision 8; OD-18 sub-question 10, third clause), and nothing here decides it.

"Decision 8" here is ADR-0045 decision 8. It became less exact when ADR-0047 landed: ADR-0047 decides what the tool function does with a tool failure an operation raises, whatever its kind. The step is ended with a `failure`. That `failure` holds the raised kind and message where the kind is a backend kind, and otherwise the tool's own kind `operation_failure_invalid` (ADR-0047 decisions 3 to 5; Status: "Closes a part of the third clause of sub-question ⑩ of OD-18"). ADR-0056 decision 6 names the two backend kinds. The code on `main` renders this: `hilclaw/check_failure.py` (`ended_with`, `BACKEND_KINDS`) and `hilclaw/check_ending.py` (`carry_out`), which joins `check_operation.ask` and `check_failure.ended_with`. Two things are still true:

- handing the raised object on as the same object is this module's own choice;
- which further kinds a later record names stays open (ADR-0047 Status).

The task is small, self-contained cleanup that depends on no open HQ. The substantive P1-1 work (OD-18 sub-question ⑰ (가) and (나), the run-tool contracts) waits on HQ-0020 (T-0176, BLOCKED). This task does not touch that question.

## Required Reading

- `PROCESS/DRIVER.md` §3-5: executor procedure, resume rule, the 2h30m limit.
- `PROCESS/DRIVER.md` §5: task format, naming convention `claude/T-0177-*`, the `Task: T-0177` trailer, size cap D4, D12 test rules.
- `CLAUDE.md` "상시 규칙": comment minimisation, the A-13 branch/merge procedure (code mode), the test rules (D12), the language policy, "개발 드라이버와 런타임의 구분".
- `hilclaw/check_operation.py` lines 1-69 (module docstring). Edit only what the acceptance criteria name.
- `hilclaw/check_failure.py` lines 1-75 and `hilclaw/check_ending.py` lines 1-78 (module docstrings). Read only, as the model for how the landed modules cite ADR-0047 and ADR-0056; do not edit them.
- `ARCHITECTURE/decisions/ADR-0047-od18-correctness-check-operation-tool-failure.md`:
  - Status, the bullets "Closes ..." and "No sentence of an earlier record is replaced" (which lists ADR-0045 decision 8 as now less exact);
  - decisions 3 to 5;
  - Limits.
- `ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md` decision 8 (lines 100-106), the decision the stale sentence cites.
- `ARCHITECTURE/decisions/ADR-0056-od18-correctness-check-verification-executable.md` decision 6 (the two backend kinds). Read only.
- `PROCESS/tasks/T-0159-check-failure-backend-kinds.md` `## Result`, the paragraph on docstring sentences of unedited modules that are now less exact (the `check_operation.py` bullet).
- `tests/test_check_operation.py`: check whether any test reads the module's source or docstring text (for example a check on imports or on kept-out strings). A docstring edit must keep every such test true.

## Acceptance Criteria

### The edit (docstring only; no code line, signature, constant, message or import changes)

1. **The bullet at lines 46-49.** It stays in the list of "Choices that are this module's own". It says that:
   - handing a raised `ToolFailure` on as the same object is this module's own choice, and no rule of a record;
   - what the tool function then does with it is the rule of ADR-0047: the step is ended with a `failure`, of the raised kind for a backend kind and otherwise of `operation_failure_invalid`. Cite the decisions you rely on, and only for what they say.
   - Say where the code renders it (`hilclaw.check_failure.ended_with`, joined with `ask` in `hilclaw.check_ending.carry_out`), in at most one short clause.

   Drop the claim "is open (decision 8; OD-18 sub-question 10, third clause), and nothing here decides it". If you keep a mention of what remains open (which further kinds a later record names), it must match ADR-0047 Status.
2. **The last paragraph** ("What the module does not do"). The clause "nor of what a tool function does with a tool failure an operation raises" may stay as it is, since the module still says nothing of it. Edit it only if the new bullet makes it contradictory or repetitive, and keep it true of this module.
3. **Further sentences.** Search the module docstring for any other sentence that calls undecided something ADR-0047 or ADR-0056 decision 6 decided. Fix each one the same way and list it in `## Result`. Edit no other module and no ARCHITECTURE document.
4. Every edited sentence must be exact against the code on `main` and against the cited records. Decide nothing new: no rule for another HW tool, no new kind, nothing about recovery or retry (OD-10), and nothing that HQ-0020 asks (the class of a failed or timed-out build).
5. Keep comment minimisation in mind. The docstring is the module boilerplate, so a sentence or two is fine, but do not grow the bullet into a paragraph.

### Tests (CLAUDE.md test rules, D12)

- This change has no behaviour of its own, so no new test is required. The module keeps its existing tests with happy, error, branch and negative cases, which cover every public function (`ask`, the class, the constant). If a test asserts on docstring text that you change, update that assertion, keep it as strong, and say so in `## Result`.
- Add no test that targets test code, the CI workflow or a script (rule 5).

### Gates

- `python -m pytest` passes locally. `python -m ruff check .` and `python -m ruff format --check .` exit 0.
- CI is green on the PR in all six jobs. Coverage of `hilclaw/` stays at line ≥ 80% and function ≥ 80%; take the figures from the CI gate. The `coverage` module is not installed on the driver machine, and it must not be added to the dependencies.
- `git diff --stat origin/main` lists only `hilclaw/check_operation.py`. `git ls-files --eol` shows `i/lf` for it, and `git diff --check` is clean. No code line changed: `git diff -U0` shows only lines inside the module docstring. Rewrapping the edited paragraph is fine; leave the words outside the edited sentences unchanged.

### Process

- Work only in the driver's dedicated clone.
- First run the §3-5 landed check: `git log origin/main --grep='^Task: T-0177'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0177 --state all`.
- Then run `gh pr list --repo myungjoo/HIL-Claw --state open`. An open PR that touches `hilclaw/check_operation.py` makes the task BLOCKED ("open PR conflict").
- Read the comments on issue #5 after `https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6160644223`. Skip the driver's own mirror comments (those ending `— posted by driver`).
  - If an owner comment objects to ADR-0045, ADR-0047 or ADR-0056, the task is BLOCKED ("requirement unclear"); quote the comment.
  - An answer to HQ-0013, HQ-0014, HQ-0016, HQ-0017, HQ-0018, HQ-0019 or HQ-0020 does not stop this task; name it in `## Result`.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Tell each reviewer to write no file and to start no `claude` process.
- **Branch and PR.** Code mode (A-13): create branch `claude/T-0177-check-operation-decision-8-sentence` from `origin/main`. Open a Draft PR with `T-0177` in its title and `Task: T-0177` as the last line of its body.
- **Review cycle.** Use the dev-item-address reviewer cycle with a fresh-context `dev-reviewer` each round, at most 7 rounds.
  - A result that starts with `SECURITY` makes the task BLOCKED.
  - If no reviewer can be spawned, the task is BLOCKED; do not review your own work.
  - Ask the reviewer to check each edited sentence word by word against the code (`check_operation.py`, `check_failure.py`, `check_ending.py`) and against ADR-0047 Status and decisions 3 to 5, ADR-0045 decision 8 and ADR-0056 decision 6.
  - Ask the reviewer to confirm that no code line changed and that nothing was invented.
- **Merge.** When the last review is an Approve and CI is green on the head:
  - squash-merge with `gh pr merge --squash --body` so that the squash message ends with `Task: T-0177`;
  - delete the branch;
  - check out `main` at `origin/main`.
- Commit and PR text are in English. Record the language in one line: Python, existing module.
- **CI failures.** Three consecutive failing runs make the task BLOCKED (`ci-3-consecutive-failures`). A run that starts no job (the HQ-0015 pattern) counts as a failure and is reported; do not re-run it in a loop.
- **Prohibitions.**
  - Never use `git push --force*` or `-f`, never a recursive forced remove, never `gh repo delete`.
  - Do not edit `.claude/settings.json` or `.claude/settings.local.json`.
  - A denied or failed tool call makes the task BLOCKED; do not work around it.
  - If the task-branch push is rejected, rebase and retry once, then BLOCKED (`branch-contention`).
  - Past 2h30m of wall-clock time, return BLOCKED (`task-timeout`) with the state written into `## Result`.
- **`## Result`.** Fill it in on `main` after the merge and leave it uncommitted for the driver (DRIVER §3-6). Record:
  - the PR and the squash commit;
  - the review rounds;
  - the CI result and the coverage figures;
  - the old and new text of each edited sentence;
  - any further sentence found under point 3;
  - follow-ups.

  `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters.

## Out of Scope

- Any code line, test behaviour or new module.
- Every module other than `hilclaw/check_operation.py`, including `check_failure.py`, `check_ending.py`, `check_tool.py`, `check_seed.py` and `mock_check.py`.
- Any ARCHITECTURE document, README, PLAN, DRIVER.md and CLAUDE.md. That includes the "now less exact" sentences of ADR-0043, ADR-0045 and ADR-0040 that ADR-0047 lists, and those of ADR-0050, ADR-0052 and ADR-0053 (integrator follow-ups).
- OD-18 sub-question ⑰ (가) and (나), the class of a failed or timed-out build, and the run-tool contracts (HQ-0020; T-0176; PLAN P1-1, OD-13 sub-question ⑩).
- What anybody does after a tool failure (OD-10; the retry part of OD-17).

## Follow-ups

- (driver/planner) T-0176 stays BLOCKED until HQ-0020 is answered. After that come the new kinds and any new `condition` value in code, then the operation of `cpu_standin` for `correctness.check` (T-0176 Follow-ups).
- (integrator, document mode) The "now less exact" sentences that ADR-0047 lists (ADR-0043 decision 6, ADR-0045 Status/decisions 4 and 8/Walk-through, ADR-0040), and those of ADR-0050, ADR-0052 and ADR-0053 (T-0175 Follow-ups).

## Result

- DONE. PR #123 squash-merged as 50f6b7e (branch deleted). Review: 1 round, Approve (one Nit, no change needed: the bullet states the ADR-0047 rule; the `str` check of the message is `check_failure`'s own choice). CI green in all six jobs on 4a694c8; coverage of `hilclaw/`: lines 99.62% (5002/5021), functions 100% (492/492). Local: pytest 18605 passed / 351 skipped; ruff check and format clean; diff is docstring-only in `hilclaw/check_operation.py`, `i/lf`.
- Bullet, old: "That is no rule of a record: what a tool function does with a tool failure an operation raises is open (decision 8; OD-18 sub-question 10, third clause), and nothing here decides it."
- Bullet, new: "That is no rule of a record. What the tool function then does with it is the rule of ``ADR-0047``: the step is ended with a ``failure`` (its decision 3), which holds the raised kind and message for a backend kind and otherwise the tool's own kind ``operation_failure_invalid`` (its decisions 4 and 5). The code gives that kind and message with `check_failure.ended_with`, joined with `ask` in `check_ending.carry_out`."
- Last paragraph, old: "..., nor of what a tool function does with a tool failure an operation raises." New: "..., and it does not render what a tool function does with a tool failure an operation raises." (edited because the bullet now states that rule).
- Point 3: no other module-docstring sentence called something undecided that ADR-0047 or ADR-0056 decision 6 decides. No test asserts on the edited text. Issue #5: no owner comment after 6160644223 (only the driver's HQ-0020 mirror); no HQ answered.
- Follow-up (outside the module docstring, so not edited): the `ask` docstring, case 3, says "No record gives this a rule (see the module docstring)". It is still true if "this" means handing the object on, but a later task could make it say so plainly.
