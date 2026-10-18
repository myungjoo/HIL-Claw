---
id: T-0302
title: Write ADR-0103 on how a measurement or a run is found to be taken in an imprecise timing environment — OD-13 sub-question ⑪ (가); no code
phase: P1
status: DONE
commitMode: doc
coversReq: [OD-13, NFR-3, FR-10, OD-14, "#5 D6", "owner decision 2026-10-15 item 3"]
dependsOn: []
touchesFiles: [ARCHITECTURE/decisions/ADR-0103-od13-imprecise-timing-detection.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 180, files: 4}
hq: []   # Design-level OD (DRIVER §9): OD-13 is not on the owner-only list. The owner's decision of 2026-10-15 item 3 left "how such an environment is detected" open without reserving it; parts (다) reuse/absolute target and (라) where the warning shows are out of scope here. Independent of every open HQ: HQ-0021..HQ-0029 concern OD-18 run-tool / check records, OD-30, instance members, profiler.collect, the build log, clang_build/local_run env checks and a shared JSON helper; HQ-0013, HQ-0014, HQ-0016..HQ-0019 are runtime-acceptance. No overlap with open PR #179 (hilclaw/clang_build.py, tests/test_clang_build.py).
---
## Why

The owner decided on 2026-10-15 (item 3, https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6182984913) that a run whose timing is hard or imprecise does not stop. It continues on relative numbers under ADR-0007 as it stands. Every report of such numbers to the user carries a warning. Recording in the data plane that a measurement or a run was made in such an environment is approved, and a record decides its form. NFR-3 states this. The owner left open how such an environment is detected: "a known environment class, measured noise, or both".

