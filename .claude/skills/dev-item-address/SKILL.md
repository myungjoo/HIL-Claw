---
name: dev-item-address
description: "HIL-Claw 표준 개발 프로세스: Github Issue나 지정된 주제에 대해 PR을 만들고 Review/Test Cycle을 돌려 Merge 가능한 수준까지 발전시킨다. 코드/문서 변경 작업(이슈 해결, 기능 추가, 리팩토링)에 사용."
---

[사용자가 지정하는 개발 대상 주제나 이슈]에 대해서 다음의 작업을 진행하라.

모델 배정 원칙: **(판단)** 표기 단계는 상위(고성능) 모델이 수행하고, **(기계적)** 표기 단계는 경량 모델(subagent)에 위임할 수 있다. 특정 모델명을 하드코딩하지 않는다.

1. 해당 Item이 정말 고쳐야 하는 이슈이고, 현재의 최신 main 기준으로 아직 고쳐지지 않은 Issue인지 확인. **(판단)**

2. 해당 Item을 고치기 위한 계획 및 구현 방법 결정. **(판단)** 단, 해당 구현이 덩치가 크거나 타 모듈에의 영향이 클 수 있으면, Architecture 변경 사항을 분석/점검하고 사용자에게 주요 쟁점과 이슈를 요약하여 설명한 뒤 합의를 보고 그 다음 단계를 진행해야 한다. 미결정 사항은 발명하지 말고 사용자에게 확인받거나 Requirements.md의 Open Decisions(OD)로 등재한다.

3. 해당 Item을 고치는 코드 작성. **(판단)**
   - 지나친 코멘트 작성은 피한다. 코드 내용으로 파악 가능한 내용은 굳이 코멘트하지 않는다. Multi-line comment 추가는 가능한 피한다.
   - Code Change 전반에 대한 설명은 코드 내 Comment가 아닌 Git Commit Message 본문에 기입한다.
   - 파일의 Boilerplate나 외부에 노출되는 API function에 대한 Doxygen(혹은 유사 방법) 등은 충분한 설명이 상대적으로 긴 Comment로 남아도 좋다.

4. 작성된 코드를 검증하고 타 기능에 영향 없음을 증명하며, 미래의 해당 Item에 대한 Regression을 막는 Test Case들의 추가. **(기계적)**

5. 작성된 코드가 잠재적으로 영향을 미칠 수 있는 타 모듈들을 점검. **(판단)**

6. 해당 타 모듈에 이번 코드 수정이 악영향(기능/비기능 모든 면에서)을 미치지 않는지 검사할 수 있는 Test Case들의 추가. **(기계적)**

7. 작성된 코드/Test Case에 대한 검토 및 수정. **(판단)** ARCHITECTURE/ 문서(Requirements, UsageCases, StandardScenarios)에 영향이 있는 변경이면 이 단계에서 문서를 함께 수정하고, [StandardScenarios.md](../../../ARCHITECTURE/StandardScenarios.md)의 검사 규칙으로 커버리지를 재검사한다.

8. Local Test 수행. **(기계적)**

9. Commit & Draft PR 작성. **(기계적)** DONOTMERGE github label도 붙인다. PR 제목이나 본문에 DONOTMERGE를 표기하지는 않는다.

10. 별도의 새 Context를 가지는 Sub-agent를 Spawn하여 [dev-code-review](../dev-code-review/SKILL.md) 스킬의 지침으로 Code Review를 수행하고 Code Review Comment를 PR에 남기도록 한다. 리뷰 대상 PR Number는 9번 과정에서 생성된 PR Number를 사용한다. **(기계적 spawn, 리뷰 자체는 판단)**

11. 코드 리뷰 결과를 조회하고 각 리뷰 항목의 적정성을 평가한 뒤, PR 내용을 그에 맞추어 수정한다. **(판단)** 단, 추후 진행할 Follow-up Item이 가급적 생기지 않도록, 해당 주제를 크게 벗어나지 않는다면 주어진 PR 내에서 완결하도록 한다. Test Case 추가나 Style Fix와 같은 사소한 수정은 Follow-up Item을 만들지 말고 항상 PR 내에서 완결한다. 이미 리뷰어가 만족하여 Approve(ok to merge) 하였더라도 Nit이나 Low-priority가 아직 있고 현 PR에서 충분히 해결할 수 있다면 이런 점도 해결한다. 혹시 이미 Fail 결과가 나온 CI 항목이 있다면 그 Fail 원인을 분석하여, 본 PR 코드 내 수정에 의한 것일 경우 곧바로 수정하며, 이러한 수정이 있었다면 코드 리뷰 결과가 모두 만족스럽더라도 수정 후 Goto 10하여 다시 리뷰를 받는다.

12. 기존 코드 리뷰의 요구가 모두 끝났으며, 리뷰어가 만족하여 Merge해도 된다고 판단하였으며, Nit 중에 이번 PR에서 Trivial하게 해결할 것도 없다면 다음 항목으로 계속 진행한다. 그렇지 않다면(리뷰어가 지난번에 만족하지 못하였고 이전 항목에서 그 점을 address하였다면, 혹은 address한 코드에 대해 새 리뷰를 받아오지 않았다면) 다시 리뷰를 받기 위해 Goto 10 한다. 리뷰어가 리뷰한 결과에 대해 대응한 건이 있다면 Goto 10하여 다시 리뷰 받아야 한다.

13. CI Test 결과 조회 및 CI Error 발생 시 분석 및 수정 대응. **(판단)** 단, 명백히 CI Infra Error이거나 이번 PR에서 고치는 것이 부적합한 기존 main branch에서의 error라면 사용자에게 상황을 알린다. 기존 main branch에서의 error라도 이번 PR에 관계되어 있다면 가급적 고치도록 한다.
    - **주의**: HIL-Claw에 CI가 아직 구축되지 않은 동안에는 이 단계를 Local Test 전체 재수행으로 대체한다.

14. CI Error Fix 과정에서 non-trivial fix가 있었다면(여러 라인에 걸친 fix) Goto 10하여 리뷰부터 다시 받는다.

15. 모든 과정 후 DONOTMERGE label을 제거하고 Ready for review 상태로 전환하여, 사용자가 수동 merge할 수 있도록 한다. 사용자가 merge/push를 직접 지시하지 않는 한 스스로 main에 merge하지 않는다.
