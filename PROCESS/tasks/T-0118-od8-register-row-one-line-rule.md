---
id: T-0118
title: Bring the OD-8 row of the Open Decisions register back under the one-line rule - move the text of its last cell to the OD-8 section of OpenDecisionProposals.md without changing a sentence, and leave the row with its status, the links to the records and a pointer
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [NFR-2, OD-8, "CLAUDE.md OD register rule"]
dependsOn: []
touchesFiles: [ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 60, files: 3}   # one line of Requirements.md replaced; about 35-45 added lines in OpenDecisionProposals.md (long lines, moved text only); a few lines of the coverage result
hq: []   # no owner-only decision and no OD closure: no sentence about a decision is written, changed or dropped; text is moved between two files that a stated rule assigns it to
---
## Why
Three places state one rule for the Open Decisions register:
- CLAUDE.md, "미결은 발명하지 않는다": "OD 등록부에는 한 줄 요약만 두고 제안 본문은 OpenDecisionProposals.md에 쓴다."
- `ARCHITECTURE/Requirements.md`, the paragraph "**제안 상세**" above the register: "본 표에는 **한 줄 요약**만 적어 표가 읽히도록 유지한다. 제안 본문의 정본은 Proposals 문서, 상태·논의 위치의 정본은 본 표다."
- `ARCHITECTURE/OpenDecisionProposals.md` line 3: "등록부에는 한 줄 요약만 남겨 표가 읽히도록 유지한다."

The OD-8 row does not follow it. Measured at `main` `3891c1f` (characters, not bytes):

| Row (line of Requirements.md) | Whole row | Status cell | Last cell |
|---|---|---|---|
| OD-8 (95) | 36,463 | 1,209 | 35,150 |
| OD-18 (105) | 5,759 | 3 | 5,604 |
| OD-4 (91), OD-16 (103), OD-13 (100), OD-6 (93), OD-17 (104) | 1,151 to 1,749 | | |
| the other 22 rows | 115 to 632 | | |

Each of the twenty records closed under OD-8 since 2026-10-07 added "one clause in the manner of the earlier clauses" to that one cell, and each record that handed a question on added its sub-question there as well. The cell now holds a condensed summary of every record (each ending in "반영: [ADR-NNNN](...)") and a condensed list of what is still open. The longer form of both already stands in the OD-8 section of `OpenDecisionProposals.md` (lines 77 to 133: one "채택분(ADR-NNNN ...)" bullet per record, one "하위 질문(ADR-NNNN이 넘긴 것 ...)" bullet per hand-over). Since T-0084 the task files tell their executors to read the row "with a script or `sed -n`, not as a whole file"; the table is no longer readable as a table, which is the one thing the rule exists for.

**This task moves the text of that cell, unchanged, to the OD-8 section of the proposals document and leaves the row with what the register is the source for**: the status (untouched), where each confirmed part is reflected (the links to the records - the "갱신 규칙" of the register asks for them), where the discussion is, and a pointer. Nothing is summarised anew, merged or deleted.

It ticks **no PLAN checkbox**. It is upkeep of a document against its own rule, in the manner of T-0115 (README against `main`).

