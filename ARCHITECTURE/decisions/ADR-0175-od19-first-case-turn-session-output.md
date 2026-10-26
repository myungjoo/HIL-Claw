# ADR-0175: Where the standard output and standard error of a first-case turn session go — both to the standard error of the process that runs the turn loop, so that the entry's standard output holds its one line alone; the loop reads, keeps and writes nothing of them, and the self-check session is not touched (part of OD-19, for the runs of ADR-0120 decision 1)

## Status

- **Accepted on 2026-10-26** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it.**
- **Two kinds of content.** What an owner decision, an agreement of #4, a requirement, an accepted record or a code docstring says is **cited**, with its source named. **Everything else is this record's own**: where each stream goes, the case of a process without a standard error, the reading of "Standard error gets nothing for an outcome", and every weighing.
- **The owner-sentence search.** Searched on 2026-10-26: the bodies of #4, #5, #7 and #8, and the 66 of their 295 comments and bodies whose text holds no "posted by driver" marker. Terms: stdout, stderr, standard output, standard error, 표준 출력, 표준 에러, 표준 오류, 터미널, terminal, 출력, 로그, log. **No owner sentence says where the output of a turn session goes or what a starter of the turn loop sees of it.** The sentences found that touch the point, each read for what it says and no further:
  - **P1** — #4 body §3d (https://github.com/myungjoo/HIL-Claw/issues/4): "감사(NFR-2)는 transcript가 아니라 산출물로: 매니저 raw transcript는 휘발, `decision.md/spec.json/eval.json`만 영속. 단 Coder는 `-p`라 출력 전체를 `coder/`로 캡처". It makes the manager's own output volatile and keeps the coder's. A turn session is the manager's session (ADR-0118 decision 3), so nothing here keeps its output.
  - **P2** — O7 as [ADR-0125](ADR-0125-od18-self-check-in-round-zero.md) Status has it: the self-check "reports to its standard output and the instance's log and writes no data-plane file". It is about the self-check, and "the instance's log" is open (ADR-0125 decision 5).
  - **P3** — the owner's D2 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5969015070): "session output + out-of-repo log; the cron wrapper surfaces the log". It is about the development driver, which is not the runtime (CLAUDE.md "개발 드라이버와 런타임의 구분"; DRIVER D16), and is not read here.
- **Answers**, **for the turn sessions of the runs of ADR-0120 decision 1**: a point inside what [ADR-0122](ADR-0122-od19-turn-loop-open-states.md) decision 5 tells the starter, so it is filed, as ADR-0122 is, under **OD-19**. **The status of every OD is unchanged.** No sub-question is registered or answered. Nothing here needs #5 A or B items, C-6, OD-25 or OD-3.
- **No member, file, path, kind, value or version of the data plane is added or changed**, and no validator changes. **It is a record with its code slice**: no `claude` process was started for it, and nothing below was tried in a live session (D16).
- It builds on [ADR-0118](ADR-0118-od18-round-process-boundary.md) (decision 3), ADR-0122 (decisions 1, 2, 5), ADR-0125 (decision 5), [ADR-0139](ADR-0139-od18-first-case-turn-session-permissions.md) (decision 8), [ADR-0141](ADR-0141-od23-first-case-coder-run-tool.md) (decision 4) and [ADR-0155](ADR-0155-od23-first-case-instance-start-command-line.md) (decision 5).
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **What the starter is told** (cited): through the process only, "the entry's exit status and its standard streams" (ADR-0122 decision 5). "Standard output gets exactly one line, a compact JSON object in ASCII ended by one LF" and "Standard error gets nothing for an outcome, except after a fault of the check" (`hilclaw/turn_start.py`, after ADR-0122 decision 5 and ADR-0125 decision 5). The starter is "a person or a CI through the entry, or an OS schedule" (ADR-0122 decision 1); the nightly routine of DRIVER D17 (PLAN P2-10) will be one that acts on the line alone.
- **The gap** (code on `main`, as observation): `hilclaw/turn_loop.py` starts each turn session with the standard output and standard error of the calling process and reads neither. A `-p` session writes its reply to its standard output, so the reply lands on the entry's standard output before the one line, and a reply without a final line feed glues the line onto its last line. T-0490 found it with the stub `claude` of `tests/first_run_stubs.py` and marked it `xfail(strict=True)`.
- **Constraints the choice must keep** (cited): the loop makes no judgement and calls no model (ADR-0118 decision 3), and does not read a session's streams (ADR-0122 decision 2, "Why"); "Nothing is written into the run or anywhere else on the starter's behalf" (ADR-0122 decision 5), which the entry keeps as "writes nothing into the run or anywhere else on the starter's behalf (no `run_status`, no file, no notification)" (`hilclaw/turn_start.py`); where the self-check's record is stored and what "the instance's log" is stay open (ADR-0125 decision 5, O7, ⑯ (나)); nothing a run needs lives in the session directory, which is removed after each turn (NFR-1; `hilclaw/turn_loop.py`). A new file under `runs/<run_id>/` or `db/` would be a data-plane change (ADR-0004).

