---
id: T-0050
title: Make every write of artifacts.json in hilclaw/artifacts.py a replacement by the steps of ADR-0014 decision 2 (a new temporary file beside the final one, flush, one rename, removal on a failure), and update its docstring and tests
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [OD-8, FR-13, NFR-1, C-3, C-7, "#5 A-2", "#5 A-3"]
dependsOn: [T-0025, T-0047, T-0049]
touchesFiles: [hilclaw/artifacts.py, tests/test_artifacts.py]
estimatedSize: {loc: 60, files: 1}   # non-test: one existing module (the private writer and a few docstring sentences); the test file is excluded from the cap (D4)
hq: []   # implements a closed decision (ADR-0014 decisions 2, 4, 5 and 6 for artifacts.json); closes no OD, writes no ADR, standard library only, changes no member or validity rule of the file
---
## Why
ADR-0014 (landed as `78d6cdb`, T-0049) closed sub-question ⑮ of OD-8: "A write of `artifacts.json` — the first one included — is a replacement by the five steps of ADR-0013 decision 2 ... The final name is never opened for writing." Its Consequences name the code slice: "`_write` of `hilclaw/artifacts.py` as a replacement and `_store` of `hilclaw/key_records.py` by the steps of decision 3. ... `hilclaw/artifacts.py` is at 298 of 300 lines, so how the slice is cut is the planner's."

Today `hilclaw/artifacts.py` `_write` (lines 284-298) opens the final name with `"wb"`. A process killed inside that write leaves an empty or partial `artifacts.json`; every later `load`, `add_record` and `set_retention_class` of the run then raises `CorruptArtifactsError`, and the records added since the last commit are lost with the file although their blobs are stored. **This task changes that one private function** and the docstring sentences and tests that describe the old behaviour. It ticks **no PLAN checkbox** (P1-6 is ticked and stays so; P1-8 stays open).

How the slice is cut (planner, DRIVER §5 and §6):
- **One module only.** `hilclaw/key_records.py` `_store` is a different last step (a step that cannot replace: `os.link` then removal, no replacing fallback, the "name found taken" case of ADR-0001 decision 3) with its own death moments and its own test file of 780 lines. Both in one PR would make the review broad. It is the candidate for the task after this one (Follow-ups).
- **No shared helper in this task.** ADR-0014 leaves "whether the three writers share a helper" to the code task. A new shared module would touch `hilclaw/run_state_file.py` (landed and reviewed in T-0047) and add a module with its own test file. The steps are about ten lines; write them inside `hilclaw/artifacts.py`. Whether a helper is worth a module is judged after the key record slice, when all three writers exist (Follow-ups).
- **The module length.** D4 bounds the change of a task (≤ 300 LOC, ≤ 5 files), not the length of a module (precedent: T-0044, `hilclaw/events.py` at 320 lines, agreed by its reviewer). The module may end a few lines above 300. Keep the growth small: replace docstring sentences instead of adding paragraphs. Do **not** split the module in this task.

Why this item now (planner, 2026-10-07 UTC, judged from the files):
- P0.5-3 is BLOCKED on HQ-0003 (T-0014). The verification half of P1-3 (T-0036), P1-4 and the "harness pass" half of P0.5-1 wait for HQ-0004. Both are unanswered on #5. The rest of P0.5-4 is the owner's hook registration. P1-1 has no tool with a fully decided contract; P1-5 slice 3 needs owner values; the rest of P1-8 hangs on OD-3 (owner-only), OD-20, OD-23, OD-29.
- T-0049 `## Follow-ups` and the journal of 2026-10-07 name this slice as the next one. No open PR and no TODO / INTERRUPTED task file at planning time.

