---
id: T-0219
title: Add the validator of a parsed verdicts file of a round (ADR-0071 decisions 2, 3, the file-local checks of decision 4, and decision 6) as `hilclaw/verdicts.py`, and its path `layout.verdict_record`; no file read or write
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-17, FR-9, OD-30, OD-8]
dependsOn: [T-0218]
touchesFiles: [hilclaw/verdicts.py, hilclaw/layout.py, tests/test_verdicts.py, tests/test_layout.py]
estimatedSize: {loc: 260, files: 2}   # excluding tests: about 230-250 lines for the new module, about 12 for layout.py; two test files besides
hq: []
---
## Why

PLAN P2-6 ("가설 레코드와 판정 ... evaluate가 가설마다 판정·원인을 기록 ... 2층의 스키마 검증·쓰기와 1층 프롬프트(P2-1·P2-3)에의 반영을 포함") is open. T-0218 landed ADR-0071 (`5ab4767`), which fixes the verdicts file of a round, `runs/<run_id>/rounds/<RRRR>/eval/verdicts.json`, and whose Consequences say: "**A code slice can be cut** (code mode, P2-6's 2층 part): a reader and validator of the bytes of this file by decisions 2, 3 and the file-local checks of decision 4, a writer by the steps of ADR-0029 decision 4 with this final name, and the path in `hilclaw/layout.py` beside `hypothesis_record`, in the manner of `hilclaw/hypotheses.py` and `hilclaw/hypotheses_file.py`; names are that task's."

That slice is about the size of `hilclaw/hypotheses.py` (216 lines) plus `hilclaw/hypotheses_file.py` (260 lines), so it exceeds the D4 cap and is split along the same line the hypothesis code took (T-0185 / T-0186):

- **This task (first half):** the pure validator of an already-parsed document (`hilclaw/verdicts.py`, the counterpart of `hilclaw/hypotheses.py`) and the path function in `hilclaw/layout.py`.
- **Next task (second half, not this one):** the bytes - `parse`, `final_name`, `write` through `hilclaw.once_write` - the counterpart of `hilclaw/hypotheses_file.py`.

**Why this item now.** No lock, no TODO or INTERRUPTED task, no open PR (checked 2026-10-16 at `94722bd`). The first unchecked PLAN items are not takeable: P0.5-4 waits on the owner's hook registration (PLAN header, D15); P1-1's remaining run-tool contract (OD-18 sub-question ⑲ and after) rests on T-0210, BLOCKED on HQ-0021, and `profiler.collect` is tied to #5 A-4 (owner-only); P1-8 needs a fresh design decision not named by any journal candidate. HQ-0013, HQ-0014, HQ-0016..HQ-0019 are `runtime-acceptance` and block nothing here. This task needs neither the run tools nor HQ-0021's answer: ADR-0071's file reads no other file and its validator depends on no run tool. It implements a landed record and changes no data-plane file, member, value or version (ADR-0071 Consequences, "A-13 reading"), so the A-13 "data-plane schema change" reason does not apply. The 7-day objection window of ADR-0071 (notice https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6206950125, ends 2026-10-23) is still open; as with T-0185 after ADR-0059, code may follow an accepted record inside the window, and an objection reverts both. The T-0218 journal line named this code slice as the next follow-up. DRIVER §6 allows an item whose `dependsOn` is met to be taken across the phase boundary.

## Required Reading

Line numbers are those of `main` at `94722bd`; the text wins. Read long ARCHITECTURE lines with `fold` or `cut`, not whole files at once. Read Python and Korean files with `PYTHONIOENCODING=utf-8` (and `encoding='utf-8'` in Python; the console code page is cp949).

