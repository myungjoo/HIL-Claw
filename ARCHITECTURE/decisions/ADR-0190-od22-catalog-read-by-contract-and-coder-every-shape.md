# ADR-0190: `catalog.read` returns only the entries that apply to the run, so that a bf16 run gets none and goes on with `techniques: none`, and the coder's prompt states the every-shape duty of the contracts (part of OD-22, part of OD-23, part of OD-31 sub-question 4, for first-case runs)

## Status

- **Accepted on 2026-10-31** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it.** The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **Two kinds of content.** What an owner decision, an accepted record or a code docstring says is **cited**, with its source named. **Everything else is this record's own**: the filter, the rule for an instance with nothing to compare, the predicate's place and the wording of the prompt's sentence.
- **The owner-sentence search.** Searched on 2026-10-31: the 68 of the 310 comments of #4, #5, #7 and #8 that hold no "posted by driver" marker, for every shape, other shape, specialise, `catalog.read`, `Applies to`, `technique_not_applicable`, and bf16 beside technique or catalog (기법, 카탈로그). **No sentence matched.**
- **Open HQs checked and not crossed** (`PROCESS/STATE.json` on `main` `34a242c7`). **HQ-0084** (weights, tokenizer, packages, the entry point): none of its answers is used. **HQ-0081**, **HQ-0082** and **HQ-0083**: not touched.
- **No file, member, value or version of the data plane changes** (decision 6). **It is a record with its code slice**; no `claude` process, Docker daemon or real weights were used for it (D16).
- **The status of every OD is unchanged.** Boundaries lists what stays open.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **Why now** (cited: DRIVER §6 D26): the work is what the owner needs to run PLAN P2-15, which needs real instance runs of the bf16 kinds whose kernels it binds ([ADR-0189](ADR-0189-od31-binding-from-run-incumbents.md)).
- **Gap 1, found on reading the code; not observed in a real run.** [ADR-0171](ADR-0171-od23-first-case-round-techniques-and-coder-delegation.md) decision 3 returns every entry, because every entry then applied to every spec, and says: "A later record that widens `Applies to` revisits this tool, so that an id it returns is not refused with `technique_not_applicable`" (cited). [ADR-0177](ADR-0177-od18-od6-contract-table.md) widened the contracts and not the tool, and for a run of a bf16 contract `spec.write` refuses every id (cited: its Boundaries). `orchestration/round-manager.md` step 8 sends a failure of `spec.write` to the stop (observation). So a selector that chooses a returned id on a bf16 run stops the round, and the next turn can choose the same id. T-0516's stub always chose an empty list, which hid the path.
- **Gap 2, found on reading the code; not observed in a real run.** ADR-0189 decision 5 binds each kernel for `"every"` shape because each contract obliges correctness there, and says that a kernel holding only at its instance's shape passes its run and fails at a generation's other shapes (cited). The obligation is in the records. The coder sees `spec.json`, whose operands give one shape, and a prompt that does not mention others (observation: `hilclaw.coder_runtime.PROMPT`).

## Decision

A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope

The result of `catalog.read` (ADR-0171 decision 3) and the prompt of the coder's call (ADR-0137 decision 6). Its request, its other checks and its kinds stay. The runs are those `catalog.read` serves today.

### 2. `catalog.read` by contract

- **It returns only the entries that apply to the run.** An entry applies when its `Applies to` values equal the `kind`, `dtype` and `layout` of the run's stated op_signature record and the `language` of the contract that covers that record. These are the four values of the rule of [ADR-0150](ADR-0150-od22-first-case-technique-catalog.md) decision 4 (cited), and the record states no language, so the contract gives it (cited: `hilclaw.contract_table`, ADR-0177 decision 1).
- **The property ADR-0171 decision 3 asks for holds**: an id `catalog.read` returns is not refused with `technique_not_applicable`.
- **The order and the checks stay.** The catalog directory is read and checked first, so check ④ of ADR-0171 decision 3 answers as before, and the filter is applied to what it found. It is no check and has no kind.
- **The predicate is one place.** `hilclaw.catalog.applies` says whether the values match. `hilclaw.catalog.mismatch` finds the first value that differs, which `spec.write` needs for its message, and `applies` is built on it. Both tools use these and hold no copy of the comparison. They take no entry, because every entry the catalog's rules admit states the same four lines (cited: ADR-0150 decision 2); a record that changes that changes their parameters.

### 3. The cases

