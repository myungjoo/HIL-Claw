---
id: T-0540
title: Write the vendor-stack evaluation design ADR for PLAN P3-7 (adapter boundary, measurement scope, fault-injection contract, fact re-check) and state the owner's parts of OD-33 as concrete questions
phase: P3
status: DONE
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

- **Status: `DONE`.** Landed on `main` as `c10d84b1` in doc mode, `Reviewed-by: reviewer agent (4 rounds, Approve)`, `Task: T-0540`; branch deleted. Rounds 1 to 3 Request changes (round 1: OD-18 ⑫ overlap — point assignment moved to V4 ①, device-absent probe, executor without GPU, ⑥ partial answer, V3 ①/V5 overlap with D29/HQ-0088 ④; round 2: runtime isolation (owner 2026-10-15) kept, launch reading, wording; round 3: S10 scope inside containers, V6 labels). Round 4 Approve with four Nits, applied as wording only (D20 exception, no new round).
- **Session entry**: no open PR, no `nightly-failure` issue, no `실패` item in `RuntimeAcceptance.md` (as of `9e1f831d`); recorded in ADR-0194 Status.
- **Coverage recheck**: S12 rechecked, "최근 재검사" rewritten in place, verdict unchanged, no gap.
- **ADR**: `ARCHITECTURE/decisions/ADR-0194-od33-vendor-stack-evaluation-design.md`. The English statement of each owner part is its decision 10 (V1 to V6, in the order of the drafts below).
- **Runtime acceptance items**: none from this record (no code lands). P3-8 to P3-10 register their own after landing (ADR-0194 Consequences).
- **Less exact, listed not edited**: none found (ADR-0194 Consequences).
- **Machine read for the ADR** (no install, D29): Windows host `nvcc` 12.3 (V12.3.107), `nvidia-smi` RTX 4070 driver 617.14; WSL Ubuntu CUDA 13.1, clang 14.0.0, Docker 29.1.3; no QNN tool.
- **Size**: ADR 178 lines (long lines) plus 7 changed lines in three other files; within the recommendation (D30).
- **Temporary files**: `${TMPDIR:-/tmp}/hilclaw-driver/T-0540/` removed at the end (vendor pages and review downloads only). No tool installed, no image made.
- **Follow-ups**: none.

### HQ drafts (final text, for `PROCESS/STATE.json`; `askedAt` and `id` the driver's; `issueComment` null)

**Draft V1**: `taskId` T-0540, `reason` `owner-decision`, `question`:

(OD-33 ①, PLAN P3-11; 설계는 ADR-0194 결정 10 V1) [쟁점] FR-19는 QNN·HexKL 등을 쓰는 LLM 코드나 CUDA 코드를 평가할 환경을 갖추라고 하지만, 평가하는 코드가 사용자가 준 기존 코드인지, 코더가 쓴 코드인지, 둘 다인지는 정하지 않았다. [선택지] (a) 사용자가 준 코드를 먼저 P3-11로 평가하고, 벤더 대상에서 코더가 쓰는 코드는 벤더 언어 커널 종류(HQ-0088 ① (c))가 정해질 때 함께 다룬다 (b) 둘 다 지금 (c) 코더가 쓴 코드만. 주어진 코드의 기록 형식은 같은 task의 다른 HQ(틀의 변경)가 묻는다. 실행자의 권고(결정 아님): (a) — 오너의 지시가 기존 LLM·CUDA 코드를 든다. [막히는 것] P3-11, P3-12. [막히지 않는 것] P3-8~P3-10, P3-13, P2-15 확인, 그 밖의 task.

**Draft V2**: `taskId` T-0540, `reason` `owner-decision`, `question`:

