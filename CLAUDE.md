# HIL-Claw 개발 가이드 (Claude Code 세션 공통)

## 표준 개발 프로세스

- 코드/문서 변경 작업(이슈 해결, 기능 추가, 리팩토링)은 [dev-item-address](.claude/skills/dev-item-address/SKILL.md) 스킬 절차를 따른다.
- PR 코드 리뷰는 [dev-code-review](.claude/skills/dev-code-review/SKILL.md) 스킬 지침을 따른다.
- 이 repo의 `.claude/skills/` 가 canonical이다. 개인 클라이언트에 등록된 유사 스킬(github-item-address, github-code-review)보다 우선한다.
- Assessment-Agent(`myungjoo/Assessment-Agent`)는 **개발 절차의 참조**일 뿐이다. 그 SW 구조·스택·디렉토리 레이아웃은 가져오지 않는다 — 두 시스템의 아키텍처가 유사할 필요는 없다(오너 2026-10-02, #5 A-12).

## 상시 규칙

- **코멘트 최소화**: 코드로 파악 가능한 내용은 코멘트하지 않는다. Multi-line comment는 지양한다. 변경 전반의 설명은 코드 코멘트가 아닌 Git Commit Message 본문에 기입한다. 예외: 파일 Boilerplate와 외부 노출 API의 Doxygen(유사 방식) 문서화는 충분히 길어도 된다.
- **문서 커버리지 재검사**: `ARCHITECTURE/` 문서(Requirements, UsageCases, StandardScenarios)를 변경하면 [StandardScenarios.md](ARCHITECTURE/StandardScenarios.md)의 검사 규칙(지원/미결/갭)으로 커버리지를 재검사하고 검사 결과 섹션을 갱신한다.
- **미결은 발명하지 않는다**: 미확정 사항은 사용자에게 확인받거나 [Requirements.md](ARCHITECTURE/Requirements.md)의 Open Decisions(OD)로 등재한다. 사용자 확정 없이 미결을 확정으로 취급하지 않는다. OD 등록부에는 한 줄 요약만 두고 제안 본문은 [OpenDecisionProposals.md](ARCHITECTURE/OpenDecisionProposals.md)에 쓴다.
- **세션 진입 점검**: `ARCHITECTURE/` 문서나 OD 번호를 건드리기 전에 열린 PR(`gh pr list`)과 Issue #4(아키텍처 결정 스레드·작업 항목)·#5(사용자 결정 대기)·#7(외부 조사)·#8(모순 트래커)을 먼저 확인한다. 열린 PR이 같은 표·절을 수정 중이면 편집 전에 사용자에게 알린다. (2026-07~09에 미merge PR과 main이 같은 OD 번호를 다른 뜻으로 써 5주간 분기한 사고의 재발 방지 — #8 M23)
- **세 층 모델**(#5 A-12): 저장소는 **1층** = Claude Code 오케스트레이션(CLAUDE.md·스킬·`.claude/agents` 정의·기법 Skill, Markdown), **2층** = 1층 에이전트가 호출하는 결정적 도구 패키지(FR-10 도구·백엔드·CAS·스키마 검증·hook 진입점·검증 하네스), **3층** = 코더(`claude -p`)가 산출하는 C 커널로 나뉜다. 언어 정책은 2층에만 해당한다.
- **도구 계층 언어 정책**(#5 A-12): 2층의 허용 언어는 **{Python, POSIX sh, C}**. 도구별 언어는 목적에 따라 task마다 개발 에이전트가 고르고 선택 이유를 commit 본문에 한 줄 기록한다. 집합 밖 언어는 ADR 없이 쓰지 않는다(ADR 양식·위치는 첫 필요 시점에 정한다). 언어별 CI 게이트(Python: pytest+ruff / sh: shellcheck / C: clang 빌드 + 하네스 통과)는 사전 구축한다(#9).
- **브랜치·merge 절차**(오너 2026-10-02, #5 A-13 — Assessment-Agent 절차 채택): 작업은 항상 브랜치에서 한다. **문서 모드**(`ARCHITECTURE/`·`CLAUDE.md`·`.claude/`·`README.md`, 그리고 `PROCESS/`(DRIVER.md §2) — 문서·프로세스 파일만 변경)는 컨텍스트 격리 리뷰어 사이클(dev-item-address 10~12단계)을 통과하면 `origin/main`에 rebase한 뒤 PR 없이 **main에 직접 push**하며, 커밋 메시지에 `Reviewed-by: reviewer agent (N rounds, Approve)` trailer를 리뷰 기록으로 남긴다. **코드 모드**(그 외 — 2층 패키지·CI 워크플로·테스트)는 Draft PR + 리뷰 사이클 + CI green(CI 구축 전: 로컬 테스트)을 통과하면 **스스로 squash-merge**하고 브랜치를 지운다. 사용자 개입은 **BLOCKED 사유**(새 외부 의존성, 데이터 plane 스키마 변경(STATE/spec/eval/artifacts), 리뷰 7라운드 초과, CI 3연속 실패, 요구 불명확·미결 발명 의심, 보안 의심)에 한정한다. branch protection은 두지 않는다.
- **테스트 규칙**(오너 2026-10-05, #5 D12): 코드 모드 변경의 테스트는 ① 2층 패키지(`hilclaw/`)의 line coverage ≥ 80%·function coverage ≥ 80%를 유지하고 ② happy/error/branch에 더해 **negative case**(잘못된 입력·실패 경로)를 포함하며 ③ 건드린 모듈의 모든 public 함수를 다루고 ④ 2층 패키지의 새 모듈에는 대응 테스트 파일을 둔다. ⑤ 테스트 코드·테스트 스위트·테스트 스크립트, CI 워크플로, hook 스크립트, 드라이버 보조 스크립트를 대상으로 하는 테스트는 추가하지 않는다 — 명시 예외는 드라이버 `STATE.json` 스키마 검증기와 `gh pr merge` 가드 hook 두 개뿐이며, 이 둘은 테스트가 필수다.
- **모델 배정 원칙**: 판단·설계·리뷰·리뷰대응 단계는 상위(고성능) 모델, 기계적 단계(테스트 작성, 로컬 테스트 실행, 커밋/PR 작성)는 경량 모델에 위임 가능. 특정 모델명을 프로세스에 하드코딩하지 않는다.

## 현재 프로젝트 상태 주의사항

- **CI 미구축**: 프로세스의 CI 단계는 CI 구축 전까지 로컬 테스트 재수행으로 대체한다.
- **바이너리 금지**: 바이너리·대용량 산출물은 git에 넣지 않는다(확정 결정 A-2: CAS `blobs/` + 해시 참조; 데이터는 별도 `HIL-Claw-data` repo — 확정 결정 A-1).
- **MVP 범위**: 방법 B(Claude Code Orchestrator), 단일 compute-kernel 최적화, Phase 1은 Git tree가 DB를 대신. 자세한 것은 [ARCHITECTURE/](ARCHITECTURE/) 문서와 GitHub Issue #2·#4·#5 참조.
