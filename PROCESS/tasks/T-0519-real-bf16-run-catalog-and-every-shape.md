---
id: T-0519
title: Keep real bf16 runs from stopping on inapplicable techniques and tell the coder its every-shape duty (ADR-0190)
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [OD-22, OD-23, OD-31, C-6, FR-5, "PLAN P2-15", D26]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0190-od22-catalog-read-by-contract-and-coder-every-shape.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
  - hilclaw/catalog.py
  - hilclaw/catalog_tool.py
  - hilclaw/spec_tool.py
  - hilclaw/coder_runtime.py
  - tests/test_catalog.py
  - tests/test_catalog_tool.py
  - tests/test_coder_runtime.py
  - tests/test_bf16_end_to_end.py
estimatedSize: {loc: 220, files: 8}   # test code is outside the cap
hq: []
---
## Why

**Why now (D26).** DRIVER §6 D26 asks what the owner needs to run P2-15. That run needs real instance runs of the bf16 kinds, whose kernels it then binds (ADR-0189). Reading the code shows two gaps that the stub end-to-end test does not reach. Neither has been observed in a real run; both are derived from the code below. If the reading is wrong for either gap, say so in the Result and do only the other.

**Gap 1: a bf16 run can stop at round 1.**
- `catalog.read` returns every entry of the accelerator's catalog, unfiltered (ADR-0171 decision 3, `hilclaw/catalog_tool.py`). All four entries apply only to fp32 `gemm` (`hilclaw.catalog.APPLIES_TO`).
- For a bf16 run, `spec.write` refuses every id with `technique_not_applicable` (ADR-0177 decision 4, `hilclaw/spec_tool.py` check 7).
- The `## When` text does not name the dtype. A real selector on a bf16 `gemm` run can reasonably choose `loop_order_ikj`.
- The coder-driver then reports the failure kind, and `orchestration/round-manager.md` step 8 sends any `spec.write` failure to the stop, so the round is not ended.
- The next turn finds `hypotheses_exist` and can choose the same id again.
- ADR-0171 decision 3 foresaw this: "A later record that widens `Applies to` revisits this tool, so that an id it returns is not refused with `technique_not_applicable`". ADR-0177 widened the contracts without revisiting the tool.
- T-0516's stub always chooses an empty list, which hides the path. Its Result says: "The empty `techniques` choice is why no bf16 catalog entry was needed."
- The selector already has the right rule: "Choose an empty list ... when its result holds no entry". So the fix belongs in the tool.

**Gap 2: the coder is not told its every-shape duty.**
- ADR-0189 decision 5 binds each kernel with `"every"` because each contract obliges correctness at every shape (for example ADR-0156 decision 7).
- The obligation lives only in the ADRs. The coder sees `spec.json`, whose operands give one fixed shape, and `hilclaw.coder_runtime.PROMPT`, which does not mention other shapes.
- A real coder asked for speed at one shape may specialise for it. Verification passes, because whether it draws other shapes is OD-16 sub-question 1. The owner's generation then fails or mismatches at the other call shapes, for a reason that is hard to trace.
- Telling the coder is one sentence in the prompt, with no data-plane change.

**Not waiting on an HQ.** HQ-0084 (real weights, tokenizer, entry point) is unanswered, and nothing here depends on it. This task reads none of its answers. HQ-0081, HQ-0082 and HQ-0083 do not touch this either.

**RuntimeAcceptance.** No item has the status `실패` as of `main` `204c0d9b`.

