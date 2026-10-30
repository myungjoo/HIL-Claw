---
id: T-0515
title: Land ADR-0181 code slice 4 — the cpu_standin operation for bf16 runs of all six kinds, the limits of decision 6, then the timed flags
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, FR-10, OD-13, OD-14, OD-16, OD-18, OD-31, HQ-0078, "PLAN P2-11", "PLAN P2-14"]
dependsOn: []
touchesFiles:
  - hilclaw/standin_run.py
  - hilclaw/standin_settings.py
  - hilclaw/contract_table.py
  - hilclaw/run_definition.py
  - hilclaw/run_tool.py
  - hilclaw/start_instance.py
  - hilclaw/harness/bf16_timing.py
  - tests/
estimatedSize: {loc: 260, files: 7}   # tests excluded from the cap; one task under DRIVER §6 "task 단위" ③, so the flags never land for only some kinds
hq: []
---
## Why

**State.** ADR-0181 decision 8 item 4 is the last slice of the bf16 timing run: "The `cpu_standin` operation for bf16 runs: the six programs built with the header copy (decision 3), the limits of decision 6 in `standin_settings`, the `rope` rows through the container client (ADR-0180 decision 3) — then the **`timed` flags** of the six entries (ADR-0177 decision 2), after which the instance start admits them with no change of its own."

The six timing programs (T-0512, T-0513) and the tool path on the mock (T-0514) have landed. `hilclaw.standin_run.operation` still refuses `Bf16TimingParameters` with `TypeError`, and every bf16 entry of `contract_table` is `timed=False`.

**Why one task.** Decision 8 item 4 allows cutting this slice in two along the size cap. The whole slice fits the cap well, so DRIVER §6 "task 단위" ③ makes it one task. ADR-0177 decision 2 sets a flag in the slice that makes the tool serve the contract on both backends.

**Why now (PLAN checklist, D24 ⑤).** The D24 freeze was released on 2026-10-30. P2-11 to P2-14 first get a real run with the minimal operation set: the six bf16 instance kinds of ADR-0152 decision 2. The instance start admits a kind only once its entry is `timed`. These are checklist items, so D18 does not apply.

**RuntimeAcceptance.** No item has the status `실패` as of `main` `44b79238`. RA-0052, RA-0053 and RA-0054 already hold ADR-0181's runtime acceptance items, so this slice is not expected to add one.

**D16.** Tests use stub clients and the mock only. They start no `claude`, real Docker daemon, board or real weights.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5. These cover the branch name `claude/T-0515-<slug>`, the `Task: T-0515` trailer in commits and as the last line of the PR body, the size cap, D12 and D21. Also read §8 (D22).
- `CLAUDE.md`: the A-13 code mode, the BLOCKED reasons, the test rules and comment minimisation.
- `PROCESS/tasks/T-0514-run-tools-bf16-on-mock.md`, `## Result`: `Bf16TimingParameters`, the type choice in `run_tool` and the readers search.
- `ARCHITECTURE/decisions/ADR-0181-od13-bf16-timing-run.md`: decision 2 (lines 30-38), decision 3 (40-44), decision 5 (54-56), decision 6 (58-77) and decision 8 (87-95).
- `ARCHITECTURE/decisions/ADR-0177-od18-od6-contract-table.md`: decision 2 (lines 47-60) and decision 5 (90-96).
- `ARCHITECTURE/decisions/ADR-0179-od14-bf16-standin-check-time-limits.md`: the work measure (decision 3), the refusals (decision 7) and the header copy (decision 5).
- `ARCHITECTURE/decisions/ADR-0180-od16-bf16-rope-check-start-position.md`: decisions 1 to 3.
- `ARCHITECTURE/decisions/ADR-0170-od18-standin-run-operation.md`: the keeper and the two builds.
- Code:
  - `hilclaw/standin_run.py`, the whole module.
  - `hilclaw/standin_check.py`: `_bf16_checked` (lines 265-285), `_carry_out` (340-361), `_placed_copies` (364-379) and `run_container` (437-470). These are the model for the bf16 path.
  - `hilclaw/standin_settings.py`: `bf16_verification_process_time_limit_s` and `_limit_s`.
  - `hilclaw/harness/bf16_timing.py`: `program_arguments` and `_rope_rows`.
  - `hilclaw/harness/bf16_timing_build.py`: `PROGRAM_SOURCES`.
  - `hilclaw/harness/bf16_timing.h`: which header it includes.
  - `hilclaw/standin_copies.py`: `place_harness_copy` (lines 177-195).
  - `hilclaw/contract_table.py`: `_ENTRIES` (lines 58-66).
  - `hilclaw/run_parameters.py`: `Bf16TimingParameters`.
  - Docstrings: `hilclaw/run_definition.py` (about line 37), `hilclaw/run_tool.py` (about line 107) and `hilclaw/start_instance.py` (about line 12).
