---
id: T-0569
title: Apply HQ-0096 (1) (b) for PLAN P3-12 — write the §9 ADR for LLM-level evaluation (the subject evaluated, the metric definitions and how they are measured, the key of LLM-wide code, the concrete record form to put to the owner), update the registers, and return the record form as an HQ
phase: P3
status: IN_PROGRESS
commitMode: doc
coversReq: [D27, FR-19, OD-33, OD-32, C-6, "PLAN P3-12", HQ-0096]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0206-od33-llm-level-evaluation.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
  - ARCHITECTURE/UsageCases.md
estimatedSize: {loc: 330, files: 5}
hq: []
---
## Why

**PLAN P3-12** (LLM 수준 평가) is now the first unchecked, unskipped P3 item: P3-1 to P3-11 and P3-13 to P3-15 and P3-17 are checked, and the owner's answer to **HQ-0096** (2026-11-14, `main` `badc6abf`) removed its owner-confirmation marker. The owner's answer (1) (b), verbatim in `PROCESS/STATE.json` `humanQuestions` HQ-0096 `decision`:

- the evaluation of given LLM code is decided apart from HQ-0088 (4); an optimisation instance stays one kernel (C-6) and the **unit of evaluation is the whole LLM**;
- **metrics**: prefill and decode tokens per second, time to first token, decode time per token, peak memory; **both the latency side and the throughput side** are recorded;
- **quality floor**: agreement with the reference output — the verdict of the existing `hilclaw.model_check`;
- the **record holds the batch size and the number of concurrent requests**, both 1 for now;
- perplexity and evaluation data are asked when a lossy candidate kind is chosen (HQ-0088 (4) as it is).

The integrator's reading recorded with the answer (not the owner's words): the form of the metrics and of the batch / concurrency members is a **data-plane frame**, so P3-12's §9 ADR writes it and it is approved again through an HQ before it is implemented (DRIVER §3 "BLOCKED 사유", D23); the key of LLM-wide code (OD-33 ⑥'s remaining part) is decided or asked by the same ADR; model execution works only on `cpu_standin` today (`model_run`) and has no model-level timing yet; GPU and NPU memory figures stay open.

**Why an ADR-only task (DRIVER §6 D20 ①, ④).** D20 ① puts an ADR with its first code slice, except when an owner-only decision is likely to appear while the ADR is written. Here it is certain: the record form needs the owner's approval before any writer exists, and the measurement itself — what is timed, under which prompt and generation lengths, what "peak memory" covers — is defined by this same ADR and feeds the program that the owner's pending P2-15 check runs (`hilclaw.model_check`, RA-0056 `미확인`), so code written before the ADR lands and the HQ is answered would be rework on the P2-15 path. The later slices (measurement, the record writer, the command surface) depend on this ADR's decisions and the owner's answer and are not created ahead (D20 ④); the ADR lists them.

