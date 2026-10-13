---
id: T-0117
title: Write the ADR that states what `task.objective` holds for the first case (`cpu_standin`, `gemm`, fp32, C kernel) - as the repository owner answers the HQ of this task (the target of the first instance) - and reflect it in the ARCHITECTURE documents; no code
phase: P1
status: TODO
commitMode: doc
coversReq: [FR-2, FR-5, OD-1, OD-6, "#5 A-4", "#5 B-4", "#5 D6"]
dependsOn: [T-0017, T-0018]
touchesFiles: [ARCHITECTURE/decisions/, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]   # one new record under ARCHITECTURE/decisions/ with the next free number at execution time (ADR-0038 at planning time; the BLOCKED T-0088 and T-0116 also take "the next free number at execution time")
estimatedSize: {loc: 180, files: 4}   # one new record of about 100-140 lines; the rest are in-place edits of a few lines each
hq: [HQ-0009]   # not to be executed before the repository owner has answered
---
## Why
PLAN P1-5 ("GEMM spec 예시 ... 와 `spec.json` 스키마") is open. Its validator is on `main` (`hilclaw/spec.py`, T-0018), and the records that give the committed example its values were closed one by one: ADR-0008 (the op side), ADR-0027 (the form of a `run_id`), ADR-0035 / ADR-0036 (the hw side). What the example still lacks is `task.objective` and a technique of the stand-in catalog (ADR-0008 Consequences, line 155; T-0108 `## Result`). **This task is `task.objective`.** It ticks **no PLAN checkbox**: the example itself is a later code or document slice, and the technique is still open.

What the fixed inputs carry:
- FR-2: the target is not fixed by the system; the user states it per loop instance, from a menu of target types.
- ADR-0002 decision 2 (line 61): `task.objective` is required, "any JSON value", "the target of the instance (FR-2), copied from the instance record. Not validated in version 1"; its example writes `NOT-DECIDED-HERE` there.
- ADR-0007 decision 1 (line 23): the measurement policy "chooses neither the quantity nor its direction (OD-1)".

What they do not carry: **which target the first instance states.** #5 A-4 (the first menu of target types, OD-1) is an unticked item of the issue body with a proposal and no answer.

