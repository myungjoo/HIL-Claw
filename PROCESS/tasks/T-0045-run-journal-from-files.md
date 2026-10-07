---
id: T-0045
title: Add hilclaw/run_journal.py, the functions over the files of a run that read its STATE.json and give the current spend view and the state of an identity (stored view folded over the tail of the log), and add its tests
phase: P1
status: DONE
commitMode: code
coversReq: [OD-17, OD-8, FR-13, NFR-1, NFR-2, "#8 M7", "#4 §1"]
dependsOn: [T-0041, T-0043, T-0044]
touchesFiles: [hilclaw/run_journal.py, tests/test_run_journal.py]
estimatedSize: {loc: 140, files: 1}   # non-test: one new module; the test file is excluded from the cap (D4)
hq: []   # implements closed decisions (ADR-0011 decisions 3, 4, 6; ADR-0012 decisions 2, 4, 5, 6; ADR-0006 decisions 2, 6); closes no OD, writes no ADR, standard library only, changes no file format, writes no file
---
## Why
Three accepted pieces exist as separate functions and nothing joins them over the files of a run:

- `hilclaw/run_state.py` (T-0043): `parse(content)` turns the bytes of a runtime `STATE.json` into `RunState(round, budget_spent, others)`, where `budget_spent` is a `journal.SpendView`. It "reads and writes no file and knows no path".
- `hilclaw/events.py` (T-0044): `read(data_root, run_id, position)` returns the complete lines of `events.ndjson` after a line position and raises `PositionBeyondLogError` when the file holds fewer complete lines.
- `hilclaw/journal.py` (T-0041): `fold(lines, view)` and `step_state(identity, lines, view)` are pure functions over parsed lines.

**ADR-0011** decision 6, *Replay*: "at any moment, the current view is the stored view folded further over the **tail**, the complete lines after the position". Decision 6, last bullet: "The lookup of decision 3 has the same bound for a step about the round in progress … the tail alone decides its state". *Disagreement*: "A position beyond the end of the log is an error of the kind of a damaged line …: the stored view is not used, the error is reported and not repaired by the reader". **ADR-0012** decision 6: "what [a validator of this file alone] cannot [check]: … that `position` is not beyond the end of the log — a reader of both files sees the second". Consequences: "`layout.run_file(data_root, run_id, "STATE.json")` is the path".

This task writes that reader of both files: a small module of its own that (1) reads the `STATE.json` of a run from its path, (2) gives the current spend view of the run, and (3) gives the state of an identity, both from the stored view and the tail. It is the function a first journaled tool of P1-1 needs before it may start a step (ADR-0011 decision 3, "the tool layer establishes the state of its identity from the log"), and the place where `PositionBeyondLogError` meets the stored position.

It ticks **no PLAN checkbox** (a slice of P1-8, and a prerequisite of the first journaled tool of P1-1).

Why this item now (planner, DRIVER §6, 2026-10-07 UTC, judged from the files):
- P0.5-3 is BLOCKED on HQ-0003 (T-0014). The verification half of P1-3 (T-0036), P1-4 and the "harness pass" half of P0.5-1 wait for HQ-0004. Both are unanswered. The rest of P0.5-4 is the owner's hook registration. P1-1 has no tool with a fully decided contract; P1-5 slice 3 needs owner values.
- The other open slice of P1-8, the **replacement** of `STATE.json` on disk, has to judge a write technique first (ADR-0004 decision 7 allows no scratch path under `runs/`; ADR-0012 decision 6 leaves the technique "to the code task and to OD-23") and sub-question ⑩ (what writes the first file). This task **reads only** and needs neither.
- T-0044 Follow-ups name exactly this slice as the next one. No open PR at planning time. No existing TODO / INTERRUPTED task file.

