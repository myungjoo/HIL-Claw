# 개발 PLAN

[DRIVER.md](DRIVER.md) §6 planner의 입력. phase 안의 항목은 **체크리스트**이며 각 항목은 1개 이상의 task(`tasks/`)로 쪼개진다. `coversReq`는 추적용 ID — Requirements ID(FR/NFR/C/OD), 오너 결정 ID(#5 A-n·B-n·D-n), 이슈(#9), 또는 DRIVER.md 절. 완료된 phase는 그대로 두고 체크만 한다(감사성). 표시 규약: "**오너 확정 필요**"(#5 A·B 항목, C-6, OD-25, OD-3) 항목은 그 결정이 닫히기 전까지 planner가 건너뛴다; "**OD-n 종결 필요(§9)**" 항목은 그 OD를 닫는 ADR 작성을 포함한 task로 만든다(DRIVER §6·§9, D6). DRIVER §11의 D1~D17은 모두 답변되어(2026-10-13) 본 PLAN에 ⚑ 항목은 없다. *(런타임 인수 항목)* 으로 표시된 줄은 체크리스트 항목이 아니며 planner가 task로 만들지 않는다(DRIVER §6, D16). D15(드라이버 병렬 실행)의 전환은 PLAN 항목이 아니며 planner는 그것을 task로 만들지 않는다 — 루틴을 멈춘 통합자 세션이 P0-3 완료와 P0.5-4의 hook 등록 뒤에 수행한다(D15-3·D15-4, [proposals/D15-parallel-drivers.md](proposals/D15-parallel-drivers.md) §8).

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

- [ ] P1-1 FR-10 도구 계약(`sim.run`/`board.run`/`profiler.collect`/`correctness.check`, `blob.push/fetch`) 인터페이스 + **mock 백엔드** + 백엔드 적합성 테스트 · coversReq: FR-10, C-3(A-2)
- [x] P1-2 `cpu_standin` 어댑터: clang 빌드 래퍼, 로컬 실행, 타이밍 수집(OpenMP/SIMD 허용) · coversReq: FR-10, #5 A-7, C-7
- [x] P1-3 하네스 `harness/`: 무작위 입력(비파일 시드), f64 reference(NumPy float64는 #5 A-7 권고 — **오너 확정 필요**), tolerance 비교(instance 파라미터), 반복 타이밍 · coversReq: FR-9, OD-16 최소분(FR-9 조항), OD-13 초기값
- [x] P1-4 하네스 3-상태 캘리브레이션 테스트(통과 커널 / 실패 커널 / 기능 통과·계약 위반 커널) — **OD-16 종결 필요(§9 ADR 경로)**(#7 S-2 N8의 제안이 OD-16에 흡수된 상태) · coversReq: OD-16
- [ ] P1-5 GEMM spec 예시(Llama 3.2 1B projection, M∈{1,32,512}, fp32)와 `spec.json` 스키마 — **OD-6 종결 필요(§9 ADR 경로)** · coversReq: FR-5, OD-6, #5 B-4
- [x] P1-6 CAS blob 저장(`blobs/sha256/..`, `artifacts.json`, retention class 기록) · coversReq: C-3(A-2)
- [x] P1-7 `hilclaw.config.json`(`data_repo.url`·`data_repo.local_path`, 환경변수 override — #5 A-1 세부 2) — 데이터 repo `HIL-Claw-data`는 2026-10-05 생성됨(D7; private, 빈 레이아웃) · coversReq: FR-13(A-1), #5 D7
- [ ] P1-8 런타임 STATE/instance/events 스키마(#4 §4) — **OD-8 종결 필요(§9 ADR 경로)** · coversReq: FR-13, NFR-1, OD-8·OD-17
- [ ] P1-9 런타임 자체 점검(인스턴스 bring-up이 런타임 머신에서 실행; P2-1 라운드 0이 호출): `claude auth status`로 CLI 로그인을 확인하고(미로그인이면 `claude auth login` 안내 후 중단) → 1회용 `claude -p`에 `--mcp-config`·`--strict-mcp-config`로 패키지 자신의 MCP front를 넘겨(좁은 권한 모드, bypass 금지) 핸드셰이크(`server/discover`·`initialize` 개정·`tools/list`)·도구 목록·호출 1회·도구 실패 1회가 모델에 닿는 모습을 관찰하며, front가 거부되면 bring-up 실패. 드라이버는 테스트가 만든 가짜 `claude` 스텁으로만 빌드·검증한다(실제 `claude` 금지 — D16). ADR에 기록: 런타임 사용자의 CLI 로그인이 인스턴스의 전제 조건임(C-7 ②·③의 파생; README·UsageCases에 명시), 점검이 쓰는 `--mcp-config` 경로와 run이 에이전트에 서버를 주는 방식(ADR-0010 148행, 미결)의 차이와 그로 인해 미관찰로 남는 것, 그리고 run 중 로그인 만료와 `-p`의 `--bare` 기본화 예고(bare 모드의 인증 동작은 ADR이 공식 문서에서 확인)는 판단만 하고 결정하지 않음. **기록의 저장 위치는 오너 미결** — 정해질 때까지 표준 출력과 인스턴스 로그에만 쓰고 데이터 plane 파일은 쓰지 않는다 · coversReq: FR-10, C-7, OD-18 ①, D16(오너 2026-10-13, HQ-0006 답변 b-2)

## P2 — 1층 런타임 오케스트레이션 (프롬프트·에이전트 정의)

- [ ] P2-1 Round-Manager 프롬프트·라운드 0(bring-up+baseline) 절차 · coversReq: FR-1
- [ ] P2-2 coder-driver(`claude -p` 호출, spec 전달, 출력 캡처) — **OD-23 종결 필요(§9 ADR 경로)**(로스터·입출력 계약, 논의중) · coversReq: FR-5, OD-23
- [ ] P2-3 evaluator(Write 권한 없음, 하네스만 호출) — **OD-16 종결 필요(§9 ADR 경로)** · coversReq: FR-9, OD-16
- [ ] P2-4 hooks: PreToolUse 예산·gate 검사, PostToolUse 저널링, Stop 커밋 강제 — **OD-18·OD-19 종결 필요(§9 ADR 경로)** · coversReq: FR-3·4·11, OD-18·19
- [ ] P2-6 가설 레코드와 판정(오너 결정 2026-10-13): 기법 선택이 가설·근거·예상 효과·출처를 구조화 기록으로 남기고 evaluate가 가설마다 판정·원인을 기록 — 스키마·파일 자리는 **OD-30 종결 필요(§9 ADR 경로)**; 2층의 스키마 검증·쓰기와 1층 프롬프트(P2-1·P2-3)에의 반영을 포함. 수행 순서는 나열 순서(P2-5보다 앞) — 첫 run이 사례를 남기도록 · coversReq: FR-11·17, OD-30·OD-23
- [ ] P2-7 가설–결과 사례 저장과 같은 키 정확 일치 조회(MVP 최소분, 오너 결정 2026-10-13): 라운드 종료 때 사례(기각·실패 포함)를 `db/<hw_profile_key>/<op_signature>/`에 저장, 기법 선택이 그 키의 사례를 읽고 참조를 결정 로그에 기록, instance 시작 시의 가설 주입 입력(FR-15) — **OD-30 종결 필요(§9 ADR 경로)**(사례 필드·싣는 사례의 선택; OD-20·OD-7과의 관계) · coversReq: FR-15·18, S11, OD-30·OD-20·OD-7
- [ ] P2-5 첫 end-to-end run: `cpu_standin` × GEMM, N=1, 5라운드 — 드라이버 task의 검증은 테스트가 만든 스텁 `claude`로 한다(D16); 드라이버 쪽에서 실제 `claude`를 쓰는 run은 P2-10의 nightly 루틴뿐이며(D17) 이 항목의 완료는 그 결과에 달려 있지 않다 · coversReq: S0, S1, S8(N=1), FR-17·18
- [ ] P2-8 S6 수용 기준의 계산 도구: 같은 키의 두 run의 기록에서 첫 run의 best에 도달하기까지의 라운드 수와 두 번째 run의 결정 로그에 든 사례 참조의 유무를 계산(fixture로 검증) — 지표 정의는 **OD-30 종결 필요(§9 ADR 경로)** · coversReq: S6, FR-18, OD-30
- P2-9 *(런타임 인수 항목 — 드라이버 task로 만들지 않는다, D16)* S6 수용 기준 측정: 오너가 런타임 머신에서 같은 키·target·tolerance·N·budget으로 run을 두 번(첫 run과 두 번째 run) 수행하고 P2-8의 도구로 판정한다 — 드라이버의 P2-5 검증(스텁 `claude`)의 run과 nightly 루틴의 run(P2-10, D17 ②)은 첫 run으로도 두 번째 run으로도 쓰지 않는다. P2-8이 체크된 뒤 planner가 처음 PLAN을 읽는 iteration(DRIVER §3-3)에 DRIVER §8의 HQ(사유 `runtime-acceptance`, `taskId` = P2-8의 task)를 한 번 올린다; 이미 올렸는지는 `PROCESS/STATE.json`의 `humanQuestions`로 판정하며 PLAN 본문에는 적지 않는다. phase 전환 조건에 들지 않으며 오너의 수동 확인으로만 닫힌다 · coversReq: S6, FR-18
- [ ] P2-10 nightly end-to-end 루틴(오너 결정 2026-10-13, DRIVER D17): DRIVER §3을 수행하는 드라이버와 분리된 별도 루틴이 런타임 오케스트레이터를 만들어 실제 `claude`로 end-to-end run을 돌리고(run의 구성은 미정 — 출발점 후보는 P2-5의 구성) 통과·실패와 로그를 회귀 신호로 남긴다 — 수용 기준(P2-9)과 사례 저장(FR-18)에는 쓰지 않는다. 실패는 이슈로 등록된 뒤 자동으로 해결된다(오너, D17 ④) — 해결하는 것은 DRIVER §3을 수행하는 드라이버이고 환경이 원인인 실패는 HQ로 간다(D17 행의 "따름"); 이슈가 task가 되는 방법을 포함해 그 흐름의 나머지는 D17 행의 (나)다. 이 항목의 task는 루틴의 절차 문서와 그것이 부르는 진입점을 만들며 실제 `claude`를 시작하지 않는다(실제 `claude`는 nightly 루틴만 시작한다); 진입점의 자리와 모드(코드/문서)는 task에서 정하고 테스트는 CLAUDE.md 테스트 규칙을 따른다(규칙 ⑤의 대상이면 테스트를 추가하지 않는다). 루틴 등록은 오너가 한다. D17 행의 "정하지 않은 것" 가운데 (가)는 task를 만들기 전에 DRIVER §8의 HQ로 묻고, (나)는 여기서 정한다. P2-5 뒤에 수행 · coversReq: S0, S1, D17

## P3 이후 (초안만)

- Best-of-N(N≤5) 실행·승격 정책(OD-29), LAN 백엔드(SSH)·`board.run` 원격(B-2 대기), attention/KV cache 커널(B-4 2차), 기법 카탈로그 콜드스타트(OD-22), 크로스런 통계의 랭킹 신호·유사 키 사례 활용(OD-7·OD-4 잔여 — 가설 레코드는 P2-6, 사례 저장과 정확 일치 조회는 P2-7), 알림(OD-27).
- **예약(오너, 2026-10-13 채팅) — 지원 대상 순서와 2번째 대상**: 1번째 지원 대상은 CPU(현재의 `cpu_standin` 백엔드, #5 A-7 — 통합자 독해), **2번째 지원 대상은 Qualcomm NPU**다. QNN·AIMET 등을 이용해 HuggingFace의 주요 On-Device LLM 모델(3B급)을 최적화한다 — 목표 산출물은 더 빠르게 동작하고 더 적은 메모리를 쓰면서 품질 성능은 유지·향상되는 **양자화 모델**. 예약일 뿐이며 planner는 이 항목을 task로 만들지 않는다. **오너 확정 필요** — 위 문장에 없는 것은 어느 것도 정해지지 않았고, 이 항목은 #5 B-1·B-2·B-3·B-5(OD-9)·B-8·A-4의 어느 부분도 닫지 않는다. 정해지지 않은 것의 예(완결된 목록이 아니다): 대상 SoC·SDK 버전, 대상 모델 목록, 모델 입력 포맷·frontend 경계, 양자화 방식, 품질 지표와 평가 데이터, simulator 유무·종류, 실행 장비 접근 방식, 3층 코더의 역할, 단일 compute-kernel 범위(C-6)와 모델 단위 양자화 산출물의 관계.
