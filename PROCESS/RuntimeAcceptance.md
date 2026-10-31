# 런타임 인수 체크리스트

[DRIVER.md](DRIVER.md) D22(오너 2026-10-26, 채팅)의 기록 자리. **런타임 인수 항목**은 실제 Claude Code 세션(로그인된 `claude`)이나 개발 머신에 없는 보드·가속기가 있어야만 확인되는 사실이다(CLAUDE.md "개발 드라이버와 런타임의 구분", DRIVER D16). 지금까지의 관행대로 C-7 머신의 컨테이너 런타임 위에서만 확인되는 사실도 포함한다(D22 통합자 적용). 드라이버 task로는 닫히지 않고, 오너가 런타임 머신에서 직접 확인하거나 런타임 자체 점검 코드가 확인해야 닫힌다. nightly end-to-end 루틴(D17)의 결과는 회귀 신호일 뿐 항목을 닫지 않는다. 드라이버의 테스트 run(D25)의 결과도 정해질 때까지 항목을 닫지 않는다.

- **더하기**: 드라이버는 planner·executor가 돌려준 런타임 인수 항목(task의 `Result`나 land된 ADR이 적은 것)을 HQ로 올리지 않는다. 대신 그 상태 커밋(§3-4·§3-6)에서 이 파일 끝에 항목 하나로 더한다. 항목 하나는 한 task(또는 한 PLAN 항목)가 남긴 인수 항목 묶음이며, 같은 출처의 항목이 이미 있으면 다시 더하지 않는다. id는 `RA-NNNN`으로 이어 붙이고, `출처`에 task와 ADR(task 없이 planner가 돌려준 항목은 PLAN 항목 id, 예: `P2-9`; 근거가 된 task가 있으면 출처 줄 괄호에 적는다)을 적고, `내용`에는 확인할 사실과 확인이 가능해지는 조건(어느 code slice가 land된 뒤인지)을 적는다. push가 거부되어 rebase할 때 이 파일이 충돌하면, origin 쪽을 취하고, 자기 항목의 id를 origin의 마지막 id 다음 번호로 다시 매겨 끝에 더한다.
- **닫기**: 오너(또는 오너의 통합자 세션)가 확인한 뒤 `상태`를 바꿔 main에 commit한다. 드라이버는 `상태`를 바꾸지 않는다. 상태 값은 다음 셋이다.
  - `미확인`
  - `확인됨 (YYYY-MM-DD, 머신 종류)`
  - `실패 (YYYY-MM-DD, 관찰 한 줄)`
- **실패**: `실패` 항목은 planner의 입력이다. planner는 그것을 고칠 일로 다루며, task로 만드는 순서는 PLAN과 DRIVER §6의 우선순위(D18)를 따른다. 고치는 task는 그 RA id와 `실패` 값(괄호 안 전체)을 Why에 적고(D18로 보류되면 보류 줄에도 적는다), planner는 같은 id·같은 값을 적은 task나 보류 줄이 이미 있으면 그 항목을 다시 다루지 않는다. 고친 것이 land되면 오너가 다시 확인해 `상태`를 바꾸며, 다시 실패하면 새 관찰을 적은 `실패`가 되어(같은 날이면 관찰 줄로 구별한다) planner가 다시 다룬다.
- **ADR**: 런타임 인수 항목을 남기는 새 ADR은 그 항목을 이 파일로 넘긴다고 적는다. D22 전의 ADR에 있는 "DRIVER §8, reason `runtime-acceptance`"는 이 파일을 뜻하는 것으로 읽는다.
- **이관**: D22 전에 HQ(사유 `runtime-acceptance`)로 기록된 미해결 항목은 아래 RA-0001부터 원문 그대로 옮겼고, 그 HQ는 `PROCESS/STATE.json`에서 이 파일의 id를 가리키며 닫혔다. 원문이 가리키는 "your check by hand"는 오너의 수동 확인이다.

## 항목

### RA-0001

- 상태: 미확인
- 출처: HQ-0013에서 이관 (task T-0121, 등록 2026-10-13, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6137374764))
- 내용(HQ 원문 그대로):

  ADR-0049 (the isolation means of one coder call for the first case, T-0121, main 1646654) rests on facts that only a live Claude Code session and a container runtime on a machine of C-7 can confirm; under D16 they are runtime acceptance items, closed by your check by hand or by the runtime's own self-check, not by a driver task. On each kind of machine of C-7: (1) a `claude -p` call runs inside a container whose only writable host path is the scratch directory of the call; (2) after a call in which the coder tried to change files of both checkouts, neither checkout has changed; (3) the scratch can be removed afterwards by the user who runs the instance; (4) the container can reach Anthropic. Nothing of this was tried, and nothing was required of the development machine. No task is blocked on this notice.

### RA-0002

- 상태: 미확인
- 출처: HQ-0014에서 이관 (task T-0149, 등록 2026-10-13, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6139794125))
- 내용(HQ 원문 그대로):

  ADR-0052 (the memory figure behind `memory_ceiling` on `cpu_standin`, T-0149, main 08ccb21) rests on facts about what an operating system reports for an ended process that only a run on a machine of C-7 can confirm; under D16 they are runtime acceptance items, closed by your check by hand or by the runtime's own self-check, not by a driver task. On each kind of machine of C-7 (Linux, macOS, Windows with WSL 1 and WSL 2): (1) the wait for an ended timing run returns a positive `ru_maxrss` in the unit the record states - KiB on Linux and WSL, bytes on macOS (if macOS reported kilobytes, a candidate over its ceiling would be called within); (2) for a kernel that allocates nothing, how far the figure lies above the size of the operands; (3) on Linux and WSL, the size of the floor that comes from the Python process that starts the run, and whether it differs between two starts; (4) whether the usage returned for a timing run takes in a descendant process the run did or did not wait for. Nothing of this was tried, and nothing was required of the development machine. No task is blocked on this notice.

### RA-0003

- 상태: 미확인
- 출처: HQ-0016에서 이관 (task T-0153, 등록 2026-10-13, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6146444000))
- 내용(HQ 원문 그대로):

  ADR-0054 (the design record of the runtime self-check, PLAN P1-9; T-0153, main a5ed142) rests on facts that only a real, logged-in `claude` on a machine of C-7 can confirm; under D16 they are runtime acceptance items, closed by your check by hand or by the first runs of the self-check once its code exists, not by a driver task. On each kind of machine of C-7: (1) `claude auth status` exits 0 or 1 as the CLI reference says and its output is one JSON object with `authMethod`; (2) a `-p` session started with `--setting-sources project` from an empty directory still reads the stored login, and no managed setting changes what the check assumes; (3) with `--tools ""` and tool search at its default the model can call an MCP tool named in `--allowedTools`; (4) in `--permission-mode dontAsk` a call of a listed MCP tool runs without a prompt; (5) the `system/init` event of `--output-format stream-json` carries `mcp_servers` (name, status), `mcp_server_errors` and the tool names, which words `status` takes, which member of the last `result` message holds the final response text, and that the exit status tells a failed session from one that ended well; (6) the session ends by itself after the reply and leaves no file outside the check's directory; (7) the server process started from a working directory outside the checkout finds the `hilclaw` package; (8) Claude Code shows nothing of the configuration file's server entry (its `env` above all) to the model. Nothing of this was tried, and nothing was required of the development machine. No task is blocked on this notice.

### RA-0004

- 상태: 미확인
- 출처: HQ-0017에서 이관 (task T-0155, 등록 2026-10-13, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6147779708))
- 내용(HQ 원문 그대로):

  ADR-0055 (the files and form of `output/` of a coder call for the first case, part of OD-23; T-0155, main a239b6f) fixes the form of `output/` from documents alone. Two facts it rests on can only be established with a real coder call in a container on a runtime machine; under D16 they are runtime acceptance items, closed by your check by hand or by the first runs of the runtime once the coder-driver exists, not by a driver task. On each kind of machine of C-7: (1) the regular files a coder wrote into the directory `output` below the root of its scratch, from inside its container, can be read after the container is removed by the user who runs the instance (ADR-0049 L6 asks the same of their removal); (2) a coder that is told the place and the admitted names - by whatever PLAN P2-2 decides - leaves there a kernel source that the bring-in takes whole. They are separate from the items of HQ-0013 (ADR-0049). Nothing of this was tried, and nothing was required of the development machine. No task is blocked on this notice.

### RA-0005

