---
id: T-0344
title: Make hilclaw.turn_start run the runtime self-check once per start, after the first step 1 finds a turn due and before the first turn session (ADR-0125 decision 6)
phase: P2
status: DONE
commitMode: code
coversReq: [FR-1, FR-10, C-7, OD-18, S0, S1, D16]
dependsOn: [T-0338, T-0343]
touchesFiles:
  - hilclaw/turn_start.py
  - hilclaw/selfcheck.py
  - hilclaw/turn_loop.py
  - tests/test_turn_start.py
estimatedSize: {loc: 140, files: 3}
hq: []
---
## Why

PLAN P2-1 ("Round-Manager prompt and the round-0 (bring-up + baseline) procedure") is the first unchecked item in the P2 order (D18), and P2-5 needs it. PLAN P1-9 says the runtime self-check runs in the instance bring-up and that "P2-1 round 0 calls it". ADR-0125 (T-0343, landed as 393bcd8) decided, for the runs of ADR-0120 decision 1, that `hilclaw.turn_start` runs `hilclaw.selfcheck.check()` in its own process once per start, after the first step 1 answers a turn due (P1 or P4) and before the first turn session, and fixed what follows each result. Its decision 6 is a requirement on a later code task; this is that task. Today nothing calls `hilclaw.selfcheck` ("Nothing calls the module yet"), so a first-case run starts its round-0 turn without the check the owner asked for (O1 to O3 of ADR-0054).