Planner's judgements (2026-10-10T11:2xZ, from the files at `main` `3891c1f`; **the reviewer is asked to re-check each**):
- **Why this item now.** No lock, no TODO / INTERRUPTED task file, no open PR. T-0088, T-0106, T-0107, T-0116 and T-0117 are BLOCKED on HQ-0005 to HQ-0009, unanswered on #5 (72 comments, the last one the HQ-0009 mirror). The two planners before this one found no executable PLAN slice and raised HQ-0008 and HQ-0009; this planner re-read the `## Follow-ups` of the DONE task files and the register and found no further record or code slice that neither waits on the repository owner nor would have to invent its content (the shared once-only write helper stays deferred until 2026-10-16). The drift above is real, has a stated rule on its side and is not named by any earlier task as someone else's.
- **The weakest point, weigh it first - whether the row's text may leave the register at all.** The register calls itself "미결 항목의 단일 등록부". The planner's reading: the registered item is OD-8; its status and discussion location stay in the row; the numbered sub-questions and the summaries of the confirmed parts are "제안 본문" in the sense of the "제안 상세" paragraph, and each already has its longer bullet in the proposals document. **If a reviewer reads the summaries or the sub-question texts as content the register itself must hold, or reads this edit as the integrator's or the repository owner's to make, do not argue it out: land nothing and return BLOCKED ("requirement unclear") with that reading as the question.**
- **Second weak point - not an unchecked PLAN item.** DRIVER §3-3 / §6 name unticked PLAN items as planner input and do not forbid an upkeep task; T-0113, T-0114 and T-0115 were of this kind and their reviewers accepted them.
- **Why the move is verbatim and not a clean-up.** Deleting what the proposals bullets "already say" would need a sentence-by-sentence judgement over 35,000 characters, and every dropped sentence would be a risk of losing a statement about a decision. A move that changes no character can be checked by a script.
- **Why OD-8 only.** It is six times longer than the next row. The rows OD-18, OD-6 and OD-1 are edited by the BLOCKED tasks T-0088, T-0116 and T-0117 once their HQs are answered; this task stays off those rows and off their sections, so it overlaps none of them (they share the two files, not a line).
- **Objection windows.** The records under OD-8 are inside their 7-day windows (the last ends 2026-10-16). A task that reverts one of them already has to edit by hand, since every later record changed the same single line; after this task it edits one bullet instead. No new risk.
- **A-13 reading**: document mode (`ARCHITECTURE/` only). No ADR, no OD status change, no owner notice under DRIVER §9, no schema, no code.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, commit trailers) - mandatory for every task (§6)
- PROCESS/DRIVER.md §0, §1-5 (Bypass permissions; the forbidden actions; a denied or failed tool call is BLOCKED, never worked around), §2, §3 "BLOCKED 사유" paragraph
- CLAUDE.md - whole file; in particular "문서 커버리지 재검사", "미결은 발명하지 않는다" (the one-line rule), "세션 진입 점검", "브랜치·merge 절차" (document mode, the `Reviewed-by` trailer)
- ARCHITECTURE/Requirements.md - the "Open Decisions" preamble (lines 66 to 86: 상태 어휘, 갱신 규칙, 정본 규칙, 제안 상세, 등록 범위, the table header) in full; rows OD-2 (line 89), OD-13 (line 100) and OD-21 (line 108) for the shape of a row; **row OD-8 (line 95)**. Read line 95 with a script (`sed -n 95p`, or Python with `encoding="utf-8"`), cell by cell (the cells are separated by ` | `), not as a whole file
- ARCHITECTURE/OpenDecisionProposals.md - lines 1 to 9 (what the document holds, who is the source for what) and the OD-8 section (lines 77 to 133): which bullets exist and in which order. Its lines are 1,000 to 21,000 characters long; read their first 300 characters each - the content is not edited
- ARCHITECTURE/StandardScenarios.md - "검사 규칙" (line 13) and "검사 결과" (from line 155: the heading note and the history paragraph with its dated passages)
- PROCESS/tasks/T-0112-adr-od6-gemm-contract-zero-dimension.md `## Result` (the bullet on `ARCHITECTURE/StandardScenarios.md`: the form in which the latest coverage re-check was recorded) and PROCESS/tasks/T-0115-readme-status-refresh.md (`## Why` "Planner's judgements" and the review part of `## Result`: how an upkeep task with a guarded exit was handled)
- .claude/skills/dev-item-address/SKILL.md (document mode: document checks instead of tests, steps 9 to 12 and 15) and .claude/skills/dev-code-review/SKILL.md (document-mode return path; the "no invented decisions" check)

Line numbers are those of `main` at `3891c1f`; if they moved, find the passage by its words.

## Acceptance Criteria
Verify every figure of `## Why` against the files at execution time; if a file says otherwise, the file wins and the difference is named in `## Result`.

### `ARCHITECTURE/Requirements.md` - exactly one line changes (the OD-8 row)
- The first four cells (`OD-8`, the item, `FR-13`, **the status cell**) stay byte for byte. The status cell is long as well, but it is the status, for which the register is the source; shortening it is not this task (Follow-ups).
- The last cell is replaced by a cell that holds only, in this order:
  1. the sentence on the discussion location that ends the cell today, unchanged: "#4 §2 초안 · #5 A-1/A-2/B-4 입력 확보(OD-3 결과는 별도 입력 — 트리는 gate 목록에 의존하지 않음)." (copy it from the file, not from here);
  2. "반영:" and the links to the records the cell names with "반영:" today - twenty at planning time, ADR-0004, 0005, 0006, 0012, 0013, 0014, 0018, 0020, 0022 to 0025, 0027 to 0034 - in the same order, each with its link text and target as they are (derive the list from the file with a script; a record the cell links without "반영:", such as ADR-0021, is not added);
  3. one pointer clause in Korean saying that the summaries of the confirmed parts and the sub-questions of OD-8 are in the OD-8 section of the proposals document, with the existing link `[상세](OpenDecisionProposals.md#od-8)`. If the moved block gets a heading of its own, the clause may link that heading in addition.
