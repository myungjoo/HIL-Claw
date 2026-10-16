---
id: T-0221
title: Add the check of the rules between a round's verdicts file and its hypothesis record (ADR-0071 decisions 1, 3 and 4) as a pure function over both parsed documents, `hilclaw/verdicts_hypotheses.py`
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-17, FR-9, OD-30]
dependsOn: [T-0185, T-0219]
touchesFiles: [hilclaw/verdicts_hypotheses.py, tests/test_verdicts_hypotheses.py]
estimatedSize: {loc: 170, files: 1}   # excluding tests: one new module of about 140-190 lines, about half docstring; one test file besides
hq: []
---
## Why

PLAN P2-6 ("가설 레코드와 판정 ... evaluate가 가설마다 판정·원인을 기록 ... 2층의 스키마 검증·쓰기 ...") is open. ADR-0071 (landed `5ab4767` by T-0218) fixes the verdicts file of a round, `runs/<run_id>/rounds/<RRRR>/eval/verdicts.json`. T-0219 (`86e5e9f`) landed its validator `hilclaw.verdicts.validate` and T-0220 (`4155d34`) its bytes reader and writer `hilclaw.verdicts_file`. Both check only what **one** document shows. ADR-0071 also states three rules **between** `verdicts.json` and `hypotheses.json` of the same round, which no code checks yet:

- decision 1: "the file has exactly one verdict per hypothesis `id` of that file and none for an `id` it does not hold";
- decision 3: a `comparison`'s `measured` is "a *ref* whose `round` is the file's `round` and whose `candidate` is in the judged hypothesis's `tested_by`";
- decision 4: the value of each verdict follows from its counted comparisons read against the hypothesis's `expected` entries ("as expected", "contrary", "no difference"; then `supported`, `refuted`, `inconclusive`).

ADR-0071 Consequences say: "A check of the rules between this file and `hypotheses.json` (one verdict per `id`, the value against `expected`, `measured` within `tested_by`) can be a function over both parsed documents; whether it is in that slice is that task's choice. Binding it to an agent, a prompt or a hook is not." T-0219 and T-0220 left it out of their slice and named it as the follow-up (T-0220 `## Follow-ups`, first item; journal 2026-10-16T03:53:13Z). This task is that function. With it the 2층 part of ADR-0071 that needs no further decision is complete.

**Why this item now.** No lock, no TODO or INTERRUPTED task, no open PR (checked 2026-10-16 at `42aba64`). The first unchecked PLAN items are not takeable: P0.5-4 waits on the owner's hook registration (PLAN header, D15); P1-1's remaining run-tool contract rests on T-0210, BLOCKED on HQ-0021, and `profiler.collect` is tied to #5 A-4 (owner-only); P1-8 needs a fresh design decision. HQ-0013, HQ-0014, HQ-0016..HQ-0019 are `runtime-acceptance` and block nothing here. This task needs neither the run tools nor HQ-0021's answer. It implements rules of a landed record and changes no data-plane file, member, value or version, so the A-13 "data-plane schema change" reason does not apply. The 7-day objection window of ADR-0071 (notice https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6206950125, ends 2026-10-23) is still open; as with T-0219 and T-0220, code may follow an accepted record inside the window, and an objection reverts both. DRIVER §6 allows an item whose `dependsOn` is met to be taken across the phase boundary. Nothing here needs a real `claude`, a logged-in CLI, hardware or an API key (D16).

## Required Reading

Line numbers are those of `main` at `42aba64`; the text wins. Read long ARCHITECTURE lines with `fold` or `cut`, not whole files at once. Read Python and Korean files with `PYTHONIOENCODING=utf-8` (and `encoding='utf-8'` in Python; the console code page is cp949).

