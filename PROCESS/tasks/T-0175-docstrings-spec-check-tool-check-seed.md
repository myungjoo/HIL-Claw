---
id: T-0175
title: Bring three stale docstring passages of spec.py, check_tool.py and check_seed.py in line with the landed code
phase: P1
status: DONE
commitMode: code
coversReq: [FR-2, OD-8, OD-18]
dependsOn: [T-0159, T-0168]
touchesFiles: [hilclaw/spec.py, hilclaw/check_tool.py, hilclaw/check_seed.py]
estimatedSize: {loc: 25, files: 3}
hq: []
---
## Why

Two follow-ups have been carried, unfixed, through many task files; both are docstring-only and need no decision.

1. **`hilclaw/spec.py`** (T-0168 / T-0174 follow-up). The module docstring lists, under "Not checked", "that ``task.objective`` is what the instance stated (ADR-0050 L2)". When ADR-0050 was written no record gave `instance.json` such a member. Since ADR-0053 and T-0168 (PR #117, `2eefb9d`), `instance.json` has the top-level member `objective`, and `hilclaw.instance.objective_of` reads it. Still, no module of `hilclaw/` compares a spec's `task.objective` with it. The sentence still holds but no longer tells the reader why: it should say that the instance's member exists and that nothing compares the two yet.
2. **`hilclaw/check_tool.py` and `hilclaw/check_seed.py`** (T-0159 `## Result`, "Docstring sentences of unedited modules that are now less exact"). Since ADR-0056 decision 6 and T-0159 (PR #108, `6a0e026`), an operation may raise the backend kinds `no_kernel_source` and `kernel_source_unreadable`. The tool function writes the raised message to the end line in `events.ndjson` as it is (ADR-0047 decision 4). So these sentences are true only of what the module itself composes:
   - `check_tool.py` module docstring, around line 57: "and writes the path to no file and puts it in no message"
   - `check_tool.py` module docstring, around line 61: "It writes no seed anywhere and puts none in a message."
   - `check_seed.py` module docstring, around line 72: "it writes the seed to no file and puts it in no message"

   An operation that puts a path or a seed into a backend kind's message gets it into `events.ndjson` through these modules. ADR-0056 decision 6 forbids that message content but "A message that breaks this is not detected".

This is small, self-contained cleanup. The substantive P1-1 work (the run-tool contracts, OD-13 sub-question ⑩) and OD-18 sub-question ⑰ (가) wait on a question that probably needs the owner (see Follow-ups).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit 2h30m) and §5 (task format, naming convention `claude/T-0175-*`, `Task: T-0175` trailer, PR body last line, size cap, D12 test rules).
- `CLAUDE.md` "상시 규칙": comment minimisation, the A-13 branch/merge procedure (code mode), the test rules (D12), the language policy.
- `hilclaw/spec.py` lines 1-45 (module docstring). Edit only the sentence on ADR-0050 L2 (lines 24-31).
- `hilclaw/instance.py`: the module docstring paragraph on `objective` and `objective_of` (around line 1127). Read only; do not edit.
- `ARCHITECTURE/decisions/ADR-0053-od8-instance-record-objective.md`: decisions 3, 4 and 7 and Consequences line 153. ADR-0050 L2 is listed there as "now less exact"; the ADR is not edited here.
- `hilclaw/check_tool.py` lines 1-80 (module docstring).
- `hilclaw/check_seed.py` lines 55-85 (module docstring).
- `PROCESS/tasks/T-0159-check-failure-backend-kinds.md` `## Result`, the paragraph "Docstring sentences of unedited modules that are now less exact". It names the three sentences and gives the reading to apply: "this module composes no message that holds ...".
- `ARCHITECTURE/decisions/ADR-0047-od18-correctness-check-operation-tool-failure.md` decision 4 and `ARCHITECTURE/decisions/ADR-0056-od18-correctness-check-verification-executable.md` decision 6: what reaches the end line from a backend kind, and the message rule that is not detected.
- Tests that read the source text of these modules. A docstring edit must keep them true:
  - `tests/test_check_seed.py` around line 693, `test_the_text_and_the_code_hold_none_of_the_kept_out_strings`. The whole file text, docstrings included, must not contain `gemm_contract` or `standin_profile`.
  - `tests/test_check_tool.py` around line 991, `test_the_module_holds_what_it_joins_and_nothing_of_its_own` (imports only).

## Acceptance Criteria

### The edits (docstrings only; no code line, signature, constant or import changes)

1. **`hilclaw/spec.py`**: the "Not checked" item on ADR-0050 L2 stays in the list, and its sentence says that:
   - `instance.json` now has the member `objective` (ADR-0053; read by `hilclaw.instance.objective_of`);
   - this module does not read it;
   - no module of `hilclaw/` compares a spec's `task.objective` with it yet.

   Keep it to one or two sentences. Do not mention a check that does not exist, and do not suggest where such a check will live.
2. **`hilclaw/check_tool.py`**: change both sentences so that each claims only what this module composes or writes. Each must also say that the message of a backend kind raised by an operation is written to the end line as raised (ADR-0047 decision 4), so a path or a seed that such a message holds reaches `events.ndjson`. ADR-0056 decision 6 forbids that, and nothing detects it. Avoid repeating that clause twice; one shared sentence is fine.
3. **`hilclaw/check_seed.py`**: change the sentence the same way. This module composes no message that holds the seed and writes it to no file. `check` passes on, through `carry_out`, the message an operation raised.
4. In the same three module docstrings, look for any other sentence that states "puts ... in no message" or "writes ... to no file" for something an operation's message can carry. Fix any you find the same way, and list each in `## Result`. Edit no other docstring.
5. Every edited sentence must be exact against the code on `main` and against the cited records. Do not decide anything new: no rule on what a message may show beyond ADR-0056 decision 6, and no check or filter.

### Tests (CLAUDE.md test rules, D12)

- This change has no behaviour of its own, so no new test is required. The three modules keep their existing tests with happy, error, branch and negative cases, which cover every public function. If a test asserts on docstring text that you change, update that assertion, keep it as strong, and say so in `## Result`.
- No test targets test code, the CI workflow or a script (rule 5).

### Gates

- `python -m pytest` passes locally. `python -m ruff check .` and `python -m ruff format --check .` exit 0.
- CI is green on the PR in all six jobs. Coverage of `hilclaw/` stays at line ≥ 80% and function ≥ 80%; take the figures from the CI gate. The `coverage` module is not installed on the driver machine, and it must not be added to the dependencies.
- `git diff --stat origin/main` lists only files in `touchesFiles`. `git ls-files --eol` shows `i/lf` for each, and `git diff --check` is clean. No code line changed: `git diff -U0` shows only lines inside module docstrings.

### Process

- Work only in the driver's dedicated clone.
- First run the §3-5 landed check: `git log origin/main --grep='^Task: T-0175'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0175 --state all`.
- Then run `gh pr list --repo myungjoo/HIL-Claw --state open`. An open PR that touches a file in `touchesFiles` is BLOCKED ("open PR conflict").
- Read the comments on issue #5 after `https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6160644223`:
  - An owner comment that objects to ADR-0047, ADR-0053 or ADR-0056 is BLOCKED ("requirement unclear"); quote it.
  - An answer to HQ-0013, 0014, 0016, 0017, 0018 or 0019 does not stop this task; name it in `## Result`.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Tell each reviewer to write no file and to start no `claude` process.
- **Branch and PR.** Code mode (A-13): create branch `claude/T-0175-docstrings-spec-check-tool-check-seed` from `origin/main`. Open a Draft PR with `T-0175` in its title and `Task: T-0175` as the last line of its body.
- **Review cycle.** Use the dev-item-address reviewer cycle with a fresh-context `dev-reviewer` each round, at most 7 rounds.
  - A result that starts with `SECURITY` is BLOCKED.
  - If no reviewer can be spawned, the task is BLOCKED; do not review your own work.
  - Ask the reviewer to check each edited sentence word by word against the code and against ADR-0047 decision 4, ADR-0053 and ADR-0056 decision 6.
  - Ask the reviewer to confirm that no code line changed and that nothing was invented.
- **Merge.** When the last review is an Approve and CI is green on the head:
  - squash-merge with `gh pr merge --squash --body` so that the squash message ends with `Task: T-0175`;
  - delete the branch;
  - check out `main` at `origin/main`.
- Commit and PR text are in English. Record the language in one line: Python, existing modules.
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
  - any further sentence found under point 4;
  - follow-ups.

  `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters.

## Out of Scope

- Any code line, test behaviour, new module, and any check that compares a spec with its instance.
- Any ARCHITECTURE document, including the "now less exact" sentences of ADR-0050, ADR-0052 and ADR-0053 (integrator follow-up), and README, PLAN, DRIVER.md, CLAUDE.md.
- `hilclaw/check_operation.py` ("what a tool function does with a tool failure an operation raises is open") and every module other than the three listed.
- The operation of `cpu_standin` for `correctness.check`, the wording of the two backend kinds' messages, and OD-18 sub-question ⑰.
- The run-tool contracts (PLAN P1-1; OD-13 sub-question ⑩).

## Follow-ups

- (planner/driver, weigh an HQ) OD-18 sub-question ⑰ (가) and the run-tool contracts (PLAN P1-1; OD-13 ⑩) meet the same question, which is very likely the owner's (A-13, "데이터 plane 스키마 변경"). The question, as suggested in T-0156 `## Result`: "For `correctness.check` (and a timing build of a run tool), is a verification build that ends not ok (compile or link failure, build past its time limit) a result (`outcome` `broken` with a new value of `condition`) or a tool failure of a backend kind, and is the compiler's log kept (where)?"
- (planner, code mode) `hilclaw/check_operation.py`, sentence on decision 8 / sub-question ⑩, third clause: less exact since ADR-0047 (T-0159 `## Result`).
- (integrator) The "now less exact" sentences of ADR-0053 Consequences line 153 and of ADR-0052 / ADR-0050 Context.

## Result

**DONE.** PR #122, squash-merged as `a9fcb23` (squash message ends with `Task: T-0175`); branch deleted on the remote and locally; clone back on `main` at `origin/main`.

- **Review**: 3 rounds, all Approve (`dev-reviewer`, fresh context each). Round 1 nit: "as it was raised" is wider than the code, since `check_failure.ended_with` passes a backend kind's message on only where it is exactly a `str` (otherwise `operation_failure_invalid`); fixed by adding "where it is exactly a ``str``" in both modules. Round 2: a cosmetic short line in `check_seed.py` (fixed by rewrapping the paragraph, words unchanged) and a nit judged needing no change (the `check_tool` sentence speaks of the end line when it is written, not of `end_line_failed`). Round 3: no finding.
- **Gates**: local `python -m pytest` 18605 passed, 351 skipped; `ruff check` and `ruff format --check` clean. CI on head `c31d466` (run 38529620976): all six jobs green. Coverage of `hilclaw/` from the CI gate: lines 5002/5021 = 99.62%, functions 492/492 = 100.00%. `git diff --check` clean, `i/lf` for the three files, only module-docstring lines changed (the two paragraphs of `check_tool.py` and `check_seed.py` were rewrapped; words outside the edited sentences unchanged).
- **Session entry**: landed check empty; no open PR; no comment on #5 after `issuecomment-6160644223` (so no objection and no HQ answer to name).
- **Edited sentences** (old -> new):
  - `hilclaw/spec.py`: "and that ``task.objective`` is what the instance stated (ADR-0050 L2)." -> the same item, followed by "``instance.json`` now has the member ``objective`` (ADR-0053), which :func:`hilclaw.instance.objective_of` reads; this module does not read it, and no module of :mod:`hilclaw` compares a spec's ``task.objective`` with it yet."
  - `hilclaw/check_tool.py`: "and writes the path to no file and puts it in no message" -> "and composes no message that holds the path"; "It writes no seed anywhere and puts none in a message." -> "It composes no message that holds a seed. The end line holds the message of a backend kind an operation raised, where it is exactly a ``str``, as it was raised (ADR-0047 decision 4), so a path or a seed in that message reaches ``events.ndjson``. By the records such a message shows no path (ADR-0056 decision 6) and has no content that holds the seed (ADR-0047 decision 4, citing ADR-0021 decision 3); nothing detects a message that breaks this."
  - `hilclaw/check_seed.py`: "it writes the seed to no file and puts it in no message." -> "it writes the seed to no file and composes no message that holds it. :func:`check` passes on, through ``carry_out``, the message an operation raised with a backend kind, where it is exactly a ``str``, as it was raised (ADR-0047 decision 4), so a seed in that message reaches the caller. By the records such a message has no content that holds the seed (ADR-0047 decision 4, citing ADR-0021 decision 3); nothing detects a message that breaks this."
- **Note on the citation**: ADR-0056 decision 6 forbids a path (and names, bytes, error text) in the message but says nothing of a seed; the seed rule is ADR-0047 decision 4 citing ADR-0021 decision 3. The sentences cite each for its part instead of naming ADR-0056 for both as the task's Why put it.
- **Point 4**: no further sentence of the form "puts ... in no message" / "writes ... to no file" for something an operation's message can carry was found in the three module docstrings (`check_seed.py`'s two `draw` messages are module constants holding no seed; `check_tool.py`'s "composes the message of no tool failure" stays true).
- **Tests**: none changed; no test asserts on the edited text. `test_check_seed.py`'s kept-out strings are not added.
- **Follow-ups**: unchanged from the task's list (OD-18 ⑰ (가) / run-tool contracts question for the owner; `check_operation.py` decision 8 sentence; integrator's "now less exact" sentences of ADR-0050/0052/0053).
