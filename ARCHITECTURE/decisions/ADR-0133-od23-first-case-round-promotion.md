# ADR-0133: The case write of a first-case round's promotion step — the Round-Manager holds it inline and calls one new registry tool, `case.write`, which builds the round's case from its two files and stores it in the run's stored key directory, as the last write of the round before the write that ends it; a round with a valid hypothesis record is promoted with or without a verdicts file, and a refusal leaves the round without a case and does not stop its end (part of OD-23 and OD-30, for the runs of ADR-0120 decision 1)

## Status

- **Accepted on 2026-10-20** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it.**
- **Two kinds of content.** What an owner decision, an agreement of #4, a requirement, an accepted record or a code docstring says is **cited**, with its source named. **Everything else is this record's own**: the scope, the holder, the tool `case.write` with its members, result, checks and kinds, which rounds get a case, the order, the readings marked as such, and every weighing.
- **The owner-sentence search.** Searched: the body of #4 and its 6 comments; the body of #5 and the 40 of its 217 comments whose text holds no "posted by driver" marker; the bodies and comments of #7 (2) and #8 (6). Terms: promoter, promot, 승격. The sentences found that touch the point, each read for what it says and no further:
  - **P1** — #4 §3a revision (https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5138366881), the roster row "promoter | 크로스런 승격 | db/ Write | best.json, technique_stats.json", its §6 item "promoter를 독립 agent로 둘지 매니저 인라인으로 할지" (open), and condition 4, "판단·소화가 불필요한 결정론적 단계는 subagent화하지 않음". ADR-0128 treats the roster row and conditions 2 to 4 as binding (its K2); **this record does the same**, and reads the row's "db/ Write" as naming the role's directory, not a means (K4 below).
  - **P2** — #4 body §3c (the agreed sketch): "promote distilled → db/<hw>/<op>/ (best, technique_stats)" stands before "STATE.json 갱신 … → commit" (ADR-0127's C3).
  - **P3** — #5 A-1 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5046307826): "매 라운드 `runs/`→`db/` 승격 커밋(#4 §3c)이 원자적 커밋 1개가 됨" (ADR-0127's C4).
  - **K4** — the owner premise "프롬프트만으로 쓰기 구역을 주는 것은 너무 약하다" (https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139876430), as ADR-0124 and ADR-0128 cite it.
  - **Research, not owner decisions**: the #4 pointer of 04:25Z (https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139248800) and #7 §2(8): "`technique-selector`·`promoter`는 인라인 후보" (a sub-agent pays a fresh context each round). Weighed below; neither binds. Also found and not bearing on the actor: the promotion PR policy and the "실패 포함 통계" unit of the shared layer (#4 comments 5138931194, 5139050963; OD-25), the sim→board promotion (OD-15, OD-29), FR-9's promotion-gate re-verification.
