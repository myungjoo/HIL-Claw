---
id: T-0123
title: Move the once-only write steps that `hilclaw/key_records.py`, `hilclaw/instance_file.py` and `hilclaw/spec_file.py` repeat into one shared helper module, with no change of behaviour of any public function
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-13, NFR-1, OD-8, "ADR-0014", "ADR-0025", "ADR-0029"]
dependsOn: [T-0083, T-0094]
touchesFiles: [hilclaw/once_write.py, hilclaw/key_records.py, hilclaw/instance_file.py, hilclaw/spec_file.py, tests/test_once_write.py, tests/test_key_records.py, tests/test_instance_file.py, tests/test_spec_file.py]
estimatedSize: {loc: 140, files: 4}   # non-test: one new module of about 40 statement lines plus its docstring, and about 20 lines replaced by a call in each of the three writers; tests are outside the cap (D4)
hq: []   # no owner-only decision and no OD closure: a refactoring under three accepted records, no rule written, changed or dropped
---
## Why
Three modules of the layer-2 package give a file its final name "once only" by the same steps, written out three times:

- `hilclaw/key_records.py`, `_store` (lines 250-290 at `main` `88b6570`) - ADR-0014 decision 3
- `hilclaw/instance_file.py`, `write` (lines 139-161) - ADR-0025 decisions 3 and 6
- `hilclaw/spec_file.py`, `write` (lines 302-324) - ADR-0029

The repeated steps are: a token `<pid>-<16 random hex characters>`; the temporary name `<final name>.<token>.tmp` beside the final name; an exclusive creation of that file (`open(..., "xb")`); write, flush, `os.fsync`; `os.link(temporary, final)`, which fails when the final name exists and replaces nothing; removal of the temporary file after any exception raised before the name is given (only when this call created it; failures of that removal are suppressed); removal of the temporary name after the link (failure suppressed). There is no fallback to a replacing rename.

T-0094 `## Result` (line 177) recorded the follow-up: "One helper for the once-only write shared by `hilclaw/key_records.py`, `hilclaw/instance_file.py` and `hilclaw/spec_file.py` (code mode, no change of behaviour): about 25 statement lines are now repeated three times. Only after the objection windows of ADR-0025 (2026-10-15) and ADR-0029 (2026-10-16), or with a note of the risk." A rule that is written three times can drift; a later change of it (for example by a task that reverts one of the records) would have to be made three times.

This task makes that helper. It ticks **no PLAN checkbox**; it is upkeep of code that PLAN P1-8 slices landed.

### What differs between the three callers (and therefore stays in the callers)
- **What a taken final name means.** `instance_file.write` and `spec_file.write` raise their own `NameTakenError` (message `<path relative to data_root>: the name is taken; the content was not written`, raised `from None`). `key_records._store` reads the record again with `_read(root, path, derive, key)`: when a record is there it returns `Stored(key, False)`; when the name is free again at that reading, **the `FileExistsError` of the link itself is raised** and nothing is retried.
- **Directories.** `key_records._store` creates each missing directory one by one and removes the ones it made when the write fails; the other two call `path.parent.mkdir(parents=True, exist_ok=True)` and leave the directories when a later step fails.
- **Everything before the file system is touched**: validation, the written-form checks, the `data_root` check, the order of those checks, and how the bytes are built.

