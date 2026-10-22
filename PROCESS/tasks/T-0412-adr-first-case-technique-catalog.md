---
id: T-0412
title: Write ADR-0150 - the first technique catalog of a first-case run (cpu_standin, gemm fp32 row_major, C): where its entries live, the form of an entry and of its id, what an entry gives a spec's guidance.techniques, and its first entries (part of OD-22 with FR-8; needed for rounds >= 1 of PLAN P2-5)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-8, OD-22, OD-6, OD-7, OD-23, "PLAN P2-5", "PLAN P2-6"]
dependsOn: []
touchesFiles: [ARCHITECTURE/decisions/ADR-0150-od22-first-case-technique-catalog.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 230, files: 4}
hq: []
---
## Why

**Where PLAN P2 stands** (as of `main` `9eef008`):
- PLAN P2 runs its items in the listed order (P2-1 to P2-4, P2-6, P2-7, then P2-5).
- P2-4's only open part is now the gate half of "예산·gate". That half is owner-only (OD-3, #5 A-5; T-0411 Result).
- Each other open part of P2-1, P2-2, P2-6 and P2-7 that is in the way of round >= 1 is held by an open HQ:
  - the selection role and the writer of `decision/hypotheses.json`: unlanded ADR-0132, HQ-0048;
  - the coder's container start: unlanded ADR-0137, HQ-0053;
  - `sim.run`/`board.run` and the `cpu_standin` operations: HQ-0021, HQ-0026.
- So `orchestration/round-manager.md` still stops every round >= 1 after its first step: "the following steps of round `<round>` are not yet defined".

**One missing piece is held by none of those HQs: the technique catalog.**
- FR-8: technique knowledge is a hybrid of a **Skill** (selection criteria) and a **catalog** (application guidance and cross-run statistics). "선택 기준은 Orchestrator 세션에서 트리거에, 적용 지침은 코더 spec에 실린다. P1에서는 기법 후보 = repo 내 문서로 시작."
- A spec names the techniques of a call by catalog entry: `guidance.techniques[]` is `{id, text}`, where `id` "names the catalog entry" and `text` is "its application guidance, copied when the spec is written" (ADR-0002 decision 2).
- **No catalog exists** (OD-22). For that reason the committed example's list is empty (ADR-0058 decision 1), a hypothesis names no technique (ADR-0059 decision 3, "No technique reference"), and the round-0 spec carries none (ADR-0138 decision 2 (b)).
- The unlanded draft ADR-0132 (branch `claude/T-0361-*`, **not a source**) leaves "The catalog and the technique ids a spec names (OD-22)" outside itself, and says the selector's `Skill` "is added by the record that gives the first one". So a catalog record does not cross HQ-0048, provided it leaves the selection side alone (see below).
- **Without a catalog, no spec of a round >= 1 can name a technique without inventing one.** The 5 rounds of P2-5 cannot apply techniques (FR-1 "기법 선택", FR-17), and neither can the later rounds of P2-14.

**D18 judgement (DRIVER §6).** This is not a PLAN checklist item: OD-22 is listed only in the "P3 이후" draft, as catalog *cold start*. The planner judges it **needed for P2-5**, for the reasons above, so it is made a task. The reviewer is asked to re-check this judgement.

**What the owner has said** (cite these; do not stretch them):
- #5 A-7, "Settled with the decision" (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944117402):
  - "The stand-in is registered as its own hw_profile (`cpu_standin`), so FR-7 statistics and the catalog are keyed separately and cannot contaminate future NPU knowledge."
  - "Catalog techniques for it are a small CPU-specific set used to exercise the loop, not the project's optimization asset."
- #5 A-7 ②: "OpenMP and SIMD intrinsics are allowed in stand-in kernels."
- #5 B-4 ④ (cited in § OD-22): nntrainer's git history is not mined for the catalog.
- **HQ-0034 (owner-only, open)**: whether OpenMP is usable by a stand-in kernel. "the first case runs without OpenMP". The record must not adopt an entry that needs the OpenMP flag or runtime.

**Scope, to keep one record reviewable.** The runs of ADR-0120 decision 1 (first case) only: hw_profile `cpu_standin` (and the mock, if the record finds it needs a word), op `gemm` fp32 `row_major`, C kernels. The record answers:

