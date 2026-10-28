# ADR-0179: The time limits of the bf16 verification builds and processes at `cpu_standin` — ADR-0117's rule unchanged, with a work measure per kind: the kind's nominal operation count plus 10 per element of the program's arrays; 60 s for each build; the shared header copied beside the kind's program; every container situation answered as for fp32 `gemm` (part of OD-14 and of OD-18 sub-question ⑱ (다))

## Status

- **Accepted on 2026-10-28.** It answers the part of [ADR-0177](ADR-0177-od18-od6-contract-table.md) decision 5 item 2 that no record states: the time limits of the `cpu_standin` operation of `correctness.check` for bf16 `gemm`, `rmsnorm`, `elementwise_add`, `swiglu` and `sdpa_kv_cache` (PLAN P2-11, P2-14). [ADR-0117](ADR-0117-od14-cpu-standin-time-limits.md) fixes the limits of the first case only (its decision 1 and Limit 6).
- **Two kinds of content.**
  - **Cited**: statements of accepted records, each with the record named; owner answers are marked **owner** and are not subject to the objection window below.
  - **This record's own**, every other sentence: the work measure, its constant, the reading of the copies, the scope reading of the container records, and every weighing. That part is accepted under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it**, is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **Session entry check** (CLAUDE.md), on 2026-10-28 before any edit of `ARCHITECTURE/`: open PRs — none (`gh pr list`); issue #4 — last comment 2026-07-31; issue #5 — last comment 2026-10-28T04:42Z, the driver notice of ADR-0178; issue #7 — last comment 2026-09-07; issue #8 — closed; `PROCESS/STATE.json` on `main` `797ccc3c` — **HQ-0076** (owner values of the nightly routine, D17) is the only unresolved HQ and is not crossed. **No owner sentence on the time limits of a bf16 check was found.**
