---
id: T-0418
title: Write ADR-0153 - the model executor of the Llama 3.2 1B end-to-end goal (place, language, how it binds and calls per-op kernels, work outside the kernels), with dtype, oracle, head count and the owner-only parts left open (OD-31 sub-question 4, for PLAN P2-13)
phase: P1
status: DONE
commitMode: doc
coversReq: [C-6, FR-9, FR-10, FR-13, OD-31, "PLAN P2-13"]
dependsOn: [T-0417]
touchesFiles: [ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 260, files: 4}
hq: []
---
## Why

**Where things stand** (as of `main` `2fe6952`):
- PLAN P2-5 cannot move: each remaining part waits on an open owner HQ (HQ-0048, HQ-0053, HQ-0021, HQ-0026, HQ-0032). PLAN P2-10 comes after P2-5.
- PLAN P2-11 (per-kind contracts) and P2-12 (bf16/fp16 harness) wait on owner answers. OD-31 sub-question 2 (dtype, accumulation precision) and sub-question 3 (oracle, tolerance) are being asked as owner HQs in this iteration. They are attached to T-0417 and are non-blocking for this task. The RoPE/SDPA shapes also wait on HQ-0064 (query-head count).
- ADR-0152 (T-0417, `73ca12a`) answered part of OD-31 sub-question 1. Several items are left to **sub-question 4, the model executor**:
  - the embedding lookup and leftover copies (decision 3);
  - which rows lm_head gets (decision 4);
  - which kernel is called for a shape no instance ran, and what happens when none fits (decision 7).
- OpenDecisionProposals § OD-31 assigns sub-question 4 to the driver, through the DRIVER §9 ADR path. A new external dependency would go to A-13.

**This task** writes the record for sub-question 4 (PLAN P2-13: "하위 질문 ④는 OD-31 종결 필요(§9 ADR 경로)"). P2-13 is a PLAN checklist item, so the D18 hold rule does not apply (DRIVER §6). It is on the path to the reach goal P2-14. It is taken now because it is the only part of P2-11 to P2-14 that waits on no owner answer.

**What makes it writable now.** The executor's own design is the driver's to decide. Every value that depends on an owner answer stays a named parameter or a Boundaries line:
- dtype and casts;
- the oracle;
- the head count;
- weights and tokenizer;
- model-level accuracy;
- dependencies;
- the artifact.

If the executor finds that some decision cannot be written without one of them, it records that decision as open (Boundaries) and does not decide it. If **no** meaningful part of sub-question 4 can be decided that way, the task stops BLOCKED (reason "Requirements OD 확정이 필요한 설계 선택", DRIVER §3) with an owner question in Result.

**No open PR overlaps.** Open PR #186 (T-0324, BLOCKED by HQ-0032) touches:
- `hilclaw/start_instance.py`;
- `tests/test_gemm_contract.py`;
- `tests/test_standin_profile.py`;
- `tests/test_start_instance.py`.

