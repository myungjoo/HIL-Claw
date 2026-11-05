# ADR-0197: The oracle and the instance start at `virtual_npu` (the owner's answer to HQ-0091 ① (a)·② (a)) — ADR-0076 decision 1 widened to `virtual_npu` instances of a contract it serves with `cpu_standin`'s required set, `correctness.check` offered there with the bf16 contracts' existing reference and the user's tolerance through the operation built with its target, and admission read at the target of the run in the check tool and the start (part of OD-32 ③, OD-31 ③ and OD-8)

## Status

- **Accepted on 2026-11-05** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed what this record decides.** The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **Three kinds of content.**
  - **Owner**, marked so: the answer to HQ-0091 (2026-11-05). The owner's words are **not subject to the objection window** above.
  - **The integrator's reading, cited and not this record's**: the note in HQ-0091's `decision` that marks itself "통합자 독해(오너의 말이 아님)".
  - **This record's own**: every other sentence — the start without an `op_signature`, the place of the join, the A-13 reading and every weighing.
- **Answers** part of **OD-32** ③ (the oracle at the virtual NPU and its data-type difference), part of **OD-31** ③ (the oracle and tolerance of the six bf16 contracts at a target other than `cpu_standin`) and part of **OD-8** (the scope of [ADR-0076](ADR-0076-od8-instance-start-required-members.md), "ADR-0076 범위 밖의 instance"). Each OD keeps its status. It is **no answer to #5 B-7** in general and says nothing of vendor targets (HQ-0096 ②).
- **Session entry check** (CLAUDE.md), on 2026-11-05 at `main` `f5fc532d`: open PRs — none; no open `nightly-failure` issue; no `실패` item in `PROCESS/RuntimeAcceptance.md`; no P2-15 preparation pending; issue #4 last comment 2026-07-31, #5 2026-11-05, #7 2026-09-07, #8 closed. Unresolved HQs: HQ-0081, HQ-0093, HQ-0095, HQ-0096, HQ-0097. None is crossed: HQ-0095 (which execution is which point) and HQ-0096 (vendor oracle) are named in Boundaries and not anticipated.
- **Code** lands with this record. No `claude` process was started, nothing was built or run in a container, and nothing needs a board or a key (D16). Statements about code are observations of `main` at `f5fc532d`. The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **The owner's answer** (**owner**, HQ-0091, 2026-11-05; the `decision` of HQ-0091 in `PROCESS/STATE.json`, verbatim up to the integrator's note): "① (a)·② (a) — 오너(채팅, 2026-11-05): \"예, ①(a)·②(a) 기록\". ① (a) bf16 계약의 기존 reference와 사용자가 정하는 허용 오차를 이 검사용 백엔드(`virtual_npu`)에 한해 그대로 쓰고, `instance.json`의 요구 멤버는 `cpu_standin`과 같게 한다 — #5 B-7의 일반 답이 아니다. ② (a) 새 형식 없음: 지원 집합의 차이(bf16 여섯 계약만 받고 fp32 `gemm`을 거부)만 데이터 타입의 차이로 본다."
- **The integrator's note** in the same `decision` (cited, not the owner's words): the follow-up gives `virtual_npu`'s backend a `correctness.check` and turns on `Target.instance_start`; its §9 ADR widens ADR-0076 decision 1's scope to `virtual_npu` instances of a bf16 op_signature; `model_run` false and the exclusion from the S6 metric stay (ADR-0193 decisions 1 and 4); a new numeric format is asked with quantization settings (HQ-0088); fp16 is asked again after P2-15 (HQ-0083 (b)); P3-3 is checked after this answer and HQ-0090's are applied (ADR-0193 decision 8).
- **Today** (cited): [ADR-0193](ADR-0193-od32-generalization-design.md) decision 4 gives `virtual_npu` the six bf16 contracts in `contracts`, the flags, the memory bound and (by [ADR-0196](ADR-0196-od32-measurement-unit-list-and-run-result-v3.md)) `cycles`; it held `instance_start` false and offered no `correctness.check` (`not_offered`, [ADR-0016](ADR-0016-od18-backend-frame.md) decision 3) until O4 ① was answered. ADR-0076 decision 1 scopes the start to `cpu_standin` and the mock and says of every other instance that "nothing is required of it here and nothing is allowed". [ADR-0177](ADR-0177-od18-od6-contract-table.md) decision 2 binds `check_covers` to the check tool and `start_covers` to the start.
- **Observations** (code at `f5fc532d`): `standin_check.operation_for(target)` already builds the verification operation with a target's flags, time limits and memory bound on the process container; `contract_table.served_at` answers a target's part alone; `run_tool` joins its bound predicate to `served_at` at the run's target (`_target_of`, `_at_target`); `check_tool` and `start_instance` hand their predicate on unjoined; `start_instance._ACCELERATORS` is read from `targets.instance_start_accelerators()`; `model_instances` imports it; `s6_metric._ACCELERATORS` is a literal (`cpu_standin`, mock).