| Run | `catalog.read` answers | What follows |
|---|---|---|
| bf16, any of the six contracts, `cpu_standin` | `{"entries": []}` | The selector's existing rule gives `techniques: none` (cited: ADR-0171 decision 2); `spec.write` gets `[]`; the round goes on with empty `guidance.techniques` |
| fp32 `gemm` | The same four entries as today | As ADR-0171 |
| Mock, whatever it states | `catalog_unusable`, as today | As ADR-0171; the check comes before the filter |
| A damaged catalog, whatever the run states | `catalog_unusable`, as today | As ADR-0171 |
| No op_signature, or one no contract covers | `{"entries": []}`; no failure | The selector reports `techniques: none`, and `spec.write` answers `op_signature_not_stated` or `op_signature_not_covered` at its check 5, before any technique is looked at (cited: the `hilclaw/spec_tool.py` docstring); the stop |

- **Why no failure for the last row.** Nothing applies, because no language can be compared, so the empty result is simply true. The instance start refuses a run no contract covers (cited: ADR-0177 decision 2), so only a file written by hand reaches this row. A failure kind here would make the selector give no `techniques:` line (cited: ADR-0171 decision 4), and the Round-Manager would report that no choice was given, which hides the cause. The empty result lets `spec.write` name it, and **no new kind is needed**.
- **Coverage by a contract with other values.** The table holds one fp32 contract, and its values equal the entries', so no committed run reaches this path today. The test uses a test catalog whose `Applies to` differs.

### 4. The every-shape sentence

`hilclaw.coder_runtime.PROMPT` gains, directly after the sentences of [ADR-0184](ADR-0184-od20-first-case-incumbent-base.md) decision 4, one sentence with this content:

> The operand shapes in `spec.json` give one set of values of the size parameters of the prototype, and the kernel may also be called with other valid values of them; it must be correct at all of them, and may specialise for the shape of `spec.json` only while staying correct at the others.

The wording is the code's, as ADR-0137 decision 6 leaves it (cited). The prompt still holds no host path, run id, model or credential (cited: the same decision).

**The duty holds for all seven contracts**, each stating it in the paragraph named:

| Contract | Paragraph (cited) | Valid values |
|---|---|---|
| `gemm` fp32 | ADR-0008 decision 6 | m, k, n ≥ 1 |
| `gemm` bf16 | ADR-0156 decision 7 | m, k, n ≥ 1 |
| `rmsnorm` | ADR-0158 decision 7 | m, n ≥ 1 |
| `elementwise_add` | ADR-0159 decision 8 | m, n ≥ 1 |
| `swiglu` | ADR-0160 decision 8 | m, n ≥ 1 |
| `rope` | ADR-0161 decision 11 | m, h ≥ 1, d even ≥ 2 |
| `sdpa_kv_cache` | ADR-0162 decision 11 | m ≥ 1, l ≥ m, h_kv ≥ 1, h a multiple of h_kv, d ≥ 1 |

Three words keep the sentence true for all seven:

- **"valid"**: `rope` and `sdpa_kv_cache` do not admit every positive value.
- **"may also be called"**: ADR-0008 decision 6 says that whether a caller ever passes other values stays open (OD-16 sub-question 1, cited), and "is called" would claim more than it does. The duty does not depend on that.
- **"size parameters"**: `rmsnorm` also takes `eps`, a value of the same obligation (cited: ADR-0158 decision 7) which the sentence does not speak of.

**The sentence is about correctness only.** What the prompt says about `feedback.base` and the plain baseline stays word for word; a round-0 coder is still told to write a plain kernel, and the sentence gives it no reason to do otherwise.

### 5. Unchanged

- **`spec.write`'s check stays as a second guard**, with its kind, messages and order (cited: ADR-0150 decision 4; ADR-0151 decision 2 (b)). A selector or a Round-Manager that names an id the tool did not return is still refused. Its code now asks `hilclaw.catalog.mismatch`, with the same result.
- **The selector and Round-Manager definitions are unchanged.** The selector's rule on an empty result exists (cited: `orchestration/agents/technique-selector.md`), and the Round-Manager's step 8 passes "none" on (cited: ADR-0171 decision 6). No step is added and the stop on a failure of `spec.write` stays.

### 6. A-13 reading

No file, member, value or version of the data plane changes. The spec's bytes do not change for any given request: a bf16 run's spec holds an empty `guidance.techniques`, as it had to already (cited: ADR-0177 Boundaries). `catalog.read` writes nothing. The prompt is a text of the package and is in no run file.

## Alternatives considered

