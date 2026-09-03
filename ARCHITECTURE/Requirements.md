주어진 [UsageCases](UsageCases.md)로부터 본 과제에서 적용할 요구사항을 기술하는 문서이다.

근거 표기: **README** = [../README.md](../README.md) 목표, **UC-n** = UsageCases, **Issue#2** = 아키텍처 토론 확정 결정(D1/D3/D4/codegen 위임/Phase 분할 등), **S0-n** = [StandardScenarios.md](StandardScenarios.md) 기본 전제 시나리오의 단계, **(Gn)** = StandardScenarios 커버리지 검사에서 발견되어 백필된 갭, **S7~S10 / (Bn)** = 확장 시나리오 및 문헌 검토 보강 제안(2026-09-03; "확장 고려" 메모는 MVP 구현 대상이 아님). Phase 표기: **P1** = Git tree 단계, **P2** = Local DB 단계, **공통** = 둘 다.

---

# 0. 범위 (Scope)

- 본 문서는 **MVP "방법 B"(Claude Code Orchestrator)** 만 다룬다.
- **방법 A(DeepAgents/LangGraph)는 "HIL-Claw 2"로 이연**하며 요구사항에서 제외한다(→ C-5). 단, 방법 B의 인터페이스는 미래 승격이 쉽도록 외부화한다(→ NFR-6).

---

# Functional Requirements

| ID | 요구사항 | 근거 | Phase |
|---|---|---|---|
| **FR-1** | **HIL 라운드 루프**를 제공한다: `기법 선택 → 코드 생성(위임) → compile → sim(조기검증) → (승격) board(최종측정) → profile → evaluate → 저장 → 다음 라운드 결정`. instance 시작 시 **라운드 0 = bring-up**(해당 HW에서 동작하는 코드 생성) + **baseline 성능 측정**을 수행하며, 이것이 이후 라운드 evaluate의 기준이 된다. | UC-1·2·3, README, S0-4 (G1) | 공통 |
| **FR-2** | 최적화 목표를 시스템이 고정하지 않고, **선택 가능한 target type 메뉴(vocabulary)** 로 제공하여 **Loop instance별로 사용자가 지정**한다. | UC-1, Issue#2 D1 | 공통 |
| **FR-3** | **Budget 어휘**를 제공한다: ① loop-iteration 수 ② 토큰 수(비용) ③ wall-clock 시간 ④ target-performance-metric(달성 시 조기 종료). 값은 run 시점 사용자 지정. 복수 지정 시 **any 소진 → 종료**. 시스템 기본 종료 의미론은 **budget 소진 + best 유지**. | UC-1·3, Issue#2 D3 | 공통 |
| **FR-4** | **자율성 gate 모델**: autonomous(gate 0) ↔ checkpoint(gate N). gate 집합은 **Loop instance 파라미터**로 사용자가 구성한다. autonomous도 budget/종료 조건까지 무정지 실행, checkpoint는 gate에서 정지·승인 대기. | UC-2·3, Issue#2 D4 | 공통 |
| **FR-5** | **코드 생성은 자체 수행하지 않고 headless Claude Code CLI(`claude -p`)에 위임**한다. compile 실패 repair도 위임 호출이다. Orchestrator→코더 전달 **spec을 1급 인터페이스**로 정의한다. | UC-1, Issue#2 codegen 위임 결정 | 공통 |
| **FR-6** | 최적화 산출물을 **중간·최종·실패 전부** 영구 저장하고, **임의 중간/완료 지점에서 재개**할 수 있어야 한다(추가 최적화·다른 기법 분기 포함). | UC-4·6, README | 공통 |
| **FR-7** | 기법 카탈로그에 **적용 가능성 메타데이터**(언제 쓰면 좋은지 = 선택 기준)를 함께 저장하고, 과거 (hw_profile, op_signature) 사례 통계로 후보를 **랭킹하여 Exhaustive Search를 회피**한다. | README, UC-2·5 | 공통 |
| **FR-8** | 기법 표현은 **Skill(선택 기준) + 카탈로그(적용 지침·크로스런 통계)** 하이브리드로 한다. 선택 기준은 Orchestrator 세션에서 트리거에, 적용 지침은 코더 spec에 실린다. P1에서는 기법 후보 = repo 내 문서로 시작. | Issue#2 쟁점2, README | 공통 |
| **FR-9** | **correctness 검증**을 제공한다(비트정확 아님; reference numeric / downstream metric / user-defined + tolerance). **최소 강건성 조항**: 최적화 과정에서 코더에 노출되지 않은 입력(shape/seed)으로, 코더가 수정할 수 없는 격리된 검증 하네스에서 재검증한다. 검증을 통과하지 못한 결과는 best·통계에 반영하지 않는다. 전면 하드닝(정밀도 검사·타이밍 동기화·정적 검사·LLM 검증자)은 확장(S7, OD-13). | UC-2, 설계노트 §B.3, S7 (B1) | 공통 |
| **FR-10** | **HW 실험 도구**를 MCP/Bash로 노출한다: `sim.run`(저비용 조기검증), `board.run`(고비용·공유·quota), `profiler.collect`, `correctness.check`. | UC-2·3, 설계노트 §C.2 | 공통 |
| **FR-11** | 최적화 과정 전반에 **로그**를 남기고, 어떤 기법을 왜 선택했는지 **결정 로그를 강제 기록**한다(재현·감사용). | README, UC-6 | 공통 |
| **FR-12** | **외부 연구 논문·코드를 이해**하여 기법 후보군을 추가/갱신/삭제할 수 있어야 한다("AI for Science"-like). | README, UC-5 | 공통 |
| **FR-13** | **상태/지식을 세션 밖으로 외부화**한다. P1에서는 **Git repo 내 디렉토리 트리가 DB를 대신**하며, 레이아웃은 **미래 DB 스키마를 미러링**한다(`db/<hw_profile_key>/<op_signature>/...`). P2에서 Local DB로 마이그레이션한다. | UC-1·4·6, Issue#2 Phase 분할, README | P1→P2 |
| **FR-14** | **HW 온보딩**을 제공한다: 새 hw_profile(가속기 + 호스트 환경)과 그 **Documentation**, sim/board 도구 접근 정보를 시스템(P1: db 트리)에 **등록**하고, instance 시작 시 **선택**할 수 있어야 한다. 절차·스키마 세부 = OD-11. | S0-1, UC-1 선행조건 (G2) | 공통 |
| **FR-15** | instance 시작 시 **(선택) 참고 사례·자료 입력**을 받을 수 있다: 내부 Storage의 기존 유사/동일 최적화 사례 참조, 외부 연구 논문 링크 등. **원칙**: 이 입력과 저장된 과거 사례는 **"참고사항"(탐색 우선순위 힌트)으로만** 사용한다 — **Ground Truth로 간주하지 않으며, 특히 기존 사례의 성능이 "최종 목표"가 되어서는 안 된다**. 목표는 오직 FR-2의 사용자 지정 target을 따른다(FR-7 랭킹에도 동일 원칙 적용). | S0-3 사용자 확정(2026-09-02) (G5·G6) | 공통 |
| **FR-16** | **알림**을 발행한다: run 종료(best 유지 종료·비수렴 종료), 강제 gate 정지 등 사용자 개입/인지가 필요한 이벤트 대상. 채널·메커니즘 세부 = OD-12. | UC-3·7 (G3) | 공통 |