## Decision

A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope

- **The turn sessions that `hilclaw.turn_loop` starts** for the runs of ADR-0120 decision 1, through the entry `python -m hilclaw.turn_start`.
- **Outside**: the self-check session, which already takes its standard output to read its stream (cited: `hilclaw/selfcheck_session.py`) and is not touched; the coder's session, started in its container by `coder.run`; `hilclaw.new_run`, which starts no session; every other run.

### 2. (a) A turn session's standard output goes to the calling process's standard error

- **The loop starts each turn session with its standard output on file descriptor 2 of the process that runs the loop** — for the entry, the entry's standard error.
- **Why.** The entry's standard output is the starter's one channel for the outcome, and an unattended starter reads it whole. The reply is the only text a person has of a turn beyond its exit status, so it is not discarded. Standard error is already one of "the entry's standard streams" of ADR-0122 decision 5, so nothing is written anywhere else.

### 3. (b) A turn session's standard error stays the calling process's standard error

- **Unchanged**: the session inherits the calling process's standard error, as today.
- **Why.** The session's two streams then reach the same place, in the order the session wrote them, and a starter reads one stream for everything a session said.

### 4. (c) The loop reads, keeps and writes nothing of either stream

- The loop hands the descriptor to the session and does nothing else with it: it reads, copies, buffers, cuts, prefixes and interprets nothing (ADR-0122 decision 2), and owns no file and no pipe. So it has no failure of its own to handle, and a turn costs no more.
- **A calling process without a standard error.** When descriptor 2 is not open at a turn, the session's standard output is discarded and its standard error is left as inherited, which reaches nothing, as today. The turn still starts and its exit status is passed on as before. **Why**: the one line does not need standard error, and a starter that closed it chose to see nothing there. Refusing the turn would stop a run for a stream no outcome uses. A descriptor 2 that the process found closed and that a later open reused for another file is not told apart: the session's text then goes to that file, as its standard error already did before this record.
- **Unchanged**: the exit status of a turn, the command line (ADR-0139 decision 8), the environment (ADR-0141 decision 4), the working directory and the closed standard input.

### 5. (d) What the starter sees, and the entry's standard error

- **Standard output**: the entry's one line and nothing else. The exception is a starter that gives the entry one stream for both (`2>&1`); it then gets the session text before the line, by its own choice.
- **Standard error**: what each turn session wrote to either stream, unread, in the order of the turns, then the entry's own line, if any. A session's last text may lack a line feed, and the entry's own line then follows it on the same line. That line was free text, never parsed, before this record too.
- **"Standard error gets nothing for an outcome"** (`hilclaw/turn_start.py`) is read as: **the entry itself** writes nothing there for an outcome. The session text is not the entry's, tells no outcome and is never parsed. The entry's own lines, after a fault of the check and on an error, stay as they are.
- **Diagnosing a failed turn**: the starter has the exit status on the line (ADR-0122 decision 2), the session's own text on standard error if it keeps it, and the run's files and history. **What a starter keeps of standard error, and where, is the starter's**; the entry writes nothing on its behalf (ADR-0122 decision 1).