**Why it cannot start without the repository owner** (planner, 2026-10-10 UTC, from the files at `main` `4dc51cc`):
- Accepted records file exactly this point as owner-only: ADR-0002 Boundaries (line 163: "the target vocabulary (#5 A-4, OD-1) - `task.objective` reserves the place only"), ADR-0008 Boundaries (line 164: "`task.objective` (OD-1, #5 A-4)"), ADR-0007 Boundaries (line 152: the target quantity, its unit and direction, the order "better than"), ADR-0020 and ADR-0034 Boundaries (the objective among what waits for the repository owner).
- DRIVER §9 puts #5 A and B items on the owner-only list; the register row OD-1 is "차단됨" on #5 A-4. The planner may not close it by a record of its own and does not choose a target (CLAUDE.md "미결은 발명하지 않는다"; BLOCKED reason "owner-only decision").
- Every task since T-0082 lists "PLAN P1-5: `task.objective` (#5 A-4)" under "(driver / owner)"; the narrowed question for the first case was never put. HQ-0004 is the precedent (the oracle and the tolerance of #5 A-7 / B-7, asked for the first case only).
- **A second owner point found at planning**: ADR-0002 decision on versions (line 100) says the spec's `schema_version` "is raised ... when `profile` or `task.objective` get defined members". Raising it is a change of the spec schema of the data plane, an owner-intervention reason of CLAUDE.md A-13. Whether the first case's value can be carried in version 1 or the version goes up is therefore asked in the same HQ (part 4), so that the task does not block a second time after the answer.

Once the target is given, the rest - how the value is spelt inside `task.objective` - is the design of a record inside ADR-0002, design-level under DRIVER §9 (OD-6 is not on the owner-only list). That part is this task's record.

## HQ question
(for the driver to record under DRIVER §8; reason `owner-only-decision`)

PLAN P1-5 (the committed GEMM spec example) lacks `task.objective`, the target of the instance (FR-2), which ADR-0002 and ADR-0008 file as owner-only under #5 A-4 / OD-1. For the first case only (`cpu_standin`, `gemm`, fp32, C kernel): (1) Which target does the run state: (a) latency minimisation - the time of the kernel call as the harness timing run measures it, lower is better; (b) throughput maximisation (name the quantity and its unit); (c) something else (name it)? (2) Is there a constraint beside it: (a) none; (b) a memory ceiling (say how it is stated); (c) another (name it)? (3) Scope of your answer: (a) the first case only, #5 A-4 stays open; (b) you also confirm the proposal of #5 A-4 (a single objective plus an optional memory ceiling; weighted combinations and Pareto later) as the MVP menu - then list its types? (4) ADR-0002 raises the spec's `schema_version` when `task.objective` gets defined members, and a change of the spec schema needs you (CLAUDE.md A-13): (a) version 1 stays - the record says what value the first case carries, `task.objective` remains "any JSON value" and `hilclaw/spec.py` checks nothing in it; (b) you approve version 2 of the spec, with the members of `task.objective` defined by the record and checked by the validator? Not asked here: how the value is spelt in `spec.json` and which member of `instance.json` it is copied from (the design of a record, under review), the improvement threshold (OD-13), the baseline (OD-28), promotion (OD-15, OD-29), any target value at which a run stops, and a technique of the stand-in catalog.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, commit trailers) - mandatory for every task (§6)
- PROCESS/DRIVER.md §0, §1-5 (Bypass permissions; the forbidden actions; a denied or failed tool call is BLOCKED, never worked around), §3 "BLOCKED 사유" paragraph, §8, §9
- **The repository owner's answer to the HQ of this task** in `PROCESS/STATE.json` (`humanQuestions`, the entry whose `taskId` is `T-0117`: `decision`) and the comment it links on issue #5. **If that entry has no `decision`, do not start: return BLOCKED.**
- CLAUDE.md - whole file; in particular "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "브랜치·merge 절차" (document mode, the `Reviewed-by` trailer; the BLOCKED reason "데이터 plane 스키마 변경")
- Issue #5: the body item A-4, the comments "B-4" (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285) and "A-7" (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944117402), and every comment newer than the HQ mirror of this task
- ARCHITECTURE/Requirements.md: FR-2, FR-5, and the register rows OD-1 and OD-6; ARCHITECTURE/OpenDecisionProposals.md sections OD-1 and OD-6
- ARCHITECTURE/decisions/ADR-0002-od6-codegen-spec.md - decision 2 (the row of `task.objective`), the decision on `schema_version` (lines 98-101), the example and its source table (lines 105-131), Boundaries
- ARCHITECTURE/decisions/ADR-0007-od13-measurement-policy.md - decisions 1, 2 and 5 (what a sample is, the summary) and Boundaries; ADR-0009 (the `cpu_standin` timing run) - what it measures and in which unit
- ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md - Consequences and Boundaries
- ARCHITECTURE/decisions/ADR-0037-od6-gemm-contract-zero-dimension.md and PROCESS/tasks/T-0112-adr-od6-gemm-contract-zero-dimension.md (`## Acceptance Criteria` "Process" part and `## Result`) - the form of a record, of the register edits, of the coverage re-check and of the owner notice as the latest §9 record landed them
- Read only, to describe what exists and not to change: `hilclaw/spec.py` (what it checks of `task`), `hilclaw/gemm_contract.py`, `hilclaw/harness/` (the timing side)
- ARCHITECTURE/StandardScenarios.md - the checking rules and the steps that name a target or an objective (S0, S1, S2)
- .claude/skills/dev-item-address/SKILL.md (document mode: steps 9 to 12 and 15) and .claude/skills/dev-code-review/SKILL.md (document-mode return path; the "no invented decisions" check)

## Acceptance Criteria
### By the answer
- Answer (1)(a), or (1)(b) with the quantity and unit named; (2)(a); (3)(a) or (3)(b); (4)(a) or (4)(b): write the record described below.
- Answer (1)(c), (2)(b), (2)(c), an answer that fits none of the options, or one that needs a quantity the harness on `main` does not measure, a new external dependency or a new member of another data-plane file: do not write the record. Return BLOCKED ("task needs re-planning") quoting the answer; the planner rewrites this file.
- No answer to part (4), or an answer that leaves it to the record: do not choose. Return BLOCKED ("data-plane schema change") with part (4) as the question.

### The record (one new file `ARCHITECTURE/decisions/ADR-NNNN-od6-first-case-task-objective.md`, next free number at execution time)
- English; the sections of ADR-0037 (Status, Context, Decision, Walk-through or Example, Alternatives considered, Consequences, Boundaries, References). **Every sentence says whose it is**: the owner's (cite the answer to this HQ by link), a cited record's, or the record's own. The target, its direction and any unit are quoted from the answer and are **not** widened, narrowed or interpreted beyond its words.
- Status: accepted under DRIVER §9 (D6) by reviewer approval, the UTC date, the objection window of 7 days, and which earlier records it builds on and falls with (ADR-0002 at least).
- The record decides, as its own design inside ADR-0002 and for the first case only:
  1. The JSON value of `task.objective` for the first case: its type and spelling (and, under (4)(b), its members), stated as provisional where the answer does not give them.
  2. How that value relates to what the timing run of ADR-0007 / ADR-0009 yields - only as far as the answer says; if the answer names the quantity "as the timing run measures it", cite the decision of ADR-0009 that defines it and add nothing.
  3. Under (4)(a): that the spec stays at version 1, that `hilclaw/spec.py` still inspects nothing in `task.objective`, and why the value is not a "defined member" in the sense of ADR-0002 line 100 (if the executor or a reviewer finds that it is one, stop: BLOCKED, "requirement unclear"). Under (4)(b): what version 2 defines, what a reader of version 1 does (or that this is OD-11 and open), and the code slice it implies.
  4. Under (3)(b): the menu as the owner listed it, quoted, with nothing defined for any type beyond the first case.
- The example of ADR-0002 (lines 105-131) rewritten for this one value, in a `json` or plain-text fence, never as Python; every other `NOT-DECIDED-HERE` that later records closed may be cited, not re-decided. Say plainly what the example still lacks (the technique).
- Boundaries, at least: every other target type and multi-objective handling (rest of #5 A-4 / OD-1 unless (3)(b)); the order "better than" and the improvement threshold (OD-13); the baseline (OD-28); promotion (OD-15, OD-29); a stop value and budgets (OD-2, OD-19); the member of `instance.json` the value is copied from (PLAN P1-8, a later record); the technique and the stand-in catalog (OD-22); other backends, kinds and dtypes.
- A "Consequences" line that cuts the next slices for the planner (the `instance.json` member; under (4)(b) the validator change; the committed example of PLAN P1-5 once the technique is settled), without writing any code.

### Edits of existing documents (same commit)
- `ARCHITECTURE/Requirements.md`: one clause in the OD-6 row in the manner of the earlier "확정분" clauses, and one clause in the OD-1 row quoting the owner's answer with its link. The status word of OD-1 changes only under (3)(b) and only as far as the answer says; otherwise it stays, and the item is named in `## Result` for the integrator. FR-2 is not reworded.
- `ARCHITECTURE/OpenDecisionProposals.md`: one "채택분" bullet under OD-6 and one dated note under OD-1, a few lines each.
- `ARCHITECTURE/StandardScenarios.md`: the coverage re-check of CLAUDE.md for the steps that name a target; update the result section with the date and the outcome. A verdict changes only if the rules of that file say so; do not edit a scenario step.
- ADR-0002, ADR-0007 and ADR-0008 are not edited; sentences of theirs that become less exact are listed in the record and in `## Result`.

### Do not invent
- No target type, direction, unit, constraint or menu entry beyond the answer's words. No order "better than", no threshold, no stop value, no baseline. No member of `instance.json`, `STATE.json`, an event or a result file. No technique. No change of the spec's `schema_version` without answer (4)(b).
- If, while writing, a point turns out to need the repository owner beyond the answer, do not decide it: land nothing and return BLOCKED ("requirement unclear") with the exact question.

### Document checks (document mode replaces tests; list each with its outcome in `## Result`)
- Every relative link of the new record and of the edited passages resolves; the ADR number is free on `origin/main` at the push.
- `git diff --stat origin/main` shows only files of `touchesFiles`; no file under `hilclaw/`, `tests/`, `.github/`, `.claude/` or `PROCESS/` is in the commit.
- Each sentence of the Decision section is marked as the owner's, a cited record's or the record's own, and each citation was checked against its source.
- The coverage re-check outcome (verdict changes, gaps) is stated.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0117'`; then the session entry check of CLAUDE.md (`gh pr list --repo myungjoo/HIL-Claw --state open`, issues #4, #5, #7, #8). An open PR that edits the OD-1 or OD-6 row or a file of `touchesFiles` is BLOCKED ("open PR conflict").
- Document mode (CLAUDE.md A-13): branch `claude/T-0117-adr-first-case-task-objective`; the reviewer cycle of dev-item-address steps 10 to 12 with a fresh-context `dev-reviewer` each round (at most 7 rounds; past the cap without a final Approve, return BLOCKED; a result starting with `SECURITY` is BLOCKED; if no reviewer can be spawned, return BLOCKED - do not self-review). Ask the reviewer explicitly to (a) compare the target the record states with the owner's answer word for word; (b) look for a sentence that decides something on the "Do not invent" list; (c) re-check point 3 against ADR-0002 line 100 and CLAUDE.md A-13; (d) re-check each provisional choice.
- Then rebase on `origin/main` and push to `main` without a PR. Commit message: English; subject starts with `T-0117:`; trailers in this order: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0117`, then any attribution trailer your session requires.
- **Owner notice (DRIVER §9)**: do not post it yourself unless the driver's spawn prompt tells you to. Put the ready-to-post English text in `## Result` in the form of the ADR-0037 notice (what is the owner's answer, what is the record's own design, the provisional choices, the objection window).
- Never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around. Delete the task branch only after the push to `main` is confirmed, remote and local in separate commands.
- `## Result`: fill it in after the push, on `main`, and leave that edit uncommitted for the driver (DRIVER §3-6). No fenced code block in it. Record: the owner answer followed (with its link), the commit, review rounds and findings, the value as landed, the provisional choices, the document checks, the notice text, the follow-ups. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters (result, commit, BLOCKED or not).

## Out of Scope
- Any code: `hilclaw/spec.py`, `hilclaw/instance.py`, `hilclaw/gemm_contract.py`, tests, a JSON Schema file, a committed example file.
- The member of `instance.json` that states the target; the comparison of two measurements; the technique of the example; OD-13, OD-15, OD-28, OD-29, OD-2, OD-19, OD-22.
- Anything HQ-0005 to HQ-0008 ask.
- Editing FR-2, the #5 body (ticking A-4), PLAN P1-5, earlier records, or the `HIL-Claw-data` repository.

## Follow-ups
- (planner, after this record - document mode, P1-8) The record of the `instance.json` member that states the target, then its code slice in `hilclaw/instance.py`.
- (planner, under answer (4)(b) - code mode, P1-5) Version 2 of the spec in `hilclaw/spec.py` with its tests.
- (planner, P1-5) The committed GEMM spec example: still needs a technique of the stand-in catalog, or a judgement under DRIVER §9 on whether the first example may carry an empty `guidance.techniques` (ADR-0002 allows the empty array).
- (integrator / repository owner) The checkbox of #5 A-4 and the status of OD-1 against the answer.
- (driver / owner) HQ-0005 (T-0088) and HQ-0008 (T-0116): the rest of PLAN P1-1. HQ-0006 (T-0106). HQ-0007 (T-0107) and the hook registration of PLAN P0.5-4.
- (planner - not before 2026-10-16, code mode, no change of behaviour) One shared once-only write helper for the three writers (`key_records`, `instance_file`, `spec_file`) (T-0094 `## Result`).

## Result
