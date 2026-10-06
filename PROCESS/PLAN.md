# 개발 PLAN

[DRIVER.md](DRIVER.md) §6 planner의 입력. phase 안의 항목은 **체크리스트**이며 각 항목은 1개 이상의 task(`tasks/`)로 쪼개진다. `coversReq`는 추적용 ID — Requirements ID(FR/NFR/C/OD), 오너 결정 ID(#5 A-n·B-n·D-n), 이슈(#9), 또는 DRIVER.md 절. 완료된 phase는 그대로 두고 체크만 한다(감사성). 표시 규약: "**오너 확정 필요**"(#5 A·B 항목, C-6, OD-25, OD-3) 항목은 그 결정이 닫히기 전까지 planner가 건너뛴다; "**OD-n 종결 필요(§9)**" 항목은 그 OD를 닫는 ADR 작성을 포함한 task로 만든다(DRIVER §6·§9, D6). DRIVER §11의 D1~D13은 모두 답변되어(2026-10-06) 본 PLAN에 ⚑ 항목은 없다.

현재 phase: `PROCESS/STATE.json`의 `phase`가 정본.

## P0 — 저장소 골격 (bootstrap) — D9 확정(2026-10-05): 골격 task에는 "첫 커밋 전 OD-4/6/8 확정" 규칙을 적용하지 않음

- [x] P0-1 저장소 공통 규칙: `.gitattributes`(LF 강제 — C-7 ①의 파생·#9), `.editorconfig`, 2층 패키지 디렉토리 생성(가칭 `hilclaw/`, 빈 패키지 + 버전) — code 모드 · coversReq: C-7, FR-10, #9
- [x] P0-2 Python 프로젝트 설정: `pyproject.toml`(최소 버전·pytest·ruff), 첫 smoke 테스트 1개 · coversReq: CLAUDE.md 언어 정책, #9
- [ ] P0-3 CI 스켈레톤(#9): PR과 main push에 Python 게이트(pytest+ruff) 1개, Linux 러너. required check는 두지 않음(D10 확정: 절차 게이트 + merge 가드 hook P0.5-4; #8 M24 해소) · coversReq: #9, #5 D10
- [x] P0-4 `PROCESS/STATE.json` JSON Schema(DRIVER §2 표를 기계화) + 검증기. 검증기 테스트는 **명시 요구됨**(D12 예외 ①) · coversReq: DRIVER §2·§4·§8, #5 D12
- [ ] P0-5 README 갱신: 세 층 모델·개발 절차 포인터(PROCESS/, CLAUDE.md) — doc 모드 · coversReq: #5 A-12
- [ ] P0-6 개발 프로세스 agent 정의: `.claude/agents/dev-planner.md`·`dev-executor.md`·`dev-reviewer.md` — 컨텍스트 격리 subagent, 허용 도구 frontmatter(모델은 CLAUDE.md 배정 원칙 — 모델명 하드코딩 금지), 기존 스킬 2개를 감쌈(DRIVER §7; 이름·도구 제한은 이 task에서 리뷰로 확정) — doc 모드 · coversReq: #5 D5, A-13

## P0.5 — 게이트 보강

- [ ] P0.5-1 sh 게이트(shellcheck) · C 게이트(clang 빌드 + 하네스 통과) CI 추가 · coversReq: #9
- [ ] P0.5-2 테스트 존재 검사(D12 확정): `hilclaw/`의 새 모듈에 대응 테스트 파일이 없으면 CI 실패 · coversReq: #5 D12, dev-code-review "테스트 완비"
- [ ] P0.5-3 커버리지 게이트(D12 확정): `hilclaw/` **line ≥ 80%·function ≥ 80%**; branch 임계는 데이터가 쌓인 뒤 · coversReq: #5 D12, #9
- [ ] P0.5-4 merge 가드 hook(D10 확정): `PreToolUse`가 `gh pr merge`를 가로채 PR checks가 전부 success가 아니면 거부. hook 테스트는 **명시 요구됨**(D12 예외 ②). 배치(P0.5)는 통합자 선택 — 오너 선택지는 "P2-4와 함께 또는 저렴하면 P0-3과 함께" · D13(2026-10-06) 이후 금지 명령(`git push --force*`·`rm -rf *`·`gh repo delete *`)의 PreToolUse 가드도 같은 hook에서 검토(follow-up — 범위 포함 여부는 P0.5-4 task 작성 시 planner/executor가 §9 기준으로 정함; 오너 전용 결정 아님) · coversReq: #5 D10·D12, OD-18

## P1 — 2층 도구 패키지 (MVP 핵심 부품)

- [ ] P1-1 FR-10 도구 계약(`sim.run`/`board.run`/`profiler.collect`/`correctness.check`, `blob.push/fetch`) 인터페이스 + **mock 백엔드** + 백엔드 적합성 테스트 · coversReq: FR-10, C-3(A-2)
- [ ] P1-2 `cpu_standin` 어댑터: clang 빌드 래퍼, 로컬 실행, 타이밍 수집(OpenMP/SIMD 허용) · coversReq: FR-10, #5 A-7, C-7
- [ ] P1-3 하네스 `harness/`: 무작위 입력(비파일 시드), f64 reference(NumPy float64는 #5 A-7 권고 — **오너 확정 필요**), tolerance 비교(instance 파라미터), 반복 타이밍 · coversReq: FR-9, OD-16 최소분(FR-9 조항), OD-13 초기값
- [ ] P1-4 하네스 3-상태 캘리브레이션 테스트(통과 커널 / 실패 커널 / 기능 통과·계약 위반 커널) — **OD-16 종결 필요(§9 ADR 경로)**(#7 S-2 N8의 제안이 OD-16에 흡수된 상태) · coversReq: OD-16
- [ ] P1-5 GEMM spec 예시(Llama 3.2 1B projection, M∈{1,32,512}, fp32)와 `spec.json` 스키마 — **OD-6 종결 필요(§9 ADR 경로)** · coversReq: FR-5, OD-6, #5 B-4
- [ ] P1-6 CAS blob 저장(`blobs/sha256/..`, `artifacts.json`, retention class 기록) · coversReq: C-3(A-2)
- [ ] P1-7 `hilclaw.config.json`(`data_repo.url`·`data_repo.local_path`, 환경변수 override — #5 A-1 세부 2) — 데이터 repo `HIL-Claw-data`는 2026-10-05 생성됨(D7; private, 빈 레이아웃) · coversReq: FR-13(A-1), #5 D7
- [ ] P1-8 런타임 STATE/instance/events 스키마(#4 §4) — **OD-8 종결 필요(§9 ADR 경로)** · coversReq: FR-13, NFR-1, OD-8·OD-17

## P2 — 1층 런타임 오케스트레이션 (프롬프트·에이전트 정의)

- [ ] P2-1 Round-Manager 프롬프트·라운드 0(bring-up+baseline) 절차 · coversReq: FR-1
- [ ] P2-2 coder-driver(`claude -p` 호출, spec 전달, 출력 캡처) — **OD-23 종결 필요(§9 ADR 경로)**(로스터·입출력 계약, 논의중) · coversReq: FR-5, OD-23
- [ ] P2-3 evaluator(Write 권한 없음, 하네스만 호출) — **OD-16 종결 필요(§9 ADR 경로)** · coversReq: FR-9, OD-16
- [ ] P2-4 hooks: PreToolUse 예산·gate 검사, PostToolUse 저널링, Stop 커밋 강제 — **OD-18·OD-19 종결 필요(§9 ADR 경로)** · coversReq: FR-3·4·11, OD-18·19
- [ ] P2-5 첫 end-to-end run: `cpu_standin` × GEMM, N=1, 5라운드 · coversReq: S0, S1, S8(N=1)

## P3 이후 (초안만)

- Best-of-N(N≤5) 실행·승격 정책(OD-29), LAN 백엔드(SSH)·`board.run` 원격(B-2 대기), attention/KV cache 커널(B-4 2차), 기법 카탈로그 콜드스타트(OD-22), 크로스런 통계(OD-7), 알림(OD-27).
