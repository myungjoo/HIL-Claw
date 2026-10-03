# 개발 PLAN

[DRIVER.md](DRIVER.md) §6 planner의 입력. phase 안의 항목은 **체크리스트**이며 각 항목은 1개 이상의 task(`tasks/`)로 쪼개진다. `coversReq`는 추적용 ID — Requirements ID(FR/NFR/C/OD), 오너 결정 ID(#5 A-n·B-n), 이슈(#9), 또는 DRIVER.md 절. 완료된 phase는 그대로 두고 체크만 한다(감사성). "**확정 필요**" 표시가 있는 항목은 해당 OD/결정이 닫히기 전까지 planner가 건너뛴다(DRIVER §6·§9). ⚑ = DRIVER §11의 결정 요청에 걸린 항목.

현재 phase: `PROCESS/STATE.json`의 `phase`가 정본.

## P0 — 저장소 골격 (bootstrap) — ⚑ D9(골격 task에 "첫 커밋 전 확정" 규칙 비적용) 승인 후 시작

- [ ] P0-1 저장소 공통 규칙: `.gitattributes`(LF 강제 — C-7 ①의 파생·#9), `.editorconfig`, 2층 패키지 디렉토리 생성(가칭 `hilclaw/`, 빈 패키지 + 버전) — code 모드 · coversReq: C-7, FR-10, #9
- [ ] P0-2 Python 프로젝트 설정: `pyproject.toml`(최소 버전·pytest·ruff), 첫 smoke 테스트 1개 · coversReq: CLAUDE.md 언어 정책, #9
- [ ] P0-3 CI 스켈레톤(#9): PR에 Python 게이트(pytest+ruff) 1개, Linux 러너. required check 설정은 ⚑ D10(A-13 "branch protection 없음"과 상충 — #8 등재) · coversReq: #9
- [ ] P0-4 `PROCESS/STATE.json` JSON Schema(DRIVER §2 표를 기계화). 검증 **테스트** 추가 여부는 ⚑ D12(도구 코드 테스트는 오너 명시 요구 시만) · coversReq: DRIVER §2·§4·§8
- [ ] P0-5 README 갱신: 세 층 모델·개발 절차 포인터(PROCESS/, CLAUDE.md) — doc 모드 · coversReq: #5 A-12

## P0.5 — 게이트 보강

- [ ] P0.5-1 sh 게이트(shellcheck) · C 게이트(clang 빌드 + 하네스 통과) CI 추가 · coversReq: #9
- [ ] P0.5-2 ⚑ D12 테스트 존재 검사(새 2층 모듈에 테스트 파일 없으면 CI 실패) — #9 범위 밖의 신규 게이트 · coversReq: dev-code-review "테스트 완비"
- [ ] P0.5-3 ⚑ D12 커버리지 게이트(임계값 포함) — #9 범위 밖의 신규 게이트 · coversReq: #9

## P1 — 2층 도구 패키지 (MVP 핵심 부품)

- [ ] P1-1 FR-10 도구 계약(`sim.run`/`board.run`/`profiler.collect`/`correctness.check`, `blob.push/fetch`) 인터페이스 + **mock 백엔드** + 백엔드 적합성 테스트 · coversReq: FR-10, C-3(A-2)
- [ ] P1-2 `cpu_standin` 어댑터: clang 빌드 래퍼, 로컬 실행, 타이밍 수집(OpenMP/SIMD 허용) · coversReq: FR-10, #5 A-7, C-7
- [ ] P1-3 하네스 `harness/`: 무작위 입력(비파일 시드), f64 reference(NumPy float64는 #5 A-7 권고 — **확정 대기**), tolerance 비교(instance 파라미터), 반복 타이밍 · coversReq: FR-9, OD-16 최소분(FR-9 조항), OD-13 초기값
- [ ] P1-4 하네스 3-상태 캘리브레이션 테스트(통과 커널 / 실패 커널 / 기능 통과·계약 위반 커널) — **OD-16 확정 필요**(#7 S-2 N8의 제안이 OD-16에 흡수된 상태) · coversReq: OD-16
- [ ] P1-5 GEMM spec 예시(Llama 3.2 1B projection, M∈{1,32,512}, fp32)와 `spec.json` 스키마 — **OD-6 확정 필요**(DRIVER §9) · coversReq: FR-5, OD-6, #5 B-4
- [ ] P1-6 CAS blob 저장(`blobs/sha256/..`, `artifacts.json`, retention class 기록) · coversReq: C-3(A-2)
- [ ] P1-7 `HIL-Claw-data` repo 생성·`hilclaw.config.json` — **오너 지시 필요(⚑ D7)** · coversReq: FR-13(A-1)
- [ ] P1-8 런타임 STATE/instance/events 스키마(#4 §4) — **OD-8 확정 필요**(DRIVER §9) · coversReq: FR-13, NFR-1, OD-8·OD-17

## P2 — 1층 런타임 오케스트레이션 (프롬프트·에이전트 정의)

- [ ] P2-1 Round-Manager 프롬프트·라운드 0(bring-up+baseline) 절차 · coversReq: FR-1
- [ ] P2-2 coder-driver(`claude -p` 호출, spec 전달, 출력 캡처) — **OD-23 확정 필요**(로스터·입출력 계약, 논의중) · coversReq: FR-5, OD-23
- [ ] P2-3 evaluator(Write 권한 없음, 하네스만 호출) — **OD-16 확정 필요** · coversReq: FR-9, OD-16
- [ ] P2-4 hooks: PreToolUse 예산·gate 검사, PostToolUse 저널링, Stop 커밋 강제 — **OD-18·OD-19 확정 필요** · coversReq: FR-3·4·11, OD-18·19
- [ ] P2-5 첫 end-to-end run: `cpu_standin` × GEMM, N=1, 5라운드 · coversReq: S0, S1, S8(N=1)

## P3 이후 (초안만)

- Best-of-N(N≤5) 실행·승격 정책(OD-29), LAN 백엔드(SSH)·`board.run` 원격(B-2 대기), attention/KV cache 커널(B-4 2차), 기법 카탈로그 콜드스타트(OD-22), 크로스런 통계(OD-7), 알림(OD-27).
