---
id: T-0565
title: PLAN P3-15 (1/2) — write the §9 ADR that lets a `catalog/cpu_standin/` entry state the values of any contract of the contract table in `## Applies to`, change the catalog reader and its two users to compare against each entry's own values, and land the first bf16 entries (`gemm` bf16)
phase: P3
status: DONE
commitMode: code
coversReq: [D31, "PLAN P3-15", FR-7, FR-8, OD-22, C-6]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0203-od22-catalog-entries-for-the-bf16-contracts.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
  - hilclaw/catalog.py
  - hilclaw/catalog_tool.py
  - hilclaw/spec_tool.py
  - catalog/cpu_standin/
  - tests/test_catalog.py
  - tests/test_catalog_tool.py
  - tests/test_spec_tool.py
estimatedSize: {loc: 380, files: 9}
hq: []
---
## Why

**PLAN P3-15** (bf16 여섯 kind의 기법 카탈로그 초판) is the next item to plan. Order on `main` `133ef308` (DRIVER §6 D27 ① and D31 ①): no PR is open; the only open `nightly-failure` issue, #373, has T-0559 for its latest report `20261112T000458Z` (BLOCKED on HQ-0100), so no nightly task is due; `PROCESS/RuntimeAcceptance.md` has no item whose `상태` is `실패` (RA-0056 is `미확인`); P3-1 to P3-11, P3-13 and P3-14 are checked; P3-12 waits on the owner (OD-33 ⑤·⑥, OD-32 ⑦), so D31 ① puts P3-15 to P3-17 ahead of it, in listing order. P3-16 waits on HQ-0096 ②. If this has changed when the task runs, report it in `## Result` and stop before writing code.

**What P3-15 asks.** All four entries of `catalog/cpu_standin/` are for fp32 `gemm`, so on a bf16 run `catalog.read` returns no entry and the selector reports `techniques: none` (ADR-0190 decision 3). P3-15 adds technique documents for each of the six bf16 kinds of ADR-0152 decision 2. The form of an entry and the `Applies to` judgement stay those of ADR-0150 and ADR-0190; the frame does not change (if it would, an HQ, D23). OD-22's cold-start policy stays open. The fp32 `gemm` entries and the nightly configuration stay as they are.

**Why a reader change is needed first.** `hilclaw/catalog.py` refuses any entry whose `## Applies to` is not exactly the four fp32 `gemm` lines (`APPLIES_TO`), and `applies`/`mismatch` compare a run against that one constant. ADR-0150 decision 2 fixes those four values for the first case only, and ADR-0190 (Alternatives, Boundaries) and the Requirements OD-22 row leave "첫 사례 밖 … dtype … 의 카탈로그와 그것을 받아들이는 `Applies to`의 형태" to OD-22. That part is design-level (OD-22 is not owner-only), so this task closes it for the `cpu_standin` bf16 contracts by a §9 ADR, as P3-15 asks. The catalog is a source-repository directory, not the data plane (ADR-0150 decision 2; A-13 reading), and a spec still gets exactly `{id, text}`, so no frame changes.

**Brake (D31 ②).** This is a PLAN item that serves the optimization capability (the catalog), not a refinement of the data plane's frame, checks or error paths.

**Split (DRIVER §5, §6 D20).** D20 ① puts the ADR with its first code slice. The ADR, its register edits, the reader and its two users, and the `gemm` bf16 entries come to nine files; adding the other five kinds would exceed the ten-file cap, so they are T-0566. T-0566 depends only on the entry form fixed by criterion 1.2 below.

