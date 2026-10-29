---
id: T-0493
title: Add the nightly end-to-end routine of DRIVER D17 - its procedure document and the entry point it calls to start a runtime run with a real `claude` and leave a pass/fail regression signal with logs - and record the D17 (나) design (PLAN P2-10)
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [S0, S1, D17, FR-1, FR-4, "PLAN P2-10"]
dependsOn: []
touchesFiles:
  - PROCESS/NIGHTLY.md
  - PROCESS/DRIVER.md
  - .claude/agents/dev-planner.md
  - hilclaw/nightly.py
  - tests/test_nightly.py
estimatedSize: {loc: 560, files: 5}   # refined after HQ-0076 (executor): entry point ~470 (formatted, docstring included), procedure document ~75, DRIVER/planner text ~12; no ADR (nothing touches ARCHITECTURE/ or the data-plane schema); tests outside the cap.
hq: [HQ-0076]
---
## Why

PLAN P2-10 is the next checklist item in PLAN P2's order (round loop -> first run P2-5 (checked) -> nightly P2-10 -> P2-11..P2-14 -> P2-8). The owner decided (2026-10-13, chat; DRIVER §11 D17) that a nightly routine, separate from the driver that performs DRIVER §3, builds the runtime orchestrator and runs it end to end with a real `claude`; its result is a regression signal only (not acceptance measurement, PLAN P2-9, and not case storage, FR-18); its failures are registered as GitHub issues and then resolved automatically by the §3 driver, with environment-caused failures going the §8 HQ path (D17 ④ and the "따름" of the D17 row).

D17 leaves two groups undecided:
- **(가) owner/operator values**, which PLAN P2-10 says must be asked as a DRIVER §8 HQ before the task is made: the nightly run's configuration (starting candidate: the P2-5 configuration), the time it runs, the usage cap, the routine's permission mode, work folder and machine, and how the `claude` child-process guard (HQ-0007 answer ④; not built yet, PLAN P0.5-4) and the nightly routine stand together. PLAN P2-15 adds: whether the nightly routine runs the real Llama 3.2 1B weights. These are asked in **HQ-0076**. This task is BLOCKED until HQ-0076 is answered; the acceptance criteria below are an outline and are refined (by the planner or the integrator, per DRIVER §3-2 when HQ-0076 resolves) within the answer's range.
- **(나) design the task decides through review**: where the result is recorded and how the §3 driver reads it; who registers a failure issue, its form, de-duplication, and the label/criteria by which the driver accepts an issue as a task; the rule that tells a code defect from an environment cause; the HQ reason and `taskId` for an environment cause and what happens to its issue; how an issue becomes a task (who writes the task file, which text of DRIVER §3-3/§6 changes) and its order against PLAN items (DRIVER §6 D24 ② fixes it: failure issues come before PLAN items; this task decides only the order among failure issues, and changing D24 ② needs an HQ to the owner under DRIVER §8); when a failure issue is closed; what happens when the nightly fails again after a fix (reopen or new issue, repeat bound and how the owner is told); exclusion against the §3 driver and measurement interference; and keeping the nightly run's records apart from case storage. Parts that touch the data plane or `ARCHITECTURE/` follow CLAUDE.md A-13 BLOCKED reasons and DRIVER §9.

Related readiness: T-0492 makes `python -m hilclaw.turn_start` keep exactly one outcome line on standard output under a real `-p` session, which an unattended nightly starter needs to read the outcome. If T-0492 is not `DONE` when this task is refined, add it to `dependsOn`.

