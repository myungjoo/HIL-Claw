# ADR-0164: The verification run of one built bf16 RoPE kernel (kind `rope`) on `cpu_standin` — a fifth verification program, the `freqs_cis` rows handed over on standard input, a start position per run, the table built on the Python side with ADR-0161's constants, the generator for `x`, the output fill, the float64 reference, an input check over `x` and the rows, the report, the verdict and the calibration (P2-12 harness record, second part; part of OD-31 sub-question 3 and of OD-16)

## Status

- **Accepted on 2026-10-25.** It is the second part of the harness record that the bf16 contract records of PLAN P2-11 leave their verification mechanism to (PLAN P2-12); [ADR-0163](ADR-0163-od31-bf16-verification-run.md) is the first.
- **Three kinds of content.**
  - **Owner answers, cited and marked owner**: HQ-0065 and HQ-0066 in `PROCESS/STATE.json`, as [ADR-0154](ADR-0154-od31-owner-answers-heads-bf16-oracle.md) decisions 1 to 3 record them, and the HQ-0004 answer as [ADR-0017](ADR-0017-od16-cpu-standin-verification-run.md) decisions 4 to 6 quote it. They are **not subject to the objection window** below.
  - **Cited**: statements of accepted records ([ADR-0003](ADR-0003-od16-harness-calibration.md), ADR-0017, [ADR-0107](ADR-0107-od16-verification-and-timing-build-relation.md), ADR-0154, [ADR-0161](ADR-0161-od31-bf16-rope-contract.md), [ADR-0162](ADR-0162-od31-bf16-sdpa-kv-cache-contract.md), ADR-0163), each with the record and decision named, and facts of the code at `4528948`.
  - **This record's own**, every other sentence: the program, the channel of the rows, the start position, the table's constants and `d`, the input check over the rows, the calibration fixtures and every weighing. That part is accepted under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it, is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **The owner-sentence search.** Searched: the body of #4 and its 6 comments; the body of #5 and the 46 of its 262 comments without a "posted by driver" marker; the bodies of #7 and #8 and their comments (2 and 6). Terms: RoPE, rotary, freqs, cos, sin, position, 위치, 회전, verification, 검증, harness, 하네스, seed, 시드, reference, tolerance, bf16, table. Found, each read for what it says and no further:
  - **K1** — the B-4 answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285): "RoPE" as part of Llama 3.2 1B, the attention configuration "follows Llama 3.2 1B", nntrainer read for idioms "(… softmax_row, rotary)". Nothing of a table, a position or a verification.
  - **K2** — the HQ-0004 answer (comment 6052377983), the HQ-0005 answer (comment 6117798837), A-12 (comment 5946779596), A-6 (comment 5933950693) and the C-6 revision (comment 6280029924), read as ADR-0163 Status reads them (its K1 to K4): the float64 reference on the Python side, the kernel's process holding neither reference nor comparison, inputs drawn anew per check, the harness in one sub-module, the tolerance an instance parameter, bf16/fp16.
  - **Ordinary words only**: "position" and "위치" are locations (of a file, a decision, a check); "table" is a Markdown table (#5 comment 5969015070, #8 comment 5566901377); cos, sin, freqs and 회전 have no hit as words.
  - **Nothing found** on the frequency table in a verification, which rows a draw uses, how the table reaches a program or the T = 1 position. **Conflicts**: none.
- **Open HQs checked and not crossed** (`PROCESS/STATE.json` on `main` `4528948`).
  - **HQ-0070** (the RoPE scale factor, 8 or 32): not crossed. No scale factor is chosen for the model; the verification table uses the constants ADR-0161 decision 13 names, "the constants of decision 4 (s = 8) whatever the answer on the scale factor, since the kernel's verification needs angles, not the model's" (decision 4).
  - **HQ-0033** (the ADR-0116 flags): no flag is chosen, and the program does no floating-point arithmetic (decision 2).
  - **HQ-0069** (runtime acceptance (lxvii)): no runtime fact is used.
  - Not touched: HQ-0021, HQ-0048 (rounds), HQ-0022, HQ-0024, HQ-0026, HQ-0028, HQ-0029 (code tasks), HQ-0023, HQ-0027 (review limits of other records) and the runtime-acceptance HQs HQ-0013, HQ-0014, HQ-0016 to HQ-0019, HQ-0030, HQ-0035 to HQ-0039, HQ-0042, HQ-0044 to HQ-0047, HQ-0049 to HQ-0052, HQ-0054 to HQ-0063 and HQ-0068.
- **Not changed**: no schema file, member, file, version or validator of the data plane; the report and the bytes on standard input are internal interfaces of the harness (as ADR-0017 decision 7). It is a record, not code: nothing was built, no `claude` process was started, and every figure below was computed in a throwaway interpreter that changed no repository file (D16).
- **Answers**: of **OD-31 sub-question 3**, for `rope` in bf16 on `cpu_standin`: the generator for `x`, which table rows a draw uses, the output fill, the widening and the reference; not the seed's source or the number of draws. Of **OD-16**: the verification run of `rope` at `cpu_standin` (a confirmed part, as ADR-0163 is for four kinds), and part of **sub-question ②** (calibration repeated for this kind). Open of them: Boundaries.
- It builds on ADR-0003 (decisions 2 to 7), ADR-0017 (decisions 2 to 10 and Alternatives), ADR-0107 (decision 1), ADR-0154 (decisions 1 to 3), ADR-0161 (decisions 3 to 13), ADR-0162 (decision 13) and ADR-0163 (decisions 1 to 11); none of them is edited. **If ADR-0017, ADR-0161 or ADR-0163 is reverted, this record is revisited with it.** The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **What exists** (code at `4528948`): ADR-0163's four programs `hilclaw/harness/bf16_verification_<kind>.c` with the shared header `bf16_verification.h` (argument rules, the generator, the output fill `0x7FC0`, the CRC-32 check value of two byte ranges, the report descriptor), the Python side `bf16_verification_arrays.py` and `bf16_verification.py`, and the build step `bf16_verification_build.py` with one program source per kind. `hilclaw/rope_table.py` builds the table of ADR-0161 decision 4 (`build`, a `float32` array of positions 0 … `positions` − 1, every constant a required argument, row 0 exactly 1.0 and +0.0). `hilclaw/local_run.py` starts a process with standard input set to the null device.
- **What ADR-0161 leaves here** (its decision 13): the value set of `x` (the 256 bf16 values of magnitude in [0.5, 1)); `freqs_cis` = rows P … P+T−1 of the table built with θ = 500000, s = 8, a = 1, b = 4, L = 8192, rows 0 … T − 1 for T ∈ {128, 2048} and row 127 or 2047 for T = 1 (ADR-0154 decision 1); and, left to this record, "generator, seed, draws, which T = 1 row a draw uses, the content of `out` before the call, the widening".
- **The new question**: `freqs_cis` is not drawn but built outside the kernel (ADR-0161 decision 4) with correctly rounded entries, while a verification program does no floating-point arithmetic (ADR-0163 decision 2) and the first case's program reads "no standard input, no file and no environment variable" (ADR-0017 decision 9).

## Decision

A sentence marked **owner** renders an HQ answer through the record named. A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**. "As ADR-0163 decision n" applies that decision to kind `rope` with the substitutions stated, and nothing else of it.

### 1. Scope

- The **verification run of one built attempt** of a C kernel of ADR-0161 (`rope`, bf16) at `cpu_standin`; the terms of ADR-0017 decision 1, with **draw** meaning one set of values of `x`.
- **Not covered**: **SDPA with KV cache**, left to a later harness record, because its verification needs the content of cache rows P … l − 1, guard rows past l and a comparison of the written cache rows (ADR-0162 decision 13), mechanisms no other kind has; the **bf16 timing run**, with whether ADR-0107's rule extends to it, as ADR-0163 decision 2 leaves them.
- Not an FR-10 tool contract (as ADR-0163 decision 1); ADR-0017, ADR-0161, ADR-0163 and the first case are unchanged.

### 2. Program and process

- **A fifth verification program** under `hilclaw/harness/`, calling `hilclaw_rope_bf16` (ADR-0161 decision 9), **as ADR-0163 decision 2**: one kernel per executable built by one call of `clang_build.build` with the caller's flags, a process of its own through `local_run.run`, every identifier besides `main` of internal linkage, the shared header reused, no floating-point arithmetic. The table rows are bytes it receives and copies (decision 3); it never converts or computes a `float`.
- **What changes**: it reads standard input (decision 3), and it keeps the received rows in a buffer of its own from which it copies them into the kernel's `freqs_cis` array before each call, so every draw passes the same rows whatever a kernel did to its inputs, as ADR-0163 decision 6 regenerates the inputs of every draw.

### 3. How the `freqs_cis` rows reach the kernel

- **The Python side writes the m rows to the process's standard input**, as the 4·m·d bytes of their binary32 patterns in memory order and host byte order, and closes it. The program reads exactly that many bytes before its first draw and then requires end of input; a short or a longer input ends the process with a non-zero status (the status number is the code task's), and the run is broken (decision 10, as ADR-0163 decision 8). The Python side keeps its own copy, from which the reference and the check value are computed, so **no part of the reference rests on bytes from the kernel's process** (ADR-0017 Alternatives, as ADR-0163 decision 6 carries it).
- **This departs from ADR-0017 decision 9** ("no standard input, no file and no environment variable"), for kind `rope` only; the four kinds of ADR-0163 keep it. Reasons: the rows are not drawn — they are a public function of `d` and the positions, the same for every seed, so handing them over tells the kernel nothing it could not compute itself, and FR-9's secret (the seed) stays on the command line as before; ADR-0017 rejected handing inputs to the program because "`local_run` gives a process no standard input, a file is excluded … and a command line cannot hold them", and of those only the first stands against standard input, which is a property of the runner, not of the principle.
- **The cost**: `local_run.run` gains an optional standard-input argument (code slice 1), with the null device kept when it is absent, so every present caller is unchanged.
- Weighed and rejected (Alternatives): the **command line** — 131,072 arguments and 1,426,466 bytes of decimal patterns with their terminators at m = 2048, d = 64 (computed), past Windows' 32,767-character command line and near Linux's default limit for arguments and environment together; a **file the harness writes** — a path, a writer rule and a clean-up (ADR-0017 Alternatives, point 7), for input values the principle of OD-16 keeps out of files; a **generated C source of the rows** built into the executable — a source the harness adds to the caller's build, 1.4 MB of initialiser text compiled with the caller's flags, and an executable tied to one P and m where every other verification executable serves any dimensions; **entries computed in the program** — floating-point arithmetic against decision 2, and correctly rounded entries (ADR-0161 decision 4) need the builder's extended-precision method, not a C library call.

