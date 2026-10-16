---
id: T-0229
title: Add the check of the rules between a round's `hypotheses.json` and the stored cases of its key directory (ADR-0073 decisions 2 and 3) as `hilclaw/hypotheses_cases.py`
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-18, FR-11, NFR-2, OD-30]
dependsOn: [T-0227, T-0228]
touchesFiles: [hilclaw/hypotheses_cases.py, tests/test_hypotheses_cases.py, hilclaw/case_lookup.py, hilclaw/hypotheses.py]
estimatedSize: {loc: 170, files: 3}   # excluding tests: one new module of about 120-160 lines, most of it docstring; a pointer sentence in each of two module docstrings; one new test file besides
hq: []
---
## Why

PLAN P2-7 ("... 기법 선택이 그 키의 사례를 읽고 참조를 결정 로그에 기록 ...") is open. ADR-0073 (landed `e350435` by T-0226) states, besides the in-file rules that T-0227 (`4407ebe`) put in `hilclaw/hypotheses.py`, **rules between files** that no write checks:

- decision 2 (line 51): a `basis` entry of kind `case` names "a valid case in the key directory of the run's instance, and its `hypothesis_record` holds a hypothesis whose `id` is `case.hypothesis`. A reader that holds both files can check them while `db/` holds the case; a pair that breaks them is reported. What checks them and when is not decided."
- decision 3 (line 60): each `cases_read` entry "names a valid case in the key directory of the run's instance, and the entries are what the lookup gave — the second cannot be checked afterwards, since later promotions add cases."

