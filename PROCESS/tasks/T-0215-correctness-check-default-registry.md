---
id: T-0215
title: Register correctness.check in the default registry with the mock-only backend table, the OS seed source and the ADR-0041 predicate (ADR-0070)
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: [T-0212, T-0214]
touchesFiles:
  - hilclaw/tools.py
  - hilclaw/check_definition.py
  - hilclaw/check_tool.py
  - hilclaw/mock_check.py
  - hilclaw/mock_backend.py
  - tests/test_check_definition.py
  - tests/test_blob_tools.py
  - tests/test_mcp_front.py
  - tests/test___main__.py
  - tests/test_tools.py
  - tests/test_check_tool.py
estimatedSize: {loc: 90, files: 5}
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts + mock backend + conformance tests) is open. ADR-0070 (landed by T-0214 as `3c78714`) decides that `correctness.check` is registered **now** in the registry `hilclaw.tools.default_registry` builds, and fixes what its tool function is bound to:

- decision 3: a default backend table with **exactly one entry, the mock backend under its reserved name** (`hilclaw.mock_backend.NAME`), offering **exactly `correctness.check`**, whose operation is the mock's operation of this tool (`hilclaw.mock_check.operation`) bound to the default script of ADR-0044 (`hilclaw.mock_check.default_script`); no `cpu_standin` entry, so a call about a `cpu_standin` run (or any other accelerator) is `no_backend`; no operation of `sim.run`, `board.run` or `profiler.collect`;
- decision 4: the source of seeds is the OS generator (`hilclaw.harness.seed_source.system`), the predicate "covered" is ADR-0041 decision 5 (`hilclaw.gemm_contract.covers`); both fixed in the source, no request, option or environment variable chooses them;
- decision 5: the definition is the name `correctness.check`, that tool function bound to the data-root source `default_registry` is given, the input schema and `DESCRIPTION` of `hilclaw/check_definition.py`; both fronts then list three tools; `default_registry` keeps its one parameter.