- **Not owner-only**: nothing here chooses a tolerance, a seed source, a number of draws, a gate, a dtype or a scope (#5 A/B, C-6, OD-25, OD-3). `draws` stays the instance's and OD-16 sub-question ⑤'s; this record only reads it.
- **Not changed**: no schema file, no member, value or meaning of a member of `instance.json`, a spec, `STATE.json` or `artifacts.json`, no member of the envelope or of the `data` of a line of `events.ndjson`, no `step` value, no value of `condition`, no failure kind, no request or result member of a tool, no version and no validator of the data plane; no dependency (decision 8, A-13 reading). No `claude` process was started and nothing needs a board, a real container runtime or a key (D16).
- **Answers** part of **OD-14** (the call level of the timeout hierarchy for these runs, and the container of sub-question ① for them — a run outside the first case) and part of **OD-18** sub-question ⑱ (다) (the situations a container adds and their answers, for these runs outside the first case). Each OD keeps its status. ⑱ (라) is not answered further: the build settings of these runs are ADR-0177 decision 3's reading of [ADR-0116](ADR-0116-od18-cpu-standin-build-settings.md).
- It builds on ADR-0116 (decision 2), ADR-0117 (all), [ADR-0144](ADR-0144-od14-first-case-build-run-container.md) (decisions 2 and 3), [ADR-0163](ADR-0163-od31-bf16-verification-run.md) (decisions 2, 3, 10 and 11), [ADR-0165](ADR-0165-od31-bf16-sdpa-kv-cache-verification-run.md) (decisions 2 to 6, 11 and 12), [ADR-0168](ADR-0168-od18-standin-container-situations.md) (decisions 2 and 5), [ADR-0169](ADR-0169-od18-standin-build-log-and-removal.md), [ADR-0152](ADR-0152-od31-llama-forward-operations.md) (decision 5) and ADR-0177 (decisions 2 and 3); none of them is edited. **If one of them is reverted, this record is revisited with it.** The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **What an operation is handed** (cited: ADR-0177 decision 3): the seed, `draws`, the `kind` and `dtype` of the covering entry and the dimensions in the order of the contract's `task_contract` parameters — `hilclaw.check_parameters.Bf16CheckParameters` (observation). For fp32 `gemm` it keeps receiving `m`, `k`, `n`.
- **The programs** (cited: ADR-0163 decision 2, ADR-0165 decision 2): one C source per kind under `hilclaw/harness/`, each including the shared header `bf16_verification.h` with quotes, found "next to the program sources, so no include directory is needed" (observation: `bf16_verification_build.py`). Sizes (observation): 85 to 179 lines per program and 185 lines of header, against 224 lines of `verification_program.c`. The command lines are ADR-0163 decision 3 and ADR-0165 decision 3; "One call per draw" (ADR-0163 decision 10). The program does "no floating-point arithmetic" and handles bf16 "as `uint16_t` patterns" (ADR-0163 decision 2).
- **What a draw costs the program besides the kernel**: it draws every input element from the shared generator, computes the check value, fills the output (and, for `sdpa_kv_cache`, the two cache allocations of l + 2m rows) with `0x7FC0` and writes the report (cited: ADR-0163 decisions 4, 5, 8; ADR-0165 decisions 4, 5, 8). The report at the largest shapes is 131,334,148 bytes per draw for `gemm` at lm_head M = 512 and 20,971,524 for `sdpa_kv_cache` at m = l = 2048 (cited: ADR-0163 Limit 4; ADR-0165 Limit 4).
- **The shapes** (cited: ADR-0152 decision 5, as the contract modules list them; observation): `gemm` M ∈ {1, 32, 512} over QKV, O, gate/up, down and lm_head 2048 → 128256 — lm_head "excluded from the first runs" (cited: ADR-0156 Status, K1); `rmsnorm` and `elementwise_add` T × 2048, `swiglu` T × 8192, T ∈ {1, 32, 512}; `sdpa_kv_cache` (m, l, h, h_kv, d) ∈ {(128, 128, 32, 8, 64), (1, 128, 32, 8, 64), (2048, 2048, 32, 8, 64), (1, 2048, 32, 8, 64)}.
- **ADR-0117's rule**: P = min(1500 s, 10 s + c × (1 s + W / R)), W = 2·m·k·n, R = 2 × 10^8 per second, c = `draws` for a verification process; B = 60 s for a build; the longest call 1560 s against the MCP idle window of 1800 s (cited: its decisions 3 to 5).

## Decision

A sentence is **cited** when a record and its decision is named with it; every other sentence is **this record's own**.

### 1. Scope and terms

- **The runs**: a check of bf16 `gemm`, `rmsnorm`, `elementwise_add`, `swiglu` or `sdpa_kv_cache` at a run whose hw_profile names `cpu_standin` (ADR-0177 decision 3, the `cpu_standin` bullet). **Not covered**: `rope` (its check waits on the start position, cited: ADR-0177 decision 4), the bf16 timing run (no record defines one), the mock (given no setting, cited: ADR-0117 decision 1), fp32 `gemm` (ADR-0117, unchanged).
- **The two limits**: the build of the verification executable (B) and its process (P), as ADR-0117 decision 1 defines a limit.

### 2. The source: ADR-0117 decision 2, unchanged

- **The limits are given by constants and one rule of the tool package, applied by the `cpu_standin` operation of `correctness.check` to the values it is handed** — the kind, the dimensions in `task_contract` order and `draws`. They change only by a commit of the source repository; no operation reads one from a file, a variable or the hw_profile, and the tool function hands none over. ADR-0117 decision 2's weighing of (a) to (d) holds as it stands: these runs add nothing that changes any of its six rows.

### 3. The process limit: ADR-0117's rule with a work measure per kind

- **P = min(1500 s, 10 s + `draws` × (1 s + W / R))**, R = 2 × 10^8 per second, with **W = A + 10 · E**:
  - **A**, the nominal operation count of the kind's textbook computation where it grows faster than the elements: **2·m·k·n** for `gemm` (as ADR-0117); **4·m·l·h·d** for `sdpa_kv_cache` (the two products Q·Kᵀ and P·V of each query head over all l positions, a multiplication and an addition each; the causal mask and the softmax are left to the element term and to R being a floor); **0** for `rmsnorm`, `elementwise_add` and `swiglu`, whose work per output element is a bounded number of operations (one `expf` in SwiGLU among them) and is taken into the element term.
  - **E**, the number of elements of the program's arrays in one draw: `gemm` m·k + k·n + m·n; `rmsnorm` 2·m·n + n; `elementwise_add` and `swiglu` 3·m·n; `sdpa_kv_cache` 2·m·h·d + 2·m·h_kv·d + 2·(l + 2m)·h_kv·d (q and out, k_new and v_new, and the two allocations of ADR-0165 decision 5).
  - **10 per element** (`BF16_ELEMENT_WEIGHT`): at R it allows 50 ns per element and draw for drawing, checking, filling and reporting it (and for the element-wise kinds, computing it). **This record's estimate**: a few ns per element for the generator and the check value, and a few ns per reported byte through the container client's pipe on a C-7 machine; so 50 ns is several times that, as R is for the products.
- **Why an element term**: at lm_head M = 1 the kernel's W = 2·m·k·n ≈ 5.3 × 10^8 allows 2.6 s per draw, while the program draws and checks about 2.6 × 10^8 input elements per draw (b is k·n); by the estimate above that alone can take one to three seconds, so ADR-0117's 1 s per call does not cover it. With the term the same draw is allowed about 16.8 s. At the shapes ADR-0117 covered, a bf16 `gemm` gets ADR-0117's value plus 10·E / R per draw (1.1 s at down, M = 512).
- **The values at the largest shape of each kind** (computed by the rule):

| Kind, shape | A | E | Per draw | One draw | Draws under the cap |
|---|---|---|---|---|---|
| `gemm` 512 × 2048 → 128256 (lm_head) | 2.69 × 10^11 | 3.29 × 10^8 | 1362.3 s | 1372.3 s | 1 |
| `gemm` 512 × 2048 → 8192 (gate/up; down alike) | 1.72 × 10^10 | 2.20 × 10^7 | 88.0 s | 98.0 s | 16 |
| `gemm` 1 × 2048 → 128256 | 5.25 × 10^8 | 2.63 × 10^8 | 16.8 s | 26.8 s | 88 |
| `sdpa_kv_cache` (2048, 2048, 32, 8, 64) | 3.44 × 10^10 | 1.68 × 10^7 | 173.6 s | 183.6 s | 8 |
| `swiglu` 512 × 8192 | 0 | 1.26 × 10^7 | 1.63 s | 11.6 s | 914 |
| `elementwise_add` 512 × 2048 | 0 | 3.15 × 10^6 | 1.16 s | 11.2 s | 1287 |
| `rmsnorm` 512 × 2048 | 0 | 2.10 × 10^6 | 1.10 s | 11.1 s | 1348 |

- **A kernel that is not slow** (estimate: 10^9 operations per second and 5 ns per element) takes at lm_head M = 512 about 270 s per draw, so five draws complete within the cap; at `sdpa_kv_cache` m = l = 2048 about 35 s per draw, so a check of up to 8 draws gets its full value and one of more gets 1500 s, in which about 40 such draws fit.

### 4. The build limit: 60 s

- **B = 60 s**, ADR-0117 decision 3's value: a build compiles one program of 85 to 179 lines and a header of 185 lines beside the kernel, no more than `verification_program.c`'s 224 lines, with the same flags. ADR-0117's estimate and its cost (a source the compiler takes longer with is a broken `build_time_limit`) hold as they stand.

### 5. How the program and the header reach the build directory

- **The kind's program is the harness program of ADR-0144 decision 2 Q3** and is copied as it is copied for fp32 `gemm`, beside the kernel sub-directory, and handed to the compiler first (cited: ADR-0163 decision 2's order, `bf16_verification_build`).
- **The header `bf16_verification.h` is copied beside it, a second harness copy, and handed to the compiler as no source.** It is read and written as the program is (no link followed, a new regular file, nothing carried over), after the kernel's and the program's copies and only when the reader found a kernel source. Reasons: the program includes it with quotes and the compiler looks first in the directory of the including file, so the copy beside the program is found with no flag; a kernel file of the same name lies in the kernel sub-directory, where the program's include does not look first, so it cannot replace the header; and adding an include directory would be a flag outside ADR-0116's fixed set.
- **Its answers are the copies' answers** (cited: ADR-0168 decision 2, rows C12, C13): a header that cannot be read or is no regular file is C12, `build_input_missing`, as a missing program; an entry already at its name or a write that fails is C13, `build_directory_unusable`; "no kernel source" (C15) is answered before the header is looked at, so nothing of it is copied.

