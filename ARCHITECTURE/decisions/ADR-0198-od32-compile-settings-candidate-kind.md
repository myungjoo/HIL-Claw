# ADR-0198: The first candidate kind that is no C kernel, compile settings (the owner's answers to HQ-0088 and HQ-0089) — a compile-settings run builds the C kernel of its own round-0 coder attempt with flags the technique-selector writes into a version-3 spec, `build.json` records the first build of such an attempt, every reader stays strict until the slice that teaches it, and the first slice is the readers of the three approved forms (part of OD-32 ①, ⑥ and ⑦, OD-6 ② and OD-18 ⑰ (다) for this kind)

## Status

- **Accepted on 2026-11-05** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed what this record decides.** The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **Three kinds of content.**
  - **Owner**, marked so: the answers to HQ-0088 and HQ-0089 (2026-11-05) and D27. The owner's words are **not subject to the objection window** above.
  - **The integrator's reading, cited and not this record's**: the notes in the two HQs' `decision` that mark themselves "통합자 독해(오너의 말이 아님)".
  - **This record's own**: every other sentence — decisions 2 to 9, the A-13 reading and every weighing.
- **Answers** part of **OD-32** ① (the record format, for compile settings), ⑥ (who makes this kind; when the "C 커널" wording changes) and ⑦ (the instance unit of this kind; when the scenario is added), part of **OD-6** ② (the `task.build` members and the record of the settings used, for this kind) and part of **OD-18** ⑰ (다) (what records the settings a build used, for this kind). Each OD keeps its status.
- **Session entry check** (CLAUDE.md), on 2026-11-05 at `main` `86f15ef9`: open PRs — none; no open `nightly-failure` issue; no `실패` item in `PROCESS/RuntimeAcceptance.md`; no P2-15 preparation pending; P3-6 is the first unchecked P3 item that is not waiting (P3-11 and P3-12 wait on HQ-0097 and HQ-0096). Issue #4 last comment 2026-07-31, #5 2026-11-05 (the HQ-0093 answer, not crossed), #7 2026-09-07, #8 closed. Unresolved HQs: HQ-0081, HQ-0095, HQ-0096, HQ-0097; none is crossed and none is anticipated (Boundaries).
- **Code** lands with this record: decision 8's first slice. No `claude` process was started, nothing was built or run in a container, and nothing needs a board or a key (D16). Statements about code are observations of `main` at `86f15ef9`. The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **The owner's answers** (**owner**, 2026-11-05, chat; the `decision` of each HQ in `PROCESS/STATE.json`, cited by number, not restated beyond what the decisions below need):
  - **HQ-0088**, "권고대로 (a)×5": ① the first kind is compile settings; ② the orchestrator's selection role writes them into the spec's `task.build` and does not call the coder; ③ CLAUDE.md's "C 커널" wording changes when the first non-kernel kind lands; ④ the unit, artefact, quality metric and evaluation data of a model-level kind are asked when that kind is chosen; ⑤ the scenario of this flow is added in the same work as the first kind that lands.
  - **HQ-0089**, "권고대로 (a)×4": ① one kind per instance; ② `build.json` under the attempt's `measure/`, for this kind only, with `schema_version` 1, `outcome`, `condition` (broken only), `flags` and `trailing_flags`, results and `step` unchanged; ③ `candidate_kind` is an approved open list of DRIVER §3, first values `c_kernel` and `compile_settings`; ④ the proposed format: `instance.json` `candidate_kind` with `schema_version` 2 (a C kernel run keeps 1 without the member; readers accept both); spec `task.build` members `candidate_kind`, `flags`, `kernel_round`, `kernel_candidate`, `kernel_attempt`, all required for `compile_settings`; a spec with no coder call is `schema_version` 3 (C kernel specs stay 2; readers accept both) and such an attempt's `output/` is empty.
