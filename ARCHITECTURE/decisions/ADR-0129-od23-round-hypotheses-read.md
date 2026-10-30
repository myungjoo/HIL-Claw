# ADR-0129: How the evaluator of a first-case turn reads a round's hypothesis record — a typed registry tool `hypotheses.read`, called through the MCP front with `run_id` and `round`, that returns the whole valid record and reuses the `hypotheses_*` kinds of `verdicts.write` (ADR-0128 Consequences slice 3, first record; part of OD-23 and OD-18, for the runs of ADR-0120 decision 1)

## Status

- **Accepted on 2026-10-20** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it.**
- **Two kinds of content.** What an owner decision, an agreement of #4, a requirement, an accepted record or a code docstring says is **cited**, with its source named. **Everything else is this record's own**: the choice of the means, the tool, its name, members, result and kinds and their order, who gets it, the readings marked as such, and every weighing.
- **The owner-sentence search.** Searched: the body of #4 and its 6 comments; the body of #5 and the 40 of its 211 comments whose text holds no "posted by driver" marker; the bodies and comments of #7 (2) and #8 (6). Terms: hypotheses.json, hypothes, 가설, 판정, verdict, evaluator, 평가자, read tool, 읽기 도구, 읽기 제한, `decision/`. **No owner sentence says how the evaluator, or any agent, reads a round's hypothesis record.** The sentences found that touch the point, each read for what it says and no further:
  - **K2 and K4** as [ADR-0128](ADR-0128-od23-first-case-evaluator.md) Status cites and treats them: the roster row of the evaluator ("MCP correctness.check", "eval.json") and condition 3 of the #4 roster revision (https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5138366881); the two owner premises of https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139876430, "읽기 제한은 채택하지 않는다" and "프롬프트만으로 쓰기 구역을 주는 것은 너무 약하다". Premise 1 binds below: nothing here restricts a read.
  - **K5** — the owner decision of 2026-10-13, point 1 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6136462569): the selection "records a structured hypothesis record"; "evaluate records a verdict and its cause per hypothesis". It names the record and the step, not how the step reads the record. Its addendum (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6136597638) is about forming hypotheses, not reading them.
  - **Research, not owner decisions**: the #4 pointer of 04:25Z (https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139248800, "`evaluator`는 반대로 강화 필요"), #7 §2(8) ("코더의 서술이 아닌 아티팩트 경로+해시만 수신") and the #7 body's "Write 권한 없는 fresh-context 평가자"; weighed by ADR-0128 decision 4 and not reopened here.
