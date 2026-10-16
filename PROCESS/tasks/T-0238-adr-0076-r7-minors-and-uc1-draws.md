---
id: T-0238
title: Correct ADR-0076 after acceptance - the round-7 minors (b)-(d) of T-0236 (objective coverage at the start registered under OD-8 sub-question 34 (ga), the order of the n_max fill-in in decision 3, the O3 quote) - and the UC-1 note on `draws` (e), with the register lines they touch and the coverage re-check
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [OD-8, FR-2, FR-9, "#5 D6"]
dependsOn: [T-0236, T-0237]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0076-od8-instance-start-required-members.md   # existing; no new ADR
  - ARCHITECTURE/OpenDecisionProposals.md   # OD-8 section only: sub-question 34 status line and, if needed, the ADR-0076 adopted line
  - ARCHITECTURE/UsageCases.md              # UC-1 only, guarded (criterion 3)
  - ARCHITECTURE/StandardScenarios.md       # the "최근 재검사" line only (coverage re-check)
  - ARCHITECTURE/Requirements.md            # OD-8 row's 잔여 only, and only if criterion 2 finds it needed
estimatedSize: {loc: 20, files: 5}
hq: []
---
## Why

T-0236 landed ADR-0076 (`be43ff0`, document mode) after 7 review rounds, the last allowed. Round 7 approved with non-blocking findings that were left unapplied, because a change after the last round would have landed unreviewed text. They are listed in `PROCESS/tasks/T-0236-adr-od8-instance-start-required-members.md`, `## Result`, the "Follow-ups" bullet, items (b) to (e):

- (b) R7 minor: register, in the rest of OD-8 sub-question ㉞ (가), whether the start checks that the **stated** objective is covered (ADR-0061 decision 4), and adjust ADR-0076's Boundaries to point at that registration.
- (c) R7 minor: decision 3 should say that filling in `n_max` happens only for a valid, in-scope content.
- (d) R7 nit: the O3 quote in Context should keep "Until the rule that combines more than one objective … is decided under A-4", and the reading of "exactly one" as also excluding none should be marked as ADR-0053's (ADR-0053 decision 5 says that reading is its own).
- (e) UC-1 step 1 does not list `draws` among the inputs of the start (UsageCases was not edited).

Item (a) of that list was the code slice and landed as T-0237 (`722ec95`, `hilclaw/instance_start.py`). T-0237's `## Result` ("Order reading") records the order the code implements: type checks, then `instance.validate`, then the scope, then the `n_max` fill-in, then the required set; an invalid or out-of-scope document gets nothing filled in. Minor (c) brings decision 3 in line with that order. T-0237's Follow-ups bullet (b) asks that the record says this task implements (c).

This is a correction of an accepted record during its objection window (notice https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6218483981, window until 2026-10-23). It changes no decision's outcome, no OD status and no data-plane schema, and ticks **no PLAN checkbox** (P1-8 continues). Earlier corrections of the same kind, each with an "Edited after acceptance" Status bullet: T-0234 (ADR-0075), T-0235 (ADR-0072, ADR-0071), T-0230 (ADR-0073).

**Why this item now.** No lock, no TODO or INTERRUPTED task, no open PR (checked 2026-10-17 at `8fb882a`). T-0210 (HQ-0021), T-0225 (HQ-0022), T-0231 (HQ-0023) and T-0233 (HQ-0024) are BLOCKED, and the code slices that rest on them wait. The other follow-up of T-0237, binding `accelerators`/`covers` in a component that performs the start, needs that component, which is OD-23 (`논의중`), so it is not planned.

**Unlanded branches.** `claude/T-0210-*` and `claude/T-0231-*` edit `ARCHITECTURE/OpenDecisionProposals.md` far from the OD-8 section (around lines 315-330 and 402-415 of their bases), one line of `ARCHITECTURE/Requirements.md` that is not the OD-8 row, and the "최근 재검사" line of `ARCHITECTURE/StandardScenarios.md`. T-0236 edited the same three files after those tasks were blocked, so this task does too; those branches rebase when their HQs are answered. Do not read those branches for content, depend on them or reconcile with them.

