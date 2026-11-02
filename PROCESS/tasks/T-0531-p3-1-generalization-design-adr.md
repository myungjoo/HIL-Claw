---
id: T-0531
title: Write the generalization design ADR for PLAN P3-1 and state the owner's parts as concrete questions
phase: P3
status: BLOCKED
commitMode: doc
coversReq: [D27, OD-32, C-6, NFR-6, "PLAN P3-1"]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 500, files: 4}
hq: [HQ-0086, HQ-0087]
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

- **Status: `BLOCKED`, review round limit (CLAUDE.md A-13; HQ-0086 (a) allowed one extra round; 8 rounds used, no Approve).** Not landed on `main`. Round 8 reviewed `664264f8` on branch `claude/T-0531-generalization-design-adr-r8` (rebased on `db796e05`; one squashed commit; the old branch `claude/T-0531-generalization-design-adr` at `01778ed1` is kept). Verdict Request changes: no Must-fix, no owner part decided, 3 Should-fix, 4 Nit. All three Should-fix come from `08711c70` (FR-19, OD-33, PLAN P3-7 to P3-12) and sit in owner-facing question text; the design decisions need no change. Nothing from round 8 is applied. The HQ drafts below stay drafts of an unaccepted record and are not to be registered yet.
- **Corrections to the drafts below, proposed by round 8 and NOT applied (need a reviewed round):**
  - **S1**: O1 ① (c) and its recommendation reason, ADR-0193 decision 2's "Waits on" cell and decision 9 O1: a real toolchain is needed only for real results and acceptance; development goes by the fake-toolchain path of P3-7 to P3-10 (FR-19 ⑤, D16). Keep the recommendation only on its remaining reasons.
  - **S1 is discarded (DRIVER D29, 2026-11-03).** The owner corrected its premise: drivers use the real toolchain on the machine, and no fake-toolchain path exists. Follow FR-19 item 5 and DRIVER section 6 "툴체인(D29)" instead. In O1 and decision 9, "no real toolchain" should read "no vendor toolchain", since compile settings also use a real compiler. The range "P3-7 to P3-12" in the ADR's Boundaries becomes "P3-7 to P3-13".
  - **S2**: O1's blocked list: add P3-12 (waits on OD-32 ⑦ besides its OD-33 answers); O1 ④ (a) does not release it.
  - **S3**: O3 and ADR-0193 decision 9: state how far the answer reaches into OD-33 ⑥ (unit list; memory figures of vendor targets only as the owner states). OD-33's wording is not edited.
  - **Nits**: N1 status date ranges of the OD-4, OD-13, OD-26, OD-31 rows; N2 ADR-0004, ADR-0009, ADR-0017, ADR-0052, ADR-0076, ADR-0117, ADR-0145, ADR-0186 missing from References; N3 O1 scenario option (c) absent from the ADR; N4 §9 notice omits ④'s data-plane side.
- **Rebase edits on the `-r8` branch beyond conflict resolution (reviewed in round 8)**: acceptance date 2026-11-03; session entry check and owner-sentence search updated for #5 comment 6572518011; Boundaries names P3-7 to P3-12, FR-19, OD-33; S12 added to the recheck; OD-32 row date 2026-11-03.
- **Round 7 state (history).** **Status: `BLOCKED`, review round limit (CLAUDE.md A-13; 7 rounds used, no Approve).** Not landed on `main`. Round 7 found no Must-fix and no owner part decided; it left 2 Should-fix and 3 Nit, all register consistency. All five are addressed on branch `claude/T-0531-generalization-design-adr` (tip after round 7), which **no reviewer has seen**. Rounds by verdict: 7 of 7 Request changes. To finish: an owner decision on another round (one review of the tip, then rebase, one commit with `Reviewed-by` and `Task: T-0531`, push to `main`). P3-1 is not to be checked until the ADR lands (PLAN P3-1). **The HQs below are drafts of an unaccepted record** and are for the driver to hold until then; only the BLOCKED question goes in now.
- **BLOCKED HQ draft**: `taskId` T-0531, `reason` `review-rounds-exceeded`, `question`: (A-13, 리뷰 7라운드 초과) [쟁점] T-0531의 ADR-0193이 7라운드에서 Approve를 받지 못했다. 7라운드의 지적은 Must-fix 0건, Should-fix 2건, Nit 3건으로 모두 등록부 정합성이고, 오너 몫을 정한 문장은 찾지 못했다. 그 지적은 브랜치 `claude/T-0531-generalization-design-adr`에 반영했으나 리뷰를 받지 않았다. [선택지] (a) 리뷰 1라운드를 더 허용하고 Approve면 land한다 (b) ADR을 더 작게 쪼개 처음부터 다시 한다 (c) 그 밖. 실행자의 권고(결정 아님): (a). [막히는 것] P3-1 체크, P3-2 이후 항목의 설계 근거, 아래 네 초안의 등재. [막히지 않는 것] P2-15 확인, P3 밖의 task.
- **ADR**: `ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md`. The English statement of each owner part is its decision 9 (O1 to O4, in the order of the drafts below).
- **Runtime acceptance items**: none. P3-3 and P3-4 register their own after landing.
- **Less exact, listed not edited**: the ADR's Consequences, "Less exact, not edited". Also PLAN P3-3 lists "측정 단위"·"데이터 타입" as differences, which ADR-0193 decision 4 reads with `ns` until O3 and a type subset unless O4 says otherwise.
- **Survey and dependency table**: ADR-0193 decisions 1 and 8. Sizes for the planner: P3-2 one task; P3-3 one, plus a small one on O3; P3-4 two; P3-5 two; P3-6 not sized.

