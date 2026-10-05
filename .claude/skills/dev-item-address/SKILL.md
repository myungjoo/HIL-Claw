---
name: dev-item-address
description: "HIL-Claw 표준 개발 프로세스: Github Issue나 지정된 주제에 대해 브랜치에서 작업하고(코드 모드는 PR) Review/Test Cycle을 돌려 Merge까지 완결한다. 코드/문서 변경 작업(이슈 해결, 기능 추가, 리팩토링)에 사용."
---

[사용자가 지정하는 개발 대상 주제나 이슈]에 대해서 다음의 작업을 진행하라.

모델 배정 원칙: **(판단)** 표기 단계는 상위(고성능) 모델이 수행하고, **(기계적)** 표기 단계는 경량 모델(subagent)에 위임할 수 있다. 특정 모델명을 하드코딩하지 않는다.

변경 모드(문서/코드)는 CLAUDE.md "브랜치·merge 절차"(#5 A-13)를 따르며 9단계에서 정한다. 이하 "PR"은 문서 모드에서는 브랜치를 뜻한다. 문서 모드에서는 4·6·8단계의 테스트 대신 해당되는 문서 검사(7단계의 커버리지 재검사 등)를 하고, 13·14단계는 건너뛴다.

1. 해당 Item이 정말 고쳐야 하는 이슈이고, 현재의 최신 main 기준으로 아직 고쳐지지 않은 Issue인지 확인. **(판단)**

2. 해당 Item을 고치기 위한 계획 및 구현 방법 결정. **(판단)** 단, 해당 구현이 덩치가 크거나 타 모듈에의 영향이 클 수 있으면, Architecture 변경 사항을 분석/점검하고 사용자에게 주요 쟁점과 이슈를 요약하여 설명한 뒤 합의를 보고 그 다음 단계를 진행해야 한다. 미결정 사항은 발명하지 말고 사용자에게 확인받거나 Requirements.md의 Open Decisions(OD)로 등재한다.

3. 해당 Item을 고치는 코드 작성. **(판단)**
   - 지나친 코멘트 작성은 피한다. 코드 내용으로 파악 가능한 내용은 굳이 코멘트하지 않는다. Multi-line comment 추가는 가능한 피한다.
   - Code Change 전반에 대한 설명은 코드 내 Comment가 아닌 Git Commit Message 본문에 기입한다.
   - 파일의 Boilerplate나 외부에 노출되는 API function에 대한 Doxygen(혹은 유사 방법) 등은 충분한 설명이 상대적으로 긴 Comment로 남아도 좋다.

4. 작성된 코드를 검증하고 타 기능에 영향 없음을 증명하며, 미래의 해당 Item에 대한 Regression을 막는 Test Case들의 추가. **(기계적)** 코드 모드 변경은 CLAUDE.md "테스트 규칙"(#5 D12)을 따른다: 2층 패키지 line·function coverage ≥ 80% 유지, negative case 포함, 건드린 모듈의 모든 public 함수 테스트, 2층 패키지의 새 모듈에는 대응 테스트 파일. 테스트 코드·CI 워크플로·hook·보조 스크립트를 대상으로 하는 테스트는 추가하지 않는다(테스트가 필수인 명시 예외 두 개는 CLAUDE.md 참조).

5. 작성된 코드가 잠재적으로 영향을 미칠 수 있는 타 모듈들을 점검. **(판단)**

6. 해당 타 모듈에 이번 코드 수정이 악영향(기능/비기능 모든 면에서)을 미치지 않는지 검사할 수 있는 Test Case들의 추가. **(기계적)**

7. 작성된 코드/Test Case에 대한 검토 및 수정. **(판단)** ARCHITECTURE/ 문서(Requirements, UsageCases, StandardScenarios)에 영향이 있는 변경이면 이 단계에서 문서를 함께 수정하고, [StandardScenarios.md](../../../ARCHITECTURE/StandardScenarios.md)의 검사 규칙으로 커버리지를 재검사한다.

8. Local Test 수행. **(기계적)**

9. 커밋 모드를 정하고 Commit한다. **(기계적)** 변경이 **문서·프로세스 파일만**(`ARCHITECTURE/`, `CLAUDE.md`, `.claude/`, `README.md`, `PROCESS/`)이면 **문서 모드**: 브랜치에 커밋·push만 하고 PR은 만들지 않는다. 그 외(2층 패키지 코드, CI 워크플로, 테스트)는 **코드 모드**: Draft PR을 작성하고 DONOTMERGE github label을 붙인다(PR 제목·본문에는 표기하지 않는다). 커밋 메시지 본문에 변경 설명과, 2층 코드라면 선택한 언어의 이유 한 줄을 적는다.

10. 별도의 새 Context를 가지는 Sub-agent를 Spawn하여 [dev-code-review](../dev-code-review/SKILL.md) 스킬의 지침으로 Code Review를 수행하게 한다. 리뷰 대상은 코드 모드면 9번에서 생성된 PR Number, 문서 모드면 브랜치 이름과 `origin/main` 대비 diff이다. 코드 모드의 리뷰 결과는 PR Comment로 남기고, 문서 모드는 호출자에게 결과(판정·지적 목록)를 반환한다. **(기계적 spawn, 리뷰 자체는 판단)**

11. 코드 리뷰 결과(코드 모드: PR Comment 조회, 문서 모드: 반환된 결과)를 확인하고 각 리뷰 항목의 적정성을 평가한 뒤, PR(문서 모드는 브랜치) 내용을 그에 맞추어 수정한다. **(판단)** 단, 추후 진행할 Follow-up Item이 가급적 생기지 않도록, 해당 주제를 크게 벗어나지 않는다면 주어진 PR 내에서 완결하도록 한다. Test Case 추가나 Style Fix와 같은 사소한 수정은 Follow-up Item을 만들지 말고 항상 PR 내에서 완결한다. 이미 리뷰어가 만족하여 Approve(ok to merge) 하였더라도 Nit이나 Low-priority가 아직 있고 현 PR에서 충분히 해결할 수 있다면 이런 점도 해결한다. 혹시 이미 Fail 결과가 나온 CI 항목이 있다면 그 Fail 원인을 분석하여, 본 PR 코드 내 수정에 의한 것일 경우 곧바로 수정하며, 이러한 수정이 있었다면 코드 리뷰 결과가 모두 만족스럽더라도 수정 후 Goto 10하여 다시 리뷰를 받는다.

12. 기존 코드 리뷰의 요구가 모두 끝났으며, 리뷰어가 만족하여 Merge해도 된다고 판단하였으며, Nit 중에 이번 PR에서 Trivial하게 해결할 것도 없다면 다음 항목으로 계속 진행한다. 그렇지 않다면(리뷰어가 지난번에 만족하지 못하였고 이전 항목에서 그 점을 address하였다면, 혹은 address한 코드에 대해 새 리뷰를 받아오지 않았다면) 다시 리뷰를 받기 위해 Goto 10 한다. 리뷰어가 리뷰한 결과에 대해 대응한 건이 있다면 Goto 10하여 다시 리뷰 받아야 한다. 리뷰가 7라운드를 넘으면 BLOCKED(CLAUDE.md A-13)로 중단하고 사용자에게 알린다.

13. CI Test 결과 조회 및 CI Error 발생 시 분석 및 수정 대응. **(판단)** 단, 명백히 CI Infra Error이거나 이번 PR에서 고치는 것이 부적합한 기존 main branch에서의 error라면 사용자에게 상황을 알린다. 기존 main branch에서의 error라도 이번 PR에 관계되어 있다면 가급적 고치도록 한다.
    - **주의**: HIL-Claw에 CI가 아직 구축되지 않은 동안에는 이 단계를 Local Test 전체 재수행으로 대체한다.
    - CI(구축 전: Local Test 재수행)가 3회 연속 실패하면 BLOCKED(CLAUDE.md A-13)로 중단하고 사용자에게 알린다.

14. CI Error Fix 과정에서 non-trivial fix가 있었다면(여러 라인에 걸친 fix) Goto 10하여 리뷰부터 다시 받는다.

15. 모든 과정 후 CLAUDE.md "브랜치·merge 절차"(#5 A-13)에 따라 스스로 merge한다. **(기계적)**
    - **문서 모드**: 브랜치를 `origin/main`에 rebase한 뒤 `git reset --soft origin/main` + 재커밋으로 커밋을 하나로 합치고, 그 커밋 메시지 끝에 `Reviewed-by: reviewer agent (N rounds, Approve)` trailer를 넣어 `git push origin HEAD:main`(fast-forward)으로 push한 뒤 원격·로컬 브랜치를 지운다. 재작성된 브랜치를 원격 브랜치에 다시 push하지 않는다(force가 필요하다). rebase에서 충돌을 해소해 내용이 바뀌었으면 Goto 10.
    - **코드 모드**: DONOTMERGE label을 제거하고 Ready for review로 전환한 뒤 squash-merge하고 브랜치를 지운다.
    - `git push --force*`는 쓰지 않는다(PROCESS/DRIVER.md §3-5). BLOCKED 사유(CLAUDE.md A-13)에 해당하면 merge하지 않고 상태를 남긴 뒤 사용자에게 알린다.
