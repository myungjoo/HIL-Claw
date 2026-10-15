---
id: T-0211
title: Record ADR-0069, the member list of a request of correctness.check, what the tool function does with a member no record names, and the tool's input schema and description (OD-18)
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-10, OD-18]
dependsOn: [T-0189]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0069-od18-correctness-check-request-schema.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 260, files: 4}
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts) is open. `correctness.check` has a tool function on `main` (`hilclaw/check_tool.py`) that joins the modules of ADR-0021, ADR-0040 to ADR-0048, ADR-0056 and ADR-0060, but it "is not yet the tool a registry offers: it has no input schema and no description" because "The member list of a request is open (ADR-0040 decision 5)". ADR-0040 decision 5 left to a later slice "Whether a request carries anything else — for `draws`, the dimensions, the kernel of the attempt, flags or time limits ... so are the input schema and the description, and so is what the tool function does with a member that no record names". Every later record of that contract (ADR-0041, ADR-0042, ADR-0046, ADR-0047, ADR-0060) carries the same item as still open ("The rest of the request").

Since ADR-0040, each of the inputs it listed has been given a source outside the request: the dimensions from `instance.json` (ADR-0041), `draws` from `instance.json` (ADR-0046), the kernel of the attempt through the output path formed from the identity (ADR-0056 decision 3), flags and time limits as the backend's own (ADR-0060 decision 3, with OD-18 sub-question ⑱ (가) open on whether settings written in run files reach the operation). So the slice "the rest of the request, its input schema and description" of `correctness.check` can now be decided as one closed piece. It is the step that stands between `hilclaw/check_tool.py` and a registered tool, and it does not depend on any unresolved HQ: it touches neither the run tools' ⑲ (나) (HQ-0021, T-0210) nor a runtime acceptance item.

