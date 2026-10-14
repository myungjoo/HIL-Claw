---
id: T-0178
title: Make case 3 of the ask() docstring in check_operation.py say plainly which part is this module's own choice and which is the rule of ADR-0047
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: [T-0177]
touchesFiles: [hilclaw/check_operation.py]
estimatedSize: {loc: 8, files: 1}
hq: []
---
## Why

T-0177 (PR #123, squash commit 50f6b7e) brought the module docstring of `hilclaw/check_operation.py` in line with ADR-0047. Its `## Result` left one follow-up outside the module docstring. The `ask` docstring, case 3 (lines 190-191 on `main` at 6a1ff6e), reads:

> 3. It raised a ``ToolFailure``, of any kind: the same object is handed on. No record gives this a rule (see the module docstring).

The sentence "No record gives this a rule" is still true if "this" means handing the same object on, because that is this module's own choice. But a reader can take "this" to mean the whole treatment of a raised tool failure. A record now gives that a rule: ADR-0047 decisions 3 to 5 say the step is ended with a `failure`, and `hilclaw.check_ending.carry_out` renders that rule outside this function. The module docstring now says both halves (the bullet at lines 46-55). Case 3 should say plainly that the handing on is this module's own choice, and point to the module docstring for the rule the tool function follows. It should not restate that rule.

This is small cleanup that depends on no open HQ. The substantive P1-1 work (OD-18 sub-question ⑰ (가) and (나); T-0176) waits on HQ-0020, and this task does not touch it. Planner's choice over the other journal idea: the "now less exact" sentences that ADR-0047 lists in ADR-0040, ADR-0043, ADR-0044 and ADR-0045, and those ADR-0053 lists, are filed in those records as follow-ups for the integrator. T-0174 judged the ADR-0053 list "not this driver task's" and said that editing a dozen accepted records goes well beyond a nit. So this task leaves them out.

## Required Reading

- `PROCESS/DRIVER.md` §3-5: executor procedure, resume rule, the 2h30m limit.
- `PROCESS/DRIVER.md` §5: task format, naming convention `claude/T-0178-*`, the `Task: T-0178` trailer, size cap D4, D12 test rules.
- `CLAUDE.md` "상시 규칙": comment minimisation, the A-13 branch/merge procedure (code mode), the test rules (D12), the language policy, "개발 드라이버와 런타임의 구분".
- `hilclaw/check_operation.py`:
  - lines 1-80 (module docstring, especially the bullet at lines 46-55 that T-0177 wrote);
  - lines 158-205 (`ask` and its docstring).

  Edit only what the acceptance criteria name.
- `hilclaw/check_ending.py` lines 1-78 (module docstring, read only). It is the place where `ask` and `check_failure.ended_with` are joined.
- `ARCHITECTURE/decisions/ADR-0047-od18-correctness-check-operation-tool-failure.md`: Status (lines 3-15) and decisions 3 to 5. Read only.
- `PROCESS/tasks/T-0177-check-operation-decision-8-sentence.md` `## Result`: the last bullet, which states the follow-up.
- `tests/test_check_operation.py`: check whether any test reads the module's source or docstring text. A docstring edit must keep every such test true.

## Acceptance Criteria

### The edit (docstring of `ask` only; no code line, signature, constant, message or import changes)

1. **Case 3 of the `ask` docstring.** It keeps the behaviour: a raised `ToolFailure` of any kind is handed on as the same object. Replace "No record gives this a rule (see the module docstring)" with wording that makes two points:
   - handing the object on is this module's own choice;
   - what the tool function then does with it is in the module docstring (ADR-0047).

   At most two short sentences. Do not restate ADR-0047's rule or the names of the backend kinds here, since the module docstring already holds them. If you cite ADR-0047, cite only what it says.
2. **No other sentence** of the `ask` docstring or of the module docstring changes, unless the new case 3 makes it contradictory. If you change one, list it in `## Result` with its old and new text.
3. Decide nothing new: no rule for another HW tool, no new kind, nothing about recovery or retry (OD-10), and nothing that HQ-0020 asks (the class of a failed or timed-out build).
4. Comment minimisation: the docstring documents a public function, so it is boilerplate and may be complete. Do not let case 3 grow beyond the other cases.

### Tests (CLAUDE.md test rules, D12)

- This change has no behaviour of its own, so no new test is required. The module keeps its existing tests with happy, error, branch and negative cases, which cover every public name (`ask`, `OperationAnswerInvalid`, the constant). If a test asserts on docstring text that you change, update that assertion, keep it as strong, and say so in `## Result`.
- Add no test that targets test code, the CI workflow or a script (rule 5).

### Gates

- `python -m pytest` passes locally. `python -m ruff check .` and `python -m ruff format --check .` exit 0.
- CI is green on the PR in all six jobs. Coverage of `hilclaw/` stays at line ≥ 80% and function ≥ 80%; take the figures from the CI gate. The `coverage` module is not installed on the driver machine, and it must not be added to the dependencies.
- `git diff --stat origin/main` lists only `hilclaw/check_operation.py`.
- `git ls-files --eol` shows `i/lf` for it, and `git diff --check` is clean.
- No code line changed: `git diff -U0` shows only lines inside the `ask` docstring, plus any lines inside the module docstring under point 2.

### Process

- Work only in the driver's dedicated clone.
- First run the §3-5 landed check: `git log origin/main --grep='^Task: T-0178'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0178 --state all`.
- Then run `gh pr list --repo myungjoo/HIL-Claw --state open`. An open PR that touches `hilclaw/check_operation.py` makes the task BLOCKED ("open PR conflict"). There was no open PR at planning time (2026-10-14T09:31Z).
- Read the comments on issue #5 after `https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6164154089` (the HQ-0020 mirror). Skip the driver's own comments (those ending `— posted by driver`).
  - If an owner comment objects to ADR-0045, ADR-0047 or ADR-0056, the task is BLOCKED ("requirement unclear"); quote the comment.
  - An answer to HQ-0013, HQ-0014, HQ-0016, HQ-0017, HQ-0018, HQ-0019 or HQ-0020 does not stop this task; name it in `## Result`.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Tell each reviewer to write no file and to start no `claude` process.
- **Branch and PR.** Code mode (A-13): create branch `claude/T-0178-check-operation-ask-case-3` from `origin/main`. Open a Draft PR with `T-0178` in its title and `Task: T-0178` as the last line of its body.
- **Review cycle.** Use the dev-item-address reviewer cycle with a fresh-context `dev-reviewer` each round, at most 7 rounds.
  - A result that starts with `SECURITY` makes the task BLOCKED.
  - If no reviewer can be spawned, the task is BLOCKED; do not review your own work.
  - Ask the reviewer to check the new case 3 word by word against:
    - the code of `ask`;
    - the module-docstring bullet at lines 46-55;
    - ADR-0047 Status and decisions 3 to 5.
  - Ask the reviewer to confirm that no code line changed and that nothing was invented.
- **Merge.** When the last review is an Approve and CI is green on the head:
  - squash-merge with `gh pr merge --squash --body` so that the squash message ends with `Task: T-0178`;
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
  - the old and new text of case 3, and of any sentence changed under point 2;
  - follow-ups.

  `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters.

## Out of Scope

- Any code line, test behaviour or new module.
- Every module other than `hilclaw/check_operation.py`, including `check_failure.py`, `check_ending.py`, `check_tool.py`, `check_seed.py`, `check_identity.py` and `mock_check.py`.
- Any ARCHITECTURE document, README, PLAN, DRIVER.md and CLAUDE.md. That includes the "now less exact" sentences that ADR-0047 lists (ADR-0021, ADR-0040, ADR-0041, ADR-0043, ADR-0044, ADR-0045, ADR-0046) and those of ADR-0050, ADR-0052 and ADR-0053, which are integrator follow-ups.
- OD-18 sub-question ⑰ (가) and (나), the class of a failed or timed-out build, and the run-tool contracts (HQ-0020; T-0176; PLAN P1-1, OD-13 sub-question ⑩).
- What anybody does after a tool failure (OD-10; the retry part of OD-17).

## Follow-ups

- (driver/planner) T-0176 stays BLOCKED until HQ-0020 is answered.
- (integrator, document mode) The "now less exact" sentences that ADR-0047 Consequences lists in ADR-0021 and ADR-0040 to ADR-0046, and those that ADR-0053 Consequences lists.

## Result
