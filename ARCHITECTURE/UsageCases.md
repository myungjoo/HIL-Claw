이 문서는 ARCHITECTURE DESCRIPTION 중 가장 첫번째로 진행되는 Item으로서 Requirement 확보 및 정제의 근원이 되는 문서이다.

본 문서는 [README](../README.md)의 목표와 Issue #2(아키텍처 토론)에서 확정된 결정사항을, **MVP인 "방법 B"(Claude Code 자신이 Orchestrator)** 범위로 한정하여 유스케이스로 정리한다.

---

# 0. 범위 (Scope)

- **In-scope**: 방법 B — Claude Code가 Long-Horizon Orchestrator가 되고, **상태는 Git repo(Phase 1) → Local DB(Phase 2)** 로 외부화한다. 코드 생성은 headless Claude Code CLI(`claude -p`)에 위임한다.
- **MVP 단계 분할**
  - **Phase 1**: 별도 DB 없이 **Git repo 내 디렉토리 트리가 DB를 대신**한다. 디렉토리 레이아웃은 미래 DB 스키마를 미러링한다. 단일 run 전제.
  - **Phase 2**: 실제 Local DB 도입. Phase 1 레이아웃을 그대로 마이그레이션.
- **Out-of-scope (Non-goal)**: 방법 A(DeepAgents/LangGraph 기반 별도 Agent System)는 **"HIL-Claw 2"** 로 이연한다. 방법 B가 완료되고 모든 동작이 원활히 검증된 이후에 착수한다. 본 문서에서 방법 A는 다루지 않으며, 다만 방법 B의 인터페이스(STATE/spec/도구/카탈로그)는 미래 HIL-Claw 2 승격이 쉽도록 외부화한다(→ [Requirements](Requirements.md) NFR-확장성).

---

# 1. 용어 (Glossary)

- **Loop instance**: 사용자가 *(특정 HW + 특정 모델 + 최적화 target + (선택) budget + (선택) gate 구성)* 을 주고 실행한 개별 최적화 건. 시스템이 목표를 일괄 고정하지 않는다.
- **Round**: 한 번의 최적화 시도 1회. `기법 선택 → 코드 생성(위임) → compile → sim → (승격) board → profile → evaluate → 저장 → 다음 결정`.
- **Gate**: 루프 진행 중 사용자 승인/지시를 기다리는 정지 지점. autonomous = gate 0개, checkpoint = gate N개. gate 구성은 instance 파라미터다.
- **hw_profile**: 성능 특성을 결정하는 HW/실행 환경 키(가속기 + 호스트 환경 튜플). 구체 필드 스키마는 미결(→ Requirements Open Decisions).
- **op_signature**: 최적화 대상 연산의 식별 키. 구체 필드 스키마는 미결.
- **기법 카탈로그(technique catalog)**: 최적화 기법 후보군과 "언제 쓰면 좋은지(선택 기준)" 및 적용 지침·과거 통계를 담는 자료. Phase 1에서는 repo 내 문서로 시작.

---

# 2. 액터 (Actors)

| 액터 | 설명 | 주 모드 |
|---|---|---|
| **배포 엔지니어** | 특정 HW에 모델을 올리려는 주 사용자. 새 HW/모델 초기 탐색, 고가 board run을 직접 감독. | checkpoint (인터랙티브) |
| **CI / 헤드리스 배치** | 야간·무인 최적화를 구동하는 자동화 주체. `claude -p`. | autonomous |
| **기법 큐레이터** | 외부 연구 논문/코드를 이해해 기법 후보군을 추가/갱신하는 사용자(또는 연구자). | 인터랙티브 |
| **(외부 위임 코더)** | Orchestrator가 호출하는 headless 코드 생성 인스턴스. 사람 액터는 아니나 시스템 경계 밖 협력자. | — |

---

# 3. 유스케이스

## UC-1. Loop instance 정의·실행
- **액터**: 배포 엔지니어 / CI
- **선행조건**: 대상 HW(hw_profile)와 모델, 사용 가능한 sim/board 도구가 등록되어 있음.
- **주 흐름**
  1. 사용자가 *(HW + 모델 + 최적화 target type + (선택) budget + (선택) gate 구성 + autonomy 모드)* 를 지정해 instance를 시작한다.
  2. 시스템이 instance용 작업공간(`/runs/<run_id>/` 또는 Phase 2 DB 레코드)을 만들고 STATE를 초기화한다.
  3. 라운드 루프(UC-2 또는 UC-3)로 진입한다.
- **종료조건**: budget 소진 또는 (선택) target-metric 조기 달성. 기본 종료 의미론은 **best 결과 유지**.
- **비고**: 목표 type은 메뉴(vocabulary)에서 선택한다. 예: latency 최소화 / throughput 최대화 / 동시 서빙 capacity 최대화 / 메모리 상한 내 latency 최소화(제약형) / 가중 조합. *(메뉴 최종 확정 = 미결)*