A-13 check (planner's reading — the reviewer is asked to re-check it):
- "데이터 plane 스키마 변경": none. No file format, member or rule of the data plane changes; the module calls `run_state.parse`, `events.read` and `journal.fold` / `journal.step_state` as they are and writes no file.
- No new external dependency: standard library only; `pyproject.toml` unchanged.
- **No decision of OD-23**: the module is a library function. It is not registered as a tool, has no command line entry, and says nothing about which agent or hook calls it or how a result reaches the Round-Manager.
- The cases the records leave unsaid are listed below with a recommended provisional convention each. If the executor or the reviewer reads one as a design choice that needs a record or the owner, that is BLOCKED with the exact question.

Known risk, accepted: ADR-0006, ADR-0011 and ADR-0012 are inside their objection windows (until 2026-10-14). An objection creates a reverting task and this module is revisited with it.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED, never worked around), §3 "BLOCKED 사유" paragraph, §9
- ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md — decision 3 "The repeated call" (lines 53-58), decision 4 (lines 61-70), **decision 6 (lines 79-92)**, decision 9 "Two turns at once" (line 111), sub-questions ① and ③ (line 173)
- ARCHITECTURE/decisions/ADR-0012-od8-runtime-state-file.md — decision 2 "A missing file" (line 39), decision 4 (lines 57-74), decision 5 (76-80), **decision 6 (lines 82-90)**, decision 7 (92-99), Consequences line 136, Boundaries (142-151, in particular sub-questions ⑩ and ⑫)
- ARCHITECTURE/decisions/ADR-0006-od8-events-log.md — decisions 2, 5 and 6 (a line, append only, torn tail and damage)
- ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md — decisions 1, 4 and 10 (the run directory, the writers, no concurrency control and no atomicity)
- `hilclaw/run_state.py` — the whole file (285 lines): the module docstring, `InvalidStateError`, `UnsupportedVersionError`, `RunState`, `parse`
- `hilclaw/events.py` — the module docstring (lines 1-39), `Log`, the four error types (86-106), `read` (181-228), `_root` and `_lstat` (277-293: the convention for `data_root` and for a path that is not a regular file; they are private — do not import them)
- `hilclaw/journal.py` — the module docstring, `Identity`, `SpendView`, `Report`, `StepState`, `EMPTY`, `fold` (133-175), `step_state` (178-206, with its stated limit)
- `hilclaw/layout.py` — `RUN_FILES`, `check_run_id`, `run_file` (lines 34, 58-77)
- `tests/test_run_state.py` lines 1-60 (the constants `START`, `AFTER`, `AFTER_VIEW`, `LINES`: the Examples of ADR-0012 and ADR-0011) and `tests/test_events.py` lines 24-110 (`root`, `place`, `snapshot`, `line`) — the style to follow; helpers are copied into the new test file, not imported from another test file
- PROCESS/tasks/T-0041-journal-fold-and-step-state.md, T-0043-runtime-state-validator.md and T-0044-events-read-from-position.md — `## Result` of each ("as landed", provisional conventions, limits)
- CLAUDE.md — 상시 규칙: "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" ①-⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- .claude/skills/dev-item-address/SKILL.md (procedure); .claude/skills/dev-code-review/SKILL.md (what the reviewer checks)
- `.github/workflows/ci.yml` — five checks run on a PR; the job `Test presence (hilclaw)` expects `tests/test_<module>.py` for a new `hilclaw/<module>.py`
- Issue #5: every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6034226175 (the ADR-0012 notice; `gh issue view 5 --repo myungjoo/HIL-Claw --comments`). If the owner has objected to ADR-0006, ADR-0011 or ADR-0012 in a way that changes a rule used here, do not start: return BLOCKED ("requirement unclear") quoting the comment

## Acceptance Criteria
The records fix what is computed. The module name, the function names, the result types, the error types and the handling of the cases the records do not mention are **conventions chosen by this task, provisional**: state each with one line of reason in the commit body, the PR body and `## Result`. Where a criterion below and a record disagree, **the record wins**: follow it and say so in `## Result`.