### HQ drafts (for `PROCESS/STATE.json`, `askedAt` and `id` the driver's; `issueComment` null)

**Draft O1**: `taskId` T-0531, `reason` `owner-decision`, `question`:

(OD-32 ⑥·⑦과 ①의 범위, PLAN P3-6; 설계는 ADR-0193 결정 2·9) [쟁점] D27은 C 커널, 벤더 언어 커널, 양자화 설정, 컴파일 설정을 모두 후보로 다루기로 했으나 어느 것을 먼저, 누가 만들고, 어떤 단위로 평가하는지는 정하지 않았다. ① P3-6의 첫 커널 밖 종류: (a) 컴파일 설정 (b) 양자화 설정 (c) 벤더 언어 커널(#5 B-1의 실제 툴체인 필요) (d) 실제 대상이 정해질 때까지 P3-6을 하지 않음. ② 그 종류의 후보를 만드는 쪽: (a) 오케스트레이터의 선택 역할이 spec의 `task.build`에 적고 코더를 부르지 않음 (b) 코더(`claude -p`) (c) 결정적 도구가 열거. ③ CLAUDE.md 세 층 모델의 "C 커널" 문구를 바꾸는 때: (a) 첫 커널 밖 종류가 land될 때 (b) 지금. ④ 모델 단위 후보(양자화 등)의 instance 단위·산출물·품질 지표·평가 데이터: (a) 그 종류를 고를 때 묻는다 (b) 지금 정한다(값 지정). ⑤ 이 흐름의 새 시나리오: (a) 첫 종류가 land될 때 같은 작업에서 더한다 (b) 지금 정한다 (c) 두지 않는다. 실행자의 권고(결정 아님): ① (a), ② (a), ③ (a), ④ (a), ⑤ (a) — 컴파일 설정은 실제 툴체인과 새 품질 지표가 필요 없고 단일 커널 instance(C-6)에 맞는다. [막히는 것] P3-6. [막히지 않는 것] P3-2~P3-5, P2-15 확인, 그 밖의 task.

**Draft O2**: `taskId` T-0531, `reason` `data-plane-schema-change`, `question`:

(A-13 틀의 변경, OD-32 ①; ADR-0193 결정 9. P3-6의 첫 종류가 컴파일 설정일 때의 형식이며 — 그 선택은 같은 task의 다른 HQ가 묻는다 — 다른 답이면 이 질문은 그 답에 맞춰 다시 묻는다) [쟁점] 커널 밖 후보를 데이터 plane에 적는 형식과, 종류 목록의 지위. [제안 형식] ⓐ `instance.json`: 멤버 `candidate_kind`(name). 지나쳐 읽으면 컴파일 설정 run을 C 커널 run으로 다루게 되므로(ADR-0018 결정 2) 이 멤버가 있는 파일은 `schema_version` 2이고, C 커널 run은 멤버 없이 1 그대로이며, 읽는 쪽은 둘 다 받는다. ⓑ `spec.json`: `task.build`의 새 멤버는 버전을 올리지 않지만(ADR-0002 결정 7) spec은 코더 호출 하나의 입력이다(`id`, ADR-0002; `coder/…/spec.json`, ADR-0004). 그래서 코더를 부르지 않는 답이면 그 spec은 `id`의 뜻을 시도로 넓히고 그 파일의 작성자에 선택 역할을 더하는 뜻의 변경이어서 `schema_version` 3이고, C 커널 spec은 2 그대로이며, 읽는 쪽은 둘 다 받는다. 코더가 만드는 답이면 2 그대로다. 그런 시도의 커널은 아래 멤버가 가리키는 시도에서 읽고 자기 `output/`은 비어 있다. `task.build`에 `candidate_kind`(문자열), `flags`(문자열 배열). `flags`는 대상의 플래그에 더하는 것, `kernel_round`·`kernel_candidate`·`kernel_attempt`(정수)는 이 후보가 빌드하는 C 커널이 나온 시도. `candidate_kind`가 `compile_settings`이면 모두 필수. 선택지 — ① 종류의 단위: (a) instance당 한 종류 (b) 후보마다(이때 `instance.json` 멤버와 그 버전 변경은 없음). ② 실제로 빌드한 설정의 기록(이 종류에 대한 OD-6 ②·OD-18 ⑰ (다)의 답이기도 하다): (a) ADR-0004가 이미 정한 자리인 시도의 `measure/` 아래 `build.json`, 아직 어떤 코드도 쓰지 않는 그 파일을 이 종류에만 쓴다: `schema_version`(정수 1), `outcome`(`"built"` 또는 `"broken"`), `condition`(broken일 때만, 기존 값 `build_time_limit`·`build_exit_status`), `flags`·`trailing_flags`(문자열 배열, 정확한 인자) — 결과와 `step`은 그대로 (b) `artifacts.json`에 `type` `build_settings`인 레코드, blob은 인자 목록 — 결과와 `step`은 그대로(`type`은 ADR-0005 결정 5의 열린 형식)이나 ADR-0004의 자리 옆에 둘째 자리가 생긴다 (c) 결과에 멤버 `build_flags`, 새 `step` 값 `correctness_check_sim_v3`·`correctness_check_board_v3`·`sim_run_timing_v3`·`board_run_timing_v3`(ADR-0100). (c)는 C 커널 run의 결과도 바꾼다. 측정 단위를 묻는 HQ에서 새 `step` 값을 함께 고르면 `sim_run_timing_v3`·`board_run_timing_v3`의 정의는 두 변경을 합친 하나이고 함께 land된다. ③ `candidate_kind` 값 목록(첫 값 `c_kernel`·`compile_settings`): (a) DRIVER §3의 열린 목록으로 지정 — 값은 §9 ADR이 A-13 읽기에 이 목록을 밝히고 더하되 내용이 오너 몫인 값(벤더 언어, 양자화)은 여전히 묻는다 (b) 닫힌 목록으로 두고 오너가 매번 넓힌다. ④ 위 형식 전체: (a) 승인 (b) 고쳐서 승인(내용 지정) (c) 그 밖. 실행자의 권고(결정 아님): ① (a), ② (a), ③ (a), ④ (a). ② (a)이면 C 커널 run의 파일과 결과는 지금과 같다. [막히는 것] P3-6의 기록. [막히지 않는 것] P3-2~P3-5, P2-15 확인, 그 밖의 task.

**Draft O3**: `taskId` T-0531, `reason` `data-plane-schema-change`, `question`:

(A-13 틀의 변경, OD-32 ②·③; HQ-0078 ⑤가 "HW 대상 설계 때 오너가 정한다"고 남긴 것; ADR-0193 결정 4·9) [쟁점] `sim.run`·`board.run` 결과의 `unit`은 지금 `"ns"` 하나의 닫힌 값이다(ADR-0183 결정 4). D27은 가상 NPU의 측정 단위를 CPU와 다르게 두기로 했다. [선택지] (a) `unit`을 DRIVER §3의 열린 목록으로 지정, 첫 값 `ns`·`cycles`, 새 `step` 값 `sim_run_timing_v3`·`board_run_timing_v3`(ADR-0100)을 모든 대상에 쓰고 읽는 쪽은 v2와 v3를 모두 읽는다; `cpu_standin`은 계속 `ns`, 값은 §9 ADR이 A-13 읽기에 이 목록을 밝히고 더한다 (b) 같은 목록을 v2 `step` 값 그대로 넓힌다(ADR-0100의 예외) (c) 지금은 하지 않고 실제 대상 때까지 `ns`만 둔다 — 이때 P3-3의 측정 단위 차이는 없는 것으로 P3-3을 닫는다. (a)·(b)이면 `virtual_npu`의 `cycles`는 자기 ns에 고정 배수를 곱한 검사용 값이며 실제 NPU의 근거가 아니고, 비교는 run 하나의 한 단위 안에서만 하며, ADR-0103의 거친 시계 검사도 한 단위 안에서만 뜻이 있다. (a)·(b)이면 함께 답할 것 — 이 목록이 메모리 수치에도 미치는가(ADR-0183이 오너 몫으로 남김): (가) 아니다, `intervals`·`resolution`에만 미치고 `memory_bytes`는 형식 그대로 (나) 미친다(형식 지정). 실행자의 권고(결정 아님): (a), (가). [막히는 것] P3-3의 "측정 단위 차이"와 P3-3의 체크. [막히지 않는 것] P3-3의 나머지(`ns`로 진행), P3-2·P3-4·P3-5, P2-15 확인, 그 밖의 task.

**Draft O4**: `taskId` T-0531, `reason` `owner-decision`, `question`:

(OD-32 ③, FR-9, #5 B-7, OD-31 ③; ADR-0193 결정 4·9. fp16은 묻지 않는다 — HQ-0083 (b), D27 ④) [쟁점 ①] FR-9는 시스템 생성 reference를 `cpu_standin`에 한해 확정으로 적고(HQ-0004) B-7의 일반 답이 아니라고 한다. 가상 NPU의 검사에 무엇을 쓸지는 답해지지 않았다. [선택지 ①] (a) bf16 계약의 기존 reference와 사용자가 정하는 허용 오차를 이 검사용 백엔드에 한해 그대로 쓰고, `instance.json`의 요구 멤버는 `cpu_standin`과 같게 한다(B-7의 일반 답이 아님) (b) 가상 NPU에서는 correctness를 검사하지 않고 instance 시작 아래의 빌드와 측정만 쓴다 (c) 그 밖. [쟁점 ②] 가상 NPU는 새 형식 없이도 CPU와 데이터 타입이 다를 수 있다 — bf16 여섯 계약만 받고 fp32 `gemm`을 거부한다. 다만 CPU에 없는 타입을 갖는 것은 새 수치 형식으로만 된다. [선택지 ②] (a) 새 형식 없음: 지원 집합의 차이만 데이터 타입의 차이로 본다 (b) 검사용 새 `dtype` 값 `int8`을 `elementwise_add` 한 kind에 계약 표 항목 하나로 더하고 `virtual_npu`만 받는다(연산의 뜻은 그 항목의 기록이 정함; 실제 NPU의 근거가 아님) (c) 양자화 설정을 후보로 다루기로 정할 때 함께 정한다. 실행자의 권고(결정 아님): ① (a), ② (a). [막히는 것] `virtual_npu`에서의 `correctness.check`와 instance 시작(①), P3-3의 체크(② (b)이면 그 항목까지). [막히지 않는 것] P3-3의 나머지(대상 항목, 백엔드, 플래그, 메모리, 대상별 범위, 시작 아래의 `sim.run`·`board.run`), P3-2·P3-4·P3-5, P2-15 확인, 그 밖의 task.

**Coverage**: ADR-0193 decision 9's table. Not reached, with the reason: OD-32 ④'s data-plane part (no record of a model-level run exists, OD-31 ⑧), the registry and real targets under ② (OD-26, #5 B-1 and B-2; no P3 item needs them). No draft repeats a question in `STATE.json`.

### §9 notice for the driver to post on #5 (last line as DRIVER §8 asks)

**Notice (PROCESS/DRIVER.md §9): ADR-0193 accepted** (commit: pending). It gives the generalization design of PLAN P3 and answers part of OD-32 sub-questions ②, ③ and ④ and all of ⑤; it adds the `virtual_npu` table entry under OD-26, for a check backend only. It also sets a memory bound and call-level time limits for `virtual_npu`'s process containers only (OD-14 sub-question ①), serves the six bf16 contracts unchanged at that check backend only (OD-31 ①), and sets that backend's hw key values, among them `revision` (OD-4), and its timing seed's source (OD-13 ⑦). OD-32 stays open: ①, ⑥, ⑦ and the owner's parts of ② and ③, with the oracle at `virtual_npu`, are put to you as HQs in `PROCESS/STATE.json`. Your D27 answer is cited and not subject to objection. You have not confirmed the rest, and may object within 7 days of this notice; an objection creates a task that reverts the record and the edits made with it. Readings to check: the target table in source, one set per `accelerator` (decision 3); the C kernel path's reading of the loop (decision 2); `s6_metric` left out of the lifted lists and `instance_start` as the place of the start's admission (decisions 1 and 3); `virtual_npu`'s values, memory bound and `model_run` false, none a fact about a real NPU (decision 4); the type subset as the data-type difference (decision 4); the graph file outside the data plane, beside the unchanged forward program (decision 5); four kinds generated, two handwritten, and fp32 `gemm` handwritten for its other form, not for difficulty (decision 6). Nothing here changes what your P2-15 check runs.

— posted by driver
