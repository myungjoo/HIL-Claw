---
id: T-0531
title: Write the generalization design ADR for PLAN P3-1 and state the owner's parts as concrete questions
phase: P3
status: IN_PROGRESS
commitMode: doc
coversReq: [D27, OD-32, C-6, NFR-6, "PLAN P3-1"]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 500, files: 4}
hq: []
---
## Why

**State.** The owner decided on 2026-11-02 (DRIVER D27, PLAN P3) to widen the system to many custom NPUs and many models. The code is still tied to the first case: build flags are CPU constants, the model run has a fixed target, contracts are C only, harnesses are written by hand per kind, and the forward program is fixed.

**Why this comes first.** PLAN P3-2 to P3-5 each take their design from this ADR: P3-2 says outright that the place of the language follows OD-32 ②.

**Why an ADR-only task.** DRIVER §6 D20 ① allows this when owner-only decisions are likely to surface while writing. OD-32 ①, ⑥ and ⑦ are owner-attributed, and parts of ②, ③ and ④ are too. DRIVER §6 D27 ⑤ says this task leaves those parts undecided and writes the form in which to ask them, so the "raise an HQ instead of a task" rule does not apply to it.

**How it ends.** The executor lists the HQs in `## Result` and returns `DONE`. The driver records them and checks P3-1 at §3-6 (D27 ⑤). §8's `BLOCKED` is not applied for these parts, and closing all of OD-32 is not required. The other BLOCKED reasons (review round limit, timeout and so on) still apply.

**No failed item or issue is being fixed.** As of `main` `dff3babf`, `PROCESS/RuntimeAcceptance.md` holds no `실패` item and no `nightly-failure` issue is open. If that has changed when this task runs, follow DRIVER §6 D27 ① and report it instead of carrying on.

**D16.** This task uses reading and writing only: no `claude`, Docker daemon, model file, board or API key.

## Required Reading