**Order (DRIVER §6 D27 ①, D31 ①).** On `main` `badc6abf`: no PR is open; no `nightly-failure` issue is open (T-0559, nightly #373, is BLOCKED on HQ-0100 and is not this task's concern); `PROCESS/RuntimeAcceptance.md` has no item whose `상태` is `실패`, and RA-0056 is `미확인` (D27 ④ asks nothing yet); no P2-15 preparation is pending. P3-12 comes before P3-16 (D31 ①; P3-16 also needs HQ-0096 ② and is its own item). If that has changed when this task runs, report it in `## Result` and stop before writing.

**The brake (DRIVER §6 D31 ②)** does not apply: this is a PLAN item.

**The HQ this task returns (D27 ⑥, ⑦).** The executor writes the owner question with the concrete record form in `## Result` and returns `DONE`; the driver records it. Do not ask again or anticipate questions already in `humanQuestions`: HQ-0081, HQ-0083 and HQ-0085 (asked again only after RA-0056); HQ-0100 (nightly #373). OD-34 and OD-35 (registered 2026-11-14) are not part of this task.

## Required Reading

- `PROCESS/DRIVER.md`:
  - **§3-5 and §5**: branch `claude/T-0569-<slug>`, the `Task: T-0569` trailer, size (D30: ≤ 600 LOC recommended — ADR lines count —, ≤ 10 files), storage (D29: temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0569/`, removed at the end).
  - §3 "BLOCKED 사유" and "**승인된 열린 목록**" (what is a frame change; the measurement-unit list of HQ-0090 reaches `intervals` and `resolution`, not `memory_bytes`).
  - §6 D27 (①, ⑥, ⑦), D31 (①, ②), and **§8** (HQ structure) and **§9** (the ADR path: executor ADR + reviewer Approve + owner notice on #5 with the 7-day objection window).
- `PROCESS/STATE.json` `humanQuestions`: **HQ-0096** (question and `decision`), HQ-0088 (④), HQ-0090 (units, `memory_bytes`), HQ-0097 (the `given_code` record, the key of given code), HQ-0071 and HQ-0084 (the `model_check` verdict and the P2-15 command).
- `PROCESS/PLAN.md` P3-12 (line ~73), P3-16 (line ~80, for the boundary only), P2-15 (line ~51).
- `ARCHITECTURE/Requirements.md`: FR-19 (①, ④), FR-6, FR-13, NFR-2, NFR-3, C-6, the OD-33 and OD-32 rows, and "**행 형식**" (the paragraph before the OD register, line ~85).
- `ARCHITECTURE/OpenDecisionProposals.md`: header "**기록 규칙**" (line ~8); § OD-33 (sub-questions ①, ⑤, ⑥); § OD-32 (⑦).
- `ARCHITECTURE/StandardScenarios.md`: §검사 규칙, S12 and its verdict row, and the first paragraph of §검사 결과 (line ~188). `ARCHITECTURE/UsageCases.md` UC-E5.
- ADRs (`ARCHITECTURE/decisions/`): `ADR-0001-od4-key-schema.md` (the key and the "Record format" section the new ADR follows); `ADR-0153-od31-model-executor.md`, `ADR-0157-od31-executor-call-site-dtype.md`, `ADR-0166-od31-bf16-forward-pass.md` (decision 7, the report), `ADR-0176-od31-model-level-reference-and-comparison.md` (decision 5, greedy generation; the comparison), `ADR-0182-od14-model-executor-container.md`, `ADR-0189-od31-binding-from-run-incumbents.md`, `ADR-0192-od31-model-check-command.md` (the command, its output line, its verdict); `ADR-0193-od32-generalization-design.md` (decisions 3 and 5 — the target table's `model_run`, the graph program); `ADR-0194-od33-vendor-stack-evaluation-design.md` (decisions 2, 4, 5 and 10 V5 — the measuring range and the question form); `ADR-0196-od32-measurement-unit-list-and-run-result-v3.md` and `ADR-0183-od18-tool-result-format-v2.md` (units, `memory_bytes`); `ADR-0200-od33-given-code-evaluation.md` (decisions 2, 3, 5 — the bundle, the key of given code, the entry point and its targets); `ADR-0005-od8-artifacts-record.md` (decision 5, `type`); `ADR-0011-od17-journal-and-spend.md` (decision 3, `step` values) and `ADR-0100-od8-tool-result-change.md`; `ADR-0103-od13-imprecise-timing-detection.md`.
- Code (read only): `hilclaw/model_check.py`, the header comment of `hilclaw/model_forward.c`, `hilclaw/model_forward_run.py`, `hilclaw/model_forward_execute.py`, `hilclaw/model_forward_container.py`, `hilclaw/model_graph_execute.py`, `hilclaw/model_run_binding.py`, `hilclaw/targets.py`, `hilclaw/given_eval.py`.

## Acceptance Criteria

1. **ADR-0206** (`ARCHITECTURE/decisions/ADR-0206-od33-llm-level-evaluation.md`; use the next free number if 0206 is taken), in the ADR-0001 record format, with Status separating **owner** content (HQ-0096 (1) (b) — cited from `STATE.json`, not subject to the objection window) from **this record's own** §9 decisions (executor + reviewer, owner notified on #5) and from the **form put to the owner** (not decided). It covers:
   1. **The subject evaluated now.** What "LLM-wide code" P3-12 measures first, from what exists: the forward program of ADR-0166/ADR-0176 built from run kernels through `hilclaw.model_check` (the progress measurement after the loop, FR-19 ①), the graph program of ADR-0193 decision 5, and given whole-LLM code from a user. A given whole-LLM bundle is not an ADR-0200 bundle (one C file implementing a contract); if the ADR wants it now, its form is an OD-33 ① remainder and goes into the HQ — do not invent it. State which targets the evaluation accepts now (`model_run` true) and what a vendor target needs before it is accepted (named, not decided).
   2. **The metric definitions and how each is measured**, for each of the owner's metrics (prefill tokens/s, decode tokens/s, time to first token, decode time per token, peak memory) and for the latency side and the throughput side: what interval is timed and by which clock, where in the program it is taken, repetitions and warm-up, the prompt and generation lengths it depends on and who sets them (if a value is the owner's — e.g. a fixed evaluation prompt — put it in the HQ rather than choosing it), what peak memory covers (process, container, weights) on `cpu_standin`, and why GPU or NPU memory figures stay open. With batch size and concurrent requests both 1, state what "throughput side" means and that it is not a measurement of batching.
   3. **The quality floor**: how the `model_check` verdict (`match`) gates the metrics — e.g. whether figures of a `no_match` generation are recorded and how they are marked — within HQ-0096 (1) as answered; perplexity and evaluation data are out (HQ-0088 ④).
   4. **The key of LLM-wide code** (OD-33 ⑥'s remainder): whether the existing `hw_profile` and a model identity serve, or a key the frame lacks is needed. If the frame lacks it, write it into the HQ in concrete form; do not invent it as decided.
   5. **The record form to put to the owner** (D23): the concrete place and shape — file or record, its location in the data plane, every member with its type and unit (the units list of HQ-0090 / ADR-0196 and what it does not reach), the batch-size and concurrent-request members with their value 1, the quality verdict, the toolchain and target identification (NFR-2), the version stamp and how readers treat it — and the alternatives considered (at least: a new member set in an existing record vs. a new record; and the option of not writing to the data plane and printing only through `model_check`'s output line, with what that loses). Mark the whole section as not decided until the owner answers.
   6. **The slices** for the planner after the answer, with rough sizes against DRIVER §5 (measurement in the program and host side; the record writer and its validator; the command surface; tests), which slice touches the P2-15 path (`model_check`, `model_forward.c`) and the rule that its existing output and verdict stay unchanged, the slice that verifies with a real toolchain on this machine (D29: clang for `cpu_standin`), any runtime acceptance item (real weights — the owner's P2-15 machine) to hand to `PROCESS/RuntimeAcceptance.md` through `## Result`, and where PLAN P3-12 is checked.
   7. **A-13 reading**: what of the frame this ADR changes (nothing until the owner answers); no approved open list of DRIVER §3 gains a value unless named and justified.
   8. **Consequences** (registers answered; "Less exact, not edited" list) and **Boundaries** (P3-16 and HQ-0096 ②, vendor targets, GPU/NPU memory figures, perplexity and evaluation data, model-unit candidate kinds of HQ-0088 ④, OD-34, OD-35, the coder's role).
2. **Registers**, by their own recording rules — follow these rules, do not copy earlier task files' wording:
   - `ARCHITECTURE/Requirements.md`: the OD-33 row gains one `**확정분**` link to ADR-0206 and its `**잔여**` is rewritten in place (⑤'s record form now waits on the HQ; ⑥'s LLM-wide key as decided or asked); FR-19's trailing open-parts list only if this ADR narrows it. Follow "행 형식": one link per new ADR, open parts rewritten in place, no restatement of the record, no dated paragraphs.
   - `ARCHITECTURE/OpenDecisionProposals.md`: § OD-33 gains one `**채택분**` line for ADR-0206; sub-questions ⑤ and ⑥ (and ① only if touched) get their state rewritten in place — bullet-head state word and the `→ …` ending, question text kept. Follow the header's "기록 규칙".
   - `ARCHITECTURE/StandardScenarios.md`: re-check coverage by §검사 규칙 (CLAUDE.md "문서 커버리지 재검사"); S12's step notes and verdict row only as far as the decided parts narrow them; update §검사 결과 by its first paragraph (only a changed verdict enters the history). `ARCHITECTURE/UsageCases.md` UC-E5 only if its text becomes wrong.
3. **The HQ in `## Result`** (Korean, DRIVER §8 structure: 쟁점, 선택지 (a)/(b)/…, 실행자의 권고, 막히는 것/막히지 않는 것), one question per owner-only part found in 1.1, 1.2, 1.4 and 1.5, each citing the ADR-0206 section that states the concrete form. Name `taskId` T-0569. "막히지 않는 것" names at least P3-16, the owner's P2-15 check and the other P3 items.
4. **No code, no test, no data-plane file changes**; every existing run, tool, nightly and model path behaves exactly as before. Nothing under `hilclaw/`, `tests/`, `orchestration/` or `.github/` changes.
5. **Process**: doc mode (CLAUDE.md A-13): dev-item-address steps, context-isolated review to Approve (≤ 14 rounds, D28), rebase on `origin/main`, push to `main` with the `Reviewed-by: reviewer agent (N rounds, Approve)` trailer and `Task: T-0569`; §9 notice of ADR-0206 on issue #5 (English, no bare `@` mentions), stating that the record form is not decided and waits on the owner's answer.

## Out of Scope

- Any code: measurement in `model_forward.c` or the graph program, the record writer, validators, changes to `model_check`'s output. Create no other task file.
- P3-16 (CUDA demonstration) and HQ-0096 ② (vendor oracle); vendor targets in the evaluation; GPU or NPU memory figures; perplexity and evaluation data; model-unit candidate kinds (HQ-0088 ④); OD-34 and OD-35.
- Starting `claude` in any form (D16); no test run (D25).

## Follow-ups

## Result
