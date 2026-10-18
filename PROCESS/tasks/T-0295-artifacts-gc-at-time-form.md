---
id: T-0295
title: Narrow the `gc_at` check of `hilclaw/artifacts.py` `validate` to the time form of ADR-0099 (ADR-0006 decision 3), with tests
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [OD-8, FR-13, NFR-2, C-3, "#5 D12"]
dependsOn: [T-0294]
touchesFiles: [hilclaw/artifacts.py, tests/test_artifacts.py]
estimatedSize: {loc: 30, files: 1}
hq: []   # Code follow-up named in ADR-0099 Consequences (accepted under DRIVER §9, T-0294). Not a new data-plane schema change: the narrowing is the change ADR-0099 decided within ADR-0005 decision 9's reservation, with no version raise. Independent of every open HQ (HQ-0021..HQ-0029 concern OD-18/OD-30/OD-8 instance-start checks, clang_build, local_run, the build log and json helpers; HQ-0013, HQ-0014, HQ-0016..HQ-0019 are runtime-acceptance). No overlap with open PR #179 (hilclaw/clang_build.py, tests/test_clang_build.py).
---
## Why

PLAN P1-8 is still open. ADR-0099 (T-0294, landed as `e85e4f2`) decided that every moment member of a data-plane file takes the form of ADR-0006 decision 3 (`YYYY-MM-DDThh:mm:ssZ`, an existing date and time, UTC), and that `gc_at` of `artifacts.json` takes it, within ADR-0005's *string*, with no `schema_version` raise. Its Consequences name exactly one code follow-up: narrow the check of a present `gc_at` in `hilclaw/artifacts.py` `validate` to that form (the check `time` gets in `hilclaw/events.py`), with tests, editing only the existing tests it lists. Until this lands, `hilclaw/artifacts.py` accepts a `gc_at` that ADR-0099 does not allow. The module still never writes `gc_at`.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (line 72; executor procedure, resume rule, time limit) and §5 (lines 86-115; task format, naming convention, `Task:` trailer in the PR body's last line, size limit, D12 test rules).
- `CLAUDE.md` "상시 규칙": "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙".
- `ARCHITECTURE/decisions/ADR-0099-od8-moment-form-of-other-files.md` — Decision §1-§3 (lines 20-41: the form; "A value is of the form exactly when `time` would accept it"; `gc_at` stays a *string*) and Consequences (lines 66-71: the follow-up and the exact list of tests to edit; the `validate` docstring to change).
- `ARCHITECTURE/decisions/ADR-0006-od8-events-log.md` decision 3 (lines 36-60; the form).
- `ARCHITECTURE/decisions/ADR-0005-od8-artifacts-record.md` decision 3 (lines 40-50) and decision 9 (lines 85-90).
- `hilclaw/artifacts.py` lines 1-125 (module docstring, `_CHECKS`, `validate` docstring) and lines 213-256 (`_member`, `_records`).
- `hilclaw/events.py` lines 55-85 (`_TIME`, `_is_time`, the `time` entry of `_CHECKS` and its rule text) — the reference check; read only, do not edit.
- `tests/test_artifacts.py` lines 30-90 (`EXAMPLE`, `rec`, `text`), 219-270 (`test_the_writer_keeps_the_layout_of_the_adr_example`, `test_validate_accepts_the_example_of_adr_0005`, `test_validate_accepts`), 311-345 (the two `SYNTHETIC-TIME` tests there), 410-480 (`BAD_GC_AT`, `BAD_MEMBERS`, `test_validate_rejects`), 556-565 (`test_add_record_requires_the_blob_also_for_a_recorded_hash`), 670-720 (stored-file-not-valid cases).

## Acceptance Criteria