This is part of OD-18, a design-level OD, not owner-only (DRIVER §9: owner-only means #5 A/B items, C-6, OD-25 and OD-3). Under DRIVER §6 and §9 this task writes the ADR.

**Numbering.** ADR-0068 is held by the unlanded branch `claude/T-0210-od18-run-tools-operation-tool-failure` (BLOCKED, HQ-0021). This task uses **ADR-0069** and must not take ADR-0068, even though it is free on `main`.

## Required Reading

- `PROCESS/DRIVER.md` §2 (doc mode), §3-5 (executor procedure, resume rule, time limit), §5 (naming: branch `claude/T-0211-<slug>`, trailer `Task: T-0211`; size cap), §8 (the `— posted by driver` footer), §9 (OD closing authority, owner notice on #5, 7-day objection window).
- `CLAUDE.md`: all rules. In particular "미결은 발명하지 않는다", the 문서 커버리지 재검사 rule, the A-13 branch/merge procedure (doc mode: reviewer cycle, rebase, direct push to main with the `Reviewed-by` trailer), the BLOCKED reasons (a data-plane schema change and a new external dependency are among them), 코멘트 최소화, and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole; doc-mode return path).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` §"Record format" (from line 146) and decision 1 (the *name* form).
- `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md` decisions 2 to 4 (a request is a JSON object; the fronts hold no check; a tool is listed with a description and an input schema).
- `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md` whole (168 lines), in particular the F-table rows F8, F11, F14, decision 2 (lines 39-57: the tool definition, "The schema is a statement to the caller, not a check of the frame", "the stated schema admits every request the tool function accepts, and what the function refuses beyond what the schema says is told in the description", `invalid_request`, the reserved kinds) and decision 4 (lines 67-82: the five members `run_id`, `round`, `candidate`, `attempt`, `execution` and their forms).
- `ARCHITECTURE/decisions/ADR-0039-od18-blob-push-fetch-local.md` decision 3 (lines 36-42): the model of a closed request ("a request with any other member" refused as `invalid_request`), its input schema with `"additionalProperties": false`, the reduction rule if Claude Code does not accept a keyword, and "The text of the two descriptions is the code task's".
- `ARCHITECTURE/decisions/ADR-0040-od18-correctness-check-call-identity.md` whole (182 lines), in particular decisions 4 and 5 (lines 62-79), decision 7 (the order of a call, ①) and Boundaries (from line 163).
- `ARCHITECTURE/decisions/ADR-0021-od18-correctness-check-split.md` decisions 1 to 4 (what stays out of a request: a seed, a tolerance).
- What gave the other inputs a source outside the request, read as far as it bears on the request: `ADR-0041-*` decisions 2 to 5 and its paragraph "The member list of a request stays open" (line 89); `ADR-0046-*` decision 6 and the Walk-through row "the request with a member `draws` added" (line 166); `ADR-0056-*` decision 3 (the output path); `ADR-0060-*` decision 3 (settings as the backend's own) and its Boundaries (line 170).
- `ARCHITECTURE/decisions/ADR-0048-od18-correctness-check-seed-draw.md` decision 10 (the order of a call as it now stands).
- `ARCHITECTURE/decisions/ADR-0062-od18-run-tools-call-identity.md` decision 4 last paragraphs (lines 66-72: a `point` in a run-tools request "states nothing; whether such a request is refused is what the tool function does with a member no record names") — read only so the record says nothing about the run tools' requests.
- `ARCHITECTURE/Requirements.md`: the OD register row OD-18 (line 107).
- `ARCHITECTURE/OpenDecisionProposals.md`: the OD-18 section (from line 281): the adopted-part bullets for ADR-0015, ADR-0039, ADR-0040 and ADR-0060; the registered sub-questions ⑤ (line 319, what checks that the stated schema matches the function's check, and what Claude Code does with `inputSchema` — unverified), ⑱ (line 330, part (가): whether settings written in run files reach the operation, among them "members a later record gives the request") and the last registered number (⑳ at line 332 at planning time; check on the day).
- `ARCHITECTURE/StandardScenarios.md`: §검사 규칙 (lines 13-29) and §검사 결과 from line 168 (its heading and its latest 2026-10-16 passages).
- Code, read only as observations (this record binds no code): `hilclaw/tools.py` (`ToolDefinition`, `Registry.register`, the description and schema checks), `hilclaw/mcp_front.py` (how `inputSchema` is listed), `hilclaw/blob_tools.py` (`_input_schema`, `_checked`), `hilclaw/journaled_tool.py` and `hilclaw/hw_tool.py` (the frame check of the five members), `hilclaw/check_identity.py` (the check of `point`), `hilclaw/check_tool.py` (module docstring: "What the module does not do").
- Before you edit `ARCHITECTURE/`, run `gh pr list` and read issues #4, #5, #7 and #8 (the CLAUDE.md 세션 진입 점검). If an open PR touches the same tables or sections, stop and return BLOCKED. Note that the unlanded branch of T-0210 also appends to the OD-18 row, the OD-18 section and §검사 결과; that is not an open PR and does not block this task — append after the ADR-0067 entries as they stand on `main`, and leave reconciling to whichever of the two lands second.

## Acceptance Criteria

1. A new record `ARCHITECTURE/decisions/ADR-0069-od18-correctness-check-request-schema.md` exists in the ADR-0001 record format: Status, Context, Decision with numbered decisions, a Walk-through, Limits, Alternatives considered, Consequences, Boundaries, References. Before the push confirm that ADR-0069 is still free on origin/main and that no branch other than T-0210's holds it; if it is taken, take the next free number above it and update every reference. Keep the record at about 200 lines or fewer so the task stays within the 300-LOC cap.
2. Scope: a request of `correctness.check` about one attempt of a run (ADR-0040 decision 5), one contract. It answers, as far as stated below, the item left by ADR-0040 decision 5 and repeated in ADR-0041, ADR-0042, ADR-0046, ADR-0047 and ADR-0060: the rest of the request, what is done with a member no record names, the input schema and the description. Each point is weighed against at least one alternative and marked as the record's own design where it is:
   - (a) **The member list.** Whether the list of a request is now closed at the six members of ADR-0040 decision 5 (`run_id`, `round`, `candidate`, `attempt`, `execution`, `point`). For each input ADR-0040 decision 5 named (`draws`, the dimensions, the kernel of the attempt, flags, time limits), cite the record that gave it a source outside the request; keep the seed and the tolerance out as ADR-0021 decisions 3 and 4 do. Say how the closing relates to OD-18 sub-question ⑱ (가) without answering it: a later record that gives the request a member extends the list (and the schema) as a change of the contract, as ADR-0060 decision 3 says a later record "reopens" it for settings.
   - (b) **A member no record names.** Weigh at least: refusal as `invalid_request` (the choice of ADR-0039 decision 3 for the blob tools), ignoring it, and passing it on to the operation. Say what a request with a `draws`, a `seed`, a `tolerance` or a dimension member gets, and at which moment of the order of a call (① of ADR-0040 decision 7 as ADR-0048 decision 10 now has it: before the data root is asked and before anything is read, drawn or appended), with the message rule (what the message may name; that it shows nothing of a given value).
   - (c) **The input schema.** The JSON Schema the tool definition states (ADR-0015 decision 2: a statement to the caller, not a check; it "admits every request the tool function accepts"). Give it in full, as ADR-0039 decision 3 did, for the forms of ADR-0015 decision 4 and ADR-0040 decisions 4 and 5 (a `run_id` *name*, the three envelope numbers with `round` ≥ 0, `execution` ≥ 1, `point` one of `"sim"` / `"board"`). Say which constraints of the function the schema cannot state (for example the *name* form of `run_id` if no pattern is used, an integer that is a JSON number with a fraction) and that the description tells them. Take over the reduction rule of ADR-0039 decision 3 for a keyword Claude Code does not accept, and leave sub-question ⑤ open (do not claim what Claude Code does with `inputSchema`).
   - (d) **The description.** What the description must at least tell the caller (that the tool checks one attempt's kernel at the stated point; that the call is journaled and a repeated identity gets the stored outcome; what the function refuses beyond the schema), and that its text is the code task's, as ADR-0039 decision 3 left it.
   - (e) A Walk-through table in the manner of ADR-0040 (a valid request; a request with an extra member such as `draws`, `seed` or `tolerance`; a request with a misspelled member such as `Point`; a request valid by the schema but refused by the function).
   - Do the name check of ADR-0041 decision 4 / ADR-0060 decision 4 for any new name (a *name* of ADR-0001; grep `hilclaw/`, `tests/` and `ARCHITECTURE/` on the day); the expected outcome is that no new kind, member or `step` value is introduced at all.
3. **Not decided, said openly**: the requests of `sim.run` / `board.run` (their member list, schema and description stay open; a `point` in them included, ADR-0062 decision 4); `blob.push` / `blob.fetch` (unchanged); sub-question ⑤ (what checks that schema and function agree, and what Claude Code does with `inputSchema`); ⑱ (가) to (마); the registration of `correctness.check` and the binding of a backend, a source of seeds and a predicate; the spend (OD-2, OD-19); ⑭; `profiler.collect`; what anybody does after any answer (FR-1, OD-10, OD-17, PLAN P2-1); #5 A-4, B-2, B-3, B-7. Do not invent an owner decision.
4. **No data-plane schema change.** Do not add, remove or change a member of a result, a line of `events.ndjson`, `instance.json`, `STATE.json`, a spec, `build.json` or a result file. A request is not a file of the data plane; state the A-13 reading in Consequences as ADR-0039 and ADR-0040 did. If the design you judge right needs a new request member, a new member of any file, or a new reserved kind, stop and return BLOCKED with the question; do not write it.
5. Cite earlier records only as they say things; mark every sentence of the record's own as its own (the "cited" versus "this record's own" convention of ADR-0040 onward). No earlier record is edited. Consequences lists the earlier sentences that become less exact, at least: ADR-0040 decision 5 ("The member list of a request is not closed by this record ...") and its Boundaries; the "member list ... stays open" paragraphs of ADR-0041 and ADR-0046 and the ADR-0046 Walk-through row with `draws` added; the "rest of the request" items in the Consequences / Boundaries of ADR-0042, ADR-0046, ADR-0047 and ADR-0060; and, as observations, the docstring of `hilclaw/check_tool.py` ("it has no input schema and no description, looks at no member but `point` and the four ..., and hands the request on as the caller gave it").
6. Consequences names the code slice this record makes possible (the refusal of an unnamed member and the input schema and description of `correctness.check`, with its tests; whether in `hilclaw/check_identity.py`, `hilclaw/check_tool.py` or a new module, and the names, are the code task's) and what still stands between that and a registered tool (the binding of a backend, a source of seeds and the predicate; the registration itself).
7. `ARCHITECTURE/Requirements.md`: in the OD-18 row, add a 반영 link to ADR-0069 as earlier ADRs were added; keep the status wording unchanged. Do not change the number of OD rows.
8. `ARCHITECTURE/OpenDecisionProposals.md`: in the OD-18 section, add one adopted-part bullet for ADR-0069 after the ADR-0067 bullet (Korean, as the neighbouring bullets). If the record answers part of a registered sub-question (for example ⑤ is **not** answered; check whether any other is), append a dated note (2026-10-16 or later) to it. Register a new sub-question only if the record needs one (next free number — check the section).
9. `ARCHITECTURE/StandardScenarios.md`: run the coverage re-check under §검사 규칙; append a dated passage to §검사 결과 with the verdict (expected: no verdict change and no gap; report honestly if otherwise) and extend the heading parenthetical with one clause for this record, as previous ADR tasks did.
10. Document checks reported in `## Result`: every relative link in the new and edited text resolves; `git diff --stat origin/main` shows only the files in `touchesFiles`; `git diff --check` is clean; the OD register has the same number of rows before and after.
11. Doc mode (CLAUDE.md A-13): branch `claude/T-0211-od18-correctness-check-request-schema`, reviewer cycle with a fresh-context reviewer, at most 7 rounds, then rebase on origin/main and push to main directly. Commit trailers: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0211`, and the `Co-Authored-By` line. Delete the branch afterwards (local and remote if pushed).
12. After landing, post the owner notice of DRIVER §9 on issue #5 in English: what ADR-0069 decides, the landed commit, the objection window (7 days from the notice). Last line `— posted by driver`. Record the comment URL in `## Result`.
13. Nothing is built or run except read-only git/gh, grep and link checks. No `claude` process, compiler, kernel or container is started (D16).

## Out of Scope

- Any code, including the refusal of unnamed members, the schema and description in code, and the registration of `correctness.check`; changes to `hilclaw/` or `tests/`.
- The requests of `sim.run` / `board.run` and of `blob.push` / `blob.fetch`; the run tools' ⑲ (나) to (라) (T-0210, HQ-0021) and ⑳.
- OD-18 sub-questions ⑤, ⑭ and ⑱; the spend (OD-2, OD-19); `profiler.collect`; a target on another machine (#5 B-2, B-3).
- Editing any earlier ADR; list less-exact sentences in Consequences instead.

## Follow-ups

## Result

- **Outcome**: DONE. Landed on `main` as `bf4a795` (document mode, direct push after rebase onto `origin/main`; trailers `Reviewed-by: reviewer agent (7 rounds, Approve)`, `Task: T-0211`). Branch `claude/T-0211-od18-correctness-check-request-schema` deleted locally and on origin.
- **Review**: 7 rounds with a fresh-context `dev-reviewer` each round; rounds 1-3 and 5-7 Approve with nits (all addressed except the round-7 nit below), round 4 Request changes (A-13 sentence said "a start line holds exactly `step` and `execution`"; fixed to the `data` of a start line).
- **Record**: `ARCHITECTURE/decisions/ADR-0069-od18-correctness-check-request-schema.md` (150 lines). ADR-0069 was free on `origin/main` and on every remote branch at push time (T-0210's branch holds ADR-0068 only). Decisions: (1) scope; (2) the member list is closed at the six members of ADR-0040 decision 5, each named input having a source outside the request (ADR-0041, ADR-0046, ADR-0056 d3, ADR-0060 d3; seed/tolerance ADR-0021); a later member is a contract change; OD-18 (18)(ga) not answered; (3) a member no record names is `invalid_request` in moment 1, before the data root is asked; the message may name refused member names and shows nothing of their values; (4) the full input schema (`run_id` pattern of ADR-0004 d8, integer bounds of ADR-0001, `point` enum, all six required, `additionalProperties: false`), the only function refusal beyond it being numbers written with a fraction or exponent; the reduction rule of ADR-0039 d3 taken over; sub-question (5) open; (5) what the description must at least tell (text is the code task's). No new kind, member or `step` value; no data-plane change.
- **Edited**: `ARCHITECTURE/Requirements.md` (OD-18 row: one sentence with the 반영 link to ADR-0069; status wording unchanged), `ARCHITECTURE/OpenDecisionProposals.md` (one adopted-part bullet after ADR-0067; no sub-question note — none is answered; none registered), `ARCHITECTURE/StandardScenarios.md` (heading clause + "2026-10-16 (2차)" passage: no verdict change, no gap).
- **Document checks**: every relative link in the new and edited text resolves (script over the ADR and the added lines; `#od-18` anchor present); `git diff --stat origin/main` before the push showed only the four `touchesFiles`; `git diff --check` clean; OD register rows 30 before and 30 after. Nothing built or run; no `claude` process started.
- **OD state**: OD-18 stays `제안됨` (a further part closed). Owner notice for #5 (DRIVER §9) to be posted by the driver:

  ```
  ### OD-18 - the member list of a request of correctness.check, what is done with a member no record names, and the tool's input schema and description, fixed by ADR-0069 under DRIVER §9 (T-0211)

  ADR-0069 (commit bf4a795) answers the item ADR-0040 decision 5 left open for `correctness.check`. It is the record's own design; no owner sentence is used.

  - The member list of a request is closed at the six members `run_id`, `round`, `candidate`, `attempt`, `execution`, `point`: every input ADR-0040 decision 5 named now has a source outside the request (dimensions ADR-0041, `draws` ADR-0046, the kernel ADR-0056 decision 3, flags and time limits ADR-0060 decision 3; seed and tolerance ADR-0021). A later record that gives the request a member changes the contract; OD-18 sub-question 18 (ga) is not answered.
  - A request with any other member (`draws`, `seed`, `tolerance`, a dimension, a misspelling such as `Point`) is refused as `invalid_request` in moment 1, before the data root is asked and before anything is read, drawn or appended; the message shows nothing of the refused member's value.
  - The input schema is stated in full (`additionalProperties: false`, the forms of ADR-0004, ADR-0001 and ADR-0040), with the reduction rule of ADR-0039 decision 3; what the description must at least tell is fixed, its text is the code task's. Sub-question 5 stays open.
  - No data-plane file or member changes; no new kind, member or `step` value; no sub-question registered.

  Objection window: 7 days from this notice. An objection creates a task that reverts ADR-0069 and the edits made with it.

  — posted by driver
  ```

## Follow-ups (from the executor)

- Round-7 reviewer nit, not addressed (fixing it would have needed an eighth round): ADR-0069 decision 1 says the terms "ADR-0040 (the moments ① to ⑦, `point`)"; the moments ① to ⑦ are ADR-0016's terms, which ADR-0040 uses. A one-word source correction for the integrator.
- For the code task of ADR-0069 (reviewer note, round 6): the refusal message may echo caller-supplied member names; the code task should decide how it bounds their length and treats control characters.
- Code slice now possible: the refusal of unnamed members in moment 1 and the input schema and description of `correctness.check`, with tests per Walk-through row.