### 4. Which table rows a draw uses

- **The start position P is a parameter of the run**, given by the caller with no default and held by the Python side only: an integer ≥ 0. Every draw of a run uses rows P … P+m−1. P is not on the program's command line, since the program receives the rows themselves.
- **For the op_signature shapes the caller passes ADR-0161 decision 13's positions**: P = 0 for m ∈ {128, 2048}; P = 127 or P = 2047 for m = 1, one per run. Whether a check of an m = 1 op_signature runs both is the caller's policy, with the number of draws (OD-16 sub-question ⑤). Reasons: the kernel's work does not depend on P (ADR-0161 decision 3), so one P per run sends the rows once and keeps the program free of any choice; a P drawn from the seed and the draw would need both rows sent, a selection in the program and a check value per row, and has a single value (P = 0) at m ∈ {128, 2048} and no set at any m outside {1, 128, 2048}.
- **Another m** (outside {1, 128, 2048}) is admitted with any P the caller gives, as other shapes are for ADR-0163's kinds (OD-16 sub-question ① stays open); the rows are still rows of the same table.
- **The table's constants** (ADR-0161 decisions 4 and 13): θ = 500000, s = 8, a = 1, b = 4, L = 8192, `head_dim` = d. **When the caller's `d` is not 64**, the table is built for that `d` with the same five constants, not refused. Reasons: the rule of ADR-0161 decision 4 is defined for every even d and the contract binds a kernel for every even d ≥ 2 (ADR-0161 decision 11), so refusing would decide sub-question ① for this kind alone; the computed facts of ADR-0161 decision 13 then do not carry (Limit 3).
- The table has P + m positions, so P + m rows always exist; P and `d` are refused before a process is started where the builder refuses (P + m)·d above 2^53 − 1.

