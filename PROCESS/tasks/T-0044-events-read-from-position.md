---
id: T-0044
title: Let hilclaw.events.read start at a line position (the reader of ADR-0011 decision 6 and ADR-0012 Consequences) with the "position beyond the end of the log" error, and add its tests
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [OD-17, OD-8, FR-13, NFR-1, NFR-2, "#8 M7", "#4 §1"]
dependsOn: [T-0027, T-0041, T-0042]
touchesFiles: [hilclaw/events.py, tests/test_events.py]
estimatedSize: {loc: 40, files: 1}   # non-test: an edit of one existing module; the test file is excluded from the cap (D4)
hq: []   # implements closed decisions (ADR-0006 decisions 2, 4, 6; ADR-0011 decision 6; ADR-0012 decision 5 and Consequences); closes no OD, writes no ADR, standard library only, changes no file format
---
## Why
Two accepted records name this code and nothing has implemented it yet:

- **ADR-0011** (`ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md`) decision 6, *Replay*: "the current view is the stored view folded further over the **tail**, the complete lines after the position"; *Disagreement*: "A position beyond the end of the log is an error of the kind of a damaged line (ADR-0006 decision 6): the stored view is not used, the error is reported and not repaired by the reader". Consequences: "`read` reads the whole file, so the code slice adds a reader that starts at a line position".
- **ADR-0012** (`ARCHITECTURE/decisions/ADR-0012-od8-runtime-state-file.md`) Consequences: "**The reader of `events.ndjson` from a position** takes a line count as its only argument: it passes over that many line feeds without parsing, returns the complete lines after them, and reports the error of ADR-0011 decision 6 when the file holds fewer complete lines." Decision 5 fixed that the position is a line count and that there is no byte offset.

The fold (`hilclaw/journal.py`, T-0041) and the stored view (`hilclaw/run_state.py`, T-0043) exist. What is missing between them is the function that returns the tail of the log of a run. With it, `journal.fold(tail, stored_view)` can be computed from files.

It ticks **no PLAN checkbox** (a slice of P1-8, and a prerequisite of the first journaled tool of P1-1).

Why this item now (planner, DRIVER §6, 2026-10-07 UTC, judged from the files):
- P0.5-3 is BLOCKED on HQ-0003 (T-0014). The verification half of P1-3 (T-0036), P1-4 and the "harness pass" half of P0.5-1 wait for HQ-0004. Both are unanswered. The rest of P0.5-4 is the owner's hook registration. P1-1 has no tool with a fully decided contract; P1-5 slice 3 needs owner values.
- The other open slice of P1-8, the file side of the runtime `STATE.json`, has to judge a write technique and sub-question ⑩ first; this one needs nothing that is not written in the three records, and no owner answer.
- No open PR at planning time. No existing TODO / INTERRUPTED task file.