## Decision

### 1. Scope of the start

- **ADR-0076 decision 1 is widened**: besides an instance whose `hw_profile.record` names `cpu_standin` or the mock, it covers **an instance whose `hw_profile.record` names `virtual_npu` and whose stated `op_signature` is covered by a contract `virtual_npu` serves** — today the six bf16 contracts. ADR-0076 decisions 2 to 5 apply to it unchanged: **the required set is `cpu_standin`'s** (**owner** ① (a): "`instance.json`의 요구 멤버는 `cpu_standin`과 같게"), `n_max` and `coder_model` are filled in as there, and a refusal writes nothing.
- **With no stated `op_signature`** a `virtual_npu` instance is in scope, as at `cpu_standin`, and is refused with `MissingMembersError` naming `op_signature` (ADR-0076 decision 2: `op_signature` is required). *Why*: telling scope apart before the required set would leave such an instance outside, where nothing is required, and so give it no report of its missing member; reading it in scope gives the same refusal at every target of decision 1, and since the start writes nothing without a stated and covered `op_signature`, no instance of a contract `virtual_npu` does not serve can start there.
- **Not widened**: any other accelerator, vendor targets included (HQ-0096 ②), and any stated op_signature no served contract covers. This is **no general answer to #5 B-7** (**owner**).

### 2. The oracle at `virtual_npu`

- **`correctness.check` at `virtual_npu` judges a run of a bf16 contract with that contract's existing reference and the tolerance the instance states** (**owner** ① (a)): the verification run, float64 reference and calibration of [ADR-0163](ADR-0163-od31-bf16-verification-run.md) to [ADR-0165](ADR-0165-od31-bf16-sdpa-kv-cache-verification-run.md), unchanged, and the v2 result of ADR-0183 decision 3.
- **The operation is `standin_check.operation_for` of the `virtual_npu` `Target`**: its flags, trailing and waiter flags, time limits and the memory bound on each process container (ADR-0193 decision 4). A verification process ended over the bound is answered as any non-zero status (`exit_status`), as `operation_for` already does. The backend table's `virtual_npu` entry offers `correctness.check`, `sim.run` and `board.run`, each built with that one target when the table is built, and no `profiler.collect` (ADR-0130 decision 2 as at `cpu_standin`).

### 3. Admission at the target

- **At a target only a record whose covering entry the target serves is covered** (ADR-0193 decision 4): the bound predicate answers `True` and `served_at` answers `True`. So **fp32 `gemm` at `virtual_npu` is `op_signature_not_covered` at the check tool and `OutOfScopeError` at the start**; that refusal is the data-type difference (**owner** ② (a): "지원 집합의 차이 … 만 데이터 타입의 차이로 본다").
- **Where the join lives: one binder in the target table, `targets.covers_at(covers, accelerator)`**, which returns `covers` joined to `served_at` at the target of `accelerator`, or `covers` itself for a name with no target (the mock). The check tool calls it with the run's `accelerator` after `instance.json` is read; the start calls it when `prepare` asks its predicate, which is after the document is valid and its accelerator in scope. *Why a binder and not a `covers` that takes the accelerator*: `check_admission.admit` and `instance_start.prepare` take a predicate of one record (ADR-0041 decision 5), and both stay unchanged; *why in `targets`*: it is the module that knows whether a name has a target and reads its `contracts`, and two callers share one form instead of two copies of `run_tool`'s. `run_tool` keeps its own join, which answers the same.
- **`cpu_standin` and the mock answer exactly as before**: `cpu_standin` serves every entry, so the join changes no answer there; the mock has no target and keeps its predicate. `model_instances` hands `prepare` the start's predicate in the same form, so its documents are still "ones the start accepts".

### 4. What stays

- `virtual_npu` keeps `model_run` false; the S6 metric keeps admitting only `cpu_standin` and the mock (`outside_metric` otherwise, `s6_metric._ACCELERATORS` unchanged); the `model_instances` command still writes documents for the hw_profile it reads, `cpu_standin`'s; its `documents` function, given another hw_profile, accepts what the start accepts there (decision 3), `virtual_npu`'s included.
- No member of `instance.json`, a spec, a result or `STATE.json`, no event kind, no `step` value and no layout version changes. fp16 is not touched (**owner**, HQ-0083 (b)). No numeric format is added (**owner** ② (a)).

