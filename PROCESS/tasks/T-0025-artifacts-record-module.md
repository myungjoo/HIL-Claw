---
id: T-0025
title: Add the blob record module (hilclaw/artifacts.py) that validates, reads and writes runs/<run_id>/artifacts.json per ADR-0005, with its tests
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [C-3, OD-8, FR-10, FR-13, NFR-2, NFR-7, C-7, "#5 A-2"]
dependsOn: [T-0008, T-0016, T-0021, T-0022, T-0024, T-0002, T-0003, T-0011]
touchesFiles: [hilclaw/artifacts.py, tests/test_artifacts.py]
estimatedSize: {loc: 230, files: 1}   # non-test: the module; the test file is excluded from the cap (D4)
hq: []   # implements a closed decision (ADR-0005); closes no OD, writes no ADR, standard library only, adds no member to the record
---
## Why
C-3 (owner decision #5 A-2) keeps binaries in the content-addressed store outside git and keeps in git only `artifacts.json` records with hash, size, type, producing round and retention class. ADR-0004 decision 6 fixed the place (`runs/<run_id>/artifacts.json`, one record per blob the run produced, written by the tool layer together with the blob store), and **ADR-0005** (`ARCHITECTURE/decisions/ADR-0005-od8-artifacts-record.md`, landed as `ae50f2d`, T-0024) fixed the content: the shape of the file, the six members of a record, identity by `sha256`, the two allowed changes, the order "blob first, then record", and `schema_version` 1. Its Consequences say: "The next code task of PLAN P1-6 can write a module that validates a file against decisions 2 and 3, adds a record after `cas.put_*` (decisions 6 and 8) and applies the two allowed edits (decision 7)."

`hilclaw/cas.py` (T-0008) stores a blob and returns `BlobRef(digest, size)` but writes no record; `hilclaw/layout.py` (T-0022) builds the path of the file but touches no file. This task adds the module between them. FR-10 asks the 2nd-layer package to validate "STATE/spec/eval/artifacts"; this is the `artifacts` part.

Planner's reading for the driver: PLAN P1-6 reads "CAS blob 저장(`blobs/sha256/..`, `artifacts.json`, retention class 기록)". With `hilclaw/cas.py` and this module all three named parts exist; `blob.push` / `blob.fetch` are named in P1-1, not in P1-6. **The executor ticks no PLAN checkbox**; say in `## Result` what of P1-6, if anything, is still missing so that the driver can decide about the checkbox.

Why this item now (planner's judgement, DRIVER §6, 2026-10-06 UTC):
- Phase P0.5 has no actionable item: P0.5-3 is BLOCKED on HQ-0003 (T-0014, unanswered on #5); the C gate of P0.5-1 waits for P1-2 / P1-3; the rest of P0.5-4 is the owner's hook registration.
- In P1: P1-3 is marked "오너 확정 필요" and is skipped, and with it P1-4, the rest of P1-2 and P1-5 slice 3. P1-1 needs request / result shapes that hang on OD-10 / 13 / 18 / 23. The P1-8 schemas need an ADR and touch the owner-only OD-3.
- This slice needs nothing that is not written down: every member, form and rule is in ADR-0005.
- No open PR at planning time. The latest comment on #5 is the ADR-0005 notice (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6022937550, 2026-10-06T18:35Z); no objection to ADR-0001..0005.

A-13 check, stated explicitly (planner's reading — the reviewer is asked to re-check it):
- "데이터 plane 스키마 변경(STATE/spec/eval/artifacts)" names `artifacts`. This module is the **first implementation** of the schema ADR-0005 defined and must add, rename or remove **no member and no rule**. The precedent is T-0018 (`hilclaw/spec.py` after ADR-0002), where all three reviewers read the BLOCKED reason as not applying. From this task on, any change of what the module accepts is an `artifacts` schema change under A-13.
- Where the ADR leaves a case unsaid, the criteria below name a provisional convention. If the executor or the reviewer reads one of them as a schema decision or as a design choice that needs an ADR or the owner, that is BLOCKED ("data-plane schema change" or "design choice needing an OD") with the exact question, not something to decide silently.
- No new external dependency: standard library only; `pyproject.toml` is unchanged.

Known risk, accepted: ADR-0005 (window until 2026-10-14), ADR-0004 (2026-10-14), ADR-0002 and ADR-0001 (2026-10-13) are inside their 7-day objection windows. An objection creates a reverting task and this module is revisited with it.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions run mode; forbidden actions held by discipline; "a denied or failed tool call is BLOCKED, never worked around"), §3 "BLOCKED 사유" paragraph, §9
- **ARCHITECTURE/decisions/ADR-0005-od8-artifacts-record.md — the whole record**: decisions 1-10, the example, Alternatives, Consequences, Boundaries
- ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md — decision 1 ("a directory exists only when something was written into it"; the path table row of `artifacts.json`), 2, **6**, **7** (last bullet: no path of the tree is a scratch or temporary location), 10 (no atomicity, no concurrency control)
- ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md — decision 1 (the value types *name*, *string*, *integer*); ARCHITECTURE/decisions/ADR-0002-od6-codegen-spec.md — the `id.round` row
- CLAUDE.md — 상시 규칙: "세 층 모델", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; the BLOCKED reasons), "테스트 규칙" ①-⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- ARCHITECTURE/Requirements.md — rows FR-10, FR-13, NFR-2, NFR-7 ②, C-2, C-3, C-7; register rows OD-8, OD-11, OD-17
- Issue #5: read every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6022937550 (`gh issue view 5 --repo myungjoo/HIL-Claw --comments`). If the owner has objected to ADR-0005, or to ADR-0001 / 0002 / 0004 in a way that changes a member, a form, the path or a rule this task uses, do not start: return BLOCKED ("requirement unclear") quoting the comment
- .claude/skills/dev-item-address/SKILL.md — the procedure to follow; .claude/skills/dev-code-review/SKILL.md — what the reviewer checks
- PROCESS/tasks/T-0023-key-record-store.md — `## Result` (the closest sibling: conventions, error message form, how unsaid cases were listed, reachability check, the four CI checks, merge and branch deletion steps); PROCESS/tasks/T-0024-adr-artifacts-record.md — `## Result`
- Existing files, read in full: `hilclaw/cas.py` (`BlobRef`, `blob_path`, `has_blob`, the `data_root` check), `hilclaw/layout.py` (`run_file`, `check_run_id`, `RUN_FILES`, `InvalidPathValueError`), `hilclaw/key_records.py` (the model for reading a stored JSON file strictly — repeated member names, exact types, not a regular file — and for a write without a temporary file), `hilclaw/keys.py` (`MAX_INTEGER`; the *name*, *string* and *integer* checks, which are private there), `tests/test_key_records.py`, `tests/test_cas.py` (test style), `pyproject.toml`, `.github/workflows/ci.yml`

## Acceptance Criteria
ADR-0005 fixes the shape, the members, the identity rule, the allowed changes and the order of writing. The module name, the public API, the error types and the handling of the cases the ADR does not mention are **conventions chosen by this task, provisional**. State each choice with one line of reason in the commit body, the PR body and `## Result`, and do not present them as requirements. Where a criterion below and ADR-0005 disagree, **the ADR wins**: follow it and say so in `## Result`.

Constraints:
- **Standard library only**, plus `hilclaw.cas`, `hilclaw.layout` and the public names of `hilclaw.keys`. Adding any package is the BLOCKED reason "new external dependency". `pyproject.toml` stays unchanged. No JSON Schema file.
- Runs on CPython 3.11 and 3.14 (both CI matrix entries) and behaves the same on POSIX and Windows hosts. The bytes of a written file are the same on every host (no `\r`, no platform default encoding, no byte order mark).
- `data_root` is always given by the caller and must be an existing directory (as in `hilclaw.cas`). The module reads no configuration and no environment variable, runs no `git`, commits nothing, and writes nowhere but `runs/<run_id>/artifacts.json` and the directories above it.
- The path comes from `layout.run_file(data_root, run_id, "artifacts.json")`; the digest form is the one `cas.blob_path` checks. The module joins no path segment itself and edits no other module. `hilclaw/keys.py` keeps its *name* / *string* checks private: do not import a private name and do not edit `keys.py`; restate the two patterns of ADR-0001 decision 1 in the module (use `keys.MAX_INTEGER`).
- **No temporary or scratch file inside `runs/`** (ADR-0004 decision 7; where scratch lives is the open rest of OD-8), and none in `blobs/sha256/` either (that would choose a scratch location). The file is written in place; the resulting limit — a process killed while it writes can leave a partial file, recoverable from the data repository's history — is stated in the module docstring (ADR-0005 decision 10, ADR-0004 decision 10).
- The module never removes or moves a record, never changes `sha256`, `size`, `type` or `round` of a stored record, and never writes `gc_at` (see Out of Scope). It stores and deletes no blob.
- No command line entry point, no `main` (OD-18 is open). No list of `type` values anywhere in the module or presented as valid in the tests (ADR-0005 decision 5).
- No value of a real run or a real artefact is written as a fact; tests use clearly synthetic values.

Module (new, `hilclaw/artifacts.py`; provisional name, flat next to the sibling modules. Python because the package is Python and JSON and file handling are in the stdlib — one line in the commit body and `## Result`):
- Module docstring that names ADR-0005 as the rule it implements, lists the conventions of this module and says what it does not do; docstrings on the public names (external API, CLAUDE.md "코멘트 최소화" exception); no other comments unless the code cannot say it.
- Public API (provisional names and shapes; the executor may rename or regroup them, but every public function must be tested and each capability must exist):
  - **Validate a document**: `validate(document)` — checks a parsed value against decisions 2, 3 and 6: an object with exactly `schema_version` (the `int` 1) and `artifacts` (a list); each record an object with exactly the five required members and optionally `gc_at`; `sha256` 64 lowercase hexadecimal characters; `size` and `round` *integer* (exactly `int`, 0 to 2^53 − 1; `bool` and `float` rejected); `type` a *name*; `retention_class` one of `best`, `final`, `intermediate`, `failed`; `gc_at`, when present, a *string* and nothing more (decision 3); no `null`; no `sha256` twice in the file. Raises an error whose message names the place (for example `artifacts[2].size`) and the rule, with values shown through `reprlib.repr`. It does not check the order of members or of records (a reader accepts any JSON text of the shape) and checks `type` against no vocabulary. A `schema_version` other than 1 is rejected; reading another version is OD-11 and is not attempted.
  - **Read**: `load(data_root, run_id)` — returns the validated records of the run in file order as plain `dict` / `str` / `int` values; a missing file gives an empty result (decision 2: a missing file and an empty array mean the same). A stored file that is not valid — not UTF-8, not JSON, a repeated member name in an object, anything `validate` rejects, not a regular file — raises a distinct error naming the path relative to `data_root`.
  - **Add a record**: `add_record(data_root, run_id, ref, *, type, round, retention_class)` — `ref` is a `cas.BlobRef` (or an equal pair of digest and size). All four values are required arguments with no default (decision 7). It requires the blob to be in the store (`cas.has_blob`), otherwise it raises and writes nothing (decision 8: a record never precedes its blob). When the file has no record with this `sha256`, the record is appended at the end and the file is written, with the directories above it created when missing. When a record exists: nothing is written, the existing record is returned unchanged with "not created" — also when `type`, `round` or the class differ (decision 6) — and a differing `size` is an error without a write. Returns the record and whether this call added it.
  - **Replace the class**: `set_retention_class(data_root, run_id, sha256, retention_class)` — the one edit of decision 7 this module performs. No record with that hash → a `LookupError` subclass, nothing written. The module judges no transition (the policy is OD-20 / OD-29 / OD-23) and allows any of the four values, also on a record that has `gc_at`. Returns the record after the call.
  - Error types (provisional): one `ValueError` subclass for a document or an argument that breaks a rule of ADR-0005; one for a stored file that cannot be used; one `LookupError` subclass for a missing record or blob; the size conflict of decision 6 as one of these or its own type — say which and why. Errors of `hilclaw.layout` for `run_id`, and `FileNotFoundError` / `NotADirectoryError` for `data_root`, pass through unchanged. Argument checks come before any file access.
- Written form (decision 2): UTF-8 without a byte order mark, LF, one final newline, each record on one line of its own with its members in the order of the table of decision 3 (`gc_at` last when present), the same bytes for the same content on every write. Take the layout of the Example of ADR-0005 unless there is a reason not to; the exact whitespace is this module's (the ADR leaves it to the writer). An edit rewrites the whole file, so a file last written by hand in another form is normalised by the next write — state this in the docstring. Records already in the file, including a `gc_at` written by someone else, are written back unchanged.
- Rules for the cases the ADR leaves unsaid (provisional; one line of reason each in `## Result`):
  - An existing invalid file makes every function raise and nothing is written; the module repairs nothing.
  - `add_record` creates `runs/<run_id>/` when it is missing (ADR-0004 decision 1: a directory exists once something is written into it); the module does not know whether the run exists.
  - Whether `set_retention_class` with the class the record already has rewrites the file: choose "no write", unless you find a reason; test it.
  - Whether `add_record` compares `ref.size` with the size of the stored blob file: not required by the ADR; do not re-hash; say what you chose.
  - Anything else you meet (a byte order mark, a symbolic link in the place of the file, JSON nested too deeply): follow `hilclaw/key_records.py` and list it.
- The argument values are not modified.

Tests (new, `tests/test_artifacts.py`; excluded from the size cap). Every test works under `tmp_path`; blobs are stored with `cas.put_bytes` on synthetic bytes; `type` values are synthetic names such as `example_kind`.
- happy:
  - `add_record` after `cas.put_bytes` creates exactly `runs/<run_id>/artifacts.json` next to the blob (assert the full list of files under `tmp_path`), returns the record with the six-member rule respected (no `gc_at`) and "created"; `load` returns it; `validate` accepts the parsed file.
  - Three records added in rounds 0, 3, 3 are loaded in order of addition (not sorted); a zero-size blob is recorded with `size` 0.
  - The written bytes are UTF-8 without a byte order mark, contain no `\r`, end with exactly one `\n`, hold each record on one line with the members in table order, and writing the same content twice gives the same bytes. Adding one record to a file of two changes no existing record line beyond the separator (decision 2, one-line diff).
  - `set_retention_class` changes exactly that member of exactly that record; every other line of the file is byte-equal.
  - `validate` accepts the Example of ADR-0005 as written in the record (including the record with `gc_at`), an empty `artifacts` array, and an unknown `type` name.
- branch:
  - Missing file → `load` returns the empty result; a file with an empty array → the same.
  - Repeated `add_record` of the same content with another `type`, `round` and class: "not created", file bytes unchanged, the first record returned.
  - The same hash recorded in the files of two runs, each with its own `round` and class.
  - A file written by hand in another valid JSON form (indented, members in another order, CRLF) is loaded; the next add normalises it and keeps every record's values, including a `gc_at`.
  - `set_retention_class` to the current class; on a record that has `gc_at` (file prepared by the test).
  - `data_root` given as `str` and as `Path`; `ref` given as `BlobRef` and as a plain tuple.
- negative (assert the error type, that the message names the place or the path, and — for every case that touches the file system — that **no file or directory was created or changed** under `tmp_path`):
  - `validate`: a non-object; a missing or extra top-level member; `schema_version` 2, `1.0`, `True`, `"1"`; `artifacts` not a list; a record that is not an object; each required member missing; an unknown member (`pushed`, `location`, `ext`, `candidate`); `sha256` upper case, 63 and 65 characters, non-hexadecimal, with a `sha256:` prefix; `size` and `round` negative, 2^53, a float, `True`, a string; `type` empty, upper case, 33 characters, with a hyphen; `retention_class` outside the four values and in another case; `gc_at` a number, `None`, empty, non-ASCII; any member `None`; the same `sha256` in two records.
  - `add_record`: each of the above for its own arguments; a digest whose blob is not in the store; a known hash with a differing `size`; an invalid `run_id` (`..`, with `/`, upper case, `None`) → `layout.InvalidPathValueError`; `data_root` that does not exist and one that is a file.
  - `set_retention_class`: unknown hash (file present, and file missing); a class outside the four; a malformed hash.
  - Stored file, each for `load`, `add_record` and `set_retention_class`: empty, invalid UTF-8, invalid JSON, a JSON array, an object with a repeated member name (top level and inside a record), `NaN`, a float `size`, `schema_version` 2, a duplicated `sha256`; the path being a directory.
  - A failing write (the file write or `os.fsync` made to raise through `monkeypatch`) raises the original error; assert what the docstring promises about the state left behind, and nothing more.
- Test rules of CLAUDE.md / DRIVER §5 (D12) apply in full: ① `hilclaw/` keeps line coverage ≥ 80 % and function coverage ≥ 80 %; ② happy, error, branch **and negative** cases; ③ every public function of the touched module is tested; ④ the new module has its test file (CI job `Test presence (hilclaw)` enforces `hilclaw/artifacts.py` → `tests/test_artifacts.py`); ⑤ no tests for test code, `pyproject.toml`, CI workflows, hook scripts or driver helper scripts. Coverage is not measured by CI yet (P0.5-3 is BLOCKED on HQ-0003), so the tests must reach every line and branch of the new module: say in `## Result` how you checked (for example `python -m trace --count --missing --coverdir <dir outside the repository> --module pytest tests/test_artifacts.py`), with throw-away scripts kept outside the repository.

Verification (record summary lines and run URLs in `## Result`):
- Local, before the commit and again before the merge, from the repository root: `python -m pytest` exits 0 (all tests; record the skip count on the driver's Windows machine — 9 on `main` today), `python -m ruff check .` exits 0, `python -m ruff format --check .` exits 0 (pinned tools: ruff 0.16.10, pytest 9.1.1).
- `git ls-files --eol hilclaw/artifacts.py tests/test_artifacts.py` shows `i/lf` for both; `git status --short` after the test run shows no stray file.
- `git diff origin/main --stat` lists only the two files in `touchesFiles`; `pyproject.toml`, `hilclaw/__init__.py`, the other modules (in particular `cas.py`, `layout.py`, `keys.py`, `key_records.py`, `spec.py`), `.claude/`, `.github/`, `README.md`, `ARCHITECTURE/` and `PROCESS/` are unchanged.
- CI on the PR: `gh pr checks <PR> --watch` ends with **four** successful checks on the final head — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `Test presence (hilclaw)`. Merge only then.
- After the squash-merge, the `push` run on `main`: check it with `gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"` and record its conclusion. If it is not `success`, do not fix forward on `main`: record the failure in `## Result` and say so in the returned summary.

Process:
- Before anything else, the §3-5 landed check: `git log origin/main --grep='^Task: T-0025'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0025 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (none at planning time).
- Code mode: branch `claude/T-0025-artifacts-record-module` from `origin/main`; Draft PR with the `DONOTMERGE` label (not in title or body); PR title contains `T-0025`; executor commits end with the trailer `Task: T-0025`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds). Ask it explicitly to (a) compare what `validate` accepts and rejects, the identity rule, the allowed changes and the order of writing with ADR-0005 decisions 2, 3, 6, 7 and 8, member by member; (b) **re-check the planner's A-13 reading in `## Why`** — that the module adds no member and no rule beyond ADR-0005 — and each provisional rule for the unsaid cases (in-place write without a temporary file, creating the run directory, requiring the blob, no function that writes `gc_at`); (c) report anything the module decides that ADR-0005 lists under Boundaries (GC, the time form of `gc_at`, push / fetch, a `type` vocabulary, class policy, locking, reading another version). If the reviewer reads (b) as a schema decision or a design choice needing an ADR, return BLOCKED with the question instead of arguing it out. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm the four checks on the final head, then `gh pr merge <PR> --squash --body-file <file>` with the PR body, whose **last line is `Task: T-0025`**. The merge guard hook is not registered, so checking the four checks before the merge is the executor's own step. Delete the remote branch and the local branch in **separate** commands and only after `gh pr view <PR> --json state` reports `MERGED` (T-0012 incident).
- Commit body: the provisional choices (module name, API grouping and return values, error types, written whitespace, in-place write, run directory creation, blob presence check, no `gc_at` writer, the unsaid cases) with one line of reason each, and the language line.
- `## Result`: fill it in **after** the merge, on `main`, and leave that edit to this task file **uncommitted** — the driver commits it in its wrap-up (DRIVER §3-6). The task branch and the PR must not contain the task file. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Size: 1 non-test file, about 230 lines; the cap is 300 LOC / 5 files (tests excluded). If the module would exceed 300 lines, finish `validate`, `load` and `add_record` and propose `set_retention_class` as a split in `Follow-ups` (DRIVER §5).
- If ADR-0005 turns out to be ambiguous or self-contradictory on a point the code must decide and that is not one of the provisional rules above, do not guess and do not edit the ADR: return BLOCKED ("requirement unclear") with the exact question.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- **Writing `gc_at`**, and anything of a GC: C-3 says the MVP builds no GC tool, ADR-0005 decision 3 says no MVP tool writes the member and leaves its time form open. The module only validates and preserves a `gc_at` that is already in a file.
- `blob.push` / `blob.fetch`, their backend, any "pushed" or "location" member (#5 B-2, #5 A-3).
- A vocabulary of `type`; which artefacts are blobs; who assigns a retention class and when (OD-20, OD-29, OD-23); `best.json`.
- A combined "store the blob and record it" call, the FR-10 tool contract and any caller (PLAN P1-1); a command line, MCP exposure or hook integration (OD-18).
- Locking, concurrency control, atomic replacement, a scratch location, isolation (OD-17, rest of OD-8, OD-14, OD-18); reading or migrating another `schema_version` (OD-11).
- Fields, schemas or validators of `STATE.json`, `instance.json`, `events.ndjson`, `build.json` or the result files (PLAN P1-8); logging an event for a blob.
- Reading or changing the real data repository `HIL-Claw-data`; using `hilclaw.config`; any `git` command on a data repository.
- Editing ADR-0001..0005, the OD register, README.md, CLAUDE.md, DRIVER.md, PLAN.md, the skills or the agents; `pyproject.toml`; any CI file; any other module under `hilclaw/`.

## Follow-ups
- (driver) Decide whether PLAN P1-6 is complete with this task (see `## Why`).
- (planner) After this task no P1 item is free of a prior decision: P1-3 is "오너 확정 필요" (owner questions in T-0021 Follow-ups); P1-8 needs an ADR in scope and a judgement on the gate fields (OD-3 is owner-only); P1-1 hangs on OD-10 / 13 / 18 / 23 and, for `blob.push` / `blob.fetch`, possibly on #5 B-2.
- (proposal, from T-0024) Register one OD for the GC design when the GC tool is planned; the `gc_at` writer belongs to it.
- (optional) Make the *name* / *string* / *integer* checks of `hilclaw/keys.py` public so that this module and `keys.py` share them.
- (P0.5-3) First coverage measurement of `hilclaw/artifacts.py` once the coverage gate exists.
- (if the owner objects to ADR-0005 or to ADR-0001 / 0002 / 0004 within its window) Revisit this module together with the reverting task.

## Result
