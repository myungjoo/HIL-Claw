---
id: T-0498
title: Build what a correctness.check of bf16 gemm, rmsnorm, elementwise_add and swiglu hands its operation and makes of the answer — check parameters per kind, the HQ-0077 result, the ADR-0163 judge and the mock's default script (ADR-0177 slice 2, module level)
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, FR-10, OD-18, OD-31, "PLAN P2-11", "PLAN P2-14"]
dependsOn: []
touchesFiles:
  - hilclaw/check_parameters.py
  - hilclaw/check_result.py
  - hilclaw/check_judging.py
  - hilclaw/check_answer.py
  - hilclaw/check_operation.py
  - hilclaw/mock_check.py
  - tests/test_check_parameters.py
  - tests/test_check_result.py
  - tests/test_check_judging.py
  - tests/test_check_answer.py
  - tests/test_check_operation.py
  - tests/test_mock_check.py
estimatedSize: {loc: 420, files: 6}   # non-test: check_parameters ~50 (the bf16 form beside the fp32 one), check_result ~80 (shape per kind, failed bound per output elements), check_judging ~80 (the ADR-0163 judge for the four kinds), check_answer ~40, check_operation ~30 (unpacking either form), mock_check ~100 (the bf16 default script), docstrings included. Tests are outside the cap (DRIVER §5, D4/D20).
hq: []
---
## Why

**State.** PLAN P2-14 (Llama 3.2 1B end-to-end, the D18 goal) needs every P2-11 operation's kernel to come from an instance. ADR-0177 (T-0496, PR #309, `main` `31ebd97f`) decided how the seven kernel contracts reach the tools; its decision 5 lists the later code slices in landing order. Slice 2 is "`correctness.check` for bf16 `gemm`, `rmsnorm`, `elementwise_add`, `swiglu` and `sdpa_kv_cache` on the mock and `cpu_standin`: the admission and the parameters per kind, the two new `step` values and the result list the owner gave (HQ-0077, decision 3), the readers of a check result (`checks.read`, `hilclaw.spec_feedback`) accepting it, the two operations and the mock's default script; then the `checked` flags of those five entries". Until slice 2 lands no bf16 contract is `checked`, the instance start admits none (ADR-0177 decision 2), and P2-14's instances cannot start.