**Planner's reading** (line numbers of `main` at `8fb882a`; the executor and the reviewer re-check each one; the text wins):

- ADR-0076 (109 lines): line 18 is Context's list of sources; its O3 quote is "an instance states exactly one objective" (nit d). Line 37 is the `objective` row of the decision 2 table ("**owner** O1, O3 (cited above)"). Line 45 is decision 2's `n_max` bullet ("when the content composed from the start's inputs states no bound, the start puts that default into the content it then validates and writes"). Line 52 is decision 3's "Order of the checks at the start" (minor c). Line 100 is the Boundaries bullet whose last item is "whether the start checks that the stated objective is covered (ADR-0061 decision 4)" (minor b). Line 11 is the last Status bullet.
- ADR-0053 line 19 is O3 in full; line 75 (decision 5) says "that reading of O3 is this record's".
- ADR-0061 decision 4 (from line 60): line 64 defines "Covered" for a present `objective`; `objective_not_covered` is the per-call kind for an uncovered one.
- OpenDecisionProposals: line 8 is the "기록 규칙"; line 114 is the ADR-0076 adopted line; line 138 is sub-question ㉞, ending "→ (가) 부분 답: [ADR-0076](…)(…). 남음: (가)의 무엇이·어느 입력에서·메뉴, 그 밖의 instance; (나)·(다)."
- Requirements: line 84 is the register's "행 형식"; line 99 is the OD-8 row. Its `**잔여**:` already has "instance의 시작이 그 밖에 무엇을 확인하는지(…)" and "하위 질문 ①~㉞ 가운데 미결분".
- UsageCases: UC-1 is from line 69; step 1 is line 73, the 비고 line 77 (it already says the user gives the tolerance as an instance parameter, FR-9).
- ADR-0046: decision 2 (b) (i) (line 47, "Whoever starts the instance states the number, once for the run"); decision 3 (from line 63) keeps "from what it takes the number" undecided. OpenDecisionProposals line 136 is sub-question ㉜.
- StandardScenarios: line 170 is the first paragraph of §검사 결과 (the "기록 규약"); line 172 is the "최근 재검사" line.

## Required Reading

ARCHITECTURE lines are very long: read them with `sed -n '<line>p' <file> | fold -w 400`, not whole files at once. Line numbers are those of `main` at `8fb882a`; the text wins.