- Tests:
  - `tests/test_standin_run.py` and `tests/test_standin_settings.py`.
  - `tests/test_standin_check.py`: how a bf16 and a `rope` call are tested through a stub client.
  - The assertions listed in criterion 6.

## Acceptance Criteria

1. **Limits** (ADR-0181 decision 6). `hilclaw.standin_settings` gains a function for the process limit of a bf16 timing run, taking the kind, the dimensions and `n_max`.
   - It applies the rule of `bf16_verification_process_time_limit_s` with `c = n_max + 1` and the same work measure. Share the measure; do not copy it.
   - Its refusals are that function's, with `n_max` in place of `draws`.
   - A test pins decision 6's table values at `n_max` = 10 within the table's rounding, for example `gemm` (512, 2048, 8192) → 978.0 s, `rope` (2048, 32, 64) → 25.8 s, and `gemm` (512, 2048, 128256) → the cap of 1500 s.
   - The build limit stays `BUILD_TIME_LIMIT_S`. The fp32 functions do not change.
2. **The operation** (ADR-0181 decisions 2, 3, 5 and 6). `hilclaw.standin_run.operation` accepts exactly a `TimingParameters` or a `Bf16TimingParameters`, and still refuses every other type with `TypeError` before anything is started.
   - For a bf16 call:
     - It refuses, before the image is read or anything is made, a `dtype` other than `bf16`, a kind outside the six, and what `bf16_timing.program_arguments` or the limit refuses.
     - It forms the arguments with `bf16_timing.program_arguments`.
     - It copies the kind's program of `bf16_timing_build.PROGRAM_SOURCES` as the harness, then both headers the program needs (`bf16_timing.h`, `bf16_verification.h`), handed to the compiler as no source, then the waiter.
     - It builds the program first, then the compiled set, with `FLAGS`, `TRAILING_FLAGS` and the shared build limit.
     - It runs `waiter <timing executable> <arguments>` as today and reads it with `read_timing_process`.
   - For `rope`:
     - It computes the rows of the timing seed's start position once, before anything is started, as `bf16_timing.run_bf16_timing` and `standin_check._bf16_checked` do.
     - It hands the rows to `run_container` as `stdin_data`. No build container gets an input.
     - A position the table cannot have raises before anything is started. Whether to make `bf16_timing._rope_rows` public or to call the two modules directly is this task's choice.
   - For `sdpa_kv_cache`, `swiglu` and the others nothing kind-specific is added.
   - The seed stays only among the process's arguments (ADR-0108 decision 4).
   - The fp32 path is unchanged, byte for byte in its containers, arguments and answers.
3. **The flags** (ADR-0177 decision 2). All six bf16 entries of `contract_table._ENTRIES` become `timed=True`. No binding of a place changes. `run_covers` and `start_covers` then answer `True` for each bf16 contract, so the registered `sim.run` / `board.run` and the instance start admit them with no change of their own.
4. **Docstrings.** Update those that this makes false:
   - `standin_run`: the refusal of a bf16 type, the step list, and the sentence that it imports no NumPy if it no longer holds as written;
   - `run_definition`, `run_tool` and `start_instance`: any "fp32 `gemm` alone" or "until a bf16 timing run exists".
