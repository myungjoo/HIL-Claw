# ADR-0200: Evaluating given code (the owner's answers to HQ-0092 (a) and HQ-0097 (b)) — a given-code bundle is one C source file that implements a contract of the contract table at a target an instance may start on, stored as one blob with no format of its own; the run's `hw_profile` and `op_signature` are its key; a run whose `instance.json` (version 3) holds `given_code` has that code as its round-0 attempt instead of the bring-up coder call, and an out-of-loop evaluation is such a run with a round budget of 1, started and carried through by a command; every reader stays strict until the slice that teaches it, and the first slice is the readers of version 3 (part of OD-33 ① and ⑥, part of OD-28)

## Status

- **Accepted on 2026-11-12** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed what this record decides.** The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **Three kinds of content.**
  - **Owner**, marked so: the answers to HQ-0092 (2026-11-05) and HQ-0097 (b) (2026-11-12), including the additions to (b) that the owner accepted as recommended. The owner's words are **not subject to the objection window** above.
  - **The integrator's reading, cited and not this record's**: the notes in the two HQs' `decision` that mark themselves "통합자 독해(오너의 말이 아님)".
  - **This record's own**: every other sentence — decisions 2 to 9, the A-13 reading and every weighing.
- **Answers** part of **OD-33** ① (the composition of the bundle, for code at an existing contract and target) and ⑥ (the key of such code), and part of **OD-28** (the baseline of a run that states given code). Each OD keeps its status.
- **Session entry check** (CLAUDE.md), on 2026-11-12 at `main` `7fbecebe`: open PRs — none; open `nightly-failure` issue #373 (task T-0559, BLOCKED on HQ-0100); no `실패` item in `PROCESS/RuntimeAcceptance.md`; no P2-15 preparation pending. Issue #4 last comment 2026-07-31, #7 2026-09-07, #8 closed; #5 2026-11-12 — the HQ-0097 answer and the owner's purpose-first re-ordering (to be recorded as DRIVER D31), neither crossed here. Unresolved HQs: HQ-0095, HQ-0096, HQ-0100; none is crossed and none is anticipated (Boundaries).
- **Code** lands with this record: decision 8's first slice. No `claude` process was started, nothing was built or run in a container, and nothing needs a board or a key (D16). Statements about code are observations of `main` at `7fbecebe`. The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **The owner's answers** (**owner**; the `decision` of each HQ in `PROCESS/STATE.json`, cited by number, not restated beyond what the decisions below need):
  - **HQ-0092 (a)**, "그렇게 기록": code the user gives is evaluated first, through PLAN P3-11; coder-written code at a vendor target comes with the vendor-language candidate kind. The uses: inside the loop the evaluation parts are FR-1's experiment step; "루프 밖의 독립평가는 가설도입과, 측정 후 진행정도 측정에 사용 가능".
  - **HQ-0097 (b) (i)**, "권고대로 기록": the code is a blob of the CAS with an `artifacts.json` record of the new `type` `given_code`, class `final`; `instance.json` gets the member `given_code` holding its hash; a file holding it has `schema_version` 3 and readers accept 1, 2 and 3; `given_code` is an optional member independent of `candidate_kind`; the composition of the bundle, the key of given code and whether an out-of-loop independent evaluation is a run with an instance are this record's, asked again if they enter the data plane.
