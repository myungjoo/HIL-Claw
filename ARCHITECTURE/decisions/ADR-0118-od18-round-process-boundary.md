# ADR-0118: The round boundary of a first-case run — one turn is one Claude Code session process of its own, each turn is started by a deterministic turn loop of the layer-2 package, and the turn session runs in a directory outside both checkouts with the runtime's layer-1 definition kept under `orchestration/` (OD-18 "라운드 = 프로세스 경계", #8 M4, for the runs of ADR-0076 decision 1; one point of OD-23)

## Status

- **Accepted on 2026-10-19** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it.**
- **Two kinds of content.** What an owner decision, an agreement of #4, a requirement, a use case, an accepted record or a documentation page says is **cited**, with its source named. **Everything else is this record's own**: that a turn is one OS process, the turn loop, the session directory, the place `orchestration/` and its naming rule, the way the server is given, and every weighing.
- **No owner sentence decides these points, and none reads two ways about them.** Searched: the body of #4 and its 6 comments; the body of #5 and the 38 of its 187 comments whose text holds no "posted by driver" marker; the bodies and comments of #7 and #8. Search terms: `/loop`, cron, turn, 턴, 프로세스 경계, process boundary, OS process, Round-Manager, working directory, `.claude/`, `.mcp.json`, `mcpServers`, `--mcp-config`, session, bring-up. The closest sentences, each read for what it says and no further:
  - #4 body §1 and §3 ([합의]): every turn starts with a clear context; "turn ≡ Round로 고정"; "한 Round를 하나의 Agent Session(Round-Manager)이 관리". They do not say whether a turn is an OS process of its own.
  - #4 body §2e: "`/loop`·cron 재기동 중복으로 두 턴이 동시 실행될 수 있음 → STATE에 `lock{owner, heartbeat}`". It names `/loop` and cron as what may restart turns and asks for a lock; it does not choose either.
  - #4 comment of 2026-07-31 (§3a revision, https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5138366881): the agreed part is that "`.claude/agents/`의 subagent가 Round 내 단일 task를 각각 대표". Its bootstrap list — "CLAUDE.md, `.claude/agents/` 5종, `.claude/skills/`, `.claude/commands/`(/optimize-round), `.claude/settings.json`" — is under "[미결 — 다음 debate 항목]", so it decides no place.
  - The same #4 comment of 2026-07-31 states its purpose as a check whether work can start "HIL-Claw 폴더에서 Claude Code CLI 기동 즉시". That is where the discussion began, not a decision on where a runtime session runs. It predates the owner's rule of 2026-10-13 that the driver and the runtime are different programs (HQ-0006 answer), and the repository root has since held the driver's files.
  - The #4 pointer comment https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139248800 and #7 supplement §2(8) (https://github.com/myungjoo/HIL-Claw/issues/7#issuecomment-5139423949): "1 round = 1 OS process = 1 turn = 1 commit" is a **recommendation** ("권고"), registered as a proposal under OD-18.
  - #5 A-3 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5537233759): "매 턴(=Round) 종료 시 `HIL-Claw-data`에 로컬 commit하는 것은 불변 규칙". It speaks of the commit, not of processes.
  - #5 B-6 point 3: "a Claude Code session acts as the **main orchestrator** (agent), spawns **sub-agents**, and those sub-agents invoke the **Claude Code CLI** (`claude -p`)". #5 A-12 context: "in Method B the repository has three layers — (1) orchestration = Claude Code prompts/skills/agent definitions (Markdown)". They say what the session is and that layer 1 is in the repository, not where in it or how a turn is started.
  - The answer to HQ-0006 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6135246858): "the agent that **builds** HIL-Claw and the agent that **runs** it are different programs"; the self-check is run by "the instance bring-up (P2-1, round 0)". The `/loop` and cron sentences of #5 D1 and D11 are about the development driver, not the runtime.
