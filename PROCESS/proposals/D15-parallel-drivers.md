# D15 — task 단위 lock으로 드라이버 병렬 실행 (확정, 전환 대기)

- 상태: **확정(오너 2026-10-06, 채팅 — D15-1~4 모두 제안대로), 전환 대기**. 2026-10-06 작성. 등록부는 [DRIVER.md](../DRIVER.md) §11의 D15 행이다.
- **아직 효력 없음**: §8의 전환 절차가 끝나기 전까지 드라이버는 본 문서를 따르지 않는다. 현행 규칙은 DRIVER.md §4의 저장소 단일 lock이다. 전환은 §10의 D15-3 조건이 충족된 뒤에 한다.
- 본문은 전환 PR(§8-2)에서 DRIVER.md §1~§6·§8로 옮기고, 그 뒤 본 파일은 이력으로 남긴다.
- 표기: 본 문서에서 "§n"은 본 문서의 절, "DRIVER §n"은 DRIVER.md의 절이다.

## 1. 배경과 목표

현행 lock은 `PROCESS/STATE.json`의 `lock` 하나이고 범위가 저장소 전체다. 유효한 lock이 있으면 두 번째 드라이버는 DRIVER §3-1에서 종료하므로, 서로 무관한 task도 동시에 진행할 수 없다.

- **목표**: 드라이버 N개(상한은 §2의 `maxParallel`)가 **서로 다른 task**를 동시에 진행한다. 같은 task를 둘이 잡지 않고, 서로 간섭하는 task를 동시에 시작하지 않으며, main의 상태 파일은 일관되게 유지된다.
- **유지**: 1 iteration = 1 task(DRIVER §0; D14에서도 유지), lock 획득 = main push(fast-forward 규칙), `git push --force*` 금지, 상태는 전부 파일.
- **범위 밖**: 한 task 안의 병렬화, merge queue, 런타임(데이터 plane) lock.
- `maxParallel = 1`이면 현행과 같은 동작이 되도록 설계한다.

## 2. 상태 구조 (`PROCESS/STATE.json` schema_version 2)

| 필드 | 변경 | 형식 |
|---|---|---|
| `lock`, `currentTask` | 삭제 | `locks[]`가 대신한다 |
| `locks` | 신설 | `[{taskId, owner, acquiredAt(ISO-8601 UTC), ttlMinutes}]` — 빈 배열 = 진행 중인 task 없음 |
| `maxParallel` | 신설 | int ≥ 1. 유효한 `locks` 항목 수의 상한 |
| 그 밖 | 유지 | `phase`, `humanQuestions`, `counters`, `notes`, 그리고 `nextTask`·`lastIteration`(둘 다 마지막으로 쓴 드라이버의 값) |

- `owner` = `<hostname>:<driverId>:<session-id>`. **`driverId`는 전용 clone마다 고정된 값**이며 호출 프롬프트가 준다. 현행 owner는 세션마다 달라서 같은 clone의 두 세션을 구분할 수 없다. 프롬프트가 `driverId`를 주지 않은 호출(수동 `/loop` 등)은 lock을 잡지 않고 종료한다.
- 불변식: `locks` 안에서 `taskId`는 유일하고 `driverId`도 유일하다(한 clone은 한 번에 한 task).
- `maxParallel`을 호출 프롬프트가 아니라 STATE에 두는 이유: 프롬프트에 두면 값이 서로 다를 때 큰 값을 받은 드라이버가 상한을 넘겨 잡게 된다.
- task 파일 frontmatter에 두 필드를 추가한다: `planItem: P1-2`(그 task가 다루는 PLAN 항목 — 중복 생성 판정의 키)와 `exclusive: true | false`(기본 false, §3-2).

## 3. 절차 변경 (DRIVER §3 대비)

### 3-1. 진입 (DRIVER §3-0·§3-1)

- `git fetch` 뒤, **0단계의 `reset --hard`·`clean`보다 먼저** `origin/main`의 `locks`를 본다. 자기 `driverId`의 유효한 항목이 있으면 아무 것도 건드리지 않고 종료한다 — 같은 clone에서 앞선 세션이 아직 일하고 있다는 뜻이다(같은 루틴의 겹친 발화, D14 연속 실행 중의 다음 발화). 현행 단일 lock이 겸하던 "한 clone에 세션 하나" 보장을 이 규칙이 대신한다.
- 자기 `driverId`의 **만료** 항목이 있으면 다른 만료 항목보다 먼저, 그리고 역시 0단계의 `reset`·`clean`보다 먼저 §5의 활동 점검을 한다(점검은 원격 브랜치만 본다). 활동 중이면 연장하고 종료한다.
- 그 밖의 만료 항목은 선택보다 먼저 §5로 처리한다.
- 유효한 항목 수가 `maxParallel` 이상이면 아무 것도 쓰지 않고 종료한다.