- **Answers**, **for the runs of ADR-0120 decision 1 only**, part of **OD-23** (one input of the evaluator: the round's hypotheses, and the means by which it gets them) and part of **OD-18** (how a turn session reaches a run file other than `STATE.json` and `instance.json`, for this one file and this one agent). **The status of OD-23, OD-18 and every other OD is unchanged.** No sub-question is registered or answered.
- **OD-30 is not answered further**: no field, place, vocabulary or rule of the hypothesis record or of the verdicts is added or changed; how a record already defined is read by one agent is the input contract of OD-23 and the tool reach of OD-18.
- **No member, file, kind, value or version of the data plane is added or changed**, and no validator changes. **It is a record, not code**: no `claude` process was started for it, and nothing below was tried in a live session (D16).
- It builds on [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decisions 3, 4, 6), [ADR-0015](ADR-0015-od18-tool-contract-frame.md) (decisions 2 to 4, 7), [ADR-0059](ADR-0059-od30-round-hypothesis-record.md) (decisions 1, 2, 5), [ADR-0073](ADR-0073-od30-case-lookup-and-case-basis.md) (decisions 2, 3), [ADR-0118](ADR-0118-od18-round-process-boundary.md) (decision 6), [ADR-0123](ADR-0123-od18-turn-session-run-identity.md) (decisions 2, 4), [ADR-0124](ADR-0124-od23-round-manager-run-file-access.md) (decisions 2, 3) and [ADR-0128](ADR-0128-od23-first-case-evaluator.md) (decisions 2 to 7). **If one of them is reverted, this record is revisited with it.**
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **The open point** (cited): what a record of the evaluator's role rests on "it gets through typed tools of the registry that take the `run_id`: an outcome, a standing, a comparison, the round's hypotheses" (ADR-0128 decision 4); the read of a round's `hypotheses.json` is the first of the slice-3 tools, each "after a record" (ADR-0128 Consequences slice 3). Until then the evaluator definition answers a verdicts delegation with one line saying the verdicts "cannot yet be written because no tool reads the round's hypotheses and results" (`orchestration/agents/evaluator.md`, "Verdicts").
- **What exists** (code, as observation): `hilclaw.hypotheses_file.parse` turns the bytes of a version-1 record into its document or raises `InvalidHypothesisFileError` or `UnsupportedVersionError`, and `final_name` gives the path its `run_id` and `round` format to; the module "reads no other version (OD-11) and is no tool". `hilclaw.verdicts_tool._hypotheses` already reads the round's record for `verdicts.write`: a place holding no regular file, a missing file, a failing read and the two parse refusals become `hypotheses_invalid`, `hypotheses_missing`, `hypotheses_unreadable`, `hypotheses_invalid` and `hypotheses_unsupported`. `hilclaw.run_file_tools` gives the Round-Manager `state.read` and `instance.read`, which return `{"state": …}` or `{"instance": …}`, members as stored. `default_registry` holds `blob.fetch`, `blob.push`, `correctness.check`, `state.read`, `instance.read`, `run.fresh`, `state.write`, `run.commit` and `verdicts.write`.
- **Constraints the means must keep** (cited): agents call tools through the MCP front (ADR-0010 decision 3); the data root is never a member of a request (ADR-0015 decision 3); the evaluator's prompt and delegation name the run id and no place (ADR-0123 decision 2; ADR-0128 decision 4); no read is restricted (K4 premise 1); the evaluator holds no file-writing means and no shell (ADR-0128 decision 3); a round-0 file is invalid and round 0 has no hypothesis record (ADR-0059 decision 5); a file whose `run_id` or `round` is not that of its path is no record of either (ADR-0059 decision 2).

## Decision

A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope

- **The read of `rounds/<RRRR>/decision/hypotheses.json` of the evaluator's run**, by the `evaluator` sub-agent of a turn of a run of ADR-0120 decision 1, for the verdicts work of ADR-0128 decision 1.
- **Outside**: every other file and every other reader; the writer of the file; the journaled results of an attempt, the standing and the comparison (ADR-0128 Consequences slice 3); everything under Boundaries.

### 2. (a) The means: a typed registry tool through the MCP front

- **The evaluator gets a round's hypothesis record by calling one tool of the registry, `hypotheses.read`, through the package's MCP front**, naming its run by `run_id` and the round by `round` in the request. The record it composes for `verdicts.write` rests on what this tool returns (ADR-0128 decision 4).
- **It is given no place for this.** The tool takes the `run_id` its delegation already names, so ADR-0123 decision 2 and ADR-0128 decision 4 stand unchanged.
- **What the rule is and is not.** It names the ground a verdicts record rests on. It restricts no read (K4 premise 1): anything else the evaluator reads with `Read`, `Grep` or `Glob` is not restricted, but a record does not rest on it.

### 3. (b) The tool

| Part | Content |
|---|---|
| Name (MCP name) | `hypotheses.read` (`mcp__hilclaw__hypotheses_read`); the name holds no `_`, so the mapping of ADR-0010 decision 4 stays reversible |
| Request | Exactly `run_id` (ADR-0015 decision 4) and `round`, an *integer* of ADR-0001 decision 1 (at most 2^53 - 1) that is at least 1, with the meaning ADR-0015 decision 4 gives it; both required; any other member, or one missing, is refused |
| Result | `{"record": …}`: the document of the file as one JSON object, its members as stored, unknown top-level members included |
| Checks, in order | the request, `round` 0 among its refusals (`invalid_request`, ADR-0015 decision 2); the data root (`no_data_root`); the read and parse of the round's `decision/hypotheses.json` as `verdicts.write` reads it (ADR-0128 decision 6): a place holding no regular file (`hypotheses_invalid`), no file there (`hypotheses_missing`), a read that fails otherwise (`hypotheses_unreadable`), bytes `hypotheses_file.parse` refuses (`hypotheses_invalid`) or another `schema_version` (`hypotheses_unsupported`); the document's `run_id` and `round` against the request's (`hypotheses_invalid`) |

- **Round 0 is a refused request**, before the data root is asked: round 0 has no hypothesis record and a file whose `round` is 0 is invalid (cited: ADR-0059 decision 5), so no answer but a failure exists for it. A `round` above the run's stored `round` is not refused: the tool reads no `STATE.json`, as `verdicts.write` reads none.
- **The kinds reuse those of `verdicts.write`** (ADR-0128 decision 6), with the same meanings for the same file: a reader of either tool's failure tells the same situations of the same file by the same names, except a file naming another run or round, which `verdicts.write` refuses as `verdicts_mismatch` (below). They stay names of the tool layer, **not a change of the data plane**; none is reserved. `verdicts.write` is not changed.
- **The last check is this tool's own**: ADR-0059 decision 2 makes a file valid only when its `run_id` and `round` are those of its path, and `parse` reads no path. In `verdicts.write` the same file is refused by the rule "`run_id`, then `round`, are the same in both documents" of `verdicts_hypotheses.check`, as `verdicts_mismatch`; both tools refuse it, under different kinds, and neither is changed for that.
- **The whole valid document, not a part.** The verdicts work uses the `id`, `tested_by` and `expected` of every entry (`verdicts_hypotheses.check`) and, for a `cause` (FR-17), may rest on its `statement` and `basis`; choosing a part would make the tool decide what the judgement needs, which is the evaluator's (ADR-0128 decision 2). The whole document also carries members later records add at the open top level (cited: ADR-0059 decision 2; for instance `cases_read`, ADR-0073 decision 3) without a change of the tool. The result member is named `record` because the document has its own member `hypotheses`, and because `verdicts.write` names the whole content of its file `record`.
- **Not journaled**: a read costs no limited resource and can be repeated (the reasoning of ADR-0124 decision 3 for `state.read` and `instance.read`). It appends no line and selects no backend. It is a tool of the registry beside the FR-10 tools, not an FR-10 tool, read as ADR-0124 decision 3 reads its four.
- **Nothing is created** by any call, and nothing is kept between calls. The fixed tool set grows by this tool in the source (`default_registry`) and in no other way (cited: #5 A-12 point 3; `hilclaw/tools.py`); it is reachable through the command-line front too (ADR-0010 decision 3).
- **Left to the code slice**: the module, the description and input schema, whether the read shares code with `verdicts_tool._hypotheses`, and what a number beyond the float range in a top-level member no record defines does to the result (for `state.read` it is `bad_result`).

### 4. (c) Who may use it

- **The evaluator: `mcp__hilclaw__hypotheses_read` is added to its `tools` list** (ADR-0128 decision 3: later tools are added "by the records or slices that create them"). It is a read and gives the evaluator no file-writing means and no shell.
- **The Round-Manager is not given it here.** Whether it reads the hypotheses — for instance before it delegates verdicts — belongs to the round steps (P2-1) and the rest of OD-23 (Boundaries). The selection side and every other member of the roster are outside this record.

### 5. (d) What the evaluator then has, and what it still lacks

- **It then has**, for a verdicts delegation, the round's hypotheses as the file holds them: which hypotheses need a verdict, which candidates test each, and which direction each expects (ADR-0059 decisions 3, 4).
- **It still lacks the ground of every evidence entry**: the outcome of an attempt's checks needs a read of an attempt's journaled results, and the standing and the comparison need their own tools (ADR-0128 Consequences slice 3). A verdicts delegation names no tuple, so the evaluator may not request a check for it (ADR-0128 decision 7), and an outcome it took from the log by `Read` would be a record resting on no typed tool (ADR-0128 decision 4).
- **So the one-line "cannot yet" report of the definition stays** until the journaled-results read exists; its reason narrows to the missing results read. The evaluator need not call `hypotheses.read` on such a delegation. Whether the results read alone is enough for the verdicts work to be given — every verdict `inconclusive` until the comparison exists (ADR-0128 decision 6; its Consequences, "The cost, plainly") — is that read's record.

### Walk-through

| Situation | What follows |
|---|---|
| Round 2 reaches evaluate, after the results read exists | The evaluator calls `hypotheses.read` with `run_id` and `round` 2, gets the record, reads the results of the attempts in `tested_by`, composes the verdicts and calls `verdicts.write` |
| After slice 2 and before the results read exists, a verdicts delegation for round 2 | The evaluator reports in one line that the verdicts cannot yet be written because no tool reads the attempts' results, and ends (decision 5) |
| A request with `round` 0 | `invalid_request`; the data root is not asked (ADR-0059 decision 5) |
| The round has no `hypotheses.json` | `hypotheses_missing`; what follows is the round steps' (ADR-0059 decision 2: a missing file means that the tree holds no record for that round, and nothing more) |
| The file is invalid, holds another `schema_version`, or names another round | `hypotheses_invalid`, `hypotheses_unsupported` or `hypotheses_invalid`; nothing of it is returned or repaired |
| The evaluator names another run's id | The tool serves that run; nothing stops it (cited: ADR-0123 decision 4; ADR-0015 decision 7). A later hook could see the `run_id` (ADR-0010 decision 6) |

## Alternatives considered

| Point | Alternative | Weighing | Outcome |
|---|---|---|---|
| (a) | **A typed registry tool through the MCP front, `run_id` and `round` in the request** | ADR-0128 decision 4 met; no place; the file's validity is judged by `parse`, not by the model; a hook can see the call and an allowlist can name it (ADR-0010 decision 6) | **Adopted** |
| (a) | The evaluator reads the file with `Read` at a path it finds | It is given no place (ADR-0123 decision 2) and would have to find the data checkout; the record would rest on no typed tool (ADR-0128 decision 4); a damaged or misplaced file would be judged by the model | Rejected |
| (a) | The Round-Manager puts the content in the delegation | Another agent's account (ADR-0128 decision 4): the Round-Manager would need its own read and would copy a file it did not validate into a message, a copying risk of the kind ADR-0124 names as its cost (the model copies values) | Rejected |
| (a) | `verdicts.write` returns the hypotheses, or gains a mode that only reads | The read is needed before the record is composed; one tool with two effects is harder to allow per agent, and the write's contract would change | Rejected |
| (a) | One generic read tool for any run file, by a relative path | The caller would name a place; each file has its own validator and kinds, which a path-keyed tool would have to choose by name; an allowlist could not tell one file from another | Rejected |
| (b) | **The whole valid document** | Decision 3 | **Adopted** |
| (b) | Only `id`, `tested_by` and `expected` of each entry | The tool would decide what the judgement needs; a `cause` may rest on `statement` and `basis`; later top-level members would need a change of the tool | Rejected |
| (b) | The bytes as a string | The model would parse JSON text the tool already parsed | Rejected |
| (b) | New kinds of its own, or the reserved `run_file_*` kinds | The same situations of the same file would get two names; `run_file_*` mean the read of a frame file (ADR-0019; ADR-0124 decision 3), which this is not | Rejected |
| (b) | Round 0 answered `hypotheses_missing` | No round-0 record can exist (ADR-0059 decision 5); a request that cannot succeed is a refused request (ADR-0015 decision 2), and refusing it asks no data root | Rejected |
| (c) | The Round-Manager gets the tool too | Its round steps are not written (P2-1); nothing of its work needs the read yet | Left open |
| — | Leave it open | The verdicts work of P2-3 and P2-6, and so rounds 1 to 4 of P2-5, would wait on one more open point | Rejected |

## Consequences

- **Slices it enables** (code mode, later tasks; each tested with a stub `claude` only, or none — D16):
  1. **Now**: the tool `hypotheses.read` of decision 3, in a module of `hilclaw/` with its test file (happy path, every kind in its order, round 0, a file naming another round, the result's members as stored); registered in `default_registry` of `hilclaw/tools.py`, with its docstring.
  2. **Now, with or after slice 1**: `mcp__hilclaw__hypotheses_read` added to the `tools` list of `orchestration/agents/evaluator.md` and to that file's test of the `tools` set; the "Verdicts" paragraph's reason narrowed to the missing results read (decision 5).
  3. **After a record each** (unchanged from ADR-0128 Consequences slice 3): a read of an attempt's journaled results; the standing of ADR-0110 as a tool; the comparison of ADR-0007 decision 7.
- **Less exact, not edited** (found by a search of `ARCHITECTURE/decisions/`, `hilclaw/` and `orchestration/` for "hypotheses.json" near "read" or "tool", "slice 3", "the contracts of the read", "no tool yet reads"; not claimed complete):
  - ADR-0128 Context ("What exists": the registry's list), decision 3 ("From what `default_registry` registers today"), Consequences slice 3 ("After a record each: a read of a round's `hypotheses.json`") and Boundaries ("the contracts of the read, standing and comparison tools"): the first read is now decided.
  - ADR-0124 decision 1 ("Outside: sub-agents …; hypotheses, verdicts") and Boundaries ("The roster: sub-agents, their access to the run's files"), for the evaluator and this file.
  - `orchestration/agents/evaluator.md` "Verdicts" ("no tool yet reads a round's `hypotheses.json`") and `hilclaw/tools.py` `default_registry` docstring (the list of the set): slices 2 and 1.
- **UsageCases and StandardScenarios**: no sentence becomes false.
- **A-13 reading.** Document mode. No code, test, setting or dependency changes. **No data-plane change**: no member, file, kind, value or version of `hypotheses.json` or any other data-plane file is added or changed, and no validator changes; the kinds of decision 3 are tool failure kinds, reused from `verdicts.write`.
- **Runtime acceptance items** (D16; nothing was tried, nothing is required of the development machine). ADR-0128 item (xviii) is used, not changed; item (xxi) below is the counterpart of ADR-0124 item (xi) for this tool. **New**, numbered in the turn-session series of ADR-0118 (i) to (vii), ADR-0122 (viii), ADR-0123 (ix), ADR-0124 (x), (xi), ADR-0126 (xii) to (xiv), ADR-0127 (xv) to (xvii) and ADR-0128 (xviii) to (xx):
  - **(xxi)** The result of `hypotheses.read` reaches the evaluator whole, within the limit Claude Code puts on the output of an MCP tool, for the largest hypothesis record a first-case round can hold. No record bounds that size; if the limit cuts the result, a bound or a paged read is a later record's.
- **The cost, plainly.** One more tool in the fixed set and its contract to keep. Nothing of the verdicts work can be done until the results read exists, so this record alone changes no behaviour of a turn. Two tools now name the same file's failures, and a change of one's kinds must be weighed against the other.

## Boundaries (not decided here)

- **Owner-only**: the evaluator's model and whether its tokens count against a budget (#5 A-8, HQ-0041, NFR-5); C-6, OD-25, OD-3. Whether any agent has a shell (HQ-0040) is untouched.
- **The selection side** (rest of OD-23; P2-6): who writes `hypotheses.json` in a turn, when, and how its presence is enforced (ADR-0059 Boundaries); **whether injected hypotheses must be tested** (HQ-0031).
- **The rest of slice 3** (ADR-0128 Consequences): the read of an attempt's journaled results and whether it suffices to give the verdicts work; the standing and comparison tools; the fields of `eval.json` (OD-20).
- **The Round-Manager's use of the tool** and every other roster member's (P2-1; rest of OD-23).
- **Permissions, allowlists beyond the `tools` list, and hooks** of a turn session (rest of OD-18; PLAN P2-4), a check of a request's `run_id` against the session's run among them.
- **A bound on the size of a hypothesis record**, or a paged read (item (xxi)).
- **Runs outside ADR-0120 decision 1**; any edit of an earlier record, of FR or NFR text, UsageCases, `hilclaw/`, `orchestration/`, tests, CI, `.claude/`, any settings file or the `HIL-Claw-data` repository; any new external dependency.

## References

- [Requirements](../Requirements.md): FR-9, FR-11, FR-17, NFR-4; register rows OD-16, OD-18, OD-23, OD-30. [OpenDecisionProposals](../OpenDecisionProposals.md) [OD-23](../OpenDecisionProposals.md#od-23), [OD-18](../OpenDecisionProposals.md#od-18). [StandardScenarios](../StandardScenarios.md) S0, S1.
- ADR-0001 (record format); ADR-0010 (decisions 3, 4, 6); ADR-0015 (decisions 2 to 4, 7); [ADR-0019](ADR-0019-od18-unusable-run-kind.md); ADR-0059 (decisions 1 to 5; Boundaries); [ADR-0071](ADR-0071-od30-hypothesis-verdict-record.md); ADR-0073 (decisions 2, 3); ADR-0118 (decision 6); ADR-0123 (decisions 2, 4); ADR-0124 (decisions 1 to 3; item (xi), as a counterpart); ADR-0128 (decisions 2 to 7; Consequences; item (xviii)).
- #4 roster revision https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5138366881 ; https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139876430 ; #5 owner decision of 2026-10-13 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6136462569 and addendum https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6136597638 · A-12 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5946779596 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 ; #7 §2(8).
- Code, as observation only: `hilclaw/hypotheses_file.py`, `hilclaw/verdicts_tool.py`, `hilclaw/verdicts_hypotheses.py`, `hilclaw/run_file_tools.py`, `hilclaw/tools.py`, `hilclaw/layout.py`, `orchestration/agents/evaluator.md`.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P2-1, P2-3, P2-4, P2-5, P2-6; CLAUDE.md "개발 드라이버와 런타임의 구분"; task T-0355.
