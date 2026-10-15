---
id: T-0191
title: Write the first record of the run tools' contract (`sim.run` / `board.run`, first case and mock) - what a call's operation does, the split between the tool function and the operation, the sample form taken from the run's objective, and the call that carries the memory figure and where it reads the `bound` (OD-13 sub-question 10, first two clauses) - and reflect it in the ARCHITECTURE documents; no code
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-10, FR-1, NFR-3, OD-18, OD-13, OD-1, "#5 D6"]
dependsOn: [T-0176]
touchesFiles: [ARCHITECTURE/decisions/, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]   # one new record under ARCHITECTURE/decisions/ with the next free number at execution time (ADR-0061 at planning time)
estimatedSize: {loc: 240, files: 4}   # one new record of about 170-200 lines; the rest are in-place edits of a few lines each
hq: []   # design-level under DRIVER §9 (OD-18 and OD-13 are not on the owner-only list); the owner's frame of OD-1 (HQ-0009) and the owner decisions of 2026-10-15 are cited, not re-decided
---
## Why
PLAN P1-1 (the FR-10 tool contracts, the mock backend, the conformance tests) is open. `blob.push` / `blob.fetch` are registered (ADR-0039), and `correctness.check` has a second record in eleven slices (ADR-0040 to ADR-0048, ADR-0056, ADR-0060). **`sim.run` and `board.run` have no contract at all.** ADR-0038 fixed only that `cpu_standin` offers both and that in the first case "the two carry out the same local run" (owner, HQ-0005); its decision 2 and Boundaries leave "what the local run is and what the call returns" to "the contract of the run tools".

What ADR-0016 Context listed as missing for these tools is now mostly on `main`: the sample form has the owner's OD-1 frame (HQ-0009: latency minimisation, the time of the kernel call, lower is better; the memory ceiling as a constraint type) and the `instance.json` member `objective` (ADR-0053); the dimensions (`op_signature`, ADR-0031), the repeat bound `n_max` (ADR-0023) and the attempt's kernel source (ADR-0055) are in run files; how a build at a call works and where its settings come from has an answer for `correctness.check` (ADR-0056, ADR-0060). On the harness side the ADR-0052 code slices (a) and (b) have landed: `hilclaw/local_run.py` hands on `ru_maxrss`, `hilclaw/harness/memory_ceiling.py` gives the figure and the three-way verdict. **Condition (c) of ADR-0052 decision 7 - the record and code that make the call carrying out a timing run at a point return the verdict, with a `bound` taken from the run's own record - is the only thing between the owner's constraint type and a usable spec.** OD-13 sub-question 10 asks exactly that: which call, from which record and how it reads the `bound`, and which result members carry figure and verdict.

**This task is the first record of the run tools' contract, the analogue of ADR-0021 for `correctness.check`**: the operation, the split, the sample form, and the first two clauses of sub-question 10. The call's identity (journaled or not, `step` values, request members), the result members (the third clause of sub-question 10) and the timing seed (OD-13 sub-question 7) are later slices. It ticks **no PLAN checkbox**; no tool can be registered from it.

Planner's judgements (from the files at `main` `7d203c6`, 2026-10-15; **the reviewer is asked to re-check each**):
- **Selectable without the repository owner (DRIVER §9).** ADR-0038 decision 7 and Boundaries, ADR-0052 decisions 6 and 7 and Boundaries (sub-question 10: "the contracts of the run tools ... close it"), ADR-0053 Boundaries ("which call reads that member ... the run tool's contract") and ADR-0056 Boundaries hand these points to the run tools' contract. OD-18 and OD-13 are design-level. The owner's words this record needs are already given: HQ-0005 (both tools, same local run), HQ-0009 (the OD-1 frame and the memory ceiling), the decisions of 2026-10-15 (issuecomment-6182984913: builds and runs in a container; timing on imprecise machines continues on relative numbers). Nothing of #5 A-4's remainder, B-1, B-2, B-3, OD-3, OD-25 or C-6 is needed.
- **Why this item now**: no lock, no TODO / INTERRUPTED task file, no open PR; the six open HQs (HQ-0013, HQ-0014, HQ-0016 to HQ-0019) are runtime-acceptance items and block no planning. The previous planner (T-0190 Follow-ups) named this item. P1-8's next step and P0.5-4 are not more ready than this. P2 items wait on P1-1.
- **Not in this slice, because each is tied to something open or would double the record**: the identity of a call (journaled, `step`, `execution`, request members) - the next slice, as ADR-0040 followed ADR-0021; the result members and any data-plane member (sub-question 10, third clause); the timing seed's source and recording (OD-13 sub-question 7); flag, compiler, time-limit values (OD-14, OD-18 sub-question 18); the container's design (OD-14 sub-question 1); detection and marking of imprecise timing (OD-13 sub-question 11); spend (OD-2, OD-19); the mock's operation and script; `profiler.collect`.

