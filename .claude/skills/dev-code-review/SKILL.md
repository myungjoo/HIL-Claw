---
name: dev-code-review
description: "HIL-Claw 표준 코드 리뷰 지침: 주어진 Pull Request에 대해 범위 규율·Regression·테스트 완비·문서 동기화·보안을 점검하고 PR에 Comment를 남긴다."
---

주어진 대상 Pull Request에 대해 다음의 지침으로 코드 리뷰를 수행하라.

* 리뷰 대상 코드 변경사항과 기존 Repository 내 내용, Target Software가 사용하는 외부 Library들을 모두 분석 대상으로 하되, 리뷰 지적 대상은 지정된 코드 변경사항으로 제한한다.
* 주어진 주제를 해결하고 있는지 검사하라.
* 기존 기능이나 성능을 해치지 않는지 검사하라. 특히 타 모듈에 Regression을 일으킬 수 있는지 점검하라.
* 코드 크기가 주제에 비해 지나치게 크거나, 불필요하게 다른 모듈을 건드리지 않는지 검사하라.
* 코드 내용을 검증하고, 미래에 문제가 발생하지 않도록 막기 위해 필요한 test case가 완비되었는지 검사하라.
* 미래에 타 모듈의 기능 추가로 인해 검사 대상 코드의 기능과 성능에 영향을 받게 되었을 때에 그 영향을 바로 Detect할 수 있도록 Test Case가 있는지 검사하라.
* Test Case로 찾아진 Issue가 있을 때에 CI가 Fail이 나서 해당 문제를 일으킨 코드가 Merge되지 않도록 막을 수 있는지 점검하라. (CI 미구축 동안에는 Local Test로 검출 가능한지를 점검한다.)
* ARCHITECTURE 변경을 일으키거나 API 변경이 있는 경우 그와 관련한 문서 수정이 PR 내에서 함께 이뤄지거나, 문서 수정이 이미 되어 있는지 점검하라. 특히 ARCHITECTURE/ 문서(Requirements, UsageCases, StandardScenarios)에 영향이 있는 변경이면 [StandardScenarios.md](../../../ARCHITECTURE/StandardScenarios.md)의 검사 규칙(지원/미결/갭)에 따른 커버리지 재검사가 수행·갱신되었는지 확인하라.
* 미결정 사항이 발명되어 코드/문서에 확정처럼 들어가지 않았는지 점검하라. 미결은 Requirements.md의 Open Decisions(OD)로 등재되어야 한다.
* 보안 이슈를 만들 수 있는 부분이 있는지 점검하며, 혹시 Back Door 가능성이 있는 코드가 있는지도 확인하라. Back Door 가능성이 있는 코드가 발견될 경우 myungjoo-ham 에게도 Notify (mention) 하라.
* 이슈가 있을 경우 이슈 심각성과 문제인 이유와 함께 PR에 Comment를 남긴다. 단, 타 Agent가 작성한 리뷰를 옮겨 적은 것임을 명시하라.
