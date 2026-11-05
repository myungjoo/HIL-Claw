---
id: T-0551
title: Apply HQ-0091 ① (a)·② (a) for PLAN P3-3 — write the §9 ADR that widens the instance-start scope (ADR-0076 decision 1) and the oracle to bf16 instances at `virtual_npu`, offer `correctness.check` there, turn on its `instance_start`, and admit at each target only the contracts it serves
phase: P3
status: IN_PROGRESS
commitMode: code
coversReq: [D27, OD-32, FR-9, OD-31, FR-10, NFR-6, "PLAN P3-3", HQ-0091]
dependsOn: [T-0550]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0197-od32-virtual-npu-oracle-and-instance-start.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
  - hilclaw/targets.py
  - hilclaw/check_definition.py
  - hilclaw/check_tool.py
  - hilclaw/instance_start.py
  - hilclaw/start_instance.py
  - hilclaw/model_instances.py
  - tests/test_targets.py
  - tests/test_check_definition.py
  - tests/test_check_tool.py
  - tests/test_instance_start.py
  - tests/test_start_instance.py
  - tests/test_model_instances.py
estimatedSize: {loc: 400, files: 10}
hq: []
---
## Why

**PLAN P3-3** (virtual NPU) is the first unchecked P3 item that is not "오너 확정 필요". ADR-0193 decision 4 left two things of `virtual_npu` to the owner (O4, asked as **HQ-0091**): the oracle and tolerance there, and whether it holds a type the CPU lacks. Until then `virtual_npu` has `instance_start` false and its backend offers no `correctness.check` (`not_offered`). ADR-0193 decision 8's P3-3 row says the item is not checked before O3 (HQ-0090) and O4 are answered.

The owner answered **HQ-0091** on 2026-11-05 (commit `c1d2f567`), verbatim source in `STATE.json` `humanQuestions` HQ-0091 `decision`:

> ① (a) the bf16 contracts' existing reference and the user's tolerance apply at this check backend (`virtual_npu`) only, and `instance.json`'s required members are those of `cpu_standin` — not the general answer of #5 B-7. ② (a) no new format: the difference of the served set (the six bf16 contracts, fp32 `gemm` refused) is the data-type difference.

The integrator's note in that `decision` (not the owner's words) names the follow-up as "a small task that gives `virtual_npu`'s backend a `correctness.check` and turns on `Target.instance_start`, whose §9 ADR widens ADR-0076 decision 1's scope to `virtual_npu` instances of a bf16 op_signature; `model_run` false and the exclusion from the S6 metric stay (ADR-0193 decisions 1, 4)". This task is that follow-up. ② (a) needs no code: it closes P3-3's data-type difference as it stands.

