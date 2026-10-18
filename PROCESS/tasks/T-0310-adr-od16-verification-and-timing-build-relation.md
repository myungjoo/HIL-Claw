---
id: T-0310
title: Record ADR-0107, the relation between the verification build and the timing build of one attempt (same settings or not, one executable or two) for the runs the existing contracts cover (OD-16 sub-question 6, with the sameness part of OD-18 sub-question 19 (ra))
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-9, FR-10, OD-16, OD-18]
dependsOn: [T-0308]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0107-od16-verification-and-timing-build-relation.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 220, files: 4}
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts) is open. Two parts of it are blocked on HQs: ⑲ (나) (T-0210, HQ-0021) and `profiler.collect` (T-0239, HQ-0025). The ADR-0106 code slice landed with T-0309. One open point is not blocked and is named in many records: **OD-16 sub-question ⑥**. Should the verification executable and the timing executable of one attempt be built with the same flags, or be one executable?

The threat is stated in ADR-0017 Limits (line 104): "**The verified executable is not the timed one**: a kernel can tell the two programs apart and compute properly only when it is verified, and two builds may differ. Nothing here detects either (rest of OD-16; sub-question ⑥)." Since then each tool contract has made its own settings "the backend's own" without relating the two:
- `correctness.check`: ADR-0056 decision 4 and ADR-0060 decision 3. ADR-0060 line 67 says: "Whether the verification build and the timing build use the same settings is open as before: the timing build is the run tools', and only a record of theirs can say whether their settings are the same backend's own."
- `sim.run` / `board.run`: ADR-0061 decision 3 (line 55). ⑲ (라) asks for "the source and values of the backend's own settings for the timing build and the timing run, **and whether they are the same as the verification build's**".

Both tool contracts now exist up to their operation form (ADR-0056/0060 and ADR-0061 to ADR-0067). The relation can be decided without the setting values, which stay with ⑱ (라), ⑲ (라) and OD-14. The relation does not depend on ⑲ (나) (T-0210), on the compiler log (⑲ (다); ADR-0078, whose code slice T-0243 is BLOCKED on HQ-0026), on `profiler.collect` or on any runtime acceptance item.

OD-16 is a design-level OD. It is not owner-only: DRIVER §9 reserves #5 A/B items, C-6, OD-25 and OD-3. Under DRIVER §6 and §9 this task writes the ADR.

**Numbering.** On `main` the highest record is ADR-0106. The unlanded, BLOCKED branches of T-0210, T-0231 and T-0264 hold ADR-0068, ADR-0074 and ADR-0088. Never take one of those numbers. This task uses **ADR-0107**.

(The planner considered a doc task that edits the earlier records ADR-0106 Consequences lists as "now less exact". It did not choose that task. Earlier records are not edited after acceptance in this repository: each new record lists the sentences it makes less exact instead, e.g. ADR-0078 Consequences. That list spans nine records, beyond the 5-file cap.)

## Required Reading

