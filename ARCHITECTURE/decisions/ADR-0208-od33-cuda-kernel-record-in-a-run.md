# ADR-0208: A CUDA kernel in a run at `cuda_gpu` (the owner's answer HQ-0104 (a)) — the attempt's `output/` admits `.cu` names there and compiles the `.cu` files, the reader learns the target as the language of its contracts, the given-code bundle there is one CUDA C++ file placed as `given.cu`, a file without `candidate_kind` keeps reading `c_kernel`, now meaning a kernel in the target's contract language, the bring-in is unchanged, and the rest of ADR-0207 slice 6 is decided here for its next task (part of OD-33 sub-questions ① and ⑥)

## Status

- **Accepted on 2026-11-15** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor (task T-0578) and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed what this record decides.** The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **Three kinds of content.**
  - **Owner**, cited by HQ id and not restated: **HQ-0104 (a)**, as its `decision` in `PROCESS/STATE.json` states it. It is **not subject to the objection window**.
  - **The integrator's readings**, cited and not this record's: the parts of that `decision` marked "통합자 독해(오너의 말이 아님)" — the `instance.json` form and version do not change; what changes is ADR-0055 N1 and R3 and ADR-0200 decision 2's bundle at `cuda_gpu` and the reading of an absent kind; the language of an absent kind is the contract language of the target the run's `hw_profile` `accelerator` names; `c_kernel` is the value the absence states and stays a value of the list "후보 종류"; whether the version-3 reader keeps returning `c_kernel` for such a run is slice 6's; the header stays `.h`, `.c` is admitted and not compiled, multi-file bundles and own build settings stay asked, the other targets are unchanged; the record is this slice's §9 ADR.
  - **This record's own**: every other sentence — decisions 1 to 5 as far as they go beyond the answer, the A-13 reading and every weighing.