This is a slice of a PLAN checklist item, not a follow-up, so the D18 rule for work outside the checklist does not apply. No owner-only decision is needed: ADR-0125 decided the design under DRIVER §9 and leaves only names, codes and the form of the member to this task. No open HQ touches it (HQ-0039 is a non-blocking runtime-acceptance notice on ADR-0125 item (xvi); HQ-0032 is about `hilclaw/start_instance.py`, PR #186, which this task does not touch).

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, size cap, test rules D12).
- `CLAUDE.md`, "상시 규칙": comment minimisation, "개발 드라이버와 런타임의 구분" (D16), the language policy, the code-mode branch/merge procedure (A-13) and the test rule (D12).
- `ARCHITECTURE/decisions/ADR-0125-od18-self-check-in-round-zero.md`: the whole file. Decisions 2, 3, 4, 5 and 6 and the Walk-through are the specification of this task.
- `ARCHITECTURE/decisions/ADR-0122-od19-turn-loop-open-states.md`: decisions 1 to 5 (the start, step 1, the five outcomes, what the starter is told).
- `ARCHITECTURE/decisions/ADR-0057-od18-runtime-self-check-as-landed.md`: decision 1 (`check()`, report members, exit statuses, the fault status 20 and its fixed stderr line naming the class only).
- `ARCHITECTURE/decisions/ADR-0054-od18-runtime-self-check.md`: decision 6 (the seven outcomes; the owner rows for `not_logged_in` and `front_refused`).
- Code: `hilclaw/turn_start.py` (whole file), `hilclaw/selfcheck.py` (whole file), `hilclaw/selfcheck_report.py` (`build`, `line`, `exit_status`, the `EXIT_*` constants), `hilclaw/turn_loop.py` (module docstring and `run`, lines 258 onward: where `further_turn` is called relative to making the session directory), `hilclaw/further_turn.py` (the cases P1 to P4 and the open reasons), `hilclaw/tools.py` (`encode`).
- Tests: `tests/test_turn_start.py` (the `Stub`, `go`, `start` and `told_once` helpers) and `tests/test_selfcheck.py` (its `STUB` and how it makes a stub `claude` answer `claude auth status` and the check's session).

## Acceptance Criteria

### Before editing

1. Run `gh pr list`. PR #186 (T-0324) touches only `hilclaw/start_instance.py` and three test files outside this task. If any open PR edits a file in `touchesFiles`, stop and return BLOCKED (open-PR conflict risk).

### Behaviour (ADR-0125 decisions 2 to 6)

2. **Where.** In one start of `hilclaw.turn_start.main`, `check()` is called at most once, in-process (no child `python -m hilclaw.selfcheck`), only when the first step 1 of the start answers a turn due (P1 or P4), and before the loop makes the session directory of the first turn. It is not called when the first step 1 answers P2, P3 or an open state, not called in a start that ends with an error before the first step 1 (bad usage, no data root, closed standard output), and never called again between turns of the same start. Implementing this inside the entry's step-1 callable (the first call that would answer a turn due) is acceptable; `hilclaw/turn_loop.py` gets no new behaviour.
3. **What follows each result** (ADR-0125 decision 3 table). `passed` and `no_call`: the loop goes on with the first turn as today. `no_claude`, `not_logged_in`, `login_unreadable`, `front_refused`, `session_failed`: no turn session is started, nothing is written into the run, and the start ends with one new outcome, "stopped at the check", carrying the report unchanged. `check()` raising an `Exception`: no turn, the start ends with the same new outcome (or a clearly distinct kind of it) carrying the name of the exception's class and **never its text** (the text may name a path), with no report. `KeyboardInterrupt` and `SystemExit` from the check are not caught. No retry of the check and no option or argument that skips it.
4. **What the starter is told** (ADR-0125 decision 5, ADR-0122 decision 5). The one standard-output line stays one compact JSON object in ASCII ended by LF. The new outcome has its own `outcome` name and an exit status that is not 0, 1, 2 or any status already used by the entry (10 to 13, 20); it is told apart from the five outcomes and from the error. One new member holds the check's report unchanged (the `dict` of `selfcheck_report.build`) on **every** line of a start in which a check ran and returned a report: the stopped line, and the line of whatever outcome or error the start ends with after the check passed. A start in which no check ran has no such member. The check's outcome `no_claude` must be distinguishable on the line from the entry's existing error kind `no_claude` (`hilclaw.turn_loop.ClaudeNotFoundError` at a turn). For a fault of the check, standard error gets one line naming the exception's class only. Names, the code and the member's form are the executor's choice; state them in the module docstring table and in `## Result`.
5. **Data root.** `check()` today asks `data_root_source.configured` for its `keep_out`, while the entry takes a `source` argument. Either keep `check()` as is, or let the entry hand its data root to the check through a new optional keyword of `check()` that leaves `python -m hilclaw.selfcheck` unchanged. Record the choice and its reason in `## Result`. Do not change the report, the outcomes, the exit statuses or the time limits of `hilclaw.selfcheck`.
6. **Testability.** `main` may take the check as a keyword argument defaulting to `hilclaw.selfcheck.check` (as it takes `source`), so that existing tests can inject a stand-in. At least the tests of AC 8 (a), (b) and (c) run the real `check()` against a stub `claude` that the test writes and that answers `claude auth status`, the check's session and the turn sessions.
7. **Docstrings** (ADR-0125 Consequences, "The code slice it enables"): update the module docstring of `hilclaw/turn_start.py` (the order of a start, the outcome table, the new member, the error section, runtime acceptance items: add ADR-0125 item (xvi) and the self-check items it relies on); in `hilclaw/selfcheck.py` replace "what a bring-up does after each outcome is PLAN P2-1's" and "Nothing calls the module yet" with a short pointer to `hilclaw.turn_start` and ADR-0125; in `hilclaw/turn_loop.py` change "no round-0 step and no self-check before a turn (OD-18 ⑯ (가))" so it says the loop itself runs no check and the entry does (ADR-0125). Keep comments minimal (CLAUDE.md); no new multi-line code comments.
8. **Tests** in `tests/test_turn_start.py` (D12: happy, error, branch and negative cases; every public name of the touched modules; coverage gates stay green). At least:
   - (a) happy: a fresh run (P1), stub login logged in and a check session that ends `passed`; the check runs once before the first turn session (observable in the stub's call record: the auth and check-session calls precede the first turn call), turns follow, and the final line carries the report member;
   - (b) `not_logged_in`: no check session and no turn session started; the line has the new outcome, its exit status, and the report with the login instruction; nothing written into the run;
   - (c) one of `front_refused` or `session_failed` with the real `check()`; no turn;
   - (d) with an injected check: each of the seven outcomes maps to "turn started" or "stopped" exactly as ADR-0125 decision 3 says (parametrised);
   - (e) an injected check that raises an `Exception` whose text holds a planted path: no turn, the outcome of a fault of the check, the class name on standard error, the planted text on neither stream, no report member;
   - (f) P2 (run over), P3 and one open state: the check is not called;
   - (g) a bad command line and a failing data-root source: the check is not called;
   - (h) a start that passes the check and has several turns: the check is called exactly once;
   - (i) a second start on the same run after a failed turn (P4): the check runs again in the second start;
   - (j) after a passed check, a turn that raises `ClaudeNotFoundError` (no `claude` on the `PATH` for the turn): the error line still carries the report member and its error kind is told apart from the check's `no_claude`;
   - (k) the check's `no_claude` outcome (injected or no stub on `PATH` for the check) is told apart from the entry's error `no_claude`;
   - (l) `KeyboardInterrupt` raised by an injected check propagates out of `main`.
   Existing tests keep passing; where they now reach a turn, they inject a check stand-in that returns a `passed` report or use a stub that answers the check.
9. **D16.** No real `claude`, no logged-in `claude` and no API key is needed or started; every `claude` the tests start is a stub the test writes. State this in `## Result`.
10. **No data-plane change**: no member, file, kind, value or version of the data plane is added or changed; the new outcome and member are process output of the entry (ADR-0125, A-13 reading). If the work turns out to need one, stop and return BLOCKED (data-plane schema change).
11. Size: within the DRIVER §5 cap (≤ 300 changed lines excluding tests, ≤ 5 files). `## Result` names the language (Python) and one line of reason.

### Commit and landing

12. Code mode (CLAUDE.md A-13): branch `claude/T-0344-turn-start-runs-self-check`, Draft PR with `T-0344` in the title, the context-isolated reviewer cycle (dev-code-review), CI green, then squash-merge with the PR body as the squash message, its last line `Task: T-0344`, and delete the branch. Never use `git push --force*`. Fill `## Result`.

## Out of Scope

- Any ADR, Requirements, OpenDecisionProposals, StandardScenarios or UsageCases edit; ADR-0122 and ADR-0125 are not edited.
- Where the record of the check is stored and "the instance's log" (owner-open O7; OD-18 ⑯ (나)); the credential form (O8); ⑯ (다) to (바); budgets for the check's session (OD-2, OD-19).
- The start function of ADR-0115 (`hilclaw/start_instance.py`, PR #186), the Round-Manager prompt (`orchestration/round-manager.md` needs no step for the check), round-0 steps beyond the check, the lock of two loops (OD-17).
- Removing a check directory left behind (ADR-0057 Boundaries).
- Any change to `.claude/`, CI workflows, `pyproject.toml` or dependencies.
- Starting a real `claude` in any form (D16).

## Follow-ups

- (none planned; the executor lists any it finds)

## Result
- PR #196 squash-merged as 835436e (branch `claude/T-0344-turn-start-runs-self-check`, deleted). 3 review rounds, each Approve; nits of rounds 1 and 2 fixed. GitHub CI green (six gates) on head a880aaa; local run 24001 passed, coverage 99% `turn_start.py`, 98% `selfcheck.py`.
- `hilclaw.turn_start` calls `selfcheck.check()` in-process from its step-1 callable, once per start, only when the first step 1 answers P1 or P4, before the first session directory is made; never for P2, P3, an open state, an error before step 1, or between turns. `turn_loop.py`: docstring only.
- New outcome `stopped_at_check` (exit status 14): `passed`/`no_call` start the first turn; the other five outcomes, a report that is not a dict or has no outcome word, and an `Exception` from the check stop the start (`KeyboardInterrupt`/`SystemExit` not caught).
- Output: `check` carries the report unchanged on every line of a start whose check returned a dict; after a fault the line carries `check_fault` (class name) and stderr one line `hilclaw.turn_start: fault of the check: <class>`. The check's `no_claude` shows as `stopped_at_check` with `check.outcome` = `no_claude`, distinct from the entry's error `no_claude`.
- `check(*, data_root=None)` keyword added; the entry passes its turns' data root (same data checkout kept out, config read once). With `None`, `python -m hilclaw.selfcheck` is unchanged. One test added to `tests/test_selfcheck.py` for it (outside `touchesFiles`, D12 ③).
- Language: Python (the touched modules are Python). Size about 150 changed lines outside tests, 5 files. No data-plane change. D16: every `claude` the tests run is a stub written by the test.
- Follow-ups: none. Incident: in review round 1 the reviewer sub-agent attempted `rm -rf` on a scratchpad directory; it was denied, nothing was deleted, no circumvention.
