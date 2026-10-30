---
id: T-0514
title: Land ADR-0181 code slice 3 — sim.run / board.run take a bf16 run on the mock (per-kind timing parameters beside the unchanged TimingParameters, operations asked with either, v2 result of the kind), still with no timed flag
phase: P2
status: TODO
commitMode: code
coversReq: [C-6, FR-9, FR-10, OD-13, OD-18, OD-31, HQ-0078, "PLAN P2-11", "PLAN P2-14"]
dependsOn: [T-0512, T-0513]
touchesFiles:
  - hilclaw/run_parameters.py
  - hilclaw/run_operation.py
  - hilclaw/run_tool.py
  - hilclaw/run_admission.py
  - hilclaw/run_definition.py
  - hilclaw/mock_run.py
  - hilclaw/standin_run.py
  - tests/
estimatedSize: {loc: 220, files: 6}   # ADR-0183 decision 9 item 4 reduces ADR-0181 item 3 to admission, per-kind parameters and the mock; tests excluded from the cap
hq: []
---
## Why

**State.** This task is **ADR-0181 decision 8 item 3**: "The run tools for bf16 on the mock: admission and the parameters per kind (decision 4), the v2 result of a bf16 run (decision 7) where the v2 code does not already produce it for a non-`gemm` kind, and the readers of run lines where they read only `m`, `k`, `n`; the mock's default script unchanged for bf16 calls (decision 9). No `timed` flag yet." ADR-0183 decision 9 item 4 narrows it. The v2 builder of T-0511 (`run_result.completed` / `broken`, which take any covering entry) already gives the v2 result of a bf16 run. What is left is the admission, the parameters per kind and the mock. The follow-up of T-0511 (review round 2, Nit 5) belongs here too: `run_tool._perform` unpacks `m, k, n = admitted.dims` into `TimingParameters`. That holds only while `run_covers` admits fp32 `gemm` alone.

**Order.** ADR-0181 decision 8 gives the landing order 1, 2, 3, 4. This slice does not use the code of T-0512 or T-0513, because the run tool judges every report through `hilclaw.harness.timing.judge_report`. It follows them in that order. All three were planned in one batch (D20 ④).

**Why now (PLAN checklist, D24 ⑤).** The D24 freeze was released on 2026-10-30. P2-11 to P2-14 first get a real run with the minimal operation set: the six bf16 instance kinds of ADR-0152 decision 2. The instance start admits a kind only once its entry is `timed`. Slice 4 sets those flags, and it needs this slice's tool path. These are checklist items, so D18 does not apply.

**RuntimeAcceptance.** No item has the status `실패` as of `main` `b7e65818`. This slice adds no item.

**D16.** Tests use the mock backend and stubs only. They do not use `claude`, Docker, a board or real weights.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5. These cover the branch name `claude/T-0514-<slug>`, the `Task: T-0514` trailer in commits and as the last line of the PR body, the size cap, D12 and D21. Also read §8 (D22).
- `CLAUDE.md`: the A-13 code mode, the BLOCKED reasons, the test rules and comment minimisation.
- `PROCESS/tasks/T-0511-run-tools-v2.md` `## Result` and `## Follow-ups`. They cover the `Admitted` fields `(entry, dims, n_max, sample_form, bound)`, the builders and Nit 5.
- `ARCHITECTURE/decisions/ADR-0181-od13-bf16-timing-run.md`: decision 1 (lines 25-28), decision 4 (46-52), decision 7 (79-85), decision 8 (87-95), decision 9 (97-99) and the A-13 reading (101-107).
- `ARCHITECTURE/decisions/ADR-0183-od18-tool-result-format-v2.md`: decision 4 (the v2 run result) and decision 9 item 4 (about line 159).
- `ARCHITECTURE/decisions/ADR-0065-od18-run-tools-operation-form.md`: decision 2 (lines 33-54) and decision 4 (64-76).
- `ARCHITECTURE/decisions/ADR-0066-od18-run-tools-mock-script.md`: decisions 3 to 5 (lines 44-79).
- `ARCHITECTURE/decisions/ADR-0177-od18-od6-contract-table.md`: decision 2 (lines 47-61) and decision 3 (62-80), which is the manner of `Bf16CheckParameters`.
- Code:
  - `hilclaw/run_parameters.py` (53 lines).
  - `hilclaw/check_parameters.py`, mainly `Bf16CheckParameters`, the model for the new type.
  - `hilclaw/run_operation.py`, mainly `ask` (about lines 203-280), which today refuses all but `TimingParameters`.
  - `hilclaw/run_tool.py`: the module docstring (about lines 95-110) and `_perform` / `_result` (about lines 242-305).
  - `hilclaw/run_admission.py`, mainly `admit`, `Admitted` and `_entry`.
  - `hilclaw/run_definition.py`: the docstring and the `covers=contract_table.run_covers` binding (about line 221).
  - `hilclaw/mock_run.py`, mainly `default_script`.
  - `hilclaw/standin_run.py`, mainly `operation` and `_checked`, which today refuse anything but `TimingParameters`.
  - `hilclaw/contract_table.py`: `run_covers`, `covers` and `task_contract`.
  - `hilclaw/check_tool.py` / `hilclaw/check_admission.py`: how the check side picks the parameters type per entry.
