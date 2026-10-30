# ADR-0125: Where the runtime self-check runs for a first-case run — the turn loop's command-line entry runs it once per start, after the start's first step 1 has found a turn due and before the first turn session; only `passed` and `no_call` let that turn start, and nothing runs it between two turns of one start (part of OD-18 sub-question ⑯ (가), for the runs of ADR-0120 decision 1)

## Status

- **Accepted on 2026-10-19** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it.**
- **Two kinds of content.** What an owner decision, a requirement, a use case, an accepted record or a code docstring says is **cited**, with its source named; the owner's sentences O1 to O8 are those quoted in the Context of [ADR-0054](ADR-0054-od18-runtime-self-check.md) from the answer to HQ-0006, and are marked **owner**. **Everything else is this record's own**: the scope, the component and the point, the row of each result, the readings marked as such, and every weighing.
- **The owner-sentence search.** Searched: the body of #4 and its 6 comments; the body of #5 and the 38 of its 198 comments whose text holds no "posted by driver" marker; the bodies and comments of #7 (2) and #8 (6). Terms: self-check, selfcheck, 자체 점검, bring-up, 라운드 0, round 0, round-0, 재개, resume, 로그인, login, auth, front, 중단, stop. **Only the answer to HQ-0006 speaks of the point.** The sentences found that touch it, each read for what it says and no further:
  - **O1** — "a self-check of the `hilclaw` package that the instance bring-up (P2-1, round 0) runs on the runtime machine". It says that the bring-up runs the check. It names no component, no point against the turns, and says nothing of later starts.
  - **O2** — when nothing is logged in, the check "stops with the instruction to run `claude auth login`"; **O3** — "a refused front fails the bring-up". The two results the owner fixed (ADR-0054 decision 6); decision 3 cites them and does not change them.
  - **O7** — "Not decided here: where the self-check's record is stored — until that is decided, it reports to its standard output and the instance's log and writes no data-plane file". Decision 5 keeps it; **O8** (the credential form) is not touched.
  - The other hits are about other things: #5 A-9 and its confirmation (FR-1 round 0 merged into the PR #6 lineage), #5 B-4 (round-0 bring-up code as a baseline candidate), #5 A-12 (exposure form), the "resume" sentences of #5 D-items (the driver's own iterations), and #4, #7, #8 texts on resuming a turn or a session in general. None says when the check runs or what follows its results.
