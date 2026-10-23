---
id: T-0340
title: Name the run in the prompt of every turn, applying ADR-0123 (the entry builds the prompt from the run id, the loop's prompt rule admits '-', the Round-Manager definition takes the id from its prompt)
phase: P2
status: DONE
commitMode: code
coversReq: [FR-1, NFR-1, NFR-7, OD-18, OD-23, S0, S1]
dependsOn: [T-0338, T-0339]
touchesFiles:
  - hilclaw/turn_start.py
  - hilclaw/turn_loop.py
  - orchestration/round-manager.md
  - tests/test_turn_start.py
  - tests/test_turn_loop.py
estimatedSize: {loc: 70, files: 5}
hq: []
---
## Why

PLAN P2-1 (Round-Manager prompt and round-0 procedure) is the first unchecked item of the P2 order (D18). This task is one of its slices, so the D18 priority rule for non-checklist work does not apply. The P2-5 run needs it: the Round-Manager of the round-0 turn must write the first `STATE.json` of its run (ADR-0120 decision 2), and journaled tool requests carry `run_id` (ADR-0015 decision 4). Neither is possible while the turn session does not know which run it carries.

ADR-0123 (T-0339, main 2f49767) decided this. The entry `hilclaw.turn_start` puts the run id into the prompt of every turn. The session is given no place of the run. The run the prompt names is the one run the turn writes into and names in its tool requests. ADR-0123 Consequences, "The code slice it enables", names this task. Today:

- `hilclaw/turn_start.py` passes the fixed `PROMPT` ("Carry out the next turn of your run as your instructions say."), which names no run, and its docstring says the point is open.
- `hilclaw/turn_loop.py` refuses any prompt outside `[A-Za-z0-9 .,_]+`. A built run id holds `-` (ADR-0027 decision 2), so a prompt holding it is refused.
- `orchestration/round-manager.md` says nothing about the run.

The prompt and the definition change together (ADR-0123 decision 3), so all three go in one slice. All verification uses a stub `claude` that the tests write. No real `claude` is started (D16). That a real session receives the prompt unchanged is runtime acceptance item (ix) of ADR-0123, already notified as HQ-0037. It is not closed here.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, size cap, test rules D12).
- `CLAUDE.md`, "상시 규칙": comment policy, layer-2 language policy, test rules ①–⑤, branch/merge procedure for code mode, and the driver/runtime separation (D16).
- `ARCHITECTURE/decisions/ADR-0123-od18-turn-session-run-identity.md`, whole file. This is the specification of this task, especially Decision §2–§5, the Walk-through, and the Consequences bullets "The code slice it enables" and "Less exact, not edited" (the two `hilclaw/` bullets).
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md` decisions 2, 3 and 5. A turn carries one round at most; the loop passes its caller's prompt to each session; the definition is one for every run.
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md` decision 8 (the `run_id` pattern), and `hilclaw/layout.py` `check_run_id`.
- `hilclaw/turn_start.py`, whole file.
- `hilclaw/turn_loop.py`: the module docstring (the "*The prompt*" bullet), `_PROMPT`, `_check_prompt` and `run`.
- `orchestration/round-manager.md`, whole file. Also `hilclaw/turn_definition.py`, module docstring only: how the file becomes the session's `CLAUDE.md`.
- `tests/test_turn_start.py`: the fixtures, the public-name test (around line 290–320), and the happy test `test_a_fresh_run_goes_from_round_zero_to_over`.
- `tests/test_turn_loop.py`: lines 1–185 (the stub `claude`, which on Windows is a `claude.cmd` launcher whose arguments pass through the command interpreter), and the prompt tests around lines 325–352.

## Acceptance Criteria

Language: Python, because the change is inside existing Python modules of the layer-2 package. Record the choice and reason in one line in the commit body and in `## Result`.

### The entry (`hilclaw/turn_start.py`)

1. The fixed `PROMPT` is replaced by a prompt built from the run id that `main` was given and checked (ADR-0123 decision 3):
   - The prompt holds the id **exactly once and unchanged**, beside fixed text.
   - It satisfies the widened prompt rule of `turn_loop` (item 4) for **every** valid run id, including:
     - a one-character id;
     - a 64-character id;
     - an id holding `-` and `_`;
     - an id ending in `-`;
     - a built id such as `20261009t012331z-9f3a6c1e0b7d4a52`.
   - Its first character is never `-`.
   - You choose the wording and the place of the id, within the prompt rule. Expose the builder as one public name, for example a function or a format constant, so tests and the definition's wording can refer to it. Keep it simple: no new module.