### Files
- `hilclaw/run_journal.py` (new; recommended name — another name is fine if the reason is given; about 140 lines with docstrings, and in any case within the cap of 300).
- `tests/test_run_journal.py` (new; the name must match the module for the `Test presence (hilclaw)` job).
- Python, because the three modules it joins are Python — one line in the commit body and `## Result`.
- Nothing else. `hilclaw/run_state.py`, `hilclaw/events.py`, `hilclaw/journal.py`, `hilclaw/layout.py`, `hilclaw/tools.py`, `hilclaw/__main__.py`, `hilclaw/mcp_front.py`, `pyproject.toml`, `.github/` and every existing test stay as they are.

### The three capabilities (recommended signatures; all read only)
1. **Read the state file of a run** — `read_state(data_root, run_id)` returns the `run_state.RunState` of `layout.run_file(data_root, run_id, "STATE.json")`: the bytes of the file given to `run_state.parse`, nothing else interpreted.
   - An invalid content raises `run_state.InvalidStateError`, another version `run_state.UnsupportedVersionError` (ADR-0012 decision 6: reported, no member used, nothing repaired). The message names the file by its path relative to the data root, as the messages of `hilclaw.events` do, in front of the message of `parse`.
   - An empty file is invalid, not missing (ADR-0012 decision 2).
2. **The current spend view of a run** — `current(data_root, run_id)` returns one result value (recommended: a `NamedTuple` with `state`, `view`, `reports`, `torn_tail`):
   - `state`: the `RunState` as stored (capability 1);
   - `view`: `journal.fold(tail, state.budget_spent)[0]`, where `tail` is `events.read(data_root, run_id, state.budget_spent.position).events` (ADR-0011 decision 6, *Replay*);
   - `reports`: the reports of that fold (ADR-0011 decision 6: such lines are "counted and reported"), unchanged;
   - `torn_tail`: the number `events.read` reports. The file is not changed (removing a torn tail is the writer's and the committing step's — ADR-0006 decision 6).
3. **The state of an identity** — `step_state(data_root, run_id, identity)` returns `journal.step_state(identity, tail, stored view)`, a `journal.StepState`, with the same stored view and tail. Its docstring states the limit of `journal.step_state` in one sentence: the answer is right for a step whose lines lie after the stored position, as those of the round in progress (ADR-0011 decision 6, last bullet; sub-question ①). The function does **not** fall back to a read from the first line.

For 2 and 3:
- **`STATE.json` is read before the log.** Reason to state in the docstring or the commit body: lines are only appended and the stored view moves only at a round end, so a state read first names a position the log read afterwards has reached, whenever the two files were consistent; the opposite order could pair an older log with a newer position. The two reads are not atomic and no lock is taken (ADR-0004 decision 10; the lock is the rest of OD-17) — a limit to state, not to solve.
- **A position beyond the end of the log** raises `events.PositionBeyondLogError` as `events.read` raises it; nothing is returned, the stored view is not used, nothing is repaired (ADR-0011 decision 6, *Disagreement*). Whether the error passes through unchanged or gets a prefix that names `STATE.json` and its position is the executor's; it must stay an instance of `PositionBeyondLogError`.
- A damaged line or a line of another version in the tail, and a tail line that `journal.fold` refuses, raise what `events.read` and `journal.fold` raise; nothing is returned. Damage **before** the position is not seen (T-0044).
- No full fold from the first line, no comparison of the stored view with one (sub-question ③ of OD-17), no write of `STATE.json`, no append to the log.
- No function modifies its arguments, and nothing returned shares mutable state with a later call.

### Constraints
- **Standard library only.** The module imports `hilclaw.events`, `hilclaw.journal`, `hilclaw.layout` and `hilclaw.run_state` and uses their public names only (no `_root`, `_lstat` or other private helper of another module; a few lines of its own for the same checks are fine).
- **Read only**: no file or directory is created, written, renamed or removed, including under a missing run directory.
- **Not a tool**: nothing is registered in `hilclaw/tools.py`, no command line entry, no use of `hilclaw.config` or of the real data repository `HIL-Claw-data`.
- **No decision of a boundary**: who calls these functions and how a result reaches the Round-Manager (OD-23); what is done about an open step (OD-10, the retry part of OD-17); a budget limit (OD-19); the lock; reading another version (OD-11); the first `STATE.json` of a run (sub-question ⑩); any member of `STATE.json` besides the three of ADR-0012 (`others` is returned as parsed and never interpreted).
- Module docstring in the style of the three modules: what it joins, its conventions that the records do not fix, and what it does not do. Docstrings exact and short; no multi-line comments (CLAUDE.md "코멘트 최소화").
- Runs on CPython 3.11 and 3.14, the same on POSIX and Windows.