### 6. (e) What it keeps

- ADR-0122 decision 1 as `hilclaw/turn_start.py` keeps it: no file, no data-plane file and no notification are written. Standard error is a stream of the entry's own process.
- **No log is defined.** The session text is not "the instance's log", and the check's report still reaches the starter only on the standard output line (ADR-0125 decision 5).
- The self-check session is not touched (decision 1).

### Walk-through

| Situation | What follows |
|---|---|
| A person starts the entry; three turns end the run with replies | Standard output: `{"outcome":"run_over",…}` alone. Standard error: the three replies, in order |
| A turn fails (exit status 3) after writing an error message to its standard output | Line `failed_turn` with `exit_status` 3; the message is on standard error |
| A reply ends without a line feed and the loop then raises | Standard error: the reply, then `hilclaw.turn_start: …` on the same line; standard output: the `error` line alone |
| A schedule starts the entry with standard error closed | The turns start; their replies are discarded; the line on standard output is as before |
| A starter runs the entry with `2>&1` | Session text, then the line, on one stream: the starter's choice |
| The nightly routine (PLAN P2-10) starts the entry | It reads the last and only line of standard output; what it keeps of standard error is its own |

## Alternatives considered

| Alternative | Why not |
|---|---|
| The calling process's own streams (before this record) | The reply comes before the one line on standard output, and a reply without a line feed glues onto it. An unattended starter cannot read the outcome (Context). |
| Discard both streams (`DEVNULL`) | The line is kept, but a person loses everything a session said about a failed turn, such as an expired login or a usage limit, with nothing in return. ADR-0122 item (viii) asks whether a session's output tells a usage limit apart; discarding would make that output unreachable. |
| Discard standard output, keep standard error | A `-p` session writes its reply, and possibly the reason it stopped, to standard output. Where a real session puts its error messages is not shown (Consequences), so a part could be lost. |
| Both to the entry's standard error (adopted) | Its cost: standard error carries session text that is not the entry's, so the entry's own line may follow it on the same line (decision 5). |
| A file outside the run (beside the session directories, or a fixed place) | A write "anywhere else on the starter's behalf" (ADR-0122 decision 1). It would also amount to a log of the instance, which ADR-0125 decision 5 leaves open (O7, ⑯ (나)), and it needs a place, a name, a retention rule and failure handling that no source gives. |
| A file in the session directory | It is removed with the directory after the turn (NFR-1), so it is a discard that costs a write. Keeping the directory would leave run state outside the data plane. |
| A file in the run (`runs/<run_id>/…`) | A data-plane change (ADR-0004; CLAUDE.md A-13), and against P1, which leaves the manager's output volatile. |
| A pipe the loop reads, and a summary on the line | The loop would read a session's streams (against ADR-0122 decision 2) and choose what to keep, which is a judgement (ADR-0118 decision 3). The line would also grow with session text. |
| Prefix each session line on standard error | The loop would read and rewrite the stream (decision 4), and a pipe adds failure paths and a reader thread for a gain that is only cosmetic. |
| Refuse the turn when standard error is closed | It stops a run for a stream that no outcome uses (decision 4). |

## Consequences