Known risk, accepted: ADR-0052, ADR-0053, ADR-0055 and ADR-0056 are inside their objection windows until 2026-10-20, ADR-0060 until 2026-10-22. Records were built inside such windows before. The Status section names the records the new one falls with.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, commit trailers) - mandatory for every task (§6)
- PROCESS/DRIVER.md §0, §1-5 (Bypass permissions; the forbidden actions; a denied or failed tool call is BLOCKED, never worked around), §3 "BLOCKED 사유" paragraph, §8, §9
- CLAUDE.md - whole file; in particular "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분" (no `claude`, no container, compiler or kernel is started), "브랜치·merge 절차" (document mode, the `Reviewed-by` trailer)
- **ARCHITECTURE/decisions/ADR-0021-od18-correctness-check-split.md - the whole record (163 lines)**: the form to follow (sections, the split of decision 2, the outcome classes of decision 5, the limits of decision 6)
- **ARCHITECTURE/decisions/ADR-0052-od13-memory-ceiling-measurement.md - the whole record**: decisions 2 to 7 (the figure, how it is obtained, the verdict, the execution points, what carries it, the admission condition (c)), Consequences "Code slices", Boundaries (sub-question 10)
- **ARCHITECTURE/decisions/ADR-0038-od18-cpu-standin-execution-points.md**: decision 2 (the owner's answer and the record's reading of "the same local run"), decision 7, the walk-through rows of `sim.run` / `board.run`, Consequences, Boundaries
- **ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md** (the timing run: driver program, Python side, the caller's parameters `n_min` / `cv_max` / the rule's direction / the seed, decision 8 completed vs broken, decision 9 what is not decided) and **ADR-0007** decisions 1 to 4 (measurement, repeat, sample, "not converged")
- **ARCHITECTURE/decisions/ADR-0053-od8-instance-record-objective.md** (the member `objective`; its Boundaries on which call reads it) and **ADR-0050** decisions 2 to 5 (the `task.objective` vocabulary; a not-judged ceiling is never met); ADR-0023 (`n_max`), ADR-0031 (`op_signature`), ADR-0041 decisions 1 to 3 (how `correctness.check` takes its dimensions - a pattern to cite or depart from, not to copy silently)
- **ARCHITECTURE/decisions/ADR-0056-od18-correctness-check-verification-executable.md** decisions 2, 3 and 5 and the weighing of choice (a) ("every check builds"), and **ADR-0060** decisions 3 to 5 and the quotations O1 to O4 (settings are the backend's own; the container of the owner's 2026-10-15 decision cited and not designed); ADR-0055 decisions 1 and 9 (the attempt's `output/`; who builds the kernel of an attempt)
- ARCHITECTURE/decisions/ADR-0016-od18-backend-frame.md decisions 2 and 3 (the moments of a call of a HW tool; offered / `not_offered`) and its Context bullet on `sim.run`, `board.run`, `profiler.collect`; ADR-0015 decisions 1, 2, 4, 5 (the frame; `invalid_request`; the reserved kinds); ADR-0019 (unusable run); ADR-0010 decision 7; ADR-0017 decisions 1 and 10 - read only
- ARCHITECTURE/Requirements.md: FR-1, FR-2, FR-10, NFR-3, C-4, C-7, and the register rows OD-1, OD-13, OD-14, OD-18 (lines 90, 102, 103, 107 at planning time; the rows are long - search them for `ADR-0052`, `ADR-0060`, `run 도구`)
- ARCHITECTURE/OpenDecisionProposals.md section `## OD-13` (line 207 on at planning time; the bullets on ADR-0052, sub-questions 7, 10 and 11, the owner decision of 2026-10-15 and the integrator note) and section `## OD-18` (line 281 on; the bullets on ADR-0038, ADR-0056, ADR-0060 and sub-questions 7, 10, 12, 17, 18)
- ARCHITECTURE/StandardScenarios.md - the checking rules (`## 검사 규칙`) and `# 검사 결과` (line 168 on at planning time); the steps that run or measure a candidate (S0, S1, S1-b, S2, S8; extension S9) and the steps that judge a constraint or a target
- Read only, to describe what exists and not to change: `hilclaw/harness/timing.py` (`driver_arguments`, `run_timing`, the result and the broken conditions), `hilclaw/harness/timing_build.py`, `hilclaw/harness/memory_ceiling.py` (`figure`, `verdict`, `Verdict`), `hilclaw/local_run.py` (the `max_rss` it hands on), `hilclaw/instance.py` (`objective_of`, `n_max` reader, `op_signature` reader), `hilclaw/backends.py` (`HW_TOOLS`, `select`), `hilclaw/hw_tool.py`, `hilclaw/check_operation.py` (how `correctness.check` hands its operation four things)
- PROCESS/tasks/T-0176-adr-od18-check-build-answers-and-settings-route.md `## Result`: the latest record of this line, its register edits, coverage re-check and owner notice
- Issue #5: every comment after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6184597227 (the ADR-0060 notice, the last comment at planning time; `gh issue view 5 --repo myungjoo/HIL-Claw --json comments`). If the repository owner has objected to ADR-0038, ADR-0052, ADR-0053, ADR-0056 or ADR-0060, or has written something that changes a sentence this record builds on, do not start: return BLOCKED ("requirement unclear") quoting the comment
- .claude/skills/dev-item-address/SKILL.md (document mode: steps 9 to 12 and 15) and .claude/skills/dev-code-review/SKILL.md (document-mode return path; the "no invented decisions" check)

## Acceptance Criteria
### The record (one new file `ARCHITECTURE/decisions/ADR-NNNN-od18-run-tools-split.md`, next free number at execution time)
- English; the sections of ADR-0021 (Status, Context, Decision with numbered points, Walk-through, Limits, Alternatives considered, Consequences, Boundaries, References). **Every sentence of the Decision says whose it is**: the owner's (quoted by link from HQ-0005, HQ-0009 or the decisions of 2026-10-15), a cited record's (record and decision named), or the record's own. No sentence of an earlier record is replaced; where one becomes less exact, list it under Consequences.
- Status: accepted under DRIVER §9 (D6) by reviewer approval, the UTC date, the 7-day objection window, the parts of OD-18 and of OD-13 (sub-question 10, first two clauses) it closes, the records it builds on and falls with, and the sentence that **it is not the whole contract and neither tool can be registered from it**.
- Scope: a call of `sim.run` or `board.run` about one attempt of a run whose hw_profile names `cpu_standin` (the first case: `gemm`, fp32, C kernel) or the mock (ADR-0038 decision 6). Say whether the record gives **one contract that both tools follow** (differing in the tool and its point only) or two, and why, against the owner's "nothing but the execution point distinguishes the two operations" and ADR-0038's reading that they stay two tools with two operations.
- The record decides, as its own design unless cited, **these points and no other**:
  1. **What the operation of a call does at `cpu_standin`**: exactly one timing run of ADR-0009 of the attempt's kernel at the call's point, the figure of ADR-0052 obtained from that run. **Who builds the timing executable and when**: weigh building at each call (the cut ADR-0056 chose for the verification executable, with its cost) against an executable built once per attempt and reused by both points (what would hold it, and ADR-0010 decision 7); take one. Whether the measurement policy of ADR-0007 applies at each point alike (ADR-0038 Boundaries asks this) - answer it for these runs.
  2. **The split between the tool function and the operation** (ADR-0016 decision 2; the pattern of ADR-0021 decision 2 and ADR-0056 decision 3): what the tool function reads from the run and hands over (the dimensions from `op_signature`, `n_max`, the sample form of point 3, and the seed as an input whose source is **not** decided here), what the operation returns (the intervals in order, the resolution, the stopping state, and the figure or its absence), and **where the verdict of ADR-0052 decision 5 is computed** (on the Python side outside the kernel's process, ADR-0052 - tool function or operation; take one with its reason). **The settings** (flags, compiler, time limits, environment): take the cut of ADR-0060 decision 3 (every setting is the backend's own; the tool function hands none over) for these tools, or say why not; no value is given.
  3. **The sample form from the run's objective**: the tool function reads the run's `objective` (ADR-0053) and derives the direction of the stopping rule (ADR-0009: interval or its reciprocal, the caller's parameter with no default) from the one objective the owner's frame allows - latency minimisation is "the time of the kernel call" (HQ-0009), so the rule is applied to the interval. Say what a call about a run whose `objective` states an objective the contract does not cover (throughput, which an instance cannot state yet), or states none, answers - a tool failure with a kind this record names, or an existing kind cited - and where in the order of a call that answer falls (before anything is started; before the start line if the tool turns out journaled).
  4. **The call that carries the memory figure** (sub-question 10, first clause): at an execution point of the first case, the call of the run tool of that point is the call whose timing run's figure is judged; each call judges its own run (ADR-0052 decision 6 - cited, not re-decided); `correctness.check` carries no figure (ADR-0017 decision 1: the verification run "is not the timing run").
  5. **Where and how the `bound` is read** (sub-question 10, second clause; ADR-0053 answered only the record's name): which of the two sides reads `objective` for a `memory_ceiling` constraint, in the same read as point 3 or not, at which moment of ADR-0016 decision 2; what a call answers when the run states no ceiling (the outcome must be distinct from *not judged* - ADR-0052 decision 5 - say how, without naming a member); what it answers when `instance.json` cannot be read (cite ADR-0019; no new kind for that).
  6. **Which outcomes are results and which are tool failures** (the pattern of ADR-0021 decision 5): what a result must let a caller tell apart - at least a completed measurement, converged or not converged (ADR-0007, ADR-0009 decision 8); a broken run; a build that did not end ok (weigh the owner's HQ-0020 answer for `correctness.check`, where such a build is a `broken` result, and say whether the run tools follow it, citing it as the owner's answer for that tool only); and, where a ceiling is stated, within / over / not judged. What a result must never contain (at least: anything the kernel wrote; anything a caller could use to pick the seed). **Name no member of a result.**
- **Limits** (a numbered list), at least: the owner's 2026-10-15 item 1 (builds and runs in a container) against ADR-0052 decision 3 (the figure is the `ru_maxrss` of the waited-for process) - under a container the process the Python side waits for may not be the kernel's; state that until OD-14 sub-question 1 designs the container this record is read against the host code, as ADR-0060 did, and register a sub-question if none holds this; the owner's 2026-10-15 item 3 (relative numbers and the warning on imprecise timing) is untouched and sub-question 11 of OD-13 stays open; a kernel can evade the figure (ADR-0052 limits, cited); the seed policy (OD-13 sub-question 7) is still open, so no code of the operation can be finished from this record alone.
- A **walk-through** of one attempt at `cpu_standin` under the record's answers: `sim.run` with a stated ceiling (within), `board.run` of the same attempt (its own build, run and verdict), a run with no ceiling stated, a run whose `objective` the contract does not cover, a broken run. No result member and no `step` value is shown.
- **Alternatives considered**: at least the other answer to "who builds" (point 1), the operation computing the verdict vs the tool function (point 2), a `bound` handed in a request (rejected by ADR-0052 decision 7 (c) - cite), and taking the sample form from a request member instead of the run's `objective`.
- **Consequences**: what the next slices must still add, item by item (the identity of a call; the result members - sub-question 10, third clause; the seed - OD-13 sub-question 7; the mock's operation and script; the settings' values; spend); **the code slices that can be cut now** and those that cannot yet; that condition (c) of ADR-0052 decision 7 is **still not met** after this record (no result member, no tool); the docstrings and earlier-record sentences that become less exact; the A-13 reading (document mode; no member of a data-plane file, no request or result member named; if a tool-failure kind is named, why that is not a "데이터 plane 스키마 변경").
- **Boundaries**, at least: every request and result member, the input schema, the description; whether the tools are journaled and their `step` values; the timing seed; the settings' values and the container's design; the mock's operation and script; `profiler.collect`; a target that lacks a point (OD-26); sub-question 12 of OD-18; what follows an *over* or a *not judged* in the round loop (FR-1, OD-10, OD-14, PLAN P2-1); detection and marking of imprecise timing (OD-13 sub-question 11); promotion and improvement (ADR-0007, OD-15, OD-29); budget and spend; hooks; the owner-only items (#5 A and B items, OD-3, OD-25, C-6).

### Edits of existing documents (same commit)
- `ARCHITECTURE/Requirements.md`: one clause each in the OD-18 and OD-13 rows in the manner of the earlier "확정분" / "반영" clauses (status words unchanged, no new OD number, 30 register rows before and after - count them at execution time and keep the count); FR-10, FR-1, NFR-3 rows are edited only if a sentence of theirs becomes false. Say in `## Result` which rows were judged and left.
- `ARCHITECTURE/OpenDecisionProposals.md`: in `## OD-18`, the heading note and one "채택분" bullet for the new record; in `## OD-13`, a dated note on sub-question 10 saying which clauses are answered and that the third clause and ADR-0052 decision 7 (c) remain; any sub-question the record registers (next free number in its section). No proposal text is deleted. Each Korean sentence must say exactly what the record says - no stronger and no weaker.
- `ARCHITECTURE/StandardScenarios.md`: the coverage re-check of CLAUDE.md, applied to every step that runs or measures a candidate and every step that judges a constraint; update the heading note of `# 검사 결과` and add one dated passage with the outcome. A verdict changes only if the rules of that file say so; do not edit a scenario step.
- No earlier ADR, UsageCases.md, README.md, PLAN.md or any file under `hilclaw/`, `tests/`, `.github/`, `.claude/`, `PROCESS/` is edited.

### Do not invent
- No result or request member, no `step` value, no decision on journaling, no input schema or description, no seed source or recording rule, no flag, compiler, time-limit or environment value, no container design, no detection rule for imprecise timing, no budget axis or amount, no rule on what the round loop does after *over* or *not judged*, no member of `instance.json`, `STATE.json`, `events.ndjson`, a spec or a result file, no new reserved `kind` of the frame (a tool-specific kind under point 3 is allowed only with its weighing).
- Cite a record only for what its sentence carries. Owner words are quoted verbatim with their link.
- If a point turns out to need the repository owner (for example point 6's build-failure answer cannot be taken without a fact only the owner can give, or the container makes point 1 impossible to answer against the host code), do not decide it: land nothing and return BLOCKED ("requirement unclear") with the exact question in the multiple-choice form of the earlier HQs.

### Document checks (document mode replaces tests; list each with its outcome in `## Result`)
- Every relative link of the new record and of the edited passages resolves; the ADR number is free on `origin/main` at the push.
- `git diff --stat origin/main` shows only files of `touchesFiles`; `git diff --check` is clean; the four files are `i/lf` in `git ls-files --eol`.
- Each sentence of the Decision is marked as the owner's, a cited record's or the record's own, and each citation was checked against its source. Each name the record fixes (a kind, if any) was searched for in `hilclaw/`, `tests/` and `ARCHITECTURE/` for a collision.
- The OD register row count is the same before and after; only the rows named above differ.
- The coverage re-check outcome (verdict changes, gaps) is stated.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0191'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0191 --state all`; then the session entry check of CLAUDE.md (`gh pr list --repo myungjoo/HIL-Claw --state open`, issues #4, #5, #7, #8). An open PR that edits the OD-13 or OD-18 row or a file of `touchesFiles` is BLOCKED ("open PR conflict").
- Nothing is built or run: no compiler, kernel, container or `claude` process (D16). Statements about code are read from source at the commit you start from, and named as observations.
- Document mode (CLAUDE.md A-13): branch `claude/T-0191-adr-od18-run-tools-split-and-memory-call`; the reviewer cycle of dev-item-address steps 10 to 12 with a fresh-context `dev-reviewer` each round (at most 7 rounds; past the cap without a final Approve, return BLOCKED; a result starting with `SECURITY` is BLOCKED; if no reviewer can be spawned, return BLOCKED - do not self-review). Ask the reviewer explicitly to (a) check every citation against its source sentence and every Korean mirror sentence against the record; (b) look for a sentence that decides something on the "Do not invent" list or under Boundaries; (c) check that the answers stay inside ADR-0009, ADR-0038, ADR-0052, ADR-0053, ADR-0056 and ADR-0060 and replace no sentence of them; (d) re-check the weighing of points 1, 2 and 6 and the container limit; (e) re-check the planner's judgements under "Why".
- Then rebase on `origin/main` and push to `main` without a PR. Commit message: English; subject starts with `T-0191:`; the body says what was decided, what is left to the next slices and that the record lies inside the objection windows named above; trailers in this order: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0191`, then any attribution trailer your session requires.
- **Owner notice (DRIVER §9)**: do not post it yourself unless the driver's spawn prompt tells you to. Put the ready-to-post English text in `## Result` in the form of the ADR-0060 notice (what the record holds, which parts are cited owner answers and which are the record's own design, the readings to check, what is left open, the A-13 reading, the objection window, the last line `— posted by driver`).
- Never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around. Delete the task branch only after the push to `main` is confirmed, remote and local in separate commands.
- `## Result`: fill it in after the push, on `main`, and leave that edit uncommitted for the driver (DRIVER §3-6). No fenced code block in it. Record: the commit, review rounds and findings, **the split as landed** (who builds, which side computes the verdict, where the objective and the `bound` are read, the kinds named - the next slice and the code are written against it), any sub-question registered, the document checks, the notice text, the follow-ups. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters (result, commit, BLOCKED or not).

## Out of Scope
- Any code: a tool function or operation of `sim.run` / `board.run`, a change of `hilclaw/harness/*`, `hilclaw/backends.py`, `hilclaw/mock_backend.py`, `hilclaw/spec.py` (check 4 of ADR-0050 stays closed), the registration of a tool, tests, a JSON Schema file.
- The identity of a call (journaled, `step`, `execution`, request members), the result members (OD-13 sub-question 10, third clause), the timing seed (OD-13 sub-question 7), the mock's operation and script, `profiler.collect`.
- The container's design (OD-14 sub-question 1), the settings' values (OD-18 sub-question 18), imprecise-timing detection and marking (OD-13 sub-question 11), OD-18 sub-question 12, OD-26.
- Editing PLAN P1-1, an earlier record, UsageCases.md, README.md or the `HIL-Claw-data` repository.

## Follow-ups
- (planner, after this record - document mode, P1-1) The second slice of the run tools' contract: the identity of a call (journaled or not, `step` values per tool, `execution`, the request members), in the manner of ADR-0040.
- (planner, later - document mode) The third slice: the result members carrying the samples, the stopping state, the figure and the verdict (OD-13 sub-question 10, third clause - may need a data-plane reading under A-13; judge it then), and the timing seed (OD-13 sub-question 7). After those and their code, check 4 of ADR-0050 in `hilclaw/spec.py` (ADR-0052 decision 7).
- (planner, later) OD-18 sub-question 18 (나) and (라) before the `cpu_standin` operation (T-0190 Follow-ups).

## Result

**DONE** (executor, 2026-10-15). Landed on `main` as `8f971f1` (document mode, one commit, fast-forward push; trailers `Reviewed-by: reviewer agent (7 rounds, Approve)`, `Task: T-0191`). Branch `claude/T-0191-adr-od18-run-tools-split-and-memory-call` deleted (remote, then local). Record: `ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md` (176 lines). Diff: 4 files, +185/-5.

Resume and entry checks: no commit with `Task: T-0191`, no PR, no open PR at all. On #5 there is no comment after `issuecomment-6184597227`, so no objection to ADR-0038, ADR-0052, ADR-0053, ADR-0056 or ADR-0060. #4, #7 and #8 have no new comment.

### Review rounds
- R1 Request changes. Major: the report parsing and the replay had been put on the operation's side, against the ADR-0021 decision 2 pattern, with a wrong reason. Minor: HQ-0020 point 1 was not weighed; the Requirements OD-18 clause left out O3 and O5. Nits: a failed build "not judged" was marked as cited; Boundaries needed a qualifier; one StandardScenarios sentence was too strong; L2 needed the (마) reading stated.
- R2 Request changes. Major: Boundaries listed "the seed's choice" as kept out of a request, which no decision says. Nits: punctuation in L2; the `memory_ceiling` docstring attribution; the Korean "not covered" list was narrower than the record.
- R3 Approve with Nits: the † marker; ADR-0009 decision 8 added to the less-exact list; "ADR-0052 decisions 3 and 4"; where `n_min` and `cv_max` come from; the Korean list of what the operation is handed.
- R4 Approve with Nits: "Limit 7" instead of "L7"; "OD-18 sub-question ⑲"; Korean wording for an unusable file; "결과·결과 파일".
- R5 Request changes. Minor: the Requirements mirror let "builds at each call" read as applying to the mock as well; the same scope Nit in StandardScenarios.
- R6 Approve with one Nit: the "builds on ADR-0038" decision list.
- R7 Approve. Two Nits are left as they are, because fixing them would need an eighth round (see Follow-ups).

### The split as landed (the next slice and the code are written against it)
- Scope: one contract for both tools. The two tools stay two tools with two operations and differ only in name and execution point. Covered runs: `cpu_standin` in the local configuration, and a run at the mock. Applying the contract to the mock is the record's own choice, made for the reason the owner gave in HQ-0005 point 4.
- Who builds, and when: the operation of the called tool, at each call. It builds from the compiled set the ADR-0055 reader finds at the output path, into a build directory of its own that it removes (the ADR-0056 decision 4 way).
  - Rejected: built once per attempt (no holder, path or tie to the source; state between calls); a cache (its key cannot be stated).
  - Cost: four builds per attempt that reaches the board point, and the file timed at one point is not the file timed at the other.
  - ADR-0007 applies at both points with the values of `cpu_standin`, and the two measurements are never pooled.
- What the tool function reads, all in the one read of `instance.json` in moment ④:
  - the dimensions, from the `shape` of the op_signature (the ADR-0041 decision 2 source);
  - `n_max` (ADR-0023);
  - `objective` (ADR-0053).
  - From these it derives the sample form and the `bound`, and forms the output path.
- What the operation is handed: the request, the hw_profile, the dimensions, `n_max`, the sample form, a seed and the output path.
  - The seed's source and recording stay with OD-13 sub-question ⑦.
  - `n_min` and `cv_max` come from `measurement.py`.
  - The operation is never handed the `bound` or the `objective`.
- What the operation returns, exactly one of:
  - (A) the raw report, together with the figure (converted to bytes on the operation side, because its unit depends on the platform) or that there is none;
  - (B) no report, and the first failed condition, in this order: build time limit, compiler exit status, run time limit, exit status or signal (the order of ADR-0060 decision 4).
- Which side computes what: the tool function does all of the judging of the run (report form, an interval of 0, the replay) and computes the memory verdict. A figure is used only for a run the tool function finds completed. Observation: `run_timing` does both halves today and is to be split, as `run_verification` was.
- Settings (flags, compiler, both time limits, environment): the backend's own, by the cut of ADR-0060 decision 3. The tool function hands none, and no value is given.
- Sample form: one objective `latency_minimisation` gives `interval`.
- The kinds named: `objective_not_stated` (a valid file without the member) and `objective_not_covered` (a type, count, weight or priority, or a constraint type, that this contract does not cover; impossible today). Both are:
  - kinds of this contract, not reserved (provisional);
  - answered in ④ after `no_backend` and `not_offered`, before the start line, and never as an end-line `failure`.
- The memory figure: the run tool of a point is the call whose figure is judged; each call judges its own run, and `correctness.check` carries no figure. The `bound` comes from `objective.constraints` in the same read (not a request, a spec, a kept value or a default).
  - An empty `constraints` means no ceiling is stated. The result must tell that apart from *not judged*.
  - An unreadable file gets the four kinds of ADR-0019.
- Results: completed (converged or not converged) and broken. Broken is one class with the first failed condition.
  - A failed timing build is a result (owner, HQ-0020 point 3). Putting it in the broken class, with the build conditions first, is the record's reading of points 3 and 1 together. No member is taken over.
  - The order of the conditions after the build: run time limit, exit status, report form, zero interval, replay (the `run_timing` order, taken as the record's own).
  - Where a ceiling is stated: within, over or not judged. A broken run, and by the record's reading a failed build, is not judged.
- Never in a result: standard error, the command line, input values, and the seed until OD-13 sub-question ⑦ is answered. The compiler log is not returned.
- Tool failures: every situation in which no timing executable can be had or started, other than a failed build (S1-S6, S9 and S10, read for the timing build). Their kinds are ⑲ (나).
- Container limit: under a container, the waited-for process may not be the kernel's. The record is read against the host code. The question is held by OD-14 sub-question ① (마), read as including where and how the figure is obtained, so no new sub-question was registered for it.
- ADR-0052 decision 7 (c) is still not met. `memory_ceiling` stays not admitted.

### Sub-question registered
OD-18 ⑲, for `sim.run` and `board.run`:
- (가) the answer for a run that states no op_signature, an uncovered op_signature or no `n_max`, and its kinds (own, `correctness.check`'s, or reserved per ADR-0041 decision 4), with their place in ④;
- (나) the kinds of the no-executable situations;
- (다) the log of a timing build;
- (라) the source and values of the timing build and run settings, and whether they equal those of the verification build.

### Register and coverage
- OD register: 30 rows before and after. Only OD-13 and OD-18 changed, and their status words are unchanged (`확정 (P1 최소분…)` and `제안됨`).
  - OD-13 row: ADR-0061 added to 반영, and the ⑩ remainder item updated (the call and the place of the `bound` are answered; the result and result-file members remain).
  - OD-18 row: one clause for ADR-0061, and ⑲ added to the 잔여 list.
- Rows judged and left: FR-10, FR-1, NFR-3, OD-1, OD-14 and OD-16. No sentence of theirs became false.
- OpenDecisionProposals: an OD-18 heading-note clause, the ADR-0061 채택분 bullet, the ⑲ bullet, and a dated 2026-10-15 note on OD-13 ⑩. No proposal text was deleted.
- StandardScenarios: the heading note of `# 검사 결과` and the passage "2026-10-15 (4차)". Steps re-checked:
  - run and measure steps: S0-5/6/10, S1-3/4/6, S1-b-2/4, S2-2, S3-4, S6-3, S11-3, S8-2/3/4;
  - instance-start steps: S1-2, S2-1, S3-3, S6-1.
  - Outcome: no verdict change and no gap. S2's throughput target goes to OD-1 and to the record that admits the type.

### Document checks
- Relative links of the record and of the edited passages resolve. ADR-0061 and OD-18 ⑲ were free at the push.
- `git diff --stat b3aa12f origin/main` lists the four files of `touchesFiles` only. `git diff --check` is clean, and all four files are `i/lf`.
- Every Decision sentence is marked as the owner's, cited, or the record's own. Owner quotations O1 to O5 were checked word for word against comments 6117798837, 6136238336, 6164154089, 6183004538 and 6182984913; the reviewer re-checked them in every round. About 60 record citations were checked in place, decision numbers included.
- `objective_not_stated` and `objective_not_covered` collide with nothing in `hilclaw/`, `tests/` or `ARCHITECTURE/`.
- Nothing was built or run, and no compiler, kernel, container or `claude` process was started (D16).

### Owner notice (posted by the driver as https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6186830791)
### OD-18 / OD-13 - the first part of the sim.run / board.run contract fixed by ADR-0061 under DRIVER §9 (T-0191)

ADR-0061 (commit 8f971f1) is the first record of the run tools' contract, for cpu_standin in the local configuration and for a run at the mock. It answers the first two clauses of OD-13 sub-question ⑩.
- Both tools follow one contract. At cpu_standin each call builds the timing executable itself, from the attempt's output/, and carries out one ADR-0009 timing run. ADR-0007 applies at both points.
- The operation returns the raw report with the ADR-0052 figure, or the first failed condition (build time limit, build exit status, run time limit, exit status). The tool function judges the run (form, replay) and computes the memory verdict.
- The tool function reads the dimensions, n_max and objective in one read of instance.json. latency_minimisation gives the sample form interval. A run that states no objective, or one this contract does not cover, is a tool failure of objective_not_stated / objective_not_covered, answered before anything starts.
- The run tool of a point is the call whose memory figure is judged, with the bound read from objective.constraints of the run. "No ceiling stated" is an outcome distinct from not judged.

Yours, quoted and not re-decided: both tools carry out the same local run (HQ-0005); latency minimisation and the memory ceiling (HQ-0009); "yes, as the principle that such a build is a result" for the timing build (HQ-0020 point 3); builds and runs in a container (2026-10-15). Everything else is the record's own.

Readings to check, most contestable first:
1. Each call builds its own timing executable, so the file timed at the sim point is not the one timed at the board point (four builds per attempt that reaches the board point).
2. A failed timing build is put into the broken class with the build conditions first, reading your HQ-0020 point 1 (given for correctness.check) together with point 3. No member is taken over.
3. Under a container, the process whose usage is read may not be the kernel's. The record reads OD-14 sub-question ① (마) as holding this, and is read against the host code until the container is designed.

Open: call identity, request and result members (the third clause of ⑩, so ADR-0052 decision 7 (c) is still not met and memory_ceiling stays not admitted), the timing seed (OD-13 ⑦), the mock, setting values, and the new OD-18 sub-question ⑲.

A-13: document mode. No request, result or data-plane member is named. The two error.kind values are answered before the start line and never reach events.ndjson. Register: OD-18 stays 제안됨 and OD-13 keeps its status. The objection window ends 2026-10-22.

— posted by driver

### Follow-ups
- (planner, document mode, small) The two R7 Nits, not applied because the review cap was reached: in decision 5 of ADR-0061, "At an execution point of the first case" should also cover a run at the mock; the OD-13 ⑩ note in OpenDecisionProposals should add "전의 호출에서 남긴 값" to the list of non-sources.
- (planner, code mode) Two code slices from ADR-0061 Consequences. (1) A function that classifies an `objective_of` value (not stated / not covered / covered) and gives the sample form and the `bound`. (2) The judging half of a timing run, split out of `run_timing`: it takes the report or the condition, with the sample form and `n_max`. D12 tests.
- (planner, document mode, P1-1) The second slice of the run tools' contract: the call identity (journaled or not, `step` values per tool, `execution`, request members), in the manner of ADR-0040. Then OD-18 ⑲ (가)/(나), the result members (the third clause of OD-13 ⑩), and the timing seed (OD-13 ⑦).