### 6. The containers and their situations

- **These runs build and run in the containers of ADR-0144** (decisions 2 and 3: one container for the build, a second for the process, the build directory the only mount), **and every situation of ADR-0168 and ADR-0169 is answered as for fp32 `gemm`**: the image (C1, C2), the build directory (S3), the copies (C12, C13, C15 as decision 5 reads them), the client statuses 125 to 127 (in a build the container runtime's, in a process the program's), the build log handed to the keeper (ADR-0169 decisions 2 and 3), the removal of the build directory (ADR-0168 decision 5) and the 60 s of a forced removal (ADR-0169 decision 5). Reason: nothing in these situations depends on which program is built or which arguments the process gets; ADR-0144 decision 1 and ADR-0168 limit them to the first case only because no other run existed.
- The program's own exit statuses (2 for the command line, 3 for the allocations; cited: ADR-0163 decision 3, ADR-0165 decision 3) are statuses of the process, answered `exit_status` as every status other than 0 is (cited: ADR-0017 decision 7, ADR-0168 decision 2).

### 7. What a call answers when a limit is reached

- **No new answer** (cited: ADR-0117 decision 7): a build past B is a broken result `build_time_limit`, a process past P a broken result `time_limit`. Both are broken results of the list the owner gave for a bf16 check (**owner**, HQ-0077, through ADR-0177 decision 3), which hold no counts (cited: ADR-0042 decision 7). The values are positive, finite and at most 1500 s, so a value the functions refuse follows only from a defect of the code (cited: ADR-0117 decision 7).
- **The operation refuses before anything is started** a value the rule does not serve — a kind outside decision 1 (`rope` among them), a `dtype` other than `bf16`, dimensions of another number or below 1 — and what the kind's command line refuses (cited: ADR-0165 decision 3, l ≥ m and h a multiple of h_kv), as it raises for fp32 values (C16: no row; the tool function admits only covered records before the call).

