# 개발 드라이버 (Development Driver)

HIL-Claw를 **만드는** 자동 개발 프로세스의 설계 문서이자, 매 반복(iteration)에 Claude Code 세션이 그대로 따르는 **드라이버 프롬프트**다. HIL-Claw가 **도는** 런타임 오케스트레이터(Requirements FR-1 라운드 루프, #4)와는 별개이며, 둘을 혼동하지 않는다.

- 절차는 Assessment-Agent(이하 A-A)의 **개발 절차**를 참조했다. 프로세스 파일 배치(드라이버 문서·PLAN·상태 파일·task 파일·journal)도 절차의 일부로서 따랐으나, A-A의 SW 구조·스택·레이아웃은 가져오지 않는다(CLAUDE.md, #5 A-12).
- 오너 결정: 실행 모델 = **로컬 Claude Code 세션의 `/loop`**(2026-10-03). 2026-10-05부터는 Claude Desktop의 스케줄 루틴(1 호출 = 1 iteration, §3-7의 연속 실행 조건을 만족하는 동안 연속 실행 상한까지(운영자 값, 현재 2); 간격은 운영자 값, 현재 매시)이 주력 진입점이며, 그 실행 설정은 §1-5(D13, 2026-10-06)에 있다. cron/스케줄 호출과의 호환은 §1의 조건으로 보장한다.
- **전제 커밋**: 본 문서는 CLAUDE.md의 "브랜치·merge 절차"(#5 A-13) 규칙 텍스트와, dev-item-address 4·9~13·15단계(문서 모드 분기·자율 merge)·dev-code-review(문서 모드 반환 경로)의 반영 커밋, 그리고 CLAUDE.md 테스트 규칙(§5, D12)을 전제한다. 전제 커밋은 2026-10-06에 main에 반영되었다. 권한 allowlist `.claude/settings.json`은 2026-10-05에 커밋되었다(D11); 루틴의 실행 모드는 2026-10-06에 D13으로 개정되었다(§1-5).
- 표기: **⚑ 결정 요청**은 §11에 모아 두었고, 2026-10-03~25에 D1~D20이 **모두 답변**되어 본 문서는 확정값으로 기술한다(§11 결정 이력). 예외는 둘이다. D17(nightly end-to-end 루틴)의 절차 본문은 PLAN P2-10이 만들 때까지 없고 §11의 행과 CLAUDE.md의 규칙만 있다. D15(드라이버 병렬 실행): 설계는 확정되었으나 전환 전이므로 본문은 아직 [proposals/D15-parallel-drivers.md](proposals/D15-parallel-drivers.md)에만 있고, 전환이 끝날 때까지 본 문서의 동작(§4 단일 lock)을 바꾸지 않는다. 새 결정 요청이 생기면 같은 방식으로 ⚑와 §11 행을 추가하고, 답변 전에는 그 항목에 걸린 task를 실행하지 않는다.

---

## 0. 범위와 원칙

- **대상**: HIL-Claw 저장소(1층 프롬프트·스킬·에이전트 정의, 2층 도구 패키지, 문서)의 구현을 task 단위로 진행·리뷰·merge하는 일. 런타임 run(데이터 plane)은 대상이 아니다.
- **단위**: 1 iteration = 1 task = 1 커밋(문서 모드) 또는 1 PR(코드 모드). 한 번에 하나만.
- **상태는 전부 파일**(`PROCESS/`)에 있다. iteration 사이에 대화 컨텍스트에 의존하지 않는다 — `/loop`·cron·`claude -p` 어느 것으로 불려도 같은 동작을 하는 근거다.
- **규칙의 정본**: CLAUDE.md(상시 규칙, A-13 merge 절차) > 본 문서 > 스킬. 본 문서는 CLAUDE.md를 반복하지 않고 참조한다.
- **미결은 발명하지 않는다**: OD는 §9의 권한 규칙으로만 확정한다 — 설계 수준 OD는 executor의 ADR + 리뷰어 Approve + 오너 통지, 오너 전용 항목은 HQ(§8). 그 밖의 방법으로 미결을 확정처럼 다루지 않는다.

## 1. 실행 모델

- 주력(2026-10-05~, D13): Claude Desktop의 스케줄 루틴 `hil-claw-dev-driver`가 새 세션으로 1 iteration을 실행하고, §3-7의 연속 실행 조건을 만족하는 동안 연속 실행 상한까지 이어서 실행한다(간격은 운영자 값 — D1, 현재 매시; 실행 설정은 §1-5). 보조: 오너 로컬 PC(C-7: Windows/WSL·macOS·Linux)의 Claude Code 세션에서 `/loop <간격> <드라이버 호출>`. 드라이버 호출 = "`PROCESS/DRIVER.md` §3을 1 iteration 수행". 간격과 세션당 iteration 상한은 **설계값이 아니라 운영자가 호출 시 정하는 값**이다(D1, 2026-10-03) — 드라이버는 이 값에 의존하지 않는다(§3-7의 연속 실행 판정만 호출 프롬프트가 준 임계·연속 실행 상한을 그대로 쓴다). 참고: 같은 대화에 wakeup이 누적되면 컨텍스트 한계에 닿으므로 세션당 상한을 두는 것이 좋다(A-A는 10회).
- **cron/스케줄 호환 조건**(오너 요구): 다음을 만족하므로 OS cron, `/schedule` 루틴, `claude -p`에서 같은 호출로 1 iteration을 실행할 수 있다(연속 실행은 3번 참조).
  1. **멱등·자기완결**: 매 iteration이 `git fetch` + `PROCESS/STATE.json` 읽기로 시작하고 대화 이력을 쓰지 않는다.
  2. **단일 실행 보장**: §4의 lock. lock이 유효하면 아무 것도 하지 않고 종료한다(중복 호출은 무해). lock은 main push의 fast-forward 규칙으로 성립하므로 **머신 간에도 유효**하다(`/schedule`의 클라우드 체크아웃 포함) — 단 ttl 판정은 벽시계에 의존하므로 시계 편차가 큰 머신을 섞지 않는다.
  3. **1 iteration = 최대 1 task**: 호출 주체가 무엇이든 한 iteration은 하나의 task를 끝내거나 BLOCKED를 기록하고 멈춘다. 1 호출은 1 iteration이 기본이며, 호출 프롬프트가 지정한 경우에만 §3-7의 연속 실행으로 iteration을 더 수행한다(D14).
  4. **네트워크 의존 최소**: GitHub(push·PR·이슈)와 Anthropic만 필요(C-7). `gh`가 없으면 **저장소 밖 로그**(`~/.hilclaw-driver.log` 또는 stderr; 추적 파일인 `PROCESS/journal/`에는 쓰지 않음 — clean tree 유지)에 "gh 불가"를 적고 종료하며 **오너에게 알린다**(세션 출력; cron 래퍼는 로그를 노출). GitHub MCP 폴백은 두지 않는다(D2, 2026-10-03).
  5. **비대화 실행 권한**(D11 → D13 개정, 2026-10-06): Claude Desktop의 스케줄 루틴은 `dontAsk` 모드를 제공하지 않고, 기본값인 auto 모드는 분류기가 sub-agent 스폰 시점에 위임 내용을 판정하여 A-13의 자율 merge를 `[Self-Approval]`로 거부할 수 있다(HQ-0001, 2026-10-05; 같은 설정에서 통과와 거부가 섞여 비결정적). 따라서 루틴은 A-A와 같은 운영 설정으로 돈다 — **권한 모드 = Bypass permissions**(permission prompt와 분류기를 거치지 않음), **작업 폴더 = 드라이버 전용 clone**(§1-6), **모델 = 루틴 설정에서 고정**(운영자 값; 모델명은 본 문서에 적지 않는다). 이 모드에서는 harness가 금지 동작을 막아 준다고 가정하지 않는다: `git push --force*`·`rm -rf *`·`gh repo delete *` 금지, Claude Code 프로그램(`claude`)의 자식 프로세스 시작 금지(D16, 2026-10-13: 하위 명령·플래그 불문; 드라이버 자신을 띄우는 호스트 세션 — Desktop 루틴, 보조 진입점 `claude -p` — 과는 별개다; 실제 Claude Code 세션이 있어야만 확인되는 사실은 런타임 인수 항목이지 드라이버 task가 아니다; CLAUDE.md "개발 드라이버와 런타임의 구분"; 예외는 §3을 수행하는 드라이버와 분리된 nightly end-to-end 루틴 하나뿐이며 §3을 수행하는 드라이버와 그 하위 에이전트에는 적용되지 않는다 — D17), `.claude/settings.json`·`settings.local.json` 편집 금지(세션이 자기 권한을 바꾸지 않음)는 드라이버·executor 규율로 지키고(금지 명령의 PreToolUse 가드 hook은 P0.5-4와 함께 검토 — follow-up, 범위는 그 task 작성 시 §9 기준으로 정함; 그 가드는 `claude` 자식 프로세스의 시작도 거부한다 — HQ-0007 답변 ④, 2026-10-13: T-0107 뒤의 별도 task. 그 가드는 nightly 루틴(D17)을 막아서는 안 되며 둘이 함께 서는 방법은 정해지지 않았다 — 가드 task는 ④대로 만들고, 그 방법은 PLAN P2-10에서 §8의 HQ로 오너에게 묻는다), 도구 호출이 거부되거나 실패하면 우회하지 않고 BLOCKED로 다룬다. HQ-0001은 오너의 #5 답변으로 종결되었다(2026-10-06). 프로젝트 **`.claude/settings.json`**(allow/deny 목록, D11 2026-10-05 커밋)은 CLI 경로(OS cron, `claude -p --permission-mode dontAsk`)의 안전망으로 유지한다: 그 경로에서는 드라이버가 쓰는 동작(`git fetch/push`, `gh pr/issue`, 테스트 실행)만 허용되고 목록 밖 호출은 묻지 않고 거부되며, `.claude/**`의 agent·스킬 `.md` 쓰기는 허용, settings 2종은 거부다.
  6. **작업 트리 전제**: 드라이버 전용 clone(또는 worktree), `main` 추적, clean tree. 오너의 개발 작업 트리와 공유하지 않는다. 스케줄 루틴의 작업 폴더(세션 cwd)도 이 clone으로 둔다 — 프롬프트로 명령만 clone에 보내면 프로젝트 설정과 권한 범위는 오너 트리 기준이 된다(2026-10-06 확인).
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
  proposals/D<n>-<slug>.md # 결정 요청(⚑)의 제안 본문(확정·반영 뒤에는 이력); §11에는 한 줄만
```

- **내용 변경**(DRIVER.md·PLAN.md 본문, task 파일의 명세부)은 **문서 모드**(CLAUDE.md A-13) — 리뷰어 통과 후 main 직접 push. *(A-13의 "문서·프로세스 파일"에 `PROCESS/`를 포함하는 것은 통합자 해석.)*
- **드라이버 상태 커밋**(`STATE.json`, journal, PLAN 체크박스, PLAN "보류" 절에 더하는 줄(D18), task 파일의 `status`/`Result`, planner가 생성한 task 파일)은 **리뷰 없이 push하는 예외**다 — lock 커밋에 리뷰를 붙이면 lock의 의미가 없고, 상태 커밋은 재생성 가능한 기계적 산출이기 때문이다. 경계: planner가 **생성 시점**에 쓴 task 파일은 이 예외에 포함되고, 그 뒤 사람이 명세를 고치는 것은 문서 모드. (D8 확정, 2026-10-05.)
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

0. **동기화** *(기계적)*: 호출의 첫 iteration이면 시작 시각(`date -u`)을 확보해 둔다(§3-7의 경과 판정용). `git fetch origin`; `main`을 checkout하고 **무조건** `git reset --hard origin/main` + `git clean -fd`로 맞춘다 — 직전 iteration의 거부된 상태 커밋, 사망 직전의 미커밋·untracked 잔재를 모두 버린다(전용 clone 전제 §1-6; 상태 커밋은 재생성 가능하다). CLAUDE.md "세션 진입 점검"의 열린 PR 목록을 확보한다(판정은 3단계에서).
1. **STATE 읽기** *(기계적)*: `PROCESS/STATE.json`을 읽는다. `lock`이 유효하면(§4) 아무 것도 쓰지 않고 종료한다. 만료된 lock이면 §4의 회수 절차로 간다(기록은 4단계 커밋에 포함).
2. **BLOCKED 동기화(읽기)** *(판단)*: 답은 오너가 `PROCESS/STATE.json`에 직접 적는다(§8). **반영 판정**: `status`가 `BLOCKED`인 task 가운데 front matter `hq`에 HQ id가 하나 이상 있고 그 HQ가 모두 `resolvedAt`을 가지며, `touchesFiles`가 0단계의 열린 PR(그 task 자신의 브랜치 `claude/T-NNNN-*`의 PR 제외)과 겹치지 않는 것. **그 task의 `status`를 `TODO`로 되돌려 `nextTask`로 둔다**(실제 쓰기는 4단계 커밋에 포함; `INTERRUPTED` task는 되돌리지 않는다 — `hq`가 모두 답을 가지면 3단계에서 그대로 선택되어 §3-5의 재개 규칙을 탄다; 이미 `DONE`인 task — 오너가 결과 없이 닫은 것, 예: D16의 T-0106 — 와 PLAN "보류" 절에 든 task(D18; `BLOCKED`로 둔다)는 되돌리지 않는다. 그 밖의 task를 되돌릴 때 그것이 PLAN 체크리스트 밖에서 나온 것(follow-up·하위 질문)이면 §6의 우선순위 판단을 하고, 두 목표에 필요하지 않으면 되돌리지 않고 보류 절에 한 줄 적는다(같은 상태 커밋). 보류 절에 넣는 task의 PR이 열려 있으면 4단계 push가 성공한 뒤 그 PR을 닫고 브랜치는 남긴다. 보류 절에 넣는 task를 `dependsOn`에 둔 `TODO` task(§6 "task 단위" ④)도 같은 상태 커밋에서 보류 절에 적고 `BLOCKED`로 둔다). "열린 PR과 충돌 위험"으로 막힌 task는 그 PR이 닫히거나 merge되면 자동 해소다. 드라이버는 #5를 읽지 않고, `resolvedAt`·`decision`을 쓰거나 고치지 않는다.
3. **task 선택(로컬)** *(판단)*: 선택 규칙 — ⓐ `hq`에 미해결 항목이 있는 task, `dependsOn`에 `DONE`이 아닌 task가 있는 task는 선택하지 않는다 ⓑ `currentTask`(직전 iteration이 중단된 것) → `nextTask` → `tasks/`의 기존 `TODO`·`INTERRUPTED` 파일 → 그래도 없으면 **planner**(§6)로 `PLAN.md`에서 다음 task를 1~3개 만들고(D20) 그 첫 번째를 고른다 ⓒ 선택한 task의 `touchesFiles`가 0단계의 열린 PR과 겹치면(**그 task 자신의 브랜치 `claude/T-NNNN-*`의 PR은 제외**) BLOCKED(사유: 열린 PR과 충돌 위험)로 두고 다음 후보를 본다. 선택 가능한 task가 없으면(전부 BLOCKED/완료/선행 task 대기) **아무 것도 커밋하지 않고**(예외: planner가 보류 줄을 돌려줬으면 드라이버가 그 줄만 PLAN "보류" 절에 적어 상태 커밋으로 push한다 — D18; push가 거부되면 그 줄을 버린다, 다음 iteration이 다시 만든다) 저장소 밖 로그에 한 줄 남기고 종료하며, 오너에게 `/loop` 중단을 권고한다 — 이때 이 iteration에서 내린 BLOCKED 판정은 저장되지 않는다(다음 iteration이 같은 판정을 반복; 멱등이라 무해).
4. **lock + currentTask 커밋** *(기계적)*: `lock`, `currentTask`, task `status: IN_PROGRESS`, 2단계의 HQ 동기화(그 단계에서 적는 보류 줄 포함), (planner가 만들었다면) 새 task 파일 전부, (planner가 돌려줬다면) PLAN "보류" 절에 적는 줄을 **한 커밋**(subject `driver: …`, §5)으로 main에 push한다. push가 거부되면(다른 드라이버나 오너의 답 commit이 먼저 push) **rebase·재시도하지 않고** 종료한다 — 이 거부가 곧 lock 경합의 패배다.
5. **실행** *(판단 + 기계적)*: task 파일(과 그 Required Reading — 모든 task는 본 문서 §3-5·§5를 포함한다, §6)만 입력으로 받는 **executor** sub-agent를 띄워 [dev-item-address](../.claude/skills/dev-item-address/SKILL.md) 절차를 수행시킨다 — 구현 → 테스트 → 커밋(모드 결정) → 리뷰어 사이클(dev-code-review) → A-13에 따라 merge/push(문서 모드는 `Reviewed-by` trailer 필수). 브랜치·커밋·PR은 §5의 `T-NNNN` 명명 규약을 따른다. executor는 요약(≤200자: 결과·커밋/PR·BLOCKED 여부)만 반환하고 긴 산출은 task 파일 `## Result`에 쓴다. **재개 규칙**(`currentTask`/`INTERRUPTED`로 재개한 경우): executor는 먼저 `git log origin/main --grep='^Task: T-NNNN'`(executor 커밋의 trailer — 드라이버 상태 커밋은 이 trailer가 없어 오탐되지 않음, §5)과 `gh pr list --search T-NNNN --state all`로 결과가 **이미 landed/merged**인지 확인한다 — 그렇다면 구현 없이 `DONE`으로 마감; PR이 open이면 이어서; closed-unmerged면 브랜치 `claude/T-NNNN-*`가 남아 있으면 이어서, 없으면 처음부터 한다. **브랜치 경합**: task 브랜치 push가 거부되면 rebase 1회 재시도, 재거부면 BLOCKED(`branch-contention`). `git push --force*`는 어떤 경우에도 쓰지 않는다(A-A 규칙). **시간 상한**: executor는 wall-clock 상한을 넘기면 현재 상태를 `Result`에 적고 BLOCKED(`task-timeout`)로 반환한다(D3: 상한 2시간 30분).
6. **마무리** *(기계적)*: task `status`(`DONE`/`BLOCKED`), `PLAN.md` 체크박스, `STATE.counters`·`lastIteration`, `nextTask`(planner가 §6에서 후보 id를 함께 제시했으면), `currentTask: null`, journal 1~5줄, **lock 해제**를 한 커밋으로 push한다. **push 전(`git fetch` 후)과 rebase 후에 `origin/main`의 `STATE.lock.owner`를 확인한다 — 자신이 아니면(ttl 만료로 회수됨) push하지 않고 저장소 밖 로그에 `lock lost`를 남기고 종료한다.** push가 거부되면(main이 움직임) `fetch` + rebase 후 재시도(≤3회 — 기계적 상수, A-A 값); `PROCESS/STATE.json`에 충돌이 나면 수동 병합하지 않고 **파일 단위로 origin 쪽을 취한 뒤**, owner가 여전히 자신이면(예: D3 ④의 lock 연장 커밋, 오너의 직접 편집·HQ 답 commit) **자기 wrap-up 변경(lock=null, currentTask=null, task status, counters — origin 값 기준으로 증분을 다시 계산 —, lastIteration, nextTask, 이 iteration이 만든 HQ 항목)을 다시 적용**하고 push한다 — 그렇지 않으면 lock이 걸린 채 push되어 ttl까지 교착한다. 그래도 실패하면 lock을 **유지한 채** 종료한다(ttl 회수에 맡김). executor가 BLOCKED로 반환해 새 HQ가 생기면 이 상태 커밋에 함께 기록한다(§8).
7. **종료 또는 연속 실행**: 한 iteration은 1 task로 끝낸다. **연속 실행**(D14, 2026-10-06): 호출 프롬프트가 연속 실행을 지정했고 다음을 모두 만족하면, 같은 세션에서 0단계부터 iteration을 한 번 더 수행한다 — ⓐ 방금 끝낸 iteration의 결과가 `DONE`이고 새 HQ가 없다 ⓑ 6단계의 마무리 push가 성공해 lock이 해제되었다 ⓒ 이 호출의 시작(0단계에서 확보한 시각)부터 그 마무리 push까지의 경과가 임계 미만이다 ⓓ 이 호출에서 수행한 iteration 수가 **연속 실행 상한**(호출당 iteration 수 — D1의 `/loop` 세션당 상한과 다른 값) 미만이다. 임계와 연속 실행 상한은 호출 프롬프트가 주는 운영자 값이다(D14; 현재 루틴은 25분·2회). 이 판정만은 이 호출의 대화에 남은 값(시작 시각, 수행한 iteration 수, 직전 결과)을 쓴다 — 프롬프트가 임계 또는 연속 실행 상한을 주지 않았거나 이 값들 중 하나라도 확인할 수 없으면 연속 실행하지 않는다. 그 밖의 경우 — BLOCKED, task를 실행하지 않고 끝난 iteration(예: 유효한 lock, lock 연장 후 종료, lock 경합 패배, 선택 가능한 task 없음, `gh` 불가), `lock lost`, 마무리 push 실패 — 에는 연속 실행하지 않고 종료한다. 추가 iteration은 첫 iteration과 같은 절차다: task 선택과 실행은 대화에 남은 직전 iteration의 내용이 아니라 다시 읽은 파일 상태만을 근거로 하고(§0), lock을 새로 잡으며, executor 시간 상한(D3)도 새로 적용된다. 추가 iteration이 다음 스케줄 발화와 겹치면 그 발화는 1단계에서 종료한다(§1-2). 고정 간격 `/loop` 호출에서 운영자가 세션당 상한(wakeup 누적 상한)을 넣었다면(D1 — 드라이버 고유값이 아님) 그 도달 시 journal에 기록하고 오너에게 `/loop` 중단을 요청한다(고정 간격 `/loop`를 모델이 스스로 멈출 수 있는지는 미확인); 넣지 않았으면 생략.

**BLOCKED 사유**: CLAUDE.md A-13의 6가지(새 외부 의존성 · 데이터 plane 스키마 변경(STATE/spec/eval/artifacts) · 리뷰 7라운드 초과 · CI 3연속 실패 · 요구 불명확/미결 발명 의심 · 보안 의심) + 드라이버 추가 4가지(D8 확정): 열린 PR과의 파일 충돌 위험 · Requirements OD 확정이 필요한 설계 선택(§9 — 오너 전용 OD이거나, task 범위에 그 OD의 ADR이 없는데 실행 중 드러난 설계 OD) · `task-timeout` · `branch-contention`(§3-5). BLOCKED는 §8에 따라 HQ로 기록한다.

## 4. Lock (단일 실행 보장)

- `STATE.lock = { owner, acquiredAt, ttlMinutes }`. owner = `<hostname>:<session-id 또는 pid>`.
- 유효 = `now < acquiredAt + ttl`. lock 획득은 **main에 push되어야** 성립한다(push 거부 = 경합 패배). A-A의 lock 브랜치 CAS와 같은 효과를 main 자체의 fast-forward 규칙으로 얻는다 — 별도 브랜치·스크립트 없음. 머신 간에도 유효(§1-2).
- **ttl과 긴 task** — ttl이 task 소요를 보장하지 못하면 stale 회수 시점에 두 드라이버가 같은 task를 병행할 수 있다(리뷰 7라운드 코드 task는 1시간을 넘길 수 있음). **확정(D3, 2026-10-03)**: ttl = **3시간**; executor wall-clock 상한 = **2시간 30분**(§3-5; 초과 시 BLOCKED `task-timeout` + lock 해제); lock이 유효한 동안 들어온 두 번째 드라이버는 스스로 종료한다(§3-1); 그리고 **회수 전 활동 점검** — 그 task 브랜치 `claude/T-NNNN-*`의 마지막 push가 ttl보다 최근이면 살아 있다고 보고 회수하지 않고 `acquiredAt`만 연장하는 상태 커밋(STATE.json만, journal은 쓰지 않음)을 push한 뒤 **종료**(이번 iteration은 작업 없음; main 커밋 없는 사실상의 heartbeat를 브랜치 활동으로 대신함). 연장 push가 거부되면(그 사이 owner의 wrap-up이 landed) §3-4와 같이 재시도 없이 종료.
- **stale 회수**: 만료 lock을 발견한 드라이버는(활동 점검을 통과한 뒤) journal에 "stale lock reclaimed(owner, acquiredAt)"를 남기고, 그 lock의 `currentTask`를 `INTERRUPTED`로 표시한 뒤 §3-3에서 재개한다(§3-5 재개 규칙: landed 확인 → 기존 브랜치/PR 이어쓰기 → 처음부터). 이전 드라이버가 아직 살아 있을 가능성은 §3-6의 owner 확인(lock을 잃은 쪽은 push하지 않음)으로 막는다.
- 운용상 결과: main에는 iteration당 상태 커밋 2개(lock, wrap-up)가 쌓인다. 오너의 수동 push는 항상 rebase가 필요하고, 오너가 `PROCESS/STATE.json`을 직접 고치는 것은 **lock이 없을 때만** 한다 — 예외는 HQ의 답(§8)이다.

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

- `status`는 드라이버가 바꾼다: `IN_PROGRESS`(§3-4), `INTERRUPTED`(§4 회수), `DONE`/`BLOCKED`(§3-6), `BLOCKED` → `TODO`(§3-2 HQ 해소). 예외: task를 다시 하지 않는 HQ 답은 오너의 답 commit이 `DONE`으로 바꾼다(§8).
- **명명 규약**(task ↔ 산출물 연결 키): 브랜치 `claude/T-NNNN-<slug>`; PR 제목에 `T-NNNN` 포함; **executor 커밋**은 메시지 끝에 trailer `Task: T-NNNN`을 넣는다; **드라이버 상태 커밋**(§3-4·§3-6·lock 연장)은 subject를 `driver: <요약>`으로 시작하고 `Task:` trailer를 넣지 않는다. §3-3의 충돌 점검 제외와 §3-5의 landed 확인·재개가 이 키로 동작한다(상태 커밋이 landed로 오탐되지 않도록 trailer를 기준으로 한다). 코드 모드의 squash-merge는 브랜치 커밋의 trailer를 잃을 수 있으므로 **PR 본문 마지막 줄에도 `Task: T-NNNN`을 두고** `gh pr merge --squash --body`로 그 본문을 squash 메시지에 쓴다.
- **크기 상한**(D4, 2026-10-03; D20 개정, 2026-10-25): 1 task ≤ 600 LOC 변경·≤ 10 파일 — **테스트 코드는 상한에서 제외**(테스트는 길어도 된다; ADR 등 문서 줄은 센다). 상한 안에서 task를 어떻게 묶는지는 §6 "task 단위"다. 초과가 예상되면 planner가 쪼갠다; 실행 중 초과가 드러나면 executor는 **task 분할을 제안**하여 `Follow-ups`에 적고 현재 범위만 끝낸다.
- 2층 코드 task는 `Result`에 선택한 언어와 이유 한 줄(CLAUDE.md 언어 정책).
- **코드 task의 테스트 규칙**(D12, 2026-10-05; CLAUDE.md 상시 규칙·dev-item-address 4단계·dev-code-review에 미러됨): ① 2층 패키지(`hilclaw/`)의 **line coverage ≥ 80%, function coverage ≥ 80%** 유지(CI 게이트, PLAN P0.5-3) ② 테스트는 happy/error/branch에 더해 **negative case**(잘못된 입력·실패 경로)를 반드시 포함 ③ 건드린 모듈의 모든 public 함수에 테스트 ④ 새 모듈에는 대응 테스트 파일 필수(CI 테스트 존재 검사, P0.5-2) ⑤ **테스트 코드·테스트 스위트·테스트 스크립트 자체를 대상으로 하는 테스트는 추가하지 않는다** — CI 워크플로·hook 스크립트·드라이버 보조 스크립트도 같은 규칙(오너 전역 규칙). 명시 예외 두 개만 테스트 대상: 드라이버 `STATE.json` 스키마 검증기(P0-4)와 `gh pr merge` 가드 hook(P0.5-4).
- task 파일 본문은 **영어**로 쓴다(커밋·PR 본문으로 흘러가므로 CLAUDE.md의 GitHub 영어 규칙에 맞춤). 본 문서·PLAN은 다른 설계 문서와 같이 한국어.

## 6. Planner

- 입력: `PLAN.md`의 현재 phase에서 체크되지 않은 첫 항목(들) + Requirements/OD 등록부 + 최근 journal + 열린 PR 목록.
- 출력: `tasks/T-NNNN-*.md` 1~3개(아래 "task 단위" ④) + 그 다음에 올 task의 후보 id(2개 이상 만들었으면 두 번째 task의 id, 아니면 선택)(`STATE.nextTask`용) + (있으면) 아래 우선순위 규칙으로 보류한 일의 줄 — planner는 그 줄을 드라이버에 돌려주고 PLAN에 쓰지 않으며, 드라이버가 §3-4(또는 §3-3의 예외)의 상태 커밋으로 PLAN "보류" 절에 적는다. **자기완결**이어야 한다 — 다른 세션이 이 파일과 Required Reading만으로 실행 가능.
- 규칙: 새 task를 만들기 전에 `tasks/`의 기존 `TODO`·`INTERRUPTED` 파일을 먼저 소비(같은 PLAN 항목의 중복 생성 금지) · 크기 상한 준수 · `dependsOn`이 충족된 것만(예외: 같은 호출에서 함께 만드는 선행 task — 아래 "task 단위" ④) · `touchesFiles`가 열린 PR과 겹치면 뒤로 미룸 · 설계 선택이 **오너 전용** 결정(#5 A·B 항목, C-6, OD-25, OD-3)을 요구하면 task를 만들지 말고 HQ를 올림 · **설계 수준** OD를 요구하면 그 OD를 닫는 **ADR 작성을 task 범위에 포함**시켜 만든다(§9; PLAN의 "OD-n 종결 필요(§9)" 표시) · PLAN 항목이 "오너 확정 필요"로 표시되어 있으면 그 결정이 닫힐 때까지 건너뜀 · task가 개발 머신에 **런타임에만 필요한 것**(로그인된 `claude`, 개발 머신에 없는 보드·가속기, API 키)을 요구하거나 Claude Code 자식 세션을 띄워야 하면 task를 만들지 않는다 — 그 확인은 런타임 인수 항목으로 돌려 §8의 HQ(사유 `runtime-acceptance`)로 기록하거나, 런타임 자체 점검 코드 task로 바꾼다(D16, CLAUDE.md "개발 드라이버와 런타임의 구분"; nightly end-to-end 루틴(D17)이 있다는 것은 이 규칙의 예외가 아니다 — §3을 수행하는 드라이버의 task는 여전히 실제 `claude`를 띄우지 않고, 그 루틴의 정의를 만드는 task(PLAN P2-10)도 스텁으로만 검증한다) · 모든 task의 Required Reading에 `PROCESS/DRIVER.md §3-5·§5`(executor 절차·명명 규약·시간 상한)를 포함.
- **우선순위(D18, [오너 2026-10-19, 채팅](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6280029924))**: 도달 목표는 PLAN P2-14(Llama 3.2 1B end-to-end), 가까운 목표는 P2-5다. PLAN 체크리스트 항목이 아닌 일 — 이전 task의 follow-up, OD 하위 질문, 재계획 — 을 task로 만들기 전에 planner는 그것이 P2-5나 P2-14에 필요한지 판단한다. 둘 다에 필요하지 않은 것 — 지금 동작으로도 목표가 도는 입력 경화, ADR·문서의 인용·문구 정리, 동작이 바뀌지 않는 리팩토링, P1-1·P1-8의 완료 기준 밖이면서 두 목표에도 필요하지 않은 하위 질문 — 은 task로 만들지 않고 보류 줄로 드라이버에 돌려준다(위 "출력"; 이미 보류 절에 있는 일은 다시 판단하지도 적지도 않는다). 이 판단의 대상이 아닌 것: §9의 오너 이의에 따른 되돌림, D17 ④의 nightly 실패 이슈(그 순서는 D17 (나)로 P2-10이 정한다). 판단이 서지 않으면 task로 만들고 그 이유를 task의 Why에 적는다. PLAN 체크리스트 항목(P2-8·P2-10 포함)은 이 규칙의 대상이 아니며 그 순서는 PLAN P2 머리에 있다 — 단 체크리스트 항목을 인용하더라도 그 항목의 완료 기준(P1-1·P1-8은 PLAN의 기준)에 들지 않는 일은 체크리스트 밖의 일로 본다. 이 규칙은 오너 전용 결정·BLOCKED 사유·품질 규칙(테스트·리뷰·CI)을 바꾸지 않는다.
- **task 단위**(D20, [오너 2026-10-25, 채팅](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6397069546)): task당 고정 비용(planner, lock·마무리 커밋, Required Reading, CI 대기, 리뷰어 spawn)이 크므로 task는 함수 하나가 아니라 기능 하나를 단위로 만든다.
  ① **ADR과 코드를 한 task로**: 드라이버가 닫을 수 있는 설계 결정(§9)의 ADR은 그 결정의 첫 코드 slice와 같은 task로 만든다(코드 모드; ADR 파일이 PR에 함께 든다). ADR만 있는 task는 결정에 코드가 따르지 않거나, ADR을 쓰다가 오너 전용 결정이 드러날 소지가 클 때만 만든다.
  ② **같은 모양의 결정은 한 ADR로**: 여러 대상에 같은 질문을 던지는 결정(예: 연산 kind마다의 계약)은 대상마다 ADR을 두지 않고 한 ADR의 표나 절로 다룬다.
  ③ **slice를 합친다**: 한 ADR의 코드 slice들은 합쳐서 크기 상한(§5) 안에 들면 한 task로 만든다. 상한의 절반에 못 미칠 task는 같은 PLAN 항목의 인접 작업과 합칠 수 있으면 합친다.
  ④ **여러 task를 한 번에**: planner는 같은 PLAN 항목에서 이어서 할 task를 최대 3개까지 한 번에 만든다. 각 task의 `dependsOn`에는 함께 만든 앞선 task를 **모두** 적고, 두 번째 task의 id를 `nextTask` 후보로 돌려준다. 아직 landed되지 않은 결정의 결과에 내용이 좌우되는 task는 미리 만들지 않는다. 드라이버는 그 파일 모두를 §3-4의 상태 커밋에 넣고 첫 번째를 실행한다. 나머지는 `TODO`로 남아, 앞선 task가 모두 `DONE`이 된 뒤 3단계에서 선택된다(3단계 ⓐ). 앞선 task가 `BLOCKED`이면 뒤 task는 그대로 기다린다. 앞선 task가 PLAN "보류" 절로 가면 드라이버는 같은 상태 커밋에서 뒤 task도 보류 절에 적고 `BLOCKED`로 둔다(§3-2). 앞선 task가 결과 없이 `DONE`으로 닫히면(§8) 뒤 task의 executor가 dev-item-address 1단계에서 그 task가 아직 유효한지 확인한다.
  이 규칙은 리뷰 7라운드 한도, 테스트 규칙(D12), BLOCKED 사유, 오너 전용 결정을 바꾸지 않는다.
- **phase 전환**: 현재 phase의 항목이 전부 `DONE` 또는 `BLOCKED`이면 `STATE.phase`를 올리고 journal에 기록한다. BLOCKED 항목은 다음 phase로 **이월**한다(교착 방지). `dependsOn`이 충족된 항목은 phase 경계를 넘어 선택할 수 있다.

## 7. 역할과 기존 스킬의 대응

| 역할 | 구현 | 비고 |
|---|---|---|
| driver | 본 문서 §3을 수행하는 세션(스케줄 루틴·`/loop`·cron 호출) | 상태·lock·journal만 다룸, 구현은 안 함 |
| planner | sub-agent (판단) | §6 |
| executor | sub-agent → [dev-item-address](../.claude/skills/dev-item-address/SKILL.md) | 구현·테스트·커밋·리뷰 사이클·merge를 모두 포함. A-13 원문은 "driver merges"라 했으나 본 설계에서는 executor가 merge를 수행한다(driver의 하위 작업) |
| reviewer | executor 안에서 spawn → [dev-code-review](../.claude/skills/dev-code-review/SKILL.md) | 컨텍스트 격리, 최대 7라운드 |
| notifier | driver가 수행 | BLOCKED → `PROCESS/STATE.json`의 HQ(§8), §9의 OD 종결 통지 → #5 코멘트, phase 전환·run 요약 → journal (FR-16의 개발 프로세스판) |

**확정(D5, 2026-10-03)**: planner·executor·reviewer 세 역할을 `.claude/agents/*.md`(컨텍스트 격리 subagent 정의)로 **MVP 개발 과정에서 만든다**; 기존 스킬 2개를 감싸고, notifier는 드라이버 본문에 남는다. PLAN P0-6. **설계(통합자 제안, P0-6에서 리뷰로 확정)**: 이름 `dev-planner`(§6)·`dev-executor`(dev-item-address 수행)·`dev-reviewer`(dev-code-review; Write 권한 없음, 읽기 + `gh pr comment`만); 허용 도구는 frontmatter로 고정하고, 모델은 CLAUDE.md 모델 배정 원칙(판단/기계적; 특정 모델명 하드코딩 금지)에 따른다.

## 8. humanQuestions (BLOCKED의 기록)

- `STATE.humanQuestions[] = { id: HQ-NNNN, taskId, reason, question, askedAt, issueComment, resolvedAt?, decision? }`.
- **기록**(D19): 드라이버는 HQ를 `PROCESS/STATE.json`에만 기록하고 #5에 미러하지 않는다. 새 HQ는 그것을 만든 상태 커밋(§3-4·§3-6)에 들어가고, 막힌 task의 `hq`에 그 id를 더하며, journal 줄에 id를 적는다. `question`은 **한국어**로 쓴다 — 쟁점, 선택지 (a)·(b)·…, 답이 없는 동안 막히는 것과 막히지 않는 것. `issueComment`는 D19 전 HQ의 #5 미러 URL이고, 이후 HQ는 null이다.
- **답**(D19): 오너는 `PROCESS/STATE.json`의 `humanQuestions`(또는 journal)에서 질문을 읽고, 그 항목에 `resolvedAt`(ISO-8601 UTC)과 `decision`을 적어 main에 commit한다. 통합자 세션이 채팅의 답을 옮겨 적는 것도 같다. 이 commit은 lock이 있어도 된다 — 드라이버의 push 거부(§3-4)와 재적용(§3-6)이 다룬다. 그 대신 STATE.json에서는 그 항목의 `resolvedAt`·`decision`만 바꾸고, push가 거부되면 rebase해 origin의 다른 필드를 덮어쓰지 않는다. 답이 task를 다시 하지 않는 것이면 같은 commit에서 그 task 파일의 `status`도 `DONE`으로 바꾼다 — 그러지 않으면 §3-2가 `TODO`로 되돌린다. #5 코멘트는 HQ의 답으로 읽지 않는다.
- **#5에 남는 드라이버 코멘트**(§9의 OD 종결 통지 등)는 마지막 줄에 `— posted by driver`를 단다 — 같은 계정으로 올라가는 오너 코멘트와 구분한다.
- 한 iteration에 새 HQ가 생기면 그 task는 `BLOCKED`로 두고, 같은 iteration에서 다른 task를 시작하지는 않는다(1 iteration = 1 task). 그 호출은 연속 실행(§3-7)도 하지 않으며, 다음 호출의 iteration이 다른 task를 고른다.

## 9. OD 종결 권한 (D6 확정, 2026-10-05)

CLAUDE.md "미결은 발명하지 않는다"를 그대로 두면 OD-4(키 스키마)·OD-6(spec)·OD-8(레이아웃)이 확정될 때까지 2층 첫 커밋이 막힌다. 자율 루프를 위해 **설계 수준 OD의 종결 권한**을 다음과 같이 둔다.

- **오너 전용**(항상 HQ): #5 A/B 항목(사용자만 아는 사실·가치 판단), MVP 범위(C-6), 데이터 거버넌스(OD-25), 안전 gate(OD-3).
- **드라이버 가능**: 그 외 설계 수준 OD는 executor가 **결정 기록**(ADR; 양식·위치는 첫 필요 시점에 정한다 — CLAUDE.md. 위치 제안: `ARCHITECTURE/decisions/ADR-NNNN.md`)을 쓰고 리뷰어가 Approve하면 OD 상태를 `확정`으로 바꾸되(반영 커밋 링크 필수), **오너에게 #5 코멘트로 통지**(드라이버 꼬리말, §8)하고 **7일** 안에 이의가 없으면 유지한다. 이의가 있으면 되돌리는 task를 만든다.

오너 전용 항목이 필요한 task는 HQ를 올린다. **D9(확정, 2026-10-05)**: Requirements의 "첫 커밋 전 확정" 규칙은 OD-4/6/8과 **무관한 골격 task**(PLAN P0)에는 적용하지 않는다.

## 10. P0~P1 시드 — 첫 task 후보 (planner 입력)

[PLAN.md](PLAN.md)가 정본. 요지(PLAN id): P0-1 저장소 공통 규칙 + 빈 패키지 · P0-2 Python 프로젝트 설정 · P0-3 CI 스켈레톤(#9) · P0-4 드라이버 STATE 스키마 · P0-5 README · P1-1 FR-10 계약 + mock + 적합성 테스트 · P1-2 `cpu_standin` 어댑터 · P1-3/4 하네스 + 3-상태 캘리브레이션 · P1-5 GEMM spec 예시(OD-6 종결 필요 — §9 ADR 경로) · P1-6 CAS · P1-7 `hilclaw.config.json`(데이터 repo `HIL-Claw-data`는 2026-10-05 생성됨 — D7) · P1-8 런타임 STATE 스키마(OD-8 종결 필요 — §9 ADR 경로).

A-A의 교훈대로 첫 task는 **작게**.

## 11. 결정 이력 (D1~D20 — 모두 답변됨, 2026-10-03~25, #5 코멘트·채팅)

확정값은 각 절 본문에 있다(D15는 예외 — 전환 전까지 본문은 proposals 문서, 해당 행 참조; D17의 절차 본문은 PLAN P2-10 전까지 없다). 본 표는 이력이며, "잠정값/제안" 열에서 제안과 달라진 행은 **→** 뒤에 확정 내용을 적었다(표시 없는 행은 제안 그대로 확정).

| # | 항목 | 잠정값/제안 | 위치 |
|---|---|---|---|
| D1 | `/loop` 간격 · 세션당 iteration 상한 | 15분 · 10회 → **운영자 값, 설계 무관** | §1 |
| D2 | `gh` 불가 시 GitHub MCP 폴백 | 두지 않음(종료) → **확정 + 오너에게 알림** | §1 |
| D3 | lock ttl과 긴 task 처리 | ②+④: ttl 3시간, executor 상한 2시간 30분, 회수 전 브랜치 활동 점검 | §4, §3-5 |
| D4 | task 크기 상한 | ≤300 LOC · ≤5 파일 → **확정, 테스트 코드는 상한 제외**(D20에서 ≤600 LOC · ≤10 파일로 개정) | §5 |
| D5 | 역할을 `.claude/agents` 파일로 분리할지 | 보류 → **채택(MVP 개발 중 생성, P0-6)** | §7 |
| D6 | **OD 종결 권한** | §9 제안(설계 OD는 ADR+리뷰로 확정, 오너 통지·7일 이의) | §9 |
| D7 | `HIL-Claw-data` repo 생성 시점·설정 | P1-7, private → **2026-10-05 즉시 생성(private, 빈 레이아웃 + README + .gitignore); P1-7은 config 파일만** | §10 |
| D8 | **상태 커밋의 리뷰 면제** + planner task 파일 포함 여부 + 드라이버 추가 BLOCKED 사유 4건 | 면제 채택, task 파일 포함, 사유 채택 | §2, §3 |
| D9 | **"첫 커밋 전 OD-4/6/8 확정" 규칙의 골격 task 적용 제외** | 제외 | §9 |
| D10 | **#9 "required check" vs A-13 "branch protection 없음"** — required status check는 branch protection/ruleset으로만 구현됨 | #8에 모순 등재; A-13 흐름에서는 executor가 CI 결과를 직접 확인하므로 required check 없이 동작 → **(a) 확정 + `gh pr merge` 가드 hook(P0.5-4); #9 재문구, #8 M24 종결** | PLAN P0-3, P0.5-4 |
| D11 | 비대화 실행 권한(allowlist) 범위·위치 | 프로젝트 `settings.json`; `git fetch/push`, `gh pr/issue`, 테스트 실행 → **확정: `dontAsk`(비대화), `.claude/settings.json` 커밋(2026-10-05), `.claude/**` 쓰기 허용·settings 2종 거부, `--force*`/`rm -rf`/`gh repo delete` 거부** → **2026-10-06 D13으로 개정**: `dontAsk`+allowlist는 CLI 경로에만 적용(Desktop 루틴에는 `dontAsk`가 없음) | §1-5 |
| D12 | P0.5 신규 게이트(테스트 존재 검사·커버리지)와 P0-4 드라이버 도구 테스트 | **채택**: 존재 검사 + line/function ≥ 80%; 도구 코드 테스트 금지의 명시 예외 2개(STATE 검증기, merge 가드 hook); 테스트 규칙 신설(§5) | PLAN P0.5-2/3/4, P0-4, §5 |
| D13 | **드라이버 루틴 실행 모드**(HQ-0001, 2026-10-05: auto 모드 분류기가 executor 스폰을 `[Self-Approval]`로 거부; 같은 설정에서 통과·거부가 섞임) | (a) 권한 설정 / (b) 절차 변경(승인된 Draft PR에서 정지, 오너 merge) → **(a) 확정(오너 2026-10-06, 채팅): A-A와 같은 운영 설정 — Bypass permissions + 전용 clone 폴더 + 모델 고정; A-13 자율 merge 유지; 금지 동작은 드라이버 규율로; Desktop 루틴이 주력 진입점, `/loop`·`claude -p`는 보조; HQ-0001 종결은 오너의 #5 답변으로(§3-2)** | §1-5, §1-6 |
| D14 | **한 호출의 연속 실행**(루틴이 매시 1 iteration만 돌아, 일찍 끝난 호출의 남은 시간이 비는 문제) | 1 호출 = 1 task 유지 / 조건부 추가 iteration → **조건부 추가 확정(오너 2026-10-06, 채팅): 직전 iteration이 `DONE`·새 HQ 없음·마무리 push 성공이고 호출 시작부터의 경과가 임계 미만이면 연속 실행 상한까지 이어서 실행; 임계·연속 실행 상한(호출당 iteration 수)은 운영자 값(현재 루틴 25분·2회); 1 iteration = 1 task는 유지** | §1-3, §3-7 |
| D15 | **드라이버 병렬 실행**(저장소 단일 lock이라 무관한 task도 동시에 진행하지 못함) | task 단위 lock(`locks[]` + `maxParallel`), clone별 `driverId`, 독립성 선택 규칙, merge 관문 — 본문: [proposals/D15-parallel-drivers.md](proposals/D15-parallel-drivers.md) → **제안대로 확정(오너 2026-10-06, 채팅; D15-1~4): 병렬 도입, 상한은 `STATE.maxParallel`(전환 직후 1 → 확인 뒤 2), CI가 main에서 동작하고 merge 가드 hook이 등록된 뒤에 전환, 전환은 루틴을 멈춘 통합자 세션이 수행. 전환이 끝날 때까지 §4의 단일 lock이 현행이며 드라이버는 proposals/D15 문서의 규칙을 따르지 않는다** | (전환 시 §1~§6·§8) |
| D16 | **개발 드라이버와 런타임의 구분**(HQ-0006, 2026-10-13: T-0106이 executor로 `claude -p` 자식 세션을 띄워 런타임 사실(ADR-0010 F10)을 확인하려다 CLI 미로그인으로 BLOCKED; 질문은 개발 머신의 CLI 로그인을 첫 선택지로 둠) | (a) 개발 머신 CLI 로그인 / (b) 오너 수동 확인·런타임 자체 점검 / (c) 보류 → **(b) 확정(오너 2026-10-13, 채팅·#5): 드라이버와 하위 에이전트는 `claude` 자식 프로세스를 시작하지 않고 런타임 전용 요건(로그인된 `claude`, 개발 머신에 없는 보드·가속기, API 키)을 개발 머신에 요구하지 않는다; 라이브 세션·그런 HW로만 확인되는 사실은 런타임 인수 항목(오너 수동 확인 또는 런타임 자체 점검 코드; 드라이버는 §8 HQ 경로, 사유 `runtime-acceptance`로 통지). T-0106은 재실행하지 않고 결과 없이 닫는다(status `DONE`, 착지 없음, 오너 세션이 main에 직접 기록) — §3-2의 복귀 대상이 아니며 그 확인은 오너의 수동 확인(b-1)과 런타임 자체 점검 P1-9(b-2)로 이관; `claude` 자식 프로세스의 가드 hook 포함 여부는 HQ-0007과 함께 → 포함(HQ-0007 답변 ④, 2026-10-13; §1-5)** | §1-5, §3-2, §6; CLAUDE.md |
| D17 | **nightly end-to-end: D16의 예외**(오너 2026-10-13, 채팅: 개발 드라이버가 end-to-end 테스트를 위해 런타임 오케스트레이터를 만들어 실행하는 것은 허용되고 적극 쓰여야 한다; 비용 때문에 자주는 못 쓰고 nightly test 정도로) | 범위: nightly E2E만 / nightly에서 다른 인수 항목도 / D16 전면 철회 · 결과: 회귀 신호로만 / 수용 기준에도 · 기동: 별도 nightly 루틴 / 시간당 드라이버가 하루 1회 → **확정(오너 2026-10-13, 채팅): ① 예외는 실제 `claude`를 쓰는 nightly end-to-end run 하나뿐 — 그 밖의 런타임 인수 항목은 D16대로 오너 수동 확인·런타임 자체 점검으로 남는다. ② 결과는 회귀 신호(통과·실패와 로그)로만 쓰고, 수용 기준 측정(PLAN P2-9)과 사례 저장(FR-18)에는 쓰지 않는다. ③ §3을 수행하는 드라이버(진입점·간격 불문 — 이 행에서 "시간당 드라이버")와 분리된 별도 nightly 루틴이 기동하고 루틴 등록은 오너가 한다; 시간당 드라이버와 그 하위 에이전트는 계속 `claude`를 시작하지 않으며 nightly의 결과만 읽는다. ④ (오너 2026-10-13, 채팅 — 추가 확정) nightly run의 실패는 이슈로 등록된 뒤 자동으로 해결된다(오너의 말은 여기까지다). 통합자 독해: "이슈"는 GitHub Issue이고, 등록도 사람이 옮겨 적지 않고 이루어진다. 따름: 자동으로 해결하는 것은 시간당 드라이버다 — 이 저장소를 고치는 것은 §4의 lock 아래 A-13 절차로 도는 §3의 드라이버뿐이므로(§0, §4) 실패 이슈는 그 드라이버의 task가 된다; 시간당 드라이버는 실제 `claude`를 띄우지 못하므로(③) 고친 것이 맞는지는 뒤따르는 nightly run만 확인한다; 드라이버가 고칠 수 없는 원인(nightly 머신의 환경 — 로그인 만료, 컨테이너 런타임 부재, 사용량 소진 등)은 자동 해결의 대상이 아니라 기존 §8의 HQ 경로다; nightly 루틴이 도는 머신은 로그인된 `claude`를 전제한다(D16의 "개발 머신에 요구하지 않는다"의 유일한 예외); HQ-0007 답변 ④의 `claude` 자식 프로세스 가드는 nightly 루틴을 막아서는 안 된다(§1-5). 정하지 않은 것 — (가) 오너·운영자의 값이어서 task가 정하지 않고 PLAN P2-10에서 §8의 HQ로 묻는 것: nightly run의 구성(출발점 후보는 P2-5의 구성), 실행 시각, 사용량 상한, 루틴의 권한 모드·작업 폴더·머신, 가드와 nightly 루틴이 함께 서는 방법; (나) P2-10의 task가 리뷰를 거쳐 정하는 설계: 결과의 기록 위치와 시간당 드라이버가 읽는 방법, 실패 이슈를 등록하는 주체·양식·중복 방지와 드라이버가 task로 받아들이는 이슈의 식별 기준, 실패 원인을 코드 결함과 환경으로 가르는 기준, 환경이 원인일 때 HQ의 사유·`taskId`와 그 이슈의 처리, 이슈가 task가 되는 방법(task 파일을 만드는 주체, §3-3·§6 가운데 바뀌는 본문)과 그 순서(PLAN 항목과의 우선순위), 실패 이슈를 닫는 시점, 고친 뒤의 nightly가 다시 실패할 때의 처리(같은 이슈의 재개 여부, 반복 상한과 그때 오너에게 올리는 방법), 시간당 드라이버와의 배타·측정 간섭 방지, nightly run의 기록을 사례 저장과 분리하는 방법 — 이 가운데 데이터 plane이나 `ARCHITECTURE/`에 닿는 것은 CLAUDE.md A-13의 BLOCKED 사유와 §9를 따른다** | §1-5, §6; CLAUDE.md; PLAN P2-5·P2-9·P2-10 |
| D18 | **우선순위와 도달 목표**([오너 2026-10-19, 채팅](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6280029924): planner가 P1-1·P1-8 주변의 하위 질문·입력 경화·문서 정리를 계속 만들어 10-14 이후 PLAN 체크가 닫히지 않고 P2가 시작되지 않았다; 통합자가 제안한 "우선순위 지시"를 오너가 받아들이며 목표를 바꿨다) | P2-5에 필요한 최소분 → **확정(오너 2026-10-19, 채팅): ① 우선순위 지시대로 진행 — 지시의 내용은 P1-1·P1-8에 완료 기준을 두고, 목표에 필요하지 않은 경화·문서 정리·리팩토링을 보류 목록으로 보내며, planner가 follow-up을 task로 만들기 전에 필요 여부를 판단하는 것(품질 규칙·오너 전용 결정·BLOCKED 사유는 그대로). ② 단 목표는 GEMM 하나가 아니라 1B급의 대중적인 오픈웨잇 LLM 하나를 end-to-end로 실행할 수 있는 수준이다 — 오너가 고른 것: 수준 = 연산별 커널로 모델 실행(그 커널들로 forward pass가 돌아 토큰을 생성하고 reference와 맞음; 그래프 수준 합성·fusion은 후속), 모델 = Llama 3.2 1B, 정밀도 = bf16/fp16. **Requirements C-6 개정과 OD-31(하위 질문과 그 귀속)로 반영했다. 통합자 적용(오너의 말이 아님): 도달 목표 P2-14와 가까운 목표 P2-5로 나눈 것, 보류를 푸는 시점을 P2-14 뒤로 둔 것(지시의 "P2-5 이후"를 바뀐 목표에 맞춤), P2-11~P2-15로 쪼갠 것, P1-1·P1-8 완료 기준의 나열, P2의 수행 순서(P2-8을 맨 뒤로), 규칙을 체크리스트 밖의 일에 한정하고 "판단이 서지 않으면 task로" 둔 것, 보류 줄을 상태 커밋으로 둔 것, 보류된 BLOCKED task를 HQ 답변 뒤에도 되돌리지 않고 그 밖의 체크리스트 밖 task는 되돌릴 때 같은 판단을 하는 것, 보류 줄을 planner가 아니라 드라이버가 쓰는 것, 이미 BLOCKED인 T-0225·T-0284·T-0286을 보류로 넣고 PR #179를 닫는 것과 보류되는 task의 열린 PR을 닫는 단계, 체크리스트 항목을 인용하는 일의 경계, C-6에서 instance 단위를 그대로 둔 독해, 이 목표를 MVP 범위(C-6) 안에 둔 독해(MVP 시나리오 계층은 OD-31 ⑩), #5 B-4 답변의 해당 줄이 대체된다는 독해 | §2, §3-2·§3-3·§3-4, §6; PLAN 머리말·P1-1·P1-8·P2·보류; Requirements C-6·OD-31; OpenDecisionProposals OD-31; StandardScenarios; `.claude/agents/dev-planner.md`; CLAUDE.md; README |
| D19 | **HQ의 기록·답변 경로**([오너 2026-10-21, 채팅](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6314880192): HQ가 모두 #5에 미러되어 #5가 비대해지고, HQ id를 언급한 코멘트가 답으로 읽힐 수 있다; A-A의 처리 방법을 따르도록 개선) | ① 경로: `PROCESS/STATE.json`만(A-A) / STATE.json + #5 한 줄 알림 · ② 미해결 HQ: 그 task만 막음 / 루프 전체 정지(A-A) / 답이 필요한 HQ만 전체 정지 · ③ 그 밖의 #5 게시: 유지 / 저장소 안으로 · ④ `question` 언어: 영어 / 한국어(A-A) → **확정(오너 2026-10-21, 채팅): ① HQ는 `PROCESS/STATE.json`에만 기록하고 #5에 미러하지 않으며, 오너가 `resolvedAt`·`decision`을 commit해 답한다(#5 답변 감지 폐지) ② 미해결 HQ는 그 task만 막는다(현행 유지) ③ §9의 OD 종결 통지 등 그 밖의 #5 게시는 현행 유지 ④ `question`은 한국어. 통합자 적용(오너의 말이 아님): 답 commit은 lock 중에도 허용하되 그 HQ 항목의 두 필드만 바꾸게 하고 §3-6 재적용 목록에 새 HQ 항목을 더한 것; task를 다시 하지 않는 답은 같은 commit에서 task를 `DONE`으로 바꾸게 한 것; 반영 판정을 `BLOCKED` task의 `hq`가 모두 답을 가졌고 열린 PR과 겹치지 않는 것으로 두고 `INTERRUPTED`는 되돌리지 않고 3단계에 맡긴 것; `question`의 구성(쟁점·선택지·막히는 것)과 journal 줄의 id, 오너가 journal에서도 질문을 읽는다는 것(A-A LOOP §5의 관행), 통합자 세션이 채팅의 답을 옮겨 적는 것; `issueComment` 필드를 스키마 변경 없이 새 HQ에서 null로 두는 것; 기존 미해결 HQ(영문 질문, #5 미러 있음)를 번역하지 않고 그대로 두며 그 답도 STATE.json으로만 받는 것; CLAUDE.md 세션 진입 점검에 미해결 HQ를 더한 것** | §1-5, §3-2·§3-4·§3-6, §4, §5, §6, §7, §8; CLAUDE.md; `.claude/agents/dev-planner.md`; proposals/D15 |
| D20 | **작업 단위 확대와 리뷰 nit 처리**([오너 2026-10-25, 채팅](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6397069546): 작업 단위를 키워 속도를 늘릴 방법을 분석하라 — 통합자 실측(10-22~24, task 55개): 코드 task 중앙값 24분·소스 194줄·리뷰 2라운드, ADR task는 전체의 31%·중앙값 리뷰 6라운드로 17개 중 8개가 7라운드 한도에 닿음, 연산 kind 하나가 ADR 1 + 코드 2~3 task) | 통합자 제안: ② 크기 상한 300 LOC·5 파일 → 600 LOC·10 파일, 한 ADR의 slice 합치기 · ③ (a) 같은 모양의 결정은 한 ADR로 (b) Approve 뒤 의미를 바꾸지 않는 Nit 수정은 재리뷰하지 않음, 리뷰어는 Nit만 남으면 Approve (c) ADR과 첫 코드 slice를 한 task로 · ④ planner가 task를 여러 개 한 번에 생성 → **확정(오너 2026-10-25, 채팅): 2~4를 제안대로 적용.** 통합자 적용(오너의 말이 아님): "함수 하나가 아니라 기능 하나"라는 단위 기준; ①을 코드 모드로 하고 ADR 파일을 PR에 함께 넣는 것과 ADR만 있는 task를 남기는 두 경우; ③의 상한 절반 미만 task를 인접 작업과 합치는 것; ④의 한 번 생성 상한 3개, "같은 PLAN 항목" 한정, `dependsOn`에 앞선 task를 모두 적고 3단계가 그것을 검사하는 것, 앞선 task가 BLOCKED·보류(뒤 task도 보류 절에 적고 `BLOCKED`)·결과 없는 DONE일 때의 처리, 미착지 결정에 좌우되는 task의 사전 생성 금지, 드라이버가 파일 모두를 §3-4 커밋에 넣고 첫 번째를 실행하는 것, 두 번째 task의 id를 `nextTask` 후보로 돌려주는 것; 크기 상한에 문서 줄을 세는 것; 리뷰 심각성 체계(Must-fix·Should-fix·Nit)와 각각의 판정, 판정의 명시, Nit의 정의(결정·동작·테스트·인터페이스의 의미를 바꾸지 않는 지적), Approve 뒤 반영하지 않은 Nit을 follow-up으로 만들지 않는 것. 리뷰 7라운드 한도·테스트 규칙(D12)·BLOCKED 사유·오너 전용 결정은 그대로 | 머리말 표기, §3-2·§3-3·§3-4, §5 크기 상한, §6 규칙·출력·"task 단위", §11 머리·D4 행, `.claude/agents/dev-planner.md`, `.claude/skills/dev-item-address/SKILL.md` 11·12단계, `.claude/skills/dev-code-review/SKILL.md` |

답변 경로(새 D-n이 생길 때): 오너가 #5 코멘트 또는 채팅으로 답하면 통합자(사람과 함께 일하는 세션)가 본 문서를 **문서 모드**로 갱신한다 — 본문에 확정값을 쓰고 ⚑를 제거하고 날짜를 남긴다. task 파일의 `hq: [D-n]`은 그때 비운다.