2. The same prompt goes to every turn of one start, and every start on the same run builds the same text (decision 3). `turn_loop.run` is called once, as now, with that prompt. Nothing else changes in `main`: the order of checks, outcomes, exit statuses and the error kinds. The id is still checked by `check_run_id` before anything is read, so an invalid id still gives `bad_usage` and builds no prompt.
3. Module docstring:
   - Replace the "**Open**: how a turn session learns which run it carries …" paragraph with what ADR-0123 decided, in a sentence or two: the prompt names the run; no place of the run is handed over; this adds no access control, as decision 4 says.
   - Correct "the fixed prompt :data:`PROMPT`" in the "**One start**" paragraph.
   - Add ADR-0123 item (ix) to the runtime acceptance items it depends on.
   - Keep the docstring short. Do not restate the ADR.

### The loop (`hilclaw/turn_loop.py`)

4. Widen the prompt rule to admit `-`, never as the first character, so that the prompt can never read as an option (ADR-0123 decision 3). Every other character stays refused as now.
   - Update the error text of `_check_prompt` to match the rule.
   - Update the "*The prompt*" bullet of the module docstring to match. Keep its reason (the Windows command interpreter) and state that `-` is admitted because a built run id holds it.
   - No other code or behaviour of the loop changes. The loop still knows no run (decision 3).

### The definition (`orchestration/round-manager.md`)

5. Add the step of ADR-0123 decision 3, before "The steps of a round":
   - The run id is in the prompt, in the form the entry writes. State the form in words that match item 1.
   - If the prompt holds no run id, more than one, or one that does not match `[a-z0-9][a-z0-9_-]{0,63}`, report that in one line. Then end the session, having written nothing into any run and made no tool request that names a run.
   - Otherwise the run the prompt names is the session's own run (decision 4): its `STATE.json` is the turn's entry point; it is the only run whose files the turn writes; and its id is the only `run_id` the turn's tool requests carry. Reads elsewhere are not restricted.
   - Keep the existing "One round at most" section and the placeholder "The steps of a round" section as they are. **Do not define any round step, any round-0 procedure, or how the run's files are read or `replace` is reached.** Those are open (ADR-0123 Boundaries; OD-23, OD-18).
   - Keep it short. Put no run's data into the file: it stays one definition for every run (decision 5).

### Tests

6. Use only the stub `claude` of the existing tests. Never start a real `claude`.
7. `tests/test_turn_start.py`:
   - **Happy:** in a multi-turn run, every stub call's prompt argument (`argv[1]`) equals the prompt built for that run id, and holds the id exactly once. Two starts on the same run give the same prompt.
   - **Branch:** the edge ids of item 1 each give a prompt that `turn_loop._check_prompt` (or the public rule you expose) accepts, that does not start with `-`, and that holds the id exactly once. At least one test drives a turn with an id holding `-` all the way to the stub, and asserts the stub received the prompt unchanged.
   - **Negative:** an invalid id still gives `bad_usage` and no stub call (existing tests may cover this; keep them passing).
   - Update the public-name test and the assertions that used the old `PROMPT` (for example `assert RUN not in PROMPT`, which now inverts).
8. `tests/test_turn_loop.py`:
   - **Happy:** a prompt holding `-` in the middle, and one ending in `-`, reaches the stub unchanged as `argv[1]`. On Windows this goes through the `claude.cmd` launcher; that is the check ADR-0123 decision 3 asks of the slice.
   - **Negative:** a prompt starting with `-`, and `-` alone, are refused with `ValueError` and no stub call. The existing bad-character cases stay refused.
9. No test asserts the wording of `orchestration/round-manager.md`. The existing `tests/test_turn_definition.py` must still pass unchanged.
10. All public functions of the touched modules stay tested. The `hilclaw/` totals of line and function coverage stay ≥ 80 %. `ruff check`, `ruff format --check` and the full `pytest` suite pass locally and in CI. Locally, the stub tests may need `--basetemp` outside the system temp directory, if a `CLAUDE.md` above it triggers the marker skip (T-0338 Result).
11. Code mode:
    - Draft PR titled with `T-0340`, PR body ending in `Task: T-0340`.
    - Reviewer cycle and CI green.
    - Squash-merge with `gh pr merge --squash --body` and delete the branch `claude/T-0340-turn-prompt-names-the-run`.