### 3-2. task 선택 — 독립성 규칙 (DRIVER §3-3에 추가)

후보 task C는 유효한 lock이 걸린 모든 task L에 대해 다음을 만족해야 한다.

1. C와 L의 `touchesFiles`가 겹치지 않는다(한쪽 경로가 다른 쪽의 접두이면 겹침).
2. C의 `dependsOn`에 L이 없다.
3. C와 L 어느 쪽도 `exclusive`가 아니다.

- 만족하지 못한 후보는 **BLOCKED로 기록하지 않고** 건너뛴다(L이 끝나면 저절로 풀리는 일시 상태다). DRIVER §3-3 ⓒ의 열린 PR 겹침 검사에서는 진행 중 task의 PR을 제외한다 — 그 겹침은 이 규칙이 "건너뜀"으로 다룬다.
- `exclusive: true`는 저장소 전역에 영향을 주는 task에 붙인다: CI 워크플로, `pyproject.toml`, `CLAUDE.md`, `.claude/`의 스킬·agent 정의, `PROCESS/DRIVER.md`, STATE 스키마와 그 검증기. 이런 task는 `locks`가 비어 있을 때만 시작하고, 진행 중에는 다른 드라이버가 lock을 잡지 않는다.
- **배수**: 선택 순서상 첫 후보가 `exclusive`인데 `locks`가 비어 있지 않으면, 다른 후보로 넘어가지 않고 커밋 없이 종료한다. 모든 드라이버가 같은 파일 상태에서 같은 첫 후보를 보므로 `locks`가 비게 되고 그 task가 시작된다(넘어가도록 두면 exclusive task가 계속 밀린다).
- 선택 순서의 "`currentTask` 우선"은 없어진다. 중단된 task의 재개는 §5의 회수가 맡는다.
- 독립적인 후보가 없으면 현행 "선택 가능한 task 없음"과 같이 커밋 없이 종료한다.

### 3-3. lock 커밋 (DRIVER §3-4)

- 자기 항목을 `locks`에 **추가**하는 커밋을 main에 push한다. task `status: IN_PROGRESS`, HQ 동기화, 새 task 파일을 같은 커밋에 담는 것은 현행과 같다. `nextTask`가 방금 잡은 task이면 null로 비운다.
- **lock 커밋은 rebase하지 않는다.** push가 거부되면 `origin/main`으로 reset한 뒤 진입부터 다시 수행한다(재시도 ≤ 2회, 그 뒤 종료). 병렬에서는 거부의 원인이 같은 task 경합이 아니라 다른 드라이버의 마무리 커밋일 수 있어서, 현행의 "재시도 없이 종료"를 완화한다.
- planner가 만든 task 파일은 reset 전에 작업 트리 밖에 보관해 두고, 다음을 모두 만족할 때만 재사용한다: 그 `T-NNNN`이 새 `origin/main`에 없다, 같은 `planItem`의 task가 새로 생기지 않았다, §3-2의 독립성을 여전히 만족한다. 하나라도 아니면 버린다.

### 3-4. 실행 (DRIVER §3-5)

구현·테스트·리뷰는 드라이버별 전용 clone과 task 브랜치에서 현행대로 진행한다. 추가되는 규칙은 둘이다.

**범위 이탈**: executor가 `touchesFiles`에 없는 파일을 바꿔야 하면 `origin/main`의 `locks`를 다시 읽는다.

- 그 파일이 다른 진행 중 task의 `touchesFiles`와 겹치거나 §3-2의 `exclusive` 대상이면 BLOCKED로 반환한다. 사유는 기존 "열린 PR과의 파일 충돌 위험"을 진행 중 task로 확장한 것이고, 막은 task id를 `Result`에 적는다. HQ는 만들지 않는다 — 그 task의 `locks` 항목이 사라지면 DRIVER §3-2의 자동 해소와 같이 `TODO`로 되돌린다(오너 답변이 필요 없다).
- 겹치지 않으면 진행하고 `Result`에 적는다.

