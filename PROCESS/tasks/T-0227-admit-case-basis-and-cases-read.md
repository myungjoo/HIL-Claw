---
id: T-0227
title: Admit the `basis` kind `case` and the optional top-level member `cases_read` in the hypothesis record (ADR-0073 decisions 2 and 3, in-file rules) in `hilclaw/hypotheses.py`, and extend the `-0` text rule of `hilclaw/hypotheses_file.py` and of the hypothesis copy in `hilclaw/cases_file.py` to `cases_read`
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-18, FR-11, OD-30, "ADR-0073", "ADR-0059", "ADR-0072"]
dependsOn: [T-0226, T-0224]
touchesFiles: [hilclaw/hypotheses.py, hilclaw/hypotheses_file.py, hilclaw/cases_file.py, hilclaw/cases.py, tests/test_hypotheses.py, tests/test_hypotheses_file.py, tests/test_cases.py, tests/test_cases_file.py]
estimatedSize: {loc: 110, files: 4}   # non-test: about 50-60 lines of validation in hypotheses.py, one tuple entry each in hypotheses_file.py and cases_file.py, docstring sentences in all four; tests outside the cap (D4)
hq: []
---
## Why

PLAN P2-7 is open. ADR-0073 (landed `e350435` by T-0226) admits the `basis` kind `case` that ADR-0059 decision 3 defined and did not admit (decision 2), and defines an optional top-level member `cases_read` of `hypotheses.json` (decision 3). Its Consequences (line 105) cut this code slice first: "admitting `case` with the in-file rules of decision 2 and accepting `cases_read` by decision 3 in `hilclaw/hypotheses.py` (and its counterpart in `hilclaw/hypotheses_file.py` if its text rules cover the new member)". They do: `hypotheses_file.py` applies the `-0` text rule only below the top-level members in `_DEFINED` (line 90), and `cases_file.py` does the same for the hypothesis copy (`_COPIES`, lines 92-95). Since `cases_read[].round` is an *integer* place now, both tuples gain `cases_read`; otherwise `-0` would be accepted there while it is refused at every other integer place. ADR-0073 Consequences line 108 also says this slice changes the tests of `tests/test_hypotheses.py` that use `case` as an unadmitted kind, and line 109 names the module docstrings of `hilclaw/hypotheses.py`, `hilclaw/cases.py` and `hilclaw/cases_file.py` that call `case` not admitted or the lookup open.

The lookup itself (ADR-0073 decision 1) and the rules between files are later slices (see Follow-ups). This task ticks **no PLAN checkbox** (P2-7 continues).

Relation to T-0225 (BLOCKED, HQ-0022): T-0225 also lists `hilclaw/hypotheses_file.py` and `hilclaw/cases_file.py`, but only to move their private JSON-text helpers (`_object`, `_nan`, `_literal`, `_unsigned`, `_MINUS_ZERO`). This task changes neither those helpers nor the import list or public names of either module, so it needs nothing of HQ-0022; T-0225's saved branch will just rebase over a tuple entry and docstring sentences. Do not touch those helpers here.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, time cap) and §5 (task format, naming convention, size cap, test rules).
- `ARCHITECTURE/decisions/ADR-0073-od30-case-lookup-and-case-basis.md`: lines 20-22 (what is cited), decision 2 (lines 38-53), decision 3 (lines 55-61), Example (lines 63-82), Consequences (lines 103-109).
- `ARCHITECTURE/decisions/ADR-0059-od30-round-hypothesis-record.md`: decision 2 (open top level, version rule) and decision 3 (the `basis` table, `kind` `case` row).
- `hilclaw/hypotheses.py` (whole file, 216 lines).
- `hilclaw/hypotheses_file.py` lines 1-92 (docstring, `_DEFINED`) and 122-200 (`parse`).
- `hilclaw/cases_file.py` lines 1-100 (docstring, `_DEFINED`, `_COPIES`) and the `parse` body that walks the copies (search `_COPIES`).
- `hilclaw/cases.py` lines 1-30 (docstring).
- `tests/test_hypotheses.py` lines 1-80 (helpers) and 280-320, 405-412 (the tests using `case` as an unadmitted kind); `tests/test_hypotheses_file.py` lines 180-195 and 330-410 (`-0` tests); `tests/test_cases_file.py` lines 160-240 (`H`, `V`, `UNKNOWN`); `tests/test_cases.py` (helpers at the top).

