---
id: T-0185
title: Add the validator of a parsed hypothesis record of a round (ADR-0059 decisions 2 to 5) as `hilclaw/hypotheses.py`, and its path `layout.hypothesis_record`; no file read or write
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-17, FR-11, OD-30, OD-8]
dependsOn: [T-0184]
touchesFiles: [hilclaw/hypotheses.py, hilclaw/layout.py, tests/test_hypotheses.py, tests/test_layout.py]
estimatedSize: {loc: 250, files: 2}   # excluding tests: about 220-240 lines for the new module, about 10 for layout.py; two test files besides
hq: []
---
## Why

PLAN P2-6 ("가설 레코드와 판정 ... 2층의 스키마 검증·쓰기와 1층 프롬프트(P2-1·P2-3)에의 반영을 포함") is open. T-0184 landed ADR-0059 (d7277f5), which fixes the hypothesis record of a round, `runs/<run_id>/rounds/<RRRR>/decision/hypotheses.json`, and whose Consequences say: "**A code slice can be cut** (code mode, P2-6's 2층 part): a reader and validator of the bytes of this file by decisions 2 to 5, a writer by the steps of ADR-0029 decision 4 with this final name, and the path in `hilclaw/layout.py` beside `decision_log`. Its names and call forms are that task's."

That slice is about the size of `hilclaw/spec.py` (308 lines) plus `hilclaw/spec_file.py` (350 lines), so it exceeds the D4 cap and is split along the same line the spec code took:

- **This task (first half):** the pure validator of an already-parsed document by ADR-0059 decisions 2 to 5 (`hilclaw/hypotheses.py`, the counterpart of `hilclaw/spec.py`), and the path function in `hilclaw/layout.py`.
- **Next task (second half, not this one):** the bytes - `parse`, `final_name`, `write` through `hilclaw.once_write` - the counterpart of `hilclaw/spec_file.py`.

**Why this item now.** No lock, no TODO or INTERRUPTED task, no open PR (checked 2026-10-14 after `437816b`). T-0176 (PLAN P1-1, OD-18 sub-question ⑰) is BLOCKED on HQ-0020; HQ-0013, HQ-0014, HQ-0016..HQ-0019 are `runtime-acceptance` and block nothing (their tasks are DONE). This task needs neither the run-tool contracts of P1-1 nor HQ-0020's answer: ADR-0059 reads no other file and depends on no run tool. It implements a landed record and changes no data-plane file, member, value or version (ADR-0059 Consequences, "A-13 reading"), so the A-13 "data-plane schema change" reason does not apply. The 7-day objection window of ADR-0059 (notice https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6170235111) is still open; as with T-0180 after ADR-0058, code may follow an accepted record inside the window, and an objection reverts both. The other candidate, the next OD-30 record (the verdict, whose natural place is `eval/`), may touch the A-13 "eval" reason and is left for the planner to weigh after this slice. DRIVER §6 allows an item whose `dependsOn` is met to be taken across the phase boundary.

## Required Reading

Line numbers are those of `main` at `437816b`; the text wins. Read long ARCHITECTURE lines with `fold` or `cut`, not whole files at once. Read Python with `PYTHONIOENCODING=utf-8`.