ADR-0070 Consequences names this code slice and estimates it at about 30 to 60 non-test lines in at most five files, with no split. Everything the tool function needs exists on `main` (`hilclaw/check_tool.py` `tool_function(*, source, table, seeds, covers)`, T-0212's `check_definition`); today `default_registry` registers only `blob.fetch` and `blob.push`, and `tests/test_check_definition.py::test_the_default_registry_holds_no_definition_of_the_tool` asserts the tool is absent.

ADR-0070 decision 3 observes one obstacle: `hilclaw.mock_backend.backend` builds operations called with two arguments, while `hilclaw.check_operation.ask` calls an operation with four, so the default table cannot be built with `mock_backend.backend` for this tool. Build the entry directly as `hilclaw.backends.Backend(mock_backend.NAME, {"correctness.check": mock_check.operation(mock_check.default_script)})` (or an equivalent the executor documents); ADR-0044 decision 2 leaves this to the code.

**Why this item now.** No lock, no TODO or INTERRUPTED task, no open PR (checked at `d5d6878`). T-0210 is BLOCKED (HQ-0021) and is about `sim.run` / `board.run`; this task does not touch them and must not read or depend on branch `claude/T-0210-od18-run-tools-operation-tool-failure`. The other open HQs (HQ-0013, 0014, 0016..0019) are runtime-acceptance items on DONE tasks and do not bear on this one.

## Required Reading

ARCHITECTURE lines are very long: read them with `sed -n '<a>,<b>p' <file> | fold -w 400`. Line numbers are those of `main` at `d5d6878`; the text wins.

- `PROCESS/DRIVER.md` §2 (code mode), **§3-5** (executor procedure, landed check, resume rule, the 2h30m limit), **§5** (task format, naming: branch `claude/T-0215-<slug>`, PR title with `T-0215`, PR body's last line `Task: T-0215`, `gh pr merge --squash --body`, size cap D4, D12 test rules), §8.
- `CLAUDE.md`: all rules, in particular the A-13 code-mode procedure and BLOCKED reasons, the D12 test rules, the language policy (record the language and reason in the commit body), "코멘트 최소화", and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole; code-mode path).
- `ARCHITECTURE/decisions/ADR-0070-od18-correctness-check-registration.md` (whole, 132 lines; above all decisions 2 to 5 at lines 31-72, the Walk-through at lines 74-85, Limits at lines 87-93 and Consequences at lines 107-114).
- `ARCHITECTURE/decisions/ADR-0016-od18-backend-frame.md` decisions 2 to 5 (lines 30-75): the moments, `no_backend` / `not_offered`, the mock in every default registry.
- `ARCHITECTURE/decisions/ADR-0044-od18-correctness-check-mock-script.md` decisions 2 and 3 (lines 34-63).
- `ARCHITECTURE/decisions/ADR-0021-od18-correctness-check-split.md` decision 3 (lines 54-65) and `ADR-0048-od18-correctness-check-seed-draw.md` decision 10 (the order of a call; the row ④ answer `no_backend` before `op_signature_*`, `draws_not_stated`, `tolerance_not_stated`).
- `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md` decision 4 (the MCP name `mcp__hilclaw__correctness_check`, i.e. listed as `correctness_check`).
- Code: `hilclaw/tools.py` lines 99-200 (`Registry`, `default_registry` at line 182); `hilclaw/blob_tools.py` lines 50-75 (`definitions`, the pattern to follow); `hilclaw/backends.py` (whole docstring, `Backend`, `BackendTable`, `select`); `hilclaw/mock_backend.py` (whole); `hilclaw/mock_check.py` (whole); `hilclaw/check_tool.py` (module docstring and `tool_function`, lines 1-140); `hilclaw/check_definition.py` (whole); `hilclaw/check_operation.py` line 160 (`ask`); `hilclaw/harness/seed_source.py` (`system`, line 56); `hilclaw/gemm_contract.py` (`covers`, line 103); `hilclaw/mcp_front.py` lines 200-220 and `hilclaw/__main__.py` lines 70-85 (both fronts build `default_registry`).
- Tests: `tests/test_check_tool.py` lines 1-230 (the helpers `profile`, `content`, `place`, `a_run`, `request`, `Bench` — reuse them or copy what you need for tests through the default registry), `tests/test_check_definition.py` lines 80-140, `tests/test_blob_tools.py` line 176, `tests/test_mcp_front.py` lines 17-24 and 450-470 (`test_the_fixed_tool_set_is_the_two_blob_tools_today`), `tests/test___main__.py` lines 200-245.

## Acceptance Criteria

1. **Language**: Python, as the rest of `hilclaw/`. Record it and the reason in one line of the commit body and in `## Result`.
2. **Registration** (ADR-0070 decisions 2 and 5): `hilclaw.tools.default_registry(data_root_source)` returns a registry whose `names()` is exactly `("blob.fetch", "blob.push", "correctness.check")`. The definition of `correctness.check` has the description `hilclaw.check_definition.DESCRIPTION` and an input schema equal to `hilclaw.check_definition.input_schema()`. `default_registry` keeps exactly one parameter, still raises `TypeError` for a non-callable source, and building it calls neither the data-root source, the seed source, the predicate nor the script. Where the `ToolDefinition` of the tool is built (a function in `hilclaw/check_definition.py` after the pattern of `blob_tools.definitions`, or the body of `default_registry`) is the executor's choice; avoid an import cycle by importing the check modules inside `default_registry` as it already does for `blob_tools`. **Add no new non-test module** (the five files of `touchesFiles` are the cap).
3. **The default table** (decision 3): a `hilclaw.backends.BackendTable` with exactly one backend named `hilclaw.mock_backend.NAME`, offering exactly `("correctness.check",)`, whose operation is `mock_check.operation(mock_check.default_script)`. Built fresh for each `default_registry` call, in the source, with no option, environment variable or plugin. No `cpu_standin` entry; no operation of another HW tool.
4. **Seed source and predicate** (decision 4): `hilclaw.harness.seed_source.system` and `hilclaw.gemm_contract.covers`, bound in the source; nothing in a request, the configuration or the environment chooses them.
5. **Docstrings** (ADR-0070 Consequences, second bullet), updated so that each is true of the code and cites ADR-0070; keep them short ("코멘트 최소화"; module docstrings are boilerplate and may stay as long as needed):
   - `default_registry`: the set is `blob.fetch`, `blob.push` and `correctness.check`; what the latter is bound to (one sentence each for table, seeds, predicate).
   - `hilclaw/mock_backend.py`: the "Not here yet: the script of the default registry ..." paragraph (the default registry's mock is built for `correctness.check` from `mock_check`, not from `backend`; fault injection, sub-question ⑧, stays open).
   - `hilclaw/check_tool.py`: the first line ("bound to no registry") and the "What the module does not do" sentences "it registers nothing" / "The function is still not the tool a registry offers, since no backend, source of seeds or predicate "covered" is bound" — the module itself still binds nothing; the default registry binds it (ADR-0070).
   - `hilclaw/mock_check.py`: "bound to no registry" in "What the module does not do".
   - `hilclaw/check_definition.py`: the first line and "What the module does not do" ("it registers nothing, builds no `ToolDefinition` ..."), consistent with where criterion 2 put the definition.
   No code change in `check_tool.py`, `mock_check.py` or `mock_backend.py` beyond docstrings.
6. **Tests** (D12 ②-④; tests are outside the size cap). Replace `test_the_default_registry_holds_no_definition_of_the_tool` and update every test that asserts the two-tool set (at least `tests/test_blob_tools.py::test_the_default_registry_holds_the_definitions`, `tests/test_mcp_front.py::test_the_fixed_tool_set_is_the_two_blob_tools_today` and `tests/test___main__.py::test_the_fixed_tool_set_is_the_two_blob_tools_today`; find others with `grep -rn default_registry tests/`). Put the new tests where they fit (e.g. `tests/test_tools.py` or `tests/test_check_definition.py`) and keep `touchesFiles` in sync in `## Result`. Cover at least, with a `tmp_path` data root and runs placed as `tests/test_check_tool.py` does:
   - **Walk-through of ADR-0070** (each row): `tools/list` through the MCP front lists exactly `blob_fetch`, `blob_push`, `correctness_check` with the description and schema of `check_definition`; a call through the default registry about a run at the mock with a covered op_signature, `draws` and a tolerance returns a result with outcome `pass` and appends a start and an end line; a call about a run whose hw_profile names `cpu_standin` is a `ToolFailure` of kind `no_backend`, with no line appended and the seed source not called (monkeypatch `seed_source.system` to a recorder); the same for an accelerator named neither (e.g. `acc_b`); the same request again after the mock call ended returns the stored result with no seed drawn and no operation called; a test-built registry with its own mock script and a seed source returning `7` answers what that script answers.
   - **Through both fronts**: the mock-run call succeeds through `hilclaw.mcp_front` (`tools/call` of `correctness_check`) and through `hilclaw.__main__.main([... "correctness.check" ...])` with exit status 0, and the `cpu_standin` call is the `no_backend` tool failure through each (MCP error object / exit status 3 or 4 as the front defines), bound to a data-root source of the test (`registry=` argument or `monkeypatch` of the configured source, as the existing front tests do).
   - **Binding** (branch/negative): the default table's names are `("mock",)` and its backend offers exactly `("correctness.check",)` (reach it through the public API or a public helper if you add one; do not assert on private attributes); `default_registry` with a non-callable source raises `TypeError` and registers nothing; building the default registry does not call the data-root source, `seed_source.system` or `gemm_contract.covers` (monkeypatched recorders); an op_signature that is not covered gives the existing `op_signature_*` answer through the default registry; a request with an extra member (`draws`) is `invalid_request` through the default registry; an environment variable or option cannot change the table or seed source (e.g. setting an arbitrary `HILCLAW_*` variable leaves the answers unchanged — keep this to one simple test).
   - Existing tests of `check_definition` that pin its imports, public names or the absence of `default_registry` / `ToolDefinition(` / `register(` in its code are updated only as far as criterion 2 requires, and still pin the new truth.
   - The full suite stays green; every public function of a touched module is tested.
7. `ruff check`, `ruff format --check` and the full `pytest` suite pass locally; the coverage gate of `hilclaw/` (line >= 80%, function >= 80%) holds; CI green on the PR.
8. **Size**: non-test change <= 300 LOC and <= 5 files (expected about 90 LOC, mostly docstrings). If exceeded, propose a split in Follow-ups and finish the current scope only.
9. **No data-plane schema change and no new dependency** (ADR-0070 Consequences, A-13 reading): no member of a result, a line of `events.ndjson`, `instance.json`, `STATE.json`, a spec, `build.json` or a result file is added, removed or changed; no request member, `error.kind`, `step` value or reserved kind is added. NumPy, imported through `mock_check` when the default registry is built, is already a dependency in `pyproject.toml`. If the work seems to need any of these, stop and return BLOCKED with the question.
10. **D16**: nothing in this task starts `claude` (any subcommand or flag), a compiler, a kernel or a container, or needs a board or an API key. The mock's default script computes in-process with NumPy only. Tell each reviewer to write no file and start no `claude` process.
11. **Code mode** (CLAUDE.md A-13): branch `claude/T-0215-correctness-check-default-registry` from `origin/main`; Draft PR whose title contains `T-0215` and whose body ends with the line `Task: T-0215`; fresh-context `dev-reviewer` cycle (dev-code-review), at most 7 rounds — past the cap without a final Approve the task is BLOCKED; a result starting with `SECURITY` is BLOCKED; if no reviewer can be spawned the task is BLOCKED (do not review your own work); CI green (3 consecutive CI failures is BLOCKED); then mark ready, `gh pr merge --squash --body <PR body>`, delete the branch. Fill `## Result` with the PR, the squash commit, review rounds, the language line, the final `touchesFiles` and any follow-ups.

### Process

- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0215'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0215 --state all`. Then `gh pr list --repo myungjoo/HIL-Claw --state open`: an open PR touching `hilclaw/tools.py`, `hilclaw/check_definition.py`, `hilclaw/check_tool.py`, `hilclaw/mock_check.py` or `hilclaw/mock_backend.py` makes the task BLOCKED ("open PR conflict").
- Read the comments on issue #5 after the ADR-0070 owner notice (the latest comment whose first line starts `### OD-18` and mentions `T-0214`), skipping the driver's own (ending `— posted by driver`). An owner objection to ADR-0070, ADR-0069 or ADR-0044 makes the task BLOCKED ("requirement unclear"); quote it. An answer to an open HQ does not stop this task; name it in `## Result`.
- Prohibitions: never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; do not edit `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call means BLOCKED; do not work around it. If the branch push is rejected, rebase and retry once, then BLOCKED (`branch-contention`). Past 2h30m wall-clock, BLOCKED (`task-timeout`) with the state in `## Result`.
- Fill in `## Result` on `main` after the merge and leave it uncommitted for the driver (DRIVER §3-6). `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. Return a summary of at most 200 characters.

## Out of Scope

- `sim.run`, `board.run`, `profiler.collect`: their registration, operations in the default table, requests and schemas (T-0210, HQ-0021; ADR-0066 Boundaries); `blob.push` / `blob.fetch` behaviour (unchanged; only the tests that pin the set change).
- A `cpu_standin` backend or its operation of `correctness.check` (ADR-0060, OD-14, sub-question ⑱).
- Fault injection in a live session (sub-question ⑧); any claim about what a live Claude Code session does with the tool (sub-questions ① and ⑤ — runtime acceptance).
- Any change to `hilclaw/mcp_front.py`, `hilclaw/__main__.py`, `hilclaw/backends.py`, `hilclaw/check_operation.py` or the frame's messages.
- Any `ARCHITECTURE/` edit, including the "Not edited and now less exact" list of ADR-0070 Consequences and the three T-0214 round-7 nits on ADR-0070 (a later doc task).
- PLAN checkboxes (P1-1 stays open: `sim.run`, `board.run`, `profiler.collect` and the conformance tests remain).

## Follow-ups

## Result

- **Outcome**: DONE. PR #143 (https://github.com/myungjoo/HIL-Claw/pull/143), squash-merged as `f40c317`; branch deleted.
- **Review**: 2 rounds with a context-isolated `dev-reviewer` (dev-code-review), both Approve; round-1 nit (test name) fixed in round 2's head; remaining items are the follow-ups below.
- **CI**: green on head `bde7e3c` (Python 3.11/3.14, coverage, C, sh, test presence). Local: `ruff check .`, `ruff format --check .`, full `pytest` 20689 passed, 354 skipped, 1 xfailed (Windows).
- **Language**: Python, as the rest of the `hilclaw/` layer-2 package it extends.
- **What landed**: `hilclaw.check_definition.default_table()` (one backend, the mock under `mock_backend.NAME`, offering only `correctness.check` with `mock_check.operation(mock_check.default_script)`; no `cpu_standin` entry) and `check_definition.definition(source)` (`check_tool.tool_function` bound to that table, `seed_source.system`, `gemm_contract.covers`; `DESCRIPTION`, `input_schema()`); `tools.default_registry` registers it and keeps one parameter. Docstrings of the five modules updated per criterion 5. Non-test change about 105 lines in 5 files.
- **Final touchesFiles**: `hilclaw/tools.py`, `hilclaw/check_definition.py`, `hilclaw/check_tool.py`, `hilclaw/mock_check.py`, `hilclaw/mock_backend.py`, `tests/test_check_definition.py`, `tests/test_blob_tools.py`, `tests/test_mcp_front.py`, `tests/test___main__.py`, `tests/test_tools.py`, `tests/test_gemm_contract.py` (`tests/test_check_tool.py` was not changed; `tests/test_gemm_contract.py`'s "bound nowhere" pin now allows `check_definition.py` as its one binder).
- **#5 after the ADR-0070 notice**: no owner comment; no open PR conflict at start.
- **Follow-ups**:
  1. Windows only: building the default registry now imports NumPy (via `mock_check`, foreseen by ADR-0070 Consequences); a process started with fd 2 closed then dies at NumPy import (0xC0000409) instead of answering. `tests/test___main__.py::test_a_process_started_without_standard_error_still_answers` is a strict xfail on win32 (Linux CI still asserts it). Options: lazy NumPy import in `mock_check` (a code change criterion 5 forbade here), or a decision that this case is not a runtime-platform concern on Windows.
  2. `hilclaw/gemm_contract.py` docstring says the module "is bound to no tool"; its `covers` is now bound by the default registry (ADR-0070 decision 4). A one-line docstring fix was out of this task's five-file cap.
  3. ADR-0070 Consequences "Not edited and now less exact" list and the T-0214 round-7 nits stay for a later doc task (Out of Scope here).
