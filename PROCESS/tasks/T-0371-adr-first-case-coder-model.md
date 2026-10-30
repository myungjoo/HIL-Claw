---
id: T-0371
title: Record ADR-0136, the model of a first-case coder call - the instance.json member, the default the start applies, the form of the value and how the call reads it (owner answer HQ-0041 part 1; part of OD-8 and OD-23; PLAN P2-2)
phase: P1
status: DONE
commitMode: doc
coversReq: [NFR-5, FR-5, FR-13, OD-8, OD-23, "#5 A-8", S0, S1]
dependsOn: [T-0346, T-0347]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0136-od8-first-case-coder-model.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 200, files: 4}
hq: []
---
## Why

PLAN P2-1 cannot go further yet. The steps between the key store and the closing steps of a round start with round 0's bring-up, and the bring-up is a coder call (ADR-0119 decision 2). Two open HQs block those steps. The delegation step waits on HQ-0040 (the front of the coder call, ADR-0126 Q1). The measurement waits on the holder of `sim.run`/`board.run` (T-0210/HQ-0021). T-0370's Follow-ups asked whether a design record could cover round 0 without them. It cannot: ADR-0126 Consequences says the delegation step "waits for this answer".

The coder call itself can still progress. `hilclaw/coder_call.py` (T-0347) performs the whole call except slice (d), the start of the container and the coder process (ADR-0049 Consequences; ADR-0126 Consequences, slice 3). Slice (d) waits on two things: the owner's #5 A-8 and a list of design points. The owner answered A-8 in HQ-0041 ([#5 comment](https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6290608368)):

- (1) The coder model is an instance parameter. When none is named, the start applies Opus and records it in `instance.json`.
- (2) There is one token axis that sums orchestrator and coder tokens, so the coder call reads and reports the coder's token usage.
- The owner left two points to the record: the form of the recorded model value (alias or full name), and which usage counts as tokens.

No record applies that answer yet. This task records part (1) only: the model. Part (2), the token axis, would be the first row of `ARCHITECTURE/SpendAxes.md`. It depends on how the coder's output stream is read (OD-23 ① (라)), which is a design point of slice (d). So it is a later record. Keeping the two apart keeps this record small.

This task is a slice of PLAN P2-2 (the coder-driver, `claude -p` call). P2-2 is a checklist item in the first group of the P2 order (PLAN P2 head, D18), so the D18 rule for work outside the checklist does not apply. P2-5 needs it: no coder call of P2-5's run can start without a model to run the coder with (NFR-5).

The owner's answer authorises recording the model in `instance.json`. The record adds that one member under the frame of ADR-0018 decision 2 along the D6 route, as ADR-0032 did for `round_budget` (DRIVER §9). The member is a data-plane addition the owner asked for, so it is not a BLOCKED reason. A new version of the file, or a change to any other file of the data plane, would be one (point 3 (e)).

Open HQs checked:

