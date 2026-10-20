---
id: T-0376
title: Write ADR-0138 - the spec of a first-case round-0 bring-up coder call, what composes it from the run's own files and by what means it is written before the call (rest of OD-6, part of OD-23)
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-1, FR-5, OD-6, OD-23, OD-28, "#5 B-4"]
dependsOn: [T-0346, T-0374]
touchesFiles: [ARCHITECTURE/decisions/ADR-0138-od6-first-case-round-zero-spec.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 230, files: 4}
hq: []
---
## Why

PLAN P2-1 (Round-Manager, round 0 bring-up and baseline) and P2-2 (coder-driver) are open checklist items in the first group of the P2 order (PLAN P2 head, D18), so the D18 rule for work outside the checklist does not apply. P2-5 needs this: the first run's round 0 cannot issue its bring-up coder call without a `spec.json` for that call, and no record says what that spec holds or what writes it.

State on `main` `8336d9e`:

- `hilclaw/coder_call.call` performs a coder call given a spec file that is already written (ADR-0126 decision 3). ADR-0126 decision 4 says "the spec of the call is the coder-driver's to have written before it requests the call; **how it is composed and by what means it is written stay open** (rest of OD-6; ADR-0029 decision 4 gives the steps of the write)". ADR-0126 Scope "Outside" repeats it.
- What exists: the version-2 spec validator `hilclaw/spec.py` (ADR-0002, ADR-0050), the spec file's text form, final name and write `hilclaw/spec_file.py` (ADR-0029 as carried over by ADR-0051), the op-side values of the first `gemm` contract `hilclaw/gemm_contract.py` (`op_signature_record`, `task_contract`; ADR-0008), and readers of the run's `instance.json` in `hilclaw/instance.py` (`hw_profile_of`, `op_signature_of`, `objective_of`, `candidates_per_round_of`, ...). `spec.py` and `gemm_contract.py` both say they build no spec; nothing in `hilclaw/` issues one.
- The OD-6 register row lists as unsettled "실제 호출의 hw 쪽 값·`run_id`·기법 등 출처 없는 값"; § OD-6 lists "spec이 자기 instance가 적은 objective·제약을 싣는지의 확인 (… spec을 쓰는 것의 기록의 몫)".
- ADR-0119 fixes that the baseline is the run's own round-0 bring-up code, kept as attempt `0000/<CC>/<AA>`; its Boundaries leave "what the spec of a round-0 call holds (OD-28; ADR-0002 Boundaries; OD-6)" open.

These are design-level points of OD-6 and OD-23, so under DRIVER §9 a record is written first. **This task writes that record**, for the narrowest case P2-5 needs: the **first coder call of round 0** (attempt 1) of a first-case run whose `instance.json` states `candidates_per_round` 1. That scope avoids the open questions of how many candidates round 0 runs (OD-28, ADR-0028 decision 5, OD-8 ㉕) and of repair specs (OD-19), which stay open.

Planner's judgements (from `main` `8336d9e`; **the reviewer is asked to re-check each**):

