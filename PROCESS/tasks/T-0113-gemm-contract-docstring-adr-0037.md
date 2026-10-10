---
id: T-0113
title: Correct the docstrings of `hilclaw/gemm_contract.py` after ADR-0037 - the refusal of a dimension of 0 is no longer "this module's choice, not a rule of a record" - settle in the docstring which exception class that refusal has, and pin the four walk-through shapes of ADR-0037 in the tests; no change of behaviour
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-5, FR-13, OD-6, OD-4]
dependsOn: [T-0110, T-0112]
touchesFiles: [hilclaw/gemm_contract.py, tests/test_gemm_contract.py]
estimatedSize: {loc: 30, files: 1}   # non-test: docstring lines of one module, no statement changes; the test file is excluded from the cap (D4)
hq: []   # carries a closed record (ADR-0037) into a docstring; closes no OD, writes no ADR, no dependency, no schema or data-plane file. Independent of HQ-0005, HQ-0006 and HQ-0007
---
## Why
ADR-0037 (T-0112, landed on `main` as `36b43df`, 2026-10-10) settled the one point T-0110 had left open: **the contract of ADR-0008 (`gemm`, `fp32`, `row_major`, `c`) covers no shape that holds a 0; for such a shape ADR-0008 defines no `task.contract` and no call, and nothing is substituted.** Its Consequences name two things about the code and do neither:

- "**One docstring sentence is now untrue**: 'The lower bound of 1 is this module's choice, not a rule of a record' (`op_signature_record`). Correcting it is a follow-up in code mode and is not done here. The rest of that sentence - that ADR-0001 lets a shape value be 0 and that a shape with a 0 describes a call the contract never has - stays true."
- "**The exception class is not chosen here.** The module raises `keys.InvalidRecordError`, which `hilclaw/keys.py` documents as 'A record or a value breaks a rule of ADR-0001'; a dimension of 0 breaks no rule of ADR-0001, with or without this record. Whether the module keeps that class or gets one of its own is left to the same follow-up."

