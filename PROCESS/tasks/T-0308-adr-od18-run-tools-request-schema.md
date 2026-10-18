---
id: T-0308
title: Record ADR-0106, the member list of a request of sim.run and board.run, what their tool function does with a member no record names, and their input schemas and descriptions (OD-18)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-10, OD-18]
dependsOn: [T-0211]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0106-od18-run-tools-request-schema.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 220, files: 4}
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts) is open. The run tools `sim.run` and `board.run` have seven accepted records (ADR-0061 to ADR-0067), and every one of them leaves the same item to a later slice. ADR-0062 decision 4 says it most directly: "The member list of a request is not closed by this record. Whether a request carries anything else, the input schema, the description and what the tool function does with a member no record names are a later slice's", and adds that "A member named `point` in a request of either tool states nothing; whether such a request is refused is what the tool function does with a member no record names". ADR-0063 to ADR-0067 carry it on as "the rest of the request" or "the input schema and the description".

`correctness.check` closed the same item in ADR-0069 (T-0211) once every input had a source outside the request. The run tools are now in that position:
- the point: the tool called says it (ADR-0061 decision 5);
- the dimensions, `n_max` and the objective: read from `instance.json` in ④ (ADR-0061 decision 3, ADR-0067);
- the sample form: derived from the objective, "the request carries none" (ADR-0061 decision 4);
- the `bound`: read from `instance.json` (ADR-0061 decision 6);
- the seed: drawn by the tool function, "No request member carries it" (ADR-0064 decision 2);
- the timing executable: reached through the output path formed from the identity (ADR-0061 decision 3; ADR-0065);
- the settings of the timing build and run: the backend's own, with their source and values open as OD-18 sub-question ⑲ (라).

So this slice can now be decided as one piece. Without it, the run tools cannot have a tool definition: a tool definition needs a non-blank description and an input schema (ADR-0015 decision 2), and ADR-0077 has a check that runs over every tool of the default registry. The slice does not depend on any unresolved HQ. It does not touch ⑲ (나) (T-0210, HQ-0021, ADR-0068 on an unlanded branch), `profiler.collect` (T-0239, HQ-0025) or any runtime acceptance item.