**D16.** This task writes a record only. It downloads no model file, needs no gated licence, starts no `claude` and needs no board or API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (executor procedure, resume rule, time limit, line 72);
  - §5 (task format, naming: branch `claude/T-0418-<slug>`, trailer `Task: T-0418`, lines 86-114);
  - §8 (HQ question form, lines 136-142);
  - §9 (OD closure by ADR, 7-day notice on #5 with the `— posted by driver` footer, lines 144-152).
- `CLAUDE.md`, the sections below. They are short; read all of them:
  - "상시 규칙": the three-layer model, the tool-layer language policy {Python, POSIX sh, C}, "미결은 발명하지 않는다", "개발 드라이버와 런타임의 구분", document mode of A-13;
  - "현재 프로젝트 상태 주의사항": no binaries in git.
- `ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md`, whole file (167 lines). This is the operation list, instance targets, shape sets and parameters H, d_h that this record builds on. Decisions 3, 4 and 7 and the Boundaries line "The model executor" name what is handed to this record.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`:
  - "Record format" (lines 146-160): sections and naming of an ADR;
  - decision 2: op_signature as part of the key.
- `ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md`:
  - decisions 1 (another kind/dtype has its own contract), 4 (the C prototype), 5 (operand entries) and 6 (obligations at a call);
  - its Boundaries.
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`, lines 50-115. This covers `db/<hw_profile_key>/<op_signature>/best.json`, whose content is OD-20/OD-7, written by the promotion step.
- `ARCHITECTURE/decisions/ADR-0005-od8-artifacts-record.md`: the CAS record and `retention_class` (lines 1-70 and Boundaries).
- `ARCHITECTURE/decisions/ADR-0016-od18-backend-frame.md`: Decision and Boundaries (what a backend of an FR-10 tool is).
- `ARCHITECTURE/Requirements.md`:
  - C-6 (line 63);
  - FR-5, FR-9, FR-10, FR-13 (lines 23-31);
  - the **"행 형식" paragraph (line 84)**;
  - OD-9 (line 100), OD-20 (line 111), OD-31 (line 122).
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - the header's **"기록 규칙" (line 8)**;
  - § OD-31 (from line 520, about 15 lines).
- `ARCHITECTURE/StandardScenarios.md`:
  - S0 (lines 30-44, step 4 especially);
  - **the first paragraph of § 검사 결과 (line 170)** and the "최근 재검사" line (line 172).
- `PROCESS/PLAN.md` P2-11 to P2-15 (lines 47-51).
- `PROCESS/STATE.json` `humanQuestions`: HQ-0064 and the two OD-31 ②/③ HQs recorded in this iteration (HQ-0065, HQ-0066), plus the other unresolved ones. Check that the record crosses none of them.
- The existing layer-2 code is background only and is not to be edited: `hilclaw/` modules for `cpu_standin` building and running (the clang build wrapper and the local run). Read them only as far as needed to weigh how C kernels are built and called on `cpu_standin`.

## Acceptance Criteria

1. **New record** `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`, in English, in the ADR-0001 "Record format":
   - sections Status, Context, Decision, Alternatives considered, Consequences, Boundaries, References;
   - one closure: part of OD-31 sub-question 4.
   - Status says it is accepted under DRIVER §9, not confirmed by the owner, with a 7-day objection window.
   - It separates **cited** content (with a named source) from **this record's own** content, as ADR-0152 does.
   - Status includes an owner-sentence search, as ADR-0152's does: issues #4, #5, #7, #8, for terms like executor, forward pass, end-to-end, whole-model, weights, tokenizer, lm_head, logits. It lists what was found, or says nothing was found.
2. **The decisions it makes** cover OD-31 sub-question 4. For each item it either decides it or states why it is open:
   - (a) **Place**: what the executor is. Weigh at least two alternatives in Alternatives considered:
     - a layer-2 module or entry point of `hilclaw/`;
     - a registry/MCP tool;
     - a generated C host program;
     - something outside layer 2.
     
     Also weigh its relation to the FR-10 tools and the backend frame of ADR-0016, and which backend(s) it targets first (`cpu_standin`).
   - (b) **Language** from CLAUDE.md's {Python, POSIX sh, C}, with the reason. It must need **no new external dependency**. `numpy` is already pinned (`pyproject.toml`). If no viable choice avoids a new dependency, the record says so and leaves the choice open for OD-31 sub-question 7 (owner).
   - (c) **How it binds and calls kernels**:
     - what it takes as the kernel of each (operation, shape) — e.g. an explicit binding of instance key → CAS artifact;
     - how it calls a C kernel through the contract's prototype (ADR-0008 decision 4 for `gemm`; for other kinds, through their future contract records, named only as such).
     
     **How the binding is derived from a run's or a key's "best"** depends on `best.json` (OD-20/OD-7, ADR-0004). It is either decided only as far as existing records allow, or left open with that OD named.
   - (d) **Work outside the kernels**, as ADR-0152 decision 3 hands it over:
     - the embedding lookup (row copy);
     - copies a contract leaves;
     - the KV-cache buffers' ownership and lifetime across layers and decode steps (capacity stays the SDPA contract's);
     - the order of calls of one forward pass and of a generation loop.
   - (e) **Operations or shapes with no fitting kernel** (ADR-0152 decision 7): what the executor does. It fails with a named outcome, or uses a fallback. If a fallback is chosen, its numerics depend on sub-questions 2 and 3, and the record must leave them as parameters.
   - (f) **Driver-side verification** (PLAN P2-13, D16): the executor is verified with small synthetic weights and a synthetic tokenizer generated by tests. The record says what "small synthetic model" means:
     - the same architecture as ADR-0152 with reduced dimensions as parameters;
     - no real Llama file.
     
     It must not fix a weight **file** format.
