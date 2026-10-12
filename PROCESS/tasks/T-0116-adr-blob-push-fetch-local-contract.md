---
id: T-0116
title: Write the ADR that gives `blob.push` / `blob.fetch` their contract for the MVP's local implementation on one machine - as the repository owner answers the HQ of this task (what a local push and a local fetch do) - and reflect it in the ARCHITECTURE documents; no code
phase: P1
status: TODO
commitMode: doc
coversReq: [FR-10, C-3, "#5 A-2", "#5 A-3", "#5 B-2", OD-18, "#5 D6"]
dependsOn: [T-0008, T-0052]
touchesFiles: [ARCHITECTURE/decisions/, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]   # one new record under ARCHITECTURE/decisions/ with the next free number at execution time (ADR-0038 at planning time; the BLOCKED T-0088 also takes "the next free number at execution time"); nothing at all under answer (c)
estimatedSize: {loc: 200, files: 4}   # one new record of about 110-160 lines; the rest are in-place edits of a few lines each
hq: [HQ-0008]   # not to be executed before the repository owner has answered
---
## Why
PLAN P1-1 names six tools: `sim.run`, `board.run`, `profiler.collect`, `correctness.check`, `blob.push`, `blob.fetch`. The frame they share is on `main` (ADR-0010, ADR-0015, ADR-0016 and their code slices), and the first part of `correctness.check` is recorded (ADR-0021). The rest of the four HW tools waits on HQ-0005 (T-0088). **This task is the blob pair**, the only part of P1-1 that HQ-0005 does not hold. It ticks **no PLAN checkbox**: P1-1 stays open at least until HQ-0005 is answered.