### Planner's judgements (2026-10-11T04:3xZ, from the files at `main` `88b6570`; **the reviewer is asked to re-check each**)
- **Why this item now.** No lock, no TODO / INTERRUPTED task file, no open PR; CI on `main` is green. T-0088, T-0106, T-0107, T-0116, T-0117 and T-0121 are BLOCKED on HQ-0005 to HQ-0010, all unanswered. The planner re-read PLAN (every unticked item of P0.5, P1 and P2), the journals of 2026-10-10 and 2026-10-11 and the `## Follow-ups` of T-0115 to T-0122: P0.5-4 waits on HQ-0007; P1-1 on HQ-0005 and HQ-0008 (`profiler.collect` follows the execution points of HQ-0005); P1-5 on HQ-0009; the rest of P1-8 on HQ-0010, OD-3 (owner-only) and the roster of OD-23, which itself rests on HQ-0005 and HQ-0010; P2-1 to P2-5 on those. Follow-ups judged and **not** planned: ADR-0023 line 131 (addressed to the integrator / repository owner; landed records are not edited by driver tasks - they are listed as "less exact" instead); the register rows OD-18, OD-16, OD-6 and OD-17 (BLOCKED tasks edit or read them; T-0122's planner and both its reviewers kept off them); CLAUDE.md "CI 미구축" (the owner's rule text); the format check of Markdown outside `PROCESS/` (T-0121: not worth a task).
- **The weakest point, weigh it first - the date.** Planners since T-0094 shortened its follow-up to "not before 2026-10-16". The follow-up as written allows the task earlier "with a note of the risk", and T-0094 `## Why` (line 29) records that code slices were carried out inside objection windows before (T-0083, T-0087, T-0091, T-0093). **The note of the risk**: ADR-0014 (accepted 2026-10-07), ADR-0025 (window until 2026-10-15) and ADR-0029 (until 2026-10-16) can still be objected to; an objection creates a reverting task, and that task then finds the steps in one module instead of three, with the caller-specific parts still in each caller. The planner judges that this makes a revert no harder. If the reviewer judges otherwise, **do not argue it out: land nothing and return BLOCKED ("task needs re-planning": re-plan on or after 2026-10-16)**.
- **Second - "no change of behaviour" is the whole contract.** No record is written or reworded, no data-plane schema or layout changes, no new dependency (standard library only). If the refactoring cannot be done without changing something a public function's docstring promises or an existing test asserts, stop and return BLOCKED ("task needs re-planning") with the finding.
- **Language**: Python, because the three callers are Python modules of `hilclaw/` (CLAUDE.md language policy; one line in the commit body and in `## Result`).

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, commit trailers, the test rules D12) - mandatory for every task (§6)
- PROCESS/DRIVER.md §0, §1-5 (Bypass permissions; the forbidden actions; a denied or failed tool call is BLOCKED, never worked around), §3 "BLOCKED 사유" paragraph
- CLAUDE.md - whole file; in particular "코멘트 최소화", "테스트 규칙", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode: Draft PR, reviewer cycle, CI green, squash-merge)
- hilclaw/key_records.py - the module docstring (lines 1-65, in particular the convention bullets on how a file comes to be and what happens when writing fails) and `_read`, `_store` (lines 207-290)
- hilclaw/instance_file.py - whole file (161 lines)
- hilclaw/spec_file.py - the module docstring paragraphs on the write, `WrittenFormError`, `NameTakenError`, and `write` (lines 260-324)
- tests/test_key_records.py, tests/test_instance_file.py, tests/test_spec_file.py - every test that patches `open`, `os.link`, `os.fsync`, `os.unlink`, `secrets.token_hex` or a name of the writer module (search for `monkeypatch.setattr`); these fix the observable behaviour
- ARCHITECTURE/decisions/ADR-0014-od8-whole-file-writes.md decisions 3 and 6; ADR-0025-od8-instance-file-write.md decisions 3, 4, 6 and 7; ADR-0029-od8-spec-file.md, the decisions on the write of the file. Read only: no record is edited
- PROCESS/tasks/T-0094-spec-file-write.md `## Result` (the round-3 note on the `created` flag, line 166, and the follow-up, line 177)
- pyproject.toml (the ruff tables, `SLF001` among them - T-0119) and .github/workflows/ci.yml (the jobs "Python gate", "Test presence (hilclaw)", "Coverage gate (hilclaw)": the commands to run locally)
- .claude/skills/dev-item-address/SKILL.md and .claude/skills/dev-code-review/SKILL.md

Line numbers are those of `main` at `88b6570`; if they moved, find the passage by its words.

## Acceptance Criteria
Verify the description of `## Why` against the files at execution time; the file wins and a difference is named in `## Result`.