- **PROCESS/DRIVER.md §3-5** (line 72: executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (lines 86-114: task format, naming, trailers, size cap D4, **the test rules ① to ⑤ at line 113**, the language line at 112).
- CLAUDE.md, the whole file; above all "개발 드라이버와 런타임의 구분", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙", "코멘트 최소화", "미결은 발명하지 않는다".
- .claude/skills/dev-item-address/SKILL.md (code mode); .claude/skills/dev-code-review/SKILL.md.
- **ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md**: decision 1 (lines 24-31; **line 30**, the relation to `hypotheses.json`, "A hypothesis without a verdict entry has no verdict"), decision 2 (33-47), **decision 3 (49-65; line 64 the `comparison` entry, `measured` within `tested_by`)**, **decision 4 (67-74: line 69 a counted comparison; line 70 the reading against `expected`; line 71 the three values; line 73 what the file itself makes checkable; line 74 what is open)**, decision 5 (76-79), the Example (85-111), Consequences (132-138, above all line 134), Boundaries (140-152).
- ARCHITECTURE/decisions/ADR-0059-od30-round-hypothesis-record.md decisions 2 to 4 (lines 32-83): above all the `expected` and `tested_by` rows (lines 60, 62), line 69, and the Example (88-111).
- **hilclaw/verdicts.py, the whole file (232 lines)**: `validate`, `InvalidVerdictRecordError`, the module docstring (what it leaves to "rules between two files"), and how it defines a counted comparison (`_verdict`, `_evidence`, lines 178-232). **hilclaw/hypotheses.py, the whole file (216 lines)**: `validate`, `InvalidHypothesisRecordError`. Their private names (`_TOP`, `_fail`, ...) are not to be imported.
- tests/test_verdicts.py and tests/test_hypotheses.py: the valid documents (the ADR Examples copied from the records) to build test pairs from.
- hilclaw/verdicts_file.py module docstring (the list of what it does not check), to keep the two docstrings consistent.

## Acceptance Criteria

### `hilclaw/verdicts_hypotheses.py` (new; Python, as the rest of the package)

Public names are the executor's (the module name too, if a better one fits; avoid `check_*`, which the package uses for `correctness.check`). The reasons for any departure from the suggestions go into the commit body.

- **Exception**: `MismatchError(ValueError)` (suggested name), neither an `InvalidVerdictRecordError` nor an `InvalidHypothesisRecordError`: a pair of valid documents breaks a rule between the two files. Message "field path: rule", the field path being in the verdicts document (for instance `verdicts[0].evidence[2].measured.candidate`), with the offending value shown shortened as the validators do (`reprlib`).
- **`check(verdicts, hypotheses)`** (suggested name) returns `None` when the parsed verdicts document `verdicts` and the parsed hypothesis record `hypotheses` of one round keep every rule below; it raises for the first rule found broken. Neither document is modified, nothing is read, written or logged. In this order:
  1. `hilclaw.verdicts.validate(verdicts)` and then `hilclaw.hypotheses.validate(hypotheses)`; their errors pass through unchanged (another `schema_version` included - this function reads version 1 only, OD-11).
  2. **Same run and round**: `MismatchError` when `run_id` or `round` differ between the two documents (ADR-0071 decision 1: the relation is to "`hypotheses.json` of the same round"; a pair of two rounds is not such a pair).
  3. **One verdict per `id`** (ADR-0071 decision 1 line 30): `MismatchError` for a verdict whose `hypothesis` is no `id` of `hypotheses`; then for an `id` of `hypotheses` with no verdict. Uniqueness inside each file is already the validators'. Say in the docstring that a missing entry is never read as `inconclusive` or any other value.
  4. **`measured` within `tested_by`** (ADR-0071 decision 3): for each verdict, `MismatchError` for a `comparison` entry whose `measured.candidate` is not in the `tested_by` of the hypothesis it judges. `against` is not checked against `tested_by` (it is the A of the pair; its base is open, decision 4 line 74). Every `comparison` entry is checked, counted or not (the rule of decision 3 is on the entry, not on counting).
  5. **The value against `expected`** (ADR-0071 decision 4 lines 69-72): for each verdict compute the value from the verdict's own evidence and the hypothesis's `expected` entries and raise `MismatchError` when the recorded `verdict` differs (message names both values). The rule, read exactly from the record:
     - a *counted comparison* is a `comparison` at `board` for whose `measured` and `against` the same verdict holds a `check` at `board` with `outcome` `pass` (the definition `hilclaw.verdicts` already applies for its file-local rule; implement it again here or expose it from `hilclaw.verdicts` only if that needs no other change to that module - see "No change" below);
     - each counted comparison of a metric that has an `expected` entry is *as expected* when `difference` equals that entry's `direction`, *contrary* when it is the other of `lower` / `higher`, *no difference* when it is `not_different`; a counted comparison of a metric with no `expected` entry counts for nothing (in version 1 both files admit only `latency_minimisation`, so this branch is reachable only if a hypothesis lacks it - say so in the docstring rather than adding a case the validators make unreachable, and test it only if reachable);
     - `supported` when every `expected` entry has at least one counted comparison of its metric and every counted comparison of an expected metric is as expected; `refuted` when at least one is contrary and none is as expected; `inconclusive` otherwise.
     Optionally expose the computed value as a public function (for instance `value(verdict_entry, hypothesis_entry)`) if the executor finds it useful to callers; if so it is tested as any public function.
- **What it does not do** (module docstring, short; it may refer to `hilclaw/verdicts.py` and `hilclaw/hypotheses.py` for conventions stated there): it does not check that a *ref* names an attempt that exists, which attempt `against` must be (the base of the comparison, OD-20 / OD-28), a magnitude, drift, `cause` text, or the shared-candidate recommendation of decision 5; it does not decide who calls it or when, whether a write is refused on a mismatch, or what follows a mismatch (ADR-0071 Boundaries; OD-23, OD-16, OD-18, P2-3); it is no tool, no hook and no CLI entry. No comment beyond the docstrings (CLAUDE.md "코멘트 최소화").
- **No change** to `hilclaw/verdicts.py`, `hilclaw/hypotheses.py`, `hilclaw/verdicts_file.py`, `hilclaw/hypotheses_file.py` or `hilclaw/layout.py`, with one allowed exception: making the counted-comparison predicate of `hilclaw/verdicts.py` public (a rename or a thin public wrapper, no behaviour change, its tests added to `tests/test_verdicts.py`) if the executor judges that better than a second copy; then add both files to the PR description and `## Result`. Any other change: stop and report why in `## Result` (BLOCKED "requirement-unclear" if the slice cannot stand without it).

### Tests (CLAUDE.md test rule; DRIVER §5 line 113)

- `tests/test_verdicts_hypotheses.py` (new), covering every public function and the exception class of the module.
- **Happy**: the pair of the two ADR Examples (ADR-0059 Example as `hypotheses`, ADR-0071 Example as `verdicts`, **copied from the records**) passes; a round with two hypotheses and a shared candidate (decision 5) where each verdict is reached alone; an `inconclusive` verdict with empty `evidence`; a `refuted` verdict with one contrary counted comparison; an `inconclusive` verdict whose counted comparisons are only `not_different`; one with as-expected and contrary mixed; one whose comparisons are all at `sim` or have an unverified side (a `check` with `fail` or `broken`, or none) and so count for nothing; extra unknown top-level members in either document are ignored; neither document is modified (deep copy compared).
- **Negative and branch**, one case at least for each rule above and in the order stated: an invalid verdicts document and an invalid hypothesis record (their exception classes and messages unchanged; the verdicts one wins when both are invalid); another `schema_version` in either; differing `run_id`; differing `round`; a verdict for an unknown `id`; a hypothesis without a verdict; `measured.candidate` outside `tested_by` (counted and not counted); every disagreement between the recorded and the computed value (`supported` recorded where `refuted` or `inconclusive` follows, and so on for each of the six ordered pairs that the validators let through), including `supported` where one `expected` metric has no counted comparison when that is reachable; non-mapping inputs (rejected by the validators).
- `hilclaw/` line and function coverage stay ≥ 80% (CI gate); the new module's own coverage should be near 100%. ruff check and format clean.

### Process

- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0221'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0221 --state all`. Then `gh pr list --repo myungjoo/HIL-Claw --state open`: an open PR touching a file of `touchesFiles` makes the task BLOCKED ("open PR conflict"); none was open at planning time.
- Read the comments on issue #5 after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6206950125 (the ADR-0071 notice). Skip comments ending `— posted by driver`. An owner comment that objects to ADR-0071 or ADR-0059, or speaks to verdicts, hypotheses or OD-30, makes the task BLOCKED ("requirement-unclear"); quote it. An answer to HQ-0013, HQ-0014, HQ-0016..HQ-0019 or HQ-0021 does not stop this task; name it in `## Result`.
- **Guarded exit**: if a behaviour cannot be implemented without choosing something ADR-0071 or ADR-0059 leaves open (the base of the comparison, which comparisons a verdict must include, whether a sim comparison counts on sim-only hardware, how a memory ceiling counts, who enforces the rules and when), do not choose it: leave it to the caller, say so in the docstring and `## Result`, or - if the module cannot stand without it - return BLOCKED ("requirement-unclear") with the question written for an HQ.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Nothing here needs it. Tell each reviewer to write no file and start no `claude` process.
- **Code mode** (CLAUDE.md A-13): branch `claude/T-0221-verdicts-hypotheses-cross-check` from `origin/main`; Draft PR titled with `T-0221`; reviewer cycle with a fresh-context `dev-reviewer` each round (at most 7 rounds; past the cap without Approve: BLOCKED; a result starting with `SECURITY`: BLOCKED; if no reviewer can be spawned: BLOCKED, do not review your own work). Ask the reviewer to check the function against ADR-0071 decisions 1, 3 and 4 line by line - above all: the definition of a counted comparison, the three readings and the three values exactly as decision 4 states them, `against` not checked against `tested_by`, a missing verdict never read as a value, the order of checks, nothing read or written, and nothing chosen that the record leaves open.
- CI green on all jobs before merge; `gh pr merge --squash --body` with the PR body whose last line is `Task: T-0221`; delete the branch.
- Commit messages in English; executor commits end with the trailer `Task: T-0221` and any attribution trailer the session requires; the commit body has one line on the language choice (Python, as the package) and the public names chosen.
- **Prohibitions**: never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around. If the task-branch push is rejected, rebase and retry once, then BLOCKED (`branch-contention`). Past 2h30m of wall-clock time, return BLOCKED (`task-timeout`) with the state in `## Result`.
- **Size**: if the module heads past 300 lines, shorten the docstring first; if it still does not fit, propose a split in `## Follow-ups` and finish the current scope (DRIVER §5).
- **`## Result`**: do **not** commit it on the task branch. Fill it in on `main` after the merge and leave it uncommitted in the working tree for the driver's wrap-up commit (DRIVER §3-6): PR and merge commit, review rounds, CI run, coverage, the public names chosen, the language line, whether `hilclaw/verdicts.py` was touched and why, what is left to the caller and why, follow-ups. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters.

## Out of Scope

- Reading files: a caller that holds the bytes uses `hilclaw.verdicts_file.parse` and `hilclaw.hypotheses_file.parse` first. No path function, no file discovery, no directory listing.
- Binding the check to `write`, to an agent, a prompt, a hook or a tool (ADR-0071 Consequences; OD-23, OD-16, OD-18, P2-3, P2-4); refusing or repairing a pair.
- Any check against `instance.json`, result files (PLAN P1-8), the existence of a referenced attempt, the base of the comparison (OD-20, OD-28), a magnitude (OD-13, OD-1), drift, or memory ceilings (ADR-0050 decision 5).
- A shared helper module for the JSON text rules (the optional follow-up of T-0220).
- Any ARCHITECTURE, PLAN, DRIVER, README or `.claude/` edit.

## Follow-ups

- (planner, code mode, optional) A shared private helper module for the JSON text rules duplicated in `spec_file.py`, `hypotheses_file.py` and `verdicts_file.py` (`_object`, `_nan`, `_literal`, `_unsigned`).
- (planner, document mode, §9) What ADR-0071 leaves to a later record of OD-30 (a `basis` kind citing a verdict, the base of comparison with OD-20 / OD-28, rounds that never reach evaluate).
- (integrator) The "not edited and now less exact" sentences listed in ADR-0071 Consequences.

## Result
