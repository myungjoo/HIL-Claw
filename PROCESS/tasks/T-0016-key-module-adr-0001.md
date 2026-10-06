---
id: T-0016
title: Add the key module (hilclaw/keys.py) that validates hw_profile / op_signature records and derives their directory names per ADR-0001, with its tests
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [OD-4, FR-13, FR-7, NFR-7, "#5 B-4"]
dependsOn: [T-0015, T-0002, T-0003, T-0011]
touchesFiles: [hilclaw/keys.py, tests/test_keys.py]
estimatedSize: {loc: 190, files: 1}   # non-test: the module; the test file is excluded from the cap (D4)
hq: []   # implements a closed decision (ADR-0001); closes no OD, writes no ADR, standard library only
---
## Why
ADR-0001 (`ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`, landed as `cb09aa6` by T-0015) closed the P1 minimum of OD-4: the key fields of `hw_profile` and `op_signature`, their canonical form, and the rule that turns a record into the two directory names of FR-13 (`db/<hw_profile_key>/<op_signature>/`). Its Consequences section says: "A code task implements the canonical form and the derivation and can test these two steps against the example above." This is that task. The module is a **pure function library**: field values in, canonical bytes / digest / directory name out. Every later P1 item needs it — the spec example (P1-5) and the runtime schemas (P1-8) carry both records, and the FR-10 contract (P1-1) identifies a backend by its hw_profile.

It ticks **no PLAN checkbox**: like T-0015 it is a prerequisite slice shared by P1-5, P1-8 and P1-1.

Why this item now (planner's judgement, DRIVER §6): phase P0.5 has no actionable item (P0.5-3 is BLOCKED on HQ-0003; the rest of P0.5-1 waits for P1-2 / P1-3; the rest of P0.5-4 is the owner's hook registration). Among the P1 candidates:
- P1-5 (ADR for OD-6 + `spec.json` schema + GEMM example) needs values no source gives (memory layout of the first GEMM, the kernel calling convention) and a spec schema is a data-plane schema; it is likely to need owner input.
- P1-8 (OD-8) depends on OD-3 (owner-only) and on a choice between two isolation candidates shared with OD-14.
- P1-2 slice 2 (run + timing) needs the kernel calling convention (P1-3 / P1-5).
- This task needs nothing undecided: every rule it implements is written in ADR-0001 decisions 1, 2, 3, 5 and 6.

T-0015's follow-up list placed this task "after OD-8". The planner narrows it instead: only the parts of ADR-0001 that need **no storage** are in scope. Where the full record is stored, the collision check against a stored canonical form (decision 3, second bullet) and the lookup (decision 4) all need OD-8 and are out of scope.

A-13 check, stated explicitly: this is **not** a "data-plane schema change (STATE/spec/eval/artifacts)". The module reads and writes no file, defines no `spec.json` / `STATE.json` / `eval` / `artifacts.json` shape and adds no JSON Schema file; it implements the key rule that ADR-0001 already fixed. If the executor or the reviewer finds that the implementation has to decide anything about those artefacts or about a storage location, that is BLOCKED ("data-plane schema change" or "design choice needing an OD"), not something to decide silently.

Known risk, accepted: ADR-0001 was accepted under DRIVER §9 and the owner's 7-day objection window runs until 2026-10-13 (notice: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6016440966). An objection would create a reverting task and this module would be revisited with it.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions run mode; forbidden actions held by discipline; "a denied or failed tool call is BLOCKED, never worked around"), §3 "BLOCKED 사유" paragraph, §9
- **ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md — the whole record.** It is the requirement of this task: Decision 1 (hw_profile fields and the value types below the table), 2 (op_signature fields, the `gemm` shape), 3 (canonical form, digest, directory name), 5 (what makes a new key), 6 (versioning), 7 (the example and why it is not a valid record), Consequences, Boundaries
- CLAUDE.md — 상시 규칙: "세 층 모델", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons incl. "새 외부 의존성" and "데이터 plane 스키마 변경"), "테스트 규칙" ①-⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- ARCHITECTURE/Requirements.md — rows FR-13, FR-15, NFR-7 ②, C-7; register rows OD-4, OD-6, OD-8, OD-11, OD-26 (read to know what is **not** decided here)
- Issue #5: read the comments after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6016440966 (`gh issue view 5 --repo myungjoo/HIL-Claw --comments`). If the owner has objected to ADR-0001 or to any part of it, do not start: return BLOCKED ("requirement unclear") quoting the comment
- .claude/skills/dev-item-address/SKILL.md — the procedure to follow; .claude/skills/dev-code-review/SKILL.md — what the reviewer checks
- PROCESS/tasks/T-0013-clang-build-wrapper.md — `## Acceptance Criteria` (sections "Verification" and "Process") and `## Result`: the conventions of a landed sibling code task (stdlib only, provisional choices listed with one line of reason, reachability check with the stdlib `trace` module, the four CI checks, how the `## Result` text is handed to the driver, branch deletion in a separate command after the merge is confirmed)
- PROCESS/tasks/T-0015-adr-od4-key-schema.md — `## Result` (decisions in short, boundaries, review findings about the example)
- Existing files: `pyproject.toml`, `hilclaw/__init__.py`, `hilclaw/cas.py` (style reference: module docstring, `NamedTuple` result, error class), `hilclaw/config.py` (a `ValueError` subclass for invalid input), `tests/test_cas.py` (test style), `.github/workflows/ci.yml`, `.editorconfig`, `.gitattributes`

