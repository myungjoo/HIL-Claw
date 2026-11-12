---
id: T-0566
title: PLAN P3-15 (2/2) — add the first technique entries of `catalog/cpu_standin/` for the bf16 `rmsnorm`, `elementwise_add`, `swiglu`, `rope` and `sdpa_kv_cache` contracts under ADR-0203, so that every one of the six bf16 kinds has at least one entry
phase: P3
status: DONE
commitMode: code
coversReq: [D31, "PLAN P3-15", FR-7, FR-8, OD-22, C-6]
dependsOn: [T-0565]
touchesFiles:
  - catalog/cpu_standin/
  - tests/test_catalog.py
  - tests/test_catalog_tool.py
  - tests/test_spec_tool.py
estimatedSize: {loc: 330, files: 8}
hq: []
---
## Why

**PLAN P3-15** asks for technique documents for each of the six bf16 kinds of ADR-0152 decision 2 in `catalog/cpu_standin/`, so that a bf16 run's selector no longer reports `techniques: none` for want of entries (ADR-0190). T-0565 wrote ADR-0203 (the `## Applies to` values of any contract of the contract table, each entry compared against its own values, and the text rules for bf16 entries), changed the reader, and added the `gemm` bf16 entries. This task adds the entries for the other five bf16 contracts. It changes no code of `hilclaw/` and no frame: entries are code-mode content of the source repository (ADR-0150 decision 2), and a spec still gets `{id, text}`.

The entry form this task relies on is fixed by T-0565's acceptance criterion 1.2 (four lines `kind`, `dtype`, `layout`, `language` with the values of one contract-table key). If ADR-0203 as landed differs from that, or T-0565 closed `DONE` without landing (DRIVER §6 D20 ④), say so in `## Result` and stop before writing entries.

**Brake (D31 ②).** A PLAN item serving the optimization capability; not a refinement of the data plane.

**Open HQs (D27 ⑦).** Do not ask again or anticipate HQ-0096 or HQ-0100. If an owner-only part appears, write it in `## Result` in the DRIVER §8 structure (Korean), land the rest and return `DONE` (D27 ⑥).

## Required Reading