- 상태: 미확인
- 출처: HQ-0018에서 이관 (task T-0156, 등록 2026-10-13, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6148899981))
- 내용(HQ 원문 그대로):

  ADR-0056 (how `correctness.check` comes to the verification executable of an attempt for the first case, part of OD-18 sub-question 10; T-0156, main 3336cee) has the operation of `cpu_standin` build the verification executable at each call in a build directory of its own, outside both checkouts, and remove it before the call returns. One fact it rests on can only be established on a runtime machine; under D16 it is a runtime acceptance item, closed by your check by hand or by the first runs of the runtime once the operation exists, not by a driver task. On each kind of machine of C-7 (Linux, macOS, Windows with WSL): the place the code chooses for the build directory lets the user who runs the instance make a directory there, start an executable that was built into it (a location for temporary files may be set up so that nothing in it can be executed - the record's expectation, not verified), and remove it. A test with clang in CI can show it for the CI machine only. Nothing of this was tried, and nothing was required of the development machine. No task is blocked on this notice.

### RA-0006

- 상태: 미확인
- 출처: HQ-0019에서 이관 (task T-0169, 등록 2026-10-14, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6160644223))
- 내용(HQ 원문 그대로):

  ADR-0057 (the runtime self-check as landed, OD-18; T-0169, main fc74780) adopts values the landed check (`hilclaw/selfcheck*.py`) took provisionally. On each kind of machine of C-7, only a real logged-in `claude` can show: (ix) the configuration file wraps server entries in `mcpServers`, and an entry needs only `command`/`args`/`env`; (x) `--allowedTools` takes both MCP names as one comma-joined argument; (xi) `--mcp-config selfcheck.mcp.json` (file name only) is read against the session's working directory; (xii) the stream names `type`/`subtype` with `system`/`init`, `type` `result`, and the reply member `result`, and a session writes exactly one `system/init` event and still writes `mcp_servers` when it drops a server; (xiii) a real session ends within 300 s and `claude auth status` within 30 s; (xiv) on Windows the empty `--tools` argument and the comma pass through `claude.cmd` unchanged; (xv) whether Claude Code forwards a `tools/call` of a name the server did not list. Under D16 these are runtime acceptance items, closed by your check by hand or by the first runs of the self-check, not by a driver task. ADR-0054's items (i)-(viii) stay under HQ-0016. Nothing was tried; no task is blocked on this notice.

### RA-0007

- 상태: 미확인
- 출처: HQ-0030에서 이관 (task T-0302, 등록 2026-10-18, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6248397499))
- 내용(HQ 원문 그대로):

  ADR-0103 (how a measurement or a run is found to be taken in an imprecise timing environment, OD-13 sub-question 11 (ga); T-0302, main 274fed8) has two grounds, either one sufficient: a measured ground (`not_converged`, or clock resolution above `resolution_share_max` = 1 % of the shortest interval) and a class ground (the timing run executed as a VM guest). Its Limit 2 rests on facts that only a run on a machine of C-7 can confirm; under D16 they are runtime acceptance items, closed by your check by hand or by the runtime's own self-check, not by a driver task: (1) whether and how a process in the Docker Desktop VM on macOS or Windows, or under WSL 2, can tell that it is a VM guest; (2) what CV and resolution timing runs show there and in a container on native Linux; (3) that WSL 2 runs its kernel in a VM; (4) that VM distortion shows mainly as additive overhead or drift, not in the CV of one measurement. Nothing was tried; no task is blocked on this notice.

### RA-0008

- 상태: 미확인
- 출처: HQ-0033에서 이관 (task T-0325, 등록 2026-10-19, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6258750066))
- 내용(HQ 원문 그대로):

  ADR-0116 (source and first values of the cpu_standin build settings, OD-18 sub-questions 18 (ra) and 19 (ra); T-0325, main 2ca335c) fixes flags `-std=gnu11 -O2 -ffp-contract=off` and trailing flags `-lm`. Under D16 it is a runtime acceptance item, closed by your check by hand or by the runtime's own self-check, not by a driver task: that the clang of each C-7 system the development machine and CI do not have (macOS with its default clang among them) accepts these flags with the outcomes ADR-0116 decision 3 and Limit 4 describe. Nothing was tried; no task is blocked on this notice.

### RA-0009

- 상태: 미확인
- 출처: HQ-0035에서 이관 (task T-0329, 등록 2026-10-19, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6260601350))
- 내용(HQ 원문 그대로):

  ADR-0118 (round boundary of a first-case run, OD-18 round boundary, #8 M4, one point of OD-23; T-0329, main a2d9e96) decides that one turn is one Claude Code session process started by a layer-2 turn loop, running in a session directory outside both checkouts, with the runtime definition copied in from `orchestration/` at every turn and the server given by `--mcp-config` + `--strict-mcp-config`. Under D16 these are runtime acceptance items, closed by your check by hand or by the runtime's own self-check, not by a driver task: (i) what a `-p` session in the session directory loads, and that it loads nothing of this repo; (ii) what it loads from the runtime user's `~/.claude/`, and what the chosen flags exclude; (iii) a sub-agent in the session directory's `.claude/agents/` is found and used; (iv) `--mcp-config`/`--strict-mcp-config` gives the server to every turn's main session, the server finds the package, sub-agents inherit its tools, and whether inline `mcpServers` survives `--strict-mcp-config` in a trusted directory; (v) a `-p` turn session exits after its last reply; (vi) the exit status separates success from failure; (vii) the later permission/allowlist means work under workspace trust. Nothing was tried; no task is blocked on this notice.

### RA-0010

- 상태: 미확인
- 출처: HQ-0036에서 이관 (task T-0337, 등록 2026-10-19, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6264739892))
- 내용(HQ 원문 그대로):

  ADR-0122 (what the turn loop of a first-case run does where its step 1 is open: it returns instead of starting another turn after a failed turn, after a turn with no progress, and in ADR-0121's open states; part of OD-19 and the OD-17 remainder; T-0337, main 8ea7115) adds one runtime acceptance item to ADR-0118's (i)-(vii) of HQ-0035. Under D16 it is closed by your check by hand or by the runtime's own self-check, not by a driver task: (viii) how a `-p` turn session that reaches the plan's usage limit ends - its exit status, and whether anything in its output tells it from another failure. ADR-0122 does not rely on it; a later record that defines the usage-limit pause would. Nothing was tried; no task is blocked on this notice.

### RA-0011

- 상태: 미확인
- 출처: HQ-0037에서 이관 (task T-0339, 등록 2026-10-19, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6266315890))
- 내용(HQ 원문 그대로):

  ADR-0123 (how a first-case turn session learns which run it carries: the command-line entry hilclaw.turn_start puts the run id into the prompt of every turn and hands the session no place of the run; part of OD-18 and OD-23; T-0339, main 2f49767) adds one runtime acceptance item to ADR-0118's (i)-(vii) of HQ-0035 and ADR-0122's (viii) of HQ-0036. Under D16 it is closed by your check by hand or by the runtime's own self-check, not by a driver task: (ix) a `-p` turn session started by the loop with the prompt the entry builds receives that text unchanged as its first user message - on Windows also where the `claude` found is a command script - and its Round-Manager takes the run id from it as the definition says. Nothing was tried; no task is blocked on this notice.

### RA-0012

- 상태: 미확인
- 출처: HQ-0038에서 이관 (task T-0341, 등록 2026-10-19, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6267838692))
- 내용(HQ 원문 그대로):

  ADR-0124 (how the Round-Manager of a first-case turn reads its run's STATE.json and instance.json and reaches hilclaw.run_state_file.replace: four registry tools state.read, instance.read, run.fresh and state.write of the hilclaw MCP server, called with run_id; part of OD-23 and OD-18; T-0341, main 6de1c68) adds two runtime acceptance items after ADR-0123's (ix) of HQ-0037. Under D16 they are closed by your check by hand or by the runtime's own self-check, not by a driver task: (x) the main session of a `-p` turn session started by the turn loop sees the four tools under the MCP names `mcp__hilclaw__state_read`, `mcp__hilclaw__instance_read`, `mcp__hilclaw__run_fresh` and `mcp__hilclaw__state_write` (whether it may call them without a prompt stays ADR-0118 item (vii)); (xi) the results of `state.read` and `instance.read` reach the Round-Manager whole, within the limit Claude Code puts on the output of an MCP tool. Best checked after the code slice of ADR-0124 lands.

### RA-0013

- 상태: 미확인
- 출처: HQ-0039에서 이관 (task T-0343, 등록 2026-10-19, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6270160894))
- 내용(HQ 원문 그대로):

  ADR-0125 (where the runtime self-check runs for a first-case run: hilclaw.turn_start runs hilclaw.selfcheck.check() once per start, after the first step 1 finds a turn due and before the first turn session; passed and no_call let the turn start, every other result and a fault of the check stop the start; part of OD-18 sub-question 16 (ga); T-0343, main 393bcd8) adds one runtime acceptance item to the self-check series. Under D16 it is closed by your check by hand or by the runtime's own self-check, not by a driver task: (xvi) what `claude auth status` reports for a stored login that has expired and cannot be refreshed: exit status 1 (`not_logged_in`), or 0 with an `authMethod` (the session then ends `session_failed`). Best checked after the code slice of ADR-0125 lands.