OD-13 registered this as sub-question ⑪ with four parts: (가) detection, (나) the record, member and form of the mark, (다) reuse across runs and judgement against an absolute target, (라) where the warning is shown. Nothing has answered any part. ADR-0061 Limit 3 and ADR-0063 Limit 5 say only that their records leave it untouched. Both the warning and the mark need a rule that says when a measurement or a run counts as imprecise, so (가) comes first. This task writes one design record (DRIVER §9) that answers ⑪ (가). It decides no place or form of the mark (that is (나), the expected next task). It writes no code and changes no data-plane schema.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (line 72: executor procedure, resume rule, time limit), §5 (lines 86-115: task format, naming convention, `Task:` trailer, size limit), §8 (lines 135-139: the driver tail of #5 comments), §9 (lines 141-149: OD closing authority, ADR + reviewer Approve + #5 notice).
- `CLAUDE.md` "상시 규칙": "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode).
- `ARCHITECTURE/Requirements.md` line 46 (NFR-3, the owner's sentence as recorded), lines 80-86 (정본 규칙 and **행 형식** at line 84: the only rule for editing a register row), line 104 (OD-13 row), line 105 (OD-14 row).
- `ARCHITECTURE/OpenDecisionProposals.md` lines 1-10 (header; **기록 규칙** at line 8: the only rule for edits to this file), lines 190-206 (OD-13 section: adopted lines 194-196, the owner decision at 202, the integrator note at 203, sub-question ⑪ at 204), and in the OD-14 section (from line 208) the sub-question ① bullet, part (마) only (timing inside a container). Read OD-14 ① only so that the record does not decide it by accident.
- `ARCHITECTURE/StandardScenarios.md` lines 13-29 (검사 규칙), S9 (lines 148-155), lines 168-172 (§검사 결과; its first paragraph at line 170 is the recording rule for the "최근 재검사" line).
- `ARCHITECTURE/decisions/ADR-0007-od13-measurement-policy.md` lines 1-47 (Status, Context, decisions 1-4: CV, `n_min`/`cv_max`/`n_max`, "not converged"), lines 60-103 (decisions 7-10: judging a difference, parameters and identification, reproducible judgement, limits), lines 142-159 (Consequences, Boundaries).
- `ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md` lines 65-93 (decisions 7-8: repeat loop, stopping rule, what the driver reports) and lines 111-end (limits).
- `ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md` lines 16-38 (Context with O5, decision 1 scope) and lines 113-122 (Limits, especially 2 and 3).
- `ARCHITECTURE/decisions/ADR-0063-od18-run-tools-result-members.md` lines 37-44 (decision 2, `outcome`), lines 66-76 (decision 4, intervals and resolution), lines 113-145 (decision 9, the closed member list), lines 170-181 (Limits 5 and 10), lines 216-232 (Boundaries).
- `ARCHITECTURE/decisions/ADR-0102-od8-spend-axis-change.md` Status section only, as the model of a Status bullet list for a §9 record (including the objection window line).

## Acceptance Criteria

1. **Pre-check.** Before writing, confirm that `ARCHITECTURE/decisions/ADR-0103-*` does not exist on `origin/main` and that no accepted record has answered OD-13 ⑪ (가) since this task was written (`git log origin/main -- ARCHITECTURE/OpenDecisionProposals.md`, and the ⑪ bullet). Run the CLAUDE.md "세션 진입 점검": open PRs and issues #4, #5, #7, #8. If the number is taken, use the next free one and say so in `## Result`. If ⑪ (가) has been answered or an owner comment on #5 addresses it, stop and report BLOCKED (requirement unclear).
2. **The record.** One new file, `ARCHITECTURE/decisions/ADR-0103-od13-imprecise-timing-detection.md`, in English, with the sections the sibling records use: Status, Context, Decision (numbered), Alternatives considered, Consequences, Boundaries (not decided here), References. The Status says it closes OD-13 ⑪ (가) for the scope it states, cites DRIVER §9, and states the 7-day objection window from the #5 notice.
3. **What it decides (⑪ (가)).** Within a scope it states explicitly, the record answers what makes a measurement, and what makes a run, count as "taken in an environment where timing is hard or imprecise" in the owner's sense. The suggested scope is the runs of ADR-0061 decision 1 (the first case's local configuration and runs whose hw_profile points at the mock). A narrower or wider scope is allowed if the record gives its reason. At minimum the record states:
   - whether detection uses a known environment class, measured noise, or both (the owner's three options), and why;
   - which inputs it uses, preferring values that the accepted records already produce (for example ADR-0007's CV and "not converged", ADR-0063's `outcome`, `resolution_ns`, `intervals_ns`). If it needs a new input, it names what and who would produce it, and leaves the producing to a later record;
   - whether the finding is per measurement, per run, or both, and how a run's finding follows from its measurements (or why it does not);
   - at which moment it is found, and whether a later reader can reproduce the finding from what is kept (ADR-0007 decision 9);
   - any constant it introduces, with an initial value and the reason for it, as ADR-0007 decision 4 did, and whether that constant is an instance parameter (cite ADR-0007 decision 8 and OD-13 sub-question ④; do not decide ④ beyond this constant).
4. **Alternatives.** At least: (a) known environment class only, (b) measured noise only, (c) both, (d) the user declares it as an instance parameter. Weigh each against the owner's text, C-7 (the same behaviour on every machine kind), ADR-0007 and what a run on `cpu_standin` can actually observe.
5. **What it must not decide or change.** The record leaves the following open and names them under Boundaries:
   - ⑪ (나): the record, member and form of the mark;
   - ⑪ (다): reuse across runs (FR-18) and judgement against an absolute target (FR-2);
   - ⑪ (라): where the warning is shown (OD-27);
   - OD-14 ①: the build/run container design, including (마);
   - OD-13 ① (paired re-measurement) and ⑥ (the spread measure).
   It does not change ADR-0007's improvement rule, because the owner said "as it stands". It does not stop a run, add or change a member of any tool result (ADR-0063 decision 9), add a `step` value, an event kind or a spend axis, raise any `schema_version`, or change any data-plane schema. If (가) cannot be answered without deciding one of these, stop and report BLOCKED (requirement unclear) with the proposed owner question in `## Result`.
6. **Runtime facts (D16).** The record may rest on a fact that only a runtime machine can establish, for example how a process inside the VM of Docker Desktop can tell where it runs, or what CV a container on macOS or WSL shows. If so, it lists that fact as a Limit, and `## Result` lists it as a runtime-acceptance item for the driver to raise through DRIVER §8. Nothing is tried on this machine. No `claude`, container, compiler or timing run is started.
7. **Records not edited.** The record does not edit ADR-0007, ADR-0009, ADR-0061 or ADR-0063. Each statement there that becomes less exact (for example ADR-0061 Limit 3 and ADR-0063 Limit 5, "untouched") is listed under the record's Consequences as "not edited and now less exact".
8. **Register edits.** Follow the rules written in the files themselves. Do not copy wording from earlier task files and do not restate the record.
   - `ARCHITECTURE/Requirements.md`: OD-13 row only, as the **행 형식** at line 84 prescribes. Add one link to the new ADR with a few words of topic after `**확정분**:`, and rewrite the ⑪ part of `**잔여**:` in place so it says what remains. Extend the status date range if the format requires it. The status word stays. NFR-3 is not edited.
   - `ARCHITECTURE/OpenDecisionProposals.md`: OD-13 section only, as the **기록 규칙** at line 8 prescribes. Add one adopted line for the new ADR in the place the rule gives. Rewrite the ⑪ bullet's tail status and head status word in place: (가) answered for the stated scope, (나)(다)(라) left. Keep the question's wording. Add no dated paragraph. If the record registers a new sub-question, add it as the rule says and name it in `## Result`.
   - `ARCHITECTURE/StandardScenarios.md`: re-check coverage under 검사 규칙 (at least S2, S9 and every scenario citing NFR-3 or OD-13). Update the "최근 재검사" line as the first paragraph of §검사 결과 (line 170) prescribes. Add a history entry only if a verdict changes or a gap is found or closed.
9. **Mode and landing.** Document mode (CLAUDE.md A-13): branch `claude/T-0302-adr-od13-imprecise-timing-detection`, context-isolated reviewer cycle (dev-code-review, at most 7 rounds), rebase on `origin/main`, one squashed commit on `main` with trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0302` in the last paragraph, no force push, branch deleted. `git diff --check` is clean, files use LF only, and every new relative link resolves.
10. **#5 notice (DRIVER §9).** After landing, post the OD-closing notice on issue #5 in English. Its last line is `— posted by driver`, and it states the commit, the scope and the 7-day objection window. Record its URL in `## Result`.

## Out of Scope

- Any code: no detection function in `hilclaw/`, no change to `hilclaw/` or `tests/`. A later code task applies the rule once ⑪ (나) fixes where the mark goes.
- ⑪ (나), (다), (라); OD-14 ①; OD-13 ①, ③, ④ (beyond a constant this record introduces), ⑥, ⑦, ⑧, ⑩; OD-16; OD-27; FR-2 or FR-18 semantics.
- Editing NFR-3, any FR, any existing ADR, `ARCHITECTURE/StepValues.md`, `ARCHITECTURE/EventKinds.md`, `ARCHITECTURE/SpendAxes.md` or `README.md`.
- Any runtime check (D16).

## Follow-ups

- (doc, expected next task) An ADR on OD-13 ⑪ (나): the record, member and form of the mark, using this record's finding. If the mark goes into a tool result, that is a result-definition change under ADR-0100 (new `step` values, `ARCHITECTURE/StepValues.md` rows, ADR-0063's table), so the task must be planned within the size cap.
- (runtime-acceptance, only if criterion 6 applies) The facts listed there, for the driver to raise through DRIVER §8.

## Result

- DONE. Landed on `main` as 274fed8 (document mode, one squashed commit); reviewer agent 6 rounds, final Approve with no findings. Branch deleted, local and remote.
- Pre-check: ADR-0103 was free, ⑪ (가) was unanswered on `origin/main`, and #5 had no owner comment on it. Open PR #179 does not overlap.
- New file `ARCHITECTURE/decisions/ADR-0103-od13-imprecise-timing-detection.md`. It answers ⑪ (가) for the runs of ADR-0061 decision 1, using both grounds, either one sufficient:
  - measured ground: `outcome` `not_converged`, or resolution above `resolution_share_max` = 1 % of the shortest interval (new policy constant, not an instance parameter);
  - class ground: the timing run executed as a VM guest. The input is named; producing it is left to a later record with OD-14 ①;
  - a run counts from its first finding on.
- Register edits: OD-13 row (one link, `잔여` ⑪ rewritten, range ~18); the OD-13 section (one adopted line, ⑪ set to 일부 답함 with a partial-answer tail). StandardScenarios recheck covered S0, S1-b, S2, S5, S6, S9 and S10: no verdict change, no gap. No sub-question was registered.
- #5 notice: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6248388913
- Runtime-acceptance (ADR-0103 Limit 2; raise via DRIVER §8):
  - (1) whether and how a process in the Docker Desktop VM on macOS or Windows, or under WSL 2, can tell that it is a VM guest;
  - (2) what CV and resolution timing runs show there and in a container on native Linux;
  - (3) that WSL 2 runs its kernel in a VM;
  - (4) that VM distortion shows mainly as additive overhead or drift, not in one measurement's CV.
- Deviation: the landed commit puts `Co-Authored-By` in a paragraph after `Reviewed-by` and `Task:`, so those two trailers are not in the last paragraph. `git log --grep='^Task: T-0302'` still finds the commit. Fixing it would need a force push, so it was left as is.
- Runtime-acceptance items raised by the driver as HQ-0030 (notice only; does not block this task).
- Follow-up: (doc) an ADR on ⑪ (나), as planned.