## UC-2. 인터랙티브 최적화 (checkpoint 모드)
- **액터**: 배포 엔지니어
- **선행조건**: instance가 checkpoint 모드, gate 집합이 정의됨.
- **주 흐름**
  1. 한 라운드를 실행: 기법 선택 → 코드 생성(외부 위임) → compile → sim.
  2. 정의된 **gate**(예: real-board 첫 투입 전 / 기법군 전환 / budget 50% 소진)에 도달하면 정지하고 사용자 승인을 기다린다.
  3. 사용자가 승인/거부/방향 수정을 입력하면 진행한다(승격 시 board 측정 → profile → evaluate).
  4. 결과·로그를 저장(commit)하고 다음 라운드 여부를 결정한다.
- **대안 흐름**: 사용자가 거부하면 해당 기법군을 건너뛰거나 instance를 중단한다.
- **종료조건**: budget 소진 / 사용자 종료 / target 달성.
- **비고**: 도구 권한 승인 UI가 곧 HIL gate로 동작한다. *(gate 후보 목록·기본 구성 = 미결)*

## UC-3. 무인 최적화 (autonomous 모드)
- **액터**: CI / 헤드리스 배치
- **선행조건**: instance가 autonomous 모드, 권한 자동 승인.
- **주 흐름**
  1. budget 소진/종료 조건까지 무정지로 라운드를 반복한다(`/loop` 또는 cron 재기동).
  2. 매 라운드 STATE/결과를 외부화(commit)하여 프로세스 사망에도 재개 가능하게 한다.
  3. 비수렴 시 기법군을 자동 전환(N회)하고, 실패하면 best 유지 종료 + 알림(UC-7).
- **대안 흐름**: 안전상 autonomous에서도 넘을 수 없는 gate(예: board 안전)가 있으면 거기서 정지·알림. *(그런 강제 gate 존재 여부 = 미결)*
- **종료조건**: budget 소진(복수 지정 시 **any 소진 → 종료**) / target 달성.

## UC-4. 중간·완료 지점에서 재개
- **액터**: 배포 엔지니어 / CI
- **선행조건**: 이전 run의 STATE·산출물(중간/최종)이 저장되어 있음.
- **주 흐름**
  1. 사용자가 특정 run의 특정 지점(중간 라운드 또는 완료 지점)을 선택한다.
  2. 시스템이 그 지점의 STATE·산출물을 복원한다.
  3. 같은 목표로 추가 최적화하거나, **다른 기법/목표로 분기**해 새 탐색을 잇는다.
- **종료조건**: UC-2/UC-3와 동일.
- **비고**: 완료 이후에도 완료 지점에서 다시 시작해 추가 최적화가 가능해야 한다(README 요구).

## UC-5. 기법 후보 추가·갱신 (외부 논문 반영)
- **액터**: 기법 큐레이터
- **선행조건**: 외부 연구 논문/코드 접근.
- **주 흐름**
  1. 외부 논문/코드를 이해(deep-research)한다.
  2. 신규 최적화 기법을 **후보 + 적용 가능성 메타데이터(언제 쓰면 좋은지 = 선택 기준)** 형태로 카탈로그에 추가한다.
  3. 기존 기법을 갱신/삭제한다.
- **종료조건**: 카탈로그 갱신 완료. 이후 run의 기법 선택에 반영됨.
- **비고**: "AI for Science"-like. 선택 기준은 Skill 트리거에, 적용 지침은 코더 spec에 실린다(하이브리드). 자동/HIL 큐레이션 경계 = 미결.

## UC-6. 결과·이력 조회·비교 (감사)
- **액터**: 배포 엔지니어 / CI
- **선행조건**: 1개 이상의 run 이력 존재.
- **주 흐름**
  1. 사용자가 특정 run 또는 (hw_profile, op_signature)에 대한 이력을 조회한다.
  2. 라운드별 산출물·프로파일·정확도·점수와 best를 비교한다.
  3. 결정 로그(어떤 기법을 왜 골랐는지)를 확인한다.
- **종료조건**: 조회 완료.
- **비고**: Phase 1에서는 git history/diff가 곧 감사 로그(숨은 이점). 중간·최종·**실패** 결과가 모두 보존되어야 한다.

## UC-7. 비수렴 에스컬레이션 / 기법군 전환
- **액터**: 시스템 → 배포 엔지니어(또는 자동)
- **선행조건**: 라운드가 목표 개선에 실패(비수렴) 판정.
- **주 흐름**
  - **autonomous**: 다른 기법군으로 자동 전환을 N회 시도 → 실패 시 best 유지 종료 + 알림.
  - **checkpoint**: 비수렴 자체가 gate → 사용자에게 에스컬레이션(승인/방향 수정).
- **종료조건**: 수렴 재개 / best 유지 종료.

---

# 4. 유스케이스 관계

- UC-1은 UC-2 또는 UC-3로 분기한다(모드에 따라).
- UC-2/UC-3는 매 라운드 산출물을 남겨 UC-4(재개)·UC-6(조회)을 가능케 한다.
- UC-5는 UC-2/UC-3의 "기법 선택" 품질을 좌우한다(guided search 근거 공급).
- UC-7은 UC-2/UC-3 내부의 분기 흐름이다.

> 본 유스케이스로부터 도출된 요구사항은 [Requirements.md](Requirements.md)에 정리한다.
> 유스케이스를 구체적 단계로 풀어 쓰고 설계 커버리지를 검사하는 표준 시나리오는 [StandardScenarios.md](StandardScenarios.md)에 있다.
