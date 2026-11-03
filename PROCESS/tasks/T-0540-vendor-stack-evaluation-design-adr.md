---
id: T-0540
title: Write the vendor-stack evaluation design ADR for PLAN P3-7 (adapter boundary, measurement scope, fault-injection contract, fact re-check) and state the owner's parts of OD-33 as concrete questions
phase: P3
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-19, OD-33, FR-10, FR-14, NFR-4, "PLAN P3-7"]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0194-od33-vendor-stack-evaluation-design.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 450, files: 4}
hq: []
---
## Why

**State.** The owner set the vendor-stack code evaluation direction on 2026-11-02 (Requirements FR-19, OD-33, PLAN P3-7 to P3-13) and answered the toolchain questions on 2026-11-03 (DRIVER §6 D29, OD-33 ③ ⑦ ⑨ in part). PLAN P3-1 to P3-5 are done except P3-3, which waits on HQ-0090 and HQ-0091 and is treated as handled until they are answered (DRIVER §6 D27 ⑦). P3-6 is "오너 확정 필요" and is skipped. P3-7 is therefore the next P3 item in listed order (D27 ①).

**What P3-7 is.** The design that P3-8 (adapter frame and environment check), P3-9 (CUDA), P3-10 (Qualcomm) and P3-13 (GPU run) build on. PLAN P3-7 limits it to what DRIVER §9 lets the driver decide: the boundary of the build, run and measure adapters; what a measurement includes; the contract of a fault-injection script; and a re-check of the OD-33 fact memo against the original sources. P3-13 and P3-10 already defer to this ADR: whether a GPU timing includes completion of the GPU work, and how two measurement points of one target are told apart in results.

**Why an ADR-only task.** DRIVER §6 D20 ① allows it when owner-only decisions are likely to surface while writing. OD-33 ①, ②, ⑤ and ⑥, the rest of ③, and the owner parts of ④, ⑧ and ⑨ are owner-attributed, and the code that follows (P3-8) depends on what this ADR decides, so no code slice is planned with it.

**How it ends.** PLAN P3-7's completion criterion is that the ADR lands; closing all of OD-33 is not required. Owner parts are not decided: under D27 ⑥ the executor writes each as a concrete question (Korean text in `## Result`) and still returns `DONE` once the ADR has landed, so the driver can check P3-7. Other BLOCKED reasons (review round limit D28, timeout, and so on) still apply.

**No failure is being fixed.** As of `main` `4de12f78`, `PROCESS/RuntimeAcceptance.md` holds no `실패` item, no `nightly-failure` issue is open and no PR is open. If that has changed when this task runs, follow DRIVER §6 D27 ① and report it instead of carrying on.

**D16 and D29.** This task reads and writes documents only. It needs no `claude` process, Docker daemon, board, accelerator, model file or API key, and it requires no vendor toolchain, so nothing is downloaded or installed. Reading which tools the machine has (for example `nvcc --version`, `nvidia-smi`) is allowed if the ADR wants to cite it, with no install; the absence of a vendor toolchain does not block this task.

## Required Reading