### RA-0014

- 상태: 미확인
- 출처: HQ-0042에서 이관 (task T-0346, 등록 2026-10-19, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6273055239))
- 내용(HQ 원문 그대로):

  ADR-0126 (main a5de4f6; part of OD-23; T-0346) adds runtime acceptance items (xii)-(xiv) to the turn-session series. Under D16 they are closed by your check by hand or by the runtime's own self-check, not by a driver task. (xii) A `coder-driver` sub-agent of a `-p` turn session can request the coder call in the form HQ-0040 gives (the entry through Bash, found from the session directory, or `mcp__hilclaw__coder_run`) without a permission prompt. (xiii) How long a first-case coder call takes, against that form's limit (foreground Bash: 2 min by default, 10 min ceiling; MCP idle window about 30 min) and the session's own limits, and whether a cut-off request leaves the function, the container or the coder running. (xiv) The exit status of the coder's `claude -p` inside the container tells a normal end from an abnormal one. Best checked after the code slices land. Nothing was tried.

### RA-0015

- 상태: 미확인
- 출처: HQ-0044에서 이관 (task T-0348, 등록 2026-10-19, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6275240712))
- 내용(HQ 원문 그대로):

  ADR-0127 (part of OD-8 sub-question 11; T-0348, main e9f16a0) adds turn-session runtime acceptance items (xv)-(xvii): (xv) the main session of a -p turn session sees mcp__hilclaw__run_commit and may call it under the permission means of item (vii); (xvi) the MCP server process of a turn session finds git and an author identity to commit in the data checkout; (xvii) a live Round-Manager calls run.commit as the first step of its entry and right after the write that ends its round. Under D16 closed by the owner's check by hand or the runtime's own self-check. Non-blocking.

### RA-0016

- 상태: 미확인
- 출처: HQ-0045에서 이관 (task T-0352, 등록 2026-10-19, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6278149061))
- 내용(HQ 원문 그대로):

  ADR-0128 (the evaluator of a first-case turn, part of OD-23 and OD-16; T-0352, main 3cb52c6) adds turn-session runtime acceptance items (xviii)-(xx): (xviii) a sub-agent of a -p turn session defined in .claude/agents/evaluator.md gets exactly the tools its tools list names, the hilclaw tools given by --mcp-config among them, and no Write, Edit, Bash or other unlisted tool; (xix) the Round-Manager's delegation message reaches the evaluator whole, and the evaluator's final message reaches the Round-Manager whole; (xx) a correctness.check called from a sub-agent through MCP returns within the MCP idle window (about 30 minutes) for the largest first-case check ADR-0117's limits allow, and a call cut off there leaves no check running. Under D16 closed by the owner's check by hand or the runtime's own self-check. Non-blocking.

### RA-0017

- 상태: 미확인
- 출처: HQ-0046에서 이관 (task T-0355, 등록 2026-10-20, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6280171707))
- 내용(HQ 원문 그대로):

  ADR-0129 (the evaluator reads a round's hypotheses.json through the registry tool hypotheses.read, part of OD-23 and OD-18; T-0355, main fdc9664) adds turn-session runtime acceptance item (xxi): the result of hypotheses.read reaches the evaluator sub-agent of a -p turn session whole, within the limit Claude Code puts on the output of an MCP tool, for the largest hypothesis record a first-case round can hold. Under D16 closed by the owner's check by hand or the runtime's own self-check. Non-blocking.

### RA-0018

- 상태: 미확인
- 출처: HQ-0047에서 이관 (task T-0357, 등록 2026-10-20, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6282186768))
- 내용(HQ 원문 그대로):

  ADR-0131 (the evaluator reads an attempt's journaled check results through the registry tool checks.read, and is given the verdicts work with every verdict inconclusive until the comparison exists; part of OD-23 and OD-18; T-0357, main 9e29340) adds turn-session runtime acceptance item (xxii): the result of checks.read reaches the evaluator sub-agent of a -p turn session whole, within the limit Claude Code puts on the output of an MCP tool, for the largest set of checks of one candidate at one point that a first-case run can hold. Under D16 closed by the owner's check by hand or the runtime's own self-check. Non-blocking.

### RA-0019

- 상태: 미확인
- 출처: HQ-0049에서 이관 (task T-0362, 등록 2026-10-20, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6285364638))
- 내용(HQ 원문 그대로):

  ADR-0133 (the case write of a first-case round's promotion step, part of OD-23 and OD-30; T-0362, main 67b6d6a) adds turn-session runtime acceptance items (xxv) the main session of a -p turn session sees mcp__hilclaw__case_write and may call it under the permission means of item (vii), and (xxvi) a live Round-Manager calls case.write once per round >= 1, after the round's verdicts work and before the write that ends the round, and goes on to that write after a failure. Under D16 closed by the owner's check by hand or the runtime's own self-check. Non-blocking.

### RA-0020

- 상태: 미확인
- 출처: HQ-0050에서 이관 (task T-0364, 등록 2026-10-20, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6287157613))
- 내용(HQ 원문 그대로):

  ADR-0134 (who stores the two key record files of a first-case run, part of OD-26 and OD-23; T-0364, main 961dbfd) adds turn-session runtime acceptance items (xxvii) the main session of a -p turn session sees mcp__hilclaw__key_store and may call it under the permission means of item (vii), and (xxviii) a live Round-Manager calls key.store as the first round step of each turn that carries a round, before any other step of it, and goes on after a failure. Under D16 closed by the owner's check by hand or the runtime's own self-check. Non-blocking.

### RA-0021

- 상태: 미확인
- 출처: HQ-0051에서 이관 (task T-0368, 등록 2026-10-20, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6290432080))
- 내용(HQ 원문 그대로):

  ADR-0135 (the write that ends a first-case round, part of OD-23; T-0368, main 0d5a3ba) adds turn-session runtime acceptance items (xxix) the main session of a -p turn session sees mcp__hilclaw__round_end and may call it under the means item (vii) gets, and (xxx) a live Round-Manager calls round.end once per round, as the round's last write before run.commit, and after a failure reports the kind and ends the session without another write. Under D16 closed by the owner's check by hand or the runtime's own self-check. Non-blocking.

### RA-0022

- 상태: 미확인
- 출처: HQ-0052에서 이관 (task T-0371, 등록 2026-10-20, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6296309336))
- 내용(HQ 원문 그대로):

  ADR-0136 (the model of a first-case coder call, owner answer HQ-0041 part 1; part of OD-8 and OD-23; T-0371, main 4423c35) adds runtime acceptance items (xxxi) the coder's `claude -p` inside the container, given the recorded full model name (`coder_model`, default `claude-opus-5-5`), runs on that model under the user's Max plan, and the model it actually ran on (after any remapping or content-based fallback) can be read back, e.g. from `modelUsage`; and (xxxii) what the coder's `claude -p` does when the recorded full name is no longer offered under the plan or is remapped: exits non-zero, runs another model, or warns, and whether its output tells which. Under D16 they are closed by your check by hand or by the runtime's own self-check, not by a driver task; nothing is blocked.

### RA-0023

- 상태: 미확인
- 출처: HQ-0054에서 이관 (task T-0376, 등록 2026-10-20, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6301665057))
- 내용(HQ 원문 그대로):

  ADR-0138 (the spec of a first-case round-0 bring-up coder call, written before the call through the new registry tool `spec.write`; rest of OD-6, part of OD-23; T-0376, main acb6801) adds runtime acceptance item (xxxiii): a `coder-driver` sub-agent of a `-p` turn session can call `mcp__hilclaw__spec_write` without a permission prompt, under whatever permission means item (vii) gets, whichever form HQ-0040 gives the call. Under D16 it is closed by your check by hand or by the runtime's own self-check, not by a driver task; nothing is blocked. Note: the unlanded T-0375 draft (HQ-0053) also numbers its first item (xxxiii); whichever lands later renumbers.

### RA-0024