- **PROCESS/DRIVER.md §3-5** (line 72: executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (lines 86-114: task format, naming, trailers, size cap D4, **the test rules ① to ⑤ at line 113**, the language line at 112).
- CLAUDE.md, the whole file; above all "개발 드라이버와 런타임의 구분", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙", "코멘트 최소화".
- .claude/skills/dev-item-address/SKILL.md (code mode); .claude/skills/dev-code-review/SKILL.md.
- **ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md, the whole record (160 lines)**: decision 1 (24-31) for the path and for the rules between two files that are *not* checked; **decision 2 (33-47), decision 3 (49-65), decision 4 (67-74; above all "A counted comparison" at 69 and "What the file itself makes checkable" at 73), decision 6 (81-83)**; the Example (85-111); Consequences (132-138) and Boundaries (140-152).
- ARCHITECTURE/decisions/ADR-0059-od30-round-hypothesis-record.md decision 2 (lines 32-50: the open top level, the version rule, an invalid file) - ADR-0071 decision 2 reads it for this file.
- ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md line 34 (the *name*, *string*, *integer* conventions); ARCHITECTURE/decisions/ADR-0002-od6-codegen-spec.md line 32 (*text*, *ref*) and decision 3 (from line 73, the *ref*).
- ARCHITECTURE/decisions/ADR-0040-od18-correctness-check-call-identity.md decision 4 (`point`: `sim` / `board`) and ARCHITECTURE/decisions/ADR-0042-od18-correctness-check-result-members.md decision 2 (from line 35: `outcome` `pass` / `fail` / `broken`) - cited by ADR-0071, read only for the spelling of the values.
- **hilclaw/hypotheses.py, the whole file** - the model of form: module docstring that says what is and is not checked, the exception with "field path: rule" messages, `SCHEMA_VERSION`, the private helpers `_name`, `_string`, `_text`, `_integer`, `_one_of`, `_object`, `_array`, `_unique`, the *ref* check inside `_basis`. **tests/test_hypotheses.py** - the model of the tests (the ADR example copied from the record, parametrised negative cases).
- **hilclaw/layout.py, the whole file** (194 lines; `ROLES` at 37, `role_dir` at 94-96, `hypothesis_record` at 104-113, `_number` at 185) and tests/test_layout.py (`every_path` at 150-160, the hypothesis_record tests at 201-212, the "exactly one role directory" test at 254-262, the invalid-argument lists near 378 and 393, the public-name set near 515-530).
- hilclaw/keys.py line 30 (`MAX_INTEGER`).

## Acceptance Criteria

### `hilclaw/layout.py`

- A new public function beside `hypothesis_record` that returns `<round_dir>/eval/verdicts.json` for (`data_root`, `run_id`, `round`), built from `role_dir(..., "eval")`. Suggested name `verdict_record`; the final name is the executor's, with the reason in the commit body.
- `round` 0 is refused with `InvalidPathValueError` before the other checks, as `hypothesis_record` does (ADR-0071 decision 6: round `0000` has no verdicts file); every other rule is that of `round_dir`. Docstring in the style of `hypothesis_record` (one short paragraph naming ADR-0071 decisions 1 and 6). No other change in `layout.py`; the module docstring's statement that it "defines no field or content of any file named here" stays true.

### `hilclaw/verdicts.py` (new; Python, as the rest of the package)

- One public validation function (suggested `validate(document)`), one public exception class (suggested `InvalidVerdictRecordError(ValueError)`, message "field path: rule" as in `hilclaw.hypotheses`), and a public `SCHEMA_VERSION = 1`. The document is the parsed JSON value; it is not modified. Return value consistent with `hypotheses.validate`.
- It checks exactly the rules of ADR-0071 decisions 2, 3, the file-local checks of decision 4 (line 73) and decision 6 that one parsed document shows, and nothing else:
  - top level: an object; `schema_version` is the *integer* `1` (any other value refused here - setting apart a newer version is the bytes module's, as in `hilclaw/hypotheses_file.py`); `run_id` a *string*; `round` an *integer* from 1 to 2**53 - 1 (round 0 refused, decision 6); `verdicts` an array of at least one entry. **The top level is open**: a member not defined by ADR-0071 is passed over, neither interpreted nor checked (decision 2, read with ADR-0059 decision 2);
  - each entry of `verdicts`: an object with exactly `hypothesis` (*name*), `verdict` (`supported` | `refuted` | `inconclusive`), `cause` (*text*), `evidence` (array); `hypothesis` unique in the file; `evidence` has at least one entry when `verdict` is `supported` or `refuted` and may be empty when it is `inconclusive`;
  - each `evidence` entry: an object whose `kind` selects its exact members - `check`: `kind`, `ref` (a *ref* of ADR-0002: exactly `round` *integer* ≥ 0, `candidate` and `attempt` *integer* ≥ 1), `point` (`sim` | `board`), `outcome` (`pass` | `fail` | `broken`); no two `check` entries of one verdict with the same (`ref`, `point`). `comparison`: `kind`, `metric` (only `latency_minimisation` admitted; any other *name*, `memory_ceiling` among them, refused), `point`, `measured` (a *ref* whose `round` **equals** the file's `round`), `against` (a *ref* whose `round` is **not above** the file's `round` and which is not equal to `measured`), `difference` (`lower` | `higher` | `not_different`). Any other `kind` is refused;
  - decision 4, file-local: a `supported` or `refuted` entry holds **at least one counted comparison** - a `comparison` entry whose `point` is `board` and for whose `measured` and `against` the same verdict holds a `check` entry at `board` with `outcome` `pass`.
- **Not checked** (state it in the module docstring, in the style of `hilclaw/hypotheses.py`): that `run_id` and `round` agree with the path; that the verdicts correspond one-to-one to the `id`s of the round's `hypotheses.json`; that the `verdict` value follows the rule of decision 4 against the hypothesis's `expected` entries; that `measured.candidate` is in the hypothesis's `tested_by`; that a *ref* names an attempt that exists; the base of the comparison (decision 4 "Open"); the recommendation on shared candidates (decision 5) is not enforced. The module reads and writes no file. No comment beyond the docstrings (CLAUDE.md "코멘트 최소화").
- Types as in `hilclaw.hypotheses`: *name* `[a-z][a-z0-9_]{0,31}`, *string* 1-255 printable ASCII, *text* a `str` of at least one character, *integer* exactly `int` (not `bool`, not a subclass) from its minimum to 2**53 - 1; an object is a `Mapping`, an array a `list`. Import nothing private from `hilclaw.hypotheses` or `hilclaw.spec`: either small private helpers of its own, or - if the executor judges the duplication too large - a shared helper module, which then counts against the size cap, needs its own test file, and must leave `hypotheses.py` behaviour unchanged (its tests pass untouched).
- **Optional (executor's choice, ADR-0071 Consequences "whether it is in that slice is that task's choice")**: a second public function over a parsed verdicts document and a parsed hypothesis document of the same round that checks the rules between the two files (one verdict per `id`, the value against `expected`, `measured.candidate` within `tested_by`). Take it **only** if the module and layout change stay within 300 LOC; otherwise leave it as a follow-up. If taken, it assumes both documents already valid, and each of its rules gets negative tests.

### Tests (CLAUDE.md test rule; DRIVER §5 line 113)

- `tests/test_verdicts.py` (new) and additions to `tests/test_layout.py`.
- Happy: the ADR-0071 Example, **copied from the record**, is valid; an `inconclusive` entry with empty `evidence`; an `inconclusive` entry holding only sim comparisons; a `refuted` entry with a counted `higher` comparison; two verdicts sharing one candidate's comparison (decision 5); a `check` at `sim` and at `board` for the same `ref`; an `against` whose `round` equals the file's round (another candidate of the round); an unknown top-level member (passed over, any JSON type).
- Negative and branch, one case at least for every rule above: wrong type for each top-level member and each entry member; missing and unknown members in a verdict, each evidence kind and a `ref`; `round` 0; `schema_version` 2, `"1"`, `True` and `1.0`; empty `verdicts`; duplicate `hypothesis`; `supported` and `refuted` with empty `evidence`; `supported` / `refuted` without a counted comparison - only a sim comparison, a board comparison without a board `pass` check on `measured`, on `against`, with a `fail` or `broken` board check, with a `pass` check only at `sim`; duplicate (`ref`, `point`) check; unknown `kind`, `verdict`, `point`, `outcome`, `difference`; `metric` `memory_ceiling` and an unknown metric; `measured.round` below and above the file's round; `against.round` above the file's round; `against` equal to `measured`; a *name*, *string* and *text* at their limits and one past them; an `int` subclass and `bool` at an *integer* place; a non-`list` sequence for an array; a non-`Mapping` at the top level and at an entry. The error message names the field path.
- `tests/test_layout.py`: the new path for a round ≥ 1 and its parent is `role_dir(..., "eval")`; round 0 and the existing invalid round values refused; invalid `run_id` refused; the new path joins `every_path`, the "every file of a round has exactly one role directory above it" check and the public-name set.
- `hilclaw/` line and function coverage stay ≥ 80% (CI gate); the new module's own coverage should be near 100%. ruff check and format clean.

### Process

- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0219'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0219 --state all`. Then `gh pr list --repo myungjoo/HIL-Claw --state open`: an open PR touching a file of `touchesFiles` makes the task BLOCKED ("open PR conflict"); none was open at planning time.
- Read the comments on issue #5 after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6206950125 (the ADR-0071 notice). Skip comments ending `— posted by driver`. An owner comment that objects to ADR-0071 or ADR-0059, or speaks to verdicts, hypotheses or OD-30, makes the task BLOCKED ("requirement-unclear"); quote it. An answer to HQ-0013, HQ-0014, HQ-0016..HQ-0019 or HQ-0021 does not stop this task; name it in `## Result`.
- **Guarded exit**: if a rule cannot be implemented without choosing something ADR-0071 leaves open (decision 4 "Open", Boundaries), do not choose it: leave it unchecked, say so in the docstring and `## Result`, or - if the module cannot stand without it - return BLOCKED ("requirement-unclear") with the question written for an HQ.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Nothing here needs it. Tell each reviewer to write no file and start no `claude` process.
- **Code mode** (CLAUDE.md A-13): branch `claude/T-0219-verdict-record-validator` from `origin/main`; Draft PR titled with `T-0219`; reviewer cycle with a fresh-context `dev-reviewer` each round (at most 7 rounds; past the cap without Approve: BLOCKED; a result starting with `SECURITY`: BLOCKED; if no reviewer can be spawned: BLOCKED, do not review your own work). Ask the reviewer to check every rule against ADR-0071 decisions 2, 3, 4 (file-local part) and 6 - nothing more checked (above all: no rule on the open top level, no admission of `memory_ceiling`, no partial-support value, no choice of the base of comparison, no cross-file rule outside the optional function), nothing less. CI green on all jobs before merge; `gh pr merge --squash --body` with the PR body whose last line is `Task: T-0219`; delete the branch.
- Commit messages in English; executor commits end with the trailer `Task: T-0219` and any attribution trailer the session requires; the commit body has one line on the language choice (Python, as the package), the reason for the path function's name, and whether the optional cross-file function was taken and why.
- **Prohibitions**: never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around. If the task-branch push is rejected, rebase and retry once, then BLOCKED (`branch-contention`). Past 2h30m of wall-clock time, return BLOCKED (`task-timeout`) with the state in `## Result`.
- **`## Result`**: fill it in on `main` after the merge and leave it uncommitted for the driver (DRIVER §3-6): PR and merge commit, review rounds, CI run, coverage, the public names chosen, the language line, what is left unchecked and why, whether the optional function was taken, follow-ups. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters.

## Out of Scope

- Bytes, parsing, the written form, the final name derived from the content, the write through `hilclaw.once_write`, and the setting apart of another `schema_version` (the next slice, counterpart of `hilclaw/hypotheses_file.py`).
- Any check across files other than the optional function above: the path, `instance.json`, the existence of a referenced attempt, result files (PLAN P1-8).
- The base of the comparison, `best_ref`, promotion, margins (OD-20, OD-28, OD-13, OD-1); a `basis` kind that cites a verdict; cases (P2-7); injection; the S6 metric (P2-8).
- Which agent writes the file, prompts, hooks, enforcement (OD-23, OD-16, OD-18, P2-1, P2-3, P2-4); any MCP tool.
- Any ARCHITECTURE, PLAN, DRIVER, README or `.claude/` edit; any change to `hilclaw/hypotheses.py` or `hilclaw/hypotheses_file.py` behaviour.

## Follow-ups

- (planner, code mode) The second half of ADR-0071's code slice: `hilclaw/verdicts_file.py` (suggested) with `parse` (ADR-0029 decision 2 text form, set apart a `schema_version` other than 1), `final_name` (path from `run_id` and `round` through the path function of this task) and `write` (ADR-0029 decisions 4 to 7 with `verdicts.json` and temporary `verdicts.json.<token>.tmp`, via `hilclaw.once_write`), on the model of `hilclaw/hypotheses_file.py`.
- (planner, code mode) The cross-file check between `verdicts.json` and `hypotheses.json`, if this task does not take it.
- (planner, document mode, §9) What ADR-0071 leaves to a later record of OD-30 (a `basis` kind citing a verdict, the base of comparison with OD-20 / OD-28, rounds that never reach evaluate).

## Result

- **Outcome**: DONE in code mode. PR https://github.com/myungjoo/HIL-Claw/pull/145 (branch `claude/T-0219-verdict-record-validator`), squash-merged by the executor; the merge commit is the one whose body ends `Task: T-0219` on `main`.
- **Review**: context-isolated `dev-reviewer`, round 1 Approve with one Nit (docstring "may be empty only when"), fixed; round 2 on the fix (see PR comments).
- **Tests and CI**: full local suite 21075 passed, 354 skipped; `hilclaw/` coverage 99% (`hilclaw/verdicts.py` and `hilclaw/layout.py` 100% line); `ruff check` and `ruff format --check` clean; CI on the PR green before merge.
- **Public names**: `hilclaw.verdicts.validate`, `hilclaw.verdicts.InvalidVerdictRecordError(ValueError)`, `hilclaw.verdicts.SCHEMA_VERSION = 1`; `hilclaw.layout.verdict_record(data_root, run_id, round)` (named after `hypothesis_record`, the path of the sibling record).
- **Language**: Python, as the rest of the package (commit body).
- **Left unchecked** (module docstring): `run_id` / `round` against the path; one verdict per `id` of `hypotheses.json`; the value against `expected`; `measured.candidate` within `tested_by`; existence of a referenced attempt; the base of the comparison (decision 4 "Open"); the shared-candidate recommendation (decision 5). A `check.ref.round` has no upper bound, as ADR-0071 sets none.
- **Optional cross-file function**: not taken; it stays a follow-up so that this slice holds the file-local rules the writer of the next slice needs.
- **Issue #5**: no comment after the ADR-0071 notice (checked 2026-10-16); no HQ answer to name.
- **Follow-ups**: as listed above (the bytes slice `hilclaw/verdicts_file.py`; the cross-file check).
