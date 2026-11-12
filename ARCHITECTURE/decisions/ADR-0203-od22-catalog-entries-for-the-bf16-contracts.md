# ADR-0203: A `catalog/cpu_standin/` entry may state, in `## Applies to`, the values of any one contract of the contract table; the reader refuses values that name none, and both tools compare a run against each entry's own values; text rules for entries of the bf16 contracts, and the first two entries for `gemm` bf16 (part of OD-22, for `cpu_standin` runs of the contract table)

## Status

- **Accepted on 2026-11-12** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor in task T-0565 and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it.** The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **It serves an owner-approved item**: PLAN P3-15 (the first technique catalog of the six bf16 kinds), one of the items of the purpose-first reorder the owner accepted on 2026-11-12 (cited: PLAN, the paragraph above P3-15; DRIVER §6 D31).
- **Two kinds of content.** What an owner decision, an accepted record, a requirement or a code docstring says is **cited**, with its source named. **Everything else is this record's own**: the scope, the form of `Applies to` for more than one contract, the refusal of values that name no contract, the parameters of the comparison, the id rule across contracts, the text rules for entries of a bf16 contract, the OpenMP rule, the first two bf16 entries, and every weighing.
- **The owner-sentence search.** Searched on 2026-11-12: the bodies of #4, #5, #7 and #8 and the 88 of their comments that hold no "posted by driver" marker, for 카탈로그, catalog, `Applies to`, technique and 기법 beside bf16, and OpenMP. **No owner sentence names the form of `Applies to`, a bf16 entry or its id.** The sentences found that touch the point, each read for what it says and no further:
  - #5 A-7 ② (owner, 2026-10-02): "**OpenMP and SIMD intrinsics are allowed** in stand-in kernels." It is the basis of decision 5's OpenMP rule.
  - PLAN P3-15 (the owner accepted the item; its wording is the integrator's): the form of a document and the `Applies to` judgement stay those of ADR-0150 and ADR-0190, and the frame does not change; "기법의 근거는 문서에 출처로 적고, 측정하지 않은 값을 측정값처럼 적지 않는다". **This record's reading** of the first half: ADR-0150 fixed the four values for its first case only and left the form that admits other contracts to OD-22 (cited: ADR-0150 decision 2, ADR-0190 Boundaries), and the four lines, their order and the judgement stay, so the frame is kept; the catalog is no data-plane file (decision 6). **Its reading** of "근거 … 출처로": an entry states in its own text why the technique may help, from the contract's own arithmetic and memory access, and names no external material, since an entry must be complete without any other file and OD-12 keeps external material open (cited: ADR-0150 decisions 3 and 5). The owner may read it otherwise (Consequences).
- **Open HQs checked and not crossed** (`PROCESS/STATE.json` on `main` `55ae9959`): **HQ-0096** (vendor oracle, LLM-level unit) and **HQ-0100** (nightly #373). Neither is touched.
- **No file, member, value or version of the data plane changes** (decision 6). **It is a record with its code slice**; no `claude` process, Docker daemon, board or real weights were used for it (D16).
- **The status of every OD is unchanged.** Boundaries lists what stays open.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **The gap** (observed, `hilclaw/catalog.py` on `main` `55ae9959`): the reader refuses every entry whose `## Applies to` is not exactly the four lines of the fp32 `gemm` contract (`APPLIES_TO`), and `applies` and `mismatch` compare a run with that one constant. So no entry for a bf16 contract can be written, every bf16 run gets `{"entries": []}` from `catalog.read`, and its technique-selector reports `techniques: none` (cited: ADR-0190 decision 3).
- **What earlier records left to this one**: ADR-0150 decision 2 fixes the four values "for the first case"; ADR-0190 decision 2 says of the comparison "a record that changes that changes their parameters", and its Boundaries keep "catalog entries for the bf16 contracts, and the form of `Applies to` that admits them" with OD-22 (cited). The Requirements OD-22 row keeps "첫 사례 밖 … dtype … 의 카탈로그와 그것을 받아들이는 `Applies to`의 형태" open (cited).
- **The contracts a run may be about** are the seven of `hilclaw.contract_table.TABLE`, keyed by `kind`, `dtype`, `layout` and `language`, with at most one entry per `kind`, `dtype` and `layout` (cited: ADR-0177 decision 1).

## Decision

A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope

- **The directory `catalog/cpu_standin/`**, and the runs whose hw_profile names `accelerator` `cpu_standin` and whose op_signature is covered by a contract of `hilclaw.contract_table.TABLE`: the fp32 `gemm` contract of ADR-0008 and the six bf16 contracts of ADR-0156 and ADR-0158 to ADR-0162 (cited: ADR-0177 decision 1).
- **Outside**: `virtual_npu`, vendor targets, the mock and the candidate kind `compile_settings`, which `catalog.read` refuses before it reads the catalog (cited: ADR-0198 decision 8). The reader is one module for every directory under `catalog/`, and only `cpu_standin` exists (observation); a record that opens a directory for another accelerator decides for itself whether this rule fits it (Boundaries).

### 2. The form of `## Applies to`

- **Still exactly four list lines**, in this order: `- kind: <v>`, `- dtype: <v>`, `- layout: <v>`, `- language: <v>`, with only blank lines before and after them (cited for the form: ADR-0150 decision 2). **Each value is a *name*** of ADR-0001 decision 1 (`[a-z][a-z0-9_]{0,31}`), the form of every `kind`, `dtype` and `layout` value and of `c` (cited: ADR-0001 decision 2; ADR-0002 decision 2).
- **The four values are the key of one contract of the contract table.** An entry whose values name no contract of the table — a typo, a dtype no contract has, an fp32 `rmsnorm` — **is refused by the reader**, with the whole directory, as any other breach of the catalog's rules (cited: ADR-0150's reader, `catalog_unusable` in both tools). *Why*: an entry that names no contract would apply to no run and would never be offered; refusing it makes the mistake show on the first read, in the tests of the commit that adds it, rather than as an entry that is silently never used. *Cost*: a contract removed from the table makes its entries refuse the directory, which then has to change in the same commit; the table changes by record only (cited: ADR-0177), so that commit exists anyway.
- **One entry applies to one contract.** An entry that would serve several contracts is out of scope; the same technique for two contracts is two entries, each with its own id (decision 4).

### 3. The predicate

- **The rule of ADR-0190 decision 2 is unchanged in meaning**: an entry applies to a run when its four values equal the `kind`, `dtype` and `layout` of the run's stated op_signature record and the `language` of the contract that covers it (cited).
- **The comparison stays in one place**, `hilclaw.catalog`, and is now made **against each entry's own values**: `applies` and `mismatch` take the entry's values as their first parameter, as ADR-0190 decision 2 foresaw (cited). The module gives both tools each entry's values beside its `## When` and its `text` from one read of the directory, so neither holds a copy of the comparison.
- **`catalog.read`** returns exactly the entries whose values apply to the run. ADR-0190 decision 3's table holds with "the entries that apply" in place of "the same four entries"; a run with no op_signature, or one no contract covers, still gets `{"entries": []}`; the mock and a damaged catalog still give `catalog_unusable` before any filtering (cited: ADR-0190 decision 3).
- **`spec.write`'s second guard stays**, with its kind `technique_not_applicable` and its message form `<directory>/<id>.md: applies to the <name> <value>, not the spec's <stated>; nothing was written` (cited: ADR-0190 decision 5). It now names the first of the entry's own values that differs, in the order of the four lines.

### 4. Ids

- **ADR-0150 decision 3's rules hold across the whole directory** (cited): one id space per accelerator, whatever contract an entry is for; an id is never given to another technique; an entry removed leaves its id unused for good.
- **An id carries no required part for its kind or dtype.** `## Applies to` states the contract, and an id never reaches a run whose contract it does not name (decision 3). A required prefix would take up to 19 of the 32 characters (`sdpa_kv_cache_bf16_`) for what the entry already states. The first bf16 entries start their ids with `gemm_bf16_` by choice, which is no rule.

### 5. Text rules for an entry of a bf16 contract

They adapt ADR-0150 decision 5 (cited) to the bf16 contracts. **Each `## Guidance` text**:

- **must** say what to change in the kernel and how, and, where the technique touches it, what keeps the kernel within its contract: the prototype and symbol of the kind's record, given in full; the `uint16_t` boundary, with every element of an input and of the output a bf16 bit pattern and every conversion done by the kernel (cited: ADR-0156 decision 5 for `gemm`); the precision of intermediate values and the conversion to bf16 as the kind's record fixes them or leaves them to the kernel (cited for `gemm`: ADR-0156 decisions 3 and 4 — fp32 accumulation, never narrower or wider, and round to nearest, ties to even); every valid shape (cited: ADR-0190 decision 4's table); outputs written before they are read; no alignment beyond that of the element type; and be in English and complete without any other file, entry or link (cited: ADR-0002 decision 1).
- **must not** claim a measured speed-up, a measured or tuned value or a ranking (a block size may be named only as a value to start from, so marked); ask for a compiler flag, a define, a library or a `task.build` member (cited: ADR-0116 decision 2); hold a verification input, a seed or an expected value (cited: ADR-0002 decision 2); or copy or name external code or material (cited: ADR-0150 decision 5; OD-12).
- **OpenMP**: an entry of a bf16 contract **may** suggest OpenMP directives, and `<omp.h>` where the kind's record admits it, because every `cpu_standin` kernel build takes `-fopenmp` (cited: ADR-0188 decision 2) and the owner allowed OpenMP in stand-in kernels (cited above). Such an entry **must** keep each output element's accumulation within the kind's precision rule, ask for no thread count, environment variable or runtime setting (cited: ADR-0188 decision 3, the backend sets none), and make the kernel's result independent of the number of threads it gets. ADR-0150's single-threaded first set was its own choice while HQ-0034 was open (cited: ADR-0150 decision 5); that choice stays for the four fp32 entries. **The two entries of this record use no OpenMP**; a later entry that does is reviewed against this paragraph.
- **Each `## When` text** states, in the terms of the op_signature's shape and of what an earlier attempt shows, when the technique is worth trying, and claims no measured effect (cited: ADR-0150 decision 5).

### 6. A-13 reading

- **No file, member, value or version of the data plane changes.** A spec still gets exactly `{"id": <id>, "text": <text>}` per entry (cited: ADR-0150 decision 4), and `## Applies to` and `## When` never travel into a spec. `catalog/` is a directory of the source repository, not of the data plane (cited: ADR-0150 decision 2), so a change of its form is not a frame change of A-13 (STATE, spec, eval, artifacts). No tool result gains a member: `catalog.read` keeps `{"entries": [{"id", "when"}]}`.
- **`catalog/` is code mode** (cited: ADR-0150 decision 2): entries land by Draft PR, review and tests.

### 7. The first two entries for `gemm` bf16

| id | Gist |
|---|---|
| `gemm_bf16_row_accumulators` | Loops in the order i, p, j over a chunk of columns at a time, the sums of the chunk held in a local array of fp32 accumulators, each element of `a` widened once per chunk, and each accumulator converted once to bf16 at the end. |
| `gemm_bf16_widened_b_panel` | Widen a panel of `b` from bf16 to fp32 once per call into scratch memory of the kernel's own (`malloc`), then run each row's fp32 accumulators over the panel; with a path that computes without the buffer when `malloc` fails. |

- **Why each fits ADR-0156** (cited where named): both keep the prototype and symbol of decision 5, accumulate in binary32 and never narrower or wider (decision 3), convert each output once by round to nearest, ties to even (decision 4), write `c` without reading it, assume no alignment beyond `uint16_t` and handle every m, k, n ≥ 1 (decision 7), and use only headers of the C standard library (decision 8). Scratch memory of the kernel's own is allowed (cited: ADR-0008 decision 6, "scratch memory of its own", which ADR-0156 decision 7 takes over for memory); the panel entry frees it before returning and keeps no pointer.
- **The full texts are the code slice's** and are reviewed against this record; this record does not hold them, so an edit of a text later does not make it false (as ADR-0150 decision 5).

## Alternatives considered

| Alternative | Why not |
|---|---|
| Accept any four *name* values, and let an entry that names no contract apply to no run | A typo makes an entry silently unused; the refusal finds it on the first read. |
| One entry with several `Applies to` blocks or lists of values | A new form for a need no entry has yet; one entry per contract keeps the comparison a plain equality. |
| Keep `APPLIES_TO` and add a second constant for bf16 | The reader would grow a constant per contract; the table already lists them. |
| Require ids of bf16 entries to start with the kind and dtype | Decision 4. |
| Single-threaded only, as the first fp32 set | The owner allowed OpenMP and ADR-0188 builds every kernel with it; a rule that keeps the result and the precision rule is enough. |
| Ask the owner (an HQ) | OD-22 is not owner-only (DRIVER §9), the form question was left to OD-22 by two records, and no data-plane frame changes. |
| Land entries for all six bf16 kinds here | Beyond the task size (DRIVER §5); T-0566 does the other five on the form fixed here. |

## Consequences

- **The slices.** This record's: `hilclaw/catalog.py` parses and checks the four values of each entry, gives each entry's values with its criteria and its text, and compares against them; `hilclaw/catalog_tool.py` and `hilclaw/spec_tool.py` use that; `catalog/cpu_standin/` gains the two `gemm` bf16 entries of decision 7. **T-0566**: entries for `rmsnorm`, `elementwise_add`, `swiglu`, `rope` and `sdpa_kv_cache`, on the form and text rules of decisions 2 and 5. **PLAN P3-15 is checked when every one of the six bf16 contracts has at least one entry.**
- **The table of ADR-0190 decision 3 now reads**: a `gemm` bf16 run on `cpu_standin` gets the two `gemm` bf16 entries; each of the other five bf16 runs gets `{"entries": []}` until T-0566; an fp32 `gemm` run gets the same four entries as before.
- **Less exact, not edited**: ADR-0150 decision 2 ("exactly four list lines `- kind: gemm`, …"), now the form of decision 2 here with the fp32 values as one case; ADR-0190 decision 2 ("They take no entry, because every entry … states the same four lines"); ADR-0190 decision 3's first row for `gemm` bf16; ADR-0171 decision 3's "every entry applied to every spec".
- **UsageCases and StandardScenarios** (S0 and S1 rechecked): S1 step 4 selects techniques from the catalog (FR-7) for bf16 runs too now; no step changes, no verdict changes, no gap.
- **Runtime acceptance items** (D16; nothing was tried with a real `claude`). They go to [PROCESS/RuntimeAcceptance.md](../../PROCESS/RuntimeAcceptance.md) (DRIVER §8, D22), not to an HQ:
  - A real technique-selector of a `gemm` bf16 run on `cpu_standin` receives the two `gemm` bf16 entries from `catalog.read`, may choose one, and `spec.write` writes a spec that carries it.
  - A real coder given one of the two entries writes a kernel that passes the bf16 `gemm` check.
- **The cost, plainly.** The entries are hand-written candidates, not measured knowledge (cited: ADR-0150 decision 3). The reading of PLAN P3-15's "출처" in Status is this record's; if the owner wants external sources cited in entries, that is OD-12's and changes decision 5.

## Boundaries (not decided here)

- **OD-22's cold-start methods** (optimization rewind, git history mining) and **UC-5's curator flow**.
- **OD-7**: the entry criterion, statistics and the ranking of entries.
- **The Skill form of the selection criteria** (FR-8; cited: ADR-0171).
- **Catalogs for other accelerators** (`virtual_npu`, vendor targets) and whether this record's rule fits them.
- **fp16** and every contract not in the table; **entries for several contracts**.
- **Whether external material may be named in an entry** (OD-12).

## References

- Owner: #5 A-7 ② (OpenMP and SIMD intrinsics allowed in stand-in kernels); DRIVER §6 D31, §9, D16, D22; PLAN P3-15. [Requirements](../Requirements.md) FR-7, FR-8, C-6, OD-22. [OpenDecisionProposals](../OpenDecisionProposals.md) [OD-22](../OpenDecisionProposals.md#od-22). [StandardScenarios](../StandardScenarios.md) S0, S1. [UsageCases](../UsageCases.md) UC-5.
- Records: [ADR-0001](ADR-0001-od4-key-schema.md); [ADR-0002](ADR-0002-od6-codegen-spec.md); [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md); [ADR-0116](ADR-0116-od18-cpu-standin-build-settings.md); [ADR-0150](ADR-0150-od22-first-case-technique-catalog.md); [ADR-0151](ADR-0151-od6-first-case-later-round-spec.md); [ADR-0152](ADR-0152-od31-llama-forward-operations.md); [ADR-0156](ADR-0156-od31-bf16-gemm-contract.md); [ADR-0171](ADR-0171-od23-first-case-round-techniques-and-coder-delegation.md); [ADR-0177](ADR-0177-od18-od6-contract-table.md); [ADR-0188](ADR-0188-od18-standin-openmp-in-the-build-set.md); [ADR-0190](ADR-0190-od22-catalog-read-by-contract-and-coder-every-shape.md); [ADR-0198](ADR-0198-od32-compile-settings-candidate-kind.md).
- Code: `hilclaw/catalog.py`, `hilclaw/catalog_tool.py`, `hilclaw/spec_tool.py`, `hilclaw/contract_table.py`, `catalog/cpu_standin/`.