- `PROCESS/DRIVER.md`: §3-5 and §5 (branch `claude/T-0531-<slug>`, the `Task: T-0531` trailer, the size cap, doc mode), §3 "BLOCKED 사유" and "승인된 열린 목록" (D23), §6 D20 and D27, §8 (the HQ fields and form), §9 (who may close what), §11 rows D16, D23 and D27.
- `CLAUDE.md`: A-13 doc mode, "세 층 모델", "도구 계층 언어 정책", "미결은 발명하지 않는다", "문서 커버리지 재검사".
- `PROCESS/PLAN.md`: section "P3 — 일반화" and the Qualcomm reservation under "P3 밖".
- `ARCHITECTURE/OpenDecisionProposals.md`: the header's "기록 규칙" and § OD-32.
- `ARCHITECTURE/Requirements.md`: "행 형식" above the register, the rows OD-4, OD-9, OD-26 and OD-32, C-6, FR-9, FR-10, FR-14, NFR-6.
- `ARCHITECTURE/StandardScenarios.md`: the inspection rules and the first paragraph of "검사 결과".
- `PROCESS/STATE.json` `humanQuestions`: HQ-0078 (especially ⑤), HQ-0083 and HQ-0085 (answered), and HQ-0081 (open).
- ADRs:
  - ADR-0001 (key fields), ADR-0016 (backend selected by `accelerator`), ADR-0018, ADR-0035.
  - ADR-0002 (spec), ADR-0005 (artifacts record).
  - ADR-0100, ADR-0183 (result format v2).
  - ADR-0116 (build settings), ADR-0144 and ADR-0182 (containers).
  - ADR-0152, ADR-0153 and ADR-0166 (model operations, executor, forward pass), ADR-0189 (binding).
  - ADR-0177 (contract table), ADR-0190.
  - ADR-0192 (the current form of an ADR's Status section; read that section only).
- Code, as the survey needs it:
  - `hilclaw/standin_settings.py`, `hilclaw/model_run_binding.py`, `hilclaw/backends.py`, `hilclaw/standin_profile.py`, `hilclaw/keys.py`, `hilclaw/contract_table.py`
  - `hilclaw/model_forward_run.py`, `hilclaw/model_program.c`, `hilclaw/harness/bf16_timing.py`, `hilclaw/harness/bf16_verification.py`
  - `orchestration/round-manager.md`, `orchestration/agents/`

## Acceptance Criteria

1. **One ADR**, `ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md`, in one record as D20 ② asks, with the Status section form of ADR-0192. It separates what the owner decided (cited, marked owner), what this record decides under §9, and what it leaves open. Its A-13 reading says which part changes the frame (D23) and, for any value added to an approved open list, which list.

2. **A survey first.** A short table of the first-case assumptions in the code that P3-2 to P3-5 must lift, each with its file and the P3 item that lifts it. Findings are cited, not restated.

3. **The design covers each thing PLAN P3-1 names:**
   - **Candidate kinds and the boundary (OD-32 ①, ⑥, ⑦).** For C kernels, vendor-language kernels, quantization settings and compile settings, the ADR states the seam at which a kind plugs in: what makes a candidate and what evaluates it. Only the C kernel path is designed as a binding decision. The others are stated as what the owner's answers would plug into, with no record format, coder role, instance unit, quality metric or evaluation data chosen.
   - **Target description (OD-32 ②).** Where build options, language, memory limit and measurement unit are written, and how that links to `hw_profile` (OD-4) and the backend table (OD-26). `cpu_standin` keeps its behaviour and its existing results. Say which placement needs no frame change, and ask the owner about any that does.
   - **Virtual NPU (OD-32 ③).** Which values differ from CPU and how, for use as a generalization check only. No value is presented as a fact or evidence about a real NPU. See criterion 4 for its limits.
   - **Model graph file (OD-32 ④).** The form of nodes, connections and weight references, its relation to the existing executor, and whether it sits inside the data plane. If inside, that part goes to the owner. External formats stay under OD-9.
   - **Table-based generation (OD-32 ⑤).** What is generated from the ADR-0177 table for the correctness and timing harnesses, which operations stay handwritten and why, and how "existing results unchanged" is verified.

4. **Limits on the design.**
   - **fp16:** do not make P3-3 depend on fp16, and do not ask about it again. HQ-0083 (b) defers it until after P2-15 and D27 ④ re-asks it then. The same holds for the gate question of HQ-0085. If the virtual NPU can differ in data type only through a new numeric format, say so and ask about that other format as an owner part (OD-32 ③).
   - **Measurement unit:** values other than `ns` and the designation of their open list are the owner's (HQ-0078 ⑤), so state whether P3-3 can proceed with `ns` meanwhile.
   - **Not closed:** real target facts (#5 B-1, B-2, B-3), the open points of the Qualcomm reservation and OD-9 (OD-32 "닫지 않는 것").
   - **P2-15:** nothing here changes what the owner's P2-15 check runs. D27 runs P3 in parallel with it, and a P2-15 failure is fixed first.

5. **A dependency table.** For each of P3-2 to P3-6, which decisions of this ADR it rests on and which HQ answers, if any, it must wait for. D27 ⑥ requires that work not depending on an answer continues, so state the part of each item that can go ahead without one. Size each of P3-2 to P3-5 roughly against the DRIVER §5 cap, as input for the planner, without creating tasks.

6. **Owner's parts as HQ drafts.** ADR and Result both carry every owner part, and every owner-attributed part of OD-32 (① ⑥ ⑦, and those of ② ③ ④ the design reaches) is either covered by a draft or stated as not yet reached, with the reason.
   - **Each draft has:** `taskId` T-0531; `reason` (`data-plane-schema-change` or `owner-decision`, as earlier HQs use them); and `question` **in Korean** in the §8 form: the issue, options (a), (b), …, and what is blocked and not blocked while unanswered.
   - **A frame change** gives the concrete format: exact member names and values, in which file, and what version change, as PLAN P3 asks. It also names who may add values if it proposes an open list.
   - **Recommendation:** a draft may name a recommended option, marked as the executor's recommendation.
   - **No duplicates:** no draft repeats a question already in `STATE.json` (D27 ⑦). Merge questions that one answer would settle, so the owner gets as few as the decisions need.

7. **Register and proposal edits**, following the rules written in those files and not earlier tasks' wording:
   - `OpenDecisionProposals.md` § OD-32 per its "기록 규칙": one adoption line for ADR-0193, sub-questions' status rewritten in place, question wording kept, no dated paragraphs and no restatement of the ADR.
   - `Requirements.md` per "행 형식": the OD-32 row names ADR-0193 once under its confirmed part and rewrites what remains. Keep the status open, since OD-32 is not closed. Edit another OD's row only if this ADR answers part of it.
   - `StandardScenarios.md`: recheck coverage by its inspection rules and rewrite the "최근 재검사" line in place, as the first paragraph of "검사 결과" says. If a verdict changes or a gap appears, add the one entry that paragraph calls for.

8. **Review and landing.** Doc mode: the reviewer cycle, then rebase on `origin/main` and push to `main` with the `Reviewed-by: reviewer agent (N rounds, Approve)` trailer and `Task: T-0531`. The review checks in particular that no owner part is decided by a sentence of this record.

9. **Result records:**
   - the commit and review rounds;
   - the HQ drafts in full, ready for the driver to copy;
   - the §9 notice for the driver to post on #5 (which sub-questions this record answers and the objection window);
   - any runtime acceptance item (expected: none, since P3-4 registers its own after landing);
   - any sentence in other records this ADR makes less exact, listed but not edited.

## Out of Scope

- Any code, test, schema or validator change; the implementation of P3-2 to P3-6.
- Editing `PROCESS/PLAN.md`, `PROCESS/STATE.json` or `PROCESS/RuntimeAcceptance.md`, or checking P3-1: the driver does these (D27 ⑤).
- Changing the "C 커널" wording of `CLAUDE.md` or `C-6` (owner: OD-32 ⑥, ⑦).
- Adding fp16, gates, catalog entries for bf16, or the S6 scale of HQ-0081.
- Choosing a real NPU, SDK, model list, quantization method, or quality metric.
- Lines in the PLAN hold section.

## Follow-ups

## Result