Its Consequences (line 105) name the slice: "a check of the rules between files of decisions 2 and 3 for a reader that holds both". The rules are settled by the accepted record; only the caller and the moment are open, and this task decides neither (the same footing as `hilclaw/verdicts_hypotheses.py`, T-0221, for ADR-0071's rules between files). T-0228 (`3b5591b`) landed `hilclaw/case_lookup.py`, whose `Found` holds exactly "every valid case of the key directory except those of the reader's own run" (decision 1); since the in-file rules already forbid a `case` entry or a `cases_read` entry with the record's own `run_id`, a named case is a valid case of the key directory **iff** its (`run_id`, `round`) is that of a case in `Found.cases` of the record's run. The T-0228 docstring (lines 50-55) says this check has no code.

**Why this item now.** No lock, no TODO or INTERRUPTED task, no open PR (checked 2026-10-16 at `382254e`). T-0210 and T-0225 are BLOCKED on HQ-0021 / HQ-0022 and are not touched here. HQ-0013, HQ-0014, HQ-0016..HQ-0019 are `runtime-acceptance` and block nothing here. The task implements rules of an accepted record, reads the data plane and writes nothing; no data-plane file, member, value or version changes, so the A-13 "data-plane schema change" reason does not apply. ADR-0073's 7-day objection window (notice https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6210927027) ends 2026-10-23; as with T-0227/T-0228, code may follow an accepted record inside the window, and an objection reverts both. Nothing here needs a real `claude`, a logged-in CLI, hardware or an API key (D16).

## Required Reading

Line numbers are those of `main` at `382254e`; the text wins. Read long ARCHITECTURE lines with `fold` or `cut`, not whole files at once. Read Python and Korean files with `PYTHONIOENCODING=utf-8` (and `encoding='utf-8'` in Python; the console code page is cp949).

- **PROCESS/DRIVER.md §3-5** (line 72: executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (lines 86-115: task format, naming, trailers, size cap D4, the language line, **the test rules ① to ⑤**).
- CLAUDE.md, the whole file; above all "개발 드라이버와 런타임의 구분", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙", "코멘트 최소화", "미결은 발명하지 않는다".
- .claude/skills/dev-item-address/SKILL.md (code mode); .claude/skills/dev-code-review/SKILL.md.
- **ARCHITECTURE/decisions/ADR-0073-od30-case-lookup-and-case-basis.md**: decision 1 (lines 24-36; above all the "Which cases" and "own run left out" bullets, lines 31-32); **decision 2** (lines 38-54; the member table, the in-file rules line 50, **the rules between files line 51**); **decision 3** (lines 55-61; **line 60**, and line 59 "Absent ... never read as 'no case read'"); the Example (lines 63-82); Consequences line 105; Boundaries lines 111-123 (above all line 121: what checks the rules between files and when, and how a report is carried, are open).
- **hilclaw/verdicts_hypotheses.py** (whole, 166 lines): the model for this module — docstring layout ("Not checked ...", "This module reads, writes and logs nothing ..."), `MismatchError`, the order of checks, `_broken` / `_fail` message form with field paths and `reprlib`.
- **hilclaw/case_lookup.py**: the module docstring (lines 1-62; lines 50-55 are changed by this task), `Found` (line 84), `find` (line 100), `lookup` (line 156), `cases_read` (line 171).
- hilclaw/hypotheses.py: the module docstring (lines 1-50; lines 35-45 are changed by this task), `validate` (line 83), `_cases_read` and `_case` (lines 199-266) — what is already checked in-file.
- hilclaw/cases.py docstring (lines 1-30): what a case document holds (`hypothesis_record` is a whole copy of a valid `hypotheses.json`).
- tests/test_case_lookup.py helpers (lines 26-165: `hw`, `op`, `hypothesis_record`, `verdict_record`, `root`, `key_dir`, `store_case`, `write_instance`) — the model for building test data; tests/test_verdicts_hypotheses.py for the style of mismatch tests.

## Acceptance Criteria

### `hilclaw/hypotheses_cases.py` (new; Python, as the rest of the package)

Public names are the executor's; the suggested ones are given. Reasons for any departure go into the commit body.

- **`MismatchError(ValueError)`**: a valid hypothesis record and the cases of its key directory break a rule between them; the message names the field path in the hypothesis record and the rule (the form of `verdicts_hypotheses.MismatchError`; a separate class, not that one).
- **`check(hypotheses, found)`** — returns `None` when the parsed `hypotheses` (ADR-0059, version 1) keeps the rules between files of ADR-0073 decisions 2 and 3 against `found`, a `case_lookup.Found` the caller obtained for the record's run. In this order, the first broken rule raises:
  1. `found` is not a `case_lookup.Found` → `TypeError`. Then `hilclaw.hypotheses.validate(hypotheses)`; its error passes through unchanged.
  2. **`cases_read`** (decision 3): when present, every entry in array order has a (`run_id`, `round`) equal to that of a case in `found.cases`; otherwise `MismatchError` with path `cases_read[<i>]`. When absent, nothing of it is checked (absence is never read as "no case read", decision 3).
  3. **`case` entries** (decision 2): for every hypothesis in order and every `basis` entry of kind `case` in order: that the named case is in `found.cases` already follows from step 2 and the in-file rule (its pair is an entry of `cases_read`), so it is not checked again (no unreachable branch); that case's `hypothesis_record.hypotheses` holds an entry whose `id` equals `case.hypothesis` (path `hypotheses[<i>].basis[<j>].case.hypothesis`).
  - Not a mismatch: a case of `found.cases` that `cases_read` does not name — that the entries are **what the lookup gave** "cannot be checked afterwards" (decision 3, line 60), so only "each entry names a valid case" is checked. Not a mismatch either: anything about the verdict of the named case (decision 2: any stored hypothesis may be named, whatever its verdict or none).
  - With `found.cases` empty (a miss, no op_signature, a reported key record, no valid case of another run), a record with a non-empty `cases_read` breaks rule 2.
  - `found.reports` is not a rule of its own: a named case whose file was reported is not in `found.cases` and so breaks rule 2 or 3. The message may add the kind and reason of a report whose `path` is the case file name the entry would have (`hilclaw.layout.case_record` with the key names of `found.key`), at the executor's choice; nothing more is decided about how a report is carried (ADR-0073 line 121).
  - Neither argument is modified; no file is read.
- **`check_run(data_root, hypotheses)`** — the check for a reader that holds the record and `db/`: validates `hypotheses` (as step 1), then `case_lookup.lookup(data_root, hypotheses["run_id"])` (its errors pass through unchanged: `instance.read`'s, `InvalidPathValueError`, `FileNotFoundError` / `NotADirectoryError`, what `hilclaw.keys` raises, an `OSError` of listing), then `check(hypotheses, found)`. Returns the `Found` it used, so a caller sees the reports. It reads only what `lookup` reads.
- **Module docstring** in the style of `hilclaw/verdicts_hypotheses.py`, no longer than it needs to be: which record and decisions it implements; that `found` must be the lookup of the record's own run (`check` cannot tell, `check_run` ensures it), and why exact membership in `found.cases` is the rule "a valid case in the key directory of the run's instance" (own-run cases are left out of `Found` and forbidden in the record by the in-file rules); **not checked**: that `cases_read` is what the lookup gave at selection time (decision 3), the *refs* inside a case, the copies against `runs/`, the rules for a `hypotheses.json` copied inside a case, cases of another key or version (OD-4, OD-11); and that it does **not** decide who calls it or when, whether a write is refused on a mismatch, how a report is carried or what follows a mismatch (ADR-0073 Boundaries; OD-18, OD-23). It is no tool, no hook and no command; it writes, creates, removes and repairs nothing, takes no lock and logs nothing. No comment beyond the docstrings (CLAUDE.md "코멘트 최소화").

### Docstring pointers (no code change in these files)

- `hilclaw/case_lookup.py` lines 53-55: the sentence that it does not check the rules between files of ADR-0073 decisions 2 and 3 stays true; add that `hilclaw.hypotheses_cases` checks them.
- `hilclaw/hypotheses.py` lines 40-43: likewise, point to `hilclaw.hypotheses_cases` for the rules between files (the "what a lookup gave" part stays named as unchecked).
- **No change** to any other module (`hilclaw/cases.py`'s docstring may stay as it is), no change to existing tests, and no private name of another module imported. If the slice cannot stand without such a change, stop and report why in `## Result` (BLOCKED "requirement-unclear" if needed).

### Tests (CLAUDE.md test rule; DRIVER §5)

`tests/test_hypotheses_cases.py` (new), covering `MismatchError`, `check` and `check_run`. Build data in `tmp_path` with public writers only (`key_records.store_hw_profile` / `store_op_signature`, `cases.build` + `cases_file.write`, `instance_file.write`) or build `case_lookup.Found` values directly for `check`; synthetic records and placeholder texts only. Helpers may be copied from `tests/test_case_lookup.py` (do not import from another test module unless the suite already does so).

- **Happy**: a record of the ADR-0073 Example form whose `cases_read` names two stored cases and whose `case` entries name hypotheses of them passes `check` and `check_run`; `check_run` returns the same `Found` as `case_lookup.lookup`; a record whose `cases_read` names only some of `found.cases` passes; a `case` entry naming a refuted case and one naming a case without `verdict_record` pass.
- **Branch**: a record without `cases_read` (and so without `case` entries) passes against any `Found`, an empty one included; a record with `"cases_read": []` passes against an empty `Found`; a run with no op_signature / a miss gives an empty `Found` and a record with empty `cases_read` passes `check_run`.
- **Negative**: `cases_read` naming a case that is not stored, one whose file is invalid, set apart (version 2) or not a regular file (reported, so absent from `found.cases`), and any non-empty `cases_read` against an empty `Found` → `MismatchError` naming `cases_read[<i>]`; a `case` entry whose `case.hypothesis` is not an `id` in the named case's `hypothesis_record` → `MismatchError` naming `....case.hypothesis`; the first broken rule is the one reported when two are broken.
- **Error**: `check` with a `found` that is no `Found` → `TypeError`; an invalid hypothesis record → `InvalidHypothesisRecordError` from both functions (before any file is read by `check_run`); `check_run` with a missing `instance.json`, a missing `data_root` → the passed-through exceptions; neither argument mutated (compare with deep copies).
- Coverage of `hilclaw/` stays ≥ 80% line and function (CI gate); `ruff` clean.

## Out of Scope

- Who calls the check and when, refusing a write on a mismatch, how a lookup report reaches the selection, binding to an agent, prompt, hook, tool or CLI (OD-18, OD-23; ADR-0073 Boundaries).
- Checking that `cases_read` equals what the lookup gave at selection time (not checkable afterwards, decision 3).
- Rules for the `hypotheses.json` copy inside a stored case, promotion, injection, similar-key lookup, ranking, a selection rule for many cases, reading other versions.
- Any change to `ARCHITECTURE/`; ADR-0073's R7 nits and the S5 note, and the "now less exact" list of ADR-0073 Consequences (a doc task).
- The shared JSON-text helper (T-0225, BLOCKED on HQ-0022).

## Follow-ups

## Result

- PR #152 (squash-merged; branch `claude/T-0229-hypotheses-cases-cross-check`). Review: 2 rounds, Approve (round 1 Approve with three nits, all fixed; round 2 Approve, no findings).
- Added `hilclaw/hypotheses_cases.py` with `MismatchError`, `check(hypotheses, found)` and `check_run(data_root, hypotheses)` using the suggested names. Added pointer sentences to the docstrings of `hilclaw/case_lookup.py` and `hilclaw/hypotheses.py`. Added the new test file `tests/test_hypotheses_cases.py` (32 tests). Module coverage is 100%. `ruff check`, `ruff format --check` and the full `pytest` suite pass locally.
- I left out the optional report hint in the mismatch message. A `cases_read` `run_id` need not be a valid run id, so building the case file name could raise. ADR-0073 line 121 also leaves open how a report is carried.
- Language: Python, as the rest of `hilclaw/`.
- Follow-ups: none.