## Acceptance Criteria
ADR-0001 fixes the field sets, the value types, the canonical form, the digest and the name rule. The module name, the public API, the result shape and the error type are **not** fixed anywhere; they are **conventions chosen by this task, provisional**. Follow the criteria below, state each choice with one line of reason in the commit body, the PR body and `## Result`, and do not present them as requirements. Where a criterion and ADR-0001 disagree, ADR-0001 wins: say so in `## Result`.

Constraints:
- **Standard library only** (`hashlib`, `json`, `re`, `typing` as needed). Adding any package is the BLOCKED reason "new external dependency". `pyproject.toml` stays unchanged.
- Runs on CPython 3.11 and 3.14 (both are CI matrix entries).
- **Pure functions**: no file, directory, environment variable, clock, `git` or network access; no use of `hilclaw.cas` or `hilclaw.config`. The module never builds a path below a data root: it returns names, the caller joins them.
- The module accepts already-parsed values (`dict`, `str`, `int`). It defines no file format, no file name and no JSON Schema file.
- No command line entry point, no `main` (OD-18 is open).
- No value of the first real instance is written into the module or its tests as a fact: no default `layout`, no default `hw_source`, no host or version string presented as real. Tests use the ADR example and clearly synthetic values.

Module (new, `hilclaw/keys.py`; provisional name, flat next to the sibling modules. Python because the package is Python and hashing and JSON are in the stdlib — one line in the commit body and `## Result`):
- Module docstring that names ADR-0001 as the rule it implements, and short docstrings on the public names (external API, CLAUDE.md "코멘트 최소화" exception); no other comments unless the code cannot say it.
- Public API (provisional names and shapes; the executor may rename or regroup them, but every public function must be tested):
  - `SCHEMA_VERSION = 1`.
  - Error type `InvalidRecordError(ValueError)`; its message names the offending field path (for example `host.cpu`) and the rule broken. Provisional: the first problem found is reported; collecting all problems is not required.
  - `Key` — a `typing.NamedTuple` with `name: str` (the directory name), `digest: str` (64 lowercase hex characters) and `canonical: bytes` (the canonical form, UTF-8).
  - `canonical_form(key_fields) -> bytes` — ADR decision 3 step 1 for a mapping that already holds exactly the key fields: UTF-8 JSON, members sorted by name at every level, no whitespace, integers in plain decimal, strings escaped only for `"` and `\`. It checks the **value-set restriction** only (every value is a string of 1 to 255 printable ASCII characters, an integer in 0 to 2^53 - 1 with `bool` excluded, or a map whose member names are names and whose values are again of these kinds; no float, boolean, null, list or tuple) and knows nothing about which fields exist.
  - `directory_name(prefix, canonical) -> Key` or an equivalent split — steps 2 and 3: SHA-256 of the canonical bytes, name `<prefix>-<first 16 hex characters>`; `prefix` must be a name (`[a-z][a-z0-9_]{0,31}`).
  - `hw_profile_key(record) -> Key` and `op_signature_key(record) -> Key` — validate a full record (key fields and attributes) against decision 1 or 2, drop the attributes, and derive the key with the prefix `accelerator` or `kind`.
- Validation rules of the two record functions (all from ADR-0001; a violation raises `InvalidRecordError`):
  - The record is a mapping. A field that is neither a key field nor an attribute of that record type is rejected (provisional: silently dropping an unknown field would hide a typo in a key field such as `tool_chain`; state the choice).
  - `schema_version` is the integer `1` (`True` and `1.0` are rejected). Any other version is rejected: reading records of another version is OD-11.
  - hw_profile: `accelerator` is a name; `revision` is a string; `toolchain` is a map of name → string with at least one member; `host` is a map of name → string or integer with the members `cpu` and `os` present; `ext`, when present, is a **non-empty** map of name → string or integer; `hw_source` is required and is exactly `external` or `in_house`; `label`, when present, is a string.
  - op_signature: `kind`, `dtype` and `layout` are names; `shape` is a map of name → integer; for `kind == "gemm"` the members of `shape` are exactly `m`, `k`, `n`; `ext` and `label` as above. The module does not restrict the values of `dtype` or `layout` beyond "is a name": their vocabularies are not decided (ADR Boundaries).
  - A `kind` for which the module knows no shape member set: provisional choice — reject it, because decision 2 says the member names are fixed per kind and the module cannot check a kind it does not know; adding a kind is then a deliberate code change (decision 6: not a schema change). If you find a reason in ADR-0001 to accept unknown kinds instead, choose that and say why; do not add the SDPA kind or guess its members.
  - Attributes never reach the canonical form: two records that differ only in `hw_source` or `label` give byte-equal canonical forms and the same `Key`.
  - Input records are not modified.
- The canonical bytes may be produced with `json.dumps(..., sort_keys=True, separators=(",", ":"))` **only if** the value-set check runs first, so that no float, non-ASCII character, control character or non-`str` member name can reach the serialiser; say in `## Result` why the output equals the form of decision 3 for the restricted value set.

