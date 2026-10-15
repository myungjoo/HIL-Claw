---
id: T-0201
title: Record ADR-0064, the timing seed of a call of sim.run / board.run (OD-13 sub-question 7, ADR-0061 Consequences item (3))
phase: P1
status: DONE
commitMode: doc
coversReq: [NFR-3, FR-9, FR-10, OD-13, OD-16, OD-18]
dependsOn: [T-0191, T-0195, T-0199]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0064-od13-run-tools-timing-seed.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 290, files: 4}
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts) is open. The run tools `sim.run` / `board.run` now have three records: ADR-0061 (split, sample form, the call that carries the memory figure, where the `bound` is read), ADR-0062 (call identity) and ADR-0063 (result members). The code that builds a result exists (`hilclaw/run_result.py`, T-0200). No tool function of either tool can be written to its end, because the timing seed is still open. ADR-0061 Consequences item (3), ADR-0062 Consequences item (3), ADR-0063 Consequences and Boundaries, and the Follow-ups of T-0199 and T-0200 all name the timing seed (OD-13 sub-question ⑦) as the next slice.

OD-13 is a design-level OD and is not owner-only (DRIVER §9: owner-only means #5 A/B items, C-6, OD-25 and OD-3). Under DRIVER §6 and §9, this task therefore includes writing the ADR that answers sub-question ⑦ for the runs of ADR-0061 decision 1: a run whose hw_profile names `cpu_standin` in the local configuration, or names the mock. Use the manner of ADR-0021 decision 3 and ADR-0048, which answered the same questions for `correctness.check`.

Sub-question ⑦ (OpenDecisionProposals.md, OD-13 section) asks about the seed policy of timing inputs: is the seed fixed or drawn fresh for each run, is it recorded after the run, and must the inputs of a timing run equal the verification inputs of the same attempt (together with OD-16). ADR-0009 decision 5 made the seed "a parameter of the run" with no default and left the policy open. ADR-0061 decision 3 made it an input that the tool function hands to the operation and that the operation does not choose. ADR-0061 decision 7 and ADR-0063 decision 8 keep the seed out of a result "until OD-13 sub-question ⑦ is answered". ADR-0062 decision 6 leaves open where the seed comes from and whether it comes before or after the start line.

## Required Reading

- `PROCESS/DRIVER.md` §2 (doc mode), §3-5 (executor procedure, resume rule, time limit), §5 (naming: branch `claude/T-0201-<slug>`, trailer `Task: T-0201`; size cap), §8 (the `— posted by driver` footer), §9 (OD closing authority, the owner notice on #5, the 7-day objection window).
- `CLAUDE.md`: all rules. In particular: "미결은 발명하지 않는다", the 문서 커버리지 재검사 rule, the A-13 branch/merge procedure (doc mode: reviewer cycle, rebase, direct push to main with the `Reviewed-by` trailer), the BLOCKED reasons (a data-plane schema change is one), the 코멘트 최소화 rule, and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole; doc-mode return path).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` §"Record format" (from line 146).
- `ARCHITECTURE/decisions/ADR-0048-od18-correctness-check-seed-draw.md` (whole, 211 lines): the model for this record.
- `ARCHITECTURE/decisions/ADR-0021-od18-correctness-check-split.md` decision 3 (lines 54-65): the seed of a check, the property of its source, not kept, not in the start line.
- `ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md` decisions 5 and 9 (lines 50-58, 94-110), Alternatives row 5 (line 130), Consequences and Boundaries (lines 141-159).
- `ARCHITECTURE/decisions/ADR-0017-od16-cpu-standin-verification-run.md` decision 3 (lines 38-48), decision 9 (lines 86-100), Boundaries (lines 136-145).
- `ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md`: Status (lines 3-15), decisions 3 and 7 (lines 49-59, 86-97), Limits (lines 113-123), Consequences and Boundaries (lines 148-170).
- `ARCHITECTURE/decisions/ADR-0062-od18-run-tools-call-identity.md`: decision 2 (lines 37-52), decision 6 and the Walk-through (lines 80-114), Consequences and Boundaries (lines 144-166).
- `ARCHITECTURE/decisions/ADR-0063-od18-run-tools-result-members.md`: Status (lines 3-15), decisions 8 and 9 (lines 107-144), Limits (lines 170-183), Consequences and Boundaries (lines 207-232).
- `ARCHITECTURE/Requirements.md`: the OD register rows OD-13 (line 102), OD-16 (line 105) and OD-18 (line 107), and NFR-3 (line 46).
- `ARCHITECTURE/OpenDecisionProposals.md`: the OD-13 section (lines 207-229; sub-question ⑦ is at line 215), the OD-16 section (lines 249-280; sub-question ⑤ is at line 267) and the start of the OD-18 section (from line 281; its adopted-part bullets for ADR-0061 to ADR-0063).
- `ARCHITECTURE/StandardScenarios.md`: §검사 규칙 (lines 13-29), and §검사 결과 from line 168 (its heading and its latest 2026-10-15 passages).
- Code, read only as observations (this record binds no code): `hilclaw/harness/seed_source.py` (module docstring, `draw`, `system`), `hilclaw/check_seed.py` (module docstring, `KIND_SEED_NOT_DRAWN`), and `hilclaw/harness/timing.py` (lines 20-35, 90-95 and 172-190: the seed argument and its range 0 <= seed < 2**64).
- Before you edit `ARCHITECTURE/`, run `gh pr list` and read issues #4, #5, #7 and #8 (the CLAUDE.md 세션 진입 점검). If an open PR touches the same tables or sections, stop and return BLOCKED.

## Acceptance Criteria

1. A new record `ARCHITECTURE/decisions/ADR-0064-od13-run-tools-timing-seed.md` exists in the ADR-0001 record format: Status, Context, Decision with numbered decisions, a Walk-through, Limits, Alternatives considered, Consequences, Boundaries, References. Before the push, confirm that ADR-0064 is still free on origin/main. If it is not, take the next free number and update every reference to it. Keep the record at about 230 lines or fewer, so that the task stays within the 300-LOC cap.
2. Scope: the runs of ADR-0061 decision 1 only, and both tools. Say explicitly that this is not a rule of the frame and not a rule for any other HW tool (#5 A-4). The record answers the following, each one weighed against at least one alternative. Every answer is the record's own design. Do not present any of them as the owner's.
   - (a) **Source and frequency**: whether the timing seed is fixed or drawn for each call. If it is drawn: who draws it (above the cut or at the backend; see ADR-0021 decision 3 "Not the backend"), how many times per call, the property its source must have (as a property, not an algorithm), and the range (the harness accepts 0 <= seed < 2**64). Also say whether a request may carry it or a calling agent may choose it.
   - (b) **Place of the draw relative to the start line** (ADR-0062 decision 6 left this open), and **what a call answers when the draw yields no seed**: the class of the answer, its `kind` and whether that kind is the tool's own, what its message may carry, and whether a line is left in `events.ndjson`. Follow the ADR-0048 manner. The kind spelling is the record's choice. If it reuses `seed_not_drawn`, say how a kind that is the tool's own can be shared by three tools, or why it is not shared.
   - (c) **Whether the seed is recorded after a run, and whether it may reach a result or the log.** This answers what ADR-0061 decision 7 and ADR-0063 decision 8 left "until OD-13 sub-question ⑦ is answered". **Do not add a member to any data-plane file or record** (results, `events.ndjson` lines, `instance.json`, STATE, result files). Such a member is a data-plane schema change and a CLAUDE.md A-13 BLOCKED reason. If the design you judge right needs such a member, stop and return BLOCKED (`data-plane schema change`) with the question. Do not write it.
   - (d) **The relation to the verification inputs of the same attempt** (the second clause of ⑦, coupled with OD-16 sub-question ⑤): either answer it for these runs, with reasons, or leave it under Boundaries with the reason it cannot be answered here. Do not answer the check-side clauses of OD-16 ⑤.
3. Cite earlier records only as they say things. Mark every sentence of the record's own as its own (the ADR-0048 convention: "cited" versus "this record's own"). Do not invent an owner decision. No earlier record is edited. In Consequences, list the earlier sentences that become less exact, at least the ones that say the seed or its place is open: ADR-0009 decision 5, the parameter table row and Consequences; ADR-0061 decision 7 and its Boundaries bullet; ADR-0062 decision 6 table row and Boundaries; ADR-0063 decision 8, its "In which sense the list is closed" bullet and Boundaries. If decision (c) adds nothing to a result, say that the closed member list of ADR-0063 decision 9 is unchanged.
4. Consequences names the code slice this record makes possible: the run tools' seed draw and its tests (names and modules are left to the code task). It also names the next contract slice, ADR-0061 Consequences item (4): the form of what crosses the cut and the neither-form answer.
5. `ARCHITECTURE/Requirements.md`: in the OD-13 row, add a 반영 link to ADR-0064 and update the 잔여 text for ⑦, as ADR-0061 and ADR-0063 were added. Keep the status wording of the row (**확정** with its parenthetical) unchanged. Edit the OD-16 and OD-18 rows only if a sentence in them becomes false. Do not change the number of OD rows.
6. `ARCHITECTURE/OpenDecisionProposals.md`: in the OD-13 section, mark what ADR-0064 answers of sub-question ⑦ for these runs, in the strike-through-and-arrow style used elsewhere in the file, or as a dated note if only part is answered. Leave ⑧ untouched. In the OD-18 section, add one adopted-part bullet for ADR-0064 after the ADR-0063 bullet. Touch OD-16 ⑤ only to note the coupling if (d) is answered. Register no new sub-question unless the record needs one; if it does, register it in the same section with the date 2026-10-15 or later.
7. `ARCHITECTURE/StandardScenarios.md`: run the coverage re-check under §검사 규칙. Append a dated passage to §검사 결과 with the verdict (expected: no verdict change and no gap; report honestly if otherwise), and extend the heading parenthetical with one clause for this record, as previous ADR tasks did.
8. Document checks are reported in `## Result`:
   - every relative link in the new and edited text resolves;
   - `git diff --stat origin/main` shows only the files in `touchesFiles`;
   - `git diff --check` is clean;
   - the OD register has the same number of rows before and after.
9. Doc mode (CLAUDE.md A-13): branch `claude/T-0201-<slug>`, the reviewer cycle with a fresh-context reviewer, at most 7 rounds, then rebase on origin/main and push to main directly. Commit trailers: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0201`, and the `Co-Authored-By` line. Delete the local branch afterwards.
10. After landing, post the owner notice of DRIVER §9 on issue #5 in English: what ADR-0064 decides, the landed commit, and the objection window (7 days from the notice). Its last line is `— posted by driver`. Record the comment URL in `## Result`.
11. Nothing is built or run except read-only git/gh and link checks. No `claude` process, compiler, kernel or container is started (D16).

## Out of Scope

- Any code. That includes the seed draw of the run tools, their tool functions, and changes to `hilclaw/harness/seed_source.py`, `hilclaw/check_seed.py`, `hilclaw/run_result.py` or `hilclaw/harness/timing.py`.
- OD-13 sub-question ⑧ (calls per repeat), ⑪ (imprecise timing environment), and the result-file half of ⑩.
- ADR-0061 Consequences items (4) to (7): the form of what crosses the cut, the neither-form answer, the mock's operation and its scripts, the answers of ⑲, setting values, the spend.
- The check-side clauses of OD-16 ⑤: the draw count, whether the check's seed is recorded, re-verification at the promotion gate.
- Editing ADR-0009, ADR-0017, ADR-0021, ADR-0048 or ADR-0061 to ADR-0063. List less-exact sentences in Consequences instead.
- The integrator list of less-exact sentences from ADR-0063 Consequences (a separate integrator follow-up).

## Follow-ups

- (planner, code mode, P1-1, after this record) The seed draw of `sim.run` / `board.run` as ADR-0064 decides it (and its no-seed answer), with D12 tests. Names and modules are left to the code task; `hilclaw/check_seed.py` is the analogue for the check.
- (planner, document mode, §9, P1-1) ADR-0061 Consequences item (4): the form of what crosses the cut, and what a call answers when an operation returns neither form (in the manner of ADR-0043 and ADR-0045).

## Result

- **Outcome: DONE.** Landed on `main` as `d1e68f3` (document mode, direct push after rebase on `origin/main` = `846db0f`; trailers `Reviewed-by: reviewer agent (5 rounds, Approve)`, `Task: T-0201`, `Co-Authored-By`). Branch `claude/T-0201-od13-run-tools-timing-seed` deleted locally and on the remote. ADR-0064 was still free on `origin/main` before the push.
- **Review**: 5 rounds with fresh-context `dev-reviewer` agents. Round 1 Request changes: (1) NFR-2 was not weighed in decision 5, (2) the non-reservation of `seed_not_drawn` was not marked provisional though the one-tool premise of ADR-0048 no longer holds, (3) nit: say test (ii) does not adopt OD-16 threat B ⑴. All three fixed. Round 2 Approve with 4 nits (plural "kinds" in the ADR-0061 citation, the ADR-0009 Consequences reading, "however its inputs are drawn" marked as the record's reading, "(b) to (e)"). Fixed. Round 3 Approve with 1 nit (ADR-0045 as the source of "a raised request to end"). Fixed. Round 4 Approve with 1 optional nit (References entry for ADR-0045). Fixed. Round 5 Approve, no findings.
- **What ADR-0064 decides** (runs of ADR-0061 decision 1 only; both tools; no frame rule; all the record's own design): (a) the timing seed is drawn, not fixed, by the tool function above the cut, once per call that reaches the draw, from a source with the property of ADR-0021 decision 3, over 0 <= seed < 2**64; no request member, no calling-agent choice (five ways weighed). (b) The draw lies after the last answer of ④ and before the start line; a draw that yields no seed is a tool failure of the run tools' own kind `seed_not_drawn` (same spelling and meaning as ADR-0048's; sharing justified by ADR-0015 decision 2 leaving unreserved kinds to each tool; not reserved, provisionally), no line, message rule of ADR-0048 decision 6; the record asks the later slice that no end line holds the kind. (c) The tool layer keeps the seed nowhere after the run; a result never holds it; ADR-0063 decision 9 unchanged; no data-plane member (recording weighed against the OD-16 principle, ADR-0062 decision 2 and NFR-2 and not taken on its merits). (d) Answered on the timing side: timing inputs are not tied to the verification inputs; check-side clauses of OD-16 ⑤ untouched.
- **Files** (`git diff --stat 846db0f d1e68f3`): `ARCHITECTURE/decisions/ADR-0064-od13-run-tools-timing-seed.md` (+167, new), `ARCHITECTURE/Requirements.md` (OD-13 row: 반영 link and narrowed ⑦ residual, status wording unchanged; OD-16 row: the "타이밍 입력과의 관계" clause notes the timing-side answer, since it became partly false; OD-18 row untouched — its seed sentences are statements about earlier records and stay true), `ARCHITECTURE/OpenDecisionProposals.md` (OD-13 ⑦ dated strike-through/arrow note, ⑧ untouched; OD-16 ⑤ coupling note; OD-18 adopted-part bullet after ADR-0063's; no new sub-question), `ARCHITECTURE/StandardScenarios.md` (heading clause and the 2026-10-15 9th passage). 4 files, 175 insertions, 5 deletions.
- **Document checks**: every relative link in the new and edited text resolves (59 links checked, 0 bad); `git diff --stat origin/main` showed only the four `touchesFiles`; `git diff --check` clean; OD register rows 30 before and 30 after. Coverage re-check (StandardScenarios §검사 규칙): no verdict change, no gap.
- **Owner notice (DRIVER §9)**: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6191741115 (English, last line `— posted by driver`; objection window 7 days, until 2026-10-22). The last sentence of the notice was corrected by an edit right after posting (it lists the windows of ADR-0048 and ADR-0061 to ADR-0063).
- **D16 / AC 11**: nothing was built or run; no `claude` process, compiler, kernel or container was started. Only git/gh and a read-only link check were run.
- **Follow-ups** (as in the task, unchanged): the code task for the run tools' seed draw and its `seed_not_drawn` answer with D12 tests; the document task for ADR-0061 Consequences item (4) (form of what crosses the cut, neither-form answer). Integrator follow-up: the less-exact sentences listed in ADR-0064 Consequences (ADR-0009, ADR-0017, ADR-0048, ADR-0061 to ADR-0063).