### 5. The table on the Python side

- **`hilclaw.rope_table.build` is the source**, called with the constants of decision 4 and `positions` = P + m, once per run; rows P … P+m−1 are the rows sent and the rows the reference uses. Whether a code task caches the table across runs is its own choice (it is a function of d and P + m only).
- **Cost** (computed with Python 3.14.4, NumPy 2.5.2, Windows 11 on Intel Family 6 Model 183): 0.107 s for 128 positions and 1.91 s for 2048 positions at d = 64, with a traced peak of 589,020 bytes; the result is 524,288 bytes. A run at P = 2047, m = 1 builds the same 2048 positions, since the builder has no start position.

### 6. The drawn `x`

- **As ADR-0163 decision 4**, with b = 8 over `rope_bf16_contract.X_PATTERNS`: each element takes one word of the shared generator, its top 8 bits index the set, and the elements of a draw are indexed in one sequence, `x` in its memory order (element (i, j, k) at (i·h + j)·d + k, ADR-0161 decision 6). There is no second drawn operand; **the table is not drawn**, and no element of `x` is derived from the table or from another element.
- Seed and `draws`: as ADR-0163 decision 4 (parameters of the run with no default; their source and number stay OD-16 sub-question ⑤).

### 7. Command line

| Kind | Arguments, in this order |
|---|---|
| `rope` | `<m> <h> <d> <draws> <seed>` |