- **Answers**, **for the runs of ADR-0120 decision 1 only**, part of **OD-23** (whether the case write of the `promoter` role is a sub-agent's or inline, and its means; not the writer of `best.json` or `technique_stats.json`) and part of **OD-30** (which agent or tool writes a case, which rounds get one, the order of that write against the write that ends the round — ADR-0072 Boundaries "Promotion", ADR-0127 decision 4). **The status of OD-23, OD-30 and every other OD is unchanged.** No sub-question is registered. Nothing here needs #5 A or B items, C-6, OD-25 or OD-3, and HQ-0031, HQ-0040, HQ-0041 and HQ-0043 are not answered.
- **No member, file, kind of event, value or version of the data plane is added or changed**, and no validator changes. **It is a record, not code**: no `claude` process was started for it, and nothing below was tried in a live session (D16).
- It builds on [ADR-0001](ADR-0001-od4-key-schema.md) (decisions 1, 4), [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decisions 4, 5), [ADR-0012](ADR-0012-od8-runtime-state-file.md) (decisions 3, 6), [ADR-0015](ADR-0015-od18-tool-contract-frame.md) (decisions 2 to 4), [ADR-0019](ADR-0019-od18-unusable-run-kind.md) (decisions 2, 3), [ADR-0059](ADR-0059-od30-round-hypothesis-record.md) (decisions 1, 5), [ADR-0071](ADR-0071-od30-hypothesis-verdict-record.md) (decisions 1, 2, 6), [ADR-0072](ADR-0072-od30-hypothesis-outcome-case-file.md) (decisions 1 to 3), [ADR-0073](ADR-0073-od30-case-lookup-and-case-basis.md) (decision 1), [ADR-0118](ADR-0118-od18-round-process-boundary.md) (decisions 2, 6), [ADR-0120](ADR-0120-od8-first-state-file.md) (decision 1), [ADR-0124](ADR-0124-od23-round-manager-run-file-access.md) (decisions 2, 3), [ADR-0127](ADR-0127-od8-commit-step.md) (decisions 3 to 5, 8), [ADR-0128](ADR-0128-od23-first-case-evaluator.md) (decisions 2, 6) and [ADR-0131](ADR-0131-od23-attempt-check-results-read.md) (decision 6). **If one of them is reverted, this record is revisited with it.**
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of ADR-0001.

## Context

- **The open points** (cited): "The writer role is the promotion step … Which agent or tool holds that step is OD-23" (ADR-0072 decision 1); its Boundaries "Promotion" holds open when and whether every round is promoted, a round without verdicts, a second case write after the name was taken, a round whose pair breaks ADR-0071 or whose `verdicts.json` is invalid, and a round ≥ 1 with no hypothesis record. ADR-0127 decision 4: "a case file is taken only if it exists when the commit of its round is made … So the promotion step writes it before the round's commit is made … the order itself is OD-23's".
- **What exists** (code, as observation only): `hilclaw.cases.build(hypotheses, verdicts=None)` forms a valid case or raises; `hilclaw.cases_file.write(data_root, hw_profile_key, op_signature, content)` stores it once, creates no directory (`FileNotFoundError` or `NotADirectoryError` for a missing key directory), raises `NameTakenError` for a taken name and an `OSError` for a failed step; nothing calls either. `hilclaw.key_records.lookup` answers ADR-0001 decision 4's exact match from the two key record files, and `store_hw_profile` and `store_op_signature` have no caller in `hilclaw/`. `hilclaw.run_commit.commit` takes in the existing case files of the rounds *H* to *W* − 1. `hilclaw.hypotheses_tool.read` is the read of `hypotheses.read` and `verdicts.write`. `orchestration/round-manager.md` defines the entry of a turn and says the round steps are not yet defined.

## Decision

A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope

- **The promotion of a round ≥ 1 of a run of ADR-0120 decision 1**: the write of that round's case (ADR-0072) in a turn that ends with its round (ADR-0118 decision 2 (i)). Round 0 has no case (cited: ADR-0072 decision 3) and no promotion step.
- **Outside**: `best.json`, `technique_stats.json` and every other file a promotion may write (OD-20, OD-7); the key directory's creation (OD-26); the selection side and the lookup (ADR-0073; the unlanded ADR-0132); everything under Boundaries.

### 2. (a) The holder: the Round-Manager, inline

- **The Round-Manager holds the promotion step, as decision 1 scopes it, itself and calls `case.write` (decision 3) through the package's MCP front**, naming its run by `run_id` and the round by `round`. No sub-agent, neither the turn loop nor the start function writes a case for these runs, and the Round-Manager writes one by no other means, Bash and its own file tools included.
- **Why inline.** Given the round's two files and the run's `instance.json`, the case is determinate (cited: ADR-0072 Consequences, "decision 3 makes it determinate"), so the step needs no judgement: one tool call with `run_id` and `round`. A sub-agent would pay a fresh context each round for that call (the research note above), and P1 condition 4 says such a step is not made a sub-agent. Unlike the evaluator (ADR-0128 decision 2), there is no `cause` to judge. The Round-Manager already holds the round's last writes and its commit (cited: W1 of ADR-0120; ADR-0127 decision 2).
- **P1's roster row, as read here**: for these runs the Round-Manager holds the case write of the `promoter` role, and "db/ Write" is met for it by a writing tool, not by a `Write` permission (K4; ADR-0124 decision 2). The row's own outputs, `best.json` and `technique_stats.json`, are not answered: who writes them, and whether it is the same holder, stays open with their content (OD-20, OD-7).

### 3. (b) What writes the case: the tool `case.write`

| Part | Content |
|---|---|
| Name (MCP name) | `case.write` (`mcp__hilclaw__case_write`); no `_` in the name, so the mapping of ADR-0010 decision 4 stays reversible |
| Request | Exactly `run_id` and `round`, both required, with the meaning and form of ADR-0015 decision 4; `round` from 1 to 2^53 − 1. Any other member, one missing, or `round` 0 is `invalid_request` |
| Result | `{"with_verdicts": true or false}`: whether the stored case holds `verdict_record` |
| Checks, in order | ① the request (`invalid_request`, ADR-0015 decision 2); ② the data root (`no_data_root`); ③ the run's `STATE.json` read and parsed (`run_file_missing`, `run_file_invalid`, `run_file_unsupported`, `run_file_unreadable`), and its `round` equal to the request's (`round_not_current`); ④ the run's `instance.json` read and parsed (the same four kinds); ⑤ the key: `instance.json` states an `op_signature` and `key_records.lookup` of its two records hits (`key_not_stored` for no `op_signature` or a miss, `key_record_invalid` for a collision or an invalid stored record, `key_record_unreadable` for any other failing read, a data root gone since ② among them); ⑥ the round's `decision/hypotheses.json` by `hypotheses_tool.read`, and its `run_id` and `round` against the request's (`hypotheses_missing`, `hypotheses_invalid` — a `run_id` or `round` other than the request's among it, as in `hypotheses.read` —, `hypotheses_unsupported`, `hypotheses_unreadable`); ⑦ the round's `eval/verdicts.json`: not there is no failure; otherwise read, parsed by `verdicts_file.parse` and its `run_id` and `round` against the request's (`verdicts_invalid` for an invalid file, a place holding no regular file or a `run_id` or `round` other than the request's, `verdicts_unsupported` for another version, `verdicts_unreadable` for any other failing read); ⑧ `cases.build`, the rules of ADR-0071 between the pair (`verdicts_mismatch`); ⑨ the write by `cases_file.write` into the key directory of ⑤ (`case_exists` for a taken name, `case_not_written` for any other failure of the file system, a key directory gone since ⑤ among them) |

- **Every check before ⑨ creates nothing.** The tool reads `STATE.json`, `instance.json`, the two key record files and the round's two files; `cases_file.write` still reads no file (cited: ADR-0072 decision 1). **Reading is the tool's step, not the write's**, as ADR-0128 decision 6 has it for `verdicts.write`.
- **③ holds the order of decision 5 by the tool, not by a prompt** (K4): `STATE.json`'s `round` is the round in progress (cited: ADR-0012 decision 3), so a call after the write that ends the round is refused.
- **⑤ writes a case only where the lookup finds it.** ADR-0073 decision 1 reads no case below a key whose record file is missing (cited); a case written into a bare key directory (the limit of ADR-0072 decision 1) would never be read. A missing key directory is a miss, so `key_not_stored` is the answer ADR-0072 decision 1 asks for: nothing is created.
- **Kinds.** Reused with their meanings: `invalid_request`, `no_data_root`; the four `run_file_*` kinds of ADR-0019 decision 3 for `STATE.json` and `instance.json` — **this record widens ADR-0019 decision 2's "only at the lookup or the selection" to these two reads of `case.write`**, as ADR-0124 decision 3 widened it for `state.read` and `instance.read`; the property holds: such a call appended no line, selected no backend, ran no step and consumed nothing; the four `hypotheses_*` kinds of `hypotheses.read`; `verdicts_mismatch` of `verdicts.write`, here for the round's stored file against its hypothesis record. **New**: `round_not_current`, `key_not_stored`, `key_record_invalid`, `key_record_unreadable`, `verdicts_invalid`, `verdicts_unsupported`, `verdicts_unreadable`, `case_exists`, `case_not_written`, each a *name* of ADR-0001 decision 1. Searched on 2026-10-20 in `hilclaw/`, `tests/`, `orchestration/` and `ARCHITECTURE/`: none occurs; the three `verdicts_*` are formed like the `hypotheses_*` kinds, and `case_exists` and `case_not_written` like `verdicts_exist` and `verdicts_not_written`, on purpose. None is reserved.
- **Not journaled**: it costs no limited resource and its outcome is the file (as ADR-0124 decision 3 reads `state.write`). It is a tool of the registry beside the FR-10 tools, added to `default_registry` in the source and in no other way (cited: #5 A-12 point 3).
- **Left to the code slice**: the module, the description and input schema, the read of `verdicts.json` beside `hypotheses_tool.read`, and the encoding of the built case into bytes (ADR-0029 decision 2's text form; as `verdicts.write` fixes one).

### 4. (c) Which rounds are promoted

- **Both files valid and the pair within ADR-0071's rules**: promoted; the case holds both copies.
- **A valid hypothesis record and no verdicts file**: promoted; the case has no `verdict_record`, which means only that the tree held no verdicts file then (cited: ADR-0072 decision 3). Weighed: FR-18 stores rejected hypotheses and failed attempts, and a round that never reached evaluate still tested hypotheses a later run should see; the cost ADR-0072 decision 3 names (the case never gains verdicts) is small here, since promotion is the round's last write (decision 5) and no record provides a round's verdicts after its end.
- **A verdicts file present but invalid, of another version or unreadable, or a pair that breaks ADR-0071**: no case (`verdicts_invalid`, `verdicts_unsupported`, `verdicts_unreadable`, `verdicts_mismatch`). A case without `verdict_record` would say that no verdicts file was there (ADR-0072 decision 3), which is false; nothing is repaired (cited: ADR-0071 decision 2). `verdicts.write` refuses such a file (cited: ADR-0128 decision 6), so it arises from another writer or from damage.
- **No hypothesis record**: no case (`hypotheses_missing`; cited: ADR-0072 decision 3). The round's failed attempts stay in `runs/` only.
- **A refusal does not stop the round.** On any failure kind the Round-Manager reports the kind in one line and goes on to the write that ends the round; that round then has no case. The alternative — ending the session with the round open so a later turn retries — would rest on what a turn does in a round it re-enters, which no record decides (OD-17); a refusal caused by a file's content repeats, and calling again after a passing failure is a per-tool retry policy, which is OD-17's too.

### 5. (d) When: right before the write that ends the round

- **Order in a round ≥ 1**: the round's last other write (its verdicts, or the step that would have delegated them); then `case.write`; then the write that ends the round (ADR-0012 decision 6); then `run.commit` (cited: ADR-0127 decision 3). Nothing else is written into the run or the key directory between `case.write` and the write that ends the round. This is P2's order, the promotion before "STATE.json 갱신 … → commit", and the order ADR-0127 decision 4 names as avoiding both losses.
- **A death between the case write and the write that ends the round** leaves the case under its final name in the key directory, uncommitted, and `STATE.json` still naming the round. The next turn's entry calls `run.commit`, which finds no round end owed and commits nothing (cited: ADR-0127 decisions 4 and 5; `hilclaw/run_commit.py`); the case stays in the working tree, and the turn goes on with the same round (cited: ADR-0118 decision 2). What it does in that round is OD-17's; if it reaches promotion again, `case.write` answers `case_exists`, nothing is replaced, and the round goes on to its end, whose commit takes the case in because it exists then (cited: ADR-0127 decision 4). **Whether a turn's end that ends no round commits anything is HQ-0043** (ADR-0127 decision 8) and is not answered here.
- **A death after the write that ends the round and before its commit**: the next entry makes the owed commit and takes the case in (cited: ADR-0127 decisions 4 and 5). **A death inside the write** leaves no case or the whole one, and a temporary file is never taken for a case (cited: ADR-0072 decision 1).

### 6. (e) The definition's place

- **The step is written into "The round steps" of `orchestration/round-manager.md`** with P2-1's round steps; its tool sentence adds `mcp__hilclaw__case_write`, with the run id as `run_id`, as the only means of writing a case. No file under `orchestration/agents/` is made for it. No model is named (HQ-0041).

### Walk-through

| Situation | What follows |
|---|---|
| Round 2: valid `hypotheses.json` and `verdicts.json` | `case.write` stores `case-<run_id>-0002.json` with both copies, `with_verdicts` true; the write that ends round 2; `run.commit` takes the case in |
| Round 1 of P2-5, every verdict `inconclusive` (cited: ADR-0131 decision 6) | As above; the case copies the `inconclusive` verdicts unchanged and keeps them (ADR-0131 decision 6's cost) |
| Round 3 has `hypotheses.json` and no `verdicts.json` | A case without `verdict_record`, `with_verdicts` false |
| The key directory or a key record file is missing (today every such run: nothing stores them, Consequences) | `key_not_stored`; nothing is created; the Round-Manager reports it and ends the round without a case |
| A second `case.write` for the round, after a death before the write that ends it | `case_exists`; nothing replaced; the round goes on to its end and its commit takes the first case in |
| A request for round 0 | `invalid_request` |
| A call after the write that ends the round | `round_not_current`; nothing written |
| `verdicts.json` present and invalid | `verdicts_invalid`; no case |

## Alternatives considered

| Point | Alternative | Weighing | Outcome |
|---|---|---|---|
| (a) | **Round-Manager inline, through a tool** | Deterministic step (P1 condition 4); one call per round | **Adopted** |
| (a) | A `promoter` sub-agent | A fresh context each round for one call with no judgement; against P1 condition 4 | Rejected |
| (a) | The turn loop, between sessions | The loop writes nothing into the run (ADR-0127 decision 6); the case would come after the round's end | Rejected |
| (b) | **A checking registry tool reads the files and writes the case** | Rules of ADR-0072 decision 3 held before the write; no file tool needed | **Adopted** |
| (b) | The Round-Manager's own `Write` | K4; ADR-0124 decision 2; the model, not a validator, would copy two documents whole | Rejected |
| (b) | `run.commit` writes the cases it commits | Revises landed ADR-0127 and its code; a refused case would then block or silently thin a commit | Rejected |
| (b) | Check only that the key directory exists | A case below a key without records is never found (ADR-0073 decision 1) | Rejected |
| (b) | No check of `STATE.json`'s `round` | The order of decision 5 would rest on a prompt (K4) | Rejected |
| (c) | No case for a round without verdicts | Loses tested hypotheses that FR-18 stores | Rejected |
| (c) | Call `case.write` again in the same turn after a passing failure (`case_not_written`, an `*_unreadable` kind) | A per-tool retry rule, open under OD-17 ("도구별 선언적 재시도"); not made here | Left open |
| (c) | Stop the session on a refusal | Rests on an undecided re-entered round (OD-17); `key_not_stored` would stop every run at round 1 until OD-26 | Rejected |
| (d) | Case after the write that ends the round | Lost to a death before the commit (ADR-0127 decision 4) | Rejected |
| (d) | Case at the next turn's entry | The round's commit is already made; the case joins no commit | Rejected |

## Consequences

- **Slices it enables** (code mode; each tested with no `claude` at all — D16):
  1. **Now**: the tool `case.write` of decision 3 in a module of `hilclaw/` with its test file (each kind in its order, both rounds with and without `verdicts.json`, the walk-through rows), registered in `default_registry` of `hilclaw/tools.py` with its docstring; the docstrings of `hilclaw/cases.py` and `hilclaw/cases_file.py` ("Promotion … is open").
  2. **With P2-1's round steps**: the promotion step of decision 6 in `orchestration/round-manager.md`.
- **A first-case run cannot store a case yet.** Nothing creates a key directory with its two record files (ADR-0004 decision 5: "whatever creates its directory … (OD-26)"; `store_hw_profile` and `store_op_signature` have no caller), so every `case.write` of such a run answers `key_not_stored`. **The next record P2-7's storing half needs is a record of OD-26 for these runs**: who stores the two key records, when, and how they enter a commit (ADR-0127 decision 4). Not decided here.
- **Less exact, not edited**: ADR-0072 decision 1 ("Which agent or tool holds that step is OD-23"; "a case can still be written into a key directory that holds no record" — not by this tool) and Boundaries "Promotion"; ADR-0127 decision 4 ("What the case files need": "the order itself is OD-23's") and Boundaries ("the order of the promotion write against the write that ends the round"); ADR-0128 Boundaries ("the promoter"); ADR-0124 and ADR-0126 Boundaries ("the rest of the roster"); ADR-0019 decision 2, widened as above; and, as observations, "The round steps" of `orchestration/round-manager.md` and the `default_registry` docstring of `hilclaw/tools.py` (slices 2 and 1).
- **UsageCases and StandardScenarios**: no sentence becomes false; the note of S0 step 6 is narrowed, and the notes of S0 step 6 and S6 step 4 name OD-26 for the key directory.
- **A-13 reading.** Document mode. No code, test, setting or dependency changes. **No data-plane change**: the case file, its members, name and write, `hypotheses.json`, `verdicts.json`, `STATE.json`, `instance.json` and the key record files are unchanged, no validator changes, and the kinds of decision 3 are tool failure kinds.
- **Runtime acceptance items** (D16; nothing was tried, nothing is required of the development machine). ADR-0118 item (vii) is used, not changed. **New**, numbered after (xxii) on `main` and (xxiii), (xxiv) on the unlanded branch of ADR-0132:
  - **(xxv)** The main session of a `-p` turn session sees `mcp__hilclaw__case_write` and may call it under the means item (vii) gets.
  - **(xxvi)** A live Round-Manager calls `case.write` once per round ≥ 1, after the round's verdicts work and before the write that ends the round, and goes on to that write after a failure.
- **The cost, plainly.** Until OD-26's record, no case is stored. A refusal of any kind, a passing file-system failure included, leaves its round without a case for good. A case written before a death and a later re-entry of the round keeps what the files held then. `case.write` does not repeat the log and comparison checks of `verdicts.write` (ADR-0128 decision 6, ADR-0131), so a verdicts file another writer left that passes ADR-0071 is copied as it is. The tool reads five files and holds the order, so one more tool and nine more kinds to keep.

## Boundaries (not decided here)

- **The key directory and its record files**: who creates them and when, and who commits them (OD-26; ADR-0127 Boundaries).
- **`best.json` and `technique_stats.json`** and any other file a promotion writes (OD-20, OD-7); **promotion across repositories** and its PR policy (OD-25, owner-only); k and Best-of-N beyond N = 1 (OD-29, OD-15).
- **The lookup and the selection side** (ADR-0073; the unlanded ADR-0132); the identification of cases read (FR-11).
- **A turn that ends before its round ends** and whether its end commits (HQ-0043; ADR-0127 decision 8); **a re-entered round** beyond decision 5 (OD-17); HQ-0031.
- **Models and token accounting** (HQ-0041, #5 A-8); whether any agent has a shell (HQ-0040); hooks and permissions (PLAN P2-4).
- **Runs outside ADR-0120 decision 1**, a run whose `instance.json` states no `op_signature` beyond "no case" (OD-8 ㉘, OD-26) or would state several (ADR-0031 decision 4; OD-6 ③, #5 B-4); retention and re-judgement of cases (ADR-0072 Boundaries).
- Any edit of an earlier record, of FR or NFR text, UsageCases, `hilclaw/`, `orchestration/`, tests, CI, `.claude/`, any settings file or the `HIL-Claw-data` repository; any new external dependency.

## References

- [Requirements](../Requirements.md): FR-11, FR-17, FR-18, NFR-1; register rows OD-17, OD-20, OD-23, OD-26, OD-29, OD-30. [OpenDecisionProposals](../OpenDecisionProposals.md) [OD-23](../OpenDecisionProposals.md#od-23), [OD-30](../OpenDecisionProposals.md#od-30). [StandardScenarios](../StandardScenarios.md) S0, S1, S6, S8.
- ADR-0001 (decisions 1, 4; record format); ADR-0004 (decisions 4, 5); [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decision 4); ADR-0012 (decisions 3, 6); ADR-0015 (decisions 2 to 4); ADR-0019 (decisions 2, 3); [ADR-0029](ADR-0029-od8-spec-file.md) (decision 2); ADR-0059 (decisions 1, 5); ADR-0071 (decisions 1, 2, 6); ADR-0072 (decisions 1 to 3; Consequences; Boundaries); ADR-0073 (decision 1); ADR-0118 (decisions 2, 6; item (vii)); ADR-0120 (decision 1; W1); ADR-0124 (decisions 2, 3); ADR-0127 (decisions 2 to 6, 8); ADR-0128 (decisions 2, 6; Boundaries); ADR-0131 (decision 6).
- #4 body §3c; §3a revision https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5138366881 ; https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139248800 ; https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139876430 ; #5 A-1 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5046307826 · A-12 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5946779596 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 ; #7 §2(8).
- Code, as observation only: `hilclaw/cases.py`, `hilclaw/cases_file.py`, `hilclaw/key_records.py`, `hilclaw/run_commit.py`, `hilclaw/hypotheses_tool.py`, `hilclaw/verdicts_file.py`, `hilclaw/verdicts_tool.py`, `hilclaw/tools.py`, `orchestration/round-manager.md`.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P2-1, P2-4, P2-5, P2-7; CLAUDE.md "개발 드라이버와 런타임의 구분"; task T-0362.