## Acceptance Criteria

### `hilclaw/hypotheses.py`

1. `validate` accepts an optional top-level member `cases_read` (ADR-0073 decision 3). When present it is an array (a `list`), **possibly empty**, of objects with exactly `run_id` (*string*, the existing `_STRING` rule) and `round` (*integer* ≥ 1, the existing `_integer` rule); no entry has a `run_id` equal to the document's `run_id`; no (`run_id`, `round`) pair occurs twice. Its order is not checked. When absent, nothing about it is checked. Every other top-level member is still passed over as today.
2. `kind` `case` is admitted in `basis` (ADR-0073 decision 2) with exactly the members `kind`, `case`, `text`: `text` is a *text*; `case` is an object with exactly `run_id` (*string*), `round` (*integer* ≥ 1) and `hypothesis` (*name*, the existing `_NAME` rule).
3. In-file rules of decision 2: `case.run_id` differs from the document's `run_id`; the pair (`case.run_id`, `case.round`) is an entry of the document's `cases_read`. A `case` entry in a document **without** `cases_read` is refused by this rule (its pair is in no `cases_read`).
4. Order of checks, so that the first broken rule is deterministic: the existing top-level checks (`schema_version`, `run_id`, `round`, `candidates`); then `cases_read` if present (entry by entry, then uniqueness); then `hypotheses` as today, the `case` rules checked inside the basis entry after its form. Error messages name the field path in the module's existing style (`cases_read[<i>]`, `cases_read[<i>].round`, `hypotheses[<h>].basis[<b>].case`, `hypotheses[<h>].basis[<b>].case.run_id`, ...) and the broken rule; `InvalidHypothesisRecordError` stays the only error class.
5. Nothing checked between files (ADR-0073 decisions 2 and 3, "Rules between files"): not that the named case exists, not that its hypothesis record holds `case.hypothesis`, not that `cases_read` is what a lookup gave. Origin `injected` is still refused. `SCHEMA_VERSION` stays 1 (ADR-0073 decisions 2 and 3, "Version").
6. The module docstring no longer says `case` is refused; it states the two admissions with a pointer to ADR-0073, the in-file rules, and adds the between-file rules to the "Not checked" paragraph. Public names of the module do not change.

### `hilclaw/hypotheses_file.py` and `hilclaw/cases_file.py`

7. `cases_read` is added to `hypotheses_file._DEFINED` and to the defined members of the `hypothesis_record` copy in `cases_file._COPIES`, so `-0` written anywhere below `cases_read` (of the file, or of the copy in a case) is refused by its text with the module's own invalid-file error and its path, like every other integer place. Nothing else of `parse`, `final_name` or `write` changes; the private JSON-text helpers, the imports and the public names stay as they are.
8. Docstrings: where they describe validity they include ADR-0073's in-file rules (for `hypotheses_file` the rules of `hilclaw.hypotheses.validate`; for `cases_file` the copy rule), and `cases_file`'s last paragraph no longer calls the `basis` kind `case` open (the lookup stays open until its slice lands; say so only as far as ADR-0073 leaves things open: the lookup has no code yet).

### `hilclaw/cases.py`

9. Docstring only: the sentence "Nothing of the lookup, the `basis` kind `case`, ... is decided here" is corrected so it does not claim `case` is undecided (a copy is validated by `hilclaw.hypotheses.validate`, which now admits `case` and `cases_read`). No code change.

### Tests (D12: happy, error, branch and negative cases; every public function touched)

