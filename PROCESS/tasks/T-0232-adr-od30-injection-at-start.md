---
id: T-0232
title: Write the ADR that settles the OD-30 part "hypotheses injected at instance start" - the form and place of what is injected (FR-15), and the admission of origin `injected` with the member that points to it (ADR-0059 decision 3) - and reflect it in the ARCHITECTURE registers by their recording rules; no gate or mid-run injection, no distribution rule, no code
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-15, FR-17, FR-11, FR-14, S11, OD-30, OD-8, "#5 D6"]
dependsOn: [T-0218, T-0226, T-0230]
touchesFiles: [ARCHITECTURE/decisions/, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]   # one new record under ARCHITECTURE/decisions/: ADR-0075 at planning time (ADR-0068 is held by the BLOCKED T-0210 branch, ADR-0074 by the BLOCKED T-0231 branch - never take either); the next free number above both at execution time
estimatedSize: {loc: 240, files: 4}   # one new record of about 170-210 lines; the register edits are a few in-place lines each
hq: []
---
## Why

The owner's decision of 2026-10-13 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6136462569, point 4) puts **injection at instance start in the MVP**: "A hypothesis can be injected from outside … injection at instance start is in the MVP. An injected hypothesis goes through the same experiment, verification and verdict as the runtime's own." FR-15 and FR-17 ④ carry it, and S11 steps 1-2 say "형식·기록 자리 = OD-30". [ADR-0059](../../ARCHITECTURE/decisions/ADR-0059-od30-round-hypothesis-record.md) decision 3 defines `origin` `injected` and does **not** admit it: "the form and place of what is injected is not decided (Boundaries). The record that decides that form admits `injected` with the member that points to the injected input." Its Consequences add: "The owner puts injection at instance start in the MVP, so the record that admits `injected` is needed before the MVP is complete." PLAN P2-6 ("가설 레코드와 판정 … 스키마·파일 자리는 **OD-30 종결 필요(§9 ADR 경로)**") is still open and this is its remaining record-level part. **This task writes the record that settles injection at instance start**. It ticks **no PLAN checkbox**: the code slice (the validator of the injected input and the admission in `hilclaw/hypotheses.py`) is a later code task.

**Why this item now.** There is no lock, no TODO or INTERRUPTED task and no open PR (checked 2026-10-16 at `297617d`). T-0210 (HQ-0021), T-0225 (HQ-0022) and T-0231 (HQ-0023) are BLOCKED. The P2-8 metric tool waits on T-0231's ADR, which is not landed. P1-1's run tools wait on T-0210's ADR. P1-8 and P2-1 to P2-4 need roster or hook decisions (OD-23, OD-16, OD-18) that are not landed. This record rests only on landed records: ADR-0004, ADR-0018, ADR-0025, ADR-0059, ADR-0071, ADR-0072 and ADR-0073. The objection windows of ADR-0071, ADR-0072 and ADR-0073 run until 2026-10-23. This record builds on them as ADR-0073 built on ADR-0072 inside its window, and an objection would revert it with them.

**Overlap with the unlanded T-0231 branch (`claude/T-0231-adr-od30-s6-metric`, ADR-0074).** That branch edits the same three register places: the OD-30 row, the OD-30 section of OpenDecisionProposals, and the "최근 재검사" line of StandardScenarios. This task neither depends on it nor reads it. Edit `origin/main` as it stands. Whichever of the two lands second resolves the textual conflict when it rebases. Do not take ADR-0074.