Tests (new, `tests/test_keys.py`; excluded from the size cap):
- happy:
  - **The ADR example, hw side**: the hw record of decision 7 with its four `NOT-DECIDED-HERE` strings (valid strings) and a valid `hw_source` gives exactly the canonical form printed in the record, digest `b0d8610d8f470856c134056a9541f60ce9e7a5c6bfabbeb9f1b784e57c495f9f` and name `cpu_standin-b0d8610d8f470856`; both `hw_source` values give the same `Key`.
  - **The ADR example, op side**: `layout = NOT-DECIDED-HERE` is deliberately not a name, so `op_signature_key` must **reject** that record (a negative case), while `canonical_form` on the key fields plus `directory_name("gemm", ...)` gives exactly the printed canonical form, digest `c43e96fb16cc3f35b841657b1743ba0a1109fb053418b480abc1764c5befe923` and name `gemm-c43e96fb16cc3f35`. Copy the expected strings from ADR-0001, not from the implementation.
  - A valid `gemm` record with a synthetic, clearly labelled `layout` name passes; the name matches `[a-z0-9_-]+`, starts with a letter and is at most 49 characters long for a 32-character prefix.
  - Member order of the input mappings does not change the result; a `label` or the absence of `ext` does not change it.
- branch:
  - Every single key field change of decision 5 gives a different name: `revision`, a `toolchain` version, an added `toolchain` component, a `host` member value, an added `host` member, `ext`; for the operation each of `m`, `k`, `n`, `dtype`, `layout`, `ext`.
  - An integer `host` member (for example a memory size) and a string one both pass; `0` and `2**53 - 1` pass as integers; a 1-character and a 255-character string pass; a 1-character and a 32-character name pass.
  - Strings containing `"`, `\`, a space and `/` are escaped as decision 3 says (only `"` and `\`).
- negative (each raises `InvalidRecordError`, or `TypeError` where you state that choice for a non-mapping argument):
  - a record that is not a mapping; a missing required field (each one); an unknown field; `schema_version` of `2`, `0`, `True`, `"1"`, `1.0`.
  - names: empty, upper case, leading digit, a hyphen, 33 characters, non-`str`.
  - strings: empty, 256 characters, a control character (`\n`, `\x7f`), a non-ASCII character, non-`str`.
  - integers: negative, `2**53`, a `bool`, a `float`.
  - a `None`, list or nested map where a scalar is required; a `toolchain` value that is an integer.
  - empty `toolchain`; `host` without `cpu` or without `os`; an empty `ext`; a member name that is not a name in `toolchain`, `host`, `ext` and `shape`.
  - `hw_source` missing, `NOT-DECIDED-HERE`, `External`.
  - `gemm` with a missing, an extra or a non-integer shape member; an unknown `kind` (per the choice above).
  - `directory_name` with a prefix that is not a name; `canonical_form` with a float, `None`, a list, a non-`str` member name.
- Coverage is not measured by CI yet (P0.5-3 is BLOCKED on HQ-0003); the tests must still reach every line and branch of the module — say in `## Result` how you checked (for example `python -m trace --count --missing --coverdir <dir outside the repository> --module pytest tests/test_keys.py`). Test rules ①-④ of CLAUDE.md apply: every public function is tested and the new module has its test file (CI job `Test presence (hilclaw)` enforces `hilclaw/keys.py` → `tests/test_keys.py`).
- Do not add tests for other test files, `pyproject.toml` or any CI file (test rule ⑤).

