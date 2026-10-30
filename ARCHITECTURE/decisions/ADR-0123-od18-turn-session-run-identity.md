# ADR-0123: How a turn session of a first-case run learns which run it carries — the command-line entry puts the run id into the prompt of every turn, the session is handed no place of the run, and the run it names is the one run the turn writes into and names in its tool requests (part of OD-18 and OD-23, for the runs of ADR-0120 decision 1)

## Status

- **Accepted on 2026-10-19** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it.**
- **Two kinds of content.** What an owner decision, an agreement of #4, a requirement, a use case, an accepted record, a code docstring or a documentation page says is **cited**, with its source named. **Everything else is this record's own**: the scope, the channel and the side that hands the run over, what the session does with it, the readings marked as such, and every weighing.
- **The owner-sentence search.** Searched: the body of #4 and its 6 comments; the body of #5 and the 38 of its 194 comments whose text holds no "posted by driver" marker; the bodies and comments of #7 (2) and #8 (6). Terms: run_id, run id, instanceID, 어느 run, which run, prompt, 프롬프트, 환경변수, 환경 변수, environment, env var, session, 세션, Round-Manager, STATE.json, 진입점, 단일 진입점, entry point, argument, 인자, working directory, cwd, 작업공간, workspace, turn, 턴. **No owner sentence says how a turn session, or any session of the runtime, learns which run it carries.** The sentences found that touch the point, each read for what it says and no further:
  - **S1** — #4 body §1 ([합의]): "항상 작은 `STATE.json` 한 개를 진입점으로(현재 라운드, `best_ref`, `next_action`, `budget_spent`, gate 상태). 거기서 **참조된 산출물만 선택 로드**. '전 디렉토리 스캔' 금지." It says what a turn reads first and that it does not scan; it does not say how the turn knows whose `STATE.json` that is.
  - **S2** — #4 body §2: "`instanceID`는 기존 용어 **`run_id`로 통일**(instanceID ≡ run_id)", and the layout line "`<run_id>/ # = instanceID`". It names the run; it does not say how a turn is told it.
  - **S3** — #4 body §3 and §3c ([합의]): "한 Round를 **하나의 Agent Session(Round-Manager)** 이 관리"; the Round begins with "read STATE.json (+ best_ref, next_action) # 진입점, 작게". What the session reads, not what it is given.
  - **S4** — #4 comment https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139876430, under "확정된 전제 2가지 (오너 판단)": "1. **읽기 제한은 채택하지 않는다.**" and "2. **프롬프트만으로 쓰기 구역을 주는 것은 너무 약하다.** … 프롬프트 위반은 **조용히 실패**해 오염된 레코드가 탐지 없이 지식베이스에 유입된다." **This record treats both as owner sentences** (the stricter classification). They are about the write zones of agents, not about how a session learns its run. They bear on decision 4: the rule there restricts no read (premise 1), and it is no write protection of the run (premise 2). The same comment's "후보 ① 요지" — "쓰기 루트는 라운드로 파라미터화하되 에이전트가 선택 불가 — supervisor가 주입" — is a candidate registered under OD-8, not a decision, and nothing here rests on it.
  - **S5** — #5 A-1 detail 2 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5046307826): "`hilclaw.config.json` — `data_repo.url` + `data_repo.local_path`, 환경변수 override 가능." It is about how the package finds the data root, which is how the data root reaches the MCP server today (decision 2); it says nothing of the run.
  - **S6** — #5 B-6 point 3 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944087839): "a Claude Code session acts as the **main orchestrator** (agent), spawns **sub-agents**, and those sub-agents invoke the **Claude Code CLI** (`claude -p`)". What the session is, not what it is given.
  - The answer to HQ-0006 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6135246858): the driver and the runtime are different programs. It governs how this record is verified (D16), not the point.
