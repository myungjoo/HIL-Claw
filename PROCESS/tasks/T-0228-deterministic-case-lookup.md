---
id: T-0228
title: Add the deterministic exact-match lookup of stored cases of a run's key directory (ADR-0073 decision 1) and the `cases_read` value it gives (decision 3) as `hilclaw/case_lookup.py`
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-18, FR-11, NFR-2, OD-30]
dependsOn: [T-0224, T-0226, T-0227]
touchesFiles: [hilclaw/case_lookup.py, tests/test_case_lookup.py, hilclaw/cases_file.py]
estimatedSize: {loc: 260, files: 2}   # excluding tests: one new module of about 200-250 lines, most of it docstring; a two-line docstring fix in cases_file.py; one new test file besides
hq: []
---
## Why

PLAN P2-7 ("가설–결과 사례 저장과 같은 키 정확 일치 조회 ... 기법 선택이 그 키의 사례를 읽고 참조를 결정 로그에 기록 ...") is open. ADR-0073 (landed `e350435` by T-0226) settles the read half of FR-18's MVP: **decision 1** the exact-match lookup of the stored cases of the run's key directory (who reads, which files count, every valid case except the reader's own run's, the parsed documents whole, deterministic ascending byte order of file names, nothing read from a source run), **decision 2** the `basis` kind `case`, **decision 3** the optional `cases_read` of `hypotheses.json`. Its Consequences (line 105) cut code slices. T-0227 (PR #150, `4407ebe`) landed decisions 2 and 3 in-file in `hilclaw/hypotheses.py`; its `## Follow-ups` names this task: "deterministic case lookup (ADR-0073 decision 1, code, T-0228 candidate)". The pieces it builds on exist: `hilclaw.key_records.lookup` (ADR-0001 decision 4 hit / miss / collision / corrupt record), `hilclaw.cases_file.parse` and `final_name` (ADR-0072 decision 2 validity, versions set apart), `hilclaw.instance.read` (the records the run's `instance.json` states).

**Why this item now.** No lock, no TODO or INTERRUPTED task, no open PR (checked 2026-10-16 at `8d11392`). T-0210 and T-0225 are BLOCKED on HQ-0021 / HQ-0022 and are not touched here. HQ-0013, HQ-0014, HQ-0016..HQ-0019 are `runtime-acceptance` and block nothing here. The task implements rules of an accepted record; it **reads** the data plane and writes nothing, and changes no data-plane file, member, value or version, so the A-13 "data-plane schema change" reason does not apply. The 7-day objection window of ADR-0073 (notice https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6210927027) ends 2026-10-23; as with T-0223/T-0224/T-0227, code may follow an accepted record inside the window, and an objection reverts both. Nothing here needs a real `claude`, a logged-in CLI, hardware or an API key (D16).

## Required Reading

Line numbers are those of `main` at `8d11392`; the text wins. Read long ARCHITECTURE lines with `fold` or `cut`, not whole files at once. Read Python and Korean files with `PYTHONIOENCODING=utf-8` (and `encoding='utf-8'` in Python; the console code page is cp949).

- **PROCESS/DRIVER.md §3-5** (line 72: executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (lines 86-115: task format, naming, trailers, size cap D4, the language line, **the test rules ① to ⑤**).
- CLAUDE.md, the whole file; above all "개발 드라이버와 런타임의 구분", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙", "코멘트 최소화", "미결은 발명하지 않는다".
- .claude/skills/dev-item-address/SKILL.md (code mode); .claude/skills/dev-code-review/SKILL.md.
- **ARCHITECTURE/decisions/ADR-0073-od30-case-lookup-and-case-basis.md**: **decision 1, lines 24-36, every bullet** (the reader, when, the key, hit and miss, which files count, which cases and how many, own run left out, what a case yields, nothing of a source run read, deterministic order, use of the output); decision 3 lines 55-61 (`cases_read`: entries of exactly `run_id` and `round`, what the lookup gave, present-and-empty versus absent); the Example (lines 63-82); **Boundaries lines 111-123** (above all line 121: "how a report of a set-apart or invalid case is carried and whether a selection may go on after it" is open; line 113: no selection rule for many cases; line 117: promotion).
- ARCHITECTURE/decisions/ADR-0072-od30-hypothesis-outcome-case-file.md decision 1 (lines 22-32: the name `case-<run_id>-<RRRR>.json`, the temporary-file form, no subdirectory) and decision 2 (lines 34-49: validity, the name against `run_id` / `round`, versions and copies of another version set apart, OD-11).
- ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md decisions 3 and 4 (collision; exact-match lookup) — as implemented in `hilclaw/key_records.py`.
- **hilclaw/key_records.py**: the module docstring (lines 1-63, its "Conventions of this module" list is the model for stating conventions the ADR does not fix), `lookup` (lines 165-190), the exception classes, `_read` (lines 208-235: `lstat`, a non-regular file reported, symlinks not followed).
- **hilclaw/cases_file.py**: the module docstring (lines 1-85; lines 83-84 say the lookup "has no code yet"), `parse` (lines 141-194), `final_name` (lines 197-218), `InvalidCaseFileError`, `UnsupportedVersionError`.
- hilclaw/cases.py: `InvalidCaseError`, `validate`, `build` (the latter for test inputs).
- hilclaw/instance.py: `OpSignature` (line 626), `Instance` (line 640), `read` (lines 848-883), `op_signature_of` (lines 977-997), the three exception classes (lines 597-612).
- hilclaw/instance_file.py `write` (line 101) and tests/test_instance_file.py helpers (lines 31-60) — for building `instance.json` in tests.
- hilclaw/layout.py: `check_run_id` (line 60), `op_signature_dir` (line 174), `case_record` (line 186).
- hilclaw/hypotheses.py: `validate` and its docstring lines 1-50 (the in-file rules for `cases_read`).
- tests/test_key_records.py helpers `hw`, `op` (lines 40-64) and fixtures (lines 131-160); tests/test_cases_file.py lines 1-60 (example case bytes) — models for test data.

## Acceptance Criteria

### `hilclaw/case_lookup.py` (new; Python, as the rest of the package)

Public names are the executor's; the suggested ones are given. Reasons for any departure go into the commit body.

- **Result types** (`NamedTuple`s):
  - `Report(path, kind, reason)`: `path` the POSIX path relative to `data_root` of the file that is reported; `kind` one of `"key_record"` (a key record file stored but colliding or not valid), `"invalid"` (a case file not valid by ADR-0072 decision 2, or an entry of the name form that is not a regular file), `"set_apart"` (a case or a copy of another integer `schema_version`, OD-11), `"unreadable"` (an `OSError` reading one case file); `reason` the message of the error.
  - `Found(key, cases, reports)`: `key` the pair of `hilclaw.keys.Key` (hw_profile, op_signature) on a hit and `None` otherwise; `cases` a tuple of case documents (each the `dict` `cases_file.parse` returned, whole, unknown members included, nothing added or repaired) in **ascending byte order of their file names** (sort by the UTF-8 bytes of the name); `reports` a tuple of `Report` in ascending byte order of `path`.
- **`find(data_root, hw_profile, op_signature, run_id)`** — the lookup for the given records (as an `instance.json` states them) and the reader's `run_id`:
  - `run_id` is checked by `layout.check_run_id` (its `InvalidPathValueError` passes through) and `data_root` must be an existing directory (`FileNotFoundError` / `NotADirectoryError`), before any file is read.
  - `op_signature is None` → `Found(None, (), ())`: a run that states no op_signature has no key, nothing is substituted (ADR-0031 decision 5, cited in ADR-0073 line 28). No file is read.
  - Otherwise `key_records.lookup(data_root, hw_profile, op_signature)`; an invalid record raises what `hilclaw.keys` raises (pass through). A miss (`None`) → `Found(None, (), ())`; nothing below the key is read or listed. `KeyCollisionError` / `CorruptKeyRecordError` → `Found(None, (), (Report(..., "key_record", ...),))` with no case (ADR-0073 line 29: "reported and yields no case"); the report's `path` is the record file the message names (the executor may derive it from the record path rather than parse the message).
  - On a hit: list the key directory once (an `OSError` of the listing passes through). Only entries **directly** in it whose name begins `case-` and ends `.json` count; every other name — `op_signature.json`, `….json.<token>.tmp` leftovers, other files, subdirectories of any other name — is ignored and never opened. No subdirectory is looked into.
  - For each counted entry, in byte order of names: an entry that is not a regular file by `os.lstat` (a directory, a symlink — not followed) → `"invalid"`. Otherwise read its bytes (an `OSError` → `"unreadable"`, the rest still read) and `cases_file.parse` them: `UnsupportedVersionError` → `"set_apart"`; `InvalidCaseFileError` → `"invalid"`; a parsed document whose `cases_file.final_name(data_root, hw.name, op.name, document)` is not the entry's path, or for which `final_name` raises (`InvalidPathValueError`), → `"invalid"` (ADR-0072 decision 2: the name formed from its `run_id` and `round`). One reported file never hides the others (ADR-0073 line 30).
  - A valid case whose `run_id` equals the reader's `run_id` is left out **silently** (no report; ADR-0073 line 32). Invalid, unreadable or set-apart files are reported whatever run they may belong to.
  - Every other valid case is in `cases`. No cap, no filter by verdict, no recency, no summary (ADR-0073 line 31); a case without `verdict_record` is returned as it is.
  - No file outside the key directory is read beyond the two key record files `key_records.lookup` reads; nothing below `runs/` is read; nothing is written, created, removed or repaired; no lock, no commit, no log line.
- **`lookup(data_root, run_id)`** — the lookup of ADR-0073 decision 1 for the run `run_id`: reads the run's `instance.json` with `hilclaw.instance.read` (its errors pass through: `MissingInstanceError`, `InvalidInstanceError`, `UnsupportedVersionError`, `OSError`, `InvalidPathValueError`) and returns `find(data_root, instance.hw_profile, instance.op_signature.record if instance.op_signature else None, run_id)`. The instance is read once; only this file of the reader's own run is read.
- **`cases_read(found)`** — returns a new `list` of `{"run_id": ..., "round": ...}` dicts, one per case of `found.cases`, in that order: the value a selection writes as `cases_read` of its `hypotheses.json` (ADR-0073 decision 3). Empty when `found.cases` is empty (a miss, no op_signature, a reported key record, no valid case of another run — ADR-0073 line 59). Raises `TypeError` for an argument that is not a `Found`.
- **Determinism** (ADR-0073 line 35): the result depends only on the two records, the key record files, the counted entries of the key directory and `run_id` — not on the order the file system lists entries in. The order claims no meaning; say so in the docstring.
- **Module docstring** in the style of `hilclaw/key_records.py`, no longer than it needs to be: which record and decisions it implements; a **"Conventions of this module, which ADR-0073 does not fix"** list — the result types and that reports are **returned, not raised**, the four report kinds, the `"unreadable"` kind, non-regular entries reported and symlinks not followed, the order of `reports` — stating that **how a report is carried to the selection and whether a selection may go on after one is not decided** (ADR-0073 Boundaries line 121; OD-18, OD-23); and what it does **not** do: it is no tool, no hook and no CLI entry; it does not decide which agent performs the lookup or how a selection is made to take its output and record `cases_read` (OD-18, OD-23); no selection rule for many cases (OD-30), no similar-key lookup (OD-4 residue), no ranking (OD-7); it does not check the rules between files of ADR-0073 decisions 2 and 3 (that a `hypotheses.json`'s `case` entries and `cases_read` name cases of the key directory); it does not resolve the *refs* inside a case or compare copies with `runs/`; it reads no other version (OD-11). No comment beyond the docstrings (CLAUDE.md "코멘트 최소화").
- **`hilclaw/cases_file.py`**: only the two docstring lines 83-84 change, so they no longer say the lookup "has no code yet" (point to `hilclaw.case_lookup`). No code change there.
- **No change** to `hilclaw/key_records.py`, `hilclaw/cases.py`, `hilclaw/instance.py`, `hilclaw/layout.py`, `hilclaw/hypotheses.py` or any other module, and no private name of another module imported. If the slice cannot stand without such a change, stop and report why in `## Result` (BLOCKED "requirement-unclear" if needed).

### Tests (CLAUDE.md test rule; DRIVER §5)

`tests/test_case_lookup.py` (new), covering every public function and type. Build data in `tmp_path` with the public writers only (`key_records.store_hw_profile` / `store_op_signature`, `cases.build` + `cases_file.write`, `instance_file.write`); for broken files, write bytes directly. Synthetic records and placeholder texts only (no real hardware or toolchain).

- **Happy**: two valid cases of two other runs plus one of the reader's own run → `cases` holds exactly the two others, in byte order of file names regardless of creation order; documents equal the parsed bytes, unknown top-level members kept; a case without `verdict_record` returned without one; `key` equals the stored keys; `reports` empty; `cases_read` gives the matching list in the same order, and a `hypotheses.json` document of the reader's run with that `cases_read` passes `hilclaw.hypotheses.validate`. `lookup(data_root, run_id)` on a written `instance.json` gives the same as `find`.
- **Branch**: instance without `op_signature` → empty `Found`, no file below `db/` read (e.g. `db/` absent); miss with no `db/`, no hw_profile record, no op_signature record (key directory present with `case-*.json` files but no `op_signature.json` → no case); hit with an empty key directory; only own-run cases → empty `cases`, no report.
- **Negative / error**: colliding and corrupt key record → one `"key_record"` report, no case, case files not read; a case file with bad JSON, one whose name does not match its `run_id` / `round`, a directory named `case-x.json`, and (where the platform allows, else skipped) a symlink of the name form → `"invalid"`, the other valid cases still returned; case and copy of `schema_version` 2 → `"set_apart"`; an unreadable file (simulate the `OSError` with `monkeypatch`) → `"unreadable"`; `….json.<token>.tmp`, `case-x.txt`, `notcase-….json` and a file inside a subdirectory → ignored (no report, not opened); a bad `run_id`, a missing `data_root`, a `data_root` that is a file, a missing `instance.json` and an invalid record → the stated exceptions; `cases_read` with a non-`Found` → `TypeError`.
- **Determinism**: the same tree gives equal results on two calls, and a listing order reversed by `monkeypatch` (of `os.listdir` / `os.scandir`, whichever the module uses) gives the same result.
- Coverage of `hilclaw/` stays ≥ 80% line and function (CI gate); `ruff` clean.

## Out of Scope

- The check of the rules between files of ADR-0073 decisions 2 and 3 (a `hypotheses.json` against the cases of its key directory) — a later code task.
- Any tool, hook, MCP registration or CLI entry exposing the lookup; which agent performs it; how a selection is made to take its output and record `cases_read` (OD-18, OD-23).
- Promotion of rounds to cases, injection, similar-key lookup, ranking, a selection rule for many cases, reading other versions (ADR-0073 Boundaries).
- Any change to `ARCHITECTURE/`, ADR-0073's R7 nits and the S5 note (a doc task).
- The shared JSON-text helper (T-0225, BLOCKED on HQ-0022).

## Follow-ups

## Result

- Landed by PR #151 (squash-merge); review: 4 rounds, Approve (nits of rounds 1 to 3 on docstring wording and wrapping fixed in the PR). Local suite: 21873 passed, 355 skipped; ruff check and format clean.
- `hilclaw/case_lookup.py` (new): `Report`, `Found`, `find`, `lookup`, `cases_read` with the suggested names; `tests/test_case_lookup.py` (new, 100% of the module; the symlink case is skipped where the platform refuses symlinks); `hilclaw/cases_file.py` docstring lines 83-84 point to the new module. No other module changed and no private name imported.
- Language: Python, as the rest of the `hilclaw` package it builds on.
- Departures stated in the module docstring and commit body: an `OSError` of `os.lstat` on a counted entry is reported as `"unreadable"` like one of reading its bytes; the `"key_record"` report path is chosen by matching the message prefix `key_records` gives against the hw_profile record path (the op_signature record path otherwise); with `op_signature is None` the hw_profile record is not validated; the name check compares the POSIX strings of `final_name` and the entry path, so a case-insensitive file system does not make a differently cased name match.
- Nothing of ADR-0073 left open was settled: how a report reaches the selection and whether a selection may go on after one stays open (Boundaries; OD-18, OD-23).
