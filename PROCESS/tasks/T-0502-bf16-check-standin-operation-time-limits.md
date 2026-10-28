---
id: T-0502
title: Write the ADR on the time limits of the bf16 verification builds and processes at cpu_standin, build the cpu_standin operation of correctness.check for the five bf16 kinds, and set their checked flags (ADR-0177 slice 2, last part)
phase: P2
status: TODO
commitMode: code
coversReq: [C-6, FR-9, FR-10, NFR-4, OD-14, OD-18, OD-31, "PLAN P2-11", "PLAN P2-14"]
dependsOn: [T-0501]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0179-od14-bf16-standin-check-time-limits.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
  - hilclaw/standin_settings.py
  - hilclaw/standin_check.py
  - hilclaw/standin_copies.py
  - hilclaw/contract_table.py
  - tests/test_standin_settings.py
  - tests/test_standin_check.py
  - tests/test_standin_copies.py
  - tests/test_contract_table.py
  - tests/test_check_tool.py
  - tests/test_check_definition.py
  - tests/test_backend_conformance.py
estimatedSize: {loc: 420, files: 8}   # non-test: ADR ~150 lines, standin_settings ~50, standin_check ~110, standin_copies ~40, contract_table ~10, registers ~15. The ADR file name and number are a suggestion (next free number after ADR-0178). Tests are outside the cap (DRIVER §5, D4/D20).
hq: []
---
## Why

**State.** ADR-0177 decision 5 item 2 ends with "the two operations and the mock's default script; then the `checked` flags of those five entries". After T-0498 to T-0501 the mock serves `correctness.check` for bf16 `gemm`, `rmsnorm`, `elementwise_add`, `swiglu` and `sdpa_kv_cache`, the tool chooses the bf16 `step` values and the readers read them (ADR-0178). What is left of item 2 is the `cpu_standin` operation — today `hilclaw/standin_check.py` takes exactly a `CheckParameters` (fp32 `gemm`) and builds `hilclaw/harness/verification_program.c` — and then the five `checked` flags. ADR-0177 decision 2 makes a flag `yes` only when the tool serves the contract "on both backends of its table (the mock and `cpu_standin`)".