- **PROCESS/DRIVER.md §3-5** (executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (task format, naming, size cap D4, trailers). Also §2 (document mode), §8 (comment format) and §9.
- `CLAUDE.md`, whole. Above all: "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검", "개발 드라이버와 런타임의 구분" (D16) and "브랜치·merge 절차" (document mode, `Reviewed-by` trailer).
- `.claude/skills/dev-item-address/SKILL.md` (document mode: steps 9 to 12 and 15) and `.claude/skills/dev-code-review/SKILL.md` (document-mode path).
- `PROCESS/tasks/T-0236-adr-od8-instance-start-required-members.md`, `## Result` (the findings are given there) and `PROCESS/tasks/T-0237-instance-start-required-set-check.md`, `## Result` ("Order reading" and Follow-ups (b)).
- `ARCHITECTURE/decisions/ADR-0076-od8-instance-start-required-members.md`, whole.
- `ARCHITECTURE/decisions/ADR-0053-od8-instance-record-objective.md`: lines 16-19 (O1 to O3) and decision 5 (from line 69, above all line 75). Read only.
- `ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md`: decision 4 (lines 60-69) and Boundaries (from line 157). Read only.
- `ARCHITECTURE/decisions/ADR-0046-od18-correctness-check-draws.md`: decisions 2 and 3 (lines 35-96). Read only.
- `ARCHITECTURE/decisions/ADR-0075-od30-injection-at-instance-start.md` line 10, an "Edited after acceptance" Status bullet. Read only, as one form of such a bullet; do not copy its wording.
- `ARCHITECTURE/OpenDecisionProposals.md`: line 8 ("기록 규칙"), the OD-8 section around lines 100-150 (above all lines 114, 136 and 138).
- `ARCHITECTURE/Requirements.md`: line 84 ("행 형식") and line 99 (OD-8 row).
- `ARCHITECTURE/UsageCases.md`: UC-1 (lines 69-78).
- `ARCHITECTURE/StandardScenarios.md`: the rules section (around line 26), §검사 결과 (from line 168), and scenarios S0, S1, S2 and S8.
- `hilclaw/instance_start.py`: read only, to confirm the order T-0237 implements.

## Acceptance Criteria

1. **ADR-0076. Make only these edits:**
   - **Minor (c)**: decision 3's "Order of the checks at the start" (line 52) states the order that keeps the outcome of the current text for every content and that `hilclaw/instance_start.py` implements: validity first, then the scope of decision 1, then the `n_max` fill-in, then the required set; an invalid or out-of-scope content gets nothing filled in. Adjust decision 2's `n_max` bullet (line 45) only if its "then validates" wording contradicts that order. Do not change what is written, refused or reported, and do not move the "never replaced" rule (line 47). If the executor finds that some content would be written or refused differently under the new order than under the old, leave (c) unapplied and argue so in `## Result` (criterion 4).
   - **Minor (b)**: the Boundaries item "whether the start checks that the stated objective is covered (ADR-0061 decision 4)" (line 100) is kept as open, and points at where criterion 2 registers it (sub-question ㉞ (가)). Do not decide it.
   - **Nit (d)**: Context's O3 quote (line 18) keeps the owner's condition "Until the rule that combines more than one objective (priority order, weighted sum, Pareto) is decided under A-4" word for word from ADR-0053 line 19, and says that reading "exactly one" as also excluding none is ADR-0053's reading (decision 5), not the owner's. If the `objective` row of the table (line 37) rests on that reading, it says so in a few words, citing ADR-0053 decision 5.
   - **One new last Status bullet**, after line 11. It says the record was edited after acceptance on the execution date by task T-0238 (document mode). It names the edits briefly, says that decision 3 now states the order T-0237 implements, says that no decision's outcome changed, and says that the objection window of https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6218483981 (until 2026-10-23) is unchanged. Write it in this record's own words.
   - Nothing else of ADR-0076 changes: decisions 1, 4 and 5, the required set and its table rows other than an edit (d) needs, Walk-through, Alternatives, Consequences (including the "less exact" list) and the other Boundaries items. References change only for a source an edit newly cites.
2. **OpenDecisionProposals, OD-8 section only (minor b).** Follow the "기록 규칙" in line 8 of that file. Register "whether the start checks that a stated objective is covered (ADR-0061 decision 4)" as open under ㉞ (가) by rewriting the status at the end of ㉞ (line 138) in place: its "남음:" part names it. Leave the question's wording as it is unless the open part cannot be named without a wording change; if so, change only what is needed and say why in `## Result`. Do not add a dated note and do not restate ADR-0076 or ADR-0061. Change the ADR-0076 adopted line (line 114) only if it becomes untrue. **Requirements**: change the OD-8 row's `**잔여**:` only if the row as it stands does not cover the newly registered open part; if you change it, rewrite it in place by the register's "행 형식" (line 84), without restating any ADR and without a dated chain. Otherwise leave `ARCHITECTURE/Requirements.md` unchanged and say so in `## Result`.
3. **UC-1 (item e), guarded.** `draws` is a member an instance of ADR-0076 decision 1 must state (ADR-0046 decision 2 (b) (i)), but from what the start takes the number is undecided (ADR-0046 decision 3; OD-8 ㉜). Do **not** add `draws` to step 1 as a user input: that would decide its source. If UC-1 can say, in one short sentence of its 비고 (line 77, beside the tolerance sentence), that the instance also states the number of correctness-check draws and that its source is open (ADR-0046, OD-8 ㉜), add that sentence with those links. If the executor finds that any wording would decide the source, or that UC-1 needs no change, leave `ARCHITECTURE/UsageCases.md` unchanged and argue so in `## Result`. Change nothing else of UsageCases.
4. **Guarded exit**: if a finding turns out wrong on the cited texts, leave that part unchanged and give the argument in `## Result`. If a fix would change what ADR-0076 decides, leave it unapplied and record it as a follow-up. Do not invent a rule, a default, a source of a value or an OD. If every part is left unchanged, finish DONE with no landing commit and no Status bullet.
5. **Coverage re-check** (CLAUDE.md "문서 커버리지 재검사"): if `ARCHITECTURE/Requirements.md` or `ARCHITECTURE/UsageCases.md` changed, re-check the scenarios the edit touches (at least S0, S1, S2 and S8) by the rules of StandardScenarios, and record the result by the first paragraph of StandardScenarios §검사 결과 (line 170): rewrite the "최근 재검사" line (line 172) in place; add a "판정 변화 이력" item only if a verdict changed or a gap was found or closed. If neither register file changed, `ARCHITECTURE/StandardScenarios.md` stays unchanged; say so in `## Result`.
6. **No other file changes.** This includes every other ADR, `README.md`, `PROCESS/` (except this task file's `## Result`, which the executor writes as DRIVER §3-5 says), `CLAUDE.md`, `.claude/`, `hilclaw/`, tests and CI.
7. **Document checks**: every relative link in edited lines resolves; `git diff --check` is clean; line endings are LF; `git diff --stat origin/main` lists only files in `touchesFiles`.
8. **`## Result`** records the landed commit, the review rounds and their findings, the exact new wording of each edit, each part left unchanged and why, the coverage re-check outcome, and the remaining follow-ups (the OD-23 binding of `accelerators`/`covers` from T-0237 at least).

### Process

- Work only in the driver's dedicated clone. First do the §3-5 landed check: `git log origin/main --grep='^Task: T-0238'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0238 --state all`. Then do the CLAUDE.md session entry check: `gh pr list --repo myungjoo/HIL-Claw --state open` and issues #4, #5, #7, #8. An open PR that edits a file in `touchesFiles` makes the task BLOCKED ("open PR conflict"). None was open at planning time.
- Read the comments on issue #5 after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6218483981 (the ADR-0076 notice). Skip the driver's own comments (last line `— posted by driver`). An owner objection to ADR-0076 makes the task BLOCKED ("requirement unclear"); quote the objection. An answer to an open HQ (HQ-0013, HQ-0014, HQ-0016 to HQ-0019, HQ-0021 to HQ-0024) does not stop this task; name it in `## Result`.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Nothing is built or run except read-only git/gh commands, grep and link checks. Tell each reviewer to write no file and start no `claude` process.
- **Document mode** (CLAUDE.md A-13): branch `claude/T-0238-adr-0076-r7-minors-and-uc1-draws` from `origin/main`; **no PR**. After the reviewer cycle (at most 7 rounds) approves, rebase on `origin/main` and push to `main` directly, with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0238` trailers. Delete the task branch afterwards.
- No §9 owner notice is due: no decision changes and no OD status changes.

## Out of Scope

- Deciding whether the start checks that a stated objective is covered, or what it does then (ADR-0061 decision 4 stays the per-call rule).
- Deciding from what the start takes `draws` or any other value (ADR-0046 decision 3, OD-23, OD-9).
- Binding `accelerators`/`covers` to a component that performs the start, and any edit of `hilclaw/` or tests (OD-23; T-0237 follow-up (a)).
- The OpenDecisionProposals and register edits of the BLOCKED T-0210 and T-0231, the OD-29 promotion-timing row, and nit (e) of T-0232 (OpenDecisionProposals adopted line of ADR-0075).
- Editing any other accepted ADR, including the sentences ADR-0076 lists as "less exact".

## Follow-ups

- (code, OD-23) Bind `accelerators=(standin_profile.ACCELERATOR, mock_backend.NAME)` and `covers=gemm_contract.covers` in whatever component performs the start, with the two binding tests and the `standin_profile` docstring named in T-0237's `## Result`; waits on OD-23.

## Result