---

# Non-Functional Requirements

| ID | 요구사항 | 근거 |
|---|---|---|
| **NFR-1 내구성** | 상태를 세션 컨텍스트 밖(STATE 파일/git, P2는 DB)으로 외부화하여, compaction·프로세스 사망과 무관하게 정확한 지점에서 재개 가능해야 한다. | UC-3·4 |
| **NFR-2 재현성·감사성** | 모든 결정·산출물을 추적 가능해야 한다. P1에서는 git history/diff가 감사 로그를 겸한다. 모델 결정의 비결정성은 결정 로그 강제 기록으로 보완한다. | UC-6, FR-11 |
| **NFR-3 측정 신뢰성** | board 성능 측정의 분산(노이즈)을 고려하여 반복 측정/신뢰구간 등으로 점수 안정성을 확보한다. *(구체 정책 = 미결)* | UC-2 |
| **NFR-4 안전·격리** | 생성된 커널 코드의 실행(특히 실제 board)에 sandbox·timeout·리소스 가드를 둔다. 중첩 `claude -p`(코더) 인스턴스의 작업 디렉토리 격리·권한 범위·실패/타임아웃 처리를 규정한다. *(구체 정책 = 미결)* *확장 고려(B8)*: 검증·프로파일 스크립트 보호(코더 수정 불가), 금지 fallback 패턴, 코더의 웹 검색 차단 여부 | Issue#2 쟁점3 |
| **NFR-5 비용 통제** | 코더에 별도 모델 지정이 가능해야 하며, Orchestrator/코더로 분산되는 토큰·비용을 집계할 수 있어야 한다. | Issue#2 쟁점3·4 |
| **NFR-6 확장성** | STATE/spec/HW 도구/카탈로그/DB 스키마 인터페이스를 외부화하여, P2 Local DB 및 미래 HIL-Claw 2(방법 A) 승격이 **오케스트레이션 레이어 교체만으로** 가능하도록 설계한다. 또한 StandardScenarios의 확장 시나리오(S7~S10)를 인터페이스가 구조적으로 배제하지 않아야 한다([확장 호환] 규칙). | Issue#2 §D, S7~S10 |

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

