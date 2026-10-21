# 개발 PLAN

[DRIVER.md](DRIVER.md) §6 planner의 입력. phase 안의 항목은 **체크리스트**이며 각 항목은 1개 이상의 task(`tasks/`)로 쪼개진다. `coversReq`는 추적용 ID — Requirements ID(FR/NFR/C/OD), 오너 결정 ID(#5 A-n·B-n·D-n), 이슈(#9), 또는 DRIVER.md 절. 완료된 phase는 그대로 두고 체크만 한다(감사성). 표시 규약: "**오너 확정 필요**"(#5 A·B 항목, C-6, OD-25, OD-3) 항목은 그 결정이 닫히기 전까지 planner가 건너뛴다; "**OD-n 종결 필요(§9)**" 항목은 그 OD를 닫는 ADR 작성을 포함한 task로 만든다(DRIVER §6·§9, D6). DRIVER §11의 D1~D18은 모두 답변되어(2026-10-03~19) 본 PLAN에 ⚑ 항목은 없다. **우선순위(D18, 오너 2026-10-19, 채팅)**: 도달 목표는 P2-14(Llama 3.2 1B end-to-end, C-6 개정)이고, 가까운 목표는 P2-5다. P1-1·P1-8은 아래 완료 기준까지만 하고, 체크리스트 밖의 일(follow-up·OD 하위 질문) 가운데 두 목표에 필요하지 않은 것은 맨 아래 "보류" 절에 한 줄로 적어 둔다(DRIVER §6). *(런타임 인수 항목)* 으로 표시된 줄은 체크리스트 항목이 아니며 planner가 task로 만들지 않는다(DRIVER §6, D16). D15(드라이버 병렬 실행)의 전환은 PLAN 항목이 아니며 planner는 그것을 task로 만들지 않는다 — 루틴을 멈춘 통합자 세션이 P0-3 완료와 P0.5-4의 hook 등록 뒤에 수행한다(D15-3·D15-4, [proposals/D15-parallel-drivers.md](proposals/D15-parallel-drivers.md) §8).

현재 phase: `PROCESS/STATE.json`의 `phase`가 정본.

## P0 — 저장소 골격 (bootstrap) — D9 확정(2026-10-05): 골격 task에는 "첫 커밋 전 OD-4/6/8 확정" 규칙을 적용하지 않음

- [x] P0-1 저장소 공통 규칙: `.gitattributes`(LF 강제 — C-7 ①의 파생·#9), `.editorconfig`, 2층 패키지 디렉토리 생성(가칭 `hilclaw/`, 빈 패키지 + 버전) — code 모드 · coversReq: C-7, FR-10, #9
- [x] P0-2 Python 프로젝트 설정: `pyproject.toml`(최소 버전·pytest·ruff), 첫 smoke 테스트 1개 · coversReq: CLAUDE.md 언어 정책, #9
- [x] P0-3 CI 스켈레톤(#9): PR과 main push에 Python 게이트(pytest+ruff) 1개, Linux 러너. required check는 두지 않음(D10 확정: 절차 게이트 + merge 가드 hook P0.5-4; #8 M24 해소) · coversReq: #9, #5 D10
- [x] P0-4 `PROCESS/STATE.json` JSON Schema(DRIVER §2 표를 기계화) + 검증기. 검증기 테스트는 **명시 요구됨**(D12 예외 ①) · coversReq: DRIVER §2·§4·§8, #5 D12
- [x] P0-5 README 갱신: 세 층 모델·개발 절차 포인터(PROCESS/, CLAUDE.md) — doc 모드 · coversReq: #5 A-12
- [x] P0-6 개발 프로세스 agent 정의: `.claude/agents/dev-planner.md`·`dev-executor.md`·`dev-reviewer.md` — 컨텍스트 격리 subagent, 허용 도구 frontmatter(모델은 CLAUDE.md 배정 원칙 — 모델명 하드코딩 금지), 기존 스킬 2개를 감쌈(DRIVER §7; 이름·도구 제한은 이 task에서 리뷰로 확정) — doc 모드 · coversReq: #5 D5, A-13

## P0.5 — 게이트 보강

- [x] P0.5-1 sh 게이트(shellcheck) · C 게이트(clang 빌드 + 하네스 통과) CI 추가 · coversReq: #9
- [x] P0.5-2 테스트 존재 검사(D12 확정): `hilclaw/`의 새 모듈에 대응 테스트 파일이 없으면 CI 실패 · coversReq: #5 D12, dev-code-review "테스트 완비"
- [x] P0.5-3 커버리지 게이트(D12 확정): `hilclaw/` **line ≥ 80%·function ≥ 80%**; branch 임계는 데이터가 쌓인 뒤 · coversReq: #5 D12, #9
- [ ] P0.5-4 merge 가드 hook(D10 확정): `PreToolUse`가 `gh pr merge`를 가로채 PR checks가 전부 success가 아니면 거부. hook 테스트는 **명시 요구됨**(D12 예외 ②). 배치(P0.5)는 통합자 선택 — 오너 선택지는 "P2-4와 함께 또는 저렴하면 P0-3과 함께" · D13(2026-10-06) 이후 금지 명령(`git push --force*`·`rm -rf *`·`gh repo delete *`)의 PreToolUse 가드도 같은 hook에서 검토(follow-up — 범위 포함 여부는 P0.5-4 task 작성 시 planner/executor가 §9 기준으로 정함; 오너 전용 결정 아님) · coversReq: #5 D10·D12, OD-18

## P1 — 2층 도구 패키지 (MVP 핵심 부품)

- [ ] P1-1 FR-10 도구 계약(`sim.run`/`board.run`/`profiler.collect`/`correctness.check`, `blob.push/fetch`) 인터페이스 + **mock 백엔드** + 백엔드 적합성 테스트 — **완료 기준(D18, 통합자 적용)**: `sim.run`·`board.run`·`correctness.check`가 `cpu_standin`과 mock에서 동작하고, 이 셋과 `blob.push`·`blob.fetch`가 도구로 등록되어 MCP front로 호출된다; `profiler.collect`는 HQ-0025의 답이 제공한다고 하면 같은 기준을 따르고 제공하지 않는다고 하면 요구하지 않는다. HQ-0025가 답해지기 전에 나머지가 충족되면 이 항목은 BLOCKED(T-0239)로 보고 phase 전환 규칙대로 이월한다. 이 기준에서 항목을 체크하고 OD-18의 잔여는 열린 채 둔다 · coversReq: FR-10, C-3(A-2)
- [x] P1-2 `cpu_standin` 어댑터: clang 빌드 래퍼, 로컬 실행, 타이밍 수집(OpenMP/SIMD 허용) · coversReq: FR-10, #5 A-7, C-7
- [x] P1-3 하네스 `harness/`: 무작위 입력(비파일 시드), f64 reference(NumPy float64는 #5 A-7 권고 — **오너 확정 필요**), tolerance 비교(instance 파라미터), 반복 타이밍 · coversReq: FR-9, OD-16 최소분(FR-9 조항), OD-13 초기값
- [x] P1-4 하네스 3-상태 캘리브레이션 테스트(통과 커널 / 실패 커널 / 기능 통과·계약 위반 커널) — **OD-16 종결 필요(§9 ADR 경로)**(#7 S-2 N8의 제안이 OD-16에 흡수된 상태) · coversReq: OD-16
- [x] P1-5 GEMM spec 예시(Llama 3.2 1B projection, M∈{1,32,512}, fp32)와 `spec.json` 스키마 — **OD-6 종결 필요(§9 ADR 경로)** · coversReq: FR-5, OD-6, #5 B-4
- [x] P1-6 CAS blob 저장(`blobs/sha256/..`, `artifacts.json`, retention class 기록) · coversReq: C-3(A-2)
- [x] P1-7 `hilclaw.config.json`(`data_repo.url`·`data_repo.local_path`, 환경변수 override — #5 A-1 세부 2) — 데이터 repo `HIL-Claw-data`는 2026-10-05 생성됨(D7; private, 빈 레이아웃) · coversReq: FR-13(A-1), #5 D7
- [ ] P1-8 런타임 STATE/instance/events 스키마(#4 §4) — **OD-8 종결 필요(§9 ADR 경로)** — **완료 기준(D18, 통합자 적용)**: P2-5의 run이 쓰고 읽는 파일 — `STATE.json`, `instance.json`, `events.ndjson`, `artifacts.json`, spec(버전 2), 가설·판정·사례 파일 — 의 스키마와 검증이 있다. 이 기준에서 항목을 체크하고 OD-8의 잔여는 열린 채 둔다 · coversReq: FR-13, NFR-1, OD-8·OD-17
- [x] P1-9 런타임 자체 점검(인스턴스 bring-up이 런타임 머신에서 실행; P2-1 라운드 0이 호출): `claude auth status`로 CLI 로그인을 확인하고(미로그인이면 `claude auth login` 안내 후 중단) → 1회용 `claude -p`에 `--mcp-config`·`--strict-mcp-config`로 패키지 자신의 MCP front를 넘겨(좁은 권한 모드, bypass 금지) 핸드셰이크(`server/discover`·`initialize` 개정·`tools/list`)·도구 목록·호출 1회·도구 실패 1회가 모델에 닿는 모습을 관찰하며, front가 거부되면 bring-up 실패. 드라이버는 테스트가 만든 가짜 `claude` 스텁으로만 빌드·검증한다(실제 `claude` 금지 — D16). ADR에 기록: 런타임 사용자의 CLI 로그인이 인스턴스의 전제 조건임(C-7 ②·③의 파생; README·UsageCases에 명시), 점검이 쓰는 `--mcp-config` 경로와 run이 에이전트에 서버를 주는 방식(ADR-0010 148행, 미결)의 차이와 그로 인해 미관찰로 남는 것, 그리고 run 중 로그인 만료와 `-p`의 `--bare` 기본화 예고(bare 모드의 인증 동작은 ADR이 공식 문서에서 확인)는 판단만 하고 결정하지 않음. **기록의 저장 위치는 오너 미결** — 정해질 때까지 표준 출력과 인스턴스 로그에만 쓰고 데이터 plane 파일은 쓰지 않는다 · coversReq: FR-10, C-7, OD-18 ①, D16(오너 2026-10-13, HQ-0006 답변 b-2)

## P2 — 1층 런타임 오케스트레이션 (프롬프트·에이전트 정의)

수행 순서는 나열 순서다(D18): 라운드 루프(P2-1~P2-4·P2-6·P2-7) → 첫 run(P2-5) → nightly(P2-10) → LLM end-to-end(P2-11~P2-14) → S6(P2-8).

- [ ] P2-1 Round-Manager 프롬프트·라운드 0(bring-up+baseline) 절차 · coversReq: FR-1
- [ ] P2-2 coder-driver(`claude -p` 호출, spec 전달, 출력 캡처) — **OD-23 종결 필요(§9 ADR 경로)**(로스터·입출력 계약, 논의중) · coversReq: FR-5, OD-23
- [ ] P2-3 evaluator(Write 권한 없음, 하네스만 호출) — **OD-16 종결 필요(§9 ADR 경로)** · coversReq: FR-9, OD-16
- [ ] P2-4 hooks: PreToolUse 예산·gate 검사, PostToolUse 저널링, Stop 커밋 강제 — **OD-18·OD-19 종결 필요(§9 ADR 경로)** · coversReq: FR-3·4·11, OD-18·19
- [ ] P2-6 가설 레코드와 판정(오너 결정 2026-10-13): 기법 선택이 가설·근거·예상 효과·출처를 구조화 기록으로 남기고 evaluate가 가설마다 판정·원인을 기록 — 스키마·파일 자리는 **OD-30 종결 필요(§9 ADR 경로)**; 2층의 스키마 검증·쓰기와 1층 프롬프트(P2-1·P2-3)에의 반영을 포함. 수행 순서는 나열 순서(P2-5보다 앞) — 첫 run이 사례를 남기도록 · coversReq: FR-11·17, OD-30·OD-23
- [ ] P2-7 가설–결과 사례 저장과 같은 키 정확 일치 조회(MVP 최소분, 오너 결정 2026-10-13): 라운드 종료 때 사례(기각·실패 포함)를 `db/<hw_profile_key>/<op_signature>/`에 저장, 기법 선택이 그 키의 사례를 읽고 참조를 결정 로그에 기록, instance 시작 시의 가설 주입 입력(FR-15) — **OD-30 종결 필요(§9 ADR 경로)**(사례 필드·싣는 사례의 선택; OD-20·OD-7과의 관계) · coversReq: FR-15·18, S11, OD-30·OD-20·OD-7
- [ ] P2-5 첫 end-to-end run: `cpu_standin` × GEMM, N=1, 5라운드 — 드라이버 task의 검증은 테스트가 만든 스텁 `claude`로 한다(D16); 드라이버 쪽에서 실제 `claude`를 쓰는 run은 P2-10의 nightly 루틴뿐이며(D17) 이 항목의 완료는 그 결과에 달려 있지 않다 · coversReq: S0, S1, S8(N=1), FR-17·18
- [ ] P2-10 nightly end-to-end 루틴(오너 결정 2026-10-13, DRIVER D17): DRIVER §3을 수행하는 드라이버와 분리된 별도 루틴이 런타임 오케스트레이터를 만들어 실제 `claude`로 end-to-end run을 돌리고(run의 구성은 미정 — 출발점 후보는 P2-5의 구성) 통과·실패와 로그를 회귀 신호로 남긴다 — 수용 기준(P2-9)과 사례 저장(FR-18)에는 쓰지 않는다. 실패는 이슈로 등록된 뒤 자동으로 해결된다(오너, D17 ④) — 해결하는 것은 DRIVER §3을 수행하는 드라이버이고 환경이 원인인 실패는 HQ로 간다(D17 행의 "따름"); 이슈가 task가 되는 방법을 포함해 그 흐름의 나머지는 D17 행의 (나)다. 이 항목의 task는 루틴의 절차 문서와 그것이 부르는 진입점을 만들며 실제 `claude`를 시작하지 않는다(실제 `claude`는 nightly 루틴만 시작한다); 진입점의 자리와 모드(코드/문서)는 task에서 정하고 테스트는 CLAUDE.md 테스트 규칙을 따른다(규칙 ⑤의 대상이면 테스트를 추가하지 않는다). 루틴 등록은 오너가 한다. D17 행의 "정하지 않은 것" 가운데 (가)는 task를 만들기 전에 DRIVER §8의 HQ로 묻고, (나)는 여기서 정한다. P2-5 뒤에 수행 · coversReq: S0, S1, D17
- [ ] P2-11 Llama 3.2 1B의 연산 계약(C-6 개정, 오너 2026-10-19, 채팅): forward에 필요한 연산 종류마다 커널 계약·op_signature·하네스 검증을 둔다(첫 kind `gemm`은 ADR-0008) — 연산 목록과 shape는 **OD-31 종결 필요(§9 ADR 경로)**(하위 질문 ①; #5 B-4 답변의 값을 바꾸는 부분은 오너에게 HQ로 묻는다) · coversReq: C-6, FR-5·9·10, OD-31·OD-6·OD-16
- [ ] P2-12 bf16/fp16(C-6 개정): 하네스의 입력·reference·허용 오차와 `cpu_standin`의 표현 — OD-31 하위 질문 ②·③은 오너 전용이다(C-6, #5 B-7): planner는 task를 만들기 전에 DRIVER §8의 HQ로 묻고, 답의 범위에서 task를 만든다 · coversReq: C-6, FR-9, OD-31, #5 B-7
- [ ] P2-13 모델 실행기(C-6 개정): instance가 낸 연산별 커널을 엮어 forward pass를 돌리고 토큰을 생성하며 모델 수준에서 reference와 대조한다 — 하위 질문 ④는 **OD-31 종결 필요(§9 ADR 경로)**, ⑤~⑧은 오너 전용이라 DRIVER §8의 HQ로 묻는다; 드라이버의 검증은 작은 합성 가중치와 합성 토크나이저로 하고 실제 Llama 3.2 1B의 가중치·토크나이저(gated 라이선스 동의가 필요)는 요구하지 않는다(D16) · coversReq: C-6, FR-9·10·13, OD-31·OD-9
- [ ] P2-14 Llama 3.2 1B end-to-end(C-6 개정의 도달 목표): P2-11의 각 연산에 대해 instance가 커널을 내고, P2-13의 실행기가 그 커널로 토큰을 생성해 reference와 맞는다 — 드라이버 task의 검증은 스텁 `claude`와 합성 가중치·토크나이저이고(D16), 이 항목의 완료는 실제 run의 결과에 달려 있지 않다; 실제 가중치의 run은 P2-15다 · coversReq: C-6, S0, OD-31
- P2-15 *(런타임 인수 항목 — 드라이버 task로 만들지 않는다, D16)* 실제 Llama 3.2 1B의 가중치·토크나이저로 P2-14의 end-to-end가 돌고 reference와 맞는지: 런타임 사용자가 라이선스에 동의해 입수한 파일로 오너가 런타임 머신에서 확인한다. nightly 루틴(P2-10)이 이것을 돌릴지는 D17 (가)의 nightly run 구성과 함께 오너에게 묻는다 — D17이 nightly 머신에 전제하는 것은 로그인된 `claude`뿐이다. P2-14가 체크된 뒤 planner가 처음 PLAN을 읽는 iteration에 DRIVER §8의 HQ(사유 `runtime-acceptance`, `taskId` = P2-14의 task)를 한 번 올린다; 이미 올렸는지는 `PROCESS/STATE.json`의 `humanQuestions`로 판정한다. phase 전환 조건에 들지 않으며 오너의 확인으로만 닫힌다 · coversReq: C-6, OD-31
- [ ] P2-8 S6 수용 기준의 계산 도구: 같은 키의 두 run의 기록에서 첫 run의 best에 도달하기까지의 라운드 수와 두 번째 run의 결정 로그에 든 사례 참조의 유무를 계산(fixture로 검증) — 지표 정의는 **OD-30 종결 필요(§9 ADR 경로)** · coversReq: S6, FR-18, OD-30
- P2-9 *(런타임 인수 항목 — 드라이버 task로 만들지 않는다, D16)* S6 수용 기준 측정: 오너가 런타임 머신에서 같은 키·target·tolerance·N·budget으로 run을 두 번(첫 run과 두 번째 run) 수행하고 P2-8의 도구로 판정한다 — 드라이버의 P2-5 검증(스텁 `claude`)의 run과 nightly 루틴의 run(P2-10, D17 ②)은 첫 run으로도 두 번째 run으로도 쓰지 않는다. P2-8이 체크된 뒤 planner가 처음 PLAN을 읽는 iteration(DRIVER §3-3)에 DRIVER §8의 HQ(사유 `runtime-acceptance`, `taskId` = P2-8의 task)를 한 번 올린다; 이미 올렸는지는 `PROCESS/STATE.json`의 `humanQuestions`로 판정하며 PLAN 본문에는 적지 않는다. phase 전환 조건에 들지 않으며 오너의 수동 확인으로만 닫힌다 · coversReq: S6, FR-18

## P3 이후 (초안만)

- Best-of-N(N≤5) 실행·승격 정책(OD-29), LAN 백엔드(SSH)·`board.run` 원격(B-2 대기), 기법 카탈로그 콜드스타트(OD-22), 크로스런 통계의 랭킹 신호·유사 키 사례 활용(OD-7·OD-4 잔여 — 가설 레코드는 P2-6, 사례 저장과 정확 일치 조회는 P2-7), 알림(OD-27).
- **예약(오너, 2026-10-13 채팅) — 지원 대상 순서와 2번째 대상**: 1번째 지원 대상은 CPU(현재의 `cpu_standin` 백엔드, #5 A-7 — 통합자 독해), **2번째 지원 대상은 Qualcomm NPU**다. QNN·AIMET 등을 이용해 HuggingFace의 주요 On-Device LLM 모델(3B급)을 최적화한다 — 목표 산출물은 더 빠르게 동작하고 더 적은 메모리를 쓰면서 품질 성능은 유지·향상되는 **양자화 모델**. 예약일 뿐이며 planner는 이 항목을 task로 만들지 않는다. **오너 확정 필요** — 위 문장에 없는 것은 어느 것도 정해지지 않았고, 이 항목은 #5 B-1·B-2·B-3·B-5(OD-9)·B-8·A-4의 어느 부분도 닫지 않는다. 정해지지 않은 것의 예(완결된 목록이 아니다): 대상 SoC·SDK 버전, 대상 모델 목록, 모델 입력 포맷·frontend 경계, 양자화 방식, 품질 지표와 평가 데이터, simulator 유무·종류, 실행 장비 접근 방식, 3층 코더의 역할, 단일 compute-kernel 범위(C-6)와 모델 단위 양자화 산출물의 관계.

## 보류 (P2-14 이후 — D18)

DRIVER §6·§3-2의 우선순위 규칙으로 task로 만들지 않았거나 되돌리지 않은 일을 한 줄씩 적는다(근거 task·ADR 또는 follow-up의 출처, 무엇). 줄은 체크박스가 아니며 phase 전환 조건에 들지 않는다. 줄을 더하는 것은 드라이버 상태 커밋이다(DRIVER §2). P2-14가 체크된 뒤 planner가 줄마다 판단한다 — task 파일이 없는 줄은 task로 만들지 버릴지, 이미 BLOCKED task가 있는 줄은 `TODO`로 되돌릴지 결과 없이 닫을지. 줄을 지우는 것, task의 status를 바꾸는 주체, 결과 없이 닫는 권한은 정하지 않았다 — 그때 오너에게 확인한다(D16의 T-0106은 오너 세션이 닫았다). 여기 든 BLOCKED task는 그 HQ가 답해져도 `TODO`로 돌아가지 않는다(DRIVER §3-2) — 답은 기록되고 P2-14 뒤에 쓰인다. 그 task의 열린 PR은 닫고 브랜치는 남긴다(DRIVER §3-2; 통합자 적용, D18).

- T-0225 (HQ-0022) — JSON 텍스트 helper 공용화, 동작 변경 없는 리팩토링.
- T-0284 (HQ-0028, PR #179 닫음 — 브랜치 `claude/T-0284-clang-build-refuses-posix-env-keys`는 남김) — `clang_build.build`의 POSIX `env` 키 사전 거부, 입력 경화.
- T-0286 (HQ-0029) — `local_run.run`의 `items` 없는 `env` 사전 거부, 입력 경화.
- T-0323 follow-up — ADR-0115 7라운드 지적 3건(결정 3·(a′)의 "에이전트를 caller로 고름" 문구, 결정 2의 "at its last step", 덜 정확해진 목록의 ADR-0111 Alternatives 2행 (c)), ADR 문구 정리.
- T-0324 follow-up — `hilclaw/standin_profile.py` 모듈 docstring의 "is bound to no tool and to no …" 문장 수정(T-0324가 land될 때에만 틀려짐), docstring 문구 정리.
- T-0325 follow-up — ADR-0116 7라운드 지적 1건(decision 2 표 (c) 열의 문구), ADR 문구 정리.
- T-0327 follow-up — ADR-0117 7라운드 지적 2건(Consequences의 "every other hit stays exact"가 ADR-0116 decision 7과 ADR-0116 자신의 less-exact 항목을 이름하지 않음, Boundaries의 "sub-questions ㉙, ㉚"에 OD(OD-8) 미표기), ADR 문구 정리.
- T-0332 follow-up — ADR-0119 7라운드 지적(StandardScenarios "최근 재검사" 줄과 S0/S1 포인터 문구, "less exact" 목록에 ADR-0029 누락, ADR-0073 귀속 문구)과 Consequences에 적힌 이전 ADR들의 덜 정확해진 문장, ADR 문구 정리.
- T-0333 follow-up — ADR-0120 7라운드 지적(decision 3의 "a check of existence is all" 범위 문구, Status의 builds-on에 ADR-0019·ADR-0025 추가)과 Consequences에 적힌 이전 ADR·docstring의 덜 정확해진 문장, ADR 문구 정리.
- T-0335 follow-up — ADR-0121 Consequences에 적힌 덜 정확해진 문장(ADR-0012·ADR-0032·ADR-0033·ADR-0117·ADR-0118·ADR-0119·ADR-0120)과 Requirements OD-28 행(잔여)·OpenDecisionProposals § OD-28 남음의 "round budget 계상", ADR·등록부 문구 정리.
- T-0337 follow-up — ADR-0122 Consequences에 적힌 덜 정확해진 문장(ADR-0118 decision 3·Consequences (1)·Walk-through·Boundaries, ADR-0120 decision 4·Consequences (3)·Walk-through·Boundaries, ADR-0121 decision 5·Consequences·Boundaries), ADR 문구 정리.
- T-0339 follow-up — ADR-0123 Consequences에 적힌 덜 정확해진 문장(ADR-0122 Context의 "fixed prompt", ADR-0118 decision 3의 "Given one run"), ADR 문구 정리.
- T-0341 follow-up — ADR-0124 Consequences의 "Less exact, not edited" 목록(ADR-0012·0013·0118·0119·0120·0121·0123의 문장, OpenDecisionProposals OD-8 ⑭), ADR·등록부 문구 정리.
- T-0348 follow-up — ADR-0127 Consequences의 "Less exact, not edited" 목록(ADR-0004·0006·0011·0012·0013·0014·0015·0018·0025·0029·0049·0072·0078·0108·0115·0118·0119·0120·0121·0122·0123·0124·0125·0126의 문장과 `hilclaw/events.py` `remove_torn_tail` docstring; `further_turn.py`·`turn_start.py` docstring은 T-0351이 처리), ADR·docstring 문구 정리.
- T-0349 follow-up — `run_commit.commit`에서 index 교체 실패 뒤 fallback reset까지 실패하면 지금은 조용히 넘어가는데 그것을 보고하게 하는 일(현재 동작은 문서화됨), 입력·실패 경로 경화.
- T-0349 follow-up — 추적되지 않은 `runs/<run_id>/STATE.json`에 ignore 규칙이 걸리면 매 호출이 owed가 된다는 점의 ADR-0127 문구 보강, ADR 문구 정리.
- T-0359 follow-up — `hilclaw/check_identity.py`의 private `_STEP_OF`와 `checks_tool.STEP_OF`가 같은 매핑을 따로 두고 있어 하나로 합치는 일(리뷰 2라운드 nit), 동작 변경 없는 리팩토링.
- T-0362 follow-up — ADR-0133 리뷰 6라운드 nit(step ⑤ 옆에 `key_records.lookup`과 함께 `hilclaw/case_lookup.py`를 인용), ADR 문구 정리.
- T-0362 follow-up — ADR-0133 Consequences의 "Less exact, not edited" 목록(ADR-0072 decision 1·Boundaries "Promotion", ADR-0127 decision 4·Boundaries, ADR-0128 Boundaries, ADR-0124·ADR-0126 Boundaries, ADR-0019 decision 2; `cases.py`·`cases_file.py`·`tools.py` docstring은 T-0363이 처리), ADR 문구 정리.
- T-0368 follow-up — ADR-0135 리뷰 7라운드 Low·Nit(decision 5 "Why not go on"의 ADR-0133 decision 4 기각 사유 인용을 ADR-0133의 사유(OD-17 재진입 라운드·반복되는 거부)대로 고치기, "The cost, plainly"에 손상된 로그 줄이 `run_file_invalid`까지 매 turn 라운드 작업을 되풀이하게 한다는 점 보강, 검사 ③·④의 순서 메모), ADR 문구 정리.
- T-0371 follow-up — ADR-0136 Consequences의 "Less exact, not edited" 목록(ADR-0126 Consequences "Waiting on the owner's #5 A-8"·Boundaries·decision 3 표, ADR-0049 Boundaries, ADR-0032·0033·0018·0029·0127 Boundaries의 "the token axis and the coder model", ADR-0023·0028·0031·0034 Boundaries, ADR-0019 decision 2 "only at the lookup or the selection", ADR-0076 decision 3·ADR-0115 decision 2의 fill-in 순서), ADR 문구 정리.
- T-0376 follow-up — ADR-0138 리뷰 7라운드 Nit 2건(Walk-through "The file was changed after the start" 행에 ADR-0004 decision 10과 함께 ADR-0018 decision 6 인용, OD-6/OD-8/OD-28 상태 칸의 날짜 범위), ADR·등록부 문구 정리.
- T-0377 follow-up — `hilclaw/gemm_contract.py` 모듈 docstring의 "It is bound to one tool: `covers` is the predicate of the `correctness.check` …" 문장이 `spec.write`도 `covers`·`task_contract`를 부르게 되어 덜 정확해짐, docstring 문구 정리.
- T-0378 follow-up — ADR-0139 리뷰 7라운드 Nit(Status "It builds on" 목록에 ADR-0128 decision 2와 ADR-0054 O8 누락), ADR 문구 정리.
- T-0378 follow-up — ADR-0139 Consequences의 "Less exact, not edited" 목록(ADR-0118 decision 4·6·Boundaries·item (vii), ADR-0123·0124·0126·0127·0128·0129·0131·0133·0134 Boundaries, ADR-0128 item (xviii)·ADR-0138 item (xxxiii), `turn_definition.py` docstring, `orchestration/round-manager.md` "not Bash or file tools"), ADR·docstring 문구 정리.
- T-0379 follow-up — `turn_permissions.options`가 같은 `name`의 agent 파일 두 개를 거부하지 않는 점(리뷰 3라운드 optional), 입력 경화.
- T-0370 follow-up — `orchestration/round-manager.md` "One round at most"가 round-end 기록 뒤 세션이 끝난다고 적지만 지금은 `run.commit`이 뒤따르는 점, 프롬프트 문구 정리.
- T-0391 follow-up — ADR-0143 리뷰 7라운드 Nit(Status "It builds on" 목록에 ADR-0123 decision 4 누락; References에는 있음), ADR 문구 정리.
