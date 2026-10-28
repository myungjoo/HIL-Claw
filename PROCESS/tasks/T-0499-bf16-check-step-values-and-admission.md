---
id: T-0499
title: Wire bf16 gemm, rmsnorm, elementwise_add and swiglu checks into the correctness.check tool — the two bf16 step values chosen from the read of ⓢ, admission and parameters per kind, the ④ answer for a changed dtype, the compiler-log step list (ADR-0177 slice 2, tool level)
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, FR-10, OD-18, OD-31, "PLAN P2-11", "PLAN P2-14"]
dependsOn: [T-0498]
touchesFiles:
  - hilclaw/check_identity.py
  - hilclaw/hw_tool.py
  - hilclaw/check_tool.py
  - hilclaw/check_admission.py
  - hilclaw/check_seed.py
  - hilclaw/layout.py
  - tests/test_check_identity.py
  - tests/test_hw_tool.py
  - tests/test_check_tool.py
  - tests/test_check_admission.py
  - tests/test_check_seed.py
  - tests/test_layout.py
estimatedSize: {loc: 330, files: 6}   # non-test: check_identity ~40 (two values, the choice from the ⓢ read), hw_tool ~50 (handing the ⓢ read to the step choice, correctness.check only), check_tool ~40, check_admission ~80 (dimensions per kind, the dtype of ④ against the step), check_seed ~40 (building the parameters per kind), layout ~5, docstrings included. Tests are outside the cap (DRIVER §5, D4/D20).
hq: []
---
## Why

**State.** PLAN P2-14 (Llama 3.2 1B end-to-end, the D18 goal) needs every P2-11 operation's kernel to come from an instance. ADR-0177 (T-0496, `main` `31ebd97f`) decision 5 item 2 is `correctness.check` for the bf16 kinds; until it lands no bf16 contract is `checked` and the instance start admits none (ADR-0177 decision 2). The planner cut that slice bottom-up (DRIVER §5 10-file cap; ADR-0177 decision 5 allows the cut): T-0498 builds, at module level, what a bf16 check of `gemm`, `rmsnorm`, `elementwise_add` and `swiglu` hands its operation and makes of the answer. **This task** puts it into the tool: the call identity (`step`), the admission and the seed step that build the bf16 parameters, the ④ answer for a file whose `dtype` changed, and the log-file step list. T-0500 then makes the readers find those lines; a later task adds the `cpu_standin` operation and flips the `checked` flags.

**No ADR here.** ADR-0177 decision 3 decides the two values (`correctness_check_bf16_sim`, `correctness_check_bf16_board`), which value a call takes and where ("from `point` and from the read of ⓢ"), the ④ answers, the dimensions per kind (ADR-0041 decision 2 read per kind) and what the operations are handed.

**PLAN order and D18.** P2-11 and P2-14 are PLAN checklist items; D18 does not apply. No RuntimeAcceptance `실패` item exists as of `main` `1b6dc8ee`.