OD-18 is a design-level OD, not owner-only (DRIVER §9: owner-only means #5 A/B items, C-6, OD-25 and OD-3). Under DRIVER §6 and §9 this task writes the ADR.

**Numbering.** On `main` the highest record is ADR-0105. ADR-0068, ADR-0074 and ADR-0088 are held by the unlanded branches of T-0210, T-0231 and T-0264 (all BLOCKED). Never take one of those three numbers. This task uses **ADR-0106**.

## Required Reading

- `PROCESS/DRIVER.md` §2 (doc mode), §3-5 (executor procedure, resume rule, time limit), §5 (naming: branch `claude/T-0308-<slug>`, trailer `Task: T-0308`; size cap), §8 (the `— posted by driver` footer), §9 (OD closing authority, owner notice on #5, 7-day objection window).
- `CLAUDE.md`: all rules. In particular "미결은 발명하지 않는다", the 문서 커버리지 재검사 rule, the A-13 branch/merge procedure (doc mode), the BLOCKED reasons (a data-plane schema change is one of them), and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole; doc-mode return path).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` §"Record format" (from line 146) and decision 1 (the *name* form).
- `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md` decisions 2 to 4.
- `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md` decision 2 (lines 39-57) and decision 4 (lines 67-82).
- `ARCHITECTURE/decisions/ADR-0039-od18-blob-push-fetch-local.md` decision 3 (lines 36-42): a closed request, `"additionalProperties": false`, the reduction rule for a keyword Claude Code does not accept, and "the text of the descriptions is the code task's".
- `ARCHITECTURE/decisions/ADR-0069-od18-correctness-check-request-schema.md` whole (151 lines). It is the model for the manner of the record. Do not re-decide it, and do not copy it where the run tools differ: there is no `point` member, there are two tools, and the operation receives the request as it is (ADR-0065 decision 2).
- `ARCHITECTURE/decisions/ADR-0077-od18-schema-function-agreement-check.md` decisions 2 to 4 and 6 (what checks that a stated schema and the function agree, the keyword set, and the open half of sub-question ⑤).
- The run tools' records, read as far as they bear on the request:
  - `ADR-0061-*` decisions 1 and 3 to 6, and its Alternatives row 4;
  - `ADR-0062-*` decisions 4 and 6 (lines 66-98), Alternatives rows for decision 4 (around line 139-141), and Boundaries (around line 154);
  - `ADR-0063-*` Boundaries "The rest of the request" (around line 219);
  - `ADR-0064-*` decision 2;
  - `ADR-0065-*` decision 2 (lines 50-59, alternative (c) and "An operation takes its point from no member of the request") and Boundaries (around line 183);
  - `ADR-0066-*` decision 3 and its alternative (b) (line 51: an answer that depends on a request member is fault injection, OD-18 sub-question ⑧);
  - `ADR-0067-*` decision 5 (the order of ④) and Consequences (lines 145-148).
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84) and the OD register row OD-18 (line 109).
- `ARCHITECTURE/OpenDecisionProposals.md`: the header's "기록 규칙" (line 8); the OD-18 section (from line 261), in particular the adopted-part bullets for ADR-0061 to ADR-0069 and ADR-0077 (lines 291-300), and the registered sub-questions ⑤ (line 320), ⑧, ⑲ (line 332) and ⑳ (line 333). Check the last registered number on the day.
- `ARCHITECTURE/StandardScenarios.md`: §검사 규칙 (lines 13-29) and §검사 결과 (from line 168), especially its first paragraph (the recording rule) and the "최근 재검사" line.
- Code, read only as observations (this record binds no code): `hilclaw/run_identity.py` (the check of the five members and the two `step` values), `hilclaw/hw_tool.py` (`stepped_tool_function`), `hilclaw/journaled_tool.py` (the frame check), `hilclaw/tools.py` (`ToolDefinition`, `Registry.register`, `default_registry`: the run tools are not registered), `hilclaw/check_identity.py` and `hilclaw/check_definition.py` (how ADR-0069 landed in code, for comparison only).
- Before you edit `ARCHITECTURE/`, run `gh pr list` and read issues #4, #5, #7 and #8 (the CLAUDE.md 세션 진입 점검). If an open PR touches the same tables or sections, stop and return BLOCKED. The unlanded branches of T-0210, T-0231 and T-0264 also edit the OD-18 row, the OD-18 section and §검사 결과. They are not open PRs and do not block this task. Edit `main` as it stands and leave reconciling to whichever lands second.

## Acceptance Criteria

1. A new record `ARCHITECTURE/decisions/ADR-0106-od18-run-tools-request-schema.md` exists in the ADR-0001 record format: Status, Context, Decision with numbered decisions, a Walk-through, Limits, Alternatives considered, Consequences, Boundaries, References. Before the push, confirm that ADR-0106 is still free on origin/main and on every remote branch. If it is taken, take the next free number that none of those holds (never 0068, 0074 or 0088) and update every reference. Keep the record at about 190 lines or fewer.
2. Scope: a request of `sim.run` or `board.run` about one attempt of a run (ADR-0062 decision 4), both tools in one record as ADR-0062 and ADR-0063 do. Weigh each point against at least one alternative, and mark the record's own design as its own, following the "cited" versus "this record's own" convention of ADR-0062 onward:
   - (a) **The member list.** Decide whether the list is closed at the five members of ADR-0062 decision 4 (`run_id`, `round`, `candidate`, `attempt`, `execution`). For each input listed in this task's Why, cite the record that gives it a source outside the request, or state that it is open with its sub-question (the settings, ⑲ (라)). State how closing the list relates to ⑲ (라) and to ⑧ without answering either. If a later record gives the request a member, that is a change of the contract and amends the list and the schema.
   - (b) **A member no record names.** Weigh at least three options: refusal as `invalid_request`, ignoring it, and handing it on to the operation. The third matters because the request reaches the operation as it is (ADR-0016 decision 2, cited in ADR-0065 decision 2), and an answer that depends on a request member is ⑧'s (ADR-0066). Say what a request with `point`, `seed`, `n_max`, `bound`, `objective` or a dimension member gets, and at which moment of the order of a call (ADR-0062 decision 6, ①). Give the message rule: what the message may name, and that it shows nothing of a given value.
   - (c) **The input schemas.** Give the JSON Schema each tool definition states (ADR-0015 decision 2: a statement to the caller, not a check, and one that admits every request the tool function accepts) in full, for the forms of ADR-0015 decision 4 and ADR-0062 decision 4. Say whether the two tools state the same schema. Say which constraints of the function a schema cannot state; the description tells those. Take over the reduction rule of ADR-0039 decision 3. Relate the schemas to ADR-0077's check and keyword set without changing that check. Leave the open half of sub-question ⑤ open: do not claim what Claude Code does with `inputSchema`.
   - (d) **The descriptions.** State what each description must at least tell the caller: which point the tool times; that the call is journaled and a repeated identity gets the stored outcome; that the run's own `instance.json` supplies the dimensions, `n_max`, the objective and the `bound`; and what the function refuses beyond the schema. The texts are the code task's.
   - (e) **A Walk-through table.** Cover at least: a valid request; a request with `point`; one with `seed` or `n_max`; one with a misspelled member; and one valid by the schema but refused by the function.
   - Do the name check of ADR-0041 decision 4 for any new name (grep `hilclaw/`, `tests/` and `ARCHITECTURE/` on the day). The expected outcome is that no new kind, member or `step` value is introduced. If one is, check `ARCHITECTURE/EventKinds.md`, `ARCHITECTURE/StepValues.md` and `ARCHITECTURE/SpendAxes.md` as their records require.
3. **Not decided, and said openly**: `correctness.check` (ADR-0069 stands, unchanged); `blob.push`/`blob.fetch`; the second half of sub-question ⑤; ⑧; ⑲ (나) to (라); ⑳; the spend (OD-2, OD-19); the tool function that joins the run tools' modules, the binding of a backend and a source of seeds, and the registration; the result files (PLAN P1-8); `profiler.collect`; what anybody does after any answer (FR-1, OD-10, OD-17, PLAN P2-1); #5 A-4, B-2, B-3, B-7. Do not invent an owner decision.
4. **No data-plane schema change.** Do not add, remove or change a member of a result, a line of `events.ndjson`, `instance.json`, `STATE.json`, a spec or a result file. A request is not a file of the data plane; state the A-13 reading in Consequences. If the design you judge right needs a new request member, a new member of any file, or a new reserved kind, stop and return BLOCKED with the question. Do not write it.
5. Cite earlier records only for what they say. No earlier record is edited. Consequences lists the earlier sentences that become less exact, found by grep on the day. At least: ADR-0062 decision 4 ("The member list of a request is not closed …" and the `point` sentence), its Alternatives row and Boundaries; the "rest of the request" or "input schema and description" items of ADR-0063, ADR-0065, ADR-0067 and ADR-0068 if it has landed by then (do not cite an unlanded branch).
6. Consequences names the code slice this record makes possible: the refusal of an unnamed member, and the two input schemas and descriptions, with tests. Whether that code lives in `hilclaw/run_identity.py` or a new module, and the names, are the code task's. Consequences also names what still stands between that slice and two registered tools: the joining tool function, ⑲ (나), and the binding and registration.
7. `ARCHITECTURE/Requirements.md`, OD-18 row: follow the "행 형식" rule written in that file (line 84). Add exactly one ADR-0106 link with a topic of a few words to `**확정분**:`. Rewrite `**잔여**:` in place only if a listed open part is now closed. Do not restate the record, and do not add a dated sentence or chain. The status cell and the number of OD rows are unchanged.
8. `ARCHITECTURE/OpenDecisionProposals.md`, OD-18 section: follow the header's "기록 규칙" (line 8). Add one `- **채택분**` line for ADR-0106 in Korean, placed with the run tools' bullets. If the record answers part of a registered sub-question, rewrite that question's status tail and its bullet-head status word in place, and keep the question's wording; add no dated note. Register a new sub-question only if the record needs one (next free number). Copy nothing from the register row.
9. `ARCHITECTURE/StandardScenarios.md`: run the coverage re-check under §검사 규칙 and record it as the first paragraph of §검사 결과 prescribes. Update the "최근 재검사" line in place (date, trigger, result). Add an entry to "판정 변화 이력" only if a verdict changed or a gap was found or closed. Write no ADR summary.
10. Document checks, reported in `## Result`: every relative link in the new and edited text resolves; `git diff --stat origin/main` shows only the files in `touchesFiles`; `git diff --check` is clean; the OD register has the same number of rows before and after.
11. Doc mode (CLAUDE.md A-13): branch `claude/T-0308-adr-od18-run-tools-request-schema`, a reviewer cycle with a fresh-context reviewer, at most 7 rounds, then rebase on origin/main and push to main directly. Commit trailers, in the last paragraph of the message: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0308` and the `Co-Authored-By` line. Delete the branch afterwards, locally and on the remote if it was pushed.
12. After landing, post the owner notice of DRIVER §9 on issue #5 in English. It states what ADR-0106 decides, the landed commit and the objection window (7 days from the notice). Its last line is `— posted by driver`. Record the comment URL in `## Result`.
13. Nothing is built or run except read-only git/gh, grep and link checks. No `claude` process, compiler, kernel or container is started (D16).

## Out of Scope

- Any code, including the refusal of unnamed members, the schemas and descriptions in code, the joining tool function and the registration of the run tools. No changes to `hilclaw/` or `tests/`.
- The request of `correctness.check` (ADR-0069) and of `blob.push`/`blob.fetch`.
- OD-18 sub-questions ⑤ (second half), ⑧, ⑲ (나) to (라) (⑲ (나) is T-0210's, HQ-0021) and ⑳; the spend (OD-2, OD-19); `profiler.collect` (T-0239, HQ-0025); the result files `sim.json`/`board.json`.
- Editing any earlier ADR. List the sentences that become less exact in Consequences instead.

## Follow-ups

## Result