### Cases the records leave unsaid — choose, implement, test and list each with one line of reason
- **A missing `STATE.json`** (no file, no run directory, or no `runs/`). ADR-0012 decision 2: it "means that no state was written for this `run_id`: no round has begun"; what a run directory that holds other files but not this one means is sub-question ⑩, open. Recommended: a dedicated error of this module (for example `MissingStateError`, **not** a subclass of `InvalidStateError`, since a missing file is not an invalid one), naming the path; the module does **not** answer with the start values of decision 4 by itself, because that would treat every such directory as a started run — the point sub-question ⑩ leaves open. If you judge that returning the start state is what decision 2 says, do not implement it: return BLOCKED with the question.
- **A path that is not a regular file** in the place of `STATE.json` (a directory, a symbolic link — not followed, as `hilclaw.events` does). Recommended: `run_state.InvalidStateError` naming the path ("is not a regular file"); say why this type and not a new one.
- **`data_root`**: recommended as `hilclaw.events` has it — an existing directory, `FileNotFoundError` or `NotADirectoryError` otherwise; `str` and `Path` accepted; not resolved.
- **The order of the argument checks**: `run_id` (the error of `hilclaw.layout` passes through), then for capability 3 the `identity` (the errors of `journal.step_state`), then the file system. Recommended: an invalid `identity` is reported before any file is read — say what you chose and assert it.
- **An `OSError`** while a file is read (other than "missing"): passes through.
- **A missing or empty `events.ndjson` with a stored position 0**: the stored view is the current view, no report (ADR-0006 decision 2). With a stored position ≥ 1: beyond the end.
- **The stored view lists an identity as open and the tail holds its end line**: the view after the fold no longer lists it and counts its amounts, and capability 3 answers `ENDED` — this is `journal`'s behaviour; assert it, do not re-implement it.
- Anything else you meet. If you read one as a rule about what `STATE.json` or the log means that no record states, return BLOCKED with the exact question.

### Tests (excluded from the size cap; `tests/test_run_journal.py`)
Helpers live in the test file and get no tests of their own (test rule ⑤). Synthetic values only (`example_step`, `example_axis`); files are written under `tmp_path` with `run_state.dump` or literal bytes and with `events.append` or literal lines.
- happy: the Example of ADR-0012 with the log it describes (the two lines of the Example of ADR-0011 and one start line of candidate 1) — `read_state` gives round 4 and the view of the Example; with the state at the start of a run (position 0) and that log, `current` gives totals `{example_axis: 7}`, position 3 and the one open step, equal to `journal.fold` of the whole log; with the stored position 3, `current` gives the stored view unchanged and no report; lines appended after the stored position with `events.append` are folded.
- the replay property: for a log of several steps and every prefix length *p*, a `STATE.json` holding the fold of the first *p* lines gives, through `current`, the same view as the fold of the whole log.
- `step_state` from files: `NO_LINE`, `OPEN` (start line in the tail; and open in the stored view with nothing in the tail) and `ENDED` with a `result` and with a `failure` (the copies of what the end line holds); an identity whose lines all lie before the stored position answers `NO_LINE` — the stated limit, asserted as such.
- branch: reports of the fold returned (`END_NOT_OPEN`, `START_REPEATED`) with the line numbers of the file; a torn tail reported and the file unchanged (bytes compared before and after); `others` returned as parsed; any order of members and white space in `STATE.json`; a total above `keys.MAX_INTEGER`; lines of other kinds in the tail counted in the position; `data_root` given as `str`; two runs with two pairs of files; no file or directory created by any call (compare a listing of `tmp_path` before and after, also for a missing run directory).
- error / negative (assert the error type and that the message names the file where the criterion says so): a missing `STATE.json` with and without a run directory, and with a log present; an empty file; content that is not UTF-8, not JSON, a repeated member name, a missing required member, `schema_version` 2 (the `UnsupportedVersionError` of `run_state`, not that of `events`); a directory and a symbolic link in the place of `STATE.json` (skip the link case where the platform cannot create one, as `tests/test_events.py` does); a stored position beyond the log for a missing log, an empty log, a log one line short, and a log whose only excess bytes are a torn tail — an instance of `events.PositionBeyondLogError`, nothing returned; a damaged line and a line of another version in the tail (reported) and before the position (not seen); a malformed step line in the tail (the error of `journal.fold`); an invalid `run_id`; a missing `data_root` and a file in its place; for `step_state`, an `identity` that is not a `journal.Identity` and one with invalid values, with nothing read.
- Test rules of CLAUDE.md / DRIVER §5 (D12): ① `hilclaw/` keeps line and function coverage ≥ 80 % — coverage is not measured by CI yet (P0.5-3 BLOCKED on HQ-0003), so check that the tests reach every line of the new module, for example with `python -m trace --count --missing --coverdir <directory outside the repository> --module pytest tests/test_run_journal.py` (T-0044 `## Result` notes that `trace` shows raising lines as missing under pytest), and say how in `## Result`; ② happy, error, branch and negative cases as above; ③ every public function and every public error type of the new module is tested; ④ the new module has its test file; ⑤ no tests for test code, CI workflows or helper scripts.