**Why an edit of `hilclaw/events.py` and not a split or a new module** (planner's reading — the reviewer is asked to re-check it). Earlier notes (T-0027 Follow-up (d), T-0041 Follow-ups, the journal of 2026-10-07) say that `hilclaw/events.py` is "at 299 of 300 lines" and that a split comes first. The cap of DRIVER §5 (D4) is "≤ 300 LOC **변경**·≤ 5 파일" per task: it bounds the change of a task, not the length of a file, and no rule of CLAUDE.md, DRIVER.md, the skills, `pyproject.toml` or CI bounds the length of a module (searched at planning time). The reader needs exactly what `events.read` already does — the path, the regular-file check, the split at the line feed, the strict parse of a line, the envelope check, the error messages with line numbers — and all of it is private there. A second module would have to copy that code or make it public, and a split would move tested code and rewrite parts of an 1100-line test file for no change of behaviour. One optional argument on `read` is about 15 changed code lines. So: **do not split the module and do not create a new one for the sake of a line count**; keep the additions short. If the executor or the reviewer finds a written rule that bounds a module's length, return BLOCKED ("requirement unclear") quoting it, instead of splitting silently.

A-13 check (planner's reading — the reviewer is asked to re-check it):
- "데이터 plane 스키마 변경": none. No file format, member or rule of the data plane changes; what a line is, what damage is and what a torn tail is stay as ADR-0006 has them. With the default position the function accepts, returns and reports exactly what it does today.
- No new external dependency: standard library only; `pyproject.toml` unchanged.
- The cases the records leave unsaid are listed below with a recommended provisional convention each. If the executor or the reviewer reads one as a design choice that needs a record or the owner, that is BLOCKED with the exact question.

Known risk, accepted: ADR-0006, ADR-0011 and ADR-0012 are inside their objection windows (until 2026-10-14). An objection creates a reverting task and this change is revisited with it.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED, never worked around), §3 "BLOCKED 사유" paragraph, §9
- ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md — **decision 6 (lines 79-92)**, in particular *Replay*, *Bound* (line 88: "The bound is on lines interpreted, not on bytes passed over") and *Disagreement* (line 89); Consequences line 160; sub-question ① (line 173)
- ARCHITECTURE/decisions/ADR-0012-od8-runtime-state-file.md — decision 4 line 69 (`position` is an *integer* of ADR-0001), **decision 5 (lines 76-80: line count alone, a carriage return before a line feed)**, decision 6 line 90 (what only a reader of both files sees), **Consequences line 135**
- ARCHITECTURE/decisions/ADR-0006-od8-events-log.md — decisions 2 (lines 28-34: a line, missing and empty file), 4 (55-58: a complete line keeps its line number), 5 (60-64), **6 (66-72: torn tail, damage reported with its line number, nothing repaired)**, 9 (87-89: "a reader can start at any line start")
- ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md line 34 (*integer*: 0 to 2^53 − 1)
- **`hilclaw/events.py` — the whole file (299 lines)**: the module docstring (lines 1-38, its conventions — "Arguments are checked before the file system is looked at"), `Log` (85-89), the three error types (92-101), `read` (176-207), `_fail` / `_member` (227-239), `_root` / `_lstat` (256-272), `_object` / `_nan` (275-283)
- `hilclaw/journal.py` lines 66-72 (`SpendView`), 95 (`EMPTY`) and 133-175 (`fold(lines, view)`: `position` grows by the number of lines; "Folding a tail from the view of its prefix gives the view of the whole") — **not edited**; `hilclaw/keys.py` line 30 (`MAX_INTEGER`)
- `tests/test_events.py` — lines 1-110 (constants, `ev`, `line`, `root`, `place`, `snapshot`, the `EXAMPLE` bytes of ADR-0006), the tests of `read` at lines 264-336 and 861-1050 (style of the parametrised negative cases; how the message and the line number are asserted)
- PROCESS/tasks/T-0027-events-log-module.md `## Result` (the provisional conventions of the module as landed); PROCESS/tasks/T-0041-journal-fold-and-step-state.md `## Result` ("Public API as landed")
- CLAUDE.md — 상시 규칙: "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" ①-⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- .claude/skills/dev-item-address/SKILL.md (procedure); .claude/skills/dev-code-review/SKILL.md (what the reviewer checks)
- `.github/workflows/ci.yml` — five checks run on a PR; no new module, so the `Test presence (hilclaw)` job needs nothing new
- Issue #5: every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6034226175 (the ADR-0012 notice; `gh issue view 5 --repo myungjoo/HIL-Claw --comments`). If the owner has objected to ADR-0006, ADR-0011 or ADR-0012 in a way that changes a rule used here, do not start: return BLOCKED ("requirement unclear") quoting the comment

## Acceptance Criteria
The records fix what the reader does. The name of the argument, the error type and the handling of the cases the records do not mention are **conventions chosen by this task, provisional**: state each with one line of reason in the commit body, the PR body and `## Result`. Where a criterion below and a record disagree, **the record wins**: follow it and say so in `## Result`.

### Files
- `hilclaw/events.py` (edited; about 15 changed code lines plus docstring lines, at most about 40 changed lines in all).
- `tests/test_events.py` (edited: **tests are added; no existing test is changed or removed** — every existing test must pass as it is, which shows that the default behaviour is unchanged).
- Python, because the module is Python — one line in the commit body and `## Result`.
- Nothing else. `hilclaw/journal.py`, `hilclaw/run_state.py`, `hilclaw/layout.py`, `hilclaw/keys.py`, `pyproject.toml`, `.github/` and every other test stay as they are.

### The capability
`read` gains one optional argument, the **position**: a number of complete lines (recommended: `read(data_root, run_id, position=0)`; say whether it is keyword-only and why).

1. **With position 0 (the default)** the function is exactly what it is today: same result, same errors, same messages.
2. **With position *p*** it returns a `Log` whose `events` are the complete lines after the first *p* complete lines, in the order of the file, and whose `torn_tail` is as today. `Log` keeps its two members (no member is added: the position after the read is *p* plus the number of events, which the caller can compute).
3. **The first *p* lines are passed over without being interpreted**: not decoded, not parsed, not validated. A damaged line or a line of another version among them is **not** reported (ADR-0012 Consequences: "passes over that many line feeds without parsing"; ADR-0011 *Bound*). The lines are counted by line feeds only, so a carriage return before a line feed changes nothing (ADR-0012 decision 5).
4. **A line after the position that is damaged or of another version** is reported as today, and the line number in the message is **its number in the file, from 1** (the line after position *p* is line *p* + 1), since a complete line keeps its line number (ADR-0006 decisions 4 and 6).
5. **A file with fewer than *p* complete lines** — a missing or an empty file with *p* ≥ 1 included, and a torn tail never counted as a line — raises the "position beyond the end of the log" error: nothing is returned, nothing is repaired, the file is not changed. The message names the path (relative to the data root, as the other messages do), the position asked for and the number of complete lines the file holds. *p* equal to the number of complete lines is **not** an error: it gives no event (the usual case just after a round ended).
6. **A path that is not a regular file** raises `CorruptEventsError` as today, whatever the position.
7. The function still writes nothing, and does not modify its arguments.

How the bytes before the position are passed over (one `read_bytes` and a split as today, or a chunked scan for line feeds) is the executor's: the records bound the lines interpreted, not the bytes read. Say which was chosen in `## Result`.

### Constraints
- **Standard library only.** No new module, no new public function is required (if you judge a separate public name better than an argument, say why; it must still live in `hilclaw/events.py` and `read` with no position must stay as it is).
- **No kind and no member of `data` is known to this module** (its docstring, last paragraph): the reader does not fold, does not look at `step_started` / `step_ended`, does not read `STATE.json`, and does not import `hilclaw.journal` or `hilclaw.run_state`.
- **No byte offset** anywhere in the interface (ADR-0012 decision 5; sub-question ⑬ is open).
- **No decision of a boundary**: nothing about who folds or how the result reaches the Round-Manager (OD-23), when a stored view is checked against a full fold (OD-17 sub-question ③), an index for steps about earlier rounds (sub-question ①), lines of another version (OD-11), a lock.
- `validate`, `append` and `remove_torn_tail` are not changed. The module docstring is updated only where a sentence became incomplete.
- Runs on CPython 3.11 and 3.14, the same on POSIX and Windows.

### Cases the records leave unsaid — choose, implement, test and list each with one line of reason
- **The error type of "beyond the end of the log".** ADR-0011 calls it "an error of the kind of a damaged line". Recommended: a subclass of `CorruptEventsError`, so that a caller that handles damage handles it too and a caller that must tell the two apart can; a plain `CorruptEventsError` is the alternative. Choose and say.
- **A position that is not a valid argument**: not exactly `int` (`True`, `1.0`, `"1"`, `None`), negative, or above `keys.MAX_INTEGER` (ADR-0012 decision 4: the position is an *integer* of ADR-0001; note that `journal.SpendView` accepts a larger one in memory). Recommended: `InvalidEventError` ("an event or an argument breaks…"), raised before the file system is looked at, as the module does for its other arguments; say what the order is between this check and the check of `run_id`.
- A missing file or a missing run directory with position 0 (no event, as today) and with position ≥ 1 (beyond the end).
- A file whose first *p* lines include blank lines or bytes that are not UTF-8: passed over and counted (criterion 3).
- A file that holds exactly *p* complete lines and a torn tail: no event, `torn_tail` reported, no error.
- Anything else you meet. If you read one as a change of what ADR-0006 calls a line, damage or a torn tail, or as a rule about `STATE.json`, return BLOCKED with the exact question.

### Tests (excluded from the size cap; added to `tests/test_events.py`)
Helpers live in the test file and get no tests of their own (test rule ⑤). Synthetic values only.
- happy: for the three lines of the Example of ADR-0006 (`EXAMPLE`), positions 0, 1, 2 and 3 return the last 3, 2, 1 and 0 events, equal to the corresponding slice of `read` without a position; lines appended with `append` are read back from a position; position 0 given explicitly equals the default.
- the replay property, with the two lines of the Example of ADR-0011 written to a file and one more start line (as in the Example of ADR-0012): for every position *p* from 0 to 3, `journal.fold(read(…, p).events, journal.fold(read(…).events[:p])[0])[0]` equals `journal.fold(read(…).events)[0]`. (A test may import `hilclaw.journal`; the module must not.)
- branch: a damaged line, a blank line, a line that is not UTF-8 and a line of another version **before** the position are not reported; CR LF line ends before and after the position; a torn tail with a position below and equal to the number of complete lines (its length reported, the file unchanged — compare `snapshot` before and after); `data_root` given as `str`; two runs have two files.
- error / negative (assert the error type and that the message names the path, the position and the count where the criterion says so): position beyond the end for a file of 0, 1 and 3 lines, for a missing file, for a missing run directory, and for a file whose only bytes beyond the complete lines are a torn tail; a damaged line and a line of another version **after** the position, with the line number of the file in the message (for example position 1 and damage on line 3 → "line 3"); each invalid position argument listed above, with nothing read (the data root may even be missing if the argument check comes first — assert what you chose); a directory or a symbolic link in the place of the file with a position ≥ 1; an invalid `run_id` with a position.
- Test rules of CLAUDE.md / DRIVER §5 (D12): ① `hilclaw/` keeps line and function coverage ≥ 80 % — coverage is not measured by CI yet (P0.5-3 BLOCKED on HQ-0003), so check that the tests reach every changed line, for example with `python -m trace --count --missing --coverdir <directory outside the repository> --module pytest tests/test_events.py`, and say how in `## Result`; ② happy, error, branch and negative cases as above; ③ every public function of the touched module is tested — `validate`, `append`, `read` and `remove_torn_tail` already are, and the new behaviour of `read` (and any new public name, such as the error type) gets the tests above; ④ no new module; ⑤ no tests for test code, CI workflows or helper scripts.

### Verification (record summary lines and run URLs in `## Result`)
- Local, before the commit and before the merge, from the repository root: `python -m pytest` exits 0 (record pass and skip counts; before this task: 4378 passed, 133 skipped on CPython 3.14 on Windows), `python -m ruff check .` and `python -m ruff format --check .` exit 0 (ruff 0.16.10, pytest 9.1.1).
- `git ls-files --eol` shows `i/lf` for both files; `git status --short` after the tests shows no stray file; `git diff origin/main --stat` lists only the two files of `touchesFiles`; `git diff origin/main -- tests/test_events.py` shows additions only (an added import line is fine).
- CI on the PR: `gh pr checks <PR> --watch` ends with **five** successful checks on the final head — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)`. Merge only then.
- After the squash-merge, check the `push` run on `main` (`gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"`) and record its conclusion; if it is not `success`, do not fix forward on `main`: record it and say so in the returned summary.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0044'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0044 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (none at planning time; a PR touching `hilclaw/events.py` or `tests/test_events.py` is BLOCKED "open PR conflict").
- Code mode: branch `claude/T-0044-events-read-from-position` from `origin/main`; Draft PR with the `DONOTMERGE` label; PR title contains `T-0044`; executor commits end with the trailer `Task: T-0044`.
- Install nothing. After a failed CI run, read the whole failed log (`gh run view <id> --log-failed`) and fix every diagnostic before pushing again. Three consecutive failed CI runs on the PR: stop and return BLOCKED ("CI 3 consecutive failures") with the last log excerpt in `## Result`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds; if the cap is passed without a final Approve, return BLOCKED). Keep docstrings exact and short so that rounds are not spent on wording. Ask the reviewer explicitly to (a) compare the behaviour with ADR-0011 decision 6 (*Replay*, *Bound*, *Disagreement*), ADR-0012 decision 5 and Consequences line 135, and ADR-0006 decisions 2, 4 and 6, sentence by sentence — nothing before the position interpreted, the tail returned, the error for fewer complete lines, the torn tail never a line, line numbers of the file; (b) confirm that `read` without a position is unchanged and that no existing test was edited; (c) re-check the planner's readings in `## Why` — the D4 cap bounds the change and not the length of `hilclaw/events.py` (311 lines or so after this task), and A-13 "data-plane schema change" does not apply; (d) re-check each convention under "unsaid", in particular the error type and the argument check of the position; (e) report anything the code decides that the records list under Boundaries (a byte offset, a fold, who folds, a check against `STATE.json`, another version). If the reviewer reads a point as a design choice needing a record or the owner, return BLOCKED with the question. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm the five checks on the final head, then `gh pr merge <PR> --squash --body-file <file outside the repository>` with the PR body, whose **last line is `Task: T-0044`**. Delete the remote branch and the local branch in **separate** commands and only after `gh pr view <PR> --json state` reports `MERGED`.
- Commit body: the provisional choices (the argument and its form, the error type, each unsaid case, how the bytes before the position are passed over) with one line of reason each, and the language line.
- `## Result`: fill it in **after** the merge, on `main`, and leave that edit **uncommitted** — the driver commits it (DRIVER §3-6). The branch and the PR must not contain this task file. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. Record: PR and commit, review rounds and findings, the signature as landed, the provisional choices and unsaid cases, the verification outcomes, the line count of `hilclaw/events.py`, the language line, and that this task ticks **no** PLAN checkbox.
- Size: about 40 changed non-test lines in 1 file; the cap is 300 LOC / 5 files (tests excluded).
- If a record turns out to be ambiguous or self-contradictory on a point the code must decide and that is not one of the provisional conventions above, do not guess and do not edit the ADR: return BLOCKED ("requirement unclear") with the exact question.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- A split of `hilclaw/events.py`, a new module, or making its private helpers public.
- Any function that reads both `STATE.json` and the log: the current view of a run (stored view folded over the tail), the lookup of an identity from files, the comparison of a stored view with a full fold and its report.
- The file side of the runtime `STATE.json` (reading it from its path, replacing it on disk); every other member of that file; `instance.json`; the result files of an attempt.
- A byte offset, an index of the log, rotation or size limits of the log, reading lines of another version.
- A command line entry, a tool or any registration in `hilclaw/tools.py`; any use of `hilclaw.config` or of the real data repository `HIL-Claw-data`.
- Sub-questions ① ② ③ of ADR-0011, ⑩ to ⑬ of ADR-0012, the rest of OD-17, anything of OD-2, OD-3, OD-10, OD-11, OD-19, OD-20, OD-23, OD-29.
- Any edit of another module or test, `pyproject.toml`, `.github/`, `.claude/`, `README.md`, any ADR, the OD register, OpenDecisionProposals, CLAUDE.md, DRIVER.md, PLAN.md, the skills, the agents.
- Answering HQ-0003 or HQ-0004 on the owner's behalf.

## Follow-ups
- (planner, next code slice, P1-8) A small module of its own over files: the current spend view of a run and the state of an identity from `STATE.json` and the tail (`run_state.parse`, `events.read` from the stored position, `journal.fold` / `journal.step_state`), with the report when the position is beyond the log. To judge then: how much of it needs the file side of `STATE.json` first, and that it decides nothing of OD-23 (who folds) or of sub-question ① (steps about earlier rounds).
- (planner, code mode, P1-8) The file side of the runtime `STATE.json`: reading the file of a run through `layout.run_file`, and the replacement that leaves the old or the new content. To judge then: whether the technique needs a record (ADR-0004 decision 7 allows no scratch path under `runs/`) and how far sub-question ⑩ must be closed first; the round-trip limits in T-0043 `## Result`.
- (unchanged) The first journaled tool of P1-1; the T-0041 question for a revision of ADR-0011; the integrator items after 2026-10-14 (T-0040 and T-0042 Follow-ups).

## Result
