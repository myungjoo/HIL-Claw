---
id: T-0041
title: Add the journal module (hilclaw/journal.py) with the pure functions of ADR-0011 over parsed event lines - check of the two step lines, identity, fold into a spend view, state of an identity - and its tests
phase: P1
status: DONE
commitMode: code
coversReq: [OD-17, NFR-1, NFR-2, FR-3, FR-13, C-4, "#8 M7"]
dependsOn: [T-0026, T-0027, T-0040]
touchesFiles: [hilclaw/journal.py, tests/test_journal.py]
estimatedSize: {loc: 220, files: 1}   # non-test: one new module; the test file is excluded from the cap (D4)
hq: []   # implements a closed decision (ADR-0011 decisions 3, 4, 6, 7); closes no OD, writes no ADR, standard library only, touches no file of the data plane, defines no member of STATE.json
---
## Why
**ADR-0011** (`ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md`, landed as `ab6f03a`, T-0040) fixed what `events.ndjson` holds around a *journaled step* (a `step_started` line and a `step_ended` line, tied by an *identity*), what a repeated call and a resumed turn may conclude from the three states of an identity (no line / open / ended), and how the spend of a run is accounted (the *fold* into a *spend view*: a total per axis, the position, the open steps). Its Consequences name the code that follows: "`read` reads the whole file, so the code slice adds a reader that starts at a line position, the fold, and the lookup of an identity". T-0040 `## Result` repeats it as a follow-up for the planner.

`hilclaw/events.py` (ADR-0006) knows no kind and no member of `data`, and it is at 299 of 300 lines, so the rules of ADR-0011 need a module of their own. The route used so far is record first, then a module that implements it (T-0026 → T-0027, T-0028 → T-0029). **This task is the first code slice after ADR-0011: the pure part** — functions over event lines that are already parsed, with no file access. The reader that starts at a position (the file side, with the "position beyond the end of the log" error) is the next slice and is **not** in this task: it needs the strict line parsing that is private to `hilclaw/events.py`, which is a separate question of where that code lives.

It ticks **no PLAN checkbox** (a slice of P1-8 and a prerequisite of the first journaled tool of P1-1).

Why this item now (planner, DRIVER §6, 2026-10-07 UTC, judged from the files):
- P0.5-3 is BLOCKED on HQ-0003 (T-0014). The verification half of P1-3 (T-0036), P1-4 and the "harness pass" half of P0.5-1 wait for HQ-0004. The rest of P0.5-4 is the owner's hook registration in `.claude/settings.json`. P1-1 has its registry and both fronts and no tool with a fully decided contract. P1-5 slice 3 needs owner values. Both HQs are unanswered.
- This slice needs nothing that is not written down in ADR-0011, and no owner answer.
- No open PR at planning time. The latest comment on #5 is the ADR-0011 notice (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6032614222); no objection to ADR-0001..0011.