- The dimensions in the prototype's order (ADR-0161 decision 9), then `draws` and the seed, with the spelling and checks of ADR-0163 decision 3; `d` must also be even (ADR-0161 decision 11), and an odd `d` is refused by both sides. Decisions 3 and 4 add nothing to it: the rows come on standard input and P stays on the Python side.

### 8. The output before the call

- **As ADR-0163 decision 5**: every element of `out` is set to `0x7FC0` before each call. ADR-0161 decision 11 ("Output") leaves its content on entry unspecified and forbids reading it before writing it, so no obligation is added; an element left unwritten, as by a wrong head count (ADR-0161 decision 13), fails as non-finite on every draw.

### 9. The reference and the input check

- **Widening**: `x` as ADR-0163 decision 6; the binary32 entries of the Python side's rows widen to float64 exactly.
- **Reference** (**owner**, HQ-0066 (1), through ADR-0154 decision 3; operation of ADR-0161 decision 7), in NumPy float64 on the widened arrays, the row of token i broadcast over the heads: **y₀ = x₀·c − x₁·s, y₁ = x₀·s + x₁·c**, c = row(i, 2p), s = row(i, 2p + 1). The products are exact and the sum has one rounding, a relative error of at most 2^−53 (ADR-0161 decision 13).
- **Input check value**, as ADR-0163 decision 6, over **`x` then the m rows as passed to the kernel**: before each call, the CRC-32 of the 2·m·h·d bytes of `x` followed by the 4·m·d bytes of the kernel's `freqs_cis` array, in memory order. The Python side computes it over its regenerated `x` and its own rows; a disagreement makes the run **broken**, never a fail. The rows are covered because decision 3 adds a channel the other kinds lack: a transfer or copy that differs is a harness defect, which must not show as a wrong kernel.

### 10. The comparison, the report and the verdict

