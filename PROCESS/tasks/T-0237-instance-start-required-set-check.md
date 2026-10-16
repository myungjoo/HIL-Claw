---
id: T-0237
title: Add `hilclaw/instance_start.py`, the pure check of a composed `instance.json` document against the scope and required set of ADR-0076 that fills in the `n_max` default, with its test file; no change to `hilclaw/instance.py`, no writer, no bytes
phase: P1
status: DONE
commitMode: code
coversReq: [FR-13, FR-2, FR-9, FR-1, OD-8, "#5 D12"]
dependsOn: [T-0236]
touchesFiles: [hilclaw/instance_start.py, tests/test_instance_start.py]
estimatedSize: {loc: 120, files: 1}   # tests excluded from the cap (DRIVER §5, D4); the test file is expected to be longer
hq: []
---
## Why

ADR-0076 (landed as `be43ff0` by T-0236, accepted under DRIVER §9, owner window until 2026-10-23) settles, for first-case instances, which members the start of an instance requires before it writes `runs/<run_id>/instance.json`, that the start fills in the `n_max` default of ADR-0007 decision 8, and that a refusal writes nothing and reports every missing member in a fixed order. Its Consequences name the code slice this task is: "a pure check of an instance content against the required set of decision 2 and the scope of decision 1, with the filling-in of `n_max`, in a new `hilclaw/` module with its own test file, reusing `hilclaw.instance.parse` without changing `hilclaw/instance.py`. Names, forms and the report's shape are that task's. Binding it to a component that performs the start is not part of it (OD-23)." It advances PLAN P1-8 and ticks **no PLAN checkbox** (P1-8 keeps event kinds, `STATE.json` members and "what writes the run's files").

**Why this item now.** No lock, no TODO or INTERRUPTED task, no open PR (checked 2026-10-17 at `8c00bed`). T-0210 (HQ-0021), T-0225 (HQ-0022), T-0231 (HQ-0023) and T-0233 (HQ-0024) are BLOCKED; this task depends on none of them. It does not touch `hilclaw/instance.py` or `tests/test_instance.py`, which the BLOCKED T-0233 branch (`claude/T-0233-admit-injections-and-injected-origin`) edits, and it uses only `instance.validate`, which that branch extends (with `injections`) without changing what this task relies on. Do not read or depend on that branch.

**Planner's design choices (the reviewer is asked to re-check each against ADR-0076):**
- **A document, not bytes.** ADR-0076 decision 3 puts the check on "the content held before step 1 of ADR-0025" and has the start put the `n_max` default *into* the content. Filling a member into `bytes` would mean building JSON text, which `hilclaw/instance_file.py` explicitly does not do ("this module builds no bytes from a document"). So the check takes the composed **document** (a `dict`, the parsed form `instance.validate` accepts) and returns a new document; turning it into bytes and calling `instance_file.write` stays with whatever performs the start (OD-23). The ADR's "today `hilclaw.instance.parse`" is rendered by `hilclaw.instance.validate`, the document-level form of the same rules; state this in the module docstring.
- **Order.** ADR-0076 decision 3 lists: compose with `n_max` filled in, check validity, check the required set. R7 minor (c) of T-0236 (not yet applied to the ADR) notes that filling in `n_max` should happen only for a valid in-scope content; ADR-0076 decision 1 says an instance outside the scope has "nothing required of it here and nothing allowed". The module therefore checks validity first, then the scope, then fills in `n_max`, then the required set. For a valid document the outcome equals the ADR's order (adding a valid `n_max` neither makes an invalid document valid nor a valid one invalid); for an out-of-scope document nothing is filled in. Say so in the module docstring and list it in `## Result` as the one place the code reads the ADR's order.
- **The default value is cited, never restated**: import `N_MAX_DEFAULT` from `hilclaw.harness.measurement` (ADR-0076 decision 2: "the value is that of ADR-0007 decision 8, and where the code holds it is no architecture question"). No literal `10` in the module.
- **The scope names are imported**: `hilclaw.standin_profile.ACCELERATOR` and `hilclaw.mock_backend.NAME`; coverage is `hilclaw.gemm_contract.covers` (the ADR-0041 decision 5 predicate already used by `check_definition`). None of these imports pulls in NumPy (checked at planning time: importing all four with `instance` leaves `numpy` out of `sys.modules`); keep it so.