## Out of Scope

- How the Round-Manager reads the run's files and reaches `hilclaw.run_state_file.replace`, and whether it then needs the place of the run. The roster and how sub-agents get the run id (OD-23, OD-18). Any round step or the round-0 procedure.
- A second channel for the run id (environment variable, file), and a hook that checks a request's `run_id` (rest of OD-18, PLAN P2-4). Any access control.
- The lock of two loops on one run (rest of OD-17); resumed, continued or branched runs (OD-8 ①); the self-check at a resume (OD-18 ⑯ (가)); the commit step (OD-8 ⑪).
- `hilclaw/start_instance.py` and its tests (open PR #186): do not touch them.
- `hilclaw/turn_definition.py` (its "placeholder prompt" bullet stays true). `hilclaw/selfcheck_session.py` and its own `PROMPT`.
- Any edit to `ARCHITECTURE/`. The less-exact sentences of ADR-0122 Context and ADR-0118 decision 3, named in ADR-0123 Consequences, stay as they are.
- `README.md`, CI, `.claude/`, `pyproject.toml`; any new dependency; any data-plane schema or validator change.
- Starting a real `claude`, or requiring a logged-in `claude`, a board or an API key (D16). Item (ix) stays a runtime acceptance item.

## Follow-ups

- The remaining P2-1 slices: how the Round-Manager reads the run's files and reaches `replace` (OD-23, OD-18); OD-18 ⑯ (가); OD-8 ⑪; then the round-0 part of the Round-Manager prompt.

## Result

- DONE. PR #194 (https://github.com/myungjoo/HIL-Claw/pull/194), squash-merged into main as 05005fd; branch `claude/T-0340-turn-prompt-names-the-run` deleted.
- Review: 2 rounds, context-isolated dev-reviewer. Round 1 Approve with 2 nits: the wording of the run-id sentence in `orchestration/round-manager.md` was fixed in 556d2c5; the other nit was informational (exactly-once for short ids such as `a` is checked by parsing, not `str.count`). Round 2 Approve with no findings.
- CI green on head 556d2c5: Python gate 3.11 and 3.14, Coverage gate, Test presence, sh gate, C gate. Locally: ruff check and ruff format --check clean; full pytest 23816 passed, 514 skipped; `hilclaw/` line coverage 99%, `turn_loop.py` 100%, `turn_start.py` 99%.
- Language: Python, because the change is inside existing Python modules of the layer-2 package.
- What changed:
  - `hilclaw/turn_start.py`: the public builder `prompt(run_id)` replaces `PROMPT`. It returns "Carry out the next turn of your run as your instructions say. Your run id is <run_id>." and checks the id with `check_run_id`. `main` passes `prompt(run_id)` to `turn_loop.run` once; the order of checks, outcomes, statuses and error kinds is unchanged. The docstring's "Open" paragraph now states the ADR-0123 decision, and item (ix) is added to the runtime acceptance items.
  - `hilclaw/turn_loop.py`: `_PROMPT` is now `[A-Za-z0-9 .,_][A-Za-z0-9 .,_-]*`, so `-` is admitted but never as the first character. The error text and docstring follow.
  - `orchestration/round-manager.md`: new "Your run" section, placed before "The steps of a round". It says where the id is and what to do when it is missing, repeated or invalid (report in one line and end), and that the named run is the turn's own run. No round step is defined.
  - Tests (stub `claude` only): in multi-turn runs and for ids holding or ending in `-`, the stub receives the built prompt unchanged as argv[1], through `claude.cmd` on Windows. Two starts on one run give the same prompt. Edge ids pass the loop's rule, and an invalid id raises `InvalidPathValueError`. In the loop, a prompt that starts with `-` (including `-` alone) is refused with no stub call.
- Follow-ups: the remaining P2-1 slices: how the Round-Manager reads the run's files and reaches `replace` (OD-23, OD-18), OD-18 ⑯ (가), OD-8 ⑪, then the round-0 part of the Round-Manager prompt. Runtime acceptance item (ix) of ADR-0123 is still open as HQ-0037.