### 8. The MCP idle window and the Bash limit (OD-18 ③)

- **The longest call these limits allow** is 60 + 1500 = **1560 s**, as for fp32 `gemm`, plus the tool function's own work, which nothing here bounds (cited: ADR-0117 decision 5). The idle window of 1800 s leaves 240 s for that work.
- **That work per draw** (the regeneration and the float64 reference of the Python side; cited: ADR-0163 decision 6, ADR-0165 decision 6): `sdpa_kv_cache` at m = l = 2048 **1.03 s, measured** (cited: ADR-0165 decision 6), so about 230 draws fit; this record's estimates — under 0.1 s for the element-wise kinds at T = 512, about 1 to 3 s for `gemm` at the projections with M = 512, and 15 to 60 s for `gemm` at lm_head M = 512, whose input alone peaks at about 4.2 GB (cited: ADR-0163 Limit 4), so a check of lm_head M = 512 fits the window only up to about four draws. A check whose process reached its limit holds no counts and is not judged.
- **The Bash default of 600 s does not fit** at `gemm` M = 512 and `sdpa_kv_cache` m = 2048 from a few draws on; what then holds is OD-18 ③, as ADR-0117 decision 5 says for fp32 `gemm`.

### A-13 reading

- **No data-plane schema change**: the operation returns the bytes of the report as for fp32 `gemm`, the tool function judges them into the result the owner gave (HQ-0077), and a limit reached is an existing value of `condition`. No member, file, kind, `step` value or version is added or changed; the rule reads only values the operation is already handed.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 3 | (i) ADR-0117's rule with W = A only (the kind's operations, no element term) | At lm_head M = 1 the 1 s per draw and 2.6 s of products do not cover drawing and checking 2.6 × 10^8 elements by the estimate; the element-wise kinds would get the 1 s per draw whatever their size. |
| 3 | (ii) A rate or a constant per kind (for example R per kind, or a fixed P per kind) | No measurement says how fast a kind's straightforward kernel runs; a rate per kind would be several invented numbers where one floor already has a stated meaning (ADR-0117 decision 4), and a fixed P has ADR-0117 decision 2's cost (a hang costs the whole value at every shape). |
| 3 | Counting the softmax's `exp` and the causal half in A | A nominal count with more terms says no more: R is a floor, and the causal mask halves the products only on average over rows. |
| 3 | The element term for fp32 `gemm` too | Changes ADR-0117's values for the first case; out of this record's scope. |
| 4 | A longer build limit for the larger SDPA program | It is still shorter than the first case's program. |
| 5 | An include directory (`-I`) for the header | A flag outside ADR-0116's fixed set, and it would let a kernel include the harness header. |
| 5 | Inlining the header into each program | Changes six harness programs and the shared code ADR-0163 decision 2 allows to be one header. |

