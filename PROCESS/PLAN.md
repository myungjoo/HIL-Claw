# 개발 PLAN

[DRIVER.md](DRIVER.md) §6 planner의 입력. phase 안의 항목은 **체크리스트**이며 각 항목은 1개 이상의 task(`tasks/`)로 쪼개진다. `coversReq`는 추적용 ID — Requirements ID(FR/NFR/C/OD), 오너 결정 ID(#5 A-n·B-n·D-n), 이슈(#9), 또는 DRIVER.md 절. 완료된 phase는 그대로 두고 체크만 한다(감사성). 표시 규약: "**오너 확정 필요**"(#5 A·B 항목, C-6, OD-25, OD-3) 항목은 그 결정이 닫히기 전까지 planner가 건너뛴다; "**OD-n 종결 필요(§9)**" 항목은 그 OD를 닫는 ADR 작성을 포함한 task로 만든다(DRIVER §6·§9, D6). DRIVER §11의 D1~D18은 모두 답변되어(2026-10-03~19) 본 PLAN에 ⚑ 항목은 없다. **우선순위(D18, 오너 2026-10-19, 채팅)**: 도달 목표는 P2-14(Llama 3.2 1B end-to-end, C-6 개정)이고, 가까운 목표는 P2-5다. P1-1·P1-8은 아래 완료 기준까지만 하고, 체크리스트 밖의 일(follow-up·OD 하위 질문) 가운데 두 목표에 필요하지 않은 것은 맨 아래 "보류" 절에 한 줄로 적어 둔다(DRIVER §6). P2-5 구성의 첫 실제 run 전까지는 이 우선순위가 DRIVER §6 D24의 동결로 좁혀진다(D24, 오너 2026-10-29) — 그 동안의 `(D24 동결)` 보류 줄은 P2-14가 아니라 동결 해제 때 다시 판단한다. *(런타임 인수 항목)* 으로 표시된 줄은 체크리스트 항목이 아니며 planner가 task로 만들지 않는다(DRIVER §6, D16). **P2-14 뒤(D26, 오너 2026-10-30, 채팅)**: P2-14가 체크되어, 체크리스트 밖의 일의 기준은 이제 오너가 P2-15를 돌려 시스템이 동작하는지 확인하는 데 필요한가이고, planner는 그 일을 HQ-0080의 묶음과 남은 체크리스트 항목보다 앞에 두되 HQ를 기다리는 그 일은 다른 task를 막지 않는다(DRIVER §6 D26). D15(드라이버 병렬 실행)의 전환은 PLAN 항목이 아니며 planner는 그것을 task로 만들지 않는다 — 루틴을 멈춘 통합자 세션이 P0-3 완료와 P0.5-4의 hook 등록 뒤에 수행한다(D15-3·D15-4, [proposals/D15-parallel-drivers.md](proposals/D15-parallel-drivers.md) §8).

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

- [x] P1-1 FR-10 도구 계약(`sim.run`/`board.run`/`profiler.collect`/`correctness.check`, `blob.push/fetch`) 인터페이스 + **mock 백엔드** + 백엔드 적합성 테스트 — **완료 기준(D18, 통합자 적용)**: `sim.run`·`board.run`·`correctness.check`가 `cpu_standin`과 mock에서 동작하고, 이 셋과 `blob.push`·`blob.fetch`가 도구로 등록되어 MCP front로 호출된다; `profiler.collect`는 HQ-0025의 답이 제공한다고 하면 같은 기준을 따르고 제공하지 않는다고 하면 요구하지 않는다. HQ-0025가 답해지기 전에 나머지가 충족되면 이 항목은 BLOCKED(T-0239)로 보고 phase 전환 규칙대로 이월한다. 이 기준에서 항목을 체크하고 OD-18의 잔여는 열린 채 둔다 · coversReq: FR-10, C-3(A-2)
- [x] P1-2 `cpu_standin` 어댑터: clang 빌드 래퍼, 로컬 실행, 타이밍 수집(OpenMP/SIMD 허용) · coversReq: FR-10, #5 A-7, C-7
- [x] P1-3 하네스 `harness/`: 무작위 입력(비파일 시드), f64 reference(NumPy float64는 #5 A-7 권고 — **오너 확정 필요**), tolerance 비교(instance 파라미터), 반복 타이밍 · coversReq: FR-9, OD-16 최소분(FR-9 조항), OD-13 초기값
- [x] P1-4 하네스 3-상태 캘리브레이션 테스트(통과 커널 / 실패 커널 / 기능 통과·계약 위반 커널) — **OD-16 종결 필요(§9 ADR 경로)**(#7 S-2 N8의 제안이 OD-16에 흡수된 상태) · coversReq: OD-16
- [x] P1-5 GEMM spec 예시(Llama 3.2 1B projection, M∈{1,32,512}, fp32)와 `spec.json` 스키마 — **OD-6 종결 필요(§9 ADR 경로)** · coversReq: FR-5, OD-6, #5 B-4
- [x] P1-6 CAS blob 저장(`blobs/sha256/..`, `artifacts.json`, retention class 기록) · coversReq: C-3(A-2)
- [x] P1-7 `hilclaw.config.json`(`data_repo.url`·`data_repo.local_path`, 환경변수 override — #5 A-1 세부 2) — 데이터 repo `HIL-Claw-data`는 2026-10-05 생성됨(D7; private, 빈 레이아웃) · coversReq: FR-13(A-1), #5 D7
- [x] P1-8 런타임 STATE/instance/events 스키마(#4 §4) — **OD-8 종결 필요(§9 ADR 경로)** — **완료 기준(D18, 통합자 적용)**: P2-5의 run이 쓰고 읽는 파일 — `STATE.json`, `instance.json`, `events.ndjson`, `artifacts.json`, spec(버전 2), 가설·판정·사례 파일 — 의 스키마와 검증이 있다. 이 기준에서 항목을 체크하고 OD-8의 잔여는 열린 채 둔다 · coversReq: FR-13, NFR-1, OD-8·OD-17
- [x] P1-9 런타임 자체 점검(인스턴스 bring-up이 런타임 머신에서 실행; P2-1 라운드 0이 호출): `claude auth status`로 CLI 로그인을 확인하고(미로그인이면 `claude auth login` 안내 후 중단) → 1회용 `claude -p`에 `--mcp-config`·`--strict-mcp-config`로 패키지 자신의 MCP front를 넘겨(좁은 권한 모드, bypass 금지) 핸드셰이크(`server/discover`·`initialize` 개정·`tools/list`)·도구 목록·호출 1회·도구 실패 1회가 모델에 닿는 모습을 관찰하며, front가 거부되면 bring-up 실패. 드라이버는 테스트가 만든 가짜 `claude` 스텁으로만 빌드·검증한다(실제 `claude` 금지 — D16). ADR에 기록: 런타임 사용자의 CLI 로그인이 인스턴스의 전제 조건임(C-7 ②·③의 파생; README·UsageCases에 명시), 점검이 쓰는 `--mcp-config` 경로와 run이 에이전트에 서버를 주는 방식(ADR-0010 148행, 미결)의 차이와 그로 인해 미관찰로 남는 것, 그리고 run 중 로그인 만료와 `-p`의 `--bare` 기본화 예고(bare 모드의 인증 동작은 ADR이 공식 문서에서 확인)는 판단만 하고 결정하지 않음. **기록의 저장 위치는 오너 미결** — 정해질 때까지 표준 출력과 인스턴스 로그에만 쓰고 데이터 plane 파일은 쓰지 않는다 · coversReq: FR-10, C-7, OD-18 ①, D16(오너 2026-10-13, HQ-0006 답변 b-2)

## P2 — 1층 런타임 오케스트레이션 (프롬프트·에이전트 정의)

수행 순서는 나열 순서다(D18): 라운드 루프(P2-1~P2-4·P2-6·P2-7) → 첫 run(P2-5) → nightly(P2-10) → LLM end-to-end(P2-11~P2-14) → S6(P2-8). **실제 run 우선(D24, 오너 2026-10-29, 채팅)**: P2-10이 여는 P2-5 구성의 첫 실제 run이 관문이었다 — 해제(2026-10-30, DRIVER §6 D24 ④) 전까지 그 run에 필요하지 않은 항목(P2-11~P2-14·P2-8 등)은 task로 만들지 않았고, nightly 실패 이슈는 해제 뒤에도 PLAN 항목보다 먼저다(D24 ②). **해제 뒤(D24 ⑤)**: P2-11~P2-14는 연산 계약을 모두 갖춘 뒤가 아니라 최소 연산 세트로 먼저 실제 run을 하고 깨지는 곳을 채운다. 연산 세트와 그 순서는 OD-31을 따른다 — 세트는 [ADR-0152](../ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md) 결정 2의 instance 대상 여섯 kind(GEMM·RMSNorm·RoPE·SDPA(KV cache 포함)·SwiGLU 활성·elementwise add)이고 lm_head는 첫 run들에 넣지 않는다(#5 B-4, ADR-0152 결정 4); 순서는 B-4의 "GEMM 먼저, 그다음 attention 계열"이며 그 밖의 kind의 순서와 RoPE가 attention 계열에 드는지는 정해지지 않았다(ADR-0152 Boundaries). 실제 run은 D17·D25대로 nightly 루틴과 오너의 수동 실행·명시적 요구로만 전체 loop을 돌리고, nightly run의 구성을 넓히는 것은 D17 (가)의 오너 값이다(DRIVER §8의 HQ). 통합자 적용(오너의 말이 아님): 최소 연산 세트를 ADR-0152의 instance 대상에서 lm_head를 뺀 것으로 읽은 것 — B-4 순서의 첫 kind인 GEMM 하나부터 실제 run을 넓혀 가는 독해도 가능하다.

- [x] P2-1 Round-Manager 프롬프트·라운드 0(bring-up+baseline) 절차 · coversReq: FR-1
- [x] P2-2 coder-driver(`claude -p` 호출, spec 전달, 출력 캡처) — **OD-23 종결 필요(§9 ADR 경로)**(로스터·입출력 계약, 논의중) · coversReq: FR-5, OD-23
- [x] P2-3 evaluator(Write 권한 없음, 하네스만 호출) — **OD-16 종결 필요(§9 ADR 경로)** · coversReq: FR-9, OD-16
- [ ] P2-4 hooks: PreToolUse 예산·gate 검사, PostToolUse 저널링, Stop 커밋 강제 — **OD-18·OD-19 종결 필요(§9 ADR 경로)** · coversReq: FR-3·4·11, OD-18·19
- [x] P2-6 가설 레코드와 판정(오너 결정 2026-10-13): 기법 선택이 가설·근거·예상 효과·출처를 구조화 기록으로 남기고 evaluate가 가설마다 판정·원인을 기록 — 스키마·파일 자리는 **OD-30 종결 필요(§9 ADR 경로)**; 2층의 스키마 검증·쓰기와 1층 프롬프트(P2-1·P2-3)에의 반영을 포함. 수행 순서는 나열 순서(P2-5보다 앞) — 첫 run이 사례를 남기도록 · coversReq: FR-11·17, OD-30·OD-23
- [x] P2-7 가설–결과 사례 저장과 같은 키 정확 일치 조회(MVP 최소분, 오너 결정 2026-10-13): 라운드 종료 때 사례(기각·실패 포함)를 `db/<hw_profile_key>/<op_signature>/`에 저장, 기법 선택이 그 키의 사례를 읽고 참조를 결정 로그에 기록, instance 시작 시의 가설 주입 입력(FR-15) — **OD-30 종결 필요(§9 ADR 경로)**(사례 필드·싣는 사례의 선택; OD-20·OD-7과의 관계) · coversReq: FR-15·18, S11, OD-30·OD-20·OD-7
- [x] P2-5 첫 end-to-end run: `cpu_standin` × GEMM, N=1, 5라운드 — 드라이버 task의 검증은 테스트가 만든 스텁 `claude`로 한다(D16); 드라이버 쪽에서 실제 `claude`를 쓰는 run은 P2-10의 nightly 루틴과 executor의 테스트 run(D25)이며(D17) 이 항목의 완료는 그 결과에 달려 있지 않다 · coversReq: S0, S1, S8(N=1), FR-17·18
- [x] P2-10 nightly end-to-end 루틴(오너 결정 2026-10-13, DRIVER D17): DRIVER §3을 수행하는 드라이버와 분리된 별도 루틴이 런타임 오케스트레이터를 만들어 실제 `claude`로 end-to-end run을 돌리고(run의 구성은 미정 — 출발점 후보는 P2-5의 구성) 통과·실패와 로그를 회귀 신호로 남긴다 — 수용 기준(P2-9)과 사례 저장(FR-18)에는 쓰지 않는다(사례 저장은 2026-11-30까지 예외 — DRIVER D25). 실패는 이슈로 등록된 뒤 자동으로 해결된다(오너, D17 ④) — 해결하는 것은 DRIVER §3을 수행하는 드라이버이고 환경이 원인인 실패는 HQ로 간다(D17 행의 "따름"); 이슈가 task가 되는 방법을 포함해 그 흐름의 나머지는 D17 행의 (나)다. 이 항목의 task는 루틴의 절차 문서와 그것이 부르는 진입점을 만들며 실제 `claude`를 시작하지 않는다(실제 `claude`는 nightly 루틴과 D25의 테스트 run만 시작한다); 진입점의 자리와 모드(코드/문서)는 task에서 정하고 테스트는 CLAUDE.md 테스트 규칙을 따른다(규칙 ⑤의 대상이면 테스트를 추가하지 않는다). 루틴 등록은 오너가 한다. D17 행의 "정하지 않은 것" 가운데 (가)는 task를 만들기 전에 DRIVER §8의 HQ로 묻고, (나)는 여기서 정한다. P2-5 뒤에 수행 · coversReq: S0, S1, D17
- [x] P2-11 Llama 3.2 1B의 연산 계약(C-6 개정, 오너 2026-10-19, 채팅): forward에 필요한 연산 종류마다 커널 계약·op_signature·하네스 검증을 둔다(첫 kind `gemm`은 ADR-0008) — 연산 목록과 shape는 **OD-31 종결 필요(§9 ADR 경로)**(하위 질문 ①; #5 B-4 답변의 값을 바꾸는 부분은 오너에게 HQ로 묻는다) · coversReq: C-6, FR-5·9·10, OD-31·OD-6·OD-16
- [ ] P2-12 bf16/fp16(C-6 개정): 하네스의 입력·reference·허용 오차와 `cpu_standin`의 표현 — OD-31 하위 질문 ②·③은 오너 전용이다(C-6, #5 B-7): planner는 task를 만들기 전에 DRIVER §8의 HQ로 묻고, 답의 범위에서 task를 만든다 · coversReq: C-6, FR-9, OD-31, #5 B-7
- [x] P2-13 모델 실행기(C-6 개정): instance가 낸 연산별 커널을 엮어 forward pass를 돌리고 토큰을 생성하며 모델 수준에서 reference와 대조한다 — 하위 질문 ④는 **OD-31 종결 필요(§9 ADR 경로)**, ⑤~⑧은 오너 전용이라 DRIVER §8의 HQ로 묻는다; 드라이버의 검증은 작은 합성 가중치와 합성 토크나이저로 하고 실제 Llama 3.2 1B의 가중치·토크나이저(gated 라이선스 동의가 필요)는 요구하지 않는다(D16) · coversReq: C-6, FR-9·10·13, OD-31·OD-9
- [x] P2-14 Llama 3.2 1B end-to-end(C-6 개정의 도달 목표): P2-11의 각 연산에 대해 instance가 커널을 내고, P2-13의 실행기가 그 커널로 토큰을 생성해 reference와 맞는다 — 드라이버 task의 검증은 스텁 `claude`와 합성 가중치·토크나이저이고(D16), 이 항목의 완료는 실제 run의 결과에 달려 있지 않다; 실제 가중치의 run은 P2-15다 · coversReq: C-6, S0, OD-31
- P2-15 *(런타임 인수 항목 — 드라이버 task로 만들지 않는다, D16)* 실제 Llama 3.2 1B의 가중치·토크나이저로 P2-14의 end-to-end가 돌고 reference와 맞는지: 런타임 사용자가 라이선스에 동의해 입수한 파일로 오너가 런타임 머신에서 확인한다. nightly 루틴(P2-10)이 이것을 돌릴지는 D17 (가)의 nightly run 구성과 함께 오너에게 묻는다 — D17이 nightly 머신에 전제하는 것은 로그인된 `claude`뿐이다. P2-14가 체크된 뒤 planner가 처음 PLAN을 읽는 iteration에 [RuntimeAcceptance.md](RuntimeAcceptance.md)에 항목(출처 = `P2-15`, 근거 task = P2-14의 task)을 한 번 더한다(DRIVER §8, D22); 이미 더했는지는 그 파일에 출처 `P2-15`의 항목이 있는지로 판정한다. phase 전환 조건에 들지 않으며 오너의 확인으로만 닫힌다 · coversReq: C-6, OD-31
- [x] P2-8 S6 수용 기준의 계산 도구: 같은 키의 두 run의 기록에서 첫 run의 best에 도달하기까지의 라운드 수와 두 번째 run의 결정 로그에 든 사례 참조의 유무를 계산(fixture로 검증) — 지표 정의는 **OD-30 종결 필요(§9 ADR 경로)** · coversReq: S6, FR-18, OD-30
- P2-9 *(런타임 인수 항목 — 드라이버 task로 만들지 않는다, D16)* S6 수용 기준 측정: 오너가 런타임 머신에서 같은 키·target·tolerance·N·budget으로 run을 두 번(첫 run과 두 번째 run) 수행하고 P2-8의 도구로 판정한다 — 드라이버의 P2-5 검증(스텁 `claude`)의 run과 nightly 루틴의 run(P2-10, D17 ②)과 테스트 run(D25 — 정해질 때까지)은 첫 run으로도 두 번째 run으로도 쓰지 않는다. P2-8이 체크된 뒤 planner가 처음 PLAN을 읽는 iteration(DRIVER §3-3)에 [RuntimeAcceptance.md](RuntimeAcceptance.md)에 항목(출처 = `P2-9`, 근거 task = P2-8의 task)을 한 번 더한다(DRIVER §8, D22); 이미 더했는지는 그 파일에 출처 `P2-9`의 항목이 있는지로 판정하며 PLAN 본문에는 적지 않는다. phase 전환 조건에 들지 않으며 오너의 수동 확인으로만 닫힌다 · coversReq: S6, FR-18

## P3 이후 (초안만)

- Best-of-N(N≤5) 실행·승격 정책(OD-29), LAN 백엔드(SSH)·`board.run` 원격(B-2 대기), 기법 카탈로그 콜드스타트(OD-22), 크로스런 통계의 랭킹 신호·유사 키 사례 활용(OD-7·OD-4 잔여 — 가설 레코드는 P2-6, 사례 저장과 정확 일치 조회는 P2-7), 알림(OD-27).
- **예약(오너, 2026-10-13 채팅) — 지원 대상 순서와 2번째 대상**: 1번째 지원 대상은 CPU(현재의 `cpu_standin` 백엔드, #5 A-7 — 통합자 독해), **2번째 지원 대상은 Qualcomm NPU**다. QNN·AIMET 등을 이용해 HuggingFace의 주요 On-Device LLM 모델(3B급)을 최적화한다 — 목표 산출물은 더 빠르게 동작하고 더 적은 메모리를 쓰면서 품질 성능은 유지·향상되는 **양자화 모델**. 예약일 뿐이며 planner는 이 항목을 task로 만들지 않는다. **오너 확정 필요** — 위 문장에 없는 것은 어느 것도 정해지지 않았고, 이 항목은 #5 B-1·B-2·B-3·B-5(OD-9)·B-8·A-4의 어느 부분도 닫지 않는다. 정해지지 않은 것의 예(완결된 목록이 아니다): 대상 SoC·SDK 버전, 대상 모델 목록, 모델 입력 포맷·frontend 경계, 양자화 방식, 품질 지표와 평가 데이터, simulator 유무·종류, 실행 장비 접근 방식, 3층 코더의 역할, 단일 compute-kernel 범위(C-6)와 모델 단위 양자화 산출물의 관계.

## 보류 (D18·D26)

DRIVER §6·§3-2의 우선순위 규칙으로 task로 만들지 않았거나 되돌리지 않은 일을 한 줄씩 적는다(근거 task·ADR 또는 follow-up의 출처, 무엇). 줄은 체크박스가 아니며 phase 전환 조건에 들지 않는다. 줄을 더하는 것은 드라이버 상태 커밋이다(DRIVER §2). P2-14 체크 뒤의 줄별 처리와 줄 삭제, status를 바꾸는 주체, 결과 없이 닫는 권한은 HQ-0080(오너 2026-10-30)이 그 승인 목록의 줄에 대해 정했다(드라이버가 상태 커밋으로 적용). 여기 든 BLOCKED task는 그 HQ가 답해져도 `TODO`로 돌아가지 않는다(DRIVER §3-2; 예외는 HQ-0080 ①~③의 적용) — 답은 기록되고 그 줄을 처리할 때 쓰인다. 그 task의 열린 PR은 닫고 브랜치는 남긴다(DRIVER §3-2; 통합자 적용, D18). 그 승인 목록에 없는 줄(DRIVER §6 D26이 이름한 T-0516 follow-up 줄 제외)과 D26 뒤에 든 줄을 언제 다시 보는지는 정하지 않았다(DRIVER §6 D26).

- T-0225 (HQ-0022) (HQ-0080: T-0225 closed without a result; replan on current main) (→ T-0524) — JSON 텍스트 helper 공용화, 동작 변경 없는 리팩토링.
- T-0284 (→ T-0284) (HQ-0028, PR #179 merged, 브랜치는 지움) — `clang_build.build`의 POSIX `env` 키 사전 거부, 입력 경화.
- T-0286 (→ T-0286) (HQ-0029) — `local_run.run`의 `items` 없는 `env` 사전 거부, 입력 경화.
- T-0324 follow-up (→ T-0522) — `hilclaw/standin_profile.py` 모듈 docstring의 "is bound to no tool and to no …" 문장 수정(T-0324가 land될 때에만 틀려짐), docstring 문구 정리.
- T-0335 follow-up (→ T-0525) — ADR-0121 Consequences에 적힌 덜 정확해진 문장(ADR-0012·ADR-0032·ADR-0033·ADR-0117·ADR-0118·ADR-0119·ADR-0120)과 Requirements OD-28 행(잔여)·OpenDecisionProposals § OD-28 남음의 "round budget 계상", ADR·등록부 문구 정리.
- T-0341 follow-up (→ T-0525) — ADR-0124 Consequences의 "Less exact, not edited" 목록(ADR-0012·0013·0118·0119·0120·0121·0123의 문장, OpenDecisionProposals OD-8 ⑭), ADR·등록부 문구 정리.
- T-0348 follow-up (→ T-0522) — ADR-0127 Consequences의 "Less exact, not edited" 목록(ADR-0004·0006·0011·0012·0013·0014·0015·0018·0025·0029·0049·0072·0078·0108·0115·0118·0119·0120·0121·0122·0123·0124·0125·0126의 문장과 `hilclaw/events.py` `remove_torn_tail` docstring; `further_turn.py`·`turn_start.py` docstring은 T-0351이 처리), ADR·docstring 문구 정리.
- T-0349 follow-up (→ T-0521) — `run_commit.commit`에서 index 교체 실패 뒤 fallback reset까지 실패하면 지금은 조용히 넘어가는데 그것을 보고하게 하는 일(현재 동작은 문서화됨), 입력·실패 경로 경화.
- T-0359 follow-up (→ T-0523) — `hilclaw/check_identity.py`의 private `_STEP_OF`와 `checks_tool.STEP_OF`가 같은 매핑을 따로 두고 있어 하나로 합치는 일(리뷰 2라운드 nit), 동작 변경 없는 리팩토링.
- T-0368 follow-up (→ T-0525) — ADR-0135 리뷰 7라운드 Low·Nit(decision 5 "Why not go on"의 ADR-0133 decision 4 기각 사유 인용을 ADR-0133의 사유(OD-17 재진입 라운드·반복되는 거부)대로 고치기, "The cost, plainly"에 손상된 로그 줄이 `run_file_invalid`까지 매 turn 라운드 작업을 되풀이하게 한다는 점 보강, 검사 ③·④의 순서 메모), ADR 문구 정리.
- T-0377 follow-up (→ T-0522) — `hilclaw/gemm_contract.py` 모듈 docstring의 "It is bound to one tool: `covers` is the predicate of the `correctness.check` …" 문장이 `spec.write`도 `covers`·`task_contract`를 부르게 되어 덜 정확해짐, docstring 문구 정리.
- T-0378 follow-up (→ T-0522) — ADR-0139 Consequences의 "Less exact, not edited" 목록(ADR-0118 decision 4·6·Boundaries·item (vii), ADR-0123·0124·0126·0127·0128·0129·0131·0133·0134 Boundaries, ADR-0128 item (xviii)·ADR-0138 item (xxxiii), `turn_definition.py` docstring, `orchestration/round-manager.md` "not Bash or file tools"), ADR·docstring 문구 정리.
- T-0379 follow-up (→ T-0521) — `turn_permissions.options`가 같은 `name`의 agent 파일 두 개를 거부하지 않는 점(리뷰 3라운드 optional), 입력 경화.
- T-0370 follow-up (→ T-0522) — `orchestration/round-manager.md` "One round at most"가 round-end 기록 뒤 세션이 끝난다고 적지만 지금은 `run.commit`이 뒤따르는 점, 프롬프트 문구 정리.
- T-0399 follow-up — ADR-0145 decision 5의 "no way is known for a kernel to make W5 fail"에 같은 uid 프로세스의 `prlimit(2)`(RLIMIT_AS·RLIMIT_STACK 낮추기) 경로를 적고 런타임 인수 항목 (liii)에 더하는 일(리뷰 7라운드 Low; W3~W5 무할당은 T-0401 코드가 지킴), ADR 문구 정리.
- T-0399 follow-up — ADR-0145 decision 3에서 waiter 빌드가 타이밍 빌드 뒤에 와서 B_t를 나눠 쓰므로, 컴파일이 느린 커널이 호출을 열린 OD-18 ⑲ 상황으로 밀 수 있다는 점: waiter를 먼저 빌드하거나, 순서의 이유를 적고 decision 5의 주의를 그 경우로 넓히는 일(리뷰 7라운드 Low), ADR 설계 보강.
- T-0404 follow-up (→ T-0521) — `turn_loop`이 정의가 가져온 `.claude/settings.local.json`을 거부하지 않는 점(리뷰 info; 실제 `put_definition`은 `LAYOUT`만 복사하고 턴은 `--setting-sources project`로 돈다), 입력 경화.
- T-0405 follow-up (→ T-0525) — ADR-0147 리뷰 7라운드 Nit(decision 4가 `instance.json`의 미지 최상위 멤버 처리를 ADR-0012 decision 2로 인용; `instance.json`은 ADR-0018 decision 2), ADR 문구 정리.
- T-0406 follow-up (→ T-0521) — `hilclaw/caller_check.py`가 입력의 `NaN`/`Infinity` 상수를 받아들이는 점(리뷰 1라운드 Info), 입력 경화.
- T-0406 follow-up (→ T-0521) — `caller_check.START`·`budget_check.START`에서 `main` 진입 전 실패(패키지 디렉토리 인수 없음, import 실패)가 exit 1(non-blocking error)로 끝나는 점을 ADR-0146 (lix)와 함께 따져 보는 일(리뷰 1라운드 Info), 실패 경로 경화.
- T-0407 follow-up (→ T-0521) — hook 경로 placeholder(`${CLAUDE_PROJECT_DIR}` 등) 거부가 data root에만 있고 `PACKAGE_DIRECTORY`·`sys.executable`에는 없는 점(리뷰 Info; T-0407 이전부터), 입력 경화.
- T-0416 follow-up (→ T-0522) — `hilclaw/spec_feedback.py` 모듈 docstring의 "Nothing calls this module until ``spec.write`` … is widened" 문장이 T-0416(ADR-0151 slice 2) 뒤로 틀려짐, docstring 문구 정리.
- T-0422 follow-up (→ T-0522) — `hilclaw/checkout_boundary.py` 모듈 docstring이 사용처로 `hilclaw.scratch`·`hilclaw.selfcheck_session`만 적고 `hilclaw.model_execute`를 빠뜨린 점, docstring 문구 정리.
- T-0375 follow-up (→ T-0525) — ADR-0137 Consequences의 "Less exact, not edited" 목록 가운데 코드 docstring(T-0425가 처리)을 뺀 나머지(ADR-0049 decision 5 L6·Boundaries, ADR-0126 decision 5·Consequences "Open parts of the start"·slice 3·Boundaries, ADR-0136 decision 7·Boundaries, ADR-0141 Status·decision 3·Boundaries, ADR-0144 Boundaries, ADR-0138·ADR-0139·ADR-0151의 "unlanded ADR-0137"/HQ-0053 언급, UsageCases UC-1 "선행조건"과 README "instance의 선행조건"에 이미지·토큰 누락, OpenDecisionProposals § OD-8 "제안으로 남는 부분"), ADR·문서 문구 정리.
- T-0429 follow-up (→ T-0525) — OpenDecisionProposals § OD-6 하위 질문 ①이 기록 규칙의 "→ 부분 답: … 남음: …" 형식이 아니라 옛 "확정: … 미결 그대로: …" 형식인 점(task 이전부터), 문서 문구 정리.
- T-0435 follow-up (→ T-0525) — ADR-0158 리뷰 7라운드 Info(decision 9의 "no value set changes this much at that width"를 "for every square"로 좁히는 일), ADR 문구 정리.
- HQ-0034 답(T-0325, 오너 2026-10-25 채팅 — (a)) (→ T-0517) — 모든 C-7 시스템에서 stand-in 커널이 OpenMP를 쓰도록 ADR-0116의 고정 빌드 설정에 OpenMP 플래그·런타임을 넣고 런타임이 없을 때의 설치 경로(2026-10-15 승인 규칙, 컨테이너는 그 이미지)를 반영하는 일(ADR·`cpu_standin` 빌드 설정·OD-18 등록부); 첫 사례와 P2-14의 커널은 OpenMP 없이 돌아 두 목표에 필요하지 않음, OD-18 하위 질문 18·19 (ra)의 반영.
- T-0451 follow-up (→ T-0525) — ADR-0163 리뷰 7라운드 지적 2건(decision 7 "Every kind"의 바르게 반올림된 bf16 최대 상대 오차는 2^−8이 아니라 1/257; Alternatives 4행의 첫 case는 값 전체가 아니라 magnitude만 `word >> 41`에서 가져옴), ADR 문구 정리.
- T-0470 follow-up (→ T-0522) — ADR-0166 Consequences의 "Less exact, not edited" 목록(`hilclaw/model_program.c` 헤더의 "It is not yet a forward pass", ADR-0153 decision 4 "Casts … none is decided"·decision 6·Boundaries 첫 항목, ADR-0157 Context·decision 1·Boundaries, ADR-0162·ADR-0165 Boundaries의 cache capacity, ADR-0161 decision 6의 QKV 열 순서, ADR-0159 decision 8의 "an example for the code slice"), ADR·docstring 문구 정리.
- T-0231 (→ T-0231) (HQ-0023 답의 단서, ADR-0074 landed, 브랜치는 지움) — OD-30의 S6 지표(첫 run의 best·도달·사례 참조, run 간 drift)를 정하는 ADR, P2-8(S6 계산 도구, P2 순서의 맨 뒤) 쪽 일로 P2-5·P2-14에 필요하지 않음.
- T-0243 follow-up (→ T-0521) — ADR-0078 code slice 4: `hilclaw/clang_build.py`가 산출물 이동이나 임시 파일 제거의 `OSError`에서 컴파일러 로그를 잃는 경우를 고치거나 그 경우를 등록하는 일, 실패 경로 경화.
- T-0243 follow-up (→ T-0523) — `hilclaw/spec_feedback.py`가 build-log 파일 이름을 직접 만드는 것을 `layout.build_log_file`로 바꾸는 일, 동작 변경 없는 리팩토링.
- T-0480 follow-up (→ T-0522) — ADR-0168·ADR-0169 Consequences가 덜 정확해졌다고 적은 `hilclaw/standin_answer.py`·`standin_container.py`·`standin_copies.py`·`standin_image.py`·`standin_waiter_line.py` 모듈 docstring의 "nothing calls it yet"/"bound to no tool" 문장 정리, docstring 문구 정리.
- T-0484 follow-up (→ T-0522) — ADR-0132 Consequences의 "Less exact, not edited" 목록과 T-0484 Result가 적은 문장(ADR-0059·ADR-0073 Boundaries, ADR-0129 decision 4, ADR-0139 decisions 1·3, ADR-0146 decision 1, `hilclaw/case_lookup.py` docstring, ADR-0132 Consequences의 "until `board.run` is registered"), ADR·docstring 문구 정리.
- HQ-0070 답(오너 2026-10-26, ADR-0176 O2) follow-up (→ T-0522) — `hilclaw/rope_table.py` 모듈 docstring "**Inputs.**"의 "Which scale factor Llama 3.2 1B needs (8 in Meta's code, 32 in Hugging Face's converter) is open, OD-31 sub-question 5 and the driver's HQ-0070" 문장이 오너 답(32) 뒤로 덜 정확해짐(값은 여전히 caller 입력), docstring 문구 정리.
- T-0506 follow-up — ADR-0182 code slice 3: fp32 `hilclaw/model_execute.py` 경로의 빌드·프로세스를 ADR-0144 컨테이너로 옮기는 일(ADR-0182 decision 9가 "P2-14 does not run it"이라 적음; 지금은 instance 커널을 이 경로로 돌리는 호출자가 없음), 격리 경화.
- OD-31 ⑤·⑦ (PLAN P2-15 준비) — 실제 Llama 3.2 1B 가중치 읽기와 토크나이저(모델 파일의 출처·포맷·변형·저장 위치와 필요한 패키지 — 오너 전용이라 착수 전에 DRIVER §8의 HQ로 묻는다), P2-14는 합성 가중치·토크나이저로 검증하므로(PLAN P2-14, ADR-0176) 그 완료에 필요하지 않음.
- T-0510 planning (→ T-0523) — ADR-0183 decision 9 item 2가 언급한 정리: T-0510 뒤로 호출자가 없어지는 `hilclaw.hw_tool.read_stepped_tool_function`과 그 아래 `hilclaw.journaled_tool.read_stepped_function`의 제거(자체 테스트가 계속 커버함), 동작 변경 없는 리팩토링.
- T-0510 follow-up (→ T-0523) — ADR-0183 decision 9 item 2가 "may follow in a third task"로 남긴, 호출하는 도구가 없어진 옛 check 결과 builder(`check_result.completed`·`broken`·`bf16_completed`·`bf16_broken`·`BF16_KINDS`, `check_judging.from_judgement`·`from_report`·`from_bf16_judgement`·`from_bf16_report`, 필요하면 `DrawCounts.cache_differences`)와 그 테스트의 제거, 동작 변경 없는 리팩토링.
- T-0510 follow-up (→ T-0522) — `hilclaw/check_seed.py` docstring(41행)이 제거된 `check_admission.admit_for_step`을 여전히 이름하는 점, docstring 문구 정리.
- T-0514 follow-up (→ T-0521) — `tests/harness/test_bf16_timing.py::test_standard_error_is_captured_and_not_parsed`가 native Windows에서만 CRLF로 실패하는 점(CI 게이트 아님), 테스트 정리.
- T-0517 follow-up — ADR-0188 later slice: nightly 진입점 밖의 instance 시작에서 stand-in 이미지의 OpenMP 런타임을 미리 검사하는 일(지금은 커널 빌드마다 `build_exit_status`로 답함), 실패 경로 경화.
- T-0517 follow-up — ADR-0188 Boundaries: 런타임의 어느 부분이 사용자에게 설치 허락을 묻고 그 뒤 이미지를 어떻게 얻는지(OD-8 ㉝ (가), OD-14 ① (나); HQ-0034 답의 "사용자 승인을 받아" 쪽), 하위 질문.
- T-0517 follow-up — ADR-0188 Consequences가 적은 덜 정확해진 문장(ADR-0116 decisions 3~6·Limits 4·Alternatives·Boundaries, ADR-0035 decision 3, ADR-0144 decisions 5·6·Boundaries 등), ADR 문구 정리.
- T-0514·T-0515 follow-up — Result가 적은 덜 정확해진 문장(ADR-0065 decision 2 "exactly these six values", ADR-0177 decision 4·decision 5 item 4·Boundaries), ADR 문구 정리.
- (→ T-0518은 binding(OD-31 ④)만; 진입점(OD-31 ⑩, HQ-0084 ④)은 열림) T-0516 follow-up — P2-15 준비: 실행기의 사용자 진입점(OD-31 ⑩, OD-18, OD-23)과 key의 best에서 binding을 얻는 방법(OD-31 ④, OD-20·OD-7·#5 A-4 — 오너 몫이 드러나면 착수 전에 HQ), 코더의 실제 커널은 `hilclaw/model_forward_container.py`로만 돌림(ADR-0182 decision 7); P2-14는 합성 가중치·스텁으로 체크되어 그 완료에 필요하지 않음.
- T-0231 follow-up — ADR-0184 결정 2의 "the median is the figure ADR-0140's comparison rests on"이 ADR-0007 결정 7의 T(trimmed mean)와 맞지 않아 보이는 점(executor 관찰, 미확인), ADR 문구 정리.
- T-0284 follow-up — ADR-0089 결정 2 아래 POSIX `env` 키 거부를 S4 `settings_refused`로 확인하고 ADR-0094 결정 3의 열린 항목을 좁히는 문서 task, ADR 문구 정리.
- T-0284 follow-up — `tests/harness/test_bf16_timing.py::test_standard_error_is_captured_and_not_parsed`가 Windows 로컬에서 stderr의 `\r\n`으로 실패(executor 관찰, CI는 통과, clean main에서 재확인 안 함), 개발 머신 테스트 정리.
- T-0286 follow-up — `local_run.run`의 이름 붙은 사전 오류 기록(OD-18 하위 질문 18 (ma), ADR-0088 계열)에 `env`의 `TypeError`를 포함하는 문서 정리.
- T-0519 planning — bf16 계약의 카탈로그 항목과 그것을 받는 `## Applies to` 형식(OD-22, ADR-0177 Boundaries): T-0519 뒤 bf16 run의 라운드 ≥ 1은 빈 `techniques`로 돌아 기법 지침 없이 코더 판단에 맡겨짐; P2-15는 reference 일치를 확인하고 속도를 요구하지 않아 그 확인에 필요하지 않음.
- T-0519 planning — 검증이 instance 밖의 shape도 뽑을지(OD-16 하위 질문 ①, ADR-0189 Boundaries): every-shape 의무를 어긴 커널은 P2-15의 `run failed`나 모델 수준 비교에서 드러나 그 확인에 필요하지 않음.
- T-0525 follow-up — `ADR-0164` 91행이 "the 2^−8 of ADR-0163 decision 7"을 인용하는데 T-0525가 그 값을 1/257로 고쳤다. 인용 문구 정리이며 P2-15의 확인에는 필요하지 않다.