Verification (record summary lines and run URLs in `## Result`):
- Local, before the commit and again before the merge, from the repository root: `python -m pytest` exits 0 (all tests, including the existing ones; the 5 real-clang tests of `tests/test_clang_build.py` skip on the driver's Windows machine — record the skip count), `python -m ruff check .` exits 0, `python -m ruff format --check .` exits 0 (pinned tools: ruff 0.16.10, pytest 9.1.1).
- `git ls-files --eol hilclaw/keys.py tests/test_keys.py` shows `i/lf` for both; `git status --short` after the test run shows no stray file.
- `git diff origin/main --stat` lists only the two files in `touchesFiles`; `pyproject.toml`, `hilclaw/__init__.py`, the other modules, `.gitignore`, `.claude/`, `.github/`, `README.md`, `ARCHITECTURE/` and `PROCESS/` are unchanged.
- CI on the PR: `gh pr checks <PR> --watch` ends with **four** successful checks on the final head — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `Test presence (hilclaw)`. Merge only then.
- After the squash-merge, the `push` run on `main`: check it with `gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"` and record its conclusion. If it is not `success`, do not fix forward on `main`: record the failure in `## Result` and say so in the returned summary.

Process:
- Code mode: branch `claude/T-0016-key-module-adr-0001`; Draft PR with the `DONOTMERGE` label (not in title or body); PR title contains `T-0016`; executor commits end with the trailer `Task: T-0016`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds). Ask it explicitly to compare every validation rule with ADR-0001 and to recompute the two example digests independently. If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Squash-merge per CLAUDE.md A-13 with `Task: T-0016` as the last line of the PR body, using `gh pr merge --squash` with that body (`--body-file` avoids quoting problems). The merge guard hook is not registered, so checking the four checks before the merge is the executor's own step. Delete the branch **after** the merge is confirmed, in a separate command (T-0012 incident).
- Commit body: the provisional choices (module name and placement, API and `Key` fields, error type and "first problem only", unknown fields rejected, unknown kinds rejected or accepted, the split between `canonical_form` and the record functions, how the canonical bytes are produced) with one line of reason each, and the language line.
- `## Result`: hand the text to the driver in your final report instead of committing this task file on the branch, so that the diff check above holds. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. This task ticks **no** PLAN checkbox; say so in `## Result`.
- Size: 1 non-test file, about 190 lines; below 300 LOC / 5 files. If the module would exceed 300 lines, finish the canonical form and the derivation with the hw side, and propose the split in `Follow-ups` (DRIVER §5).
- If ADR-0001 turns out to be ambiguous or self-contradictory on a point the code must decide (not a naming or API convention), do not guess and do not edit the ADR: return BLOCKED ("requirement unclear") with the exact question.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- Storing or reading a record: file names, the place of the full record beside the data, the `db/` tree below the two names, creating directories (OD-8, P1-8).
- The collision check against a stored canonical form (decision 3) and the lookup of decision 4: both need the stored record.
- Obtaining field values: probing the host, reading the clang version (`hilclaw.clang_build.compiler_version` is not called here), normalising `host.cpu` / `host.os` strings, the member set of `toolchain`, the `hw_source` of `cpu_standin`, registering `cpu_standin` (OD-26, ADR Boundaries).
- The memory layout of the first GEMM and the vocabularies of `layout` and `dtype`; the SDPA kind; any constant that names the real first instance.
- The similarity-vector layer, nearest-neighbour matching (rest of OD-4); reading or migrating other schema versions (OD-11).
- `spec.json`, `instance.json`, `STATE.json`, `eval`, `artifacts.json`, any JSON Schema file, any change of `hilclaw/driver_state.py` (OD-6, OD-8; data-plane schemas).
- A command line, MCP exposure or hook integration (OD-18).
- Editing ADR-0001, the OD register, README.md, CLAUDE.md, DRIVER.md, PLAN.md, the skills or the agents; `pyproject.toml`; any CI file.

## Follow-ups
- (after OD-8 / P1-8) Store the full record beside the data, add the collision check of decision 3 and the exact-match lookup of decision 4 on top of this module.
- (P1-5) The spec example builds its `op_signature` with this module once the layout question is answered; (P1-1) the FR-10 contract can identify a backend by `hw_profile_key`.
- (owner question candidates, unchanged from T-0015) the memory layout of the first GEMM; which `hw_source` value a CPU stand-in has.
- (integrator, document mode) Register the sub-questions ADR-0001 raised under OD-6 / OD-8 / OD-26 (T-0015 `## Result`, Follow-ups).
- (P0.5-3) First coverage measurement of `hilclaw/keys.py` once the coverage gate exists.
- (if the owner objects to ADR-0001 before 2026-10-13) Revisit this module together with the reverting task.

## Result