- **Not owner-only.** No #5 A/B open item, C-6, OD-25 or OD-3 is decided. #5 B-4 values are used only as ADR-0008 and ADR-0058 already carry them for fp32 `gemm`; nothing of OD-31 (the C-6 revision) is touched.
- **No open HQ is crossed, if the means is chosen with care.** HQ-0040 asks whether the coder-driver reaches the *coder-call function* through Bash or as registry tool `coder.run`. The means of writing the spec is a separate question; the record must choose a means that works under either answer of HQ-0040 (for example a typed registry tool through the MCP front, which both forms can call, as ADR-0124, ADR-0133 and ADR-0134 did for other writes), and must say so. If the executor concludes the means cannot be chosen without the HQ-0040 answer, return BLOCKED (requirement unclear) with the question instead of choosing. HQ-0031 (whether injected hypotheses must be tested) and HQ-0048 (unlanded ADR-0132, technique-selector) are not touched: the record must not decide whether round 0 uses injected inputs or cases (OD-28; ADR-0073, ADR-0075 Boundaries) and must not cite unlanded ADR-0132 as accepted. HQ-0053 (the coder's sign-in) is not touched.
- **`guidance.techniques` in round 0.** ADR-0058 decision 1 explains what an empty list says and declines to say whether a real call may be issued with one. FR-1 round 0 is bring-up ("해당 HW에서 동작하는 코드 생성"). Whether round 0's spec carries an empty technique list is this record's to decide **only with cited support** (FR-1, S0 step 4, ADR-0119 decision 2); it must not invent a catalog entry (OD-22) nor decide whether the coder may pick a technique itself (OD-23, OD-12). If the honest reading is that it cannot be decided from documents, leave it open and say what the code slice may not do.
- **No data-plane schema change.** The spec's members, its file, its path (ADR-0004) and its version (2) exist. `task.build` is optional and its member names are open (OD-6 ②); the `cpu_standin` settings come from the package source (ADR-0116), so the record should omit `task.build` rather than name members. `ext` stays absent. If the record needs any new member, file, kind, value or version, leave the point open or return BLOCKED (A-13 data-plane schema change).
- **No overlap with open PR #186** (`hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py`, `tests/test_start_instance.py`). The unlanded branch `claude/T-0375-adr-first-case-coder-process-start` (BLOCKED, HQ-0053) holds **ADR-0137** and edits the OD-23 row and § OD-23; this task therefore uses **ADR-0138** and edits only the cells, bullets and sub-question ends it needs. Unlanded branches `claude/T-0361-*` (ADR-0132) and `claude/T-0318-*` (ADR-0112) also have no open PR.

All work is documents. No `claude` is started and nothing is tried on this machine (D16).

## Required Reading

- `PROCESS/DRIVER.md`: §3-5 (executor procedure, resume rule, the 2h30m limit); §5 (task format; naming: branch `claude/T-0376-<slug>`, trailer `Task: T-0376`; size cap D4); §3 "BLOCKED 사유" paragraph; §8; §9 (OD closing by ADR; the #5 notice with the driver footer; 7-day objection window).
- `CLAUDE.md`, 상시 규칙: "문서 커버리지 재검사"; "미결은 발명하지 않는다"; "세션 진입 점검"; "개발 드라이버와 런타임의 구분"; "브랜치·merge 절차" (document mode; BLOCKED reasons); "코멘트 최소화".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- **`ARCHITECTURE/decisions/ADR-0126-od23-coder-call-issuer.md`**: Status and Context (lines 3-30); Scope (from line 32); decisions 3 to 5 (lines 43-69); Walk-through row "A round-0 turn reaches its bring-up call"; Consequences and Boundaries.
- **`ARCHITECTURE/decisions/ADR-0002-od6-codegen-spec.md`**: decisions 1 to 4 and 7 (lines 23-83, 97-102); Boundaries (from line 161).
- `ARCHITECTURE/decisions/ADR-0050-od6-task-objective-members.md` and `ADR-0053-od8-instance-record-objective.md`: the objective of a spec and of an instance. Read their decisions and Boundaries.
- **`ARCHITECTURE/decisions/ADR-0029-od8-spec-file.md`**: decisions 3 and 4 (lines 40-57) and Boundaries (from line 121); `ADR-0051-od6-spec-file-version-2.md` decisions.
- **`ARCHITECTURE/decisions/ADR-0058-od6-committed-gemm-spec-example.md`**: decisions 1 and 3 (lines 35-42, 50-57), the Example (lines 76-113), Boundaries.
- `ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md`: decisions 1, 2, 4, 5, 9 (what `gemm_contract.py` renders).
- `ARCHITECTURE/decisions/ADR-0028-od8-instance-record-candidates-per-round.md`: decision 5 (lines 65-72) and Boundaries.
- **`ARCHITECTURE/decisions/ADR-0119-od28-first-case-baseline.md`**: decisions 1, 2 and 4; Consequences "The next slice it enables"; Boundaries.
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`: decisions 3 and 4 (lines 86-105) — the attempt path and the `coder/` writer role.
- `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md`, `ADR-0133-od23-first-case-round-promotion.md` decision 3 (lines 39-54) and `ADR-0134-od26-first-case-key-records-store.md`: precedents for a typed registry tool that builds and writes a run file from the run's own files. Read only.
- `ARCHITECTURE/decisions/ADR-0018-od8-instance-record-hw-profile.md` and `ADR-0031-od8-instance-record-op-signature.md`: where the two key records of a run are stated.
- Code, read only: module docstrings of `hilclaw/spec.py`, `hilclaw/spec_file.py`, `hilclaw/gemm_contract.py`, `hilclaw/coder_call.py`, `hilclaw/tools.py` (`registry`), and the reader functions of `hilclaw/instance.py` listed in Why.
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84); FR-1, FR-5; register rows OD-6 (line 97), OD-23, OD-28.
- `ARCHITECTURE/OpenDecisionProposals.md`: the header "기록 규칙" (line 8); § OD-6 (from line 59); § OD-23 (from line 395); § OD-28 (from line 449).
- `ARCHITECTURE/StandardScenarios.md`: the inspection rules and the first paragraph of § 검사 결과 (from line 168); S0.
- Issue #5: every comment after the ADR-0136 §9 notice (`gh issue view 5 --repo myungjoo/HIL-Claw --json comments`). If the owner has objected to ADR-0002, ADR-0058, ADR-0119 or ADR-0126, answered HQ-0040, or said anything about the round-0 spec or techniques in round 0, read it first; an objection or a statement that contradicts this task's plan means BLOCKED ("requirement unclear") with the comment quoted. If HQ-0040 is answered, name the answer in `## Result` and check the chosen means against it.
- Session entry check (CLAUDE.md): `gh pr list`, and issues #4, #7, #8 for anything on the spec of a coder call or round 0.

## Acceptance Criteria

### Files

- New `ARCHITECTURE/decisions/ADR-0138-od6-first-case-round-zero-spec.md` (the slug may change; keep `ADR-0138` and `od6`). ADR-0137 is held by the unlanded T-0375 branch; if 0138 is taken on `origin/main` or on any `origin/claude/*` branch when you start, use the next free number and say so in `## Result`.
- Edit `ARCHITECTURE/Requirements.md` and `ARCHITECTURE/OpenDecisionProposals.md` as below. Edit `ARCHITECTURE/StandardScenarios.md` only if the recheck changes a verdict.
- Nothing else changes: no code, test, CI, setting, `.claude/`, `orchestration/`, `PROCESS/` (other than this task file's `## Result`), no earlier ADR. If another file must change, return BLOCKED with the reason.

### The record

Follow the structure and conventions of ADR-0126 and ADR-0133: Status (accepted under DRIVER §9; which OD parts it answers; builds on which records; the 7-day objection window), Context (owner sentences found by a stated search, with terms and counts; facts of the code as observation), Decision, Walk-through, Alternatives considered, Consequences, Boundaries, References. Each sentence is evidently **owner's**, **cited** or **this record's own**.

Scope: the spec of the first coder call of round 0 (`round` 0, `candidate` 1, `attempt` 1) of a run of ADR-0120 decision 1 whose `instance.json` states `candidates_per_round` 1 and whose op_signature the `gemm` contract of ADR-0008 covers (ADR-0041 decision 5). Decide:

1. **Each member's source.** For every member of a version-2 spec (ADR-0002 decision 2, ADR-0050): `schema_version`; `id` (`run_id`, `round`, `candidate`, `attempt`, `candidates`, `relation`); `hw_profile` (key and record); `task.op_signature`, `task.contract`, `task.objective`; `task.build`; `guidance.techniques`; `feedback.attempts` and `feedback.base`; `repair`; `ext` — say where its value comes from (the run's `instance.json` by which reader; the request's tuple; a fixed value of a cited record; absent), citing the record that makes each value right. In particular: `task.objective` is the objective the run's `instance.json` states (answers the § OD-6 point "spec이 자기 instance가 적은 objective·제약을 싣는지" for this scope), `task.contract` is ADR-0008's for the run's op_signature, `id.candidates` is 1 and `relation` follows ADR-0002 for one candidate, `feedback.attempts` is empty with no `base` (no earlier attempt), `repair` is absent (attempt 1). `task.build` and `ext` are absent unless a cited rule requires them (see Why). For `guidance.techniques`, decide only with cited support or leave open (see Why).
2. **What composes and writes it, and when.** The role stays the coder-driver's (ADR-0126 decision 4; ADR-0004 decision 4). Choose the means by which it is written before the call — for example a new typed registry tool, called through the MCP front with `run_id` and the tuple, that builds the spec from the run's files, validates it with `spec.validate` and writes it with `spec_file.write` (ADR-0029 decision 4 steps) — or another means with reasons. The means must work under either answer to HQ-0040 and the record must say why (Why). If you add a tool: its name, request members, result members, failure kinds (reusing reserved kinds of ADR-0015 decision 2 and existing `run_file_*` / `spec_*` kinds where the meaning is the same; any new kind is a tool-failure kind, not a data-plane value — say so), whether it is journaled (and if so its `step` value, ADR-0100), and what it does when the spec file's final name is taken (ADR-0029 decision 4 "a taken name").
3. **What the record does not decide**, named in Boundaries: specs of later rounds, of other candidates (N > 1, OD-28, OD-29, ADR-0028 decision 5, OD-8 ㉕), of repair attempts (OD-19, ADR-0002 decision 5); techniques and their selection (FR-8, OD-7, OD-22; unlanded ADR-0132); injected inputs and cases in round 0 (OD-28, FR-15, HQ-0031); profile and contrastive feedback (OD-6 (B4), top-k/bottom-k); `task.build` member names (OD-6 ②); `ext` contents (S7, B5); other kinds, dtypes and OD-31; the coder's prompt and process start (ADR-0049 slice (d), HQ-0053); the front of the coder call (HQ-0040); the Round-Manager's delegation step and the coder-driver definition file.

State in Consequences:

- **Code slices for the planner** (code mode; tests with fixtures only): the module(s) and registry entry the record names, and the `orchestration/` steps that wait on HQ-0040. Keep the first slice within the D4 cap if possible.
- **Runtime acceptance items** (D16): none expected — if the means adds one (for example that a live coder-driver sub-agent calls the new tool), number it after the last in the turn-session series on `origin/main` (ADR-0136 used (xxxi), (xxxii); the unlanded T-0375 draft used (xxxiii)-(xxxviii), so start after the last number **on main** and note the possible clash in `## Result`).
- **A-13 reading**: document mode; no code, dependency, setting or data-plane schema change; nothing required of the development machine.
- **"Less exact, not edited"**: sentences of earlier records this record narrows, found by a stated search (at least ADR-0126 decision 4 and Scope "Outside", ADR-0119 Boundaries "what the spec of a round-0 call holds", ADR-0002 Boundaries, ADR-0058 decision 1 "whether a real call may or should be issued with an empty list" if decided, ADR-0050 L2, and the "builds no spec" sentences of `hilclaw/spec.py` and `hilclaw/gemm_contract.py` docstrings); list them, edit none.
- **The cost, plainly.**

Do not invent: every value the record fixes is cited from a record or the run's own files, or marked as this record's choice with its reason; nothing about an owner's preference is assumed.

### The registers (follow the recording rules written in those files, not earlier task files)

- `ARCHITECTURE/Requirements.md`: follow the "행 형식" paragraph (line 84). In the OD-6 row, and in the OD-23 and OD-28 rows only where the record answers part of them: add **one link** to the new ADR with a few words of its subject under the confirmed part, and rewrite the remainder (`**잔여**:`) in place. Do not restate the record and add no dated paragraph. Change a status cell only if the rule there requires it.
- `ARCHITECTURE/OpenDecisionProposals.md`: follow the header's "기록 규칙" (line 8). Add one `- **채택분** [ADR-0138](…) — <what it covers> (답함: …)` line in § OD-6 (and in § OD-23 / § OD-28 only where it answers part of them). Where an open point or sub-question is partly or fully answered (for example the § OD-6 "spec이 자기 instance가 적은 objective·제약을 싣는지의 확인"), rewrite that text's status in place (`→ 부분 답: … 남음: …` / `→ 답함: …`, and the bullet-head status word); keep the question's wording. A new sub-question is registered with its wording only.
- `ARCHITECTURE/StandardScenarios.md`: recheck coverage with its inspection rules (CLAUDE.md "문서 커버리지 재검사"); per the first paragraph of § 검사 결과, add to the history only if a verdict changes; otherwise record nothing there and say so in `## Result`.

### Process

- Document mode (CLAUDE.md A-13): branch `claude/T-0376-<slug>`; context-isolated reviewer cycle (dev-item-address steps 10-12, at most 7 rounds) to Approve; rebase on `origin/main`; push to `main` directly with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0376`. No force push.
- After landing, post the §9 notice on #5 (English; first line `### ADR-0138 accepted under DRIVER §9 — T-0376: <summary>`, naming the landed commit and the 7-day window, and any runtime acceptance items; last line `— posted by driver`). Put the comment URL in `## Result`.
- If the record adds runtime acceptance items, say so in `## Result` so that the driver raises the HQ with reason `runtime-acceptance` (DRIVER §8).
- No `claude` is started at any point (D16).

## Out of Scope

- Any code: the tool or module the record names, `hilclaw/`, tests, `orchestration/` (later slices).
- Specs of any call other than round 0 / candidate 1 / attempt 1 under the scope above.
- The coder's prompt, the container and the coder process start (ADR-0049 slice (d), T-0375, HQ-0053).
- The front of the coder call and the coder-driver definition (HQ-0040).
- Technique selection, injected inputs, cases, OD-31.
- Editing any earlier ADR or less-exact sentence (list them; D18 hold).

## Follow-ups

- Planner's view of what follows: the code slice the record names (the spec composer/writer and its registry entry), tested with fixtures; the Round-Manager round-0 steps after HQ-0040 is answered.

## Result

DONE. ADR-0138 (`ARCHITECTURE/decisions/ADR-0138-od6-first-case-round-zero-spec.md`; number 0138 was free on main and on every `origin/claude/*` branch) landed on `main` as acb6801 (document mode, `Reviewed-by: reviewer agent (7 rounds, Approve)`, `Task: T-0376`); branch deleted. §9 notice: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6301641619 .

- Record: every member of the round-0 first-call spec gets a cited source (hw_profile, op_signature, objective copied whole from `instance.json`; contract from ADR-0008; `id.candidates` 1 / `single` as this record's reading of FR-1 with ADR-0119 decision 4; empty feedback; no repair, `task.build` or `ext`); `guidance.techniques` empty on ADR-0059 decision 5, G1 and FR-1. Means: new registry tool `spec.write` (MCP front, called by the coder-driver before the call; checks ① to ⑧; reused kinds plus new tool-layer kinds `candidates_per_round_not_stated`, `candidates_per_round_not_covered`, `spec_exists`, `spec_not_written`; not journaled). What follows `spec_exists` is left open (OD-8 ㉖ (가)).
- HQ-0040 is not answered (checked 2026-10-21); the means works under either answer (decision 4). HQ-0053, HQ-0031, HQ-0048 untouched; ADR-0132/0137 not relied on.
- Runtime acceptance: new item **(xxxiii)** (coder-driver sub-agent calls `mcp__hilclaw__spec_write` without a prompt) — the driver should raise an HQ with reason `runtime-acceptance`. Possible number clash: the unlanded T-0375 draft (ADR-0137) also uses (xxxiii)-(xxxviii); whichever lands second renumbers.
- Registers: OD-6, OD-23, OD-28 rows and sections as asked; also the OD-8 row and § OD-8 (adopted line; in-place partial answers of ⑱, ㉕ (나), ㉘ (나), ㉞ (나)), because the record partly answers those sub-questions and the "기록 규칙" requires the in-place status. No status cell changed. T-0375's branch edits the same OD-23 row and § OD-23; expect a rebase conflict there.
- StandardScenarios: S0, S1, S8 rechecked, no verdict change; only the "최근 재검사" line was updated, as that file's own recording rule requires on every recheck (no history entry).
- Deferred nits from review round 7 (not applied, to stay within 7 rounds): the Walk-through row "The file was changed after the start" should cite ADR-0018 decision 6 beside ADR-0004 decision 10; the OD-6/OD-8/OD-28 status-cell date ranges were left as they were.
- Follow-up for the planner: code slice 1 of the record (`hilclaw/spec_tool.py` + `tests/test_spec_tool.py` + `default_registry` entry), which does not wait on HQ-0040.