### Verification (record summary lines and run URLs in `## Result`)
- Local, before the commit and before the merge, from the repository root: `python -m pytest` exits 0 (record pass and skip counts; before this task: 4487 passed, 137 skipped on CPython 3.14 on Windows), `python -m ruff check .` and `python -m ruff format --check .` exit 0 (ruff 0.16.10, pytest 9.1.1).
- `git ls-files --eol` shows `i/lf` for both files; `git status --short` after the tests shows no stray file; `git diff origin/main --stat` lists only the two files of `touchesFiles`.
- CI on the PR: `gh pr checks <PR> --watch` ends with **five** successful checks on the final head — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)`. Merge only then.
- After the squash-merge, check the `push` run on `main` (`gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"`) and record its conclusion; if it is not `success`, do not fix forward on `main`: record it and say so in the returned summary.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0045'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0045 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (none at planning time; a PR touching the two files of `touchesFiles`, or changing the public names used from `hilclaw/run_state.py`, `hilclaw/events.py` or `hilclaw/journal.py`, is BLOCKED "open PR conflict").
- Code mode: branch `claude/T-0045-run-journal-from-files` from `origin/main`; Draft PR with the `DONOTMERGE` label; PR title contains `T-0045`; executor commits end with the trailer `Task: T-0045`.
- Install nothing. After a failed CI run, read the whole failed log (`gh run view <id> --log-failed`) and fix every diagnostic before pushing again. Three consecutive failed CI runs on the PR: stop and return BLOCKED ("CI 3 consecutive failures") with the last log excerpt in `## Result`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds; if the cap is passed without a final Approve, return BLOCKED). Keep docstrings exact and short so that rounds are not spent on wording. Ask the reviewer explicitly to (a) compare the behaviour with ADR-0011 decisions 3, 4 and 6 (*Replay*, *Disagreement*, the last bullet) and ADR-0012 decisions 2 and 6, sentence by sentence — state before log, the tail from the stored position, nothing repaired, nothing written, the stored view not used when the position is beyond the log; (b) re-check the planner's readings in `## Why` — A-13 "data-plane schema change" does not apply, and a library function that is not registered decides nothing of OD-23; (c) re-check each convention under "unsaid", in particular the missing file (that the module does not answer sub-question ⑩) and the error type for a path that is not a regular file; (d) report anything the code decides that the records list under Boundaries (a recovery of an open step, a comparison with a full fold, a lock, a write, another version, an interpretation of `others`). If the reviewer reads a point as a design choice needing a record or the owner, return BLOCKED with the question. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm the five checks on the final head, then `gh pr merge <PR> --squash --body-file <file outside the repository>` with the PR body, whose **last line is `Task: T-0045`**. Delete the remote branch and the local branch in **separate** commands and only after `gh pr view <PR> --json state` reports `MERGED`.
- Commit body: the provisional choices (module and function names, the result type, each error type, each unsaid case, the order of the two reads) with one line of reason each, and the language line.
- `## Result`: fill it in **after** the merge, on `main`, and leave that edit **uncommitted** — the driver commits it (DRIVER §3-6). The branch and the PR must not contain this task file. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. Record: PR and commit, review rounds and findings, the public API as landed, the provisional choices and unsaid cases, the verification outcomes, the line count of the module, the language line, and that this task ticks **no** PLAN checkbox.
- Size: about 140 non-test lines in 1 file; the cap is 300 LOC / 5 files (tests excluded). If the module would pass the cap, finish the smaller scope (capabilities 1 and 2) and propose the split in `Follow-ups`.
- If a record turns out to be ambiguous or self-contradictory on a point the code must decide and that is not one of the provisional conventions above, do not guess and do not edit the ADR: return BLOCKED ("requirement unclear") with the exact question.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- Writing or replacing `STATE.json` (the write that leaves the old or the new content, its technique, the first file of a run — sub-question ⑩), keeping unknown members on a write (sub-question ⑫), and any other member of that file; `instance.json`; the result files of an attempt.
- A fold from the first line, the comparison of the stored view with it and its report (OD-17 sub-question ③); an index for steps about earlier rounds (sub-question ①); a byte offset or a chunked scan (sub-question ⑬).
- Appending `step_started` / `step_ended`, running a step, the rule of the repeated call as a whole (it belongs to the first journaled tool of P1-1 and the rest of OD-18), recovery of an open step (OD-10), budget limits (OD-19), the lock (rest of OD-17).
- A tool, a command line entry or any registration in `hilclaw/tools.py`; any use of `hilclaw.config` or of the real data repository.
- Any edit of another module or test, `pyproject.toml`, `.github/`, `.claude/`, `README.md`, any ADR, the OD register, OpenDecisionProposals, CLAUDE.md, DRIVER.md, PLAN.md, the skills, the agents.
- Answering HQ-0003 or HQ-0004 on the owner's behalf.

