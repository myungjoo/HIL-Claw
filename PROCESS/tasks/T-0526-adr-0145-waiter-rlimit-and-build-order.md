---
id: T-0526
title: Correct ADR-0145 on what a kernel can do to the waiter's limits and state why the waiter's build comes second (HQ-0080 group D)
phase: P2
status: DONE
commitMode: doc
coversReq: [HQ-0080, OD-14, NFR-4]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0145-od14-first-case-container-measurement.md
estimatedSize: {loc: 15, files: 1}
hq: []
---
## Why

The owner approved group D ("design hardening") of the PLAN hold section in HQ-0080. Two of its three lines are the T-0399 follow-ups on ADR-0145. The lines are not judged again here, and P2-15 does not need the work. The third line is T-0527.

- **The waiter's limits.** ADR-0145 decision 5 says "this record knows of no way for a kernel to make W5 fail". `prlimit(2)` lets a process of the same user change another process's resource limits, and decision 5 does not weigh that. The kernel's process could use it on the waiter between W2 and W4.
- **The order of the builds.** ADR-0145 decision 3 builds the waiter after the timing build, and both share B_t. A kernel that compiles slowly can leave the waiter too little time. When the follow-up was written, that situation was open under OD-18 ⑲. ADR-0168 C19 and ADR-0170 R1 and R6 have since answered it (`build_time_limit`, a condition and no tool failure), and `hilclaw/standin_run.py` and its tests implement that order.

The planner chose the hold line's second option for the order: keep it and state the reason. Moving the waiter first would reopen ADR-0168 C19, ADR-0170 and landed code for a situation that now has a fitting answer.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5.
- `CLAUDE.md`, "세션 진입 점검".
- `ARCHITECTURE/decisions/ADR-0145-od14-first-case-container-measurement.md`: Status, F6 to F8 in Context, decisions 3, 5 and 6, and Consequences (runtime acceptance item (liii)).
- `ARCHITECTURE/decisions/ADR-0168-od18-standin-container-situations.md`: row C19 and decision 4 (lines 84 and 85).
- `ARCHITECTURE/decisions/ADR-0170-od18-standin-run-operation.md`: rows R1 and R6.
- `hilclaw/harness/timing_waiter.c`, header comment.
- `hilclaw/standin_run.py`, module docstring steps 4 and 5, and `_build`.
- `hilclaw/standin_answer.py`, `read_timing_process`.
- The `prlimit(2)`/`getrlimit(2)` man page, https://man7.org/linux/man-pages/man2/getrlimit.2.html, for the permission rule and the effect of each limit.

## Acceptance Criteria

All edits are to ADR-0145, in place. They are corrections to this record, not a new decision.

1. **New fact.** Add one fact to the documentation facts in Context (next free F number), quoted from the man page, with the reading date. It gives the rule under which a process may change another process's limits.
2. **Decision 5, the sentence on W5.** Replace "this record knows of no way for a kernel to make W5 fail" with what the reading supports:
   - The kernel's process, being of the same user as the waiter and able to act until W4, has a route to the waiter's resource limits through `prlimit(2)`, and `PR_SET_DUMPABLE` is not shown to close it. If the man page shows otherwise, say what it shows.
   - W3 to W5 allocate no memory (`timing_waiter.c`), so lowering `RLIMIT_AS` or `RLIMIT_STACK` is not expected to fail them. Name any other limit the reading shows may end or fail the waiter, such as a CPU limit. Mark each expectation as this record's reading, not observed.
3. **Decision 5, what follows.** State the bound on the harm, citing ADR-0168 decision 4: a stream with no waiter's line and a non-zero status is `exit_status`, so a kernel that uses this route breaks its own run and cannot turn it into a tool failure. If the reading shows a way to reach no waiter's line with status 0, which ADR-0168 leaves open, say so in the sentence and name it under `## Result`.
4. **Consequences, item (liii).** Add to it: whether a process inside can change the waiter's limits with `prlimit(2)`, and whether a call so changed ends in anything other than the answers of criterion 3.
5. **Decision 3, "The waiter's build".** Keep the order. In the sentences on the cost, add:
   - why the timing build comes first: a failed timing build answers without starting a second container, and its log is handed to the keeper first (ADR-0170 decision 3);
   - the answer in the case the cost names: `build_time_limit` by ADR-0168 C19 and ADR-0170 R1 and R6, a broken run and no tool failure;
   - the remaining cost: a kernel whose compile finished within B_t can still get `build_time_limit`, and nothing in the result says which build gave it (ADR-0170 "The cost").
   Verify each citation against the record. If `hilclaw/standin_run.py` differs from these rows, leave the sentence out, name the difference under `## Result` and return BLOCKED.
6. **Boundaries and Decision 6.** Where decision 6 or Boundaries still says the waiter's build past the limit is open under ⑲, and ADR-0168 has answered it, narrow that clause to what stays open and cite the row. Change nothing else there.
7. **Runtime acceptance item.** Nothing here is started or observed. Under `## Result`, write one runtime acceptance item for the driver to add to `PROCESS/RuntimeAcceptance.md` (D22): the check of criterion 4, source T-0526 and ADR-0145. Do not edit that file.
8. **No decision is made and no open question is closed** beyond what the landed records answer. Keep the status word of OD-14 and OD-13. `ARCHITECTURE/Requirements.md`, `OpenDecisionProposals.md` and `StandardScenarios.md` do not change, so no coverage recheck is due.
9. **Document mode.** Before editing, make the session-entry check of `CLAUDE.md`. Reviewer cycle, rebase on `origin/main`, push to main with the `Reviewed-by` trailer and `Task: T-0526`.

## Out of Scope

- Any code or test, including a change to `timing_waiter.c` or to the order in `standin_run.py`. If the reading shows the waiter should defend itself, name that as a follow-up.
- The answer to a stream with no waiter's line and status 0 (ADR-0168 decision 4 leaves it open).
- The "less exact" lists of other ADRs, the ADR-0164 citation and the other hold lines.
- T-0527 (ADR-0182 slice 3).

## Follow-ups

## Result

ADR-0145 corrected in place: new fact F10, decisions 3, 5 and 6, Consequences item (liii), Boundaries and References.

- Criterion 2: `prlimit(2)` is a route to the waiter's limits; `PR_SET_DUMPABLE` is not shown to close it. The man page's rule names no dumpable attribute. `RLIMIT_CPU` is the limit the reading shows may end the waiter (`SIGKILL` at the hard limit). All marked as this record's reading, not observed.
- Criterion 3: the reading shows no way through a limit to no waiter's line with status 0, so nothing is named here as a new case of the stream ADR-0168 decision 4 leaves open.
- Criterion 5: `hilclaw/standin_run.py` `_build` matches ADR-0168 C19 and ADR-0170 decision 3, R1 and R6.
- Follow-up named by the reading: none. The harm stays bounded, so the waiter need not defend itself on this ground.

**Runtime acceptance item** (for `PROCESS/RuntimeAcceptance.md`; source T-0526, ADR-0145 item (liii), D22): on each kind of machine of C-7 with Docker, whether a process inside a timing process container, of the waiter's user, can change the waiter's resource limits with `prlimit(2)`, and whether a call so changed, a lowered `RLIMIT_CPU` hard limit among them, ends in anything other than `exit_status` for a stream with no waiter's line and a non-zero status; in particular that it never gives a stream with no waiter's line and status 0.