(OD-33 ②, #5 B-1; ADR-0194 결정 9·10 V2) [쟁점] PLAN의 예약은 "2번째 지원 대상은 Qualcomm NPU"(오너 2026-10-13)이고 CUDA가 이 순서의 어디에 드는지, 대상의 세대와 SDK 버전은 정해지지 않았다. HexKL은 Qualcomm 소프트웨어 센터의 항목이지만 "currently available on request"다(hexagon-mlir `docs/faq.md`, 2026-11-03 확인). [선택지] ① 순서: (a) Qualcomm은 예약대로 2번째 지원 대상이고 CUDA는 그 순서 밖의 FR-19 평가 대상 (b) CUDA 2번째, Qualcomm 3번째 (c) 그 밖. ② 버전: (a) CUDA는 머신에 있는 툴킷의 버전을 run마다 기록(지금 Windows host 12.3, WSL 13.1) (b) 오너가 정한 버전; 그리고 Qualcomm의 SoC 또는 Hexagon 세대(예: v73·v75·v79)와 QNN 버전(ExecuTorch 문서의 권장은 2.37.0)을 지정해 주십시오. ③ HexKL: (a) 오너가 지금 Qualcomm에 요청 (b) Qualcomm 장비가 생기기 전에는 하지 않음. 실행자의 권고(결정 아님): ① (a), ② (a), ③ (b). [막히는 것] P3-9·P3-10에서 이 값에 기대는 부분, HexKL. [막히지 않는 것] P3-8, 머신에 있는 도구로 하는 P3-9·P3-10, P2-15 확인, 그 밖의 task.

**Draft V3**: `taskId` T-0540, `reason` `owner-decision`, `question`:

(OD-33 ③의 나머지, A-13 새 외부 의존성, NFR-4; ADR-0194 결정 9·10 V3. Qualcomm·NVIDIA 공식 사이트 밖의 도구는 D29대로 도구마다 요청하므로 묻지 않는다) [쟁점] D29는 드라이버의 Qualcomm·NVIDIA 도구 입수와 컨테이너 이미지를 허용했으나, 런타임의 입수, 라이선스 때문에 다른 규칙이 필요한지, 스토리지 상한은 남았다. QNN SDK 안의 `LICENSE.pdf`, Hexagon SDK·HexKL·CUDA 툴킷의 조건과 그것이 컨테이너 이미지에 대해 말하는 것은 읽지 못했다. [선택지] ① 런타임의 입수: (a) NFR-4대로 설치마다 사용자 허락, 같은 공식 출처 (b) 그 밖. ② 라이선스: (a) 벤더 SDK와 그것을 담은 이미지는 그 머신을 떠나지 않고 push·commit하지 않으며, 설치와 함께 라이선스 파일의 경로와 버전을 기록한다 (b) 첫 다운로드 전에 오너가 각 라이선스를 읽는다 (c) 그 밖. ③ 스토리지 상한: (a) D29의 정리와 P3-14 밖의 상한은 없다 (b) 상한을 둔다(값 지정). 실행자의 권고(결정 아님): ① (a), ② (a), ③ (a). [막히는 것] 런타임의 벤더 SDK 설치. [막히지 않는 것] P3-8, D29의 Qualcomm·NVIDIA 공식 다운로드, P2-15 확인, 그 밖의 task.

**Draft V4**: `taskId` T-0540, `reason` `owner-decision`, `question`:

(OD-33 ④의 오너 몫과 벤더 대상에 대한 OD-18 ⑫, #5 B-2·B-3, FR-9; ADR-0194 결정 5·10 V4) [쟁점] HQ-0005는 sim 지점이 에뮬레이터, board 지점이 측정인 구성을 내다보았으나 정하지 않았고(OD-18 ⑫, "필요한 것들과 함께 정하며 그 전에는 정하지 않는다"), ADR-0194는 지점이 정해진 뒤 결과에서 구별하는 수단만 정했다(기존 `step` 값, 지점 사이 대체 없음). [선택지] ① 에뮬레이터·시뮬레이터와 장비가 있는 대상에서 어느 실행이 어느 지점인가: (a) 에뮬레이터·시뮬레이터는 `sim`, 장비는 `board` (b) 에뮬레이터는 mock처럼 다른 `accelerator`의 별도 대상 (c) 그 밖. ② 로컬 GPU의 CUDA는 두 지점의 수단이 하나다: (a) 두 지점 모두 같은 로컬 GPU 실행(HQ-0005가 `cpu_standin`에 한해 답한 것과 같게) (b) `board`만, `sim.run`은 제공하지 않음(한 지점 대상의 규칙 OD-26, 미결). ③ Qualcomm 장비: (a) 개발 머신에 연결(USB, `adb`) (b) LAN의 머신(#5 B-2) (c) 당분간 없음 — 에뮬레이터만, 다른 지점은 제공하지 않음. 실행자의 권고(결정 아님): ① (a) — FR-9의 역할(sim은 조기 필터, board가 최종 판정)을 지킨다, ② (a), ③ (c) 장비가 생길 때까지. [막히는 것] P3-9·P3-10·P3-13의 지점 배정. [막히지 않는 것] 어댑터, P3-8의 틀, ADR-0194 결정 5의 구별 수단, P2-15 확인, 그 밖의 task.

**Draft V5**: `taskId` T-0540, `reason` `owner-decision`, `question`:

(OD-33 ⑤, #5 A-4·B-7·B-8, OD-32 ⑦; ADR-0194 결정 10 V5. HQ-0088 ④와 겹치는 부분은 다시 묻지 않는다) [쟁점 ①] HQ-0088 ④는 모델 단위 후보의 instance 단위·품질 지표·평가 데이터를 언제 정할지 묻는다. 그 답이 주어진 LLM 코드의 평가(OD-33 ⑤의 단위와 LLM 수준 지표)에도 그대로 미치는가: (a) 예, 하나의 답으로 둘 다 정하고 P3-12는 그 답을 따른다 (b) 따로 정한다 — 단위(커널 하나 또는 LLM 전체)와 지표를 지정(예: prefill·decode 초당 토큰, 첫 토큰까지의 시간, 최대 메모리; 품질은 reference 출력과의 일치 또는 지정한 데이터의 perplexity). [쟁점 ②] FR-9는 시스템 생성 reference를 `cpu_standin`에 한해 확정으로 적고, HQ-0091은 `virtual_npu`만 묻는다. 벤더 대상에서 기존 커널 계약의 oracle: (a) 그 계약의 기존 reference와 사용자가 정하는 허용 오차를 그 대상에 한해 쓴다(B-7의 일반 답이 아님) (b) 벤더의 golden output (c) 그 밖. 실행자의 권고(결정 아님): ① (a), ② (a)(HQ-0091 ① (a)와 같은 모양). [막히는 것] 벤더 대상의 `correctness.check`와 instance 시작(②), P3-12(①). [막히지 않는 것] 시작 아래의 빌드·실행·측정, P3-8~P3-10, P2-15 확인, 그 밖의 task.

**Draft V6**: `taskId` T-0540, `reason` `data-plane-schema-change`, `question`:

(A-13 틀의 변경, OD-33 ⑥; ADR-0194 결정 3·10 V6. 측정 단위와 GPU·NPU 메모리 수치는 HQ-0090이 묻는다) [쟁점 (a)] run을 시작할 때 장치가 없거나 쓸 수 없으면(GPU 없음, 장비에 닿지 않음) 프로그램은 시작되므로 기존 tool failure `compiler_unavailable`(S6)·`executable_unstartable`(S10)이 맞지 않고, broken `exit_status`는 머신의 사실을 시도의 탓으로 돌린다. 어떤 답이든 이것은 시도의 코드가 없는 probe 프로세스가 시도의 프로세스 전에 찾으며, 시도의 프로세스의 status·출력은 그렇게 읽지 않는다(커널이 같은 것을 써서 자기 broken 결과를 tool failure로 바꿀 수 있으므로 — ADR-0168 결정 3, ADR-0110 결정 3). 답이 있을 때까지 벤더 백엔드는 기본 백엔드 표에 들지 않는다(GPU·장치를 쓰는 대상은 런타임 컨테이너에 그것을 여는 기록도 있어야 한다 — OD-33 ⑨의 나머지). [선택지 (a)] (i) 새 backend kind `device_unavailable` — probe가 쓸 수 있는 장치를 찾지 못했다는 뜻의 tool failure, `correctness.check`·`sim.run`·`board.run` 공통, 끝 줄의 `failure`에 저장 (ii) 기존 `executable_unstartable`로 읽는다(기존 값의 뜻 변경) (iii) broken `exit_status`(변경 없음, 그러나 시도의 탓). [쟁점 (b)] 주어진 코드를 평가한다면(같은 task의 OD-33 ① HQ) 그 기록. [선택지 (b)] (i) 코드를 CAS blob으로 두고 `artifacts.json`에 새 `type` `given_code`의 레코드(`type`은 ADR-0005 결정 5의 열린 형식), `instance.json`에 그 해시를 담는 멤버 `given_code` — 그 파일의 `schema_version`이 오른다(ADR-0018 결정 2) (ii) OD-33 ①의 답 뒤에 다른 형식으로 다시 묻는다. 실행자의 권고(결정 아님): (a) (i) — 시도에 대해 아무것도 확인되지 않았다, (b) (i). [막히는 것] 벤더 백엔드를 기본 표에 넣는 것(P3-9의 장치 없음 응답 — 쟁점 (a)), P3-11의 기록. [막히지 않는 것] P3-8과 P3-9의 나머지, P3-10, P3-13, P2-15 확인, 그 밖의 task.

**Coverage**: ADR-0194 decision 10's table. Not asked again: the coder's role and the "C 커널" wording (HQ-0088), the unit list and memory figures (HQ-0090), another vendor's tools (D29 already answers). No draft repeats a question in `STATE.json`.

### §9 notice

Posted on #5 by the executor after landing (AC10): https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6602545962