### New module `hilclaw/once_write.py`
- One public function (no leading underscore, so that the three callers use it without a `# noqa: SLF001`); its name and signature are the executor's choice under review. It takes the final path and the whole content as `bytes` and carries out exactly the repeated steps listed in `## Why`: token, temporary name, exclusive creation, write, flush, `os.fsync`, `os.link`, clean-up. It creates no directory, reads nothing, lists nothing, never opens the final name, and falls back to no rename.
- A taken final name must reach the caller in a form from which **each caller can keep its present behaviour**, `key_records` included (it must be able to raise the `FileExistsError` of the link itself when its second reading finds the name free). How (a return value, the exception passed through, something else) is the executor's choice under review.
- The temporary file is removed only when this call created it; a file of the same name form left by another write is never read, removed or linked. A removal that fails is suppressed in both places, as now.
- The `created` flag keeps its present form (it is set in the statement after `open` returns). The round-3 note of T-0094 - an interrupt between those two statements leaves the temporary file - now applies in one place; **do not try to close that gap in this task**. Say so in `## Result`.
- A module docstring in the manner of the other modules: what the steps are, which decisions of which records they implement (ADR-0014 decision 3, ADR-0025 decisions 3 and 6, ADR-0029), the limits those records state (POSIX file systems with hard links; nothing for a network file system or native Windows), and what the module does not do. It states no rule that the three records do not state. The function has a docstring naming its arguments, result and exceptions. No multi-line comments (CLAUDE.md).
- It is not a tool, is not registered in `hilclaw/tools.py` and is not exported from `hilclaw/__init__.py`.

### The three callers
- `key_records._store`, `instance_file.write` and `spec_file.write` call the helper for the repeated steps and keep everything listed under "What differs between the three callers". Imports that become unused are removed.
- **No change of behaviour**: every public function of the three modules raises the same exception types with the same messages in the same order of checks, returns the same values, leaves the same files and directories behind in every failure path (in `key_records`: the temporary file and the directories the call created are removed; in the other two: the directories stay), and writes the same bytes under the same names, the temporary name form included.
- One order is allowed to change, and must be named in `## Result` if it does: in `key_records._store`, whether the temporary file is removed before or after the second reading of a taken name. No docstring promises that order. If an existing test asserts it, keep the present order.
- The module docstrings and function docstrings of the three callers stay true. Edit a sentence only where it has become false or where it should now point to the helper; do not shorten or rewrite the conventions.