**Planner's judgements (the reviewer is asked to re-check each):**
- **Authority (DRIVER §9).** OD-30 is design-level and not owner-only. The owner fixed the direction (injection at start is in the MVP; injected hypotheses get the same verification; injection never replaces the runtime's own hypothesis forming), and the OD-30 section of OpenDecisionProposals names only ② (gate) and ③ (during a run), and whether they are in the MVP, as owner questions ("②·③을 MVP에 넣을지는 범위 결정이므로 … 드라이버 ADR로 닫지 않고 오너에게 확인한다(HQ)"). ① at start is therefore within §9.
- **Not decided here** (name each in Boundaries): injection at a gate or during a run, and their MVP inclusion (owner, HQ; write the question text under `## Follow-ups` so the driver can raise it, and do not raise it yourself); the **order and share** of injected and system hypotheses across rounds and candidates (FR-17's addendum is a requirement, not a rule of distribution); **who derives a hypothesis from material** (orchestrator versus the UC-5 curator flow; OD-12 for the coder's own search); the catalog boundary of a supported injected hypothesis (UC-5, OD-24); what writes `instance.json` or any new file (OD-8 sub-question ⑰, OD-23); MVP scope (C-6), OD-25, OD-3.
- **What is injected.** FR-15 counts two inputs as injection: a hypothesis the user wrote, and material (for example a paper link) from which a hypothesis is to be derived. The record must decide the form of the **written hypothesis** at start. For **material**, it may decide how a pointer to it is stated at start (FR-14 ② "식별자+버전(또는 해시)") only if that is possible without deciding who derives the hypothesis or when. Otherwise, name it in Boundaries with the reason. The record must also say what an injected written hypothesis holds, weighed against ADR-0059 decision 3's members (`statement`, `basis`, `expected`): whether the user states all of them, some of them, or only a statement that the selection completes, and how FR-17's "same experiment, verification and verdict" is kept either way.
- **Place (weigh at least two).** (a) An optional top-level member of `instance.json`. ADR-0018 decision 2 leaves the top level open in version 1, and its "What raises the version" bullet gives the rule for an optional member. The file is written once (ADR-0004, ADR-0025), which matches "at start". (b) A new run-level file next to `instance.json`. ADR-0004 decision 1 says "Directly under `runs/<run_id>/` are the four run-level files and `rounds/`". A fifth file is a change to the layout, so the record must say whether it raises the layout version of ADR-0024. (c) Another place, if one is better. State the costs of each option: a misspelt optional member goes undetected (ADR-0018 decision 2, "The cost"); every HW tool call reads `instance.json`; NFR-7 ② applies; and so does the A-13 reading. **Guarded exit**: if the chosen option changes a defined member, raises a version, or makes a member required, stop. Return BLOCKED (`data-plane-schema-change`) with the question for an HQ, before landing anything. Adding an optional member at an open top level, or a file in a place ADR-0004 left open, is the route ADR-0059 and ADR-0073 took, and that route needs no BLOCKED stop.
- **The pointer from `hypotheses.json` (ADR-0059 decision 3).** Decide the member that an `origin: "injected"` entry uses to point to its injected input, and how an injected input is identified (an id unique within the run, its index, or another form). State the rules of that pointer:
  - the rules inside the file, which a validator of `hypotheses.json` alone can check;
  - the rules across files, against the injected input. Model these on ADR-0073 decisions 2-3 and the `hilclaw/hypotheses_cases.py` split.
  Say whether the admission raises the `schema_version` of `hypotheses.json`. ADR-0073 admitted `case` and the optional `cases_read` without a raise, and ADR-0059 decision 2 provides for admitting a defined value. Then say what reaches the case file through ADR-0072 decision 3, which copies `hypotheses.json` whole.
- **FR-11 identification.** FR-11 requires the decision log to identify "주입된 가설(FR-15)". Say how the pointer satisfies that. Say whether a round that leaves an injected hypothesis untested records anything. Weigh "nothing; the run-level input is the record" against a member, and do not invent a distribution rule while doing so.
- **Round 0.** ADR-0059 decision 5 adopts round 0 without a hypothesis record. Say whether an injected hypothesis can be tested in round 0 (it cannot, if round 0 holds no record) and cite the rule.
- **D16.** The record is written from documents and source alone. Nothing is built or run; no `claude`, board or API key is needed.

## Required Reading

Line numbers are those of `main` at `297617d`; the text wins. ARCHITECTURE lines are long: read them with `sed -n '<line>p' | fold -w 200` or by character range, never whole files at once. Read Korean files and Python with `PYTHONIOENCODING=utf-8` (the console code page is cp949).

- **PROCESS/DRIVER.md §3-5** (the executor procedure, landed check, resume rule and time limit) and **§5** (task format, naming, size cap D4, trailers); §8 (comment format and the `— posted by driver` footer); **§9 whole**.
- CLAUDE.md, the whole file. Above all: "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분" (D16), and "브랜치·merge 절차" (document mode, `Reviewed-by`, the A-13 BLOCKED reasons).
- .claude/skills/dev-item-address/SKILL.md (document mode: steps 9-12 and 15); .claude/skills/dev-code-review/SKILL.md (document-mode path; the "no invented decisions" check).
- PROCESS/PLAN.md lines 41-43 (P2-6, P2-7).
- ARCHITECTURE/Requirements.md: **line 84 ("행 형식", the recording rule your row edit follows)**; FR-11 (29), FR-12 (30), FR-14 (32), **FR-15 (33)**, **FR-17 (35)**, FR-18 (36), NFR-7 (the row naming ① and ②); register rows OD-8 (99), OD-12 (103), OD-23 (114), OD-24 (115), **OD-30 (121)**.
- **ARCHITECTURE/OpenDecisionProposals.md line 8 (the header's "기록 규칙")** and the **OD-30 section (lines 397-417)**: the four 채택분 lines, "제안으로 남는 부분", and the bullets "가설 주입의 시점과 형식", "주입 가설과 시스템이 세운 가설의 배분", "자료에서 가설을 도출하는 주체" and "주입 가설과 카탈로그의 경계".
- ARCHITECTURE/UsageCases.md lines 29, 73, 77, 85, 124 (UC-1 inputs, the injection note, the gate's "방향 수정", UC-5).
- ARCHITECTURE/StandardScenarios.md: 검사 규칙 (lines 13-29); S0 step 3 (line 36); **S11 (lines 122-130)**; **§검사 결과 (from line 168; line 170 is its recording rule, line 172 the "최근 재검사" line, line 195 the S11 row)**.
- **ARCHITECTURE/decisions/ADR-0059-od30-round-hypothesis-record.md, whole (162 lines)**: decision 2 (the open top level and the admission of defined values), **decision 3 (`origin`, lines 51-75)**, decision 5 (round 0), Alternatives row 3, Consequences, Boundaries ("Injected hypotheses", lines 140-155).
- **ARCHITECTURE/decisions/ADR-0073-od30-case-lookup-and-case-basis.md, whole (132 lines)**: the model of form for an admission plus an optional member, its A-13 reading (line 107) and its Boundaries.
- ARCHITECTURE/decisions/ADR-0018-od8-instance-record-hw-profile.md: **decision 2 (lines 28-41; open top level, "What raises the version", "The cost")**.
- ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md: the tree (from line 20), the path table (lines 66-69), decision 1 (line 82), decision 9 (line 134).
- ARCHITECTURE/decisions/ADR-0025-od8-instance-file-write.md: Context (lines 14-19) and decision 2.
- ARCHITECTURE/decisions/ADR-0024-od8-instance-record-layout-version.md: what the layout version is, and when it rises.
- ARCHITECTURE/decisions/ADR-0072-od30-hypothesis-outcome-case-file.md decision 3 (the whole copy of `hypotheses.json`); ADR-0071 decision 6 (round 0).
- ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md "Record format" (from line 146).
- Code, read as observations only (this record binds no code): `hilclaw/hypotheses.py` (line 26 refuses `injected`), `hilclaw/hypotheses_cases.py`, `hilclaw/instance.py` (`validate`, `_checked`).
- `PROCESS/tasks/T-0226-adr-od30-case-lookup.md` `## Result`: the review findings of the previous OD-30 admission. Do **not** copy its register-edit wording; follow the recording rules named below.

## Acceptance Criteria

### The record (one new ADR, English, under `ARCHITECTURE/decisions/`)

**Number.** Take the next free number above ADR-0074, checked on `origin/main` and on every remote branch at execution time (`git ls-remote --heads origin`). At planning time this is ADR-0075. **Never ADR-0068 or ADR-0074**: the unlanded branches `claude/T-0210-od18-run-tools-operation-tool-failure` and `claude/T-0231-adr-od30-s6-metric` hold them. Confirm the number before the push. If it is taken, use the next free one and update every reference.

**Form.** Use the sections of ADR-0001 "Record format", in that order. The record is accepted under DRIVER §9 (owner notice, 7-day window). The Status says it answers **one more part of OD-30**: injection at instance start, and the admission of `injected`. It also says OD-30 stays `제안됨`. Quote the owner only where an owner sentence exists (the 2026-10-13 decision and its addendum, FR-15, FR-17), and link it. Mark everything else as this record's own design ("cited" versus "own", as ADR-0059 and ADR-0073 do). Keep the record to about 210 lines or fewer.

It decides the following points, and weighs each against at least one alternative:

1. **What is injected at start, and its form.** The written hypothesis: its members, and how they relate to ADR-0059 decision 3. Material: a pointer form, or a Boundaries entry with the reason (see `## Why`).
2. **Where it is recorded.** The chosen option among (a)/(b)/(c), with the version consequences for `instance.json` (ADR-0018 decision 2) and for the layout (ADR-0024). Also say who writes it, by reference only: what writes `instance.json` stays OD-8 ⑰ and OD-23.
3. **The admission of `origin` `injected`** in `hypotheses.json`. Give the pointer member, its in-file rules, and its cross-file rules against the injected input. Say whether the version is raised, and what reaches the case file (ADR-0072 decision 3).
4. **FR-11 identification**, and what (if anything) records an injected hypothesis that is never tested. Do not set a distribution rule.
5. **Round 0** and injected hypotheses.
6. **An example** on synthetic values. Show the injected input and a round-1 `hypotheses.json` with one `injected` and one `system` entry. Any JSON shown must parse and must be valid by the rules stated. Any `run_id` follows ADR-0027.
7. **Guarded exit.** Name in Boundaries any point that would need an owner-only item, a change to a defined member or version, a new external dependency, or inventing what OD-8, OD-12, OD-23 or OD-24 leave open. If the record cannot stand without such a point, return BLOCKED (`owner-only-decision`, `data-plane-schema-change` or `requirement-unclear`) before landing anything, with the question written for an HQ.

**Boundaries must name at least**:
- injection at a gate and during a run, and their MVP inclusion (owner);
- the order and share of injected versus system hypotheses;
- who derives a hypothesis from material, and the coder's own search (OD-12);
- the catalog boundary (UC-5, OD-24);
- what writes the injected input, and when (OD-8 ⑰, OD-23);
- material that is unavailable (FR-14 ③);
- the selection rule for many cases and the S6 metric (other OD-30 parts);
- code, tests and prompts.

**Consequences** must give:
- the code slice it makes possible: the validator of the injected input, the admission in `hilclaw/hypotheses.py`, and a cross-file check. Leave the names to that task.
- the A-13 reading: what is added, what is unchanged, and what is reached indirectly, as ADR-0073 line 107 does.
- a name check of every new member, value or file name. Grep `hilclaw/`, `tests/` and `ARCHITECTURE/` on the day, and report any equalities and whether they are on purpose.
- the sentences of accepted records that become less exact. List them (ADR-0059 decision 3's "defined and not admitted" for `injected`, its Consequences "Until `injected` … are admitted", its Boundaries "Injected hypotheses", ADR-0073 Boundaries "Injection in any form", and any others found), and do not edit them.

### Register edits (in place, in Korean as the documents are). Follow the recording rules, not earlier task files

- **`ARCHITECTURE/Requirements.md` OD-30 row (line 121)**, by the "행 형식" of line 84:
  - Add **one** ADR link with a subject of a few words to `**확정분**:`.
  - Rewrite `**잔여**:` in place, so that "주입 경로·배분" names only what is left.
  - The status stays `제안됨`. Do not restate the record and add no dated chain.
  - Edit the parentheses in FR-15 and FR-17 ("주입 형식과 기록 자리 = OD-30", "값의 어휘 = OD-30") or any other sentence only if it becomes false. If it is only less exact, report it under Follow-ups.
  - The register keeps 30 rows.
- **`ARCHITECTURE/OpenDecisionProposals.md` OD-30 section**, by the header's "기록 규칙" (line 8):
  - Add one `- **채택분** [ADR-NNNN](…) — 다룬 것 (답함: …)` line after the ADR-0073 one.
  - In "제안으로 남는 부분", rewrite the injection entries in place.
  - In the bullet "가설 주입의 시점과 형식", change its head status word, and give it a `→ 부분 답: [ADR]…. 남음: …` ending that keeps ② and ③ open.
  - Keep the questions' wording, and add no dated notes.
- **`ARCHITECTURE/StandardScenarios.md`**:
  - In S11 steps 1-2, rewrite only the parenthetical notes that become false: "형식·기록 자리 = OD-30" in step 1. Point to the ADR with a link and do not restate it.
  - Re-run the coverage check by its rules (lines 13-29). The scenario touched is S11; also check S0 (step 3) and S5.
  - Then, by line 170, update the "최근 재검사" line (date, trigger, outcome) and the S11 row note (line 195), so that it names only what is still open.
  - Add a "판정 변화 이력" entry only if a verdict or gap changes.
- **No other file**: not README, UsageCases (report any sentence of it that becomes false under Follow-ups), PLAN, DRIVER.md, CLAUDE.md, any accepted ADR, any code, test, schema or `.claude/` file, and nothing in `HIL-Claw-data`.

### Document checks (report in `## Result`)

- Every link in the new record and in every edited line resolves.
- `git diff --check` is clean.
- All changed files are LF.
- Only the files in `touchesFiles` changed.
- Every JSON block in the record parses.
- The ADR number is free on `origin/main` and on every remote branch at push time.

### Process

- Run the session-entry check of CLAUDE.md before editing: `gh pr list`, and issues #4, #5, #7 and #8. Read the #5 comments after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6210927027. If the owner objected to ADR-0059, 0071, 0072 or 0073, or answered anything about injection, stop and return BLOCKED (`requirement-unclear`) with the reason.
- Use document mode: follow dev-item-address steps 9-12 with fresh context-isolated `dev-reviewer` rounds, up to 7. Then rebase on `origin/main`, and push directly to `main` with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0232`.
- After landing, post the DRIVER §9 owner notice on #5. Use the §8 comment format with the footer `— posted by driver`, and give the link and the end of the window. Record the comment URL in `## Result`.
- D16: start no `claude` process, and build or run nothing.

## Out of Scope

- Injection at a gate or during a run, and whether either is in the MVP. These are for the owner: write the question under Follow-ups.
- The order and share of injected versus system hypotheses, and who derives a hypothesis from material.
- Any other OD-30 part: the verdict comparison base, failed-attempt records, promotion, the selection rule for many cases, and the S6 metric (T-0231, HQ-0023).
- Edits to accepted ADRs, including ADR-0059's now less exact sentences: list them only.
- `hilclaw/`, tests, 1층 prompts and agent definitions.
- PLAN checkboxes: P2-6 stays open.

## Follow-ups

## Result
