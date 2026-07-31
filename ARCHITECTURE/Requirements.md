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
| **FR-9** | **correctness 검증**을 제공한다(비트정확 아님; reference numeric / downstream metric / user-defined + tolerance). *(검증 harness 강건화 = 미결 → OD-16; 정확도의 제약/목적 위치 = OD-5)* | UC-2, 설계노트 §B.3 | 공통 |
| **FR-10** | **HW 실험 도구**를 MCP/Bash로 노출한다: `sim.run`(저비용 조기검증), `board.run`(고비용·공유·quota), `profiler.collect`, `correctness.check`. | UC-2·3, 설계노트 §C.2 | 공통 |
| **FR-11** | 최적화 과정 전반에 **로그**를 남기고, 어떤 기법을 왜 선택했는지 **결정 로그를 강제 기록**한다(재현·감사용). | README, UC-6 | 공통 |
| **FR-12** | **외부 연구 논문·코드를 이해**하여 기법 후보군을 추가/갱신/삭제할 수 있어야 한다("AI for Science"-like). | README, UC-5 | 공통 |
| **FR-13** | **상태/지식을 세션 밖으로 외부화**한다. P1에서는 **Git repo 내 디렉토리 트리가 DB를 대신**하며, 레이아웃은 **미래 DB 스키마를 미러링**한다(`db/<hw_profile_key>/<op_signature>/...`). P2에서 Local DB로 마이그레이션한다. | UC-1·4·6, Issue#2 Phase 분할, README | P1→P2 |
| **FR-14** | **외부 참조 자료의 MCP 접근**: HW 스펙·벤더 문서·release된 SW 코드 등 외부에 별도 저장된 참조 자료는 HIL-Claw 내부에 복제 저장하지 않고 **MCP 도구로 접근**한다. ① 참조 소스별 MCP 서버/어댑터를 등록하는 방식을 제공하며, repo에는 원본이 아닌 **소스 등록부(포인터·접근 방법)** 만 둔다. ② 재현성(NFR-2, NFR-7③)을 위해 run 중 실제 참조한 자료의 **식별자+버전(또는 해시)을 결정 로그·instance 기록에 남기고**, 필요 시 발췌 스냅샷을 run 산출물로 캐시한다(원본 복제가 아닌 참조 증빙). ③ 외부 소스 불가용 시의 동작(캐시 폴백/실패 처리)을 정의한다. *(소스 목록·어댑터 계약·캐시 정책 = 미결 → OD-12, #5 B-1 연계)* | 사용자 지시(2026-07-31), #5 B-1 | 공통 |

---

# Non-Functional Requirements

| ID | 요구사항 | 근거 |
|---|---|---|
| **NFR-1 내구성** | 상태를 세션 컨텍스트 밖(STATE 파일/git, P2는 DB)으로 외부화하여, compaction·프로세스 사망과 무관하게 정확한 지점에서 재개 가능해야 한다. | UC-3·4 |
| **NFR-2 재현성·감사성** | 모든 결정·산출물을 추적 가능해야 한다. P1에서는 git history/diff가 감사 로그를 겸한다. 모델 결정의 비결정성은 결정 로그 강제 기록으로 보완한다. | UC-6, FR-11 |
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

| # | 미결 항목 | 관련 | 상태 | 논의 위치 · 현재 제안 |
|---|---|---|---|---|
| OD-1 | **Objective type 메뉴**의 최종 목록 및 각 type별 **best/improving 순서관계**(다목적: scalarization vs Pareto frontier, 제약형 feasibility 처리) | FR-2, D1 | 차단됨 | #5 A-4 — 제안: MVP는 "단일 목적 + 선택적 제약(메모리 상한)"만, 가중조합/Pareto는 후속 |
| OD-2 | **Budget 어휘에 HW quota**(sim 시간/board 시간) 포함 여부 | FR-3, D3 | 제안됨 | #7 §6 — board-second를 1급 예산 축으로 포함 권고(trial 수는 비용이 균일하지 않아 분모로 부적합) |
| OD-3 | **Gate 후보 목록** + 모드별 기본 구성(autonomous에서도 강제되는 안전 gate 존재 여부) | FR-4, D4 | 차단됨 | #5 A-5 · #7 §6 — 제안: **비-설정형 최소 gate 4종**(승격 게이트 / 신규 바이너리 첫 실물 실행 / board health 실패 / roofline 위반). "autonomous"는 탐색에 gate 없음이지 실물 승격에 없음이 아님 |
| OD-4 | **hw_profile / op_signature 키 필드 스키마** + 유사도 매칭(정확 일치 vs 최근접) 규칙. P1 디렉토리 명명에 즉시 필요. | FR-7·13, D10/D11 | 제안됨 | #4 코멘트 · #7 §6 — 제안: **2층 구조**. 정확 식별층(op: 정규화 IR 구조해시+전체 인자튜플+dtype/layout, hw: 칩+리비전+**펌웨어·드라이버·툴체인 버전**) + 유사도 벡터층(FLOPs, 이동 바이트, arithmetic intensity, working set÷SRAM…). 정확일치=캐시히트, 최근접=**prior로만**. TVM/TenSet 선례 |
| OD-5 | **정확도-성능 trade-off 정책**: 정확도를 제약(floor)으로 둘지 목적의 한 축으로 둘지 | FR-9 | 차단됨 | #5 A-6 · #7 §5 G1 — **최우선 권고: hard floor**(+ MLPerf식 downstream 지표 floor 병행). 목적 축으로 두면 옵티마이저에 정확도를 팔 권한을 명시 부여하는 것이며 외부 사례(Sakana 철회, METR 프록시-온리 73.8%)가 결과를 이미 보여줌 |
| OD-6 | **codegen spec 페이로드** 정의(커널 명세, hw_profile, 직전 라운드 프로파일/에러, 적용 기법 지침) + repair 코더 **resume vs 재기동** | FR-5, D7/쟁점4 | 논의중 | #4 §4 첫 항목(resume 여부는 §3b에서 "phase=coded 체크포인트 resume"으로 정리됨) · #7 — spec을 coder-driver **입출력 계약의 부분집합**으로 흡수 권고. 추가 권고: 직전 라운드만이 아니라 **top-k/bottom-k 시도와 프로파일을 대조적으로** 실어야(CUDA-L1 근거) |
| OD-7 | **기법 통계 환류 경로**: 정적 Skill 트리거에 동적 크로스런 통계를 피드백하는 구체 메커니즘(P1 랭킹 신호 정의 포함) | FR-7·8, D5/D6/쟁점1·2 | 제안됨 | #4 코멘트 · #7 §6 — 제안: 빈도 카운트가 아니라 **contextual bandit**(OpenTuner AUC-Bandit: 최근 개선 빈도 곡선의 AUC + UCB). latency 모델 없이 1라운드부터 동작. 카탈로그 승격은 **실측 검증 통과분만**(Voyager 근거) |
| OD-8 | **P1 디렉토리 레이아웃** 확정(OD-3·OD-4·C-3 결과 반영) | FR-13 | 차단됨 | #4 §2 레이아웃 초안 존재 · #5 A-1 확정(별도 data repo) 반영 필요 · **#5 A-2·B-4가 첫 커밋을 막고 있음** |
| OD-9 | **frontend IR 출처·포맷**: `model_ref`(format-agnostic frontend 결과 IR)를 어떤 frontend/포맷(예: ONNX/StableHLO/TOSA)에서 받는지, 시스템 경계 안/밖 여부 | FR-1, Issue#2 | 차단됨 | #5 B-5 |
| OD-10 | **board 실패·회복 모델**: board 행/크래시/예약 경합 시 재시도·타임아웃·회복 정책(측정 노이즈와 별개) | FR-10, NFR-3 | 제안됨 | #5 B-2 입력 필요 · #7 §6 — 제안: **브로커/트래커**(키별 큐, TVM RPC Tracker형) + **health check**(LAVA형, 실패 시 보드 격리) + **candidate-fault vs board-fault 구분**(후자를 "이 기법이 나쁘다"로 기록하면 지식베이스 오염) + quarantine·백오프 |
| OD-11 | **버전·마이그레이션 정책**: `schema_version` 부여 범위(어떤 아티팩트까지), 하위호환 읽기 보장 vs 마이그레이션 도구 제공의 경계, 시스템 버전이 바뀐 뒤 구버전 run 재개(FR-6)의 검증 방법 | NFR-7 | 제안됨 | #4 코멘트 · #7 §6 — **NFR-7①(라운드 경계 핫스왑)과 점수 비교가능성이 충돌**한다는 점이 추가 확인됨. 제안: **측정 계약**(harness 버전·tolerance·warmup/repeat 정책·roofline 모델)을 Loop instance마다 pin하고 모든 eval 레코드에 해시 기록, 변경 시 incumbent **재측정** 강제 |
| OD-12 | **외부 참조 MCP 어댑터 설계**: 대상 소스 목록(벤더 문서 포털/release repo/내부 문서 시스템), 어댑터 계약(검색·조회·버전 질의), 참조 증빙 기록 포맷, 캐시 폴백·retention 정책 | FR-14, #5 B-1 | 차단됨 | #5 B-1 · #4 코멘트 · #7 §8 — 추가 제약: 검색은 **해킹 벡터이기도 하므로** 권한을 orchestrator/curator에 한정하고 **코더 서브프로세스에는 금지**(ByteDance 선례). FR-14 ②의 식별자+해시 기록은 best effort가 아니라 hard precondition |
| OD-13 | **측정·노이즈 정책 구체화**(NFR-3의 "구체 정책 = 미결"을 등록부로 승격): 반복 횟수 결정 방식, 판정 통계량, 개선 인정 기준, 원시 샘플 보존, warmup/steady-state 처리 | NFR-3, FR-10 | 제안됨 | #7 §5 G2 — 제안: **적응적 반복**(throughput 변동계수 <5%에서 중단, n∈[5,30]) · **trimmed mean**(min 금지) · **paired interleaved 측정 + 비율의 부트스트랩 95% CI 전체가 1+δ 초과 시에만 개선 인정, δ=2%** · **per-repeat 원시 벡터 저장** · 고정 warmup 폐기하고 **steady-state 검출·라벨링** · 클럭/온도/펌웨어 기록, 후보 순서 무작위화 |
| OD-14 | **샌드박스·격리·보드 안전 정책 구체화**(NFR-4의 "구체 정책 = 미결"을 등록부로 승격): 생성 코드 실행 격리, 타임아웃 계층, 자원 상한, 보드 health·복구·격리 | NFR-4, FR-10 | 제안됨 | #7 §5 G1 — 제안: **1 후보 = 1 프로세스**(치명적 오류를 겪은 디바이스 컨텍스트는 오염되어 이후 측정 전부 무효) · **계층 타임아웃**(커널 워치독 < 호출 < 서브프로세스 SIGKILL < 라운드 < run) · 디바이스 메모리/그리드 상한 선언 · 후보 간 health check와 reset 에스컬레이션 · 보드를 멈춘 후보는 **content hash로 영구 blacklist**(FR-6 재개도 준수) |
| OD-15 | **sim→board 승격 기준**: 어떤 조건에서 시뮬레이터 결과를 실물 측정으로 승격시킬지 | FR-1, C-4 | 제안됨 | #7 §6 — 제안: **고정 임계값 금지**. (hw_profile, op_class)별 **rank correlation·recall@k를 측정해서** 승격 폭 k 결정. compute-bound와 memory-bound는 다른 k 필요. **sim이 거부한 후보용 ε-greedy 슬롯 상시 확보**(없으면 sim 편향을 영구히 감지 불가) · 매 라운드 sim/board 상관 추적, 열화 시 gate 발동 · **board 측정만이 기록(record)을 세울 수 있음** |
| OD-16 | **검증 harness 강건화(anti-reward-hacking)**: FR-9를 확장할지 별도 FR로 승격할지 + 구체 방어책 채택 범위 | FR-9, NFR-4 | 제안됨 | #7 §5 G1 — **본 조사 최대 리스크**. 제안: 측정 harness를 코더 사정권 밖(별도 프로세스·경로 deny) · **순서 의존성 테스트** · **roofline(speed-of-light) 상한 검사** · trial마다 새 할당·무작위 입력(관측 불가 시드) · **held-out private metrics** · 벤더 라이브러리 fallback 금지 정적 검사 · 승격 전 적대적 재검증 · hacker-fixer 루프로 자기 harness 사전 강화 |
| OD-17 | **실행 내구성 정책**: 라운드 재개 시 비용 이중 지출 방지, 예산 계상 방식, 동시 실행 방어 | NFR-1, FR-3, #4 §2e·§3b | 제안됨 | #4 코멘트 · #7 §5 G4 — 제안: 지출 전 `intent` + 후 `result` 이벤트를 **idempotency key**로 묶기 · **`budget_spent`를 저장값이 아니라 `events.ndjson` fold로 유도**(STATE.json은 재생성 가능한 materialized view) · `lock{owner,heartbeat}`는 fencing 없는 lease라 불안전하므로 **읽은 STATE commit SHA를 expected parent로 CAS push**하여 git을 fencing 수단으로 사용 · 도구별 **선언적 재시도 정책**(모델 판단 금지) |
| OD-18 | **강제 계층(hooks) 및 라운드 경계 정의**: 규범을 프롬프트가 아닌 하네스로 강제하는 범위, 라운드=프로세스 경계 채택 여부 | FR-11, NFR-4·5·7 | 제안됨 | #4 코멘트 · #7 §5 G5 — 제안: `SessionStart`(STATE·예산·gate 주입) · `PreToolUse`(board.run 예산·중복·gate 검사, harness 경로 deny) · `PostToolUse`(**결과 저널링은 모델 행동이면 안 됨**) · `Stop`(commit 강제) · `PreCompact` 차단 · `AGENT_STOP` kill switch · **default-FAIL 계약**과 **Write 권한 없는 fresh-context 평가자**. **`.claude/agents/`가 세션 중 재탐지되지 않으므로 NFR-7①은 "1 round = 1 OS process = 1 turn = 1 commit"일 때만 성립** |