## Follow-ups
- (planner, P1-8) The replacement of the runtime `STATE.json` on disk: to judge first whether the technique needs a §9 record (ADR-0004 decision 7 allows no scratch path under `runs/`; ADR-0012 decision 6 leaves it "to the code task and to OD-23") together with sub-questions ⑩ and ⑫ — probably a document-mode ADR slice before the code.
- (planner, P1-1) The first journaled tool on top of this module and ADR-0011 decision 3, once a tool has a fully decided contract.
- (unchanged) The T-0041 question for a revision of ADR-0011; the integrator items after 2026-10-14 (T-0040 and T-0042 Follow-ups); OD-18 sub-questions ① and ③ (T-0039 Follow-ups).

## Result
**DONE** — PR [#41](https://github.com/myungjoo/HIL-Claw/pull/41), squash commit `40a1942` on `main` (branch commits `f527c47`, `3bcf1e4`, `9da2b9c`; branch deleted remote and local after the PR state was `MERGED`). This task ticks **no** PLAN checkbox (a slice of P1-8 and a prerequisite of the first journaled tool of P1-1). No new HQ.

**Start checks.** Landed check: no commit with `Task: T-0045` on `origin/main` and no PR for T-0045; no open PR. Issue #5: no comment after the ADR-0012 notice (issuecomment-6034226175), so no objection to ADR-0006, ADR-0011 or ADR-0012.

**Review** (fresh-context `dev-reviewer`, 3 rounds, final Approve; no blocking finding in any round, no security suspicion):
- Round 1 — Approve, with two notes handled in `3bcf1e4`: the shared helper unpacked `events.Log` by field order (now `_state_and_log` returns the `Log` and the callers use `log.events` and `log.torn_tail`); the docstring of `read_state` now says that a file that disappears between the check and the read is an `OSError`.
- Round 2 — Approve, with one wording note handled in `9da2b9c`: the docstring of `Current` called the fourth member "the tail" (now the length of the torn tail).
- Round 3 — Approve, "no nit remains that should be resolved in this PR".
- The reviewer re-checked the points the task asked for and agreed with all: (a) the behaviour matches ADR-0011 decisions 3, 4 and 6 and ADR-0012 decisions 2 and 6; (b) A-13 "data-plane schema change" does not apply and a library function that is not registered decides nothing of OD-23; (c) every convention under "unsaid" accepted, in particular `MissingStateError` (sub-question ⑩ is not answered) and `InvalidStateError` for a path that is not a regular file; (d) nothing decided that the records list under Boundaries. No point that needs a record or the owner.
- Observations kept (no change asked): "a symbolic link is not followed" holds for the last path component only, as in `hilclaw.events` (ADR-0004 decision 10: no isolation); a file in the place of `runs/` or of the run directory is reported as a missing `STATE.json`, as `hilclaw.events` treats the log; the "nothing read" test patches `Path.read_bytes` only, and the order is proved by the assertion with a missing data root; the symbolic-link cases are skipped on Windows and run in the Linux CI jobs.

**As landed** (`hilclaw/run_journal.py`, 130 lines, 1 non-test file; imports `os`, `stat`, `pathlib`, `typing` and the public names of `hilclaw.events`, `hilclaw.journal`, `hilclaw.layout`, `hilclaw.run_state`):
- `read_state(data_root, run_id)` → `run_state.RunState`: the bytes of `layout.run_file(data_root, run_id, "STATE.json")` given to `run_state.parse`.
- `current(data_root, run_id)` → `Current(state, view, reports, torn_tail)` (a `NamedTuple`): the state as stored; `journal.fold(tail, state.budget_spent)` with `tail = events.read(data_root, run_id, state.budget_spent.position).events`; the reports of that fold (line numbers of the file); the number of bytes of a torn tail.
- `step_state(data_root, run_id, identity)` → `journal.StepState`: `journal.step_state(identity, tail, stored view)`; the limit is in the docstring (right for a step whose lines lie after the stored position; a step that ended before it answers `NO_LINE`; no read from the first line).
- `class MissingStateError(Exception)`; message `runs/<run_id>/STATE.json: is missing`.
- Messages about the content: `runs/<run_id>/STATE.json: <message of parse>`, the error type kept (`run_state.InvalidStateError` or `run_state.UnsupportedVersionError`); a path that is not a regular file: `run_state.InvalidStateError`, `runs/<run_id>/STATE.json: is not a regular file`.
- Nothing is written, created or removed; not registered in `hilclaw/tools.py`; no command line entry; no other file of the repository changed.

**Provisional conventions chosen by this task** (the records do not fix them; also in the commit and PR body):
- Module name `run_journal` — it joins `run_state` and `journal` over the files of a run. Function names `read_state`, `current`, `step_state` — the last is the name of the `journal` function it answers with. Result type `Current`, a `NamedTuple`, as `events.Log` and `run_state.RunState` are.
- `STATE.json` is read before the log — lines are only appended and the stored view moves only at a round end, so a state read first names a position the log read afterwards has reached whenever the two files were consistent. The two reads are not atomic and no lock is taken (ADR-0004 decision 10): a limit stated, not solved.
- A missing `STATE.json` (no file, no run directory, no `runs/`, a file in the place of a directory above it; also with a log or another file present): `MissingStateError`, a plain `Exception` — not a subclass of `InvalidStateError` (a missing file is not an invalid one, ADR-0012 decision 2) and not an `OSError` (a state of the run, not a failure of the system). The start values of decision 4 are not answered in its place (sub-question ⑩ stays open).
- A path that is not a regular file (a directory; a symbolic link, not followed, also a dangling one): `run_state.InvalidStateError` — no state can be read and nothing is repaired, exactly as for an invalid content, and `hilclaw.events` reports the same case with its damage error. An empty file is invalid, not missing.
- `PositionBeyondLogError` passes through unchanged — its message already names the log, the position and the number of complete lines, and the position can only be the stored one.
- `data_root`: an existing directory, `FileNotFoundError` or `NotADirectoryError` otherwise; `str` and `Path`; not resolved (a relative root works) — as `hilclaw.events`. A few lines of the module's own, no private helper of another module.
- Order of the checks: `run_id` (`layout.InvalidPathValueError`), then for `step_state` the `identity` (`journal.JournalError` / `events.InvalidEventError`, raised before any file is read, also with a missing data root; done with `journal.step_state(identity, ())`, a public name), then the file system.
- An `OSError` while a file is read passes through, a file removed between the `lstat` and the read included.
- A missing or empty log with a stored position 0: the stored view is the current view, no report; with a position ≥ 1: beyond the end. A torn tail is never counted.
- An identity open in the stored view whose end line is in the tail: the view no longer lists it and counts its amounts, and `step_state` answers `ENDED` — the behaviour of `journal`, asserted and not re-implemented.
- A damaged line, a line of another version (`events.UnsupportedVersionError`, not that of `run_state`) and a malformed step line (`journal.JournalError`, `line <n>:` with the number in the file) in the tail raise what `events.read` and `journal.fold` raise; damage before the position is not seen.
- No criterion disagreed with a record.

**Tests** (`tests/test_run_journal.py`, new, 861 lines; 191 passed and 6 skipped on Windows — the symbolic-link cases): the signatures and types; the Examples of ADR-0012 and ADR-0011 through all three functions; lines appended with `events.append`; the replay property for every prefix of a log of ten lines; `NO_LINE`, `OPEN` (in the tail; in the stored view), `ENDED` with a result and with a failure, the first end line, the stated limit; reports with the line numbers of the file; a torn tail with the tree compared before and after; `others`, member order and white space, a total above `keys.MAX_INTEGER`, lines of other kinds, `data_root` as `str` and relative, two runs, nothing created, no state shared between calls; a missing `STATE.json` in six forms; twelve invalid contents with the exact message; versions 0 and 2; a directory and a symbolic link; an `OSError`; a position beyond the log in five forms; damage and another version in the tail and before the position; malformed step lines; a directory in the place of the log; invalid `run_id`, `data_root` and `identity`, and the order of the checks.

**Verification**
- Local (CPython 3.14.4, Windows; pytest 9.1.1, ruff 0.16.10), before the first commit and again on the final head: `python -m pytest` → 4678 passed, 143 skipped (before this task: 4487 passed, 137 skipped); `python -m ruff check .` → "All checks passed!"; `python -m ruff format --check .` → "121 files already formatted".
- `git ls-files --eol`: `i/lf` for both files. `git status --short` after the tests: only the two files. `git diff origin/main --stat`: `hilclaw/run_journal.py` and `tests/test_run_journal.py` only.
- Lines reached (test rule ①; coverage is not measured by CI yet): `python -m trace --count --missing --coverdir <scratch directory outside the repository> --module pytest tests/test_run_journal.py`, run on the first commit — every executable line of the module has a count, the raising lines included, and no line is marked missing. The two later commits changed what a helper returns and two docstrings, and added no branch; the trace was not run again on them.
- CI on the final head `9da2b9c`: five successful checks — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)` — https://github.com/myungjoo/HIL-Claw/actions/runs/37608342979 . No failed CI run on the PR.
- Push run on `main` for `40a1942`: `success` — https://github.com/myungjoo/HIL-Claw/actions/runs/37608557914 .
- Wall clock: about 17 minutes (10:22 to 10:38 UTC).

**Language**: Python, because the three modules it joins are Python.

**Follow-ups left** (none new beyond the planner's list above): the replacement of the runtime `STATE.json` on disk with sub-questions ⑩ and ⑫ (P1-8); the first journaled tool on top of this module (P1-1). A note for that tool: `step_state` answers `NO_LINE` for a step that ended before the stored position, so a tool whose steps can be about an earlier round needs sub-question ① of OD-17 answered first.