- **As ADR-0163 decisions 7 and 8**, with `out` of m·h·d elements: element-wise `rtol` and `atol` (**owner**, HQ-0066 (2)), never passed to the program; a report of the check value and the output per draw and an end mark, **draws · (4 + 2·m·h·d) + E bytes**; completed, broken, pass and fail as ADR-0017 decision 7.
- **For whoever sets a tolerance** (no value, no default): besides the 2^−8 of ADR-0163 decision 7, y may cancel — a compliant output differs from y by more than a relative 2^−8 on 0.0039 % of the cases and by up to a relative 457 at the smallest outputs, exact outputs reaching down to 2^−31 (ADR-0161 decision 13) — so an `rtol` with `atol` = 0 can fail a conforming kernel. Every compliant output is within an absolute 2^−8 + 2^−21 of y: the bound of ADR-0161 decision 7 is below 2^−22 · 2, and |v| < 2 keeps half a bf16 unit in the last place at most 2^−8 (a binary32 evaluation with round-to-nearest-even output reached 0.0039064 against 0.0039067 on rows 0, 7, 14, … and 2047; computed).

### 11. Calibration

- **ADR-0003 holds for this kind** as ADR-0163 decision 9 applies it: three hand-written C kernels — conforming, violating (V1, right on the functional test's seed, shape and P, wrong elsewhere) and failing — added with the change that makes the harness verify `rope` (ADR-0003 decision 6 (a)); the tests pass their own `rtol`, `atol`, seed, `draws` and P.
- **Failing: cos and sin swapped** (y₀ = x₀·s − x₁·c, y₁ = x₀·c + x₁·s), which moves the result by a relative 2^−6 or more on 95.6 % of the cases, the most of ADR-0161 decision 13's list. **Why it is outside**: the functional test uses **P = 0**, so row 0 (c = 1, s = +0 exactly) is among the rows. There the conforming output is x itself, exactly, and the swapped kernel gives (−x₁, x₀), so of every pair one element is off by |x₀| + |x₁| ≥ 1 while |ref| < 1 (computed: the least such difference over the set is 1.0). It is therefore outside under every tolerance with atol + rtol < 1, and the conforming kernel passes under every tolerance with atol ≥ 2^−8 + 2^−21 (decision 10), so the two ranges meet. The flipped sine (73.1 %) is not chosen: at row 0 it changes nothing.
- **No test may require these to fail**: a table rounded to bf16 in the kernel (18.5 % of cases non-compliant, 2.1 % by a relative 2^−6 or more) and truncation in place of round-to-nearest-even (49.9 %, a relative error up to 0.00775), both detected only under a tight enough tolerance (ADR-0161 decision 13); fused against unfused multiply-adds, any association and a wider evaluation, all compliant (ADR-0161 decision 7), so no test separates them; the sign of a zero output (ADR-0161 decision 8); an input written by the kernel, against ADR-0161 decision 11 but not observed, since every draw sets `x` and the rows anew; and errors of the table builder or the binding — a wrong `rope_theta`, scaling or position, Q and K swapped — which the kernel does not compute (ADR-0161 decision 13), tested in their own code.

### 12. Parameters

| Value | Given by | Source |
|---|---|---|
| `m`, `h`, `d` | the caller | each ≥ 1, `d` even (ADR-0161 decision 11); other shapes: OD-16 sub-question ① |
| Start position P | the caller, no default, held by the Python side | decision 4; its values for the op_signature shapes: ADR-0161 decision 13; both T = 1 rows or one: sub-question ⑤ |
| Seed, `draws` | the caller, no default | as ADR-0163 decision 10; sub-question ⑤ |
| `rtol`, `atol` | the caller, from the instance, no default | **owner**, HQ-0066 (2) |
| Time limit, flags, trailing flags, compiler, build time limit, path, environment, working directory | the caller | as ADR-0163 decision 10 |
| Table constants θ = 500000, s = 8, a = 1, b = 4, L = 8192; `x` by the b = 8 mapping; output fill `0x7FC0`; rows on standard input; one call per draw | constants of the mechanism | ADR-0161 decision 13 for the constants; the rest this record's own |

### 13. Limits

1. **As ADR-0163 decision 11, items 1 and 5**: the kernel shares its process with the program, a pass says the output is right and not how, nothing is sandboxed (OD-14, OD-8, threat A of OD-16); one machine, so the rows and the report travel in host byte order.
2. **What the set cannot detect** is decision 11's list; no zero, subnormal or non-finite `x` is drawn (#5 B-7, OD-16).
3. **The computed facts of ADR-0161 decision 13 hold for d = 64 and P + m ≤ 2048**; a run outside is a valid run whose cancellation and detection shares were not computed.
4. **Cost at the largest shape** (m = 2048, h = 32, d = 64; computed): standard input 524,288 bytes; a report of 8,388,612 bytes per draw (4,194,304 elements), all held by the runner at once; the table 1.91 s once per run (decision 5); `x` of 4,194,304 elements per draw, under 202 MB at the existing array code's peak of under 48 bytes per drawn element (`bf16_verification_arrays.py`). The table's cost grows with P + m, not with m (decision 5), and lies outside the process's time limit, as all Python-side work does. **The Python side is bounded by nothing here** (OD-14).

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 3 | Rows on the command line | 1,426,466 bytes over 131,072 arguments at the largest shape, past Windows' limit and near Linux's. |
| 3 | A file the harness writes | Path, writer rule and clean-up (ADR-0017 Alternatives); input values kept out of files (OD-16 principle). |
| 3 | A generated C source of the rows in the build | A source added to the caller's build, 1.4 MB of initialiser per build, an executable tied to one P and m. |
| 3 | Entries computed in the program | Floating-point arithmetic in the program (ADR-0163 decision 2); correctly rounded entries need the builder's method. |
| 3 | The whole table sent, the program slicing by P | More bytes and P in the program for nothing; the rows alone suffice. |
| 4 | P drawn from the seed and the draw | Both rows sent, a choice in the program; a single value at m ∈ {128, 2048} and no set at any m outside {1, 128, 2048}. |
| 4 | P fixed (0, or 2047 for m = 1) | Drops one of ADR-0161 decision 13's two T = 1 rows from every verification. |
| 4 | Refuse d ≠ 64 | Decides OD-16 sub-question ① for one kind; the rule and the contract hold for every even d. |
| 9 | Check value over `x` only | A transfer or copy of the rows that differs would show as a failing kernel. |
| 11 | Flipped sine as the failing kernel | Identical to the conforming output at row 0; detected on 73.1 % of cases only. |
| 11 | Truncation or a bf16 table as the failing kernel | Compliant under the tolerances a conforming kernel passes, or detected only under a tight one (ADR-0161 decision 13). |

## Consequences

- **A-13 reading**: document mode; no code, dependency, settings file or schema file changes. NumPy and the standard library suffice.
- **Code slices this record makes possible** (for the planner; each within 300 LOC and 5 files excluding tests): (1) an optional standard-input argument of `local_run.run`, written while the output is drained and closed, a broken pipe from a process that exits early being its result, not an exception; (2) the program `bf16_verification_rope.c` and `rope` in `bf16_verification_build.PROGRAM_SOURCES`; (3) the Python side — the draw of `x`, the table rows from `rope_table.build`, the check value over `x` and the rows, the reference, judging the report with P and the bytes on standard input; (4) the three calibration kernels with their tests. A test that needs clang shows that the two generators agree. **Registering `rope` with `correctness.check`, `spec.write` or the instance start is not one of them** (Boundaries).
- **Runtime acceptance items**: none. Nothing here needs a live `claude`, a board or a model file.
- **Readings for the owner to check**, listed in the #5 notice: the rows handed over on standard input, a departure from ADR-0017 decision 9 for `rope` only (decision 3); P a run parameter, with both T = 1 rows or one left to the caller (decision 4); the table built for any `d` with ADR-0161's constants (decision 4); the input check covering the rows (decision 9); cos and sin swapped as the failing kernel, with P = 0 in the functional test (decision 11).
- **Later work**: the harness record of SDPA with KV cache, and the record of the bf16 timing run.
- **Less exact, not edited** (search of `ARCHITECTURE/` for "Left to P2-12", "The harness mechanism", "second harness record", "sentinel" and "standard input"; not claimed complete):
  - now answered for verification: ADR-0161 decision 13 ("Left to P2-12" and "depends on the harness's sentinel (P2-12)") and its Boundaries ("The harness mechanism and the parts of decision 13 left to it"; the timing part stays open); ADR-0163 decision 1 ("RoPE and SDPA, left to a second harness record", with "which T = 1 row a draw uses is open"), its Consequences ("the second harness record (RoPE and SDPA …)", and "still true: ADR-0161 decision 13, ADR-0162 decision 13 and their Boundaries (the second harness record)" for its ADR-0161 part) and Boundaries ("RoPE and SDPA verification (a second harness record …)") — RoPE now has this record, SDPA does not;
  - less exact once code slice 1 lands: ADR-0009 Context ("runs one process … with no standard input") and ADR-0017 Alternatives ("`local_run` gives a process no standard input"), facts of the code they read;
  - still true: ADR-0017 decision 9 for the first case and ADR-0163's four kinds; ADR-0162 decision 13 and its Boundaries.
- **UsageCases and StandardScenarios** (S0, S1, S7 and S8 re-checked, and the rows citing OD-31 sub-question 3 or OD-16: S0 steps 5 and 6, S1 step 2, S7 steps 2 and 3, S8 step 3): no use case step changes; their open parts — shapes and draws (OD-16 ① and ⑤), the build relation (⑥) and the vocabulary outside the first case and the Llama kinds (#5 B-7, OD-31 ③) — stay. Verdicts unchanged, no gap.

## Boundaries (not decided here)

- **Tolerance values** (FR-9; **owner**, HQ-0066 (2), no default).
- **Seeds, draws and positions**: the seed's source, the number of draws and whether an m = 1 check runs both T = 1 rows (OD-16 sub-question ⑤).
- **Other shapes** (OD-16 sub-question ①); **corner-case, non-finite and subnormal inputs** (#5 B-7, OD-16 threat B ⑵).
- **The model's scale factor** (HQ-0070; OD-31 sub-questions 5 and 6, owner) and the model-level comparison.
- **SDPA with KV cache verification** (a later harness record) and **the bf16 timing run**, with ADR-0107's rule (OD-16 sub-question ⑥).
- **Build settings and OpenMP** (HQ-0033; ADR-0116); **isolation of the run** (OD-14).
- **How a check or an instance reaches these runs**: `correctness.check`, `spec.write` and the instance start for `rope` (OD-18, OD-6).
- **fp16** (owner, HQ-0065 (1)); **backends other than `cpu_standin`** (#5 B-2, B-7); **any change to ADR-0017, ADR-0161, ADR-0163** or another accepted record.

## References

- Owner: HQ-0065 and HQ-0066 in `PROCESS/STATE.json` (through ADR-0154); HQ-0004 answer https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6052377983 (through ADR-0017); #5 B-4 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285; D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506.
- [Requirements](../Requirements.md): FR-9, C-6; register rows OD-14, OD-16, OD-31. [OpenDecisionProposals](../OpenDecisionProposals.md) § OD-16 (sub-questions ①, ②, ⑤, ⑥) and § OD-31 (sub-question ③); [StandardScenarios](../StandardScenarios.md) S0, S1, S7, S8.
- Records: ADR-0001 (record format), ADR-0003, ADR-0009 (Context), ADR-0017, ADR-0107, ADR-0154, ADR-0161, ADR-0162 (decision 13), ADR-0163.
- Code read at `4528948`: `hilclaw/rope_table.py`, `hilclaw/rope_bf16_contract.py`, `hilclaw/local_run.py`, `hilclaw/harness/bf16_verification.h`, `bf16_verification_rmsnorm.c`, `bf16_verification_arrays.py`, `bf16_verification.py`, `bf16_verification_build.py`.
- Process: [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §8, §9, D16; [PROCESS/PLAN.md](../../PROCESS/PLAN.md) P2-11, P2-12, P2-14.
