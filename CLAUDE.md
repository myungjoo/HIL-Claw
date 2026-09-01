# HIL-Claw 개발 가이드 (Claude Code 세션 공통)

## 표준 개발 프로세스

- 코드/문서 변경 작업(이슈 해결, 기능 추가, 리팩토링)은 [dev-item-address](.claude/skills/dev-item-address/SKILL.md) 스킬 절차를 따른다.
- PR 코드 리뷰는 [dev-code-review](.claude/skills/dev-code-review/SKILL.md) 스킬 지침을 따른다.
- 이 repo의 `.claude/skills/` 가 canonical이다. 개인 클라이언트에 등록된 유사 스킬(github-item-address, github-code-review)보다 우선한다.

## 상시 규칙

- **코멘트 최소화**: 코드로 파악 가능한 내용은 코멘트하지 않는다. Multi-line comment는 지양한다. 변경 전반의 설명은 코드 코멘트가 아닌 Git Commit Message 본문에 기입한다. 예외: 파일 Boilerplate와 외부 노출 API의 Doxygen(유사 방식) 문서화는 충분히 길어도 된다.
- **문서 커버리지 재검사**: `ARCHITECTURE/` 문서(Requirements, UsageCases, StandardScenarios)를 변경하면 [StandardScenarios.md](ARCHITECTURE/StandardScenarios.md)의 검사 규칙(지원/미결/갭)으로 커버리지를 재검사하고 검사 결과 섹션을 갱신한다.
- **미결은 발명하지 않는다**: 미확정 사항은 사용자에게 확인받거나 [Requirements.md](ARCHITECTURE/Requirements.md)의 Open Decisions(OD)로 등재한다. 사용자 확정 없이 미결을 확정으로 취급하지 않는다.
- **브랜치 작업**: main 직접 커밋 대신 브랜치 + PR을 기본으로 한다. main으로의 merge/push는 사용자 지시가 있을 때만 수행한다.
- **모델 배정 원칙**: 판단·설계·리뷰·리뷰대응 단계는 상위(고성능) 모델, 기계적 단계(테스트 작성, 로컬 테스트 실행, 커밋/PR 작성)는 경량 모델에 위임 가능. 특정 모델명을 프로세스에 하드코딩하지 않는다.

## 현재 프로젝트 상태 주의사항

- **CI 미구축**: 프로세스의 CI 단계는 CI 구축 전까지 로컬 테스트 재수행으로 대체한다.
- **바이너리 금지**: 바이너리·대용량 산출물은 git에 넣지 않는다(확정 결정 A-2: CAS `blobs/` + 해시 참조; 데이터는 별도 `HIL-Claw-data` repo — 확정 결정 A-1).
- **MVP 범위**: 방법 B(Claude Code Orchestrator), 단일 compute-kernel 최적화, Phase 1은 Git tree가 DB를 대신. 자세한 것은 [ARCHITECTURE/](ARCHITECTURE/) 문서와 GitHub Issue #2·#4·#5 참조.