- **Answers** part of **OD-33** ① (the bundle at `cuda_gpu`) and ⑥ (the record of a CUDA kernel in a run). OD-33 stays open.
- **Session entry check** (CLAUDE.md), on 2026-11-15 at `main` `9e980f86`: open PRs — none; no open `nightly-failure` issue; no `실패` item in `PROCESS/RuntimeAcceptance.md`; issue #4 last comment 2026-07-31, #7 2026-09-07, #8 closed, #5 2026-11-14. Unresolved HQs: HQ-0102, HQ-0103; neither is crossed, and neither are HQ-0088 ① (c), HQ-0090 and #5 B-7.
- **The machine** (D29, read without installing anything): WSL2 `nvcc` at `/usr/local/cuda-13.1/bin/nvcc`; `nvidia-smi` answers `NVIDIA GeForce RTX 4070, 8.9`; the Windows host's `nvcc` is release 12.3. The code of this record reaches no real-GPU test.
- **Code** lands with this record: decision 6's first slice. No `claude` process was started, nothing was installed or pulled, and nothing needs a board or a key (D16). Statements about code are observations of `main` at `9e980f86`. The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **The answer** (**owner**): HQ-0104 (a), "(a)로 기록" (2026-11-15). The options weighed before it are [ADR-0207](ADR-0207-od33-cuda-target-demonstration.md) decision 5.
- **Earlier records** (cited): [ADR-0055](ADR-0055-od23-coder-output-form.md) decision 3 (R1 to R8: the reader of an attempt's `output/`), decision 5 (N1, N2: admitted names) and L2 (a name is no kind); [ADR-0200](ADR-0200-od33-given-code-evaluation.md) decision 2 (one C file placed as `given.c`), decision 5 (the command and its targets), decision 6 (a version-3 file without `candidate_kind` states `c_kernel`) and decision 7 (the reader table); [ADR-0198](ADR-0198-od32-compile-settings-candidate-kind.md) decisions 4 and 8 (version 1 states `c_kernel` by absence; opt-in readers); [ADR-0207](ADR-0207-od33-cuda-target-demonstration.md) decisions 3, 4, 5 and 9 (the `cuda_gpu` entry with `coder_loop` false, the `cuda` contract, the question, slice 6); [ADR-0076](ADR-0076-od8-instance-start-required-members.md) decision 1 and its widening by [ADR-0197](ADR-0197-od32-virtual-npu-oracle-and-instance-start.md) decision 1; [ADR-0201](ADR-0201-od33-given-code-run-fresh-directory.md) decision 2 (`given.place` as a tool of the registry); [ADR-0056](ADR-0056-od18-correctness-check-verification-executable.md) decision 6 (the reader's outcomes as kinds at the operation).
- **Code at `9e980f86`** (observed): `kernel_source.read_compiled_set` and `is_admitted_name` take a path or a name only; their callers are `bring_in` (names), `build_record` (a compile-settings build's named kernel), `standin_copies.place_copies` (the `cpu_standin` and `virtual_npu` operations) and `attempt_kernel.kernel_reference` (the model executor). `given_attempt.place` writes `output/given.c` and reads `instance.json` once with `instance.parse_given`. `instance.Given.candidate_kind` is `c_kernel` for a file without the member, and `check_tool`, `run_tool`, `run_file_tools` and `spec_tool` branch on it: `c_kernel` builds the attempt's own `output/`, `compile_settings` the named kernel with the spec's flags. `cuda_check.operation_for` and `cuda_run.operation_for` take a required selection `sources`; `check_definition.default_table` holds no `cuda_gpu` entry. Every `Target.contracts` key carries the contract's language (`targets._language_contracts`).

## Decision

### 1. Names and compiled set at `cuda_gpu`

- **ADR-0055 N1 and R3 are amended for `cuda_gpu` only** (**owner**). At `cuda_gpu`, N1 reads: the name matches, in full, `[a-z0-9][a-z0-9_-]{0,61}\.(c|h|cu)`. The part before the dot follows the same rule as before, so a `.cu` name has 4 to 65 characters. R3 reads: the compiled set is the kernel files whose name ends in `.cu`, in ascending byte order of their names. A `.c` file there is admitted and is a kernel file (R2), but it is never compiled and is never handed to a build. `.h` stays the header suffix (R5).
- **Unchanged at `cuda_gpu`**: N2 (the reserved stems, `con.cu` included), R1, R2, R4 (an attempt whose `output/` holds no `.cu` file has **no kernel source**, `no_compiled_file`), R5 to R8, the order and the reader's outcomes and failures. **Unchanged at every other target**: every name, set, answer and failure, byte for byte.
- **How the reader learns the target: a keyword parameter `language`** of `read_compiled_set` and `is_admitted_name`, one of `c` and `cuda`, by default `c`, with `kernel_source.language_at(accelerator)` giving the language of the target an `accelerator` names. That language is the one language of the target's contracts in the target table: `cuda` for `cuda_gpu`, `c` for `cpu_standin` and `virtual_npu`. A name the table holds no target for gives `c`, which is ADR-0055 as it stands (the mock). A target whose contracts are in no language, in more than one, or in one the reader does not know is refused with an error: the table is package source, so such an entry is a mistake of this repository, not of a run. The reader maps `c` to the compiled suffix `.c` and `cuda` to `.cu` (`nvcc` chooses CUDA C++ by that suffix).
  - *Why the language and not the name `cuda_gpu`*: the owner's answer reads an absent kind as "a kernel in the target's contract language", and the table already says which language that is. The contract key's language is the one fact; a reader keyed on the target's name would need a change for the next target in the same language, the argument [ADR-0207](ADR-0207-od33-cuda-target-demonstration.md) decision 3 made against keying on a name.
  - *Why a parameter and not a new `Target` member holding the suffix*: a `Target` member would be package source too and no frame change (ADR-0207 decision 3), but it would state again what `Target.contracts` already states and could disagree with it. The parameter keeps the reader a function of a path and a language that reads no table, no hw_profile and no file but the listings. The default keeps every existing caller exactly as before.

### 2. The bundle at `cuda_gpu`

- **ADR-0200 decision 2 is amended for `cuda_gpu` only** (**owner**): the given-code bundle there is **one CUDA C++ file**, placed as **`given.cu`** in the `output/` of the given attempt `(0, 1, 1)`. With decision 1 it is that attempt's whole compiled set. Every other rule of the bundle holds: the blob holds the bytes of the one file and has no format, at most 256 KiB, no header of its own, the target's build settings, the contract's inputs and reference. At every other target the file stays `given.c`.
- **How the placement learns the run's target**: from the `accelerator` of the `hw_profile` of the `instance.json` that `given.place` already reads once (its step 1). `given_attempt.given_name(accelerator)` answers `given.cu` where `language_at` answers `cuda`, else `given.c`. No new read, failure kind or order of checks is added; the tool's description names both files.
- **Still asked, as ADR-0200 decision 2 says**: several files or a header of the bundle's own, build settings, inputs or expected output of its own, and any other language. The name of the user's file is not read: the run's target decides the placed name.

### 3. The absent kind

- **At `cuda_gpu`, a version-3 `instance.json` without `candidate_kind` means a kernel in the target's contract language, CUDA C++** (**owner**). The file's form and version do not change (integrator's reading).
- **The readers keep returning `c_kernel` for such a run.** `instance.Given.candidate_kind` (and `Kinded.candidate_kind`, `candidate_kind_of`) answer `c_kernel` for a file without the member at every target. `check_tool`, `run_tool`, `run_file_tools` and `spec_tool` read it unchanged. What changes is the reading of the name: `c_kernel` is "a kernel built from the attempt's own `output/` in the language of the run's target", which is C at `cpu_standin` and `virtual_npu` and CUDA C++ at `cuda_gpu`.
  - *Why*: `c_kernel` is the value the absence states and stays a value of the approved list "후보 종류" (integrator's reading). A reader that returned another name for the same absence would introduce a value that list does not hold, which is option (b) of HQ-0104, not chosen. Adding a value to `CANDIDATE_KINDS` is not this record's, and HQ-0088 ① (c) is not asked again.
  - *Why nothing breaks*: every reader that branches on the kind tells "build the attempt's own `output/`" from "build the named kernel with the spec's flags" (`compile_settings`). That distinction holds at `cuda_gpu`. The language is the concern of the backend that the run's `accelerator` selects, and that backend applies the reader with the target's language (decision 5).
- **Versions 1 and 2 at `cuda_gpu`**: a version-1 file is written only by the start of the coder's round loop, which refuses `cuda_gpu` (`coder_loop` false). A `compile_settings` run at `cuda_gpu` is not opened by this record (Boundaries). If a later record writes one, its absence is read as above.

### 4. The bring-in

- **Unchanged.** `hilclaw.bring_in` keeps `is_admitted_name` with the language `c`. The coder's path is closed at `cuda_gpu` (`coder_loop` false), so no coder call brings files into a `cuda_gpu` attempt, and the given code is placed by `given.place`, not by a bring-in. The language of a bring-in at a target in another language comes with that path (HQ-0088 ① (c)).
- **Also unchanged**: `build_record` and `attempt_kernel` (a compile-settings build and the model executor; neither is opened at `cuda_gpu`, where `model_run` is false), and `standin_copies.place_copies` (the `cpu_standin` and `virtual_npu` operations).

### 5. The rest of ADR-0207 slice 6 (decided here, for the next slice)

1. **`instance_start` true** for `cuda_gpu` in the target table. `coder_loop` and `model_run` stay false.
2. **ADR-0076 decision 1 is widened to `cuda_gpu`**, as ADR-0197 decision 1 widened it to `virtual_npu`: besides the instances it covers, it covers **an instance whose `hw_profile.record` names `cuda_gpu` and whose stated `op_signature` is covered by a contract `cuda_gpu` serves** (today fp32 `gemm` `row_major` in `cuda`). ADR-0076 decisions 2 to 5 apply unchanged: **the required set is `cpu_standin`'s**, `n_max` and `coder_model` are filled in as there, and a refusal writes nothing. With no stated `op_signature` such an instance is in scope and is refused with `MissingMembersError` naming `op_signature`. A stated op_signature that no contract `cuda_gpu` serves is `OutOfScopeError` through `targets.covers_at`, as at `virtual_npu`. Not widened: any other accelerator.
3. **The given-code command at `cuda_gpu`**: `hilclaw.given_eval` accepts `cuda_gpu` through `targets.instance_start_accelerators` once 1 holds. It stores the user's file as it is, starts the version-3 instance, records the blob, places `given.cu` (decision 2), then runs `correctness.check` at `sim` and at `board`, `board.run`, `round.end` and `run.commit` through their tool functions, as at the other targets. It reads no suffix of the user's path. A start of the coder's round loop at `cuda_gpu` stays refused.
4. **The `cuda_gpu` backend in the default tables**: `correctness.check` by `cuda_check.operation_for(targets.target("cuda_gpu"), sources=cuda_check.compiled_sources)`, and `sim.run` and `board.run` by `cuda_run.operation_for` of the same target with the same `sources`. `profiler.collect` is not offered. `compiled_sources` is the selection of decision 1 applied to the attempt's own `output/` in the language `cuda`. Its "no kernel source" (an empty answer) is `no_kernel_source` and a failure of the reader is `kernel_source_unreadable`: the kinds of the same two answers at `cpu_standin` (ADR-0056 decision 6). Its headers are not copied, since the one way into a `cuda_gpu` attempt is the one-file bundle, which has none.
5. **The demonstration**: a test-placed fp32 `gemm` CUDA C++ kernel, given to the command, goes through `correctness.check` at both points, `board.run` and `run.commit` on this PC's GPU, in containers of the image ADR-0207 decision 7 names. The real-GPU test is skipped where `nvcc`, the GPU, the Container Toolkit or the image is absent (FR-19 ⑤).

These five are decisions of this record; the slice that implements them needs no further record. The files [ADR-0207](ADR-0207-od33-cuda-target-demonstration.md) decision 9 listed for slice 6 change accordingly: `attempt_kernel.py` stays as it is (decision 4).

### 6. The slices (code mode; no task is created here)

| Slice | What | Files |
|---|---|---|
| 6a (lands with this record) | Decision 1 (the reader's `language`, `language_at`), decision 2 (`given_name`, `given.place`), decision 3 (docstrings only; no behaviour changes), and the selection `cuda_check.compiled_sources`, which is not registered in any default table: a `cuda_gpu` call through the default registry stays `no_backend` | `kernel_source.py`, `given_attempt.py`, `instance.py`, `cuda_check.py` |
| 6b | Decision 5: `instance_start` true, the start's scope, the command at `cuda_gpu`, the default-table entries, the demonstration through `run.commit` on the real GPU | `targets.py`, `instance_start.py`/`start_instance.py`, `given_eval.py`, `check_definition.py` and the run tools' table, a demonstration test |

### A-13 reading

- **The frame change is the owner's** (HQ-0104 (a)): the admitted names and the compiled set of an attempt's `output/` at `cuda_gpu`, the bundle there, and the reading of an absent `candidate_kind` there. Decisions 1 to 3 stay inside the answer. They add no member, no value and no version: `instance.json`, spec, results, `STATE.json`, `artifacts.json`, `events.ndjson` and the layout version are unchanged, and `given.cu` sits in a place of layout 1.
- **No approved open list gains a value**: "후보 종류" keeps `c_kernel` and `compile_settings` (decision 3), and the contract table is not touched.
- **Package source only beyond that**: the reader's parameter and `language_at`, `given_name`, the selection, and decision 5's table and scope changes (`Target` members and the default tables are package source; the start's scope is widened as ADR-0197 decision 1 widened it).
- **No BLOCKED reason remains**: no new dependency (Python, the standard library), no unapproved frame change, and no owner part left undecided by the answer.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 1 | A `Target` member holding the kernel-file suffix | It states again what `Target.contracts` states (the language) and could disagree with it |
| 1 | The reader reads the target table or the hw_profile itself | The reader would read more than its two listings; a caller that knows no run (the bring-in, a test) would need a run |
| 1 | `.cu` names admitted at every target, compiled only at `cuda_gpu` | Changes N1 at `cpu_standin` and `virtual_npu`, which the answer leaves unchanged |
| 1 | `.cu` names limited to 64 characters (a shorter part before the dot) | Two stem rules for one name form; the owner's answer adds the suffix and keeps the other rules |
| 2 | Name the placed file after the user's file | The run's target decides the language (decision 3); a user's name is not read anywhere else |
| 3 | The reader returns a new name (for example `cuda_kernel`) for a kind-less `cuda_gpu` file | A value outside the list "후보 종류": HQ-0104 (b), not chosen |
| 3 | The readers raise for a kind-less `cuda_gpu` file until a kind value exists | It closes what the owner's answer opens |
| 5.4 | The selection returns the compiled set and the headers | `place_selected_copies` hands every selected file to the build; a header given to `nvcc` as a source is no compiled-set member (R5) |

## Consequences

- **Answers**: of OD-33 ①, the bundle at `cuda_gpu` (one CUDA C++ file); of ⑥, the record of a CUDA kernel in a run. OD-33 stays open (its other parts). OD-23's ADR-0055 is amended for one target. No open part of OD-23 is answered, so its register row is not edited.
- **Less exact, not edited**: ADR-0055 decision 5 N1 and decision 3 R3, as read at `cuda_gpu` (decision 1); ADR-0200 decision 2 ("is placed as `given.c`") and decision 4 (a) ("its `output/` holds `given.c`"), at `cuda_gpu` (decision 2); ADR-0198 decision 4 and ADR-0200 decision 6 ("C kernel run", "states `c_kernel`"), read at `cuda_gpu` as decision 3 says; ADR-0207 decision 9's file list for slice 6 (decision 5). [ADR-0207](ADR-0207-od33-cuda-target-demonstration.md) decision 5 gains a pointer to this record. ADR-0055 and ADR-0200 carry no amendment pointers, so none is added to them.
- **Readings for the owner to check**, listed in the #5 notice: the reader learns the target as its contracts' language (decision 1); `.cu` names of up to 65 characters (decision 1); `c_kernel` kept as the name the readers return for a kind-less `cuda_gpu` run (decision 3); decision 5 decided here for the next slice, ADR-0076's scope at `cuda_gpu` included.
- **Runtime acceptance items** (D22): none from this record's slice. The given-code round 0 of a live turn keeps the item ADR-0200 slice 3b left. Slice 6b states its own in its `Result`, which go to `PROCESS/RuntimeAcceptance.md`, not to an HQ.
- **UsageCases and StandardScenarios**: no use case step changes. S12's step 5 drops "CUDA 커널의 run 기록" from its open notes. Verdict unchanged, no gap.

## Boundaries (not decided here)

- **HQ-0088 ① (c)**: the coder's CUDA path, a vendor-language candidate kind, and then how a kind-less `cuda_gpu` run is read (integrator's reading: that HQ asks it). The bring-in's language comes with it.
- **`compile_settings` at `cuda_gpu`**, `model_run` at `cuda_gpu`, GPU memory figures (HQ-0090), bf16 in CUDA.
- **Multi-file bundles, headers of a bundle, own build settings** and every other language's bundle (ADR-0200 decision 2).
- **Every other vendor target**, and a target whose contracts are in more than one language.

## References

- Owner: HQ-0104 in `PROCESS/STATE.json`; [Requirements](../Requirements.md) FR-10, FR-19, OD-23, OD-33; [OpenDecisionProposals](../OpenDecisionProposals.md) § OD-33; [PROCESS/PLAN.md](../../PROCESS/PLAN.md) P3-16; [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §3 (D23), §6 (D29, D31), §9.
- Records: ADR-0001, ADR-0055, ADR-0056, ADR-0076, ADR-0197, ADR-0198, ADR-0200, ADR-0201, ADR-0207.
- Code read: `hilclaw/kernel_source.py`, `hilclaw/bring_in.py`, `hilclaw/build_record.py`, `hilclaw/standin_copies.py`, `hilclaw/attempt_kernel.py`, `hilclaw/given_attempt.py`, `hilclaw/instance.py`, `hilclaw/check_tool.py`, `hilclaw/run_tool.py`, `hilclaw/run_file_tools.py`, `hilclaw/spec_tool.py`, `hilclaw/cuda_check.py`, `hilclaw/cuda_run.py`, `hilclaw/targets.py`, `hilclaw/check_definition.py`; task T-0577.
