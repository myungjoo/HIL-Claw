---
id: T-0022
title: Add the path module (hilclaw/layout.py) that builds the data-plane paths of ADR-0004 from run_id / round / candidate / attempt and the key directory names, with its tests
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [OD-8, FR-13, FR-6, NFR-1, NFR-2, C-7]
dependsOn: [T-0021, T-0016, T-0002, T-0003, T-0011]
touchesFiles: [hilclaw/layout.py, tests/test_layout.py]
estimatedSize: {loc: 170, files: 1}   # non-test: the module; the test file is excluded from the cap (D4)
hq: []   # implements a closed decision (ADR-0004); closes no OD, writes no ADR, standard library only, defines no field of any file
---
## Why
ADR-0004 (`ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`, landed as `417b6d4` by T-0021) closed the P1 minimum of OD-8: the directory tree of the data plane. Its Consequences section says: "A code task can build every path from the tuple of ADR-0002 and the names of `hilclaw.keys`, without reading a file (PLAN P1-8). [...] what is still missing is a module that builds paths, the writer of the two key record files [...], and the `artifacts.json` record". This task is the first of the three: a **pure function library** that turns (`run_id`, `round`, `candidate`, `attempt`) and the two key directory names into paths, and that enforces the `run_id` constraint of decision 8 and the number forms of decisions 2 and 3. Every later writer of the data plane (the P1-8 schema tasks, the `artifacts.json` record of P1-6, the spec writer of P1-5 / P2-2, the key record writer) needs these paths, and none of them should format a directory name by hand.

It is **slice 2 of PLAN P1-8** and ticks **no PLAN checkbox**: the runtime STATE / instance / events schemas remain.

