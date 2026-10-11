---
id: T-0122
title: Bring the OD-4 and OD-13 rows of the Open Decisions register back under the one-line rule - move the per-record summaries of their last cells to the OD-4 and OD-13 sections of OpenDecisionProposals.md without changing a sentence, and leave each row with its status, the links to the records, what it already says is still open and a pointer
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [NFR-2, OD-4, OD-13, "CLAUDE.md OD register rule"]
dependsOn: [T-0118]
touchesFiles: [ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 40, files: 3}   # two lines of Requirements.md replaced; about 10-20 added lines in OpenDecisionProposals.md (long lines, moved text only); a few lines of the coverage result
hq: []   # no owner-only decision and no OD closure: no sentence about a decision is written, changed or dropped; text is moved between two files that a stated rule assigns it to
---
## Why
Three places state one rule for the Open Decisions register:
- CLAUDE.md, "미결은 발명하지 않는다": "OD 등록부에는 한 줄 요약만 두고 제안 본문은 OpenDecisionProposals.md에 쓴다."
- `ARCHITECTURE/Requirements.md`, the paragraph "**제안 상세**" above the register: "본 표에는 **한 줄 요약**만 적어 표가 읽히도록 유지한다. 제안 본문의 정본은 Proposals 문서, 상태·논의 위치의 정본은 본 표다."
- `ARCHITECTURE/OpenDecisionProposals.md` line 3: "등록부에는 한 줄 요약만 남겨 표가 읽히도록 유지한다."

T-0118 (landed `bba80b0`, 1 review round, Approve) applied the rule to the OD-8 row by moving the text of its last cell, unchanged, to the OD-8 section of the proposals document. Its `## Follow-ups` left "a judgement on the rows of 1,100 to 1,800 characters (OD-4, OD-16, OD-13, OD-6, OD-17)" to a later planner. Measured at `main` `31da22a` (characters as `awk` counts them; verify):

| Row (line of Requirements.md) | Whole row | Status cell | Last cell |
|---|---|---|---|
| OD-18 (105) | 10,885 | 11 | 10,616 |
| OD-8 (95), after T-0118 | 3,831 | 2,112 | 1,551 |
| OD-16 (103) | 2,766 | 11 | 2,607 |
| **OD-4 (91)** | 2,712 | 217 | 2,259 |
| **OD-13 (100)** | 2,463 | 181 | 2,089 |
| OD-6 (93) | 1,869 | 128 | 1,546 |
| OD-17 (104) | 1,788 | 11 | 1,593 |
| the other 22 rows | 190 to 976 | | |