- **Not an owner-only item.** The point is a part of OD-18 ⑯ (가), a design-level OD. Nothing here needs #5 A or B, C-6, OD-25, OD-3 or O7 and O8, which stay open (Boundaries).
- Answers, **for the runs of ADR-0120 decision 1 only**, part of **sub-question ⑯ (가) of OD-18**: which component runs the check and at which point, what follows each of its results, and whether it runs again at a later start of the same run and between two turns. **OD-18 keeps its status.** No sub-question is registered.
- **No member, file, kind, value or version of the data plane is added or changed**, and no validator changes. **It is a record, not code**: no `claude` process, compiler, `hilclaw.selfcheck` or `hilclaw.turn_start` was started for it, and nothing below was tried in a live session (D16).
- It builds on [ADR-0054](ADR-0054-od18-runtime-self-check.md) (decisions 1, 2, 6, 7), [ADR-0057](ADR-0057-od18-runtime-self-check-as-landed.md) (decision 1; Consequences "For P2-1"), [ADR-0118](ADR-0118-od18-round-process-boundary.md) (decisions 2, 3), [ADR-0120](ADR-0120-od8-first-state-file.md) (decisions 1 to 4), [ADR-0121](ADR-0121-od8-run-over-member.md) (decision 5) and [ADR-0122](ADR-0122-od19-turn-loop-open-states.md) (decisions 1 to 5). **If one of them is reverted, this record is revisited with it.**
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **The open point** (cited): ADR-0054 decision 6, "What round 0 does after any of the other five — `passed` included — is PLAN P2-1's and is not decided here (sub-question ⑯ (가))"; ADR-0057 Boundaries reads (가) as covering exit status 20 too; ⑯ (가) also asks whether the check runs again "at a resume or at a round boundary". ADR-0118 Boundaries: "whether the loop runs the check before a turn is the round-0 slice's question"; ADR-0119 and ADR-0120 Boundaries list "the self-check in round 0" as open.
- **The check as landed** (cited: ADR-0057 decision 1; `hilclaw/selfcheck.py`): `check()` reads the login once and, only when logged in, starts one throwaway session; it returns the report as a value and passes on what its steps raise, with a text that may name a path. The command `python -m hilclaw.selfcheck` writes the report line and exits with 0 (`passed`), 10 to 15 (the other six outcomes) or 20 (a fault, with no report). One check spends one session of plan usage when logged in (ADR-0054 L5) and may take about 30 s plus 300 s. "What a bring-up does after each outcome is PLAN P2-1's", and "Nothing calls the module yet".
- **What drives a first-case run** (cited): the start function of ADR-0115 writes `instance.json`, and its caller is open; the turn loop of ADR-0118 decision 3 starts each turn session, and its command-line entry `python -m hilclaw.turn_start <run_id>` (ADR-0122; `hilclaw/turn_start.py`) makes one start: it checks the run id, asks the data-root source once, then runs the loop, whose step 1 answers P1 (fresh run directory) and P4 (`STATE.json` without `run_status`, `round_budget` stated) with a turn due, and ends with one line on standard output naming one of five outcomes or an error (ADR-0122 decision 5). A start may be followed by another start on the same run — after a failed or unchanged turn, by a person (ADR-0122 decision 2) — which then finds P4, or P1 again. The Round-Manager of the round-0 turn writes the first `STATE.json` (ADR-0120 decision 2).

## Decision

A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope and terms

- **The runs of ADR-0120 decision 1**, driven through `hilclaw.turn_start`. Resumed, continued or branched runs (OD-8 ①; UC-4) and every other run are outside; nothing here is required or allowed of them.
- **The check** is one call of `hilclaw.selfcheck.check`. **A start** is one invocation of the entry, as `hilclaw/turn_start.py` uses the word (it holds the start of ADR-0122 decision 1, from its first step 1 until the loop returns); **the starter** is that of ADR-0122 decision 1. **The first step 1** is the step 1 that a start makes before its first turn.

### 2. (a) The component and the point