- **The integrator's notes** (cited, not the owner's words): this ADR decides which attempt the C kernel of a compile-settings instance comes from, asking an HQ if that needs a frame element the answer did not approve (a new member, a reference to another run); `build.json` is one per attempt and this ADR says which build it records; the register updates of OD-32 ①, ⑥, ⑦, OD-6 ② and OD-18 ⑰ (다) are this ADR's; the task that lands the first kind changes the "C 커널" wording and adds the scenario.
- **Today** (cited): [ADR-0193](ADR-0193-od32-generalization-design.md) decision 2 places a candidate kind at the make and evaluate seam of an unchanged round loop and gives compile settings the row "`task.build` … the three tools as they are, with ADR-0116's 'one fixed set' read per target and per candidate". [ADR-0002](ADR-0002-od6-codegen-spec.md) makes a spec the input of one coder call (`id`) and `task.build` the place of settings prescribed for a candidate (decisions 6 (b) and 7). [ADR-0004](ADR-0004-od8-data-plane-layout.md) places `coder/…/spec.json`, `coder/…/output/` and `measure/…/build.json`; no code writes `build.json` (`hilclaw/layout.py` names it). [ADR-0024](ADR-0024-od8-instance-record-layout-version.md) and [ADR-0030](ADR-0030-od8-layout-stamp-read-order.md): an `instance.json` states the layout version of its run through its `schema_version`. [ADR-0116](ADR-0116-od18-cpu-standin-build-settings.md) decision 2 gives `cpu_standin` one fixed set of build settings, read per target since P3-2 (ADR-0193 decision 3).
- **Observations** (code at `86f15ef9`): round 0 has one coder attempt `(0, 1, 1)` (`orchestration/round-manager.md` steps 2 to 5); a round ≥ 1 has the `technique-selector` choose (step 6) and the `coder-driver` write the spec through `spec.write` and call the coder for `(round, 1, 1)` (step 8), then the evaluator's two checks, the experiment-runner's timing and the verdicts (steps 9 to 12). Each of `correctness.check` at `sim` and at `board`, `sim.run` and `board.run` builds the attempt's kernel once (`layout.BUILD_LOG_STEPS`; [ADR-0078](ADR-0078-od18-correctness-check-compiler-log-file.md), [ADR-0108](ADR-0108-od18-run-tools-timing-build-compiler-log.md)), forming the `output/` path of the requested attempt (`check_tool.py`, `run_tool.py`) and building with the target's flags; a failed build is the `broken` result with `build_time_limit` or `build_exit_status` (`check_build.py`; [ADR-0060](ADR-0060-od18-correctness-check-build-answers-and-settings.md)), and a flag `clang_build` refuses (one setting the output) is `settings_refused`. Every reader of `instance.json` and of a spec refuses another version with `UnsupportedVersionError`, which each caller maps to an existing kind (`run_file_unsupported` and the like).

## Decision

### 1. The owner's answers

As cited in Context (**owner**). Decisions 2 to 9 stay inside them: they add no member, value or version beyond HQ-0089 ④ and ②.

### 2. Where the C kernel comes from

- **Within the run: the round-0 bring-up coder attempt `(0, 1, 1)` of the compile-settings run itself.** Round 0 of such a run is the round 0 of today: the `coder-driver` writes a version-2 spec and the coder writes the C kernel to that attempt's `output/` (HQ-0088 ② concerns the candidates of the kind, not the kernel they build). In each round ≥ 1 the selection role names that attempt in `kernel_round` 0, `kernel_candidate` 1, `kernel_attempt` 1.
- **The form admits any attempt of an earlier round of the same run**: `kernel_round` is less than `id.round` (checked on one spec, decision 4); `kernel_candidate` and `kernel_attempt` are from 1. Naming round 0 is the selection role's rule (decision 3), not a rule of the form, so a later design can name another coder attempt of the run without a format change.
- **What is checked about it, at evaluation (slice 3)**: the named attempt has a version-2 spec (a coder attempt; a version-3 attempt is no kernel source) and an `output/` that yields a compiled set (ADR-0055). Otherwise the tool refuses with the existing kinds of a missing or unreadable kernel; no result is written. That the named attempt passed its own check is not a precondition: the candidate's own `correctness.check` decides its standing, since flags can change the numerics.
- **A kernel of another run is not provided.** It would need a run reference, a frame element HQ-0089 did not approve; this design does not need it, so no HQ is asked (Boundaries).

