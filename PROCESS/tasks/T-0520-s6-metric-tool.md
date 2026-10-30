---
id: T-0520
title: Compute the S6 verdict of one pair of runs from their recorded facts (PLAN P2-8, ADR-0074)
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [S6, FR-18, NFR-5, OD-30, "PLAN P2-8"]
dependsOn: []
touchesFiles:
  - hilclaw/s6_metric.py
  - hilclaw/timings_tool.py
  - tests/test_s6_metric.py
  - tests/test_timings_tool.py
estimatedSize: {loc: 500, files: 2}   # test code is outside the cap
hq: []
---
## Why

**State.** PLAN P2-8 is the calculation tool of the S6 acceptance criterion. [ADR-0074](../../ARCHITECTURE/decisions/ADR-0074-od30-s6-metric-one-pair.md) (T-0231, landed as 250b3df2) defines the metric of one pair of runs. Its Consequences say "The P2-8 code slice can be cut" and leave three things to this task: the names, the form of the input and output, and which moment's `instance.json` values are compared. No code computes the metric today. PLAN P2-9, the owner's acceptance measurement, judges its pair with this tool.

**Why now.** P2-8 is the first PLAN checklist item that nothing holds:

- P0.5-4 waits on HQ-0082.
- P2-12 waits on HQ-0083.
- P2-4 stays unchecked by the HQ-0080 ④ answer, and its gate check needs OD-3, which is owner-only.

P2-8 is a checklist item, so the D18 and D26 judgement of off-checklist work does not apply to it. No P2-15 work is available ahead of it: what remains of that work, the real weights, the tokenizer and the executor's entry point, waits on HQ-0084.

**Not waiting on an HQ.** HQ-0081 (how many pairs, a control run, the spend) is the scale of P2-9 and is unanswered. HQ-0081 itself says the P2-8 tool is not blocked. This task judges one pair and combines nothing.

**Objection window.** The #5 notice of ADR-0074 runs to 2026-11-07. An objection creates a task that reverts the record. That is not a reason to wait.

**RuntimeAcceptance.** No item has the status `실패` as of `main` `61aaf11c`.

**D16.** Verification uses run files and journal lines that the tests write. No real `claude`, Docker daemon or D25 test run is used, and this task needs none of them.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5 (branch `claude/T-0520-<slug>`, the `Task: T-0520` trailer in commits and as the last line of the PR body, the size cap, D12, D21), §3 "BLOCKED 사유", §8 (D22) and §9.
- `CLAUDE.md`: A-13 code mode, the BLOCKED reasons, the test rules, comment minimisation and the language policy.
- `PROCESS/PLAN.md`: P2-8 and P2-9.
- `ARCHITECTURE/decisions/ADR-0074-od30-s6-metric-one-pair.md`: all of it. This record is the specification. Where this task file and the record differ, the record wins, and the Result says so.
- `ARCHITECTURE/decisions/ADR-0140-od16-first-case-attempt-comparison.md`: decisions 3 and 4.
- `ARCHITECTURE/decisions/ADR-0110-od18-check-executions-hard-floor.md`: decisions 1 to 3.
- `ARCHITECTURE/decisions/ADR-0076-*.md`: decision 1 (the scope of the runs).
- Code:
  - `hilclaw/timings_tool.py`: `compare`, `timing_problem`, `_measurement`.
  - `hilclaw/harness/measurement.py`: `trimmed_mean`, `ratio_interval`, `DELTA`.
  - `hilclaw/check_standing.py`: `point_standing`.
  - `hilclaw/checks_tool.py`: `log_lines`.
  - `hilclaw/harness/timing_finding.py`: `run_found_at`.
  - `hilclaw/instance.py`: `read`.
  - `hilclaw/hypotheses_file.py`: `parse`.
  - `hilclaw/layout.py`: `hypothesis_record`.
  - `hilclaw/contract_table.py`: `start_covers`.
  - `hilclaw/new_run.py`: the form of a command-line entry, with one JSON line and its own exit status per kind.
  - `hilclaw/data_root_source.py`.
  - `hilclaw/model_run_binding.py`: an example of a read-only computation over one run.

## Acceptance Criteria

1. **The computation.** A new module `hilclaw/s6_metric.py` has a public function that takes a data root and two run ids in the order (first run, second run) and returns the outcome below.
   - It implements ADR-0074 decisions 1 to 5 and adds no rule of its own. Writing nothing is part of the contract: no file under the data root changes, including `best.json` and any verdict file.
   - It starts no process and no build. It is not registered in `hilclaw.tools` and has no MCP name.
   - Python: this is host-side layer-2 code beside the Python it reuses. State the language and reason in the Result.

2. **No second copy of the comparison.** The `lower`, `higher` or `not_different` rule of ADR-0140 decision 4 and the timing-result admission stay in one place.
   - Move what is needed out of `hilclaw.timings_tool.compare` into a public helper of that module, and call it from both.
   - `timings.compare` and `verdicts.write` keep their exact behaviour, and their existing tests pass with their assertions unchanged.
   - Do not copy `measurement.DELTA` or the thresholds.

3. **The moment of `instance.json`.** The comparison reads the file as it stands at the call, with `hilclaw.instance.read`, and the module docstring says so with the reason. This is the choice ADR-0074 leaves to this task. The tool reads current facts only and does not walk git history.

