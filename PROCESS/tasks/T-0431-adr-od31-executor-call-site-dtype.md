---
id: T-0431
title: Write ADR-0157 - how the model executor learns the dtype of its GEMM call sites, and what that dtype selects (the contract a fit is checked against, the "every shape" acceptance, the entry point and element type of the call) for fp32 and bf16 `gemm` (part of OD-31 sub-question 4)
phase: P1
status: DONE
commitMode: doc
coversReq: [C-6, FR-10, OD-31, "PLAN P2-13", "PLAN P2-14"]
dependsOn: [T-0430]
touchesFiles: [ARCHITECTURE/decisions/ADR-0157-od31-executor-call-site-dtype.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 200, files: 4}
hq: []
---
## Why

**Where things stand** (as of `main` `9b7e33c`):
- ADR-0156 (T-0429) defines the bf16 `gemm` contract on `cpu_standin`: symbol `hilclaw_gemm_bf16`, operands `uint16_t` bit patterns, dtype `bf16`. T-0430 (PR #252) added `hilclaw/gemm_bf16_contract.py` with its values. Nothing uses it yet.
- ADR-0156 Consequences name the next code step: the use of that contract "by `hilclaw/model_binding.py` (fit and the 'every shape' binding) and by the model program, which calls `hilclaw_gemm_bf16` over `uint16_t` buffers".
- The model executor's code (ADR-0153 code slice 1: `hilclaw/model_binding.py`, `model_build.py`, `model_run.py`, `model_execute.py`, `model_gemm.py`, `model_program.c`) knows fp32 `gemm` only. `model_binding._unfit` compares every entry with the fp32 contract, and `model_program.c` calls `hilclaw_gemm` over `float` arrays.

**The gap this task closes.** ADR-0153 decision 3 says a kernel fits a call site when its `task.contract` is "the contract of the call site's kind, dtype, layout and language". It does not say **where a call site's dtype comes from**. The host-side inputs of decision 3 are (a) model parameters, (b) weights "already in the dtype and layout of the operand that receives it", (c) the binding and (d) run settings. None of them names a dtype the binding check can read before anything is built. The owner fixed the dtype of the Llama goal as bf16 and kept the first case at fp32 (ADR-0154 decision 2). The executor's landed slice is fp32. So the executor needs a rule for which dtype each call site has.

The T-0430 Follow-ups asked the planner to return this as a design question rather than invent it in code. It is part of OD-31 sub-question 4 (the model executor), which OpenDecisionProposals § OD-31 assigns to the driver. So under DRIVER §9 the task is a driver ADR, accepted by the reviewer and noticed to the owner. It is not an owner-only decision: no #5 A/B item, C-6, OD-25 or OD-3 value is chosen. The owner's answers (bf16 for the Llama goal, fp32 for the first case, casts left to sub-question 2) are cited, not changed.

**D18.** This comes from a follow-up, so the priority rule applies. It is needed for P2-14 (and P2-13): the executor cannot bind or call a bf16 kernel until it knows a call site is bf16. It is not wording, hardening or a refactor, so it is not set aside. The PLAN P2 order holds: the round-loop items and P2-5 still wait on unresolved HQs (HQ-0021, HQ-0031, HQ-0048; the P2-4 gate is owner-only OD-3), and P2-10 follows P2-5. So the work continues with P2-11 to P2-14.

**D16.** Nothing here starts `claude`, needs a board, a model file or an API key. The ADR should add no runtime acceptance item unless its decision creates a fact only a live run can show; if it does, it lists the item for the driver's HQ, as ADR-0153 did.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (executor procedure, resume rule, time limit; line 72);
  - §5 (task format; naming: branch `claude/T-0431-<slug>`, commit trailer `Task: T-0431`; size cap; lines 86-114);
  - §9 (OD closure: driver ADR, reviewer Approve, #5 notice with the driver tail of §8, 7-day objection window; lines 144-151) and §8 line 141 (the `— posted by driver` tail).
- `CLAUDE.md`: "상시 규칙", especially "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검" and "브랜치·merge 절차" (document mode).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` "Record format" (from line 146): location, name, section order, one closure per record.
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`:
  - decision 3 (inputs, binding, fit, loading, the call; lines 40-46);
  - decision 4 "Copies a contract leaves" (the sentence on casts) and "Buffers" (lines 50-51);
  - decision 5 (outcomes; lines 58-62);
  - Consequences, code slices (line 88) and Boundaries (lines 101-116), especially "Dtype, accumulation precision and the casts between kernels" and "the form in which the host side hands the program its inputs (code slices)".
- `ARCHITECTURE/decisions/ADR-0154-od31-owner-answers-heads-bf16-oracle.md` decision 2 (lines 45-52): the owner's precision answer, quoted.
- `ARCHITECTURE/decisions/ADR-0156-od31-bf16-gemm-contract.md`:
  - decision 1 (scope; lines 32-35);
  - decision 2 (dtype and layout, the weights' order; lines 37-41);
  - decision 5 (prototype and symbol, with the "wrong binding fails at loading" reason; lines 59-72);
  - decision 7, "Every set of dimensions" (line 110);
  - Consequences, code slice (lines 173-177).
- `ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md` decisions 1, 4 and 6 (the fp32 contract, its entry point and "for the values it is called with").
- `hilclaw/model_binding.py`: the module docstring (lines 1-47), `check` (lines 199-290) and `_unfit` (lines 323-346). Read only.
- `hilclaw/model_program.c` header comment (lines 1-60) and `hilclaw/model_run.py` lines 1-20 and 85-110: what the landed program and its input encoding assume (`float` elements, `hilclaw_gemm`). Read only.
- `hilclaw/gemm_bf16_contract.py` (module docstring and `task_contract`). Read only.
- `ARCHITECTURE/Requirements.md` line 84 (the register's "행 형식") and line 122 (the OD-31 row).
- `ARCHITECTURE/OpenDecisionProposals.md` line 8 ("기록 규칙") and § OD-31 (from line 524), sub-question ④.
- `ARCHITECTURE/StandardScenarios.md` § 검사 결과, its first paragraph (lines 168-172), and the S0 and S1 rows of its verdict table.

## Acceptance Criteria

1. **New record `ARCHITECTURE/decisions/ADR-0157-od31-executor-call-site-dtype.md`** (English; ADR-0001 "Record format"; the slug may be adjusted if the number is kept). Before writing, confirm that no `ADR-0157` exists on `main` or in an open PR. If one does, take the next free number and use it everywhere this task says 0157.
2. **Status** names, as ADR-0156 does:
   - what is cited (owner answers through ADR-0154; ADR-0008, ADR-0153, ADR-0156) and what is the record's own (accepted under DRIVER §9);
   - the open HQs checked in `PROCESS/STATE.json` and how none is crossed — at least HQ-0069 (ADR-0153 runtime acceptance item (lxvii)), HQ-0033 and HQ-0034 if they bear on the decision;
   - a search for owner sentences on the subject (#4, #5 without driver-tail comments, #7, #8; terms such as dtype, bf16, fp32, 실행기, executor, mixed, 혼합, cast). Quote what is found, or say nothing was found;
   - "Not changed": no data-plane schema, member, file, version or validator; no code.
3. **Decision**, at least these points, each with its reasons:
   - **The source of a call site's dtype.** How the host side knows, before anything is built, the dtype of each GEMM call site of a generation. Weigh at least:
     - (a) one dtype for the whole generation, given as an input of the host side (a model parameter or a run setting);
     - (b) a dtype per call site, given with the binding or the model parameters;
     - (c) the dtype read from the bound kernel's own `task.contract`.
     
     Check each against ADR-0153 decision 3 ("the executor never chooses a kernel itself"; fit compared with "the contract of the call site's … dtype") and decision 5 (all checks before anything is built). Option (c) would make the dtype part of the fit check vacuous; say how the choice avoids that.
   - **Mixed dtypes in one generation.** Whether call sites of different dtypes may meet in one generation. Casts between kernels are left to sub-question 2 (ADR-0153 decision 4; owner). So the record must not decide a cast. If it allows mixing, it must say what stops a generation that would need a cast. If it forbids mixing, it must say which outcome refuses such an input (an existing outcome of decision 5, e.g. `invalid_input` or `kernel_unfit`, or why a new one is needed).
   - **What the dtype selects** for `gemm`, for each of `fp32` and `bf16`:
     - the contract a fit is checked against (ADR-0008 for fp32, ADR-0156 for bf16), compared as ADR-0153 decision 3 says;
     - whether a binding "for every shape" and a listed shape other than the spec's own are accepted (ADR-0008 decision 6; ADR-0156 decision 7);
     - the entry point the model program finds with `dlsym` and the element type of the buffers it passes (`hilclaw_gemm` over `float`; `hilclaw_gemm_bf16` over `uint16_t` bit patterns).
   - **A dtype the executor knows no contract for** (for example `fp16`, or a kind other than `gemm` at this dtype). Which outcome of ADR-0153 decision 5 it gives. fp16 itself stays after P2-14 (owner, HQ-0065 (1)); the record must not define an fp16 contract.
   - **The fp32 path stays.** The landed slice 1 (fp32 `gemm`) remains valid, or the record says exactly what of it changes. The first case (ADR-0008, PLAN P1-5) is unchanged.
4. **What the record must not decide** (list in Boundaries):
   - casts and intermediate precisions (sub-question 2, owner);
   - the weights' source, file form, conversion to bf16 or order on reading a model file (sub-question 5, owner);
   - tolerance values, the reference and the model-level comparison (sub-questions 3 and 6);
   - the binary form in which the host side hands inputs to the model program and reads its report (ADR-0153 leaves it to code slices). The record may name the element type but not the file layout;
   - the contracts of the other five kinds and their dtypes;
   - targets other than `cpu_standin`;
   - deriving a binding from a key's best (OD-20, OD-7).
5. **Alternatives considered**: a table with the options of criterion 3 that were not taken and why.
6. **Consequences**:
   - A-13 reading (no data-plane change).
   - The code slices it makes possible, for the planner, each small enough for one task. At least: the dtype in `hilclaw/model_binding.py`'s check with the bf16 fit; the model program and its host-side build and run steps over `uint16_t` buffers with hand-written bf16 kernel fixtures.
   - "Less exact, not edited" records found by a search of `ARCHITECTURE/`, for example ADR-0153 decision 3's "for other kinds, through the prototypes of their future contract records". Accepted records are not edited.
   - Runtime acceptance items: none, or each listed with its number after ADR-0153's (lxviii).
   - Readings for the owner to check, listed in the #5 notice.
   - UsageCases and StandardScenarios: S0 and S1 re-checked.
7. **`ARCHITECTURE/OpenDecisionProposals.md` § OD-31**: follow that file's "기록 규칙" (line 8). The executor reads the rule and applies it; this task does not restate the rule's wording.
8. **`ARCHITECTURE/Requirements.md` OD-31 row** (line 122): follow the register's "행 형식" (line 84). The status cell changes only if the rule requires it.
9. **`ARCHITECTURE/StandardScenarios.md` § 검사 결과**: re-check S0 and S1 (CLAUDE.md "문서 커버리지 재검사") and record the result as the first paragraph of that section says. A verdict-change history entry is added only if a verdict or gap changes.
10. **No other file changes.** Do not edit:
    - any accepted ADR (ADR-0008, ADR-0153, ADR-0154, ADR-0156 included);
    - `ARCHITECTURE/UsageCases.md`;
    - any `hilclaw/` or `tests/` file;
    - any `PROCESS/` file other than this task's `## Result`.
11. **Process**: document mode (CLAUDE.md A-13).
    - Branch `claude/T-0431-<slug>`; context-isolated reviewer cycle (dev-code-review) to Approve; rebase on `origin/main`; push to `main` directly with the trailer `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0431`.
    - After landing, post the DRIVER §9 owner notice as a #5 comment. It names the ADR, its commit, what it decides, the readings for the owner to check and the 7-day objection window, and its last line is `— posted by driver`. Record the comment URL in `## Result`.
    - The reviewer checks at least:
      - that no owner-only point (casts, fp16, weights, tolerance, the model-level comparison) is decided;
      - that the chosen dtype source keeps the fit check meaningful and refuses before anything is built;
      - that every cited sentence matches its source;
      - that the OpenDecisionProposals, Requirements and StandardScenarios edits follow their files' own recording rules (no restatement of the ADR, no dated paragraphs, one link per new ADR, open parts rewritten in place).

## Out of Scope

- Any code: the dtype in `hilclaw/model_binding.py`, the bf16 model program, `model_run.py` encoding of `uint16_t`, bf16 kernel fixtures. These are later tasks the ADR's Consequences list.
- The P2-12 bf16 harness record (generator, seed, draws, widening, comparison).
- The contracts of RMSNorm, elementwise add, SwiGLU activation, RoPE and SDPA.
- fp16; targets other than `cpu_standin`.
- The PLAN "보류" items, including the two T-0429 wording follow-ups.

## Follow-ups

- (planner) After this ADR lands: the code slice it lists first (the call-site dtype and the bf16 fit in `hilclaw/model_binding.py`, with tests), then the model program over `uint16_t` with hand-written bf16 kernel fixtures, split to the size cap.

## Result

- **Outcome**: DONE. Document mode; landed on `main` as `4fef3b8` (squashed, rebased on `821d4bf`, trailers `Task: T-0431` and `Reviewed-by: reviewer agent (7 rounds, Approve)`). Branch `claude/T-0431-executor-call-site-dtype` deleted (remote and local).
- **Files**: new `ARCHITECTURE/decisions/ADR-0157-od31-executor-call-site-dtype.md` (no other ADR-0157 existed on `main` or in an open PR); `ARCHITECTURE/OpenDecisionProposals.md` § OD-31 (one 채택분 line, sub-question ④ "→ 부분 답" rewritten in place); `ARCHITECTURE/Requirements.md` OD-31 row (one link in `**확정분**`, status cell unchanged); `ARCHITECTURE/StandardScenarios.md` "최근 재검사" line (S0, S1 re-checked, verdicts unchanged, no gap, no history entry).
- **Decision in short**: the dtype is one model parameter per generation, no default; no mixed dtypes (a kernel of another dtype's contract is kernel unfit); for `gemm` it selects the contract (ADR-0008 / ADR-0156), "every shape" acceptance (both), the `dlsym` entry point (`hilclaw_gemm` / `hilclaw_gemm_bf16`) and the buffer element type (`float` / `uint16_t`); a dtype with no contract at every call site's kind (fp16 among them) or a weight of the wrong element type is invalid input; the fp32 path of ADR-0153 slice 1 stays, its binding check gains the dtype input. No owner-only point decided; no runtime acceptance item; no data-plane change.
- **Review**: 7 rounds (dev-reviewer, fresh context each). Round 1 and 2 Request changes (blocking: weights' element type stated per model dtype instead of per receiving operand, crossing sub-question 2; embedding table placed under kind contracts); rounds 3-7 Approve with nits, all addressed through round 6. Round 7 Approve left two nits unaddressed because an 8th round is not allowed (below).
- **#5 notice (DRIVER §9)**: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6377336741 (7-day objection window from 2026-10-24).
- **Follow-ups**:
  - (planner) The code slices of ADR-0157 Consequences: (1) the model's dtype and the bf16 fit in `hilclaw/model_binding.py` (contract selected by dtype, kernel unfit for another dtype, invalid input for a dtype out of range, fp32 callers pass `fp32`), with tests; (2) the bf16 model program and its host-side build and run steps over `uint16_t` buffers with hand-written bf16 kernel fixtures, split to the size cap. The weights' element-type check goes with ADR-0153 code slice 2.
  - (wording, D18 candidate for 보류) Round-7 nits left open: ADR-0157 Status "It builds on" and References list ADR-0008 decision 1, ADR-0156 decision 1 and ADR-0152 decision 5 without a numbered citation in the body; decision 4 Reasons "a binding that is right for the dtype" could read "every bound entry, whatever its kernel" as in the Alternatives row.
  - (driver note) ADR-0157 decision 1 states that the host side holds bf16 GEMM weights as 16-bit patterns and does no arithmetic on them, which overlaps the first point of the PLAN 보류 line "T-0418 follow-up" (ADR-0153 decision 2 wording); that line was not edited.
