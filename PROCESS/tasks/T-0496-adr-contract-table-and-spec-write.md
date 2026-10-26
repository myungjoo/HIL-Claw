---
id: T-0496
title: Write the ADR on how the seven kernel contracts reach the instance start, spec.write, correctness.check, sim.run and board.run (OD-18, OD-6), and land its first code slice — one contract table and spec.write composing the spec of every contract in it
phase: P2
status: BLOCKED
commitMode: code
coversReq: [C-6, FR-5, FR-10, OD-6, OD-18, OD-31, "PLAN P2-11", "PLAN P2-14"]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0177-od18-od6-contract-table.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
  - hilclaw/contract_table.py
  - hilclaw/spec_tool.py
  - hilclaw/start_instance.py
  - hilclaw/check_definition.py
  - hilclaw/run_definition.py
  - tests/test_contract_table.py
  - tests/test_spec_tool.py
  - tests/test_start_instance.py
  - tests/test_check_definition.py
  - tests/test_run_definition.py
  - tests/test_gemm_contract.py
  - tests/test_gemm_bf16_contract.py
  - tests/test_rmsnorm_bf16_contract.py
  - tests/test_elementwise_add_bf16_contract.py
  - tests/test_swiglu_bf16_contract.py
  - tests/test_rope_bf16_contract.py
  - tests/test_sdpa_kv_cache_bf16_contract.py
estimatedSize: {loc: 560, files: 9}   # non-test: ADR ~300 lines, hilclaw/contract_table.py ~150, spec_tool.py ~40 (check 5 and composition through the table, docstring), start_instance.py / check_definition.py / run_definition.py ~10 each (the predicate taken from the table, docstrings), Requirements/OpenDecisionProposals/StandardScenarios ~10. The module name `contract_table` is a suggestion; the executor may choose another and adjust touchesFiles in the PR body. Tests are outside the cap (DRIVER §5, D4/D20).
hq: [HQ-0077]
---
## Why