A-13 check (planner's reading — the reviewer is asked to re-check it):
- "데이터 plane 스키마 변경(STATE/spec/eval/artifacts)": the module is the **first implementation** of rules ADR-0011 already fixed (precedents: T-0018, T-0025, T-0027, where every reviewer read the BLOCKED reason as not applying). It must add, rename or remove **no kind, no member of `data` and no rule**. The spend view it returns is a **Python value in memory**: ADR-0011 decision 6 leaves "the form of these members" in `STATE.json` to PLAN P1-8, and nothing here may be presented as that form.
- No new external dependency: standard library only; `pyproject.toml` unchanged.
- Where ADR-0011 leaves a case unsaid, the criteria below recommend a provisional convention. If the executor or the reviewer reads one as a design choice that needs a record or the owner, that is BLOCKED with the exact question, not something to decide silently.

Known risk, accepted: ADR-0011 and the records it builds on (ADR-0004, 0006, 0010; ADR-0002) are inside their objection windows (until 2026-10-14 / 2026-10-13). An objection creates a reverting task and this module is revisited with it.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED, never worked around), §3 "BLOCKED 사유" paragraph, §9
- **ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md — the whole record**; in particular decision 1 (terms), **3** (the table of the two kinds, identity, the repeated call), **4** (the table of the three states), **6** (fold, the stored view, tail, *Disagreement*, the last bullet about the lookup), **7** (`spend`), 8, 9, the Example with the table of the three death points, Consequences, Boundaries (sub-questions ① ② ③)
- ARCHITECTURE/decisions/ADR-0006-od8-events-log.md — decisions 3 (envelope; `round`, `candidate`, `attempt`), 4 (order), 5, 6, 8; ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md — decision 1 (the value types *name* and *integer*); ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md — decision 4 ("Result or tool failure")
- `hilclaw/events.py` (whole file — `validate`, `read`, `Log`, the error types, the conventions in the module docstring; **not edited**); `hilclaw/tools.py` lines 1-48 and `check_json_object` (what a result object is; `ToolFailure(kind, message)`; **not edited**); `hilclaw/keys.py` (`MAX_INTEGER`; the *name* check is private there)
- `hilclaw/harness/measurement.py` and `tests/harness/test_measurement.py` — the closest sibling in kind (pure functions after a record: docstring style, argument checks, test style); `tests/test_events.py` — how event lines are built in tests
- PROCESS/tasks/T-0040-adr-od17-journal-and-spend.md `## Result` ("Decisions of ADR-0011", "Three death points", "Provisional readings", Follow-ups); PROCESS/tasks/T-0027-events-log-module.md `## Result` ("Public API as landed", "Known limits", follow-up (d))
- CLAUDE.md — 상시 규칙: "세 층 모델", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" ①-⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- .claude/skills/dev-item-address/SKILL.md (procedure); .claude/skills/dev-code-review/SKILL.md (what the reviewer checks)
- `.github/workflows/ci.yml` — job `Test presence (hilclaw)`: `hilclaw/journal.py` needs `tests/test_journal.py`; five checks run on a PR. `pyproject.toml` (no runtime dependency, `requires-python >= 3.11`)
- Issue #5: every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6032614222 (`gh issue view 5 --repo myungjoo/HIL-Claw --comments`). If the owner has objected to ADR-0011, or to ADR-0006 / 0010 in a way that changes a rule used here, do not start: return BLOCKED ("requirement unclear") quoting the comment

## Acceptance Criteria
ADR-0011 fixes the two kinds, the members of their `data`, the identity, the three states, the fold and what `spend` is. The module name, the public names, the Python shapes of what is returned, the error types and the handling of the cases the record does not mention are **conventions chosen by this task, provisional**: state each with one line of reason in the commit body, the PR body and `## Result`. Where a criterion below and ADR-0011 disagree, **the ADR wins**: follow it and say so in `## Result`.

### Files
- `hilclaw/journal.py` (new; about 180-240 lines; provisional name — if you judge another name better say why; the Test presence job must pass **without an edit of `.github/`**).
- `tests/test_journal.py` (new).
- Python, because the event log module is Python — one line in the commit body and `## Result`.
- Nothing else. `hilclaw/events.py`, `hilclaw/tools.py`, `hilclaw/keys.py`, `hilclaw/layout.py`, `pyproject.toml` and every existing test stay as they are.

### Constraints
- **Standard library only**, plus public names of `hilclaw.events`, `hilclaw.keys` (`MAX_INTEGER`) and `hilclaw.tools` (`check_json_object`, if used for `result`). Do not import a private name of another module and do not edit one: restate the *name* pattern of ADR-0001 where needed.
- **Pure functions**: no file access, no `data_root`, no call of `events.read` or `events.append`, no clock, no random source, no configuration, no environment variable, no global state. Arguments are not modified. The same input gives the same output.
- **No append and no execution of a step**: the module does not write the start or the end line and does not run anything. Where the appending part of the tool layer sits is the rest of OD-18.
- **No step name, no axis name, no result member**: none is defined, listed, special-cased or presented as valid, in the module or in the tests. Tests use placeholders such as `example_step`, `example_axis`, `example_member` (as the Example of ADR-0011).
- **No decision about an open step**: no retry, no wait, no further `execution` chosen or computed, no "next free execution" helper (OD-10, the retry part of OD-17, ADR-0011 decision 9 "a caller that changes the identity").
- **No enforcement and no budget**: nothing compares a total with a limit (OD-19).
- **No `STATE.json` form**: no function that writes, reads or checks `budget_spent` as stored, no JSON form of the spend view, no byte offset (PLAN P1-8).
- Runs on CPython 3.11 and 3.14, the same on POSIX and Windows.

