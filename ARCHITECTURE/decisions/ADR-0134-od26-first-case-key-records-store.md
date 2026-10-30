# ADR-0134: The two key record files of a first-case run — the Round-Manager stores the two records its run's `instance.json` states through one new registry tool, `key.store`, as the first round step of every turn that carries a round, and `run.commit` takes the record files into the run's next round-end commit where `HEAD` does not hold them (part of OD-26 and OD-23, for the runs of ADR-0120 decision 1)

## Status

- **Accepted on 2026-10-20** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it.**
- **Two kinds of content.** What an owner decision, a requirement, an accepted record or a code docstring says is **cited**, with its source named. **Everything else is this record's own**: the scope, the holder, the tool `key.store` with its request, result, checks and kinds, the source of the stored records, the moment, the widening of `run.commit`, the readings marked as such, and every weighing.
- **The owner-sentence search.** Searched: the body of #4 and its 6 comments; the body of #5 and the 40 of its 219 comments whose text holds no "posted by driver" marker; the bodies and comments of #7 (2) and #8 (6). Terms: 온보딩, onboard, 등록, register, registr, hw_profile.json, op_signature.json, key record, 키 레코드, key_records, hw_source. The sentences found that touch the point, each read for what it says and no further:
  - **O1** — FR-14 ④ (owner, 2026-09-03 for the HW source): a new hw_profile, its HW source, document pointers and tool access are **registered** "등록부에" and can be **selected** at instance start. **This record reads the 등록부 as the onboarding registry of OD-26 and #5 B-2**, which no record has placed or shaped; no record names the key record files of `db/` as that registry (ADR-0004 decision 5 says only that their writer "may be onboarding").
  - **O2** — #5 A-7 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944117402): "The stand-in is registered as its own hw_profile (`cpu_standin`), so FR-7 statistics and the catalog are keyed separately". Read as: a key of its own, not a means or a moment of registration.
  - **O3** — #5 A-1 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5046307826): "매 라운드 `runs/`→`db/` 승격 커밋 … 원자적 커밋 1개" (ADR-0127's C4); and **K4**, "프롬프트만으로 쓰기 구역을 주는 것은 너무 약하다" (https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139876430), as ADR-0124 and ADR-0133 cite it.
  - Found and not bearing on the point: the source registry of FR-14 ① (#4 comment 5139060413), the registration of the stand-in as a backend (#5 A-7 body), the registry-of-ODs comments of #7 and #8.
- **Answers**, **for the runs of ADR-0120 decision 1 only**, part of **OD-26** (who stores the two key record files of the run's key, from what, when, and how they enter a commit — ADR-0004 decision 5, ADR-0127 decision 4 and Boundaries, ADR-0133 Consequences) and part of **OD-23** (which agent holds that step, and its means). **OD-26 moves from `미착수` to `논의중`; OD-23 and every other OD keep their status.** No sub-question is registered. Nothing here needs #5 A or B items, C-6, OD-25 or OD-3, and HQ-0032 and HQ-0043 are not answered.
- **No member, file, path, kind of event, value or version of the data plane is added or changed**, and no validator changes. **It is a record, not code**: no `claude` process was started for it, and nothing below was tried in a live session (D16).
- It builds on [ADR-0001](ADR-0001-od4-key-schema.md) (decisions 1, 3 to 5), [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decisions 5, 10), [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decision 4), [ADR-0014](ADR-0014-od8-whole-file-writes.md) (decisions 3, 6), [ADR-0015](ADR-0015-od18-tool-contract-frame.md) (decisions 2 to 4), [ADR-0018](ADR-0018-od8-instance-record-hw-profile.md) (decision 3), [ADR-0019](ADR-0019-od18-unusable-run-kind.md) (decisions 2, 3), [ADR-0031](ADR-0031-od8-instance-record-op-signature.md) (decisions 3, 5), [ADR-0041](ADR-0041-od18-correctness-check-dimensions.md) (decision 4), [ADR-0073](ADR-0073-od30-case-lookup-and-case-basis.md) (decision 1), [ADR-0076](ADR-0076-od8-instance-start-required-members.md) (decision 2), [ADR-0025](ADR-0025-od8-instance-file-write.md) (the write of `instance.json`), [ADR-0115](ADR-0115-od8-instance-start-performer.md) (decision 2), [ADR-0118](ADR-0118-od18-round-process-boundary.md) (decision 2), [ADR-0120](ADR-0120-od8-first-state-file.md) (decisions 1 to 3), [ADR-0124](ADR-0124-od23-round-manager-run-file-access.md) (decisions 2, 3), [ADR-0127](ADR-0127-od8-commit-step.md) (decisions 2 to 5, 8) and [ADR-0133](ADR-0133-od23-first-case-round-promotion.md) (decisions 2 to 5). **If one of them is reverted, this record is revisited with it.**
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of ADR-0001.

## Context

- **The open points** (cited): "a key record file is written by whatever creates its directory, which may be onboarding rather than a promotion (OD-26)" (ADR-0004 decision 5); "The key record files of the directory are not taken in either … who commits them, and when, is open (OD-26)" (ADR-0127 decision 4); ADR-0133 Consequences: until such a record "every `case.write` of such a run answers `key_not_stored`", and "The next record P2-7's storing half needs is a record of OD-26 for these runs".
- **What exists** (code, as observation only): `hilclaw.key_records.store_hw_profile(data_root, record)` and `store_op_signature(data_root, hw_profile_key, record)` validate the record, write its file once by ADR-0014 decision 3 with the directories above it, return `created`, write nothing for a stored key "also when the attributes (`hw_source`, `label`) … differ", raise `KeyCollisionError` or `CorruptKeyRecordError` for a stored record, `KeyRecordNotFoundError` for an op_signature below an unstored hw_profile, and pass an `OSError` through; nothing in `hilclaw/` calls them. `hilclaw.run_commit.commit` takes in, against `HEAD`, the files below `runs/<run_id>/` and the case files of the owed rounds from 1, "and nothing else". The start function of ADR-0115 is not on `main` (PR #186, T-0324, BLOCKED by HQ-0032). `orchestration/round-manager.md` says the round steps are not yet defined.

## Decision

A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope

- **The two key record files of the key of a run of ADR-0120 decision 1**: `db/<hw_profile_key>/hw_profile.json` and `db/<hw_profile_key>/<op_signature>/op_signature.json` (ADR-0004 decision 5) for the records its `instance.json` states. Not the onboarding registry of O1, any other file of a key directory, or any other run.

### 2. (a) Who: the Round-Manager, inline, through the tool `key.store`

- **The Round-Manager stores them itself by calling `key.store` (decision 3) through the package's MCP front**, naming its run by `run_id`. No sub-agent, neither the turn loop, the start function, `case.write` nor `run.commit` stores them for these runs, and the Round-Manager stores them by no other means.
- **Why.** The step needs no judgement: given `instance.json`, both files are determinate (decision 4), so it is one tool call, inline (P1 condition 4 of #4 §3a, as ADR-0133 decision 2 cites it). Every run of the scope has a Round-Manager turn that reads `instance.json` through a typed tool already (ADR-0124 decision 3), and a tool, not a prompt, keeps the write to what the store function checks (K4).
- **What each choice makes P2-7 and P2-5 wait for** (Alternatives): with this choice the tool and the commit change are code slices that can land now, with no `claude` and without the start function; the definition step lands with P2-1's round steps, as ADR-0133 slice 2 does. P2-5 still waits for the start (T-0324, HQ-0032) and P2-1, as it did before this record, and for nothing more.

### 3. The tool `key.store`

| Part | Content |
|---|---|
| Name (MCP name) | `key.store` (`mcp__hilclaw__key_store`); no `_` in the name, so the mapping of ADR-0010 decision 4 stays reversible |
| Request | Exactly `run_id`, required, with the meaning and form of ADR-0015 decision 4; any other member, or none, is `invalid_request` |
| Result | `{"hw_profile_created": true or false, "op_signature_created": true or false}`: whether this call created each file |
| Checks, in order | ① the request (`invalid_request`, ADR-0015 decision 2); ② the data root (`no_data_root`); ③ the run's `instance.json` read and parsed, as `instance.read` reads it (`run_file_missing`, `run_file_invalid`, `run_file_unsupported`, `run_file_unreadable`); ④ an `op_signature` stated (`op_signature_not_stated`); ⑤ `store_hw_profile` of `hw_profile.record` (`key_record_invalid` for a collision or an invalid stored record; `key_not_written` for any other failure, a failing read of a stored record, a data root gone since ② and a name taken during the write and free again when re-read among them; a name taken by a record during the write is read as one found before it); ⑥ `store_op_signature` of `op_signature.record` below `hw_profile.key` (the same two kinds; a hw_profile record gone since ⑤ is `key_not_written`) |

- **Nothing is created before ⑤.** A refusal at ⑥ keeps a file ⑤ created: no atomicity between the two record files is given (cited: ADR-0014 decision 6). A call that finds both stored writes nothing and returns two `false`.
- **Kinds.** Reused with their meanings: `invalid_request`, `no_data_root`; the four `run_file_*` kinds of ADR-0019 decision 3 — **this record widens ADR-0019 decision 2's "only at the lookup or the selection" to this read**, as ADR-0124 decision 3 and ADR-0133 decision 3 did; the property holds: such a call appended no line, selected no backend, ran no step and consumed nothing; `op_signature_not_stated` of ADR-0041 decision 4 (a valid file that states no op_signature), the same name for the same situation on purpose, where `case.write` folds it into `key_not_stored`; `key_record_invalid` of ADR-0133 decision 3. **New**: `key_not_written`, a *name* of ADR-0001 decision 1. Searched on 2026-10-20 in `hilclaw/`, `tests/`, `orchestration/` and `ARCHITECTURE/`: `key.store`, `key_store` and `key_not_written` do not occur; `key_not_written` is formed like `case_not_written` and `state_not_written`, on purpose. It is not reserved.
- **Not journaled**: it costs no limited resource, repeats without effect, and its outcome is the files (as ADR-0124 decision 3 reads `state.write`). A tool of the registry beside the FR-10 tools, added to `default_registry` in the source and in no other way (cited: #5 A-12 point 3).
- **Not checked**: `STATE.json`, the round, the scope. Within the scope a call at any moment stores the same two files, and a missed call costs cases only (decision 5), so a check of `round` would refuse a write that does no harm. The tool does not check the scope, as this record reads the checks of `case.write` (ADR-0133 decision 3, which has none); it is defined for, and given to, the Round-Manager of these runs only (decision 5). Whether a run outside the scope may have its key stored this way is not decided (Boundaries).
- **Left to the code slice**: the module, the description and input schema, and the message texts.

### 4. (b) From what: exactly the two records `instance.json` states

- **The stored records are `hw_profile.record` and `op_signature.record` of the run's `instance.json`, whole** (key fields and attributes; cited: ADR-0018 decision 3, ADR-0031 decision 3). No other source is read. A valid file holds valid records whose keys are the stated `key` members (cited: same decisions), so the store raises no validation error.
- **So the lookup hits.** `case.write` check ⑤ and the lookup of ADR-0073 decision 1 look up the same two records of the same file (cited: ADR-0133 decision 3; ADR-0073 decision 1), and a match compares canonical forms only (cited: ADR-0001 decision 4). Once both files are stored, a later miss is only a collision or damage.
- **No `op_signature` stated**: `op_signature_not_stated`; nothing is stored, not the hw_profile alone: this record's reading is that a run's key is the pair, as the knowledge is kept per pair (cited: FR-13; ADR-0004 decision 5), and no case of such a run is written (cited: ADR-0133 decision 3 ⑤). Within the scope it does not arise: the start requires the member (cited: ADR-0076 decision 2).
- **OD-8 ⑱ is not answered**: whether the start requires a stored record and takes the embedded one from it stays open. If a later record has it do so, `key.store` finds both stored and writes nothing.

### 5. (c) When: the first round step of every turn that carries a round

- **Order**: the entry steps (cited: `run.commit` first, ADR-0127 decision 5; the first `STATE.json` of a fresh run directory, ADR-0120 decision 2); then `key.store`, before any other step of the round, whether the round is begun or gone on with (ADR-0118 decision 2); then the round. So the round-0 turn stores the files, after `instance.json` is under its final name (cited: ADR-0025, ADR-0115 decision 2, ADR-0120 decision 3) and before round 1's lookup (ADR-0073 decision 1) and `case.write` (ADR-0133 decision 5); later turns find them stored and write nothing. A turn whose entry ends it (an entry failure, `"over"`) does not call it.
- **A failure does not stop the round.** The Round-Manager reports the kind in one line and goes on. The round's case is then refused at ⑤ (cited: ADR-0133 decisions 3 and 4) unless the files are stored by then; the next turn's call is the next attempt. Calling again within a turn is a per-tool retry policy, OD-17's. What else a turn does in a round it goes on with stays OD-17's.

### 6. (d) What a store that does not simply succeed answers

- **Another run of the same key stored them** (same attributes): `created` false for each (cited: `key_records`, "writes nothing"); success.
- **Stored with other attributes** (`hw_source` or `label`): the same, success; the stored attributes stay, the run's `instance.json` keeps its own (cited: ADR-0018 decision 3), and the difference is neither compared nor reported. Whether a stored attribute may be updated is OD-26 (cited: `key_records` docstring) and is not changed here.
- **A collision or a corrupt stored record**: `key_record_invalid`; nothing written for that file (cited: ADR-0001 decision 3). The run goes on without cases (decision 5) until a person acts; ADR-0014 decision 3 says the same of a partial file (cited).
- **A failing file system**, a name taken during the write, or a data root gone since ②: `key_not_written`; ADR-0014 decision 3 leaves no record file or the whole one (cited). **A data root not usable at ②**: `no_data_root`.

### 7. (e) How they enter a commit: `run.commit` takes them in where `HEAD` does not hold them

- **Every commit `run.commit` makes for the run also holds each of the two key record files of the run's key directory that exists in the working tree as a regular file and that `HEAD` does not hold**, the paths formed from the keys of `instance.json` with no listing, as for the case files, and no content inspected (cited: ADR-0127 decision 4); an uncommitted record file that collides or is corrupt is therefore committed as it is. A path `HEAD` holds is never taken in again, so a committed record is never changed by a commit. **This record widens ADR-0127 decision 4's "The changes of no other path go into the commit" by these two paths**, without editing it; no failure kind is added.
- **`instance.json` gives no key** (unreadable, invalid, no `op_signature`): no record file is taken in, and nothing is refused on this account; the refusal of ADR-0127 decision 4 for an owed range with a round from 1 is unchanged.
- **Shared files.** Unlike `best.json` (ADR-0127 decision 4), a record file is written once and never changed (cited: ADR-0014 decision 3), so whichever run's commit takes it first takes the one stored record of the key; a run's commit may thus hold a record file another run of the key created. Two runs in one checkout at once stay outside (C-2; OD-17).
- **A death between the store and the commit** leaves the files uncommitted in the working tree; the next commit the run makes takes them in, and the next turn's `key.store` writes nothing. **Whether a turn's end that ends no round commits anything is HQ-0043** (ADR-0127 decision 8) and is not answered: the files wait for the next round-end commit.

### Walk-through

| Situation | What follows |
|---|---|
| A fresh key, round-0 turn | Entry; the first `STATE.json`; `key.store` creates both files, `true`, `true`; round 0 ends; `run.commit` takes in the run's files and both record files |
| The key stored and committed by a previous run, same attributes | `false`, `false`; nothing written or committed |
| The same key, stored with another `hw_source` | `false`, `false`; the stored `hw_source` stays; the run's `instance.json` keeps its own; the lookup hits |
| A stored record collides | `key_record_invalid`; one line; the round goes on; every `case.write` of the run answers `key_record_invalid` |
| A death after the store and before the commit | Next turn: `run.commit`; `key.store` `false`, `false`; the next round-end commit takes the files in |
| The `op_signature` store fails after `hw_profile.json` was created | `key_not_written`; the next turn: `false`, `true`; each file is taken in by the first commit after it exists |
| An earlier run of the key in the same checkout created the files and died before its commit | `false`, `false`; this run's next commit takes them in |
| Round 1's `case.write` afterwards | Check ⑤ hits; the case is stored and committed with round 1 (ADR-0133 decision 5) |

## Alternatives considered

| Point | Alternative | Weighing | Outcome |
|---|---|---|---|
| (a) | **Round-Manager inline, through a tool** | Deterministic; available now; reads the same file the lookup reads | **Adopted** |
| (a) | The start function of ADR-0115, around its `instance.json` write | Not on `main`; P2-7 would wait for T-0324 and HQ-0032. Before the write, a refused start leaves a stored key no run used; after it, a death leaves a run with no key stored and nothing to store it | Rejected |
| (a) | `case.write` stores on a miss | Supersedes ADR-0133 check ⑤ and changes landed code and its tests; nothing stored before round 1, and a round refused before ⑤ stores none | Rejected |
| (a) | `run.commit` stores before it commits | A commit tool that creates data; a store failure would block the commit point or thin it silently | Rejected |
| (a) | An onboarding step a person runs before the instance (UC-0) | The registry is #5 B-2 (owner-only) and OD-26; P2-5 would wait for an owner decision and a manual step per key. An onboarding that a later record defines, run before an instance, stays possible: `key.store` then writes nothing | Rejected for these runs |
| (a) | A sub-agent, or the Round-Manager's own `Write` | P1 condition 4; K4 and ADR-0124 decision 2 | Rejected |
| (b) | Store hw_profile alone when no op_signature is stated | A key directory is the pair; no case follows from it | Rejected |
| (c) | Round 0 only | A failure or a death before the call would leave the run without a stored key for good | Rejected |
| (c) | Before every `case.write` | Too late for round 1's lookup; one more step between promotion and the round's end | Rejected |
| (e) | A commit of `key.store`'s own | A commit that ends no round, beside HQ-0043; a death between store and commit needs the adopted rule anyway | Rejected |
| (e) | Only the round-0 commit takes them in | Misses files a later turn stores after a failure | Rejected |
| (e) | Left uncommitted | Lost to another clone; S6 in another checkout finds no key | Rejected |

## Consequences

- **Slices it enables** (code mode; each tested with no `claude` at all — D16; neither needs the unlanded start function of PR #186, since a test writes `instance.json` itself):
  1. **Now**: the tool `key.store` of decision 3 in a module of `hilclaw/` with its test file (each kind in its order, the walk-through rows), registered in `default_registry` of `hilclaw/tools.py` with its docstring. **And** the widening of decision 7 in `hilclaw/run_commit.py`, its docstring and the tool description: **it changes landed behaviour**, pinned by `tests/test_run_commit.py` (the paths a commit takes in, the cases of the range, round 0 without an op_signature, the refusal for an instance that gives no key directory); those tests gain the cases of decision 7. The two may be one task or two.
  2. **With P2-1's round steps**: the step of decision 5 in "The round steps" of `orchestration/round-manager.md`, with `mcp__hilclaw__key_store` as the only means of storing the files.
- **Less exact, not edited**: ADR-0004 decision 5 ("whatever creates its directory … (OD-26)" — for these runs, the Round-Manager through `key.store`); ADR-0127 decision 4 ("The changes of no other path go into the commit"; "The key record files … are not taken in either … (OD-26)") and its Boundaries item "who commits the key record files, and when (OD-26)"; ADR-0133 Consequences ("A first-case run cannot store a case yet"), its Walk-through row "The key directory or a key record file is missing (today every such run …)" and its Boundaries "The key directory and its record files"; ADR-0018 Boundaries and ADR-0001 Boundaries ("who fills in the record") for these runs; ADR-0019 decision 2, widened as above; and, as observations, the `hilclaw/key_records.py` docstring ("registers no key on its own" stays true of the module, which now has a caller), the `hilclaw/run_commit.py` docstring and description ("and nothing else"), the `default_registry` docstring, and "The round steps" of `orchestration/round-manager.md`.
- **UsageCases and StandardScenarios**: no sentence becomes false; the notes of S0 step 6 and S6 step 4 narrow OD-26 to runs outside the first case.
- **A-13 reading.** Document mode. No code, test, setting or dependency changes. **No data-plane change**: the key record files, their names, form, content and write, `instance.json`, `STATE.json`, the case file and every other file are unchanged; which paths a commit holds is no member, file or value of a file; no validator changes; `key_not_written` is a tool failure kind.
- **Runtime acceptance items** (D16; nothing was tried, nothing is required of the development machine). ADR-0118 item (vii) is used, not changed. **New**, numbered after (xxvi) on `main` and (xxiii), (xxiv) on the unlanded branch of ADR-0132:
  - **(xxvii)** The main session of a `-p` turn session sees `mcp__hilclaw__key_store` and may call it under the means item (vii) gets.
  - **(xxviii)** A live Round-Manager calls `key.store` as the first round step of each turn that carries a round, before any other step of it, and goes on after a failure.
- **The cost, plainly.** One tool call per turn that carries a round, reading `instance.json` and up to two record files. A store failure costs the cases of the rounds until a later turn's store succeeds. A collision blocks the cases of the key until a person acts. A run's commit may hold a record file another run created. The stored attributes are those of the first run that stored the key, whatever later runs state.

## Boundaries (not decided here)

- **The onboarding registry** of FR-14 ④ (O1), its schema and storage, and the description of endpoint, transport, quota and reservation (#5 B-2, owner-only; OD-26); **sim-only onboarding**; **a smoke test** (UC-0 step 5); **attribution of history between keys**; **handling per `hw_source`**; **the `hw_source` value of `cpu_standin`** (ADR-0035 decision 8); **whether a stored attribute may be updated** (OD-26); **other accelerators**; and who registers a key, when, for any run outside the scope.
- **Whether the start of an instance is logged** (OD-8 ⑧); **the caller of the start function** (ADR-0115 decision 1), and HQ-0032; OD-8 ⑱.
- **A turn that ends before its round ends** and whether its end commits (HQ-0043; ADR-0127 decision 8); **a re-entered round** beyond decision 5 (OD-17).
- **`best.json` and `technique_stats.json`** and any other file of a key directory (OD-20, OD-7); **the lock and two writers of one key** (OD-17; C-2).
- **Runs outside ADR-0120 decision 1**, and what `key.store` may store for one; models and token accounting (HQ-0041, #5 A-8); whether any agent has a shell (HQ-0040); hooks and permissions (PLAN P2-4).
- Any edit of an earlier record, of FR or NFR text, UsageCases, `hilclaw/`, `orchestration/`, tests, CI, `.claude/`, any settings file or the `HIL-Claw-data` repository; any new external dependency.

## References

- [Requirements](../Requirements.md): FR-13, FR-14 ④, FR-18, NFR-1; register rows OD-8, OD-17, OD-23, OD-26. [OpenDecisionProposals](../OpenDecisionProposals.md) [OD-23](../OpenDecisionProposals.md#od-23), [OD-26](../OpenDecisionProposals.md#od-26). [StandardScenarios](../StandardScenarios.md) S0, S1, S1-b, S6. [UsageCases](../UsageCases.md) UC-0.
- ADR-0001 (decisions 1, 3 to 5; Boundaries; record format); ADR-0004 (decisions 5, 10); ADR-0010 (decision 4); ADR-0014 (decisions 3, 6); ADR-0015 (decisions 2 to 4); ADR-0018 (decision 3; Boundaries); ADR-0025; ADR-0019 (decisions 2, 3); ADR-0031 (decisions 3, 5); [ADR-0035](ADR-0035-od4-cpu-standin-hw-key-values.md) (decision 8); ADR-0041 (decision 4); ADR-0073 (decision 1); ADR-0076 (decision 2); ADR-0115 (decisions 1, 2); ADR-0118 (decision 2; item (vii)); ADR-0120 (decisions 1 to 3); ADR-0124 (decisions 2, 3); ADR-0127 (decisions 2 to 5, 8; Boundaries); ADR-0133 (decisions 2 to 5; Consequences; Boundaries).
- #4 §3a revision https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5138366881 ; https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139876430 ; #5 A-1 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5046307826 · A-7 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944117402 · A-12 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5946779596 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 .
- Code, as observation only: `hilclaw/key_records.py`, `hilclaw/keys.py`, `hilclaw/case_tool.py`, `hilclaw/run_commit.py`, `hilclaw/run_file_tools.py`, `hilclaw/instance_start.py`, `hilclaw/tools.py`, `orchestration/round-manager.md`.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P2-1, P2-5, P2-7; CLAUDE.md "개발 드라이버와 런타임의 구분"; tasks T-0324, T-0362, T-0363.