- **Not an owner-only item.** The point is design-level: what a turn session is given (OD-18, the round boundary) and one input of the Round-Manager (OD-23). Nothing here needs #5 A or B, C-6, OD-25 or OD-3.
- Answers, **for the runs of decision 1 only**, one point of **OD-18** (what a turn session of ADR-0118 is given besides its definition and its server) and one point of **OD-23** (the Round-Manager's input that names its run). **OD-18 and OD-23 keep their status.** No sub-question is registered or answered.
- **No member, file, kind, value or version of the data plane is added or changed**, and no validator changes. **It is a record, not code**: no `claude` process was started for it, and no fact below was tried in a live session (D16).
- It builds on [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decision 8), [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decisions 6, 8), [ADR-0015](ADR-0015-od18-tool-contract-frame.md) (decisions 3, 4, 7), [ADR-0027](ADR-0027-od8-run-id-form.md) (decisions 1, 2), [ADR-0115](ADR-0115-od8-instance-start-performer.md) (decisions 1 to 3), [ADR-0118](ADR-0118-od18-round-process-boundary.md) (decisions 1 to 6), [ADR-0120](ADR-0120-od8-first-state-file.md) (decisions 1 to 4) and [ADR-0122](ADR-0122-od19-turn-loop-open-states.md) (decisions 1, 5). **If one of them is reverted, this record is revisited with it.**
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **The open point** (cited: `hilclaw/turn_start.py`, module docstring): "**Open**: how a turn session learns which run it carries. No record decides it, so the prompt does not name the run and nothing else hands it over." The entry `python -m hilclaw.turn_start <run_id>` knows the run id; it starts every turn through `hilclaw.turn_loop.run` with the fixed prompt "Carry out the next turn of your run as your instructions say."
- **Why it must be answered now.** The Round-Manager of the round-0 turn reads `STATE.json` and, in a fresh run directory, writes the first one (cited: ADR-0120 decision 2). The request of a journaled tool carries `run_id` (cited: ADR-0015 decision 4). Neither can be written into the Round-Manager's prompt while the session does not know its run.
- **What a turn session gets today** (cited: `hilclaw/turn_loop.py`, module docstring; ADR-0118 decisions 4 to 6): a session directory made per turn outside both checkouts, holding a copy of `orchestration/` and the server configuration file; the command line `claude -p <prompt> --mcp-config <file> --strict-mcp-config` and nothing else; "the environment of the calling process unchanged". The server entry of that file has `env` exactly `hilclaw.config.ENV_LOCAL_PATH` with the data root, "so the server names the same data root whatever its working directory is".
- **The prompt rule** (cited: `hilclaw/turn_loop.py`): the prompt "is one line of ASCII letters, digits, spaces, `.`, `,` and `_`: on Windows the `claude` found may be a command script, whose arguments pass through the command interpreter" (`_PROMPT = [A-Za-z0-9 .,_]+`).
- **The run id.** A valid `run_id` matches `[a-z0-9][a-z0-9_-]{0,63}` (cited: ADR-0004 decision 8). An id the system builds is `<time>-<random>` with one hyphen, for example `20261009t012331z-9f3a6c1e0b7d4a52` (cited: ADR-0027 decision 2). So a prompt that holds a built id is refused by today's rule. The start of ADR-0115 returns the id it built to its caller; who that caller is stays open (cited: ADR-0115 decisions 1, 2).
- **No access control** (cited: ADR-0010 decision 8): "whoever can start the command or connect the server can call every tool"; ADR-0015 decision 7: "whoever can call a tool can present any `run_id` and any identity". The data root "is never a member of a request, and no calling agent chooses it" (cited: ADR-0015 decision 3).
- **What reaches the run's files is open** (cited: ADR-0118 decision 4): "How the session reaches the run's files — for example `--add-dir` of the data checkout — is the definition's and the code task's." How the Round-Manager reaches `hilclaw.run_state_file.replace` is open (cited: ADR-0120 decision 2; OD-23, OD-18).

## Decision

A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope

- **The runs of ADR-0120 decision 1** (new first-case runs of ADR-0076 decision 1 whose `instance.json` the start function of ADR-0115 writes), **driven by the turn loop of ADR-0118 decision 3 through its command-line entry `hilclaw.turn_start`**. Resumed, continued or branched runs (OD-8 ①), runs started in any other way and every other run are outside; nothing here is required or allowed of them.
- **Turn session**, **turn loop**, **session directory** and **definition** are the terms of ADR-0118 decision 1. **The entry** is `hilclaw.turn_start`. **The run** of a turn is the run whose id the entry was given.

### 2. (a) What the session learns: the run id, and no place

- **A turn session learns the `run_id` of its run, exactly as the entry was given it, and nothing else about the run.** It is not told the round, the phase or any other state: those it reads from `STATE.json` (S1, S3).
- **The session is not handed the place of the run** — neither the data root nor the run directory. Reasons:
  - The tools that need the data plane already get the data root from their front process and never from a request (cited: ADR-0015 decision 3); the server of a turn gets it through the server's environment (Context). A session that names its run by id therefore reaches every tool it is given.
  - Whether the Round-Manager itself needs the place depends **only** on how it will read the run's files and reach `replace`: through a means that takes a `run_id` (such as a tool), it needs no place; through its own file tools (such as `--add-dir` of the data checkout, ADR-0118 decision 4), it needs the run directory as a path. **That means is not chosen here** (OD-23, OD-18; Boundaries). A record that chooses a means needing the place says how the place reaches the session.

### 3. (b) The channel: the prompt, written by the entry, the same in every turn

- **The entry puts the run id into the prompt** it passes to `hilclaw.turn_loop.run`, and that prompt is the prompt of every turn the call starts (cited: `run`, "`prompt` is the one-line prompt of every turn"). The prompt holds the id once, unchanged, beside fixed text; the wording and where the id stands are the code slice's, and the definition (`orchestration/round-manager.md`) says how the Round-Manager finds it there. The two change together.
- **The same channel and the same value in every turn of a run.** The prompt is built from the id alone, so every turn of one start, and every start of the same run through the entry, gets the same text.
- **The side that hands it over is the entry**, which alone knows the run id. The loop stays as it is in kind: it passes its caller's prompt to each session and knows no run (cited: ADR-0118 decision 3; `run`). The definition stays the same for every run.
- **For the code slice** (a consequence, not a code edit): the loop's prompt rule refuses `-`, which a built id holds (Context). The slice widens the rule to admit `-`, not as the first character of the prompt, so that the prompt can never read as an option; whether `-` passes the Windows command interpreter unchanged is the slice's to check against a stub. The entry already refuses an invalid id before anything is read (cited: `hilclaw/turn_start.py`, `bad_usage`), so every prompt it builds holds a valid id.
- **When the run id is missing or invalid.** If the Round-Manager finds no run id in its prompt, more than one, or one that does not match the pattern of ADR-0004 decision 8, it reports that in one line and ends the turn, having written nothing into any run and made no tool request naming a run. What it does when the id is valid but no run directory or no `instance.json` is there is ADR-0120 decision 3's (it writes no `STATE.json`); the loop starts no turn there (cited: ADR-0122 decision 4).

### 4. (c) What the session does with it

- **The run its prompt names is its own run.** Its `STATE.json` is the one the turn reads as its entry point (S1, S3). It is the only run whose files the turn writes, and the only `run_id` that the turn's tool requests carry, journaled ones included (ADR-0015 decision 4). Sub-agents of the turn work for that run as well; how the Round-Manager passes the id to them is the roster's (OD-23).
- **No read is restricted.** Reading other files of the data plane — the knowledge tree for the cases of FR-18, for example — is not limited by this record (S4, premise 1).
- **This record adds no access control.** The rule above is part of the definition that the Round-Manager follows; no tool, front or loop checks it, and a session can still present any `run_id` (cited: ADR-0010 decision 8; ADR-0015 decision 7). By S4 premise 2, a rule given by prompt alone is not enough as a write zone; so this rule is **not** counted as the run's protection against writes into another run. Such a protection is the isolation means (rest of OD-8; OD-14) or a hook that compares a request's `run_id` with the session's run (rest of OD-18, PLAN P2-4). What such a check would need is in the Alternatives (hook visibility).

### 5. (d) What it keeps from earlier records

- **The loop** makes no judgement, calls no model, is no FR-10 tool and writes nothing into the run (cited: ADR-0118 decision 3; ADR-0122 decision 1). It is unchanged in kind: it still passes one prompt to each session. **The entry** composes a fixed text with the id it was given, which is no judgement either, and writes nothing (cited: `hilclaw/turn_start.py`, "**Kept from ADR-0122 decision 1**: the entry writes nothing into the run or anywhere else on the starter's behalf").
- **Nothing a run needs lives in the session directory** (NFR-1; ADR-0118 decision 4). The run id is an argument of the entry and of the session's command line, not a file; nothing is added to the session directory.
- **`STATE.json` stays the single entry point of a turn** (S1). The prompt names whose entry point it is and carries no state.
- **The definition stays one for every run** (ADR-0118 decision 5): no run's data enters `orchestration/` or its copy, so a component can still be replaced between two turns (NFR-7 ①) without touching any run.

### Walk-through

| Situation | What follows |
|---|---|
| A person runs `python -m hilclaw.turn_start 20261009t012331z-9f3a6c1e0b7d4a52` on a fresh run | The entry builds the prompt with that id; the loop starts the round-0 turn with it; the Round-Manager reads the id from its prompt, finds the run directory fresh and writes the first `STATE.json` there (ADR-0120 decision 2) |
| The round-0 turn ends and the loop starts the next turn | The next session gets the same prompt, reads the same id and goes on with the round `STATE.json` names (ADR-0012 decision 3) |
| The loop dies and is started again on the same run | The new start builds the same prompt from the same id |
| The entry is given an invalid id | `bad_usage` before anything is read; no turn starts (cited: `hilclaw/turn_start.py`) |
| A definition or a person passes the loop a prompt without a valid id | The Round-Manager reports in one line and ends the turn, writing nothing into any run (decision 3) |
| A sub-agent calls a tool with another run's id | Nothing in the tool layer stops it (decision 4); detection or prevention is a later hook or the isolation means |

## Alternatives considered

| Alternative | Prompt rule | Hook visibility | NFR-7 ① (replaceable definition) | NFR-1 (session directory) | A later lock or resume | Why not |
|---|---|---|---|---|---|---|
| **(1) The run id in the prompt, written by the entry** (adopted) | Must admit `-` (decision 3) | A tool-use hook reads the request as `tool_input` and the calling agent (ADR-0010 decision 6); whether and how any hook sees the prompt is not established here | Kept: the definition is run-free | Kept: nothing written there | The entry holds the id, which a lock or a resume can key on; a resume would hand its id the same way | — (cost: the prompt rule change, and a check on `run_id` by a hook would need a second channel) |
| (2) An environment variable of the session, set by the entry or the loop | Untouched | A hook command started by the session might inherit its environment; that is unverified and would be a runtime acceptance item | Kept | Kept | As (1) | The Round-Manager cannot read the environment without a shell or a tool, and in-process agents may have no shell (OD-8 candidate ① item 4; ADR-0010 decision 6). Kept open as a **second** channel for a later hook record, with the same value from the same side |
| (3) A file in the session directory written by the entry or the loop | Untouched | A hook command could read the file from the session directory (unverified) | Kept, but a third kind of file beside the definition and the server configuration (ADR-0118 decisions 4 to 6) | Holds, since the file is a copy of the entry's argument, but the loop then writes run data where ADR-0118 puts only the definition and the server configuration | As (1) | The Round-Manager spends a read to learn it, and an agent of the session could edit it during the turn (the isolation means is open — ADR-0118 decision 5) |
| (4) The definition copy carries the run id (a templated `CLAUDE.md`) | Untouched | As (3) | **Broken**: the copy is no longer the definition "as it then is in the source checkout" (ADR-0118 decision 4), and `hilclaw.turn_definition.put` copies byte for byte | Holds, as (3) | As (1) | It mixes run data into layer 1 |
| (5) The server's environment, with a tool that reports the run | Untouched | A tool-use hook reads the request and the calling agent (ADR-0010 decision 6), not the server's environment | Kept | Kept | The loop would have to know the run to write the server configuration | It adds a tool to the registry and its contract (OD-18 records), and a tool answering "the run" invites a default for `run_id`, which ADR-0015 decision 4 keeps in the request |
| (6) The Round-Manager finds its run by listing `runs/` | Untouched | — | Kept | Kept | Ambiguous once two runs exist; a resume could not choose | "'전 디렉토리 스캔' 금지" (S1) |
| (7) The prompt names the run directory as a path | A path holds `/`, `\`, `:` and possibly spaces; the rule would widen far more | As (1) | Kept | Kept | As (1) | It hands the session a place, which point (a) leaves to the means of OD-23 and OD-18 |
| (8) Leave it open | — | — | — | — | — | The round-0 part of the Round-Manager prompt (PLAN P2-1) and the P2-5 run cannot be written without inventing it |

## Consequences

- **The code slice it enables** (code mode, a later task; names and wording are its own): `hilclaw/turn_start.py` builds the prompt from the run id and passes it to `hilclaw.turn_loop.run` instead of the fixed `PROMPT`; `hilclaw/turn_loop.py` widens its prompt rule to admit `-`, not as the first character (decision 3), and its docstring follows; `orchestration/round-manager.md` gains the step of decision 3 — take the run id from the prompt, and if it is missing or invalid, report in one line and end — in the same slice, since the prompt and the definition change together (decision 3). Tested against a stub `claude` only, which can show the prompt it was given (D16). The slice corrects the "**Open**: how a turn session learns which run it carries" sentence of the `turn_start` docstring.
- **What the round-0 part of the Round-Manager prompt still waits on**: how the Round-Manager reads the run's files and reaches `replace` — the means that also settles whether it needs the place (decision 2; OD-23, OD-18); whether the self-check runs again at a resume or at a round boundary (OD-18 ⑯ (가)); the commit step (OD-8 ⑪). The step of decision 3 does not wait; it goes with the code slice above.
- **Less exact, not edited** (found by a search of `ARCHITECTURE/decisions/` and `hilclaw/` for "which run", "does not name the run" and "prompt"; follow-ups for the integrator and the code slice):
  - `hilclaw/turn_start.py` module docstring, "**Open**: how a turn session learns which run it carries. No record decides it, so the prompt does not name the run and nothing else hands it over", and `PROMPT` ("Carry out the next turn of your run as your instructions say."), which names no run.
  - `hilclaw/turn_loop.py` module docstring, "*The prompt* is one line of ASCII letters, digits, spaces, `.`, `,` and `_`", and `_PROMPT`: for the runs of decision 1 the prompt now holds a run id with `-`.
  - ADR-0122 Context ("it starts `claude -p` with a fixed prompt"): true of the code it observed; the prompt is now built from the run id.
  - ADR-0118 decision 3 ("Given one run, it repeats these steps"): the loop is given the run through its caller's prompt, and the run's files through the caller's predicate; it holds no run id itself.
  - The list is not claimed to be complete.
- **UsageCases and StandardScenarios**: no sentence becomes false. UC-2, UC-3 and UC-4 say nothing of how a turn is told its run.
- **A-13 reading.** Document mode. No code, test, setting or dependency changes. **No data-plane change**: no member, file, kind, value or version is added or changed, and no validator changes. The prompt is no file of the data plane.
- **Runtime acceptance items** (D16; nothing was tried, and nothing is required of the development machine):
  - ADR-0118 items (i), (iv) and (v) are used, not changed.
  - **New**, numbered after ADR-0118's (i) to (vii) and ADR-0122's (viii): **(ix)** a `-p` turn session started by the loop with the prompt the entry builds receives that text unchanged as its first user message — on Windows also where the `claude` found is a command script — and its Round-Manager takes the run id from it as the definition says.
- **The cost, plainly.** The rule of decision 4 is a model following a prompt; a slip writes into another run or names another run in a request, and nothing detects it until a hook or the isolation means exists (S4, premise 2). The prompt rule widens by one character.

## Boundaries (not decided here)

- **How the Round-Manager reads the run's files and reaches `replace`**, whether it then needs the place of the run, and **the roster** — sub-agents, how they get the run id, their allowlists (OD-23, OD-18).
- **The lock** of two loops on one run and fencing (rest of OD-17; #4 §2e).
- **Who calls the start of ADR-0115** and how its id reaches the entry (OD-8, OD-23).
- **Resumed, continued or branched runs** (OD-8 ①), and how such a run's turns learn their run.
- **The self-check at a resume or a round boundary** (OD-18 ⑯ (가)).
- **The commit step** (OD-8 ⑪).
- **Permissions and hooks**, including a hook that checks a request's `run_id` against the session's run and any second channel it needs (rest of OD-18; PLAN P2-4); the isolation means (rest of OD-8; OD-14).
- **Gates** (OD-3 — owner-only; #5 A-5).
- **Runs outside ADR-0120 decision 1** and turn sessions started other than by the entry.
- Any change to an earlier record, to FR or NFR text, UsageCases, `hilclaw/`, `orchestration/`, tests, CI, `.claude/`, any settings file or the `HIL-Claw-data` repository; any new external dependency.

## References

- [Requirements](../Requirements.md): FR-1, FR-13, FR-18, NFR-1, NFR-7 ①, C-7; register rows OD-3, OD-8, OD-14, OD-17, OD-18, OD-23. [OpenDecisionProposals](../OpenDecisionProposals.md) [OD-18](../OpenDecisionProposals.md#od-18) (⑯), [OD-23](../OpenDecisionProposals.md#od-23), [OD-8](../OpenDecisionProposals.md#od-8) (①, ⑪; candidate ①). [UsageCases](../UsageCases.md) UC-2, UC-3, UC-4. [StandardScenarios](../StandardScenarios.md) S0, S1.
- ADR-0001 (record format); ADR-0004 (decision 8); ADR-0010 (decisions 6, 8); [ADR-0012](ADR-0012-od8-runtime-state-file.md) (decision 3); ADR-0015 (decisions 3, 4, 7); ADR-0027 (decisions 1, 2); [ADR-0076](ADR-0076-od8-instance-start-required-members.md) (decision 1); ADR-0115 (decisions 1, 2, 3); ADR-0118 (decisions 1 to 6); ADR-0120 (decisions 1 to 4); ADR-0122 (Context; decisions 1, 4, 5).
- #4 body §1, §2, §2e, §3, §3c; #4 comment https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139876430 ; #5 A-1 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5046307826 · B-6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944087839 · A-5 · HQ-0006 answer https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6135246858 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 .
- Code, as observation only: `hilclaw/turn_start.py`, `hilclaw/turn_loop.py`, `hilclaw/turn_definition.py`, `hilclaw/layout.py` (`check_run_id`), `orchestration/round-manager.md`.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P2-1, P2-4, P2-5; CLAUDE.md "개발 드라이버와 런타임의 구분"; tasks T-0329, T-0331, T-0338.