### A-13 reading

- **No frame change.** The record widens the scope of an existing check (the start's required set, applied unchanged to more instances) and turns on a boolean and an operation in package source (`Target.instance_start`, the backend table; ADR-0193 decision 3: no data-plane value). The check result is the existing v2 result. No approved open list is used.
- **The oracle is the owner's** (HQ-0091 ① (a)), and so is the reading of the data-type difference (② (a)); what this record adds is the detail of decisions 1 and 3 above.
- **No BLOCKED reason remains**: no new dependency, no schema change, no owner part left undecided by the answer.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 1 | A `virtual_npu` instance without `op_signature` out of scope | It would get no report of its missing member, unlike the same document at `cpu_standin` |
| 3 | `check_admission.admit` and `instance_start.prepare` take the accelerator | Changes two accepted interfaces to carry what one binder gives |
| 3 | Copying `run_tool`'s private join into each caller | Three copies of one rule |
| 3 | Narrowing `contract_table.check_covers` / `start_covers` by a target argument bound per accelerator in the registry | The registry binds before any run is read; the accelerator is known only per call |

## Consequences

- **PLAN P3-3**: with ADR-0196's slice 2 (T-0550) and this record, every difference P3-3 names exists — flags, memory bound, data types (the served subset, by ② (a)), unit `cycles` — and the oracle answer is applied; ADR-0193 decision 8's condition for checking the item is met.
- **Runtime acceptance item**: on a runtime machine with Docker and the clang image, a `correctness.check` at `virtual_npu` of a bf16 instance runs its verification process within the memory bound (`--memory`/`--memory-swap` 268435456) and returns the bf16 contract's verdict; the existing `virtual_npu` memory item names the timing process only.
- **Less exact, not edited** (the docstrings this task touches are updated; the list is what a search of these records and of `hilclaw/` found, not claimed complete):
  - ADR-0076 decision 1 (the accelerator list "`cpu_standin` or the mock") and Boundaries ("Instances outside decision 1: other accelerators").
  - ADR-0193 decision 4 ("Until it is answered, `virtual_npu` has `instance_start` false and its backend offers no `correctness.check`, which answers `not_offered`", the table row "`model_run` … needs O4 ①") and decision 9's O4.
  - ADR-0196 Boundaries ("Left to HQ-0091's follow-up task").
  - `PROCESS/RuntimeAcceptance.md`, the `virtual_npu` memory item: "`virtual_npu`는 아직 `correctness.check`를 제공하지 않으므로(HQ-0091) 확인 대상은 timing process뿐이다".
  - Docstrings not touched here that name `virtual_npu`'s check as not offered: none found beyond `hilclaw/check_definition.py`, `hilclaw/targets.py`, `hilclaw/start_instance.py` and `hilclaw/instance_start.py`, which this task updates.

## Boundaries (not decided here)

- The oracle and tolerance at vendor targets (HQ-0096 ②); the general answer of #5 B-7.
- New numeric formats (with HQ-0088); fp16 (HQ-0083 (b)).
- Model runs at `virtual_npu` (`model_run`), the S6 metric's accelerators (HQ-0081's neighbour).
- Which execution is which point (HQ-0095).
- Any change to an accepted record, to `orchestration/` or to `catalog/`.

## References

- Owner: HQ-0091 in `PROCESS/STATE.json`; HQ-0083, HQ-0088, HQ-0096 where named; D6, D27.
- [Requirements](../Requirements.md): FR-9, FR-10, NFR-6; rows OD-8, OD-31, OD-32. [OpenDecisionProposals](../OpenDecisionProposals.md) § OD-8, § OD-31, § OD-32; [StandardScenarios](../StandardScenarios.md).
- Records: ADR-0016, ADR-0041, ADR-0076, ADR-0130, ADR-0163 to ADR-0165, ADR-0177, ADR-0181, ADR-0183, ADR-0193, ADR-0196.
- Code read: `hilclaw/targets.py`, `check_definition.py`, `check_tool.py`, `run_tool.py`, `contract_table.py`, `standin_check.py`, `instance_start.py`, `start_instance.py`, `model_instances.py`, `new_run.py`, `s6_metric.py`.
- Process: [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §3, §5, §6 D27, §8, §9; [PROCESS/PLAN.md](../../PROCESS/PLAN.md) P3-3; task T-0551.