A-13 check (planner's reading — the reviewer is asked to re-check it):
- "데이터 plane 스키마 변경(STATE/spec/eval/artifacts)": none. The bytes under the final name are exactly those written today; no member, type, value list or validity rule changes, and `validate` is untouched. The temporary file and its name form are ADR-0014's (decision 4), not this task's.
- No new external dependency: standard library only (`secrets` is added to the imports); `pyproject.toml` unchanged.
- Nothing of OD-23, of the lock (rest of OD-17) or of the isolation means is decided: the public functions, their signatures, results and error types stay as they are.

Known risk, accepted: ADR-0014, ADR-0013, ADR-0005 and ADR-0004 are inside their objection windows (until 2026-10-14). T-0047 was carried out inside such a window in the same way. An objection creates a reverting task and this change is revisited with it.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED, never worked around), §2 last bullet (the driver's `PROCESS/STATE.json` is a different file — never touch it), §3 "BLOCKED 사유" paragraph, §9
- **ARCHITECTURE/decisions/ADR-0014-od8-whole-file-writes.md** — Status (lines 5-10), Context (14-15, 18-19), **decision 1 (27), decision 2 (29-35)**, the table of death moments (46-54, the `artifacts.json` column), **decision 4 (56-63)**, **decision 5 (65-71)**, **decision 6 (73-80)**, Alternatives rows for point 2, Consequences (102-109), Boundaries (111-119). Decision 3 (37-44) is the key record files: read it to know what is **not** in this task
- ARCHITECTURE/decisions/ADR-0013-od8-state-file-replacement.md — decision 2 (the five steps and the table), decision 3 (place and name form), decision 4 (a leftover), decision 5 (the flush of the content required, that of the directory entry not; the environments), decision 6
- ARCHITECTURE/decisions/ADR-0005-od8-artifacts-record.md — decisions 2, 6, 7, 8 and 10
- **`hilclaw/artifacts.py` — the whole file (298 lines)**: the module docstring (lines 1-48; the sentences that change are at 26-32 and 46-47), `add_record` (131-175), `set_retention_class` (178-201), `_read` (269-281), `_write` (284-298)
- **`hilclaw/run_state_file.py` — the whole file (92 lines)**: the landed form of the same steps (`replace`, lines 77-92: `mkdir(parents=True, exist_ok=True)`, the token `f"{os.getpid()}-{secrets.token_hex(8)}"`, `open(temporary, "xb")`, `flush`, `os.fsync`, `os.replace`, the `created` flag so that only the file this call created is removed, removal after `BaseException`). Its docstring conventions (lines 11-30) are the model for the wording
- `hilclaw/layout.py` — `RUN_FILES`, `run_file`
- **`tests/test_artifacts.py`** — the helpers (lines 1-122: `RUN`, `FILE`, `rec`, `text`, `root`, `snapshot`, `put`, `add`, `place`, `stored`) and the section "negative: a failing write" (lines 752-837: `failing`, `TornFile`, `torn_open` and the four tests there), plus `test_a_file_in_the_place_of_a_directory` (738-749), `test_the_file_path_is_a_directory` and `test_a_symbolic_link_in_the_place_of_the_file_is_not_followed` (709-735)
- `tests/test_run_state_file.py` — how the steps are observed (wrappers on `os.fsync` and `os.replace` through `monkeypatch`, the spy on `open`, the leftover cases, the POSIX-only cases with their skips). A style to follow; helpers are copied, not imported from another test file
- PROCESS/tasks/T-0049-adr-od8-whole-file-writes.md `## Result` (decisions 2, 4, 5, 6; "Death moments"; Follow-ups) and PROCESS/tasks/T-0047-run-state-file-replace.md `## Result` ("Provisional conventions", the review Nits, "Verification")
- CLAUDE.md — 상시 규칙: "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" ①-⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- .claude/skills/dev-item-address/SKILL.md (procedure); .claude/skills/dev-code-review/SKILL.md (what the reviewer checks)
- `.github/workflows/ci.yml` — five checks run on a PR
- Issue #5: every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6038200543 (`gh issue view 5 --repo myungjoo/HIL-Claw --comments`). If the owner has objected to ADR-0014, ADR-0013 or ADR-0005 in a way that changes a rule used here, do not start: return BLOCKED ("requirement unclear") quoting the comment

## Acceptance Criteria
ADR-0014 fixes what the write is. How the token is built and the handling of the cases the record does not mention are **conventions of this task, provisional**: state each with one line of reason in the commit body, the PR body and `## Result`. Where a criterion below and a record disagree, **the record wins**: follow it and say so in `## Result`.

### Files
- `hilclaw/artifacts.py` (edited): the private writer `_write`, the import of `secrets`, and the docstring sentences named below. About 60 changed lines.
- `tests/test_artifacts.py` (edited): new tests, and the existing tests whose expectation the record changes.
- Python, because the module is Python — one line in the commit body and `## Result`.
- Nothing else. `hilclaw/key_records.py`, `hilclaw/run_state_file.py`, `hilclaw/cas.py`, `hilclaw/layout.py`, `hilclaw/tools.py`, `pyproject.toml`, `.github/`, every ADR and every other test stay as they are. No new module.

### The write (ADR-0014 decision 2)
Every write of `runs/<run_id>/artifacts.json` — by `add_record` and by `set_retention_class`, the first file included — is:
1. **The content first**: the whole new text is built as bytes before the file system is touched by the write (it is today).
2. **A new file beside the final one**: a temporary file in `runs/<run_id>/` named `artifacts.json.<token>.tmp`, `<token>` matching `[a-z0-9-]{1,64}` and different per write, **created as a new file** (exclusive creation), holding the whole content. Recommended token: the one of `hilclaw/run_state_file.py` (process id, a hyphen, `secrets.token_hex(8)`).
3. **Stable storage**: `flush` and `os.fsync` on the temporary file, which is closed before the move.
4. **The move**: `os.replace(temporary, final)` — the only step that changes what the final name holds. The final name is never opened for writing.
5. **A failure while the writer lives**: the temporary file this call created is removed and the exception raised again; the final name is as it was (the previous bytes, or absent).

To hold in the code:
- `runs/` and `runs/<run_id>/` are created when missing, as today; `data_root` is never created.
- **Unchanged public behaviour**: the signatures, results and error types of `validate`, `load`, `add_record` and `set_retention_class`; the order of the checks; the bytes of the written file (the layout of the Example of ADR-0005); no write for a repeated add of a known hash or for a class that is already the given one; `_read` (a missing file is no record; a file that is not regular or not valid raises `CorruptArtifactsError` and nothing is written — the record "adds no rule for a previous file that is invalid").
- A leftover (a file of the name form that another write left) is never read in the place of the final file and never moved over it (decision 5). `load` opens the final name only and lists nothing.
- The directory entry is not flushed (decision 6).

### Cases the record leaves to this task — choose, implement, test and list each with one line of reason
- **A failed step** (creation of the temporary file, write, flush, move): recommended that the `OSError` passes through unchanged, as today and as in `hilclaw/run_state_file.py`.
- **Which file is removed on a failure**: recommended only the file this call created (the `created` flag of `run_state_file.replace`); a removal that fails is not reported in the place of the failure it follows.
- **A `BaseException`** (`KeyboardInterrupt`) inside the steps: recommended that the temporary file is removed then as well (today's `_write` and `run_state_file.replace` both catch `BaseException`).
- **Directories created before a step failed** stay (today's docstring says so; ADR-0013 decision 6 describes that state).
- **Leftovers of other writes**: recommended that they are **not** removed, listed or read (decision 5: allowed, not required; a removal can remove the temporary file of a live writer — decision 6).
- **The mode of the new file**: what a newly created file gets from the process; no test asserts a mode. Note in `## Result` that a replacement gives the file a new inode and the default mode, where the in-place write kept those of the existing file.
- Anything else you meet. If you read one as a rule about what may exist in the data plane that no record states, return BLOCKED with the exact question.

### Docstring (module docstring of `hilclaw/artifacts.py`; keep it short — replace, do not add paragraphs)
- The bullet at lines 26-32 ("written in place, without a temporary file: no path of `runs/` is a scratch location ... a file that existed stays as the failed write left it, possibly partial; so can a process killed while it writes") is replaced by what holds now: every write is a replacement by ADR-0014 decision 2 through `artifacts.json.<token>.tmp` in the run directory; after a failed write the final name holds what it held and the temporary file of the call is removed; the death of the process leaves the previous records or the new ones (and possibly a leftover, which is never read). Keep "Only what was committed is recovered ..." only as far as it is still true (machine loss, #5 A-3).
- The last sentence ("it gives no locking and no atomicity (OD-17, ADR-0004 decision 10)") is made exact: still no locking; two writers at once are not prevented and the later move wins (ADR-0014 decision 6); no atomicity between the store and the file or with a commit.
- The docstrings of `add_record` and `set_retention_class` change only where a sentence became false. No multi-line comments (CLAUDE.md "코멘트 최소화").

### Tests (`tests/test_artifacts.py`; excluded from the size cap)
Helpers live in the test file and get no tests of their own (test rule ⑤). Synthetic values only; everything under `tmp_path`. Existing tests stay unless the record changes what they assert; **the ones that change** (say which and why in the PR body):
- `test_a_write_that_fails_midway`, case `existing=True`: today it expects `CorruptArtifactsError` from `load` after a torn write. Now `load` returns the previous records, the final file holds its previous bytes and no file of the temporary name form remains. (`torn_open` wraps `open(path, mode)` and keeps working with the mode `"xb"`.)
- `test_a_failing_rewrite_keeps_the_file_in_its_place`: strengthen from "is a file" to "holds exactly the previous bytes", with no temporary file left.
- `test_a_failing_first_write_leaves_no_file` and `test_a_file_that_cannot_be_opened`: also assert that the run directory holds no file of the temporary name form.

New cases:
- happy: the first file of a run and a later write — afterwards the run directory holds `artifacts.json` with the expected bytes and **no** file of the temporary name form; the same for `set_retention_class`.
- the steps, observed through `monkeypatch` wrappers on `artifacts.os.fsync` and `artifacts.os.replace` (wrap the real function), for `add_record` (first file and existing file) and for `set_retention_class`: at the moment of the flush and of the move the final name still holds the previous bytes (or is absent); the source of the move lies in the run directory, matches `artifacts\.json\.[a-z0-9-]{1,64}\.tmp`, is no member of `layout.RUN_FILES` and holds the whole new content; the descriptor given to `os.fsync` is that of the temporary file; the flush precedes the move; two writes use two different temporary names; the final name is never opened for writing (a spy on `open` in the module: the only file opened for writing is the temporary one, mode `xb`).
- branch: nothing besides `artifacts.json` and the directories above it is created (a listing of `tmp_path` before and after, the blob store aside); a repeated add and an unchanged class create no temporary file and call neither `os.fsync` nor `os.replace`; a leftover of the name form, partial and whole, present before the call — `load` answers from the final name (an empty list when there is none), a write succeeds beside it, and whether the leftover is still there afterwards is asserted as you chose.
- error / negative (assert the error object or type, that the final name holds the previous bytes or is absent, that `load` then gives the previous records, and that no file of the temporary name form remains): an `OSError` raised by the creation of the temporary file, by the write (`torn_open`), by `os.fsync` and by `os.replace`, each for a first file and for an existing one, for `add_record`; `os.fsync` and `os.replace` failing for `set_retention_class`; `KeyboardInterrupt` in a step; after each failure a repeated call succeeds (`monkeypatch.undo()`); a previous file that is invalid still raises `CorruptArtifactsError` and creates no temporary file.
- No test asserts a platform-specific `OSError` subclass, a file mode, or replaces a file that a reader holds open (the local clone is native Windows, outside C-7).
- Test rules of CLAUDE.md / DRIVER §5 (D12): ① `hilclaw/` keeps line and function coverage ≥ 80 % — coverage is not measured by CI yet (P0.5-3 BLOCKED on HQ-0003), so check that the tests reach every line of `_write`, for example with `python -m trace --count --missing --coverdir <directory outside the repository> --module pytest tests/test_artifacts.py`, and say how in `## Result`; ② happy, error, branch and negative cases as above; ③ every public function of the touched module (`validate`, `load`, `add_record`, `set_retention_class`) and every public error type keeps its tests; ④ no new module, so no new test file; ⑤ no tests for test code, CI workflows or helper scripts.

### Verification (record summary lines and run URLs in `## Result`)
- Local, before the commit and before the merge, from the repository root: `python -m pytest` exits 0 (record pass and skip counts before and after), `python -m ruff check .` and `python -m ruff format --check .` exit 0.
- `git ls-files --eol` shows `i/lf` for both files; `git status --short` after the tests shows no stray file (no `*.tmp` in the repository); `git diff origin/main --stat` lists only the two files of `touchesFiles`. Record the line count of `hilclaw/artifacts.py` after the change.
- CI on the PR: `gh pr checks <PR> --watch` ends with **five** successful checks on the final head — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)`. Merge only then.
- After the squash-merge, check the `push` run on `main` (`gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"`) and record its conclusion; if it is not `success`, do not fix forward on `main`: record it and say so in the returned summary.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0050'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0050 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (none at planning time; a PR touching either file of `touchesFiles` is BLOCKED "open PR conflict").
- Code mode: branch `claude/T-0050-artifacts-file-replace` from `origin/main`; Draft PR with the `DONOTMERGE` label; PR title contains `T-0050`; executor commits end with the trailer `Task: T-0050`.
- Install nothing. After a failed CI run, read the whole failed log (`gh run view <id> --log-failed`) and fix every diagnostic before pushing again. Three consecutive failed CI runs on the PR: stop and return BLOCKED ("CI 3 consecutive failures") with the last log excerpt in `## Result`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds; if the cap is passed without a final Approve, return BLOCKED). Ask the reviewer explicitly to (a) compare the code with ADR-0014 decisions 2, 4, 5 and 6 sentence by sentence — the content before any file, a new file in the run directory, the name form, the flush before the move, the final name never opened for writing, the temporary file removed on a failure, a leftover never read or moved; (b) confirm that no public behaviour changed besides what a failed or interrupted write leaves, and that the bytes written are the same; (c) re-check the planner's readings in `## Why` — A-13 "data-plane schema change" does not apply, one module only and no shared helper are tenable, a module slightly above 300 lines is within D4; (d) re-check each convention under "Cases the record leaves to this task" and each changed existing test; (e) report anything the code decides that ADR-0014 lists under Boundaries (a lock, a commit, a restore, who writes, another file, a member of the record). If the reviewer reads a point as a design choice needing a record or the owner, return BLOCKED with the question. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm the five checks on the final head, then `gh pr merge <PR> --squash --body-file <file outside the repository>` with the PR body, whose **last line is `Task: T-0050`**. Delete the remote branch and the local branch in **separate** commands and only after `gh pr view <PR> --json state` reports `MERGED`.
- Commit body: what changed in one paragraph, the provisional choices with one line of reason each, the existing tests whose expectation changed, and the language line.
- `## Result`: fill it in **after** the merge, on `main`, and leave that edit **uncommitted** — the driver commits it (DRIVER §3-6). The branch and the PR must not contain this task file. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. Record: PR and commit, review rounds and findings, the provisional choices, the changed tests, the verification outcomes, the line count of the module, the language line, and that this task ticks **no** PLAN checkbox.
- Size: about 60 non-test lines in 1 file; the cap is 300 LOC / 5 files (tests excluded). If the change cannot be made without a new module or without touching another `hilclaw/` file, do not widen the task: finish what fits, or return BLOCKED with the reason, and propose the split in `## Follow-ups` (DRIVER §5).
- If ADR-0014 turns out to be ambiguous or self-contradictory on a point the code must decide and that is not one of the conventions above, do not guess and do not edit the ADR: return BLOCKED ("requirement unclear") with the exact question.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- `hilclaw/key_records.py` and its tests (ADR-0014 decision 3): the task after this one.
- A shared helper or a new module for the replacement; any edit of `hilclaw/run_state_file.py`, `hilclaw/cas.py` (the T-0047 follow-up about `cas._store` removing a temporary name it did not create) or `hilclaw/layout.py`; splitting `hilclaw/artifacts.py`.
- Any member, value list or validity rule of `artifacts.json`; `validate`; a recovery or repair of an invalid file; removal of leftovers as a duty; GC, `gc_at`, retention policy.
- A lock, fencing or a second writer (rest of OD-17); a commit or the rule that a temporary file is never committed (it binds the committing step, undecided); who calls the functions and whether through a tool (OD-23); the isolation means (sub-questions ⑭ and ⑯ of OD-8).
- Any edit of an ADR (the sentences ADR-0014 lists as "now less exact" are the integrator's, after the objection window), the OD register, OpenDecisionProposals, StandardScenarios, CLAUDE.md, DRIVER.md, PLAN.md, `pyproject.toml`, `.github/`, `.claude/`, `README.md`; any change to the `HIL-Claw-data` repository.
- Answering HQ-0003 or HQ-0004 on the owner's behalf.

## Follow-ups
- (planner, next — code mode) `hilclaw/key_records.py` `_store` by ADR-0014 decision 3: a temporary file `<final name>.<token>.tmp` in the key directory, flush, then a last step that cannot replace (`os.link` to the final name and removal of the temporary name, or a rename that does not replace; **no fallback to a replacing rename**), the "name found taken" case handled by ADR-0001 decision 3, the directories a failed write created, the docstring sentences at lines 38-42 and 49-50, and the tests in `tests/test_key_records.py`.
- (planner, after that) Whether the three writers (`run_state_file`, `artifacts`, `key_records`) should share one helper module, judged from the three landed forms.
- (unchanged) The mock backend with fault injection and the first tool on top of `hilclaw/journaled_step.py` once a tool has a fully decided contract (P1-1); the rest of P1-8; the integrator items after 2026-10-14 (T-0040, T-0042, T-0046 and T-0049 Follow-ups); the T-0047 and T-0048 follow-ups.

## Result