Why this item now (planner's judgement, DRIVER §6, 2026-10-07):
- Phase P0.5 has no actionable item: P0.5-3 is BLOCKED on HQ-0003 (T-0014, unanswered on #5); the C gate of P0.5-1 waits for P1-3; the rest of P0.5-4 is the owner's hook registration.
- P1-3 is marked "오너 확정 필요" and is skipped, and with it P1-4, the rest of P1-2 and P1-5 slice 3. P1-1 needs request / result shapes that hang on OD-10 / 13 / 18 / 23.
- The other two things ADR-0004 names as missing are not chosen: the `artifacts.json` record (P1-6) and the runtime schemas (P1-8) define fields of data-plane files, which is the A-13 reason "data-plane schema change" and touches OD-17 / OD-11; the key record writer needs a file format decision for the stored record. All three need this module first.
- This task needs nothing undecided: every path, file name and number form it implements is written in ADR-0004 decisions 1-3, 5 and 8.
- No open PR (`gh pr list` empty at planning time); no comment on #5 after the ADR-0004 notice (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6021138854, 2026-10-06T16:52Z).

A-13 check, stated explicitly:
- **Not a "data-plane schema change (STATE/spec/eval/artifacts)"**: the module reads and writes no file, defines no field of `STATE.json`, `instance.json`, `events.ndjson`, `artifacts.json`, `spec.json`, `eval.json` or any other file, and adds no JSON Schema file. It implements the paths ADR-0004 already fixed. It does **not** change `hilclaw/spec.py` (see Out of Scope).
- **No new external dependency**: standard library only; `pyproject.toml` is unchanged.
- If the executor or the reviewer finds that the implementation has to decide a field, a file format, a `run_id` form, the isolation means or anything else ADR-0004 lists under Boundaries, that is BLOCKED ("data-plane schema change" or "design choice needing an OD"), not something to decide silently.

Known risk, accepted: ADR-0004 was accepted under DRIVER §9 and the owner's 7-day objection window runs from the notice of 2026-10-06T16:52Z; ADR-0001 and ADR-0002 are inside theirs (until 2026-10-13). An objection would create a reverting task and this module would be revisited with it.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions run mode; forbidden actions held by discipline; "a denied or failed tool call is BLOCKED, never worked around"), §3 "BLOCKED 사유" paragraph, §9
- **ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md — the whole record.** It is the requirement of this task: decision 1 (top level, the tree diagram and the path table), 2 (run tree, round number form), 3 (candidate and attempt, number form, "by formatting alone"), 4 (role directories), 5 (knowledge tree and its file names), 6 (`artifacts.json` per run), 8 (`run_id` constraint), 9 (layout version 1), 10 (limits), Consequences, Boundaries
- ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md — decision 1 (the value types below the table: *name*, *string*, *integer*) and decision 3 (the directory name `<prefix>-<first 16 characters of the digest>` and the paragraph on its character set and length)
- ARCHITECTURE/decisions/ADR-0002-od6-codegen-spec.md — the `id` rows (`run_id`, `round` from 0, `candidate` and `attempt` from 1) and the definition of a *ref*
- CLAUDE.md — 상시 규칙: "세 층 모델", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons incl. "새 외부 의존성" and "데이터 plane 스키마 변경"), "테스트 규칙" ①-⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- Issue #5: read the comments after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6021138854 (`gh issue view 5 --repo myungjoo/HIL-Claw --comments`). If the owner has objected to ADR-0004, or to ADR-0001 / ADR-0002 in a way that changes a name or number this task uses, do not start: return BLOCKED ("requirement unclear") quoting the comment
- .claude/skills/dev-item-address/SKILL.md — the procedure to follow; .claude/skills/dev-code-review/SKILL.md — what the reviewer checks
- PROCESS/tasks/T-0016-key-module-adr-0001.md — `## Result`: the conventions of the sibling module this one builds on (exact `str` / `int`, `reprlib` in error messages, provisional choices listed with one line of reason, reachability check, the four CI checks, branch deletion in a separate command)
- PROCESS/tasks/T-0021-adr-od8-data-plane-layout.md — `## Result` (decisions in short, boundaries, the follow-up "P1-8 slice 2 — path module")
- Existing files: `hilclaw/keys.py` (whole file: `Key`, `NAME_DIGEST_LENGTH`, `MAX_INTEGER`, the name pattern, the error style), `hilclaw/cas.py` (`blob_path`: the model for "a path below `data_root` without touching the file system"), `hilclaw/spec.py` (`_id`, `_integer`, `_ref`: how the tuple members are typed today — read only), `tests/test_keys.py` and `tests/test_cas.py` (test style), `pyproject.toml`, `.github/workflows/ci.yml`

## Acceptance Criteria
ADR-0004 fixes the paths, the file names, the number forms and the `run_id` constraint. The module name, the public API, the return type and the error type are **not** fixed anywhere; they are **conventions chosen by this task, provisional**. Follow the criteria below, state each choice with one line of reason in the commit body, the PR body and `## Result`, and do not present them as requirements. Where a criterion and ADR-0004 disagree, ADR-0004 wins: say so in `## Result`.

Constraints:
- **Standard library only** (`pathlib`, `re`, `reprlib` as needed) plus `hilclaw.keys` for its constants. Adding any package is the BLOCKED reason "new external dependency". `pyproject.toml` stays unchanged.
- Runs on CPython 3.11 and 3.14 (both are CI matrix entries) and gives the same result on POSIX and Windows hosts (the driver machine is Windows; the targets are POSIX, C-7).
- **Pure functions**: no file, directory, environment variable, clock, `git` or network access. Nothing is created, listed, read or checked for existence; no use of `hilclaw.config` or `hilclaw.cas`. `data_root` is always given by the caller and is not validated beyond being accepted by `pathlib.Path`.
- The module defines no file content: no field, no JSON Schema, no record shape, no reader or writer.
- No `run_id` is generated, proposed or compared for uniqueness; only the constraint of decision 8 is checked.
- No command line entry point, no `main` (OD-18 is open).
- No value of a real run is written into the module or its tests as a fact; tests use clearly synthetic ids.

Module (new, `hilclaw/layout.py`; provisional name, flat next to the sibling modules. Python because the package is Python and path handling is in the stdlib — one line in the commit body and `## Result`):
- Module docstring that names ADR-0004 as the rule it implements, says what it does not do (no file access, no content, no isolation or single-writer enforcement — decision 10), and short docstrings on the public names (external API, CLAUDE.md "코멘트 최소화" exception); no other comments unless the code cannot say it.
- Public API (provisional names and shapes; the executor may rename or regroup them, but every public function must be tested and every path of the ADR listed below must be obtainable):
  - `LAYOUT_VERSION = 1` (decision 9). The module does not say where or under which name the version is stored.
  - Error type `InvalidPathValueError(ValueError)` (provisional name); its message names the argument and the rule broken and shows the value with `reprlib.repr`.
  - `check_run_id(value) -> str` — returns `value` when it is exactly a `str` that fully matches `[a-z0-9][a-z0-9_-]{0,63}` (decision 8), raises otherwise. Public so that a later task can apply the same rule elsewhere.
  - Run level: `run_dir(data_root, run_id)` and the four run-level files `STATE.json`, `instance.json`, `events.ndjson`, `artifacts.json` (four functions, or one function taking a name from a public tuple of the four).
  - Round level: `round_dir(data_root, run_id, round)` → `runs/<run_id>/rounds/<RRRR>`; `role_dir(data_root, run_id, round, role)` for the four roles `decision`, `coder`, `measure`, `eval` (the write prefix of decision 4); the decision log `…/decision/decision.md`.
  - Attempt level: `attempt_dir(data_root, run_id, round, role, candidate, attempt)` → `…/<role>/candidates/<CC>/attempts/<AA>` for the three roles `coder`, `measure`, `eval` only (`decision` has no candidate level and is rejected); and the fixed artefacts of an attempt, each under its own role: `spec.json` and `output` (a directory) under `coder/`; `build.json`, `sim.json`, `board.json`, `profile.json` under `measure/`; `eval.json` under `eval/`. One function taking an artefact name that selects role and file name is enough.
  - Knowledge tree: `hw_profile_dir(data_root, hw_profile_key)` → `db/<hw_profile_key>`; `op_signature_dir(data_root, hw_profile_key, op_signature)` → `db/<hw_profile_key>/<op_signature>`; and the files `hw_profile.json` (in the first), `op_signature.json`, `best.json`, `technique_stats.json` (in the second).
- Value rules (a violation raises the module's error; nothing is truncated, normalised or corrected):
  - `run_id`: as `check_run_id`.
  - `round` is an integer from 0, `candidate` and `attempt` are integers from 1, each at most `keys.MAX_INTEGER` and exactly `int` (`bool`, `float`, `str` are rejected) — the *integer* of ADR-0001 with the lower bounds of ADR-0002 `id`, as `hilclaw/spec.py` checks them.
  - Number forms: the round in decimal zero-padded to at least four digits (`0000`, `0001`, `9999`, `10000`); candidate and attempt zero-padded to at least two (`01`, `99`, `100`); a longer number is written in full.
  - Key directory names: exactly a `str` of the form ADR-0001 decision 3 produces — a name `[a-z][a-z0-9_]{0,31}`, a hyphen, and `keys.NAME_DIGEST_LENGTH` lowercase hexadecimal characters. Provisional: the functions take the **name string** (`Key.name`), not a `Key` or a record, so that a path can be built for a name read back from a directory listing; they do not recompute or verify the digest (that needs the stored record). State the choice.
  - Role and artefact names: only the ones listed above; an unknown one is rejected.
  - Because every component is checked against a closed pattern or built from an integer, no result can leave `data_root` (no separator, `.` or `..` can enter). Say so in the docstring.
- Return type, provisional: a `pathlib.Path` below `Path(data_root)`, as `cas.blob_path` does, so both modules are used the same way. If you find a concrete reason to return paths relative to the data root instead (or in addition), choose that and say why; do not add both without a caller.
- `blobs/sha256/<hh>/<hash>` is already `cas.blob_path` and is **not** duplicated here. Do not edit `hilclaw/cas.py`.
- The module must not import `hilclaw.spec`, and `hilclaw/spec.py` and `hilclaw/keys.py` are not edited.

Tests (new, `tests/test_layout.py`; excluded from the size cap). Compare results as `Path` objects or through `relative_to(data_root).as_posix()`, never as strings with a hard-coded separator, so the tests pass on Windows and Linux. Use `tmp_path` or a synthetic root only as a value: no test may need a directory to exist, and a test asserts that building paths creates nothing under `tmp_path`.
- happy:
  - **Every path of the ADR-0004 tree diagram and path table**, copied from the record and not from the implementation, for one synthetic tuple: the four run-level files, `rounds/0000/decision/decision.md`, the spec path quoted verbatim in decision 3 (`runs/<run_id>/rounds/<RRRR>/coder/candidates/<CC>/attempts/<AA>/spec.json`), `output`, the four `measure/` files, `eval.json`, the two key record files, `best.json`, `technique_stats.json`.
  - The attempt directories of the three roles share the suffix `candidates/<CC>/attempts/<AA>` and differ only in the role directory; every file of a round has exactly one role directory above it.
  - Key directory names derived with `hilclaw.keys` from clearly synthetic records (`keys.hw_profile_key(...).name`, `keys.op_signature_key(...).name`) are accepted, as is the ADR-0001 example name `cpu_standin-b0d8610d8f470856`.
  - `data_root` as `str` and as `Path` give the same result; a relative `data_root` stays relative (nothing is resolved).
- branch:
  - Round `0` → `0000`, `1` → `0001`, `9999`, `10000` → `10000`, `keys.MAX_INTEGER` written in full; candidate / attempt `1` → `01`, `99`, `100` → `100`.
  - `run_id` of 1 and of 64 characters; starting with a digit; containing `_` and `-` after the first character.
  - A key name with a 1-character and with a 32-character prefix.
  - Each role and each artefact name once.
- negative (each raises the module's error; assert that the message names the argument):
  - `run_id`: empty; 65 characters; upper case (`NOT-DECIDED-HERE`, the placeholder of the ADR-0002 example, is rejected); leading `_`, `-` or `.`; containing `/`, `\`, `.`, `:`, a space; `..`; a non-ASCII character; a trailing newline (`"abc\n"` — the check must be a full match); `None`, `bytes`, an `int`, a `str` subclass.
  - `round`: `-1`, `True`, `1.0`, `"1"`, `None`, `2**53`. `candidate` and `attempt`: `0`, `-1`, `True`, `"01"`, `2**53`.
  - Role: an unknown name, `decision` given to the attempt-level functions, upper case, non-`str`. Artefact: an unknown name, a file name with a directory part.
  - Key directory names: no digest part; 15 or 17 hexadecimal characters; upper-case hexadecimal; a prefix that is not a name (empty, leading digit, 33 characters, upper case); a name with `/` or `..`; the file names `hw_profile.json` and `.gitkeep`; a `keys.Key` tuple instead of its name (per the choice above); `None`.
- Test rules of CLAUDE.md / DRIVER §5 (D12) apply in full: ① `hilclaw/` keeps line coverage ≥ 80 % and function coverage ≥ 80 %; ② happy, error, branch **and negative** cases; ③ every public function of the touched module is tested; ④ the new module has its test file (CI job `Test presence (hilclaw)` enforces `hilclaw/layout.py` → `tests/test_layout.py`); ⑤ no tests for test code, `pyproject.toml`, CI workflows, hook scripts or driver helper scripts. Coverage is not measured by CI yet (P0.5-3 is BLOCKED on HQ-0003), so the tests must reach every line and branch of the new module: say in `## Result` how you checked (for example `python -m trace --count --missing --coverdir <dir outside the repository> --module pytest tests/test_layout.py`), with throw-away scripts kept outside the repository.

Verification (record summary lines and run URLs in `## Result`):
- Local, before the commit and again before the merge, from the repository root: `python -m pytest` exits 0 (all tests, including the existing ones; the real-clang tests of `tests/test_clang_build.py` and any POSIX-only test skip on the driver's Windows machine — record the skip count), `python -m ruff check .` exits 0, `python -m ruff format --check .` exits 0 (pinned tools: ruff 0.16.10, pytest 9.1.1).
- `git ls-files --eol hilclaw/layout.py tests/test_layout.py` shows `i/lf` for both; `git status --short` after the test run shows no stray file.
- `git diff origin/main --stat` lists only the two files in `touchesFiles`; `pyproject.toml`, `hilclaw/__init__.py`, the other modules (in particular `keys.py`, `spec.py`, `cas.py`), `.claude/`, `.github/`, `README.md`, `ARCHITECTURE/` and `PROCESS/` are unchanged.
- CI on the PR: `gh pr checks <PR> --watch` ends with **four** successful checks on the final head — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `Test presence (hilclaw)`. Merge only then.
- After the squash-merge, the `push` run on `main`: check it with `gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"` and record its conclusion. If it is not `success`, do not fix forward on `main`: record the failure in `## Result` and say so in the returned summary.

Process:
- Before anything else, the §3-5 landed check: `git log origin/main --grep='^Task: T-0022'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0022 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (none on 2026-10-07 at planning time).
- Code mode: branch `claude/T-0022-data-plane-path-module` from `origin/main`; Draft PR with the `DONOTMERGE` label (not in title or body); PR title contains `T-0022`; executor commits end with the trailer `Task: T-0022`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds). Ask it explicitly to (a) compare every path, file name and number form with ADR-0004 and the key name form with ADR-0001 decision 3; (b) report anything the module decides that ADR-0004 lists under Boundaries (a field, a `run_id` form, a scratch location, the isolation means, a writer check); (c) re-check the planner's A-13 reading in `## Why`. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm the four checks on the final head, then `gh pr merge <PR> --squash --body-file <file>` with the PR body, whose **last line is `Task: T-0022`**. The merge guard hook is not registered, so checking the four checks before the merge is the executor's own step. Delete the remote branch and the local branch in **separate** commands and only after `gh pr view <PR> --json state` reports `MERGED` (T-0012 incident).
- Commit body: the provisional choices (module name and placement, API grouping, error type, return type and `data_root` handling, key names as strings without digest verification, exact `str` / `int`, integer upper bound, which roles have a candidate level) with one line of reason each, and the language line.
- `## Result`: fill it in **after** the merge, on `main`, and leave that edit to this task file **uncommitted** — the driver commits it in its wrap-up (DRIVER §3-6). The task branch and the PR must not contain the task file. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. **PLAN P1-8 is not complete** after this task; say so in `## Result`.
- Size: 1 non-test file, about 170 lines; the cap is 300 LOC / 5 files (tests excluded). If the module would exceed 300 lines, finish the run tree and propose the knowledge tree as a split in `Follow-ups` (DRIVER §5).
- If ADR-0004 turns out to be ambiguous or self-contradictory on a point the code must decide (not a naming or API convention), do not guess and do not edit the ADR: return BLOCKED ("requirement unclear") with the exact question.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- Reading, writing, creating or listing anything in the data repository; any change to `HIL-Claw-data`.
- Fields, schemas and validators of `STATE.json`, `instance.json`, `events.ndjson`, `artifacts.json`, `build.json`, the result files and the `db/` files (PLAN P1-8, P1-6; OD-17, OD-20, OD-7, OD-11, OD-13); the name and place of the layout-version stamp inside `instance.json` (OD-11).
- The form of a `run_id`, generating one, uniqueness within `runs/` (ADR-0004 decision 8: open).
- **Tightening `hilclaw/spec.py`** so that `id.run_id` must satisfy the directory-name constraint: that changes what the spec validator accepts, which the planner reads as a spec schema matter (A-13). It is listed as a follow-up to be judged on its own.
- Writing the two key record files, the collision check of ADR-0001 decision 3 and the lookup of decision 4 (need a stored-record format).
- The isolation means, write-root enforcement, scratch / temporary / build-cache locations, path checks in hooks (rest of OD-8, OD-14, OD-18, OD-23).
- Files ADR-0004 leaves open: per-candidate and per-round files of a role, further records of one step for one attempt, the files inside `output/`, any further file of a key directory.
- How a branch or a continuation of a run is represented; reading runs of another layout version.
- A command line, MCP exposure or hook integration (OD-18).
- Editing ADR-0001..0004, the OD register, README.md, CLAUDE.md, DRIVER.md, PLAN.md, the skills or the agents; `pyproject.toml`; any CI file; `hilclaw/keys.py`, `hilclaw/spec.py`, `hilclaw/cas.py`.

## Follow-ups
- (planner, next candidates) The writer of the two key record files with the ADR-0001 collision check, on top of this module and `hilclaw/keys.py` — it has to settle how the full record is serialised on disk, so judge §9 / A-13 first; P1-6 slice 3 (`artifacts.json` record, using `cas.BlobRef` and the run-level path of this module) and the P1-8 schemas (runtime `STATE.json` / `instance.json` / `events.ndjson`) — both define data-plane fields and have to judge A-13 "data-plane schema change" and OD-17 / OD-11 again, likely with an ADR in scope or an HQ.
- (planner or integrator) Whether `hilclaw/spec.py` should reject an `id.run_id` that is not a valid directory name (ADR-0004 decision 8 is narrower than the *string* of ADR-0002); `check_run_id` of this module is the rule to reuse.
- (planner) PLAN P1-3 is still marked "오너 확정 필요"; its owner questions are listed in T-0021 `## Follow-ups` (oracle of `cpu_standin`, memory layout / operand order / C prototype of the first GEMM, `hw_source`).
- (integrator, from T-0021) `README.md` line 36, the FR-13 pointer to ADR-0004, the commit hash in the OD-8 register row, the `HIL-Claw-data` README.
- (P0.5-3) First coverage measurement of `hilclaw/layout.py` once the coverage gate exists.
- (if the owner objects to ADR-0004 within its window) Revisit this module together with the reverting task.

## Result
