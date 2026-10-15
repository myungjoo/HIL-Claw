이 문서는 ARCHITECTURE DESCRIPTION 중 가장 첫번째로 진행되는 Item으로서 Requirement 확보 및 정제의 근원이 되는 문서이다.

본 문서는 [README](../README.md)의 목표와 Issue #2(아키텍처 토론)에서 확정된 결정사항을, **MVP인 "방법 B"(Claude Code 자신이 Orchestrator)** 범위로 한정하여 유스케이스로 정리한다.

---

# 0. 범위 (Scope)

- **In-scope**: 방법 B — Claude Code가 Long-Horizon Orchestrator가 되고, **상태는 데이터 plane(Phase 1: git 트리 → Phase 2: Local DB)** 으로 외부화한다. 코드 생성은 headless Claude Code CLI(`claude -p`)에 위임한다.
- **MVP 단계 분할**
  - **Phase 1**: 별도 DB 없이 **데이터 plane의 디렉토리 트리가 DB를 대신**한다(소스 repo와 분리 — #5 A-1). 디렉토리 레이아웃은 미래 DB 스키마를 미러링한다. 단일 run 전제.
  - **Phase 2**: 실제 Local DB 도입. Phase 1 레이아웃을 그대로 마이그레이션.
- **계층**: 본 문서의 UC-0~7은 **기본(MVP)** 유스케이스다. §4의 확장 유스케이스(UC-E1·E3·E4)는 MVP 구현 대상이 아니며, 설계가 이를 막지 않아야 한다는 제약만 진다([StandardScenarios](StandardScenarios.md) 계층·[확장 호환] 규칙과 동일). UC-E2(라운드 내 다중 후보)는 2026-10-01 OD-21 확정으로 MVP에 편입되어 UC-1·UC-2에 흡수되었다.
- **대상 HW의 출처**: 외부 타사 HW를 가져와 시험하는 경우와 **자사의 개발 중 HW**를 대상으로 하는 경우가 모두 있다(2026-09-03 확정). 후자는 실리콘·문서·도구가 개발 진행에 따라 변동될 수 있을 것으로 예상되며, 그 처리 방식은 미결이다(→ UC-0, Requirements OD-26).
- **Out-of-scope (Non-goal)**: 방법 A(DeepAgents/LangGraph 기반 별도 Agent System)는 **"HIL-Claw 2"** 로 이연한다. 방법 B가 완료되고 모든 동작이 원활히 검증된 이후에 착수한다. 본 문서에서 방법 A는 다루지 않으며, 다만 방법 B의 인터페이스(STATE/spec/도구/카탈로그)는 미래 HIL-Claw 2 승격이 쉽도록 외부화한다(→ [Requirements](Requirements.md) NFR-확장성).

---

# 1. 용어 (Glossary)

- **Loop instance**: 사용자가 *(특정 HW + 특정 모델 + 최적화 target + (선택) budget + (선택) gate 구성 + 라운드당 후보 수 N)* 을 주고 실행한 개별 최적화 건. 시스템이 목표를 일괄 고정하지 않는다.
- **Round**: 한 번의 최적화 시도 1회. `기법 선택 → 후보 N개 코드 생성(위임) → compile → sim + correctness → (승격: 상위 k개) board + correctness → profile → evaluate → 저장 → 다음 결정`. N은 instance 파라미터(초기 UI 범위 1~5), k와 실행 방식은 미결(→ Requirements OD-29).
- **후보(candidate)**: 한 라운드에서 생성된 커널 코드 1건. 라운드는 N개의 후보를 가지며, board에는 sim 상위 k개만 승격된다.
- **Gate**: 루프 진행 중 사용자 승인/지시를 기다리는 정지 지점. autonomous = gate 0개, checkpoint = gate N개. gate 구성은 instance 파라미터다.
- **hw_profile**: 성능 특성을 결정하는 HW/실행 환경 키(가속기 + 호스트 환경 튜플). 필드 스키마의 P1 최소분(정확 식별 필드·키 유도)은 [ADR-0001](decisions/ADR-0001-od4-key-schema.md), 유사도 매칭 등 나머지는 미결(→ Requirements OD-4).
- **op_signature**: 최적화 대상 연산의 식별 키. 필드 스키마의 P1 최소분은 [ADR-0001](decisions/ADR-0001-od4-key-schema.md), 나머지는 미결(→ Requirements OD-4).
- **데이터 plane**: run 산출물과 크로스런 지식(`runs/`, `db/`, `blobs/`)이 사는 저장 공간. **소스(도구) repo와 분리**된 별도 repo `HIL-Claw-data`(#5 A-1 확정)이며, 소스 쪽에서는 `hilclaw.config.json`으로 참조한다. 운영 모델 변경안(template 파생 등)은 미결 — Requirements OD-25.
- **기법 카탈로그(technique catalog)**: 최적화 기법 후보군과 "언제 쓰면 좋은지(선택 기준)" 및 적용 지침·과거 통계를 담는 자료. Phase 1에서는 repo 내 문서로 시작.
- **가설 레코드**: 라운드의 기법 선택이 남기는 구조화된 기록 — 가설·근거·예상 효과·출처. evaluate가 가설마다 판정과 원인을 덧붙인다(Requirements FR-17). 가설은 기본적으로 시스템이 스스로 세우며, 사용자가 직접 또는 논문 링크 등으로 주입할 수도 있다 — 주입은 시스템의 가설 수립을 대신하지 않는다(FR-15·17).
- **사례(case)**: 가설 레코드·판정·원인을 측정 결과에 이어 `db/<hw_profile_key>/<op_signature>/`에 저장한 것. 기각·실패도 포함하며 같은 키의 이후 instance가 참조한다(FR-18). 필드·파일 = Requirements OD-30.
- **HW 출처(hw_source)**: hw_profile의 속성. **외부 타사 HW** 또는 **자사 개발 중 HW**(2026-09-03 확정). 출처별 특성은 예상치다(예: 외부 타사 = 문서·툴체인이 벤더 고정, 자사 개발 중 = 실리콘 부재 가능·문서/도구/revision 변동). 키에 넣지 않는 필수 속성([ADR-0001](decisions/ADR-0001-od4-key-schema.md), Requirements OD-4), 출처별 처리 = OD-26.
- **CAS(content-addressable storage)**: 바이너리 산출물을 해시로 식별해 git 밖에 두는 저장소(확정 결정 A-2: `HIL-Claw-data/blobs/sha256/`, git에는 `artifacts.json`의 해시 참조만).
- **라운드 0 / bring-up**: instance 시작 시 해당 HW에서 *동작하는* 코드를 먼저 만들고 그 성능을 재는 라운드. 이 측정값이 **baseline**이다. baseline 선택지(bring-up 코드 / 벤더 라이브러리 / 기존 best) = Requirements OD-28.
- **참고 입력(reference input)**: instance 시작 시 사용자가 선택적으로 주는 기존 사례·논문 링크. 참고사항일 뿐 Ground Truth·최종 목표가 아니다(FR-15).
- **검증 하네스(verification harness)**: correctness를 판정하는 실행 환경. 코더가 수정할 수 없고 코더 scratch에 포함되지 않으며, 최적화 중 노출되지 않은 입력으로 재검증한다(FR-9; 도구 패키지 안의 단일 하위 모듈, #5 A-12).

---

# 2. 액터 (Actors)

| 액터 | 설명 | 주 모드 |
|---|---|---|
| **배포 엔지니어** | 특정 HW에 모델을 올리려는 주 사용자. 새 HW/모델 초기 탐색, 고가 board run을 직접 감독. | checkpoint (인터랙티브) |
| **CI / 헤드리스 배치** | 야간·무인 최적화를 구동하는 자동화 주체. `claude -p`. | autonomous |
| **기법 큐레이터** | 외부 연구 논문/코드를 이해해 기법 후보군을 추가/갱신하는 사용자(또는 연구자). | 인터랙티브 |
| **HW 온보딩 담당** | 새 HW(외부 타사 또는 자사 개발 중)의 hw_profile·문서 소스·sim/board 접근을 등록하는 사용자. 배포 엔지니어가 겸하거나, 자사 개발 중 HW의 경우 HW 개발팀이 맡을 수 있다. | 인터랙티브 |
| **(외부 위임 코더)** | Orchestrator가 호출하는 headless 코드 생성 인스턴스. 사람 액터는 아니나 시스템 경계 밖 협력자. | — |
| **(검증 하네스)** | correctness 판정을 수행하는 시스템 구성요소. 코더와 격리되어 코더가 수정할 수 없다(FR-9). 사람 액터 아님. | — |

---

# 3. 유스케이스

## UC-0. HW 온보딩 (hw_profile·문서 소스·도구 등록)
- **액터**: HW 온보딩 담당
- **선행조건**: 가용 범위의 스펙 문서가 있고, sim 또는 board 접근 수단 중 하나 이상이 존재. (문서를 필수로 둘지 = Requirements OD-26)
- **주 흐름**
  1. hw_profile을 등록한다: 가속기 식별 + 호스트 환경(CPU type, DRAM 등) + **HW 출처(외부 타사 / 자사 개발 중)**. *(키 필드 스키마 = OD-4, 온보딩 스키마 = OD-26)*
  2. HW Documentation(스펙, 프로그래밍 가이드, ISA/intrinsic 문서 등)의 **소스를 등록**한다 — 원본을 저장소에 복제하지 않고 포인터·접근 방법·버전을 등록부에 둔다(FR-14 ①, 오너 결정 2026-07-31). run이 실제 참조한 자료는 식별자+버전으로 기록된다(FR-14 ②).
  3. sim/board 도구 접근 정보(endpoint, quota, 예약 방식)를 등록한다(FR-10; 도구는 LAN 원격일 수 있음 — C-7). (실리콘 없는 자사 개발 중 HW의 sim-only 온보딩 허용 여부 = OD-26)
  4. (선택) 벤더 라이브러리 커널·참조 구현을 baseline 후보로 연결한다. (온보딩 시 등록 여부 = OD-28)
  5. (선택) 등록된 도구로 smoke test(간단한 커널 compile·실행)를 수행해 접근성을 확인한다. (포함 여부 = OD-26)
- **대안 흐름** *(키 여부(ADR-0001) 외에는 모두 미결 — 처리 규칙은 OD-26에서 확정)*
  - **자사 개발 중 HW의 revision 변경**(실리콘/펌웨어/툴체인 갱신): revision·toolchain 버전은 키 필드라 새 hw_profile 키가 된다(OD-4 확정분, [ADR-0001](decisions/ADR-0001-od4-key-schema.md)); 갱신 등록 절차와 기존 이력의 귀속 규칙은 미결(OD-26).
  - **외부 타사 HW의 문서 제한**: 접근 가능한 문서 소스만 등록. 문서 부재의 표시 방법(OD-26)과 코더 spec 반영 여부(OD-6 잔여 — 하위 질문(UC-0); ADR-0002는 `ext` 자리만 둠).
- **종료조건**: UC-1 선행조건 충족. hw_profile이 instance 시작 시 선택 가능.
- **비고**: FR-14 ④. HW 출처 차원은 2026-09-03 사용자 확정. 출처별 특성(예: 자사 개발 중 HW는 문서·도구가 변동되어 온보딩이 갱신 흐름이 될 수 있음)은 예상이며 처리 방식은 OD-26. MVP의 첫 hw_profile은 `cpu_standin`(#5 A-7)이다.

## UC-1. Loop instance 정의·실행
- **액터**: 배포 엔지니어 / CI
- **선행조건**: 대상 HW(hw_profile)와 모델, 사용 가능한 sim/board 도구가 등록되어 있음(→ UC-0, Requirements FR-14 ④). instance를 실행하는 머신에서 런타임 사용자의 Claude Code 명령줄(`claude`)이 로그인되어 있음(UC-0이 만드는 조건이 아니다; Requirements C-7 ②·③의 파생 — [오너 답변 HQ-0006](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6135246858), [ADR-0054](decisions/ADR-0054-od18-runtime-self-check.md)).
- **주 흐름**
  1. 사용자가 *(HW + 모델 + 최적화 target type + (선택) budget + (선택) gate 구성 + autonomy 모드 + 라운드당 후보 수 N + (선택) 참고 사례·자료 + (선택) 주입할 가설)* 를 지정해 instance를 시작한다.
  2. 시스템이 instance용 작업공간(데이터 plane의 `runs/<run_id>/` 또는 Phase 2 DB 레코드)을 만들고 STATE를 초기화한다.
  3. **라운드 0**(bring-up: 해당 HW에서 동작하는 코드 생성 + baseline 성능 측정)을 수행한 뒤 라운드 루프(UC-2 또는 UC-3)로 진입한다. 라운드 루프는 같은 (hw_profile, op_signature) 키의 과거 사례를 조회해 입력으로 쓴다(FR-18).
- **종료조건**: budget 소진 또는 (선택) target-metric 조기 달성. 기본 종료 의미론은 **best 결과 유지**.
- **비고**: 목표 type은 메뉴(vocabulary)에서 선택한다. 예: latency 최소화 / throughput 최대화 / 동시 서빙 capacity 최대화 / 메모리 상한 내 latency 최소화(제약형) / 가중 조합. *(메뉴 최종 확정 = 미결)* 참고 사례·자료(내부 Storage의 기존 사례 참조, 외부 논문 링크)는 **참고사항으로만** 쓰이며 Ground Truth나 최종 목표가 아니다(Requirements FR-15). 주입한 가설(직접 쓴 가설 또는 논문 링크 등 가설을 도출할 자료)도 같은 원칙을 따르며 시스템이 세운 가설과 같은 실험·검증·판정을 거친다 — 주입이 있어도 시스템은 라운드마다 결과에서 교훈을 얻어 스스로 추가 가설을 세운다(FR-15·17; 형식·시작 뒤의 주입 = OD-30). correctness tolerance도 instance 파라미터로 사용자가 지정한다(FR-9).

## UC-2. 인터랙티브 최적화 (checkpoint 모드)
- **액터**: 배포 엔지니어
- **선행조건**: instance가 checkpoint 모드, gate 집합이 정의됨.
- **주 흐름**
  1. 한 라운드를 실행: 기법 선택(**가설 레코드** 작성 — FR-17; 같은 키의 과거 사례 참조 — FR-18) → 후보 N개 코드 생성(외부 위임) → compile → sim **+ correctness**. correctness 실패 후보는 실패 리포트와 함께 코드 생성 단계로 복귀한다(repair).
  2. 정의된 **gate**(예: real-board 첫 투입 전 / 기법군 전환 / budget 50% 소진)에 도달하면 정지하고 사용자 승인을 기다린다.
  3. 사용자가 승인/거부/방향 수정을 입력하면 진행한다(승격 시 sim 상위 k개를 board 측정 **+ correctness 재검증** → profile → evaluate — 가설마다 **판정과 원인**을 기록, FR-17). 방향 수정으로 가설을 주입하는 것은 OD-30. **sim 통과·board 실패**는 해당 측정을 격리하고 원인을 후보/board/시뮬레이터 결함으로 분류(triage)한 뒤 처리한다 — 시뮬레이터 결함으로 분류되면 escalate한다(sim 버그 리포트, → UC-7).
  4. 결과·로그(전 후보 포함)와 가설–결과 사례(기각·실패 포함, FR-18)를 저장(commit)하고, 판정을 입력으로 다음 라운드 여부를 결정한다.
- **대안 흐름**
  - 사용자가 거부하면 해당 기법군을 건너뛰거나 instance를 중단한다.
  - **검증 실패**: 검증 하네스가 correctness 실패(또는 최적화 중 노출되지 않은 입력에서의 불일치)를 판정하면 해당 후보를 **실패로 기록**하고 best·통계에 반영하지 않는다(FR-9 hard floor). sim 단계 실패는 실패 리포트와 함께 repair로 복귀하고(주 흐름 1), 복귀 횟수 상한은 OD-19; 실패 원인은 다음 라운드 코더 spec의 `feedback` 구획에 실린다(자리 = OD-6 확정분 [ADR-0002](decisions/ADR-0002-od6-codegen-spec.md); 어떤 시도를 싣는지는 OD-6 잔여).
- **종료조건**: budget 소진 / 사용자 종료 / target 달성.
- **비고**: 도구 권한 승인 UI가 곧 HIL gate로 동작한다. *(gate 후보 목록·기본 구성 = 미결; gate 강제 층(권한 UI vs hook)과의 관계 = Requirements OD-18)*

## UC-3. 무인 최적화 (autonomous 모드)
- **액터**: CI / 헤드리스 배치
- **선행조건**: instance가 autonomous 모드, 권한 자동 승인(툴체인·환경 변경의 허락은 제외 — FR-4).
- **주 흐름**
  1. budget 소진/종료 조건까지 무정지로 라운드를 반복한다(`/loop` 또는 cron 재기동; 라운드 = 프로세스 경계 채택 여부 = Requirements OD-18).
  2. 매 라운드 STATE/결과(가설 레코드·판정·사례 포함 — UC-2 주 흐름 1·3·4와 같다)를 외부화(commit)하여 프로세스 사망에도 재개 가능하게 한다.
  3. 비수렴 시 기법군을 자동 전환(N회)하고, 실패하면 best 유지 종료 + 알림(UC-7, FR-16).
- **대안 흐름**
  - 안전상 autonomous에서도 넘을 수 없는 gate(예: board 안전)가 있으면 거기서 정지·알림. *(안전상 강제 gate의 존재·목록 = 미결, OD-3; 툴체인·환경 변경의 정지는 아래)*
  - **툴체인·환경 변경**: 필요하면 무엇이 왜 필요한지 사용자에게 알리고 허락을 기다리며 정지한다 — autonomous에서도 자동 승인되지 않는다([오너 결정 2026-10-15](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6182984913) 2항, FR-4·NFR-4; 기다리는 동안의 처리와 거절된 뒤의 동작 = OD-8 ㉝).
  - **검증 실패**: UC-2와 동일하게 후보를 실패로 기록하고 best·통계에서 제외한 뒤 무정지로 다음 라운드를 진행한다(FR-9). 반복 실패 시의 처리(비수렴 판정 UC-7과의 연동 기준)는 미결 — 무진전 서킷브레이커(OD-19)와 함께 정한다.
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
- **비고**: "AI for Science"-like. 선택 기준은 Skill 트리거에, 적용 지침은 코더 spec에 실린다(하이브리드). 자동/HIL 큐레이션 경계 = 미결. instance에 주입된 가설(FR-15)은 본 UC와 다른 경로다 — 지지 판정을 받은 주입 가설을 카탈로그로 올리는 경로는 미결(OD-30·OD-24).

## UC-6. 결과·이력 조회·비교 (감사)
- **액터**: 배포 엔지니어 / CI
- **선행조건**: 1개 이상의 run 이력 존재.
- **주 흐름**
  1. 사용자가 특정 run 또는 (hw_profile, op_signature)에 대한 이력을 조회한다.
  2. 라운드별·후보별 산출물·프로파일·정확도·점수와 best를 비교한다.
  3. 결정 로그(어떤 기법을 왜 골랐는지 — 가설·예상 효과·판정·원인과 참조한 과거 사례, FR-11·17·18)를 확인한다.
- **종료조건**: 조회 완료.
- **비고**: Phase 1에서는 git history/diff가 곧 감사 로그(숨은 이점). 단 데이터 plane과 소스가 분리되어 있으므로 **두 history를 `instance.json`의 소스 commit 기록으로 이어야** 감사가 성립한다(→ Requirements NFR-2). 중간·최종·**실패** 결과가 모두 보존되어야 한다.

## UC-7. 비수렴 에스컬레이션 / 기법군 전환
- **액터**: 시스템 → 배포 엔지니어(또는 자동)
- **선행조건**: 라운드가 목표 개선에 실패(비수렴) 판정, 또는 sim/board 불일치가 시뮬레이터 결함으로 분류됨(UC-2 주 흐름 3).
- **주 흐름**
  - **autonomous**: 다른 기법군으로 자동 전환을 N회 시도 → 실패 시 best 유지 종료 + 알림.
  - **checkpoint**: 비수렴 자체가 gate → 사용자에게 에스컬레이션(승인/방향 수정).
  - **시뮬레이터 결함**: 격리된 board 측정과 재현 정보를 묶어 sim 버그 리포트로 사용자에게 알린다(FR-16).
- **종료조건**: 수렴 재개 / best 유지 종료.

---

# 4. 확장 유스케이스 (Post-MVP)

MVP 구현 대상이 아니다. 설계(STATE/spec/도구/레이아웃 인터페이스)가 아래를 **구조적으로 배제하지 않아야** 한다(NFR-6, [확장 호환] 규칙). 구체 단계는 [StandardScenarios](StandardScenarios.md) S7·S9·S10 참조. UC-E2(라운드 내 다중 후보, S8)는 OD-21 확정(2026-10-01)으로 MVP에 편입되어 UC-1·UC-2의 N·k로 흡수되었다(ID는 이력 보존을 위해 비워 둔다).

| ID | 확장 유스케이스 | 대응 시나리오 | 설계에 대한 제약 |
|---|---|---|---|
| **UC-E1** | 검증 우회·퇴화 해 탐지 — 강화 검증(정밀도·타이밍·정적 검사)으로 가짜 개선을 걸러내고 실패 유형을 태깅 | S7 | 검증 하네스가 코더와 격리되고 검증 단계가 확장 가능할 것(OD-16) |
| ~~UC-E2~~ | *(MVP 편입 — OD-21, UC-1·UC-2)* | S8(기본 계층) | — |
| **UC-E3** | board 장애·측정 노이즈 대응 — 재시도/대체 board, 반복 측정·신뢰구간 | S9 | board 도구 인터페이스가 실패·재시도 상태를 표현할 것(OD-10, OD-13, NFR-3) |
| **UC-E4** | 결과 재현 — 과거 best를 source commit + CAS 해시로 복원해 재측정, 환경 변화 감지 | S10 | hw_profile에 환경 revision 정보가 있을 것(OD-4·OD-26, UC-0 대안 흐름); 참조 자료 스냅샷(FR-14 ②, OD-12) |

---

# 5. 유스케이스 관계

- UC-0은 UC-1의 선행조건을 만든다. 자사 개발 중 HW에서는 UC-0이 반복(갱신)될 수 있다(필요 여부 = OD-26).
- UC-1은 UC-2 또는 UC-3로 분기한다(모드에 따라).
- UC-2/UC-3의 매 라운드에 검증 하네스가 개입하며(sim·board 두 지점, FR-1), 검증 실패는 두 UC 공통의 대안 흐름이다.
- UC-2/UC-3는 매 라운드 산출물을 남겨 UC-4(재개)·UC-6(조회)을 가능케 한다.
- UC-5는 UC-2/UC-3의 "기법 선택" 품질을 좌우한다(guided search 근거 공급).
- UC-2/UC-3의 매 라운드가 남긴 가설–결과 사례는 같은 키의 이후 UC-1 instance의 입력이 된다(FR-18, 크로스런 학습 — StandardScenarios S6).
- UC-7은 UC-2/UC-3 내부의 분기 흐름이다.
- UC-E1·E3·E4는 UC-2/UC-3·UC-6의 확장이며, MVP 인터페이스 설계 시 배제 여부만 검사한다.

> 본 유스케이스로부터 도출된 요구사항은 [Requirements.md](Requirements.md)에 정리한다.
> 유스케이스를 구체적 단계로 풀어 쓰고 설계 커버리지를 검사하는 표준 시나리오는 [StandardScenarios.md](StandardScenarios.md)에 있다.