**merge 관문**: `main`에 합치기 직전에 다음을 한다.

1. `git fetch` 후, 리뷰받은 시점 이후 `origin/main`에 **드라이버 상태 커밋이 아닌 커밋**이 들어왔는지 본다. 상태 커밋의 판정은 subject가 아니라 내용으로 한다: 변경 경로가 `PROCESS/STATE.json`·`PROCESS/journal/`·`PROCESS/PLAN.md`·`PROCESS/tasks/`뿐이고 `Task:` trailer가 없는 커밋. 없으면 현행대로 merge한다.
2. 있으면 코드 모드는 `gh pr update-branch`로 `main`을 PR 브랜치에 merge한다(rebase는 force push가 필요하므로 쓰지 않는다; squash-merge가 이력을 접는다). 이 명령은 충돌을 해소하지 못하므로, 충돌로 실패하면 BLOCKED(`branch-contention`)로 반환한다(로컬 `git merge`는 CLI 경로의 allowlist에 없다). 이 HQ의 선택지는 (a) 오너가 PR 브랜치의 충돌을 직접 해소, (b) allowlist에 `git merge *`를 추가해 executor가 해소하는 것이다. 문서 모드는 현행대로 로컬에서 rebase한다(push 대상이 main이라 force가 필요 없다).
3. 테스트를 다시 수행한다(CI가 있으면 새 head의 green).
4. 문서 모드의 rebase에서 충돌을 해소했거나, 들어온 커밋이 이 task가 바꾼 파일을 건드렸으면 리뷰 사이클로 돌아간다.
5. 1을 다시 본다(≤ 3회; 초과하면 BLOCKED `branch-contention`). 새로 들어온 것이 없으면 merge한다.

### 3-5. 마무리 커밋 (DRIVER §3-6)

- 마무리 커밋도 lock 커밋처럼 **rebase하지 않고 최신 `origin/main` 위에 다시 만든다**. 내용은 다음과 같다.
  - `STATE.json`: origin의 값에서 자기 lock 항목(`owner`와 `taskId`가 모두 일치)을 지우고, `counters` 증분, `lastIteration`, `nextTask`, 새 HQ 항목을 적용한다.
  - 자기 task 파일의 `status`와 `Result`, `PLAN.md`의 자기 항목 체크, journal에 자기 줄 추가.
