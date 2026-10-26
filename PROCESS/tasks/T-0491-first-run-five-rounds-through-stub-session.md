---
id: T-0491
title: Extend PLAN P2-5's stub end-to-end run to the five rounds of a `cpu_standin` x GEMM, N=1 first-case run (rounds >= 1 with selection, coder call, checks, timing, verdicts, cases and round end), with tests
phase: P2
status: TODO
commitMode: code
coversReq: [S0, S1, S8, S11, FR-1, FR-11, FR-15, FR-17, FR-18, "PLAN P2-5", "PLAN P2-6", "PLAN P2-7", D16]
dependsOn: [T-0490]
touchesFiles:
  - tests/test_first_run_end_to_end.py
  - tests/first_run_stubs.py
  - hilclaw/   # only for a defect the run reveals (criterion 4); name each file in the PR body and in ## Result
estimatedSize: {loc: 60, files: 2}   # non-test lines only for defect fixes, if any; the stubs and the test are test code and outside the cap (DRIVER §5, D4/D20). Use the file names T-0490 actually landed.
hq: []
---
## Why

PLAN P2-5 is the first end-to-end run: `cpu_standin` x GEMM, N=1, 5 rounds. The driver verifies it with a stub `claude` that a test writes (D16). T-0490 built the stub `claude` (which speaks MCP to the package's front and runs the session's hooks) and the stub `docker`. It also drove round 0 of a first-case run through `python -m hilclaw.new_run` and `python -m hilclaw.turn_start`. This task carries the same run through rounds 1 to 4. Under ADR-0121 decision 4, round 0 counts and a `round_budget` of 5 gives rounds 0 to 4. ADR-0172 Consequences says: "A whole round >= 1 through a stub `claude` is PLAN P2-5's verification."

When this task lands, the planner reads P2-5 as met: its verification is this stub run, and its completion does not depend on a real run (PLAN P2-5; D17). The real-`claude` run belongs to the nightly routine (P2-10).

No ADR is planned: the task writes test code that replays the landed definitions. Its choices are test choices: the hypotheses and techniques the stub selector writes, the kernel variants the stub coder brings and the verdicts the stub evaluator gives. The definitions leave these to the agents' judgement.

Start by reading T-0490's `## Result` and its landed test files. If T-0490 marked a step `xfail` for a gap, or left a follow-up that rounds >= 1 need, deal with it first as criterion 4 says.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5 (including D21 on pinning lists).
- `CLAUDE.md`: "개발 드라이버와 런타임의 구분" (D16), "테스트 규칙" (rule ⑤: no tests of the stubs), "미결은 발명하지 않는다".
- `PROCESS/tasks/T-0490-first-run-round-zero-through-stub-session.md` (whole, `## Result` first) and the test files it landed.
- `PLAN.md` P2-5, P2-6, P2-7 lines.
- The definitions the stub replays for rounds >= 1:
  - `orchestration/round-manager.md` ("The round steps" 6 to 12, "The closing steps of a round", "The end of a session");
  - `orchestration/agents/technique-selector.md`, `coder-driver.md`, `evaluator.md` and `experiment-runner.md`;
  - `catalog/cpu_standin/*.md`.