- The new cell states **no content of a decision and no sub-question**: no sentence that says what a record decided, left open or handed on. It has no raw `|`, and the row still has five cells.
- No other line of the file changes: the preamble (the long paragraph at line 84 included), every other row, the FR / NFR / C tables. `git diff --numstat origin/main -- ARCHITECTURE/Requirements.md` shows `1 1`.

### `ARCHITECTURE/OpenDecisionProposals.md` - one added block inside the OD-8 section
- The whole text of the old last cell, **minus** the discussion-location sentence of point 1 and the closing `[상세](...)` link, is added as one block at the end of the OD-8 section (after its last existing line, before `## OD-9`).
- The block opens with one label line in Korean (a sub-heading or a bold line; the form is yours) that says only where the text comes from and when it was moved: the last cell of the OD-8 row of the register, 2026-10-10, sentences unchanged. No statement about which copy is authoritative, about the records or about the bullets above it.
- The text is split into list items so that it can be read: split only between two sentences, never inside one. **No character of the moved text is added, removed or replaced.** The only differences from the cell are the list marker and line break at each split and the single space that stood there. (The cell holds no escaped pipe and no `<br>` at planning time; if it does at execution time, say how each was carried over.) A phrase that reads oddly outside the table, such as "— 상세 참조", stays as it is and is named in `## Result`.
- Every existing line of the file stays byte for byte, lines 1 to 9 and the existing bullets of the OD-8 section included: no merge with the "채택분" or "하위 질문" bullets, no deduplication, no reordering. `git diff --numstat` for this file shows additions only.

### `ARCHITECTURE/StandardScenarios.md` - the coverage re-check CLAUDE.md asks for
- Re-apply the checking rules of the document to the steps that cite OD-8 (S3, S5, S8, S10 and whatever a search for `OD-8` finds). Expected, and to be confirmed: no step, no verdict and no gap changes, because no status and no decision changed. Record it in "검사 결과" in the form the latest re-check used (the date in the heading note and one dated passage of one or two sentences; no row edited). If the rules give another outcome, stop and return BLOCKED ("requirement unclear") with the finding.

### Do not invent, do not tidy
- No new summary of a record, no rewording, no translation, no correction of a sentence of the moved text even where it looks wrong or stale (name it in `## Result` instead).
- No change of an OD status, no new sub-question, no renumbering. No edit of a record under `ARCHITECTURE/decisions/`, of `UsageCases.md`, of CLAUDE.md, of `PROCESS/DRIVER.md` or `PROCESS/PLAN.md`, of a file under `hilclaw/`, `tests/`, `.github/` or `.claude/`.
- No rule for future edits is written into either document (how the next record under OD-8 adds its clause is for the planner of that task; see Follow-ups).

