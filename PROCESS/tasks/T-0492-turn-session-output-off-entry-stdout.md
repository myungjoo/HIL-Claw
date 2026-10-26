---
id: T-0492
title: Record where the standard output and standard error of a first-case turn session go, so that `python -m hilclaw.turn_start` keeps writing exactly one line on its standard output under a real `-p` session, as one new ADR, and land it in `hilclaw/turn_loop.py` with tests (removes T-0490's strict xfail)
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [FR-1, FR-4, NFR-1, OD-19, OD-17, OD-18, S0, S2, D17, "PLAN P2-10", "PLAN P2-14"]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0175-od19-first-case-turn-session-output.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
  - hilclaw/turn_loop.py
  - hilclaw/turn_start.py
  - tests/test_turn_loop.py
  - tests/test_turn_start.py
  - tests/test_first_run_end_to_end.py
  - tests/first_run_stubs.py
estimatedSize: {loc: 260, files: 6}   # non-test: ADR ~180, turn_loop.py ~30 (code + docstring), turn_start.py docstring ~10, registers ~10, StandardScenarios only if the coverage re-check changes a verdict. Tests are outside the cap; the ADR's lines count (DRIVER §5, D4/D20). The ADR file name is a suggestion: use the next free ADR number and the OD the record is filed under.
hq: []
---
## Why

**The gap** (T-0490 Follow-ups, `PROCESS/tasks/T-0490-first-run-round-zero-through-stub-session.md`): `hilclaw/turn_loop.py` starts each turn session with the calling process's standard output and standard error ("its standard output and standard error are those of the calling process and are not read here", module docstring; the `subprocess.run` call in the turn function passes neither `stdout` nor `stderr`). A `-p` session writes its reply to its standard output. So under a real session — and under the stub `claude` of `tests/first_run_stubs.py`, which behaves the same way — the reply text lands on the entry's standard output before the one JSON line, and the rule of `hilclaw/turn_start.py` (after ADR-0122 decision 5 and ADR-0125 decision 5) that "Standard output gets exactly one line" does not hold. If a reply does not end with a line feed, the JSON line is glued onto the reply's last line and even "read the last line" fails. T-0490 marked this `xfail(strict=True)` in `tests/test_first_run_end_to_end.py::test_the_entry_writes_one_line_on_standard_output`, saying no record chooses where a session's output should go; whatever task makes that choice removes the marker. The same holds for standard error: `hilclaw/turn_start.py` says standard error "gets nothing for an outcome", which a session writing to standard error also breaks.

**Why this is planned now (DRIVER §6, D18).** It is not a PLAN checklist item; it is a follow-up of T-0490. The judgement:
- The starter of the entry is "a person or a CI through the entry, or an OS schedule" (ADR-0122 decision 1). An unattended starter acts only on the outcome line. PLAN P2-10, the next checklist item in PLAN P2's order, is such a starter: the nightly routine (D17) starts the runtime with a real `claude` and must read whether the run ended `run_over`, `failed_turn`, `unchanged_turn` or `open_state` to record a pass or failure as its regression signal. Under the present code that line is not reliably readable.
- P2-14's verification drives the run through a stub `claude` that writes its reply on standard output like a real `-p` session (D16); the entry's stated contract fails there too, today hidden only by a test that reads `splitlines()[-1]`.
- It is not input hardening, wording or a refactoring: the behaviour of a real run differs from the recorded contract. Where the planner could not fully settle "needed for P2-14", DRIVER §6 says to make the task and give the reason here; this is that reason.

**No RuntimeAcceptance `실패` item is fixed by this task** (none exists as of `main` `9cf2be14`).

**Design level, not owner-only.** Where a turn session's two streams go is a choice inside the turn loop (ADR-0118 decision 3, ADR-0122), a design-level OD under DRIVER §9 — no #5 A/B item, C-6, OD-25 or OD-3. File the record under the OD the executor finds the turn loop's records filed under (ADR-0122 is filed under OD-19 and OD-17; name the one used in the title and the file name). Per D20 ① the ADR and its code slice are one code-mode task.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task format, naming convention `claude/T-0492-<slug>`, `Task: T-0492` trailer, size cap, test rules D12, list-assertion rule D21), §9 (ADR path: Approve, OD status, owner notice on #5 with `— posted by driver`).
- `CLAUDE.md` (repo) — "상시 규칙" (comments, coverage re-check, "미결은 발명하지 않는다", branch/merge procedure, test rules, language policy).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `PROCESS/tasks/T-0490-first-run-round-zero-through-stub-session.md` — Follow-ups and Result (the gap, the stub's behaviour).
- `hilclaw/turn_loop.py` — module docstring paragraph "The command line" (lines ~73-89) and the turn function around the `subprocess.run` call (lines ~430-460).
- `hilclaw/turn_start.py` — module docstring "What the starter is told" and the paragraph after it (lines ~55-100); `main`.
- `ARCHITECTURE/decisions/ADR-0122-od19-turn-loop-open-states.md` — decisions 1 and 5, Alternatives, Boundaries.
- `ARCHITECTURE/decisions/ADR-0125-od18-self-check-in-round-zero.md` — decision 5 (the report on the entry's line; O7 and ⑯ (나): where the record is stored and "the instance's log" stay open).
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md` — decision 3 (the turn loop, its starter).
- `ARCHITECTURE/decisions/ADR-0139-od18-first-case-turn-session-permissions.md` — decision 8 (the turn command line).
- `ARCHITECTURE/decisions/ADR-0155-od23-first-case-instance-start-command-line.md` — decision 5 (the same one-line form for `new_run`, as precedent).
- The latest ADR (`ARCHITECTURE/decisions/ADR-0174-od23-first-case-earlier-verdicts-read.md`) for the present ADR form (Status, Context, Decision, Walk-through, Alternatives considered, Consequences, Boundaries, References).
- `ARCHITECTURE/Requirements.md` — the "행 형식" paragraph and the row of the OD the record is filed under.
- `ARCHITECTURE/OpenDecisionProposals.md` — header "기록 규칙" and the section of that OD.
- `ARCHITECTURE/StandardScenarios.md` — the rule section near the top and the first paragraph of §검사 결과.
- `tests/test_first_run_end_to_end.py` (the xfail test and the `world` fixture) and `tests/first_run_stubs.py` (what the stub `claude` writes to its standard output and standard error).
- `tests/test_turn_loop.py` (how the turn's `subprocess.run` call and stub sessions are tested) and `tests/test_turn_start.py` (`test_one_line_on_standard_error` and the standard-output tests).

## Acceptance Criteria

1. **ADR** — one new file `ARCHITECTURE/decisions/ADR-NNNN-…md` (next free number; ADR-0175 as of `main` `9cf2be14`) in the form of the latest ADRs, that decides for the turn sessions of the runs of ADR-0120 decision 1:
   - where a turn session's **standard output** goes and where its **standard error** goes (each separately), with reasons and an Alternatives table that weighs at least: the entry's own streams (today), discarding (`DEVNULL`), the entry's standard error, and a file outside the run;
   - what the starter can and cannot still see of a session after the choice (diagnosis of a failed turn), and how this squares with `hilclaw/turn_start.py`'s "Standard error gets nothing for an outcome";
   - **constraints it must keep, stated as cited**: ADR-0122 decision 1 as kept in `hilclaw/turn_start.py` (the entry writes nothing into the run "or anywhere else on the starter's behalf"); no new file in the data plane (`runs/<run_id>/`, `db/`, any file of the data repository) — a choice that needs one is a data-plane schema change, a CLAUDE.md A-13 BLOCKED reason; it must **not define "the instance's log"** nor where the self-check's record is stored (ADR-0125 decision 5, O7 and ⑯ (나) are open and partly owner's). If the executor finds that every acceptable choice needs one of these, stop and return BLOCKED with the question (DRIVER §8) instead of choosing;
   - that the self-check session is not touched (it already captures its output, `hilclaw/selfcheck_session.py`);
   - Boundaries: what stays open, including anything left to the nightly routine of PLAN P2-10;
   - any new runtime acceptance item (a fact only a real `-p` session shows, e.g. whether a real session writes anything the choice loses that the starter needs) is listed and handed to `PROCESS/RuntimeAcceptance.md` (DRIVER §8, D22) by naming it in the task's Result; the ADR says it hands the item to that file.
2. **Registers** — follow the recording rules written in the files themselves, without copying wording from earlier task files: in `ARCHITECTURE/Requirements.md` follow the "행 형식" paragraph (one link for the new ADR after `**확정분**:`, the open part rewritten in place under `**잔여**:`, the status cell kept short; no restatement of the ADR, no dated chain); in `ARCHITECTURE/OpenDecisionProposals.md` follow the header's "기록 규칙" (one `**채택분**` line for the ADR in that OD's section; a sub-question's end state rewritten in place only if one is answered); in `ARCHITECTURE/StandardScenarios.md` re-check coverage by its rules (CLAUDE.md) and record only as the first paragraph of §검사 결과 says (a history line only if a verdict changes).
3. **Code** — `hilclaw/turn_loop.py` starts each turn session with the streams the ADR chose; the module docstring paragraph "The command line" says it (replacing "its standard output and standard error are those of the calling process and are not read here"). If the choice makes the loop own a file or a stream, every failure path of it is handled and stated (no traceback reaches the starter; `hilclaw/turn_start.py`'s error kinds are unchanged unless the ADR changes them). `hilclaw/turn_start.py`'s docstring is brought in line where it describes standard output or standard error. The exit status of a turn, the command line, the environment, the working directory and closed standard input stay as they are.
4. **Tests** (D12: happy, error, branch and negative cases; every public function of the touched modules stays covered; coverage gates hold):
   - remove the `xfail(strict=True)` marker from `tests/test_first_run_end_to_end.py::test_the_entry_writes_one_line_on_standard_output`; the test passes as written (exactly one line on the entry's standard output) with the stub `claude` still writing its reply to its standard output;
   - add to that test, or a sibling, that the entry's standard error after a `run_over` start holds nothing (or exactly what the ADR says it holds);
   - in `tests/test_turn_loop.py`: a stub session that writes to both its standard output and its standard error — the bytes end up exactly where the ADR says and nowhere else (the calling process's streams checked at the file-descriptor level, e.g. with `capfd` or by running the loop in a child Python process); a session that writes a reply with no trailing line feed; a session that writes nothing; and, if the ADR makes the loop own a file or stream, the failure of opening/writing it (negative case) and that the turn's exit status is still returned;
   - existing tests keep passing. Under D21, assertions that pin a list of public names, imports, fields or binders may be edited only as far as this change requires and are listed in the PR body; none is foreseen (no public name is expected to be added), but if the ADR adds a module constant (for example a stream or file name) to `hilclaw/turn_loop.py`, a public-name set asserted in `tests/test_turn_loop.py` may need it. Other existing assertions are not weakened.
5. **No real `claude`**: tests use only stub `claude` programs written by the tests (D16). Nothing requires a logged-in `claude`, Docker, an image or a token on the development machine.
6. **Procedure**: branch `claude/T-0492-<slug>`, Draft PR whose title holds `T-0492` and whose body ends with `Task: T-0492`, review cycle (dev-code-review, ≤ 7 rounds), CI green, squash-merge with that body (DRIVER §5). After merge, the §9 owner notice on #5 for the OD the ADR is filed under (7-day objection window), ending with `— posted by driver`. Result records the language choice (Python, the module's language) in one line.

## Out of Scope

- The nightly routine itself, its entry point, run configuration and result recording (PLAN P2-10; its owner questions (D17 (가)) are asked separately).
- Defining "the instance's log", where the self-check's record is stored (ADR-0125 O7, ⑯ (나)), or any notification channel (OD-27).
- The lock of two loops on one run (rest of OD-17) and the limit `hilclaw/turn_start.py` states about schedules.
- `hilclaw/new_run.py` and the self-check session (they do not hand their standard output to a session).
- Changing what the stub `claude` writes, except where a test needs the stub to write to standard error or omit a trailing line feed.

## Follow-ups

## Result
