---
id: T-0057
title: Add the backend table and the selection of ADR-0016 decisions 2 to 4 (hilclaw/backends.py - a backend with its name and its operations, the backend table, and the selection as a function from a hw_profile record and a HW tool to an operation) and the two reserved kinds no_backend and not_offered beside the five of hilclaw/tools.py
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, FR-14, OD-18, NFR-6, "#5 A-7", "#5 A-12"]
dependsOn: [T-0053, T-0054, T-0055, T-0056]
touchesFiles: [hilclaw/backends.py, hilclaw/tools.py, tests/test_backends.py, tests/test_tools.py]
estimatedSize: {loc: 140, files: 2}   # non-test: about 120-130 lines in the new module with its docstrings, about 8 changed lines in tools.py; the two test files are excluded from the cap (D4)
hq: []   # implements closed decisions (ADR-0016 decisions 2, 3 and 4); closes no OD, writes no ADR, standard library only, registers no tool, defines no backend, reads no data-plane file
---
## Why
ADR-0016 (landed as `7220fb4`, T-0056) fixed what a backend of an FR-10 HW tool is, the backend table, how the backend of a call is selected and the two further reserved kinds. Its Consequences cut three code slices:

> ① the backend table, the selection as a function from a hw_profile record, and the two kinds beside the five of `hilclaw/tools.py`; ② the mock backend and its scripts; ③ the path of a HW tool over a backend, checked through both fronts by a test-only tool with the mock.

**This task is slice ①.** Today the word "backend" occurs nowhere in `hilclaw/`, `hilclaw.tools.RESERVED_KINDS` holds five kinds, and nothing maps a hw_profile record to anything but its key.

It ticks **no PLAN checkbox**: P1-1 stays open (every tool, the mock backend, the `cpu_standin` backend, the path of a HW tool and the conformance tests remain). `hilclaw.tools.default_registry` keeps its signature and keeps returning an empty registry.