**Why an ADR.** The build settings are decided (ADR-0177 decision 3 reads ADR-0116's fixed set as holding for these builds), but the time limits are not: ADR-0117 fixes the build limit and the process-limit rule `min(1500, 10 + draws * (1 + 2*m*k*n / 2e8))` for the fp32 `gemm` verification and timing runs only (its decision 8 item 6, "Scope"), and the bf16 kinds have other shapes, another amount of work per draw (bf16 conversions in software; `sdpa_kv_cache` over `m·l·h·d`) and another Python-side judging cost. Which limits these builds and processes get is part of **OD-14** (timeout hierarchy, call level) — a design-level choice the driver closes under DRIVER §9, written with its first code slice in one task (DRIVER §6 "task 단위" ①, D20). T-0500's Result named this as the planner's next candidate.

**PLAN order and D18.** P2-11 and P2-14 are PLAN checklist items; D18 does not apply. No RuntimeAcceptance `실패` item exists as of `main` `00560812`.

**D16.** Everything is verified with tests in this repository and stub `docker`/compiler where the existing `standin_check` tests use them; nothing starts `claude`, needs a board, a real container runtime or real Llama weights. Facts only a real container on a C-7 machine can establish (whether the limits fit) are runtime acceptance items, not tasks.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task format, naming `claude/T-0502-<slug>`, `Task: T-0502` trailer, size cap, test rules D12, list-assertion rule D21), §8 (runtime acceptance items, D22), §9 (OD closing: ADR + reviewer Approve + owner notice on #5).
- `CLAUDE.md` (rules; "미결은 발명하지 않는다"; "세션 진입 점검"; A-13 BLOCKED reasons; test rules; language policy).
- `PROCESS/tasks/T-0498-*.md`, `T-0499-*.md`, `T-0500-*.md`, `T-0501-*.md` (their Results).
- `ARCHITECTURE/decisions/ADR-0177-od18-od6-contract-table.md` decisions 1, 2, 3 ("What the operations are handed", `cpu_standin` bullet) and 5.
- `ARCHITECTURE/decisions/ADR-0117-od14-cpu-standin-time-limits.md` (all; the rule, its estimates, decisions 5 and 7, Limits, Consequences' runtime acceptance items); `ARCHITECTURE/decisions/ADR-0116-od18-cpu-standin-build-settings.md` decision 2.
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md` decisions 2, 3, 10 and 11; `ARCHITECTURE/decisions/ADR-0165-od31-bf16-sdpa-kv-cache-verification-run.md` decisions 2, 3, 11 and 12; `ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md` (the shape sets).
- `ARCHITECTURE/decisions/ADR-0144-od14-first-case-build-run-container.md` decision 3; `ARCHITECTURE/decisions/ADR-0168-od18-standin-container-situations.md` decision 2 (rows C12, C13, C15 on the copies) and decision 5; `ARCHITECTURE/decisions/ADR-0169-od18-standin-build-log-and-removal.md`; `ARCHITECTURE/decisions/ADR-0056-od18-correctness-check-verification-executable.md`; `ARCHITECTURE/decisions/ADR-0017-od16-cpu-standin-verification-run.md` decision 2.
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph of the OD register (line ~84) and the rows of the ODs the ADR answers part of (at least OD-14, OD-18). `ARCHITECTURE/OpenDecisionProposals.md`: the header's "기록 규칙" (line ~8) and those sections. `ARCHITECTURE/StandardScenarios.md`: the first paragraph of § 검사 결과 (line ~168) and rows S0 and S1.
- Code: `hilclaw/standin_check.py`, `hilclaw/standin_settings.py`, `hilclaw/standin_copies.py`, `hilclaw/contract_table.py`, `hilclaw/check_parameters.py`, `hilclaw/harness/bf16_verification_build.py`, `hilclaw/harness/bf16_verification.py` (`program_arguments`), `hilclaw/harness/bf16_sdpa_kv_cache_verification.py` (`program_arguments`), `hilclaw/harness/bf16_verification.h` and the `bf16_verification_*.c` programs (they include the header).
- Tests: the test files of the touched modules, `tests/test_backend_conformance.py`.

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md): before editing `ARCHITECTURE/`, check open PRs, Issues #4/#5/#7/#8 and the unresolved `humanQuestions` of `PROCESS/STATE.json` (HQ-0076 concerns P2-10 and is not crossed). Name in the ADR's Status what was checked.
2. **ADR** at `ARCHITECTURE/decisions/ADR-0179-<slug>.md` (next free number), in the form of recent ADRs (Status, Context, Decision, Alternatives considered, Consequences, Boundaries, References). It decides the build time limit and the process time limit of the verification build and process of each of the five bf16 kinds at `cpu_standin` (part of OD-14), as ADR-0117 did for fp32 `gemm`: the source (a rule in the package source applied to what the operation is handed — the kind and its dimensions in `task_contract` order, and `draws`), the work measure per kind, the values and the estimates behind them, how they stand against the MCP idle window (ADR-0117 decision 5) at the largest shapes of ADR-0152, and what a call answers when a limit is reached (ADR-0117 decision 7, unchanged unless shown otherwise). Weigh at least: (i) ADR-0117's rule applied unchanged with a per-kind work measure; (ii) a per-kind rate or constant. Say which estimates are unverified and hand them to `PROCESS/RuntimeAcceptance.md` as runtime acceptance items (D22). It also states how the bf16 program and the header `bf16_verification.h` reach the build directory (the copies of ADR-0168 C12/C13/C15) if that needs a choice. **A-13 reading**: if anything changes the form or meaning of a data-plane member, a line of `events.ndjson` or a tool result an agent reads, say so; a "데이터 plane 스키마 변경" stops the task as BLOCKED with the question for the owner. Do not decide anything owner-only (#5 A/B, C-6, OD-25, OD-3) — tolerances, seed source and number of draws stay the instance's and OD-16 ⑤'s.
3. **Register edits** follow the recording rules written in those files — not earlier task files: `Requirements.md` rows of the ODs the ADR answers part of, per the register's "행 형식" (one link per new ADR in `**확정분**:`, `**잔여**:` rewritten in place, no restatement of the record, no dated paragraph); `OpenDecisionProposals.md` per its header's "기록 규칙" (one `채택분` line per section the ADR answers, sub-question status rewritten in place); `StandardScenarios.md` § 검사 결과 per its first paragraph (CLAUDE.md "문서 커버리지 재검사"), S0 and S1 at least.
4. **Operation built.** `hilclaw/standin_check.py`'s operation takes `Bf16CheckParameters` for the five kinds as well as `CheckParameters`: it places the kernel files, the kind's program source (`bf16_verification_build.PROGRAM_SOURCES`) and whatever the program includes, builds with ADR-0116's fixed set (`standin_settings.FLAGS`, `TRAILING_FLAGS`) within the ADR's build limit, runs the executable with the arguments of the kind's `program_arguments` within the ADR's process limit, and returns the standard output as today. Every situation of ADR-0168/ADR-0169 (image, build directory, copies, build log, statuses 125–127, removal) is answered as for fp32 `gemm`. For `CheckParameters` every answer, argument and limit is exactly today's.
5. **Flags.** In `hilclaw/contract_table.py`, the `checked` flag of the bf16 `gemm`, `rmsnorm`, `elementwise_add`, `swiglu` and `sdpa_kv_cache` entries becomes `True`; `rope` stays `False`; every `timed` flag stays as it is, so `run_covers` and `start_covers` are unchanged (ADR-0177 decision 2 table, "After slice 2" column).
6. **Tests** (D12), with the stub client/compiler the existing `standin_check` tests use: happy — each of the five kinds through the `cpu_standin` operation (arguments, sources placed, limits handed), and through the registered `correctness.check` on the mock and on `cpu_standin` with the default registry (the tool now admits them); the backend conformance test covering at least one bf16 kind on both backends; branch — fp32 `gemm` unchanged; `rope` still refused `op_signature_not_covered`; the largest shape of each kind reaching or not reaching the cap; negative — a build or process past its limit (`time_limit`), a missing program or header copy, wrong parameter types, a value the limit rule refuses. Package line and function coverage stay at or above 80 %, ruff is clean, the full local suite passes on Linux/WSL with clang; CI is green.
7. **Existing tests.** D21 list pins foreseen: the public-name and import assertions of `tests/test_standin_settings.py`, `tests/test_standin_check.py`, `tests/test_standin_copies.py` and `tests/test_contract_table.py`. Besides those, the change of criterion 5 is this task's purpose: assertions that pin the `checked` flags of those five entries (for example `tests/test_contract_table.py` line ~86, `(found.checked, found.timed) == (False, False)`) and tests that pin `correctness.check` refusing a covered bf16 record of those five kinds under the default registry (`tests/test_check_tool.py`, `tests/test_check_definition.py`) change to the new admission, and only those. Other existing assertions stay unchanged. List every edited assertion in the PR body.
8. **Owner notice** (DRIVER §9): after merge, one comment on Issue #5 announcing the ADR and the OD rows it changes, ending with `— posted by driver`; record the URL in Result.
9. **Result** names: the language choice and reason (Python), the PR, review rounds, edited assertions, the runtime acceptance items worded for `PROCESS/RuntimeAcceptance.md` (D22), and the planner's next candidate (expected: the record of the bf16 timing run, ADR-0177 decision 5 item 4 — OD-13, OD-16 ⑥ — or the `rope` start-position record, item 3, whichever needs no owner answer first).

## Out of Scope

- `rope` (its check waits on the start-position record, ADR-0177 decision 4); the bf16 timing run and the `timed` flags; the instance start; the executor binding (OD-20, OD-7).
- OpenMP (HQ-0034, deferred), any flag outside ADR-0116's set, any change of the fp32 `gemm` limits of ADR-0117.
- Catalog entries for bf16 contracts (OD-22); the orchestration prompts and agent definitions.
- Any deferred line of PLAN "보류". Starting `claude`, a real Docker daemon, real weights, a board, an API key (D16).

## Follow-ups

## Result