### 3. The selection role

- **The `technique-selector`** is "the orchestrator's selection role" (**owner** HQ-0088 ②): it already chooses what a round ≥ 1 tries (round-manager step 6). In a run whose kind is `compile_settings` it chooses the flags and has the version-3 spec of `(round, 1, 1)` written with `task.build` (decision 4) **in step 6**, through `spec.write` (slice 2b).
- **No coder call** for that attempt: round-manager step 8 is not taken in such a run, and steps 9 to 12 follow on the same tuple. `coder.run` on a version-3 spec refuses it as today (`spec_file.parse`, another version).
- **Unchanged** (ADR-0193 decision 2): hypotheses and `hypotheses.json`, verdicts, the budget, `STATE.json`, `case.write`'s place, `round.end`, `run.commit` and the round-manager's order apart from step 8. Round 0 is unchanged.
- This bounds the text slice 2b changes in `orchestration/round-manager.md` and `orchestration/agents/technique-selector.md`; no `orchestration/` file is edited here.

### 4. The version-3 spec

- **`id` names the attempt** (**owner** HQ-0089 ④: widened from one coder call to the attempt); its members, form and rules are version 2's.
- **The place is ADR-0004's `coder/…/spec.json`** of the attempt; no new place. Its writers are `spec.write` on the request of the `technique-selector` (slice 2b), besides the `coder-driver` for version 2. The attempt's `output/` stays empty (**owner**).
- **Form**: every section and rule of version 2 (ADR-0050), and `task.build` required, an object with exactly `candidate_kind` (the string `compile_settings`), `flags` (an array of strings of 1 to 255 printable ASCII characters, possibly empty), `kernel_round` (an integer from 0, less than `id.round`), `kernel_candidate` and `kernel_attempt` (integers from 1). *Why closed*: the build reads exactly these, and another member would be read by nothing; a version-2 spec keeps its open `task.build` (ADR-0002 decision 7) but for `candidate_kind` (next bullet). *Why `c_kernel` is no value of a version-3 spec*: a C kernel spec is version 2 (**owner**).
- **A version-2 spec states no kind**: its `task.build` may not hold `candidate_kind`, whatever the value; its other `task.build` names stay open. *Why*: the owner's rule "all required when `candidate_kind` is `compile_settings`" would otherwise be broken by a version-2 spec naming the kind without the `kernel_*` members, and a compile-settings spec read as a coder spec is the misreading the version change exists to prevent (HQ-0089 ④). No writer puts the member in a version-2 spec (`spec.write` writes no `task.build`).
- **Form of `instance.json` version 2**: version 1's members and rules, and `candidate_kind` required, a value of the list other than `c_kernel` (today `compile_settings`); a version-1 file holding `candidate_kind` is invalid. *Why*: a C kernel run keeps version 1 without the member (**owner**), so one meaning has one form, and a version-1 file naming a kind would be read as a C kernel run by every strict reader.

### 5. `build.json`

