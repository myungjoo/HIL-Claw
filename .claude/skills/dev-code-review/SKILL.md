---
name: dev-code-review
description: "HIL-Claw 표준 코드 리뷰 지침: 주어진 Pull Request(문서 모드는 브랜치 diff)에 대해 범위 규율·Regression·테스트 완비·문서 동기화·보안을 점검하고 PR에 Comment를 남기거나 호출자에게 결과를 반환한다."
---

주어진 대상 Pull Request에 대해 다음의 지침으로 코드 리뷰를 수행하라. 대상이 PR Number가 아니라 브랜치 이름으로 주어지면 **문서 모드**(CLAUDE.md "브랜치·merge 절차", #5 A-13)이며, 그 브랜치의 `origin/main` 대비 diff를 리뷰한다.

* 리뷰 대상 코드 변경사항과 기존 Repository 내 내용, Target Software가 사용하는 외부 Library들을 모두 분석 대상으로 하되, 리뷰 지적 대상은 지정된 코드 변경사항으로 제한한다.
* 주어진 주제를 해결하고 있는지 검사하라.
* 기존 기능이나 성능을 해치지 않는지 검사하라. 특히 타 모듈에 Regression을 일으킬 수 있는지 점검하라.
* 코드 크기가 주제에 비해 지나치게 크거나, 불필요하게 다른 모듈을 건드리지 않는지 검사하라.
* 코드 내용을 검증하고, 미래에 문제가 발생하지 않도록 막기 위해 필요한 test case가 완비되었는지 검사하라.
* 코드 모드 변경이면 CLAUDE.md "테스트 규칙"(#5 D12)을 점검하라: 2층 패키지 line·function coverage ≥ 80% 유지, negative case 포함, 건드린 모듈의 모든 public 함수 테스트, 2층 패키지 새 모듈의 대응 테스트 파일. 테스트 코드·CI 워크플로·hook·보조 스크립트를 대상으로 하는 테스트가 명시 예외 밖에서 추가되었거나, 테스트가 필수인 명시 예외 두 개(CLAUDE.md)에 테스트가 빠졌으면 지적하라.
* 미래에 타 모듈의 기능 추가로 인해 검사 대상 코드의 기능과 성능에 영향을 받게 되었을 때에 그 영향을 바로 Detect할 수 있도록 Test Case가 있는지 검사하라.
* Test Case로 찾아진 Issue가 있을 때에 CI가 Fail이 나서 해당 문제를 일으킨 코드가 Merge되지 않도록 막을 수 있는지 점검하라. (CI 미구축 동안에는 Local Test로 검출 가능한지를 점검한다.)
* ARCHITECTURE 변경을 일으키거나 API 변경이 있는 경우 그와 관련한 문서 수정이 PR 내에서 함께 이뤄지거나, 문서 수정이 이미 되어 있는지 점검하라. 특히 ARCHITECTURE/ 문서(Requirements, UsageCases, StandardScenarios)에 영향이 있는 변경이면 [StandardScenarios.md](../../../ARCHITECTURE/StandardScenarios.md)의 검사 규칙(지원/미결/갭)에 따른 커버리지 재검사가 수행·갱신되었는지 확인하라.
* 미결정 사항이 발명되어 코드/문서에 확정처럼 들어가지 않았는지 점검하라. 미결은 Requirements.md의 Open Decisions(OD)로 등재되어야 한다.
* 변경의 구현·테스트·검증이 개발 드라이버를 런타임의 대역으로 쓰는지 점검하라 — Claude Code 자식 세션 시작, 개발 머신에 없는 보드·가속기, `claude` 로그인·API 키 같은 런타임 자격 증명 중 하나라도 전제하면 Request changes다(CLAUDE.md "개발 드라이버와 런타임의 구분", DRIVER D16). 런타임 코드 자체가 런타임 머신에서 `claude -p`를 띄우는 변경과 테스트가 만든 가짜 `claude` 스텁은 해당하지 않는다. DRIVER D17의 nightly end-to-end 루틴의 절차를 정의하는 변경도 해당하지 않는다 — 단 그 변경을 만드는 드라이버 task의 검증은 스텁으로만 한다.
* 보안 이슈를 만들 수 있는 부분이 있는지 점검하며, 혹시 Back Door 가능성이 있는 코드가 있는지도 확인하라. Back Door 가능성이 있는 코드가 발견될 경우 myungjoo-ham 에게도 Notify (mention) 하라.
* 이슈가 있을 경우 이슈 심각성과 문제인 이유와 함께 PR에 Comment를 남긴다(코드 모드). 단, 타 Agent가 작성한 리뷰를 옮겨 적은 것임을 명시하라.
* 지적마다 심각성을 표시하라(PROCESS/DRIVER.md D20). **Must-fix**: 정확성·Regression·보안 결함, CLAUDE.md·DRIVER 규칙 위반, 미결 발명, 테스트 규칙 미충족. **Should-fix**: 결함은 아니나 이번 변경 안에서 고쳐야 할 문제(빠진 테스트 케이스, 오해를 부르는 서술, 범위에 든 문서의 누락 등). **Nit**: 결정·동작·테스트·인터페이스의 의미를 바꾸지 않는 지적(문구·오타·인용 위치·서식·주석). Must-fix나 Should-fix가 하나라도 있으면 판정은 Request changes, **남은 지적이 Nit뿐이면 Approve**다. 판정은 두 모드 모두 결과의 첫 줄(`SECURITY` 표시가 있으면 그 다음 줄)에 `Verdict: Approve` 또는 `Verdict: Request changes`로 적는다.
* 문서 모드에서는 PR Comment 대신 판정(Approve / Request changes)과 지적 목록(심각성·이유·위치)을 호출자에게 반환한다. 문서 모드 변경에 문서·프로세스 파일이 아닌 것이 섞여 있으면 Request changes로 반환한다. Back Door·보안 의심이 있으면 반환 결과 첫 줄에 `SECURITY`로 표시하여 호출자가 BLOCKED(보안 의심)로 처리하게 한다.
