---
id: T-0578
title: PLAN P3-16 (6a) — ADR-0207 slice 6, first half: ADR-0208 records HQ-0104 (a) (a `.cu` attempt file and the `given.cu` bundle at `cuda_gpu`, the reading of an absent candidate kind there, and the rest of slice 6), with the reader of an attempt's `output/` and the placement of given code made target-aware
phase: P3
status: DONE
commitMode: code
coversReq: [D31, "PLAN P3-16", "ADR-0207", "HQ-0104", "HQ-0096", FR-10, FR-19, OD-33, OD-23]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0208-od33-cuda-kernel-record-in-a-run.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
  - hilclaw/kernel_source.py
  - hilclaw/given_attempt.py
  - hilclaw/instance.py
  - hilclaw/cuda_check.py
  - tests/test_kernel_source.py
  - tests/test_given_attempt.py
  - tests/test_instance.py
  - tests/test_cuda_check.py
estimatedSize: {loc: 420, files: 8}
hq: []
---
## Why

**PLAN P3-16** (line ~80) asks to show on this PC's GPU that a CUDA `gemm` kernel goes through build, correctness, measurement **and record**. [ADR-0207](../../ARCHITECTURE/decisions/ADR-0207-od33-cuda-target-demonstration.md) decision 5 asked how a CUDA kernel is recorded in a run, and decision 9 left **slice 6** until the answer.

The owner answered **HQ-0104 (a)** on 2026-11-15 (its `decision` in `PROCESS/STATE.json`). In short:

- At `cuda_gpu` only, an attempt's `output/` also admits names ending in `.cu`, and the compiled set there is the `.cu` files (`.c` is admitted but not compiled; ordering, size and count rules unchanged).
- At `cuda_gpu` the given-code bundle is one CUDA C++ file placed as `given.cu`.
- The run's `instance.json` is written as today, without `candidate_kind`; that absence is read as "a kernel in the target's contract language (`cuda`)" — a changed reading of an existing value.

