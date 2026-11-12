---
id: T-0563
title: Land ADR-0200 slice 3b for PLAN P3-11 — place the given code as attempt `(0, 1, 1)` (`output/given.c`, written from the verified blob), and teach round 0 of a given-code run in `orchestration/round-manager.md` (no coder call, no spec, no repair), handing one runtime acceptance item to the driver
phase: P3
status: IN_PROGRESS
commitMode: code
coversReq: [D27, FR-19, FR-1, OD-33, OD-28, "PLAN P3-11", HQ-0092, HQ-0097, ADR-0200]
dependsOn: [T-0561, T-0562]
touchesFiles:
  - hilclaw/given_attempt.py
  - hilclaw/run_file_tools.py
  - hilclaw/turn_permissions.py
  - hilclaw/spec_tool.py
  - orchestration/round-manager.md
  - tests/test_given_attempt.py
  - tests/test_run_file_tools.py
  - tests/test_turn_permissions.py
  - tests/test_spec_tool.py
  - tests/test_turn_definition.py
  - tests/first_run_stubs.py
estimatedSize: {loc: 300, files: 5}
hq: []
---
## Why

**PLAN P3-11** continues with **ADR-0200 slice 3b** (decision 8: "The placement of `(0, 1, 1)` from the blob; `orchestration/round-manager.md` round 0 of a given-code run (no coder call, no repair); a runtime acceptance item for that live round 0", ~300 LOC, 3–4 files). After slice 2 (T-0561) a started given-code run holds `given_code` in `instance.json` version 3, and after slice 3a (T-0562) the run-level readers and the evaluation tools read it; this slice puts the given code where round 0 evaluates it and tells the Round-Manager to do so. Slice 4 (the command `hilclaw.given_eval`, verified with the real clang; PLAN P3-11 is checked after it) is planned after this batch.

**Order and brake**: as in T-0561's Why (D27 ①, D31 ① and ②: PLAN P3-11 work, the PLAN-item exception to the E4 brake). If the order has changed when the task runs, report it in `## Result` and stop before writing code.

**The one design point ADR-0200 leaves to this slice**: how the Round-Manager of a live turn reaches the placement. ADR-0200 decision 7 names "the placement of `(0, 1, 1)` (new) — writes `given.c` from the verified blob; called by the command", and decision 4 (a) puts the placement in round 0 of a loop run; it does not say whether the Round-Manager calls a new FR-10 tool (registered beside `instance.read`/`run.fresh` and admitted in `turn_permissions.ROUND_MANAGER_TOOLS`) or whether an existing step places it. The Round-Manager has no file tools (`orchestration/round-manager.md`), so a tool is the expected answer. Decide it under DRIVER §9 (an MCP tool name and its caller are no data-plane frame, D23): if the choice fits a short paragraph, write it in the module docstring and the PR body; if it needs a record (for example a new step value or a new error kind of a result), write a short ADR in this task (D20 ①) in the ADR-0001 record format and notify #5. Open HQs not to be anticipated or asked: HQ-0081, HQ-0083, HQ-0085, HQ-0095, HQ-0096, HQ-0100. An owner-only part found during the work goes into `## Result` in the DRIVER §8 structure (Korean), the rest lands, `DONE` (D27 ⑥).

## Required Reading

- `PROCESS/DRIVER.md`:
  - **§3-5 and §5**: branch `claude/T-0563-<slug>`, the `Task: T-0563` trailer and the PR body's last line, size (D30), tests (D12), list assertions (D21), storage (D29: `${TMPDIR:-/tmp}/hilclaw-driver/T-0563/`, removed at the end).
  - §3 "BLOCKED 사유" and "승인된 열린 목록"; §6 D27 (⑥), D31 ②; §8 and D22 (runtime acceptance items are returned in `## Result`, the driver adds them to `PROCESS/RuntimeAcceptance.md`); §9.
- `PROCESS/tasks/T-0560-…`, `T-0561-given-code-instance-start.md`, `T-0562-given-code-run-readers.md` (`## Result` of each).
- **`ARCHITECTURE/decisions/ADR-0200-od33-given-code-evaluation.md`**: decisions 2 (`given.c`, ADR-0055 rules), **4 (a)** (round 0 makes no coder call; `(0, 1, 1)` holds `given.c` written after `cas.verify_blob`; no `spec.json`; no repair; a given attempt that cannot stand leaves round 0 without a standing attempt — ADR-0185; `candidates_per_round` 1 only), 5 (the command calls the placement), 7 (reader table, column "3b") and Consequences (the runtime acceptance item).
- ADRs: `ADR-0142-od23-first-case-round-zero-after-coder-call.md` (round 0's steps after the coder call), `ADR-0185-od23-first-case-round-zero-ends-without-standing-attempt.md`, `ADR-0119-od28-first-case-baseline.md`, `ADR-0055-od23-coder-output-form.md`, `ADR-0004` (the run layout; the attempt directory), `ADR-0118` (turn sessions), the ADRs that registered `instance.read`/`run.fresh` (cited in `hilclaw/run_file_tools.py`'s docstring).
- Code and prompts: `orchestration/round-manager.md` (round 0 steps 1–5 and "The end of a session"), `orchestration/agents/*.md` (what the evaluator and experiment-runner read for round 0), `hilclaw/run_file_tools.py` (tool registration form), `hilclaw/turn_permissions.py` (`ROUND_MANAGER_TOOLS`), `hilclaw/caller_check.py`, `hilclaw/mcp_front.py`, `hilclaw/cas.py` (`verify_blob`, blob path), `hilclaw/layout.py` (attempt `output/` path), `hilclaw/spec_tool.py`, `tests/test_turn_definition.py` and `tests/first_run_stubs.py` (how the prompt and the stub-`claude` first run are tested).

