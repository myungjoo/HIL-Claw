---
id: T-0501
title: Build correctness.check of bf16 sdpa_kv_cache up to the mock — the HQ-0077 result with cache_differs, the ADR-0165 judge, admission and parameters, and the mock's default script (ADR-0177 slice 2, second part, without cpu_standin)
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, FR-10, OD-18, OD-31, "PLAN P2-11", "PLAN P2-14"]
dependsOn: []
touchesFiles:
  - hilclaw/check_result.py
  - hilclaw/check_judging.py
  - hilclaw/check_answer.py
  - hilclaw/check_operation.py
  - hilclaw/check_parameters.py
  - hilclaw/check_admission.py
  - hilclaw/mock_check.py
  - tests/test_check_result.py
  - tests/test_check_judging.py
  - tests/test_check_answer.py
  - tests/test_check_operation.py
  - tests/test_check_parameters.py
  - tests/test_check_admission.py
  - tests/test_mock_check.py
  - tests/test_check_tool.py
estimatedSize: {loc: 240, files: 7}   # non-test: check_result ~70, check_judging ~50, check_answer/check_operation ~40, check_parameters ~10, check_admission ~15, mock_check ~55. Tests are outside the cap (DRIVER §5, D4/D20).
hq: []
---
## Why

**State.** PLAN P2-14 (Llama 3.2 1B end-to-end, the D18 goal) needs an instance per P2-11 operation, and the instance start admits a contract only once it is both `checked` and `timed` (ADR-0177 decision 2). ADR-0177 decision 5 item 2 makes `correctness.check` serve bf16 `gemm`, `rmsnorm`, `elementwise_add`, `swiglu` and `sdpa_kv_cache`, and allows cutting it "the five kinds of ADR-0163 first, `sdpa_kv_cache` second". T-0498 (module level), T-0499 (tool level) and T-0500 (readers, ADR-0178) built the first four kinds up to the mock. `sdpa_kv_cache` is still refused: `check_result.BF16_KINDS` holds the four kinds only, and `check_admission` answers a bf16 kind outside it `op_signature_not_covered` whatever the predicate says (T-0499 Follow-ups, reviewer Nit 3 of PR #312).

**What this task does.** The `sdpa_kv_cache` counterpart of T-0498 and of the admission part of T-0499, with no new decision: the result form is the owner's (HQ-0077, quoted in ADR-0177 decision 3 — each `counts` entry of an `sdpa_kv_cache` check gains `cache_differs`, and pass/fail is judged over `failed` and `cache_differs`), the judge is ADR-0165's Python side (`hilclaw.harness.bf16_sdpa_kv_cache_verification`), and the mock's default script is ADR-0177 decision 3's ("a conforming kernel … from the harness's own arrays modules"). The `cpu_standin` operation, its time limits and the `checked` flags are the next task (T-0502), which needs a record on the time limits; doing this part first keeps T-0502 free of any decision this task would make.

**Size.** Under half the cap (DRIVER §6 "task 단위" ③). It cannot be merged with T-0502: together they would touch about 13 non-test files (the ADR and three registers included), over the 10-file cap.

**PLAN order and D18.** P2-11 and P2-14 are PLAN checklist items; D18 does not apply. Items before them in the P2 order: P2-10 waits on HQ-0076 (T-0493); P2-1 to P2-7 have no open work the last planners found before P2-5, which is checked. No RuntimeAcceptance `실패` item exists as of `main` `00560812`.

**D16.** Everything is verified with tests in this repository; nothing starts `claude`, needs a board, a container runtime or real Llama weights.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task format, naming `claude/T-0501-<slug>`, `Task: T-0501` trailer, size cap, test rules D12, list-assertion rule D21), §8 (runtime acceptance items, D22).
- `CLAUDE.md` (rules; "미결은 발명하지 않는다"; A-13 BLOCKED reasons, in particular "데이터 plane 스키마 변경"; test rules; language policy).
- `PROCESS/tasks/T-0498-bf16-check-parameters-result-judging-mock.md`, `PROCESS/tasks/T-0499-bf16-check-step-values-and-admission.md` and `PROCESS/tasks/T-0500-bf16-check-lines-readers.md` (their Results and Follow-ups — the form this task follows).
- `ARCHITECTURE/decisions/ADR-0177-od18-od6-contract-table.md` decision 3 (all of it, in particular the HQ-0077 answer, "Read here" and "Pass and fail of an `sdpa_kv_cache` check") and decision 5.
- `ARCHITECTURE/decisions/ADR-0165-od31-bf16-sdpa-kv-cache-verification-run.md` decisions 3, 8, 10 and 11; `ARCHITECTURE/decisions/ADR-0042-od18-correctness-check-result-members.md` decisions 4, 5 and 7; `ARCHITECTURE/decisions/ADR-0038-od18-cpu-standin-execution-points.md` decision 6.
- Code: `hilclaw/check_result.py`, `hilclaw/check_judging.py`, `hilclaw/check_answer.py`, `hilclaw/check_operation.py`, `hilclaw/check_parameters.py`, `hilclaw/check_admission.py`, `hilclaw/mock_check.py`, `hilclaw/contract_table.py`, `hilclaw/harness/bf16_sdpa_kv_cache_verification.py`, `hilclaw/harness/bf16_sdpa_kv_cache_arrays.py`.
- Tests: the test files of the touched modules, `tests/test_check_tool.py`.