- Answers, **for the runs of ADR-0076 decision 1**, the OD-18 point "라운드=프로세스 경계 채택 여부 (NFR-7① 전제, UC-3 `/loop`과의 관계 = #8 M4)" (Open Decisions register in [Requirements](../Requirements.md)): what a turn is in processes (decision 2), what starts each turn (decision 3), where the turn session runs (decision 4) and how it is given the MCP server (decision 6). For **OD-23** it answers one point: where in this repository the definition of the turn session's agents lives and how it reaches the session (decision 5). **OD-18 and OD-23 keep their status.** OD-18 sub-question ⑯ (가) is **not** answered (Boundaries).
- **It is a record, not code. No `claude` process was started** (D16), and no fact below was tried in a live session. **No member, file, kind, value or version of the data plane is added or changed.**
- It builds on [ADR-0004](ADR-0004-od8-data-plane-layout.md) (path table; decisions 2, 4), [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (F1, F3, F6, F7; decisions 3, 7), [ADR-0012](ADR-0012-od8-runtime-state-file.md) (decisions 3, 6, 7), [ADR-0054](ADR-0054-od18-runtime-self-check.md) (K4, K10, K11; decisions 4, 9) and [ADR-0115](ADR-0115-od8-instance-start-performer.md) (decisions 2, 3). **If one of them is reverted, this record is revisited with it.**
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **The open point.** OD-18 (register row): "라운드=프로세스 경계 채택 여부(NFR-7① 전제, UC-3 `/loop`과의 관계 = #8 M4)". NFR-7 ①: components "라운드 경계(stateless turn 경계)에서 교체·수정 가능해야 하며 … *전제*: 라운드 경계가 프로세스 경계여야 성립하며(OD-18)". UC-3 step 1: rounds repeat "(`/loop` 또는 cron 재기동; 라운드 = 프로세스 경계 채택 여부 = Requirements OD-18)". #8 M4: "`/loop`은 **동일 프로세스 내 반복**이므로 UC-3의 기본 구동 방식을 택하면 NFR-7①이 성립하지 않는다". ADR-0010, ADR-0015 and ADR-0054 leave the point open.
- **The moments a turn meets** (cited: ADR-0012 decision 3): a run starts with `round` 0; "A process died inside round *k*" → the fresh turn finds `round` *k* and "goes on with it"; after the commit of round *k*, `round` is *k* + 1. `round` does not say "whether a turn runs at all … that the run is over, stopped or waiting is said by members this record does not define". ADR-0012 decision 6: `STATE.json` "is replaced as a whole by its one writer" (the Round-Manager — ADR-0004 path table), and the write that ends a round moves `round`. Which step commits is OD-8 sub-question ⑪.
- **Inside a round** (cited: #4 body §3a, §3c and the §3a revision): the Round-Manager is "1 agent session"; sub-agents represent single tasks inside it; a coder call is "headless `claude -p` (별도 프로세스)"; HW experiments are tool calls. The tool layer is a stdio MCP server that "lives as long as what it was given to … It runs the code it loaded at its start" (ADR-0010 decision 7, F7).
- **The repository today**: its root holds the development driver's `CLAUDE.md` and `.claude/` (`settings.json` with an allow and deny list, `agents/dev-planner.md`, `dev-executor.md`, `dev-reviewer.md`, `skills/dev-item-address`, `skills/dev-code-review`) and `hilclaw.config.json`. DRIVER §1-5 plans a guard hook in that settings file that "`claude` 자식 프로세스의 시작도 거부한다". CLAUDE.md "개발 드라이버와 런타임의 구분" (owner, 2026-10-13): the driver and the runtime orchestrator "다른 프로그램이다".
- **Facts about Claude Code** the decisions use. *Verified* = read in the named page on 2026-10-19; none was tried. K-numbers are those of ADR-0054, F-numbers those of ADR-0010.

| # | Fact | Status |
|---|---|---|
| R1 | "Claude Code loads `CLAUDE.md` and `CLAUDE.local.md` from your current working directory and every directory above it." `CLAUDE.md` files "in subdirectories under your current working directory" load "once Claude reads, writes, or edits another file in that subdirectory"; `AGENTS.md` is read by default "only when you have no `CLAUDE.md` in your working directory or above it" (the setting `claude-md-and-agents-md` reads both); then a subdirectory's `AGENTS.md` loads "when Claude opens a file there with the Read tool and that subdirectory has none of the three `CLAUDE.md` files of its own". | verified — https://code.claude.com/docs/en/memory |
| R2 | "Project subagents are discovered by walking up from the current working directory, so every `.claude/agents/` between there and the repository root is scanned." | verified — https://code.claude.com/docs/en/sub-agents |
| R3 | Project skills load "from `.claude/skills/` in the directory where you start it and in every parent directory up to the repository root"; a nested `<subdir>/.claude/skills/` loads for "A session started above it … once Claude works on files there". | verified — https://code.claude.com/docs/en/skills |
| R4 | "Hooks and other `.claude/settings.json` keys load from the current working directory's `.claude/` folder with no parent-directory fallback"; but "If you start Claude Code in a subdirectory of a git repository, it reads and writes [`.claude/settings.local.json`] at the repository root" — except, among other cases, "on Windows", where "the file stays with `.claude/settings.json`". | verified — https://code.claude.com/docs/en/permissions, https://code.claude.com/docs/en/settings |
| R5 | "Claude Code watches `~/.claude/agents/` and `.claude/agents/`. When you add or edit a subagent file on disk … the next delegation uses the updated definition, with no restart needed"; "The watcher covers only directories that existed when the session started". | verified — https://code.claude.com/docs/en/sub-agents |
| R6 | `/loop` runs "a prompt on repeat while the session stays open"; "Tasks are session-scoped"; "Tasks only fire while Claude Code is running and idle. Closing the terminal or letting the session exit stops them firing"; "Recurring tasks automatically expire 7 days after creation." | verified — https://code.claude.com/docs/en/scheduled-tasks |
| R7 | A `claude -p` run "can stay open to wait for background work", including pending wakeups: "when Claude has scheduled a self-paced `/loop` wakeup, the run waits for each wakeup to fire and runs its iteration until the loop ends" (said of a run whose prompt was passed as text; a fixed-interval `/loop` is not named there). "Claude Code exits with code 0 on success and a non-zero code when the run fails." | verified — https://code.claude.com/docs/en/headless |
| R8 | The auto memory directory "is derived from the git repository, so all worktrees and subdirectories within the same repo share one auto memory directory. Outside a git repo, the project root is used instead." | verified — https://code.claude.com/docs/en/memory |
| R9 | `--add-dir` "Grants file access; Claude Code doesn't discover most `.claude/` configuration from these directories" — but skills in `.claude/skills/`, command files and subagents in `.claude/agents/` are loaded from such a directory. | verified — https://code.claude.com/docs/en/cli-reference, https://code.claude.com/docs/en/permissions |
| R10 | "Claude Code shows the trust dialog in interactive sessions only. A `claude -p` run or an SDK session never shows it, and trusting a parent folder doesn't count". For `claude -p` in a folder never trusted, hooks in settings files are "Used"; `permissions.allow` rules and `additionalDirectories` in `.claude/settings.json` are "Not used"; frontmatter hooks of a project subagent and inline `mcpServers` of a subagent are "Not used". A folder is trusted by hand by setting `projects["<path>"].hasTrustDialogAccepted` in `~/.claude.json`, where `<path>` is "the repository root, or the folder itself outside a repository". | verified — https://code.claude.com/docs/en/permissions |
| F6 / K10 | Without `--bare`, a `-p` session runs the hooks of its project's `.claude/settings.json`, connects the servers of its `.mcp.json` with no approval prompt, and loads "anything configured in the working directory or `~/.claude`". | cited — ADR-0010, ADR-0054 |
| K4 | `--mcp-config` loads MCP servers from JSON files; `--strict-mcp-config` uses "Only … MCP servers from `--mcp-config`, ignoring all other MCP configurations." | cited — ADR-0054 |
| K11 | `--bare` skips that discovery and reads no OAuth credential; it "will become the default for `-p` in a future release". | cited — ADR-0054 |

- R5 differs from the premise of the OD-18 proposal and #7 supplement §2(8), "`.claude/agents/`가 세션 중 재탐지되지 않으므로": an edited agent file now reaches a running session. Other parts of a session are still fixed at its start: the `CLAUDE.md` files of R1 and the MCP server process of ADR-0010 decision 7. A fresh context per turn (#4 §1) is fixed as well, whatever the files do.

## Decision

A sentence is **cited** when a source is named with it; it says what that source says. Every other sentence is **this record's own**.

### 1. Scope and terms

- **The runs** are those of ADR-0076 decision 1, the first case: the hw_profile names `cpu_standin` or the mock; the op_signature is absent or one that ADR-0041 decision 5 covers. Other runs are outside: nothing here is required or allowed of them.
- **Turn session**: the Claude Code process that carries one turn of a run. **Turn loop**: the layer-2 function of decision 3. **Session directory**: the working directory of a turn session (decision 4). **Definition**: the runtime's layer-1 files a turn session is given — the Round-Manager's prompt and any agent definitions, skills and hook settings (decision 5).

### 2. One turn is one session process of its own (a)

- **Every turn of a run is one Claude Code session, started fresh as an OS process of its own, and that process carries that turn only.** No turn session begins a second turn. This makes concrete "turn ≡ Round" and the clear context of every turn (cited: #4 body §1, §3), which this record takes as fixed.
- The Round-Manager is the main conversation of the turn session (cited: #4 §3c "1 agent session"; #5 B-6 point 3). Its sub-agents run inside that process. A coder call is a separate `claude -p` process (cited: #4 §3a); it is not a turn and starts none.
- **What ends a turn: the end of the turn session's process, whatever causes it.** A turn ends in one of two ways.
  - **(i) With its round.** The session ends after the write that ends its round (ADR-0012 decision 6), together with whatever commit step OD-8 sub-question ⑪ names. It does not begin the next round.
  - **(ii) Before its round ends.** The process dies or is stopped (cited: #4 §3b). Or the session ends while the run waits for the user — for permission to change the toolchain or the environment, where the wait ends the session (UC-3; how a run waits is OD-8 ㉝ (가)), or at a gate (OD-3) where the gate layer ends the session rather than waiting inside it (decision 3). Or it ends without that write for any other reason, such as an error or a usage limit.
- **So a turn may end before its round ends, and a round may take more than one turn.** In every case of (ii), `round` still names the round, and the next turn goes on with it (cited: ADR-0012 decision 3, the second moment; #4 §3b, a fresh turn skips the expensive substeps that are finished). No turn spans two rounds.
- **What this gives NFR-7 ①.** Every turn is a new process. It reads the definition and the `CLAUDE.md` files anew (R1), and it starts its own MCP server (decision 6; ADR-0010 decision 7). A component replaced between two turns therefore takes effect at the next turn. Between two turns of one round, the copy of decision 4 makes a replacement take effect in the same way. Whether such a replacement is allowed is not decided here, and neither is what a replaced measurement contract requires (OD-11).

### 3. A deterministic turn loop of the layer-2 package starts each turn (b)

- **One function of the layer-2 package `hilclaw/`, the turn loop, starts every turn session of a run.** Given one run, it repeats these steps:
  1. it reads the run's files to tell whether a further turn is to run, and returns if not;
  2. it prepares the session directory (decisions 4 to 6);
  3. it starts one turn session in that directory;
  4. it waits until that process has ended;
  5. it goes back to step 1.
- It makes no judgement and calls no model itself, in the sense of ADR-0115 decision 2. It never has two turn sessions of one run running at once.
- **What it reads in step 1 is not defined.** `STATE.json` version 1 requires `schema_version`, `round` and `budget_spent` and leaves its top level open, and that the run is over, stopped or waiting "is said by members this record does not define" (cited: ADR-0012 decisions 2 and 3). This record defines no such member. The question stays with the rest of OD-8 (the other members of `STATE.json`) and with OD-19 (termination when a budget is spent). Until a record answers it, the code slice takes from its caller a predicate that step 1 asks before every turn (Consequences).
- **What it does after a turn session failed** — the process ended with a failure or did not write the end of its round — is not decided: retry at once, wait, stop, notify, or a pause on a usage limit (an OD-19 proposal drawn from C-7 ②) (OD-10, rest of OD-17, OD-19, OD-27). This record requires only step 4: the next turn starts after the previous turn session has ended.
- **Two loops on one run.** Each loop runs its turns one after another. Two loops started on the same run — by two starts, or by a scheduler while a loop still runs — could run two turns at once. Preventing that is the lock of #4 §2e (rest of OD-17), which is not defined here.
- **What starts the loop.** A person or a CI starts it through a command-line entry of the package; the form of that entry is the code task's. A loop that died itself, for example on a machine restart, is started again by whatever started it: by hand (UC-2, UC-4) or by an OS schedule — the "cron 재기동" of UC-3 and S2 step 3. A schedule then starts the loop, not a turn. Whether the loop also calls the start function of ADR-0115 for a new instance is not decided; the caller of the start stays open.
- **Modes.** The same loop serves both modes.
  - **Autonomous (UC-3).** The turn session is a non-interactive `claude -p` session (cited: S2 step 1, "CI가 `claude -p`로"; UC-3, actor "CI / 헤드리스 배치").
  - **Checkpoint (UC-2).** How a gate stops a turn is not decided. It rides on the gate layer: the rest of OD-18, #8 M3, and OD-3 / #5 A-5, which is owner-only. Two forms stay possible, and this record serves both:
    - the checkpoint turn session is interactive and a permission prompt is the gate (UC-2 비고): the session waits in place, and the turn does not end at the gate. How such a session ends at the end of its round, so that step 4 of the loop goes on, and the trust dialog it shows for a directory not yet trusted (R10), are not decided; they go with the gate layer;
    - the gate ends the turn session (decision 2 (ii)): the loop returns once the run's files say the run waits, and after the user's input the run goes on (UC-2 step 3) when the loop is started again. How the input reaches the run, and what starts the loop then, are not decided.
- **The loop is no FR-10 tool** (as ADR-0115 decision 3): it is not in the registry, and no agent calls it.
- **Why a layer-2 loop:**
  - Starting the next session is a fixed step that needs no judgement, so this record keeps it outside a model. That is this record's own reasoning, by analogy only: #4 §3a revision condition 4 says such steps are not made sub-agents ("subagent화하지 않음"), and it does not speak of the Round-Manager's own steps (as ADR-0115 Alternatives (b) notes).
  - It works with no session alive between turns, which neither `/loop` (R6, R7) nor a chain of sessions does (Alternatives).
  - Its rules are code that tests check against a stub `claude` (D16; CLAUDE.md D12).

### 4. Where a turn session runs (c, first half)

- **The session directory lies outside the source checkout and outside the data checkout. None of its ancestor directories holds a `CLAUDE.md`, `CLAUDE.local.md` or `AGENTS.md`, of whatever origin, or a `.claude/` other than the runtime user's own configuration directory** (R1; what loads from that user directory is runtime acceptance item (ii)). Before each turn, the turn loop puts into it the definition as it then is in the source checkout (decision 5) and the server configuration (decision 6). It replaces whatever definition the directory held before. The turn session starts with this directory as its working directory.
- **Why not the root of the source checkout.** A session there would load the development driver's files as the runtime's (F6, K10, R1 to R4):
  - the driver's `CLAUDE.md`;
  - the rules of its `.claude/settings.json` — its deny list, and its allow list once the folder is trusted (R10) — and the guard hook DRIVER §1-5 plans there, which refuses to start `claude` (the runtime's coder calls are `claude -p` — C-7 ③);
  - its agents and skills.
  It would also share the driver's auto memory (R8).
- **Why not a subdirectory of the source checkout.** The ancestor `CLAUDE.md` loads (R1). Agents and skills are scanned up to the repository root (R2, R3). `settings.local.json` is read at the repository root (R4). Auto memory is shared (R8).
- **Why not the data checkout.** At its root the definition files would put source into the data repository (#4 §2b; #5 A-1), and a commit step of the run could take them in. In a subdirectory of it, the scan up to the repository root (R2, R3), the root `settings.local.json` (R4) and the shared auto memory (R8) apply as in the source checkout.
- **Left to the code task.** The location, the name, whether the directory is made per turn or per run, and its removal. One constraint holds: **nothing a run needs in order to go on lives only in the session directory** (NFR-1; #4 §1; the owner's invariant "agent-memory 전체를 삭제해도 재개(FR-6)·랭킹(FR-7)·감사(NFR-2)가 성립해야 한다", https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5138931194). Auto memory or agent memory kept there may be lost, and that invariant allows it.
- **Agent memory is not settled.** The agreed data-layer policy places per-agent know-how in `.claude/agent-memory/<agent>/`, "휘발 허용", and starts the promotion ladder there (cited: #4 §2 of https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5138366881; OD-24). In a turn session, a project-scope `.claude/agent-memory/` is the session directory's. So a directory made per turn loses it at every turn, and one made per run loses it with the run. **Where agent memory is kept across turns and runs, and how it reaches the promotion ladder, is not decided here** (OD-24, Boundaries). Decision 4 neither settles it nor rules out keeping it elsewhere.
- **Workspace trust.** A `-p` session never shows the trust dialog. In a directory never trusted, it does not use the `permissions.allow` rules of the directory's `.claude/settings.json`, the frontmatter hooks of its sub-agents or their inline `mcpServers`; it does use the hooks in its settings files (R10). Trust is bound to the directory's path, which bears on whether the directory is made per turn or per run. **How a turn session is given its permissions and the agents' allowlists is not decided.** Candidates are a trust record in the runtime user's `~/.claude.json`, `--settings`, `--allowedTools` and the permission mode (ADR-0054 K5, K6). This record writes nothing into the runtime user's configuration and presumes no such write (Boundaries).
- **How the session reaches the run's files** — for example `--add-dir` of the data checkout — is the definition's and the code task's. **The source checkout is never added with `--add-dir`**: its agents and skills would load (R9).

### 5. Where the definition lives (c, second half; the OD-23 point)

- **The runtime's layer-1 definition is kept in the top-level directory `orchestration/` of this repository**, apart from the driver's `CLAUDE.md` and `.claude/`. It holds the Round-Manager's prompt and, if any, the agent definitions, skills and hook settings of the turn session. The name is #5 A-12's word for layer 1 ("orchestration = Claude Code prompts/skills/agent definitions (Markdown)"). Keeping layer 1 in this repository is cited (#5 A-12 context; CLAUDE.md "세 층 모델").
- **Naming rule:** no file under `orchestration/` is named `CLAUDE.md`, `CLAUDE.local.md` or `AGENTS.md`, and no directory under it is named `.claude`. A driver session that reads or edits those files would otherwise load the runtime's instructions or skills on demand (R1, R3).
- **Files get the names that Claude Code reads only in the session directory**, where the turn loop puts them: a project `CLAUDE.md`, `.claude/agents/`, `.claude/skills/` and `.claude/settings.json`. The definition task decides the internal layout of `orchestration/` and which file becomes which.
- **Why a copy per turn rather than the files in place.** A turn session sees the definition as it was when its turn started. An edit in the source checkout during a turn does not reach the running session, R5 notwithstanding. The next turn picks the edit up (decision 2).
- **What it does not settle.** The roster, the sub-agents, their `tools` and allowlists stay with the rest of OD-23. Whether an agent of the session may edit its own copy is the isolation means (OD-8, OD-14).

### 6. How the turn session is given the MCP server

- **The turn loop writes a server configuration file into the session directory.** It names the package's MCP front (ADR-0010 decision 3). The turn session starts with `--mcp-config` naming that file, together with `--strict-mcp-config` (K4). This is the way the runtime self-check gives the server to its session (cited: ADR-0054 decisions 4 and 9). **Each turn therefore has its own server process**, started with its session, and a replaced tool layer takes effect at the next turn (ADR-0010 decision 7).
- **No `.mcp.json` is used**, so the approval of F1 does not arise for a `-p` session (K10). **This record decides and presumes no approval by the owner.**
- **Not decided here:**
  - whether sub-agents reach the tools by inheritance, by a `tools` list or by an inline `mcpServers` server (F3; OD-23);
  - further servers, such as the external-reference adapters (OD-12);
  - how the server is given its data root (the code task's);
  - whether an interactive checkpoint session would prompt for a server given this way (decision 3).

### Walk-through

| Situation | What follows |
|---|---|
| A new first-case run (its `instance.json` written by the function of ADR-0115); a person starts the loop | The loop prepares the session directory and starts the turn session of round 0. Which side writes the first `STATE.json` stays OD-8 ⑩. After the write that ends round 0, the session ends, and the loop starts the turn of round 1 |
| The turn session dies in round 3 after `board_done` | The loop's wait ends. What it does next is open (decision 3). The next turn is a new process: it finds `round` 3 and goes on, skipping finished substeps (ADR-0012 decision 3; #4 §3b) |
| The machine restarts during a turn | No loop runs. The user or an OS schedule starts the loop again, and the next turn goes on as above. A second loop on the same run is the lock's matter (rest of OD-17) |
| Checkpoint mode: the Round-Manager reaches a gate, and the gate layer ends the session there | The turn ends before its round ends (decision 2 (ii)). Once the run's files say "waiting" (a member not yet defined), the loop returns; after the user's input the loop is started again. If the gate is instead a permission prompt in an interactive session, the session waits in place (decision 3) |
| `orchestration/` is edited during a turn | The running session keeps its copy; the next turn copies the edited definition (decisions 4, 5) |
| A developer edits `orchestration/` in a driver session at the repository root | No runtime instruction file loads into that session (decision 5, naming rule) |
| A turn session schedules a self-paced `/loop` | The `-p` run waits for its wakeups (R7), so the turn would not end. The definition carries rounds by turns and does not use `/loop` or the scheduling tools for that |

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| a | Several turns in one session process (UC-3 `/loop`) | The context is not cleared between turns (#4 §1). The `CLAUDE.md` files and the MCP server stay those of the session's start (R1; ADR-0010 decision 7), so NFR-7 ① would not hold. Tasks fire only while the session is running and idle and expire after 7 days (R6). |
| a | A turn may span several rounds | Contradicts "turn ≡ Round" (#4 §3). |
| b | UC-3's `/loop` as what starts each turn | Starts no new process (R6, R7): the row above. |
| b | An OS schedule starts each turn at fixed intervals | Rounds differ in length, so the interval either leaves the run idle or fires while a turn still runs. Every firing then needs the lock of OD-17, which is undefined, to skip. A schedule keeps its place as what restarts a loop that died (decision 3). |
| b | The user by hand for every turn | Not the "무정지" of UC-3. In checkpoint mode the user starts the loop again after a gate, which keeps the user where UC-2 puts them (decision 3). |
| b | Each turn session starts the next one before it ends | The next session would be started by a model step that needs no judgement (this record's reasoning, decision 3), as a child of the dying process. A session that dies starts nothing. |
| c | The session runs at the root of the source checkout | It would load the driver's `CLAUDE.md`, settings, planned guard hook, agents and skills, and share its auto memory (decision 4). |
| c | The session runs in `orchestration/`, a subdirectory | Ancestor `CLAUDE.md`, agents and skills up to the repository root, and the root `settings.local.json` and auto memory, would still load (R1 to R4, R8). |
| c | The definition under the repository's own `.claude/` beside the driver's | It is the same tree as the driver's and loads in every driver session (R2, R3). |
| c | Definition files named `CLAUDE.md` or kept in `.claude/` inside `orchestration/` | They would load on demand in driver sessions (R1, R3). |
| c | The definition passed only by flags (`--system-prompt-file`, `--agents`, `--settings`) from the source checkout | Possible, but the session still needs a working directory away from the driver's files. Skills have no dedicated flag; they would come through `--plugin-dir` or the `.claude/skills/` of an `--add-dir` directory (R9). Kept open as a later form inside decision 4 if the definition task needs it. |
| 6 | A `.mcp.json` in the session directory | Connects with no prompt under `-p` (K10), but not exclusively, and differs from the way the self-check exercises (ADR-0054 decision 9). |
| 6 | Leave the way open | The code slice of the loop would wait on it, and ADR-0054 decision 9's unshown list would stay as long. |

## Consequences

- **Code slices it makes possible** (code mode; names, modules and entries are the code tasks'):
  - (1) **The turn loop** of decision 3 and its command-line entry. It takes from its caller a predicate, asked before every turn, that answers "is a further turn to run?", until a record of OD-8 defines the member, and it is tested against a stub `claude` that the tests write (D16).
  - (2) **The preparation of the session directory**: the copy of decision 4 and the server configuration file of decision 6.
  - (3) **The definition** under `orchestration/`. These are the next P2-1 slices, with the Round-Manager's prompt and the round-0 procedure.
- **Runtime acceptance items** (D16): facts only a logged-in `claude` on a C-7 machine can establish. **Nothing was tried, and nothing is required of the development machine.**
  - (i) A `claude -p` session started in a session directory as decision 4 builds it loads that directory's `CLAUDE.md`, `.claude/agents/`, `.claude/skills/` and `.claude/settings.json`, and no file of this repository.
  - (ii) Which files of the runtime user's `~/.claude/` such a session loads — the user `CLAUDE.md`, agents, skills, settings and hooks — and what the flags the definition picks exclude of them.
  - (iii) A sub-agent defined in the session directory's `.claude/agents/` is found, and the main session of a `-p` run delegates to it.
  - (iv) `--mcp-config` with `--strict-mcp-config` gives the `hilclaw` server to the main session of every turn, and the server process started from the session directory finds the package; and whether sub-agents reach its tools by inheritance. That an inline `mcpServers` server of a sub-agent is not used in a never-trusted directory is documented (R10) and is no such item; whether `--strict-mcp-config` also drops it in a trusted directory is.
  - (v) A `-p` turn session that started no background work exits after the Round-Manager's last reply (R7), so the loop's wait ends.
  - (vi) The exit status of a turn session tells a session that ended well from a failed one, if the loop comes to rely on it (R7; ADR-0054 K8).
  - (vii) Whatever means a later record picks for permissions and allowlists (decision 4, "Workspace trust") lets a `-p` turn session call the tools it is meant to call and nothing else.
- **Not edited and now less exact.** Found by a search of `ARCHITECTURE/` for "process boundary", "프로세스 경계", "/loop", "cron", "Registration", "gives the server" and "gives it to its agents". For the runs of decision 1, these say that the point is open, and it now is answered. Each stays true of what is still open:
  - Requirements NFR-7 ①, *전제* "라운드 경계가 프로세스 경계여야 성립하며(OD-18)": for the first case, it holds by decision 2. The reason the OD-18 proposal gave ("`.claude/agents/`가 세션 중 재탐지되지 않으므로") is not what R5 says.
  - StandardScenarios S2 step 1 ("CI가 `claude -p`로 … instance를 기동한다"): the CI starts the loop, which starts the `claude -p` sessions. S2 step 3 ("cron 재기동이 마지막 commit 지점에서 이어간다"): cron restarts the loop, and the loop starts the next turn.
  - ADR-0010: decision 7 ("Whether a round boundary is a process boundary … is #8 M4 and stays open"; "Which of these ways is used is not decided here"), Limits ("Registration is not done or chosen by this record"), Consequences ("Registration") and Boundaries ("round boundary = process boundary (#8 M4, UC-3 `/loop`)"). For the main session of a turn, the way is decision 6.
  - ADR-0015: Status and Boundaries ("round boundary = process boundary (#8 M4)").
  - ADR-0054: decision 9 ("How a run gives it to its agents … **stays open**") and its list of what a pass leaves unshown, for the main session's part; Boundaries ("**The way a run gives the server to its agents**").
  - The #4 §2 data-layer row for per-agent know-how (`.claude/agent-memory/<agent>/`, an issue comment, not edited): for a turn session that place is inside the session directory, and whether it persists is open (decision 4, "Agent memory is not settled").
  - CLAUDE.md "세 층 모델" (layer 1 = "CLAUDE.md·스킬·`.claude/agents` 정의"): the files of those names at the repository root are the development driver's; the runtime's layer 1 is under `orchestration/` (decision 5).
  - The list is not claimed to be complete.
- **Edited with this record:** UC-3 step 1's parenthesis now names the loop for the first case. No other UsageCases sentence became false.
- **Follow-up for the integrator** (not done here):
  - #8 M4: its resolution for the first case is decisions 2 and 3, with UC-3 step 1 already edited.
  - The NFR-7 ① wording and S2 steps 1 and 3 listed above.
  - The #4 body's statement of the process boundary (§3).
  - The CLAUDE.md "세 층 모델" sentence and the #4 §2 agent-memory row listed above.
- **A-13 reading.** Document mode. No code, test, setting or dependency changes. **No data-plane schema change**: no member, file, kind or version is added; the member that step 1 of decision 3 reads is named as open, not defined. Later changes under `orchestration/` are not in A-13's document-mode list, so they take the code mode. Whether to add the directory to that list is not decided here, and CLAUDE.md is not edited.
- **The cost, plainly.** Every turn starts a session, its definition and its server anew, which takes seconds and the tokens of the definition (NFR-5). A round that is cut short pays this again. The copy of decision 4 also means that the definition a turn ran with is that of the source checkout at the turn's start, not necessarily the commit `instance.json` records. Which version made which round is NFR-7 ③ and OD-11, and this record records nothing of it.

## Boundaries (not decided here)

- **Hooks**: which exist and what they check, where a check before a call is placed, default-FAIL and the kill switch (rest of OD-18; PLAN P2-4). Decision 5 says only where hook settings would live.
- **Gates**: the gate list and what a gate checks (OD-3; #5 A-5 — owner-only), and the gate layer (permission UI or hook; #8 M3). This record says only that a turn may end when a run waits (decision 2 (ii)), depending on the gate layer (decision 3).
- **The member that says a run is over, stopped or waiting**, and the other members of `STATE.json` (rest of OD-8; ADR-0012 Boundaries); **budget enforcement** and termination (OD-19).
- **The lock** against two turns or two loops at once, fencing, and what the loop does after a failed turn (rest of OD-17; OD-10; OD-27).
- **The roster** beyond the Round-Manager being the main conversation, and the per-agent allowlists (rest of OD-23); **how the coder is started** (PLAN P2-2).
- **Agent memory across turns and runs**: where per-agent know-how is kept once the session directory is gone, and how it reaches the promotion ladder (OD-24; #4 §2).
- **How a turn session gets its permissions** under the workspace-trust rules of R10 — a trust record, `--settings`, `--allowedTools`, the permission mode — and any write into the runtime user's configuration.
- **Round 0**: its content and the baseline (later P2-1 slices; OD-28). **OD-18 sub-question ⑯ (가)** — whether the self-check runs again at a resume or at a round boundary — is not settled by decisions 2 and 3. Every turn starts a new server by the checked way, but whether the loop runs the check before a turn is the round-0 slice's question.
- **The commit step** and who makes it (OD-8 ⑪), including whether a turn that ends before its round ends commits. #5 A-3 makes a local commit at "매 턴(=Round) 종료 시" an invariant; this record reads that sentence neither as "at every turn end" nor as "at every round end". **Resume from a chosen point** (UC-4; OD-8 ①).
- **How a run waits** for the user's permission to change the toolchain or the environment (OD-8 ㉝ (가)).
- **The CLAUDE.md invariant list** of OD-18, which the definition would carry.
- **Runs outside ADR-0076 decision 1**; the `--bare` default and a login that expires during a run (⑯ (바)); the credential form for unattended runs (owner). Decisions 4 and 5 rest on the discovery of a non-bare `-p` session; if `--bare` becomes the default of `-p` with no way to leave it (K11), they are reopened, and the flag form of the Alternatives is the first to weigh.
- Any change to an earlier record, to `hilclaw/`, to tests, to CI, to `.claude/`, to CLAUDE.md, to any settings file or to the `HIL-Claw-data` repository; any new external dependency.

## References

- [Requirements](../Requirements.md): FR-1, FR-10, NFR-1, NFR-5, NFR-7 ① ③, C-7; register rows OD-3, OD-8, OD-11, OD-17, OD-18, OD-19, OD-23. [OpenDecisionProposals OD-18](../OpenDecisionProposals.md#od-18) (the proposal bullets; ⑯), [OD-23](../OpenDecisionProposals.md#od-23), [OD-8](../OpenDecisionProposals.md#od-8) (①, ⑩, ⑪, ㉝). [UsageCases](../UsageCases.md) UC-2, UC-3, UC-4. [StandardScenarios](../StandardScenarios.md) S2.
- ADR-0001 (record format); ADR-0004 (path table; decisions 2, 4); ADR-0010 (F1, F3, F6, F7; decisions 3, 7; Limits; Consequences; Boundaries); [ADR-0012](ADR-0012-od8-runtime-state-file.md) (decisions 2, 3, 6; Boundaries); [ADR-0015](ADR-0015-od18-tool-contract-frame.md) (Status; Boundaries); ADR-0054 (K4, K5, K6, K8, K10, K11; decisions 4, 9; Boundaries); [ADR-0076](ADR-0076-od8-instance-start-required-members.md) (decision 1); ADR-0115 (decisions 2, 3).
- #4 body §1, §2e, §3, §3a, §3b, §3c; §3a revision https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5138366881 ; agent-memory confirmation https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5138931194 ; #7 pointer https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139248800 ; #7 supplement §2(8) https://github.com/myungjoo/HIL-Claw/issues/7#issuecomment-5139423949 ; #8 M3, M4.
- #5 A-1 · A-3 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5537233759 · A-12 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5946779596 · B-6 · HQ-0006 answer https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6135246858 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 .
- Claude Code documentation, read 2026-10-19: https://code.claude.com/docs/en/memory · https://code.claude.com/docs/en/sub-agents · https://code.claude.com/docs/en/skills · https://code.claude.com/docs/en/settings · https://code.claude.com/docs/en/permissions · https://code.claude.com/docs/en/scheduled-tasks · https://code.claude.com/docs/en/headless · https://code.claude.com/docs/en/cli-reference
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §1-5, §9; PROCESS/PLAN.md P2-1, P2-2, P2-4; CLAUDE.md "세 층 모델", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차"; task T-0329.
