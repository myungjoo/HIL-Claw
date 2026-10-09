---
id: T-0097
title: Carry out the five docstring tidies that the reviews of T-0079, T-0081, T-0087, T-0089, T-0091 and T-0094 deferred - five modules of `hilclaw/`, docstrings only, no statement and no behaviour changes
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, FR-13, NFR-7, OD-8, OD-18]
dependsOn: [T-0079, T-0081, T-0087, T-0089, T-0091, T-0094, T-0096]
touchesFiles: [hilclaw/instance.py, hilclaw/layout.py, hilclaw/journaled_tool.py, hilclaw/hw_tool.py, hilclaw/spec_file.py]
estimatedSize: {loc: 40, files: 5}   # docstring lines only, in five modules of hilclaw/; no test file is expected to change
hq: []   # decides nothing: every sentence written restates a landed record or the landed code. Independent of HQ-0005
---
## Why
Six landed tasks each left a small docstring tidy that their reviewers saw and did not ask for inside that change, because the sentence had not become inexact through it. They were recorded as follow-ups and never done:

| # | Module | What | Recorded in |
|---|---|---|---|
| 1 | `hilclaw/instance.py` | The `source_commit` bullet under "Conventions of this module, which the six records do not fix" states the rule of ADR-0022 decision 3 as if it were a convention of the module - the form the `n_max` bullet had before round 2 of T-0079 | T-0079 `## Result` "Follow-ups left"; T-0081 and T-0091 `## Result` ("still open") |
| 2 | `hilclaw/instance.py` | "what follows for a round of a run whose file states none" lacks the word "valid" of OD-8 sub-question 25 | T-0091 `## Result`, round 3 Info |
| 3 | `hilclaw/layout.py` | The docstring of `check_run_id` says "the form of a `run_id` is open". ADR-0027 has since fixed the form of an id the system builds, and `hilclaw.run_id` is that code | T-0087 `## Result` "Follow-ups added by this task" |
| 4 | `hilclaw/journaled_tool.py`, `hilclaw/hw_tool.py` | The docstring of each `tool_function` says the returned function raises `invalid_request` "with a message that names the member". The refusal of a request that is no object names no member. `checked_function` was corrected in T-0089; the two builders were not | T-0089 `## Result` "Follow-ups left", round 2 Nit |
| 5 | `hilclaw/spec_file.py` | One short line inside a reflowed paragraph at the end of the module docstring | T-0094 `## Result`, round 3 Info |

**This task does the five, in one change, and nothing else.** It ticks **no PLAN checkbox** (P1-1 and P1-8 stay open).