(a) **Place and form.** Where the catalog's entries live, and in what file form. Weigh at least:
- (i) Claude Code skills under `orchestration/skills/` (copied to the turn session's `.claude/skills/` by `hilclaw/turn_definition.LAYOUT`, ADR-0118 R3). Note: ADR-0139 decision 4 closes the main session's built-ins with `--tools` (today `Agent`, `Read`, `Grep`, `Glob`), so a skill is not reachable through the `Skill` tool unless a later record opens it.
- (ii) a package data file or module under `hilclaw/`, read by a registry tool, so that `text` is copied by code (as `spec.write` copies the run's records, ADR-0138);
- (iii) a separate directory of the code repository;
- (iv) the data repository under `db/<hw_profile_key>/`. This is data plane: a new file of the data plane is a schema change (CLAUDE.md A-13). The record may weigh (iv) but may not adopt it (see the data-plane judgement below).

How the FR-8 split (selection criteria vs application guidance) maps onto the place chosen. How A-7's "keyed separately" by hw_profile is met.

(b) **An entry and its id.** What one entry holds (at least: the id, the application guidance that becomes `text`, and where and how the selection criteria are kept). The form of an id: a *name* of ADR-0001 decision 1, or a stated other form, with the reason. The rule that an id is never reused for a different technique (cases and later statistics refer to what a spec applied: `feedback.attempts[].techniques`, ADR-0002 decision 2). What a change of an entry's text means for specs already written: the spec holds a copy (ADR-0002).

(c) **What an entry gives a spec.** That `guidance.techniques[]` of a later spec is `{id, text}` taken from an entry, unchanged in form. **Not** how a round >= 1 spec is composed, who chooses its techniques or how they reach `spec.write`: that is rest of OD-6 and the selection side (HQ-0048).

(d) **The first entries.** A small set for `cpu_standin` × `gemm` fp32 `row_major` in C, "used to exercise the loop" (A-7). Name each entry by id with a one-line gist. Say why each fits ADR-0008 (contract; what a kernel may include, decision 7) and ADR-0116 (the fixed build flags: `-std=gnu11`, `-ffp-contract=off`, no target-specific flag; function attributes for intrinsics) on every machine kind of C-7. Exclude OpenMP (HQ-0034). Say whether the full guidance text is written in the record or left to a code slice reviewed against the record. Either way, the record states what each text must and must not say (for example, no claim of a measured speed-up the project has not measured).

(e) **What follows**:
- code slices (each within the D4 cap, tested with fixtures only, no `claude`), or "none";
- runtime acceptance items, if any, numbered from **(lxvii)** (ADR-0149 added none; the last on `main` is ADR-0148's (lxvi));
- "Less exact, not edited";
- what stays open.

**Planner's judgements** (from `main` `9eef008`; **the reviewer is asked to re-check each**):
- **Not owner-only.** OD-22 is a design-level OD, not among the owner-only items of DRIVER §9 (#5 A/B items, C-6, OD-25, OD-3). Choosing a first hand-written set fits A-7's "small CPU-specific set". The following need the owner:
  - OpenMP (HQ-0034);
  - a vendor library baseline (OD-28; a new external dependency);
  - anything of #5 B-1 to B-8 or OD-31.
  If a coherent answer needs one of them, stop and return BLOCKED (`requirement-unclear`) with the question in Korean (DRIVER §8).
- **Data plane.** A spec's `guidance.techniques` already exists (ADR-0002, version 2 by ADR-0051); an entry in the code repository is not data plane. If the executor finds that a coherent answer needs any of these, it does not choose one: it either concludes on another option and names that point open, or returns BLOCKED (`data-plane-schema`):
  - a new member, file, kind or version of the data plane (a new `spec` member or `ext` member, a file under `db/`, `technique_stats.json` content);
  - a change to `hypotheses.json`.
- **No new external dependency.**
- **No open HQ is crossed**:
  - HQ-0048: do not decide the selection role, its tools (the `Skill` tool included), how the selection reads the catalog, or `decision/decision.md`. Say that the record of the selection side decides them.
  - HQ-0053, HQ-0021, HQ-0026, HQ-0032 (open PR #186), HQ-0031 (injected hypotheses), HQ-0034 (OpenMP): unrelated or excluded as said; do not presume their answers.
  - The `runtime-acceptance` HQs: cite them, treat none as confirmed.
  - Unlanded branches (`claude/T-0210-*`, `claude/T-0231-*`, `claude/T-0264-*`, `claude/T-0318-*`, `claude/T-0324-*`, `claude/T-0361-*`, `claude/T-0375-*`) are not sources, and their ADR numbers (0132, 0137 and others) are not taken. **ADR-0150 is free** on `main` and on every remote branch as of `9eef008`.
- **Not decided here**:
  - OD-22's cold-start methods (optimization rewind, git-history mining) and UC-5's curator flow;
  - OD-7 (statistics, ranking signal, feedback path) and the content of `technique_stats.json`;
  - OD-12 (external references; documentation excerpts in specs, (B5));
  - entries for other kinds, dtypes, backends or OD-31's operations.
- **No open PR overlaps.** PR #186 (T-0324) touches `hilclaw/start_instance.py` and three test files only.

All work is documents and documentation reading. **No `claude` process is started on this machine** (D16; DRIVER §1-5). Any fact about Claude Code (skills, `--tools`, the `Skill` tool, how `.claude/skills/` loads in a `-p` session) comes only from the official documentation:
- https://code.claude.com/docs/en/skills
- https://code.claude.com/docs/en/cli-reference
- https://code.claude.com/docs/en/headless

Read them with a web fetch or `curl`. Quote each fact with its URL and the date read, in a Context fact table. ADR-0118 R3/R9 and ADR-0139 P5 already quote part of this: cite them and re-read only what is needed. What the documentation cannot show becomes a runtime acceptance item.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, the 2h30m limit, no force push;
  - §5 (lines 86-114): task format; naming convention (branch `claude/T-0412-<slug>`, trailer `Task: T-0412`); the D4 size cap;
  - §6 (line 121): the D18 priority rule;
  - §8 (lines 136-142) and §9 (lines 144-151): HQ form, OD closing authority, and the #5 notice with the `— posted by driver` footer (line 141).
- `CLAUDE.md`, 상시 규칙: "문서 커버리지 재검사", "미결은 발명하지 않는다", "세 층 모델", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode; BLOCKED reasons).
- `ARCHITECTURE/decisions/ADR-0138-od6-first-case-round-zero-spec.md` (all, 144 lines). It is the closest model for structure, the owner-sentence search, Status bullets, Consequences and Boundaries. Note decision 2 (b) (line 58) and Boundaries lines 129-131.
- `ARCHITECTURE/decisions/ADR-0149-od18-first-case-post-tool-use.md`: Status only, for the current Status form and the fact-mark numbering.
- `ARCHITECTURE/decisions/ADR-0002-od6-codegen-spec.md`: decision 2 (lines 30-72, `guidance.techniques`, `feedback.attempts[].techniques`), decision 7 (lines 97-102), Boundaries (lines 161-172).
- `ARCHITECTURE/decisions/ADR-0058-od6-committed-gemm-spec-example.md`: decision 1 (lines 35-42), Boundaries.
- `ARCHITECTURE/decisions/ADR-0059-od30-round-hypothesis-record.md`: Context line 16; decision 3 (lines 51-75, "No technique reference" at line 74); decision 5 (line 86); Alternatives row 3 (line 124).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: decision 1 (names) and "Record format" (line 146 on).
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`: lines 57, 70, 77, 91, 109-110 (`decision.md`, `technique_stats.json`).
- `ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md`: decision 7 (lines 100-106).
- `ARCHITECTURE/decisions/ADR-0116-od18-cpu-standin-build-settings.md`: decisions 1-3 (lines 26-61), Walk-through (lines 88-97), Alternatives row 3 (line 117).
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`: facts R3 and R9 (lines 34, 40).
- `ARCHITECTURE/decisions/ADR-0139-od18-first-case-turn-session-permissions.md`: fact P5 (line 35); decision 4 (lines 67-73).
- `ARCHITECTURE/Requirements.md`:
  - FR-1, FR-7, FR-8 (line 26), FR-17;
  - line 84 (**행 형식**);
  - register rows OD-6 (line 97), OD-7 (line 98), OD-22 (line 113), OD-23 (line 114).
- `ARCHITECTURE/OpenDecisionProposals.md`: line 8 (**기록 규칙**); § OD-22 (lines 401-407); § OD-23 open parts (line 435).
- `ARCHITECTURE/UsageCases.md`: line 28 (glossary "기법 카탈로그") and UC-5 (lines ~115-124).
- `ARCHITECTURE/StandardScenarios.md`: §검사 결과 (from line 168), its first paragraph (기록 규약) and the "최근 재검사" line; S0, S1, G1.
- Code, as observation only:
  - `hilclaw/turn_definition.py` lines 1-60 and `LAYOUT` (line 90);
  - `hilclaw/spec.py` module docstring (`guidance.techniques` validation);
  - `orchestration/round-manager.md` "The round steps".

## Acceptance Criteria

1. **The record.** `ARCHITECTURE/decisions/ADR-0150-od22-first-case-technique-catalog.md` exists in the format of ADR-0001 "Record format", as ADR-0138 follows it:
   - **Status**:
     - accepted under DRIVER §9, not owner-confirmed;
     - the two kinds of content;
     - the owner-sentence search, with its terms and what it found;
     - what it answers, and that **OD-22 keeps its status word `제안됨`**;
     - open HQs checked and not crossed;
     - not owner-only;
     - no data-plane change and no new dependency;
     - nothing started;
     - which earlier sentences it makes less exact, none edited;
     - what it builds on;
     - the 7-day objection.
   - **Context**, with a fact table if any Claude Code fact is used.
   - **Decision**: scope and terms, then answers (a) to (e) of Why.
   - **Walk-through.**
   - **Alternatives considered**: at least places (i) to (iv), and an empty catalog kept until OD-22's cold start.
   - **Consequences**, **Boundaries**, **References**.
2. **Every sentence is either cited (source named) or the record's own**, and every reading is marked as such. Facts about Claude Code come only from the documentation, with URL and date read. Nothing is tried in a live session.
3. **The first entries are named by id**, each with a one-line gist and its fit to ADR-0008 decision 7 and ADR-0116 on every C-7 machine kind. No entry needs OpenMP (HQ-0034) or any library beyond what ADR-0008 decision 7 allows. No entry claims a measured effect.
4. **Nothing of the selection side is decided** (HQ-0048):
   - not who reads the catalog for selection, or by what tool;
   - not how chosen techniques reach a spec;
   - not `decision/decision.md`.
   **No data-plane member, file, kind or version is adopted.**
5. **Boundaries** name at least:
   - the selection role and its tools (HQ-0048);
   - round >= 1 spec composition (rest of OD-6);
   - OD-22's cold-start methods and UC-5;
   - OD-7 and `technique_stats.json`;
   - OD-12;
   - OpenMP (HQ-0034);
   - other hw_profiles, kinds, dtypes, layouts and OD-31;
   - runs outside ADR-0120 decision 1.
6. **Consequences** give:
   - the code slices (or "none"), each within the D4 cap, tested with fixtures only. If a slice adds files under `orchestration/` or `hilclaw/`, say which test-rule items (CLAUDE.md 테스트 규칙 ①-⑤) apply, as earlier records did, without deciding a test-rule question that is not the record's.
   - runtime acceptance items numbered from **(lxvii)**, each with how it is closed (owner by hand, or a runtime self-check), or "none";
   - "Less exact, not edited": for example ADR-0058 decision 1, ADR-0059 decision 3 and Context line 16, ADR-0002 Boundaries, ADR-0138 decision 2 (b) and Boundaries. Say how the list was found; do not claim it complete.
   - "UsageCases and StandardScenarios";
   - the A-13 reading;
   - "The cost, plainly".
7. **`ARCHITECTURE/Requirements.md`**: edit the OD-22 row by **행 형식** (line 84):
   - add `**확정분**:` with exactly one link to ADR-0150 and a topic of a few words;
   - add or rewrite `**잔여**:` in place;
   - keep the status word `제안됨` in the status cell.
   No restatement of the record and no dated sentence or chain. If the record also answers a part of OD-6, OD-7 or OD-23, apply the same rule to that row; otherwise leave it.
8. **`ARCHITECTURE/OpenDecisionProposals.md`**: edit § OD-22 by **기록 규칙** (line 8):
   - add one `- **채택분** [ADR-0150](decisions/ADR-0150-od22-first-case-technique-catalog.md) — …` line;
   - rewrite in place any sentence of the section that ADR-0150 makes untrue (for example the line on the committed example's empty list, if it still reads as "no catalog"), keeping the proposal's wording otherwise.
   No restatement and no dated annotation. Touch another section only under the same rule, for a sentence ADR-0150 answers.
9. **`ARCHITECTURE/StandardScenarios.md`**: recheck the coverage (CLAUDE.md "문서 커버리지 재검사"; at least S0, S1 and G1) and update §검사 결과 by the rule in its first paragraph:
   - the "최근 재검사" line in place;
   - a "판정 변화 이력" entry only if a verdict changed or a gap was found or closed.
10. **No other file** changes: no `hilclaw/`, `orchestration/`, tests, CI, `.claude/`, `CLAUDE.md`, `PROCESS/PLAN.md`, `PROCESS/STATE.json`, UsageCases, earlier ADRs, or the `HIL-Claw-data` repository. `git diff origin/main --stat` lists only `touchesFiles` (plus this task file's `Result`, if written on the branch). `git ls-files --eol` shows `i/lf` for them.
11. **Review.** Run the reviewer cycle with a fresh-context `dev-reviewer` (dev-code-review, document-mode return path), at most 7 rounds. Ask the reviewer explicitly to:
    - (a) check every owner citation against its source, and that A-7's "small CPU-specific set used to exercise the loop" and "keyed separately" are not stretched;
    - (b) check that each first entry fits ADR-0008 decision 7 and ADR-0116 on every C-7 machine kind, needs no OpenMP and claims no measured effect;
    - (c) check that nothing of the selection side (HQ-0048) and nothing of round >= 1 spec composition is decided;
    - (d) check that no data-plane member, file, kind or version is adopted and no new dependency is introduced;
    - (e) check every Claude Code fact against the cited page and date;
    - (f) check the register edits against **행 형식** and **기록 규칙**, and the §검사 결과 edit against its first paragraph;
    - (g) re-check each planner's judgement in Why, including the D18 judgement.
    A finding starting with `SECURITY` is BLOCKED.
12. **Landing.** On Approve: rebase on `origin/main`, then push to `main` directly (document mode, A-13) with the trailer `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0412`. Post the DRIVER §9 notice on issue #5: link to the landed commit, the OD, the 7-day objection window, and `— posted by driver` as the last line. Record the notice's URL in `Result`.

## Out of Scope

- Any code, test, skill, settings or definition change. That includes writing catalog entry files: they are later code slices, if the record places them so.
- The selection role, its tools and `decision/decision.md` (HQ-0048); round >= 1 spec composition and `spec.write`'s request for later rounds (rest of OD-6); the Round-Manager's round >= 1 steps (P2-1).
- OpenMP (HQ-0034); vendor libraries (OD-28); OD-7 statistics and `technique_stats.json`; OD-12; OD-22's cold-start methods; UC-5's curator flow; OD-31.
- Any data-plane schema change (A-13 BLOCKED reason).
- Editing the "Less exact, not edited" sentences of earlier records (D18; PLAN "보류" holds many such lines).
- Editing `PROCESS/PLAN.md` or `PROCESS/STATE.json`.
- Starting `claude` (D16), and closing any runtime acceptance item.

## Follow-ups

- (planner) If ADR-0150 places entries in files, its code slices come next. After them, the round >= 1 spec record (rest of OD-6) can name catalog ids; its selection half still waits on HQ-0048.
- (planner, for the driver) P2-4's gate half is owner-only (OD-3, #5 A-5). There is no HQ for it in `PROCESS/STATE.json`: A-5 predates D19. Whether to raise one is the driver's call (DRIVER §8).

## Result