Planner's judgements (2026-10-08 UTC, from the files; the reviewer is asked to re-check them):
- **Slice ① is separable from ② and ③ and needs no open sub-question.** Sub-question ⑥ (where a run states its hw_profile) is not needed: ADR-0016 decision 4 says "The rule above is complete without it — a function from a hw_profile record to a backend". Sub-question ⑦ (which tools `cpu_standin` offers) is not needed: no backend is defined here. Sub-question ⑧ and the mock are slice ②.
- **Sub-question ④ of ADR-0015 stays open and this slice does not answer it.** ADR-0016 decision 4: "A hw_profile that cannot be read or is no valid record is not `no_backend`: the run cannot be used, and that kind is open". So the selection lets the error of an invalid record pass through unchanged and maps it to no kind, as `hilclaw/journaled_tool.py` does for an unusable run (T-0055).
- **Chosen over the alternative** (a small §9 record closing sub-question ④): that question is registered "with OD-10", which waits for owner input (#5 B-2), and nothing on `main` is blocked by it; the code of P1-1 is.

Why this item now: P0.5-3 is BLOCKED on HQ-0003 (T-0014); the verification half of P1-3 (T-0036), P1-4 and the "harness pass" half of P0.5-1 wait for HQ-0004; both are unanswered on #5. The rest of P0.5-4 is the owner's hook registration. P1-5 slice 3 needs owner values; the rest of P1-8 hangs on OD-3 (owner-only), OD-20, OD-23, OD-29. No open PR and no TODO / INTERRUPTED task file at planning time. The latest comment on #5 is the ADR-0016 notice (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6052048692); no objection to ADR-0001..0016.

A-13 check (planner's reading — the reviewer is asked to re-check it):
- "데이터 plane 스키마 변경": none. The hw_profile record keeps ADR-0001 as it is; the new module reads no file and names no member of a data-plane file beyond the `accelerator` field that ADR-0016 decision 4 names.
- No new external dependency: standard library only; `pyproject.toml` unchanged.
- No tool, no backend (neither the mock nor `cpu_standin`), no reach rule, no `step` value, hook, gate or roster is decided.

Known risk, accepted: ADR-0016 is inside its objection window (until 2026-10-15), ADR-0010, 0011 and 0015 until 2026-10-14. Code slices were carried out inside such windows before (T-0053, T-0054, T-0055). An objection creates a reverting task and this change is revisited with it.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, code-task test rules D12, language line in `Result`) — mandatory for every task (§6)
- PROCESS/DRIVER.md §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED, never worked around), §2 last bullet (the driver's `PROCESS/STATE.json` — never touch it), §3 "BLOCKED 사유" paragraph, §9
- **ARCHITECTURE/decisions/ADR-0016-od18-backend-frame.md** — Status (5-10), decision 1 (24-28), **decision 2 (30-40), decision 3 (42-55) and decision 4 (57-65), every sentence**, decision 5 (67-74; read to keep the mock out and not to close a door slice ② needs), the Walk-through (76-90), Limits (92-99), Alternatives rows of points 2 to 4 (103-115), Consequences (123-130), Boundaries (132-141)
- ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md — decision 2 (39-56: the reserved kinds, "not a closed list"), decision 3 (58-65: bound when the registry is built), decision 7 (112-120), Boundaries (150-159; sub-question ④)
- ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md — decision 1 (the field `accelerator`, a *name*), decision 5; ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md — decision 4 ("Result or tool failure") and decision 7 (no kept state)
- **`hilclaw/tools.py`** (280 lines): the reserved kinds (27-41), `ToolFailure` (48-67), `default_registry` (165-178, not changed), `call` (254-280)
- **`hilclaw/keys.py`**: the module docstring (1-20), `InvalidRecordError` (57-58), `hw_profile_key` (99-129) — how a hw_profile record is validated
- `hilclaw/data_root_source.py` (74 lines) and `hilclaw/journaled_tool.py` (128 lines) — the style of a small module of this layer: module docstring naming the record, what passes through, the limits; how a `ToolFailure` of a reserved kind is raised
- `tests/test_tools.py` — the reserved-kind tests (441-460 and 740-749); `tests/test_data_root_source.py` — `registry_of`, `through_command_line`, `mcp_line`, `through_mcp`, `outcome_of` (around 84-123): how one request is put through `tools.call` and both fronts in memory
- PROCESS/tasks/T-0056-adr-od18-backend-frame.md `## Result` (the decisions as landed and the review findings: which sentences said more than the inputs carry); PROCESS/tasks/T-0055-journaled-tool-path.md `## Result` ("Provisional choices" — the form this task's choices are recorded in)
- CLAUDE.md — 상시 규칙: "도구 계층 언어 정책", "브랜치·merge 절차" (code mode; BLOCKED reasons), "테스트 규칙" ①-⑤, "코멘트 최소화", "미결은 발명하지 않는다"
- .claude/skills/dev-item-address/SKILL.md (procedure); .claude/skills/dev-code-review/SKILL.md (what the reviewer checks)
- `.github/workflows/ci.yml` — five checks run on a PR; the job `Test presence (hilclaw)` requires `tests/test_backends.py` for `hilclaw/backends.py`
- Issue #5: every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6052048692 (`gh issue view 5 --repo myungjoo/HIL-Claw --comments`). If the owner has objected to ADR-0016, ADR-0015 or ADR-0001 in a way that changes a rule used here, do not start: return BLOCKED ("requirement unclear") quoting the comment

## Acceptance Criteria
ADR-0016 fixes: a backend has a name, which is an `accelerator` value, and one operation for each HW tool it offers; the frame requires no operation of a backend; the backend table maps a name to a backend and a name has one backend; the table is built from the source alone when a registry is built; the backend of a call is the entry of the table under the `accelerator` of the hw_profile record of the call and no other key field selects; `no_backend` and `not_offered` with their meanings; a hw_profile that is no valid record is not `no_backend`. The names of the new public objects, the form of their parameters and the cases the record does not mention are **this task's choices, provisional**: state each with one line of reason in the commit body, the PR body and `## Result`. Where a criterion below and a record disagree, **the record wins**: follow it and say so in `## Result`.

### Files
- `hilclaw/backends.py` (new): about 120-130 lines with its docstrings.
- `hilclaw/tools.py` (edited): two constants, two members of `RESERVED_KINDS`, the comment at line 27. Nothing else.
- `tests/test_backends.py` (new); `tests/test_tools.py` (edited: the reserved-kind test).
- Python, because the modules it joins are Python — one line in the commit body and `## Result`.
- Nothing else. `hilclaw/keys.py`, `hilclaw/key_records.py`, `hilclaw/journaled_tool.py`, `hilclaw/journaled_step.py`, the two fronts, `pyproject.toml`, `.github/`, every ADR and the OD register stay as they are.

### The two kinds (`hilclaw/tools.py`)
- `KIND_NO_BACKEND = "no_backend"` and `KIND_NOT_OFFERED = "not_offered"`, each with a one-line `#:` comment of its meaning (ADR-0016 decision 3, the table), both members of `RESERVED_KINDS`, which then holds seven.
- The comment "The reserved kinds (ADR-0015 decision 2)" names ADR-0016 decision 3 as well; it stays one line.
- `default_registry`, `call`, `Registry` and every docstring are unchanged. `tools.py` does not import the new module.

### The module (`hilclaw/backends.py`)
Recommended shape (the names are yours to choose):
- `HW_TOOLS`: the four names `sim.run`, `board.run`, `profiler.collect`, `correctness.check` (cited: FR-10; ADR-0016 decision 1).
- **A backend**: an immutable value of a name and its operations, built by one constructor or function, for example `Backend(name, operations)` with `operations` a mapping from a HW tool name to a callable.
  - `name` must be a *name* in the sense of ADR-0001 (`[a-z][a-z0-9_]{0,31}`, exactly a `str`) — it is an `accelerator` value. The package keeps this pattern module-private in each module that needs it (`keys`, `journal`, `events`, `artifacts`); follow that convention and do not edit `hilclaw/keys.py`.
  - An empty `operations` is valid ("the frame requires none").
  - Refused when it is **built**, with `TypeError` or `ValueError` (a defect of the author of a backend, not a tool failure): a name that is no name; `operations` that is no mapping; an operation that is not callable; a member name that is none of `HW_TOOLS` (ADR-0016 defines an operation for a HW tool only — see the choices below).
  - The backend keeps its own copy of the mapping; a later change of the mapping handed in changes nothing, and the value offers no way to add or replace an operation.
- **The backend table**: an immutable value built from backends in one step, for example `BackendTable(backends)` with an iterable of backends.
  - A name given twice is refused when the table is built (`ValueError`): "a name has one backend". An entry that is no backend is refused (`TypeError`). An empty table is valid.
  - Nothing adds to a table after it is built: no `register` method, no option, no environment variable, no entry point (ADR-0016 decision 2; #5 A-12).
  - It can be asked for its names (sorted) — the conformance tests of a later slice run over them.
- **The selection**: one public function, for example `select(table, hw_profile, tool)`, which returns the operation of `tool` of the backend of the call. In this order:
  1. `tool` that is none of `HW_TOOLS`, or `table` that is no backend table: `ValueError` / `TypeError` — a defect of the tool's author, not a tool failure.
  2. `hw_profile` is validated with `hilclaw.keys.hw_profile_key`. **Its `InvalidRecordError` passes through unchanged**: the module catches it nowhere, maps it to no kind and adds no kind or constant for it (ADR-0016 decision 4, last but one bullet; sub-question ④ of ADR-0015). In particular it is **not** `no_backend`.
  3. The table has no entry under `hw_profile["accelerator"]` → `ToolFailure(tools.KIND_NO_BACKEND, …)`; the message names the `accelerator`.
  4. The entry has no operation for `tool` → `ToolFailure(tools.KIND_NOT_OFFERED, …)`; the message names the backend and the tool.
  5. Otherwise the operation is returned — the very object the backend was built with. **The selection calls no operation.**
  - Only `accelerator` selects: two valid records that differ in `revision`, `toolchain`, `host`, `ext`, `hw_source` or `label` select the same operation (ADR-0016 decision 4; ADR-0001 decision 5).
  - The record is not modified and not kept.
- **Nothing is kept and nothing is read**: the module holds no table, no default table and no backend at module level; it reads no file, no configuration and no environment variable, uses no clock and no random source, and imports from `hilclaw` only `keys` and `tools`. Whoever builds a registry builds the table and hands it to the tool functions (slice ③); that is not done here.
- The module defines **no backend**: neither the mock nor `cpu_standin`, no reserved mock name, no script. It defines no order of a call (decision 2's ①-⑦ is slice ③) and does not touch the journaled path.

### Docstrings (CLAUDE.md "코멘트 최소화": no multi-line comments; docstrings of the public API may be as long as needed)
- A module docstring naming ADR-0016 decisions 2 to 4 and saying in few sentences: what a backend, an operation and the backend table are; that nobody names a backend and only `accelerator` selects; the two kinds and that a failed selection has called nothing; what passes through (an invalid record, with OD-18 sub-question ④ named as open); and the limits it does not remove (ADR-0016 decision 6: the target reached is not checked against the key; a backend that does not answer the contract is not detected; two processes hold two tables). **Sweep every unconditional sentence against sub-questions ⑥ to ⑧ before the first review** (T-0056 process note): the docstring must not say where the record of a call comes from, what an operation is called with beyond what decision 2 states, or anything of the mock.
- Each public name gets a docstring with its parameters and what it raises.

### Cases the record leaves to this task — choose, implement, test and list each with one line of reason
- The names of the public objects, positional or keyword-only parameters, and whether a backend and a table are classes, named tuples or frozen dataclasses.
- An operation under a name that is none of the four HW tools. Recommended: refused when the backend is built — the record defines an operation for a HW tool only, and a test registers its test-only tool function under one of the four names in a registry of its own, as `tests/test_tools.py` does with `sim.run`. If you read this as closing a door slice ③ needs, say so and choose the other way; accepting and silently ignoring such a member is **not** acceptable.
- What the selection returns: the operation alone (recommended) or the backend with it.
- Whether the record is validated in full (recommended, as above: a record that is no valid record never selects a backend) or only its `accelerator` is read. If you read "validated in full" as more than decision 4 carries, return BLOCKED with the question instead of choosing the weaker form silently.
- Equality and hashing of the two values; what `repr` shows.
- Anything else you meet. If you read one as a rule of a tool's contract, of the mock, of how a backend is reached (#5 B-2), of recovery (OD-10) or of sub-questions ④, ⑥, ⑦ or ⑧ that no record states, do not decide it: return BLOCKED with the exact question.

### Tests (excluded from the size cap)
Helpers live in the test file and get no tests of their own (test rule ⑤). Synthetic values only: placeholder `accelerator` names (for example `acc_a`, `acc_b`) in records the tests write themselves, valid under `keys.hw_profile_key`; **no value of a real hw_profile record and no reserved mock name is invented**. No test reads or writes the real data repository; this module needs no data directory at all. The tests pass on Linux (CI) and on Windows (the driver's clone).

`tests/test_backends.py` (new):
- happy: a backend with one, several and all four operations; a backend with none; a table of none, one and several backends and its sorted names; the selection returns the very operation object for each offered tool; two tables built in one process stay apart.
- branch — only `accelerator` selects: records that differ in `revision`, in a `toolchain` member, in a `host` member, in `ext`, in `hw_source`, in `label` select the same operation; two records that differ in `accelerator` select the operations of two backends.
- branch — the order: an invalid record with an `accelerator` the table lacks raises `InvalidRecordError`, not `no_backend`; a valid record with an unknown `accelerator` and a tool no backend offers is `no_backend`, not `not_offered`.
- error / negative — `no_backend`: an empty table; a table without the entry; a name that differs in one character. The failure is a `ToolFailure` whose `kind` is `tools.KIND_NO_BACKEND` and whose message names the `accelerator`. **No operation of any backend was called** (counting operations stay at 0).
- error / negative — `not_offered`: a backend built without the operation of the called tool, a backend with no operation at all; kind `tools.KIND_NOT_OFFERED`, the message names the backend and the tool; no operation was called; the other tools of the same backend are still selected.
- error / negative — a record that is no valid record: not a mapping, `accelerator` missing, `accelerator` that is no name (upper case, empty, an `int`, 33 characters), an unknown field, a missing `hw_source`, a wrong `schema_version`. Called directly, the selection raises `hilclaw.keys.InvalidRecordError` unchanged (same type, not a `ToolFailure`), also when the table holds an entry of that spelling; no operation is called.
- error / negative — building: a backend name that is no name (the cases above, a `str` subclass); `operations` that is no mapping; an operation that is not callable; a member name outside `HW_TOOLS`, as you chose; a table with a name twice; a table entry that is no backend; a selection with a tool outside `HW_TOOLS` or with something that is no table. Each raises when built or called, and building calls no operation.
- negative — immutability and no kept state: changing the mapping a backend was built from, or the list a table was built from, changes neither; no public way adds an entry; the selection with the same arguments twice gives the same answer and the record handed in is unchanged (compare with a deep copy).
- through `tools.call` and both fronts (in memory, as `tests/test_data_root_source.py` does it): a test-only tool function, registered under one of the four names in a registry of the test, selects with a table and a record the test holds and calls the operation. One request gives the **same outcome through `tools.call`, `hilclaw.__main__.main` and `hilclaw.mcp_front.main`**: the result of the operation; `no_backend` and `not_offered` as the error object `{"error": {"kind": …, "message": …}}` with exit status 3 on the command line and as a text block with `isError` true from the MCP front; for an invalid record a tool failure that is **equal through both fronts** and whose kind is none of `no_backend`, `not_offered`, `invalid_request` (**the kind is not pinned** — sub-question ④).

`tests/test_tools.py` (edited): `test_the_reserved_kinds_are_the_five_of_the_record` asserts the two new constants and the set of seven; rename it to match. This is the one existing test whose expectation changes — name it with the reason in the PR body. The two tests parametrized over `RESERVED_KINDS` take the new kinds without an edit. No assertion is weakened.

Test rules of CLAUDE.md / DRIVER §5 (D12): ① `hilclaw/` keeps line and function coverage ≥ 80 % — coverage is not measured by CI yet (P0.5-3 BLOCKED on HQ-0003; **install nothing**), so check that the tests reach every line of the new module, for example with `python -m trace --count --missing --coverdir <directory outside the repository> --module pytest tests/test_backends.py`, and say how in `## Result`; ② happy, error, branch and negative cases as above; ③ every public name of the new module gets a test; ④ the new module has its test file; ⑤ no tests for test code, CI workflows or helper scripts.

### Verification (record summary lines and run URLs in `## Result`)
- Local, before the commit and before the merge, from the repository root: `python -m pytest` exits 0 (record pass and skip counts before and after; 5393 passed and 147 skipped on `c745e08` on the driver's Windows clone, and T-0056 changed no code), `python -m ruff check .` and `python -m ruff format --check .` exit 0.
- `git grep -n -i "backend" -- hilclaw/` shows matches in `hilclaw/backends.py` and the two new lines of `hilclaw/tools.py` only; `git grep -n -E "environ|import config|open\(|import (time|random)" -- hilclaw/backends.py` has no match; `git grep -n -i -E "mock|cpu_standin" -- hilclaw/backends.py` has no match; `git diff origin/main -- hilclaw/tools.py` shows only the kinds and the comment; `git ls-files --eol` shows `i/lf` for the new and changed files; `git status --short` after the tests shows no stray file; `git diff origin/main --stat` lists only the four files of `touchesFiles`. Record the line counts of the two modules after the change.
- CI on the PR: `gh pr checks <PR> --watch` ends with **five** successful checks on the final head — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)`. Merge only then.
- After the squash-merge, check the `push` run on `main` (`gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"`) and record its conclusion; if it is not `success`, do not fix forward on `main`: record it and say so in the returned summary.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0057'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0057 --state all`; then `gh pr list --repo myungjoo/HIL-Claw --state open` (none at planning time; a PR touching a file of `touchesFiles` is BLOCKED "open PR conflict").
- Code mode: branch `claude/T-0057-backend-table-selection` from `origin/main`; Draft PR with the `DONOTMERGE` label; PR title contains `T-0057`; executor commits end with the trailer `Task: T-0057`.
- Install nothing. After a failed CI run, read the whole failed log (`gh run view <id> --log-failed`) and fix every diagnostic before pushing again. Three consecutive failed CI runs on the PR: stop and return BLOCKED ("CI 3 consecutive failures") with the last log excerpt in `## Result`.
- Reviewer cycle via a fresh-context `dev-reviewer` sub-agent running dev-code-review (at most 7 rounds; if the cap is passed without a final Approve, return BLOCKED). Ask the reviewer explicitly to (a) compare the code and the docstrings with ADR-0016 decisions 2, 3 and 4 sentence by sentence — the name of a backend is an `accelerator` value, one operation per offered HW tool, none required, one backend per name, the table closed after it is built, only `accelerator` selects, the two kinds with exactly their meanings, a failed selection calls nothing; (b) confirm that an invalid record is not `no_backend`, that the code decides, reserves or uses no kind for it, and that no test pins one (sub-question ④); (c) confirm that nothing is kept or read (no module-level table, no file, configuration, environment, clock or random source), that no backend, mock name, script or order of a call is defined, and that `tools.py` changed in the kinds and the comment only; (d) re-check the planner's judgements in `## Why` and each choice under "Cases the record leaves to this task" — the refused operation name and the full validation of the record in particular; (e) re-check the A-13 readings; (f) report any docstring sentence that says more than ADR-0016 carries, against sub-questions ⑥ to ⑧ and its Boundaries. If the reviewer reads a point as a design choice needing a record or the owner, return BLOCKED with the question; do not write an ADR inside this task. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Squash-merge per CLAUDE.md A-13 once the reviewer approved and CI is green: remove `DONOTMERGE`, mark the PR ready, confirm the five checks on the final head, then `gh pr merge <PR> --squash --body-file <file outside the repository>` with the PR body, whose **last line is `Task: T-0057`**. Delete the remote branch and the local branch in **separate** commands and only after `gh pr view <PR> --json state` reports `MERGED`.
- Commit body: what changed in one paragraph, the provisional choices with one line of reason each, and the language line.
- `## Result`: fill it in **after** the merge, on `main`, and leave that edit **uncommitted** — the driver commits it (DRIVER §3-6). The branch and the PR must not contain this task file. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. Record: PR and commit, review rounds and findings, the public API as landed (names and signatures — slices ② and ③ are written against it), the provisional choices, the verification outcomes, the line counts, the language line, and that this task ticks **no** PLAN checkbox.
- Size: about 140 non-test lines in 2 files; the cap is 300 LOC / 5 files (tests excluded). If the change cannot be made without touching another `hilclaw/` file, do not widen the task: return BLOCKED with the reason, or finish what fits and propose the split in `## Follow-ups` (DRIVER §5).
- If ADR-0016 turns out to be ambiguous or self-contradictory on a point the code must decide and that is not one of the choices above, do not guess and do not edit a record: return BLOCKED ("requirement unclear") with the exact question.
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, PR / commit, BLOCKED or not).

## Out of Scope
- The mock backend, its reserved name, its scripts and the default script (slice ②; ADR-0016 decision 5; sub-question ⑧). The `cpu_standin` backend and which tools it offers (sub-question ⑦).
- The path of a HW tool over a backend: the order of a call, the place between the lookup and the start line of `hilclaw.journaled_step.run`, the reader of the hw_profile of a run, `run_id` in the request of a HW tool (slice ③; sub-question ⑥). Any change to `hilclaw/journaled_tool.py` or `hilclaw/journaled_step.py`.
- Any tool of the package, its description, schema, `step` value or result members; a non-empty `default_registry` or a change of its parameters; a table built in `default_registry`; any change to a front.
- A kind for a hw_profile that cannot be read or is no valid record, or for any unusable run (OD-18 sub-question ④); enforcement that only a HW tool raises the two kinds or that a backend answers the contract (ADR-0016 decision 6).
- How a backend is reached (#5 B-2, A-7 ③), the simulator (#5 B-3), board faults and recovery (OD-10), the onboarding registry and a table filled from it (OD-26), the blob pair (#5 B-2, A-3).
- Any change to `hilclaw/keys.py` or `hilclaw/key_records.py`; any member of a data-plane file or of `hilclaw.config.json`.
- Any edit of an ADR (the sentences ADR-0016 lists as "now less exact" are the integrator's, after the objection window), the OD register, OpenDecisionProposals, StandardScenarios, CLAUDE.md, DRIVER.md, PLAN.md, `pyproject.toml`, `.github/`, `.claude/`, `README.md`; any change to the `HIL-Claw-data` repository.
- Answering HQ-0003 or HQ-0004 on the owner's behalf.

## Follow-ups
- (planner, next — code mode, P1-1) Slice ② of ADR-0016: the mock backend and its scripts over the table of this task (the reserved name's spelling is that code task's; the default script has nothing to answer until a tool has a contract — judge then what the default registry holds and whether ② and ③ are one task or two).
- (planner — code mode, P1-1) Slice ③: the path of a HW tool over a backend, checked through both fronts by a test-only tool with the mock; it takes the reader of the hw_profile of a run as a parameter until sub-question ⑥ is answered.
- (planner — doc mode, small §9 record) OD-18 sub-question ④: the kind of a call about a run that cannot be used; this task adds `hilclaw.keys.InvalidRecordError` to the exceptions T-0055 `## Result` lists. To judge then: whether it can be closed apart from OD-10.
- (unchanged) Sub-questions ⑥ (with the `instance.json` record, P1-8), ⑦ (with the first HW tool contract; an HQ if it needs the owner's reading of #5 A-7) and ⑧; the integrator items after 2026-10-15 (T-0056 Follow-ups); the rest of P1-8; the T-0053, T-0054 and T-0055 follow-ups.

## Result
**DONE.** PR #49 (https://github.com/myungjoo/HIL-Claw/pull/49), squash commit `3bc6821` on `main`. Branch commits `efeb007` (the change) and `e604d5e` (review round 1). This task ticks **no** PLAN checkbox: P1-1 stays open.

### What landed
- `hilclaw/backends.py` (new, 169 lines): `HW_TOOLS`, `Backend`, `BackendTable`, `select`. It imports `keys` and `tools` from `hilclaw` and nothing else of the package.
- `hilclaw/tools.py` (284 lines, was 280): `KIND_NO_BACKEND = "no_backend"`, `KIND_NOT_OFFERED = "not_offered"`, both in `RESERVED_KINDS` (seven), and the comment above the kinds names ADR-0016 decision 3. `default_registry`, `call`, `Registry` and every docstring are unchanged; `tools.py` does not import the new module.
- `tests/test_backends.py` (new, 644 lines, 141 tests); `tests/test_tools.py`: `test_the_reserved_kinds_are_the_five_of_the_record` became `test_the_reserved_kinds_are_the_seven_of_the_records` (the one existing test whose expectation changed; nothing weakened).
- No backend, no mock name, no script, no tool, no order of a call; nothing read or kept. `InvalidRecordError` of an invalid record passes through `select` unchanged and gets no kind (sub-question ④ stays open).

### Public API as landed (slices ② and ③ are written against it)
- `backends.HW_TOOLS == ("sim.run", "board.run", "profiler.collect", "correctness.check")` (a tuple).
- `backends.Backend(name, operations)` — `name`: exactly a `str` matching `[a-z][a-z0-9_]{0,31}`; `operations`: a mapping from a member of `HW_TOOLS` to a callable, may be empty, copied. `TypeError`: `name` or a member name no `str`, `operations` no mapping, an operation not callable. `ValueError`: `name` no name, a member name outside `HW_TOOLS`. Read-only property `name`; method `offered()` returns the offered tool names as a sorted tuple. No other public attribute (`__slots__`).
- `backends.BackendTable(backends)` — any iterable of `Backend`, may be empty. `TypeError`: not iterable, an entry no `Backend`. `ValueError`: a name twice. Method `names()` returns a sorted tuple. No `register`, no public lookup of a backend.
- `backends.select(table, hw_profile, tool)` returns the operation object the backend was built with and calls nothing. In this order: `TypeError` (`table` no `BackendTable`; `tool` no `str`), `ValueError` (`tool` outside `HW_TOOLS`), `hilclaw.keys.InvalidRecordError` unchanged (the record is validated in full by `keys.hw_profile_key`), `ToolFailure(tools.KIND_NO_BACKEND, "the backend table has no entry for the accelerator <accelerator>")`, `ToolFailure(tools.KIND_NOT_OFFERED, "the backend <name> offers no operation for <tool>")`.
- **What an operation is called with is not fixed here**: `select` only returns it. The tests call it with the request alone; slice ③ decides the call (ADR-0016 decision 2: the request and the hw_profile of the call).

### Provisional choices (the records leave them to the code task)
- Names `HW_TOOLS`, `Backend`, `BackendTable`, `select`; positional parameters: each takes two or three values of different kinds, so none is easy to swap silently.
- `Backend` and `BackendTable` are plain classes with `__slots__` and no setter, not named tuples or dataclasses: both must check and copy what they are handed, and a tuple would expose the held mapping.
- A backend shows its `name` and `offered()`; an operation is obtained through `select` only, so there is one way to an operation and it always passes the record check.
- An operation under a name that is none of the four HW tools is refused when the backend is built: ADR-0016 defines an operation for a HW tool only; a test-only tool function is registered under one of the four names in a registry of its own. Not read as closing a door slice ③ needs.
- A backend name and a HW tool name are exactly a `str` (a subclass is refused, as `hilclaw.keys` does for a name): what is no `str` is `TypeError`, a `str` that is no name or no HW tool is `ValueError`, as `ToolFailure` does for a kind. A wrong type therefore stays apart from `InvalidRecordError`, which is a `ValueError` (changed in review round 1; it was `ValueError` for every case of a tool name).
- A table files a backend under the name it was built with, not under a `name` property a subclass may redefine (review round 1).
- `BackendTable` takes any iterable and `names()` returns a sorted tuple, as `Registry.names()` does. The table has no public lookup of a backend: nothing needs one yet (a conformance test builds the backends itself; slice ② or ③ may add one).
- `select` returns the operation alone: the caller of slice ③ needs nothing else, and the backend is named in the message of `not_offered`.
- The record is validated in full before anything is looked up: a record that is no valid record never selects a backend (decision 4), also when the table holds an entry of that spelling. Not read as more than decision 4 carries; the reviewer agreed.
- In `select`, the table and the tool are checked before the record: they are defects of the tool's author and the same for every record.
- Equality and hashing are by identity: an operation is a callable and compares by identity anyway. `repr`: `Backend('acc_a', offered=('sim.run',))`, `BackendTable(('acc_a', 'acc_b'))`.
- The wording of the messages is not fixed by a record; they name the `accelerator`, or the backend and the tool.
- The module's docstring writes "variable of the front process" where the task says "environment variable", so that the verification grep for `environ` has no match.

### Review (dev-reviewer, fresh context, 2 rounds, final Approve; no SECURITY, no point needing a record or the owner)
- Round 1 (head `efeb007`): Approve with one Low and three Nits — https://github.com/myungjoo/HIL-Claw/pull/49#issuecomment-6052204689. Low: the table took its key from the public `name` property, which a subclass can redefine (fixed: it reads the held value; regression test added). Nit: `hw_profile["accelerator"]` is read a second time after the validation (not changed: `keys.hw_profile_key` returns the key and not the validated fields, and `hilclaw/keys.py` is out of scope; it holds for any mapping whose reads are stable). Nit: exception class of a tool name of another type (changed to `TypeError`). Nit: size above the estimate. Response: https://github.com/myungjoo/HIL-Claw/pull/49#issuecomment-6052228241.
- Round 2 (head `e604d5e`): Approve — https://github.com/myungjoo/HIL-Claw/pull/49#issuecomment-6052259813. Low: the PR body still described `efeb007` (updated before the merge: the two choices of round 1 and the count 5538; no code change, so no further round). Nits: the subclass regression test pins undocumented behaviour (accepted by the reviewer); the grep wording below.
- The reviewer confirmed points (a) to (f) of the task, the planner's judgements and the A-13 readings (no data-plane schema change, no new dependency, only the four files of `touchesFiles`).

### Verification
- Local (Windows, Python 3.14.4): `python -m pytest` — 5393 passed / 147 skipped before, **5538 passed / 147 skipped** on the final head and again on `main` at `3bc6821` (+141 in `tests/test_backends.py`, +4 from the two tests parametrized over `RESERVED_KINDS`). `python -m ruff check .` and `python -m ruff format --check .` exit 0.
- Test rule ①: coverage is not measured by CI yet and nothing was installed. `python -m trace --count --missing --coverdir <scratch directory outside the repository> --module pytest tests/test_backends.py` leaves **no line** of `hilclaw/backends.py` marked as missing (0 lines `>>>>>>`), on both heads. Rules ② to ⑤ hold: negative cases, every public name tested, the test file exists, helpers untested.
- Greps: `git grep -n -E "environ|import config|open\(|import (time|random)" -- hilclaw/backends.py` and `git grep -n -i -E "mock|cpu_standin" -- hilclaw/backends.py` have no match. `git grep -n -i "backend" -- hilclaw/` matches `hilclaw/backends.py` and **three** lines of `hilclaw/tools.py` (the two constants and the set member `KIND_NO_BACKEND`), not the two the task wrote — all three are the kinds. `git diff origin/main -- hilclaw/tools.py` showed only the kinds and the comment; `git ls-files --eol` gave `i/lf` for the four files; `git status --short` after the tests showed no stray file; the diff listed only the four files of `touchesFiles`.
- CI on the final head `e604d5e`: five checks passed — `Python gate (3.11)`, `Python gate (3.14)`, `sh gate (shellcheck)`, `C gate (clang)`, `Test presence (hilclaw)` — https://github.com/myungjoo/HIL-Claw/actions/runs/37727616470. No failed CI run on the PR.
- `push` run on `main` after the squash-merge (`3bc6821`): **success** — https://github.com/myungjoo/HIL-Claw/actions/runs/37727867384.
- The remote and the local branch are deleted (after `MERGED`).

### Size
- Non-test: 169 new lines in `hilclaw/backends.py` (estimate 120-130; the difference is docstrings and the `__repr__` of the two classes) and 6 changed lines in `hilclaw/tools.py` — about 175 lines in 2 files, inside the cap (300 LOC / 5 files).

### Language
- Python, because the modules it joins (`hilclaw/tools.py`, `hilclaw/keys.py`) are Python.

### Notes for the driver and the planner
- No new HQ. No criterion disagreed with a record; the only deviations from the task's wording are the three grep lines and the docstring wording noted above.
- Seen on #5 after the ADR-0016 notice: an owner comment answering HQ-0003 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6052108898). It is no objection to ADR-0016, ADR-0015 or ADR-0001 and changed nothing here; it is the driver's to sync (§3-2).
- The squash commit ends with the `Co-Authored-By` line followed by `Task: T-0057` as its last line; the first branch commit has a blank line between its `Task:` and `Co-Authored-By` lines, which does not affect `git log --grep='^Task: T-0057'`.
- Follow-ups are unchanged from `## Follow-ups`; one addition for slice ② or ③: decide whether the table needs a public lookup of a backend (for example for the conformance tests "over each backend that offers a tool").