- 상태: 미확인
- 출처: HQ-0055에서 이관 (task T-0378, 등록 2026-10-20, [#5 미러](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6303635446))
- 내용(HQ 원문 그대로):

  ADR-0139 (the permissions of a first-case `-p` turn session: `--permission-mode dontAsk`, an exact `--allowedTools` list derived from the Round-Manager's fixed list and the agent files, `--tools` closed to `Agent` plus `Read`/`Grep`/`Glob`, `--setting-sources project`, no bypass flag; part of OD-18 and OD-23; T-0378, main 930e7eb) gives ADR-0118 item (vii) its means and adds runtime acceptance items (xxxiv)-(xl): the flags take effect in a never-trusted session directory; pre-approved `mcp__hilclaw__` calls run without a prompt and unlisted ones are denied without a wait; `--tools` leaves no other command-running or file-writing built-in and `hilclaw` tools stay reachable; a sub-agent with no `permissionMode` runs in `dontAsk` with its listed tools; `Agent(evaluator)` allows the delegation and the list survives a Windows command script; bare `Read`/`Grep`/`Glob` read outside the working directories without a prompt; under `--setting-sources project` nothing of `~/.claude/settings.json` acts on the session while the session directory's `.claude/settings.json` is read. Under D16 they are closed by your check by hand or by the runtime's own self-check, not by a driver task; nothing is blocked. Note: the unlanded T-0375 draft (HQ-0053) uses numbers from (xxxiii); whichever lands later renumbers.

### RA-0025

- 상태: 미확인
- 출처: HQ-0056에서 이관 (task T-0384, 등록 2026-10-21)
- 내용(HQ 원문 그대로):

  ADR-0141(첫 사례 턴의 등록표 도구 `coder.run`; OD-23·OD-18 일부; T-0384, main 3815c42)이 런타임 인수 항목 (xli)~(xliii)을 더했다. (xli) `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT=0`인 `-p` 턴 세션에서 coder-driver의 `coder.run` 호출이 30분 넘게 조용해도 중단되지 않는가(관리 설정이 이 변수를 정하지 않고 (xl)이 성립한다는 전제). (xlii) `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`(그리고 `CLAUDE_AUTO_BACKGROUND_TASKS` 제거)에서 coder-driver 위임이 전경에서 돌아 같은 턴에 보고하고, sub-agent stall 타이머(`CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS`)가 호출 대기 중인 coder-driver를 중단하지 않는가. (xliii) 단일 스레드 front가 긴 호출을 처리하는 동안 세션이 `ping` 같은 다른 요청 때문에 그 호출을 중단하거나 서버를 실패로 보지 않는가. ADR-0126 (xii)·(xiii)은 좁혀졌다. 선택지: (a) 오너가 손으로 확인 (b) 런타임 자체 점검 코드(P1-9 계열)로 확인 (c) 보류. D16에 따라 드라이버 task로는 닫지 않는다. 막히는 것: 없음(T-0384는 DONE; 코드 slice 1~4는 스텁으로 진행 가능). 실패로 드러나면 ADR-0141의 결정 3(긴 호출 유지 방법)을 다시 정해야 한다.

### RA-0026

- 상태: 미확인
- 출처: HQ-0057에서 이관 (task T-0389, 등록 2026-10-21)
- 내용(HQ 원문 그대로):

  ADR-0142(라운드 0의 coder 호출 뒤 단계; OD-23 일부; T-0389, main cd4879b)가 런타임 인수 항목 (xliv)~(xlvi)을 더했다. (xliv) `-p` 턴 세션에서 `.claude/agents/experiment-runner.md`로 정의되고 `tools`가 정확히 `mcp__hilclaw__board_run`인 sub-agent가 그 도구만 받고, 파생 목록의 사전 승인으로 `dontAsk`에서 prompt 없이 호출되는가. (xlv) 한 라운드 0 턴 세션에서 네 번의 foreground 위임(coder-driver, evaluator 두 번, experiment-runner)이 같은 턴에서 순서대로 보고를 돌려주고, 세션 자체의 한계로 끝나기 전에 `round.end`와 `run.commit`에 이르는가. (xlvi) ADR-0117의 한계가 허용하는 가장 큰 first-case timing run의 `board.run` 호출이 ADR-0141 결정 4의 환경에서 idle 점검이나 sub-agent stall 타이머로 중단되지 않고, 세션이 끝날 때 남아 돌지 않는가. 선택지: (a) 오너가 수동 확인 (b) 런타임 자체 점검 코드(P1-9 계열)로 확인 (c) 보류. D16에 따라 드라이버 task로는 닫지 않는다. 막히는 것: 없음(T-0389는 DONE; 코드 slice는 계속 진행). 막히지 않는 것: ADR-0142 코드 slice 1(round-manager.md step 3·4). 실패로 드러나면 ADR-0142 결정 4(experiment-runner의 단일 호출)와 (xlv)의 위임 순서를 다시 정해야 한다.

### RA-0027

- 상태: 미확인
- 출처: HQ-0058에서 이관 (task T-0391, 등록 2026-10-21)
- 내용(HQ 원문 그대로):

  ADR-0143(라운드를 끝내지 않는 첫 사례 턴 끝의 commit; OD-8 ⑪ 일부; T-0391, main a3eb31c)이 런타임 인수 항목 (xlvii)을 더했다. (xlvii) 살아 있는 Round-Manager가 진입 0단계가 성공한 뒤의 모든 세션 종료 직전(stop, 세션을 끝내는 진입 단계, 실패한 `round.end`)에 마지막 행동으로 `run.commit`을 부르고, 그 호출이 실패한 뒤에는 다시 부르지 않는가. 선택지: (a) 오너가 수동 확인 (b) 런타임 자체 점검 코드(P1-9 계열)로 확인 (c) 보류. D16에 따라 드라이버 task로는 닫지 않는다. 막히는 것: 없음(T-0391은 DONE). 막히지 않는 것: ADR-0143 코드 slice (1)~(3). 실패로 드러나면 결정 2(모든 종료 전 호출)를 다시 정해야 한다.

### RA-0028

- 상태: 미확인
- 출처: HQ-0059에서 이관 (task T-0395, 등록 2026-10-21)
- 내용(HQ 원문 그대로):

  ADR-0144(첫 사례의 cpu_standin 빌드·프로세스를 담는 컨테이너; OD-14 하위 질문 ① 일부; T-0395, main bba593f)가 런타임 인수 항목 (xlviii)~(lii)를 남겼다 — C-7의 각 머신 종류에서 Docker로, 코드 slice가 착지한 뒤 확인한다. (xlviii) 클라이언트가 닿는 daemon이 그 operation을 돌리는 머신의 것인가, 빌드 디렉토리를 컨테이너에 줄 수 있는가(Docker Desktop은 VM 경유), 그것이 컨테이너 안에서 쓸 수 있는 유일한 호스트 경로이고 어느 checkout의 경로도 보이지 않는가. (xlix) 안의 프로세스가 호스트·LAN·인터넷의 어떤 주소에도 닿지 않는가. (l) 안의 프로세스가 빌드 디렉토리에 다른 사용자·그룹 소유 파일, 그런 소유자의 setuid/setgid 파일, device node를 만들 수 없는가; 시간 상한에서 강제 제거한 뒤 그 빌드·프로세스의 프로세스가 남지 않고 컨테이너가 뒤늦게 만들어지지 않는가; 그 뒤 instance를 돌리는 사용자가 빌드 디렉토리를 지울 수 있는가. (li) 컨테이너 시작·제거가 빌드·프로세스에 수 초 이하만 더하는가, pull policy `never`가 없는 이미지를 pull 없이 오류로 만드는가. (lii) 클라이언트가 컴파일러·프로그램의 exit status와 출력 바이트를 바꾸지 않고 넘기는가, 클라이언트가 스스로 더하는 status와 텍스트는 무엇인가. 선택지: (a) 오너가 수동 확인 (b) 런타임 자체 점검 코드(P1-9 계열)로 확인 (c) 보류. D16에 따라 드라이버 task로는 닫지 않는다. 막히는 것: 없음(T-0395는 DONE; 코드 slice도 막히지 않음). 막히지 않는 것: ADR-0144 코드 slice (1)~(4). 실패로 드러나면 ADR-0144 결정 2·3(호스트 경로 하나, 클라이언트 경유 시작)을 다시 봐야 한다.

### RA-0029

- 상태: 미확인
- 출처: HQ-0060에서 이관 (task T-0399, 등록 2026-10-22)
- 내용(HQ 원문 그대로):

  ADR-0145(ADR-0144 컨테이너 안에서 첫 사례 cpu_standin 타이밍 run의 타이밍·메모리 수치를 얻는 방법; OD-14 하위 질문 ① (마)의 측정 절반; T-0399, main a0601f4)가 런타임 인수 항목 (liii)~(lv)를 남겼다 — C-7의 각 머신 종류에서 Docker로, waiter 코드 slice가 착지한 뒤 확인한다. (liii) waiter가 init 없는 새 PID namespace의 PID 1인가; dumpable을 끈 뒤 같은 사용자의 프로세스가 시그널로 끝내거나 /proc의 디스크립터·메모리를 열 수 없는가; W4 뒤 다른 프로세스가 남지 않는가; 클라이언트가 타이밍 프로세스의 모든 바이트 뒤에 waiter의 마지막 줄을 넘기는가. (liv) native Linux, macOS·Windows의 Docker Desktop, WSL에서 waiter가 KiB 단위의 양수 ru_maxrss를 돌려주는가; 그곳의 바닥값과 하네스 몫의 크기. (lv) 타이밍 빌드와 waiter 빌드가 합쳐 수 초 안에 끝나 B_t(60 s)에 드는가. 선택지: (a) 오너가 수동 확인 (b) 런타임 자체 점검 코드(P1-9 계열)로 확인 (c) 보류. D16에 따라 드라이버 task로는 닫지 않는다. 막히는 것: 없음(T-0399는 DONE; 코드 slice (5)·(6)도 막히지 않음). 막히지 않는 것: ADR-0145 코드 slice. 실패로 드러나면 ADR-0145 결정(waiter를 PID 1로 두는 방식, ru_maxrss 단위 규칙, B_t 공유)을 다시 봐야 한다.

### RA-0030

- 상태: 미확인
- 출처: HQ-0061에서 이관 (task T-0402, 등록 2026-10-22)
- 내용(HQ 원문 그대로):

  ADR-0146(첫 사례 턴 세션의 호출자 점검 hook — PreToolUse hook이 hilclaw 도구를 그 도구를 가질 의도가 없는 호출자로부터 거부; OD-18 일부; T-0402, main a368b11)가 런타임 인수 항목 (lvi)~(lx)를 남겼다 — hook 코드 slice 1·2가 착지한 뒤 런타임 머신에서 확인한다. (lvi) 신뢰된 적 없는 세션 디렉토리에서 ADR-0139 결정 8의 명령줄(--setting-sources project 포함)로 시작한 -p 턴 세션이 루프가 쓴 .claude/settings.json의 PreToolUse hook을 main 세션과 각 sub-agent의 모든 mcp__hilclaw__ 호출에 대해 실행하고 내장 도구에는 실행하지 않는가; hook 환경의 CLAUDE_PROJECT_DIR가 세션 디렉토리인가. (lvii) main 세션 호출의 hook 입력에 agent_id·agent_type이 없고 custom sub-agent 호출에는 둘 다 있으며 agent_type이 frontmatter name과 같은가. (lviii) exit 2가 호출을 멈추고 모델이 그 줄을 거부로 읽으며 세션이 기다리지 않고 계속되는가; 출력 없는 exit 0이 dontAsk와 사전 승인 목록에 맡기는가. (lix) 사용 중인 Claude Code 버전이 onFailure: "block"(v2.1.295 이상)과 exec 형식을 따르는가; command의 sys.executable 절대 경로가 PATH 검색 없이 실행되고 Windows에서 시작 텍스트가 그대로 닿는가. (lx) 런타임 머신에서 managed 설정(allowManagedHooksOnly, disableAllHooks)이 hook을 막지 않고, 설치된 mod가 hook이 막은 호출을 승인하지 않는가. 선택지: (a) 오너가 수동 확인 (b) 런타임 자체 점검 코드(P1-9 계열)로 확인 (c) 보류. D16에 따라 드라이버 task로는 닫지 않는다. 막히는 것: 없음(T-0402는 DONE; ADR-0146 코드 slice 1·2도 막히지 않음). 막히지 않는 것: ADR-0146 코드 slice. 실패로 드러나면 ADR-0146 결정(hook 위치, 호출자 판별 방식, 판별 불가 시 동작)을 다시 봐야 한다.

### RA-0031

- 상태: 미확인
- 출처: HQ-0062에서 이관 (task T-0405, 등록 2026-10-22)
- 내용(HQ 원문 그대로):

  ADR-0147(첫 사례 턴 세션의 지출 도구 앞 라운드 budget 검사 hook; OD-19·OD-18 일부; T-0405)의 런타임 인수 항목 (lxi)·(lxii)를 런타임 머신에서 확인해 주세요. (lxi) `mcp__hilclaw__coder_run`·`mcp__hilclaw__correctness_check` 호출의 `PreToolUse` 입력 `tool_input`이 서버가 받는 인자 객체(그 `run_id` 포함)와 같은지. (lxii) 한 `.claude/settings.json`의 두 `PreToolUse` 항목이 같은 호출에 모두 걸릴 때 — 두 hook의 `command`가 같고 `args`만 달라도 — 둘 다 실행되고, 하나가 exit 2·다른 하나가 exit 0(출력 없음)이면 호출이 막히는지. 선택지: (a) 오너가 수동으로 확인해 결과를 답한다 (b) 런타임 자체 점검 코드 task로 돌린다(예: hook 입력과 서버 요청을 기록해 비교, 시험 도구에 건 두 hook이 각각 흔적을 남기는지) (c) 확인 전까지 그대로 둔다. 답이 없는 동안 막히는 것: 이 검사가 실제 세션에서 지출 호출을 막는다는 확신(실패 시 모든 지출 호출이 거절되거나 검사가 효력이 없음). 막히지 않는 것: ADR-0147의 두 코드 slice(픽스처·스텁 `claude`로만 검증)와 그 밖의 드라이버 task.

### RA-0032

- 상태: 미확인
- 출처: HQ-0063에서 이관 (task T-0408, 등록 2026-10-22)
- 내용(HQ 원문 그대로):

  ADR-0148(첫 사례 턴 세션의 끝 commit을 붙드는 `Stop` hook; OD-18 일부; T-0408, main 4dbe250)의 런타임 인수 항목 (lxiii)~(lxvi)을 런타임 머신에서 확인해 주세요. (lxiii) 루프가 쓴 `.claude/settings.json`의 `Stop` 항목이 `-p` 턴 세션 메인 세션의 응답이 끝날 때, 프로세스가 끝나기 전에 실행되고 sub-agent의 끝에서는 실행되지 않는지. (lxiv) 그 hook이 stderr 한 줄과 함께 exit 2로 끝나면 `-p` 메인 세션이 그 줄을 지시로 받아 계속하고, 그 뒤의 `Stop`에는 `stop_hook_active`가 `true`로 오는지(그 사이에 도구 호출이 있어도). (lxv) 런타임 머신에서 hook 프로세스가 서버와 같은 `git`을 찾고 `commit_owed`가 hook의 timeout 안에 끝나는지; timeout에 걸린 `Stop` hook은 멈춤을 통과시키는지. (lxvi) 이 줄을 받은 Round-Manager가 `run_commit`을 한 번 부르고 끝내며, 호출하지 않는 두 끝(유효한 run id 없음, 실패한 호출 뒤)에서는 바로 끝내는지. 선택지: (a) 오너가 수동으로 확인해 결과를 답한다 (b) 런타임 자체 점검에 `Stop` hook 표식 검사를 넣는 task로 돌린다 (c) 확인 전까지 그대로 둔다. 답이 없는 동안 막히는 것: 이 hook이 실제 세션에서 끝 commit을 붙든다는 확신. 막히지 않는 것: ADR-0148의 코드 slice 1·2(스텁 `claude`와 임시 git 저장소로 검증)와 그 밖의 드라이버 task.

### RA-0033

- 상태: 미확인
- 출처: HQ-0068에서 이관 (task T-0375, 등록 2026-10-23)
- 내용(HQ 원문 그대로):

  ADR-0137(첫 사례 코더 호출의 컨테이너와 코더 `claude -p` 시작 방법; OD-23 일부; T-0375, main a1e5c3f)이 런타임 인수 항목 (lxix)~(lxxiv)를 남겼다 — 코드 slice가 착지한 뒤 런타임 머신에서 확인해 주세요. (lxix) C-7의 각 머신에서 `docker version --format '{{.Server.Version}}'`이 daemon이 응답하면 exit 0과 버전을, 응답하지 않으면 시간 상한 안에 실패를 내는지. (lxx) 결정 3의 옵션(숫자 user, `HOME=/tmp`, `--entrypoint=`, `--cap-drop ALL`, `no-new-privileges`)으로 시작한 컨테이너 안에서 결정 6의 명령(`--permission-mode dontAsk --allowedTools Bash,Read,Edit,Write` 등)의 코더 `claude -p`가 `setup-token` 토큰(HQ-0053 (a))으로 Max 요금제 아래 인증되고, spec.json 읽기·output 아래 쓰기·clang 빌드와 실행(redirect 포함)이 거부 없이 되는지; 만료·폐기된 토큰에서 어떻게 되는지; 토큰을 폐기할 수 있는지와 방법. (lxxi) 그 세션이 이미지의 managed settings 외의 settings·hook·MCP·CLAUDE.md를 읽지 않고 토큰 위의 자격 증명 출처가 없으며 `DISABLE_UPDATES=1`이 버전을 고정하는지; 그리고 호스트에서 턴 세션 에이전트가 사전 승인된 `Read`·`Grep`으로 `/proc`의 프로세스 환경에서 `HILCLAW_CODER_OAUTH_TOKEN`을 읽을 수 있는지. (lxxii) 결정 3의 옵션으로 P2가 성립하는지 — scratch가 유일한 쓰기 가능 호스트 경로, 안의 `docker`·`sudo`가 호스트에 닿지 않음, 코더가 쓴 파일이 함수를 실행한 사용자 소유로 지울 수 있음(Linux, macOS Docker Desktop, Windows WSL). (lxxiii) `docker run`이 코더의 exit status를 그대로 돌려주는지; `--pull never`에서 이미지가 없으면 125인지; Claude Code가 125·126·127로 끝나는 일이 있는지; `--rm` 반환 시와 이름으로 `docker container rm --force` 뒤 컨테이너가 사라지는지; 없는 이름에 대한 `rm --force`의 exit·출력; `docker inspect`에 `CLAUDE_CODE_OAUTH_TOKEN`이 보이는지와 제거 뒤 daemon 저장소에 남는지. (lxxiv) 턴 루프가 시작한 턴 세션에서 `--mcp-config` 파일의 server entry `env`에 쓴 참조 `${HILCLAW_CODER_OAUTH_TOKEN}`이 세션 환경에서 펼쳐져 MCP front가 값을 받는지(파일에는 참조만); `HILCLAW_CODER_IMAGE`가 `HILCLAW_STANDIN_IMAGE`처럼 front에 닿는지. 선택지: (a) 오너가 수동으로 확인해 결과를 답한다 (b) 런타임 자체 점검 코드 task로 돌린다(예: docker 가용성·exit 매핑·참조 펼침을 점검하는 self-check 항목) (c) 확인 전까지 그대로 둔다. 답이 없는 동안 막히는 것: 이 방법으로 실제 코더 호출이 시작·인증·격리된다는 확신(특히 (lxxiv)가 실패하면 수정 기록 전까지 코더 호출이 시작되지 않음). 막히지 않는 것: ADR-0137의 코드 slice 1·2(스텁 `docker`로만 검증)와 그 밖의 드라이버 task.

### RA-0034

- 상태: 미확인
- 출처: HQ-0069에서 이관 (task T-0428, 등록 2026-10-23)
- 내용(HQ 원문 그대로):

  ADR-0153(모델 실행기의 GEMM binding·빌드·실행; OD-31 일부, PLAN P2-13)의 code slice 1이 T-0428(PR #251, main 790a9c8)로 끝나 런타임 인수 항목 (lxvii)을 확인할 때가 되었습니다. (lxvii) C-7의 각 종류의 머신에서, OD-14가 모델 프로그램에 주는 격리 환경(사용자가 지정한 이미지) 안에서 모델 프로그램이 커널들의 공유 라이브러리와 함께 빌드되고 그것들을 `dlopen`으로 적재하는지. 선택지: (a) 오너가 수동으로 확인해 결과를 답한다 (b) 런타임 자체 점검 코드 task로 돌린다(예: 격리 환경에서 공유 라이브러리 빌드·`dlopen` 적재를 점검하는 self-check 항목) (c) 확인 전까지 그대로 둔다. 답이 없는 동안 막히는 것: 그 격리 환경에서 모델 프로그램이 실제로 커널을 적재한다는 확신. 막히지 않는 것: ADR-0153 code slice 2, P2-11 계약 기록과 그 밖의 드라이버 task(드라이버 테스트는 POSIX의 clang으로 격리 환경 밖에서 빌드·적재를 검증함).

### RA-0035

- 상태: 미확인
- 출처: HQ-0072에서 이관 (task T-0474, 등록 2026-10-25)
- 내용(HQ 원문 그대로):

  ADR-0166(bf16 모델 forward program; OD-31 일부, PLAN P2-13)의 code slice 1~5(와 6)가 T-0474(PR #286, main 78b64f0d)로 모두 land되어 ADR-0153의 런타임 인수 항목 (lxviii)을 확인할 때가 되었습니다. (lxviii) Llama 3.2 1B 차원의 한 generation(ADR-0166 decision 2의 버퍼와 decision 4의 KV cache)이 OD-14가 모델 프로그램에 주는 격리 환경의 메모리 한도 안에 드는지. 선택지: (a) 오너가 런타임 머신에서 수동으로 확인해 결과를 답한다 (b) 런타임 자체 점검 코드 task로 돌린다(예: 실행 전 필요 메모리를 계산해 환경 한도와 비교하는 self-check) (c) 확인 전까지 그대로 둔다. 답이 없는 동안 막히는 것: 실제 Llama 3.2 1B 크기에서 generation이 메모리 한도 안에서 돈다는 확신(P2-15). 막히지 않는 것: P2-13의 나머지·P2-14와 그 밖의 드라이버 task(드라이버 테스트는 합성 가중치로 검증함).

### RA-0036

- 상태: 미확인
- 출처: HQ-0073에서 이관 (task T-0479, 등록 2026-10-25)
- 내용(HQ 원문 그대로):

  ADR-0168(cpu_standin의 컨테이너 상황에서 세 HW 도구의 답; OD-18 ⑱ (다)·⑲ (나) 일부; T-0479, PR #293, main bc54bd01)이 런타임 인수 항목 (lxxv)~(lxxvii)를 남겼다. (lxxv) Docker client가 도달 불가 daemon, `--pull never`에서 store에 없는 image, 생성·시작할 수 없는 container, image에 없거나 실행할 수 없는 program의 각 경우에 build·process container를 125·126·127 중 하나(그 밖의 상태가 아님)로 끝내는지와 그때 쓰는 문구. (lxxvi) image의 `clang`이 compile·link 실패에서 125~127로 끝나지 않는지. (lxxvii) 정상 종료 뒤 `--rm` 제거가 실패할 때 client가 주는 상태, container가 없는 이름에 `rm --force`가 주는 상태. 선택지: (a) 오너가 런타임 머신에서 수동 확인해 결과를 답한다 (b) 런타임 자체 점검 코드 task로 만든다 (c) 확인 전까지 그대로 둔다. 답이 없는 동안 막히는 것: 실제 Docker에서 ADR-0168의 상태 해석이 맞다는 확인. 막히지 않는 것: ADR-0144 slice (4) 등 이후 드라이버 task(테스트는 스텁으로 검증).

### RA-0037

- 상태: 미확인
- 출처: HQ-0074에서 이관 (task T-0480, 등록 2026-10-26)
- 내용(HQ 원문 그대로):

  ADR-0169(cpu_standin 빌드 컨테이너의 컴파일러 로그 추출과 강제 제거 시간 제한 60 s; OD-18 일부; T-0480, PR #294, main 5f3eee69)이 런타임 인수 항목 (lxxviii)~(lxxx)를 남겼다. (lxxviii) `-o` 빌드에서 client가 image의 `clang` 진단을 stderr로만 돌려주고 stdout에는 `clang`의 것을 쓰지 않는지, 그리고 build container가 프로그램의 상태로 끝날 때 client가 어느 스트림에 자기 문구(예: platform 경고)를 쓰는지. (lxxix) 실행 중인 build·process container의 `docker rm --force`가 Docker Desktop을 포함해 60 s 안에 끝나고 그 뒤 container의 프로세스가 없어지는지. (lxxx) client가 0을 돌려줄 때 `clang`이 container 안 경로에 쓴 실행 파일이 host 빌드 디렉토리의 대응 경로에 일반 파일로 있는지. 선택지: (a) 오너가 런타임 머신에서 수동 확인해 결과를 답한다 (b) 런타임 자체 점검 코드 task로 만든다 (c) 확인 전까지 그대로 둔다. 답이 없는 동안 막히는 것: 실제 Docker에서 ADR-0169의 로그·제거 해석이 맞다는 확인. 막히지 않는 것: run 도구의 cpu_standin 동작 등 이후 드라이버 task(테스트는 스텁으로 검증).

### RA-0038

- 상태: 미확인
- 출처: HQ-0075에서 이관 (task T-0481, 등록 2026-10-26)
- 내용(HQ 원문 그대로):

  ADR-0170(첫 사례 대기자 빌드의 컴파일러 로그와 cpu_standin `sim.run`·`board.run` 동작; OD-18 ⑲ (다) 일부; T-0481, PR #295, main a3cab425)이 런타임 인수 항목 (lxxxi)·(lxxxii)를 남겼다. T-0482(기본 표의 cpu_standin 항목)가 착지한 뒤 C-7의 각 머신 종류에서 Docker로 확인할 것. (lxxxi) image의 `clang`이 ADR-0116 결정 3의 플래그로 build container 안에서 `timing_waiter.c`를 빌드할 때 상태 0으로 끝나고 두 스트림에 아무것도 쓰지 않으며 host 빌드 디렉토리의 대응 경로에 대기자 실행 파일을 일반 파일로 남기는지. (lxxxii) 두 build container가 ADR-0144 결정 6의 숫자 user로 빌드 디렉토리에 쓴 두 실행 파일을 같은 user가 timing process container에서 시작할 수 있는지(대기자는 container의 프로그램으로, 타이밍 실행 파일은 대기자의 `execv`로). 선택지: (a) 오너가 런타임 머신에서 수동 확인해 결과를 답한다 (b) 런타임 자체 점검 코드 task로 만든다 (c) 확인 전까지 그대로 둔다. 답이 없는 동안 막히는 것: 실제 Docker에서 ADR-0170의 대기자 빌드·시작 해석이 맞다는 확인. 막히지 않는 것: T-0482 등 이후 드라이버 task(테스트는 스텁으로 검증).

### RA-0039

- 상태: 미확인
- 출처: task T-0361 (ADR-0132)의 Result, planner가 T-0484 생성 시 반환 (등록 2026-10-26)
- 내용:

  ADR-0132(첫 사례 선택 역할 `technique-selector`와 등록표 도구 `hypotheses.write`; OD-23·OD-30·OD-18 일부; T-0361)의 런타임 인수 항목 (xxiii)·(xxiv). T-0484가 land한 뒤 런타임 머신에서 확인한다. (xxiii) `-p` 턴 세션에서 `.claude/agents/technique-selector.md`로 정의된 sub-agent가 그 `tools` 목록의 도구만 정확히 받는가, 위임 메시지와 최종 메시지가 온전히 전달되는가. (xxiv) 첫 사례 라운드가 가질 수 있는 가장 큰 가설 레코드에서도 `hypotheses.write` 요청의 `record`가 MCP 도구 호출 입력 한도 안에서 온전히 도구에 닿는가.

### RA-0040

- 상태: 미확인
- 출처: task T-0485 (ADR-0171)의 Result (등록 2026-10-26)
- 내용:

  ADR-0171(라운드 ≥ 1 spec의 기법 선택과 coder-driver 위임; 등록표 도구 `catalog.read`; OD-23·OD-22·OD-6 일부; T-0485)의 런타임 인수 항목 (lxxxiii)·(lxxxiv). ADR-0171 slice 2(정의 파일)가 land한 뒤 런타임 머신에서 확인한다. (lxxxiii) `-p` 턴 세션에서 technique-selector의 `mcp__hilclaw__catalog_read` 호출이 도구에 닿고 그 결과가 selector에 온전히 전달되며, caller 검사가 selector에는 통과시키고 main 세션에는 거부한다. (lxxxiv) selector의 마지막 메시지에 `techniques:` 줄이 정확히 하나 있고, Round-Manager가 그 id들을 바꾸지 않고 순서대로 coder-driver 위임 메시지에 옮기며, coder-driver가 그것을 바꾸지 않고 `spec.write` 요청의 `techniques`에 넣는다.

### RA-0041

- 상태: 미확인
- 출처: task T-0487 (ADR-0172)의 Result (등록 2026-10-26)
- 내용:

  ADR-0172(코더 호출 뒤 라운드 ≥ 1의 단계 — 검사·측정·판정 위임·닫는 단계; OD-23 일부, OD-16·OD-17·OD-30 관련; T-0487)의 런타임 인수 항목 (lxxxv)·(lxxxvi). 원문 그대로:

  (lxxxv) In one round >= 1 turn session, the six foreground delegations of steps 6, 8, 9, 10, 11 and 12 (technique-selector, coder-driver, evaluator at `sim`, evaluator at `board`, experiment-runner, evaluator for the verdicts) each return their report in the same turn and in order, and the session reaches `case.write`, `round.end` and `run.commit` before any limit of the session itself ends it (as ADR-0142 (xlv) for round 0).

  (lxxxvi) From the coder-driver's final message, the Round-Manager tells a result of `coder.run` with a non-empty `taken`, a result with an empty one or a kind of `coder.run`, and a kind of `spec.write`, and takes step 9, step 12 or the stop as ADR-0172 decision 2 says; and from the evaluator's final message of step 12 it tells written verdicts (the file written, or `verdicts_exist`) from any other report, and goes to the closing steps or the stop as decision 5 says.

### RA-0042

- 상태: 미확인
- 출처: task T-0488 (ADR-0173)의 Result (등록 2026-10-26)
- 내용:

  ADR-0173(technique-selector의 사례 조회 읽기 도구 `cases.lookup`; OD-30·OD-23 일부; T-0488)의 런타임 인수 항목 (lxxxvii)·(lxxxviii).

  (lxxxvii) In a `-p` turn session, the technique-selector's call of `mcp__hilclaw__cases_lookup` runs under the derived pre-approval without a prompt, and the caller check lets it through for the selector and refuses it for the main session.

  (lxxxviii) The result of `cases.lookup` for the largest key directory a first-case data root holds reaches the selector whole, within any limit Claude Code puts on the result of an MCP tool call; and the selector writes the result's `cases_read` into the record unchanged and before the record, as ADR-0173 decision 5 says.

### RA-0043

- 상태: 미확인
- 출처: task T-0489 (ADR-0174)의 Result (등록 2026-10-26)
- 내용:

  ADR-0174(technique-selector의 앞선 판정 읽기 도구 `verdicts.read`; OD-23·OD-18 일부; T-0489)의 런타임 인수 항목 (lxxxix)·(xc).

  (lxxxix) In a `-p` turn session, the technique-selector's call of `mcp__hilclaw__verdicts_read` runs under the derived pre-approval without a prompt, and the caller check lets it through for the selector and refuses it for the main session.

  (xc) In a round ≥ 2 of a first-case run, the technique-selector calls `mcp__hilclaw__verdicts_read` once for each earlier round, in ascending order and before `mcp__hilclaw__hypotheses_write`, as ADR-0174 decision 6 says. The result for the largest verdicts file a first-case round writes reaches it whole, within any limit Claude Code puts on the result of an MCP tool call.

### RA-0044

- 상태: 미확인
- 출처: task T-0492 (ADR-0175)의 Result (등록 2026-10-26)
- 내용:

  ADR-0175(첫 사례 turn 세션의 표준 출력·표준 오류의 행선; OD-19 일부; T-0492)의 런타임 인수 항목 (xci).

  (xci) A `-p` turn session started with its standard output on the entry's standard error writes its reply and every message about why it stopped, such as an expired login, a usage limit or an error, only to its standard output and standard error, and not to the terminal or another descriptor. Nothing of it then reaches the entry's standard output, and a person reading the entry's standard error after a failed turn finds there what the session said.

### RA-0045

- 상태: 미확인
- 출처: task T-0502 (ADR-0179)의 Result (등록 2026-10-28)
- 내용:

  ADR-0179(cpu_standin의 bf16 검증 빌드·프로세스 시간 상한; OD-14·OD-18 일부; T-0502)의 런타임 인수 항목 1.

  Check that the ADR-0179 limits let a correct, untuned kernel of each of bf16 `gemm`, `rmsnorm`, `elementwise_add`, `swiglu` and `sdpa_kv_cache` complete at the shapes of ADR-0152, and end one that does not end. Check this on each C-7 system, inside the container of ADR-0144. In particular, check that 10 per element covers drawing, checking and reporting the 2.6e8 input elements of lm_head at M = 1, and the 131 MB report per draw at M = 512 through the container client.

### RA-0046

- 상태: 미확인
- 출처: task T-0502 (ADR-0179)의 Result (등록 2026-10-28)
- 내용:

  ADR-0179(cpu_standin의 bf16 검증 빌드·프로세스 시간 상한; OD-14·OD-18 일부; T-0502)의 런타임 인수 항목 2.

  Find the number of draws up to which the tool function's own work (regeneration and the float64 reference) stays inside the 240 s left in the MCP idle window. Do this for bf16 `gemm` at lm_head M = 512 and at the projections at M = 512.

### RA-0047

- 상태: 미확인
- 출처: task T-0503 (ADR-0180)의 Result (등록 2026-10-28)
- 내용:

  ADR-0180(bf16 `rope` 검사의 시작 위치, cpu_standin 시간 상한, 표준 입력 행 전달; OD-16·OD-14·OD-18 일부; T-0503)의 런타임 인수 항목 1.

  On each C-7 system, check that a container client started with `--interactive` and without `--tty` passes the 4·m·d bytes of the `rope` rows to the program's standard input unchanged and closes it at the end, including when the program ends before it has read them all.

### RA-0048

- 상태: 미확인
- 출처: task T-0503 (ADR-0180)의 Result (등록 2026-10-28)
- 내용:

  ADR-0180(bf16 `rope` 검사의 시작 위치, cpu_standin 시간 상한, 표준 입력 행 전달; OD-16·OD-14·OD-18 일부; T-0503)의 런타임 인수 항목 2.

  On each C-7 system, inside the container of ADR-0144, check that the ADR-0180 limits let a correct, untuned `rope` kernel complete at the shapes of ADR-0152 and end one that does not end, and that the tool function's two table builds (1.85 s each on the development machine) and its per-draw work (0.18 s) stay inside the 240 s left in the MCP idle window.

### RA-0049

- 상태: 미확인
- 출처: task T-0506 (ADR-0182)의 Result (등록 2026-10-28)
- 내용:

  ADR-0182(모델 실행기의 빌드·생성 프로세스 컨테이너 격리; OD-14·OD-31 ④ 일부; T-0506)의 런타임 인수 항목 1. RA-0034·RA-0035를 좁힌다(둘은 열린 채 둔다).

  On each C-7 machine kind with Docker and the image the user names, in the containers of ADR-0182 decision 2: check that the image links each kernel into a shared library and the forward program (with `-ldl` where its C library needs it), and that the program loads the libraries with `dlopen` by their paths below `/build` and finds each entry point with `dlsym`.

### RA-0050

- 상태: 미확인
- 출처: task T-0506 (ADR-0182)의 Result (등록 2026-10-28)
- 내용:

  ADR-0182(모델 실행기의 빌드·생성 프로세스 컨테이너 격리; OD-14·OD-31 ④ 일부; T-0506)의 런타임 인수 항목 2. RA-0034·RA-0035를 좁힌다(둘은 열린 채 둔다).

  Check that a generation at Llama 3.2 1B dimensions, whose multi-GB input file is written into the build directory on the host and read through the bind mount (on Docker Desktop through its VM's file sharing), completes in a container with no memory bound.

### RA-0051

- 상태: 미확인
- 출처: task T-0506 (ADR-0182)의 Result (등록 2026-10-28)
- 내용:

  ADR-0182(모델 실행기의 빌드·생성 프로세스 컨테이너 격리; OD-14·OD-31 ④ 일부; T-0506)의 런타임 인수 항목 3. RA-0034·RA-0035를 좁힌다(둘은 열린 채 둔다).

  Check that the k + 2 container starts of one generation add seconds each and nothing more.

### RA-0052

- 상태: 미확인
- 출처: task T-0505 (ADR-0181)의 Result (등록 2026-10-29)
- 내용:

  ADR-0181(sim.run·board.run의 bf16 타이밍 run; OD-13·OD-14·OD-16 ⑥·OD-18 일부; T-0505)의 런타임 인수 항목 1.

  Check that the limits of ADR-0181 decision 6 let a correct, untuned bf16 kernel of each kind complete a timing run at ADR-0152's shapes and end one that does not end, on each C-7 system in the ADR-0144 container (lm_head M = 512 excepted as stated in decision 6).

### RA-0053

- 상태: 미확인
- 출처: task T-0505 (ADR-0181)의 Result (등록 2026-10-29)
- 내용:

  ADR-0181(sim.run·board.run의 bf16 타이밍 run; OD-13·OD-14·OD-16 ⑥·OD-18 일부; T-0505)의 런타임 인수 항목 2.

  Check that the waiter reports `waiter_max_rss_kib` for the bf16 timing executables as for the fp32 one, on each C-7 system.

### RA-0054

- 상태: 미확인
- 출처: task T-0505 (ADR-0181)의 Result (등록 2026-10-29)
- 내용:

  ADR-0181(sim.run·board.run의 bf16 타이밍 run; OD-13·OD-14·OD-16 ⑥·OD-18 일부; T-0505)의 런타임 인수 항목 3.

  Check that the `rope` rows reach the timing program through the waiter's inherited descriptor 0 byte for byte.

### RA-0055

- 상태: 미확인
- 출처: task T-0493 (`PROCESS/NIGHTLY.md`)의 Result (등록 2026-10-29)
- 내용:

  PLAN P2-10 nightly 루틴의 런타임 인수 항목. #323이 land된 뒤 nightly 머신에서 확인한다(첫 확인은 오너의 수동 run — D24 E2).

  (nightly-1) On the driver's machine, a separate clone with the routine registered daily at KST 03:00 in Bypass permissions, with the prompt "`PROCESS/NIGHTLY.md` §2를 1회 수행":
  - (1) Inside WSL 2, the routine session runs `python -m hilclaw.nightly <base>`. The pre-firing check finds `HILCLAW_CODER_IMAGE`, `HILCLAW_CODER_OAUTH_TOKEN`, `HILCLAW_STANDIN_IMAGE`, `claude`, `docker` and `git` (a host `clang` is no longer checked: ADR-0186, 2026-10-30).
  - (2) The turn sessions start from the entry with `CLAUDECODE` and `CLAUDE_CODE_ENTRYPOINT` removed, and are not refused as nested sessions. A failure here would be reported as `turn_start/stopped_at_check/*` or `failed_turn`.
  - (3) The P2-5 configuration run ends `run_over` after 5 rounds.
  - (4) The machine's `gh` is logged in as the repository owner. It can create the `nightly-failure` label, create and comment on issues, and close them. The filtered `--jq` read returns that account's reports.
  - (5) The firing's data root stays local and nothing reaches HIL-Claw-data.

### RA-0056

- 상태: 미확인
- 출처: `P2-15` (근거 task T-0516, 등록 2026-10-30)
- 내용:

  PLAN P2-15. 실제 Llama 3.2 1B의 가중치·토크나이저로 P2-14의 end-to-end가 돌고 reference와 맞는지를, 런타임 사용자가 라이선스에 동의해 입수한 파일로 오너가 런타임 머신에서 확인한다. 맞는다는 것은 HQ-0071의 답대로 둘 다를 뜻한다: 행마다 teacher forcing logit을 Hugging Face transformers reference와 원소별 `rtol`·`atol`로 비교해 통과하고, 같은 프롬프트에서 처음 N개 greedy 토큰이 reference와 같다(`rtol`·`atol`·N은 사용자 지정).

  확인이 가능해지는 조건: 2026-10-30 현재 저장소에는 실제 가중치 읽기, 토크나이저, P2-15 비교의 구현이 없고(`hilclaw/`에 safetensors·tokenizer·transformers 언급 없음), OD-31 ⑤와 ⑦의 나머지(모델 파일의 출처·포맷·변형·저장 위치, 필요한 패키지)가 미결이다. best에서 binding을 얻는 방법과 실행기의 노출 형태(OD-31 ④)도 열려 있다. 이것들이 land된 뒤 확인한다. RA-0035·RA-0050(Llama 3.2 1B 차원의 메모리·입력 파일)과 함께 본다. nightly 루틴은 이것을 돌리지 않는다(HQ-0076 (2)의 답 (a)).

### RA-0057

- 상태: 미확인
- 출처: T-0517, ADR-0188 (등록 2026-10-30)
- 내용:

  (i) the image's clang accepts `-std=gnu11 -O2 -ffp-contract=off -fopenmp` and `-lm` under each C-7 system's Docker: Linux, macOS Docker Desktop and WSL; (ii) a kernel using OpenMP completes a check and a timing run in the container under the options of ADR-0144 and the limits of ADR-0117; (iii) the thread count the runtime picks in that container, and whether it fits the processors the machine gives; (iv) the waiter still reports `waiter_max_rss_kib` for such a kernel in a container; (v) a kernel with no OpenMP is measured as before within noise.

### RA-0058

- 상태: 미확인
- 출처: T-0519, ADR-0190 (등록 2026-10-30)
- 내용:

  (i) A real technique-selector whose `catalog.read` result on a bf16 run holds no entry reports `techniques: none`, and the round goes on to a spec with an empty `guidance.techniques`. (ii) A real coder given the prompt's every-shape sentence keeps its kernel correct at values of the size parameters other than its spec's. This shows in a generation at the other call shapes (RA-0056).

### RA-0059

- 상태: 미확인
- 출처: `P2-9` (근거 task T-0520, ADR-0074; 등록 2026-10-31)
- 내용:

  PLAN P2-9. S6 수용 기준 측정: 오너가 런타임 머신에서 같은 키·target·tolerance·N·budget으로 run을 두 번(첫 run과 두 번째 run) 수행하고 `python -m hilclaw.s6_metric <first_run_id> <second_run_id>`로 판정한다(met·not met·not applicable, ADR-0074). 드라이버의 스텁 `claude` 검증 run, nightly 루틴의 run, 테스트 run(D25)은 첫 run으로도 두 번째 run으로도 쓰지 않는다. 몇 쌍을 돌리고 판정을 어떻게 합치는지, 대조 run과 시간 상한은 HQ-0081의 답을 따른다.