- **A-13 reading.** Code mode for the slice. **No data-plane change**: no file, member or value of `runs/`, `db/` or any validator. No new external dependency.
- **The code slice, landed with this record** (tests with stub `claude` programs only, no `claude`, D16): `hilclaw/turn_loop.py` starts each turn with its standard output on descriptor 2, or discarded when descriptor 2 is not open, and its docstring paragraph "The command line" says so; the `hilclaw/turn_start.py` docstring says what standard error carries; tests in `tests/test_turn_loop.py` and `tests/test_turn_start.py` check where the bytes go at the descriptor level; `tests/test_first_run_end_to_end.py` drops T-0490's strict xfail and checks both streams of a `run_over` start.
- **Less exact, not edited** (found by a search of `ARCHITECTURE/decisions/` for "standard error", "standard output", "its streams" and "Standard error gets"; not claimed complete): ADR-0122 decision 2 "Why" ("`hilclaw.turn_loop` does not read its streams") stays true; ADR-0125 decision 5 ("Standard error gets one line for a fault of the check") stays true of the entry's own writing under decision 5's reading. ADR-0155 decision 5 is about `hilclaw.new_run` and is untouched.
- **UsageCases and StandardScenarios**: re-checked by the StandardScenarios rules; no sentence becomes false and no verdict changes. S2 step 1 ("CI가 `claude -p`로 … instance를 기동") gains, for these runs, a standard output a CI can read.
- **Runtime acceptance items** (D16; nothing was tried, nothing is required of the development machine). They go to [PROCESS/RuntimeAcceptance.md](../../PROCESS/RuntimeAcceptance.md) (DRIVER §8, D22), not to an HQ. ADR-0118 items (v) and (vi) and ADR-0122 item (viii) are used, not changed. **New**:
  - **(xci)** A `-p` turn session started with its standard output on the entry's standard error writes its reply and every message about why it stopped, such as an expired login, a usage limit or an error, only to its standard output and standard error, and not to the terminal or another descriptor. Nothing of it then reaches the entry's standard output, and a person reading the entry's standard error after a failed turn finds there what the session said.
- **The cost, plainly.** The entry's standard error now carries session text of unbounded length, which a starter that keeps it must store. A starter that treats any standard error as a failure must use the exit status instead, as ADR-0122 decision 5 already says. Nothing of a session is kept by the runtime itself (P1).

## Boundaries (not decided here)

- **The instance's log** and where the self-check's record is stored (ADR-0125 decision 5; O7 and ⑯ (나), partly owner's); any **notification channel** (OD-27; FR-16).
- **What a starter keeps of standard error**, and where: for the nightly routine of DRIVER D17, its result recording is PLAN P2-10's.
- **Telling a usage-limit end from another failure** by a session's output, and the pause (ADR-0122 decision 6; rest of OD-19).
- **The lock** of two loops on one run (rest of OD-17) and the limit the entry states about schedules.
- The output of the self-check session, of the coder's session and of runs outside ADR-0120 decision 1.
- Any edit of an earlier record, of FR or NFR text, UsageCases, `orchestration/`, CI, `.claude/` or any settings file; any new external dependency.

## References

- [Requirements](../Requirements.md): FR-1, FR-4, FR-16, NFR-1, NFR-2; register rows OD-17, OD-19, OD-27. [OpenDecisionProposals](../OpenDecisionProposals.md) [OD-19](../OpenDecisionProposals.md#od-19). [StandardScenarios](../StandardScenarios.md) S0, S2.
- ADR-0001 (record format); [ADR-0004](ADR-0004-od8-data-plane-layout.md); ADR-0118 (decision 3); ADR-0120 (decision 1); ADR-0122 (decisions 1, 2, 5, 6; Consequences); ADR-0125 (Status O7; decision 5); ADR-0139 (decision 8); ADR-0141 (decision 4); ADR-0155 (decision 5).
- #4 body §3d; #5 D2 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5969015070 , D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 .
- Code, as observation and as changed: `hilclaw/turn_loop.py`, `hilclaw/turn_start.py`, `hilclaw/selfcheck_session.py`; tests `tests/first_run_stubs.py`, `tests/test_first_run_end_to_end.py`.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §8, §9, D16, D17; PROCESS/PLAN.md P2-10, P2-14; CLAUDE.md "개발 드라이버와 런타임의 구분"; tasks T-0490, T-0492.
