---
id: T-0364
title: Record ADR-0134, who stores the two key record files of a first-case run, when, and how they enter a commit (part of OD-26 and OD-23; PLAN P2-7)
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-13, FR-14, FR-18, NFR-1, OD-26, OD-23, OD-8, OD-4, OD-30, S0, S1, S6]
dependsOn: [T-0362, T-0363]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0134-od26-first-case-key-records-store.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 220, files: 4}
hq: []
---
## Why

PLAN P2-7 is a checklist item. Its storing half writes each round's case into `db/<hw_profile_key>/<op_signature>/`. P2-7 comes before P2-5 in the P2 order (PLAN P2 head, D18), so the D18 rule for work outside the checklist does not apply.

The case writer now exists: ADR-0133 and the registry tool `case.write` (T-0363, `hilclaw/case_tool.py`). But today every real `case.write` answers `key_not_stored`, because nothing creates a key directory with its two record files:
- ADR-0004 decision 5 says "a key record file is written by whatever creates its directory, which may be onboarding rather than a promotion (OD-26)".
- `hilclaw.key_records.store_hw_profile` and `store_op_signature` have no caller.
- ADR-0127 decision 4 and its Boundaries leave "who commits them, and when" to OD-26.
- ADR-0133 Consequences names this as "the next record P2-7's storing half needs": a record of OD-26 for first-case runs, covering who stores the two key records, when, and how they enter a commit.