- `PROCESS/DRIVER.md`: §3-5 and §5 (branch `claude/T-0540-<slug>`, the `Task: T-0540` trailer, the size recommendation and file cap, doc mode, the storage rule), §3 "BLOCKED 사유" and "승인된 열린 목록" (D23), §6 D20, D27 and **D29 (the toolchain line: what counts as a toolchain, who checks the machine, the pre-allowed Qualcomm and NVIDIA downloads, the HQ path for anything else, container images, FR-19 ⑤ test rule)**, §8 (HQ fields and form), §9 (what the driver may close), §11 rows D16, D22, D23, D25, D27 and D29.
- `CLAUDE.md`: A-13 doc mode, "세 층 모델", "도구 계층 언어 정책", "미결은 발명하지 않는다", "문서 커버리지 재검사", "개발 드라이버와 런타임의 구분".
- `PROCESS/PLAN.md`: section "P3 — 일반화" (P3-7 to P3-14 and the paragraph above P3-7) and the Qualcomm reservation under "P3 밖".
- `ARCHITECTURE/Requirements.md`: "행 형식" above the register; FR-9, FR-10, FR-14, FR-19, NFR-2, NFR-3, NFR-4, C-3, C-6, C-7; the register rows OD-14, OD-26, OD-32 and OD-33.
- `ARCHITECTURE/OpenDecisionProposals.md`: the header's "기록 규칙"; § OD-33 (all sub-questions and the fact memo); § OD-32; § OD-14 and § OD-26 for what this ADR must not close.
- `ARCHITECTURE/StandardScenarios.md`: §검사 규칙, the first paragraph of §검사 결과, S12 and its row in the verdict table.
- `PROCESS/STATE.json` `humanQuestions`: HQ-0088, HQ-0089, HQ-0090 and HQ-0091 (open; HQ-0090 already covers the unit list and says how far its answer reaches into OD-33 ⑥), HQ-0078 ⑤ and HQ-0085 (answered).
- ADRs: [ADR-0193](../../ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md) (decisions 2, 3, 4, 8, 9 and Boundaries — the target table and seam this design sits on); ADR-0001 "Record format" section (format of the new ADR); ADR-0016 (backend frame); ADR-0060 decision 3; ADR-0063 and ADR-0183 (result members, `unit`, conditions); ADR-0100 (step value change); ADR-0007 and ADR-0103 (what a timing is, coarse clock); ADR-0116 and ADR-0188 (build settings); ADR-0144 and ADR-0168 (build and process container, exit statuses 125 to 127); ADR-0004 (attempt layout).
- Code, to state the boundary against what exists: `hilclaw/targets.py`, `hilclaw/backends.py`, `hilclaw/mock_backend.py`, `hilclaw/hw_tool.py`, `hilclaw/clang_build.py`, `hilclaw/local_run.py`, `hilclaw/standin_container.py`.
- Fact memo sources named in § OD-33 (ExecuTorch Qualcomm backend page, NVIDIA CUDA on WSL guide, the Qualcomm Hexagon-MLIR blog post) — read the originals (web fetch); cite what is confirmed and list what is not.

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md) before any edit of `ARCHITECTURE/`: open PRs, issues #4, #5, #7, #8, unresolved HQs and `RuntimeAcceptance.md` `실패` items, recorded in the ADR's Status as ADR-0193 does. If an open PR edits the same OD-33 section or register row, stop and report.
2. **New ADR** `ARCHITECTURE/decisions/ADR-0194-od33-vendor-stack-evaluation-design.md` (use the next free number if 0194 is taken on `main`), in the ADR-0001 record format, with Status separating owner content (cited), this record's own content (accepted under DRIVER §9, objection window and #5 notice), and the parts left for the owner. It decides, within §9, at least:
   - **Adapter boundary**: the build, run and measure adapters of a vendor target, how they attach to the target table (`hilclaw/targets.py`, ADR-0193 decision 3) and the backend table (ADR-0016) without changing `cpu_standin`'s behaviour or results; the split between assembling a tool's arguments, executing it and interpreting its output, so that assembly and interpretation are testable without the tool (FR-19 ⑤).
   - **Outcomes the adapters distinguish**: build success, compile failure, run failure, time-out, tool missing — mapped to existing result conditions where one fits. Any outcome that needs a new value or member in the data plane is not added: it becomes a question (criterion 4).
   - **Measurement scope**: what one timing includes and excludes (launch, transfer, synchronisation, warm-up), and in particular whether a GPU timing includes completion of the GPU work (PLAN P3-13), consistent with ADR-0007 and ADR-0103.
   - **Two measurement points of one target**: the means by which results tell an emulator or simulator measurement from a device measurement (FR-19 ④; PLAN P3-10 offers FR-10 mock as an example), stating which part is the driver's and which is OD-33 ④'s owner part.
   - **Fault-injection script contract**: where test-written scripts live, how an adapter is pointed at one, what they must emit, which failures they may stand in for (only ones hard to cause with the real tool), and that they are never evidence of real behaviour and never replace an absent toolchain (FR-19 ⑤, D29).
   - **Environment check command** (PLAN P3-8): its boundary only — it reads host and image toolchains, drivers and devices and their versions without installing anything, and is shared by driver tasks and the runtime; where its report goes (outside the data plane unless the owner decides otherwise).
   - **Fact memo re-check**: each fact of the § OD-33 memo re-read in the original and cited with URL and date; facts not confirmed (for example HexKL distribution, SDK and image licence terms) are listed and carried into the questions of OD-33 ② and ③.
   - **The driver's part of OD-33 ⑧ and ⑨**: whether CUDA or C++ sources may sit in the repository as test fixtures under the layer-2 language policy (and if the ADR admits a language outside {Python, POSIX sh, C}, it says so as the ADR CLAUDE.md requires); the reading of isolation for driver checks. The layer-3 "C 커널" wording and the coder's role are not decided (owner; HQ-0088 already asks them).