### Capabilities (provisional names and shapes; each must exist and every public name must be tested)
1. **Check the `data` of a step line** — for an event whose `kind` is `step_started` or `step_ended`, the table of decision 3 and decision 7, "exactly these" members:
   - `step`: a *name* (`[a-z][a-z0-9_]{0,31}`), checked against **no** vocabulary; `execution`: an *integer* ≥ 1 (exactly `int`, not `bool`, at most `keys.MAX_INTEGER`);
   - `step_started`: exactly `step` and `execution`;
   - `step_ended`: `step`, `execution`, `spend`, and **exactly one** of `result` and `failure` (both and neither are errors);
   - `spend`: an object, possibly empty, from an axis *name* to a non-negative *integer* (exactly `int`, not `bool`, not `float`, 0 to `keys.MAX_INTEGER`);
   - `result`: an object (ADR-0010: the result object of the call); its members are not looked at;
   - `failure`: "holds the `kind` and `message` of the tool failure" — recommended reading: an object with exactly `kind` (a *name*, as `tools.ToolFailure` requires) and `message` (a `str`); say that the exactness is this module's reading.
   The error names the member and the rule. An event of any other kind is not this function's business (choose: returned untouched / refused — say which). Whether the function also runs `events.validate` on the envelope or assumes it: choose and say.
2. **Identity of a step line** — a hashable value built from those of `round`, `candidate`, `attempt` the line carries (absent is distinct from every number) together with `step` and `execution` (decision 3). A constructor a caller can use to name the identity it wants to look up, with the same argument checks as the envelope and capability 1 (`candidate` only with `round`, `attempt` only with `candidate`).
3. **Fold** (decisions 6 and 7) — from a spend view and a sequence of events **in the order of the file**, the spend view after them:
   - totals: per axis, the sum of every `spend` of every `step_ended` line; **an end line is counted whatever else the log holds for its identity**;
   - position: the number of lines folded, **lines of every kind counted** (the position is a count of complete lines of the file);
   - open steps: the identities that have a start line and no end line;
   - the empty view (no total, position 0, no open step) is public, and is the default starting view;
   - **reports**: an end line whose identity is not open — "a second end line, or one without a start line" — is counted **and reported** (decision 6 *Disagreement*); the fold returns such findings to the caller and raises nothing for them. Recommended: the returned value holds the view and a list of findings, each with the identity and the index of the line;
   - the defining property, which the tests must show: for every split of a sequence into a prefix and a tail, folding the tail from the view of the prefix gives the same totals, position and open steps as folding the whole sequence from the empty view.
4. **State of an identity** (decisions 3 and 4) — from a starting view and a sequence of events, one of the three states: *no line*, *open*, *ended*; for *ended*, what the end line holds (the `result`, or the `failure`, and its `spend`), so that a caller can return it for a repeated call. An identity that is open in the starting view and has no end line in the sequence is open. The docstring must state the limit of decision 6: with a starting view that is not empty, an identity that **ended before the position** is not visible, and the answer is right only for a step whose lines lie after the position (the round in progress) or for the empty view with the whole log (sub-question ① — not solved here).