- **The integrator's notes** (cited): given code serves the two out-of-loop uses and the round-0 baseline (OD-28), coder candidates the loop's normal path; figures used for hypothesis introduction are reference, not target (FR-15); a file without `given_code` stays version 1 or 2; class `final` meets [ADR-0195](ADR-0195-p3-14-storage-cleanup-and-cas-gc.md) decision 7; the `type` value is the open name form of [ADR-0005](ADR-0005-od8-artifacts-record.md) decision 5; LLM-wide code touches HQ-0096 ①.
- **Today** (cited): [ADR-0198](ADR-0198-od32-compile-settings-candidate-kind.md) decisions 7 and 8 add `instance.json` version 2 through opt-in readers (`parse_kinded`, `validate_kinded`, `read_kinded`) while the strict ones read version 1 only. [ADR-0055](ADR-0055-od23-coder-output-form.md) makes an attempt's kernel the compiled set of its `output/` (the `.c` files under admitted names, at most 16 files of at most 256 KiB). [ADR-0119](ADR-0119-od28-first-case-baseline.md) makes the baseline of a first-case run its own round-0 attempt, measured at the board point. [ADR-0177](ADR-0177-od18-od6-contract-table.md) holds the contracts in one table keyed by the op_signature's kind and dtype. [ADR-0076](ADR-0076-od8-instance-start-required-members.md) gives the members a start requires; `targets.instance_start_accelerators` names the targets an instance may start on (today `cpu_standin` and `virtual_npu`, [ADR-0193](ADR-0193-od32-generalization-design.md) decision 4, [ADR-0197](ADR-0197-od32-virtual-npu-oracle-and-instance-start.md)). [ADR-0024](ADR-0024-od8-instance-record-layout-version.md) decision 3: a record that raises this file's `schema_version` says which layout version the new version states.
- **Observations** (code at `7fbecebe`): `correctness.check`, `sim.run` and `board.run` of a `c_kernel` run build the compiled set of the requested attempt's `output/` with the target's flags and read no spec (`check_tool.py`, `run_tool.py`); `round.end` ends a run whose `round_budget` is reached (`round_end_tool.py`); `cas.put_file` stores a file and `artifacts.add_record` records it; a CAS digest and an `artifacts.json` `sha256` are 64 lowercase hexadecimal characters (`cas.py`, `artifacts.py`).

## Decision

### 1. The owner's answers

As cited in Context (**owner**). Decisions 2 to 9 stay inside them: they add no member, value or version beyond HQ-0097 (b) (i) and its additions.

### 2. The bundle

| Part | What it is | Where it comes from |
|---|---|---|
| Source | **One C source file** that defines the entry function of the contract the run's op_signature names | the user; stored as the `given_code` blob |
| Build method | the target's build settings, as for any kernel of the run (for `cpu_standin` [ADR-0116](ADR-0116-od18-cpu-standin-build-settings.md) decision 2, for `virtual_npu` its target flags) | the target entry (ADR-0193 decision 3) |
| Inputs | drawn by the harness from the contract, the op_signature's shape and the run's `draws` | the contract table (ADR-0177), the instance |
| Expected output | the contract's reference under the run's `tolerance`, the oracle of the target | the contract table; ADR-0197 for `virtual_npu` |

- **The blob holds the bytes of the one file and has no format of its own**: nothing in it is parsed by a reader of the data plane, so it is no data-plane frame (D23), and no HQ is asked. The other parts are what the instance start request already states (`hw_profile`, `op_signature`, `tolerance`, `draws`, …); the bundle adds the file and nothing else.
- **The file obeys the kernel-file rules of ADR-0055** (one file of the compiled set, at most 256 KiB, its own headers not admitted) and is placed as **`given.c`**, an admitted name, when it becomes an attempt's kernel (decision 4).
- **Not provided, each needing a form the owner has not approved**: several files or a header of its own (a blob would need an archive or manifest format), build settings of its own, inputs or an expected output of its own, another language (CUDA, a vendor kernel). The task that needs one asks its form as an HQ (D23); nothing below depends on it.

### 3. The key of given code (OD-33 ⑥'s remaining part, for this scope)

- **Code that implements an existing contract at an existing target needs no key of its own.** The run's `hw_profile` (where it runs) and `op_signature` (which operation) are the key of its figures exactly as for a coder kernel of the run (FR-13, [ADR-0001](ADR-0001-od4-key-schema.md)); the code itself is identified by its blob's hash (`given_code`, the `artifacts.json` record).
- **LLM-wide code** (a model, not one operation) has no op_signature and its key is not decided here: it belongs to OD-33 ⑤ and HQ-0096 ①.

