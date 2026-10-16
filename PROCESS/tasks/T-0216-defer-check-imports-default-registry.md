---
id: T-0216
title: Defer the NumPy-pulling imports of correctness.check until its first call, so building the default registry imports no NumPy (T-0215 follow-ups 1 and 2)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18, C-7]
dependsOn: [T-0215]
touchesFiles:
  - hilclaw/check_definition.py
  - hilclaw/tools.py
  - hilclaw/gemm_contract.py
  - tests/test_check_definition.py
  - tests/test___main__.py
  - tests/test_tools.py
estimatedSize: {loc: 60, files: 3}
hq: []
---
## Why

T-0215 (PR #143, squash `f40c317`) registered `correctness.check` in `hilclaw.tools.default_registry` (ADR-0070). Since then, **building** the default registry imports NumPy: `hilclaw/check_definition.py` imports `check_tool` (which imports `check_judging` → `hilclaw.harness.verification` → `numpy`) and `mock_check` (which imports `numpy` and the harness verification modules) at module level, and `tools.default_registry` imports `check_definition`. Both fronts (`hilclaw.mcp_front`, `hilclaw.__main__`) build the default registry before they look at the request.

On Windows (a runtime platform, C-7), a process started with file descriptor 2 closed dies while importing NumPy (exit `0xC0000409`) instead of answering. The test `tests/test___main__.py::test_a_process_started_without_standard_error_still_answers` (added by T-0038; it calls the unknown tool `sim.run` and expects exit status 4 with `unknown_tool`) was therefore marked a strict `xfail` on `win32` by T-0215 (its Result, follow-up 1). Every call through either front, including `blob.push`, `blob.fetch`, an unknown tool and `tools/list`, now pays the NumPy import, although only a call of `correctness.check` needs it.

The fix is a code matter, not a design decision: ADR-0070 decides **what** the tool is bound to (decisions 3 to 5), not **when** the modules are imported; its Consequences sentence "Building the default registry then imports NumPy through `hilclaw/mock_check.py`" is an observation (listed among "observations, not edited"), and the closed-standard-error behaviour is a T-0038 code choice, not an ADR rule (ADR-0010 only says standard error is free text). This task makes the registration bind the same parties, but import the modules that pull NumPy only when `correctness.check` is first called.

It also takes T-0215 follow-up 2: `hilclaw/gemm_contract.py`'s module docstring still says the module "is bound to no tool", while `covers` is now bound by the default registry (ADR-0070 decision 4).

**Why this item now.** No lock, no TODO or INTERRUPTED task, no open PR (checked at `4716ffd`). PLAN P1-1 stays open. T-0210 is BLOCKED (HQ-0021) and is about `sim.run` / `board.run`; this task does not touch them and must not read or depend on branch `claude/T-0210-od18-run-tools-operation-tool-failure`. The other open HQs (HQ-0013, 0014, 0016..0019) are runtime-acceptance items on DONE tasks and do not bear on this one.

## Required Reading

ARCHITECTURE lines are very long: read them with `sed -n '<a>,<b>p' <file> | fold -w 400`. Line numbers are those of `main` at `4716ffd`; the text wins.

- `PROCESS/DRIVER.md` §2 (code mode), **§3-5** (executor procedure, landed check, resume rule, the 2h30m limit), **§5** (task format, naming: branch `claude/T-0216-<slug>`, PR title with `T-0216`, PR body's last line `Task: T-0216`, `gh pr merge --squash --body`, size cap D4, D12 test rules), §8.
- `CLAUDE.md`: all rules, in particular the A-13 code-mode procedure and BLOCKED reasons, the D12 test rules, the language policy (record language and reason in the commit body), "코멘트 최소화", and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole; code-mode path).
- `PROCESS/tasks/T-0215-correctness-check-default-registry.md` (whole, above all Acceptance Criteria 2 to 6 and `## Result` follow-ups 1 and 2).
- `ARCHITECTURE/decisions/ADR-0070-od18-correctness-check-registration.md` decisions 3 to 5 (lines 31-72) and Consequences (lines 107-114).
- Code: `hilclaw/check_definition.py` (whole; `default_table` line 104, `definition` line 119, the module docstring); `hilclaw/tools.py` lines 99-208 (`ToolDefinition`, `Registry`, `default_registry` at line 182); `hilclaw/check_tool.py` lines 1-140 (`tool_function` and its argument checks); `hilclaw/mock_check.py` lines 1-80; `hilclaw/gemm_contract.py` lines 1-60; `hilclaw/__main__.py` lines 60-100 and `hilclaw/mcp_front.py` lines 190-230 (where each front builds the registry and handles a tool function's exceptions).
- Tests: `tests/test_check_definition.py` (whole; above all `test_the_module_imports_what_it_names_and_has_its_public_names_only` at line 152, the `parties` fixture at line 277, `test_building_the_default_registry_calls_no_party` at line 354); `tests/test___main__.py` lines 420-460 (the strict xfail); `tests/test_gemm_contract.py` lines 380-400 (the "bound only by `check_definition.py`" pin); `tests/test_tools.py` (tests of `default_registry`).

## Acceptance Criteria

1. **Language**: Python, as the rest of `hilclaw/`. Record it and the reason in one line of the commit body and in `## Result`.
2. **No NumPy at build** (happy): in a fresh interpreter, `from hilclaw import tools; tools.default_registry(lambda: None)` leaves `"numpy"`, `"hilclaw.check_tool"`, `"hilclaw.mock_check"` and `"hilclaw.harness.verification"` absent from `sys.modules`. The same holds after a `tools/list` through `hilclaw.mcp_front` and after a `blob.push` / `blob.fetch` call or an unknown-tool call through `hilclaw.__main__.main`. Test this in a subprocess (`sys.executable -c ...`), since the test session itself has NumPy loaded.
3. **Same binding at the first call** (happy/branch): the first call of `correctness.check` through a registry `default_registry` built imports what it needs and binds `check_tool.tool_function` to `default_table()`, `hilclaw.harness.seed_source.system` and `hilclaw.gemm_contract.covers`, exactly as ADR-0070 decisions 3 and 4 say; every T-0215 test of the tool through the default registry and both fronts (mock pass, `no_backend` for `cpu_standin` and `acc_b`, stored result on repeat, `op_signature_*`, `invalid_request`, the environment-variable test, the test-built registry) passes unchanged in what it asserts. The table is built **at most once per registry** (at the first call, then reused), so a registry still holds one table as before; a second registry builds its own. The executor chooses the mechanism (e.g. the `ToolDefinition`'s function is a small closure in `check_definition.py` that imports `check_tool` / `mock_check` inside a function on first use and caches the bound tool function), keeping it short and with no module-level mutable state.
4. **What building still does and does not do** (branch/negative): `default_registry` keeps one parameter and still raises `TypeError` for a non-callable source, **at build time**, registering nothing; `check_definition.definition(source)` still raises `TypeError` for a non-callable source at build time. Building calls neither the data-root source, `seed_source.system`, `gemm_contract.covers`, `mock_check.default_script` nor `default_table` (recorders). `tools/list` still lists `correctness_check` with `DESCRIPTION` and `input_schema()` (they must not need `check_tool` or `mock_check`). `check_definition.default_table()` stays public and returns the same table as before when called directly (it may then import `mock_check`).
5. **No new behaviour on failure**: if the deferred import or the binding raises at the first call, the exception goes to the front as any exception of a tool function does today; add no handling, no new `error.kind`, no message. A later call retries the binding (no half-built state is cached) — test it with a monkeypatched failing `default_table` that fails once.
6. **Windows closed-standard-error test**: remove the strict `xfail` of `test_a_process_started_without_standard_error_still_answers`; it passes on Windows locally and on Linux CI. A process that calls `correctness.check` itself with fd 2 closed on Windows still imports NumPy; that case is not in scope — state it in `## Result` as a remaining limit.
7. **Docstrings** (keep short, "코멘트 최소화"; module docstrings may stay as long as needed), each true of the code: `check_definition.py` (module docstring and `definition`: when `check_tool` / `mock_check` are imported and the table built; "building a definition calls neither ..." now also names `default_table`); `tools.default_registry` (one clause: building it imports no module of `correctness.check`'s operation and so no NumPy); `hilclaw/gemm_contract.py` (T-0215 follow-up 2: replace "is bound to no tool" with the truth — `covers` is bound by the default registry's `correctness.check`, ADR-0070 decision 4). No code change in `gemm_contract.py`, `check_tool.py` or `mock_check.py`.
8. **Tests** (D12 ②-④; tests are outside the size cap): update `test_the_module_imports_what_it_names_and_has_its_public_names_only` only as far as the new import placement requires, still pinning the truth (which names are imported at module level and which inside functions); keep `tests/test_gemm_contract.py`'s binder pin green (edit it only if the docstring change needs it, and then add the file to `touchesFiles` in `## Result`). Add the subprocess tests of criterion 2, the once-per-registry and retry-after-failure tests of criteria 3 and 5, and the build-time negative tests of criterion 4. Every public function of a touched module stays tested. Keep `touchesFiles` in sync in `## Result`.
9. `ruff check`, `ruff format --check` and the full `pytest` suite pass locally; the coverage gate of `hilclaw/` (line >= 80%, function >= 80%) holds; CI green on the PR.
10. **Size**: non-test change <= 300 LOC and <= 5 files (expected about 60 LOC in 3 files, mostly docstrings). If exceeded, propose a split in Follow-ups and finish the current scope only.
11. **No data-plane schema change and no new dependency**: no member of a result, a line of `events.ndjson`, `instance.json`, `STATE.json`, a spec, `build.json` or a result file is added, removed or changed; no request member, `error.kind`, `step` value or reserved kind is added; no new package. If the work seems to need any of these, or a change to what ADR-0070 binds, stop and return BLOCKED with the question.
12. **D16**: nothing in this task starts `claude` (any subcommand or flag), a compiler, a kernel or a container, or needs a board or an API key; subprocess tests run only `sys.executable`. Tell each reviewer to write no file and start no `claude` process.
13. **Code mode** (CLAUDE.md A-13): branch `claude/T-0216-defer-check-imports-default-registry` from `origin/main`; Draft PR whose title contains `T-0216` and whose body ends with the line `Task: T-0216`; fresh-context `dev-reviewer` cycle (dev-code-review), at most 7 rounds — past the cap without a final Approve the task is BLOCKED; a result starting with `SECURITY` is BLOCKED; if no reviewer can be spawned the task is BLOCKED (do not review your own work); CI green (3 consecutive CI failures is BLOCKED); then mark ready, `gh pr merge --squash --body <PR body>`, delete the branch. Fill `## Result` with the PR, the squash commit, review rounds, the language line, the final `touchesFiles` and any follow-ups.

### Process

- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0216'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0216 --state all`. Then `gh pr list --repo myungjoo/HIL-Claw --state open`: an open PR touching a file of `touchesFiles` makes the task BLOCKED ("open PR conflict").
- Read the comments on issue #5 after the ADR-0070 owner notice (the latest comment whose first line starts `### OD-18` and mentions `T-0214`), skipping the driver's own (ending `— posted by driver`). An owner objection to ADR-0070 makes the task BLOCKED ("requirement unclear"); quote it. An answer to an open HQ does not stop this task; name it in `## Result`.
- Prohibitions: never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; do not edit `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call means BLOCKED; do not work around it. If the branch push is rejected, rebase and retry once, then BLOCKED (`branch-contention`). Past 2h30m wall-clock, BLOCKED (`task-timeout`) with the state in `## Result`.
- Fill in `## Result` on `main` after the merge and leave it uncommitted for the driver (DRIVER §3-6). `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. Return a summary of at most 200 characters.

## Out of Scope

- Lazy NumPy imports inside `hilclaw/harness/verification.py`, `verification_arrays.py` or `mock_check.py` (the deferral is at the registration only); a `correctness.check` call with fd 2 closed on Windows.
- Any change to what `correctness.check` is bound to (ADR-0070 decisions 3 to 5), to `hilclaw/mcp_front.py`, `hilclaw/__main__.py`, `hilclaw/backends.py`, `hilclaw/check_tool.py`, `hilclaw/mock_check.py`, `hilclaw/mock_backend.py` or the frame's messages.
- `sim.run`, `board.run`, `profiler.collect` (T-0210, HQ-0021).
- Any `ARCHITECTURE/` edit, including ADR-0070's Consequences sentence on NumPy at build (now less exact; record it as a follow-up for the doc task that takes the ADR-0070 "less exact" list and the T-0214 round-7 nits).
- PLAN checkboxes (P1-1 stays open).

## Follow-ups

## Result