| # | 미결 항목 | 관련 |
|---|---|---|
| OD-1 | **Objective type 메뉴**의 최종 목록 및 각 type별 **best/improving 순서관계**(다목적: scalarization vs Pareto frontier, 제약형 feasibility 처리). *확장 고려(B2)*: HW 이론 한계(speed-of-light/roofline) 대비 달성률을 target·정지 어휘에 포함할지 | FR-2, D1 |
| OD-2 | **Budget 어휘에 HW quota**(sim 시간/board 시간) 포함 여부 | FR-3, D3 |
| OD-3 | **Gate 후보 목록** + 모드별 기본 구성(autonomous에서도 강제되는 안전 gate 존재 여부) | FR-4, D4 |
| OD-4 | **hw_profile / op_signature 키 필드 스키마** + 유사도 매칭(정확 일치 vs 최근접) 규칙. P1 디렉토리 명명에 즉시 필요. | FR-7·13, D10/D11 |
| OD-5 | **정확도-성능 trade-off 정책**: 정확도를 제약(floor)으로 둘지 목적의 한 축으로 둘지 | FR-9 |
| OD-6 | **codegen spec 페이로드** 정의(커널 명세, hw_profile, 직전 라운드 프로파일/에러, 적용 기법 지침) + repair 코더 **resume vs 재기동**. *확장 고려*: (B4) 프로파일 요약의 구조(병목 유형·점유율·memory/compute bound 판정), (B5) HW Documentation 발췌·같은 카테고리 예시 커널의 검색증강 전달, (S7) 금지 패턴 목록, (S8) 라운드당 후보 다중성을 spec이 배제하지 않을 것 | FR-5, D7/쟁점4 |
| OD-7 | **기법 통계 환류 경로**: 정적 Skill 트리거에 동적 크로스런 통계를 피드백하는 구체 메커니즘(P1 랭킹 신호 정의 포함). *확장 고려(B6)*: 저장 단위를 통계에 더해 "변환 전/후 코드 쌍 + 개선 이유 요약"으로 확장 | FR-7·8, D5/D6/쟁점1·2 |
| OD-8 | **P1 디렉토리 레이아웃** 확정(OD-3·OD-4·C-3 결과 반영). *확장 고려(S8)*: 라운드 아래 후보(candidate) 다중성을 레이아웃이 배제하지 않을 것 | FR-13 |
| OD-9 | **frontend IR 출처·포맷**: `model_ref`(format-agnostic frontend 결과 IR)를 어떤 frontend/포맷(예: ONNX/StableHLO/TOSA)에서 받는지, 시스템 경계 안/밖 여부 | FR-1, Issue#2 |
| OD-10 | **board 실패·회복 모델**: board 행/크래시/예약 경합 시 재시도·타임아웃·회복 정책(측정 노이즈와 별개) | FR-10, NFR-3 |
| OD-11 | **HW 온보딩 절차 세부**: hw_profile 등록 스키마(OD-4와 연동), Documentation 포맷·저장 위치, sim/board 도구 endpoint 기술 방법 | FR-14, OD-4 |
| OD-12 | **알림 채널·메커니즘**: 채널(콘솔/파일/외부 메신저 등), checkpoint gate 대기 알림과의 통합 여부 | FR-16 |
| OD-13 | **correctness 검증 수행 지점**: FR-1 라운드 시퀀스 내 위치(sim 후 / board 후 / 양쪽) 및 실패 시 라운드 처리. *확장 고려(B1/S7)*: 전면 하드닝(정밀도 하향 검사, warm-up·stream sync·클록 고정 타이밍, 정적 검사·금지 패턴, LLM 검증자) | FR-1·9 (G4) |
| OD-14 | **baseline 선택**: 라운드 0의 baseline을 bring-up 코드 / 벤더 라이브러리 커널 / 기존 best 중 instance 파라미터로 택할지. baseline에 따라 개선율의 의미가 달라짐 | FR-1 (B7) |