## Consequences

- **Code slice** (landed with this record): `hilclaw.standin_settings` gains `bf16_verification_process_time_limit_s`, `BF16_CHECK_KINDS` and `BF16_ELEMENT_WEIGHT`; `hilclaw.standin_check.operation` takes `Bf16CheckParameters` for the five kinds, copies the kind's program and `BF16_HEADER`, builds with ADR-0116's set within `BUILD_TIME_LIMIT_S` and runs the program with the kind's `program_arguments` within that limit; `hilclaw.contract_table` sets `checked` for the five entries, so `correctness.check` admits them (ADR-0177 decision 2, "After slice 2"); `rope` stays not `checked` and every `timed` flag stays as it is.
- **Not edited and now less exact**: ADR-0117 Limit 6 ("other backends … are not covered") stays exact for the backends; its scope now has this record beside it for the bf16 checks. ADR-0144 decision 1 and ADR-0168's scope ("the first case") are read with decision 6 for these runs.
- **Runtime acceptance items** (D16; to [PROCESS/RuntimeAcceptance.md](../../PROCESS/RuntimeAcceptance.md), D22 — closed by the owner by hand or by the runtime's own self-check, never by a driver task): (1) that the values of decisions 3 and 4 let a correct, untuned kernel of each of the five kinds complete at the shapes of ADR-0152 and end one that does not end, on each C-7 system and in the container of ADR-0144 — in particular that the 10 per element covers drawing, checking and reporting the 2.6 × 10^8 input elements of lm_head at M = 1 and the report of 131 MB per draw at M = 512 through the container client; (2) the number of draws up to which the tool function's own work stays inside the 240 s of decision 8 for `gemm` at lm_head M = 512 and at the projections at M = 512. That the rule gives the stated values is no such item: the tests of the code slice check it.

## Boundaries (not decided here)

- `rope` and its start position (ADR-0177 decision 4); the bf16 timing run and its limits (OD-13, OD-16 ⑥); fp32 `gemm` (ADR-0117).
- The rest of OD-14: the kernel watchdog, a limit of the whole call, resource caps, health checks, reset and the blacklist; the container image and runtime beyond ADR-0144.
- OD-18 ③ (progress notifications, the idle window); ⑱ (가) (a limit stated for a run); OpenMP (HQ-0034); any flag outside ADR-0116's set.
- Owner-only (DRIVER §9): tolerances, the seed source and the number of draws (OD-16 ⑤), the #5 A and B items, OD-3, OD-25, C-6.

## References

- [Requirements](../Requirements.md): NFR-4, FR-9, FR-10, C-6; register rows OD-14, OD-18.
- [OpenDecisionProposals OD-14](../OpenDecisionProposals.md#od-14) (sub-question ①), [OD-18](../OpenDecisionProposals.md#od-18) (sub-questions ③, ⑱).
- ADR-0001; ADR-0017 (decision 7); ADR-0042 (decision 7); ADR-0116 (decision 2); ADR-0117; ADR-0144 (decisions 1 to 3); ADR-0152 (decision 5); ADR-0156 (Status, K1); ADR-0163 (decisions 2 to 6, 8, 10, 11); ADR-0165 (decisions 2 to 6, 8, 11, 12); ADR-0168 (decisions 2, 5); ADR-0169 (decisions 2, 3, 5); ADR-0177 (decisions 2 to 5).
- `hilclaw/standin_settings.py`, `hilclaw/standin_check.py`, `hilclaw/standin_copies.py`, `hilclaw/contract_table.py`, `hilclaw/harness/bf16_verification_build.py`; PROCESS/PLAN.md P2-11, P2-14; task T-0502.