## Acceptance Criteria

1. **The placement** (a new module, name the executor's; `hilclaw/given_attempt.py` is a placeholder): for a run whose `instance.json` is version 3, verifies the `given_code` blob with `cas.verify_blob` and writes it as `output/given.c` of attempt `(0, 1, 1)`, creating the attempt directory as a coder attempt's would be; refuses with a named error, writing nothing, when the run is not version 3, the blob is missing or fails verification, or `(0, 1, 1)`'s `output/` already holds anything; never writes a `spec.json`. Callable by the slice-4 command as a function.
2. **The Round-Manager's way to it** (the design point in Why): implemented and, if a tool, registered on the MCP front and admitted only for the Round-Manager (`turn_permissions`, `caller_check` as the existing tools are), with its journaling as the existing run-file tools have it.
3. **`orchestration/round-manager.md`**: round 0 of a run whose `instance.json` holds `given_code` places the given code instead of delegating to `coder-driver` (step 2), writes no spec, makes no repair, then proceeds with the two checks, the timing and `round.end`/`run.commit` as for a coder attempt (ADR-0142); a given attempt that cannot stand follows ADR-0185. Rounds ≥ 1 and runs without `given_code` read exactly as before. Cite ADR-0200 decision 4 (a) as the text cites its records.
4. **No spec for `(0, 1, 1)`**: if T-0562 did not already refuse a spec write for round 0 of a version-3 run, `spec_tool` refuses it here with an existing error kind.
5. **Tests** (D12): the placement's happy, error, branch and **negative** cases (each refusal of criterion 1, a corrupted blob, a version-1/2 run, a second placement); the tool's registration and admission (only the Round-Manager); the prompt text for round 0 of a given-code run, in the manner of `tests/test_turn_definition.py`; if feasible within the stub-`claude` first-run tests (`tests/first_run_stubs.py`), one stubbed round 0 of a given-code run at `cpu_standin` reaching `round.end` with the real clang (D29). Every public function of touched modules tested; `hilclaw/` coverage ≥ 80%. Existing tests unchanged except list assertions under D21 (foreseen: the tool-name sets pinned in `tests/test_turn_permissions.py`, `tests/test_run_file_tools.py`, `tests/test_mcp_front.py` or `tests/test_caller_check.py`, and any public-name set of `tests/test_run_file_tools.py`). List every such edit in the PR body.
6. **Unchanged**: runs without `given_code`, rounds ≥ 1, nightly and model paths behave as before; the full test suite passes.
7. **Runtime acceptance item** in `## Result` (DRIVER §8, D22; ADR-0200 Consequences), in Korean in the form of `PROCESS/RuntimeAcceptance.md` (출처 = `T-0563`, ADR-0200): a live round 0 of a given-code loop run in which the real Round-Manager places the given code, makes no coder call and evaluates `(0, 1, 1)`. Do not edit `PROCESS/RuntimeAcceptance.md`.
8. **Process**: dev-item-address steps, Draft PR, context-isolated review to Approve (≤ 14 rounds, D28), CI green, self squash-merge with the PR body's last line `Task: T-0563`; a §9 notice on #5 only if an ADR is written. Record the language choice (Python; Markdown for the prompt) in the commit body.

## Out of Scope

- Slice 4 (`hilclaw.given_eval`) and slice 5 (`compile_settings` with given code); round 0 with N > 1 in a given-code run (OD-28).
- Cases, the S6 metric and model runs of a given-code run; vendor targets, HQ-0095, HQ-0096, `device_unavailable`.
- Starting `claude` in any form (D16). A partial test run (D25) of round 0 is allowed only if the executor judges it needed and the machine meets its preconditions; the live check is the runtime acceptance item above.

## Follow-ups

- The planner creates ADR-0200 slice 4 (the command `hilclaw.given_eval`, verified with the real clang at `cpu_standin`; PLAN P3-11 is checked after it) once this batch lands.

## Result