- push 전마다 `origin/main`의 `locks`에 자기 항목이 그대로 있는지 확인한다. 없거나 자기 task 파일의 `status`가 origin에서 바뀌어 있으면 회수된 것이므로 `lock lost`로 종료한다.
- push 전에 STATE 스키마 검증기를 통과시킨다.
- push가 거부되면 fetch 후 다시 만든다(≤ 3회). 그래도 실패하면 현행대로 lock을 유지한 채 종료한다(ttl 회수에 맡김).
- 이렇게 하면 깨끗하게 병합된 것처럼 보이면서 증분을 잃는 경우(두 드라이버가 `counters`를 같은 값으로 바꾼 경우)가 생기지 않고, journal·PLAN의 병합 규칙도 따로 필요 없다.
- **phase 전환**(DRIVER §6)은 lock 커밋과 마무리 커밋 어느 쪽에서든 할 수 있다. 조건은 그 커밋의 부모인 `origin/main` 기준으로 판정하고, origin의 `phase`가 이미 올라가 있으면 그대로 둔다.
- 새 HQ의 `HQ-NNNN` 번호는 push가 성공한 커밋의 값이 확정이다. 다시 만드는 중에 번호가 이미 쓰였으면 다음 번호로 바꾸고 task 파일의 `hq:`도 맞춘다. (D19, 2026-10-21: HQ는 #5에 미러하지 않으므로 이 문서가 두었던 미러 게시와 미러 복구의 유예 규칙은 없어졌다.)

## 4. Planner (DRIVER §6)

- 입력에 진행 중 task의 목록(각 `touchesFiles`와 `planItem`)을 추가한다.
- planner의 대상은 "체크되지 않았고, 기존 task가 없으며(진행 중·BLOCKED인 항목 제외), 건너뛰는 표시가 없는 첫 항목"이다.
- 그 항목이 `exclusive` 대상이고 `locks`가 비어 있지 않으면 task를 만들지 않고 끝낸다(§3-2의 배수; 이 규칙이 다음 규칙보다 먼저다).
- 그 밖에는 그 항목부터 순서대로 §3-2의 독립성을 만족하는 첫 항목으로 task를 만든다. 그런 항목이 없으면 만들지 않는다.
- `touchesFiles`에는 공용 설정 파일을 포함해 바꿀 가능성이 있는 경로를 빠짐없이 적고, 전역 영향이 있으면 `exclusive: true`로 표시한다.

## 5. lock 회수와 연장 (DRIVER §4)

- ttl, executor 시간 상한, 브랜치 활동 점검은 현행 값(D3)을 **항목별로** 적용한다.
- 만료 항목은 task 선택보다 먼저 처리하고, 한 iteration에 1건만 다룬다. 자기 `driverId`의 항목이 먼저다(§3-1).
  - 그 task 브랜치가 활동 중이면 그 항목의 `acquiredAt`만 연장하고 이번 iteration은 종료한다(현행과 같다).
  - 회수하면 그 항목의 `owner`·`acquiredAt`을 자기 값으로 **교체**하고 task를 `INTERRUPTED`로 표시한다. **그 task가 이번 iteration의 task**이며 §3-2의 선택은 하지 않는다. 회수한 드라이버가 다른 task를 골라 자기 owner의 항목이 엉뚱한 task에 남는 일을 막는다.
- 회수된 쪽이 살아 있을 가능성은 §3-5의 확인(자기 항목이 없으면 push하지 않음)으로 막는다.

## 6. 운영 (DRIVER §1)

- 드라이버마다 **전용 clone, 전용 루틴, 고유한 `driverId`**를 둔다(DRIVER §1-6).
- 발화 시각을 엇갈리게 한다(예: :17과 :47). 동시에 planner를 돌려 한쪽 결과를 버리는 일이 줄어든다.
- DRIVER §1-2의 "단일 실행 보장"은 "task당·clone당 단일 실행 보장"으로, "`/loop`과 cron을 동시에 켜지 않는다"는 "`maxParallel`까지 허용"으로 바뀐다.
- 연속 실행(D14)은 드라이버별로 그대로 적용된다. 추가 iteration이 같은 루틴의 다음 발화와 겹치면 그 발화는 §3-1의 `driverId` 규칙으로 종료한다.
- 오너가 `STATE.json`을 직접 고치는 것은 `locks`가 비어 있을 때만 한다.

## 7. 보장 범위와 남는 위험

### 7-1. 보장되는 것

- 같은 task, 같은 `T-NNNN`, 같은 `planItem`을 두 드라이버가 동시에 잡지 않는다 — lock 커밋이 fast-forward push이고 재시도는 새 `origin/main` 위에서 재검증한 뒤에만 한다.
- 한 clone에서 자기 lock 항목이 유효한 동안 다른 세션이 일하지 않는다(§3-1). lock 커밋 전 구간과 ttl 만료 뒤는 현행과 같이 보호되지 않는다.
- 선언된 `touchesFiles`가 겹치거나 의존 관계인 task, 전역 영향 task는 동시에 시작하지 않는다.
- 한 드라이버의 마무리 커밋이 다른 드라이버의 lock 항목이나 `counters` 증분을 지우지 않는다(§3-5).

### 7-2. 남는 위험

1. **`touchesFiles`가 부정확한 경우**: 선택 규칙은 선언에 의존한다. 범위 이탈 규칙(§3-4)이 일부를 잡고, 나머지는 merge 관문에서 충돌이나 테스트 실패로 드러난다. 즉 안전은 merge 관문이, 재작업 감소는 선택 규칙이 맡는다.
2. **파일은 안 겹치고 의미가 충돌하는 경우**: merge 관문의 재테스트로만 잡힌다. 테스트가 없는 영역은 잡히지 않는다.
3. **merge 관문의 경합 구간**(코드 모드에 한함): 관문의 마지막 확인과 실제 squash-merge 사이에 다른 task가 merge되면 재테스트 없이 합쳐진다. 이 경우는 `main`의 push CI(P0-3)와 다음 iteration의 수정 task로 대응한다. 문서 모드는 main push가 fast-forward라 이 구간이 없다(거부되면 관문부터 다시).
4. **사용량**: 토큰과 Actions 실행이 드라이버 수만큼 늘고, 한도에 걸리면 모든 드라이버가 함께 멈춘다.

위험 2·3 때문에 병렬은 **CI가 main에서 동작한 뒤**에 켠다(D15-3 확정; P0-3 = T-0003).

## 8. 전환 절차

드라이버가 자기 lock 형식을 바꾸는 task를 스스로 실행하면, v1 규칙으로 시작한 세션이 v2 형식으로 마무리해야 한다. 그래서 전환은 드라이버 task가 아니라 **루틴을 멈춘 상태에서 통합자 세션**이 한다(D15-4 확정). 시작 조건은 D15-3이다: T-0003이 완료되어 CI가 main에서 동작하고, merge 가드 hook(P0.5-4)이 등록되어 있다.

1. 루틴을 일시 정지하고 `lock`이 null인지 확인한다.
2. 코드 모드 PR 하나로 다음을 함께 반영한다: `PROCESS/STATE.schema.json` v2, `hilclaw/driver_state.py`와 그 테스트(D12 예외 ①), `STATE.json` 이전(`locks: []`, `maxParallel: 1`), 기존 task 파일의 `planItem`, DRIVER.md 본문 개정, agent 정의·스킬의 해당 문장.
3. 루틴 프롬프트에 `driverId`를 넣고(오너 작업 — 저장소 밖 설정) 재개하여 `maxParallel = 1`로 1 iteration 이상 정상 동작을 확인한다.
4. 두 번째 전용 clone과 루틴을 만들고(오너 작업 — 폴더·모델·권한 모드는 Routines 편집 화면에서만 설정된다) `maxParallel = 2`로 올린다.

되돌릴 때는 루틴을 멈추고 `locks`가 빈 뒤 `maxParallel`을 1로 내린다. 스키마를 v1으로 되돌릴 필요는 없다.

## 9. 검토한 대안

- **순차 처리량만 올리기**(루틴 간격 단축, D14 연속 실행 상한 상향): 변경이 프롬프트 값뿐이고 §7-2의 위험이 없다. 독립적인 task가 동시에 2개 이상 꾸준히 나오기 전에는 이쪽이 싸다.
- **task별 lock 브랜치**(`lock/T-NNNN` 생성을 CAS로 사용, A-A 방식): lock 때문에 main의 상태 커밋이 경합하지 않는다. 대신 진행 상태의 정본이 `STATE.json`과 브랜치 목록 둘로 나뉘고, PLAN 항목 중복 방지는 여전히 main이 필요하다. 채택하지 않았다.
- **고정 레인**(드라이버 A는 코드, B는 문서): 선택 규칙은 단순해지지만 `STATE.json`·PLAN·journal 경합은 그대로이고 한쪽 레인이 비면 놀게 된다. 채택하지 않았다.

## 10. 오너 결정 (2026-10-06 채팅, 모두 제안대로 확정)

| # | 질문 | 확정 |
|---|---|---|
| D15-1 | task 단위 lock으로 병렬 실행을 도입할지, 순차 처리량 상향(§9 첫 항목)으로 충분한지. 병렬은 토큰·Actions 사용량이 드라이버 수만큼 는다 | 설계는 확정해 두고 실제 전환은 D15-3 조건 뒤에 |
| D15-2 | 병렬 상한의 위치와 값 | `STATE.maxParallel`, 전환 직후 1 → 확인 뒤 2 |
| D15-3 | CI가 main에서 동작하기 전에 병렬을 켤지 | 켜지 않음(T-0003 완료와 merge 가드 hook 등록 뒤) |
| D15-4 | 전환을 드라이버 task가 아닌 통합자 세션(루틴 정지)으로 할지 | 그렇게 함(§8) |

그 밖의 설계 세부(`driverId`, `planItem`·`exclusive` 필드와 배수 규칙, lock 커밋 재시도 2회, 마무리 커밋 재생성, merge 관문과 그 반복 3회·충돌 시 BLOCKED, 미러 복구 유예 30분 — D19로 폐지)는 D15-1의 확정과 함께 채택되었다. 이 중에는 앞서 확정된 항목의 문구를 바꾸는 것이 있으며, 전환 때 함께 고친다(§8-2; A-13은 CLAUDE.md) — D3의 "두 번째 드라이버는 스스로 종료", D8의 BLOCKED 사유 목록, A-13 merge 절차에 관문 단계 추가. 오너가 이견을 내면 그에 따른다.