**This task is that follow-up.** A reader of the module is told today that no record states the bound, which is false since `36b43df`. It ticks **no PLAN checkbox** (P1-5 stays open: `task.objective` waits on #5 A-4).

Planner's judgements (2026-10-10T01:3xZ, from the files at `main` `353a2c8`; **the reviewer is asked to re-check each**):
- **No decision of a record is taken.** The rule is ADR-0037's; the task only makes the docstring say so. ADR-0037 says the behaviour of the module agrees with the rule "and no change of behaviour follows".
- **The exception class - the weakest point, weigh it first.** It is a choice about the interface of one module that has no caller, left by ADR-0037 to this task; the planner reads it as a provisional code choice, not as an open decision of a record and not as an owner-only item (DRIVER §9 list: #5 A/B items, C-6, OD-25, OD-3). **The planner's reading: keep `keys.InvalidRecordError` and no new class.** Reasons: the task is "no change of behaviour"; the module has no caller that could tell the classes apart; one `_shape` check refuses a 0 together with the values `keys` itself would refuse (a negative value, a `bool`, `MAX_INTEGER + 1`), and a caller meets one class for all of them (the reason T-0110 recorded); a class of its own is cheapest to add when the first caller needs to tell the cases apart. What changes is that the docstring says plainly that the class is reused for a refusal that is **not** a broken rule of ADR-0001 but the rule of ADR-0037. **The docstring of `InvalidRecordError` in `hilclaw/keys.py` is not edited** (it is true of `keys`; the difference is stated where it arises). **If the executor or a reviewer reads a class of its own as required, do not argue it out and do not add one here: keep the class, record the reading in `## Result` and name the class as a follow-up for the task that binds the values.** If a reviewer reads the choice as needing a record or the repository owner, return BLOCKED ("requirement unclear") with the exact question.
- **Second weak point - whether a docstring-only slice is worth a PR.** The planner's reading: yes, because a public docstring states something a landed record contradicts, ADR-0037 names the correction as a follow-up, and the walk-through of that record is not yet pinned by any test (only m = 0 is, by `test_zero_is_accepted_by_keys_and_refused_here`, and only for `op_signature_record`).
- **Why this item now**: no lock, no TODO / INTERRUPTED / IN_PROGRESS task file and no open PR at planning time. T-0088, T-0106 and T-0107 are BLOCKED on HQ-0005, HQ-0006 and HQ-0007, unanswered on #5. This item is the first follow-up of T-0112 `## Result` and of the journal of 2026-10-10. Candidates weighed and not taken now: the test of `hilclaw/standin_profile.py` for a macOS product version of three or more words (T-0111 `## Result`; the candidate after this one); the shared once-only write helper (not before 2026-10-16); the rest of P1-1 (HQ-0005), of P0.5-4 (HQ-0007), `task.objective` (#5 A-4), the rest of P1-8 (OD-3 and others, re-checked by the planners of T-0105 to T-0112).
- **A-13 reading** (ask the reviewer explicitly): code mode (a file of `hilclaw/` changes); no new dependency, no schema file, no data-plane file, no statement of the module changes. No BLOCKED reason applies.

Known risk, accepted: ADR-0037 is inside its objection window until 2026-10-17, ADR-0008 until 2026-10-14, ADR-0001 until 2026-10-13. If ADR-0037 is reverted, the docstring edit is reverted with it.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) - mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED, never worked around), §2 last bullet (never touch `PROCESS/STATE.json`), §3 "BLOCKED 사유" paragraph, §9
- **ARCHITECTURE/decisions/ADR-0037-od6-gemm-contract-zero-dimension.md - the whole record (113 lines)**: Status, Context, **decision 1 (scope), decision 2 (the rule, what it is a statement about, the table of four cases), decision 3 (how ADR-0008 is read; "chosen, not found")**, the walk-through table (four shapes and their names), **Consequences (the two bullets quoted above)**, Boundaries
- ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md decision 6 (the row "Dimensions") and decision 9 - read only
- ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md decision 1 (an integer is in the range 0 to 2^53 - 1) - read only
- **`hilclaw/gemm_contract.py`** (131 lines, whole): the module docstring (lines 1-35), the docstring of `op_signature_record` (lines 57-76; the sentence to correct is at lines 68-71), the docstring of `task_contract` (lines 103-105), `_shape` (lines 119-127)
- **`tests/test_gemm_contract.py`** (372 lines, whole): the literals copied from ADR-0008 at the top, `BAD_DIMENSIONS`, `test_bad_dimension_is_refused` (line 287), `test_zero_is_accepted_by_keys_and_refused_here` (line 328)
- `hilclaw/keys.py` lines 57-58 (`InvalidRecordError` and its docstring) and `op_signature_key` - read only
- PROCESS/tasks/T-0112-adr-od6-gemm-contract-zero-dimension.md `## Result` ("The rule as landed", "Whether the code agrees", "Follow-ups left") and PROCESS/tasks/T-0110-gemm-contract-op-side-values.md `## Result` ("Public API as landed", "Provisional choices", "For a later record", "Verification") - how the point arose and how the sibling slice landed
- CLAUDE.md - 상시 규칙: "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" 1 to 5, "코멘트 최소화", "미결은 발명하지 않는다"
- .claude/skills/dev-item-address/SKILL.md (procedure); .claude/skills/dev-code-review/SKILL.md (what the reviewer checks)
- `.github/workflows/ci.yml` - read only (six checks at planning time)
- Issue #5: every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6091831907 (the ADR-0037 notice; `gh issue view 5 --repo myungjoo/HIL-Claw --json comments`). **If the repository owner has objected to ADR-0037, ADR-0008 or ADR-0001, do not start: return BLOCKED ("requirement unclear") quoting the comment.** An owner answer to HQ-0005, HQ-0006 or HQ-0007 does not stop this task

Line numbers are those of `main` at `353a2c8`; if they moved, find the sentence by its words.

## Acceptance Criteria
ADR-0037 fixes the rule. The wording of the docstrings is the executor's; where a criterion below and the record disagree, **the record wins**: follow it and say so in `## Result`.

### Files
- `hilclaw/gemm_contract.py` (docstrings only) and `tests/test_gemm_contract.py`. **Nothing else**: `hilclaw/keys.py`, `hilclaw/spec.py`, `hilclaw/instance.py`, the harness, every other test, every ADR, the OD register, `pyproject.toml`, `.github/` stay as they are.
- Language: Python (the module exists in Python; no choice arises). One line in the commit body and `## Result`.