- **`hilclaw.turn_start`, the turn loop's command-line entry, runs the check, once per start, in its own process.** It runs it **after the first step 1 has answered a turn due (P1 or P4)** and **before the loop prepares the session directory of the first turn**. The order of a start is then: the run id, standard output, the data root and the loop's checks before its first step 1, as today; the first step 1; the check; the first turn.
- **No check** when the first step 1 answers no turn — P2, P3 or an open state (ADR-0122 decisions 4 and 5) — and none in a start that ends with an error before it.
- **Why the entry.** It is the one layer-2 component that starts the turn sessions of these runs; the check spends a session only where a turn session is about to be spent and right before it, so what the check saw is as close as it can be to what that turn meets (ADR-0054 L2, L4). It makes no judgement (ADR-0118 decision 3): the row of each result is fixed (decision 3). The check stays no tool and no agent's call (ADR-0054 decision 1).
- **Why in-process.** `check()` gives the report as a value, as ADR-0057 decision 1 made it public for; no second interpreter, no line to parse.
- **For the bring-up** (O1; PLAN P1-9, written by the owner's session with that answer: "P2-1 라운드 0이 호출"). This record reads round 0's bring-up as including a step the entry carries out right before the round-0 turn session, not only what that session does. The first start of such a run finds P1, so the check runs before the round-0 turn — before the first `STATE.json` and the rest of the bring-up (ADR-0120 decision 2). It writes no data-plane file (O7), so ADR-0120 decision 2 needs no order against it.

### 3. (b) What follows each result

Every row is told through the start's process output (decision 5). "No turn" means the start returns without starting any turn session and writes nothing into the run.

| Result of the check | A turn? | What the starter is told |
|---|---|---|
| `passed` (0) | Yes: the loop goes on with the first turn | The outcome the start ends with (ADR-0122 decision 5), with the report |
| `no_claude` (10) | No | Stopped at the check, with the report |
| `not_logged_in` (11) (**owner**, O2: "stops") | No | Stopped at the check, with the report, which carries the instruction to run `claude auth login` |
| `login_unreadable` (12) | No | Stopped at the check, with the report |
| `front_refused` (13) (**owner**, O3: "fails the bring-up") | No | Stopped at the check, with the report |
| `no_call` (14) | Yes, as for `passed` | As for `passed`; the report says which names, calls and tokens were seen |
| `session_failed` (15) | No | Stopped at the check, with the report |
| ADR-0057 status 20 (a fault): here, `check()` raised an `Exception` | No | Stopped at a fault of the check, with the name of the exception's class and never its text; no report |
| No readable result: the start is interrupted (`KeyboardInterrupt`, not caught — `hilclaw/turn_start.py`) or killed during the check. Status 120 of the command does not arise: the check is no child process (decision 2) | No | No line: the start ends with the interpreter's or the system's status, as any interrupted start does today; the check's directory may stay behind (ADR-0057 decision 2) |

- **The two owner rows apply at every start** of decision 4, not only at the bring-up: a command line that is not logged in, or a front the client refuses, would stop the turn session of a later start as well. This is this record's reading; it neither widens nor narrows O2 and O3 at the bring-up.
- **`no_call` lets the turn start.** Reading: the session ended by itself with exit status 0, the login worked and the client showed `hilclaw` connected; what is missing is the model's part, which is not deterministic and "says nothing against the front" (cited: ADR-0054 L3 and decision 6). Stopping on it would let one reply of the model stop a run; and if a real session always ends in `no_call` (ADR-0054 K14; its Alternatives row on tool search), no run could start at all. A turn whose model cannot reach the tools ends without progress, and ADR-0122 decision 3 ends that start after it: at most one session more.
- **`session_failed` stops the start.** Reading: the session itself did not end well, and the causes ADR-0054 decision 6 names for it — a usage limit, the network, an expired login, an option the installed version does not know — are ones a turn session started at once meets again; so, as ADR-0122 decision 2 reasons for a failed turn, a turn now would spend a session for nothing, and returning loses nothing. It "says nothing about the front" (cited) and is not read as a refusal; the next start runs the check again (decision 4).
- **`no_claude`, `login_unreadable` and status 20 stop the start**: no turn session could start without `claude`, ADR-0054 decision 3 reads neither of the first two as logged in, and after a fault nothing is known.
- **No retry of the check and no option that skips it.** A start makes one check; a stopped start is started again by its starter, as after a failed turn (ADR-0122 decision 2).

### 4. (c) Again at a later start; not between turns

- **(i) A later start on the same run runs the check again**, by decision 2: whenever its first step 1 answers a turn due — P4, or P1 when an earlier round-0 turn wrote nothing. Why: the facts the check observes belong to the machine and the moment, not to the run — whether the command line is still logged in (ADR-0054 K12), which version of Claude Code answers the front (L2) — and a later start may come days after the first, after a failed turn whose cause may be one of them (ADR-0122 decision 2). Its cost is one session per start, and starts are few: by ADR-0122 a start ends only when the run is over, a turn failed or made no progress, a state is open, or on an error.
- **(ii) Nothing runs the check between two turns of one start**, at a round boundary or otherwise. Why: the turns of one start follow each other with no gap a starter chose; a check before every turn would double the sessions of a run (ADR-0054 L5; NFR-5); and a turn that meets a failure the check would have shown ends with a status other than 0 or no progress, so ADR-0122 decisions 2 and 3 end the start, and the next start's check runs (i). **This makes no rule for a login that expires during a run** (⑯ (바)): what the loop does after a failed turn, whatever its cause, is ADR-0122's.

### 5. (d) How the report reaches the starter

- **Through the start's process output.** This record reads O7's "its standard output" as the standard output of the process that runs the check, here the entry (decision 2). The one line the entry writes to standard output (cited: `hilclaw/turn_start.py`) **carries the check's report unchanged as one member** whenever a check ran: on the line of "stopped at the check" and on the line of whatever outcome a start that passed the check ends with. Standard error gets one line for a fault of the check, naming the exception's class only, as `hilclaw.selfcheck` does (ADR-0057 decision 1).
- **The report stays the output of a process, not a data-plane schema** (cited: ADR-0054 decision 7; ADR-0057 decision 1). Nothing of the check is written into the run, the data checkout or any file on the starter's behalf (O7; ADR-0122 decision 1); the check's own temporary directory outside both checkouts (ADR-0057 decision 1) is no such file.
- **Not decided**: where the record of the check is stored (**owner**, O7, open) and what "the instance's log" is and how the report also reaches it (O7; ⑯ (나), open). This record defines no log. Until ⑯ (나) is answered, the entry's standard output is the only place this record sends the report.

### 6. What the code slice must do (a requirement on a later task)

- **It changes the set of outcomes of `turn_start`** (ADR-0122 decision 5), plainly: one new outcome, **stopped at the check**, told apart from the five and from the error, with an exit status other than 0 (only "run over" says the run needs no further start), holding the check's report or, after a fault, the class name; and one new member holding the report on every line of a start in which a check ran. Names, codes and the form of the member are the code task's, and so is how the check's `no_claude` is told apart from the entry's existing error `no_claude` (`hilclaw.turn_loop.ClaudeNotFoundError`). ADR-0122 is not edited.
- `check()` asks the configured data-root source for its `keep_out` (cited: `hilclaw/selfcheck.py`), while the entry takes a `source` argument; whether the entry hands its data root to the check is the code task's.
- Tested against a stub `claude` that the tests write, which answers `claude auth status` and the check's session as well as the turn sessions; never a real one (D16; O4).

### Walk-through

| Situation | What follows |
|---|---|
| P2-5: a new `cpu_standin` × GEMM run (N = 1, `round_budget` 5); a person starts `turn_start` on its id | First step 1: P1. The check ends `passed`; the round-0 turn starts and writes the first `STATE.json` (decision 2; ADR-0120 decision 2); later turns follow with no further check (decision 4 (ii)). The line at the end of the start names its outcome and carries the report (decision 5) |
| The command line is not logged in | `not_logged_in`: no session spent, no turn; the line says stopped at the check and carries the instruction (decision 3; O2) |
| The client drops the server after `initialize` | `front_refused`: no turn (decision 3; O3) |
| The usage limit is reached during the check's session | `session_failed`: no turn; a later start checks again (decisions 3, 4) |
| The model of the check's session calls nothing | `no_call`: the round-0 turn starts; if its model cannot use the tools either, the start ends as an unchanged turn (decision 3; ADR-0122 decision 3) |
| `check()` raises (status 20), for example its directory cannot be made | No turn; stopped at a fault of the check, with the class name, no report (decision 3) |
| The round-0 turn fails; days later the person starts `turn_start` on the same run | First step 1: P4 (or P1 if nothing was written); the check runs again before the first turn of this start (decision 4 (i)) |
| A run that is over is started again | First step 1: P2; no check, no turn: run over (decision 2; ADR-0121 decision 5) |

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| a | The start function of ADR-0115, before it writes `instance.json` | Its caller is open (CI, UI, an agent); a start may be followed by no loop, or by one days later, so the check would be spent where no turn follows and not where one does; later starts are not covered. It would also put a `claude` child into a function that only writes a file |
| a | The Round-Manager of the round-0 turn | A turn session already needs the login and the front, so it cannot run when either fails; the check would be started by a model through Bash, which ADR-0054 decision 1 keeps away from agents (a session per call); a fixed step would sit in a model (ADR-0118 decision 3) |
| a | The starter by hand (`python -m hilclaw.selfcheck` before `turn_start`) | Not enforced, and an unattended start (UC-3) has nobody to read it; O1 has the bring-up run it |
| a | `turn_start` before its first step 1, whatever the state | Spends a session on runs that need no turn (P2, P3, open states) |
| a | The command `python -m hilclaw.selfcheck` as a child process | A second interpreter, a line to parse and more statuses to map (120, signals) for the same report `check()` returns |
| b | `no_call` stops the start | One reply of a non-deterministic model would stop a run; if every real session ends in `no_call` (K14), no run starts |
| b | `session_failed` lets the turn start | Its causes are ones the turn meets again (ADR-0122 decision 2's reason); the turn would fail too, one session later |
| b | Retry the check inside the start | A second session decided by the code (ADR-0054 L5; its Alternatives row on a retry) |
| c | Only at the bring-up (P1) | A later start, often after a failed turn, would spend a turn session to learn that the login expired or the front changed |
| c | Before every turn | Doubles the sessions of a run; ADR-0122 already ends the start after the turn that meets such a failure |
| d | Write the report into the run, or into a log file the entry defines | Into the run: a data-plane file, against O7. A log file: it would define the instance's log, which is ⑯ (나) and stays open |

## Consequences

- **The code slice it enables** (code mode; a later task): decision 6 in `hilclaw/turn_start.py` and its tests; the docstrings of `hilclaw/selfcheck.py` ("what a bring-up does after each outcome is PLAN P2-1's"; "Nothing calls the module yet"), `hilclaw/turn_start.py` and `hilclaw/turn_loop.py`. `orchestration/round-manager.md` needs no step for the check: the Round-Manager does not run it.
- **Less exact, not edited** (found by a search of `ARCHITECTURE/decisions/`, `hilclaw/` and `orchestration/` for "⑯ (가)", "self-check in round 0", "P2-1's" and "Nothing calls"; not claimed complete). For the runs of decision 1 they say the point is open, and it now is answered in part:
  - ADR-0054 L5 and Consequences ("one session per bring-up"; "Every bring-up spends one session"): by decision 4 (i) it is one session per start that has a turn due.
  - ADR-0054 decision 6 ("What round 0 does after any of the other five … is PLAN P2-1's") and Boundaries ("**Round 0**: … what it does after each outcome …, whether the check runs again at a resume or at a round boundary").
  - ADR-0057 Consequences "For P2-1" (the first caller is now named) and Boundaries ((가)).
  - ADR-0118 Boundaries ("whether the loop runs the check before a turn is the round-0 slice's question"); ADR-0119 and ADR-0120 Boundaries and ADR-0120 Consequences (1) ("the self-check in round 0"); ADR-0123 and ADR-0124 Consequences and Boundaries ("whether the self-check runs again at a resume"; "The self-check at a resume or a round boundary").
  - ADR-0122 decision 5 (five outcomes; decision 6 here adds one) and Consequences "The cost, plainly" ("at most two sessions that end no round"; "one session per start" for a run whose turns keep failing): each start that has a turn due now also spends the check's session.
  - The docstrings of `hilclaw/selfcheck.py` and `hilclaw/turn_start.py` named above, and of `hilclaw/turn_loop.py` ("no self-check before a turn (OD-18 ⑯ (가))"; the loop itself stays without one).
- **UsageCases and StandardScenarios**: no sentence becomes false. UC-1's precondition (the login) is now observed at every start of these runs, before any turn.
- **A-13 reading.** Document mode. No code, test, setting or dependency changes. **No data-plane change**: no member, file, kind, value or version is added or changed; the new outcome and member of decision 6 are process output of the entry.
- **Runtime acceptance items** (D16; nothing was tried and nothing is required of the development machine). The self-check series of ADR-0054 (i) to (viii) and ADR-0057 (ix) to (xv) and the turn-session series of ADR-0118, ADR-0122, ADR-0123 and ADR-0124 are used, not changed. **New**, in the self-check series:
  - **(xvi)** What `claude auth status` reports for a stored login that has expired and cannot be refreshed: exit status 1 (the check ends `not_logged_in`) or 0 with an `authMethod` (the session ends `session_failed`). Either stops the start (decision 3); only the instruction the starter gets differs.
- **The cost, plainly.** Every start that has a turn due spends one session of plan usage and waits roughly 30 s plus 300 s plus the removal before its first turn, with no bound stated (ADR-0057 Consequences "For P2-1"). A check that misreads real sessions (ADR-0057 decision 4; items (v), (xii)) stops every start until a code task fixes it — visibly, by the report, and with no option to skip it. A `no_call` lets one turn run that may make no progress.

## Boundaries (not decided here)

- **Owner, open** (O7, O8): where the record of the check is stored; the credential form for unattended runs.
- **The rest of ⑯**: (나) the instance's log and how the report reaches it; (다) an `authMethod` other than `none` and `claude.ai`; (라) whether the check's session counts against a budget (OD-2, OD-19); (마) the tool list of a run's registry and the ways the check does not exercise; (바) a login that expires during a run, and `--bare` as the default of `-p`.
- **⑯ (가) for every other run**: runs outside ADR-0120 decision 1, and resumed, continued or branched runs (OD-8 ①; UC-4).
- **Recovery** of open steps and failed boards (OD-10, OD-17); the usage-limit pause and a retry inside the loop (OD-19); the lock of two loops, which the time between the first step 1 and the first turn does not change (rest of OD-17); notification (OD-27).
- **Who removes a check directory left behind** (ADR-0057 Boundaries); the caller of the start function (ADR-0115).
- Any change to an earlier record, FR or NFR text, UsageCases, `hilclaw/`, `orchestration/`, tests, CI, `.claude/`, any settings file or the `HIL-Claw-data` repository; any new external dependency.

## References

- [Requirements](../Requirements.md): FR-1, FR-10, NFR-5, C-7; register rows OD-10, OD-17, OD-18, OD-19, OD-23. [OpenDecisionProposals OD-18](../OpenDecisionProposals.md#od-18) (⑯). [UsageCases](../UsageCases.md) UC-1, UC-3, UC-4. [StandardScenarios](../StandardScenarios.md) S0, S1.
- ADR-0001 (record format); ADR-0054 (Context O1 to O8; K12, K14; L2 to L5; decisions 1, 3, 6, 7; Alternatives; Boundaries); ADR-0057 (decisions 1, 2, 4; Consequences; Boundaries); [ADR-0115](ADR-0115-od8-instance-start-performer.md); ADR-0118 (decisions 2, 3; Boundaries); [ADR-0119](ADR-0119-od28-first-case-baseline.md) (Boundaries); ADR-0120 (decisions 1 to 4; Consequences; Boundaries); ADR-0121 (decision 5); ADR-0122 (decisions 1 to 5; Consequences); [ADR-0123](ADR-0123-od18-turn-session-run-identity.md) (Consequences; Boundaries); [ADR-0124](ADR-0124-od23-round-manager-run-file-access.md) (Consequences; Boundaries).
- #5 HQ-0006 answer https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6135246858 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 .
- Code, as observation only: `hilclaw/selfcheck.py`, `hilclaw/selfcheck_report.py`, `hilclaw/turn_start.py`, `hilclaw/turn_loop.py`, `hilclaw/further_turn.py`, `orchestration/round-manager.md`.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §8, §9; PROCESS/PLAN.md P1-9, P2-1, P2-5; CLAUDE.md "개발 드라이버와 런타임의 구분" (D16).