- Records, at the decisions named:
  - ADR-0171 (technique choice and the coder-driver's delegation);
  - ADR-0172 (steps after the coder call, decisions 2 to 7);
  - ADR-0151 (round >= 1 spec);
  - ADR-0132 (`hypotheses.write`; selection order);
  - ADR-0150 (`catalog.read`);
  - ADR-0173 (`cases.lookup`);
  - ADR-0174 (`verdicts.read`; decision 6, the order of reads);
  - ADR-0059 and ADR-0071 (the hypothesis and verdict records);
  - ADR-0128, ADR-0131 and ADR-0140 (`verdicts.write`, `checks.read`, `timings.compare`);
  - ADR-0133 (`case.write`) and ADR-0072 (the case file under `db/<hw_profile_key>/<op_signature>/`);
  - ADR-0135 (`round.end`);
  - ADR-0121 decision 4 (when the run is over).

## Acceptance Criteria

1. **Stub `claude`, rounds >= 1.** Extend T-0490's turn-session replay to the round >= 1 steps of `orchestration/round-manager.md` and to each delegated agent's requests, in the order the definitions give. At least:
   - the technique-selector's reads before its record: `cases.lookup`, `catalog.read`, `hypotheses.read`/`checks.read` where the definition asks for them, and `verdicts.read` once for each earlier round from 1 to r-1 in ascending order (ADR-0174 decision 6). Then one `hypotheses.write` whose hypotheses name catalog techniques and cite their sources as the definition requires;
   - the coder-driver's `spec.write` for the round (ADR-0151) and `coder.run`. The stub `docker` brings in a kernel variant per round (for example a loop-order or blocking variant of the GEMM kernel; the test supplies the sources), each correct under ADR-0008;
   - the evaluator's `sim` and `board` checks of (`r`, 1, 1);
   - the experiment-runner's `board.run`;
   - the evaluator's verdicts delegation (`checks.read`, `hypotheses.read`, `timings.compare` as ADR-0140 gives it, then `verdicts.write`);
   - the Round-Manager's `case.write`, `round.end` and `run.commit`.

   The stub's choices (which technique, which verdict) are fixed by the test, and each must be one the definitions allow. Hooks run as in T-0490 for every call.
2. **The five-round run** (`round_budget` 5, `candidates_per_round` 1, `cpu_standin` x GEMM fp32). Use the same instance shape as T-0490 unless its `## Result` gives a reason to change. Started with `python -m hilclaw.new_run` and driven by one `python -m hilclaw.turn_start <run_id>` as child processes.
   - **Happy path, asserted**:
     - the outcome line is `run_over`, exit 0, after five turns that each began and ended one round;
     - `STATE.json` holds `round` 5 and `run_status` `"over"`;
     - for each round 1 to 4: the hypothesis record, the spec, the attempt `rrrr/01/01`, the check results, the timing result, the verdicts file and the case file exist where the records place them, and each passes the package's own parser or validator;
     - every verdict names a hypothesis of its round's record (FR-17);
     - in rounds 2 to 4 the stub log shows `verdicts.read` for each earlier round, in order, before `hypotheses.write` (FR-17 "앞선 판정을 입력으로");
     - the data repository's history holds one commit per turn at least, and a clean tree for the run's files;
     - `events.ndjson` and `artifacts.json` parse.
   - **FR-18 / S11, a second run on the same key**: start a second instance with the same hw_profile and `op_signature`. Drive its round 0 and round 1 (`round_budget` 2). Assert that its selector's `cases.lookup` in round 1 returns the first run's cases, and that its hypothesis record carries the case reference as ADR-0173 says. A case reference is a hint, not a target (FR-15).
   - **Branch / error / negative**, each a separate test:
     - a round >= 1 whose stub coder brings no kernel (empty `taken`): the run goes to the verdicts step and the round still ends (ADR-0172 decision 2);
     - a round >= 1 whose kernel fails the `sim` check: no `board` check or `board.run` follows, and the round goes to the verdicts (decision 3);
     - a selector call refused by the caller check (for example `verdicts.write` requested by the technique-selector): the hook refuses it and the server sees no such call;
     - a turn that stops at step 12, because the verdicts are not written (decision 5): the outcome line and the files left are as ADR-0172 decision 7 and ADR-0122 decision 5 say.
3. **Platform and tools**: as T-0490 criterion 4. Skip with a stated reason where `os.getuid`, git or the needed host `clang` is missing. CI's Linux job runs these tests and they pass there. Never start a real `claude` or `docker` (D16). State the module's measured run time in `## Result`. If the five-round test is too slow for CI, shrink the shape or the draws within what the records allow, and say so.
4. **Defects the run reveals**: as T-0490 criterion 5.
   - Fix one that needs no design choice, with unit tests in the module's own test file (D12).
   - Mark a gap that needs an unmade design choice `xfail(strict=True)` and name it in `## Follow-ups`.
   - Return BLOCKED with a Korean question for an owner-only gap (DRIVER §8).
   - Pinning lists (D21) change only with a public name; list each in the PR body.
5. **Checks**: `python -m pytest`, `ruff check .`, `ruff format --check .`; `hilclaw/` coverage stays at line >= 80% and function >= 80%; the test-presence check holds; CI green before the squash-merge.
6. **Landing**: the commit body names the language and the reason in one line. The PR body ends with `Task: T-0491`.
7. **Result.** In `## Result`, write:
   - the run's asserted outcome per round;
   - the stub choices per round (technique, kernel variant, verdict);
   - the second run's case reference;
   - defects fixed and gaps marked;
   - the module run time;
   - new runtime acceptance items not already in `PROCESS/RuntimeAcceptance.md`, for the driver to add there (not as an HQ);
   - in the executor's reading, whether PLAN P2-5 is met, and whether P2-1, P2-2, P2-3, P2-4, P2-6 or P2-7 showed any first-case gap in this run (for the planner and the driver's PLAN checkboxes).

## Out of Scope

- Any new ADR or `ARCHITECTURE/` edit; any data-plane schema change (a BLOCKED reason, CLAUDE.md A-13).
- N > 1, Best-of-N, ranking or `best.json` (#5 A-4, OD-7, OD-29); profiles (ADR-0130); `eval.json` (OD-20).
- The nightly routine (P2-10), the S6 tool (P2-8) and the S6 measurement (P2-9, runtime acceptance); any real `claude`, Docker or API key (D16).
- Tests of the stubs themselves (CLAUDE.md test rule ⑤); `.claude/settings.json`, `.claude/settings.local.json`; any new external dependency.

## Follow-ups

## Result