**D16.** Verification uses stubs and test-written files. No real `claude`, Docker daemon, weights or tokenizer is used, and this task needs no D25 test run.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5 (branch `claude/T-0519-<slug>`, the `Task: T-0519` trailer in commits and as the last line of the PR body, the size cap, D12, D21), §3 "BLOCKED 사유", §6 D26, §8 (D22) and §9.
- `CLAUDE.md`: A-13 code mode, the BLOCKED reasons, the test rules, comment minimisation, the language policy and the coverage recheck for `ARCHITECTURE/` edits.
- `ARCHITECTURE/decisions/ADR-0171-od23-first-case-round-techniques-and-coder-delegation.md`: decisions 2, 3 and 6, and its table of cases.
- `ARCHITECTURE/decisions/ADR-0150-od22-first-case-technique-catalog.md`: decisions 2 and 4.
- `ARCHITECTURE/decisions/ADR-0177-*.md`: decision 4's catalog paragraph and Boundaries.
- `ARCHITECTURE/decisions/ADR-0151-od6-first-case-later-round-spec.md`: decision 2 (b).
- `ARCHITECTURE/decisions/ADR-0189-od31-binding-from-run-incumbents.md`: decision 5.
- `ARCHITECTURE/decisions/ADR-0184-od20-first-case-incumbent-base.md`: decision 4 (the sentences it added to the prompt).
- `ARCHITECTURE/decisions/ADR-0137-*.md`: decision 6 (the coder's command and prompt).
- The "every set of dimensions" paragraph of each contract: ADR-0008 decision 6, ADR-0156 decision 7, ADR-0158 decision 7, ADR-0159 decision 8, ADR-0160 decision 8, ADR-0161 decision 11, ADR-0162 decision 11.
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph and the OD-22, OD-23 and OD-31 rows.
- `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" paragraph in the header, and sections OD-22, OD-23 and OD-31.
- `ARCHITECTURE/StandardScenarios.md`: the first paragraph of §검사 결과.
- Code: `hilclaw/catalog.py`, `hilclaw/catalog_tool.py`, `hilclaw/spec_tool.py` (the function holding check 7), `hilclaw/contract_table.py` (`covers`, `task_contract`), `hilclaw/coder_runtime.py` (`PROMPT` and the module docstring), `orchestration/round-manager.md` steps 6 to 8, `orchestration/agents/technique-selector.md` "The choice of techniques".
- Tests: `tests/test_catalog_tool.py`, `tests/test_coder_runtime.py` (the `PROMPT` assertions near lines 597 to 608 and 641), `tests/test_bf16_end_to_end.py`, `tests/first_run_stubs.py` (`technique_selector`).

## Acceptance Criteria

1. **ADR-0190**, in the "Record format" of ADR-0001, decides:
   - **`catalog.read` by contract.** It returns only the entries that apply to the run. An entry applies when its `Applies to` values equal the `kind`, `dtype` and `layout` of the run's stated op_signature record and the `language` of that record's contract. So an id it returns is not refused with `technique_not_applicable`, which is the property ADR-0171 decision 3 asks for.
   - **The cases.** State what the tool answers in each of these, with no new failure kind unless the ADR shows one is needed:
     - a bf16 run (no entry, so the selector's existing rule gives `techniques: none`);
     - an fp32 `gemm` run (the same four entries as today);
     - a mock run (`catalog_unusable`, as today; the existing check order stays);
     - an instance with no op_signature, or with one no contract covers.
   - **Unchanged.** Say that `spec.write`'s check stays as a second guard, and that the selector and Round-Manager definitions are unchanged. If the executor finds a definition must change, it records why.
   - **The every-shape sentence.** Add to `PROMPT` the duty the contracts state: the kernel is called with other values of the prototype's size parameters as well as the spec's, must be correct at all of them, and may specialise for the spec's shape only while staying correct elsewhere. Tie it to the contract paragraphs in Required Reading. Check that the duty holds for all seven contracts. If one does not, word the sentence so it stays true and say so. The sentence is about correctness only and must not change what the prompt says about baseline or base.
   - **A-13 reading.** No file, member, value or version of the data plane changes. The spec's bytes do not change. A design that needs any of that is a BLOCKED reason, not a choice for this ADR.
   - **Boundaries** names what stays open: catalog entries for the bf16 contracts and the form of `Applies to` that admits them (OD-22), whether verification draws other shapes (OD-16 sub-question 1), and the entry and real weights (HQ-0084). It lists any runtime acceptance item for `PROCESS/RuntimeAcceptance.md`. The expected ones are that a real selector given no entry reports `techniques: none`, and that a real coder keeps its kernel general after this sentence.
2. **Code.**
   - One public predicate in `hilclaw/catalog.py` (or a better place the ADR names) says whether an entry's `Applies to` matches given kind, dtype, layout and language values. `catalog_tool` and `spec_tool` both use it rather than holding copies. `spec.write`'s behaviour and messages do not change.
   - `catalog_tool` filters as the ADR says. Update its module docstring, its `_DESCRIPTION` and any docstring sentence this makes false, including "Every entry is returned".
   - `coder_runtime.PROMPT` gains the sentence, and the module docstring points to ADR-0190.
3. **Tests.**
   - **Happy:** an fp32 `gemm` run gets the committed catalog as today (`test_the_committed_catalog_of_cpu_standin` keeps passing unchanged); a test catalog entry returns with its `when` in id order.
   - **Branch:** a run of each of the six bf16 contracts gets `{"entries": []}` from the committed catalog; an fp32 run of a covered contract whose values differ from an entry, if the table has one; the case of an instance with no op_signature or an uncovered one, as the ADR rules.
   - **Negative and error:** the existing failure kinds and their order are unchanged, including a mock run answering `catalog_unusable` and a damaged catalog; `spec.write` still refuses a non-applicable id with the same kind and message; the predicate is tested on each mismatching member and on malformed values.
   - **Property:** for the committed catalog and each contract of `hilclaw.contract_table.TABLE`, every id `catalog.read` returns passes `spec.write`'s applicability check.
   - **One joined path:** in `tests/test_bf16_end_to_end.py`, a bf16 run whose stub selector would choose a real catalog id but sees no entry reaches a spec with empty `guidance.techniques`, and the run goes on. Existing assertions in that file stay. The stub's filter (`first_run_stubs.py`, `[t for t in chosen["techniques"] if t in entries]`) may be used as it stands; change the stub only if the test needs it, and say so in the Result.
   - **Prompt:** an assertion pins that `PROMPT` states the every-shape duty, without pinning the whole sentence. The existing `PROMPT` assertions keep passing.
   - **List assertions (D21).** Existing tests keep passing, and their assertions do not change except the list assertions D21 allows. The foreseen ones are `test_public_names_and_documentation` in `tests/test_catalog_tool.py` and a public-names assertion in `tests/test_catalog.py`, if one exists, and any import pin that names `catalog_tool`'s imports (for example the one `tests/test_standin_profile.py` holds on who may name a module). List each edited assertion in the PR body.
4. **Records.**
   - `Requirements.md` follows its "행 형식": one link per new ADR in the rows ADR-0190 answers, with the open parts rewritten in place.
   - `OpenDecisionProposals.md` follows its header's "기록 규칙": one `채택분` line in each OD it answers, with open parts rewritten in place.
   - `StandardScenarios.md` §검사 결과 follows the rule in its first paragraph: record only if a verdict changes. Recheck coverage either way, as CLAUDE.md requires.
   - Restate no content of the ADR in any of them, and add no dated paragraph.
5. **Result** records: the language and the reason for it (no new language is expected); whether each gap held on reading; the ADR's rule for the uncovered instance; any edited assertion (D21); runtime acceptance items, for the driver to add; that the §9 notice on #5 is due with its 7-day window; and what the owner's P2-15 run still lacks after this task.

## Out of Scope

- Writing catalog entries for the bf16 contracts, or widening `Applies to` (OD-22).
- Making verification draw other shapes (OD-16 sub-question 1).
- The user-facing entry, real weights, the tokenizer and the `transformers` comparison (HQ-0084, OD-31 ⑤·⑦·⑩). Do not guess its answers.
- A real `claude` run, a D25 test run, a Docker daemon or real weights (D16; RA-0056).
- Changing the Round-Manager's stop on a `spec.write` failure.
- Other lines of the PLAN hold section, P2-8, P2-4 and fp16 (HQ-0083).

## Follow-ups

## Result