**State.** PLAN P2-13 (model executor) was checked by T-0495 (PR #308, `main` `f0dbab88`). PLAN P2-14 (Llama 3.2 1B end-to-end, the D18 goal) needs "P2-11의 각 연산에 대해 instance가 커널을 내고, P2-13의 실행기가 그 커널로 토큰을 생성해 reference와 맞는다". Today an instance can only be about one contract: fp32 `gemm` (ADR-0008). Four places hold that as the predicate "covered" of ADR-0041 decision 5, each bound to `hilclaw.gemm_contract.covers`: the instance start (`hilclaw/start_instance.py`), `spec.write` (`hilclaw/spec_tool.py` check 5, and its composition calls `gemm_contract.task_contract(m, k, n)`), `correctness.check` (`hilclaw/check_definition.py`) and `sim.run` / `board.run` (`hilclaw/run_definition.py`). The six bf16 contracts of P2-11 exist as records and modules — ADR-0156 (`gemm` bf16), ADR-0158 (`rmsnorm`), ADR-0159 (`elementwise_add`), ADR-0160 (`swiglu`), ADR-0161 (`rope`), ADR-0162 (`sdpa_kv_cache`), each with `op_signature_record`, `covers` and `task_contract` in `hilclaw/*_bf16_contract.py` — and their verification runs exist in the harness (ADR-0163, ADR-0164, ADR-0165; `hilclaw/harness/bf16_*verification*.py`). But no record says how a run reaches them: ADR-0163 Boundaries leaves "How a check or an instance reaches these runs: `correctness.check` for bf16 kinds, the instance start and the spec (OD-18, OD-6, ADR-0021, ADR-0041, ADR-0048)", and ADR-0176 Boundaries leaves "Registering the six bf16 kinds with `correctness.check`, `spec.write` and the instance start (OD-18, OD-6)". T-0495's Result names this as the planner's candidate for P2-14.

**This task.** One ADR (DRIVER §9: OD-18 and OD-6 are design-level and driver-closable) that answers that open point for all seven contracts at once (DRIVER §6 "task 단위" ②: the same question per kind goes in one record, as a table), with its first code slice in the same task (DRIVER §6 "task 단위" ①, D20). The slice is: one table of the contracts in `hilclaw/`, and `spec.write` composing the spec of every contract in it. The later slices — `correctness.check` for bf16 kinds on the mock and `cpu_standin`, the timing runs of `sim.run` / `board.run` for bf16 kinds, the binding of the model executor from an instance's kernels (OD-20, OD-7) — are not built here; the ADR names them in landing order for the planner.

**Why the slice stops at spec.write.** The check path takes `m`, `k`, `n` throughout (`hilclaw/check_admission.py` `admit`, `check_parameters`, `check_answer`, `check_judging`, `check_result` — ADR-0042 decision 5 fixes `shape` as "exactly `m`, `k` and `n`" — `mock_check`, `standin_check`), and no record defines a bf16 timing run (ADR-0163 decision 1 and Context: "no bf16 timing run exists"). Widening the predicate of those tools in this task would let a call reach code that cannot serve the kind. Joining the check slice would exceed the size cap with the ADR.

**PLAN order and D18.** P2-11 and P2-14 are PLAN checklist items in the P2 order; the D18 rule does not apply. P2-10 is blocked on HQ-0076 (T-0493). P2-12 (bf16 harness) has its owner answers (HQ-0065, HQ-0066) and its verification runs landed.

**No RuntimeAcceptance `실패` item is fixed by this task** (none exists as of `main` `5a7e41da`).

**D16.** Everything is verified with tests in this repository; nothing starts `claude`, needs a board, a container runtime or real Llama weights.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task format, naming `claude/T-0496-<slug>`, `Task: T-0496` trailer, size cap, test rules D12, list-assertion rule D21), §8 (runtime acceptance items go to `PROCESS/RuntimeAcceptance.md`, D22), §9 (OD closing: ADR + reviewer Approve + owner notice on #5).
- `CLAUDE.md` (rules; "미결은 발명하지 않는다"; "세션 진입 점검"; A-13 BLOCKED reasons, in particular "데이터 plane 스키마 변경"; test rules; language policy).
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph of the OD register (line ~84), and the rows OD-6, OD-18, OD-31.
- `ARCHITECTURE/OpenDecisionProposals.md`: the header's "기록 규칙" (line ~8), and § OD-6, § OD-18, § OD-31.
- `ARCHITECTURE/StandardScenarios.md`: the first paragraph of § 검사 결과 and the rows S0 and S1.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` decisions 2 and 6 (shape members per kind; new values without a version change).
- `ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md` decisions 1 and 5 (one contract per kind, dtype, layout, language; `task.contract`).
- `ARCHITECTURE/decisions/ADR-0041-od18-correctness-check-dimensions.md` decisions 2, 5, 7 and Boundaries (the predicate "covered").
- `ARCHITECTURE/decisions/ADR-0042-od18-correctness-check-result-members.md` decision 5 and its A-13 reading (the result `shape`).
- `ARCHITECTURE/decisions/ADR-0070-od18-correctness-check-registration.md` decisions 3–5; `ARCHITECTURE/decisions/ADR-0167-od18-run-tools-registration.md` decisions 3–5.
- `ARCHITECTURE/decisions/ADR-0076-od8-instance-start-required-members.md` decision 1; `ARCHITECTURE/decisions/ADR-0115-od8-instance-start-performer.md` decision 2.
- `ARCHITECTURE/decisions/ADR-0138-od6-first-case-round-zero-spec.md` decisions 2–3; `ARCHITECTURE/decisions/ADR-0151-od6-first-case-later-round-spec.md` decisions 2–3 (the spec `spec.write` composes; check 7 compares catalog `applies_to` with the record's `kind`, `dtype`, `layout` and the contract's `language`).
- `ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md` (operations, Boundaries) and the six bf16 contract records: ADR-0156 decisions 5, 6, 10; ADR-0158, ADR-0159, ADR-0160, ADR-0161, ADR-0162 — their prototype, operand and `op_signature` decisions only.
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md` decisions 1–3, 10 and Boundaries; ADR-0164 and ADR-0165 decision 1 and Boundaries.
- `ARCHITECTURE/decisions/ADR-0176-od31-model-level-reference-and-comparison.md` Consequences and Boundaries.
- Code: `hilclaw/gemm_contract.py`, `hilclaw/gemm_bf16_contract.py` (and the public names of the five other `hilclaw/*_bf16_contract.py`), `hilclaw/spec_tool.py`, `hilclaw/start_instance.py`, `hilclaw/instance_start.py` (`prepare`'s `covers`), `hilclaw/check_definition.py`, `hilclaw/run_definition.py`, `hilclaw/check_admission.py` (`admit`), `hilclaw/keys.py` (`_SHAPE_MEMBERS`), `hilclaw/model_binding.py` lines 140–185 (its own kind/dtype tables, read only).
- Tests: `tests/test_spec_tool.py`, `tests/test_start_instance.py`, and the pinning tests named in criterion 7.

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md): before editing `ARCHITECTURE/`, check open PRs, Issues #4/#5/#7/#8 and the unresolved `humanQuestions` of `PROCESS/STATE.json` (HQ-0076 is about P2-10 and is not crossed). Name in the ADR's Status what was checked.
2. **ADR-0177** at `ARCHITECTURE/decisions/ADR-0177-<slug>.md`, in the form of the recent ADRs (Status, Context, Decision, Alternatives considered, Consequences, Boundaries, References). It decides, for the seven contracts (fp32 `gemm` of ADR-0008 and the six bf16 contracts), with one table where the question is the same per contract:
   - (a) the one place in `hilclaw/` that lists the contracts a run may be about, keyed by (`kind`, `dtype`, `layout`, `language`), and what each entry gives (at least the predicate "covered" of ADR-0041 decision 5 read per contract, and the `task.contract` of a stated record's shape);
   - (b) for each of the instance start, `spec.write`, `correctness.check`, `sim.run` and `board.run`: which contracts it admits after this task's slice and after each later slice, with the reason. The record must not let the instance start admit a contract that a tool round 0 calls (ADR-0138, ADR-0142) refuses as not covered, unless it states why that is wanted;
   - (c) what `correctness.check` takes and returns for a contract other than fp32 `gemm`: the dimensions (ADR-0041 decision 2 read per kind), the result's `shape` (ADR-0042 decision 5), the judge (ADR-0163 / ADR-0164 / ADR-0165 judges) and what the mock and `cpu_standin` operations are handed — decided here, built in a later slice;
   - (d) what stays open and to which record: the timing run of `sim.run` / `board.run` for bf16 kinds (no record defines one), the binding of the model executor from an instance's kernels (OD-20, OD-7), the orchestration text if any names `gemm` only;
   - (e) the later code slices in landing order, for the planner;
   - (f) an **A-13 reading** in the form of the recent ADRs. If a decision changes the form or meaning of a member of a data-plane file or of a line of `events.ndjson` (for example the `shape` of a check result for kinds whose shape has no `k`), say so plainly. If it is a "데이터 plane 스키마 변경", **stop and return BLOCKED** (CLAUDE.md A-13) with the question for the owner instead of deciding it; ADR-0042's own reading ("the members inside `result` are the interface between layer 1 and layer 2") may be weighed, not assumed.
   Do not decide anything that is owner-only (#5 A/B, C-6, OD-25, OD-3) or invent an undecided value; if one is needed, return BLOCKED with the question.
3. **Register edits** follow the recording rules written in the files — not earlier task files: `Requirements.md` rows OD-6 and OD-18 (and OD-31 if the ADR answers part of it) per the register's "행 형식": one link per new ADR in `**확정분**:`, `**잔여**:` rewritten in place, no restatement of the record and no dated paragraph. `OpenDecisionProposals.md` per its header's "기록 규칙": one `채택분` line per section the ADR answers, the sub-question status rewritten in place. Re-check coverage and update `StandardScenarios.md` § 검사 결과 per its first paragraph (CLAUDE.md "문서 커버리지 재검사"), S0 and S1 at least.
4. **The table module** (suggested `hilclaw/contract_table.py`): lists the seven contracts as ADR-0177 (a) decides, using the existing contract modules' `covers` / `task_contract` / constants — no copy of a contract's constants. It imports no NumPy (the registry and the MCP front must still build without NumPy: `tests/test_check_definition.py::test_building_the_default_registry_imports_no_numpy` and `tests/test_run_definition.py::test_building_the_definitions_and_the_registry_imports_no_numpy` stay green). A record that matches no entry, or matches an entry whose `covers` refuses it, is not covered. `hilclaw/model_binding.py` is not changed.
5. **spec.write** composes, for an `instance.json` whose stated `op_signature` is covered by any entry of the table, the spec whose `task.contract` is that entry's `task_contract` of the record's shape. Every other member of the composed document and every other check of the tool are as ADR-0138 / ADR-0151 fix them. A stated record that no entry covers is answered `op_signature_not_covered` as today, with the module docstring's check 5 and composition paragraphs updated. Tests: for each of the seven contracts, round 0 composes a spec that `hilclaw.spec_file.parse` accepts and whose `task.contract` equals the contract module's `task_contract` for that shape (happy); round ≥ 1 with a technique whose `applies_to` names the bf16 record passes check 7 and one naming fp32 is refused `technique_not_applicable` (branch); a bf16 record with a shape outside the contract's shapes, a record with an unknown `dtype`, and a record of a known kind with another `layout` are refused `op_signature_not_covered` and write nothing (negative).
6. **The other four places** take their predicate from the table as ADR-0177 (b) decides for this slice. Each keeps admitting exactly what (b) says. If (b) says they still admit fp32 `gemm` only, a test shows that the instance start, `correctness.check` and `sim.run` / `board.run` refuse a valid bf16 record as not covered, and that their answers for fp32 `gemm` are unchanged. All existing tests of those modules pass unchanged except the list pins of criterion 7.
7. **D21 list pins.** These assertions pin which modules may name a contract module or which names a module imports and exports. They may be edited only as far as this task's moves require. Foreseen: `tests/test_gemm_contract.py::test_module_is_bound_by_the_registry_the_start_and_the_model_binding_only_and_imports_keys_only`; the six `test_module_imports_keys_only_and_is_bound_by_the_model_binding_only` tests of `tests/test_{gemm,rmsnorm,elementwise_add,swiglu,rope,sdpa_kv_cache}_bf16_contract.py`; `tests/test_check_definition.py::test_the_module_imports_what_it_names_and_has_its_public_names_only`; `tests/test_run_definition.py::test_the_module_imports_what_it_names_and_has_its_public_names_only`; and `tests/test_start_instance.py::test_prepare_is_given_the_bound_accelerators_and_covers` if it pins `gemm_contract.covers` by identity. List each edited assertion in the PR body.
8. **Tests and gates** (D12): a new `tests/test_contract_table.py` covers every public function of the new module: happy (each of the seven contracts), branch (same kind, other dtype; same dtype, other kind), negative (non-mapping record, unknown kind, wrong layout or language, a shape outside a contract's set, a `bool` where an integer is due). Package line and function coverage stay at or above 80%, ruff is clean, and the full local suite passes on Linux/WSL with clang; CI is green.
9. **Owner notice** (DRIVER §9): after merge, one comment on Issue #5 announcing ADR-0177 and the OD rows it changes, ending with `— posted by driver`. Record the comment URL in Result.
10. **Result** names: the language choice and its reason (Python), the PR, review rounds, edited list pins, the later slices in the ADR's landing order (planner's next candidates), and any runtime acceptance item the ADR leaves (expected none; if any, word it for `PROCESS/RuntimeAcceptance.md`, D22).

## Out of Scope

- Changing `correctness.check`'s dimensions, judging, result `shape`, `check_parameters`, `mock_check` or `standin_check` for bf16 kinds (a later slice of ADR-0177).
- A bf16 timing run of `sim.run` / `board.run` (its own record), and the timing driver.
- Deriving the model executor's binding from an instance's kernels or a key's best (OD-20, OD-7); `hilclaw/model_binding.py`.
- fp16 (HQ-0065 (1): after P2-14), OpenMP (PLAN "보류", HQ-0034), the orchestration prompts under `orchestration/` and `.claude/agents/` (unless the ADR finds one that names `gemm` only — then name it in (d), do not edit it here).
- Any deferred line of PLAN "보류".
- Starting `claude`, real weights, a board, an API key (D16).

## Follow-ups

- On the owner's answer to the HQ below: write the answer into ADR-0177 decision 3 (the result of a bf16 check) and its registers on the PR branch, take one more review round, then land PR #309. Slice 1 needs no code change for it.

## Result

**BLOCKED** (CLAUDE.md A-13, data-plane schema change) — PR #309 (Draft, `DONOTMERGE`, branch `claude/T-0496-contract-table-spec-write`, head `90ce5ddb`), not merged.

- **What is on the branch.** ADR-0177 (`ARCHITECTURE/decisions/ADR-0177-od18-od6-contract-table.md`): (a) one contract table `hilclaw/contract_table.py` keyed by (kind, dtype, layout, language) with the seven contract modules and two flags `checked` / `timed`; (b) per place and slice — `spec.write` admits all seven now; `correctness.check` / `sim.run` / `board.run` admit what their flag says; the instance start admits a contract only when it is both checked and timed (every round-0 tool serves it, ADR-0142); fp32 `gemm` only for those four after this slice; (c) what `correctness.check` takes for a bf16 kind (dimensions per kind, seed/draws/tolerance path, judges of ADR-0163/0164/0165, what the mock and `cpu_standin` operations are handed, ADR-0116 build settings read as holding for the bf16 verification builds); **the result form is left to the owner**; (d) open: bf16 timing run (OD-13, OD-16 ⑥), `rope` start position (OD-16 ⑤), catalog entries for bf16 contracts (OD-22), executor binding (OD-20, OD-7); no orchestration prompt names `gemm`/`fp32`; (e) slices in landing order. Code slice 1: `hilclaw/contract_table.py`, `spec.write` through the table, the four other places bound to `start_covers` / `check_covers` / `run_covers` (same answers as before). Registers: Requirements OD-6 / OD-18 rows, OpenDecisionProposals § OD-6 / § OD-18, StandardScenarios (S0 note, 최근 재검사; S0·S1 re-checked, no verdict change). Touched beyond `touchesFiles`: `hilclaw/instance_start.py`, `hilclaw/gemm_contract.py` (one docstring sentence each).
- **Language**: Python — the layer-2 modules this slice joins (contract modules, `spec_tool`, tool definitions) are Python.
- **Review**: round 1 (dev-reviewer, https://github.com/myungjoo/HIL-Claw/pull/309#issuecomment-6418215608) — Request changes: Blocker — decision 3 decided a check result whose `shape` holds each kind's members and an SDPA `counts` member `cache_differs`, which changes the closed result list of ADR-0042; ADR-0063's A-13 reading and ADR-0100 decisions 3–4 treat a change of a landed list as a data-plane schema change put to the owner (precedent HQ-0020). Two Nits (a register typo, a docstring). All addressed in `90ce5ddb`: the result form is no longer decided and is put to the owner (criterion 2 (f)); not yet re-reviewed.
- **Edited list pins / binding tests** (D21): `tests/test_gemm_contract.py::test_module_is_bound_by_the_registry_the_start_and_the_model_binding_only_and_imports_keys_only` (renamed `..._bound_by_the_contract_table_and_the_model_binding_only_...`); the six `test_module_imports_keys_only_and_is_bound_by_the_model_binding_only` (renamed `..._contract_table_and_the_model_binding_only`, binder added); `tests/test_check_definition.py` and `tests/test_run_definition.py` `::test_the_module_imports_what_it_names_and_has_its_public_names_only`; `tests/test_start_instance.py::test_prepare_is_given_the_bound_accelerators_and_covers` and `::test_the_errors_of_prepare_are_the_same_objects`; `::test_the_first_call_binds_the_tool_function_of_the_record` in `tests/test_check_definition.py` and `tests/test_run_definition.py`.
- **Local tests** (WSL, clang, at `c205cf9a`; the later commit changes docs and one docstring): 36228 passed, 50 skipped; `hilclaw/` line coverage 99.8 %, function coverage 100 %; ruff check and format clean. CI had not reported on the branch when this was written.
- **Later slices** (ADR-0177 decision 5, planner's candidates after the answer): 2 — `correctness.check` for bf16 `gemm`, `rmsnorm`, `elementwise_add`, `swiglu`, `sdpa_kv_cache` (needs the HQ answer); 3 — `correctness.check` for `rope` (needs the start position's source, OD-16 ⑤); 4 — the bf16 timing run record (OD-13, OD-16 ⑥) and its code, after which the instance start admits the checked-and-timed contracts.
- **Runtime acceptance items**: none new (the ADR-0116 build settings it extends are RA-0008's).
- **§9 owner notice**: not posted (not merged).
- **HQ (for `PROCESS/STATE.json`, reason: A-13 data-plane schema change)**: 쟁점 — bf16 여섯 계약의 `correctness.check` 결과(`events.ndjson`의 `step_ended` 줄 `result`)는 ADR-0042의 닫힌 목록에 맞지 않습니다: `shape`는 "정확히 `m`·`k`·`n`"인데 `gemm` 밖의 kind에는 `k`가 없고(`rmsnorm`·`elementwise_add`·`swiglu`는 `m`·`n`, `rope`는 `m`·`h`·`d`, `sdpa_kv_cache`는 `m`·`l`·`h`·`h_kv`·`d`), `counts` 항목은 `failed`·`non_finite`뿐인데 SDPA는 캐시 원소의 차이도 판정에 씁니다(ADR-0165 결정 8). ADR-0063의 A-13 읽기와 ADR-0100(결과 정의가 바뀌면 새 `step` 값)에 따라 이는 데이터 plane 스키마 변경입니다. 선택지 — (a) bf16 kind의 검사는 새 `step` 값 둘(sim·board 지점; ADR-0100 결정 3)을 쓰고, 그 결과 목록은 ADR-0042의 목록에서 `shape`를 "기록된 op_signature의 그 kind의 shape 멤버 전부"로, SDPA의 `counts` 항목에 캐시 차이 수 멤버(`cache_differs`)를 더한 것으로 한다(fp32 `gemm`의 기존 값·결과는 그대로); (b) `step` 값은 그대로 두고 ADR-0042의 목록 자체를 (a)처럼 넓힌다(ADR-0100의 예외); (c) SDPA의 캐시 차이를 `failed`에 합쳐 `counts`는 그대로 두고 `shape`만 (a)나 (b)처럼 바꾼다; (d) 그 밖. 막히는 것: ADR-0177 PR #309의 착지와 그 뒤의 bf16 `correctness.check` 슬라이스(P2-11·P2-14 경로). 막히지 않는 것: fp32 `gemm` 첫 사례 전부, 다른 PLAN 항목, PR #309의 슬라이스 1 코드(답과 무관 — 답을 ADR 결정 3에 적고 재리뷰 후 착지).