- HQ-0040: not crossed. The model reaches the function the same way under (B) and (T).
- HQ-0041 part (2): left to a later record.
- HQ-0032 (PR #186, the start function of ADR-0115): not answered. This record may say what the start does with the member. It must not depend on how the start learns of a given id, and it edits no code.
- HQ-0031, HQ-0043 and HQ-0048: not touched.

All verification is by reading and review. No `claude` is started (D16).

## Required Reading

- `PROCESS/DRIVER.md`:
  - §2 (doc mode);
  - §3-5 (executor procedure, resume rule, time limit);
  - §5 (naming: branch `claude/T-0371-<slug>`, trailer `Task: T-0371`; size cap);
  - §8 (the `— posted by driver` footer);
  - §9 (OD closing authority, the owner notice on #5, the 7-day objection window).
- `CLAUDE.md`, all rules. In particular:
  - "미결은 발명하지 않는다";
  - 문서 커버리지 재검사;
  - the A-13 doc-mode procedure: reviewer cycle, rebase onto `origin/main`, one squashed commit with the `Reviewed-by` and `Task:` trailers, direct push to main;
  - the BLOCKED reasons;
  - "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole; doc-mode return path).
- The owner's answer:
  - `PROCESS/STATE.json`, the `humanQuestions` entry `HQ-0041` (`question` and `decision`);
  - the #5 comment it links (`gh api repos/myungjoo/HIL-Claw/issues/comments/6290608368`);
  - the original #5 A-8 item, found by a search of #5.
- The call and its open parts: `ARCHITECTURE/decisions/ADR-0126-od23-coder-call-issuer.md`:
  - decisions 3, 5 and 7 (lines 43-80);
  - Consequences (lines 103-127), especially "Open parts of the start" (lines 110-114);
  - Boundaries (lines 128-136).
- The means: `ARCHITECTURE/decisions/ADR-0049-od8-coder-call-isolation-means.md`:
  - decision 2, P1 to P4 (lines 41-52);
  - L5 (line 101);
  - Consequences, slice (d) (line 144);
  - Boundaries, "How the coder process is started" (line 153).
- The file the member goes into:
  - `ARCHITECTURE/decisions/ADR-0018-od8-instance-record-hw-profile.md` decision 2 (lines 28-41): the open top level and what raises the version.
  - `ARCHITECTURE/decisions/ADR-0032-od8-instance-record-round-budget.md` (whole, 179 lines). It is the model of a record that adds one `instance.json` member, including its A-13 reading (line 158). Use it as a model of form; do not restate it.
- What the start does with a default: `ARCHITECTURE/decisions/ADR-0076-od8-instance-start-required-members.md` decisions 2 and 3 (lines 31-58: the `n_max` default put into the content). Also `ARCHITECTURE/decisions/ADR-0115-od8-instance-start-performer.md` decisions 1 and 2 (lines 46-80).
- Code, read only as observations. This record binds no code.
  - `hilclaw/coder_call.py`: the module docstring and `call`.
  - `hilclaw/instance.py`: the module docstring and the members it defines.
  - `hilclaw/instance_start.py`: the module docstring and `prepare`.
- Claude Code documentation on the day, cited with the date read:
  - the CLI reference for `--model` (https://docs.claude.com/en/docs/claude-code/cli-reference);
  - model configuration, for aliases and full model names (https://docs.claude.com/en/docs/claude-code/model-config).
  - Quote only what the pages say. Nothing may be tried on this machine (D16).
- The record format: `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` §"Record format" (line 146 on).
- `ARCHITECTURE/Requirements.md`:
  - NFR-5 (line 48) and C-7 ② (line 64);
  - the OD register preamble, **"행 형식"** (line 84);
  - rows OD-8 (line 99), OD-19 (line 110) and OD-23 (line 114).
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - the header's **"기록 규칙"** (line 8);
  - § OD-8 (lines 87-166) and § OD-23 (lines 394-416);
  - § OD-19 (lines 360-370), only to check that nothing there becomes false.
- `ARCHITECTURE/StandardScenarios.md`:
  - §검사 규칙 (from line 13);
  - §검사 결과 (from line 168). **Its first paragraph is the recording rule.**
  - S0, S1 and S2.
- Before you edit `ARCHITECTURE/`, run `gh pr list` and read issues #4, #5, #7 and #8 (CLAUDE.md 세션 진입 점검). If an open PR touches the same tables or sections, stop and return BLOCKED.
  - Open PR #186 (T-0324, BLOCKED by HQ-0032) touches only `hilclaw/start_instance.py` and three test files. It does not overlap this task.
  - The unlanded branches `claude/T-0361-*`, `claude/T-0318-*`, `claude/T-0231-*`, `claude/T-0210-*` and `claude/T-0264-*` edit `Requirements.md`, `OpenDecisionProposals.md` and `StandardScenarios.md`. `claude/T-0361-*` edits the OD-23 row and section. Do not take their content, and note in the Result any overlap you find.

## Acceptance Criteria

1. **The record and its number.**
   - A new record `ARCHITECTURE/decisions/ADR-0136-od8-first-case-coder-model.md` exists in the ADR-0001 record format: Status, Context, Decision with numbered decisions, a Walk-through, Alternatives considered, Consequences, Boundaries, References.
   - ADR-0112 and ADR-0132 are held by unlanded branches. Before the push, confirm that ADR-0136 is free on `origin/main` and on every remote branch. If it is not, take the next free number and update every reference.
   - Keep the record at about 160 lines or fewer.
   - Mark the owner's words (HQ-0041 and A-8, quoted with links) apart from what is cited and from what is this record's own. The owner's words are not subject to the objection window. The record's own choices are.
2. **Scope.**
   - The runs of ADR-0120 decision 1 only. The record decides the model of their coder calls and nothing else.
   - It does not decide the model of any other agent: the Round-Manager, the evaluator, the selection or the coder-driver sub-agent. HQ-0041 answered for the coder only. If the record seems to need one of them, list it under Boundaries.
   - It does not decide the token axis (HQ-0041 part (2)) or any other design point of slice (d).
3. **Points to weigh.** Weigh each point against at least one alternative, in the Alternatives table.
   - (a) **The member.** Give its name and its place: a top-level member of `instance.json` or a place inside another member. A place inside `hw_profile` raises the version (ADR-0018 decision 2), so weigh that cost. Search `hilclaw/`, `tests/`, `orchestration/` and `ARCHITECTURE/` for the chosen name on the day, and record that search.
   - (b) **The form of the value.** This is the point the owner left to the record. Weigh at least two answers against each other:
     - an alias that Claude Code accepts, which may later resolve to another model;
     - a full model name that Claude Code accepts, fixed when written.
     Count as costs:
     - what a reader of a finished run can tell from the value (FR-13, S10 reproduction);
     - what happens when a named model is no longer offered (C-7 ②, Max subscription).
     Base every statement about what `--model` accepts on the documentation pages, quoted and dated.
   - (c) **What a valid value is.** Say whether the record checks a present value only as a string of some form, or against a list. Weigh at least one alternative, and name the cost of each. The file is never rewritten, so a wrong value stays for the life of the run (ADR-0018 decision 2).
   - (d) **The default.** The owner's words are "when none is named the start applies Opus and records it in instance.json". Say which value of the form of (b) stands for Opus, and how the start puts it into the content when none is given (compare ADR-0076's `n_max` default). Do not decide which function performs the start, or how it learns of a given id (HQ-0032).
   - (e) **A file without the member, and the version.**
     - Say what a coder call of a run whose `instance.json` lacks the member does. Weigh at least: refuse with a new failure kind, or apply the default at the call.
     - Say whether the version of `instance.json` stays `1`, by ADR-0018 decision 2's own rule.
     - If the record needs a new version, a change to another data-plane file, or a change to an existing member, stop and return BLOCKED (data-plane schema change). The owner authorised the record in `instance.json`, nothing more.
   - (f) **How the call learns the model.** ADR-0126 decision 3 fixes the request as exactly `run_id`, `round`, `candidate` and `attempt`. Say how the function of decision 3 obtains the value, for example by reading the run's `instance.json` through the data-root source, and with which checks.
     - Say where any new check stands in the order of ADR-0126 decision 3's failure kinds. The rule there is that every check before `no_container_runtime` creates and consumes nothing.
     - Say which existing failure kinds it reuses, and justify every new kind. Search for each new kind on the day, as in (a).
     - The request stays as ADR-0126 fixes it. If the record needs a new request member, weigh it explicitly as an alternative.
   - (g) **What the value is for.** Say only that it is the model the coder's `claude -p` runs with inside the container. Leave how it reaches that process (a flag, an environment variable, the seam `runtime.run`) to slice (d), and say so.
4. **Walk-through.** Cover at least these rows:
   - a start with no model named;
   - a start with a model named in the chosen form;
   - a start with a value of the wrong form;
   - a coder call of a run whose `instance.json` holds the member;
   - a coder call of a run whose `instance.json` lacks it (for example, a file written before this record);
   - a named model that the plan no longer offers when the call starts. Say only what the record decides here, and leave the rest to runtime acceptance.
5. **Consequences.** These must cover:
   - **The code slices the record enables**, as later tasks, each under the D4 cap:
     - the member in `hilclaw/instance.py` with its tests;
     - the default in `hilclaw/instance_start.py` (or wherever the record places it) with its tests;
     - the read in `hilclaw/coder_call.py` with its tests.
     - Note that a slice touching the start must not overlap open PR #186 while it is open.
   - **Every sentence that becomes less exact**, listed and not edited (D18 hold). At least: ADR-0126 Consequences "Waiting on the owner's #5 A-8" and Boundaries "model and token budget"; ADR-0049 Boundaries "the model and permissions of `claude -p`"; ADR-0032 Context "the token axis and the coder model (#5 A-8, owner)"; the `hilclaw/coder_call.py` docstring if a sentence there becomes false.
   - **New runtime acceptance items**, numbered after ADR-0135's (xxix) and (xxx). For example: the coder's `claude -p` inside the container runs with the recorded value under the user's Max plan. Their HQ is the driver's to raise, not this task's.
   - **The A-13 reading**: doc mode; no code; the one data-plane addition, its version reading, and the owner's authorisation for it.
6. **Boundaries.** List what stays open:
   - the token axis and which usage counts (HQ-0041 part (2), the next record);
   - every other design point of slice (d) (ADR-0126 Consequences, "Design points left to a later record");
   - the models of every other agent;
   - Q1 (HQ-0040) and HQ-0032.
   Edit nothing in `hilclaw/`, `orchestration/`, `tests/`, `.claude/`, any settings file or the `HIL-Claw-data` repository. Edit no earlier ADR.
7. **Requirements.md.**
   - Follow the register's "행 형식" rule (line 84).
   - In the OD-8 row, add one link to ADR-0136 with a few words of topic after `**확정분**:`. If the record answers part of OD-23 (the coder start's model), do the same in the OD-23 row. Use `**오너 결정(날짜, 링크)**` for the owner's part, as the rule says.
   - Rewrite each row's `**잔여**:` in place so that it no longer lists what ADR-0136 answers. Where the OD-19 row's `**잔여**:` names "토큰 — #5 A-8", keep the token axis open and change nothing else.
   - Do not restate the record and do not add a dated note. Change no OD status. Leave NFR-5's text unchanged.
8. **OpenDecisionProposals.md.**
   - Follow the header's "기록 규칙" (line 8).
   - In § OD-8, and in § OD-23 if 7 applies there, add one `- **채택분**` link line for ADR-0136.
   - Rewrite in place any sub-question status or "제안으로 남는 부분" bullet that the record narrows.
   - Write no summary of the decisions and no dated paragraph. Touch § OD-19 only where a sentence there becomes false, in the same way.
9. **StandardScenarios.md.** Re-check coverage by §검사 규칙. Record the result as the first paragraph of §검사 결과 prescribes. If no verdict changes, write only what that paragraph asks for in that case, and add no history entry.
10. **Process.**
    - Doc mode (CLAUDE.md A-13): use branch `claude/T-0371-<slug>`.
    - Run the context-isolated reviewer cycle (at most 7 rounds) to Approve.
    - Rebase onto `origin/main`.
    - Push one squashed commit to main whose message ends with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0371`.
    - The §9 notice on #5 is the driver's. Write its text into `## Result` for the driver to post: English, one paragraph, the link to ADR-0136, the 7-day objection window for the record's own choices.
    - No `claude` is started at any point (D16).

## Out of Scope

- Any code: `hilclaw/instance.py`, `hilclaw/instance_start.py`, `hilclaw/coder_call.py`, `hilclaw/start_instance.py` (PR #186) and their tests. These are later code slices.
- The token axis, which usage counts, and any row of `ARCHITECTURE/SpendAxes.md` (HQ-0041 part (2)).
- Slice (d) itself and its other design points: image, container flags, sign-in, permission mode, prompt, time limit and output stream.
- The front of the call (HQ-0040), `orchestration/agents/coder-driver.md`, and any step of `orchestration/round-manager.md`.
- The models of the Round-Manager, the evaluator, the selection and the coder-driver.
- HQ-0031, HQ-0032, HQ-0043 and HQ-0048. The owner-only items: #5 A/B items beyond A-8's answered part, C-6, OD-25 and OD-3.
- Every less-exact sentence of earlier records: list it, do not edit it (D18 hold).

## Follow-ups

- Next P2-2 record (planner's view): the token axis of HQ-0041 part (2). It covers the first `ARCHITECTURE/SpendAxes.md` row, which usage counts, and how the coder call reads and reports the coder's usage. It is likely tied to the coder's output stream (OD-23 ① (라)).
- Carried from T-0370, for the `orchestration/round-manager.md` slice that replaces the explicit stop (not this task): "One round at most" still says the session ends after the write that ends its round, while the closing steps now put `run.commit` after it. P2-5 needs the two to agree once turns reach the closing steps.

## Result

- **Outcome**: DONE. Landed on main as `4423c35` (doc mode, one squashed commit with `Reviewed-by: reviewer agent (3 rounds, Approve)` and `Task: T-0371`); branch `claude/T-0371-adr-first-case-coder-model` deleted. ADR-0136 was free on `origin/main` and every remote branch.
- **Files**: `ARCHITECTURE/decisions/ADR-0136-od8-first-case-coder-model.md` (new, 165 lines); `ARCHITECTURE/Requirements.md` (OD-8 and OD-23 rows: one `**확정분**` link each with `**오너 결정(2026-10-20, HQ-0041)**`; OD-23 `**잔여**` rewritten in place; OD-19 row and NFR-5 untouched; no status change); `ARCHITECTURE/OpenDecisionProposals.md` (§ OD-8 and § OD-23: one `**채택분**` line each; the "제안으로 남는 부분" bullets narrowed in place); `ARCHITECTURE/StandardScenarios.md` ("최근 재검사" line only: S0, S1, S2, S10 rechecked, no verdict change, no gap, no history entry).
- **Decisions (record's own, subject to the 7-day window)**: top-level member `coder_model`, a full Claude model name (form check only, `claude-` + `[a-z0-9-]`, ≤ 64 chars; aliases, `default` and `[1m]` suffixes are not values), stating the model the call *requests*; the start (ADR-0076 scope) fills in `claude-opus-5-5` (F2, read 2026-10-21) at the `n_max` fill-in step and never replaces a given value; the member may be absent, `schema_version` stays 1; the coder call reads `instance.json` after `no_data_root` and before `output_exists`, with the reserved `run_file_*` kinds (ADR-0019 widened as ADR-0124 did) and one new kind `coder_model_not_stated`; the request of ADR-0126 is unchanged.
- **Review**: round 1 Request changes (requested vs actually-run model given F2's remapping and content-based fallback; form-(B) reading of the ADR-0019 kinds; OD-8 remainder for runs outside the first case; why passing over the member is harmless; Max `default` row); round 2 Approve with minors (fixed); round 3 Approve, no findings.
- **Overlap with unlanded branches**: none taken. `claude/T-0361-*` edits the OD-23 row and section; a later rebase of T-0361 may conflict textually on the OD-23 `**확정분**`, `**채택분**` and `**잔여**` lines.
- **Runtime acceptance items (new; driver raises the HQ, reason `runtime-acceptance`)**: (xxxi) the coder's `claude -p` inside the container, given the recorded full name in the form slice (d) chooses, runs on that model under the user's Max plan, and the model it actually ran on (after any remapping or content-based fallback) can be read back, e.g. from `modelUsage`; (xxxii) what the coder's `claude -p` does when the recorded full name is no longer offered under the plan or is remapped: exits non-zero, runs another model, or warns, and whether its output tells which.
- **§9 notice**: posted on #5 by the driver.
- **Follow-ups (code slices, P2-2, each within the D4 cap)**: (1) `hilclaw/instance.py` member + `coder_model_of` + tests; (2) `hilclaw/instance_start.py` default fill-in with the F2-cited constant + tests, after (1), not overlapping open PR #186; (3) `hilclaw/coder_call.py` read + kinds + hand-over to the seam + tests, after (1); slice (d) after (3). Next record: the token axis of HQ-0041 part (2). Less-exact sentences of earlier records are listed in ADR-0136 Consequences and stay unedited (D18 hold).
- (Result recorded by the driver from the executor's report.)