## Required Reading

Line numbers are those of `main` at `8c00bed`; the text wins. Read Korean files and Python with `PYTHONIOENCODING=utf-8` (the console code page is cp949).

- **PROCESS/DRIVER.md §3-5** (executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (task format, naming, size cap D4, trailers, the test rules D12).
- CLAUDE.md, the whole file; above all "테스트 규칙", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "개발 드라이버와 런타임의 구분", "코멘트 최소화".
- .claude/skills/dev-item-address/SKILL.md (code mode, all steps); .claude/skills/dev-code-review/SKILL.md.
- **ARCHITECTURE/decisions/ADR-0076-od8-instance-start-required-members.md, the whole record** (109 lines): decision 1 (line 26-28, scope), decision 2 (lines 30-48, the required set, the `n_max` filling, "A value the user gives is never replaced"), decision 3 (lines 50-56, order, refusal writes nothing, every missing member in the fixed order `op_signature`, `objective`, `candidates_per_round`, `draws`, `tolerance`), decision 4 (58-61, the tools' per-call answers stay), Walk-through (67-75), Consequences line 92, Boundaries (96-103).
- ARCHITECTURE/decisions/ADR-0007-od13-measurement-policy.md decision 8 (lines 72-90); ADR-0023-od8-instance-record-n-max.md decisions 3-4 (the `n_max` validity: an `int` from 5 up); ADR-0025-od8-instance-file-write.md decision 2 (what the write fills in: nothing); ADR-0041-od18-correctness-check-dimensions.md decision 5 (coverage).
- `hilclaw/instance.py` lines 560-847 (`_DEFINED`, the exceptions, `Instance`, `parse`, `validate`) - read only, **not edited**.
- `hilclaw/instance_file.py` lines 1-140 (the writer's conventions; why it takes bytes) - read only.
- `hilclaw/gemm_contract.py` `covers` (line 106 on); `hilclaw/standin_profile.py` line 81 (`ACCELERATOR`); `hilclaw/mock_backend.py` line 35 (`NAME`); `hilclaw/harness/measurement.py` line 47 (`N_MAX_DEFAULT`).
- `hilclaw/check_admission.py` (whole, 190 lines): the house style of a small pure module over `Instance` - module docstring sections "Choices that are this module's own" and "What the module does not do", exact-type checks, messages built at import, `NamedTuple` results.
- `tests/test_instance.py` lines 1-300 and `tests/test_check_admission.py`: how valid hw_profile and op_signature records and contents are built in tests (reuse the patterns; do not import from other test files unless the suite already does so).

## Acceptance Criteria

### The module `hilclaw/instance_start.py` (Python; record the language reason in the commit body)

1. **Public names** (final names are the executor's if the reviewer agrees; keep the shape):
   - `REPORT_ORDER`: the tuple `("op_signature", "objective", "candidates_per_round", "draws", "tolerance")` (ADR-0076 decision 3).
   - `OutOfScopeError(Exception)`: the document is valid but outside ADR-0076 decision 1; the message names why (the accelerator, or the stated op_signature not covered). It is no `ValueError`, so it is not taken for an invalid document.
   - `MissingMembersError(Exception)`: the refusal of decision 3; attribute `missing`, a `tuple` of member names in `REPORT_ORDER` order, never empty; the message lists them in that order and shows no value of the document.
   - `prepare(document)`: returns the document the start may hand to the writer.
2. **`prepare(document)` behaviour, in this order**:
   1. `TypeError` when `type(document) is not dict`.
   2. `hilclaw.instance.validate(document)`; what it raises (`InvalidInstanceError`, `UnsupportedVersionError`) passes through unchanged. A given `n_max` that breaks ADR-0023 (e.g. `4`, `True`, `10.0`) is therefore refused as invalid and **never replaced** by the default (ADR-0076 decision 2).
   3. Scope (decision 1): `hw_profile.record.accelerator` is `standin_profile.ACCELERATOR` or `mock_backend.NAME`, **and** `op_signature` is absent or `gemm_contract.covers(op_signature.record)` is `True`. Otherwise `OutOfScopeError`; nothing is filled in.
   4. If `n_max` is absent, a new top-level `dict` equal to the input plus `"n_max": N_MAX_DEFAULT` is built; otherwise a new top-level `dict` equal to the input. The input is never modified (nested values may be shared; say which in the docstring). No other member is added, removed or changed; members not defined by `instance.py` are kept as given.
   5. If any member of `REPORT_ORDER` is absent from that dict, `MissingMembersError` with **every** absent one, in `REPORT_ORDER` order.
   6. Otherwise return the dict. The returned dict passes `instance.validate`.
3. **Not done by the module** (say so in the docstring, briefly): it writes, reads and builds no bytes and no file; it names no component of the start and takes values from no user (OD-23, UC-1); it does not check `source_commit`, budgets, `owner`, `project`, `injections`, the N range or initial caps, or whether the stated objective is covered (ADR-0076 Boundaries, ADR-0061 decision 4); it does not change or stand in for any tool's per-call answer (decision 4); it does not raise `hilclaw.tools.ToolFailure`. It imports no NumPy, directly or transitively.
4. Comment and docstring style per CLAUDE.md "코멘트 최소화": a module docstring and docstrings of the public names (external API) may be full; no inline multi-line comments.

### Tests `tests/test_instance_start.py` (D12: happy, error, branch and negative cases; every public name)

- Happy: a `cpu_standin` document and a mock document stating all six members (with `n_max` 12) are returned equal, as a new object, `n_max` 12 kept (Walk-through row 1); without `n_max` the result holds `n_max == measurement.N_MAX_DEFAULT` and the input still has no `n_max` (row 3); the result passes `instance.validate`; a member not defined by `instance.py` is kept.
- Refusal: each of the five members missing alone gives `missing == (that,)`; the Walk-through row 4 mock case (only `objective` and `tolerance` stated) gives `("op_signature", "candidates_per_round", "draws")`; all five missing gives `REPORT_ORDER`; the message lists the names in order. `n_max` is never in `missing`.
- Scope: another accelerator, and a `cpu_standin` document with a valid but uncovered op_signature (e.g. `fp16`, or a dimension 0), raise `OutOfScopeError` — also when members are missing and `n_max` is absent (nothing filled in, no `MissingMembersError` first) (Walk-through row 5); an absent op_signature with an in-scope accelerator is in scope (and then refused for `op_signature`).
- Negative / error: non-`dict` inputs (`None`, `bytes` of a valid content, a `list`, a `dict` subclass) give `TypeError`; an invalid document (e.g. a bad `hw_profile`, `n_max` 4, `n_max` `True`) gives `InvalidInstanceError` with no filling; `schema_version` 2 gives `UnsupportedVersionError`; the input is unmodified after every raise.
- `REPORT_ORDER` equals the ADR-0076 decision 3 order exactly.
- Do not edit any existing test file. Coverage of `hilclaw/` stays at or above 80 % line and 80 % function (CI gate); the new module is near 100 %.

### Checks (report in `## Result`)

- `python -m pytest`, `ruff check .` and `ruff format --check .` (the pinned versions of `pyproject.toml`) pass locally; CI green on the PR.
- `git diff --stat origin/main` shows only `touchesFiles`; non-test lines within 300.
- `python -I -c "import sys, hilclaw.instance_start; print('numpy' in sys.modules)"` prints `False`.

### Process

- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0237'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0237 --state all`. Then `gh pr list --repo myungjoo/HIL-Claw --state open`: an open PR that touches `hilclaw/instance_start.py`, `tests/test_instance_start.py` or ADR-0076 makes the task BLOCKED ("open PR conflict"); none was open at planning time.
- Read the comments on issue #5 after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6218483981, skipping the driver's own (ending `— posted by driver`). An owner objection to ADR-0076, or an owner comment on the instance start, `n_max`, `draws`, N, tolerance or the objective, makes the task BLOCKED ("requirement-unclear"); quote it. An answer to an open HQ (HQ-0013, HQ-0014, HQ-0016..HQ-0019, HQ-0021..HQ-0024) does not stop this task; name it in `## Result`.
- **Code mode** (CLAUDE.md A-13): branch `claude/T-0237-instance-start-required-set-check` from `origin/main`; Draft PR with `T-0237` in the title; reviewer cycle of dev-item-address with a fresh-context `dev-reviewer` each round, given the PR and this file's path; at most 7 rounds (past the cap without Approve: BLOCKED `review-rounds-exceeded`). Ask the reviewer to (a) re-check the planner's design choices in `## Why` against ADR-0076; (b) look for any constant restated (a literal 10, a default for `draws`, a range for N) or any check ADR-0076 leaves open (objective coverage, budgets, `source_commit`); (c) check that nothing in `hilclaw/instance.py` or an existing test changed. A result starting with `SECURITY` is BLOCKED. If no reviewer can be spawned, BLOCKED; do not review your own work. CI 3 consecutive failures: BLOCKED.
- **Merge**: after Approve and CI green, `gh pr ready`, then `gh pr merge --squash --delete-branch --body "<PR body>"` with the PR body's last line `Task: T-0237`. Commit and PR text in English; the commit body records the language choice in one line.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Nothing here needs a `claude`, a board or an API key. Tell each reviewer to write no file and start no `claude` process.
- **Prohibitions**: never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around. Past 2h30m of wall-clock time, return BLOCKED (`task-timeout`) with the state in `## Result`.
- **`## Result`**: fill it in on `main` after the merge and leave it uncommitted for the driver (DRIVER §3-6): PR and squash commit, review rounds and findings, the final public names, the order reading (validity, scope, fill, required set), the language reason, follow-ups. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters.

## Out of Scope

- Any edit of `hilclaw/instance.py`, `hilclaw/instance_file.py`, any other existing module or any existing test; any change to the members, validity rules or `schema_version` of `instance.json` or of any other data-plane file; any change to a tool's per-call answer (`check_admission`, `run_admission`).
- Serialising the document to bytes, calling `instance_file.write`, creating a run directory, a `run_id`, or a first `STATE.json` (⑩, ⑰, OD-23).
- Who performs the start and where its values come from (OD-23, UC-1); the N range and initial caps (owner, #5 A-9 / B-4); the objective menu and whether the stated objective is covered (#5 A-4, OD-1, ADR-0061 decision 4); budgets (㉙, ㉚, OD-19); `owner`/`project` (㉛); `source_commit` (⑳); `injections` (ADR-0075, T-0233 / HQ-0024).
- Any ADR or register edit, including the T-0236 R7 minors (b)-(d) and the UC-1 `draws` note (e).
- Registering the check as a tool, an MCP entry, a hook or a prompt.

## Follow-ups

- (planner, doc mode) T-0236 R7 minors (b)-(d) on ADR-0076 (register in the rest of ㉞ (가) whether the start checks that the stated objective is covered; decision 3 should say filling in `n_max` happens only for a valid in-scope content, as this task implements it; the O3 quote) and the UC-1 `draws` note (e), with the OD-8 register lines they touch.

## Result

- **Status: DONE.** PR https://github.com/myungjoo/HIL-Claw/pull/153, squash-merged as `722ec95` (branch `claude/T-0237-instance-start-required-set-check` deleted, local and remote). Landed check at start: no commit with `Task: T-0237`, no PR; no open PR; no comment on #5 after 6218483981, so no owner objection and no HQ answer to name.
- **Files**: `hilclaw/instance_start.py` (178 lines), `tests/test_instance_start.py` (524 lines); `git diff --stat` showed only these two. `hilclaw/instance.py`, all other modules and all existing tests are unchanged.
- **Final public names**: `REPORT_ORDER` (the ADR-0076 decision 3 tuple), `OutOfScopeError(Exception)` (no `ValueError`; its docstring says it is no refusal of the start, since what the start does then stays open), `MissingMembersError(Exception)` with `missing` (every absent member in `REPORT_ORDER` order), and `prepare(document, *, accelerators, covers)`.
- **Deviation from AC 2.3 / the planner's imports (reviewer-accepted in both rounds)**: importing `standin_profile.ACCELERATOR` and `gemm_contract.covers` breaks two existing tests, `tests/test_standin_profile.py::test_module_is_bound_nowhere_and_imports_no_store` (no other `hilclaw/*.py` may contain `standin_profile`; that module's docstring says it is "bound to no tool and to no start of an instance") and `tests/test_gemm_contract.py::test_module_is_bound_by_the_default_registry_only_and_imports_keys_only` (only `check_definition.py` may name `gemm_contract`). Editing them is out of scope, and writing the names out as literals would restate constants. So, following the `check_admission.admit(..., *, covers)` precedent, the caller passes `accelerators` (exactly a tuple of exactly `str`) and `covers` (callable; an answer that is not exactly `bool` raises `TypeError`) by name, with no default. The tests pass `(standin_profile.ACCELERATOR, mock_backend.NAME)` and `gemm_contract.covers`. The module imports only `hilclaw.instance` and `hilclaw.harness.measurement` and holds no integer literal (an AST test checks this).
- **Order reading (the one place the code reads ADR-0076's order)**: type checks, then `instance.validate` (errors pass through, and a given invalid `n_max` is never replaced), then the scope, then the `n_max` fill-in with `measurement.N_MAX_DEFAULT`, then the required set. For a valid document the outcome is the same as decision 3's order. An invalid or out-of-scope document gets nothing filled in. The check runs on a document, not on bytes, and uses `validate`, the document form of `parse`.
- **Review**: 2 rounds with a context-isolated `dev-reviewer` (opus), Approve in both. In round 1 the reviewer made 2 minor findings and 2 nits. Applied in `df11e3c`: the `OutOfScopeError` docstring now says it is no refusal of the start, the order note is reworded, and the public-name test checks the exact set. In round 2 the reviewer made only notes for this Result (the deviation above, and the `-I` check below), with no code change. Neither round reported a SECURITY finding.
- **Checks**:
  - Local: `python -m pytest` gave 22017 passed and 355 skipped. `ruff check .` and `ruff format --check .` (ruff 0.16.10) are clean.
  - Coverage: `hilclaw/instance_start.py` is at 100 % and `hilclaw/` at 99 %.
  - NumPy: `python -I -c "import sys; sys.path.insert(0, <repo>); import hilclaw.instance_start; print('numpy' in sys.modules)"` prints `False`. The literal `python -I -c` of the task cannot find `hilclaw`, because the package is not installed and `-I` leaves the cwd off `sys.path`. The test runs the same check without `-I`, with cwd at the repo root.
  - CI on `df11e3c`: all six checks green (Python 3.11/3.14, Coverage, C, sh, Test presence).
- **Language**: Python, because the check runs over `hilclaw.instance` documents in the existing Python package. This is recorded in the commit body.
- **Follow-ups**:
  - (a) Code, OD-23: whatever component performs the start must bind `accelerators=(standin_profile.ACCELERATOR, mock_backend.NAME)` and `covers=gemm_contract.covers`. Doing that inside `hilclaw/` means updating the two binding tests named above and the `standin_profile` docstring sentence "bound to ... no start of an instance".
  - (b) Doc mode: the T-0236 R7 minors (b) to (d) and the UC-1 `draws` note (e), unchanged from the task's Follow-ups. Note there that this task implements minor (c), filling in `n_max` only for a valid in-scope content.