The `decision` also carries integrator readings (not the owner's words) that this task takes as written:

- `instance.json`'s form and version do not change.
- What changes is ADR-0055 N1/R3 (at `cuda_gpu`), ADR-0200 decision 2's bundle (at `cuda_gpu`) and the reading of an absent kind.
- **"그 기록은 slice 6의 task가 §9 ADR로 적는다"**: the record is this task's ADR.
- Whether the version-3 reader keeps returning the name `c_kernel` for such a run is slice 6's question.

This is an owner-approved frame change (A-13; D23), so it is **not** a BLOCKED reason. The task only writes it down and implements its first code slice (D20 ①).

**Split.** Slice 6 touches more than ten non-test files with its ADR, so it is split in two:

- **This task**: the ADR, plus the frame code — the reader of `output/` and the placement of given code.
- **T-0579**: opening `cuda_gpu` (`instance_start`, the start's scope, the given-code command, the default table) and the real-GPU demonstration through `run.commit`.

**Order check (D27 ①)** at planning time (main `57509340`): no open PR, no open `nightly-failure` issue, no `실패` item in `PROCESS/RuntimeAcceptance.md`.

**Brake (D31 ②).** This is the PLAN item's own work, which is exempt. Do not harden existing paths beyond what this slice needs.

**Open HQs (D27 ⑦).** Do not ask again or anticipate:

- HQ-0102 and HQ-0103 (P3-12);
- HQ-0088 ① (c) (the coder's CUDA path);
- HQ-0090 (GPU memory figures);
- #5 B-7.

If an owner-only part appears, write it in `## Result` as an HQ in the DRIVER §8 structure: Korean; the issue; options (a)/(b)… with the executor's recommendation; what it blocks and what it does not. Land the rest and return `DONE` (D27 ⑥). Owner-only parts here are:

- a frame change beyond HQ-0104 (a) — for example a new candidate-kind value or an `instance.json` version change;
- a multi-file bundle or the bundle's own build settings (ADR-0200 decision 2, unchanged).

## Required Reading

- `PROCESS/DRIVER.md`:
  - **§3-5 and §5**: branch `claude/T-0578-<slug>`, the `Task: T-0578` trailer and the PR body's last line, size D30, tests D12, list assertions D21, and **storage D29** (temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0578/`).
  - §6 lines **D27 ⑥ ⑦**, **D29** (toolchain: "task가 요구하는 벤더 툴체인이 있는지는 planner가 아니라 executor가 코드를 쓰기 전에 머신에서(넣어 둔 이미지 포함) 확인한다"; FR-19 ⑤ test skipping) and **D31**.
  - §8 and §9.
  - §3 (D23): the approved open lists and what a frame change is.
- `PROCESS/PLAN.md` P3-16 (line ~80).
- `PROCESS/STATE.json` `humanQuestions`: **HQ-0104** (the whole `decision`), HQ-0096 (② (a) and its addition), HQ-0089 (③ ④) and HQ-0088 (① and ②).
- ADRs:
  - [ADR-0207](../../ARCHITECTURE/decisions/ADR-0207-od33-cuda-target-demonstration.md): all, especially decisions 3, 5 and 9 (slice 6).
  - [ADR-0055](../../ARCHITECTURE/decisions/ADR-0055-od23-coder-output-form.md): decisions 3 (R1 to R8) and 5 (N1, N2), and L2.
  - [ADR-0200](../../ARCHITECTURE/decisions/ADR-0200-od33-given-code-evaluation.md): decisions 2, 5, 6 and 7 (the reader table).
  - [ADR-0198](../../ARCHITECTURE/decisions/ADR-0198-od32-compile-settings-candidate-kind.md): decisions 4 and 8.
  - [ADR-0197](../../ARCHITECTURE/decisions/ADR-0197-od32-virtual-npu-oracle-and-instance-start.md): decision 1, as the precedent of widening ADR-0076 decision 1.
  - [ADR-0076](../../ARCHITECTURE/decisions/ADR-0076-od8-instance-start-required-members.md): decision 1.
  - [ADR-0201](../../ARCHITECTURE/decisions/ADR-0201-od33-given-code-run-fresh-directory.md): decision 2.
- Recording rules, to be followed rather than copied from earlier tasks:
  - `ARCHITECTURE/Requirements.md` register **"행 형식"** (line ~85);
  - `ARCHITECTURE/OpenDecisionProposals.md` header **"기록 규칙"** (line ~8) and § OD-33 (line ~657);
  - `ARCHITECTURE/StandardScenarios.md` the first paragraph of **§검사 결과** (line ~188).
- Code:
  - `hilclaw/kernel_source.py` (`is_admitted_name`, `read_compiled_set`), and its callers `hilclaw/bring_in.py`, `hilclaw/build_record.py`, `hilclaw/standin_copies.py` and `hilclaw/attempt_kernel.py`;
  - `hilclaw/given_attempt.py` (`GIVEN_NAME`, `place`);
  - `hilclaw/instance.py` (`CANDIDATE_KINDS`, `read_given`/`parse_given`, `Given`, `candidate_kind_of`);
  - `hilclaw/check_tool.py` and `hilclaw/run_tool.py` (`_EVALUATED_KINDS`, `_C_KERNEL` and the given-code refusal), `hilclaw/run_file_tools.py` (`c_kernel_only`), `hilclaw/spec_tool.py`;
  - `hilclaw/cuda_check.py` (`operation_for(target, *, sources)`, `select_sources`), `hilclaw/targets.py` (`cuda_gpu`, `coder_loop`).
- `PROCESS/tasks/T-0577-cuda-gpu-operations-in-containers.md` `## Result`.

## Acceptance Criteria

1. **ADR-0208** (`ARCHITECTURE/decisions/ADR-0208-od33-cuda-kernel-record-in-a-run.md`), accepted under DRIVER §9. Status names three kinds of content:
   - the owner's (HQ-0104 (a), cited by id and not restated);
   - the integrator's readings in that `decision`, cited;
   - the ADR's own.

   It decides:
   1. **Names and compiled set at `cuda_gpu`.** ADR-0055 N1 and R3 are amended for `cuda_gpu` only: `.cu` names are admitted, and the compiled set is the `.cu` files. `.h` stays the header suffix, `.c` is admitted but not compiled, and N2, R1, R2 and R4 to R8 are unchanged. Other targets are unchanged.

      The ADR also decides **how the reader learns the target**, for example:
      - a parameter of `read_compiled_set` and `is_admitted_name`;
      - or a `Target` member holding the kernel-file suffix.

      State why. A `Target` member is package source, not a data-plane value (ADR-0207 decision 3).
   2. **The bundle.** ADR-0200 decision 2 is amended for `cuda_gpu`: one CUDA C++ file, placed as `given.cu` in the attempt's `output/`. Say how the placement learns the run's target. Multi-file bundles and own build settings stay asked, as ADR-0200 decision 2 says.
   3. **The absent kind.** At `cuda_gpu`, a version-3 `instance.json` without `candidate_kind` means a kernel in the target's contract language. Decide whether the reader (`Given.candidate_kind` and its readers in `check_tool`, `run_tool`, `run_file_tools` and `spec_tool`) keeps returning `c_kernel` for such a run, or returns something else, and why.

      Adding a value to `CANDIDATE_KINDS` is **not** this ADR's (HQ-0104 (b) was not chosen; HQ-0088 ① (c) is not asked again).
   4. **The bring-in.** Whether `hilclaw.bring_in` follows the target-aware names. The coder's path is closed at `cuda_gpu` (`coder_loop` false), so the expected answer is "unchanged"; state it either way.
   5. **The rest of slice 6 for T-0579**, as ADR-0207 decision 9 lists it:
      - `instance_start` true;
      - ADR-0076 decision 1 widened to `cuda_gpu` and the contracts it serves, as ADR-0197 decision 1 did for `virtual_npu`, with `cpu_standin`'s required set;
      - the given-code command at `cuda_gpu`;
      - the `cuda_gpu` backend in the default table, with the compiled-set selection as its `sources`;
      - the demonstration through `run.commit`.

      State these as decisions, so that T-0579 implements them without a new ADR.

   Also give its A-13 reading, Consequences ("Less exact, not edited" sentences of earlier records, if any), Boundaries and the slices (this task's and T-0579's).

   Add a pointer line to ADR-0207 decision 5, and to ADR-0055/ADR-0200 only if those records already carry amendment pointers of the same kind. Change no other sentence of an accepted record.
2. **Register and proposals.** Do not copy the wording of earlier task files for these edits.
   - `ARCHITECTURE/Requirements.md`: one ADR-0208 link added to OD-33's row (and OD-23's if this ADR answers a part of it), with the open part rewritten in place, by the register's "행 형식" rule.
   - `ARCHITECTURE/OpenDecisionProposals.md` § OD-33: one `채택분` line and the status of the sub-questions it answers, rewritten in place by the "기록 규칙".
   - Recheck coverage by the first paragraph of `ARCHITECTURE/StandardScenarios.md` §검사 결과. Record a change there only if a verdict changes.
3. **Code: the reader** (`hilclaw/kernel_source.py`), as ADR-0208 decides:
   - at `cuda_gpu`, `.cu` names are admitted and form the compiled set, with `.h` as headers;
   - every other target's answers, including `NO_COMPILED_FILE` and the reader failures, stay exactly as today;
   - existing callers (`bring_in`, `build_record`, `standin_copies`, `attempt_kernel`) behave byte-for-byte as before unless the ADR says otherwise.
4. **Code: the placement** (`hilclaw/given_attempt.py`). For a run at `cuda_gpu`, the given code is placed as `output/given.cu`, and for other targets as `output/given.c`, exactly as today. The tool's description and its kinds change only as far as the name does.
5. **Code: the reading of the absent kind**, as ADR-0208 decides (`hilclaw/instance.py` and, only if the ADR changes what they read, the tools). If the ADR keeps `c_kernel`, the change is the docstrings that state the reading; behaviour stays the same.
6. **Code: the selection.** Add a `sources` selection for `cuda_gpu` built on the reader, for T-0579 to put in the default table (for example in `hilclaw/cuda_check.py`). Its no-kernel-source and reader-failure answers map to the kinds `check_failure` already uses for `cpu_standin` (ADR-0056 decision 6).

   **Do not register it in the default table** and do not change `targets.py`: that is T-0579's. A `cuda_gpu` call through the default registry stays `no_backend`.
7. **Tests** (D12): happy, error, branch and negative cases for every public function of the touched modules. Cover at least:
   - `.cu` admitted and compiled at `cuda_gpu` and refused at `cpu_standin`/`virtual_npu`;
   - `.c` admitted but not compiled at `cuda_gpu`;
   - a `cuda_gpu` `output/` holding only `.c` is no kernel source;
   - `given.cu` versus `given.c`;
   - the selection's answers.

   Existing tests stay unchanged except list assertions under D21. Foreseen: the public-name pins of `kernel_source`, `given_attempt` and `cuda_check`, and any pinned description text of `given.place`. List each changed assertion in the PR body.

   Verification:
   - the full suite passes, with the real-GPU tests run in WSL2 with the CUDA `bin` on `PATH` if the touched code reaches them;
   - `hilclaw/` line and function coverage ≥ 80%;
   - `ruff check` and `ruff format --check` pass.
8. **Process**:
   - Follow the dev-item-address steps.
   - Open a Draft PR (code mode; the ADR and documents go in the same PR, D20 ①) and run a context-isolated review to Approve (≤ 14 rounds, D28). The review prompt names criterion 1.3 (no new kind value), criterion 6 (no default-table change) and that HQ-0104 (a) is the owner's and not reopened.
   - Once CI is green, self squash-merge with the PR body's last line `Task: T-0578`.
   - In `Result` record:
     - the language and reason;
     - the ADR's choices for 1.1 to 1.4 in one line each (T-0579 reads them);
     - any HQ;
     - any runtime acceptance item (D22).
   - Remove the task directory with `rm -r` (D29).

## Out of Scope

- Anything T-0579 does:
  - `instance_start` true;
  - `start_instance`/`instance_start` scope;
  - `given_eval` at `cuda_gpu`;
  - the default-table entry;
  - the real-GPU demonstration and `run.commit`.
- A new candidate-kind value, an `instance.json` version change, the coder's CUDA path (HQ-0088 ① (c)), `model_run` at `cuda_gpu`, GPU memory figures (HQ-0090), bf16 at CUDA, multi-file bundles.
- Installing anything or pulling any image.
- Starting `claude` in any form (D16), and a test run (D25).

## Follow-ups

## Result

- **Outcome**: DONE. PR #391 (squash-merged; ADR-0208 and slice 6a code in one PR, D20 ①). Review: 1 round, Approve (context-isolated `dev-reviewer`). Two nits followed the Approve. The stale docstring sentence in `kernel_source` was fixed; this is a nit-only change and needs no re-review (D20). The second nit asked to rename the existing test `test_the_module_reads_no_attempt_file_name_and_runs_nothing_on_the_host`. It was not taken, because the task keeps existing tests unchanged beyond D21 list assertions.
- **Language**: Python. All touched modules are Python 2층 code, and the change adds no process or tool.
- **ADR-0208 choices for T-0579**:
  - 1.1: at `cuda_gpu`, `.cu` names are admitted (stem rule of N1 unchanged, so 4 to 65 characters). The compiled set is the `.cu` files; `.c` is admitted but not compiled, and `.h` stays the header suffix. The reader learns the target through the keyword `language` (`"c"` by default, or `"cuda"`) of `read_compiled_set`/`is_admitted_name`. `kernel_source.language_at(accelerator)` gives the one language of the target's contracts, and `"c"` for a name without a target. A `Target` member was not used because it would restate `Target.contracts`.
  - 1.2: at `cuda_gpu` the bundle is one CUDA C++ file placed as `given.cu`. `given.place` takes the `accelerator` from the `instance.json` it already reads (`given_attempt.given_name`). Multi-file bundles and own build settings are still asked.
  - 1.3: a kind-less file keeps reading `c_kernel` at every target, now meaning "a kernel built from the attempt's own `output/` in the target's contract language". No reader or tool changes behaviour, and no `CANDIDATE_KINDS` value is added.
  - 1.4: `bring_in` is unchanged (`language` `"c"`; `coder_loop` is false at `cuda_gpu`). `build_record`, `standin_copies.place_copies` and `attempt_kernel` are also unchanged.
  - 1.5 (decision 5, for T-0579, no new ADR needed):
    - `instance_start` true.
    - ADR-0076 decision 1 widened to `cuda_gpu` with `cpu_standin`'s required set, as ADR-0197 decision 1 did.
    - `given_eval` accepts `cuda_gpu`.
    - Default tables: `correctness.check` by `cuda_check.operation_for(target, sources=cuda_check.compiled_sources)`, and `sim.run`/`board.run` by `cuda_run.operation_for` with the same `sources`; no `profiler.collect`.
    - The demonstration through `run.commit`.
- **Implementation note for T-0579**: `kernel_source.language_at` and `given_attempt.given_name` import `hilclaw.targets` at the first call, not at module import. Building the tool registry must not import `hilclaw.standin_profile`; `test_building_the_default_registry_imports_no_numpy` enforces this.
- **Verification**:
  - Full local suite: 40619 passed, 2372 skipped (Windows host, Python 3.12).
  - `hilclaw/` coverage: line 98.57%, functions 1805/1822 (99.07%); all four touched modules at 100%.
  - `ruff check` and `ruff format --check` pass. CI on PR #391 is green.
  - The touched code reaches no real-GPU test. Toolchain present: WSL2 `nvcc` at `/usr/local/cuda-13.1/bin`, RTX 4070 sm_89.
- **Changed existing assertions (D21)**, both in `tests/test_cuda_check.py`, and listed in the PR body:
  - In the public-name test, `kernel_source` was added to the imported set and `compiled_sources` to the public set.
  - In the no-import test, `kernel_source` was removed from the forbidden import set.
- **HQ**: none.
- **Runtime acceptance items (D22)**: none from this slice. T-0579 states its own.
- **Size**: 9 non-test files. About 300 lines are code and docstrings; the ADR is about 120 lines.
- **Installs and images**: none. The task directory `${TMPDIR:-/tmp}/hilclaw-driver/T-0578/` is removed with `rm -r` at the end.