4. **Outcomes.** The result is one of:
   - **Not a pair**, naming the members that differ (decision 1's list, with "both leave it out" counting as equal).
   - **Outside the metric**, with its reason:
     - a run with no `op_signature` (this one forms no pair, per decision 1, and is reported as such);
     - a run outside the scope of ADR-0076 decision 1: hw_profile accelerator other than `cpu_standin` or the mock, or `contract_table.start_covers` false;
     - an objective other than exactly `latency_minimisation` with no constraint.

     The docstring states one limit of the scope check. ADR-0120 decision 1 also requires a new run written by the start function, and the files do not record that.
   - **A verdict** with the words of the record, exactly `met`, `not met` or `not applicable`, in decision 3's order, with the reason for `not applicable` ((i), (ii) or (iii)) or for `not met`. Do not use the file-value form `not_applicable` or `not_met` (ADR-0074 Consequences on names).
   - **A failure to read**: a damaged or missing `instance.json`, log or `hypotheses.json`. It is told apart from a verdict and never treated as `not met`. Reuse the kinds of the modules it reads where they exist.

5. **The report.** Beside a verdict, every item of decision 5 is present:
   - the first-run best (round, candidate, attempt), the first-run round, the second-run round or "not reached", and the attempt that reached;
   - the `case` entries found, by round and hypothesis;
   - the board measurement count of each run up to its count, or to its last recorded round where it has no such round;
   - what was left out, per run, up to its count and in all, by each reason of decision 5, and the attempts that did not reach for a reason of decision 2 other than the interval;
   - the first round of each run with a `verified` attempt at `board`, and the runs that each run's `cases_read` names;
   - the token spend, stated as not available with no figure;
   - each run's imprecise finding, through `timing_finding.run_found_at`;
   - whether `source_commit` and `draws` are equal.

6. **The entry.** `python -m hilclaw.s6_metric <first_run_id> <second_run_id>` follows `hilclaw.new_run`:
   - exactly two arguments, data root from `data_root_source`, one compact JSON object and one LF on standard output, and a distinct exit status per kind of outcome;
   - status 0 is any of the three verdicts, because a verdict is an answer;
   - the statuses are listed in the docstring.

   The module docstring is the owner's usage text for P2-9.

7. **Tests** (`tests/test_s6_metric.py`, following D12), on files the tests write:
   - **Happy path:** ADR-0074's worked example with its samples gives `met`, first-run round 3, second-run round 2, the first-run best at round 3, 4 and 3 board timing runs, one attempt left out as not converged and the first run found imprecise.
   - **Each boundary of the record:**
     - the record's boundary case with first-run round 1;
     - first-run round 0;
     - no qualifying attempt in the first run;
     - second-run round 0;
     - second-run round equal to the first-run round;
     - a second run that never reaches;
     - a second run faster with only `cases_read` and no `case` entry (`not met`);
     - a `case` entry only after the second-run round (`not met`);
     - a `case` entry naming another run (`not met`).
   - **Ties and earlier reaching:** the tie order of the first-run best (round, then candidate, then attempt), and a first-run round lower than the first-run best's own round because an earlier attempt reaches it.
   - **Qualification:** one attempt each for `not_converged`, `broken` only, several completed results, a `failure` end line, an open identity, and a standing other than `verified`, each counted under its reason.
   - **Decision 2's "does not reach":** a different `contract_key` or `shape`, and samples outside the domain.
   - **Not a pair:** one case for each member of decision 1's list, and a case where both leave a member out, which is equal.
   - **Attributes:** a differing `label`, `hw_source`, `source_commit` or `draws` still forms a pair, and the last two are reported.
   - **Outside the metric:** one case for each reason.
   - **Read failures:** a missing run, a damaged log line and a damaged `hypotheses.json`.
   - **The entry:** usage errors, no data root and each exit status.
   - **Files:** a test that the data root's files are byte-identical after a call.
   - **The moved helper:** tests for it in `tests/test_timings_tool.py`, if it is public.

8. **Existing tests.** Assertions keep their meaning. D21 still allows the edits it names to assertions that pin a list. If a test pins who may import a module (`tests/test_standin_profile.py` pins `hilclaw.standin_profile`, as T-0518 found), avoid naming that module: use a local constant, as `hilclaw.model_run_binding.TARGET` does. List any edited assertion in the PR body.

9. **Result** records the language and reason, the moment chosen, the statuses and any edited assertion. It also says whether PLAN P2-8's stated completion holds in the executor's reading, so that the driver can set its checkbox. The P2-9 runtime acceptance item follows from the PLAN rule; do not add it in this task.

10. **No record changes are expected.** ADR-0074 already answers the design, so `ARCHITECTURE/` needs no edit. If reading the facts shows a gap that needs a design decision no record gives, do not invent it: raise it as BLOCKED (DRIVER §3, §9).

## Out of Scope

- Several pairs, how verdicts combine, a control run with the case lookup off, and the spend (OD-30 sub-question ③, HQ-0081).
- Storing a verdict anywhere (ADR-0074 Boundaries).
- A token ledger (OD-19, NFR-5, #5 A-8).
- `best.json`, `best_ref` and any change to how a run orders its own attempts (OD-20, OD-13, OD-1).
- Other objectives, constraints, sim-only hardware and similar-key pairs.
- A real run, including a D25 test run, and running P2-9 (D16).
- Editing the sentences ADR-0074 Consequences lists as less exact.

## Follow-ups

## Result