**Open HQs (D27 ⑦).** Do not ask again or anticipate: HQ-0096 (vendor oracle and LLM-level unit) and HQ-0100 (nightly #373). If the work shows an owner-only part, write the question in `## Result` in the DRIVER §8 structure (Korean: 쟁점, 선택지 (a)/(b)/…, 실행자의 권고, 막히는 것/막히지 않는 것), land the rest and return `DONE` (D27 ⑥).

## Required Reading

- `PROCESS/DRIVER.md`:
  - **§3-5 and §5**: branch `claude/T-0565-<slug>`, the `Task: T-0565` trailer and the PR body's last line, size (D30: ≤ 600 LOC recommended, ≤ 10 files, tests excluded), tests (D12), list assertions (D21), storage (D29: temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0565/`, removed at the end).
  - §3 "BLOCKED 사유" (what a frame change is); §6 D27 (⑥, ⑦), D31 (①, ②); §9 (the ADR path: executor ADR + reviewer Approve + owner notice on #5 with the 7-day objection window).
- `PROCESS/PLAN.md` P3-15 (line ~79) and the paragraph above P3-15 (line ~77).
- `ARCHITECTURE/Requirements.md`: FR-7, FR-8, C-6, the OD-22 row, and "**행 형식**" (the paragraph before the OD register).
- `ARCHITECTURE/OpenDecisionProposals.md`: header "**기록 규칙**"; § OD-22.
- `ARCHITECTURE/StandardScenarios.md`: S1 (step 4) and S0; the first paragraph of §검사 결과. `ARCHITECTURE/UsageCases.md` UC-5.
- ADRs: `ADR-0150-od22-first-case-technique-catalog.md` (decisions 1–5, Consequences, Boundaries — the form, the id rules, the text rules this ADR adapts); `ADR-0190-od22-catalog-read-by-contract-and-coder-every-shape.md` (decisions 2, 3, 5 — the filter and the predicate's one place); `ADR-0171-od23-first-case-round-techniques-and-coder-delegation.md` decision 3; `ADR-0151-od6-first-case-later-round-spec.md` decision 2 (b); `ADR-0177-od18-od6-contract-table.md` decision 1 (the table and its key); `ADR-0152-od31-llama-forward-operations.md` decision 2 (the six kinds); `ADR-0156-od31-bf16-gemm-contract.md` (decisions 3–9: precision, fp32 accumulation, the fp32 → bf16 conversion, prototype, guarantees and obligations, what the source provides); `ADR-0116-od18-cpu-standin-build-settings.md` and `ADR-0188-od18-standin-openmp-in-the-build-set.md` (the fixed build settings and OpenMP on `cpu_standin`); `ADR-0001-od4-key-schema.md` ("Record format" and the *name* form).
- Code: `hilclaw/catalog.py`, `hilclaw/catalog_tool.py` (`_applicable`), `hilclaw/spec_tool.py` (the technique lookup around line 510–540 and its docstring lines 55–70), `hilclaw/contract_table.py` (`TABLE`, `entry`), `hilclaw/gemm_bf16_contract.py`, `catalog/cpu_standin/*.md` (the existing four entries as the model of form and tone).
- Tests: `tests/test_catalog.py`, `tests/test_catalog_tool.py` (the section "Which entries apply to the run (ADR-0190)", about lines 425–600), `tests/test_spec_tool.py` (the entry helper near line 804 and the bf16 later-round tests near lines 1200–1290).

## Acceptance Criteria

1. **ADR-0203** (`ARCHITECTURE/decisions/ADR-0203-od22-catalog-entries-for-the-bf16-contracts.md`; take the next free number if 0203 is taken), in the ADR-0001 record format, Status marking it a §9 record (executor + reviewer, owner notified on #5) and citing PLAN P3-15 and D31 as the owner-approved item it serves. It decides:
   1. **Scope**: `catalog/cpu_standin/` and runs whose accelerator is `cpu_standin` and whose op_signature is covered by a contract of `hilclaw.contract_table.TABLE` (the fp32 `gemm` contract and the six bf16 contracts). `virtual_npu`, vendor targets, the mock and other candidate kinds stay outside (Boundaries).
   2. **The form of `## Applies to`**: still exactly four list lines in the order `- kind: <v>`, `- dtype: <v>`, `- layout: <v>`, `- language: <v>`, with the values of **one key of the contract table** (`kind`, `dtype`, `layout`, `language`). Whether an entry whose values name no contract of the table is refused by the reader (recommended: refused, so a typo cannot make an entry silently inapplicable) is the ADR's choice; state it. One entry applies to one contract; an entry for several contracts is out of scope.
   3. **The predicate**: ADR-0190 decision 2's rule is unchanged in meaning: an entry applies when its four values equal the run's op_signature `kind`, `dtype`, `layout` and the covering contract's `language`. The comparison stays in one place in `hilclaw.catalog` and is now made against each entry's own values; `spec.write`'s second guard and its message form (`<directory>/<id>.md: applies to the <name> <value>, not the spec's <stated>; nothing was written`) and kind `technique_not_applicable` stay.
   4. **Ids**: ADR-0150 decision 3's rules hold across the whole directory (one id space per accelerator; never reused). Whether ids of bf16 entries carry a kind or dtype part is the ADR's choice (ids are `[a-z][a-z0-9_]{0,31}`).
   5. **Text rules for entries of a bf16 contract**, adapting ADR-0150 decision 5 (must / must not, `## When` in terms of the op_signature's shape and of what an earlier attempt shows): the guidance keeps the contract — the prototype and symbol of the kind's ADR, the `uint16_t` bf16 bit-pattern boundary with conversions done by the kernel, the intermediate precision and the fp32 → bf16 conversion the contract fixes or leaves to the kernel, every valid shape (ADR-0190 decision 4's table), outputs written before read, no alignment beyond the element type; it claims no measured speed-up, ranking or tuned value (a block size may be named only as a starting value, so marked); asks for no flag, define, library or `task.build` member; names no external code or material (OD-12). Whether an entry may suggest OpenMP is decided against ADR-0188 (which put OpenMP into the `cpu_standin` build set) and ADR-0150's single-thread choice for the first set; state it.
   6. **A-13 reading**: no file, member, value or version of the data plane changes; a spec still gets `{id, text}` (ADR-0150 decision 4); `catalog/` is code mode.
   7. **Consequences** (the slices: this task's and T-0566's other five kinds; P3-15 is checked when every one of the six bf16 contracts has at least one entry; runtime acceptance items, if any, handed through `## Result`; "Less exact, not edited") and **Boundaries** (OD-22's cold-start methods and UC-5's curator flow, OD-7 statistics and ranking, the Skill form of the criteria, other accelerators, fp16, multi-contract entries).
2. **Registers**, by their own recording rules — follow these rules, do not copy earlier task files' wording:
   - `ARCHITECTURE/Requirements.md` OD-22 row: one `**확정분**` link to ADR-0203 with a few-word topic, and `**잔여**` rewritten in place (the bf16 `cpu_standin` part of "첫 사례 밖 … `Applies to`의 형태" is answered; what stays open stays). Follow "행 형식": one link per new ADR, open parts rewritten in place, no restatement of the record, no dated paragraphs.
   - `ARCHITECTURE/OpenDecisionProposals.md` § OD-22: one `**채택분**` line for ADR-0203; any sub-question it answers gets its state rewritten in place (bullet-head state word and the `→ …` ending, question text kept). Follow "기록 규칙".
   - `ARCHITECTURE/StandardScenarios.md`: re-check coverage by its rules (CLAUDE.md "문서 커버리지 재검사"; S1 step 4 and S0 are the likely ones) and update §검사 결과 by its first paragraph.
3. **Code** (Python; record the language choice in the commit body):
   - `hilclaw/catalog.py`: each entry's four `Applies to` values are parsed and checked as ADR-0203 decides; `applies` and `mismatch` compare against an entry's values (their parameters change as ADR-0190 decision 2 foresaw); the module gives `catalog_tool` and `spec_tool` what they need (for example `criteria` returning, or a new function returning, each entry's values beside its `when`). `APPLIES_TO` is removed or kept only if ADR-0203 gives it a meaning. Docstrings say what the module now does.
   - `hilclaw/catalog_tool.py`: `catalog.read` returns exactly the entries whose values apply to the run (ADR-0190 decision 3's table holds with "the entries that apply" in place of "the same four entries"); a run with no op_signature or an uncovered one still gets `{"entries": []}`; the mock and a damaged catalog still give `catalog_unusable` before any filtering. Its description and docstring follow.
   - `hilclaw/spec_tool.py`: the lookup asks the new comparison with the same result kinds and message form; its docstring (lines ~55–70, "every entry applies to the fp32 `gemm` contract") follows.
4. **Entries**: at least one, at most three, new files in `catalog/cpu_standin/` for the `gemm` bf16 contract (ADR-0156), following ADR-0203's text rules. Candidate gists, to be checked against ADR-0156 by the executor and the reviewer (not prescribed): the fp32 `gemm` loop order i, p, j with a row of fp32 accumulators widened once per row and converted to bf16 once at the end; converting a block of `b` from bf16 to fp32 once into the kernel's own scratch memory before the products (if ADR-0156 decision 7/8 allows scratch memory). The four fp32 entries are not changed.
5. **Tests** (D12): cover happy, error, branch and **negative** cases of the touched public functions:
   - `tests/test_catalog.py`: an entry for each of the seven table contracts is accepted; refused: a line missing, lines out of order, a value not of the *name* form, a fifth line, and (if ADR-0203 so decides) values that name no table contract; the committed `catalog/cpu_standin/` passes the check; `applies`/`mismatch` for equal values, for each differing member, and for a non-`str` argument.
   - `tests/test_catalog_tool.py`: a `gemm` bf16 run gets exactly the committed `gemm` bf16 entries; an fp32 `gemm` run gets exactly the four fp32 entries; each of the other five bf16 runs still gets `{"entries": []}` (T-0566 changes that); every id returned for each contract passes `spec.write`.
   - `tests/test_spec_tool.py`: a later round of the `gemm` bf16 contract takes a committed `gemm` bf16 entry; it refuses an fp32 entry, and a `gemm` bf16 entry is refused for an fp32 run, with the message form above.
   - `hilclaw/` line and function coverage stay ≥ 80%.
   - Existing tests stay unchanged except: (a) list assertions under D21 — foreseen: tests that pin or monkeypatch `catalog.APPLIES_TO` (`tests/test_catalog_tool.py` `CHANGED_TO_BF16` and its two users, the entry helper in `tests/test_spec_tool.py` near line 804, any in `tests/test_catalog.py`) and any public-name set of `hilclaw.catalog`; (b) the assertions this task's behaviour change makes false, rewritten to the new rule: `test_a_bf16_run_gets_no_entry_of_the_committed_catalog` (now true for five kinds, not `gemm`), `test_every_id_returned_for_a_contract_passes_spec_write` (`bool(ids) == (key == FP32_GEMM)`), and `test_spec_write_still_refuses_a_catalog_id_for_a_bf16_run` only if its message changes. List every such edit in the PR body.
6. **Unchanged behaviour**: the fp32 `gemm` path, `spec.write` for fp32 runs, the nightly configuration and every other tool behave exactly as before; the full test suite passes. No `orchestration/` text changes unless ADR-0203 shows that a sentence there became false (then the smallest edit, listed in the PR body).
7. **Process**: dev-item-address steps, Draft PR, context-isolated review to Approve (≤ 14 rounds, D28), CI green, self squash-merge with the PR body's last line `Task: T-0565`; §9 notice of ADR-0203 on issue #5 (English, no bare `@` mentions).

## Out of Scope

- Entries for `rmsnorm`, `elementwise_add`, `swiglu`, `rope`, `sdpa_kv_cache` (T-0566); checking PLAN P3-15 (after T-0566).
- OD-22's cold-start methods, UC-5's curator flow, OD-7 statistics and ranking, the Skill form of the criteria (FR-8), catalogs for `virtual_npu` or vendor targets, fp16.
- Any change to the selector or Round-Manager definitions beyond criterion 6, to `spec.json` or any data-plane file, to the nightly routine.
- Starting `claude` in any form (D16); no test run (D25) is needed.

## Follow-ups

## Result

- **DONE.** PR #379, squash-merged as `4dd59de3`; branch deleted. Review: 1 round, Approve (dev-reviewer, fresh context; two Nits fixed after Approve — the owner-sentence citation now `#5 A-7 ②`, and one test edit added to the PR body's D21 list). CI green on the PR head (`80586de6`); local full suite 39825 passed, 2217 skipped; `hilclaw/` coverage 99% (catalog.py 99%, catalog_tool.py 100%, spec_tool.py 100%).
- **Order check** (Why): unchanged at the start — no open PR, #373 the only open `nightly-failure` issue (T-0559, BLOCKED on HQ-0100), unresolved HQs only HQ-0096 and HQ-0100.
- **ADR-0203** (`ARCHITECTURE/decisions/ADR-0203-od22-catalog-entries-for-the-bf16-contracts.md`): `Applies to` holds the key of one table contract; values naming no contract are refused by the reader; comparison against each entry's own values in `hilclaw.catalog` (`AppliesTo`, `Entry`, `entries`, `applies(applies_to, …)`, `mismatch(applies_to, …)`; `APPLIES_TO` removed); ids carry no required kind/dtype part; bf16 text rules; entries of a bf16 contract may suggest OpenMP under conditions (the two new entries do not). §9 notice posted on #5: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6818127866 (7-day objection window).
- **Entries**: `catalog/cpu_standin/gemm_bf16_row_accumulators.md`, `catalog/cpu_standin/gemm_bf16_widened_b_panel.md`. Supporting check (not committed): C kernels written from both guidances, built with gcc `-std=gnu11 -O2 -ffp-contract=off`, agree with each other and with the malloc-failure path and stay within half a bf16 ulp of a float64 reference on five shapes (1x1x1 and non-multiples of the block sizes included).
- **Readings for the owner** (in the ADR Status and the #5 notice, not HQs): PLAN P3-15's "틀을 바꾸지 않는다" read as the four lines, their order and the judgement (the values were left to OD-22 by ADR-0150/ADR-0190); "기법의 근거는 문서에 출처로 적고" read as the entry stating its reason in its own text, naming no external material (OD-12).
- **Runtime acceptance items** for `PROCESS/RuntimeAcceptance.md` (D22):
  1. A real technique-selector of a `gemm` bf16 run on `cpu_standin` receives the two `gemm` bf16 entries from `catalog.read`, may choose one, and `spec.write` writes a spec that carries it.
  2. A real coder given one of the two entries writes a kernel that passes the bf16 `gemm` check.
- **Follow-up**: T-0566 (the other five bf16 kinds) on the form of ADR-0203 decisions 2 and 5; P3-15 is checked when all six bf16 contracts have an entry.
- No install, no work image, no test run, no `claude` started. Task directory `${TMPDIR:-/tmp}/hilclaw-driver/T-0565/` removed.