**Why after T-0550.** Both tasks touch `hilclaw/targets.py`; T-0550 lands ADR-0196 slice 2 (`virtual_npu` reports `cycles`). This task depends on none of T-0550's decisions (ADR-0196 already made them); the dependency is only file overlap. With both landed, every difference P3-3 names (flags, memory, data types, unit) exists and the oracle answer is applied, so **the executor states in `## Result` whether PLAN P3-3's completion condition now holds** (ADR-0193 decision 8's P3-3 row); the driver checks the box (DRIVER §3-6).

**Order (DRIVER §6 D27 ①).** As T-0550's Why. If a `nightly-failure` issue, an RA `실패` item or a P2-15 preparation has appeared when this task runs, report it in `## Result` and stop before writing code.

**Open HQs (D27 ⑦).** Do not ask again or anticipate: HQ-0081, HQ-0083 (fp16 — not asked again, D27 ④), HQ-0085 (gates), HQ-0093, HQ-0095, HQ-0096 (oracle at **vendor** targets — this task decides nothing there), HQ-0097, HQ-0088/0089 (candidate kinds; a new numeric format comes with them). If the work shows a further owner-only part none of these covers, write the question in `## Result` in the DRIVER §8 structure (Korean), land the rest and return `DONE` (D27 ⑥).

## Required Reading

- `PROCESS/DRIVER.md`:
  - **§3-5 and §5**: branch `claude/T-0551-<slug>`, the `Task: T-0551` trailer and the PR body's last line, size (≤ 10 non-test files; 600 changed lines advised), tests (D12), list assertions (D21), storage (D29: temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0551/`, removed with `rm -r` at the end).
  - §3 "BLOCKED 사유" and "승인된 열린 목록" (what is and is not a frame change); §6 D27 (⑥, ⑦); §9 (the ADR path: executor ADR + reviewer Approve + owner notice on #5).
- `PROCESS/STATE.json` `humanQuestions`: **HQ-0091** (question and `decision`), HQ-0096 ② (vendor oracle, not to be anticipated).
- `ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md`: decision 1 (`model_run`, S6), decision 3 (`Target`, `instance_start`), **decision 4** (the virtual NPU table and "What this table cannot decide: the oracle and tolerance outside `cpu_standin`"), decision 8 (P3-3 row), decision 9 (O4).
- `ARCHITECTURE/decisions/ADR-0076-*.md` **decision 1** (scope: accelerators and covered op_signatures; "nothing is required … and nothing is allowed") and decision 2 (required set), Boundaries.
- `ARCHITECTURE/decisions/ADR-0016-*.md` decisions 2 to 5 (backend table, `not_offered`, `no_backend`); `ARCHITECTURE/decisions/ADR-0130-*.md` decision 2.
- `ARCHITECTURE/decisions/ADR-0177-*.md` decision 2 (coverage predicates `check_covers`/`run_covers`/`start_covers`); `ARCHITECTURE/decisions/ADR-0181-*.md` decision 8 (bf16 contracts at the start).
- `ARCHITECTURE/decisions/ADR-0196-od32-measurement-unit-list-and-run-result-v3.md` (as landed by T-0549/T-0550; nothing here changes it).
- `ARCHITECTURE/Requirements.md` FR-9 (the reference settled for `cpu_standin` by HQ-0004) and the OD-32 row.
- Code: `hilclaw/targets.py` (`VIRTUAL_NPU`, `instance_start_accelerators`), `hilclaw/check_definition.py` (`default_table`, `definition`), `hilclaw/check_tool.py` (`tool_function`, where the backend is selected and `check_admission.admit` gets `covers`), `hilclaw/run_tool.py` (`_target_of`, `_at_target` — the existing per-target join to copy the form of), `hilclaw/contract_table.py` (`check_covers`, `start_covers`, `served_at`), `hilclaw/standin_check.py` (`operation_for`), `hilclaw/instance_start.py` (`prepare`, `OutOfScopeError`), `hilclaw/start_instance.py` (`_ACCELERATORS`), `hilclaw/model_instances.py` (~line 150-190), `hilclaw/new_run.py` (refusal messages), `hilclaw/s6_metric.py` (`_ACCELERATORS` — must stay as is), `hilclaw/standin_profile.py` (`local_record` for `virtual_npu`).
- Recording rules — follow these, do not copy earlier task files' wording:
  - `ARCHITECTURE/Requirements.md` "**행 형식**" (the paragraph before the OD register).
  - `ARCHITECTURE/OpenDecisionProposals.md` header "**기록 규칙**".
  - `ARCHITECTURE/StandardScenarios.md` § 검사 결과, its first paragraph (기록 규약).

## Acceptance Criteria

1. **The ADR** `ARCHITECTURE/decisions/ADR-0197-<slug>.md` (next free number; adjust the `touchesFiles` name if the slug differs) records under §9 the record's part of HQ-0091 ① (a)·② (a), citing the owner's answer as the owner's and marking the integrator's and the record's readings as such. It decides at least:
   1. **Scope**: ADR-0076 decision 1 is widened to instances whose `hw_profile.record` names `virtual_npu` and whose stated op_signature is covered by a contract `virtual_npu` serves (the six bf16 contracts); with no stated op_signature, what the start does at `virtual_npu` (decide and give the reason). The required set is `cpu_standin`'s (owner). State that this is no general answer to #5 B-7 and says nothing of vendor targets (HQ-0096 ②).
   2. **The oracle**: `correctness.check` at `virtual_npu` uses the bf16 contracts' existing reference and the user's tolerance, through `standin_check.operation_for` of the `virtual_npu` `Target` (its flags and its memory bound on the verification container, ADR-0193 decision 4).
   3. **Admission per target** for `correctness.check` and the instance start, in the form of `run_tool`'s per-target join (ADR-0193 decision 4): at a target, only a record whose covering entry the target serves is covered; so fp32 `gemm` at `virtual_npu` is `op_signature_not_covered` at the check tool and `OutOfScopeError` at the start (② (a): this is the data-type difference). Decide where the join lives (for example a `covers` that takes the accelerator, or a binder per accelerator) with the reason; `cpu_standin` and the mock answer exactly as today.
   4. **What stays**: `virtual_npu` keeps `model_run` false; the S6 metric keeps admitting only `cpu_standin` and the mock (`outside_metric` otherwise); no `instance.json`, spec, result or `STATE.json` member, event kind, `step` value or layout version changes; fp16 is not touched (HQ-0083 (b)).
   5. **A-13 reading**: no frame change — a widened scope of an existing check and a boolean of package source; name the owner's answer as the source of the oracle; no BLOCKED reason remains.
   6. **Consequences**: list the sentences of earlier records made less exact and not edited (at least ADR-0076 decision 1's accelerator list, ADR-0193 decision 4's "Until it is answered, `virtual_npu` has `instance_start` false …", the docstrings that say `virtual_npu` offers no `correctness.check`, RA's note that only the timing process is checked) — do not edit those records; module docstrings this task touches are updated.
   7. **Boundaries**: the oracle at vendor targets (HQ-0096 ②), new numeric formats (with HQ-0088), model runs at `virtual_npu`, which execution is which point (HQ-0095).
2. **Registers**, by their recording rules (Required Reading), with no restatement of the record and no dated paragraphs: `ARCHITECTURE/Requirements.md` — one link to the new ADR in the `**확정분**:` of each OD row it answers part of (at least OD-32), the `**잔여**:` rewritten in place; `ARCHITECTURE/OpenDecisionProposals.md` § OD-32 — one adopted-ADR line, ③'s oracle and data-type parts' end state and bullet status word rewritten in place; `ARCHITECTURE/StandardScenarios.md` — re-check coverage by its rules and update the "최근 재검사" line in place, adding to "판정 변화 이력" only if a verdict changes or a gap opens or closes. Touch FR-9's row only if its recording rule requires a link for this kind of scope widening, and say which way you read it.
3. **Code**:
   - `hilclaw/targets.py`: `VIRTUAL_NPU` has `instance_start` true; the docstring says so, citing the new ADR.
   - `hilclaw/check_definition.py`: the `virtual_npu` backend offers `correctness.check` with `standin_check.operation_for(<virtual_npu Target>)` besides `sim.run`/`board.run`; docstring updated.
   - `hilclaw/check_tool.py` (or where ADR criterion 1.3 places it): the per-target admission join.
   - `hilclaw/instance_start.py` / `hilclaw/start_instance.py` / `hilclaw/model_instances.py`: the start admits `virtual_npu` (its `_ACCELERATORS` is read from `targets.instance_start_accelerators()`) and refuses at a target a record of a contract it does not serve; `model_instances` keeps building model instances at `cpu_standin` only (model runs need `model_run`), changing only if the new covers form requires it.
   - Every existing behaviour at `cpu_standin` and the mock is unchanged.
4. **Tests** (D12: happy, error, branch and negative; every public function of a touched module). At least: the backend table offers `correctness.check` at `virtual_npu`, and the operation is built with the `virtual_npu` `Target` (memory bound passed to the verification container, stub Docker client); `correctness.check` at `virtual_npu` of a bf16 record is admitted and of fp32 `gemm` is `op_signature_not_covered` (negative); the start of a `virtual_npu` bf16 instance writes `instance.json`, and of a `virtual_npu` fp32 `gemm` instance raises `OutOfScopeError` (negative); an instance missing a required member at `virtual_npu` raises `MissingMembersError` as at `cpu_standin`; an unknown accelerator is still out of scope; `cpu_standin` and mock behaviour unchanged (existing tests pass); `instance_start_accelerators()` returns both targets. Coverage of `hilclaw/` stays ≥ 80 % line and function. No Docker, no `claude`, no network.
5. **List assertions (D21)** expected to change, only as far as needed, each listed in the PR body: the backend table's tool lists in `tests/test_check_definition.py`; `instance_start_accelerators` / `_ACCELERATORS` equalities in `tests/test_targets.py` and `tests/test_start_instance.py`; the `VIRTUAL_NPU` field values in `tests/test_targets.py`; any public-name set of a touched module. Tests that assert `virtual_npu` answers `not_offered` for `correctness.check` or is out of the start's scope change because that behaviour is this task's change; list them too. No other existing assertion changes.
6. **Size**: about 400 changed non-test lines including the ADR, ≤ 10 non-test files (4 documents + at most 6 modules). If another module is needed, drop `model_instances.py` first if it needs no change; never exceed the cap — record any overflow as a follow-up.
7. **Language**: Python, as the existing modules (one line in the commit body).
8. **§9 notice**: after landing, post the owner notice on #5 as §9 requires (the ADR, the OD parts it answers, the 7-day objection period), and record the comment link in `## Result`.
9. `## Result` lists: PR and merge commit, review rounds, the ADR's decisions in one line each, **whether PLAN P3-3's completion condition now holds** (with the reason against ADR-0193 decision 8's P3-3 row), any runtime acceptance item in the RuntimeAcceptance form — at least that a `correctness.check` at `virtual_npu` on a real container runs within the memory bound and gives the bf16 contract's verdict (the existing `virtual_npu` memory item of `PROCESS/RuntimeAcceptance.md` names the timing process only) — and any new owner-only question in the §8 form.

## Out of Scope

- The unit change and the v3 writers (T-0550, ADR-0196).
- Model runs at `virtual_npu` (`model_run` stays false), the S6 metric's accelerators.
- Any new numeric format (`int8` etc.), fp16, the oracle at vendor targets, any vendor backend change.
- Editing earlier ADRs (list them in Consequences), PLAN (the driver checks P3-3), RuntimeAcceptance.md (the driver adds items).
- Any `claude` process, Docker run or vendor tool.

## Follow-ups

## Result
