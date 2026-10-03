# 개발 드라이버 (Development Driver)

HIL-Claw를 **만드는** 자동 개발 프로세스의 설계 문서이자, 매 반복(iteration)에 Claude Code 세션이 그대로 따르는 **드라이버 프롬프트**다. HIL-Claw가 **도는** 런타임 오케스트레이터(Requirements FR-1 라운드 루프, #4)와는 별개이며, 둘을 혼동하지 않는다.

- 절차는 Assessment-Agent(이하 A-A)의 **개발 절차**를 참조했다. 프로세스 파일 배치(드라이버 문서·PLAN·상태 파일·task 파일·journal)도 절차의 일부로서 따랐으나, A-A의 SW 구조·스택·레이아웃은 가져오지 않는다(CLAUDE.md, #5 A-12).
- 오너 결정: 실행 모델 = **로컬 Claude Code 세션의 `/loop`**(2026-10-03). cron/스케줄 호출과의 호환은 §1의 조건으로 보장한다.
- **전제 커밋**: 본 문서는 CLAUDE.md의 "브랜치·merge 절차"(#5 A-13) 규칙 텍스트와, dev-item-address 9·10·15단계(문서 모드 분기·자율 merge)·dev-code-review(문서 모드 반환 경로)의 반영 커밋을 전제한다. 그 커밋이 main에 들어가기 전에는 드라이버를 가동하지 않는다.
- 표기: **⚑ 결정 요청** = 오너 확정 전 잠정값(제안). §11에 모아 둔다. **§11의 항목이 답변되기 전에는 드라이버를 가동하지 않는다**(잠정값으로 가동하는 것은 미결을 확정처럼 운용하는 것이다). 오너가 "잠정값 그대로"라고 답하면 그것이 확정이다.

---

## 0. 범위와 원칙

- **대상**: HIL-Claw 저장소(1층 프롬프트·스킬·에이전트 정의, 2층 도구 패키지, 문서)의 구현을 task 단위로 진행·리뷰·merge하는 일. 런타임 run(데이터 plane)은 대상이 아니다.
- **단위**: 1 iteration = 1 task = 1 커밋(문서 모드) 또는 1 PR(코드 모드). 한 번에 하나만.
- **상태는 전부 파일**(`PROCESS/`)에 있다. iteration 사이에 대화 컨텍스트에 의존하지 않는다 — `/loop`·cron·`claude -p` 어느 것으로 불려도 같은 동작을 하는 근거다.
- **규칙의 정본**: CLAUDE.md(상시 규칙, A-13 merge 절차) > 본 문서 > 스킬. 본 문서는 CLAUDE.md를 반복하지 않고 참조한다.
- **미결은 발명하지 않는다**: 드라이버는 Requirements의 OD를 스스로 확정하지 않는다(§9가 확정되기 전까지). 필요한 결정은 BLOCKED(§8)로 올린다.

## 1. 실행 모델

- 기본: 오너 로컬 PC(C-7: Windows/WSL·macOS·Linux)의 Claude Code 세션에서 `/loop <간격> <드라이버 호출>`. 드라이버 호출 = "`PROCESS/DRIVER.md` §3을 1 iteration 수행". 간격은 Max 플랜 한도(C-7)와 task 소요시간을 고려해 정한다. ⚑ D1: 간격 초기값 15분; 세션당 iteration 상한 10회 — 같은 대화에 wakeup이 누적되어 컨텍스트 한계에 닿는 것을 막기 위한 값(A-A의 `/loop` 10-turn cap 차용; A-A의 cron 자체는 1시간 간격).
- **cron/스케줄 호환 조건**(오너 요구): 다음을 만족하므로 OS cron, `/schedule` 루틴, `claude -p`에서 같은 호출로 1 iteration을 실행할 수 있다.
  1. **멱등·자기완결**: 매 iteration이 `git fetch` + `PROCESS/STATE.json` 읽기로 시작하고 대화 이력을 쓰지 않는다.
  2. **단일 실행 보장**: §4의 lock. lock이 유효하면 아무 것도 하지 않고 종료한다(중복 호출은 무해). lock은 main push의 fast-forward 규칙으로 성립하므로 **머신 간에도 유효**하다(`/schedule`의 클라우드 체크아웃 포함) — 단 ttl 판정은 벽시계에 의존하므로 시계 편차가 큰 머신을 섞지 않는다.
  3. **1 호출 = 최대 1 task**: 호출 주체가 무엇이든 한 iteration은 하나의 task를 끝내거나 BLOCKED를 기록하고 멈춘다.
  4. **네트워크 의존 최소**: GitHub(push·PR·이슈)와 Anthropic만 필요(C-7). `gh`가 없으면 **저장소 밖 로그**(`~/.hilclaw-driver.log` 또는 stderr; 추적 파일인 `PROCESS/journal/`에는 쓰지 않음 — clean tree 유지)에 "gh 불가"를 적고 종료한다. ⚑ D2: GitHub MCP 폴백을 둘지(A-A는 두었음) — 초기값: 두지 않음.
  5. **비대화 실행 권한**: cron/`claude -p`는 permission prompt에서 멈추므로, 드라이버가 쓰는 동작(`git fetch/push`, `gh pr/issue`, 테스트 실행)이 사전 허용되어 있어야 한다. ⚑ D11: 허용 범위와 설정 위치(프로젝트 `settings.json` allowlist)는 오너가 정한다.
  6. **작업 트리 전제**: 드라이버 전용 clone(또는 worktree), `main` 추적, clean tree. 오너의 개발 작업 트리와 공유하지 않는다.
- 운용 지침: `/loop`과 cron을 동시에 켜지 않는 것이 기본이며, 켜야 하면 호출 간격 ≥ 평균 task 소요 × 2(A-A 운용 규칙). cron 체크아웃은 iteration마다 fresh여도 된다(상태는 전부 main에 있다).
- 런타임(HIL-Claw run)의 `/loop`·lock과 무관하다. 드라이버 lock은 `PROCESS/STATE.json`, 런타임 lock은 데이터 plane `runs/<run_id>/STATE.json`에 있고 구조도 다르다(§2 표).

## 2. 디렉토리와 변경 모드

```
PROCESS/
  DRIVER.md          # 본 문서 (드라이버 프롬프트 + 규칙)
  PLAN.md            # 단계(phase)별 체크리스트, FR/OD 추적
  STATE.json         # 드라이버 상태 (유일 진입점)
  tasks/T-NNNN-<slug>.md   # task 1건 = 파일 1개 (자기완결)
  journal/YYYY-MM-DD.md    # iteration마다 ≤5줄
```

- **내용 변경**(DRIVER.md·PLAN.md 본문, task 파일의 명세부)은 **문서 모드**(CLAUDE.md A-13) — 리뷰어 통과 후 main 직접 push. *(A-13의 "문서·프로세스 파일"에 `PROCESS/`를 포함하는 것은 통합자 해석.)*
- **드라이버 상태 커밋**(`STATE.json`, journal, PLAN 체크박스, task 파일의 `status`/`Result`, planner가 생성한 task 파일)은 **리뷰 없이 push하는 예외**다 — lock 커밋에 리뷰를 붙이면 lock의 의미가 없고, 상태 커밋은 재생성 가능한 기계적 산출이기 때문이다. 경계: planner가 **생성 시점**에 쓴 task 파일은 D8의 예외, 그 뒤 사람이 명세를 고치는 것은 문서 모드. ⚑ D8: 이 예외의 채택 여부, 그리고 **planner가 만든 task 파일**을 예외에 포함할지(A-A는 리뷰 없이 둠) vs 다음 iteration의 executor가 첫 단계로 검토할지.
- `PROCESS/STATE.json` 필드(P0-4의 JSON Schema가 생기기 전까지 본 표가 정의):

| 필드 | 형식 | 의미 |
|---|---|---|
| `schema_version` | int | 본 표의 버전(현재 1) |
| `phase` | `"P0"\|"P0.5"\|"P1"\|"P2"\|"P3"` | PLAN.md의 현재 phase |
| `currentTask` | task id \| null | §3-4에서 lock과 함께 기록, §3-6에서 해제 |
| `nextTask` | task id \| null | planner가 미리 정한 다음 task |
| `lock` | `{owner, acquiredAt(ISO-8601 UTC), ttlMinutes}` \| null | §4. 런타임 STATE의 `lock{owner, heartbeat}`(#4 §2e)와 다른 구조 |
| `humanQuestions[]` | `{id, taskId, reason, question, askedAt, issueComment, resolvedAt?, decision?}` | §8 |
| `counters` | `{iterations, tasksDone, tasksBlocked, reviewRoundsTotal}` | 누계 |
| `lastIteration` | `{at(ISO-8601 UTC), owner, taskId, outcome}` \| null | 직전 iteration 요약 |
| `notes` | string | 사람용 메모 |

- 런타임 `STATE.json`(데이터 plane `runs/<run_id>/`)과 이름이 같지만 위치·구조가 다르다. 드라이버 문서에서는 항상 `PROCESS/STATE.json`으로 전체 경로를 쓴다.

## 3. 1 iteration 절차 (드라이버 프롬프트)

호출되면 다음을 **순서대로** 수행한다. 모델 배정은 CLAUDE.md 원칙(판단 = 상위, 기계적 = 경량 위임 가능)을 따른다.

0. **동기화** *(기계적)*: `git fetch origin`; `main`을 checkout하고 **무조건** `git reset --hard origin/main` + `git clean -fd`로 맞춘다 — 직전 iteration의 거부된 상태 커밋, 사망 직전의 미커밋·untracked 잔재를 모두 버린다(전용 clone 전제 §1-6; 상태 커밋은 재생성 가능하다). CLAUDE.md "세션 진입 점검"의 열린 PR 목록을 확보한다(판정은 3단계에서).
1. **STATE 읽기** *(기계적)*: `PROCESS/STATE.json`을 읽는다. `lock`이 유효하면(§4) 아무 것도 쓰지 않고 종료한다. 만료된 lock이면 §4의 회수 절차로 간다(기록은 4단계 커밋에 포함).
2. **BLOCKED 동기화(읽기)** *(판단)*: `humanQuestions`의 미해결 항목마다 #5를 확인한다. **답변 판정**: 그 HQ의 `issueComment`보다 **뒤에** 달린 코멘트 중 본문에 `HQ-NNNN`이 들어 있고 **드라이버 표식(§8)이 없는** 것 — 드라이버 자신의 미러 코멘트는 같은 계정으로 올라가므로 작성자로는 구분할 수 없다. 답변이 여러 개면 가장 최근 것을 `decision`으로 삼는다. 답변이 있으면 `resolvedAt`·`decision`을 STATE에 옮기고, **그 HQ를 참조하는 task의 `status`를 `BLOCKED`/`INTERRUPTED` → `TODO`로 되돌려 `nextTask`로 둔다**(실제 쓰기는 4단계 커밋에 포함). "열린 PR과 충돌 위험"으로 막힌 task는 그 PR이 닫히거나 merge되면 자동 해소다. 동기화 방향은 #5 → STATE. **`issueComment`가 null인 미해결 HQ**(미러 게시 직후 사망)는 #5에서 `### HQ-NNNN` 머리말로 검색해 URL을 복구하고(있으면 재게시 금지, 없을 때만 4단계 뒤에 게시), 답변 판정의 시간 앵커는 `askedAt`으로 대체한다.
3. **task 선택(로컬)** *(판단)*: 선택 규칙 — ⓐ `hq`에 미해결 항목이 있는 task는 선택하지 않는다 ⓑ `currentTask`(직전 iteration이 중단된 것) → `nextTask` → `tasks/`의 기존 `TODO`·`INTERRUPTED` 파일 → 그래도 없으면 **planner**(§6)로 `PLAN.md`에서 다음 task 1개를 만든다 ⓒ 선택한 task의 `touchesFiles`가 0단계의 열린 PR과 겹치면(**그 task 자신의 브랜치 `claude/T-NNNN-*`의 PR은 제외**) BLOCKED(사유: 열린 PR과 충돌 위험)로 두고 다음 후보를 본다. 선택 가능한 task가 없으면(전부 BLOCKED/완료) **아무 것도 커밋하지 않고** 저장소 밖 로그에 한 줄 남기고 종료하며, 오너에게 `/loop` 중단을 권고한다 — 이때 이 iteration에서 내린 BLOCKED 판정은 저장되지 않는다(다음 iteration이 같은 판정을 반복; 멱등이라 무해).
4. **lock + currentTask 커밋** *(기계적)*: `lock`, `currentTask`, task `status: IN_PROGRESS`, 2단계의 HQ 동기화, (planner가 만들었다면) 새 task 파일을 **한 커밋**(subject `driver: …`, §5)으로 main에 push한다. push가 거부되면(다른 드라이버가 먼저 push) **rebase·재시도하지 않고** 종료한다 — 이 거부가 곧 lock 경합의 패배다. 새 HQ의 #5 미러 코멘트는 이 push가 **성공한 뒤** 게시하고(거부 시 고아 코멘트 방지), 그 URL은 다음 상태 커밋(§3-6)에서 `issueComment`에 채운다.
5. **실행** *(판단 + 기계적)*: task 파일(과 그 Required Reading — 모든 task는 본 문서 §3-5·§5를 포함한다, §6)만 입력으로 받는 **executor** sub-agent를 띄워 [dev-item-address](../.claude/skills/dev-item-address/SKILL.md) 절차를 수행시킨다 — 구현 → 테스트 → 커밋(모드 결정) → 리뷰어 사이클(dev-code-review) → A-13에 따라 merge/push(문서 모드는 `Reviewed-by` trailer 필수). 브랜치·커밋·PR은 §5의 `T-NNNN` 명명 규약을 따른다. executor는 요약(≤200자: 결과·커밋/PR·BLOCKED 여부)만 반환하고 긴 산출은 task 파일 `## Result`에 쓴다. **재개 규칙**(`currentTask`/`INTERRUPTED`로 재개한 경우): executor는 먼저 `git log origin/main --grep='^Task: T-NNNN'`(executor 커밋의 trailer — 드라이버 상태 커밋은 이 trailer가 없어 오탐되지 않음, §5)과 `gh pr list --search T-NNNN --state all`로 결과가 **이미 landed/merged**인지 확인한다 — 그렇다면 구현 없이 `DONE`으로 마감; PR이 open이면 이어서; closed-unmerged면 브랜치 `claude/T-NNNN-*`가 남아 있으면 이어서, 없으면 처음부터 한다. **브랜치 경합**: task 브랜치 push가 거부되면 rebase 1회 재시도, 재거부면 BLOCKED(`branch-contention`). `git push --force*`는 어떤 경우에도 쓰지 않는다(A-A 규칙). **시간 상한**: executor는 wall-clock 상한을 넘기면 현재 상태를 `Result`에 적고 BLOCKED(`task-timeout`)로 반환한다(⚑ D3과 연동).
6. **마무리** *(기계적)*: task `status`(`DONE`/`BLOCKED`), `PLAN.md` 체크박스, `STATE.counters`·`lastIteration`, `nextTask`(planner가 §6에서 후보 id를 함께 제시했으면), `currentTask: null`, journal 1~5줄, **lock 해제**를 한 커밋으로 push한다. **push 전(`git fetch` 후)과 rebase 후에 `origin/main`의 `STATE.lock.owner`를 확인한다 — 자신이 아니면(ttl 만료로 회수됨) push하지 않고 저장소 밖 로그에 `lock lost`를 남기고 종료한다.** push가 거부되면(main이 움직임) `fetch` + rebase 후 재시도(≤3회 — 기계적 상수, A-A 값); `PROCESS/STATE.json`에 충돌이 나면 수동 병합하지 않고 **파일 단위로 origin 쪽을 취한 뒤**, owner가 여전히 자신이면(예: D3 ④의 lock 연장 커밋, 오너의 직접 편집) **자기 wrap-up 변경(lock=null, currentTask=null, task status, counters — origin 값 기준으로 증분을 다시 계산 —, lastIteration, nextTask)을 다시 적용**하고 push한다 — 그렇지 않으면 lock이 걸린 채 push되어 ttl까지 교착한다. 그래도 실패하면 lock을 **유지한 채** 종료한다(ttl 회수에 맡김). executor가 BLOCKED로 반환해 새 HQ가 생기면 §3-4와 같은 순서다 — 이 상태 커밋의 push가 성공한 뒤 미러를 게시하고 URL은 다음 상태 커밋에서 채운다.
7. **종료**: 1 task로 끝낸다. 세션당 iteration 상한(D1)에 도달했으면 journal에 기록하고 오너에게 `/loop` 중단을 요청한다(고정 간격 `/loop`를 모델이 스스로 멈출 수 있는지는 미확인).

**BLOCKED 사유**: CLAUDE.md A-13의 6가지(새 외부 의존성 · 데이터 plane 스키마 변경 · 리뷰 7라운드 초과 · CI 3연속 실패 · 요구 불명확/미결 발명 의심 · 보안 의심) + 드라이버 제안 4가지 *(⚑ D8과 함께 확정)*: 열린 PR과의 파일 충돌 위험 · Requirements OD 확정이 필요한 설계 선택(§9) · `task-timeout` · `branch-contention`(§3-5). BLOCKED는 §8에 따라 HQ로 기록하고 #5에 미러한다.

## 4. Lock (단일 실행 보장)

- `STATE.lock = { owner, acquiredAt, ttlMinutes }`. owner = `<hostname>:<session-id 또는 pid>`.
- 유효 = `now < acquiredAt + ttl`. lock 획득은 **main에 push되어야** 성립한다(push 거부 = 경합 패배). A-A의 lock 브랜치 CAS와 같은 효과를 main 자체의 fast-forward 규칙으로 얻는다 — 별도 브랜치·스크립트 없음. 머신 간에도 유효(§1-2).
- **ttl과 긴 task** — ttl이 task 소요를 보장하지 못하면 stale 회수 시점에 두 드라이버가 같은 task를 병행할 수 있다(리뷰 7라운드 코드 task는 1시간을 넘길 수 있음). ⚑ D3(택1 또는 조합): ① executor 반환 직후와 리뷰 라운드마다 드라이버가 `acquiredAt`을 갱신(heartbeat; 상태 커밋 노이즈 증가) ② executor wall-clock 상한(§3-5)을 ttl보다 짧게 두고 초과 시 BLOCKED+lock 해제 ③ ttl을 최악 소요(예: 3시간)로 올리고 호출 간격 ≥ 소요×2 운용 ④ **회수 전 활동 점검** — 그 task 브랜치 `claude/T-NNNN-*`의 마지막 push가 ttl보다 최근이면 살아 있다고 보고 회수하지 않고 `acquiredAt`만 연장하는 상태 커밋(STATE.json만, journal은 쓰지 않음)을 push한 뒤 **종료**(이번 iteration은 작업 없음; main 커밋 없는 사실상의 heartbeat를 브랜치 활동으로 대신함). 연장 push가 거부되면(그 사이 owner의 wrap-up이 landed) §3-4와 같이 재시도 없이 종료. 초기 제안: ②+④(ttl 3시간, executor 상한 2시간 30분, 회수 전 활동 점검).
- **stale 회수**: 만료 lock을 발견한 드라이버는(④ 채택 시 활동 점검을 통과한 뒤) journal에 "stale lock reclaimed(owner, acquiredAt)"를 남기고, 그 lock의 `currentTask`를 `INTERRUPTED`로 표시한 뒤 §3-3에서 재개한다(§3-5 재개 규칙: landed 확인 → 기존 브랜치/PR 이어쓰기 → 처음부터). 이전 드라이버가 아직 살아 있을 가능성은 §3-6의 owner 확인(lock을 잃은 쪽은 push하지 않음)으로 막는다.
- 운용상 결과: main에는 iteration당 상태 커밋 2개(lock, wrap-up)가 쌓인다. 오너의 수동 push는 항상 rebase가 필요하고, 오너가 `PROCESS/STATE.json`을 직접 고치는 것은 **lock이 없을 때만** 한다.

## 5. Task 파일 포맷

```markdown
---
id: T-0001
title: <imperative, one line>
phase: P0
status: TODO | IN_PROGRESS | INTERRUPTED | DONE | BLOCKED
commitMode: doc | code            # CLAUDE.md A-13 문서 모드 / 코드 모드
coversReq: [FR-10, OD-8]          # Requirements ID 또는 결정 ID(#5 A-n, #9) — 추적용
dependsOn: []                     # 선행 task id
touchesFiles: [...]               # 예상 변경 파일/디렉토리 (충돌 점검용)
estimatedSize: {loc: 150, files: 4}
hq: []                            # 이 task를 막고 있는 HQ id 또는 §11의 D id
---
## Why
## Required Reading        # 파일 경로 + §/행 범위. 에이전트는 이것만 읽고 시작한다
## Acceptance Criteria     # 코드 task는 happy/error/branch/negative 케이스 포함
## Out of Scope
## Follow-ups
## Result                  # executor가 채움: 커밋/PR, 리뷰 라운드 수, 남긴 follow-up
```

- `status`는 드라이버가 바꾼다: `IN_PROGRESS`(§3-4), `INTERRUPTED`(§4 회수), `DONE`/`BLOCKED`(§3-6), `BLOCKED`/`INTERRUPTED` → `TODO`(§3-2 HQ 해소).
- **명명 규약**(task ↔ 산출물 연결 키): 브랜치 `claude/T-NNNN-<slug>`; PR 제목에 `T-NNNN` 포함; **executor 커밋**은 메시지 끝에 trailer `Task: T-NNNN`을 넣는다; **드라이버 상태 커밋**(§3-4·§3-6·lock 연장)은 subject를 `driver: <요약>`으로 시작하고 `Task:` trailer를 넣지 않는다. §3-3의 충돌 점검 제외와 §3-5의 landed 확인·재개가 이 키로 동작한다(상태 커밋이 landed로 오탐되지 않도록 trailer를 기준으로 한다). 코드 모드의 squash-merge는 브랜치 커밋의 trailer를 잃을 수 있으므로 **PR 본문 마지막 줄에도 `Task: T-NNNN`을 두고** `gh pr merge --squash --body`로 그 본문을 squash 메시지에 쓴다.
- **크기 상한** ⚑ D4: 1 task ≤ 300 LOC 변경·≤ 5 파일(A-A 값 차용). 초과가 예상되면 planner가 쪼갠다; 실행 중 초과가 드러나면 executor는 **task 분할을 제안**하여 `Follow-ups`에 적고 현재 범위만 끝낸다.
- 2층 코드 task는 `Result`에 선택한 언어와 이유 한 줄(CLAUDE.md 언어 정책).
- task 파일 본문은 **영어**로 쓴다(커밋·PR 본문으로 흘러가므로 CLAUDE.md의 GitHub 영어 규칙에 맞춤). 본 문서·PLAN은 다른 설계 문서와 같이 한국어.

## 6. Planner

- 입력: `PLAN.md`의 현재 phase에서 체크되지 않은 첫 항목(들) + Requirements/OD 등록부 + 최근 journal + 열린 PR 목록.
- 출력: `tasks/T-NNNN-*.md` 1개 + (선택) 그 다음에 올 task의 후보 id(`STATE.nextTask`용). **자기완결**이어야 한다 — 다른 세션이 이 파일과 Required Reading만으로 실행 가능.
- 규칙: 새 task를 만들기 전에 `tasks/`의 기존 `TODO`·`INTERRUPTED` 파일을 먼저 소비(같은 PLAN 항목의 중복 생성 금지) · 크기 상한 준수 · `dependsOn` 충족된 것만 · `touchesFiles`가 열린 PR과 겹치면 뒤로 미룸 · 설계 선택이 OD 확정을 요구하면 task를 만들지 말고 HQ를 올림(§9 확정 전) · PLAN 항목이 "확정 필요"로 표시되어 있으면 그 OD/결정이 닫힐 때까지 건너뜀 · 모든 task의 Required Reading에 `PROCESS/DRIVER.md §3-5·§5`(executor 절차·명명 규약·시간 상한)를 포함.
- **phase 전환**: 현재 phase의 항목이 전부 `DONE` 또는 `BLOCKED`이면 `STATE.phase`를 올리고 journal에 기록한다. BLOCKED 항목은 다음 phase로 **이월**한다(교착 방지). `dependsOn`이 충족된 항목은 phase 경계를 넘어 선택할 수 있다.

## 7. 역할과 기존 스킬의 대응

| 역할 | 구현 | 비고 |
|---|---|---|
| driver | 본 문서 §3을 수행하는 세션(`/loop` 또는 cron 호출) | 상태·lock·journal만 다룸, 구현은 안 함 |
| planner | sub-agent (판단) | §6 |
| executor | sub-agent → [dev-item-address](../.claude/skills/dev-item-address/SKILL.md) | 구현·테스트·커밋·리뷰 사이클·merge를 모두 포함. A-13 원문은 "driver merges"라 했으나 본 설계에서는 executor가 merge를 수행한다(driver의 하위 작업) |
| reviewer | executor 안에서 spawn → [dev-code-review](../.claude/skills/dev-code-review/SKILL.md) | 컨텍스트 격리, 최대 7라운드 |
| notifier | driver가 수행 | BLOCKED → #5 코멘트, phase 전환·run 요약 → journal (FR-16의 개발 프로세스판) |

⚑ D5: 역할을 `.claude/agents/*.md` 파일로 분리할지(planner 포함). 초기 제안: 분리하지 않고 기존 스킬 2개 + 본 문서로 운용, 반복 후 필요가 드러나면 분리.

## 8. humanQuestions (BLOCKED의 기록)

- `STATE.humanQuestions[] = { id: HQ-NNNN, taskId, reason, question, askedAt, issueComment, resolvedAt?, decision? }`.
- 드라이버는 HQ를 만들 때 **#5에 코멘트**(영문, CLAUDE.md 언어 규칙)로 미러하고 그 URL을 `issueComment`에 적는다. **미러 코멘트의 고정 형식**: 첫 줄 `### HQ-NNNN — <task id>: <한 줄 요약>`, 마지막 줄 `— posted by driver`. **드라이버가 #5에 올리는 모든 코멘트**(HQ 미러, §9의 OD 종결 통지, phase 전환 알림 등)는 이 꼬리말을 단다 — §3-2 답변 판정에서 드라이버 코멘트를 제외하는 근거다(모든 코멘트가 같은 계정으로 올라가므로). 통합자 세션이 #5에 남기는 반영 노트도 HQ id를 언급할 때는 같은 꼬리말을 쓴다. 오너는 #5에서 **`HQ-NNNN`을 본문에 포함한 코멘트**(표식 없음; `✅`/`confirmed` 관례 권장)로 답하거나(§3-2가 감지), lock이 없을 때 STATE를 직접 고친다.
- 한 iteration에 새 HQ가 생기면 그 task는 `BLOCKED`로 두고, 같은 iteration에서 다른 task를 시작하지는 않는다(1 호출 = 1 task). 다음 iteration이 다른 task를 고른다.

## 9. OD 종결 권한 — ⚑ D6

현 규칙(CLAUDE.md "미결은 발명하지 않는다")대로면 OD-4(키 스키마)·OD-6(spec)·OD-8(레이아웃)이 확정될 때까지 2층 첫 커밋이 막힌다(Requirements "첫 커밋 전에 확정해야 하는 항목"). 자율 루프가 돌려면 **설계 수준 OD의 종결 권한**이 필요하다. 제안:

- **오너 전용**: #5 A/B 항목(사용자만 아는 사실·가치 판단), MVP 범위(C-6), 데이터 거버넌스(OD-25), 안전 gate(OD-3) — 항상 HQ.
- **드라이버 가능(제안)**: 그 외 설계 수준 OD는 executor가 **결정 기록**(ADR; 양식·위치는 첫 필요 시점에 — CLAUDE.md. 위치 제안: `ARCHITECTURE/decisions/ADR-NNNN.md`)을 쓰고 리뷰어가 Approve하면 OD 상태를 `확정`으로 바꾸되, **오너에게 #5 코멘트로 통지**하고 7일(⚑) 안에 이의가 없으면 유지. 이의가 있으면 되돌리는 task를 만든다.

이 항목이 확정되기 전까지 planner는 OD 확정이 필요한 task를 만들지 않고 HQ만 올린다. 관련: ⚑ D9 — Requirements의 "첫 커밋 전 확정" 규칙을 OD-4/6/8과 **무관한 골격 task**(PLAN P0-1~P0-5: `.gitattributes`, `pyproject`, CI 스켈레톤, 드라이버 STATE 스키마, README)에는 적용하지 않는다는 해석의 승인.

## 10. P0~P1 시드 — 첫 task 후보 (planner 입력)

[PLAN.md](PLAN.md)가 정본. 요지(PLAN id): P0-1 저장소 공통 규칙 + 빈 패키지 · P0-2 Python 프로젝트 설정 · P0-3 CI 스켈레톤(#9) · P0-4 드라이버 STATE 스키마 · P0-5 README · P1-1 FR-10 계약 + mock + 적합성 테스트 · P1-2 `cpu_standin` 어댑터 · P1-3/4 하네스 + 3-상태 캘리브레이션 · P1-5 GEMM spec 예시(OD-6 확정 필요) · P1-6 CAS · P1-7 `HIL-Claw-data` repo 생성(⚑ D7, 오너 지시 필요) · P1-8 런타임 STATE 스키마(OD-8 확정 필요).

A-A의 교훈대로 첫 task는 **작게**.

## 11. 결정 요청 목록 (⚑) — 답변 전 드라이버 미가동

| # | 항목 | 잠정값/제안 | 위치 |
|---|---|---|---|
| D1 | `/loop` 간격 · 세션당 iteration 상한 | 15분 · 10회 | §1 |
| D2 | `gh` 불가 시 GitHub MCP 폴백 | 두지 않음(종료) | §1 |
| D3 | lock ttl과 긴 task 처리 | ②+④: ttl 3시간, executor 상한 2시간 30분, 회수 전 브랜치 활동 점검 | §4, §3-5 |
| D4 | task 크기 상한 | ≤300 LOC · ≤5 파일 | §5 |
| D5 | 역할을 `.claude/agents` 파일로 분리할지 | 보류 | §7 |
| D6 | **OD 종결 권한** | §9 제안(설계 OD는 ADR+리뷰로 확정, 오너 통지·7일 이의) | §9 |
| D7 | `HIL-Claw-data` repo 생성 시점·설정 | P1-7, private | §10 |
| D8 | **상태 커밋의 리뷰 면제** + planner task 파일 포함 여부 + 드라이버 추가 BLOCKED 사유 4건 | 면제 채택, task 파일 포함, 사유 채택 | §2, §3 |
| D9 | **"첫 커밋 전 OD-4/6/8 확정" 규칙의 골격 task 적용 제외** | 제외 | §9 |
| D10 | **#9 "required check" vs A-13 "branch protection 없음"** — required status check는 branch protection/ruleset으로만 구현됨 | #8에 모순 등재; A-13 흐름에서는 executor가 CI 결과를 직접 확인하므로 required check 없이 동작 | PLAN P0-3 |
| D11 | 비대화 실행 권한(allowlist) 범위·위치 | 프로젝트 `settings.json`; `git fetch/push`, `gh pr/issue`, 테스트 실행 | §1-5 |
| D12 | P0.5 신규 게이트(테스트 존재 검사·커버리지)와 P0-4 드라이버 도구 테스트 — #9 범위 밖·오너 전역 규칙(도구 코드 테스트는 명시 요구 시만)과 맞닿음 | 오너 명시 여부 | PLAN P0.5-2/3, P0-4 |

답변 경로: 오너가 #5 코멘트 또는 채팅으로 D-n에 답하면 통합자(사람과 함께 일하는 세션)가 본 문서를 **문서 모드**로 갱신한다 — 표에서 지우고 해당 절의 ⚑를 제거하고 날짜를 남긴다. task 파일의 `hq: [D-n]`은 그때 비운다.