### Cases ADR-0011 leaves unsaid — choose, implement, test and list each with one line of reason
- A `step_started` or `step_ended` line whose `data` breaks the table (as met by the fold and by the state lookup). Recommended: raise an error that names the index of the line — never skip it silently and never count part of it; ADR-0006 decision 6 defines damage for the envelope only, so say that this is the module's convention and not a new damage rule.
- A **second start line** of an identity that is open, and a start line of an identity that already ended (two turns at once, decision 9; a caller that broke "an identity is never started twice"). Recommended: report it like the end-line findings; the identity stays open in the first case; say what the state is in the second.
- **Two end lines** of one identity: which one the state lookup returns. Recommended: the first in file order, because lines are never edited and an answer already given to a repeated call must not change when the log grows; both `spend` values are counted by the fold.
- The findings of a fold over a tail and of a fold from the first line can differ in wording (an identity that ended before the position looks like "no start line" from the tail): one category "end line whose identity is not open" is enough — say what is reported.
- A total above `keys.MAX_INTEGER` after summing (Python integers do not overflow): recommended to keep the exact sum and raise nothing; whether a stored form can hold it is PLAN P1-8.
- An axis whose amounts are all 0: whether it appears in the totals with 0 or not — choose; it must not break the split property.
- The Python types accepted for the sequence (a list, any iterable, a generator consumed once) and for the starting view; what is returned must not share mutable state with the arguments.
- A starting view that is not well formed (a negative position, a total that is not an integer ≥ 0, an open step that is not an identity): an argument error, before any line is folded.
- Lines of other kinds, with any `data`: counted in the position, otherwise ignored.
- `execution` 0, negative, `True`, a float; `spend` holding `True`, `1.0`, `-1`, `None`, a nested object, a member name that is not a *name*; `data` with an extra member; `result` `null` or a list; `failure` a string.
- Anything else you meet. If you read one as a rule about **what is done with an open step**, about a budget, or as the form of `budget_spent` in `STATE.json`, return BLOCKED with the exact question.

### Tests (excluded from the size cap)
Helpers that build event lines live in the test file and get no tests of their own (test rule ⑤). Build the lines as `dict` values that `events.validate` accepts.
- happy: the two lines of the Example of ADR-0011 as written in the record pass the check; their identities are equal; folded from the empty view they give the total `{"example_axis": 7}`, position 2 and no open step; the state of that identity is *ended* with the `result` and the `spend` of the line. A start line alone → *open*, position 1, one open step, no total. No line → *no line*. Run-level, round-level, candidate-level and attempt-level identities are distinct from one another, and so are two values of `step` and two of `execution`.
- branch: an end line with `failure` → *ended*, the failure and its `spend` returned, the amounts counted (decision 7); an empty `spend`; several axes on one line and one axis on several lines; lines of other kinds between the two lines; the **three death points** of the record's table — a log cut before the start line, between the two lines, after the end line — give *no line*, *open* (nothing counted, the step listed as open) and *ended* (counted once); an end line appended later for an open identity ends it and its amounts are counted from then on; a state lookup from a view that holds the identity as open, with and without the end line in the tail; the **split property** for every split point of a sequence of a dozen mixed lines (several identities, open ones, findings included); the arguments are unchanged after each call; a generator as the sequence, if accepted.
- error / negative (assert the error type and that the message names the member or the line index): every malformed `data` listed under capability 1 and under "unsaid"; `step_ended` with both `result` and `failure`, and with neither; `step_started` with `spend`; a second end line and an end line without a start line → counted and reported, nothing raised; a second start line as chosen; a malformed step line in the middle of a sequence for the fold and for the lookup, as chosen; a malformed starting view; an identity argument that breaks a rule (`attempt` without `candidate`, `execution` 0, a `step` that is not a *name*).
- Test rules of CLAUDE.md / DRIVER §5 (D12): ① `hilclaw/` keeps line and function coverage ≥ 80 % — coverage is not measured by CI yet (P0.5-3 BLOCKED on HQ-0003), so check that the tests reach every line of the new module, for example with `python -m trace --count --missing --coverdir <directory outside the repository> --module pytest tests/test_journal.py`, and say how in `## Result`; ② happy, error, branch and negative cases as above; ③ every public name of the module is tested; ④ the new module has its test file; ⑤ no tests for test code, CI workflows or helper scripts.