Planner's judgements (2026-10-09 UTC, from the files; the reviewer is asked to re-check each):
- **No PLAN slice can go forward without the owner or without a record that is not ripe.** P0.5-4 waits on the owner's hook registration. The rest of P1-1 waits on HQ-0005 (T-0088, BLOCKED; no owner answer on #5 at planning time - the ADR-0030 notice, issuecomment-6078320056, is the last comment). The example of P1-5 waits on #5 A-4 (`task.objective`). Of P1-8, every open sub-question of OD-8 in `ARCHITECTURE/OpenDecisionProposals.md` (1 to 27, lines 96-111) names as its companion the start of an instance or the first writer (10, 17, 19, 20, 21, 23 (i), 24, 25, 27 (i)), OD-23 (6, 7, 8, 26), OD-11 (5, 8, 12, 27 (ii)), the isolation means (14, 16, 23 (ii), 26 (ii)) or OD-20 / OD-28 / OD-12 (1 to 4). The planner found none that a record could answer today without choosing for one of those; writing such a record now would be inventing a decision. This is a judgement, not a proof: a later planner may find a slice.
- **Selectable without the owner.** A docstring that restates a landed record or the landed code decides nothing. No #5 A / B item, C-6, OD-25 or OD-3 is touched.
- **Objection windows.** Tidy 3 points at ADR-0027 (window until 2026-10-16) and tidy 5 lies in the module of ADR-0029 (until 2026-10-16); tidy 4 lies in sentences next to those of ADR-0030 (until 2026-10-16). If one of those records is reverted, its reverting task reverts or rewrites these sentences with it; the cost is a few docstring lines. Tidies 1 and 2 restate ADR-0022 and ADR-0028 and add nothing to them.
- **Code mode** although only docstrings change: the files are in the layer-2 package, which is not in the document-mode list of CLAUDE.md A-13. So: Draft PR, reviewer cycle, CI green, squash-merge.
- **A-13 reading**: no statement changes, so no data-plane schema change, no new dependency, no new kind.
- **The once-only write helper** for the three writers (T-0094 follow-up) is deliberately not this task: it changes statements of modules whose records are inside their windows until 2026-10-16.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) - mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED, never worked around), §2 last bullet (the driver's `PROCESS/STATE.json` - never touch it), §3 "BLOCKED 사유" paragraph, §9
- CLAUDE.md - 상시 규칙: "코멘트 최소화" (docstrings of the public API may be long; no multi-line comments), "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" 1 to 5, "미결은 발명하지 않는다"
- .claude/skills/dev-item-address/SKILL.md (procedure); .claude/skills/dev-code-review/SKILL.md (what the reviewer checks)
- **Tidy 1 and 2** - `hilclaw/instance.py` lines 1-216 (the module docstring): the list "Conventions of this module" from line 42, **the `source_commit` bullet at lines 83-91**, the `n_max` bullet at lines 92-100 and the `candidates_per_round` bullet at lines 101-110 (the two models), the paragraph on the source commit at lines 140-155, **line 184**; `_source_commit` (line 618) and the function that reports a broken rule, to see what the code does with a value. ARCHITECTURE/decisions/ADR-0022-od8-instance-record-source-commit.md **decision 3 "The member"** (line 38), decision 4, decision 5 (a file without the member). ARCHITECTURE/OpenDecisionProposals.md line 109 (sub-question 25, the word "유효한" / "valid" there). PROCESS/tasks/T-0079-instance-record-n-max-reader.md `## Result` (how round 2 reshaped the `n_max` bullet)
- **Tidy 3** - `hilclaw/layout.py` lines 1-30 and `check_run_id` (lines 60-69); `hilclaw/run_id.py` lines 1-60 (the module docstring, read only: "what a valid `run_id` is stays what `hilclaw.layout.check_run_id` checks"); ARCHITECTURE/decisions/ADR-0027-od8-run-id-form.md **decision 1** (the form binds what builds an id and is no rule of validity), decision 2, and Boundaries; ADR-0004 decision 8; OpenDecisionProposals.md line 108 (sub-question 24: an id the system did not build - open)
- **Tidy 4** - `hilclaw/journaled_tool.py`: the docstring of `tool_function` (line 129; the sentence at lines 149-151), the docstring of `checked_function` (line 177; **the corrected sentence at lines 208-210 is the model**), `_checked` (line 251: the first refusal has no member name). `hilclaw/hw_tool.py`: the docstring of `tool_function` (line 132; the sentence at lines 162-164). `tests/test_journaled_tool.py` lines 780-790 and 1318-1325 and `tests/test_hw_tool.py` near line 572 (the landed tests of a request that is no object, read only)
- **Tidy 5** - `hilclaw/spec_file.py` lines 1-140 (the module docstring to its end); PROCESS/tasks/T-0094-spec-file-write.md `## Result`, the three review rounds
- `.github/workflows/ci.yml` - read only (the six jobs)
- Issue #5: every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6078320056 (`gh issue view 5 --repo myungjoo/HIL-Claw --json comments`). If the owner has objected to ADR-0022, ADR-0027, ADR-0028, ADR-0029 or ADR-0030, leave out the tidy that restates the objected record, do the others, and say so in `## Result`. An owner answer to HQ-0005 does not stop this task

Line numbers are those of `main` at `f0cde74`; if they moved, find the sentence by its words.

## Acceptance Criteria
The words are the executor's. What each tidy must and must not say is fixed below. Where a criterion and a record disagree, **the record wins**: follow it and say so in `## Result`.

### Files
- Exactly these five, docstrings only: `hilclaw/instance.py`, `hilclaw/layout.py`, `hilclaw/journaled_tool.py`, `hilclaw/hw_tool.py`, `hilclaw/spec_file.py`. **No statement of any module changes** - no code, no constant, no message, no import, no `__all__`.
- No other file: no test, no ADR, no register, no other document, `pyproject.toml`, `.github/`.
- Python, because the modules are Python - one line in the commit body and `## Result`.

### Tidy 1 - the `source_commit` bullet of `hilclaw/instance.py`
- The bullet separates what ADR-0022 decision 3 fixes from what the module adds, in the shape the `n_max` and `candidates_per_round` bullets have ("What is a value of ... is ADR-NNNN decision N and not a convention: ... The conventions are that ...").
- **Read decision 3 and sort each clause of today's bullet by what the record says**, not by this table. The planner's expectation, to be checked: the record's are the type and the two lengths and the sixteen characters, and that either length is a value; the module's are that the characters themselves are compared (if the record does not already say so), that the one rule is reported as a whole, how a `str` that breaks it is shown, that the string is handed out unchanged, and the `None` of a content without the member as the module's representation. That a file without the member is valid is ADR-0022 decision 5 and is not presented as a convention.
- No clause of today's bullet is lost and none is added that the code or the record does not hold. The header line of the list ("which the six records do not fix") stays true of every bullet, as it is for the `n_max` bullet.

### Tidy 2 - line 184 of `hilclaw/instance.py`
- "a run whose file states none" becomes "a run whose valid file states none". Nothing else in that sentence changes.
- The parallel sentences for the other members (lines 137, 150, 164-165) are worded differently and are **not** edited unless one of them says something false; report what you found.

### Tidy 3 - `check_run_id` in `hilclaw/layout.py`
- The clause "the form of a `run_id` is open" is replaced by what is true now: this function checks the constraint of ADR-0004 decision 8 and nothing else; the form of an id that the system builds is ADR-0027 and is built by `hilclaw.run_id`; that form is no rule of validity, so this function does not check it (ADR-0027 decision 1).
- It must **not** say that every `run_id` has the form of ADR-0027, that an id of another form is invalid or valid for starting a run (sub-question 24 is open), or anything about uniqueness.
- `hilclaw/layout.py` does not import `hilclaw.run_id` and still does not; the reference is a docstring cross-reference only. Lines 20-22 of the module docstring ("builds no `run_id` and does not know whether one is unique") stay true and stay as they are.

### Tidy 4 - the two `tool_function` docstrings
- In `hilclaw/journaled_tool.py` and in `hilclaw/hw_tool.py`, the sentence about `invalid_request` says what `checked_function` already says: the message names the member, or says that the request is no object.
- Check the rest of that sentence in both builders against `_checked` and against what `check` may raise, and against the `invalid_request` each builder adds of its own, if any; change nothing that is true. Do not touch the sentences T-0096 wrote about the stamp.

### Tidy 5 - `hilclaw/spec_file.py`
- The paragraph with the short line is re-wrapped to the width of the lines around it. **No word of the module docstring changes.** If you cannot find a line that is visibly short against its paragraph, change nothing in this file and say so in `## Result`.

### Tests
No statement changes, so **no test is added, changed or removed**, and the reasons are stated here against the test rules of CLAUDE.md / DRIVER §5 (D12):
- 1 coverage: unchanged by construction; record the two figures of the CI run (99.47 lines / 100.00 functions on the T-0096 head).
- 2 happy / error / branch / negative: each sentence written must be true of the landed code, and the executor names in `## Result` the landed test that shows it:
  - happy: a request that breaks a rule of a member is refused with a message that starts with the member's name, for both builders (tidy 4); a string of the pattern is returned by `check_run_id` (tidy 3); a content with a valid `source_commit` is read (tidy 1).
  - error / negative: a request that is no object (`None`, a list) is refused as `invalid_request` with "the request must be an object", naming no member, for both builders (tidy 4; `tests/test_journaled_tool.py`, `tests/test_hw_tool.py`); a `source_commit` of another length, with an upper-case letter or with a digit of another script is invalid (tidy 1; `tests/test_instance.py`); a `run_id` outside the pattern is refused (tidy 3; `tests/test_layout.py`).
  - branch: a `run_id` that matches the pattern and is not of the form of ADR-0027 passes `check_run_id` (tidy 3); a content without `source_commit` is valid and gives `None` (tidy 1).
  - **If one of these claims has no landed test**, do not write the sentence on trust: add the one missing case to the existing test file of that module (test code is outside the size cap), list it in `## Result`, and add that test file to the PR. Do not add a test that reads a docstring.
- 3 every public function of a module whose statements change has tests: no statement changes.
- 4 no new module. 5 no tests for test code, CI workflows or helper scripts.

### Verification (record the outcomes in `## Result`)
- **The syntax trees are equal without docstrings.** For each of the five files, compare `origin/main` with the branch after removing docstrings from the tree (`ast.parse`, drop the first statement of a module, class or function body when it is a string constant, `ast.dump`). Run this as a one-off from outside the repository (a `python -c` or a file below the system temporary directory); **do not commit the script**. All five equal.
- Local, from the repository root, before the commit and before the merge: `python -m pytest` exits 0 with the same pass and skip counts as on `origin/main` (10026 passed, 284 skipped on Windows at the T-0096 head; measure first), `python -m ruff check .` and `python -m ruff format --check .` exit 0. Install nothing.
- `git diff origin/main --stat` lists only files of `touchesFiles` (plus a test file only under the exception above); `git ls-files --eol` shows `i/lf` for them. Record the line count of the diff (cap 300 LOC / 5 files).
- CI on the PR: `gh pr checks <PR> --watch` ends with **every check of the final head successful** - six at planning time: `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)`, `Coverage gate (hilclaw)`. Record the run URL and the two coverage lines. Merge only then.
- After the squash-merge, check the `push` run on `main` (`gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"`) and record its conclusion; if it is not `success`, do not fix forward on `main`: record it and say so in the returned summary.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0097'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0097 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (none at planning time; a PR touching a file of `touchesFiles` is BLOCKED "open PR conflict").
- Code mode: branch `claude/T-0097-deferred-docstring-tidies` from `origin/main`; Draft PR with the `DONOTMERGE` label; PR title contains `T-0097`; executor commits end with the trailer `Task: T-0097`. The PR body lists the five tidies with the task that recorded each, says that no statement changes, and names the records inside their objection windows (ADR-0027, ADR-0029, ADR-0030 until 2026-10-16).
- **Sweep every sentence you write against its record before the first review** (process notes of T-0066 to T-0096: most review rounds went to single sentences that said more than the record). No sentence says what anybody does after an answer, names a tool, attributes a rule to the owner, or closes a sub-question.
- After a failed CI run, read the whole failed log (`gh run view <id> --log-failed`) and fix every diagnostic before pushing again. Three consecutive failed CI runs on the PR: stop and return BLOCKED ("CI 3 consecutive failures") with the last log excerpt in `## Result`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds; if the cap is passed without a final Approve, return BLOCKED). Ask the reviewer explicitly to (a) confirm that no statement of the five modules changed; (b) read each new sentence against its record and the code and report any that says more than they do - for tidy 1 against ADR-0022 decisions 3 to 5 clause by clause, for tidy 3 against ADR-0027 decision 1 and sub-question 24; (c) confirm that no clause of the old `source_commit` bullet was lost; (d) confirm that tidy 5 changed no word; (e) re-check the planner's judgements in `## Why` (no PLAN slice selectable today, code mode, proceeding inside the windows). If the reviewer reads a point as a design choice needing a record or the owner, drop that tidy from the change and record it as a follow-up; if that is not possible, return BLOCKED with the question. Do not write or edit an ADR inside this task. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED - do not self-review.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm that every check of the final head is successful, then `gh pr merge <PR> --squash --body-file <file outside the repository>` with the PR body, whose **last line is `Task: T-0097`**. Delete the remote branch and the local branch in **separate** commands and only after `gh pr view <PR> --json state` reports `MERGED`.
- Commit body: the five tidies in one line each with the task that recorded them, that no statement changes, and the language line.
- `## Result`: fill it in **after** the merge, on `main`, and leave that edit **uncommitted** - the driver commits it (DRIVER §3-6). The branch and the PR must not contain this task file. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. **Do not put a fenced code block into `## Result`** (`ruff format --check .` reads Markdown); use inline code, and write a percentage as a plain figure. Record: PR and commit, review rounds and findings, for each tidy the old and the new sentence in short and the landed test that shows it (or "left out" with the reason), the verification outcomes, the line counts, the language line, and that this task ticks **no** PLAN checkbox.
- Size: about 40 docstring lines in 5 files; the cap is 300 LOC / 5 files. A sixth non-test file is not needed; if you find the same inexact sentence in another module, record it as a follow-up and do not edit it here.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- Any statement of any module; any message, name, signature or kind; any behaviour.
- The shared once-only write helper for `hilclaw/key_records.py`, `hilclaw/instance_file.py` and `hilclaw/spec_file.py`, and the `created` flag noted in round 3 of T-0094.
- An automatic guard for the rule "no private name of a sibling module" (T-0089 follow-up): a CI or lint change, a planner's question of its own.
- Whether `hilclaw.run_id.new` reports a second of 60 (T-0087 follow-up; it waits for the record of the start of an instance).
- The sentences of earlier ADRs that later records list as superseded or "less exact" (the integrator's); any edit of an ADR, of the OD register, OpenDecisionProposals, StandardScenarios, UsageCases, CLAUDE.md, DRIVER.md, PLAN.md, `.claude/`, `README.md`.
- Any docstring sentence of the five modules that is not one of the five tidies, however it reads; any other module.
- Anything HQ-0005 asks; any open sub-question of OD-8 or OD-18; anything in the `HIL-Claw-data` repository.

## Follow-ups
- (planner, candidate for the task after this one, **not before 2026-10-16** unless the risk is noted - code mode, no change of behaviour) One helper for the once-only write shared by `hilclaw/key_records.py`, `hilclaw/instance_file.py` and `hilclaw/spec_file.py` (about 25 statement lines repeated three times; T-0094 `## Result`).
- (driver / owner) HQ-0005 (T-0088): the rest of PLAN P1-1 waits on it; when the owner answers on #5, T-0088 returns to TODO (DRIVER §3-2).
- (driver / owner) PLAN P1-5: `task.objective` (#5 A-4). PLAN P0.5-4: the hook registration.
- (driver, operational) After this task, no task that waits on nobody is known to the planner until 2026-10-16 or an owner answer. If the next planner confirms that, DRIVER §3-3 applies: nothing selectable, nothing committed, and the owner is advised to pause the routine.
- (planner, with the record that defines the start of an instance) OD-8 sub-questions 10, 17, 19, 20, 21, 23 (i), 24, 25 and 27 (i) share that companion; one record on the start of an instance would have to be judged under DRIVER §9 against OD-23 and the owner-only items (#5 A-4, A-5, OD-3) before it is planned.

## Result