- Tests: `tests/test_run_parameters.py` (public names, about line 93), `tests/test_run_operation.py` (the parameters type refusal; public names, about line 595), `tests/test_run_tool.py`, `tests/test_run_admission.py`, `tests/test_run_definition.py`, `tests/test_mock_run.py` and `tests/test_standin_run.py`.

## Acceptance Criteria

1. **Per-kind timing parameters** (ADR-0181 decision 4). `hilclaw.run_parameters` gains a type for a bf16 run, in the manner of `Bf16CheckParameters`. It holds the `kind` and `dtype` of the covering entry, `dims` in `task_contract` order, `n_max`, `sample_form` and `seed`. The name and field order are this slice's. `TimingParameters` is unchanged, and the operations of fp32 `gemm` keep receiving exactly a `TimingParameters`.
2. **The tool path.**
   - `hilclaw.run_tool` builds `TimingParameters` for the fp32 `gemm` entry and the new type for any other covering entry. The choice comes from the entry, as on the check side. Nit 5's unpacking is gone.
   - `hilclaw.run_operation.ask` accepts exactly either type and still refuses every other type with `TypeError` before the operation is called.
   - `hilclaw.run_admission` keeps admitting through the `covers` it is handed. It changes only if it needs to for the per-kind parameters.
   - The v2 result of a bf16 run is that of `run_result.completed` / `broken` with the kind's `contract_key` and `shape`. The `step` values are `sim_run_timing_v2` / `board_run_timing_v2`, the same for every kind.
   - Search `hilclaw/` for readers of run lines that read only `m`, `k` and `n`, and fix any found. Name the result of the search in the Result.
3. **Bound predicate unchanged.** `run_definition` still binds `contract_table.run_covers`, and no `timed` flag changes. So the registered `sim.run` / `board.run` still refuse every bf16 record with `op_signature_not_covered`. A bf16 run is reachable only through `run_tool.tool_function(..., covers=...)` given a predicate that admits it, for example `contract_table.covers`. Docstrings that say "fp32 `gemm` alone" are updated to say what is now true: admitted only once `timed`.
4. **The mock** (decision 9). `mock_run.default_script` is unchanged and answers a bf16 call as it answers any call. Only docstrings may change.
5. **`cpu_standin`.** `standin_run.operation` refuses the new type before anything is started, as it refuses every non-`TimingParameters` today, and its docstring names the refusal. The bf16 operation is slice 4's. If a docstring-only change is not needed, leave the file untouched.
6. **Tests.** They follow D12: happy, error, branch and negative cases, every public function of the touched modules, and coverage of at least 80 % for lines and for functions.
   - For each of the six bf16 kinds, `tool_function` for `sim.run` and `board.run` on the mock, with `covers=contract_table.covers`, appends a `step_ended` line under the v2 value. Its v2 `result` holds the kind's `contract_key` and `shape` (for example `rmsnorm` `{m, n}` and `sdpa_kv_cache` `{m, l, h, h_kv, d}`), `outcome` `converged`, `unit` `ns`, and no `memory_bytes`.
   - The operation is handed the new type with the right `kind`, `dtype` and `dims` order (a recording script).
   - fp32 `gemm` is still handed `TimingParameters`, and its results are unchanged.
   - A script that answers a broken condition for a bf16 call gives a broken v2 result with the kind's `shape`.
   - The registered tools (`run_covers`) refuse a bf16 record with `op_signature_not_covered`.
   - `ask` refuses a third type, such as `Bf16CheckParameters` or a tuple, with `TypeError`.
   - `standin_run.operation` refuses the new type with `TypeError` before any container or build.
7. **Existing tests.** Assertions that pin the old single-type contract are rewritten as this task's change: `ask` refusing everything but `TimingParameters`, and `_perform`'s three-member unpacking. List assertions may be edited (D21). The ones foreseen are:
   - `tests/test_run_parameters.py` public names: `{"TimingParameters"}` becomes the two names;
   - `tests/test_run_operation.py::test_public_names_of_the_module_and_no_default`, if the names or imports change;
   - import and public-name pins in `tests/test_run_tool.py` and `tests/test_run_admission.py`, if they change.
   No other existing assertion changes. List every edited assertion in the PR body.
8. **No record edits.** No file under `ARCHITECTURE/` changes. The Result names sentences that become less exact. Candidates are ADR-0065 decision 2's "exactly these six values" and `run_parameters`' docstring, which this task updates.
9. **Result** records:
   - the language (Python) and the reason;
   - the new type's name and fields;
   - the files changed;
   - the readers search;
   - the edited assertions;
   - runtime acceptance items (none expected);
   - the next candidate, ADR-0181 decision 8 item 4 (the `cpu_standin` bf16 operation, the limits, the `rope` rows through the container client, the header copies, then the `timed` flags). It may be split as decision 8 item 4 allows.

## Out of Scope

- The `cpu_standin` operation for bf16 runs, `standin_settings` limits, header copies into the container, the `rope` rows through `standin_check.run_container` and the `timed` flags (slice 4).
- Any change to `hilclaw/harness/` (T-0512 / T-0513) or to the check side.
- Widening the nightly run configuration. That is D17 (가), the owner's value, through DRIVER §8.
- Owner-only values. fp16.
- Starting `claude`, a real Docker daemon, a board, real weights or an API key (D16).

## Follow-ups

## Result