- **PROCESS/DRIVER.md §3-5** (line 72: executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (lines 86-114: task format, naming, trailers, size cap D4, **the test rules ① to ⑤ at line 113**, the language line at 112).
- CLAUDE.md, the whole file; above all "개발 드라이버와 런타임의 구분", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙", "코멘트 최소화".
- .claude/skills/dev-item-address/SKILL.md (code mode); .claude/skills/dev-code-review/SKILL.md.
- **ARCHITECTURE/decisions/ADR-0059-od30-round-hypothesis-record.md, the whole record (162 lines)**: Decision (from line 20) - decision 1 (24-31) for the path, **decision 2 (32-50), decision 3 (51-75), decision 4 (76-83), decision 5 (84-87)** for the rules, the Example (88-112), Consequences (132-139) and Boundaries (140-155).
- ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md line 34 (the *name*, *string*, *integer* conventions).
- ARCHITECTURE/decisions/ADR-0002-od6-codegen-spec.md line 32 (*text*, *ref*) and decision 3 (from line 73, the *ref* and `id.candidate`).
- ARCHITECTURE/decisions/ADR-0018-od8-instance-record-hw-profile.md decision 2 (lines 28-41): the open top level ("A reader does not interpret a member it does not know and does not treat it as an error; a validator of this record checks the two members above and, of the others, only the rules for the whole text").
- **hilclaw/spec.py, the whole file** - the model of form: module docstring that says what is and is not checked, `InvalidSpecError` with "field path: rule" messages, the private helpers `_name`, `_string`, `_text`, `_integer`, `_one_of`, `_object`, `_array`, `_ref`. **tests/test_spec.py** - the model of the tests (the ADR example copied from the record, parametrised negative cases).
- **hilclaw/layout.py, the whole file** (182 lines; `decision_log` at 99-101, `_number` at 173-176) and tests/test_layout.py (the `decision_log` tests at 192-195, 359, 373; the "every path" helpers at 149-159 and 237-246).
- hilclaw/keys.py line 30 (`MAX_INTEGER`).

## Acceptance Criteria

### `hilclaw/layout.py`

- A new public function beside `decision_log` that returns `<round_dir>/decision/hypotheses.json` for (`data_root`, `run_id`, `round`), built from `role_dir(..., "decision")` like `decision_log`. Suggested name `hypothesis_record`; the final name is the executor's, with the reason in the commit body.
- `round` 0 is refused with `InvalidPathValueError` (ADR-0059 decision 5: round `0000` has no hypothesis record), and every other rule is that of `round_dir`. If the executor judges that the path function should format round 0 like `decision_log` does and leave the rule to the validator, it may, with the reason in the commit body and the docstring - but not both silently.
- The docstring of `decision_log` is brought in line with ADR-0059 Consequences: `decision.md` is now one of two files of the round's decision log (the narrative), the other being the hypothesis record. One line; no other change in `layout.py`, and the module docstring's statement that it "defines no field or content of any file named here" stays true.

### `hilclaw/hypotheses.py` (new; Python, as the rest of the package)

- One public validation function (suggested `validate(document)`), one public exception class (suggested `InvalidHypothesisRecordError(ValueError)`, message "field path: rule" as in `hilclaw.spec`), and a public `SCHEMA_VERSION = 1`. The document is the parsed JSON value; it is not modified. The function returns nothing (or the document) on success, as the executor chooses, consistent with `spec.validate`.
- It checks exactly the rules of ADR-0059 decisions 2 to 5 that one parsed document shows, and nothing else:
  - top level: an object; `schema_version` is the *integer* `1` (any other value, an integer other than 1 included, is refused here - setting apart a newer version is the bytes module's, as in `hilclaw/spec_file.py`); `run_id` a *string*; `round` an *integer* from 1 to 2**53 - 1 (round 0 refused, decision 5); `candidates` an *integer* ≥ 1; `hypotheses` an array of at least one entry. **The top level is open**: a member not defined by ADR-0059 is passed over, neither interpreted nor checked (ADR-0059 decision 2, ADR-0018 decision 2);
  - each entry of `hypotheses`: an object with exactly `id` (*name*), `statement` (*text*), `basis` (array, ≥ 1 entry), `expected` (array, ≥ 1 entry), `origin`, `tested_by` (array of *integer* ≥ 1, ≥ 1 entry, no value twice); `id` unique in the file;
  - each `basis` entry: an object whose `kind` selects its exact members - `attempt`: `kind`, `ref` (a *ref* of ADR-0002: exactly `round` *integer*, `candidate` and `attempt` *integer* ≥ 1) whose `round` is **lower than the file's `round`**, and `text`; `external`: `kind`, `source` (*string*), `version` (*string*), `text`. `case` is **defined and not admitted** and is refused, as is any other `kind`;
  - each `expected` entry: an object with exactly `metric` and `direction`; `metric` admits only `latency_minimisation`; `direction` is `lower` or `higher`; no two entries of one hypothesis have the same `metric`;
  - `origin`: only `system` is admitted; `injected` is **defined and not admitted** and is refused, as is any other value;
  - decision 4: no value of any `tested_by` is above `candidates`, and every integer from 1 to `candidates` occurs in the `tested_by` of at least one entry.
- Types as in `hilclaw.spec`: *name* `[a-z][a-z0-9_]{0,31}`, *string* 1-255 printable ASCII, *text* a `str` of at least one character, *integer* exactly `int` (not `bool`, not a subclass) from its minimum to 2**53 - 1; an object is a `Mapping`, an array a `list`. The executor may import nothing private from `hilclaw.spec`: either small private helpers of its own, or - if it judges the duplication too large - a shared helper module, which then counts against the size cap and needs its own test file.
- The module docstring states, in the style of `hilclaw/spec.py`: which record it implements; what is **not** checked because one document does not show it (that `run_id` and `round` agree with the path, that `candidates` equals the `id.candidates` of the round's specs, that a `ref` names an attempt that exists, that the `metric` is an objective of the run's `instance.json`); that the recommendation on causal misattribution (decision 4) is not enforced; and that it reads and writes no file - the text form, the final name and the write are the next slice's. No comment beyond that (CLAUDE.md "코멘트 최소화").

### Tests (CLAUDE.md test rule; DRIVER §5 line 113)

- `tests/test_hypotheses.py` (new) and additions to `tests/test_layout.py`.
- Happy: the ADR-0059 Example, **copied from the record** (as `tests/test_spec.py` copies ADR-0050's), is valid; a valid file with N = 2 where one hypothesis spans both candidates, one with two hypotheses on one candidate, one with an `external` basis, one with `direction` `higher`, and one with an unknown top-level member (passed over, even with a value of any JSON type).
- Negative and branch, one case at least for every rule above: wrong type for each top-level member and each entry member; missing and unknown members in an entry, a `basis` entry, an `expected` entry and a `ref`; `round` 0; `schema_version` 2, `"1"`, `True` and `1.0`; empty `hypotheses`, `basis`, `expected`, `tested_by`; duplicate `id`; duplicate value in `tested_by`; duplicate `metric`; `kind` `case` and an unknown `kind`; `origin` `injected` and an unknown origin; `metric` `memory_ceiling`; a `ref.round` equal to and above the file's `round`; a `tested_by` value above `candidates`; a candidate that no entry tests; a *name*, *string* and *text* at their limits and one past them; an `int` subclass and `bool` at an *integer* place; a non-`list` sequence for an array; a non-`Mapping` at the top level. The error message names the field path.
- `tests/test_layout.py`: the new path for a round ≥ 1 and its parent is `role_dir(..., "decision")`; round 0 and the existing invalid round values refused (if the executor keeps the round-0 refusal); invalid `run_id` refused; the new path joins the "every file of a round has exactly one role directory above it" and "building paths creates nothing" checks.
- `hilclaw/` line and function coverage stay ≥ 80% (CI gate); the new module's own coverage should be near 100%. ruff clean.

### Process

- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0185'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0185 --state all`. Then `gh pr list --repo myungjoo/HIL-Claw --state open`: an open PR touching a file of `touchesFiles` makes the task BLOCKED ("open PR conflict"); none was open at planning time.
- Read the comments on issue #5 after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6170235111 (the ADR-0059 notice). Skip comments ending `— posted by driver`. An owner comment that objects to ADR-0059 or speaks to hypotheses / OD-30 makes the task BLOCKED ("requirement-unclear"); quote it. An answer to HQ-0013, HQ-0014, HQ-0016..HQ-0020 does not stop this task; name it in `## Result`.
- **Guarded exit**: if a rule of decisions 2 to 5 cannot be implemented without choosing something ADR-0059 leaves open (Boundaries), do not choose it: leave it unchecked, say so in the docstring and `## Result`, or - if the module cannot stand without it - return BLOCKED ("requirement-unclear") with the question written for an HQ.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Nothing here needs it. Tell each reviewer to write no file and start no `claude` process.
- **Code mode** (CLAUDE.md A-13): branch `claude/T-0185-hypothesis-record-validator` from `origin/main`; Draft PR titled with `T-0185`; reviewer cycle with a fresh-context `dev-reviewer` each round (at most 7 rounds; past the cap without Approve: BLOCKED; a result starting with `SECURITY`: BLOCKED; if no reviewer can be spawned: BLOCKED, do not review your own work). Ask the reviewer to check every rule against ADR-0059 decisions 2 to 5 - nothing more checked (above all: no rule on the open top level, no admission of `case`, `injected` or `memory_ceiling`, no cross-file check), nothing less. CI green on all jobs before merge; `gh pr merge --squash --body` with the PR body whose last line is `Task: T-0185`; delete the branch.
- Commit messages in English; executor commits end with the trailer `Task: T-0185` and any attribution trailer the session requires; the commit body has one line on the language choice (Python, as the package) and the reason for the path function's name and its round-0 behaviour.
- **Prohibitions**: never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around. If the task-branch push is rejected, rebase and retry once, then BLOCKED (`branch-contention`). Past 2h30m of wall-clock time, return BLOCKED (`task-timeout`) with the state in `## Result`.
- **`## Result`**: fill it in on `main` after the merge and leave it uncommitted for the driver (DRIVER §3-6): PR and merge commit, review rounds, CI run, coverage, the public names chosen, the language line, what is left unchecked and why, follow-ups. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters.

## Out of Scope

- Bytes, parsing, the written form, the final name derived from the content, the write through `hilclaw.once_write`, and the setting apart of another `schema_version` (the next slice, counterpart of `hilclaw/spec_file.py`).
- Any check across files: the path, the round's specs, `instance.json`, the existence of a referenced attempt.
- The verdict and its file (next OD-30 record), cases (P2-7), injected hypotheses, the S6 metric (P2-8).
- Which agent writes the file, prompts, hooks, enforcement (OD-23, OD-18, P2-1, P2-3, P2-4); any MCP tool.
- Any ARCHITECTURE, PLAN, DRIVER, README or `.claude/` edit; the "now less exact" sentences of ADR-0059 Consequences other than the `decision_log` docstring.

## Follow-ups

- (planner, code mode) The second half of ADR-0059's code slice: `hilclaw/hypotheses_file.py` (suggested) with `parse` (ADR-0029 decision 2 text form, set apart a `schema_version` other than 1), `final_name` (path from `run_id` and `round` through the path function of this task) and `write` (ADR-0029 decisions 4 to 7 with `hypotheses.json`, via `hilclaw.once_write`), on the model of `hilclaw/spec_file.py`.
- (planner, document mode, §9) The next part of OD-30: the verdict and cause of each hypothesis (FR-17); check first whether a file under `eval/` falls under the A-13 "data-plane schema change" reason.
- (driver/planner) T-0176 stays BLOCKED until HQ-0020 is answered.

## Result