What the fixed inputs carry (the repository owner's own words, #5 A-2 supplement 1 and #5 A-3, mirrored in Requirements C-3):
- The interface is fixed: a two-function contract `blob.push(hash)` / `blob.fetch(hash)`.
- "MVP(단일 머신, C-2)는 로컬 구현." When the access to the board farm (#5 B-2, open) is decided, an rsync / S3 / in-house storage backend is plugged in.
- `blob.push` is never called automatically; it runs on a user command (#5 A-3).

What they do not carry: **what a local push and a local fetch do** on one machine, where the only store is `<data_root>/blobs/sha256/` (`hilclaw/cas.py`, T-0008) and no second place exists that a blob could be pushed to or fetched from.

**Why it cannot start without the repository owner** (planner, 2026-10-10 UTC, from the files at `main` `8a68141`):
- Two accepted records file exactly this point as owner-only: ADR-0005 Boundaries ("`blob.push` / `blob.fetch` (#5 B-2, #5 A-3): their meaning on one machine, their backend, and any "pushed" or "location" member of a record", with #5 B-2 in its owner-only line) and ADR-0016 context and Boundaries ("their meaning on one machine and their store (#5 B-2, A-3 - owner-only)"). ADR-0004 Boundaries lists it as open under C-3 / #5 B-2.
- T-0008 (the local store) left it out with "C-3 says the MVP has a "local implementation" but not what a local push or fetch does; do not guess it here". T-0056 `## Follow-ups` recorded: "(owner question, to be raised as an HQ when a planner reaches the blob pair - not blocking this task) What `blob.push(hash)` and `blob.fetch(hash)` do in the MVP's local implementation on one machine". The question was never put.
- The planner has reached the pair now: every other open slice of P1-1 is held by HQ-0005, and the planners of T-0104 and T-0115 listed the pair as "waits on #5 B-2" without raising the question.
- DRIVER §9 puts #5 A and B items on the owner-only list, so the planner may not close the point by an ADR of its own, and it does not choose among the readings (CLAUDE.md "미결은 발명하지 않는다"; BLOCKED reason "owner-only decision").

Once the meaning is given, the rest - the request and result members of the two tools, their failure kinds, whether they are journaled - is the design of a tool contract inside the frame of ADR-0015, which that record leaves to "each tool" and which is design-level under DRIVER §9 (OD-18 is not on the owner-only list). That part is this task's record.

## HQ question
(for the driver to record under DRIVER §8; reason `owner-only-decision`)

PLAN P1-1 names `blob.push` / `blob.fetch`, and your decisions fix their frame: a two-function contract `blob.push(hash)` / `blob.fetch(hash)`, a local implementation in the MVP (one machine, C-2), a storage backend plugged in once #5 B-2 is decided (#5 A-2 supplement 1), and no automatic push - `blob.push` runs on a user command (#5 A-3). No input says what a local push and a local fetch do on one machine, where the only store is `blobs/sha256/` under the data root; ADR-0005 and ADR-0016 filed that as yours, and it was never asked. (1) What does the MVP's local implementation do: (a) nothing is copied - the local store is the only store; `blob.push(hash)` and `blob.fetch(hash)` each look at the local store and answer whether a blob of that hash is there (whether the content is also re-hashed is left to the record); (b) there is a second store on the same machine, a directory outside the data repository that the user names - `blob.push(hash)` copies the blob from `blobs/sha256/` to it, and `blob.fetch(hash)` copies it back when it is missing locally; (c) the pair is put off - no `blob.push` / `blob.fetch` tool is written until #5 B-2 is answered, and PLAN P1-1 does not wait for the pair; (d) something else (say what each of the two does)? (2) Only under (1)(b): where does the user name that directory - (a) a new member of `hilclaw.config.json` with an environment override, in the manner of `data_repo.local_path` (#5 A-1 detail 2); (b) you leave the place to the record; (c) another place (name it)? Not asked here: the board farm access and the remote backend (#5 B-2), retention, GC and `gc_at`, any "pushed" or "location" member of `artifacts.json`, who may call the pair (OD-23), and the request and result members and failure kinds of the two tools (the design of the record, under review).

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, commit trailers) - mandatory for every task (§6)
- PROCESS/DRIVER.md §0, §1-5 (Bypass permissions; the forbidden actions; a denied or failed tool call is BLOCKED, never worked around), §3 "BLOCKED 사유" paragraph, §8, §9
- **The repository owner's answer to the HQ of this task** in `PROCESS/STATE.json` (`humanQuestions`, the entry whose `taskId` is `T-0116`: `decision`) and the comment it links on issue #5. **If that entry has no `decision`, do not start: return BLOCKED.**
- CLAUDE.md - whole file; in particular "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "브랜치·merge 절차" (document mode, the `Reviewed-by` trailer)
- Issue #5: the comments "A-2 확정 (2026-07-23)" (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5495860612) and "A-3 확정 (2026-07-23)" (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5537233759), the body item B-2, and every comment newer than the HQ mirror of this task
- ARCHITECTURE/Requirements.md: C-2, C-3, FR-10, NFR-2, and the register rows OD-18 and OD-8 (search the long OD-8 row for `blob` instead of reading it whole)
- ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md - decisions 1 to 4 (tool function, the two fronts, the name table with `mcp__hilclaw__blob_push` / `mcp__hilclaw__blob_fetch`, result versus tool failure) and Boundaries
- ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md - whole (the registry entry, `invalid_request`, the data root source and `no_data_root`, which members a request about a run carries, the journaled path); ADR-0016 - decision 3 ("`blob.push` and `blob.fetch` are not HW tools", the two reserved kinds they must not reuse) and Boundaries
- ARCHITECTURE/decisions/ADR-0005-od8-artifacts-record.md - decisions on what a record asserts and Boundaries; ADR-0004 - decision 1 (the row of `blobs/sha256/<hh>/<hash>`) and Boundaries
- ARCHITECTURE/decisions/ADR-0037-od6-gemm-contract-zero-dimension.md and PROCESS/tasks/T-0112-adr-od6-gemm-contract-zero-dimension.md (`## Acceptance Criteria` "Process" part and `## Result`) - the form of a record, of the register edits, of the coverage re-check and of the owner notice as the latest §9 record landed them
- Read only, to describe what exists and not to change: `hilclaw/cas.py` (`blob_path`, `put_bytes`, `put_file`, `has_blob`, `verify_blob`, `BlobNotFoundError`), `hilclaw/tools.py` (`ToolDefinition`, `Registry`, `default_registry`, the reserved kinds), `hilclaw/data_root_source.py`, `hilclaw/config.py`, `hilclaw.config.json`
- ARCHITECTURE/StandardScenarios.md - the checking rules and the steps that name `blob.fetch` (lines 149, 157, 172 at planning time)
- .claude/skills/dev-item-address/SKILL.md (document mode: steps 9 to 12 and 15) and .claude/skills/dev-code-review/SKILL.md (document-mode return path; the "no invented decisions" check)

## Acceptance Criteria
### By the answer
- Answer (1)(c): change nothing. Write "put off (owner answer)" with the link of the answer into `## Result` and return; no branch, no commit. Name in `## Result`, for the integrator, that PLAN P1-1 then no longer waits for the pair (the PLAN text is not edited here).
- Answer (1)(a), or (1)(b) with (2)(a) or (2)(b): write the record described below.
- Answer (1)(d), (2)(c), an answer that fits none of these, or an answer that brings in a new external dependency, a network, or a new member of `artifacts.json` (a data-plane schema change): do not write the record. Return BLOCKED ("task needs re-planning") quoting the answer; the planner rewrites this file.

### The record (one new file `ARCHITECTURE/decisions/ADR-NNNN-od18-blob-push-fetch-local.md`, next free number at execution time)
- English; the sections of ADR-0037 (Status, Context, Decision, Walk-through, Alternatives considered, Consequences, Boundaries, References). **Every sentence says whose it is**: the owner's (cite #5 A-2, A-3 or the answer to this HQ by link), a cited record's, or the record's own. The meaning of a local push and a local fetch is quoted from the answer and is **not** widened, narrowed or interpreted beyond its words; where the answer leaves a case open, the record registers a sub-question instead of choosing, unless the case is plainly a matter of form.
- Status: accepted under DRIVER §9 (D6) by reviewer approval, the UTC date, the objection window of 7 days, and which earlier records it builds on and falls with.
- The record decides, as its own design inside the frame of ADR-0015 and for the MVP's local implementation only:
  1. What a call of each tool is: the request members (the hash in the form `hilclaw.cas` uses - 64 lowercase hexadecimal characters; whether anything else is carried), what makes a request `invalid_request`, and that the data root comes from the bound source (`no_data_root`), never from the request.
  2. What each tool answers: which outcomes are **results** (ADR-0010 decision 4: an outcome the tool exists to report) and which are **tool failures**, with the names of any kind of its own; in particular the answer for a hash the local store does not hold, and for a stored file whose content does not match its name if the record has the tools re-hash.
  3. Whether the two tools are journaled steps of a run (ADR-0015 decision 5) or calls outside any run. Weigh that the request of the owner's contract carries a hash only, that #5 A-3 makes `blob.push` a user command, and that a hash may be recorded by several runs (ADR-0005). If the answer cannot be had without deciding who calls the pair (OD-23), register the sub-question and state the smallest rule that does not depend on it.
  4. That the pair reads and writes no `artifacts.json`, changes no retention class, deletes nothing, and never runs `git`; and what it guarantees beyond the death of the process (nothing more than `hilclaw.cas` does today, unless the answer says otherwise).
  5. Under (1)(b) only: the directory layout of the second store (the same `sha256/<hh>/<hash>` layout or another), what a copy guarantees when the process dies midway (no partial file under a final name - cite the technique `hilclaw/cas.py` uses), what a push answers when the second store already holds the blob, what a fetch answers when neither store holds it, and what a call answers when the directory is not named or does not exist. Under (2)(a) the member name and the environment variable are the record's own and are stated as provisional; under (2)(b) the place is the record's own choice, with the alternatives named.
  6. How the later remote backend (#5 B-2) relates: the record says only that the contract of points 1 to 3 is meant to hold unchanged when a backend is plugged in (the owner's "어댑터만 꽂는다"), and decides nothing about that backend.
- A walk-through of at least four calls with their answers (a blob present; a blob absent; a malformed hash; no data root), plus the cases of point 5 under (1)(b).
- Boundaries, at least: the remote backend and how it is reached (#5 B-2); retention, GC, `gc_at`; any "pushed" or "location" member of a record; who may call the pair and whether an agent ever does (OD-23, #5 A-3); visibility of unpushed blobs in a STATE summary (#5 A-3 "설계 귀결"); datasets (#5 B-8); OD-25.
- A "Consequences" line that cuts the code slice for the next planner (the two tool functions, their registration in `tools.default_registry`, tests through both fronts), without writing any code.

### Edits of existing documents (same commit)
- `ARCHITECTURE/Requirements.md`: one clause in the OD-18 row in the manner of the earlier "확정분" clauses (the status word of the row unchanged), and any new sub-question registered there. C-3 is **not** reworded (the owner's decision text); if its sentence is now less exact, name it in `## Result` for the integrator.
- `ARCHITECTURE/OpenDecisionProposals.md`: one "채택분" bullet under OD-18, a few lines.
- `ARCHITECTURE/StandardScenarios.md`: the coverage re-check of CLAUDE.md, applied to every step that names `blob.push` or `blob.fetch`; update the result section with the date and the outcome. A verdict changes only if the rules of that file say so; do not edit a scenario step.
- ADR-0004, ADR-0005, ADR-0010, ADR-0015 and ADR-0016 are not edited; sentences of theirs that become less exact are listed in the record and in `## Result`.

### Do not invent
- No statement about the remote backend, its protocol, credentials or a network. No retention or GC rule. No new member of `artifacts.json`, `instance.json`, `STATE.json` or an event. No rule on who calls the pair.
- If, while writing, a point turns out to need the repository owner beyond the answer (for example the answer's words fit two readings that give different tools), do not decide it: land nothing and return BLOCKED ("requirement unclear") with the exact question.

### Document checks (document mode replaces tests; list each with its outcome in `## Result`)
- Every relative link of the new record and of the edited passages resolves; the ADR number is free on `origin/main` at the push.
- `git diff --stat origin/main` shows only files of `touchesFiles`; no file under `hilclaw/`, `tests/`, `.github/`, `.claude/` or `PROCESS/` is in the commit.
- Each sentence of the Decision section is marked as the owner's, a cited record's or the record's own, and each citation was checked against its source.
- The coverage re-check outcome (verdict changes, gaps) is stated.

### Process
- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0116'`; then the session entry check of CLAUDE.md (`gh pr list --repo myungjoo/HIL-Claw --state open`, issues #4, #5, #7, #8). An open PR that edits the OD-18 row or a file of `touchesFiles` is BLOCKED ("open PR conflict").
- Document mode (CLAUDE.md A-13): branch `claude/T-0116-adr-blob-push-fetch-local-contract`; the reviewer cycle of dev-item-address steps 10 to 12 with a fresh-context `dev-reviewer` each round (at most 7 rounds; past the cap without a final Approve, return BLOCKED; a result starting with `SECURITY` is BLOCKED; if no reviewer can be spawned, return BLOCKED - do not self-review). Ask the reviewer explicitly to (a) compare the meaning the record gives the pair with the owner's answer word for word; (b) look for a sentence that decides something on the "Do not invent" list; (c) re-check that points 1 to 5 stay inside the frame of ADR-0015 and reuse no reserved kind with another meaning; (d) re-check each provisional choice.
- Then rebase on `origin/main` and push to `main` without a PR. Commit message: English; subject starts with `T-0116:`; trailers in this order: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0116`, then any attribution trailer your session requires.
- **Owner notice (DRIVER §9)**: do not post it yourself unless the driver's spawn prompt tells you to. Put the ready-to-post English text in `## Result` in the form of the ADR-0037 notice (what was decided, what is the owner's answer and what is the record's own design, the provisional choices, the objection window).
- Never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`; no edit of `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call is BLOCKED, not worked around. Delete the task branch only after the push to `main` is confirmed, remote and local in separate commands.
- `## Result`: fill it in after the push, on `main`, and leave that edit uncommitted for the driver (DRIVER §3-6). No fenced code block in it. Record: the owner answer followed (with its link), the commit, review rounds and findings, the contract as landed (a code slice is written against it), the provisional choices, the document checks, the notice text, the follow-ups. `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters (result, commit, BLOCKED or not).

## Out of Scope
- Any code: the two tool functions, their registration, a change of `hilclaw/cas.py`, `hilclaw/config.py` or `hilclaw.config.json`, tests, a JSON Schema file (the code slice follows this record as its own task).
- The remote backend and #5 B-2; retention, GC, `gc_at`; `artifacts.json`; the roster (OD-23); OD-25; datasets (#5 B-8).
- Anything HQ-0005, HQ-0006 or HQ-0007 asks; the contracts of the four HW tools.
- Editing C-3, PLAN P1-1, earlier records, or the `HIL-Claw-data` repository.

## Follow-ups
- (planner, after this record - code mode, P1-1) The code slice of the record: the tool functions of `blob.push` / `blob.fetch`, registered in `tools.default_registry` (the first registered tools of the package - the README layer-2 cell then goes stale, T-0115 `## Result`), tests through both fronts.
- (integrator) Under answer (1)(c): the text of PLAN P1-1 and of C-3 ("MVP 로컬 구현") against the owner's answer.
- (driver / owner) HQ-0005 (T-0088): the rest of PLAN P1-1. HQ-0006 (T-0106): the live check of the MCP front. HQ-0007 (T-0107): the forbidden-command guard and the hook registration of PLAN P0.5-4. PLAN P1-5: `task.objective` (#5 A-4).
- (planner - not before 2026-10-16, code mode, no change of behaviour) One shared once-only write helper for the three writers (`key_records`, `instance_file`, `spec_file`) (T-0094 `## Result`).
- (planner - judged and not planned on 2026-10-10) OD-13 sub-questions 7 and 8, OD-16 sub-questions 1 and 6, OD-18 sub-questions 2, 3, 5, 10 and 11: each has no caller before HQ-0005 is answered or is tied to OD-23 / OD-14 / OD-10; re-judge when the contracts of `sim.run` / `board.run` exist.

## Result