### Document checks (document mode replaces tests; list each with its outcome in `## Result`)
- **The verbatim check, by a script kept outside the repository** (session scratchpad; not committed): take the old last cell from `git show origin/main:ARCHITECTURE/Requirements.md` and the added block from the working tree; strip the label line, the list markers and the line breaks of the block, join its items with single spaces, and compare with the old cell minus the sentence of point 1 and the closing link. The two strings are equal. State the comparison and the two lengths in `## Result`, and give the reviewer the script so that it can be run again.
- The twenty (or, at execution time, N) links of the new cell are the "반영:" links of the old cell in the same order (script), and every link of the new cell and of the added block resolves from the file it is in (both files are in `ARCHITECTURE/`, so the relative targets `decisions/ADR-...` hold in both).
- The anchor `#od-8` still matches its heading; a new sub-heading, if any, has an anchor that the pointer clause matches.
- `git diff --stat origin/main` lists only the three files of `touchesFiles`; the numstat lines above hold; `git ls-files --eol` shows `i/lf` for all three (when a script writes a file on Windows, open it with `encoding="utf-8"` and `newline="\n"`; the console is not UTF-8, set `PYTHONIOENCODING=utf-8` before printing).
- The lengths of the OD-8 row before and after, in characters.
- A search, reported by file with counts and **edited nowhere**: sentences outside the two edited files that say a summary or a sub-question is "in the OD-8 row" of the register (`git grep -n "OD-8" -- ARCHITECTURE/decisions ARCHITECTURE/StandardScenarios.md ARCHITECTURE/UsageCases.md hilclaw README.md PROCESS/DRIVER.md PROCESS/PLAN.md`, read for that claim only). They are records or out of this task's mode; the pointer of the row keeps them followable.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0118'`; then the session entry check of CLAUDE.md (`gh pr list --repo myungjoo/HIL-Claw --state open`, issues #4, #5, #7, #8). An open PR that edits `ARCHITECTURE/Requirements.md` line 95 or the OD-8 section of the proposals document is BLOCKED ("open PR conflict"). If the repository owner has answered an HQ in the meantime, that does not stop this task.
- Document mode (CLAUDE.md A-13): branch `claude/T-0118-od8-register-row-one-line-rule`; the reviewer cycle of dev-item-address steps 10 to 12 with a fresh-context `dev-reviewer` each round (at most 7 rounds; past the cap without a final Approve, return BLOCKED; a result starting with `SECURITY` is BLOCKED; if no reviewer can be spawned, return BLOCKED - do not self-review). Ask the reviewer explicitly to (a) **re-check the planner's judgements in `## Why`, the weakest point first**; (b) run the verbatim script itself; (c) read the new cell for any sentence that states a decision or a sub-question; (d) confirm that the status cell and every other line of both files are unchanged; (e) re-check the coverage outcome.
- Then rebase on `origin/main` and push to `main` without a PR. Commit message: English; subject starts with `T-0118:`; the body names the rule, says that the text was moved unchanged and how that was checked, and gives the row length before and after; trailers in this order: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0118`, then any attribution trailer your session requires.
- Never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around. Delete the task branch only after the push to `main` is confirmed, remote and local in separate commands.
- `## Result`: fill it in after the push, on `main`, and leave that edit uncommitted for the driver (DRIVER §3-6). No fenced code block in it. Record: the commit, review rounds and findings (what each reviewer said on the weakest point), the new cell as landed (quoted inline), the label line as landed, the number of list items, the document checks with their outcomes, the coverage outcome, the follow-ups. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters (result, commit, BLOCKED or not).

## Out of Scope
- The status cell of the OD-8 row; the rows OD-18, OD-4, OD-16, OD-13, OD-6, OD-17 and every other row; the preamble paragraph at line 84.
- Any change inside the moved text or inside the existing bullets of the proposals document; removing what is said twice there.
- Every record under `ARCHITECTURE/decisions/`; `UsageCases.md`; CLAUDE.md; `PROCESS/`; code, tests, CI.
- Anything HQ-0005 to HQ-0009 ask; the task files of T-0088, T-0106, T-0107, T-0116 and T-0117.

## Follow-ups
- (planner of the next record under OD-8) The row no longer takes a clause per record: the record's link joins the "반영:" list of the row, and its summary and sub-question go to the OD-8 section of the proposals document. Write the criteria of that task accordingly.
- (driver / planner) T-0116 `## Required Reading` says "search the long OD-8 row for `blob`"; after this task that search belongs to the OD-8 section of the proposals document. The task file is not edited here.
- (planner - after T-0088 and T-0116 are done or re-planned, document mode) The same move for the OD-18 row (5,759 characters), then a judgement on the rows of 1,100 to 1,800 characters (OD-4, OD-16, OD-13, OD-6, OD-17).
- (integrator / repository owner) The status cell of the OD-8 row (1,209 characters: one clause per confirmed part) and the preamble paragraph at line 84 of Requirements.md (1,996 characters, the same list in prose); whether what is said twice in the OD-8 section of the proposals document is merged.
- (driver / owner) HQ-0005 (T-0088) and HQ-0008 (T-0116): the rest of PLAN P1-1. HQ-0006 (T-0106). HQ-0007 (T-0107) and the hook registration of PLAN P0.5-4. HQ-0009 (T-0117): PLAN P1-5.
- (planner - not before 2026-10-16, code mode, no change of behaviour) One shared once-only write helper for the three writers (`key_records`, `instance_file`, `spec_file`) (T-0094 `## Result`).

## Result