### 4. The two uses

**(a) The round-0 baseline of a loop run (OD-28).** In a run whose `instance.json` holds `given_code`:

- **Round 0 makes no coder call.** Its one attempt `(0, 1, 1)` is the given code: its `output/` holds `given.c`, written from the blob after `cas.verify_blob` confirms the hash. The attempt has **no `spec.json`**: a spec is the input of a coder call, and a spec with no coder call is version 3, whose form is that of `compile_settings` (**owner** HQ-0089 ④).
- **No repair attempt is made for it** (a repair is a coder call that rewrites the code, and the code would then no longer be the code given). A given attempt that cannot stand leaves round 0 without a standing attempt, and the existing rule for that applies ([ADR-0185](ADR-0185-od23-first-case-round-zero-ends-without-standing-attempt.md) for a first-case run of one candidate; otherwise OD-28's remainder).
- **Unchanged**: the two checks, the timing and the verdicts of round 0 run on `(0, 1, 1)` as on a coder attempt; ADR-0119's baseline rule applies to the given attempt as "the run's own round-0 attempt"; rounds ≥ 1, hypotheses, the budget, `STATE.json`, `round.end` and `run.commit` do not change.
- **One candidate**: the slices start a given-code run with `candidates_per_round` 1 only; whether round 0 of a run with N > 1 adds coder candidates beside the given one stays with OD-28 (N > 1 in round 0, ADR-0119 decision 4).

**(b) The out-of-loop independent evaluation.** It **is a run with an instance**: a given-code run whose `round_budget` is 1, so round 0 alone (round 0 counts against the budget, [ADR-0121](ADR-0121-od8-run-over-member.md)), carried through by the command of decision 5.

- **Its outcome** is that run's own files — the check and run results of `(0, 1, 1)`, `events.ndjson`, `artifacts.json` — and no new data-plane file.
- **Hypothesis introduction** (FR-15, FR-17 ②): another run names the evaluation run as `injections` material at its start ([ADR-0075](ADR-0075-od30-injection-at-instance-start.md), `source` a string such as `runs/<run_id>`). The figures stay reference, not target: they set no objective, baseline or bound of the receiving run, whose baseline remains its own round-0 attempt (ADR-0119; a kernel of another run is not provided, ADR-0198 decision 2).
- **Progress measurement after the loop**: a given-code run of the same target, op_signature, tolerance and draws as a loop run gives figures of the same quantity at the same points (ADR-0194 decision 5), to be read beside the loop run's. Comparing figures across runs is the reader's here; no tool compares them, and comparability across sessions stays OD-13 ① and OD-11.

### 5. The entry point

- **A command, `python -m hilclaw.given_eval <request>`**, run by a person, registered as no tool, starting no `claude` (as [ADR-0192](ADR-0192-od31-model-check-command.md) decision 1 and [ADR-0155](ADR-0155-od23-first-case-instance-start-command-line.md)). The request is an instance start request of ADR-0155's form plus the path of the C file. The steps stop at the first failure: the request; the data root (the existing data-root source); the file stored by `cas.put_file`; the instance started with `given_code` and `round_budget` 1 (slice 2); the `artifacts.json` record (`type` `given_code`, `round` 0, class `final`); the placement of `(0, 1, 1)` (slice 3b); `correctness.check` at `sim`, then at `board`, then `board.run`, through their tool functions, as round 0 orders them ([ADR-0142](ADR-0142-od23-first-case-round-zero-after-coder-call.md)); `round.end` of round 0, which ends the run; `run.commit`; a summary on standard output.
- **Order of the start**: the blob, then `instance.json` (which claims the run id, [ADR-0025](ADR-0025-od8-instance-file-write.md)), then the record. A failure between the last two leaves a blob no `artifacts.json` names, which the GC keeps (ADR-0195 decision 7, "kept by construction"), and the command reports the failure.
- **Targets accepted now**: those an instance may start on (`targets.instance_start_accelerators`), whose oracle and points are decided — `cpu_standin` and `virtual_npu`. **A vendor target needs first**: a `Target` with `instance_start` true, which waits on the measuring points (HQ-0095), the oracle (HQ-0096 ②), a GPU or device in the runtime's container (the rest of OD-33 ⑨) and the `device_unavailable` kind (HQ-0097 (a), its own task); and a bundle form for its language (decision 2). None is decided here.

### 6. The instance start and the layout version

- **The start takes `given_code`** (slice 2): a request that names a C file stores it and writes `instance.json` version 3 with the member; a request without one writes version 1, or version 2 for `compile_settings`, exactly as today. The required set of ADR-0076 and its scope are unchanged. Slice 2 writes version 3 for a `c_kernel` run only; `given_code` with `candidate_kind` `compile_settings` (whose rounds ≥ 1 would build the given attempt, ADR-0198 decision 2) is refused at the start until slice 5.
- **Form of version 3**: version 1's members and rules; `given_code` required, exactly a string of 64 lowercase hexadecimal characters (the form of a CAS digest and of an `artifacts.json` `sha256`); `candidate_kind` optional under version 2's rule (a value of the list other than `c_kernel`), its absence stating `c_kernel`. `given_code` in a file of version 1 or 2 is invalid. *Why*: one meaning has one form — a file without given code keeps its version (**owner**), and a version-1 or version-2 file naming given code would be read by every strict reader as an ordinary run. Only the form is checked: not that the blob is stored or recorded.
- **A version-3 file states layout version 1**: given code uses only places layout 1 has (`blobs/sha256/`, `runs/<run_id>/artifacts.json`, the attempt's `output/`), so the layout does not change (ADR-0024 decision 3, [ADR-0030](ADR-0030-od8-layout-stamp-read-order.md)).

### 7. Readers, and the first slice

- **Choice for this slice**: opt-in entries beside the existing ones, which stay unchanged, as ADR-0198 decision 8 chose. `hilclaw.instance` gains `GIVEN_SCHEMA_VERSION`, `Given`, `parse_given`, `validate_given`, `read_given` and `given_code_of` (`None` for a version-1 or version-2 file); `parse`, `validate`, `read` and every `*_of` accessor read version 1 only, and `parse_kinded`, `validate_kinded`, `read_kinded`, `candidate_kind_of`, `layout_version_of_kinded` and `read_as_version_1` read 1 and 2, each refusing version 3 with `UnsupportedVersionError` as before. `hilclaw/instance_file.py` is not changed: no writer writes version 3 yet.
- **The reader table** (what each caller does with an `instance.json` of version 3; "refuses" is the existing kind of another version):

| Caller | Slice 1 (this) | 2 (start) | 3a (run readers) | 3b (round 0) | 4 (command) |
|---|---|---|---|---|---|
| `instance_file`, `instance_start`, `start_instance`, `new_run` | write v1 or v2 only | write v3 for a request with a C file (`c_kernel`, N = 1) | — | — | used by the command |
| `journaled_tool` / `layout_version_of_kinded`, `hw_tool`, `run_file_tools` (`instance.read`, `state.read`), `round_end_tool`, `key_store_tool`, `run_admission`, `run_objective`, `run_commit`, `further_turn`, `tools` | refuse v3 | refuse v3 | read v3 as its v1 twin (its other members mean the same) | — | — |
| `check_admission`, `check_tool`, `run_tool` | refuse v3 | refuse v3 | read v3 of kind `c_kernel`; the given attempt is evaluated as a C kernel attempt, from its `output/` | — | called by the command |
| `spec_tool`, `coder_call`, `spec_feedback` | refuse v3 (through `run_file_tools`) | — | read v3 for rounds ≥ 1 | no spec and no coder call for `(0, 1, 1)` | — |
| the placement of `(0, 1, 1)` (new) | — | — | — | writes `given.c` from the verified blob | called by the command |
| `attempt_kernel`, `model_run_binding`, `case_lookup`, `cases_tool`, `catalog_tool`, `s6_metric` | refuse v3 | refuse v3 | refuse v3 (cases, the S6 metric and model runs of a given-code run are not P3-11's; `case.write`'s failure lets the round go on) | — | — |

- **This slice**: no writer writes a version-3 instance, a `given_code` blob or record; every caller above behaves as before for versions 1 and 2 and refuses version 3 with its existing kind.
- **One narrowing of versions 1 and 2, by decision 6**: a version-1 or version-2 `instance.json` holding `given_code` is now invalid at every entry. No run writes one, but **the start (`instance.start`, `instance_start.prepare`) wrote an undefined member as given (a reader passes over a member it does not know, ADR-0018 decision 2), so a start request holding `given_code` was written before and is now refused**, with the `InvalidInstanceError` that `instance.validate_kinded` raises and its existing kind, until slice 2 gives the member its meaning.

### 8. The slices (input for the planner; no task is created)

| Slice | Content | Rough size |
|---|---|---|
| 1 (this) | Validators and readers of `instance.json` v3 | ~120 LOC in 1 file, with this record (tests excluded) |
| 2 | The start takes a C file: `cas.put_file`, v3 `instance.json`, the `given_code` record (`instance_start`, `start_instance`, `new_run`, `instance_file`) | ~300 LOC, 4–5 files |
| 3a | Run-level readers and the three evaluation tools read v3 (table rows 2 to 4) | ~400 LOC, 8–10 files |
| 3b | The placement of `(0, 1, 1)` from the blob; `orchestration/round-manager.md` round 0 of a given-code run (no coder call, no repair); a runtime acceptance item for that live round 0 | ~300 LOC, 3–4 files |
| 4 | **The command** `hilclaw.given_eval`, **verified with the real clang at `cpu_standin`** (D29; clang is on the machine and in CI); PLAN P3-11 is checked after it | ~350 LOC, 2–3 files |
| 5 | Given code with `compile_settings`: `attempt_kernel` and the three tools take the given attempt as the named kernel; the start admits the pair | ~200 LOC, 3–4 files |

The order is 1, 2, 3a, 3b, 4; 3a depends only on 1, and 5 on 3a. 5 is not needed for P3-11.

### A-13 reading

- **The frame elements used are exactly those HQ-0097 (b) approved**: the `instance.json` member `given_code` and its `schema_version` 3, readers accepting 1, 2 and 3; the `artifacts.json` `type` value `given_code` with the existing class `final`. Decision 6 adds rules of value inside them (the form of the hash, `given_code` required at 3 and not admitted at 1 or 2, `candidate_kind` at 3 under version 2's rule with `c_kernel` stated by absence), each grounded in the owner's "a file without it stays 1 or 2" and "independent of `candidate_kind`", and no member, value or version.
- **The `type` value `given_code` is the open name form of ADR-0005 decision 5**, not an approved open list of DRIVER §3; **no approved open list gains a value** ("후보 종류" keeps `c_kernel` and `compile_settings`).
- **Nothing else changes the frame**: the blob has no format (decision 2); `given.c` is an admitted kernel-file name in a place of layout 1; an attempt without a coder call has no coder spec, as ADR-0004 places a spec for a coder call; results, `step` values, `events.ndjson`, `STATE.json`, `spec.json` and the layout version are unchanged.
- **No BLOCKED reason remains**: no new dependency (Python, the standard library), no unapproved schema change, no owner part left undecided by the answers.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | A bundle archive (several files, a manifest) now | A blob format is a frame element the owner has not approved; one C file covers the contracts of today |
| 2 | Inputs and an expected output from the user | The contract's harness and reference already give both, and a second oracle would need the owner (HQ-0096 ② for vendor targets) |
| 4a | Given code beside the bring-up coder call | Two round-0 candidates make N > 1 in round 0, open under OD-28 |
| 4a | A version-2 spec for the given attempt | A spec with no coder call is version 3 (**owner** HQ-0089 ④), and version 3 is the compile-settings form |
| 4b | An evaluation that is no run, its answer on standard output only | FR-19 ① ends in a record; a run records with the existing files and the approved member |
| 5 | The evaluation through a live orchestrator turn | Out-of-loop evaluation needs no model judgement; a command is deterministic and testable with clang |
| 7 | Widening `parse_kinded`/`read_kinded` to version 3 | Every kinded caller would read a given-code run as an ordinary one before it is taught; opt-in entries widen none |

## Consequences

- **Registers**: OD-33 ① and ⑥ and OD-28 are answered in part (Requirements rows, OpenDecisionProposals sections); FR-19's list of open parts is narrowed. The StandardScenarios coverage is re-checked (S12 steps 2 and 5).
- **Runtime acceptance item**: none from this slice. Slice 3b hands one to `PROCESS/RuntimeAcceptance.md` through its `## Result`: a live round 0 of a given-code loop run in which the Round-Manager places the given code, makes no coder call and evaluates `(0, 1, 1)`.
- **Less exact, not edited**: ADR-0018 decision 2 and ADR-0024 decision 3 (only version 1 named); ADR-0198 decisions 7 and 8 ("versions 1 and 2" as all there are); ADR-0119 decision 2 ("bring-up code", which for a given-code run is the given attempt); ADR-0055 ("a coder call" as the only writer of `output/`); the docstrings of `hilclaw/instance_file.py`, `instance_start.py` and `run_file_tools.py` that name versions 1 and 2 only.

## Boundaries (not decided here)

- Vendor targets: the measuring points (HQ-0095), the oracle (HQ-0096 ②), a device in the runtime's container (OD-33 ⑨), `device_unavailable` (HQ-0097 (a)); coder-written vendor code (the vendor-language kind, HQ-0092 (a)).
- LLM-level evaluation, its unit, metrics and key (P3-12, OD-33 ⑤, HQ-0096 ①); GPU or NPU memory figures (OD-33 ⑥).
- Bundles of several files, own build settings, own inputs or expected output, other languages (decision 2); round 0 with N > 1 in a given-code run (OD-28); cases and model runs of a given-code run (FR-18).

## References

- Owner: HQ-0092, HQ-0097 in `PROCESS/STATE.json`; HQ-0089 ④; D6, D23, D27, D29.
- [Requirements](../Requirements.md): FR-1, FR-9, FR-13, FR-15, FR-17, FR-19; rows OD-28, OD-33. [OpenDecisionProposals](../OpenDecisionProposals.md) § OD-28, § OD-33; [StandardScenarios](../StandardScenarios.md) S12; [UsageCases](../UsageCases.md) UC-E5.
- Records: ADR-0001, ADR-0004, ADR-0005, ADR-0018, ADR-0024, ADR-0025, ADR-0030, ADR-0055, ADR-0075, ADR-0076, ADR-0116, ADR-0119, ADR-0121, ADR-0142, ADR-0155, ADR-0177, ADR-0185, ADR-0192, ADR-0193, ADR-0194, ADR-0195, ADR-0197, ADR-0198.
- Code read: `hilclaw/instance.py`, `instance_file.py`, `instance_start.py`, `artifacts.py`, `cas.py`, `targets.py`, `check_tool.py`, `run_tool.py`, `round_end_tool.py`, `run_file_tools.py`, `journaled_tool.py`, `hw_tool.py`, `spec_tool.py`, `attempt_kernel.py`.
- Process: [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §3 ("승인된 열린 목록"), §5, §6 D27, §8, §9; [PROCESS/PLAN.md](../../PROCESS/PLAN.md) P3-11; task T-0560.