3. **Kept as parameters or Boundaries, not decided** (each named in Boundaries with its owner or OD):
   - dtype, accumulation and the casts between kernels (sub-question 2; ADR-0152 "precision steps");
   - oracle, tolerance and input distribution (sub-question 3; #5 B-7);
   - H, d_h and any B-4 value (HQ-0064);
   - weights and tokenizer, their source, file format, storage, tied embeddings (sub-question 5; OD-9, OD-25);
   - model-level reference, comparison metric, prompts, generation length, token selection, **lm_head rows** (sub-question 6);
   - any new external dependency (sub-question 7);
   - whether the executor's output is C-6's "whole-model binary" (sub-question 8);
   - model-level performance (sub-question 9);
   - the scenario (sub-question 10);
   - each kind's contract (OD-6 sub-question 1);
   - one instance per shape (OD-6 sub-question 3);
   - `best.json` content (OD-20).
4. **No data-plane change** (A-13): no member, file, kind value or version of `STATE.json`, `instance.json`, spec, eval or `artifacts.json` is added or changed. Consequences says so. If the design seems to need a data-plane file (e.g. a record of a model run), the record leaves it open and names it; it does not define it.
5. **Runtime acceptance items**: Consequences lists any fact that only a runtime machine, a real model file or a live `claude` can establish, numbered for an HQ with reason `runtime-acceptance`. If there are none, it says "none".
6. **`ARCHITECTURE/Requirements.md`**: the OD-31 row follows the register's **"행 형식" (line 84)**:
   - add one link to ADR-0153 with a few-word topic after `**확정분**:`;
   - rewrite `**잔여**:` in place so it shows what remains of ④;
   - leave the status word as "논의중" with a short date/path.
   
   Do not restate the record and do not add dated sentences.
7. **`ARCHITECTURE/OpenDecisionProposals.md` § OD-31** follows the header's **"기록 규칙" (line 8)**:
   - add one `- **채택분** [ADR-0153](…) — <topic> (부분 답: 하위 질문 ④)` line;
   - rewrite sub-question ④'s bullet-head status word and its closing status (`→ 부분 답: [ADR-0153]…. 남음: …`, or `→ 답함`) in place;
   - keep the question's wording.
8. **`ARCHITECTURE/StandardScenarios.md`**: re-check coverage of S0 (step 4) and S1 by the "검사 규칙", then follow **the first paragraph of § 검사 결과 (line 170)**:
   - rewrite the "최근 재검사" line in place (date, trigger, result);
   - add a "판정 변화 이력" entry only if a verdict or gap changed.
9. **Less exact, not edited**: Consequences lists sentences in earlier ADRs or registers made less exact by this record (search `ARCHITECTURE/`, `PROCESS/PLAN.md`; not claimed complete). They are not edited here.
10. **Size and scope**:
    - `git diff origin/main --stat` lists only `touchesFiles`;
    - non-test size ≤ 300 LOC (DRIVER §5, D4);
    - no `hilclaw/`, `tests/`, `orchestration/` or `PROCESS/` file is changed.
11. **Document mode** (CLAUDE.md A-13):
    - context-isolated reviewer cycle (dev-code-review) until Approve, at most 7 rounds;
    - rebase on `origin/main`, then push straight to `main`;
    - the commit carries `Reviewed-by: reviewer agent (N rounds, Approve)` and the trailer `Task: T-0418`;
    - delete the branch.
    
    Never use `git push --force*`.
12. **DRIVER §9 notice**: after landing, post one comment on issue #5 that names ADR-0153, the 7-day objection window and the record's readings of owner sentences (if any), ending with `— posted by driver`.

## Out of Scope

- Any code: the executor itself, kernels, harness, synthetic model fixtures (later code slices named in Consequences).
- Kind contracts, `kind` values, `op_signature` members for kinds other than `gemm` (P2-11).
- Answering or rephrasing HQ-0064 or the OD-31 ②/③ HQs, and any owner-only sub-question (②, ③, ⑤–⑩).
- `best.json` / candidate archive content (OD-20), promotion (OD-29).
- Editing earlier ADRs, UsageCases, PLAN, or any file outside `touchesFiles`.
- Downloading Llama weights or tokenizer, starting `claude`, using a board (D16).

## Follow-ups

- (executor fills) Code slices named by ADR-0153 Consequences, e.g. the executor module over `gemm` fp32 with a synthetic model, if one is possible before the ②/③ answers. The next planner judges whether such a slice waits on those HQs.
- (executor fills) Any owner question the record raises, in DRIVER §8 form (Korean, options, what is blocked and what is not), for the driver to record as an HQ.

## Result

- **DONE.** ADR-0153 (`ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`) with the OD-31 register row, OpenDecisionProposals § OD-31 (④ → 일부 답함) and the StandardScenarios re-check line (S0, S1: no verdict change, no gap) landed on `main` as **4498d50** (document mode, direct push, `Reviewed-by: reviewer agent (7 rounds, Approve)`, `Task: T-0418`). Branch `claude/T-0418-adr-od31-model-executor` deleted (local and remote).
- **Review**: 7 rounds. Rounds 1-3 requested changes (ADR-0144 image citation narrowed and the two loading needs made this record's own; runtime item renumbered; OD-16 ① and OD-6 ④ limits; RoPE table, KV cache capacity left to the SDPA contract; listed-shape fit rule; invalid-input outcome; in-process tamper limit); rounds 4-7 approved with nits, each addressed through round 6. Round 7 approved with two non-blocking points not addressed (round limit), listed under Follow-ups below.
- **DRIVER §9 notice** posted on #5: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6355510786
- **Decided** (part of OD-31 ④): Python host side in `hilclaw/` + a fixed-source C model program, one process per generation; explicit binding (call site → kernel source + `task.contract` + build settings), fit check, one shared library per kernel loaded with `dlopen`; embedding copy, contract-left copies, buffers and KV cache owned by the model program; pass and generation order; named outcomes (no kernel, kernel unfit, invalid input, build failed, run failed), no fallback; synthetic-model verification. **Open of ④**: binding from best (OD-20, OD-7), where token selection is applied (with ⑥), isolation of the model program (OD-14), exposure (⑩, OD-18, OD-23), targets other than `cpu_standin`.
- **Runtime acceptance items for HQs** (reason `runtime-acceptance`, ADR-0153 Consequences): (lxvii) the model program builds with its kernels' shared libraries and loads them with `dlopen` in the isolated environment OD-14 gives it, with the user's image, on each kind of C-7 machine — ask once code slice 1 has landed; (lxviii) a generation at Llama 3.2 1B dimensions (any weights) fits that environment's memory limit — ask once code slice 2 has landed. Neither is to be raised now.
- **Owner question**: none new.

### Follow-ups (executor)

- Code slice 1 (ADR-0153 Consequences): host-side binding checks and outcomes, build of fp32 `gemm` kernels as shared libraries, a model program calling them through ADR-0008's prototype, tested with hand-written kernels — possible before the HQ-0064/0065/0066 answers; the planner judges whether it is worth taking first (D18). Code slice 2 (full pass and generation loop on the synthetic model) waits on the P2-11 contract records.
- Two non-blocking review-round-7 points, for a later edit of ADR-0153 if wanted: (1) Decision 2 could state that an array whose dtype `numpy` lacks (bf16) is held and passed as its raw 16-bit pattern and that the host side does no arithmetic on it, so "no new dependency" holds whatever ② answers; (2) the Boundaries item of sub-question 8 could say that the per-kernel loading and the build directory's lifetime are revisited if the executor's output is the whole-model binary. Under D18 these are wording touch-ups (보류 candidates) unless a code slice needs them.