- `PROCESS/DRIVER.md`: **§3-5 and §5** (branch `claude/T-0566-<slug>`, the `Task: T-0566` trailer and the PR body's last line, size D30, tests D12, list assertions D21, storage D29: temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0566/`, removed at the end); §6 D27 ⑥·⑦, D31 ②.
- `PROCESS/PLAN.md` P3-15 (line ~79).
- `PROCESS/tasks/T-0565-bf16-catalog-applies-to-and-gemm-entries.md` (criteria and `## Result`).
- ADRs: **ADR-0203** as landed by T-0565 (`ARCHITECTURE/decisions/ADR-0203-*.md`; the form, ids and the text rules for bf16 entries, its OpenMP choice); `ADR-0150-od22-first-case-technique-catalog.md` decisions 2–5; `ADR-0190-od22-catalog-read-by-contract-and-coder-every-shape.md` decision 4 (the every-shape table of valid values); the five contracts: `ADR-0158-od31-bf16-rmsnorm-contract.md`, `ADR-0159-od31-bf16-elementwise-add-contract.md`, `ADR-0160-od31-bf16-swiglu-contract.md`, `ADR-0161-od31-bf16-rope-contract.md`, `ADR-0162-od31-bf16-sdpa-kv-cache-contract.md` (each: the operation and its precision, the fp32 → bf16 conversion, prototype, guarantees and obligations, what the source provides); `ADR-0116-od18-cpu-standin-build-settings.md` and `ADR-0188-od18-standin-openmp-in-the-build-set.md`.
- Code: `hilclaw/catalog.py` (as T-0565 left it), `hilclaw/contract_table.py`, the five `hilclaw/*_bf16_contract.py` modules (`KIND`, `DTYPE`, `LAYOUT`, `LANGUAGE`, `PROTOTYPE`), `catalog/cpu_standin/*.md` (the `gemm` bf16 entries of T-0565 as the model).
- Tests: `tests/test_catalog.py`, `tests/test_catalog_tool.py` (the section "Which entries apply to the run"), `tests/test_spec_tool.py` (the bf16 later-round tests near lines 1200–1290).

## Acceptance Criteria

1. **Entries**: for each of `rmsnorm`, `elementwise_add`, `swiglu`, `rope` and `sdpa_kv_cache` (bf16, `row_major`, `c`), one entry — two where a second technique is clearly distinct and the file cap allows (≤ 10 non-test files in total) — in `catalog/cpu_standin/`, each in ADR-0203's form and keeping its text rules: the kind's prototype and symbol, the `uint16_t` bf16 boundary with conversions done by the kernel, the intermediate precision and output conversion its contract fixes, every valid shape of ADR-0190 decision 4's table (for `rope`, `d` even ≥ 2; for `sdpa_kv_cache`, `l ≥ m` and `h` a multiple of `h_kv`), outputs written before read, no alignment beyond the element type; no measured claim, ranking or tuned value (a block size only as a marked starting value); no flag, define, library or `task.build` member; no external code or material. Each `## When` speaks in terms of the op_signature's shape and of what an earlier attempt shows. Each entry is checked against its contract ADR by the executor and by the reviewer (the review prompt names that check). Candidate gists, not prescribed: for `rmsnorm`, one pass of fp32 sum of squares per row with the bf16 inputs widened once and the scale applied in a second pass; for `elementwise_add` and `swiglu`, a single contiguous pass over `m * n` elements with the widening, the operation and the conversion in one loop body that the compiler can vectorise; for `rope`, pairing the two halves the contract defines with the `freqs_cis` row loaded once per position; for `sdpa_kv_cache`, a numerically stable softmax in fp32 per query row (running maximum), with each `h_kv` head's cache rows read once for the `h / h_kv` query heads that share them.
2. **No code or ADR change**: `hilclaw/`, `ARCHITECTURE/`, `orchestration/` and the existing entries are not edited. If an entry cannot be written within ADR-0203 (for example its text rules forbid what a kind needs), stop that entry, write it in `## Result`, and land the rest.
3. **Tests** (D12; the entries are not modules, so ① to ④ apply only to the test that the committed directory passes):
   - `tests/test_catalog.py`: the committed `catalog/cpu_standin/` passes the check, and every one of the six bf16 contracts and the fp32 `gemm` contract is named by at least one committed entry.
   - `tests/test_catalog_tool.py`: each bf16 run gets exactly the committed entries of its contract and none of another; every id returned for each contract passes `spec.write`.
   - `tests/test_spec_tool.py`: a later round of each of the five contracts takes one of its committed entries and refuses an entry of another contract, with the message form of `technique_not_applicable`.
   - Existing tests stay unchanged except: (a) list assertions under D21 — foreseen: the expected id lists of committed entries in `tests/test_catalog.py` and `tests/test_catalog_tool.py`; (b) assertions T-0565 left true only for the five kinds without entries (for example a test that a bf16 run other than `gemm` gets `{"entries": []}` from the committed catalog), rewritten to the new rule. List every such edit in the PR body.
   - The full test suite passes; `hilclaw/` coverage stays ≥ 80%.
4. **P3-15's completion**: `## Result` states, for each of the six bf16 contracts, the ids of its committed entries, so the driver can check PLAN P3-15 in its §3-6 state commit. Runtime acceptance items, if any (for example a real selector choosing a bf16 entry and a real coder following it), are listed in `## Result` for `PROCESS/RuntimeAcceptance.md` (DRIVER §8, D22), not as HQs.
5. **Process**: dev-item-address steps, Draft PR, context-isolated review to Approve (≤ 14 rounds, D28), CI green, self squash-merge with the PR body's last line `Task: T-0566`.

## Out of Scope

- Any change to the catalog reader, `catalog.read`, `spec.write`, ADR-0203 or the registers (T-0565's).
- Changing the fp32 `gemm` or `gemm` bf16 entries; catalogs for `virtual_npu` or vendor targets; fp16; OD-22's cold-start methods; OD-7 statistics.
- Starting `claude` in any form (D16); no test run (D25) is needed.

## Follow-ups

## Result

- **DONE.** PR #380, squash-merged as `47b26b8d`; branch deleted. Review: 1 round, Approve (dev-reviewer, fresh context, opus; the review prompt named the check of each entry against its contract ADR and ADR-0203 decision 5). Three wording Nits fixed after Approve (D20 exception: rmsnorm entry's `static inline` widening helper and its `## When` in terms of the lane count; both sdpa entries now state the error bound over ADR-0162's input domain); two test Nits left as they are. CI green on head `62fd0aa5`; local full suite 39847 passed, 2217 skipped; `hilclaw/` coverage 99% (no `hilclaw/` change).
- **Precondition** (Why): ADR-0203 landed by T-0565 (`4dd59de3`) with the four-line form of criterion 1.2; T-0565 closed `DONE` with landing. No open PR at start.
- **P3-15 completion — committed entries per bf16 contract** (all in `catalog/cpu_standin/`):
  - `gemm` bf16: `gemm_bf16_row_accumulators`, `gemm_bf16_widened_b_panel` (T-0565)
  - `rmsnorm` bf16: `rmsnorm_bf16_lane_sums`
  - `elementwise_add` bf16: `elementwise_add_bf16_flat_loop`
  - `swiglu` bf16: `swiglu_bf16_flat_loop`, `swiglu_bf16_poly_exp`
  - `rope` bf16: `rope_bf16_table_row_per_token`
  - `sdpa_kv_cache` bf16: `sdpa_kv_cache_bf16_gqa_groups`, `sdpa_kv_cache_bf16_two_pass`
  Every one of the six bf16 contracts has at least one entry, so PLAN P3-15 can be checked.
- **No code or ADR change**: `hilclaw/`, `ARCHITECTURE/`, `orchestration/` and the existing entries untouched; no entry needed anything ADR-0203 forbids. No new entry uses OpenMP.
- **Reading of the task's gist**: for `rope` the gist's "the two halves the contract defines" does not match ADR-0161 decision 5 (adjacent pairs `2p`, `2p + 1`); the entry follows the contract and says the pairs are not the halves of a head. For `sdpa_kv_cache` the entries use the maximum subtracted before every `expf` with scores kept in kernel-owned scratch and no rescaling (the straightforward evaluation of ADR-0162 decision 7's argument) instead of a running-maximum online softmax, whose error ADR-0162 leaves for the kernel to show.
- **Supporting check (not committed)**: C kernels written from every guidance, built with MinGW gcc 16.2 `-std=gnu11 -O2 -ffp-contract=off -fopenmp ... -lm`, matched a float64 reference after bf16 rounding (0 ulp) on several shapes each, including 1 x 1, odd sizes, `rope` d = 2 and 6, `sdpa_kv_cache` with l = m, m = 1, h = h_kv and h / h_kv = 2, 3, 4; both sdpa entries and the malloc-failure path gave identical bits and exact cache copies; the inline exponential of `swiglu_bf16_poly_exp` had a worst relative error of 2^-17.75 over |g| <= 87.34 (contract needs 2^-12).
- **D21 / criterion 3 (b) edits of existing tests** (listed in the PR body): `tests/test_catalog.py` `ALL_COMMITTED` and the id-to-contract map of `test_committed_entries_state_their_contracts`; `tests/test_catalog_tool.py` `test_a_bf16_run_gets_no_entry_of_the_committed_catalog` rewritten as `test_a_bf16_run_gets_the_committed_entries_of_its_contract_only`, and the expected ids of `test_every_id_returned_for_a_contract_passes_spec_write` read from a per-contract `COMMITTED` map.
- **Runtime acceptance items** for `PROCESS/RuntimeAcceptance.md` (D22):
  1. A real technique-selector of a `rmsnorm`, `elementwise_add`, `swiglu`, `rope` or `sdpa_kv_cache` bf16 run on `cpu_standin` receives that contract's committed entries from `catalog.read`, may choose one, and `spec.write` writes a spec that carries it.
  2. A real coder given one of these entries writes a kernel that passes the bf16 check of its contract.
- No install, no work image, no test run, no `claude` started. Task directory `${TMPDIR:-/tmp}/hilclaw-driver/T-0566/` removed.