## Acceptance Criteria

1. **Result.** `check_result` builds the completed and broken results of an `sdpa_kv_cache` check as ADR-0177 decision 3 reads the HQ-0077 answer: `shape` with the five members `m`, `l`, `h`, `h_kv`, `d` in the `task_contract` order; each `counts` entry `{"failed", "non_finite", "cache_differs"}`, `cache_differs` an `int` ≥ 0 bounded by the number of cache elements over both allocations (ADR-0165 decision 8), `failed` bounded by the number of output elements of the kind; the outcome `fail` iff some `failed` or some `cache_differs` is ≥ 1. The four kinds of T-0498 and fp32 `gemm` give exactly the results they give today. The Python form (widening `bf16_completed`/`bf16_broken` and `BF16_KINDS`, or a separate function) is this task's; name it in Result.
2. **Judge.** `check_judging` judges an `sdpa_kv_cache` report with `bf16_sdpa_kv_cache_verification.judge_report` and turns its judgement into the result of criterion 1, with the same consistency checks as `_from_judgement` (a verdict that disagrees with the counts is refused). `check_answer` and `check_operation.ask` route an `sdpa_kv_cache` answer there; fp32 `gemm` and the four kinds are unchanged.
3. **Admission and parameters.** `check_admission` and `check_parameters` admit a covered `sdpa_kv_cache` record (dimensions in `task_contract` order) when the predicate answers `True`; `rope` stays refused `op_signature_not_covered` whatever the predicate says. `check_covers` is not changed and the `checked` flag of the `sdpa_kv_cache` entry stays `False` (T-0502), so the registered tool still refuses the record; reach the new path with a test-bound predicate, as T-0499's tests do.
4. **Mock.** `mock_check.default_script` answers an `sdpa_kv_cache` check with the report of ADR-0165 decision 8 for a conforming kernel — the output nearest the float64 reference in bf16 (as T-0498 did for the four kinds) and the cache allocations as a conforming kernel leaves them — built from the harness's arrays modules, so the judge passes it under any tolerance the calibration (ADR-0165 decision 10) admits.
5. **No new decision.** If building any of this needs a choice no record makes (for example a member, a bound or an order the HQ-0077 answer and ADR-0165 do not give), stop and return BLOCKED with the question rather than choosing; if it changes the form or meaning of a data-plane member beyond HQ-0077's answer, it is an A-13 "데이터 plane 스키마 변경" — BLOCKED.
6. **Tests** (D12): happy — a pass and a fail result, a completed and broken judgement, an `sdpa_kv_cache` check through `check_tool` with a test-bound predicate on the mock (sim and board points, the bf16 `step` values), the mock's default script passing; branch — fail by `failed` only, by `cache_differs` only, by both; `h` a multiple of `h_kv` > 1 and `h == h_kv`; fp32 `gemm` and the four kinds unchanged; negative — `cache_differs` negative, not an `int`, a `bool`, above its bound; a counts entry of the wrong length; a verdict beside counts of the other outcome; a damaged report; `rope` still refused. Package line and function coverage stay at or above 80 %, ruff is clean, the full local suite passes on Linux/WSL with clang; CI is green.
7. **Existing tests.** D21 list pins foreseen: the public-name and import assertions of `tests/test_check_result.py`, `tests/test_check_judging.py`, `tests/test_check_answer.py`, `tests/test_check_admission.py`, `tests/test_check_parameters.py` and `tests/test_mock_check.py` (for example `test_public_names_of_the_module`, `test_module_imports_the_builder_and_the_judging_only_and_has_no_entry`, `test_the_module_imports_the_harness_and_the_type_only_and_has_no_entry`) and any assertion that pins `BF16_KINDS`. Besides those, a test that uses `sdpa_kv_cache` as *the example* of a bf16 kind the admission refuses may switch its example to `rope` (the refusal it pins stays). Other existing assertions stay unchanged. List every edited assertion in the PR body.
8. **Result** names: the language choice and reason (Python), the PR, review rounds, the form chosen in criterion 1, edited assertions, and any runtime acceptance item (expected none; if any, word it for `PROCESS/RuntimeAcceptance.md`, D22).

## Out of Scope

- The `cpu_standin` operation of any bf16 kind, its time limits, the copy of the bf16 programs and header into the build directory, the `checked` flags of `hilclaw/contract_table.py` (T-0502).
- `rope` (ADR-0177 decision 5 item 3); the bf16 timing run (item 4); the instance start; the executor binding.
- The readers `checks.read`, `verdicts.write`, `spec_feedback` (they do not read `counts` members; if one turns out to, name it in Follow-ups).
- Any ADR or `ARCHITECTURE/` edit. Any deferred line of PLAN "보류". Starting `claude`, real weights, a board, an API key (D16).

## Follow-ups

## Result