10. `tests/test_hypotheses.py`:
    - The three tests that use `case` as an unadmitted kind (`test_basis_kind_not_admitted_is_rejected` parameter `"case"`, `test_case_basis_with_a_reference_member_is_rejected`, `test_later_bad_basis_entry_is_reported_with_its_index`) are changed to fit the admission (for example use another unadmitted kind such as `"paper"`, and turn the reference-member test into a test of a malformed `case` member). These edits are expressly allowed by this task (ADR-0073 Consequences line 108); no other existing test is weakened.
    - Happy: the ADR-0073 Example document (copied from the record, as `ADR_EXAMPLE` copies ADR-0059's) is valid; `cases_read` empty and no `case` entry is valid; `cases_read` absent and no `case` entry is valid; `cases_read` listing cases no `case` entry rests on is valid; a `case` entry naming a refuted-looking hypothesis id is valid (no verdict check).
    - Negative/error: `cases_read` not an array; entry not an object; entry with a missing or an unknown member; bad `run_id` and bad `round` values (reuse `BAD_STRINGS`, `BAD_POSITIVE_INTEGERS`); entry `run_id` equal to the file's; duplicate pair. `case` entry: missing/unknown member; `case` not an object; bad `case.run_id`, `case.round`, `case.hypothesis` (reuse `BAD_NAMES`); `case.run_id` equal to the file's; pair not in `cases_read`; `cases_read` absent with a `case` entry.
    - Branch: the order of item 4 (a document breaking a `cases_read` rule and a `case` rule reports the `cases_read` one); same `run_id` with different `round` in `cases_read` is not a duplicate.
11. `tests/test_hypotheses_file.py`: `-0` at `cases_read[<i>].round` and at `hypotheses[<h>].basis[<b>].case.round` is refused with its path; a valid file with `cases_read` and a `case` entry parses to its document.
12. `tests/test_cases_file.py`: `-0` at `hypothesis_record.cases_read[<i>].round` is refused with its path; a case whose hypothesis copy holds `cases_read` and a `case` entry parses.
13. `tests/test_cases.py`: a case whose hypothesis copy holds `cases_read` and a `case` entry is valid; one whose copy breaks an in-file rule of ADR-0073 (for example a `case` pair not in `cases_read`) is refused with the `hypothesis_record.` prefix.
14. `ruff check`, `ruff format --check` and the whole `pytest` suite pass locally and in CI; line and function coverage of `hilclaw/` stay ≥ 80%.
15. `Result` names the language (Python, as the modules) with one line of reason.

## Out of Scope

- The deterministic lookup over a key directory (ADR-0073 decision 1) and any new module for it.
- The check of the rules between files of ADR-0073 decisions 2 and 3 (case exists, hypothesis id in it, `cases_read` against a lookup).
- Origin `injected`, any other `basis` kind, any `schema_version` change, any change to `verdicts.py`, `verdicts_file.py`, `key_records.py`, `layout.py`.
- The shared JSON-text helper of T-0225 (HQ-0022): do not move, rename or change `_object`, `_nan`, `_literal`, `_unsigned`, `_MINUS_ZERO` or the imports of any module.
- Any edit under `ARCHITECTURE/` (the "now less exact" list of ADR-0073 Consequences is a separate doc follow-up).
- Starting `claude` in any form (D16).

## Follow-ups

- Deterministic case lookup by ADR-0073 decision 1 (code): a module that, given `data_root`, the run's instance key and the reader's `run_id`, uses the hit of `hilclaw/key_records.py` and `hilclaw.cases_file.parse`, lists only the key directory, skips temporary files and the reader's own run, reports invalid and set-apart files without hiding the rest, and returns the cases in ascending byte order of file names.
- Check of the rules between files of ADR-0073 decisions 2 and 3 for a reader holding a `hypotheses.json` and the cases of its key directory (code).
- ADR-0073 R7 nits, the S5 note and the "not edited and now less exact" list (doc).

## Result
