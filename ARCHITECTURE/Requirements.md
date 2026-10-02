주어진 [UsageCases](UsageCases.md)로부터 본 과제에서 적용할 요구사항을 기술하는 문서이다.

근거 표기: **README** = [../README.md](../README.md) 목표, **UC-n** = UsageCases, **Issue#2** = 아키텍처 토론 확정 결정(D1/D3/D4/codegen 위임/Phase 분할 등), **#4 / #5 / #7 / #8** = 아키텍처 결정 스레드 / 사용자 입력 대기 목록 / 외부 조사(상설) / 모순 트래커, **오너 결정(날짜)** = 이슈 스레드에서 프로젝트 오너가 내린 결정, **S0-n** = [StandardScenarios.md](StandardScenarios.md) 기본 전제 시나리오의 단계, **(Gn)** = StandardScenarios 커버리지 검사에서 발견되어 백필된 갭, **S7~S10 / (Bn)** = 시나리오 계층 및 문헌 검토 보강 제안(2026-09-03; S8은 2026-10-01 MVP로 승격, 그 외 "확장 고려" 메모는 MVP 구현 대상이 아님). Phase 표기: **P1** = Git tree 단계, **P2** = Local DB 단계, **공통** = 둘 다.

---

# 0. 범위 (Scope)

- 본 문서는 **MVP "방법 B"(Claude Code Orchestrator)** 만 다룬다.
- **방법 A(DeepAgents/LangGraph)는 "HIL-Claw 2"로 이연**하며 요구사항에서 제외한다(→ C-5). 단, 방법 B의 인터페이스는 미래 승격이 쉽도록 외부화한다(→ NFR-6).

---

# Functional Requirements