5. **Tests** (D12: happy, error, branch and negative cases, every public function of the touched modules, coverage of at least 80 % for lines and for functions).
   - For each of the six kinds, through the stub client, `standin_run.operation`:
     - starts three containers in order, with the right program and header copies in the build directory, the program first in the compile command, and the kind's arguments on the timing process's command line;
     - returns `(report, figure)` from a stub waiter's line.
   - `rope` hands exactly the rows of `start_position(dims, seed=seed)` to the process container and none to a build container, for m ≥ 2 and for m = 1 at an even and an odd seed. The other kinds hand none.
   - Negative cases, each with no container started and no build directory left:
     - a wrong `dtype`;
     - a kind outside the six;
     - a wrong `dims` length;
     - odd `d` for `rope`;
     - `l < m` for `sdpa_kv_cache`;
     - a wrong type for the parameters or the keeper.
   - Failure answers at a bf16 call, as for fp32: a timing build `build_time_limit` and `build_exit_status`, a missing executable, a process `time_limit` and `exit_status`. The keeper is handed the timing build's log only.
   - Through the registered tools at the `cpu_standin` entry with a stub client, or the mock if the entry cannot be reached that way: a bf16 call of each kind yields a v2 result with the kind's `contract_key` and `shape`.
   - A clang-backed test where clang is available: one small bf16 timing program with a kernel, built and started through a stub `docker` that runs the program on the host, as `tests/first_run_stubs.py` does. Name the kind you pick in the PR.
6. **Existing tests.** The flags end what these assertions pin. They are this task's change and are rewritten to the new truth, each keeping a negative case with a record that is still not covered (for example an fp16 or fp64 record):
   - `tests/test_contract_table.py`, about line 86 (`(found.checked, found.timed) == (True, False)` for the bf16 entries) and about line 180 (`start_covers(fp32) and not start_covers(bf16)`);
   - `tests/test_check_admission.py`, about lines 707-708 (`rope` not `run_covers`, not `start_covers`);
   - `tests/test_run_admission.py`, about lines 515-516 and 531-534;
   - `tests/test_run_definition.py`, about lines 1068-1087 (`test_a_bf16_record_is_not_covered_by_the_run_tools`);
   - `tests/test_run_tool.py`, about line 879 (`test_a_bf16_kind_is_refused_where_the_predicate_is_run_covers`);
   - `tests/test_start_instance.py`, about lines 568-588 (`test_a_bf16_record_is_out_of_scope_of_the_start`);
   - `tests/test_standin_run.py`: the test T-0514 added that refuses `Bf16TimingParameters`.

   List assertions may also be edited (D21), for example the public names of `standin_settings` or `bf16_timing`, and any import pin in `tests/test_standin_run.py`. Any other pinned sentence that the flags make false and this list does not name may be rewritten the same way. No other existing assertion changes. List every edited assertion in the PR body.
7. **No record edits.** No file under `ARCHITECTURE/` changes, and no new ADR is written. A design question that no record answers is a BLOCKED reason (DRIVER §3). The Result names the sentences that become less exact, starting with ADR-0177 decisions 4 and 5 item 4 and Boundaries.
8. **Result** records:
   - the language (Python) and the reason;
   - the files changed;
   - the edited assertions;
   - runtime acceptance items (none expected; RA-0052 to RA-0054 become checkable once this lands);
   - whether PLAN P2-11 is now complete in the executor's reading, so that the driver can set its checkbox;
   - the next candidate, T-0516.

## Out of Scope

- The end-to-end run of a bf16 instance through stub `claude` and the generation from its kernels (T-0516).
- Any change to the timing programs or `hilclaw/harness/timing.py`, except a public name for the `rope` rows if chosen under criterion 2.
- The fp32 model executor path and other PLAN hold items.
- Widening the nightly run configuration. That is D17 (가), the owner's value, through DRIVER §8.
- Owner-only values (tolerances, `n_min`, `cv_max`, the seed source, the number of draws). fp16. OpenMP (HQ-0034).
- Starting `claude`, a real Docker daemon, a board, real weights or an API key (D16). No test run (D25) is needed.

## Follow-ups

## Result