**How slice 2 is cut.** Slice 2 touches about twenty modules — above the 10-file cap (DRIVER §5) — so the planner cuts it bottom-up, for the four ADR-0163 kinds first (ADR-0177 decision 5 allows the cut; `sdpa_kv_cache` follows in a later task):
1. **This task** — module level: what a bf16 check hands its operation and what it makes of the answer (parameters, result, judge, the mock's operation and default script). Nothing calls the new paths from the tool yet.
2. **T-0499** — the tool: the two new `step` values chosen from the read of ⓢ, admission per kind, the seed step building the bf16 parameters, the compiler-log step list.
3. **T-0500** — the readers of a check's lines (`checks.read`, `verdicts.write`, `spec_feedback`), with the record of how they find a bf16 check's lines.
Later (next planner run): the `cpu_standin` operation for these kinds with the record of its time limits (OD-14) and the `checked` flags; then `sdpa_kv_cache`; then `rope` and the bf16 timing run (ADR-0177 decision 5 items 3–4).

**No ADR here.** ADR-0177 decision 3 decides what a bf16 check takes (dimensions, seed, draws, tolerance, the judge, what the mock and `cpu_standin` operations are handed) and the result the owner gave (HQ-0077), and leaves the Python form to the slice ("a widened `CheckParameters` or a second type is the slice's, provided the operations keep receiving `m`, `k`, `n` for fp32 `gemm` as today").

**PLAN order and D18.** P2-11 and P2-14 are PLAN checklist items; D18 does not apply. P2-10 is blocked on HQ-0076 (T-0493). No RuntimeAcceptance `실패` item exists as of `main` `1b6dc8ee`, so none is fixed here.

**D16.** Everything is verified with tests in this repository; nothing starts `claude`, needs a board, a container runtime or real Llama weights.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task format, naming `claude/T-0498-<slug>`, `Task: T-0498` trailer, size cap, test rules D12, list-assertion rule D21), §8 (runtime acceptance items, D22).
- `CLAUDE.md` (rules; "미결은 발명하지 않는다"; A-13 BLOCKED reasons; test rules; language policy).
- `ARCHITECTURE/decisions/ADR-0177-od18-od6-contract-table.md` decisions 1 and 3 (all of it: dimensions, seed/draws/tolerance, the judge, "What the operations are handed", the result as the owner answered HQ-0077, "Read here", "What a result does not say") and 5.
- `ARCHITECTURE/decisions/ADR-0042-od18-correctness-check-result-members.md` decisions 2–5 and 7; `ARCHITECTURE/decisions/ADR-0043-od18-correctness-check-operation-form.md` decisions 2 and 4–5; `ARCHITECTURE/decisions/ADR-0044-od18-correctness-check-mock-script.md` decisions 2–4 (and ADR-0038 decision 6 as ADR-0177 cites it).
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md` decisions 1–3, 7–10 (the program arguments, the report, the judge, verdict classes).
- Code: `hilclaw/check_parameters.py`, `hilclaw/check_result.py`, `hilclaw/check_judging.py`, `hilclaw/check_answer.py`, `hilclaw/check_operation.py`, `hilclaw/mock_check.py`, `hilclaw/check_seed.py` (how `CheckParameters` is built today; read only), `hilclaw/harness/bf16_verification.py` (`program_arguments`, `judge_report`), `hilclaw/harness/bf16_verification_arrays.py`, `hilclaw/harness/verification.py` (`Judgement`, `Broken`, `Verdict`, `END_MARK`), `hilclaw/contract_table.py` (the key and `task_contract` parameter order), `hilclaw/{gemm,rmsnorm,elementwise_add,swiglu}_bf16_contract.py` (`task_contract` parameters).
- Tests: the test files of the six touched modules, `tests/test_check_definition.py::test_building_the_default_registry_imports_no_numpy` and the other two `..._imports_no_numpy` tests there (must stay green).

## Acceptance Criteria

1. **Check parameters for a bf16 kind** (ADR-0177 decision 3, "What the operations are handed"): a Python form that holds exactly the seed, the number of draws, the table key's `kind` and `dtype`, and the dimensions in the order of the kind's `task_contract` parameters (`m`, `k`, `n` for `gemm`; `m`, `n` for `rmsnorm`, `elementwise_add`, `swiglu`). Whether it is a widened `CheckParameters` or a second type is the executor's choice, stated in Result; in either case **an fp32 `gemm` operation receives exactly what it receives today** (`seed`, `draws`, `m`, `k`, `n`), and every existing caller of `CheckParameters` keeps working unchanged.
2. **The result** (ADR-0177 decision 3 as HQ-0077 answered it, "Read here"): `hilclaw.check_result` builds the result of a completed and of a broken bf16 check with ADR-0042's member list, `shape` holding the stated record's shape members of its kind (each an integer ≥ 1), `counts` entries with exactly `failed` and `non_finite`, the bound "`failed` ≤ m·n" read as "≤ the number of output elements of the kind" (m·n for all four kinds here). The result holds no `kind`, `dtype` or `layout`. The fp32 `gemm` functions and their results are unchanged. `sdpa_kv_cache` (`cache_differs`) is not built here.
3. **The judge** (ADR-0177 decision 3, "The judge"): a report of a bf16 check of one of the four kinds is judged by `hilclaw.harness.bf16_verification.judge_report` with the kind and the dimensions, and its `Judgement` becomes the result of criterion 2 through `hilclaw.check_judging` (the verdict classes and conditions as for fp32). A condition string (ADR-0060 decision 4) becomes a broken result with the bf16 `shape`. The fp32 path is unchanged.
4. **The operation call** (`hilclaw.check_operation.ask`): hands the bf16 parameters to the operation as they are and judges its answer by criterion 3. For fp32 parameters nothing changes.
5. **The mock** (ADR-0177 decision 3, "The mock"; ADR-0044): the mock's operation accepts the bf16 parameters, and its default script, for a bf16 entry, writes the report of ADR-0163 decision 8 for a conforming kernel of that contract from the harness's own arrays modules (`bf16_verification_arrays`), so that the judge passes it under any tolerance the calibration admits; a test script can still stand for any other kernel. Building the default registry still imports no NumPy (the three `..._imports_no_numpy` tests of `tests/test_check_definition.py` stay green).
6. **Not reachable from the tool yet**: nothing in `check_seed`, `check_admission`, `check_tool`, `check_identity`, `contract_table` or the registry changes; through the default registry every answer of `correctness.check` is the same as before. State this in each touched module's docstring only where it names its callers.
7. **Tests** (D12): for each of the four kinds — happy: the mock's default script's report judged pass, at the smallest shape and one larger shape; branch: a test script standing for a kernel that writes one wrong element (fail with that draw's `failed` = 1), a non-finite output (`non_finite`), each condition string (broken with the bf16 `shape`); negative: parameters of an unknown kind or dtype, a dimension that is a `bool`, zero or missing, the wrong number of dimensions for the kind, `failed` above the kind's output elements, a malformed report (broken `report_form`), a wrong check value (broken `check_value`). The fp32 tests of these modules pass unchanged except the list pins of criterion 8. Package line and function coverage stay at or above 80 %, ruff is clean, the full local suite passes on Linux/WSL with clang; CI is green.
8. **D21 list pins** foreseen: `tests/test_check_parameters.py::test_the_fields_are_the_five_in_their_order` (only if the executor widens `CheckParameters`) and `::test_the_module_has_the_type_and_imports_typing_only`; `tests/test_check_result.py::test_public_names_of_the_module` and `::test_module_imports_the_standard_library_only_and_has_no_entry`; `tests/test_check_judging.py::test_module_imports_the_builder_and_the_judging_only_and_has_no_entry` and `::test_public_names_of_the_module_and_no_default`; `tests/test_check_answer.py::test_module_imports_the_judging_and_the_builder_only_and_has_no_entry` and `::test_public_names_of_the_module_and_no_default`; `tests/test_check_operation.py::test_module_imports_the_three_only_and_has_no_entry` and `::test_public_names_of_the_module_and_no_default`; `tests/test_mock_check.py::test_the_module_imports_the_harness_and_the_type_only_and_has_no_entry` and `::test_public_names_of_the_module_and_no_default`. Other existing assertions stay unchanged. List each edited assertion in the PR body.
9. **No record changes.** If the work shows that ADR-0177 decision 3 does not settle something this task needs (for example how the mock's default script derives its report for a kind), do not invent it: return BLOCKED with the question (DRIVER §3 BLOCKED reasons).
10. **Result** names: the language choice and reason (Python), the parameter form chosen, the PR, review rounds, edited list pins, and any runtime acceptance item (expected none).

## Out of Scope

- The `step` values, the read of ⓢ, admission per kind, the seed step, `layout.BUILD_LOG_STEPS` (T-0499).
- The readers `checks.read`, `verdicts.write`, `spec_feedback` (T-0500).
- The `cpu_standin` operation and its time limits; the `checked` flags of `hilclaw/contract_table.py`.
- `sdpa_kv_cache` (`cache_differs`), `rope` (ADR-0177 decision 5 items 2 second part and 3); the bf16 timing run; the instance start; the executor binding.
- Any deferred line of PLAN "보류". Starting `claude`, real weights, a board, an API key (D16).

## Follow-ups

## Result
