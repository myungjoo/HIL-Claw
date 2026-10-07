---
id: T-0047
title: Add hilclaw/run_state_file.py, the function that replaces the runtime STATE.json of a run on disk by the five steps of ADR-0013 (on top of layout.run_file and run_state.dump), and add its tests
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [OD-8, FR-13, NFR-1, NFR-2, C-7, "#5 A-3"]
dependsOn: [T-0021, T-0043, T-0045, T-0046]
touchesFiles: [hilclaw/run_state_file.py, tests/test_run_state_file.py]
estimatedSize: {loc: 120, files: 1}   # non-test: one new module; the test file is excluded from the cap (D4)
hq: []   # implements closed decisions (ADR-0013 decisions 2 to 7; ADR-0012 decisions 2, 6); closes no OD, writes no ADR, standard library only, changes no member or rule of any file format
---
## Why
PLAN P1-8 has, for the runtime `runs/<run_id>/STATE.json`: the record of the file (ADR-0012), the pure functions (`hilclaw/run_state.py`, T-0043), the reader over the files of a run (`hilclaw/run_journal.py`, T-0045) and, since T-0046, the record of how the file is replaced on disk (**ADR-0013**). **Nothing in the package writes the file yet.**

ADR-0013 Consequences name this slice: "The code slice of PLAN P1-8 can implement the write: a function over `layout.run_file` and `run_state.dump` that performs the five steps. `dump` is step 1 (it refuses what it cannot write before a file is touched). It needs to report: a failure of the creation, the write, the flush or the move (with its temporary file removed), a final name that cannot be replaced (a directory in its place), and a data root that does not exist (the convention of the package's other writers, which never create it). In which module it lives is that task's choice, and it is a library function: registering it as a tool is OD-23."

This task writes that function and its tests. It ticks **no PLAN checkbox** (P1-8 stays open: the other members of the file, `instance.json` and the result files remain).

Why this item now (planner, DRIVER §6, 2026-10-07 UTC, judged from the files):
- P0.5-3 is BLOCKED on HQ-0003 (T-0014). The verification half of P1-3 (T-0036), P1-4 and the "harness pass" half of P0.5-1 wait for HQ-0004. Both are unanswered. The rest of P0.5-4 is the owner's hook registration. P1-1 has no tool with a fully decided contract; P1-5 slice 3 needs owner values.
- T-0046 `## Follow-ups` and the journal of 2026-10-07 name this slice as the next one. No open PR and no TODO / INTERRUPTED task file at planning time. The latest comment on #5 is the ADR-0013 notice (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6036469993); no objection to ADR-0001..0013.

Planner's choice of the module — **a module of its own**, not `hilclaw/run_journal.py`: that module's docstring promises "It writes, creates and removes nothing", its tests assert it, and a reader that can be imported without the write keeps the read side separable when the isolation means is decided (sub-question ⑭ of OD-8). The name `run_state_file` is a recommendation.