3. **Not decided, not invented**: OD-33 ①, ②, ⑤, ⑥, the rest of ③, the owner parts of ④, ⑧ and ⑨, real target facts (#5 B-1, B-2, B-3), OD-14 and OD-26's registry, the Qualcomm reservation. No frame change (D23) is made: no member, value, version or validator of the data plane.
4. **Owner's parts as questions** (D27 ⑥): a section of the ADR lists each open owner part with concrete options and the executor's recommendation, marked as deciding nothing. `## Result` holds, for each, the full Korean HQ text in DRIVER §8 form (쟁점, 선택지 (a)·(b)·…, 막히는 것, 막히지 않는 것) and its reason (`owner-decision` or `data-plane-schema-change`). No question repeats one already in `STATE.json` (HQ-0088 to HQ-0091 in particular: the unit list is HQ-0090's; who writes non-C code is HQ-0088's). The executor does not write `STATE.json`; the task still returns `DONE` when the ADR has landed (PLAN P3-7 completion criterion).
5. **Runtime acceptance items**: any fact only a board, accelerator or C-7 container runtime can establish is listed in `## Result` as a runtime acceptance item for `PROCESS/RuntimeAcceptance.md` (D22), not as an HQ; the ADR says it hands them to that file.
6. **OpenDecisionProposals § OD-33** follows that file's "기록 규칙": one `- **채택분** [ADR-0194](…) — …` line; each sub-question this ADR answers in part or whole gets its end state and bullet head word rewritten in place (`→ 부분 답: … 남음: …` / `→ 답함: …`); the fact memo bullet is rewritten in place to point at the ADR's re-check rather than restated; no dated paragraph, no restatement of the ADR.
7. **Requirements register row OD-33** follows "행 형식": the last cell stays one line, the ADR is added once as a link, the 잔여 list is rewritten in place to what remains; the status word changes only if the rules say so. FR-19 text is not edited unless a sentence becomes wrong, and then only that sentence.
8. **StandardScenarios**: S12 (and any scenario the ADR touches) re-checked by §검사 규칙; §검사 결과 updated as its first paragraph says (verdict-change records only; refresh the "최근 재검사" line).
9. **Consequences** of the ADR lists sentences of accepted records or docstrings that become less exact (not edited), and the A-13 reading (no frame change; any open-list value added names the list of DRIVER §3).
10. Doc mode (A-13): reviewer cycle per dev-item-address 10 to 12 until Approve (limit D28), rebase on `origin/main`, push to `main` with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0540` trailers. Post the §9 notice on issue #5 ending with `— posted by driver`.
11. Size: about 450 lines across 4 files; if the ADR needs much more, finish the scope and record size and reason in `## Result` (DRIVER §5 D30).

## Out of Scope

- Any code, test, CI or image (P3-8 onward). No download or install of any tool.
- P3-3's open parts (HQ-0090, HQ-0091), P3-6 (HQ-0088, HQ-0089), P3-11 and P3-12 (OD-33 ①, ⑤, ⑥), P3-14 storage cleanup and the GC questions of ADR-0005.
- Editing `PROCESS/STATE.json`, `PROCESS/PLAN.md` or `PROCESS/RuntimeAcceptance.md` (the driver does that).
- Re-asking fp16, gates or the post-P2-15 priority criterion (D27 ④ waits for RA-0056).

## Follow-ups

## Result