1. In `hilclaw/artifacts.py`, the `gc_at` entry of `_CHECKS` accepts a value exactly when it is a `str` of the form of ADR-0006 decision 3 that is an existing date and time (the same rule as `time` in `hilclaw/events.py`: pattern `YYYY-MM-DDThh:mm:ssZ` by `fullmatch`, then the date/time must construct, so Feb 30, Feb 29 of a non-leap year, `hh` 24, `mm`/`ss` 60 and year `0000` are rejected). Implement the check inside `hilclaw/artifacts.py` (do not import a private name from `hilclaw/events.py` and do not edit `events.py`). The rule text in the error message names the form (for example "a str YYYY-MM-DDThh:mm:ssZ of an existing date and time"). Nothing else in `_CHECKS`, `_REQUIRED`, `SCHEMA_VERSION`, the member set, the writer, or the type of `gc_at` changes; the module still never writes `gc_at`. Drop `_STRING` only if nothing else uses it.
2. The `validate` docstring sentence "A ``gc_at`` is checked to be a string of ADR-0001 and nothing more" is replaced by one stating the form and citing ADR-0099; the module docstring is touched only where it becomes untrue. Comments minimal (CLAUDE.md).
3. A stored `artifacts.json` with a `gc_at` not of the form makes `load`, `add_record` and `set_retention_class` raise `CorruptArtifactsError` (follows from `validate`; no new code path).
4. Tests in `tests/test_artifacts.py`, editing only what ADR-0099 Consequences lists, plus new tests:
   - `EXAMPLE`: replace `TIME-FORM-NOT-DECIDED-HERE` with a value of the form, keeping ADR-0005's Example layout; its two users keep passing.
   - `test_validate_accepts`: the `gc_at` cases become values of the form (include boundary values such as `0001-01-01T00:00:00Z`, `9999-12-31T23:59:59Z` and a leap day `2024-02-29T12:00:00Z`).
   - The three `SYNTHETIC-TIME` tests use a value of the form.
   - `BAD_GC_AT` keeps its cases and gains strings of ADR-0001 not of the form: ADR-0005's placeholder `TIME-FORM-NOT-DECIDED-HERE`, `x`, lower-case `t`/`z`, an offset (`+00:00`), fractions (`.000Z`), a space instead of `T`, 19 and 21 characters, a trailing newline, non-ASCII digits, and non-existent dates/times (`2023-02-29`, `2024-02-30`, `hh` 24, `mm` 60, `ss` 60, year `0000`).
   - New test(s): a stored file with a `gc_at` not of the form is a `CorruptArtifactsError` for each reading function (negative case), and the error message of `validate` names the place (`artifacts[i].gc_at`) and the form.
   - No other existing test is edited.
5. D12: line and function coverage of `hilclaw/` stay ≥ 80%; happy, error, branch and negative cases present; all public functions of `hilclaw/artifacts.py` still covered. `ruff` and `pytest` pass locally; CI green.
6. Code mode (CLAUDE.md A-13): branch `claude/T-0295-artifacts-gc-at-time-form`, Draft PR with `T-0295` in the title and `Task: T-0295` as the last line of the body, reviewer cycle (dev-code-review, context-isolated, ≤ 7 rounds) to Approve, CI green, `gh pr merge --squash --body` with that body, branch deleted. No `git push --force*`.
7. `## Result`: PR number and squash commit, review rounds and unapplied findings, language and reason in one line (Python — the module is Python), coverage numbers. No `claude` process is started (D16).

## Out of Scope

- Any ADR or `ARCHITECTURE/` edit (ADR-0005's Example placeholder stays as written in the record).
- Writing `gc_at`, any GC behaviour, retention, OD-25.
- `hilclaw/events.py` or any shared time helper module; other data-plane modules (`STATE.json`, `instance.json` have no moment member).
- Open PR #179 files and blocked tasks (T-0210, T-0225, T-0231, T-0233, T-0239, T-0243, T-0264, T-0284, T-0286).

## Follow-ups

- If a shared time-form helper for the data plane seems worth having (events and artifacts), propose it as a separate code task; do not do it here.

## Result