The rows OD-4 and OD-13 grew since T-0118 measured them (ADR-0035, ADR-0036 and the T-0118 reviewer's figures are older). Each holds, in one table cell, a condensed summary of every record closed under it. The longer form of each summary already stands in the proposals document: the OD-4 section (lines 32 to 44) has one "채택분(ADR-NNNN ...)" bullet for ADR-0001, ADR-0035 and ADR-0036 and a note on ADR-0008; the OD-13 section (lines 188 to 199) has one for ADR-0007 and ADR-0009 and the "하위 질문" bullets.

**This task moves those summaries, unchanged, to the two sections and leaves each row with what the register is the source for**: the status (untouched), where each confirmed part is reflected (links to the records), where the discussion is, the one sentence the row already has on what is still proposed, and a pointer. Nothing is summarised anew, merged or deleted. It ticks **no PLAN checkbox**; it is upkeep of a document against its own rule, in the manner of T-0118.

### The cells as they are (copy from the file, not from here)
OD-4, last cell, four parts in this order:
- A: from "**정확 식별층**: 두 키의 필드," to "잔여(제안 유지): 유사도 벡터층·최근접 매칭(prior로만), S10 확장 고려." - the one-line summary of the item, "반영: [ADR-0001](...)." and the residual sentence. **Stays.**
- B: from "첫 인스턴스 = `cpu_standin` × Llama 3.2 1B GEMM/SDPA(#5 B-4) —" to "SDPA의 shape 멤버(ADR-0001 Boundaries)." - the clauses on ADR-0008, ADR-0035 and ADR-0036 and the list "미정으로 남은 것". About 1,900 characters. **Moves.**
- C: "#4 코멘트 · #7 §6 · [상세](OpenDecisionProposals.md#od-4)" - the discussion location. **Stays.**

OD-13, last cell, four parts in this order:
- A: from "**P1 정책**: 반복마다 스칼라 샘플 하나" to "반영: [ADR-0007](decisions/ADR-0007-od13-measurement-policy.md)." **Moves.**
- B: from "**`cpu_standin`에서 C 커널의 샘플을 얻는 방법**" to "반영: [ADR-0009](decisions/ADR-0009-od13-cpu-standin-timing-run.md)." **Moves** (A and B are contiguous: one moved span).
- C: from "잔여(제안 유지): incumbent의 paired interleaved 재측정," to "타이밍 방어는 OD-16." - what is still proposed. **Stays.**
- D: "#7 §5 G2 · [상세](OpenDecisionProposals.md#od-13)". **Stays.**

### Planner's judgements (2026-10-11T00:3xZ, from the files at `main` `31da22a`; **the reviewer is asked to re-check each**)
- **Why this item now.** No lock, no TODO / INTERRUPTED task file, no open PR. T-0088, T-0106, T-0107, T-0116, T-0117 and T-0121 are BLOCKED on HQ-0005 to HQ-0010, unanswered. The planner re-read PLAN, the journal of 2026-10-09 and 2026-10-10 and the `## Follow-ups` of the DONE tasks: every open PLAN item waits on one of those HQs or on an owner item, the shared once-only write helper stays deferred until 2026-10-16, and the design-level sub-questions without a caller (OD-13 sub-questions 7 and 8, OD-16 sub-questions 1 and 6, OD-18 sub-questions 2, 3, 5, 10, 11) were judged and not planned on 2026-10-10 (T-0107 and T-0116 `## Follow-ups`); this planner did not overturn that. This row upkeep is the one recorded follow-up that needs neither an owner answer nor new content.
- **The weakest point, weigh it first - the order T-0118 wrote.** Its follow-up reads "after T-0088 and T-0116 are done or re-planned ... the same move for the OD-18 row, then a judgement on the rows of 1,100 to 1,800 characters". The planner reads the condition as protecting the rows that BLOCKED tasks edit, not as an order between unrelated rows: T-0088, T-0106 and T-0116 edit the OD-18 row; T-0088 reads the rows OD-16 and OD-17 by line number and T-0121 reads OD-16; T-0117 edits the rows OD-6 and OD-1; T-0121 edits OD-8 and OD-14. **No BLOCKED task edits or quotes the OD-4 or the OD-13 row** (T-0117 names OD-13 only as a boundary). So this task takes those two rows and stays off OD-18, OD-16, OD-6 and OD-17. **If a reviewer reads T-0118's order as binding, or reads this edit as the integrator's or the repository owner's to make, do not argue it out: land nothing and return BLOCKED ("requirement unclear") with that reading as the question.**
- **Second weak point - what stays differs between the two rows and from T-0118.** T-0118 left the OD-8 row with location, links and pointer only, and its reviewer noted (Minor) that the register alone then no longer says what is open. Here each row already has one sentence "잔여(제안 유지): ..." that says it; keeping an existing sentence writes no new summary, so it stays in both rows. OD-4's first sentence is a one-line summary of the item (about 135 characters) and stays; OD-13's part A is a paragraph of about 750 characters that cannot be made a line without rewording it, so it moves whole. If the reviewer wants another **whole existing sentence** kept or moved, follow the reviewer, provided no sentence is reworded and the verbatim check below still holds; say so in `## Result`.
- **Third - "미정으로 남은 것" leaves the OD-4 row.** Part B ends with a list of what is undecided about the first instance (the values of a real machine, `hw_source`, who registers, the SDPA shape members). It is inside the moved span and cannot be kept without splitting a sentence. The pointer clause of the new cell says where it is; the OD-26 row, which states the `hw_source` and registration questions as its own, is not touched.
- **Not an unchecked PLAN item.** DRIVER §3-3 / §6 name unticked PLAN items as planner input and do not forbid an upkeep task; T-0113, T-0114, T-0115, T-0118, T-0119 and T-0120 were of this kind and their reviewers accepted them.
- **Objection windows.** ADR-0035 and ADR-0036 are inside their 7-day windows (until 2026-10-16), ADR-0007 to ADR-0009 until 2026-10-14. A task that reverts one of them edits its clause wherever it stands; after this task it stands in a list item instead of a table cell. No new risk.
- **A-13 reading**: document mode (`ARCHITECTURE/` only). No ADR, no OD status change, no owner notice under DRIVER §9, no schema, no code.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, commit trailers) - mandatory for every task (§6)
- PROCESS/DRIVER.md §0, §1-5 (Bypass permissions; the forbidden actions; a denied or failed tool call is BLOCKED, never worked around), §2, §3 "BLOCKED 사유" paragraph
- CLAUDE.md - whole file; in particular "문서 커버리지 재검사", "미결은 발명하지 않는다" (the one-line rule), "세션 진입 점검", "브랜치·merge 절차" (document mode, the `Reviewed-by` trailer)
- ARCHITECTURE/Requirements.md - the "Open Decisions" preamble (from "본 표가 미결 항목의 단일 등록부" to the table header: 상태 어휘, 갱신 규칙, 정본 규칙, 제안 상세, 등록 범위) in full; **row OD-4 (line 91) and row OD-13 (line 100)**; row OD-8 (line 95) for the form T-0118 landed; rows OD-2 and OD-21 for the shape of a short row. Read the long rows with a script (`sed -n 91p`, or Python with `encoding="utf-8"`), cell by cell (the cells are separated by ` | `)
- ARCHITECTURE/OpenDecisionProposals.md - lines 1 to 9 (what the document holds, who is the source for what); the OD-4 section (lines 32 to 44) and the OD-13 section (lines 188 to 199): which bullets exist and in which order; the end of the OD-8 section (the bold label line "**등록부(Requirements.md) OD-8 행의 마지막 칸에서 옮긴 글 (2026-10-10, 문장 변경 없음)**" and the list under it) for the form of a moved block. The lines are long; read their first 300 characters each - the existing content is not edited
- ARCHITECTURE/StandardScenarios.md - "검사 규칙" (line 13) and "검사 결과" (from line 155: the heading note and the history paragraph with its dated passages, the last of which is T-0118's)
- PROCESS/tasks/T-0118-od8-register-row-one-line-rule.md - `## Acceptance Criteria` and `## Result` (the new cell, the label line, the verbatim script check, the coverage passage and the reviewer's findings as landed)
- .claude/skills/dev-item-address/SKILL.md (document mode: document checks instead of tests, steps 9 to 12 and 15) and .claude/skills/dev-code-review/SKILL.md (document-mode return path; the "no invented decisions" check)

Line numbers are those of `main` at `31da22a`; if they moved, find the passage by its words.

## Acceptance Criteria
Verify every figure and every part boundary of `## Why` against the files at execution time; if a file says otherwise, the file wins and the difference is named in `## Result`. If a cell no longer has the parts described (a task landed in between and changed it), stop and return BLOCKED ("task needs re-planning").

### `ARCHITECTURE/Requirements.md` - exactly two lines change (the OD-4 row and the OD-13 row)
- In both rows the first four cells (the id, the item, the related ids, **the status cell**) stay byte for byte.
- OD-4, new last cell, in this order: part A unchanged, except that its "반영:" names, after ADR-0001 and separated by " · " as in the OD-8 row, the other records the old cell links, in the order of their first appearance and each with its link text and target as they are (ADR-0008, ADR-0035, ADR-0036 at planning time; derive the list with a script) - the residual sentence of part A keeps its place after the links; then one pointer clause in Korean saying that the summaries of what those records fixed for the first instance, and what is left undecided there, are in the OD-4 section of the proposals document; then part C unchanged.
- OD-13, new last cell, in this order: "반영:" and the links to ADR-0007 and ADR-0009 (text and target as they are, " · " between them); one pointer clause in Korean saying that the summaries of the confirmed parts and the sub-questions of OD-13 are in the OD-13 section of the proposals document; then part C unchanged; then part D unchanged.
- Apart from the kept parts, a new cell states **no content of a decision and no sub-question**: the added words are the link list and the pointer clause only. No raw `|` in a new cell; each row still has five cells.
- No other line of the file changes: the preamble, every other row (OD-26 included), the FR / NFR / C tables. `git diff --numstat origin/main -- ARCHITECTURE/Requirements.md` shows `2 2`.

### `ARCHITECTURE/OpenDecisionProposals.md` - one added block in each of the two sections
- OD-4: part B, whole, is added as one block at the end of the OD-4 section (after its last existing line, before `## OD-5`). OD-13: parts A and B, whole and in that order, are added as one block at the end of the OD-13 section (before `## OD-14`).
- Each block opens with one label line in Korean in the form T-0118 landed (a bold line, no new heading) that says only where the text comes from and when it was moved: the last cell of the OD-4 (OD-13) row of the register, the UTC date of the move, sentences unchanged. No statement about which copy is authoritative, about the records or about the bullets above it.
- The text is split into list items so that it can be read: split only between two sentences, never inside one (part B of OD-4 may turn out to be one sentence or very few; then it is one or few items - do not split inside it). **No character of the moved text is added, removed or replaced.** The only differences from the cell are the list marker and line break at each split and the single space that stood there. If a cell holds an escaped pipe or a `<br>`, say how each was carried over. A phrase that reads oddly outside the table stays as it is and is named in `## Result`.
- Every existing line of the file stays byte for byte: no merge with the "채택분" or "하위 질문" bullets, no deduplication, no reordering. `git diff --numstat` for this file shows additions only.

### `ARCHITECTURE/StandardScenarios.md` - the coverage re-check CLAUDE.md asks for
- Re-apply the checking rules of the document to the steps and result rows that cite OD-4 or OD-13 (at planning time: steps at lines 105, 141 and 151; result rows S0, S1, S6, S9, S10 and whatever a search finds). Expected, and to be confirmed: no step, no verdict and no gap changes, because no status and no decision changed. Record it in "검사 결과" in the form T-0118 used (the heading note and one dated passage of one or two sentences; no row edited). If the rules give another outcome, stop and return BLOCKED ("requirement unclear") with the finding.

### Do not invent, do not tidy
- No new summary of a record, no rewording, no translation, no correction of a sentence of the moved or kept text even where it looks wrong or stale (name it in `## Result` instead).
- No change of an OD status, no new sub-question, no renumbering. No edit of the rows OD-18, OD-16, OD-6, OD-17, OD-8, OD-26 or any other row, of a record under `ARCHITECTURE/decisions/`, of `UsageCases.md`, of CLAUDE.md, of anything under `PROCESS/` (the BLOCKED task files included), `hilclaw/`, `tests/`, `.github/` or `.claude/`.
- No rule for future edits is written into either document.

### Document checks (document mode replaces tests; list each with its outcome in `## Result`)
- **The verbatim check, by a script kept outside the repository** (session scratchpad; not committed), once per row: take the old last cell from `git show origin/main:ARCHITECTURE/Requirements.md`; take the kept parts from the new cell and the added block from the working tree; strip the label line, the list markers and the line breaks of the block and join its items with single spaces. Then (a) the moved text equals the span of the old cell described in `## Why`, character for character, and (b) the old cell equals its kept parts and the moved span put back in their old order (single spaces between them), once the added link list and pointer clause are taken out of the new cell. State both comparisons and the lengths in `## Result`, and give the reviewer the script.
- The links after "반영:" in each new cell are exactly the record links of the old cell, in order of first appearance, with unchanged text and targets (script); every link of the new cells and of the added blocks resolves from the file it is in.
- The anchors `#od-4` and `#od-13` still match their headings; no new heading was added.
- `git diff --stat origin/main` lists only the three files of `touchesFiles`; the numstat lines above hold; `git ls-files --eol` shows `i/lf` for all three (when a script writes a file on Windows, open it with `encoding="utf-8"` and `newline="\n"`; set `PYTHONIOENCODING=utf-8` before printing).
- The lengths of both rows and of their last cells before and after, in characters.
- A search, reported by file with counts and **edited nowhere**: sentences outside the two edited files that say a summary or a sub-question is "in the OD-4 row" or "in the OD-13 row" of the register (`git grep -n -e "OD-4" -e "OD-13" -- ARCHITECTURE/decisions ARCHITECTURE/StandardScenarios.md ARCHITECTURE/UsageCases.md hilclaw README.md PROCESS/DRIVER.md PROCESS/PLAN.md PROCESS/tasks`, read for that claim only). If a BLOCKED task file (T-0088, T-0106, T-0107, T-0116, T-0117, T-0121) tells its executor to find a sentence in one of the two rows that this task moves, name the file and line in `## Result` and in the follow-ups; do not edit it.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0122'`; then the session entry check of CLAUDE.md (`gh pr list --repo myungjoo/HIL-Claw --state open`, issues #4, #5, #7, #8). An open PR that edits line 91 or line 100 of `ARCHITECTURE/Requirements.md` or the OD-4 or OD-13 section of the proposals document is BLOCKED ("open PR conflict"). If the repository owner has answered an HQ in the meantime, that does not stop this task.
- Document mode (CLAUDE.md A-13): branch `claude/T-0122-od4-od13-register-rows-one-line-rule`; the reviewer cycle of dev-item-address steps 10 to 12 with a fresh-context `dev-reviewer` each round (at most 7 rounds; past the cap without a final Approve, return BLOCKED; a result starting with `SECURITY` is BLOCKED; if no reviewer can be spawned, return BLOCKED - do not self-review). Ask the reviewer explicitly to (a) **re-check the planner's judgements in `## Why`, the weakest point first**; (b) run the verbatim script itself; (c) read the added words of the two new cells for any sentence that states a decision or a sub-question; (d) confirm that the status cells and every other line of both files are unchanged; (e) re-check the coverage outcome.
- Then rebase on `origin/main` and push to `main` without a PR. Commit message: English; subject starts with `T-0122:`; the body names the rule, says that the text was moved unchanged and how that was checked, and gives the row lengths before and after; trailers in this order: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0122`, then any attribution trailer your session requires.
- Never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around. Delete the task branch only after the push to `main` is confirmed, remote and local in separate commands.
- `## Result`: fill it in after the push, on `main`, and leave that edit uncommitted for the driver (DRIVER §3-6). Record: the commit, review rounds and findings (what each reviewer said on the weakest point), the two new cells as landed (quoted inline), the label lines as landed, the number of list items per block, the document checks with their outcomes, the coverage outcome, the follow-ups. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters (result, commit, BLOCKED or not).

## Out of Scope
- The status cells of both rows; the rows OD-18, OD-16, OD-6, OD-17, OD-8 and every other row; the preamble of the register.
- Any change inside the moved text, inside the kept parts or inside the existing bullets of the proposals document; removing what is said twice there.
- Every record under `ARCHITECTURE/decisions/`; `UsageCases.md`; CLAUDE.md; `PROCESS/`; code, tests, CI.
- Anything HQ-0005 to HQ-0010 ask; the task files of T-0088, T-0106, T-0107, T-0116, T-0117 and T-0121.
- Closing any sub-question of OD-4 or OD-13.

## Follow-ups
- (planner of the next record under OD-4 or OD-13) The row no longer takes a clause per record: the record's link joins the "반영:" list of the row, and its summary and sub-question go to the section of the proposals document.
- (planner - after T-0088, T-0116, T-0117 and T-0121 are done or re-planned, document mode) The same move for the rows OD-18 (10,885 characters), OD-16, OD-6 and OD-17 (T-0118 `## Follow-ups`).
- (integrator / repository owner) The long status cells of the rows OD-8, OD-4 and OD-13 and the preamble paragraph that repeats them in prose; whether the OD-8 row should carry a one-line summary of what is still open (T-0118 `## Result`).
- (planner - not before 2026-10-16, code mode, no change of behaviour) One shared once-only write helper for the three writers (`key_records`, `instance_file`, `spec_file`) (T-0094 `## Result`).
- (driver / owner) HQ-0005 (T-0088) and HQ-0008 (T-0116): the rest of PLAN P1-1. HQ-0006 (T-0106). HQ-0007 (T-0107) and the hook registration of PLAN P0.5-4. HQ-0009 (T-0117): PLAN P1-5. HQ-0010 (T-0121): the isolation means of OD-8.

## Result