Without this record the first run (P2-5) stores no case (FR-18), and S6 (the second run reads the first run's cases) cannot hold.

OD-26, OD-23 and OD-8 are design-level ODs, not owner-only (DRIVER §9: owner-only means the #5 A/B items, C-6, OD-25 and OD-3). Under DRIVER §6 and §9, this task therefore writes the ADR. It must stay inside first-case runs (ADR-0120 decision 1, `cpu_standin` or the mock). It must not decide any of these:
- the general onboarding registry, its schema, or endpoint and transport description (#5 B-2, owner-only);
- sim-only onboarding or a smoke test;
- the `hw_source` value of `cpu_standin` (the question ADR-0035 decision 8 files under OD-26);
- whether a stored attribute may be updated;
- HQ-0032 (how the start function learns of a given id; T-0324);
- HQ-0043 (#5 A-3 and the turn that ends before its round ends).

## Required Reading

- `PROCESS/DRIVER.md`:
  - §2 (doc mode);
  - §3-5 (executor procedure, resume rule, time limit);
  - §5 (naming: branch `claude/T-0364-<slug>`, trailer `Task: T-0364`; size cap);
  - §8 (the `— posted by driver` footer);
  - §9 (OD closing authority, owner notice on #5, 7-day objection window).
- `CLAUDE.md`, all rules. In particular:
  - "미결은 발명하지 않는다";
  - 문서 커버리지 재검사;
  - the A-13 branch/merge procedure: in doc mode, the reviewer cycle, a rebase onto `origin/main`, one squashed commit with the `Reviewed-by` and `Task:` trailers, and a direct push to main;
  - the BLOCKED reasons (a data-plane schema change is one);
  - "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole; doc-mode return path).
- The record that asks for this one, read whole: `ARCHITECTURE/decisions/ADR-0133-od23-first-case-round-promotion.md` (134 lines). Decision 3's check ⑤, the Walk-through row "The key directory or a key record file is missing", Consequences (line 109) and Boundaries (line 120) matter most.
- Keys and records, in `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`:
  - decisions 1 to 5 (lines 17-72; `hw_source` and `label` are attributes; the exact-match rule of P1);
  - Boundaries (lines 125-137);
  - §"Record format" (line 146 on).
- The knowledge tree, in `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`:
  - decisions 4 and 5 (lines 98-111);
  - decision 10 (lines 146-149);
  - Boundaries (lines 178-188).
- How a key record file comes to be: `ARCHITECTURE/decisions/ADR-0014-od8-whole-file-writes.md` decisions 3 and 6 (lines 37-55, 73-81).
- What `instance.json` states, which is the likely source of both records:
  - `ARCHITECTURE/decisions/ADR-0018-od8-instance-record-hw-profile.md` decisions 3 and 5 (lines 42-56, 64-68) and Boundaries (lines 139-149);
  - `ARCHITECTURE/decisions/ADR-0031-od8-instance-record-op-signature.md` decisions 2 to 5 (lines 32-83).
- `ARCHITECTURE/decisions/ADR-0035-od4-cpu-standin-hw-key-values.md` decision 8 (lines 112-116) and Boundaries (lines 181-182). These hold the `hw_source` question this record must not answer.
- The start and the first state:
  - `ARCHITECTURE/decisions/ADR-0115-od8-instance-start-performer.md` decisions 1 to 3 (lines 44-89; the start function, no tool, caller not decided);
  - `ARCHITECTURE/decisions/ADR-0076-od8-instance-start-required-members.md` decisions 1 to 3 (lines 23-58);
  - `ARCHITECTURE/decisions/ADR-0120-od8-first-state-file.md` decisions 1 to 4 (lines 34-69; the scope, and the round-0 Round-Manager writes the first `STATE.json`).
- The commit: `ARCHITECTURE/decisions/ADR-0127-od8-commit-step.md`:
  - decision 4 (lines 50-68). Read the bullet "`best.json` and `technique_stats.json`", whose last sentences leave the key record files to OD-26;
  - Boundaries (lines 149-160).
- The lookup that must hit: `ARCHITECTURE/decisions/ADR-0073-od30-case-lookup-and-case-basis.md` decision 1 (lines 25-38) and `ARCHITECTURE/decisions/ADR-0072-od30-hypothesis-outcome-case-file.md` decisions 1 and 4 (lines 23-34, 63-69).
- The model for a Round-Manager registry tool, if you choose one: `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md` decisions 2 and 3 (lines 37-63).
- `ARCHITECTURE/Requirements.md`:
  - FR-13, FR-14 (④ is onboarding), FR-18;
  - the 상태 어휘 and 갱신 규칙 paragraphs (lines 76-78);
  - the OD register preamble **"행 형식"** (line 84);
  - rows OD-4, OD-8, OD-23, OD-26 and OD-30.
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - the header's **"기록 규칙"** (line 8);
  - sections OD-4 (from line 36), OD-23 (from line 394) and OD-26 (from line 435; its last bullet lists the open points one by one).
- `ARCHITECTURE/StandardScenarios.md`:
  - §검사 규칙 (lines 13-29);
  - §검사 결과 (from line 168). **Its first paragraph is the recording rule**;
  - S0, S1, S1-b and S6, and the verdict rows that name OD-26 (lines 186-193).
- `ARCHITECTURE/UsageCases.md` UC-0 (lines 54-67), as context only. It is the general onboarding flow; this record is not it.
- Code, read only as observations (this record binds no code):
  - `hilclaw/key_records.py`: the module docstring, `store_hw_profile`, `store_op_signature`, `lookup` and their errors. A store for a stored key writes nothing, even when the attributes differ;
  - `hilclaw/keys.py` (record validation);
  - `hilclaw/case_tool.py` (check ⑤);
  - `hilclaw/run_commit.py` (the paths a commit takes in);
  - `hilclaw/instance_start.py` and `hilclaw/instance_file.py`;
  - `hilclaw/run_file_tools.py`;
  - `hilclaw/tools.py` `default_registry`;
  - `orchestration/round-manager.md`.
- Before you edit `ARCHITECTURE/`, run `gh pr list` and read issues #4, #5, #7 and #8 (CLAUDE.md 세션 진입 점검). If an open PR touches the same tables or sections, stop and return BLOCKED.
  - Open PR #186 (T-0324, BLOCKED by HQ-0032) touches only `hilclaw/start_instance.py`, `tests/test_start_instance.py`, `tests/test_standin_profile.py` and `tests/test_gemm_contract.py`. The start function of ADR-0115 is therefore **not on main**.
  - The unlanded branches `claude/T-0361-*`, `claude/T-0318-*`, `claude/T-0231-*`, `claude/T-0210-*` and `claude/T-0264-*` edit `Requirements.md`, `OpenDecisionProposals.md` and `StandardScenarios.md`. None is known to edit the OD-26 row or section, but check on the day. Do not take their content, and note any overlap in the Result.

## Acceptance Criteria

1. **The new record and its number.**
   - A new record `ARCHITECTURE/decisions/ADR-0134-od26-first-case-key-records-store.md` exists in the ADR-0001 record format: Status, Context, Decision with numbered decisions, a Walk-through, Alternatives considered, Consequences, Boundaries, References.
   - ADR-0132 is taken by the unlanded branch `claude/T-0361-*`. Before the push, confirm that ADR-0134 is free on `origin/main` and on every remote branch. If it is not, take the next free number and update every reference.
   - Keep the record at about 180 lines or fewer.
   - Mark every sentence of the record's own as such: use the "cited" versus "this record's own" convention of ADR-0128 / ADR-0133.
2. **Scope and points.** The scope is the runs of ADR-0120 decision 1. Weigh each point below against at least one alternative. Each answer must let `case.write` of a round ≥ 1 find the key (ADR-0133 check ⑤, ADR-0073 decision 1) without inventing anything else.
   - (a) **Who stores the two key record files** (`db/<hw_profile_key>/hw_profile.json` and `db/<hw_profile_key>/<op_signature>/op_signature.json`). Candidates to weigh, at least:
     - the start function of ADR-0115, around its `instance.json` write;
     - the Round-Manager of the round-0 turn, through a new typed registry tool that reads the run's `instance.json` (as ADR-0124 does);
     - `case.write` itself on a miss (this would change ADR-0133 check ⑤; a later record may supersede part of an earlier one but must say so and must not edit it);
     - `run.commit`;
     - an onboarding step that a person runs before the instance (UC-0).
     Weigh the facts that the ADR-0115 function is not on main and its task is BLOCKED (T-0324, HQ-0032), and that ADR-0115 leaves its caller undecided. Say plainly what each choice makes P2-7 and P2-5 wait for.
   - (b) **From what**: whether the stored records are exactly the `hw_profile` and `op_signature` records `instance.json` states (ADR-0018, ADR-0031), or come from elsewhere. Also state what happens when `instance.json` states no `op_signature`.
   - (c) **When**: the order against the `instance.json` write (ADR-0025, ADR-0115), the first `STATE.json` (ADR-0120) and round 1's `case.write`.
   - (d) **The answers of a store that does not simply succeed**, each named with the `key_records` behaviour cited:
     - the key is already stored (another run of the same key);
     - it is stored with different attributes (`hw_source` or `label`); writing nothing and leaving the attribute question to OD-26 is the landed behaviour, not this record's to change;
     - a collision or a corrupt stored record;
     - a file-system failure;
     - the data root is not usable.
     Say what the run does then. If a tool is chosen, give its request, result, refusals and their order, and any new kind as a *name* of ADR-0001. Grep `hilclaw/`, `tests/`, `orchestration/` and `ARCHITECTURE/` on the day, and report equality with existing kinds as on purpose. Also say whether it journals (ADR-0124 decision 3 as precedent).
   - (e) **How they enter a commit** (ADR-0127 decision 4 and Boundaries). Options include taken in by `run.commit` with the round in which they were written, or a commit of their own. Weigh:
     - these files are created once and shared by every run of the key, so another run of the same key may have created them;
     - what a death between the store and the commit leaves;
     - the HQ-0043 point (ADR-0127 decision 8), which you must not answer.
   - (f) A **Walk-through** table with at least these rows:
     - a fresh key;
     - a key a previous run already stored, same attributes;
     - the same key with a different `hw_source`;
     - a collision;
     - a death between the store and the commit;
     - round 1's `case.write` afterwards.
3. **Not decided, said openly.** List these under Boundaries:
   - the general onboarding registry, its schema and storage, and endpoint, transport, quota and reservation description (#5 B-2, owner-only);
   - sim-only onboarding;
   - a smoke test;
   - history attribution between keys;
   - handling per `hw_source`;
   - the `hw_source` value of `cpu_standin` (ADR-0035 decision 8);
   - whether a stored attribute may be updated;
   - other accelerators;
   - whether the start of an instance is logged (OD-8 ⑧);
   - the caller of the start function (ADR-0115 decision 1) beyond what (a) needs;
   - HQ-0032;
   - HQ-0043;
   - `best.json` and `technique_stats.json` (OD-20, OD-7);
   - the lock and two writers of one key (OD-17);
   - runs outside ADR-0120 decision 1.

   Do not invent an owner decision.
4. **No data-plane schema change.**
   - No member, file, path, `events.ndjson` kind, value or version of a key record file, `instance.json`, `STATE.json`, the case file or any other data-plane file is added or changed.
   - Tool-failure kinds may be named. State the A-13 reading in Consequences, as ADR-0128 and ADR-0133 did.
   - If the design you judge right needs a data-plane change or a new external dependency, stop and return BLOCKED with the question.
5. **No earlier record is edited.** Consequences lists the earlier sentences that become less exact. Include at least:
   - ADR-0004 decision 5 ("whatever creates its directory … (OD-26)");
   - ADR-0127 decision 4's key-record sentence and its Boundaries item;
   - ADR-0133 Consequences ("A first-case run cannot store a case yet") and its Walk-through row for a missing key directory;
   - as observations, the `hilclaw/key_records.py` docstring ("registers no key on its own") and the docstrings or definitions the chosen code slices would touch.
6. **Code slices and runtime acceptance items.**
   - Consequences names the code slices this record makes possible, each testable with no `claude` or with a stub one (D16). Say which slice, if any, depends on the unlanded ADR-0115 function (PR #186, T-0324 BLOCKED by HQ-0032).
   - If a slice changes `hilclaw/run_commit.py` or `hilclaw/case_tool.py`, say that it changes landed behaviour and which tests pin it.
   - Name any new runtime acceptance item of the turn-session series. Number it after the highest number on `origin/main` (today (xxvi), ADR-0133) **and** on the branch `claude/T-0361-*` (which uses (xxiii) and (xxiv)), so start at (xxvii) unless that has changed. Say so in the Result.
7. **Register edits follow the recording rules written in those files, not earlier task files.**
   - `ARCHITECTURE/Requirements.md`: in row OD-26, and in OD-23, OD-8 or OD-4 only if the record answers part of them, follow the register's "행 형식":
     - add one link to ADR-0134 with a few words of topic after `**확정분**:`. Row OD-26 has no `**확정분**:` or `**잔여**:` yet, so give it the "행 형식" form in place, keeping its existing content as the proposal gist and its open points as `**잔여**:`;
     - no restatement of the record and no dated paragraph;
     - change the status word only as the 상태 어휘 and 갱신 규칙 paragraphs say.
   - `ARCHITECTURE/OpenDecisionProposals.md`: in section OD-26, and others only as in the item above, follow the header's "기록 규칙":
     - add one `- **채택분** [ADR-0134](…) — …` line;
     - rewrite in place the state at the end of the open point this record answers in part ("누가 언제 등록하는지" in the last bullet), leaving the question's wording;
     - no restatement and no dated note.
   - `ARCHITECTURE/StandardScenarios.md`: re-check S0, S1, S1-b and S6 by §검사 규칙. Record the result exactly as the first paragraph of §검사 결과 says (a re-check with no verdict change leaves no dated line there). The verdict notes name only open ODs.
8. **Doc mode.**
   - Run the reviewer cycle (dev-item-address steps 10 to 12).
   - Then rebase onto `origin/main` and push **one squashed commit** to `main` carrying `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0364`. Do not chain the rebase and the push in one command; check that the rebase finished before pushing.
   - Do not post to #5 yourself. Put in the Result the text of the DRIVER §9 owner notice (ending with `— posted by driver`) and any runtime acceptance HQ text, for the driver to post.

## Out of Scope

- Any change to code, tests, CI, prompts, agent definitions or settings, including `orchestration/`, `hilclaw/` and `.claude/`.
- ADR-0133 slice 2 (the promotion step in `orchestration/round-manager.md`; it is written with P2-1).
- The selection and lookup side (ADR-0132, T-0361).
- `best.json` and `technique_stats.json`.
- The general onboarding flow of UC-0.
- HQ-0031, HQ-0032, HQ-0040, HQ-0041 and HQ-0043, and every owner-only point (#5 A/B items, C-6, OD-25, OD-3).
- Editing earlier ADRs, FR or NFR text, UsageCases, the README or the index documents.
- Starting `claude`, or any program that needs a logged-in `claude`, a board or an API key (D16).

## Follow-ups

- Expected next for the planner: the code slice or slices the record names (for example a store step or tool and its test file, `default_registry`, and a `run_commit` change if (e) chooses it). After that comes ADR-0133 slice 2, with P2-1's round steps.

## Result

- **Outcome**: DONE. Document mode. ADR-0134 (`ARCHITECTURE/decisions/ADR-0134-od26-first-case-key-records-store.md`, 136 lines) landed on `main` as one squashed commit, 961dbfd (`Reviewed-by: reviewer agent (6 rounds, Approve)`, `Task: T-0364`), fast-forward from 302e435. The task branch was deleted locally and remotely. Before the push, ADR-0134 was confirmed free on `origin/main` and on every remote branch; ADR-0132 is only on `claude/T-0361-*`.
- **Review**: 6 context-isolated rounds (dev-reviewer, dev-code-review). Every round returned Approve, with Minor findings and nits.
  - Rounds 1 to 5: each finding was addressed. The fixes:
    - the walk-through row of another run's uncommitted files now names an earlier run that died;
    - ADR-0025 and ADR-0115 decision 2 are cited for the order;
    - the record now settles that `key.store` checks no scope, and the scope of a call outside ADR-0120 decision 1 is under Boundaries;
    - the builds-on list is complete (ADR-0010, ADR-0025, ADR-0115, ADR-0120 decision 3, ADR-0133 decision 2);
    - the "key is the pair" sentence is marked as this record's reading of FR-13 and ADR-0004 decision 5;
    - `key_not_written` now names the failing read of a stored record, and the case of a name taken during the write;
    - the record states that an uncommitted colliding record is committed as it is (no content inspected);
    - the OD-26 `**잔여**:` was completed.
  - Round 6: its two nits were not applied, to stay clear of the 7-round limit. One is that ADR-0025 sits out of number order in the builds-on list and References. The other is a test hint for the code slice (Follow-ups below).
- **What the record decides** (runs of ADR-0120 decision 1 only):
  - (a) Who and how: the Round-Manager stores the files inline, through a new registry tool `key.store` (`mcp__hilclaw__key_store`).
    - The request is exactly `run_id`. The result is `hw_profile_created` and `op_signature_created`.
    - Checks, in order: request; data root; `instance.json` (the four `run_file_*` kinds, widening ADR-0019 decision 2 as ADR-0124 did); `op_signature` stated (`op_signature_not_stated`, reused from ADR-0041 on purpose); `store_hw_profile`; then `store_op_signature`.
    - Failure kinds of the two stores: `key_record_invalid` (reused from ADR-0133) for a collision or a corrupt stored record, and the new kind `key_not_written` for any other failure.
    - It is not journaled and checks neither `STATE.json` nor the scope.
  - (b) From what: exactly the two records `instance.json` states. OD-8 ⑱ is not answered.
  - (c) When: as the first round step of every turn that carries a round, after the entry steps. A failure does not stop the round.
  - (d) Each non-simple outcome is answered and cited to `key_records`. A stored key with other attributes writes nothing and reports nothing; updating an attribute stays OD-26.
  - (e) The commit: `run.commit` takes in each record file that exists and that `HEAD` does not hold, with the run's next commit. This widens ADR-0127 decision 4; HQ-0043 is not answered.
- **Grep on 2026-10-20**: `key.store`, `key_store` and `key_not_written` occur nowhere in `hilclaw/`, `tests/`, `orchestration/` or `ARCHITECTURE/`. `op_signature_not_stated` (ADR-0041, `run_admission.py`, `check_admission.py`) and `key_record_invalid` (ADR-0133, `case_tool.py`) are reused with their meanings, on purpose.
- **Register**:
  - `Requirements.md`:
    - Row OD-26 now has the 행 형식 in place. ADR-0016 and ADR-0035 moved into `**확정분**:` and ADR-0134 was added. The open points became `**잔여**:`.
    - The OD-26 status changed from `미착수` to `논의중 (부분 답 2026-10-20 — PROCESS/DRIVER.md §9, 오너 통지 후 7일 이의 기간)`, the form of the OD-19 row.
    - Row OD-23: one `**확정분**` link was added.
    - OD-4 and OD-8 were not edited: the record answers no part of them.
  - `OpenDecisionProposals.md`:
    - OD-26 gained a `**채택분**` line. The open point "누가 언제 등록하는지와 …" now ends with `→ 부분 답: … 남음: …`, and "(상태 `미착수`)" was dropped.
    - OD-23 gained a `**채택분**` line.
  - `StandardScenarios.md`: S0, S1, S1-b and S6 were re-checked, with no verdict change and no gap. Only the 최근 재검사 line was rewritten. The OD-26 notes of S0 step 6 and S6 step 4 were narrowed to runs outside the first case.
- **Runtime acceptance items (new)**: (xxvii) and (xxviii). They are numbered after (xxvi) on `origin/main` (ADR-0133). The branch `claude/T-0361-*` uses (xxiii) and (xxiv), and no branch uses (xxvii).
  - HQ text for the driver (reason `runtime-acceptance`): "ADR-0134 (T-0364, main 961dbfd) adds two turn-session runtime acceptance items. **(xxvii)**: the main session of a `-p` turn session sees `mcp__hilclaw__key_store` and may call it under the means item (vii) gets. **(xxviii)**: a live Round-Manager calls `key.store` as the first round step of each turn that carries a round, before any other step of it, and goes on after a failure. Under D16 these are closed by the owner's check by hand or by the runtime's self-check; non-blocking."
- **DRIVER §9 owner notice**: not posted by the executor (AC 8). Text for the driver to post on #5:
  ```
  ### ADR-0134 accepted — T-0364: who stores the two key record files of a first-case run (part of OD-26 and OD-23)
  Under PROCESS/DRIVER.md §9 the driver accepted ADR-0134 (main 961dbfd; context-isolated review, 6 rounds, Approve). For first-case runs (ADR-0120 decision 1), the Round-Manager stores `db/<hw_profile_key>/hw_profile.json` and `.../<op_signature>/op_signature.json` itself through a new registry tool `key.store`. It stores exactly the two records the run's `instance.json` states, as the first round step of every turn that carries a round. `run.commit` takes the files into the run's next round-end commit where `HEAD` does not hold them. A stored key is never changed; whether a stored attribute (`hw_source`, `label`) may be updated stays open. This does not decide the onboarding registry (#5 B-2), the `hw_source` of `cpu_standin`, HQ-0032 or HQ-0043. OD-26 is now 논의중 (partial answer); OD-23 keeps its status. You may object within 7 days.
  — posted by driver
  ```
- **Overlap with unlanded branches** (none of their content was taken):
  - `claude/T-0361-*` (ADR-0132) edits the OD-23 row and the OD-23 section, and the 최근 재검사 line.
  - `claude/T-0231-*` edits the S6 row and the 최근 재검사 line.
  - `claude/T-0318-*` and `claude/T-0264-*` edit the 최근 재검사 line.
  - `claude/T-0210-*` edits only the OD-18 row.
  - None edits the OD-26 row or section. Whichever branch lands later needs a rebase on those lines.
- **Follow-ups**:
  1. Code slice: the tool `key.store` in a new `hilclaw/` module with its test file, registered in `default_registry`.
  2. Code slice (it may share a task with 1): the widening of `hilclaw/run_commit.py` by decision 7, with its docstring and tool description. This changes landed behaviour pinned by `tests/test_run_commit.py`. Reviewer hint: test that nothing owed means no record file is committed either, and that a record file `HEAD` holds is never taken again.
  3. Definition slice, with P2-1's round steps: the `key.store` step in "The round steps" of `orchestration/round-manager.md`.