### Verification (record summary lines and run URLs in `## Result`)
- Local, before the commit and before the merge, from the repository root: `python -m pytest` exits 0 (record pass and skip counts), `python -m ruff check .` and `python -m ruff format --check .` exit 0 (ruff 0.16.10, pytest 9.1.1).
- `git ls-files --eol` shows `i/lf` for both files; `git status --short` after the tests shows no stray file; `git diff origin/main --stat` lists only the two files of `touchesFiles`.
- CI on the PR: `gh pr checks <PR> --watch` ends with **five** successful checks on the final head — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)`. Merge only then.
- After the squash-merge, check the `push` run on `main` (`gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"`) and record its conclusion; if it is not `success`, do not fix forward on `main`: record it and say so in the returned summary.

### Process
- First the §3-5 landed check: `git log origin/main --grep='^Task: T-0041'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0041 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (none at planning time; a PR touching `hilclaw/journal.py`, `hilclaw/events.py` or their test files is BLOCKED "open PR conflict").
- Code mode: branch `claude/T-0041-journal-fold-and-step-state` from `origin/main`; Draft PR with the `DONOTMERGE` label; PR title contains `T-0041`; executor commits end with the trailer `Task: T-0041`.
- Install nothing. After a failed CI run, read the whole failed log (`gh run view <id> --log-failed`) and fix every diagnostic before pushing again. Three consecutive failed CI runs on the PR: stop and return BLOCKED ("CI 3 consecutive failures") with the last log excerpt in `## Result`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds; if the cap is passed without a final Approve, return BLOCKED). Keep docstrings exact and short so that rounds are not spent on wording. Ask the reviewer explicitly to (a) compare the check, the identity, the fold and the state lookup with ADR-0011 decisions 3, 4, 6 and 7 sentence by sentence — "exactly these" members, exactly one of `result` and `failure`, an end line counted whatever else the log holds, the position as a count of lines of every kind, the open steps, the three states, what is reported and not raised; (b) re-check the planner's A-13 reading in `## Why` — no kind, member or rule added, and the returned view not presented as the form of `budget_spent`; (c) re-check each convention under "unsaid", in particular the malformed step line, the second start line and which of two end lines the lookup returns; (d) report anything the code decides that ADR-0011 lists under Boundaries or Limits (a recovery for an open step, a further `execution`, enforcement, an axis, a step name, a `STATE.json` member, where the append sits, sub-questions ① ② ③); (e) confirm the module is pure (no file, clock, random source or kept state). If the reviewer reads a point as a design choice needing a record or the owner, return BLOCKED with the question. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm the five checks on the final head, then `gh pr merge <PR> --squash --body-file <file>` with the PR body, whose **last line is `Task: T-0041`**. Delete the remote branch and the local branch in **separate** commands and only after `gh pr view <PR> --json state` reports `MERGED`.
- Commit body: the provisional choices (module name, public names and shapes, error types, each unsaid case) with one line of reason each, and the language line.
- `## Result`: fill it in **after** the merge, on `main`, and leave that edit **uncommitted** — the driver commits it (DRIVER §3-6). The branch and the PR must not contain this task file. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. Record: PR and commit, review rounds and findings, the public API as landed, the provisional choices and unsaid cases, the verification outcomes, the language line, and that this task ticks **no** PLAN checkbox.
- Size: about 220 non-test lines in 1 file; the cap is 300 LOC / 5 files (tests excluded). If the module cannot stay within it, first shorten the docstrings; if that is not enough, land the check, the identity and the fold, and propose the state lookup as a split in `## Follow-ups` (DRIVER §5).
- If ADR-0011 turns out to be ambiguous or self-contradictory on a point the code must decide and that is not one of the provisional conventions above, do not guess and do not edit the ADR: return BLOCKED ("requirement unclear") with the exact question.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- Any file access: a reader of `events.ndjson` that starts at a line position or a byte offset, the "position beyond the end of the log" error, a check of a stored view against a fold from the first line (next slice; sub-question ③).
- Appending the start or the end line, running a step, a wrapper that carries out the repeated-call rule around a tool function, any tool, any registration in `hilclaw/tools.py` (PLAN P1-1; rest of OD-18).
- The `STATE.json` and `instance.json` member tables, schemas and validators; the stored form of the spend view; the `phase` marker (PLAN P1-8).
- The rest of OD-17 (lock, fencing, retry), recovery of an open step (OD-10), enforcement (OD-19), axes, units and who measures (FR-3, OD-2, #5 A-8), gates (OD-3), sub-questions ① ② ③ of ADR-0011.
- Any edit of `hilclaw/events.py`, `hilclaw/tools.py`, `hilclaw/keys.py`, `pyproject.toml`, `.github/`, `.claude/`, `README.md`, any ADR, the OD register, OpenDecisionProposals, CLAUDE.md, DRIVER.md, PLAN.md, the skills, the agents.
- Reading or changing the real data repository `HIL-Claw-data`; using `hilclaw.config`.
- Answering HQ-0003 or HQ-0004 on the owner's behalf.

## Follow-ups
- (planner, next code slice) The file side of ADR-0011 decision 6: a reader that returns the complete lines after a line position without interpreting the lines before it, with the "position beyond the end of the log" error. To judge then: `hilclaw/events.py` is at 299 of 300 lines and its strict line parsing is private, so either that module is split or a small public parsing function is moved out first; a change of what the event module accepts or reports is a data-plane schema change under A-13 (T-0027 `## Result`).
- (planner, document mode, P1-8) The record of the runtime `STATE.json` members that hang on no owner item (`schema_version`, the round pointer, `phase`, `next_action`, the stored spend view with its position and, if chosen, the byte offset), with gate status, target and tolerance left out; then its validator as a code task.
- (planner, P1-1) The first journaled tool on top of this module and the mock's fault injection for the three death points; until a recovery rule exists an open step is a point the run does not pass by itself (T-0040 Follow-ups).
- (unchanged) OD-18 sub-question ① live check and sub-question ③ (T-0039 Follow-ups); the integrator items after 2026-10-14 (T-0040 Follow-ups).
- (executor, T-0041; for a later revision of ADR-0011 — raised by both reviewers, not decided in the code) "After a start line of an identity that already has an end line, is the identity among the open steps of the spend view? Decisions 1 and 6 define open as a start line and no end line (answer: no), but the replay rule of decision 6 (the stored view folded over the tail equals the fold from the first line) cannot give that answer, because the stored view holds no ended identity." The module follows the replay rule (the identity is listed as open again) and `step_state` answers `ENDED`; the case arises only after "an identity is never started twice" was broken.
- (executor, T-0041) `hilclaw/journal.py` is at 297 of 300 lines: a later change of it starts by shortening docstrings or by moving the checks of a step line into a module of their own. The next slice (the reader from a position) should not be added to this file.
- (executor, T-0041) No task was split: the four capabilities landed together inside the cap.

## Result
**DONE** — PR #38 (https://github.com/myungjoo/HIL-Claw/pull/38), squash-merged to `main` as `39dfb30` ("T-0041: Add the journal module of ADR-0011 (step lines, identity, fold, state of an identity) (#38)"); the squash message is the PR body and its last line is `Task: T-0041`. Branch commits: `cab9a43` (implementation), `ab24521` (review round 1). The remote and the local branch were deleted in separate commands after `gh pr view 38 --json state` reported `MERGED`. This task ticks **no PLAN checkbox**. This `## Result` edit (and the three Follow-ups above marked "executor, T-0041") is **not** in the PR; it is left uncommitted on `main` for the driver's wrap-up commit.

**Language**: Python, because the event log module it builds on is Python; standard library only (`pyproject.toml` unchanged).

### Files
- `hilclaw/journal.py` (new, 297 lines — above the "about 180-240" of the task, inside the 300 LOC / 5 files cap; the reviewers accepted it) and `tests/test_journal.py` (new, 631 lines, 160 test cases). Nothing else changed: `git diff 8e9017d 39dfb30 --stat` lists these two files only; both are `i/lf`.

### Public API as landed (all names and shapes are conventions of this task, provisional)
- `STEP_STARTED = "step_started"`, `STEP_ENDED = "step_ended"` — the two kinds of ADR-0011 decision 3.
- `JournalError(ValueError)` — a step line, an identity or a view breaks a rule; the message names the member (`data.spend.<axis>: must be …`, `view.position: …`). One type, because a caller tells the cases apart by the member named.
- `Identity(step, execution, round=None, candidate=None, attempt=None)` — named tuple; `None` is an absent envelope number, so absent differs from every number; hashable.
- `SpendView(totals, position, open_steps)` — named tuple. Returned with `totals` as a read-only mapping (`types.MappingProxyType` over a new `dict`) and `open_steps` as a `frozenset`; a view given by a caller may hold any mapping and a `set`. `EMPTY` is the view of no line and the default starting view.
- `Problem` (`END_NOT_OPEN`, `START_REPEATED`) and `State` (`NO_LINE`, `OPEN`, `ENDED`) — enumerations.
- `Report(line, identity, problem)` — a line the fold counted and reports. `StepState(state, result=None, failure=None, spend=None)` — for `ENDED`, copies of what the end line holds.
- `check_step(event)` → `None`. Runs `events.validate` on the envelope first (its errors pass through), then the table of decision 3 on `data`. An event of **another kind is refused** (`JournalError`, "kind: must be step_started or step_ended"): the function is asked about a step line.
- `identity_of(event)` → `Identity`, checked as by `check_step`.
- `step_identity(step, execution, round=None, candidate=None, attempt=None)` → `Identity`. It builds a start line from the values and checks that line, so the rules and the errors are exactly those of a line: `events.InvalidEventError` for an envelope number (`candidate` only with `round`, `attempt` only with `candidate`), `JournalError` for `step` or `execution`.
- `fold(lines, view=EMPTY)` → `(SpendView, reports)`, `reports` a tuple of `Report` in the order of the lines.
- `step_state(identity, lines, view=EMPTY)` → `StepState`. The docstring states the limit of decision 6 (an identity that ended before the position of `view` is not visible; sub-question ① is not solved).

### Provisional readings and the cases ADR-0011 leaves unsaid (each as implemented and tested)
- `failure` is read as an object with **exactly** `kind` (a *name*, as `tools.ToolFailure` requires) and `message` (a `str`) — the exactness is this module's reading of "holds the `kind` and `message` of the tool failure".
- `result` must be a `dict`; its members are not looked at. `tools.check_json_object` is not used: strictness of the JSON is the event module's concern (it reads and appends the lines), so `hilclaw.tools` is not imported.
- **Malformed step line** met by the fold or the lookup: an error with `line <number>:` in front, nothing returned — never skipped, never counted in part. The module's convention, not a new damage rule (ADR-0006 decision 6 defines damage for the envelope only). An envelope `events.validate` refuses is reported the same way with its own type (`InvalidEventError`, `UnsupportedVersionError`). The envelope is re-validated for every line, also of other kinds.
- **Line numbers** count from 1 and continue the position of the view given, so a report or an error of a tail names the same line as one of the whole log.
- **Second start line of an open identity**: reported (`START_REPEATED`); the identity stays open; state `OPEN`.
- **Start line of an identity that ended**: the fold lists the identity as open again (a view holds no ended identity, and the fold of a tail must give the view of the whole), and reports it when the end line is among the lines folded; from a tail it is not reported. `step_state` answers `ENDED` with the first end line. See the Follow-up for ADR-0011 above.
- **Two end lines**: both `spend` values are counted; the second is reported (`END_NOT_OPEN`), also when a start line stands between them and the first is among the lines folded (review round 1). The lookup returns the **first in file order**, so an answer given to a repeated call does not change when the log grows.
- **One category** for an end line whose identity is not open: from a tail, "ended before the position" and "never started" cannot be told apart.
- **A total above `keys.MAX_INTEGER`**: the exact sum is kept, nothing raised; a view given with such a total is accepted. Whether a stored form can hold it is PLAN P1-8.
- **An axis whose amounts are all 0** appears in the totals with 0 (the line named it; holds for every split).
- **`lines`** is any iterable, read once (a generator works); something that cannot be iterated raises `TypeError`. Every line is read and checked, also by the lookup after it found the end line.
- **A malformed view** (not a `SpendView`, a negative or non-`int` position, a total that is not an `int` ≥ 0, an axis that is not a *name*, an open step that is not a valid `Identity`) is refused before any line is read.
- **Lines of other kinds**, with any `data`, count in the position only.
- Integers are exactly `int` (`bool` and `float` refused), `execution` from 1 and an amount from 0, both at most `keys.MAX_INTEGER`. The *name* pattern of ADR-0001 is restated in the module (no private import).
- Nothing was read as a rule about what is done with an open step, about a budget, or as the form of `budget_spent`.

### Known limits
- `step_state` copies the `data` of the end line with `copy.deepcopy`: a `result` nested hundreds of levels deep can raise `RecursionError`, which is not a `JournalError` and is not in the docstring (review round 1, F3 — accepted as a limit).
- One malformed step line makes every fold and lookup that reads it fail, and the repository has no means to repair a line (lines are never edited). What a run does then is not decided anywhere.
- On CPython 3.11 an integer too long to print is shown as "a value too long to show"; on 3.12 and later `reprlib` prints a placeholder that holds a memory address, so that one error message is not the same from run to run.
- The fold keeps the identities that ended among the lines it reads (for the reports only): memory grows with the number of step lines of one call, not across calls.

### Review (2 rounds; a fresh-context `dev-reviewer` each, spawned with `model: opus`; no `SECURITY` finding)
Verdict sequence: **Request changes, Approve.**
- **Round 1 — Request changes** (`cab9a43`), https://github.com/myungjoo/HIL-Claw/pull/38#issuecomment-6033243323 : F1 (Medium) for `start, end, start, end` of one identity the fourth line was counted but not reported, against "a second end line … is counted and reported" (decision 6) → fixed (`identity not in open_steps or identity in ended`), docstring and test adjusted; F2 (Low) `fold` lists the identity as open while `step_state` answers `ENDED` → judged a module convention forced by the replay rule, a sentence added to the docstring of `fold`, the question recorded in Follow-ups; F3 (Low, optional) the `RecursionError` of `deepcopy` → recorded as a known limit; F4 (Nit) a vacuous assertion in the death point test → removed. Response: https://github.com/myungjoo/HIL-Claw/pull/38#issuecomment-6033281257
- **Round 2 — Approve** (`ab24521`), https://github.com/myungjoo/HIL-Claw/pull/38#issuecomment-6033338869 : no finding and no remaining nit.
- Review points: (a) the check, the identity, the fold and the lookup agree with decisions 3, 4, 6 and 7 (both rounds, after F1); (b) both reviewers agree with the planner's A-13 reading — no kind, member or rule added, the view is a value in memory and not presented as the form of `budget_spent`, the BLOCKED reason does not apply; (c) every convention under "unsaid" accepted; (d) nothing of Boundaries or Limits is decided; (e) the module is pure. Neither reviewer read a point as a design choice needing a record or the owner.

### Verification
- **Landed check** before work: `git log origin/main --grep='^Task: T-0041'` empty; `gh pr list --search T-0041 --state all` empty; no open PR. Issue #5: the latest comment was the ADR-0011 notice (6032614222), nothing after it; no objection.
- **Local** (Windows, CPython 3.14.4, pytest 9.1.1, ruff 0.16.10), before the commit, before the merge and on `main` after it: `python -m pytest` **4173 passed, 133 skipped**; `python -m ruff check .` "All checks passed!"; `python -m ruff format --check .` "112 files already formatted". `git status --short` after the tests showed no stray file.
- **Coverage** (test rule ①; not measured by CI yet): `python -m trace --count --missing --coverdir <scratch directory outside the repository> --module pytest tests/test_journal.py` reaches every line of `hilclaw/journal.py` except the two lines of the `except ValueError` branch in `_fail`, which only CPython 3.11 reaches (run by hand there: `step_identity("example_step", 10**5000)` gives the `JournalError`; the 3.11 gate runs the test case). All fifteen public names are tested.
- **CI on the PR**, final head `ab24521`, run https://github.com/myungjoo/HIL-Claw/actions/runs/37588458147 : five successful checks — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)`. No failed CI run on the PR.
- **`push` run on `main`** for `39dfb30`: https://github.com/myungjoo/HIL-Claw/actions/runs/37588912738 — `completed` / `success`.