`commitMode: code` is a provisional judgement: the entry point the routine calls is expected to be code (a 2nd-layer module or a POSIX sh script) plus a procedure document; if the refined scope ends up documents only, switch to `doc`.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task format, naming `claude/T-0493-<slug>`, `Task: T-0493` trailer, size cap, test rules D12 including rule ⑤, list-assertion rule D21); §1-5 (prohibitions; the nightly exception), §3-3 and §6 (the text the D17 (나) issue-to-task flow may change), §8 (HQ path), §9, §11 rows D16, D17, D22.
- `CLAUDE.md` (repo) — "개발 드라이버와 런타임의 구분" (the nightly exception and its limits), test rules, branch/merge procedure, language policy.
- `PROCESS/PLAN.md` — P2 head (order), P2-5, P2-9, P2-10, P2-15.
- `PROCESS/STATE.json` — `humanQuestions` entry HQ-0076 (its `decision` sets this task's scope).
- `PROCESS/RuntimeAcceptance.md` — header (the nightly result closes no item).
- `PROCESS/tasks/T-0490-first-run-round-zero-through-stub-session.md` and `PROCESS/tasks/T-0491-first-run-five-rounds-through-stub-session.md` — Result (the P2-5 configuration, the commands `hilclaw.new_run` and `hilclaw.turn_start`, the environment variables a run needs).
- `PROCESS/tasks/T-0492-turn-session-output-off-entry-stdout.md` and its ADR once landed.
- `hilclaw/new_run.py` and `hilclaw/turn_start.py` — module docstrings (entry command lines, outcome lines, exit statuses, the stated schedule limit about the lock of two loops on one run).
- `ARCHITECTURE/decisions/ADR-0122-od19-turn-loop-open-states.md` (decision 5, the starter) and `ARCHITECTURE/decisions/ADR-0155-od23-first-case-instance-start-command-line.md` (decision 5).
- `.claude/skills/dev-item-address/SKILL.md`, `.claude/skills/dev-code-review/SKILL.md`.

## Acceptance Criteria

Outline only; to be refined within the range of the HQ-0076 answer before the task is set back to `TODO`.

1. **Procedure document** for the nightly routine (place decided here, e.g. `PROCESS/NIGHTLY.md`): what the routine does per firing — sync, build/prepare the runtime, start the run of the configuration HQ-0076 names via `hilclaw.new_run` and `hilclaw.turn_start` (repeated starts as the outcome lines allow), record pass/fail and logs, register a failure issue; its machine, work folder, permission mode, time and usage cap exactly as HQ-0076 answers; the statement that its result is a regression signal only (D17 ②) and closes no runtime acceptance item. The routine's registration is the owner's (D17 ③) and is not done by this task.
2. **Entry point** the routine calls (place and language chosen here, reason in one line in Result): starts the run, reads each outcome line, decides pass/fail, writes the result record, and produces the failure issue body. Testable without a real `claude`.
3. **D17 (나) design**, recorded (in the procedure document, DRIVER text, or an ADR where it touches `ARCHITECTURE/` or the data plane): every item listed in Why's (나), including the DRIVER §3-3/§6 text by which the §3 driver accepts a nightly failure issue as a task and its order (D17 ④; DRIVER §6 says D17 ④ issues are not subject to the D18 priority judgement and their order is set by P2-10). DRIVER.md changes keep its style (Korean) and update the D17 row's "절차 본문은 PLAN P2-10이 만들 때까지 없고" statement in the header.
4. **Guard coexistence** exactly as HQ-0076 answers (nothing about the guard is decided beyond the answer).
5. **Tests** per CLAUDE.md test rules: a 2nd-layer module gets its test file with happy/error/branch/negative cases against a stub `claude` written by the tests and fake run outcomes; a script that is a driver helper or CI/hook script gets no tests (rule ⑤). Coverage gates hold.
6. **No real `claude`** is started by this task, its tests or its executor (D16; only the registered nightly routine does, D17 ③). Nothing requires a logged-in `claude`, Docker, an image, a token or weights on the development machine.
7. **Procedure**: branch `claude/T-0493-<slug>`, Draft PR with `T-0493` in the title and `Task: T-0493` as the body's last line, review cycle (≤ 7 rounds), CI green, squash-merge (DRIVER §5); DRIVER §9 owner notice if an OD is closed by an ADR.

**Refinement within the HQ-0076 answer** (executor, 2026-10-29; the outline above stands, read with these values):
- Configuration: the P2-5 configuration as it is (`cpu_standin` x GEMM fp32 row_major m=8 k=16 n=8, N=1, `round_budget` 5, the P2-5 test's tolerance and parameters); no real Llama 3.2 1B weights; daily KST 03:00; no cap beyond `round_budget` (no timeout, no turn count in the entry); same machine as the driver, separate clone, Bypass permissions, with Docker, images and the coder token prepared by the owner; the guard only in the driver clone's settings, the nightly clone without it.
- Paths: procedure document `PROCESS/NIGHTLY.md`; entry point `hilclaw/nightly.py` (`python -m hilclaw.nightly <base>`) with `tests/test_nightly.py`; DRIVER §1-5, §2, §3-3, §3 BLOCKED reasons, §6, §11 head and D17 row; `.claude/agents/dev-planner.md` one line. No ADR: the entry writes no data-plane record beyond what `hilclaw.new_run` and the run already write, into a per-firing data root.
- Repeated starts: the entry starts `turn_start` once per firing on the run it just created (ADR-0122's lock limit); anything but `run_over` is a failure.

## Out of Scope

- Registering the routine (owner, D17 ③) and running it.
- Any value of D17 (가) beyond the HQ-0076 answer; P2-15 beyond what that answer says.
- Changing the D16 prohibitions for the §3 driver and its sub-agents.
- The `claude` child-process guard hook itself (separate task after T-0107, DRIVER §1-5), except the coexistence rule HQ-0076 sets.
- Using nightly results for P2-9 acceptance or FR-18 case storage (D17 ②).

## Follow-ups

## Result