### The module - docstrings only
- **No statement changes**: `_shape`, the bound of 1, the exception class, the message text `shape.<name>: must be an integer from 1 to 2**53 - 1, got <value>`, the constants and the two return values are byte for byte what they are. Check: `git diff origin/main -- hilclaw/gemm_contract.py` touches only lines inside docstrings; the statement count reported by coverage for the module stays 22.
- **`op_signature_record`**: the sentence "The lower bound of 1 is this module's choice, not a rule of a record" is replaced by one that names the source: ADR-0037 (decision 2) - the contract of ADR-0008 covers no shape that holds a 0, so there is no op_signature record "of the shape under this contract" to return. Keep what ADR-0037 says stays true: that ADR-0001 lets a shape value be 0, and that ADR-0008 decision 6 has the caller pass dimensions of at least 1. Add, in one or two sentences: that such a record is still a valid record with a key for `hilclaw.keys.op_signature_key` (ADR-0001, unchanged - the refusal says the contract does not cover the shape, **not** that the record is invalid); and that `keys.InvalidRecordError` is raised for it although a 0 breaks no rule of ADR-0001 - the class is reused, the refused rule is ADR-0037's.
- **`task_contract`**: one sentence that for a shape that holds a 0 the contract has no `task.contract` and nothing is substituted (ADR-0037 decision 2, the fourth case), raised in the same way.
- **Module docstring**: name ADR-0037 next to ADR-0008 where the module says by which record it returns its values (one clause or one short sentence; the first line may stay as it is if the reference is added in the body).
- **Say no more than the record.** Do not write that a spec, a record or an `instance.json` with a 0 is invalid; that a tool or a writer of specs refuses it; what a kernel does when called with a 0; that the repository owner decided or confirmed anything; any reason for "at least 1" attributed to ADR-0008 (it gives none). The rule is a statement about the contract only. Before the first review, check every sentence you wrote against ADR-0037 decision 2 and Consequences word by word (most review rounds of T-0110 to T-0112 went to single sentences that said more than their source).
- CLAUDE.md "코멘트 최소화": no new comment; docstrings of the public API may be as long as needed, but keep the addition short (about 10-20 lines in all).

### Tests (`tests/test_gemm_contract.py`, excluded from the size cap)
The existing 125 cases stay and pass unchanged; none is deleted. Add (helpers, if any, live in the test file and get no tests of their own - test rule 5):
- **The walk-through of ADR-0037, written into the test as literals copied from the record** (a comment line naming the record, in the manner of the ADR-0008 literals at the top of the file): (1, 2048, 8192) `gemm-485b9bc494d477eb`; (0, 2048, 8192) `gemm-d765fb955295628a`; (1, 0, 8192) `gemm-ae3e9e269ea6e812`; (0, 0, 0) `gemm-f5ed2636b2d123a9`. Compute each with `hilclaw.keys.op_signature_key` before writing it; if a computed name differs from the record, do not change the literal to fit: return BLOCKED quoting both.
- happy: for the first shape, `op_signature_key(op_signature_record(1, 2048, 8192)).name` is the first name and `task_contract(1, 2048, 8192)` returns a contract.
- negative (the rule, both halves, for each of the three shapes that hold a 0 and **for both functions**): a record with that shape, built in the test from the module's constants, is accepted by `op_signature_key` and has exactly the name of the record; `op_signature_record` and `task_contract` each raise `keys.InvalidRecordError` (assert `type(...) is InvalidRecordError`) and return nothing; the message starts with `shape.` and names the first dimension that is 0 in the order m, k, n.
- branch: a 0 in each single position (m only, k only, n only, the others at least 1) is refused by both functions - if `BAD_DIMENSIONS` already holds 0 this is covered by `test_bad_dimension_is_refused`; say so in `## Result` rather than duplicating it.
- No test asserts the wording of a docstring.

Test rules of CLAUDE.md / DRIVER §5 (D12): 1 the package total of `hilclaw/` stays at or above 80 % lines and functions (record the two figures of the final head from the CI log); 2 happy, error, branch and negative cases as above; 3 both public functions of the touched module have tests (they do; the new cases call both); 4 the module has its test file; 5 no tests for test code, CI workflows or helper scripts.

