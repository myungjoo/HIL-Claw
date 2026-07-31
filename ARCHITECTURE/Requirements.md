주어진 [UsageCases](UsageCases.md)로부터 본 과제에서 적용할 요구사항을 기술하는 문서이다.

근거 표기: **README** = [../README.md](../README.md) 목표, **UC-n** = UsageCases, **Issue#2** = 아키텍처 토론 확정 결정(D1/D3/D4/codegen 위임/Phase 분할 등). Phase 표기: **P1** = Git tree 단계, **P2** = Local DB 단계, **공통** = 둘 다.

---

# 0. 범위 (Scope)

- 본 문서는 **MVP "방법 B"(Claude Code Orchestrator)** 만 다룬다.
- **방법 A(DeepAgents/LangGraph)는 "HIL-Claw 2"로 이연**하며 요구사항에서 제외한다(→ C-5). 단, 방법 B의 인터페이스는 미래 승격이 쉽도록 외부화한다(→ NFR-6).

---

# Functional Requirements

| ID | 요구사항 | 근거 | Phase |
|---|---|---|---|
| **FR-1** | **HIL 라운드 루프**를 제공한다: `기법 선택 → 코드 생성(위임) → compile → sim(조기검증) → (승격) board(최종측정) → profile → evaluate → 저장 → 다음 라운드 결정`. *(sim→board 승격 기준 = 미결 → OD-15)* | UC-1·2·3, README | 공통 |
| **FR-2** | 최적화 목표를 시스템이 고정하지 않고, **선택 가능한 target type 메뉴(vocabulary)** 로 제공하여 **Loop instance별로 사용자가 지정**한다. | UC-1, Issue#2 D1 | 공통 |
| **FR-3** | **Budget 어휘**를 제공한다: ① loop-iteration 수 ② 토큰 수(비용) ③ wall-clock 시간 ④ target-performance-metric(달성 시 조기 종료). 값은 run 시점 사용자 지정. 복수 지정 시 **any 소진 → 종료**. 시스템 기본 종료 의미론은 **budget 소진 + best 유지**. | UC-1·3, Issue#2 D3 | 공통 |
| **FR-4** | **자율성 gate 모델**: autonomous(gate 0) ↔ checkpoint(gate N). gate 집합은 **Loop instance 파라미터**로 사용자가 구성한다. autonomous도 budget/종료 조건까지 무정지 실행, checkpoint는 gate에서 정지·승인 대기. | UC-2·3, Issue#2 D4 | 공통 |
| **FR-5** | **코드 생성은 자체 수행하지 않고 headless Claude Code CLI(`claude -p`)에 위임**한다. compile 실패 repair도 위임 호출이다. Orchestrator→코더 전달 **spec을 1급 인터페이스**로 정의한다. | UC-1, Issue#2 codegen 위임 결정 | 공통 |
| **FR-6** | 최적화 산출물을 **중간·최종·실패 전부** 영구 저장하고, **임의 중간/완료 지점에서 재개**할 수 있어야 한다(추가 최적화·다른 기법 분기 포함). | UC-4·6, README | 공통 |
| **FR-7** | 기법 카탈로그에 **적용 가능성 메타데이터**(언제 쓰면 좋은지 = 선택 기준)를 함께 저장하고, 과거 (hw_profile, op_signature) 사례 통계로 후보를 **랭킹하여 Exhaustive Search를 회피**한다. | README, UC-2·5 | 공통 |
| **FR-8** | 기법 표현은 **Skill(선택 기준) + 카탈로그(적용 지침·크로스런 통계)** 하이브리드로 한다. 선택 기준은 Orchestrator 세션에서 트리거에, 적용 지침은 코더 spec에 실린다. P1에서는 기법 후보 = repo 내 문서로 시작. | Issue#2 쟁점2, README | 공통 |
| **FR-9** | **correctness 검증**을 제공한다(비트정확 아님; reference numeric / downstream metric / user-defined + tolerance). *(검증 harness 강건화 = 미결 → OD-16; 정확도의 제약/목적 위치 = OD-5)* | UC-2, Issue#2 §C.2 *(검증 방식 어휘는 §B.3 도구 계약에서 유래하나 §B.3은 방법 A 절이므로 C-5에 따라 근거에서 제외)* | 공통 |
| **FR-10** | **HW 실험 도구**를 MCP/Bash로 노출한다: `sim.run`(저비용 조기검증), `board.run`(고비용·공유·quota), `profiler.collect`, `correctness.check`. | UC-2·3, Issue#2 §C.2 | 공통 |
| **FR-11** | 최적화 과정 전반에 **로그**를 남기고, 어떤 기법을 왜 선택했는지 **결정 로그를 강제 기록**한다(재현·감사용). | README, UC-6 | 공통 |
| **FR-12** | **외부 연구 논문·코드를 이해**하여 기법 후보군을 추가/갱신/삭제할 수 있어야 한다("AI for Science"-like). | README, UC-5 | 공통 |
| **FR-13** | **상태/지식을 세션 밖으로 외부화**한다. P1에서는 **데이터 plane의 디렉토리 트리가 DB를 대신**하며(소스 repo와 분리 — #5 A-1; 물리적 바인딩은 `hilclaw.config.json`이 지정), 레이아웃은 **미래 DB 스키마를 미러링**한다(`db/<hw_profile_key>/<op_signature>/...`). P2에서 Local DB로 마이그레이션한다. *(데이터 plane의 구체 형태 = 별도 repo / fork / template 파생 중 미결 → #4 「repo 구조 단순화」 안건. 확정 시 본 문구 재검토)* | UC-1·4·6, Issue#2 Phase 분할, #5 A-1, README | P1→P2 |
| **FR-14** | **외부 참조 자료의 MCP 접근**: HW 스펙·벤더 문서·release된 SW 코드 등 외부에 별도 저장된 참조 자료는 HIL-Claw 내부에 복제 저장하지 않고 **MCP 도구로 접근**한다. ① 참조 소스별 MCP 서버/어댑터를 등록하는 방식을 제공하며, repo에는 원본이 아닌 **소스 등록부(포인터·접근 방법)** 만 둔다. ② 재현성(NFR-2, NFR-7③)을 위해 run 중 실제 참조한 자료의 **식별자+버전(또는 해시)을 결정 로그·instance 기록에 남기고**, 필요 시 발췌 스냅샷을 run 산출물로 캐시한다(원본 복제가 아닌 참조 증빙). ③ 외부 소스 불가용 시의 동작(캐시 폴백/실패 처리)을 정의한다. *(소스 목록·어댑터 계약·캐시 정책 = 미결 → OD-12, #5 B-1 연계)* | 사용자 지시(2026-07-31), #5 B-1 | 공통 |

---

# Non-Functional Requirements

| ID | 요구사항 | 근거 |
|---|---|---|
| **NFR-1 내구성** | 상태를 세션 컨텍스트 밖(STATE 파일/git, P2는 DB)으로 외부화하여, compaction·프로세스 사망과 무관하게 정확한 지점에서 재개 가능해야 한다. | UC-3·4 |
| **NFR-2 재현성·감사성** | 모든 결정·산출물을 추적 가능해야 한다. 특히 **결과에서 그것을 만든 도구·설정 버전을 역추적할 수 있어야 한다**. P1에서는 git history/diff가 그 기록을 겸하되, **데이터 plane과 소스가 분리되어 있으므로 어느 한쪽 history만으로는 감사 로그가 성립하지 않는다** — 둘을 잇는 고리(`instance.json`에 소스 commit 기록, #5 A-1 세부 3 · NFR-7③)가 필수다. 모델 결정의 비결정성은 결정 로그 강제 기록으로 보완한다. | UC-6, FR-11, #5 A-1 |
| **NFR-3 측정 신뢰성** | board 성능 측정의 분산(노이즈)을 고려하여 반복 측정/신뢰구간 등으로 점수 안정성을 확보한다. *(구체 정책 = 미결 → OD-13)* | UC-2 |
| **NFR-4 안전·격리** | 생성된 커널 코드의 실행(특히 실제 board)에 sandbox·timeout·리소스 가드를 둔다. 중첩 `claude -p`(코더) 인스턴스의 작업 디렉토리 격리·권한 범위·실패/타임아웃 처리를 규정한다. *(구체 정책 = 미결 → OD-14)* | Issue#2 쟁점3 |
| **NFR-5 비용 통제** | 코더에 별도 모델 지정이 가능해야 하며, Orchestrator/코더로 분산되는 토큰·비용을 집계할 수 있어야 한다. | Issue#2 쟁점3·4 |
| **NFR-6 확장성** | STATE/spec/HW 도구/카탈로그/DB 스키마 인터페이스를 외부화하여, P2 Local DB 및 미래 HIL-Claw 2(방법 A) 승격이 **오케스트레이션 레이어 교체만으로** 가능하도록 설계한다. | Issue#2 §D |
| **NFR-7 진화 가능성(Evolvability)** | 본 시스템은 개념이 증명되지 않은 채 실사용에 투입되므로 **운용 중 지속적 개선·개조를 1급 요구사항**으로 한다: ① 시스템 구성요소(orchestrator 지침, subagent 정의, Skill, 커맨드, 도구 계약)는 **라운드 경계(stateless turn 경계)에서 교체·수정 가능**해야 하며 진행 중 run을 깨뜨리지 않아야 한다. ② 모든 영속 아티팩트(STATE/spec/eval/db 레코드)는 `schema_version`을 가지며 구버전 데이터의 읽기 또는 마이그레이션이 보장되어야 한다 — **FR-6 재개는 시스템 버전이 달라진 후에도 성립**해야 한다. ③ 어떤 시스템 버전이 어떤 결과를 만들었는지 추적 가능해야 한다(instance.json의 소스 commit 기록, Issue#5 A-1 세부 3). ④ 개선 방향의 근거가 되는 관측(결정 로그·실패 통계)이 축적·조회 가능해야 한다(FR-11, NFR-2 연계). *(버저닝·마이그레이션 세부 정책 = 미결 → OD-11)* | 사용자 지시(2026-07-31), Issue#2 유지보수·진화 항목, Issue#4 §1 |

---

# Constraints

| ID | 제약 |
|---|---|
| **C-1** | 벤더 종속: 방법 B는 Claude Code/Anthropic 하네스에 종속된다(MVP에서 수용). |
| **C-2** | P1은 **단일 run 전제**. 동시 다중 run은 P2로 이연(Issue#2 D17). |
| **C-3** | 대용량 산출물 정책: 바이너리·중간 산출물을 전부 git에 넣으면 repo가 비대화된다. P1 레이아웃 결정 시 **Git LFS vs (메타·프로파일=git) + (바이너리=로컬 캐시 + 해시 참조)** 중 택1을 포함하고, 실패/중간 산출물의 retention/GC 정책을 둔다. |
| **C-4** | HW 자원: board는 공유·제한 자원이고 sim은 저비용 조기검증 수단이다. |
| **C-5** | **방법 A(DeepAgents/LangGraph)는 HIL-Claw 2로 이연** — 본 MVP의 non-goal. |
| **C-6** | MVP 범위는 **단일 compute-kernel 최적화**. 커널→whole-model 바이너리 합성(그래프 레벨 연산자 merge 등)은 후속 범위. |

---

# Open Decisions (미결 — 구체 설계 단계에서 확정)

발명하지 않고 명시적으로 남긴다. 각 항목은 관련 FR 및 Issue#2 결정 ID와 연결된다.

**본 표가 미결 항목의 단일 등록부(registry)다.** 논의가 이슈에 흩어져도 각 항목의 현재 상태와 논의 위치는 여기서 확인할 수 있어야 한다.

**이슈 역할 분담**: **#4** = 아키텍처·실행모델 결정 스레드 · **#5** = 사용자만 답할 수 있는 입력 대기(A/B 항목) · **#7** = 외부 시스템 조사·분석(상설) · **#1** = 참고문헌 메모.

**상태 어휘**: `미착수` 논의 없음 · `논의중` 논의 진행, 제안 미수렴 · `제안됨` 구체 제안 존재, 오너 확정 대기 · `차단됨` #5의 사용자 입력 대기 · `확정` 결정 완료(본문 반영 커밋 링크 필수).

**갱신 규칙**: 상태가 바뀌면 **본 표를 같은 커밋에서 갱신**한다. 확정 시 행을 지우지 말고 상태를 `확정`으로 바꾸고 반영 위치를 남긴다(감사성 NFR-2).

**정본 규칙**: **OD 항목의 제안·상태·논의 위치는 본 표가 정본**이다. 이슈·코멘트에는 **표를 복제하지 말고 링크만** 둔다. (사본을 두었더니 등록부 개편 직후 번호가 어긋나 별도 정정이 필요했다 — 갱신 지점이 늘면 반드시 어긋난다.)

**등록 범위**: 본 표는 **미결 "결정"** 만 담는다. 결정이 아닌 **작업**(예: 부트스트랩 골격 작성)은 여기 넣지 않고 이슈에서 작업 항목으로 추적한다 — 섞으면 표가 진척 관리용으로 변질된다.

| # | 미결 항목 | 관련 | 상태 | 논의 위치 · 현재 제안 |
|---|---|---|---|---|
| OD-1 | **Objective type 메뉴**의 최종 목록 및 각 type별 **best/improving 순서관계**(다목적: scalarization vs Pareto frontier, 제약형 feasibility 처리) | FR-2, D1 | 차단됨 | #5 A-4 — 제안: MVP는 "단일 목적 + 선택적 제약(메모리 상한)"만, 가중조합/Pareto는 후속 |
| OD-2 | **Budget 어휘에 HW quota**(sim 시간/board 시간) 포함 여부 | FR-3, D3 | 제안됨 | #7 §6 — board-second를 1급 예산 축으로 포함 권고(trial 수는 비용이 균일하지 않아 분모로 부적합) |
| OD-3 | **Gate 후보 목록** + 모드별 기본 구성(autonomous에서도 강제되는 안전 gate 존재 여부) | FR-4, D4 | 차단됨 | #5 A-5 · #7 §6 — 제안: **비-설정형 최소 gate 4종**(승격 게이트 / 신규 바이너리 첫 실물 실행 / board health 실패 / roofline 위반). "autonomous"는 탐색에 gate 없음이지 실물 승격에 없음이 아님 |
| OD-4 | **hw_profile / op_signature 키 필드 스키마** + 유사도 매칭(정확 일치 vs 최근접) 규칙. P1 디렉토리 명명에 즉시 필요. | FR-7·13, D10/D11 | 제안됨 | #4 코멘트 · #7 §6 — 제안: **2층 구조**. 정확 식별층(op: 정규화 IR 구조해시+전체 인자튜플+dtype/layout, hw: 칩+리비전+**펌웨어·드라이버·툴체인 버전**) + 유사도 벡터층(FLOPs, 이동 바이트, arithmetic intensity, working set÷SRAM…). 정확일치=캐시히트, 최근접=**prior로만**. TVM/TenSet 선례 |
| OD-5 | **정확도-성능 trade-off 정책**: 정확도를 제약(floor)으로 둘지 목적의 한 축으로 둘지 | FR-9 | 차단됨 | #5 A-6 · #7 §5 G1 — **최우선 권고: hard floor**(+ MLPerf식 downstream 지표 floor 병행). 목적 축으로 두면 옵티마이저에 정확도를 팔 권한을 명시 부여하는 것이며 외부 사례(Sakana 철회, METR 프록시-온리 73.8%)가 결과를 이미 보여줌 |
| OD-6 | **codegen spec 페이로드** 정의(커널 명세, hw_profile, 직전 라운드 프로파일/에러, 적용 기법 지침) + repair 코더 **resume vs 재기동** | FR-5, D7/쟁점4 | 논의중 | #4 §4 첫 항목(resume 여부는 §3b에서 "phase=coded 체크포인트 resume"으로 정리됨) · #7 — spec을 coder-driver **입출력 계약의 부분집합**으로 흡수 권고. 추가 권고: 직전 라운드만이 아니라 **top-k/bottom-k 시도와 프로파일을 대조적으로** 실어야(CUDA-L1 근거) |
| OD-7 | **기법 통계 환류 경로**: 정적 Skill 트리거에 동적 크로스런 통계를 피드백하는 구체 메커니즘(P1 랭킹 신호 정의 포함) | FR-7·8, D5/D6/쟁점1·2 | 제안됨 | #4 코멘트 · #7 §6 — 제안: 빈도 카운트가 아니라 **contextual bandit**(OpenTuner AUC-Bandit: 최근 개선 빈도 곡선의 AUC + UCB). latency 모델 없이 1라운드부터 동작.<br>**흡수: 카탈로그 진입 기준**(#7 보충 §2(4)) — 등재 자격 = (held-out correctness 통과) ∧ (실 board 측정) ∧ (격리 평가자 PASS). selector·coder의 주장만으로는 불가하며, **검증 없이 쌓으면 카탈로그가 부패한다**(Voyager ablation: 자가검증 제거 시 버그 코드가 스킬 라이브러리에 축적). ExpeL식 `cases/`(불변 사례) + `insights/`(가변 규칙, ADD/EDIT/UPVOTE/DOWNVOTE + `supported_by` 출처) 분리 검토 |
| OD-8 | **P1 디렉토리 레이아웃** 확정(OD-3·OD-4·C-3 결과 반영) | FR-13 | 차단됨 (후보 1건) | #4 §2 레이아웃 초안 존재 · #5 A-1 확정(별도 data repo) 반영 필요 · **#5 A-2·B-4가 첫 커밋을 막고 있음**.<br>**후보 ①「레이아웃 = 권한 모델」**: 에이전트마다 **쓰기 루트 1개**를 지정하고 **그 외 전부 read-only**(읽기는 무제한 — 읽기 제한은 채택하지 않음). *(OD-16과의 관계: OD-16이 은닉이 아닌 **위조 불가능성** 기반으로 개정되어 충돌 없음. 단 **런타임 시드·입력 값은 파일로 존재하지 않아야** 한다 — 이것이 읽기 개방의 유일한 전제. 또한 **코더/평가 프로세스 분리**가 OD-16 위협 A(조작 계열)를 담당한다.)* ⑴ `rounds/<N>/`을 **소유자별로 분할** — `decision/`(technique-selector) · `coder/`(반입 게이트가 채움, 코더는 직접 못 씀) · `measure/`(experiment-runner) · `eval/`(evaluator). 현행 §2 평면 구조는 evaluator가 `board.json`을 덮어쓸 수 있어 single-writer 위반. ⑵ 폴더 모델 **밖의 특수 케이스 3**: `.git/`(에이전트 전원 쓰기 금지 — 이력 재작성 = 감사 로그 파괴, NFR-2), `events.ndjson`(도구 계층이 append하므로 에이전트 쓰기 권한 불필요), `TMPDIR`·빌드 캐시(쓰기 루트 안에 둘 것 — 누락 시 빌드 실패). ⑶ 쓰기 루트는 **라운드로 파라미터화하되 에이전트가 선택 불가**, supervisor가 주입. ⑷ 강제 백엔드 2개(정책은 하나): 코더 = **OS 경계**(저장소 read-only 마운트 + scratch, 셸 허용), in-process subagent = **`PreToolUse` 경로 검사**(→ Bash 금지, 특권 동작은 타입 있는 도구로: `sim.run`/`board.run`/`coder.run`). ⑸ **흡수: per-agent tools allowlist**(#4 §6) — frontmatter 도구 허용목록은 경로 정책의 도구 단위 표현이므로 본 후보와 함께 확정한다. **이점**: 권한이 문서가 아니라 디렉토리 구조에 새겨져 git diff 검증이 자명해지고, `.claude/` 재귀 문제(강제 장치가 강제 대상 안에 있음)가 부수적으로 해소되며, **OD-14와 사실상 같은 결정으로 수렴**. **전제조건**: 대상 toolchain의 **out-of-tree 빌드 지원 여부**(#5 B-1) — 인플레이스 빌드 강제 시 저장소를 scratch로 복사 후 diff 반입하는 우회 필요(라운드마다 복사 비용) |
| OD-9 | **frontend IR 출처·포맷**: `model_ref`(format-agnostic frontend 결과 IR)를 어떤 frontend/포맷(예: ONNX/StableHLO/TOSA)에서 받는지, 시스템 경계 안/밖 여부 | FR-1, Issue#2 | 차단됨 | #5 B-5 |
| OD-10 | **board 실패·회복 모델**: board 행/크래시/예약 경합 시 재시도·타임아웃·회복 정책(측정 노이즈와 별개) | FR-10, NFR-3 | 제안됨 | #5 B-2 입력 필요 · #7 §6 — 제안: **브로커/트래커**(키별 큐, TVM RPC Tracker형) + **health check**(LAVA형, 실패 시 보드 격리) + **candidate-fault vs board-fault 구분**(후자를 "이 기법이 나쁘다"로 기록하면 지식베이스 오염) + quarantine·백오프 |
| OD-11 | **버전·마이그레이션 정책**: `schema_version` 부여 범위(어떤 아티팩트까지), 하위호환 읽기 보장 vs 마이그레이션 도구 제공의 경계, 시스템 버전이 바뀐 뒤 구버전 run 재개(FR-6)의 검증 방법 | NFR-7 | 제안됨 | #4 코멘트 · #7 §6 — **NFR-7①(라운드 경계 핫스왑)과 점수 비교가능성이 충돌**한다는 점이 추가 확인됨. 제안: **측정 계약**(harness 버전·tolerance·warmup/repeat 정책·roofline 모델)을 Loop instance마다 pin하고 모든 eval 레코드에 해시 기록, 변경 시 incumbent **재측정** 강제 |
| OD-12 | **외부 참조 MCP 어댑터 설계**: 대상 소스 목록(벤더 문서 포털/release repo/내부 문서 시스템), 어댑터 계약(검색·조회·버전 질의), 참조 증빙 기록 포맷, 캐시 폴백·retention 정책 | FR-14, #5 B-1 | 차단됨 | #5 B-1 · #4 코멘트 · #7 §8 — 추가 제약: 검색은 **해킹 벡터이기도 하므로** 권한을 orchestrator/curator에 한정하고 **코더 서브프로세스에는 금지**(ByteDance 선례). FR-14 ②의 식별자+해시 기록은 best effort가 아니라 hard precondition |
| OD-13 | **측정·노이즈 정책 구체화**(NFR-3의 "구체 정책 = 미결"을 등록부로 승격): 반복 횟수 결정 방식, 판정 통계량, 개선 인정 기준, 원시 샘플 보존, warmup/steady-state 처리 | NFR-3, FR-10 | 제안됨 | #7 §5 G2 — 제안: **적응적 반복**(throughput 변동계수 <5%에서 중단, n∈[5,30]) · **trimmed mean**(min 금지) · **paired interleaved 측정 + 비율의 부트스트랩 95% CI 전체가 1+δ 초과 시에만 개선 인정, δ=2%** · **per-repeat 원시 벡터 저장** · 고정 warmup 폐기하고 **steady-state 검출·라벨링** · 클럭/온도/펌웨어 기록, 후보 순서 무작위화 |
| OD-14 | **샌드박스·격리·보드 안전 정책 구체화**(NFR-4의 "구체 정책 = 미결"을 등록부로 승격): 생성 코드 실행 격리, 타임아웃 계층, 자원 상한, 보드 health·복구·격리 | NFR-4, FR-10 | 제안됨 | #7 §5 G1 — 제안: **1 후보 = 1 프로세스**(치명적 오류를 겪은 디바이스 컨텍스트는 오염되어 이후 측정 전부 무효) · **계층 타임아웃**(커널 워치독 < 호출 < 서브프로세스 SIGKILL < 라운드 < run) · 디바이스 메모리/그리드 상한 선언 · 후보 간 health check와 reset 에스컬레이션 · 보드를 멈춘 후보는 **content hash로 영구 blacklist**(FR-6 재개도 준수). **쓰기 범위 정책은 OD-8 후보 ①(「레이아웃 = 권한 모델」)과 동일 결정으로 수렴** — 거기서 함께 확정할 것 |
| OD-15 | **sim→board 승격 기준**: 어떤 조건에서 시뮬레이터 결과를 실물 측정으로 승격시킬지 | FR-1, C-4 | 제안됨 | #7 §6 — 제안: **고정 임계값 금지**. (hw_profile, op_class)별 **rank correlation·recall@k를 측정해서** 승격 폭 k 결정. compute-bound와 memory-bound는 다른 k 필요. **sim이 거부한 후보용 ε-greedy 슬롯 상시 확보**(없으면 sim 편향을 영구히 감지 불가) · 매 라운드 sim/board 상관 추적, 열화 시 gate 발동 · **board 측정만이 기록(record)을 세울 수 있음** |
| OD-16 | **측정·검증의 위조 불가능성(anti-reward-hacking)**: FR-9를 확장할지 별도 FR로 승격할지 + 방어책 채택 범위 | FR-9, NFR-4 | 제안됨 | #7 §5 G1 — **본 조사 최대 리스크**. **원칙(2026-07-31 개정): 은닉이 아니라 위조 불가능성.** 전부 읽혀도 성립하는 방어만 채택한다(Kerckhoffs). 유일한 예외는 **런타임 시드·입력 값이 파일로 존재하지 않을 것** — 알고리즘은 읽혀도 되고 값만 없으면 된다. → **읽기 제한은 채택하지 않으며 OD-8 후보 ①과 충돌하지 않는다.** 근거: 성능 최적화 시스템에서 정답을 알아도 **베끼면 speedup 1.0이라 이길 수 없고**, harness 은닉은 security-by-obscurity이며(루프홀은 소스를 읽어야만 발견되지 않는다 — 없애는 것이 진짜 방어), 문서·기존 커널 읽기는 저밀도 언어 대응(FR-14)과 콜드스타트(OD-22)에 오히려 필요하다.<br>**위협 A — 조작 계열**(출력 버퍼 절도 · harness/타이머 패치 · 점수 레코드 조작 · 감사 로그 조작): **코더와 평가를 별도 프로세스로 분리 + 쓰기 격리**로 소멸한다(OD-8 후보 ① / OD-14). Sakana 사건의 버퍼 절도는 reference와 후보가 같은 프로세스에서 버퍼를 공유했기 때문에 성립했다.<br>**위협 B — 산출물 퇴화 계열**(생성 커널이 일을 하지 않음): 치팅이 코더의 정당한 산출물인 소스 안에 있으므로 **격리로는 잡히지 않고 측정 설계로 잡는다**. ⑴ 하드코딩 출력 → **매 trial 런타임 무작위 입력**(값 비파일화) ⑵ 계산 누락 → 오라클 강화(FP32/FP64 CPU 레퍼런스 · opschema 기반 퍼징 · per-(op,dtype) tolerance · 코너케이스 subnormal/zero/inf/NaN/catastrophic cancellation) ⑶ 벤더 라이브러리 디스패치 → **정적 검사**(규칙이 읽혀도 무방 — 우회하려면 위반해야 하고 위반은 탐지된다) + **프로파일러로 해당 커널의 실제 실행 확인** ⑷ 다른 큐/스레드로 회피 → 전체 디바이스 배리어 + 호스트 wall-clock 교차검증 + **roofline(speed-of-light) 상한** ⑸ **타이밍 반복 구간 캐싱**(정확도는 입력을 바꾸지만 성능 측정은 같은 입력을 N회 반복하는 것이 정상이라 열리는 틈) → 매 trial 새 버퍼 할당 · 캐시 플러시 · **1회차 이후 시간 급감 탐지** ⑹ **순서 의존성 테스트**(reference→candidate와 candidate→reference 결과가 다르면 실격).<br>**`private_metrics` 재정의**: 은닉 지표가 아니라 **일반화 측정 지표** — 평가에는 쓰되 최적화 대상에는 넣지 않는다. 실배포에서는 대상 shape 분포를 코더에게 알리는 편이 맞다(벤치마크와 위협 모델이 다름).<br>**방어가 여전히 필요한 이유**: 코더가 악의를 갖기 때문이 아니라 **탐색 루프가 가장 싼 경로를 고르기 때문**이다. 루프홀이 있으면 결국 선택되고, 그 결과는 board 시간 낭비 · **크로스런 통계 오염(FR-7)** · 잘못된 바이너리 승격이다.<br>**흡수: 조기 종료 재검증**(#7 보충 §2(2), #8 M18) — FR-3 ④의 target 조기 달성은 해킹된 결과의 전형적 징후이므로 조기 종료 인정 전 승격 게이트 수준의 재검증을 강제할 것.<br>**잔여 미결**: 정적 검사 규칙의 범위 · roofline 모델 산출 방법(op_signature별 FLOPs/바이트) · 승격 전 적대적 재검증의 강도 · hacker-fixer 루프로 자기 harness를 사전 강화할지 |
| OD-17 | **실행 내구성 정책**: 라운드 재개 시 비용 이중 지출 방지, 예산 계상 방식, 동시 실행 방어 | NFR-1, FR-3, #4 §2e·§3b | 제안됨 | #4 코멘트 · #7 §5 G4 — 제안: 지출 전 `intent` + 후 `result` 이벤트를 **idempotency key**로 묶기 · **`budget_spent`를 저장값이 아니라 `events.ndjson` fold로 유도**(STATE.json은 재생성 가능한 materialized view) · `lock{owner,heartbeat}`는 fencing 없는 lease라 불안전하므로 **읽은 STATE commit SHA를 expected parent로 CAS push**하여 git을 fencing 수단으로 사용 · 도구별 **선언적 재시도 정책**(모델 판단 금지) |
| OD-18 | **강제 계층(hooks) 및 라운드 경계 정의**: 규범을 프롬프트가 아닌 하네스로 강제하는 범위, 라운드=프로세스 경계 채택 여부 | FR-11, NFR-4·5·7 | 제안됨 | #4 코멘트 · #7 §5 G5 — 제안: `SessionStart`(STATE·예산·gate 주입) · `PreToolUse`(board.run 예산·중복·gate 검사, harness 경로 deny) · `PostToolUse`(**결과 저널링은 모델 행동이면 안 됨**) · `Stop`(commit 강제) · `PreCompact` 차단 · `AGENT_STOP` kill switch · **default-FAIL 계약**과 **Write 권한 없는 fresh-context 평가자**. **`.claude/agents/`가 세션 중 재탐지되지 않으므로 NFR-7①은 "1 round = 1 OS process = 1 turn = 1 commit"일 때만 성립**.<br>**흡수: CLAUDE.md 불변식 목록**(#4 §6) — 세션 기동 시 강제할 규범 목록 확정. 현재까지 나온 것: "agent-memory 전체를 삭제해도 FR-6·FR-7·NFR-2가 성립한다" · "전 디렉토리 스캔 금지, STATE.json이 유일 진입점"(#4 §1) |
| OD-19 | **예산 집행(enforcement) 정책**: FR-3의 "소진 → 종료"를 실제로 강제하는 수단. OD-17(계상)과는 별개 항목 | FR-3, FR-5, NFR-5 | 제안됨 | #7 보충 §2(1), #8 M5 — NFR-5는 "집계할 수 있어야 한다"까지만 요구하여 **다음 지출을 막는 경로가 요구사항 어디에도 없다**. 제안: 검사를 **다음 지출의 경로 위에** 둘 것 · run 예산과 별도로 **라운드당 상한 + 코더 호출 횟수 상한** · 오케스트레이터와 모든 중첩 `claude -p`를 **단일 원장**에 합산하고 spawn 전 확인(중첩이 비용 증폭 경로) · 원장을 세션 밖에 영속(재개된 run이 자기 예산을 0으로 리셋 불가) · **무진전 서킷브레이커**(N라운드 연속 미개선 시 중단) |
| OD-20 | **후보 아카이브 스키마**: `best_ref` 단일 포인터를 유지할지 **후보 집단(아카이브)** 을 저장할지 + 저장 필드 확정 | FR-6·7·13 | 제안됨 | #7 보충 §2(3) — README의 "중간 지점 재개·완료 후 다른 방법으로 추가 최적화" 요구는 **사실상 아카이브 요구**인데 현재 best 하나 + 통계로 축소되어 있고, 단일 포인터는 greedy hill-climb이다. 제안 필드: 계보(`parent_id`·`generation`·`children_count`) · **단계별 분리 평가**(`compile_ok`/`correct`/`sim_metrics`/`board_metrics`+`board_evaluated`) · **`public_metrics` vs `private_metrics`**(후자는 LLM 미노출 — 해킹·과적합 트립와이어) · **생성 프롬프트 보존**(재현·감사·프롬프트 크레딧) · 아티팩트 타입 필드(임계 이하 인라인) · 행동 기술자(score-signature = 워크로드별 결과 튜플, 임베딩 불요) · **실패 보존 필수** |
| OD-21 | **탐색 폭(라운드당 후보 수)**: 라운드당 1후보 직렬을 유지할지, N후보 생성 후 상위만 board로 승격할지 | FR-1, C-4, #4 §3d | 제안됨 | #7 §5 G3·§7(**즉시 개선 1순위**), #8 M16 — board 직렬성은 **평가 처리량만** 제약하고 생성·컴파일·sim은 제약하지 않으므로 **board 비용 증가 0으로 best-of-N** 확보 가능. #4 §3d("병렬은 sim까지만 의미 있음 → MVP는 Round 직렬")와 정면 대립하며 **같은 사실에서 반대 결론**을 낸다. 단계적 도입 권고: ①N-후보 → ②아카이브 가중 parent 샘플링 → ③islands/MAP-Elites(post-MVP). 반대 근거도 존재(단순 병렬 샘플링이 진화적 기법을 따라잡았다는 보고) |
| OD-22 | **기법 카탈로그 콜드스타트**: 실행 이력이 0인 상태에서 카탈로그를 채우는 방법 | FR-8, UC-5 | 제안됨 | #7 보충 §2(5) — FR-8의 "P1에서는 기법 후보 = repo 내 문서로 시작"(손으로 쓴 문서)보다 나은 검증된 방법 2가지: **optimization rewind**(대상 HW의 known-good 전문가 커널을 체계적으로 **역최적화**해 bad→good 궤적에서 전이 가능한 모티프를 채굴, retrievable experience bank로) · **git 이력 채굴**(기존 커널 라이브러리의 개발 이력에서 최적화 아이디어를 형식화). 둘 다 UC-5 큐레이터 흐름에 그대로 들어감 |
| OD-23 | **subagent 로스터 및 입출력 계약**: 에이전트 종류 확정 + 각 에이전트의 입력·출력 파일 스키마 | #4 §3a·§6, NFR-6 | 논의중 | #4 §6 첫 두 항목 · #7 §2(8) — 현재 5종(technique-selector / coder-driver / experiment-runner / evaluator / promoter)이 #4 개정 코멘트로 제시됨. 미결: experiment-runner를 sim/board로 분리할지 · `technique-selector`·`promoter`를 **인라인**할지(subagent는 fresh context라 라운드마다 STATE·카탈로그 재로드 비용을 곱으로 지불) · **`evaluator`는 반대로 강화**(실험 수행 주체가 아닐 것, Write 권한 없음, 아티팩트 경로+해시만 수신). 입출력 계약은 **방법 A 노드 스펙으로 기계 번역 가능**해야 함(NFR-6). **OD-6(codegen spec)은 coder-driver 계약의 부분집합으로 흡수** |
| OD-24 | **agent-memory → db 승격 트리거**: 에이전트별 서술적 요령이 언제·어떤 형식으로 정량 신호가 되어 크로스런 지식으로 승격되는지 | FR-7, NFR-2, #4 데이터 계층 정책 | 미착수 | #4 §6 · #4 데이터 계층 코멘트 — 승격 사다리(agent-memory → 개인 db → 공유 db → 카탈로그/Skill)의 **첫 단계 조건이 미정**. OD-7(통계 환류)·OD-20(아카이브 스키마)과 인접하므로 함께 볼 것 |
| OD-25 | **데이터 거버넌스**: 데이터 plane의 물리 형태(별도 repo / 1-repo+fork / template 파생) + 공유 계층 승격 PR 정책 | FR-13, NFR-2, #5 A-1 | 차단됨 (오너 확정 대기) | #4 코멘트 2건 — ⑴ **「repo 구조 단순화(1-repo + upstream-fork)」 안건**: 분석 결과 **기각 권고**(같은 계정 self-fork 불가로 P1 부트스트랩 모순 · private repo fork는 권한 상실 시 삭제되어 자산 수명이 소스 접근권에 종속 · public 전환 시 fork를 private로 둘 수 없어 HW 특성·실패 이력이 강제 공개) ⑵ **대안 = template 모델**(HIL-Claw-data를 template repository로 지정, fork 대신 파생 생성 — private 가능·수명 독립·레이아웃 표준 자동 획득) + 후속 3건(template 지정 시점 · 경량 승격 경로 · 개인 repo의 template 버전 메타 규약) ⑶ **공유 main 승격 PR 정책**(자동 머지 범위 vs 사람 리뷰 범위). **#5 A-1 확정(2-repo)이 현행 기준**이며 본 안건 채택 시 A-1 재개봉 필요. FR-13 문구도 이 결정에 연동 |