- **It records the first build of the attempt's candidate**: in the round order that is the build of `correctness.check` at `sim` (round-manager step 9). The four builds of an attempt use the same arguments (the target's flags plus the candidate's, and the target's trailing flags), so one file records the settings of all of them; the outcome of each later build stays in its own result, as today.
- **Writer and time**: the evaluation tool that carries out that build (slice 3), after the build ended and before its result is written, by a write that gives the name only if it is free (as ADR-0029's write). A later build finds it present and writes nothing. A call that ends before a build ran (`settings_refused`, a missing kernel, another backend kind) writes no `build.json`.
- **Mapping**: a build that `check_build.read_build` answers `built` gives `outcome` `"built"` and no `condition`; one it answers `build_time_limit` or `build_exit_status` gives `outcome` `"broken"` and that `condition`, the same value as the `broken` result. `flags` and `trailing_flags` are the exact argument arrays handed to the compiler.
- **Results and `step` do not change** (**owner** HQ-0089 ②; [ADR-0100](ADR-0100-od18-tool-result-change.md)), and a C kernel attempt writes no `build.json`.

### 6. How evaluation reads the candidate

- **`correctness.check`, `sim.run` and `board.run`** (slice 3), for an attempt whose spec is version 3, read the kernel from the `output/` of the attempt the spec names (decision 2) and build it with the target's `flags` followed by the candidate's `flags`, and the target's `trailing_flags`: ADR-0116's "one fixed set" read per target and per candidate. The verification, timing, time limits, memory bound and results are the target's, unchanged.
- **Refused**: a named attempt that is no coder attempt or has no compiled set (decision 2); a flag `clang_build` refuses (one setting the output, one holding U+0000), answered `settings_refused` as today. No other flag is forbidden here; a target that needs a forbidden list adds it to its target entry.

### 7. The instance start and the layout version

- **The start takes `candidate_kind`** (slice 2a): a request that names `compile_settings` writes `instance.json` version 2 with that member; one that names no kind, or `c_kernel`, writes version 1 without it, exactly as today. The required set of ADR-0076 and its scope are unchanged.
- **A version-2 file states layout version 1**: the kind uses only places layout 1 has (`coder/…/spec.json`, an empty `output/`, `measure/…/build.json`), so the layout does not change (ADR-0024 decision 3, ADR-0030).

### 8. Readers, and the first slice

- **Choice for this slice**: explicit opt-in entries beside the strict ones, which stay unchanged. `hilclaw.instance` gains `KIND_SCHEMA_VERSION`, `CANDIDATE_KINDS`, `Kinded`, `parse_kinded`, `validate_kinded`, `read_kinded` and `candidate_kind_of` (`c_kernel` for a version-1 file); `parse`, `validate`, `read`, `layout_version_of` and every `*_of` accessor still read version 1 only. `hilclaw.spec` gains `SETTINGS_SCHEMA_VERSION` and `validate_versioned`; `hilclaw.spec_file` gains `parse_versioned`; `validate`, `parse`, `final_name` and `write` keep version 2. The new `hilclaw.build_record` validates and reads `build.json`; nothing writes it. *Why opt-in entries*: no caller is widened by accident, and each later slice switches the callers it teaches.
- **The reader table** (what each caller does with an `instance.json` version 2 / a spec version 3; "refuses" is the existing kind of another version):

| Caller | Slice 1 (this) | Slice 2a (start) | Slice 2b (round) | Slice 3 (evaluation) |
|---|---|---|---|---|
| `instance_file`, `instance_start`, `start_instance` (and `new_run`) | write v1 only | write v2 for `compile_settings` | — | — |
| `journaled_tool` / `layout_version_of`, `hw_tool` / `hw_profile_of`, `run_file_tools`, `key_store_tool`, `run_admission`, `run_objective`, `run_commit`, `further_turn`, `tools` | refuse v2 | refuse v2 | read v2 as v1 (its members mean the same) | — |
| `spec_tool` (`spec.write`) | refuses v2 (through `run_file_tools`); writes v2 specs only | — | composes and writes a v3 spec on the technique-selector's request in a `compile_settings` run; v2 elsewhere | — |
| `coder_call` (`coder.run`) | refuses v2 (through `run_file_tools`) and v3 | — | reads a v2 run through `run_file_tools`, for round 0's v2 spec; refuses v3 (no coder call for such an attempt) | — |
| `spec_feedback` | refuses v3 | — | refuses v3 (no coder spec follows one in such a run) | — |
| `check_admission`, `check_tool`, `run_tool` (behind `hw_tool` and `journaled_tool`) | refuse v2 | refuse v2 | refuse a run whose kind is not `c_kernel`, with `run_file_unsupported`, though `hw_tool` and `journaled_tool` read it | read v2; for a v3 attempt build the named kernel with the candidate's flags and write `build.json` |
| `attempt_kernel` (and `kernel_source`) | refuses v3 | — | — | for a v3 attempt reads the named attempt's kernel |
| `case_lookup`, `cases_tool`, `catalog_tool`, `s6_metric`, `model_run_binding` | refuse v2 | refuse v2 | refuse v2 (those reading through `run_file_tools` by the kind read, with their existing unsupported kind) | refuse v2 (cases, the metric and model runs of this kind are not P3-6's; `case.write`'s failure lets the round go on, round-manager closing step 1) |

- **This slice**: no writer writes a version-2 instance, a version-3 spec or a `build.json`; every caller above behaves as before for version-1 instances and version-2 specs and refuses the new versions with its existing kind.
- **Two narrowings of version 1 and 2, by decision 4**: a version-1 `instance.json` holding `candidate_kind` and a version-2 spec whose `task.build` holds it are now invalid at every entry. No run writes either, but **the start (`instance.start`, `instance_start.prepare`) carried an undefined member over (ADR-0076 decision 4), so a start request holding `candidate_kind` was written before and is now refused**, with the `InvalidInstanceError` that `instance.validate` raises and its existing kind, until slice 2a gives the member its meaning.

### 9. The slices (input for the planner; no task is created)

| Slice | Content | Rough size |
|---|---|---|
| 1 (this) | Validators and readers of `instance.json` v2, spec v3, `build.json` v1 | ~460 LOC, 4 files (tests excluded) |
| 2a | The start takes `candidate_kind` (`instance_start`, `start_instance`, `new_run`, `instance_file`); writes v2 | ~300 LOC, 4–5 files |
| 2b | Run-level readers read v2 (table row 2); `spec.write` composes v3 for the technique-selector; `orchestration/round-manager.md` step 6/8 and `technique-selector.md` | ~500 LOC, 8–10 files |
| 3 | The three tools build a v3 attempt from the named kernel with the candidate's flags and write `build.json`; `attempt_kernel` follows the reference | ~550 LOC, 6–8 files |
| 4 | **Landing**: CLAUDE.md's three-layer "C 커널" wording (**owner** HQ-0088 ③), the StandardScenarios scenario of this flow with the coverage re-check (HQ-0088 ⑤), a runtime acceptance item for a coder-free round; PLAN P3-6 is checked after it | ~150 lines of documents |

The order is 1, 2a, 2b, 3, 4; 2a and 3 depend only on 1. The kind is runnable end to end after 3; slice 4 is the "first non-kernel kind lands" of HQ-0088 ③ and ⑤.

### A-13 reading

- **The frame elements used are exactly those HQ-0089 approved**: the `instance.json` member `candidate_kind` and its `schema_version` 2; the spec `task.build` members `candidate_kind`, `flags`, `kernel_round`, `kernel_candidate`, `kernel_attempt` and `schema_version` 3; `measure/…/build.json` with `schema_version` 1, `outcome`, `condition`, `flags`, `trailing_flags`. Decisions 2 to 7 add rules of value inside them (closed members of a version-3 `task.build`, `kernel_round` below `id.round`, no `candidate_kind` in a version-1 `instance.json` or in the `task.build` of a version-2 spec, no `c_kernel` at version 2 or 3), each grounded in HQ-0089 ④ (a C kernel run and a C kernel spec keep their version without the member), and no member, value or version.
- **The values `c_kernel` and `compile_settings` are the approved open list "후보 종류"** of DRIVER §3 (HQ-0089 ③); this record adds no value to it.
- **Nothing else changes the frame**: results, `step` values, `events.ndjson`, `artifacts.json`, `STATE.json` and the layout version are unchanged; `build_time_limit` and `build_exit_status` are existing values.
- **No BLOCKED reason remains**: no new dependency (Python, the standard library), no unapproved schema change, no owner part left undecided by the answers.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | The best kernel of another run | Needs a run reference (an unapproved frame element); the run's own round 0 gives a kernel |
| 2 | Any attempt with a passing check only | The candidate's own check judges it; flags can change numerics |
| 3 | The `coder-driver` writes the v3 spec | The owner named the selection role; the `coder-driver` exists to call the coder |
| 4 | An open `task.build` in v3 | A member nothing reads would be silently ignored |
| 5 | One `build.json` per build | The owner approved one file; the arguments of the four builds are the same |
| 8 | Widening `parse`/`read` with a version argument | Every caller would have to be audited in this slice; opt-in entries widen none |

## Consequences

- **Registers**: OD-32 ①, ⑥, ⑦, OD-6 ② and OD-18 ⑰ (다) are answered in part for this kind (Requirements rows and OpenDecisionProposals sections). The StandardScenarios coverage is re-checked; no scenario is added (HQ-0088 ⑤ puts it in slice 4).
- **Runtime acceptance item** (handed to `PROCESS/RuntimeAcceptance.md` by slice 4, when the flow exists; none from this slice): a live round ≥ 1 of a `compile_settings` run in which the technique-selector writes a v3 spec, no coder call is made, and the evaluator builds round 0's kernel with the candidate's flags and writes `build.json`.
- **Less exact, not edited**: ADR-0002's "the input of one coder invocation" (true of version 2) and decision 7's open `task.build` (at version 2 it may no longer hold `candidate_kind`); ADR-0029 and ADR-0051 ("a file of another version" includes 3); ADR-0018 decision 2 and ADR-0024 decision 3 (only version 1 named); ADR-0193 decision 2's "Files of today state no kind"; ADR-0116 decision 2 ("one fixed set", per candidate once slice 3 lands); the docstrings of `hilclaw/spec_tool.py`, `coder_call.py`, `attempt_kernel.py` and `layout.py` that say no code writes `build.json` or that a spec is one coder call's.

## Boundaries (not decided here)

- Vendor-language kernels and quantization settings (not chosen, still candidate kinds — D27 ①); model-level kinds and their unit, artefact, quality metric and evaluation data (**owner** HQ-0088 ④).
- A kernel from another run; cases, the S6 metric and model runs of a compile-settings run (FR-18 for this kind).
- Which execution is which point (HQ-0095), the vendor oracle and LLM-level unit (HQ-0096), the device-unavailable kind and given-code record (HQ-0097); fp16, gates and the S6 scale (HQ-0083, HQ-0085, HQ-0081).

## References

- Owner: HQ-0088, HQ-0089 in `PROCESS/STATE.json`; D6, D23, D27.
- [Requirements](../Requirements.md): C-6, FR-1, FR-5; rows OD-6, OD-18, OD-32. [OpenDecisionProposals](../OpenDecisionProposals.md) § OD-6, § OD-18, § OD-32; [StandardScenarios](../StandardScenarios.md).
- Records: ADR-0001, ADR-0002, ADR-0004, ADR-0018, ADR-0024, ADR-0029, ADR-0030, ADR-0050, ADR-0051, ADR-0055, ADR-0060, ADR-0076, ADR-0078, ADR-0100, ADR-0108, ADR-0116, ADR-0138, ADR-0151, ADR-0193, ADR-0196.
- Code read: `hilclaw/instance.py`, `spec.py`, `spec_file.py`, `layout.py`, `attempt_kernel.py`, `kernel_source.py`, `check_build.py`, `check_tool.py`, `run_tool.py`, `clang_build.py`, `spec_tool.py`; `orchestration/round-manager.md`.
- Process: [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §3 ("승인된 열린 목록", 후보 종류), §5, §6 D27, §8, §9; [PROCESS/PLAN.md](../../PROCESS/PLAN.md) P3-6; task T-0552.