**D16.** Everything is verified with tests in this repository; nothing starts `claude`, needs a board, a container runtime or real Llama weights.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task format, naming `claude/T-0499-<slug>`, `Task: T-0499` trailer, size cap, test rules D12, list-assertion rule D21), §8 (runtime acceptance items, D22).
- `CLAUDE.md` (rules; "미결은 발명하지 않는다"; A-13 BLOCKED reasons; test rules; language policy).
- `PROCESS/tasks/T-0498-bf16-check-parameters-result-judging-mock.md` (its Result: the parameter form chosen and the module-level paths this task calls).
- `ARCHITECTURE/decisions/ADR-0177-od18-od6-contract-table.md` decisions 1–3 ("Dimensions", "Covered", "Seed, draws and tolerance", "What the operations are handed", "The two values", "Which value a call takes, and where in the order of a call") and 5.
- `ARCHITECTURE/decisions/ADR-0040-od18-correctness-check-call-identity.md` decisions 3–7; `ARCHITECTURE/decisions/ADR-0100-od8-tool-result-change.md` decisions 3–5; `ARCHITECTURE/decisions/ADR-0030-od8-layout-stamp-read-order.md` decisions 1–4 (ⓢ and ④ are two reads); `ARCHITECTURE/decisions/ADR-0041-od18-correctness-check-dimensions.md` decisions 2–5 and 8; `ARCHITECTURE/decisions/ADR-0048-od18-correctness-check-seed-draw.md` decision 10 (the order of a call); `ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md` decision 6 (the log file per `step`).
- Code: `hilclaw/check_identity.py`, `hilclaw/hw_tool.py` (`stepped_tool_function`, `_carry_out`), `hilclaw/check_tool.py`, `hilclaw/run_tool.py` (the other user of `stepped_tool_function`; read only), `hilclaw/check_admission.py`, `hilclaw/check_seed.py`, `hilclaw/instance.py` (`read`, `Instance`), `hilclaw/layout.py` (`BUILD_LOG_STEPS`, `build_log_file`), `hilclaw/contract_table.py`, `hilclaw/check_definition.py` (the registry's binding; read only).
- Tests: the test files of the six touched modules, `tests/test_run_tool.py`, `tests/test_check_definition.py` (must stay green unchanged).

## Acceptance Criteria

1. **The two `step` values** (ADR-0177 decision 3): `hilclaw.check_identity` exposes `correctness_check_bf16_sim` and `correctness_check_bf16_board` beside the existing two, and its tuple of every `step` value of the tool holds all four. `STEP_SIM`, `STEP_BOARD` and their values are unchanged. `hilclaw.layout.BUILD_LOG_STEPS` admits the two new values (the compiler log of a bf16 check has its file, ADR-0078).
2. **The value a call takes**: when the `instance.json` read whole in ⓢ states an `op_signature` whose record's `dtype` is `bf16`, the call takes the bf16 value of its `point`; in every other case (no `op_signature`, any other `dtype`, a file ⓢ does not read as valid) the value `point` gives today. For `correctness.check` only — `sim.run` / `board.run` keep their values and `tests/test_run_tool.py` passes unchanged. How `stepped_tool_function` hands the read of ⓢ to the choice is the executor's; it adds no read of the file and keeps the order of a call (ADR-0048 decision 10; ADR-0030).
3. **Admission and parameters per kind** (ADR-0177 decision 3): for a record the bound predicate covers, `check_admission.admit` gives the shape members of the record's kind (ADR-0041 decision 2 read per kind), and `check_seed` builds the bf16 parameters of T-0498 (kind, dtype, dimensions in `task_contract` order, seed, draws), so the operation of the selected backend receives them. For an fp32 `gemm` record `Admitted` and the parameters are as today.
4. **④ for a changed file**: a record covered in ④ whose `dtype` is not the one the `step` was taken for is answered `op_signature_not_covered`, with no line appended, nothing consumed and no seed drawn — in both directions. A bf16 record the predicate refuses is answered `op_signature_not_covered` under the bf16 value, with no line. Answers for every fp32 file are as today.
5. **Nothing more is admitted through the registry**: the `checked` flags of `hilclaw/contract_table.py` and the registry's binding are unchanged, so through the default registry every bf16 file is still answered `op_signature_not_covered`, now looked up under the bf16 value. A test shows this through the default registry for each of the four kinds.
6. **End to end through the tool function**: with `check_tool.tool_function` bound in a test to the mock backend and a predicate admitting the four bf16 entries (for example `contract_table.covers`), a call for each kind at both points appends start and end lines under the bf16 value and returns the T-0498 result (pass with the default script; fail and broken with test scripts); a repeated call returns the stored result under the same identity; the compiler-log path is formed under the bf16 value.
7. **Tests** (D12): happy and branch as in criteria 2, 3 and 6; negative — a file that changes `dtype` between ⓢ and ④ in both directions; a bf16 record with a shape outside its contract's set; a bf16 record of `rope` or `sdpa_kv_cache` (not covered by the four-kind test predicate, or refused by `check_covers`); an invalid file in ⓢ; a `point` that is neither value. Package line and function coverage stay at or above 80 %, ruff is clean, the full local suite passes on Linux/WSL with clang; CI is green.
8. **D21 list pins** foreseen: `tests/test_check_identity.py::test_the_step_values_the_numbers_and_the_members_are_tuples`, `::test_public_names_of_the_module_and_no_default` and `::test_module_imports_re_and_the_tools_only_and_has_no_entry` (if an import is added); `tests/test_check_admission.py::test_admitted_has_six_fields_and_no_default`, `::test_module_imports_three_modules_and_has_no_entry` and `::test_public_names_of_the_module_and_no_default`; `tests/test_check_seed.py::test_module_imports_the_five_only_and_has_no_entry` and `::test_public_names_of_the_module_and_no_default`; `tests/test_layout.py::test_public_name_lists_match_the_adr` if it pins `BUILD_LOG_STEPS`. Other existing assertions stay unchanged. List each edited assertion in the PR body.
9. **No record changes.** If ADR-0177 decision 3 does not settle something this task needs, do not invent it: return BLOCKED with the question.
10. **Result** names: the language choice and reason (Python), the PR, review rounds, edited list pins, and any runtime acceptance item (expected none).

## Out of Scope

- What T-0498 builds (parameters type, result, judge, mock script), except calling it.
- The readers `checks.read`, `verdicts.write`, `spec_feedback`, `check_standing` beyond what criterion 1's tuple widens (T-0500).
- The `cpu_standin` operation, its time limits, the `checked` flags; `sdpa_kv_cache`, `rope`; the bf16 timing run; the instance start; the executor binding.
- Any deferred line of PLAN "보류". Starting `claude`, real weights, a board, an API key (D16).

## Follow-ups

## Result