### Verification (record summary lines and run URLs in `## Result`)
- Local, before the commit and before the merge, from the repository root: `python -m pytest` exits 0 (measure the pass and skip counts on `origin/main` first; record before and after), `python -m ruff check .` and `python -m ruff format --check .` exit 0. Install nothing.
- `git diff origin/main --stat` lists only the two files of `touchesFiles`; `git ls-files --eol` shows `i/lf` for both; `git diff --check` is clean. Record the line count of the non-test diff (cap 300 LOC / 5 files).
- CI on the PR: `gh pr checks <PR> --watch` ends with **every check of the final head successful** - six at planning time: `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)`, `Coverage gate (hilclaw)`. Record the run URL and the two coverage lines. Merge only then.
- After the squash-merge, check the `push` run on `main` (`gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"`) and record its conclusion; if it is not `success`, do not fix forward on `main`: record it and say so in the returned summary.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0113'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0113 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (none at planning time; a PR touching a file of `touchesFiles` is BLOCKED "open PR conflict").
- Code mode: branch `claude/T-0113-gemm-contract-docstring-adr-0037` from `origin/main`; Draft PR with the `DONOTMERGE` label; PR title contains `T-0113`; executor commits end with the trailer `Task: T-0113`.
- After a failed CI run, read the whole failed log (`gh run view <id> --log-failed`) and fix every diagnostic before pushing again. Three consecutive failed CI runs on the PR: stop and return BLOCKED ("CI 3 consecutive failures") with the last log excerpt in `## Result`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds; past the cap without a final Approve is BLOCKED; a result starting with `SECURITY` is BLOCKED; if no reviewer can be spawned, BLOCKED - no self-review). Ask the reviewer explicitly to (a) **re-check the planner's judgements in `## Why`**: the exception class kept (the weakest point), that the slice is worth a PR, that it is selectable without the repository owner, and the A-13 reading; (b) compare every new docstring sentence with ADR-0037 decision 2, decision 3 and Consequences word by word and confirm that none says more than the record - nothing about the validity of a record, a spec or a file, nothing about a tool or a kernel, nothing attributed to the repository owner or to ADR-0008 that they do not state; (c) confirm that no statement of the module changed; (d) compare the four names in the test with the walk-through table of the record character by character.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm that every check of the final head is successful, then `gh pr merge <PR> --squash --body-file <file outside the repository>` with the PR body, whose **last line is `Task: T-0113`**. Delete the remote branch and the local branch in **separate** commands and only after `gh pr view <PR> --json state` reports `MERGED`.
- Commit body: what changed in one paragraph; the exception class as kept, with its one line of reason; the language line.
- `## Result`: fill it in **after** the merge, on `main`, and leave that edit **uncommitted** - the driver commits it (DRIVER §3-6). The branch and the PR must not contain this task file. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. **Do not put a fenced code block into `## Result`** (`ruff format --check .` reads Markdown); use inline code. Record: PR and commit, review rounds and findings, the docstring sentences as landed (quoted inline), the exception class as landed and whether a reviewer asked for a class of its own, the test cases added, the verification outcomes, the line counts, the language line, and that this task ticks **no** PLAN checkbox.
- Size: about 30 non-test lines in one file; the cap is 300 LOC / 5 files (tests excluded).
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- Any change of behaviour of `hilclaw/gemm_contract.py`: the bound, the message, the exception class, a new class, a new function, a new constant.
- `hilclaw/keys.py` (the docstring of `InvalidRecordError` included), `hilclaw/spec.py`, `hilclaw/instance.py`, the harness; any new check in a validator (ADR-0037 Boundaries).
- Whether a tool, the writer of specs or the start of an instance refuses a record whose shape holds a 0 (OD-18, OD-23, OD-26); OD-16 sub-question ①; what a kernel does when called with a 0; an upper bound; any other contract.
- Any edit of an ADR (ADR-0037 and ADR-0008 included), the OD register, OpenDecisionProposals, StandardScenarios, UsageCases, CLAUDE.md, DRIVER.md, PLAN.md, `.claude/`, `README.md`.
- Binding the values of the module to a caller; the committed spec example; `task.objective` (#5 A-4); anything HQ-0005, HQ-0006 or HQ-0007 asks.

## Follow-ups
- (planner, candidate after this - code mode, tiny, no module change) A test of `hilclaw/standin_profile.py` that pins a macOS line left with three or more words after the spelling (`macos 0.0 beta 1`), the one case where ADR-0036 and a literal reading of "two or three words" differ (T-0111 `## Result`). Test rule 5 does not forbid it: it tests a module of `hilclaw/`.
- (planner, when a caller binds the values of `gemm_contract`) Whether the refusal of a 0 gets an exception class of its own; the structure assertion of `tests/test_gemm_contract.py` that no module of `hilclaw/` names `gemm_contract` (T-0110).
- (driver / owner) HQ-0005 (T-0088), HQ-0006 (T-0106), HQ-0007 (T-0107). PLAN P1-5: `task.objective` (#5 A-4); the place and form of a committed example.
- (planner, when a caller exists) Whether `clang_build.compiler_version` is kept, changed to the rule of ADR-0035 or removed (T-0109 `## Result`).
- (planner - not before 2026-10-16, code mode, no change of behaviour) One shared once-only write helper for the three writers (`key_records`, `instance_file`, `spec_file`).

## Result