- `PROCESS/DRIVER.md` §2 (doc mode), §3-5 (executor procedure, resume rule, time limit), §5 (naming: branch `claude/T-0310-<slug>`, trailer `Task: T-0310`; size cap), §8 (the `— posted by driver` footer), §9 (OD closing authority, owner notice on #5, 7-day objection window).
- `CLAUDE.md`: all rules. In particular: "미결은 발명하지 않는다"; the 문서 커버리지 재검사 rule; the A-13 branch/merge procedure (doc mode) and its BLOCKED reasons, a data-plane schema change among them; "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole; doc-mode return path).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` §"Record format" (from line 146).
- `ARCHITECTURE/decisions/ADR-0017-od16-cpu-standin-verification-run.md`: decisions 1 and 2 (lines 24-37), Limits (lines 101-108), Alternatives (lines 109-125), Boundaries (lines 136-145).
- `ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md`: decisions 1 and 2 (lines 23-35), 9 and 10 (lines 94-117), Alternatives (lines 118-140).
- `ARCHITECTURE/decisions/ADR-0056-od18-correctness-check-verification-executable.md`: decisions 3 and 4 (lines 46-94), Alternatives (lines 166-184), Boundaries (lines 193-206; line 197 names OD-16 ⑥).
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`: decision 3 (lines 46-68, especially the settings table and line 67), Boundaries (lines 162-176), and the sub-question ⑱ it registers.
- `ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md`: decisions 2 and 3 (lines 39-59), Limits (lines 113-123), and the sub-question ⑲ it registers (line 168).
- `ARCHITECTURE/decisions/ADR-0064-od13-run-tools-timing-seed.md` decision 6 (lines 86-91). This is the parallel choice for inputs: timing and verification inputs are not tied. Do not reopen it.
- `ARCHITECTURE/decisions/ADR-0065-od18-run-tools-operation-form.md`: decisions 2 and 9 (lines 33-54, 117-124) and Boundaries (lines 179-190).
- `ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md`: Status (lines 3-13) and Boundaries (lines 131-143). It is a model for the manner of a record: cited versus this record's own, stated costs, objection points.
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84), FR-9 (line 27), and the OD register rows OD-6 (line 97), OD-14 (line 105), OD-16 (line 107) and OD-18 (line 109).
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - the header's "기록 규칙" (line 8);
  - the OD-16 section (lines 230-250), in particular sub-question ⑥ at the end of the bullet at line 247 and the 채택분 lines;
  - the OD-18 section's sub-questions ⑱ and ⑲ (⑲ at line 333);
  - OD-6 sub-question ② (the members of `build.json`);
  - OD-14 sub-question ①.
  - Check the last registered sub-question number of OD-16 on the day.
- `ARCHITECTURE/StandardScenarios.md`: §검사 규칙 (lines 13-29) and §검사 결과 (from line 168), especially its first paragraph (the recording rule) and the "최근 재검사" line (line 172).
- Code, read only as observations at the current `main` (this record binds no code): `hilclaw/harness/verification_build.py`, `hilclaw/harness/timing_build.py`, `hilclaw/check_build.py`, `hilclaw/run_operation.py`, `hilclaw/clang_build.py` (read only; it is under open PR #179).
- Before you edit `ARCHITECTURE/`, run `gh pr list` and read issues #4, #5, #7 and #8 (the CLAUDE.md 세션 진입 점검). If an open PR touches the same tables or sections, stop and return BLOCKED. Open PR #179 touches only `hilclaw/clang_build.py` and its test. The unlanded branches of T-0210, T-0231 and T-0264 edit the OD-18 row, the OD-18 section and §검사 결과. They are not open PRs and do not block this task. Edit `main` as it stands and leave reconciling to whichever lands second.

## Acceptance Criteria

1. **The record.** A new record `ARCHITECTURE/decisions/ADR-0107-od16-verification-and-timing-build-relation.md` exists in the ADR-0001 record format: Status, Context, Decision with numbered decisions, a Walk-through, Limits, Alternatives considered, Consequences, Boundaries, References.
   - Before the push, confirm that ADR-0107 is still free on origin/main and on every remote branch. If it is taken, take the next free number that none of those holds (never 0068, 0074 or 0088) and update every reference.
   - Keep the record at about 190 lines or fewer.
2. **Scope and decisions.** Scope: the runs for which both tools have contracts, i.e. the first case's local configuration (`cpu_standin`) and runs whose hw_profile names the mock (ADR-0060 decision 1, ADR-0061 decision 1). Follow the "cited" versus "this record's own" convention of ADR-0062 onward, and state the cost of each choice. Weigh each point against at least one alternative:
   - (a) **One executable or two.** Weigh at least: keeping two programs (ADR-0017 decision 2, ADR-0009 decision 2); one program that both verifies and times; and the verification program linked into the timing run. Choosing one executable reopens ADR-0017 decision 2 and ADR-0009. If you judge that right, stop and return BLOCKED with the question rather than reopening them.
   - (b) **Sameness of settings.** Decide whether the kernel sources of one attempt must be compiled with the same compiler, flags and trailing flags (and whatever other settings you judge relevant, e.g. the environment of the build) in the verification build of a check and in the timing build of a run tool call. Say at which granularity: the same execution point, both points, or across `execution` numbers. Say what may differ: the harness-side program, its own sources and their defines. Weigh at least "the same, required of the backend" against "no relation stated" (today's state, ADR-0060 line 67), and consider a third such as "the same only for the kernel's translation units".
   - (c) **Who guarantees it and what detects a breach.** Nothing records the settings of a build today: `build.json` members are OD-6 ②; the record of a build's command and settings is ⑰ (다). State that, and whether the rule is a requirement on the backend that nothing detects (as ADR-0016 decision 6 is cited elsewhere) or needs something more. Do not add a file or a member.
   - (d) **What the decision does to the threat of ADR-0017 Limits.** State which part is narrowed and which remains: a kernel that tells the programs apart at run time is not prevented by equal settings. Say whether that remaining part stays in OD-16 or needs a new sub-question.
3. **Walk-through table.** Cover at least these cases:
   - a check and a timing run of the same attempt at the same point;
   - the same at different points;
   - a further `execution`;
   - a backend whose settings differ between the two builds;
   - a run at the mock (which builds nothing).
4. **Not decided, and said openly**:
   - the setting values and their source (⑱ (라), ⑲ (라) apart from sameness, OD-14);
   - the container (OD-14 ①);
   - the members of `build.json` and any record of a build's settings (OD-6 ②, ⑱ (가), ⑰ (다));
   - the compiler log of the timing build (⑲ (다));
   - ⑲ (나) (T-0210, an unlanded branch; do not cite it);
   - the seeds and draws (OD-16 ⑤; ADR-0064 decision 6 stands);
   - which check or execution counts (⑭, ⑳);
   - other backends and runs;
   - #5 A-4, B-2, B-3, B-7.

   Do not invent an owner decision.
5. **No data-plane schema change.** Do not add, remove or change a file, a member of a result, a request, a line of `events.ndjson`, `instance.json`, `STATE.json`, a spec, `build.json` or a result file, and do not add a value of `condition`, an `error.kind` or a reserved kind. State the A-13 reading in Consequences. If the design you judge right needs any of these, stop and return BLOCKED with the question. Do not write it.
6. **Earlier records.** Cite earlier records only for what they say. No earlier record is edited. Consequences lists the earlier sentences that become less exact, found by grep on the day. At least check: ADR-0017 Limits (line 104); ADR-0056 Boundaries (line 197); ADR-0060 decision 3 (line 67) and its Boundaries ("Whether the builds of an attempt use the same flags"); ADR-0061 decision 3 and the ⑲ (라) text. Consequences names any code slice the record makes possible, or states that none follows; a code slice would be, for example, the `cpu_standin` operations taking their build settings from one source. Name no module or function as binding.
7. **`ARCHITECTURE/Requirements.md`**: follow the "행 형식" rule written in that file (line 84). In the OD-16 row, add exactly one ADR-0107 link with a topic of a few words to `**확정분**:`, creating that label in the row's form if the row has none. Rewrite `**잔여**:` in place for ⑥: remove it, or narrow it to what stays open. If the record also answers the sameness part of ⑲ (라), edit the OD-18 row's `**잔여**:` entry for ⑲ in place, and add an ADR-0107 link there only if that row's own form lists the records answering its sub-questions. Do not restate the record, and add no dated sentence or chain. The status cells and the number of OD rows are unchanged.
8. **`ARCHITECTURE/OpenDecisionProposals.md`**: follow the header's "기록 규칙" (line 8).
   - Add one `- **채택분**` line for ADR-0107, in Korean, in the OD-16 section.
   - Rewrite the status tail of sub-question ⑥ and its bullet-head status word in place. Do the same for ⑲ in the OD-18 section if (라) is partly answered. Keep each question's wording, and add no dated note.
   - Register a new sub-question only if the record needs one, with the next free number of that OD.
   - Copy nothing from the register row.
9. **`ARCHITECTURE/StandardScenarios.md`**: run the coverage re-check under §검사 규칙 and record it as the first paragraph of §검사 결과 prescribes. Update the "최근 재검사" line in place (date, trigger, result). Add an entry to "판정 변화 이력" only if a verdict changed or a gap was found or closed. Write no ADR summary.
10. **Document checks**, reported in `## Result`:
    - every relative link in the new and edited text resolves;
    - `git diff --stat origin/main` shows only the files in `touchesFiles`;
    - `git diff --check` is clean;
    - the OD register has the same number of rows before and after.
11. **Doc mode** (CLAUDE.md A-13):
    - Branch `claude/T-0310-adr-od16-verification-and-timing-build-relation`.
    - A reviewer cycle with a fresh-context reviewer, at most 7 rounds.
    - Then rebase on origin/main and push to main directly.
    - Commit trailers, in the last paragraph of the message: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0310` and the `Co-Authored-By` line, with no blank line between them.
    - Delete the branch afterwards, locally and on the remote if it was pushed.
12. **Owner notice.** After landing, post the owner notice of DRIVER §9 on issue #5 in English. It states what ADR-0107 decides, the landed commit and the objection window (7 days from the notice). Its last line is `— posted by driver`. Record the comment URL in `## Result`.

## Out of Scope

- Any change to `hilclaw/`, `tests/`, CI, settings files or the `HIL-Claw-data` repository. In particular `hilclaw/clang_build.py` and `tests/test_clang_build.py` (open PR #179).
- Editing any earlier ADR, including the "now less exact" sentences ADR-0106 lists.
- ⑲ (나) and ADR-0068 (T-0210, HQ-0021), ADR-0078's code slices (T-0243, HQ-0026), `profiler.collect` (T-0239, HQ-0025).
- Setting values, the container design, and any runtime acceptance item. No compiler, container or `claude` is started.

## Follow-ups

- If the record makes a code slice possible (e.g. one settings source shared by the `cpu_standin` check and run operations), a later code task.

## Result