| Alternative | Why not |
|---|---|
| A clearer `## When` that names the dtype | It leaves a model to read it right and a round that stops when it does not; the tool can make the wrong answer impossible. |
| Let the Round-Manager end the round on `technique_not_applicable` | It changes a stop this task keeps, and the selector could repeat the choice. |
| Write bf16 catalog entries | The content and the form of `Applies to` are OD-22's. |
| Have `spec.write` drop an inapplicable id | The spec would differ from the request, and the selector's choice would be lost silently. |
| Answer `op_signature_not_stated` or `op_signature_not_covered` from `catalog.read` | Decision 3. |
| Return an entry with a flag that says it does not apply | A new member of a result, and a selector could still choose it. |
| Keep a copy of the comparison in `catalog_tool` | Two readings of one rule could drift. |
| Put the duty into `spec.json` | A data-plane change (A-13). |
| Make verification draw other shapes | OD-16 sub-question 1. |

## Consequences

- `hilclaw/catalog.py` gains `applies` and `mismatch`. `hilclaw/catalog_tool.py` filters, and its docstring and description say so. `hilclaw/spec_tool.py` asks `mismatch`. `hilclaw/coder_runtime.py` gains the sentence.
- **Less exact, not edited**: ADR-0171 decision 3 "Every entry is returned, unfiltered" and its Result row, now for the entries that apply; ADR-0137 decision 6's list of the prompt's contents, which gains this sentence as it gained ADR-0184's. `orchestration/agents/technique-selector.md` says the tool gives the criteria "of the entries of the run's catalog", which stays true of the ones it returns.
- **UsageCases and StandardScenarios** (S0 and S1 rechecked): no step changes, no verdict changes, no gap.
- **The cost, plainly.** A bf16 round's only guidance is its hypotheses and feedback until OD-22 gives it entries. The prompt tells the coder a duty and nothing enforces it: a coder that ignores it still passes its run (cited: ADR-0189 decision 5).
- **Runtime acceptance items** (D16; nothing was tried). They go to [PROCESS/RuntimeAcceptance.md](../../PROCESS/RuntimeAcceptance.md) (DRIVER §8, D22), not to an HQ:
  - A real technique-selector whose `catalog.read` result on a bf16 run holds no entry reports `techniques: none`, and the round goes on to a spec with an empty `guidance.techniques`.
  - A real coder given the prompt's every-shape sentence keeps its kernel correct at values of the size parameters other than its spec's. This shows in a generation at the other call shapes (RA-0056).

## Boundaries (not decided here)

- **Catalog entries for the bf16 contracts, and the form of `Applies to` that admits them** (OD-22; cited: ADR-0177 Boundaries).
- **Whether verification draws other shapes** (OD-16 sub-question 1).
- **The user-facing entry, real weights and the tokenizer** (OD-31 sub-questions 5, 7 and 10; HQ-0084).
- **The Round-Manager's stop on a failure of `spec.write`** (ADR-0172 decision 2).
- **The ranking of entries and statistics** (OD-7); **the Skill form of the selection criteria** (FR-8).

## References

- Owner: DRIVER §6 D26, D16, D22; [Requirements](../Requirements.md) OD-22, OD-23, OD-31. [OpenDecisionProposals](../OpenDecisionProposals.md) [OD-22](../OpenDecisionProposals.md#od-22), [OD-23](../OpenDecisionProposals.md#od-23), [OD-31](../OpenDecisionProposals.md#od-31). [StandardScenarios](../StandardScenarios.md) S0, S1.
- Records: ADR-0001; [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md); [ADR-0137](ADR-0137-od23-first-case-coder-process-start.md); ADR-0150; [ADR-0151](ADR-0151-od6-first-case-later-round-spec.md); [ADR-0156](ADR-0156-od31-bf16-gemm-contract.md); [ADR-0158](ADR-0158-od31-bf16-rmsnorm-contract.md); [ADR-0159](ADR-0159-od31-bf16-elementwise-add-contract.md); [ADR-0160](ADR-0160-od31-bf16-swiglu-contract.md); [ADR-0161](ADR-0161-od31-bf16-rope-contract.md); [ADR-0162](ADR-0162-od31-bf16-sdpa-kv-cache-contract.md); ADR-0171; [ADR-0172](ADR-0172-od23-first-case-round-one-after-coder-call.md); ADR-0177; ADR-0184; ADR-0189.
- Code: `hilclaw/catalog.py`, `hilclaw/catalog_tool.py`, `hilclaw/spec_tool.py`, `hilclaw/contract_table.py`, `hilclaw/coder_runtime.py`, `orchestration/round-manager.md`, `orchestration/agents/technique-selector.md`.
