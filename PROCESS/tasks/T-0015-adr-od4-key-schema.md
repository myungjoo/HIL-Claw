---
id: T-0015
title: Write ADR-0001 closing the P1 minimum of OD-4 (hw_profile / op_signature key schema) and reflect it in the ARCHITECTURE documents
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [OD-4, FR-13, FR-7, FR-14, "#5 D6", "#5 B-4"]
dependsOn: []
touchesFiles: [ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/UsageCases.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 180, files: 5}   # one new record of about 130 lines, the rest are in-place edits of a few lines each
hq: []   # OD-4 is a design-level OD (DRIVER §9, D6): closed by an ADR + reviewer Approve + owner notice, not by an HQ
---
## Why
Requirements names three decisions that must be closed before the layer-2 code that depends on them: OD-4 (key schema), OD-6 (coder spec) and OD-8 (P1 directory layout). Their owner inputs (#5 A-1, A-2, B-4) have all been given; what remains is the design decision. Owner decision D6 (2026-10-05, DRIVER §9) gives the driver the authority to close such **design-level** ODs: the executor writes a decision record (ADR), a context-isolated reviewer approves it, the OD register is updated, and the owner is notified on #5 with a 7-day objection window.

OD-4 is the root of that chain. FR-13 already fixes that cross-run knowledge is stored under `db/<hw_profile_key>/<op_signature>/...`, but nothing says which fields make up either key or how a field set becomes a directory name. The open PLAN items that can still be planned all wait for it:
- P1-5 (GEMM spec example and `spec.json` schema, OD-6): the spec carries a kernel description and an hw_profile, both of which are instances of these keys.
- P1-8 (runtime STATE / instance / events schemas, OD-8): the layout uses both keys as path levels, and the OD-8 row says it reflects the result of OD-4.
- P1-1 (FR-10 tool contract): two earlier planning rounds found that the request shapes cannot be written without the hw_profile identity (journal 2026-10-06).

This task is therefore **a prerequisite slice shared by P1-5 and P1-8**: the ADR that closes the **P1 minimum** of OD-4, plus the edits that keep the ARCHITECTURE documents consistent with it. It ticks no PLAN checkbox. No ADR exists yet, so this is also the "first need" at which CLAUDE.md says the ADR form and location are settled.

Why this item now (planner's judgement, DRIVER §6): every P0.5 item is DONE, BLOCKED or waiting on something that is not a task — the rest of P0.5-1 (C gate) waits for P1-2 / P1-3, P0.5-3 is BLOCKED on HQ-0003, and the rest of P0.5-4 is the owner's hook registration. In P1, P1-3 is marked "owner confirmation needed" and P1-4 depends on it; the rest of P1-2 needs the kernel calling convention (P1-3 / P1-5); the rest of P1-6 needs OD-8. §6 says a task that needs a design-level OD is created with the ADR in its scope; the size cap makes the ADR its own first slice.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, naming `T-NNNN`, resume rule, 2h30m limit) and §5 (task format, size cap D4, commit trailers) — mandatory for every task (§6)
- PROCESS/DRIVER.md §0 last bullet, §1-5 (Bypass permissions run mode; forbidden actions held by discipline; "a denied or failed tool call is BLOCKED, never worked around"), §3 "BLOCKED 사유" paragraph, §8 (the driver tail on #5 comments), **§9 (the whole section: what is owner-only, what the driver may close, the notice and the 7 days)**, §11 rows D6 and D9
- CLAUDE.md — 상시 규칙: "문서 커버리지 재검사", "미결은 발명하지 않는다" (register one line, proposal text in OpenDecisionProposals.md), **"세션 진입 점검"** (do it before the first edit: `gh pr list`, issues #4, #5, #7, #8), "세 층 모델", "브랜치·merge 절차" (document mode), "코멘트 최소화"
- .claude/skills/dev-item-address/SKILL.md — the procedure to follow (document mode: steps 2, 7, 9-12, 15); .claude/skills/dev-code-review/SKILL.md — what the reviewer checks (in particular "no invented decisions")
- ARCHITECTURE/Requirements.md — rows FR-1, FR-7, FR-13, FR-14, FR-15, NFR-2, NFR-6, NFR-7, C-2, C-3, C-6, C-7; the whole "Open Decisions" preamble (status vocabulary, update rule, canonical rule, the "first commit" sentence); register rows **OD-4**, OD-5 and OD-11 / OD-16 (the two existing ways a partly decided OD is recorded), OD-6, OD-8, OD-9, OD-25, OD-26
- ARCHITECTURE/OpenDecisionProposals.md — the header (lines 1-9) and sections **OD-4**, OD-6, OD-8, OD-26
- ARCHITECTURE/UsageCases.md — the glossary entries hw_profile, op_signature and "HW 출처(hw_source)" (lines 25-29), UC-0, UC-E4
- ARCHITECTURE/StandardScenarios.md — "검사 규칙", S1-b, S6, S10, and "검사 결과" (the table rows that cite OD-4)
- Issue #5 comments (owner inputs; they are the fixed part of this decision): B-4 `gh api repos/myungjoo/HIL-Claw/issues/comments/5944412285 --jq .body`; A-7 `.../comments/5944117402`; B-6 `.../comments/5944087839`; A-12 `.../comments/5946779596`; D6 `.../comments/5986348506`. Also the issue body, items B-1, B-5 (both unanswered)
- Issue #4 (`gh issue view 4 --repo myungjoo/HIL-Claw --json body,comments`) — body §2a, §2c ("owner/project are meta fields, not path levels"), the "합의 레이아웃" block, §4 item "OD-4/OD-8"; the comment table row "OD-4 키 스키마"
- Issue #7 (`gh issue view 7 --repo myungjoo/HIL-Claw --json body,comments`) — the parts cited by the OD-4 proposal: S-1 §6, the TVM MetaSchedule database row, note N7
- Existing files for conventions only: `hilclaw.config.json`, `hilclaw/cas.py` docstring (how the data repository root and a fixed path rule are described), PROCESS/tasks/T-0006-dev-process-agent-definitions.md `## Result` (a landed document-mode task)

## Acceptance Criteria
What is **fixed** and must be taken as input, not re-decided:
- FR-13: cross-run knowledge lives under `db/<hw_profile_key>/<op_signature>/...` in the data repository, and the layout mirrors the future DB schema. #4 §2c: owner and project are meta fields, not path levels.
- UsageCases glossary: hw_profile is the tuple "accelerator + host environment"; `hw_source` is an attribute of it with two values, external vendor / in-house under development (owner, 2026-09-03).
- #5 A-7, B-4, B-6: the first hw_profile is `cpu_standin` (C + clang, OpenMP / SIMD allowed; the owner's local PC under WSL first, a LAN machine later); the first operations are the Llama 3.2 1B projection GEMMs — gate/up 2048→8192, down 8192→2048, QKV 2048→3072, O 2048→2048 — with M ∈ {1, 32, 512} **as an instance parameter**, dtype fp32; the second family is SDPA with KV cache.
- FR-15: stored past cases are hints, never ground truth. C-7: everything behaves the same on Linux, macOS and WSL.
- NFR-7 ②: persistent artefacts carry a `schema_version`.

What the ADR **decides** (the P1 minimum of OD-4). The content of each decision is the executor's to work out and justify from the fixed inputs and the registered proposal (OpenDecisionProposals OD-4); the reviewer's Approve is what confirms it. For every point give the choice, the alternatives considered and one or two lines of reason:
1. **Exact-identification fields of `hw_profile`**: name, type, meaning and required / optional for each field, covering at least the accelerator identity, the host environment, `hw_source`, a revision, and the toolchain version (the proposal's reason: without the toolchain version a cached result cannot be invalidated). Say which fields are part of the **key** and which are descriptive attributes that do not change the key.
2. **Exact-identification fields of `op_signature`**: the same, covering at least operation kind, shape parameters, dtype and layout. Decide explicitly **whether M (the token count, an instance parameter) is part of the key** or a dimension below it, and state the consequence of that choice for `db/` (one directory per M, or one per projection) and for FR-7 statistics.
3. **Canonical form and key derivation**: one deterministic canonical serialisation of a field set, and the rule that turns it into the directory names `<hw_profile_key>` and `<op_signature>`. The names must be valid and distinct on case-sensitive and case-insensitive file systems, use a portable character set, have a stated length bound, and be reproducible by any tool from the field values alone. State how a human reads a key back (the name itself, or a record that must exist beside it — see the OD-8 boundary below).
4. **Matching rule in P1**: what counts as "the same (hw_profile, op_signature)" for a lookup. The registered proposal is exact match = hit, nearest neighbour = prior only.
5. **What makes a new key**: which field changes produce a new key (for example a toolchain version bump on `cpu_standin`) and which do not.
6. **Versioning** of the key schema itself (NFR-7 ②), and how the schema leaves room for fields of hardware that is not known yet.
7. **The first concrete instance**, written out as an example with the canonical form and the two resulting directory names: `cpu_standin` × one of the B-4 GEMMs. Every value must come from a cited source. A value no source gives is written as an explicit placeholder with the note "not decided here" — never a plausible guess.

What the ADR must **not** decide — name each as a boundary in the record, with the place where it is decided:
- Owner-only items (DRIVER §9): anything that needs #5 B-1 (target NPU and its toolchain — the schema may leave extension points, it may not name vendor fields), #5 B-5 / OD-9 (whether there is a frontend IR: a "normalised IR structure hash" from the proposal cannot be a required field, because no IR exists in the MVP), OD-25, OD-3, C-6.
- The **memory layout value** of the first GEMM instance: B-4 does not give it, and "row-major" in the OD-4 proposal is marked as the integrator's assumption. The schema may have a `layout` field; its value for the example is a placeholder (criterion 7). Record this as a question for the task that writes the spec example (P1-5).
- OD-8: where under the data repository a key's full field record is stored, file names, and anything else about the directory tree beyond the two path levels FR-13 already fixes.
- OD-26: the onboarding registry schema, how history is attributed when an in-house HW revision changes, sim-only onboarding.
- OD-6 (what of the keys goes into `spec.json`), OD-7 (statistics), OD-13 (measurement), and the **similarity-vector layer** of the OD-4 proposal (FLOPs, bytes moved, arithmetic intensity, …) together with nearest-neighbour ranking: no P1 code needs them. They stay registered as open.
- Any code, JSON Schema file or validator (later code tasks implement the record this ADR describes).

If a point of 1-7 cannot be written without one of the excluded items, do not fill the gap: return BLOCKED ("design choice needing an owner-only decision" or "requirement unclear") with the exact question (DRIVER §3, §9).

The record (`ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`, new; location as proposed in DRIVER §9):
- This is the first ADR, so its form is set here. Provisional conventions of this task, to be stated in one short closing section of the record ("Record format") so that the next ADR can follow them without a separate file: file name `ADR-NNNN-<slug>.md` with a four-digit running number; sections **Status**, **Context**, **Decision**, **Alternatives considered**, **Consequences**, **Boundaries (not decided here)**, **References**; one decision per record; a superseded record is kept and marked, never deleted (NFR-2).
- **Status** says: accepted under DRIVER §9 (D6) by reviewer approval, the acceptance date, the OD it closes and to what extent, and that the owner may object on #5 within 7 days of the notice, in which case a reverting task is created. Do not write that the owner confirmed it.
- **Language**: write the new record in English (the owner's standing rule for documents that enter the repository). In-place edits of the four existing documents keep the language of the text around them (Korean), as every edit of those documents has done so far. Record this split in `## Result` as provisional.
- Length: enough to be executable by the author of a later schema task without reading the issues again; about 100-150 lines. Tables for the field lists.
- **References** cite the sources by stable handle: Requirements IDs, issue comment URLs, the proposal section.

Edits of existing documents (same commit as the record — register update rule):
- `ARCHITECTURE/Requirements.md`, row **OD-4** only, plus the sentence "첫 커밋(P0 골격) 전에 확정해야 하는 항목" if it must mention that OD-4's P1 minimum is closed. Keep the row to one line. How the partial closure is shown, following the two precedents in the register: use status `확정` with the remaining open part listed as "잔여" (as the OD-5 row does) **only if** the record decides both things the row names — the key field schema and the matching rule for P1; otherwise keep `제안됨` and add a "**확정분**" note (as the OD-11 and OD-16 rows do). Say in the commit body which precedent you followed and why. The row must point to the record by path. The register asks for a link to the reflecting commit, which a single squashed commit cannot contain for itself: point to the record's path in the row and give the commit hash in `## Result` (Follow-ups has the entry for adding the hash). Do not renumber, add or remove any OD row.
- `ARCHITECTURE/OpenDecisionProposals.md`, section **OD-4**: mark which parts of the proposal the record adopted (link to it) and which remain proposals (similarity layer, S10 extension note). Do not delete proposal text. The header line 6 says confirmation is made by the owner on #4 / #5; D6 added the §9 route — amend that one line minimally to mention it, citing DRIVER §9, and change nothing else in the header.
- `ARCHITECTURE/UsageCases.md`: the two glossary lines that call the field schema of hw_profile and op_signature undecided now point to the record for the P1 minimum and to OD-4 for what remains. No other change; UC-0 and UC-E4 keep their OD-4 / OD-26 references unless a sentence has become false.
- `ARCHITECTURE/StandardScenarios.md`: re-run the coverage check (CLAUDE.md "문서 커버리지 재검사") with the document's own rules for every scenario step that cites OD-4 (S1-b, S6, S10 and any other the search finds), and update the "검사 결과" section: heading date / note and the affected rows. A step whose remaining detail is still a registered OD stays "지원(미결)". State the outcome of the re-check in the commit body even if no verdict changes.
- No edit to `CLAUDE.md`, `README.md`, `PROCESS/DRIVER.md`, `PROCESS/PLAN.md`, the skills, the agents, or any file under `hilclaw/`, `tests/`, `.github/`.

Tests:
- None. Document mode: no code changes, so CLAUDE.md test rules ①-④ do not apply and rule ⑤ forbids nothing here. The document checks below replace steps 4, 6 and 8 of dev-item-address.

Document checks (record the outcome of each in `## Result`):
- Session-entry check done before the first edit: `gh pr list --repo myungjoo/HIL-Claw --state open` (the planner saw none on 2026-10-06T12:20Z) and issues #4, #5, #7, #8 read for anything newer than this task file about OD-4, OD-8 or key schemas. If an open PR edits the OD register or the OD-4 sections, stop and return BLOCKED ("open PR conflict").
- Every relative link in the new record and in the edited lines resolves to an existing file or anchor (`ARCHITECTURE/decisions/` is one level below `ARCHITECTURE/`).
- OD numbers: `git diff origin/main -- ARCHITECTURE/Requirements.md` touches the OD-4 row (and at most the "first commit" sentence); the count and numbering of register rows are unchanged.
- The example in criterion 7 is reproducible: applying the record's own derivation rule by hand (or with a throw-away snippet that is not committed) to the example's field values gives exactly the two directory names printed in the record.
- Nothing in the record states an excluded item as decided; every value in the example has a source or is a marked placeholder.
- `git ls-files --eol` shows `i/lf` for the five files; `git diff origin/main --stat` lists exactly the five files in `touchesFiles`.
- CI is not a gate for document mode, but the push to `main` triggers the workflow: check the `push` run with `gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"` and record its conclusion; if it is not `success`, do not fix forward — record it and say so in the returned summary.

Process (document mode, CLAUDE.md A-13, dev-item-address steps 9-12 and 15):
- Branch `claude/T-0015-adr-od4-key-schema` from `origin/main`. Commit and push the branch; **no PR**.
- Reviewer cycle: spawn a fresh-context `dev-reviewer` sub-agent, give it the branch name (review target = diff against `origin/main`) and this task file's path, and receive the verdict and findings as its return value. Ask it explicitly to check (a) that no owner-only or excluded item is decided, (b) that each decision follows from a cited source or is argued as a design choice with alternatives, (c) the register and coverage-check updates. Address findings and re-request review until Approve with nothing trivially fixable left; more than 7 rounds is BLOCKED. A result starting with `SECURITY` is BLOCKED. If you cannot spawn a reviewer, return BLOCKED — do not self-review.
- Landing: `git fetch origin`, rebase the branch onto `origin/main`, then squash to **one** commit (`git reset --soft origin/main` + commit — only after the rebase). `git show --stat HEAD` must list exactly the five files. If the rebase needed conflict resolution that changed content, go back to review.
- Commit message: English; subject starts with `T-0015:`; the body gives the decisions 1-7 in one line each, the boundaries, which register precedent was followed, the coverage re-check outcome and the provisional ADR conventions; it ends with the trailers, in this order: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0015`, then any attribution trailer your session requires.
- Push with `git push origin HEAD:main` (fast-forward). If rejected because `main` moved, fetch, rebase and retry (at most 3 times); never `git push --force*`, and never push the rewritten branch back to its remote branch. Delete the remote branch and the local branch in separate commands after the push is confirmed, then check out `main` at `origin/main`.
- **Owner notice (DRIVER §9)**: do not post it yourself — the driver is the notifier (DRIVER §7, §8). Put the ready-to-post English text in `## Result`: what was decided in five lines or fewer, the record's path and commit, the boundaries left open, and the date on which the 7-day window ends. The driver posts it on #5 with its tail.
- `## Result`: fill it in **after** the push, on `main`, and leave that edit to this task file **uncommitted** — the driver commits it in its wrap-up (DRIVER §3-6). The landed commit must not contain the task file. Record: commit hash, review rounds and findings with how each was handled, the decisions with their reasons, the boundaries, the document-check outcomes, the notice text, follow-ups.
- `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver. This task ticks **no** PLAN checkbox.
- Size: one new file of about 130 lines and four small edits; within 300 LOC / 5 files. If consistency turns out to need a sixth file, do not exceed the cap: finish the five, and list the sixth as a proposed follow-up (DRIVER §5).
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, commit, BLOCKED or not).

## Out of Scope
- Closing or changing any OD other than OD-4, and any part of OD-4 beyond the P1 minimum (similarity layer, nearest-neighbour matching, the S10 "environment change as a new key candidate" note).
- The data-plane directory layout, file names and record locations (OD-8, P1-8); `spec.json` (OD-6, P1-5); the onboarding registry (OD-26); `instance.json`.
- Code: a key module in `hilclaw/`, a JSON Schema, a validator, tests. Any write to the `HIL-Claw-data` repository.
- An ADR index or template file, a pointer to `ARCHITECTURE/decisions/` in CLAUDE.md or README.md, and the CLAUDE.md sentence "ADR 양식·위치는 첫 필요 시점에 정한다" (integrator, separate document-mode change — see Follow-ups).
- Posting on GitHub issues (the driver posts the owner notice), editing the body of issue #4 (its §4 checklist).
- Answering #5 B-1, B-5 or the layout question on the owner's behalf.

## Follow-ups
- (driver, after the wrap-up push) Post the §9 owner notice on #5 from the text in `## Result`, with the driver tail.
- (driver or integrator, document mode) Add the landed commit hash to the OD-4 register row, which the squashed commit could not contain.
- (integrator, document mode) Point CLAUDE.md ("ADR 양식·위치는 첫 필요 시점에 정한다") and README at `ARCHITECTURE/decisions/` and at the record format set by ADR-0001; decide whether the format moves into a README of that directory.
- (planner, next) P1-5 slice: `spec.json` schema + GEMM spec example with an ADR closing OD-6, using these keys. Open point to settle before that task: the memory layout of the first GEMM instance (not in #5 B-4) — possibly an owner question.
- (planner) P1-8 slice: ADR for OD-8 (its register row also depends on OD-3, which is owner-only), then the runtime schemas; P1-1 can then take the hw_profile identity from this record.
- (code task, after OD-8) A key module in `hilclaw/` that builds the canonical form and the two directory names from field values, with tests against the example in the record.
- (owner, informational) The 7-day objection window of DRIVER §9 starts with the notice; later tasks that build on the record before it ends would have to be revisited if the owner objects.

## Result