A-13 check (planner's reading — the reviewer is asked to re-check it):
- "데이터 plane 스키마 변경": none. The bytes written are exactly those of `run_state.dump`; no member, type or validity rule changes. The temporary file and its name form are ADR-0013's, not this task's.
- No new external dependency: standard library only; `pyproject.toml` unchanged.
- **No decision of OD-23**: a library function. It is not registered as a tool, has no command line entry, and says nothing of which agent or hook calls it.
- **Nothing of sub-questions ⑩ and ⑫ beyond ADR-0013 decisions 6 and 7**: the function may create the run directory and writes exactly what its caller gives; it does not read the previous file.

Known risk, accepted: ADR-0004, 0006, 0011, 0012 and 0013 are inside their objection windows (until 2026-10-14). An objection creates a reverting task and this module is revisited with it.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED, never worked around), §2 last bullet (the driver's `PROCESS/STATE.json` is a different file — never touch it), §3 "BLOCKED 사유" paragraph, §9
- **ARCHITECTURE/decisions/ADR-0013-od8-state-file-replacement.md — the whole record (139 lines)**: decision 2 (lines 29-47: the five steps and the table of death moments), decision 3 (49-58: place, name form `STATE.json.<token>.tmp` with `<token>` matching `[a-z0-9-]{1,64}`, a new file per write), decision 4 (60-65: a leftover), decision 5 (67-75: what is promised; the flush of the content required, that of the directory entry not; the environments; a symbolic link under the final name is replaced, not followed), decision 6 (77-82: the first file; the run directory may be created), decision 7 (84-88: exactly what the caller gives), Consequences (111-118), Boundaries (120-129)
- ARCHITECTURE/decisions/ADR-0012-od8-runtime-state-file.md — decision 2 ("A missing file"), decision 6, decision 7
- ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md — decisions 1, 2, 4, 7 and 10
- `hilclaw/run_state.py` — the module docstring (lines 1-37), `InvalidStateError`, `dump` (159-187), `parse` (74-104)
- `hilclaw/layout.py` — `RUN_FILES`, `check_run_id`, `run_dir`, `run_file` (lines 34, 58-77), `InvalidPathValueError`
- `hilclaw/run_journal.py` — the whole file (130 lines): the docstring style, the `data_root` check of `read_state` (lines 77-81), `MissingStateError`; used by the tests to read back what was written
- `hilclaw/cas.py` lines 96-120 (`_store`: the existing pattern — `open(..., "xb")`, `flush`, `os.fsync`, `os.replace`, removal in `finally`, a name built from `os.getpid()` and `secrets.token_hex(8)`) and `hilclaw/events.py` lines 171-177 and 277-282 (the `data_root` convention and the creation of `runs/<run_id>/` with `mkdir(parents=True, exist_ok=True)`; `_root` is private — do not import it)
- `tests/test_run_journal.py` lines 1-160 (constants `RUN`, `START`, `AFTER`, `AFTER_VIEW`, helpers `root`, `place`, `store`, `snapshot`, `link`) — the style to follow; helpers are copied into the new test file, not imported from another test file
- PROCESS/tasks/T-0046-adr-od8-state-file-replacement.md `## Result` (decisions, "Death moments", Follow-ups) and PROCESS/tasks/T-0045-run-journal-from-files.md `## Result` ("Provisional conventions")
- CLAUDE.md — 상시 규칙: "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" ①-⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- .claude/skills/dev-item-address/SKILL.md (procedure); .claude/skills/dev-code-review/SKILL.md (what the reviewer checks)
- `.github/workflows/ci.yml` — five checks run on a PR; the job `Test presence (hilclaw)` expects `tests/test_<module>.py` for a new `hilclaw/<module>.py`
- Issue #5: every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6036469993 (`gh issue view 5 --repo myungjoo/HIL-Claw --comments`). If the owner has objected to ADR-0004, ADR-0012 or ADR-0013 in a way that changes a rule used here, do not start: return BLOCKED ("requirement unclear") quoting the comment

## Acceptance Criteria
ADR-0013 fixes what a replacement is. The module name, the function name, its return value, the error types and the handling of the cases the record does not mention are **conventions chosen by this task, provisional**: state each with one line of reason in the commit body, the PR body and `## Result`. Where a criterion below and a record disagree, **the record wins**: follow it and say so in `## Result`.

### Files
- `hilclaw/run_state_file.py` (new; recommended name — another name is fine if the reason is given, and the test file is then named to match; about 120 lines with docstrings, in any case within the cap of 300).
- `tests/test_run_state_file.py` (new; the name must match the module for the `Test presence (hilclaw)` job).
- Python, because `run_state.dump` and `layout.run_file` are Python — one line in the commit body and `## Result`.
- Nothing else. `hilclaw/run_state.py`, `hilclaw/run_journal.py`, `hilclaw/layout.py`, `hilclaw/events.py`, `hilclaw/cas.py`, `hilclaw/artifacts.py`, `hilclaw/tools.py`, `hilclaw/__main__.py`, `hilclaw/mcp_front.py`, `pyproject.toml`, `.github/` and every existing test stay as they are.

### The capability (recommended signature)
`replace(data_root, run_id, round, view, others=None)` puts the content `run_state.dump(round, view, others)` under `layout.run_file(data_root, run_id, "STATE.json")` by the five steps of ADR-0013 decision 2:
1. **The content first**: `run_id` is checked and `run_state.dump` is called before the file system is touched; `layout.InvalidPathValueError` and `run_state.InvalidStateError` pass through and nothing is created — no directory either.
2. **A new file beside the final one**: a temporary file in `runs/<run_id>/` named `STATE.json.<token>.tmp`, `<token>` matching `[a-z0-9-]{1,64}` and different per call (how it is built is this task's; `cas.py` uses the process id and a random part), **created as a new file** (exclusive creation, never by opening an existing one), holding the whole content.
3. **Stable storage**: the content is flushed and `os.fsync` is called on the temporary file, which is then closed, before the move.
4. **The move**: `os.replace(temporary, final)` — the only step that changes what the final name holds. The final name is never opened for writing; no backup copy and no marker is written.
5. **A failure while the writer lives**: the function removes its own temporary file and raises; the final name is as it was (the previous bytes, or absent).

Fixed by the record and to hold in the code:
- `runs/` and `runs/<run_id>/` are created when missing (decision 6); no other file is required to be there; **`data_root` is never created** (Consequences).
- The first file is written by the same steps; afterwards `run_journal.read_state` returns the values given.
- Exactly what the caller gives is written: the previous file is **not read** and no member is carried over (decision 7).
- A leftover (a file of the name form that another replacement left) is never read and never moved over the final name (decision 4).
- The directory entry is not required to be flushed (decision 5).

### Constraints
- **Standard library only.** The module imports `hilclaw.layout` and `hilclaw.run_state` and uses their public names only (no private helper of another module; a few lines of its own for the `data_root` check are fine).
- **Not a tool**: nothing is registered in `hilclaw/tools.py`, no command line entry, no use of `hilclaw.config` or of the real data repository `HIL-Claw-data`.
- **No decision of a boundary** (ADR-0013 Boundaries): who calls the function (OD-23); a lock or a second writer (rest of OD-17); a commit; the restore of the file from the history; any member besides the three of ADR-0012; whether a caller keeps a member it does not know (sub-question ⑫); what a run directory without `STATE.json` means (sub-question ⑩); how `artifacts.json` or any other file is written (sub-question ⑮).
- Module docstring in the style of `hilclaw/run_journal.py`: what it implements, its conventions that the records do not fix, the limits (ADR-0013 decision 5: process death only; the environments; two writers), and what it does not do. Docstrings exact and short; no multi-line comments (CLAUDE.md "코멘트 최소화").
- Runs on CPython 3.11 and 3.14. The local clone is native Windows, which is outside C-7 and for which ADR-0013 states no behaviour: the function must still work there for the cases tested, and no test asserts a platform-specific `OSError` subclass or replaces a file that a reader holds open.

### Cases the record leaves to this task — choose, implement, test and list each with one line of reason
- **`data_root`**: recommended as `hilclaw.events` and `hilclaw.cas` have it — an existing directory, `FileNotFoundError` or `NotADirectoryError` otherwise; `str` and `Path` accepted; not resolved.
- **The order of the checks**: recommended `run_id`, then the values (`dump`), then `data_root`, then the file system. Say what you chose and assert it.
- **The error for a failed step** (creation, write, flush, move): recommended that the `OSError` passes through unchanged, as in the package's other writers; a dedicated error type is acceptable with a reason.
- **A directory in the place of `STATE.json`**: an error and nothing left behind (no temporary file; the directory and its content unchanged). Whether it is found by a check before the temporary file is created or by the failed move is yours. **A symbolic link under the final name is replaced, not followed** (decision 5): do not refuse it, and its target is not changed.
- **A file in the place of `runs/` or of the run directory**: the `OSError` of the directory creation passes through; nothing is changed.
- **Leftovers of other writes**: recommended that the function does **not** remove them (decision 4: allowed, not required; a removal needs a listing and can remove the temporary file of a live writer — decision 5). If you choose to remove them, say why and test it.
- **The return value**: recommended `None`, or the `Path` of the file; say which and why.
- **The mode of the new file**: decision 5 says no rule rests on it. Recommended: what a normally created file gets (the process umask), not a private mode; one line of reason.
- **A `BaseException`** (for example `KeyboardInterrupt`) inside the steps: whether the temporary file is removed then as well (`cas.py` removes in `finally`).
- Anything else you meet. If you read one as a rule about what may exist in the data plane that no record states, return BLOCKED with the exact question.

### Tests (excluded from the size cap; `tests/test_run_state_file.py`)
Helpers live in the test file and get no tests of their own (test rule ⑤). Synthetic values only (`example_step`, `example_axis`); everything under `tmp_path`.
- happy: the first file of a run (no `runs/` at all; `runs/` without the run directory; the run directory with another file) — afterwards the run directory holds `STATE.json` with exactly the bytes of `run_state.dump` and no file of the temporary name form, and `run_journal.read_state` gives the values; a replacement of an existing file (the Example of ADR-0012 after the start state); `others` written and read back; a second run untouched; `data_root` as `str`.
- the steps, observed through `monkeypatch` on `os.fsync` and `os.replace` (wrap the real function): at the moment of the flush and of the move, the final name still holds the previous bytes (or is absent for a first file); the source of the move lies in the run directory, matches `STATE\.json\.[a-z0-9-]{1,64}\.tmp`, is no member of `layout.RUN_FILES` and holds the whole new content; the flush precedes the move; two calls use two different temporary names; the final name is never opened for writing (for example: an existing final file made unwritable is still replaced, where the platform allows the assertion — otherwise say how it was checked).
- branch: nothing besides `STATE.json` (and the directories above it) is created — compare a listing of `tmp_path` before and after; the previous file is not read (a previous content that is invalid, of another version, or holds further members is replaced and none of its members appears in the new file); a leftover of the name form, partial and whole, is present before the call — it is neither read nor moved, `run_journal.read_state` answers from the final name (or `MissingStateError` when there is none), and whether it is still there afterwards is asserted as you chose; a symbolic link under the final name is replaced and its target unchanged (skip where the platform cannot create one, as `tests/test_run_journal.py` does); the mode case on POSIX only if you assert one.
- error / negative (assert the error type, that the final name holds the previous bytes or is absent, and that no file of the temporary name form remains): an `OSError` raised by the creation, by the write, by `os.fsync` and by `os.replace` (through `monkeypatch`), each for a first file and for an existing one; a directory in the place of `STATE.json`; a file in the place of `runs/` and of the run directory; a missing `data_root` (not created) and a file in its place; an invalid `run_id`; every kind of value `run_state.dump` refuses (a `round` that is no integer of ADR-0001, a view `to_stored` refuses, `others` holding one of the three names or a value outside strict JSON) — with nothing created, the run directory included; the order of the checks as chosen.
- Test rules of CLAUDE.md / DRIVER §5 (D12): ① `hilclaw/` keeps line and function coverage ≥ 80 % — coverage is not measured by CI yet (P0.5-3 BLOCKED on HQ-0003), so check that the tests reach every line of the new module, for example with `python -m trace --count --missing --coverdir <directory outside the repository> --module pytest tests/test_run_state_file.py`, and say how in `## Result`; ② happy, error, branch and negative cases as above; ③ every public function and every public error type of the new module is tested; ④ the new module has its test file; ⑤ no tests for test code, CI workflows or helper scripts.

### Verification (record summary lines and run URLs in `## Result`)
- Local, before the commit and before the merge, from the repository root: `python -m pytest` exits 0 (record pass and skip counts; before this task: 4678 passed, 143 skipped on CPython 3.14 on Windows), `python -m ruff check .` and `python -m ruff format --check .` exit 0.
- `git ls-files --eol` shows `i/lf` for both files; `git status --short` after the tests shows no stray file (no `*.tmp` in the repository); `git diff origin/main --stat` lists only the two files of `touchesFiles`.
- CI on the PR: `gh pr checks <PR> --watch` ends with **five** successful checks on the final head — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)`. Merge only then. The Linux jobs are where the POSIX behaviour (the symbolic-link case, a directory under the final name) is exercised.
- After the squash-merge, check the `push` run on `main` (`gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"`) and record its conclusion; if it is not `success`, do not fix forward on `main`: record it and say so in the returned summary.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0047'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0047 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (none at planning time; a PR touching the two files of `touchesFiles`, or changing `run_state.dump`, `layout.run_file` or `hilclaw/run_journal.py`, is BLOCKED "open PR conflict").
- Code mode: branch `claude/T-0047-run-state-file-replace` from `origin/main`; Draft PR with the `DONOTMERGE` label; PR title contains `T-0047`; executor commits end with the trailer `Task: T-0047`.
- Install nothing. After a failed CI run, read the whole failed log (`gh run view <id> --log-failed`) and fix every diagnostic before pushing again. Three consecutive failed CI runs on the PR: stop and return BLOCKED ("CI 3 consecutive failures") with the last log excerpt in `## Result`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds; if the cap is passed without a final Approve, return BLOCKED). Ask the reviewer explicitly to (a) compare the code with ADR-0013 decisions 2 to 7 sentence by sentence — the content before any file, a new file in the same directory, the name form, the flush before the move, the final name never opened for writing, the temporary file removed on a failure, a leftover never read or moved, the run directory created and the data root not, nothing read from the previous file; (b) re-check the planner's readings in `## Why` — A-13 "data-plane schema change" does not apply, a library function that is not registered decides nothing of OD-23, and a module of its own is tenable; (c) re-check each convention under "Cases the record leaves to this task"; (d) report anything the code decides that ADR-0013 lists under Boundaries (a lock, a commit, a restore, a kept member, another file). If the reviewer reads a point as a design choice needing a record or the owner, return BLOCKED with the question. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm the five checks on the final head, then `gh pr merge <PR> --squash --body-file <file outside the repository>` with the PR body, whose **last line is `Task: T-0047`**. Delete the remote branch and the local branch in **separate** commands and only after `gh pr view <PR> --json state` reports `MERGED`.
- Commit body: the provisional choices (module and function names, the return value, the token, each error, each case left to the task) with one line of reason each, and the language line.
- `## Result`: fill it in **after** the merge, on `main`, and leave that edit **uncommitted** — the driver commits it (DRIVER §3-6). The branch and the PR must not contain this task file. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. Record: PR and commit, review rounds and findings, the public API as landed, the provisional choices, the verification outcomes, the line count of the module, the language line, and that this task ticks **no** PLAN checkbox.
- Size: about 120 non-test lines in 1 file; the cap is 300 LOC / 5 files (tests excluded).
- If ADR-0013 turns out to be ambiguous or self-contradictory on a point the code must decide and that is not one of the conventions above, do not guess and do not edit the ADR: return BLOCKED ("requirement unclear") with the exact question.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- Any edit of `hilclaw/run_state.py`, `hilclaw/run_journal.py`, `hilclaw/layout.py` or another module or test; writing `artifacts.json`, the key record files or `events.ndjson` by this technique (sub-question ⑮).
- A tool, a command line entry or any registration in `hilclaw/tools.py`; any use of `hilclaw.config` or of the real data repository; any change to `HIL-Claw-data`.
- A lock, fencing or a second writer (rest of OD-17); a commit or the rule that a temporary file is never committed (it binds the committing step, undecided); the restore of the file from the history; a read-modify-write helper that carries members over (sub-question ⑫); the first-file policy beyond "may be created" (sub-question ⑩); flushing the directory entry as a promise.
- Any member of `STATE.json` besides the three of ADR-0012; `instance.json`; the result files; `run_id`.
- Any edit of an ADR, the OD register, OpenDecisionProposals, StandardScenarios, CLAUDE.md, DRIVER.md, PLAN.md, `pyproject.toml`, `.github/`, `.claude/`, `README.md`.
- Answering HQ-0003 or HQ-0004 on the owner's behalf.

## Follow-ups
- (planner, P1-1) The first journaled tool on top of `hilclaw/run_journal.py` and this module, once a tool has a fully decided contract (T-0045 `## Result`: `step_state` needs sub-question ① of OD-17 for a step about an earlier round).
- (planner, P1-8) The rest of the item: the further members of `STATE.json`, `instance.json` and the result files hang on OD-3 (owner-only), OD-20, OD-23, OD-29 and owner items — to judge which part, if any, is a design-level ADR slice.
- (unchanged) The integrator items after 2026-10-14 (T-0040, T-0042 and T-0046 Follow-ups); sub-questions ⑭ and ⑮ of OD-8; the T-0043 follow-up on a number beyond the float range in an undefined member.

## Result