| ID | 요구사항 | 근거 | Phase |
|---|---|---|---|
| **FR-1** | **HIL 라운드 루프**를 제공한다: `기법 선택 → 후보 N개 코드 생성(위임) → compile → sim(조기검증) + correctness → (승격: sim 상위 k개) board(최종측정) + correctness → profile → evaluate → 저장 → 다음 라운드 결정`. **라운드당 후보 수 N은 instance 파라미터**로 사용자가 시작 시 지정한다(초기 UI 선택 범위 1~5, 정책은 추후 변경 가능 — 오너 결정 2026-10-01; S8). 후보가 N개여도 board 승격은 상위 k개로 제한한다(C-4; k 결정·N개 코더 호출의 병렬/순차 = OD-29, sim→board 승격 기준 = OD-15). instance 시작 시 **라운드 0 = bring-up**(해당 HW에서 동작하는 코드 생성) + **baseline 성능 측정**을 수행하며, 이것이 이후 라운드 evaluate의 기준이 된다(baseline 선택 = OD-28). **correctness는 sim·board 두 지점에서 모두 수행**하며(FR-9), 결과에 따라: ⑴ **sim 실패 → 실패 리포트를 첨부해 코드 생성 단계로 복귀**(repair; 복귀 횟수 상한 = OD-19) ⑵ **board 실패 → 해당 후보 탈락**(board가 최종 판정) ⑶ **sim 통과·board 실패 → 원인 미확정으로 취급**: 해당 board 측정은 격리하고(기록은 남기되 record로 인정하지 않음) 원인을 **후보 결함 / board 결함 / 시뮬레이터 결함**으로 분류(triage)한 뒤 분류 결과에 따라 처리한다 — 후보 결함 = 탈락, board 결함 = OD-10 회복 정책, 시뮬레이터 결함 = 사용자 escalate → sim 버그 리포트(UC-7). | UC-1·2·3, README, S0-4 (G1), 오너 결정(2026-07-31 correctness 2지점; 2026-10-01 ⑶ 완화·N후보) | 공통 |
| **FR-2** | 최적화 목표를 시스템이 고정하지 않고, **선택 가능한 target type 메뉴(vocabulary)** 로 제공하여 **Loop instance별로 사용자가 지정**한다. | UC-1, Issue#2 D1 | 공통 |
| **FR-3** | **Budget 어휘**를 제공한다: ① loop-iteration 수 ② 토큰 수(비용) ③ wall-clock 시간 ④ target-performance-metric(달성 시 조기 종료 — 재검증 조건 = FR-9). 값은 run 시점 사용자 지정. 복수 지정 시 **any 소진 → 종료**. 시스템 기본 종료 의미론은 **budget 소진 + best 유지**. | UC-1·3, Issue#2 D3 | 공통 |
| **FR-4** | **자율성 gate 모델**: autonomous(gate 0) ↔ checkpoint(gate N). gate 집합은 **Loop instance 파라미터**로 사용자가 구성한다. autonomous도 budget/종료 조건까지 무정지 실행, checkpoint는 gate에서 정지·승인 대기. | UC-2·3, Issue#2 D4 | 공통 |
| **FR-5** | **코드 생성은 자체 수행하지 않고 headless Claude Code CLI(`claude -p`)에 위임**한다. compile 실패 repair도 위임 호출이다. Orchestrator→코더 전달 **spec을 1급 인터페이스**로 정의한다. | UC-1, Issue#2 codegen 위임 결정 | 공통 |
| **FR-6** | 최적화 산출물을 **중간·최종·실패 전부** 영구 저장하고, **임의 중간/완료 지점에서 재개**할 수 있어야 한다(추가 최적화·다른 기법 분기 포함). | UC-4·6, README | 공통 |
| **FR-7** | 기법 카탈로그에 **적용 가능성 메타데이터**(언제 쓰면 좋은지 = 선택 기준)를 함께 저장하고, 과거 (hw_profile, op_signature) 사례 통계로 후보를 **랭킹하여 Exhaustive Search를 회피**한다. | README, UC-2·5 | 공통 |
| **FR-8** | 기법 표현은 **Skill(선택 기준) + 카탈로그(적용 지침·크로스런 통계)** 하이브리드로 한다. 선택 기준은 Orchestrator 세션에서 트리거에, 적용 지침은 코더 spec에 실린다. P1에서는 기법 후보 = repo 내 문서로 시작. | Issue#2 쟁점2, README | 공통 |
| **FR-9** | **correctness 검증**을 제공한다(비트정확 아님; reference numeric / downstream metric / user-defined + tolerance). **정확도는 hard floor(게이트)이며 점수의 한 축이 아니다** — 실패는 감점이 아니라 복귀·탈락이다(오너 결정 2026-10-01, #5 A-6 → OD-5 확정). **tolerance는 사용자가 instance 파라미터로 지정·변경**한다(어휘는 #5 B-7 답변 후 확정); 손실 허용 기법(양자화·근사 연산 등)은 사용자가 정한 tolerance 안에서만 허용되며, 얼마나 잃을지를 시스템이 고르지 않는다 — 더 느슨한 tolerance에서 더 빠른 후보가 있으면 시스템은 **보고만** 하고 채택하지 않으며, 채택은 사용자가 tolerance를 바꾼 새 instance로 한다. **실행 지점은 sim·board 두 곳이며 동일 검증을 반복한다** — sim은 조기 필터, **board가 최종 판정**(수치 결과가 HW마다 달라질 수 있으므로 sim 통과가 board를 보장하지 않는다). 실패 시 처리와 sim/board 불일치 처리는 FR-1 참조. **최소 강건성 조항(MVP)**: 최적화 과정에서 코더에 노출되지 않은 입력(shape/seed)으로, 코더가 수정할 수 없는 격리된 검증 하네스에서 재검증한다. 검증을 통과하지 못한 결과는 best·통계에 반영하지 않는다. FR-3 ④ target 조기 달성은 승격 게이트 수준의 재검증을 통과한 뒤에만 종료로 인정한다. 전면 하드닝(정밀도 검사·타이밍 동기화·정적 검사·LLM 검증자)은 확장(S7) → OD-16. **검증 하네스**(입력 생성·f64 reference·tolerance 비교·타이밍·프로파일·eval/event 기록)는 도구 패키지(FR-10) 안의 **단일 하위 모듈**에 모여 있고 코더의 scratch에 포함되지 않으며, P1에서 그 버전은 `instance.json`의 소스 commit 해시다(오너 결정 2026-10-02, #5 A-12; OD-11 측정 계약 pin의 P1 구현). | UC-2, Issue#2 §C.2, S7 (B1), #5 A-6·A-12 *(검증 방식 어휘는 §B.3 도구 계약에서 유래하나 §B.3은 방법 A 절이므로 C-5에 따라 근거에서 제외)* | 공통 |
| **FR-10** | **HW 실험 도구**를 MCP/Bash로 노출한다: `sim.run`(저비용 조기검증), `board.run`(고비용·공유·quota), `profiler.collect`, `correctness.check`. 도구 계약은 **transport 무관**(로컬 실행·LAN 원격 — C-7 ⑤·⑥의 귀결)이며 mock 백엔드(고장 주입·계약 테스트)를 항상 갖는다. 첫 등록 백엔드는 **CPU 스탠드인 `cpu_standin`**(#5 A-7)으로, 실 HW 도착 전에 FR-1 전 루프를 실물로 검증한다. 도구 계층 전체는 **단일 패키지**(가칭 `hilclaw/`)로 제공되며 1층(Claude Code 오케스트레이터)이 호출하는 툴이다; **MVP에서 런타임 오케스트레이터는 미리 만들어진 도구 집합만 사용하고 run 중 도구를 생성하지 않는다**(오너 결정 2026-10-02, #5 A-12; 런타임 도구 생성은 post-MVP 확장 → NFR-6). MCP 서버 vs CLI 노출 형태 = OD-18. | UC-2·3, Issue#2 §C.2, #5 A-7·A-12 | 공통 |
| **FR-11** | 최적화 과정 전반에 **로그**를 남기고, 어떤 기법을 왜 선택했는지 **결정 로그를 강제 기록**한다(재현·감사용). | README, UC-6 | 공통 |
| **FR-12** | **외부 연구 논문·코드를 이해**하여 기법 후보군을 추가/갱신/삭제할 수 있어야 한다("AI for Science"-like). | README, UC-5 | 공통 |
| **FR-13** | **상태/지식을 세션 밖으로 외부화**한다. P1에서는 **데이터 plane의 디렉토리 트리가 DB를 대신**하며(소스 repo와 분리된 별도 repo `HIL-Claw-data` — #5 A-1 확정; 소스 쪽에서는 `hilclaw.config.json`이 물리적 바인딩을 지정), 레이아웃은 **미래 DB 스키마를 미러링**한다(`db/<hw_profile_key>/<op_signature>/...`). 레이아웃은 라운드 아래 **후보 다중성**(FR-1의 N)을 1급 차원으로 가진다(S8). P2에서 Local DB로 마이그레이션한다. *(운영 모델 변경안(template 파생 등)은 OD-25 — 채택 시 A-1 재개봉)* | UC-1·4·6, Issue#2 Phase 분할, #5 A-1, README | P1→P2 |
| **FR-14** | **외부 참조 접근 + HW 온보딩 등록부**: ① HW 스펙·벤더 문서·release된 SW 코드 등 외부에 원본이 있는 참조 자료는 HIL-Claw 내부에 **복제 저장하지 않고 MCP로 접근**한다(오너 결정 2026-07-31). 어댑터 종류를 메커니즘 중립(로컬 파일·사내 문서 시스템 포함)으로 일반화하는 것은 **통합 시 제안**이다(확정 = OD-12). repo에는 원본이 아닌 **소스 등록부(포인터·접근 방법·버전)** 만 둔다. ② 재현성(NFR-2, NFR-7③)을 위해 run 중 **실제 참조한 자료의 식별자+버전(또는 해시)을 결정 로그·instance 기록에 남기고**, **필요 시 발췌를 run 산출물로 스냅샷**한다(원본 복제가 아닌 참조 증빙). ③ 외부 소스 불가용 시의 동작(스냅샷 폴백/실패 처리)을 정의한다. ④ **HW 온보딩**: 새 hw_profile(가속기 + 호스트 환경; 스키마 = OD-4)과 **HW 출처**(외부 타사 / 자사 개발 중 — 오너 확정 2026-09-03), 문서 소스 포인터(①), sim/board 도구 접근 정보(FR-10)를 등록부에 **등록**하고, instance 시작 시 **선택**할 수 있어야 한다. *(어댑터 계약·소스 목록·스냅샷 retention, **코더의 직접 검색 허용 여부**, **발췌 스냅샷 필수화 여부** = OD-12; 온보딩 절차·출처별 처리 세부 = OD-26; #5 B-1 연계)* | 오너 결정(2026-07-31), S0-1, UC-1 선행조건 (G2), #5 B-1 | 공통 |
| **FR-15** | instance 시작 시 **(선택) 참고 사례·자료 입력**을 받을 수 있다: 내부 Storage의 기존 유사/동일 최적화 사례 참조, 외부 연구 논문 링크 등. **원칙**: 이 입력과 저장된 과거 사례는 **"참고사항"(탐색 우선순위 힌트)으로만** 사용한다 — **Ground Truth로 간주하지 않으며, 특히 기존 사례의 성능이 "최종 목표"가 되어서는 안 된다**. 목표는 오직 FR-2의 사용자 지정 target을 따른다(FR-7 랭킹에도 동일 원칙 적용). 참고 코드 소스의 예: nntrainer CPU 커널 — **커널 코드 참조로만** 사용(baseline·oracle·카탈로그 채굴 아님, #5 B-4 ④; FR-14 등록부 포인터로 참조). | S0-3 사용자 확정(2026-09-02) (G5·G6), #5 B-4 | 공통 |
| **FR-16** | **알림**을 발행한다: run 종료(best 유지 종료·비수렴 종료), 강제 gate 정지 등 사용자 개입/인지가 필요한 이벤트 대상. 채널·메커니즘 세부 = OD-27. | UC-3·7 (G3) | 공통 |

---

# Non-Functional Requirements

| ID | 요구사항 | 근거 |
|---|---|---|
| **NFR-1 내구성** | 상태를 세션 컨텍스트 밖(STATE 파일/git, P2는 DB)으로 외부화하여, compaction·프로세스 사망과 무관하게 정확한 지점에서 재개 가능해야 한다. | UC-3·4 |
| **NFR-2 재현성·감사성** | 모든 결정·산출물을 추적 가능해야 한다. 특히 **결과에서 그것을 만든 도구·설정 버전을 역추적할 수 있어야 한다**. P1에서는 git history/diff가 그 기록을 겸하되, **데이터 plane과 소스가 분리되어 있으므로 어느 한쪽 history만으로는 감사 로그가 성립하지 않는다** — 둘을 잇는 고리(`instance.json`에 소스 commit 기록, #5 A-1 세부 3 · NFR-7③)가 필수다. 모델 결정의 비결정성은 결정 로그 강제 기록으로 보완한다. | UC-6, FR-11, #5 A-1 |
| **NFR-3 측정 신뢰성** | board 성능 측정의 분산(노이즈)을 고려하여 반복 측정/신뢰구간 등으로 점수 안정성을 확보한다. *(구체 정책 = 미결 → OD-13)* | UC-2 |
| **NFR-4 안전·격리** | 생성된 커널 코드의 실행(특히 실제 board)에 sandbox·timeout·리소스 가드를 둔다. 중첩 `claude -p`(코더) 인스턴스의 작업 디렉토리 격리·권한 범위·실패/타임아웃 처리를 규정한다. *(구체 정책 = 미결 → OD-14; 코더 측 보호 — 검증·프로파일 스크립트 보호, 금지 fallback 패턴, 코더 웹 검색 차단(B8) — 는 OD-16·OD-12)* | Issue#2 쟁점3 |
| **NFR-5 비용 통제** | 코더에 별도 모델 지정이 가능해야 하며, Orchestrator/코더로 분산되는 토큰·비용을 집계할 수 있어야 한다. | Issue#2 쟁점3·4 |
| **NFR-6 확장성** | STATE/spec/HW 도구/카탈로그/DB 스키마 인터페이스를 외부화하여, P2 Local DB 및 미래 HIL-Claw 2(방법 A) 승격이 **오케스트레이션 레이어 교체만으로** 가능하도록 설계한다. 또한 StandardScenarios의 확장 시나리오(S7·S9·S10)를 인터페이스가 구조적으로 배제하지 않아야 한다([확장 호환] 규칙). **런타임 도구 생성**(post-MVP, #5 A-12)도 같은 규칙으로 다룬다 — MVP의 고정 도구 집합·정적 allowlist가 미래의 동적 도구 등록을 구조적으로 배제하지 않을 것. | Issue#2 §D, S7~S10, #5 A-12 |
| **NFR-7 진화 가능성(Evolvability)** | 본 시스템은 개념이 증명되지 않은 채 실사용에 투입되므로 **운용 중 지속적 개선·개조를 1급 요구사항**으로 한다: ① 시스템 구성요소(orchestrator 지침, subagent 정의, Skill, 커맨드, 도구 계약)는 **라운드 경계(stateless turn 경계)에서 교체·수정 가능**해야 하며 진행 중 run을 깨뜨리지 않아야 한다. *전제*: 라운드 경계가 프로세스 경계여야 성립하며(OD-18), 측정 계약(harness·tolerance·측정 정책)이 바뀐 경우 incumbent(best)를 재측정해야 점수 비교가능성이 유지된다(**OD-11 제안, 확정 전 잠정**). ② 모든 영속 아티팩트(STATE/spec/eval/db 레코드)는 `schema_version`을 가지며, **구버전 데이터의 읽기 또는 마이그레이션이 보장**되어야 한다. **FR-6 재개는 시스템 버전이 달라진 후에도 성립**해야 한다. *(보장 수단 및 P1/P2 경계 = OD-11 제안, 확정 전 잠정)* ③ 어떤 시스템 버전이 어떤 결과를 만들었는지 추적 가능해야 한다(instance.json의 소스 commit 기록, #5 A-1 세부 3). ④ 개선 방향의 근거가 되는 관측(결정 로그·실패 통계, FR-11·NFR-2)이 축적·조회 가능해야 한다. | 오너 결정(2026-07-31), Issue#2 유지보수·진화 항목, #4 §1 |

---

# Constraints

| ID | 제약 |
|---|---|
| **C-1** | 벤더 종속: 방법 B는 Claude Code/Anthropic 하네스에 종속된다(MVP에서 수용). |
| **C-2** | P1은 **단일 run 전제**. 동시 다중 run은 P2로 이연(Issue#2 D17). |
| **C-3** | 대용량 산출물 정책 — **확정(#5 A-2, 2026-07-23)**: 바이너리는 git(LFS 포함)에 넣지 않고 `HIL-Claw-data/blobs/sha256/<hh>/<hash>`(CAS, gitignore 대상)에 두며, git에는 `artifacts.json`(hash·size·type·생산 라운드·retention class)만 커밋한다. retention class: `best`/`final` = 영구, `intermediate`/`failed` = run 종료 후 유예기간(기본 30일, 설정 가능) 뒤 GC 대상 — MVP는 class 기록만 하고 GC 도구는 후속, GC 시 `gc_at` 기록 커밋으로 감사 흔적 보존(NFR-2). 동기화는 `blob.push`/`blob.fetch` 2-함수 계약(MVP 로컬 구현, 백엔드는 #5 B-2 확정 후). |
| **C-4** | HW 자원: board는 공유·제한 자원이고 sim은 저비용 조기검증 수단이다. |
| **C-5** | **방법 A(DeepAgents/LangGraph)는 HIL-Claw 2로 이연** — 본 MVP의 non-goal. |
| **C-6** | MVP 범위는 **단일 compute-kernel 최적화**. 커널→whole-model 바이너리 합성(그래프 레벨 연산자 merge 등)은 후속 범위. |
| **C-7** | **실행 환경(오너 답변 #5 B-6, 2026-10-02)**: ① 개발자 PC는 Windows·macOS·Linux가 혼재하며 Windows는 **WSL 사용을 전제**한다. ② Claude Code는 **Max 구독**으로 사용하며 별도 API 비용을 쓰지 않는다. ③ 메인 오케스트레이터는 Claude Code 세션이고, sub-agent를 띄우며, sub-agent가 `claude -p`를 호출한다. ④ 망 조건은 미정이며 "어디서든" 동작해야 한다. ⑤ sim/board 도구는 **로컬 네트워크의 원격 머신**에 있다. ⑥ 첫 HW 백엔드는 **CPU 스탠드인**(#5 A-7: C + clang, OpenMP/SIMD 허용, hw_profile `cpu_standin`, 오너 로컬 PC에서 시작 → LAN). *(파생 — 통합자 해석, #5 B-6 "Design consequences", 확정 전 잠정: ①→ 시스템은 POSIX(Linux/macOS/WSL)에서 동일 동작, Windows 네이티브 도구 비의존, LF 줄바꿈 강제 · ②→ 모든 LLM 호출은 Claude Code 안에서 일어나고 비용 통제(NFR-5)의 희소 자원은 달러가 아닌 플랜 사용 한도 · ④→ Anthropic 접속은 필수, **외부 인터넷** 의존(벤더 문서·논문·데이터 plane 원격)은 선택적이어야 하며 LAN 도구 접속은 FR-10 백엔드 선택에 따름 · ⑤→ FR-10 도구 계약은 transport 무관)* |

---

# Open Decisions (미결 — 구체 설계 단계에서 확정)

발명하지 않고 명시적으로 남긴다. 각 항목은 관련 FR 및 Issue#2 결정 ID와 연결된다.

**본 표가 미결 항목의 단일 등록부(registry)다.** 논의가 이슈에 흩어져도 각 항목의 현재 상태와 논의 위치는 여기서 확인할 수 있어야 한다.

**이슈 역할 분담**: **#4** = 아키텍처·실행모델 결정 스레드 · **#5** = 사용자만 답할 수 있는 입력 대기(A/B 항목) · **#7** = 외부 시스템 조사·분석(상설) · **#8** = 문서·이슈 간 모순 트래커 · **#1** = 참고문헌 메모.

**상태 어휘**: `미착수` 논의 없음 · `논의중` 논의 진행, 제안 미수렴 · `제안됨` 구체 제안 존재, 오너 확정 대기 · `차단됨` #5의 사용자 입력 대기 · `확정` 결정 완료(본문 반영 커밋 링크 필수).

**갱신 규칙**: 상태가 바뀌면 **본 표를 같은 커밋에서 갱신**한다. 확정 시 행을 지우지 말고 상태를 `확정`으로 바꾸고 반영 위치를 남긴다(감사성 NFR-2).

**정본 규칙**: **OD 항목의 상태·논의 위치는 본 표가 정본**이다. 이슈·코멘트에는 **표를 복제하지 말고 링크만** 둔다. (사본을 두었더니 등록부 개편 직후 번호가 어긋나 별도 정정이 필요했고, 2026-09에는 미merge PR과 main이 같은 번호를 다른 뜻으로 써 5주간 분기했다 — #8 M19, #5 A-9.)

**제안 상세**: 각 항목의 구체 제안·근거 본문은 [OpenDecisionProposals.md](OpenDecisionProposals.md)의 같은 번호 절에 둔다. 본 표에는 **한 줄 요약**만 적어 표가 읽히도록 유지한다. 제안 본문의 정본은 Proposals 문서, 상태·논의 위치의 정본은 본 표다.

**등록 범위**: 본 표는 **미결 "결정"** 만 담는다. 결정이 아닌 **작업**(예: 부트스트랩 골격 작성)은 여기 넣지 않고 이슈에서 작업 항목으로 추적한다 — 섞으면 표가 진척 관리용으로 변질된다.

**첫 커밋(P0 골격) 전에 확정해야 하는 항목**: OD-4 · OD-6 · OD-8. 이들의 사용자 입력(#5 A-1·A-2·B-4)은 2026-10-02 기준 모두 확보되었으므로 남은 것은 설계 확정(#4)이다.

| # | 미결 항목 | 관련 | 상태 | 논의 위치 · 제안 요약 |
|---|---|---|---|---|
| OD-1 | **Objective type 메뉴**의 최종 목록 및 각 type별 **best/improving 순서관계**(다목적: scalarization vs Pareto frontier, 제약형 feasibility 처리) | FR-2, D1 | 차단됨 | #5 A-4 — 제안: MVP는 "단일 목적 + 선택적 제약(메모리 상한)"만, 가중조합/Pareto는 후속. *확장 고려(B2)*: HW 이론 한계(roofline) 대비 달성률을 target·정지 어휘에 포함할지. [상세](OpenDecisionProposals.md#od-1) |
| OD-2 | **Budget 어휘에 HW quota**(sim 시간/board 시간) 포함 여부 | FR-3, D3 | 제안됨 | #7 §6 — board-second를 1급 예산 축으로 포함 권고. [상세](OpenDecisionProposals.md#od-2) |
| OD-3 | **Gate 후보 목록** + 모드별 기본 구성(autonomous에서도 강제되는 안전 gate 존재 여부) | FR-4, D4 | 차단됨 | #5 A-5 · #7 §6 — 제안: 비-설정형 최소 gate 4종. [상세](OpenDecisionProposals.md#od-3) |
| OD-4 | **hw_profile / op_signature 키 필드 스키마** + 유사도 매칭(정확 일치 vs 최근접) 규칙. P1 디렉토리 명명에 즉시 필요. HW 출처(hw_source)·revision은 hw 식별층의 필드 후보. | FR-7·13·14, D10/D11 | 제안됨 | #4 코멘트 · #7 §6 — 제안: 2층 구조(정확 식별층 + 유사도 벡터층). 첫 구체 인스턴스 = `cpu_standin` × Llama 3.2 1B GEMM/SDPA(#5 B-4). [상세](OpenDecisionProposals.md#od-4) |
| OD-5 | **정확도-성능 trade-off 정책**: 정확도를 제약(floor)으로 둘지 목적의 한 축으로 둘지 | FR-9 | **확정** (2026-10-01, #5 A-6) | **hard floor**; tolerance = 사용자 instance 파라미터. 반영: FR-9 (`cc5bf4d`, PR #6). 잔여: tolerance 어휘(per-dtype rtol/atol, downstream 지표 임계 등)는 #5 B-7 답변 후 확정. [상세](OpenDecisionProposals.md#od-5) |
| OD-6 | **codegen spec 페이로드** 정의(커널 명세, hw_profile, 직전 라운드 프로파일/에러, 적용 기법 지침) + repair 코더 **resume vs 재기동** | FR-5, D7/쟁점4 | 논의중 | #4 §4 첫 항목 · #7 — spec = coder-driver 계약의 부분집합, 대조적(top-k/bottom-k) 프로파일 동봉. spec은 **후보 식별(S8, MVP)** 을 수용. *확장 고려*: (B4) 프로파일 요약 구조, (B5) HW 문서 발췌·예시 커널 동봉(코더 직접 검색 금지 여부 = OD-12에 연동), (S7) 금지 패턴. 첫 페이로드 예시 = #5 B-4의 GEMM spec. [상세](OpenDecisionProposals.md#od-6) |
| OD-7 | **기법 통계 환류 경로**: 정적 Skill 트리거에 동적 크로스런 통계를 피드백하는 구체 메커니즘(P1 랭킹 신호 정의 포함) | FR-7·8, D5/D6/쟁점1·2 | 제안됨 | #4 코멘트 · #7 §6 — 제안: contextual bandit; 카탈로그 진입 기준 흡수. *확장 고려(B6)*: 변환 전/후 코드 쌍 저장. [상세](OpenDecisionProposals.md#od-7) |
| OD-8 | **P1 디렉토리 레이아웃** 확정(OD-3·OD-4·C-3 결과 반영). 라운드 아래 **후보 다중성을 1급 차원**으로 둔다(S8, MVP). | FR-13 | 제안됨 (후보 2건) | #4 §2 초안 · #5 A-1/A-2/B-4 입력 확보(B-4 2026-10-02 확정으로 차단 해제; OD-3 결과는 별도 입력). 격리 수단 후보 ①「레이아웃 = 권한 모델」(OS 경계: read-only 마운트 + scratch) / 후보 ②「scratch 복사 + diff 반입」(하네스·reference를 복사하지 않아 구조적으로 격리; C-7 크로스플랫폼에 유리). [상세](OpenDecisionProposals.md#od-8) |
| OD-9 | **frontend IR 출처·포맷**: `model_ref`(format-agnostic frontend 결과 IR)를 어떤 frontend/포맷(예: ONNX/StableHLO/TOSA)에서 받는지, 시스템 경계 안/밖 여부 | FR-1, Issue#2 | 차단됨 | #5 B-5 · [상세](OpenDecisionProposals.md#od-9) |
| OD-10 | **board 실패·회복 모델**: board 행/크래시/예약 경합 시 재시도·타임아웃·회복 정책(측정 노이즈와 별개) | FR-10, NFR-3 | 제안됨 | #5 B-2 입력 필요 · #7 §6 — 브로커/트래커 + health check + candidate-fault vs board-fault 구분(FR-1 ⑶ triage와 연동). [상세](OpenDecisionProposals.md#od-10) |
| OD-11 | **버전·마이그레이션 정책**: `schema_version` 부여 범위(어떤 아티팩트까지), 하위호환 읽기 보장 vs 마이그레이션 도구 제공의 경계, 시스템 버전이 바뀐 뒤 구버전 run 재개(FR-6)의 검증 방법 | NFR-7 | 제안됨 | #4 코멘트 · #7 §6 — 측정 계약 pin + 변경 시 incumbent 재측정; P1 스탬프 / P2 도구 분할(통합 시 제안, 미확정). **확정분**: P1 하네스 버전 = 소스 commit 해시(#5 A-12, FR-9). [상세](OpenDecisionProposals.md#od-11) |
| OD-12 | **외부 참조 MCP 어댑터 설계**: 대상 소스 목록(벤더 문서 포털/release repo/내부 문서 시스템), 비-MCP 소스(로컬 파일)의 어댑터 취급, 어댑터 계약(검색·조회·버전 질의), 참조 증빙 기록 포맷, 발췌 스냅샷의 필수화 여부, 코더의 직접 검색 허용 여부, 캐시 폴백·retention 정책 | FR-14, #5 B-1 | 차단됨 | #5 B-1 · #4 코멘트 · #7 §8 — 검색 권한은 orchestrator/curator 한정·코더 금지(제안); 식별자+해시 기록은 hard precondition. C-7 ④(망 미정)에 따라 ③ 불가용 폴백을 1급 경로로 볼 것(통합자 해석). [상세](OpenDecisionProposals.md#od-12) |
| OD-13 | **측정·노이즈 정책 구체화**(NFR-3): 반복 횟수 결정 방식, 판정 통계량, 개선 인정 기준, 원시 샘플 보존, warmup/steady-state 처리 | NFR-3, FR-10 | 제안됨 | #7 §5 G2 — 적응적 반복, trimmed mean, paired 측정 + 부트스트랩 CI, per-repeat 원시 벡터 저장. [상세](OpenDecisionProposals.md#od-13) |
| OD-14 | **샌드박스·격리·보드 안전 정책 구체화**(NFR-4): 생성 코드 실행 격리, 타임아웃 계층, 자원 상한, 보드 health·복구·격리 | NFR-4, FR-10 | 제안됨 | #7 §5 G1 — 1 후보 = 1 프로세스, 계층 타임아웃, blacklist(FR-6 재개도 준수). 쓰기 범위는 OD-8 후보 ①/②와 동일 결정(격리 수단은 C-7 POSIX/WSL 전제, 컨테이너 가용성 미확인). [상세](OpenDecisionProposals.md#od-14) |
| OD-15 | **sim→board 승격 기준**: 어떤 조건에서 시뮬레이터 결과를 실물 측정으로 승격시킬지 | FR-1, C-4, OD-29 | 제안됨 | #7 §6 — 고정 임계값 금지, rank correlation 기반 k, ε-greedy 슬롯(correctness false negative 탐지 겸함). [상세](OpenDecisionProposals.md#od-15) |
| OD-16 | **측정·검증의 위조 불가능성(anti-reward-hacking)**: FR-9 최소 조항 너머의 방어책 채택 범위 | FR-9, NFR-4, S7 | 제안됨 | #7 §5 G1 — 원칙: 은닉이 아닌 **위조 불가능성**(2026-07-31 개정). 위협 A(조작) = 프로세스 분리·쓰기 격리, 위협 B(퇴화) = 측정 설계. MVP 최소분은 FR-9에 반영; 전면 하드닝(S7, B1/B8)은 확장. **확정분**: 하네스는 단일 하위 모듈·코더 scratch 외(#5 A-12, FR-9). [상세](OpenDecisionProposals.md#od-16) |
| OD-17 | **실행 내구성 정책**: 라운드 재개 시 비용 이중 지출 방지, 예산 계상 방식, 동시 실행 방어 | NFR-1, FR-3, #4 §2e·§3b | 제안됨 | #4 코멘트 · #7 §5 G4 — idempotency key, 예산 fold, CAS push fencing, 선언적 재시도. [상세](OpenDecisionProposals.md#od-17) |
| OD-18 | **강제 계층(hooks) 및 라운드 경계 정의**: 규범을 프롬프트가 아닌 하네스로 강제하는 범위, 라운드=프로세스 경계 채택 여부(NFR-7① 전제, UC-3 `/loop`과의 관계 = #8 M4) | FR-11, NFR-4·5·7 | 제안됨 | #4 코멘트 · #7 §5 G5 — hooks 계층, 1 round = 1 process; CLAUDE.md 불변식 목록 흡수. FR-10 도구의 노출 형태(MCP 서버 vs CLI)도 여기서 결정(#5 A-12). [상세](OpenDecisionProposals.md#od-18) |
| OD-19 | **예산 집행(enforcement) 정책**: FR-3의 "소진 → 종료"와 FR-1 ⑴ repair 복귀 상한을 실제로 강제하는 수단. OD-17(계상)과는 별개 | FR-3, FR-5, NFR-5 | 제안됨 | #7 보충 §2(1), #8 M5 — 라운드당 상한 + 코더 호출 상한, 단일 원장, 무진전 서킷브레이커. C-7(Max 구독): 플랜 rate limit 도달은 실패가 아닌 **일시정지·재개** 조건으로 다룸(제안). [상세](OpenDecisionProposals.md#od-19) |
| OD-20 | **후보 아카이브 스키마**: `best_ref` 단일 포인터를 유지할지 **후보 집단(아카이브)** 을 저장할지 + 저장 필드 확정 | FR-6·7·13 | 제안됨 | #7 보충 §2(3) — 계보·단계별 분리 평가·public/private metrics·생성 프롬프트 보존·실패 보존. [상세](OpenDecisionProposals.md#od-20) |
| OD-21 | **탐색 폭(라운드당 후보 수)**: 라운드당 1후보 직렬을 유지할지, N후보 생성 후 상위만 board로 승격할지 | FR-1, C-4, #4 §3d | **확정** (2026-10-01, 오너 결정) | **Best-of-N은 MVP 범위.** N = 사용자 instance 파라미터(초기 UI 1~5, 정책 추후 변경 가능). 반영: FR-1·FR-13, S8 기본 계층 승격 (`cc5bf4d`, PR #6), #8 M16. 실행·승격 세부는 OD-29. [상세](OpenDecisionProposals.md#od-21) |
| OD-22 | **기법 카탈로그 콜드스타트**: 실행 이력이 0인 상태에서 카탈로그를 채우는 방법 | FR-8, UC-5 | 제안됨 | #7 보충 §2(5) — optimization rewind, git 이력 채굴(nntrainer 이력 채굴은 오너 결정으로 제외, #5 B-4 ④). [상세](OpenDecisionProposals.md#od-22) |
| OD-23 | **subagent 로스터 및 입출력 계약**: 에이전트 종류 확정(inline vs subagent 경계 포함) + 각 에이전트의 입력·출력 파일 스키마 | #4 §3a·§6, NFR-6 | 논의중 | #4 §6 · #7 §2(8) — 5종 로스터 제시, selector/promoter inline 후보, evaluator 강화. MVP 전제: 도구 집합 고정(런타임 생성 없음, #5 A-12) → per-agent tools allowlist는 정적. [상세](OpenDecisionProposals.md#od-23) |
| OD-24 | **agent-memory → db 승격 트리거**: 에이전트별 서술적 요령이 언제·어떤 형식으로 정량 신호가 되어 크로스런 지식으로 승격되는지 | FR-7, NFR-2, #4 데이터 계층 정책 | 미착수 | #4 §6 · #4 데이터 계층 코멘트 — 승격 사다리의 첫 단계 조건 미정; OD-7·OD-20과 인접. [상세](OpenDecisionProposals.md#od-24) |
| OD-25 | **데이터 거버넌스**: 데이터 plane의 물리 형태(별도 repo / 1-repo+fork / template 파생) + 공유 계층 승격 PR 정책 | FR-13, NFR-2, #5 A-1 | 차단됨 (오너 확정 대기) | #4 코멘트 2건 — fork 안 기각 권고, template 모델 대안. **#5 A-1 확정(2-repo)이 현행**. [상세](OpenDecisionProposals.md#od-25) |
| OD-26 | **HW 온보딩 절차 세부**(FR-14 ④): 등록 스키마(OD-4 연동), 문서 소스 포인터·sim/board endpoint 기술 방법, HW 출처별 처리 | FR-14, OD-4 | 미착수 | PR #10 UC-0 대안 흐름이 참조. *(통합 전 main OD-11)* [상세](OpenDecisionProposals.md#od-26) |
| OD-27 | **알림 채널·메커니즘**: 채널(콘솔/파일/외부 메신저 등), checkpoint gate 대기 알림과의 통합 여부 | FR-16 | 미착수 | — *(통합 전 main OD-12)* |
| OD-28 | **baseline 선택**: 라운드 0의 baseline을 bring-up 코드 / 벤더 라이브러리 커널 / 기존 best 중 instance 파라미터로 택할지. baseline에 따라 개선율의 의미가 달라짐 | FR-1 (B7) | 제안됨 | reviews/2026-09-03 B7. `cpu_standin` 후보 = 라운드 0 bring-up 코드 / OpenBLAS `cblas_sgemm`(nntrainer 제외, #5 B-4 ④). *(통합 전 main OD-14)* [상세](OpenDecisionProposals.md#od-28) |
| OD-29 | **N후보 실행·승격 정책**: N개 코더 호출의 병렬/순차, board 승격 수 k의 결정 방식(고정 파라미터 vs OD-15 상관 기반), 후보별 토큰·HW 비용 집계(NFR-5) | FR-1, OD-15, OD-21, C-4, C-7, S8 | 제안됨 | #7 §7 1단계 제안(상위 1~2개 승격). C-7(구독 한도를 중첩 코더가 공유) → 순차 또는 소N 권고; 초기 run은 N=1~2(#5 B-4). #4 §3d "MVP Round 직렬" 합의는 OD-21 확정으로 개정됨. [상세](OpenDecisionProposals.md#od-29) |

**번호 이력(2026-10-01 통합, #5 A-9)**: 2026-09 main 작업의 OD-11 → OD-26, OD-12 → OD-27, OD-14 → OD-28. main OD-13(correctness 수행 지점)은 2026-07-31 오너 결정(FR-1 두 지점)으로 이미 해소된 질문이라 폐기하고, 그 "확장 고려" 메모(B1/S7 전면 하드닝)는 OD-16으로 이관했다. OD-16의 하위 질문 "FR-9 확장 vs 별도 FR 승격"은 통합으로 해소됨 — 최소 조항은 FR-9, 나머지는 OD-16.