### Tests (D12 rules; tests are outside the size cap)
- `tests/test_once_write.py` (required by the "Test presence" gate and test rule ④), covering the public function with: happy path (the bytes under the final name, the temporary name gone, the temporary name form with a fixed token); the final name taken (nothing replaced, the entry under the name untouched, the temporary file gone, the signal the caller gets); **negative and failure paths** - the temporary name already in use (the foreign file is left as it is), a failing write, a failing `os.fsync`, a failing `os.link` other than "exists", a `KeyboardInterrupt` during a step (the temporary file is removed and the exception passes through), a failing removal after the link (not reported), a content that is not `bytes`, a missing parent directory. Skip or mark by platform exactly as the existing writer tests do where hard links are not available.
- The existing tests of the three writers must pass with **no assertion changed**. Where a test patches a name that the writer module no longer holds (`key_records.secrets`, the module-level `open` of `key_records`), change only the patch target so that it reaches the helper; list every such edit in `## Result`. If a test can only be kept by changing what it asserts, that is a change of behaviour: stop (see `## Why`, second judgement).
- No test for a test helper, a CI workflow or a script (test rule ⑤).
- Local run before the PR and again after the last review round: `python -m ruff check .`, `python -m ruff format --check .`, `python -m pytest`, and the coverage command of the "Coverage gate (hilclaw)" job; line and function coverage of `hilclaw/` stay at or above 80 %, and `hilclaw/once_write.py` itself is fully covered or the uncovered lines are named in `## Result`.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0123'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0123 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open`. An open PR that edits one of the files of `touchesFiles` is BLOCKED ("open PR conflict"). If a comment on issue #5 newer than 2026-10-11T04:00Z objects to ADR-0014, ADR-0025 or ADR-0029, return BLOCKED ("task needs re-planning") quoting it. An owner answer to an HQ does not stop this task.
- Code mode (CLAUDE.md A-13): branch `claude/T-0123-shared-once-only-write-helper`; Draft PR whose title contains `T-0123` and whose body ends with the line `Task: T-0123`; the reviewer cycle of dev-item-address with a fresh-context `dev-reviewer` each round (at most 7 rounds; past the cap without a final Approve, return BLOCKED; a result starting with `SECURITY` is BLOCKED; if no reviewer can be spawned, return BLOCKED - do not self-review). Ask the reviewer explicitly to (a) **re-check the planner's judgements in `## Why`, the weakest point first**; (b) compare each caller before and after, path by path through every failure branch, for a change of behaviour; (c) check that every edit of an existing test changes a patch target only; (d) check that the helper's docstring states nothing beyond the three records.
- CI green on the PR (three consecutive red runs: BLOCKED), then squash-merge with `gh pr merge --squash --body` so that the squash message ends with `Task: T-0123` (after it, any attribution trailer your session requires), delete the branch (remote and local in separate commands), and confirm the `push` run on `main`.
- Commit / PR text in English. The body says: what moved, that no behaviour changed and how that was checked, **the note of the risk** (the objection windows of ADR-0014, ADR-0025 and ADR-0029 and their end dates), and one line on the language chosen and why.
- Never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around.
- `## Result`: fill it in after the merge, on `main`, and leave that edit uncommitted for the driver (DRIVER §3-6). Record: the PR and squash commit, review rounds and findings (what each reviewer said on the weakest point), the helper's name and signature as landed and how a taken name is signalled, the non-test line counts per file, every edited existing test, the order question in `key_records._store`, the coverage figures, the language line, the follow-ups. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- `hilclaw/run_state_file.py`, `hilclaw/artifacts.py`, `hilclaw/cas.py` and `hilclaw/clang_build.py`: they replace by `os.replace` (ADR-0013 and others), a different rule; no shared helper for them here.
- Any change of a rule: a fallback, a retry, a directory flush, a lock, a different temporary name form, closing the `created` gap, a new exception class shared by the callers, merging the two `NameTakenError` or `WrittenFormError` classes.
- Every file under `ARCHITECTURE/` (no record, register row or scenario is edited), `PROCESS/` other than this task's `## Result`, `.github/`, `.claude/`, `pyproject.toml`, CLAUDE.md, README.md.
- Anything HQ-0005 to HQ-0010 ask; the task files of T-0088, T-0106, T-0107, T-0116, T-0117 and T-0121.

## Follow-ups
- (planner, if ADR-0014, ADR-0025 or ADR-0029 is objected to) The reverting task changes the steps in `hilclaw/once_write.py` and the caller-specific part in the caller the record covers.
- (planner - after T-0088, T-0116, T-0117 and T-0121 are done or re-planned, document mode) The move of T-0118 / T-0122 for the register rows OD-18, OD-16, OD-6 and OD-17.
- (integrator / repository owner) ADR-0023 line 131 quotes a clause that since T-0122 stands in the OD-13 section of `OpenDecisionProposals.md`; CLAUDE.md "CI 미구축" and "(CI 구축 전: 로컬 테스트)" no longer match `main`; whether the OD-4 and OD-8 rows should say in one line what is still open.
- (driver / owner) HQ-0005 (T-0088) and HQ-0008 (T-0116): the rest of PLAN P1-1. HQ-0006 (T-0106). HQ-0007 (T-0107) and the hook registration of PLAN P0.5-4. HQ-0009 (T-0117): PLAN P1-5. HQ-0010 (T-0121): the isolation means of OD-8.
- (planner) After this task the planner of T-0123 knows of no further task that is executable without an owner answer; the next iterations may find no selectable task (DRIVER §3-3).

## Result
